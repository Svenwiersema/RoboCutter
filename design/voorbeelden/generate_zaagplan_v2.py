"""
RoboCutter - voorbeeld zaagplan (mockup) - VARIANT B
Zelfde project/plaat als variant A, maar met een andere zaagstrategie:
"lange zijdes eerst" - het programma zoekt onderdelen met gelijke
breedte/hoogte en groepeert ze in volledige-breedte rijen over de lange
zijde van de plaat. Eerst de lange, volledige-breedte sneden (de rijen
scheiden), daarna pas de kortere sneden om de rijen in losse onderdelen
te verdelen. Dit in tegenstelling tot variant A, waar de sneden per
onderdeel-cluster afwisselden (een "zigzag"-patroon).

Zelfde lay-outregels als variant A:
- plaat neemt het grootste deel van de pagina in
- volledige-breedte onderdelentabel eronder
- smalle footer met projectgegevens + QR
- geen legenda, iconen alleen waar ze iets toevoegen
- benutting als percentage
- zaagsnede-nummering volgt de werkelijke zaagvolgorde
- fabrieks-kantenband nooit afgezaagd, blijft zichtbaar op onderdelen
"""

from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, black, white

PAGE_W, PAGE_H = landscape(A3)  # points

# ---- kleuren ----
INK = HexColor("#1a1a1a")
LINE = HexColor("#333333")
FACTORY_EDGE = HexColor("#111111")
PART_FILL = HexColor("#eef2f6")
OFFCUT_FILL = HexColor("#e6f4ea")
WASTE_FILL = HexColor("#f5f5f5")
GRID = HexColor("#999999")
HEADER_BG = HexColor("#1a1a1a")

c = canvas.Canvas("/home/claude/robocutter-design/zaagplan_mockup/RoboCutter_Zaagplan_voorbeeld_v2.pdf", pagesize=(PAGE_W, PAGE_H))

MARGIN = 10 * mm

# ---------------------------------------------------------------
# Titelbalk
# ---------------------------------------------------------------
title_h = 12 * mm
title_y = PAGE_H - MARGIN - title_h

c.setFillColor(HEADER_BG)
c.rect(MARGIN, title_y, PAGE_W - 2 * MARGIN, title_h, fill=1, stroke=0)

c.setFillColor(white)
c.setFont("Helvetica-Bold", 15)
c.drawString(MARGIN + 4 * mm, title_y + 3.3 * mm, "ZAAGPLAN")

c.setFont("Helvetica", 10)
c.drawString(MARGIN + 40 * mm, title_y + 3.6 * mm, "Project: Keuken – Jansen")
c.drawString(MARGIN + 110 * mm, title_y + 3.6 * mm, "Model: Onderkast-serie 60/90")
c.drawString(MARGIN + 200 * mm, title_y + 3.6 * mm, "Rev. A")

c.setFont("Helvetica", 10)
right_text = "Zaagplan 3 van 5  ·  variant: lange zijdes eerst"
c.drawRightString(PAGE_W - MARGIN - 4 * mm, title_y + 3.6 * mm, right_text)

# ---------------------------------------------------------------
# Zones verdelen
# ---------------------------------------------------------------
gap = 4 * mm
footer_h = 17 * mm
table_h = 52 * mm

plate_zone_top = title_y - gap
plate_zone_bottom = MARGIN + footer_h + gap + table_h + gap
plate_zone_h = plate_zone_top - plate_zone_bottom
plate_zone_w = PAGE_W - 2 * MARGIN

table_top = plate_zone_bottom - gap
table_bottom = MARGIN + footer_h + gap

footer_top = MARGIN + footer_h
footer_bottom = MARGIN

# ---------------------------------------------------------------
# Plaat tekenen (2800 x 2070 mm werkelijk - zelfde plaat as variant A)
# ---------------------------------------------------------------
PLATE_W_MM, PLATE_H_MM = 2800.0, 2070.0
KERF = 4.0  # mm, uit de materialenbibliotheek

scale = min(plate_zone_w / (PLATE_W_MM * mm), plate_zone_h / (PLATE_H_MM * mm))
draw_w = PLATE_W_MM * mm * scale
draw_h = PLATE_H_MM * mm * scale
plate_x0 = MARGIN + (plate_zone_w - draw_w) / 2
plate_y0 = plate_zone_bottom + (plate_zone_h - draw_h) / 2


def to_page(x_mm, y_mm):
    """Plaat-lokale mm-coördinaten (0,0 = linksonder) naar pagina-punten."""
    return plate_x0 + x_mm * mm * scale, plate_y0 + y_mm * mm * scale


