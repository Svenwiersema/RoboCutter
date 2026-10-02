"""Zaagplan-optimalisatie-motor.

Implementeert de regels uit design/chapters/05-zaagplan-optimalisatie.md
als een losstaande, testbare Python-module (nog zonder UI — dat is
bewust de eerste stap, zie checklist.md).

Drie door de gebruiker kiesbare strategieën (namen/omschrijvingen
vastgesteld in ``robocutter.instellingen.models.GELDIGE_ZAAGSTRATEGIEEN``,
zie ook ``instellingen_page.py``'s ``_STRATEGIE_OMSCHRIJVING``):
  - "cnc": NIET kiesbaar in de app — bewaard voor een latere, bredere
    CNC-upgrade (Sven: "eigenlijk hoeft deze niet in zaagplannen want daar
    ben je geen zaagplan voor nodig ... dit word later gebruikt denk ik
    voor een gehele cnc upgrade"). Heette eerder "efficient"/"Efficiënt".
    Op Svens verzoek een strategie voor een CNC-freesmachine — "kijken
    wat het minste afval laat liggen maakt niet uit hoe het gezaagd
    word". Onderdelen worden vrij in elkaar geschoven (MaxRects, zie
    ``_pak_nesting``), zonder paneelzaag-beperking en zonder
    zaagvolgorde; de tussenruimte is ``materiaal.kerf``, hier bedoeld als
    freesdiameter (nog geen instelling: die komt met de CNC-upgrade). Doel: eerst
    zo min mogelijk platen, dan zo min mogelijk afval / een zo groot
    mogelijk reststuk (``_nesting_score``).
  - "horizontaal" (heette tot en met de eerste versies "rijen"): lange
    zijdes eerst (rij-gebaseerd, volledige-breedte sneden eerst, daarna
    kortere sneden per rij) — de rijhoogte past zich per rij aan aan het
    grootste stuk erin. De hoofdzaagsnedes lopen dus horizontaal over
    de plaat.
  - "verticaal": precies hetzelfde, maar een kwartslag gedraaid —
    kolommen over de volle plaathoogte, dus de hoofdzaagsnedes lopen
    verticaal (zie ``_pak_kolommen``).
  - "guillotine": uitsluitend doorlopende zaagsnedes van rand tot rand
    van het op dat moment resterende deelgebied. Werkt een wachtrij van
    deelgebieden strikt één voor één helemaal af (plaatsen + volledig
    opsplitsen) voordat het volgende deelgebied aan de beurt is, en bouwt
    de zaagvolgorde rechtstreeks op uit die opsplitsingen
    (``_splits_vrije_rechthoek``) — zo is elke genoteerde snede
    gegarandeerd rand-tot-rand van het deelgebied waarin hij gemaakt
    wordt, en loopt hij nooit dwars door een al geplaatst onderdeel.

Vroeger bestond er ook een strategie "stroken" (zoals "horizontaal",
maar met overal dezelfde vaste strookhoogte); die is op Svens verzoek
helemaal uit het programma gehaald.

Belangrijke, expliciete aannames (graag door Sven te bevestigen aan de
hand van de gegenereerde voorbeelden — zie ``demo.py``):

  1. De nerf van een plaat loopt altijd langs de lengte-as (x-as).
     Een onderdeel met nerfrichting "lange_zijde" wordt dus zo
     georiënteerd dat zijn langste zijde evenwijdig aan de x-as ligt;
     "korte_zijde" juist loodrecht daarop.
  2. Een kerf (zaagsnede-breedte) wordt verrekend door elk geplaatst
     onderdeel te behandelen alsof het kerf-breedte extra ruimte
     inneemt aan de kant(en) waar nog een snede nodig is om het
     volgende stuk te vrij te maken (niet aan de plaatrand zelf).
  3. Een groep (vaste volgorde/oriëntatie voor doorlopende nerf) wordt
     behandeld als één samengesteld blok dat niet roteert; de leden
     worden verticaal gestapeld in de opgegeven volgorde. De
     optimizer kiest nog wel zelf waar dat blok op de plaat komt.
  4. Een reststuk telt alleen als "bruikbaar" (i.p.v. afval) als
     zowel de breedte als de hoogte minstens ``min_reststukgrootte``
     zijn.
  5. Als een onderdeel een fabriekskantenband nodig heeft, wordt het
     geplaatst tegen één van de randen in
     ``materiaal.fabriekskantenband_randen``. Heeft de plaat er
     meerdere (bv. onder én boven), dan worden ze in volgorde (links,
     onder, boven, rechts) allemaal geprobeerd: wat niet meer in de
     eerste rand-strook past, schuift door naar de volgende beschikbare
     rand-strook op dezelfde plaat, vóór het pas echt niet-geplaatst
     raakt (zie ``_plaats_fabriek_rand``/de fabriekskantenband-lus in
     ``genereer_zaagplan``, op Svens verzoek — voorheen werd altijd
     maar één rand gebruikt).
  6. De zaagvolgorde-nummering (welke snede het volgnummer 1, 2, ...
     krijgt) is voor de zaagstrategieën (rijen, guillotine; "cnc" heeft
     geen zaagvolgorde) een eerste, redelijke benadering op
     basis van de plaatsings-/opsplitsingsvolgorde — dit wordt verder
     verfijnd zodra er meer gegenereerde voorbeelden zijn beoordeeld
     (zie hoofdstuk 5, "Openstaande vragen"). De sneden zélf
     (positie/start/einde) zijn dat sinds de zaagvolgorde-fix (zie
     OVERDRACHT.md) niet meer: die zijn voor alle vier heuristieken
     gegarandeerd rand-tot-rand van hun eigen deelgebied/rij en lopen
     dus nooit door een al geplaatst onderdeel heen.
"""

from __future__ import annotations

import math
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, replace

from .models import (
    Materiaal,
    Nerfrichting,
    Onderdeel,
    Plaatsing,
    Rand,
    Reststuk,
    ZaagplanResultaat,
    Zaagsnede,
)

_RANDVOLGORDE = (Rand.LINKS, Rand.ONDER, Rand.BOVEN, Rand.RECHTS)


def _ruis_sleutel(waarde: float, rng: random.Random | None) -> float:
    """Vermenigvuldigt een sorteersleutel met een kleine willekeurige
    factor als ``rng`` gegeven is — gebruikt om de vier pak-heuristieken
    andere verwerkingsvolgordes te laten proberen dan hun standaard
    grootste/hoogste-eerst-sortering (zie ``genereer_zaagplan``'s
    ``zoek_tijdsbudget``). Zonder ``rng`` (het standaardgedrag) blijft
    de sortering exact zoals voorheen."""
    return waarde if rng is None else waarde * rng.uniform(0.7, 1.3)


@dataclass
class _Eenheid:
    """Eén plaatsbare eenheid: ofwel één exemplaar van een los
    onderdeel, ofwel een samengestelde groep (zie module-docstring)."""

    unit_id: str
    breedte: float
    hoogte: float
    mag_roteren: bool
    fabriekskantenband_vereist: bool
    kantenband_randen: frozenset[Rand]
    leden: list[tuple[Onderdeel, int]]  # (onderdeel, instantienummer), in plaatsingsvolgorde

    def expand(self, x: float, y: float, breedte: float, hoogte: float, geroteerd: bool) -> list[Plaatsing]:
        if len(self.leden) == 1:
            onderdeel, instantie = self.leden[0]
            return [Plaatsing(onderdeel.id, instantie, x, y, breedte, hoogte, geroteerd)]
        # Groep: verticaal stapelen in vaste volgorde, elk lid op zijn
        # eigen (ongeroteerde) breedte/hoogte, kerf ertussen. De groep
        # zelf roteert niet (mag_roteren=False), dus breedte/hoogte
        # hier zijn de niet-geroteerde afmetingen van het blok.
        plaatsingen: list[Plaatsing] = []
        cursor_y = y
        for onderdeel, instantie in self.leden:
            plaatsingen.append(
                Plaatsing(onderdeel.id, instantie, x, cursor_y, onderdeel.breedte, onderdeel.hoogte, False)
            )
            cursor_y += onderdeel.hoogte + self._kerf
        return plaatsingen

    # kerf wordt er tijdens het bouwen van de eenheid bijgezet zodat expand() erbij kan
    _kerf: float = 0.0


def _reden_niet_geplaatst(eenheid: _Eenheid, materiaal: Materiaal) -> str:
    """Legt in gewone-mensen-taal uit waarom ``eenheid`` zelfs op een
    volledig lege plaat van ``materiaal`` niet geplaatst kon worden —
    getoond in de zaagplan-UI (op Svens verzoek: "ik wil ook een
    functie als hij niks plaatst dat ie aangeeft ... waarom hij deze
    item niet heeft geplaatst"). Puur een afmeting-toets tegen het
    bruikbare werkgebied (na randafzaag-marge) — losstaand van de
    pak-heuristieken zelf, dus dit kan nooit een geldige plaatsing
    alsnog blokkeren of het pakresultaat beinvloeden.

    Houdt ook rekening met de fabriekskantenband-regel uit
    ``_plaats_fabriek_rand``: een onderdeel met een ``kantenband_randen``-
    eis die een rand van ``materiaal`` raakt die zelf al fabrieks-
    kantenband heeft, roteert daar NOOIT (op Svens eerdere, expliciete
    verzoek — anders komt de kantenband aan de verkeerde kant) — dus voor
    zo'n onderdeel telt hier ook alleen de ONGEROTEERDE afmeting. Zonder
    deze uitzondering zou de generieke "probeer het opnieuw"-reden
    misleidend zijn: geen zoekbudget of groepering kan dit ooit oplossen,
    ook niet op een extra plaat — de plaat zelf is voor déze combinatie
    van kantenband-eis en afmeting structureel te smal/kort."""

    x0, y0, x1, y1 = _werkgebied(materiaal)
    breedte_beschikbaar = x1 - x0
    hoogte_beschikbaar = y1 - y0
    b, h = eenheid.breedte, eenheid.hoogte
    is_groep = len(eenheid.leden) > 1
    omschrijving = (
        f"deze groep ({len(eenheid.leden)} onderdelen, samen {b:.0f}×{h:.0f}mm gestapeld)"
        if is_groep
        else f"dit onderdeel ({b:.0f}×{h:.0f}mm)"
    )

    fabriek_randen_geraakt = eenheid.kantenband_randen & materiaal.fabriekskantenband_randen
    mag_roteren_hier = eenheid.mag_roteren and not fabriek_randen_geraakt

    past_normaal = b <= breedte_beschikbaar and h <= hoogte_beschikbaar
    past_geroteerd = h <= breedte_beschikbaar and b <= hoogte_beschikbaar

    if past_normaal or (mag_roteren_hier and past_geroteerd):
        return (
            f"Past qua afmeting wel op een lege plaat van {materiaal.naam} "
            f"({breedte_beschikbaar:.0f}×{hoogte_beschikbaar:.0f}mm bruikbaar), maar kreeg toch geen "
            "plek toegewezen door de plaatsingsstrategie — probeer het zaagplan "
            "opnieuw te genereren, eventueel met een groter zoekbudget."
        )
    if fabriek_randen_geraakt and not past_normaal:
        rand_namen = ", ".join(sorted(r.value for r in fabriek_randen_geraakt))
        knelpunten = []
        if b > breedte_beschikbaar + 1e-9:
            knelpunten.append(f"breedte {b:.0f}mm > beschikbare {breedte_beschikbaar:.0f}mm")
        if h > hoogte_beschikbaar + 1e-9:
            knelpunten.append(f"hoogte {h:.0f}mm > beschikbare {hoogte_beschikbaar:.0f}mm")
        return (
            f"{omschrijving.capitalize()} heeft een fabriekskantenband-eis op rand \"{rand_namen}\" van "
            f"{materiaal.naam} en mag daardoor NOOIT roteren bij het plaatsen (anders komt de kantenband "
            f"aan de verkeerde kant) — in die vaste oriëntatie past het niet ({'; '.join(knelpunten)}). "
            "Dit lost een extra plaat niet op: elke plaat van dit materiaal heeft dezelfde afmeting."
        )
    if not eenheid.mag_roteren and past_geroteerd:
        reden_roteren = "een groep wordt nooit geroteerd" if is_groep else "de vereiste nerfrichting staat roteren niet toe"
        return f"{omschrijving.capitalize()} past alleen geroteerd op de plaat, maar {reden_roteren}."
    return (
        f"{omschrijving.capitalize()} is te groot voor {materiaal.naam} "
        f"({breedte_beschikbaar:.0f}×{hoogte_beschikbaar:.0f}mm bruikbaar), ook na roteren."
    )


def _bouw_eenheden(onderdelen: list[Onderdeel], kerf: float) -> tuple[list[_Eenheid], list[str]]:
    """Zet de onderdelenlijst (met aantallen en groepen) om in een
    lijst van plaatsbare eenheden. Retourneert ook eventuele
    validatiefouten (bv. inconsistente groepsafmetingen) als
    waarschuwingen-strings."""

    waarschuwingen: list[str] = []
    losse: list[_Eenheid] = []
    groepen: dict[str, list[Onderdeel]] = {}

    for onderdeel in onderdelen:
        if onderdeel.groep_id:
            groepen.setdefault(onderdeel.groep_id, []).append(onderdeel)
        else:
            for i in range(1, onderdeel.aantal + 1):
                losse.append(
                    _Eenheid(
                        unit_id=f"{onderdeel.id}#{i}",
                        breedte=onderdeel.breedte,
                        hoogte=onderdeel.hoogte,
                        mag_roteren=onderdeel.mag_roteren(),
                        fabriekskantenband_vereist=onderdeel.fabriekskantenband_vereist,
                        kantenband_randen=onderdeel.kantenband_randen,
                        leden=[(onderdeel, i)],
                        _kerf=kerf,
                    )
                )

    for groep_id, leden in groepen.items():
        leden_gesorteerd = sorted(leden, key=lambda o: (o.groep_volgorde if o.groep_volgorde is not None else 0))
        breedtes = {o.breedte for o in leden_gesorteerd}
        if len(breedtes) > 1:
            waarschuwingen.append(
                f"Groep '{groep_id}': leden hebben verschillende breedtes ({sorted(breedtes)}); "
                "grootste breedte wordt aangehouden voor het blok."
            )
        blok_breedte = max(o.breedte for o in leden_gesorteerd)
        aantal_leden = len(leden_gesorteerd)
        blok_hoogte = sum(o.breedte if False else o.hoogte for o in leden_gesorteerd) + kerf * (aantal_leden - 1)
        expand_leden: list[tuple[Onderdeel, int]] = [(o, 1) for o in leden_gesorteerd]
        losse.append(
            _Eenheid(
                unit_id=f"groep:{groep_id}",
                breedte=blok_breedte,
                hoogte=blok_hoogte,
                mag_roteren=False,
                fabriekskantenband_vereist=any(o.fabriekskantenband_vereist for o in leden_gesorteerd),
                # Vereenvoudiging: de unie van alle leden-eisen. Een groep
                # roteert toch al nooit (zie hierboven), dus dit is alleen
                # relevant om te bepalen tegen welke rand(en) de motor de
                # groep als geheel mag proberen te plaatsen.
                kantenband_randen=frozenset().union(*(o.kantenband_randen for o in leden_gesorteerd)),
                leden=expand_leden,
                _kerf=kerf,
            )
        )

    return losse, waarschuwingen


