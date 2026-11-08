"""Materiaaltekst uit een importbestand koppelen aan een materiaal uit de
bibliotheek (hoofdstuk 10, bevestigd door Sven): eerst de productcode, dan
de naam — hoofdletters en spaties tellen niet — en pas als niets precies
past een eerder door de gebruiker gekozen koppeling (``MateriaalKoppelingen``).
Een exacte productcode of naam gaat dus altijd voor: een onthouden keuze
uit de tijd dat het materiaal nog niet bestond (Svens test: "Beuken massief
26" eerst aan Melamine grijs gekoppeld, daarna zelf aangemaakt) mag die
niet overschrijven. Wat niet gevonden wordt, krijgt "bedoelde je…?"-
suggesties.
"""

from __future__ import annotations

import difflib
import re
import sqlite3

from robocutter.importeren import opslag
from robocutter.importeren.models import ImportRegel
from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.materialen.models import MateriaalStatus

__all__ = ["MateriaalKoppelingen", "normaliseer", "stel_koppeling_voor", "suggesties"]


def normaliseer(tekst: str) -> str:
    """"Eiken  Multiplex 18×18" en "eiken multiplex 18x18" zijn hetzelfde."""
    return re.sub(r"\s+", " ", tekst.replace("×", "x")).strip().casefold()


class MateriaalKoppelingen:
    """Onthouden koppelingen (genormaliseerde tekst -> materiaal_id)."""

    def __init__(self, db_verbinding: sqlite3.Connection | None = None) -> None:
        self._db = db_verbinding
        self._koppelingen: dict[str, str] = opslag.laad_alles(db_verbinding) if db_verbinding is not None else {}

    def materiaal_voor(self, tekst: str) -> str | None:
        return self._koppelingen.get(normaliseer(tekst))

    def onthoud(self, tekst: str, materiaal_id: str) -> None:
        sleutel = normaliseer(tekst)
        self._koppelingen[sleutel] = materiaal_id
        if self._db is not None:
            opslag.opslaan(self._db, sleutel, materiaal_id)

    def vergeet(self, tekst: str) -> None:
        sleutel = normaliseer(tekst)
        self._koppelingen.pop(sleutel, None)
        if self._db is not None:
            opslag.verwijderen(self._db, sleutel)


def zoek_materiaal(tekst: str, materialen: MaterialenBibliotheek, onthouden: MateriaalKoppelingen | None = None) -> str | None:
    sleutel = normaliseer(tekst)
    kandidaten = sorted(materialen.lijst(), key=lambda m: m.status != MateriaalStatus.ACTIEF)
    for m in kandidaten:
        if m.productcode and normaliseer(m.productcode) == sleutel:
            return m.id
    for m in kandidaten:
        if normaliseer(m.naam) == sleutel:
            return m.id
    if onthouden is not None:
        materiaal_id = onthouden.materiaal_voor(tekst)
        if materiaal_id is not None:
            try:
                materialen.ophalen(materiaal_id)
                return materiaal_id
            except KeyError:
                pass  # materiaal is intussen verwijderd
    return None


def suggesties(tekst: str, materialen: MaterialenBibliotheek, aantal: int = 3) -> list[str]:
    """Materiaal-id's die op ``tekst`` lijken (naam of productcode), beste
    eerst; alleen actieve materialen."""
    sleutel = normaliseer(tekst)
    per_tekst: dict[str, str] = {}
    for m in materialen.lijst():
        if m.status != MateriaalStatus.ACTIEF:
            continue
        per_tekst.setdefault(normaliseer(m.naam), m.id)
        if m.productcode:
            per_tekst.setdefault(normaliseer(m.productcode), m.id)
    resultaat: list[str] = []
    for gevonden in difflib.get_close_matches(sleutel, list(per_tekst), n=aantal * 2, cutoff=0.5):
        materiaal_id = per_tekst[gevonden]
        if materiaal_id not in resultaat:
            resultaat.append(materiaal_id)
    return resultaat[:aantal]


def stel_koppeling_voor(
    regels: list[ImportRegel], materialen: MaterialenBibliotheek, onthouden: MateriaalKoppelingen | None = None
) -> dict[str, str | None]:
    """Per verschillende materiaaltekst (genormaliseerd) het gevonden
    materiaal, of ``None`` als de gebruiker moet kiezen."""
    koppeling: dict[str, str | None] = {}
    for regel in regels:
        sleutel = normaliseer(regel.materiaal)
        if sleutel not in koppeling:
            koppeling[sleutel] = zoek_materiaal(regel.materiaal, materialen, onthouden)
    return koppeling