def draw_check_icon(cx, cy, r=3.2 * mm):
    """Vector checkmark-badge (geen font-emoji, dus altijd consistent)."""
    c.setFillColor(HexColor("#2e7d46"))
    c.circle(cx, cy, r, fill=1, stroke=0)
    c.setStrokeColor(white)
    c.setLineWidth(1.3)
    c.line(cx - r * 0.45, cy - r * 0.05, cx - r * 0.1, cy - r * 0.4)
    c.line(cx - r * 0.1, cy - r * 0.4, cx + r * 0.5, cy + r * 0.35)


def draw_rect_mm(x, y, w, h, fill_color, label=None, icon=None, sub=None, badge=False):
    x0, y0 = to_page(x, y)
    w_pt = w * mm * scale
    h_pt = h * mm * scale
    c.setFillColor(fill_color)
    c.setStrokeColor(GRID)
    c.setLineWidth(0.6)
    c.rect(x0, y0, w_pt, h_pt, fill=1, stroke=1)
    if label:
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(x0 + w_pt / 2, y0 + h_pt / 2 + 3, label)
    if badge:
        draw_check_icon(x0 + w_pt / 2 + 8 * mm, y0 + h_pt / 2 + 6.5, )
    if icon == "waste":
        # eenvoudige vuilnisbak-vorm i.p.v. font-emoji
        bx, by = x0 + w_pt / 2, y0 + h_pt / 2 - 4
        c.setStrokeColor(HexColor("#888888"))
        c.setFillColor(HexColor("#888888"))
        c.setLineWidth(1.1)
        c.rect(bx - 3.2 * mm, by - 4 * mm, 6.4 * mm, 5.5 * mm, fill=0, stroke=1)
        c.line(bx - 4.2 * mm, by + 1.7 * mm, bx + 4.2 * mm, by + 1.7 * mm)
        c.line(bx - 1.6 * mm, by + 1.7 * mm, bx - 1.6 * mm, by + 3.2 * mm)
        c.line(bx + 1.6 * mm, by + 1.7 * mm, bx + 1.6 * mm, by + 3.2 * mm)
    if sub:
        c.setFont("Helvetica", 7.5)
        c.setFillColor(HexColor("#555555"))
        c.drawCentredString(x0 + w_pt / 2, y0 + h_pt / 2 - 20, sub)


# Buitenrand van de plaat
plate_x0_pt, plate_y0_pt = to_page(0, 0)
c.setFillColor(white)
c.setStrokeColor(LINE)
c.setLineWidth(1.2)
c.rect(plate_x0_pt, plate_y0_pt, draw_w, draw_h, fill=1, stroke=1)

# ---------------------------------------------------------------
# Onderdelen: gegroepeerd in 3 rijen over de volle breedte (2800mm),
# elke rij bevat onderdelen met dezelfde hoogte. Rij A (boven) raakt de
# fabrieks-kantenband.
# ---------------------------------------------------------------
# elk: (x, y, w, h, label, icon, sub)
parts = [
    # Rij A - boven, hoogte 902mm, raakt fabrieksrand
    (0,    1168, 850, 902, "1", "✅", "850×902"),
    (854,  1168, 850, 902, "2", "✅", "850×902"),
    (1708, 1168, 850, 902, "3", "✅", "850×902"),
    # Rij B - midden, hoogte 700mm
    (0,    464,  1200, 700, "4", "✅", "1200×700"),
    (1204, 464,  1200, 700, "5", "✅", "1200×700"),
    # Rij C - onder, hoogte 460mm
    (0,    0,    1390, 460, "6", "✅", "1390×460"),
    (1394, 0,    1390, 460, "7", "✅", "1390×460"),
]
offcuts = [
    (2408, 464, 392, 700, "R1", "♻", "392×700\nherbruikbaar"),
]
waste = [
    (2558, 1168, 242, 902, None, "\U0001F5D1", "afval"),
]

for (x, y, w, h, label, icon, sub) in parts:
    draw_rect_mm(x, y, w, h, PART_FILL, label=label, sub=sub, badge=True)

for (x, y, w, h, label, icon, sub) in offcuts:
    lines = sub.split("\n") if sub else None
    draw_rect_mm(x, y, w, h, OFFCUT_FILL, label=label, sub=(lines[0] if lines else None))
    if lines and len(lines) > 1:
        x0, y0 = to_page(x, y)
        w_pt, h_pt = w * mm * scale, h * mm * scale
        c.setFont("Helvetica", 7.5)
        c.setFillColor(HexColor("#555555"))
        c.drawCentredString(x0 + w_pt / 2, y0 + h_pt / 2 - 29, lines[1])

for (x, y, w, h, label, icon, sub) in waste:
    draw_rect_mm(x, y, w, h, WASTE_FILL, label=label, icon="waste", sub=sub)

