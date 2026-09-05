"""Placeholder-voorbeelddata voor de home pagina.

Module 1 (Projectbeheer) en Module 4 (Projecten) zijn ontwerpmatig
afgerond (zie ``design/chapters/``) maar hebben nog geen echte
database-backend. Deze module levert dezelfde voorbeeldprojecten als de
goedgekeurde HTML-conceptmockup, zodat de UI nu al getoond en getest kan
worden. Vervang dit door een echte query zodra Module 1/4 gebouwd is.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ProjectStatus(str, Enum):
    WERKVOORBEREIDING = "Werkvoorbereiding"
    IN_PRODUCTIE = "In productie"
    INSTALLATIE = "Installatie"
    AFGEROND = "Afgerond"


@dataclass(frozen=True)
class ProjectSummary:
    naam: str
    klant: str
    opdrachtnummer: str
    opleverdatum: str
    status: ProjectStatus
    modellen_compleet: int
    modellen_totaal: int
    ontbrekend_materiaal: str | None = None


VOORBEELD_PROJECTEN: list[ProjectSummary] = [
    ProjectSummary("Keuken Jansen", "fam. Jansen", "#2026-014", "8 sep 2026",
                    ProjectStatus.IN_PRODUCTIE, 6, 9),
    ProjectSummary("Badkamermeubel Bakker", "dhr. Bakker", "#2026-021", "29 sep 2026",
                    ProjectStatus.WERKVOORBEREIDING, 1, 3),
    ProjectSummary("Keuken De Vries", "fam. De Vries", "#2026-009", "11 sep 2026",
                    ProjectStatus.INSTALLATIE, 8, 8),
    ProjectSummary("Inbouwkast Willemsen", "fam. Willemsen", "#2026-017", "22 sep 2026",
                    ProjectStatus.IN_PRODUCTIE, 2, 4, "Eiken fineer 19mm"),
    ProjectSummary("Keuken Verhoeven", "fam. Verhoeven", "#2026-011", "15 sep 2026",
                    ProjectStatus.INSTALLATIE, 7, 7),
    ProjectSummary("Kantoorkast Smits", "Smits Advocatuur", "#2026-019", "3 okt 2026",
                    ProjectStatus.IN_PRODUCTIE, 3, 5, "MDF gegrond 12mm"),
]
