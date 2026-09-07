"""Projectkaart voor de home pagina (rasterweergave van alle projecten).

Toont nu een echt ``robocutter.projecten.models.Project`` i.p.v. de
voormalige ``sample_data.ProjectSummary`` (zie OVERDRACHT.md: het
Dashboard is nu echt gekoppeld aan ``ProjectenBibliotheek``). De
voortgangsbalk ("modellen compleet") en de "ontbrekend materiaal"-
waarschuwing zijn bewust komen te vervallen — daar bestaat geen
backend-concept voor (geen compleetheids-/voorraad-tracking), en die
nabootsen zou misleidend zijn."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from robocutter.projecten.models import Project, ProjectStatus
from robocutter.ui.icons import icon_pixmap
from robocutter.ui.theme import Theme

_STATUS_CHIP = {
    ProjectStatus.WERKVOORBEREIDING: ("prep", "neutral_dot"),
    ProjectStatus.IN_PRODUCTIE: ("production", "accent"),
    ProjectStatus.INSTALLATIE: ("install", "indigo"),
    ProjectStatus.AFGEROND: ("done", "success"),
}


def _status_combo(project: Project, theme: Theme, on_status_gewijzigd) -> QComboBox:
    """Zelfde kleurcodering als de statische statuschip, maar nu een
    echte ``QComboBox`` — op Svens verzoek kun je de status van een
    project zo meteen vanaf het Dashboard wijzigen, zonder het project
    eerst te hoeven openen. Consumeert zijn eigen muisklikken (standaard
    Qt-gedrag voor een QComboBox), dus dit opent nooit per ongeluk ook
    het project via ``ProjectCard.mousePressEvent``."""

    _, dot_color_attr = _STATUS_CHIP[project.status]
    accentkleur = getattr(theme, dot_color_attr)

    combo = QComboBox()
    combo.setProperty("role", "cardStatusCombo")
    combo.setCursor(Qt.CursorShape.PointingHandCursor)
    combo.setStyleSheet(
        f"QComboBox[role=\"cardStatusCombo\"] {{ color: {accentkleur}; border-color: {accentkleur}; }}"
    )
    for status in ProjectStatus:
        combo.addItem(status.value, status.value)
    combo.setCurrentIndex(combo.findData(project.status.value))
    # QComboBox-userData van een str-Enum komt bij het uitlezen altijd als
    # kale str terug, nooit als het oorspronkelijke enum-lid (zelfde
    # Qt/PySide6-eigenaardigheid als elders in deze codebase) -- daarom
    # hier expliciet met .value opslaan en via de enum-constructor
    # terugzetten, i.p.v. te vertrouwen op wat currentData() teruggeeft.
    combo.currentIndexChanged.connect(
        lambda _i, c=combo: on_status_gewijzigd(project.id, ProjectStatus(c.currentData()))
    )
    return combo


def _datum_tekst(d) -> str:
    return d.isoformat() if d is not None else "—"


class ProjectCard(QFrame):
    def __init__(self, project: Project, theme: Theme, on_click, on_status_gewijzigd, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("ProjectCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._on_click = on_click
        self._project_id = project.id

        layout = QVBoxLayout(self)
        layout.setContentsMargins(17, 16, 17, 16)
        layout.setSpacing(11)

        top_row = QHBoxLayout()
        top_row.addWidget(_status_combo(project, theme, on_status_gewijzigd))
        top_row.addStretch(1)
        layout.addLayout(top_row)

        title = QLabel(project.naam)
        title.setObjectName("CardTitle")
        layout.addWidget(title)

        client_line = QLabel(f"Klant: {project.klant} · {project.opdrachtnummer or '—'}")
        client_line.setProperty("role", "cardMeta")
        layout.addWidget(client_line)

        delivery_row = QHBoxLayout()
        delivery_row.setSpacing(6)
        delivery_icon = QLabel()
        delivery_icon.setPixmap(icon_pixmap("calendar", theme.text_faint, 13))
        delivery_row.addWidget(delivery_icon)
        delivery_text = QLabel(f"Oplevering {_datum_tekst(project.opleverdatum)}")
        delivery_text.setProperty("role", "cardMeta")
        delivery_row.addWidget(delivery_text)
        delivery_row.addStretch(1)
        layout.addLayout(delivery_row)

        samenstelling_row = QHBoxLayout()
        samenstelling_row.setSpacing(6)
        samenstelling_icon = QLabel()
        samenstelling_icon.setPixmap(icon_pixmap("layers", theme.text_faint, 13))
        samenstelling_row.addWidget(samenstelling_icon)
        delen = []
        if project.modelinstanties:
            delen.append(f"{len(project.modelinstanties)} model{'len' if len(project.modelinstanties) != 1 else ''}")
        if project.losse_onderdelen:
            delen.append(f"{len(project.losse_onderdelen)} los onderdeel" if len(project.losse_onderdelen) == 1 else f"{len(project.losse_onderdelen)} losse onderdelen")
        samenstelling_text = QLabel(", ".join(delen) if delen else "Nog geen samenstelling")
        samenstelling_text.setProperty("role", "cardMeta")
        samenstelling_row.addWidget(samenstelling_text)
        samenstelling_row.addStretch(1)
        layout.addLayout(samenstelling_row)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_click(self._project_id)
        super().mousePressEvent(event)
