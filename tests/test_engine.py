"""Tests voor de zaagplan-optimalisatie-motor.

Dekt de kernregels uit hoofdstuk 5: geen overlap, kerf-verrekening,
randafzaag-marge, nerfrichting-rotatie, groepering, en de
min-reststukgrootte-classificatie.
"""

from __future__ import annotations

import itertools

import pytest

from robocutter.optimalisatie.engine import genereer_zaagplan
from robocutter.optimalisatie.models import (
    Materiaal,
    Nerfrichting,
    Onderdeel,
    Rand,
)


def _rechthoeken_overlappen(a, b) -> bool:
    ax0, ay0, ax1, ay1 = a.x, a.y, a.x + a.breedte, a.y + a.hoogte
    bx0, by0, bx1, by1 = b.x, b.y, b.x + b.breedte, b.y + b.hoogte
    return ax0 < bx1 - 1e-6 and bx0 < ax1 - 1e-6 and ay0 < by1 - 1e-6 and by0 < ay1 - 1e-6


def _standaard_materiaal(**overrides) -> Materiaal:
    basis = dict(naam="Testplaat", lengte=2800, breedte=2070, dikte=18, kerf=4, min_reststukgrootte=300)
    basis.update(overrides)
    return Materiaal(**basis)


@pytest.mark.parametrize("strategie", ["efficient", "rijen"])
def test_geen_overlappende_plaatsingen(strategie):
    mat = _standaard_materiaal()
    onderdelen = [
        Onderdeel(id="a", breedte=850, hoogte=902, aantal=3),
        Onderdeel(id="b", breedte=1200, hoogte=700, aantal=2),
        Onderdeel(id="c", breedte=1390, hoogte=460, aantal=2),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie=strategie)
    assert resultaat.niet_geplaatst == []
    for p1, p2 in itertools.combinations(resultaat.plaatsingen, 2):
        assert not _rechthoeken_overlappen(p1, p2), f"{p1} overlapt met {p2}"


@pytest.mark.parametrize("strategie", ["efficient", "rijen"])
def test_alle_plaatsingen_binnen_de_plaat(strategie):
    mat = _standaard_materiaal()
    onderdelen = [Onderdeel(id="a", breedte=850, hoogte=902, aantal=3)]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie=strategie)
    for p in resultaat.plaatsingen:
        assert p.x >= -1e-6
        assert p.y >= -1e-6
        assert p.x + p.breedte <= mat.lengte + 1e-6
        assert p.y + p.hoogte <= mat.breedte + 1e-6


def test_kerf_wordt_aangehouden_tussen_onderdelen_in_een_rij():
    mat = _standaard_materiaal(kerf=4)
    onderdelen = [Onderdeel(id="a", breedte=500, hoogte=500, aantal=2)]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="rijen")
    xs = sorted(p.x for p in resultaat.plaatsingen)
    # Tweede onderdeel moet minstens breedte + kerf verder beginnen.
    assert xs[1] >= xs[0] + 500 + mat.kerf - 1e-6


def test_randafzaag_marge_wordt_gerespecteerd():
    mat = _standaard_materiaal(
        randafzaag_marge=10, randafzaag_randen=frozenset({Rand.LINKS, Rand.ONDER, Rand.RECHTS, Rand.BOVEN})
    )
    onderdelen = [Onderdeel(id="a", breedte=500, hoogte=500, aantal=1)]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="efficient")
    p = resultaat.plaatsingen[0]
    assert p.x >= 10 - 1e-6
    assert p.y >= 10 - 1e-6
    assert p.x + p.breedte <= mat.lengte - 10 + 1e-6
    assert p.y + p.hoogte <= mat.breedte - 10 + 1e-6


def test_fabriekskantenband_rand_wordt_niet_afgezaagd_ook_niet_met_randafzaag():
    # Links staat zowel in randafzaag_randen als fabriekskantenband_randen ->
    # de fabrieksrand moet winnen, dus geen marge aan de linkerkant.
    mat = _standaard_materiaal(
        randafzaag_marge=10,
        randafzaag_randen=frozenset({Rand.LINKS}),
        fabriekskantenband_randen=frozenset({Rand.LINKS}),
    )
    onderdelen = [Onderdeel(id="a", breedte=500, hoogte=500, aantal=1, fabriekskantenband_vereist=True)]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="efficient")
    p = resultaat.plaatsingen[0]
    assert p.x == pytest.approx(0.0)