def _werkgebied(materiaal: Materiaal) -> tuple[float, float, float, float]:
    """Bruikbaar gebied (x0, y0, x1, y1) na randafzaag-marge, met
    uitzondering van randen die een fabriekskantenband hebben (die
    mogen nooit afgezaagd worden)."""

    x0, y0 = 0.0, 0.0
    x1, y1 = materiaal.lengte, materiaal.breedte
    marge = materiaal.randafzaag_marge
    te_negeren = materiaal.fabriekskantenband_randen
    if Rand.LINKS in materiaal.randafzaag_randen and Rand.LINKS not in te_negeren:
        x0 += marge
    if Rand.RECHTS in materiaal.randafzaag_randen and Rand.RECHTS not in te_negeren:
        x1 -= marge
    if Rand.ONDER in materiaal.randafzaag_randen and Rand.ONDER not in te_negeren:
        y0 += marge
    if Rand.BOVEN in materiaal.randafzaag_randen and Rand.BOVEN not in te_negeren:
        y1 -= marge
    return x0, y0, x1, y1


def _kies_afmeting(eenheid: _Eenheid, vereiste_orientatie: Nerfrichting | None) -> tuple[float, float, bool]:
    """Geeft (breedte, hoogte, geroteerd) terug voor de eenheid,
    rekening houdend met de nerfrichting-eis (indien van toepassing op
    het enkele onderdeel in deze eenheid)."""

    b, h = eenheid.breedte, eenheid.hoogte
    if not eenheid.mag_roteren and len(eenheid.leden) == 1:
        onderdeel = eenheid.leden[0][0]
        lang, kort = max(b, h), min(b, h)
        breedte_is_lang = b >= h
        if onderdeel.nerfrichting_vereist == Nerfrichting.LANGE_ZIJDE:
            # Lange zijde evenwijdig aan de x-as (plaat-nerf loopt langs x).
            return (lang, kort, not breedte_is_lang)
        if onderdeel.nerfrichting_vereist == Nerfrichting.KORTE_ZIJDE:
            return (kort, lang, breedte_is_lang)
    return (b, h, False)


# De vier randen van een onderdeel in de volgorde waarin ze doorschuiven
# bij een kwartslag tegen de klok in: de onderrand komt dan rechts te
# liggen, de rechterrand boven, enz.
_RANDEN_TEGEN_DE_KLOK = (Rand.ONDER, Rand.RECHTS, Rand.BOVEN, Rand.LINKS)


def _fabriek_orientaties(eenheid: _Eenheid, plaat_rand: Rand) -> list[bool]:
    """Welke oriëntaties van ``eenheid`` een van zijn eigen
    ``kantenband_randen`` tegen ``plaat_rand`` leggen, als lijst van
    "breedte en hoogte verwisseld?"-waarden (``False`` = 0° of 180°,
    ``True`` = 90° of 270°), voorkeur eerst. Leeg = kan niet.

    Een onderdeel mag hiervoor ook een halve of een kwartslag draaien:
    een stijl met kantenband op zijn (lange) linkerzijde hoort tegen de
    lange onderrand van een smalle plaat met fabriekskantenband op
    onder/boven, dus een kwartslag gedraaid (Sven: "de stijlen hebben
    een fabrieksrand maar liggen niet tegen een fabrieksrand" — voorheen
    werd alleen de ongedraaide stand geprobeerd, en viel zo'n stijl
    terug op een gewone plaatsing ergens midden op de plaat). Een halve
    slag verandert de afmetingen/nerfrichting niet en mag dus altijd
    (bv. een dwarsbalk met kantenband "onder" tegen de bovenrand); een
    kwartslag alleen als het onderdeel vrij mag roteren (geen
    nerf-eis), anders alleen de stand die de nerf afdwingt (zie
    ``_kies_afmeting``). Een groep draait bewust nooit (de volgorde van
    de leden ligt vast, zie ``_bouw_eenheden``). Zonder specifieke
    ``kantenband_randen`` (alleen het kale
    ``fabriekskantenband_vereist``) past elke rand, in beide standen als
    roteren mag."""

    if len(eenheid.leden) > 1:
        return [False] if not eenheid.kantenband_randen or plaat_rand in eenheid.kantenband_randen else []

    toegestaan = [False, True] if eenheid.mag_roteren else [_kies_afmeting(eenheid, None)[2]]
    if not eenheid.kantenband_randen:
        return toegestaan

    doel = _RANDEN_TEGEN_DE_KLOK.index(plaat_rand)
    kwartslagen = {
        (doel - _RANDEN_TEGEN_DE_KLOK.index(rand)) % 4 for rand in eenheid.kantenband_randen
    }
    return [verwisseld for verwisseld in toegestaan if any(k % 2 == verwisseld for k in kwartslagen)]


def _classificeer_restruimte(vrije_rechten: list[tuple[float, float, float, float]], materiaal: Materiaal):
    reststukken: list[Reststuk] = []
    afval = 0.0
    for (x, y, w, h) in vrije_rechten:
        if w <= 0 or h <= 0:
            continue
        if w >= materiaal.min_reststukgrootte and h >= materiaal.min_reststukgrootte:
            reststukken.append(Reststuk(x, y, w, h))
        else:
            afval += w * h
    return reststukken, afval


def _splits_vrije_rechthoek(
    fx: float,
    fy: float,
    fw: float,
    fh: float,
    genomen_b: float,
    genomen_h: float,
    volgnr_start: int,
    stuk_b: float | None = None,
    stuk_h: float | None = None,
) -> tuple[list[tuple[float, float, float, float]], list[Zaagsnede]]:
    """Splitst het vrije rechthoek ``(fx, fy, fw, fh)`` in maximaal twee
    nieuwe vrije rechthoeken nadat er een stuk van ``genomen_b x
    genomen_h`` (kerf inbegrepen) uit de linkerbenedenhoek genomen is —
    kortste-as-eerst heuristiek. Gebruikt door ``_pak_guillotine``: zo
    is elke snede rand-tot-rand en loopt hij nooit door een geplaatst
    onderdeel heen.

    ``stuk_b``/``stuk_h`` (de echte afmetingen van het stuk, zonder kerf):
    blijft er naast het stuk maar een reepje over dat smaller is dan de
    kerf, dan komt er geen nieuw vrij rechthoek, maar moet het stuk daar
    nog steeds op maat gezaagd worden - dan wel een snede, op de rand van
    het stuk (voorheen ontbrak die)."""

    rest_breedte = fw - genomen_b
    rest_hoogte = fh - genomen_h
    reepje_rechts = rest_breedte <= 1e-6 and stuk_b is not None and stuk_b < fw - 1e-6
    reepje_boven = rest_hoogte <= 1e-6 and stuk_h is not None and stuk_h < fh - 1e-6
    nieuwe_rechten: list[tuple[float, float, float, float]] = []
    sneden: list[Zaagsnede] = []

    if rest_breedte < rest_hoogte:
        if rest_breedte > 1e-6:
            snede_x = fx + genomen_b
            sneden.append(Zaagsnede(volgnr_start + len(sneden), "verticaal", snede_x, fy, fy + fh))
            nieuwe_rechten.append((snede_x, fy, rest_breedte, fh))
        if rest_hoogte > 1e-6:
            snede_y = fy + genomen_h
            sneden.append(Zaagsnede(volgnr_start + len(sneden), "horizontaal", snede_y, fx, fx + genomen_b))
            nieuwe_rechten.append((fx, snede_y, genomen_b, rest_hoogte))
    else:
        if rest_hoogte > 1e-6:
            snede_y = fy + genomen_h
            sneden.append(Zaagsnede(volgnr_start + len(sneden), "horizontaal", snede_y, fx, fx + fw))
            nieuwe_rechten.append((fx, snede_y, fw, rest_hoogte))
        if rest_breedte > 1e-6:
            snede_x = fx + genomen_b
            sneden.append(Zaagsnede(volgnr_start + len(sneden), "verticaal", snede_x, fy, fy + genomen_h))
            nieuwe_rechten.append((snede_x, fy, rest_breedte, genomen_h))

    # Reepjes pas NA de gewone opsplitsing, en alleen binnen het blok van
    # het stuk zelf (fx..fx+genomen_b, fy..fy+genomen_h) - over de volle
    # breedte/hoogte van het vrije rechthoek zou zo'n snede door een later,
    # hoger/breder stuk ernaast kunnen lopen.
    if reepje_rechts:
        sneden.append(Zaagsnede(volgnr_start + len(sneden), "verticaal", fx + stuk_b, fy, fy + genomen_h))
    if reepje_boven:
        sneden.append(Zaagsnede(volgnr_start + len(sneden), "horizontaal", fy + stuk_h, fx, fx + genomen_b))

    return nieuwe_rechten, sneden


def _landschap_indien_vrij(
    eenheid: _Eenheid, b: float, h: float, rot: bool, beschikbare_breedte: float
) -> tuple[float, float, bool]:
    """Voor 'rijen' ("lange zijdes eerst"): een eenheid die vrij
    mag roteren (geen nerf-eis, geen groep) wordt met zijn langste zijde
    langs de x-as gelegd — zoals de strategienaam zelf al belooft — i.p.v.
    de invoer-oriëntatie van het onderdeel klakkeloos over te nemen.
    Zonder deze stap roteerde de motor in deze twee strategieën nooit een
    vrij onderdeel, ook niet als "liggend" leggen overduidelijk beter
    (kortere rij, dus meer rijen passend) of zelfs noodzakelijk was (om
    sowieso te passen op een plaat die smaller is dan het onderdeel hoog
    staat). ``_pak_guillotine``/``_pak_nesting`` hebben dit al langer
    via hun eigen zoektocht over beide oriëntaties.

    Bugfix: de eerste versie van deze functie koos ALTIJD het landschap
    (lange zijde langs x), ook als die lange zijde domweg breder is dan
    de hele plaat terwijl de staande oriëntatie (korte zijde langs x)
    wél binnen de plaatbreedte past — zo'n onderdeel eindigde dan
    blijvend als niet-geplaatst (ook op een verse plaat), puur door deze
    voorkeur zelf, wat precies andersom is dan de bedoeling. Val daarom
    terug op de staande oriëntatie zodra landschap niet binnen
    ``beschikbare_breedte`` past maar staand wel."""
    if not eenheid.mag_roteren:
        return b, h, rot
    lang, kort = max(b, h), min(b, h)
    if lang <= beschikbare_breedte + 1e-9 or kort > beschikbare_breedte + 1e-9:
        return lang, kort, h > b
    return kort, lang, b > h


_HOOGTE_TOLERANTIE = 1.0  # mm; "(bijna) gelijke hoogte" bij het groeperen in _pak_rijen


def _groepeer_op_hoogte(
    genormaliseerd: list[tuple[_Eenheid, float, float, bool]]
) -> list[list[tuple[_Eenheid, float, float, bool]]]:
    """Groepeer een op hoogte (aflopend) gesorteerde lijst in
    aaneengesloten hoogte-groepen: opeenvolgende stukken waarvan de
    hoogte minder dan ``_HOOGTE_TOLERANTIE`` verschilt van het eerste
    (hoogste) lid van de groep. Voorkomt dat (bijna) identieke
    onderdelen toevallig over meerdere rijen versnipperen (zie
    ``_pak_rijen``'s docstring)."""

    groepen: list[list[tuple[_Eenheid, float, float, bool]]] = []
    for item in genormaliseerd:
        if groepen and abs(item[2] - groepen[-1][0][2]) <= _HOOGTE_TOLERANTIE:
            groepen[-1].append(item)
        else:
            groepen.append([item])
    return groepen


def _sorteer_op_hoogte_met_ruis(
    genormaliseerd: list[tuple[_Eenheid, float, float, bool]], rng: random.Random | None
) -> list[tuple[_Eenheid, float, float, bool]]:
    """Sorteert op hoogte aflopend (ongewijzigd t.o.v. het
    standaardgedrag) en husselt daarna, als ``rng`` gegeven is, alleen
    de volgorde BINNEN elke (bijna) gelijke-hoogte-groep (zie
    ``_groepeer_op_hoogte``) door elkaar — nooit tússen groepen. Anders
    dan bij ``_pak_guillotine``/``_pak_nesting`` (waar ``_ruis_sleutel``
    de sorteersleutel zelf mag vervuilen) is de aflopende-hoogte-volgorde
    hier een STRUCTURELE aanname waar ``_vul_rij``/``_vind_plaatsbare_rij``
    op leunen: een latere groep wordt verondersteld nooit hoger te zijn
    dan een eerdere. Ruis op de sorteersleutel zelf bleek tijdens het
    testen van deze zoekfunctie die aanname te kunnen breken (een kort
    onderdeel dat door ruis toevallig vóór een lang onderdeel kwam),
    waardoor een rij hoger uitpakte dan de resterende plaathoogte
    toestond. Husselen binnen een groep is wel altijd veilig: de leden
    verschillen per definitie minder dan ``_HOOGTE_TOLERANTIE`` in
    hoogte, dus de daadwerkelijk geplaatste rijhoogte (het maximum van
    de leden die ook echt in de rij komen) verandert daar niet wezenlijk
    door."""
    genormaliseerd = sorted(genormaliseerd, key=lambda t: t[2], reverse=True)
    if rng is None:
        return genormaliseerd
    resultaat: list[tuple[_Eenheid, float, float, bool]] = []
    for groep in _groepeer_op_hoogte(genormaliseerd):
        groep = list(groep)
        rng.shuffle(groep)
        resultaat.extend(groep)
    return resultaat


