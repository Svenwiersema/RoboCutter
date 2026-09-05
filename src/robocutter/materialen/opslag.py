"""SQLite-opslag voor de materialenbibliotheek.

Hoofdstuk 8 legt vast: Demo/Hobby (1 werkplek) gebruikt één lokaal
SQLite-bestand. Dit is dat bestand. Bewust nog GEEN multi-gebruiker-
opslag: een SQLite-bestand op een gedeelde schijf (bv. een NAS) geeft
corruptie-problemen zodra twee pc's er gelijktijdig in schrijven.
Hoofdstuk 8 lost dat voor Pro/Enterprise op met één lokale
netwerk-server-pc waar de andere werkplekken mee verbinden — dat stuk
(een server + netwerkprotocol) bestaat hier nog niet.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from robocutter.materialen.models import (
    Materiaal,
    MateriaalStatus,
    MateriaalType,
    Nerfrichting,
    Rand,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS materialen (
    id TEXT PRIMARY KEY,
    naam TEXT NOT NULL,
    type TEXT NOT NULL,
    lengte REAL NOT NULL,
    breedte REAL NOT NULL,
    derde_afmeting REAL NOT NULL,
    familie TEXT NOT NULL,
    kleur_afwerking TEXT NOT NULL,
    nerfrichting TEXT NOT NULL,
    kerf REAL NOT NULL,
    randafzaag_marge REAL NOT NULL,
    randafzaag_randen TEXT NOT NULL,
    min_reststukgrootte REAL NOT NULL,
    mes_groef_notitie TEXT NOT NULL,
    fabriekskantenband_randen TEXT NOT NULL,
    productcode TEXT NOT NULL,
    leverancier TEXT NOT NULL,
    tags TEXT NOT NULL,
    status TEXT NOT NULL
)
"""


def open_verbinding(db_pad: str | Path) -> sqlite3.Connection:
    verbinding = sqlite3.connect(db_pad)
    verbinding.row_factory = sqlite3.Row
    verbinding.execute(_SCHEMA)
    verbinding.commit()
    return verbinding


def laad_alles(verbinding: sqlite3.Connection) -> list[Materiaal]:
    rijen = verbinding.execute("SELECT * FROM materialen").fetchall()
    return [_rij_naar_materiaal(rij) for rij in rijen]


def opslaan(verbinding: sqlite3.Connection, materiaal: Materiaal) -> None:
    verbinding.execute(
        """
        INSERT OR REPLACE INTO materialen (
            id, naam, type, lengte, breedte, derde_afmeting, familie,
            kleur_afwerking, nerfrichting, kerf, randafzaag_marge,
            randafzaag_randen, min_reststukgrootte, mes_groef_notitie,
            fabriekskantenband_randen, productcode, leverancier, tags,
            status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        _materiaal_naar_rij(materiaal),
    )
    verbinding.commit()


def verwijderen(verbinding: sqlite3.Connection, materiaal_id: str) -> None:
    verbinding.execute("DELETE FROM materialen WHERE id = ?", (materiaal_id,))
    verbinding.commit()


def _materiaal_naar_rij(m: Materiaal) -> tuple:
    return (
        m.id,
        m.naam,
        m.type.value,
        m.lengte,
        m.breedte,
        m.derde_afmeting,
        m.familie,
        m.kleur_afwerking,
        m.nerfrichting.value,
        m.kerf,
        m.randafzaag_marge,
        json.dumps(sorted(r.value for r in m.randafzaag_randen)),
        m.min_reststukgrootte,
        m.mes_groef_notitie,
        json.dumps(sorted(r.value for r in m.fabriekskantenband_randen)),
        m.productcode,
        m.leverancier,
        json.dumps(list(m.tags)),
        m.status.value,
    )


def _rij_naar_materiaal(rij: sqlite3.Row) -> Materiaal:
    return Materiaal(
        id=rij["id"],
        naam=rij["naam"],
        type=MateriaalType(rij["type"]),
        lengte=rij["lengte"],
        breedte=rij["breedte"],
        derde_afmeting=rij["derde_afmeting"],
        familie=rij["familie"],
        kleur_afwerking=rij["kleur_afwerking"],
        nerfrichting=Nerfrichting(rij["nerfrichting"]),
        kerf=rij["kerf"],
        randafzaag_marge=rij["randafzaag_marge"],
        randafzaag_randen=frozenset(Rand(v) for v in json.loads(rij["randafzaag_randen"])),
        min_reststukgrootte=rij["min_reststukgrootte"],
        mes_groef_notitie=rij["mes_groef_notitie"],
        fabriekskantenband_randen=frozenset(
            Rand(v) for v in json.loads(rij["fabriekskantenband_randen"])
        ),
        productcode=rij["productcode"],
        leverancier=rij["leverancier"],
        tags=tuple(json.loads(rij["tags"])),
        status=MateriaalStatus(rij["status"]),
    )
