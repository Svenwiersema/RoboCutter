"""Tests voor robocutter.projecten.zaagplannen: het groeperen van de
zaaglijst per materiaal en het aanroepen van de optimalisatie-motor
per groep.
"""

from __future__ import annotations

from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.materialen.models import Materiaal, MateriaalType
from robocutter.modellen.models import ModelOnderdeel
from robocutter.projecten.bibliotheek import ProjectenBibliotheek
from robocutter.projecten.models import Project
from robocutter.projecten.zaagplannen import genereer_zaagplannen_voor_project


def _materiaal(**overrides) -> Materiaal:
    basis = dict(
        id="", naam="Eiken multiplex 18mm", type=MateriaalType.PLAAT,
        lengte=2800, breedte=2070, derde_afmeting=18, kerf=4, min_reststukgrootte=300,
    )
    basis.update(overrides)
    return Materiaal(**basis)


def _onderdeel(materiaal_id: str, **overrides) -> ModelOnderdeel:
    basis = dict(id="", naam="Zijkant", materiaal_id=materiaal_id, breedte=600, hoogte=720, aantal=1)
    basis.update(overrides)
    return ModelOnderdeel(**basis)


def _bibliotheken() -> tuple[MaterialenBibliotheek, ProjectenBibliotheek]:
    materialen = MaterialenBibliotheek()
    from robocutter.modellen.bibliotheek import ModellenBibliotheek

    modellen = ModellenBibliotheek(materialen)
    projecten = ProjectenBibliotheek(modellen, materialen)
    return materialen, projecten


def test_genereert_een_plaat_per_materiaal_in_de_zaaglijst():
    materialen, projecten = _bibliotheken()
    hout = materialen.toevoegen(_materiaal(naam="Eiken multiplex"))
    wit = materialen.toevoegen(_materiaal(naam="Wit gemelamineerd"))
    project = projecten.toevoegen(
        Project(
            id="", naam="Test", klant="Test",
            losse_onderdelen=[
                _onderdeel(hout.id, naam="Zijkant", breedte=600, hoogte=720, aantal=2),
                _onderdeel(wit.id, naam="Deur", breedte=300, hoogte=700, aantal=4),
            ],
        )
    )

    plannen, waarschuwingen = genereer_zaagplannen_voor_project(project, materialen, strategie="rijen")

    assert waarschuwingen == []
    assert {p.materiaal_naam for p in plannen} == {"Eiken multiplex", "Wit gemelamineerd"}
    hout_plan = next(p for p in plannen if p.materiaal_id == hout.id)
    assert len(hout_plan.resultaat.plaatsingen) == 2
    assert hout_plan.resultaat.niet_geplaatst == []


def test_onbekend_materiaal_wordt_overgeslagen_met_waarschuwing():
    # Simuleert een materiaal dat ná het toevoegen aan het project weer
    # definitief verwijderd is uit de bibliotheek (valideer() blokkeert
    # een project met een materiaal dat al bij het toevoegen onbekend is,
    # dus dit scenario kan alleen zo ontstaan).
    materialen, projecten = _bibliotheken()
    materiaal = materialen.toevoegen(_materiaal())
    project = projecten.toevoegen(
        Project(
            id="", naam="Test", klant="Test",
            losse_onderdelen=[_onderdeel(materiaal.id, naam="Plank", breedte=500, hoogte=500)],
        )
    )
    materialen.archiveren(materiaal.id)
    materialen.verwijderen_definitief(materiaal.id)

    plannen, waarschuwingen = genereer_zaagplannen_voor_project(project, materialen)

    assert plannen == []
    assert len(waarschuwingen) == 1
    assert materiaal.id in waarschuwingen[0]


def test_meerdere_platen_voor_een_materiaal_krijgen_elk_een_eigen_plaatzaagplan():
    materialen, projecten = _bibliotheken()
    hout = materialen.toevoegen(_materiaal(lengte=2800, breedte=2070, kerf=4))
    # Elke plaat heeft plek voor 2 stukken van 1398x2070 (met kerf net
    # geen 2800) -- 5 stuks moeten dus over meerdere platen verdeeld worden.
    project = projecten.toevoegen(
        Project(
            id="", naam="Test", klant="Test",
            losse_onderdelen=[_onderdeel(hout.id, naam="Paneel", breedte=1398, hoogte=2070, aantal=5)],
        )
    )

    plannen, waarschuwingen = genereer_zaagplannen_voor_project(project, materialen, strategie="efficient")

    assert waarschuwingen == []
    hout_plannen = [p for p in plannen if p.materiaal_id == hout.id]
    assert len(hout_plannen) > 1
    assert [p.plaat_nummer for p in hout_plannen] == list(range(1, len(hout_plannen) + 1))
    assert all(p.platen_totaal == len(hout_plannen) for p in hout_plannen)
    assert sum(len(p.resultaat.plaatsingen) for p in hout_plannen) == 5
    assert hout_plannen[-1].resultaat.niet_geplaatst == []


def test_naam_voor_zoekt_zowel_losse_als_groep_units_op():
    materialen, projecten = _bibliotheken()
    hout = materialen.toevoegen(_materiaal())
    project = projecten.toevoegen(
        Project(
            id="", naam="Test", klant="Test",
            losse_onderdelen=[
                _onderdeel(hout.id, naam="Ladefront", breedte=400, hoogte=180, groep_id="g1", groep_volgorde=1),
                _onderdeel(hout.id, naam="Ladefront 2", breedte=400, hoogte=180, groep_id="g1", groep_volgorde=2),
            ],
        )
    )

    plannen, _ = genereer_zaagplannen_voor_project(project, materialen)
    plan = plannen[0]
    # De groep wordt door de motor als één eenheid geplaatst -> een
    # niet-geplaatste groep heeft de vorm "groep:<id>", geen "#instantie".
    assert plan.naam_voor("r0#1") == "Ladefront"
    assert plan.naam_voor("groep:g1").startswith("Groep")
