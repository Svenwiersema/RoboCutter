"""SQLite-opslag voor projectrevisies (zie ``revisies.py``). Zelfde
db-bestand als de rest (``InstellingenBeheer.effectieve_db_pad()``),
eigen tabel. De momentopname van het project gaat als één JSON-blob mee,
in dezelfde vorm als ``projecten/opslag.py`` een project bewaart."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from robocutter.projecten.opslag import dict_naar_project, project_naar_dict

if TYPE_CHECKING:
    from robocutter.projecten.revisies import ProjectRevisie

_SCHEMA = """
CREATE TABLE IF NOT EXISTS project_revisies (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    nummer INTEGER NOT NULL,
    aangemaakt TEXT NOT NULL,
    samenvatting TEXT NOT NULL,
    notitie TEXT NOT NULL,
    momentopname TEXT NOT NULL
)
"""


def open_verbinding(db_pad: str | Path) -> sqlite3.Connection:
    verbinding = sqlite3.connect(db_pad)
    verbinding.row_factory = sqlite3.Row
    verbinding.execute(_SCHEMA)
    verbinding.commit()
    return verbinding


def laad_alles(verbinding: sqlite3.Connection) -> list["ProjectRevisie"]:
    from robocutter.projecten.revisies import ProjectRevisie

    return [
        ProjectRevisie(
            id=rij["id"],
            project_id=rij["project_id"],
            nummer=rij["nummer"],
            aangemaakt=datetime.fromisoformat(rij["aangemaakt"]),
            momentopname=dict_naar_project(json.loads(rij["momentopname"])),
            samenvatting=json.loads(rij["samenvatting"]),
            notitie=rij["notitie"],
        )
        for rij in verbinding.execute("SELECT * FROM project_revisies").fetchall()
    ]


def opslaan(verbinding: sqlite3.Connection, revisie: "ProjectRevisie") -> None:
    verbinding.execute(
        """
        INSERT OR REPLACE INTO project_revisies (
            id, project_id, nummer, aangemaakt, samenvatting, notitie, momentopname
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            revisie.id,
            revisie.project_id,
            revisie.nummer,
            revisie.aangemaakt.isoformat(),
            json.dumps(revisie.samenvatting),
            revisie.notitie,
            json.dumps(project_naar_dict(revisie.momentopname)),
        ),
    )
    verbinding.commit()


def verwijder_project(verbinding: sqlite3.Connection, project_id: str) -> None:
    verbinding.execute("DELETE FROM project_revisies WHERE project_id = ?", (project_id,))
    verbinding.commit()
