"""De zaaglijst: de gecombineerde onderdelenlijst van een project (alle
model-snapshots én losse onderdelen samen), met multi-criteria
sortering.

Op Svens verzoek moet de gebruiker de zaaglijst op meerdere criteria
tegelijk kunnen sorteren, bijvoorbeeld eerst op materiaal en dan op
breedte — ``sorteer_zaaglijst`` doet dat door een samengestelde
sorteersleutel te bouwen uit een geordende lijst sleutelnamen.

Hoofdstuk 5's regel dat een groep (``groep_id``) nooit onderdelen uit
verschillende modellen combineert, hoeft hier niet apart afgedwongen te
worden: dat is al een invariant van hoe modellen zelf gevalideerd
worden (hoofdstuk 2, cirkelverwijzing- en veldvalidatie) — deze module
leest die data alleen maar.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.modellen.models import ModelOnderdeel
from robocutter.projecten.models import Project

__all__ = ["ZaaglijstRegel", "bouw_zaaglijst", "sorteer_zaaglijst", "OnbekendeSorteersleutelError", "SORTEERSLEUTELS"]


class OnbekendeSorteersleutelError(Exception):
    """Een gevraagde sorteersleutel staat niet in ``SORTEERSLEUTELS``."""


@dataclass
class ZaaglijstRegel:
    """Eén regel in de zaaglijst: een onderdeel plus waar het vandaan
    komt (een model-instantie, of rechtstreeks als los onderdeel)."""

    onderdeel: ModelOnderdeel
    herkomst: str


def bouw_zaaglijst(project: Project) -> list[ZaaglijstRegel]:
    """Voegt alle model-snapshots (aantal vermenigvuldigd met de
    instantie zelf, bovenop wat er bij het platslaan al doorgerekend is
    voor eventuele nesting) en losse onderdelen samen tot één lijst."""

    regels: list[ZaaglijstRegel] = []
    for instantie in project.modelinstanties:
        for onderdeel in instantie.onderdelen:
            regels.append(
                ZaaglijstRegel(
                    onderdeel=replace(onderdeel, aantal=onderdeel.aantal * instantie.aantal),
                    herkomst=instantie.model_naam,
                )
            )
    for onderdeel in project.losse_onderdelen:
        regels.append(ZaaglijstRegel(onderdeel=onderdeel, herkomst="Los onderdeel"))
    return regels


def _materiaal_naam(materiaal_id: str, materialen: MaterialenBibliotheek) -> str:
    try:
        return materialen.ophalen(materiaal_id).naam
    except KeyError:
        return materiaal_id


SORTEERSLEUTELS = {
    "materiaal": lambda regel, materialen: _materiaal_naam(regel.onderdeel.materiaal_id, materialen).lower(),
    "naam": lambda regel, materialen: regel.onderdeel.naam.lower(),
    "breedte": lambda regel, materialen: regel.onderdeel.breedte,
    "hoogte": lambda regel, materialen: regel.onderdeel.hoogte,
    "aantal": lambda regel, materialen: regel.onderdeel.aantal,
    "herkomst": lambda regel, materialen: regel.herkomst.lower(),
}


def sorteer_zaaglijst(
    regels: list[ZaaglijstRegel], sleutels: list[str], materialen: MaterialenBibliotheek
) -> list[ZaaglijstRegel]:
    """Sorteert op een geordende lijst sleutels, bv. ``["materiaal",
    "breedte"]`` sorteert eerst op materiaalnaam, en binnen elk
    materiaal op breedte — precies "sorteren op meerdere criteria"."""

    onbekend = [s for s in sleutels if s not in SORTEERSLEUTELS]
    if onbekend:
        raise OnbekendeSorteersleutelError(f"Onbekende sorteersleutel(s): {', '.join(onbekend)}")

    def sleutel(regel: ZaaglijstRegel) -> tuple:
        return tuple(SORTEERSLEUTELS[s](regel, materialen) for s in sleutels)

    return sorted(regels, key=sleutel)
