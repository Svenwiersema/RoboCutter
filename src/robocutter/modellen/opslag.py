"""SQLite-opslag voor de modellenbibliotheek.

Zelfde aanpak als ``robocutter.reststukken.opslag``: bewust hetzelfde
db-bestand (``data/robocutter.db``), maar in een eigen tabel. De
``onderdelen`` en ``submodellen``-lijsten van een model worden als JSON
in de rij opgeslagen (zelfde aanpak als ``tags`` bij Materialen).

``onderdeel_naar_dict``/``dict_naar_onderdeel`` zijn bewust publiek: de
projectenbibliotheek (module 1/4) hergebruikt ze om ``ModelOnderdeel``-
snapshots op te slaan, in plaats van dezelfde (de)serialisatie nog eens
te dupliceren.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from robocutter.modellen.models import Model, ModelOnderdeel, Nerfrichting, Rand, SubModelVerwijzing

_SCHEMA = """
CREATE TABLE IF NOT EXISTS modellen (
    id TEXT PRIMARY KEY,
    naam TEXT NOT NULL,
    omschrijving TEXT NOT NULL,
    map TEXT NOT NULL,
    tags TEXT NOT NULL,
    onderdelen TEXT NOT NULL,
    submodellen TEXT NOT NULL
)
"""


def open_verbinding(db_pad: str | Path) -> sqlite3.Connection:
    verbinding = sqlite3.connect(db_pad)
    verbinding.row_factory = sqlite3.Row
    verbinding.execute(_SCHEMA)
    verbinding.commit()
    return verbinding


def laad_alles(verbinding: sqlite3.Connection) -> list[Model]:
    rijen = verbinding.execute("SELECT * FROM modellen").fetchall()
    return [_rij_naar_model(rij) for rij in rijen]


def opslaan(verbinding: sqlite3.Connection, model: Model) -> None:
    verbinding.execute(
        """
        INSERT OR REPLACE INTO modellen (
            id, naam, omschrijving, map, tags, onderdelen, submodellen
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        _model_naar_rij(model),
    )
    verbinding.commit()


def verwijderen(verbinding: sqlite3.Connection, model_id: str) -> None:
    verbinding.execute("DELETE FROM modellen WHERE id = ?", (model_id,))
    verbinding.commit()


def onderdeel_naar_dict(o: ModelOnderdeel) -> dict:
    return {
        "id": o.id,
        "naam": o.naam,
        "materiaal_id": o.materiaal_id,
        "breedte": o.breedte,
        "hoogte": o.hoogte,
        "aantal": o.aantal,
        "nerfrichting_vereist": o.nerfrichting_vereist.value,
        "kantenband_randen": sorted(r.value for r in o.kantenband_randen),
        "fabriekskantenband_vereist": o.fabriekskantenband_vereist,
        "groep_id": o.groep_id,
        "groep_volgorde": o.groep_volgorde,
    }


def dict_naar_onderdeel(d: dict) -> ModelOnderdeel:
    return ModelOnderdeel(
        id=d["id"],
        naam=d["naam"],
        materiaal_id=d["materiaal_id"],
        breedte=d["breedte"],
        hoogte=d["hoogte"],
        aantal=d["aantal"],
        nerfrichting_vereist=Nerfrichting(d["nerfrichting_vereist"]),
        kantenband_randen=frozenset(Rand(v) for v in d["kantenband_randen"]),
        fabriekskantenband_vereist=d["fabriekskantenband_vereist"],
        groep_id=d.get("groep_id"),
        groep_volgorde=d.get("groep_volgorde"),
    )


def _submodel_naar_dict(s: SubModelVerwijzing) -> dict:
    return {"model_id": s.model_id, "aantal": s.aantal}


def _dict_naar_submodel(d: dict) -> SubModelVerwijzing:
    return SubModelVerwijzing(model_id=d["model_id"], aantal=d["aantal"])


def _model_naar_rij(m: Model) -> tuple:
    return (
        m.id,
        m.naam,
        m.omschrijving,
        m.map,
        json.dumps(list(m.tags)),
        json.dumps([onderdeel_naar_dict(o) for o in m.onderdelen]),
        json.dumps([_submodel_naar_dict(s) for s in m.submodellen]),
    )


def _rij_naar_model(rij: sqlite3.Row) -> Model:
    return Model(
        id=rij["id"],
        naam=rij["naam"],
        omschrijving=rij["omschrijving"],
        map=rij["map"],
        tags=tuple(json.loads(rij["tags"])),
        onderdelen=[dict_naar_onderdeel(d) for d in json.loads(rij["onderdelen"])],
        submodellen=[_dict_naar_submodel(d) for d in json.loads(rij["submodellen"])],
    )
