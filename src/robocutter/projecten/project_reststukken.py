"""Reststukken van één project: een tijdelijke, aan het project gekoppelde
reststukkenbibliotheek (module 1/4: reststukken pas ná afronding naar de
gedeelde Reststukkenbibliotheek).

Sven: "restukken lijst in een project is eigenlijk een tijdelijke
bibliotheek gekoppeld aan het project en die nog niet in het algemene
bibliotheek staat zodat je nog kan aanpassen of hergebruiken of
wegschrijven, want een project verloopt nooit perfect". Mockup:
``design/assets/mockups/project-reststukken-concept.html``.

- Gevuld uit het laatst gegenereerde zaagplan (``overnemen_uit_zaagplan``,
  één record per ``Reststuk`` per plaat). Opnieuw genereren vervangt de
  reststukken uit het zaagplan; handmatig toegevoegde blijven staan.
- Per reststuk: Bewaren / Hergebruikt in project / Afgeschreven, en de
  afmeting is aan te passen (de oorspronkelijke maat uit het zaagplan
  blijft bewaard). Er is bewust geen verwijderen — afschrijven is
  omkeerbaar (zie de "verwijderen nooit direct opslaan"-afspraak).
- ``vrijgeven`` kan alleen als het project Afgerond is: alleen de
  Bewaren-stukken gaan als ``Reststuk`` de Reststukkenbibliotheek in
  (herkomst = projectnaam). Daarna is de lijst alleen nog ter informatie.

Lengte/breedte volgen de plaat: lengte langs de lengte-as van het
materiaal (x in het zaagplan, ook de nerfrichting), breedte langs y.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.optimalisatie.models import Rand
from robocutter.projecten import project_reststukken_opslag as opslag
from robocutter.projecten.models import Project, ProjectStatus
from robocutter.projecten.zaagplannen import PlaatZaagplan
from robocutter.reststukken.bibliotheek import ReststukkenBibliotheek
from robocutter.reststukken.models import Reststuk

__all__ = [
    "ProjectReststukStatus",
    "ProjectReststukBron",
    "ProjectReststuk",
    "AlVrijgegevenError",
    "ProjectNietAfgerondError",
    "valideer",
    "ProjectReststukkenBibliotheek",
]


class ProjectReststukStatus(str, Enum):
    BEWAREN = "bewaren"
    HERGEBRUIKT = "hergebruikt"
    AFGESCHREVEN = "afgeschreven"


class ProjectReststukBron(str, Enum):
    ZAAGPLAN = "zaagplan"
    HANDMATIG = "handmatig"


@dataclass
class ProjectReststuk:
    id: str
    project_id: str
    volgnummer: int  # getoond als "R<volgnummer>"
    materiaal_id: str
    lengte: float  # mm, huidige (eventueel aangepaste) maat
    breedte: float  # mm
    bron: ProjectReststukBron = ProjectReststukBron.HANDMATIG
    status: ProjectReststukStatus = ProjectReststukStatus.BEWAREN
    # Alleen bij bron ZAAGPLAN: waar het stuk op welke plaat zat (voor de
    # kleine plaattekening) en de maat zoals het zaagplan hem opleverde.
    plaat_nummer: int | None = None
    platen_totaal: int | None = None
    plaat_lengte: float = 0.0
    plaat_breedte: float = 0.0
    x: float = 0.0
    y: float = 0.0
    oorspronkelijke_lengte: float | None = None
    oorspronkelijke_breedte: float | None = None
    vrijgegeven_op: date | None = None
    # Het zaagplan zaagde dit stuk af van een reststuk uit de bibliotheek
    # (i.p.v. een volle plaat); plaat_nummer telt dan de reststukken.
    uit_bibliotheek_reststuk: bool = False
    # Randen die aan een fabriekskantenband-rand van de plaat grenzen (zie
    # _fabrieksranden_van); gaan bij vrijgeven mee naar de bibliotheek.
    fabriekskantenband_randen: frozenset[Rand] = field(default_factory=frozenset)

    @property
    def code(self) -> str:
        return f"R{self.volgnummer}"

    @property
    def is_aangepast(self) -> bool:
        return self.oorspronkelijke_lengte is not None and (
            self.lengte != self.oorspronkelijke_lengte or self.breedte != self.oorspronkelijke_breedte
        )


class AlVrijgegevenError(Exception):
    """De reststukken van dit project zijn al naar de bibliotheek
    vrijgegeven; de projectlijst is daarna alleen nog ter informatie."""


class ProjectNietAfgerondError(Exception):
    """Vrijgeven kan pas als het project de status Afgerond heeft."""


def _fabrieksranden_van(x: float, y: float, lengte: float, breedte: float, plaat_lengte: float,
                        plaat_breedte: float, plaat_randen: frozenset[Rand]) -> frozenset[Rand]:
    """Welke randen van een reststuk op (x, y) nog fabriekskantenband
    hebben: die op een fabrieksrand van de plaat liggen. Fabrieksranden
    worden nooit afgezaagd (zie ``engine._werkgebied``), dus een reststuk
    dat tot aan zo'n plaatrand loopt, heeft die rand nog."""

    marge = 0.5  # mm, afronding
    randen = set()
    if Rand.LINKS in plaat_randen and x <= marge:
        randen.add(Rand.LINKS)
    if Rand.RECHTS in plaat_randen and x + lengte >= plaat_lengte - marge:
        randen.add(Rand.RECHTS)
    if Rand.ONDER in plaat_randen and y <= marge:
        randen.add(Rand.ONDER)
    if Rand.BOVEN in plaat_randen and y + breedte >= plaat_breedte - marge:
        randen.add(Rand.BOVEN)
    return frozenset(randen)


