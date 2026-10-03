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
from robocutter.projecten.zaagplannen import ZaagplanVoortgang, genereer_zaagplannen_voor_project


def _materiaal(**overrides) -> Materiaal:
    basis = dict(
        id="", naam="Eiken multiplex 18mm", type=MateriaalType.PLAAT,
        lengte=2800, breedte=2070, derde_afmeting=18, min_reststukgrootte=300,
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

    plannen, waarschuwingen = genereer_zaagplannen_voor_project(project, materialen, strategie="horizontaal")

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
    hout = materialen.toevoegen(_materiaal(lengte=2800, breedte=2070))
    # Elke plaat heeft plek voor 2 stukken van 1398x2070 (met tussenruimte net
    # geen 2800) -- 5 stuks moeten dus over meerdere platen verdeeld worden.
    project = projecten.toevoegen(
        Project(
            id="", naam="Test", klant="Test",
            losse_onderdelen=[_onderdeel(hout.id, naam="Paneel", breedte=1398, hoogte=2070, aantal=5)],
        )
    )

    plannen, waarschuwingen = genereer_zaagplannen_voor_project(project, materialen, strategie="horizontaal")

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


def test_reden_voor_geeft_uitleg_voor_een_te_groot_onderdeel():
    materialen, projecten = _bibliotheken()
    hout = materialen.toevoegen(_materiaal(lengte=1000, breedte=1000))
    project = projecten.toevoegen(
        Project(
            id="", naam="Test", klant="Test",
            losse_onderdelen=[
                _onderdeel(hout.id, naam="Te groot paneel", breedte=5000, hoogte=5000, aantal=1),
            ],
        )
    )

    plannen, _ = genereer_zaagplannen_voor_project(project, materialen)
    plan = plannen[0]
    assert plan.resultaat.niet_geplaatst == ["r0#1"]
    assert "te groot" in plan.reden_voor("r0#1")
    assert plan.reden_voor("onbestaande#1") == ""


def test_voortgang_over_meerdere_materialen_loopt_op_tot_een():
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
    meldingen: list[ZaagplanVoortgang] = []

    genereer_zaagplannen_voor_project(
        project, materialen, strategie="horizontaal",
        zoek_tijdsbudget=1.0, min_zoek_tijdsbudget=0.25, voortgang=meldingen.append,
    )

    fracties = [m.fractie for m in meldingen]
    assert fracties == sorted(fracties)
    assert fracties[-1] == 1.0
    assert {m.materiaal_nummer for m in meldingen} == {1, 2}
    assert all(m.materiaal_totaal == 2 for m in meldingen)
    # Halverwege (na het eerste materiaal) nog niet klaar.
    assert max(m.fractie for m in meldingen if m.materiaal_nummer == 1) < 1.0


def test_zaagsnede_komt_uit_de_instellingen():
    materialen, projecten = _bibliotheken()
    hout = materialen.toevoegen(_materiaal())
    project = projecten.toevoegen(
        Project(id="", naam="Test", klant="Test", losse_onderdelen=[_onderdeel(hout.id, breedte=400, hoogte=300)])
    )

    plannen, _ = genereer_zaagplannen_voor_project(project, materialen, strategie="guillotine", zaagsnede=3)

    assert plannen[0].resultaat.materiaal.kerf == 3


# ---------------------------------------------------------------------------
# Reststukken uit de bibliotheek eerst, kleinste eerst, zonder randafzaag
# ---------------------------------------------------------------------------


def _reststuk(materiaal_id: str, rid: str, lengte: float, breedte: float):
    from robocutter.reststukken.models import Reststuk

    return Reststuk(id=rid, materiaal_id=materiaal_id, lengte=lengte, breedte=breedte)


def test_reststukken_gaan_voor_volle_platen_kleinste_eerst():
    materialen, projecten = _bibliotheken()
    hout = materialen.toevoegen(_materiaal(randafzaag_marge=10))
    ander = materialen.toevoegen(_materiaal(naam="MDF"))
    project = projecten.toevoegen(
        Project(
            id="", naam="Test", klant="Test",
            losse_onderdelen=[_onderdeel(hout.id, naam="Plankje", breedte=400, hoogte=300, aantal=2)],
        )
    )
    reststukken = [
        _reststuk(hout.id, "groot", 1200, 800),
        _reststuk(hout.id, "klein", 900, 320),
        _reststuk(ander.id, "ander-materiaal", 450, 350),
    ]

    plannen, _ = genereer_zaagplannen_voor_project(project, materialen, reststukken=reststukken)

    # Beide plankjes passen naast elkaar op het kleine reststuk: geen volle
    # plaat en het grote reststuk blijft liggen.
    assert [p.reststuk_id for p in plannen] == ["klein"]
    plan = plannen[0]
    assert plan.is_reststuk
    assert (plan.resultaat.materiaal.lengte, plan.resultaat.materiaal.breedte) == (900, 320)
    assert plan.resultaat.materiaal.randafzaag_marge == 0
    assert len(plan.resultaat.plaatsingen) == 2


def test_wat_niet_op_reststukken_past_gaat_naar_een_volle_plaat():
    materialen, projecten = _bibliotheken()
    hout = materialen.toevoegen(_materiaal())
    project = projecten.toevoegen(
        Project(
            id="", naam="Test", klant="Test",
            losse_onderdelen=[
                _onderdeel(hout.id, naam="Klein", breedte=400, hoogte=300, aantal=1),
                _onderdeel(hout.id, naam="Groot", breedte=2000, hoogte=600, aantal=1),
            ],
        )
    )
    reststukken = [_reststuk(hout.id, "r1", 500, 400), _reststuk(hout.id, "te-klein", 200, 200)]

    plannen, _ = genereer_zaagplannen_voor_project(project, materialen, reststukken=reststukken)

    assert [p.reststuk_id for p in plannen] == ["r1", None]
    assert plannen[0].onderdeel_info[plannen[0].resultaat.plaatsingen[0].onderdeel_id].naam == "Klein"
    volle = plannen[1]
    assert not volle.is_reststuk and volle.plaat_nummer == 1 and volle.platen_totaal == 1
    assert [volle.naam_voor(p.onderdeel_id) for p in volle.resultaat.plaatsingen] == ["Groot"]
    assert not volle.resultaat.niet_geplaatst


def test_zonder_reststukken_ongewijzigd():
    materialen, projecten = _bibliotheken()
    hout = materialen.toevoegen(_materiaal())
    project = projecten.toevoegen(
        Project(id="", naam="Test", klant="Test", losse_onderdelen=[_onderdeel(hout.id, aantal=3)])
    )
    met_leeg, _ = genereer_zaagplannen_voor_project(project, materialen, reststukken=[])
    zonder, _ = genereer_zaagplannen_voor_project(project, materialen)
    assert [p.reststuk_id for p in met_leeg] == [None] * len(zonder)
    assert [len(p.resultaat.plaatsingen) for p in met_leeg] == [len(p.resultaat.plaatsingen) for p in zonder]


def test_onderdeel_met_fabrieksrand_gaat_nooit_op_een_reststuk():
    from robocutter.modellen.models import Rand

    materialen, projecten = _bibliotheken()
    hout = materialen.toevoegen(_materiaal(fabriekskantenband_randen=frozenset({Rand.ONDER})))
    project = projecten.toevoegen(
        Project(
            id="", naam="Test", klant="Test",
            losse_onderdelen=[
                _onderdeel(hout.id, naam="Fabriek", breedte=400, hoogte=300, fabriekskantenband_vereist=True),
                _onderdeel(hout.id, naam="Groep A", breedte=400, hoogte=200, groep_id="g", groep_volgorde=1),
                _onderdeel(hout.id, naam="Groep B", breedte=400, hoogte=200, groep_id="g", groep_volgorde=2,
                           fabriekskantenband_vereist=True),
                _onderdeel(hout.id, naam="Gewoon", breedte=400, hoogte=300),
            ],
        )
    )
    plannen, _ = genereer_zaagplannen_voor_project(
        project, materialen, reststukken=[_reststuk(hout.id, "r", 1500, 1000)]
    )
    rest = [p for p in plannen if p.is_reststuk]
    assert len(rest) == 1
    assert {rest[0].naam_voor(p.onderdeel_id) for p in rest[0].resultaat.plaatsingen} == {"Gewoon"}
    volle = [p for p in plannen if not p.is_reststuk]
    assert {volle[0].naam_voor(p.onderdeel_id) for p in volle[0].resultaat.plaatsingen} == {"Fabriek", "Groep A", "Groep B"}


def test_reststuk_met_fabrieksrand_neemt_fabrieksrand_onderdeel_aan():
    from robocutter.modellen.models import Rand

    materialen, projecten = _bibliotheken()
    hout = materialen.toevoegen(_materiaal(fabriekskantenband_randen=frozenset({Rand.ONDER, Rand.BOVEN})))
    project = projecten.toevoegen(
        Project(
            id="", naam="Test", klant="Test",
            losse_onderdelen=[
                _onderdeel(hout.id, naam="Fabriek", breedte=400, hoogte=300, fabriekskantenband_vereist=True),
            ],
        )
    )
    met_rand = _reststuk(hout.id, "met-rand", 1500, 1000)
    met_rand.fabriekskantenband_randen = frozenset({Rand.ONDER})
    zonder_rand = _reststuk(hout.id, "zonder-rand", 600, 500)  # kleiner, dus eerst geprobeerd

    plannen, _ = genereer_zaagplannen_voor_project(project, materialen, reststukken=[zonder_rand, met_rand])

    assert [p.reststuk_id for p in plannen] == ["met-rand"]
    plaatsing = plannen[0].resultaat.plaatsingen[0]
    assert plaatsing.y == 0  # tegen de fabrieksrand ONDER
