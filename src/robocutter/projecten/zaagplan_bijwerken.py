"""Zaagplan bijwerken tijdens productie: na een revisie alleen een deel
opnieuw genereren (mockup ``design/assets/mockups/deel-opnieuw-genereren-concept.html``).

Sven: als een revisie tijdens productie wordt doorgevoerd is er al gezaagd,
dus niet het hele zaagplan opnieuw. Gekozen (vooraf gevraagd):

- **Per onderdeel afvinken** wat gezaagd is (``PlaatZaagplan.gezaagd``).
  Een plaat met minstens één gezaagd onderdeel is *aangezaagd* en blijft
  staan, inclusief de onderdelen die er nog uit moeten.
- **Platen waar nog niets uit gezaagd is worden opnieuw verdeeld**, samen
  met wat de nieuwe samenstelling verder nog nodig heeft.
- **Reststukken van aangezaagde platen mogen gebruikt worden**: nieuwe
  onderdelen worden eerst in die reststukken gelegd (in de plaat zelf, met
  extra zaagsnedes na de bestaande), daarna in reststukken uit de
  bibliotheek, daarna op volle platen.
- **Gezaagd maar niet meer nodig**: die stukken worden gemeld; de UI laat
  per stuk kiezen tussen bewaren als reststuk en afschrijven.

Een onderdeel uit de nieuwe samenstelling wordt herkend aan materiaal,
naam, herkomst, maat (rotatie maakt niet uit), kantenband, fabrieksrand en
nerfrichting (``_regel_sleutel``/``_plaatsing_sleutel``). Een onderdeel dat
van maat verandert is dus "vervallen + nieuw". Een nog niet gezaagd
onderdeel op een aangezaagde plaat dat vervalt, laat een plek over die als
reststuk op de plaat komt.

Platen die blijven staan houden hun nummer; nieuwe platen krijgen de vrije
nummers (per materiaal, reststukken apart geteld).
"""

from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field, replace

from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.optimalisatie.models import Plaatsing, Rand, Zaagsnede
from robocutter.optimalisatie.models import Reststuk as OptReststuk
from robocutter.projecten.models import Project
from robocutter.projecten.project_reststukken import _fabrieksranden_van
from robocutter.projecten.zaaglijst import ZaaglijstRegel, bouw_zaaglijst
from robocutter.projecten.zaagplannen import PlaatZaagplan, ZaagplanVoortgang, _genereer_voor_regels
from robocutter.reststukken.models import Reststuk

__all__ = [
    "BijwerkResultaat",
    "BijwerkVoorstel",
    "BlijvendePlaat",
    "VervallenStuk",
    "plaat_naam",
    "stel_bijwerking_voor",
    "werk_zaagplannen_bij",
]

_PLAAT_VOORVOEGSEL = "plaat:"


@dataclass
class BlijvendePlaat:
    plan_index: int
    naam: str
    gezaagd: int
    totaal: int


@dataclass
class VervallenStuk:
    """Een onderdeel op een aangezaagde plaat dat de nieuwe samenstelling
    niet meer nodig heeft."""

    plan_index: int
    sleutel: tuple[str, int]  # (onderdeel_id, instantie) van de Plaatsing
    naam: str
    herkomst: str
    materiaal_id: str
    breedte: float  # zoals op de plaat (x)
    hoogte: float  # y
    plaat: str
    nr: int  # positienummer op de plaat (zoals in de tabel/tekening)
    gezaagd: bool


@dataclass
class BijwerkVoorstel:
    """Wat ``werk_zaagplannen_bij`` zou doen, zonder iets te genereren."""

    blijvend: list[BlijvendePlaat] = field(default_factory=list)
    opnieuw: list[str] = field(default_factory=list)  # platen die opnieuw verdeeld worden
    erbij: list[tuple[str, int]] = field(default_factory=list)  # (omschrijving, aantal) t.o.v. het oude zaagplan
    eraf: list[tuple[str, int]] = field(default_factory=list)
    overbodig_gezaagd: list[VervallenStuk] = field(default_factory=list)
    vervallen_niet_gezaagd: list[VervallenStuk] = field(default_factory=list)
    # (omschrijving, lengte, breedte): reststukken op blijvende platen die
    # de nieuwe verdeling mag gebruiken, incl. vrijgekomen plekken.
    bruikbare_reststukken: list[tuple[str, float, float]] = field(default_factory=list)

    @property
    def is_mogelijk(self) -> bool:
        """Alleen zinvol als er iets aangezaagd is; anders gewoon opnieuw genereren."""
        return bool(self.blijvend)


