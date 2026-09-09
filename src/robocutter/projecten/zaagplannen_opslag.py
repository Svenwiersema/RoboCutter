"""SQLite-opslag voor gegenereerde zaagplannen per project.

Bewaart, per project, alléén het LAATST gegenereerde zaagplan (één rij
per project, ``INSERT OR REPLACE`` bij elke nieuwe generatie) — geen
volledige revisiegeschiedenis (Rev A/B/C...), dat is een apart, groter
onderwerp en blijft bewust uitgesteld (zie OVERDRACHT.md, "Nog niet
gebouwd"). Dit lost specifiek op dat een gegenereerd zaagplan tot nu toe
alleen in het geheugen van het openstaande tabblad leefde en dus
verdween zodra je het project sloot of de app herstartte — Sven vroeg
hier expliciet om ("zorg er ook voor dat zaagplannen binnen een project
worden opgeslagen").

Zelfde aanpak als de andere opslag-modules: bewust hetzelfde db-bestand
(``data/robocutter.db``, pad via ``InstellingenBeheer.effectieve_db_pad()``),
maar in een eigen tabel. De volledige geneste structuur (``PlaatZaagplan``
→ ``ZaagplanResultaat`` → ``Plaatsing``/``Reststuk``/``Zaagsnede`` +
``OnderdeelInfo``) wordt als één JSON-blob per project bewaard, net als
``modelinstanties``/``losse_onderdelen`` in ``projecten/opslag.py`` — een
losse tabel per geneste dataclass zou hier geen enkel voordeel opleveren
(niets hiervan wordt los doorzocht/gefilterd) en alleen complexiteit
toevoegen.

Bewuste beperking van deze eerste stap: geen "is dit zaagplan nog
actueel?"-detectie als de samenstelling van het project verandert ná het
genereren — dat is, net als revisiegeschiedenis, een apart vervolgstuk.
Voorlopig blijft "opnieuw genereren" de manier om een verouderd
opgeslagen zaagplan te vervangen.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from robocutter.modellen.models import Rand as ModRand
from robocutter.optimalisatie.models import Materiaal as OptMateriaal
from robocutter.optimalisatie.models import Plaatsing, Rand as OptRand, Reststuk, ZaagplanResultaat, Zaagsnede
from robocutter.projecten.zaagplannen import OnderdeelInfo, PlaatZaagplan

_SCHEMA = """
CREATE TABLE IF NOT EXISTS zaagplannen (
    project_id TEXT PRIMARY KEY,
    strategie TEXT NOT NULL,
    gegenereerd_op TEXT NOT NULL,
    plannen TEXT NOT NULL,
    waarschuwingen TEXT NOT NULL
)
"""


def open_verbinding(db_pad: str | Path) -> sqlite3.Connection:
    verbinding = sqlite3.connect(db_pad)
    verbinding.row_factory = sqlite3.Row
    verbinding.execute(_SCHEMA)
    verbinding.commit()
    return verbinding


class ZaagplannenOpslag:
    """Dunne wrapper om de ``zaagplannen``-tabel — geen validatie/in-
    memory cache nodig zoals bij de echte bibliotheek-modules (dit is
    afgeleide, herberekenbare data, geen brongegevens die de gebruiker
    zelf beheert), dus bewust geen ``*Bibliotheek``-klasse hier."""

    def __init__(self, verbinding: sqlite3.Connection) -> None:
        self._db = verbinding

    def laad(self, project_id: str) -> tuple[list[PlaatZaagplan], list[str], str] | None:
        """Retourneert (plannen, waarschuwingen, strategie) voor het
        laatst opgeslagen zaagplan van dit project, of ``None`` als er
        nog niets is opgeslagen."""
        rij = self._db.execute(
            "SELECT * FROM zaagplannen WHERE project_id = ?", (project_id,)
        ).fetchone()
        if rij is None:
            return None
        plannen = [_dict_naar_plan(d) for d in json.loads(rij["plannen"])]
        waarschuwingen = list(json.loads(rij["waarschuwingen"]))
        return plannen, waarschuwingen, rij["strategie"]

    def opslaan(
        self, project_id: str, plannen: list[PlaatZaagplan], waarschuwingen: list[str], strategie: str
    ) -> None:
        self._db.execute(
            """
            INSERT OR REPLACE INTO zaagplannen (project_id, strategie, gegenereerd_op, plannen, waarschuwingen)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                project_id,
                strategie,
                datetime.now().isoformat(timespec="seconds"),
                json.dumps([_plan_naar_dict(p) for p in plannen]),
                json.dumps(list(waarschuwingen)),
            ),
        )
        self._db.commit()

    def verwijderen(self, project_id: str) -> None:
        self._db.execute("DELETE FROM zaagplannen WHERE project_id = ?", (project_id,))
        self._db.commit()


def _materiaal_naar_dict(m: OptMateriaal) -> dict:
    return {
        "naam": m.naam,
        "lengte": m.lengte,
        "breedte": m.breedte,
        "dikte": m.dikte,
        "kerf": m.kerf,
        "nerfrichting_aanwezig": m.nerfrichting_aanwezig,
        "randafzaag_marge": m.randafzaag_marge,
        "randafzaag_randen": sorted(r.value for r in m.randafzaag_randen),
        "min_reststukgrootte": m.min_reststukgrootte,
        "fabriekskantenband_randen": sorted(r.value for r in m.fabriekskantenband_randen),
    }


