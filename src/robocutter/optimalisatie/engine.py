"""Zaagplan-optimalisatie-motor.

Implementeert de regels uit design/chapters/05-zaagplan-optimalisatie.md
als een losstaande, testbare Python-module (nog zonder UI — dat is
bewust de eerste stap, zie checklist.md).

Vier strategieën (namen/omschrijvingen vastgesteld in
``robocutter.instellingen.models.GELDIGE_ZAAGSTRATEGIEEN``, zie ook
``instellingen_page.py``'s ``_STRATEGIE_OMSCHRIJVING``):
  - "efficient": meest efficiënte plaatsing. Probeert intern alle drie
    andere heuristieken hieronder (guillotine free-rectangle
    best-area-fit, plus "guillotine", "rijen" én "stroken", zie
    hieronder) en gebruikt gewoon de beste van de vier uitkomsten (zie
    ``_kies_beste_pakresultaat``) — geen enkele losse heuristiek is
    altijd de beste (fuzz-getest, bekende zwakte van greedy
    bin-packing: elk van de andere drie plaatst in zo'n 10% van de
    gevallen aantoonbaar meer stukken op dezelfde plaat dan de
    best-area-fit-aanpak alleen), dus "efficient" vertrouwt niet blind
    op één heuristiek.
  - "rijen": lange zijdes eerst (rij-gebaseerd, volledige-breedte
    sneden eerst, daarna kortere sneden per rij) — de rijhoogte past
    zich per rij aan aan het grootste stuk erin.
  - "stroken": zoals "rijen", maar met overal dezelfde vaste
    strookhoogte i.p.v. een per-rij aangepaste hoogte — eenvoudiger te
    herhalen op een paneelzaag (elke doorsnede zit op dezelfde hoogte),
    iets minder efficiënt. De vaste hoogte is (op Svens verzoek, geen
    aparte instelling) de hoogte van het hoogste onderdeel over de hele
    plaat.
  - "guillotine": uitsluitend doorlopende zaagsnedes van rand tot rand
    van het op dat moment resterende deelgebied — een écht apart,
    strikter algoritme dan "efficient". "efficient" splitst intern ook
    al steeds een los vrij rechthoekje in twee (dus óók een geldige
    guillotine-partitie), maar kiest daarbij telkens het best passende
    rechthoekje uit de HELE verzameling vrije ruimtes; "guillotine"
    werkt in plaats daarvan een wachtrij van deelgebieden strikt één
    voor één helemaal af (plaatsen + volledig opsplitsen) voordat het
    volgende deelgebied aan de beurt is. Beide bouwen de zaagvolgorde
    rechtstreeks op uit hun eigen opsplitsingen (gedeelde hulpfunctie
    ``_splits_vrije_rechthoek``) — zo is elke genoteerde snede voor
    zowel "efficient" als "guillotine" gegarandeerd een volledige snede
    van rand tot rand van het deelgebied waarin hij gemaakt wordt, en
    loopt hij dus nooit dwars door een al geplaatst onderdeel heen. Het
    verschil tussen de twee zit dus alleen nog in de
    plaatsings-/keuzeheuristiek, niet meer in de kwaliteit van de
    zaagvolgorde zelf.

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
     geplaatst tegen de eerste rand in ``materiaal.fabriekskantenband_randen``
     (volgorde: links, onder, boven, rechts) die de plaat heeft.
  6. De zaagvolgorde-nummering (welke snede het volgnummer 1, 2, ...
     krijgt) is voor alle vier strategieën een eerste, redelijke
     benadering op basis van de plaatsings-/opsplitsingsvolgorde — dit
     wordt verder verfijnd zodra er meer gegenereerde voorbeelden zijn
     beoordeeld (zie hoofdstuk 5, "Openstaande vragen"). De sneden zélf
     (positie/start/einde) zijn dat sinds de zaagvolgorde-fix (zie
     OVERDRACHT.md) niet meer: die zijn voor alle vier strategieën
     gegarandeerd rand-tot-rand van hun eigen deelgebied/rij en lopen
     dus nooit door een al geplaatst onderdeel heen.
"""

from __future__ import annotations

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


