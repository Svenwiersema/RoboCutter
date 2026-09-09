"""Kleuren en stylesheet (QSS) voor de RoboCutter-UI.

Tokens zijn 1-op-1 overgenomen uit de goedgekeurde HTML-conceptmockup van de
home pagina, die op zijn beurt is gebaseerd op de kleurafspraken uit
``design/chapters/11-ux-ui.md`` (accent #5F7FFF, licht/donker thema,
pastelachtige statuskleuren). De "chrome" (header, tabbalk, statusbalk)
blijft bewust altijd donker, ook in het lichte thema — zoals in de
conceptmockup uit hoofdstuk 11 (VS Code-stijl chrome versus een themebare
werkruimte).
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import Qt


@dataclass(frozen=True)
class Theme:
    naam: str

    bg: str
    surface: str
    surface_2: str
    surface_hover: str
    border: str
    text: str
    text_muted: str
    text_faint: str

    accent: str
    accent_text: str
    accent_soft: str
    accent_soft_border: str

    success: str
    success_ink: str
    success_soft: str
    warning: str
    warning_ink: str
    warning_soft: str
    critical: str
    critical_soft: str
    neutral_dot: str
    indigo: str
    indigo_soft: str

    # Chrome-kleuren zijn in beide thema's gelijk.
    chrome_bg: str = "#16171D"
    chrome_bg_raised: str = "#1D1F27"
    chrome_text: str = "#E7E8EE"
    chrome_text_muted: str = "#8B8FA3"
    chrome_border: str = "#2B2D37"
    chrome_active_bg: str = "rgba(95, 127, 255, 46)"


LICHT = Theme(
    naam="licht",
    bg="#F2F3F4",
    surface="#FFFFFF",
    surface_2="#F7F8FB",
    surface_hover="#ECEEF3",
    border="#E1E3EA",
    text="#1E2028",
    text_muted="#676B7D",
    text_faint="#9297A8",
    accent="#5F7FFF",
    accent_text="#4C63E0",
    accent_soft="#EBEFFF",
    accent_soft_border="#CDD6FF",
    success="#4FA875",
    success_ink="#1E5E3B",
    success_soft="#E7F7EE",
    warning="#B5872A",
    warning_ink="#7A5A15",
    warning_soft="#FBF1DC",
    critical="#C74F4F",
    critical_soft="#FBEAEA",
    neutral_dot="#9297A8",
    indigo="#7B6FE0",
    indigo_soft="#EFEDFB",
)

DONKER = Theme(
    naam="donker",
    bg="#1B1D24",
    surface="#23252F",
    surface_2="#2A2C38",
    surface_hover="#30323F",
    border="#383A47",
    text="#EDEEF3",
    text_muted="#A7ABBE",
    text_faint="#767B90",
    accent="#6D8AFF",
    accent_text="#9DB0FF",
    accent_soft="#2A2F52",
    accent_soft_border="#40447A",
    success="#6FCF97",
    success_ink="#BFF0D4",
    success_soft="#1D3226",
    warning="#E8B84B",
    warning_ink="#F6DFA9",
    warning_soft="#382C13",
    critical="#E57373",
    critical_soft="#3A2020",
    neutral_dot="#767B90",
    indigo="#A79CFF",
    indigo_soft="#2C2A4D",
)


def systeem_is_donker() -> bool:
    """Vraagt Windows' systeembrede licht/donker-voorkeur op via Qt's
    ``styleHints`` (Qt 6.5+). Onbekend/geen voorkeur telt als licht."""
    return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark


def resolve_thema(waarde: str) -> Theme:
    """Zet een opgeslagen ``Instellingen.thema``-waarde ("licht"/"donker"/
    "systeem") om in het daadwerkelijk te gebruiken ``Theme``-object. Bij
    "systeem" wordt de OS-voorkeur op het moment van aanroepen gebruikt —
    er is geen live-volgen van een OS-thema-wissel terwijl de app open
    staat, dat is voor een latere iteratie."""
    if waarde == "systeem":
        return DONKER if systeem_is_donker() else LICHT
    return DONKER if waarde == "donker" else LICHT


def build_stylesheet(t: Theme) -> str:
    """Bouwt de volledige Qt-stylesheet voor het gegeven thema."""
    return f"""
    QMainWindow, QWidget#MainScrollContent, QScrollArea#MainScroll {{
        background: {t.bg};
    }}
    QLabel, QCheckBox, QPushButton {{
        font-family: "Inter", "Segoe UI", sans-serif;
        color: {t.text};
    }}

    /* ---------- Chrome: header ---------- */
    QWidget#Header {{
        background: {t.chrome_bg};
        border-bottom: 1px solid {t.chrome_border};
    }}
    QLabel#BrandLabel {{
        color: {t.chrome_text};
        font-size: 15px;
        font-weight: 800;
    }}
    QLabel#BrandMark {{
        background: #F4F5F7;
        border-radius: 8px;
    }}
    QPushButton[role="nav"] {{
        background: transparent;
        color: {t.chrome_text_muted};
        border: none;
        border-radius: 7px;
        padding: 7px 13px;
        font-weight: 600;
        font-size: 13px;
        text-align: left;
    }}
    QPushButton[role="nav"]:hover {{ background: rgba(255, 255, 255, 18); color: {t.chrome_text}; }}
    QPushButton[role="nav"]:checked {{ background: {t.chrome_active_bg}; color: #C7D3FF; }}
    QPushButton[role="nav"]:disabled {{ color: {t.chrome_border}; }}
    QLabel#EditionBadge {{
        color: {t.chrome_text_muted};
        background: rgba(255, 255, 255, 13);
        border: 1px solid {t.chrome_border};
        border-radius: 12px;
        padding: 0 10px;
        font-size: 12px;
        font-weight: 600;
    }}
    QToolButton#ThemeToggle, QToolButton#IconBtn {{
        background: transparent;
        border: none;
        border-radius: 7px;
        color: {t.chrome_text_muted};
    }}
    QToolButton#ThemeToggle:hover {{ background: rgba(255, 255, 255, 18); color: {t.chrome_text}; }}
    QLabel#Avatar {{
        background: {t.accent};
        color: #12141B;
        border-radius: 15px;
        font-weight: 700;
        font-size: 12px;
    }}

    /* ---------- Chrome: tab strip ---------- */
    QWidget#TabStrip {{
        background: {t.chrome_bg_raised};
        border-bottom: 1px solid {t.chrome_border};
    }}
    QWidget#TabItem[active="true"] {{
        background: {t.bg};
        border-right: 1px solid {t.border};
    }}
    QWidget#TabItem[active="false"]:hover {{ background: rgba(255, 255, 255, 8); }}
    QLabel[role="tabLabel"][active="true"] {{ color: {t.text}; font-weight: 600; font-size: 13px; }}
    QLabel[role="tabLabel"][active="false"] {{ color: {t.chrome_text_muted}; font-weight: 500; font-size: 13px; }}
    QLabel#TabDot {{ background: {t.accent}; border-radius: 3px; }}
    /* Sleep-invoegindicator: gekleurde rand aan de kant van een tabblad
       waar de gesleepte tab zou landen (zie MainWindow._herschik_tab). */
    QWidget#TabItem[dropZijde="links"] {{ border-left: 2px solid {t.accent}; }}
    QWidget#TabItem[dropZijde="rechts"] {{ border-right: 2px solid {t.accent}; }}
    QToolButton[role="tabClose"] {{
        background: transparent;
        border: none;
        border-radius: 4px;
        padding: 2px;
    }}
    QToolButton[role="tabClose"]:hover {{ background: rgba(255, 255, 255, 18); }}

    /* ---------- Sidebar ---------- */
    QWidget#Sidebar {{
        background: {t.surface};
        border-right: 1px solid {t.border};
    }}
    QLabel[role="sidebarLabel"] {{
        color: {t.text_faint};
        font-size: 10.5px;
        font-weight: 700;
        letter-spacing: 1px;
    }}
    QPushButton[role="sidebarItem"] {{
        background: transparent;
        border: none;
        border-radius: 7px;
        padding: 7px 8px;
        text-align: left;
        font-size: 13px;
        font-weight: 500;
        color: {t.text_muted};
    }}
    QPushButton[role="sidebarItem"]:hover {{ background: {t.surface_hover}; color: {t.text}; }}
    QPushButton[role="sidebarItem"]:checked {{
        background: {t.accent_soft};
        color: {t.accent_text};
        font-weight: 600;
    }}
    QFrame#SidebarDivider {{ background: {t.border}; max-height: 1px; min-height: 1px; }}
    QCheckBox[role="filter"] {{ font-size: 13px; color: {t.text_muted}; spacing: 8px; }}
    QLabel[role="filterCount"] {{ color: {t.text_faint}; font-size: 11px; }}

    /* ---------- Page head ---------- */
    QLabel#PageTitle {{ font-size: 20px; font-weight: 800; }}
    QLabel#PageSub {{ color: {t.text_muted}; font-size: 13px; }}
    QLineEdit#SearchInput {{
        background: {t.surface};
        border: 1px solid {t.border};
        border-radius: 8px;
        padding: 6px 10px;
        color: {t.text};
        font-size: 13px;
    }}
    QPushButton[role="primary"] {{
        background: {t.accent};
        color: #12141B;
        border: none;
        border-radius: 8px;
        padding: 8px 15px;
        font-weight: 600;
        font-size: 13px;
    }}
    QPushButton[role="primary"]:hover {{ background: {t.accent_text}; color: white; }}
    QPushButton[role="ghost"] {{
        background: {t.surface};
        color: {t.text};
        border: 1px solid {t.border};
        border-radius: 8px;
        padding: 8px 15px;
        font-weight: 600;
        font-size: 13px;
    }}
    QPushButton[role="ghost"]:hover {{ background: {t.surface_hover}; }}

    /* ---------- Stat tiles ---------- */
    QFrame#StatTile {{
        background: {t.surface};
        border: 1px solid {t.border};
        border-radius: 12px;
    }}
    QLabel[role="statLabel"] {{ color: {t.text_muted}; font-size: 12px; font-weight: 600; }}
    QLabel[role="statValue"] {{ font-size: 26px; font-weight: 800; }}
    QLabel[role="statValue"][tone="warn"] {{ color: {t.warning_ink}; }}
    QLabel[role="statFoot"] {{ color: {t.text_faint}; font-size: 11.5px; }}
    QFrame[role="statIcon"][tone="neutral"] {{ background: {t.accent_soft}; color: {t.accent_text}; border-radius: 7px; }}
    QFrame[role="statIcon"][tone="warn"] {{ background: {t.warning_soft}; color: {t.warning_ink}; border-radius: 7px; }}
    QFrame[role="statIcon"][tone="good"] {{ background: {t.success_soft}; color: {t.success_ink}; border-radius: 7px; }}

    /* ---------- Segmented control ---------- */
    QWidget#Segmented {{ background: {t.surface_2}; border: 1px solid {t.border}; border-radius: 8px; }}
    QPushButton[role="segment"] {{
        background: transparent;
        border: none;
        border-radius: 6px;
        padding: 6px 7px;
        font-size: 12px;
        font-weight: 600;
        color: {t.text_muted};
    }}
    QPushButton[role="segment"]:checked {{ background: {t.surface}; color: {t.text}; }}
    QLabel#SortLabel {{ color: {t.text_muted}; font-size: 12.5px; font-weight: 500; }}

    /* ---------- Project cards ---------- */
    QFrame#ProjectCard {{
        background: {t.surface};
        border: 1px solid {t.border};
        border-radius: 13px;
    }}
    QToolButton#AddProjectTile {{
        background: transparent;
        border: 2px dashed {t.border};
        border-radius: 13px;
        color: {t.text_faint};
        font-size: 13px;
        font-weight: 600;
    }}
    QToolButton#AddProjectTile:hover {{
        border-color: {t.accent};
        color: {t.accent_text};
        background: {t.accent_soft};
    }}
    QLabel#CardTitle {{ font-size: 15px; font-weight: 700; }}
    QLabel[role="cardMeta"] {{ color: {t.text_muted}; font-size: 12px; }}

    QFrame[chip="prep"] {{ background: {t.surface_2}; border-radius: 10px; }}
    QFrame[chip="prep"] QLabel {{ color: {t.text_muted}; font-size: 11px; font-weight: 700; }}
    QFrame[chip="production"] {{ background: {t.accent_soft}; border-radius: 10px; }}
    QFrame[chip="production"] QLabel {{ color: {t.accent_text}; font-size: 11px; font-weight: 700; }}
    QFrame[chip="install"] {{ background: {t.indigo_soft}; border-radius: 10px; }}
    QFrame[chip="install"] QLabel {{ color: {t.indigo}; font-size: 11px; font-weight: 700; }}
    QFrame[chip="done"] {{ background: {t.success_soft}; border-radius: 10px; }}
    QFrame[chip="done"] QLabel {{ color: {t.success_ink}; font-size: 11px; font-weight: 700; }}

    /* Statuschip-achtige QComboBox op een Dashboard-projectkaart, zodat
       de status meteen vanaf het Dashboard te wijzigen is (op Svens
       verzoek) — tekstkleur/randkleur worden per instantie inline
       overschreven (zie widgets/project_card.py) met de kleur van de
       HUIDIGE status; deze regel levert alleen de gedeelde vorm. */
    QComboBox[role="cardStatusCombo"] {{
        background: {t.surface_2}; border: 1px solid transparent; border-radius: 10px;
        padding: 3px 8px; font-size: 11px; font-weight: 700;
    }}
    QComboBox[role="cardStatusCombo"]::drop-down {{ border: none; width: 16px; }}
    QComboBox[role="cardStatusCombo"] QAbstractItemView {{
        background: {t.surface}; color: {t.text}; border: 1px solid {t.border};
        selection-background-color: {t.accent_soft}; selection-color: {t.accent_text};
    }}

    /* ---------- Status bar ---------- */
    QStatusBar {{
        background: {t.chrome_bg};
        color: {t.chrome_text_muted};
        border-top: 1px solid {t.chrome_border};
        font-size: 11.5px;
    }}
    QStatusBar QLabel {{ color: {t.chrome_text_muted}; font-size: 11.5px; }}
    QLabel#LiveDot {{ background: {t.success}; border-radius: 3px; }}

    QScrollArea {{ border: none; }}

    /* ---------- Materialen-/reststukkenbibliotheek (gedeelde stijl) ---------- */
    QFrame#TableCard {{ background: {t.surface}; border: 1px solid {t.border}; border-radius: 12px; }}
    QTableWidget#LibraryTable {{
        background: {t.surface};
        border: none;
        gridline-color: transparent;
        font-size: 13px;
        selection-background-color: {t.surface_2};
        selection-color: {t.text};
    }}
    QTableWidget#LibraryTable::item {{ padding: 4px; border-bottom: 1px solid {t.border}; }}
    QTableWidget#LibraryTable QHeaderView::section {{
        background: {t.surface_2};
        color: {t.text_faint};
        font-size: 11px;
        font-weight: 700;
        border: none;
        border-bottom: 1px solid {t.border};
        padding: 8px 10px;
        text-transform: uppercase;
    }}
    QLabel[role="matName"] {{ font-size: 13.5px; font-weight: 700; }}
    QLabel[role="matMeta"] {{ color: {t.text_muted}; font-size: 12px; }}
    QLabel[role="typePill"] {{ color: {t.text_muted}; font-size: 12px; font-weight: 600; }}
    QLabel[role="dims"] {{ font-size: 13px; }}
    QLabel[role="nerf"] {{ color: {t.text_muted}; font-size: 12.5px; }}
    QLabel[role="nerfNone"] {{ color: {t.text_faint}; font-size: 12.5px; }}
    QLabel[role="tagChip"] {{
        background: {t.surface_2}; color: {t.text_muted};
        border-radius: 9px; padding: 2px 8px; font-size: 11px; font-weight: 600;
    }}
    QLabel[role="tagEmpty"] {{ color: {t.text_faint}; font-size: 12px; }}

    QFrame[chip="archived"] {{ background: {t.surface_2}; border-radius: 10px; }}
    QFrame[chip="archived"] QLabel {{ color: {t.text_faint}; font-size: 11px; font-weight: 700; }}

    /* Modellenbibliotheek: aantal-onderdelen-badge en de nesting-badge
       ("bevat N submodellen") in de tabel, en de rijachtergrond voor
       onderdeel-/submodel-rijen in de drawer. */
    QLabel[role="countPill"] {{
        background: {t.surface_2}; color: {t.text_muted}; border: 1px solid {t.border};
        border-radius: 10px; padding: 2px 8px; font-size: 11px; font-weight: 600;
    }}
    QLabel[role="nestingPill"] {{
        background: {t.indigo_soft}; color: {t.indigo}; border-radius: 10px;
        padding: 2px 8px; font-size: 11px; font-weight: 600;
    }}
    QLabel[role="inUseWarning"] {{ color: {t.warning_ink}; font-size: 11px; font-weight: 600; }}
    QFrame[role="subRow"] {{ background: {t.surface_2}; border-radius: 8px; }}

    QToolButton[role="rowAction"] {{
        background: transparent; border: none; border-radius: 6px; color: {t.text_faint};
    }}
    QToolButton[role="rowAction"]:hover {{ background: {t.surface_hover}; color: {t.text}; }}
    QToolButton[role="rowActionDanger"] {{
        background: transparent; border: none; border-radius: 6px; color: {t.text_faint};
    }}
    QToolButton[role="rowActionDanger"]:hover {{ background: {t.critical_soft}; color: {t.critical}; }}
    QLabel[role="confirmDeleteLabel"] {{ color: {t.critical}; font-size: 11.5px; font-weight: 600; }}
    QToolButton[role="confirmYes"] {{
        background: {t.critical}; border: 1px solid {t.critical}; border-radius: 5px; color: white;
    }}
    QToolButton[role="confirmNo"] {{
        background: {t.surface}; border: 1px solid {t.border}; border-radius: 5px; color: {t.text_muted};
    }}

    QLabel[role="sortLabel"] {{ color: {t.text_muted}; font-size: 12.5px; font-weight: 500; }}
    QPushButton[role="sortControl"] {{
        background: transparent; border: none; padding: 4px 6px; border-radius: 6px;
        color: {t.text_muted}; font-size: 12.5px; font-weight: 500; text-align: left;
    }}
    QPushButton[role="sortControl"]:hover {{ background: {t.surface_hover}; color: {t.text}; }}

    /* ---------- Materiaal-drawer (toevoegen/bewerken) ---------- */
    QFrame#Drawer {{
        background: {t.surface};
        border-left: 1px solid {t.border};
    }}
    /* Zonder dit laat de scrollviewport (een ongenoemde QWidget die Qt zelf
       aanmaakt) op Windows het OS-brede donker/licht-thema van de viewport
       zien i.p.v. de eigen kleur van de drawer erboven — leek dan of het
       paneel in het lichte thema toch donker was. */
    QScrollArea#DrawerScroll, QScrollArea#DrawerScroll > QWidget, QWidget#DrawerBody {{
        background: transparent;
        border: none;
    }}
    QLabel#DrawerTitle {{ font-size: 15.5px; font-weight: 800; }}
    QFrame#DrawerStatusRow {{ background: {t.surface_2}; border-bottom: 1px solid {t.border}; }}
    QLabel[role="fieldSectionLabel"] {{
        color: {t.text_faint}; font-size: 10.5px; font-weight: 700; letter-spacing: 0.6px;
    }}
    QLabel[role="fieldLabel"] {{ color: {t.text_muted}; font-size: 12px; font-weight: 600; }}
    QLabel[role="fieldHint"] {{ color: {t.text_faint}; font-size: 11px; }}
    QLineEdit[role="field"], QComboBox[role="field"] {{
        background: {t.surface}; border: 1px solid {t.border}; border-radius: 7px;
        padding: 6px 9px; font-size: 13px; color: {t.text};
    }}
    QLineEdit[role="field"]:focus, QComboBox[role="field"]:focus {{ border-color: {t.accent}; }}
    /* Zonder expliciete stijl hier leunt QComboBox op de (in dit paneel
       bewust transparant gemaakte, zie hierboven) achtergrond van zijn
       voorouders voor zijn eigen "niet expliciet gestileerde" uiterlijk —
       resultaat: een combobox die niets tekent (letterlijk onzichtbaar)
       zodra hij ergens binnen een transparante DrawerScroll/DrawerBody
       staat. Vandaar hier, net als bij de andere velden, een eigen
       ondubbelzinnige achtergrond/rand. */
    QComboBox[role="field"]::drop-down {{ border: none; width: 22px; }}
    QComboBox[role="field"] QAbstractItemView {{
        background: {t.surface}; color: {t.text}; border: 1px solid {t.border};
        selection-background-color: {t.accent_soft}; selection-color: {t.accent_text};
    }}
    /* Getalvelden: Qt's eigen omhoog/omlaag-pijltjes voor QDoubleSpinBox
       tekenen niet betrouwbaar zodra het veld een eigen stylesheet krijgt
       (de "driehoek via transparante randen"-truc voor ::up-arrow/
       ::down-arrow rendert hier als een dichtgekleurd blokje i.p.v. een
       pijl) — vandaar een eigen stap-knoppenkolom met hetzelfde
       chevron-icoon als de rest van de UI (zie materialen_page.py
       ``_field_spin``); de rand/achtergrond zit op de omringende wrapper,
       het spinveld zelf is daarbinnen kaderloos. */
    QFrame[role="fieldSpinWrap"] {{
        background: {t.surface}; border: 1px solid {t.border}; border-radius: 7px;
    }}
    QDoubleSpinBox[role="fieldSpin"], QSpinBox[role="fieldSpin"] {{
        background: transparent; border: none;
        padding: 6px 0 6px 9px; font-size: 13px; color: {t.text};
    }}
    QToolButton[role="spinStep"] {{
        background: transparent; border: none; border-left: 1px solid {t.border};
        padding: 0 4px;
    }}
    QToolButton[role="spinStep"]:hover {{ background: {t.surface_hover}; }}
    QPushButton[role="chipToggle"] {{
        background: {t.surface}; border: 1px solid {t.border}; border-radius: 12px;
        padding: 4px 12px; font-size: 12px; font-weight: 600; color: {t.text_muted};
    }}
    QPushButton[role="chipToggle"]:checked {{
        background: {t.accent_soft}; border-color: {t.accent_soft_border}; color: {t.accent_text};
    }}
    QFrame#ValidationBanner {{
        background: {t.critical_soft}; border: 1px solid {t.critical}; border-radius: 9px;
    }}
    QLabel[role="validationText"] {{ color: {t.critical}; font-size: 12.5px; }}

    /* ---------- Projectdetail-tabblad ---------- */
    QPushButton[role="breadcrumbLink"] {{
        background: transparent; border: none; color: {t.text_faint};
        font-size: 12px; font-weight: 700; text-align: left; padding: 0;
    }}
    QPushButton[role="breadcrumbLink"]:hover {{ color: {t.accent_text}; }}
    QLabel[role="metaText"] {{ color: {t.text_muted}; font-size: 13px; }}
    QLabel[role="sidebarSoon"] {{
        background: {t.surface_2}; color: {t.text_faint}; border-radius: 8px;
        padding: 1px 5px; font-size: 9px; font-weight: 700;
    }}
    QFrame[role="rowIconBox"] {{ background: {t.surface_2}; border-radius: 8px; color: {t.text_muted}; }}
    QFrame[role="rowItem"] {{ background: transparent; border-bottom: 1px solid {t.border}; }}
    QFrame[role="splitAdd"] {{
        background: {t.surface_2}; border-left: 1px solid {t.border};
        border-top-right-radius: 12px; border-bottom-right-radius: 12px;
    }}
    QLabel[role="cardCount"] {{ color: {t.text_faint}; font-size: 12px; font-weight: 600; }}
    QListView#ModelPickerPopup {{
        background: {t.surface}; border: 1px solid {t.border}; border-radius: 8px;
        color: {t.text}; font-size: 13px; padding: 4px;
        selection-background-color: {t.accent_soft}; selection-color: {t.accent_text};
    }}
    QFrame[role="sortLevel"] {{ background: {t.surface}; border: 1px solid {t.border}; border-radius: 8px; }}
    QLabel[role="sortLevelNum"] {{
        background: {t.accent_soft}; color: {t.accent_text}; border-radius: 8px;
        font-size: 9.5px; font-weight: 800;
    }}
    QPushButton[role="addSortLevel"] {{
        background: transparent; border: 1px dashed {t.border}; border-radius: 8px;
        padding: 6px 10px; font-size: 12px; font-weight: 600; color: {t.text_faint};
    }}
    QPushButton[role="addSortLevel"]:hover {{ color: {t.accent_text}; border-color: {t.accent_soft_border}; }}
    QLabel[role="placeholderTitle"] {{ font-size: 16px; font-weight: 800; }}
    QLabel[role="placeholderText"] {{ color: {t.text_muted}; font-size: 13px; }}

    /* ---------- Modeldetail-tabblad ---------- */
    QFrame#ModelDetailFooter {{
        background: {t.surface_2}; border-top: 1px solid {t.border};
    }}

    /* ---------- Zaagplannen-paneel (projectdetail) ---------- */
    QFrame#ZaagplanDocHead {{
        background: {t.chrome_bg}; border-top-left-radius: 12px; border-top-right-radius: 12px;
    }}
    QLabel[role="docTag"] {{ color: {t.chrome_text}; font-size: 12.5px; font-weight: 800; letter-spacing: 0.5px; }}
    QLabel[role="docMeta"] {{ color: {t.chrome_text_muted}; font-size: 12px; }}
    QLabel[role="docMetaStrong"] {{ color: {t.chrome_text}; font-size: 12px; font-weight: 700; }}
    QFrame#ZaagplanPlateWrap {{ background: {t.surface_2}; }}
    QFrame#ZaagplanFooter {{
        background: {t.surface_2}; border-top: 1px solid {t.border};
        border-bottom-left-radius: 12px; border-bottom-right-radius: 12px;
    }}
    QFrame[role="footCell"] {{ border-right: 1px solid {t.border}; }}
    QLabel[role="footLabel"] {{
        color: {t.text_faint}; font-size: 9.5px; font-weight: 700; text-transform: uppercase;
    }}
    QLabel[role="footValue"] {{ color: {t.text}; font-size: 12.5px; font-weight: 700; }}
    QLabel[role="warningText"] {{ color: {t.warning_ink}; font-size: 12.5px; font-weight: 600; }}
    """
