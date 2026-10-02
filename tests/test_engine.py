"""Tests voor de zaagplan-optimalisatie-motor.

Dekt de kernregels uit hoofdstuk 5: geen overlap, kerf-verrekening,
randafzaag-marge, nerfrichting-rotatie, groepering, en de
min-reststukgrootte-classificatie.
"""

from __future__ import annotations

import itertools
import random
import math
import time

import pytest

from robocutter.optimalisatie.engine import genereer_zaagplan, genereer_zaagplannen, schat_aantal_platen
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


def _snede_kruist_plaatsing(snede, p) -> bool:
    """True als ``snede`` dwars door het binnenste van plaatsing ``p``
    loopt (i.p.v. er alleen langs de rand van te lopen)."""
    if snede.richting == "verticaal":
        binnen_x = p.x < snede.positie < p.x + p.breedte
        binnen_y = snede.start < p.y + p.hoogte and snede.einde > p.y
    else:
        binnen_y = p.y < snede.positie < p.y + p.hoogte
        binnen_x = snede.start < p.x + p.breedte and snede.einde > p.x
    return binnen_x and binnen_y


def _standaard_materiaal(**overrides) -> Materiaal:
    basis = dict(naam="Testplaat", lengte=2800, breedte=2070, dikte=18, kerf=4, min_reststukgrootte=300)
    basis.update(overrides)
    return Materiaal(**basis)


@pytest.mark.parametrize("strategie", ["cnc", "horizontaal"])
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


@pytest.mark.parametrize("strategie", ["cnc", "horizontaal", "guillotine"])
def test_geplaatste_stukken_overlappen_nooit_ongeacht_strategie(strategie):
    # Zelfde mix als hierboven, maar zonder te eisen dat alles geplaatst
    # wordt: "guillotine" is bewust minder efficiënt (uitsluitend
    # rand-tot-rand sneden), dus kan op een krappe plaat stukken
    # onplaatsbaar laten — dat is geen bug, zie engine.py. Geen overlap is
    # wel een harde eis voor elke strategie.
    mat = _standaard_materiaal()
    onderdelen = [
        Onderdeel(id="a", breedte=850, hoogte=902, aantal=3),
        Onderdeel(id="b", breedte=1200, hoogte=700, aantal=2),
        Onderdeel(id="c", breedte=1390, hoogte=460, aantal=2),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie=strategie)
    for p1, p2 in itertools.combinations(resultaat.plaatsingen, 2):
        assert not _rechthoeken_overlappen(p1, p2), f"{p1} overlapt met {p2}"


@pytest.mark.parametrize("strategie", ["cnc", "horizontaal", "guillotine"])
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
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="horizontaal")
    xs = sorted(p.x for p in resultaat.plaatsingen)
    # Tweede onderdeel moet minstens breedte + kerf verder beginnen.
    assert xs[1] >= xs[0] + 500 + mat.kerf - 1e-6


def test_randafzaag_marge_wordt_gerespecteerd():
    mat = _standaard_materiaal(
        randafzaag_marge=10, randafzaag_randen=frozenset({Rand.LINKS, Rand.ONDER, Rand.RECHTS, Rand.BOVEN})
    )
    onderdelen = [Onderdeel(id="a", breedte=500, hoogte=500, aantal=1)]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="cnc")
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
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="cnc")
    p = resultaat.plaatsingen[0]
    assert p.x == pytest.approx(0.0)


def test_nerfrichting_lange_zijde_dwingt_orientatie_af():
    mat = _standaard_materiaal()
    # Onderdeel is "liggend" (breder dan hoog) maar vraagt lange zijde
    # -> mag niet roteren, blijft dus liggend t.o.v. de x-as.
    onderdeel = Onderdeel(id="a", breedte=800, hoogte=300, aantal=1, nerfrichting_vereist=Nerfrichting.LANGE_ZIJDE)
    resultaat = genereer_zaagplan(mat, [onderdeel], strategie="cnc")
    p = resultaat.plaatsingen[0]
    assert p.breedte == 800 and p.hoogte == 300 and p.geroteerd is False

    # Nu staand (hoger dan breed) met dezelfde eis -> moet roteren zodat
    # de lange zijde (800) alsnog evenwijdig aan de x-as komt.
    onderdeel2 = Onderdeel(id="b", breedte=300, hoogte=800, aantal=1, nerfrichting_vereist=Nerfrichting.LANGE_ZIJDE)
    resultaat2 = genereer_zaagplan(mat, [onderdeel2], strategie="cnc")
    p2 = resultaat2.plaatsingen[0]
    assert p2.breedte == 800 and p2.hoogte == 300 and p2.geroteerd is True


def test_nerfrichting_korte_zijde_is_tegenovergesteld_van_lange_zijde():
    mat = _standaard_materiaal()
    onderdeel = Onderdeel(id="a", breedte=800, hoogte=300, aantal=1, nerfrichting_vereist=Nerfrichting.KORTE_ZIJDE)
    resultaat = genereer_zaagplan(mat, [onderdeel], strategie="cnc")
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
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="cnc")
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
    resultaat = genereer_zaagplan(mat, [onderdeel], strategie="cnc")
    assert resultaat.reststukken == []
    assert resultaat.afval_oppervlak > 0


def test_min_reststukgrootte_classificeert_groot_gat_als_reststuk():
    mat = _standaard_materiaal(min_reststukgrootte=300)
    onderdeel = Onderdeel(id="a", breedte=2000, hoogte=1500, aantal=1)
    resultaat = genereer_zaagplan(mat, [onderdeel], strategie="cnc")
    assert len(resultaat.reststukken) >= 1
    for r in resultaat.reststukken:
        assert r.breedte >= 300 and r.hoogte >= 300


def test_te_veel_onderdelen_worden_gerapporteerd_als_niet_geplaatst():
    mat = _standaard_materiaal(lengte=1000, breedte=1000)
    onderdelen = [Onderdeel(id="a", breedte=900, hoogte=900, aantal=3)]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="cnc")
    assert len(resultaat.plaatsingen) == 1
    assert len(resultaat.niet_geplaatst) == 2


def test_onbekende_strategie_geeft_duidelijke_fout():
    mat = _standaard_materiaal()
    with pytest.raises(ValueError):
        genereer_zaagplan(mat, [], strategie="onzin")


def test_rijen_stapelt_meerdere_smallere_onderdelen_side_by_side_in_een_band():
    # Svens concrete voorbeeld: een "bodem" laat, binnen zijn eigen kolom,
    # nog verticale restruimte over (110mm) waar meerdere "dwarsbalken"
    # (elk 100mm hoog) NAAST ELKAAR in passen i.p.v. dat er maar één per
    # band gebruikt wordt en de rest van de kolombreedte braak blijft
    # liggen: "als je een bodem hebt van 500mm lang dan passen daar ook 4
    # dwarsbalken binnen in die strook van 100mm".
    mat = _standaard_materiaal(lengte=700, breedte=900, kerf=4, min_reststukgrootte=0)
    onderdelen = [
        # Hoogste groep: bepaalt de rijhoogte (710) en krijgt zijn eigen,
        # smalle kolom (90mm) waar geen dwarsbalk (120mm breed) op past.
        Onderdeel(id="anker", breedte=90, hoogte=710, aantal=1),
        # Tweede groep: te breed (500mm) om op de anker-kolom te stapelen
        # -> eigen nieuwe kolom van 500mm breed, 600mm hoog (110mm over).
        Onderdeel(id="bodem", breedte=500, hoogte=600, aantal=1),
        # Derde (kortste) groep: 4x 120mm breed, 100mm hoog -- passen qua
        # hoogte in de 110mm restruimte boven de bodem, en qua breedte
        # (4x120 + 3x kerf = 492mm) ruim binnen de bodem's 500mm kolom.
        Onderdeel(id="dwarsbalk", breedte=120, hoogte=100, aantal=4),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="horizontaal")

    assert resultaat.niet_geplaatst == []
    assert len(resultaat.plaatsingen) == 6

    dwarsbalken = [p for p in resultaat.plaatsingen if p.onderdeel_id == "dwarsbalk"]
    assert len(dwarsbalken) == 4
    # Allemaal in dezelfde band (side-by-side): gelijke y, oplopende x.
    ys = {round(p.y, 6) for p in dwarsbalken}
    assert len(ys) == 1
    xs = sorted(p.x for p in dwarsbalken)
    assert xs == sorted(set(xs))  # geen twee op precies dezelfde x

    bodem = next(p for p in resultaat.plaatsingen if p.onderdeel_id == "bodem")
    # De dwarsbalken-band staat boven op de bodem, binnen zijn kolom (x).
    for p in dwarsbalken:
        assert p.x >= bodem.x - 1e-6
        assert p.x + p.breedte <= bodem.x + bodem.breedte + 1e-6
        assert p.y >= bodem.y + bodem.hoogte - 1e-6

    for a, b in itertools.combinations(resultaat.plaatsingen, 2):
        assert not _rechthoeken_overlappen(a, b)


def test_rijen_laat_later_lid_van_dezelfde_groep_stapelen_op_nieuwe_kolom_van_eerder_lid():
    # Echt teruggevonden scenario (Sven's testproject "Keuken Jansen",
    # materiaal "Melamine grijs 18"): twee identieke "lade rug korf"-
    # stukken passen geen van beiden nog op de (al volledig hoge)
    # kolommen van de vorige groep ("lade bodem") -- zonder de fixed-
    # point-herhaling in _vul_rij kreeg de TWEEDE dan zijn eigen, aparte
    # kolom, terwijl hij prima op de zojuist aangemaakte kolom van de
    # EERSTE had gepast: "die 2e lade rug korf past makkelijk nog onder
    # de andere 2 lade ruggen" (een derde, nog kortere "lade rug bestek"
    # stapelt in de praktijk ook nog daarboven).
    mat = _standaard_materiaal(lengte=2200, breedte=500, kerf=3, min_reststukgrootte=0)
    onderdelen = [
        Onderdeel(id="lade_bodem", breedte=506, hoogte=500, aantal=3),
        Onderdeel(id="lade_rug_korf", breedte=506, hoogte=170, aantal=2),
        Onderdeel(id="lade_rug_bestek", breedte=506, hoogte=70, aantal=1),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="horizontaal")

    assert resultaat.niet_geplaatst == []
    ruggen = [
        p for p in resultaat.plaatsingen if p.onderdeel_id in ("lade_rug_korf", "lade_rug_bestek")
    ]
    assert len(ruggen) == 3
    # Alle drie in dezelfde kolom (gelijke x), gestapeld op oplopende y.
    xs = {round(p.x, 6) for p in ruggen}
    assert len(xs) == 1

    for a, b in itertools.combinations(resultaat.plaatsingen, 2):
        assert not _rechthoeken_overlappen(a, b)


