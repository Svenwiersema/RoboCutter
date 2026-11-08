"""Ruwe test-ui voor onderdelen importeren (hoofdstuk 10).

GEEN voorbeeld van het uiteindelijke scherm (dat komt via de
mockup-workflow). Alleen om ``robocutter.importeren`` functioneel uit te
proberen: een CSV- of Excel-bestand kiezen, de gelezen regels en meldingen
bekijken, onbekende materialen koppelen (met "bedoelde je…?"-suggesties,
onthouden voor de volgende keer) en importeren in een testproject — zonder
styling.

Werkt bewust op een EIGEN testdatabase (``data/import_test/``), nooit op
de echte ``data/robocutter.db``. Bij de eerste start wordt de echte
database daarheen gekopieerd (alleen gelezen), zodat je eigen materialen
erin staan; "Testdatabase opnieuw kopiëren" begint opnieuw.

Draaien: python scripts/test_importeren_ui.py
(vereist: pip install -e ".[ui]")
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

_TEST_MAP = _REPO_ROOT / "data" / "import_test"
_TEST_DB = _TEST_MAP / "robocutter.db"

from PySide6.QtWidgets import (  # noqa: E402
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from robocutter.importeren import opslag as koppel_opslag  # noqa: E402
from robocutter.importeren.koppelen import MateriaalKoppelingen, normaliseer, stel_koppeling_voor, suggesties  # noqa: E402
from robocutter.importeren.lezen import lees_bestand, schrijf_sjabloon  # noqa: E402
from robocutter.importeren.toepassen import controleer, importeer_in_project  # noqa: E402
from robocutter.instellingen.beheer import InstellingenBeheer  # noqa: E402
from robocutter.materialen import opslag as mat_opslag  # noqa: E402
from robocutter.materialen.bibliotheek import MaterialenBibliotheek  # noqa: E402
from robocutter.modellen import opslag as mod_opslag  # noqa: E402
from robocutter.modellen.bibliotheek import ModellenBibliotheek  # noqa: E402
from robocutter.projecten import opslag as proj_opslag  # noqa: E402
from robocutter.projecten.bibliotheek import ProjectenBibliotheek  # noqa: E402
from robocutter.projecten.models import Project  # noqa: E402
from robocutter.projecten.zaaglijst import bouw_zaaglijst  # noqa: E402

_TESTPROJECT = "Importtest"


def _kopieer_echte_database() -> None:
    _TEST_MAP.mkdir(parents=True, exist_ok=True)
    echt = InstellingenBeheer().effectieve_db_pad()
    if _TEST_DB.exists():
        _TEST_DB.unlink()
    doel = sqlite3.connect(_TEST_DB)
    if echt.exists():
        bron = sqlite3.connect(f"file:{echt}?mode=ro", uri=True)
        bron.backup(doel)
        bron.close()
    doel.close()


class Venster(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Test: onderdelen importeren (testdatabase)")
        self.resize(1100, 760)
        self._open()
        self._resultaat = None
        self._koppeling: dict[str, str | None] = {}

        layout = QVBoxLayout(self)
        knoppen = QHBoxLayout()
        for tekst, actie in (
            ("Bestand kiezen…", self._kies_bestand),
            ("Sjabloon opslaan…", self._sjabloon),
            ("Onvolledige regels overslaan", self._sla_onvolledig_over),
            ("Importeren in project 'Importtest'", self._importeer),
            ("Testdatabase opnieuw kopiëren", self._opnieuw_kopieren),
        ):
            knop = QPushButton(tekst)
            knop.clicked.connect(actie)
            knoppen.addWidget(knop)
        layout.addLayout(knoppen)
        self._bestand = QLabel("Nog geen bestand gekozen.")
        layout.addWidget(self._bestand)
        layout.addWidget(QLabel("Regels:"))
        self._tabel = QTableWidget(0, 9)
        self._tabel.setHorizontalHeaderLabels(
            ["Regel", "Naam", "Materiaal (bestand)", "Lengte", "Breedte", "Aantal", "Model", "×", "Overig"]
        )
        layout.addWidget(self._tabel, 3)
        layout.addWidget(QLabel("Materialen koppelen (keuze wordt onthouden):"))
        self._koppel_box = QVBoxLayout()
        layout.addLayout(self._koppel_box)
        layout.addWidget(QLabel("Meldingen:"))
        self._meldingen = QListWidget()
        layout.addWidget(self._meldingen, 2)
        self._status = QLabel("")
        layout.addWidget(self._status)

    def _open(self) -> None:
        if not _TEST_DB.exists():
            _kopieer_echte_database()
        self._materialen = MaterialenBibliotheek(mat_opslag.open_verbinding(_TEST_DB))
        self._modellen = ModellenBibliotheek(self._materialen, mod_opslag.open_verbinding(_TEST_DB))
        self._projecten = ProjectenBibliotheek(self._modellen, self._materialen, proj_opslag.open_verbinding(_TEST_DB))
        self._onthouden = MateriaalKoppelingen(koppel_opslag.open_verbinding(_TEST_DB))

    def _opnieuw_kopieren(self) -> None:
        _kopieer_echte_database()
        self._open()
        self._ververs()
        self._status.setText("Testdatabase opnieuw gekopieerd van de echte database.")

    def _kies_bestand(self) -> None:
        pad, _ = QFileDialog.getOpenFileName(self, "Importbestand", "", "Zaaglijst (*.csv *.xlsx)")
        if not pad:
            return
        self._bestand.setText(pad)
        self._resultaat = lees_bestand(pad)
        self._koppeling = stel_koppeling_voor(self._resultaat.regels, self._materialen, self._onthouden)
        self._ververs()

    def _sjabloon(self) -> None:
        pad, _ = QFileDialog.getSaveFileName(self, "Sjabloon opslaan", "RoboCutter-importsjabloon.xlsx", "Excel (*.xlsx)")
        if pad:
            schrijf_sjabloon(pad)
            self._status.setText(f"Sjabloon opgeslagen: {pad}")

    def _ververs(self) -> None:
        self._tabel.setRowCount(0)
        self._meldingen.clear()
        while self._koppel_box.count():
            item = self._koppel_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if self._resultaat is None:
            return
        regels = self._resultaat.regels
        self._tabel.setRowCount(len(regels))
        for rij, r in enumerate(regels):
            overig = " ".join(
                t for t in (
                    r.nerf.value if r.nerf.value != "geen" else "",
                    "".join(sorted(x.value[0].upper() for x in r.kantenband)),
                    "fabriek" if r.fabriekskantenband else "",
                    f"groep {r.groep}#{r.volgorde}" if r.groep else "",
                ) if t
            )
            for kolom, waarde in enumerate(
                [r.regelnummer, r.naam, r.materiaal, f"{r.lengte:g}", "" if r.breedte is None else f"{r.breedte:g}",
                 r.aantal, r.model, r.modelaantal if r.model else "", overig]
            ):
                self._tabel.setItem(rij, kolom, QTableWidgetItem(str(waarde)))
        teksten = {}
        for r in regels:
            teksten.setdefault(normaliseer(r.materiaal), r.materiaal)
        for sleutel, tekst in teksten.items():
            rij = QWidget()
            rij_layout = QHBoxLayout(rij)
            rij_layout.setContentsMargins(0, 0, 0, 0)
            rij_layout.addWidget(QLabel(f"'{tekst}' →"))
            combo = QComboBox()
            combo.addItem("— kies een materiaal —", "")
            voorstel = suggesties(tekst, self._materialen)
            for mid in voorstel:
                combo.addItem(f"bedoelde je: {self._materialen.ophalen(mid).naam}", mid)
            for m in sorted(self._materialen.lijst(), key=lambda m: m.naam.lower()):
                combo.addItem(m.naam, m.id)
            gekozen = self._koppeling.get(sleutel)
            if gekozen:
                combo.setCurrentIndex(combo.findData(gekozen))
            combo.currentIndexChanged.connect(lambda _i, s=sleutel, t=tekst, c=combo: self._kies(s, t, c.currentData()))
            rij_layout.addWidget(combo, 1)
            self._koppel_box.addWidget(rij)
        meldingen = list(self._resultaat.meldingen) + controleer(regels, self._koppeling, self._materialen)
        for m in meldingen:
            plek = (f"regel {m.regelnummer}: " if m.regelnummer else "") + (f"[{m.kolom}] " if m.kolom else "")
            self._meldingen.addItem(f"[{m.ernst.value}] {plek}{m.tekst}")
        if not meldingen:
            self._meldingen.addItem("Geen meldingen.")

    def _sla_onvolledig_over(self) -> None:
        # In het echte scherm vul je ze in; hier alleen overslaan.
        if self._resultaat is not None:
            self._resultaat.regels = [r for r in self._resultaat.regels if r.is_compleet]
            self._ververs()

    def _kies(self, sleutel: str, tekst: str, materiaal_id: str) -> None:
        self._koppeling[sleutel] = materiaal_id or None
        if materiaal_id:
            self._onthouden.onthoud(tekst, materiaal_id)
        self._ververs()

    def _importeer(self) -> None:
        if self._resultaat is None:
            self._status.setText("Kies eerst een bestand.")
            return
        project = next((p for p in self._projecten.lijst() if p.naam == _TESTPROJECT), None)
        if project is None:
            project = self._projecten.toevoegen(Project(id="", naam=_TESTPROJECT, klant="Test"))
        try:
            project = importeer_in_project(
                self._projecten, project.id, self._resultaat.regels, self._koppeling, self._materialen
            )
        except ValueError as exc:
            self._status.setText(f"Niet geïmporteerd: {exc}")
            return
        n = sum(r.onderdeel.aantal for r in bouw_zaaglijst(project))
        self._status.setText(
            f"Geïmporteerd in '{_TESTPROJECT}': {len(project.modelinstanties)} modellen, "
            f"{len(project.losse_onderdelen)} losse onderdelen, {n} stuks in de zaaglijst"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    venster = Venster()
    venster.show()
    sys.exit(app.exec())
