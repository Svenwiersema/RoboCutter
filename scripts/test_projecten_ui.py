"""Ruwe test-ui voor de projectenbibliotheek-functie (Module 1/4).

Dit is GEEN voorbeeld van het uiteindelijke Projecten-scherm (dat komt
later via de mockup-workflow: eerst een HTML-concept, dan pas PySide6).
Dit script bestaat alleen om ``robocutter.projecten`` functioneel te
kunnen uittesten: een project met klantgegevens aanmaken, een model als
vaste kopie toevoegen (met aantal), een los onderdeel toevoegen, en de
gecombineerde zaaglijst op meerdere criteria tegelijk sorteren (bv.
eerst materiaal, dan breedte) — zonder styling of polish.

Deelt de materialen- en modellen-testbestanden met de andere test-ui's
(``data/materialen_test.db``, ``data/modellen_test.db``) en heeft
daarnaast een eigen ``data/projecten_test.db``.

Draaien: python scripts/test_projecten_ui.py
(vereist: pip install -e ".[ui]")
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

_MATERIALEN_DB_PAD = _REPO_ROOT / "data" / "materialen_test.db"
_MODELLEN_DB_PAD = _REPO_ROOT / "data" / "modellen_test.db"
_PROJECTEN_DB_PAD = _REPO_ROOT / "data" / "projecten_test.db"

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
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.materialen.models import Materiaal, MateriaalType
from robocutter.materialen.opslag import open_verbinding as open_materialen_verbinding
from robocutter.modellen.bibliotheek import ModellenBibliotheek
from robocutter.modellen.models import Model, ModelOnderdeel
from robocutter.modellen.opslag import open_verbinding as open_modellen_verbinding
from robocutter.projecten.bibliotheek import OngeldigeStatusOvergangError, ProjectenBibliotheek, valideer
from robocutter.projecten.models import Project, ProjectStatus
from robocutter.projecten.opslag import open_verbinding as open_projecten_verbinding
from robocutter.projecten.zaaglijst import SORTEERSLEUTELS, bouw_zaaglijst, sorteer_zaaglijst

KOLOMMEN = ["Naam", "Klant", "Status", "Gearchiveerd", "Modellen", "Losse onderdelen"]
ZAAGLIJST_KOLOMMEN = ["Onderdeel", "Materiaal", "Breedte", "Hoogte", "Aantal", "Herkomst"]
_GEEN_SLEUTEL = "(geen)"


def _voorbeeld_materialen(bib: MaterialenBibliotheek) -> None:
    """Alleen zaaien als de bibliotheek nog leeg is — zelfde
    voorbeelddata als de andere test-ui's."""
    if bib.lijst():
        return
    bib.toevoegen(
        Materiaal(
            id="", naam="Eiken multiplex 18mm", type=MateriaalType.PLAAT,
            lengte=2800, breedte=2070, derde_afmeting=18, familie="Eiken multiplex",
            productcode="EMP-18", tags=("multiplex", "eiken"),
        )
    )
    bib.toevoegen(
        Materiaal(
            id="", naam="Wit MDF 18mm", type=MateriaalType.PLAAT,
            lengte=2800, breedte=2070, derde_afmeting=18, familie="MDF",
        )
    )