@pytest.mark.parametrize("strategie", ["cnc", "horizontaal"])
def test_rijen_vult_verticale_restruimte_boven_kortere_onderdelen(strategie):
    # Sven: "checkt dat bepaalde items ... minder [hoog] zijn dan de
    # rijhoogte en deze dan in de rij kan plaatsen zodat je efficiëntie
    # houdt" -- een onderdeel dat niet meer horizontaal in de rij/strook
    # past, maar wel verticaal boven een korter onderdeel in dezelfde
    # rij/strook, hoeft niet meer te wachten op een nieuwe rij/strook.
    # Nerf-eisen vastgezet zodat de bekende afmetingen niet alsnog
    # geroteerd worden (zie ook de "paneel"-toelichting hieronder).
    mat = _standaard_materiaal(lengte=1000, breedte=1000, kerf=4, min_reststukgrootte=0)
    onderdelen = [
        Onderdeel(id="tall", breedte=100, hoogte=600, aantal=1, nerfrichting_vereist=Nerfrichting.KORTE_ZIJDE),
        Onderdeel(id="wide", breedte=896, hoogte=200, aantal=1, nerfrichting_vereist=Nerfrichting.LANGE_ZIJDE),
        Onderdeel(id="vulling", breedte=500, hoogte=150, aantal=1, nerfrichting_vereist=Nerfrichting.LANGE_ZIJDE),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie=strategie)
    assert resultaat.niet_geplaatst == []
    wide = next(p for p in resultaat.plaatsingen if p.onderdeel_id == "wide")
    vulling = next(p for p in resultaat.plaatsingen if p.onderdeel_id == "vulling")
    assert vulling.x == pytest.approx(wide.x)
    assert vulling.y == pytest.approx(wide.y + wide.hoogte + mat.kerf)
    for p1, p2 in itertools.combinations(resultaat.plaatsingen, 2):
        assert not _rechthoeken_overlappen(p1, p2), f"{p1} overlapt met {p2}"
    for snede in resultaat.zaagvolgorde:
        for plaatsing in resultaat.plaatsingen:
            assert not _snede_kruist_plaatsing(snede, plaatsing), f"{snede} kruist {plaatsing}"


def test_rijen_vult_verticale_restruimte_ook_met_geroteerd_onderdeel():
    # Zelfde idee als hierboven, maar nu past de vulling alleen geroteerd
    # (breedte/hoogte omgewisseld) in het overgebleven gat -- moet net als
    # de horizontale plaatsing (_pak_efficient/_pak_guillotine) ook hier
    # de geroteerde oriëntatie proberen voor een vrij-roteerbaar onderdeel.
    mat = _standaard_materiaal(lengte=1000, breedte=1000, kerf=4, min_reststukgrootte=0)
    onderdelen = [
        Onderdeel(id="tall", breedte=100, hoogte=600, aantal=1, nerfrichting_vereist=Nerfrichting.KORTE_ZIJDE),
        Onderdeel(id="wide", breedte=896, hoogte=200, aantal=1, nerfrichting_vereist=Nerfrichting.LANGE_ZIJDE),
        # Vulling: 150 x 500 (ongeroteerd te hoog voor het gat van 400),
        # maar geroteerd (500 x 150) past het net als in de vorige test.
        Onderdeel(id="vulling", breedte=150, hoogte=500, aantal=1),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="horizontaal")
    assert resultaat.niet_geplaatst == []
    vulling = next(p for p in resultaat.plaatsingen if p.onderdeel_id == "vulling")
    assert vulling.geroteerd is True
    assert vulling.breedte == pytest.approx(500)
    assert vulling.hoogte == pytest.approx(150)
    for p1, p2 in itertools.combinations(resultaat.plaatsingen, 2):
        assert not _rechthoeken_overlappen(p1, p2), f"{p1} overlapt met {p2}"


@pytest.mark.parametrize("strategie", ["horizontaal"])
def test_groep_interne_snede_blijft_binnen_eigen_kolom(strategie):
    # Een gestapelde groep (bv. ladefronten) naast een los onderdeel van
    # een heel andere hoogte in dezelfde rij/strook: de sneden die de
    # groepsleden van elkaar scheiden mogen alleen de breedte van de
    # groep-kolom zelf overspannen, nooit de volle plaatbreedte -- anders
    # loopt zo'n snede dwars door het losse onderdeel ernaast heen.
    mat = _standaard_materiaal(lengte=1500, breedte=900, kerf=4)
    onderdelen = [
        Onderdeel(id="front_onder", breedte=596, hoogte=220, groep_id="g1", groep_volgorde=1),
        Onderdeel(id="front_midden", breedte=596, hoogte=180, groep_id="g1", groep_volgorde=2),
        Onderdeel(id="front_boven", breedte=596, hoogte=180, groep_id="g1", groep_volgorde=3),
        # Nerf-eis vastgezet zodat "paneel" zijn 588-hoogte behoudt (dus in
        # dezelfde rij/strook als de even hoge groep terechtkomt, wat deze
        # test bewust nodig heeft) i.p.v. te roteren naar de kortere
        # landschap-oriëntatie die "horizontaal" sinds de rotatiefix
        # kiezen voor een vrij-roteerbaar onderdeel.
        Onderdeel(id="paneel", breedte=500, hoogte=588, aantal=1, nerfrichting_vereist=Nerfrichting.KORTE_ZIJDE),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie=strategie)
    assert resultaat.niet_geplaatst == []
    for snede in resultaat.zaagvolgorde:
        for plaatsing in resultaat.plaatsingen:
            assert not _snede_kruist_plaatsing(snede, plaatsing), f"{snede} kruist {plaatsing}"
    groep_sneden = [s for s in resultaat.zaagvolgorde if s.richting == "horizontaal" and s.einde - s.start < mat.lengte]
    assert len(groep_sneden) == 2  # de 2 naden tussen de 3 groepsleden
    for s in groep_sneden:
        # Van rand tot rand van het deelgebied van de groep-kolom: dat begint
        # direct na het paneel (500) — de kerf ertussen (500..504) hoort bij
        # dat deelgebied (zie _zet_sneden_op_deelgebieden) — en eindigt bij
        # de rand van de groep (1100).
        assert 500.0 - 1e-6 <= s.start <= 504.0 + 1e-6
        assert s.einde == pytest.approx(1100.0)


@pytest.mark.parametrize("strategie", ["horizontaal", "verticaal", "cnc", "guillotine"])
def test_geen_enkele_snede_kruist_een_plaatsing(strategie):
    # Bredere, minder gerichte check dan hierboven: over alle vier
    # strategieën tegelijk, met een mix van een groep, losse onderdelen
    # van verschillende hoogte, en aantallen > 1.
    mat = _standaard_materiaal(lengte=1500, breedte=900, kerf=4, min_reststukgrootte=0)
    onderdelen = [
        Onderdeel(id="front_onder", breedte=596, hoogte=220, groep_id="g1", groep_volgorde=1),
        Onderdeel(id="front_midden", breedte=596, hoogte=180, groep_id="g1", groep_volgorde=2),
        Onderdeel(id="front_boven", breedte=596, hoogte=180, groep_id="g1", groep_volgorde=3),
        Onderdeel(id="paneel", breedte=500, hoogte=588, aantal=1),
        Onderdeel(id="klein", breedte=300, hoogte=150, aantal=2),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie=strategie)
    for snede in resultaat.zaagvolgorde:
        for plaatsing in resultaat.plaatsingen:
            assert not _snede_kruist_plaatsing(snede, plaatsing), f"{snede} kruist {plaatsing}"


def test_fabriekskantenband_gebruikt_meerdere_beschikbare_randen():
    # Sven: een plaat met fabriekskantenband op zowel onder als boven
    # moet beide randen benutten i.p.v. alleen de eerste (voorheen bleef
    # de tweede rand ongebruikt, ook als de eerste strook vol zat).
    mat = _standaard_materiaal(
        lengte=1000, breedte=700, kerf=4, min_reststukgrootte=0,
        fabriekskantenband_randen=frozenset({Rand.ONDER, Rand.BOVEN}),
    )
    onderdelen = [
        Onderdeel(id=f"fabriek{i}", breedte=300, hoogte=150, aantal=1, fabriekskantenband_vereist=True)
        for i in range(6)
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="horizontaal")
    assert resultaat.niet_geplaatst == []
    ys = sorted({round(p.y, 1) for p in resultaat.plaatsingen})
    assert ys == [0.0, 550.0]  # onder-strook (y=0) én boven-strook (y=breedte-hoogte)
    for p1, p2 in itertools.combinations(resultaat.plaatsingen, 2):
        assert not _rechthoeken_overlappen(p1, p2), f"{p1} overlapt met {p2}"

    # Zelfde plaat/onderdelen, maar dan met maar één beschikbare rand:
    # nu past nog maar de helft, de rest is echt niet-geplaatst.
    mat_een_rand = _standaard_materiaal(
        lengte=1000, breedte=700, kerf=4, min_reststukgrootte=0,
        fabriekskantenband_randen=frozenset({Rand.ONDER}),
    )
    resultaat_een_rand = genereer_zaagplan(mat_een_rand, onderdelen, strategie="horizontaal")
    assert len(resultaat_een_rand.niet_geplaatst) == 3


def test_fabriekskantenband_respecteert_kantenband_randen_zonder_kwartslag():
    # Sven, over een dwarsbalk in een echt testproject: "de dwarsbalk
    # geroteerd dat de korte kant de kantenband raakt maar is het niet
    # zo dat de kantenband de lange zijde moet hebben". Kern van de bug:
    # de motor koos alleen een willekeurige beschikbare rand en roteerde
    # zo nodig, zonder te kijken welke kant van het onderdeel zelf
    # (kantenband_randen) de band nodig heeft. Nu: elk onderdeel gaat
    # alleen naar ZIJN eigen aangewezen rand, in zijn eigen
    # (niet-geroteerde) oriëntatie.
    mat = _standaard_materiaal(
        lengte=1000, breedte=700, kerf=4, min_reststukgrootte=0,
        fabriekskantenband_randen=frozenset({Rand.ONDER, Rand.BOVEN}),
    )
    onderdelen = [
        # Lange zijde (564) moet de kantenband op BOVEN raken.
        Onderdeel(id="dwarsbalk_boven", breedte=564, hoogte=100, aantal=1,
                  kantenband_randen=frozenset({Rand.BOVEN}), fabriekskantenband_vereist=True),
        # Een ander onderdeel wil juist de ONDER-rand.
        Onderdeel(id="plank_onder", breedte=400, hoogte=120, aantal=1,
                  kantenband_randen=frozenset({Rand.ONDER}), fabriekskantenband_vereist=True),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="horizontaal")
    assert resultaat.niet_geplaatst == []
    dwarsbalk = next(p for p in resultaat.plaatsingen if p.onderdeel_id == "dwarsbalk_boven")
    plank = next(p for p in resultaat.plaatsingen if p.onderdeel_id == "plank_onder")
    # Geen kwartslag: de lange zijde (waar de kantenband op zit) ligt
    # langs de rand, dus hun eigen breedte/hoogte zoals opgegeven.
    assert not dwarsbalk.geroteerd and (dwarsbalk.breedte, dwarsbalk.hoogte) == (564, 100)
    assert not plank.geroteerd and (plank.breedte, plank.hoogte) == (400, 120)
    # Elk raakt met die lange zijde een fabrieksrand: ongedraaid tegen
    # de eigen rand, of een halve slag gedraaid tegen de tegenoverliggende
    # (ook een fabrieksrand op deze plaat) — beide leggen de juiste zijde
    # tegen de fabriekskantenband.
    for p in (dwarsbalk, plank):
        assert p.y == pytest.approx(0.0) or p.y + p.hoogte == pytest.approx(mat.breedte)


