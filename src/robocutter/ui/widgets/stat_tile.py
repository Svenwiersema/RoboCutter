"""KPI-tegel bovenaan de home pagina (actieve projecten, opleverdata, ...)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from robocutter.ui.icons import icon_pixmap


class StatTile(QFrame):
    def __init__(
        self,
        label: str,
        value: str,
        footer: str,
        icon_name: str,
        icon_color: str,
        tone: str = "neutral",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("StatTile")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(9)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        label_widget = QLabel(label)
        label_widget.setProperty("role", "statLabel")
        top_row.addWidget(label_widget)
        top_row.addStretch(1)

        icon_frame = QFrame()
        icon_frame.setProperty("role", "statIcon")
        icon_frame.setProperty("tone", tone)
        icon_frame.setFixedSize(26, 26)
        icon_frame_layout = QHBoxLayout(icon_frame)
        icon_frame_layout.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel()
        icon_label.setPixmap(icon_pixmap(icon_name, icon_color, 14))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_frame_layout.addWidget(icon_label)
        top_row.addWidget(icon_frame)

        layout.addLayout(top_row)

        value_label = QLabel(value)
        value_label.setProperty("role", "statValue")
        value_label.setProperty("tone", tone)
        layout.addWidget(value_label)

        footer_label = QLabel(footer)
        footer_label.setProperty("role", "statFoot")
        footer_label.setWordWrap(True)
        layout.addWidget(footer_label)
