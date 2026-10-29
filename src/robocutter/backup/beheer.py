"""Back-ups maken, opruimen en terugzetten.

Keuzes van Sven (2026-10-29):
- hoe vaak is instelbaar: elk uur, dagelijks (standaard) of wekelijks;
- de map is te kiezen, standaard een ``backups``-map naast de database.
  Staat die op dezelfde schijf, dan waarschuwt de app (``zelfde_schijf``):
  zo'n back-up helpt niet als de schijf kapotgaat;
- bewaren: alles van de laatste 24 uur, daarna de nieuwste per dag voor 14
  dagen, en daarvoor de nieuwste per week voor nog 8 weken (``opruimen``);
- terugzetten kan vanuit de app; de huidige database wordt eerst zelf nog
  veiliggesteld als back-up.

Een back-up is een volledige kopie via de SQLite-backup-API
(``Connection.backup``), dus ook veilig terwijl de app de database open
heeft. Eerst naar een tijdelijke naam, dan hernoemen: een afgebroken
back-up laat zo nooit een half bestand achter dat als back-up meetelt.
"""

from __future__ import annotations

import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

__all__ = [
    "BackupBestand",
    "BackupError",
    "lijst_backups",
    "laatste_backup",
    "backup_nodig",
    "maak_backup",
    "opruimen",
    "zet_terug",
    "zelfde_schijf",
    "BACKUP_INTERVAL",
]

BACKUP_INTERVAL = {
    "uur": timedelta(hours=1),
    "dag": timedelta(days=1),
    "week": timedelta(weeks=1),
}

_VOORVOEGSEL = "robocutter-backup-"
_TIJD_FORMAAT = "%Y%m%d-%H%M%S"
# robocutter-backup-20261029-143005.db, met -2/-3 als er in dezelfde
# seconde al een was, en -voor-terugzetten voor de back-up die vlak voor
# een terugzetting van de huidige stand gemaakt wordt.
_ACHTERVOEGSEL_TERUGZETTEN = "-voor-terugzetten"
_PATROON = re.compile(
    rf"^{_VOORVOEGSEL}(\d{{8}}-\d{{6}})(?:-(\d+))?({_ACHTERVOEGSEL_TERUGZETTEN})?\.db$"
)

_DAGEN_BEWAREN = 14
_WEKEN_BEWAREN = 8


class BackupError(Exception):
    """Back-up maken of terugzetten lukt niet; de tekst is voor de gebruiker."""


@dataclass(frozen=True)
class BackupBestand:
    pad: Path
    tijdstip: datetime
    grootte: int  # bytes
    voor_terugzetten: bool = False


def lijst_backups(backup_map: Path) -> list[BackupBestand]:
    """Alle back-ups in ``backup_map``, nieuwste eerst. Andere bestanden in
    de map worden genegeerd."""
    if not backup_map.is_dir():
        return []
    gevonden: list[tuple[datetime, int, BackupBestand]] = []
    for pad in backup_map.iterdir():
        treffer = _PATROON.match(pad.name)
        if treffer is None or not pad.is_file():
            continue
        try:
            tijdstip = datetime.strptime(treffer.group(1), _TIJD_FORMAAT)
            grootte = pad.stat().st_size
        except (ValueError, OSError):
            continue
        volgnummer = int(treffer.group(2) or 1)
        gevonden.append(
            (tijdstip, volgnummer, BackupBestand(pad, tijdstip, grootte, voor_terugzetten=bool(treffer.group(3))))
        )
    gevonden.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return [b for _, _, b in gevonden]


def laatste_backup(backup_map: Path) -> BackupBestand | None:
    backups = lijst_backups(backup_map)
    return backups[0] if backups else None


def backup_nodig(backup_map: Path, frequentie: str, nu: datetime | None = None) -> bool:
    """True als er nog geen back-up is, of de laatste ouder is dan het
    interval van ``frequentie``."""
    nu = nu or datetime.now()
    laatste = laatste_backup(backup_map)
    return laatste is None or nu - laatste.tijdstip >= BACKUP_INTERVAL[frequentie]


def maak_backup(
    db_pad: Path, backup_map: Path, nu: datetime | None = None, voor_terugzetten: bool = False
) -> BackupBestand:
    """Maakt een volledige kopie van ``db_pad`` in ``backup_map``."""
    nu = (nu or datetime.now()).replace(microsecond=0)
    if not db_pad.is_file():
        raise BackupError(f"De database {db_pad} bestaat niet.")
    try:
        backup_map.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise BackupError(
            f"De back-upmap {backup_map} is niet bereikbaar. Is de schijf, USB-stick of netwerkmap aangesloten?"
        ) from exc

    basis = f"{_VOORVOEGSEL}{nu.strftime(_TIJD_FORMAAT)}"
    achter = _ACHTERVOEGSEL_TERUGZETTEN if voor_terugzetten else ""
    doel = backup_map / f"{basis}{achter}.db"
    volgnummer = 2
    while doel.exists():
        doel = backup_map / f"{basis}-{volgnummer}{achter}.db"
        volgnummer += 1
    tijdelijk = doel.with_name(doel.name + ".bezig")

    try:
        _kopieer_database(db_pad, tijdelijk)
        os.replace(tijdelijk, doel)
    except (sqlite3.Error, OSError) as exc:
        tijdelijk.unlink(missing_ok=True)
        raise BackupError(
            f"Back-up maken in {backup_map} is mislukt. Is er genoeg ruimte en mag RoboCutter daar schrijven?"
        ) from exc
    return BackupBestand(doel, nu, doel.stat().st_size, voor_terugzetten=voor_terugzetten)


