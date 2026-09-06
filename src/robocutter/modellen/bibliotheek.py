"""Modellenbibliotheek: validatie + de nesting-regels uit hoofdstuk 2,
met optionele SQLite-opslag.

Een model verwijst voor elk onderdeel naar een bestaand materiaal uit
de materialenbibliotheek (``materiaal_id``, op Svens verzoek per
onderdeel i.p.v. één materiaalkeuze voor het hele model) — vandaar dat
deze klasse een ``MaterialenBibliotheek`` nodig heeft. Een model mag
ook andere modellen bevatten (nesting, hoofdstuk 2: "dit is ook waar
een kast onder valt"), dus deze klasse valideert ook tegen zichzelf: elk
submodel moet bestaan, en een model mag zichzelf niet direct of
indirect bevatten (cirkelverwijzing).
"""

from __future__ import annotations

import sqlite3
import uuid

from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.materialen.models import Materiaal
from robocutter.modellen import opslag
from robocutter.modellen.models import Model, ModelOnderdeel, SubModelVerwijzing


class OnbekendMateriaalError(Exception):
    """Het materiaal waar een onderdeel naar verwijst bestaat niet (meer)."""


class OnbekendModelError(Exception):
    """Het model waar een submodel-verwijzing naar verwijst bestaat niet (meer)."""


class ModelInGebruikError(Exception):
    """Dit model wordt nog als submodel gebruikt in een ander model en
    kan daarom niet verwijderd worden."""


def _bevat_cirkelverwijzing(model: Model, modellen: "ModellenBibliotheek") -> bool:
    """Loopt de submodel-keten van ``model`` af (via de al opgeslagen
    modellen in de bibliotheek) en kijkt of die ooit weer bij
    ``model.id`` zelf uitkomt."""

    bezocht: set[str] = set()
    te_bezoeken = [s.model_id for s in model.submodellen if s.model_id]
    while te_bezoeken:
        model_id = te_bezoeken.pop()
        if model_id == model.id:
            return True
        if model_id in bezocht:
            continue
        bezocht.add(model_id)
        try:
            volgende = modellen.ophalen(model_id)
        except KeyError:
            continue
        te_bezoeken.extend(s.model_id for s in volgende.submodellen if s.model_id)
    return False


def valideer(model: Model, materialen: MaterialenBibliotheek, modellen: "ModellenBibliotheek") -> list[str]:
    """Live validatie: geeft een lijst foutmeldingen terug (leeg =
    geldig). Bedoeld om direct in het paneel te tonen, geen pop-ups
    (zelfde principe als bij de materialen-/reststukkenbibliotheek)."""

    fouten: list[str] = []

    if not model.naam.strip():
        fouten.append("Naam is verplicht.")

    for onderdeel in model.onderdelen:
        label = onderdeel.naam or "(naamloos onderdeel)"
        if onderdeel.breedte <= 0:
            fouten.append(f"Onderdeel '{label}': breedte moet groter dan 0 zijn.")
        if onderdeel.hoogte <= 0:
            fouten.append(f"Onderdeel '{label}': hoogte moet groter dan 0 zijn.")
        if onderdeel.aantal < 1:
            fouten.append(f"Onderdeel '{label}': aantal moet minstens 1 zijn.")
        if not onderdeel.materiaal_id:
            fouten.append(f"Onderdeel '{label}': materiaal is verplicht.")
        else:
            try:
                materialen.ophalen(onderdeel.materiaal_id)
            except KeyError:
                fouten.append(f"Onderdeel '{label}': gekoppeld materiaal bestaat niet (meer).")

    for submodel in model.submodellen:
        if not submodel.model_id:
            fouten.append("Submodel-verwijzing: model is verplicht.")
            continue
        if submodel.aantal < 1:
            fouten.append("Submodel-verwijzing: aantal moet minstens 1 zijn.")
        try:
            modellen.ophalen(submodel.model_id)
        except KeyError:
            fouten.append(f"Submodel-verwijzing: model {submodel.model_id!r} bestaat niet (meer).")

    if model.id and _bevat_cirkelverwijzing(model, modellen):
        fouten.append("Dit model mag niet (indirect) zichzelf als submodel bevatten.")

    return fouten


def _model_matcht_term(model: Model, term: str) -> bool:
    tekstvelden = [model.naam, model.omschrijving, model.map, *model.tags]
    return any(term in veld.lower() for veld in tekstvelden)


class ModellenBibliotheek:
    """Houdt model-records bij en handhaaft de nesting-regels uit
    hoofdstuk 2 (geen cirkelverwijzingen, geen submodel-verwijderen
    zolang het nog ergens gebruikt wordt)."""

    def __init__(self, materialen: MaterialenBibliotheek, db_verbinding: sqlite3.Connection | None = None) -> None:
        self._materialen = materialen
        self._db = db_verbinding
        self._modellen: dict[str, Model] = {}
        if self._db is not None:
            for model in opslag.laad_alles(self._db):
                self._modellen[model.id] = model

    def toevoegen(self, model: Model) -> Model:
        fouten = valideer(model, self._materialen, self)
        if fouten:
            raise ValueError("; ".join(fouten))
        if not model.id:
            model.id = uuid.uuid4().hex[:8]
        self._modellen[model.id] = model
        self._persisteer(model)
        return model

    def bijwerken(self, model: Model) -> Model:
        if model.id not in self._modellen:
            raise KeyError(f"Onbekend model-id: {model.id!r}")
        fouten = valideer(model, self._materialen, self)
        if fouten:
            raise ValueError("; ".join(fouten))
        self._modellen[model.id] = model
        self._persisteer(model)
        return model

    def ophalen(self, model_id: str) -> Model:
        return self._modellen[model_id]

    def materiaal_van(self, onderdeel: ModelOnderdeel) -> Materiaal:
        try:
            return self._materialen.ophalen(onderdeel.materiaal_id)
        except KeyError as exc:
            raise OnbekendMateriaalError(
                f"Materiaal {onderdeel.materiaal_id!r} bestaat niet (meer)."
            ) from exc

    def submodel_van(self, verwijzing: SubModelVerwijzing) -> Model:
        try:
            return self._modellen[verwijzing.model_id]
        except KeyError as exc:
            raise OnbekendModelError(
                f"Model {verwijzing.model_id!r} bestaat niet (meer)."
            ) from exc

    def verwijderen(self, model_id: str) -> None:
        for ander in self._modellen.values():
            if ander.id == model_id:
                continue
            if any(s.model_id == model_id for s in ander.submodellen):
                raise ModelInGebruikError(
                    f"Dit model wordt nog gebruikt als submodel in '{ander.naam}' en kan niet verwijderd worden."
                )
        del self._modellen[model_id]
        if self._db is not None:
            opslag.verwijderen(self._db, model_id)

    def _persisteer(self, model: Model) -> None:
        if self._db is not None:
            opslag.opslaan(self._db, model)

    def lijst(self, zoekterm: str = "") -> list[Model]:
        resultaat = list(self._modellen.values())
        termen = zoekterm.lower().split()
        if termen:
            resultaat = [m for m in resultaat if all(_model_matcht_term(m, term) for term in termen)]
        return sorted(resultaat, key=lambda m: m.naam.lower())