def test_fabriekskantenband_met_nerfrichting_conflict_valt_terug_op_gewoon_onderdeel():
    # Een onderdeel met zowel een kantenband_randen-eis als een eigen
    # nerfrichting-eis kan door die nerf-eis alsnog gedwongen geroteerd
    # worden (nerf gaat voor) -- wat de kantenband-rand-garantie zou
    # doorbreken. Zo'n onderdeel mag dan niet via de fabriekskantenband-
    # rand-matching geplaatst worden (waar juist GEEN rotatie meer mag),
    # maar moet gewoon meedraaien met de rest van het werkgebied.
    mat = _standaard_materiaal(
        lengte=1000, breedte=700, kerf=4, min_reststukgrootte=0,
        fabriekskantenband_randen=frozenset({Rand.ONDER, Rand.BOVEN}),
    )
    onderdelen = [
        Onderdeel(
            id="conflict", breedte=564, hoogte=100, aantal=1,
            kantenband_randen=frozenset({Rand.BOVEN}), fabriekskantenband_vereist=True,
            nerfrichting_vereist=Nerfrichting.KORTE_ZIJDE,
        ),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="horizontaal")
    # Nog steeds gewoon geplaatst (via het normale werkgebied), niet
    # stilzwijgend verloren of vast blijven zitten in de fabriek-route.
    assert resultaat.niet_geplaatst == []
    assert len(resultaat.plaatsingen) == 1


def test_fabriekskantenband_strook_krijgt_eigen_scheidingssnede():
    # Hiaat 1 (zie OVERDRACHT.md): de fabriekskantenband-strook leverde
    # zelf geen Zaagsnede op, terwijl er fysiek wel een snede nodig is om
    # 'm van de rest van de plaat te scheiden.
    mat = _standaard_materiaal(kerf=4, fabriekskantenband_randen=frozenset({Rand.LINKS}))
    onderdelen = [
        Onderdeel(id="fabriek", breedte=500, hoogte=500, aantal=1, fabriekskantenband_vereist=True),
        Onderdeel(id="rest", breedte=400, hoogte=400, aantal=1),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="horizontaal")
    eerste = min(resultaat.zaagvolgorde, key=lambda s: s.volgnummer)
    assert eerste.richting == "verticaal"
    # Op de rand van de strook zelf (het stuk van 500), vóór de kerf.
    assert eerste.positie == pytest.approx(500)
    assert eerste.start == pytest.approx(0.0)
    assert eerste.einde == pytest.approx(mat.breedte)


def test_rijen_enkele_rij_krijgt_scheidingssnede_naar_restruimte_erboven():
    # Hiaat 2 (zie OVERDRACHT.md): bij precies één gebruikte rij ontbrak
    # de horizontale snede die die rij scheidt van het reststuk erboven.
    mat = _standaard_materiaal(lengte=2800, breedte=2070, kerf=4)
    onderdelen = [Onderdeel(id="a", breedte=800, hoogte=500, aantal=2)]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="horizontaal")
    assert resultaat.niet_geplaatst == []
    horizontale_sneden = [s for s in resultaat.zaagvolgorde if s.richting == "horizontaal"]
    assert len(horizontale_sneden) == 1
    snede = horizontale_sneden[0]
    assert snede.positie == pytest.approx(500)
    assert snede.start == pytest.approx(0.0)
    assert snede.einde == pytest.approx(mat.lengte)


def test_rijen_houdt_identieke_onderdelen_bij_elkaar_in_een_rij():
    # Hiaat 3 (zie OVERDRACHT.md), het belangrijkste: twee identieke
    # onderdelen mogen niet losraken over twee rijen puur omdat er na de
    # hogere stukken toevallig net plek was voor precies één van de twee.
    # Plaatlengte zo gekozen dat er na de twee zijkant-stukken toevallig
    # net plek over is voor precies één bodemplaat, niet voor twee --
    # exact het scenario dat de oude, ongegroepeerde rij-vulling liet
    # versnipperen.
    mat = _standaard_materiaal(lengte=2148, breedte=2070, kerf=4)
    onderdelen = [
        Onderdeel(id="zijkant", breedte=720, hoogte=720, aantal=2),
        Onderdeel(id="bodem", breedte=564, hoogte=560, aantal=2),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="horizontaal")
    assert resultaat.niet_geplaatst == []
    bodems = sorted((p for p in resultaat.plaatsingen if p.onderdeel_id == "bodem"), key=lambda p: p.x)
    # Allebei op dezelfde y (zelfde rij) i.p.v. verspreid over twee rijen.
    assert bodems[0].y == pytest.approx(bodems[1].y)


def test_rijen_slaat_te_hoge_groep_over_en_plaatst_kleinere_onderdelen_alsnog():
    # Hiaat 4 (zie OVERDRACHT.md): een groep die als hoogste/eerste rij
    # gekozen wordt maar niet in de plaathoogte past, mocht niet langer de
    # hele rest van de onderdelenlijst als niet-geplaatst laten wegvallen
    # -- kleinere onderdelen verderop in de lijst moeten alsnog in een
    # (lagere) rij geplaatst worden. Exact het testproject-scenario:
    # de ladefronten-groep past niet op een 600x500 plaatje, de
    # lade-bodems (elk apart wél passend) horen dan alsnog geplaatst te
    # worden i.p.v. ook te sneuvelen.
    mat = _standaard_materiaal(lengte=600, breedte=500, kerf=4, min_reststukgrootte=0)
    onderdelen = [
        Onderdeel(id="front_onder", breedte=596, hoogte=220, groep_id="lades", groep_volgorde=1),
        Onderdeel(id="front_midden", breedte=596, hoogte=180, groep_id="lades", groep_volgorde=2),
        Onderdeel(id="front_boven", breedte=596, hoogte=180, groep_id="lades", groep_volgorde=3),
        Onderdeel(id="lade_bodem", breedte=550, hoogte=400, aantal=1),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="horizontaal")
    assert resultaat.niet_geplaatst == ["groep:lades"]
    assert len(resultaat.plaatsingen) == 1
    assert resultaat.plaatsingen[0].onderdeel_id == "lade_bodem"


def test_rijen_stopt_pas_als_ook_de_laagste_resterende_groep_niet_meer_past():
    # Tegenhanger van de vorige test: als ZELFS het kleinste resterende
    # onderdeel niet meer past (plaat verticaal echt vol), moet alles wat
    # nog over is terecht als niet-geplaatst eindigen -- geen regressie
    # naar "altijd maar doorproberen".
    mat = _standaard_materiaal(lengte=600, breedte=250, kerf=4, min_reststukgrootte=0)
    onderdelen = [
        Onderdeel(id="past_al_niet", breedte=550, hoogte=220, aantal=1),
        Onderdeel(id="past_ook_niet", breedte=550, hoogte=100, aantal=1),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="horizontaal")
    # De eerste (hoogste) past nog wel (220 < 250); de tweede rij zou
    # cursor_y=224 + 100 = 324 > 250 zijn, past dus niet meer.
    assert len(resultaat.plaatsingen) == 1
    assert resultaat.plaatsingen[0].onderdeel_id == "past_al_niet"
    assert resultaat.niet_geplaatst == ["past_ook_niet#1"]


@pytest.mark.parametrize("strategie", ["guillotine", "horizontaal"])
def test_eerste_snede_is_rand_tot_rand_van_de_hele_plaat(strategie):
    mat = _standaard_materiaal(lengte=2800, breedte=2070, kerf=4)
    onderdelen = [
        Onderdeel(id="a", breedte=850, hoogte=902, aantal=3),
        Onderdeel(id="b", breedte=1200, hoogte=700, aantal=2),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie=strategie)
    assert resultaat.zaagvolgorde, f"{strategie} moet minstens één snede opleveren bij meerdere onderdelen"
    eerste = min(resultaat.zaagvolgorde, key=lambda s: s.volgnummer)
    if eerste.richting == "verticaal":
        assert eerste.start == pytest.approx(0.0)
        assert eerste.einde == pytest.approx(mat.breedte)
    else:
        assert eerste.start == pytest.approx(0.0)
        assert eerste.einde == pytest.approx(mat.lengte)


@pytest.mark.parametrize("strategie", ["cnc", "guillotine", "horizontaal", "verticaal"])
def test_elke_snede_is_rand_tot_rand_van_zijn_eigen_deelgebied(strategie):
    # Sterkere check dan alleen de eerste snede: reconstrueer voor elke
    # snede het deelgebied waarin hij viel (op basis van alle eerdere
    # sneden) en controleer dat start/einde exact de randen van dat
    # deelgebied raken -- dat garandeert dat een snede nooit dwars door
    # een al geplaatst onderdeel heen loopt. Geldt voor "guillotine" via
    # _splits_vrije_rechthoek, en sinds de rij-hoogte-bugfix ook voor
    # "horizontaal"/"verticaal" (zie _bouw_zaagvolgorde_uit_rijen). "cnc"
    # heeft geen zaagvolgorde, dus daar is niets te controleren.
    mat = _standaard_materiaal(lengte=2800, breedte=2070, kerf=4)
    onderdelen = [
        Onderdeel(id="a", breedte=850, hoogte=902, aantal=3),
        Onderdeel(id="b", breedte=1200, hoogte=700, aantal=2),
        Onderdeel(id="c", breedte=1390, hoogte=460, aantal=2),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie=strategie)
    deelgebieden = [(0.0, 0.0, mat.lengte, mat.breedte)]
    for snede in sorted(resultaat.zaagvolgorde, key=lambda s: s.volgnummer):
        gevonden = None
        for gebied in deelgebieden:
            gx0, gy0, gx1, gy1 = gebied
            if snede.richting == "verticaal":
                if gx0 - 1e-6 <= snede.positie <= gx1 + 1e-6 and snede.start == pytest.approx(gy0) and snede.einde == pytest.approx(gy1):
                    gevonden = gebied
                    break
            else:
                if gy0 - 1e-6 <= snede.positie <= gy1 + 1e-6 and snede.start == pytest.approx(gx0) and snede.einde == pytest.approx(gx1):
                    gevonden = gebied
                    break
        assert gevonden is not None, f"{snede} is geen rand-tot-rand snede van een bekend deelgebied"
        gx0, gy0, gx1, gy1 = gevonden
        deelgebieden.remove(gevonden)
        if snede.richting == "verticaal":
            deelgebieden.append((gx0, gy0, snede.positie, gy1))
            deelgebieden.append((snede.positie, gy0, gx1, gy1))
        else:
            deelgebieden.append((gx0, gy0, gx1, snede.positie))
            deelgebieden.append((gx0, snede.positie, gx1, gy1))


def test_genereer_zaagplannen_gebruikt_meerdere_platen_als_nodig():
    # Elke plaat heeft plek voor precies 2 stukken van 1400x2070 (met kerf);
    # 5 stukken moeten dus over 3 platen verdeeld worden.
    mat = _standaard_materiaal(lengte=2800, breedte=2070, kerf=4, min_reststukgrootte=0)
    onderdelen = [Onderdeel(id="paneel", breedte=1398, hoogte=2070, aantal=5)]
    resultaten = genereer_zaagplannen(mat, onderdelen, strategie="cnc")
    assert len(resultaten) == 3
    totaal_geplaatst = sum(len(r.plaatsingen) for r in resultaten)
    assert totaal_geplaatst == 5
    # Onderdelen die naar een volgende plaat doorschuiven zijn geen
    # "niet geplaatst" (dat zou een misleidende waarschuwing geven op een
    # tussenliggende plaat terwijl het onderdeel verderop wél terechtkomt)
    # -- alleen de laatste plaat mag echt niets meer overhouden.
    assert all(r.niet_geplaatst == [] for r in resultaten)
    # Elke plaat gebruikt hetzelfde materiaal (verse plaat, geen gedeelde voorraad).
    assert all(r.materiaal == mat for r in resultaten)


