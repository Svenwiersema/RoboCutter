"""Logbestand voor de alphatest: start, fouten met traceback, afsluiten.

Altijd een map in ``tmp_path`` meegeven — nooit het echte
``%APPDATA%\\RoboCutter\\logboek`` (zelfde les als bij de instellingen-tests).
"""

from __future__ import annotations

import sys

import pytest

from robocutter import __version__
from robocutter.logboek import log, log_fout, start_logboek, stop_logboek


@pytest.fixture
def logmap(tmp_path):
    yield tmp_path / "logboek"
    stop_logboek()


def test_start_schrijft_versie_en_maakt_de_map(logmap):
    pad = start_logboek(logmap)
    assert pad == logmap / "robocutter.log"
    assert (logmap / "vastloper.log").exists()
    assert f"RoboCutter {__version__} gestart" in pad.read_text(encoding="utf-8")


def test_nog_eens_starten_voegt_geen_tweede_logbestand_toe(logmap, tmp_path):
    eerste = start_logboek(logmap)
    tweede = start_logboek(tmp_path / "ergens_anders")
    assert tweede == eerste
    log.info("één keer")
    assert eerste.read_text(encoding="utf-8").count("één keer") == 1
    assert not (tmp_path / "ergens_anders").exists()


def test_fout_komt_met_traceback_in_het_logbestand(logmap):
    pad = start_logboek(logmap)
    try:
        {}["materiaal"]
    except KeyError:
        samenvatting = log_fout(*sys.exc_info(), waar="test")
    assert samenvatting == "KeyError: 'materiaal'"
    inhoud = pad.read_text(encoding="utf-8")
    assert "Onverwachte fout (test)" in inhoud
    assert "Traceback" in inhoud and "KeyError: 'materiaal'" in inhoud


def test_fout_zonder_tekst_en_afsluiten(logmap):
    pad = start_logboek(logmap)
    try:
        raise RuntimeError()
    except RuntimeError:
        assert log_fout(*sys.exc_info()) == "RuntimeError"
    stop_logboek()
    assert pad.read_text(encoding="utf-8").rstrip().endswith("RoboCutter afgesloten")
    log.info("na afsluiten")
    assert "na afsluiten" not in pad.read_text(encoding="utf-8")
