"""Reststukkenbibliotheek-tabblad: de PySide6-uitwerking, rechtstreeks
gebouwd (op Svens verzoek, zonder eigen HTML-mockup — "praktisch
hetzelfde als de materialenbibliotheek") als variant van
``materialen_page.py``: zijbalk met Beschikbaar/Gebruikt, type- en
familiefilters (afgeleid van het gekoppelde materiaal — een reststuk
heeft geen eigen type/familie, zie ``robocutter.reststukken.models``);
hoofdgedeelte met zoeken, een sorteerbare/doorzoekbare tabel, en een
uitklapbaar paneel (geen pop-up, hoofdstuk 3) om een reststuk toe te
voegen of te bewerken.

Deelt de ``MaterialenBibliotheek``-instantie van ``MaterialenPage``
(zie ``main_window.py``) i.p.v. een eigen materialen-verbinding te
openen — één bron van waarheid in het geheugen, geen risico dat deze
pagina een verouderde materialenlijst laat zien. Reststukken zelf
krijgen wél hun eigen SQLite-opslag (``robocutter.reststukken.opslag``,
zelfde ``data/robocutter.db``-bestand, eigen tabel).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QSize, Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.materialen.models import MateriaalStatus, MateriaalType
from robocutter.reststukken.bibliotheek import (
    OngeldigeStatusOvergangError,
    ReststukkenBibliotheek,
    valideer,
)
from robocutter.reststukken.models import Reststuk, ReststukStatus
from robocutter.reststukken.opslag import open_verbinding
from robocutter.ui.icons import icon, icon_pixmap
from robocutter.ui.theme import Theme

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DB_PAD = _REPO_ROOT / "data" / "robocutter.db"

_KOLOMBREEDTES = [230, 80, 150, 200, 110, 110]
_SORT_OPTIES = [("naam", "Sorteren op materiaal"), ("type", "Sorteren op type"), ("status", "Sorteren op status")]
_DRAWER_BREEDTE = 420
_MATERIAAL_KOLOM_MIN = 200


def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
        elif item.layout() is not None:
            _clear_layout(item.layout())


class ReststukkenPage(QWidget):
    def __init__(self, materialen: MaterialenBibliotheek, theme: Theme, parent=None) -> None:
        super().__init__(parent)
        self._theme = theme
        self.materialen = materialen

        _DB_PAD.parent.mkdir(parents=True, exist_ok=True)
        self._db = open_verbinding(_DB_PAD)
        self.bibliotheek = ReststukkenBibliotheek(materialen, self._db)

        self._status_filter = ReststukStatus.BESCHIKBAAR
        self._type_filter: MateriaalType | None = None
        self._familie_filter: str | None = None
        self._zoekterm = ""
        self._sort = "naam"
        self._confirm_delete_id: str | None = None
        self._alle_families_tonen = False
        self._bewerk_id: str | None = None

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
    # Thema: zelfde aanpak als MaterialenPage — bewuste volledige
    # herbouw, alleen bij een expliciete thema-wissel.
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

        layout.addWidget(self._sidebar_label("Reststukkenbibliotheek"))
        self._btn_beschikbaar = self._sidebar_item("recycle", "Beschikbaar")
        self._btn_beschikbaar.clicked.connect(lambda: self._zet_status_filter(ReststukStatus.BESCHIKBAAR))
        layout.addWidget(self._btn_beschikbaar)
        self._btn_gebruikt = self._sidebar_item("archive", "Gebruikt")
        self._btn_gebruikt.clicked.connect(lambda: self._zet_status_filter(ReststukStatus.GEBRUIKT))
        layout.addWidget(self._btn_gebruikt)
        layout.addWidget(self._divider())

        layout.addWidget(self._sidebar_label("Filteren op type"))
        self._type_filter_rows: dict[MateriaalType | None, tuple[QPushButton, QLabel]] = {}
        for waarde, kleur_attr, tekst in [
            (None, "accent", "Alle reststukken"),
            (MateriaalType.PLAAT, "indigo", "Platen"),
            (MateriaalType.BALK, "warning", "Balken"),
        ]:
            row, count_label = self._filter_row(tekst, getattr(self._theme, kleur_attr))
            row.clicked.connect(lambda checked=False, w=waarde: self._zet_type_filter(w))
            self._type_filter_rows[waarde] = (row, count_label)
            layout.addWidget(row)
        layout.addWidget(self._divider())

        layout.addWidget(self._sidebar_label("Materiaalfamilies"))
        self._family_container = QVBoxLayout()
        self._family_container.setSpacing(2)
        layout.addLayout(self._family_container)
        self._btn_families_meer = QPushButton("")
        self._btn_families_meer.setProperty("role", "sortControl")
        self._btn_families_meer.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_families_meer.clicked.connect(self._toggle_alle_families)
        layout.addWidget(self._btn_families_meer)
        layout.addWidget(self._divider())

        layout.addWidget(self._sidebar_label("Snelacties"))
        add_action = self._sidebar_item("plus", "Reststuk toevoegen")
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

    def _filter_row(self, text: str, dot_color: str) -> tuple[QPushButton, QLabel]:
        button = QPushButton()
        button.setProperty("role", "sidebarItem")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QHBoxLayout(button)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(9)
        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background: {dot_color}; border-radius: 4px;")
        layout.addWidget(dot)
        label = QLabel(text)
        label.setStyleSheet(f"color: {self._theme.text_muted}; font-size: 13px; background: transparent;")
        layout.addWidget(label, 1)
        count_label = QLabel("0")
        count_label.setProperty("role", "filterCount")
        layout.addWidget(count_label)
        return button, count_label

    def _divider(self) -> QFrame:
        line = QFrame()
        line.setObjectName("SidebarDivider")
        line.setFixedHeight(1)
        line.setContentsMargins(0, 8, 0, 12)
        return line

    def _toggle_alle_families(self) -> None:
        self._alle_families_tonen = not self._alle_families_tonen
        self._ververs_sidebar()

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
        title = QLabel("Reststukkenbibliotheek")
        title.setObjectName("PageTitle")
        titles.addWidget(title)
        self._page_sub = QLabel("")
        self._page_sub.setObjectName("PageSub")
        titles.addWidget(self._page_sub)
        head.addLayout(titles)
        head.addStretch(1)

        self._search = QLineEdit()
        self._search.setObjectName("SearchInput")
        self._search.setPlaceholderText('Zoek op materiaal, familie, herkomst of maat, bijv. "eiken 800"')
        self._search.setFixedWidth(280)
        self._search.addAction(icon("search", self._theme.text_faint, 15), QLineEdit.ActionPosition.LeadingPosition)
        self._search.setText(self._zoekterm)
        self._search.textChanged.connect(self._zoekterm_gewijzigd)
        head.addWidget(self._search)

        add_btn = QPushButton("  Reststuk toevoegen")
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
        self._table.setHorizontalHeaderLabels(["Materiaal", "Type", "Afmetingen", "Herkomst", "Status", ""])
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Zelfde reden als in materialen_page.py: Interactive overal +
        # zelf de Materiaal-kolom herberekenen i.p.v. Stretch, anders
        # knijpt de tabel die kolom tot onleesbaar smal zodra het paneel
        # rechts openstaat.
        header = self._table.horizontalHeader()
        header.setStretchLastSection(False)
        for col, breedte in enumerate(_KOLOMBREEDTES):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            self._table.setColumnWidth(col, breedte)
        self._table.installEventFilter(self)
        card_layout.addWidget(self._table)

        self._empty_label = QLabel("Geen reststukken gevonden voor deze zoekopdracht/filter.")
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

    def _zet_status_filter(self, status: ReststukStatus) -> None:
        self._status_filter = status
        self._confirm_delete_id = None
        self._ververs_alles()

    def _zet_type_filter(self, waarde: MateriaalType | None) -> None:
        self._type_filter = waarde
        self._ververs_alles()

    def _zet_familie_filter(self, familie: str) -> None:
        self._familie_filter = None if self._familie_filter == familie else familie
        self._ververs_alles()

    # ------------------------------------------------------------------
    # Verversen (in-place, geen volledige herbouw — behoudt focus/scroll)
    # ------------------------------------------------------------------
    def _ververs_alles(self) -> None:
        self._ververs_sidebar()
        self._ververs_tabel()

    def _ververs_sidebar(self) -> None:
        alles = self.bibliotheek.lijst()
        beschikbaar_count = sum(1 for r in alles if r.status == ReststukStatus.BESCHIKBAAR)
        gebruikt_count = sum(1 for r in alles if r.status == ReststukStatus.GEBRUIKT)
        plaat_count = sum(1 for r in alles if self.bibliotheek.materiaal_van(r).type == MateriaalType.PLAAT)
        balk_count = sum(1 for r in alles if self.bibliotheek.materiaal_van(r).type == MateriaalType.BALK)

        self._btn_beschikbaar.setStyleSheet(self._sidebar_actief_stylesheet(self._status_filter == ReststukStatus.BESCHIKBAAR))
        self._btn_gebruikt.setStyleSheet(self._sidebar_actief_stylesheet(self._status_filter == ReststukStatus.GEBRUIKT))
        self._btn_gebruikt.setText(f"  Gebruikt   ·   {gebruikt_count}" if gebruikt_count else "  Gebruikt")

        binnen_weergave = [r for r in alles if r.status == self._status_filter]
        weergave_plaat_count = sum(1 for r in binnen_weergave if self.bibliotheek.materiaal_van(r).type == MateriaalType.PLAAT)
        weergave_balk_count = sum(1 for r in binnen_weergave if self.bibliotheek.materiaal_van(r).type == MateriaalType.BALK)

        tellingen = {None: len(binnen_weergave), MateriaalType.PLAAT: weergave_plaat_count, MateriaalType.BALK: weergave_balk_count}
        for waarde, (row, count_label) in self._type_filter_rows.items():
            count_label.setText(str(tellingen[waarde]))
            actief = self._type_filter == waarde
            row.setStyleSheet(
                f"QPushButton {{ background: {self._theme.accent_soft if actief else 'transparent'}; "
                f"border: none; border-radius: 7px; padding: 5px 0; text-align: left; }}"
                f"QPushButton:hover {{ background: {self._theme.surface_hover}; }}"
            )

        self._page_sub.setText(
            f"{len(alles)} reststukken · {beschikbaar_count} beschikbaar · {gebruikt_count} gebruikt · "
            f"{plaat_count} platen · {balk_count} balken"
        )

        familie_counts: dict[str, int] = {}
        for r in binnen_weergave:
            familie = self.bibliotheek.materiaal_van(r).familie
            if familie:
                familie_counts[familie] = familie_counts.get(familie, 0) + 1
        families = sorted(familie_counts, key=lambda f: (-familie_counts[f], f.lower()))
        zichtbaar = families if self._alle_families_tonen else families[:6]
        rest = len(families) - len(zichtbaar)

        _clear_layout(self._family_container)
        for naam in zichtbaar:
            row = QPushButton()
            row.setProperty("role", "sidebarItem")
            row.setCursor(Qt.CursorShape.PointingHandCursor)
            actief = self._familie_filter == naam
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
            count_label = QLabel(str(familie_counts[naam]))
            count_label.setProperty("role", "filterCount")
            row_layout.addWidget(count_label)
            row.clicked.connect(lambda checked=False, n=naam: self._zet_familie_filter(n))
            self._family_container.addWidget(row)

        if rest > 0:
            self._btn_families_meer.setText(f"+ {rest} andere families" if not self._alle_families_tonen else "Toon minder families")
            self._btn_families_meer.show()
        else:
            self._btn_families_meer.hide()

    def _sidebar_actief_stylesheet(self, actief: bool) -> str:
        if not actief:
            return ""
        return (
            f"QPushButton {{ background: {self._theme.accent_soft}; color: {self._theme.accent_text}; "
            f"font-weight: 600; border: none; border-radius: 7px; padding: 7px 8px; text-align: left; }}"
        )

    def _zichtbare_rijen(self) -> list[Reststuk]:
        rijen = self.bibliotheek.lijst(status=self._status_filter, type_filter=self._type_filter, zoekterm=self._zoekterm)
        if self._familie_filter:
            rijen = [r for r in rijen if self.bibliotheek.materiaal_van(r).familie == self._familie_filter]
        if self._sort == "type":
            rijen.sort(key=lambda r: (self.bibliotheek.materiaal_van(r).type.value, self.bibliotheek.materiaal_van(r).naam.lower()))
        elif self._sort == "status":
            rijen.sort(key=lambda r: (r.status.value, self.bibliotheek.materiaal_van(r).naam.lower()))
        return rijen

    def eventFilter(self, obj, event) -> bool:
        if obj is self._table and event.type() == QEvent.Type.Resize:
            QTimer.singleShot(0, self._herbereken_materiaal_kolom)
        return super().eventFilter(obj, event)

    def _herbereken_materiaal_kolom(self) -> None:
        andere_kolommen_breedte = sum(_KOLOMBREEDTES[1:])
        beschikbaar = self._table.viewport().width() - andere_kolommen_breedte
        self._table.setColumnWidth(0, max(_MATERIAAL_KOLOM_MIN, beschikbaar))

    def _ververs_tabel(self) -> None:
        label, _ = next(o for o in _SORT_OPTIES if o[0] == self._sort)
        self._sort_btn.setText(label)

        rijen = self._zichtbare_rijen()
        self._table.clearContents()
        self._table.setRowCount(len(rijen))
        self._table.setVisible(bool(rijen))
        self._empty_label.setVisible(not rijen)

        for row_index, reststuk in enumerate(rijen):
            materiaal = self.bibliotheek.materiaal_van(reststuk)
            self._table.setRowHeight(row_index, 56)
            self._table.setCellWidget(row_index, 0, self._cel_materiaal(reststuk, materiaal))
            self._table.setCellWidget(row_index, 1, self._cel_type(materiaal))
            self._table.setCellWidget(row_index, 2, self._cel_afmetingen(reststuk, materiaal))
            self._table.setCellWidget(row_index, 3, self._cel_herkomst(reststuk))
            self._table.setCellWidget(row_index, 4, self._cel_status(reststuk))
            self._table.setCellWidget(row_index, 5, self._cel_acties(reststuk))

    def _cel_materiaal(self, r: Reststuk, m) -> QWidget:
        cell = QWidget()
        layout = QVBoxLayout(cell)
        layout.setContentsMargins(10, 4, 4, 4)
        layout.setSpacing(2)
        naam = QLabel(m.naam)
        naam.setProperty("role", "matName")
        layout.addWidget(naam)
        meta_tekst = " · ".join(t for t in [m.familie, m.kleur_afwerking] if t) or "—"
        meta = QLabel(meta_tekst)
        meta.setProperty("role", "matMeta")
        layout.addWidget(meta)
        return cell

    def _cel_type(self, m) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)
        icon_label = QLabel()
        icon_label.setPixmap(icon_pixmap("layers" if m.type == MateriaalType.PLAAT else "bar", self._theme.text_faint, 15))
        layout.addWidget(icon_label)
        text = QLabel("Plaat" if m.type == MateriaalType.PLAAT else "Balk")
        text.setProperty("role", "typePill")
        layout.addWidget(text)
        layout.addStretch(1)
        return cell

    def _cel_afmetingen(self, r: Reststuk, m) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(4, 4, 4, 4)
        tekst = f"{r.lengte:g} × {r.breedte:g} × {m.derde_afmeting:g} mm"
        label = QLabel(tekst)
        label.setProperty("role", "dims")
        layout.addWidget(label)
        return cell

    def _cel_herkomst(self, r: Reststuk) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(4, 4, 4, 4)
        tekst = " / ".join(t for t in [r.herkomst_project, r.herkomst_model] if t) or "—"
        label = QLabel(tekst)
        label.setProperty("role", "matMeta" if tekst != "—" else "tagEmpty")
        label.setWordWrap(False)
        layout.addWidget(label)
        return cell

    def _cel_status(self, r: Reststuk) -> QWidget:
        is_gebruikt = r.status == ReststukStatus.GEBRUIKT
        chip = QFrame()
        chip.setProperty("chip", "archived" if is_gebruikt else "done")
        layout = QHBoxLayout(chip)
        layout.setContentsMargins(9, 3, 9, 3)
        layout.setSpacing(6)
        dot = QLabel()
        dot.setFixedSize(7, 7)
        dot_color = self._theme.text_faint if is_gebruikt else self._theme.success
        dot.setStyleSheet(f"background: {dot_color}; border-radius: 3px;")
        layout.addWidget(dot)
        text = QLabel("Gebruikt" if is_gebruikt else "Beschikbaar")
        layout.addWidget(text)

        wrapper = QWidget()
        wrapper_layout = QHBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(4, 4, 4, 4)
        wrapper_layout.addWidget(chip)
        wrapper_layout.addStretch(1)
        return wrapper

    def _cel_acties(self, r: Reststuk) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(1)

        edit_btn = QToolButton()
        edit_btn.setProperty("role", "rowAction")
        edit_btn.setIcon(icon("pencil", self._theme.text_faint, 15))
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setToolTip("Bewerken")
        edit_btn.clicked.connect(lambda: self._open_drawer(r.id))
        layout.addWidget(edit_btn)

        if self._confirm_delete_id == r.id:
            label = QLabel("Verwijderen?")
            label.setProperty("role", "confirmDeleteLabel")
            layout.addWidget(label)
            yes_btn = QToolButton()
            yes_btn.setProperty("role", "confirmYes")
            yes_btn.setIcon(icon("check", "#FFFFFF", 11))
            yes_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            yes_btn.clicked.connect(lambda: self._verwijderen(r.id))
            layout.addWidget(yes_btn)
            no_btn = QToolButton()
            no_btn.setProperty("role", "confirmNo")
            no_btn.setIcon(icon("close", self._theme.text_muted, 11))
            no_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            no_btn.clicked.connect(self._annuleer_verwijderen)
            layout.addWidget(no_btn)
        else:
            if r.status == ReststukStatus.BESCHIKBAAR:
                toggle_btn = QToolButton()
                toggle_btn.setProperty("role", "rowAction")
                toggle_btn.setIcon(icon("archive", self._theme.text_faint, 15))
                toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                toggle_btn.setToolTip("Markeer als gebruikt")
                toggle_btn.clicked.connect(lambda: self._markeer_gebruikt(r.id))
                layout.addWidget(toggle_btn)
            else:
                toggle_btn = QToolButton()
                toggle_btn.setProperty("role", "rowAction")
                toggle_btn.setIcon(icon("recycle", self._theme.text_faint, 15))
                toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                toggle_btn.setToolTip("Zet terug op beschikbaar")
                toggle_btn.clicked.connect(lambda: self._zet_beschikbaar(r.id))
                layout.addWidget(toggle_btn)

            delete_btn = QToolButton()
            delete_btn.setProperty("role", "rowActionDanger")
            delete_btn.setIcon(icon("trash", self._theme.text_faint, 15))
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.setToolTip("Verwijderen")
            delete_btn.clicked.connect(lambda: self._vraag_verwijder_bevestiging(r.id))
            layout.addWidget(delete_btn)

        layout.addStretch(1)
        return cell

    # ------------------------------------------------------------------
    # Statusacties
    # ------------------------------------------------------------------
    def _markeer_gebruikt(self, reststuk_id: str) -> None:
        try:
            self.bibliotheek.markeer_gebruikt(reststuk_id)
        except OngeldigeStatusOvergangError:
            pass
        self._ververs_alles()

    def _zet_beschikbaar(self, reststuk_id: str) -> None:
        try:
            self.bibliotheek.zet_beschikbaar(reststuk_id)
        except OngeldigeStatusOvergangError:
            pass
        self._ververs_alles()

    def _vraag_verwijder_bevestiging(self, reststuk_id: str) -> None:
        self._confirm_delete_id = reststuk_id
        self._ververs_tabel()

    def _annuleer_verwijderen(self) -> None:
        self._confirm_delete_id = None
        self._ververs_tabel()

    def _verwijderen(self, reststuk_id: str) -> None:
        self.bibliotheek.verwijderen(reststuk_id)
        self._confirm_delete_id = None
        self._ververs_alles()

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
        self._drawer_title = QLabel("Nieuw reststuk")
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

        self._status_row = QFrame()
        self._status_row.setObjectName("DrawerStatusRow")
        status_layout = QHBoxLayout(self._status_row)
        status_layout.setContentsMargins(18, 10, 18, 10)
        status_layout.addWidget(QLabel("Status"))
        self._status_chip_label = QLabel("Beschikbaar")
        status_layout.addWidget(self._status_chip_label)
        status_layout.addStretch(1)
        self._status_toggle_action = None
        self._status_toggle_btn = QPushButton()
        self._status_toggle_btn.setProperty("role", "ghost")
        self._status_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._status_toggle_btn.clicked.connect(lambda: self._status_toggle_action and self._status_toggle_action())
        status_layout.addWidget(self._status_toggle_btn)
        outer.addWidget(self._status_row)
        self._status_row.hide()

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
        body_layout.setSpacing(20)
        body_layout.addLayout(self._build_basisgegevens_sectie())
        body_layout.addLayout(self._build_afmetingen_sectie())
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
        save_btn = QPushButton("Reststuk opslaan")
        save_btn.setProperty("role", "primary")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._opslaan)
        footer.addWidget(save_btn)
        footer_widget = QWidget()
        footer_widget.setLayout(footer)
        outer.addWidget(footer_widget)

        return drawer

    def _field_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty("role", "fieldLabel")
        return label

    def _field_input(self) -> QLineEdit:
        field = QLineEdit()
        field.setProperty("role", "field")
        return field

    def _field_spin(self) -> tuple[QFrame, QDoubleSpinBox]:
        field = QDoubleSpinBox()
        field.setProperty("role", "fieldSpin")
        field.setRange(0.01, 100000.0)
        field.setDecimals(1)
        field.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

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
        return wrapper, field

    def _build_basisgegevens_sectie(self) -> QVBoxLayout:
        section = QVBoxLayout()
        section.setSpacing(10)
        label = QLabel("BASISGEGEVENS")
        label.setProperty("role", "fieldSectionLabel")
        section.addWidget(label)

        section.addWidget(self._field_label("Materiaal"))
        self._in_materiaal = QComboBox()
        self._in_materiaal.setProperty("role", "field")
        self._in_materiaal.currentIndexChanged.connect(self._update_materiaal_info)
        section.addWidget(self._in_materiaal)
        self._materiaal_info = QLabel("")
        self._materiaal_info.setProperty("role", "fieldHint")
        self._materiaal_info.setWordWrap(True)
        section.addWidget(self._materiaal_info)

        rij = QHBoxLayout()
        kol1 = QVBoxLayout()
        kol1.addWidget(self._field_label("Herkomst project"))
        self._in_herkomst_project = self._field_input()
        kol1.addWidget(self._in_herkomst_project)
        rij.addLayout(kol1)
        kol2 = QVBoxLayout()
        kol2.addWidget(self._field_label("Herkomst model"))
        self._in_herkomst_model = self._field_input()
        kol2.addWidget(self._in_herkomst_model)
        rij.addLayout(kol2)
        section.addLayout(rij)

        return section

    def _build_afmetingen_sectie(self) -> QVBoxLayout:
        section = QVBoxLayout()
        section.setSpacing(10)
        label = QLabel("RESTERENDE AFMETINGEN")
        label.setProperty("role", "fieldSectionLabel")
        section.addWidget(label)

        rij = QHBoxLayout()
        rij.setSpacing(8)
        kol1 = QVBoxLayout()
        kol1.addWidget(self._field_label("Lengte (mm)"))
        lengte_wrap, self._in_lengte = self._field_spin()
        kol1.addWidget(lengte_wrap)
        rij.addLayout(kol1)
        kol2 = QVBoxLayout()
        kol2.addWidget(self._field_label("Breedte (mm)"))
        breedte_wrap, self._in_breedte = self._field_spin()
        kol2.addWidget(breedte_wrap)
        rij.addLayout(kol2)
        section.addLayout(rij)
        return section

    def _update_materiaal_info(self) -> None:
        materiaal_id = self._in_materiaal.currentData()
        if not materiaal_id:
            self._materiaal_info.setText("")
            return
        try:
            materiaal = self.materialen.ophalen(materiaal_id)
        except KeyError:
            self._materiaal_info.setText("")
            return
        status_tekst = "" if materiaal.status == MateriaalStatus.ACTIEF else " · gearchiveerd"
        self._materiaal_info.setText(
            f"Dikte {materiaal.derde_afmeting:g} mm · kerf {materiaal.kerf:g} mm"
            f"{(' · ' + materiaal.familie) if materiaal.familie else ''}{status_tekst}"
        )

    def _reset_form(self) -> None:
        huidige = self._in_materiaal.currentData()
        self._in_materiaal.clear()
        for materiaal in sorted(self.materialen.lijst(), key=lambda m: m.naam.lower()):
            label = f"{materiaal.naam} ({materiaal.type.value})"
            if materiaal.status != MateriaalStatus.ACTIEF:
                label += ", gearchiveerd"
            self._in_materiaal.addItem(label, materiaal.id)
        index = self._in_materiaal.findData(huidige)
        if index >= 0:
            self._in_materiaal.setCurrentIndex(index)
        self._in_herkomst_project.clear()
        self._in_herkomst_model.clear()
        self._in_lengte.setValue(0)
        self._in_breedte.setValue(0)
        self._update_materiaal_info()
        self._validation_banner.hide()

    def _open_drawer(self, reststuk_id: str | None = None) -> None:
        self._reset_form()
        self._bewerk_id = reststuk_id

        if reststuk_id is not None:
            r = self.bibliotheek.ophalen(reststuk_id)
            self._drawer_title.setText("Reststuk bewerken")
            index = self._in_materiaal.findData(r.materiaal_id)
            if index >= 0:
                self._in_materiaal.setCurrentIndex(index)
            self._update_materiaal_info()
            self._in_lengte.setValue(r.lengte)
            self._in_breedte.setValue(r.breedte)
            self._in_herkomst_project.setText(r.herkomst_project)
            self._in_herkomst_model.setText(r.herkomst_model)

            is_gebruikt = r.status == ReststukStatus.GEBRUIKT
            self._status_chip_label.setText("Gebruikt" if is_gebruikt else "Beschikbaar")
            self._status_toggle_btn.setText("Zet terug op beschikbaar" if is_gebruikt else "Markeer als gebruikt")
            if is_gebruikt:
                self._status_toggle_action = lambda: (self._zet_beschikbaar(r.id), self._sluit_drawer())
            else:
                self._status_toggle_action = lambda: (self._markeer_gebruikt(r.id), self._sluit_drawer())
            self._status_row.show()
        else:
            self._drawer_title.setText("Nieuw reststuk")
            self._status_row.hide()

        self._drawer.show()
        self._in_materiaal.setFocus()

    def _sluit_drawer(self) -> None:
        self._drawer.hide()

    def _opslaan(self) -> None:
        kandidaat = Reststuk(
            id=self._bewerk_id or "",
            materiaal_id=self._in_materiaal.currentData() or "",
            lengte=self._in_lengte.value(),
            breedte=self._in_breedte.value(),
            herkomst_project=self._in_herkomst_project.text().strip(),
            herkomst_model=self._in_herkomst_model.text().strip(),
        )

        fouten = valideer(kandidaat, self.materialen)
        if fouten:
            self._validation_label.setText("• " + "\n• ".join(fouten))
            self._validation_banner.show()
            return

        if self._bewerk_id:
            kandidaat.status = self.bibliotheek.ophalen(self._bewerk_id).status
            self.bibliotheek.bijwerken(kandidaat)
        else:
            self.bibliotheek.toevoegen(kandidaat)
            self._status_filter = ReststukStatus.BESCHIKBAAR

        self._sluit_drawer()
        self._ververs_alles()
