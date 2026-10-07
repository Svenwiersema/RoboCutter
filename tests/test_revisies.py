"""Tests voor de revisiegeschiedenis van projecten (``projecten/revisies.py``)."""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.materialen.models import Materiaal, MateriaalType
from robocutter.modellen.bibliotheek import ModellenBibliotheek
from robocutter.modellen.models import Model, ModelOnderdeel
from robocutter.projecten.bibliotheek import ProjectenBibliotheek
from robocutter.projecten.models import Project, ProjectStatus
from robocutter.projecten.revisies import (
    ONBEKENDE_HERKOMST,
    GeenWijzigingenError,
    ProjectRevisiesBibliotheek,
    revisie_naam,
    vergelijk_projecten,
)


def _opzet(db=None):
    from robocutter.materialen.opslag import open_verbinding as open_mat
    from robocutter.modellen.opslag import open_verbinding as open_mod
    from robocutter.projecten.opslag import open_verbinding as open_proj
    from robocutter.projecten.revisies_opslag import open_verbinding as open_rev

    materialen = MaterialenBibliotheek(open_mat(db) if db else None)
    modellen = ModellenBibliotheek(materialen, open_mod(db) if db else None)
    projecten = ProjectenBibliotheek(modellen, materialen, open_proj(db) if db else None)
    revisies = ProjectRevisiesBibliotheek(projecten, materialen, open_rev(db) if db else None)
    return materialen, modellen, projecten, revisies


def _project_met_inhoud(materialen, modellen, projecten):
    wit = materialen.toevoegen(
        Materiaal(id="", naam="Wit 18", type=MateriaalType.PLAAT, lengte=2800, breedte=2070, derde_afmeting=18)
    )
    kast = modellen.toevoegen(
        Model(
            id="",
            naam="Onderkast",
            onderdelen=[ModelOnderdeel(id="b", naam="Bodem", materiaal_id=wit.id, breedte=564, hoogte=540)],
        )
    )
    project = projecten.toevoegen(Project(id="", naam="Keuken", klant="Jansen"))
    project = projecten.model_toevoegen(project.id, kast.id, aantal=2)
    projecten.los_onderdeel_toevoegen(
        project.id, ModelOnderdeel(id="", naam="Plint", materiaal_id=wit.id, breedte=2400, hoogte=120)
    )
    return wit, kast, projecten.ophalen(project.id)


def test_revisie_namen():
    assert [revisie_naam(n) for n in (0, 1, 2, 26, 27, 28)] == [
        "Origineel", "Rev A", "Rev B", "Rev Z", "Rev AA", "Rev AB",
    ]


def test_eerste_vastlegging_is_origineel_daarna_letters():
    materialen, modellen, projecten, revisies = _opzet()
    _, _, project = _project_met_inhoud(materialen, modellen, projecten)

    assert revisies.wijzigingen(project.id) is None
    assert revisies.volgende_naam(project.id) == "Origineel"
    origineel = revisies.vastleggen(project.id, notitie="  akkoord klant  ")
    assert origineel.naam == "Origineel" and origineel.notitie == "akkoord klant"
    assert origineel.samenvatting == ["Eerste vastlegging: 2 modellen, 1 los onderdeel"]
    assert revisies.wijzigingen(project.id) == []
    assert revisies.volgende_naam(project.id) == "Rev A"

    with pytest.raises(GeenWijzigingenError):
        revisies.vastleggen(project.id)

    instantie = project.modelinstanties[0]
    projecten.model_instantie_onderdelen_opslaan(
        project.id, instantie.id, [replace(instantie.onderdelen[0], hoogte=520)]
    )
    assert revisies.wijzigingen(project.id) == ["Onderkast: Bodem (564 × 540 → 564 × 520 mm)"]
    rev_a = revisies.vastleggen(project.id)
    assert rev_a.naam == "Rev A" and rev_a.samenvatting == ["Onderkast: Bodem (564 × 540 → 564 × 520 mm)"]
    assert [r.naam for r in revisies.lijst(project.id)] == ["Origineel", "Rev A"]


def test_status_en_archief_zijn_geen_wijziging():
    materialen, modellen, projecten, revisies = _opzet()
    _, _, project = _project_met_inhoud(materialen, modellen, projecten)
    revisies.vastleggen(project.id)
    projecten.zet_status(project.id, ProjectStatus.IN_PRODUCTIE)
    assert revisies.wijzigingen(project.id) == []


