"""Labelgeneratie voor een project (hoofdstuk 6 — Labels &
identificatie): bouwt één ``OnderdeelLabel`` per fysiek geplaatst
onderdeel-exemplaar uit een gegenereerd zaagplan (module 1/4, zie
``zaagplannen.py``).

Daarnaast één ``ReststukLabel`` per projectreststuk dat op Bewaren staat
(``genereer_reststuk_labels``, zie ``project_reststukken.py``) — zonder
projectnummer (hoofdstuk 6: het stuk hoort na vrijgeven niet meer bij het
project). De scancode ``RC:reststuk:<id>`` blijft na vrijgeven geldig:
het reststuk houdt in de bibliotheek hetzelfde id.

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

from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.modellen.models import Nerfrichting, Rand
from robocutter.projecten.models import Project
from robocutter.projecten.project_reststukken import ProjectReststuk, ProjectReststukStatus
from robocutter.projecten.zaagplannen import PlaatZaagplan

from robocutter.reststukken.models import Reststuk

__all__ = [
    "OnderdeelLabel",
    "ReststukLabel",
    "genereer_bibliotheek_reststuk_labels",
    "genereer_labels_voor_project",
    "genereer_reststuk_labels",
]


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


@dataclass
class ReststukLabel:
    """Eén label voor een reststuk dat bewaard wordt. Lengte loopt langs de
    lengte-as van de plaat, dus langs de nerf als het materiaal er een heeft
    (zie de nerf-aanname in ``engine.py``)."""

    scancode_waarde: str
    reststuk_id: str
    code: str  # "R2" in een project, het bibliotheeknummer ("3F9A21C0") daarbuiten
    materiaal_naam: str
    lengte: float  # mm, huidige (eventueel aangepaste) maat
    breedte: float  # mm
    fabriekskantenband_randen: frozenset[Rand]
    nerf_langs_lengte: bool

    @property
    def afmeting_tekst(self) -> str:
        return f"{self.lengte:g} × {self.breedte:g} mm"


def genereer_reststuk_labels(items: list[ProjectReststuk], materialen: MaterialenBibliotheek) -> list[ReststukLabel]:
    """Eén label per reststuk in ``items`` dat op Bewaren staat; hergebruikte
    en afgeschreven stukken gaan het magazijn niet in en krijgen er geen."""

    labels: list[ReststukLabel] = []
    for item in items:
        if item.status != ProjectReststukStatus.BEWAREN:
            continue
        try:
            materiaal = materialen.ophalen(item.materiaal_id)
            materiaal_naam, nerf = materiaal.naam, materiaal.nerfrichting != Nerfrichting.GEEN
        except KeyError:
            materiaal_naam, nerf = "onbekend materiaal", False
        labels.append(
            ReststukLabel(
                scancode_waarde=f"RC:reststuk:{item.id}",
                reststuk_id=item.id,
                code=item.code,
                materiaal_naam=materiaal_naam,
                lengte=item.lengte,
                breedte=item.breedte,
                fabriekskantenband_randen=item.fabriekskantenband_randen,
                nerf_langs_lengte=nerf,
            )
        )
    return labels


def genereer_bibliotheek_reststuk_labels(
    reststukken: list[Reststuk], materialen: MaterialenBibliotheek
) -> list[ReststukLabel]:
    """Labels voor reststukken uit de Reststukkenbibliotheek (los opnieuw
    printen). De projectcode R2 bestaat daar niet meer: de naam wordt
    "Reststuk" + het vaste nummer uit de scancode, zodat je het stuk ook
    zonder scanner kunt opzoeken."""

    labels: list[ReststukLabel] = []
    for r in reststukken:
        try:
            materiaal = materialen.ophalen(r.materiaal_id)
            materiaal_naam, nerf = materiaal.naam, materiaal.nerfrichting != Nerfrichting.GEEN
        except KeyError:
            materiaal_naam, nerf = "onbekend materiaal", False
        labels.append(
            ReststukLabel(
                scancode_waarde=f"RC:reststuk:{r.id}",
                reststuk_id=r.id,
                code=r.id.upper(),
                materiaal_naam=materiaal_naam,
                lengte=r.lengte,
                breedte=r.breedte,
                fabriekskantenband_randen=r.fabriekskantenband_randen,
                nerf_langs_lengte=nerf,
            )
        )
    return labels
