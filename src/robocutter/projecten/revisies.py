"""Revisiegeschiedenis van een project (hoofdstuk 1, Module 1).

Een project bestaat uit revisies: de eerste vastlegging heet
"Origineel" (het origineel heeft zelf geen revisieletter), daarna Rev A,
Rev B, ... Revisies worden altijd **handmatig** vastgelegd, nooit
automatisch. Elke revisie krijgt een automatische wijzigingssamenvatting
(``vergelijk_projecten``) plus een optionele notitie.

Keuzes van Sven (oktober 2026):

- De "sandbox"/werkkopie uit hoofdstuk 1 is gewoon de huidige stand van
  het project: je werkt erin, en "revisie vastleggen" maakt van de
  wijzigingen sinds de vorige revisie de nieuwe revisie. Intern bewaart
  elke revisie een volledige momentopname (klein, en betrouwbaarder dan
  delta's); de wijzigingen worden bij het tonen uitgerekend.
- Een oude revisie kun je bekijken en terugzetten. Terugzetten maakt de
  huidige stand weer gelijk aan die revisie; dat is zelf een wijziging,
  die je daarna als nieuwe revisie kunt vastleggen.
- Eerst alleen projecten; modelrevisies volgen later.

Een momentopname bevat de projectgegevens en de samenstelling
(modelkopieën + losse onderdelen). Status en archief horen er niet bij:
dat is voortgang, geen inhoud, en terugzetten laat ze ongemoeid.
"""

from __future__ import annotations

import sqlite3
import uuid
from copy import deepcopy
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Callable

from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.modellen.models import ModelOnderdeel
from robocutter.projecten import revisies_opslag as opslag
from robocutter.projecten.bibliotheek import ProjectenBibliotheek
from robocutter.projecten.models import Project


class GeenWijzigingenError(Exception):
    """Vastleggen terwijl er sinds de vorige revisie niets veranderd is."""


def revisie_naam(nummer: int) -> str:
    """0 → "Origineel", 1 → "Rev A", 26 → "Rev Z", 27 → "Rev AA", ..."""

    if nummer <= 0:
        return "Origineel"
    letters = ""
    n = nummer
    while n > 0:
        n, rest = divmod(n - 1, 26)
        letters = chr(ord("A") + rest) + letters
    return f"Rev {letters}"


@dataclass
class ProjectRevisie:
    id: str
    project_id: str
    nummer: int  # 0 = Origineel, 1 = Rev A, ...
    aangemaakt: datetime
    momentopname: Project
    samenvatting: list[str] = field(default_factory=list)
    notitie: str = ""

    @property
    def naam(self) -> str:
        return revisie_naam(self.nummer)


# ----------------------------------------------------------------------
# Wijzigingssamenvatting
# ----------------------------------------------------------------------
_PROJECTVELDEN = (
    ("naam", "Projectnaam"),
    ("klant", "Klant"),
    ("contactpersoon", "Contactpersoon"),
    ("email", "E-mail"),
    ("telefoon", "Telefoon"),
    ("opdrachtnummer", "Opdrachtnummer"),
    ("startdatum", "Startdatum"),
    ("opleverdatum", "Opleverdatum"),
)


def _tekst(waarde) -> str:
    if waarde is None or waarde == "":
        return "leeg"
    if hasattr(waarde, "isoformat"):
        return waarde.isoformat()
    return str(waarde)


def _onderdeel_verschillen(oud: ModelOnderdeel, nieuw: ModelOnderdeel, materiaal_naam: Callable[[str], str]) -> list[str]:
    delen: list[str] = []
    if oud.naam != nieuw.naam:
        delen.append(f"naam → {nieuw.naam}")
    if (oud.breedte, oud.hoogte) != (nieuw.breedte, nieuw.hoogte):
        delen.append(f"{oud.breedte:g} × {oud.hoogte:g} → {nieuw.breedte:g} × {nieuw.hoogte:g} mm")
    if oud.aantal != nieuw.aantal:
        delen.append(f"aantal {oud.aantal} → {nieuw.aantal}")
    if oud.materiaal_id != nieuw.materiaal_id:
        delen.append(f"materiaal → {materiaal_naam(nieuw.materiaal_id)}")
    if oud.nerfrichting_vereist != nieuw.nerfrichting_vereist:
        delen.append("nerfrichting")
    if oud.kantenband_randen != nieuw.kantenband_randen:
        delen.append("kantenband")
    if oud.fabriekskantenband_vereist != nieuw.fabriekskantenband_vereist:
        delen.append("fabriekskantenband")
    if (oud.groep_id, oud.groep_volgorde) != (nieuw.groep_id, nieuw.groep_volgorde):
        delen.append("groep")
    return delen


