"""Datamodel voor het RoboCutter-importformaat (hoofdstuk 10).

Eén ``ImportRegel`` per onderdeelregel uit een CSV- of Excel-bestand, nog
met de materiaaltekst zoals die in het bestand stond: het koppelen aan een
materiaal uit de bibliotheek is een aparte stap (``koppelen.py``), zodat
het importscherm onbekende materialen kan laten kiezen. Maten staan hier in
de termen van het bestand (Lengte × Breedte); ``toepassen.py`` zet ze om
naar breedte × hoogte van een ``ModelOnderdeel``.

Een regel met een fout wordt niet weggegooid (Sven: liever laten zien wat
er mist en de gebruiker het laten invullen): ``problemen`` zegt per kolom
wat er mis is, ``waarden`` bewaart de tekst uit het bestand, en
``lezen.lees_regel`` leest de regel opnieuw nadat de gebruiker een waarde
heeft aangevuld.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from robocutter.modellen.models import Nerfrichting, Rand

__all__ = ["Ernst", "ImportMelding", "ImportRegel", "LeesResultaat"]


class Ernst(str, Enum):
    """Een fout houdt het importeren tegen tot hij is opgelost (of de
    regel wordt overgeslagen), een waarschuwing niet."""

    FOUT = "fout"
    WAARSCHUWING = "waarschuwing"


@dataclass(frozen=True)
class ImportMelding:
    tekst: str
    ernst: Ernst = Ernst.FOUT
    # Regelnummer zoals in het bestand (de kop is regel 1); None = het hele
    # bestand of meerdere regels.
    regelnummer: int | None = None
    # De kolom die aangevuld/aangepast moet worden, als dat er één is.
    kolom: str | None = None


@dataclass
class ImportRegel:
    regelnummer: int
    naam: str
    materiaal: str  # tekst uit het bestand: productcode of naam
    lengte: float | None  # mm, horizontaal (wordt ModelOnderdeel.breedte); None = leeg of fout
    breedte: float | None  # mm, verticaal (wordt ModelOnderdeel.hoogte); None = leeg (balk) of fout
    aantal: int = 1
    model: str = ""  # leeg = los onderdeel
    modelaantal: int = 1
    nerf: Nerfrichting = Nerfrichting.GEEN
    kantenband: frozenset[Rand] = field(default_factory=frozenset)
    fabriekskantenband: bool = False
    groep: str = ""
    volgorde: int | None = None
    # Tekst per kolom zoals in het bestand (of zoals de gebruiker hem
    # aanvulde), en per kolom wat er mis mee is.
    waarden: dict[str, str] = field(default_factory=dict)
    problemen: dict[str, str] = field(default_factory=dict)

    @property
    def is_compleet(self) -> bool:
        return not self.problemen


@dataclass
class LeesResultaat:
    regels: list[ImportRegel] = field(default_factory=list)
    # Meldingen over het hele bestand (lege kop, ontbrekende kolom,
    # onbekende kolom) en waarschuwingen; fouten per regel staan in
    # ``ImportRegel.problemen``.
    meldingen: list[ImportMelding] = field(default_factory=list)

    @property
    def heeft_fouten(self) -> bool:
        """Fout in het bestand zelf: dan is er niets in te lezen."""
        return any(m.ernst == Ernst.FOUT for m in self.meldingen)

    @property
    def onvolledig(self) -> list[ImportRegel]:
        return [r for r in self.regels if not r.is_compleet]
