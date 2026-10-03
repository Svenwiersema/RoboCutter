"""SQLite-opslag voor de reststukken van een project (zie
``project_reststukken.py``). Zelfde db-bestand als de rest
(``InstellingenBeheer.effectieve_db_pad()``), eigen tabel."""

from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from robocutter.projecten.project_reststukken import ProjectReststuk

_SCHEMA = """
CREATE TABLE IF NOT EXISTS project_reststukken (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    volgnummer INTEGER NOT NULL,
    materiaal_id TEXT NOT NULL,
    lengte REAL NOT NULL,
    breedte REAL NOT NULL,
    bron TEXT NOT NULL,
    status TEXT NOT NULL,
    plaat_nummer INTEGER,
    platen_totaal INTEGER,
    plaat_lengte REAL NOT NULL,
    plaat_breedte REAL NOT NULL,
    x REAL NOT NULL,
    y REAL NOT NULL,
    oorspronkelijke_lengte REAL,
    oorspronkelijke_breedte REAL,
    vrijgegeven_op TEXT,
    uit_bibliotheek_reststuk INTEGER NOT NULL DEFAULT 0,
    fabriekskantenband_randen TEXT NOT NULL DEFAULT '[]'
)
"""


def open_verbinding(db_pad: str | Path) -> sqlite3.Connection:
    verbinding = sqlite3.connect(db_pad)
    verbinding.row_factory = sqlite3.Row
    verbinding.execute(_SCHEMA)
    kolommen = {rij["name"] for rij in verbinding.execute("PRAGMA table_info(project_reststukken)")}
    for kolom, definitie in (
        ("uit_bibliotheek_reststuk", "INTEGER NOT NULL DEFAULT 0"),
        ("fabriekskantenband_randen", "TEXT NOT NULL DEFAULT '[]'"),
    ):
        if kolom not in kolommen:
            verbinding.execute(f"ALTER TABLE project_reststukken ADD COLUMN {kolom} {definitie}")
    verbinding.commit()
    return verbinding


def laad_alles(verbinding: sqlite3.Connection) -> list[ProjectReststuk]:
    rijen = verbinding.execute("SELECT * FROM project_reststukken").fetchall()
    return [_rij_naar_item(rij) for rij in rijen]


def opslaan(verbinding: sqlite3.Connection, item: ProjectReststuk) -> None:
    verbinding.execute(
        """
        INSERT OR REPLACE INTO project_reststukken (
            id, project_id, volgnummer, materiaal_id, lengte, breedte, bron,
            status, plaat_nummer, platen_totaal, plaat_lengte, plaat_breedte,
            x, y, oorspronkelijke_lengte, oorspronkelijke_breedte, vrijgegeven_op,
            uit_bibliotheek_reststuk, fabriekskantenband_randen
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item.id,
            item.project_id,
            item.volgnummer,
            item.materiaal_id,
            item.lengte,
            item.breedte,
            item.bron.value,
            item.status.value,
            item.plaat_nummer,
            item.platen_totaal,
            item.plaat_lengte,
            item.plaat_breedte,
            item.x,
            item.y,
            item.oorspronkelijke_lengte,
            item.oorspronkelijke_breedte,
            item.vrijgegeven_op.isoformat() if item.vrijgegeven_op else None,
            int(item.uit_bibliotheek_reststuk),
            json.dumps(sorted(r.value for r in item.fabriekskantenband_randen)),
        ),
    )
    verbinding.commit()


def verwijderen(verbinding: sqlite3.Connection, item_id: str) -> None:
    verbinding.execute("DELETE FROM project_reststukken WHERE id = ?", (item_id,))
    verbinding.commit()


def _rij_naar_item(rij: sqlite3.Row) -> ProjectReststuk:
    from robocutter.optimalisatie.models import Rand
    from robocutter.projecten.project_reststukken import (
        ProjectReststuk,
        ProjectReststukBron,
        ProjectReststukStatus,
    )

    return ProjectReststuk(
        id=rij["id"],
        project_id=rij["project_id"],
        volgnummer=rij["volgnummer"],
        materiaal_id=rij["materiaal_id"],
        lengte=rij["lengte"],
        breedte=rij["breedte"],
        bron=ProjectReststukBron(rij["bron"]),
        status=ProjectReststukStatus(rij["status"]),
        plaat_nummer=rij["plaat_nummer"],
        platen_totaal=rij["platen_totaal"],
        plaat_lengte=rij["plaat_lengte"],
        plaat_breedte=rij["plaat_breedte"],
        x=rij["x"],
        y=rij["y"],
        oorspronkelijke_lengte=rij["oorspronkelijke_lengte"],
        oorspronkelijke_breedte=rij["oorspronkelijke_breedte"],
        vrijgegeven_op=date.fromisoformat(rij["vrijgegeven_op"]) if rij["vrijgegeven_op"] else None,
        uit_bibliotheek_reststuk=bool(rij["uit_bibliotheek_reststuk"]),
        fabriekskantenband_randen=frozenset(Rand(v) for v in json.loads(rij["fabriekskantenband_randen"])),
    )
