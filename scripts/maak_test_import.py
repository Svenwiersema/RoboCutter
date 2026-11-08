"""Maakt een test-importbestand (Excel) met bewust een paar fouten, om het
importvenster (hoofdstuk 10) mee uit te proberen.

Gebruikt materiaalnamen uit Svens eigen bibliotheek (stand 2026-11-08):
Meubelpaneel wit 18, MDF water werend 18, Melamine grijs 18, HDF wit 5,
Vuren regel 44×68 en Grenen lat 18×44. Het tweede blad ("Wat is er fout")
somt de fouten op; RoboCutter leest alleen het eerste blad.

Draaien: python scripts/maak_test_import.py
Schrijft: data/import_test/test-import-met-fouten.xlsx (gitignored)
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from openpyxl import Workbook  # noqa: E402
from openpyxl.styles import Font, PatternFill  # noqa: E402

from robocutter.importeren.lezen import KOLOMMEN  # noqa: E402

_DOEL = _REPO_ROOT / "data" / "import_test" / "test-import-met-fouten.xlsx"

# Kolommen: de 12 van het formaat + een onbekende kolom "Opmerking".
_KOP = [*KOLOMMEN, "Opmerking"]

# (rij, fout of None). Rij in de volgorde van _KOP.
_RIJEN: list[tuple[list, str | None]] = [
    # Onderkast 60 ×3 — goed, op één fout na
    (["Zijkant", "Meubelpaneel wit 18", 720, 560, 2, "Onderkast 60", 3, "lang", "B", "", "", "", ""], None),
    (["Bodem", "Meubelpaneel wit 18", 564, 560, 1, "Onderkast 60", 3, "", "B", "", "", "", ""], None),
    (["Achterwand", "HDF wit 5", 716, 596, 1, "Onderkast 60", 3, "", "", "", "", "", ""], None),
    (["Legplank", "Meubelpaneel wit 18", 562, None, 1, "Onderkast 60", 3, "", "B", "", "", "", "breedte vergeten"],
     "Breedte is leeg bij een plaat (aanvullen)"),
    # Bovenkast 80 ×2 — modelaantal klopt niet overal, typfout in materiaal
    (["Zijkant", "Meubelpanel wit 18", 720, 320, 2, "Bovenkast 80", 2, "lang", "B", "", "", "", ""],
     "Typfout in materiaal 'Meubelpanel' (koppelen, 'Bedoelde je…?')"),
    (["Bodem", "Meubelpaneel wit 18", 764, 320, 2, "Bovenkast 80", 3, "", "B", "", "", "", ""],
     "Modelaantal 3 i.p.v. 2 (waarschuwing, eerste telt)"),
    (["Deur", "MDF  water WEREND 18", 716, "39,6 cm", 2, "Bovenkast 80", 2, "lang", "BOLR", "", "", "", ""],
     "Breedte '39,6 cm' is geen getal in mm (aanvullen); materiaal met rare spaties/hoofdletters wordt wél herkend"),
    # Ladekast ×1 — fronten als groep, diverse foute waarden
    (["Front lade 1", "MDF water werend 18", 596, 180, 1, "Ladekast", 1, "lang", "BOLR", "", "Fronten", 1], None),
    (["Front lade 2", "MDF water werend 18", 596, 180, 0, "Ladekast", 1, "lang", "BOLR", "", "Fronten", 2],
     "Aantal 0 (aanvullen)"),
    (["Front lade 3", "MDF water werend 18", 596, 356, 1, "Ladekast", 1, "schuin", "BOLR", "", "Fronten", 3],
     "Nerf 'schuin' (aanvullen: lang, kort of leeg)"),
    (["Ladebodem", "Melamine grijs 18", 520, 480, 3, "Ladekast", 1, "", "BX", "", "", "", ""],
     "Kantenband 'BX' (aanvullen: letters B, O, L, R)"),
    (["Ladezijkant", "Melamine grijs 18", 500, 150, 6, "Ladekast", 1, "", "B", "misschien", "", "", ""],
     "Fabriekskantenband 'misschien' (aanvullen: ja of leeg)"),
    # Losse onderdelen
    (["", "Meubelpaneel wit 18", 900, 560, 1, "", "", "", "BO", "", "", "", ""], "Naam is leeg (aanvullen of overslaan)"),
    (["Werkblad", "Beuken massief 26", 2600, 620, 1, "", "", "lang", "", "", "", "", ""],
     "Materiaal 'Beuken massief 26' bestaat niet (koppelen aan een ander materiaal, of regel overslaan)"),
    (["Zijpaneel hoge kast", "Meubelpaneel wit 18", 2950, 600, 2, "", "", "lang", "", "", "", "", ""],
     "Langer dan een plaat Meubelpaneel wit 18 (2800 × 600): waarschuwing, past niet"),
    (["Plintregel", "Vuren regel 44x68", 2400, 68, 2, "", "", "lang", "", "", "", "", ""],
     "Balk met nerf ingevuld (waarschuwing: vervalt, alleen de lengte telt); 'x' i.p.v. '×' wordt herkend"),
    (["Ophangregel", "Vuren regel 44×68", 1200, None, 2, "", "", "", "", "", "", "", ""], None),
    (["Afwerklat", "Grenen lat 18×44", 2100, None, 2, "", "", "", "", "", "", "", ""], None),
    (["Stelregel", "Vuren regel 44×68", "", None, 6, "", "", "", "", "", "", "", ""], "Lengte is leeg (aanvullen)"),
]


def main() -> None:
    _DOEL.parent.mkdir(parents=True, exist_ok=True)
    boek = Workbook()
    blad = boek.active
    blad.title = "Onderdelen"
    blad.append(_KOP)
    for cel in blad[1]:
        cel.font = Font(bold=True)
    geel = PatternFill("solid", fgColor="FFF2CC")
    for rij, fout in _RIJEN:
        blad.append(rij)
        if fout:
            for cel in blad[blad.max_row]:
                cel.fill = geel
    for i, kolom in enumerate(_KOP, start=1):
        blad.column_dimensions[blad.cell(row=1, column=i).column_letter].width = max(12, len(kolom) + 4)
    blad.column_dimensions["A"].width = 22
    blad.column_dimensions["B"].width = 24
    blad.freeze_panes = "A2"

    uitleg = boek.create_sheet("Wat is er fout")
    uitleg.append(["Regel", "Naam", "Bewuste fout"])
    for cel in uitleg[1]:
        cel.font = Font(bold=True)
    for nummer, (rij, fout) in enumerate(_RIJEN, start=2):
        if fout:
            uitleg.append([nummer, rij[0] or "(leeg)", fout])
    uitleg.append([])
    uitleg.append(["", "Hele bestand", "Kolom 'Opmerking' bestaat niet in het formaat (waarschuwing)"])
    uitleg.column_dimensions["B"].width = 24
    uitleg.column_dimensions["C"].width = 100
    boek.save(_DOEL)
    print(_DOEL)


if __name__ == "__main__":
    main()
