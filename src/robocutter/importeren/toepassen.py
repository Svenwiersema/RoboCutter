"""Gelezen importregels (``lezen.py``) met hun materiaalkoppeling
(``koppelen.py``) controleren en omzetten naar onderdelen, en die in een
project of model zetten (hoofdstuk 10).

In een project maakt de kolom Model het verschil: regels met dezelfde
modelnaam worden samen één modelkopie (``ProjectModelInstantie`` zonder
bibliotheekmodel, ``model_id`` leeg) met het modelaantal; regels zonder
modelnaam worden losse onderdelen. In een model worden alle regels gewoon
onderdelen van dat model.

Maten: Lengte (horizontaal) wordt ``ModelOnderdeel.breedte`` (x), Breedte
(verticaal) wordt ``hoogte`` (y), zodat de kantenbandletters B/O/L/R op
dezelfde randen blijven. Bij een balk komt de hoogte van de balk zelf en
vervallen nerf, kantenband, fabrieksrand en groep (zoals in de
onderdeelformulieren).
"""

from __future__ import annotations

import uuid
from dataclasses import replace

from robocutter.importeren.koppelen import normaliseer
from robocutter.importeren.models import Ernst, ImportMelding, ImportRegel
from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.materialen.models import Materiaal, MateriaalStatus, MateriaalType
from robocutter.modellen.bibliotheek import ModellenBibliotheek
from robocutter.modellen.models import Model, ModelOnderdeel, Nerfrichting
from robocutter.projecten.bibliotheek import ProjectenBibliotheek
from robocutter.projecten.models import Project, ProjectModelInstantie

__all__ = ["controleer", "importeer_in_model", "importeer_in_project", "maak_onderdeel"]


def _materiaal(regel: ImportRegel, koppeling: dict[str, str | None], materialen: MaterialenBibliotheek) -> Materiaal | None:
    materiaal_id = koppeling.get(normaliseer(regel.materiaal))
    if not materiaal_id:
        return None
    try:
        return materialen.ophalen(materiaal_id)
    except KeyError:
        return None


def controleer(
    regels: list[ImportRegel], koppeling: dict[str, str | None], materialen: MaterialenBibliotheek
) -> list[ImportMelding]:
    """Alles wat er per regel mis is: de problemen uit het lezen plus wat
    pas blijkt nu het materiaal bekend is. Fouten houden het importeren
    tegen tot ze zijn aangevuld (of de regel wordt overgeslagen);
    waarschuwingen niet. Elke melding noemt zo mogelijk de kolom die
    aangevuld moet worden."""
    meldingen: list[ImportMelding] = []
    niet_gekoppeld: dict[str, list[int]] = {}
    for regel in regels:
        for kolom, tekst in regel.problemen.items():
            meldingen.append(ImportMelding(tekst, Ernst.FOUT, regel.regelnummer, kolom))
        if not regel.materiaal:
            continue
        m = _materiaal(regel, koppeling, materialen)
        if m is None:
            niet_gekoppeld.setdefault(regel.materiaal, []).append(regel.regelnummer)
            continue
        if m.status != MateriaalStatus.ACTIEF:
            meldingen.append(ImportMelding(f"Materiaal '{m.naam}' is gearchiveerd.", Ernst.WAARSCHUWING, regel.regelnummer))
        if m.type == MateriaalType.BALK:
            genegeerd = [
                naam
                for naam, gezet in (
                    ("breedte", regel.breedte is not None and regel.breedte != m.breedte),
                    ("nerf", regel.nerf != Nerfrichting.GEEN),
                    ("kantenband", bool(regel.kantenband)),
                    ("fabriekskantenband", regel.fabriekskantenband),
                    ("groep", bool(regel.groep)),
                )
                if gezet
            ]
            if genegeerd:
                meldingen.append(ImportMelding(
                    f"'{m.naam}' is een balk: {', '.join(genegeerd)} vervalt, alleen de lengte telt.",
                    Ernst.WAARSCHUWING,
                    regel.regelnummer,
                ))
            if regel.lengte is not None and regel.lengte > m.lengte:
                meldingen.append(ImportMelding(
                    f"{regel.naam} ({regel.lengte:g} mm) is langer dan een balk {m.naam} ({m.lengte:g} mm).",
                    Ernst.WAARSCHUWING,
                    regel.regelnummer,
                    "Lengte",
                ))
            continue
        if regel.breedte is None:
            if "Breedte" not in regel.problemen:
                meldingen.append(ImportMelding(
                    f"Breedte is leeg, maar '{m.naam}' is een plaat.", Ernst.FOUT, regel.regelnummer, "Breedte"
                ))
            continue
        if regel.lengte is None:
            continue
        lang, kort = max(regel.lengte, regel.breedte), min(regel.lengte, regel.breedte)
        if lang > max(m.lengte, m.breedte) or kort > min(m.lengte, m.breedte):
            meldingen.append(ImportMelding(
                f"{regel.naam} ({regel.lengte:g} × {regel.breedte:g} mm) past niet op een plaat {m.naam} "
                f"({m.lengte:g} × {m.breedte:g} mm).",
                Ernst.WAARSCHUWING,
                regel.regelnummer,
            ))
    for tekst, nummers in niet_gekoppeld.items():
        meldingen.append(ImportMelding(
            f"Materiaal '{tekst}' is niet gevonden in de materialenbibliotheek (regel {_regels_tekst(nummers)}). Kies het juiste materiaal.",
            Ernst.FOUT,
            kolom="Materiaal",
        ))
    return meldingen


