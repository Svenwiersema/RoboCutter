"""Tests voor zaagplan bijwerken tijdens productie (zaagplan_bijwerken.py)."""

from __future__ import annotations

from collections import Counter

from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.materialen.models import Materiaal, MateriaalType
from robocutter.modellen.bibliotheek import ModellenBibliotheek
from robocutter.modellen.models import Model, ModelOnderdeel
from robocutter.projecten.bibliotheek import ProjectenBibliotheek
from robocutter.projecten.labels import genereer_labels_voor_project
from robocutter.projecten.models import Project
from robocutter.projecten.zaaglijst import bouw_zaaglijst
from robocutter.projecten.zaagplan_bijwerken import (
    _plaatsing_sleutel,
    _regel_sleutel,
    stel_bijwerking_voor,
    werk_zaagplannen_bij,
)
from robocutter.projecten.zaagplannen import genereer_zaagplannen_voor_project
from robocutter.projecten.zaagplannen_opslag import ZaagplannenOpslag, open_verbinding


def _opzet(aantal_kasten=6):
    materialen = MaterialenBibliotheek()
    modellen = ModellenBibliotheek(materialen)
    projecten = ProjectenBibliotheek(modellen, materialen)
    wit = materialen.toevoegen(
        Materiaal(id="", naam="Wit 18", type=MateriaalType.PLAAT, lengte=2800, breedte=2070, derde_afmeting=18)
    )
    kast = modellen.toevoegen(
        Model(
            id="",
            naam="Onderkast",
            onderdelen=[
                ModelOnderdeel(id="z", naam="Zijwand", materiaal_id=wit.id, breedte=720, hoogte=560, aantal=2),
                ModelOnderdeel(id="b", naam="Bodem", materiaal_id=wit.id, breedte=564, hoogte=540),
            ],
        )
    )
    project = projecten.toevoegen(Project(id="", naam="Keuken", klant="Jansen"))
    projecten.model_toevoegen(project.id, kast.id, aantal=aantal_kasten)
    project = projecten.ophalen(project.id)
    plannen, _ = genereer_zaagplannen_voor_project(project, materialen, revisie="Rev A")
    return materialen, projecten, project, wit, plannen


def _zet_aantal(projecten, project, aantal):
    project = projecten.ophalen(project.id)
    project.modelinstanties[0].aantal = aantal
    projecten.bijwerken(project)
    return projecten.ophalen(project.id)


def _vraag(project) -> Counter:
    c = Counter()
    for regel in bouw_zaaglijst(project):
        c[_regel_sleutel(regel)] += regel.onderdeel.aantal
    return c


def _geplaatst(plannen) -> Counter:
    c = Counter()
    for plan in plannen:
        for p in plan.resultaat.plaatsingen:
            c[_plaatsing_sleutel(plan, p)] += 1
    return c


def _overlapt(plan) -> bool:
    stukken = [(p.x, p.y, p.breedte, p.hoogte) for p in plan.resultaat.plaatsingen]
    stukken += [(r.x, r.y, r.breedte, r.hoogte) for r in plan.resultaat.reststukken]
    mat = plan.resultaat.materiaal
    for i, (x, y, b, h) in enumerate(stukken):
        if x < -0.01 or y < -0.01 or x + b > mat.lengte + 0.01 or y + h > mat.breedte + 0.01:
            return True
        for x2, y2, b2, h2 in stukken[i + 1 :]:
            if x < x2 + b2 - 0.01 and x2 < x + b - 0.01 and y < y2 + h2 - 0.01 and y2 < y + h - 0.01:
                return True
    return False


def _markeer(plan, aantal):
    for p in plan.resultaat.plaatsingen[:aantal]:
        plan.gezaagd.add((p.onderdeel_id, p.instantie))


def test_zonder_gezaagd_is_bijwerken_niet_nodig():
    _, _, project, _, plannen = _opzet()
    assert not stel_bijwerking_voor(project, plannen).is_mogelijk


