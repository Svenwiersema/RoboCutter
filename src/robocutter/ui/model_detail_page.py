"""Modeldetail-tabblad: los, sluitbaar tabblad per geopend model
(analoog aan project_detail_page.py voor Projecten, op Svens verzoek
— "maak de modellen bewerken ook een apart scherm net zoals met
projecten"). Vervangt het uitklappaneel in modellen_page.py volledig:
zowel bewerken van een bestaand model (rijklik, geen apart
potlood-icoon, analoog aan de Projecten-rijklik, zie
``modellen_page.py``'s ``_KlikbareCel``) als een NIEUW model toevoegen
openen voortaan dit tabblad (``MainWindow._open_tab_model``,
tabsleutel ``f"model:{model_id}"`` resp. het tijdelijke ``"model:new"``
zolang een nieuw model nog niet voor het eerst is opgeslagen) — Sven
vroeg dit expliciet ook voor het nieuw-toevoegen-pad: "ik wil ook dat
met eerste instantie als je nieuw model toevoegd dat hij een tab opent
inplaats van het oude menu dat rechts verschijnt". Anders dan bij
Projecten (waar nieuw toevoegen nog wél het uitklappaneel gebruikt)
wijkt Modellen hier dus bewust af van het Projecten-patroon; het
uitklappaneel in modellen_page.py blijft in de code staan als
defensieve terugval voor het geval deze pagina ooit zonder
``on_open_model``-callback geconstrueerd wordt, maar wordt door de
echte app niet meer aangeroepen.

Anders dan ProjectDetailPage heeft dit scherm geen zijbalk met
meerdere panelen (Overzicht/Samenstelling/...) — een model heeft geen
vergelijkbare rijkdom aan submodules (geen klantgegevens, geen eigen
zaaglijst/zaagplannen-data), dus alle velden staan gewoon onder elkaar
in één scrollend formulier: basisgegevens, onderdelen en submodellen
(nesting). Het onderdelenformulier zelf staat, op Svens verzoek ("niet
dat dat hele menu eronder staat maar dat er dan een menu rechts
verschijnt waar je de info kan invullen"), als een vaste 300px-kaart
rechts naast de onderdelenlijst i.p.v. eronder — zelfde split-kaart-
patroon als ``project_detail_page.py``'s Losse onderdelen-kaart, zie
``_build_onderdelen_kaart``. Submodellen (nesting) bleven wel het
eenvoudigere inline-formulier onder de lijst, zoals voorheen in het
uitklappaneel van modellen_page.py.

Deelt de ``ModellenBibliotheek``/``MaterialenBibliotheek``-instanties
van ``main_window.py`` i.p.v. eigen verbindingen te openen — dit
scherm opent zelf geen SQLite-verbinding en heeft dus ook geen
``sluit_verbinding()``.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from typing import Callable

from PySide6.QtCore import QSize, Qt, QStringListModel
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QCompleter,
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
from robocutter.modellen.bibliotheek import ModellenBibliotheek, valideer
from robocutter.modellen.models import Model, ModelOnderdeel, Nerfrichting, Rand, SubModelVerwijzing
from robocutter.ui.icons import icon, icon_pixmap
from robocutter.ui.theme import Theme

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


class _ZoekVeld(QLineEdit):
    """Zelfde focus-triggert-de-QCompleter-popup-patroon als
    modellen_page.py/project_detail_page.py."""

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        if self.completer() is not None:
            self.completer().setCompletionPrefix(self.text())
            self.completer().complete()


class ModelDetailPage(QWidget):
    def __init__(
        self,
        model_id: str | None,
        modellen: ModellenBibliotheek,
        materialen: MaterialenBibliotheek,
        theme: Theme,
        on_gewijzigd: Callable[[], None] | None = None,
        on_open_modellen_tab: Callable[[], None] | None = None,
        on_aangemaakt: Callable[[str], None] | None = None,
        on_annuleren_nieuw: Callable[[], None] | None = None,
        parent=None,
    ) -> None:
        """``model_id=None`` opent dit tabblad in "nieuw model"-modus (op
        Svens verzoek dezelfde tab als bewerken, i.p.v. het oude
        uitklappaneel in modellen_page.py): het formulier start leeg en
        ``_opslaan`` roept ``bibliotheek.toevoegen`` i.p.v. ``bijwerken``
        aan, waarna ``on_aangemaakt(nieuw_id)`` MainWindow laat weten dat
        dit tabblad voortaan bij dat definitieve model hoort. Annuleren
        vóór de eerste keer opslaan heeft niets om naar terug te vallen,
        dus roept dan ``on_annuleren_nieuw`` aan (sluit het tabblad) i.p.v.
        ``_laad_model`` + terug naar de modellenlijst."""
        super().__init__(parent)
        self._model_id = model_id
        self.bibliotheek = modellen
        self.materialen = materialen
        self._theme = theme
        self._on_gewijzigd = on_gewijzigd
        self._on_open_modellen_tab = on_open_modellen_tab
        self._on_aangemaakt = on_aangemaakt
        self._on_annuleren_nieuw = on_annuleren_nieuw

        self._werk_onderdelen: list[ModelOnderdeel] = []
        self._werk_submodellen: list[SubModelVerwijzing] = []
        self._bewerk_onderdeel_index: int | None = None
        self._sm_naam_naar_id: dict[str, str] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self._view = self._build_view()
        outer.addWidget(self._view, 1)
        self._footer = self._build_footer()
        outer.addWidget(self._footer)

        self._laad_model()

    def _model(self) -> Model:
        if self._model_id is None:
            return Model(id="", naam="", omschrijving="", map="", tags=())
        return self.bibliotheek.ophalen(self._model_id)

    # ------------------------------------------------------------------
    # Thema: zelfde bewuste volledige-herbouw-aanpak als de andere pagina's
    # ------------------------------------------------------------------
    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        layout = self.layout()
        _clear_layout(layout)
        self._view = self._build_view()
        layout.addWidget(self._view, 1)
        self._footer = self._build_footer()
        layout.addWidget(self._footer)
        self._laad_model()

    def _meld_gewijzigd(self) -> None:
        if self._on_gewijzigd is not None:
            self._on_gewijzigd()

    # ------------------------------------------------------------------
    # Kop + inhoud
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

        body = QWidget()
        body.setObjectName("DrawerBody")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(22)
        body_layout.addLayout(self._build_basisgegevens_sectie())
        body_layout.addLayout(self._build_onderdelen_sectie())
        body_layout.addLayout(self._build_submodellen_sectie())
        outer.addWidget(body)
        outer.addStretch(1)

        scroll.setWidget(content)
        return scroll

    def _build_head(self) -> QVBoxLayout:
        wrapper = QVBoxLayout()
        wrapper.setSpacing(8)

        breadcrumb = QPushButton("  MODELLENBIBLIOTHEEK")
        breadcrumb.setProperty("role", "breadcrumbLink")
        breadcrumb.setIcon(icon("cube", self._theme.text_faint, 12))
        breadcrumb.setIconSize(QSize(12, 12))
        breadcrumb.setCursor(Qt.CursorShape.PointingHandCursor)
        if self._on_open_modellen_tab is not None:
            breadcrumb.clicked.connect(self._on_open_modellen_tab)
        wrapper.addWidget(breadcrumb)

        self._titel_label = QLabel("")
        self._titel_label.setObjectName("PageTitle")
        wrapper.addWidget(self._titel_label)

        self._sub_label = QLabel("")
        self._sub_label.setObjectName("PageSub")
        wrapper.addWidget(self._sub_label)

        return wrapper

    def _ververs_head(self) -> None:
        model = self._model()
        self._titel_label.setText(model.naam or ("Nieuw model" if self._model_id is None else "Naamloos model"))
        delen = [
            f"{len(model.onderdelen)} onderdeel" if len(model.onderdelen) == 1 else f"{len(model.onderdelen)} onderdelen",
            f"{len(model.submodellen)} submodel" if len(model.submodellen) == 1 else f"{len(model.submodellen)} submodellen",
        ]
        if model.map:
            delen.append(model.map)
        self._sub_label.setText(" · ".join(delen))

    # ------------------------------------------------------------------
    # Voettekst (annuleren/opslaan)
    # ------------------------------------------------------------------
    def _build_footer(self) -> QFrame:
        footer = QFrame()
        footer.setObjectName("ModelDetailFooter")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(28, 14, 28, 14)
        cancel_btn = QPushButton("Annuleren")
        cancel_btn.setProperty("role", "ghost")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self._annuleren)
        layout.addWidget(cancel_btn)
        layout.addStretch(1)
        save_btn = QPushButton("  Model opslaan")
        save_btn.setProperty("role", "primary")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._opslaan)
        layout.addWidget(save_btn)
        return footer

    def _annuleren(self) -> None:
        if self._model_id is None:
            # Een nog nooit opgeslagen nieuw model heeft niets om naar terug
            # te vallen — annuleren sluit dit tabblad dus meteen i.p.v. een
            # leeg formulier te blijven tonen.
            if self._on_annuleren_nieuw is not None:
                self._on_annuleren_nieuw()
            return
        self._laad_model()
        if self._on_open_modellen_tab is not None:
            self._on_open_modellen_tab()

    def _opslaan(self) -> None:
        tags = tuple(t.strip() for t in self._in_tags.text().split(",") if t.strip())
        kandidaat = Model(
            id=self._model_id or "",
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

        if self._model_id is None:
            nieuw = self.bibliotheek.toevoegen(kandidaat)
            self._model_id = nieuw.id
            if self._on_aangemaakt is not None:
                self._on_aangemaakt(nieuw.id)
        else:
            self.bibliotheek.bijwerken(kandidaat)
        self._meld_gewijzigd()
        self._laad_model()

    # ------------------------------------------------------------------
    # Gedeelde veld-helpers (zelfde patroon als modellen_page.py)
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
    # Secties
    # ------------------------------------------------------------------
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
        # Split-kaart (lijst links, invulformulier vast rechts, 300px) i.p.v.
        # het formulier onder de lijst — zelfde patroon als de Losse
        # onderdelen-kaart op de projectdetailpagina
        # (project_detail_page.py::_build_losse_onderdelen_kaart), op Svens
        # verzoek: "niet dat dat hele menu eronder staat maar dat er dan een
        # menu rechts verschijnt waar je de info kan invullen".
        section = QVBoxLayout()
        section.setSpacing(10)
        self._onderdelen_label = QLabel("ONDERDELEN (0)")
        self._onderdelen_label.setProperty("role", "fieldSectionLabel")
        section.addWidget(self._onderdelen_label)
        section.addWidget(self._build_onderdelen_kaart())
        return section

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
        self._onderdelen_leeg_label = QLabel("Nog geen onderdelen toegevoegd.")
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

        self._onderdeel_form_titel = QLabel("NIEUW ONDERDEEL")
        self._onderdeel_form_titel.setProperty("role", "fieldSectionLabel")
        rechts_layout.addWidget(self._onderdeel_form_titel)

        rechts_layout.addWidget(self._field_label("Naam"))
        self._of_naam = self._field_input()
        self._of_naam.setPlaceholderText("bijv. Zijkant links")
        rechts_layout.addWidget(self._of_naam)

        rechts_layout.addWidget(self._field_label("Materiaal"))
        self._of_materiaal = QComboBox()
        self._of_materiaal.setProperty("role", "field")
        rechts_layout.addWidget(self._of_materiaal)

        afmeting_rij = QHBoxLayout()
        afmeting_rij.setSpacing(8)
        breedte_col = QVBoxLayout()
        breedte_col.addWidget(self._field_label("Breedte mm"))
        breedte_wrap, self._of_breedte = self._field_spin()
        breedte_col.addWidget(breedte_wrap)
        afmeting_rij.addLayout(breedte_col)
        hoogte_col = QVBoxLayout()
        hoogte_col.addWidget(self._field_label("Hoogte mm"))
        hoogte_wrap, self._of_hoogte = self._field_spin()
        hoogte_col.addWidget(hoogte_wrap)
        afmeting_rij.addLayout(hoogte_col)
        rechts_layout.addLayout(afmeting_rij)

        rechts_layout.addWidget(self._field_label("Aantal"))
        aantal_wrap, self._of_aantal = self._field_spin_int(minimum=1, maximum=1000)
        rechts_layout.addWidget(aantal_wrap)

        rechts_layout.addWidget(self._field_label("Nerfrichting"))
        nerf_widget, self._of_nerf_group = self._segmented(
            [(Nerfrichting.GEEN, "Geen"), (Nerfrichting.LANGE_ZIJDE, "Lange zijde"), (Nerfrichting.KORTE_ZIJDE, "Korte zijde")]
        )
        rechts_layout.addWidget(nerf_widget)

        rechts_layout.addWidget(self._field_label("Kantenband op"))
        self._of_rand_buttons = self._rand_chip_rij(rechts_layout)

        self._of_fabriek = QCheckBox("Fabriekskantenband vereist")
        rechts_layout.addWidget(self._of_fabriek)

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
        rechts_layout.addLayout(groep_rij)
        groep_hint = QLabel(
            "Onderdelen met dezelfde groepsnaam blijven in vaste volgorde en roteren niet los van "
            "elkaar — bijv. laatjes die precies op elkaar moeten aansluiten."
        )
        groep_hint.setProperty("role", "fieldHint")
        groep_hint.setWordWrap(True)
        rechts_layout.addWidget(groep_hint)

        knoppen_rij = QHBoxLayout()
        self._btn_onderdeel_annuleren = QPushButton("Annuleren")
        self._btn_onderdeel_annuleren.setProperty("role", "ghost")
        self._btn_onderdeel_annuleren.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_onderdeel_annuleren.clicked.connect(self._reset_onderdeel_form)
        self._btn_onderdeel_annuleren.hide()
        knoppen_rij.addWidget(self._btn_onderdeel_annuleren)
        self._btn_onderdeel_opslaan = QPushButton("  Onderdeel toevoegen")
        self._btn_onderdeel_opslaan.setProperty("role", "primary")
        self._btn_onderdeel_opslaan.setIcon(icon("plus", "#12141B", 12))
        self._btn_onderdeel_opslaan.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_onderdeel_opslaan.clicked.connect(self._onderdeel_opslaan_klik)
        knoppen_rij.addWidget(self._btn_onderdeel_opslaan, 1)
        rechts_layout.addLayout(knoppen_rij)
        rechts_layout.addStretch(1)
        outer.addWidget(rechts)

        return kaart

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
        self._sm_search = _ZoekVeld()
        self._sm_search.setProperty("role", "field")
        self._sm_search.setPlaceholderText("Zoek een model…")
        self._sm_completer = QCompleter([])
        self._sm_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._sm_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._sm_completer.popup().setObjectName("ModelPickerPopup")
        self._sm_search.setCompleter(self._sm_completer)
        add_rij.addWidget(self._sm_search, 1)
        sm_aantal_wrap, self._sm_aantal = self._field_spin_int(minimum=1, maximum=1000)
        sm_aantal_wrap.setMaximumWidth(90)
        add_rij.addWidget(sm_aantal_wrap)
        btn_sm_add = QPushButton("+ Toevoegen")
        btn_sm_add.setProperty("role", "ghost")
        btn_sm_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sm_add.clicked.connect(self._submodel_toevoegen)
        add_rij.addWidget(btn_sm_add)
        section.addLayout(add_rij)

        self._sm_fout_label = QLabel("")
        self._sm_fout_label.setProperty("role", "validationText")
        self._sm_fout_label.setWordWrap(True)
        self._sm_fout_label.hide()
        section.addWidget(self._sm_fout_label)

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
        self._onderdelen_leeg_label.setVisible(not self._werk_onderdelen)
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
        self._onderdeel_form_titel.setText("NIEUW ONDERDEEL")
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
        self._onderdeel_form_titel.setText(f"ONDERDEEL BEWERKEN: {o.naam.upper()}")
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
        if kandidaat_id == self._model_id:
            return True
        bezocht: set[str] = set()
        stack = [kandidaat_id]
        while stack:
            model_id = stack.pop()
            if model_id == self._model_id:
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

    def _ververs_submodel_picker(self) -> None:
        self._sm_naam_naar_id = {}
        item_model = QStandardItemModel(self._sm_completer)
        for model in sorted(self.bibliotheek.lijst(), key=lambda m: m.naam.lower()):
            if model.id == self._model_id:
                continue
            cirkel = self._zou_cirkel_veroorzaken(model.id)
            label = model.naam + (" (cirkelverwijzing)" if cirkel else "")
            item = QStandardItem(label)
            if cirkel:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            else:
                self._sm_naam_naar_id[label] = model.id
            item_model.appendRow(item)
        self._sm_completer.setModel(item_model)

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
        model_id = self._sm_naam_naar_id.get(self._sm_search.text().strip())
        if not model_id:
            self._sm_fout_label.setText("Kies een model uit de lijst.")
            self._sm_fout_label.show()
            return
        self._sm_fout_label.hide()
        aantal = self._sm_aantal.value()
        self._sm_search.clear()
        self._sm_aantal.setValue(1)
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
        self._ververs_submodel_picker()

    # ------------------------------------------------------------------
    # Laden vanaf schijf (bij openen, en na annuleren/opslaan)
    # ------------------------------------------------------------------
    def _laad_model(self) -> None:
        m = self._model()
        self._in_naam.setText(m.naam)
        self._in_omschrijving.setText(m.omschrijving)
        self._in_map.setText(m.map)
        self._in_tags.setText(", ".join(m.tags))
        self._werk_onderdelen = [replace(o) for o in m.onderdelen]
        self._werk_submodellen = [replace(s) for s in m.submodellen]

        mappen = sorted({model.map for model in self.bibliotheek.lijst() if model.map})
        self._map_completer.setModel(QStringListModel(mappen, self._map_completer))
        self._sm_search.clear()
        self._sm_aantal.setValue(1)
        self._sm_fout_label.hide()
        self._validation_banner.hide()

        self._reset_onderdeel_form()
        self._ververs_onderdelen()
        self._ververs_submodel_picker()
        self._ververs_submodellen()
        self._ververs_head()
