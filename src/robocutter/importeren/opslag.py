"""SQLite-opslag voor onthouden materiaalkoppelingen bij importeren: welke
materiaaltekst uit een importbestand bij welk materiaal hoort. Zelfde
db-bestand als de bibliotheken, eigen tabel."""

from __future__ import annotations

import sqlite3
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS import_koppelingen (
    tekst TEXT PRIMARY KEY,
    materiaal_id TEXT NOT NULL
)
"""


def open_verbinding(db_pad: str | Path) -> sqlite3.Connection:
    verbinding = sqlite3.connect(db_pad)
    verbinding.row_factory = sqlite3.Row
    verbinding.execute(_SCHEMA)
    verbinding.commit()
    return verbinding


def laad_alles(verbinding: sqlite3.Connection) -> dict[str, str]:
    return {rij["tekst"]: rij["materiaal_id"] for rij in verbinding.execute("SELECT * FROM import_koppelingen")}


def opslaan(verbinding: sqlite3.Connection, tekst: str, materiaal_id: str) -> None:
    verbinding.execute(
        "INSERT OR REPLACE INTO import_koppelingen (tekst, materiaal_id) VALUES (?, ?)", (tekst, materiaal_id)
    )
    verbinding.commit()


def verwijderen(verbinding: sqlite3.Connection, tekst: str) -> None:
    verbinding.execute("DELETE FROM import_koppelingen WHERE tekst = ?", (tekst,))
    verbinding.commit()