def _vul_rij(
    resterend: list[tuple[_Eenheid, float, float, bool]],
    x0: float,
    x1: float,
    kerf: float,
) -> tuple[list[list[list[tuple[_Eenheid, float, float, bool]]]], list[tuple[_Eenheid, float, float, bool]], float]:
    """Vult één rij vanaf ``x0`` tot ``x1`` met KOLOMMEN — elke kolom is
    een lijst van één of meer op elkaar gestapelde BANDEN (onderin tot
    bovenin), en elke band is zelf weer een lijst van één of meer
    onderdelen die side-by-side dezelfde band delen. Zonder dit zou een
    korter onderdeel per se een eigen, nieuwe kolom naast de rest moeten
    krijgen als het net zo goed boven een al bestaande, minder hoge kolom
    past (het "meerdere stukken per kolom"-idee), én zou de OVERGEBLEVEN
    BREEDTE naast zo'n stukje binnen die kolom altijd blijven liggen —
    ook als er nog een paar smallere onderdelen van (bijna) dezelfde
    hoogte zijn die daar samen wél naast elkaar in zouden passen.
    Toegevoegd/uitgebreid op Svens verzoek, in twee stappen:
    1. Losse "ruggen" (van dezelfde hoogte-groep) die allebei hun eigen
       kolom kregen terwijl ze samen — en met een derde, nog kortere
       "rug" erbij — ruim in één kolom hadden gepast: "dan zouden alle
       ruggen toch onder elkaar kunnen en dan nog in de rij passen".
    2. Concreet voorbeeld met een "bodem" van (in zijn kolom) 500mm
       vrije breedte, waar 4 "dwarsbalken" samen in diezelfde band van
       ~100mm hoog naast elkaar hadden gepast i.p.v. dat er maar ÉÉN
       dwarsbalk per band gebruikt werd en de rest van die 500mm breedte
       braak bleef liggen: "dan passen daar ook 4 dwarsbalken binnen in
       die strook van 100mm".
    3. Concreet voorbeeld met twee identieke "lade rug korf"-stukken:
       geen van beiden past nog op de (al volledig hoge) kolommen van de
       vorige groep ("lade bodem"), dus allebei zouden ze — net als
       vóór deze stap — ieder hun eigen nieuwe kolom krijgen, terwijl de
       tweede prima op de kolom van de EERSTE had gepast: "die 2e lade
       rug korf past makkelijk nog onder de andere 2 lade ruggen" (een
       derde, nog kortere "lade rug bestek" stapelt daar in de praktijk
       ook nog bovenop). Zie punt 3 in de simulatie-uitleg hieronder.

    De eerste (hoogte-bepalende) hoogte-groep in ``resterend`` mag
    gedeeltelijk in de rij komen (de rest wacht op een volgende rij,
    normaal gedrag als er simpelweg meer stukken van die hoogte zijn dan
    in één rij passen); elk lid daarvan start zijn eigen, nieuwe kolom
    (met daarin één band van één stuk). Elke latere, kortere hoogte-groep
    mag alleen als GEHEEL meedoen — nooit gedeeltelijk, want dat zou
    (bijna) identieke onderdelen zonder aanleiding over meerdere RIJEN
    verspreiden (zie ``_pak_rijen``'s docstring / OVERDRACHT.md) — maar
    voor elke bestaande kolom (in volgorde) wordt eerst zoveel mogelijk
    van de groep als een nieuwe, gedeelde band boven op die kolom
    gestapeld (zolang de resterende hoogte-ruimte en de kolombreedte het
    toelaten — meerdere leden naast elkaar in diezelfde band, net als een
    mini-rij); is een kolom's hoogte-ruimte op, dan gaat de rest van de
    groep naar de volgende bestaande kolom, enzovoort. Wat dan nog
    overblijft krijgt elk zijn eigen nieuwe kolom ernaast — maar (punt 3
    hierboven) daarna wordt de HELE kolom-ronde opnieuw geprobeerd, dus
    ook tegen die zojuist aangemaakte kolom(men): zo kan een later lid
    van dezelfde groep alsnog op de nieuwe kolom van een eerder lid
    stapelen, in plaats van dat elk lid domweg zijn eigen, aparte kolom
    houdt. Dit wordt eerst gesimuleerd voor de hele groep tegelijk —
    lukt ook maar één lid nergens (geen kolom met genoeg ruimte, en ook
    geen plek meer voor een nieuwe kolom), dan wordt de HELE groep alsnog
    in zijn geheel overgeslagen (dezelfde alles-of-niets-regel als
    voorheen), zodat een net-niet-passende groep niet alsnog gedeeltelijk
    versnippert.
"""

    kolommen: list[list[list[tuple[_Eenheid, float, float, bool]]]] = []
    kolom_breedtes: list[float] = []
    kolom_hoogtes: list[float] = []
    overig: list[tuple[_Eenheid, float, float, bool]] = []
    cursor_x = x0
    rij_hoogte = 0.0

    groepen = _groepeer_op_hoogte(resterend)
    if not groepen:
        return kolommen, overig, rij_hoogte

    genomen = 0
    for (eenheid, b, h, rot) in groepen[0]:
        if (cursor_x + b) <= x1 + 1e-9:
            kolommen.append([[(eenheid, b, h, rot)]])
            kolom_breedtes.append(b)
            kolom_hoogtes.append(h)
            rij_hoogte = max(rij_hoogte, h)
            cursor_x += b + kerf
            genomen += 1
        else:
            break
    overig.extend(groepen[0][genomen:])

    for groep in groepen[1:]:
        # Als de rij nog helemaal leeg is (de allereerste, hoogte-
        # bepalende groep paste zelf al niet één keer), mag een latere,
        # kortere groep ook niet alsnog een eigen kolom beginnen — anders
        # zou de rijhoogte op 0 blijven staan (die wordt hierboven alleen
        # bijgewerkt vanuit de eerste groep) terwijl er toch kolommen met
        # een echte hoogte in de rij zouden staan, wat de aanroeper
        # (``_pak_rijen``) de volgende rij bovenop deze zou laten leggen.
        # Zelfde bewuste "alles hangt af van de eerste groep"-regel als
        # voorheen (``if rij and ...``), nu alleen expliciet gemaakt.
        if not kolommen:
            overig.extend(groep)
            continue

        # Eerst simuleren zonder de echte kolomstaat aan te passen, zodat
        # bij een gedeeltelijke mislukking niets hoeft te worden
        # teruggedraaid (zie docstring hierboven).
        sim_hoogtes = list(kolom_hoogtes)
        sim_breedtes = list(kolom_breedtes)
        sim_cursor_x = cursor_x
        # Elke toewijzing is (kolom_idx | None, band) — een band is een
        # lijst van één of meer leden van DEZE groep die samen, side-by-
        # side, één nieuwe horizontale laag boven op kolom_idx vormen (of,
        # bij kolom_idx=None, een gloednieuwe kolom naast de rest).
        toewijzingen: list[tuple[int | None, list[tuple[_Eenheid, float, float, bool]]]] = []
        stapel_limiet = rij_hoogte
        pool = list(groep)

        # Herhaal "probeer alle kolommen te vullen" tot de pool leeg is of
        # geen enkele kolom nog iets kwijt kan — dan krijgt het eerste
        # resterende lid een gloednieuwe kolom, en wordt de HELE
        # kolom-ronde opnieuw geprobeerd (dus ook tegen die zojuist
        # aangemaakte kolom). Zonder die herhaling zou een groep met
        # meerdere leden die geen van allen op een bestaande (oudere)
        # kolom passen, maar wél samen in één nieuwe kolom hadden
        # gepast, ieder een eigen, aparte kolom krijgen i.p.v. samen te
        # stapelen — precies het concrete geval waarbij een tweede "lade
        # rug korf" zijn eigen kolom kreeg terwijl hij prima op de kolom
        # van de eerste had gepast (beide leden van dezelfde groep, dus
        # geen van beiden kan op de bodem-kolommen van de vorige, hogere
        # groep stapelen — die zijn al vol).
        haalbaar = True
        while pool:
            voortgang = False
            for idx in range(len(sim_hoogtes)):
                gat = stapel_limiet - sim_hoogtes[idx]
                resterende_breedte = sim_breedtes[idx]
                band: list[tuple[_Eenheid, float, float, bool]] = []
                band_hoogte = 0.0
                overgebleven: list[tuple[_Eenheid, float, float, bool]] = []
                for (eenheid, b, h, rot) in pool:
                    if h + kerf <= gat + 1e-9 and b <= resterende_breedte + 1e-9:
                        band.append((eenheid, b, h, rot))
                        resterende_breedte -= b + kerf
                        band_hoogte = max(band_hoogte, h)
                    else:
                        overgebleven.append((eenheid, b, h, rot))
                if band:
                    sim_hoogtes[idx] += band_hoogte + kerf
                    toewijzingen.append((idx, band))
                    pool = overgebleven
                    voortgang = True
                if not pool:
                    break
            if not pool or voortgang:
                continue

            eenheid, b, h, rot = pool[0]
            if sim_cursor_x + b <= x1 + 1e-9:
                sim_hoogtes.append(h)
                sim_breedtes.append(b)
                sim_cursor_x += b + kerf
                toewijzingen.append((None, [(eenheid, b, h, rot)]))
                pool = pool[1:]
            else:
                haalbaar = False
                break

        if not haalbaar:
            overig.extend(groep)
            continue

        for (kolom_idx, band) in toewijzingen:
            band_hoogte = max(h for (_, _, h, _) in band)
            if kolom_idx is not None:
                kolommen[kolom_idx].append(band)
                kolom_hoogtes[kolom_idx] += band_hoogte + kerf
            else:
                kolommen.append([band])
                kolom_breedtes.append(band[0][1])
                kolom_hoogtes.append(band_hoogte)
                cursor_x += band[0][1] + kerf

    return kolommen, overig, rij_hoogte


def _groepssneden(leden: list[Plaatsing]) -> list[Zaagsnede]:
    """De sneden tussen de leden van een gestapelde groep (hoofdstuk 5),
    elk begrensd tot het groepslid zelf. Normaal liggen de leden boven
    elkaar; bij "verticaal" rekent ``_pak_rijen`` op een gespiegelde plaat
    (zie ``_pak_kolommen``) en liggen ze daarin naast elkaar - dan dus
    verticale sneden. Gedeeld door alle strategieen (Efficient en
    Guillotine noteerden tussen groepsleden eerder helemaal geen snede)."""

    if len(leden) < 2:
        return []
    if len({round(lid.x, 6) for lid in leden}) == 1:
        return [
            Zaagsnede(0, "horizontaal", round(lid.y + lid.hoogte, 6), lid.x, lid.x + lid.breedte)
            for lid in sorted(leden, key=lambda p: p.y)[:-1]
        ]
    return [
        Zaagsnede(0, "verticaal", round(lid.x + lid.breedte, 6), lid.y, lid.y + lid.hoogte)
        for lid in sorted(leden, key=lambda p: p.x)[:-1]
    ]


