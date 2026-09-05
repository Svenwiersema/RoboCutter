"""Datamodel voor één materiaal-record in de materialenbibliotheek.

Zie design/chapters/module-3-materialen.md voor het bevestigde
veldenoverzicht. Dit is bewust een los model van
``robocutter.optimalisatie.models.Materiaal`` (dat een enkele
voorraadplaat beschrijft zoals de optimalisatie-motor die nodig
heeft) — het bibliotheek-record draagt daarnaast metadata
(naam, familie, leverancier, tags, status) die de optimizer niet
gebruikt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from robocutter.optimalisatie.models import Nerfrichting, Rand

__all__ = ["MateriaalType", "MateriaalStatus", "Nerfrichting", "Rand", "Materiaal"]


class MateriaalType(str, Enum):
    """Platen en balken staan in dezelfde lijst, zie hoofdstuk 3/principe 5."""

    PLAAT = "plaat"
    BALK = "balk"


class MateriaalStatus(str, Enum):
    """Archiveren is de standaard, definitief verwijderen een bewuste,
    aparte actie die alleen vanuit "gearchiveerd" bereikbaar is."""

    ACTIEF = "actief"
    GEARCHIVEERD = "gearchiveerd"


@dataclass
class Materiaal:
    """Eén materiaal-record uit de materialenbibliotheek (bevestigde
    velden uit hoofdstuk 3). Nadrukkelijk géén voorraadaantal of
    prijs/kostprijs — dat is een ERP-taak (hoofdstuk 9)."""

    id: str
    naam: str
    type: MateriaalType
    lengte: float = 0.0  # mm
    breedte: float = 0.0  # mm
    derde_afmeting: float = 0.0  # mm: dikte (plaat) of hoogte (balk)
    familie: str = ""
    kleur_afwerking: str = ""
    nerfrichting: Nerfrichting = Nerfrichting.GEEN
    kerf: float = 4.0  # mm
    randafzaag_marge: float = 0.0  # mm
    randafzaag_randen: frozenset[Rand] = field(default_factory=frozenset)
    min_reststukgrootte: float = 0.0  # mm
    mes_groef_notitie: str = ""
    fabriekskantenband_randen: frozenset[Rand] = field(default_factory=frozenset)
    productcode: str = ""
    leverancier: str = ""
    tags: tuple[str, ...] = ()
    status: MateriaalStatus = MateriaalStatus.ACTIEF

    @property
    def derde_afmeting_label(self) -> str:
        return "Dikte" if self.type == MateriaalType.PLAAT else "Hoogte"