def _vergelijk_onderdelen(
    oud: list[ModelOnderdeel], nieuw: list[ModelOnderdeel], materiaal_naam: Callable[[str], str]
) -> tuple[list[str], list[str], list[str]]:
    """(toegevoegd, verwijderd, gewijzigd) als korte teksten. Vergelijkt op
    onderdeel-id; zonder bruikbare (unieke) id's op volgorde."""

    oud_ids = [o.id for o in oud]
    nieuw_ids = [o.id for o in nieuw]
    if all(oud_ids) and all(nieuw_ids) and len(set(oud_ids)) == len(oud_ids) and len(set(nieuw_ids)) == len(nieuw_ids):
        oud_per_id = {o.id: o for o in oud}
        nieuw_per_id = {o.id: o for o in nieuw}
        toegevoegd = [o.naam for o in nieuw if o.id not in oud_per_id]
        verwijderd = [o.naam for o in oud if o.id not in nieuw_per_id]
        paren = [(oud_per_id[o.id], o) for o in nieuw if o.id in oud_per_id]
    else:
        n = min(len(oud), len(nieuw))
        toegevoegd = [o.naam for o in nieuw[n:]]
        verwijderd = [o.naam for o in oud[n:]]
        paren = list(zip(oud[:n], nieuw[:n]))
    gewijzigd = []
    for o, n_ in paren:
        delen = _onderdeel_verschillen(o, n_, materiaal_naam)
        if delen:
            gewijzigd.append(f"{o.naam} ({', '.join(delen)})")
    return toegevoegd, verwijderd, gewijzigd


def vergelijk_projecten(
    oud: Project, nieuw: Project, materiaal_naam: Callable[[str], str] = lambda materiaal_id: materiaal_id
) -> list[str]:
    """De wijzigingen van ``oud`` naar ``nieuw`` als korte Nederlandse
    regels (leeg = niets veranderd). Status en archief tellen niet mee."""

    regels: list[str] = []
    for veld, label in _PROJECTVELDEN:
        a, b = getattr(oud, veld), getattr(nieuw, veld)
        if a != b:
            regels.append(f"{label}: {_tekst(a)} → {_tekst(b)}")

    oud_inst = {i.id: i for i in oud.modelinstanties}
    nieuw_inst = {i.id: i for i in nieuw.modelinstanties}
    for i in nieuw.modelinstanties:
        if i.id not in oud_inst:
            regels.append(f"Model toegevoegd: {i.model_naam} ×{i.aantal}")
    for i in oud.modelinstanties:
        if i.id not in nieuw_inst:
            regels.append(f"Model verwijderd: {i.model_naam} ×{i.aantal}")
    for i in nieuw.modelinstanties:
        o = oud_inst.get(i.id)
        if o is None:
            continue
        if o.aantal != i.aantal:
            regels.append(f"{i.model_naam}: aantal {o.aantal} → {i.aantal}")
        if o.model_naam != i.model_naam:
            regels.append(f"{o.model_naam} hoort nu bij model {i.model_naam}")
        toegevoegd, verwijderd, gewijzigd = _vergelijk_onderdelen(o.onderdelen, i.onderdelen, materiaal_naam)
        for naam in toegevoegd:
            regels.append(f"{i.model_naam}: onderdeel toegevoegd: {naam}")
        for naam in verwijderd:
            regels.append(f"{i.model_naam}: onderdeel verwijderd: {naam}")
        for tekst in gewijzigd:
            regels.append(f"{i.model_naam}: {tekst}")

    toegevoegd, verwijderd, gewijzigd = _vergelijk_onderdelen(oud.losse_onderdelen, nieuw.losse_onderdelen, materiaal_naam)
    regels.extend(f"Los onderdeel toegevoegd: {naam}" for naam in toegevoegd)
    regels.extend(f"Los onderdeel verwijderd: {naam}" for naam in verwijderd)
    regels.extend(f"Los onderdeel gewijzigd: {tekst}" for tekst in gewijzigd)
    return regels


def samenstelling_wijzigingen(
    oud: Project, nieuw: Project, materiaal_naam: Callable[[str], str] = lambda materiaal_id: materiaal_id
) -> list[str]:
    """Zoals ``vergelijk_projecten``, maar alleen wat het zaagplan raakt:
    modelkopieën en losse onderdelen, geen projectgegevens. Basis voor
    "Niet gecontroleerd" (hoofdstuk 1/2): een zaagplan of label dat op
    ``oud`` gebaseerd is klopt niet meer als dit niet leeg is."""

    gelijk = {veld: getattr(nieuw, veld) for veld, _ in _PROJECTVELDEN}
    return vergelijk_projecten(replace(oud, **gelijk), nieuw, materiaal_naam)


def _inhoud_samenvatting(project: Project) -> list[str]:
    n_modellen = sum(i.aantal for i in project.modelinstanties)
    n_los = len(project.losse_onderdelen)
    return [
        f"Eerste vastlegging: {n_modellen} {'model' if n_modellen == 1 else 'modellen'}, "
        f"{n_los} {'los onderdeel' if n_los == 1 else 'losse onderdelen'}"
    ]


