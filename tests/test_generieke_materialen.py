"""Generieke materialen met een decor per project (Sven, 2026-11-08: "hpl
met nerf generiek zodat je niet voor elke apparte hpl textuur een eigen
materiaal moet aanmaken"). Mockup: design/assets/mockups/balken-en-generiek-concept.html."""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import date

from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.materialen.models import Materiaal, MateriaalType
from robocutter.materialen.opslag import open_verbinding as open_materialen_verbinding
from robocutter.modellen.bibliotheek import ModellenBibliotheek
from robocutter.modellen.models import ModelOnderdeel
from robocutter.projecten.bibliotheek import ProjectenBibliotheek
from robocutter.projecten.labels import genereer_bibliotheek_reststuk_labels, genereer_labels_voor_project, genereer_reststuk_labels
from robocutter.projecten.models import Project, ProjectStatus
from robocutter.projecten.opslag import open_verbinding as open_projecten_verbinding
from robocutter.projecten.project_reststukken import ProjectReststukkenBibliotheek
from robocutter.projecten.revisies import samenstelling_wijzigingen
from robocutter.projecten.zaagplannen import genereer_zaagplannen_voor_project
from robocutter.reststukken.bibliotheek import ReststukkenBibliotheek
from robocutter.reststukken.models import Reststuk
from robocutter.reststukken.opslag import open_verbinding as open_reststukken_verbinding


def _hpl(**overrides) -> Materiaal:
    basis = dict(
        id="", naam="HPL met nerf 0,8 mm", type=MateriaalType.PLAAT,
        lengte=3050, breedte=1300, derde_afmeting=0.8, min_reststukgrootte=200, generiek=True,
    )
    basis.update(overrides)
    return Materiaal(**basis)


def _opzet():
    materialen = MaterialenBibliotheek()
    projecten = ProjectenBibliotheek(ModellenBibliotheek(materialen), materialen)
    hpl = materialen.toevoegen(_hpl())
    mdf = materialen.toevoegen(_hpl(naam="MDF 18 mm", lengte=2800, breedte=2070, derde_afmeting=18, generiek=False))
    project = projecten.toevoegen(
        Project(
            id="", naam="Keuken Jansen", klant="Jansen",
            losse_onderdelen=[
                ModelOnderdeel(id="", naam="Front", materiaal_id=hpl.id, breedte=600, hoogte=700, aantal=2),
                ModelOnderdeel(id="", naam="Zijkant", materiaal_id=mdf.id, breedte=560, hoogte=720),
            ],
        )
    )
    return materialen, projecten, hpl, mdf, project


def test_generiek_overleeft_herstart_en_oude_tabel_krijgt_de_kolom(tmp_path):
    db = tmp_path / "materialen.db"
    oud = sqlite3.connect(db)
    oud.execute(
        """CREATE TABLE materialen (
            id TEXT PRIMARY KEY, naam TEXT NOT NULL, type TEXT NOT NULL,
            lengte REAL NOT NULL, breedte REAL NOT NULL, derde_afmeting REAL NOT NULL,
            familie TEXT NOT NULL, kleur_afwerking TEXT NOT NULL, nerfrichting TEXT NOT NULL,
            randafzaag_marge REAL NOT NULL, randafzaag_randen TEXT NOT NULL,
            min_reststukgrootte REAL NOT NULL, mes_groef_notitie TEXT NOT NULL,
            fabriekskantenband_randen TEXT NOT NULL, productcode TEXT NOT NULL,
            leverancier TEXT NOT NULL, tags TEXT NOT NULL, status TEXT NOT NULL)"""
    )
    oud.execute(
        "INSERT INTO materialen VALUES ('m1','Oud','plaat',2800,2070,18,'','','geen',0,'[]',0,'','[]','','','[]','actief')"
    )
    oud.commit()
    oud.close()

    verbinding = open_materialen_verbinding(db)
    bib = MaterialenBibliotheek(verbinding)
    assert bib.ophalen("m1").generiek is False
    hpl = bib.toevoegen(_hpl())
    verbinding.close()

    herstart = MaterialenBibliotheek(open_materialen_verbinding(db))
    assert herstart.ophalen(hpl.id).generiek is True


def test_decors_overleven_herstart(tmp_path):
    materialen = MaterialenBibliotheek()
    hpl = materialen.toevoegen(_hpl())
    db = tmp_path / "projecten.db"
    verbinding = open_projecten_verbinding(db)
    projecten = ProjectenBibliotheek(ModellenBibliotheek(materialen), materialen, verbinding)
    project = projecten.toevoegen(Project(id="", naam="Keuken", klant="K"))
    projecten.decor_zetten(project.id, hpl.id, "  Egger H1145 ST10  ")
    verbinding.close()

    herstart = ProjectenBibliotheek(ModellenBibliotheek(materialen), materialen, open_projecten_verbinding(db))
    assert herstart.ophalen(project.id).decors == {hpl.id: "Egger H1145 ST10"}
    herstart.decor_zetten(project.id, hpl.id, "")
    assert herstart.ophalen(project.id).decors == {}


