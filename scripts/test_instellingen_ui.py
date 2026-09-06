"""Ruwe test-ui voor de instellingen-functie.

Dit is GEEN voorbeeld van het uiteindelijke Opties-scherm (dat komt
later via de mockup-workflow: eerst een HTML-concept, dan pas PySide6).
Dit script bestaat alleen om ``robocutter.instellingen`` functioneel te
kunnen uittesten: instellingen tonen/bewerken, en de opslaglocatie
wijzigen (incl. het automatisch verplaatsen van een bestaand
databasebestand) — zonder styling of polish.

Gebruikt bewust EIGEN testbestanden, nooit de echte
``%APPDATA%\\RoboCutter\\instellingen.json`` of ``data/robocutter.db`` —
zie ``InstellingenBeheer``'s ``standaard_data_map``-parameter en de
memory over waarom dat hier extra belangrijk is (een eerdere versie van
de pytest-tests voor deze functie verplaatste per ongeluk het échte
ontwikkel-databasebestand).

Draaien: python scripts/test_instellingen_ui.py
(vereist: pip install -e ".[ui]")
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

_INSTELLINGEN_TEST_PAD = _REPO_ROOT / "data" / "instellingen_test.json"
_STANDAARD_TEST_DATA_MAP = _REPO_ROOT / "data" / "instellingen_test_data"

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from robocutter.instellingen.beheer import InstellingenBeheer, OpslagVerplaatsenError
from robocutter.instellingen.models import GELDIGE_THEMAS, GELDIGE_ZAAGSTRATEGIEEN


def _zorg_voor_demo_databestand(data_map: Path) -> None:
    """Zorgt dat er iets staat om te verplaatsen bij het uitproberen
    van "opslaglocatie wijzigen" — puur voor de demo, geen echte data."""
    data_map.mkdir(parents=True, exist_ok=True)
    demo_bestand = data_map / "robocutter.db"
    if not demo_bestand.exists():
        demo_bestand.write_text("demo-databasebestand voor de instellingen-test-ui", encoding="utf-8")


class InstellingenTestVenster(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RoboCutter — instellingen (test-ui)")
        self.resize(640, 480)

        _zorg_voor_demo_databestand(_STANDAARD_TEST_DATA_MAP)
        self.beheer = InstellingenBeheer(
            bestand_pad=_INSTELLINGEN_TEST_PAD,
            standaard_data_map=_STANDAARD_TEST_DATA_MAP,
        )

        centraal = QWidget()
        self.setCentralWidget(centraal)
        layout = QVBoxLayout(centraal)
        layout.addWidget(self._bouw_instellingen_groep())
        layout.addWidget(self._bouw_opslaglocatie_groep())
        layout.addStretch(1)

        self._toon_huidige_instellingen()
        self._toon_effectieve_paden()

    def _bouw_instellingen_groep(self) -> QGroupBox:
        groep = QGroupBox("Instellingen")
        form = QFormLayout(groep)

        self.veld_thema = QComboBox()
        self.veld_thema.addItems(GELDIGE_THEMAS)
        form.addRow("Thema", self.veld_thema)

        logo_rij = QHBoxLayout()
        self.veld_logo = QLineEdit()
        logo_rij.addWidget(self.veld_logo, 1)
        knop_logo_kiezen = QPushButton("Bestand kiezen…")
        knop_logo_kiezen.clicked.connect(self._kies_logo)
        logo_rij.addWidget(knop_logo_kiezen)
        form.addRow("Bedrijfslogo", logo_rij)

        self.veld_strategie = QComboBox()
        self.veld_strategie.addItems(GELDIGE_ZAAGSTRATEGIEEN)
        form.addRow("Standaard zaagstrategie", self.veld_strategie)

        self.veld_werkvoorbereider = QLineEdit()
        form.addRow("Werkvoorbereider-naam", self.veld_werkvoorbereider)

        self.label_fouten = QLabel("")
        self.label_fouten.setStyleSheet("color: #c0392b;")
        self.label_fouten.setWordWrap(True)
        form.addRow(self.label_fouten)

        knop_opslaan = QPushButton("Opslaan")
        knop_opslaan.clicked.connect(self._opslaan)
        form.addRow(knop_opslaan)

        return groep

    def _bouw_opslaglocatie_groep(self) -> QGroupBox:
        groep = QGroupBox("Opslaglocatie databasebestand")
        layout = QVBoxLayout(groep)

        self.label_huidige_locatie = QLabel("")
        self.label_huidige_locatie.setWordWrap(True)
        layout.addWidget(self.label_huidige_locatie)

        rij = QHBoxLayout()
        self.veld_nieuwe_map = QLineEdit()
        rij.addWidget(self.veld_nieuwe_map, 1)
        knop_map_kiezen = QPushButton("Map kiezen…")
        knop_map_kiezen.clicked.connect(self._kies_map)
        rij.addWidget(knop_map_kiezen)
        layout.addLayout(rij)

        knop_wijzigen = QPushButton("Opslaglocatie wijzigen (verplaatst bestaand bestand automatisch)")
        knop_wijzigen.clicked.connect(self._wijzig_opslaglocatie)
        layout.addWidget(knop_wijzigen)

        return groep

    def _toon_huidige_instellingen(self) -> None:
        instellingen = self.beheer.huidige
        self.veld_thema.setCurrentText(instellingen.thema)
        self.veld_logo.setText(instellingen.bedrijfslogo_pad or "")
        self.veld_strategie.setCurrentText(instellingen.standaard_zaagstrategie)
        self.veld_werkvoorbereider.setText(instellingen.werkvoorbereider_naam)
        self.label_fouten.setText("")

    def _toon_effectieve_paden(self) -> None:
        self.label_huidige_locatie.setText(
            f"Huidige databaselocatie: {self.beheer.effectieve_db_pad()}"
        )

    def _kies_logo(self) -> None:
        pad, _ = QFileDialog.getOpenFileName(self, "Kies een logobestand")
        if pad:
            self.veld_logo.setText(pad)

    def _kies_map(self) -> None:
        map_pad = QFileDialog.getExistingDirectory(self, "Kies een nieuwe opslaglocatie")
        if map_pad:
            self.veld_nieuwe_map.setText(map_pad)

    def _opslaan(self) -> None:
        try:
            self.beheer.bijwerken(
                thema=self.veld_thema.currentText(),
                bedrijfslogo_pad=self.veld_logo.text().strip() or None,
                standaard_zaagstrategie=self.veld_strategie.currentText(),
                werkvoorbereider_naam=self.veld_werkvoorbereider.text().strip(),
            )
        except ValueError as exc:
            self.label_fouten.setText(str(exc))
            return
        self.label_fouten.setText("Opgeslagen.")

    def _wijzig_opslaglocatie(self) -> None:
        nieuwe_map = self.veld_nieuwe_map.text().strip()
        if not nieuwe_map:
            return
        try:
            self.beheer.wijzig_opslaglocatie(Path(nieuwe_map))
        except OpslagVerplaatsenError as exc:
            QMessageBox.warning(self, "Kan niet wijzigen", str(exc))
            return
        self._toon_effectieve_paden()
        QMessageBox.information(self, "Gelukt", "Opslaglocatie gewijzigd (en bestand verplaatst indien nodig).")


def main() -> None:
    app = QApplication(sys.argv)
    venster = InstellingenTestVenster()
    venster.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
