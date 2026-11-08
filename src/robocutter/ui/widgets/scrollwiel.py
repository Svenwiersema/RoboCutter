"""Keuzelijsten (QComboBox) reageren in heel RoboCutter alleen op het
scrollwiel als je er eerst op geklikt hebt.

Standaard verandert Qt de keuze al als je met de muis over een keuzelijst
zweeft en scrolt — zo kwamen in Svens test van het importvenster drie
materiaalkoppelingen door elkaar ("dit kan heel makkelijk per ongeluk
gaan"). Zonder focus gaat het scrollen nu naar de pagina eronder, zodat die
gewoon doorscrolt. Een geopende keuzelijst (de lijst zelf) scrolt normaal.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QAbstractScrollArea, QApplication, QComboBox

__all__ = ["ScrollwielFilter"]


class ScrollwielFilter(QObject):
    """Eén keer installeren op de QApplication (zie ``app.main``)."""

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802 (Qt-signatuur)
        if event.type() == QEvent.Type.Polish and isinstance(obj, QComboBox):
            # Standaard krijgt een keuzelijst focus door eroverheen te scrollen
            # (WheelFocus) — nog vóór dit filter het scrollen ziet. Alleen nog
            # focus door klikken of Tab.
            obj.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        if event.type() == QEvent.Type.Wheel and isinstance(obj, QComboBox) and not obj.hasFocus():
            # Naar het dichtstbijzijnde scrollgebied dat ook echt kan scrollen
            # (een doorgestuurd event gaat in Qt niet vanzelf omhoog).
            ouder = obj.parentWidget()
            while ouder is not None:
                if isinstance(ouder, QAbstractScrollArea) and ouder.verticalScrollBar().maximum() > 0:
                    QApplication.sendEvent(ouder.viewport(), event)
                    break
                ouder = ouder.parentWidget()
            return True
        return super().eventFilter(obj, event)
