"""Leest een bestand in het RoboCutter-importformaat (hoofdstuk 10): CSV of
Excel (.xlsx), eerste regel de kop, één onderdeel per regel.

Meldingen over het bestand komen terug als ``ImportMelding`` (nooit als
exceptie of pop-up, zelfde principe als ``valideer`` in de bibliotheken).
Een regel met een fout blijft bewaard met zijn ``problemen`` per kolom, om
in het importscherm aan te vullen (``lees_regel`` leest hem daarna
opnieuw); ontbreekt een verplichte kolom, dan komt er geen regel terug.
"""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path

from robocutter.importeren.models import Ernst, ImportMelding, ImportRegel, LeesResultaat
from robocutter.modellen.models import Nerfrichting, Rand

__all__ = ["KOLOMMEN", "VERPLICHTE_KOLOMMEN", "lees_bestand", "lees_csv", "lees_regel", "lees_rijen", "lees_xlsx", "schrijf_sjabloon"]

# Kolomnamen zoals in het sjabloon, in die volgorde (hoofdstuk 10).
KOLOMMEN = (
    "Naam", "Materiaal", "Lengte", "Breedte", "Aantal", "Model", "Modelaantal",
    "Nerf", "Kantenband", "Fabriekskantenband", "Groep", "Volgorde",
)
VERPLICHTE_KOLOMMEN = ("Naam", "Materiaal", "Lengte")

_UITLEG = {
    "Naam": "Naam van het onderdeel, bv. Zijkant links",
    "Materiaal": "Productcode of naam uit de materialenbibliotheek",
    "Lengte": "mm, horizontaal in de tekening (langs de randen B en O)",
    "Breedte": "mm, verticaal (langs de randen L en R); leeg bij een balk",
    "Aantal": "Aantal stuks per model (standaard 1)",
    "Model": "Modelnaam; leeg = los onderdeel",
    "Modelaantal": "Hoe vaak het model in het project zit (standaard 1)",
    "Nerf": "lang, kort of leeg: welke zijde langs de nerf",
    "Kantenband": "Randen met kantenband: B (boven), O (onder), L (links), R (rechts), bv. BO",
    "Fabriekskantenband": "ja als het onderdeel een fabriekskantenband nodig heeft",
    "Groep": "Groepsnaam: vaste volgorde, doorlopende nerf",
    "Volgorde": "Plaats binnen de groep",
}

_RANDLETTERS = {"B": Rand.BOVEN, "O": Rand.ONDER, "L": Rand.LINKS, "R": Rand.RECHTS}
_NERF = {
    "": Nerfrichting.GEEN, "geen": Nerfrichting.GEEN,
    "lang": Nerfrichting.LANGE_ZIJDE, "lange zijde": Nerfrichting.LANGE_ZIJDE,
    "kort": Nerfrichting.KORTE_ZIJDE, "korte zijde": Nerfrichting.KORTE_ZIJDE,
}
_JA = {"ja", "j", "x", "1", "waar", "true", "yes", "y"}
_NEE = {"", "nee", "n", "0", "onwaar", "false", "no"}


def _sleutel(kop: str) -> str:
    return re.sub(r"[\s_\-]+", "", kop).casefold()


_KOLOM_PER_SLEUTEL = {_sleutel(k): k for k in KOLOMMEN}


def lees_bestand(pad: str | Path) -> LeesResultaat:
    pad = Path(pad)
    if pad.suffix.lower() == ".csv":
        return lees_csv(pad)
    if pad.suffix.lower() in (".xlsx", ".xlsm"):
        return lees_xlsx(pad)
    return LeesResultaat(meldingen=[ImportMelding(f"Onbekend bestandstype '{pad.suffix}': kies een .csv- of .xlsx-bestand.")])


def lees_csv(pad: str | Path) -> LeesResultaat:
    data = Path(pad).read_bytes()
    try:
        tekst = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        # Excel op Windows bewaart CSV vaak in Windows-1252.
        tekst = data.decode("cp1252")
    # Scheidingsteken uit de kopregel: ";" (Nederlandse Excel), "," of tab.
    kop = tekst.split("\n", 1)[0]
    scheiding = max(";,\t", key=kop.count) if any(t in kop for t in ";,\t") else ";"
    return lees_rijen(list(csv.reader(io.StringIO(tekst), delimiter=scheiding)))


