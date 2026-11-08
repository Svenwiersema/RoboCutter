"""Startpunt van de RoboCutter-UI.

Gebruik: python -m robocutter.ui.app
"""

from __future__ import annotations

import sys
from datetime import datetime

from PySide6.QtWidgets import QApplication

from robocutter.instellingen.beheer import InstellingenBeheer
from robocutter.logboek import log, start_logboek, stop_logboek
from robocutter.ui.foutafhandeling import installeer_foutafhandeling
from robocutter.ui.main_window import MainWindow
from robocutter.ui.widgets.scrollwiel import ScrollwielFilter

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
    # Logbestand eerst: ook een fout tijdens het opstarten komt erin.
    log_pad = start_logboek()
    app = QApplication(sys.argv)
    app.setApplicationName("RoboCutter")
    installeer_foutafhandeling(app, log_pad)
    app.aboutToQuit.connect(stop_logboek)
    log.info("Database: %s", InstellingenBeheer().effectieve_db_pad())
    # Keuzelijsten veranderen niet meer per ongeluk door overheen te scrollen.
    scrollwiel = ScrollwielFilter(app)
    app.installEventFilter(scrollwiel)

    window = MainWindow(na_terugzetten=_na_terugzetten(sys.argv[1:]))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
