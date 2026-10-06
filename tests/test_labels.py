"""Tests voor robocutter.projecten.labels: labelgeneratie (hoofdstuk 6)
vanuit een gegenereerd projectzaagplan.
"""

from __future__ import annotations

from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.materialen.models import Materiaal, MateriaalType
from robocutter.modellen.bibliotheek import ModellenBibliotheek
from robocutter.modellen.models import ModelOnderdeel, Nerfrichting, Rand
from robocutter.projecten.bibliotheek import ProjectenBibliotheek
from robocutter.projecten.labels import genereer_labels_voor_project
from robocutter.projecten.models import Project
from robocutter.projecten.zaagplannen import genereer_zaagplannen_voor_project


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
    modellen = ModellenBibliotheek(materialen)
    projecten = ProjectenBibliotheek(modellen, materialen)
    return materialen, projecten


def test_een_label_per_geplaatst_exemplaar():
    materialen, projecten = _bibliotheken()
    hout = materialen.toevoegen(_materiaal())
    project = projecten.toevoegen(
        Project(
            id="", naam="Keuken Jansen", klant="Jansen", opdrachtnummer="P-042",
            losse_onderdelen=[_onderdeel(hout.id, naam="Zijkant", breedte=600, hoogte=720, aantal=3)],
        )
    )

    plannen, _ = genereer_zaagplannen_voor_project(project, materialen, strategie="horizontaal")
    labels = genereer_labels_voor_project(project, plannen)

    assert len(labels) == 3
    assert all(label.onderdeel_naam == "Zijkant" for label in labels)
    assert all(label.materiaal_naam == "Eiken multiplex 18mm" for label in labels)
    assert all(label.projectnummer == "P-042" for label in labels)
    # Zonder nerfrichting-eis mag de motor het onderdeel roteren, dus check
    # de afmeting oriëntatie-onafhankelijk (zie ook de tweede test hieronder
    # met een nerfrichting-eis, waar rotatie juist uitgesloten is).
    assert all({label.breedte, label.hoogte} == {600, 720} for label in labels)
    # Elk exemplaar krijgt een eigen, unieke scancode-waarde.
    assert len({label.scancode_waarde for label in labels}) == 3
    assert all(label.scancode_waarde.startswith(f"RC:onderdeel:{project.id}:") for label in labels)


def test_label_neemt_kantenband_en_nerfrichting_over_van_het_onderdeel():
    materialen, projecten = _bibliotheken()
    hout = materialen.toevoegen(_materiaal())
    project = projecten.toevoegen(
        Project(
            id="", naam="Test", klant="Test",
            losse_onderdelen=[
                _onderdeel(
                    hout.id, naam="Deur", breedte=400, hoogte=600,
                    kantenband_randen=frozenset({Rand.BOVEN, Rand.ONDER}),
                    nerfrichting_vereist=Nerfrichting.LANGE_ZIJDE,
                )
            ],
        )
    )

    plannen, _ = genereer_zaagplannen_voor_project(project, materialen)
    labels = genereer_labels_voor_project(project, plannen)

    assert len(labels) == 1
    label = labels[0]
    assert label.kantenband_randen == frozenset({Rand.BOVEN, Rand.ONDER})
    assert label.nerfrichting_vereist == Nerfrichting.LANGE_ZIJDE
    assert label.fabriekskantenband_vereist is False


def test_niet_geplaatste_onderdelen_krijgen_geen_label():
    materialen, projecten = _bibliotheken()
    # Materiaal te klein om ook maar één onderdeel op te plaatsen.
    hout = materialen.toevoegen(_materiaal(lengte=500, breedte=500))
    project = projecten.toevoegen(
        Project(
            id="", naam="Test", klant="Test",
            losse_onderdelen=[_onderdeel(hout.id, naam="Te groot", breedte=1000, hoogte=1000)],
        )
    )

    plannen, _ = genereer_zaagplannen_voor_project(project, materialen)
    labels = genereer_labels_voor_project(project, plannen)

    assert labels == []


def test_geen_zaagplannen_geeft_geen_labels():
    _, projecten = _bibliotheken()
    project = projecten.toevoegen(Project(id="", naam="Leeg project", klant="Test"))
    assert genereer_labels_voor_project(project, []) == []


def test_reststuk_label_nerfpijl_volgt_het_materiaal():
    from robocutter.projecten.labels import genereer_reststuk_labels
    from robocutter.projecten.project_reststukken import ProjectReststuk

    materialen, _ = _bibliotheken()
    eiken = materialen.toevoegen(_materiaal(nerfrichting=Nerfrichting.LANGE_ZIJDE))
    item = ProjectReststuk(
        id="abc12345", project_id="p1", volgnummer=3, materiaal_id=eiken.id, lengte=1240, breedte=600,
        fabriekskantenband_randen=frozenset({Rand.ONDER}),
    )
    [label] = genereer_reststuk_labels([item], materialen)
    assert label.code == "R3"
    assert label.nerf_langs_lengte is True
    assert label.fabriekskantenband_randen == frozenset({Rand.ONDER})


def test_bibliotheek_reststuk_label_heeft_het_vaste_nummer_als_naam():
    from robocutter.projecten.labels import genereer_bibliotheek_reststuk_labels
    from robocutter.reststukken.models import Reststuk

    materialen, _ = _bibliotheken()
    hout = materialen.toevoegen(_materiaal())
    [label] = genereer_bibliotheek_reststuk_labels(
        [Reststuk(id="3f9a21c0", materiaal_id=hout.id, lengte=1124, breedte=594)], materialen
    )
    assert label.code == "3F9A21C0"
    assert label.scancode_waarde == "RC:reststuk:3f9a21c0"
    assert label.afmeting_tekst == "1124 × 594 mm"