@dataclass
class BijwerkResultaat:
    plannen: list[PlaatZaagplan]
    waarschuwingen: list[str]
    vervallen_platen: list[str]  # namen van oude platen die niet meer nodig zijn
    overbodig_gezaagd: list[VervallenStuk]


def plaat_naam(plan: PlaatZaagplan) -> str:
    soort = "Reststuk" if plan.is_reststuk else "Plaat"
    return f"{soort} {plan.plaat_nummer} ({plan.materiaal_naam})"


# ----------------------------------------------------------------------
# Herkennen: welk onderdeel uit de samenstelling hoort bij welke plaatsing
# ----------------------------------------------------------------------
def _sleutel(materiaal_id, naam, herkomst, breedte, hoogte, kantenband, fabriek, nerf) -> tuple:
    return (
        materiaal_id,
        naam,
        herkomst,
        tuple(sorted((round(breedte, 3), round(hoogte, 3)))),
        tuple(sorted(r.value for r in kantenband)),
        bool(fabriek),
        getattr(nerf, "value", nerf),
    )


def _regel_sleutel(regel: ZaaglijstRegel) -> tuple:
    o = regel.onderdeel
    return _sleutel(
        o.materiaal_id, o.naam, regel.herkomst, o.breedte, o.hoogte,
        o.kantenband_randen, o.fabriekskantenband_vereist, o.nerfrichting_vereist,
    )


def _plaatsing_sleutel(plan: PlaatZaagplan, p: Plaatsing) -> tuple | None:
    info = plan.onderdeel_info.get(p.onderdeel_id)
    if info is None:
        return None
    return _sleutel(
        plan.materiaal_id, info.naam, info.herkomst, p.breedte, p.hoogte,
        info.kantenband_randen, info.fabriekskantenband_vereist, info.nerfrichting_vereist,
    )


def _omschrijving(sleutel: tuple) -> str:
    _, naam, herkomst, (a, b), *_ = sleutel
    return f"{naam} ({herkomst}) {a:g} × {b:g}"


@dataclass
class _Analyse:
    blijvend: list[int]
    overbodig: list[VervallenStuk]
    vervallen: list[VervallenStuk]
    rest_vraag: Counter
    oud: Counter
    nieuw: Counter


def _analyseer(project: Project, plannen: list[PlaatZaagplan]) -> _Analyse:
    vraag = Counter()
    for regel in bouw_zaaglijst(project):
        vraag[_regel_sleutel(regel)] += regel.onderdeel.aantal
    nieuw = Counter(vraag)
    oud = Counter()
    for plan in plannen:
        for p in plan.resultaat.plaatsingen:
            sleutel = _plaatsing_sleutel(plan, p)
            if sleutel is not None:
                oud[sleutel] += 1

    blijvend = [i for i, plan in enumerate(plannen) if plan.is_aangezaagd]
    overbodig: list[VervallenStuk] = []
    vervallen: list[VervallenStuk] = []
    # Eerst alle gezaagde stukken (die liggen er al), dan de rest van de
    # blijvende platen.
    for alleen_gezaagd in (True, False):
        for i in blijvend:
            plan = plannen[i]
            for nr, p in enumerate(plan.resultaat.plaatsingen, start=1):
                is_gezaagd = (p.onderdeel_id, p.instantie) in plan.gezaagd
                if is_gezaagd != alleen_gezaagd:
                    continue
                sleutel = _plaatsing_sleutel(plan, p)
                if sleutel is not None and vraag[sleutel] > 0:
                    vraag[sleutel] -= 1
                    continue
                info = plan.onderdeel_info.get(p.onderdeel_id)
                stuk = VervallenStuk(
                    plan_index=i,
                    sleutel=(p.onderdeel_id, p.instantie),
                    naam=info.naam if info else p.onderdeel_id,
                    herkomst=info.herkomst if info else "",
                    materiaal_id=plan.materiaal_id,
                    breedte=p.breedte,
                    hoogte=p.hoogte,
                    plaat=plaat_naam(plan),
                    nr=nr,
                    gezaagd=is_gezaagd,
                )
                (overbodig if is_gezaagd else vervallen).append(stuk)
    return _Analyse(blijvend, overbodig, vervallen, +vraag, oud, nieuw)


