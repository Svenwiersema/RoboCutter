"""Tests voor robocutter.projecten.project_reststukken: de tijdelijke
reststukkenlijst per project, gevuld uit het zaagplan en pas bij Afgerond
vrij te geven naar de Reststukkenbibliotheek.
"""

from __future__ import annotations

from datetime import date

import pytest

from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.materialen.models import Materiaal, MateriaalType
from robocutter.modellen.bibliotheek import ModellenBibliotheek
from robocutter.modellen.models import ModelOnderdeel
from robocutter.projecten import project_reststukken_opslag
from robocutter.projecten.bibliotheek import ProjectenBibliotheek
from robocutter.projecten.models import Project, ProjectStatus
from robocutter.projecten.project_reststukken import (
    AlVrijgegevenError,
    ProjectNietAfgerondError,
    ProjectReststukBron,
    ProjectReststukkenBibliotheek,
    ProjectReststukStatus,
)
from robocutter.projecten.zaagplannen import genereer_zaagplannen_voor_project
from robocutter.reststukken.bibliotheek import ReststukkenBibliotheek
from robocutter.reststukken.models import ReststukStatus


def _opzet(db=None):
    materialen = MaterialenBibliotheek()
    modellen = ModellenBibliotheek(materialen)
    projecten = ProjectenBibliotheek(modellen, materialen)
    reststukken = ReststukkenBibliotheek(materialen)
    hout = materialen.toevoegen(
        Materiaal(
            id="", naam="Eiken multiplex 18mm", type=MateriaalType.PLAAT,
            lengte=2800, breedte=2070, derde_afmeting=18, min_reststukgrootte=300,
        )
    )
    project = projecten.toevoegen(
        Project(
            id="", naam="Keuken Jansen", klant="Jansen",
            losse_onderdelen=[
                ModelOnderdeel(id="", naam="Zijkant", materiaal_id=hout.id, breedte=600, hoogte=720, aantal=2)
            ],
        )
    )
    plannen, _ = genereer_zaagplannen_voor_project(project, materialen, strategie="horizontaal")
    bib = ProjectReststukkenBibliotheek(materialen, reststukken, db)
    return bib, projecten, reststukken, project, plannen, hout


def test_overnemen_uit_zaagplan_maakt_een_record_per_reststuk():
    bib, _, _, project, plannen, hout = _opzet()
    verwacht = [r for p in plannen for r in p.resultaat.reststukken]
    assert verwacht, "testopzet moet minstens één reststuk opleveren"

    lijst = bib.overnemen_uit_zaagplan(project.id, plannen)

    assert len(lijst) == len(verwacht)
    assert [r.code for r in lijst] == [f"R{i}" for i in range(1, len(verwacht) + 1)]
    for item, rest in zip(lijst, verwacht):
        assert item.materiaal_id == hout.id
        assert (item.lengte, item.breedte) == (rest.breedte, rest.hoogte)
        assert (item.x, item.y) == (rest.x, rest.y)
        assert item.bron == ProjectReststukBron.ZAAGPLAN
        assert item.status == ProjectReststukStatus.BEWAREN
        assert item.plaat_nummer == 1 and item.plaat_lengte == 2800
        assert not item.is_aangepast


def test_opnieuw_overnemen_vervangt_zaagplanstukken_en_houdt_handmatige():
    bib, _, _, project, plannen, hout = _opzet()
    bib.overnemen_uit_zaagplan(project.id, plannen)
    handmatig = bib.toevoegen_handmatig(project.id, hout.id, 900, 450)
    eerste = bib.lijst(project.id)[0]
    bib.zet_status(eerste.id, ProjectReststukStatus.AFGESCHREVEN)

    lijst = bib.overnemen_uit_zaagplan(project.id, plannen)

    zaagplan = [r for r in lijst if r.bron == ProjectReststukBron.ZAAGPLAN]
    assert all(r.status == ProjectReststukStatus.BEWAREN for r in zaagplan)
    assert eerste.id not in {r.id for r in lijst}
    assert lijst[-1].id == handmatig.id
    assert lijst[-1].volgnummer == len(zaagplan) + 1


def test_handmatig_toevoegen_valideert():
    bib, _, _, project, _, hout = _opzet()
    with pytest.raises(ValueError):
        bib.toevoegen_handmatig(project.id, hout.id, 0, 450)
    with pytest.raises(ValueError):
        bib.toevoegen_handmatig(project.id, "bestaat-niet", 900, 450)
    assert bib.lijst(project.id) == []


