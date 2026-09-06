"""Tests voor de modellenbibliotheek-functie (Module 2).

Dekt: live validatie (incl. koppeling aan een bestaand materiaal per
onderdeel), nesting (submodellen), cirkelverwijzing-detectie (direct en
indirect), het blokkeren van verwijderen zolang een model nog als
submodel gebruikt wordt, zoeken, en het wegschrijven/herladen via de
SQLite-opslag.
"""

from __future__ import annotations

import pytest

from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.materialen.models import Materiaal, MateriaalType
from robocutter.modellen.bibliotheek import (
    ModelInGebruikError,
    ModellenBibliotheek,
    valideer,
)
from robocutter.modellen.models import Model, ModelOnderdeel, SubModelVerwijzing
from robocutter.modellen.opslag import open_verbinding


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


def _bibliotheken() -> tuple[MaterialenBibliotheek, ModellenBibliotheek]:
    materialen = MaterialenBibliotheek()
    modellen = ModellenBibliotheek(materialen)
    return materialen, modellen


def test_valideer_geldig_model_geeft_geen_fouten():
    materialen, modellen = _bibliotheken()
    materiaal = materialen.toevoegen(_materiaal())
    model = _model(onderdelen=[_onderdeel(materiaal.id)])
    assert valideer(model, materialen, modellen) == []


def test_valideer_zonder_naam():
    materialen, modellen = _bibliotheken()
    fouten = valideer(_model(naam=""), materialen, modellen)
    assert "Naam is verplicht." in fouten


@pytest.mark.parametrize(
    "overrides,verwachte_fout",
    [
        ({"breedte": 0}, "breedte moet groter dan 0 zijn."),
        ({"hoogte": -5}, "hoogte moet groter dan 0 zijn."),
        ({"aantal": 0}, "aantal moet minstens 1 zijn."),
    ],
)
def test_valideer_signaleert_ongeldig_onderdeel(overrides, verwachte_fout):
    materialen, modellen = _bibliotheken()
    materiaal = materialen.toevoegen(_materiaal())
    model = _model(onderdelen=[_onderdeel(materiaal.id, **overrides)])
    fouten = valideer(model, materialen, modellen)
    assert any(f.endswith(verwachte_fout) for f in fouten)


def test_valideer_met_onbekend_materiaal_id():
    materialen, modellen = _bibliotheken()
    model = _model(onderdelen=[_onderdeel("bestaat-niet")])
    fouten = valideer(model, materialen, modellen)
    assert any("materiaal bestaat niet (meer)" in f for f in fouten)


def test_valideer_met_onbekend_submodel():
    materialen, modellen = _bibliotheken()
    model = _model(submodellen=[SubModelVerwijzing(model_id="bestaat-niet")])
    fouten = valideer(model, materialen, modellen)
    assert any("bestaat niet (meer)" in f for f in fouten)


def test_toevoegen_wijst_id_toe():
    materialen, modellen = _bibliotheken()
    materiaal = materialen.toevoegen(_materiaal())
    model = modellen.toevoegen(_model(onderdelen=[_onderdeel(materiaal.id)]))
    assert model.id


def test_toevoegen_met_ongeldig_model_faalt():
    materialen, modellen = _bibliotheken()
    with pytest.raises(ValueError):
        modellen.toevoegen(_model(naam=""))


def test_nesting_submodel_wordt_correct_opgeslagen():
    materialen, modellen = _bibliotheken()
    materiaal = materialen.toevoegen(_materiaal())
    onderkast = modellen.toevoegen(_model(naam="Onderkast", onderdelen=[_onderdeel(materiaal.id)]))
    keuken = modellen.toevoegen(
        _model(naam="Keuken", submodellen=[SubModelVerwijzing(model_id=onderkast.id, aantal=3)])
    )
    opgehaald = modellen.ophalen(keuken.id)
    assert len(opgehaald.submodellen) == 1
    assert opgehaald.submodellen[0].aantal == 3
    assert modellen.submodel_van(opgehaald.submodellen[0]).id == onderkast.id


def test_directe_cirkelverwijzing_wordt_geblokkeerd():
    materialen, modellen = _bibliotheken()
    a = modellen.toevoegen(_model(naam="A"))
    b = modellen.toevoegen(_model(naam="B", submodellen=[SubModelVerwijzing(model_id=a.id)]))

    a_bijgewerkt = modellen.ophalen(a.id)
    a_bijgewerkt.submodellen = [SubModelVerwijzing(model_id=b.id)]
    with pytest.raises(ValueError):
        modellen.bijwerken(a_bijgewerkt)


