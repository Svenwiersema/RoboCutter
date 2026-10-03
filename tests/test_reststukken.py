"""Tests voor de reststukkenbibliotheek-functie (Module 3).

Dekt: live validatie (incl. koppeling aan een bestaand materiaal), de
beschikbaar/gebruikt-workflow, filteren/zoeken (via het gekoppelde
materiaal, want type/familie/kleur staan niet los op het reststuk), en
het wegschrijven/herladen via de SQLite-opslag.
"""

from __future__ import annotations

import pytest

from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.materialen.models import Materiaal, MateriaalType
from robocutter.reststukken.bibliotheek import (
    OngeldigeStatusOvergangError,
    ReststukkenBibliotheek,
    valideer,
)
from robocutter.reststukken.models import Reststuk, ReststukStatus
from robocutter.reststukken.opslag import open_verbinding


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


def _reststuk(materiaal_id: str, **overrides) -> Reststuk:
    basis = dict(id="", materiaal_id=materiaal_id, lengte=800, breedte=400)
    basis.update(overrides)
    return Reststuk(**basis)


def _bibliotheken() -> tuple[MaterialenBibliotheek, ReststukkenBibliotheek]:
    materialen = MaterialenBibliotheek()
    reststukken = ReststukkenBibliotheek(materialen)
    return materialen, reststukken


def test_valideer_geldig_reststuk_geeft_geen_fouten():
    materialen, reststukken = _bibliotheken()
    materiaal = materialen.toevoegen(_materiaal())
    assert valideer(_reststuk(materiaal.id), materialen) == []


def test_valideer_zonder_materiaal_id():
    materialen, _ = _bibliotheken()
    assert "Materiaal is verplicht." in valideer(_reststuk(""), materialen)


def test_valideer_met_onbekend_materiaal_id():
    materialen, _ = _bibliotheken()
    fouten = valideer(_reststuk("bestaat-niet"), materialen)
    assert "Gekoppeld materiaal bestaat niet (meer)." in fouten


@pytest.mark.parametrize(
    "overrides,verwachte_fout",
    [
        ({"lengte": 0}, "Lengte moet groter dan 0 zijn."),
        ({"breedte": -5}, "Breedte moet groter dan 0 zijn."),
    ],
)
def test_valideer_signaleert_ongeldige_afmetingen(overrides, verwachte_fout):
    materialen, _ = _bibliotheken()
    materiaal = materialen.toevoegen(_materiaal())
    fouten = valideer(_reststuk(materiaal.id, **overrides), materialen)
    assert verwachte_fout in fouten


def test_toevoegen_wijst_id_toe_en_zet_status_beschikbaar():
    materialen, reststukken = _bibliotheken()
    materiaal = materialen.toevoegen(_materiaal())
    reststuk = reststukken.toevoegen(_reststuk(materiaal.id))
    assert reststuk.id
    assert reststuk.status == ReststukStatus.BESCHIKBAAR


def test_toevoegen_met_ongeldig_reststuk_faalt():
    materialen, reststukken = _bibliotheken()
    with pytest.raises(ValueError):
        reststukken.toevoegen(_reststuk("bestaat-niet"))


def test_materiaal_van_geeft_gekoppeld_materiaal():
    materialen, reststukken = _bibliotheken()
    materiaal = materialen.toevoegen(_materiaal())
    reststuk = reststukken.toevoegen(_reststuk(materiaal.id))
    assert reststukken.materiaal_van(reststuk).id == materiaal.id


def test_gebruikt_beschikbaar_workflow():
    materialen, reststukken = _bibliotheken()
    materiaal = materialen.toevoegen(_materiaal())
    reststuk = reststukken.toevoegen(_reststuk(materiaal.id))

    # Nog niet gebruikt, dus niet weer beschikbaar te maken.
    with pytest.raises(OngeldigeStatusOvergangError):
        reststukken.zet_beschikbaar(reststuk.id)

    reststukken.markeer_gebruikt(reststuk.id)
    assert reststukken.ophalen(reststuk.id).status == ReststukStatus.GEBRUIKT

    # Nogmaals als gebruikt markeren mag niet.
    with pytest.raises(OngeldigeStatusOvergangError):
        reststukken.markeer_gebruikt(reststuk.id)

    reststukken.zet_beschikbaar(reststuk.id)
    assert reststukken.ophalen(reststuk.id).status == ReststukStatus.BESCHIKBAAR


