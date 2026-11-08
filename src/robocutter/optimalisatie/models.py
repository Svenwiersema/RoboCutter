"""Datamodellen voor de zaagplan-optimalisatie-motor.

Zie design/chapters/05-zaagplan-optimalisatie.md en
design/chapters/module-3-materialen.md voor de volledige achtergrond
en besluitvorming achter deze velden.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Nerfrichting(str, Enum):
    """Drie mogelijke waarden, zoals vastgesteld in hoofdstuk 5."""

    LANGE_ZIJDE = "lange_zijde"
    KORTE_ZIJDE = "korte_zijde"
    GEEN = "geen"


class Rand(str, Enum):
    """Een rand van een rechthoekige plaat of onderdeel."""

    BOVEN = "boven"
    ONDER = "onder"
    LINKS = "links"
    RECHTS = "rechts"


@dataclass
class Materiaal:
    """Eén (voorraad)plaat van een materiaal, met de instellingen uit
    Module 3 die de optimalisatie beïnvloeden.

    ``nerfrichting`` is de nerf van de plaat zelf (Sven, 2026-11-08: "je
    moet bij materiaal kunnen kiezen of de nerf over lengte of breedte
    loopt"): ``LANGE_ZIJDE`` = over de lengte (x-as / ``lengte``),
    ``KORTE_ZIJDE`` = over de breedte (y-as), ``GEEN`` = geen nerf, dan
    vervalt de nerf-eis van een onderdeel (zie
    ``engine._onderdelen_voor_plaatnerf``). Een onderdeel met
    ``nerfrichting_vereist=LANGE_ZIJDE`` ligt met zijn langste zijde
    langs die plaatnerf, ``KORTE_ZIJDE`` juist loodrecht daarop.

    ``is_balk``: lengtemateriaal (Sven: "balken moet heel simpel zijn die
    kan je maar op 1 manier zagen") — alleen afkorten, zie
    ``engine._pak_balk``. ``lengte`` is dan de balklengte, ``breedte`` de
    breedte van de doorsnede.
    """

    naam: str
    lengte: float  # mm, x-as
    breedte: float  # mm, y-as
    dikte: float = 18.0
    kerf: float = 4.0
    nerfrichting: Nerfrichting = Nerfrichting.LANGE_ZIJDE
    randafzaag_marge: float = 0.0
    randafzaag_randen: frozenset[Rand] = field(default_factory=frozenset)
    min_reststukgrootte: float = 0.0
    fabriekskantenband_randen: frozenset[Rand] = field(default_factory=frozenset)
    is_balk: bool = False


@dataclass
class Onderdeel:
    """Eén te zagen onderdeel (vóór vermenigvuldiging met ``aantal``)."""

    id: str
    breedte: float  # mm, gewenste breedte (x-richting bij niet-geroteerd)
    hoogte: float  # mm, gewenste hoogte (y-richting bij niet-geroteerd)
    aantal: int = 1
    nerfrichting_vereist: Nerfrichting = Nerfrichting.GEEN
    kantenband_randen: frozenset[Rand] = field(default_factory=frozenset)
    fabriekskantenband_vereist: bool = False
    groep_id: str | None = None
    groep_volgorde: int | None = None

    def mag_roteren(self) -> bool:
        return self.nerfrichting_vereist == Nerfrichting.GEEN


@dataclass
class Plaatsing:
    """Het resultaat: waar één stuk van een onderdeel op de plaat ligt."""

    onderdeel_id: str
    instantie: int  # 1e, 2e, ... exemplaar van dit onderdeel-id
    x: float
    y: float
    breedte: float
    hoogte: float
    geroteerd: bool


@dataclass
class Reststuk:
    x: float
    y: float
    breedte: float
    hoogte: float

    @property
    def oppervlak(self) -> float:
        return self.breedte * self.hoogte


@dataclass
class Zaagsnede:
    """Eén volledige zaagbeweging (kan meerdere onderdelen tegelijk
    scheiden — zie de nummeringsregel in hoofdstuk 5)."""

    volgnummer: int
    richting: str  # "horizontaal" of "verticaal"
    positie: float  # x (verticale snede) of y (horizontale snede)
    start: float
    einde: float


@dataclass
class ZaagplanResultaat:
    materiaal: Materiaal
    strategie: str
    plaatsingen: list[Plaatsing] = field(default_factory=list)
    reststukken: list[Reststuk] = field(default_factory=list)
    afval_oppervlak: float = 0.0
    zaagvolgorde: list[Zaagsnede] = field(default_factory=list)
    niet_geplaatst: list[str] = field(default_factory=list)
    niet_geplaatst_redenen: dict[str, str] = field(default_factory=dict)

    @property
    def benuttingspercentage(self) -> float:
        plaat_opp = self.materiaal.lengte * self.materiaal.breedte
        if plaat_opp <= 0:
            return 0.0
        gebruikt = sum(p.breedte * p.hoogte for p in self.plaatsingen)
        return round(100.0 * gebruikt / plaat_opp, 1)
