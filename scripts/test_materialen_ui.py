"""Ruwe test-ui voor de materialenbibliotheek-functie (Module 3).

Dit is GEEN voorbeeld van het uiteindelijke Materialenbibliotheek-
scherm (dat komt later via de mockup-workflow: eerst een HTML-concept,
dan pas PySide6, zie ``design/chapters/11-ux-ui.md``). Dit script
bestaat alleen om ``robocutter.materialen`` functioneel te kunnen
uittesten: toevoegen/bewerken, live validatie, en de archiveer-/
verwijderworkflow uit hoofdstuk 3 — zonder styling of polish.

Slaat op in een lokaal SQLite-bestand (``data/materialen_test.db``,
zie ``robocutter.materialen.opslag``) zodat materialen tussen
sessies bewaard blijven — nog geen gedeelde/multi-gebruiker-opslag
(zie hoofdstuk 8: dat vereist een lokale netwerk-server, niet zomaar
een gedeeld bestand op een NAS).

Draaien: python scripts/test_materialen_ui.py
(vereist: pip install -e ".[ui]")
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

_DB_PAD = _REPO_ROOT / "data" / "materialen_test.db"

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
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

from robocutter.materialen.bibliotheek import (
    MaterialenBibliotheek,
    OngeldigeStatusOvergangError,
    valideer,
)
from robocutter.materialen.opslag import open_verbinding
from robocutter.materialen.models import (
    Materiaal,
    MateriaalStatus,
    MateriaalType,
    Nerfrichting,
    Rand,
)

KOLOMMEN = ["Naam", "Type", "Afmetingen (l x b x d/h)", "Familie", "Status"]


def _voorbeelddata(bib: MaterialenBibliotheek) -> None:
    """Alleen zaaien als de bibliotheek nog leeg is (eerste run) —
    anders duiken deze na een herstart telkens opnieuw op naast de
    intussen al opgeslagen materialen."""
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
    balk = bib.toevoegen(
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
    bib.archiveren(balk.id)


class MaterialenTestVenster(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RoboCutter — materialenbibliotheek (test-ui)")
        self.resize(1000, 560)

        _DB_PAD.parent.mkdir(parents=True, exist_ok=True)
        self.db_verbinding = open_verbinding(_DB_PAD)
        self.bibliotheek = MaterialenBibliotheek(self.db_verbinding)
        _voorbeelddata(self.bibliotheek)
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
        self.zoekveld.setPlaceholderText("Zoeken op naam, familie, productcode of tag…")
        self.zoekveld.textChanged.connect(self._ververs_tabel)
        filters.addWidget(self.zoekveld, stretch=2)

        self.type_filter = QComboBox()
        self.type_filter.addItem("Alle types", None)
        self.type_filter.addItem("Plaat", MateriaalType.PLAAT)
        self.type_filter.addItem("Balk", MateriaalType.BALK)
        self.type_filter.currentIndexChanged.connect(self._ververs_tabel)
        filters.addWidget(self.type_filter)

        self.status_filter = QComboBox()
        self.status_filter.addItem("Actief", MateriaalStatus.ACTIEF)
        self.status_filter.addItem("Gearchiveerd", MateriaalStatus.GEARCHIVEERD)
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
        self.knop_nieuw = QPushButton("Nieuw materiaal")
        self.knop_nieuw.clicked.connect(self._nieuw_materiaal)
        acties.addWidget(self.knop_nieuw)

        self.knop_archiveren = QPushButton("Archiveren")
        self.knop_archiveren.clicked.connect(self._archiveren)
        acties.addWidget(self.knop_archiveren)

        self.knop_heractiveren = QPushButton("Terugzetten naar actief")
        self.knop_heractiveren.clicked.connect(self._heractiveren)
        acties.addWidget(self.knop_heractiveren)

        self.knop_verwijderen = QPushButton("Definitief verwijderen")
        self.knop_verwijderen.clicked.connect(self._verwijderen)
        acties.addWidget(self.knop_verwijderen)

        kolom.addLayout(acties)
        return kolom

    # -- rechterkolom: formulier --------------------------------------
    def _bouw_formulier_groep(self) -> QGroupBox:
        groep = QGroupBox("Materiaal-gegevens")
        form = QFormLayout(groep)

        self.veld_naam = QLineEdit()
        form.addRow("Naam", self.veld_naam)

        self.veld_type = QComboBox()
        self.veld_type.addItem("Plaat", MateriaalType.PLAAT)
        self.veld_type.addItem("Balk", MateriaalType.BALK)
        self.veld_type.currentIndexChanged.connect(self._type_gewijzigd)
        form.addRow("Type", self.veld_type)

        self.veld_lengte = self._maak_afmeting_veld()
        form.addRow("Lengte (mm)", self.veld_lengte)
        self.veld_breedte = self._maak_afmeting_veld()
        form.addRow("Breedte (mm)", self.veld_breedte)
        self.veld_derde_afmeting = self._maak_afmeting_veld()
        self.label_derde_afmeting = QLabel("Dikte (mm)")
        form.addRow(self.label_derde_afmeting, self.veld_derde_afmeting)

        self.veld_familie = QLineEdit()
        form.addRow("Materiaalfamilie", self.veld_familie)

        self.veld_kleur = QLineEdit()
        form.addRow("Kleur/afwerking", self.veld_kleur)

        self.veld_nerfrichting = QComboBox()
        for waarde, label in [
            (Nerfrichting.GEEN, "Geen"),
            (Nerfrichting.LANGE_ZIJDE, "Lange zijde"),
            (Nerfrichting.KORTE_ZIJDE, "Korte zijde"),
        ]:
            self.veld_nerfrichting.addItem(label, waarde)
        form.addRow("Nerfrichting", self.veld_nerfrichting)

        self.veld_kerf = self._maak_afmeting_veld(toegestaan_nul=True)
        form.addRow("Zaagsnede/kerf-breedte (mm)", self.veld_kerf)

        self.veld_randafzaag_marge = self._maak_afmeting_veld(toegestaan_nul=True)
        form.addRow("Randafzaag-marge (mm)", self.veld_randafzaag_marge)

        self.randafzaag_checks = self._maak_rand_checkboxen()
        form.addRow("Randafzaag op", self._checkboxen_rij(self.randafzaag_checks))

        self.veld_min_reststuk = self._maak_afmeting_veld(toegestaan_nul=True)
        form.addRow("Min. reststukgrootte (mm)", self.veld_min_reststuk)

        self.veld_mes_groef = QLineEdit()
        form.addRow("Mes/groef-notitie", self.veld_mes_groef)

        self.fabriekskant_checks = self._maak_rand_checkboxen()
        form.addRow("Fabriekskantenband op", self._checkboxen_rij(self.fabriekskant_checks))

        self.veld_productcode = QLineEdit()
        form.addRow("Productcode/artikelnummer", self.veld_productcode)

        self.veld_leverancier = QLineEdit()
        form.addRow("Leverancier", self.veld_leverancier)

        self.veld_tags = QLineEdit()
        self.veld_tags.setPlaceholderText("komma-gescheiden")
        form.addRow("Tags", self.veld_tags)

        self.label_fouten = QLabel("")
        self.label_fouten.setStyleSheet("color: #c0392b;")
        self.label_fouten.setWordWrap(True)
        form.addRow(self.label_fouten)

        self.knop_opslaan = QPushButton("Opslaan")
        self.knop_opslaan.clicked.connect(self._opslaan)
        form.addRow(self.knop_opslaan)

        return groep

    @staticmethod
    def _maak_afmeting_veld(toegestaan_nul: bool = False) -> QDoubleSpinBox:
        veld = QDoubleSpinBox()
        veld.setRange(0.0 if toegestaan_nul else 0.01, 100000.0)
        veld.setDecimals(1)
        return veld

    @staticmethod
    def _maak_rand_checkboxen() -> dict[Rand, QCheckBox]:
        return {rand: QCheckBox(rand.value) for rand in Rand}

    @staticmethod
    def _checkboxen_rij(checks: dict[Rand, QCheckBox]) -> QWidget:
        rij = QWidget()
        layout = QHBoxLayout(rij)
        layout.setContentsMargins(0, 0, 0, 0)
        for check in checks.values():
            layout.addWidget(check)
        return rij

    def _type_gewijzigd(self) -> None:
        type_ = self.veld_type.currentData()
        self.label_derde_afmeting.setText(
            "Dikte (mm)" if type_ == MateriaalType.PLAAT else "Hoogte (mm)"
        )

    # -- tabel vullen / selectie ---------------------------------------
    def _huidige_filters(self):
        return (
            self.status_filter.currentData(),
            self.type_filter.currentData(),
            self.zoekveld.text(),
        )

    def _ververs_tabel(self) -> None:
        status, type_filter, zoekterm = self._huidige_filters()
        materialen = self.bibliotheek.lijst(
            status=status, type_filter=type_filter, zoekterm=zoekterm
        )

        self.tabel.setRowCount(len(materialen))
        for rij, materiaal in enumerate(materialen):
            afmetingen = f"{materiaal.lengte:g} x {materiaal.breedte:g} x {materiaal.derde_afmeting:g}"
            waarden = [
                materiaal.naam,
                materiaal.type.value,
                afmetingen,
                materiaal.familie,
                materiaal.status.value,
            ]
            for kolom, waarde in enumerate(waarden):
                item = QTableWidgetItem(waarde)
                item.setData(Qt.ItemDataRole.UserRole, materiaal.id)
                self.tabel.setItem(rij, kolom, item)
        self.tabel.resizeColumnsToContents()

    def _geselecteerd_materiaal_id(self) -> str | None:
        rijen = self.tabel.selectionModel().selectedRows()
        if not rijen:
            return None
        item = self.tabel.item(rijen[0].row(), 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _selectie_gewijzigd(self) -> None:
        materiaal_id = self._geselecteerd_materiaal_id()
        if materiaal_id is None:
            return
        materiaal = self.bibliotheek.ophalen(materiaal_id)
        self._toon_in_formulier(materiaal)

    def _toon_in_formulier(self, materiaal: Materiaal) -> None:
        self.huidig_id = materiaal.id
        self.veld_naam.setText(materiaal.naam)
        self._zet_combo(self.veld_type, materiaal.type)
        self.veld_lengte.setValue(materiaal.lengte)
        self.veld_breedte.setValue(materiaal.breedte)
        self.veld_derde_afmeting.setValue(materiaal.derde_afmeting)
        self.veld_familie.setText(materiaal.familie)
        self.veld_kleur.setText(materiaal.kleur_afwerking)
        self._zet_combo(self.veld_nerfrichting, materiaal.nerfrichting)
        self.veld_kerf.setValue(materiaal.kerf)
        self.veld_randafzaag_marge.setValue(materiaal.randafzaag_marge)
        for rand, check in self.randafzaag_checks.items():
            check.setChecked(rand in materiaal.randafzaag_randen)
        self.veld_min_reststuk.setValue(materiaal.min_reststukgrootte)
        self.veld_mes_groef.setText(materiaal.mes_groef_notitie)
        for rand, check in self.fabriekskant_checks.items():
            check.setChecked(rand in materiaal.fabriekskantenband_randen)
        self.veld_productcode.setText(materiaal.productcode)
        self.veld_leverancier.setText(materiaal.leverancier)
        self.veld_tags.setText(", ".join(materiaal.tags))
        self.label_fouten.setText("")

    @staticmethod
    def _zet_combo(combo: QComboBox, waarde) -> None:
        index = combo.findData(waarde)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _nieuw_materiaal(self) -> None:
        self.huidig_id = None
        self.tabel.clearSelection()
        for veld in (
            self.veld_naam,
            self.veld_familie,
            self.veld_kleur,
            self.veld_mes_groef,
            self.veld_productcode,
            self.veld_leverancier,
            self.veld_tags,
        ):
            veld.clear()
        for veld in (
            self.veld_lengte,
            self.veld_breedte,
            self.veld_derde_afmeting,
            self.veld_kerf,
            self.veld_randafzaag_marge,
            self.veld_min_reststuk,
        ):
            veld.setValue(0)
        for check in {**self.randafzaag_checks, **self.fabriekskant_checks}.values():
            check.setChecked(False)
        self.label_fouten.setText("")
        self.veld_naam.setFocus()

    def _materiaal_uit_formulier(self) -> Materiaal:
        return Materiaal(
            id=self.huidig_id or "",
            naam=self.veld_naam.text(),
            # PySide6 slaat een str-Enum in combo-userdata op als kale str
            # terug op (het is er immers letterlijk een), dus expliciet
            # terugzetten naar het echte enum-lid.
            type=MateriaalType(self.veld_type.currentData()),
            lengte=self.veld_lengte.value(),
            breedte=self.veld_breedte.value(),
            derde_afmeting=self.veld_derde_afmeting.value(),
            familie=self.veld_familie.text(),
            kleur_afwerking=self.veld_kleur.text(),
            nerfrichting=Nerfrichting(self.veld_nerfrichting.currentData()),
            kerf=self.veld_kerf.value(),
            randafzaag_marge=self.veld_randafzaag_marge.value(),
            randafzaag_randen=frozenset(
                rand for rand, check in self.randafzaag_checks.items() if check.isChecked()
            ),
            min_reststukgrootte=self.veld_min_reststuk.value(),
            mes_groef_notitie=self.veld_mes_groef.text(),
            fabriekskantenband_randen=frozenset(
                rand for rand, check in self.fabriekskant_checks.items() if check.isChecked()
            ),
            productcode=self.veld_productcode.text(),
            leverancier=self.veld_leverancier.text(),
            tags=tuple(t.strip() for t in self.veld_tags.text().split(",") if t.strip()),
        )

    # -- acties ----------------------------------------------------------
    def _opslaan(self) -> None:
        materiaal = self._materiaal_uit_formulier()
        fouten = valideer(materiaal)
        if fouten:
            self.label_fouten.setText("\n".join(fouten))
            return
        self.label_fouten.setText("")

        if self.huidig_id is None:
            materiaal = self.bibliotheek.toevoegen(materiaal)
            self.huidig_id = materiaal.id
        else:
            materiaal.status = self.bibliotheek.ophalen(self.huidig_id).status
            self.bibliotheek.bijwerken(materiaal)

        self._ververs_tabel()

    def _archiveren(self) -> None:
        self._voer_statusactie_uit(self.bibliotheek.archiveren)

    def _heractiveren(self) -> None:
        self._voer_statusactie_uit(self.bibliotheek.heractiveren)

    def _verwijderen(self) -> None:
        materiaal_id = self._geselecteerd_materiaal_id()
        if materiaal_id is None:
            return
        try:
            self.bibliotheek.verwijderen_definitief(materiaal_id)
        except OngeldigeStatusOvergangError as exc:
            QMessageBox.warning(self, "Kan niet verwijderen", str(exc))
            return
        self.huidig_id = None
        self._ververs_tabel()

    def _voer_statusactie_uit(self, actie) -> None:
        materiaal_id = self._geselecteerd_materiaal_id()
        if materiaal_id is None:
            return
        try:
            actie(materiaal_id)
        except OngeldigeStatusOvergangError as exc:
            QMessageBox.warning(self, "Actie niet mogelijk", str(exc))
            return
        self._ververs_tabel()


def main() -> None:
    app = QApplication(sys.argv)
    venster = MaterialenTestVenster()
    venster.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