_Stuk = tuple[float, float, float, float]  # x0, y0, x1, y1


def _afzaag(mat, rand: Rand) -> float:
    return mat.randafzaag_marge if rand in mat.randafzaag_randen and rand not in mat.fabriekskantenband_randen else 0.0


def _stukken(resultaat) -> list[_Stuk]:
    """De losse stukken plaat na de hele zaagvolgorde, zoals een paneelzaag
    ze maakt (elke snede loopt van rand tot rand door één stuk). De motor
    legt een snedepositie niet overal aan dezelfde kant van de zaagsnede,
    dus de grenzen van een reststuk volgen hieruit, niet uit de kerf."""

    m = resultaat.materiaal
    stukken: list[_Stuk] = [
        (_afzaag(m, Rand.LINKS), _afzaag(m, Rand.ONDER), m.lengte - _afzaag(m, Rand.RECHTS), m.breedte - _afzaag(m, Rand.BOVEN))
    ]
    for s in sorted(resultaat.zaagvolgorde, key=lambda z: z.volgnummer):
        for g in stukken:
            x0, y0, x1, y1 = g
            if s.richting == "verticaal":
                past = x0 < s.positie < x1 and abs(s.start - y0) < 1e-3 and abs(s.einde - y1) < 1e-3
            else:
                past = y0 < s.positie < y1 and abs(s.start - x0) < 1e-3 and abs(s.einde - x1) < 1e-3
            if past:
                stukken.remove(g)
                if s.richting == "verticaal":
                    stukken += [(x0, y0, s.positie, y1), (s.positie, y0, x1, y1)]
                else:
                    stukken += [(x0, y0, x1, s.positie), (x0, s.positie, x1, y1)]
                break
    return stukken


def _eigen_stuk(resultaat, r: OptReststuk, negeer: set[tuple[str, int]]) -> _Stuk | None:
    """Het stuk plaat waarin reststuk ``r`` los ligt, of ``None`` als er
    ook een onderdeel (buiten ``negeer``) of een ander reststuk in ligt:
    dan kun je er niet van rand tot rand in zagen."""

    k = resultaat.materiaal.kerf + 1e-6
    e = 1e-6
    binnen = [
        g for g in _stukken(resultaat)
        if g[0] - k <= r.x and r.x + r.breedte <= g[2] + k and g[1] - k <= r.y and r.y + r.hoogte <= g[3] + k
    ]
    if not binnen:
        return None
    g = min(binnen, key=lambda g: (g[2] - g[0]) * (g[3] - g[1]))

    def raakt(x, y, b, h) -> bool:
        return x < g[2] - e and x + b > g[0] + e and y < g[3] - e and y + h > g[1] + e

    if any(raakt(p.x, p.y, p.breedte, p.hoogte) for p in resultaat.plaatsingen if (p.onderdeel_id, p.instantie) not in negeer):
        return None
    if any(raakt(x.x, x.y, x.breedte, x.hoogte) for x in resultaat.reststukken if x != r):
        return None
    return g


def _bruikbare_plaatreststukken(
    plannen: list[PlaatZaagplan],
    analyse: _Analyse,
    bruikbaar: Callable[[PlaatZaagplan, OptReststuk], bool],
) -> list[tuple[int, OptReststuk, bool, _Stuk]]:
    """(plan_index, reststuk, is_vrijgekomen_plek, stuk plaat) op blijvende
    platen: alleen reststukken die een eigen stuk plaat zijn."""

    uit: list[tuple[int, OptReststuk, bool, _Stuk]] = []
    for i in analyse.blijvend:
        plan = plannen[i]
        weg = {s.sleutel for s in analyse.overbodig + analyse.vervallen if s.plan_index == i}
        kandidaten = [(r, False) for r in plan.resultaat.reststukken if bruikbaar(plan, r)]
        for stuk in analyse.vervallen:
            if stuk.plan_index == i:
                p = next(p for p in plan.resultaat.plaatsingen if (p.onderdeel_id, p.instantie) == stuk.sleutel)
                kandidaten.append((OptReststuk(p.x, p.y, p.breedte, p.hoogte), True))
        for r, vrijgekomen in kandidaten:
            g = _eigen_stuk(plan.resultaat, r, weg)
            if g is not None:
                uit.append((i, r, vrijgekomen, g))
    return uit


