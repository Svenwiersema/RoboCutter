"""De drie vensterknoppen (minimaliseren/maximaliseren/sluiten) rechts in
de donkere header, die de standaard Windows-titelbalk vervangen (zie
``ui/vensterframe.py``).

De symbolen worden zelf getekend met dunne lijnen, net als die van
Windows 11 zelf, i.p.v. via ``icons.py`` (Phosphor Bold is voor deze
kleine vensterknoppen te zwaar). Bewust een ``QWidget`` met eigen
``clicked``-signaal i.p.v. een ``QPushButton``/``QToolButton``: zo hoeft
er niets van de stylesheet doorheen te komen en blijft de hover-kleur
(rood bij sluiten) volledig in eigen hand.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QWidget

_BREEDTE = 46
_SLUIT_HOVER = "#C42B1C"  # dezelfde rode kleur als de Windows-sluitknop


class VensterKnop(QWidget):
    """Eén vensterknop; ``soort`` is ``"min"``, ``"max"`` of ``"sluit"``."""

    clicked = Signal()

    def __init__(self, soort: str, kleur: str, kleur_hover: str, parent=None) -> None:
        super().__init__(parent)
        self._soort = soort
        self._kleur = QColor(kleur)
        self._kleur_hover = QColor(kleur_hover)
        self._hover = False
        self._ingedrukt = False
        self._gemaximaliseerd = False
        self.setFixedWidth(_BREEDTE)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setToolTip({"min": "Minimaliseren", "max": "Maximaliseren", "sluit": "Sluiten"}[soort])

    def zet_gemaximaliseerd(self, gemaximaliseerd: bool) -> None:
        self._gemaximaliseerd = gemaximaliseerd
        if self._soort == "max":
            self.setToolTip("Vorige grootte" if gemaximaliseerd else "Maximaliseren")
        self.update()

    def herbepaal_hover(self) -> None:
        # Na maximaliseren/herstellen schuift de knop onder de muis vandaan
        # zonder dat Qt een leaveEvent stuurt — anders blijft hij "gehoverd".
        self._hover = self.isVisible() and self.rect().contains(self.mapFromGlobal(QCursor.pos()))
        self._ingedrukt = False
        self.update()

    def zet_native_toestand(self, hover: bool, ingedrukt: bool) -> None:
        """Voor de maximaliseerknop: die krijgt zijn muis via Windows'
        niet-client-berichten i.p.v. Qt-events (zie ``vensterframe.py``,
        nodig voor de Windows 11-schermindelingen)."""
        if (hover, ingedrukt) != (self._hover, self._ingedrukt):
            self._hover = hover
            self._ingedrukt = ingedrukt
            self.update()

    def is_native_ingedrukt(self) -> bool:
        return self._ingedrukt

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self._ingedrukt = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._ingedrukt = True
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._ingedrukt:
            self._ingedrukt = False
            self.update()
            if self.rect().contains(event.position().toPoint()):
                self.clicked.emit()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        if self._hover:
            if self._soort == "sluit":
                achtergrond = QColor(_SLUIT_HOVER)
                if self._ingedrukt:
                    achtergrond = achtergrond.darker(115)
            else:
                achtergrond = QColor(255, 255, 255, 30 if self._ingedrukt else 18)
            painter.fillRect(self.rect(), achtergrond)

        kleur = self._kleur
        if self._hover:
            kleur = QColor("#FFFFFF") if self._soort == "sluit" else self._kleur_hover
        pen = QPen(kleur, 1.0)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        cx = self.width() / 2
        cy = self.height() / 2
        h = 5.0  # halve symboolgrootte (10 px symbool, zoals Windows 11)
        if self._soort == "min":
            painter.drawLine(QPointF(cx - h, cy + 0.5), QPointF(cx + h, cy + 0.5))
        elif self._soort == "max":
            if self._gemaximaliseerd:
                # Twee overlappende vierkantjes: "vorige grootte".
                painter.drawRoundedRect(QRectF(cx - h, cy - h + 2, 2 * h - 2, 2 * h - 2), 1.2, 1.2)
                painter.drawLine(QPointF(cx - h + 2, cy - h), QPointF(cx + h - 1, cy - h))
                painter.drawLine(QPointF(cx + h, cy - h + 1), QPointF(cx + h, cy + h - 2))
            else:
                painter.drawRoundedRect(QRectF(cx - h, cy - h, 2 * h, 2 * h), 1.5, 1.5)
        else:
            painter.drawLine(QPointF(cx - h, cy - h), QPointF(cx + h, cy + h))
            painter.drawLine(QPointF(cx - h, cy + h), QPointF(cx + h, cy - h))


class VensterKnoppen(QWidget):
    """De drie knoppen naast elkaar, gekoppeld aan ``venster``."""

    def __init__(self, venster: QWidget, kleur: str, kleur_hover: str, parent=None) -> None:
        super().__init__(parent)
        self._venster = venster
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.min_knop = VensterKnop("min", kleur, kleur_hover)
        self.max_knop = VensterKnop("max", kleur, kleur_hover)
        self.sluit_knop = VensterKnop("sluit", kleur, kleur_hover)
        self.min_knop.clicked.connect(venster.showMinimized)
        self.max_knop.clicked.connect(self._wissel_maximaliseren)
        self.sluit_knop.clicked.connect(venster.close)
        for knop in (self.min_knop, self.max_knop, self.sluit_knop):
            layout.addWidget(knop)
        self.werk_status_bij()

    def _wissel_maximaliseren(self) -> None:
        if self._venster.isMaximized():
            self._venster.showNormal()
        else:
            self._venster.showMaximized()

    def werk_status_bij(self) -> None:
        self.max_knop.zet_gemaximaliseerd(self._venster.isMaximized())
        # Uitgesteld: tijdens de toestandswissel klopt de geometrie nog niet.
        QTimer.singleShot(0, self._herbepaal_hover)

    def _herbepaal_hover(self) -> None:
        for knop in (self.min_knop, self.max_knop, self.sluit_knop):
            knop.herbepaal_hover()
