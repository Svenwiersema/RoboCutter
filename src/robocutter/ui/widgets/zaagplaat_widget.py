"""Tekent één gegenereerde plaat (``ZaagplanResultaat``) met QPainter:
plaatrand, fabrieksrand-indicatie, geplaatste onderdelen, reststukken en
de zaagvolgorde — de PySide6-tegenhanger van de SVG-tekening in de
goedgekeurde HTML-mockup (``design/assets/mockups/``), maar met vaste
pixelgroottes voor tekst i.p.v. mm-geschaalde tekst (die bij een grote
plaat en een klein scherm onleesbaar zou worden)."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from robocutter.optimalisatie.models import Rand, ZaagplanResultaat
from robocutter.ui.theme import Theme


class ZaagplaatWidget(QWidget):
    # Klik op een onderdeel (index in resultaat.plaatsingen); alleen als
    # ``klikbaar`` aan staat (gezaagd afvinken in het Zaagplannen-paneel).
    onderdeel_geklikt = Signal(int)

    def __init__(
        self,
        resultaat: ZaagplanResultaat,
        naam_voor: Callable[[str], str],
        theme: Theme,
        parent=None,
        gezaagd: set[tuple[str, int]] | None = None,
        klikbaar: bool = False,
    ) -> None:
        super().__init__(parent)
        self._resultaat = resultaat
        self._naam_voor = naam_voor
        self._theme = theme
        # Al gezaagde onderdelen, als (onderdeel_id, instantie): gearceerd
        # met een vinkje (mockup deel-opnieuw-genereren-concept.html).
        self._gezaagd = gezaagd or set()
        self._klikbaar = klikbaar
        self._rects: list[QRectF] = []
        self.setMinimumHeight(160)
        if klikbaar:
            self.setMouseTracking(True)

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt-signatuur)
        if self._klikbaar and event.button() == Qt.MouseButton.LeftButton:
            for i, rect in enumerate(self._rects):
                if rect.contains(event.position()):
                    self.onderdeel_geklikt.emit(i)
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 (Qt-signatuur)
        if self._klikbaar:
            boven = any(rect.contains(event.position()) for rect in self._rects)
            self.setCursor(Qt.CursorShape.PointingHandCursor if boven else Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    def heightForWidth(self, width: int) -> int:
        mat = self._resultaat.materiaal
        if mat.lengte <= 0:
            return width
        verhouding = mat.breedte / mat.lengte
        return max(160, int(width * verhouding) + 24)

    def sizeHint(self) -> QSize:
        return QSize(800, self.heightForWidth(800))

    def resizeEvent(self, event) -> None:
        nieuwe_hoogte = self.heightForWidth(self.width())
        if nieuwe_hoogte != self.height():
            self.setFixedHeight(nieuwe_hoogte)
        super().resizeEvent(event)

    # ------------------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802 (Qt-signatuur)
        t = self._theme
        mat = self._resultaat.materiaal
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pad = 12.0
        beschikbaar_w = self.width() - 2 * pad
        beschikbaar_h = self.height() - 2 * pad
        if mat.lengte <= 0 or mat.breedte <= 0 or beschikbaar_w <= 0 or beschikbaar_h <= 0:
            painter.end()
            return
        schaal = min(beschikbaar_w / mat.lengte, beschikbaar_h / mat.breedte)
        plaat_w = mat.lengte * schaal
        plaat_h = mat.breedte * schaal
        ox = pad + (beschikbaar_w - plaat_w) / 2
        oy = pad + (beschikbaar_h - plaat_h) / 2

        # De motor legt y=0 aan de rand ONDER (zie engine._werkgebied), dus
        # y loopt hier omhoog: "onder" staat zo ook echt onderaan, net als in
        # de randtekening bij materialen/onderdelen (op Svens verzoek; vroeger
        # stond y=0 bovenaan en lag een onderdeel met kantenband onder
        # getekend tegen de bovenrand).
        def px(x_mm: float, y_mm: float) -> QPointF:
            return QPointF(ox + x_mm * schaal, oy + (mat.breedte - y_mm) * schaal)

        def rect_mm(x: float, y: float, b: float, h: float) -> QRectF:
            return QRectF(px(x, y), px(x + b, y + h)).normalized()

        # Plaatrand.
        painter.setPen(QPen(QColor(t.text), 2))
        painter.setBrush(QColor(t.surface))
        painter.drawRect(rect_mm(0, 0, mat.lengte, mat.breedte))

        # Reststukken (herbruikbaar).
        rest_pen = QPen(QColor(t.success), 2)
        rest_brush = QColor(t.success_soft)
        for r in self._resultaat.reststukken:
            rect = rect_mm(r.x, r.y, r.breedte, r.hoogte)
            painter.setPen(rest_pen)
            painter.setBrush(rest_brush)
            painter.drawRoundedRect(rect, 4, 4)
            self._teken_label(painter, rect, f"{r.breedte:g}×{r.hoogte:g}", "herbruikbaar", QColor(t.success_ink))

        # Geplaatste onderdelen.
        piece_pen = QPen(QColor(t.accent), 2)
        piece_brush = QColor(t.accent_soft)
        gezaagd_brush = QBrush(QColor(t.text_faint), Qt.BrushStyle.BDiagPattern)
        self._rects = []
        for i, p in enumerate(self._resultaat.plaatsingen, start=1):
            rect = rect_mm(p.x, p.y, p.breedte, p.hoogte)
            self._rects.append(rect)
            is_gezaagd = (p.onderdeel_id, p.instantie) in self._gezaagd
            painter.setPen(QPen(QColor(t.text_faint), 2) if is_gezaagd else piece_pen)
            painter.setBrush(QColor(t.surface_2) if is_gezaagd else piece_brush)
            painter.drawRoundedRect(rect, 4, 4)
            if is_gezaagd:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(gezaagd_brush)
                painter.drawRoundedRect(rect, 4, 4)
            naam = self._naam_voor(p.onderdeel_id)
            kleur = QColor(t.text_muted) if is_gezaagd else QColor(t.text)
            self._teken_label(painter, rect, f"{p.breedte:g}×{p.hoogte:g}", naam, kleur, nummer=i)
            if is_gezaagd:
                self._teken_vinkje(painter, rect)

        # Fabrieksrand(en): dikke amberkleurige lijn op elke rand van de
        # plaat die fabriekskantenband heeft (fysiek al vanaf de
        # leverancier voorzien, ongeacht welke rand de motor voor de
        # huidige onderdelen daadwerkelijk gebruikt heeft). Bewust NA de
        # onderdelen getekend: een onderdeel dat fabriekskantenband nodig
        # heeft ligt per definitie vlak tegen deze rand aan (zie
        # engine.py), dus zijn eigen rechthoekrand zou de lijn er anders
        # overheen tekenen.
        fabriek_pen = QPen(QColor(t.warning), 6)
        fabriek_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(fabriek_pen)
        for rand in mat.fabriekskantenband_randen:
            if rand == Rand.LINKS:
                painter.drawLine(px(0, 0), px(0, mat.breedte))
            elif rand == Rand.RECHTS:
                painter.drawLine(px(mat.lengte, 0), px(mat.lengte, mat.breedte))
            elif rand == Rand.ONDER:
                painter.drawLine(px(0, 0), px(mat.lengte, 0))
            else:  # BOVEN
                painter.drawLine(px(0, mat.breedte), px(mat.lengte, mat.breedte))

        # Zaagsnedes.
        painter.setPen(QPen(QColor(t.critical), 2.5, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for s in self._resultaat.zaagvolgorde:
            if s.richting == "verticaal":
                painter.drawLine(px(s.positie, s.start), px(s.positie, s.einde))
            else:
                painter.drawLine(px(s.start, s.positie), px(s.einde, s.positie))

        painter.end()

    def _teken_label(
        self, painter: QPainter, rect: QRectF, maat_tekst: str, naam: str, kleur: QColor, nummer: int | None = None
    ) -> None:
        if rect.width() < 46 or rect.height() < 26:
            return
        painter.setPen(QPen(kleur))
        font = QFont(painter.font())
        font.setPointSizeF(max(7.5, min(11.0, rect.height() / 9)))
        font.setBold(True)
        painter.setFont(font)
        kop = f"{nummer}. {naam}" if nummer is not None else naam
        boven = QRectF(rect.x() + 2, rect.y() + rect.height() / 2 - 16, rect.width() - 4, 14)
        painter.drawText(boven, Qt.AlignmentFlag.AlignCenter, self._elide(painter, kop, boven.width()))
        if rect.height() >= 40:
            font.setBold(False)
            font.setPointSizeF(max(7.0, font.pointSizeF() - 1.5))
            painter.setFont(font)
            onder = QRectF(rect.x() + 2, rect.y() + rect.height() / 2, rect.width() - 4, 13)
            painter.drawText(onder, Qt.AlignmentFlag.AlignCenter, maat_tekst)

    def _teken_vinkje(self, painter: QPainter, rect: QRectF) -> None:
        """Groen rondje met vinkje rechtsboven in een gezaagd onderdeel."""
        straal = 8.0 if min(rect.width(), rect.height()) >= 30 else 5.0
        midden = QPointF(rect.right() - straal - 4, rect.top() + straal + 4)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self._theme.success))
        painter.drawEllipse(midden, straal, straal)
        pen = QPen(QColor("#ffffff"), max(1.5, straal / 4))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        s = straal * 0.45
        painter.drawLine(QPointF(midden.x() - s, midden.y()), QPointF(midden.x() - s * 0.25, midden.y() + s * 0.7))
        painter.drawLine(QPointF(midden.x() - s * 0.25, midden.y() + s * 0.7), QPointF(midden.x() + s, midden.y() - s * 0.6))

    @staticmethod
    def _elide(painter: QPainter, tekst: str, breedte: float) -> str:
        metrics = painter.fontMetrics()
        return metrics.elidedText(tekst, Qt.TextElideMode.ElideRight, int(breedte))
