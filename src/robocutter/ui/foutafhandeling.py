"""Onverwachte fouten opvangen: wegschrijven in het logbestand
(``robocutter.logboek``) en een nette melding tonen, in plaats van dat de
.exe (zonder consolevenster) zonder iets te zeggen verdwijnt.

Geldt voor fouten in knoppen/signalen (PySide stuurt die naar
``sys.excepthook``), in gewone threads (``threading.excepthook``) en bij het
opstarten. Een fout uit een andere thread wordt via een signaal op de
hoofdthread gemeld (widgets mogen alleen daar). Dezelfde fout vlak na
elkaar geeft één melding; alles komt wel in het logbestand.
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QMessageBox

from robocutter.logboek import log_fout

__all__ = ["installeer_foutafhandeling", "open_logmap"]

_HERHAAL_SECONDEN = 10


def open_logmap(log_pad: Path) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(log_pad).parent)))


class _Melder(QObject):
    melden = Signal(str)

    def __init__(self, log_pad: Path) -> None:
        super().__init__()
        self._log_pad = Path(log_pad)
        self._open = False
        self._laatste: tuple[str, float] = ("", 0.0)
        self.melden.connect(self._toon)

    def _toon(self, samenvatting: str) -> None:
        nu = time.monotonic()
        if self._open or (samenvatting == self._laatste[0] and nu - self._laatste[1] < _HERHAAL_SECONDEN):
            return
        self._laatste = (samenvatting, nu)
        self._open = True
        try:
            venster = QMessageBox(QApplication.activeWindow())
            venster.setIcon(QMessageBox.Icon.Warning)
            venster.setWindowTitle("RoboCutter")
            venster.setText("Er ging iets mis in RoboCutter.")
            venster.setInformativeText(
                "Wat je al had opgeslagen, blijft bewaard. Probeer het nog een keer; gaat het opnieuw mis, "
                "bewaar dan het logbestand.\n\n"
                f"Fout: {samenvatting}\n\nLogbestand: {self._log_pad}"
            )
            logmap = venster.addButton("Logmap openen", QMessageBox.ButtonRole.ActionRole)
            venster.addButton(QMessageBox.StandardButton.Ok)
            venster.exec()
            if venster.clickedButton() is logmap:
                open_logmap(self._log_pad)
        finally:
            self._open = False


def installeer_foutafhandeling(app: QApplication, log_pad: Path) -> None:
    """Na het aanmaken van de QApplication aanroepen (zie ``app.main``)."""
    melder = _Melder(log_pad)
    melder.setParent(app)
    vorige = sys.excepthook

    def bij_fout(soort, fout, traceback, waar: str = "") -> None:
        if issubclass(soort, KeyboardInterrupt):
            vorige(soort, fout, traceback)
            return
        samenvatting = log_fout(soort, fout, traceback, waar)
        # Ook in een terminal zichtbaar (ontwikkelen); de exe heeft er geen.
        if sys.stderr is not None:
            vorige(soort, fout, traceback)
        melder.melden.emit(samenvatting)

    sys.excepthook = bij_fout
    threading.excepthook = lambda a: bij_fout(a.exc_type, a.exc_value, a.exc_traceback, f"thread {a.thread.name if a.thread else '?'}")
