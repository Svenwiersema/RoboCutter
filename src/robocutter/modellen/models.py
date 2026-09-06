"""Datamodel voor één model-record in de modellenbibliotheek.

Zie design/chapters/module-2-modellen.md: een model bestaat uit
onderdelen en/of andere modellen (nesting — dit is ook waar een "kast"
onder valt), met een vrije mappenstructuur + tags voor zoeken/
filteren. Op Svens verzoek kiest elk onderdeel zijn eigen materiaal
(``materiaal_id``, zelfde referentiepatroon als
``reststukken.models.Reststuk``) in plaats van één materiaalkeuze voor
het hele model.

Dit is bewust een los model van ``robocutter.optimalisatie.models``
(dat een lean, technisch model is dat de optimalisatie-motor nodig
heeft) — zelfde reden als waarom ``materialen.models.Materiaal`` los
staat van ``optimalisatie.models.Materiaal``. Een bibliotheek-
``ModelOnderdeel`` draagt metadata (naam, materiaalkeuze) die de
optimizer niet gebruikt; bij het genereren van een zaagplan wordt dit
omgezet naar het lean ``optimalisatie.models.Onderdeel``.

Bewust nog niet meegenomen (zie OVERDRACHT.md voor de afweging):
archiveren/verwijderworkflow zoals bij Materialen, revisiegeschiedenis,
en een thumbnail/afbeelding.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from robocutter.optimalisatie.models import Nerfrichting, Rand

__all__ = ["ModelOnderdeel", "SubModelVerwijzing", "Model", "Nerfrichting", "Rand"]


@dataclass
class ModelOnderdeel:
    """Eén te zagen onderdeel binnen een model. Kiest zijn eigen
    materiaal (via ``materiaal_id``), zodat een model gemengde
    materialen kan bevatten (bv. kastromp in spaanplaat, deurtjes in
    mdf)."""

    id: str
    naam: str
    materiaal_id: str
    breedte: float = 0.0  # mm
    hoogte: float = 0.0  # mm
    aantal: int = 1
    nerfrichting_vereist: Nerfrichting = Nerfrichting.GEEN
    kantenband_randen: frozenset[Rand] = field(default_factory=frozenset)
    fabriekskantenband_vereist: bool = False
    # Hoofdstuk 5: een "groep" is een vaste set onderdelen (zelfde
    # groep_id) die niet los van elkaar roteren en als één blok
    # verticaal gestapeld blijven, in de volgorde van groep_volgorde.
    # Zelfde velden/semantiek als
    # ``optimalisatie.models.Onderdeel.groep_id``/``groep_volgorde``.
    groep_id: str | None = None
    groep_volgorde: int | None = None


@dataclass
class SubModelVerwijzing:
    """Eén verwijzing naar een ander model binnen dit model (nesting),
    met het aantal keer dat dat submodel hierin voorkomt."""

    model_id: str
    aantal: int = 1


@dataclass
class Model:
    """Eén model-record uit de modellenbibliotheek (hoofdstuk 2): een
    herbruikbaar, zelfstandig ontwerp opgebouwd uit onderdelen en/of
    andere modellen."""

    id: str
    naam: str
    omschrijving: str = ""
    map: str = ""  # vrije mappenstructuur, bv. "Keukens/Onderkasten"
    tags: tuple[str, ...] = ()
    onderdelen: list[ModelOnderdeel] = field(default_factory=list)
    submodellen: list[SubModelVerwijzing] = field(default_factory=list)
