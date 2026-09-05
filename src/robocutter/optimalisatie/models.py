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

    Aanname (expliciet, ter bevestiging): de nerf van de plaat zelf
    loopt altijd langs de lengte-as (x-as / ``lengte``). Een
    onderdeel met ``nerfrichting_vereist=LANGE_ZIJDE`` moet dus met
    zijn langste zijde evenwijdig aan de x-as geplaatst worden, en
    ``KORTE_ZIJDE`` juist loodrecht daarop. Dit is de gebruikelijke
    conventie (nerf loopt over de lange kant van een plaat) maar is
    niet letterlijk zo benoemd in hoofdstuk 5 — graag checken of dit
    klopt met de praktijk.
    """

    naam: str
    lengte: float  # mm, x-as
    breedte: float  # mm, y-as
    dikte: float = 18.0
    kerf: float = 4.0
    nerfrichting_aanwezig: bool = False
    randafzaag_marge: float = 0.0
    randafzaag_randen: frozenset[Rand] = field(default_factory=frozenset)
    min_reststukgrootte: float = 0.0
    fabriekskantenband_randen: frozenset[Rand] = field(default_factory=frozenset)


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

    @property
    def benuttingspercentage(self) -> float:
        plaat_opp = self.materiaal.lengte * self.materiaal.breedte
        if plaat_opp <= 0:
            return 0.0
        gebruikt = sum(p.breedte * p.hoogte for p in self.plaatsingen)
        return round(100.0 * gebruikt / plaat_opp, 1)
