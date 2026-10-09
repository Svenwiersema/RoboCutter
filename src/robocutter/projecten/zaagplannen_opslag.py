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
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from robocutter.instellingen.models import normaliseer_zaagstrategie
from robocutter.modellen.models import Nerfrichting as ModNerfrichting
from robocutter.modellen.models import Rand as ModRand
from robocutter.optimalisatie.models import Materiaal as OptMateriaal
from robocutter.optimalisatie.models import Plaatsing, Rand as OptRand, Reststuk, ZaagplanResultaat, Zaagsnede
from robocutter.projecten.models import Project
from robocutter.projecten.opslag import dict_naar_project, project_naar_dict
from robocutter.projecten.zaagplan_bijwerken import VervallenPlaat
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


# Later toegevoegde kolommen (revisies, "Niet gecontroleerd"): oudere
# databases krijgen ze erbij, met NULL voor bestaande zaagplannen.
_EXTRA_KOLOMMEN = {"bron": "TEXT", "revisie": "TEXT", "vervallen": "TEXT"}


def open_verbinding(db_pad: str | Path) -> sqlite3.Connection:
    verbinding = sqlite3.connect(db_pad)
    verbinding.row_factory = sqlite3.Row
    verbinding.execute(_SCHEMA)
    bestaand = {rij["name"] for rij in verbinding.execute("PRAGMA table_info(zaagplannen)")}
    for naam, soort in _EXTRA_KOLOMMEN.items():
        if naam not in bestaand:
            verbinding.execute(f"ALTER TABLE zaagplannen ADD COLUMN {naam} {soort}")
    verbinding.commit()
    return verbinding