def test_genereer_zaagplannen_alles_past_op_een_plaat():
    mat = _standaard_materiaal()
    onderdelen = [Onderdeel(id="a", breedte=500, hoogte=500, aantal=2)]
    resultaten = genereer_zaagplannen(mat, onderdelen, strategie="horizontaal")
    assert len(resultaten) == 1
    assert resultaten[0].niet_geplaatst == []


def test_genereer_zaagplannen_stopt_bij_te_groot_onderdeel_i_p_v_oneindig_door_te_gaan():
    # Een onderdeel dat groter is dan de hele plaat past nooit, ook niet
    # op een verse plaat -- moet als niet_geplaatst blijven staan i.p.v.
    # tot _MAX_PLATEN platen te blijven genereren.
    mat = _standaard_materiaal(lengte=1000, breedte=1000)
    onderdelen = [
        Onderdeel(id="te_groot", breedte=5000, hoogte=5000, aantal=1),
        Onderdeel(id="past_wel", breedte=400, hoogte=400, aantal=1),
    ]
    resultaten = genereer_zaagplannen(mat, onderdelen, strategie="cnc")
    assert len(resultaten) == 1
    assert resultaten[0].niet_geplaatst == ["te_groot#1"]
    reden = resultaten[0].niet_geplaatst_redenen["te_groot#1"]
    assert "te groot" in reden
    assert "ook na roteren" in reden


def test_niet_geplaatst_redenen_is_leeg_als_alles_geplaatst_is():
    mat = _standaard_materiaal(lengte=1000, breedte=1000)
    onderdelen = [Onderdeel(id="a", breedte=400, hoogte=400, aantal=1)]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="cnc")
    assert resultaat.niet_geplaatst == []
    assert resultaat.niet_geplaatst_redenen == {}


def test_niet_geplaatst_reden_meldt_dat_onderdeel_te_groot_is_ook_na_roteren():
    mat = _standaard_materiaal(lengte=1000, breedte=1000)
    onderdelen = [Onderdeel(id="te_groot", breedte=5000, hoogte=1500, aantal=1)]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="cnc")
    assert resultaat.niet_geplaatst == ["te_groot#1"]
    reden = resultaat.niet_geplaatst_redenen["te_groot#1"]
    assert "te groot" in reden
    assert "ook na roteren" in reden


def test_niet_geplaatst_reden_meldt_dat_nerfrichting_roteren_blokkeert():
    # Een smalle, lange plaat: het onderdeel (1200x500) past niet
    # ongeroteerd (1200 > lengte 1000) maar wel geroteerd (500 <= 1000
    # en 1200 <= breedte 1600) -- de nerfrichting-eis staat die rotatie
    # echter niet toe.
    mat = _standaard_materiaal(lengte=1000, breedte=1600)
    onderdelen = [
        Onderdeel(
            id="vast_om",
            breedte=1200,
            hoogte=500,
            aantal=1,
            nerfrichting_vereist=Nerfrichting.LANGE_ZIJDE,
        )
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="cnc")
    assert resultaat.niet_geplaatst == ["vast_om#1"]
    reden = resultaat.niet_geplaatst_redenen["vast_om#1"]
    assert "alleen geroteerd" in reden
    assert "nerfrichting" in reden


def test_niet_geplaatst_reden_meldt_dat_groep_te_groot_is():
    # Zelfde scenario als test_rijen_slaat_te_hoge_groep_over_en_plaatst_kleinere_onderdelen_alsnog:
    # de gestapelde groep (588mm hoog) past niet op een plaat van 500mm hoog.
    mat = _standaard_materiaal(lengte=600, breedte=500, kerf=4, min_reststukgrootte=0)
    onderdelen = [
        Onderdeel(id="front_onder", breedte=596, hoogte=220, groep_id="lades", groep_volgorde=1),
        Onderdeel(id="front_midden", breedte=596, hoogte=180, groep_id="lades", groep_volgorde=2),
        Onderdeel(id="front_boven", breedte=596, hoogte=180, groep_id="lades", groep_volgorde=3),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="horizontaal")
    assert resultaat.niet_geplaatst == ["groep:lades"]
    reden = resultaat.niet_geplaatst_redenen["groep:lades"]
    assert "groep" in reden.lower()
    assert "te groot" in reden


def test_niet_geplaatst_reden_meldt_geen_ruimte_meer_als_onderdeel_dimensioneel_wel_past():
    # Zelfde scenario als test_rijen_stopt_pas_als_ook_de_laagste_resterende_groep_niet_meer_past:
    # "past_ook_niet" (550x100) past qua afmeting prima op een lege
    # 600x250-plaat, maar de rijen-heuristiek had al geen ruimte meer
    # over op DEZE plaat -- een ander soort reden dan "te groot".
    mat = _standaard_materiaal(lengte=600, breedte=250, kerf=4, min_reststukgrootte=0)
    onderdelen = [
        Onderdeel(id="past_al_niet", breedte=550, hoogte=220, aantal=1),
        Onderdeel(id="past_ook_niet", breedte=550, hoogte=100, aantal=1),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="horizontaal")
    assert resultaat.niet_geplaatst == ["past_ook_niet#1"]
    reden = resultaat.niet_geplaatst_redenen["past_ook_niet#1"]
    assert "past qua afmeting wel" in reden.lower()
    assert "te groot" not in reden


def test_niet_geplaatst_reden_meldt_fabriekskantenband_blokkeert_rotatie():
    # Echt teruggevonden scenario (Sven's testproject "Keuken Jansen",
    # materiaal "Meubelpaneel wit 18"): een onderdeel met een
    # kantenband_randen-eis op een rand die de plaat zelf al als
    # fabriekskantenband heeft, mag daar NOOIT roteren (zie
    # _plaats_fabriek_rand) -- past het dan niet, dan is de generieke
    # "past qua afmeting wel, probeer opnieuw"-reden misleidend (geen
    # zoekbudget of extra plaat lost dit ooit op), dus dit moet een
    # eigen, specifieke reden krijgen.
    mat = _standaard_materiaal(
        lengte=2800, breedte=600, kerf=3, min_reststukgrootte=0,
        fabriekskantenband_randen=frozenset({Rand.ONDER}),
    )
    onderdelen = [
        Onderdeel(id="bodem", breedte=540, hoogte=864, aantal=1, kantenband_randen=frozenset({Rand.ONDER}), fabriekskantenband_vereist=True),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="horizontaal")
    assert resultaat.niet_geplaatst == ["bodem#1"]
    reden = resultaat.niet_geplaatst_redenen["bodem#1"]
    assert "fabriekskantenband" in reden
    assert "nooit roteren" in reden.lower()
    assert "600mm" in reden
    assert "past qua afmeting wel" not in reden.lower()


@pytest.mark.parametrize("strategie", ["cnc", "guillotine"])
def test_krappe_restmarge_kleiner_dan_de_kerf_geeft_geen_plaatsing_buiten_de_plaat(strategie):
    # Regressietest voor een door fuzz-testen gevonden bug (concreet
    # scenario, teruggevonden met een vaste seed): zowel
    # `_pak_efficient` als `_pak_guillotine` bepaalden of een kerf nog
    # verrekend moest worden door te toetsen aan de rand van de HELE
    # plaat (x1/y1) i.p.v. aan de rand van het op dat moment behandelde
    # vrije rechthoek (fw/fh) zelf, en topten `genomen_b`/`genomen_h`
    # niet af op fw/fh. Zodra de resterende marge na een plaatsing
    # kleiner was dan de kerf (bv. nog maar 1mm over terwijl de kerf
    # 4mm is), werd het volgende vrije rechthoek daardoor te BREED
    # berekend, waardoor een net iets te breed onderdeel (o9, 186mm)
    # alsnog in dezelfde 185mm-brede kolom "paste" als een eerder
    # geplaatst 184mm-breed onderdeel (o5), en zo net buiten de
    # plaatrand kwam te staan.
    mat = _standaard_materiaal(lengte=2620, breedte=1552, kerf=4, min_reststukgrootte=100)
    onderdelen = [
        Onderdeel(id="o0", breedte=673, hoogte=1177, aantal=1, nerfrichting_vereist=Nerfrichting.LANGE_ZIJDE, kantenband_randen=frozenset({Rand.LINKS})),
        Onderdeel(id="o1", breedte=824, hoogte=76, aantal=4, groep_id="g0", groep_volgorde=1),
        Onderdeel(id="o2", breedte=1066, hoogte=255, aantal=2, kantenband_randen=frozenset({Rand.LINKS, Rand.RECHTS})),
        Onderdeel(id="o3", breedte=1060, hoogte=989, aantal=2, kantenband_randen=frozenset({Rand.BOVEN, Rand.LINKS}), groep_id="g0", groep_volgorde=3),
        Onderdeel(id="o4", breedte=51, hoogte=112, aantal=3, nerfrichting_vereist=Nerfrichting.LANGE_ZIJDE, kantenband_randen=frozenset({Rand.ONDER, Rand.RECHTS})),
        Onderdeel(id="o5", breedte=184, hoogte=292, aantal=3, nerfrichting_vereist=Nerfrichting.KORTE_ZIJDE, kantenband_randen=frozenset({Rand.RECHTS})),
        Onderdeel(id="o6", breedte=966, hoogte=507, aantal=4, nerfrichting_vereist=Nerfrichting.LANGE_ZIJDE),
        Onderdeel(id="o7", breedte=1175, hoogte=619, aantal=4, nerfrichting_vereist=Nerfrichting.KORTE_ZIJDE),
        Onderdeel(id="o8", breedte=1396, hoogte=385, aantal=1, nerfrichting_vereist=Nerfrichting.KORTE_ZIJDE),
        Onderdeel(id="o9", breedte=186, hoogte=410, aantal=3, nerfrichting_vereist=Nerfrichting.KORTE_ZIJDE),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie=strategie)

    for p in resultaat.plaatsingen:
        assert p.x >= -1e-6
        assert p.y >= -1e-6
        assert p.x + p.breedte <= mat.lengte + 1e-6
        assert p.y + p.hoogte <= mat.breedte + 1e-6
    for a, b in itertools.combinations(resultaat.plaatsingen, 2):
        assert not _rechthoeken_overlappen(a, b)


