"""Ruwe test-ui voor de modellenbibliotheek-functie (Module 2).

Dit is GEEN voorbeeld van het uiteindelijke Modellenbibliotheek-scherm
(dat komt later via de mockup-workflow: eerst een HTML-concept, dan pas
PySide6). Dit script bestaat alleen om ``robocutter.modellen``
functioneel te kunnen uittesten: modellen aanmaken/bewerken, onderdelen
met een materiaalkeuze toevoegen, submodellen koppelen (nesting), en de
foutmeldingen bij een cirkelverwijzing of onbekend materiaal proberen
uit te lokken — zonder styling of polish.

Een model-onderdeel hoort bij een bestaand materiaal (zie
``robocutter.materialen``), dus dit script deelt hetzelfde
materialen-testbestand als ``test_materialen_ui.py``/
``test_reststukken_ui.py`` (``data/materialen_test.db``) en heeft
daarnaast een eigen ``data/modellen_test.db``.

Draaien: python scripts/test_modellen_ui.py
(vereist: pip install -e ".[ui]")
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

_MATERIALEN_DB_PAD = _REPO_ROOT / "data" / "materialen_test.db"
_MODELLEN_DB_PAD = _REPO_ROOT / "data" / "modellen_test.db"

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
from robocutter.modellen.bibliotheek import ModelInGebruikError, ModellenBibliotheek, valideer
from robocutter.modellen.models import Model, ModelOnderdeel, Nerfrichting, Rand, SubModelVerwijzing
from robocutter.modellen.opslag import open_verbinding as open_modellen_verbinding

_NERFRICHTING_LABELS = {
    Nerfrichting.GEEN: "Geen eis",
    Nerfrichting.LANGE_ZIJDE: "Lange zijde langs de nerf",
    Nerfrichting.KORTE_ZIJDE: "Korte zijde langs de nerf",
}
_RAND_LABELS = {
    Rand.BOVEN: "Boven",
    Rand.ONDER: "Onder",
    Rand.LINKS: "Links",
    Rand.RECHTS: "Rechts",
}

KOLOMMEN = ["Naam", "Map", "Onderdelen", "Submodellen", "Tags"]


def _voorbeeld_materialen(bib: MaterialenBibliotheek) -> None:
    """Alleen zaaien als de bibliotheek nog leeg is — zelfde
    voorbeelddata als test_materialen_ui.py/test_reststukken_ui.py."""
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
            naam="Wit MDF 18mm",
            type=MateriaalType.PLAAT,
            lengte=2800,
            breedte=2070,
            derde_afmeting=18,
            familie="MDF",
            kleur_afwerking="Wit gelakt",
            kerf=3,
        )
    )


class ModellenTestVenster(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RoboCutter — modellenbibliotheek (test-ui)")
        self.resize(1200, 640)

        _MATERIALEN_DB_PAD.parent.mkdir(parents=True, exist_ok=True)
        self.materialen_verbinding = open_materialen_verbinding(_MATERIALEN_DB_PAD)
        self.materialen = MaterialenBibliotheek(self.materialen_verbinding)
        _voorbeeld_materialen(self.materialen)

        self.modellen_verbinding = open_modellen_verbinding(_MODELLEN_DB_PAD)
        self.bibliotheek = ModellenBibliotheek(self.materialen, self.modellen_verbinding)
        self.huidig_id: str | None = None
        self.huidige_onderdelen: list[ModelOnderdeel] = []
        self.huidige_submodellen: list[SubModelVerwijzing] = []

        centraal = QWidget()
        self.setCentralWidget(centraal)
        layout = QHBoxLayout(centraal)

        layout.addLayout(self._bouw_lijst_kolom(), stretch=3)
        layout.addWidget(self._bouw_formulier_groep(), stretch=2)

        self._ververs_tabel()

    # -- linkerkolom: zoeken + tabel -------------------------------------
    def _bouw_lijst_kolom(self) -> QVBoxLayout:
        kolom = QVBoxLayout()

        self.zoekveld = QLineEdit()
        self.zoekveld.setPlaceholderText("Zoeken op naam, omschrijving, map of tag…")
        self.zoekveld.textChanged.connect(self._ververs_tabel)
        kolom.addWidget(self.zoekveld)

        self.tabel = QTableWidget(0, len(KOLOMMEN))
        self.tabel.setHorizontalHeaderLabels(KOLOMMEN)
        self.tabel.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabel.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabel.itemSelectionChanged.connect(self._selectie_gewijzigd)
        kolom.addWidget(self.tabel)

        acties = QHBoxLayout()
        self.knop_nieuw = QPushButton("Nieuw model")
        self.knop_nieuw.clicked.connect(self._nieuw_model)
        acties.addWidget(self.knop_nieuw)

        self.knop_verwijderen = QPushButton("Verwijderen")
        self.knop_verwijderen.clicked.connect(self._verwijderen)
        acties.addWidget(self.knop_verwijderen)

        kolom.addLayout(acties)
        return kolom

    # -- rechterkolom: formulier ------------------------------------------
    def _bouw_formulier_groep(self) -> QGroupBox:
        groep = QGroupBox("Model-gegevens")
        buiten = QVBoxLayout(groep)

        form = QFormLayout()
        self.veld_naam = QLineEdit()
        form.addRow("Naam", self.veld_naam)
        self.veld_omschrijving = QLineEdit()
        form.addRow("Omschrijving", self.veld_omschrijving)
        self.veld_map = QLineEdit()
        self.veld_map.setPlaceholderText("bijv. Keukens/Onderkasten")
        form.addRow("Map", self.veld_map)
        self.veld_tags = QLineEdit()
        self.veld_tags.setPlaceholderText("kommagescheiden, bijv. keuken, eiken")
        form.addRow("Tags", self.veld_tags)
        buiten.addLayout(form)

        buiten.addWidget(QLabel("Onderdelen"))
        self.lijst_onderdelen = QListWidget()
        buiten.addWidget(self.lijst_onderdelen)

        onderdeel_form = QHBoxLayout()
        self.veld_onderdeel_naam = QLineEdit()
        self.veld_onderdeel_naam.setPlaceholderText("Naam onderdeel")
        onderdeel_form.addWidget(self.veld_onderdeel_naam)
        self.veld_onderdeel_materiaal = QComboBox()
        onderdeel_form.addWidget(self.veld_onderdeel_materiaal)
        self.veld_onderdeel_breedte = self._maak_afmeting_veld()
        onderdeel_form.addWidget(self.veld_onderdeel_breedte)
        self.veld_onderdeel_hoogte = self._maak_afmeting_veld()
        onderdeel_form.addWidget(self.veld_onderdeel_hoogte)
        self.veld_onderdeel_aantal = QSpinBox()
        self.veld_onderdeel_aantal.setRange(1, 1000)
        onderdeel_form.addWidget(self.veld_onderdeel_aantal)
        buiten.addLayout(onderdeel_form)

        onderdeel_form_2 = QHBoxLayout()
        onderdeel_form_2.addWidget(QLabel("Nerfrichting:"))
        self.veld_onderdeel_nerfrichting = QComboBox()
        for waarde, label in _NERFRICHTING_LABELS.items():
            self.veld_onderdeel_nerfrichting.addItem(label, waarde)
        onderdeel_form_2.addWidget(self.veld_onderdeel_nerfrichting)

        onderdeel_form_2.addWidget(QLabel("Kantenband:"))
        self.veld_onderdeel_kantenband: dict[Rand, QCheckBox] = {}
        for rand, label in _RAND_LABELS.items():
            vinkje = QCheckBox(label)
            self.veld_onderdeel_kantenband[rand] = vinkje
            onderdeel_form_2.addWidget(vinkje)

        self.veld_onderdeel_fabriekskantenband = QCheckBox("Fabriekskantenband vereist")
        onderdeel_form_2.addWidget(self.veld_onderdeel_fabriekskantenband)
        buiten.addLayout(onderdeel_form_2)

        onderdeel_form_3 = QHBoxLayout()
        onderdeel_form_3.addWidget(QLabel("Groep (vaste volgorde/nerf, leeg = geen groep):"))
        self.veld_onderdeel_groep_id = QLineEdit()
        self.veld_onderdeel_groep_id.setPlaceholderText("bijv. lades-onderkast")
        onderdeel_form_3.addWidget(self.veld_onderdeel_groep_id)
        onderdeel_form_3.addWidget(QLabel("Volgorde in groep:"))
        self.veld_onderdeel_groep_volgorde = QSpinBox()
        self.veld_onderdeel_groep_volgorde.setRange(0, 1000)
        onderdeel_form_3.addWidget(self.veld_onderdeel_groep_volgorde)
        buiten.addLayout(onderdeel_form_3)

        knop_onderdeel_toevoegen = QPushButton("+ Onderdeel")
        knop_onderdeel_toevoegen.clicked.connect(self._onderdeel_toevoegen)
        buiten.addWidget(knop_onderdeel_toevoegen)

        buiten.addWidget(QLabel("Submodellen (nesting)"))
        self.lijst_submodellen = QListWidget()
        buiten.addWidget(self.lijst_submodellen)

        submodel_form = QHBoxLayout()
        self.veld_submodel = QComboBox()
        submodel_form.addWidget(self.veld_submodel)
        self.veld_submodel_aantal = QSpinBox()
        self.veld_submodel_aantal.setRange(1, 1000)
        submodel_form.addWidget(self.veld_submodel_aantal)
        knop_submodel_toevoegen = QPushButton("+ Submodel")
        knop_submodel_toevoegen.clicked.connect(self._submodel_toevoegen)
        submodel_form.addWidget(knop_submodel_toevoegen)
        buiten.addLayout(submodel_form)

        self.label_fouten = QLabel("")
        self.label_fouten.setStyleSheet("color: #c0392b;")
        self.label_fouten.setWordWrap(True)
        buiten.addWidget(self.label_fouten)

        self.knop_opslaan = QPushButton("Opslaan")
        self.knop_opslaan.clicked.connect(self._opslaan)
        buiten.addWidget(self.knop_opslaan)

        self._ververs_materiaal_combo()
        self._ververs_submodel_combo()
        return groep

    @staticmethod
    def _maak_afmeting_veld() -> QDoubleSpinBox:
        veld = QDoubleSpinBox()
        veld.setRange(0.01, 100000.0)
        veld.setDecimals(1)
        return veld

    def _ververs_materiaal_combo(self) -> None:
        self.veld_onderdeel_materiaal.clear()
        for materiaal in self.materialen.lijst():
            self.veld_onderdeel_materiaal.addItem(f"{materiaal.naam} ({materiaal.type.value})", materiaal.id)

    def _ververs_submodel_combo(self) -> None:
        self.veld_submodel.clear()
        for model in self.bibliotheek.lijst():
            if model.id == self.huidig_id:
                continue  # een model kan zichzelf niet als submodel kiezen
            self.veld_submodel.addItem(model.naam, model.id)

    # -- tabel vullen / selectie -------------------------------------------
    def _ververs_tabel(self) -> None:
        modellen = self.bibliotheek.lijst(zoekterm=self.zoekveld.text())

        self.tabel.clearContents()
        self.tabel.setRowCount(len(modellen))
        for rij, model in enumerate(modellen):
            waarden = [
                model.naam,
                model.map or "—",
                str(len(model.onderdelen)),
                str(len(model.submodellen)),
                ", ".join(model.tags) or "—",
            ]
            for kolom, waarde in enumerate(waarden):
                item = QTableWidgetItem(waarde)
                item.setData(Qt.ItemDataRole.UserRole, model.id)
                self.tabel.setItem(rij, kolom, item)
        self.tabel.resizeColumnsToContents()

    def _geselecteerd_model_id(self) -> str | None:
        rijen = self.tabel.selectionModel().selectedRows()
        if not rijen:
            return None
        item = self.tabel.item(rijen[0].row(), 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _selectie_gewijzigd(self) -> None:
        model_id = self._geselecteerd_model_id()
        if model_id is None:
            return
        self._toon_in_formulier(self.bibliotheek.ophalen(model_id))

    def _toon_in_formulier(self, model: Model) -> None:
        self.huidig_id = model.id
        self.huidige_onderdelen = list(model.onderdelen)
        self.huidige_submodellen = list(model.submodellen)
        self.veld_naam.setText(model.naam)
        self.veld_omschrijving.setText(model.omschrijving)
        self.veld_map.setText(model.map)
        self.veld_tags.setText(", ".join(model.tags))
        self._ververs_submodel_combo()
        self._ververs_onderdelen_lijst()
        self._ververs_submodellen_lijst()
        self.label_fouten.setText("")

    def _nieuw_model(self) -> None:
        self.huidig_id = None
        self.huidige_onderdelen = []
        self.huidige_submodellen = []
        self.tabel.clearSelection()
        self.veld_naam.clear()
        self.veld_omschrijving.clear()
        self.veld_map.clear()
        self.veld_tags.clear()
        self._ververs_submodel_combo()
        self._ververs_onderdelen_lijst()
        self._ververs_submodellen_lijst()
        self.label_fouten.setText("")

    def _ververs_onderdelen_lijst(self) -> None:
        self.lijst_onderdelen.clear()
        for onderdeel in self.huidige_onderdelen:
            try:
                materiaal_naam = self.bibliotheek.materiaal_van(onderdeel).naam
            except Exception:
                materiaal_naam = f"onbekend materiaal ({onderdeel.materiaal_id})"
            randen = "+".join(_RAND_LABELS[r] for r in sorted(onderdeel.kantenband_randen, key=lambda r: r.value)) or "geen"
            groep = f" — groep: {onderdeel.groep_id} (#{onderdeel.groep_volgorde})" if onderdeel.groep_id else ""
            tekst = (
                f"{onderdeel.naam} — {onderdeel.breedte:g}x{onderdeel.hoogte:g}mm x{onderdeel.aantal} — "
                f"{materiaal_naam} — nerf: {_NERFRICHTING_LABELS[onderdeel.nerfrichting_vereist]} — "
                f"kantenband: {randen}"
                + (" — fabriekskantenband" if onderdeel.fabriekskantenband_vereist else "")
                + groep
            )
            self.lijst_onderdelen.addItem(QListWidgetItem(tekst))

    def _ververs_submodellen_lijst(self) -> None:
        self.lijst_submodellen.clear()
        for submodel in self.huidige_submodellen:
            try:
                naam = self.bibliotheek.ophalen(submodel.model_id).naam
            except KeyError:
                naam = f"onbekend model ({submodel.model_id})"
            self.lijst_submodellen.addItem(QListWidgetItem(f"{naam} x{submodel.aantal}"))

    def _onderdeel_toevoegen(self) -> None:
        naam = self.veld_onderdeel_naam.text().strip() or "Onderdeel"
        gekozen_randen = frozenset(
            rand for rand, vinkje in self.veld_onderdeel_kantenband.items() if vinkje.isChecked()
        )
        groep_id = self.veld_onderdeel_groep_id.text().strip() or None
        self.huidige_onderdelen.append(
            ModelOnderdeel(
                id="",
                naam=naam,
                materiaal_id=self.veld_onderdeel_materiaal.currentData(),
                breedte=self.veld_onderdeel_breedte.value(),
                hoogte=self.veld_onderdeel_hoogte.value(),
                aantal=self.veld_onderdeel_aantal.value(),
                nerfrichting_vereist=self.veld_onderdeel_nerfrichting.currentData(),
                kantenband_randen=gekozen_randen,
                fabriekskantenband_vereist=self.veld_onderdeel_fabriekskantenband.isChecked(),
                groep_id=groep_id,
                groep_volgorde=self.veld_onderdeel_groep_volgorde.value() if groep_id else None,
            )
        )
        self.veld_onderdeel_naam.clear()
        self.veld_onderdeel_nerfrichting.setCurrentIndex(0)
        for vinkje in self.veld_onderdeel_kantenband.values():
            vinkje.setChecked(False)
        self.veld_onderdeel_fabriekskantenband.setChecked(False)
        self.veld_onderdeel_groep_id.clear()
        self.veld_onderdeel_groep_volgorde.setValue(0)
        self._ververs_onderdelen_lijst()

    def _submodel_toevoegen(self) -> None:
        model_id = self.veld_submodel.currentData()
        if model_id is None:
            return
        self.huidige_submodellen.append(
            SubModelVerwijzing(model_id=model_id, aantal=self.veld_submodel_aantal.value())
        )
        self._ververs_submodellen_lijst()

    def _model_uit_formulier(self) -> Model:
        tags = tuple(t.strip() for t in self.veld_tags.text().split(",") if t.strip())
        return Model(
            id=self.huidig_id or "",
            naam=self.veld_naam.text(),
            omschrijving=self.veld_omschrijving.text(),
            map=self.veld_map.text(),
            tags=tags,
            onderdelen=list(self.huidige_onderdelen),
            submodellen=list(self.huidige_submodellen),
        )

    # -- acties -------------------------------------------------------------
    def _opslaan(self) -> None:
        model = self._model_uit_formulier()
        fouten = valideer(model, self.materialen, self.bibliotheek)
        if fouten:
            self.label_fouten.setText("\n".join(fouten))
            return
        self.label_fouten.setText("")

        if self.huidig_id is None:
            model = self.bibliotheek.toevoegen(model)
            self.huidig_id = model.id
        else:
            self.bibliotheek.bijwerken(model)

        self._ververs_tabel()

    def _verwijderen(self) -> None:
        model_id = self._geselecteerd_model_id()
        if model_id is None:
            return
        try:
            self.bibliotheek.verwijderen(model_id)
        except ModelInGebruikError as exc:
            QMessageBox.warning(self, "Verwijderen niet mogelijk", str(exc))
            return
        self.huidig_id = None
        self._ververs_tabel()


def main() -> None:
    app = QApplication(sys.argv)
    venster = ModellenTestVenster()
    venster.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