@dataclass
class _Eenheid:
    """Eén plaatsbare eenheid: ofwel één exemplaar van een los
    onderdeel, ofwel een samengestelde groep (zie module-docstring)."""

    unit_id: str
    breedte: float
    hoogte: float
    mag_roteren: bool
    fabriekskantenband_vereist: bool
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
    fx: float, fy: float, fw: float, fh: float, genomen_b: float, genomen_h: float, volgnr_start: int
) -> tuple[list[tuple[float, float, float, float]], list[Zaagsnede]]:
    """Splitst het vrije rechthoek ``(fx, fy, fw, fh)`` in maximaal twee
    nieuwe vrije rechthoeken nadat er een stuk van ``genomen_b x
    genomen_h`` (kerf inbegrepen) uit de linkerbenedenhoek genomen is —
    kortste-as-eerst heuristiek. Gedeeld door ``_pak_efficient`` en
    ``_pak_guillotine`` zodat beide voor exact dezelfde opsplitsing
    exact dezelfde (rand-tot-rand, dus nooit door een geplaatst
    onderdeel heen lopende) zaagsnede opleveren."""

    rest_breedte = fw - genomen_b
    rest_hoogte = fh - genomen_h
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

    return nieuwe_rechten, sneden


def _pak_efficient(
    eenheden: list[_Eenheid], werkgebied: tuple[float, float, float, float], kerf: float
) -> tuple[list[Plaatsing], list[tuple[float, float, float, float]], list[str], list[Zaagsnede]]:
    """Guillotine free-rectangle packing, best-area-fit, voor de
    strategie 'meest efficiënte plaatsing'. Bouwt de zaagvolgorde
    rechtstreeks op uit de guillotine-opsplitsingen zelf (zie
    ``_splits_vrije_rechthoek``, dezelfde aanpak als ``_pak_guillotine``)
    i.p.v. de eerdere, losse per-plaatsing benadering — zo is elke
    genoteerde snede gegarandeerd een rand-tot-rand snede van het op
    dat moment gekozen vrije rechthoek en loopt hij dus nooit dwars
    door een al geplaatst onderdeel heen."""

    x0, y0, x1, y1 = werkgebied
    vrije_rechten: list[tuple[float, float, float, float]] = [(x0, y0, x1 - x0, y1 - y0)]
    plaatsingen: list[Plaatsing] = []
    niet_geplaatst: list[str] = []
    zaagvolgorde: list[Zaagsnede] = []

    # Grootste eerst plaatsen (best-area-fit werkt beter met grote stukken eerst).
    volgorde = sorted(eenheden, key=lambda e: e.breedte * e.hoogte, reverse=True)

    for eenheid in volgorde:
        breedte, hoogte, geroteerd = _kies_afmeting(eenheid, None)
        kandidaten = [(breedte, hoogte, geroteerd)]
        if eenheid.mag_roteren and abs(breedte - hoogte) > 1e-9:
            kandidaten.append((hoogte, breedte, not geroteerd))

        beste = None  # (rest_opp, rect_index, b, h, geroteerd)
        for i, (fx, fy, fw, fh) in enumerate(vrije_rechten):
            for (b, h, rot) in kandidaten:
                if b <= fw + 1e-9 and h <= fh + 1e-9:
                    rest_opp = fw * fh - b * h
                    if beste is None or rest_opp < beste[0]:
                        beste = (rest_opp, i, b, h, rot)

        if beste is None:
            niet_geplaatst.append(eenheid.unit_id)
            continue

        _, idx, b, h, rot = beste
        fx, fy, fw, fh = vrije_rechten.pop(idx)
        plaatsingen.extend(eenheid.expand(fx, fy, b, h, rot))

        # Ruimte die door de kerf verloren gaat (alleen als er nog een
        # snede nodig is, d.w.z. niet aan de plaatrand).
        kerf_r = kerf if (fx + b) < x1 - 1e-9 else 0.0
        kerf_o = kerf if (fy + h) < y1 - 1e-9 else 0.0
        genomen_b = b + kerf_r
        genomen_h = h + kerf_o

        nieuwe_rechten, sneden = _splits_vrije_rechthoek(
            fx, fy, fw, fh, genomen_b, genomen_h, len(zaagvolgorde) + 1
        )
        zaagvolgorde.extend(sneden)
        vrije_rechten.extend(nieuwe_rechten)

    return plaatsingen, vrije_rechten, niet_geplaatst, zaagvolgorde