def test_zoek_tijdsbudget_zonder_budget_geeft_ongewijzigd_deterministisch_resultaat():
    # zoek_tijdsbudget=0 (de standaardwaarde) moet exact hetzelfde resultaat
    # geven als vóórdat deze parameter bestond -- geen enkel bestaand
    # aanroeppunt (of test) mag hierdoor iets anders terugkrijgen.
    mat = _standaard_materiaal()
    onderdelen = [
        Onderdeel(id="a", breedte=900, hoogte=600, aantal=2),
        Onderdeel(id="b", breedte=500, hoogte=400, aantal=3),
    ]
    zonder_param = genereer_zaagplan(mat, onderdelen, strategie="cnc")
    met_expliciete_nul = genereer_zaagplan(mat, onderdelen, strategie="cnc", zoek_tijdsbudget=0.0)
    assert zonder_param.plaatsingen == met_expliciete_nul.plaatsingen
    assert zonder_param.zaagvolgorde == met_expliciete_nul.zaagvolgorde


def test_min_zoek_tijdsbudget_dwingt_de_zoektocht_langer_door_te_gaan():
    # Op Svens verzoek ("een minimale denktijd van 10 seconden ofzo"),
    # gebruikt hier een kleine waarde om de test snel te houden: zelfs
    # een triviaal, al-optimaal scenario (dat zonder minimum meteen na
    # de eerste _MAX_POGINGEN_ZONDER_VERBETERING-stagnatie stopt) moet
    # met min_zoek_tijdsbudget minstens zo lang doorzoeken.
    mat = _standaard_materiaal(lengte=1000, breedte=1000)
    onderdelen = [Onderdeel(id="a", breedte=400, hoogte=400, aantal=1)]

    start = time.monotonic()
    genereer_zaagplan(mat, onderdelen, strategie="cnc", zoek_tijdsbudget=1.0, min_zoek_tijdsbudget=0.0)
    duur_zonder_minimum = time.monotonic() - start

    start = time.monotonic()
    genereer_zaagplan(mat, onderdelen, strategie="cnc", zoek_tijdsbudget=1.0, min_zoek_tijdsbudget=0.3)
    duur_met_minimum = time.monotonic() - start

    assert duur_zonder_minimum < 0.3
    assert duur_met_minimum >= 0.3


def test_min_zoek_tijdsbudget_wordt_begrensd_door_zoek_tijdsbudget_zelf():
    # Een min_zoek_tijdsbudget groter dan het totale zoek_tijdsbudget mag
    # niet langer laten wachten dan dat totale budget zelf toestaat.
    mat = _standaard_materiaal(lengte=1000, breedte=1000)
    onderdelen = [Onderdeel(id="a", breedte=400, hoogte=400, aantal=1)]

    start = time.monotonic()
    genereer_zaagplan(mat, onderdelen, strategie="cnc", zoek_tijdsbudget=0.2, min_zoek_tijdsbudget=10.0)
    duur = time.monotonic() - start
    assert duur < 2.0


def _scenario_efficient():
    mat = Materiaal(naam="T", lengte=1588, breedte=1376, kerf=4.0)
    onderdelen = [
        Onderdeel(id="o0", breedte=141, hoogte=365, aantal=3),
        Onderdeel(id="o1", breedte=597, hoogte=514, aantal=2),
        Onderdeel(id="o2", breedte=588, hoogte=466, aantal=3),
        Onderdeel(id="o3", breedte=323, hoogte=616, aantal=1),
        Onderdeel(id="o4", breedte=388, hoogte=243, aantal=1),
        Onderdeel(id="o5", breedte=733, hoogte=356, aantal=3),
        Onderdeel(id="o6", breedte=822, hoogte=716, aantal=1),
        Onderdeel(id="o7", breedte=417, hoogte=201, aantal=3),
        Onderdeel(id="o8", breedte=175, hoogte=800, aantal=2),
        Onderdeel(id="o9", breedte=583, hoogte=673, aantal=1),
        Onderdeel(id="o10", breedte=462, hoogte=544, aantal=2),
        Onderdeel(id="o11", breedte=725, hoogte=755, aantal=1),
        Onderdeel(id="o12", breedte=665, hoogte=588, aantal=2),
        Onderdeel(id="o13", breedte=633, hoogte=366, aantal=1),
        Onderdeel(id="o14", breedte=661, hoogte=114, aantal=1),
        Onderdeel(id="o15", breedte=836, hoogte=508, aantal=3),
        Onderdeel(id="o16", breedte=784, hoogte=740, aantal=1),
        Onderdeel(id="o17", breedte=726, hoogte=605, aantal=2),
        Onderdeel(id="o18", breedte=349, hoogte=847, aantal=2),
        Onderdeel(id="o19", breedte=820, hoogte=164, aantal=1),
        Onderdeel(id="o20", breedte=681, hoogte=327, aantal=1),
    ]
    return mat, onderdelen


def _scenario_rijen():
    mat = Materiaal(naam="T", lengte=1283, breedte=910, kerf=4.0)
    onderdelen = [
        Onderdeel(id="o0", breedte=838, hoogte=505, aantal=2),
        Onderdeel(id="o1", breedte=258, hoogte=192, aantal=1),
        Onderdeel(id="o2", breedte=120, hoogte=511, aantal=3),
        Onderdeel(id="o3", breedte=396, hoogte=883, aantal=1),
        Onderdeel(id="o4", breedte=327, hoogte=632, aantal=3),
        Onderdeel(id="o5", breedte=468, hoogte=383, aantal=1),
        Onderdeel(id="o6", breedte=208, hoogte=368, aantal=1),
        Onderdeel(id="o7", breedte=126, hoogte=756, aantal=2),
        Onderdeel(id="o8", breedte=378, hoogte=298, aantal=1),
        Onderdeel(id="o9", breedte=417, hoogte=396, aantal=3),
        Onderdeel(id="o10", breedte=849, hoogte=481, aantal=1),
    ]
    return mat, onderdelen


def _scenario_guillotine():
    mat = Materiaal(naam="T", lengte=1075, breedte=1182, kerf=4.0)
    onderdelen = [
        Onderdeel(id="o0", breedte=361, hoogte=220, aantal=2),
        Onderdeel(id="o1", breedte=879, hoogte=560, aantal=2),
        Onderdeel(id="o2", breedte=767, hoogte=488, aantal=1),
        Onderdeel(id="o3", breedte=196, hoogte=599, aantal=1),
        Onderdeel(id="o4", breedte=499, hoogte=543, aantal=3),
        Onderdeel(id="o5", breedte=880, hoogte=885, aantal=1),
        Onderdeel(id="o6", breedte=812, hoogte=556, aantal=2),
        Onderdeel(id="o7", breedte=838, hoogte=334, aantal=3),
        Onderdeel(id="o8", breedte=204, hoogte=425, aantal=1),
        Onderdeel(id="o9", breedte=122, hoogte=126, aantal=3),
    ]
    return mat, onderdelen


@pytest.mark.parametrize(
    "strategie, scenario",
    [
        ("cnc", _scenario_efficient),
        ("horizontaal", _scenario_rijen),
        ("guillotine", _scenario_guillotine),
    ],
)
def test_zoek_tijdsbudget_vindt_aantoonbaar_betere_plaatsing(strategie, scenario):
    # Op Svens verzoek ("dat je dan even moet wachten op het resultaat
    # zodat ie goed kijkt waar alle items kunnen ... rekening houdend met
    # de zaagstrategie"): met een zoekbudget probeert de motor meerdere
    # verwerkingsvolgordes (zie _ruis_sleutel/_sorteer_op_hoogte_met_ruis)
    # en houdt de beste. Elk van deze drie scenario's (teruggevonden met
    # een vaste seed via fuzz-zoeken, één per strategie omdat niet elk
    # scenario voor elke strategie evenveel ruimte voor verbetering laat
    # zien) is met de standaard, deterministische volgorde aantoonbaar
    # niet optimaal: met budget plaatst de motor meer onderdelen op
    # dezelfde ene plaat.
    mat, onderdelen = scenario()
    zonder_budget = genereer_zaagplan(mat, onderdelen, strategie=strategie, zoek_tijdsbudget=0.0)
    met_budget = genereer_zaagplan(mat, onderdelen, strategie=strategie, zoek_tijdsbudget=2.0)

    assert len(met_budget.niet_geplaatst) < len(zonder_budget.niet_geplaatst)
    for p in met_budget.plaatsingen:
        assert p.x + p.breedte <= mat.lengte + 1e-6
        assert p.y + p.hoogte <= mat.breedte + 1e-6
    for a, b in itertools.combinations(met_budget.plaatsingen, 2):
        assert not _rechthoeken_overlappen(a, b)


def test_voortgang_loopt_nooit_terug_en_eindigt_op_een():
    # Voor de voortgangsbalk in de UI: tussentijdse meldingen tijdens de
    # minimale denktijd, nooit dalend, en altijd afgesloten met 1.0.
    mat = _standaard_materiaal(lengte=1000, breedte=1000)
    onderdelen = [Onderdeel(id="a", breedte=400, hoogte=400, aantal=1)]
    meldingen: list[float] = []

    genereer_zaagplan(
        mat, onderdelen, strategie="cnc",
        zoek_tijdsbudget=1.0, min_zoek_tijdsbudget=0.35, voortgang=meldingen.append,
    )

    assert len(meldingen) >= 3
    assert meldingen == sorted(meldingen)
    assert all(0.0 <= f <= 1.0 for f in meldingen)
    assert meldingen[-1] == 1.0


def test_voortgang_zonder_zoekbudget_meldt_alleen_klaar():
    mat = _standaard_materiaal(lengte=1000, breedte=1000)
    onderdelen = [Onderdeel(id="a", breedte=400, hoogte=400, aantal=1)]
    meldingen: list[float] = []

    genereer_zaagplan(mat, onderdelen, strategie="horizontaal", voortgang=meldingen.append)

    assert meldingen == [1.0]


def test_voortgang_over_meerdere_platen_meldt_het_plaatnummer():
    mat = _standaard_materiaal(lengte=1000, breedte=1000)
    onderdelen = [Onderdeel(id="a", breedte=900, hoogte=900, aantal=3)]
    meldingen: list[tuple[int, float]] = []

    resultaten = genereer_zaagplannen(mat, onderdelen, strategie="horizontaal", voortgang=lambda n, f: meldingen.append((n, f)))

    assert len(resultaten) == 3
    assert [n for n, f in meldingen if f == 1.0] == [1, 2, 3]


def test_schat_aantal_platen():
    mat = _standaard_materiaal(lengte=1000, breedte=1000)
    assert schat_aantal_platen(mat, []) == 1
    assert schat_aantal_platen(mat, [Onderdeel(id="a", breedte=100, hoogte=100, aantal=1)]) == 1
    # 3 onderdelen van elk 0,81 m² op een plaat van 1 m² kunnen nooit op minder dan 3 platen.
    assert schat_aantal_platen(mat, [Onderdeel(id="a", breedte=900, hoogte=900, aantal=3)]) >= 3


def test_oneindig_zoekbudget_stopt_na_minimale_denktijd_op_stagnatie():
    # Zonder tijdsplafond (math.inf) moet de zoektocht nog steeds vanzelf
    # stoppen: minimaal min_zoek_tijdsbudget, daarna zodra
    # _MAX_POGINGEN_ZONDER_VERBETERING pogingen op rij niets opleveren.
    # Ook over meerdere platen: elke plaat krijgt zijn eigen minimale
    # denktijd (geen gedeeld budget dat opraakt).
    mat = _standaard_materiaal(lengte=1000, breedte=1000)
    onderdelen = [Onderdeel(id="a", breedte=900, hoogte=900, aantal=3)]
    meldingen: list[tuple[int, float]] = []

    start = time.monotonic()
    resultaten = genereer_zaagplannen(
        mat, onderdelen, strategie="cnc",
        zoek_tijdsbudget=math.inf, min_zoek_tijdsbudget=0.2,
        voortgang=lambda n, f: meldingen.append((n, f)),
    )
    duur = time.monotonic() - start

    assert len(resultaten) == 3
    assert 0.6 <= duur < 3.0
    # Elke plaat meldde tussentijdse voortgang (dus kreeg echt zoektijd).
    for plaat in (1, 2, 3):
        assert any(n == plaat and 0.0 < f < 1.0 for n, f in meldingen)


