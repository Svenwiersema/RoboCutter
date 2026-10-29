"""Plant de automatische back-up terwijl RoboCutter openstaat (hoofdstuk 12,
mockup ``design/assets/mockups/backup-concept.html``).

Kort na het opstarten en daarna elke ``_CONTROLE_MS`` kijkt de planner of
er volgens de gekozen frequentie een back-up nodig is. Mislukt er een (bv.
USB-stick niet aangesloten), dan blijft ``backup_nodig`` waar en probeert
hij het bij de volgende controle vanzelf opnieuw; de fout blijft zichtbaar
in de statusbalk en in Instellingen tot er een lukt. De back-up zelf loopt
in een eigen thread, zodat een trage netwerkmap de app niet laat haperen.

Eén gedeelde instantie in ``MainWindow``; de statusbalk en het Back-up-blok
in ``InstellingenPage`` luisteren naar ``gewijzigd``.
"""

from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from robocutter.backup.beheer import (
    BACKUP_INTERVAL,
    BackupBestand,
    BackupError,
    backup_nodig,
    laatste_backup,
    maak_backup,
    opruimen,
    zelfde_schijf,
    zet_terug,
)
from robocutter.instellingen.beheer import InstellingenBeheer

__all__ = ["BackupPlanner", "tijd_tekst", "datum_tijd_tekst", "grootte_tekst", "leeftijd_tekst"]

_START_MS = 3_000
_CONTROLE_MS = 10 * 60 * 1000

_DAGEN = ["ma", "di", "wo", "do", "vr", "za", "zo"]
_MAANDEN = ["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"]


def tijd_tekst(moment: datetime, nu: datetime | None = None) -> str:
    """"vandaag 13:52", "gisteren 13:47", "morgen 13:52" of "zo 27 okt 13:50"."""
    nu = nu or datetime.now()
    verschil = (moment.date() - nu.date()).days
    uur = f"{moment:%H:%M}"
    if verschil == 0:
        return f"vandaag {uur}"
    if verschil == -1:
        return f"gisteren {uur}"
    if verschil == 1:
        return f"morgen {uur}"
    return f"{_DAGEN[moment.weekday()]} {moment.day} {_MAANDEN[moment.month - 1]} {uur}"


def datum_tijd_tekst(moment: datetime) -> str:
    """"di 29 okt 2026 · 13:52"."""
    return f"{_DAGEN[moment.weekday()]} {moment.day} {_MAANDEN[moment.month - 1]} {moment.year} · {moment:%H:%M}"


def leeftijd_tekst(moment: datetime, vandaag: date | None = None) -> str:
    dagen = ((vandaag or date.today()) - moment.date()).days
    if dagen <= 0:
        return "Vandaag"
    if dagen == 1:
        return "Gisteren"
    if dagen < 7:
        return f"{dagen} dagen geleden"
    weken = dagen // 7
    return "1 week geleden" if weken == 1 else f"{weken} weken geleden"


def grootte_tekst(bytes_: int) -> str:
    if bytes_ >= 1024 * 1024:
        return f"{bytes_ / (1024 * 1024):.1f} MB".replace(".", ",")
    return f"{max(1, round(bytes_ / 1024))} kB"


class _BackupThread(QThread):
    klaar = Signal(object, str)  # BackupBestand | None, foutmelding

    def __init__(self, db_pad, backup_map) -> None:
        super().__init__()
        self._db_pad = db_pad
        self._backup_map = backup_map

    def run(self) -> None:
        try:
            backup = maak_backup(self._db_pad, self._backup_map)
        except BackupError as exc:
            self.klaar.emit(None, str(exc))
            return
        opruimen(self._backup_map)
        self.klaar.emit(backup, "")


class BackupPlanner(QObject):
    gewijzigd = Signal()
    # Na een gelukte back-up via "Nu back-up maken" (voor de melding).
    handmatig_gelukt = Signal(object)

    def __init__(self, beheer: InstellingenBeheer, parent=None) -> None:
        super().__init__(parent)
        self._beheer = beheer
        self._thread: _BackupThread | None = None
        self._handmatig = False
        self.fout: str = ""
        self.fout_moment: datetime | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(_CONTROLE_MS)
        self._timer.timeout.connect(self.controleer)

    def start(self) -> None:
        self._timer.start()
        QTimer.singleShot(_START_MS, self, self.controleer)

    def stop(self, wacht_ms: int = 5_000) -> None:
        self._timer.stop()
        if self._thread is not None:
            self._thread.wait(wacht_ms)

    # ------------------------------------------------------------------
    # Stand (voor statusbalk en Instellingen)
    # ------------------------------------------------------------------
    @property
    def backup_map(self):
        return self._beheer.effectieve_backup_map()

    @property
    def bezig(self) -> bool:
        return self._thread is not None

    def laatste(self) -> BackupBestand | None:
        return laatste_backup(self.backup_map)

    def volgende(self) -> datetime | None:
        laatste = self.laatste()
        if laatste is None:
            return None
        return laatste.tijdstip + BACKUP_INTERVAL[self._beheer.huidige.backup_frequentie]

    def op_zelfde_schijf(self) -> bool:
        return zelfde_schijf(self._beheer.effectieve_db_pad(), self.backup_map)

    # ------------------------------------------------------------------
    # Acties
    # ------------------------------------------------------------------
    def controleer(self) -> None:
        if self.bezig:
            return
        try:
            nodig = backup_nodig(self.backup_map, self._beheer.huidige.backup_frequentie)
        except OSError:
            nodig = True  # map onbereikbaar: de poging zelf meldt de fout
        if nodig:
            self._start_backup(handmatig=False)

    def nu_maken(self) -> None:
        if not self.bezig:
            self._start_backup(handmatig=True)

    def zet_terug(self, backup: BackupBestand) -> BackupBestand | None:
        """Zet ``backup`` terug (synchroon; de app herstart daarna). Gooit
        ``BackupError`` met een tekst voor de gebruiker."""
        self.stop()
        try:
            return zet_terug(backup.pad, self._beheer.effectieve_db_pad(), self.backup_map)
        except BackupError:
            self._timer.start()
            raise

    def _start_backup(self, handmatig: bool) -> None:
        self._handmatig = handmatig
        # Geen parent: de thread moet een paginawissel/thema-herbouw overleven
        # (zelfde reden als _ZaagplanWorker); stop() wacht hem af bij sluiten.
        self._thread = _BackupThread(self._beheer.effectieve_db_pad(), self.backup_map)
        self._thread.klaar.connect(self._klaar)
        self._thread.start()
        self.gewijzigd.emit()

    def _klaar(self, backup: BackupBestand | None, fout: str) -> None:
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.wait()
            thread.deleteLater()
        if backup is None:
            self.fout = fout
            self.fout_moment = datetime.now()
        else:
            self.fout = ""
            self.fout_moment = None
            if self._handmatig:
                self.handmatig_gelukt.emit(backup)
        self.gewijzigd.emit()
