"""Ruwe test-ui voor de reststukkenbibliotheek-functie (Module 3).

Dit is GEEN voorbeeld van het uiteindelijke Reststukkenbibliotheek-
scherm (dat komt later via de mockup-workflow: eerst een HTML-concept,
dan pas PySide6). Dit script bestaat alleen om
``robocutter.reststukken`` functioneel te kunnen uittesten: toevoegen/
bewerken, live validatie, en de beschikbaar/gebruikt-workflow uit
hoofdstuk 3 — zonder styling of polish.

Een reststuk hoort bij een bestaand materiaal (zie
``robocutter.materialen``), dus dit script deelt hetzelfde
materialen-testbestand als ``test_materialen_ui.py``
(``data/materialen_test.db``) en heeft daarnaast een eigen
``data/reststukken_test.db``.

Draaien: python scripts/test_reststukken_ui.py
(vereist: pip install -e ".[ui]")
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

_MATERIALEN_DB_PAD = _REPO_ROOT / "data" / "materialen_test.db"
_RESTSTUKKEN_DB_PAD = _REPO_ROOT / "data" / "reststukken_test.db"

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.materialen.models import Materiaal, MateriaalType, Nerfrichting
from robocutter.materialen.opslag import open_verbinding as open_materialen_verbinding
from robocutter.reststukken.bibliotheek import (
    OngeldigeStatusOvergangError,
    ReststukkenBibliotheek,
    valideer,
)
from robocutter.reststukken.models import Reststuk, ReststukStatus
from robocutter.reststukken.opslag import open_verbinding as open_reststukken_verbinding

KOLOMMEN = ["Materiaal", "Type", "Afmetingen (resterend)", "Familie", "Herkomst", "Status"]


def _voorbeeld_materialen(bib: MaterialenBibliotheek) -> None:
    """Alleen zaaien als de bibliotheek nog leeg is — zelfde
    voorbeelddata als test_materialen_ui.py, zodat dit script ook
    standalone (zonder dat script eerst te draaien) te proberen is."""
    if bib.lijst():
        return
    bib.toevoegen(
        Materiaal(
            id="",
            naam="Eiken multiplex 18mm",
            type=MateriaalType.PLAAT,
            lengte=2800,
            breedte=2070,
            derde_afmeting=18,
            familie="Eiken multiplex",
            kleur_afwerking="Naturel",
            nerfrichting=Nerfrichting.LANGE_ZIJDE,
            kerf=4,
            min_reststukgrootte=300,
            productcode="EMP-18",
            leverancier="Houthandel Jansen",
            tags=("multiplex", "eiken"),
        )
    )
    bib.toevoegen(
        Materiaal(
            id="",
            naam="Vurenhouten regel 40x60",
            type=MateriaalType.BALK,
            lengte=3000,
            breedte=40,
            derde_afmeting=60,
            familie="Vurenhout regelwerk",
            kerf=3,
        )
    )


class ReststukkenTestVenster(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RoboCutter — reststukkenbibliotheek (test-ui)")
        self.resize(1050, 560)

        _MATERIALEN_DB_PAD.parent.mkdir(parents=True, exist_ok=True)
        self.materialen_verbinding = open_materialen_verbinding(_MATERIALEN_DB_PAD)
        self.materialen = MaterialenBibliotheek(self.materialen_verbinding)
        _voorbeeld_materialen(self.materialen)

        self.reststukken_verbinding = open_reststukken_verbinding(_RESTSTUKKEN_DB_PAD)
        self.bibliotheek = ReststukkenBibliotheek(self.materialen, self.reststukken_verbinding)
        self.huidig_id: str | None = None

        centraal = QWidget()
        self.setCentralWidget(centraal)
        layout = QHBoxLayout(centraal)

        layout.addLayout(self._bouw_lijst_kolom(), stretch=3)
        layout.addWidget(self._bouw_formulier_groep(), stretch=2)

        self._ververs_tabel()

    # -- linkerkolom: filters + tabel --------------------------------
    def _bouw_lijst_kolom(self) -> QVBoxLayout:
        kolom = QVBoxLayout()

        filters = QHBoxLayout()
        self.zoekveld = QLineEdit()
        self.zoekveld.setPlaceholderText('Zoeken op naam, familie, herkomst of maat, bijv. "eiken 800"…')
        self.zoekveld.textChanged.connect(self._ververs_tabel)
        filters.addWidget(self.zoekveld, stretch=2)

        self.type_filter = QComboBox()
        self.type_filter.addItem("Alle types", None)
        self.type_filter.addItem("Plaat", MateriaalType.PLAAT)
        self.type_filter.addItem("Balk", MateriaalType.BALK)
        self.type_filter.currentIndexChanged.connect(self._ververs_tabel)
        filters.addWidget(self.type_filter)

        self.status_filter = QComboBox()
        self.status_filter.addItem("Beschikbaar", ReststukStatus.BESCHIKBAAR)
        self.status_filter.addItem("Gebruikt", ReststukStatus.GEBRUIKT)
        self.status_filter.addItem("Alle statussen", None)
        self.status_filter.currentIndexChanged.connect(self._ververs_tabel)
        filters.addWidget(self.status_filter)

        kolom.addLayout(filters)

        self.tabel = QTableWidget(0, len(KOLOMMEN))
        self.tabel.setHorizontalHeaderLabels(KOLOMMEN)
        self.tabel.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabel.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabel.itemSelectionChanged.connect(self._selectie_gewijzigd)
        kolom.addWidget(self.tabel)

        acties = QHBoxLayout()
        self.knop_nieuw = QPushButton("Nieuw reststuk")
        self.knop_nieuw.clicked.connect(self._nieuw_reststuk)
        acties.addWidget(self.knop_nieuw)

        self.knop_gebruikt = QPushButton("Markeer als gebruikt")
        self.knop_gebruikt.clicked.connect(self._markeer_gebruikt)
        acties.addWidget(self.knop_gebruikt)

        self.knop_beschikbaar = QPushButton("Zet terug op beschikbaar")
        self.knop_beschikbaar.clicked.connect(self._zet_beschikbaar)
        acties.addWidget(self.knop_beschikbaar)

        self.knop_verwijderen = QPushButton("Verwijderen")
        self.knop_verwijderen.clicked.connect(self._verwijderen)
        acties.addWidget(self.knop_verwijderen)

        kolom.addLayout(acties)
        return kolom

    # -- rechterkolom: formulier --------------------------------------
    def _bouw_formulier_groep(self) -> QGroupBox:
        groep = QGroupBox("Reststuk-gegevens")
        form = QFormLayout(groep)

        self.veld_materiaal = QComboBox()
        form.addRow("Materiaal", self.veld_materiaal)

        self.veld_lengte = self._maak_afmeting_veld()
        form.addRow("Resterende lengte (mm)", self.veld_lengte)
        self.veld_breedte = self._maak_afmeting_veld()
        form.addRow("Resterende breedte (mm)", self.veld_breedte)

        self.veld_herkomst_project = QLineEdit()
        form.addRow("Herkomst project", self.veld_herkomst_project)
        self.veld_herkomst_model = QLineEdit()
        form.addRow("Herkomst model", self.veld_herkomst_model)

        self.label_fouten = QLabel("")
        self.label_fouten.setStyleSheet("color: #c0392b;")
        self.label_fouten.setWordWrap(True)
        form.addRow(self.label_fouten)

        self.knop_opslaan = QPushButton("Opslaan")
        self.knop_opslaan.clicked.connect(self._opslaan)
        form.addRow(self.knop_opslaan)

        self._ververs_materiaal_combo()
        return groep

    @staticmethod
    def _maak_afmeting_veld() -> QDoubleSpinBox:
        veld = QDoubleSpinBox()
        veld.setRange(0.01, 100000.0)
        veld.setDecimals(1)
        return veld

    def _ververs_materiaal_combo(self) -> None:
        huidige = self.veld_materiaal.currentData()
        self.veld_materiaal.clear()
        for materiaal in self.materialen.lijst():
            self.veld_materiaal.addItem(f"{materiaal.naam} ({materiaal.type.value})", materiaal.id)
        index = self.veld_materiaal.findData(huidige)
        if index >= 0:
            self.veld_materiaal.setCurrentIndex(index)

    # -- tabel vullen / selectie ---------------------------------------
    def _huidige_filters(self):
        return (
            self.status_filter.currentData(),
            self.type_filter.currentData(),
            self.zoekveld.text(),
        )

    def _ververs_tabel(self) -> None:
        status, type_filter, zoekterm = self._huidige_filters()
        reststukken = self.bibliotheek.lijst(status=status, type_filter=type_filter, zoekterm=zoekterm)

        self.tabel.clearContents()
        self.tabel.setRowCount(len(reststukken))
        for rij, reststuk in enumerate(reststukken):
            materiaal = self.bibliotheek.materiaal_van(reststuk)
            afmetingen = f"{reststuk.lengte:g} x {reststuk.breedte:g} x {materiaal.derde_afmeting:g}"
            herkomst = " / ".join(t for t in [reststuk.herkomst_project, reststuk.herkomst_model] if t) or "—"
            waarden = [materiaal.naam, materiaal.type.value, afmetingen, materiaal.familie, herkomst, reststuk.status.value]
            for kolom, waarde in enumerate(waarden):
                item = QTableWidgetItem(waarde)
                item.setData(Qt.ItemDataRole.UserRole, reststuk.id)
                self.tabel.setItem(rij, kolom, item)
        self.tabel.resizeColumnsToContents()

    def _geselecteerd_reststuk_id(self) -> str | None:
        rijen = self.tabel.selectionModel().selectedRows()
        if not rijen:
            return None
        item = self.tabel.item(rijen[0].row(), 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _selectie_gewijzigd(self) -> None:
        reststuk_id = self._geselecteerd_reststuk_id()
        if reststuk_id is None:
            return
        self._toon_in_formulier(self.bibliotheek.ophalen(reststuk_id))

    def _toon_in_formulier(self, reststuk: Reststuk) -> None:
        self.huidig_id = reststuk.id
        self._ververs_materiaal_combo()
        index = self.veld_materiaal.findData(reststuk.materiaal_id)
        if index >= 0:
            self.veld_materiaal.setCurrentIndex(index)
        self.veld_lengte.setValue(reststuk.lengte)
        self.veld_breedte.setValue(reststuk.breedte)
        self.veld_herkomst_project.setText(reststuk.herkomst_project)
        self.veld_herkomst_model.setText(reststuk.herkomst_model)
        self.label_fouten.setText("")

    def _nieuw_reststuk(self) -> None:
        self.huidig_id = None
        self.tabel.clearSelection()
        self._ververs_materiaal_combo()
        self.veld_lengte.setValue(0)
        self.veld_breedte.setValue(0)
        self.veld_herkomst_project.clear()
        self.veld_herkomst_model.clear()
        self.label_fouten.setText("")

    def _reststuk_uit_formulier(self) -> Reststuk:
        return Reststuk(
            id=self.huidig_id or "",
            materiaal_id=self.veld_materiaal.currentData(),
            lengte=self.veld_lengte.value(),
            breedte=self.veld_breedte.value(),
            herkomst_project=self.veld_herkomst_project.text(),
            herkomst_model=self.veld_herkomst_model.text(),
        )

    # -- acties ----------------------------------------------------------
    def _opslaan(self) -> None:
        reststuk = self._reststuk_uit_formulier()
        fouten = valideer(reststuk, self.materialen)
        if fouten:
            self.label_fouten.setText("\n".join(fouten))
            return
        self.label_fouten.setText("")

        if self.huidig_id is None:
            reststuk = self.bibliotheek.toevoegen(reststuk)
            self.huidig_id = reststuk.id
        else:
            reststuk.status = self.bibliotheek.ophalen(self.huidig_id).status
            self.bibliotheek.bijwerken(reststuk)

        self._ververs_tabel()

    def _markeer_gebruikt(self) -> None:
        self._voer_statusactie_uit(self.bibliotheek.markeer_gebruikt)

    def _zet_beschikbaar(self) -> None:
        self._voer_statusactie_uit(self.bibliotheek.zet_beschikbaar)

    def _verwijderen(self) -> None:
        reststuk_id = self._geselecteerd_reststuk_id()
        if reststuk_id is None:
            return
        self.bibliotheek.verwijderen(reststuk_id)
        self.huidig_id = None
        self._ververs_tabel()

    def _voer_statusactie_uit(self, actie) -> None:
        reststuk_id = self._geselecteerd_reststuk_id()
        if reststuk_id is None:
            return
        try:
            actie(reststuk_id)
        except OngeldigeStatusOvergangError as exc:
            QMessageBox.warning(self, "Actie niet mogelijk", str(exc))
            return
        self._ververs_tabel()


def main() -> None:
    app = QApplication(sys.argv)
    venster = ReststukkenTestVenster()
    venster.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
