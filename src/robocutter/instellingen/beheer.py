"""Beheer van de instellingen: validatie, en de effectieve paden die
andere modules (materialen/reststukken/modellen/projecten) gebruiken om
te weten waar hun databasebestand staat.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from robocutter.instellingen.models import (
    GELDIGE_LABEL_SCANCODES,
    GELDIGE_THEMAS,
    GELDIGE_ZAAGSTRATEGIEEN,
    Instellingen,
)
from robocutter.instellingen.opslag import laad_instellingen, sla_instellingen_op, standaard_instellingen_pad

# In een PyInstaller-build (``sys.frozen``) staat de exe meestal in een
# niet-schrijfbare map (bv. Program Files), dus valt de standaard
# datamap daar terug op dezelfde ``%APPDATA%\RoboCutter``-map als
# instellingen.json — in dev-modus blijft dat gewoon <repo>/data.
if getattr(sys, "frozen", False):
    _STANDAARD_DATA_MAP = standaard_instellingen_pad().parent / "data"
else:
    _REPO_ROOT = Path(__file__).resolve().parents[3]
    _STANDAARD_DATA_MAP = _REPO_ROOT / "data"
_DB_BESTANDSNAAM = "robocutter.db"


class OpslagVerplaatsenError(Exception):
    """Bijv. de doelmap heeft al een eigen databasebestand."""


def valideer(instellingen: Instellingen) -> list[str]:
    fouten: list[str] = []
    if instellingen.thema not in GELDIGE_THEMAS:
        fouten.append(f"Onbekend thema: {instellingen.thema!r} (verwacht {', '.join(GELDIGE_THEMAS)}).")
    if instellingen.standaard_zaagstrategie not in GELDIGE_ZAAGSTRATEGIEEN:
        fouten.append(
            f"Onbekende zaagstrategie: {instellingen.standaard_zaagstrategie!r} "
            f"(verwacht {', '.join(GELDIGE_ZAAGSTRATEGIEEN)})."
        )
    if instellingen.label_scancode not in GELDIGE_LABEL_SCANCODES:
        fouten.append(
            f"Onbekende labelscancode: {instellingen.label_scancode!r} "
            f"(verwacht {', '.join(GELDIGE_LABEL_SCANCODES)})."
        )
    return fouten


class InstellingenBeheer:
    """Houdt de huidige instellingen bij en handelt de opslaglocatie-
    wijziging af (met automatisch verplaatsen van een bestaand
    databasebestand, op Svens verzoek)."""

    def __init__(self, bestand_pad: Path | None = None, standaard_data_map: Path | None = None) -> None:
        # ``standaard_data_map`` is injecteerbaar (i.p.v. altijd de echte
        # ``_STANDAARD_DATA_MAP``) zodat tests nooit per ongeluk tegen de
        # échte ``<repo>/data``-map aan kunnen lopen wanneer ze een
        # InstellingenBeheer zonder vooraf ingestelde ``opslag_map``
        # gebruiken — dat verplaatste tijdens het bouwen hiervan eens
        # per ongeluk het echte ontwikkel-databasebestand naar een
        # pytest-tmp-map.
        self._bestand_pad = bestand_pad or standaard_instellingen_pad()
        self._standaard_data_map = standaard_data_map or _STANDAARD_DATA_MAP
        self._instellingen = laad_instellingen(self._bestand_pad)

    @property
    def huidige(self) -> Instellingen:
        return self._instellingen

    def bijwerken(self, **wijzigingen) -> Instellingen:
        kandidaat = Instellingen(**{**self._instellingen.__dict__, **wijzigingen})
        fouten = valideer(kandidaat)
        if fouten:
            raise ValueError("; ".join(fouten))
        self._instellingen = kandidaat
        self._persisteer()
        return self._instellingen

    def effectieve_data_map(self) -> Path:
        if self._instellingen.opslag_map:
            return Path(self._instellingen.opslag_map)
        return self._standaard_data_map

    def effectieve_db_pad(self) -> Path:
        return self.effectieve_data_map() / _DB_BESTANDSNAAM

    def wijzig_opslaglocatie(self, nieuwe_map: Path | str) -> Instellingen:
        """Verplaatst een bestaand databasebestand naar de nieuwe map
        (automatisch, op Svens verzoek) en slaat de nieuwe locatie op.

        Bewuste vereenvoudiging: dit herlaadt geen al-open SQLite-
        verbindingen elders in de app — een lopende sessie moet
        herstart worden voordat andere schermen de nieuwe locatie
        gebruiken."""

        nieuwe_map = Path(nieuwe_map)
        huidige_db_pad = self.effectieve_db_pad()
        nieuwe_db_pad = nieuwe_map / _DB_BESTANDSNAAM

        if huidige_db_pad != nieuwe_db_pad and huidige_db_pad.exists():
            if nieuwe_db_pad.exists():
                raise OpslagVerplaatsenError(
                    f"Er staat al een databasebestand op {nieuwe_db_pad} — kies een andere map."
                )
            nieuwe_map.mkdir(parents=True, exist_ok=True)
            shutil.move(str(huidige_db_pad), str(nieuwe_db_pad))
        else:
            nieuwe_map.mkdir(parents=True, exist_ok=True)

        return self.bijwerken(opslag_map=str(nieuwe_map))

    def _persisteer(self) -> None:
        sla_instellingen_op(self._instellingen, self._bestand_pad)