def test_fabriekskantenband_draait_een_kwartslag_om_de_juiste_zijde_tegen_de_rand_te_leggen():
    # Sven, over "Keuken Jansen": "de stijlen hebben een fabrieksrand maar
    # liggen niet tegen een fabrieksrand". Een stijl (60×802) met
    # kantenband op zijn lange linkerzijde, op een smalle plaat met
    # fabriekskantenband op onder/boven: alleen een kwartslag gedraaid
    # komt die lange zijde tegen een fabrieksrand. Voorheen viel zo'n stijl
    # terug op een gewone plaatsing, ergens midden op de plaat.
    mat = _standaard_materiaal(
        lengte=2800, breedte=600, kerf=3, min_reststukgrootte=0,
        fabriekskantenband_randen=frozenset({Rand.ONDER, Rand.BOVEN}),
    )
    onderdelen = [
        Onderdeel(id="zijkant", breedte=360, hoogte=880, aantal=3,
                  kantenband_randen=frozenset({Rand.LINKS}), fabriekskantenband_vereist=True),
        # 3 × 802 (+ kerf) past precies langs de bovenrand; een 4e zou
        # alleen in een tweede rij passen die geen rand meer raakt.
        Onderdeel(id="stijl", breedte=60, hoogte=802, aantal=3,
                  kantenband_randen=frozenset({Rand.LINKS}), fabriekskantenband_vereist=True),
    ]
    for strategie in ("cnc", "horizontaal", "guillotine"):
        resultaat = genereer_zaagplan(mat, onderdelen, strategie=strategie)
        assert resultaat.niet_geplaatst == [], strategie
        for p in resultaat.plaatsingen:
            # Kwartslag gedraaid: de lange zijde ligt langs de plaat...
            assert p.geroteerd, (strategie, p)
            # ...en raakt de onder- of bovenrand.
            assert p.y == pytest.approx(0.0) or p.y + p.hoogte == pytest.approx(mat.breedte), (strategie, p)


def test_fabriekskantenband_gebruikt_tegenoverliggende_rand_als_eigen_rand_vol_is():
    # Een dwarsbalk met kantenband "onder" die niet meer in de volle
    # onderstrook past, mag een halve slag gedraaid tegen de (ook
    # fabrieks-)bovenrand — i.p.v. door te schuiven naar een volgende
    # plaat terwijl daar nog ruim plek is (Sven: "bij 1 plaat is nog
    # precies genoeg over dat er een onderdeel naast kan maar dat doet hij
    # niet").
    mat = _standaard_materiaal(
        lengte=2800, breedte=600, kerf=3, min_reststukgrootte=0,
        fabriekskantenband_randen=frozenset({Rand.ONDER, Rand.BOVEN}),
    )
    onderdelen = [
        Onderdeel(id="bodem", breedte=564, hoogte=360, aantal=4,
                  kantenband_randen=frozenset({Rand.ONDER}), fabriekskantenband_vereist=True),
        Onderdeel(id="dwarsbalk", breedte=864, hoogte=100, aantal=2,
                  kantenband_randen=frozenset({Rand.ONDER}), fabriekskantenband_vereist=True),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="horizontaal")
    assert resultaat.niet_geplaatst == []
    for p in resultaat.plaatsingen:
        assert not p.geroteerd
        assert p.y == pytest.approx(0.0) or p.y + p.hoogte == pytest.approx(mat.breedte)



def test_lege_ruimte_in_fabrieksband_strook_wordt_reststuk():
    # Sven, over een plaat met alleen een Bodem en een Dwarsbalk in de
    # onderstrook: "dat is iets wat helaas kan gebeuren met deze
    # strategie de rest moet gewoon als rest stuk bewaard worden". Die
    # ruimte telde tot nu toe nergens mee en werd ook niet afgezaagd.
    mat = _standaard_materiaal(
        lengte=2800, breedte=600, kerf=3, min_reststukgrootte=300,
        fabriekskantenband_randen=frozenset({Rand.ONDER, Rand.BOVEN}),
    )
    onderdelen = [
        Onderdeel(id="bodem", breedte=564, hoogte=540, aantal=1,
                  kantenband_randen=frozenset({Rand.ONDER}), fabriekskantenband_vereist=True),
        Onderdeel(id="dwarsbalk", breedte=564, hoogte=100, aantal=1,
                  kantenband_randen=frozenset({Rand.BOVEN}), fabriekskantenband_vereist=True),
    ]

    resultaat = genereer_zaagplan(mat, onderdelen, strategie="horizontaal")

    rest = [(r.x, r.y, r.breedte, r.hoogte) for r in resultaat.reststukken]
    # Achter het laatste stuk: volle strookdiepte tot het einde van de plaat.
    assert (pytest.approx(1134.0), pytest.approx(0.0), pytest.approx(1666.0), pytest.approx(540.0)) in rest
    # Boven de ondiepere dwarsbalk.
    assert (pytest.approx(567.0), pytest.approx(103.0), pytest.approx(564.0), pytest.approx(437.0)) in rest
    # Elk reststuk wordt ook echt afgezaagd, zonder door een onderdeel te gaan.
    for p in resultaat.plaatsingen:
        for snede in resultaat.zaagvolgorde:
            assert not _snede_kruist_plaatsing(snede, p)
    assert any(s.richting == "verticaal" and s.positie == pytest.approx(1131.0) for s in resultaat.zaagvolgorde)


@pytest.mark.parametrize("rand", [Rand.ONDER, Rand.BOVEN, Rand.LINKS, Rand.RECHTS])
def test_reststuk_in_fabrieksband_strook_ligt_binnen_de_plaat_en_naast_de_stukken(rand):
    mat = _standaard_materiaal(lengte=2000, breedte=1500, kerf=4, min_reststukgrootte=0,
                               fabriekskantenband_randen=frozenset({rand}))
    onderdelen = [
        Onderdeel(id="diep", breedte=400, hoogte=400, aantal=1, fabriekskantenband_vereist=True),
        Onderdeel(id="ondiep", breedte=400, hoogte=150, aantal=1,
                  kantenband_randen=frozenset({Rand.ONDER}), fabriekskantenband_vereist=True),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="horizontaal")
    assert resultaat.niet_geplaatst == []
    assert resultaat.reststukken
    for r in resultaat.reststukken:
        assert r.x >= -1e-6 and r.y >= -1e-6
        assert r.x + r.breedte <= mat.lengte + 1e-6 and r.y + r.hoogte <= mat.breedte + 1e-6
        for p in resultaat.plaatsingen:
            assert not _rechthoeken_overlappen(r, p), (r, p)


def _geldig_zaagplan(resultaat, mat) -> None:
    for a, b in itertools.combinations(resultaat.plaatsingen, 2):
        assert not _rechthoeken_overlappen(a, b), (a, b)
    for p in resultaat.plaatsingen:
        assert p.x >= -1e-6 and p.y >= -1e-6
        assert p.x + p.breedte <= mat.lengte + 1e-6 and p.y + p.hoogte <= mat.breedte + 1e-6
        for snede in resultaat.zaagvolgorde:
            assert not _snede_kruist_plaatsing(snede, p), (snede, p)


def test_verticaal_maakt_kolommen_met_verticale_hoofdzaagsnedes():
    # Sven: "een extra strategie genaamd verticaal die hetzelfde doet maar
    # dan in plaats van de hoofd zaagsnedes horizontaal over de plaat
    # verticaal over de plaat".
    mat = _standaard_materiaal(lengte=2800, breedte=2070, kerf=4, min_reststukgrootte=0)
    onderdelen = [
        Onderdeel(id="zijkant", breedte=720, hoogte=560, aantal=5),
        Onderdeel(id="plank", breedte=500, hoogte=300, aantal=6),
    ]

    horizontaal = genereer_zaagplan(mat, onderdelen, strategie="horizontaal")
    verticaal = genereer_zaagplan(mat, onderdelen, strategie="verticaal")

    for resultaat in (horizontaal, verticaal):
        assert resultaat.niet_geplaatst == []
        _geldig_zaagplan(resultaat, mat)
    eerste_h = min(horizontaal.zaagvolgorde, key=lambda s: s.volgnummer)
    eerste_v = min(verticaal.zaagvolgorde, key=lambda s: s.volgnummer)
    # Horizontaal: eerste snede over de volle plaatbreedte.
    assert eerste_h.richting == "horizontaal"
    assert (eerste_h.start, eerste_h.einde) == (pytest.approx(0.0), pytest.approx(mat.lengte))
    # Verticaal: eerste snede over de volle plaathoogte.
    assert eerste_v.richting == "verticaal"
    assert (eerste_v.start, eerste_v.einde) == (pytest.approx(0.0), pytest.approx(mat.breedte))
    # Lange zijdes langs de kolom (staand), zoals bij horizontaal langs de rij (liggend).
    assert all(p.breedte >= p.hoogte for p in horizontaal.plaatsingen)
    assert all(p.hoogte >= p.breedte for p in verticaal.plaatsingen)


def test_verticaal_respecteert_nerfrichting_van_de_echte_plaat():
    # De plaatnerf loopt langs de echte x-as — ook als de strategie
    # intern met een gespiegelde plaat rekent.
    mat = _standaard_materiaal()
    onderdelen = [
        Onderdeel(id="lang", breedte=300, hoogte=800, aantal=2, nerfrichting_vereist=Nerfrichting.LANGE_ZIJDE),
        Onderdeel(id="kort", breedte=800, hoogte=300, aantal=2, nerfrichting_vereist=Nerfrichting.KORTE_ZIJDE),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="verticaal")
    assert resultaat.niet_geplaatst == []
    for p in resultaat.plaatsingen:
        if p.onderdeel_id == "lang":
            assert (p.breedte, p.hoogte) == (800, 300)  # lange zijde langs x
        else:
            assert (p.breedte, p.hoogte) == (300, 800)  # lange zijde loodrecht op x


def test_verticaal_legt_een_groep_net_zo_neer_als_horizontaal():
    # Een groep (doorlopende nerf) roteert nooit: ook bij verticaal staan
    # de leden op hun eigen afmetingen, in volgorde boven elkaar.
    mat = _standaard_materiaal()
    onderdelen = [
        Onderdeel(id=f"ladefront-{i}", breedte=400, hoogte=180, groep_id="g1", groep_volgorde=i)
        for i in (1, 2, 3)
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="verticaal")
    op_id = {p.onderdeel_id: p for p in resultaat.plaatsingen}
    p1, p2, p3 = op_id["ladefront-1"], op_id["ladefront-2"], op_id["ladefront-3"]
    assert all((p.breedte, p.hoogte, p.geroteerd) == (400, 180, False) for p in (p1, p2, p3))
    assert p1.x == p2.x == p3.x
    assert p1.y < p2.y < p3.y
    assert p2.y >= p1.y + p1.hoogte


