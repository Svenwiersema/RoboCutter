"""Modelkopie-tabblad: één model uit een project bewerken, als eigen
sluitbaar tabblad (tabsleutel ``f"projectmodel:{project_id}:{instantie_id}"``,
zie ``MainWindow._open_tab_projectmodel``), geopend via het potlood bij
een model in de Samenstelling van ``project_detail_page.py``.

Op Svens verzoek: "ik wil ook rechtstreeks vanuit projecten een model
kunnen bewerken en dit dan binnen een project houden of opslaan in
modellen bibliotheek en ook optie om op te slaan als nieuwe model". De
HTML-mockup hiervan is door Sven goedgekeurd. Een model in een project
is een vaste, platgeslagen kopie (hoofdstuk 4, zie
``ProjectModelInstantie``); dit scherm bewerkt die kopie:

- Een onderdeel opslaan/toevoegen gaat meteen de projectkopie in
  (``ProjectenBibliotheek.model_instantie_onderdelen_opslaan``) — de
  modellenbibliotheek blijft ongewijzigd. Wat afwijkt van het
  bibliotheekmodel krijgt een "gewijzigd"-label.
- Een onderdeel verwijderen gaat níet meteen de opslag in (Sven: "dit kan
  per ongeluk gaan"): de rij wordt doorgestreept, kan teruggezet worden, en
  wordt pas bij een van de drie opslaan-keuzes echt verwijderd.
- Onderaan drie keuzes: alleen in dit project, ook in de
  modellenbibliotheek (overschrijven, met bevestiging; niet bij een
  bibliotheekmodel met submodellen — Svens keuze, zie
  ``ModelHeeftSubmodellenError``), of als nieuw model (daarna hoort de
  kopie bij dat nieuwe model).

Geen modal pop-ups: bevestigen gebeurt inline in de keuze zelf, en elke
opslaan-actie toont een ``OpslagMelding``. Onderdelen-formulier en
veld-helpers zijn, volgens de conventie in deze codebase, per bestand
gedupliceerd (zelfde opbouw als ``model_detail_page.py``).
"""

from __future__ import annotations

import uuid
from typing import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.materialen.models import MateriaalStatus
from robocutter.modellen.bibliotheek import ModellenBibliotheek
from robocutter.modellen.models import ModelOnderdeel, Nerfrichting, Rand
from robocutter.projecten.bibliotheek import ModelHeeftSubmodellenError, OnbekendModelError, ProjectenBibliotheek
from robocutter.projecten.models import Project, ProjectModelInstantie
from robocutter.ui.icons import icon
from robocutter.ui.theme import Theme
from robocutter.ui.widgets.opslag_melding import OpslagMelding
from robocutter.ui.widgets.randen_diagram import RandenDiagram

_NERF_LABEL = {
    Nerfrichting.GEEN: "Geen",
    Nerfrichting.LANGE_ZIJDE: "Lange zijde",
    Nerfrichting.KORTE_ZIJDE: "Korte zijde",
}
_RAND_LABEL = {Rand.BOVEN: "Boven", Rand.ONDER: "Onder", Rand.LINKS: "Links", Rand.RECHTS: "Rechts"}


def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
        elif item.layout() is not None:
            _clear_layout(item.layout())