class ProjectenTestVenster(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RoboCutter — projectenbibliotheek (test-ui)")
        self.resize(1280, 700)

        _MATERIALEN_DB_PAD.parent.mkdir(parents=True, exist_ok=True)
        self.materialen_verbinding = open_materialen_verbinding(_MATERIALEN_DB_PAD)
        self.materialen = MaterialenBibliotheek(self.materialen_verbinding)
        _voorbeeld_materialen(self.materialen)

        self.modellen_verbinding = open_modellen_verbinding(_MODELLEN_DB_PAD)
        self.modellen = ModellenBibliotheek(self.materialen, self.modellen_verbinding)

        self.projecten_verbinding = open_projecten_verbinding(_PROJECTEN_DB_PAD)
        self.bibliotheek = ProjectenBibliotheek(self.modellen, self.materialen, self.projecten_verbinding)
        self.huidig_id: str | None = None

        centraal = QWidget()
        self.setCentralWidget(centraal)
        layout = QHBoxLayout(centraal)
        layout.addLayout(self._bouw_lijst_kolom(), stretch=3)
        layout.addWidget(self._bouw_formulier_groep(), stretch=3)
        layout.addWidget(self._bouw_zaaglijst_groep(), stretch=3)

        self._ververs_tabel()

    # -- linkerkolom: projectenlijst --------------------------------------
    def _bouw_lijst_kolom(self) -> QVBoxLayout:
        kolom = QVBoxLayout()

        self.zoekveld = QLineEdit()
        self.zoekveld.setPlaceholderText("Zoeken op naam, klant, contactpersoon of opdrachtnummer…")
        self.zoekveld.textChanged.connect(self._ververs_tabel)
        kolom.addWidget(self.zoekveld)

        self.tabel = QTableWidget(0, len(KOLOMMEN))
        self.tabel.setHorizontalHeaderLabels(KOLOMMEN)
        self.tabel.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabel.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabel.itemSelectionChanged.connect(self._selectie_gewijzigd)
        kolom.addWidget(self.tabel)

        acties = QHBoxLayout()
        self.knop_nieuw = QPushButton("Nieuw project")
        self.knop_nieuw.clicked.connect(self._nieuw_project)
        acties.addWidget(self.knop_nieuw)
        self.knop_archiveren = QPushButton("Archiveren")
        self.knop_archiveren.clicked.connect(self._archiveren)
        acties.addWidget(self.knop_archiveren)
        self.knop_heractiveren = QPushButton("Heractiveren")
        self.knop_heractiveren.clicked.connect(self._heractiveren)
        acties.addWidget(self.knop_heractiveren)
        self.knop_verwijderen = QPushButton("Definitief verwijderen")
        self.knop_verwijderen.clicked.connect(self._verwijderen_definitief)
        acties.addWidget(self.knop_verwijderen)
        kolom.addLayout(acties)
        return kolom

    # -- middenkolom: formulier --------------------------------------------
    def _bouw_formulier_groep(self) -> QGroupBox:
        groep = QGroupBox("Project-gegevens")
        buiten = QVBoxLayout(groep)

        form = QFormLayout()
        self.veld_naam = QLineEdit()
        form.addRow("Naam", self.veld_naam)
        self.veld_klant = QLineEdit()
        form.addRow("Klant", self.veld_klant)
        self.veld_contactpersoon = QLineEdit()
        form.addRow("Contactpersoon", self.veld_contactpersoon)
        self.veld_email = QLineEdit()
        form.addRow("E-mail", self.veld_email)
        self.veld_telefoon = QLineEdit()
        form.addRow("Telefoon", self.veld_telefoon)
        self.veld_opdrachtnummer = QLineEdit()
        form.addRow("Opdrachtnummer", self.veld_opdrachtnummer)
        self.veld_startdatum = QLineEdit()
        self.veld_startdatum.setPlaceholderText("jjjj-mm-dd")
        form.addRow("Startdatum", self.veld_startdatum)
        self.veld_opleverdatum = QLineEdit()
        self.veld_opleverdatum.setPlaceholderText("jjjj-mm-dd")
        form.addRow("Opleverdatum", self.veld_opleverdatum)
        self.veld_status = QComboBox()
        for status in ProjectStatus:
            # Qt's dynamic-property/QVariant-opslag zet een str-Enum
            # (ProjectStatus is een str-subklasse) terug om naar een kale
            # str zodra 'm via userData/currentData rondgaat — zelfde val
            # als eerder bij MateriaalType/Nerfrichting (zie
            # materialen_page.py::_segmented). Daarom hier bewust
            # ``.value`` opslaan en bij het uitlezen terugzetten naar het
            # enum-lid via ``ProjectStatus(...)``.
            self.veld_status.addItem(status.value, status.value)
        form.addRow("Status", self.veld_status)
        buiten.addLayout(form)

        self.label_fouten = QLabel("")
        self.label_fouten.setStyleSheet("color: #c0392b;")
        self.label_fouten.setWordWrap(True)
        buiten.addWidget(self.label_fouten)

        self.knop_opslaan = QPushButton("Opslaan")
        self.knop_opslaan.clicked.connect(self._opslaan)
        buiten.addWidget(self.knop_opslaan)

        buiten.addWidget(QLabel("Modellen (vaste kopie)"))
        self.lijst_modelinstanties = QListWidget()
        buiten.addWidget(self.lijst_modelinstanties)
        model_rij = QHBoxLayout()
        self.veld_model = QComboBox()
        model_rij.addWidget(self.veld_model, 1)
        self.veld_model_aantal = QSpinBox()
        self.veld_model_aantal.setRange(1, 1000)
        model_rij.addWidget(self.veld_model_aantal)
        knop_model_toevoegen = QPushButton("+ Toevoegen")
        knop_model_toevoegen.clicked.connect(self._model_toevoegen)
        model_rij.addWidget(knop_model_toevoegen)
        buiten.addLayout(model_rij)
        model_acties = QHBoxLayout()
        knop_model_bijwerken = QPushButton("Bijwerken naar laatste versie")
        knop_model_bijwerken.clicked.connect(self._model_bijwerken)
        model_acties.addWidget(knop_model_bijwerken)
        knop_model_verwijderen = QPushButton("Verwijderen")
        knop_model_verwijderen.clicked.connect(self._model_instantie_verwijderen)
        model_acties.addWidget(knop_model_verwijderen)
        buiten.addLayout(model_acties)

        buiten.addWidget(QLabel("Losse onderdelen"))
        self.lijst_losse_onderdelen = QListWidget()
        buiten.addWidget(self.lijst_losse_onderdelen)
        onderdeel_rij = QHBoxLayout()
        self.veld_onderdeel_naam = QLineEdit()
        self.veld_onderdeel_naam.setPlaceholderText("Naam onderdeel")
        onderdeel_rij.addWidget(self.veld_onderdeel_naam)
        self.veld_onderdeel_materiaal = QComboBox()
        onderdeel_rij.addWidget(self.veld_onderdeel_materiaal)
        self.veld_onderdeel_breedte = self._maak_afmeting_veld()
        onderdeel_rij.addWidget(self.veld_onderdeel_breedte)
        self.veld_onderdeel_hoogte = self._maak_afmeting_veld()
        onderdeel_rij.addWidget(self.veld_onderdeel_hoogte)
        knop_onderdeel_toevoegen = QPushButton("+ Toevoegen")
        knop_onderdeel_toevoegen.clicked.connect(self._los_onderdeel_toevoegen)
        onderdeel_rij.addWidget(knop_onderdeel_toevoegen)
        buiten.addLayout(onderdeel_rij)
        knop_onderdeel_verwijderen = QPushButton("Geselecteerd onderdeel verwijderen")
        knop_onderdeel_verwijderen.clicked.connect(self._los_onderdeel_verwijderen)
        buiten.addWidget(knop_onderdeel_verwijderen)

        self._ververs_model_combo()
        self._ververs_materiaal_combo()
        return groep

    @staticmethod
    def _maak_afmeting_veld() -> QDoubleSpinBox:
        veld = QDoubleSpinBox()
        veld.setRange(0.01, 100000.0)
        veld.setDecimals(1)
        return veld

    def _ververs_model_combo(self) -> None:
        self.veld_model.clear()
        for model in self.modellen.lijst():
            self.veld_model.addItem(model.naam, model.id)

    def _ververs_materiaal_combo(self) -> None:
        self.veld_onderdeel_materiaal.clear()
        for materiaal in self.materialen.lijst():
            self.veld_onderdeel_materiaal.addItem(f"{materiaal.naam} ({materiaal.type.value})", materiaal.id)

    # -- rechterkolom: zaaglijst --------------------------------------------
    def _bouw_zaaglijst_groep(self) -> QGroupBox:
        groep = QGroupBox("Zaaglijst")
        buiten = QVBoxLayout(groep)

        sorteer_rij = QHBoxLayout()
        sorteer_rij.addWidget(QLabel("Sorteer op:"))
        self.veld_sorteer_1 = QComboBox()
        for sleutel in SORTEERSLEUTELS:
            self.veld_sorteer_1.addItem(sleutel, sleutel)
        self.veld_sorteer_1.setCurrentText("materiaal")
        sorteer_rij.addWidget(self.veld_sorteer_1)
        sorteer_rij.addWidget(QLabel("dan:"))
        self.veld_sorteer_2 = QComboBox()
        self.veld_sorteer_2.addItem(_GEEN_SLEUTEL, None)
        for sleutel in SORTEERSLEUTELS:
            self.veld_sorteer_2.addItem(sleutel, sleutel)
        self.veld_sorteer_2.setCurrentText("breedte")
        sorteer_rij.addWidget(self.veld_sorteer_2)
        knop_vernieuwen = QPushButton("Vernieuwen")
        knop_vernieuwen.clicked.connect(self._ververs_zaaglijst)
        sorteer_rij.addWidget(knop_vernieuwen)
        buiten.addLayout(sorteer_rij)

        self.zaaglijst_tabel = QTableWidget(0, len(ZAAGLIJST_KOLOMMEN))
        self.zaaglijst_tabel.setHorizontalHeaderLabels(ZAAGLIJST_KOLOMMEN)
        self.zaaglijst_tabel.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        buiten.addWidget(self.zaaglijst_tabel)

        return groep

    def _ververs_zaaglijst(self) -> None:
        self.zaaglijst_tabel.setRowCount(0)
        if self.huidig_id is None:
            return
        project = self.bibliotheek.ophalen(self.huidig_id)
        sleutels = [self.veld_sorteer_1.currentData()]
        if self.veld_sorteer_2.currentData():
            sleutels.append(self.veld_sorteer_2.currentData())
        regels = sorteer_zaaglijst(bouw_zaaglijst(project), sleutels, self.materialen)

        self.zaaglijst_tabel.setRowCount(len(regels))
        for rij, regel in enumerate(regels):
            try:
                materiaal_naam = self.materialen.ophalen(regel.onderdeel.materiaal_id).naam
            except KeyError:
                materiaal_naam = "onbekend materiaal"
            waarden = [
                regel.onderdeel.naam,
                materiaal_naam,
                f"{regel.onderdeel.breedte:g}",
                f"{regel.onderdeel.hoogte:g}",
                str(regel.onderdeel.aantal),
                regel.herkomst,
            ]
            for kolom, waarde in enumerate(waarden):
                self.zaaglijst_tabel.setItem(rij, kolom, QTableWidgetItem(waarde))

    # -- tabel vullen / selectie ---------------------------------------------
    def _ververs_tabel(self) -> None:
        projecten = self.bibliotheek.lijst(zoekterm=self.zoekveld.text())
        self.tabel.setRowCount(len(projecten))
        for rij, project in enumerate(projecten):
            waarden = [
                project.naam,
                project.klant,
                project.status.value,
                "ja" if project.gearchiveerd else "nee",
                str(len(project.modelinstanties)),
                str(len(project.losse_onderdelen)),
            ]
            for kolom, waarde in enumerate(waarden):
                item = QTableWidgetItem(waarde)
                item.setData(Qt.ItemDataRole.UserRole, project.id)
                self.tabel.setItem(rij, kolom, item)
        self.tabel.resizeColumnsToContents()

    def _geselecteerd_project_id(self) -> str | None:
        rijen = self.tabel.selectionModel().selectedRows()
        if not rijen:
            return None
        item = self.tabel.item(rijen[0].row(), 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _selectie_gewijzigd(self) -> None:
        project_id = self._geselecteerd_project_id()
        if project_id is None:
            return
        self._toon_in_formulier(self.bibliotheek.ophalen(project_id))

    def _toon_in_formulier(self, project: Project) -> None:
        self.huidig_id = project.id
        self.veld_naam.setText(project.naam)
        self.veld_klant.setText(project.klant)
        self.veld_contactpersoon.setText(project.contactpersoon)
        self.veld_email.setText(project.email)
        self.veld_telefoon.setText(project.telefoon)
        self.veld_opdrachtnummer.setText(project.opdrachtnummer)
        self.veld_startdatum.setText(project.startdatum.isoformat() if project.startdatum else "")
        self.veld_opleverdatum.setText(project.opleverdatum.isoformat() if project.opleverdatum else "")
        index = self.veld_status.findData(project.status.value)
        if index >= 0:
            self.veld_status.setCurrentIndex(index)
        self.label_fouten.setText("")
        self._ververs_model_combo()
        self._ververs_materiaal_combo()
        self._ververs_modelinstanties_lijst()
        self._ververs_losse_onderdelen_lijst()
        self._ververs_zaaglijst()

    def _ververs_modelinstanties_lijst(self) -> None:
        self.lijst_modelinstanties.clear()
        if self.huidig_id is None:
            return
        project = self.bibliotheek.ophalen(self.huidig_id)
        for instantie in project.modelinstanties:
            tekst = f"{instantie.model_naam} × {instantie.aantal} ({len(instantie.onderdelen)} onderdelen)"
            item = QListWidgetItem(tekst)
            item.setData(Qt.ItemDataRole.UserRole, instantie.id)
            self.lijst_modelinstanties.addItem(item)

    def _ververs_losse_onderdelen_lijst(self) -> None:
        self.lijst_losse_onderdelen.clear()
        if self.huidig_id is None:
            return
        project = self.bibliotheek.ophalen(self.huidig_id)
        for index, onderdeel in enumerate(project.losse_onderdelen):
            try:
                materiaal_naam = self.materialen.ophalen(onderdeel.materiaal_id).naam
            except KeyError:
                materiaal_naam = "onbekend materiaal"
            tekst = f"{onderdeel.naam} — {onderdeel.breedte:g}×{onderdeel.hoogte:g}mm — {materiaal_naam}"
            item = QListWidgetItem(tekst)
            item.setData(Qt.ItemDataRole.UserRole, index)
            self.lijst_losse_onderdelen.addItem(item)

    def _nieuw_project(self) -> None:
        self.huidig_id = None
        self.tabel.clearSelection()
        self.veld_naam.clear()
        self.veld_klant.clear()
        self.veld_contactpersoon.clear()
        self.veld_email.clear()
        self.veld_telefoon.clear()
        self.veld_opdrachtnummer.clear()
        self.veld_startdatum.clear()
        self.veld_opleverdatum.clear()
        self.veld_status.setCurrentIndex(0)
        self.label_fouten.setText("")
        self.lijst_modelinstanties.clear()
        self.lijst_losse_onderdelen.clear()
        self.zaaglijst_tabel.setRowCount(0)

    def _parse_datum(self, tekst: str):
        tekst = tekst.strip()
        if not tekst:
            return None
        try:
            return date.fromisoformat(tekst)
        except ValueError:
            return None

    def _project_uit_formulier(self) -> Project:
        bestaand = self.bibliotheek.ophalen(self.huidig_id) if self.huidig_id else None
        return Project(
            id=self.huidig_id or "",
            naam=self.veld_naam.text(),
            klant=self.veld_klant.text(),
            contactpersoon=self.veld_contactpersoon.text().strip(),
            email=self.veld_email.text().strip(),
            telefoon=self.veld_telefoon.text().strip(),
            opdrachtnummer=self.veld_opdrachtnummer.text().strip(),
            startdatum=self._parse_datum(self.veld_startdatum.text()),
            opleverdatum=self._parse_datum(self.veld_opleverdatum.text()),
            status=ProjectStatus(self.veld_status.currentData()),
            gearchiveerd=bestaand.gearchiveerd if bestaand else False,
            modelinstanties=bestaand.modelinstanties if bestaand else [],
            losse_onderdelen=bestaand.losse_onderdelen if bestaand else [],
        )

    def _opslaan(self) -> None:
        project = self._project_uit_formulier()
        fouten = valideer(project, self.materialen)
        if fouten:
            self.label_fouten.setText("\n".join(fouten))
            return
        self.label_fouten.setText("")

        if self.huidig_id is None:
            project = self.bibliotheek.toevoegen(project)
            self.huidig_id = project.id
        else:
            self.bibliotheek.bijwerken(project)

        self._ververs_tabel()
        self._toon_in_formulier(self.bibliotheek.ophalen(self.huidig_id))

    def _model_toevoegen(self) -> None:
        if self.huidig_id is None:
            QMessageBox.information(self, "Eerst opslaan", "Sla het project eerst op voordat je modellen toevoegt.")
            return
        model_id = self.veld_model.currentData()
        if not model_id:
            return
        self.bibliotheek.model_toevoegen(self.huidig_id, model_id, self.veld_model_aantal.value())
        self._ververs_modelinstanties_lijst()
        self._ververs_zaaglijst()
        self._ververs_tabel()

    def _geselecteerde_instantie_id(self) -> str | None:
        item = self.lijst_modelinstanties.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _model_bijwerken(self) -> None:
        instantie_id = self._geselecteerde_instantie_id()
        if self.huidig_id is None or instantie_id is None:
            return
        self.bibliotheek.model_bijwerken_naar_laatste_versie(self.huidig_id, instantie_id)
        self._ververs_modelinstanties_lijst()
        self._ververs_zaaglijst()

    def _model_instantie_verwijderen(self) -> None:
        instantie_id = self._geselecteerde_instantie_id()
        if self.huidig_id is None or instantie_id is None:
            return
        self.bibliotheek.model_instantie_verwijderen(self.huidig_id, instantie_id)
        self._ververs_modelinstanties_lijst()
        self._ververs_zaaglijst()
        self._ververs_tabel()

    def _los_onderdeel_toevoegen(self) -> None:
        if self.huidig_id is None:
            QMessageBox.information(self, "Eerst opslaan", "Sla het project eerst op voordat je onderdelen toevoegt.")
            return
        project = self.bibliotheek.ophalen(self.huidig_id)
        project.losse_onderdelen.append(
            ModelOnderdeel(
                id="",
                naam=self.veld_onderdeel_naam.text().strip() or "Onderdeel",
                materiaal_id=self.veld_onderdeel_materiaal.currentData(),
                breedte=self.veld_onderdeel_breedte.value(),
                hoogte=self.veld_onderdeel_hoogte.value(),
            )
        )
        fouten = valideer(project, self.materialen)
        if fouten:
            self.label_fouten.setText("\n".join(fouten))
            return
        self.bibliotheek.bijwerken(project)
        self.veld_onderdeel_naam.clear()
        self._ververs_losse_onderdelen_lijst()
        self._ververs_zaaglijst()
        self._ververs_tabel()

    def _los_onderdeel_verwijderen(self) -> None:
        item = self.lijst_losse_onderdelen.currentItem()
        if self.huidig_id is None or item is None:
            return
        index = item.data(Qt.ItemDataRole.UserRole)
        project = self.bibliotheek.ophalen(self.huidig_id)
        del project.losse_onderdelen[index]
        self.bibliotheek.bijwerken(project)
        self._ververs_losse_onderdelen_lijst()
        self._ververs_zaaglijst()
        self._ververs_tabel()

    def _archiveren(self) -> None:
        self._voer_statusactie_uit(self.bibliotheek.archiveren)

    def _heractiveren(self) -> None:
        self._voer_statusactie_uit(self.bibliotheek.heractiveren)

    def _verwijderen_definitief(self) -> None:
        project_id = self._geselecteerd_project_id()
        if project_id is None:
            return
        try:
            self.bibliotheek.verwijderen_definitief(project_id)
        except OngeldigeStatusOvergangError as exc:
            QMessageBox.warning(self, "Actie niet mogelijk", str(exc))
            return
        self.huidig_id = None
        self._ververs_tabel()

    def _voer_statusactie_uit(self, actie) -> None:
        project_id = self._geselecteerd_project_id()
        if project_id is None:
            return
        try:
            actie(project_id)
        except OngeldigeStatusOvergangError as exc:
            QMessageBox.warning(self, "Actie niet mogelijk", str(exc))
            return
        self._ververs_tabel()
        if self.huidig_id == project_id:
            self._toon_in_formulier(self.bibliotheek.ophalen(project_id))


def main() -> None:
    app = QApplication(sys.argv)
    venster = ProjectenTestVenster()
    venster.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