@pytest.mark.parametrize("strategie", ["horizontaal", "verticaal"])
def test_horizontaal_en_verticaal_met_fabrieksband_en_randafzaag(strategie):
    mat = _standaard_materiaal(
        lengte=2800, breedte=2070, kerf=4, min_reststukgrootte=0, randafzaag_marge=10,
        randafzaag_randen=frozenset({Rand.LINKS, Rand.RECHTS, Rand.ONDER, Rand.BOVEN}),
        fabriekskantenband_randen=frozenset({Rand.ONDER}),
    )
    onderdelen = [
        Onderdeel(id="bodem", breedte=564, hoogte=500, aantal=3,
                  kantenband_randen=frozenset({Rand.ONDER}), fabriekskantenband_vereist=True),
        Onderdeel(id="deur", breedte=450, hoogte=700, aantal=4),
        Onderdeel(id="plank", breedte=800, hoogte=300, aantal=3),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie=strategie)
    assert resultaat.niet_geplaatst == []
    _geldig_zaagplan(resultaat, mat)
    for p in resultaat.plaatsingen:
        if p.onderdeel_id == "bodem":
            assert p.y == pytest.approx(0.0)
        else:
            # Gewone onderdelen blijven binnen de randafzaag-marge.
            assert p.x >= 10 - 1e-6 and p.x + p.breedte <= mat.lengte - 10 + 1e-6
            assert p.y + p.hoogte <= mat.breedte - 10 + 1e-6


@pytest.mark.parametrize("strategie", ["horizontaal", "verticaal", "cnc", "guillotine"])
def test_groepssneden_lopen_nooit_door_een_ander_onderdeel(strategie):
    # Sven, over de MDF-plaat van "Keuken Jansen" met strategie Verticaal:
    # "hij laat een rode zaaglijn zien door een onderdeel". De snede
    # tussen twee groepsleden (Front 1/Front 2, doorlopende nerf) werd bij
    # Verticaal verkeerd teruggespiegeld en liep dwars door een Deur.
    mat = _standaard_materiaal(
        lengte=2800, breedte=2150, kerf=3, min_reststukgrootte=0, randafzaag_marge=5,
        randafzaag_randen=frozenset({Rand.LINKS, Rand.RECHTS, Rand.ONDER, Rand.BOVEN}),
    )
    onderdelen = [
        Onderdeel(id="deur", breedte=594, hoogte=895, aantal=2),
        Onderdeel(id="front-1", breedte=594, hoogte=416, groep_id="fronten", groep_volgorde=1),
        Onderdeel(id="front-2", breedte=594, hoogte=416, groep_id="fronten", groep_volgorde=2),
        Onderdeel(id="passtuk", breedte=144, hoogte=835, aantal=1),
        Onderdeel(id="blende-1", breedte=444, hoogte=835, aantal=2),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie=strategie)
    assert resultaat.niet_geplaatst == []
    _geldig_zaagplan(resultaat, mat)
    # De groep ligt zoals altijd: boven elkaar, op eigen afmetingen.
    op_id = {p.onderdeel_id: p for p in resultaat.plaatsingen}
    f1, f2 = op_id["front-1"], op_id["front-2"]
    assert f1.x == f2.x and f1.y < f2.y
    # En de snede tussen de twee leden bestaat en ligt precies tussen hen
    # in. (Efficiënt/Guillotine noteren tussen groepsleden nog helemaal
    # geen snede — bestaande beperking, los van deze bug.)
    if strategie in ("horizontaal", "verticaal"):
        assert any(
            s.richting == "horizontaal" and s.positie == pytest.approx(f1.y + f1.hoogte)
            and s.start <= f1.x + 1e-6 and s.einde >= f1.x + f1.breedte - 1e-6
            for s in resultaat.zaagvolgorde
        )


def _randen_zonder_snede(resultaat) -> list[str]:
    """Elke rand van elk onderdeel moet óf op de plaatrand (binnen de
    randafzaag-marge) liggen, óf over zijn volle lengte door een snede in
    de zaagvolgorde gemaakt worden (binnen één kerf) — anders wordt dat
    onderdeel volgens de zaagvolgorde nooit op maat gezaagd."""
    m = resultaat.materiaal
    tol = m.kerf + 0.5

    def gedekt(richting, pos, a, b):
        stukken = sorted(
            (max(a, s.start), min(b, s.einde))
            for s in resultaat.zaagvolgorde
            if s.richting == richting and abs(s.positie - pos) <= tol and s.einde > a and s.start < b
        )
        c = a
        for x, y in stukken:
            if x > c + 0.5:
                return False
            c = max(c, y)
        return c >= b - 0.5

    def plaatrand(richting, pos):
        grens = m.lengte if richting == "verticaal" else m.breedte
        return pos <= m.randafzaag_marge + 0.5 or pos >= grens - m.randafzaag_marge - 0.5

    fout = []
    for q in resultaat.plaatsingen:
        for richting, pos, a, b, naam in (
            ("verticaal", q.x, q.y, q.y + q.hoogte, "links"),
            ("verticaal", q.x + q.breedte, q.y, q.y + q.hoogte, "rechts"),
            ("horizontaal", q.y, q.x, q.x + q.breedte, "onder"),
            ("horizontaal", q.y + q.hoogte, q.x, q.x + q.breedte, "boven"),
        ):
            if not plaatrand(richting, pos) and not gedekt(richting, pos, a, b):
                fout.append(f"{q.onderdeel_id}#{q.instantie} {naam}")
    return fout


def _onverantwoord_oppervlak(resultaat) -> float:
    """Plaatoppervlak dat nergens meetelt (geen onderdeel, reststuk of
    afval), na aftrek van wat zaagsnedes (kerf × lengte) en randafzaag
    (marge × zijde) mogen opeten. Hoort ≤ 0 te zijn."""
    m = resultaat.materiaal
    marge = sum(
        m.randafzaag_marge * (m.breedte if rand in (Rand.LINKS, Rand.RECHTS) else m.lengte)
        for rand in m.randafzaag_randen
        if rand not in m.fabriekskantenband_randen
    )
    return (
        m.lengte * m.breedte
        - sum(q.breedte * q.hoogte for q in resultaat.plaatsingen)
        - sum(r.breedte * r.hoogte for r in resultaat.reststukken)
        - resultaat.afval_oppervlak
        - sum((s.einde - s.start) * m.kerf for s in resultaat.zaagvolgorde)
        - marge
    )


_ALLE_STRATEGIEEN = ["cnc", "horizontaal", "verticaal", "guillotine"]
# "cnc" is een CNC-strategie zonder zaagvolgorde (zie engine.py) —
# de zaag-specifieke controles gelden alleen voor deze:
_ZAAGSTRATEGIEEN = [s for s in _ALLE_STRATEGIEEN if s != "cnc"]


def _keuken_jansen_scenario():
    # Nagebouwd uit Svens "Keuken Jansen" (MDF-plaat + lade-onderdelen op
    # melamine), waar Sven vroeg "hoe bereken je wat hergebruikt kan
    # worden" en het narekenen twee gaten liet zien: ruimte boven een stuk
    # dat lager is dan zijn rij telde nergens mee, en diverse randen van
    # onderdelen kregen in de zaagvolgorde nooit een snede.
    mdf = _standaard_materiaal(
        lengte=2800, breedte=2150, kerf=3, min_reststukgrootte=150, randafzaag_marge=5,
        randafzaag_randen=frozenset({Rand.LINKS, Rand.RECHTS, Rand.ONDER, Rand.BOVEN}),
    )
    mdf_onderdelen = [
        Onderdeel(id="deur", breedte=594, hoogte=895, aantal=2),
        Onderdeel(id="front-1", breedte=594, hoogte=416, groep_id="fronten", groep_volgorde=1),
        Onderdeel(id="front-2", breedte=594, hoogte=416, groep_id="fronten", groep_volgorde=2),
        Onderdeel(id="passtuk", breedte=144, hoogte=835, aantal=1),
        Onderdeel(id="blende", breedte=444, hoogte=835, aantal=2),
    ]
    melamine = mdf
    melamine_onderdelen = [
        Onderdeel(id="lade-bodem", breedte=506, hoogte=500, aantal=3),
        Onderdeel(id="rug-korf", breedte=506, hoogte=170, aantal=2),
        Onderdeel(id="rug-bestek", breedte=506, hoogte=70, aantal=1),
    ]
    return [(mdf, mdf_onderdelen), (melamine, melamine_onderdelen)]


@pytest.mark.parametrize("strategie", _ZAAGSTRATEGIEEN)
def test_elke_rand_van_elk_onderdeel_wordt_gezaagd(strategie):
    for mat, onderdelen in _keuken_jansen_scenario():
        resultaat = genereer_zaagplan(mat, onderdelen, strategie=strategie)
        assert resultaat.niet_geplaatst == []
        assert _randen_zonder_snede(resultaat) == []
        _geldig_zaagplan(resultaat, mat)


@pytest.mark.parametrize("strategie", _ALLE_STRATEGIEEN)
def test_alle_restruimte_telt_mee_als_reststuk_of_afval(strategie):
    for mat, onderdelen in _keuken_jansen_scenario():
        resultaat = genereer_zaagplan(mat, onderdelen, strategie=strategie)
        assert _onverantwoord_oppervlak(resultaat) <= 1e-3 * mat.lengte * mat.breedte


def test_ruimte_boven_een_lager_stuk_in_een_rij_wordt_reststuk():
    # Horizontaal: 3 lade-bodems (500 hoog) bepalen de rijhoogte; de
    # lade-ruggen (170 + 170 + 70, gestapeld) blijven daar ~81 mm onder.
    # Met een lagere drempel moet dat reepje als reststuk verschijnen, met
    # een snede erboven.
    mat = _standaard_materiaal(lengte=2800, breedte=2150, kerf=3, min_reststukgrootte=50)
    onderdelen = [
        Onderdeel(id="lade-bodem", breedte=506, hoogte=500, aantal=3),
        Onderdeel(id="rug-korf", breedte=506, hoogte=170, aantal=2),
        Onderdeel(id="rug-bestek", breedte=506, hoogte=70, aantal=1),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="horizontaal")
    ruggen = [p for p in resultaat.plaatsingen if p.onderdeel_id.startswith("rug")]
    kolom_x = ruggen[0].x
    kolom_top = max(p.y + p.hoogte for p in ruggen)
    assert any(
        r.x == pytest.approx(kolom_x) and r.y == pytest.approx(kolom_top + mat.kerf) and r.breedte == pytest.approx(506)
        for r in resultaat.reststukken
    ), resultaat.reststukken
    assert any(
        s.richting == "horizontaal" and s.positie == pytest.approx(kolom_top) for s in resultaat.zaagvolgorde
    )


@pytest.mark.parametrize("strategie", ["guillotine", "horizontaal"])
def test_reepje_smaller_dan_de_kerf_krijgt_toch_een_snede(strategie):
    # 2 liggende stukken van 997 op een werkgebied van 2000 met kerf 4:
    # 997 + 4 + 997 laat rechts 2 mm over — te smal voor een vrij
    # rechthoek, maar het tweede stuk moet daar nog steeds op maat
    # gezaagd worden.
    mat = _standaard_materiaal(lengte=2000, breedte=1000, kerf=4, min_reststukgrootte=0)
    onderdelen = [Onderdeel(id="a", breedte=997, hoogte=500, aantal=2)]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie=strategie)
    assert resultaat.niet_geplaatst == []
    assert _randen_zonder_snede(resultaat) == []