# ----------------------------------------------------------------------
# Bibliotheek
# ----------------------------------------------------------------------
class ProjectRevisiesBibliotheek:
    """Revisies per project, met optionele SQLite-opslag (eigen tabel in
    hetzelfde db-bestand, zie ``revisies_opslag.py``)."""

    def __init__(
        self,
        projecten: ProjectenBibliotheek,
        materialen: MaterialenBibliotheek,
        db_verbinding: sqlite3.Connection | None = None,
    ) -> None:
        self._projecten = projecten
        self._materialen = materialen
        self._db = db_verbinding
        self._revisies: dict[str, ProjectRevisie] = {}
        if self._db is not None:
            for revisie in opslag.laad_alles(self._db):
                self._revisies[revisie.id] = revisie

    def _materiaal_naam(self, materiaal_id: str) -> str:
        try:
            return self._materialen.ophalen(materiaal_id).naam
        except KeyError:
            return materiaal_id

    def lijst(self, project_id: str) -> list[ProjectRevisie]:
        return sorted((r for r in self._revisies.values() if r.project_id == project_id), key=lambda r: r.nummer)

    def ophalen(self, revisie_id: str) -> ProjectRevisie:
        return self._revisies[revisie_id]

    def laatste(self, project_id: str) -> ProjectRevisie | None:
        revisies = self.lijst(project_id)
        return revisies[-1] if revisies else None

    def volgende_naam(self, project_id: str) -> str:
        laatste = self.laatste(project_id)
        return revisie_naam(0 if laatste is None else laatste.nummer + 1)

    def wijzigingen(self, project_id: str) -> list[str] | None:
        """Wijzigingen in de huidige stand sinds de laatste revisie.
        ``None`` als er nog geen enkele revisie is."""

        laatste = self.laatste(project_id)
        if laatste is None:
            return None
        return vergelijk_projecten(laatste.momentopname, self._projecten.ophalen(project_id), self._materiaal_naam)

    def huidige_revisie_label(self, project_id: str) -> str:
        """Voor op zaagplannen/labels: "" zonder revisies, anders de naam
        van de laatste revisie, met een * als de huidige stand daarvan
        afwijkt (niet-vastgelegde wijzigingen)."""

        laatste = self.laatste(project_id)
        if laatste is None:
            return ""
        return laatste.naam + ("*" if self.wijzigingen(project_id) else "")

    def zaagplan_wijzigingen(self, project_id: str, bron: Project) -> list[str]:
        """Wat er in de samenstelling veranderd is sinds een zaagplan uit
        ``bron`` gegenereerd werd (leeg = zaagplan klopt nog)."""
        return samenstelling_wijzigingen(bron, self._projecten.ophalen(project_id), self._materiaal_naam)

    def wijzigingen_van(self, revisie_id: str) -> list[str]:
        """Wat deze revisie veranderde t.o.v. de revisie ervoor (de
        bewaarde samenvatting)."""
        return list(self._revisies[revisie_id].samenvatting)

    def vastleggen(self, project_id: str, notitie: str = "") -> ProjectRevisie:
        project = self._projecten.ophalen(project_id)
        laatste = self.laatste(project_id)
        if laatste is None:
            nummer, samenvatting = 0, _inhoud_samenvatting(project)
        else:
            samenvatting = vergelijk_projecten(laatste.momentopname, project, self._materiaal_naam)
            if not samenvatting:
                raise GeenWijzigingenError(f"Er is niets veranderd sinds {laatste.naam}.")
            nummer = laatste.nummer + 1
        revisie = ProjectRevisie(
            id=uuid.uuid4().hex[:8],
            project_id=project_id,
            nummer=nummer,
            aangemaakt=datetime.now().replace(microsecond=0),
            momentopname=deepcopy(project),
            samenvatting=samenvatting,
            notitie=notitie.strip(),
        )
        self._revisies[revisie.id] = revisie
        if self._db is not None:
            opslag.opslaan(self._db, revisie)
        return revisie

    def terugzetten(self, project_id: str, revisie_id: str) -> Project:
        """Maakt de huidige stand weer gelijk aan deze revisie
        (projectgegevens + samenstelling). Status en archief blijven zoals
        ze nu zijn. Legt zelf geen revisie vast."""

        revisie = self._revisies[revisie_id]
        if revisie.project_id != project_id:
            raise KeyError(f"Revisie {revisie_id!r} hoort niet bij project {project_id!r}.")
        huidig = self._projecten.ophalen(project_id)
        teruggezet = replace(
            deepcopy(revisie.momentopname),
            id=huidig.id,
            status=huidig.status,
            gearchiveerd=huidig.gearchiveerd,
        )
        return self._projecten.bijwerken(teruggezet)

    def verwijder_project(self, project_id: str) -> None:
        """Bij definitief verwijderen van het project."""
        for revisie in [r for r in self._revisies.values() if r.project_id == project_id]:
            del self._revisies[revisie.id]
        if self._db is not None:
            opslag.verwijder_project(self._db, project_id)
