"""Tests voor de materialenbibliotheek-functie (Module 3).

Dekt: live validatie, de archiveer-/verwijderworkflow (actief ->
gearchiveerd -> definitief verwijderd, alleen vanuit het archief), en
het wegschrijven/herladen via de SQLite-opslag (hoofdstuk 8).
"""

from __future__ import annotations

import pytest

from robocutter.materialen.bibliotheek import (
    MaterialenBibliotheek,
    OngeldigeStatusOvergangError,
    valideer,
)
from robocutter.materialen.models import (
    Materiaal,
    MateriaalStatus,
    MateriaalType,
    Nerfrichting,
    Rand,
)
from robocutter.materialen.opslag import open_verbinding


def _plaat(**overrides) -> Materiaal:
    basis = dict(
        id="",
        naam="Eiken multiplex 18mm",
        type=MateriaalType.PLAAT,
        lengte=2800,
        breedte=2070,
        derde_afmeting=18,
    )
    basis.update(overrides)
    return Materiaal(**basis)


def test_valideer_geldig_materiaal_geeft_geen_fouten():
    assert valideer(_plaat()) == []


@pytest.mark.parametrize(
    "overrides,verwachte_fout",
    [
        ({"naam": "  "}, "Naam is verplicht."),
        ({"lengte": 0}, "Lengte moet groter dan 0 zijn."),
        ({"breedte": -5}, "Breedte moet groter dan 0 zijn."),
        ({"derde_afmeting": 0}, "Dikte moet groter dan 0 zijn."),
        ({"kerf": -1}, "Kerf/zaagsnede-breedte kan niet negatief zijn."),
        ({"randafzaag_marge": -1}, "Randafzaag-marge kan niet negatief zijn."),
        ({"min_reststukgrootte": -1}, "Minimale reststukgrootte kan niet negatief zijn."),
    ],
)
def test_valideer_signaleert_ongeldige_velden(overrides, verwachte_fout):
    assert verwachte_fout in valideer(_plaat(**overrides))


def test_derde_afmeting_label_verschilt_per_type():
    assert _plaat(type=MateriaalType.PLAAT).derde_afmeting_label == "Dikte"
    assert _plaat(type=MateriaalType.BALK).derde_afmeting_label == "Hoogte"


def test_toevoegen_wijst_id_toe_en_zet_status_actief():
    bib = MaterialenBibliotheek()
    materiaal = bib.toevoegen(_plaat())
    assert materiaal.id
    assert materiaal.status == MateriaalStatus.ACTIEF


def test_toevoegen_met_ongeldig_materiaal_faalt():
    bib = MaterialenBibliotheek()
    with pytest.raises(ValueError):
        bib.toevoegen(_plaat(naam=""))


def test_archiveer_verwijder_workflow():
    bib = MaterialenBibliotheek()
    materiaal = bib.toevoegen(_plaat())

    # Direct verwijderen (nog actief) mag niet.
    with pytest.raises(OngeldigeStatusOvergangError):
        bib.verwijderen_definitief(materiaal.id)

    bib.archiveren(materiaal.id)
    assert bib.ophalen(materiaal.id).status == MateriaalStatus.GEARCHIVEERD

    # Nogmaals archiveren mag niet.
    with pytest.raises(OngeldigeStatusOvergangError):
        bib.archiveren(materiaal.id)

    bib.verwijderen_definitief(materiaal.id)
    with pytest.raises(KeyError):
        bib.ophalen(materiaal.id)


def test_heractiveren_zet_gearchiveerd_terug_naar_actief():
    bib = MaterialenBibliotheek()
    materiaal = bib.toevoegen(_plaat())
    bib.archiveren(materiaal.id)

    bib.heractiveren(materiaal.id)

    assert bib.ophalen(materiaal.id).status == MateriaalStatus.ACTIEF
    with pytest.raises(OngeldigeStatusOvergangError):
        bib.heractiveren(materiaal.id)


def test_lijst_filtert_op_status_type_en_zoekterm():
    bib = MaterialenBibliotheek()
    plaat = bib.toevoegen(_plaat(naam="Eiken plaat", productcode="EIK-18"))
    balk = bib.toevoegen(
        _plaat(naam="Vurenhouten balk", type=MateriaalType.BALK, id="")
    )
    bib.archiveren(balk.id)

    alleen_actief = bib.lijst(status=MateriaalStatus.ACTIEF)
    assert [m.id for m in alleen_actief] == [plaat.id]

    alleen_balken = bib.lijst(type_filter=MateriaalType.BALK)
    assert [m.id for m in alleen_balken] == [balk.id]

    gevonden = bib.lijst(zoekterm="eik")
    assert [m.id for m in gevonden] == [plaat.id]


def test_lijst_zoekterm_combineert_tekst_en_afmeting():
    bib = MaterialenBibliotheek()
    multiplex_18 = bib.toevoegen(
        _plaat(naam="Eiken multiplex 18mm", familie="Eiken multiplex", lengte=2800, breedte=2070, derde_afmeting=18)
    )
    bib.toevoegen(
        _plaat(naam="Eiken multiplex 25mm", familie="Eiken multiplex", lengte=2800, breedte=2070, derde_afmeting=25)
    )
    bib.toevoegen(
        _plaat(naam="Wit gemelamineerd 18mm", familie="Wit gemelamineerd", lengte=2800, breedte=2070, derde_afmeting=18)
    )

    gevonden = bib.lijst(zoekterm="multiplex 2800 18")
    assert [m.id for m in gevonden] == [multiplex_18.id]

    # Een term die nergens matcht (ook niet als los getal) levert niets op.
    assert bib.lijst(zoekterm="multiplex 999") == []


def test_sqlite_opslag_overleeft_herstart(tmp_path):
    db_pad = tmp_path / "materialen.db"

    verbinding = open_verbinding(db_pad)
    bib = MaterialenBibliotheek(verbinding)
    materiaal = bib.toevoegen(
        _plaat(
            familie="Eiken multiplex",
            kleur_afwerking="Naturel",
            nerfrichting=Nerfrichting.LANGE_ZIJDE,
            randafzaag_randen=frozenset({Rand.BOVEN, Rand.ONDER}),
            fabriekskantenband_randen=frozenset({Rand.LINKS}),
            tags=("multiplex", "eiken"),
        )
    )
    bib.archiveren(materiaal.id)
    verbinding.close()

    # Nieuwe verbinding + bibliotheek simuleert een herstart van de app.
    herstart_verbinding = open_verbinding(db_pad)
    herstarte_bib = MaterialenBibliotheek(herstart_verbinding)

    herladen = herstarte_bib.ophalen(materiaal.id)
    assert herladen.naam == materiaal.naam
    assert herladen.status == MateriaalStatus.GEARCHIVEERD
    assert herladen.randafzaag_randen == frozenset({Rand.BOVEN, Rand.ONDER})
    assert herladen.fabriekskantenband_randen == frozenset({Rand.LINKS})
    assert herladen.tags == ("multiplex", "eiken")

    herstarte_bib.verwijderen_definitief(materiaal.id)
    herstart_verbinding.close()

    # Ook definitief verwijderen moet doorwerken naar het bestand.
    derde_verbinding = open_verbinding(db_pad)
    derde_bib = MaterialenBibliotheek(derde_verbinding)
    assert derde_bib.lijst() == []
    derde_verbinding.close()
