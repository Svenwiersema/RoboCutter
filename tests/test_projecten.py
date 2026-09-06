"""Tests voor de projectenbibliotheek-functie (Module 1/4).

Dekt: live validatie (incl. losse onderdelen), het model-snapshot-
mechanisme (platslaan, ook met geneste submodellen, en het expliciet
bijwerken naar de laatste modelversie), de archiveer-workflow (alleen
vanuit status Afgerond), de zaaglijst (combineren van model-snapshots +
losse onderdelen) en de multi-criteria sortering daarvan, en het
wegschrijven/herladen via de SQLite-opslag.
"""

from __future__ import annotations

import pytest

from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.materialen.models import Materiaal, MateriaalType
from robocutter.modellen.bibliotheek import ModellenBibliotheek
from robocutter.modellen.models import Model, ModelOnderdeel, SubModelVerwijzing
from robocutter.projecten.bibliotheek import (
    OngeldigeStatusOvergangError,
    ProjectenBibliotheek,
    valideer,
)
from robocutter.projecten.models import Project, ProjectStatus
from robocutter.projecten.opslag import open_verbinding
from robocutter.projecten.zaaglijst import (
    OnbekendeSorteersleutelError,
    bouw_zaaglijst,
    sorteer_zaaglijst,
)


def _materiaal(**overrides) -> Materiaal:
    basis = dict(
        id="",
        naam="Eiken multiplex 18mm",
        type=MateriaalType.PLAAT,
        lengte=2800,
        breedte=2070,
        derde_afmeting=18,
        familie="Eiken multiplex",
    )
    basis.update(overrides)
    return Materiaal(**basis)


def _onderdeel(materiaal_id: str, **overrides) -> ModelOnderdeel:
    basis = dict(id="", naam="Zijkant", materiaal_id=materiaal_id, breedte=600, hoogte=720)
    basis.update(overrides)
    return ModelOnderdeel(**basis)


def _model(**overrides) -> Model:
    basis = dict(id="", naam="Onderkast 60cm")
    basis.update(overrides)
    return Model(**basis)


def _project(**overrides) -> Project:
    basis = dict(id="", naam="Keuken Jansen", klant="fam. Jansen")
    basis.update(overrides)
    return Project(**basis)


def _bibliotheken() -> tuple[MaterialenBibliotheek, ModellenBibliotheek, ProjectenBibliotheek]:
    materialen = MaterialenBibliotheek()
    modellen = ModellenBibliotheek(materialen)
    projecten = ProjectenBibliotheek(modellen, materialen)
    return materialen, modellen, projecten


def test_valideer_geldig_project_geeft_geen_fouten():
    materialen, _, _ = _bibliotheken()
    assert valideer(_project(), materialen) == []


def test_valideer_zonder_naam_en_klant():
    materialen, _, _ = _bibliotheken()
    fouten = valideer(_project(naam="", klant=""), materialen)
    assert "Naam is verplicht." in fouten
    assert "Klant is verplicht." in fouten


def test_valideer_signaleert_ongeldig_los_onderdeel():
    materialen, _, _ = _bibliotheken()
    materiaal = materialen.toevoegen(_materiaal())
    project = _project(losse_onderdelen=[_onderdeel(materiaal.id, breedte=0)])
    fouten = valideer(project, materialen)
    assert any(f.endswith("breedte moet groter dan 0 zijn.") for f in fouten)


def test_valideer_met_onbekend_materiaal_op_los_onderdeel():
    materialen, _, _ = _bibliotheken()
    project = _project(losse_onderdelen=[_onderdeel("bestaat-niet")])
    fouten = valideer(project, materialen)
    assert any("materiaal bestaat niet (meer)" in f for f in fouten)


def test_toevoegen_wijst_id_toe():
    materialen, _, projecten = _bibliotheken()
    project = projecten.toevoegen(_project())
    assert project.id


def test_toevoegen_met_ongeldig_project_faalt():
    materialen, _, projecten = _bibliotheken()
    with pytest.raises(ValueError):
        projecten.toevoegen(_project(naam=""))


