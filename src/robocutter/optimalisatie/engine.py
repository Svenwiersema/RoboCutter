"""Zaagplan-optimalisatie-motor.

Implementeert de regels uit design/chapters/05-zaagplan-optimalisatie.md
als een losstaande, testbare Python-module (nog zonder UI — dat is
bewust de eerste stap, zie checklist.md).

Twee strategieën, zoals besproken:
  - "efficient": meest efficiënte plaatsing (guillotine free-rectangle
    packing, best-area-fit).
  - "rijen": lange zijdes eerst (rij-gebaseerd, volledige-breedte
    sneden eerst, daarna kortere sneden per rij).

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
  6. De zaagvolgorde (zaagvolgorde-lijst) is een eerste, redelijke
     benadering op basis van de plaatsingsvolgorde — dit wordt verder
     verfijnd zodra er meer gegenereerde voorbeelden zijn beoordeeld
     (zie hoofdstuk 5, "Openstaande vragen").
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


def _pak_efficient(
    eenheden: list[_Eenheid], werkgebied: tuple[float, float, float, float], kerf: float
) -> tuple[list[Plaatsing], list[tuple[float, float, float, float]], list[str]]:
    """Guillotine free-rectangle packing, best-area-fit, voor de
    strategie 'meest efficiënte plaatsing'."""

    x0, y0, x1, y1 = werkgebied
    vrije_rechten: list[tuple[float, float, float, float]] = [(x0, y0, x1 - x0, y1 - y0)]
    plaatsingen: list[Plaatsing] = []
    niet_geplaatst: list[str] = []

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

        # Guillotine-split: verdeel de rest van fw x fh in twee nieuwe
        # vrije rechthoeken (kortste-as-eerst heuristiek).
        rest_breedte = fw - genomen_b
        rest_hoogte = fh - genomen_h
        if rest_breedte < rest_hoogte:
            if rest_breedte > 1e-6:
                vrije_rechten.append((fx + genomen_b, fy, rest_breedte, fh))
            if rest_hoogte > 1e-6:
                vrije_rechten.append((fx, fy + genomen_h, genomen_b, rest_hoogte))
        else:
            if rest_hoogte > 1e-6:
                vrije_rechten.append((fx, fy + genomen_h, fw, rest_hoogte))
            if rest_breedte > 1e-6:
                vrije_rechten.append((fx + genomen_b, fy, rest_breedte, genomen_h))

    return plaatsingen, vrije_rechten, niet_geplaatst


def _pak_rijen(
    eenheden: list[_Eenheid], werkgebied: tuple[float, float, float, float], kerf: float
) -> tuple[list[Plaatsing], list[tuple[float, float, float, float]], list[str]]:
    """Rij-gebaseerde packing voor de strategie 'lange zijdes eerst':
    volledige-breedte rijen, binnen een rij van links naar rechts."""

    x0, y0, x1, y1 = werkgebied
    breedte_plaat = x1 - x0

    # Voor elke eenheid de hoogte bepalen die hij in een rij zou
    # innemen (rekening houdend met eventuele nerf-rotatie-eis).
    genormaliseerd = []
    for eenheid in eenheden:
        b, h, rot = _kies_afmeting(eenheid, None)
        genormaliseerd.append((eenheid, b, h, rot))

    # Grootste hoogte eerst (rijen met de langste/breedste stukken onderaan/bovenaan eerst).
    genormaliseerd.sort(key=lambda t: t[2], reverse=True)

    plaatsingen: list[Plaatsing] = []
    niet_geplaatst: list[str] = []
    resterend = list(genormaliseerd)
    cursor_y = y0
    vrije_rechten: list[tuple[float, float, float, float]] = []

    while resterend:
        # Nieuwe rij starten met het eerste (hoogste) overgebleven stuk.
        rij: list[tuple[_Eenheid, float, float, bool]] = []
        rij_hoogte = 0.0
        cursor_x = x0
        overig_na_rij = []
        for (eenheid, b, h, rot) in resterend:
            past_in_breedte = (cursor_x + b) <= x1 + 1e-9
            if past_in_breedte:
                rij.append((eenheid, b, h, rot))
                rij_hoogte = max(rij_hoogte, h)
                cursor_x += b + kerf
            else:
                overig_na_rij.append((eenheid, b, h, rot))
        if not rij:
            # Past geen enkel overgebleven stuk meer (te breed of te hoog) -> stoppen.
            niet_geplaatst.extend(e.unit_id for (e, _, _, _) in overig_na_rij)
            break
        if cursor_y + rij_hoogte > y1 + 1e-9:
            niet_geplaatst.extend(e.unit_id for (e, _, _, _) in rij)
            niet_geplaatst.extend(e.unit_id for (e, _, _, _) in overig_na_rij)
            break

        x = x0
        for (eenheid, b, h, rot) in rij:
            plaatsingen.extend(eenheid.expand(x, cursor_y, b, h, rot))
            x += b + kerf
        # Restruimte rechts in de rij (indien nog iets overblijft binnen de rijhoogte).
        if x < x1 - 1e-6:
            vrije_rechten.append((x - kerf if rij else x, cursor_y, x1 - x, rij_hoogte))

        volgende_y = cursor_y + rij_hoogte + kerf
        resterend = overig_na_rij
        cursor_y = volgende_y

    if cursor_y < y1 - 1e-6:
        vrije_rechten.append((x0, cursor_y, breedte_plaat, y1 - cursor_y))

    return plaatsingen, vrije_rechten, niet_geplaatst


def _bouw_zaagvolgorde_rijen(plaatsingen: list[Plaatsing], werkgebied: tuple[float, float, float, float]) -> list[Zaagsnede]:
    x0, y0, x1, y1 = werkgebied
    sneden: list[Zaagsnede] = []
    volgnr = 1
    rij_ys = sorted({round(p.y, 6) for p in plaatsingen})
    rij_hoogtes = {}
    for ry in rij_ys:
        hoogtes = [p.hoogte for p in plaatsingen if round(p.y, 6) == ry]
        rij_hoogtes[ry] = max(hoogtes) if hoogtes else 0.0

    # Volledige-breedte horizontale sneden tussen rijen (van boven naar beneden overgeslagen: eerste snede scheidt eerste rij van de rest).
    for ry in rij_ys[1:]:
        sneden.append(Zaagsnede(volgnr, "horizontaal", ry, x0, x1))
        volgnr += 1

    # Daarna, per rij, de verticale sneden die de rij in onderdelen verdeelt.
    for ry in rij_ys:
        rij_plaatsingen = sorted((p for p in plaatsingen if round(p.y, 6) == ry), key=lambda p: p.x)
        for p in rij_plaatsingen[:-1]:
            snede_x = round(p.x + p.breedte, 6)
            sneden.append(Zaagsnede(volgnr, "verticaal", snede_x, ry, ry + rij_hoogtes[ry]))
            volgnr += 1

    return sneden


def _bouw_zaagvolgorde_generiek(plaatsingen: list[Plaatsing]) -> list[Zaagsnede]:
    """Eenvoudige, plaatsingsvolgorde-gebaseunde benadering van de
    zaagvolgorde voor de 'efficient'-strategie (zie aanname 6
    hierboven — dit is een eerste versie)."""

    sneden: list[Zaagsnede] = []
    gezien_x: set[float] = set()
    gezien_y: set[float] = set()
    volgnr = 1
    for p in plaatsingen:
        rechts = round(p.x + p.breedte, 6)
        boven = round(p.y + p.hoogte, 6)
        if rechts not in gezien_x:
            sneden.append(Zaagsnede(volgnr, "verticaal", rechts, p.y, p.y + p.hoogte))
            gezien_x.add(rechts)
            volgnr += 1
        if boven not in gezien_y:
            sneden.append(Zaagsnede(volgnr, "horizontaal", boven, p.x, p.x + p.breedte))
            gezien_y.add(boven)
            volgnr += 1
    return sneden


def genereer_zaagplan(
    materiaal: Materiaal, onderdelen: list[Onderdeel], strategie: str = "efficient"
) -> ZaagplanResultaat:
    """Genereer een zaagplan voor één plaat van ``materiaal`` met de
    gegeven ``onderdelen``.

    :param strategie: "efficient" (meest efficiënte plaatsing) of
        "rijen" (lange zijdes eerst).
    """

    if strategie not in ("efficient", "rijen"):
        raise ValueError(f"Onbekende strategie: {strategie!r} (verwacht 'efficient' of 'rijen')")

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

    if rand is not None:
        cursor = x0 if rand in (Rand.LINKS, Rand.RECHTS) else y0
        for eenheid in fabriek_eenheden:
            b, h, rot = _kies_afmeting(eenheid, None)
            if rand == Rand.LINKS:
                px, py = x0, cursor
            elif rand == Rand.ONDER:
                px, py = cursor, y0
            elif rand == Rand.RECHTS:
                px, py = x1 - b, cursor
            else:  # BOVEN
                px, py = cursor, y1 - h
            plaatsingen.extend(eenheid.expand(px, py, b, h, rot))
            cursor += (h if rand in (Rand.LINKS, Rand.RECHTS) else b) + kerf

        # Werkgebied voor de rest verkleinen met de strook die de
        # fabriekskantenband-onderdelen nu innemen.
        if rand == Rand.LINKS:
            breedte_strook = max((p.breedte for p in plaatsingen), default=0.0)
            x0 = x0 + breedte_strook + kerf
        elif rand == Rand.RECHTS:
            breedte_strook = max((p.breedte for p in plaatsingen), default=0.0)
            x1 = x1 - breedte_strook - kerf
        elif rand == Rand.ONDER:
            hoogte_strook = max((p.hoogte for p in plaatsingen), default=0.0)
            y0 = y0 + hoogte_strook + kerf
        else:
            hoogte_strook = max((p.hoogte for p in plaatsingen), default=0.0)
            y1 = y1 - hoogte_strook - kerf
        werkgebied = (x0, y0, x1, y1)
    else:
        overige_eenheden = eenheden

    if strategie == "efficient":
        p2, vrije, np2 = _pak_efficient(overige_eenheden, werkgebied, kerf)
        alle_plaatsingen = plaatsingen + p2
        zaagvolgorde = _bouw_zaagvolgorde_generiek(alle_plaatsingen)
    else:
        p2, vrije, np2 = _pak_rijen(overige_eenheden, werkgebied, kerf)
        alle_plaatsingen = plaatsingen + p2
        zaagvolgorde = _bouw_zaagvolgorde_rijen(alle_plaatsingen, werkgebied)

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