def stel_bijwerking_voor(
    project: Project,
    plannen: list[PlaatZaagplan],
    bruikbaar: Callable[[PlaatZaagplan, OptReststuk], bool] = lambda plan, r: True,
) -> BijwerkVoorstel:
    """Overzicht voor het bijwerk-paneel: welke platen blijven staan, wat
    opnieuw verdeeld wordt, welke reststukken meedoen en welke gezaagde
    stukken niet meer nodig zijn. ``bruikbaar`` filtert reststukken op
    blijvende platen (bv. alleen die nog op Bewaren staan)."""

    analyse = _analyseer(project, plannen)
    voorstel = BijwerkVoorstel(
        blijvend=[
            BlijvendePlaat(i, plaat_naam(plannen[i]), plannen[i].aantal_gezaagd, len(plannen[i].resultaat.plaatsingen))
            for i in analyse.blijvend
        ],
        opnieuw=[plaat_naam(p) for i, p in enumerate(plannen) if i not in analyse.blijvend],
        erbij=sorted((_omschrijving(k), n) for k, n in (analyse.nieuw - analyse.oud).items()),
        eraf=sorted((_omschrijving(k), n) for k, n in (analyse.oud - analyse.nieuw).items()),
        overbodig_gezaagd=analyse.overbodig,
        vervallen_niet_gezaagd=analyse.vervallen,
    )
    for i, r, vrijgekomen, _ in _bruikbare_plaatreststukken(plannen, analyse, bruikbaar):
        bron = plaat_naam(plannen[i])
        voorstel.bruikbare_reststukken.append(
            (f"{bron}, vrijgekomen plek" if vrijgekomen else bron, r.breedte, r.hoogte)
        )
    return voorstel


