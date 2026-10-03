"""Projectdetail-tabblad: de PySide6-uitwerking van de door Sven
goedgekeurde HTML-conceptmockup
(``design/assets/mockups/project-detail-concept.html``). Eén los,
sluitbaar tabblad per geopend project (``MainWindow._open_tab_project``,
tabsleutel ``f"project:{project_id}"``) — anders dan de
bibliotheekschermen kunnen meerdere van deze tabbladen tegelijk open
staan, en worden ze bij sluiten ook echt vernietigd i.p.v. voor altijd
in leven te blijven (zie ``main_window.py``).

Zijbalk (216px, zelfde opzet als ``materialen_page.py``/
``projecten_page.py``) met zes secties: Overzicht/Samenstelling/
Zaaglijst, en onder een "Documenten"-scheiding Labels/Zaagplannen/
Reststukken (dat laatste: zie ``projecten/project_reststukken.py``). Beide
zijn inmiddels echt (geen placeholder meer): Zaagplannen genereert en
bewaart een zaagplan per project (``genereer_zaagplannen_voor_project``/
``ZaagplannenOpslag``), en Labels (hoofdstuk 6) leidt daar op zijn beurt
één label per fysiek geplaatst onderdeel-exemplaar uit af
(``robocutter.projecten.labels.genereer_labels_voor_project``) — dus
altijd "genereer eerst een zaagplan" zolang er nog geen is. De zes
panelen zitten in een ``QStackedWidget`` onder een gedeelde projectkop
(breadcrumb, titel + statuschip, klant-/opdracht-/opleverdatum,
archiveerknop).

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
en heeft dus ook geen ``sluit_verbinding()``. Zelfde voor de gedeelde
``ZaagplannenOpslag`` (zie ``zaagplannen_opslag.py``): het laatst
gegenereerde zaagplan van een project wordt bij het openen van dit
tabblad herladen (i.p.v. altijd leeg te beginnen) en bij elke
(opnieuw-)generatie meteen opgeslagen — op Svens verzoek ("zorg er ook
voor dat zaagplannen binnen een project worden opgeslagen"). Geen
revisiegeschiedenis: alleen de laatste stand overleeft een herstart.
"""

from __future__ import annotations

import math
import sys
import threading
import time
from dataclasses import replace
from datetime import date
from typing import Callable

from PySide6.QtCore import QRectF, QSize, Qt, QStringListModel, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QDoubleValidator, QPainter, QTransform
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QButtonGroup,
    QComboBox,
    QCompleter,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
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
from robocutter.projecten.labels import OnderdeelLabel, genereer_labels_voor_project
from robocutter.projecten.models import Project, ProjectModelInstantie, ProjectStatus
from robocutter.projecten.project_reststukken import (
    AlVrijgegevenError,
    ProjectNietAfgerondError,
    ProjectReststuk,
    ProjectReststukBron,
    ProjectReststukkenBibliotheek,
    ProjectReststukStatus,
)
from robocutter.projecten.zaaglijst import SORTEERSLEUTELS, bouw_zaaglijst, sorteer_zaaglijst
from robocutter.projecten.zaagplannen import PlaatZaagplan, ZaagplanVoortgang, genereer_zaagplannen_voor_project
from robocutter.projecten.zaagplannen_opslag import ZaagplannenOpslag
from robocutter.reststukken.models import Reststuk
from robocutter.ui.icons import icon, icon_pixmap
from robocutter.ui.label_pdf import schrijf_labels_pdf
from robocutter.ui.theme import Theme
from robocutter.ui.widgets.randen_diagram import RandenDiagram
from robocutter.ui.widgets.stat_tile import StatTile
from robocutter.ui.widgets.zaagplaat_widget import ZaagplaatWidget
from robocutter.ui.zaagplan_pdf import schrijf_zaagplannen_pdf
from robocutter.ui.widgets.opslag_melding import OpslagMelding

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
# Beide "Documenten"-items zijn inmiddels echt: Zaagplannen sinds de
# vorige stap, Labels sinds deze stap (zie _build_labels_paneel) — allebei
# leunen op een gegenereerd zaagplan van dit project.
# Reststukken: de tijdelijke reststukkenlijst van dit project (zie
# projecten/project_reststukken.py), ook afgeleid van het zaagplan.
_DOC_ITEMS = [
    ("labels", "tag", "Labels", False),
    ("zaagplannen", "document", "Zaagplannen", False),
    ("reststukken", "recycle", "Reststukken", False),
]
_STRATEGIE_LABEL = {
    "horizontaal": "Horizontaal",
    "verticaal": "Verticaal",
    "guillotine": "Guillotine",
}
# Op Svens verzoek ("dat je dan even moet wachten op het resultaat zodat
# ie goed kijkt waar alle items kunnen ... rekening houdend met de
# zaagstrategie"): de motor probeert extra verwerkingsvolgordes (zie
# engine.genereer_zaagplan's zoek_tijdsbudget) in ruil voor een mogelijk
# beter zaagplan, en stopt zodra _MAX_POGINGEN_ZONDER_VERBETERING pogingen
# op rij niets beters opleveren. Géén tijdsplafond meer (was 60 s per
# materiaal): dat budget werd gedeeld over alle platen van een materiaal,
# dus met de minimale denktijd hieronder kregen de laatste platen van een
# materiaal met veel platen helemaal geen zoektijd meer (gemeten op
# "Keuken Jansen": plaat 7 en 8 van Meubelpaneel wit 18 kregen 0
# pogingen). Sven: "minimaal op 3 zetten en maximaal weglaten".
_ZOEK_TIJDSBUDGET_SECONDEN = math.inf
# Minimale denktijd per plaat (eerst 10 s, op Svens verzoek "een minimale
# denktijd van 10 seconden ofzo"; teruggebracht naar 3 s nadat een meting
# op "Keuken Jansen" liet zien dat alle verbeteringen binnen ~2 s gevonden
# werden en de rest van de 10 s niets meer opleverde, terwijl het genereren
# daardoor ~90 s duurde). Zie engine.genereer_zaagplan's min_zoek_tijdsbudget.
_MIN_ZOEK_TIJDSBUDGET_SECONDEN = 3.0
# Zolang er een zaagplan gegenereerd wordt, geeft Python de GIL veel vaker
# door tussen threads dan de standaard 5 ms (sys.getswitchinterval()).
# Zonder dit bevroor de UI ~3 seconden direct na het klikken op
# "Genereren" (Sven: "het moment je op zaagplan genereren drukt hij even
# vastloopt"): Qt heeft voor het eerste opbouwen/tekenen van de
# "bezig"-kaart honderden keren de GIL nodig (PySide6 roept per
# virtuele methode van een Python-widget-subklasse even Python aan), en
# moest daar elke keer tot 5 ms op wachten terwijl _ZaagplanWorker vol
# aan het rekenen was — gemeten: ~3,2 s bij 5 ms, ~0,7 s bij 1 ms, geen
# merkbare hapering meer bij 0,2 ms. De motor zelf wordt daar
# nauwelijks trager van (en is sowieso door een tijdsbudget begrensd).
_GIL_WISSELINTERVAL_TIJDENS_GENEREREN = 0.0002
_NERFRICHTING_LABEL = {
    Nerfrichting.LANGE_ZIJDE: "Lange zijde",
    Nerfrichting.KORTE_ZIJDE: "Korte zijde",
    Nerfrichting.GEEN: "—",
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


class _ZaagplanWorker(QThread):
    """Genereert de zaagplannen van een project op een eigen thread i.p.v.
    de UI te blokkeren (op Svens verzoek: een echte laad-animatie tijdens
    het genereren) — voorheen liep dit synchroon op de UI-thread (zie
    OVERDRACHT.md, "geen aparte achtergrond-thread ... kandidaat voor een
    latere iteratie als dit hinderlijk blijkt"). Krijgt een losstaande
    kopie van het project/de materialenbibliotheek mee en raakt zelf geen
    Qt-widgets aan; het resultaat komt terug via het ``klaar``-signaal,
    door Qt automatisch op de UI-thread afgeleverd."""

    klaar = Signal(list, list)
    voortgang = Signal(object)  # ZaagplanVoortgang

    # Het GIL-wisselinterval is proces-breed, en er kunnen in meerdere
    # projecttabbladen tegelijk zaagplannen gegenereerd worden — pas
    # terugzetten zodra de laatste worker klaar is.
    _slot = threading.Lock()
    _aantal_actief = 0
    _oorspronkelijk_interval = sys.getswitchinterval()

    def __init__(
        self,
        project: Project,
        materialen: MaterialenBibliotheek,
        strategie: str,
        reststukken: list[Reststuk],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._project = project
        self._materialen = materialen
        self._strategie = strategie
        # Losse kopieën: de bibliotheek kan intussen op de UI-thread wijzigen.
        self._reststukken = [replace(r) for r in reststukken]
        # Hier (op de UI-thread) uitlezen, niet in run().
        instellingen = InstellingenBeheer().huidige
        self._zaagsnede = instellingen.zaagsnede

    def run(self) -> None:
        cls = _ZaagplanWorker
        with cls._slot:
            if cls._aantal_actief == 0:
                cls._oorspronkelijk_interval = sys.getswitchinterval()
                sys.setswitchinterval(_GIL_WISSELINTERVAL_TIJDENS_GENEREREN)
            cls._aantal_actief += 1
        try:
            plannen, waarschuwingen = genereer_zaagplannen_voor_project(
                self._project,
                self._materialen,
                strategie=self._strategie,
                zoek_tijdsbudget=_ZOEK_TIJDSBUDGET_SECONDEN,
                min_zoek_tijdsbudget=_MIN_ZOEK_TIJDSBUDGET_SECONDEN,
                voortgang=self.voortgang.emit,
                zaagsnede=self._zaagsnede,
                reststukken=self._reststukken,
            )
        finally:
            with cls._slot:
                cls._aantal_actief -= 1
                if cls._aantal_actief == 0:
                    sys.setswitchinterval(cls._oorspronkelijk_interval)
        self.klaar.emit(plannen, waarschuwingen)


class _Schakelaar(QWidget):
    """Kleine aan/uit-schakelaar voor "Bewaren" in het Reststukken-paneel.
    Zelf getekend: een gestylede QCheckBox oogt in dit thema niet als een
    schakelaar, en een QPushButton als container klapt in (zie CLAUDE.md)."""

    omgezet = Signal(bool)

    def __init__(self, aan: bool, theme: Theme, actief: bool = True, parent=None) -> None:
        super().__init__(parent)
        self._aan = aan
        self._theme = theme
        self._actief = actief
        self.setFixedSize(34, 20)
        if actief:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Gaat naar de bibliotheek" if aan else "Gaat niet naar de bibliotheek")

    def mouseReleaseEvent(self, event) -> None:
        if self._actief and event.button() == Qt.MouseButton.LeftButton:
            self._aan = not self._aan
            self.update()
            self.omgezet.emit(self._aan)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(1.0 if self._actief else 0.5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self._theme.success if self._aan else self._theme.border))
        p.drawRoundedRect(QRectF(0, 0, 34, 20), 10, 10)
        p.setBrush(QColor(self._theme.surface))
        p.drawEllipse(QRectF(16 if self._aan else 2, 2, 16, 16))


class _MiniPlaat(QWidget):
    """Kleine plaattekening: waar het reststuk op zijn plaat zat (zelfde
    oriëntatie als ``ZaagplaatWidget``: y=0 = rand ONDER, onderaan). Handmatig toegevoegde stukken
    hebben geen plaat: stippelrand met een stuk in het midden."""

    BREEDTE = 54

    def __init__(self, item: ProjectReststuk, theme: Theme, aan: bool, parent=None) -> None:
        super().__init__(parent)
        self._item = item
        self._theme = theme
        self._aan = aan
        if item.plaat_lengte > 0 and item.plaat_breedte > 0:
            hoogte = max(14, round(self.BREEDTE * item.plaat_breedte / item.plaat_lengte))
        else:
            hoogte = 27
        self.setFixedSize(self.BREEDTE, hoogte)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        pen = p.pen()
        pen.setColor(QColor(self._theme.border))
        if self._item.plaat_nummer is None:
            pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.setBrush(QColor(self._theme.surface_2))
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 2, 2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self._theme.success if self._aan else self._theme.text_faint))
        it = self._item
        if it.plaat_nummer is None or it.plaat_lengte <= 0:
            p.drawRect(QRectF(w / 2 - 9, h / 2 - 5, 18, 10))
            return
        sx, sy = w / it.plaat_lengte, h / it.plaat_breedte
        lengte = it.oorspronkelijke_lengte or it.lengte
        breedte = it.oorspronkelijke_breedte or it.breedte
        rect_h = max(2.0, breedte * sy)
        rect = QRectF(it.x * sx, h - it.y * sy - rect_h, max(2.0, lengte * sx), rect_h)
        p.drawRect(rect)
        # Fabrieksranden van het reststuk als dikke lijn.
        if it.fabriekskantenband_randen:
            pen = p.pen()
            pen.setStyle(Qt.PenStyle.SolidLine)
            pen.setColor(QColor(self._theme.accent))
            pen.setWidthF(2.0)
            p.setPen(pen)
            lijnen = {
                Rand.LINKS: (rect.topLeft(), rect.bottomLeft()),
                Rand.RECHTS: (rect.topRight(), rect.bottomRight()),
                Rand.ONDER: (rect.bottomLeft(), rect.bottomRight()),
                Rand.BOVEN: (rect.topLeft(), rect.topRight()),
            }
            for rand in it.fabriekskantenband_randen:
                p.drawLine(*lijnen[rand])