def test_model_toevoegen_slaat_onderdelen_plat():
    materialen, modellen, projecten = _bibliotheken()
    materiaal = materialen.toevoegen(_materiaal())
    onderkast = modellen.toevoegen(
        _model(naam="Onderkast", onderdelen=[_onderdeel(materiaal.id, naam="Zijkant", aantal=2)])
    )
    project = projecten.toevoegen(_project())

    project = projecten.model_toevoegen(project.id, onderkast.id, aantal=1)
    assert len(project.modelinstanties) == 1
    instantie = project.modelinstanties[0]
    assert instantie.model_naam == "Onderkast"
    assert len(instantie.onderdelen) == 1
    assert instantie.onderdelen[0].aantal == 2


def test_model_toevoegen_slaat_geneste_submodellen_plat_met_vermenigvuldigde_aantallen():
    materialen, modellen, projecten = _bibliotheken()
    materiaal = materialen.toevoegen(_materiaal())
    onderkast = modellen.toevoegen(
        _model(naam="Onderkast", onderdelen=[_onderdeel(materiaal.id, naam="Zijkant", aantal=2)])
    )
    keuken = modellen.toevoegen(
        _model(naam="Keuken", submodellen=[SubModelVerwijzing(model_id=onderkast.id, aantal=3)])
    )
    project = projecten.toevoegen(_project())

    project = projecten.model_toevoegen(project.id, keuken.id, aantal=1)
    instantie = project.modelinstanties[0]
    # 3 onderkasten x 2 zijkanten elk = aantal 6 op de platgeslagen regel.
    assert len(instantie.onderdelen) == 1
    assert instantie.onderdelen[0].aantal == 6


def test_model_bijwerken_naar_laatste_versie():
    materialen, modellen, projecten = _bibliotheken()
    materiaal = materialen.toevoegen(_materiaal())
    onderkast = modellen.toevoegen(
        _model(naam="Onderkast", onderdelen=[_onderdeel(materiaal.id, naam="Zijkant", aantal=1)])
    )
    project = projecten.toevoegen(_project())
    project = projecten.model_toevoegen(project.id, onderkast.id)
    instantie_id = project.modelinstanties[0].id

    # Bronmodel wijzigen: extra onderdeel toevoegen.
    onderkast_bijgewerkt = modellen.ophalen(onderkast.id)
    onderkast_bijgewerkt.onderdelen.append(_onderdeel(materiaal.id, naam="Deur", aantal=1))
    modellen.bijwerken(onderkast_bijgewerkt)

    # De snapshot in het project verandert niet vanzelf mee.
    project = projecten.ophalen(project.id)
    assert len(project.modelinstanties[0].onderdelen) == 1

    project = projecten.model_bijwerken_naar_laatste_versie(project.id, instantie_id)
    assert len(project.modelinstanties[0].onderdelen) == 2


def test_archiveren_alleen_vanuit_afgerond():
    materialen, _, projecten = _bibliotheken()
    project = projecten.toevoegen(_project())

    with pytest.raises(OngeldigeStatusOvergangError):
        projecten.archiveren(project.id)

    projecten.zet_status(project.id, ProjectStatus.AFGEROND)
    projecten.archiveren(project.id)
    assert projecten.ophalen(project.id).gearchiveerd is True

    with pytest.raises(OngeldigeStatusOvergangError):
        projecten.archiveren(project.id)


def test_verwijderen_definitief_alleen_vanuit_archief():
    materialen, _, projecten = _bibliotheken()
    project = projecten.toevoegen(_project())

    with pytest.raises(OngeldigeStatusOvergangError):
        projecten.verwijderen_definitief(project.id)

    projecten.zet_status(project.id, ProjectStatus.AFGEROND)
    projecten.archiveren(project.id)
    projecten.verwijderen_definitief(project.id)
    with pytest.raises(KeyError):
        projecten.ophalen(project.id)


def test_zaaglijst_combineert_modelinstanties_en_losse_onderdelen():
    materialen, modellen, projecten = _bibliotheken()
    materiaal = materialen.toevoegen(_materiaal())
    onderkast = modellen.toevoegen(
        _model(naam="Onderkast", onderdelen=[_onderdeel(materiaal.id, naam="Zijkant", aantal=1)])
    )
    project = projecten.toevoegen(
        _project(losse_onderdelen=[_onderdeel(materiaal.id, naam="Los plankje", aantal=1)])
    )
    project = projecten.model_toevoegen(project.id, onderkast.id, aantal=2)

    regels = bouw_zaaglijst(project)
    assert len(regels) == 2
    zijkant = next(r for r in regels if r.onderdeel.naam == "Zijkant")
    assert zijkant.onderdeel.aantal == 2  # 1 (per onderdeel) x instantie-aantal 2
    assert zijkant.herkomst == "Onderkast"
    los = next(r for r in regels if r.onderdeel.naam == "Los plankje")
    assert los.herkomst == "Los onderdeel"


