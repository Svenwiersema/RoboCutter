"""Datamodel voor één project-record in de projectenbibliotheek.

Zie design/chapters/module-1-projectbeheer.md en
design/chapters/module-4-projecten.md: een project is in essentie een
model (onderdelen en/of modellen), aangevuld met klantgegevens en een
voortgangsstatus. Hergebruikt bewust ``ModelOnderdeel`` uit
``robocutter.modellen.models`` — zowel voor losse projectonderdelen als
voor de platgeslagen model-snapshots (``ProjectModelInstantie``) — in
plaats van een apart "ProjectOnderdeel"-type te verzinnen dat toch
dezelfde velden zou hebben.

Op Svens verzoek zijn klant/contactpersoon vrije tekstvelden: RoboCutter
onderhoudt zelf geen klantenbibliotheek (die hoofdstuk 1 wel noemt maar
die nog nergens ontworpen/gebouwd is) — dat wordt later opgelost met een
ERP-koppeling (hoofdstuk 9).

Bewust nog niet meegenomen (zie OVERDRACHT.md voor de afweging):
revisiegeschiedenis/sandboxes, "project opslaan als nieuw model", en
echte zaagplan-generatie (en de daarvan afgeleide reststukken-vrijgave
bij afronding).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from robocutter.modellen.models import ModelOnderdeel, Nerfrichting, Rand

__all__ = ["ProjectStatus", "ProjectModelInstantie", "Project", "ModelOnderdeel", "Nerfrichting", "Rand"]


class ProjectStatus(str, Enum):
    """De vier fasen uit hoofdstuk 4. Geen expliciete overgangsregels
    tussen fasen — vrij instelbaar."""

    WERKVOORBEREIDING = "Werkvoorbereiding"
    IN_PRODUCTIE = "In productie"
    INSTALLATIE = "Installatie"
    AFGEROND = "Afgerond"


@dataclass
class ProjectModelInstantie:
    """Eén model, als vaste kopie aan een project toegevoegd (hoofdstuk
    4). ``onderdelen`` is een platgeslagen snapshot — inclusief eventuele
    geneste submodellen (hoofdstuk 2), met aantallen al doorvermenigvuldigd
    via de nesting — dus een latere wijziging aan het bronmodel in de
    bibliotheek werkt hier niet automatisch door. ``model_id`` blijft
    bewaard zodat een expliciete "bijwerken naar laatste versie"-actie
    het bronmodel opnieuw kan platslaan."""

    id: str
    model_id: str
    model_naam: str  # snapshot van de naam, blijft zichtbaar ook als het bronmodel later verdwijnt
    aantal: int = 1
    onderdelen: list[ModelOnderdeel] = field(default_factory=list)


@dataclass
class Project:
    """Eén project-record (hoofdstuk 1/4): model + klantgegevens +
    status. Bevat modellen als vaste kopie (``modelinstanties``) en/of
    losse onderdelen die rechtstreeks aan het project zijn toegevoegd."""

    id: str
    naam: str
    klant: str
    contactpersoon: str = ""
    email: str = ""
    telefoon: str = ""
    opdrachtnummer: str = ""
    startdatum: date | None = None
    opleverdatum: date | None = None
    status: ProjectStatus = ProjectStatus.WERKVOORBEREIDING
    gearchiveerd: bool = False
    modelinstanties: list[ProjectModelInstantie] = field(default_factory=list)
    losse_onderdelen: list[ModelOnderdeel] = field(default_factory=list)