def test_zaagplan_en_labels_tonen_het_decor_alleen_bij_generiek_materiaal():
    materialen, projecten, hpl, mdf, project = _opzet()

    plannen, _ = genereer_zaagplannen_voor_project(project, materialen)
    namen = {p.materiaal_id: p.materiaal_naam for p in plannen}
    assert namen == {hpl.id: "HPL met nerf 0,8 mm · decor onbekend", mdf.id: "MDF 18 mm"}

    project = projecten.decor_zetten(project.id, hpl.id, "Egger H1145")
    plannen, _ = genereer_zaagplannen_voor_project(project, materialen)
    assert {p.materiaal_naam for p in plannen if p.materiaal_id == hpl.id} == {"HPL met nerf 0,8 mm · Egger H1145"}
    labels = genereer_labels_voor_project(project, plannen)
    assert {lb.materiaal_naam for lb in labels if lb.onderdeel_naam == "Front"} == {"HPL met nerf 0,8 mm · Egger H1145"}


def test_alleen_reststukken_met_hetzelfde_decor_worden_gebruikt():
    materialen, projecten, hpl, _, project = _opzet()
    project = projecten.decor_zetten(project.id, hpl.id, "Egger H1145")
    reststukken = [
        Reststuk(id="ander", materiaal_id=hpl.id, lengte=1500, breedte=1300, decor="Polyrey Chêne"),
        Reststuk(id="zelfde", materiaal_id=hpl.id, lengte=1500, breedte=1300, decor="egger h1145"),
    ]

    plannen, _ = genereer_zaagplannen_voor_project(project, materialen, reststukken=reststukken)

    assert {p.reststuk_id for p in plannen if p.materiaal_id == hpl.id} == {"zelfde"}


def test_vrijgeven_en_reststuklabels_nemen_het_decor_mee(tmp_path):
    materialen, projecten, hpl, _, project = _opzet()
    project = projecten.decor_zetten(project.id, hpl.id, "Egger H1145")
    verbinding = open_reststukken_verbinding(tmp_path / "reststukken.db")
    reststukken = ReststukkenBibliotheek(materialen, verbinding)
    bib = ProjectReststukkenBibliotheek(materialen, reststukken)
    item = bib.toevoegen_handmatig(project.id, hpl.id, 900, 600)

    labels = genereer_reststuk_labels([item], materialen, project.decors)
    assert labels[0].materiaal_naam == "HPL met nerf 0,8 mm · Egger H1145"

    project = projecten.zet_status(project.id, ProjectStatus.AFGEROND)
    nieuw = bib.vrijgeven(project, op=date(2026, 11, 8))
    assert [r.decor for r in nieuw] == ["Egger H1145"]
    verbinding.close()

    herstart = ReststukkenBibliotheek(materialen, open_reststukken_verbinding(tmp_path / "reststukken.db"))
    herladen = herstart.ophalen(nieuw[0].id)
    assert herladen.decor == "Egger H1145"
    assert genereer_bibliotheek_reststuk_labels([herladen], materialen)[0].materiaal_naam.endswith("Egger H1145")


def test_ander_decor_telt_als_gewijzigde_samenstelling():
    materialen, projecten, hpl, _, project = _opzet()
    oud = replace(project, decors=dict(project.decors))
    nieuw = projecten.decor_zetten(project.id, hpl.id, "Egger H1145")

    assert samenstelling_wijzigingen(oud, nieuw, lambda mid: materialen.ophalen(mid).naam) == [
        "Decor HPL met nerf 0,8 mm: — → Egger H1145"
    ]
    # De momentopname zelf veranderde niet mee.
    assert oud.decors == {}


def test_generieke_materialen_in_project_en_eerder_gebruikte_decors():
    materialen, projecten, hpl, _, project = _opzet()
    assert projecten.generieke_materialen_in_project(project.id) == [hpl.id]

    for naam, start, decor in (
        ("Oud", date(2026, 1, 5), "Polyrey Chêne"),
        ("Nieuw", date(2026, 10, 1), "Egger H1145"),
        ("Dubbel", date(2026, 3, 1), "egger h1145"),
        ("Zonder datum", None, "Formica F7927"),
    ):
        p = projecten.toevoegen(Project(id="", naam=naam, klant="K", startdatum=start))
        projecten.decor_zetten(p.id, hpl.id, decor)
    projecten.decor_zetten(project.id, hpl.id, "Eigen decor")

    assert projecten.eerder_gebruikte_decors(hpl.id, behalve_project_id=project.id) == [
        "Egger H1145", "Polyrey Chêne", "Formica F7927",
    ]
