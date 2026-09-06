"""Visuele demo van de zaagplan-optimalisatie-motor.

Genereert voor alle vier strategieën een PNG op basis van dezelfde
testcase als de eerdere handgemaakte voorbeelden
(design/voorbeelden/zaagplan-voorbeeld-v1.pdf en -v2.pdf), zodat de
algoritme-output visueel te vergelijken is met die eerdere concepten.

Let op: "stroken" en "guillotine" zijn bewust minder efficiënt dan
"efficient"/"rijen" (zie de module-docstring van
``robocutter.optimalisatie.engine``) en laten voor deze specifieke,
krap-passende testcase een deel van de onderdelen onplaatsbaar — dat is
zichtbaar in de gegenereerde PNG's als de "Niet geplaatst"-regel
onderaan, geen bug.

Gebruik: python3 scripts/demo_render.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from robocutter.optimalisatie.engine import genereer_zaagplan  # noqa: E402
from robocutter.optimalisatie.models import Materiaal, Onderdeel  # noqa: E402

ACCENT = (95, 127, 255)
DARK = (22, 23, 29)
SUCCESS = (111, 207, 151)
WASTE = (225, 227, 232)
SCHAAL = 0.35  # px per mm


def render(resultaat, bestandsnaam: str, titel: str) -> None:
    mat = resultaat.materiaal
    breedte_px = int(mat.lengte * SCHAAL) + 80
    hoogte_px = int(mat.breedte * SCHAAL) + 140

    img = Image.new("RGB", (breedte_px, hoogte_px), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        font_klein = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except Exception:
        font = ImageFont.load_default()
        font_klein = font

    ox, oy = 40, 60
    draw.text((ox, 15), titel, fill=DARK, font=font)
    draw.text(
        (ox, 36),
        f"{mat.naam} — {mat.lengte:.0f}×{mat.breedte:.0f}mm — kerf {mat.kerf:.0f}mm — "
        f"benutting {resultaat.benuttingspercentage}%",
        fill=(107, 111, 122),
        font=font_klein,
    )

    def naar_px(x, y, w, h):
        # y-as omdraaien: model-y=0 is "onder", beeld-y=0 is "boven".
        py = oy + (mat.breedte - y - h) * SCHAAL
        return ox + x * SCHAAL, py, ox + (x + w) * SCHAAL, py + h * SCHAAL

    # Plaatcontour
    x0, y0, x1, y1 = naar_px(0, 0, mat.lengte, mat.breedte)
    draw.rectangle([x0, y0, x1, y1], outline=DARK, width=3)

    for p in resultaat.plaatsingen:
        rx0, ry0, rx1, ry1 = naar_px(p.x, p.y, p.breedte, p.hoogte)
        draw.rectangle([rx0, ry0, rx1, ry1], outline=ACCENT, width=2, fill=(240, 242, 255))
        label = f"{p.onderdeel_id} #{p.instantie}"
        draw.text(((rx0 + rx1) / 2, (ry0 + ry1) / 2), label, fill=DARK, font=font_klein, anchor="mm")

    for r in resultaat.reststukken:
        rx0, ry0, rx1, ry1 = naar_px(r.x, r.y, r.breedte, r.hoogte)
        draw.rectangle([rx0, ry0, rx1, ry1], outline=SUCCESS, width=2, fill=(232, 247, 238))
        draw.text(((rx0 + rx1) / 2, (ry0 + ry1) / 2), "♻ reststuk", fill=(46, 125, 79), font=font_klein, anchor="mm")

    # Zaagvolgorde als genummerde stippen op de sneden.
    for snede in resultaat.zaagvolgorde:
        if snede.richting == "verticaal":
            mx, my = snede.positie, (snede.start + snede.einde) / 2
        else:
            mx, my = (snede.start + snede.einde) / 2, snede.positie
        cx, cy, _, _ = naar_px(mx, my, 0, 0)
        r = 11
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=DARK)
        draw.text((cx, cy), str(snede.volgnummer), fill="white", font=font_klein, anchor="mm")

    if resultaat.niet_geplaatst:
        draw.text(
            (ox, hoogte_px - 24),
            f"⚠ Niet geplaatst: {', '.join(resultaat.niet_geplaatst)}",
            fill=(178, 58, 58),
            font=font_klein,
        )

    img.save(bestandsnaam)
    print(f"Opgeslagen: {bestandsnaam}")


def main():
    mat = Materiaal(naam="Wit gemelamineerd 18mm", lengte=2800, breedte=2070, dikte=18, kerf=4, min_reststukgrootte=300)
    onderdelen = [
        Onderdeel(id="zijpaneel", breedte=850, hoogte=902, aantal=3),
        Onderdeel(id="bodemplaat", breedte=1200, hoogte=700, aantal=2),
        Onderdeel(id="rugpaneel", breedte=1390, hoogte=460, aantal=2),
    ]

    out = Path(__file__).resolve().parent.parent / "output"
    out.mkdir(exist_ok=True)

    r1 = genereer_zaagplan(mat, onderdelen, strategie="efficient")
    render(r1, str(out / "demo_efficient.png"), "Zaagplan — strategie: meest efficiënte plaatsing")

    r2 = genereer_zaagplan(mat, onderdelen, strategie="rijen")
    render(r2, str(out / "demo_rijen.png"), "Zaagplan — strategie: lange zijdes eerst")

    r1b = genereer_zaagplan(mat, onderdelen, strategie="stroken")
    render(r1b, str(out / "demo_stroken.png"), "Zaagplan — strategie: stroken (vaste strookhoogte)")

    r1c = genereer_zaagplan(mat, onderdelen, strategie="guillotine")
    render(r1c, str(out / "demo_guillotine.png"), "Zaagplan — strategie: guillotine (rand-tot-rand sneden)")

    # Derde demo: groepering voor doorlopende nerf (3 ladefronten).
    mat2 = Materiaal(naam="Eiken fineer 19mm", lengte=1600, breedte=1500, dikte=19, kerf=4, min_reststukgrootte=250)
    onderdelen2 = [
        # groep_volgorde=1 komt onderin de kast, aflopend hoger genummerd naar boven toe.
        Onderdeel(id="ladefront-1-onder", breedte=596, hoogte=220, groep_id="lades-onderkast", groep_volgorde=1),
        Onderdeel(id="ladefront-2-midden", breedte=596, hoogte=180, groep_id="lades-onderkast", groep_volgorde=2),
        Onderdeel(id="ladefront-3-boven", breedte=596, hoogte=180, groep_id="lades-onderkast", groep_volgorde=3),
        Onderdeel(id="zijpaneel-kast", breedte=560, hoogte=720, aantal=2),
    ]
    r3 = genereer_zaagplan(mat2, onderdelen2, strategie="efficient")
    render(r3, str(out / "demo_groepering.png"), "Zaagplan — groep 'lades-onderkast' (vaste volgorde/nerf)")


if __name__ == "__main__":
    main()
