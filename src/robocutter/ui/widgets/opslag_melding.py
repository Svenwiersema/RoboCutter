"""Korte, vanzelf verdwijnende bevestiging na een opslaan-actie.

Op Svens verzoek: "als je een model opslaat dat er een melding komt dat
ie is opgeslagen want nu druk je op de knop en moet je erop vertrouwen
dat ie het opgeslagen heeft" — en, na goedkeuring van de mockup, bij
álle opslaan-knoppen in de app. Een groene melding rechtsonder in de
pagina die na ``_ZICHTBAAR_MS`` vanzelf weer verdwijnt (klikken sluit
'm meteen): bewust geen ``QMessageBox`` — RoboCutter vermijdt pop-ups
die je moet wegklikken (zie de ``ValidationBanner``-aanpak voor fouten).

Zweeft als kind-widget boven de pagina die 'm aanmaakt (geen eigen
venster), en herpositioneert zich bij elke resize van die pagina. Een
complete, zelf-positionerende widget, dus — net als ``randen_diagram.py``
— in ``widgets/`` i.p.v. per pagina gedupliceerd.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from robocutter.ui.icons import icon_pixmap
from robocutter.ui.theme import Theme

_ZICHTBAAR_MS = 3000
_MARGE = 20


class OpslagMelding(QFrame):
    def __init__(self, pagina: QWidget, theme: Theme) -> None:
        super().__init__(pagina)
        self._pagina = pagina
        self.setObjectName("OpslagMelding")
        # Zonder deze vlag tekent een QWidget-subklasse zijn stylesheet-
        # achtergrond niet (zie CLAUDE.md, bekende Qt-valkuilen).
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 16, 10)
        layout.setSpacing(10)
        self._icoon = QLabel()
        layout.addWidget(self._icoon, 0, Qt.AlignmentFlag.AlignVCenter)
        tekst_kolom = QVBoxLayout()
        tekst_kolom.setSpacing(1)
        self._tekst = QLabel("")
        self._sub = QLabel("")
        tekst_kolom.addWidget(self._tekst)
        tekst_kolom.addWidget(self._sub)
        layout.addLayout(tekst_kolom)

        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(1.0)
        self.setGraphicsEffect(self._effect)
        self._vervaag = QPropertyAnimation(self._effect, b"opacity", self)
        self._vervaag.setDuration(250)
        self._vervaag.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._vervaag.finished.connect(self._na_vervagen)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._verberg)

        self.set_theme(theme)
        pagina.installEventFilter(self)
        self.hide()

    def set_theme(self, theme: Theme) -> None:
        self._icoon.setPixmap(icon_pixmap("check", theme.success, 16))
        self.setStyleSheet(
            f"QFrame#OpslagMelding {{ background: {theme.success_soft}; border: 1px solid {theme.success};"
            f" border-radius: 10px; }}"
            f"QLabel {{ background: transparent; color: {theme.success_ink}; }}"
        )
        self._tekst.setStyleSheet("font-weight: 700; font-size: 13px;")
        self._sub.setStyleSheet("font-size: 12px;")

    def toon(self, tekst: str, sub: str = "") -> None:
        self._tekst.setText(tekst)
        self._sub.setText(sub)
        self._sub.setVisible(bool(sub))
        self._vervaag.stop()
        self._effect.setOpacity(1.0)
        self.adjustSize()
        self._herpositioneer()
        self.show()
        self.raise_()
        self._timer.start(_ZICHTBAAR_MS)

    def mousePressEvent(self, event) -> None:
        self._timer.stop()
        self._verberg()

    def eventFilter(self, bron: QObject, event: QEvent) -> bool:
        if bron is self._pagina and event.type() == QEvent.Type.Resize and self.isVisible():
            self._herpositioneer()
        return False

    def _herpositioneer(self) -> None:
        maximale_breedte = max(200, self._pagina.width() - 2 * _MARGE)
        self.setMaximumWidth(maximale_breedte)
        self.adjustSize()
        self.move(self._pagina.width() - self.width() - _MARGE, self._pagina.height() - self.height() - _MARGE)

    def _verberg(self) -> None:
        self._vervaag.stop()
        self._vervaag.setStartValue(self._effect.opacity())
        self._vervaag.setEndValue(0.0)
        self._vervaag.start()

    def _na_vervagen(self) -> None:
        if self._effect.opacity() <= 0.01:
            self.hide()