# ---------------------------------------------------------------
# Zaagsneden - "lange zijdes eerst": eerst de 2 volledige-breedte
# sneden die de rijen scheiden, dan pas de kortere sneden binnen elke rij.
# ---------------------------------------------------------------
c.setStrokeColor(HexColor("#c0392b"))
c.setDash(3, 2)
c.setLineWidth(1.3)

# cut 1: horizontaal, volledige breedte op y=1168 - scheidt Rij A van B+C
x0, y0 = to_page(0, 1168)
x1, y1 = to_page(2800, 1168)
c.line(x0, y0, x1, y1)

# cut 2: horizontaal, volledige breedte op y=464 - scheidt Rij B van Rij C
x0, y0 = to_page(0, 464)
x1, y1 = to_page(2800, 464)
c.line(x0, y0, x1, y1)

# cut 3: verticaal binnen Rij A op x=854 (onderdeel 1 | 2)
x0, y0 = to_page(854, 1168)
x1, y1 = to_page(854, 2070)
c.line(x0, y0, x1, y1)

# cut 4: verticaal binnen Rij A op x=1708 (onderdeel 2 | 3)
x0, y0 = to_page(1708, 1168)
x1, y1 = to_page(1708, 2070)
c.line(x0, y0, x1, y1)

# cut 5: verticaal binnen Rij A op x=2558 (onderdeel 3 | afval)
x0, y0 = to_page(2558, 1168)
x1, y1 = to_page(2558, 2070)
c.line(x0, y0, x1, y1)

# cut 6: verticaal binnen Rij B op x=1204 (onderdeel 4 | 5)
x0, y0 = to_page(1204, 464)
x1, y1 = to_page(1204, 1164)
c.line(x0, y0, x1, y1)

# cut 7: verticaal binnen Rij B op x=2408 (onderdeel 5 | reststuk R1)
x0, y0 = to_page(2408, 464)
x1, y1 = to_page(2408, 1164)
c.line(x0, y0, x1, y1)

# cut 8: verticaal binnen Rij C op x=1394 (onderdeel 6 | 7)
x0, y0 = to_page(1394, 0)
x1, y1 = to_page(1394, 460)
c.line(x0, y0, x1, y1)

c.setDash()  # reset naar doorgetrokken lijn

# Nummer-cirkels: net BINNEN de plaatrand geplaatst (nooit erbuiten), zodat
# ze nooit overlappen met de titelbalk of de onderdelentabel.
label_positions = [
    (18,   1168, "1", "left"),
    (18,   464,  "2", "left"),
    (854,  2070, "3", "top"),
    (1708, 2070, "4", "top"),
    (2558, 2070, "5", "top"),
    (1204, 1164, "6", "top"),
    (2408, 1164, "7", "top"),
    (1394, 0,    "8", "bottom"),
]
for (x_mm, y_mm, num, side) in label_positions:
    x, y = to_page(x_mm, y_mm)
    offset = 5.5 * mm
    if side == "top":
        y -= offset
    elif side == "bottom":
        y += offset
    r = 3.6 * mm
    c.setFillColor(white)
    c.setStrokeColor(HexColor("#c0392b"))
    c.setLineWidth(1.1)
    c.circle(x, y, r, fill=1, stroke=1)
    c.setFillColor(HexColor("#c0392b"))
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(x, y - 3, num)

# ---- fabrieks-kantenband: dikke lijn langs de bovenkant ----
x0, y0 = to_page(0, 2070)
x1, y1 = to_page(2800, 2070)
c.setStrokeColor(FACTORY_EDGE)
c.setLineWidth(5)
c.line(x0, y0, x1, y1)
c.setFont("Helvetica-Bold", 8)
c.setFillColor(FACTORY_EDGE)
c.drawString(x0, y1 + 3, "fabrieks-kantenband — niet afzagen")

# ---------------------------------------------------------------
# Onderdelentabel (volledige breedte)
# ---------------------------------------------------------------
table_x0 = MARGIN
table_x1 = PAGE_W - MARGIN
cols = [
    ("Nr", 0.06),
    ("Omschrijving", 0.30),
    ("Aantal", 0.08),
    ("Afmeting (mm)", 0.16),
    ("Kantenband", 0.16),
    ("Opmerkingen", 0.24),
]
rows = [
    ("1", "Front A", "1", "850 × 902", "Voorzijde", "Fabrieksrand boven"),
    ("2", "Front B", "1", "850 × 902", "Voorzijde", "Fabrieksrand boven"),
    ("3", "Front C", "1", "850 × 902", "Voorzijde", "Fabrieksrand boven"),
    ("4", "Zijpaneel links", "1", "1200 × 700", "—", ""),
    ("5", "Zijpaneel rechts", "1", "1200 × 700", "—", ""),
    ("6", "Bodemplaat A", "1", "1390 × 460", "Voorzijde", ""),
    ("7", "Bodemplaat B", "1", "1390 × 460", "Voorzijde", ""),
]

