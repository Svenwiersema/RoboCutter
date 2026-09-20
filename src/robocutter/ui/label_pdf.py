"""PDF-export van onderdeel-labels (hoofdstuk 6 — Labels &
identificatie): net als ``zaagplan_pdf.py`` van de grond af opgebouwd
met directe ``QPainter``-tekencode tegen een eigen, van het
schermthema losstaand wit print-palet — zelfde reden als daar (Sven
wil geen ``QWidget.render()`` op schermwidgets voor exports).

Layout is een rooster van losse labels op een gewone A4-printer (nog
géén afmetingen voor een specifiek labelprinter-merk — hoofdstuk 6
noemt dat expliciet als open vraag, later te bepalen bij technische
uitwerking/testen met een echte printer). Elke labelcel toont de vaste
kernvelden uit hoofdstuk 6 (onderdeel-ID via de scancode, materiaal,
projectnummer, afmeting) plus de optionele velden die
``Instellingen`` aan/uit zet (scancode QR/barcode/geen,
kantenband-indicatie, nerfrichting-pijl) — één algemene instelling,
geen keuze per printactie.

De scancode wordt zelf getekend (geen plaatje/afbeeldingsbestand):
een QR-code via ``qrcode``'s ``get_matrix()`` (geeft een boolean-
rooster, geen Pillow-afhankelijkheid nodig) en een 1D-barcode via
``python-barcode``'s Code128 ``build()`` (geeft een "1010..."-string op
module-resolutie) — beide gewoon als rechthoekjes getekend met
dezelfde ``QPainter`` als de rest van dit document.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QMarginsF, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPageLayout, QPageSize, QPainter, QPen
from PySide6.QtPrintSupport import QPrinter

from robocutter.instellingen.models import Instellingen
from robocutter.modellen.models import Nerfrichting
from robocutter.projecten.labels import OnderdeelLabel
from robocutter.projecten.models import Project

__all__ = ["schrijf_labels_pdf"]

_INK = QColor("#1a1a1a")
_MUTED = QColor("#5b6470")
_LINE = QColor("#c7ccd3")
_CUT_LINE = QColor("#c7ccd3")
_WHITE = QColor("#ffffff")

_SANS = "Segoe UI"
_MONO = "Consolas"

# Geen specifiek labelprinter-formaat (bewust nog niet bepaald, zie
# module-docstring) — een ruim, goed leesbaar formaat voor een A4-vel
# om desgewenst los te knippen.
_LABEL_W_MM = 64.0
_LABEL_H_MM = 38.0
_GAP_MM = 3.0
_MARGE_MM = 8.0


@dataclass
class _Ctx:
    painter: QPainter
    dpmm: float

    def px(self, x_mm: float, y_mm: float) -> QPointF:
        return QPointF(x_mm * self.dpmm, y_mm * self.dpmm)

    def mm(self, waarde: float) -> float:
        return waarde * self.dpmm


def _font(familie: str, punten: float, bold: bool = False) -> QFont:
    font = QFont(familie)
    font.setPointSizeF(punten)
    font.setBold(bold)
    return font


def _elide(painter: QPainter, font: QFont, tekst: str, breedte_px: float) -> str:
    painter.setFont(font)
    return painter.fontMetrics().elidedText(tekst, Qt.TextElideMode.ElideRight, int(breedte_px))


def _kantenband_tekst(label: OnderdeelLabel) -> str:
    if label.fabriekskantenband_vereist:
        return "Fabrieksrand"
    if label.kantenband_randen:
        return "Kantenband: " + ", ".join(sorted(r.value for r in label.kantenband_randen))
    return ""


def schrijf_labels_pdf(pad: str, project: Project, labels: list[OnderdeelLabel], instellingen: Instellingen) -> None:
    """Schrijft ``labels`` als een rooster labels naar één PDF op
    ``pad`` (A4 staand, meerdere pagina's zodra het rooster vol is)."""

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(pad)
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    printer.setPageOrientation(QPageLayout.Orientation.Portrait)
    printer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)

    painter = QPainter(printer)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pagina_px = printer.pageRect(QPrinter.Unit.DevicePixel)
    pagina_mm = printer.pageRect(QPrinter.Unit.Millimeter)
    dpmm = pagina_px.width() / pagina_mm.width()
    ctx = _Ctx(painter=painter, dpmm=dpmm)

    breedte_mm = pagina_mm.width()
    hoogte_mm = pagina_mm.height()
    beschikbaar_w = breedte_mm - 2 * _MARGE_MM
    beschikbaar_h = hoogte_mm - 2 * _MARGE_MM
    kolommen = max(1, int((beschikbaar_w + _GAP_MM) // (_LABEL_W_MM + _GAP_MM)))
    rijen = max(1, int((beschikbaar_h + _GAP_MM) // (_LABEL_H_MM + _GAP_MM)))
    per_pagina = kolommen * rijen

    if not labels:
        painter.end()
        return

    for start in range(0, len(labels), per_pagina):
        if start > 0:
            printer.newPage()
        for i, label in enumerate(labels[start : start + per_pagina]):
            kol, rij = i % kolommen, i // kolommen
            x = _MARGE_MM + kol * (_LABEL_W_MM + _GAP_MM)
            y = _MARGE_MM + rij * (_LABEL_H_MM + _GAP_MM)
            _teken_label(ctx, x, y, project, label, instellingen)

    painter.end()


def _teken_label(ctx: _Ctx, x_mm: float, y_mm: float, project: Project, label: OnderdeelLabel, instellingen: Instellingen) -> None:
    p = ctx.painter
    rect = QRectF(ctx.px(x_mm, y_mm), ctx.px(x_mm + _LABEL_W_MM, y_mm + _LABEL_H_MM))

    # Knip-contour: een dunne stippellijn (geen echte rand — dit is één
    # aaneengesloten vel, geen losse labelbon).
    p.setPen(QPen(_CUT_LINE, ctx.mm(0.25), Qt.PenStyle.DashLine))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(rect)

    pad = 2.5
    scancode = instellingen.label_scancode
    code_zone_mm = 15.0 if scancode == "qr" else 0.0
    tekst_breedte = _LABEL_W_MM - 2 * pad - (code_zone_mm + pad if scancode == "qr" else 0)

    # Onderdeelnaam + materiaal.
    naam_font = _font(_SANS, 9.0, bold=True)
    naam_rect = QRectF(ctx.px(x_mm + pad, y_mm + pad), QPointF(ctx.mm(x_mm + pad + tekst_breedte), ctx.mm(y_mm + pad + 4.5)))
    p.setPen(QPen(_INK))
    p.drawText(naam_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, _elide(p, naam_font, label.onderdeel_naam, naam_rect.width()))

    mat_font = _font(_SANS, 7.0)
    mat_rect = QRectF(ctx.px(x_mm + pad, y_mm + pad + 4.8), QPointF(ctx.mm(x_mm + pad + tekst_breedte), ctx.mm(y_mm + pad + 8.3)))
    p.setPen(QPen(_MUTED))
    p.drawText(mat_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, _elide(p, mat_font, label.materiaal_naam, mat_rect.width()))

    # Afmeting (groot, mono) + projectnummer.
    afm_font = _font(_MONO, 11.0, bold=True)
    afm_rect = QRectF(ctx.px(x_mm + pad, y_mm + pad + 9.0), QPointF(ctx.mm(x_mm + pad + tekst_breedte), ctx.mm(y_mm + pad + 15.0)))
    p.setPen(QPen(_INK))
    p.drawText(afm_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, _elide(p, afm_font, label.afmeting_tekst, afm_rect.width()))

    proj_font = _font(_SANS, 6.5)
    proj_rect = QRectF(ctx.px(x_mm + pad, y_mm + pad + 15.4), QPointF(ctx.mm(x_mm + pad + tekst_breedte), ctx.mm(y_mm + pad + 18.4)))
    p.setPen(QPen(_MUTED))
    proj_tekst = f"Project: {label.projectnummer}" if label.projectnummer else f"Project: {project.naam}"
    p.drawText(proj_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, _elide(p, proj_font, proj_tekst, proj_rect.width()))

    onder_y = y_mm + _LABEL_H_MM - pad - 4.0

    # Optionele kantenband-indicatie.
    kant_tekst = _kantenband_tekst(label) if instellingen.label_kantenband_indicatie else ""
    if kant_tekst:
        kant_font = _font(_SANS, 6.5, bold=True)
        kant_rect = QRectF(ctx.px(x_mm + pad, onder_y), QPointF(ctx.mm(x_mm + pad + tekst_breedte), ctx.mm(onder_y + 4.0)))
        p.setPen(QPen(_MUTED))
        p.drawText(kant_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, _elide(p, kant_font, kant_tekst, kant_rect.width()))

    # Optionele nerfrichting-pijl, rechtsonder in de tekstzone.
    if instellingen.label_nerfrichting_pijl and label.nerfrichting_vereist != Nerfrichting.GEEN:
        _teken_nerf_pijl(ctx, x_mm + tekst_breedte + pad - 9.0, onder_y + 2.0, label.nerfrichting_vereist)

    # Optionele scancode: QR rechtsboven (vierkant), of barcode als
    # volle-breedte strook onderaan (verdringt dan de kantenband-/
    # nerf-regel niet — die staat al hoger in de tekstzone).
    if scancode == "qr":
        _teken_qr(ctx, x_mm + _LABEL_W_MM - pad - code_zone_mm, y_mm + pad, code_zone_mm, label.scancode_waarde)
    elif scancode == "barcode":
        barcode_h = 8.0
        _teken_barcode(
            ctx, x_mm + pad, y_mm + _LABEL_H_MM - pad - barcode_h, _LABEL_W_MM - 2 * pad, barcode_h, label.scancode_waarde
        )


def _teken_nerf_pijl(ctx: _Ctx, x_mm: float, y_mm: float, richting: Nerfrichting) -> None:
    """Een klein pijl-icoon dat aangeeft langs welke zijde van dít
    onderdeel de nerf moet lopen (lange zijde = horizontale pijl, korte
    zijde = verticale pijl) — puur symbolisch, geen schaalgetrouwe
    weergave van het onderdeel zelf."""

    p = ctx.painter
    lengte = 7.0
    p.setPen(QPen(_INK, ctx.mm(0.35)))
    cx, cy = x_mm + lengte / 2, y_mm + lengte / 2
    if richting == Nerfrichting.LANGE_ZIJDE:
        a, b = ctx.px(x_mm, cy), ctx.px(x_mm + lengte, cy)
    else:
        a, b = ctx.px(cx, y_mm), ctx.px(cx, y_mm + lengte)
    p.drawLine(a, b)
    for punt, richt in ((a, -1), (b, 1)):
        _teken_pijlpunt(ctx, punt, a, b, richt)


def _teken_pijlpunt(ctx: _Ctx, punt: QPointF, a: QPointF, b: QPointF, richt: int) -> None:
    p = ctx.painter
    kop = ctx.mm(1.1)
    if abs(a.y() - b.y()) < 0.01:  # horizontale lijn
        dx = kop * richt
        p.drawLine(punt, QPointF(punt.x() - dx, punt.y() - kop * 0.7))
        p.drawLine(punt, QPointF(punt.x() - dx, punt.y() + kop * 0.7))
    else:  # verticale lijn
        dy = kop * richt
        p.drawLine(punt, QPointF(punt.x() - kop * 0.7, punt.y() - dy))
        p.drawLine(punt, QPointF(punt.x() + kop * 0.7, punt.y() - dy))


def _teken_qr(ctx: _Ctx, x_mm: float, y_mm: float, grootte_mm: float, waarde: str) -> None:
    import qrcode

    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0)
    qr.add_data(waarde)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    n = len(matrix)
    if n == 0:
        return
    modulegrootte = grootte_mm / n

    p = ctx.painter
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(_INK)
    for row_i, rij in enumerate(matrix):
        for kol_i, aan in enumerate(rij):
            if not aan:
                continue
            mx = x_mm + kol_i * modulegrootte
            my = y_mm + row_i * modulegrootte
            p.drawRect(QRectF(ctx.px(mx, my), QPointF(ctx.mm(mx + modulegrootte), ctx.mm(my + modulegrootte))))


def _teken_barcode(ctx: _Ctx, x_mm: float, y_mm: float, breedte_mm: float, hoogte_mm: float, waarde: str) -> None:
    from barcode.codex import Code128

    patroon = Code128(waarde, writer=None).build()[0]
    if not patroon:
        return
    modulebreedte = breedte_mm / len(patroon)

    p = ctx.painter
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(_INK)
    for i, teken in enumerate(patroon):
        if teken != "1":
            continue
        mx = x_mm + i * modulebreedte
        p.drawRect(QRectF(ctx.px(mx, y_mm), QPointF(ctx.mm(mx + modulebreedte), ctx.mm(y_mm + hoogte_mm))))
