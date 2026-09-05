"""SQLite-opslag voor de reststukkenbibliotheek.

Zelfde aanpak als ``robocutter.materialen.opslag`` (hoofdstuk 8:
Demo/Hobby = één lokaal SQLite-bestand) — bewust hetzelfde db-bestand
(``data/robocutter.db``), maar in een eigen tabel, want de
materialenbibliotheek en de reststukkenbibliotheek zijn twee aparte
bibliotheken (zie hoofdstuk 3) die wél in dezelfde lokale database
mogen leven.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from robocutter.reststukken.models import Reststuk, ReststukStatus

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reststukken (
    id TEXT PRIMARY KEY,
    materiaal_id TEXT NOT NULL,
    lengte REAL NOT NULL,
    breedte REAL NOT NULL,
    herkomst_project TEXT NOT NULL,
    herkomst_model TEXT NOT NULL,
    status TEXT NOT NULL
)
"""


def open_verbinding(db_pad: str | Path) -> sqlite3.Connection:
    verbinding = sqlite3.connect(db_pad)
    verbinding.row_factory = sqlite3.Row
    verbinding.execute(_SCHEMA)
    verbinding.commit()
    return verbinding


def laad_alles(verbinding: sqlite3.Connection) -> list[Reststuk]:
    rijen = verbinding.execute("SELECT * FROM reststukken").fetchall()
    return [_rij_naar_reststuk(rij) for rij in rijen]


def opslaan(verbinding: sqlite3.Connection, reststuk: Reststuk) -> None:
    verbinding.execute(
        """
        INSERT OR REPLACE INTO reststukken (
            id, materiaal_id, lengte, breedte, herkomst_project,
            herkomst_model, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            reststuk.id,
            reststuk.materiaal_id,
            reststuk.lengte,
            reststuk.breedte,
            reststuk.herkomst_project,
            reststuk.herkomst_model,
            reststuk.status.value,
        ),
    )
    verbinding.commit()


def verwijderen(verbinding: sqlite3.Connection, reststuk_id: str) -> None:
    verbinding.execute("DELETE FROM reststukken WHERE id = ?", (reststuk_id,))
    verbinding.commit()


def _rij_naar_reststuk(rij: sqlite3.Row) -> Reststuk:
    return Reststuk(
        id=rij["id"],
        materiaal_id=rij["materiaal_id"],
        lengte=rij["lengte"],
        breedte=rij["breedte"],
        herkomst_project=rij["herkomst_project"],
        herkomst_model=rij["herkomst_model"],
        status=ReststukStatus(rij["status"]),
    )
