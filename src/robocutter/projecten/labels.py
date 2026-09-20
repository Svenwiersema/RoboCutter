"""Labelgeneratie voor een project (hoofdstuk 6 — Labels &
identificatie): bouwt één ``OnderdeelLabel`` per fysiek geplaatst
onderdeel-exemplaar uit een gegenereerd zaagplan (module 1/4, zie
``zaagplannen.py``).

Op Svens verzoek is dit v1 bewust beperkt tot onderdeel-labels vanuit
een projectzaagplan — reststuk-labels (vanuit de Reststukkenbibliotheek,
zonder projectnummer, zie hoofdstuk 6) zijn een aparte, latere stap.

Net als ``zaagplannen.py``/``zaagplannen_opslag.py`` is dit afgeleide,
herberekenbare data (geen eigen bibliotheek/CRUD): labels volgen simpelweg
uit het laatst gegenereerde zaagplan van een project, en worden opnieuw
opgebouwd zodra dat zaagplan opnieuw gegenereerd wordt.

De scancode-waarde codeert alleen een uniek record-ID (geen URL/online
schema — logisch voor een offline, single-user app zoals RoboCutter nu
is); hoofdstuk 6 laat de precieze scancode-inhoud bewust open ("verder
uit te werken bij hoofdstuk 8"), en hoofdstuk 8 zelf noemt dit onderwerp
nergens expliciet — dit is dus de eerste concrete invulling ervan.
"""

from __future__ import annotations

from dataclasses import dataclass

from robocutter.modellen.models import Nerfrichting, Rand
from robocutter.projecten.models import Project
from robocutter.projecten.zaagplannen import PlaatZaagplan

__all__ = ["OnderdeelLabel", "genereer_labels_voor_project"]


@dataclass
class OnderdeelLabel:
    """Eén label voor één fysiek geplaatst onderdeel-exemplaar. De
    optionele velden (scancode/kantenband-indicatie/nerfrichting-pijl)
    worden altijd meegegeven — welke daarvan echt op het label komen is
    een instelling die de labelrenderer (``robocutter.ui.label_pdf``)
    zelf naleest, niet iets wat hier al bepaald wordt."""

    scancode_waarde: str
    onderdeel_naam: str
    materiaal_naam: str
    projectnummer: str
    breedte: float  # mm, zoals daadwerkelijk gezaagd (na eventuele rotatie)
    hoogte: float  # mm
    kantenband_randen: frozenset[Rand]
    nerfrichting_vereist: Nerfrichting
    fabriekskantenband_vereist: bool

    @property
    def afmeting_tekst(self) -> str:
        return f"{self.breedte:g} × {self.hoogte:g} mm"


def genereer_labels_voor_project(project: Project, plannen: list[PlaatZaagplan]) -> list[OnderdeelLabel]:
    """Eén label per ``Plaatsing`` in ``plannen`` (het resultaat van
    ``zaagplannen.genereer_zaagplannen_voor_project``) — dus inclusief
    dubbele exemplaren van hetzelfde onderdeel, want elk exemplaar wordt
    fysiek apart uitgezaagd en moet dus ook een eigen label krijgen."""

    labels: list[OnderdeelLabel] = []
    for plan in plannen:
        for plaatsing in plan.resultaat.plaatsingen:
            info = plan.onderdeel_info.get(plaatsing.onderdeel_id)
            labels.append(
                OnderdeelLabel(
                    scancode_waarde=(
                        f"RC:onderdeel:{project.id}:{plan.materiaal_id}:"
                        f"{plaatsing.onderdeel_id}:{plaatsing.instantie}"
                    ),
                    onderdeel_naam=info.naam if info else plaatsing.onderdeel_id,
                    materiaal_naam=plan.materiaal_naam,
                    projectnummer=project.opdrachtnummer,
                    breedte=plaatsing.breedte,
                    hoogte=plaatsing.hoogte,
                    kantenband_randen=info.kantenband_randen if info else frozenset(),
                    nerfrichting_vereist=info.nerfrichting_vereist if info else Nerfrichting.GEEN,
                    fabriekskantenband_vereist=info.fabriekskantenband_vereist if info else False,
                )
            )
    return labels
