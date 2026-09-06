"""Projectenbibliotheek-tabblad: de PySide6-uitwerking van het echte
Projecten-scherm, op Svens expliciete verzoek rechtstreeks gebouwd
zonder eigen HTML-mockup ("net zoals met materiaalbibliotheek") — dus
een variant van ``materialen_page.py``: zijbalk met Overzicht/Archief
en status-snelfilters, een doorzoekbare/sorteerbare tabel, en een
uitklapbaar paneel (geen pop-up) om een project toe te voegen of de
basisgegevens te bewerken.

Bewust nog GEEN model-instanties/losse-onderdelen-beheer of
zaaglijst-view in dit paneel — dat hoort bij het latere, aparte
detailtabblad per project (met eigen HTML-mockup, zie
``main_window.py``'s moduledocstring) waarin je een project ook
daadwerkelijk kunt samenstellen. Dit scherm dekt voorlopig alleen de
CRUD- en archiveerworkflow uit hoofdstuk 1/4 (klantgegevens, status,
planning), zodat de projectenbibliotheek al bruikbaar is vóórdat dat
rijkere scherm er is.

Opslag: lokaal SQLite-bestand (``robocutter.instellingen.beheer.
InstellingenBeheer().effectieve_db_pad()``), eigen ``projecten``-tabel
in hetzelfde bestand als de andere bibliotheken. Deelt de
``ModellenBibliotheek``/``MaterialenBibliotheek``-instanties van
``main_window.py`` (nodig voor het model-snapshot-mechanisme en
materiaal-validatie van losse onderdelen) i.p.v. eigen verbindingen te
openen.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QEvent, Qt, QSize, QTimer
from PySide6.QtWidgets import (
    QComboBox,
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

from robocutter.instellingen.beheer import InstellingenBeheer
from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.modellen.bibliotheek import ModellenBibliotheek
from robocutter.projecten.bibliotheek import (
    OngeldigeStatusOvergangError,
    ProjectenBibliotheek,
    valideer,
)
from robocutter.projecten.models import Project, ProjectStatus
from robocutter.projecten.opslag import open_verbinding
from robocutter.ui.icons import icon
from robocutter.ui.theme import Theme

# Zelfde chip-namen/kleuren als widgets/project_card.py (Dashboard), voor
# visuele consistentie tussen Dashboard en de echte Projectenbibliotheek —
# hier lokaal gedupliceerd, net als de andere pagina's hun helpers niet
# delen (zie CLAUDE.md).
_STATUS_CHIP = {
    ProjectStatus.WERKVOORBEREIDING: ("prep", "neutral_dot"),
    ProjectStatus.IN_PRODUCTIE: ("production", "accent"),
    ProjectStatus.INSTALLATIE: ("install", "indigo"),
    ProjectStatus.AFGEROND: ("done", "success"),
}
_KOLOMBREEDTES = [220, 150, 140, 130, 110, 190, 90]
_SORT_OPTIES = [
    ("naam", "Sorteren op naam"),
    ("klant", "Sorteren op klant"),
    ("status", "Sorteren op status"),
    ("opleverdatum", "Sorteren op opleverdatum"),
]
_DRAWER_BREEDTE = 420
_PROJECT_KOLOM_MIN = 190


def _sample_projecten() -> list[Project]:
    return [
        Project(
            id="", naam="Keuken Jansen", klant="Fam. Jansen", contactpersoon="Piet Jansen",
            email="p.jansen@example.com", telefoon="06-12345678", opdrachtnummer="OP-2026-014",
            status=ProjectStatus.IN_PRODUCTIE,
        ),
        Project(
            id="", naam="Inbouwkast Willemsen", klant="R. Willemsen", opdrachtnummer="OP-2026-021",
            status=ProjectStatus.WERKVOORBEREIDING,
        ),
        Project(
            id="", naam="Kantoorkast Smits", klant="Smits Advocatuur", contactpersoon="L. Smits",
            opdrachtnummer="OP-2025-098", status=ProjectStatus.AFGEROND,
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


def _datum_tekst(d: date | None) -> str:
    return d.isoformat() if d is not None else "—"


class ProjectenPage(QWidget):
    def __init__(
        self,
        modellen: ModellenBibliotheek,
        materialen: MaterialenBibliotheek,
        theme: Theme,
        on_open_project=None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._theme = theme
        self._materialen = materialen
        # Op Svens verzoek opent het potlood-icoon in een rij nu het losse
        # projectdetailtabblad (project_detail_page.py) i.p.v. dit paneel in
        # bewerk-modus — dit paneel blijft wel de manier om een NIEUW project
        # aan te maken. Optioneel/None zodat dit bestand ook zonder
        # main_window.py bruikbaar blijft (bv. toekomstige tests).
        self._on_open_project = on_open_project

        db_pad = InstellingenBeheer().effectieve_db_pad()
        db_pad.parent.mkdir(parents=True, exist_ok=True)
        self._db = open_verbinding(db_pad)
        self.bibliotheek = ProjectenBibliotheek(modellen, materialen, self._db)
        if not self.bibliotheek.lijst():
            for project in _sample_projecten():
                self.bibliotheek.toevoegen(project)
            afgerond_project = next(p for p in self.bibliotheek.lijst() if p.naam == "Kantoorkast Smits")
            self.bibliotheek.archiveren(afgerond_project.id)

        self._gearchiveerd_filter = False
        self._status_filter: ProjectStatus | None = None
        self._zoekterm = ""
        self._sort = "naam"
        self._confirm_delete_id: str | None = None
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
    # Thema: zelfde bewuste volledige-herbouw-aanpak als materialen_page.py
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

    def ververs(self) -> None:
        """Publiek aanknooppunt zodat main_window.py deze lijst kan laten
        bijwerken nadat een project elders is gewijzigd (bijv. vanuit een
        losse project_detail_page.py-tabblad)."""
        self._ververs_alles()

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

        layout.addWidget(self._sidebar_label("Projecten"))
        self._btn_overzicht = self._sidebar_item("folder", "Overzicht")
        self._btn_overzicht.clicked.connect(lambda: self._zet_gearchiveerd_filter(False))
        layout.addWidget(self._btn_overzicht)
        self._btn_archief = self._sidebar_item("archive", "Archief")
        self._btn_archief.clicked.connect(lambda: self._zet_gearchiveerd_filter(True))
        layout.addWidget(self._btn_archief)
        layout.addWidget(self._divider())

        layout.addWidget(self._sidebar_label("Snelfilters"))
        self._status_filter_rows: dict[ProjectStatus | None, tuple[QPushButton, QLabel]] = {}
        row, count_label = self._filter_row("Alle statussen", self._theme.text_muted)
        row.clicked.connect(lambda checked=False: self._zet_status_filter(None))
        self._status_filter_rows[None] = (row, count_label)
        layout.addWidget(row)
        for status in ProjectStatus:
            _, kleur_attr = _STATUS_CHIP[status]
            row, count_label = self._filter_row(status.value, getattr(self._theme, kleur_attr))
            row.clicked.connect(lambda checked=False, s=status: self._zet_status_filter(s))
            self._status_filter_rows[status] = (row, count_label)
            layout.addWidget(row)
        layout.addWidget(self._divider())

        layout.addWidget(self._sidebar_label("Snelacties"))
        add_action = self._sidebar_item("plus", "Project toevoegen")
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
        title = QLabel("Projecten")
        title.setObjectName("PageTitle")
        titles.addWidget(title)
        self._page_sub = QLabel("")
        self._page_sub.setObjectName("PageSub")
        titles.addWidget(self._page_sub)
        head.addLayout(titles)
        head.addStretch(1)

        self._search = QLineEdit()
        self._search.setObjectName("SearchInput")
        self._search.setPlaceholderText("Zoek op naam, klant, contactpersoon of opdrachtnummer…")
        self._search.setFixedWidth(280)
        self._search.addAction(icon("search", self._theme.text_faint, 15), QLineEdit.ActionPosition.LeadingPosition)
        self._search.setText(self._zoekterm)
        self._search.textChanged.connect(self._zoekterm_gewijzigd)
        head.addWidget(self._search)

        add_btn = QPushButton("  Nieuw project")
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
            ["Project", "Klant", "Status", "Opdrachtnummer", "Oplevering", "Onderdelen", ""]
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Zelfde reden als materialen_page.py: alle kolommen Interactive en de
        # Project-kolom zelf herberekend, i.p.v. een Stretch-kolom die anders
        # onleesbaar smal geknepen wordt zodra het paneel rechts openstaat.
        header = self._table.horizontalHeader()
        header.setStretchLastSection(False)
        for col, breedte in enumerate(_KOLOMBREEDTES):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            self._table.setColumnWidth(col, breedte)
        self._table.installEventFilter(self)
        card_layout.addWidget(self._table)

        self._empty_label = QLabel("Geen projecten gevonden voor deze zoekopdracht/filter.")
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

    def _zet_gearchiveerd_filter(self, gearchiveerd: bool) -> None:
        self._gearchiveerd_filter = gearchiveerd
        self._confirm_delete_id = None
        self._ververs_alles()

    def _zet_status_filter(self, status: ProjectStatus | None) -> None:
        self._status_filter = None if self._status_filter == status else status
        self._ververs_alles()

    # ------------------------------------------------------------------
    # Verversen (in-place, geen volledige herbouw — behoudt focus/scroll)
    # ------------------------------------------------------------------
    def _ververs_alles(self) -> None:
        self._ververs_sidebar()
        self._ververs_tabel()

    def _ververs_sidebar(self) -> None:
        alles = self.bibliotheek.lijst()
        actief_count = sum(1 for p in alles if not p.gearchiveerd)
        archief_count = sum(1 for p in alles if p.gearchiveerd)

        self._btn_overzicht.setStyleSheet(self._sidebar_actief_stylesheet(not self._gearchiveerd_filter))
        self._btn_archief.setStyleSheet(self._sidebar_actief_stylesheet(self._gearchiveerd_filter))
        self._btn_archief.setText(f"  Archief   ·   {archief_count}" if archief_count else "  Archief")

        binnen_weergave = [p for p in alles if p.gearchiveerd == self._gearchiveerd_filter]
        tellingen: dict[ProjectStatus | None, int] = {None: len(binnen_weergave)}
        for status in ProjectStatus:
            tellingen[status] = sum(1 for p in binnen_weergave if p.status == status)
        for waarde, (row, count_label) in self._status_filter_rows.items():
            count_label.setText(str(tellingen[waarde]))
            actief = self._status_filter == waarde
            row.setStyleSheet(
                f"QPushButton {{ background: {self._theme.accent_soft if actief else 'transparent'}; "
                f"border: none; border-radius: 7px; padding: 5px 0; text-align: left; }}"
                f"QPushButton:hover {{ background: {self._theme.surface_hover}; }}"
            )

        self._page_sub.setText(f"{len(alles)} projecten · {actief_count} actief · {archief_count} gearchiveerd")

    def _sidebar_actief_stylesheet(self, actief: bool) -> str:
        if not actief:
            return ""
        return (
            f"QPushButton {{ background: {self._theme.accent_soft}; color: {self._theme.accent_text}; "
            f"font-weight: 600; border: none; border-radius: 7px; padding: 7px 8px; text-align: left; }}"
        )

    def _zichtbare_rijen(self) -> list[Project]:
        rijen = self.bibliotheek.lijst(
            status=self._status_filter, gearchiveerd=self._gearchiveerd_filter, zoekterm=self._zoekterm
        )
        if self._sort == "klant":
            rijen.sort(key=lambda p: p.klant.lower())
        elif self._sort == "status":
            rijen.sort(key=lambda p: (p.status.value, p.naam.lower()))
        elif self._sort == "opleverdatum":
            rijen.sort(key=lambda p: (p.opleverdatum is None, p.opleverdatum or date.min))
        return rijen

    def eventFilter(self, obj, event) -> bool:
        if obj is self._table and event.type() == QEvent.Type.Resize:
            # Zelfde uitstel-truc als materialen_page.py: de viewport-breedte
            # tijdens het Resize-event zelf is vaak nog tussentijds/te klein.
            QTimer.singleShot(0, self._herbereken_project_kolom)
        return super().eventFilter(obj, event)

    def _herbereken_project_kolom(self) -> None:
        andere_kolommen_breedte = sum(_KOLOMBREEDTES[1:])
        beschikbaar = self._table.viewport().width() - andere_kolommen_breedte
        self._table.setColumnWidth(0, max(_PROJECT_KOLOM_MIN, beschikbaar))

    def _ververs_tabel(self) -> None:
        label, _ = next(o for o in _SORT_OPTIES if o[0] == self._sort)
        self._sort_btn.setText(label)

        rijen = self._zichtbare_rijen()
        self._table.clearContents()
        self._table.setRowCount(len(rijen))
        self._table.setVisible(bool(rijen))
        self._empty_label.setVisible(not rijen)

        for row_index, project in enumerate(rijen):
            self._table.setRowHeight(row_index, 56)
            self._table.setCellWidget(row_index, 0, self._cel_project(project))
            self._table.setCellWidget(row_index, 1, self._cel_klant(project))
            self._table.setCellWidget(row_index, 2, self._cel_status(project))
            self._table.setCellWidget(row_index, 3, self._cel_tekst(project.opdrachtnummer or "—"))
            self._table.setCellWidget(row_index, 4, self._cel_tekst(_datum_tekst(project.opleverdatum)))
            self._table.setCellWidget(row_index, 5, self._cel_onderdelen(project))
            self._table.setCellWidget(row_index, 6, self._cel_acties(project))

    def _cel_project(self, p: Project) -> QWidget:
        cell = QWidget()
        layout = QVBoxLayout(cell)
        layout.setContentsMargins(10, 4, 4, 4)
        layout.setSpacing(2)
        naam = QLabel(p.naam)
        naam.setProperty("role", "matName")
        layout.addWidget(naam)
        meta = QLabel(p.contactpersoon or "—")
        meta.setProperty("role", "matMeta")
        layout.addWidget(meta)
        return cell

    def _cel_klant(self, p: Project) -> QWidget:
        return self._cel_tekst(p.klant)

    def _cel_tekst(self, tekst: str) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(4, 4, 4, 4)
        label = QLabel(tekst)
        label.setProperty("role", "dims")
        layout.addWidget(label)
        return cell

    def _cel_status(self, p: Project) -> QWidget:
        if p.gearchiveerd:
            chip_key, dot_color, tekst = "archived", self._theme.text_faint, "Gearchiveerd"
        else:
            chip_key, kleur_attr = _STATUS_CHIP[p.status]
            dot_color, tekst = getattr(self._theme, kleur_attr), p.status.value

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

        wrapper = QWidget()
        wrapper_layout = QHBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(4, 4, 4, 4)
        wrapper_layout.addWidget(chip)
        wrapper_layout.addStretch(1)
        return wrapper

    def _cel_onderdelen(self, p: Project) -> QWidget:
        delen = []
        if p.modelinstanties:
            delen.append(f"{len(p.modelinstanties)} model{'len' if len(p.modelinstanties) != 1 else ''}")
        if p.losse_onderdelen:
            delen.append(f"{len(p.losse_onderdelen)} los")
        return self._cel_tekst(", ".join(delen) if delen else "Nog leeg")

    def _cel_acties(self, p: Project) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(1)

        edit_btn = QToolButton()
        edit_btn.setProperty("role", "rowAction")
        edit_btn.setIcon(icon("pencil", self._theme.text_faint, 15))
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setToolTip("Openen")
        if self._on_open_project is not None:
            edit_btn.clicked.connect(lambda: self._on_open_project(p.id))
        else:
            edit_btn.clicked.connect(lambda: self._open_drawer(p.id))
        layout.addWidget(edit_btn)

        if self._confirm_delete_id == p.id:
            label = QLabel("Definitief verwijderen?")
            label.setProperty("role", "confirmDeleteLabel")
            layout.addWidget(label)
            yes_btn = QToolButton()
            yes_btn.setProperty("role", "confirmYes")
            yes_btn.setIcon(icon("check", "#FFFFFF", 11))
            yes_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            yes_btn.clicked.connect(lambda: self._verwijder_definitief(p.id))
            layout.addWidget(yes_btn)
            no_btn = QToolButton()
            no_btn.setProperty("role", "confirmNo")
            no_btn.setIcon(icon("close", self._theme.text_muted, 11))
            no_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            no_btn.clicked.connect(self._annuleer_verwijderen)
            layout.addWidget(no_btn)
        elif p.gearchiveerd:
            restore_btn = QToolButton()
            restore_btn.setProperty("role", "rowAction")
            restore_btn.setIcon(icon("recycle", self._theme.text_faint, 15))
            restore_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            restore_btn.setToolTip("Terugzetten naar actief")
            restore_btn.clicked.connect(lambda: self._heractiveren(p.id))
            layout.addWidget(restore_btn)

            delete_btn = QToolButton()
            delete_btn.setProperty("role", "rowActionDanger")
            delete_btn.setIcon(icon("trash", self._theme.text_faint, 15))
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.setToolTip("Definitief verwijderen")
            delete_btn.clicked.connect(lambda: self._vraag_verwijder_bevestiging(p.id))
            layout.addWidget(delete_btn)
        elif p.status == ProjectStatus.AFGEROND:
            archive_btn = QToolButton()
            archive_btn.setProperty("role", "rowAction")
            archive_btn.setIcon(icon("archive", self._theme.text_faint, 15))
            archive_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            archive_btn.setToolTip("Archiveren")
            archive_btn.clicked.connect(lambda: self._archiveren(p.id))
            layout.addWidget(archive_btn)

        layout.addStretch(1)
        return cell

    # ------------------------------------------------------------------
    # Statusacties
    # ------------------------------------------------------------------
    def _archiveren(self, project_id: str) -> None:
        try:
            self.bibliotheek.archiveren(project_id)
        except OngeldigeStatusOvergangError:
            pass
        self._ververs_alles()

    def _heractiveren(self, project_id: str) -> None:
        try:
            self.bibliotheek.heractiveren(project_id)
        except OngeldigeStatusOvergangError:
            pass
        self._ververs_alles()

    def _vraag_verwijder_bevestiging(self, project_id: str) -> None:
        self._confirm_delete_id = project_id
        self._ververs_tabel()

    def _annuleer_verwijderen(self) -> None:
        self._confirm_delete_id = None
        self._ververs_tabel()

    def _verwijder_definitief(self, project_id: str) -> None:
        try:
            self.bibliotheek.verwijderen_definitief(project_id)
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
        self._drawer_title = QLabel("Nieuw project")
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
        status_layout.addWidget(QLabel("Archief"))
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

        scroll = QScrollArea()
        scroll.setObjectName("DrawerScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        body.setObjectName("DrawerBody")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(18, 0, 18, 12)
        body_layout.setSpacing(20)
        body_layout.addLayout(self._build_klantgegevens_sectie())
        body_layout.addLayout(self._build_planning_sectie())
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
        save_btn = QPushButton("Project opslaan")
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

    def _build_klantgegevens_sectie(self) -> QVBoxLayout:
        section = QVBoxLayout()
        section.setSpacing(10)
        label = QLabel("PROJECT- EN KLANTGEGEVENS")
        label.setProperty("role", "fieldSectionLabel")
        section.addWidget(label)

        section.addWidget(self._field_label("Projectnaam"))
        self._in_naam = self._field_input()
        self._in_naam.setPlaceholderText("bijv. Keuken Jansen")
        section.addWidget(self._in_naam)

        section.addWidget(self._field_label("Klant"))
        self._in_klant = self._field_input()
        section.addWidget(self._in_klant)

        rij1 = QHBoxLayout()
        kol1 = QVBoxLayout()
        kol1.addWidget(self._field_label("Contactpersoon"))
        self._in_contactpersoon = self._field_input()
        kol1.addWidget(self._in_contactpersoon)
        rij1.addLayout(kol1)
        kol2 = QVBoxLayout()
        kol2.addWidget(self._field_label("Opdrachtnummer"))
        self._in_opdrachtnummer = self._field_input()
        kol2.addWidget(self._in_opdrachtnummer)
        rij1.addLayout(kol2)
        section.addLayout(rij1)

        rij2 = QHBoxLayout()
        kol3 = QVBoxLayout()
        kol3.addWidget(self._field_label("E-mail"))
        self._in_email = self._field_input()
        kol3.addWidget(self._in_email)
        rij2.addLayout(kol3)
        kol4 = QVBoxLayout()
        kol4.addWidget(self._field_label("Telefoon"))
        self._in_telefoon = self._field_input()
        kol4.addWidget(self._in_telefoon)
        rij2.addLayout(kol4)
        section.addLayout(rij2)

        return section

    def _build_planning_sectie(self) -> QVBoxLayout:
        section = QVBoxLayout()
        section.setSpacing(10)
        label = QLabel("STATUS EN PLANNING")
        label.setProperty("role", "fieldSectionLabel")
        section.addWidget(label)

        section.addWidget(self._field_label("Status"))
        # Combobox i.p.v. een segmented control: de vier statuslabels
        # ("Werkvoorbereiding" voorop) zijn te lang om naast elkaar in het
        # 420px-brede paneel te passen zonder de drawer horizontaal te laten
        # scrollen — zelfde reden waarom de ruwe test-ui hier ook al een
        # QComboBox gebruikte i.p.v. de segmented control van de andere
        # bibliotheekschermen.
        self._in_status = QComboBox()
        self._in_status.setProperty("role", "field")
        for status in ProjectStatus:
            # Str-Enum-valkuil (zie materialen_page.py::_segmented): bewust
            # ``.value`` opslaan i.p.v. het enum-lid zelf.
            self._in_status.addItem(status.value, status.value)
        section.addWidget(self._in_status)

        rij = QHBoxLayout()
        kol1 = QVBoxLayout()
        kol1.addWidget(self._field_label("Startdatum"))
        self._in_startdatum = self._field_input()
        self._in_startdatum.setPlaceholderText("jjjj-mm-dd")
        kol1.addWidget(self._in_startdatum)
        rij.addLayout(kol1)
        kol2 = QVBoxLayout()
        kol2.addWidget(self._field_label("Opleverdatum"))
        self._in_opleverdatum = self._field_input()
        self._in_opleverdatum.setPlaceholderText("jjjj-mm-dd")
        kol2.addWidget(self._in_opleverdatum)
        rij.addLayout(kol2)
        section.addLayout(rij)

        return section

    def _parse_datum(self, tekst: str) -> tuple[date | None, str | None]:
        """Geeft (datum, foutmelding) terug — precies één daarvan is None."""
        tekst = tekst.strip()
        if not tekst:
            return None, None
        try:
            return date.fromisoformat(tekst), None
        except ValueError:
            return None, f"Ongeldige datum {tekst!r} (verwacht jjjj-mm-dd)."

    def _reset_form(self) -> None:
        for veld in (
            self._in_naam, self._in_klant, self._in_contactpersoon, self._in_email,
            self._in_telefoon, self._in_opdrachtnummer, self._in_startdatum, self._in_opleverdatum,
        ):
            veld.clear()
        self._in_status.setCurrentIndex(0)
        self._validation_banner.hide()

    def _open_drawer(self, project_id: str | None = None) -> None:
        self._reset_form()
        self._bewerk_id = project_id

        if project_id is not None:
            p = self.bibliotheek.ophalen(project_id)
            self._drawer_title.setText("Project bewerken")
            self._in_naam.setText(p.naam)
            self._in_klant.setText(p.klant)
            self._in_contactpersoon.setText(p.contactpersoon)
            self._in_email.setText(p.email)
            self._in_telefoon.setText(p.telefoon)
            self._in_opdrachtnummer.setText(p.opdrachtnummer)
            self._in_startdatum.setText(p.startdatum.isoformat() if p.startdatum else "")
            self._in_opleverdatum.setText(p.opleverdatum.isoformat() if p.opleverdatum else "")
            index = self._in_status.findData(p.status.value)
            if index >= 0:
                self._in_status.setCurrentIndex(index)

            self._status_chip_label.setText("Gearchiveerd" if p.gearchiveerd else "Actief")
            if p.gearchiveerd:
                self._status_toggle_btn.setText("Terugzetten naar actief")
                self._status_toggle_btn.setEnabled(True)
                self._status_toggle_btn.setToolTip("")
                self._status_toggle_action = lambda: (self._heractiveren(p.id), self._sluit_drawer())
            else:
                self._status_toggle_btn.setText("Archiveren")
                kan_archiveren = p.status == ProjectStatus.AFGEROND
                self._status_toggle_btn.setEnabled(kan_archiveren)
                self._status_toggle_btn.setToolTip(
                    "" if kan_archiveren else "Alleen mogelijk vanuit status Afgerond"
                )
                self._status_toggle_action = lambda: (self._archiveren(p.id), self._sluit_drawer())
            self._status_row.show()
        else:
            self._drawer_title.setText("Nieuw project")
            self._status_row.hide()

        self._drawer.show()
        self._in_naam.setFocus()

    def _sluit_drawer(self) -> None:
        self._drawer.hide()

    def _opslaan(self) -> None:
        status_waarde = ProjectStatus(self._in_status.currentData())
        startdatum, fout_start = self._parse_datum(self._in_startdatum.text())
        opleverdatum, fout_op = self._parse_datum(self._in_opleverdatum.text())
        datum_fouten = [f for f in (fout_start, fout_op) if f]

        bestaand = self.bibliotheek.ophalen(self._bewerk_id) if self._bewerk_id else None
        kandidaat = Project(
            id=self._bewerk_id or "",
            naam=self._in_naam.text(),
            klant=self._in_klant.text(),
            contactpersoon=self._in_contactpersoon.text().strip(),
            email=self._in_email.text().strip(),
            telefoon=self._in_telefoon.text().strip(),
            opdrachtnummer=self._in_opdrachtnummer.text().strip(),
            startdatum=startdatum,
            opleverdatum=opleverdatum,
            status=status_waarde,
            gearchiveerd=bestaand.gearchiveerd if bestaand else False,
            modelinstanties=bestaand.modelinstanties if bestaand else [],
            losse_onderdelen=bestaand.losse_onderdelen if bestaand else [],
        )

        fouten = datum_fouten + valideer(kandidaat, self._materialen)
        if fouten:
            self._validation_label.setText("• " + "\n• ".join(fouten))
            self._validation_banner.show()
            return

        if self._bewerk_id:
            self.bibliotheek.bijwerken(kandidaat)
        else:
            self.bibliotheek.toevoegen(kandidaat)
            self._gearchiveerd_filter = False

        self._sluit_drawer()
        self._ververs_alles()