row_h = table_h / (len(rows) + 1)

c.setStrokeColor(GRID)
c.setLineWidth(0.6)
c.setFillColor(HexColor("#dfe6ea"))
c.rect(table_x0, table_top - row_h, table_x1 - table_x0, row_h, fill=1, stroke=1)

x_cursor = table_x0
c.setFont("Helvetica-Bold", 8.5)
c.setFillColor(INK)
for (name, frac) in cols:
    w = (table_x1 - table_x0) * frac
    c.drawString(x_cursor + 2 * mm, table_top - row_h + row_h / 2 - 3, name)
    x_cursor += w

for i, row in enumerate(rows):
    y_top = table_top - row_h * (i + 2)
    c.setFillColor(white if i % 2 == 0 else HexColor("#f7f9fa"))
    c.rect(table_x0, y_top, table_x1 - table_x0, row_h, fill=1, stroke=1)
    c.setFillColor(INK)
    c.setFont("Helvetica", 8.5)
    x_cursor = table_x0
    for (val, (name, frac)) in zip(row, cols):
        w = (table_x1 - table_x0) * frac
        c.drawString(x_cursor + 2 * mm, y_top + row_h / 2 - 3, str(val))
        x_cursor += w

# verticale kolomlijnen
x_cursor = table_x0
for (name, frac) in cols:
    c.setStrokeColor(GRID)
    c.line(x_cursor, table_top, x_cursor, table_top - row_h * (len(rows) + 1))
    x_cursor += (table_x1 - table_x0) * frac
c.line(table_x1, table_top, table_x1, table_top - row_h * (len(rows) + 1))

# ---------------------------------------------------------------
# Footer: projectgegevens + QR (platte tekst, geen iconen)
# ---------------------------------------------------------------
c.setStrokeColor(GRID)
c.setLineWidth(0.6)
c.rect(MARGIN, footer_bottom, PAGE_W - 2 * MARGIN, footer_h, fill=0, stroke=1)

qr_size = footer_h - 4 * mm
qr_x = PAGE_W - MARGIN - qr_size - 3 * mm
qr_y = footer_bottom + 2 * mm

footer_cols = [
    ("Bronmateriaal", "Nieuwe plaat"),
    ("Materiaal", "Berken Multiplex"),
    ("Formaat", "2800 × 2070 mm"),
    ("Dikte", "18 mm"),
    ("Benutting", "90,7 %"),
    ("Nerfrichting", "→"),
]
avail_w = qr_x - MARGIN - 4 * mm
col_w = avail_w / len(footer_cols)
for i, (label, value) in enumerate(footer_cols):
    x = MARGIN + i * col_w + 3 * mm
    c.setFont("Helvetica", 7)
    c.setFillColor(HexColor("#666666"))
    c.drawString(x, footer_bottom + footer_h - 5.5 * mm, label)
    c.setFont("Helvetica-Bold", 10.5)
    c.setFillColor(INK)
    c.drawString(x, footer_bottom + 4.5 * mm, value)
    if i > 0:
        c.setStrokeColor(GRID)
        c.line(MARGIN + i * col_w, footer_bottom + 2 * mm, MARGIN + i * col_w, footer_bottom + footer_h - 2 * mm)

# eenvoudige QR-placeholder (finder patterns + ruis) i.p.v. een echte QR-lib
def draw_qr_placeholder(x, y, size):
    c.setFillColor(white)
    c.rect(x, y, size, size, fill=1, stroke=1)
    module = size / 21.0
    import random
    random.seed(42)
    c.setFillColor(black)
    for row in range(21):
        for col in range(21):
            in_finder = (row < 7 and col < 7) or (row < 7 and col > 13) or (row > 13 and col < 7)
            if in_finder:
                continue
            if random.random() > 0.55:
                c.rect(x + col * module, y + size - (row + 1) * module, module, module, fill=1, stroke=0)
    for (fx, fy) in [(0, 14), (14, 14), (0, 0)]:
        c.setFillColor(black)
        c.rect(x + fx * module, y + size - (fy + 7) * module, 7 * module, 7 * module, fill=1, stroke=0)
        c.setFillColor(white)
        c.rect(x + (fx + 1) * module, y + size - (fy + 6) * module, 5 * module, 5 * module, fill=1, stroke=0)
        c.setFillColor(black)
        c.rect(x + (fx + 2) * module, y + size - (fy + 5) * module, 3 * module, 3 * module, fill=1, stroke=0)

draw_qr_placeholder(qr_x, qr_y, qr_size)
c.setFont("Helvetica", 6)
c.setFillColor(HexColor("#666666"))
c.drawCentredString(qr_x + qr_size / 2, qr_y - 3, "QR → model")

c.showPage()
c.save()
print("done")