def _plaats_rij(
    kolommen: list[list[list[tuple[_Eenheid, float, float, bool]]]],
    x0: float,
    cursor_y: float,
    kerf: float,
    rij_hoogte: float | None = None,
) -> tuple[list[Plaatsing], list[Zaagsnede], list[float], float, list[tuple[float, float, float, float]]]:
    """Plaatst de kolommen van één rij/strook (van links naar rechts,
    startend op ``x0``); elke kolom kan één of meer op elkaar gestapelde
    BANDEN bevatten (zie ``_vul_rij``) — onderin de eerste band, dan
    omhoog — en elke band kan zelf weer één of meer leden side-by-side
    bevatten (het "meerdere dwarsbalken naast elkaar in dezelfde band"-
    geval). Bouwt de interne scheidingssneden op (nog met voorlopig
    volgnummer 0, zie ``_bouw_zaagvolgorde_uit_rijen``): horizontale
    naden tussen twee banden in dezelfde kolom (begrensd tot de breedte
    van díe kolom zelf — het breedste lid erin), en verticale naden
    tussen leden binnen dezelfde band (begrensd tot de hoogte van díe
    band zelf) — nooit de volle plaatbreedte/-hoogte, anders zou zo'n
    snede dwars door een ander onderdeel in dezelfde rij heen lopen. Dit
    geldt ook voor de sneden binnen een gestapelde groep (hoofdstuk 5),
    begrensd tot de breedte van het groepslid zelf (niet de hele band) —
    alle drie zijn voor deze functie hetzelfde soort interne naad.
    Sinds Sven de zaagvolgorde liet narekenen ("hoe bereken je wat
    hergebruikt kan worden") maakt dit ook de sneden boven een stuk dat
    lager is dan zijn band, rechts van een band die smaller is dan zijn
    kolom, en boven een kolom die lager is dan ``rij_hoogte`` - die
    ontbraken, zodat zulke stukken in de zaagvolgorde nooit op maat
    gezaagd werden - en levert die restruimte als vrije rechthoeken
    (laatste retourwaarde).
    Retourneert ook de kolomranden (x-posities tussen kolommen) en de
    eind-x-positie; de sneden TUSSEN kolommen zelf worden hier bewust NOG
    NIET gebouwd — dat kan pas nadat de aanroeper de rij heeft afgerond en
    de ECHTE bovengrens van de rij kent (zie de bugfix-toelichting bij
    ``_bouw_zaagvolgorde_uit_rijen``). Losgetrokken uit
    ``_pak_rijen``."""

    plaatsingen: list[Plaatsing] = []
    groep_sneden: list[Zaagsnede] = []
    kolom_randen: list[float] = []
    vrije_rechten: list[tuple[float, float, float, float]] = []
    x = x0
    for kolom in kolommen:
        kolom_breedte = max(b for band in kolom for (_, b, _, _) in band)
        # Sneden binnen deze kolom, in de volgorde waarin je ze zaagt: eerst
        # de naden tussen de banden (over de volle kolombreedte), dan per
        # band de naden tussen de stukken, dan per stuk wat er nog boven
        # moet (restruimte, groepsleden).
        kolom_sneden: list[Zaagsnede] = []
        band_sneden: list[Zaagsnede] = []
        stuk_sneden: list[Zaagsnede] = []
        y = cursor_y
        eerste_band = True
        for band in kolom:
            band_hoogte = max(h for (_, _, h, _) in band)
            if not eerste_band:
                # Naad tussen deze band en de vorige in dezelfde kolom
                # (zie _vul_rij), begrensd tot de kolombreedte zelf.
                kolom_sneden.append(Zaagsnede(0, "horizontaal", round(y, 6), x, x + kolom_breedte))
            eerste_band = False
            x_in_band = x
            for i, (eenheid, b, h, rot) in enumerate(band):
                nieuwe = eenheid.expand(x_in_band, y, b, h, rot)
                plaatsingen.extend(nieuwe)
                if i < len(band) - 1:
                    # Naad naar het volgende stuk in dezelfde band,
                    # begrensd tot de hoogte van die band zelf.
                    band_sneden.append(Zaagsnede(0, "verticaal", round(x_in_band + b, 6), y, y + band_hoogte))
                if h < band_hoogte - 1e-6:
                    # Stuk lager dan zijn band: snede erboven, en wat erboven
                    # overblijft telt mee als reststuk/afval (zie
                    # _classificeer_restruimte) - voorheen telde het nergens.
                    stuk_sneden.append(Zaagsnede(0, "horizontaal", round(y + h, 6), x_in_band, x_in_band + b))
                    if band_hoogte - h - kerf > 1e-6:
                        vrije_rechten.append((x_in_band, y + h + kerf, b, band_hoogte - h - kerf))
                stuk_sneden.extend(_groepssneden(nieuwe))
                x_in_band += b + kerf
            band_eind = x_in_band - kerf
            if band_eind < x + kolom_breedte - 1e-6:
                # Band smaller dan zijn kolom: snede rechts ervan + restruimte.
                band_sneden.append(Zaagsnede(0, "verticaal", round(band_eind, 6), y, y + band_hoogte))
                rest = x + kolom_breedte - (band_eind + kerf)
                if rest > 1e-6:
                    vrije_rechten.append((band_eind + kerf, y, rest, band_hoogte))
            y += band_hoogte + kerf
        inhoud_top = y - kerf
        if rij_hoogte is not None and inhoud_top < cursor_y + rij_hoogte - 1e-6:
            # Kolom lager dan zijn rij: snede erboven + restruimte.
            kolom_sneden.append(Zaagsnede(0, "horizontaal", round(inhoud_top, 6), x, x + kolom_breedte))
            rest = cursor_y + rij_hoogte - (inhoud_top + kerf)
            if rest > 1e-6:
                vrije_rechten.append((x, inhoud_top + kerf, kolom_breedte, rest))
        groep_sneden.extend(kolom_sneden + band_sneden + stuk_sneden)
        kolom_randen.append(round(x + kolom_breedte, 6))
        x += kolom_breedte + kerf

    return plaatsingen, groep_sneden, kolom_randen, x, vrije_rechten




def _bouw_zaagvolgorde_uit_rijen(
    rij_grenzen: list[tuple[float, float]],
    rijen_kolomranden: list[list[float]],
    groep_sneden: list[Zaagsnede],
    x0: float,
    x1: float,
    y1: float,
) -> list[Zaagsnede]:
    """Zet de volledige-breedte sneden tussen de rijen onderling, de
    tussen-kolom-sneden per rij en de interne groeps-naadsneden samen tot
    één doorlopend genummerde zaagvolgorde. ``rij_grenzen`` is de lijst
    (rij_start_y, rij_hoogte) in plaatsingsvolgorde (dus al oplopend in
    y) — de ENIGE bron voor waar een rij daadwerkelijk begint, in plaats
    van (zoals voorheen) elke losse y-coördinaat uit de platte
    plaatsingenlijst te gebruiken, wat bij een gestapelde groep ten
    onrechte ook diens interne naad-hoogtes als "rijgrens" behandelde en
    zo een volle-breedte snede dwars door andere onderdelen in dezelfde
    rij liet lopen.

    Bugfix (tussen-kolom-sneden): een eerdere versie liet elke
    tussen-kolom-snede stoppen bij de CONTENT-hoogte van de rij zelf
    (``rij_hoogte``, zonder kerf) — maar de rij als fysiek stuk plaat is,
    zodra er nóg een rij op volgt, in werkelijkheid net zo hoog als waar
    de horizontale scheidingssnede naar die volgende rij ligt (inclusief
    de kerf-tussenruimte); een snede die daar 1 kerf te vroeg stopt is
    geen echte rand-tot-rand snede van het fysieke rij-stuk meer. Elke
    rij i (behalve de laatste) krijgt zijn tussen-kolom-sneden daarom nu
    tot ``rij_grenzen[i + 1][0]`` (waar de volgende rij begint); de
    laatste rij behoudt haar eigen content-hoogte als bovengrens (daar
    ligt de eventuele scheidingssnede naar de restruimte ook echt, zie
    hieronder — dat was al correct)."""

    sneden: list[Zaagsnede] = []
    volgnr = 1

    for (rij_y, _) in rij_grenzen[1:]:
        sneden.append(Zaagsnede(volgnr, "horizontaal", rij_y, x0, x1))
        volgnr += 1

    if rij_grenzen:
        laatste_y, laatste_hoogte = rij_grenzen[-1]
        top_laatste_rij = laatste_y + laatste_hoogte
        if top_laatste_rij < y1 - 1e-6:
            sneden.append(Zaagsnede(volgnr, "horizontaal", top_laatste_rij, x0, x1))
            volgnr += 1

    kolom_sneden: list[Zaagsnede] = []
    for i, kolom_randen in enumerate(rijen_kolomranden):
        cursor_y_i, rij_hoogte_i = rij_grenzen[i]
        rij_top = rij_grenzen[i + 1][0] if i + 1 < len(rij_grenzen) else cursor_y_i + rij_hoogte_i
        # Ook de rechterrand van de laatste kolom, als er rechts ervan nog
        # iets overblijft (anders werd het laatste stuk van een rij nooit
        # op maat gezaagd).
        te_zagen = kolom_randen if kolom_randen and kolom_randen[-1] < x1 - 1e-6 else kolom_randen[:-1]
        for grens_x in te_zagen:
            kolom_sneden.append(Zaagsnede(0, "verticaal", grens_x, cursor_y_i, rij_top))

    # Eerst de kolommen los, dan pas wat er binnen een kolom gezaagd moet
    # worden (zie _plaats_rij) - andersom kan een paneelzaag niet.
    for snede in kolom_sneden + groep_sneden:
        sneden.append(replace(snede, volgnummer=volgnr))
        volgnr += 1

    y0 = rij_grenzen[0][0] if rij_grenzen else y1
    return _zet_sneden_op_deelgebieden(sneden, x0, y0, x1, y1)


def _zet_sneden_op_deelgebieden(
    sneden: list[Zaagsnede], x0: float, y0: float, x1: float, y1: float
) -> list[Zaagsnede]:
    """Loopt de zaagvolgorde na zoals een paneelzaag 'm uitvoert: elke
    snede gaat van rand tot rand door het deelgebied waarin hij valt, en
    splitst dat deelgebied in tweeen. Zet start/einde van elke snede exact
    op de randen van dat deelgebied. De pak-functies noteren sneden niet
    overal op dezelfde manier (voor of na de kerf, begrensd tot een stuk
    of tot een kolom), wat voor de sneden binnen een kolom of groep
    kleine verschillen gaf t.o.v. het echte deelgebied; zo sluit het
    altijd. Een snede die op de rand van zijn deelgebied valt (al
    gezaagd) wordt weggelaten; nummering loopt daarna weer door vanaf 1."""

    gebieden = [(x0, y0, x1, y1)]
    resultaat: list[Zaagsnede] = []
    e = 1e-6
    for snede in sorted(sneden, key=lambda z: z.volgnummer):
        midden = (snede.start + snede.einde) / 2
        gevonden = None
        for gebied in gebieden:
            gx0, gy0, gx1, gy1 = gebied
            if snede.richting == "verticaal":
                if gx0 - e <= snede.positie <= gx1 + e and gy0 - e <= midden <= gy1 + e:
                    gevonden = gebied
                    break
            elif gy0 - e <= snede.positie <= gy1 + e and gx0 - e <= midden <= gx1 + e:
                gevonden = gebied
                break
        if gevonden is None:
            resultaat.append(snede)  # valt buiten het bijgehouden gebied: ongewijzigd laten
            continue
        gx0, gy0, gx1, gy1 = gevonden
        if snede.richting == "verticaal":
            if snede.positie <= gx0 + e or snede.positie >= gx1 - e:
                continue
            gebieden.remove(gevonden)
            gebieden += [(gx0, gy0, snede.positie, gy1), (snede.positie, gy0, gx1, gy1)]
            resultaat.append(replace(snede, start=gy0, einde=gy1))
        else:
            if snede.positie <= gy0 + e or snede.positie >= gy1 - e:
                continue
            gebieden.remove(gevonden)
            gebieden += [(gx0, gy0, gx1, snede.positie), (gx0, snede.positie, gx1, gy1)]
            resultaat.append(replace(snede, start=gx0, einde=gx1))
    return [replace(z, volgnummer=i) for i, z in enumerate(resultaat, start=1)]


def _vind_plaatsbare_rij(
    resterend: list[tuple[_Eenheid, float, float, bool]], x0: float, x1: float, cursor_y: float, y1: float, kerf: float
) -> tuple[list[tuple[_Eenheid, float, float, bool]], list[tuple[_Eenheid, float, float, bool]], float, list[str]]:
    """Zoekt, hoogte-groep voor hoogte-groep (aflopend, dus hoogste
    eerst — zie ``_groepeer_op_hoogte``), de eerste groep die nog binnen
    de resterende hoogte (``y1 - cursor_y``) past én daadwerkelijk een
    niet-lege rij oplevert (dus ook breed genoeg is), en vult daarmee een
    rij via ``_vul_rij``. Groepen die worden overgeslagen omdat ze niet
    passen komen NOOIT meer aan de beurt (``cursor_y`` loopt alleen maar
    op, dus de resterende hoogte wordt nooit meer groter) en worden dus
    direct als definitief niet-plaatsbaar teruggegeven — dat is precies
    de fix voor het hiaat waarbij één te hoge groep (bv. een groep
    ladefronten die net niet past) tot dan toe de hele rest van de
    onderdelenlijst onnodig liet weggooien, terwijl kleinere onderdelen
    verderop in de lijst wél in een lagere rij zouden passen.

    Retourneert (rij, overig_na_rij, rij_hoogte, definitief_niet_plaatsbaar)
    — ``rij`` is leeg als zelfs de laagste resterende groep niet meer
    past (qua hoogte of breedte), in welk geval ``overig_na_rij`` leeg is
    en alle resterende onderdelen in ``definitief_niet_plaatsbaar`` zitten."""

    groepen = _groepeer_op_hoogte(resterend)
    overgeslagen: list[str] = []

    for i, groep in enumerate(groepen):
        groep_hoogte = groep[0][2]
        if cursor_y + groep_hoogte > y1 + 1e-9:
            overgeslagen.extend(e.unit_id for (e, _, _, _) in groep)
            continue

        kandidaat = [item for latere_groep in groepen[i:] for item in latere_groep]
        rij, overig_na_rij, rij_hoogte = _vul_rij(kandidaat, x0, x1, kerf)
        if not rij:
            # Zelfs deze (lagere) groep is te breed voor de plaat -> ook
            # definitief niet plaatsbaar, probeer de volgende (nog lagere) groep.
            overgeslagen.extend(e.unit_id for (e, _, _, _) in groep)
            continue

        return rij, overig_na_rij, rij_hoogte, overgeslagen

    # Geen enkele resterende hoogte-groep past nog, ook niet de laagste.
    return [], [], 0.0, overgeslagen


def _pak_rijen(
    eenheden: list[_Eenheid],
    werkgebied: tuple[float, float, float, float],
    kerf: float,
    rng: random.Random | None = None,
) -> tuple[list[Plaatsing], list[tuple[float, float, float, float]], list[str], list[Zaagsnede]]:
    """Rij-gebaseerde packing voor de strategie 'lange zijdes eerst':
    volledige-breedte rijen, binnen een rij van links naar rechts."""

    x0, y0, x1, y1 = werkgebied
    breedte_plaat = x1 - x0

    # Voor elke eenheid de hoogte bepalen die hij in een rij zou
    # innemen (rekening houdend met eventuele nerf-rotatie-eis, en anders
    # -- "lange zijdes eerst" -- de langste zijde langs de x-as).
    genormaliseerd = []
    for eenheid in eenheden:
        b, h, rot = _kies_afmeting(eenheid, None)
        b, h, rot = _landschap_indien_vrij(eenheid, b, h, rot, breedte_plaat)
        genormaliseerd.append((eenheid, b, h, rot))

    # Grootste hoogte eerst (rijen met de langste/breedste stukken onderaan/bovenaan eerst).
    genormaliseerd = _sorteer_op_hoogte_met_ruis(genormaliseerd, rng)

    plaatsingen: list[Plaatsing] = []
    niet_geplaatst: list[str] = []
    resterend = list(genormaliseerd)
    cursor_y = y0
    vrije_rechten: list[tuple[float, float, float, float]] = []
    rij_grenzen: list[tuple[float, float]] = []
    rijen_kolomranden: list[list[float]] = []
    groep_sneden: list[Zaagsnede] = []

    while resterend:
        # Nieuwe rij starten; onderdelen met (bijna) gelijke hoogte
        # blijven bij voorkeur bij elkaar (zie _vul_rij hierboven), en
        # een te hoge groep slaat niet langer de hele rest van de
        # onderdelenlijst plat (zie _vind_plaatsbare_rij hierboven).
        rij, overig_na_rij, rij_hoogte, definitief_niet_plaatsbaar = _vind_plaatsbare_rij(
            resterend, x0, x1, cursor_y, y1, kerf
        )
        niet_geplaatst.extend(definitief_niet_plaatsbaar)
        if not rij:
            # Zelfs de laagste resterende hoogte-groep past niet meer -> stoppen.
            break

        nieuwe_plaatsingen, nieuwe_groep_sneden, kolom_randen, x, rij_vrij = _plaats_rij(
            rij, x0, cursor_y, kerf, rij_hoogte
        )
        plaatsingen.extend(nieuwe_plaatsingen)
        groep_sneden.extend(nieuwe_groep_sneden)
        vrije_rechten.extend(rij_vrij)
        rijen_kolomranden.append(kolom_randen)
        rij_grenzen.append((cursor_y, rij_hoogte))
        # Restruimte rechts in de rij (indien nog iets overblijft binnen de rijhoogte).
        if x < x1 - 1e-6:
            vrije_rechten.append((x - kerf if rij else x, cursor_y, x1 - x, rij_hoogte))

        volgende_y = cursor_y + rij_hoogte + kerf
        resterend = overig_na_rij
        cursor_y = volgende_y

    if cursor_y < y1 - 1e-6:
        vrije_rechten.append((x0, cursor_y, breedte_plaat, y1 - cursor_y))

    zaagvolgorde = _bouw_zaagvolgorde_uit_rijen(rij_grenzen, rijen_kolomranden, groep_sneden, x0, x1, y1)
    return plaatsingen, vrije_rechten, niet_geplaatst, zaagvolgorde


