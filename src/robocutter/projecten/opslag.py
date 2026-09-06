"""SQLite-opslag voor de projectenbibliotheek.

Zelfde aanpak als ``robocutter.modellen.opslag``: bewust hetzelfde
db-bestand (``data/robocutter.db``), maar in een eigen tabel.
Hergebruikt ``onderdeel_naar_dict``/``dict_naar_onderdeel`` uit
``robocutter.modellen.opslag`` voor de (de)serialisatie van
``ModelOnderdeel``-records, i.p.v. dat te dupliceren.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

from robocutter.modellen.opslag import dict_naar_onderdeel, onderdeel_naar_dict
from robocutter.projecten.models import Project, ProjectModelInstantie, ProjectStatus

_SCHEMA = """
CREATE TABLE IF NOT EXISTS projecten (
    id TEXT PRIMARY KEY,
    naam TEXT NOT NULL,
    klant TEXT NOT NULL,
    contactpersoon TEXT NOT NULL,
    email TEXT NOT NULL,
    telefoon TEXT NOT NULL,
    opdrachtnummer TEXT NOT NULL,
    startdatum TEXT,
    opleverdatum TEXT,
    status TEXT NOT NULL,
    gearchiveerd INTEGER NOT NULL,
    modelinstanties TEXT NOT NULL,
    losse_onderdelen TEXT NOT NULL
)
"""


def open_verbinding(db_pad: str | Path) -> sqlite3.Connection:
    verbinding = sqlite3.connect(db_pad)
    verbinding.row_factory = sqlite3.Row
    verbinding.execute(_SCHEMA)
    verbinding.commit()
    return verbinding


def laad_alles(verbinding: sqlite3.Connection) -> list[Project]:
    rijen = verbinding.execute("SELECT * FROM projecten").fetchall()
    return [_rij_naar_project(rij) for rij in rijen]


def opslaan(verbinding: sqlite3.Connection, project: Project) -> None:
    verbinding.execute(
        """
        INSERT OR REPLACE INTO projecten (
            id, naam, klant, contactpersoon, email, telefoon, opdrachtnummer,
            startdatum, opleverdatum, status, gearchiveerd, modelinstanties,
            losse_onderdelen
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        _project_naar_rij(project),
    )
    verbinding.commit()


def verwijderen(verbinding: sqlite3.Connection, project_id: str) -> None:
    verbinding.execute("DELETE FROM projecten WHERE id = ?", (project_id,))
    verbinding.commit()


def _instantie_naar_dict(i: ProjectModelInstantie) -> dict:
    return {
        "id": i.id,
        "model_id": i.model_id,
        "model_naam": i.model_naam,
        "aantal": i.aantal,
        "onderdelen": [onderdeel_naar_dict(o) for o in i.onderdelen],
    }


def _dict_naar_instantie(d: dict) -> ProjectModelInstantie:
    return ProjectModelInstantie(
        id=d["id"],
        model_id=d["model_id"],
        model_naam=d["model_naam"],
        aantal=d["aantal"],
        onderdelen=[dict_naar_onderdeel(o) for o in d["onderdelen"]],
    )


def _datum_naar_tekst(d: date | None) -> str | None:
    return d.isoformat() if d is not None else None


def _tekst_naar_datum(t: str | None) -> date | None:
    return date.fromisoformat(t) if t is not None else None


def _project_naar_rij(p: Project) -> tuple:
    return (
        p.id,
        p.naam,
        p.klant,
        p.contactpersoon,
        p.email,
        p.telefoon,
        p.opdrachtnummer,
        _datum_naar_tekst(p.startdatum),
        _datum_naar_tekst(p.opleverdatum),
        p.status.value,
        int(p.gearchiveerd),
        json.dumps([_instantie_naar_dict(i) for i in p.modelinstanties]),
        json.dumps([onderdeel_naar_dict(o) for o in p.losse_onderdelen]),
    )


def _rij_naar_project(rij: sqlite3.Row) -> Project:
    return Project(
        id=rij["id"],
        naam=rij["naam"],
        klant=rij["klant"],
        contactpersoon=rij["contactpersoon"],
        email=rij["email"],
        telefoon=rij["telefoon"],
        opdrachtnummer=rij["opdrachtnummer"],
        startdatum=_tekst_naar_datum(rij["startdatum"]),
        opleverdatum=_tekst_naar_datum(rij["opleverdatum"]),
        status=ProjectStatus(rij["status"]),
        gearchiveerd=bool(rij["gearchiveerd"]),
        modelinstanties=[_dict_naar_instantie(d) for d in json.loads(rij["modelinstanties"])],
        losse_onderdelen=[dict_naar_onderdeel(d) for d in json.loads(rij["losse_onderdelen"])],
    )
