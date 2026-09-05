"""Datamodel voor één reststuk-record in de reststukkenbibliotheek.

Zie design/chapters/module-3-materialen.md voor het bevestigde
veldenoverzicht. Een reststuk "neemt de eigenschappen van zijn
onderliggende materiaal over" (kerf, nerfrichting, randafzaag-marge,
type, familie, enz.) — dat wordt hier bewust niet gekopieerd naar dit
record (dan zou het uit de pas kunnen lopen als het materiaal wijzigt),
maar opgehaald via ``materiaal_id`` uit de materialenbibliotheek
(zie ``reststukken.bibliotheek.ReststukkenBibliotheek``). Dit record
bevat alleen wat een reststuk uniek maakt: de resterende afmetingen,
herkomst en status.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

__all__ = ["ReststukStatus", "Reststuk"]


class ReststukStatus(str, Enum):
    BESCHIKBAAR = "beschikbaar"
    GEBRUIKT = "gebruikt"


@dataclass
class Reststuk:
    """Eén reststuk (bevestigde velden uit hoofdstuk 3). De dikte is niet
    los opgeslagen — die is altijd gelijk aan de dikte van het
    onderliggende materiaal (``materiaal_id``), een reststuk kan alleen
    korter/smaller worden, niet dunner."""

    id: str
    materiaal_id: str
    lengte: float = 0.0  # mm, resterende lengte
    breedte: float = 0.0  # mm, resterende breedte
    herkomst_project: str = ""
    herkomst_model: str = ""
    status: ReststukStatus = ReststukStatus.BESCHIKBAAR