def _dict_naar_materiaal(d: dict) -> OptMateriaal:
    return OptMateriaal(
        naam=d["naam"],
        lengte=d["lengte"],
        breedte=d["breedte"],
        dikte=d["dikte"],
        kerf=d["kerf"],
        nerfrichting_aanwezig=d["nerfrichting_aanwezig"],
        randafzaag_marge=d["randafzaag_marge"],
        randafzaag_randen=frozenset(OptRand(v) for v in d["randafzaag_randen"]),
        min_reststukgrootte=d["min_reststukgrootte"],
        fabriekskantenband_randen=frozenset(OptRand(v) for v in d["fabriekskantenband_randen"]),
    )


def _plaatsing_naar_dict(p: Plaatsing) -> dict:
    return {
        "onderdeel_id": p.onderdeel_id,
        "instantie": p.instantie,
        "x": p.x,
        "y": p.y,
        "breedte": p.breedte,
        "hoogte": p.hoogte,
        "geroteerd": p.geroteerd,
    }


def _dict_naar_plaatsing(d: dict) -> Plaatsing:
    return Plaatsing(
        onderdeel_id=d["onderdeel_id"],
        instantie=d["instantie"],
        x=d["x"],
        y=d["y"],
        breedte=d["breedte"],
        hoogte=d["hoogte"],
        geroteerd=d["geroteerd"],
    )


def _reststuk_naar_dict(r: Reststuk) -> dict:
    return {"x": r.x, "y": r.y, "breedte": r.breedte, "hoogte": r.hoogte}


def _dict_naar_reststuk(d: dict) -> Reststuk:
    return Reststuk(x=d["x"], y=d["y"], breedte=d["breedte"], hoogte=d["hoogte"])


def _zaagsnede_naar_dict(s: Zaagsnede) -> dict:
    return {
        "volgnummer": s.volgnummer,
        "richting": s.richting,
        "positie": s.positie,
        "start": s.start,
        "einde": s.einde,
    }


def _dict_naar_zaagsnede(d: dict) -> Zaagsnede:
    return Zaagsnede(
        volgnummer=d["volgnummer"],
        richting=d["richting"],
        positie=d["positie"],
        start=d["start"],
        einde=d["einde"],
    )


def _resultaat_naar_dict(r: ZaagplanResultaat) -> dict:
    return {
        "materiaal": _materiaal_naar_dict(r.materiaal),
        "strategie": r.strategie,
        "plaatsingen": [_plaatsing_naar_dict(p) for p in r.plaatsingen],
        "reststukken": [_reststuk_naar_dict(x) for x in r.reststukken],
        "afval_oppervlak": r.afval_oppervlak,
        "zaagvolgorde": [_zaagsnede_naar_dict(s) for s in r.zaagvolgorde],
        "niet_geplaatst": list(r.niet_geplaatst),
    }


def _dict_naar_resultaat(d: dict) -> ZaagplanResultaat:
    return ZaagplanResultaat(
        materiaal=_dict_naar_materiaal(d["materiaal"]),
        strategie=d["strategie"],
        plaatsingen=[_dict_naar_plaatsing(p) for p in d["plaatsingen"]],
        reststukken=[_dict_naar_reststuk(x) for x in d["reststukken"]],
        afval_oppervlak=d["afval_oppervlak"],
        zaagvolgorde=[_dict_naar_zaagsnede(s) for s in d["zaagvolgorde"]],
        niet_geplaatst=list(d["niet_geplaatst"]),
    )


def _onderdeel_info_naar_dict(o: OnderdeelInfo) -> dict:
    return {
        "naam": o.naam,
        "herkomst": o.herkomst,
        "kantenband_randen": sorted(r.value for r in o.kantenband_randen),
        "fabriekskantenband_vereist": o.fabriekskantenband_vereist,
    }


def _dict_naar_onderdeel_info(d: dict) -> OnderdeelInfo:
    return OnderdeelInfo(
        naam=d["naam"],
        herkomst=d["herkomst"],
        kantenband_randen=frozenset(ModRand(v) for v in d["kantenband_randen"]),
        fabriekskantenband_vereist=d["fabriekskantenband_vereist"],
    )


def _plan_naar_dict(p: PlaatZaagplan) -> dict:
    return {
        "materiaal_id": p.materiaal_id,
        "materiaal_naam": p.materiaal_naam,
        "resultaat": _resultaat_naar_dict(p.resultaat),
        "plaat_nummer": p.plaat_nummer,
        "platen_totaal": p.platen_totaal,
        "onderdeel_info": {k: _onderdeel_info_naar_dict(v) for k, v in p.onderdeel_info.items()},
    }


def _dict_naar_plan(d: dict) -> PlaatZaagplan:
    return PlaatZaagplan(
        materiaal_id=d["materiaal_id"],
        materiaal_naam=d["materiaal_naam"],
        resultaat=_dict_naar_resultaat(d["resultaat"]),
        plaat_nummer=d["plaat_nummer"],
        platen_totaal=d["platen_totaal"],
        onderdeel_info={k: _dict_naar_onderdeel_info(v) for k, v in d["onderdeel_info"].items()},
    )