def test_aangezaagde_plaat_blijft_staan_en_de_rest_wordt_opnieuw_verdeeld():
    materialen, projecten, project, _, plannen = _opzet(aantal_kasten=6)
    assert len(plannen) >= 2
    eerste = plannen[0]
    _markeer(eerste, 2)
    oud_eerste = [(p.onderdeel_id, p.instantie, p.x, p.y) for p in eerste.resultaat.plaatsingen]
    project = _zet_aantal(projecten, project, 7)

    voorstel = stel_bijwerking_voor(project, plannen)
    assert [b.plan_index for b in voorstel.blijvend] == [0]
    assert voorstel.blijvend[0].gezaagd == 2
    assert voorstel.erbij and not voorstel.eraf and not voorstel.overbodig_gezaagd

    res = werk_zaagplannen_bij(project, plannen, materialen, revisie="Rev B")
    gebleven = [p for p in res.plannen if p.bijwerking == "gebleven"]
    assert len(gebleven) == 1 and gebleven[0].plaat_nummer == eerste.plaat_nummer
    # Alles wat er stond, staat er nog op dezelfde plek, gezaagd blijft gezaagd.
    nu = {(p.onderdeel_id, p.instantie, p.x, p.y) for p in gebleven[0].resultaat.plaatsingen}
    assert set(oud_eerste) <= nu
    assert gebleven[0].gezaagd == eerste.gezaagd
    assert all(p.bijwerking == "nieuw" and p.revisie == "Rev B" for p in res.plannen if p is not gebleven[0])
    # Precies de nieuwe samenstelling, niets dubbel, niets overlapt.
    assert _geplaatst(res.plannen) == _vraag(project)
    assert not any(_overlapt(p) for p in res.plannen)
    # Nummering per materiaal 1..n zonder gaten.
    assert sorted(p.plaat_nummer for p in res.plannen if not p.is_reststuk) == list(
        range(1, sum(1 for p in res.plannen if not p.is_reststuk) + 1)
    )
    # Labels: blijvende platen houden hun scancodes, alles uniek.
    oude_codes = {l.scancode_waarde for l in genereer_labels_voor_project(project, [eerste])}
    codes = [l.scancode_waarde for l in genereer_labels_voor_project(project, res.plannen)]
    assert len(codes) == len(set(codes))
    assert oude_codes <= set(codes)
    # Origineel ongewijzigd.
    assert [(p.onderdeel_id, p.instantie, p.x, p.y) for p in plannen[0].resultaat.plaatsingen] == oud_eerste


def test_gezaagd_maar_niet_meer_nodig_en_vrijgekomen_plek():
    materialen, projecten, project, _, plannen = _opzet(aantal_kasten=6)
    # Een plaat met zijwanden én bodems: alle zijwanden gezaagd, de bodems niet.
    eerste = next(
        plan for plan in plannen
        if {plan.onderdeel_info[p.onderdeel_id].naam for p in plan.resultaat.plaatsingen} == {"Zijwand", "Bodem"}
    )
    for p in eerste.resultaat.plaatsingen:
        if eerste.onderdeel_info[p.onderdeel_id].naam == "Zijwand":
            eerste.gezaagd.add((p.onderdeel_id, p.instantie))
    zijwanden_op_1 = len(eerste.gezaagd)
    bodems_op_1 = len(eerste.resultaat.plaatsingen) - zijwanden_op_1
    assert zijwanden_op_1 >= 2 and bodems_op_1 >= 1
    # Nog maar één kast: 2 zijwanden + 1 bodem nodig.
    project = _zet_aantal(projecten, project, 1)

    voorstel = stel_bijwerking_voor(project, plannen)
    assert len(voorstel.overbodig_gezaagd) == zijwanden_op_1 - 2
    assert all(s.gezaagd and s.naam == "Zijwand" for s in voorstel.overbodig_gezaagd)
    assert len(voorstel.vervallen_niet_gezaagd) == bodems_op_1 - 1
    assert len(voorstel.bruikbare_reststukken) >= len(voorstel.vervallen_niet_gezaagd)
    assert any("vrijgekomen" in naam for naam, _, _ in voorstel.bruikbare_reststukken)

    res = werk_zaagplannen_bij(project, plannen, materialen, revisie="Rev B")
    assert len(res.overbodig_gezaagd) == zijwanden_op_1 - 2
    assert _geplaatst(res.plannen) == _vraag(project)
    assert len(res.plannen) == 1  # de andere platen vervallen
    assert res.vervallen_platen
    assert all(v.revisie == "Rev B" and not v.is_reststuk for v in res.vervallen_platen)
    assert {v.plaat_nummer for v in res.vervallen_platen}.isdisjoint({res.plannen[0].plaat_nummer})
    plaat = res.plannen[0]
    assert len(plaat.gezaagd) == 2
    assert not _overlapt(plaat)