def valideer(reststuk: ProjectReststuk, materialen: MaterialenBibliotheek) -> list[str]:
    fouten: list[str] = []
    if not reststuk.materiaal_id:
        fouten.append("Materiaal is verplicht.")
    else:
        try:
            materialen.ophalen(reststuk.materiaal_id)
        except KeyError:
            fouten.append("Gekoppeld materiaal bestaat niet (meer).")
    if reststuk.lengte <= 0:
        fouten.append("Lengte moet groter dan 0 zijn.")
    if reststuk.breedte <= 0:
        fouten.append("Breedte moet groter dan 0 zijn.")
    return fouten


class ProjectReststukkenBibliotheek:
    def __init__(
        self,
        materialen: MaterialenBibliotheek,
        reststukken: ReststukkenBibliotheek,
        db_verbinding: sqlite3.Connection | None = None,
    ) -> None:
        self._materialen = materialen
        self._reststukken = reststukken
        self._db = db_verbinding
        self._items: dict[str, ProjectReststuk] = {}
        if self._db is not None:
            for item in opslag.laad_alles(self._db):
                self._items[item.id] = item

    @property
    def reststukken(self) -> ReststukkenBibliotheek:
        """De gedeelde Reststukkenbibliotheek (ook nodig voor het
        reserveren van reststukken bij het genereren van een zaagplan)."""
        return self._reststukken

    # -- lezen ---------------------------------------------------------
    def lijst(self, project_id: str) -> list[ProjectReststuk]:
        return sorted(
            (r for r in self._items.values() if r.project_id == project_id),
            key=lambda r: r.volgnummer,
        )

    def ophalen(self, reststuk_id: str) -> ProjectReststuk:
        return self._items[reststuk_id]

    def is_vrijgegeven(self, project_id: str) -> bool:
        return any(r.vrijgegeven_op is not None for r in self.lijst(project_id))

    def vrijgegeven_op(self, project_id: str) -> date | None:
        return next((r.vrijgegeven_op for r in self.lijst(project_id) if r.vrijgegeven_op is not None), None)

    # -- vullen --------------------------------------------------------
    def overnemen_uit_zaagplan(self, project_id: str, plannen: list[PlaatZaagplan]) -> list[ProjectReststuk]:
        """Vervangt de reststukken uit het (vorige) zaagplan door die uit
        ``plannen``; handmatig toegevoegde blijven staan en schuiven in de
        nummering achter de zaagplan-stukken."""

        self._controleer_niet_vrijgegeven(project_id)
        oud = self.lijst(project_id)
        for r in oud:
            if r.bron == ProjectReststukBron.ZAAGPLAN:
                self._verwijder(r.id)
        volgnummer = 1
        for plan in plannen:
            mat = plan.resultaat.materiaal
            for rest in plan.resultaat.reststukken:
                item = ProjectReststuk(
                    id=uuid.uuid4().hex[:8],
                    project_id=project_id,
                    volgnummer=volgnummer,
                    materiaal_id=plan.materiaal_id,
                    lengte=rest.breedte,
                    breedte=rest.hoogte,
                    bron=ProjectReststukBron.ZAAGPLAN,
                    plaat_nummer=plan.plaat_nummer,
                    platen_totaal=plan.platen_totaal,
                    plaat_lengte=mat.lengte,
                    plaat_breedte=mat.breedte,
                    x=rest.x,
                    y=rest.y,
                    oorspronkelijke_lengte=rest.breedte,
                    oorspronkelijke_breedte=rest.hoogte,
                    uit_bibliotheek_reststuk=plan.is_reststuk,
                    fabriekskantenband_randen=_fabrieksranden_van(
                        rest.x, rest.y, rest.breedte, rest.hoogte, mat.lengte, mat.breedte,
                        mat.fabriekskantenband_randen,
                    ),
                )
                self._items[item.id] = item
                self._persisteer(item)
                volgnummer += 1
        for r in oud:
            if r.bron == ProjectReststukBron.HANDMATIG:
                r.volgnummer = volgnummer
                self._persisteer(r)
                volgnummer += 1
        return self.lijst(project_id)

    def toevoegen_handmatig(self, project_id: str, materiaal_id: str, lengte: float, breedte: float) -> ProjectReststuk:
        self._controleer_niet_vrijgegeven(project_id)
        bestaand = self.lijst(project_id)
        item = ProjectReststuk(
            id=uuid.uuid4().hex[:8],
            project_id=project_id,
            volgnummer=max((r.volgnummer for r in bestaand), default=0) + 1,
            materiaal_id=materiaal_id,
            lengte=lengte,
            breedte=breedte,
            bron=ProjectReststukBron.HANDMATIG,
        )
        fouten = valideer(item, self._materialen)
        if fouten:
            raise ValueError("; ".join(fouten))
        self._items[item.id] = item
        self._persisteer(item)
        return item

    # -- wijzigen ------------------------------------------------------
    def zet_status(self, reststuk_id: str, status: ProjectReststukStatus) -> ProjectReststuk:
        item = self._items[reststuk_id]
        self._controleer_niet_vrijgegeven(item.project_id)
        item.status = status
        self._persisteer(item)
        return item

    def wijzig_afmeting(self, reststuk_id: str, lengte: float, breedte: float) -> ProjectReststuk:
        item = self._items[reststuk_id]
        self._controleer_niet_vrijgegeven(item.project_id)
        oude = (item.lengte, item.breedte)
        item.lengte, item.breedte = lengte, breedte
        fouten = valideer(item, self._materialen)
        if fouten:
            item.lengte, item.breedte = oude
            raise ValueError("; ".join(fouten))
        self._persisteer(item)
        return item

    def vrijgeven(self, project: Project, op: date | None = None) -> list[Reststuk]:
        """Zet alle Bewaren-stukken van ``project`` als nieuw, beschikbaar
        ``Reststuk`` in de Reststukkenbibliotheek en sluit de projectlijst af."""

        if project.status != ProjectStatus.AFGEROND:
            raise ProjectNietAfgerondError("Reststukken vrijgeven kan pas als het project Afgerond is.")
        self._controleer_niet_vrijgegeven(project.id)
        items = self.lijst(project.id)
        nieuw: list[Reststuk] = []
        for item in items:
            if item.status == ProjectReststukStatus.BEWAREN:
                nieuw.append(
                    self._reststukken.toevoegen(
                        Reststuk(
                            id="",
                            materiaal_id=item.materiaal_id,
                            lengte=item.lengte,
                            breedte=item.breedte,
                            herkomst_project=project.naam,
                            fabriekskantenband_randen=item.fabriekskantenband_randen,
                        )
                    )
                )
        datum = op or date.today()
        for item in items:
            item.vrijgegeven_op = datum
            self._persisteer(item)
        return nieuw

    def verwijder_project(self, project_id: str) -> None:
        for r in self.lijst(project_id):
            self._verwijder(r.id)

    # -- intern --------------------------------------------------------
    def _controleer_niet_vrijgegeven(self, project_id: str) -> None:
        if self.is_vrijgegeven(project_id):
            raise AlVrijgegevenError("De reststukken van dit project zijn al vrijgegeven naar de bibliotheek.")

    def _persisteer(self, item: ProjectReststuk) -> None:
        if self._db is not None:
            opslag.opslaan(self._db, item)

    def _verwijder(self, reststuk_id: str) -> None:
        del self._items[reststuk_id]
        if self._db is not None:
            opslag.verwijderen(self._db, reststuk_id)