@dataclass
class ZaagplanHerkomst:
    """Waar een opgeslagen zaagplan op gebaseerd is: de samenstelling van
    het project op het moment van genereren (``None`` bij een zaagplan van
    vóór deze functie) en de revisie van dat moment ("Rev A", "Rev A*" als
    er niet-vastgelegde wijzigingen waren, "" zonder revisies)."""

    gegenereerd_op: datetime
    bron: Project | None
    revisie: str


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
        return plannen, waarschuwingen, normaliseer_zaagstrategie(rij["strategie"])

    def laad_herkomst(self, project_id: str) -> ZaagplanHerkomst | None:
        rij = self._db.execute(
            "SELECT gegenereerd_op, bron, revisie FROM zaagplannen WHERE project_id = ?", (project_id,)
        ).fetchone()
        if rij is None:
            return None
        return ZaagplanHerkomst(
            gegenereerd_op=datetime.fromisoformat(rij["gegenereerd_op"]),
            bron=dict_naar_project(json.loads(rij["bron"])) if rij["bron"] else None,
            revisie=rij["revisie"] or "",
        )

    def laad_vervallen(self, project_id: str) -> list[VervallenPlaat]:
        """De platen die bij de laatste bijwerking vervallen zijn (leeg na
        een volledig nieuw zaagplan)."""
        rij = self._db.execute(
            "SELECT vervallen FROM zaagplannen WHERE project_id = ?", (project_id,)
        ).fetchone()
        if rij is None or not rij["vervallen"]:
            return []
        return [VervallenPlaat(**d) for d in json.loads(rij["vervallen"])]

    def opslaan(
        self,
        project_id: str,
        plannen: list[PlaatZaagplan],
        waarschuwingen: list[str],
        strategie: str,
        bron: Project | None = None,
        revisie: str = "",
        vervallen: list[VervallenPlaat] | None = None,
    ) -> None:
        """``bron``: de samenstelling waaruit dit zaagplan gegenereerd is
        (voor "Niet gecontroleerd"), ``revisie``: zie ``ZaagplanHerkomst``,
        ``vervallen``: platen die bij deze bijwerking wegvielen."""
        self._db.execute(
            """
            INSERT OR REPLACE INTO zaagplannen (
                project_id, strategie, gegenereerd_op, plannen, waarschuwingen, bron, revisie, vervallen
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                strategie,
                datetime.now().isoformat(timespec="seconds"),
                json.dumps([_plan_naar_dict(p) for p in plannen]),
                json.dumps(list(waarschuwingen)),
                json.dumps(project_naar_dict(bron)) if bron is not None else None,
                revisie,
                json.dumps([vars(v) for v in vervallen or []]),
            ),
        )
        self._db.commit()

    def werk_plannen_bij(self, project_id: str, plannen: list[PlaatZaagplan]) -> None:
        """Alleen de platen opnieuw wegschrijven (bv. na gezaagd afvinken);
        herkomst en tijdstip van genereren blijven staan."""
        self._db.execute(
            "UPDATE zaagplannen SET plannen = ? WHERE project_id = ?",
            (json.dumps([_plan_naar_dict(p) for p in plannen]), project_id),
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
        "niet_geplaatst_redenen": dict(r.niet_geplaatst_redenen),
    }


def _dict_naar_resultaat(d: dict) -> ZaagplanResultaat:
    return ZaagplanResultaat(
        materiaal=_dict_naar_materiaal(d["materiaal"]),
        strategie=normaliseer_zaagstrategie(d["strategie"]),
        plaatsingen=[_dict_naar_plaatsing(p) for p in d["plaatsingen"]],
        reststukken=[_dict_naar_reststuk(x) for x in d["reststukken"]],
        afval_oppervlak=d["afval_oppervlak"],
        zaagvolgorde=[_dict_naar_zaagsnede(s) for s in d["zaagvolgorde"]],
        niet_geplaatst=list(d["niet_geplaatst"]),
        niet_geplaatst_redenen=dict(d.get("niet_geplaatst_redenen", {})),
    )


def _onderdeel_info_naar_dict(o: OnderdeelInfo) -> dict:
    return {
        "naam": o.naam,
        "herkomst": o.herkomst,
        "kantenband_randen": sorted(r.value for r in o.kantenband_randen),
        "fabriekskantenband_vereist": o.fabriekskantenband_vereist,
        "nerfrichting_vereist": o.nerfrichting_vereist.value,
    }


def _dict_naar_onderdeel_info(d: dict) -> OnderdeelInfo:
    return OnderdeelInfo(
        naam=d["naam"],
        herkomst=d["herkomst"],
        kantenband_randen=frozenset(ModRand(v) for v in d["kantenband_randen"]),
        fabriekskantenband_vereist=d["fabriekskantenband_vereist"],
        # Val terug op "geen" voor een zaagplan dat vóór de labelgeneratie-
        # stap is opgeslagen en dit veld dus nog niet heeft.
        nerfrichting_vereist=ModNerfrichting(d.get("nerfrichting_vereist", "geen")),
    )


def _plan_naar_dict(p: PlaatZaagplan) -> dict:
    return {
        "materiaal_id": p.materiaal_id,
        "materiaal_naam": p.materiaal_naam,
        "resultaat": _resultaat_naar_dict(p.resultaat),
        "plaat_nummer": p.plaat_nummer,
        "platen_totaal": p.platen_totaal,
        "onderdeel_info": {k: _onderdeel_info_naar_dict(v) for k, v in p.onderdeel_info.items()},
        "reststuk_id": p.reststuk_id,
        "revisie": p.revisie,
        "gezaagd": sorted([oid, inst] for oid, inst in p.gezaagd),
        "bijwerking": p.bijwerking,
        "toegevoegd": sorted([oid, inst] for oid, inst in p.toegevoegd),
    }


def _dict_naar_plan(d: dict) -> PlaatZaagplan:
    return PlaatZaagplan(
        materiaal_id=d["materiaal_id"],
        materiaal_naam=d["materiaal_naam"],
        resultaat=_dict_naar_resultaat(d["resultaat"]),
        plaat_nummer=d["plaat_nummer"],
        platen_totaal=d["platen_totaal"],
        onderdeel_info={k: _dict_naar_onderdeel_info(v) for k, v in d["onderdeel_info"].items()},
        reststuk_id=d.get("reststuk_id"),
        revisie=d.get("revisie", ""),
        gezaagd={(oid, int(inst)) for oid, inst in d.get("gezaagd", [])},
        bijwerking=d.get("bijwerking", ""),
        toegevoegd={(oid, int(inst)) for oid, inst in d.get("toegevoegd", [])},
    )
