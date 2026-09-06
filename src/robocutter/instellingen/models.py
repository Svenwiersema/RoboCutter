"""Datamodel voor de app-brede instellingen. Eén enkel record (geen
lijst/CRUD zoals de bibliotheken) — dit is letterlijk "de instellingen".

``thema`` en ``standaard_zaagstrategie`` hergebruiken bewust bestaande
stringwaarden uit andere modules (``robocutter.ui.theme.LICHT.naam``/
``DONKER.naam`` resp. ``robocutter.optimalisatie.engine.genereer_zaagplan``'s
``strategie``-parameter) in plaats van nieuwe enums te verzinnen voor
iets dat al bestaat.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["Instellingen", "GELDIGE_THEMAS", "GELDIGE_ZAAGSTRATEGIEEN"]

GELDIGE_THEMAS = ("licht", "donker")
GELDIGE_ZAAGSTRATEGIEEN = ("efficient", "rijen")


@dataclass
class Instellingen:
    opslag_map: str | None = None  # None = standaardlocatie (<repo>/data)
    thema: str = "licht"
    bedrijfslogo_pad: str | None = None
    standaard_zaagstrategie: str = "efficient"
    werkvoorbereider_naam: str = ""
