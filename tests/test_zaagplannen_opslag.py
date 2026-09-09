"""Tests voor robocutter.projecten.zaagplannen_opslag: het bewaren van
het laatst gegenereerde zaagplan van een project, en het herladen ervan
alsof de app opnieuw is opgestart (nieuwe SQLite-verbinding op hetzelfde
bestand, zelfde patroon als de andere opslag-tests)."""

from __future__ import annotations

from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.materialen.models import Materiaal, MateriaalType
from robocutter.modellen.models import ModelOnderdeel, Rand
from robocutter.projecten.bibliotheek import ProjectenBibliotheek
from robocutter.projecten.models import Project
from robocutter.projecten.zaagplannen import genereer_zaagplannen_voor_project
from robocutter.projecten.zaagplannen_opslag import ZaagplannenOpslag, open_verbinding


def _materiaal(**overrides) -> Materiaal:
    basis = dict(
        id="", naam="Eiken multiplex 18mm", type=MateriaalType.PLAAT,
        lengte=2800, breedte=2070, derde_afmeting=18, kerf=4, min_reststukgrootte=300,
        fabriekskantenband_randen=frozenset({Rand.LINKS}),
    )
    basis.update(overrides)
    return Materiaal(**basis)


def _project_met_zaagplan() -> tuple[list, list, MaterialenBibliotheek]:
    materialen = MaterialenBibliotheek()
    from robocutter.modellen.bibliotheek import ModellenBibliotheek

    modellen = ModellenBibliotheek(materialen)
    projecten = ProjectenBibliotheek(modellen, materialen)
    hout = materialen.toevoegen(_materiaal())
    project = projecten.toevoegen(
        Project(
            id="", naam="Test", klant="Test",
            losse_onderdelen=[
                ModelOnderdeel(
                    id="", naam="Zijkant", materiaal_id=hout.id, breedte=600, hoogte=720, aantal=2,
                    fabriekskantenband_vereist=True, kantenband_randen=frozenset({Rand.BOVEN}),
                ),
            ],
        )
    )
    plannen, waarschuwingen = genereer_zaagplannen_voor_project(project, materialen, strategie="rijen")
    return plannen, waarschuwingen, project


def test_sqlite_opslag_overleeft_herstart(tmp_path):
    db_pad = tmp_path / "zaagplannen.db"
    plannen, waarschuwingen, project = _project_met_zaagplan()
    assert plannen and plannen[0].resultaat.plaatsingen

    verbinding = open_verbinding(db_pad)
    opslag = ZaagplannenOpslag(verbinding)
    opslag.opslaan(project.id, plannen, waarschuwingen, "rijen")
    verbinding.close()

    # Nieuwe verbinding simuleert een herstart van de app.
    herstart_verbinding = open_verbinding(db_pad)
    herstarte_opslag = ZaagplannenOpslag(herstart_verbinding)
    geladen = herstarte_opslag.laad(project.id)
    assert geladen is not None
    herladen_plannen, herladen_waarschuwingen, herladen_strategie = geladen

    assert herladen_strategie == "rijen"
    assert herladen_waarschuwingen == waarschuwingen
    assert len(herladen_plannen) == len(plannen)
    origineel, herladen = plannen[0], herladen_plannen[0]
    assert herladen.materiaal_id == origineel.materiaal_id
    assert herladen.materiaal_naam == origineel.materiaal_naam
    assert herladen.plaat_nummer == origineel.plaat_nummer
    assert herladen.platen_totaal == origineel.platen_totaal
    assert herladen.onderdeel_info.keys() == origineel.onderdeel_info.keys()
    for oid, info in origineel.onderdeel_info.items():
        herladen_info = herladen.onderdeel_info[oid]
        assert herladen_info.naam == info.naam
        assert herladen_info.herkomst == info.herkomst
        assert herladen_info.kantenband_randen == info.kantenband_randen
        assert herladen_info.fabriekskantenband_vereist == info.fabriekskantenband_vereist

    r1, r2 = origineel.resultaat, herladen.resultaat
    assert r2.strategie == r1.strategie
    assert r2.afval_oppervlak == r1.afval_oppervlak
    assert r2.niet_geplaatst == r1.niet_geplaatst
    assert r2.materiaal == r1.materiaal
    assert r2.plaatsingen == r1.plaatsingen
    assert r2.zaagvolgorde == r1.zaagvolgorde
    assert r2.reststukken == r1.reststukken

    herstart_verbinding.close()


def test_laad_geeft_none_als_er_niets_is_opgeslagen(tmp_path):
    verbinding = open_verbinding(tmp_path / "leeg.db")
    opslag = ZaagplannenOpslag(verbinding)
    assert opslag.laad("onbekend-project-id") is None
    verbinding.close()


def test_opslaan_overschrijft_het_vorige_zaagplan_van_hetzelfde_project(tmp_path):
    verbinding = open_verbinding(tmp_path / "overschrijven.db")
    opslag = ZaagplannenOpslag(verbinding)
    plannen, waarschuwingen, project = _project_met_zaagplan()

    opslag.opslaan(project.id, plannen, waarschuwingen, "rijen")
    opslag.opslaan(project.id, plannen, waarschuwingen, "efficient")

    geladen = opslag.laad(project.id)
    assert geladen is not None
    assert geladen[2] == "efficient"
    aantal_rijen = verbinding.execute("SELECT COUNT(*) AS n FROM zaagplannen").fetchone()["n"]
    assert aantal_rijen == 1
    verbinding.close()


def test_verwijderen_maakt_laad_weer_none(tmp_path):
    verbinding = open_verbinding(tmp_path / "verwijderen.db")
    opslag = ZaagplannenOpslag(verbinding)
    plannen, waarschuwingen, project = _project_met_zaagplan()
    opslag.opslaan(project.id, plannen, waarschuwingen, "rijen")
    assert opslag.laad(project.id) is not None

    opslag.verwijderen(project.id)

    assert opslag.laad(project.id) is None
    verbinding.close()