def test_nerfrichting_lange_zijde_dwingt_orientatie_af():
    mat = _standaard_materiaal()
    # Onderdeel is "liggend" (breder dan hoog) maar vraagt lange zijde
    # -> mag niet roteren, blijft dus liggend t.o.v. de x-as.
    onderdeel = Onderdeel(id="a", breedte=800, hoogte=300, aantal=1, nerfrichting_vereist=Nerfrichting.LANGE_ZIJDE)
    resultaat = genereer_zaagplan(mat, [onderdeel], strategie="efficient")
    p = resultaat.plaatsingen[0]
    assert p.breedte == 800 and p.hoogte == 300 and p.geroteerd is False

    # Nu staand (hoger dan breed) met dezelfde eis -> moet roteren zodat
    # de lange zijde (800) alsnog evenwijdig aan de x-as komt.
    onderdeel2 = Onderdeel(id="b", breedte=300, hoogte=800, aantal=1, nerfrichting_vereist=Nerfrichting.LANGE_ZIJDE)
    resultaat2 = genereer_zaagplan(mat, [onderdeel2], strategie="efficient")
    p2 = resultaat2.plaatsingen[0]
    assert p2.breedte == 800 and p2.hoogte == 300 and p2.geroteerd is True


def test_nerfrichting_korte_zijde_is_tegenovergesteld_van_lange_zijde():
    mat = _standaard_materiaal()
    onderdeel = Onderdeel(id="a", breedte=800, hoogte=300, aantal=1, nerfrichting_vereist=Nerfrichting.KORTE_ZIJDE)
    resultaat = genereer_zaagplan(mat, [onderdeel], strategie="efficient")
    p = resultaat.plaatsingen[0]
    # Lange zijde (800) moet nu loodrecht op de x-as staan -> breedte=300, hoogte=800.
    assert p.breedte == 300 and p.hoogte == 800


def test_groep_wordt_aaneengesloten_en_in_volgorde_geplaatst():
    mat = _standaard_materiaal()
    onderdelen = [
        Onderdeel(id="ladefront-1", breedte=400, hoogte=180, groep_id="g1", groep_volgorde=1),
        Onderdeel(id="ladefront-2", breedte=400, hoogte=180, groep_id="g1", groep_volgorde=2),
        Onderdeel(id="ladefront-3", breedte=400, hoogte=180, groep_id="g1", groep_volgorde=3),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="efficient")
    op_id = {p.onderdeel_id: p for p in resultaat.plaatsingen}
    p1, p2, p3 = op_id["ladefront-1"], op_id["ladefront-2"], op_id["ladefront-3"]
    # Zelfde x (zelfde kolom) en oplopende y in de opgegeven volgorde.
    assert p1.x == p2.x == p3.x
    assert p1.y < p2.y < p3.y
    assert p2.y >= p1.y + p1.hoogte  # geen overlap, kerf ertussen


def test_min_reststukgrootte_classificeert_klein_gat_als_afval():
    mat = _standaard_materiaal(min_reststukgrootte=300)
    # Onderdeel dat een smalle reststrook overlaat (< 300mm breed).
    onderdeel = Onderdeel(id="a", breedte=2600, hoogte=2070, aantal=1)
    resultaat = genereer_zaagplan(mat, [onderdeel], strategie="efficient")
    assert resultaat.reststukken == []
    assert resultaat.afval_oppervlak > 0


def test_min_reststukgrootte_classificeert_groot_gat_als_reststuk():
    mat = _standaard_materiaal(min_reststukgrootte=300)
    onderdeel = Onderdeel(id="a", breedte=2000, hoogte=1500, aantal=1)
    resultaat = genereer_zaagplan(mat, [onderdeel], strategie="efficient")
    assert len(resultaat.reststukken) >= 1
    for r in resultaat.reststukken:
        assert r.breedte >= 300 and r.hoogte >= 300


def test_te_veel_onderdelen_worden_gerapporteerd_als_niet_geplaatst():
    mat = _standaard_materiaal(lengte=1000, breedte=1000)
    onderdelen = [Onderdeel(id="a", breedte=900, hoogte=900, aantal=3)]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="efficient")
    assert len(resultaat.plaatsingen) == 1
    assert len(resultaat.niet_geplaatst) == 2


def test_onbekende_strategie_geeft_duidelijke_fout():
    mat = _standaard_materiaal()
    with pytest.raises(ValueError):
        genereer_zaagplan(mat, [], strategie="onzin")
