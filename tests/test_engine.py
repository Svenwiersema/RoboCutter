"""Tests voor de zaagplan-optimalisatie-motor.

Dekt de kernregels uit hoofdstuk 5: geen overlap, kerf-verrekening,
randafzaag-marge, nerfrichting-rotatie, groepering, en de
min-reststukgrootte-classificatie.
"""

from __future__ import annotations

import itertools

import pytest

from robocutter.optimalisatie.engine import genereer_zaagplan, genereer_zaagplannen
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


@pytest.mark.parametrize("strategie", ["efficient", "rijen", "stroken", "guillotine"])
def test_geplaatste_stukken_overlappen_nooit_ongeacht_strategie(strategie):
    # Zelfde mix als hierboven, maar zonder te eisen dat alles geplaatst
    # wordt: "stroken" en "guillotine" zijn bewust minder efficiënt dan
    # "efficient"/"rijen" (vaste strookhoogte resp. uitsluitend
    # rand-tot-rand sneden), dus kunnen op een krappe plaat stukken
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


@pytest.mark.parametrize("strategie", ["efficient", "rijen", "stroken", "guillotine"])
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


def test_stroken_gebruikt_overal_dezelfde_vaste_strookhoogte():
    mat = _standaard_materiaal(lengte=2800, breedte=2070, kerf=4)
    # Allebei te breed om samen in één strook te passen -> elk onderdeel
    # komt in zijn eigen strook terecht. De afstand tussen de stroken moet
    # gelijk zijn aan de hoogte van het HOOGSTE onderdeel + kerf, ook al
    # staat het lagere onderdeel in zijn eigen, verder ongebruikte strook.
    onderdelen = [
        Onderdeel(id="hoog", breedte=2600, hoogte=900, aantal=1),
        Onderdeel(id="laag", breedte=2600, hoogte=500, aantal=1),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="stroken")
    assert resultaat.niet_geplaatst == []
    p_hoog = next(p for p in resultaat.plaatsingen if p.onderdeel_id == "hoog")
    p_laag = next(p for p in resultaat.plaatsingen if p.onderdeel_id == "laag")
    assert abs(p_laag.y - p_hoog.y) == pytest.approx(900 + mat.kerf)


@pytest.mark.parametrize("strategie", ["rijen", "stroken"])
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
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="rijen")
    assert resultaat.niet_geplaatst == []
    vulling = next(p for p in resultaat.plaatsingen if p.onderdeel_id == "vulling")
    assert vulling.geroteerd is True
    assert vulling.breedte == pytest.approx(500)
    assert vulling.hoogte == pytest.approx(150)
    for p1, p2 in itertools.combinations(resultaat.plaatsingen, 2):
        assert not _rechthoeken_overlappen(p1, p2), f"{p1} overlapt met {p2}"


@pytest.mark.parametrize("strategie", ["rijen", "stroken"])
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
        # landschap-oriëntatie die "rijen"/"stroken" sinds de rotatiefix
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
        assert s.start == pytest.approx(504.0) and s.einde == pytest.approx(1100.0)


@pytest.mark.parametrize("strategie", ["rijen", "stroken", "efficient", "guillotine"])
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
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="rijen")
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
    resultaat_een_rand = genereer_zaagplan(mat_een_rand, onderdelen, strategie="rijen")
    assert len(resultaat_een_rand.niet_geplaatst) == 3


def test_fabriekskantenband_respecteert_kantenband_randen_en_roteert_niet():
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
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="rijen")
    assert resultaat.niet_geplaatst == []
    dwarsbalk = next(p for p in resultaat.plaatsingen if p.onderdeel_id == "dwarsbalk_boven")
    plank = next(p for p in resultaat.plaatsingen if p.onderdeel_id == "plank_onder")
    # Geen van beide geroteerd: hun eigen breedte/hoogte, zoals opgegeven.
    assert not dwarsbalk.geroteerd and (dwarsbalk.breedte, dwarsbalk.hoogte) == (564, 100)
    assert not plank.geroteerd and (plank.breedte, plank.hoogte) == (400, 120)
    # De dwarsbalk raakt zijn BOVEN-rand (de lange 564-zijde ligt daar plat tegenaan).
    assert dwarsbalk.y + dwarsbalk.hoogte == pytest.approx(mat.breedte)
    # De plank raakt zijn ONDER-rand.
    assert plank.y == pytest.approx(0.0)


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
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="rijen")
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
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="rijen")
    eerste = min(resultaat.zaagvolgorde, key=lambda s: s.volgnummer)
    assert eerste.richting == "verticaal"
    assert eerste.positie == pytest.approx(500 + mat.kerf)
    assert eerste.start == pytest.approx(0.0)
    assert eerste.einde == pytest.approx(mat.breedte)


