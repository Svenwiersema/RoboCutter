"""Klikbare tekening van een rechthoek (materiaal of onderdeel) met de
vier randen (Links/Rechts/Onder/Boven) als aanklikbare zones en de echte
afmetingen als maatlijn erlangs — vervangt de kale ``_rand_chip_rij``
(vier losse tekst-knoppen zonder verband met de vorm) voor
``randafzaag_randen``/``fabriekskantenband_randen`` (materialen_page.py)
en ``kantenband_randen`` (model_detail_page.py/project_detail_page.py).

Sven keurde het concept goed als HTML/Artifact-mockup (zie
OVERDRACHT.md): "je klikt de rand aan op de vorm zelf, en ziet er direct
de maat naast staan — geen giswerk meer welke zijde welke lengte heeft."
Aanleiding was een concreet datafoutje (een onderdeel met kantenband op
"Onder" terwijl die zijde met de opgegeven afmetingen nooit op de plaat
kon passen) — dit widget maakt zo'n mismatch meteen zichtbaar in plaats
van pas na het genereren van een zaagplan.

Eén instantie dekt alle drie de toepassingen: de aanroeper geeft gewoon
de twee relevante afmetingen (lengte/breedte, of breedte/hoogte) en het
al gekozen randen-``frozenset`` mee."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QToolButton, QWidget

from robocutter.optimalisatie.models import Rand
from robocutter.ui.theme import Theme

_RAND_LABEL = {Rand.BOVEN: "Boven", Rand.ONDER: "Onder", Rand.LINKS: "Links", Rand.RECHTS: "Rechts"}

_PLAAT_MAX = 172.0  # px, langste zijde van de getekende rechthoek
_PLAAT_MIN = 40.0
_MARGE_BOVEN = 34.0  # ruimte voor de breedte-maatlijn
_MARGE_LINKS = 46.0  # ruimte voor de hoogte-maatlijn
_MARGE_RECHTS_ONDER = 16.0
_RAND_DIKTE = 8.0
_RAND_TUSSENRUIMTE = 3.0


class RandenDiagram(QWidget):
    """``breedte``/``hoogte`` zijn puur weergave-afmetingen (mm) — deze
    klasse muteert geen model, roept alleen ``gewijzigd`` aan zodra de
    gebruiker een rand aan-/uitklikt."""

    gewijzigd = Signal()

    def __init__(self, theme: Theme, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = theme
        self._breedte = 100.0
        self._hoogte = 100.0
        self._geselecteerd: set[Rand] = set()

        self.setMinimumSize(int(_MARGE_LINKS + _PLAAT_MIN + _MARGE_RECHTS_ONDER), int(_MARGE_BOVEN + _PLAAT_MIN + _MARGE_RECHTS_ONDER))

        self._knoppen: dict[Rand, QToolButton] = {}
        for rand in Rand:
            knop = QToolButton(self)
            knop.setCheckable(True)
            knop.setCursor(Qt.CursorShape.PointingHandCursor)
            knop.setToolTip(_RAND_LABEL[rand])
            knop.setAutoRaise(True)
            knop.toggled.connect(lambda aan, r=rand: self._op_toggle(r, aan))
            self._knoppen[rand] = knop
        self._herstijl()

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        self._herstijl()
        self.update()

    def set_afmetingen(self, breedte: float, hoogte: float) -> None:
        self._breedte = max(breedte, 1.0)
        self._hoogte = max(hoogte, 1.0)
        self._herschik()
        self.update()

    def geselecteerde_randen(self) -> frozenset[Rand]:
        return frozenset(self._geselecteerd)

    def set_geselecteerde_randen(self, randen: frozenset[Rand] | set[Rand]) -> None:
        self._geselecteerd = set(randen)
        for rand, knop in self._knoppen.items():
            knop.blockSignals(True)
            knop.setChecked(rand in self._geselecteerd)
            knop.blockSignals(False)
        self.update()

    # ------------------------------------------------------------------
    def _op_toggle(self, rand: Rand, aan: bool) -> None:
        if aan:
            self._geselecteerd.add(rand)
        else:
            self._geselecteerd.discard(rand)
        self.update()
        self.gewijzigd.emit()

    def _herstijl(self) -> None:
        t = self._theme
        for knop in self._knoppen.values():
            knop.setStyleSheet(
                f"""
                QToolButton {{ background: {t.border}; border: none; border-radius: 3px; }}
                QToolButton:hover {{ background: {t.text_faint}; }}
                QToolButton:checked {{ background: {t.accent}; }}
                QToolButton:checked:hover {{ background: {t.accent_text}; }}
                """
            )

    def _plaat_rect(self) -> QRectF:
        beschikbaar_w = max(self.width() - _MARGE_LINKS - _MARGE_RECHTS_ONDER, _PLAAT_MIN)
        beschikbaar_h = max(self.height() - _MARGE_BOVEN - _MARGE_RECHTS_ONDER, _PLAAT_MIN)
        verhouding = self._breedte / self._hoogte
        w = beschikbaar_w
        h = w / verhouding if verhouding > 0 else beschikbaar_h
        if h > beschikbaar_h:
            h = beschikbaar_h
            w = h * verhouding
        w = max(min(w, _PLAAT_MAX), _PLAAT_MIN)
        h = max(min(h, _PLAAT_MAX), _PLAAT_MIN)
        x = _MARGE_LINKS + (beschikbaar_w - w) / 2
        y = _MARGE_BOVEN + (beschikbaar_h - h) / 2
        return QRectF(x, y, w, h)

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt-signatuur)
        super().resizeEvent(event)
        self._herschik()

    def _herschik(self) -> None:
        rect = self._plaat_rect()
        d, g = int(_RAND_DIKTE), int(_RAND_TUSSENRUIMTE)
        self._knoppen[Rand.BOVEN].setGeometry(int(rect.left()), int(rect.top() - g - d), int(rect.width()), d)
        self._knoppen[Rand.ONDER].setGeometry(int(rect.left()), int(rect.bottom() + g), int(rect.width()), d)
        self._knoppen[Rand.LINKS].setGeometry(int(rect.left() - g - d), int(rect.top()), d, int(rect.height()))
        self._knoppen[Rand.RECHTS].setGeometry(int(rect.right() + g), int(rect.top()), d, int(rect.height()))

    def sizeHint(self) -> QSize:
        return QSize(int(_MARGE_LINKS + _PLAAT_MAX + _MARGE_RECHTS_ONDER), int(_MARGE_BOVEN + _PLAAT_MAX + _MARGE_RECHTS_ONDER))

    # ------------------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802 (Qt-signatuur)
        t = self._theme
        rect = self._plaat_rect()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(QPen(QColor(t.border), 1.3))
        painter.setBrush(QColor(t.surface_2))
        painter.drawRoundedRect(rect, 3, 3)

        painter.setPen(QColor(t.text_faint))
        font = painter.font()
        font.setPointSizeF(max(font.pointSizeF() - 2.5, 7.5))
        painter.setFont(font)

        breedte_tekst = f"{self._breedte:g} mm"
        painter.drawText(
            QRectF(rect.left(), rect.top() - _MARGE_BOVEN, rect.width(), _MARGE_BOVEN - _RAND_DIKTE - _RAND_TUSSENRUIMTE - 2),
            Qt.AlignmentFlag.AlignCenter,
            breedte_tekst,
        )

        painter.save()
        painter.translate(rect.left() - _RAND_DIKTE - _RAND_TUSSENRUIMTE - 4, rect.center().y())
        painter.rotate(-90)
        hoogte_tekst = f"{self._hoogte:g} mm"
        painter.drawText(QRectF(-60, -12, 120, 24), Qt.AlignmentFlag.AlignCenter, hoogte_tekst)
        painter.restore()

        painter.end()
