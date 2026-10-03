"""Zaagplan-generatie voor een project: groepeert de zaaglijst (module
1/4) per materiaal en roept voor elke groep de optimalisatie-motor
(hoofdstuk 5) aan.

Een materiaal levert zoveel ``PlaatZaagplan``-items op als de motor
platen nodig heeft om alle onderdelen ervoor te plaatsen (onbeperkte
voorraad aangenomen — zie ``engine.genereer_zaagplannen``). Elk item is
één fysieke plaat, met ``plaat_nummer``/``platen_totaal`` om dat in de UI
te kunnen tonen ("Plaat 2 van 3"). Onderdelen die zelfs op een lege plaat
niet passen (te groot voor het materiaal) komen terecht in
``ZaagplanResultaat.niet_geplaatst`` van de laatste plaat.

Reststukken eerst (op Svens verzoek: de motor "hoort eerst reststukken te
controleren voordat hij volle platen pakt"): krijgt deze module
``reststukken`` uit de Reststukkenbibliotheek mee, dan probeert hij per
materiaal eerst die stukken, kleinste eerst (zo blijven grote reststukken
over voor grote onderdelen), zonder randafzaag (een reststuk is al recht
gezaagd). Onderdelen met een fabriekskantenband-eis (en hun groep) gaan
alleen op een reststuk dat zelf nog een fabrieksrand heeft
(``Reststuk.fabriekskantenband_randen``). Elk reststuk waar iets op past
wordt een eigen
``PlaatZaagplan`` met ``reststuk_id``; wat overblijft gaat naar volle
platen. Het reserveren in de bibliotheek doet de aanroeper (zie
``ReststukkenBibliotheek.wijs_toe_aan_project``).

Geen persistentie/revisiegeschiedenis hier: dat is expliciet uitgesteld
(zie OVERDRACHT.md, "Nog niet gebouwd") zolang de motor zelf nog actief
bijgeschaafd wordt — een gegenereerd zaagplan leeft alleen in het
geheugen van het scherm dat het opvraagt, en wordt bij elke klik op
"(Opnieuw) genereren" gewoon opnieuw berekend.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace

from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.modellen.models import Nerfrichting, Rand
from robocutter.optimalisatie.engine import (
    _onderdelen_voor_niet_geplaatst,
    genereer_zaagplan,
    genereer_zaagplannen,
    schat_aantal_platen,
)
from robocutter.optimalisatie.models import Materiaal as OptMateriaal
from robocutter.optimalisatie.models import Onderdeel as OptOnderdeel
from robocutter.optimalisatie.models import ZaagplanResultaat
from robocutter.projecten.models import Project
from robocutter.projecten.zaaglijst import ZaaglijstRegel, bouw_zaaglijst
from robocutter.reststukken.models import Reststuk

__all__ = ["OnderdeelInfo", "PlaatZaagplan", "ZaagplanVoortgang", "genereer_zaagplannen_voor_project"]


@dataclass
class OnderdeelInfo:
    """Weergave-informatie voor één regel uit de zaaglijst, apart
    bewaard omdat de motor zelf alleen het lean ``OptOnderdeel`` (met
    een synthetische id) ziet en niets van naam/herkomst afweet.

    ``nerfrichting_vereist`` is hier toegevoegd voor de labelgeneratie
    (hoofdstuk 6): de optionele nerfrichting-pijl op een label leest
    dit veld, in plaats van dat labels.py zelf opnieuw bij de
    modellen-/projectenbibliotheek moet gaan opzoeken welk onderdeel dit
    was."""

    naam: str
    herkomst: str
    kantenband_randen: frozenset[Rand]
    fabriekskantenband_vereist: bool
    nerfrichting_vereist: Nerfrichting = Nerfrichting.GEEN


@dataclass
class PlaatZaagplan:
    """Eén gegenereerde, fysieke plaat voor één materiaal binnen een
    project. Een materiaal dat niet op één plaat past levert meerdere
    ``PlaatZaagplan``-items op (zelfde ``materiaal_id``, oplopende
    ``plaat_nummer``), zie ``genereer_zaagplannen_voor_project``."""

    materiaal_id: str
    materiaal_naam: str
    resultaat: ZaagplanResultaat
    plaat_nummer: int = 1
    platen_totaal: int = 1
    onderdeel_info: dict[str, OnderdeelInfo] = field(default_factory=dict)
    # Gezaagd uit dit reststuk uit de Reststukkenbibliotheek i.p.v. een
    # volle plaat; plaat_nummer/platen_totaal tellen dan de reststukken.
    reststuk_id: str | None = None

    @property
    def is_reststuk(self) -> bool:
        return self.reststuk_id is not None

    def naam_voor(self, onderdeel_of_unit_id: str) -> str:
        """Zoekt de leesbare naam op voor een ``Plaatsing.onderdeel_id``
        of een ruwe ``niet_geplaatst``-unit-id (die voor een groep de
        vorm ``"groep:<groep_id>"`` heeft, en voor een los onderdeel
        ``"<onderdeel_id>#<instantie>"``)."""

        basis_id = onderdeel_of_unit_id.split("#", 1)[0]
        if basis_id in self.onderdeel_info:
            return self.onderdeel_info[basis_id].naam
        if basis_id.startswith("groep:"):
            return f"Groep {basis_id.removeprefix('groep:')}"
        return onderdeel_of_unit_id

    def reden_voor(self, niet_geplaatst_unit_id: str) -> str:
        """Leesbare uitleg waarom deze ``niet_geplaatst``-unit-id niet op
        deze plaat geplaatst kon worden, zie
        ``ZaagplanResultaat.niet_geplaatst_redenen``. Lege string als er
        (onverwacht) geen reden voor bekend is."""

        return self.resultaat.niet_geplaatst_redenen.get(niet_geplaatst_unit_id, "")


@dataclass(frozen=True)
class ZaagplanVoortgang:
    """Tussenstand tijdens ``genereer_zaagplannen_voor_project``, voor de
    voortgangsbalk in de UI.

    ``fractie`` (0.0-1.0, nooit dalend) weegt elke plaat even zwaar —
    elke plaat kost ongeveer even veel zoektijd (de minimale denktijd) —
    over alle materialen van het project samen. Hoeveel platen een
    materiaal nodig heeft staat pas vast als dat materiaal klaar is;
    tot dan wordt ``engine.schat_aantal_platen`` gebruikt, dus de balk
    kan even stilstaan (schatting te laag) of een sprongetje maken
    (schatting te hoog)."""

    fractie: float
    materiaal_nummer: int
    materiaal_totaal: int
    materiaal_naam: str
    plaat_nummer: int


def _naar_optimalisatie_materiaal(
    materiaal_id: str, materialen: MaterialenBibliotheek, kerf: float
) -> OptMateriaal | None:
    try:
        m = materialen.ophalen(materiaal_id)
    except KeyError:
        return None
    return OptMateriaal(
        naam=m.naam,
        lengte=m.lengte,
        breedte=m.breedte,
        dikte=m.derde_afmeting,
        kerf=kerf,
        randafzaag_marge=m.randafzaag_marge,
        randafzaag_randen=m.randafzaag_randen,
        min_reststukgrootte=m.min_reststukgrootte,
        fabriekskantenband_randen=m.fabriekskantenband_randen,
    )


def genereer_zaagplannen_voor_project(
    project: Project,
    materialen: MaterialenBibliotheek,
    strategie: str = "horizontaal",
    zoek_tijdsbudget: float = 0.0,
    min_zoek_tijdsbudget: float = 0.0,
    voortgang: Callable[[ZaagplanVoortgang], None] | None = None,
    zaagsnede: float = 3.0,
    reststukken: list[Reststuk] | None = None,
) -> tuple[list[PlaatZaagplan], list[str]]:
    """Genereert één of meer ``PlaatZaagplan``-items per materiaal dat in
    de zaaglijst van ``project`` voorkomt — meerdere zodra de onderdelen
    voor dat materiaal niet op één plaat passen (zie
    ``engine.genereer_zaagplannen``). Retourneert daarnaast een lijst
    Nederlandse waarschuwingen voor materialen die niet meer bestaan
    (bv. inmiddels verwijderd uit de bibliotheek) — diezelfde
    onderdelen worden dan overgeslagen in plaats van de hele generatie
    te laten crashen.

    :param zoek_tijdsbudget: zie ``engine.genereer_zaagplan`` — geldt
        hier PER MATERIAAL (elk materiaal in de zaaglijst is een eigen,
        onafhankelijk pak-probleem en krijgt dus zijn eigen budget, niet
        een gedeeld totaal over alle materialen samen).
    :param min_zoek_tijdsbudget: zie ``engine.genereer_zaagplannen`` —
        wordt hier ook per materiaal/plaat toegepast.
    :param voortgang: optionele callback die tussentijds een
        ``ZaagplanVoortgang`` krijgt (vanaf de thread waarop deze functie
        draait).
    :param zaagsnede: zaagsnede-breedte (mm) uit de instellingen (op Svens
        verzoek niet meer per materiaal) — wordt de ``kerf`` van de motor.
    :param reststukken: reststukken die vóór volle platen geprobeerd worden
        (zie de module-docstring); alleen die met hetzelfde ``materiaal_id``
        tellen per materiaal."""

    per_materiaal: dict[str, list[ZaaglijstRegel]] = {}
    for regel in bouw_zaaglijst(project):
        per_materiaal.setdefault(regel.onderdeel.materiaal_id, []).append(regel)

    plannen: list[PlaatZaagplan] = []
    waarschuwingen: list[str] = []
    # Eerst alles omzetten, pas daarna genereren: de voortgangsbalk heeft
    # vooraf het (geschatte) aantal platen van álle materialen nodig.
    te_genereren: list[tuple[str, OptMateriaal, dict[str, OnderdeelInfo], list[OptOnderdeel]]] = []

    for materiaal_id, regels in per_materiaal.items():
        opt_materiaal = _naar_optimalisatie_materiaal(materiaal_id, materialen, zaagsnede)
        if opt_materiaal is None:
            waarschuwingen.append(
                f"Materiaal '{materiaal_id}' bestaat niet (meer) in de materialenbibliotheek — "
                f"{len(regels)} onderdeel(en) hierop overgeslagen."
            )
            continue

        onderdeel_info: dict[str, OnderdeelInfo] = {}
        opt_onderdelen: list[OptOnderdeel] = []
        for i, regel in enumerate(regels):
            oid = f"r{i}"
            onderdeel_info[oid] = OnderdeelInfo(
                naam=regel.onderdeel.naam,
                herkomst=regel.herkomst,
                kantenband_randen=regel.onderdeel.kantenband_randen,
                fabriekskantenband_vereist=regel.onderdeel.fabriekskantenband_vereist,
                nerfrichting_vereist=regel.onderdeel.nerfrichting_vereist,
            )
            opt_onderdelen.append(
                OptOnderdeel(
                    id=oid,
                    breedte=regel.onderdeel.breedte,
                    hoogte=regel.onderdeel.hoogte,
                    aantal=regel.onderdeel.aantal,
                    nerfrichting_vereist=regel.onderdeel.nerfrichting_vereist,
                    kantenband_randen=regel.onderdeel.kantenband_randen,
                    fabriekskantenband_vereist=regel.onderdeel.fabriekskantenband_vereist,
                    groep_id=regel.onderdeel.groep_id,
                    groep_volgorde=regel.onderdeel.groep_volgorde,
                )
            )

        te_genereren.append((materiaal_id, opt_materiaal, onderdeel_info, opt_onderdelen))

    # Per materiaal: het echte aantal platen zodra het klaar is, tot dan
    # de schatting (zie ZaagplanVoortgang).
    platen_per_materiaal = [schat_aantal_platen(m, o) for _, m, _, o in te_genereren]
    hoogste_fractie = 0.0

    for index, (materiaal_id, opt_materiaal, onderdeel_info, opt_onderdelen) in enumerate(te_genereren):

        def meld(plaat_nummer: int, plaat_fractie: float, index=index, naam=opt_materiaal.naam) -> None:
            nonlocal hoogste_fractie
            platen_hier = max(platen_per_materiaal[index], plaat_nummer)
            totaal = sum(platen_per_materiaal[:index]) + platen_hier + sum(platen_per_materiaal[index + 1 :])
            voltooid = sum(platen_per_materiaal[:index]) + (plaat_nummer - 1) + plaat_fractie
            hoogste_fractie = max(hoogste_fractie, min(1.0, voltooid / totaal))
            voortgang(
                ZaagplanVoortgang(
                    fractie=hoogste_fractie,
                    materiaal_nummer=index + 1,
                    materiaal_totaal=len(te_genereren),
                    materiaal_naam=naam,
                    plaat_nummer=plaat_nummer,
                )
            )

        # Onderdelen met een fabriekskantenband-eis (en hun hele groep)
        # mogen alleen op een reststuk dat nog een fabrieksrand heeft —
        # zonder fabrieksrand negeert de motor die eis anders stilletjes.
        fabriek_groepen = {o.groep_id for o in opt_onderdelen if o.groep_id and o.fabriekskantenband_vereist}

        def vraagt_fabrieksrand(o: OptOnderdeel) -> bool:
            return o.fabriekskantenband_vereist or bool(o.groep_id and o.groep_id in fabriek_groepen)

        resterend = list(opt_onderdelen)
        rest_plannen: list[PlaatZaagplan] = []
        eigen_reststukken = sorted(
            (r for r in (reststukken or []) if r.materiaal_id == materiaal_id and r.lengte > 0 and r.breedte > 0),
            key=lambda r: (r.lengte * r.breedte, r.id),
        )
        for reststuk in eigen_reststukken:
            if not resterend:
                break
            rest_materiaal = replace(
                opt_materiaal,
                lengte=reststuk.lengte,
                breedte=reststuk.breedte,
                randafzaag_marge=0.0,
                randafzaag_randen=frozenset(),
                fabriekskantenband_randen=reststuk.fabriekskantenband_randen,
            )
            if reststuk.fabriekskantenband_randen:
                proberen, overslaan = resterend, []
            else:
                proberen = [o for o in resterend if not vraagt_fabrieksrand(o)]
                overslaan = [o for o in resterend if vraagt_fabrieksrand(o)]
            if not proberen:
                continue
            resultaat = genereer_zaagplan(rest_materiaal, proberen, strategie=strategie)
            if not resultaat.plaatsingen:
                continue
            resterend = overslaan + _onderdelen_voor_niet_geplaatst(proberen, resultaat.niet_geplaatst)
            rest_plannen.append(
                PlaatZaagplan(
                    materiaal_id=materiaal_id,
                    materiaal_naam=opt_materiaal.naam,
                    resultaat=replace(resultaat, niet_geplaatst=[], niet_geplaatst_redenen={}),
                    onderdeel_info=onderdeel_info,
                    reststuk_id=reststuk.id,
                )
            )
        for i, plan in enumerate(rest_plannen, start=1):
            plan.plaat_nummer, plan.platen_totaal = i, len(rest_plannen)
        plannen.extend(rest_plannen)
        if not resterend:
            platen_per_materiaal[index] = 0
            continue

        resultaten = genereer_zaagplannen(
            opt_materiaal,
            resterend,
            strategie=strategie,
            zoek_tijdsbudget=zoek_tijdsbudget,
            min_zoek_tijdsbudget=min_zoek_tijdsbudget,
            voortgang=meld if voortgang is not None else None,
        )
        platen_per_materiaal[index] = len(resultaten)
        for i, resultaat in enumerate(resultaten, start=1):
            plannen.append(
                PlaatZaagplan(
                    materiaal_id=materiaal_id,
                    materiaal_naam=opt_materiaal.naam,
                    resultaat=resultaat,
                    plaat_nummer=i,
                    platen_totaal=len(resultaten),
                    onderdeel_info=onderdeel_info,
                )
            )

    return plannen, waarschuwingen
