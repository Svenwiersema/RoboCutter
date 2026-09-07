"""Projectdetail-tabblad: de PySide6-uitwerking van de door Sven
goedgekeurde HTML-conceptmockup
(``design/assets/mockups/project-detail-concept.html``). Eén los,
sluitbaar tabblad per geopend project (``MainWindow._open_tab_project``,
tabsleutel ``f"project:{project_id}"``) — anders dan de
bibliotheekschermen kunnen meerdere van deze tabbladen tegelijk open
staan, en worden ze bij sluiten ook echt vernietigd i.p.v. voor altijd
in leven te blijven (zie ``main_window.py``).

Zijbalk (216px, zelfde opzet als ``materialen_page.py``/
``projecten_page.py``) met vijf secties: Overzicht/Samenstelling/
Zaaglijst, en onder een "Documenten"-scheiding Labels/Zaagplannen
(allebei nu een "binnenkort"-placeholder — ze hangen vast aan
hoofdstuk 6 resp. echte zaagplan-generatie vanuit een project, allebei
nog niet gebouwd). De vijf panelen zitten in een ``QStackedWidget``
onder een gedeelde projectkop (breadcrumb, titel + statuschip,
klant-/opdracht-/opleverdatum, archiveerknop).

Twee dingen die Sven tijdens het goedkeuren van de mockup liet
rechtzetten (verwerkt in het bewaarde mockup-bestand, en dus ook hier):
lijst en toevoegpaneel in Samenstelling staan naast elkaar i.p.v. onder
elkaar, en "model toevoegen" is geen kale dropdown maar een
doorzoekbare zoekpopup. Dat laatste is hier gebouwd met een
``QCompleter`` (``Qt.MatchFlag.MatchContains``, gekoppeld aan een
``QLineEdit``) i.p.v. een los, handmatig gepositioneerd popup-frame
zoals in de HTML — hetzelfde bewezen patroon als de map-completer in
``modellen_page.py``, en functioneel identiek aan wat Sven vroeg
("doorzoekbare popup i.p.v. kale dropdown"). Dit patroon moet ook nog
toegepast worden op de submodel-picker in ``modellen_page.py`` (nog een
kale combobox — vastgelegd aandachtspunt, niet in deze stap
aangepakt).

Deelt de ``ProjectenBibliotheek``/``ModellenBibliotheek``/
``MaterialenBibliotheek``-instanties van ``main_window.py`` i.p.v. eigen
verbindingen te openen — dit scherm opent zelf geen SQLite-verbinding
en heeft dus ook geen ``sluit_verbinding()``.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Callable

from PySide6.QtCore import QSize, Qt, QStringListModel, QTimer
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QButtonGroup,
    QComboBox,
    QCompleter,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from robocutter.instellingen.beheer import InstellingenBeheer
from robocutter.instellingen.models import GELDIGE_ZAAGSTRATEGIEEN
from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.materialen.models import MateriaalStatus
from robocutter.modellen.bibliotheek import ModellenBibliotheek
from robocutter.modellen.models import ModelOnderdeel, Nerfrichting, Rand
from robocutter.projecten.bibliotheek import (
    OnbekendModelError,
    OngeldigeStatusOvergangError,
    ProjectenBibliotheek,
    valideer,
)
from robocutter.projecten.models import Project, ProjectModelInstantie, ProjectStatus
from robocutter.projecten.zaaglijst import SORTEERSLEUTELS, bouw_zaaglijst, sorteer_zaaglijst
from robocutter.projecten.zaagplannen import PlaatZaagplan, genereer_zaagplannen_voor_project
from robocutter.ui.icons import icon, icon_pixmap
from robocutter.ui.theme import Theme
from robocutter.ui.widgets.stat_tile import StatTile
from robocutter.ui.widgets.zaagplaat_widget import ZaagplaatWidget

_STATUS_CHIP = {
    ProjectStatus.WERKVOORBEREIDING: ("prep", "neutral_dot"),
    ProjectStatus.IN_PRODUCTIE: ("production", "accent"),
    ProjectStatus.INSTALLATIE: ("install", "indigo"),
    ProjectStatus.AFGEROND: ("done", "success"),
}
_SORTEER_LABEL = {
    "materiaal": "Materiaal", "naam": "Naam", "breedte": "Breedte",
    "hoogte": "Hoogte", "aantal": "Aantal", "herkomst": "Herkomst",
}
_PANEEL_ITEMS = [("overzicht", "user", "Overzicht"), ("samenstelling", "layers", "Samenstelling"), ("zaaglijst", "list", "Zaaglijst")]
# "Labels" hangt nog vast aan hoofdstuk 6 (niet gebouwd) en blijft dus
# een "binnenkort"-placeholder; "Zaagplannen" is dat sinds deze stap
# niet meer, zie _build_zaagplannen_paneel.
_DOC_ITEMS = [("labels", "tag", "Labels", True), ("zaagplannen", "document", "Zaagplannen", False)]
_STRATEGIE_LABEL = {
    "efficient": "Efficiënt",
    "rijen": "Rijen",
    "stroken": "Stroken",
    "guillotine": "Guillotine",
}


def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
        elif item.layout() is not None:
            _clear_layout(item.layout())


def _datum_tekst(d: date | None) -> str:
    return d.isoformat() if d is not None else "—"


class _ZoekVeld(QLineEdit):
    """Een QLineEdit die zijn QCompleter-popup ook al bij focus toont
    (niet pas na de eerste toetsaanslag) — zodat de volledige
    modellenlijst meteen zichtbaar is, net als de focus-getriggerde
    popup uit de goedgekeurde HTML-mockup."""

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        if self.completer() is not None:
            self.completer().setCompletionPrefix(self.text())
            self.completer().complete()


class ProjectDetailPage(QWidget):
    def __init__(
        self,
        project_id: str,
        projecten: ProjectenBibliotheek,
        modellen: ModellenBibliotheek,
        materialen: MaterialenBibliotheek,
        theme: Theme,
        on_gewijzigd: Callable[[], None] | None = None,
        on_open_projecten_tab: Callable[[], None] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._project_id = project_id
        self._projecten = projecten
        self._modellen = modellen
        self._materialen = materialen
        self._theme = theme
        self._on_gewijzigd = on_gewijzigd
        self._on_open_projecten_tab = on_open_projecten_tab

        self._actief_paneel = "overzicht"
        self._sort_niveaus: list[str] = ["materiaal", "breedte"]
        self._bewerk_los_onderdeel_id: str | None = None
        self._model_naam_naar_id: dict[str, str] = {}
        self._instanties_uitgeklapt: set[str] = set()
        self._zaagplan_strategie = self._standaard_zaagstrategie()
        self._zaagplannen: list[PlaatZaagplan] | None = None
        self._zaagplan_waarschuwingen: list[str] = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._sidebar = self._build_sidebar()
        self._view = self._build_view()
        layout.addWidget(self._sidebar)
        layout.addWidget(self._view, 1)

        self._ververs_alles()

    def _project(self) -> Project:
        return self._projecten.ophalen(self._project_id)

    def _standaard_zaagstrategie(self) -> str:
        waarde = InstellingenBeheer().huidige.standaard_zaagstrategie
        return waarde if waarde in GELDIGE_ZAAGSTRATEGIEEN else GELDIGE_ZAAGSTRATEGIEEN[0]

    # ------------------------------------------------------------------
    # Thema: zelfde bewuste volledige-herbouw-aanpak als de andere pagina's
    # ------------------------------------------------------------------
    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        layout = self.layout()
        _clear_layout(layout)
        self._sidebar = self._build_sidebar()
        self._view = self._build_view()
        layout.addWidget(self._sidebar)
        layout.addWidget(self._view, 1)
        self._ververs_alles()

    def _meld_gewijzigd(self) -> None:
        if self._on_gewijzigd is not None:
            self._on_gewijzigd()

    # ------------------------------------------------------------------
    # Zijbalk
    # ------------------------------------------------------------------
    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(216)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(4)

        self._sidebar_titel = self._sidebar_label(self._project().naam)
        layout.addWidget(self._sidebar_titel)

        self._paneel_groep = QButtonGroup(sidebar)
        self._paneel_groep.setExclusive(True)
        self._paneel_knoppen: dict[str, QPushButton] = {}

        for key, icon_naam, tekst in _PANEEL_ITEMS:
            widget, knop = self._sidebar_nav_item(icon_naam, tekst)
            knop.clicked.connect(lambda checked=False, k=key: self._zet_paneel(k))
            self._paneel_groep.addButton(knop)
            self._paneel_knoppen[key] = knop
            layout.addWidget(widget)

        layout.addWidget(self._divider())
        layout.addWidget(self._sidebar_label("Documenten"))

        for key, icon_naam, tekst, soon in _DOC_ITEMS:
            widget, knop = self._sidebar_nav_item(icon_naam, tekst, soon=soon)
            knop.clicked.connect(lambda checked=False, k=key: self._zet_paneel(k))
            self._paneel_groep.addButton(knop)
            self._paneel_knoppen[key] = knop
            layout.addWidget(widget)

        self._paneel_knoppen[self._actief_paneel].setChecked(True)
        layout.addStretch(1)
        return sidebar

    def _sidebar_label(self, text: str) -> QLabel:
        label = QLabel(text.upper())
        label.setProperty("role", "sidebarLabel")
        label.setContentsMargins(8, 4, 8, 4)
        return label

    def _sidebar_nav_item(self, icon_naam: str, tekst: str, soon: bool = False) -> tuple[QWidget, QPushButton]:
        button = QPushButton(f"  {tekst}")
        button.setProperty("role", "sidebarItem")
        button.setCheckable(True)
        button.setIcon(icon(icon_naam, self._theme.text_muted, 16))
        button.setIconSize(QSize(16, 16))
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        if not soon:
            return button, button
        wrapper = QWidget()
        wrapper_layout = QHBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(button, 1)
        badge = QLabel("BINNENKORT")
        badge.setProperty("role", "sidebarSoon")
        wrapper_layout.addWidget(badge)
        return wrapper, button

    def _divider(self) -> QFrame:
        line = QFrame()
        line.setObjectName("SidebarDivider")
        line.setFixedHeight(1)
        line.setContentsMargins(0, 8, 0, 12)
        return line

    def _zet_paneel(self, key: str) -> None:
        if key == self._actief_paneel:
            return
        self._actief_paneel = key
        self._stack.setCurrentWidget(self._paneel_widgets[key])

    # ------------------------------------------------------------------
    # Hoofdgedeelte: projectkop + gestapelde panelen
    # ------------------------------------------------------------------
    def _build_view(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setObjectName("MainScroll")
        scroll.setWidgetResizable(True)

        content = QWidget()
        content.setObjectName("MainScrollContent")
        outer = QVBoxLayout(content)
        outer.setContentsMargins(28, 22, 28, 32)
        outer.setSpacing(18)

        outer.addLayout(self._build_head())

        self._stack = QStackedWidget()
        self._paneel_widgets: dict[str, QWidget] = {
            "overzicht": self._build_overzicht_paneel(),
            "samenstelling": self._build_samenstelling_paneel(),
            "zaaglijst": self._build_zaaglijst_paneel(),
            "labels": self._build_labels_paneel(),
            "zaagplannen": self._build_zaagplannen_paneel(),
        }
        for widget in self._paneel_widgets.values():
            self._stack.addWidget(widget)
        self._stack.setCurrentWidget(self._paneel_widgets[self._actief_paneel])
        outer.addWidget(self._stack)

        scroll.setWidget(content)
        return scroll

    def _build_head(self) -> QVBoxLayout:
        wrapper = QVBoxLayout()
        wrapper.setSpacing(0)

        head_row = QHBoxLayout()
        head_row.setSpacing(20)

        left = QVBoxLayout()
        left.setSpacing(8)

        breadcrumb = QPushButton("  PROJECTEN")
        breadcrumb.setProperty("role", "breadcrumbLink")
        breadcrumb.setIcon(icon("folder", self._theme.text_faint, 12))
        breadcrumb.setIconSize(QSize(12, 12))
        breadcrumb.setCursor(Qt.CursorShape.PointingHandCursor)
        if self._on_open_projecten_tab is not None:
            breadcrumb.clicked.connect(self._on_open_projecten_tab)
        left.addWidget(breadcrumb)

        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        self._titel_label = QLabel("")
        self._titel_label.setObjectName("PageTitle")
        title_row.addWidget(self._titel_label)
        self._chip_container = QWidget()
        chip_layout = QHBoxLayout(self._chip_container)
        chip_layout.setContentsMargins(0, 0, 0, 0)
        title_row.addWidget(self._chip_container)
        title_row.addStretch(1)
        left.addLayout(title_row)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(16)
        self._meta_klant_label = self._meta_item(meta_row, "user")
        self._meta_opdracht_label = self._meta_item(meta_row, "envelope")
        self._meta_oplevering_label = self._meta_item(meta_row, "calendar")
        meta_row.addStretch(1)
        left.addLayout(meta_row)

        head_row.addLayout(left, 1)

        self._archiveer_btn = QPushButton()
        self._archiveer_btn.setProperty("role", "ghost")
        self._archiveer_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._archiveer_btn.clicked.connect(self._archiveer_actie)
        head_row.addWidget(self._archiveer_btn)

        wrapper.addLayout(head_row)
        return wrapper

    def _meta_item(self, row: QHBoxLayout, icon_naam: str) -> QLabel:
        icon_label = QLabel()
        icon_label.setPixmap(icon_pixmap(icon_naam, self._theme.text_faint, 14))
        row.addWidget(icon_label)
        text_label = QLabel("")
        text_label.setProperty("role", "metaText")
        row.addWidget(text_label)
        return text_label

    def _bouw_status_chip(self, project: Project) -> QFrame:
        if project.gearchiveerd:
            chip_key, dot_color, tekst = "archived", self._theme.text_faint, "Gearchiveerd"
        else:
            chip_key, kleur_attr = _STATUS_CHIP[project.status]
            dot_color, tekst = getattr(self._theme, kleur_attr), project.status.value
        chip = QFrame()
        chip.setProperty("chip", chip_key)
        layout = QHBoxLayout(chip)
        layout.setContentsMargins(9, 3, 9, 3)
        layout.setSpacing(6)
        dot = QLabel()
        dot.setFixedSize(7, 7)
        dot.setStyleSheet(f"background: {dot_color}; border-radius: 3px;")
        layout.addWidget(dot)
        layout.addWidget(QLabel(tekst))
        return chip

    def _ververs_head(self) -> None:
        project = self._project()
        self._sidebar_titel.setText(project.naam.upper())
        self._titel_label.setText(project.naam)

        chip_layout = self._chip_container.layout()
        _clear_layout(chip_layout)
        chip_layout.addWidget(self._bouw_status_chip(project))

        self._meta_klant_label.setText(project.klant or "—")
        self._meta_opdracht_label.setText(project.opdrachtnummer or "—")
        self._meta_oplevering_label.setText(
            f"Oplevering {project.opleverdatum.isoformat()}" if project.opleverdatum else "Geen opleverdatum"
        )

        if project.gearchiveerd:
            self._archiveer_btn.setText("  Terugzetten naar actief")
            self._archiveer_btn.setIcon(icon("recycle", self._theme.text, 14))
            self._archiveer_btn.setEnabled(True)
            self._archiveer_btn.setToolTip("")
        else:
            self._archiveer_btn.setText("  Archiveren")
            self._archiveer_btn.setIcon(icon("archive", self._theme.text, 14))
            kan_archiveren = project.status == ProjectStatus.AFGEROND
            self._archiveer_btn.setEnabled(kan_archiveren)
            self._archiveer_btn.setToolTip("" if kan_archiveren else "Alleen mogelijk vanuit status Afgerond")

    def _archiveer_actie(self) -> None:
        project = self._project()
        try:
            if project.gearchiveerd:
                self._projecten.heractiveren(project.id)
            else:
                self._projecten.archiveren(project.id)
        except OngeldigeStatusOvergangError:
            return
        self._ververs_head()
        self._meld_gewijzigd()

    # ------------------------------------------------------------------
    # Gedeelde veld-helpers (zelfde patroon als materialen_page.py/modellen_page.py)
    # ------------------------------------------------------------------
    def _field_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty("role", "fieldLabel")
        return label

    def _field_input(self) -> QLineEdit:
        field = QLineEdit()
        field.setProperty("role", "field")
        return field

    def _wrap_spin_met_stappen(self, field) -> QFrame:
        omhoog = QToolButton()
        omhoog.setProperty("role", "spinStep")
        omhoog.setIcon(icon("chevron-up", self._theme.text_muted, 9))
        omhoog.setCursor(Qt.CursorShape.PointingHandCursor)
        omhoog.setAutoRepeat(True)
        omhoog.clicked.connect(field.stepUp)
        omlaag = QToolButton()
        omlaag.setProperty("role", "spinStep")
        omlaag.setIcon(icon("chevron-down", self._theme.text_muted, 9))
        omlaag.setCursor(Qt.CursorShape.PointingHandCursor)
        omlaag.setAutoRepeat(True)
        omlaag.clicked.connect(field.stepDown)
        stap_kolom = QVBoxLayout()
        stap_kolom.setContentsMargins(0, 0, 0, 0)
        stap_kolom.setSpacing(0)
        stap_kolom.addWidget(omhoog)
        stap_kolom.addWidget(omlaag)

        wrapper = QFrame()
        wrapper.setProperty("role", "fieldSpinWrap")
        wrap_layout = QHBoxLayout(wrapper)
        wrap_layout.setContentsMargins(0, 0, 0, 0)
        wrap_layout.setSpacing(0)
        wrap_layout.addWidget(field, 1)
        wrap_layout.addLayout(stap_kolom)
        return wrapper

    def _field_spin(self, toegestaan_nul: bool = False) -> tuple[QFrame, QDoubleSpinBox]:
        field = QDoubleSpinBox()
        field.setProperty("role", "fieldSpin")
        field.setRange(0.0 if toegestaan_nul else 0.01, 100000.0)
        field.setDecimals(1)
        field.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        return self._wrap_spin_met_stappen(field), field

    def _field_spin_int(self, minimum: int = 1, maximum: int = 1000) -> tuple[QFrame, QSpinBox]:
        field = QSpinBox()
        field.setProperty("role", "fieldSpin")
        field.setRange(minimum, maximum)
        field.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        return self._wrap_spin_met_stappen(field), field

    def _segmented(self, opties: list[tuple[object, str]]) -> tuple[QWidget, QButtonGroup]:
        container = QWidget()
        container.setObjectName("Segmented")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        group = QButtonGroup(container)
        group.setExclusive(True)
        for waarde, tekst in opties:
            btn = QPushButton(tekst)
            btn.setProperty("role", "segment")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("waarde", waarde.value)
            group.addButton(btn)
            layout.addWidget(btn, 1)
        group.buttons()[0].setChecked(True)
        return container, group

    def _rand_chip_rij(self, section: QVBoxLayout) -> dict[Rand, QPushButton]:
        row = QHBoxLayout()
        row.setSpacing(6)
        buttons: dict[Rand, QPushButton] = {}
        for rand in Rand:
            btn = QPushButton(rand.value.capitalize())
            btn.setProperty("role", "chipToggle")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            row.addWidget(btn)
            buttons[rand] = btn
        row.addStretch(1)
        section.addLayout(row)
        return buttons

    def _cel_tekst(self, tekst: str) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(10, 4, 4, 4)
        label = QLabel(tekst)
        label.setProperty("role", "dims")
        layout.addWidget(label)
        return cell

    def _cel_herkomst(self, herkomst: str) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(10, 4, 4, 4)
        chip = QLabel(herkomst)
        chip.setProperty("role", "tagChip")
        layout.addWidget(chip)
        layout.addStretch(1)
        return cell

    # ------------------------------------------------------------------
    # Paneel: Overzicht
    # ------------------------------------------------------------------
    def _build_overzicht_paneel(self) -> QWidget:
        kaart = QFrame()
        kaart.setObjectName("TableCard")
        layout = QVBoxLayout(kaart)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._ov_validation_banner = QFrame()
        self._ov_validation_banner.setObjectName("ValidationBanner")
        banner_layout = QVBoxLayout(self._ov_validation_banner)
        banner_layout.setContentsMargins(12, 10, 12, 10)
        self._ov_validation_label = QLabel("")
        self._ov_validation_label.setProperty("role", "validationText")
        self._ov_validation_label.setWordWrap(True)
        banner_layout.addWidget(self._ov_validation_label)
        self._ov_validation_banner.hide()
        banner_wrap = QWidget()
        banner_wrap_layout = QVBoxLayout(banner_wrap)
        banner_wrap_layout.setContentsMargins(22, 16, 22, 0)
        banner_wrap_layout.addWidget(self._ov_validation_banner)
        layout.addWidget(banner_wrap)

        grid = QGridLayout()
        grid.setContentsMargins(22, 16, 22, 22)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(18)

        def veld_kolom(label_tekst: str, veld: QWidget, rij: int, kolom: int) -> None:
            kol = QVBoxLayout()
            kol.setSpacing(6)
            kol.addWidget(self._field_label(label_tekst))
            kol.addWidget(veld)
            grid.addLayout(kol, rij, kolom)

        self._ov_naam = self._field_input()
        veld_kolom("Projectnaam", self._ov_naam, 0, 0)
        self._ov_klant = self._field_input()
        veld_kolom("Klant", self._ov_klant, 0, 1)
        self._ov_opdrachtnummer = self._field_input()
        veld_kolom("Opdrachtnummer", self._ov_opdrachtnummer, 0, 2)

        self._ov_contactpersoon = self._field_input()
        veld_kolom("Contactpersoon", self._ov_contactpersoon, 1, 0)
        self._ov_email = self._field_input()
        veld_kolom("E-mail", self._ov_email, 1, 1)
        self._ov_telefoon = self._field_input()
        veld_kolom("Telefoon", self._ov_telefoon, 1, 2)

        self._ov_startdatum = self._field_input()
        self._ov_startdatum.setPlaceholderText("jjjj-mm-dd")
        veld_kolom("Startdatum", self._ov_startdatum, 2, 0)
        self._ov_opleverdatum = self._field_input()
        self._ov_opleverdatum.setPlaceholderText("jjjj-mm-dd")
        veld_kolom("Opleverdatum", self._ov_opleverdatum, 2, 1)
        self._ov_status = QComboBox()
        self._ov_status.setProperty("role", "field")
        for status in ProjectStatus:
            self._ov_status.addItem(status.value, status.value)
        veld_kolom("Status", self._ov_status, 2, 2)

        layout.addLayout(grid)

        footer = QHBoxLayout()
        footer.setContentsMargins(22, 14, 22, 14)
        footer.addStretch(1)
        annuleren_btn = QPushButton("Annuleren")
        annuleren_btn.setProperty("role", "ghost")
        annuleren_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        annuleren_btn.clicked.connect(self._ververs_overzicht_paneel)
        footer.addWidget(annuleren_btn)
        opslaan_btn = QPushButton("Wijzigingen opslaan")
        opslaan_btn.setProperty("role", "primary")
        opslaan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        opslaan_btn.clicked.connect(self._overzicht_opslaan)
        footer.addWidget(opslaan_btn)
        footer_widget = QWidget()
        footer_widget.setLayout(footer)
        layout.addWidget(footer_widget)

        return kaart

    def _ververs_overzicht_paneel(self) -> None:
        project = self._project()
        self._ov_naam.setText(project.naam)
        self._ov_klant.setText(project.klant)
        self._ov_opdrachtnummer.setText(project.opdrachtnummer)
        self._ov_contactpersoon.setText(project.contactpersoon)
        self._ov_email.setText(project.email)
        self._ov_telefoon.setText(project.telefoon)
        self._ov_startdatum.setText(project.startdatum.isoformat() if project.startdatum else "")
        self._ov_opleverdatum.setText(project.opleverdatum.isoformat() if project.opleverdatum else "")
        idx = self._ov_status.findData(project.status.value)
        if idx >= 0:
            self._ov_status.setCurrentIndex(idx)
        self._ov_validation_banner.hide()

    def _parse_datum(self, tekst: str) -> tuple[date | None, str | None]:
        """Geeft (datum, foutmelding) terug — precies één daarvan is None."""
        tekst = tekst.strip()
        if not tekst:
            return None, None
        try:
            return date.fromisoformat(tekst), None
        except ValueError:
            return None, f"Ongeldige datum {tekst!r} (verwacht jjjj-mm-dd)."

    def _overzicht_opslaan(self) -> None:
        bestaand = self._project()
        startdatum, fout_start = self._parse_datum(self._ov_startdatum.text())
        opleverdatum, fout_op = self._parse_datum(self._ov_opleverdatum.text())
        datum_fouten = [f for f in (fout_start, fout_op) if f]

        kandidaat = replace(
            bestaand,
            naam=self._ov_naam.text(),
            klant=self._ov_klant.text(),
            contactpersoon=self._ov_contactpersoon.text().strip(),
            email=self._ov_email.text().strip(),
            telefoon=self._ov_telefoon.text().strip(),
            opdrachtnummer=self._ov_opdrachtnummer.text().strip(),
            startdatum=startdatum,
            opleverdatum=opleverdatum,
            status=ProjectStatus(self._ov_status.currentData()),
        )

        fouten = datum_fouten + valideer(kandidaat, self._materialen)
        if fouten:
            self._ov_validation_label.setText("• " + "\n• ".join(fouten))
            self._ov_validation_banner.show()
            return

        self._projecten.bijwerken(kandidaat)
        self._ov_validation_banner.hide()
        self._ververs_head()
        self._meld_gewijzigd()

    # ------------------------------------------------------------------
    # Paneel: Samenstelling
    # ------------------------------------------------------------------
    def _build_samenstelling_paneel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        layout.addWidget(self._build_modellen_kaart())
        layout.addWidget(self._build_losse_onderdelen_kaart())
        layout.addStretch(1)
        return panel

    def _build_modellen_kaart(self) -> QFrame:
        kaart = QFrame()
        kaart.setObjectName("TableCard")
        outer = QHBoxLayout(kaart)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        links = QWidget()
        links_layout = QVBoxLayout(links)
        links_layout.setContentsMargins(0, 0, 0, 0)
        links_layout.setSpacing(0)

        head = QHBoxLayout()
        head.setContentsMargins(18, 16, 18, 16)
        titel = QLabel("Modellen")
        titel.setObjectName("CardTitle")
        head.addWidget(titel)
        head.addStretch(1)
        self._modellen_count_label = QLabel("")
        self._modellen_count_label.setProperty("role", "cardCount")
        head.addWidget(self._modellen_count_label)
        head_widget = QWidget()
        head_widget.setLayout(head)
        links_layout.addWidget(head_widget)

        self._modellen_lijst_container = QVBoxLayout()
        self._modellen_lijst_container.setSpacing(0)
        links_layout.addLayout(self._modellen_lijst_container)
        self._modellen_leeg_label = QLabel("Nog geen modellen toegevoegd aan dit project.")
        self._modellen_leeg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._modellen_leeg_label.setStyleSheet(f"color: {self._theme.text_faint}; font-size: 13px; padding: 32px 0;")
        links_layout.addWidget(self._modellen_leeg_label)
        links_layout.addStretch(1)
        outer.addWidget(links, 1)

        rechts = QFrame()
        rechts.setProperty("role", "splitAdd")
        rechts.setFixedWidth(300)
        rechts_layout = QVBoxLayout(rechts)
        rechts_layout.setContentsMargins(18, 16, 18, 16)
        rechts_layout.setSpacing(12)

        label = QLabel("MODEL TOEVOEGEN")
        label.setProperty("role", "fieldSectionLabel")
        rechts_layout.addWidget(label)

        self._model_search = _ZoekVeld()
        self._model_search.setProperty("role", "field")
        self._model_search.setPlaceholderText("Zoek een model…")
        self._model_completer = QCompleter([])
        self._model_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._model_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._model_completer.popup().setObjectName("ModelPickerPopup")
        self._model_search.setCompleter(self._model_completer)
        rechts_layout.addWidget(self._model_search)

        rechts_layout.addWidget(self._field_label("Aantal"))
        aantal_wrap, self._model_aantal = self._field_spin_int(minimum=1, maximum=1000)
        rechts_layout.addWidget(aantal_wrap)

        self._model_toevoegen_fout = QLabel("")
        self._model_toevoegen_fout.setProperty("role", "validationText")
        self._model_toevoegen_fout.setWordWrap(True)
        self._model_toevoegen_fout.hide()
        rechts_layout.addWidget(self._model_toevoegen_fout)

        model_toevoegen_btn = QPushButton("  Model toevoegen")
        model_toevoegen_btn.setProperty("role", "primary")
        model_toevoegen_btn.setIcon(icon("plus", "#12141B", 12))
        model_toevoegen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        model_toevoegen_btn.clicked.connect(self._model_toevoegen)
        rechts_layout.addWidget(model_toevoegen_btn)
        rechts_layout.addStretch(1)
        outer.addWidget(rechts)

        return kaart

    def _bouw_model_instantie_rij(self, instantie: ProjectModelInstantie, is_laatste: bool) -> QWidget:
        uitgeklapt = instantie.id in self._instanties_uitgeklapt

        row = QFrame()
        row.setProperty("role", "rowItem")
        if is_laatste and not uitgeklapt:
            row.setStyleSheet("border-bottom: none;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(12)

        toggle_btn = QToolButton()
        toggle_btn.setProperty("role", "rowAction")
        toggle_btn.setIcon(icon("chevron-down" if uitgeklapt else "chevron-up", self._theme.text_faint, 13))
        toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle_btn.setToolTip("Onderdelen inklappen" if uitgeklapt else "Onderdelen tonen (materiaal per onderdeel wijzigen)")
        toggle_btn.clicked.connect(lambda: self._toggle_instantie_uitgeklapt(instantie.id))
        layout.addWidget(toggle_btn)

        icon_box = QFrame()
        icon_box.setProperty("role", "rowIconBox")
        icon_box.setFixedSize(34, 34)
        icon_box_layout = QVBoxLayout(icon_box)
        icon_box_layout.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel()
        icon_label.setPixmap(icon_pixmap("cube", self._theme.text_muted, 16))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("background: transparent;")
        icon_box_layout.addWidget(icon_label)
        layout.addWidget(icon_box)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        titel_tekst = instantie.model_naam + (f"  ×{instantie.aantal}" if instantie.aantal != 1 else "")
        titel = QLabel(titel_tekst)
        titel.setProperty("role", "matName")
        info_col.addWidget(titel)
        sub = QLabel(f"{len(instantie.onderdelen)} onderdelen (platgeslagen kopie) · toegevoegd vanuit Modellenbibliotheek")
        sub.setProperty("role", "matMeta")
        info_col.addWidget(sub)
        layout.addLayout(info_col, 1)

        bijwerken_btn = QToolButton()
        bijwerken_btn.setProperty("role", "rowAction")
        bijwerken_btn.setIcon(icon("recycle", self._theme.text_faint, 15))
        bijwerken_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        bijwerken_btn.setToolTip("Bijwerken naar laatste versie")
        bijwerken_btn.clicked.connect(lambda: self._model_instantie_bijwerken(instantie.id))
        layout.addWidget(bijwerken_btn)

        del_btn = QToolButton()
        del_btn.setProperty("role", "rowActionDanger")
        del_btn.setIcon(icon("trash", self._theme.text_faint, 15))
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setToolTip("Verwijderen")
        del_btn.clicked.connect(lambda: self._model_instantie_verwijderen(instantie.id))
        layout.addWidget(del_btn)

        if not uitgeklapt:
            return row

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)
        wrapper_layout.addWidget(row)
        for index, onderdeel in enumerate(instantie.onderdelen):
            is_laatste_onderdeel = is_laatste and index == len(instantie.onderdelen) - 1
            wrapper_layout.addWidget(self._bouw_model_onderdeel_rij(instantie, onderdeel, is_laatste_onderdeel))
        return wrapper

    def _bouw_model_onderdeel_rij(self, instantie: ProjectModelInstantie, onderdeel: ModelOnderdeel, is_laatste: bool) -> QWidget:
        row = QFrame()
        row.setProperty("role", "rowItem")
        row.setStyleSheet(f"background: {self._theme.surface_2}; border-bottom: none;" if is_laatste else f"background: {self._theme.surface_2};")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(18, 8, 18, 8)
        layout.setSpacing(12)

        info_col = QVBoxLayout()
        info_col.setSpacing(1)
        titel = QLabel(onderdeel.naam + (f"  ×{onderdeel.aantal}" if onderdeel.aantal != 1 else ""))
        titel.setProperty("role", "dims")
        info_col.addWidget(titel)
        sub = QLabel(f"{onderdeel.breedte:g} × {onderdeel.hoogte:g} mm")
        sub.setProperty("role", "matMeta")
        info_col.addWidget(sub)
        layout.addLayout(info_col, 1)

        materiaal_combo = QComboBox()
        materiaal_combo.setProperty("role", "field")
        materiaal_combo.setMinimumWidth(220)
        for materiaal in sorted(self._materialen.lijst(), key=lambda m: m.naam.lower()):
            label = materiaal.naam
            if materiaal.status != MateriaalStatus.ACTIEF:
                label += " (gearchiveerd)"
            materiaal_combo.addItem(label, materiaal.id)
        idx = materiaal_combo.findData(onderdeel.materiaal_id)
        if idx >= 0:
            materiaal_combo.setCurrentIndex(idx)
        materiaal_combo.currentIndexChanged.connect(
            lambda _i, c=materiaal_combo: self._model_onderdeel_materiaal_wijzigen(instantie.id, onderdeel.id, c.currentData())
        )
        layout.addWidget(materiaal_combo)

        return row

    def _ververs_modellen_kaart(self) -> None:
        project = self._project()
        n_model = len(project.modelinstanties)
        n_onderdelen = sum(len(i.onderdelen) * i.aantal for i in project.modelinstanties)
        self._modellen_count_label.setText(
            f"{n_model} model{'' if n_model == 1 else 'len'} · {n_onderdelen} onderdelen" if n_model else ""
        )
        _clear_layout(self._modellen_lijst_container)
        self._modellen_leeg_label.setVisible(not project.modelinstanties)
        for index, instantie in enumerate(project.modelinstanties):
            is_laatste = index == len(project.modelinstanties) - 1
            self._modellen_lijst_container.addWidget(self._bouw_model_instantie_rij(instantie, is_laatste))

        modellen = sorted(self._modellen.lijst(), key=lambda m: m.naam.lower())
        self._model_naam_naar_id = {m.naam: m.id for m in modellen}
        self._model_completer.setModel(QStringListModel([m.naam for m in modellen], self._model_completer))

    def _model_toevoegen(self) -> None:
        model_id = self._model_naam_naar_id.get(self._model_search.text().strip())
        if not model_id:
            self._model_toevoegen_fout.setText("Kies een model uit de lijst.")
            self._model_toevoegen_fout.show()
            return
        self._model_toevoegen_fout.hide()
        self._projecten.model_toevoegen(self._project_id, model_id, self._model_aantal.value())
        self._model_search.clear()
        self._model_aantal.setValue(1)
        self._ververs_samenstelling()
        self._ververs_zaaglijst_paneel()
        self._meld_gewijzigd()

    def _model_instantie_bijwerken(self, instantie_id: str) -> None:
        try:
            self._projecten.model_bijwerken_naar_laatste_versie(self._project_id, instantie_id)
        except OnbekendModelError:
            pass
        self._ververs_samenstelling()
        self._ververs_zaaglijst_paneel()
        self._meld_gewijzigd()

    def _model_instantie_verwijderen(self, instantie_id: str) -> None:
        self._projecten.model_instantie_verwijderen(self._project_id, instantie_id)
        self._instanties_uitgeklapt.discard(instantie_id)
        self._ververs_samenstelling()
        self._ververs_zaaglijst_paneel()
        self._meld_gewijzigd()

    def _toggle_instantie_uitgeklapt(self, instantie_id: str) -> None:
        if instantie_id in self._instanties_uitgeklapt:
            self._instanties_uitgeklapt.discard(instantie_id)
        else:
            self._instanties_uitgeklapt.add(instantie_id)
        self._ververs_modellen_kaart()

    def _model_onderdeel_materiaal_wijzigen(self, instantie_id: str, onderdeel_id: str, materiaal_id: str) -> None:
        if not materiaal_id:
            return
        self._projecten.model_onderdeel_materiaal_wijzigen(self._project_id, instantie_id, onderdeel_id, materiaal_id)
        self._ververs_samenstelling()
        self._ververs_zaaglijst_paneel()
        self._meld_gewijzigd()

    def _build_losse_onderdelen_kaart(self) -> QFrame:
        kaart = QFrame()
        kaart.setObjectName("TableCard")
        outer = QHBoxLayout(kaart)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        links = QWidget()
        links_layout = QVBoxLayout(links)
        links_layout.setContentsMargins(0, 0, 0, 0)
        links_layout.setSpacing(0)

        head = QHBoxLayout()
        head.setContentsMargins(18, 16, 18, 16)
        titel = QLabel("Losse onderdelen")
        titel.setObjectName("CardTitle")
        head.addWidget(titel)
        head.addStretch(1)
        self._onderdelen_count_label = QLabel("")
        self._onderdelen_count_label.setProperty("role", "cardCount")
        head.addWidget(self._onderdelen_count_label)
        head_widget = QWidget()
        head_widget.setLayout(head)
        links_layout.addWidget(head_widget)

        self._onderdelen_lijst_container = QVBoxLayout()
        self._onderdelen_lijst_container.setSpacing(0)
        links_layout.addLayout(self._onderdelen_lijst_container)
        self._onderdelen_leeg_label = QLabel("Nog geen losse onderdelen toegevoegd.")
        self._onderdelen_leeg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._onderdelen_leeg_label.setStyleSheet(f"color: {self._theme.text_faint}; font-size: 13px; padding: 32px 0;")
        links_layout.addWidget(self._onderdelen_leeg_label)
        links_layout.addStretch(1)
        outer.addWidget(links, 1)

        rechts = QFrame()
        rechts.setProperty("role", "splitAdd")
        rechts.setFixedWidth(300)
        rechts_layout = QVBoxLayout(rechts)
        rechts_layout.setContentsMargins(18, 16, 18, 16)
        rechts_layout.setSpacing(10)

        self._onderdeel_form_titel = QLabel("NIEUW LOS ONDERDEEL")
        self._onderdeel_form_titel.setProperty("role", "fieldSectionLabel")
        rechts_layout.addWidget(self._onderdeel_form_titel)

        rechts_layout.addWidget(self._field_label("Naam"))
        self._lo_naam = self._field_input()
        self._lo_naam.setPlaceholderText("bijv. Plint")
        rechts_layout.addWidget(self._lo_naam)

        rechts_layout.addWidget(self._field_label("Materiaal"))
        self._lo_materiaal = QComboBox()
        self._lo_materiaal.setProperty("role", "field")
        rechts_layout.addWidget(self._lo_materiaal)

        afmeting_rij = QHBoxLayout()
        afmeting_rij.setSpacing(8)
        breedte_col = QVBoxLayout()
        breedte_col.addWidget(self._field_label("Breedte mm"))
        breedte_wrap, self._lo_breedte = self._field_spin()
        breedte_col.addWidget(breedte_wrap)
        afmeting_rij.addLayout(breedte_col)
        hoogte_col = QVBoxLayout()
        hoogte_col.addWidget(self._field_label("Hoogte mm"))
        hoogte_wrap, self._lo_hoogte = self._field_spin()
        hoogte_col.addWidget(hoogte_wrap)
        afmeting_rij.addLayout(hoogte_col)
        rechts_layout.addLayout(afmeting_rij)

        rechts_layout.addWidget(self._field_label("Aantal"))
        aantal_wrap, self._lo_aantal = self._field_spin_int(minimum=1, maximum=1000)
        rechts_layout.addWidget(aantal_wrap)

        rechts_layout.addWidget(self._field_label("Nerfrichting"))
        nerf_widget, self._lo_nerf_group = self._segmented(
            [(Nerfrichting.GEEN, "Geen"), (Nerfrichting.LANGE_ZIJDE, "Lange zijde"), (Nerfrichting.KORTE_ZIJDE, "Korte zijde")]
        )
        rechts_layout.addWidget(nerf_widget)

        rechts_layout.addWidget(self._field_label("Kantenband"))
        self._lo_rand_buttons = self._rand_chip_rij(rechts_layout)

        self._onderdeel_toevoegen_fout = QLabel("")
        self._onderdeel_toevoegen_fout.setProperty("role", "validationText")
        self._onderdeel_toevoegen_fout.setWordWrap(True)
        self._onderdeel_toevoegen_fout.hide()
        rechts_layout.addWidget(self._onderdeel_toevoegen_fout)

        knoppen_rij = QHBoxLayout()
        self._lo_annuleren_btn = QPushButton("Annuleren")
        self._lo_annuleren_btn.setProperty("role", "ghost")
        self._lo_annuleren_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._lo_annuleren_btn.clicked.connect(self._reset_los_onderdeel_form)
        self._lo_annuleren_btn.hide()
        knoppen_rij.addWidget(self._lo_annuleren_btn)
        self._lo_opslaan_btn = QPushButton("  Onderdeel toevoegen")
        self._lo_opslaan_btn.setProperty("role", "primary")
        self._lo_opslaan_btn.setIcon(icon("plus", "#12141B", 12))
        self._lo_opslaan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._lo_opslaan_btn.clicked.connect(self._los_onderdeel_opslaan)
        knoppen_rij.addWidget(self._lo_opslaan_btn, 1)
        rechts_layout.addLayout(knoppen_rij)
        rechts_layout.addStretch(1)
        outer.addWidget(rechts)

        return kaart

    def _bouw_los_onderdeel_rij(self, o: ModelOnderdeel, is_laatste: bool) -> QWidget:
        row = QFrame()
        row.setProperty("role", "rowItem")
        if is_laatste:
            row.setStyleSheet("border-bottom: none;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(12)

        icon_box = QFrame()
        icon_box.setProperty("role", "rowIconBox")
        icon_box.setFixedSize(34, 34)
        icon_box_layout = QVBoxLayout(icon_box)
        icon_box_layout.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel()
        icon_label.setPixmap(icon_pixmap("bar", self._theme.text_muted, 16))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("background: transparent;")
        icon_box_layout.addWidget(icon_label)
        layout.addWidget(icon_box)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        titel = QLabel(o.naam)
        titel.setProperty("role", "matName")
        info_col.addWidget(titel)
        try:
            materiaal_naam = self._materialen.ophalen(o.materiaal_id).naam
        except KeyError:
            materiaal_naam = "onbekend materiaal"
        sub = QLabel(f"{materiaal_naam} · {o.breedte:g} × {o.hoogte:g} mm · aantal {o.aantal}")
        sub.setProperty("role", "matMeta")
        info_col.addWidget(sub)
        layout.addLayout(info_col, 1)

        edit_btn = QToolButton()
        edit_btn.setProperty("role", "rowAction")
        edit_btn.setIcon(icon("pencil", self._theme.text_faint, 14))
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setToolTip("Bewerken")
        edit_btn.clicked.connect(lambda: self._bewerk_los_onderdeel(o.id))
        layout.addWidget(edit_btn)

        del_btn = QToolButton()
        del_btn.setProperty("role", "rowActionDanger")
        del_btn.setIcon(icon("trash", self._theme.text_faint, 14))
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setToolTip("Verwijderen")
        del_btn.clicked.connect(lambda: self._verwijder_los_onderdeel(o.id))
        layout.addWidget(del_btn)

        return row

    def _ververs_onderdelen_kaart(self) -> None:
        project = self._project()
        n = len(project.losse_onderdelen)
        self._onderdelen_count_label.setText(f"{n} onderdeel" if n == 1 else (f"{n} onderdelen" if n else ""))
        _clear_layout(self._onderdelen_lijst_container)
        self._onderdelen_leeg_label.setVisible(not project.losse_onderdelen)
        for index, onderdeel in enumerate(project.losse_onderdelen):
            is_laatste = index == len(project.losse_onderdelen) - 1
            self._onderdelen_lijst_container.addWidget(self._bouw_los_onderdeel_rij(onderdeel, is_laatste))

        huidige = self._lo_materiaal.currentData()
        self._lo_materiaal.clear()
        for materiaal in sorted(self._materialen.lijst(), key=lambda m: m.naam.lower()):
            label = materiaal.naam
            if materiaal.status != MateriaalStatus.ACTIEF:
                label += " (gearchiveerd)"
            self._lo_materiaal.addItem(label, materiaal.id)
        idx = self._lo_materiaal.findData(huidige)
        if idx >= 0:
            self._lo_materiaal.setCurrentIndex(idx)

    def _ververs_samenstelling(self) -> None:
        self._ververs_modellen_kaart()
        self._ververs_onderdelen_kaart()

    def _reset_los_onderdeel_form(self) -> None:
        self._bewerk_los_onderdeel_id = None
        self._onderdeel_form_titel.setText("NIEUW LOS ONDERDEEL")
        self._lo_opslaan_btn.setText("  Onderdeel toevoegen")
        self._lo_annuleren_btn.hide()
        self._lo_naam.clear()
        if self._lo_materiaal.count():
            self._lo_materiaal.setCurrentIndex(0)
        self._lo_breedte.setValue(0)
        self._lo_hoogte.setValue(0)
        self._lo_aantal.setValue(1)
        self._lo_nerf_group.buttons()[0].setChecked(True)
        for btn in self._lo_rand_buttons.values():
            btn.setChecked(False)
        self._onderdeel_toevoegen_fout.hide()

    def _bewerk_los_onderdeel(self, onderdeel_id: str) -> None:
        onderdeel = next((o for o in self._project().losse_onderdelen if o.id == onderdeel_id), None)
        if onderdeel is None:
            return
        self._bewerk_los_onderdeel_id = onderdeel_id
        self._onderdeel_form_titel.setText(f"ONDERDEEL BEWERKEN: {onderdeel.naam.upper()}")
        self._lo_opslaan_btn.setText("  Wijzigingen opslaan")
        self._lo_annuleren_btn.show()
        self._lo_naam.setText(onderdeel.naam)
        idx = self._lo_materiaal.findData(onderdeel.materiaal_id)
        if idx >= 0:
            self._lo_materiaal.setCurrentIndex(idx)
        self._lo_breedte.setValue(onderdeel.breedte)
        self._lo_hoogte.setValue(onderdeel.hoogte)
        self._lo_aantal.setValue(onderdeel.aantal)
        for btn in self._lo_nerf_group.buttons():
            btn.setChecked(btn.property("waarde") == onderdeel.nerfrichting_vereist)
        for rand, btn in self._lo_rand_buttons.items():
            btn.setChecked(rand in onderdeel.kantenband_randen)
        self._onderdeel_toevoegen_fout.hide()

    def _los_onderdeel_opslaan(self) -> None:
        nerf_waarde = Nerfrichting(self._lo_nerf_group.checkedButton().property("waarde"))
        onderdeel = ModelOnderdeel(
            id=self._bewerk_los_onderdeel_id or "",
            naam=self._lo_naam.text().strip() or "Onderdeel",
            materiaal_id=self._lo_materiaal.currentData() or "",
            breedte=self._lo_breedte.value(),
            hoogte=self._lo_hoogte.value(),
            aantal=self._lo_aantal.value(),
            nerfrichting_vereist=nerf_waarde,
            kantenband_randen=frozenset(r for r, b in self._lo_rand_buttons.items() if b.isChecked()),
        )
        try:
            if self._bewerk_los_onderdeel_id:
                self._projecten.los_onderdeel_bijwerken(self._project_id, onderdeel)
            else:
                self._projecten.los_onderdeel_toevoegen(self._project_id, onderdeel)
        except ValueError as exc:
            self._onderdeel_toevoegen_fout.setText(str(exc))
            self._onderdeel_toevoegen_fout.show()
            return
        self._reset_los_onderdeel_form()
        self._ververs_samenstelling()
        self._ververs_zaaglijst_paneel()
        self._meld_gewijzigd()

    def _verwijder_los_onderdeel(self, onderdeel_id: str) -> None:
        self._projecten.los_onderdeel_verwijderen(self._project_id, onderdeel_id)
        if self._bewerk_los_onderdeel_id == onderdeel_id:
            self._reset_los_onderdeel_form()
        self._ververs_samenstelling()
        self._ververs_zaaglijst_paneel()
        self._meld_gewijzigd()

    # ------------------------------------------------------------------
    # Paneel: Zaaglijst
    # ------------------------------------------------------------------
    def _build_zaaglijst_paneel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        sort_label = QLabel("SORTEREN OP")
        sort_label.setProperty("role", "fieldSectionLabel")
        toolbar.addWidget(sort_label)
        self._sort_niveau_container = QHBoxLayout()
        self._sort_niveau_container.setSpacing(8)
        toolbar.addLayout(self._sort_niveau_container)
        self._sort_toevoegen_btn = QPushButton("  Niveau toevoegen")
        self._sort_toevoegen_btn.setProperty("role", "addSortLevel")
        self._sort_toevoegen_btn.setIcon(icon("plus", self._theme.text_faint, 11))
        self._sort_toevoegen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sort_toevoegen_btn.clicked.connect(self._sort_niveau_toevoegen)
        toolbar.addWidget(self._sort_toevoegen_btn)
        toolbar.addStretch(1)
        vernieuwen_btn = QPushButton("  Vernieuwen")
        vernieuwen_btn.setProperty("role", "ghost")
        vernieuwen_btn.setIcon(icon("recycle", self._theme.text, 13))
        vernieuwen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        vernieuwen_btn.clicked.connect(self._ververs_zaaglijst_paneel)
        toolbar.addWidget(vernieuwen_btn)
        layout.addLayout(toolbar)

        table_card = QFrame()
        table_card.setObjectName("TableCard")
        card_layout = QVBoxLayout(table_card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        self._zaaglijst_table = QTableWidget(0, 6)
        self._zaaglijst_table.setObjectName("LibraryTable")
        self._zaaglijst_table.setHorizontalHeaderLabels(
            ["Onderdeel", "Materiaal", "Breedte", "Hoogte", "Aantal", "Herkomst"]
        )
        self._zaaglijst_table.verticalHeader().setVisible(False)
        self._zaaglijst_table.setShowGrid(False)
        self._zaaglijst_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._zaaglijst_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._zaaglijst_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        header = self._zaaglijst_table.horizontalHeader()
        header.setStretchLastSection(True)
        for col, breedte in enumerate([260, 220, 100, 100, 90]):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            self._zaaglijst_table.setColumnWidth(col, breedte)
        card_layout.addWidget(self._zaaglijst_table)

        self._zaaglijst_leeg_label = QLabel("Nog geen onderdelen in dit project.")
        self._zaaglijst_leeg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zaaglijst_leeg_label.setStyleSheet(f"color: {self._theme.text_faint}; font-size: 13px; padding: 48px 0;")
        self._zaaglijst_leeg_label.hide()
        card_layout.addWidget(self._zaaglijst_leeg_label)

        layout.addWidget(table_card, 1)

        footer = QHBoxLayout()
        self._zaaglijst_totaal_label = QLabel("")
        self._zaaglijst_totaal_label.setProperty("role", "matMeta")
        footer.addWidget(self._zaaglijst_totaal_label)
        footer.addStretch(1)
        self._zaaglijst_gesorteerd_label = QLabel("")
        self._zaaglijst_gesorteerd_label.setProperty("role", "matMeta")
        footer.addWidget(self._zaaglijst_gesorteerd_label)
        layout.addLayout(footer)

        return panel

    def _bouw_sort_niveau(self, index: int, sleutel: str) -> QWidget:
        row = QFrame()
        row.setProperty("role", "sortLevel")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(4, 2, 2, 2)
        layout.setSpacing(4)

        badge = QLabel(str(index + 1))
        badge.setProperty("role", "sortLevelNum")
        badge.setFixedSize(16, 16)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(badge)

        combo = QComboBox()
        # Zelfde valkuil als elders gedocumenteerd: een QComboBox zonder
        # expliciete eigen kleur kan onzichtbaar renderen op een transparante
        # achtergrond — vandaar hier bewust ook color/font-weight meegeven
        # i.p.v. alleen border/background.
        combo.setStyleSheet(
            f"border: none; background: transparent; color: {self._theme.text}; "
            f"font-size: 12.5px; font-weight: 600;"
        )
        for sleutel_optie in SORTEERSLEUTELS:
            combo.addItem(_SORTEER_LABEL[sleutel_optie], sleutel_optie)
        idx = combo.findData(sleutel)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        combo.currentIndexChanged.connect(lambda _i, i=index: self._sort_niveau_gewijzigd(i, combo.currentData()))
        layout.addWidget(combo)

        verwijder_btn = QToolButton()
        verwijder_btn.setProperty("role", "rowAction")
        verwijder_btn.setIcon(icon("close", self._theme.text_faint, 10))
        verwijder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        verwijder_btn.clicked.connect(lambda: self._sort_niveau_verwijderen(index))
        layout.addWidget(verwijder_btn)

        return row

    def _sort_niveau_gewijzigd(self, index: int, sleutel: str) -> None:
        self._sort_niveaus[index] = sleutel
        self._ververs_zaaglijst_paneel()

    def _sort_niveau_verwijderen(self, index: int) -> None:
        del self._sort_niveaus[index]
        self._ververs_zaaglijst_paneel()

    def _sort_niveau_toevoegen(self) -> None:
        beschikbaar = [s for s in SORTEERSLEUTELS if s not in self._sort_niveaus]
        if not beschikbaar:
            return
        self._sort_niveaus.append(beschikbaar[0])
        self._ververs_zaaglijst_paneel()

    def _ververs_zaaglijst_paneel(self) -> None:
        _clear_layout(self._sort_niveau_container)
        for index, sleutel in enumerate(self._sort_niveaus):
            self._sort_niveau_container.addWidget(self._bouw_sort_niveau(index, sleutel))
        self._sort_toevoegen_btn.setEnabled(len(self._sort_niveaus) < len(SORTEERSLEUTELS))

        project = self._project()
        regels = sorteer_zaaglijst(bouw_zaaglijst(project), self._sort_niveaus, self._materialen)

        self._zaaglijst_table.clearContents()
        self._zaaglijst_table.setRowCount(len(regels))
        self._zaaglijst_table.setVisible(bool(regels))
        self._zaaglijst_leeg_label.setVisible(not regels)
        for row_index, regel in enumerate(regels):
            try:
                materiaal_naam = self._materialen.ophalen(regel.onderdeel.materiaal_id).naam
            except KeyError:
                materiaal_naam = "onbekend materiaal"
            waarden = [
                regel.onderdeel.naam,
                materiaal_naam,
                f"{regel.onderdeel.breedte:g} mm",
                f"{regel.onderdeel.hoogte:g} mm",
                str(regel.onderdeel.aantal),
            ]
            for col, tekst in enumerate(waarden):
                self._zaaglijst_table.setCellWidget(row_index, col, self._cel_tekst(tekst))
            self._zaaglijst_table.setCellWidget(row_index, 5, self._cel_herkomst(regel.herkomst))

        totaal = sum(r.onderdeel.aantal for r in regels)
        self._zaaglijst_totaal_label.setText(
            "1 onderdeel totaal" if totaal == 1 else f"{totaal} onderdelen totaal"
        )
        if self._sort_niveaus:
            namen = [_SORTEER_LABEL[s].lower() for s in self._sort_niveaus]
            self._zaaglijst_gesorteerd_label.setText("Gesorteerd op: " + ", dan ".join(namen))
        else:
            self._zaaglijst_gesorteerd_label.setText("")

    # ------------------------------------------------------------------
    # Panelen: Labels / Zaagplannen (placeholders)
    # ------------------------------------------------------------------
    def _build_labels_paneel(self) -> QWidget:
        return self._build_placeholder_paneel(
            icon_naam="tag",
            tag_tekst="Hoofdstuk 6",
            titel="Labels zijn nog niet beschikbaar",
            tekst=(
                "Labels worden straks automatisch gegenereerd zodra het zaagplan voor dit "
                "project klaar is — met materiaal, projectnummer en afmeting per onderdeel, "
                "optioneel aangevuld met een QR-/barcode. Dat vereist eerst echte "
                "zaagplan-generatie vanuit een project, wat nog gebouwd moet worden."
            ),
        )

    # ------------------------------------------------------------------
    # Paneel: Zaagplannen
    # ------------------------------------------------------------------
    def _build_zaagplannen_paneel(self) -> QWidget:
        panel = QWidget()
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(16)
        self._zaagplannen_content = QVBoxLayout()
        self._zaagplannen_content.setSpacing(16)
        outer.addLayout(self._zaagplannen_content)
        return panel

    def _bouw_strategie_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.setProperty("role", "field")
        for waarde in GELDIGE_ZAAGSTRATEGIEEN:
            combo.addItem(_STRATEGIE_LABEL[waarde], waarde)
        idx = combo.findData(self._zaagplan_strategie)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        combo.currentIndexChanged.connect(lambda _i, c=combo: self._zet_zaagplan_strategie(c.currentData()))
        return combo

    def _zet_zaagplan_strategie(self, waarde: str) -> None:
        self._zaagplan_strategie = waarde

    def _genereer_zaagplannen(self) -> None:
        plannen, waarschuwingen = genereer_zaagplannen_voor_project(
            self._project(), self._materialen, strategie=self._zaagplan_strategie
        )
        self._zaagplannen = plannen
        self._zaagplan_waarschuwingen = waarschuwingen
        self._ververs_zaagplannen_paneel()

    def _ververs_zaagplannen_paneel(self) -> None:
        _clear_layout(self._zaagplannen_content)
        if self._zaagplannen is None:
            self._zaagplannen_content.addWidget(self._bouw_zaagplan_start())
        else:
            self._zaagplannen_content.addWidget(self._bouw_zaagplan_resultaat())

    def _bouw_zaagplan_start(self) -> QWidget:
        kaart = QFrame()
        kaart.setObjectName("TableCard")
        layout = QVBoxLayout(kaart)
        layout.setContentsMargins(30, 56, 30, 56)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_box = QFrame()
        icon_box.setProperty("role", "rowIconBox")
        icon_box.setFixedSize(56, 56)
        icon_box_layout = QVBoxLayout(icon_box)
        icon_box_layout.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel()
        icon_label.setPixmap(icon_pixmap("document", self._theme.text_faint, 26))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("background: transparent;")
        icon_box_layout.addWidget(icon_label)
        layout.addWidget(icon_box, 0, Qt.AlignmentFlag.AlignHCenter)

        titel = QLabel("Nog geen zaagplan gegenereerd")
        titel.setProperty("role", "placeholderTitle")
        titel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(titel)

        aantal_regels = sum(r.onderdeel.aantal for r in bouw_zaaglijst(self._project()))
        tekst = QLabel(
            f"RoboCutter verdeelt de {aantal_regels} onderdelen uit de Zaaglijst automatisch over "
            "zoveel platen per materiaal als nodig, rekening houdend met kerf, randafzaag, "
            "kantenband en nerfrichting. Onderdelen die zelfs op een lege plaat niet passen "
            "worden hieronder gemeld als niet geplaatst."
        )
        tekst.setProperty("role", "placeholderText")
        tekst.setWordWrap(True)
        tekst.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tekst.setMaximumWidth(460)
        layout.addWidget(tekst, 0, Qt.AlignmentFlag.AlignHCenter)

        opties_row = QHBoxLayout()
        opties_row.setSpacing(10)
        opties_row.addStretch(1)
        strategie_label = QLabel("STRATEGIE")
        strategie_label.setProperty("role", "fieldSectionLabel")
        opties_row.addWidget(strategie_label)
        opties_row.addWidget(self._bouw_strategie_combo())
        opties_row.addStretch(1)
        layout.addLayout(opties_row)

        genereer_btn = QPushButton("  Zaagplan genereren")
        genereer_btn.setProperty("role", "primary")
        genereer_btn.setIcon(icon("plus", "#12141B", 13))
        genereer_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        genereer_btn.clicked.connect(self._genereer_zaagplannen)
        layout.addWidget(genereer_btn, 0, Qt.AlignmentFlag.AlignHCenter)

        return kaart

    def _bouw_zaagplan_resultaat(self) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        toolbar = QHBoxLayout()
        titel_kolom = QVBoxLayout()
        titel_kolom.setSpacing(2)
        titel = QLabel("Zaagplannen")
        titel.setProperty("role", "matName")
        titel_kolom.addWidget(titel)
        aantal = len(self._zaagplannen)
        sub = QLabel(
            f"{aantal} {'plaat' if aantal == 1 else 'platen'} · strategie {_STRATEGIE_LABEL[self._zaagplan_strategie]}"
        )
        sub.setProperty("role", "matMeta")
        titel_kolom.addWidget(sub)
        toolbar.addLayout(titel_kolom)
        toolbar.addStretch(1)
        toolbar.addWidget(self._bouw_strategie_combo())
        opnieuw_btn = QPushButton("  Opnieuw genereren")
        opnieuw_btn.setProperty("role", "ghost")
        opnieuw_btn.setIcon(icon("recycle", self._theme.text, 13))
        opnieuw_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        opnieuw_btn.clicked.connect(self._genereer_zaagplannen)
        toolbar.addWidget(opnieuw_btn)
        layout.addLayout(toolbar)

        if self._zaagplan_waarschuwingen:
            waarschuwing = QLabel("\n".join(self._zaagplan_waarschuwingen))
            waarschuwing.setProperty("role", "warningText")
            waarschuwing.setWordWrap(True)
            layout.addWidget(waarschuwing)

        stat_row = QHBoxLayout()
        stat_row.setSpacing(10)
        aantal_materialen = len({p.materiaal_id for p in self._zaagplannen})
        gem_benutting = (
            sum(p.resultaat.benuttingspercentage for p in self._zaagplannen) / aantal if aantal else 0.0
        )
        niet_geplaatst_totaal = sum(len(p.resultaat.niet_geplaatst) for p in self._zaagplannen)
        stat_row.addWidget(StatTile("Platen", str(aantal), f"Over {aantal_materialen} materialen", "document", self._theme.accent_text, "neutral"))
        stat_row.addWidget(StatTile("Materialen", str(aantal_materialen), "In deze zaaglijst", "layers", self._theme.accent_text, "neutral"))
        stat_row.addWidget(
            StatTile(
                "Gem. benutting", f"{gem_benutting:.1f}%".replace(".", ","), "Gemiddeld over alle platen",
                "cube", self._theme.success_ink, "good",
            )
        )
        if niet_geplaatst_totaal:
            stat_row.addWidget(
                StatTile(
                    "Niet geplaatst", f"{niet_geplaatst_totaal} onderdelen", "Past niet op een lege plaat",
                    "warning", self._theme.warning_ink, "warn",
                )
            )
        else:
            stat_row.addWidget(
                StatTile("Niet geplaatst", "0 onderdelen", "Alles past op de gegenereerde platen", "check", self._theme.success_ink, "good")
            )
        layout.addLayout(stat_row)

        for plan in self._zaagplannen:
            layout.addWidget(self._bouw_zaagplan_document(plan))

        return wrapper

    def _bouw_zaagplan_document(self, plan: PlaatZaagplan) -> QWidget:
        kaart = QFrame()
        kaart.setObjectName("TableCard")
        layout = QVBoxLayout(kaart)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        head = QFrame()
        head.setObjectName("ZaagplanDocHead")
        head_layout = QHBoxLayout(head)
        head_layout.setContentsMargins(18, 12, 18, 12)
        head_layout.setSpacing(14)
        tag = QLabel("ZAAGPLAN")
        tag.setProperty("role", "docTag")
        head_layout.addWidget(tag)
        mat = plan.resultaat.materiaal
        naam_label = QLabel(plan.materiaal_naam)
        naam_label.setProperty("role", "docMetaStrong")
        head_layout.addWidget(naam_label)
        afmeting_label = QLabel(f"{mat.lengte:g} × {mat.breedte:g} mm")
        afmeting_label.setProperty("role", "docMeta")
        head_layout.addWidget(afmeting_label)
        if plan.platen_totaal > 1:
            plaat_label = QLabel(f"Plaat {plan.plaat_nummer} van {plan.platen_totaal}")
            plaat_label.setProperty("role", "docMeta")
            head_layout.addWidget(plaat_label)
        head_layout.addStretch(1)
        layout.addWidget(head)

        plate_wrap = QFrame()
        plate_wrap.setObjectName("ZaagplanPlateWrap")
        plate_layout = QVBoxLayout(plate_wrap)
        plate_layout.setContentsMargins(16, 16, 16, 10)
        plate_layout.addWidget(ZaagplaatWidget(plan.resultaat, plan.naam_voor, self._theme))
        layout.addWidget(plate_wrap)

        if plan.resultaat.niet_geplaatst:
            namen = ", ".join(sorted({plan.naam_voor(uid) for uid in plan.resultaat.niet_geplaatst}))
            waarschuwing = QLabel(f"⚠ Niet geplaatst: {namen}")
            waarschuwing.setProperty("role", "warningText")
            waarschuwing.setContentsMargins(16, 0, 16, 10)
            waarschuwing.setWordWrap(True)
            layout.addWidget(waarschuwing)

        layout.addWidget(self._bouw_onderdelen_tabel(plan))
        layout.addWidget(self._bouw_zaagplan_footer(plan))

        return kaart

    def _bouw_onderdelen_tabel(self, plan: PlaatZaagplan) -> QTableWidget:
        groepen: dict[str, list] = {}
        volgorde: list[str] = []
        for p in plan.resultaat.plaatsingen:
            if p.onderdeel_id not in groepen:
                groepen[p.onderdeel_id] = []
                volgorde.append(p.onderdeel_id)
            groepen[p.onderdeel_id].append(p)

        tabel = QTableWidget(len(volgorde), 5)
        tabel.setObjectName("LibraryTable")
        tabel.setHorizontalHeaderLabels(["Omschrijving", "Aantal", "Afmeting (mm)", "Kantenband", "Herkomst"])
        tabel.verticalHeader().setVisible(False)
        tabel.setShowGrid(False)
        tabel.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        tabel.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tabel.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Vaste rijhoogte (zelfde 56px-conventie als de bibliotheekschermen)
        # i.p.v. resizeRowsToContents(): dat laatste meet de sizeHint van de
        # cel-widgets vóórdat ze een keer echt gelayout zijn, wat een te
        # kleine tabelhoogte (en dus een scrollbalk) opleverde. Dit moet
        # altijd een statische tabel blijven, zonder interne scroll.
        tabel.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tabel.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        header = tabel.horizontalHeader()
        header.setStretchLastSection(True)
        for col, breedte in enumerate([260, 90, 140, 140]):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            tabel.setColumnWidth(col, breedte)

        rij_hoogte = 44
        for row, oid in enumerate(volgorde):
            tabel.setRowHeight(row, rij_hoogte)
            plaatsingen = groepen[oid]
            info = plan.onderdeel_info.get(oid)
            naam = info.naam if info else oid
            eerste = plaatsingen[0]
            if info and info.fabriekskantenband_vereist:
                kantenband = "Fabrieksrand"
            elif info and info.kantenband_randen:
                kantenband = ", ".join(sorted(r.value for r in info.kantenband_randen))
            else:
                kantenband = "—"
            herkomst = info.herkomst if info else "—"
            waarden = [naam, str(len(plaatsingen)), f"{eerste.breedte:g} × {eerste.hoogte:g}", kantenband]
            for col, tekst in enumerate(waarden):
                tabel.setCellWidget(row, col, self._cel_tekst(tekst))
            tabel.setCellWidget(row, 4, self._cel_herkomst(herkomst))

        aantal_rijen = max(1, len(volgorde))
        header_hoogte = header.sizeHint().height()
        tabel.setFixedHeight(header_hoogte + rij_hoogte * aantal_rijen + 4)

        # header.sizeHint() geeft hier (nog) de kale, ongestylede hoogte
        # terug -- de padding/border-bottom uit de QSS ("QTableWidget#
        # LibraryTable QHeaderView::section") wordt pas na een echte
        # style-polish meegerekend, wat pas gebeurt zodra deze tabel
        # daadwerkelijk in de zichtbare widgetboom hangt. Zonder correctie
        # bleef de vaste hoogte te krap, met een (onzichtbare, want
        # scrollbars staan uit) maar wél muiswiel-scrollbare tabel tot
        # gevolg. Zelfde uitgestelde-herberekening-patroon als de
        # stretch-kolom-fix in materialen_page.py.
        def _herstel_hoogte(tabel=tabel, aantal_rijen=aantal_rijen, rij_hoogte=rij_hoogte) -> None:
            echte_header_hoogte = tabel.horizontalHeader().height()
            tabel.setFixedHeight(echte_header_hoogte + rij_hoogte * aantal_rijen + 4)

        QTimer.singleShot(0, _herstel_hoogte)
        return tabel

    def _bouw_zaagplan_footer(self, plan: PlaatZaagplan) -> QFrame:
        footer = QFrame()
        footer.setObjectName("ZaagplanFooter")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        mat = plan.resultaat.materiaal
        cellen = [
            ("Materiaal", plan.materiaal_naam),
            ("Formaat", f"{mat.lengte:g} × {mat.breedte:g} mm"),
            ("Dikte", f"{mat.dikte:g} mm"),
            ("Kerf", f"{mat.kerf:g} mm"),
            ("Benutting", f"{plan.resultaat.benuttingspercentage:g}%".replace(".", ",")),
        ]
        for label, waarde in cellen:
            cel = QFrame()
            cel.setProperty("role", "footCell")
            cel_layout = QVBoxLayout(cel)
            cel_layout.setContentsMargins(14, 10, 14, 10)
            cel_layout.setSpacing(2)
            lbl = QLabel(label.upper())
            lbl.setProperty("role", "footLabel")
            cel_layout.addWidget(lbl)
            val = QLabel(waarde)
            val.setProperty("role", "footValue")
            cel_layout.addWidget(val)
            layout.addWidget(cel, 1)
        return footer

    def _build_placeholder_paneel(self, icon_naam: str, tag_tekst: str, titel: str, tekst: str) -> QWidget:
        kaart = QFrame()
        kaart.setObjectName("TableCard")
        layout = QVBoxLayout(kaart)
        layout.setContentsMargins(30, 60, 30, 60)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_box = QFrame()
        icon_box.setProperty("role", "rowIconBox")
        icon_box.setFixedSize(56, 56)
        icon_box_layout = QVBoxLayout(icon_box)
        icon_box_layout.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel()
        icon_label.setPixmap(icon_pixmap(icon_naam, self._theme.text_faint, 26))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("background: transparent;")
        icon_box_layout.addWidget(icon_label)
        layout.addWidget(icon_box, 0, Qt.AlignmentFlag.AlignHCenter)

        tag = QLabel(tag_tekst.upper())
        tag.setProperty("role", "tagChip")
        layout.addWidget(tag, 0, Qt.AlignmentFlag.AlignHCenter)

        titel_label = QLabel(titel)
        titel_label.setProperty("role", "placeholderTitle")
        titel_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(titel_label)

        tekst_label = QLabel(tekst)
        tekst_label.setProperty("role", "placeholderText")
        tekst_label.setWordWrap(True)
        tekst_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tekst_label.setMaximumWidth(440)
        layout.addWidget(tekst_label, 0, Qt.AlignmentFlag.AlignHCenter)

        return kaart

    # ------------------------------------------------------------------
    # Alles verversen (na het openen, en na een thema-wissel)
    # ------------------------------------------------------------------
    def _ververs_alles(self) -> None:
        self._ververs_head()
        self._ververs_overzicht_paneel()
        self._ververs_samenstelling()
        self._ververs_zaaglijst_paneel()
        self._ververs_zaagplannen_paneel()