class ProjectModelPage(QWidget):
    def __init__(
        self,
        project_id: str,
        instantie_id: str,
        projecten: ProjectenBibliotheek,
        modellen: ModellenBibliotheek,
        materialen: MaterialenBibliotheek,
        theme: Theme,
        on_project_gewijzigd: Callable[[], None] | None = None,
        on_bibliotheek_gewijzigd: Callable[[str], None] | None = None,
        on_open_project: Callable[[], None] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.project_id = project_id
        self.instantie_id = instantie_id
        self._projecten = projecten
        self._modellen = modellen
        self._materialen = materialen
        self._theme = theme
        self._melding = OpslagMelding(self, theme)
        self._on_project_gewijzigd = on_project_gewijzigd
        self._on_bibliotheek_gewijzigd = on_bibliotheek_gewijzigd
        self._on_open_project = on_open_project

        self._werk_onderdelen: list[ModelOnderdeel] = []
        self._bewerk_onderdeel_index: int | None = None
        # Indexen in _werk_onderdelen die pas bij een opslaan-keuze
        # verwijderd worden (zie de module-docstring).
        self._te_verwijderen: set[int] = set()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_view(), 1)
        self._laad()

    # ------------------------------------------------------------------
    # Gegevens
    # ------------------------------------------------------------------
    def _project(self) -> Project:
        return self._projecten.ophalen(self.project_id)

    def _instantie(self) -> ProjectModelInstantie | None:
        try:
            project = self._project()
        except KeyError:
            return None
        return next((i for i in project.modelinstanties if i.id == self.instantie_id), None)

    def _bronmodel_status(self) -> str:
        """"ok", "submodellen" of "weg" — bepaalt of terugschrijven naar de
        bibliotheek kan."""
        instantie = self._instantie()
        if instantie is None:
            return "weg"
        try:
            model = self._modellen.ophalen(instantie.model_id)
        except KeyError:
            return "weg"
        return "submodellen" if model.submodellen else "ok"

    def tab_titel(self) -> str:
        instantie = self._instantie()
        if instantie is None:
            return "Verwijderd model"
        try:
            projectnaam = self._project().naam
        except KeyError:
            projectnaam = "?"
        return f"{instantie.model_naam} · {projectnaam}"

    # ------------------------------------------------------------------
    # Thema: zelfde bewuste volledige herbouw als de andere pagina's
    # ------------------------------------------------------------------
    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        self._melding.set_theme(theme)
        layout = self.layout()
        _clear_layout(layout)
        layout.addWidget(self._build_view(), 1)
        self._laad()

    # ------------------------------------------------------------------
    # Opbouw
    # ------------------------------------------------------------------
    def _build_view(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setObjectName("MainScroll")
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setObjectName("MainScrollContent")
        outer = QVBoxLayout(content)
        outer.setContentsMargins(28, 22, 28, 20)
        outer.setSpacing(18)

        outer.addLayout(self._build_head())

        self._uitleg = self._notitie(
            "Je bewerkt de kopie van dit model in dit project. De modellenbibliotheek verandert pas als je daar "
            "onderaan voor kiest. Andere projecten houden altijd hun eigen kopie."
        )
        outer.addWidget(self._uitleg)

        self._validation_banner = QFrame()
        self._validation_banner.setObjectName("ValidationBanner")
        banner_layout = QVBoxLayout(self._validation_banner)
        banner_layout.setContentsMargins(12, 10, 12, 10)
        self._validation_label = QLabel("")
        self._validation_label.setProperty("role", "validationText")
        self._validation_label.setWordWrap(True)
        banner_layout.addWidget(self._validation_label)
        self._validation_banner.hide()
        outer.addWidget(self._validation_banner)

        self._inhoud = QWidget()
        inhoud_layout = QVBoxLayout(self._inhoud)
        inhoud_layout.setContentsMargins(0, 0, 0, 0)
        inhoud_layout.setSpacing(18)
        self._onderdelen_label = QLabel("ONDERDELEN (0)")
        self._onderdelen_label.setProperty("role", "fieldSectionLabel")
        inhoud_layout.addWidget(self._onderdelen_label)
        inhoud_layout.addWidget(self._build_onderdelen_kaart())
        opslaan_label = QLabel("OPSLAAN")
        opslaan_label.setProperty("role", "fieldSectionLabel")
        inhoud_layout.addWidget(opslaan_label)
        self._status_label = QLabel("")
        self._status_label.setProperty("role", "fieldHint")
        inhoud_layout.addWidget(self._status_label)
        # Onder de tabel (bij de opslaan-keuzes) i.p.v. erboven, zodat de
        # rijen niet verspringen als je iets verwijdert (Sven).
        self._verwijder_hint = QLabel("")
        self._verwijder_hint.setWordWrap(True)
        self._verwijder_hint.hide()
        inhoud_layout.addWidget(self._verwijder_hint)
        inhoud_layout.addLayout(self._build_keuzes())
        outer.addWidget(self._inhoud)

        self._weg_label = QLabel(
            "Dit model staat niet meer in het project (verwijderd uit de Samenstelling). Sluit dit tabblad."
        )
        self._weg_label.setProperty("role", "placeholderText")
        self._weg_label.setWordWrap(True)
        self._weg_label.hide()
        outer.addWidget(self._weg_label)
        outer.addStretch(1)

        scroll.setWidget(content)
        return scroll

    def _notitie(self, tekst: str) -> QFrame:
        t = self._theme
        kaart = QFrame()
        kaart.setObjectName("ModelKopieNotitie")
        kaart.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        kaart.setStyleSheet(
            f"QFrame#ModelKopieNotitie {{ background: {t.accent_soft}; border: 1px solid {t.accent_soft_border};"
            f" border-radius: 10px; }} QLabel {{ background: transparent; color: {t.text}; font-size: 13px; }}"
        )
        layout = QHBoxLayout(kaart)
        layout.setContentsMargins(14, 11, 14, 11)
        label = QLabel(tekst)
        label.setWordWrap(True)
        layout.addWidget(label)
        return kaart

    def _build_head(self) -> QVBoxLayout:
        wrapper = QVBoxLayout()
        wrapper.setSpacing(8)
        self._breadcrumb = QPushButton("")
        self._breadcrumb.setProperty("role", "breadcrumbLink")
        self._breadcrumb.setIcon(icon("folder", self._theme.text_faint, 12))
        self._breadcrumb.setIconSize(QSize(12, 12))
        self._breadcrumb.setCursor(Qt.CursorShape.PointingHandCursor)
        if self._on_open_project is not None:
            self._breadcrumb.clicked.connect(self._on_open_project)
        wrapper.addWidget(self._breadcrumb)

        titel_rij = QHBoxLayout()
        titel_rij.setSpacing(10)
        self._titel_label = QLabel("")
        self._titel_label.setObjectName("PageTitle")
        self._titel_label.setWordWrap(True)
        titel_rij.addWidget(self._titel_label, 1)
        self._pill = QLabel("")
        self._pill.setProperty("role", "tagChip")
        titel_rij.addWidget(self._pill, 0, Qt.AlignmentFlag.AlignVCenter)
        wrapper.addLayout(titel_rij)

        self._sub_label = QLabel("")
        self._sub_label.setObjectName("PageSub")
        wrapper.addWidget(self._sub_label)
        return wrapper

    # ------------------------------------------------------------------
    # Veld-helpers (zelfde als model_detail_page.py)
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

    def _field_spin(self) -> tuple[QFrame, QDoubleSpinBox]:
        field = QDoubleSpinBox()
        field.setProperty("role", "fieldSpin")
        field.setRange(0.01, 100000.0)
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
            # .value i.p.v. het enum zelf: een str-Enum komt via
            # setProperty als kale str terug (zie CLAUDE.md).
            btn.setProperty("waarde", waarde.value)
            group.addButton(btn)
            layout.addWidget(btn, 1)
        group.buttons()[0].setChecked(True)
        return container, group

    # ------------------------------------------------------------------
    # Onderdelen: lijst links, formulier rechts (zelfde split-kaart)
    # ------------------------------------------------------------------
    def _build_onderdelen_kaart(self) -> QFrame:
        kaart = QFrame()
        kaart.setObjectName("TableCard")
        outer = QHBoxLayout(kaart)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        links = QWidget()
        links_layout = QVBoxLayout(links)
        links_layout.setContentsMargins(0, 0, 0, 0)
        links_layout.setSpacing(0)
        self._onderdelen_container = QVBoxLayout()
        self._onderdelen_container.setSpacing(0)
        links_layout.addLayout(self._onderdelen_container)
        self._onderdelen_leeg_label = QLabel("Deze kopie heeft geen onderdelen.")
        self._onderdelen_leeg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._onderdelen_leeg_label.setStyleSheet(f"color: {self._theme.text_faint}; font-size: 13px; padding: 32px 0;")
        links_layout.addWidget(self._onderdelen_leeg_label)
        links_layout.addStretch(1)
        outer.addWidget(links, 1)

        rechts = QFrame()
        rechts.setProperty("role", "splitAdd")
        rechts.setFixedWidth(300)
        rl = QVBoxLayout(rechts)
        rl.setContentsMargins(18, 16, 18, 16)
        rl.setSpacing(10)

        self._onderdeel_form_titel = QLabel("NIEUW ONDERDEEL")
        self._onderdeel_form_titel.setProperty("role", "fieldSectionLabel")
        rl.addWidget(self._onderdeel_form_titel)

        rl.addWidget(self._field_label("Naam"))
        self._of_naam = self._field_input()
        self._of_naam.setPlaceholderText("bijv. Zijkant links")
        rl.addWidget(self._of_naam)

        rl.addWidget(self._field_label("Materiaal"))
        self._of_materiaal = QComboBox()
        self._of_materiaal.setProperty("role", "field")
        rl.addWidget(self._of_materiaal)

        afmeting_rij = QHBoxLayout()
        afmeting_rij.setSpacing(8)
        breedte_col = QVBoxLayout()
        breedte_col.addWidget(self._field_label("Breedte mm"))
        breedte_wrap, self._of_breedte = self._field_spin()
        breedte_col.addWidget(breedte_wrap)
        afmeting_rij.addLayout(breedte_col)
        wissel = QToolButton()
        wissel.setIcon(icon("swap", self._theme.text_muted, 15))
        wissel.setAutoRaise(True)
        wissel.setCursor(Qt.CursorShape.PointingHandCursor)
        wissel.setToolTip("Breedte en hoogte omwisselen (bv. per ongeluk verwisseld ingevoerd)")
        wissel.clicked.connect(self._of_wissel_breedte_hoogte)
        afmeting_rij.addWidget(wissel, 0, Qt.AlignmentFlag.AlignBottom)
        hoogte_col = QVBoxLayout()
        hoogte_col.addWidget(self._field_label("Hoogte mm"))
        hoogte_wrap, self._of_hoogte = self._field_spin()
        hoogte_col.addWidget(hoogte_wrap)
        afmeting_rij.addLayout(hoogte_col)
        rl.addLayout(afmeting_rij)
        self._of_breedte.valueChanged.connect(self._of_ververs_rand_diagram)
        self._of_hoogte.valueChanged.connect(self._of_ververs_rand_diagram)

        rl.addWidget(self._field_label("Aantal"))
        aantal_wrap, self._of_aantal = self._field_spin_int(minimum=1, maximum=1000)
        rl.addWidget(aantal_wrap)

        rl.addWidget(self._field_label("Nerfrichting"))
        nerf_widget, self._of_nerf_group = self._segmented(
            [(Nerfrichting.GEEN, "Geen"), (Nerfrichting.LANGE_ZIJDE, "Lange zijde"), (Nerfrichting.KORTE_ZIJDE, "Korte zijde")]
        )
        rl.addWidget(nerf_widget)

        rl.addWidget(self._field_label("Kantenband op"))
        self._of_rand_diagram = RandenDiagram(self._theme)
        rl.addWidget(self._of_rand_diagram)

        self._of_fabriek = QCheckBox("Fabriekskantenband vereist")
        rl.addWidget(self._of_fabriek)

        groep_rij = QHBoxLayout()
        groep_rij.setSpacing(8)
        groep_naam_col = QVBoxLayout()
        groep_naam_col.addWidget(self._field_label("Groepsnaam"))
        self._of_groep_naam = self._field_input()
        self._of_groep_naam.setPlaceholderText("optioneel — leeg = geen groep")
        groep_naam_col.addWidget(self._of_groep_naam)
        groep_rij.addLayout(groep_naam_col, 1)
        groep_volgorde_col = QVBoxLayout()
        groep_volgorde_col.addWidget(self._field_label("Volgorde"))
        groep_volgorde_wrap, self._of_groep_volgorde = self._field_spin_int(minimum=0, maximum=1000)
        groep_volgorde_col.addWidget(groep_volgorde_wrap)
        groep_rij.addLayout(groep_volgorde_col)
        rl.addLayout(groep_rij)

        knoppen = QHBoxLayout()
        self._btn_onderdeel_annuleren = QPushButton("Annuleren")
        self._btn_onderdeel_annuleren.setProperty("role", "ghost")
        self._btn_onderdeel_annuleren.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_onderdeel_annuleren.clicked.connect(self._reset_onderdeel_form)
        self._btn_onderdeel_annuleren.hide()
        knoppen.addWidget(self._btn_onderdeel_annuleren)
        self._btn_onderdeel_opslaan = QPushButton("  Onderdeel toevoegen")
        self._btn_onderdeel_opslaan.setProperty("role", "primary")
        self._btn_onderdeel_opslaan.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_onderdeel_opslaan.clicked.connect(self._onderdeel_opslaan_klik)
        knoppen.addWidget(self._btn_onderdeel_opslaan, 1)
        rl.addLayout(knoppen)
        hint = QLabel("Slaat meteen op in de kopie in dit project. Het label \"gewijzigd\" laat zien wat afwijkt van het bibliotheekmodel.")
        hint.setProperty("role", "fieldHint")
        hint.setWordWrap(True)
        rl.addWidget(hint)
        rl.addStretch(1)
        outer.addWidget(rechts)
        return kaart

    # ------------------------------------------------------------------
    # Opslaan-keuzes
    # ------------------------------------------------------------------
    def _keuze_kaart(self, objectnaam: str) -> tuple[QFrame, QVBoxLayout]:
        t = self._theme
        kaart = QFrame()
        kaart.setObjectName(objectnaam)
        kaart.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        kaart.setStyleSheet(
            f"QFrame#{objectnaam} {{ background: {t.surface}; border: 1px solid {t.border}; border-radius: 10px; }}"
            f"QFrame#{objectnaam}[uit=\"true\"] {{ background: {t.surface_2}; }}"
        )
        layout = QVBoxLayout(kaart)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        return kaart, layout

    def _keuze_titel(self, tekst: str) -> QLabel:
        label = QLabel(tekst)
        label.setStyleSheet(f"font-weight: 700; font-size: 13px; color: {self._theme.text}; background: transparent;")
        return label

    def _keuze_tekst(self, tekst: str = "") -> QLabel:
        label = QLabel(tekst)
        label.setWordWrap(True)
        label.setStyleSheet(f"font-size: 12px; color: {self._theme.text_muted}; background: transparent;")
        return label

    def _build_keuzes(self) -> QHBoxLayout:
        rij = QHBoxLayout()
        rij.setSpacing(12)

        # 1. alleen in dit project
        kaart, layout = self._keuze_kaart("KeuzeProject")
        layout.addWidget(self._keuze_titel("Alleen in dit project"))
        layout.addWidget(self._keuze_tekst("De kopie in dit project houdt je wijzigingen. De modellenbibliotheek blijft ongewijzigd."))
        layout.addStretch(1)
        btn = QPushButton("Opslaan in project")
        btn.setProperty("role", "primary")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self._opslaan_in_project)
        layout.addWidget(btn)
        rij.addWidget(kaart, 1)

        # 2. ook in de modellenbibliotheek
        self._bib_kaart, layout = self._keuze_kaart("KeuzeBibliotheek")
        layout.addWidget(self._keuze_titel("Ook in de modellenbibliotheek"))
        self._bib_tekst = self._keuze_tekst()
        layout.addWidget(self._bib_tekst)
        layout.addStretch(1)
        self._btn_bib = QPushButton("Opslaan in bibliotheek…")
        self._btn_bib.setProperty("role", "ghost")
        self._btn_bib.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_bib.clicked.connect(lambda: self._bib_bevestiging.show())
        layout.addWidget(self._btn_bib)
        self._bib_bevestiging = QWidget()
        bl = QVBoxLayout(self._bib_bevestiging)
        bl.setContentsMargins(0, 4, 0, 0)
        bl.setSpacing(6)
        bl.addWidget(self._keuze_tekst("Weet je het zeker? Het bibliotheekmodel wordt overschreven."))
        bk = QHBoxLayout()
        nee = QPushButton("Annuleren")
        nee.setProperty("role", "ghost")
        nee.setCursor(Qt.CursorShape.PointingHandCursor)
        nee.clicked.connect(lambda: self._bib_bevestiging.hide())
        ja = QPushButton("Ja, overschrijven")
        ja.setProperty("role", "primary")
        ja.setCursor(Qt.CursorShape.PointingHandCursor)
        ja.clicked.connect(self._opslaan_in_bibliotheek)
        bk.addWidget(nee)
        bk.addWidget(ja, 1)
        bl.addLayout(bk)
        self._bib_bevestiging.hide()
        layout.addWidget(self._bib_bevestiging)
        rij.addWidget(self._bib_kaart, 1)

        # 3. als nieuw model
        kaart, layout = self._keuze_kaart("KeuzeNieuw")
        layout.addWidget(self._keuze_titel("Als nieuw model"))
        layout.addWidget(self._keuze_tekst("Maakt een nieuw model in de bibliotheek. Deze kopie hoort daarna bij het nieuwe model."))
        layout.addStretch(1)
        self._btn_nieuw = QPushButton("Opslaan als nieuw model…")
        self._btn_nieuw.setProperty("role", "ghost")
        self._btn_nieuw.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_nieuw.clicked.connect(self._toon_nieuw_formulier)
        layout.addWidget(self._btn_nieuw)
        self._nieuw_formulier = QWidget()
        nl = QVBoxLayout(self._nieuw_formulier)
        nl.setContentsMargins(0, 4, 0, 0)
        nl.setSpacing(6)
        nl.addWidget(self._field_label("Naam van het nieuwe model"))
        self._in_nieuwe_naam = self._field_input()
        self._in_nieuwe_naam.returnPressed.connect(self._opslaan_als_nieuw_model)
        nl.addWidget(self._in_nieuwe_naam)
        nk = QHBoxLayout()
        nee = QPushButton("Annuleren")
        nee.setProperty("role", "ghost")
        nee.setCursor(Qt.CursorShape.PointingHandCursor)
        nee.clicked.connect(lambda: self._nieuw_formulier.hide())
        ja = QPushButton("Nieuw model opslaan")
        ja.setProperty("role", "primary")
        ja.setCursor(Qt.CursorShape.PointingHandCursor)
        ja.clicked.connect(self._opslaan_als_nieuw_model)
        nk.addWidget(nee)
        nk.addWidget(ja, 1)
        nl.addLayout(nk)
        self._nieuw_formulier.hide()
        layout.addWidget(self._nieuw_formulier)
        rij.addWidget(kaart, 1)
        return rij

    # ------------------------------------------------------------------
    # Laden / verversen
    # ------------------------------------------------------------------
    def _laad(self) -> None:
        instantie = self._instantie()
        weg = instantie is None
        self._inhoud.setVisible(not weg)
        self._uitleg.setVisible(not weg)
        self._weg_label.setVisible(weg)
        if weg:
            self._titel_label.setText("Verwijderd model")
            self._sub_label.setText("")
            self._pill.hide()
            return
        self._werk_onderdelen = list(instantie.onderdelen)
        self._te_verwijderen = set()
        self._validation_banner.hide()
        self._bib_bevestiging.hide()
        self._nieuw_formulier.hide()
        self._reset_onderdeel_form()
        self._ververs()

    def herlaad(self) -> None:
        """Opnieuw inlezen (bv. na "bijwerken naar laatste versie" of een
        wijziging vanuit het projecttabblad)."""
        self._laad()

    def herlaad_als_gewijzigd(self) -> None:
        """Alleen volledig herladen (en dus een half ingevuld formulier
        wissen) als de kopie zelf van buitenaf veranderd is; anders alleen
        kop/status bijwerken (bv. een nieuwe projectnaam)."""
        instantie = self._instantie()
        if instantie is None or instantie.onderdelen != self._werk_onderdelen:
            self._laad()
        else:
            self._ververs()

    def _ververs(self) -> None:
        instantie = self._instantie()
        if instantie is None:
            self._laad()
            return
        project = self._project()
        self._breadcrumb.setText(f"  {project.naam.upper()} › SAMENSTELLING")
        self._titel_label.setText(instantie.model_naam)
        self._pill.setText(f"Bewerkt in project {project.naam}")
        self._pill.show()

        status = self._bronmodel_status()
        bron = {
            "ok": "kopie van bibliotheekmodel",
            "submodellen": "kopie van bibliotheekmodel met submodellen",
            "weg": "het bibliotheekmodel bestaat niet meer",
        }[status]
        self._sub_label.setText(f"{instantie.aantal}× in dit project · {bron}")

        afwijkingen = self._projecten.model_instantie_afwijkingen(self.project_id, self.instantie_id)
        gewijzigd, verwijderd = afwijkingen if afwijkingen is not None else (set(), 0)
        delen = []
        if gewijzigd:
            delen.append(f"{len(gewijzigd)} onderdeel wijkt af" if len(gewijzigd) == 1 else f"{len(gewijzigd)} onderdelen wijken af")
        if verwijderd:
            delen.append(f"{verwijderd} onderdeel verwijderd" if verwijderd == 1 else f"{verwijderd} onderdelen verwijderd")
        if afwijkingen is None:
            self._status_label.setText("Het bibliotheekmodel bestaat niet meer; vergelijken kan niet.")
        else:
            self._status_label.setText(
                ("Ten opzichte van het bibliotheekmodel: " + ", ".join(delen) + ".") if delen else "Gelijk aan het bibliotheekmodel."
            )

        self._bib_kaart.setProperty("uit", status != "ok")
        self._bib_kaart.style().unpolish(self._bib_kaart)
        self._bib_kaart.style().polish(self._bib_kaart)
        self._btn_bib.setEnabled(status == "ok")
        if status == "ok":
            self._bib_tekst.setText(
                f'Overschrijft "{instantie.model_naam}" in de bibliotheek. Andere projecten houden hun eigen kopie.'
            )
        elif status == "submodellen":
            self._bib_tekst.setText(
                "Kan niet bij dit model: het bibliotheekmodel is opgebouwd uit submodellen, en de projectkopie is "
                "platgeslagen. Overschrijven zou die opbouw wissen. Kies \"Als nieuw model\" om je wijzigingen toch "
                "in de bibliotheek te bewaren."
            )
        else:
            self._bib_tekst.setText(
                "Kan niet: het bibliotheekmodel bestaat niet meer. Kies \"Als nieuw model\" om deze kopie in de "
                "bibliotheek te bewaren."
            )

        self._onderdelen_label.setText(f"ONDERDELEN ({len(self._werk_onderdelen) - len(self._te_verwijderen)})")
        n = len(self._te_verwijderen)
        if n:
            t = self._theme
            self._verwijder_hint.setStyleSheet(
                f"background: transparent; color: {t.critical}; font-size: 12.5px; font-weight: 600;"
            )
            wat = "1 onderdeel wordt" if n == 1 else f"{n} onderdelen worden"
            self._verwijder_hint.setText(
                f"{wat} verwijderd bij opslaan — kies hieronder waar."
            )
        self._verwijder_hint.setVisible(bool(n))
        _clear_layout(self._onderdelen_container)
        self._onderdelen_leeg_label.setVisible(not self._werk_onderdelen)
        for index, onderdeel in enumerate(self._werk_onderdelen):
            self._onderdelen_container.addWidget(
                self._bouw_onderdeel_rij(onderdeel, index, onderdeel.id in gewijzigd, index in self._te_verwijderen)
            )

    def _bouw_onderdeel_rij(self, o: ModelOnderdeel, index: int, gewijzigd: bool, te_verwijderen: bool = False) -> QWidget:
        row = QFrame()
        row.setProperty("role", "subRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 7, 8, 7)
        layout.setSpacing(8)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        titel_rij = QHBoxLayout()
        titel_rij.setSpacing(8)
        titel = QLabel(o.naam + (f"  ×{o.aantal}" if o.aantal > 1 else ""))
        titel.setProperty("role", "matName")
        if te_verwijderen:
            titel.setText(titel.text() + "  · wordt verwijderd")
            titel.setStyleSheet(f"color: {self._theme.critical}; text-decoration: line-through;")
            row.setProperty("role", "subRowVerwijderd")
        titel_rij.addWidget(titel)
        if gewijzigd and not te_verwijderen:
            t = self._theme
            label = QLabel("gewijzigd")
            label.setStyleSheet(
                f"background: {t.warning_soft}; color: {t.warning_ink}; border-radius: 6px; padding: 1px 7px;"
                " font-size: 11px; font-weight: 600;"
            )
            titel_rij.addWidget(label)
        titel_rij.addStretch(1)
        info_col.addLayout(titel_rij)

        try:
            materiaal_naam = self._materialen.ophalen(o.materiaal_id).naam
        except KeyError:
            materiaal_naam = "onbekend materiaal"
        details = [f"{o.breedte:g}×{o.hoogte:g} mm", materiaal_naam]
        if o.nerfrichting_vereist != Nerfrichting.GEEN:
            details.append(_NERF_LABEL[o.nerfrichting_vereist].lower())
        if o.kantenband_randen:
            randen = ", ".join(_RAND_LABEL[r].lower() for r in sorted(o.kantenband_randen, key=lambda r: r.value))
            details.append(f"kantenband {randen}")
        if o.groep_id:
            details.append(f"groep {o.groep_id} #{o.groep_volgorde}")
        detail = QLabel(" · ".join(details))
        detail.setProperty("role", "matMeta")
        info_col.addWidget(detail)
        layout.addLayout(info_col, 1)

        if te_verwijderen:
            terug_btn = QToolButton()
            terug_btn.setProperty("role", "rowAction")
            terug_btn.setIcon(icon("undo", self._theme.critical, 14))
            terug_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            terug_btn.setToolTip("Terugzetten")
            terug_btn.clicked.connect(lambda: self._zet_onderdeel_terug(index))
            layout.addWidget(terug_btn)
            return row

        edit_btn = QToolButton()
        edit_btn.setProperty("role", "rowAction")
        edit_btn.setIcon(icon("pencil", self._theme.text_faint, 14))
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setToolTip("Bewerken")
        edit_btn.clicked.connect(lambda: self._bewerk_onderdeel(index))
        layout.addWidget(edit_btn)
        del_btn = QToolButton()
        del_btn.setProperty("role", "rowActionDanger")
        del_btn.setIcon(icon("trash", self._theme.text_faint, 14))
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setToolTip("Verwijderen uit deze kopie (definitief bij opslaan)")
        del_btn.clicked.connect(lambda: self._verwijder_onderdeel(index))
        layout.addWidget(del_btn)
        return row

    # ------------------------------------------------------------------
    # Onderdeel-formulier
    # ------------------------------------------------------------------
    def _ververs_materiaal_combo(self) -> None:
        huidige = self._of_materiaal.currentData()
        self._of_materiaal.clear()
        for materiaal in sorted(self._materialen.lijst(), key=lambda m: m.naam.lower()):
            label = f"{materiaal.naam} ({materiaal.type.value})"
            if materiaal.status != MateriaalStatus.ACTIEF:
                label += ", gearchiveerd"
            self._of_materiaal.addItem(label, materiaal.id)
        idx = self._of_materiaal.findData(huidige)
        if idx >= 0:
            self._of_materiaal.setCurrentIndex(idx)

    def _of_wissel_breedte_hoogte(self) -> None:
        breedte, hoogte = self._of_breedte.value(), self._of_hoogte.value()
        self._of_breedte.setValue(hoogte)
        self._of_hoogte.setValue(breedte)

    def _of_ververs_rand_diagram(self) -> None:
        self._of_rand_diagram.set_afmetingen(self._of_breedte.value(), self._of_hoogte.value())

    def _reset_onderdeel_form(self) -> None:
        self._bewerk_onderdeel_index = None
        self._onderdeel_form_titel.setText("NIEUW ONDERDEEL")
        self._btn_onderdeel_opslaan.setText("  Onderdeel toevoegen")
        self._btn_onderdeel_annuleren.hide()
        self._of_naam.clear()
        self._ververs_materiaal_combo()
        self._of_materiaal.setCurrentIndex(0 if self._of_materiaal.count() else -1)
        self._of_breedte.setValue(0)
        self._of_hoogte.setValue(0)
        self._of_aantal.setValue(1)
        self._of_nerf_group.buttons()[0].setChecked(True)
        self._of_rand_diagram.set_geselecteerde_randen(frozenset())
        self._of_ververs_rand_diagram()
        self._of_fabriek.setChecked(False)
        self._of_groep_naam.clear()
        self._of_groep_volgorde.setValue(0)

    def _bewerk_onderdeel(self, index: int) -> None:
        self._bewerk_onderdeel_index = index
        o = self._werk_onderdelen[index]
        self._onderdeel_form_titel.setText(f"ONDERDEEL BEWERKEN: {o.naam.upper()}")
        self._btn_onderdeel_opslaan.setText("  Wijzigingen opslaan")
        self._btn_onderdeel_annuleren.show()
        self._of_naam.setText(o.naam)
        self._ververs_materiaal_combo()
        idx = self._of_materiaal.findData(o.materiaal_id)
        if idx >= 0:
            self._of_materiaal.setCurrentIndex(idx)
        self._of_breedte.setValue(o.breedte)
        self._of_hoogte.setValue(o.hoogte)
        self._of_aantal.setValue(o.aantal)
        for btn in self._of_nerf_group.buttons():
            btn.setChecked(Nerfrichting(btn.property("waarde")) == o.nerfrichting_vereist)
        self._of_rand_diagram.set_geselecteerde_randen(o.kantenband_randen)
        self._of_ververs_rand_diagram()
        self._of_fabriek.setChecked(o.fabriekskantenband_vereist)
        self._of_groep_naam.setText(o.groep_id or "")
        self._of_groep_volgorde.setValue(o.groep_volgorde or 0)

    def _onderdeel_uit_formulier(self) -> ModelOnderdeel:
        huidig_id = ""
        if self._bewerk_onderdeel_index is not None:
            huidig_id = self._werk_onderdelen[self._bewerk_onderdeel_index].id
        groep_naam = self._of_groep_naam.text().strip() or None
        return ModelOnderdeel(
            id=huidig_id or uuid.uuid4().hex[:8],
            naam=self._of_naam.text().strip() or "Onderdeel",
            materiaal_id=self._of_materiaal.currentData() or "",
            breedte=self._of_breedte.value(),
            hoogte=self._of_hoogte.value(),
            aantal=self._of_aantal.value(),
            nerfrichting_vereist=Nerfrichting(self._of_nerf_group.checkedButton().property("waarde")),
            kantenband_randen=self._of_rand_diagram.geselecteerde_randen(),
            fabriekskantenband_vereist=self._of_fabriek.isChecked(),
            groep_id=groep_naam,
            groep_volgorde=(self._of_groep_volgorde.value() if groep_naam else None),
        )

    def _sla_kopie_op(self, nieuwe: list[ModelOnderdeel]) -> bool:
        try:
            self._projecten.model_instantie_onderdelen_opslaan(self.project_id, self.instantie_id, nieuwe)
        except ValueError as exc:
            self._toon_fout(str(exc))
            return False
        self._werk_onderdelen = list(nieuwe)
        self._validation_banner.hide()
        if self._on_project_gewijzigd is not None:
            self._on_project_gewijzigd()
        return True

    def _toon_fout(self, tekst: str) -> None:
        self._validation_label.setText("• " + "\n• ".join(tekst.split("; ")))
        self._validation_banner.show()

    def _onderdeel_opslaan_klik(self) -> None:
        onderdeel = self._onderdeel_uit_formulier()
        nieuwe = list(self._werk_onderdelen)
        if self._bewerk_onderdeel_index is not None:
            nieuwe[self._bewerk_onderdeel_index] = onderdeel
        else:
            nieuwe.append(onderdeel)
        if not self._sla_kopie_op(nieuwe):
            return
        self._melding.toon(f'Onderdeel "{onderdeel.naam}" opgeslagen', f"in de kopie in {self._project().naam}")
        self._reset_onderdeel_form()
        self._ververs()

    def _verwijder_onderdeel(self, index: int) -> None:
        # Alleen markeren (zie de module-docstring). De rij blijft in
        # _werk_onderdelen, zodat de indexen gelijk blijven aan de opgeslagen
        # kopie en het direct opslaan van een ánder onderdeel deze
        # verwijdering niet stilletjes meeneemt.
        self._te_verwijderen.add(index)
        if self._bewerk_onderdeel_index == index:
            self._reset_onderdeel_form()
        self._ververs()

    def _zet_onderdeel_terug(self, index: int) -> None:
        self._te_verwijderen.discard(index)
        self._ververs()

    def _verwijderingen_doorvoeren(self) -> bool:
        """Gemarkeerde verwijderingen echt in de projectkopie opslaan —
        de eerste stap van elke opslaan-keuze."""
        if not self._te_verwijderen:
            return True
        nieuwe = [o for i, o in enumerate(self._werk_onderdelen) if i not in self._te_verwijderen]
        # Vóór het opslaan leegmaken: _sla_kopie_op roept on_project_gewijzigd
        # aan, wat dit tabblad al kan verversen met de nieuwe, kortere lijst.
        gemarkeerd, self._te_verwijderen = self._te_verwijderen, set()
        if not self._sla_kopie_op(nieuwe):
            self._te_verwijderen = gemarkeerd
            return False
        self._reset_onderdeel_form()
        return True

    # ------------------------------------------------------------------
    # De drie opslaan-keuzes
    # ------------------------------------------------------------------
    def _opslaan_in_project(self) -> None:
        # Toegevoegde/gewijzigde onderdelen staan al in de projectkopie; dit
        # voert de gemarkeerde verwijderingen door en bevestigt de stand.
        if not self._verwijderingen_doorvoeren():
            return
        if not self._sla_kopie_op(list(self._werk_onderdelen)):
            return
        self._melding.toon(f"Opgeslagen in project {self._project().naam}", "de modellenbibliotheek is niet gewijzigd")
        self._ververs()

    def _opslaan_in_bibliotheek(self) -> None:
        self._bib_bevestiging.hide()
        if not self._verwijderingen_doorvoeren():
            return
        try:
            model = self._projecten.model_instantie_naar_bibliotheek(self.project_id, self.instantie_id)
        except (ModelHeeftSubmodellenError, OnbekendModelError, ValueError) as exc:
            self._toon_fout(str(exc))
            self._ververs()
            return
        self._validation_banner.hide()
        if self._on_project_gewijzigd is not None:
            self._on_project_gewijzigd()
        if self._on_bibliotheek_gewijzigd is not None:
            self._on_bibliotheek_gewijzigd(model.id)
        self._melding.toon("Opgeslagen in project én modellenbibliotheek", f'"{model.naam}" is bijgewerkt')
        self._ververs()

    def _toon_nieuw_formulier(self) -> None:
        instantie = self._instantie()
        if instantie is None:
            return
        self._in_nieuwe_naam.setText(f"{instantie.model_naam} ({self._project().naam})")
        self._nieuw_formulier.show()
        self._in_nieuwe_naam.setFocus()
        self._in_nieuwe_naam.selectAll()

    def _opslaan_als_nieuw_model(self) -> None:
        if not self._verwijderingen_doorvoeren():
            return
        try:
            model = self._projecten.model_instantie_als_nieuw_model(
                self.project_id, self.instantie_id, self._in_nieuwe_naam.text()
            )
        except ValueError as exc:
            self._toon_fout(str(exc))
            return
        self._nieuw_formulier.hide()
        self._validation_banner.hide()
        self._werk_onderdelen = list(self._instantie().onderdelen)
        if self._on_project_gewijzigd is not None:
            self._on_project_gewijzigd()
        if self._on_bibliotheek_gewijzigd is not None:
            self._on_bibliotheek_gewijzigd(model.id)
        self._melding.toon(f'Nieuw model "{model.naam}" opgeslagen', "deze kopie hoort nu bij het nieuwe model")
        self._ververs()