@dataclass
class _GespiegeldeEenheid(_Eenheid):
    """Een ``_Eenheid`` zoals ``_pak_kolommen`` 'm aan ``_pak_rijen``
    aanbiedt: x en y verwisseld. ``expand`` laat de echte eenheid de
    plaatsingen maken (op de echte plaat) en spiegelt die daarna weer
    naar het gespiegelde assenstelsel waarin ``_pak_rijen`` rekent —
    ``_pak_kolommen`` spiegelt ze aan het eind terug. Zo ligt een groep
    (doorlopende nerf) op de echte plaat precies zoals bij elke andere
    strategie, en niet mee-gespiegeld, terwijl ``_pak_rijen`` (o.a. voor
    de sneden tussen groepsleden) consequent in één assenstelsel blijft
    rekenen. Een eerdere versie gaf hier de ECHTE plaatsingen terug, en
    dan rekende ``_plaats_rij`` de groepssneden met echte coördinaten in
    het gespiegelde assenstelsel uit — Sven zag daardoor op de MDF-plaat
    van "Keuken Jansen" een rode zaaglijn dwars door een Deur lopen, waar
    eigenlijk de snede tussen Front 1 en Front 2 hoorde."""

    origineel: _Eenheid | None = None

    def expand(self, x: float, y: float, breedte: float, hoogte: float, geroteerd: bool) -> list[Plaatsing]:
        return [_spiegel_plaatsing(p) for p in self.origineel.expand(y, x, hoogte, breedte, geroteerd)]


def _spiegel_plaatsing(p: Plaatsing) -> Plaatsing:
    return replace(p, x=p.y, y=p.x, breedte=p.hoogte, hoogte=p.breedte)


_GESPIEGELDE_NERF = {
    Nerfrichting.LANGE_ZIJDE: Nerfrichting.KORTE_ZIJDE,
    Nerfrichting.KORTE_ZIJDE: Nerfrichting.LANGE_ZIJDE,
    Nerfrichting.GEEN: Nerfrichting.GEEN,
}


def _spiegel_eenheid(eenheid: _Eenheid) -> _GespiegeldeEenheid:
    # Breedte/hoogte verwisseld, en de nerf-eis ook: de plaatnerf loopt
    # langs de echte x-as, en die is in het gespiegelde assenstelsel de
    # y-as — "lange zijde langs de nerf" wordt daar dus "korte zijde langs
    # de (gespiegelde) x-as" (zie _kies_afmeting).
    if len(eenheid.leden) == 1:
        onderdeel, instantie = eenheid.leden[0]
        leden = [(
            replace(
                onderdeel,
                breedte=onderdeel.hoogte,
                hoogte=onderdeel.breedte,
                nerfrichting_vereist=_GESPIEGELDE_NERF[onderdeel.nerfrichting_vereist],
            ),
            instantie,
        )]
    else:
        leden = list(eenheid.leden)  # groep: roteert nooit, alleen het aantal leden telt hier
    return _GespiegeldeEenheid(
        unit_id=eenheid.unit_id,
        breedte=eenheid.hoogte,
        hoogte=eenheid.breedte,
        mag_roteren=eenheid.mag_roteren,
        fabriekskantenband_vereist=eenheid.fabriekskantenband_vereist,
        kantenband_randen=eenheid.kantenband_randen,
        leden=leden,
        _kerf=eenheid._kerf,
        origineel=eenheid,
    )


def _pak_kolommen(
    eenheden: list[_Eenheid],
    werkgebied: tuple[float, float, float, float],
    kerf: float,
    rng: random.Random | None = None,
) -> _PakResultaat:
    """Strategie "verticaal" (op Svens verzoek: "hetzelfde ... maar dan in
    plaats van de hoofdzaagsnedes horizontaal over de plaat verticaal over
    de plaat"): precies ``_pak_rijen``, maar op een gespiegelde plaat (x en
    y verwisseld) en daarna teruggespiegeld. Rijen worden zo kolommen over
    de volle plaathoogte, lange zijdes liggen langs de kolom, en de eerste
    zaagsnedes lopen verticaal. Door te spiegelen i.p.v. een tweede
    kopie van de hele rij-logica te schrijven blijven beide strategieën
    vanzelf gelijk lopen bij toekomstige verbeteringen/bugfixes."""

    x0, y0, x1, y1 = werkgebied
    plaatsingen, vrije_rechten, niet_geplaatst, sneden = _pak_rijen(
        [_spiegel_eenheid(e) for e in eenheden], (y0, x0, y1, x1), kerf, rng=rng
    )
    terug_plaatsingen = [_spiegel_plaatsing(p) for p in plaatsingen]
    terug_vrij = [(fy, fx, fh, fw) for (fx, fy, fw, fh) in vrije_rechten]
    terug_sneden = [
        replace(snede, richting="verticaal" if snede.richting == "horizontaal" else "horizontaal")
        for snede in sneden
    ]
    return terug_plaatsingen, terug_vrij, niet_geplaatst, terug_sneden


def _pak_guillotine(
    eenheden: list[_Eenheid],
    werkgebied: tuple[float, float, float, float],
    kerf: float,
    rng: random.Random | None = None,
) -> tuple[list[Plaatsing], list[tuple[float, float, float, float]], list[str], list[Zaagsnede]]:
    """Recursieve rand-tot-rand guillotine-plaatsing voor de strategie
    'Guillotine' — zie de module-docstring. Verwerkt een wachtrij van deelgebieden strikt
    FIFO: voor elk deelgebied wordt het eerste onderdeel uit de
    (grootste-eerst gesorteerde) resterende lijst geplaatst dat erin
    past, waarna het deelgebied in maximaal twee nieuwe deelgebieden
    wordt gesplitst (kortste-as-eerst, zie
    ``_splits_vrije_rechthoek``) — pas dan komt het volgende deelgebied aan de
    beurt. Bouwt de zaagvolgorde rechtstreeks op uit die opsplitsingen,
    zodat elke genoteerde snede een echte rand-tot-rand snede van het
    op dat moment behandelde deelgebied is."""

    x0, y0, x1, y1 = werkgebied
    resterend = sorted(eenheden, key=lambda e: _ruis_sleutel(e.breedte * e.hoogte, rng), reverse=True)

    plaatsingen: list[Plaatsing] = []
    vrije_rechten: list[tuple[float, float, float, float]] = []
    zaagvolgorde: list[Zaagsnede] = []
    wachtrij: list[tuple[float, float, float, float]] = [(x0, y0, x1 - x0, y1 - y0)]

    while wachtrij:
        fx, fy, fw, fh = wachtrij.pop(0)
        if not resterend:
            vrije_rechten.append((fx, fy, fw, fh))
            continue

        gekozen = None  # (index, b, h, geroteerd)
        for i, eenheid in enumerate(resterend):
            b, h, rot = _kies_afmeting(eenheid, None)
            if b <= fw + 1e-9 and h <= fh + 1e-9:
                gekozen = (i, b, h, rot)
                break
            if eenheid.mag_roteren and abs(b - h) > 1e-9 and h <= fw + 1e-9 and b <= fh + 1e-9:
                gekozen = (i, h, b, not rot)
                break

        if gekozen is None:
            # Niets uit de resterende lijst past in dit deelgebied — het
            # blijft over als vrije ruimte (of afval, als het te klein is).
            vrije_rechten.append((fx, fy, fw, fh))
            continue

        i, b, h, rot = gekozen
        eenheid = resterend.pop(i)
        nieuwe = eenheid.expand(fx, fy, b, h, rot)
        plaatsingen.extend(nieuwe)

        # Toetsen aan de rand
        # van DIT vrije rechthoek (fw/fh), niet aan de rand van de hele
        # plaat, en aftoppen zodat een marge kleiner dan de kerf geen
        # negatief-brede (buiten de plaat stekende) nieuwe vrije
        # rechthoek kan opleveren.
        kerf_r = kerf if b < fw - 1e-9 else 0.0
        kerf_o = kerf if h < fh - 1e-9 else 0.0
        genomen_b = min(b + kerf_r, fw)
        genomen_h = min(h + kerf_o, fh)

        nieuwe_rechten, sneden = _splits_vrije_rechthoek(
            fx, fy, fw, fh, genomen_b, genomen_h, len(zaagvolgorde) + 1, b, h
        )
        zaagvolgorde.extend(sneden)
        for snede in _groepssneden(nieuwe):
            zaagvolgorde.append(replace(snede, volgnummer=len(zaagvolgorde) + 1))
        wachtrij.extend(nieuwe_rechten)

    niet_geplaatst = [e.unit_id for e in resterend]
    return plaatsingen, vrije_rechten, niet_geplaatst, _zet_sneden_op_deelgebieden(zaagvolgorde, *werkgebied)


def _plaats_fabriek_rand(
    eenheden: list[_Eenheid], rand: Rand, x0: float, y0: float, x1: float, y1: float, kerf: float
) -> tuple[list[Plaatsing], list[str], float, float, float, float]:
    """Plaatst ``eenheden`` (die alle een fabriekskantenband op ``rand``
    nodig hebben) in ÉÉN rechte lijn tegen die rand — elk stuk raakt de
    rand dus altijd echt (dat is het hele punt van een fabriekskanten-
    band: die zit fysiek op precies één rand van de plaat). Onderdelen
    die niet meer binnen de resterende lengte langs die rand passen (of
    individueel al te diep zijn voor het beschikbare werkgebied) komen
    terecht in ``niet_geplaatst`` en schuiven — net als elk ander
    niet-geplaatst onderdeel — door naar een volgende, verse plaat (die
    weer een volledig lege rand ter beschikking heeft), zie
    ``genereer_zaagplannen``.

    Bugfix-geschiedenis: een eerdere versie stapelde alles blindelings
    in één kolom/rij zonder grenscontrole, en plaatste zo onderdelen ver
    buiten de plaat. De daaropvolgende fix liet een volle rand
    "wraparound" naar een tweede kolom/rij verder de plaat in om dat te
    voorkomen — maar die tweede kolom/rij raakt de vereiste rand niet
    meer, wat de fabriekskantenband-eis zelf stilletjes schond (Svens
    melding: "hij houdt nu geen rekening met fabriekskantenband in
    rijen"). Deze versie doet dus bewust GEEN wraparound meer: gewoon
    één lijn, en alles wat daar niet meer bij past is echt
    niet-geplaatst op déze plaat.

    Rotatie-regel (Sven, eerder gemeld: een dwarsbalk werd zo geroteerd
    dat zijn KORTE zijde de kantenband raakte, terwijl zijn eigen
    ``kantenband_randen`` juist de lange zijde aanwijst): een onderdeel
    met een specifieke ``kantenband_randen``-eis draait hier alleen naar
    een stand waarin precies die zijde tegen ``rand`` ligt — zie
    ``_fabriek_orientaties``. Past het in geen van die standen, dan is
    het niet-geplaatst op déze plaat i.p.v. verkeerd-om neergezet. Een
    onderdeel ZONDER specifieke ``kantenband_randen`` (alleen het kale
    ``fabriekskantenband_vereist=True``) mag nog gewoon roteren als dat
    nodig is om te passen.

    Retourneert (plaatsingen, niet_geplaatst, nieuw_x0, nieuw_y0, nieuw_x1,
    nieuw_y1, strook_vrij, strook_sneden) — het bijgewerkte werkgebied ná
    aftrek van de daadwerkelijk ingenomen rand-strook (ongewijzigd als er
    niets geplaatst kon worden), plus de lege ruimte binnen de strook en
    de sneden daarbinnen (zie ``_strook_restruimte``)."""

    langs_verticaal = rand in (Rand.LINKS, Rand.RECHTS)
    langs_lengte = (y1 - y0) if langs_verticaal else (x1 - x0)
    beschikbare_diepte = (x1 - x0) if langs_verticaal else (y1 - y0)

    plaatsingen: list[Plaatsing] = []
    niet_geplaatst: list[str] = []
    geplaatst_langs: list[tuple[float, float, float]] = []  # per stuk: (start langs, lengte langs, diepte)
    groeps_sneden: list[Zaagsnede] = []
    langs_cursor = 0.0  # positie langs de rand, al ingenomen door eerder geplaatste stukken
    strook_diepte = 0.0  # diepte (loodrecht op de rand) van de strook, bepaald door het diepste geplaatste stuk

    for eenheid in eenheden:
        # De standen waarin dit stuk tegen déze rand mag (zie
        # _fabriek_orientaties), in volgorde van voorkeur; de eerste die
        # nog past wint.
        gekozen = None
        for verwisseld in _fabriek_orientaties(eenheid, rand):
            b, h = (eenheid.hoogte, eenheid.breedte) if verwisseld else (eenheid.breedte, eenheid.hoogte)
            diepte, lengte_langs = (b, h) if langs_verticaal else (h, b)
            if diepte <= beschikbare_diepte + 1e-9 and langs_cursor + lengte_langs <= langs_lengte + 1e-9:
                gekozen = (b, h, verwisseld, diepte, lengte_langs)
                break
        if gekozen is None:
            niet_geplaatst.append(eenheid.unit_id)
            continue
        b, h, rot, diepte, lengte_langs = gekozen

        if langs_verticaal:
            px, py = x0, y0 + langs_cursor
        else:
            px, py = x0 + langs_cursor, y0
        if rand == Rand.RECHTS:
            px = x1 - diepte
        elif rand == Rand.BOVEN:
            py = y1 - diepte

        nieuwe = eenheid.expand(px, py, b, h, rot)
        plaatsingen.extend(nieuwe)
        groeps_sneden.extend(_groepssneden(nieuwe))
        geplaatst_langs.append((langs_cursor, lengte_langs, diepte))
        strook_diepte = max(strook_diepte, diepte)
        langs_cursor += lengte_langs + kerf

    if strook_diepte <= 0:
        return plaatsingen, niet_geplaatst, x0, y0, x1, y1, [], []

    vrije_rechten, sneden = _strook_restruimte(
        rand, geplaatst_langs, strook_diepte, langs_cursor, langs_lengte, x0, y0, x1, y1, kerf
    )
    sneden = sneden + groeps_sneden
    if rand == Rand.LINKS:
        return plaatsingen, niet_geplaatst, x0 + strook_diepte + kerf, y0, x1, y1, vrije_rechten, sneden
    if rand == Rand.RECHTS:
        return plaatsingen, niet_geplaatst, x0, y0, x1 - strook_diepte - kerf, y1, vrije_rechten, sneden
    if rand == Rand.ONDER:
        return plaatsingen, niet_geplaatst, x0, y0 + strook_diepte + kerf, x1, y1, vrije_rechten, sneden
    return plaatsingen, niet_geplaatst, x0, y0, x1, y1 - strook_diepte - kerf, vrije_rechten, sneden  # BOVEN


