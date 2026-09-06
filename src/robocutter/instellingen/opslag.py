"""Opslag van de instellingen als klein JSON-bestand, bewust los van
``data/robocutter.db`` (zie ``robocutter.instellingen`` docstring)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from robocutter.instellingen.models import Instellingen

__all__ = ["standaard_instellingen_pad", "laad_instellingen", "sla_instellingen_op"]


def standaard_instellingen_pad() -> Path:
    appdata = os.environ.get("APPDATA")
    basis = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    return basis / "RoboCutter" / "instellingen.json"


def laad_instellingen(pad: Path | None = None) -> Instellingen:
    """Geeft de standaardwaarden terug als het bestand ontbreekt of
    corrupt is — instellingen zijn nooit een harde vereiste om de app
    te kunnen starten."""

    bestand = pad or standaard_instellingen_pad()
    if not bestand.exists():
        return Instellingen()
    try:
        ruwe_data = json.loads(bestand.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return Instellingen()

    velden = {veld.name for veld in Instellingen.__dataclass_fields__.values()}
    return Instellingen(**{k: v for k, v in ruwe_data.items() if k in velden})


def sla_instellingen_op(instellingen: Instellingen, pad: Path | None = None) -> None:
    bestand = pad or standaard_instellingen_pad()
    bestand.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "opslag_map": instellingen.opslag_map,
        "thema": instellingen.thema,
        "bedrijfslogo_pad": instellingen.bedrijfslogo_pad,
        "standaard_zaagstrategie": instellingen.standaard_zaagstrategie,
        "werkvoorbereider_naam": instellingen.werkvoorbereider_naam,
    }
    bestand.write_text(json.dumps(data, indent=2), encoding="utf-8")
