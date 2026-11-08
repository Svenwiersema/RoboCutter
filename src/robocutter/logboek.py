"""Logbestand van RoboCutter (voor de alphatest op Svens werk).

De .exe draait zonder consolevenster: zonder logbestand verdween een fout
spoorloos. ``start_logboek`` schrijft naar ``%APPDATA%\\RoboCutter\\logboek``
(naast ``instellingen.json``, dus los van de database en de exe):

- ``robocutter.log`` — start, afsluiten en elke onverwachte fout met de
  volledige traceback; roteert bij 1 MB, de laatste 5 blijven bewaard.
- ``vastloper.log`` — als Python zelf omvalt (``faulthandler``), wat het
  gewone logbestand niet meer kan schrijven.

Fouten opvangen en melden gebeurt in ``ui/foutafhandeling.py``; dit deel
heeft geen Qt nodig en is zo ook te testen.
"""

from __future__ import annotations

import faulthandler
import logging
import platform
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType

from robocutter import __version__
from robocutter.instellingen.opslag import standaard_instellingen_pad

__all__ = ["log", "log_fout", "standaard_log_map", "start_logboek", "stop_logboek"]

log = logging.getLogger("robocutter")

_LOGBESTAND = "robocutter.log"
_VASTLOPER = "vastloper.log"
_handler: RotatingFileHandler | None = None
_vastloper_bestand = None


def standaard_log_map() -> Path:
    return standaard_instellingen_pad().parent / "logboek"


def start_logboek(map_: Path | None = None) -> Path:
    """Zet het logbestand op (één keer; nog eens aanroepen doet niets) en
    geeft het pad terug."""
    global _handler, _vastloper_bestand
    map_ = Path(map_) if map_ is not None else standaard_log_map()
    if _handler is not None:
        return Path(_handler.baseFilename)
    map_.mkdir(parents=True, exist_ok=True)
    _handler = RotatingFileHandler(map_ / _LOGBESTAND, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
    log.addHandler(_handler)
    log.setLevel(logging.INFO)
    _vastloper_bestand = open(map_ / _VASTLOPER, "a", encoding="utf-8")  # noqa: SIM115 (blijft open voor faulthandler)
    faulthandler.enable(_vastloper_bestand)
    log.info(
        "RoboCutter %s gestart (Python %s, %s%s)",
        __version__, platform.python_version(), platform.platform(), ", exe" if getattr(sys, "frozen", False) else "",
    )
    return map_ / _LOGBESTAND


def stop_logboek() -> None:
    """Sluit het logbestand (bij afsluiten, en in tests)."""
    global _handler, _vastloper_bestand
    if _handler is not None:
        log.info("RoboCutter afgesloten")
        log.removeHandler(_handler)
        _handler.close()
        _handler = None
    if _vastloper_bestand is not None:
        faulthandler.disable()
        _vastloper_bestand.close()
        _vastloper_bestand = None


def log_fout(
    soort: type[BaseException], fout: BaseException, traceback: TracebackType | None, waar: str = ""
) -> str:
    """Schrijft een onverwachte fout met traceback weg; geeft een korte
    samenvatting terug voor de melding op het scherm."""
    log.error("Onverwachte fout%s", f" ({waar})" if waar else "", exc_info=(soort, fout, traceback))
    tekst = str(fout).strip()
    return f"{soort.__name__}: {tekst}" if tekst else soort.__name__