def test_sorteer_zaaglijst_op_materiaal_en_dan_breedte():
    materialen, modellen, projecten = _bibliotheken()
    eiken = materialen.toevoegen(_materiaal(naam="Eiken multiplex 18mm"))
    mdf = materialen.toevoegen(_materiaal(naam="Wit MDF 18mm", familie="MDF"))

    project = projecten.toevoegen(
        _project(
            losse_onderdelen=[
                _onderdeel(mdf.id, naam="MDF breed", breedte=800),
                _onderdeel(eiken.id, naam="Eiken smal", breedte=300),
                _onderdeel(mdf.id, naam="MDF smal", breedte=200),
                _onderdeel(eiken.id, naam="Eiken breed", breedte=900),
            ]
        )
    )

    regels = bouw_zaaglijst(project)
    gesorteerd = sorteer_zaaglijst(regels, ["materiaal", "breedte"], materialen)
    volgorde = [r.onderdeel.naam for r in gesorteerd]
    # Eiken multiplex komt alfabetisch vóór Wit MDF; binnen elk materiaal
    # oplopend op breedte.
    assert volgorde == ["Eiken smal", "Eiken breed", "MDF smal", "MDF breed"]


def test_sorteer_zaaglijst_met_onbekende_sleutel_faalt():
    materialen, _, projecten = _bibliotheken()
    project = projecten.toevoegen(_project())
    with pytest.raises(OnbekendeSorteersleutelError):
        sorteer_zaaglijst(bouw_zaaglijst(project), ["onbestaand"], materialen)


def test_sqlite_opslag_overleeft_herstart(tmp_path):
    materialen_db = tmp_path / "materialen.db"
    modellen_db = tmp_path / "modellen.db"
    projecten_db = tmp_path / "projecten.db"

    from robocutter.materialen.opslag import open_verbinding as open_materialen_verbinding
    from robocutter.modellen.opslag import open_verbinding as open_modellen_verbinding

    mat_verbinding = open_materialen_verbinding(materialen_db)
    materialen = MaterialenBibliotheek(mat_verbinding)
    materiaal = materialen.toevoegen(_materiaal())

    mod_verbinding = open_modellen_verbinding(modellen_db)
    modellen = ModellenBibliotheek(materialen, mod_verbinding)
    onderkast = modellen.toevoegen(_model(naam="Onderkast", onderdelen=[_onderdeel(materiaal.id)]))

    proj_verbinding = open_verbinding(projecten_db)
    projecten = ProjectenBibliotheek(modellen, materialen, proj_verbinding)
    project = projecten.toevoegen(_project(opdrachtnummer="#2026-014"))
    project = projecten.model_toevoegen(project.id, onderkast.id, aantal=2)
    projecten.zet_status(project.id, ProjectStatus.AFGEROND)
    proj_verbinding.close()
    mod_verbinding.close()
    mat_verbinding.close()

    # Nieuwe verbindingen simuleren een herstart van de app.
    herstart_mat_verbinding = open_materialen_verbinding(materialen_db)
    herstarte_materialen = MaterialenBibliotheek(herstart_mat_verbinding)
    herstart_mod_verbinding = open_modellen_verbinding(modellen_db)
    herstarte_modellen = ModellenBibliotheek(herstarte_materialen, herstart_mod_verbinding)
    herstart_proj_verbinding = open_verbinding(projecten_db)
    herstarte_projecten = ProjectenBibliotheek(herstarte_modellen, herstarte_materialen, herstart_proj_verbinding)

    herladen = herstarte_projecten.ophalen(project.id)
    assert herladen.opdrachtnummer == "#2026-014"
    assert herladen.status == ProjectStatus.AFGEROND
    assert len(herladen.modelinstanties) == 1
    assert herladen.modelinstanties[0].aantal == 2
    assert herladen.modelinstanties[0].onderdelen[0].naam == "Zijkant"

    herstarte_projecten.archiveren(project.id)
    herstart_proj_verbinding.close()
    herstart_mod_verbinding.close()
    herstart_mat_verbinding.close()
