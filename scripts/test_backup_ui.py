"""Ruwe test-ui voor de automatische back-up (hoofdstuk 12).

GEEN voorbeeld van het uiteindelijke scherm (dat komt via de
mockup-workflow in Instellingen). Alleen om ``robocutter.backup``
functioneel uit te proberen: back-up maken, de lijst bekijken, opruimen
volgens het bewaarschema en terugzetten — zonder styling.

Werkt bewust op een EIGEN testdatabase (``data/backup_test/``), nooit op
de echte ``data/robocutter.db``. "Testdatabase wijzigen" schrijft een
nieuwe waarde, zodat je na terugzetten ziet dat de oude terugkomt.

Draaien: python scripts/test_backup_ui.py
(vereist: pip install -e ".[ui]")
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

_TEST_MAP = _REPO_ROOT / "data" / "backup_test"
_TEST_DB = _TEST_MAP / "robocutter.db"
_TEST_BACKUPS = _TEST_MAP / "backups"

from PySide6.QtWidgets import (  # noqa: E402
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from robocutter.backup.beheer import (  # noqa: E402
    BackupError,
    backup_nodig,
    lijst_backups,
    maak_backup,
    opruimen,
    zet_terug,
    zelfde_schijf,
)


def _schrijf_waarde(waarde: str) -> None:
    _TEST_MAP.mkdir(parents=True, exist_ok=True)
    verbinding = sqlite3.connect(_TEST_DB)
    verbinding.execute("CREATE TABLE IF NOT EXISTS t (waarde TEXT)")
    verbinding.execute("DELETE FROM t")
    verbinding.execute("INSERT INTO t VALUES (?)", (waarde,))
    verbinding.commit()
    verbinding.close()


def _lees_waarde() -> str:
    if not _TEST_DB.exists():
        return "(geen database)"
    verbinding = sqlite3.connect(_TEST_DB)
    try:
        rij = verbinding.execute("SELECT waarde FROM t").fetchone()
        return rij[0] if rij else "(leeg)"
    finally:
        verbinding.close()


class Venster(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Back-up — ruwe test-ui")
        self.resize(640, 520)
        if not _TEST_DB.exists():
            _schrijf_waarde("eerste versie")

        layout = QVBoxLayout(self)
        self._inhoud = QLabel()
        layout.addWidget(self._inhoud)
        self._frequentie = QComboBox()
        self._frequentie.addItems(["uur", "dag", "week"])
        self._frequentie.setCurrentText("dag")
        self._frequentie.currentTextChanged.connect(self._ververs)
        layout.addWidget(self._frequentie)
        self._status = QLabel()
        self._status.setWordWrap(True)
        layout.addWidget(self._status)
        self._lijst = QListWidget()
        layout.addWidget(self._lijst, 1)

        knoppen = QHBoxLayout()
        for tekst, actie in [
            ("Testdatabase wijzigen", self._wijzig),
            ("Nu back-up maken", self._backup),
            ("Oude back-ups simuleren (40 dagen)", self._simuleer),
            ("Opruimen", self._opruimen),
            ("Geselecteerde terugzetten", self._terugzetten),
        ]:
            knop = QPushButton(tekst)
            knop.clicked.connect(actie)
            knoppen.addWidget(knop)
        layout.addLayout(knoppen)
        self._ververs()

    def _ververs(self, melding: str = "") -> None:
        self._inhoud.setText(f"Inhoud testdatabase: {_lees_waarde()}")
        nodig = backup_nodig(_TEST_BACKUPS, self._frequentie.currentText())
        schijf = "zelfde schijf als de database" if zelfde_schijf(_TEST_DB, _TEST_BACKUPS) else "andere schijf"
        self._status.setText(f"Back-up nodig: {'ja' if nodig else 'nee'} · {schijf}. {melding}")
        self._lijst.clear()
        for backup in lijst_backups(_TEST_BACKUPS):
            item = QListWidgetItem(f"{backup.tijdstip:%Y-%m-%d %H:%M:%S} · {backup.grootte} bytes · {backup.pad.name}")
            item.setData(256, str(backup.pad))
            self._lijst.addItem(item)

    def _wijzig(self) -> None:
        _schrijf_waarde(f"gewijzigd om {datetime.now():%H:%M:%S}")
        self._ververs()

    def _backup(self) -> None:
        try:
            backup = maak_backup(_TEST_DB, _TEST_BACKUPS)
        except BackupError as exc:
            self._ververs(str(exc))
            return
        self._ververs(f"Gemaakt: {backup.pad.name}")

    def _simuleer(self) -> None:
        for dag in range(1, 41):
            maak_backup(_TEST_DB, _TEST_BACKUPS, datetime.now() - timedelta(days=dag))
        self._ververs("40 oude back-ups aangemaakt.")

    def _opruimen(self) -> None:
        self._ververs(f"{len(opruimen(_TEST_BACKUPS))} back-ups opgeruimd.")

    def _terugzetten(self) -> None:
        item = self._lijst.currentItem()
        if item is None:
            self._ververs("Kies eerst een back-up.")
            return
        try:
            veilig = zet_terug(Path(item.data(256)), _TEST_DB, _TEST_BACKUPS)
        except BackupError as exc:
            self._ververs(str(exc))
            return
        self._ververs(f"Teruggezet; huidige stand eerst bewaard als {veilig.pad.name if veilig else '—'}.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    venster = Venster()
    venster.show()
    sys.exit(app.exec())