def test_verwijderen():
    materialen, reststukken = _bibliotheken()
    materiaal = materialen.toevoegen(_materiaal())
    reststuk = reststukken.toevoegen(_reststuk(materiaal.id))

    reststukken.verwijderen(reststuk.id)

    with pytest.raises(KeyError):
        reststukken.ophalen(reststuk.id)


def test_lijst_filtert_op_status_type_en_zoekterm():
    materialen, reststukken = _bibliotheken()
    plaat = materialen.toevoegen(_materiaal(naam="Eiken plaat", familie="Eiken multiplex"))
    balk = materialen.toevoegen(
        _materiaal(naam="Vurenhouten balk", type=MateriaalType.BALK, lengte=3000, breedte=40, derde_afmeting=60)
    )
    reststuk_plaat = reststukken.toevoegen(_reststuk(plaat.id, lengte=800, breedte=400))
    reststuk_balk = reststukken.toevoegen(_reststuk(balk.id, lengte=500, breedte=40))
    reststukken.markeer_gebruikt(reststuk_balk.id)

    alleen_beschikbaar = reststukken.lijst(status=ReststukStatus.BESCHIKBAAR)
    assert [r.id for r in alleen_beschikbaar] == [reststuk_plaat.id]

    alleen_balken = reststukken.lijst(type_filter=MateriaalType.BALK)
    assert [r.id for r in alleen_balken] == [reststuk_balk.id]

    gevonden = reststukken.lijst(zoekterm="eiken 800")
    assert [r.id for r in gevonden] == [reststuk_plaat.id]


def test_sqlite_opslag_overleeft_herstart(tmp_path):
    materialen_db = tmp_path / "materialen.db"
    reststukken_db = tmp_path / "reststukken.db"

    from robocutter.materialen.opslag import open_verbinding as open_materialen_verbinding

    mat_verbinding = open_materialen_verbinding(materialen_db)
    materialen = MaterialenBibliotheek(mat_verbinding)
    materiaal = materialen.toevoegen(_materiaal())

    rest_verbinding = open_verbinding(reststukken_db)
    reststukken = ReststukkenBibliotheek(materialen, rest_verbinding)
    reststuk = reststukken.toevoegen(_reststuk(materiaal.id, herkomst_project="Keuken Jansen", herkomst_model="Onderkast 60cm"))
    reststukken.markeer_gebruikt(reststuk.id)
    rest_verbinding.close()
    mat_verbinding.close()

    # Nieuwe verbindingen simuleren een herstart van de app.
    herstart_mat_verbinding = open_materialen_verbinding(materialen_db)
    herstarte_materialen = MaterialenBibliotheek(herstart_mat_verbinding)
    herstart_rest_verbinding = open_verbinding(reststukken_db)
    herstarte_reststukken = ReststukkenBibliotheek(herstarte_materialen, herstart_rest_verbinding)

    herladen = herstarte_reststukken.ophalen(reststuk.id)
    assert herladen.herkomst_project == "Keuken Jansen"
    assert herladen.herkomst_model == "Onderkast 60cm"
    assert herladen.status == ReststukStatus.GEBRUIKT
    assert herstarte_reststukken.materiaal_van(herladen).id == materiaal.id

    herstarte_reststukken.verwijderen(reststuk.id)
    herstart_rest_verbinding.close()
    herstart_mat_verbinding.close()

    derde_rest_verbinding = open_verbinding(reststukken_db)
    derde_reststukken = ReststukkenBibliotheek(herstarte_materialen, derde_rest_verbinding)
    assert derde_reststukken.lijst() == []
    derde_rest_verbinding.close()


