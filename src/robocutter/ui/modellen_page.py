"""Modellenbibliotheek-tabblad: de PySide6-uitwerking van de door Sven
goedgekeurde HTML-conceptmockup. Zijbalk met Mappen- en Tags-filters
(geen Overzicht/Archief — module 2 kent geen archiveerstap voor
modellen); hoofdgedeelte met zoeken, een sorteerbare/doorzoekbare
tabel, en een uitklapbaar paneel (geen pop-up) om een model toe te
voegen of te bewerken, mét de onderdelen- en submodellen-lijsten die
bij een model horen (hoofdstuk 2: nesting, materiaal per onderdeel).

Twee dingen die Sven na de mockup liet fixen tijdens het uitwerken
naar PySide6:
  1. De pijltjes van getalvelden (aantal, groepsvolgorde) gebruiken
     dezelfde eigen chevron-stapknoppen als Materialen/Reststukken
     i.p.v. Qt's/de browser's eigen omhoog/omlaag-pijltjes — die
     tekenen niet betrouwbaar zodra een veld een eigen stylesheet
     krijgt (zelfde bug als bij de QDoubleSpinBox's eerder).
  2. De headernavigatie noemde dit onderdeel "Modellen" i.p.v.
     "Modellenbibliotheek", terwijl Materialenbibliotheek en
     Reststukkenbibliotheek wél de volledige naam gebruiken — dat is
     rechtgezet in ``main_window.py``.

Deelt de ``MaterialenBibliotheek``-instantie van ``MaterialenPage``
(zie ``main_window.py``) i.p.v. een eigen materialen-verbinding te
openen. Modellen krijgen wél hun eigen SQLite-opslag
(``robocutter.modellen.opslag``, zelfde ``data/robocutter.db``-bestand,
eigen tabel).
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QEvent, QSize, Qt, QStringListModel, QTimer
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QCompleter,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.materialen.models import MateriaalStatus
from robocutter.modellen.bibliotheek import ModelInGebruikError, ModellenBibliotheek, valideer
from robocutter.modellen.models import Model, ModelOnderdeel, Nerfrichting, Rand, SubModelVerwijzing
from robocutter.modellen.opslag import open_verbinding
from robocutter.ui.icons import icon, icon_pixmap
from robocutter.ui.theme import Theme

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DB_PAD = _REPO_ROOT / "data" / "robocutter.db"

_NERF_LABEL = {
    Nerfrichting.GEEN: "Geen",
    Nerfrichting.LANGE_ZIJDE: "Lange zijde",
    Nerfrichting.KORTE_ZIJDE: "Korte zijde",
}
_RAND_LABEL = {Rand.BOVEN: "Boven", Rand.ONDER: "Onder", Rand.LINKS: "Links", Rand.RECHTS: "Rechts"}
_KOLOMBREEDTES = [230, 150, 110, 150, 160, 90]
_SORT_OPTIES = [("naam", "Sorteren op naam"), ("map", "Sorteren op map")]
_DRAWER_BREEDTE = 480
_MODEL_KOLOM_MIN = 200


def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
        elif item.layout() is not None:
            _clear_layout(item.layout())


class ModellenPage(QWidget):
    def __init__(self, materialen: MaterialenBibliotheek, theme: Theme, parent=None) -> None:
        super().__init__(parent)
        self._theme = theme
        self.materialen = materialen

        _DB_PAD.parent.mkdir(parents=True, exist_ok=True)
        self._db = open_verbinding(_DB_PAD)
        self.bibliotheek = ModellenBibliotheek(materialen, self._db)

        self._map_filter: str | None = None
        self._tag_filter: str | None = None
        self._zoekterm = ""
        self._sort = "naam"
        self._confirm_delete_id: str | None = None
        self._alle_mappen_tonen = False
        self._alle_tags_tonen = False
        self._bewerk_id: str | None = None
        self._werk_onderdelen: list[ModelOnderdeel] = []
        self._werk_submodellen: list[SubModelVerwijzing] = []
        self._bewerk_onderdeel_index: int | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._sidebar = self._build_sidebar()
        self._main = self._build_main()
        self._drawer = self._build_drawer()
        layout.addWidget(self._sidebar)
        layout.addWidget(self._main, 1)
        layout.addWidget(self._drawer)
        self._drawer.hide()

        self._ververs_alles()

    # ------------------------------------------------------------------
    # Thema: zelfde aanpak als MaterialenPage/ReststukkenPage — bewuste
    # volledige herbouw, alleen bij een expliciete thema-wissel.
    # ------------------------------------------------------------------
    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        layout = self.layout()
        _clear_layout(layout)
        self._sidebar = self._build_sidebar()
        self._main = self._build_main()
        self._drawer = self._build_drawer()
        layout.addWidget(self._sidebar)
        layout.addWidget(self._main, 1)
        layout.addWidget(self._drawer)
        self._drawer.hide()
        self._ververs_alles()

    def sluit_verbinding(self) -> None:
        self._db.close()

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

        layout.addWidget(self._sidebar_label("Modellenbibliotheek"))
        layout.addWidget(self._divider())

        layout.addWidget(self._sidebar_label("Mappen"))
        self._map_container = QVBoxLayout()
        self._map_container.setSpacing(2)
        layout.addLayout(self._map_container)
        self._btn_mappen_meer = QPushButton("")
        self._btn_mappen_meer.setProperty("role", "sortControl")
        self._btn_mappen_meer.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_mappen_meer.clicked.connect(self._toggle_alle_mappen)
        layout.addWidget(self._btn_mappen_meer)
        layout.addWidget(self._divider())

        layout.addWidget(self._sidebar_label("Tags"))
        self._tag_container = QVBoxLayout()
        self._tag_container.setSpacing(2)
        layout.addLayout(self._tag_container)
        self._btn_tags_meer = QPushButton("")
        self._btn_tags_meer.setProperty("role", "sortControl")
        self._btn_tags_meer.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_tags_meer.clicked.connect(self._toggle_alle_tags)
        layout.addWidget(self._btn_tags_meer)
        layout.addWidget(self._divider())

        layout.addWidget(self._sidebar_label("Snelacties"))
        add_action = self._sidebar_item("plus", "Model toevoegen")
        add_action.clicked.connect(lambda: self._open_drawer())
        layout.addWidget(add_action)

        layout.addStretch(1)
        return sidebar

    def _sidebar_label(self, text: str) -> QLabel:
        label = QLabel(text.upper())
        label.setProperty("role", "sidebarLabel")
        label.setContentsMargins(8, 4, 8, 4)
        return label

    def _sidebar_item(self, icon_name: str, text: str) -> QPushButton:
        button = QPushButton(f"  {text}")
        button.setProperty("role", "sidebarItem")
        button.setIcon(icon(icon_name, self._theme.text_muted, 16))
        button.setIconSize(QSize(16, 16))
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def _divider(self) -> QFrame:
        line = QFrame()
        line.setObjectName("SidebarDivider")
        line.setFixedHeight(1)
        line.setContentsMargins(0, 8, 0, 12)
        return line

    def _toggle_alle_mappen(self) -> None:
        self._alle_mappen_tonen = not self._alle_mappen_tonen
        self._ververs_sidebar()

    def _toggle_alle_tags(self) -> None:
        self._alle_tags_tonen = not self._alle_tags_tonen
        self._ververs_sidebar()

    def _zet_map_filter(self, waarde: str) -> None:
        self._map_filter = None if self._map_filter == waarde else waarde
        self._ververs_alles()

    def _zet_tag_filter(self, waarde: str) -> None:
        self._tag_filter = None if self._tag_filter == waarde else waarde
        self._ververs_alles()

    # ------------------------------------------------------------------
    # Hoofdgedeelte
    # ------------------------------------------------------------------
    def _build_main(self) -> QWidget:
        main = QWidget()
        main.setObjectName("MainScrollContent")
        layout = QVBoxLayout(main)
        layout.setContentsMargins(28, 22, 28, 20)
        layout.setSpacing(14)

        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(3)
        title = QLabel("Modellenbibliotheek")
        title.setObjectName("PageTitle")
        titles.addWidget(title)
        self._page_sub = QLabel("")
        self._page_sub.setObjectName("PageSub")
        titles.addWidget(self._page_sub)
        head.addLayout(titles)
        head.addStretch(1)

        self._search = QLineEdit()
        self._search.setObjectName("SearchInput")
        self._search.setPlaceholderText('Zoek op naam, omschrijving, map of tag, bijv. "keuken onderkast"')
        self._search.setFixedWidth(280)
        self._search.addAction(icon("search", self._theme.text_faint, 15), QLineEdit.ActionPosition.LeadingPosition)
        self._search.setText(self._zoekterm)
        self._search.textChanged.connect(self._zoekterm_gewijzigd)
        head.addWidget(self._search)

        add_btn = QPushButton("  Model toevoegen")
        add_btn.setProperty("role", "primary")
        add_btn.setIcon(icon("plus", "#12141B", 14))
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(lambda: self._open_drawer())
        head.addWidget(add_btn)
        layout.addLayout(head)

        toolbar = QHBoxLayout()
        toolbar.addStretch(1)
        self._sort_btn = QPushButton()
        self._sort_btn.setProperty("role", "sortControl")
        self._sort_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sort_btn.setIcon(icon("chevron-down", self._theme.text_muted, 11))
        self._sort_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._sort_btn.clicked.connect(self._volgende_sortering)
        toolbar.addWidget(self._sort_btn)
        layout.addLayout(toolbar)

        table_card = QFrame()
        table_card.setObjectName("TableCard")
        card_layout = QVBoxLayout(table_card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        self._table = QTableWidget(0, 6)
        self._table.setObjectName("LibraryTable")
        self._table.setHorizontalHeaderLabels(["Model", "Map", "Onderdelen", "Submodellen", "Tags", ""])
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Zelfde reden als in materialen_page.py: Interactive overal + de
        # Model-kolom zelf herberekenen i.p.v. Stretch, anders knijpt de
        # tabel die kolom tot onleesbaar smal zodra het paneel rechts
        # openstaat.
        header = self._table.horizontalHeader()
        header.setStretchLastSection(False)
        for col, breedte in enumerate(_KOLOMBREEDTES):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            self._table.setColumnWidth(col, breedte)
        self._table.installEventFilter(self)
        card_layout.addWidget(self._table)

        self._empty_label = QLabel("Geen modellen gevonden voor deze zoekopdracht/filter.")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(f"color: {self._theme.text_faint}; font-size: 13px; padding: 48px 0;")
        self._empty_label.hide()
        card_layout.addWidget(self._empty_label)

        layout.addWidget(table_card, 1)
        return main

    def _zoekterm_gewijzigd(self, tekst: str) -> None:
        self._zoekterm = tekst
        self._ververs_tabel()

    def _volgende_sortering(self) -> None:
        idx = [key for key, _ in _SORT_OPTIES].index(self._sort)
        self._sort = _SORT_OPTIES[(idx + 1) % len(_SORT_OPTIES)][0]
        self._ververs_tabel()

    # ------------------------------------------------------------------
    # Verversen (in-place, geen volledige herbouw — behoudt focus/scroll)
    # ------------------------------------------------------------------
    def _ververs_alles(self) -> None:
        self._ververs_sidebar()
        self._ververs_tabel()

    def _ververs_sidebar(self) -> None:
        alles = self.bibliotheek.lijst()
        totaal_onderdelen = sum(len(m.onderdelen) for m in alles)
        totaal_nesting = sum(len(m.submodellen) for m in alles)
        self._page_sub.setText(
            f"{len(alles)} modellen · {totaal_onderdelen} onderdelen · {totaal_nesting} nesting-koppelingen"
        )

        map_counts: dict[str, int] = {}
        for m in alles:
            if m.map:
                map_counts[m.map] = map_counts.get(m.map, 0) + 1
        self._render_filter_lijst(
            self._map_container, map_counts, self._map_filter, self._btn_mappen_meer,
            self._alle_mappen_tonen, self._zet_map_filter, "mappen",
        )

        tag_counts: dict[str, int] = {}
        for m in alles:
            for tag in m.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        self._render_filter_lijst(
            self._tag_container, tag_counts, self._tag_filter, self._btn_tags_meer,
            self._alle_tags_tonen, self._zet_tag_filter, "tags",
        )

    def _render_filter_lijst(self, container, counts, actieve_waarde, meer_knop, alle_tonen, on_click, meervoud: str) -> None:
        namen = sorted(counts, key=lambda n: (-counts[n], n.lower()))
        zichtbaar = namen if alle_tonen else namen[:6]
        rest = len(namen) - len(zichtbaar)

        _clear_layout(container)
        for naam in zichtbaar:
            row = QPushButton()
            row.setProperty("role", "sidebarItem")
            row.setCursor(Qt.CursorShape.PointingHandCursor)
            actief = actieve_waarde == naam
            row.setStyleSheet(
                f"QPushButton {{ background: {self._theme.accent_soft if actief else 'transparent'}; "
                f"color: {self._theme.accent_text if actief else self._theme.text_muted}; "
                f"border: none; border-radius: 7px; padding: 5px 8px; text-align: left; font-size: 12.5px; }}"
                f"QPushButton:hover {{ background: {self._theme.surface_hover}; }}"
            )
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            label = QLabel(naam)
            label_kleur = self._theme.accent_text if actief else self._theme.text_muted
            label.setStyleSheet(f"background: transparent; color: {label_kleur};")
            row_layout.addWidget(label, 1)
            count_label = QLabel(str(counts[naam]))
            count_label.setProperty("role", "filterCount")
            row_layout.addWidget(count_label)
            row.clicked.connect(lambda checked=False, n=naam: on_click(n))
            container.addWidget(row)

        if rest > 0:
            meer_knop.setText(f"+ {rest} andere {meervoud}" if not alle_tonen else f"Toon minder {meervoud}")
            meer_knop.show()
        else:
            meer_knop.hide()

    def _zichtbare_rijen(self) -> list[Model]:
        rijen = self.bibliotheek.lijst(zoekterm=self._zoekterm)
        if self._map_filter:
            rijen = [m for m in rijen if m.map == self._map_filter]
        if self._tag_filter:
            rijen = [m for m in rijen if self._tag_filter in m.tags]
        if self._sort == "map":
            rijen.sort(key=lambda m: (m.map.lower(), m.naam.lower()))
        return rijen

    def eventFilter(self, obj, event) -> bool:
        if obj is self._table and event.type() == QEvent.Type.Resize:
            QTimer.singleShot(0, self._herbereken_model_kolom)
        return super().eventFilter(obj, event)

    def _herbereken_model_kolom(self) -> None:
        andere_kolommen_breedte = sum(_KOLOMBREEDTES[1:])
        beschikbaar = self._table.viewport().width() - andere_kolommen_breedte
        self._table.setColumnWidth(0, max(_MODEL_KOLOM_MIN, beschikbaar))

    def _ververs_tabel(self) -> None:
        label, _ = next(o for o in _SORT_OPTIES if o[0] == self._sort)
        self._sort_btn.setText(label)

        rijen = self._zichtbare_rijen()
        self._table.clearContents()
        self._table.setRowCount(len(rijen))
        self._table.setVisible(bool(rijen))
        self._empty_label.setVisible(not rijen)

        for row_index, model in enumerate(rijen):
            self._table.setRowHeight(row_index, 56)
            self._table.setCellWidget(row_index, 0, self._cel_model(model))
            self._table.setCellWidget(row_index, 1, self._cel_map(model))
            self._table.setCellWidget(row_index, 2, self._cel_onderdelen(model))
            self._table.setCellWidget(row_index, 3, self._cel_submodellen(model))
            self._table.setCellWidget(row_index, 4, self._cel_tags(model))
            self._table.setCellWidget(row_index, 5, self._cel_acties(model))

    def _cel_model(self, m: Model) -> QWidget:
        cell = QWidget()
        layout = QVBoxLayout(cell)
        layout.setContentsMargins(10, 4, 4, 4)
        layout.setSpacing(2)
        naam = QLabel(m.naam)
        naam.setProperty("role", "matName")
        layout.addWidget(naam)
        omschrijving = QLabel(m.omschrijving if m.omschrijving else "—")
        omschrijving.setProperty("role", "matMeta" if m.omschrijving else "tagEmpty")
        omschrijving.setWordWrap(False)
        layout.addWidget(omschrijving)
        return cell

    def _cel_map(self, m: Model) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)
        if m.map:
            icon_label = QLabel()
            icon_label.setPixmap(icon_pixmap("folder", self._theme.text_faint, 14))
            layout.addWidget(icon_label)
            text = QLabel(m.map)
            text.setProperty("role", "matMeta")
        else:
            text = QLabel("—")
            text.setProperty("role", "tagEmpty")
        layout.addWidget(text)
        layout.addStretch(1)
        return cell

    def _cel_onderdelen(self, m: Model) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(4, 4, 4, 4)
        aantal = len(m.onderdelen)
        label = QLabel(f"{aantal} onderdeel" if aantal == 1 else f"{aantal} onderdelen")
        label.setProperty("role", "countPill")
        layout.addWidget(label)
        layout.addStretch(1)
        return cell

    def _cel_submodellen(self, m: Model) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(4, 4, 4, 4)
        if m.submodellen:
            totaal = sum(s.aantal for s in m.submodellen)
            tekst = f"{len(m.submodellen)} model" if len(m.submodellen) == 1 else f"{len(m.submodellen)} modellen"
            label = QLabel(f"{tekst} ({totaal}x)")
            label.setProperty("role", "nestingPill")
        else:
            label = QLabel("—")
            label.setProperty("role", "tagEmpty")
        layout.addWidget(label)
        layout.addStretch(1)
        return cell

    def _cel_tags(self, m: Model) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        if m.tags:
            for tag in m.tags[:2]:
                chip = QLabel(tag)
                chip.setProperty("role", "tagChip")
                layout.addWidget(chip)
            if len(m.tags) > 2:
                meer = QLabel(f"+{len(m.tags) - 2}")
                meer.setProperty("role", "tagEmpty")
                layout.addWidget(meer)
        else:
            empty = QLabel("—")
            empty.setProperty("role", "tagEmpty")
            layout.addWidget(empty)
        layout.addStretch(1)
        return cell

    def _model_wordt_gebruikt_door(self, model_id: str) -> Model | None:
        for ander in self.bibliotheek.lijst():
            if ander.id != model_id and any(s.model_id == model_id for s in ander.submodellen):
                return ander
        return None

    def _cel_acties(self, m: Model) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(1)

        edit_btn = QToolButton()
        edit_btn.setProperty("role", "rowAction")
        edit_btn.setIcon(icon("pencil", self._theme.text_faint, 15))
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setToolTip("Bewerken")
        edit_btn.clicked.connect(lambda: self._open_drawer(m.id))
        layout.addWidget(edit_btn)

        if self._confirm_delete_id == m.id:
            gebruiker = self._model_wordt_gebruikt_door(m.id)
            if gebruiker is not None:
                warn = QLabel(f"In gebruik in '{gebruiker.naam}'")
                warn.setProperty("role", "inUseWarning")
                warn.setWordWrap(False)
                layout.addWidget(warn)
                ok_btn = QToolButton()
                ok_btn.setProperty("role", "confirmNo")
                ok_btn.setIcon(icon("close", self._theme.text_muted, 11))
                ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                ok_btn.clicked.connect(self._annuleer_verwijderen)
                layout.addWidget(ok_btn)
            else:
                label = QLabel("Verwijderen?")
                label.setProperty("role", "confirmDeleteLabel")
                layout.addWidget(label)
                yes_btn = QToolButton()
                yes_btn.setProperty("role", "confirmYes")
                yes_btn.setIcon(icon("check", "#FFFFFF", 11))
                yes_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                yes_btn.clicked.connect(lambda: self._verwijderen(m.id))
                layout.addWidget(yes_btn)
                no_btn = QToolButton()
                no_btn.setProperty("role", "confirmNo")
                no_btn.setIcon(icon("close", self._theme.text_muted, 11))
                no_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                no_btn.clicked.connect(self._annuleer_verwijderen)
                layout.addWidget(no_btn)
        else:
            delete_btn = QToolButton()
            delete_btn.setProperty("role", "rowActionDanger")
            delete_btn.setIcon(icon("trash", self._theme.text_faint, 15))
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.setToolTip("Verwijderen")
            delete_btn.clicked.connect(lambda: self._vraag_verwijder_bevestiging(m.id))
            layout.addWidget(delete_btn)

        layout.addStretch(1)
        return cell

    # ------------------------------------------------------------------
    # Verwijderen
    # ------------------------------------------------------------------
    def _vraag_verwijder_bevestiging(self, model_id: str) -> None:
        self._confirm_delete_id = model_id
        self._ververs_tabel()

    def _annuleer_verwijderen(self) -> None:
        self._confirm_delete_id = None
        self._ververs_tabel()

    def _verwijderen(self, model_id: str) -> None:
        try:
            self.bibliotheek.verwijderen(model_id)
        except ModelInGebruikError:
            pass
        self._confirm_delete_id = None
        self._ververs_alles()

    # ------------------------------------------------------------------
    # Gedeelde veld-helpers (zelfde patroon als materialen_page.py)
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
        # Zelfde reden als materialen_page.py::_field_spin: Qt's eigen
        # omhoog/omlaag-pijltjes tekenen niet betrouwbaar zodra het veld
        # een eigen stylesheet krijgt (rendert als een dichtgekleurd
        # blokje i.p.v. een driehoek) — vandaar een eigen stap-
        # knoppenkolom met hetzelfde chevron-icoon als de rest van de UI.
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
            btn = QPushButton(_RAND_LABEL[rand])
            btn.setProperty("role", "chipToggle")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            row.addWidget(btn)
            buttons[rand] = btn
        row.addStretch(1)
        section.addLayout(row)
        return buttons

    # ------------------------------------------------------------------
    # Toevoegen/bewerken-paneel (drawer)
    # ------------------------------------------------------------------
    def _build_drawer(self) -> QFrame:
        drawer = QFrame()
        drawer.setObjectName("Drawer")
        drawer.setFixedWidth(_DRAWER_BREEDTE)
        outer = QVBoxLayout(drawer)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        head = QHBoxLayout()
        head.setContentsMargins(18, 16, 12, 16)
        self._drawer_title = QLabel("Nieuw model")
        self._drawer_title.setObjectName("DrawerTitle")
        head.addWidget(self._drawer_title, 1)
        close_btn = QToolButton()
        close_btn.setProperty("role", "rowAction")
        close_btn.setIcon(icon("close", self._theme.text_faint, 16))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self._sluit_drawer)
        head.addWidget(close_btn)
        head_widget = QWidget()
        head_widget.setLayout(head)
        outer.addWidget(head_widget)

        self._validation_banner = QFrame()
        self._validation_banner.setObjectName("ValidationBanner")
        banner_layout = QVBoxLayout(self._validation_banner)
        banner_layout.setContentsMargins(12, 10, 12, 10)
        self._validation_label = QLabel("")
        self._validation_label.setProperty("role", "validationText")
        self._validation_label.setWordWrap(True)
        banner_layout.addWidget(self._validation_label)
        self._validation_banner.hide()
        banner_wrap = QWidget()
        banner_wrap_layout = QVBoxLayout(banner_wrap)
        banner_wrap_layout.setContentsMargins(18, 0, 18, 12)
        banner_wrap_layout.addWidget(self._validation_banner)
        outer.addWidget(banner_wrap)

        scroll = QScrollArea()
        scroll.setObjectName("DrawerScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        body.setObjectName("DrawerBody")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(18, 0, 18, 12)
        body_layout.setSpacing(22)
        body_layout.addLayout(self._build_basisgegevens_sectie())
        body_layout.addLayout(self._build_onderdelen_sectie())
        body_layout.addLayout(self._build_submodellen_sectie())
        body_layout.addStretch(1)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        footer = QHBoxLayout()
        footer.setContentsMargins(18, 14, 18, 14)
        cancel_btn = QPushButton("Annuleren")
        cancel_btn.setProperty("role", "ghost")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self._sluit_drawer)
        footer.addWidget(cancel_btn)
        footer.addStretch(1)
        save_btn = QPushButton("Model opslaan")
        save_btn.setProperty("role", "primary")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._opslaan)
        footer.addWidget(save_btn)
        footer_widget = QWidget()
        footer_widget.setLayout(footer)
        outer.addWidget(footer_widget)

        return drawer

    def _build_basisgegevens_sectie(self) -> QVBoxLayout:
        section = QVBoxLayout()
        section.setSpacing(10)
        label = QLabel("BASISGEGEVENS")
        label.setProperty("role", "fieldSectionLabel")
        section.addWidget(label)

        section.addWidget(self._field_label("Naam"))
        self._in_naam = self._field_input()
        self._in_naam.setPlaceholderText("bijv. Onderkast 60cm")
        section.addWidget(self._in_naam)

        section.addWidget(self._field_label("Omschrijving"))
        self._in_omschrijving = self._field_input()
        self._in_omschrijving.setPlaceholderText("Korte omschrijving voor in de bibliotheek")
        section.addWidget(self._in_omschrijving)

        section.addWidget(self._field_label("Map"))
        self._in_map = self._field_input()
        self._in_map.setPlaceholderText("bijv. Keukens/Onderkasten")
        self._map_completer = QCompleter([])
        self._map_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._in_map.setCompleter(self._map_completer)
        section.addWidget(self._in_map)
        map_hint = QLabel("Vrije mapstructuur, alleen voor overzicht/filteren.")
        map_hint.setProperty("role", "fieldHint")
        map_hint.setWordWrap(True)
        section.addWidget(map_hint)

        section.addWidget(self._field_label("Tags"))
        self._in_tags = self._field_input()
        self._in_tags.setPlaceholderText("komma-gescheiden")
        section.addWidget(self._in_tags)

        return section

    def _build_onderdelen_sectie(self) -> QVBoxLayout:
        section = QVBoxLayout()
        section.setSpacing(10)
        self._onderdelen_label = QLabel("ONDERDELEN (0)")
        self._onderdelen_label.setProperty("role", "fieldSectionLabel")
        section.addWidget(self._onderdelen_label)

        self._onderdelen_container = QVBoxLayout()
        self._onderdelen_container.setSpacing(6)
        section.addLayout(self._onderdelen_container)

        self._onderdeel_form_titel = self._field_label("Onderdeel toevoegen")
        section.addWidget(self._onderdeel_form_titel)

        rij1 = QHBoxLayout()
        rij1.setSpacing(8)
        kol1 = QVBoxLayout()
        kol1.addWidget(self._field_label("Naam"))
        self._of_naam = self._field_input()
        self._of_naam.setPlaceholderText("bijv. Zijkant links")
        kol1.addWidget(self._of_naam)
        rij1.addLayout(kol1, 1)
        kol2 = QVBoxLayout()
        kol2.addWidget(self._field_label("Materiaal"))
        self._of_materiaal = QComboBox()
        self._of_materiaal.setProperty("role", "field")
        kol2.addWidget(self._of_materiaal)
        rij1.addLayout(kol2, 1)
        section.addLayout(rij1)

        rij2 = QHBoxLayout()
        rij2.setSpacing(8)
        kol3 = QVBoxLayout()
        kol3.addWidget(self._field_label("Breedte (mm)"))
        breedte_wrap, self._of_breedte = self._field_spin()
        kol3.addWidget(breedte_wrap)
        rij2.addLayout(kol3)
        kol4 = QVBoxLayout()
        kol4.addWidget(self._field_label("Hoogte (mm)"))
        hoogte_wrap, self._of_hoogte = self._field_spin()
        kol4.addWidget(hoogte_wrap)
        rij2.addLayout(kol4)
        kol5 = QVBoxLayout()
        kol5.addWidget(self._field_label("Aantal"))
        aantal_wrap, self._of_aantal = self._field_spin_int(minimum=1, maximum=1000)
        kol5.addWidget(aantal_wrap)
        rij2.addLayout(kol5)
        section.addLayout(rij2)

        section.addWidget(self._field_label("Nerfrichting"))
        nerf_widget, self._of_nerf_group = self._segmented(
            [(Nerfrichting.GEEN, "Geen"), (Nerfrichting.LANGE_ZIJDE, "Lange zijde"), (Nerfrichting.KORTE_ZIJDE, "Korte zijde")]
        )
        section.addWidget(nerf_widget)

        section.addWidget(self._field_label("Kantenband op"))
        self._of_rand_buttons = self._rand_chip_rij(section)

        self._of_fabriek = QCheckBox("Fabriekskantenband vereist")
        section.addWidget(self._of_fabriek)

        rij3 = QHBoxLayout()
        rij3.setSpacing(8)
        kol6 = QVBoxLayout()
        kol6.addWidget(self._field_label("Groepsnaam"))
        self._of_groep_naam = self._field_input()
        self._of_groep_naam.setPlaceholderText("optioneel — leeg = geen groep")
        kol6.addWidget(self._of_groep_naam)
        rij3.addLayout(kol6, 1)
        kol7 = QVBoxLayout()
        kol7.addWidget(self._field_label("Volgorde"))
        groep_volgorde_wrap, self._of_groep_volgorde = self._field_spin_int(minimum=0, maximum=1000)
        kol7.addWidget(groep_volgorde_wrap)
        rij3.addLayout(kol7)
        section.addLayout(rij3)
        groep_hint = QLabel(
            "Onderdelen met dezelfde groepsnaam blijven in vaste volgorde en roteren niet los van "
            "elkaar — bijv. laatjes die precies op elkaar moeten aansluiten."
        )
        groep_hint.setProperty("role", "fieldHint")
        groep_hint.setWordWrap(True)
        section.addWidget(groep_hint)

        knoppen_rij = QHBoxLayout()
        knoppen_rij.addStretch(1)
        self._btn_onderdeel_annuleren = QPushButton("Annuleren")
        self._btn_onderdeel_annuleren.setProperty("role", "ghost")
        self._btn_onderdeel_annuleren.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_onderdeel_annuleren.clicked.connect(self._reset_onderdeel_form)
        self._btn_onderdeel_annuleren.hide()
        knoppen_rij.addWidget(self._btn_onderdeel_annuleren)
        self._btn_onderdeel_opslaan = QPushButton("  Onderdeel toevoegen")
        self._btn_onderdeel_opslaan.setProperty("role", "ghost")
        self._btn_onderdeel_opslaan.setIcon(icon("plus", self._theme.text, 12))
        self._btn_onderdeel_opslaan.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_onderdeel_opslaan.clicked.connect(self._onderdeel_opslaan_klik)
        knoppen_rij.addWidget(self._btn_onderdeel_opslaan)
        section.addLayout(knoppen_rij)

        return section

    def _build_submodellen_sectie(self) -> QVBoxLayout:
        section = QVBoxLayout()
        section.setSpacing(10)
        self._submodellen_label = QLabel("SUBMODELLEN, NESTING (0)")
        self._submodellen_label.setProperty("role", "fieldSectionLabel")
        section.addWidget(self._submodellen_label)

        self._submodellen_container = QVBoxLayout()
        self._submodellen_container.setSpacing(6)
        section.addLayout(self._submodellen_container)

        add_rij = QHBoxLayout()
        add_rij.setSpacing(8)
        self._sm_select = QComboBox()
        self._sm_select.setProperty("role", "field")
        add_rij.addWidget(self._sm_select, 1)
        sm_aantal_wrap, self._sm_aantal = self._field_spin_int(minimum=1, maximum=1000)
        sm_aantal_wrap.setMaximumWidth(90)
        add_rij.addWidget(sm_aantal_wrap)
        btn_sm_add = QPushButton("+ Toevoegen")
        btn_sm_add.setProperty("role", "ghost")
        btn_sm_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sm_add.clicked.connect(self._submodel_toevoegen)
        add_rij.addWidget(btn_sm_add)
        section.addLayout(add_rij)

        hint = QLabel(
            "Modellen die dit model al (indirect) bevatten staan uitgeschakeld in de lijst — "
            "dat zou een cirkelverwijzing veroorzaken."
        )
        hint.setProperty("role", "fieldHint")
        hint.setWordWrap(True)
        section.addWidget(hint)

        return section

    # ------------------------------------------------------------------
    # Onderdelen-lijst en -formulier
    # ------------------------------------------------------------------
    def _ververs_materiaal_combo_onderdeel(self) -> None:
        huidige = self._of_materiaal.currentData()
        self._of_materiaal.clear()
        for materiaal in sorted(self.materialen.lijst(), key=lambda m: m.naam.lower()):
            label = f"{materiaal.naam} ({materiaal.type.value})"
            if materiaal.status != MateriaalStatus.ACTIEF:
                label += ", gearchiveerd"
            self._of_materiaal.addItem(label, materiaal.id)
        idx = self._of_materiaal.findData(huidige)
        if idx >= 0:
            self._of_materiaal.setCurrentIndex(idx)

    def _ververs_onderdelen(self) -> None:
        self._onderdelen_label.setText(f"ONDERDELEN ({len(self._werk_onderdelen)})")
        _clear_layout(self._onderdelen_container)
        for index, onderdeel in enumerate(self._werk_onderdelen):
            self._onderdelen_container.addWidget(self._bouw_onderdeel_rij(onderdeel, index))

    def _bouw_onderdeel_rij(self, o: ModelOnderdeel, index: int) -> QWidget:
        row = QFrame()
        row.setProperty("role", "subRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 7, 8, 7)
        layout.setSpacing(8)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        titel_tekst = o.naam + (f"  ×{o.aantal}" if o.aantal > 1 else "")
        titel = QLabel(titel_tekst)
        titel.setProperty("role", "matName")
        info_col.addWidget(titel)

        try:
            materiaal_naam = self.materialen.ophalen(o.materiaal_id).naam
        except KeyError:
            materiaal_naam = "onbekend materiaal"
        details = [f"{o.breedte:g}×{o.hoogte:g} mm", materiaal_naam]
        if o.nerfrichting_vereist != Nerfrichting.GEEN:
            details.append(_NERF_LABEL[o.nerfrichting_vereist].lower())
        if o.kantenband_randen:
            randen_tekst = ", ".join(_RAND_LABEL[r].lower() for r in sorted(o.kantenband_randen, key=lambda r: r.value))
            details.append(f"kantenband {randen_tekst}")
        detail = QLabel(" · ".join(details))
        detail.setProperty("role", "matMeta")
        detail.setWordWrap(False)
        info_col.addWidget(detail)

        if o.groep_id:
            badge = QLabel(f"Groep: {o.groep_id} · #{o.groep_volgorde}")
            badge.setProperty("role", "tagChip")
            badge_row = QHBoxLayout()
            badge_row.setContentsMargins(0, 0, 0, 0)
            badge_row.addWidget(badge)
            badge_row.addStretch(1)
            info_col.addLayout(badge_row)

        layout.addLayout(info_col, 1)

        edit_btn = QToolButton()
        edit_btn.setProperty("role", "rowAction")
        edit_btn.setIcon(icon("pencil", self._theme.text_faint, 14))
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.clicked.connect(lambda: self._bewerk_onderdeel(index))
        layout.addWidget(edit_btn)

        del_btn = QToolButton()
        del_btn.setProperty("role", "rowActionDanger")
        del_btn.setIcon(icon("trash", self._theme.text_faint, 14))
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.clicked.connect(lambda: self._verwijder_onderdeel(index))
        layout.addWidget(del_btn)

        return row

    def _reset_onderdeel_form(self) -> None:
        self._bewerk_onderdeel_index = None
        self._onderdeel_form_titel.setText("Onderdeel toevoegen")
        self._btn_onderdeel_opslaan.setText("  Onderdeel toevoegen")
        self._btn_onderdeel_annuleren.hide()
        self._of_naam.clear()
        self._ververs_materiaal_combo_onderdeel()
        self._of_materiaal.setCurrentIndex(0 if self._of_materiaal.count() else -1)
        self._of_breedte.setValue(0)
        self._of_hoogte.setValue(0)
        self._of_aantal.setValue(1)
        self._of_nerf_group.buttons()[0].setChecked(True)
        for btn in self._of_rand_buttons.values():
            btn.setChecked(False)
        self._of_fabriek.setChecked(False)
        self._of_groep_naam.clear()
        self._of_groep_volgorde.setValue(0)

    def _vul_onderdeel_form(self, o: ModelOnderdeel) -> None:
        self._of_naam.setText(o.naam)
        self._ververs_materiaal_combo_onderdeel()
        idx = self._of_materiaal.findData(o.materiaal_id)
        if idx >= 0:
            self._of_materiaal.setCurrentIndex(idx)
        self._of_breedte.setValue(o.breedte)
        self._of_hoogte.setValue(o.hoogte)
        self._of_aantal.setValue(o.aantal)
        for btn in self._of_nerf_group.buttons():
            btn.setChecked(btn.property("waarde") == o.nerfrichting_vereist)
        for rand, btn in self._of_rand_buttons.items():
            btn.setChecked(rand in o.kantenband_randen)
        self._of_fabriek.setChecked(o.fabriekskantenband_vereist)
        self._of_groep_naam.setText(o.groep_id or "")
        self._of_groep_volgorde.setValue(o.groep_volgorde or 0)

    def _bewerk_onderdeel(self, index: int) -> None:
        self._bewerk_onderdeel_index = index
        o = self._werk_onderdelen[index]
        self._onderdeel_form_titel.setText(f"Onderdeel bewerken: {o.naam}")
        self._btn_onderdeel_opslaan.setText("  Wijzigingen opslaan")
        self._btn_onderdeel_annuleren.show()
        self._vul_onderdeel_form(o)

    def _verwijder_onderdeel(self, index: int) -> None:
        del self._werk_onderdelen[index]
        if self._bewerk_onderdeel_index == index:
            self._reset_onderdeel_form()
        self._ververs_onderdelen()

    def _onderdeel_uit_formulier(self) -> ModelOnderdeel:
        huidig_id = ""
        if self._bewerk_onderdeel_index is not None:
            huidig_id = self._werk_onderdelen[self._bewerk_onderdeel_index].id
        groep_naam = self._of_groep_naam.text().strip() or None
        nerf_waarde = Nerfrichting(self._of_nerf_group.checkedButton().property("waarde"))
        return ModelOnderdeel(
            id=huidig_id or uuid.uuid4().hex[:8],
            naam=self._of_naam.text().strip() or "Onderdeel",
            materiaal_id=self._of_materiaal.currentData() or "",
            breedte=self._of_breedte.value(),
            hoogte=self._of_hoogte.value(),
            aantal=self._of_aantal.value(),
            nerfrichting_vereist=nerf_waarde,
            kantenband_randen=frozenset(r for r, b in self._of_rand_buttons.items() if b.isChecked()),
            fabriekskantenband_vereist=self._of_fabriek.isChecked(),
            groep_id=groep_naam,
            groep_volgorde=(self._of_groep_volgorde.value() if groep_naam else None),
        )

    def _onderdeel_opslaan_klik(self) -> None:
        onderdeel = self._onderdeel_uit_formulier()
        if self._bewerk_onderdeel_index is not None:
            self._werk_onderdelen[self._bewerk_onderdeel_index] = onderdeel
        else:
            self._werk_onderdelen.append(onderdeel)
        self._reset_onderdeel_form()
        self._ververs_onderdelen()

    # ------------------------------------------------------------------
    # Submodellen-lijst (nesting)
    # ------------------------------------------------------------------
    def _zou_cirkel_veroorzaken(self, kandidaat_id: str) -> bool:
        if self._bewerk_id is None:
            return False
        if kandidaat_id == self._bewerk_id:
            return True
        bezocht: set[str] = set()
        stack = [kandidaat_id]
        while stack:
            model_id = stack.pop()
            if model_id == self._bewerk_id:
                return True
            if model_id in bezocht:
                continue
            bezocht.add(model_id)
            try:
                model = self.bibliotheek.ophalen(model_id)
            except KeyError:
                continue
            stack.extend(s.model_id for s in model.submodellen)
        return False

    def _ververs_submodel_combo(self) -> None:
        self._sm_select.clear()
        for model in self.bibliotheek.lijst():
            if model.id == self._bewerk_id:
                continue
            cirkel = self._zou_cirkel_veroorzaken(model.id)
            label = model.naam + (" (cirkelverwijzing)" if cirkel else "")
            self._sm_select.addItem(label, model.id)
            if cirkel:
                item = self._sm_select.model().item(self._sm_select.count() - 1)
                if item is not None:
                    item.setEnabled(False)

    def _ververs_submodellen(self) -> None:
        self._submodellen_label.setText(f"SUBMODELLEN, NESTING ({len(self._werk_submodellen)})")
        _clear_layout(self._submodellen_container)
        for index, submodel in enumerate(self._werk_submodellen):
            self._submodellen_container.addWidget(self._bouw_submodel_rij(submodel, index))

    def _bouw_submodel_rij(self, s: SubModelVerwijzing, index: int) -> QWidget:
        row = QFrame()
        row.setProperty("role", "subRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 7, 8, 7)
        layout.setSpacing(8)

        icon_label = QLabel()
        icon_label.setPixmap(icon_pixmap("cube", self._theme.indigo, 15))
        layout.addWidget(icon_label)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        try:
            model = self.bibliotheek.ophalen(s.model_id)
            naam, meta_tekst = model.naam, f"{len(model.onderdelen)} onderdelen · {model.map or 'geen map'}"
        except KeyError:
            naam, meta_tekst = "onbekend model", ""
        naam_label = QLabel(naam)
        naam_label.setProperty("role", "matName")
        info_col.addWidget(naam_label)
        if meta_tekst:
            meta_label = QLabel(meta_tekst)
            meta_label.setProperty("role", "matMeta")
            info_col.addWidget(meta_label)
        layout.addLayout(info_col, 1)

        aantal_label = QLabel(f"× {s.aantal}")
        aantal_label.setProperty("role", "countPill")
        layout.addWidget(aantal_label)

        del_btn = QToolButton()
        del_btn.setProperty("role", "rowActionDanger")
        del_btn.setIcon(icon("trash", self._theme.text_faint, 14))
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.clicked.connect(lambda: self._verwijder_submodel(index))
        layout.addWidget(del_btn)

        return row

    def _submodel_toevoegen(self) -> None:
        model_id = self._sm_select.currentData()
        if not model_id:
            return
        aantal = self._sm_aantal.value()
        for s in self._werk_submodellen:
            if s.model_id == model_id:
                s.aantal += aantal
                self._ververs_submodellen()
                return
        self._werk_submodellen.append(SubModelVerwijzing(model_id=model_id, aantal=aantal))
        self._ververs_submodellen()

    def _verwijder_submodel(self, index: int) -> None:
        del self._werk_submodellen[index]
        self._ververs_submodellen()
        self._ververs_submodel_combo()

    # ------------------------------------------------------------------
    # Model toevoegen/bewerken/opslaan
    # ------------------------------------------------------------------
    def _reset_model_form(self) -> None:
        self._in_naam.clear()
        self._in_omschrijving.clear()
        self._in_map.clear()
        self._in_tags.clear()
        self._werk_onderdelen = []
        self._werk_submodellen = []
        mappen = sorted({m.map for m in self.bibliotheek.lijst() if m.map})
        self._map_completer.setModel(QStringListModel(mappen, self._map_completer))
        self._validation_banner.hide()

    def _open_drawer(self, model_id: str | None = None) -> None:
        self._reset_model_form()
        self._bewerk_id = model_id

        if model_id is not None:
            m = self.bibliotheek.ophalen(model_id)
            self._drawer_title.setText("Model bewerken")
            self._in_naam.setText(m.naam)
            self._in_omschrijving.setText(m.omschrijving)
            self._in_map.setText(m.map)
            self._in_tags.setText(", ".join(m.tags))
            self._werk_onderdelen = [replace(o) for o in m.onderdelen]
            self._werk_submodellen = [replace(s) for s in m.submodellen]
        else:
            self._drawer_title.setText("Nieuw model")

        self._reset_onderdeel_form()
        self._ververs_onderdelen()
        self._ververs_submodel_combo()
        self._ververs_submodellen()

        self._drawer.show()
        self._in_naam.setFocus()

    def _sluit_drawer(self) -> None:
        self._drawer.hide()

    def _opslaan(self) -> None:
        tags = tuple(t.strip() for t in self._in_tags.text().split(",") if t.strip())
        kandidaat = Model(
            id=self._bewerk_id or "",
            naam=self._in_naam.text().strip(),
            omschrijving=self._in_omschrijving.text().strip(),
            map=self._in_map.text().strip(),
            tags=tags,
            onderdelen=list(self._werk_onderdelen),
            submodellen=list(self._werk_submodellen),
        )

        fouten = valideer(kandidaat, self.materialen, self.bibliotheek)
        if fouten:
            self._validation_label.setText("• " + "\n• ".join(fouten))
            self._validation_banner.show()
            return

        if self._bewerk_id:
            self.bibliotheek.bijwerken(kandidaat)
        else:
            self.bibliotheek.toevoegen(kandidaat)

        self._sluit_drawer()
        self._ververs_alles()
