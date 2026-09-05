"""Hoofdvenster: de RoboCutter home pagina (projectenoverzicht), de
materialenbibliotheek en de reststukkenbibliotheek, met een echte
VS Code-stijl tabbalk.

Implementeert de architectuur uit ``design/chapters/11-ux-ui.md``: een
donkere "chrome"-header met de hoofdonderdelen (Projecten/
Materialenbibliotheek/Reststukkenbibliotheek/Modellen) en een tabbalk
waarin meerdere tabbladen tegelijk open kunnen staan (``self._open_tabs``,
in volgorde van openen) — klikken op een hoofdonderdeel opent het als tab
(of activeert 'm als al open), en elk tabblad is te sluiten met een
kruisje behalve het vaste "Projecten"-tabblad. Modellen en losse project-/
modeltabbladen bestaan nog niet als scherm (geen ontwerp/mockup voor) en
zijn dus nog niet op te nemen in de tabbalk. De Projecten-pagina gebruikt
nog vaste voorbeelddata (zie ``sample_data.py``); Materialenbibliotheek en
Reststukkenbibliotheek hebben echte, SQLite-opgeslagen data en kunnen (net
als in VS Code) maar in één instantie tegelijk open staan.
Reststukkenbibliotheek (``reststukken_page.py``) is op Svens verzoek
rechtstreeks gebouwd zonder eigen HTML-mockup, als variant van
``materialen_page.py`` ("praktisch hetzelfde als de materialenbibliotheek").

De ``MaterialenPage``-/``ReststukkenPage``-instanties blijven bij een
thema-wissel of tabwissel in leven (herbouw kost anders zoektekst/
filters/open paneel) — zie ``_rebuild_content`` en ``_toggle_theme``.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from robocutter.ui.icons import icon, icon_pixmap
from robocutter.ui.materialen_page import MaterialenPage
from robocutter.ui.reststukken_page import ReststukkenPage
from robocutter.ui.sample_data import VOORBEELD_PROJECTEN, ProjectStatus
from robocutter.ui.theme import DONKER, LICHT, Theme, build_stylesheet
from robocutter.ui.widgets.project_card import ProjectCard
from robocutter.ui.widgets.stat_tile import StatTile

# De volledige logo-illustratie ("zonder tekst") leest bij 28px niet meer als
# een gezicht (zie design/chapters/11-ux-ui.md); hoofdstuk 11 wijst voor
# precies dit doel — werkbalk/systemtray op klein formaat — daarom
# uitdrukkelijk het vereenvoudigde robotgezicht-icoon aan.
# Pad is relatief aan de repo-root; bij het bundelen met Nuitka (hoofdstuk 8)
# moet dit meeverhuizen naar een gebundelde resource.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_LOGO_ICON_PATH = _REPO_ROOT / "design" / "assets" / "logo" / "robocutter_icon_toolbar.png"

_NAV_ITEMS = [
    ("Projecten", "folder"),
    ("Materialenbibliotheek", "layers"),
    ("Reststukkenbibliotheek", "recycle"),
    ("Modellen", "cube"),
]
# None = hoofdonderdeel nog niet gebouwd (Modellen); de bijbehorende
# navigatieknop is dan uitgeschakeld, zie ``_build_header``.
_NAV_PAGE_KEYS = ["projecten", "materialen", "reststukken", None]
_PAGE_TAB = {
    "projecten": ("Projecten", "folder"),
    "materialen": ("Materialenbibliotheek", "layers"),
    "reststukken": ("Reststukkenbibliotheek", "recycle"),
}


class _KlikbareTab(QWidget):
    """Een QWidget i.p.v. QPushButton als klikbare tab-container: een
    QPushButton berekent zijn sizeHint zelf op basis van tekst/icoon en
    negeert daarbij een eigen child-layout (bleek in de praktijk: een lege
    QPushButton met alleen kind-widgets in een layout kromp naar een paar
    pixels). QWidget geeft die berekening gewoon door aan zijn layout.

    Een eigen QWidget-subklasse schildert zijn ``background:``-regel uit de
    stylesheet niet vanzelf (dat doen alleen QFrame/QPushButton/QLabel e.d.
    standaard) — vandaar hier expliciet ``WA_StyledBackground`` aanzetten,
    anders blijft het actieve tabblad de donkere chrome-achtergrond tonen
    i.p.v. het lichte/donkere themakleur die hoort bij het actieve tabblad."""

    clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RoboCutter")
        self.resize(1360, 860)

        self._theme: Theme = LICHT
        self._nav_buttons: list[QPushButton] = []
        self._open_tabs: list[str] = ["projecten"]
        self._active_tab: str = "projecten"
        self._materialen_page = MaterialenPage(self._theme)
        self._reststukken_page = ReststukkenPage(self._materialen_page.bibliotheek, self._theme)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())
        root.addWidget(self._build_tab_strip())
        root.addLayout(self._build_workspace(), 1)

        self._build_status_bar()
        self._apply_theme()

    def _build_workspace(self) -> QHBoxLayout:
        workspace = QHBoxLayout()
        workspace.setContentsMargins(0, 0, 0, 0)
        workspace.setSpacing(0)
        if self._active_tab == "materialen":
            workspace.addWidget(self._materialen_page, 1)
        elif self._active_tab == "reststukken":
            workspace.addWidget(self._reststukken_page, 1)
        else:
            workspace.addWidget(self._build_sidebar())
            workspace.addWidget(self._build_main(), 1)
        return workspace

    # ------------------------------------------------------------------
    # Chrome: header
    # ------------------------------------------------------------------

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("Header")
        header.setFixedHeight(52)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(18, 0, 18, 0)
        layout.setSpacing(28)

        brand = QHBoxLayout()
        brand.setSpacing(9)
        mark = QLabel()
        mark.setObjectName("BrandMark")
        mark.setFixedSize(28, 28)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setPixmap(
            QPixmap(str(_LOGO_ICON_PATH)).scaled(
                20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
        )
        brand.addWidget(mark)
        name = QLabel('Robo<span style="color: #8CA0FF;">Cutter</span>')
        name.setObjectName("BrandLabel")
        name.setTextFormat(Qt.TextFormat.RichText)
        brand.addWidget(name)
        brand_widget = QWidget()
        brand_widget.setLayout(brand)
        layout.addWidget(brand_widget)

        nav = QHBoxLayout()
        nav.setSpacing(2)
        group = QButtonGroup(self)
        group.setExclusive(True)
        for index, (label, icon_name) in enumerate(_NAV_ITEMS):
            page_key = _NAV_PAGE_KEYS[index]
            button = QPushButton(f"  {label}")
            button.setProperty("role", "nav")
            button.setCheckable(True)
            button.setIcon(icon(icon_name, "#8B8FA3", 15))
            button.setIconSize(QSize(15, 15))
            if page_key is not None:
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                button.setChecked(page_key == self._active_tab)
                button.clicked.connect(lambda checked=False, key=page_key: self._open_tab(key))
            else:
                # Modellen: nog niet gebouwd.
                button.setEnabled(False)
                button.setToolTip("Nog niet gebouwd")
            group.addButton(button)
            nav.addWidget(button)
            self._nav_buttons.append(button)
        nav.addStretch(1)
        nav_widget = QWidget()
        nav_widget.setLayout(nav)
        layout.addWidget(nav_widget, 1)

        edition = QLabel("Editie: Pro")
        edition.setObjectName("EditionBadge")
        edition.setFixedHeight(24)
        edition.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(edition)

        theme_toggle = QToolButton()
        theme_toggle.setObjectName("ThemeToggle")
        theme_toggle.setFixedSize(32, 32)
        theme_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        theme_toggle.setIcon(icon("sun" if self._theme is DONKER else "moon", self._theme.chrome_text_muted, 17))
        theme_toggle.clicked.connect(self._toggle_theme)
        layout.addWidget(theme_toggle)

        avatar = QLabel("SW")
        avatar.setObjectName("Avatar")
        avatar.setFixedSize(30, 30)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(avatar)

        return header

    # ------------------------------------------------------------------
    # Chrome: tab strip
    # ------------------------------------------------------------------

    def _build_tab_strip(self) -> QWidget:
        strip = QWidget()
        strip.setObjectName("TabStrip")
        strip.setFixedHeight(38)
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(0)

        for key in self._open_tabs:
            titel, icon_naam = _PAGE_TAB[key]
            layout.addWidget(self._build_tab_item(key, titel, icon_naam))
        layout.addStretch(1)

        return strip

    def _build_tab_item(self, key: str, titel: str, icon_naam: str) -> QWidget:
        actief = key == self._active_tab
        sluitbaar = key != "projecten"

        tab = _KlikbareTab()
        tab.setObjectName("TabItem")
        tab.setProperty("active", "true" if actief else "false")
        tab.setCursor(Qt.CursorShape.PointingHandCursor)
        tab.clicked.connect(lambda: self._activate_tab(key))
        tab_layout = QHBoxLayout(tab)
        tab_layout.setContentsMargins(14, 0, 8 if sluitbaar else 14, 0)
        tab_layout.setSpacing(8)

        tab_icon = QLabel()
        tab_icon.setPixmap(icon_pixmap(icon_naam, self._theme.text if actief else self._theme.chrome_text_muted, 14))
        tab_icon.setStyleSheet("background: transparent;")
        tab_layout.addWidget(tab_icon)

        tab_label = QLabel(titel)
        tab_label.setProperty("role", "tabLabel")
        tab_label.setProperty("active", "true" if actief else "false")
        tab_label.setStyleSheet("background: transparent;")
        tab_layout.addWidget(tab_label)

        if sluitbaar:
            close_btn = QToolButton()
            close_btn.setProperty("role", "tabClose")
            close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            close_btn.setIcon(icon("close", self._theme.chrome_text_muted, 10))
            close_btn.clicked.connect(lambda: self._close_tab(key))
            tab_layout.addWidget(close_btn)
        elif actief:
            tab_dot = QLabel()
            tab_dot.setObjectName("TabDot")
            tab_dot.setFixedSize(6, 6)
            tab_layout.addWidget(tab_dot)

        return tab

    def _activate_tab(self, key: str) -> None:
        if key == self._active_tab:
            return
        self._active_tab = key
        self._rebuild_content()

    def _open_tab(self, key: str) -> None:
        if key not in self._open_tabs:
            self._open_tabs.append(key)
        self._active_tab = key
        self._rebuild_content()

    def _close_tab(self, key: str) -> None:
        if key == "projecten" or key not in self._open_tabs:
            return
        index = self._open_tabs.index(key)
        was_active = key == self._active_tab
        self._open_tabs.remove(key)
        if was_active:
            self._active_tab = self._open_tabs[max(0, index - 1)]
        self._rebuild_content()

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(216)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(4)

        layout.addWidget(self._sidebar_label("Projecten"))
        overzicht = self._sidebar_item("folder", "Overzicht", checked=True)
        layout.addWidget(overzicht)
        archief = self._sidebar_item("archive", "Archief", count=3)
        layout.addWidget(archief)
        layout.addWidget(self._divider())

        layout.addWidget(self._sidebar_label("Snelfilters"))
        filters = [
            (ProjectStatus.WERKVOORBEREIDING, self._theme.neutral_dot, 2),
            (ProjectStatus.IN_PRODUCTIE, self._theme.accent, 4),
            (ProjectStatus.INSTALLATIE, self._theme.indigo, 3),
            (ProjectStatus.AFGEROND, self._theme.success, 3),
        ]
        for status, color, count in filters:
            layout.addWidget(self._filter_row(status.value, color, count))
        layout.addWidget(self._divider())

        layout.addWidget(self._sidebar_label("Snelacties"))
        layout.addWidget(self._sidebar_item("plus", "Nieuw project"))
        layout.addWidget(self._sidebar_item("upload", "Importeren (DXF)"))

        layout.addStretch(1)
        return sidebar

    def _sidebar_label(self, text: str) -> QLabel:
        label = QLabel(text.upper())
        label.setProperty("role", "sidebarLabel")
        label.setContentsMargins(8, 4, 8, 4)
        return label

    def _sidebar_item(self, icon_name: str, text: str, checked: bool = False, count: int | None = None) -> QWidget:
        button = QPushButton(f"  {text}")
        button.setProperty("role", "sidebarItem")
        button.setCheckable(True)
        button.setChecked(checked)
        button.setIcon(icon(icon_name, self._theme.text_muted, 16))
        button.setIconSize(QSize(16, 16))
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        if count is not None:
            wrapper = QWidget()
            wrapper_layout = QHBoxLayout(wrapper)
            wrapper_layout.setContentsMargins(0, 0, 0, 0)
            wrapper_layout.addWidget(button, 1)
            count_label = QLabel(str(count))
            count_label.setProperty("role", "filterCount")
            wrapper_layout.addWidget(count_label)
            return wrapper
        return button

    def _filter_row(self, text: str, dot_color: str, count: int) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(9)
        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background: {dot_color}; border-radius: 4px;")
        layout.addWidget(dot)
        label = QLabel(text)
        label.setStyleSheet(f"color: {self._theme.text_muted}; font-size: 13px;")
        layout.addWidget(label, 1)
        count_label = QLabel(str(count))
        count_label.setProperty("role", "filterCount")
        layout.addWidget(count_label)
        return row

    def _divider(self) -> QFrame:
        line = QFrame()
        line.setObjectName("SidebarDivider")
        line.setFixedHeight(1)
        line.setContentsMargins(0, 8, 0, 12)
        return line

    # ------------------------------------------------------------------
    # Main content
    # ------------------------------------------------------------------

    def _build_main(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setObjectName("MainScroll")
        scroll.setWidgetResizable(True)

        content = QWidget()
        content.setObjectName("MainScrollContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 22, 28, 32)
        layout.setSpacing(18)

        layout.addLayout(self._build_page_head())
        layout.addLayout(self._build_stat_row())
        layout.addLayout(self._build_toolbar_row())
        layout.addLayout(self._build_project_grid())
        layout.addWidget(self._build_warning_panel())
        layout.addStretch(1)

        scroll.setWidget(content)
        return scroll

    def _build_page_head(self) -> QHBoxLayout:
        row = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(3)
        title = QLabel("Projecten")
        title.setObjectName("PageTitle")
        titles.addWidget(title)
        actief = sum(1 for p in VOORBEELD_PROJECTEN if p.status != ProjectStatus.AFGEROND)
        sub = QLabel(f"{len(VOORBEELD_PROJECTEN)} projecten · {actief} actief · 3 gearchiveerd")
        sub.setObjectName("PageSub")
        titles.addWidget(sub)
        row.addLayout(titles)
        row.addStretch(1)

        search = QLineEdit()
        search.setObjectName("SearchInput")
        search.setPlaceholderText("Zoek op klant, projectnummer…")
        search.setFixedWidth(230)
        search.addAction(icon("search", self._theme.text_faint, 15), QLineEdit.ActionPosition.LeadingPosition)
        row.addWidget(search)

        new_project = QPushButton("  Nieuw project")
        new_project.setProperty("role", "primary")
        new_project.setIcon(icon("plus", "#12141B", 14))
        new_project.setCursor(Qt.CursorShape.PointingHandCursor)
        row.addWidget(new_project)
        return row

    def _build_stat_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(StatTile("Actieve projecten", "9", "2 nieuw deze maand", "folder", self._theme.accent_text, "neutral"))
        row.addWidget(StatTile("Oplevering deze week", "3", "Eerstvolgende: 8 sep · Keuken Jansen", "calendar", self._theme.accent_text, "neutral"))
        row.addWidget(StatTile("Materiaal ontbreekt", "2", "Verspreid over 2 projecten", "warning", self._theme.warning_ink, "warn"))
        row.addWidget(StatTile("Reststukken beschikbaar", "47", "In de reststukkenbibliotheek", "recycle", self._theme.success_ink, "good"))
        return row

    def _build_toolbar_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        segmented = QWidget()
        segmented.setObjectName("Segmented")
        seg_layout = QHBoxLayout(segmented)
        seg_layout.setContentsMargins(2, 2, 2, 2)
        seg_layout.setSpacing(2)
        seg_group = QButtonGroup(self)
        for index, label in enumerate(["Alle · 12", "Actief · 9", "Archief · 3"]):
            btn = QPushButton(label)
            btn.setProperty("role", "segment")
            btn.setCheckable(True)
            btn.setChecked(index == 0)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            seg_group.addButton(btn)
            seg_layout.addWidget(btn)
        row.addWidget(segmented)
        row.addStretch(1)

        sort_row = QHBoxLayout()
        sort_row.setSpacing(6)
        sort_label = QLabel("Sorteren op opleverdatum")
        sort_label.setObjectName("SortLabel")
        sort_row.addWidget(sort_label)
        chevron = QLabel()
        chevron.setPixmap(icon_pixmap("chevron-down", self._theme.text_muted, 12))
        sort_row.addWidget(chevron)
        row.addLayout(sort_row)
        return row

    def _build_project_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(14)
        columns = 3
        for index, project in enumerate(VOORBEELD_PROJECTEN):
            card = ProjectCard(project, self._theme)
            grid.addWidget(card, index // columns, index % columns)

        add_index = len(VOORBEELD_PROJECTEN)
        add_tile = QToolButton()
        add_tile.setObjectName("AddProjectTile")
        add_tile.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        add_tile.setIcon(icon("plus", self._theme.text_faint, 22))
        add_tile.setIconSize(QSize(22, 22))
        add_tile.setText("Nieuw project")
        add_tile.setMinimumHeight(176)
        add_tile.setCursor(Qt.CursorShape.PointingHandCursor)
        add_tile.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        grid.addWidget(add_tile, add_index // columns, add_index % columns)
        return grid

    def _build_warning_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("WarningPanel")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        icon_wrap = QFrame()
        icon_wrap.setObjectName("WarningIconWrap")
        icon_wrap.setFixedSize(30, 30)
        icon_wrap_layout = QHBoxLayout(icon_wrap)
        icon_wrap_layout.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel()
        icon_label.setPixmap(icon_pixmap("warning", "#2B2004", 16))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_wrap_layout.addWidget(icon_label)
        layout.addWidget(icon_wrap, 0, Qt.AlignmentFlag.AlignTop)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        title = QLabel("2 projecten hebben ontbrekend materiaal")
        title.setObjectName("WarningTitle")
        text_col.addWidget(title)
        body = QLabel(
            "Los dit op vóórdat het zaagplan gegenereerd wordt:\n"
            "• Inbouwkast Willemsen — Eiken fineer 19mm\n"
            "• Kantoorkast Smits — MDF gegrond 12mm"
        )
        body.setProperty("role", "warningBody")
        text_col.addWidget(body)
        layout.addLayout(text_col, 1)
        return panel

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _build_status_bar(self) -> None:
        bar = self.statusBar()
        bar.setFixedHeight(26)
        bar.setSizeGripEnabled(False)

        left = QWidget()
        left_layout = QHBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)
        dot = QLabel()
        dot.setObjectName("LiveDot")
        dot.setFixedSize(7, 7)
        offline_row = QHBoxLayout()
        offline_row.setSpacing(6)
        offline_row.addWidget(dot)
        offline_row.addWidget(QLabel("Offline modus — lokale database"))
        offline_widget = QWidget()
        offline_widget.setLayout(offline_row)
        left_layout.addWidget(offline_widget)
        left_layout.addWidget(QLabel("Laatste back-up: vandaag 06:00"))
        bar.addWidget(left)

        totaal = sum(p.modellen_totaal for p in VOORBEELD_PROJECTEN) * 12
        bar.addPermanentWidget(QLabel(f"{totaal} onderdelen totaal"))

    # ------------------------------------------------------------------
    # Thema
    # ------------------------------------------------------------------

    def _toggle_theme(self) -> None:
        self._theme = DONKER if self._theme is LICHT else LICHT
        # De materialen-/reststukkenpagina's beheren hun eigen (zoek/filter/
        # paneel-)status en worden daarom niet zomaar meegesloopt met de rest
        # van het venster; ze herbouwen hier bewust wél hun eigen iconen/
        # kleuren voor het nieuwe thema (zien daarbij wél hun open paneel/
        # zoektekst kwijtraken).
        self._materialen_page.set_theme(self._theme)
        self._reststukken_page.set_theme(self._theme)
        self._rebuild_content()
        self._apply_theme()

    def _apply_theme(self) -> None:
        self.setStyleSheet(build_stylesheet(self._theme))

    def closeEvent(self, event) -> None:
        self._reststukken_page.sluit_verbinding()
        self._materialen_page.sluit_verbinding()
        super().closeEvent(event)

    def _rebuild_content(self) -> None:
        # Sommige elementen (iconen, statuspuntjes) hebben expliciete kleuren
        # nodig die niet via de stylesheet lopen — eenvoudiger om het venster
        # opnieuw op te bouwen dan elk element los bij te werken. De
        # materialen-/reststukkenpagina overleven dit door ze hier los te
        # maken vóórdat de oude central widget (en daarmee al haar kinderen)
        # verwijderd wordt.
        central = self.centralWidget()
        self._materialen_page.setParent(None)
        self._reststukken_page.setParent(None)
        central.deleteLater()
        self._nav_buttons = []
        new_central = QWidget()
        self.setCentralWidget(new_central)
        root = QVBoxLayout(new_central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())
        root.addWidget(self._build_tab_strip())
        root.addLayout(self._build_workspace(), 1)