class _ZaagplanSpinner(QLabel):
    """Draaiend laad-icoontje tijdens het genereren van een zaagplan (op
    Svens verzoek: "ik wil ook dat hij tijdens het laden een animatie
    laat zien") — een QTimer draait de basis-pixmap elke tik een stukje
    verder, i.p.v. een statische "Bezig..."-tekst die niets laat zien."""

    def __init__(self, kleur: str, grootte: int = 40, parent=None) -> None:
        super().__init__(parent)
        self._basis = icon_pixmap("loader", kleur, grootte)
        self.setFixedSize(grootte, grootte)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background: transparent;")
        self._hoek = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)
        self._tick()

    def _tick(self) -> None:
        self._hoek = (self._hoek + 8) % 360
        getransformeerd = self._basis.transformed(
            QTransform().rotate(self._hoek), Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(getransformeerd)


class ProjectDetailPage(QWidget):
    def __init__(
        self,
        project_id: str,
        projecten: ProjectenBibliotheek,
        modellen: ModellenBibliotheek,
        materialen: MaterialenBibliotheek,
        zaagplannen_opslag: ZaagplannenOpslag,
        project_reststukken: ProjectReststukkenBibliotheek,
        theme: Theme,
        on_gewijzigd: Callable[[], None] | None = None,
        on_open_projecten_tab: Callable[[], None] | None = None,
        on_open_modelkopie: Callable[[str, str], None] | None = None,
        on_reststukken_gewijzigd: Callable[[], None] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._project_id = project_id
        self._on_open_modelkopie = on_open_modelkopie
        self._projecten = projecten
        self._modellen = modellen
        self._materialen = materialen
        self._zaagplannen_opslag = zaagplannen_opslag
        self._project_reststukken = project_reststukken
        # Na vrijgeven of reserveren: Reststukkenbibliotheek-scherm verversen.
        self._on_reststukken_gewijzigd = on_reststukken_gewijzigd
        self._theme = theme
        self._melding = OpslagMelding(self, theme)
        self._on_gewijzigd = on_gewijzigd
        self._on_open_projecten_tab = on_open_projecten_tab

        self._actief_paneel = "overzicht"
        self._sort_niveaus: list[str] = ["materiaal", "breedte"]
        self._bewerk_los_onderdeel_id: str | None = None
        self._model_naam_naar_id: dict[str, str] = {}
        self._instanties_uitgeklapt: set[str] = set()
        # Reststukken-paneel: welk reststuk staat in "afmeting aanpassen",
        # en staat de "reststuk toevoegen"-regel open.
        self._rs_bewerk_id: str | None = None
        self._rs_toevoegen_open = False
        self._rs_melding_timer = QTimer(self)
        self._rs_melding_timer.setSingleShot(True)
        self._rs_melding_timer.timeout.connect(self._rs_verberg_melding)
        self._rs_melding: QLabel | None = None
        self._rs_melding_tekst = ""
        # Een eerder gegenereerd zaagplan van dít project herladen (zie
        # zaagplannen_opslag.py) i.p.v. altijd leeg te beginnen — op Svens
        # verzoek ("zorg er ook voor dat zaagplannen binnen een project
        # worden opgeslagen"). Geen persistentie/revisiegeschiedenis
        # verder dan dat: alleen de laatst gegenereerde stand.
        opgeslagen = self._zaagplannen_opslag.laad(self._project_id)
        if opgeslagen is not None:
            self._zaagplannen, self._zaagplan_waarschuwingen, opgeslagen_strategie = opgeslagen
            # Val terug op de standaardstrategie als een eerder opgeslagen
            # zaagplan een inmiddels afgeschafte strategienaam heeft (zie
            # het schrappen van "stroken" en "efficient") — zelfde
            # verdediging als _standaard_zaagstrategie hieronder.
            self._zaagplan_strategie = (
                opgeslagen_strategie if opgeslagen_strategie in GELDIGE_ZAAGSTRATEGIEEN else self._standaard_zaagstrategie()
            )
        else:
            self._zaagplannen = None
            self._zaagplan_waarschuwingen = []
            self._zaagplan_strategie = self._standaard_zaagstrategie()
        self._zaagplan_worker: _ZaagplanWorker | None = None
        # Laatste tussenstand + starttijd van een lopende generatie, zodat
        # de "bezig"-kaart na een thema-wissel (_ververs_alles) met de
        # juiste stand herbouwd kan worden i.p.v. weer bij 0 te beginnen.
        self._zaagplan_voortgang: ZaagplanVoortgang | None = None
        self._zaagplan_starttijd = 0.0
        self._zaagplan_balk: QProgressBar | None = None
        self._zaagplan_status: QLabel | None = None
        self._zaagplan_eta: QLabel | None = None

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
        self._melding.set_theme(theme)
        layout = self.layout()
        _clear_layout(layout)
        self._sidebar = self._build_sidebar()
        self._view = self._build_view()
        layout.addWidget(self._sidebar)
        layout.addWidget(self._view, 1)
        self._ververs_alles()

    def ververs(self) -> None:
        """Opnieuw inlezen na een wijziging van buitenaf, bv. een modelkopie
        die in zijn eigen tabblad bewerkt is (zie project_model_page.py)."""
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
        if key == "reststukken":
            # De projectstatus kan intussen elders (Overzicht, Dashboard)
            # gewijzigd zijn — die bepaalt of vrijgeven kan.
            self._ververs_reststukken_paneel()
        self._activeer_stack_paneel(key)

    def _activeer_stack_paneel(self, key: str) -> None:
        # QStackedWidget/QStackedLayout houdt standaard bij het bepalen van
        # de eigen sizeHint rekening met ALLE pagina's, niet alleen de
        # actieve — zonder deze fix bleef de pagina na een bezoek aan het
        # (potentieel hoge, want tabel- en zaagplaat-afbeeldingen-gevulde)
        # Zaagplannen-paneel net zo hoog staan bij het terugschakelen naar
        # bijv. Overzicht, met een grote lege ruimte tot gevolg (Svens
        # melding: "de ui [wordt] even lang als die van zaagplan"). Fix:
        # niet-actieve pagina's krijgen size policy Ignored (tellen dan niet
        # meer mee in de sizeHint-berekening), de actieve pagina krijgt haar
        # normale Preferred-beleid terug.
        for widget in self._paneel_widgets.values():
            widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        actief_widget = self._paneel_widgets[key]
        actief_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self._stack.setCurrentWidget(actief_widget)
        actief_widget.adjustSize()
        self._stack.adjustSize()
        self._stack.updateGeometry()

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
            "reststukken": self._build_reststukken_paneel(),
        }
        for widget in self._paneel_widgets.values():
            self._stack.addWidget(widget)
        self._activeer_stack_paneel(self._actief_paneel)
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
        self._melding.toon("Projectgegevens opgeslagen", f"project {kandidaat.naam}")

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

        if self._on_open_modelkopie is not None:
            # Op Svens verzoek: het model in dit project bewerken, als eigen
            # tabblad (zie project_model_page.py).
            bewerk_btn = QToolButton()
            bewerk_btn.setProperty("role", "rowAction")
            bewerk_btn.setIcon(icon("pencil", self._theme.text_faint, 15))
            bewerk_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            bewerk_btn.setToolTip("Bewerken in dit project")
            bewerk_btn.clicked.connect(lambda: self._on_open_modelkopie(self._project_id, instantie.id))
            layout.addWidget(bewerk_btn)

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

        lo_wissel_btn = QToolButton()
        lo_wissel_btn.setIcon(icon("swap", self._theme.text_muted, 15))
        lo_wissel_btn.setAutoRaise(True)
        lo_wissel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        lo_wissel_btn.setToolTip("Breedte en hoogte omwisselen (bv. per ongeluk verwisseld ingevoerd)")
        lo_wissel_btn.clicked.connect(self._lo_wissel_breedte_hoogte)
        afmeting_rij.addWidget(lo_wissel_btn, 0, Qt.AlignmentFlag.AlignBottom)

        hoogte_col = QVBoxLayout()
        hoogte_col.addWidget(self._field_label("Hoogte mm"))
        hoogte_wrap, self._lo_hoogte = self._field_spin()
        hoogte_col.addWidget(hoogte_wrap)
        afmeting_rij.addLayout(hoogte_col)
        rechts_layout.addLayout(afmeting_rij)
        self._lo_breedte.valueChanged.connect(self._lo_ververs_rand_diagram)
        self._lo_hoogte.valueChanged.connect(self._lo_ververs_rand_diagram)

        rechts_layout.addWidget(self._field_label("Aantal"))
        aantal_wrap, self._lo_aantal = self._field_spin_int(minimum=1, maximum=1000)
        rechts_layout.addWidget(aantal_wrap)

        rechts_layout.addWidget(self._field_label("Nerfrichting"))
        nerf_widget, self._lo_nerf_group = self._segmented(
            [(Nerfrichting.GEEN, "Geen"), (Nerfrichting.LANGE_ZIJDE, "Lange zijde"), (Nerfrichting.KORTE_ZIJDE, "Korte zijde")]
        )
        rechts_layout.addWidget(nerf_widget)

        rechts_layout.addWidget(self._field_label("Kantenband"))
        self._lo_rand_diagram = RandenDiagram(self._theme)
        rechts_layout.addWidget(self._lo_rand_diagram)

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
        self._lo_rand_diagram.set_geselecteerde_randen(frozenset())
        self._lo_ververs_rand_diagram()
        self._onderdeel_toevoegen_fout.hide()

    def _lo_wissel_breedte_hoogte(self) -> None:
        # Op Svens verzoek: snel breedte/hoogte omdraaien als je ze per
        # ongeluk verwisseld hebt ingevoerd.
        breedte, hoogte = self._lo_breedte.value(), self._lo_hoogte.value()
        self._lo_breedte.setValue(hoogte)
        self._lo_hoogte.setValue(breedte)

    def _lo_ververs_rand_diagram(self) -> None:
        self._lo_rand_diagram.set_afmetingen(self._lo_breedte.value(), self._lo_hoogte.value())

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
        self._lo_rand_diagram.set_geselecteerde_randen(onderdeel.kantenband_randen)
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
            kantenband_randen=self._lo_rand_diagram.geselecteerde_randen(),
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
        self._melding.toon(f'Onderdeel "{onderdeel.naam}" opgeslagen', f"in project {self._project().naam}")

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
        panel = QWidget()
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(16)
        self._labels_content = QVBoxLayout()
        self._labels_content.setSpacing(16)
        outer.addLayout(self._labels_content)
        return panel

    def _ververs_labels_paneel(self) -> None:
        _clear_layout(self._labels_content)
        if not self._zaagplannen:
            self._labels_content.addWidget(
                self._build_placeholder_paneel(
                    icon_naam="tag",
                    tag_tekst="Hoofdstuk 6",
                    titel="Nog geen labels beschikbaar",
                    tekst=(
                        "Labels worden automatisch afgeleid van het gegenereerde zaagplan van "
                        "dit project — met materiaal, projectnummer en afmeting per onderdeel, "
                        "optioneel aangevuld met een QR-/barcode, kantenband-indicatie en "
                        "nerfrichting-pijl (in te stellen bij Opties). Genereer eerst een "
                        "zaagplan bij Zaagplannen."
                    ),
                )
            )
        else:
            self._labels_content.addWidget(self._bouw_labels_resultaat())

    def _bouw_labels_resultaat(self) -> QWidget:
        labels = genereer_labels_voor_project(self._project(), self._zaagplannen)

        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        titel_kolom = QVBoxLayout()
        titel_kolom.setSpacing(2)
        titel = QLabel("Labels")
        titel.setProperty("role", "matName")
        titel_kolom.addWidget(titel)
        aantal = len(labels)
        sub = QLabel(f"{aantal} {'label' if aantal == 1 else 'labels'} · één per gezaagd onderdeel-exemplaar")
        sub.setProperty("role", "matMeta")
        titel_kolom.addWidget(sub)
        toolbar.addLayout(titel_kolom)
        toolbar.addStretch(1)
        pdf_btn = QPushButton("  Labels als PDF")
        pdf_btn.setProperty("role", "primary")
        pdf_btn.setIcon(icon("download", "#12141B", 13))
        pdf_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pdf_btn.setEnabled(aantal > 0)
        pdf_btn.clicked.connect(lambda: self._exporteer_labels_pdf(labels))
        toolbar.addWidget(pdf_btn)
        layout.addLayout(toolbar)

        if not labels:
            waarschuwing = QLabel(
                "Geen enkel onderdeel kon op het huidige zaagplan geplaatst worden — er zijn dus "
                "nog geen labels om te genereren."
            )
            waarschuwing.setProperty("role", "warningText")
            waarschuwing.setWordWrap(True)
            layout.addWidget(waarschuwing)
        else:
            kaart = QFrame()
            kaart.setObjectName("TableCard")
            kaart_layout = QVBoxLayout(kaart)
            kaart_layout.setContentsMargins(0, 0, 0, 0)
            kaart_layout.addWidget(self._bouw_labels_tabel(labels))
            layout.addWidget(kaart)

        return wrapper

    def _bouw_labels_tabel(self, labels: list[OnderdeelLabel]) -> QTableWidget:
        tabel = QTableWidget(len(labels), 5)
        tabel.setObjectName("LibraryTable")
        tabel.setHorizontalHeaderLabels(["Onderdeel", "Materiaal", "Afmeting", "Kantenband", "Nerfrichting"])
        tabel.verticalHeader().setVisible(False)
        tabel.setShowGrid(False)
        tabel.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        tabel.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tabel.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        tabel.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tabel.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        header = tabel.horizontalHeader()
        header.setStretchLastSection(True)
        for col, breedte in enumerate([260, 220, 140, 160]):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            tabel.setColumnWidth(col, breedte)

        rij_hoogte = 40
        for row, label in enumerate(labels):
            tabel.setRowHeight(row, rij_hoogte)
            if label.fabriekskantenband_vereist:
                kantenband_tekst = "Fabrieksrand"
            elif label.kantenband_randen:
                kantenband_tekst = ", ".join(sorted(r.value for r in label.kantenband_randen))
            else:
                kantenband_tekst = "—"
            tabel.setItem(row, 0, QTableWidgetItem(label.onderdeel_naam))
            tabel.setItem(row, 1, QTableWidgetItem(label.materiaal_naam))
            tabel.setItem(row, 2, QTableWidgetItem(label.afmeting_tekst))
            tabel.setItem(row, 3, QTableWidgetItem(kantenband_tekst))
            tabel.setItem(row, 4, QTableWidgetItem(_NERFRICHTING_LABEL[label.nerfrichting_vereist]))
        return tabel

    def _exporteer_labels_pdf(self, labels: list[OnderdeelLabel]) -> None:
        if not labels:
            return
        standaard_naam = f"Labels {self._project().naam}.pdf"
        pad, _ = QFileDialog.getSaveFileName(self, "Labels opslaan als PDF", standaard_naam, "PDF-bestanden (*.pdf)")
        if not pad:
            return
        schrijf_labels_pdf(pad, project=self._project(), labels=labels, instellingen=InstellingenBeheer().huidige)

    # ------------------------------------------------------------------
    # Paneel: Reststukken (tijdelijke reststukkenlijst van dit project)
    # ------------------------------------------------------------------
    # Mockup: design/assets/mockups/project-reststukken-concept.html. Elke
    # wijziging (bewaren, reden, afmeting, toevoegen) gaat meteen de opslag
    # in — er wordt niets verwijderd, alles is terug te zetten — met een
    # groene regel in de voettekst van de kaart.
    def _build_reststukken_paneel(self) -> QWidget:
        panel = QWidget()
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(14)
        self._rs_content = QVBoxLayout()
        self._rs_content.setSpacing(14)
        outer.addLayout(self._rs_content)
        # Anders rekt de kaart uit tot de paneelhoogte en zakt de voettekst weg.
        outer.addStretch(1)
        return panel

    def _ververs_reststukken_paneel(self) -> None:
        _clear_layout(self._rs_content)
        self._rs_melding = None
        # Een zaagplan van vóór dit paneel bestond: reststukken alsnog
        # overnemen zodra de lijst nog leeg is.
        if (
            self._zaagplannen
            and not self._project_reststukken.lijst(self._project_id)
            and not self._project_reststukken.is_vrijgegeven(self._project_id)
        ):
            self._project_reststukken.overnemen_uit_zaagplan(self._project_id, self._zaagplannen)

        items = self._project_reststukken.lijst(self._project_id)
        if not self._zaagplannen and not items and not self._rs_toevoegen_open:
            self._rs_content.addWidget(
                self._build_placeholder_paneel(
                    icon_naam="recycle",
                    tag_tekst="Nog geen zaagplan",
                    titel="Nog geen reststukken",
                    tekst=(
                        "De reststukken van dit project komen uit het zaagplan. Genereer eerst "
                        "een zaagplan bij Zaagplannen, daarna kun je ze hier aanpassen, "
                        "hergebruiken of afschrijven en bij Afgerond vrijgeven naar de "
                        "Reststukkenbibliotheek."
                    ),
                )
            )
            return

        project = self._project()
        vrijgegeven = self._project_reststukken.is_vrijgegeven(self._project_id)
        afgerond = project.status == ProjectStatus.AFGEROND

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        titel_kolom = QVBoxLayout()
        titel_kolom.setSpacing(2)
        titel = QLabel("Reststukken")
        titel.setProperty("role", "matName")
        titel_kolom.addWidget(titel)
        sub = QLabel(
            "De reststukken die dit project oplevert, los van de Reststukkenbibliotheek: "
            "aan te passen, te hergebruiken of af te schrijven."
        )
        sub.setProperty("role", "matMeta")
        sub.setWordWrap(True)
        titel_kolom.addWidget(sub)
        toolbar.addLayout(titel_kolom, 1)
        toevoegen_btn = QPushButton("  Reststuk toevoegen")
        toevoegen_btn.setProperty("role", "ghost")
        toevoegen_btn.setIcon(icon("plus", self._theme.text, 13))
        toevoegen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        toevoegen_btn.setEnabled(not vrijgegeven)
        toevoegen_btn.clicked.connect(self._rs_open_toevoegen)
        toolbar.addWidget(toevoegen_btn, 0, Qt.AlignmentFlag.AlignTop)
        vrijgeven_btn = QPushButton("  Vrijgeven naar bibliotheek")
        vrijgeven_btn.setProperty("role", "primary")
        vrijgeven_btn.setIcon(icon("recycle", "#12141B", 13))
        vrijgeven_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        vrijgeven_btn.setEnabled(afgerond and not vrijgegeven)
        if vrijgegeven:
            vrijgeven_btn.setToolTip("Al vrijgegeven")
        elif not afgerond:
            vrijgeven_btn.setToolTip("Kan pas als het project Afgerond is")
        vrijgeven_btn.clicked.connect(self._rs_vrijgeven)
        toolbar.addWidget(vrijgeven_btn, 0, Qt.AlignmentFlag.AlignTop)
        self._rs_content.addLayout(toolbar)

        bewaren = sum(1 for r in items if r.status == ProjectReststukStatus.BEWAREN)
        if vrijgegeven:
            datum = self._project_reststukken.vrijgegeven_op(self._project_id)
            self._rs_content.addWidget(
                self._rs_banner(
                    f"<b>Vrijgegeven op {_datum_tekst(datum)}.</b> {bewaren} "
                    f"{'reststuk staat' if bewaren == 1 else 'reststukken staan'} nu in de "
                    f"Reststukkenbibliotheek met herkomst “{project.naam}”. Deze lijst is vanaf nu "
                    "alleen nog ter informatie.",
                    succes=True,
                )
            )
        elif afgerond:
            self._rs_content.addWidget(
                self._rs_banner(
                    "<b>Het project is afgerond.</b> Controleer de lijst en klik op “Vrijgeven naar "
                    f"bibliotheek”. Alleen de {bewaren} {'reststuk' if bewaren == 1 else 'reststukken'} "
                    "met <i>Bewaren</i> aan gaan mee."
                )
            )
        else:
            self._rs_content.addWidget(
                self._rs_banner(
                    "Pas bij <b>Afgerond</b> kun je deze reststukken vrijgeven naar de bibliotheek. "
                    "Opnieuw genereren vervangt de reststukken uit het zaagplan; handmatig "
                    "toegevoegde blijven staan."
                )
            )

        kaart = QFrame()
        kaart.setObjectName("TableCard")
        kaart_layout = QVBoxLayout(kaart)
        kaart_layout.setContentsMargins(0, 0, 0, 0)
        kaart_layout.setSpacing(0)
        if items:
            kaart_layout.addWidget(self._rs_bouw_tabel(items, vrijgegeven))
        if self._rs_toevoegen_open and not vrijgegeven:
            kaart_layout.addWidget(self._rs_bouw_toevoegen())

        voet = QFrame()
        voet.setStyleSheet(f"QFrame {{ border-top: 1px solid {self._theme.border}; }} QLabel {{ border: none; }}")
        voet_layout = QHBoxLayout(voet)
        voet_layout.setContentsMargins(16, 12, 16, 12)
        voet_layout.setSpacing(14)
        for status, tekst in (
            (ProjectReststukStatus.BEWAREN, "bewaren"),
            (ProjectReststukStatus.HERGEBRUIKT, "hergebruikt"),
            (ProjectReststukStatus.AFGESCHREVEN, "afgeschreven"),
        ):
            aantal = sum(1 for r in items if r.status == status)
            label = QLabel(f"<b style='color:{self._theme.text}'>{aantal}</b> {tekst}")
            label.setStyleSheet(f"color: {self._theme.text_muted}; font-size: 12px;")
            voet_layout.addWidget(label)
        voet_layout.addStretch(1)
        self._rs_melding = QLabel()
        self._rs_melding.setStyleSheet(f"color: {self._theme.success_ink}; font-size: 12px; font-weight: 600;")
        self._rs_melding.setVisible(self._rs_melding_timer.isActive())
        self._rs_melding.setText(self._rs_melding_tekst)
        voet_layout.addWidget(self._rs_melding)
        kaart_layout.addWidget(voet)
        self._rs_content.addWidget(kaart)

    def _rs_banner(self, html: str, succes: bool = False) -> QFrame:
        banner = QFrame()
        banner.setObjectName("RsBanner")
        if succes:
            achter, rand, inkt, icoon = self._theme.success_soft, self._theme.success_soft, self._theme.success_ink, "check"
        else:
            achter, rand, inkt, icoon = self._theme.accent_soft, self._theme.accent_soft_border, self._theme.accent_text, "warning"
        banner.setStyleSheet(
            f"QFrame#RsBanner {{ background: {achter}; border: 1px solid {rand}; border-radius: 10px; }}"
            f"QFrame#RsBanner QLabel {{ background: transparent; color: {inkt}; font-size: 12.5px; }}"
        )
        layout = QHBoxLayout(banner)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)
        icon_label = QLabel()
        icon_label.setPixmap(icon_pixmap(icoon, inkt, 15))
        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)
        tekst = QLabel(html)
        tekst.setTextFormat(Qt.TextFormat.RichText)
        tekst.setWordWrap(True)
        layout.addWidget(tekst, 1)
        return banner

    def _rs_bouw_tabel(self, items: list[ProjectReststuk], vrijgegeven: bool) -> QTableWidget:
        per_materiaal: dict[str, list[ProjectReststuk]] = {}
        for item in items:
            per_materiaal.setdefault(item.materiaal_id, []).append(item)

        def materiaal_naam(materiaal_id: str) -> str:
            try:
                return self._materialen.ophalen(materiaal_id).naam
            except KeyError:
                return "Onbekend materiaal"

        groepen = sorted(per_materiaal.items(), key=lambda kv: materiaal_naam(kv[0]).lower())
        aantal_rijen = sum(1 + len(g) for _, g in groepen)

        tabel = QTableWidget(aantal_rijen, 6)
        tabel.setObjectName("LibraryTable")
        tabel.setHorizontalHeaderLabels(["Bewaren", "Reststuk", "Afmeting (l × b)", "Status", "Herkomst", ""])
        tabel.verticalHeader().setVisible(False)
        tabel.setShowGrid(False)
        tabel.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        tabel.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tabel.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        tabel.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tabel.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        header = tabel.horizontalHeader()
        header.setStretchLastSection(True)
        for col, breedte in enumerate([84, 200, 260, 220, 120]):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            tabel.setColumnWidth(col, breedte)

        groep_hoogte, rij_hoogte = 38, 52
        hoogte_rijen = 0
        row = 0
        for materiaal_id, groep in groepen:
            tabel.setSpan(row, 0, 1, 6)
            tabel.setRowHeight(row, groep_hoogte)
            hoogte_rijen += groep_hoogte
            groep_cel = QWidget()
            groep_layout = QHBoxLayout(groep_cel)
            groep_layout.setContentsMargins(12, 10, 12, 4)
            groep_layout.setSpacing(8)
            naam = QLabel(materiaal_naam(materiaal_id))
            naam.setStyleSheet(f"color: {self._theme.text}; font-size: 12px; font-weight: 700;")
            groep_layout.addWidget(naam)
            # Plaatmaat van een volle plaat, niet van een bibliotheek-reststuk.
            volle_plaat = next(
                (r for r in groep if r.plaat_lengte > 0 and not r.uit_bibliotheek_reststuk), None
            )
            extra = f"{len(groep)} {'reststuk' if len(groep) == 1 else 'reststukken'}"
            if volle_plaat is not None:
                extra += f" · plaat {volle_plaat.plaat_lengte:g} × {volle_plaat.plaat_breedte:g} mm"
            meta = QLabel(extra)
            meta.setStyleSheet(f"color: {self._theme.text_faint}; font-size: 12px; font-weight: 600;")
            groep_layout.addWidget(meta)
            groep_layout.addStretch(1)
            tabel.setCellWidget(row, 0, groep_cel)
            row += 1

            for item in groep:
                tabel.setRowHeight(row, rij_hoogte)
                hoogte_rijen += rij_hoogte
                self._rs_vul_rij(tabel, row, item, vrijgegeven)
                row += 1

        tabel.setFixedHeight(header.sizeHint().height() + hoogte_rijen + 4)

        # Zie _bouw_onderdelen_tabel: de echte (gestylede) headerhoogte is
        # pas na het tonen bekend.
        def _herstel_hoogte(tabel=tabel, hoogte_rijen=hoogte_rijen) -> None:
            tabel.setFixedHeight(tabel.horizontalHeader().height() + hoogte_rijen + 4)

        QTimer.singleShot(0, _herstel_hoogte)
        return tabel

    def _rs_vul_rij(self, tabel: QTableWidget, row: int, item: ProjectReststuk, vrijgegeven: bool) -> None:
        aan = item.status == ProjectReststukStatus.BEWAREN
        uit_kleur = self._theme.text_faint

        # Bewaren
        cel = QWidget()
        layout = QHBoxLayout(cel)
        layout.setContentsMargins(14, 0, 4, 0)
        schakelaar = _Schakelaar(aan, self._theme, actief=not vrijgegeven)
        schakelaar.omgezet.connect(lambda nieuw, i=item.id: self._rs_zet_bewaren(i, nieuw))
        layout.addWidget(schakelaar)
        layout.addStretch(1)
        tabel.setCellWidget(row, 0, cel)

        # Reststuk: plaattekening + code + plaat
        cel = QWidget()
        layout = QHBoxLayout(cel)
        layout.setContentsMargins(10, 4, 4, 4)
        layout.setSpacing(10)
        layout.addWidget(_MiniPlaat(item, self._theme, aan))
        tekst_kolom = QVBoxLayout()
        tekst_kolom.setSpacing(1)
        code = QLabel(item.code)
        code.setStyleSheet(f"color: {self._theme.text if aan else uit_kleur}; font-size: 13px; font-weight: 700;")
        tekst_kolom.addWidget(code)
        if item.plaat_nummer is not None and item.uit_bibliotheek_reststuk:
            plaat_tekst = "Uit reststuk"
        elif item.plaat_nummer is not None:
            plaat_tekst = f"Plaat {item.plaat_nummer} van {item.platen_totaal}"
        else:
            plaat_tekst = "Niet uit het zaagplan"
        if item.fabriekskantenband_randen:
            plaat_tekst += " · fabrieksrand"
        plaat = QLabel(plaat_tekst)
        plaat.setStyleSheet(f"color: {self._theme.text_muted}; font-size: 11.5px;")
        if item.fabriekskantenband_randen:
            plaat.setToolTip(
                "Fabriekskantenband op: " + ", ".join(sorted(r.value for r in item.fabriekskantenband_randen))
            )
        tekst_kolom.addWidget(plaat)
        layout.addLayout(tekst_kolom)
        layout.addStretch(1)
        tabel.setCellWidget(row, 1, cel)

        # Afmeting (of de twee invoervelden bij "aanpassen")
        cel = QWidget()
        layout = QHBoxLayout(cel)
        layout.setContentsMargins(10, 4, 4, 4)
        layout.setSpacing(6)
        if self._rs_bewerk_id == item.id and not vrijgegeven:
            self._rs_in_lengte = self._rs_maatveld(item.lengte)
            self._rs_in_breedte = self._rs_maatveld(item.breedte)
            layout.addWidget(self._rs_in_lengte)
            maal = QLabel("×")
            maal.setStyleSheet(f"color: {uit_kleur};")
            layout.addWidget(maal)
            layout.addWidget(self._rs_in_breedte)
            mm = QLabel("mm")
            mm.setStyleSheet(f"color: {uit_kleur};")
            layout.addWidget(mm)
            self._rs_in_lengte.returnPressed.connect(lambda i=item.id: self._rs_afmeting_opslaan(i))
            self._rs_in_breedte.returnPressed.connect(lambda i=item.id: self._rs_afmeting_opslaan(i))
            QTimer.singleShot(0, self._rs_in_lengte.setFocus)
        else:
            afm = QLabel(f"{item.lengte:g} × {item.breedte:g} mm")
            stijl = f"color: {self._theme.text if aan else uit_kleur}; font-size: 13px;"
            if not aan:
                stijl += " text-decoration: line-through;"
            afm.setStyleSheet(stijl)
            layout.addWidget(afm)
            if item.is_aangepast:
                was = QLabel(f"{item.oorspronkelijke_lengte:g} × {item.oorspronkelijke_breedte:g}")
                was.setStyleSheet(f"color: {uit_kleur}; font-size: 11.5px; text-decoration: line-through;")
                layout.addWidget(was)
                chip = QLabel("aangepast")
                chip.setStyleSheet(
                    f"background: {self._theme.warning_soft}; color: {self._theme.warning_ink}; border-radius: 8px;"
                    " padding: 1px 7px; font-size: 10.5px; font-weight: 700;"
                )
                layout.addWidget(chip)
        layout.addStretch(1)
        tabel.setCellWidget(row, 2, cel)

        # Status
        cel = QWidget()
        layout = QHBoxLayout(cel)
        layout.setContentsMargins(10, 4, 8, 4)
        if vrijgegeven:
            if aan:
                layout.addWidget(self._rs_pil("In bibliotheek", self._theme.accent_soft, self._theme.accent_text, self._theme.accent))
            else:
                tekst = "Hergebruikt in project" if item.status == ProjectReststukStatus.HERGEBRUIKT else "Afgeschreven"
                label = QLabel(tekst)
                label.setStyleSheet(f"color: {uit_kleur}; font-size: 12px; font-weight: 600;")
                layout.addWidget(label)
        elif aan:
            layout.addWidget(self._rs_pil("Bewaren", self._theme.success_soft, self._theme.success_ink, self._theme.success))
        else:
            combo = QComboBox()
            combo.setProperty("role", "field")
            combo.addItem("Hergebruikt in project", ProjectReststukStatus.HERGEBRUIKT.value)
            combo.addItem("Afgeschreven", ProjectReststukStatus.AFGESCHREVEN.value)
            combo.setCurrentIndex(combo.findData(item.status.value))
            combo.currentIndexChanged.connect(
                lambda _i, c=combo, i=item.id: self._rs_zet_reden(i, ProjectReststukStatus(c.currentData()))
            )
            layout.addWidget(combo)
        layout.addStretch(1)
        tabel.setCellWidget(row, 3, cel)

        # Herkomst
        tabel.setCellWidget(row, 4, self._cel_herkomst("Zaagplan" if item.bron == ProjectReststukBron.ZAAGPLAN else "Handmatig"))

        # Acties
        if not vrijgegeven:
            cel = QWidget()
            layout = QHBoxLayout(cel)
            layout.setContentsMargins(4, 0, 10, 0)
            layout.setSpacing(2)
            layout.addStretch(1)
            if self._rs_bewerk_id == item.id:
                ok = self._rs_actieknop("check", "Opslaan")
                ok.clicked.connect(lambda _c=False, i=item.id: self._rs_afmeting_opslaan(i))
                layout.addWidget(ok)
                annuleer = self._rs_actieknop("close", "Annuleren")
                annuleer.clicked.connect(self._rs_annuleer_bewerken)
                layout.addWidget(annuleer)
            else:
                potlood = self._rs_actieknop("pencil", "Afmeting aanpassen")
                potlood.clicked.connect(lambda _c=False, i=item.id: self._rs_start_bewerken(i))
                layout.addWidget(potlood)
            tabel.setCellWidget(row, 5, cel)

    def _rs_pil(self, tekst: str, achter: str, inkt: str, stip: str) -> QLabel:
        pil = QLabel(f"<span style='color:{stip}'>●</span>&nbsp;{tekst}")
        pil.setTextFormat(Qt.TextFormat.RichText)
        pil.setStyleSheet(
            f"background: {achter}; color: {inkt}; border-radius: 10px; padding: 3px 9px;"
            " font-size: 11.5px; font-weight: 700;"
        )
        return pil

    def _rs_actieknop(self, icon_naam: str, tip: str) -> QToolButton:
        knop = QToolButton()
        knop.setProperty("role", "rowAction")
        knop.setIcon(icon(icon_naam, self._theme.text_muted, 15))
        knop.setIconSize(QSize(15, 15))
        knop.setFixedSize(28, 28)
        knop.setToolTip(tip)
        knop.setCursor(Qt.CursorShape.PointingHandCursor)
        return knop

    def _rs_maatveld(self, waarde: float | None = None, placeholder: str = "") -> QLineEdit:
        veld = QLineEdit(f"{waarde:g}" if waarde is not None else "")
        veld.setProperty("role", "field")
        veld.setPlaceholderText(placeholder)
        validator = QDoubleValidator(0.0, 100000.0, 1, veld)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        veld.setValidator(validator)
        veld.setFixedWidth(84)
        return veld

    def _rs_bouw_toevoegen(self) -> QFrame:
        regel = QFrame()
        regel.setStyleSheet(
            f"QFrame#RsToevoegen {{ background: {self._theme.surface_2}; border-top: 1px solid {self._theme.border}; }}"
        )
        regel.setObjectName("RsToevoegen")
        regel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QHBoxLayout(regel)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        def met_label(tekst: str, veld: QWidget) -> QVBoxLayout:
            kolom = QVBoxLayout()
            kolom.setSpacing(5)
            kolom.addWidget(self._field_label(tekst))
            kolom.addWidget(veld)
            return kolom

        self._rs_in_materiaal = QComboBox()
        self._rs_in_materiaal.setProperty("role", "field")
        # Materialen uit dit project eerst, daarna de rest van de actieve materialen.
        in_project = {item.materiaal_id for item in self._project_reststukken.lijst(self._project_id)}
        in_project |= {plan.materiaal_id for plan in (self._zaagplannen or [])}
        materialen = self._materialen.lijst(status=MateriaalStatus.ACTIEF)
        materialen.sort(key=lambda m: (m.id not in in_project, m.naam.lower()))
        for m in materialen:
            self._rs_in_materiaal.addItem(m.naam, m.id)
        self._rs_in_materiaal.setMinimumWidth(240)
        layout.addLayout(met_label("Materiaal", self._rs_in_materiaal))
        self._rs_in_nieuw_lengte = self._rs_maatveld(placeholder="bv. 800")
        layout.addLayout(met_label("Lengte (mm)", self._rs_in_nieuw_lengte))
        self._rs_in_nieuw_breedte = self._rs_maatveld(placeholder="bv. 400")
        layout.addLayout(met_label("Breedte (mm)", self._rs_in_nieuw_breedte))

        ok = QPushButton("Toevoegen")
        ok.setProperty("role", "primary")
        ok.setCursor(Qt.CursorShape.PointingHandCursor)
        ok.clicked.connect(self._rs_toevoegen)
        layout.addWidget(ok, 0, Qt.AlignmentFlag.AlignBottom)
        annuleer = QPushButton("Annuleren")
        annuleer.setProperty("role", "ghost")
        annuleer.setCursor(Qt.CursorShape.PointingHandCursor)
        annuleer.clicked.connect(self._rs_sluit_toevoegen)
        layout.addWidget(annuleer, 0, Qt.AlignmentFlag.AlignBottom)
        self._rs_toevoegen_fout = QLabel()
        self._rs_toevoegen_fout.setProperty("role", "validationText")
        self._rs_toevoegen_fout.setWordWrap(True)
        layout.addWidget(self._rs_toevoegen_fout, 1, Qt.AlignmentFlag.AlignBottom)
        QTimer.singleShot(0, self._rs_in_nieuw_lengte.setFocus)
        return regel

    @staticmethod
    def _rs_getal(veld: QLineEdit) -> float:
        try:
            return float(veld.text().replace(",", "."))
        except ValueError:
            return 0.0

    # -- acties --------------------------------------------------------
    def _rs_meld(self, tekst: str) -> None:
        self._rs_melding_tekst = f"✓  {tekst}"
        self._rs_melding_timer.start(3000)
        if self._rs_melding is not None:
            self._rs_melding.setText(self._rs_melding_tekst)
            self._rs_melding.show()

    def _rs_verberg_melding(self) -> None:
        self._rs_melding_tekst = ""
        if self._rs_melding is not None:
            self._rs_melding.hide()

    def _rs_na_wijziging(self, melding: str) -> None:
        self._ververs_reststukken_paneel()
        self._rs_meld(melding)

    def _rs_zet_bewaren(self, reststuk_id: str, aan: bool) -> None:
        status = ProjectReststukStatus.BEWAREN if aan else ProjectReststukStatus.AFGESCHREVEN
        try:
            item = self._project_reststukken.zet_status(reststuk_id, status)
        except AlVrijgegevenError:
            self._ververs_reststukken_paneel()
            return
        # Uitgestelde herbouw: de schakelaar die dit signaal geeft, wordt
        # anders midden in zijn eigen muisafhandeling verwijderd.
        QTimer.singleShot(
            0, lambda: self._rs_na_wijziging(f"{item.code} {'wordt bewaard' if aan else 'afgeschreven'}")
        )

    def _rs_zet_reden(self, reststuk_id: str, status: ProjectReststukStatus) -> None:
        try:
            item = self._project_reststukken.zet_status(reststuk_id, status)
        except AlVrijgegevenError:
            self._ververs_reststukken_paneel()
            return
        tekst = "hergebruikt in project" if status == ProjectReststukStatus.HERGEBRUIKT else "afgeschreven"
        QTimer.singleShot(0, lambda: self._rs_na_wijziging(f"{item.code}: {tekst}"))

    def _rs_start_bewerken(self, reststuk_id: str) -> None:
        self._rs_bewerk_id = reststuk_id
        self._ververs_reststukken_paneel()

    def _rs_annuleer_bewerken(self) -> None:
        self._rs_bewerk_id = None
        self._ververs_reststukken_paneel()

    def _rs_afmeting_opslaan(self, reststuk_id: str) -> None:
        lengte, breedte = self._rs_getal(self._rs_in_lengte), self._rs_getal(self._rs_in_breedte)
        try:
            item = self._project_reststukken.wijzig_afmeting(reststuk_id, lengte, breedte)
        except ValueError:
            # Ongeldige maat (0 of leeg): veld blijft open, rood omrand.
            for veld, waarde in ((self._rs_in_lengte, lengte), (self._rs_in_breedte, breedte)):
                if waarde <= 0:
                    veld.setStyleSheet(f"border-color: {self._theme.critical};")
            return
        except AlVrijgegevenError:
            self._rs_bewerk_id = None
            self._ververs_reststukken_paneel()
            return
        self._rs_bewerk_id = None
        QTimer.singleShot(
            0, lambda: self._rs_na_wijziging(f"{item.code} aangepast naar {item.lengte:g} × {item.breedte:g} mm")
        )

    def _rs_open_toevoegen(self) -> None:
        self._rs_toevoegen_open = True
        self._ververs_reststukken_paneel()

    def _rs_sluit_toevoegen(self) -> None:
        self._rs_toevoegen_open = False
        self._ververs_reststukken_paneel()

    def _rs_toevoegen(self) -> None:
        materiaal_id = self._rs_in_materiaal.currentData()
        lengte, breedte = self._rs_getal(self._rs_in_nieuw_lengte), self._rs_getal(self._rs_in_nieuw_breedte)
        try:
            item = self._project_reststukken.toevoegen_handmatig(self._project_id, materiaal_id or "", lengte, breedte)
        except ValueError as fout:
            self._rs_toevoegen_fout.setText(str(fout).replace("; ", "\n"))
            return
        except AlVrijgegevenError:
            self._rs_sluit_toevoegen()
            return
        self._rs_toevoegen_open = False
        QTimer.singleShot(0, lambda: self._rs_na_wijziging(f"{item.code} toegevoegd"))

    def _rs_vrijgeven(self) -> None:
        try:
            nieuw = self._project_reststukken.vrijgeven(self._project())
        except (ProjectNietAfgerondError, AlVrijgegevenError):
            self._ververs_reststukken_paneel()
            return
        self._rs_bewerk_id = None
        self._rs_toevoegen_open = False
        if self._on_reststukken_gewijzigd is not None:
            self._on_reststukken_gewijzigd()
        aantal = len(nieuw)
        QTimer.singleShot(
            0,
            lambda: self._rs_na_wijziging(
                f"{aantal} {'reststuk' if aantal == 1 else 'reststukken'} vrijgegeven naar de bibliotheek"
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
        # Het grondiger zoeken (zoek_tijdsbudget, met een minimale
        # denktijd van _MIN_ZOEK_TIJDSBUDGET_SECONDEN) kan een tijdje
        # duren per materiaal — draait daarom op een eigen thread
        # (_ZaagplanWorker) i.p.v. de UI te blokkeren, met een echte
        # draaiende laad-animatie (op Svens verzoek: "ik wil ook dat hij
        # tijdens het laden een animatie laat zien"). Voorheen liep dit
        # synchroon op de UI-thread met alleen een statische
        # "Bezig..."-tekst (zie OVERDRACHT.md) — bewust een latere
        # iteratie zodra dit hinderlijk zou blijken, wat nu het geval is.
        if self._zaagplan_worker is not None:
            return
        self._zaagplan_voortgang = None
        self._zaagplan_starttijd = time.monotonic()
        # Reststukken eerst: alle beschikbare stukken uit de bibliotheek, plus
        # wat een eerder zaagplan van dit project al gereserveerd had.
        kandidaten = self._project_reststukken.reststukken.kandidaten_voor_project(self._project_id)
        self._zaagplan_worker = _ZaagplanWorker(
            self._project(), self._materialen, self._zaagplan_strategie, kandidaten, self
        )
        self._zaagplan_worker.voortgang.connect(self._op_zaagplan_voortgang)
        self._zaagplan_worker.klaar.connect(self._op_zaagplannen_klaar)
        self._ververs_zaagplannen_paneel()
        self._zaagplan_worker.start()

    def _op_zaagplan_voortgang(self, voortgang: ZaagplanVoortgang) -> None:
        self._zaagplan_voortgang = voortgang
        self._toon_zaagplan_voortgang()

    def _toon_zaagplan_voortgang(self) -> None:
        if self._zaagplan_balk is None or self._zaagplan_status is None or self._zaagplan_eta is None:
            return
        v = self._zaagplan_voortgang
        if v is None:
            self._zaagplan_balk.setValue(0)
            self._zaagplan_status.setText("Voorbereiden…")
            self._zaagplan_eta.setText("Resterende tijd berekenen…")
            return

        self._zaagplan_balk.setValue(round(v.fractie * 1000))
        materiaal = f"Materiaal {v.materiaal_nummer} van {v.materiaal_totaal}" if v.materiaal_totaal > 1 else "Materiaal"
        self._zaagplan_status.setText(f"{materiaal}: {v.materiaal_naam} · plaat {v.plaat_nummer}")

        # Resterende tijd: lineair doorgetrokken vanuit de verstreken tijd
        # (elke plaat kost ongeveer even lang, zie ZaagplanVoortgang), pas
        # vanaf een paar procent — daarvoor is de schatting te wild.
        # Afgerond op 5 seconden zodat het getal niet elke tik verspringt.
        verstreken = time.monotonic() - self._zaagplan_starttijd
        procent = round(v.fractie * 100)
        if v.fractie < 0.03 or verstreken < 1.0:
            self._zaagplan_eta.setText(f"{procent}% · resterende tijd berekenen…")
            return
        rest = verstreken * (1.0 - v.fractie) / v.fractie
        if rest < 5:
            self._zaagplan_eta.setText(f"{procent}% · bijna klaar…")
            return
        seconden = 5 * math.ceil(rest / 5)
        tijd = f"{seconden} seconden" if seconden < 60 else f"{seconden // 60} min {seconden % 60:02d} s"
        self._zaagplan_eta.setText(f"{procent}% · nog ongeveer {tijd}")

    def _op_zaagplannen_klaar(self, plannen: list[PlaatZaagplan], waarschuwingen: list[str]) -> None:
        self._zaagplan_worker = None
        self._zaagplan_voortgang = None
        self._zaagplannen = plannen
        self._zaagplan_waarschuwingen = waarschuwingen
        # Meteen opslaan zodat dit zaagplan overleeft als je het project
        # sluit of de app herstart (zie zaagplannen_opslag.py) — "opnieuw
        # genereren" overschrijft gewoon de eerder opgeslagen stand.
        self._zaagplannen_opslag.opslaan(self._project_id, plannen, waarschuwingen, self._zaagplan_strategie)
        # Gebruikte bibliotheek-reststukken reserveren voor dit project (of
        # meteen "gebruikt" als het al in productie is); niet meer gebruikte
        # komen weer beschikbaar.
        project = self._project()
        self._project_reststukken.reststukken.wijs_toe_aan_project(
            self._project_id,
            project.naam,
            {plan.reststuk_id for plan in plannen if plan.reststuk_id},
            verbruikt=project.status != ProjectStatus.WERKVOORBEREIDING,
        )
        if self._on_reststukken_gewijzigd is not None:
            self._on_reststukken_gewijzigd()
        # Reststukken uit het nieuwe zaagplan overnemen (handmatig toegevoegde
        # blijven staan); na vrijgeven ligt de projectlijst vast.
        if not self._project_reststukken.is_vrijgegeven(self._project_id):
            self._project_reststukken.overnemen_uit_zaagplan(self._project_id, plannen)
            self._rs_bewerk_id = None
        self._ververs_zaagplannen_paneel()
        self._ververs_labels_paneel()
        self._ververs_reststukken_paneel()

    def _bouw_zaagplan_bezig(self) -> QWidget:
        kaart = QFrame()
        kaart.setObjectName("TableCard")
        layout = QVBoxLayout(kaart)
        layout.setContentsMargins(30, 56, 30, 56)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        t = self._theme
        layout.addWidget(_ZaagplanSpinner(t.accent_text), 0, Qt.AlignmentFlag.AlignHCenter)

        titel = QLabel("Bezig met zoeken naar het beste zaagplan…")
        titel.setProperty("role", "placeholderTitle")
        titel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(titel)

        # Voortgangsbalk + tussenstand (op Svens verzoek: "zodat de
        # gebruiker kan zien hoelang het ongeveer gaat duren en hoe ver
        # hij is"), bijgewerkt via _op_zaagplan_voortgang.
        balk = QProgressBar()
        balk.setRange(0, 1000)
        balk.setTextVisible(False)
        balk.setFixedSize(420, 8)
        balk.setStyleSheet(
            f"QProgressBar {{ background: {t.surface_2}; border: 1px solid {t.border}; border-radius: 4px; }}"
            f"QProgressBar::chunk {{ background: {t.accent}; border-radius: 3px; }}"
        )
        layout.addSpacing(4)
        layout.addWidget(balk, 0, Qt.AlignmentFlag.AlignHCenter)

        status = QLabel()
        status.setStyleSheet(f"color: {t.text}; font-size: 13px; font-weight: 600; background: transparent;")
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(status)

        eta = QLabel()
        eta.setProperty("role", "placeholderText")
        eta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(eta)

        self._zaagplan_balk, self._zaagplan_status, self._zaagplan_eta = balk, status, eta
        self._toon_zaagplan_voortgang()
        return kaart

    def _ververs_zaagplannen_paneel(self) -> None:
        _clear_layout(self._zaagplannen_content)
        self._zaagplan_balk = self._zaagplan_status = self._zaagplan_eta = None
        if self._zaagplan_worker is not None:
            self._zaagplannen_content.addWidget(self._bouw_zaagplan_bezig())
        elif self._zaagplannen is None:
            self._zaagplannen_content.addWidget(self._bouw_zaagplan_start())
        else:
            self._zaagplannen_content.addWidget(self._bouw_zaagplan_resultaat())

    # ------------------------------------------------------------------
    # PDF-export: alle platen + de zaaglijst in één bestand
    # ------------------------------------------------------------------
    def _exporteer_pdf(self) -> None:
        if not self._zaagplannen:
            return
        standaard_naam = f"Zaagplan {self._project().naam}.pdf"
        pad, _ = QFileDialog.getSaveFileName(self, "Zaagplan opslaan als PDF", standaard_naam, "PDF-bestanden (*.pdf)")
        if not pad:
            return
        self._schrijf_zaagplannen_pdf(pad)

    def _schrijf_zaagplannen_pdf(self, pad: str) -> None:
        schrijf_zaagplannen_pdf(
            pad,
            project=self._project(),
            zaagplannen=self._zaagplannen,
            strategie_label=_STRATEGIE_LABEL[self._zaagplan_strategie],
            materialen=self._materialen,
            sort_niveaus=self._sort_niveaus,
        )

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
        toolbar.setSpacing(10)
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
        pdf_btn = QPushButton("  Alles + zaaglijst als PDF")
        pdf_btn.setProperty("role", "primary")
        pdf_btn.setIcon(icon("download", "#12141B", 13))
        pdf_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pdf_btn.clicked.connect(self._exporteer_pdf)
        toolbar.addWidget(pdf_btn)
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
        afmeting_tekst = f"{mat.lengte:g} × {mat.breedte:g} mm"
        if plan.is_reststuk:
            tag.setText("RESTSTUK")
            afmeting_tekst += "  ·  Reststuk uit de bibliotheek"
            if plan.platen_totaal > 1:
                afmeting_tekst += f" ({plan.plaat_nummer} van {plan.platen_totaal})"
        elif plan.platen_totaal > 1:
            afmeting_tekst += f"  ·  Plaat {plan.plaat_nummer} van {plan.platen_totaal}"
        afmeting_label = QLabel(afmeting_tekst)
        afmeting_label.setProperty("role", "docMeta")
        head_layout.addWidget(afmeting_label)
        head_layout.addStretch(1)
        layout.addWidget(head)

        plate_wrap = QFrame()
        plate_wrap.setObjectName("ZaagplanPlateWrap")
        plate_layout = QVBoxLayout(plate_wrap)
        plate_layout.setContentsMargins(16, 16, 16, 10)
        plate_layout.addWidget(ZaagplaatWidget(plan.resultaat, plan.naam_voor, self._theme))
        layout.addWidget(plate_wrap)

        if plan.resultaat.niet_geplaatst:
            layout.addWidget(self._bouw_niet_geplaatst_banner(plan))

        layout.addWidget(self._bouw_onderdelen_tabel(plan))
        layout.addWidget(self._bouw_zaagplan_footer(plan))

        return kaart

    def _bouw_niet_geplaatst_banner(self, plan: PlaatZaagplan) -> QWidget:
        """Nette, kaart-achtige weergave van de niet-geplaatste onderdelen
        op deze plaat (i.p.v. een kale meerregelige ⚠-tekst): een
        kop-regel met het totaal, en per item de naam + de reden waarom
        de motor het niet kwijt kon (zie ``ZaagplanResultaat.
        niet_geplaatst_redenen``)."""

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(16, 0, 16, 10)

        banner = QFrame()
        banner.setObjectName("NietGeplaatstBanner")
        layout = QVBoxLayout(banner)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        wrapper_layout.addWidget(banner)

        tellingen: dict[tuple[str, str], int] = {}
        for uid in plan.resultaat.niet_geplaatst:
            sleutel = (plan.naam_voor(uid), plan.reden_voor(uid))
            tellingen[sleutel] = tellingen.get(sleutel, 0) + 1
        totaal = sum(tellingen.values())

        kop = QHBoxLayout()
        kop.setSpacing(8)
        kop_icoon = QLabel()
        kop_icoon.setPixmap(icon_pixmap("warning", self._theme.warning_ink, 14))
        kop_icoon.setStyleSheet("background: transparent;")
        kop.addWidget(kop_icoon)
        kop_tekst = QLabel(f"{totaal} {'onderdeel' if totaal == 1 else 'onderdelen'} niet geplaatst op deze plaat")
        kop_tekst.setProperty("role", "warningHeading")
        kop.addWidget(kop_tekst)
        kop.addStretch(1)
        layout.addLayout(kop)

        for (naam, reden), aantal in sorted(tellingen.items()):
            rij = QHBoxLayout()
            rij.setSpacing(8)
            bullet = QLabel("•")
            bullet.setProperty("role", "warningItemBullet")
            bullet.setFixedWidth(10)
            rij.addWidget(bullet)

            tekst_col = QVBoxLayout()
            tekst_col.setSpacing(1)
            naam_tekst = naam + (f"  ×{aantal}" if aantal > 1 else "")
            naam_label = QLabel(naam_tekst)
            naam_label.setProperty("role", "warningItemName")
            tekst_col.addWidget(naam_label)
            reden_label = QLabel(reden or "Niet geplaatst.")
            reden_label.setProperty("role", "warningItemReden")
            reden_label.setWordWrap(True)
            tekst_col.addWidget(reden_label)
            rij.addLayout(tekst_col, 1)
            layout.addLayout(rij)

        return wrapper

    def _bouw_onderdelen_tabel(self, plan: PlaatZaagplan) -> QTableWidget:
        # De "Nr"-kolom toont dezelfde positienummers als de genummerde
        # bolletjes op de plaat (ZaagplaatWidget enumereert
        # plan.resultaat.plaatsingen in dezelfde volgorde) — bij meerdere
        # plaatsingen van hetzelfde onderdeel staan al hun nummers,
        # komma-gescheiden, in één rij.
        groepen: dict[str, list] = {}
        posities: dict[str, list[int]] = {}
        volgorde: list[str] = []
        for i, p in enumerate(plan.resultaat.plaatsingen, start=1):
            if p.onderdeel_id not in groepen:
                groepen[p.onderdeel_id] = []
                posities[p.onderdeel_id] = []
                volgorde.append(p.onderdeel_id)
            groepen[p.onderdeel_id].append(p)
            posities[p.onderdeel_id].append(i)

        tabel = QTableWidget(len(volgorde), 6)
        tabel.setObjectName("LibraryTable")
        tabel.setHorizontalHeaderLabels(["Nr", "Omschrijving", "Aantal", "Afmeting (mm)", "Kantenband", "Herkomst"])
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
        for col, breedte in enumerate([50, 260, 90, 140, 140]):
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
            nr_tekst = ", ".join(str(n) for n in posities[oid])
            waarden = [nr_tekst, naam, str(len(plaatsingen)), f"{eerste.breedte:g} × {eerste.hoogte:g}", kantenband]
            for col, tekst in enumerate(waarden):
                tabel.setCellWidget(row, col, self._cel_tekst(tekst))
            tabel.setCellWidget(row, 5, self._cel_herkomst(herkomst))

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
            ("Zaagsnede", f"{mat.kerf:g} mm"),
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
        self._ververs_labels_paneel()
        self._ververs_reststukken_paneel()