def test_vergelijk_projecten_noemt_alle_soorten_wijzigingen():
    materialen, modellen, projecten, _ = _opzet()
    wit, kast, oud = _project_met_inhoud(materialen, modellen, projecten)
    eiken = materialen.toevoegen(
        Materiaal(id="", naam="Eiken 18", type=MateriaalType.PLAAT, lengte=2800, breedte=2070, derde_afmeting=18)
    )
    from copy import deepcopy

    oud = deepcopy(oud)  # de bibliotheek past het project-object ter plekke aan
    nieuw = deepcopy(oud)
    nieuw.klant = "fam. Jansen"
    nieuw.opleverdatum = date(2026, 11, 20)
    nieuw.modelinstanties[0].aantal = 3
    plint = nieuw.losse_onderdelen[0]
    nieuw.losse_onderdelen = [
        replace(plint, materiaal_id=eiken.id, aantal=2),
        ModelOnderdeel(id="x", naam="Passtuk", materiaal_id=wit.id, breedte=720, hoogte=45),
    ]
    projecten.model_toevoegen(oud.id, kast.id)
    nieuw.modelinstanties.append(deepcopy(projecten.ophalen(oud.id).modelinstanties[-1]))

    regels = vergelijk_projecten(oud, nieuw, lambda m: materialen.ophalen(m).naam)
    assert regels == [
        "Klant: Jansen → fam. Jansen",
        "Opleverdatum: leeg → 2026-11-20",
        "Model toegevoegd: Onderkast ×1",
        "Onderkast: aantal 2 → 3",
        "Los onderdeel toegevoegd: Passtuk",
        "Los onderdeel gewijzigd: Plint (aantal 1 → 2, materiaal → Eiken 18)",
    ]
    assert vergelijk_projecten(nieuw, oud)[2] == "Model verwijderd: Onderkast ×1"


def test_terugzetten_houdt_status_en_maakt_geen_revisie():
    materialen, modellen, projecten, revisies = _opzet()
    _, _, project = _project_met_inhoud(materialen, modellen, projecten)
    origineel = revisies.vastleggen(project.id)
    project.naam = "Keuken groot"
    projecten.bijwerken(project)
    projecten.model_instantie_verwijderen(project.id, project.modelinstanties[0].id)
    projecten.zet_status(project.id, ProjectStatus.IN_PRODUCTIE)
    revisies.vastleggen(project.id)

    teruggezet = revisies.terugzetten(project.id, origineel.id)

    assert teruggezet.naam == "Keuken" and len(teruggezet.modelinstanties) == 1
    assert teruggezet.status == ProjectStatus.IN_PRODUCTIE
    assert len(revisies.lijst(project.id)) == 2
    assert revisies.wijzigingen(project.id) == [
        "Projectnaam: Keuken groot → Keuken",
        "Model toegevoegd: Onderkast ×2",
    ]
    # De momentopname zelf blijft onaangeroerd door latere wijzigingen.
    projecten.zet_status(project.id, ProjectStatus.AFGEROND)
    projecten.model_instantie_verwijderen(project.id, teruggezet.modelinstanties[0].id)
    assert len(revisies.ophalen(origineel.id).momentopname.modelinstanties) == 1


def test_revisies_overleven_herstart_en_verdwijnen_met_project(tmp_path):
    db = tmp_path / "robocutter.db"
    materialen, modellen, projecten, revisies = _opzet(db)
    _, _, project = _project_met_inhoud(materialen, modellen, projecten)
    revisies.vastleggen(project.id, notitie="eerste")
    project.klant = "Pietersen"
    projecten.bijwerken(project)
    revisies.vastleggen(project.id)

    _, _, projecten2, revisies2 = _opzet(db)
    lijst = revisies2.lijst(project.id)
    assert [(r.naam, r.notitie) for r in lijst] == [("Origineel", "eerste"), ("Rev A", "")]
    assert lijst[1].samenvatting == ["Klant: Jansen → Pietersen"]
    assert lijst[0].momentopname.losse_onderdelen[0].naam == "Plint"
    assert lijst[0].aangemaakt <= lijst[1].aangemaakt
    assert revisies2.wijzigingen(project.id) == []

    revisies2.verwijder_project(project.id)
    _, _, _, revisies3 = _opzet(db)
    assert revisies3.lijst(project.id) == []


def test_revisielabel_en_zaagplan_wijzigingen():
    from copy import deepcopy

    materialen, modellen, projecten, revisies = _opzet()
    _, _, project = _project_met_inhoud(materialen, modellen, projecten)
    assert revisies.huidige_revisie_label(project.id) == ""
    revisies.vastleggen(project.id)
    assert revisies.huidige_revisie_label(project.id) == "Origineel"

    bron = deepcopy(projecten.ophalen(project.id))
    assert revisies.zaagplan_wijzigingen(project.id, bron) == []
    # Projectgegevens raken het zaagplan niet...
    project.klant = "Pietersen"
    projecten.bijwerken(project)
    assert revisies.zaagplan_wijzigingen(project.id, bron) == []
    assert revisies.huidige_revisie_label(project.id) == "Origineel*"
    # ...de samenstelling wel.
    projecten.los_onderdeel_verwijderen(project.id, project.losse_onderdelen[0].id)
    assert revisies.zaagplan_wijzigingen(project.id, bron) == ["Los onderdeel verwijderd: Plint"]
    revisies.vastleggen(project.id)
    assert revisies.huidige_revisie_label(project.id) == "Rev A"


def test_zaagplan_controle_telt_onbekende_herkomst_als_niet_gecontroleerd():
    from copy import deepcopy

    materialen, modellen, projecten, revisies = _opzet()
    _, _, project = _project_met_inhoud(materialen, modellen, projecten)
    assert revisies.zaagplan_controle(project.id, None) == [ONBEKENDE_HERKOMST]
    bron = deepcopy(project)
    assert revisies.zaagplan_controle(project.id, bron) == []
    projecten.los_onderdeel_verwijderen(project.id, project.losse_onderdelen[0].id)
    assert revisies.zaagplan_controle(project.id, bron) == ["Los onderdeel verwijderd: Plint"]
