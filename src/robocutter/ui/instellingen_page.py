"""Opties/instellingen-scherm: één simpel formulier voor de app-brede
instellingen uit ``robocutter.instellingen`` (thema, bedrijfslogo,
standaard zaagstrategie, zaagsnede-breedte,
werkvoorbereider-naam, opslaglocatie van het databasebestand).

Op Svens expliciete verzoek zonder HTML-mockup rechtstreeks in PySide6
gebouwd ("dit moet een simpel ui zijn") — geen sidebar, tabel of drawer
nodig, want ``Instellingen`` is één enkel record, geen bibliotheek met
losse records (zie ``robocutter.instellingen.models``).

Thema is de uitzondering op "alles achter de Opslaan-knop" (op Svens
verzoek): de segmented control Licht/Donker/Systeem past meteen live
toe zodra je erop klikt, i.p.v. pas na Opslaan. "Systeem" volgt
Windows' eigen licht/donker-voorkeur (``robocutter.ui.theme.
resolve_thema``/``systeem_is_donker``). Er is bewust geen aparte
thema-toggle-knop meer elders in de chrome — die is verwijderd nu
thema-keuze hier zit.

Deelt de ``InstellingenBeheer``-instantie met ``MainWindow`` (zelfde
patroon als de gedeelde ``MaterialenBibliotheek`` tussen de
Materialen-/Reststukken-/Modellenpagina's) en roept bij een gewijzigd
thema ``on_gewijzigd`` aan zodat de rest van de app (chrome, andere
tabbladen) meteen meewisselt i.p.v. pas na een herstart.

``standaard zaagstrategie`` heeft, op Svens verzoek, drie
keuze-opties (``_STRATEGIE_LABEL``/``_STRATEGIE_OMSCHRIJVING``):
"Horizontaal" (de standaard), "Verticaal" en "Guillotine". "Efficiënt"
(later "CNC (nesting)") is eruit gehaald: een CNC heeft geen zaagplan
nodig — de nesting-code is bewaard in de motor voor een latere
CNC-upgrade. Dit ging via meerdere
correctierondes (zie OVERDRACHT.md voor de volledige geschiedenis) —
met name: Sven corrigeerde zichzelf expliciet dat "efficient" en
"guillotine" NIET hetzelfde zijn (Guillotine is een écht apart,
strikter algoritme — uitsluitend doorlopende zaagsnedes — ook al
gebruikt de huidige "efficient"-implementatie zelf ook al een
guillotine-stijl interne splitsing, zie ``engine.py``), en dat
"efficient" juist wél hetzelfde was als wat eerder apart
"vrije_plaatsing"/"Nesting" heette (vrije plaatsing voor maximale
opbrengst) — die twee zijn daarom weer samengevoegd tot alleen
"efficient". Er was ook een vierde optie, "Stroken" (net als Rijen,
maar met overal dezelfde vaste strookhoogte), die later weer is
geschrapt als losse keuze: Sven zag 'm in de praktijk niet gebruikt
worden en het resultaat verschilt zelden merkbaar van "Rijen" (alleen
bij sterk uiteenlopende onderdeelhoogtes); inmiddels ook uit de motor
gehaald.
Alle drie overgebleven opties worden echt uitgevoerd door
``robocutter.optimalisatie.engine.genereer_zaagplan`` (zie de
docstring van die module voor de precieze algoritmes).
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QButtonGroup,
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from robocutter.backup.beheer import BackupBestand, lijst_backups
from robocutter.instellingen.beheer import InstellingenBeheer, OpslagVerplaatsenError
from robocutter.instellingen.models import (
    GELDIGE_BACKUP_FREQUENTIES,
    GELDIGE_LABEL_SCANCODES,
    GELDIGE_THEMAS,
    GELDIGE_ZAAGSTRATEGIEEN,
)
from robocutter.ui.backup_planner import (
    BackupPlanner,
    datum_tijd_tekst,
    grootte_tekst,
    leeftijd_tekst,
    tijd_tekst,
)
from robocutter.ui.icons import icon
from robocutter.ui.theme import Theme
from robocutter.ui.widgets.opslag_melding import OpslagMelding

_THEMA_LABEL = {"licht": "Licht", "donker": "Donker", "systeem": "Systeem"}
_LABEL_SCANCODE_LABEL = {"geen": "Geen", "qr": "QR-code", "barcode": "Barcode"}
_BACKUP_FREQUENTIE_LABEL = {"uur": "Elk uur", "dag": "Dagelijks", "week": "Wekelijks"}
# Zonder "Alle n tonen" alleen de nieuwste paar back-ups in de lijst.
_BACKUPS_KORT = 8
# Sven corrigeerde zichzelf hier expliciet: "efficient" en "guillotine" zijn
# NIET hetzelfde (ook al gebruikt de huidige "efficient"-implementatie zelf
# ook al een guillotine-stijl interne splitsing, zie engine.py) — Guillotine
# is een écht apart, strikter algoritme (alleen doorlopende zaagsnedes).
# "efficient" was juist wel hetzelfde als wat eerder "vrije_plaatsing" heette
# (vrije plaatsing voor maximale opbrengst) — die twee zijn daarom weer
# samengevoegd tot alleen "efficient". Later een CNC-strategie geworden en
# uit de keuzes gehaald (zie de module-docstring).
_STRATEGIE_LABEL = {
    "horizontaal": "Horizontaal",
    "verticaal": "Verticaal",
    "guillotine": "Guillotine",
}
# Alle drie worden echt uitgevoerd door
# robocutter.optimalisatie.engine.genereer_zaagplan — zie de docstring
# van die module voor de precieze algoritmes per strategie.
_STRATEGIE_OMSCHRIJVING = {
    "horizontaal": "Lange zijdes eerst in rijen over de volle plaatbreedte; de hoofdzaagsnedes lopen horizontaal en elke rij krijgt zijn eigen hoogte op basis van het grootste stuk erin — overzichtelijke zaagvolgorde.",
    "verticaal": "Zoals Horizontaal, maar in kolommen over de volle plaathoogte: de hoofdzaagsnedes lopen verticaal en elke kolom krijgt zijn eigen breedte op basis van het grootste stuk erin.",
    "guillotine": "Uitsluitend doorlopende zaagsnedes van rand tot rand — de gangbare beperking van de meeste paneelzagen.",
}


def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
        elif item.layout() is not None:
            _clear_layout(item.layout())


class InstellingenPage(QWidget):
    def __init__(
        self,
        beheer: InstellingenBeheer,
        theme: Theme,
        on_gewijzigd: Callable[[], None],
        backup_planner: BackupPlanner | None = None,
        on_terugzetten: Callable[[BackupBestand], str] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._beheer = beheer
        self._theme = theme
        self._melding = OpslagMelding(self, theme)
        self._on_gewijzigd = on_gewijzigd
        # Back-up (hoofdstuk 12, mockup backup-concept.html). Zonder planner
        # (bv. de losse test-ui) blijft het Back-up-blok weg.
        self._backup_planner = backup_planner
        self._on_terugzetten = on_terugzetten
        self._backup_alles_tonen = False
        self._backup_terug_keuze: Path | None = None
        if backup_planner is not None:
            backup_planner.gewijzigd.connect(self._ververs_backup)
            backup_planner.handmatig_gelukt.connect(
                lambda backup: self._melding.toon("Back-up gemaakt", f"in {backup.pad.parent}")
            )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._build_main())

    # ------------------------------------------------------------------
    # Thema: zelfde bewuste volledige-herbouw-aanpak als de andere
    # pagina's (zie materialen_page.py) — alleen bij een expliciete
    # thema-wissel, niet bij normaal gebruik.
    # ------------------------------------------------------------------
    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        self._melding.set_theme(theme)
        _clear_layout(self.layout())
        self.layout().addWidget(self._build_main())

    # ------------------------------------------------------------------
    # Opbouw
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

        title = QLabel("Instellingen")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        sub = QLabel("App-brede voorkeuren en de opslaglocatie van het databasebestand.")
        sub.setObjectName("PageSub")
        layout.addWidget(sub)

        layout.addWidget(self._build_algemeen_kaart())
        layout.addWidget(self._build_labels_kaart())
        layout.addWidget(self._build_opslag_kaart())
        if self._backup_planner is not None:
            layout.addWidget(self._build_backup_kaart())
        layout.addStretch(1)

        scroll.setWidget(content)
        return scroll

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
        field.setRange(0.0, 100.0)
        field.setDecimals(1)
        field.setSingleStep(0.5)
        field.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        return self._wrap_spin_met_stappen(field), field

    def _segmented(self, opties: list[tuple[str, str]], huidig: str) -> tuple[QWidget, QButtonGroup]:
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
            btn.setProperty("waarde", waarde)
            btn.setChecked(waarde == huidig)
            group.addButton(btn)
            layout.addWidget(btn, 1)
        return container, group

    def _build_banner(self) -> tuple[QFrame, QLabel]:
        banner = QFrame()
        banner.setObjectName("ValidationBanner")
        layout = QVBoxLayout(banner)
        layout.setContentsMargins(12, 10, 12, 10)
        label = QLabel("")
        label.setProperty("role", "validationText")
        label.setWordWrap(True)
        layout.addWidget(label)
        banner.hide()
        return banner, label

    def _toon_banner(self, banner: QFrame, label: QLabel, tekst: str, fout: bool) -> None:
        label.setText(tekst)
        label.setStyleSheet(f"color: {self._theme.critical if fout else self._theme.success_ink};")
        banner.show()

    def _build_algemeen_kaart(self) -> QFrame:
        kaart = QFrame()
        kaart.setObjectName("TableCard")
        layout = QVBoxLayout(kaart)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(12)

        sectie_label = QLabel("ALGEMEEN")
        sectie_label.setProperty("role", "fieldSectionLabel")
        layout.addWidget(sectie_label)

        instellingen = self._beheer.huidige

        layout.addWidget(self._field_label("Thema"))
        thema_widget, self._thema_group = self._segmented(
            [(waarde, _THEMA_LABEL[waarde]) for waarde in GELDIGE_THEMAS], instellingen.thema
        )
        # Thema is de uitzondering op "alles achter de Opslaan-knop": past
        # meteen live toe zodra je 'm aanklikt, i.p.v. pas na Opslaan — net
        # als thema-keuzes in de meeste andere Windows-apps.
        self._thema_group.buttonClicked.connect(self._thema_live_gewijzigd)
        layout.addWidget(thema_widget)

        layout.addWidget(self._field_label("Standaard zaagstrategie"))
        strategie_widget, self._strategie_group = self._segmented(
            [(waarde, _STRATEGIE_LABEL[waarde]) for waarde in GELDIGE_ZAAGSTRATEGIEEN],
            instellingen.standaard_zaagstrategie,
        )
        layout.addWidget(strategie_widget)
        self._strategie_hint = QLabel()
        self._strategie_hint.setProperty("role", "fieldHint")
        self._strategie_hint.setWordWrap(True)
        # Val terug op de eerste geldige waarde als een eerder opgeslagen
        # strategienaam inmiddels niet meer bestaat (bijv. na een latere
        # hernoeming) — dan geen KeyError, gewoon de eerste optie tonen.
        huidige_strategie = (
            instellingen.standaard_zaagstrategie
            if instellingen.standaard_zaagstrategie in GELDIGE_ZAAGSTRATEGIEEN
            else GELDIGE_ZAAGSTRATEGIEEN[0]
        )
        self._ververs_strategie_hint(huidige_strategie)
        layout.addWidget(self._strategie_hint)
        self._strategie_group.buttonClicked.connect(
            lambda btn: self._ververs_strategie_hint(btn.property("waarde"))
        )

        # Op Svens verzoek centraal i.p.v. per materiaal: wat het zaagblad
        # tussen twee onderdelen wegneemt.
        maten = QHBoxLayout()
        maten.setSpacing(12)
        kol = QVBoxLayout()
        kol.setSpacing(6)
        kol.addWidget(self._field_label("Zaagsnede-breedte (mm)"))
        zaag_wrap, self._in_zaagsnede = self._field_spin()
        self._in_zaagsnede.setValue(instellingen.zaagsnede)
        kol.addWidget(zaag_wrap)
        maten.addLayout(kol, 1)
        maten.addStretch(1)
        layout.addLayout(maten)
        maten_hint = QLabel("De ruimte die het zaagblad tussen twee onderdelen wegneemt; geldt voor alle materialen.")
        maten_hint.setProperty("role", "fieldHint")
        maten_hint.setWordWrap(True)
        layout.addWidget(maten_hint)

        layout.addWidget(self._field_label("Werkvoorbereider-naam"))
        self._in_werkvoorbereider = self._field_input()
        self._in_werkvoorbereider.setText(instellingen.werkvoorbereider_naam)
        layout.addWidget(self._in_werkvoorbereider)

        layout.addWidget(self._field_label("Bedrijfslogo"))
        logo_rij = QHBoxLayout()
        logo_rij.setSpacing(8)
        self._in_logo = self._field_input()
        self._in_logo.setText(instellingen.bedrijfslogo_pad or "")
        self._in_logo.setPlaceholderText("Geen logo geselecteerd")
        logo_rij.addWidget(self._in_logo, 1)
        logo_kiezen = QPushButton("Bestand kiezen…")
        logo_kiezen.setProperty("role", "ghost")
        logo_kiezen.setCursor(Qt.CursorShape.PointingHandCursor)
        logo_kiezen.clicked.connect(self._kies_logo)
        logo_rij.addWidget(logo_kiezen)
        layout.addLayout(logo_rij)

        self._algemeen_banner, self._algemeen_banner_label = self._build_banner()
        layout.addWidget(self._algemeen_banner)

        footer = QHBoxLayout()
        footer.addStretch(1)
        opslaan = QPushButton("Opslaan")
        opslaan.setProperty("role", "primary")
        opslaan.setCursor(Qt.CursorShape.PointingHandCursor)
        opslaan.clicked.connect(self._opslaan_algemeen)
        footer.addWidget(opslaan)
        layout.addLayout(footer)

        return kaart

    def _build_labels_kaart(self) -> QFrame:
        kaart = QFrame()
        kaart.setObjectName("TableCard")
        layout = QVBoxLayout(kaart)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(12)

        sectie_label = QLabel("LABELS")
        sectie_label.setProperty("role", "fieldSectionLabel")
        layout.addWidget(sectie_label)

        instellingen = self._beheer.huidige

        layout.addWidget(self._field_label("Scancode op label"))
        scancode_widget, self._scancode_group = self._segmented(
            [(waarde, _LABEL_SCANCODE_LABEL[waarde]) for waarde in GELDIGE_LABEL_SCANCODES],
            instellingen.label_scancode,
        )
        layout.addWidget(scancode_widget)
        hint = QLabel(
            "Onderdeel-ID, materiaal, projectnummer en afmeting staan altijd op het label — "
            "dit bepaalt alleen of, en welke, scanbare code erbij komt."
        )
        hint.setProperty("role", "fieldHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._chk_kantenband = QCheckBox("Kantenband-indicatie tonen")
        self._chk_kantenband.setChecked(instellingen.label_kantenband_indicatie)
        layout.addWidget(self._chk_kantenband)

        self._chk_nerf = QCheckBox("Nerfrichting-pijl tonen")
        self._chk_nerf.setChecked(instellingen.label_nerfrichting_pijl)
        layout.addWidget(self._chk_nerf)

        self._labels_banner, self._labels_banner_label = self._build_banner()
        layout.addWidget(self._labels_banner)

        footer = QHBoxLayout()
        footer.addStretch(1)
        opslaan = QPushButton("Opslaan")
        opslaan.setProperty("role", "primary")
        opslaan.setCursor(Qt.CursorShape.PointingHandCursor)
        opslaan.clicked.connect(self._opslaan_labels)
        footer.addWidget(opslaan)
        layout.addLayout(footer)

        return kaart

    def _build_opslag_kaart(self) -> QFrame:
        kaart = QFrame()
        kaart.setObjectName("TableCard")
        layout = QVBoxLayout(kaart)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(12)

        sectie_label = QLabel("OPSLAGLOCATIE DATABASEBESTAND")
        sectie_label.setProperty("role", "fieldSectionLabel")
        layout.addWidget(sectie_label)

        self._label_huidige_locatie = QLabel()
        self._label_huidige_locatie.setProperty("role", "fieldHint")
        self._label_huidige_locatie.setWordWrap(True)
        self._ververs_huidige_locatie()
        layout.addWidget(self._label_huidige_locatie)

        rij = QHBoxLayout()
        rij.setSpacing(8)
        self._in_map = self._field_input()
        self._in_map.setPlaceholderText("Kies een map…")
        rij.addWidget(self._in_map, 1)
        map_kiezen = QPushButton("Map kiezen…")
        map_kiezen.setProperty("role", "ghost")
        map_kiezen.setCursor(Qt.CursorShape.PointingHandCursor)
        map_kiezen.clicked.connect(self._kies_map)
        rij.addWidget(map_kiezen)
        layout.addLayout(rij)

        hint = QLabel(
            "Een bestaand databasebestand wordt automatisch meeverhuisd. Al geopende "
            "vensters gebruiken de nieuwe locatie pas na het herstarten van RoboCutter."
        )
        hint.setProperty("role", "fieldHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._opslag_banner, self._opslag_banner_label = self._build_banner()
        layout.addWidget(self._opslag_banner)

        footer = QHBoxLayout()
        footer.addStretch(1)
        wijzigen = QPushButton("Opslaglocatie wijzigen")
        wijzigen.setProperty("role", "primary")
        wijzigen.setCursor(Qt.CursorShape.PointingHandCursor)
        wijzigen.clicked.connect(self._wijzig_opslaglocatie)
        footer.addWidget(wijzigen)
        layout.addLayout(footer)

        return kaart

    def _build_backup_kaart(self) -> QFrame:
        t = self._theme
        kaart = QFrame()
        kaart.setObjectName("TableCard")
        layout = QVBoxLayout(kaart)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(12)

        sectie_label = QLabel("BACK-UP")
        sectie_label.setProperty("role", "fieldSectionLabel")
        layout.addWidget(sectie_label)

        # Stand: laatste en volgende back-up, met "Nu back-up maken".
        status = QFrame()
        status.setObjectName("BackupStatus")
        status.setStyleSheet(
            f"QFrame#BackupStatus {{ background: {t.surface_2}; border: 1px solid {t.border}; border-radius: 10px; }}"
        )
        status_rij = QHBoxLayout(status)
        status_rij.setContentsMargins(14, 12, 14, 12)
        status_rij.setSpacing(12)
        self._backup_stip = QLabel()
        self._backup_stip.setFixedSize(9, 9)
        status_rij.addWidget(self._backup_stip, 0, Qt.AlignmentFlag.AlignVCenter)
        tekst_kolom = QVBoxLayout()
        tekst_kolom.setSpacing(2)
        self._backup_hoofd = QLabel()
        self._backup_hoofd.setStyleSheet(f"color: {t.text}; font-weight: 600; font-size: 13px;")
        tekst_kolom.addWidget(self._backup_hoofd)
        self._backup_sub = QLabel()
        self._backup_sub.setStyleSheet(f"color: {t.text_muted}; font-size: 12px;")
        self._backup_sub.setWordWrap(True)
        tekst_kolom.addWidget(self._backup_sub)
        status_rij.addLayout(tekst_kolom, 1)
        self._backup_nu_btn = QPushButton("  Nu back-up maken")
        self._backup_nu_btn.setProperty("role", "ghost")
        self._backup_nu_btn.setIcon(icon("download", t.text, 13))
        self._backup_nu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._backup_nu_btn.clicked.connect(self._backup_planner.nu_maken)
        status_rij.addWidget(self._backup_nu_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(status)

        self._backup_schijf_paneel = self._backup_paneel(
            t.warning_soft,
            t.warning_ink,
            "De back-ups staan op <b>dezelfde schijf</b> als de database. Gaat die schijf kapot, dan ben "
            "je de back-ups ook kwijt. Kies een map op een andere schijf, een USB-stick of een netwerkmap.",
        )
        layout.addWidget(self._backup_schijf_paneel)
        self._backup_fout_paneel = self._backup_paneel(t.critical_soft, t.critical_ink, "")
        layout.addWidget(self._backup_fout_paneel)

        instellingen = self._beheer.huidige
        layout.addWidget(self._field_label("Hoe vaak"))
        freq_widget, self._backup_freq_group = self._segmented(
            [(waarde, _BACKUP_FREQUENTIE_LABEL[waarde]) for waarde in GELDIGE_BACKUP_FREQUENTIES],
            instellingen.backup_frequentie,
        )
        freq_widget.setMaximumWidth(520)
        layout.addWidget(freq_widget)
        freq_hint = QLabel(
            "Bij het opstarten als de laatste back-up te oud is, en daarna zolang RoboCutter openstaat."
        )
        freq_hint.setProperty("role", "fieldHint")
        freq_hint.setWordWrap(True)
        layout.addWidget(freq_hint)

        layout.addWidget(self._field_label("Back-upmap"))
        map_rij = QHBoxLayout()
        map_rij.setSpacing(8)
        self._in_backup_map = self._field_input()
        self._in_backup_map.setText(instellingen.backup_map or "")
        self._in_backup_map.setPlaceholderText(f"Standaard: {self._standaard_backup_map()}")
        map_rij.addWidget(self._in_backup_map, 1)
        backup_map_kiezen = QPushButton("Map kiezen…")
        backup_map_kiezen.setProperty("role", "ghost")
        backup_map_kiezen.setCursor(Qt.CursorShape.PointingHandCursor)
        backup_map_kiezen.clicked.connect(self._kies_backup_map)
        map_rij.addWidget(backup_map_kiezen)
        layout.addLayout(map_rij)
        map_hint = QLabel(
            f'<a href="standaard" style="color: {t.accent_text}; text-decoration: none; font-weight: 600;">'
            "Standaardmap gebruiken</a> (een map &quot;backups&quot; naast de database). Bewaard blijven: alles "
            "van de laatste 24 uur, daarna één per dag (14 dagen) en één per week (8 weken). Oudere back-ups "
            "ruimt RoboCutter zelf op."
        )
        map_hint.setProperty("role", "fieldHint")
        map_hint.setWordWrap(True)
        map_hint.setTextFormat(Qt.TextFormat.RichText)
        map_hint.linkActivated.connect(lambda _link: self._in_backup_map.clear())
        layout.addWidget(map_hint)

        self._backup_banner, self._backup_banner_label = self._build_banner()
        layout.addWidget(self._backup_banner)

        footer = QHBoxLayout()
        footer.addStretch(1)
        opslaan = QPushButton("Opslaan")
        opslaan.setProperty("role", "primary")
        opslaan.setCursor(Qt.CursorShape.PointingHandCursor)
        opslaan.clicked.connect(self._opslaan_backup)
        footer.addWidget(opslaan)
        layout.addLayout(footer)

        lijst_kop = QHBoxLayout()
        lijst_kop.setSpacing(10)
        lijst_titel = QLabel("BACK-UPS")
        lijst_titel.setProperty("role", "fieldSectionLabel")
        lijst_kop.addWidget(lijst_titel)
        self._backup_aantal = QLabel()
        self._backup_aantal.setProperty("role", "fieldHint")
        lijst_kop.addWidget(self._backup_aantal)
        lijst_kop.addStretch(1)
        layout.addLayout(lijst_kop)

        self._backup_lijst = QFrame()
        self._backup_lijst.setObjectName("BackupLijst")
        self._backup_lijst.setStyleSheet(
            f"QFrame#BackupLijst {{ border: 1px solid {t.border}; border-radius: 10px; background: {t.surface}; }}"
        )
        self._backup_lijst_layout = QVBoxLayout(self._backup_lijst)
        self._backup_lijst_layout.setContentsMargins(0, 0, 0, 0)
        self._backup_lijst_layout.setSpacing(0)
        layout.addWidget(self._backup_lijst)

        self._backup_meer = QLabel()
        self._backup_meer.setTextFormat(Qt.TextFormat.RichText)
        self._backup_meer.linkActivated.connect(self._wissel_alle_backups)
        layout.addWidget(self._backup_meer)

        self._ververs_backup()
        return kaart

    def _backup_paneel(self, achtergrond: str, inkt: str, tekst: str) -> QFrame:
        paneel = QFrame()
        paneel.setObjectName("BackupPaneel")
        paneel.setStyleSheet(f"QFrame#BackupPaneel {{ background: {achtergrond}; border-radius: 10px; }}")
        rij = QHBoxLayout(paneel)
        rij.setContentsMargins(14, 12, 14, 12)
        label = QLabel(tekst)
        label.setObjectName("BackupPaneelTekst")
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setStyleSheet(f"color: {inkt}; font-size: 12.5px;")
        rij.addWidget(label, 1)
        paneel.hide()
        return paneel

    def _standaard_backup_map(self) -> Path:
        return self._beheer.effectieve_data_map() / "backups"

    def _ververs_backup(self) -> None:
        if self._backup_planner is None or not hasattr(self, "_backup_hoofd"):
            return
        try:
            self._backup_hoofd.text()
        except RuntimeError:
            return  # kaart is net herbouwd (thema-wissel)
        t = self._theme
        planner = self._backup_planner
        laatste = planner.laatste()
        backups = lijst_backups(planner.backup_map)
        totaal = sum(b.grootte for b in backups)
        zelfde_schijf = laatste is not None and planner.op_zelfde_schijf()

        if planner.fout:
            stip = t.critical
            self._backup_hoofd.setText("Back-up mislukt")
            delen = [f"Laatste gelukte back-up: {tijd_tekst(laatste.tijdstip)}" if laatste else "Nog geen back-up"]
            delen.append("volgende poging over 10 minuten")
        elif laatste is None:
            stip = t.text_faint
            self._backup_hoofd.setText("Back-up maken…" if planner.bezig else "Nog geen back-up")
            delen = ["De eerste back-up wordt zo gemaakt"]
        else:
            stip = t.warning if zelfde_schijf else t.success
            soort = " (voor terugzetten)" if laatste.voor_terugzetten else ""
            self._backup_hoofd.setText(f"Laatste back-up: {tijd_tekst(laatste.tijdstip)}{soort}")
            delen = [grootte_tekst(laatste.grootte)]
            volgende = planner.volgende()
            if volgende is not None:
                delen.append(
                    "volgende: zo meteen" if volgende <= datetime.now() else f"volgende: {tijd_tekst(volgende)}"
                )
            if zelfde_schijf:
                delen.append("op dezelfde schijf als de database")
            else:
                delen.append(f"{len(backups)} back-ups bewaard ({grootte_tekst(totaal)})")
        self._backup_sub.setText(" · ".join(delen))
        self._backup_stip.setStyleSheet(f"background: {stip}; border-radius: 4px;")
        self._backup_nu_btn.setEnabled(not planner.bezig)
        self._backup_nu_btn.setText("  Back-up maken…" if planner.bezig else "  Nu back-up maken")

        self._backup_schijf_paneel.setVisible(zelfde_schijf and not planner.fout)
        if planner.fout:
            moment = f" van {tijd_tekst(planner.fout_moment)}" if planner.fout_moment else ""
            self._backup_fout_paneel.findChild(QLabel, "BackupPaneelTekst").setText(
                f"<b>De back-up{moment} is mislukt:</b> {planner.fout} RoboCutter probeert het elke 10 minuten "
                "opnieuw, of klik op Nu back-up maken."
            )
        self._backup_fout_paneel.setVisible(bool(planner.fout))

        self._ververs_backup_lijst(backups)

    def _ververs_backup_lijst(self, backups: list[BackupBestand]) -> None:
        t = self._theme
        _clear_layout(self._backup_lijst_layout)
        self._backup_aantal.setText(f"{len(backups)} in deze map, nieuwste eerst" if backups else "")
        if not backups:
            leeg = QLabel("Nog geen back-ups in deze map.")
            leeg.setStyleSheet(f"color: {t.text_faint}; font-size: 12.5px; padding: 18px;")
            leeg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._backup_lijst_layout.addWidget(leeg)
            self._backup_meer.hide()
            return

        tonen = backups if self._backup_alles_tonen else backups[:_BACKUPS_KORT]
        rijen = QWidget()
        grid = QGridLayout(rijen)
        grid.setContentsMargins(14, 8, 14, 8)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(0)
        for kolom, kop in enumerate(["WANNEER", "DATUM EN TIJD", "GROOTTE", "", ""]):
            label = QLabel(kop)
            label.setStyleSheet(
                f"color: {t.text_faint}; font-size: 10.5px; font-weight: 700; letter-spacing: 0.6px; padding: 4px 0;"
            )
            grid.addWidget(label, 0, kolom, Qt.AlignmentFlag.AlignRight if kolom == 2 else Qt.AlignmentFlag.AlignLeft)
        rij = 1
        vandaag = date.today()
        for backup in tonen:
            gekozen = backup.pad == self._backup_terug_keuze
            wanneer = QLabel(leeftijd_tekst(backup.tijdstip, vandaag))
            wanneer.setStyleSheet(f"color: {t.text}; font-weight: 600; font-size: 12.5px; padding: 7px 0;")
            grid.addWidget(wanneer, rij, 0)
            tijd = QLabel(datum_tijd_tekst(backup.tijdstip))
            tijd.setStyleSheet(f"color: {t.text_muted}; font-size: 12px;")
            grid.addWidget(tijd, rij, 1)
            grootte = QLabel(grootte_tekst(backup.grootte))
            grootte.setStyleSheet(f"color: {t.text_muted}; font-size: 12px;")
            grid.addWidget(grootte, rij, 2, Qt.AlignmentFlag.AlignRight)
            if backup.voor_terugzetten:
                soort = QLabel("Voor terugzetten")
                soort.setStyleSheet(
                    f"color: {t.text_muted}; background: {t.surface_2}; border: 1px solid {t.border}; "
                    "border-radius: 9px; padding: 1px 8px; font-size: 11px; font-weight: 700;"
                )
                grid.addWidget(soort, rij, 3, Qt.AlignmentFlag.AlignLeft)
            knop = QPushButton("Terugzetten")
            knop.setProperty("role", "ghost")
            knop.setCursor(Qt.CursorShape.PointingHandCursor)
            knop.setEnabled(not gekozen)
            knop.clicked.connect(lambda _=False, pad=backup.pad: self._kies_terugzetten(pad))
            grid.addWidget(knop, rij, 4, Qt.AlignmentFlag.AlignRight)
            rij += 1
            if gekozen:
                grid.addWidget(self._bouw_terugzet_bevestiging(backup), rij, 0, 1, 5)
                rij += 1
        grid.setColumnStretch(3, 1)
        self._backup_lijst_layout.addWidget(rijen)

        if len(backups) > _BACKUPS_KORT:
            tekst = "Alleen de nieuwste tonen" if self._backup_alles_tonen else f"Alle {len(backups)} tonen"
            self._backup_meer.setText(
                f'<a href="wissel" style="color: {t.accent_text}; text-decoration: none; font-weight: 600;">{tekst}</a>'
            )
            self._backup_meer.show()
        else:
            self._backup_meer.hide()

    def _bouw_terugzet_bevestiging(self, backup: BackupBestand) -> QFrame:
        t = self._theme
        paneel = QFrame()
        paneel.setObjectName("TerugzetBevestiging")
        paneel.setStyleSheet(f"QFrame#TerugzetBevestiging {{ background: {t.critical_soft}; border-radius: 8px; }}")
        rij = QHBoxLayout(paneel)
        rij.setContentsMargins(14, 12, 14, 12)
        rij.setSpacing(14)
        tekst = QLabel(
            f"<b>Terugzetten naar {tijd_tekst(backup.tijdstip)}?</b> Alles wat je daarna hebt gewijzigd is dan "
            "weg uit de app. De huidige stand wordt eerst als back-up bewaard, dus je kunt dit terugdraaien. "
            "RoboCutter start daarna opnieuw."
        )
        tekst.setWordWrap(True)
        tekst.setTextFormat(Qt.TextFormat.RichText)
        tekst.setStyleSheet(f"color: {t.critical_ink}; font-size: 12.5px;")
        rij.addWidget(tekst, 1)
        annuleren = QPushButton("Annuleren")
        annuleren.setProperty("role", "ghost")
        annuleren.setCursor(Qt.CursorShape.PointingHandCursor)
        annuleren.clicked.connect(lambda: self._kies_terugzetten(None))
        rij.addWidget(annuleren, 0, Qt.AlignmentFlag.AlignVCenter)
        bevestig = QPushButton("Terugzetten en herstarten")
        bevestig.setCursor(Qt.CursorShape.PointingHandCursor)
        # Geen rode knop-rol in theme.py; zelfde kleur als het kritieke paneel.
        bevestig.setStyleSheet(
            f"QPushButton {{ background: {t.critical}; color: #FFFFFF; border: none; border-radius: 8px; "
            "padding: 8px 15px; font-weight: 600; font-size: 13px; }"
        )
        bevestig.clicked.connect(lambda: self._terugzetten(backup))
        rij.addWidget(bevestig, 0, Qt.AlignmentFlag.AlignVCenter)
        return paneel

    def meld_teruggezet(self, teruggezet: datetime, veiliggesteld: datetime | None) -> None:
        """Na de herstart die bij Terugzetten hoort (zie ``MainWindow._terugzetten``)."""
        sub = (
            f"De stand van daarvoor staat bewaard als back-up van {tijd_tekst(veiliggesteld)}."
            if veiliggesteld is not None
            else ""
        )
        self._melding.toon(f"Back-up van {tijd_tekst(teruggezet)} teruggezet", sub)

    def _ververs_strategie_hint(self, waarde: str) -> None:
        self._strategie_hint.setText(_STRATEGIE_OMSCHRIJVING[waarde])

    def _ververs_huidige_locatie(self) -> None:
        self._label_huidige_locatie.setText(f"Huidige locatie: {self._beheer.effectieve_db_pad()}")

    # ------------------------------------------------------------------
    # Acties
    # ------------------------------------------------------------------
    def _kies_logo(self) -> None:
        pad, _ = QFileDialog.getOpenFileName(self, "Kies een logobestand")
        if pad:
            self._in_logo.setText(pad)

    def _kies_map(self) -> None:
        map_pad = QFileDialog.getExistingDirectory(self, "Kies een nieuwe opslaglocatie")
        if map_pad:
            self._in_map.setText(map_pad)

    def _kies_backup_map(self) -> None:
        map_pad = QFileDialog.getExistingDirectory(self, "Kies een map voor de back-ups")
        if map_pad:
            self._in_backup_map.setText(map_pad)

    def _wissel_alle_backups(self, _link: str = "") -> None:
        self._backup_alles_tonen = not self._backup_alles_tonen
        self._ververs_backup()

    def _kies_terugzetten(self, pad: Path | None) -> None:
        self._backup_terug_keuze = pad
        self._ververs_backup()

    def _terugzetten(self, backup: BackupBestand) -> None:
        if self._on_terugzetten is None:
            return
        fout = self._on_terugzetten(backup)
        if fout:
            self._backup_terug_keuze = None
            self._ververs_backup()
            self._toon_banner(self._backup_banner, self._backup_banner_label, fout, fout=True)

    def _opslaan_backup(self) -> None:
        map_tekst = self._in_backup_map.text().strip()
        try:
            self._beheer.bijwerken(
                backup_frequentie=self._backup_freq_group.checkedButton().property("waarde"),
                backup_map=map_tekst or None,
            )
        except ValueError as exc:
            self._toon_banner(self._backup_banner, self._backup_banner_label, str(exc), fout=True)
            return
        self._backup_banner.hide()
        self._backup_terug_keuze = None
        self._ververs_backup()
        self._melding.toon("Instellingen opgeslagen", "back-up")
        # Nieuwe map of vaker: meteen kijken of er een back-up nodig is.
        self._backup_planner.controleer()

    def _thema_live_gewijzigd(self, button) -> None:
        try:
            self._beheer.bijwerken(thema=button.property("waarde"))
        except ValueError as exc:
            self._toon_banner(self._algemeen_banner, self._algemeen_banner_label, str(exc), fout=True)
            return
        self._on_gewijzigd()

    def _opslaan_algemeen(self) -> None:
        try:
            self._beheer.bijwerken(
                standaard_zaagstrategie=self._strategie_group.checkedButton().property("waarde"),
                zaagsnede=self._in_zaagsnede.value(),
                werkvoorbereider_naam=self._in_werkvoorbereider.text().strip(),
                bedrijfslogo_pad=self._in_logo.text().strip() or None,
            )
        except ValueError as exc:
            self._toon_banner(self._algemeen_banner, self._algemeen_banner_label, str(exc), fout=True)
            return
        self._algemeen_banner.hide()
        self._melding.toon("Instellingen opgeslagen", "algemeen")

    def _opslaan_labels(self) -> None:
        try:
            self._beheer.bijwerken(
                label_scancode=self._scancode_group.checkedButton().property("waarde"),
                label_kantenband_indicatie=self._chk_kantenband.isChecked(),
                label_nerfrichting_pijl=self._chk_nerf.isChecked(),
            )
        except ValueError as exc:
            self._toon_banner(self._labels_banner, self._labels_banner_label, str(exc), fout=True)
            return
        self._labels_banner.hide()
        self._melding.toon("Instellingen opgeslagen", "labels")

    def _wijzig_opslaglocatie(self) -> None:
        nieuwe_map = self._in_map.text().strip()
        if not nieuwe_map:
            return
        try:
            self._beheer.wijzig_opslaglocatie(Path(nieuwe_map))
        except OpslagVerplaatsenError as exc:
            self._toon_banner(self._opslag_banner, self._opslag_banner_label, str(exc), fout=True)
            return
        self._ververs_huidige_locatie()
        self._toon_banner(
            self._opslag_banner,
            self._opslag_banner_label,
            "Opslaglocatie gewijzigd — herstart RoboCutter om overal de nieuwe locatie te gebruiken.",
            fout=False,
        )