def lees_xlsx(pad: str | Path) -> LeesResultaat:
    from openpyxl import load_workbook

    try:
        boek = load_workbook(pad, read_only=True, data_only=True)
    except Exception as exc:  # beschadigd of geen echt .xlsx-bestand
        return LeesResultaat(meldingen=[ImportMelding(f"Het Excel-bestand kan niet gelezen worden ({exc}).")])
    try:
        blad = boek.worksheets[0]
        rijen = [["" if c is None else c for c in rij] for rij in blad.iter_rows(values_only=True)]
    finally:
        boek.close()
    return lees_rijen(rijen)


def lees_rijen(rijen: list[list[object]]) -> LeesResultaat:
    """De kern: de rijen van een bestand (kop eerst), als tekst of getal."""
    resultaat = LeesResultaat()
    meldingen = resultaat.meldingen
    while rijen and all(_tekst(c) == "" for c in rijen[0]):
        rijen = rijen[1:]
    if not rijen:
        meldingen.append(ImportMelding("Het bestand is leeg."))
        return resultaat

    kolom_index: dict[str, int] = {}
    for i, kop in enumerate(rijen[0]):
        kop_tekst = _tekst(kop)
        if not kop_tekst:
            continue
        kolom = _KOLOM_PER_SLEUTEL.get(_sleutel(kop_tekst))
        if kolom is None:
            meldingen.append(ImportMelding(f"Kolom '{kop_tekst}' wordt niet gebruikt.", Ernst.WAARSCHUWING))
        elif kolom in kolom_index:
            meldingen.append(ImportMelding(f"Kolom '{kolom}' staat er twee keer in; de eerste wordt gebruikt.", Ernst.WAARSCHUWING))
        else:
            kolom_index[kolom] = i
    ontbreekt = [k for k in VERPLICHTE_KOLOMMEN if k not in kolom_index]
    if ontbreekt:
        meldingen.append(ImportMelding(
            f"Verplichte kolom{'men' if len(ontbreekt) > 1 else ''} ontbreekt: {', '.join(ontbreekt)}. "
            "Gebruik het RoboCutter-sjabloon voor de juiste kolomnamen."
        ))
        return resultaat

    for nummer, rij in enumerate(rijen[1:], start=2):
        waarden = {k: _tekst(rij[i] if i < len(rij) else "") for k, i in kolom_index.items()}
        if all(v == "" for v in waarden.values()):
            continue
        resultaat.regels.append(lees_regel(nummer, waarden))

    if not resultaat.regels:
        meldingen.append(ImportMelding("Het bestand bevat geen onderdelen."))
    _controleer_modelaantallen(resultaat)
    return resultaat


def lees_regel(nummer: int, waarden: dict[str, str]) -> ImportRegel:
    """Eén regel uit de tekst per kolom. Altijd een regel terug: wat niet
    klopt staat in ``problemen`` (per kolom), zodat het importscherm het
    kan laten aanvullen en deze functie daarna opnieuw kan aanroepen."""
    w = {k: _tekst(v) for k, v in waarden.items()}
    problemen: dict[str, str] = {}
    naam = w.get("Naam", "")
    materiaal = w.get("Materiaal", "")
    if not naam:
        problemen["Naam"] = "Naam is leeg."
    if not materiaal:
        problemen["Materiaal"] = "Materiaal is leeg."
    lengte = _getal(w.get("Lengte"), "Lengte", problemen, verplicht=True)
    breedte = _getal(w.get("Breedte"), "Breedte", problemen, verplicht=False)
    if lengte is not None and lengte <= 0:
        problemen["Lengte"] = "Lengte moet groter dan 0 zijn."
        lengte = None
    if breedte is not None and breedte <= 0:
        problemen["Breedte"] = "Breedte moet groter dan 0 zijn (laat hem leeg bij een balk)."
        breedte = None
    aantal = _geheel(w.get("Aantal"), "Aantal", problemen, standaard=1, minimum=1)
    modelaantal = _geheel(w.get("Modelaantal"), "Modelaantal", problemen, standaard=1, minimum=1)

    nerf = _NERF.get(w.get("Nerf", "").casefold())
    if nerf is None:
        problemen["Nerf"] = f"Nerf '{w['Nerf']}' is onbekend: gebruik lang, kort of laat hem leeg."
        nerf = Nerfrichting.GEEN

    kantenband: set[Rand] = set()
    for teken in re.sub(r"[\s,;/+\-]", "", w.get("Kantenband", "")).upper():
        if teken not in _RANDLETTERS:
            problemen["Kantenband"] = f"Kantenband '{w['Kantenband']}' is onbekend: gebruik de letters B, O, L en R."
            kantenband = set()
            break
        kantenband.add(_RANDLETTERS[teken])

    fabriek_tekst = w.get("Fabriekskantenband", "").casefold()
    if fabriek_tekst not in _JA | _NEE:
        problemen["Fabriekskantenband"] = (
            f"Fabriekskantenband '{w['Fabriekskantenband']}' is onbekend: gebruik ja of laat hem leeg."
        )

    groep = w.get("Groep", "")
    volgorde = _geheel(w.get("Volgorde"), "Volgorde", problemen, standaard=None, minimum=0)
    if groep and volgorde is None:
        volgorde = 0

    return ImportRegel(
        regelnummer=nummer,
        naam=naam,
        materiaal=materiaal,
        lengte=lengte,
        breedte=breedte,
        aantal=aantal,
        model=w.get("Model", ""),
        modelaantal=modelaantal,
        nerf=nerf,
        kantenband=frozenset(kantenband),
        fabriekskantenband=fabriek_tekst in _JA,
        groep=groep,
        volgorde=volgorde if groep else None,
        waarden=w,
        problemen=problemen,
    )


