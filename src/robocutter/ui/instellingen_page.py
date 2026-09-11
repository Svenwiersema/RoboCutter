"""Opties/instellingen-scherm: één simpel formulier voor de app-brede
instellingen uit ``robocutter.instellingen`` (thema, bedrijfslogo,
standaard zaagstrategie, werkvoorbereider-naam, opslaglocatie van het
databasebestand).

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
"Efficiënt", "Rijen" en "Guillotine". Dit ging via meerdere
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
bij sterk uiteenlopende onderdeelhoogtes). De onderliggende heuristiek
bestaat nog wel en draait nog steeds intern mee binnen "Efficiënt" (zie
``engine.py``'s module-docstring) — alleen de zichtbare optie is weg.
Alle drie overgebleven opties worden echt uitgevoerd door
``robocutter.optimalisatie.engine.genereer_zaagplan`` (zie de
docstring van die module voor de precieze algoritmes).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from robocutter.instellingen.beheer import InstellingenBeheer, OpslagVerplaatsenError
from robocutter.instellingen.models import GELDIGE_THEMAS, GELDIGE_ZAAGSTRATEGIEEN
from robocutter.ui.theme import Theme

_THEMA_LABEL = {"licht": "Licht", "donker": "Donker", "systeem": "Systeem"}
# Sven corrigeerde zichzelf hier expliciet: "efficient" en "guillotine" zijn
# NIET hetzelfde (ook al gebruikt de huidige "efficient"-implementatie zelf
# ook al een guillotine-stijl interne splitsing, zie engine.py) — Guillotine
# is een écht apart, strikter algoritme (alleen doorlopende zaagsnedes).
# "efficient" was juist wel hetzelfde als wat eerder "vrije_plaatsing" heette
# (vrije plaatsing voor maximale opbrengst) — die twee zijn daarom weer
# samengevoegd tot alleen "efficient"/"Efficiënt".
_STRATEGIE_LABEL = {
    "efficient": "Efficiënt",
    "rijen": "Rijen",
    "guillotine": "Guillotine",
}
# Alle drie worden echt uitgevoerd door
# robocutter.optimalisatie.engine.genereer_zaagplan — zie de docstring
# van die module voor de precieze algoritmes per strategie.
_STRATEGIE_OMSCHRIJVING = {
    "efficient": "Vrije plaatsing voor maximale materiaalopbrengst (best-fit) bij gemengde afmetingen — dit is de methode die de zaagmotor nu al uitvoert.",
    "rijen": "Lange zijdes eerst in volledige-breedte rijen; elke rij krijgt zijn eigen hoogte op basis van het grootste stuk erin — overzichtelijke zaagvolgorde.",
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
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._beheer = beheer
        self._theme = theme
        self._on_gewijzigd = on_gewijzigd

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
        layout.addWidget(self._build_opslag_kaart())
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
                werkvoorbereider_naam=self._in_werkvoorbereider.text().strip(),
                bedrijfslogo_pad=self._in_logo.text().strip() or None,
            )
        except ValueError as exc:
            self._toon_banner(self._algemeen_banner, self._algemeen_banner_label, str(exc), fout=True)
            return
        self._toon_banner(self._algemeen_banner, self._algemeen_banner_label, "Instellingen opgeslagen.", fout=False)

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