def _regels_tekst(nummers: list[int]) -> str:
    return ", ".join(str(n) for n in nummers[:6]) + (" …" if len(nummers) > 6 else "")


def maak_onderdeel(regel: ImportRegel, materiaal: Materiaal) -> ModelOnderdeel:
    if materiaal.type == MateriaalType.BALK:
        return ModelOnderdeel(
            id=uuid.uuid4().hex[:8],
            naam=regel.naam,
            materiaal_id=materiaal.id,
            breedte=regel.lengte,
            hoogte=materiaal.breedte,
            aantal=regel.aantal,
        )
    return ModelOnderdeel(
        id=uuid.uuid4().hex[:8],
        naam=regel.naam,
        materiaal_id=materiaal.id,
        breedte=regel.lengte,
        hoogte=regel.breedte or 0.0,
        aantal=regel.aantal,
        nerfrichting_vereist=regel.nerf,
        kantenband_randen=regel.kantenband,
        fabriekskantenband_vereist=regel.fabriekskantenband,
        groep_id=regel.groep or None,
        groep_volgorde=regel.volgorde if regel.groep else None,
    )


def _onderdelen(
    regels: list[ImportRegel], koppeling: dict[str, str | None], materialen: MaterialenBibliotheek
) -> list[tuple[ImportRegel, ModelOnderdeel]]:
    fouten = [m for m in controleer(regels, koppeling, materialen) if m.ernst == Ernst.FOUT]
    if fouten:
        raise ValueError("; ".join(m.tekst for m in fouten))
    return [(r, maak_onderdeel(r, _materiaal(r, koppeling, materialen))) for r in regels]


def importeer_in_project(
    projecten: ProjectenBibliotheek,
    project_id: str,
    regels: list[ImportRegel],
    koppeling: dict[str, str | None],
    materialen: MaterialenBibliotheek,
) -> Project:
    """Voegt de regels toe aan het project: per modelnaam één modelkopie,
    de rest als losse onderdelen. ``ValueError`` bij een fout (bv. een
    niet-gekoppeld materiaal); dan verandert er niets."""
    paren = _onderdelen(regels, koppeling, materialen)
    instanties: dict[str, ProjectModelInstantie] = {}
    losse: list[ModelOnderdeel] = []
    for regel, onderdeel in paren:
        if not regel.model:
            losse.append(onderdeel)
            continue
        sleutel = regel.model.casefold()
        if sleutel not in instanties:
            instanties[sleutel] = ProjectModelInstantie(
                id=uuid.uuid4().hex[:8], model_id="", model_naam=regel.model, aantal=regel.modelaantal
            )
        instanties[sleutel].onderdelen.append(onderdeel)
    return projecten.voeg_import_toe(project_id, list(instanties.values()), losse)


def importeer_in_model(
    modellen: ModellenBibliotheek,
    model_id: str,
    regels: list[ImportRegel],
    koppeling: dict[str, str | None],
    materialen: MaterialenBibliotheek,
) -> Model:
    """Voegt alle regels als onderdelen aan het model toe (de kolommen
    Model en Modelaantal tellen hier niet)."""
    paren = _onderdelen(regels, koppeling, materialen)
    model = modellen.ophalen(model_id)
    return modellen.bijwerken(replace(model, onderdelen=[*model.onderdelen, *(o for _, o in paren)]))