def _strook_restruimte(
    rand: Rand,
    geplaatst_langs: list[tuple[float, float, float]],
    strook_diepte: float,
    langs_eind: float,
    langs_lengte: float,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    kerf: float,
) -> tuple[list[tuple[float, float, float, float]], list[Zaagsnede]]:
    """De lege ruimte BINNEN een fabrieksband-strook als vrije
    rechthoeken (voor ``_classificeer_restruimte``: reststuk of afval),
    plus de sneden die de stukken in die strook van elkaar en van die
    ruimte scheiden.

    Een strook neemt de volle lengte langs de rand in, ter diepte van zijn
    diepste stuk — ook als hij maar deels gevuld is. Sven accepteert dat
    als eigenschap van deze aanpak ("dat is iets wat helaas kan gebeuren
    met deze strategie"), maar: "de rest moet gewoon als reststuk bewaard
    worden". Tot nu toe telde die ruimte nergens mee (geen reststuk, geen
    afval) en zaagde ook geen enkele snede 'm af — bv. een onderstrook met
    alleen een Bodem 564×540 en een Dwarsbalk 564×100 op een plaat van
    2800×600 liet ~1666×540 volledig onvermeld.

    Twee soorten ruimte: achter het laatste stuk (volle strookdiepte tot
    het einde van de rand) en boven een stuk dat ondieper is dan de
    strook. ``geplaatst_langs`` is per stuk (start langs de rand, lengte
    langs de rand, diepte); ``langs_eind`` is waar het volgende stuk zou
    beginnen (dus inclusief de kerf na het laatste stuk)."""

    langs_verticaal = rand in (Rand.LINKS, Rand.RECHTS)

    def rechthoek(langs_a: float, langs_b: float, diepte_a: float, diepte_b: float) -> tuple[float, float, float, float]:
        # (langs, diepte)-bereik binnen de strook -> (x, y, breedte, hoogte) op de plaat.
        if rand == Rand.ONDER:
            return (x0 + langs_a, y0 + diepte_a, langs_b - langs_a, diepte_b - diepte_a)
        if rand == Rand.BOVEN:
            return (x0 + langs_a, y1 - diepte_b, langs_b - langs_a, diepte_b - diepte_a)
        if rand == Rand.LINKS:
            return (x0 + diepte_a, y0 + langs_a, diepte_b - diepte_a, langs_b - langs_a)
        return (x1 - diepte_b, y0 + langs_a, diepte_b - diepte_a, langs_b - langs_a)  # RECHTS

    def dwars(langs: float) -> Zaagsnede:
        # Snede loodrecht op de rand, over de volle strookdiepte.
        x, y, b, h = rechthoek(langs, langs, 0.0, strook_diepte)
        if langs_verticaal:
            return Zaagsnede(0, "horizontaal", round(y, 6), x, x + b)
        return Zaagsnede(0, "verticaal", round(x, 6), y, y + h)

    def evenwijdig(diepte: float, langs_a: float, langs_b: float) -> Zaagsnede:
        # Snede evenwijdig aan de rand, op ``diepte``, alleen over dit ene stuk.
        x, y, b, h = rechthoek(langs_a, langs_b, diepte, diepte)
        if langs_verticaal:
            return Zaagsnede(0, "verticaal", round(x, 6), y, y + h)
        return Zaagsnede(0, "horizontaal", round(y, 6), x, x + b)

    vrije_rechten: list[tuple[float, float, float, float]] = []
    sneden: list[Zaagsnede] = []
    heeft_eindstuk = langs_lengte - langs_eind > 1e-6

    for i, (start, lengte, diepte) in enumerate(geplaatst_langs):
        # Na het laatste stuk ook een snede als er maar een reepje smaller
        # dan de kerf tot het einde van de rand overblijft.
        if i < len(geplaatst_langs) - 1 or langs_lengte - (start + lengte) > 1e-6:
            sneden.append(dwars(start + lengte))
        if strook_diepte - diepte > 1e-6:
            # Ook bij een reepje smaller dan de kerf moet het stuk hier nog
            # op maat gezaagd worden; alleen een breder reepje levert ook
            # restruimte op.
            sneden.append(evenwijdig(diepte, start, start + lengte))
            if strook_diepte - diepte > kerf + 1e-6:
                vrije_rechten.append(rechthoek(start, start + lengte, diepte + kerf, strook_diepte))

    if heeft_eindstuk:
        vrije_rechten.append(rechthoek(langs_eind, langs_lengte, 0.0, strook_diepte))

    return vrije_rechten, sneden


_PakResultaat = tuple[list[Plaatsing], list[tuple[float, float, float, float]], list[str], list[Zaagsnede]]


# ----------------------------------------------------------------------
# CNC-nesting ("cnc")
# ----------------------------------------------------------------------
#
# Op Svens verzoek is "cnc" een strategie voor een CNC-freesmachine (niet
# kiesbaar in de app; bewaard voor een latere CNC-upgrade):
# "deze strategie moet eigenlijk kijken wat het minste afval laat liggen
# maakt niet uit hoe het gezaagd word". Er is dus geen paneelzaag-
# beperking (geen rand-tot-rand sneden) en geen zaagvolgorde: onderdelen
# mogen vrij in elkaar geschoven worden, met alleen de freesdiameter
# (``materiaal.kerf``, gevuld uit de instellingen) als tussenruimte.
#
# Doel (Svens keuze): eerst zo min mogelijk platen — per plaat zoveel
# mogelijk onderdeel-oppervlak — en daarna zo min mogelijk afval, d.w.z.
# een zo groot mogelijk bruikbaar reststuk.
#
# Aanpak: MaxRects (een lijst van maximale vrije rechthoeken, die elkaar
# mogen overlappen), met meerdere plaatsingsregels en verwerkingsvolgordes;
# de beste uitkomst wint (zie ``_nesting_score``). De tussenruimte zit in
# het pakken zelf: elk onderdeel neemt rechts en boven een freesdiameter
# extra in, in een werkgebied dat aan die kanten ook een freesdiameter
# groter is — zo liggen twee onderdelen precies een freesdiameter uit
# elkaar en mag een onderdeel wel direct tegen de plaatrand.

_Rechthoek = tuple[float, float, float, float]  # (x, y, breedte, hoogte)

_NESTING_REGELS = ("onder_links", "links_onder", "korte_zijde", "oppervlak", "contact")


def _snijden(a: _Rechthoek, b: _Rechthoek) -> bool:
    return a[0] < b[0] + b[2] - 1e-9 and b[0] < a[0] + a[2] - 1e-9 and a[1] < b[1] + b[3] - 1e-9 and b[1] < a[1] + a[3] - 1e-9


def _bevat(a: _Rechthoek, b: _Rechthoek) -> bool:
    """Ligt ``b`` helemaal binnen ``a``?"""
    return (
        b[0] >= a[0] - 1e-9
        and b[1] >= a[1] - 1e-9
        and b[0] + b[2] <= a[0] + a[2] + 1e-9
        and b[1] + b[3] <= a[1] + a[3] + 1e-9
    )


def _trek_af(vrije: list[_Rechthoek], bezet: _Rechthoek) -> list[_Rechthoek]:
    """MaxRects: haalt ``bezet`` uit elke vrije rechthoek die hij raakt
    (tot vier nieuwe, maximale stukken per rechthoek) en ruimt daarna
    rechthoeken op die helemaal binnen een andere liggen."""

    bx, by, bw, bh = bezet
    nieuw: list[_Rechthoek] = []
    for vrij in vrije:
        if not _snijden(vrij, bezet):
            nieuw.append(vrij)
            continue
        fx, fy, fw, fh = vrij
        if bx > fx + 1e-9:
            nieuw.append((fx, fy, bx - fx, fh))
        if bx + bw < fx + fw - 1e-9:
            nieuw.append((bx + bw, fy, fx + fw - (bx + bw), fh))
        if by > fy + 1e-9:
            nieuw.append((fx, fy, fw, by - fy))
        if by + bh < fy + fh - 1e-9:
            nieuw.append((fx, by + bh, fw, fy + fh - (by + bh)))
    nieuw = [r for r in nieuw if r[2] > 1e-6 and r[3] > 1e-6]
    opgeschoond: list[_Rechthoek] = []
    for i, r in enumerate(nieuw):
        if any(j != i and _bevat(s, r) and (s != r or j < i) for j, s in enumerate(nieuw)):
            continue
        opgeschoond.append(r)
    return opgeschoond


def _contact(x: float, y: float, b: float, h: float, bak_b: float, bak_h: float, bezet: list[_Rechthoek]) -> float:
    """Lengte van de randen van (x, y, b, h) die tegen de bak-rand of een
    al geplaatst stuk liggen — de "contact point"-regel van MaxRects."""

    def overlap(a0: float, a1: float, b0: float, b1: float) -> float:
        return max(0.0, min(a1, b1) - max(a0, b0))

    totaal = 0.0
    if x <= 1e-9 or x + b >= bak_b - 1e-9:
        totaal += h
    if y <= 1e-9 or y + h >= bak_h - 1e-9:
        totaal += b
    for (px, py, pb, ph) in bezet:
        if abs(px + pb - x) <= 1e-9 or abs(x + b - px) <= 1e-9:
            totaal += overlap(y, y + h, py, py + ph)
        if abs(py + ph - y) <= 1e-9 or abs(y + h - py) <= 1e-9:
            totaal += overlap(x, x + b, px, px + pb)
    return totaal


def _nesting_volgorde(eenheden: list[_Eenheid], sortering: str, rng: random.Random | None) -> list[_Eenheid]:
    sleutels = {
        "oppervlak": lambda e: e.breedte * e.hoogte,
        "lange_zijde": lambda e: max(e.breedte, e.hoogte),
        "hoogte": lambda e: e.hoogte,
        "breedte": lambda e: e.breedte,
        "omtrek": lambda e: e.breedte + e.hoogte,
    }
    sleutel = sleutels[sortering]
    return sorted(eenheden, key=lambda e: _ruis_sleutel(sleutel(e), rng), reverse=True)


_NESTING_SORTERINGEN = ("oppervlak", "lange_zijde", "hoogte", "breedte", "omtrek")


@dataclass
class _NestResultaat:
    plaatsingen: list[Plaatsing]
    niet_geplaatst: list[str]
    reststukken: list[Reststuk]
    geplaatst_oppervlak: float
    afval: float  # werkgebied − onderdelen − reststukken


def _nesting_reststukken(
    plaatsingen: list[Plaatsing], werkgebied: tuple[float, float, float, float], kerf: float, min_grootte: float
) -> list[Reststuk]:
    """Zo groot mogelijke bruikbare reststukken uit de lege ruimte, steeds
    het grootste eerst. Een reststuk blijft (net als een onderdeel) een
    freesdiameter van elk onderdeel en van elk ander reststuk af — de frees
    moet er ook omheen kunnen."""

    x0, y0, x1, y1 = werkgebied
    vrije: list[_Rechthoek] = [(x0, y0, x1 - x0, y1 - y0)]
    for p in plaatsingen:
        vrije = _trek_af(vrije, (p.x - kerf, p.y - kerf, p.breedte + 2 * kerf, p.hoogte + 2 * kerf))
    reststukken: list[Reststuk] = []
    while True:
        bruikbaar = [r for r in vrije if r[2] >= min_grootte - 1e-9 and r[3] >= min_grootte - 1e-9]
        if not bruikbaar:
            return reststukken
        x, y, b, h = max(bruikbaar, key=lambda r: (r[2] * r[3], -r[1], -r[0]))
        reststukken.append(Reststuk(x, y, b, h))
        vrije = _trek_af(vrije, (x - kerf, y - kerf, b + 2 * kerf, h + 2 * kerf))


