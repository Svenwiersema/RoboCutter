"""Projectenbibliotheek: validatie + het snapshot-mechanisme en de
archiveer-/verwijderworkflow uit hoofdstuk 1/4, met optionele
SQLite-opslag.

Een project verwijst voor elke model-instantie naar een bestaand model
uit de modellenbibliotheek (om er een platgeslagen kopie van te maken,
en om 'm later te kunnen bijwerken naar de laatste versie) en voor elk
los onderdeel naar een bestaand materiaal — vandaar dat deze klasse
zowel een ``ModellenBibliotheek`` als een ``MaterialenBibliotheek``
nodig heeft.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import replace

from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.modellen.bibliotheek import ModellenBibliotheek
from robocutter.modellen.models import Model, ModelOnderdeel
from robocutter.projecten import opslag
from robocutter.projecten.models import Project, ProjectModelInstantie, ProjectStatus


class OngeldigeStatusOvergangError(Exception):
    """Bijv. archiveren vanuit een project dat nog niet is afgerond."""


class OnbekendModelError(Exception):
    """Het model waarnaar een model-instantie verwijst bestaat niet (meer)."""


def _platslaan(model: Model, modellen: ModellenBibliotheek, vermenigvuldiger: int = 1) -> list[ModelOnderdeel]:
    """Zet een model (incl. eventuele geneste submodellen, hoofdstuk 2)
    om in één platte onderdelenlijst, met aantallen doorvermenigvuldigd
    via de nesting-aantallen. De kern van het snapshot-mechanisme uit
    hoofdstuk 4: het resultaat wordt één keer berekend en daarna
    losgekoppeld bewaard, niet steeds opnieuw uit de bibliotheek
    gelezen."""

    resultaat: list[ModelOnderdeel] = [replace(o, aantal=o.aantal * vermenigvuldiger) for o in model.onderdelen]
    for submodel in model.submodellen:
        submodel_model = modellen.ophalen(submodel.model_id)
        resultaat.extend(_platslaan(submodel_model, modellen, vermenigvuldiger * submodel.aantal))
    return resultaat


def valideer(project: Project, materialen: MaterialenBibliotheek) -> list[str]:
    """Live validatie: geeft een lijst foutmeldingen terug (leeg =
    geldig), geen pop-ups (zelfde principe als bij de andere
    bibliotheken). Model-snapshots (``modelinstanties``) worden niet
    opnieuw gevalideerd — ze waren geldig op het moment van toevoegen,
    dat is precies het punt van een vaste kopie (hoofdstuk 4)."""

    fouten: list[str] = []

    if not project.naam.strip():
        fouten.append("Naam is verplicht.")
    if not project.klant.strip():
        fouten.append("Klant is verplicht.")

    for onderdeel in project.losse_onderdelen:
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

    return fouten


def _project_matcht_term(project: Project, term: str) -> bool:
    tekstvelden = [project.naam, project.klant, project.contactpersoon, project.opdrachtnummer]
    return any(term in veld.lower() for veld in tekstvelden)


class ProjectenBibliotheek:
    """Houdt project-records bij: CRUD, het model-snapshot-mechanisme
    (toevoegen/bijwerken naar laatste versie), en de archiveer-
    workflow (alleen vanuit status Afgerond, zelfde patroon als
    Materialen)."""

    def __init__(
        self,
        modellen: ModellenBibliotheek,
        materialen: MaterialenBibliotheek,
        db_verbinding: sqlite3.Connection | None = None,
    ) -> None:
        self._modellen = modellen
        self._materialen = materialen
        self._db = db_verbinding
        self._projecten: dict[str, Project] = {}
        if self._db is not None:
            for project in opslag.laad_alles(self._db):
                self._projecten[project.id] = project

    def toevoegen(self, project: Project) -> Project:
        fouten = valideer(project, self._materialen)
        if fouten:
            raise ValueError("; ".join(fouten))
        if not project.id:
            project.id = uuid.uuid4().hex[:8]
        self._projecten[project.id] = project
        self._persisteer(project)
        return project

    def bijwerken(self, project: Project) -> Project:
        if project.id not in self._projecten:
            raise KeyError(f"Onbekend project-id: {project.id!r}")
        fouten = valideer(project, self._materialen)
        if fouten:
            raise ValueError("; ".join(fouten))
        self._projecten[project.id] = project
        self._persisteer(project)
        return project

    def ophalen(self, project_id: str) -> Project:
        return self._projecten[project_id]

    # ------------------------------------------------------------------
    # Samenstelling: modellen (snapshot) en losse onderdelen
    # ------------------------------------------------------------------
    def model_toevoegen(self, project_id: str, model_id: str, aantal: int = 1) -> Project:
        project = self._projecten[project_id]
        model = self._modellen.ophalen(model_id)
        instantie = ProjectModelInstantie(
            id=uuid.uuid4().hex[:8],
            model_id=model.id,
            model_naam=model.naam,
            aantal=aantal,
            onderdelen=_platslaan(model, self._modellen),
        )
        project.modelinstanties.append(instantie)
        self._persisteer(project)
        return project

    def model_bijwerken_naar_laatste_versie(self, project_id: str, instantie_id: str) -> Project:
        project = self._projecten[project_id]
        instantie = next((i for i in project.modelinstanties if i.id == instantie_id), None)
        if instantie is None:
            raise KeyError(f"Onbekende model-instantie: {instantie_id!r}")
        try:
            model = self._modellen.ophalen(instantie.model_id)
        except KeyError as exc:
            raise OnbekendModelError(
                f"Model {instantie.model_id!r} bestaat niet (meer) — kan niet bijgewerkt worden."
            ) from exc
        instantie.model_naam = model.naam
        instantie.onderdelen = _platslaan(model, self._modellen)
        self._persisteer(project)
        return project

    def model_instantie_verwijderen(self, project_id: str, instantie_id: str) -> Project:
        project = self._projecten[project_id]
        project.modelinstanties = [i for i in project.modelinstanties if i.id != instantie_id]
        self._persisteer(project)
        return project

    def model_onderdeel_materiaal_wijzigen(
        self, project_id: str, instantie_id: str, onderdeel_id: str, materiaal_id: str
    ) -> Project:
        """Wijzigt het materiaal van één onderdeel binnen een
        model-snapshot — bijv. dezelfde kast met hetzelfde
        corpusmateriaal maar andere frontjes, per project. Bewust de
        ENIGE toegestane wijziging op een snapshot-onderdeel (de rest —
        afmetingen, kantenband, nerf, groep — blijft ongewijzigd); voor
        al het andere is "bijwerken naar laatste versie" (opnieuw
        platslaan vanuit de bibliotheek) of het model verwijderen en
        opnieuw toevoegen de weg."""

        project = self._projecten[project_id]
        instantie = next((i for i in project.modelinstanties if i.id == instantie_id), None)
        if instantie is None:
            raise KeyError(f"Onbekende model-instantie: {instantie_id!r}")
        index = next((i for i, o in enumerate(instantie.onderdelen) if o.id == onderdeel_id), None)
        if index is None:
            raise KeyError(f"Onbekend onderdeel: {onderdeel_id!r}")
        try:
            self._materialen.ophalen(materiaal_id)
        except KeyError:
            raise ValueError(f"Materiaal {materiaal_id!r} bestaat niet.") from None
        instantie.onderdelen[index] = replace(instantie.onderdelen[index], materiaal_id=materiaal_id)
        self._persisteer(project)
        return project

    def los_onderdeel_toevoegen(self, project_id: str, onderdeel: ModelOnderdeel) -> Project:
        # Anders dan een model-instantie (een vaste snapshot, al gevalideerd op het
        # moment van toevoegen aan het model) is een los onderdeel live invoer vanuit
        # het project zelf — dus wél door valideer() heen, net als toevoegen()/bijwerken().
        project = self._projecten[project_id]
        if not onderdeel.id:
            onderdeel.id = uuid.uuid4().hex[:8]
        project.losse_onderdelen.append(onderdeel)
        fouten = valideer(project, self._materialen)
        if fouten:
            project.losse_onderdelen.remove(onderdeel)
            raise ValueError("; ".join(fouten))
        self._persisteer(project)
        return project

    def los_onderdeel_bijwerken(self, project_id: str, onderdeel: ModelOnderdeel) -> Project:
        project = self._projecten[project_id]
        index = next((i for i, o in enumerate(project.losse_onderdelen) if o.id == onderdeel.id), None)
        if index is None:
            raise KeyError(f"Onbekend los onderdeel: {onderdeel.id!r}")
        oorspronkelijk = project.losse_onderdelen[index]
        project.losse_onderdelen[index] = onderdeel
        fouten = valideer(project, self._materialen)
        if fouten:
            project.losse_onderdelen[index] = oorspronkelijk
            raise ValueError("; ".join(fouten))
        self._persisteer(project)
        return project

    def los_onderdeel_verwijderen(self, project_id: str, onderdeel_id: str) -> Project:
        project = self._projecten[project_id]
        project.losse_onderdelen = [o for o in project.losse_onderdelen if o.id != onderdeel_id]
        self._persisteer(project)
        return project

    # ------------------------------------------------------------------
    # Status en archief (hoofdstuk 1/4)
    # ------------------------------------------------------------------
    def zet_status(self, project_id: str, status: ProjectStatus) -> Project:
        project = self._projecten[project_id]
        project.status = status
        self._persisteer(project)
        return project

    def archiveren(self, project_id: str) -> Project:
        project = self._projecten[project_id]
        if project.status != ProjectStatus.AFGEROND:
            raise OngeldigeStatusOvergangError("Alleen afgeronde projecten kunnen gearchiveerd worden.")
        if project.gearchiveerd:
            raise OngeldigeStatusOvergangError("Dit project is al gearchiveerd.")
        project.gearchiveerd = True
        self._persisteer(project)
        return project

    def heractiveren(self, project_id: str) -> Project:
        project = self._projecten[project_id]
        if not project.gearchiveerd:
            raise OngeldigeStatusOvergangError("Dit project staat niet in het archief.")
        project.gearchiveerd = False
        self._persisteer(project)
        return project

    def verwijderen_definitief(self, project_id: str) -> None:
        project = self._projecten[project_id]
        if not project.gearchiveerd:
            raise OngeldigeStatusOvergangError("Alleen gearchiveerde projecten kunnen definitief verwijderd worden.")
        del self._projecten[project_id]
        if self._db is not None:
            opslag.verwijderen(self._db, project_id)

    def _persisteer(self, project: Project) -> None:
        if self._db is not None:
            opslag.opslaan(self._db, project)

    def lijst(
        self,
        status: ProjectStatus | None = None,
        gearchiveerd: bool | None = None,
        zoekterm: str = "",
    ) -> list[Project]:
        resultaat = list(self._projecten.values())
        if status is not None:
            resultaat = [p for p in resultaat if p.status == status]
        if gearchiveerd is not None:
            resultaat = [p for p in resultaat if p.gearchiveerd == gearchiveerd]
        termen = zoekterm.lower().split()
        if termen:
            resultaat = [p for p in resultaat if all(_project_matcht_term(p, term) for term in termen)]
        return sorted(resultaat, key=lambda p: p.naam.lower())
