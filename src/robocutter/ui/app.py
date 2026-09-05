"""Startpunt van de RoboCutter-UI.

Gebruik: python -m robocutter.ui.app
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from robocutter.ui.main_window import MainWindow

# Inter (design/chapters/11-ux-ui.md) is nog niet als lettertypebestand
# gebundeld; de stylesheet valt terug op "Segoe UI" totdat dat is toegevoegd.


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("RoboCutter")

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