def test_afmeting_aanpassen_bewaart_oorspronkelijke_maat():
    bib, _, _, project, plannen, _ = _opzet()
    item = bib.overnemen_uit_zaagplan(project.id, plannen)[0]
    oud = (item.lengte, item.breedte)

    bib.wijzig_afmeting(item.id, 500, 400)
    assert (item.lengte, item.breedte) == (500, 400)
    assert (item.oorspronkelijke_lengte, item.oorspronkelijke_breedte) == oud
    assert item.is_aangepast

    with pytest.raises(ValueError):
        bib.wijzig_afmeting(item.id, -1, 400)
    assert (item.lengte, item.breedte) == (500, 400)


def test_vrijgeven_kan_alleen_bij_afgerond():
    bib, _, reststukken, project, plannen, _ = _opzet()
    bib.overnemen_uit_zaagplan(project.id, plannen)
    with pytest.raises(ProjectNietAfgerondError):
        bib.vrijgeven(project)
    assert reststukken.lijst() == []
    assert not bib.is_vrijgegeven(project.id)


def test_vrijgeven_zet_alleen_bewaren_stukken_in_de_bibliotheek_en_sluit_af():
    bib, projecten, reststukken, project, plannen, hout = _opzet()
    lijst = bib.overnemen_uit_zaagplan(project.id, plannen)
    handmatig = bib.toevoegen_handmatig(project.id, hout.id, 900, 450)
    bib.toevoegen_handmatig(project.id, hout.id, 700, 350)
    weg = bib.toevoegen_handmatig(project.id, hout.id, 600, 300)
    bib.zet_status(weg.id, ProjectReststukStatus.HERGEBRUIKT)
    project = projecten.zet_status(project.id, ProjectStatus.AFGEROND)

    nieuw = bib.vrijgeven(project, op=date(2026, 10, 3))

    assert len(nieuw) == len(lijst) + 2
    assert all(r.status == ReststukStatus.BESCHIKBAAR for r in reststukken.lijst())
    assert all(r.herkomst_project == "Keuken Jansen" for r in nieuw)
    assert (900, 450) in {(r.lengte, r.breedte) for r in nieuw}
    assert (600, 300) not in {(r.lengte, r.breedte) for r in nieuw}
    assert bib.is_vrijgegeven(project.id)
    assert bib.vrijgegeven_op(project.id) == date(2026, 10, 3)

    with pytest.raises(AlVrijgegevenError):
        bib.vrijgeven(project)
    with pytest.raises(AlVrijgegevenError):
        bib.zet_status(handmatig.id, ProjectReststukStatus.AFGESCHREVEN)
    with pytest.raises(AlVrijgegevenError):
        bib.overnemen_uit_zaagplan(project.id, plannen)


def test_lijst_is_per_project():
    bib, projecten, _, project, plannen, hout = _opzet()
    ander = projecten.toevoegen(Project(id="", naam="Badkamer", klant="X"))
    bib.overnemen_uit_zaagplan(project.id, plannen)
    bib.toevoegen_handmatig(ander.id, hout.id, 900, 450)
    assert len(bib.lijst(ander.id)) == 1
    assert all(r.project_id == project.id for r in bib.lijst(project.id))


def test_opslag_overleeft_herstart(tmp_path):
    db_pad = tmp_path / "test.db"
    verbinding = project_reststukken_opslag.open_verbinding(db_pad)
    bib, projecten, reststukken, project, plannen, hout = _opzet(verbinding)
    lijst = bib.overnemen_uit_zaagplan(project.id, plannen)
    bib.wijzig_afmeting(lijst[0].id, 500, 400)
    handmatig = bib.toevoegen_handmatig(project.id, hout.id, 900, 450)
    bib.zet_status(handmatig.id, ProjectReststukStatus.AFGESCHREVEN)
    project = projecten.zet_status(project.id, ProjectStatus.AFGEROND)
    bib.vrijgeven(project, op=date(2026, 10, 3))
    verbinding.close()

    tweede = project_reststukken_opslag.open_verbinding(db_pad)
    herladen = ProjectReststukkenBibliotheek(MaterialenBibliotheek(), ReststukkenBibliotheek(MaterialenBibliotheek()), tweede)
    voor = {r.id: r for r in bib.lijst(project.id)}
    na = {r.id: r for r in herladen.lijst(project.id)}
    assert voor == na
    assert na[handmatig.id].status == ProjectReststukStatus.AFGESCHREVEN
    assert na[lijst[0].id].is_aangepast
    assert herladen.is_vrijgegeven(project.id)
    tweede.close()


