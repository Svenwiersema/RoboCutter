"""Importvenster voor onderdelen (hoofdstuk 10), naar de goedgekeurde
mockup ``design/assets/mockups/importeren-concept.html``.

Een bewuste uitzondering op "zo min mogelijk pop-ups" (hoofdstuk 11,
Sven: "met importeren kan al gou soms veel fout zijn dus dan is het beter
dat je dit als apparte menu hebt"). Drie stappen in een scrollend midden,
met een vaste kop (bestand, ander bestand, sjabloon) en voet (stand +
Importeren):

1. Materialen koppelen — per materiaaltekst uit het bestand; wat niet
   herkend is kies je, met "Bedoelde je…?" bovenaan, en die keuze wordt
   onthouden (``MateriaalKoppelingen``). Lijkt niets erop, dan maak je via
   "+ Nieuw materiaal aanmaken…" ter plekke een materiaal aan (Sven: "er
   moet eigenlijk een optie zijn om dit materiaal te kunnen toevoegen aan
   je bibliotheek"); dat staat meteen in de materialenbibliotheek.
2. Nog aanvullen — alleen de regels met een fout, met per fout veld een
   invoer en de reden eronder; of de regel overslaan.
3. Dit komt erbij — welke modellen (met ×aantal) en losse onderdelen, plus
   de waarschuwingen.

Importeren wordt pas actief als er geen fout meer over is. Het venster zelf
schrijft niets weg tot "Importeren"; sluiten of Annuleren laat alles zoals
het was: gekozen materiaalkoppelingen worden pas bij "Importeren" onthouden.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
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

from robocutter.importeren.koppelen import MateriaalKoppelingen, normaliseer, suggesties, zoek_materiaal
from robocutter.importeren.lezen import lees_bestand, lees_regel, schrijf_sjabloon
from robocutter.importeren.models import Ernst, ImportMelding, ImportRegel, LeesResultaat
from robocutter.importeren.toepassen import controleer, importeer_in_model, importeer_in_project
from robocutter.materialen.bibliotheek import MaterialenBibliotheek, valideer as valideer_materiaal
from robocutter.materialen.models import Materiaal, MateriaalStatus, MateriaalType, Nerfrichting
from robocutter.modellen.bibliotheek import ModellenBibliotheek
from robocutter.projecten.bibliotheek import ProjectenBibliotheek
from robocutter.ui.theme import Theme

__all__ = ["ImportDialoog", "kies_importbestand"]

_BESTANDSFILTER = "Zaaglijst (*.csv *.xlsx)"
_NIEUW = "__nieuw__"  # keuzelijst-waarde voor "+ Nieuw materiaal aanmaken…"


def kies_importbestand(parent: QWidget) -> str | None:
    pad, _ = QFileDialog.getOpenFileName(parent, "Onderdelen importeren", "", _BESTANDSFILTER)
    return pad or None


def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.hide()
            widget.deleteLater()
        elif item.layout() is not None:
            _clear_layout(item.layout())


class ImportDialoog(QDialog):
    """``doel`` is "project" (modellen + losse onderdelen) of "model" (alle
    regels worden onderdelen van ``doel_id``). Na ``exec()`` ==
    ``Accepted`` staat in ``samenvatting`` wat er is toegevoegd."""

    def __init__(
        self,
        pad: str,
        doel: str,
        doel_id: str,
        doel_naam: str,
        materialen: MaterialenBibliotheek,
        onthouden: MateriaalKoppelingen,
        theme: Theme,
        projecten: ProjectenBibliotheek | None = None,
        modellen: ModellenBibliotheek | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._doel, self._doel_id, self._doel_naam = doel, doel_id, doel_naam
        self._materialen, self._onthouden, self._theme = materialen, onthouden, theme
        self._projecten, self._modellen = projecten, modellen
        self.samenvatting = ""
        # Namen van materialen die in dit venster zijn aangemaakt (staan al in
        # de bibliotheek, ook als de import daarna wordt geannuleerd).
        self.nieuwe_materialen: list[str] = []
        self.setWindowTitle("Onderdelen importeren")
        self.setObjectName("ImportDialoog")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"QDialog#ImportDialoog {{ background: {theme.surface}; }}")
        self.setMinimumSize(900, 600)
        if parent is not None and parent.window() is not None:
            venster = parent.window().size()
            self.resize(max(900, int(venster.width() * 0.8)), max(600, int(venster.height() * 0.85)))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._bouw_kop())
        scroll = QScrollArea()
        scroll.setObjectName("ImportScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea#ImportScroll, QScrollArea#ImportScroll > QWidget > QWidget { background: transparent; }")
        inhoud = QWidget()
        self._inhoud = QVBoxLayout(inhoud)
        self._inhoud.setContentsMargins(0, 0, 0, 0)
        self._inhoud.setSpacing(0)
        scroll.setWidget(inhoud)
        layout.addWidget(scroll, 1)
        layout.addWidget(self._bouw_voet())

        self._laad(pad)

    # ------------------------------------------------------------------
    # Toestand
    # ------------------------------------------------------------------
    def _laad(self, pad: str) -> None:
        self._pad = pad
        self._resultaat: LeesResultaat = lees_bestand(pad)
        self._regels: list[ImportRegel] = list(self._resultaat.regels)
        self._overslaan: set[int] = set()
        self._koppeling: dict[str, str | None] = {}
        self._herkomst: dict[str, str] = {}  # sleutel -> "eerder gekozen" / "productcode" / "naam" / ""
        # Zelf gekozen koppelingen met het vinkje "onthouden": pas bij
        # Importeren opslaan (sleutel -> tekst uit het bestand).
        self._te_onthouden: dict[str, str] = {}
        # Materiaaltekst waarvoor het formulier "nieuw materiaal" openstaat.
        self._nieuw_open: str | None = None
        self._koppel_materialen()
        n = len(self._regels)
        self._bestand_label.setText(f"{Path(pad).name} · {n} {'regel' if n == 1 else 'regels'}")
        self._bouw_inhoud()

    def _koppel_materialen(self) -> None:
        for regel in self._regels:
            sleutel = normaliseer(regel.materiaal)
            if not sleutel or sleutel in self._koppeling:
                continue
            self._koppeling[sleutel] = zoek_materiaal(regel.materiaal, self._materialen, self._onthouden)
            self._herkomst[sleutel] = self._hoe_herkend(regel.materiaal, self._koppeling[sleutel])

    def _hoe_herkend(self, tekst: str, materiaal_id: str | None) -> str:
        if materiaal_id is None:
            return ""
        m = self._materialen.ophalen(materiaal_id)
        if m.productcode and normaliseer(m.productcode) == normaliseer(tekst):
            return "herkend op productcode"
        if normaliseer(m.naam) == normaliseer(tekst):
            return "herkend op naam"
        return "eerder zo gekozen"

    def _actieve_regels(self) -> list[ImportRegel]:
        return [r for r in self._regels if r.regelnummer not in self._overslaan]

    def _meldingen(self) -> list[ImportMelding]:
        return [m for m in self._resultaat.meldingen] + controleer(self._actieve_regels(), self._koppeling, self._materialen)

    # ------------------------------------------------------------------
    # Kop en voet
    # ------------------------------------------------------------------
    def _bouw_kop(self) -> QWidget:
        t = self._theme
        kop = QFrame()
        kop.setObjectName("ImportKop")
        kop.setStyleSheet(f"QFrame#ImportKop {{ background: {t.surface}; border-bottom: 1px solid {t.border}; }}")
        layout = QHBoxLayout(kop)
        layout.setContentsMargins(22, 16, 22, 16)
        layout.setSpacing(14)
        titel = QLabel(f"Importeren in {self._doel_naam}")
        titel.setStyleSheet(f"color: {t.text}; font-size: 15px; font-weight: 700; background: transparent;")
        layout.addWidget(titel)
        self._bestand_label = QLabel("")
        self._bestand_label.setStyleSheet(
            f"color: {t.text_muted}; font-family: 'JetBrains Mono', Consolas, monospace; font-size: 12px; background: transparent;"
        )
        layout.addWidget(self._bestand_label)
        layout.addStretch(1)
        for tekst, actie in (("Ander bestand…", self._ander_bestand), ("Sjabloon opslaan…", self._sjabloon)):
            knop = QPushButton(tekst)
            knop.setCursor(Qt.CursorShape.PointingHandCursor)
            knop.setStyleSheet(
                f"QPushButton {{ color: {t.accent_text}; background: transparent; border: none; font-size: 12.5px; font-weight: 600; }}"
                f"QPushButton:hover {{ text-decoration: underline; }}"
            )
            knop.clicked.connect(actie)
            layout.addWidget(knop)
        return kop

    def _bouw_voet(self) -> QWidget:
        t = self._theme
        voet = QFrame()
        voet.setObjectName("ImportVoet")
        voet.setStyleSheet(f"QFrame#ImportVoet {{ background: {t.surface_2}; border-top: 1px solid {t.border}; }}")
        layout = QHBoxLayout(voet)
        layout.setContentsMargins(22, 14, 22, 14)
        layout.setSpacing(10)
        self._stand = QLabel("")
        layout.addWidget(self._stand)
        layout.addStretch(1)
        annuleren = QPushButton("Annuleren")
        annuleren.setProperty("role", "ghost")
        annuleren.setCursor(Qt.CursorShape.PointingHandCursor)
        annuleren.clicked.connect(self.reject)
        layout.addWidget(annuleren)
        self._importeer_knop = QPushButton("Importeren")
        self._importeer_knop.setProperty("role", "primary")
        self._importeer_knop.setCursor(Qt.CursorShape.PointingHandCursor)
        self._importeer_knop.clicked.connect(self._importeer)
        layout.addWidget(self._importeer_knop)
        return voet

    def _ander_bestand(self) -> None:
        pad = kies_importbestand(self)
        if pad:
            self._laad(pad)

    def _sjabloon(self) -> None:
        pad, _ = QFileDialog.getSaveFileName(self, "Sjabloon opslaan", "RoboCutter-importsjabloon.xlsx", "Excel (*.xlsx)")
        if pad:
            schrijf_sjabloon(pad)

    # ------------------------------------------------------------------
    # Inhoud
    # ------------------------------------------------------------------
    def _bouw_inhoud(self) -> None:
        _clear_layout(self._inhoud)
        bestandsfouten = [m for m in self._resultaat.meldingen if m.ernst == Ernst.FOUT]
        if bestandsfouten:
            self._inhoud.addWidget(self._bouw_bestandsfout(bestandsfouten))
            self._inhoud.addStretch(1)
            self._werk_stand_bij()
            return
        self._stap1 = self._stap("1", "Materialen koppelen")
        self._inhoud.addWidget(self._stap1["frame"])
        self._stap2 = self._stap("2", "Nog aanvullen")
        self._inhoud.addWidget(self._stap2["frame"])
        self._stap3 = self._stap("3", "Dit komt erbij")
        self._inhoud.addWidget(self._stap3["frame"])
        self._inhoud.addStretch(1)
        self._vul_stap1()
        self._vul_stap2()
        self._werk_stand_bij()

    def _bouw_bestandsfout(self, fouten: list[ImportMelding]) -> QWidget:
        t = self._theme
        vak = QFrame()
        vak.setObjectName("ImportBestandsfout")
        vak.setStyleSheet(
            f"QFrame#ImportBestandsfout {{ background: {t.critical_soft}; border-radius: 10px; margin: 22px; }}"
        )
        layout = QVBoxLayout(vak)
        layout.setContentsMargins(18, 14, 18, 14)
        tekst = QLabel(
            "Dit bestand kan niet ingelezen worden:\n"
            + "\n".join(f"• {m.tekst}" for m in fouten)
            + "\n\nKies een ander bestand, of sla het sjabloon op om de juiste kolommen te zien."
        )
        tekst.setWordWrap(True)
        tekst.setStyleSheet(f"color: {t.critical_ink}; background: transparent; font-size: 13px;")
        layout.addWidget(tekst)
        return vak

    def _stap(self, nummer: str, titel: str) -> dict:
        t = self._theme
        frame = QFrame()
        frame.setObjectName("ImportStap")
        frame.setStyleSheet(f"QFrame#ImportStap {{ background: transparent; border-bottom: 1px solid {t.border}; }}")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(22, 16, 22, 18)
        layout.setSpacing(10)
        kop = QHBoxLayout()
        kop.setSpacing(10)
        nr = QLabel(nummer)
        nr.setFixedSize(20, 20)
        nr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        kop.addWidget(nr)
        titel_label = QLabel(titel)
        titel_label.setStyleSheet(f"color: {t.text}; font-size: 13.5px; font-weight: 700; background: transparent;")
        kop.addWidget(titel_label)
        sub = QLabel("")
        sub.setStyleSheet(f"color: {t.text_muted}; font-size: 12px; background: transparent;")
        kop.addWidget(sub)
        kop.addStretch(1)
        layout.addLayout(kop)
        body = QVBoxLayout()
        body.setSpacing(8)
        layout.addLayout(body)
        return {"frame": frame, "nr": nr, "sub": sub, "body": body}

    def _zet_stapstatus(self, stap: dict, open_: bool, sub: str) -> None:
        t = self._theme
        if open_:
            stijl = f"background: {t.critical_soft}; color: {t.critical_ink}; border: 1px solid {t.critical};"
        else:
            stijl = f"background: {t.success_soft}; color: {t.success_ink}; border: 1px solid {t.success};"
        stap["nr"].setStyleSheet(stijl + " border-radius: 10px; font-size: 11px; font-weight: 700;")
        stap["sub"].setText(sub)

    def _hint(self, tekst: str) -> QLabel:
        label = QLabel(tekst)
        label.setWordWrap(True)
        label.setStyleSheet(f"color: {self._theme.text_faint}; font-size: 12px; background: transparent;")
        return label

    # Stap 1 ------------------------------------------------------------
    def _vul_stap1(self) -> None:
        t = self._theme
        body = self._stap1["body"]
        _clear_layout(body)
        body.addWidget(self._hint(
            "Zo heten de materialen in je bestand. Wat RoboCutter herkent, staat al goed. "
            "Kies je zelf een materiaal, dan wordt dat onthouden voor de volgende import."
        ))
        raster = QGridLayout()
        raster.setHorizontalSpacing(14)
        raster.setVerticalSpacing(8)
        raster.setColumnStretch(0, 2)
        raster.setColumnStretch(1, 3)
        per_tekst: dict[str, tuple[str, int]] = {}
        for regel in self._actieve_regels():
            sleutel = normaliseer(regel.materiaal)
            if sleutel:
                tekst, n = per_tekst.get(sleutel, (regel.materiaal, 0))
                per_tekst[sleutel] = (tekst, n + 1)
        for rij, (sleutel, (tekst, n)) in enumerate(per_tekst.items()):
            links = QLabel(
                f"<b>{tekst}</b><br><span style='color:{t.text_faint}'>{n} {'regel' if n == 1 else 'regels'} · "
                f"{self._herkomst.get(sleutel) or 'niet gevonden'}</span>"
            )
            links.setStyleSheet(f"color: {t.text}; background: transparent; font-size: 12.5px;")
            raster.addWidget(links, rij * 2, 0)
            combo = QComboBox()
            combo.setProperty("role", "field")
            combo.addItem("— kies een materiaal —", "")
            combo.addItem("+ Nieuw materiaal aanmaken…", _NIEUW)
            voorstel = suggesties(tekst, self._materialen) if self._koppeling.get(sleutel) is None else []
            for mid in voorstel:
                combo.addItem(f"Bedoelde je: {self._materiaal_label(mid)}", mid)
            if voorstel:
                combo.insertSeparator(combo.count())
            for m in sorted(self._materialen.lijst(), key=lambda m: m.naam.lower()):
                combo.addItem(self._materiaal_label(m.id), m.id)
            gekozen = self._koppeling.get(sleutel)
            if gekozen:
                # De regel in "alle materialen" (niet de suggestie erboven).
                combo.setCurrentIndex(max(i for i in range(combo.count()) if combo.itemData(i) == gekozen))
            elif self._nieuw_open == sleutel:
                combo.setCurrentIndex(1)
            raster.addWidget(combo, rij * 2, 1)
            onthoud = QCheckBox("onthouden")
            onthoud.setChecked(sleutel in self._te_onthouden or self._herkomst.get(sleutel) == "")
            onthoud.setVisible(self._herkomst.get(sleutel) in ("", "zelf gekozen"))
            onthoud.toggled.connect(lambda aan, s=sleutel, tx=tekst: self._zet_onthouden(s, tx, aan))
            raster.addWidget(onthoud, rij * 2, 2)
            combo.currentIndexChanged.connect(
                lambda _i, s=sleutel, tx=tekst, c=combo, o=onthoud: self._kies_materiaal(s, tx, c.currentData(), o.isChecked())
            )
            if self._nieuw_open == sleutel:
                raster.addWidget(self._bouw_nieuw_materiaal(sleutel, tekst), rij * 2 + 1, 0, 1, 3)
        body.addLayout(raster)

    def _bouw_nieuw_materiaal(self, sleutel: str, tekst: str) -> QWidget:
        """Klein formulier onder de keuzelijst: de naam uit het bestand staat
        al ingevuld; de rest (randafzaag, fabriekskantenband, …) vul je later
        aan in Materialen."""
        t = self._theme
        vak = QFrame()
        vak.setObjectName("ImportNieuwMateriaal")
        vak.setStyleSheet(
            f"QFrame#ImportNieuwMateriaal {{ background: {t.surface_2}; border: 1px solid {t.accent}; border-radius: 10px; }}"
        )
        layout = QVBoxLayout(vak)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        kop = QLabel("Nieuw materiaal in de materialenbibliotheek")
        kop.setStyleSheet(f"color: {t.text}; font-weight: 700; font-size: 12.5px; background: transparent;")
        layout.addWidget(kop)

        veldstijl = (
            f"QLineEdit {{ background: {t.surface}; color: {t.text}; border: 1px solid {t.border}; border-radius: 7px;"
            " padding: 5px 8px; font-size: 12.5px; }"
        )
        rij = QHBoxLayout()
        rij.setSpacing(10)

        def kolom(titel: str, widget: QWidget, stretch: int = 0) -> QLabel:
            k = QVBoxLayout()
            k.setSpacing(3)
            label = QLabel(titel)
            label.setStyleSheet(f"color: {t.text_muted}; font-size: 11.5px; font-weight: 600; background: transparent;")
            k.addWidget(label)
            k.addWidget(widget)
            rij.addLayout(k, stretch)
            return label

        naam = QLineEdit(tekst)
        naam.setStyleSheet(veldstijl)
        kolom("Naam", naam, 3)
        soort = QComboBox()
        soort.setProperty("role", "field")
        soort.addItem("Plaat", MateriaalType.PLAAT.value)
        soort.addItem("Balk", MateriaalType.BALK.value)
        kolom("Type", soort, 1)
        maten: dict[str, QLineEdit] = {}
        derde_label = None
        for titel in ("Lengte", "Breedte", "Dikte"):
            veld = QLineEdit()
            veld.setStyleSheet(veldstijl)
            veld.setPlaceholderText("mm")
            veld.setMaximumWidth(110)
            derde_label = kolom(f"{titel} mm", veld)
            maten[titel] = veld
        soort.currentIndexChanged.connect(
            lambda _i: derde_label.setText("Hoogte mm" if soort.currentData() == MateriaalType.BALK.value else "Dikte mm")
        )
        nerf = QComboBox()
        nerf.setProperty("role", "field")
        for waarde, label in (
            (Nerfrichting.GEEN, "Geen"), (Nerfrichting.LANGE_ZIJDE, "Over de lengte"), (Nerfrichting.KORTE_ZIJDE, "Over de breedte"),
        ):
            nerf.addItem(label, waarde.value)
        kolom("Nerf", nerf, 1)
        layout.addLayout(rij)

        fout = QLabel("")
        fout.setWordWrap(True)
        fout.setStyleSheet(f"color: {t.critical_ink}; font-size: 12px; background: transparent;")
        fout.hide()
        layout.addWidget(fout)
        knoppen = QHBoxLayout()
        knoppen.addWidget(self._hint("Randafzaag, fabriekskantenband en de rest vul je later aan in Materialen."), 1)
        annuleer = QPushButton("Annuleren")
        annuleer.setProperty("role", "ghost")
        annuleer.setCursor(Qt.CursorShape.PointingHandCursor)
        annuleer.clicked.connect(self._sluit_nieuw_materiaal)
        knoppen.addWidget(annuleer)
        maak = QPushButton("Aanmaken en koppelen")
        maak.setProperty("role", "primary")
        maak.setCursor(Qt.CursorShape.PointingHandCursor)
        maak.clicked.connect(lambda: self._maak_materiaal(sleutel, tekst, naam, soort, maten, nerf, fout))
        knoppen.addWidget(maak)
        layout.addLayout(knoppen)
        return vak

    def _sluit_nieuw_materiaal(self) -> None:
        self._nieuw_open = None
        QTimer.singleShot(0, self._vul_stap1)

    def _maak_materiaal(
        self, sleutel: str, tekst: str, naam: QLineEdit, soort: QComboBox, maten: dict[str, QLineEdit], nerf: QComboBox,
        fout: QLabel,
    ) -> None:
        def getal(veld: QLineEdit) -> float:
            tekst = veld.text().strip().replace(" ", "")
            if "," in tekst:
                tekst = tekst.replace(".", "").replace(",", ".")
            try:
                return float(tekst)
            except ValueError:
                return 0.0

        kandidaat = Materiaal(
            id="",
            naam=naam.text().strip(),
            type=MateriaalType(soort.currentData()),
            lengte=getal(maten["Lengte"]),
            breedte=getal(maten["Breedte"]),
            derde_afmeting=getal(maten["Dikte"]),
            nerfrichting=Nerfrichting(nerf.currentData()),
        )
        fouten = valideer_materiaal(kandidaat)
        if fouten:
            fout.setText("\n".join(f"• {f}" for f in fouten))
            fout.show()
            return
        materiaal = self._materialen.toevoegen(kandidaat)
        self.nieuwe_materialen.append(materiaal.naam)
        self._koppeling[sleutel] = materiaal.id
        self._herkomst[sleutel] = "nieuw aangemaakt"
        if normaliseer(materiaal.naam) != sleutel:
            # Andere naam dan in het bestand: koppeling onthouden (bij Importeren).
            self._te_onthouden[sleutel] = tekst
        self._nieuw_open = None
        self._vul_stap2()
        self._werk_stand_bij()
        QTimer.singleShot(0, self._vul_stap1)

    def _zet_onthouden(self, sleutel: str, tekst: str, aan: bool) -> None:
        if self._herkomst.get(sleutel) == "nieuw aangemaakt":
            return  # zie _maak_materiaal
        if aan and self._herkomst.get(sleutel) == "zelf gekozen":
            self._te_onthouden[sleutel] = tekst
        else:
            self._te_onthouden.pop(sleutel, None)

    def _materiaal_label(self, materiaal_id: str) -> str:
        m = self._materialen.ophalen(materiaal_id)
        soort = " (balk)" if m.type == MateriaalType.BALK else ""
        archief = " (gearchiveerd)" if m.status != MateriaalStatus.ACTIEF else ""
        return f"{m.naam}{soort}{archief}"

    def _kies_materiaal(self, sleutel: str, tekst: str, materiaal_id: str, onthouden: bool) -> None:
        if materiaal_id == _NIEUW:
            self._nieuw_open = sleutel
            self._koppeling[sleutel] = None
            self._herkomst[sleutel] = ""
            self._te_onthouden.pop(sleutel, None)
            self._vul_stap2()
            self._werk_stand_bij()
            QTimer.singleShot(0, self._vul_stap1)
            return
        if self._nieuw_open == sleutel:
            self._nieuw_open = None
        self._koppeling[sleutel] = materiaal_id or None
        self._herkomst[sleutel] = "zelf gekozen" if materiaal_id else ""
        self._zet_onthouden(sleutel, tekst, onthouden)
        # Plaat of balk bepaalt wat er aangevuld moet worden (bv. een breedte).
        self._vul_stap2()
        self._werk_stand_bij()
        # Stap 1 opnieuw (tekst "zelf gekozen") pas na dit signaal: de keuzelijst
        # die het stuurde, wordt daarbij vervangen.
        QTimer.singleShot(0, self._vul_stap1)

    # Stap 2 ------------------------------------------------------------
    def _vul_stap2(self) -> None:
        body = self._stap2["body"]
        _clear_layout(body)
        self._rij_refs: dict[int, dict] = {}
        fout_per_regel: dict[int, dict[str, str]] = {}
        for m in controleer(self._regels, self._koppeling, self._materialen):
            if m.ernst == Ernst.FOUT and m.regelnummer is not None and m.kolom:
                fout_per_regel.setdefault(m.regelnummer, {})[m.kolom] = m.tekst
        # Regels zonder materiaaltekst kun je niet in stap 1 koppelen: hier invullen.
        for regel in self._regels:
            if not regel.materiaal:
                fout_per_regel.setdefault(regel.regelnummer, {})["Materiaal"] = regel.problemen.get("Materiaal", "Materiaal is leeg.")
        if not fout_per_regel:
            body.addWidget(self._hint("Niets aan te vullen: alle regels zijn compleet."))
            return
        body.addWidget(self._hint("Alleen de regels waar iets ontbreekt of niet klopt. Vul het rode veld in, of sla de regel over."))
        for regel in self._regels:
            if regel.regelnummer in fout_per_regel:
                body.addWidget(self._bouw_aanvul_rij(regel, fout_per_regel[regel.regelnummer]))

    def _bouw_aanvul_rij(self, regel: ImportRegel, fouten: dict[str, str]) -> QWidget:
        t = self._theme
        rij = QFrame()
        rij.setObjectName("ImportAanvulRij")
        rij.setStyleSheet(
            f"QFrame#ImportAanvulRij {{ background: {t.surface_2}; border: 1px solid {t.border}; border-radius: 10px; }}"
        )
        layout = QHBoxLayout(rij)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(14)
        info = QLabel(
            f"<span style='color:{t.text_faint}'>Regel {regel.regelnummer}</span><br>"
            f"<b>{regel.naam or '(geen naam)'}</b><br><span style='color:{t.text_muted}'>{regel.materiaal or '(geen materiaal)'}</span>"
        )
        info.setStyleSheet(f"color: {t.text}; background: transparent; font-size: 12.5px;")
        info.setFixedWidth(220)
        layout.addWidget(info, 0, Qt.AlignmentFlag.AlignTop)
        velden: dict[str, tuple[QLineEdit, QLabel]] = {}
        for kolom, reden in fouten.items():
            kolom_layout = QVBoxLayout()
            kolom_layout.setSpacing(3)
            kop = QLabel(kolom)
            kop.setStyleSheet(f"color: {t.text_muted}; font-size: 11.5px; font-weight: 600; background: transparent;")
            kolom_layout.addWidget(kop)
            invoer = QLineEdit(regel.waarden.get(kolom, ""))
            invoer.setPlaceholderText("mm" if kolom in ("Lengte", "Breedte") else kolom)
            invoer.setMinimumWidth(140)
            invoer.editingFinished.connect(lambda n=regel.regelnummer: self._vul_aan(n))
            kolom_layout.addWidget(invoer)
            waarom = QLabel(reden)
            waarom.setWordWrap(True)
            waarom.setMaximumWidth(260)
            waarom.setStyleSheet(f"color: {t.critical_ink}; font-size: 11.5px; background: transparent;")
            kolom_layout.addWidget(waarom)
            layout.addLayout(kolom_layout)
            velden[kolom] = (invoer, waarom)
        layout.addStretch(1)
        sla = QPushButton("Overslaan")
        sla.setCursor(Qt.CursorShape.PointingHandCursor)
        sla.setStyleSheet(
            f"QPushButton {{ color: {t.accent_text}; background: transparent; border: none; font-size: 12.5px; font-weight: 600; }}"
        )
        sla.clicked.connect(lambda _c=False, n=regel.regelnummer: self._wissel_overslaan(n))
        layout.addWidget(sla, 0, Qt.AlignmentFlag.AlignTop)
        self._rij_refs[regel.regelnummer] = {"rij": rij, "velden": velden, "info": info, "sla": sla}
        self._werk_rij_bij(regel.regelnummer)
        return rij

    def _regel(self, nummer: int) -> ImportRegel:
        return next(r for r in self._regels if r.regelnummer == nummer)

    def _vul_aan(self, nummer: int) -> None:
        refs = self._rij_refs.get(nummer)
        if refs is None:
            return
        oud = self._regel(nummer)
        waarden = dict(oud.waarden)
        for kolom, (invoer, _) in refs["velden"].items():
            waarden[kolom] = invoer.text().strip()
        nieuw = lees_regel(nummer, waarden)
        self._regels[self._regels.index(oud)] = nieuw
        if normaliseer(nieuw.materiaal) != normaliseer(oud.materiaal):
            # Nieuwe materiaaltekst: koppelen, en stap 1 laat hem zien.
            self._koppel_materialen()
            self._vul_stap1()
        self._werk_rij_bij(nummer)
        self._werk_stand_bij()

    def _wissel_overslaan(self, nummer: int) -> None:
        if nummer in self._overslaan:
            self._overslaan.discard(nummer)
        else:
            self._overslaan.add(nummer)
        self._werk_rij_bij(nummer)
        self._werk_stand_bij()

    def _werk_rij_bij(self, nummer: int) -> None:
        t = self._theme
        refs = self._rij_refs[nummer]
        overgeslagen = nummer in self._overslaan
        regel = self._regel(nummer)
        fouten = {
            m.kolom: m.tekst
            for m in controleer([regel], self._koppeling, self._materialen)
            if m.ernst == Ernst.FOUT and m.kolom
        }
        if not regel.materiaal:
            fouten["Materiaal"] = regel.problemen.get("Materiaal", "Materiaal is leeg.")
        for kolom, (invoer, waarom) in refs["velden"].items():
            fout = fouten.get(kolom)
            invoer.setEnabled(not overgeslagen)
            rand, achtergrond = (t.critical, t.critical_soft) if fout and not overgeslagen else (t.border, t.surface)
            invoer.setStyleSheet(
                f"QLineEdit {{ background: {achtergrond}; color: {t.text}; border: 1px solid {rand}; border-radius: 7px; padding: 5px 8px; font-size: 12.5px; }}"
                f"QLineEdit:disabled {{ color: {t.text_faint}; }}"
            )
            waarom.setText(fout or "In orde")
            waarom.setStyleSheet(
                f"color: {t.critical_ink if fout else t.success_ink}; font-size: 11.5px; background: transparent;"
            )
            waarom.setVisible(not overgeslagen)
        refs["sla"].setText("Toch meenemen" if overgeslagen else "Overslaan")
        refs["info"].setEnabled(not overgeslagen)

    # Stap 3 en stand -------------------------------------------------
    def _vul_stap3(self, meldingen: list[ImportMelding]) -> None:
        t = self._theme
        body = self._stap3["body"]
        _clear_layout(body)
        regels = self._actieve_regels()
        blokken = QGridLayout()
        blokken.setHorizontalSpacing(10)
        blokken.setVerticalSpacing(10)
        items: list[tuple[str, str, str]] = []
        if self._doel == "model":
            items.append((self._doel_naam, "", f"{len(regels)} onderdelen erbij in dit model"))
        else:
            modellen: dict[str, list[ImportRegel]] = {}
            losse: list[ImportRegel] = []
            for r in regels:
                (modellen.setdefault(r.model.casefold(), []) if r.model else losse).append(r)
            for groep in modellen.values():
                items.append((groep[0].model, f"×{groep[0].modelaantal}", f"model · {len(groep)} onderdelen"))
            if losse:
                namen = ", ".join(r.naam for r in losse[:3] if r.naam) + (" …" if len(losse) > 3 else "")
                items.append(("Losse onderdelen", "", f"{len(losse)} {'onderdeel' if len(losse) == 1 else 'onderdelen'} ({namen})"))
        for i, (naam, aantal, sub) in enumerate(items):
            blok = QFrame()
            blok.setObjectName("ImportBlok")
            blok.setStyleSheet(
                f"QFrame#ImportBlok {{ background: {t.surface_2}; border: 1px solid {t.border}; border-radius: 10px; }}"
            )
            bl = QVBoxLayout(blok)
            bl.setContentsMargins(12, 10, 12, 10)
            bl.setSpacing(3)
            kop = QLabel(f"<b>{naam}</b>" + (f"  <span style='color:{t.accent_text}'>{aantal}</span>" if aantal else ""))
            kop.setStyleSheet(f"color: {t.text}; background: transparent; font-size: 13px;")
            bl.addWidget(kop)
            sub_label = QLabel(sub)
            sub_label.setWordWrap(True)
            sub_label.setStyleSheet(f"color: {t.text_muted}; background: transparent; font-size: 12px;")
            bl.addWidget(sub_label)
            blokken.addWidget(blok, i // 3, i % 3)
        body.addLayout(blokken)

        waarschuwingen = [m for m in meldingen if m.ernst == Ernst.WAARSCHUWING]
        if waarschuwingen:
            knop = QToolButton()
            knop.setCheckable(True)
            knop.setCursor(Qt.CursorShape.PointingHandCursor)
            n = len(waarschuwingen)
            woord = "waarschuwing" if n == 1 else "waarschuwingen"
            knop.setText(f"Toon {n} {woord} (importeren kan wel)")
            knop.setStyleSheet(
                f"QToolButton {{ color: {t.warning_ink}; background: transparent; border: none; font-size: 12.5px; font-weight: 600; }}"
            )
            lijst = QLabel("\n".join(
                f"• {'Regel ' + str(m.regelnummer) + ': ' if m.regelnummer else ''}{m.tekst}" for m in waarschuwingen
            ))
            lijst.setWordWrap(True)
            lijst.setStyleSheet(f"color: {t.text_muted}; background: transparent; font-size: 12px;")
            lijst.hide()
            knop.toggled.connect(lambda aan, k=knop, lb=lijst, n=n, w=woord: (
                lb.setVisible(aan),
                k.setText(f"Verberg {w}" if aan else f"Toon {n} {w} (importeren kan wel)"),
            ))
            body.addWidget(knop, 0, Qt.AlignmentFlag.AlignLeft)
            body.addWidget(lijst)

    def _werk_stand_bij(self) -> None:
        t = self._theme
        meldingen = self._meldingen()
        fouten = [m for m in meldingen if m.ernst == Ernst.FOUT]
        bestandsfout = any(m.ernst == Ernst.FOUT for m in self._resultaat.meldingen)
        regels = self._actieve_regels()
        if not bestandsfout:
            open_koppel = sum(1 for s, mid in self._koppeling.items() if mid is None and any(
                normaliseer(r.materiaal) == s for r in regels))
            self._zet_stapstatus(
                self._stap1, bool(open_koppel),
                f"{open_koppel} {'materiaal' if open_koppel == 1 else 'materialen'} kiezen" if open_koppel else "alles gekoppeld",
            )
            open_rijen = len({m.regelnummer for m in fouten if m.regelnummer is not None})
            overgeslagen = len(self._overslaan)
            sub2 = f"{open_rijen} {'regel' if open_rijen == 1 else 'regels'}" if open_rijen else "alles in orde"
            if overgeslagen:
                sub2 += f" · {overgeslagen} overgeslagen"
            self._zet_stapstatus(self._stap2, bool(open_rijen), sub2)
            stuks = sum(r.aantal * (r.modelaantal if r.model and self._doel == "project" else 1) for r in regels)
            self._zet_stapstatus(self._stap3, False, f"{len(regels)} regels, {stuks} stuks in de zaaglijst")
            self._vul_stap3(meldingen)
        else:
            stuks = 0
        if bestandsfout or not regels:
            self._stand.setText("Niets om te importeren")
            kleur = t.critical_ink
            klaar = False
        elif fouten:
            n = len(fouten)
            self._stand.setText(f"Nog {n} {'ding' if n == 1 else 'dingen'} aanvullen")
            kleur = t.critical_ink
            klaar = False
        else:
            self._stand.setText("Alles klopt")
            kleur = t.success_ink
            klaar = True
        self._stand.setStyleSheet(f"color: {kleur}; font-size: 12.5px; font-weight: 600; background: transparent;")
        self._importeer_knop.setEnabled(klaar)
        self._importeer_knop.setText(f"Importeren ({stuks} stuks)" if klaar else "Importeren")

    # ------------------------------------------------------------------
    def _importeer(self) -> None:
        regels = self._actieve_regels()
        try:
            if self._doel == "model":
                importeer_in_model(self._modellen, self._doel_id, regels, self._koppeling, self._materialen)
                self.samenvatting = f"{len(regels)} onderdelen toegevoegd aan {self._doel_naam}"
                if self.nieuwe_materialen:
                    self.samenvatting += f" · nieuw materiaal: {', '.join(self.nieuwe_materialen)}"
            else:
                importeer_in_project(self._projecten, self._doel_id, regels, self._koppeling, self._materialen)
                n_model = len({r.model.casefold() for r in regels if r.model})
                n_los = sum(1 for r in regels if not r.model)
                delen = []
                if n_model:
                    delen.append(f"{n_model} {'model' if n_model == 1 else 'modellen'}")
                if n_los:
                    delen.append(f"{n_los} {'los onderdeel' if n_los == 1 else 'losse onderdelen'}")
                self.samenvatting = " en ".join(delen) + " geïmporteerd"
            if self.nieuwe_materialen:
                self.samenvatting += f" · nieuw materiaal: {', '.join(self.nieuwe_materialen)}"
        except ValueError as exc:
            # Mag niet voorkomen (de knop staat dan uit), maar nooit stil falen.
            self._stand.setText(f"Niet geïmporteerd: {exc}")
            self._stand.setStyleSheet(f"color: {self._theme.critical_ink}; font-size: 12.5px; font-weight: 600;")
            return
        for sleutel, tekst in self._te_onthouden.items():
            if self._koppeling.get(sleutel):
                self._onthouden.onthoud(tekst, self._koppeling[sleutel])
        self.accept()