def test_reserveren_door_zaagplan_en_verbruiken_bij_productie(tmp_path):
    db_pad = tmp_path / "rest.db"
    verbinding = open_verbinding(db_pad)
    materialen = MaterialenBibliotheek()
    materiaal = materialen.toevoegen(_materiaal())
    reststukken = ReststukkenBibliotheek(materialen, verbinding)
    a = reststukken.toevoegen(_reststuk(materiaal.id))
    b = reststukken.toevoegen(_reststuk(materiaal.id))
    c = reststukken.toevoegen(_reststuk(materiaal.id))

    reststukken.wijs_toe_aan_project("p1", "Keuken", {a.id, b.id})
    assert a.status == ReststukStatus.GERESERVEERD and a.project_naam == "Keuken"
    # Een ander project ziet gereserveerde stukken van p1 niet als kandidaat.
    assert {r.id for r in reststukken.kandidaten_voor_project("p2")} == {c.id}
    assert {r.id for r in reststukken.kandidaten_voor_project("p1")} == {a.id, b.id, c.id}

    # Opnieuw genereren gebruikt b niet meer: b komt weer vrij.
    reststukken.wijs_toe_aan_project("p1", "Keuken", {a.id})
    assert b.status == ReststukStatus.BESCHIKBAAR and b.project_id == ""

    assert [r.id for r in reststukken.verbruik_reserveringen("p1")] == [a.id]
    assert a.status == ReststukStatus.GEBRUIKT and a.project_id == "p1"
    assert reststukken.verbruik_reserveringen("p1") == []

    # In productie opnieuw genereren met een nieuw stuk: meteen gebruikt.
    reststukken.wijs_toe_aan_project("p1", "Keuken", {a.id, c.id}, verbruikt=True)
    assert c.status == ReststukStatus.GEBRUIKT

    # Handmatig terugzetten wist de koppeling.
    reststukken.zet_beschikbaar(c.id)
    assert c.project_id == ""
    verbinding.close()

    herladen = ReststukkenBibliotheek(materialen, open_verbinding(db_pad)).ophalen(a.id)
    assert (herladen.status, herladen.project_id, herladen.project_naam) == (ReststukStatus.GEBRUIKT, "p1", "Keuken")


def test_oude_database_krijgt_projectkolommen(tmp_path):
    import sqlite3

    db_pad = tmp_path / "oud.db"
    oud = sqlite3.connect(db_pad)
    oud.execute(
        "CREATE TABLE reststukken (id TEXT PRIMARY KEY, materiaal_id TEXT NOT NULL, lengte REAL NOT NULL, "
        "breedte REAL NOT NULL, herkomst_project TEXT NOT NULL, herkomst_model TEXT NOT NULL, status TEXT NOT NULL)"
    )
    oud.execute("INSERT INTO reststukken VALUES ('x', 'm', 800, 400, '', '', 'beschikbaar')")
    oud.commit()
    oud.close()

    from robocutter.reststukken import opslag

    herladen = opslag.laad_alles(open_verbinding(db_pad))
    assert herladen[0].project_id == "" and herladen[0].status == ReststukStatus.BESCHIKBAAR


def test_fabrieksranden_worden_bewaard(tmp_path):
    from robocutter.optimalisatie.models import Rand

    db_pad = tmp_path / "r.db"
    materialen = MaterialenBibliotheek()
    materiaal = materialen.toevoegen(_materiaal())
    reststukken = ReststukkenBibliotheek(materialen, open_verbinding(db_pad))
    r = reststukken.toevoegen(_reststuk(materiaal.id, fabriekskantenband_randen=frozenset({Rand.BOVEN, Rand.ONDER})))
    herladen = ReststukkenBibliotheek(materialen, open_verbinding(db_pad)).ophalen(r.id)
    assert herladen.fabriekskantenband_randen == {Rand.BOVEN, Rand.ONDER}
