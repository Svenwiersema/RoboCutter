"""Projectkaart voor de home pagina (rasterweergave van alle projecten)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QToolButton,
    QVBoxLayout,
)

from robocutter.ui.icons import icon, icon_pixmap
from robocutter.ui.sample_data import ProjectStatus, ProjectSummary
from robocutter.ui.theme import Theme

_STATUS_CHIP = {
    ProjectStatus.WERKVOORBEREIDING: ("prep", "neutral_dot"),
    ProjectStatus.IN_PRODUCTIE: ("production", "accent"),
    ProjectStatus.INSTALLATIE: ("install", "indigo"),
    ProjectStatus.AFGEROND: ("done", "success"),
}


def _status_chip(status: ProjectStatus, theme: Theme) -> QFrame:
    chip_key, dot_color_attr = _STATUS_CHIP[status]
    dot_color = getattr(theme, dot_color_attr)

    chip = QFrame()
    chip.setProperty("chip", chip_key)
    layout = QHBoxLayout(chip)
    layout.setContentsMargins(8, 3, 9, 3)
    layout.setSpacing(6)

    dot = QLabel()
    dot.setFixedSize(7, 7)
    dot.setStyleSheet(f"background: {dot_color}; border-radius: 3px;")
    layout.addWidget(dot)

    text = QLabel(status.value)
    layout.addWidget(text)
    return chip


class ProjectCard(QFrame):
    def __init__(self, project: ProjectSummary, theme: Theme, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("ProjectCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(17, 16, 17, 16)
        layout.setSpacing(11)

        top_row = QHBoxLayout()
        top_row.addWidget(_status_chip(project.status, theme))
        top_row.addStretch(1)
        kebab = QToolButton()
        kebab.setObjectName("KebabBtn")
        kebab.setIcon(icon("kebab", theme.text_faint, 16))
        kebab.setFixedSize(26, 26)
        kebab.setCursor(Qt.CursorShape.PointingHandCursor)
        top_row.addWidget(kebab)
        layout.addLayout(top_row)

        title = QLabel(project.naam)
        title.setObjectName("CardTitle")
        layout.addWidget(title)

        client_line = QLabel(f"Klant: {project.klant} · {project.opdrachtnummer}")
        client_line.setProperty("role", "cardMeta")
        layout.addWidget(client_line)

        delivery_row = QHBoxLayout()
        delivery_row.setSpacing(6)
        delivery_icon = QLabel()
        delivery_icon.setPixmap(icon_pixmap("calendar", theme.text_faint, 13))
        delivery_row.addWidget(delivery_icon)
        delivery_text = QLabel(f"Oplevering {project.opleverdatum}")
        delivery_text.setProperty("role", "cardMeta")
        delivery_row.addWidget(delivery_text)
        delivery_row.addStretch(1)
        layout.addLayout(delivery_row)

        progress_label_row = QHBoxLayout()
        progress_caption = QLabel("Modellen compleet")
        progress_caption.setProperty("role", "progressLabel")
        progress_label_row.addWidget(progress_caption)
        progress_label_row.addStretch(1)
        frac = QLabel(f"{project.modellen_compleet} / {project.modellen_totaal}")
        frac.setProperty("role", "progressFrac")
        progress_label_row.addWidget(frac)
        layout.addLayout(progress_label_row)

        complete = project.modellen_compleet >= project.modellen_totaal
        progress = QProgressBar()
        progress.setObjectName("CardProgress")
        progress.setProperty("complete", "true" if complete else "false")
        progress.setTextVisible(False)
        progress.setRange(0, project.modellen_totaal)
        progress.setValue(project.modellen_compleet)
        layout.addWidget(progress)

        if project.ontbrekend_materiaal:
            warning = QFrame()
            warning.setObjectName("CardWarning")
            warning_layout = QHBoxLayout(warning)
            warning_layout.setContentsMargins(9, 7, 9, 7)
            warning_layout.setSpacing(7)
            warning_icon = QLabel()
            warning_icon.setPixmap(icon_pixmap("warning", theme.warning_ink, 14))
            warning_icon.setAlignment(Qt.AlignmentFlag.AlignTop)
            warning_layout.addWidget(warning_icon, 0, Qt.AlignmentFlag.AlignTop)
            warning_text = QLabel(
                f"Materiaal ontbreekt: <b>{project.ontbrekend_materiaal}</b> niet in bibliotheek"
            )
            warning_text.setWordWrap(True)
            warning_layout.addWidget(warning_text, 1)
            layout.addWidget(warning)