def test_rijen_enkele_rij_krijgt_scheidingssnede_naar_restruimte_erboven():
    # Hiaat 2 (zie OVERDRACHT.md): bij precies één gebruikte rij ontbrak
    # de horizontale snede die die rij scheidt van het reststuk erboven.
    mat = _standaard_materiaal(lengte=2800, breedte=2070, kerf=4)
    onderdelen = [Onderdeel(id="a", breedte=800, hoogte=500, aantal=2)]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="rijen")
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
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="rijen")
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
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="rijen")
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
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="rijen")
    # De eerste (hoogste) past nog wel (220 < 250); de tweede rij zou
    # cursor_y=224 + 100 = 324 > 250 zijn, past dus niet meer.
    assert len(resultaat.plaatsingen) == 1
    assert resultaat.plaatsingen[0].onderdeel_id == "past_al_niet"
    assert resultaat.niet_geplaatst == ["past_ook_niet#1"]


def test_stroken_stopt_wel_meteen_helemaal_want_strookhoogte_is_plaatbreed_vast():
    # Bewuste asymmetrie met de twee tests hierboven: "Stroken" gebruikt
    # NIET de _pak_rijen-fix (zie de docstring van _pak_stroken) omdat de
    # strookhoogte voor de hele plaat vastligt op het hoogste onderdeel --
    # als één strook niet meer past, past dus ECHT niets meer, ook geen
    # kleiner onderdeel (elke strook is immers altijd even hoog).
    mat = _standaard_materiaal(lengte=600, breedte=500, kerf=4, min_reststukgrootte=0)
    onderdelen = [
        Onderdeel(id="front_onder", breedte=596, hoogte=220, groep_id="lades", groep_volgorde=1),
        Onderdeel(id="front_midden", breedte=596, hoogte=180, groep_id="lades", groep_volgorde=2),
        Onderdeel(id="front_boven", breedte=596, hoogte=180, groep_id="lades", groep_volgorde=3),
        Onderdeel(id="lade_bodem", breedte=550, hoogte=400, aantal=1),
    ]
    resultaat = genereer_zaagplan(mat, onderdelen, strategie="stroken")
    assert resultaat.plaatsingen == []
    assert set(resultaat.niet_geplaatst) == {"groep:lades", "lade_bodem#1"}


@pytest.mark.parametrize("strategie", ["efficient", "guillotine", "rijen", "stroken"])
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


@pytest.mark.parametrize("strategie", ["efficient", "guillotine", "rijen", "stroken"])
def test_elke_snede_is_rand_tot_rand_van_zijn_eigen_deelgebied(strategie):
    # Sterkere check dan alleen de eerste snede: reconstrueer voor elke
    # snede het deelgebied waarin hij viel (op basis van alle eerdere
    # sneden) en controleer dat start/einde exact de randen van dat
    # deelgebied raken -- dat garandeert dat een snede nooit dwars door
    # een al geplaatst onderdeel heen loopt. Geldt voor "efficient"/
    # "guillotine" via _splits_vrije_rechthoek, en sinds de
    # rij-hoogte-bugfix ook voor "rijen"/"stroken" (zie
    # _bouw_zaagvolgorde_uit_rijen: een tussen-kolom-snede stopte voorheen
    # 1 kerf te vroeg t.o.v. de echte fysieke rijgrens zodra er nóg een
    # rij op volgde — dit was tot nu toe ongedekt, want "efficient" kon
    # tot deze iteratie nooit intern op de uitkomst van "rijen"/"stroken"
    # uitkomen).
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
    resultaten = genereer_zaagplannen(mat, onderdelen, strategie="efficient")
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
    resultaten = genereer_zaagplannen(mat, onderdelen, strategie="rijen")
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
    resultaten = genereer_zaagplannen(mat, onderdelen, strategie="efficient")
    assert len(resultaten) == 1
    assert resultaten[0].niet_geplaatst == ["te_groot#1"]


@pytest.mark.parametrize("strategie", ["efficient", "guillotine"])
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