def _controleer_modelaantallen(resultaat: LeesResultaat) -> None:
    eerste: dict[str, ImportRegel] = {}
    for regel in resultaat.regels:
        if not regel.model:
            continue
        sleutel = regel.model.casefold()
        if sleutel not in eerste:
            eerste[sleutel] = regel
        elif regel.modelaantal != eerste[sleutel].modelaantal:
            resultaat.meldingen.append(ImportMelding(
                f"Model '{regel.model}' heeft hier modelaantal {regel.modelaantal}, maar op regel "
                f"{eerste[sleutel].regelnummer} {eerste[sleutel].modelaantal}; {eerste[sleutel].modelaantal} wordt gebruikt.",
                Ernst.WAARSCHUWING,
                regel.regelnummer,
                "Modelaantal",
            ))
            regel.modelaantal = eerste[sleutel].modelaantal


def _tekst(waarde: object) -> str:
    if waarde is None:
        return ""
    if isinstance(waarde, float) and waarde.is_integer():
        return str(int(waarde))
    return str(waarde).strip()


def _getal(waarde: object, kolom: str, problemen: dict[str, str], verplicht: bool) -> float | None:
    tekst = _tekst(waarde).replace(" ", "").replace("mm", "")
    if not tekst:
        if verplicht:
            problemen[kolom] = f"{kolom} is leeg."
        return None
    # "1.200,5" (Nederlands) en "1200.5" allebei goed lezen.
    if "," in tekst:
        tekst = tekst.replace(".", "").replace(",", ".")
    try:
        return float(tekst)
    except ValueError:
        problemen[kolom] = f"{kolom} '{_tekst(waarde)}' is geen getal."
        return None


def _geheel(waarde: object, kolom: str, problemen: dict[str, str], standaard: int | None, minimum: int) -> int | None:
    getal = _getal(waarde, kolom, problemen, verplicht=False)
    if getal is None:
        return standaard
    if not float(getal).is_integer() or getal < minimum:
        problemen[kolom] = f"{kolom} '{_tekst(waarde)}' moet een geheel getal van minstens {minimum} zijn."
        return standaard
    return int(getal)


def schrijf_sjabloon(pad: str | Path) -> None:
    """Een leeg Excel-sjabloon: de kop op het eerste blad, uitleg per kolom
    op een tweede blad."""
    from openpyxl import Workbook
    from openpyxl.styles import Font

    boek = Workbook()
    blad = boek.active
    blad.title = "Onderdelen"
    blad.append(list(KOLOMMEN))
    for cel in blad[1]:
        cel.font = Font(bold=True)
    for i, kolom in enumerate(KOLOMMEN, start=1):
        blad.column_dimensions[blad.cell(row=1, column=i).column_letter].width = max(12, len(kolom) + 4)
    blad.freeze_panes = "A2"
    uitleg = boek.create_sheet("Uitleg")
    uitleg.append(["Kolom", "Verplicht", "Inhoud"])
    for cel in uitleg[1]:
        cel.font = Font(bold=True)
    for kolom in KOLOMMEN:
        verplicht = "ja" if kolom in VERPLICHTE_KOLOMMEN else ("ja, behalve bij een balk" if kolom == "Breedte" else "nee")
        uitleg.append([kolom, verplicht, _UITLEG[kolom]])
    uitleg.column_dimensions["A"].width = 20
    uitleg.column_dimensions["B"].width = 24
    uitleg.column_dimensions["C"].width = 80
    boek.save(pad)