# ----------------------------------------------------------------------
# Bijwerken
# ----------------------------------------------------------------------
def werk_zaagplannen_bij(
    project: Project,
    plannen: list[PlaatZaagplan],
    materialen: MaterialenBibliotheek,
    strategie: str = "horizontaal",
    revisie: str = "",
    zoek_tijdsbudget: float = 0.0,
    min_zoek_tijdsbudget: float = 0.0,
    voortgang: Callable[[ZaagplanVoortgang], None] | None = None,
    zaagsnede: float = 3.0,
    reststukken: list[Reststuk] | None = None,
    bruikbaar: Callable[[PlaatZaagplan, OptReststuk], bool] = lambda plan, r: True,
) -> BijwerkResultaat:
    """Werkt ``plannen`` bij naar de huidige samenstelling van ``project``
    (zie de module-docstring). ``reststukken``: kandidaten uit de
    Reststukkenbibliotheek, zoals bij ``genereer_zaagplannen_voor_project``.
    ``plannen`` zelf wordt niet gewijzigd."""

    analyse = _analyseer(project, plannen)
    plaatreststukken = _bruikbare_plaatreststukken(plannen, analyse, bruikbaar)

    # 1. Blijvende platen: wat vervalt eraf; een vrijgekomen plek wordt een
    #    reststuk op de plaat.
    weg: dict[int, set[tuple[str, int]]] = {}
    for stuk in analyse.overbodig + analyse.vervallen:
        weg.setdefault(stuk.plan_index, set()).add(stuk.sleutel)
    blijvend: dict[int, PlaatZaagplan] = {}
    for i in analyse.blijvend:
        plan = deepcopy(plannen[i])
        verwijderd = weg.get(i, set())
        vrij = [p for p in plan.resultaat.plaatsingen if (p.onderdeel_id, p.instantie) in verwijderd
                and (p.onderdeel_id, p.instantie) not in plan.gezaagd]
        plan.resultaat.plaatsingen = [
            p for p in plan.resultaat.plaatsingen if (p.onderdeel_id, p.instantie) not in verwijderd
        ]
        plan.resultaat.reststukken = list(plan.resultaat.reststukken) + [
            OptReststuk(p.x, p.y, p.breedte, p.hoogte) for p in vrij
        ]
        plan.gezaagd = {k for k in plan.gezaagd if k not in verwijderd}
        plan.bijwerking = "gebleven"
        plan.toegevoegd = set()
        plan.onderdeel_info = dict(plan.onderdeel_info)
        blijvend[i] = plan

    # 2. Wat nog niet gedekt is: de zaaglijstregels met het resterende aantal.
    rest = Counter(analyse.rest_vraag)
    te_genereren: list[ZaaglijstRegel] = []
    for regel in bouw_zaaglijst(project):
        sleutel = _regel_sleutel(regel)
        aantal = min(regel.onderdeel.aantal, rest[sleutel])
        if aantal > 0:
            rest[sleutel] -= aantal
            te_genereren.append(replace(regel, onderdeel=replace(regel.onderdeel, aantal=aantal)))

    # 3. Kandidaat-reststukken: eerst die op blijvende platen (als
    #    bibliotheek-Reststuk met een herkenbaar id), dan de bibliotheek.
    kandidaten: list[Reststuk] = []
    plaatrest_per_id: dict[str, tuple[int, OptReststuk, _Stuk]] = {}
    for n, (i, r, _, g) in enumerate(plaatreststukken):
        plan = blijvend[i]
        mat = plan.resultaat.materiaal
        rid = f"{_PLAAT_VOORVOEGSEL}{i}:{n}"
        plaatrest_per_id[rid] = (i, r, g)
        kandidaten.append(
            Reststuk(
                id=rid,
                materiaal_id=plan.materiaal_id,
                lengte=r.breedte,
                breedte=r.hoogte,
                fabriekskantenband_randen=_fabrieksranden_van(
                    r.x, r.y, r.breedte, r.hoogte, mat.lengte, mat.breedte, mat.fabriekskantenband_randen
                ),
            )
        )
    kandidaten.extend(reststukken or [])

    nieuw: list[PlaatZaagplan] = []
    waarschuwingen: list[str] = []
    if te_genereren:
        nieuw, waarschuwingen = _genereer_voor_regels(
            te_genereren,
            materialen,
            strategie=strategie,
            zoek_tijdsbudget=zoek_tijdsbudget,
            min_zoek_tijdsbudget=min_zoek_tijdsbudget,
            voortgang=voortgang,
            zaagsnede=zaagsnede,
            reststukken=kandidaten,
            revisie=revisie,
            # Uniek t.o.v. de onderdeel-id's op blijvende platen: hun labels
            # (scancode met onderdeel-id + instantie) blijven geldig.
            id_voorvoegsel=f"b{uuid.uuid4().hex[:4]}r",
        )

    # 4. Wat in een reststuk van een blijvende plaat kwam: in die plaat zelf.
    gebruikte_plaatrest: set[str] = set()
    losse_nieuwe: list[PlaatZaagplan] = []
    for plan in nieuw:
        if plan.reststuk_id and plan.reststuk_id in plaatrest_per_id:
            i, r, g = plaatrest_per_id[plan.reststuk_id]
            _voeg_in(blijvend[i], plan, r, g, revisie)
            gebruikte_plaatrest.add(plan.reststuk_id)
        else:
            plan.bijwerking = "nieuw"
            losse_nieuwe.append(plan)
    for rid in gebruikte_plaatrest:
        i, r, _ = plaatrest_per_id[rid]
        blijvend[i].resultaat.reststukken = [x for x in blijvend[i].resultaat.reststukken if x != r]

    # 5. Nummering: blijvende platen houden hun nummer, nieuwe vullen de
    #    vrije nummers (per materiaal, reststukken apart).
    resultaat = list(blijvend.values())
    for plan in losse_nieuwe:
        groep = (plan.materiaal_id, plan.is_reststuk)
        bezet = {p.plaat_nummer for p in resultaat if (p.materiaal_id, p.is_reststuk) == groep}
        nummer = 1
        while nummer in bezet:
            nummer += 1
        plan.plaat_nummer = nummer
        resultaat.append(plan)
    for plan in resultaat:
        groep = (plan.materiaal_id, plan.is_reststuk)
        plan.platen_totaal = sum(1 for p in resultaat if (p.materiaal_id, p.is_reststuk) == groep)
    volgorde_materiaal = {m: n for n, m in enumerate(dict.fromkeys(p.materiaal_id for p in plannen + resultaat))}
    resultaat.sort(key=lambda p: (volgorde_materiaal[p.materiaal_id], not p.is_reststuk, p.plaat_nummer))

    nu = {(p.materiaal_id, p.is_reststuk, p.plaat_nummer) for p in resultaat}
    vervallen_platen = [
        plaat_naam(p)
        for i, p in enumerate(plannen)
        if i not in blijvend and (p.materiaal_id, p.is_reststuk, p.plaat_nummer) not in nu
    ]
    return BijwerkResultaat(resultaat, waarschuwingen, vervallen_platen, analyse.overbodig)