def opruimen(backup_map: Path, nu: datetime | None = None) -> list[Path]:
    """Verwijdert back-ups die buiten het bewaarschema vallen en geeft de
    verwijderde paden terug. De nieuwste blijft altijd staan."""
    nu = nu or datetime.now()
    backups = lijst_backups(backup_map)  # nieuwste eerst
    houden: set[Path] = set()
    gezien_dagen: set = set()
    gezien_weken: set = set()
    dag_grens = nu - timedelta(days=_DAGEN_BEWAREN)
    week_grens = dag_grens - timedelta(weeks=_WEKEN_BEWAREN)
    for index, backup in enumerate(backups):
        if index == 0 or nu - backup.tijdstip < timedelta(hours=24):
            houden.add(backup.pad)
        elif backup.tijdstip >= dag_grens:
            dag = backup.tijdstip.date()
            if dag not in gezien_dagen:
                gezien_dagen.add(dag)
                houden.add(backup.pad)
        elif backup.tijdstip >= week_grens:
            week = backup.tijdstip.isocalendar()[:2]
            if week not in gezien_weken:
                gezien_weken.add(week)
                houden.add(backup.pad)

    verwijderd: list[Path] = []
    for backup in backups:
        if backup.pad in houden:
            continue
        try:
            backup.pad.unlink()
        except OSError:
            continue  # bv. even in gebruik; volgende keer opnieuw
        verwijderd.append(backup.pad)
    return verwijderd


def zet_terug(
    backup_pad: Path, db_pad: Path, backup_map: Path, nu: datetime | None = None
) -> BackupBestand | None:
    """Zet ``backup_pad`` terug als database. Eerst wordt de huidige
    database zelf als back-up veiliggesteld (die wordt teruggegeven, of
    None als er nog geen database was), zodat terugzetten nooit iets
    onherroepelijk weggooit.

    Overschrijft de inhoud van het bestand via de backup-API, dus ook als
    de app het open heeft; de app moet daarna wel herstarten, want de
    bibliotheken houden hun gegevens in het geheugen."""
    _controleer_backup(backup_pad)
    veiliggesteld = maak_backup(db_pad, backup_map, nu, voor_terugzetten=True) if db_pad.is_file() else None
    try:
        db_pad.parent.mkdir(parents=True, exist_ok=True)
        _kopieer_database(backup_pad, db_pad)
    except (sqlite3.Error, OSError) as exc:
        raise BackupError(f"Terugzetten is mislukt ({exc}). De huidige database is niet gewijzigd.") from exc
    return veiliggesteld


def zelfde_schijf(pad_a: Path, pad_b: Path) -> bool:
    """True als beide paden op dezelfde schijf staan (ook als een van beide
    nog niet bestaat: dan telt de dichtstbijzijnde bestaande bovenmap)."""
    try:
        return os.stat(_bestaand_deel(pad_a)).st_dev == os.stat(_bestaand_deel(pad_b)).st_dev
    except OSError:
        return Path(pad_a).resolve().anchor.lower() == Path(pad_b).resolve().anchor.lower()


def _bestaand_deel(pad: Path) -> Path:
    pad = Path(pad).resolve()
    while not pad.exists() and pad != pad.parent:
        pad = pad.parent
    return pad


def _kopieer_database(bron_pad: Path, doel_pad: Path) -> None:
    bron = sqlite3.connect(bron_pad)
    try:
        doel = sqlite3.connect(doel_pad)
        try:
            bron.backup(doel)
        finally:
            doel.close()
    finally:
        bron.close()


def _controleer_backup(backup_pad: Path) -> None:
    if not backup_pad.is_file():
        raise BackupError(f"De back-up {backup_pad.name} bestaat niet (meer).")
    try:
        verbinding = sqlite3.connect(f"file:{backup_pad.as_posix()}?mode=ro", uri=True)
        try:
            resultaat = verbinding.execute("PRAGMA integrity_check").fetchone()
        finally:
            verbinding.close()
    except sqlite3.Error as exc:
        raise BackupError(f"De back-up {backup_pad.name} is geen geldige database ({exc}).") from exc
    if not resultaat or resultaat[0] != "ok":
        raise BackupError(f"De back-up {backup_pad.name} is beschadigd en wordt niet teruggezet.")
