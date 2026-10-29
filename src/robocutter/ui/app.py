"""Startpunt van de RoboCutter-UI.

Gebruik: python -m robocutter.ui.app
"""

from __future__ import annotations

import sys
from datetime import datetime

from PySide6.QtWidgets import QApplication

from robocutter.ui.main_window import MainWindow

# Inter (design/chapters/11-ux-ui.md) is nog niet als lettertypebestand
# gebundeld; de stylesheet valt terug op "Segoe UI" totdat dat is toegevoegd.


def _na_terugzetten(argumenten: list[str]) -> tuple[datetime, datetime | None] | None:
    """Na "Terugzetten" herstart RoboCutter zichzelf met ``--teruggezet
    <tijdstip>`` (en ``--veiliggesteld <tijdstip>``), zie
    ``MainWindow._terugzetten``."""

    def waarde(vlag: str) -> datetime | None:
        if vlag in argumenten and argumenten.index(vlag) + 1 < len(argumenten):
            try:
                return datetime.fromisoformat(argumenten[argumenten.index(vlag) + 1])
            except ValueError:
                return None
        return None

    teruggezet = waarde("--teruggezet")
    return (teruggezet, waarde("--veiliggesteld")) if teruggezet is not None else None


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("RoboCutter")

    window = MainWindow(na_terugzetten=_na_terugzetten(sys.argv[1:]))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