def _oorsprong(resultaat, r: OptReststuk, stuk: _Stuk) -> tuple[float, float]:
    """Waar het materiaal van reststuk ``r`` echt begint. Zaagplannen van
    vóór 2026-10-07 legden het reststuk rechts in een rij een zaagsnede te
    ver naar links (x op de snede, rechterrand een kerf vóór de plaatrand;
    bij "verticaal" hetzelfde in y). Dat patroon wordt hier rechtgezet."""

    m = resultaat.materiaal
    e = 1e-3
    x, y = r.x, r.y
    if stuk[0] > _afzaag(m, Rand.LINKS) + e and abs(r.x - stuk[0]) < e and abs(r.x + r.breedte - (stuk[2] - m.kerf)) < e:
        x += m.kerf
    if stuk[1] > _afzaag(m, Rand.ONDER) + e and abs(r.y - stuk[1]) < e and abs(r.y + r.hoogte - (stuk[3] - m.kerf)) < e:
        y += m.kerf
    return x, y


def _voeg_in(plaat: PlaatZaagplan, sub: PlaatZaagplan, r: OptReststuk, stuk: _Stuk, revisie: str) -> None:
    """Legt het resultaat van een generatie op reststuk ``r`` terug in de
    blijvende ``plaat``: plaatsingen, reststukken en zaagsnedes verschoven
    naar plaatcoördinaten, de snedes genummerd na de bestaande."""

    res = plaat.resultaat
    dx, dy = _oorsprong(res, r, stuk)
    # Meerdere reststukken van dezelfde plaat kunnen hetzelfde onderdeel-id
    # krijgen: exemplaren doornummeren, zodat (id, instantie) uniek blijft.
    for p in sub.resultaat.plaatsingen:
        instantie = 1 + max((q.instantie for q in res.plaatsingen if q.onderdeel_id == p.onderdeel_id), default=0)
        res.plaatsingen.append(replace(p, x=p.x + dx, y=p.y + dy, instantie=instantie))
        plaat.toegevoegd.add((p.onderdeel_id, instantie))
    res.reststukken.extend(OptReststuk(x.x + dx, x.y + dy, x.breedte, x.hoogte) for x in sub.resultaat.reststukken)
    # Een snede loopt van rand tot rand van het stuk plaat waar het
    # reststuk los in ligt (zie _stukken): een eindpunt op de rand van het
    # reststuk komt op de rand van dat stuk.
    links, onder, rechts, boven = stuk

    def naar_x(v: float) -> float:
        return links if v <= 1e-6 else (rechts if v >= r.breedte - 1e-6 else v + dx)

    def naar_y(v: float) -> float:
        return onder if v <= 1e-6 else (boven if v >= r.hoogte - 1e-6 else v + dy)

    start = max((s.volgnummer for s in res.zaagvolgorde), default=0)
    for s in sub.resultaat.zaagvolgorde:
        if s.richting == "verticaal":
            nieuw = Zaagsnede(start + s.volgnummer, s.richting, s.positie + dx, naar_y(s.start), naar_y(s.einde))
        else:
            nieuw = Zaagsnede(start + s.volgnummer, s.richting, s.positie + dy, naar_x(s.start), naar_x(s.einde))
        res.zaagvolgorde.append(nieuw)
    res.afval_oppervlak += sub.resultaat.afval_oppervlak
    plaat.onderdeel_info.update(sub.onderdeel_info)
    plaat.revisie = revisie or plaat.revisie