def _pak_nesting(
    eenheden: list[_Eenheid],
    werkgebied: tuple[float, float, float, float],
    kerf: float,
    min_reststukgrootte: float,
    regel: str,
    sortering: str,
    rng: random.Random | None = None,
) -> _NestResultaat:
    x0, y0, x1, y1 = werkgebied
    bak_b = x1 - x0 + kerf
    bak_h = y1 - y0 + kerf
    vrije: list[_Rechthoek] = [(0.0, 0.0, bak_b, bak_h)]
    bezet: list[_Rechthoek] = []
    plaatsingen: list[Plaatsing] = []
    niet_geplaatst: list[str] = []
    oppervlak = 0.0

    for eenheid in _nesting_volgorde(eenheden, sortering, rng):
        breedte, hoogte, geroteerd = _kies_afmeting(eenheid, None)
        standen = [(breedte, hoogte, geroteerd)]
        if eenheid.mag_roteren and abs(breedte - hoogte) > 1e-9:
            standen.append((hoogte, breedte, not geroteerd))

        beste = None  # (score, x, y, b, h, geroteerd)
        for (fx, fy, fw, fh) in vrije:
            for (b, h, rot) in standen:
                gb, gh = b + kerf, h + kerf
                if gb > fw + 1e-9 or gh > fh + 1e-9:
                    continue
                if regel == "onder_links":
                    score = (fy + gh, fx)
                elif regel == "links_onder":
                    score = (fx + gb, fy)
                elif regel == "korte_zijde":
                    rest_b, rest_h = fw - gb, fh - gh
                    score = (min(rest_b, rest_h), max(rest_b, rest_h))
                elif regel == "oppervlak":
                    score = (fw * fh - gb * gh, min(fw - gb, fh - gh))
                else:  # "contact"
                    score = (-_contact(fx, fy, gb, gh, bak_b, bak_h, bezet), fy, fx)
                if beste is None or score < beste[0]:
                    beste = (score, fx, fy, b, h, rot)

        if beste is None:
            niet_geplaatst.append(eenheid.unit_id)
            continue
        _, bx, by, b, h, rot = beste
        plaatsingen.extend(eenheid.expand(x0 + bx, y0 + by, b, h, rot))
        oppervlak += b * h
        stuk = (bx, by, b + kerf, h + kerf)
        bezet.append(stuk)
        vrije = _trek_af(vrije, stuk)

    reststukken = _nesting_reststukken(plaatsingen, werkgebied, kerf, min_reststukgrootte)
    onderdelen_opp = sum(p.breedte * p.hoogte for p in plaatsingen)
    afval = (x1 - x0) * (y1 - y0) - onderdelen_opp - sum(r.oppervlak for r in reststukken)
    return _NestResultaat(plaatsingen, niet_geplaatst, reststukken, oppervlak, max(0.0, afval))


def _nesting_score(resultaat: _NestResultaat) -> tuple[float, float, float]:
    """Lager is beter: eerst zoveel mogelijk onderdeel-oppervlak op deze
    plaat (minder platen in totaal), dan het minste afval (dus het meeste
    reststuk), dan het grootste losse reststuk."""

    grootste = max((r.oppervlak for r in resultaat.reststukken), default=0.0)
    return (-round(resultaat.geplaatst_oppervlak, 3), round(resultaat.afval, 3), -round(grootste, 3))


def _nesting_kandidaten(
    eenheden: list[_Eenheid],
    werkgebied: tuple[float, float, float, float],
    kerf: float,
    min_reststukgrootte: float,
    rng: random.Random | None,
) -> list[_NestResultaat]:
    """Zonder ``rng``: elke plaatsingsregel met elke vaste sortering. Met
    ``rng`` (de zoektocht van ``genereer_zaagplan``): één willekeurige regel
    met een willekeurig verstoorde volgorde."""

    if rng is None:
        return [
            _pak_nesting(eenheden, werkgebied, kerf, min_reststukgrootte, regel, sortering)
            for regel in _NESTING_REGELS
            for sortering in _NESTING_SORTERINGEN
        ]
    return [
        _pak_nesting(
            eenheden, werkgebied, kerf, min_reststukgrootte,
            rng.choice(_NESTING_REGELS), rng.choice(_NESTING_SORTERINGEN), rng,
        )
    ]


def _kies_beste_pakresultaat(kandidaten: list[_PakResultaat], materiaal: Materiaal) -> _PakResultaat:
    """Kiest, uit meerdere ``(plaatsingen, vrije_rechten, niet_geplaatst,
    zaagvolgorde)``-uitkomsten voor hetzelfde werkgebied/dezelfde
    eenheden, de beste: de minste niet-geplaatste onderdelen, en bij een
    gelijke stand het minste afval (zie ``_classificeer_restruimte``)."""

    def score(kandidaat: _PakResultaat) -> tuple[int, float]:
        _, vrije, niet_geplaatst, _ = kandidaat
        _, afval = _classificeer_restruimte(vrije, materiaal)
        return (len(niet_geplaatst), afval)

    return min(kandidaten, key=score)


_GELDIGE_STRATEGIEEN = ("horizontaal", "verticaal", "guillotine", "cnc")


_MAX_POGINGEN_ZONDER_VERBETERING = 300  # zie genereer_zaagplan's zoek_tijdsbudget
_VOORTGANG_INTERVAL = 0.1  # seconden tussen twee voortgangsmeldingen, zie genereer_zaagplan
_AANDEEL_MINIMALE_DENKTIJD = 0.9  # zie _zoek_fractie


def _zoek_fractie(verstreken: float, min_duur: float, max_duur: float, pogingen_zonder_verbetering: int) -> float:
    """Schatting (0.0-1.0) van hoe ver de zoektocht van één plaat is.

    De zoektocht duurt altijd minstens ``min_duur`` (de minimale
    denktijd) en daarna nog tot ``_MAX_POGINGEN_ZONDER_VERBETERING``
    pogingen op rij niets beters opleveren, of uiterlijk tot
    ``max_duur``. In de praktijk stopt hij meestal vrijwel meteen na de
    minimale denktijd, dus die krijgt het grootste deel van de balk
    (``_AANDEEL_MINIMALE_DENKTIJD``); het restant loopt op met wat het
    eerst bereikt wordt — het pogingen-plafond of het tijdsplafond.
    Kan tussendoor iets dalen (een verbetering zet de teller terug) —
    de aanroeper houdt daarom het hoogste gemelde getal aan."""

    if min_duur > 0 and verstreken < min_duur:
        return _AANDEEL_MINIMALE_DENKTIJD * verstreken / min_duur
    basis = _AANDEEL_MINIMALE_DENKTIJD if min_duur > 0 else 0.0
    rest_tijd = max_duur - min_duur
    tijd_fractie = (verstreken - min_duur) / rest_tijd if rest_tijd > 0 else 1.0
    pogingen_fractie = pogingen_zonder_verbetering / _MAX_POGINGEN_ZONDER_VERBETERING
    return min(1.0, basis + (1.0 - basis) * max(tijd_fractie, pogingen_fractie))


def genereer_zaagplan(
    materiaal: Materiaal,
    onderdelen: list[Onderdeel],
    strategie: str = "horizontaal",
    zoek_tijdsbudget: float = 0.0,
    min_zoek_tijdsbudget: float = 0.0,
    voortgang: Callable[[float], None] | None = None,
) -> ZaagplanResultaat:
    """Genereer een zaagplan voor één plaat van ``materiaal`` met de
    gegeven ``onderdelen``.

    :param strategie: "horizontaal" (lange zijdes eerst in rijen,
        rijhoogte per rij aangepast), "verticaal" (idem in kolommen),
        "guillotine" (uitsluitend rand-tot-rand sneden) of "cnc"
        (CNC-nesting zonder zaagvolgorde; niet kiesbaar in de app, zie de
        module-docstring) — zie de module-docstring voor de precieze
        verschillen.
    :param zoek_tijdsbudget: aantal seconden dat de motor, bovenop de
        standaard (deterministische) plaatsing, extra verwerkings-
        volgordes van dezelfde onderdelen mag proberen om een betere
        uitkomst te vinden (minder niet-geplaatste onderdelen, of bij
        een gelijke stand minder afval) — zie ``_ruis_sleutel``. ``0``
        (standaard) slaat deze extra zoektocht over en levert precies
        de oude, deterministische uitkomst op, ongewijzigd t.o.v. vóór
        deze parameter bestond. Op Svens verzoek ("dat je dan even moet
        wachten op het resultaat zodat ie goed kijkt waar alle items
        kunnen") geldt dit voor alle strategieën (horizontaal/
        verticaal/guillotine/cnc) — elke strategie blijft zijn eigen aanpak
        gebruiken, maar probeert die met meerdere verwerkingsvolgordes.
        Een nieuwe poging vervangt de tot dan toe beste uitkomst alleen
        bij een STRIKTE verbetering (nooit bij gelijke stand — zo blijft
        de uitkomst bij een klein/eenvoudig zaagplan waar geen betere
        volgorde bestaat identiek aan zonder zoekbudget). Stopt vanzelf
        eerder dan het budget als ``_MAX_POGINGEN_ZONDER_VERBETERING``
        pogingen op rij niets beters meer opleveren — geen zin om door
        te zoeken op een zaagplan dat al (vrijwel) optimaal is.
        ``math.inf`` mag ook: dan is er geen tijdsplafond en stopt de
        zoektocht alléén op die stagnatie (na ``min_zoek_tijdsbudget``).
    :param min_zoek_tijdsbudget: minimum aantal seconden dat de zoektocht
        altijd doorgaat, ook als ``_MAX_POGINGEN_ZONDER_VERBETERING`` al
        eerder gehaald is — op Svens verzoek ("een minimale denktijd van
        10 seconden ofzo"), zodat een eenvoudig zaagplan niet meteen
        (schijnbaar zonder iets te proberen) teruggegeven wordt en de
        UI's laad-animatie ook echt iets te doen heeft. Heeft geen effect
        als ``zoek_tijdsbudget`` zelf 0 is (dan is zoeken al uitgeschakeld)
        en wordt nooit hoger dan ``zoek_tijdsbudget`` zelf toegepast.
    :param voortgang: optionele callback die tijdens de zoektocht
        (hoogstens elke ``_VOORTGANG_INTERVAL`` seconden) een schatting
        krijgt van hoe ver deze plaat is, als fractie 0.0-1.0 (nooit
        dalend), en aan het eind altijd precies 1.0 — voor de
        voortgangsbalk in de UI (op Svens verzoek: "zodat de gebruiker
        kan zien hoelang het ongeveer gaat duren en hoe ver hij is").
        Zie ``_zoek_fractie`` voor hoe die schatting tot stand komt."""

    if strategie not in _GELDIGE_STRATEGIEEN:
        raise ValueError(
            f"Onbekende strategie: {strategie!r} (verwacht een van: {', '.join(_GELDIGE_STRATEGIEEN)})"
        )

    kerf = materiaal.kerf
    eenheden, waarschuwingen = _bouw_eenheden(onderdelen, kerf)
    werkgebied = _werkgebied(materiaal)

    # Onderdelen die een fabriekskantenband nodig hebben eerst tegen de
    # betreffende rand(en) plaatsen; de rest van het werkgebied gaat
    # door naar de gekozen strategie. Als de plaat op meerdere randen
    # fabriekskantenband heeft (bv. onder én boven), proberen we ze in
    # volgorde van ``_RANDVOLGORDE`` allemaal: wat niet meer in de
    # eerste strook past, schuift door naar de volgende beschikbare
    # rand-strook, vóór het pas echt niet-geplaatst raakt (op Svens
    # verzoek — voorheen werd altijd maar één rand gebruikt, ook als de
    # plaat er meerdere had).
    fabriek_eenheden = [e for e in eenheden if e.fabriekskantenband_vereist]
    overige_eenheden = [e for e in eenheden if not e.fabriekskantenband_vereist]

    x0, y0, x1, y1 = werkgebied
    beschikbare_randen = [r for r in _RANDVOLGORDE if r in materiaal.fabriekskantenband_randen]

    plaatsingen: list[Plaatsing] = []
    niet_geplaatst: list[str] = []
    fabriek_snedes: list[Zaagsnede] = []
    fabriek_vrij: list[tuple[float, float, float, float]] = []  # lege ruimte binnen de stroken, zie _strook_restruimte

    if fabriek_eenheden and beschikbare_randen:
        # Een onderdeel met een specifieke kantenband_randen-eis mag hier
        # alleen in een stand (eventueel een halve of kwartslag gedraaid)
        # waarin een van zijn eigen kantenband-randen echt tegen een
        # fabriekskantenband-rand van de plaat ligt — zie
        # _fabriek_orientaties. Kan dat op geen enkele rand van deze
        # plaat (bv. een nerf-eis die precies de verkeerde stand
        # afdwingt), dan kan de fabrieksband-route 'm niet correct helpen
        # en telt het gewoon als een doodgewoon onderdeel mee.
        def _mag_edge_matchen(e: _Eenheid) -> bool:
            return any(_fabriek_orientaties(e, rand) for rand in beschikbare_randen)

        resterend_fabriek = [e for e in fabriek_eenheden if _mag_edge_matchen(e)]
        overige_eenheden.extend(e for e in fabriek_eenheden if not _mag_edge_matchen(e))

        for rand in beschikbare_randen:
            if not resterend_fabriek:
                break
            kandidaten = [e for e in resterend_fabriek if _fabriek_orientaties(e, rand)]
            if not kandidaten:
                continue
            (
                nieuwe_plaatsingen, fabriek_niet_geplaatst, nieuw_x0, nieuw_y0, nieuw_x1, nieuw_y1,
                strook_vrij, strook_sneden,
            ) = _plaats_fabriek_rand(
                kandidaten, rand, x0, y0, x1, y1, kerf
            )
            plaatsingen.extend(nieuwe_plaatsingen)

            # De snede die deze fabriekskantenband-strook van de rest
            # scheidt (rand-tot-rand van het werkgebied zoals het vóór
            # déze strook was) — alleen als er ook daadwerkelijk een
            # strook is overgebleven (kan leeg zijn als geen van de
            # kandidaten er nog in paste). Genoteerd op de rand van de strook
            # zelf (dus vóór de kerf, gezien vanuit de strook), net als de
            # kolomranden bij rijen — eerder stond hij na de kerf, en dan
            # vielen de sneden van twee precies aansluitende stroken (bv.
            # onder én boven op een smalle plaat) op dezelfde coördinaat,
            # waardoor er één wegviel en een stuk een kerf te groot bleef
            # (gevonden bij het nalopen van Guillotine met een eigen
            # paneelzaag-simulatie).
            if rand == Rand.LINKS and nieuw_x0 != x0:
                fabriek_snedes.append(Zaagsnede(0, "verticaal", nieuw_x0 - kerf, y0, y1))
            elif rand == Rand.RECHTS and nieuw_x1 != x1:
                fabriek_snedes.append(Zaagsnede(0, "verticaal", nieuw_x1 + kerf, y0, y1))
            elif rand == Rand.ONDER and nieuw_y0 != y0:
                fabriek_snedes.append(Zaagsnede(0, "horizontaal", nieuw_y0 - kerf, x0, x1))
            elif rand == Rand.BOVEN and nieuw_y1 != y1:
                fabriek_snedes.append(Zaagsnede(0, "horizontaal", nieuw_y1 + kerf, x0, x1))
            # Daarna pas de sneden binnen de (nu losgezaagde) strook zelf.
            fabriek_snedes.extend(strook_sneden)
            fabriek_vrij.extend(strook_vrij)
            x0, y0, x1, y1 = nieuw_x0, nieuw_y0, nieuw_x1, nieuw_y1

            # Alleen de kandidaten die ook echt geplaatst zijn uit de
            # resterende pool halen — een kandidaat die hier niet paste
            # blijft over voor een volgende, ook door hem toegestane rand
            # (bv. een onderdeel met kantenband_randen={onder, boven} dat
            # de onder-strook net niet meer in past, krijgt zo alsnog een
            # kans in de boven-strook).
            niet_geplaatst_ids = set(fabriek_niet_geplaatst)
            geplaatste_ids = {e.unit_id for e in kandidaten} - niet_geplaatst_ids
            resterend_fabriek = [e for e in resterend_fabriek if e.unit_id not in geplaatste_ids]

        niet_geplaatst.extend(e.unit_id for e in resterend_fabriek)
        werkgebied = (x0, y0, x1, y1)
    else:
        overige_eenheden = eenheden

    if strategie == "cnc":
        # CNC-nesting: eigen pak-functie en eigen score, zie _pak_nesting.
        def _kandidaten_voor(rng: random.Random | None) -> list:
            return _nesting_kandidaten(overige_eenheden, werkgebied, kerf, materiaal.min_reststukgrootte, rng)

        def _kies(kandidaten: list):
            return min(kandidaten, key=_nesting_score)
    else:
        def _kandidaten_voor(rng: random.Random | None) -> list:
            if strategie == "horizontaal":
                return [_pak_rijen(overige_eenheden, werkgebied, kerf, rng=rng)]
            if strategie == "verticaal":
                return [_pak_kolommen(overige_eenheden, werkgebied, kerf, rng=rng)]
            return [_pak_guillotine(overige_eenheden, werkgebied, kerf, rng=rng)]  # "guillotine"

        def _kies(kandidaten: list):
            return _kies_beste_pakresultaat(kandidaten, materiaal)

    # min() houdt bij een gelijke stand de eerste: een poging vervangt de
    # beste tot nu toe dus alleen bij een strikte verbetering.
    beste = _kies(_kandidaten_voor(None))

    if zoek_tijdsbudget > 0 and overige_eenheden:
        start = time.monotonic()
        deadline = start + zoek_tijdsbudget
        min_deadline = start + min(min_zoek_tijdsbudget, zoek_tijdsbudget)
        pogingen_zonder_verbetering = 0
        iteratie = 0
        hoogste_fractie = 0.0
        laatste_melding = start
        while time.monotonic() < deadline and (
            time.monotonic() < min_deadline
            or pogingen_zonder_verbetering < _MAX_POGINGEN_ZONDER_VERBETERING
        ):
            if voortgang is not None:
                nu = time.monotonic()
                if nu - laatste_melding >= _VOORTGANG_INTERVAL:
                    laatste_melding = nu
                    hoogste_fractie = max(
                        hoogste_fractie,
                        _zoek_fractie(nu - start, min_deadline - start, deadline - start, pogingen_zonder_verbetering),
                    )
                    voortgang(hoogste_fractie)
            iteratie += 1
            variant = _kies(_kandidaten_voor(random.Random(iteratie)))
            nieuwe_beste = _kies([beste, variant])
            if nieuwe_beste is not beste:
                beste = nieuwe_beste
                pogingen_zonder_verbetering = 0
            else:
                pogingen_zonder_verbetering += 1

    if voortgang is not None:
        voortgang(1.0)

    if strategie == "cnc":
        # Geen zaagvolgorde (een CNC heeft die niet nodig — Svens keuze),
        # ook niet die van de fabriekskantenband-stroken. Afval = alles in
        # het werkgebied dat geen onderdeel en geen reststuk is (dus ook de
        # freesbanen tussen de onderdelen).
        alle_plaatsingen = plaatsingen + beste.plaatsingen
        niet_geplaatst.extend(beste.niet_geplaatst)
        fabriek_reststukken, _ = _classificeer_restruimte(fabriek_vrij, materiaal)
        reststukken = fabriek_reststukken + beste.reststukken
        wx0, wy0, wx1, wy1 = _werkgebied(materiaal)
        afval = max(
            0.0,
            (wx1 - wx0) * (wy1 - wy0)
            - sum(pl.breedte * pl.hoogte for pl in alle_plaatsingen)
            - sum(r.oppervlak for r in reststukken),
        )
        return _bouw_resultaat(materiaal, strategie, eenheden, alle_plaatsingen, reststukken, afval, [], niet_geplaatst)

    p2, vrije, np2, zaagvolgorde = beste
    alle_plaatsingen = plaatsingen + p2

    if fabriek_snedes:
        # De fabriekskantenband-scheidingssneden komen altijd het eerst
        # op de plaat (in de volgorde waarin hun stroken zijn afgesneden);
        # de rest van de (strategie-eigen) volgorde schuift evenveel
        # plekken op.
        zaagvolgorde = [replace(s, volgnummer=i) for i, s in enumerate(fabriek_snedes, start=1)] + [
            replace(s, volgnummer=i) for i, s in enumerate(zaagvolgorde, start=len(fabriek_snedes) + 1)
        ]
        # De sneden binnen een strook noteren hun lengte tot de rand van het
        # stuk, terwijl hun deelgebied tot de (na de kerf genoteerde)
        # scheidingssnede loopt — ook deze op de echte deelgebied-randen
        # zetten (zie _zet_sneden_op_deelgebieden).
        zaagvolgorde = _zet_sneden_op_deelgebieden(zaagvolgorde, *_werkgebied(materiaal))

    niet_geplaatst.extend(np2)
    reststukken, afval = _classificeer_restruimte(vrije + fabriek_vrij, materiaal)
    return _bouw_resultaat(materiaal, strategie, eenheden, alle_plaatsingen, reststukken, afval, zaagvolgorde, niet_geplaatst)


