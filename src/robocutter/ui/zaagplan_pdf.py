"""PDF-export van zaagplannen: van de grond af opgebouwd met directe
``QPainter``-tekencode (rechthoeken/lijnen/tekst) tegen een eigen, van
het schermthema losstaand wit print-palet — GEEN ``QWidget.render()``
meer op de (donker-getinte) schermwidgets, zoals de eerste versie van
deze export deed. Sven keurde die eerste versie af ("ik wil echt dat
hij de pdfs eigenlijk van de grond opbouwt"): het gaf een donkere
achtergrond op een verder wit PDF-document.

Deze versie houdt zich aan de goedgekeurde HTML-conceptmockup
(zie OVERDRACHT.md voor de link en de correctierondes), die op zijn
beurt de visuele taal aanhoudt van de eerder door Sven goedgekeurde
Cowork-referentiescripts
``design/voorbeelden/generate_zaagplan.py``/``_v2.py`` (reportlab):
een witte titelbalk met een dunne onderrand (i.p.v. een dichtgevulde
donkere balk, inktbesparend bij printen), rode stippellijn-zaagsnedes
met genummerde cirkels, groen gemarkeerde herbruikbare reststukken, een
onderdelentabel met een lege afvinkkolom (een écht getekend vierkantje,
geen font-checkbox-symbool) en een footer-strook met projectgegevens.

Layout-eenheid is millimeters (zoals het reportlab-referentiescript),
omgerekend naar apparaatpixels via ``_dpmm`` — dat maakt de code
onafhankelijk van de daadwerkelijke printerresolutie.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QMarginsF, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPageLayout, QPageSize, QPainter, QPen, QPixmap
from PySide6.QtPrintSupport import QPrinter

from robocutter.instellingen.beheer import InstellingenBeheer
from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.optimalisatie.models import Rand, ZaagplanResultaat
from robocutter.projecten.models import Project
from robocutter.projecten.zaaglijst import ZaaglijstRegel, bouw_zaaglijst, sorteer_zaaglijst
from robocutter.projecten.zaagplannen import PlaatZaagplan

__all__ = ["schrijf_zaagplannen_pdf"]

# Pad is relatief aan de repo-root (dev) resp. de gebundelde data (een
# PyInstaller-build), zelfde patroon en reden als _LOGO_ICON_PATH in
# main_window.py.
if getattr(sys, "frozen", False):
    _REPO_ROOT = Path(getattr(sys, "_MEIPASS", None) or Path(sys.executable).resolve().parent)
else:
    _REPO_ROOT = Path(__file__).resolve().parents[3]
_STANDAARD_LOGO_PAD = _REPO_ROOT / "design" / "assets" / "logo" / "robocutter_logo_met_tekst.png"

# ---------------------------------------------------------------------
# Print-palet: eigen, van robocutter.ui.theme losstaande kleuren — dit
# document moet er hetzelfde uitzien ongeacht het licht/donker-thema van
# de app zelf (zie de mockup-beslissing hierboven).
# ---------------------------------------------------------------------
_INK = QColor("#1a1a1a")
_MUTED = QColor("#5b6470")
_HEADER_MUTED = QColor("#6b7280")
_LINE = QColor("#c7ccd3")
_ROW_LINE = QColor("#e4e7ea")
_CUT = QColor("#c0392b")
_PART_FILL = QColor("#eef2f6")
_PART_LINE = QColor("#c3cbd6")
_OFFCUT_FILL = QColor("#e3f3e9")
_OFFCUT_INK = QColor("#2e7d46")
_OFFCUT_LINE = QColor("#bcdfc9")
_WARN_BG = QColor("#fdf1e2")
_WARN_INK = QColor("#9a5b12")
_WARN_BORDER = QColor("#f2d6ab")
_TABLE_HEAD = QColor("#dfe6ea")
_TABLE_HEAD_INK = QColor("#3a3f46")
_TABLE_STRIPE = QColor("#f7f9fa")
_TOTAAL_BG = QColor("#f1f3f5")
_FACTORY_EDGE = QColor("#111318")
_WHITE = QColor("#ffffff")

_SANS = "Segoe UI"  # zelfde terugval als de rest van de app (Inter niet gebundeld)
_MONO = "Consolas"

_SORTEER_LABEL = {
    "materiaal": "materiaal", "naam": "naam", "breedte": "breedte",
    "hoogte": "hoogte", "aantal": "aantal", "herkomst": "herkomst",
}


@dataclass
class _Kolom:
    label: str
    frac: float
    mono: bool = False


@dataclass
class _Ctx:
    painter: QPainter
    printer: QPrinter
    dpmm: float
    breedte_mm: float
    hoogte_mm: float
    project_naam: str
    werkvoorbereider: str
    logo: QPixmap | None

    def px(self, x_mm: float, y_mm: float) -> QPointF:
        return QPointF(x_mm * self.dpmm, y_mm * self.dpmm)

    def mm(self, waarde: float) -> float:
        return waarde * self.dpmm


def schrijf_zaagplannen_pdf(
    pad: str,
    project: Project,
    zaagplannen: list[PlaatZaagplan],
    strategie_label: str,
    materialen: MaterialenBibliotheek,
    sort_niveaus: list[str],
) -> None:
    """Schrijft alle platen van ``zaagplannen`` plus de volledige
    zaaglijst van ``project`` naar één PDF-bestand op ``pad`` — elke
    plaat op zijn eigen pagina (A4 liggend), gevolgd door de zaaglijst
    (die zelf over meerdere pagina's kan lopen, zie
    ``_teken_zaaglijst_paginas``)."""

    instellingen = InstellingenBeheer().huidige
    logo = _laad_logo(instellingen.bedrijfslogo_pad)

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(pad)
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    printer.setPageOrientation(QPageLayout.Orientation.Landscape)
    printer.setPageMargins(QMarginsF(6, 6, 6, 6), QPageLayout.Unit.Millimeter)

    painter = QPainter(printer)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pagina_px = printer.pageRect(QPrinter.Unit.DevicePixel)
    pagina_mm = printer.pageRect(QPrinter.Unit.Millimeter)
    dpmm = pagina_px.width() / pagina_mm.width()

    ctx = _Ctx(
        painter=painter,
        printer=printer,
        dpmm=dpmm,
        breedte_mm=pagina_mm.width(),
        hoogte_mm=pagina_mm.height(),
        project_naam=project.naam,
        werkvoorbereider=instellingen.werkvoorbereider_naam,
        logo=logo,
    )

    for i, plan in enumerate(zaagplannen):
        if i > 0:
            printer.newPage()
        _teken_plaat_pagina(ctx, plan, strategie_label)

    if zaagplannen:
        printer.newPage()
    _teken_zaaglijst_paginas(ctx, project, materialen, sort_niveaus)

    painter.end()


def _laad_logo(bedrijfslogo_pad: str | None) -> QPixmap | None:
    for kandidaat in (bedrijfslogo_pad, str(_STANDAARD_LOGO_PAD)):
        if not kandidaat:
            continue
        pix = QPixmap(kandidaat)
        if not pix.isNull():
            return pix
    return None


# ---------------------------------------------------------------------
# Gedeelde bouwstenen: kop, tabel, footer.
# ---------------------------------------------------------------------
def _font(familie: str, punten: float, bold: bool = False) -> QFont:
    font = QFont(familie)
    font.setPointSizeF(punten)
    font.setBold(bold)
    return font


def _elide(painter: QPainter, font: QFont, tekst: str, breedte_px: float) -> str:
    # Metrics via de actieve painter (niet een losstaande QFontMetricsF)
    # zodat de meting in dezelfde apparaatpixel-ruimte gebeurt als de
    # printer-DPI waarin breedte_px is uitgedrukt — anders wordt met een
    # verkeerde (scherm-)DPI vergeleken en triggert eliding vrijwel nooit.
    painter.setFont(font)
    return painter.fontMetrics().elidedText(tekst, Qt.TextElideMode.ElideRight, int(breedte_px))


def _teken_kop(ctx: _Ctx, regel2: str) -> float:
    """Tekent de titelbalk (tag/projectnaam, submeta, werkvoorbereider +
    logo rechts) en de dunne onderrand. Retourneert de y (mm) direct
    onder de balk."""

    p = ctx.painter
    kop_hoogte = 15.0
    marge_x = 3.0

    # Rechterkant eerst (logo + werkvoorbereider), zodat de linkerkant
    # weet hoeveel ruimte hij vrij moet laten.
    logo_hoogte_mm = 8.0
    logo_breedte_mm = 0.0
    if ctx.logo is not None and ctx.logo.height() > 0:
        logo_breedte_mm = ctx.logo.width() * (logo_hoogte_mm / ctx.logo.height())

    rechts_x = ctx.breedte_mm - marge_x
    if ctx.logo is not None:
        logo_rect = QRectF(
            ctx.px(rechts_x - logo_breedte_mm, kop_hoogte / 2 - logo_hoogte_mm / 2),
            QPointF(ctx.mm(rechts_x), ctx.mm(kop_hoogte / 2 + logo_hoogte_mm / 2)),
        )
        p.drawPixmap(logo_rect, ctx.logo, QRectF(ctx.logo.rect()))
        rechts_x -= logo_breedte_mm + 3.0

    if ctx.werkvoorbereider:
        p.setPen(QPen(_LINE, ctx.mm(0.25)))
        p.drawLine(ctx.px(rechts_x, 3.0), ctx.px(rechts_x, kop_hoogte - 3.0))
        rechts_x -= 3.0
        wv_breedte = 34.0
        label_rect = QRectF(ctx.px(rechts_x - wv_breedte, 3.6), QPointF(ctx.mm(rechts_x), ctx.mm(7.0)))
        p.setPen(QPen(_HEADER_MUTED))
        p.setFont(_font(_SANS, 6.0))
        p.drawText(label_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "WERKVOORBEREIDER")
        naam_rect = QRectF(ctx.px(rechts_x - wv_breedte, 7.2), QPointF(ctx.mm(rechts_x), ctx.mm(11.2)))
        p.setPen(QPen(_INK))
        font = _font(_SANS, 8.5, bold=True)
        p.drawText(naam_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, _elide(p, font, ctx.werkvoorbereider, ctx.mm(wv_breedte)))

    links_max_breedte = rechts_x - marge_x - 4.0

    # Linkerkant: "ZAAGPLAN" tag + projectnaam, daaronder de submeta.
    tag_font = _font(_SANS, 12.5, bold=True)
    p.setFont(tag_font)
    p.setPen(QPen(_INK))
    tag_rect = QRectF(ctx.px(marge_x, 3.4), QPointF(ctx.mm(marge_x + 26), ctx.mm(8.0)))
    p.drawText(tag_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "ZAAGPLAN")

    naam_font = _font(_SANS, 10.5, bold=True)
    naam_x = marge_x + 26
    naam_rect = QRectF(ctx.px(naam_x, 3.4), QPointF(ctx.mm(links_max_breedte), ctx.mm(8.0)))
    p.setFont(naam_font)
    p.drawText(naam_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, _elide(p, naam_font, ctx.project_naam, naam_rect.width()))

    sub_font = _font(_SANS, 8.5)
    sub_rect = QRectF(ctx.px(marge_x, 8.6), QPointF(ctx.mm(links_max_breedte), ctx.mm(13.4)))
    p.setPen(QPen(_MUTED))
    p.setFont(sub_font)
    p.drawText(sub_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, _elide(p, sub_font, regel2, sub_rect.width()))

    # Dunne onderrand (bewust géén dichtgevulde balk — inktbesparend bij printen).
    p.setPen(QPen(_INK, ctx.mm(0.5)))
    p.drawLine(ctx.px(0, kop_hoogte), ctx.px(ctx.breedte_mm, kop_hoogte))

    return kop_hoogte


def _teken_footer(ctx: _Ctx, y_mm: float, cellen: list[tuple[str, str]]) -> None:
    p = ctx.painter
    hoogte = 12.0
    rect = QRectF(ctx.px(0, y_mm), ctx.px(ctx.breedte_mm, y_mm + hoogte))
    p.setPen(QPen(_LINE, ctx.mm(0.3)))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(rect)

    cel_breedte = ctx.breedte_mm / len(cellen)
    for i, (label, waarde) in enumerate(cellen):
        cel_x = i * cel_breedte
        if i > 0:
            p.drawLine(ctx.px(cel_x, y_mm + 1.5), ctx.px(cel_x, y_mm + hoogte - 1.5))
        label_rect = QRectF(ctx.px(cel_x + 3, y_mm + 1.5), QPointF(ctx.mm(cel_x + cel_breedte - 2), ctx.mm(y_mm + 5.5)))
        p.setPen(QPen(_MUTED))
        p.setFont(_font(_SANS, 6.0))
        p.drawText(label_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label.upper())
        waarde_rect = QRectF(ctx.px(cel_x + 3, y_mm + 5.5), QPointF(ctx.mm(cel_x + cel_breedte - 2), ctx.mm(y_mm + hoogte - 1.5)))
        p.setPen(QPen(_INK))
        waarde_font = _font(_MONO, 9.5, bold=True)
        p.drawText(waarde_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, _elide(p, waarde_font, waarde, waarde_rect.width()))


def _teken_tabel(
    ctx: _Ctx,
    y_mm: float,
    kolommen: list[_Kolom],
    rijen: list[list[str]],
    rij_hoogte_mm: float,
    header_hoogte_mm: float,
    totaal_rij: list[str] | None = None,
) -> float:
    """Tekent een tabel met een grijze koprij en gestreepte datarijen.
    Kolom 0 is altijd de afvinkkolom: een waarde ``"[ ]"`` tekent een
    echt vierkantje (geen font-checkbox-symbool), een lege string laat
    de cel leeg (voor de totaalregel). Retourneert de y (mm) net onder
    de tabel."""

    p = ctx.painter
    breedte = ctx.breedte_mm  # tabel loopt over de volle paginabreedte
    x_offsets = []
    x = 0.0
    for k in kolommen:
        x_offsets.append(x)
        x += breedte * k.frac
    x_offsets.append(breedte)

    # Koprij.
    kop_rect = QRectF(ctx.px(0, y_mm), ctx.px(breedte, y_mm + header_hoogte_mm))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(_TABLE_HEAD)
    p.drawRect(kop_rect)
    p.setPen(QPen(_INK))
    header_font = _font(_SANS, 6.6, bold=True)
    for i, k in enumerate(kolommen):
        if i == 0:
            continue
        cel_rect = QRectF(ctx.px(x_offsets[i] + 2, y_mm), QPointF(ctx.mm(x_offsets[i + 1] - 1), ctx.mm(y_mm + header_hoogte_mm)))
        p.setFont(header_font)
        p.setPen(QPen(_TABLE_HEAD_INK))
        p.drawText(cel_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, k.label.upper())

    y = y_mm + header_hoogte_mm
    for row_index, rij in enumerate(rijen):
        rij_rect = QRectF(ctx.px(0, y), ctx.px(breedte, y + rij_hoogte_mm))
        if row_index % 2 == 1:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(_TABLE_STRIPE)
            p.drawRect(rij_rect)
        _teken_tabelrij(ctx, y, rij_hoogte_mm, kolommen, x_offsets, rij, bold=False)
        p.setPen(QPen(_ROW_LINE, ctx.mm(0.25)))
        p.drawLine(ctx.px(0, y + rij_hoogte_mm), ctx.px(breedte, y + rij_hoogte_mm))
        y += rij_hoogte_mm

    if totaal_rij is not None:
        rij_rect = QRectF(ctx.px(0, y), ctx.px(breedte, y + rij_hoogte_mm))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(_TOTAAL_BG)
        p.drawRect(rij_rect)
        _teken_tabelrij(ctx, y, rij_hoogte_mm, kolommen, x_offsets, totaal_rij, bold=True)
        y += rij_hoogte_mm

    # Buitenrand + kolomlijnen.
    p.setPen(QPen(_LINE, ctx.mm(0.3)))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(QRectF(ctx.px(0, y_mm), ctx.px(breedte, y)))
    for offset in x_offsets[1:-1]:
        p.drawLine(ctx.px(offset, y_mm), ctx.px(offset, y))

    return y


def _teken_tabelrij(
    ctx: _Ctx, y_mm: float, rij_hoogte_mm: float, kolommen: list[_Kolom], x_offsets: list[float], rij: list[str], bold: bool
) -> None:
    p = ctx.painter
    for i, (k, waarde) in enumerate(zip(kolommen, rij)):
        breedte_col = x_offsets[i + 1] - x_offsets[i]
        if i == 0:
            if waarde == "[ ]":
                grootte = 3.2
                cx = x_offsets[i] + breedte_col / 2 - grootte / 2
                cy = y_mm + rij_hoogte_mm / 2 - grootte / 2
                p.setPen(QPen(_INK, ctx.mm(0.3)))
                p.setBrush(_WHITE)
                p.drawRect(QRectF(ctx.px(cx, cy), QPointF(ctx.mm(cx + grootte), ctx.mm(cy + grootte))))
            continue
        cel_rect = QRectF(ctx.px(x_offsets[i] + 2, y_mm), QPointF(ctx.mm(x_offsets[i + 1] - 1), ctx.mm(y_mm + rij_hoogte_mm)))
        font = _font(_MONO if k.mono else _SANS, 8.0, bold=bold)
        p.setPen(QPen(_INK))
        p.drawText(cel_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, _elide(p, font, waarde, cel_rect.width()))


def _teken_waarschuwing(ctx: _Ctx, y_mm: float, tekst: str) -> float:
    hoogte = 7.0
    rect = QRectF(ctx.px(0, y_mm), ctx.px(ctx.breedte_mm, y_mm + hoogte))
    p = ctx.painter
    p.setPen(QPen(_WARN_BORDER, ctx.mm(0.3)))
    p.setBrush(_WARN_BG)
    p.drawRoundedRect(rect, ctx.mm(1.2), ctx.mm(1.2))
    p.setPen(QPen(_WARN_INK))
    font = _font(_SANS, 8.0, bold=True)
    tekst_rect = rect.adjusted(ctx.mm(3), 0, -ctx.mm(3), 0)
    p.drawText(tekst_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, _elide(p, font, tekst, tekst_rect.width()))
    return y_mm + hoogte


# ---------------------------------------------------------------------
# Pagina 1: één zaagplan (plaat + onderdelentabel + footer).
# ---------------------------------------------------------------------
def _kantenband_tekst(info) -> str:
    if info is None:
        return "—"
    if info.fabriekskantenband_vereist:
        return "Fabrieksrand"
    if info.kantenband_randen:
        return ", ".join(sorted(r.value for r in info.kantenband_randen))
    return "—"


def _teken_plaat_pagina(ctx: _Ctx, plan: PlaatZaagplan, strategie_label: str) -> None:
    mat = plan.resultaat.materiaal
    afmeting = f"{mat.lengte:g} × {mat.breedte:g} mm"
    regel2 = f"{mat.naam}  ·  Plaat {plan.plaat_nummer} van {plan.platen_totaal}  ·  strategie {strategie_label}"
    kop_onder = _teken_kop(ctx, regel2)

    # Groepeer plaatsingen per onderdeel-id (zelfde als het scherm) voor
    # de onderdelentabel.
    groepen: dict[str, list] = {}
    volgorde: list[str] = []
    for pl in plan.resultaat.plaatsingen:
        if pl.onderdeel_id not in groepen:
            groepen[pl.onderdeel_id] = []
            volgorde.append(pl.onderdeel_id)
        groepen[pl.onderdeel_id].append(pl)

    kolommen = [
        _Kolom("", 0.05),
        _Kolom("Nr", 0.04, mono=True),
        _Kolom("Omschrijving", 0.23),
        _Kolom("Aantal", 0.08, mono=True),
        _Kolom("Afmeting (mm)", 0.15, mono=True),
        _Kolom("Kantenband", 0.15),
        _Kolom("Herkomst", 0.30),
    ]
    tabel_rijen: list[list[str]] = []
    for i, oid in enumerate(volgorde, start=1):
        plaatsingen = groepen[oid]
        info = plan.onderdeel_info.get(oid)
        naam = info.naam if info else oid
        eerste = plaatsingen[0]
        herkomst = info.herkomst if info else "—"
        tabel_rijen.append(
            ["[ ]", str(i), naam, str(len(plaatsingen)), f"{eerste.breedte:g} × {eerste.hoogte:g}", _kantenband_tekst(info), herkomst]
        )

    header_h = 6.5
    rij_h = 6.5
    tabel_h = header_h + rij_h * max(1, len(tabel_rijen))

    footer_h = 12.0
    gap = 3.0
    warn_h = 7.0
    heeft_waarschuwing = bool(plan.resultaat.niet_geplaatst)

    # Alles wat ONDER de plaatzone staat, elk gevolgd door zijn eigen
    # tussenruimte: [gap] + [waarschuwingsbalk + gap, indien van
    # toepassing] + onderdelentabel + [gap] + footer.
    onder_plaat_h = gap + tabel_h + gap + footer_h
    if heeft_waarschuwing:
        onder_plaat_h += warn_h + gap

    plaat_zone_top = kop_onder + gap
    plaat_zone_h = ctx.hoogte_mm - plaat_zone_top - onder_plaat_h

    _teken_plaat(ctx, plan.resultaat, plaat_zone_top, plaat_zone_h)

    y = plaat_zone_top + plaat_zone_h + gap
    if heeft_waarschuwing:
        namen = ", ".join(sorted({plan.naam_voor(uid) for uid in plan.resultaat.niet_geplaatst}))
        y = _teken_waarschuwing(ctx, y, f"⚠ Niet geplaatst: {namen}") + gap

    y = _teken_tabel(ctx, y, kolommen, tabel_rijen, rij_h, header_h) + gap
    _teken_footer(
        ctx,
        y,
        [
            ("Materiaal", plan.materiaal_naam),
            ("Formaat", afmeting),
            ("Dikte", f"{mat.dikte:g} mm"),
            ("Kerf", f"{mat.kerf:g} mm"),
            ("Benutting", f"{plan.resultaat.benuttingspercentage:g}%".replace(".", ",")),
        ],
    )


def _teken_plaat(ctx: _Ctx, resultaat: ZaagplanResultaat, zone_top_mm: float, zone_h_mm: float) -> None:
    p = ctx.painter
    mat = resultaat.materiaal
    if mat.lengte <= 0 or mat.breedte <= 0 or zone_h_mm <= 0:
        return

    # Ruimte voor de fabrieksrand-labels reserveren (boven/links) zodat
    # die niet buiten de zone vallen.
    marge = 6.0
    beschikbaar_w = ctx.breedte_mm - 2 * marge
    beschikbaar_h = zone_h_mm - 2 * marge
    schaal_mm_per_mm = min(beschikbaar_w / mat.lengte, beschikbaar_h / mat.breedte)
    plaat_w = mat.lengte * schaal_mm_per_mm
    plaat_h = mat.breedte * schaal_mm_per_mm
    ox = marge + (beschikbaar_w - plaat_w) / 2
    oy = zone_top_mm + marge + (beschikbaar_h - plaat_h) / 2

    def px(x_stuk: float, y_stuk: float) -> QPointF:
        return ctx.px(ox + x_stuk * schaal_mm_per_mm, oy + y_stuk * schaal_mm_per_mm)

    # Plaatrand.
    p.setPen(QPen(_LINE, ctx.mm(0.4)))
    p.setBrush(_WHITE)
    p.drawRect(QRectF(px(0, 0), px(mat.lengte, mat.breedte)))

    # Reststukken (herbruikbaar) — groen.
    for i, r in enumerate(resultaat.reststukken, start=1):
        rect = QRectF(px(r.x, r.y), px(r.x + r.breedte, r.y + r.hoogte))
        p.setPen(QPen(_OFFCUT_LINE, ctx.mm(0.25)))
        p.setBrush(_OFFCUT_FILL)
        p.drawRect(rect)
        _teken_stuk_label(ctx, rect, f"R{i}", f"{r.breedte:g}×{r.hoogte:g}", "herbruikbaar", _OFFCUT_INK, cirkel=False)

    # Geplaatste onderdelen — neutraal grijsblauw, groen nummerbolletje.
    for i, pl in enumerate(resultaat.plaatsingen, start=1):
        rect = QRectF(px(pl.x, pl.y), px(pl.x + pl.breedte, pl.y + pl.hoogte))
        p.setPen(QPen(_PART_LINE, ctx.mm(0.25)))
        p.setBrush(_PART_FILL)
        p.drawRect(rect)
        _teken_stuk_label(ctx, rect, str(i), f"{pl.breedte:g}×{pl.hoogte:g}", None, _MUTED, cirkel=True)

    # Fabriekskantenband: dikke donkere lijn net buiten de betreffende rand.
    for rand in mat.fabriekskantenband_randen:
        _teken_fabrieksrand(ctx, rand, px, mat)

    # Zaagsnedes: rode stippellijn + genummerde cirkel aan het "aankomst"-
    # uiteinde van elke snede (verticaal: onderkant van het segment,
    # horizontaal: linkerkant — zelfde plaatsingsregel als de
    # goedgekeurde HTML-mockup, zie robocutter/ui/zaagplan_pdf.py).
    p.setPen(QPen(_CUT, ctx.mm(0.45), Qt.PenStyle.DashLine))
    for s in resultaat.zaagvolgorde:
        if s.richting == "verticaal":
            p.drawLine(px(s.positie, s.start), px(s.positie, s.einde))
        else:
            p.drawLine(px(s.start, s.positie), px(s.einde, s.positie))

    straal = 3.0
    for s in resultaat.zaagvolgorde:
        if s.richting == "verticaal":
            # Badge aan de onderkant van dit sneden-segment (het punt waar
            # de snede "aankomt"), zelfde regel als de goedgekeurde mockup.
            badge_x, badge_y = s.positie, max(s.start, s.einde)
        else:
            # Horizontale snede: badge aan de linkerkant van het segment.
            badge_x, badge_y = min(s.start, s.einde), s.positie
        centrum = px(badge_x, badge_y)
        cirkel = QRectF(centrum.x() - ctx.mm(straal), centrum.y() - ctx.mm(straal), ctx.mm(2 * straal), ctx.mm(2 * straal))
        p.setPen(QPen(_CUT, ctx.mm(0.35)))
        p.setBrush(_WHITE)
        p.drawEllipse(cirkel)
        p.setPen(QPen(_CUT))
        p.setFont(_font(_MONO, 6.5, bold=True))
        p.drawText(cirkel, Qt.AlignmentFlag.AlignCenter, str(s.volgnummer))


def _teken_fabrieksrand(ctx: _Ctx, rand: Rand, px, mat) -> None:
    # Dikke donkere lijn net buiten de betreffende plaatrand, met een
    # niet-geroteerde onderschrift-tekst ernaast — zelfde eenvoudige
    # horizontale-labelkeuze als de goedgekeurde mockup zelf maakt
    # (die het label ook niet meeroteert met de rand).
    p = ctx.painter
    afstand = 2.5
    fabriek_pen = QPen(_FACTORY_EDGE, ctx.mm(1.4))
    fabriek_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(fabriek_pen)
    label = "FABRIEKSKANTENBAND — NIET AFZAGEN"
    label_font = _font(_SANS, 5.5, bold=True)

    if rand == Rand.LINKS:
        p.drawLine(px(0, 0) + QPointF(-ctx.mm(afstand), 0), px(0, mat.breedte) + QPointF(-ctx.mm(afstand), 0))
        label_rect = QRectF(px(0, 0) + QPointF(0, -ctx.mm(5.5)), px(mat.lengte, 0) + QPointF(0, -ctx.mm(1.5)))
    elif rand == Rand.RECHTS:
        p.drawLine(px(mat.lengte, 0) + QPointF(ctx.mm(afstand), 0), px(mat.lengte, mat.breedte) + QPointF(ctx.mm(afstand), 0))
        label_rect = QRectF(px(0, 0) + QPointF(0, -ctx.mm(5.5)), px(mat.lengte, 0) + QPointF(0, -ctx.mm(1.5)))
    elif rand == Rand.ONDER:
        p.drawLine(px(0, mat.breedte) + QPointF(0, ctx.mm(afstand)), px(mat.lengte, mat.breedte) + QPointF(0, ctx.mm(afstand)))
        label_rect = QRectF(px(0, mat.breedte) + QPointF(0, ctx.mm(afstand + 1)), px(mat.lengte, mat.breedte) + QPointF(0, ctx.mm(afstand + 5)))
    else:  # BOVEN
        p.drawLine(px(0, 0) + QPointF(0, -ctx.mm(afstand)), px(mat.lengte, 0) + QPointF(0, -ctx.mm(afstand)))
        label_rect = QRectF(px(0, 0) + QPointF(0, -ctx.mm(5.5)), px(mat.lengte, 0) + QPointF(0, -ctx.mm(1.5)))

    p.setPen(QPen(_FACTORY_EDGE))
    p.setFont(label_font)
    p.drawText(label_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, _elide(p, label_font, label, label_rect.width()))


def _teken_stuk_label(ctx: _Ctx, rect: QRectF, nummer_tekst: str, maat_tekst: str, tag: str | None, kleur: QColor, cirkel: bool) -> None:
    if rect.width() < ctx.mm(18) or rect.height() < ctx.mm(10):
        return
    p = ctx.painter
    midden_x = rect.center().x()
    boven_y = rect.center().y() - ctx.mm(4)

    if cirkel:
        straal = ctx.mm(2.6)
        cirkel_rect = QRectF(midden_x - straal, boven_y - straal, 2 * straal, 2 * straal)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(_OFFCUT_INK)
        p.drawEllipse(cirkel_rect)
        p.setPen(QPen(_WHITE))
        p.setFont(_font(_MONO, 6.5, bold=True))
        p.drawText(cirkel_rect, Qt.AlignmentFlag.AlignCenter, nummer_tekst)
    else:
        p.setPen(QPen(kleur))
        p.setFont(_font(_SANS, 8.0, bold=True))
        p.drawText(QRectF(rect.left(), boven_y - ctx.mm(3), rect.width(), ctx.mm(6)), Qt.AlignmentFlag.AlignCenter, nummer_tekst)

    if rect.height() < ctx.mm(16):
        return
    p.setPen(QPen(kleur))
    p.setFont(_font(_MONO, 6.5))
    onder_y = boven_y + ctx.mm(5) if cirkel else boven_y + ctx.mm(6)
    p.drawText(QRectF(rect.left(), onder_y, rect.width(), ctx.mm(5)), Qt.AlignmentFlag.AlignCenter, maat_tekst)

    if tag and rect.height() >= ctx.mm(22):
        p.setFont(_font(_SANS, 5.0, bold=True))
        p.drawText(QRectF(rect.left(), onder_y + ctx.mm(5), rect.width(), ctx.mm(4)), Qt.AlignmentFlag.AlignCenter, tag.upper())


# ---------------------------------------------------------------------
# Zaaglijst: kan over meerdere pagina's lopen — kolomkop herhaalt zich,
# de "Totaal"-rij verschijnt alleen op de allerlaatste pagina.
# ---------------------------------------------------------------------
def _materiaal_naam(materiaal_id: str, materialen: MaterialenBibliotheek) -> str:
    try:
        return materialen.ophalen(materiaal_id).naam
    except KeyError:
        return "onbekend materiaal"


def _teken_zaaglijst_paginas(ctx: _Ctx, project: Project, materialen: MaterialenBibliotheek, sort_niveaus: list[str]) -> None:
    alle_regels = sorteer_zaaglijst(bouw_zaaglijst(project), sort_niveaus, materialen)
    aantal_materialen = len({r.onderdeel.materiaal_id for r in alle_regels})
    aantal_onderdelen = sum(r.onderdeel.aantal for r in alle_regels)
    totaal_gesorteerd_op = ", ".join(_SORTEER_LABEL[s] for s in sort_niveaus) if sort_niveaus else "—"

    kolommen = [
        _Kolom("", 0.05),
        _Kolom("Onderdeel", 0.19),
        _Kolom("Materiaal", 0.18),
        _Kolom("Breedte", 0.10, mono=True),
        _Kolom("Hoogte", 0.10, mono=True),
        _Kolom("Aantal", 0.08, mono=True),
        _Kolom("Herkomst", 0.30),
    ]

    header_h = 6.5
    rij_h = 6.0
    footer_h = 12.0
    gap = 3.0
    kop_hoogte = 15.0
    beschikbaar_h = ctx.hoogte_mm - kop_hoogte - gap - footer_h - gap
    rijen_per_pagina = max(1, int((beschikbaar_h - header_h) // rij_h))

    paginas: list[list[ZaaglijstRegel]] = (
        [alle_regels[i : i + rijen_per_pagina] for i in range(0, len(alle_regels), rijen_per_pagina)] if alle_regels else [[]]
    )
    # Past de totaalregel niet meer op de laatste pagina, geef hem een
    # eigen vervolgpagina i.p.v. de tabel daar te laten overlopen.
    if len(paginas[-1]) >= rijen_per_pagina:
        paginas.append([])

    totaal_paginas = len(paginas)
    for i, pagina_regels in enumerate(paginas, start=1):
        if i > 1:
            ctx.printer.newPage()
        regel2 = f"Zaaglijst — pagina {i} van {totaal_paginas}  ·  {aantal_materialen} materialen  ·  {aantal_onderdelen} onderdelen"
        kop_onder = _teken_kop(ctx, regel2)

        tabel_rijen = [
            ["[ ]", r.onderdeel.naam, _materiaal_naam(r.onderdeel.materiaal_id, materialen), f"{r.onderdeel.breedte:g} mm", f"{r.onderdeel.hoogte:g} mm", str(r.onderdeel.aantal), r.herkomst]
            for r in pagina_regels
        ]
        totaal_rij = None
        if i == totaal_paginas:
            totaal_rij = ["", "Totaal", "", "", "", str(aantal_onderdelen), ""]

        y = kop_onder + gap
        y = _teken_tabel(ctx, y, kolommen, tabel_rijen, rij_h, header_h, totaal_rij=totaal_rij) + gap
        _teken_footer(
            ctx,
            ctx.hoogte_mm - footer_h,
            [
                ("Project", project.naam),
                ("Materialen", str(aantal_materialen)),
                ("Gesorteerd op", totaal_gesorteerd_op),
            ],
        )
