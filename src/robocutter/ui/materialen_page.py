"""Materialenbibliotheek-tabblad: de PySide6-uitwerking van de door Sven
goedgekeurde HTML-conceptmockup (zie OVERDRACHT.md). Zijbalk met
Overzicht/Archief, type- en familiefilters; hoofdgedeelte met zoeken,
een sorteerbare/doorzoekbare tabel, en een uitklapbaar paneel (geen
pop-up, zie hoofdstuk 3) om een materiaal toe te voegen of te bewerken.

Opslag: lokaal SQLite-bestand (``data/robocutter.db``, zie
``robocutter.materialen.opslag`` en hoofdstuk 8). Nog geen
multi-gebruiker-/netwerkopslag, en nog geen instelbare locatie (zie de
openstaande punten in OVERDRACHT.md).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QSize, Qt, QStringListModel, QTimer
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QButtonGroup,
    QCompleter,
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

from robocutter.materialen.bibliotheek import (
    MaterialenBibliotheek,
    OngeldigeStatusOvergangError,
    valideer,
)
from robocutter.materialen.models import Materiaal, MateriaalStatus, MateriaalType, Nerfrichting, Rand
from robocutter.materialen.opslag import open_verbinding
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
_KOLOMBREEDTES = [230, 80, 150, 110, 140, 100, 110]
_SORT_OPTIES = [("naam", "Sorteren op naam"), ("type", "Sorteren op type"), ("status", "Sorteren op status")]
_DRAWER_BREEDTE = 420
_MATERIAAL_KOLOM_MIN = 200


def _sample_materialen() -> list[Materiaal]:
    return [
        Materiaal(
            id="", naam="Eiken multiplex 18mm", type=MateriaalType.PLAAT,
            lengte=2800, breedte=2070, derde_afmeting=18, familie="Eiken multiplex",
            kleur_afwerking="Naturel", nerfrichting=Nerfrichting.LANGE_ZIJDE, kerf=4,
            min_reststukgrootte=300, productcode="EMP-18", leverancier="Houthandel Jansen",
            tags=("multiplex", "eiken"),
        ),
        Materiaal(
            id="", naam="Wit gemelamineerd 18mm", type=MateriaalType.PLAAT,
            lengte=2800, breedte=2070, derde_afmeting=18, familie="Wit gemelamineerd",
            kleur_afwerking="Wit", nerfrichting=Nerfrichting.GEEN, kerf=3.2,
            min_reststukgrootte=200, productcode="MEL-WIT-18", leverancier="Egger",
            tags=("melamine",),
        ),
        Materiaal(
            id="", naam="Vurenhouten regel 40x60", type=MateriaalType.BALK,
            lengte=3000, breedte=40, derde_afmeting=60, familie="Vurenhout regelwerk",
            kleur_afwerking="Naturel", nerfrichting=Nerfrichting.LANGE_ZIJDE, kerf=3,
            min_reststukgrootte=200,
        ),
    ]


def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
        elif item.layout() is not None:
            _clear_layout(item.layout())


class MaterialenPage(QWidget):
    def __init__(self, theme: Theme, parent=None) -> None:
        super().__init__(parent)
        self._theme = theme

        _DB_PAD.parent.mkdir(parents=True, exist_ok=True)
        self._db = open_verbinding(_DB_PAD)
        self.bibliotheek = MaterialenBibliotheek(self._db)
        if not self.bibliotheek.lijst():
            for materiaal in _sample_materialen():
                self.bibliotheek.toevoegen(materiaal)
            self.bibliotheek.archiveren(
                next(m.id for m in self.bibliotheek.lijst() if m.naam == "Vurenhouten regel 40x60")
            )

        self._status_filter = MateriaalStatus.ACTIEF
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
    # Thema: bewuste volledige herbouw (zelfde aanpak als MainWindow),
    # gebeurt alleen bij een expliciete thema-wissel, niet bij normaal
    # gebruik — filters/zoekterm/open paneel gaan dan wél verloren, dat
    # is geaccepteerd voor deze eerste versie.
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

        layout.addWidget(self._sidebar_label("Materialenbibliotheek"))
        self._btn_overzicht = self._sidebar_item("layers", "Overzicht")
        self._btn_overzicht.clicked.connect(lambda: self._zet_status_filter(MateriaalStatus.ACTIEF))
        layout.addWidget(self._btn_overzicht)
        self._btn_archief = self._sidebar_item("archive", "Archief")
        self._btn_archief.clicked.connect(lambda: self._zet_status_filter(MateriaalStatus.GEARCHIVEERD))
        layout.addWidget(self._btn_archief)
        layout.addWidget(self._divider())

        layout.addWidget(self._sidebar_label("Filteren op type"))
        self._type_filter_rows: dict[MateriaalType | None, tuple[QPushButton, QLabel]] = {}
        for waarde, kleur_attr, tekst in [
            (None, "accent", "Alle materialen"),
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
        add_action = self._sidebar_item("plus", "Materiaal toevoegen")
        add_action.clicked.connect(lambda: self._open_drawer())
        layout.addWidget(add_action)
        import_action = self._sidebar_item("upload", "Importeren (CSV/Excel)")
        import_action.setEnabled(False)
        import_action.setToolTip("Nog niet beschikbaar")
        layout.addWidget(import_action)

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
        title = QLabel("Materialenbibliotheek")
        title.setObjectName("PageTitle")
        titles.addWidget(title)
        self._page_sub = QLabel("")
        self._page_sub.setObjectName("PageSub")
        titles.addWidget(self._page_sub)
        head.addLayout(titles)
        head.addStretch(1)

        self._search = QLineEdit()
        self._search.setObjectName("SearchInput")
        self._search.setPlaceholderText('Zoek op naam, familie, tag of maat, bijv. "multiplex 2800 18"')
        self._search.setFixedWidth(280)
        self._search.addAction(icon("search", self._theme.text_faint, 15), QLineEdit.ActionPosition.LeadingPosition)
        self._search.setText(self._zoekterm)
        self._search.textChanged.connect(self._zoekterm_gewijzigd)
        head.addWidget(self._search)

        add_btn = QPushButton("  Materiaal toevoegen")
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

        self._table = QTableWidget(0, 7)
        self._table.setObjectName("LibraryTable")
        self._table.setHorizontalHeaderLabels(
            ["Materiaal", "Type", "Afmetingen", "Nerfrichting", "Tags", "Status", ""]
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Bewust overal Interactive i.p.v. de Materiaal-kolom op Stretch: met
        # Stretch ernaast dwingen de vaste kolommen de tabel nooit tot
        # horizontaal scrollen — ze knijpen de stretch-kolom in plaats daarvan
        # tot onleesbaar smal zodra het paneel rechts openstaat en er te
        # weinig ruimte overblijft. In plaats daarvan berekenen we de breedte
        # van de Materiaal-kolom zelf (_herbereken_materiaal_kolom): vult de
        # rest van de kaart als er ruimte is, maar zakt nooit onder een
        # minimum — dan scrollt de tabel liever horizontaal.
        header = self._table.horizontalHeader()
        header.setStretchLastSection(False)
        for col, breedte in enumerate(_KOLOMBREEDTES):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            self._table.setColumnWidth(col, breedte)
        self._table.installEventFilter(self)
        card_layout.addWidget(self._table)

        self._empty_label = QLabel("Geen materialen gevonden voor deze zoekopdracht/filter.")
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

    def _zet_status_filter(self, status: MateriaalStatus) -> None:
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
        actief_count = sum(1 for m in alles if m.status == MateriaalStatus.ACTIEF)
        archief_count = sum(1 for m in alles if m.status == MateriaalStatus.GEARCHIVEERD)
        plaat_count = sum(1 for m in alles if m.type == MateriaalType.PLAAT)
        balk_count = sum(1 for m in alles if m.type == MateriaalType.BALK)

        self._btn_overzicht.setStyleSheet(self._sidebar_actief_stylesheet(self._status_filter == MateriaalStatus.ACTIEF))
        self._btn_archief.setStyleSheet(self._sidebar_actief_stylesheet(self._status_filter == MateriaalStatus.GEARCHIVEERD))
        self._btn_archief.setText(f"  Archief   ·   {archief_count}" if archief_count else "  Archief")

        # Type- en familiefilters horen bij de huidige weergave (Overzicht of
        # Archief): een gearchiveerd balk-materiaal mag niet meetellen bij
        # "Balken" zolang je in Overzicht zit, en andersom.
        binnen_weergave = [m for m in alles if m.status == self._status_filter]
        weergave_plaat_count = sum(1 for m in binnen_weergave if m.type == MateriaalType.PLAAT)
        weergave_balk_count = sum(1 for m in binnen_weergave if m.type == MateriaalType.BALK)

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
            f"{len(alles)} materialen · {actief_count} actief · {archief_count} gearchiveerd · "
            f"{plaat_count} platen · {balk_count} balken"
        )

        familie_counts: dict[str, int] = {}
        for m in binnen_weergave:
            if m.familie:
                familie_counts[m.familie] = familie_counts.get(m.familie, 0) + 1
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

    def _zichtbare_rijen(self) -> list[Materiaal]:
        rijen = self.bibliotheek.lijst(
            status=self._status_filter, type_filter=self._type_filter, zoekterm=self._zoekterm
        )
        if self._familie_filter:
            rijen = [m for m in rijen if m.familie == self._familie_filter]
        if self._sort == "type":
            rijen.sort(key=lambda m: (m.type.value, m.naam.lower()))
        elif self._sort == "status":
            rijen.sort(key=lambda m: (m.status.value, m.naam.lower()))
        return rijen

    def eventFilter(self, obj, event) -> bool:
        if obj is self._table and event.type() == QEvent.Type.Resize:
            # Uitgesteld: op het moment van dit Resize-event heeft de
            # viewport vaak nog een tussentijdse (te kleine) breedte — pas
            # bij de eerstvolgende event-loop-doorgang staat de layout echt
            # vast. Zonder uitstel zakte de kolom naar het minimum en bleef
            # daar hangen totdat er toevallig weer een resize kwam.
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
        # clearContents() vóór het herbouwen: setCellWidget() op een rij die
        # al een widget had (bv. omdat filteren de rij-index van een ander
        # materiaal geeft) liet in de praktijk oude en nieuwe tekst over
        # elkaar heen zien totdat er toevallig een volledige repaint kwam.
        self._table.clearContents()
        self._table.setRowCount(len(rijen))
        self._table.setVisible(bool(rijen))
        self._empty_label.setVisible(not rijen)

        for row_index, materiaal in enumerate(rijen):
            self._table.setRowHeight(row_index, 56)
            self._table.setCellWidget(row_index, 0, self._cel_materiaal(materiaal))
            self._table.setCellWidget(row_index, 1, self._cel_type(materiaal))
            self._table.setCellWidget(row_index, 2, self._cel_afmetingen(materiaal))
            self._table.setCellWidget(row_index, 3, self._cel_nerf(materiaal))
            self._table.setCellWidget(row_index, 4, self._cel_tags(materiaal))
            self._table.setCellWidget(row_index, 5, self._cel_status(materiaal))
            self._table.setCellWidget(row_index, 6, self._cel_acties(materiaal))

    def _cel_materiaal(self, m: Materiaal) -> QWidget:
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

    def _cel_type(self, m: Materiaal) -> QWidget:
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

    def _cel_afmetingen(self, m: Materiaal) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(4, 4, 4, 4)
        tekst = f"{m.lengte:g} × {m.breedte:g} × {m.derde_afmeting:g} mm"
        label = QLabel(tekst)
        label.setProperty("role", "dims")
        layout.addWidget(label)
        return cell

    def _cel_nerf(self, m: Materiaal) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)
        is_geen = m.nerfrichting == Nerfrichting.GEEN
        icon_label = QLabel()
        icon_label.setPixmap(icon_pixmap("grain", self._theme.text_faint, 15))
        layout.addWidget(icon_label)
        text = QLabel(_NERF_LABEL[m.nerfrichting])
        text.setProperty("role", "nerfNone" if is_geen else "nerf")
        layout.addWidget(text)
        layout.addStretch(1)
        return cell

    def _cel_tags(self, m: Materiaal) -> QWidget:
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

    def _cel_status(self, m: Materiaal) -> QWidget:
        is_archived = m.status == MateriaalStatus.GEARCHIVEERD
        chip = QFrame()
        chip.setProperty("chip", "archived" if is_archived else "done")
        layout = QHBoxLayout(chip)
        layout.setContentsMargins(9, 3, 9, 3)
        layout.setSpacing(6)
        dot = QLabel()
        dot.setFixedSize(7, 7)
        dot_color = self._theme.text_faint if is_archived else self._theme.success
        dot.setStyleSheet(f"background: {dot_color}; border-radius: 3px;")
        layout.addWidget(dot)
        text = QLabel("Gearchiveerd" if is_archived else "Actief")
        layout.addWidget(text)

        wrapper = QWidget()
        wrapper_layout = QHBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(4, 4, 4, 4)
        wrapper_layout.addWidget(chip)
        wrapper_layout.addStretch(1)
        return wrapper

    def _cel_acties(self, m: Materiaal) -> QWidget:
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
            label = QLabel("Definitief verwijderen?")
            label.setProperty("role", "confirmDeleteLabel")
            layout.addWidget(label)
            yes_btn = QToolButton()
            yes_btn.setProperty("role", "confirmYes")
            yes_btn.setIcon(icon("check", "#FFFFFF", 11))
            yes_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            yes_btn.clicked.connect(lambda: self._verwijder_definitief(m.id))
            layout.addWidget(yes_btn)
            no_btn = QToolButton()
            no_btn.setProperty("role", "confirmNo")
            no_btn.setIcon(icon("close", self._theme.text_muted, 11))
            no_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            no_btn.clicked.connect(self._annuleer_verwijderen)
            layout.addWidget(no_btn)
        elif m.status == MateriaalStatus.GEARCHIVEERD:
            restore_btn = QToolButton()
            restore_btn.setProperty("role", "rowAction")
            restore_btn.setIcon(icon("recycle", self._theme.text_faint, 15))
            restore_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            restore_btn.setToolTip("Terugzetten naar actief")
            restore_btn.clicked.connect(lambda: self._heractiveren(m.id))
            layout.addWidget(restore_btn)

            delete_btn = QToolButton()
            delete_btn.setProperty("role", "rowActionDanger")
            delete_btn.setIcon(icon("trash", self._theme.text_faint, 15))
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.setToolTip("Definitief verwijderen")
            delete_btn.clicked.connect(lambda: self._vraag_verwijder_bevestiging(m.id))
            layout.addWidget(delete_btn)
        else:
            archive_btn = QToolButton()
            archive_btn.setProperty("role", "rowAction")
            archive_btn.setIcon(icon("archive", self._theme.text_faint, 15))
            archive_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            archive_btn.setToolTip("Archiveren")
            archive_btn.clicked.connect(lambda: self._archiveren(m.id))
            layout.addWidget(archive_btn)

        layout.addStretch(1)
        return cell

    # ------------------------------------------------------------------
    # Statusacties
    # ------------------------------------------------------------------
    def _archiveren(self, materiaal_id: str) -> None:
        try:
            self.bibliotheek.archiveren(materiaal_id)
        except OngeldigeStatusOvergangError:
            pass
        self._ververs_alles()

    def _heractiveren(self, materiaal_id: str) -> None:
        try:
            self.bibliotheek.heractiveren(materiaal_id)
        except OngeldigeStatusOvergangError:
            pass
        self._ververs_alles()

    def _vraag_verwijder_bevestiging(self, materiaal_id: str) -> None:
        self._confirm_delete_id = materiaal_id
        self._ververs_tabel()

    def _annuleer_verwijderen(self) -> None:
        self._confirm_delete_id = None
        self._ververs_tabel()

    def _verwijder_definitief(self, materiaal_id: str) -> None:
        try:
            self.bibliotheek.verwijderen_definitief(materiaal_id)
        except OngeldigeStatusOvergangError:
            pass
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
        self._drawer_title = QLabel("Nieuw materiaal")
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
        self._status_chip_label = QLabel("Actief")
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

        # objectName's hier zijn puur om de globale stylesheet (theme.py) de
        # viewport-achtergrond expliciet transparant te kunnen laten maken —
        # zónder dat blijft het OS-brede donker/licht-thema van de viewport
        # doorschijnen i.p.v. de eigen licht/donker-instelling van de app.
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
        body_layout.addLayout(self._build_zaagplan_sectie())
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
        save_btn = QPushButton("Materiaal opslaan")
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

    def _field_spin(self, toegestaan_nul: bool = False) -> tuple[QFrame, QDoubleSpinBox]:
        # De native omhoog/omlaag-pijltjes van QDoubleSpinBox blijken met een
        # eigen stylesheet niet betrouwbaar te tekenen (Qt's "driehoek via
        # transparante randen"-truc voor ::up-arrow/::down-arrow rendert hier
        # als een dichtgekleurd blokje i.p.v. een pijl) — dus i.p.v. daarmee
        # te blijven vechten: eigen stap-knoppen met hetzelfde chevron-icoon
        # als de rest van de UI, en de native knoppen van het spinveld uit.
        field = QDoubleSpinBox()
        field.setProperty("role", "fieldSpin")
        field.setRange(0.0 if toegestaan_nul else 0.01, 100000.0)
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
        # Zonder maximumbreedte eist het spinveld (tot 100000.0) meer ruimte
        # dan de 420px-brede drawer heeft voor drie naast elkaar — dat liep
        # in de praktijk over de rand van het paneel.
        wrapper.setMaximumWidth(112)
        wrap_layout = QHBoxLayout(wrapper)
        wrap_layout.setContentsMargins(0, 0, 0, 0)
        wrap_layout.setSpacing(0)
        wrap_layout.addWidget(field, 1)
        wrap_layout.addLayout(stap_kolom)
        return wrapper, field

    def _segmented(self, opties: list[tuple[object, str]]) -> tuple[QWidget, QButtonGroup]:
        # Let op: Qt's dynamic-property-opslag zet een str-Enum (MateriaalType/
        # Nerfrichting zijn beide str-subklassen) terug om naar een kale str
        # zodra je 'm via setProperty/property() laat rondgaan — zelfde val als
        # de eerdere combobox-bug in de test-ui. Daarom hier bewust ``.value``
        # opslaan en bij het uitlezen expliciet terugzetten naar het enum-lid.
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

    def _build_basisgegevens_sectie(self) -> QVBoxLayout:
        section = QVBoxLayout()
        section.setSpacing(10)
        label = QLabel("BASISGEGEVENS")
        label.setProperty("role", "fieldSectionLabel")
        section.addWidget(label)

        section.addWidget(self._field_label("Naam"))
        self._in_naam = self._field_input()
        self._in_naam.setPlaceholderText("bijv. Eiken multiplex 18mm")
        section.addWidget(self._in_naam)

        section.addWidget(self._field_label("Type"))
        type_widget, self._type_group = self._segmented([(MateriaalType.PLAAT, "Plaat"), (MateriaalType.BALK, "Balk")])
        self._type_group.buttonClicked.connect(lambda: self._update_derde_label())
        section.addWidget(type_widget)

        section.addWidget(self._field_label("Materiaalfamilie"))
        self._in_familie = self._field_input()
        self._in_familie.setPlaceholderText("bijv. Eiken multiplex")
        self._familie_completer = QCompleter([])
        self._familie_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._in_familie.setCompleter(self._familie_completer)
        section.addWidget(self._in_familie)
        hint = QLabel("Begin te typen voor bestaande families — een nieuwe naam maakt een nieuwe familie aan.")
        hint.setProperty("role", "fieldHint")
        hint.setWordWrap(True)
        section.addWidget(hint)

        rij1 = QHBoxLayout()
        kol1 = QVBoxLayout()
        kol1.addWidget(self._field_label("Kleur/afwerking"))
        self._in_kleur = self._field_input()
        kol1.addWidget(self._in_kleur)
        rij1.addLayout(kol1)
        kol2 = QVBoxLayout()
        kol2.addWidget(self._field_label("Productcode"))
        self._in_productcode = self._field_input()
        kol2.addWidget(self._in_productcode)
        rij1.addLayout(kol2)
        section.addLayout(rij1)

        rij2 = QHBoxLayout()
        kol3 = QVBoxLayout()
        kol3.addWidget(self._field_label("Leverancier"))
        self._in_leverancier = self._field_input()
        kol3.addWidget(self._in_leverancier)
        rij2.addLayout(kol3)
        kol4 = QVBoxLayout()
        kol4.addWidget(self._field_label("Tags"))
        self._in_tags = self._field_input()
        self._in_tags.setPlaceholderText("komma-gescheiden")
        kol4.addWidget(self._in_tags)
        rij2.addLayout(kol4)
        section.addLayout(rij2)

        return section

    def _build_afmetingen_sectie(self) -> QVBoxLayout:
        section = QVBoxLayout()
        section.setSpacing(10)
        label = QLabel("AFMETINGEN")
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
        kol3 = QVBoxLayout()
        self._derde_label = self._field_label("Dikte (mm)")
        kol3.addWidget(self._derde_label)
        derde_wrap, self._in_derde = self._field_spin()
        kol3.addWidget(derde_wrap)
        rij.addLayout(kol3)
        section.addLayout(rij)
        return section

    def _build_zaagplan_sectie(self) -> QVBoxLayout:
        section = QVBoxLayout()
        section.setSpacing(10)
        label = QLabel("ZAAGPLAN-INSTELLINGEN")
        label.setProperty("role", "fieldSectionLabel")
        section.addWidget(label)

        section.addWidget(self._field_label("Nerfrichting"))
        nerf_widget, self._nerf_group = self._segmented(
            [(Nerfrichting.GEEN, "Geen"), (Nerfrichting.LANGE_ZIJDE, "Lange zijde"), (Nerfrichting.KORTE_ZIJDE, "Korte zijde")]
        )
        section.addWidget(nerf_widget)

        rij = QHBoxLayout()
        kol1 = QVBoxLayout()
        kol1.addWidget(self._field_label("Zaagsnede/kerf-breedte (mm)"))
        kerf_wrap, self._in_kerf = self._field_spin(toegestaan_nul=True)
        self._in_kerf.setValue(4.0)
        kol1.addWidget(kerf_wrap)
        rij.addLayout(kol1)
        kol2 = QVBoxLayout()
        kol2.addWidget(self._field_label("Min. reststukgrootte (mm)"))
        minrest_wrap, self._in_minrest = self._field_spin(toegestaan_nul=True)
        kol2.addWidget(minrest_wrap)
        rij.addLayout(kol2)
        section.addLayout(rij)

        section.addWidget(self._field_label("Randafzaag-marge (mm)"))
        marge_wrap, self._in_marge = self._field_spin(toegestaan_nul=True)
        section.addWidget(marge_wrap)

        section.addWidget(self._field_label("Randafzaag op"))
        self._marge_rand_buttons = self._rand_chip_rij(section)

        section.addWidget(self._field_label("Fabriekskantenband op"))
        self._kanten_rand_buttons = self._rand_chip_rij(section)

        section.addWidget(self._field_label("Mes/groef-notitie"))
        self._in_mesgroef = self._field_input()
        self._in_mesgroef.setPlaceholderText("verder te detailleren")
        section.addWidget(self._in_mesgroef)

        return section

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

    def _update_derde_label(self) -> None:
        type_waarde = MateriaalType(self._type_group.checkedButton().property("waarde"))
        self._derde_label.setText("Dikte (mm)" if type_waarde == MateriaalType.PLAAT else "Hoogte (mm)")

    def _reset_form(self) -> None:
        for veld in (self._in_naam, self._in_familie, self._in_kleur, self._in_productcode, self._in_leverancier, self._in_tags, self._in_mesgroef):
            veld.clear()
        for veld in (self._in_lengte, self._in_breedte, self._in_derde, self._in_minrest):
            veld.setValue(0)
        self._in_kerf.setValue(4.0)
        self._in_marge.setValue(0)
        self._type_group.buttons()[0].setChecked(True)
        self._nerf_group.buttons()[0].setChecked(True)
        for btn in {**self._marge_rand_buttons, **self._kanten_rand_buttons}.values():
            btn.setChecked(False)
        self._update_derde_label()
        self._validation_banner.hide()
        namen = sorted({m.familie for m in self.bibliotheek.lijst() if m.familie})
        self._familie_completer.setModel(QStringListModel(namen, self._familie_completer))

    def _open_drawer(self, materiaal_id: str | None = None) -> None:
        self._reset_form()
        self._bewerk_id = materiaal_id

        if materiaal_id is not None:
            m = self.bibliotheek.ophalen(materiaal_id)
            self._drawer_title.setText("Materiaal bewerken")
            self._in_naam.setText(m.naam)
            self._in_familie.setText(m.familie)
            self._in_kleur.setText(m.kleur_afwerking)
            self._in_productcode.setText(m.productcode)
            self._in_leverancier.setText(m.leverancier)
            self._in_tags.setText(", ".join(m.tags))
            self._in_lengte.setValue(m.lengte)
            self._in_breedte.setValue(m.breedte)
            self._in_derde.setValue(m.derde_afmeting)
            self._in_kerf.setValue(m.kerf)
            self._in_marge.setValue(m.randafzaag_marge)
            self._in_minrest.setValue(m.min_reststukgrootte)
            self._in_mesgroef.setText(m.mes_groef_notitie)
            for btn in self._type_group.buttons():
                btn.setChecked(btn.property("waarde") == m.type)
            for btn in self._nerf_group.buttons():
                btn.setChecked(btn.property("waarde") == m.nerfrichting)
            for rand, btn in self._marge_rand_buttons.items():
                btn.setChecked(rand in m.randafzaag_randen)
            for rand, btn in self._kanten_rand_buttons.items():
                btn.setChecked(rand in m.fabriekskantenband_randen)
            self._update_derde_label()

            is_archived = m.status == MateriaalStatus.GEARCHIVEERD
            self._status_chip_label.setText("Gearchiveerd" if is_archived else "Actief")
            self._status_toggle_btn.setText("Terugzetten naar actief" if is_archived else "Archiveren")
            if is_archived:
                self._status_toggle_action = lambda: (self._heractiveren(m.id), self._sluit_drawer())
            else:
                self._status_toggle_action = lambda: (self._archiveren(m.id), self._sluit_drawer())
            self._status_row.show()
        else:
            self._drawer_title.setText("Nieuw materiaal")
            self._status_row.hide()

        self._drawer.show()
        self._in_naam.setFocus()

    def _sluit_drawer(self) -> None:
        self._drawer.hide()

    def _opslaan(self) -> None:
        type_waarde = MateriaalType(self._type_group.checkedButton().property("waarde"))
        nerf_waarde = Nerfrichting(self._nerf_group.checkedButton().property("waarde"))
        tags = tuple(t.strip() for t in self._in_tags.text().split(",") if t.strip())

        kandidaat = Materiaal(
            id=self._bewerk_id or "",
            naam=self._in_naam.text(),
            type=type_waarde,
            lengte=self._in_lengte.value(),
            breedte=self._in_breedte.value(),
            derde_afmeting=self._in_derde.value(),
            familie=self._in_familie.text().strip(),
            kleur_afwerking=self._in_kleur.text().strip(),
            nerfrichting=nerf_waarde,
            kerf=self._in_kerf.value(),
            randafzaag_marge=self._in_marge.value(),
            randafzaag_randen=frozenset(r for r, b in self._marge_rand_buttons.items() if b.isChecked()),
            min_reststukgrootte=self._in_minrest.value(),
            mes_groef_notitie=self._in_mesgroef.text().strip(),
            fabriekskantenband_randen=frozenset(r for r, b in self._kanten_rand_buttons.items() if b.isChecked()),
            productcode=self._in_productcode.text().strip(),
            leverancier=self._in_leverancier.text().strip(),
            tags=tags,
        )

        fouten = valideer(kandidaat)
        if fouten:
            self._validation_label.setText("• " + "\n• ".join(fouten))
            self._validation_banner.show()
            return

        if self._bewerk_id:
            kandidaat.status = self.bibliotheek.ophalen(self._bewerk_id).status
            self.bibliotheek.bijwerken(kandidaat)
        else:
            self.bibliotheek.toevoegen(kandidaat)
            self._status_filter = MateriaalStatus.ACTIEF

        self._sluit_drawer()
        self._ververs_alles()
