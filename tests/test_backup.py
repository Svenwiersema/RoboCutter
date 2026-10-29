"""Tests voor de automatische back-up (hoofdstuk 12): maken, het
bewaarschema (24 uur alles, 14 dagen per dag, 8 weken per week),
terugzetten met veiligstellen van de huidige database, en de
back-upinstellingen. Alles in ``tmp_path``, nooit de echte datamap.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

import pytest

from robocutter.backup.beheer import (
    BackupError,
    backup_nodig,
    laatste_backup,
    lijst_backups,
    maak_backup,
    opruimen,
    zelfde_schijf,
    zet_terug,
)
from robocutter.instellingen.beheer import InstellingenBeheer
from robocutter.instellingen.opslag import laad_instellingen

NU = datetime(2026, 10, 29, 14, 30, 0)


def _maak_db(pad, waarde: str) -> None:
    verbinding = sqlite3.connect(pad)
    verbinding.execute("CREATE TABLE IF NOT EXISTS t (waarde TEXT)")
    verbinding.execute("DELETE FROM t")
    verbinding.execute("INSERT INTO t VALUES (?)", (waarde,))
    verbinding.commit()
    verbinding.close()


def _lees_db(pad) -> str:
    verbinding = sqlite3.connect(pad)
    try:
        return verbinding.execute("SELECT waarde FROM t").fetchone()[0]
    finally:
        verbinding.close()


def test_backup_is_volledige_kopie_en_wordt_gevonden(tmp_path):
    db = tmp_path / "robocutter.db"
    _maak_db(db, "origineel")
    backup = maak_backup(db, tmp_path / "backups", NU)

    assert backup.pad.name == "robocutter-backup-20261029-143000.db"
    assert _lees_db(backup.pad) == "origineel"
    assert laatste_backup(tmp_path / "backups") == backup
    assert not list((tmp_path / "backups").glob("*.bezig"))


def test_backup_terwijl_database_open_is(tmp_path):
    db = tmp_path / "robocutter.db"
    _maak_db(db, "open")
    open_verbinding = sqlite3.connect(db)  # zoals de app
    try:
        backup = maak_backup(db, tmp_path / "backups", NU)
    finally:
        open_verbinding.close()
    assert _lees_db(backup.pad) == "open"


def test_twee_backups_in_dezelfde_seconde_overschrijven_elkaar_niet(tmp_path):
    db = tmp_path / "robocutter.db"
    _maak_db(db, "a")
    eerste = maak_backup(db, tmp_path / "backups", NU)
    _maak_db(db, "b")
    tweede = maak_backup(db, tmp_path / "backups", NU)

    assert eerste.pad != tweede.pad
    assert _lees_db(eerste.pad) == "a"
    assert lijst_backups(tmp_path / "backups")[0].pad == tweede.pad


def test_lijst_negeert_andere_bestanden(tmp_path):
    backups = tmp_path / "backups"
    backups.mkdir()
    (backups / "notities.txt").write_text("x")
    (backups / "robocutter-backup-kapot.db").write_text("x")
    (backups / "robocutter-backup-20261029-143000.db.bezig").write_text("x")
    assert lijst_backups(backups) == []
    assert lijst_backups(tmp_path / "bestaat-niet") == []


def test_backup_zonder_database_geeft_nette_fout(tmp_path):
    with pytest.raises(BackupError):
        maak_backup(tmp_path / "bestaat-niet.db", tmp_path / "backups", NU)


@pytest.mark.parametrize(
    ("frequentie", "leeftijd", "nodig"),
    [
        ("uur", timedelta(minutes=59), False),
        ("uur", timedelta(hours=1), True),
        ("dag", timedelta(hours=23), False),
        ("dag", timedelta(days=1), True),
        ("week", timedelta(days=6), False),
        ("week", timedelta(days=7), True),
    ],
)
def test_backup_nodig_volgt_frequentie(tmp_path, frequentie, leeftijd, nodig):
    db = tmp_path / "robocutter.db"
    _maak_db(db, "x")
    maak_backup(db, tmp_path / "backups", NU - leeftijd)
    assert backup_nodig(tmp_path / "backups", frequentie, NU) is nodig


def test_zonder_backups_is_er_altijd_een_nodig(tmp_path):
    assert backup_nodig(tmp_path / "backups", "week", NU)


def test_opruimen_houdt_24_uur_alles_dan_per_dag_dan_per_week(tmp_path):
    backups = tmp_path / "backups"
    backups.mkdir()
    # Elk uur een back-up, 120 dagen lang (alleen de bestandsnaam telt).
    for uur in range(0, 120 * 24):
        tijd = NU - timedelta(hours=uur)
        (backups / f"robocutter-backup-{tijd.strftime('%Y%m%d-%H%M%S')}.db").write_bytes(b"")

    opruimen(backups, NU)
    over = lijst_backups(backups)
    tijden = [b.tijdstip for b in over]

    laatste_24u = [t for t in tijden if NU - t < timedelta(hours=24)]
    assert len(laatste_24u) == 24
    dag_grens = NU - timedelta(days=14)
    per_dag = [t for t in tijden if dag_grens <= t and NU - t >= timedelta(hours=24)]
    assert len(per_dag) == len({t.date() for t in per_dag})  # max één per dag
    assert len(per_dag) >= 13
    week_grens = dag_grens - timedelta(weeks=8)
    per_week = [t for t in tijden if week_grens <= t < dag_grens]
    assert len(per_week) == len({t.isocalendar()[:2] for t in per_week})
    assert 8 <= len(per_week) <= 9
    assert all(t >= week_grens for t in tijden)  # niets ouder


def test_opruimen_laat_de_nieuwste_altijd_staan(tmp_path):
    db = tmp_path / "robocutter.db"
    _maak_db(db, "x")
    oud = maak_backup(db, tmp_path / "backups", NU - timedelta(days=400))
    assert opruimen(tmp_path / "backups", NU) == []
    assert oud.pad.exists()


def test_terugzetten_stelt_huidige_database_eerst_veilig(tmp_path):
    db = tmp_path / "robocutter.db"
    backups = tmp_path / "backups"
    _maak_db(db, "gisteren")
    gisteren = maak_backup(db, backups, NU - timedelta(days=1))
    _maak_db(db, "vandaag")

    open_verbinding = sqlite3.connect(db)  # de app heeft hem open
    try:
        veiliggesteld = zet_terug(gisteren.pad, db, backups, NU)
    finally:
        open_verbinding.close()

    assert _lees_db(db) == "gisteren"
    assert veiliggesteld is not None and _lees_db(veiliggesteld.pad) == "vandaag"
    assert veiliggesteld.voor_terugzetten
    assert veiliggesteld.pad.name == "robocutter-backup-20261029-143000-voor-terugzetten.db"
    assert lijst_backups(backups)[0] == veiliggesteld  # telt als gewone (nieuwste) back-up mee
    assert not gisteren.voor_terugzetten
    assert _lees_db(gisteren.pad) == "gisteren"  # back-up zelf ongewijzigd


def test_beschadigde_backup_wordt_niet_teruggezet(tmp_path):
    db = tmp_path / "robocutter.db"
    backups = tmp_path / "backups"
    backups.mkdir()
    _maak_db(db, "vandaag")
    kapot = backups / "robocutter-backup-20261028-120000.db"
    kapot.write_bytes(b"dit is geen database" * 100)

    with pytest.raises(BackupError):
        zet_terug(kapot, db, backups, NU)
    assert _lees_db(db) == "vandaag"
    assert len(lijst_backups(backups)) == 1  # niets veiliggesteld, niets gewijzigd


def test_zelfde_schijf(tmp_path):
    assert zelfde_schijf(tmp_path / "a" / "robocutter.db", tmp_path / "b" / "backups")


def test_backupinstellingen_standaard_en_bewaard(tmp_path):
    beheer = InstellingenBeheer(bestand_pad=tmp_path / "instellingen.json", standaard_data_map=tmp_path / "data")
    assert beheer.huidige.backup_frequentie == "dag"
    assert beheer.effectieve_backup_map() == tmp_path / "data" / "backups"

    beheer.bijwerken(backup_frequentie="uur", backup_map=str(tmp_path / "usb"))
    herladen = laad_instellingen(tmp_path / "instellingen.json")
    assert herladen.backup_frequentie == "uur"
    assert herladen.backup_map == str(tmp_path / "usb")
    assert beheer.effectieve_backup_map() == tmp_path / "usb"

    with pytest.raises(ValueError):
        beheer.bijwerken(backup_frequentie="maand")