def test_nieuwe_onderdelen_gaan_eerst_in_een_reststuk_van_de_blijvende_plaat():
    materialen, projecten, project, wit, plannen = _opzet(aantal_kasten=1)
    assert len(plannen) == 1 and plannen[0].resultaat.reststukken
    _markeer(plannen[0], 1)
    project = projecten.ophalen(project.id)
    projecten.los_onderdeel_toevoegen(
        project.id, ModelOnderdeel(id="", naam="Passtuk", materiaal_id=wit.id, breedte=300, hoogte=200)
    )
    project = projecten.ophalen(project.id)

    res = werk_zaagplannen_bij(project, plannen, materialen, revisie="Rev B")
    assert len(res.plannen) == 1
    plaat = res.plannen[0]
    assert plaat.bijwerking == "gebleven" and len(plaat.toegevoegd) == 1
    assert plaat.is_nieuw_bij_bijwerking and plaat.revisie == "Rev B"
    assert _geplaatst(res.plannen) == _vraag(project)
    assert not _overlapt(plaat)
    # Nieuwe zaagsnedes komen na de bestaande, en de plaat is nog gewoon op
    # de paneelzaag te zagen.
    nummers = [s.volgnummer for s in plaat.resultaat.zaagvolgorde]
    assert nummers == sorted(nummers) and len(set(nummers)) == len(nummers)
    from tests.test_engine import _geldig_zaagplan, _paneelzaag_fouten

    _geldig_zaagplan(plaat.resultaat, plaat.resultaat.materiaal)
    assert _paneelzaag_fouten(plaat.resultaat) == []


def test_bruikbaar_sluit_reststukken_uit():
    materialen, projecten, project, wit, plannen = _opzet(aantal_kasten=1)
    _markeer(plannen[0], 1)
    project = projecten.ophalen(project.id)
    projecten.los_onderdeel_toevoegen(
        project.id, ModelOnderdeel(id="", naam="Passtuk", materiaal_id=wit.id, breedte=300, hoogte=200)
    )
    project = projecten.ophalen(project.id)
    res = werk_zaagplannen_bij(project, plannen, materialen, revisie="Rev B", bruikbaar=lambda plan, r: False)
    assert [p.bijwerking for p in res.plannen] == ["gebleven", "nieuw"]
    assert [p.plaat_nummer for p in res.plannen] == [1, 2]


def test_nieuwe_velden_overleven_opslaan(tmp_path):
    materialen, projecten, project, _, plannen = _opzet(aantal_kasten=1)
    _markeer(plannen[0], 2)
    plannen[0].bijwerking = "gebleven"
    plannen[0].toegevoegd = {("x1", 1)}
    db = tmp_path / "rc.db"
    ZaagplannenOpslag(open_verbinding(db)).opslaan(project.id, plannen, [], "horizontaal", bron=project, revisie="Rev A")
    opslag2 = ZaagplannenOpslag(open_verbinding(db))
    terug, _, _ = opslag2.laad(project.id)
    assert terug[0].gezaagd == plannen[0].gezaagd
    assert terug[0].revisie == "Rev A" and terug[0].bijwerking == "gebleven" and terug[0].toegevoegd == {("x1", 1)}
    # werk_plannen_bij laat de herkomst staan.
    terug[0].gezaagd = set()
    opslag2.werk_plannen_bij(project.id, terug)
    opslag3 = ZaagplannenOpslag(open_verbinding(db))
    assert opslag3.laad(project.id)[0][0].gezaagd == set()
    assert opslag3.laad_herkomst(project.id).revisie == "Rev A"