def test_indirecte_cirkelverwijzing_wordt_geblokkeerd():
    materialen, modellen = _bibliotheken()
    a = modellen.toevoegen(_model(naam="A"))
    b = modellen.toevoegen(_model(naam="B"))
    c = modellen.toevoegen(_model(naam="C", submodellen=[SubModelVerwijzing(model_id=a.id)]))

    b_bijgewerkt = modellen.ophalen(b.id)
    b_bijgewerkt.submodellen = [SubModelVerwijzing(model_id=c.id)]
    modellen.bijwerken(b_bijgewerkt)  # B -> C -> A, nog geen cykel

    a_bijgewerkt = modellen.ophalen(a.id)
    a_bijgewerkt.submodellen = [SubModelVerwijzing(model_id=b.id)]
    with pytest.raises(ValueError):
        modellen.bijwerken(a_bijgewerkt)  # zou A -> B -> C -> A maken


def test_verwijderen_geblokkeerd_zolang_model_gebruikt_wordt():
    materialen, modellen = _bibliotheken()
    a = modellen.toevoegen(_model(naam="A"))
    b = modellen.toevoegen(_model(naam="B", submodellen=[SubModelVerwijzing(model_id=a.id)]))

    with pytest.raises(ModelInGebruikError):
        modellen.verwijderen(a.id)

    b_bijgewerkt = modellen.ophalen(b.id)
    b_bijgewerkt.submodellen = []
    modellen.bijwerken(b_bijgewerkt)

    modellen.verwijderen(a.id)
    with pytest.raises(KeyError):
        modellen.ophalen(a.id)


def test_lijst_filtert_op_zoekterm():
    materialen, modellen = _bibliotheken()
    onderkast = modellen.toevoegen(_model(naam="Onderkast 60cm", map="Keukens/Onderkasten", tags=("keuken",)))
    modellen.toevoegen(_model(naam="Boekenkast", map="Woonkamer"))

    gevonden = modellen.lijst(zoekterm="onderkast")
    assert [m.id for m in gevonden] == [onderkast.id]

    gevonden_tag = modellen.lijst(zoekterm="keuken")
    assert [m.id for m in gevonden_tag] == [onderkast.id]


def test_groep_velden_worden_bewaard():
    materialen, modellen = _bibliotheken()
    materiaal = materialen.toevoegen(_materiaal())
    onderdeel_1 = _onderdeel(materiaal.id, naam="Lade 1", groep_id="lades", groep_volgorde=0)
    onderdeel_2 = _onderdeel(materiaal.id, naam="Lade 2", groep_id="lades", groep_volgorde=1)
    model = modellen.toevoegen(_model(onderdelen=[onderdeel_1, onderdeel_2]))

    opgehaald = modellen.ophalen(model.id)
    assert opgehaald.onderdelen[0].groep_id == "lades"
    assert opgehaald.onderdelen[0].groep_volgorde == 0
    assert opgehaald.onderdelen[1].groep_volgorde == 1


def test_sqlite_opslag_overleeft_herstart(tmp_path):
    materialen_db = tmp_path / "materialen.db"
    modellen_db = tmp_path / "modellen.db"

    from robocutter.materialen.opslag import open_verbinding as open_materialen_verbinding

    mat_verbinding = open_materialen_verbinding(materialen_db)
    materialen = MaterialenBibliotheek(mat_verbinding)
    materiaal = materialen.toevoegen(_materiaal())

    mod_verbinding = open_verbinding(modellen_db)
    modellen = ModellenBibliotheek(materialen, mod_verbinding)
    onderkast = modellen.toevoegen(
        _model(naam="Onderkast", onderdelen=[_onderdeel(materiaal.id, groep_id="lades", groep_volgorde=0)])
    )
    keuken = modellen.toevoegen(
        _model(naam="Keuken", submodellen=[SubModelVerwijzing(model_id=onderkast.id, aantal=2)])
    )
    mod_verbinding.close()
    mat_verbinding.close()

    # Nieuwe verbindingen simuleren een herstart van de app.
    herstart_mat_verbinding = open_materialen_verbinding(materialen_db)
    herstarte_materialen = MaterialenBibliotheek(herstart_mat_verbinding)
    herstart_mod_verbinding = open_verbinding(modellen_db)
    herstarte_modellen = ModellenBibliotheek(herstarte_materialen, herstart_mod_verbinding)

    herladen_keuken = herstarte_modellen.ophalen(keuken.id)
    assert herladen_keuken.submodellen == [SubModelVerwijzing(model_id=onderkast.id, aantal=2)]
    herladen_onderkast = herstarte_modellen.ophalen(onderkast.id)
    assert herladen_onderkast.onderdelen[0].materiaal_id == materiaal.id
    assert herladen_onderkast.onderdelen[0].groep_id == "lades"
    assert herladen_onderkast.onderdelen[0].groep_volgorde == 0

    with pytest.raises(ModelInGebruikError):
        herstarte_modellen.verwijderen(onderkast.id)

    herstart_mod_verbinding.close()
    herstart_mat_verbinding.close()