def test_reepje_in_fabrieksband_strook_krijgt_toch_een_snede():
    # Een stuk dat 1 mm minder diep is dan zijn strook, en een laatste stuk
    # dat 1 mm voor het einde van de rand ophoudt (beide uit de fuzz).
    mat = _standaard_materiaal(lengte=2000, breedte=1500, kerf=4, min_reststukgrootte=0,
                               fabriekskantenband_randen=frozenset({Rand.ONDER}))
    onderdelen = [
        Onderdeel(id="diep", breedte=995, hoogte=600, aantal=1, fabriekskantenband_vereist=True),
        Onderdeel(id="ondiep", breedte=1000, hoogte=599, aantal=1, fabriekskantenband_vereist=True),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="horizontaal")
    assert resultaat.niet_geplaatst == []
    assert _randen_zonder_snede(resultaat) == []


def _paneelzaag_fouten(resultaat) -> list[str]:
    """Voert de zaagvolgorde uit zoals een paneelzaag: begint met de plaat
    na de randafzaag, en elke snede moet van rand tot rand door precies één
    op dat moment bestaand stuk plaat lopen (en splitst dat in tweeën). Aan
    het eind mag elk stuk plaat hoogstens één onderdeel bevatten."""
    m = resultaat.materiaal
    e = 1e-6

    def af(rand):
        return m.randafzaag_marge if rand in m.randafzaag_randen and rand not in m.fabriekskantenband_randen else 0.0

    gebieden = [(af(Rand.LINKS), af(Rand.ONDER), m.lengte - af(Rand.RECHTS), m.breedte - af(Rand.BOVEN))]
    fout = []
    for s in sorted(resultaat.zaagvolgorde, key=lambda z: z.volgnummer):
        hit = None
        for g in gebieden:
            gx0, gy0, gx1, gy1 = g
            if s.richting == "verticaal":
                ok = gx0 + e < s.positie < gx1 - e and abs(s.start - gy0) < 1e-3 and abs(s.einde - gy1) < 1e-3
            else:
                ok = gy0 + e < s.positie < gy1 - e and abs(s.start - gx0) < 1e-3 and abs(s.einde - gx1) < 1e-3
            if ok:
                hit = g
                break
        if hit is None:
            fout.append(f"snede {s.volgnummer} is geen rand-tot-rand snede van een stuk plaat: {s}")
            continue
        gx0, gy0, gx1, gy1 = hit
        gebieden.remove(hit)
        if s.richting == "verticaal":
            gebieden += [(gx0, gy0, s.positie, gy1), (s.positie, gy0, gx1, gy1)]
        else:
            gebieden += [(gx0, gy0, gx1, s.positie), (gx0, s.positie, gx1, gy1)]
    k = m.kerf + e
    for g in gebieden:
        gx0, gy0, gx1, gy1 = g
        binnen = [
            p for p in resultaat.plaatsingen
            if p.x >= gx0 - k and p.x + p.breedte <= gx1 + k and p.y >= gy0 - k and p.y + p.hoogte <= gy1 + k
        ]
        if len(binnen) > 1:
            fout.append(f"stuk plaat {g} bevat {len(binnen)} onderdelen")
    return fout


def _willekeurig_scenario(seed: int):
    rng = random.Random(seed)
    randen = [Rand.ONDER, Rand.BOVEN, Rand.LINKS, Rand.RECHTS]
    mat = Materiaal(
        naam="m", lengte=rng.choice([2800, 2440, 1200]), breedte=rng.choice([600, 1220, 2070, 800]), dikte=18,
        kerf=rng.choice([3, 4]), min_reststukgrootte=rng.choice([0, 150, 300]), randafzaag_marge=rng.choice([0, 5]),
        randafzaag_randen=frozenset(rng.sample(randen, rng.randint(0, 4))),
        fabriekskantenband_randen=frozenset(rng.sample(randen, rng.choice([0, 0, 1, 2]))),
    )
    onderdelen = []
    for i in range(rng.randint(1, 9)):
        fab = rng.random() < 0.25
        onderdelen.append(Onderdeel(
            id=f"o{i}", breedte=rng.randint(40, 1100), hoogte=rng.randint(40, 1100), aantal=rng.randint(1, 5),
            nerfrichting_vereist=rng.choice([Nerfrichting.GEEN] * 4 + [Nerfrichting.LANGE_ZIJDE, Nerfrichting.KORTE_ZIJDE]),
            kantenband_randen=frozenset(rng.sample(randen, rng.randint(0, 2))) if fab else frozenset(),
            fabriekskantenband_vereist=fab,
        ))
    if rng.random() < 0.4:
        breedte = rng.randint(100, 900)
        for j in range(rng.randint(2, 4)):
            onderdelen.append(Onderdeel(id=f"g{j}", breedte=breedte, hoogte=rng.randint(60, 500), groep_id="g", groep_volgorde=j))
    return mat, onderdelen


@pytest.mark.parametrize("strategie", _ZAAGSTRATEGIEEN)
def test_paneelzaag_simulatie_op_willekeurige_scenarios(strategie):
    # Sven: "kan je deze strategie simuleren en zelf controleren of alles
    # klopt" (over Guillotine). Een vaste set willekeurige scenario's
    # (fabrieksband, randafzaag, nerf, groepen) per strategie: de
    # zaagvolgorde moet uitvoerbaar zijn op een paneelzaag, elk onderdeel in
    # een eigen stuk plaat eindigen, elke rand gezaagd zijn en alle
    # oppervlakte verantwoord.
    for seed in range(120):
        mat, onderdelen = _willekeurig_scenario(seed)
        resultaat = genereer_zaagplan(mat, onderdelen, strategie=strategie)
        _geldig_zaagplan(resultaat, mat)
        assert _paneelzaag_fouten(resultaat) == [], (seed, _paneelzaag_fouten(resultaat)[:2])
        assert _randen_zonder_snede(resultaat) == [], (seed, _randen_zonder_snede(resultaat)[:2])
        assert _onverantwoord_oppervlak(resultaat) <= 1e-3 * mat.lengte * mat.breedte, seed


# ----------------------------------------------------------------------
# CNC-nesting ("cnc", niet kiesbaar in de app; bewaard voor een latere CNC-upgrade)
# ----------------------------------------------------------------------


def _tussenruimte(a, b) -> float:
    """Afstand tussen twee rechthoeken langs de as waarop ze uit elkaar
    liggen (≥ freesdiameter betekent: de frees past ertussen)."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return max(bx - (ax + aw), ax - (bx + bw), by - (ay + ah), ay - (by + bh))


def _cnc_fouten(resultaat, mat) -> list[str]:
    fouten = []
    if resultaat.zaagvolgorde:
        fouten.append("CNC hoort geen zaagvolgorde te hebben")
    stukken = [(p.x, p.y, p.breedte, p.hoogte) for p in resultaat.plaatsingen]
    rest = [(r.x, r.y, r.breedte, r.hoogte) for r in resultaat.reststukken]
    for a, b in itertools.combinations(stukken, 2):
        if _tussenruimte(a, b) < mat.kerf - 1e-6:
            fouten.append(f"onderdelen te dicht op elkaar: {a} {b}")
    for r in rest:
        if r[2] < mat.min_reststukgrootte - 1e-6 or r[3] < mat.min_reststukgrootte - 1e-6:
            fouten.append(f"reststuk te klein: {r}")
        for a in stukken:
            if _tussenruimte(a, r) < mat.kerf - 1e-6:
                fouten.append(f"reststuk te dicht op onderdeel: {r} {a}")
    for a, b in itertools.combinations(rest, 2):
        if _tussenruimte(a, b) < mat.kerf - 1e-6:
            fouten.append(f"reststukken te dicht op elkaar: {a} {b}")
    if abs(_onverantwoord_oppervlak(resultaat)) > 1e-3 * mat.lengte * mat.breedte:
        fouten.append(f"oppervlak klopt niet: {_onverantwoord_oppervlak(resultaat)}")
    return fouten


def test_cnc_nesting_op_willekeurige_scenarios():
    # Zelfde willekeurige scenario's (fabrieksband, randafzaag, nerf,
    # groepen) als de paneelzaag-simulatie: geen overlap, binnen de plaat,
    # overal minstens een freesdiameter tussenruimte (ook rond reststukken),
    # geen zaagvolgorde en alle oppervlak precies verantwoord.
    for seed in range(120):
        mat, onderdelen = _willekeurig_scenario(seed)
        resultaat = genereer_zaagplan(mat, onderdelen, strategie="cnc")
        _geldig_zaagplan(resultaat, mat)
        assert _cnc_fouten(resultaat, mat) == [], (seed, _cnc_fouten(resultaat, mat)[:2])


def test_cnc_respecteert_nerfrichting():
    mat = _standaard_materiaal(lengte=2800, breedte=2070, kerf=8)
    onderdelen = [
        Onderdeel(id="lang", breedte=300, hoogte=900, aantal=4, nerfrichting_vereist=Nerfrichting.LANGE_ZIJDE),
        Onderdeel(id="kort", breedte=900, hoogte=300, aantal=4, nerfrichting_vereist=Nerfrichting.KORTE_ZIJDE),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="cnc")
    assert resultaat.niet_geplaatst == []
    for p in resultaat.plaatsingen:
        if p.onderdeel_id == "lang":
            assert p.breedte >= p.hoogte
        else:
            assert p.hoogte >= p.breedte


def test_cnc_laat_lege_ruimte_als_een_groot_reststuk():
    # Svens keuze: na zo min mogelijk platen zo min mogelijk afval, dus een
    # zo groot mogelijk reststuk i.p.v. losse snippers.
    mat = _standaard_materiaal(lengte=2800, breedte=2070, kerf=8, min_reststukgrootte=200)
    onderdelen = [Onderdeel(id="a", breedte=600, hoogte=400, aantal=6), Onderdeel(id="b", breedte=300, hoogte=250, aantal=5)]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="cnc")
    assert resultaat.niet_geplaatst == []
    vrij = mat.lengte * mat.breedte - sum(p.breedte * p.hoogte for p in resultaat.plaatsingen)
    grootste = max(r.oppervlak for r in resultaat.reststukken)
    assert grootste >= 0.75 * vrij


def test_cnc_heeft_in_totaal_niet_meer_platen_nodig_dan_de_zaagstrategieen():
    # Vrije plaatsing heeft geen paneelzaag-beperking, dus hoort over een
    # reeks projecten samen nooit méér platen nodig te hebben dan de kiesbare
    # zaagstrategieën.
    platen = {s: 0 for s in _ALLE_STRATEGIEEN}
    for seed in range(40):
        mat, onderdelen = _willekeurig_scenario(seed)
        for strategie in _ALLE_STRATEGIEEN:
            platen[strategie] += len(genereer_zaagplannen(mat, onderdelen, strategie=strategie))
    assert platen["cnc"] <= min(platen[s] for s in _ZAAGSTRATEGIEEN), platen