def test_stukken_van_een_bibliotheek_reststuk_worden_herkend_en_bewaard(tmp_path):
    from robocutter.projecten.zaagplannen_opslag import ZaagplannenOpslag
    from robocutter.projecten.zaagplannen_opslag import open_verbinding as open_zaagplannen
    from robocutter.reststukken.models import Reststuk

    db_pad = tmp_path / "test.db"
    verbinding = project_reststukken_opslag.open_verbinding(db_pad)
    bib, _, _, project, _, hout = _opzet(verbinding)
    groot_reststuk = Reststuk(id="lib1", materiaal_id=hout.id, lengte=2000, breedte=1500)
    plannen, _ = genereer_zaagplannen_voor_project(
        project, _materialen_van(bib),
        strategie="horizontaal", reststukken=[groot_reststuk],
    )
    assert plannen[0].reststuk_id == "lib1"

    lijst = bib.overnemen_uit_zaagplan(project.id, plannen)
    assert lijst and all(r.uit_bibliotheek_reststuk for r in lijst)
    assert all(r.plaat_lengte == 2000 for r in lijst)

    zaagplannen = ZaagplannenOpslag(open_zaagplannen(db_pad))
    zaagplannen.opslaan(project.id, plannen, [], "horizontaal")
    herladen_plannen, _, _ = zaagplannen.laad(project.id)
    assert herladen_plannen[0].reststuk_id == "lib1"
    verbinding.close()

    herladen = ProjectReststukkenBibliotheek(
        MaterialenBibliotheek(), ReststukkenBibliotheek(MaterialenBibliotheek()),
        project_reststukken_opslag.open_verbinding(db_pad),
    )
    assert all(r.uit_bibliotheek_reststuk for r in herladen.lijst(project.id))


def _materialen_van(bib: ProjectReststukkenBibliotheek) -> MaterialenBibliotheek:
    return bib._materialen


def test_fabrieksranden_gaan_mee_naar_projectlijst_en_bibliotheek(tmp_path):
    from robocutter.optimalisatie.models import Rand

    materialen = MaterialenBibliotheek()
    modellen = ModellenBibliotheek(materialen)
    projecten = ProjectenBibliotheek(modellen, materialen)
    reststukken = ReststukkenBibliotheek(materialen)
    paneel = materialen.toevoegen(
        Materiaal(
            id="", naam="Meubelpaneel wit 18", type=MateriaalType.PLAAT, lengte=2800, breedte=600,
            derde_afmeting=18, min_reststukgrootte=150,
            fabriekskantenband_randen=frozenset({Rand.ONDER, Rand.BOVEN}),
        )
    )
    project = projecten.toevoegen(
        Project(
            id="", naam="Kast", klant="X",
            losse_onderdelen=[ModelOnderdeel(id="", naam="Zijkant", materiaal_id=paneel.id, breedte=800, hoogte=600)],
        )
    )
    plannen, _ = genereer_zaagplannen_voor_project(project, materialen, strategie="horizontaal")
    db_pad = tmp_path / "t.db"
    bib = ProjectReststukkenBibliotheek(materialen, reststukken, project_reststukken_opslag.open_verbinding(db_pad))
    lijst = bib.overnemen_uit_zaagplan(project.id, plannen)

    # Het stuk naast de zijkant loopt over de volle plaatbreedte: beide
    # fabrieksranden blijven.
    assert any(r.fabriekskantenband_randen == {Rand.ONDER, Rand.BOVEN} for r in lijst)
    herladen = ProjectReststukkenBibliotheek(
        materialen, reststukken, project_reststukken_opslag.open_verbinding(db_pad)
    ).lijst(project.id)
    assert [r.fabriekskantenband_randen for r in herladen] == [r.fabriekskantenband_randen for r in lijst]

    project = projecten.zet_status(project.id, ProjectStatus.AFGEROND)
    nieuw = bib.vrijgeven(project)
    assert {r.fabriekskantenband_randen for r in nieuw} == {r.fabriekskantenband_randen for r in lijst}