def test_willekeurige_bijwerkingen_blijven_zaagbaar():
    import random

    from tests.test_engine import _geldig_zaagplan, _paneelzaag_fouten

    for seed in range(12):
        rng = random.Random(seed)
        materialen, projecten, project, wit, plannen = _opzet(aantal_kasten=rng.randint(1, 8))
        for plan in plannen:
            for p in plan.resultaat.plaatsingen:
                if rng.random() < 0.3:
                    plan.gezaagd.add((p.onderdeel_id, p.instantie))
        project = _zet_aantal(projecten, project, rng.randint(1, 8))
        for _ in range(rng.randint(0, 4)):
            projecten.los_onderdeel_toevoegen(
                project.id,
                ModelOnderdeel(
                    id="", naam=f"Los {rng.randint(1, 3)}", materiaal_id=wit.id,
                    breedte=rng.randint(60, 900), hoogte=rng.randint(60, 700),
                ),
            )
        project = projecten.ophalen(project.id)
        res = werk_zaagplannen_bij(project, plannen, materialen, revisie="Rev B")
        assert _geplaatst(res.plannen) == _vraag(project), seed
        codes = [l.scancode_waarde for l in genereer_labels_voor_project(project, res.plannen)]
        assert len(codes) == len(set(codes)), seed
        for plan in res.plannen:
            _geldig_zaagplan(plan.resultaat, plan.resultaat.materiaal)
            assert _paneelzaag_fouten(plan.resultaat) == [], (seed, plan.plaat_nummer)
            assert not _overlapt(plan), seed


def test_oud_zaagplan_met_verschoven_rijrest_wordt_rechtgezet():
    """Zaagplannen van vóór de motorcorrectie hadden het reststuk rechts in
    een rij een zaagsnede te ver naar links; bijwerken moet daar toch
    zaagbaar in leggen."""
    from dataclasses import replace

    from tests.test_engine import _paneelzaag_fouten

    materialen, projecten, project, wit, plannen = _opzet(aantal_kasten=1)
    plaat = plannen[0]
    kerf = plaat.resultaat.materiaal.kerf
    oud = []
    for r in plaat.resultaat.reststukken:
        if r.y == 0 and r.x + r.breedte == plaat.resultaat.materiaal.lengte:
            r = replace(r, x=r.x - kerf)  # zoals de motor het vroeger opsloeg
        oud.append(r)
    plaat.resultaat.reststukken = oud
    _markeer(plaat, 1)
    projecten.los_onderdeel_toevoegen(
        project.id, ModelOnderdeel(id="", naam="Passtuk", materiaal_id=wit.id, breedte=300, hoogte=200)
    )
    project = projecten.ophalen(project.id)
    res = werk_zaagplannen_bij(project, plannen, materialen)
    assert len(res.plannen) == 1 and res.plannen[0].toegevoegd
    nieuw = [p for p in res.plannen[0].resultaat.plaatsingen if (p.onderdeel_id, p.instantie) in res.plannen[0].toegevoegd]
    assert nieuw[0].x == 2013.0
    assert _paneelzaag_fouten(res.plannen[0].resultaat) == []


def test_reststukken_van_gebleven_platen_houden_code_en_status():
    from robocutter.projecten.project_reststukken import ProjectReststukkenBibliotheek, ProjectReststukStatus
    from robocutter.reststukken.bibliotheek import ReststukkenBibliotheek

    materialen, projecten, project, wit, plannen = _opzet(aantal_kasten=6)
    lijst = ProjectReststukkenBibliotheek(materialen, ReststukkenBibliotheek(materialen))
    lijst.overnemen_uit_zaagplan(project.id, plannen)
    handmatig = lijst.toevoegen_handmatig(project.id, wit.id, 500, 400)
    _markeer(plannen[0], 1)
    op_plaat_1 = [r for r in lijst.lijst(project.id) if r.plaat_nummer == plannen[0].plaat_nummer and r.bron.value == "zaagplan"]
    assert op_plaat_1
    lijst.zet_status(op_plaat_1[0].id, ProjectReststukStatus.AFGESCHREVEN)

    project = _zet_aantal(projecten, project, 7)
    # Geen reststukken van plaat 1 gebruiken, dan liggen ze er na het bijwerken allemaal nog.
    res = werk_zaagplannen_bij(project, plannen, materialen, bruikbaar=lambda plan, r: False)
    lijst.overnemen_uit_zaagplan(project.id, res.plannen, behoud_gebleven=True)
    na = {r.id: r for r in lijst.lijst(project.id)}
    for r in op_plaat_1:
        assert r.id in na and na[r.id].volgnummer == r.volgnummer
    assert na[op_plaat_1[0].id].status == ProjectReststukStatus.AFGESCHREVEN
    assert na[handmatig.id].volgnummer == handmatig.volgnummer
    nummers = [r.volgnummer for r in na.values()]
    assert len(nummers) == len(set(nummers))
