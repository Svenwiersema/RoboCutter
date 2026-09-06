"""Hoofdvenster: het RoboCutter Dashboard, de Projectenbibliotheek, de
materialenbibliotheek, de reststukkenbibliotheek, de
modellenbibliotheek en het Opties/instellingen-scherm, met een echte
VS Code-stijl tabbalk.

Implementeert de architectuur uit ``design/chapters/11-ux-ui.md``: een
donkere "chrome"-header met de hoofdonderdelen (Projecten/
Materialenbibliotheek/Reststukkenbibliotheek/Modellenbibliotheek) en
een tabbalk waarin meerdere tabbladen tegelijk open kunnen staan
(``self._open_tabs``, in volgorde van openen) — klikken op een
hoofdonderdeel opent het als tab (of activeert 'm als al open), en elk
tabblad is te sluiten met een kruisje behalve het vaste
"Dashboard"-tabblad (tabsleutel ``"dashboard"``, opent automatisch bij
opstarten). Losse projecttabbladen (tabsleutel ``f"project:{project_id}"``,
één per geopend project, dus meerdere tegelijk open) tonen
``ProjectDetailPage`` (op basis van de goedgekeurde HTML-mockup
``design/assets/mockups/project-detail-concept.html``) — bereikbaar via
het potlood-icoon in ``projecten_page.py``'s rijen of het aanklikken van
een Dashboard-kaart (``_open_tab_project``). Anders dan de
bibliotheekschermen hieronder worden deze tabbladen bij sluiten ook
echt vernietigd i.p.v. voor altijd in leven te blijven, en zitten ze
niet in de vaste ``_PAGE_TAB``-tabel maar in ``self._project_pages``
(zie ``_tab_titel_icoon`` voor hoe de tabbladtitel dan toch de actuele
projectnaam volgt).

Op Svens verzoek is het onderscheid tussen "Dashboard" (het KPI-/
overzichtsscherm, tabsleutel ``"dashboard"``, inmiddels ook echt
gekoppeld aan ``ProjectenBibliotheek``/``ReststukkenBibliotheek`` i.p.v.
de voormalige ``sample_data.py``-voorbeelddata, geen eigen
navigatieknop — alleen bereikbaar via het vaste tabblad) en "Projecten"
(de échte,
SQLite-opgeslagen projectenbibliotheek — een doorzoekbare/sorteerbare
lijst, zusje van ``materialen_page.py``, tabsleutel ``"projecten"``,
bereikbaar via de "Projecten"-navigatieknop) expliciet gemaakt: vóór
deze wijziging was er maar één "Projecten"-tabblad dat beide rollen
door elkaar vervulde. Materialenbibliotheek, Reststukkenbibliotheek,
Modellenbibliotheek en nu ook Projecten hebben echte, SQLite-opgeslagen
data en kunnen (net als in VS Code) maar in één instantie tegelijk open
staan. Reststukkenbibliotheek (``reststukken_page.py``) is op Svens
verzoek rechtstreeks gebouwd zonder eigen HTML-mockup, als variant van
``materialen_page.py`` — Projecten (``projecten_page.py``) is om
dezelfde reden ("net zoals de materialenbibliotheek", Svens eigen
woorden) ook zonder mockup gebouwd. Modellenbibliotheek
(``modellen_page.py``) kreeg wél een eigen HTML-mockup (goedgekeurd,
incl. twee correcties tijdens het uitwerken: eigen chevron-stapknoppen
i.p.v. onbetrouwbare native pijltjes, en de headerlabel
"Modellenbibliotheek" i.p.v. "Modellen" voor consistentie met de andere
hoofdonderdelen). Instellingen (``instellingen_page.py``) is, op Svens
verzoek, ook zonder mockup gebouwd ("dit moet een simpel ui zijn") en
is bewust geen vijfde hoofdonderdeel in de navigatierij — het is geen
bibliotheekmodule, dus alleen bereikbaar via het schuifknoppen-icoon in
de header, dat het scherm als gewoon (sluitbaar) tabblad opent. Er is
geen aparte thema-toggle-knop meer in de header (op Svens verzoek
verwijderd): thema kiezen ("Licht"/"Donker"/"Systeem", de laatste volgt
Windows' eigen voorkeur via ``theme.resolve_thema``) gebeurt nu
uitsluitend op het Opties-scherm zelf, en past meteen live toe.

De ``MaterialenPage``-/``ReststukkenPage``-/``ModellenPage``-/
``ProjectenPage``-/``InstellingenPage``-instanties blijven bij een
thema-wissel of tabwissel in leven (herbouw kost anders zoektekst/
filters/open paneel) — zie ``_rebuild_content``. Een thema-wijziging
vanuit het Opties-scherm komt binnen via ``_on_instellingen_gewijzigd``:
het scherm heeft de nieuwe waarde dan al zelf opgeslagen, dit hoeft
alleen de rest van de chrome/tabbladen te laten meewisselen.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import QMimeData, QSize, Qt, Signal
from PySide6.QtGui import QDrag, QPainter, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from robocutter.instellingen.beheer import InstellingenBeheer
from robocutter.projecten.models import Project, ProjectStatus
from robocutter.projecten.zaaglijst import bouw_zaaglijst
from robocutter.reststukken.models import ReststukStatus
from robocutter.ui.icons import icon, icon_pixmap
from robocutter.ui.instellingen_page import InstellingenPage
from robocutter.ui.materialen_page import MaterialenPage
from robocutter.ui.modellen_page import ModellenPage
from robocutter.ui.project_detail_page import ProjectDetailPage
from robocutter.ui.projecten_page import ProjectenPage
from robocutter.ui.reststukken_page import ReststukkenPage
from robocutter.ui.theme import Theme, build_stylesheet, resolve_thema
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
    ("Modellenbibliotheek", "cube"),
]
# Alle vier hoofdonderdelen hebben nu een echt scherm; geen None-plekken
# meer nodig in _NAV_PAGE_KEYS (die markering was voor Modellen, dat nu
# ook gebouwd is). "Projecten" opent hier de bibliotheek-lijst
# (ProjectenPage) — niet de Dashboard-tab, die heeft geen eigen
# navigatieknop nodig (zie module-docstring).
_NAV_PAGE_KEYS = ["projecten", "materialen", "reststukken", "modellen"]
_PAGE_TAB = {
    "dashboard": ("Dashboard", "house"),
    "projecten": ("Projecten", "folder"),
    "materialen": ("Materialenbibliotheek", "layers"),
    "reststukken": ("Reststukkenbibliotheek", "recycle"),
    "modellen": ("Modellenbibliotheek", "cube"),
    "instellingen": ("Instellingen", "sliders"),
}


_TAB_MIME_TYPE = "application/x-robocutter-tab"
_SLEEP_DREMPEL = 8  # pixels muisbeweging voordat een klik een sleepactie wordt


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
    i.p.v. het lichte/donkere themakleur die hoort bij het actieve tabblad.

    Op Svens verzoek ook sleepbaar: een niet-vast tabblad kan met de muis
    naar een andere positie in de tabbalk gesleept worden om de volgorde te
    wijzigen (zelfde interactie als VS Code) — via een eigen Qt-drag met
    ``QMimeData`` (i.p.v. Qt's ingebouwde ``QTabBar``-herschikking, die deze
    op maat gebouwde tabbalk niet gebruikt). Het vaste "Dashboard"-tabblad
    is bewust noch sleepbaar, noch een geldig sleepdoel — dat blijft altijd
    vooraan staan (``versleepbaar=False`` voor die ene tab).

    Twee stukjes visuele feedback maken het slepen duidelijker (op Svens
    verzoek, de kale ``QDrag`` zonder aanpassingen liet nauwelijks zien dát
    je aan het slepen was of waar de tab zou landen):
    1. Het brontabblad krijgt tijdens het slepen zelf een halfdoorzichtige
       ``QGraphicsOpacityEffect`` (i.p.v. een stylesheet-``opacity``, die
       Qt's QSS niet ondersteunt) en de sleep-cursor toont een
       halfdoorzichtige momentopname van de tab (``drag.setPixmap``) die met
       de muis meebeweegt — ``drag.exec()`` blokkeert tot de sleep klaar is,
       dus de effect-aan/-uit-volgorde hierboven/-onder die aanroep is veilig.
    2. Het tabblad waar de muis overheen sleept krijgt een gekleurde rand
       aan de kant waar de gesleepte tab zou worden ingevoegd (links/rechts
       van het midden van die tab, zie ``_toon_drop_indicator``) via de
       dynamische property ``dropZijde`` (``theme.py`` tekent daar een
       rand voor) — dit is het "hier komt-ie terecht"-signaal."""

    clicked = Signal()

    def __init__(self, key: str, versleepbaar: bool, on_herschikken, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._key = key
        self._versleepbaar = versleepbaar
        self._on_herschikken = on_herschikken
        self._sleep_start = None
        if versleepbaar:
            self.setAcceptDrops(True)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            self._sleep_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if (
            self._versleepbaar
            and self._sleep_start is not None
            and bool(event.buttons() & Qt.MouseButton.LeftButton)
            and (event.position().toPoint() - self._sleep_start).manhattanLength() >= _SLEEP_DREMPEL
        ):
            hotspot = self._sleep_start
            self._sleep_start = None
            self._start_sleep(hotspot)
        super().mouseMoveEvent(event)

    def _start_sleep(self, hotspot) -> None:
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(_TAB_MIME_TYPE, self._key.encode("utf-8"))
        drag.setMimeData(mime)

        # Halfdoorzichtige "spooktab" die met de cursor meebeweegt, zodat
        # duidelijk is dát en wélke tab je sleept.
        snapshot = self.grab()
        spook = QPixmap(snapshot.size())
        spook.fill(Qt.GlobalColor.transparent)
        painter = QPainter(spook)
        painter.setOpacity(0.7)
        painter.drawPixmap(0, 0, snapshot)
        painter.end()
        drag.setPixmap(spook)
        drag.setHotSpot(hotspot)

        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(0.35)
        self.setGraphicsEffect(effect)
        drag.exec(Qt.DropAction.MoveAction)  # blokkeert tot drop/annuleren
        self.setGraphicsEffect(None)

    def dragEnterEvent(self, event) -> None:
        if self._versleepbaar and event.mimeData().hasFormat(_TAB_MIME_TYPE):
            event.acceptProposedAction()
            self._toon_drop_indicator(event.position().toPoint().x())

    def dragMoveEvent(self, event) -> None:
        if self._versleepbaar and event.mimeData().hasFormat(_TAB_MIME_TYPE):
            event.acceptProposedAction()
            self._toon_drop_indicator(event.position().toPoint().x())

    def dragLeaveEvent(self, event) -> None:
        self._wis_drop_indicator()

    def dropEvent(self, event) -> None:
        zijde = "rechts" if event.position().toPoint().x() > self.width() / 2 else "links"
        self._wis_drop_indicator()
        bron_key = bytes(event.mimeData().data(_TAB_MIME_TYPE)).decode("utf-8")
        self._on_herschikken(bron_key, self._key, zijde)
        event.acceptProposedAction()

    def _toon_drop_indicator(self, cursor_x: float) -> None:
        zijde = "rechts" if cursor_x > self.width() / 2 else "links"
        if self.property("dropZijde") != zijde:
            self.setProperty("dropZijde", zijde)
            self._herpolijst()

    def _wis_drop_indicator(self) -> None:
        if self.property("dropZijde"):
            self.setProperty("dropZijde", "")
            self._herpolijst()

    def _herpolijst(self) -> None:
        # Een dynamische property die in een QSS-attribuutselector wordt
        # gebruikt (hier ``dropZijde``) wordt pas hertekend na een expliciete
        # unpolish/polish — anders blijft de oude rand-status hangen.
        self.style().unpolish(self)
        self.style().polish(self)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RoboCutter")
        self.resize(1360, 860)

        self._instellingen = InstellingenBeheer()
        self._theme: Theme = resolve_thema(self._instellingen.huidige.thema)
        self._nav_buttons: list[QPushButton] = []
        self._open_tabs: list[str] = ["dashboard"]
        self._active_tab: str = "dashboard"
        self._materialen_page = MaterialenPage(self._theme)
        self._reststukken_page = ReststukkenPage(self._materialen_page.bibliotheek, self._theme)
        self._modellen_page = ModellenPage(self._materialen_page.bibliotheek, self._theme)
        self._projecten_page = ProjectenPage(
            self._modellen_page.bibliotheek,
            self._materialen_page.bibliotheek,
            self._theme,
            on_open_project=self._open_tab_project,
        )
        self._instellingen_page = InstellingenPage(self._instellingen, self._theme, self._on_instellingen_gewijzigd)
        # Eén losse, sluitbare ProjectDetailPage per geopend project
        # (tabsleutel f"project:{project_id}") — anders dan de
        # bibliotheekschermen hierboven kunnen hier meerdere tegelijk open
        # staan, en worden ze bij sluiten ook echt vernietigd i.p.v. voor
        # altijd in leven te blijven (zie _close_tab/_rebuild_content).
        self._project_pages: dict[str, ProjectDetailPage] = {}

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
        elif self._active_tab == "modellen":
            workspace.addWidget(self._modellen_page, 1)
        elif self._active_tab == "instellingen":
            workspace.addWidget(self._instellingen_page, 1)
        elif self._active_tab == "projecten":
            workspace.addWidget(self._projecten_page, 1)
        elif self._active_tab in self._project_pages:
            workspace.addWidget(self._project_pages[self._active_tab], 1)
        else:  # "dashboard"
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
                # Voor een toekomstig hoofdonderdeel zonder scherm: knop
                # zichtbaar maar uitgeschakeld i.p.v. hem weg te laten.
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

        settings_button = QToolButton()
        settings_button.setObjectName("ThemeToggle")
        settings_button.setFixedSize(32, 32)
        settings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_button.setToolTip("Instellingen")
        settings_button.setIcon(icon("sliders", self._theme.chrome_text_muted, 17))
        settings_button.clicked.connect(lambda: self._open_tab("instellingen"))
        layout.addWidget(settings_button)

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
            titel, icon_naam = self._tab_titel_icoon(key)
            layout.addWidget(self._build_tab_item(key, titel, icon_naam))
        layout.addStretch(1)

        return strip

    def _tab_titel_icoon(self, key: str) -> tuple[str, str]:
        # Losse projecttabbladen zitten niet in _PAGE_TAB (dat is een vaste
        # tabel voor de hoofdonderdelen) — hun titel volgt de actuele
        # projectnaam uit de bibliotheek, zodat een naamswijziging in het
        # projectdetailtabblad meteen ook hier zichtbaar wordt.
        if key.startswith("project:"):
            project_id = key.split(":", 1)[1]
            try:
                naam = self._projecten_page.bibliotheek.ophalen(project_id).naam
            except KeyError:
                naam = "Verwijderd project"
            return naam, "folder"
        return _PAGE_TAB[key]

    def _build_tab_item(self, key: str, titel: str, icon_naam: str) -> QWidget:
        actief = key == self._active_tab
        sluitbaar = key != "dashboard"

        tab = _KlikbareTab(key, sluitbaar, self._herschik_tab)
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

    def _open_tab_project(self, project_id: str) -> None:
        # Elk project krijgt zijn eigen tabsleutel (i.p.v. de vaste sleutels
        # in _PAGE_TAB), zodat meerdere projecten tegelijk een los,
        # individueel sluitbaar tabblad kunnen hebben — zie
        # project_detail_page.py voor het scherm zelf.
        key = f"project:{project_id}"
        if key not in self._project_pages:
            self._project_pages[key] = ProjectDetailPage(
                project_id,
                self._projecten_page.bibliotheek,
                self._modellen_page.bibliotheek,
                self._materialen_page.bibliotheek,
                self._theme,
                on_gewijzigd=self._on_project_gewijzigd,
                on_open_projecten_tab=lambda: self._open_tab("projecten"),
            )
        if key not in self._open_tabs:
            self._open_tabs.append(key)
        self._active_tab = key
        self._rebuild_content()

    def _on_project_gewijzigd(self) -> None:
        # Anders dan bijv. een thema-wissel raakt dit de projectenlijst zelf
        # (naam/status/samenstelling) — die pagina moet dus expliciet
        # verversen, niet alleen de chrome/tabbladen (die haalt haar data pas
        # weer op bij de volgende _rebuild_content-aanroep, hierna).
        self._projecten_page.ververs()
        self._rebuild_content()

    def _close_tab(self, key: str) -> None:
        if key == "dashboard" or key not in self._open_tabs:
            return
        index = self._open_tabs.index(key)
        was_active = key == self._active_tab
        self._open_tabs.remove(key)
        if was_active:
            self._active_tab = self._open_tabs[max(0, index - 1)]
        if key.startswith("project:"):
            # Anders dan de bibliotheekschermen (die voor altijd in leven
            # blijven, zie _rebuild_content) wordt een projecttabblad bij
            # sluiten ook echt vernietigd — er kunnen er willekeurig veel
            # tegelijk open staan, dus ze blijven laten bestaan zou een
            # sluipend geheugenlek zijn.
            pagina = self._project_pages.pop(key, None)
            if pagina is not None:
                pagina.setParent(None)
                pagina.deleteLater()
        self._rebuild_content()

    def _herschik_tab(self, bron_key: str, doel_key: str, zijde: str = "links") -> None:
        # "dashboard" kan hier nooit als bron/doel binnenkomen (niet
        # versleepbaar, geen geldig sleepdoel, zie _KlikbareTab), maar wordt
        # hier defensief ook nog geweerd zodat het altijd vooraan blijft
        # staan, ook als dat ooit anders aangeroepen wordt.
        if (
            bron_key == doel_key
            or "dashboard" in (bron_key, doel_key)
            or bron_key not in self._open_tabs
            or doel_key not in self._open_tabs
        ):
            return
        self._open_tabs.remove(bron_key)
        # doel_index pas ná het verwijderen opvragen: als bron vóór doel
        # stond, schuift doel's index anders één op en beland je toch aan
        # de verkeerde kant — precies het probleem dat de drop-indicator
        # (links/rechts van het midden van de doeltab) belooft op te lossen.
        doel_index = self._open_tabs.index(doel_key)
        invoeg_index = doel_index if zijde == "links" else doel_index + 1
        self._open_tabs.insert(invoeg_index, bron_key)
        self._rebuild_content()

    # ------------------------------------------------------------------
    # Dashboard-data
    # ------------------------------------------------------------------

    def _dashboard_alle_projecten(self) -> list[Project]:
        return self._projecten_page.bibliotheek.lijst()

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

        alle = self._dashboard_alle_projecten()
        actief = [p for p in alle if not p.gearchiveerd]

        layout.addWidget(self._sidebar_label("Dashboard"))
        overzicht = self._sidebar_item("folder", "Overzicht", checked=True)
        layout.addWidget(overzicht)
        archief = self._sidebar_item("archive", "Archief", count=sum(1 for p in alle if p.gearchiveerd))
        layout.addWidget(archief)
        layout.addWidget(self._divider())

        layout.addWidget(self._sidebar_label("Snelfilters"))
        filters = [
            (ProjectStatus.WERKVOORBEREIDING, self._theme.neutral_dot),
            (ProjectStatus.IN_PRODUCTIE, self._theme.accent),
            (ProjectStatus.INSTALLATIE, self._theme.indigo),
            (ProjectStatus.AFGEROND, self._theme.success),
        ]
        for status, color in filters:
            count = sum(1 for p in actief if p.status == status)
            layout.addWidget(self._filter_row(status.value, color, count))
        layout.addWidget(self._divider())

        layout.addWidget(self._sidebar_label("Snelacties"))
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
        layout.addStretch(1)

        scroll.setWidget(content)
        return scroll

    def _build_page_head(self) -> QHBoxLayout:
        row = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(3)
        title = QLabel("Dashboard")
        title.setObjectName("PageTitle")
        titles.addWidget(title)
        alle = self._dashboard_alle_projecten()
        actief_count = sum(1 for p in alle if not p.gearchiveerd)
        archief_count = len(alle) - actief_count
        sub = QLabel(f"{len(alle)} projecten · {actief_count} actief · {archief_count} gearchiveerd")
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
        return row

    def _build_stat_row(self) -> QHBoxLayout:
        alle = self._dashboard_alle_projecten()
        actief = [p for p in alle if not p.gearchiveerd]

        vandaag = date.today()
        deze_week = sorted(
            (p for p in actief if p.opleverdatum and vandaag <= p.opleverdatum <= vandaag + timedelta(days=7)),
            key=lambda p: p.opleverdatum,
        )
        if deze_week:
            eerstvolgende = deze_week[0]
            oplevering_sub = f"Eerstvolgende: {eerstvolgende.opleverdatum.isoformat()} · {eerstvolgende.naam}"
        else:
            oplevering_sub = "Geen opleveringen gepland"

        reststukken_beschikbaar = len(self._reststukken_page.bibliotheek.lijst(status=ReststukStatus.BESCHIKBAAR))

        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(StatTile("Actieve projecten", str(len(actief)), "Niet gearchiveerd", "folder", self._theme.accent_text, "neutral"))
        row.addWidget(StatTile("Oplevering deze week", str(len(deze_week)), oplevering_sub, "calendar", self._theme.accent_text, "neutral"))
        row.addWidget(StatTile("Reststukken beschikbaar", str(reststukken_beschikbaar), "In de reststukkenbibliotheek", "recycle", self._theme.success_ink, "good"))
        row.addWidget(StatTile("Totaal projecten", str(len(alle)), "Inclusief archief", "layers", self._theme.accent_text, "neutral"))
        return row

    def _build_toolbar_row(self) -> QHBoxLayout:
        alle = self._dashboard_alle_projecten()
        actief_count = sum(1 for p in alle if not p.gearchiveerd)
        archief_count = len(alle) - actief_count

        row = QHBoxLayout()
        segmented = QWidget()
        segmented.setObjectName("Segmented")
        seg_layout = QHBoxLayout(segmented)
        seg_layout.setContentsMargins(2, 2, 2, 2)
        seg_layout.setSpacing(2)
        seg_group = QButtonGroup(self)
        labels = [f"Alle · {len(alle)}", f"Actief · {actief_count}", f"Archief · {archief_count}"]
        for index, label in enumerate(labels):
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
        projecten = self._projecten_page.bibliotheek.lijst(gearchiveerd=False)
        grid = QGridLayout()
        grid.setSpacing(14)
        columns = 3
        for index, project in enumerate(projecten):
            card = ProjectCard(project, self._theme, on_click=self._open_tab_project)
            grid.addWidget(card, index // columns, index % columns)
        return grid

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _build_status_bar(self) -> None:
        bar = self.statusBar()
        bar.setSizeGripEnabled(False)

        left = QWidget()
        left_layout = QHBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)
        dot = QLabel()
        dot.setObjectName("LiveDot")
        dot.setFixedSize(7, 7)
        left_layout.addWidget(dot)
        left_layout.addWidget(QLabel("Offline modus — lokale database"))
        left_layout.addWidget(QLabel("Laatste back-up: vandaag 06:00"))
        bar.addWidget(left)

        totaal = sum(len(bouw_zaaglijst(p)) for p in self._dashboard_alle_projecten())
        bar.addPermanentWidget(QLabel(f"{totaal} onderdelen totaal"))

    # ------------------------------------------------------------------
    # Thema
    # ------------------------------------------------------------------

    def _on_instellingen_gewijzigd(self) -> None:
        # Het Opties-scherm heeft het thema zelf al opgeslagen via
        # InstellingenBeheer (dezelfde instantie als hier) zodra de
        # gebruiker daar een thema-optie aanklikt (live, geen aparte
        # "Opslaan"-stap voor het thema) — dit hoeft dus alleen de rest van
        # de chrome/tabbladen te laten meewisselen. ``resolve_thema`` lost
        # ook "systeem" op naar de daadwerkelijke Windows-voorkeur van dit
        # moment.
        self._theme = resolve_thema(self._instellingen.huidige.thema)
        self._materialen_page.set_theme(self._theme)
        self._reststukken_page.set_theme(self._theme)
        self._modellen_page.set_theme(self._theme)
        self._projecten_page.set_theme(self._theme)
        self._instellingen_page.set_theme(self._theme)
        for pagina in self._project_pages.values():
            pagina.set_theme(self._theme)
        self._rebuild_content()
        self._apply_theme()

    def _apply_theme(self) -> None:
        self.setStyleSheet(build_stylesheet(self._theme))

    def closeEvent(self, event) -> None:
        self._modellen_page.sluit_verbinding()
        self._reststukken_page.sluit_verbinding()
        self._materialen_page.sluit_verbinding()
        self._projecten_page.sluit_verbinding()
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
        self._modellen_page.setParent(None)
        self._projecten_page.setParent(None)
        self._instellingen_page.setParent(None)
        for pagina in self._project_pages.values():
            pagina.setParent(None)
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
