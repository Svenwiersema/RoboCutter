"""Reststukkenbibliotheek: validatie + de beschikbaar/gebruikt-workflow
uit hoofdstuk 3, met optionele SQLite-opslag.

Een reststuk hoort altijd bij een bestaand materiaal uit de
materialenbibliotheek (``materiaal_id``) — vandaar dat deze klasse een
``MaterialenBibliotheek`` nodig heeft: om te valideren dat het
gekoppelde materiaal bestaat, en om platen/balken-type, familie,
kleur, tags e.d. te kunnen filteren/doorzoeken (die staan niet op het
reststuk zelf, zie ``models.py``).
"""

from __future__ import annotations

import re
import sqlite3
import uuid

from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.materialen.models import Materiaal, MateriaalType
from robocutter.reststukken import opslag
from robocutter.reststukken.models import Reststuk, ReststukStatus

_GETAL_TERM = re.compile(r"^\d+([.,]\d+)?$")


class OngeldigeStatusOvergangError(Exception):
    """Bijv. een al gebruikt reststuk nogmaals als gebruikt markeren."""


class OnbekendMateriaalError(Exception):
    """Het materiaal waar dit reststuk naar verwijst bestaat niet (meer)."""


def valideer(reststuk: Reststuk, materialen: MaterialenBibliotheek) -> list[str]:
    """Live validatie: geeft een lijst foutmeldingen terug (leeg =
    geldig). Bedoeld om direct in het paneel te tonen, geen pop-ups
    (zelfde principe als bij de materialenbibliotheek, hoofdstuk 3)."""

    fouten: list[str] = []

    if not reststuk.materiaal_id:
        fouten.append("Materiaal is verplicht.")
    else:
        try:
            materialen.ophalen(reststuk.materiaal_id)
        except KeyError:
            fouten.append("Gekoppeld materiaal bestaat niet (meer).")
    if reststuk.lengte <= 0:
        fouten.append("Lengte moet groter dan 0 zijn.")
    if reststuk.breedte <= 0:
        fouten.append("Breedte moet groter dan 0 zijn.")

    return fouten


def _reststuk_matcht_term(reststuk: Reststuk, materiaal: Materiaal, term: str) -> bool:
    if _GETAL_TERM.match(term):
        getal = float(term.replace(",", "."))
        maten = (reststuk.lengte, reststuk.breedte, materiaal.derde_afmeting)
        return any(maat == getal for maat in maten)

    tekstvelden = [
        materiaal.naam,
        materiaal.familie,
        materiaal.kleur_afwerking,
        materiaal.type.value,
        reststuk.herkomst_project,
        reststuk.herkomst_model,
        *materiaal.tags,
    ]
    return any(term in veld.lower() for veld in tekstvelden)


class ReststukkenBibliotheek:
    """Houdt reststuk-records bij en handhaaft de workflow: beschikbaar
    <-> gebruikt (hoofdstuk 3 noemt geen archiveerstap voor reststukken,
    dus definitief verwijderen kan direct)."""

    def __init__(self, materialen: MaterialenBibliotheek, db_verbinding: sqlite3.Connection | None = None) -> None:
        self._materialen = materialen
        self._db = db_verbinding
        self._reststukken: dict[str, Reststuk] = {}
        if self._db is not None:
            for reststuk in opslag.laad_alles(self._db):
                self._reststukken[reststuk.id] = reststuk

    def toevoegen(self, reststuk: Reststuk) -> Reststuk:
        fouten = valideer(reststuk, self._materialen)
        if fouten:
            raise ValueError("; ".join(fouten))
        if not reststuk.id:
            reststuk.id = uuid.uuid4().hex[:8]
        reststuk.status = ReststukStatus.BESCHIKBAAR
        self._reststukken[reststuk.id] = reststuk
        self._persisteer(reststuk)
        return reststuk

    def bijwerken(self, reststuk: Reststuk) -> Reststuk:
        if reststuk.id not in self._reststukken:
            raise KeyError(f"Onbekend reststuk-id: {reststuk.id!r}")
        fouten = valideer(reststuk, self._materialen)
        if fouten:
            raise ValueError("; ".join(fouten))
        self._reststukken[reststuk.id] = reststuk
        self._persisteer(reststuk)
        return reststuk

    def ophalen(self, reststuk_id: str) -> Reststuk:
        return self._reststukken[reststuk_id]

    def materiaal_van(self, reststuk: Reststuk) -> Materiaal:
        try:
            return self._materialen.ophalen(reststuk.materiaal_id)
        except KeyError as exc:
            raise OnbekendMateriaalError(
                f"Materiaal {reststuk.materiaal_id!r} bestaat niet (meer)."
            ) from exc

    def markeer_gebruikt(self, reststuk_id: str) -> Reststuk:
        reststuk = self._reststukken[reststuk_id]
        if reststuk.status != ReststukStatus.BESCHIKBAAR:
            raise OngeldigeStatusOvergangError("Alleen beschikbare reststukken kunnen als gebruikt gemarkeerd worden.")
        reststuk.status = ReststukStatus.GEBRUIKT
        self._persisteer(reststuk)
        return reststuk

    def zet_beschikbaar(self, reststuk_id: str) -> Reststuk:
        reststuk = self._reststukken[reststuk_id]
        if reststuk.status != ReststukStatus.GEBRUIKT:
            raise OngeldigeStatusOvergangError("Alleen gebruikte reststukken kunnen weer beschikbaar gezet worden.")
        reststuk.status = ReststukStatus.BESCHIKBAAR
        self._persisteer(reststuk)
        return reststuk

    def verwijderen(self, reststuk_id: str) -> None:
        del self._reststukken[reststuk_id]
        if self._db is not None:
            opslag.verwijderen(self._db, reststuk_id)

    def _persisteer(self, reststuk: Reststuk) -> None:
        if self._db is not None:
            opslag.opslaan(self._db, reststuk)

    def lijst(
        self,
        status: ReststukStatus | None = None,
        type_filter: MateriaalType | None = None,
        zoekterm: str = "",
    ) -> list[Reststuk]:
        resultaat = list(self._reststukken.values())
        if status is not None:
            resultaat = [r for r in resultaat if r.status == status]
        if type_filter is not None:
            resultaat = [r for r in resultaat if self.materiaal_van(r).type == type_filter]
        termen = zoekterm.lower().split()
        if termen:
            resultaat = [
                r
                for r in resultaat
                if all(_reststuk_matcht_term(r, self.materiaal_van(r), term) for term in termen)
            ]
        return sorted(resultaat, key=lambda r: self.materiaal_van(r).naam.lower())
