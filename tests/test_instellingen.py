"""Tests voor de instellingen-functie: laden/opslaan van het JSON-
bestand, validatie, en het (automatisch) verplaatsen van het
databasebestand bij een opslaglocatie-wijziging.

Belangrijk: ``InstellingenBeheer`` wordt hier ALTIJD met een expliciete
``standaard_data_map`` binnen ``tmp_path`` aangemaakt — nooit met de
standaard (die verwijst naar de échte ``<repo>/data``-map). Zonder die
override raakte een eerdere versie van deze tests per ongeluk het echte
ontwikkel-databasebestand aan (verplaatst naar een pytest-tmp-map);
vandaar deze expliciete, altijd-sandboxed aanpak.
"""

from __future__ import annotations

import pytest

from robocutter.instellingen.beheer import InstellingenBeheer, OpslagVerplaatsenError, valideer
from robocutter.instellingen.models import Instellingen
from robocutter.instellingen.opslag import laad_instellingen, sla_instellingen_op


def _beheer(tmp_path, **kwargs) -> InstellingenBeheer:
    return InstellingenBeheer(
        bestand_pad=tmp_path / "instellingen.json",
        standaard_data_map=tmp_path / "standaard-data",
        **kwargs,
    )


def test_laden_zonder_bestand_geeft_standaardwaarden(tmp_path):
    instellingen = laad_instellingen(tmp_path / "bestaat-niet.json")
    assert instellingen == Instellingen()


def test_laden_van_corrupt_bestand_geeft_standaardwaarden(tmp_path):
    pad = tmp_path / "instellingen.json"
    pad.write_text("dit is geen json", encoding="utf-8")
    assert laad_instellingen(pad) == Instellingen()


def test_opslaan_en_laden_roundtrip(tmp_path):
    pad = tmp_path / "instellingen.json"
    origineel = Instellingen(
        opslag_map=str(tmp_path / "andere-map"),
        thema="donker",
        bedrijfslogo_pad=str(tmp_path / "logo.png"),
        standaard_zaagstrategie="rijen",
        werkvoorbereider_naam="Sven",
    )
    sla_instellingen_op(origineel, pad)
    herladen = laad_instellingen(pad)
    assert herladen == origineel


def test_valideer_signaleert_onbekend_thema_en_strategie():
    fouten = valideer(Instellingen(thema="paars", standaard_zaagstrategie="willekeurig"))
    assert any("thema" in f.lower() for f in fouten)
    assert any("zaagstrategie" in f.lower() for f in fouten)


def test_valideer_geldige_instellingen_geeft_geen_fouten():
    assert valideer(Instellingen()) == []


def test_beheer_bijwerken_valideert_en_persisteert(tmp_path):
    beheer = _beheer(tmp_path)
    beheer.bijwerken(werkvoorbereider_naam="Sven", thema="donker")

    herladen = _beheer(tmp_path)
    assert herladen.huidige.werkvoorbereider_naam == "Sven"
    assert herladen.huidige.thema == "donker"


def test_beheer_bijwerken_met_ongeldige_waarde_faalt(tmp_path):
    beheer = _beheer(tmp_path)
    with pytest.raises(ValueError):
        beheer.bijwerken(thema="fluorescerend")


def test_effectieve_db_pad_standaard_zonder_instelling(tmp_path):
    beheer = _beheer(tmp_path)
    assert beheer.effectieve_db_pad() == tmp_path / "standaard-data" / "robocutter.db"
    assert beheer.huidige.opslag_map is None


def test_wijzig_opslaglocatie_verplaatst_bestaand_databasebestand(tmp_path):
    oude_map = tmp_path / "oud"
    oude_map.mkdir()
    oude_db = oude_map / "robocutter.db"
    oude_db.write_text("dummy-inhoud", encoding="utf-8")

    beheer = _beheer(tmp_path)
    # Forceer de "huidige" locatie op de oude map, alsof dat al eerder was ingesteld.
    beheer.bijwerken(opslag_map=str(oude_map))

    nieuwe_map = tmp_path / "nieuw"
    beheer.wijzig_opslaglocatie(nieuwe_map)

    assert beheer.effectieve_data_map() == nieuwe_map
    assert (nieuwe_map / "robocutter.db").read_text(encoding="utf-8") == "dummy-inhoud"
    assert not oude_db.exists()


def test_wijzig_opslaglocatie_zonder_bestaand_databasebestand(tmp_path):
    beheer = _beheer(tmp_path)
    nieuwe_map = tmp_path / "nieuw"
    beheer.wijzig_opslaglocatie(nieuwe_map)
    assert beheer.effectieve_data_map() == nieuwe_map
    assert not (nieuwe_map / "robocutter.db").exists()


def test_wijzig_opslaglocatie_faalt_bij_conflicterend_bestand(tmp_path):
    oude_map = tmp_path / "oud"
    oude_map.mkdir()
    (oude_map / "robocutter.db").write_text("oud", encoding="utf-8")

    nieuwe_map = tmp_path / "nieuw"
    nieuwe_map.mkdir()
    (nieuwe_map / "robocutter.db").write_text("bestaat-al", encoding="utf-8")

    beheer = _beheer(tmp_path)
    beheer.bijwerken(opslag_map=str(oude_map))

    with pytest.raises(OpslagVerplaatsenError):
        beheer.wijzig_opslaglocatie(nieuwe_map)

    # Geen van beide bestanden mag zijn aangetast door de mislukte poging.
    assert (oude_map / "robocutter.db").read_text(encoding="utf-8") == "oud"
    assert (nieuwe_map / "robocutter.db").read_text(encoding="utf-8") == "bestaat-al"