def _landschap_indien_vrij(
    eenheid: _Eenheid, b: float, h: float, rot: bool, beschikbare_breedte: float
) -> tuple[float, float, bool]:
    """Voor 'rijen'/'stroken' ("lange zijdes eerst"): een eenheid die vrij
    mag roteren (geen nerf-eis, geen groep) wordt met zijn langste zijde
    langs de x-as gelegd — zoals de strategienaam zelf al belooft — i.p.v.
    de invoer-oriëntatie van het onderdeel klakkeloos over te nemen.
    Zonder deze stap roteerde de motor in deze twee strategieën nooit een
    vrij onderdeel, ook niet als "liggend" leggen overduidelijk beter
    (kortere rij, dus meer rijen passend) of zelfs noodzakelijk was (om
    sowieso te passen op een plaat die smaller is dan het onderdeel hoog
    staat). ``_pak_efficient``/``_pak_guillotine`` hebben dit al langer
    via hun eigen best-fit-zoektocht over beide oriëntaties.

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


_HOOGTE_TOLERANTIE = 1.0  # mm; "(bijna) gelijke hoogte" bij het groeperen in _pak_rijen/_pak_stroken


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


def _vul_rij(
    resterend: list[tuple[_Eenheid, float, float, bool]], x0: float, x1: float, kerf: float
) -> tuple[list[tuple[_Eenheid, float, float, bool]], list[tuple[_Eenheid, float, float, bool]], float]:
    """Vult één rij vanaf ``x0`` tot ``x1``. De eerste (hoogte-bepalende)
    hoogte-groep in ``resterend`` mag gedeeltelijk in de rij komen (de
    rest wacht op een volgende rij, normaal gedrag als er simpelweg meer
    stukken van die hoogte zijn dan in één rij passen). Elke latere,
    kortere hoogte-groep mag alleen als geheel meedoen als opvulling van
    de resterende breedte — nooit gedeeltelijk, want dat zou (bijna)
    identieke onderdelen zonder aanleiding over meerdere rijen
    verspreiden (zie ``_pak_rijen``'s docstring / OVERDRACHT.md)."""

    rij: list[tuple[_Eenheid, float, float, bool]] = []
    overig: list[tuple[_Eenheid, float, float, bool]] = []
    cursor_x = x0
    rij_hoogte = 0.0
    for i, groep in enumerate(_groepeer_op_hoogte(resterend)):
        if i == 0:
            genomen = 0
            for (eenheid, b, h, rot) in groep:
                if (cursor_x + b) <= x1 + 1e-9:
                    rij.append((eenheid, b, h, rot))
                    rij_hoogte = max(rij_hoogte, h)
                    cursor_x += b + kerf
                    genomen += 1
                else:
                    break
            overig.extend(groep[genomen:])
        else:
            breedte_nodig = sum(b for (_, b, _, _) in groep) + kerf * (len(groep) - 1)
            if rij and (cursor_x + breedte_nodig) <= x1 + 1e-9:
                for (eenheid, b, h, rot) in groep:
                    rij.append((eenheid, b, h, rot))
                    rij_hoogte = max(rij_hoogte, h)
                    cursor_x += b + kerf
            else:
                overig.extend(groep)
    return rij, overig, rij_hoogte


def _plaats_rij(
    rij: list[tuple[_Eenheid, float, float, bool]], x0: float, cursor_y: float, kerf: float
) -> tuple[list[Plaatsing], list[Zaagsnede], list[float], float]:
    """Plaatst de onderdelen van één rij/strook (van links naar rechts,
    startend op ``x0``) en bouwt de interne groeps-naadsneden op (nog met
    voorlopig volgnummer 0, zie ``_bouw_zaagvolgorde_uit_rijen``) — voor
    een kolom die een gestapelde groep is, de horizontale sneden tussen
    de leden, begrensd tot de breedte van die kolom zelf, nooit de volle
    plaatbreedte. Retourneert ook de kolomranden (x-posities tussen
    kolommen) en de eind-x-positie; de sneden TUSSEN kolommen zelf worden
    hier bewust NOG NIET gebouwd — dat kan pas nadat de aanroeper de rij
    heeft afgerond en de ECHTE bovengrens van de rij kent (zie de
    bugfix-toelichting bij ``_bouw_zaagvolgorde_uit_rijen``). Losgetrokken
    uit ``_pak_rijen``/``_pak_stroken`` omdat beide exact dezelfde
    rij-opbouw hebben."""

    plaatsingen: list[Plaatsing] = []
    groep_sneden: list[Zaagsnede] = []
    kolom_randen: list[float] = []
    x = x0
    for (eenheid, b, h, rot) in rij:
        nieuwe = eenheid.expand(x, cursor_y, b, h, rot)
        plaatsingen.extend(nieuwe)
        if len(nieuwe) > 1:
            # Gestapelde groep: interne sneden tussen de leden, begrensd
            # tot deze kolom (x .. x+b) i.p.v. de volle plaatbreedte —
            # zonder deze begrenzing zou zo'n interne snede dwars door
            # elk ander onderdeel in dezelfde rij heen lopen.
            for lid in sorted(nieuwe, key=lambda p: p.y)[:-1]:
                grens_y = round(lid.y + lid.hoogte, 6)
                groep_sneden.append(Zaagsnede(0, "horizontaal", grens_y, x, x + b))
        kolom_randen.append(round(x + b, 6))
        x += b + kerf

    return plaatsingen, groep_sneden, kolom_randen, x


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
        for grens_x in kolom_randen[:-1]:
            kolom_sneden.append(Zaagsnede(0, "verticaal", grens_x, cursor_y_i, rij_top))

    for snede in groep_sneden + kolom_sneden:
        sneden.append(replace(snede, volgnummer=volgnr))
        volgnr += 1

    return sneden


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
    eenheden: list[_Eenheid], werkgebied: tuple[float, float, float, float], kerf: float
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
    genormaliseerd.sort(key=lambda t: t[2], reverse=True)

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

        nieuwe_plaatsingen, nieuwe_groep_sneden, kolom_randen, x = _plaats_rij(rij, x0, cursor_y, kerf)
        plaatsingen.extend(nieuwe_plaatsingen)
        groep_sneden.extend(nieuwe_groep_sneden)
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


def _pak_stroken(
    eenheden: list[_Eenheid], werkgebied: tuple[float, float, float, float], kerf: float
) -> tuple[list[Plaatsing], list[tuple[float, float, float, float]], list[str], list[Zaagsnede]]:
    """Rij-gebaseerde packing voor de strategie 'Stroken': zoals
    ``_pak_rijen``, maar met overal dezelfde vaste strookhoogte i.p.v.
    een per-rij aangepaste hoogte. De vaste hoogte is de hoogte van het
    hoogste onderdeel over de hele plaat, dus per definitie past elk
    onderdeel op zijn eigen hoogte binnen één strook — enige reden om
    iets niet te plaatsen is dat de plaat verticaal vol is.

    Gebruikt bewust NIET de ``_vind_plaatsbare_rij``-fix die ``_pak_rijen``
    wel heeft (zie daar): bij "Stroken" is de strookhoogte plaatbreed
    vast, dus zodra één strook niet meer past, past — anders dan bij
    "Rijen" — ECHT geen enkel resterend onderdeel meer, hoe klein ook
    (elke strook is immers altijd even hoog, ongeacht wat erin ligt).
    Vroegtijdig stoppen zodra ``cursor_y + strook_hoogte`` de plaat niet
    meer in past, is voor deze strategie dus geen bug maar het juiste
    gedrag."""

    x0, y0, x1, y1 = werkgebied
    breedte_plaat = x1 - x0

    genormaliseerd = []
    for eenheid in eenheden:
        b, h, rot = _kies_afmeting(eenheid, None)
        b, h, rot = _landschap_indien_vrij(eenheid, b, h, rot, breedte_plaat)
        genormaliseerd.append((eenheid, b, h, rot))
    genormaliseerd.sort(key=lambda t: t[2], reverse=True)

    strook_hoogte = max((h for (_, _, h, _) in genormaliseerd), default=0.0)

    plaatsingen: list[Plaatsing] = []
    niet_geplaatst: list[str] = []
    resterend = list(genormaliseerd)
    cursor_y = y0
    vrije_rechten: list[tuple[float, float, float, float]] = []
    rij_grenzen: list[tuple[float, float]] = []
    rijen_kolomranden: list[list[float]] = []
    groep_sneden: list[Zaagsnede] = []

    while resterend:
        if cursor_y + strook_hoogte > y1 + 1e-9:
            niet_geplaatst.extend(e.unit_id for (e, _, _, _) in resterend)
            break

        # Onderdelen met (bijna) gelijke hoogte blijven bij voorkeur bij
        # elkaar in dezelfde strook (zie _vul_rij/_pak_rijen hierboven).
        rij, overig_na_rij, _ = _vul_rij(resterend, x0, x1, kerf)
        if not rij:
            niet_geplaatst.extend(e.unit_id for (e, _, _, _) in overig_na_rij)
            break

        nieuwe_plaatsingen, nieuwe_groep_sneden, kolom_randen, x = _plaats_rij(rij, x0, cursor_y, kerf)
        plaatsingen.extend(nieuwe_plaatsingen)
        groep_sneden.extend(nieuwe_groep_sneden)
        rijen_kolomranden.append(kolom_randen)
        rij_grenzen.append((cursor_y, strook_hoogte))
        if x < x1 - 1e-6:
            vrije_rechten.append((x - kerf if rij else x, cursor_y, x1 - x, strook_hoogte))

        # Restruimte boven kortere stukken binnen dezelfde strook (h <
        # strook_hoogte) wordt bewust niet als apart bruikbaar reststuk
        # vrijgegeven — dat zou allemaal losse, smalle reepjes worden.
        # Zelfde vereenvoudiging als bij "rijen" voor restruimte binnen
        # een rij.
        cursor_y += strook_hoogte + kerf
        resterend = overig_na_rij

    if cursor_y < y1 - 1e-6:
        vrije_rechten.append((x0, cursor_y, x1 - x0, y1 - cursor_y))

    zaagvolgorde = _bouw_zaagvolgorde_uit_rijen(rij_grenzen, rijen_kolomranden, groep_sneden, x0, x1, y1)
    return plaatsingen, vrije_rechten, niet_geplaatst, zaagvolgorde


def _pak_guillotine(
    eenheden: list[_Eenheid], werkgebied: tuple[float, float, float, float], kerf: float
) -> tuple[list[Plaatsing], list[tuple[float, float, float, float]], list[str], list[Zaagsnede]]:
    """Recursieve rand-tot-rand guillotine-plaatsing voor de strategie
    'Guillotine' — zie de module-docstring voor het verschil met
    ``_pak_efficient``. Verwerkt een wachtrij van deelgebieden strikt
    FIFO: voor elk deelgebied wordt het eerste onderdeel uit de
    (grootste-eerst gesorteerde) resterende lijst geplaatst dat erin
    past, waarna het deelgebied in maximaal twee nieuwe deelgebieden
    wordt gesplitst (kortste-as-eerst, zelfde heuristiek als
    ``_pak_efficient``) — pas dan komt het volgende deelgebied aan de
    beurt. Bouwt de zaagvolgorde rechtstreeks op uit die opsplitsingen,
    zodat elke genoteerde snede een echte rand-tot-rand snede van het
    op dat moment behandelde deelgebied is."""

    x0, y0, x1, y1 = werkgebied
    resterend = sorted(eenheden, key=lambda e: e.breedte * e.hoogte, reverse=True)

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
        plaatsingen.extend(eenheid.expand(fx, fy, b, h, rot))

        kerf_r = kerf if (fx + b) < x1 - 1e-9 else 0.0
        kerf_o = kerf if (fy + h) < y1 - 1e-9 else 0.0
        genomen_b = b + kerf_r
        genomen_h = h + kerf_o

        nieuwe_rechten, sneden = _splits_vrije_rechthoek(
            fx, fy, fw, fh, genomen_b, genomen_h, len(zaagvolgorde) + 1
        )
        zaagvolgorde.extend(sneden)
        wachtrij.extend(nieuwe_rechten)

    niet_geplaatst = [e.unit_id for e in resterend]
    return plaatsingen, vrije_rechten, niet_geplaatst, zaagvolgorde


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

    Retourneert (plaatsingen, niet_geplaatst, nieuw_x0, nieuw_y0, nieuw_x1, nieuw_y1)
    — het bijgewerkte werkgebied ná aftrek van de daadwerkelijk ingenomen
    rand-strook (ongewijzigd als er niets geplaatst kon worden)."""

    langs_verticaal = rand in (Rand.LINKS, Rand.RECHTS)
    langs_lengte = (y1 - y0) if langs_verticaal else (x1 - x0)
    beschikbare_diepte = (x1 - x0) if langs_verticaal else (y1 - y0)

    plaatsingen: list[Plaatsing] = []
    niet_geplaatst: list[str] = []
    langs_cursor = 0.0  # positie langs de rand, al ingenomen door eerder geplaatste stukken
    strook_diepte = 0.0  # diepte (loodrecht op de rand) van de strook, bepaald door het diepste geplaatste stuk

    for eenheid in eenheden:
        b, h, rot = _kies_afmeting(eenheid, None)
        diepte, lengte_langs = (b, h) if langs_verticaal else (h, b)

        if diepte > beschikbare_diepte + 1e-9 or langs_cursor + lengte_langs > langs_lengte + 1e-9:
            # Natuurlijke oriëntatie past niet -- een vrij-roteerbaar stuk
            # (geen nerf-eis) krijgt, net als _pak_efficient/_pak_guillotine
            # en de "lange zijdes eerst"-fix voor rijen/stroken, ook de
            # geroteerde oriëntatie als kans i.p.v. blijvend te sneuvelen
            # (ook op een verse plaat) puur omdat het toevallig "verkeerd
            # om" in de onderdelenlijst stond.
            if eenheid.mag_roteren and abs(b - h) > 1e-9:
                b, h, rot = h, b, not rot
                diepte, lengte_langs = (b, h) if langs_verticaal else (h, b)
            if diepte > beschikbare_diepte + 1e-9 or langs_cursor + lengte_langs > langs_lengte + 1e-9:
                niet_geplaatst.append(eenheid.unit_id)
                continue

        if langs_verticaal:
            px, py = x0, y0 + langs_cursor
        else:
            px, py = x0 + langs_cursor, y0
        if rand == Rand.RECHTS:
            px = x1 - diepte
        elif rand == Rand.BOVEN:
            py = y1 - diepte

        plaatsingen.extend(eenheid.expand(px, py, b, h, rot))
        strook_diepte = max(strook_diepte, diepte)
        langs_cursor += lengte_langs + kerf

    if strook_diepte <= 0:
        return plaatsingen, niet_geplaatst, x0, y0, x1, y1

    if rand == Rand.LINKS:
        return plaatsingen, niet_geplaatst, x0 + strook_diepte + kerf, y0, x1, y1
    if rand == Rand.RECHTS:
        return plaatsingen, niet_geplaatst, x0, y0, x1 - strook_diepte - kerf, y1
    if rand == Rand.ONDER:
        return plaatsingen, niet_geplaatst, x0, y0 + strook_diepte + kerf, x1, y1
    return plaatsingen, niet_geplaatst, x0, y0, x1, y1 - strook_diepte - kerf  # BOVEN


_PakResultaat = tuple[list[Plaatsing], list[tuple[float, float, float, float]], list[str], list[Zaagsnede]]


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


_GELDIGE_STRATEGIEEN = ("efficient", "rijen", "stroken", "guillotine")


def genereer_zaagplan(
    materiaal: Materiaal, onderdelen: list[Onderdeel], strategie: str = "efficient"
) -> ZaagplanResultaat:
    """Genereer een zaagplan voor één plaat van ``materiaal`` met de
    gegeven ``onderdelen``.

    :param strategie: "efficient" (meest efficiënte plaatsing), "rijen"
        (lange zijdes eerst, rijhoogte per rij aangepast), "stroken"
        (zoals rijen, maar overal dezelfde vaste strookhoogte) of
        "guillotine" (uitsluitend rand-tot-rand sneden) — zie de
        module-docstring voor de precieze verschillen.
    """

    if strategie not in _GELDIGE_STRATEGIEEN:
        raise ValueError(
            f"Onbekende strategie: {strategie!r} (verwacht een van: {', '.join(_GELDIGE_STRATEGIEEN)})"
        )

    kerf = materiaal.kerf
    eenheden, waarschuwingen = _bouw_eenheden(onderdelen, kerf)
    werkgebied = _werkgebied(materiaal)

    # Onderdelen die een fabriekskantenband nodig hebben eerst tegen de
    # betreffende rand plaatsen; de rest van het werkgebied gaat door
    # naar de gekozen strategie. (Eerste versie: ondersteunt één
    # gekozen fabrieksrand tegelijk — zie aanname 5.)
    fabriek_eenheden = [e for e in eenheden if e.fabriekskantenband_vereist]
    overige_eenheden = [e for e in eenheden if not e.fabriekskantenband_vereist]

    x0, y0, x1, y1 = werkgebied
    if fabriek_eenheden and materiaal.fabriekskantenband_randen:
        rand = next((r for r in _RANDVOLGORDE if r in materiaal.fabriekskantenband_randen), None)
    else:
        rand = None

    plaatsingen: list[Plaatsing] = []
    niet_geplaatst: list[str] = []
    fabriek_snede: Zaagsnede | None = None

    if rand is not None:
        plaatsingen, fabriek_niet_geplaatst, nieuw_x0, nieuw_y0, nieuw_x1, nieuw_y1 = _plaats_fabriek_rand(
            fabriek_eenheden, rand, x0, y0, x1, y1, kerf
        )
        niet_geplaatst.extend(fabriek_niet_geplaatst)

        # De snede die de fabriekskantenband-strook van de rest scheidt
        # (rand-tot-rand van het werkgebied, want dit is de allereerste
        # snede op deze plaat) — alleen als er ook daadwerkelijk een
        # strook is overgebleven (kan leeg zijn als geen van de
        # fabriek-eenheden ergens in paste).
        if rand == Rand.LINKS and nieuw_x0 != x0:
            fabriek_snede = Zaagsnede(0, "verticaal", nieuw_x0, y0, y1)
        elif rand == Rand.RECHTS and nieuw_x1 != x1:
            fabriek_snede = Zaagsnede(0, "verticaal", nieuw_x1, y0, y1)
        elif rand == Rand.ONDER and nieuw_y0 != y0:
            fabriek_snede = Zaagsnede(0, "horizontaal", nieuw_y0, x0, x1)
        elif rand == Rand.BOVEN and nieuw_y1 != y1:
            fabriek_snede = Zaagsnede(0, "horizontaal", nieuw_y1, x0, x1)
        x0, y0, x1, y1 = nieuw_x0, nieuw_y0, nieuw_x1, nieuw_y1
        werkgebied = (x0, y0, x1, y1)
    else:
        overige_eenheden = eenheden

    if strategie == "efficient":
        # De greedy best-area-fit-heuristiek van _pak_efficient (steeds het
        # vrije rechthoekje met de minste restruimte kiezen voor het
        # huidige stuk) kan in de praktijk soms slechter uitpakken dan een
        # van de andere drie heuristieken -- een bekende zwakte van greedy
        # bin-packing: de lokaal beste keuze voor het huidige stuk is niet
        # altijd de beste keuze op de lange termijn (fuzz-getest: elk van
        # "guillotine"/"rijen"/"stroken" plaatst in zo'n 10% van de
        # gevallen aantoonbaar meer stukken op dezelfde plaat dan
        # "efficient" zelf). "efficient" probeert daarom alle vier en
        # gebruikt gewoon de beste van de vier uitkomsten (zie
        # _kies_beste_pakresultaat) i.p.v. blind op één heuristiek te
        # vertrouwen -- "efficient" betekent hier dus letterlijk "het
        # beste resultaat van alle beschikbare aanpakken", niet "altijd
        # dezelfde ene slimme aanpak".
        kandidaten = [
            _pak_efficient(overige_eenheden, werkgebied, kerf),
            _pak_guillotine(overige_eenheden, werkgebied, kerf),
            _pak_rijen(overige_eenheden, werkgebied, kerf),
            _pak_stroken(overige_eenheden, werkgebied, kerf),
        ]
        p2, vrije, np2, zaagvolgorde = _kies_beste_pakresultaat(kandidaten, materiaal)
        alle_plaatsingen = plaatsingen + p2
    elif strategie == "rijen":
        p2, vrije, np2, zaagvolgorde = _pak_rijen(overige_eenheden, werkgebied, kerf)
        alle_plaatsingen = plaatsingen + p2
    elif strategie == "stroken":
        p2, vrije, np2, zaagvolgorde = _pak_stroken(overige_eenheden, werkgebied, kerf)
        alle_plaatsingen = plaatsingen + p2
    else:  # "guillotine"
        p2, vrije, np2, zaagvolgorde = _pak_guillotine(overige_eenheden, werkgebied, kerf)
        alle_plaatsingen = plaatsingen + p2

    if fabriek_snede is not None:
        # De fabriekskantenband-scheidingssnede is altijd de eerste
        # snede op de plaat; de rest van de (strategie-eigen) volgorde
        # schuift een plek op.
        zaagvolgorde = [replace(fabriek_snede, volgnummer=1)] + [
            replace(s, volgnummer=i) for i, s in enumerate(zaagvolgorde, start=2)
        ]

    niet_geplaatst.extend(np2)
    reststukken, afval = _classificeer_restruimte(vrije, materiaal)

    return ZaagplanResultaat(
        materiaal=materiaal,
        strategie=strategie,
        plaatsingen=alle_plaatsingen,
        reststukken=reststukken,
        afval_oppervlak=afval,
        zaagvolgorde=zaagvolgorde,
        niet_geplaatst=niet_geplaatst,
    )


_MAX_PLATEN = 500  # veiligheidsgrens tegen een oneindige lus, zie genereer_zaagplannen


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
    materiaal: Materiaal, onderdelen: list[Onderdeel], strategie: str = "efficient"
) -> list[ZaagplanResultaat]:
    """Genereert zoveel platen van ``materiaal`` als nodig zijn om alle
    ``onderdelen`` te plaatsen (onbeperkte voorraad aangenomen — dit is
    geen voorraadbeheer, alleen optimalisatie). Onderdelen die niet op
    de eerste plaat passen schuiven door naar een volgende, verse plaat,
    enzovoort, tot alles geplaatst is. Onderdelen die zelfs op een
    volledig lege plaat niet passen (te groot voor het materiaal) komen
    terecht in ``niet_geplaatst`` van de laatste gegenereerde plaat i.p.v.
    tot in het oneindige nieuwe, even lege platen op te leveren."""

    resterend = list(onderdelen)
    resultaten: list[ZaagplanResultaat] = []
    for _ in range(_MAX_PLATEN):
        if not resterend:
            break
        resultaat = genereer_zaagplan(materiaal, resterend, strategie=strategie)

        if not resultaat.plaatsingen:
            # Geen enkel onderdeel van wat nog over was kon zelfs op een
            # verse, lege plaat geplaatst worden -> definitief gestrand
            # (een volgende, even lege plaat lost dit niet op). Geen
            # zinloze extra (helemaal lege) plaat toevoegen; gewoon de
            # laatst gegenereerde (wél bruikbare) plaat zijn
            # niet_geplaatst-lijst bijwerken naar deze definitieve stand
            # — tenzij dit al de allereerste plaat was.
            if resultaten:
                resultaten[-1] = replace(resultaten[-1], niet_geplaatst=resultaat.niet_geplaatst)
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
        resultaten.append(replace(resultaat, niet_geplaatst=[]))
    return resultaten