def _bouw_resultaat(
    materiaal: Materiaal,
    strategie: str,
    eenheden: list[_Eenheid],
    plaatsingen: list[Plaatsing],
    reststukken: list[Reststuk],
    afval: float,
    zaagvolgorde: list[Zaagsnede],
    niet_geplaatst: list[str],
) -> ZaagplanResultaat:
    eenheden_per_id = {e.unit_id: e for e in eenheden}
    niet_geplaatst_redenen = {
        uid: _reden_niet_geplaatst(eenheden_per_id[uid], materiaal)
        for uid in niet_geplaatst
        if uid in eenheden_per_id
    }
    return ZaagplanResultaat(
        materiaal=materiaal,
        strategie=strategie,
        plaatsingen=plaatsingen,
        reststukken=reststukken,
        afval_oppervlak=afval,
        zaagvolgorde=zaagvolgorde,
        niet_geplaatst=niet_geplaatst,
        niet_geplaatst_redenen=niet_geplaatst_redenen,
    )


_MAX_PLATEN = 500  # veiligheidsgrens tegen een oneindige lus, zie genereer_zaagplannen
_VERWACHTE_BENUTTING = 0.8  # zie schat_aantal_platen


def schat_aantal_platen(materiaal: Materiaal, onderdelen: list[Onderdeel]) -> int:
    """Ruwe schatting (minstens 1) van hoeveel platen
    ``genereer_zaagplannen`` voor deze onderdelen nodig zal hebben:
    totale onderdeel-oppervlakte gedeeld door het bruikbare werkgebied
    van één plaat, bij een aangenomen benutting van
    ``_VERWACHTE_BENUTTING``. Alleen bedoeld voor de voortgangsbalk
    (elke plaat kost ongeveer even veel zoektijd) — niet voor iets dat
    exact moet kloppen."""

    x0, y0, x1, y1 = _werkgebied(materiaal)
    plaat_oppervlak = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    if plaat_oppervlak <= 0:
        return 1
    totaal = sum(o.breedte * o.hoogte * o.aantal for o in onderdelen)
    return max(1, math.ceil(totaal / (plaat_oppervlak * _VERWACHTE_BENUTTING)))


def _onderdelen_voor_niet_geplaatst(
    onderdelen: list[Onderdeel], niet_geplaatst: list[str]
) -> list[Onderdeel]:
    """Bouwt de onderdelenlijst voor de volgende (verse) plaat: alleen
    de onderdelen die deze keer als ``niet_geplaatst`` zijn teruggekomen,
    met hun ``aantal`` teruggebracht tot het aantal exemplaren dat nog
    niet geplaatst is. Een groep (``groep_id``) is altijd atomair — die
    komt met al zijn leden terug zodra ``"groep:<id>"`` erbij zit, net
    als in ``_bouw_eenheden``."""

    groepen_niet_geplaatst = {
        uid.removeprefix("groep:") for uid in niet_geplaatst if uid.startswith("groep:")
    }
    volgende: list[Onderdeel] = []
    for onderdeel in onderdelen:
        if onderdeel.groep_id:
            if onderdeel.groep_id in groepen_niet_geplaatst:
                volgende.append(onderdeel)
            continue
        aantal = sum(1 for uid in niet_geplaatst if uid.split("#", 1)[0] == onderdeel.id)
        if aantal:
            volgende.append(replace(onderdeel, aantal=aantal))
    return volgende


def genereer_zaagplannen(
    materiaal: Materiaal,
    onderdelen: list[Onderdeel],
    strategie: str = "horizontaal",
    zoek_tijdsbudget: float = 0.0,
    min_zoek_tijdsbudget: float = 0.0,
    voortgang: Callable[[int, float], None] | None = None,
) -> list[ZaagplanResultaat]:
    """Genereert zoveel platen van ``materiaal`` als nodig zijn om alle
    ``onderdelen`` te plaatsen (onbeperkte voorraad aangenomen — dit is
    geen voorraadbeheer, alleen optimalisatie). Onderdelen die niet op
    de eerste plaat passen schuiven door naar een volgende, verse plaat,
    enzovoort, tot alles geplaatst is. Onderdelen die zelfs op een
    volledig lege plaat niet passen (te groot voor het materiaal) komen
    terecht in ``niet_geplaatst`` van de laatste gegenereerde plaat i.p.v.
    tot in het oneindige nieuwe, even lege platen op te leveren.

    :param zoek_tijdsbudget: zie ``genereer_zaagplan`` — geldt hier als
        TOTAAL budget over alle platen van deze aanroep samen (niet per
        plaat): elke volgende plaat krijgt wat er van het budget nog
        over is, zodat een project met meerdere platen nooit veel langer
        dan dit ene budget hoeft te wachten.
    :param min_zoek_tijdsbudget: zie ``genereer_zaagplan`` — wordt hier,
        anders dan ``zoek_tijdsbudget``, op elke plaat opnieuw toegepast
        (niet gedeeld over alle platen samen), zodat ook een project met
        meerdere platen elke plaat afzonderlijk zichtbaar laat
        "nadenken". Blijft wel begrensd door wat er op dat moment nog
        over is van het gedeelde ``zoek_tijdsbudget`` — bij een héél
        strak totaalbudget kan een latere plaat dus een kortere
        denktijd krijgen dan gevraagd.
    :param voortgang: optionele callback ``(plaat_nummer, fractie)``:
        ``plaat_nummer`` telt vanaf 1, ``fractie`` is de voortgang van
        díe plaat (zie ``genereer_zaagplan``'s ``voortgang``). Hoeveel
        platen er uiteindelijk nodig zijn staat vooraf niet vast — zie
        ``schat_aantal_platen`` voor een schatting."""

    resterend = list(onderdelen)
    resultaten: list[ZaagplanResultaat] = []
    deadline = time.monotonic() + zoek_tijdsbudget if zoek_tijdsbudget > 0 else None
    for plaat_nummer in range(1, _MAX_PLATEN + 1):
        if not resterend:
            break
        plaat_budget = max(0.0, deadline - time.monotonic()) if deadline is not None else 0.0
        resultaat = genereer_zaagplan(
            materiaal,
            resterend,
            strategie=strategie,
            zoek_tijdsbudget=plaat_budget,
            min_zoek_tijdsbudget=min_zoek_tijdsbudget,
            voortgang=(lambda f, n=plaat_nummer: voortgang(n, f)) if voortgang is not None else None,
        )

        if not resultaat.plaatsingen:
            # Geen enkel onderdeel van wat nog over was kon zelfs op een
            # verse, lege plaat geplaatst worden -> definitief gestrand
            # (een volgende, even lege plaat lost dit niet op). Geen
            # zinloze extra (helemaal lege) plaat toevoegen; gewoon de
            # laatst gegenereerde (wél bruikbare) plaat zijn
            # niet_geplaatst-lijst bijwerken naar deze definitieve stand
            # — tenzij dit al de allereerste plaat was.
            if resultaten:
                resultaten[-1] = replace(
                    resultaten[-1],
                    niet_geplaatst=resultaat.niet_geplaatst,
                    niet_geplaatst_redenen=resultaat.niet_geplaatst_redenen,
                )
            else:
                resultaten.append(resultaat)
            break

        if not resultaat.niet_geplaatst:
            # Alles wat nog over was past op deze plaat -> klaar.
            resultaten.append(resultaat)
            break

        # Deze plaat plaatst een deel; de rest schuift door naar een
        # volgende, verse plaat. Wat híer "niet_geplaatst" heet is dus
        # nog niet definitief (het wordt hierna alsnog geprobeerd) —
        # alleen de állerlaatste plaat mag onderdelen als écht niet
        # geplaatst tonen, dus deze tussenliggende plaat krijgt een lege
        # niet_geplaatst-lijst.
        resterend = _onderdelen_voor_niet_geplaatst(resterend, resultaat.niet_geplaatst)
        resultaten.append(replace(resultaat, niet_geplaatst=[], niet_geplaatst_redenen={}))
    return resultaten
