"""Materialenbibliotheek: validatie + de archiveer-/verwijderworkflow
uit hoofdstuk 3, met optionele SQLite-opslag (hoofdstuk 8:
Demo/Hobby = één lokaal SQLite-bestand).

Zonder ``db_verbinding`` blijft alles in-memory (handig voor tests).
Met een verbinding (zie ``opslag.open_verbinding``) wordt elke
mutatie ook weggeschreven, en worden bestaande records bij het
aanmaken direct ingeladen.
"""

from __future__ import annotations

import re
import sqlite3
import uuid

from robocutter.materialen import opslag
from robocutter.materialen.models import Materiaal, MateriaalStatus, MateriaalType

_GETAL_TERM = re.compile(r"^\d+([.,]\d+)?$")


class OngeldigeStatusOvergangError(Exception):
    """Bijv. proberen te verwijderen zonder eerst te archiveren."""


def valideer(materiaal: Materiaal) -> list[str]:
    """Live validatie: geeft een lijst foutmeldingen terug (leeg =
    geldig). Bedoeld om direct in het paneel te tonen, geen pop-ups."""

    fouten: list[str] = []

    if not materiaal.naam.strip():
        fouten.append("Naam is verplicht.")
    if materiaal.lengte <= 0:
        fouten.append("Lengte moet groter dan 0 zijn.")
    if materiaal.breedte <= 0:
        fouten.append("Breedte moet groter dan 0 zijn.")
    if materiaal.derde_afmeting <= 0:
        fouten.append(f"{materiaal.derde_afmeting_label} moet groter dan 0 zijn.")
    if materiaal.kerf < 0:
        fouten.append("Kerf/zaagsnede-breedte kan niet negatief zijn.")
    if materiaal.randafzaag_marge < 0:
        fouten.append("Randafzaag-marge kan niet negatief zijn.")
    if materiaal.min_reststukgrootte < 0:
        fouten.append("Minimale reststukgrootte kan niet negatief zijn.")

    return fouten


def _materiaal_matcht_term(materiaal: Materiaal, term: str) -> bool:
    """Eén los getypte zoekterm: een puur getal matcht exact op een van de
    afmetingen/technische maten, andere termen zoeken als losse tekst door
    naam/familie/kleur/productcode/leverancier/tags/type/nerfrichting. Alle
    termen moeten matchen (zie ``lijst``), zodat bv. "multiplex 2800 18"
    de multiplex-platen vindt die 2800 lang of breed zijn én 18 dik."""

    if _GETAL_TERM.match(term):
        getal = float(term.replace(",", "."))
        maten = (
            materiaal.lengte,
            materiaal.breedte,
            materiaal.derde_afmeting,
            materiaal.kerf,
            materiaal.randafzaag_marge,
            materiaal.min_reststukgrootte,
        )
        return any(maat == getal for maat in maten)

    tekstvelden = [
        materiaal.naam,
        materiaal.familie,
        materiaal.kleur_afwerking,
        materiaal.productcode,
        materiaal.leverancier,
        materiaal.type.value,
        materiaal.nerfrichting.value.replace("_", " "),
        *materiaal.tags,
    ]
    return any(term in veld.lower() for veld in tekstvelden)


class MaterialenBibliotheek:
    """Houdt materiaal-records bij en handhaaft de workflow: actief ->
    gearchiveerd -> definitief verwijderd (alleen vanuit gearchiveerd,
    zie hoofdstuk 3)."""

    def __init__(self, db_verbinding: sqlite3.Connection | None = None) -> None:
        self._db = db_verbinding
        self._materialen: dict[str, Materiaal] = {}
        if self._db is not None:
            for materiaal in opslag.laad_alles(self._db):
                self._materialen[materiaal.id] = materiaal

    def toevoegen(self, materiaal: Materiaal) -> Materiaal:
        fouten = valideer(materiaal)
        if fouten:
            raise ValueError("; ".join(fouten))
        if not materiaal.id:
            materiaal.id = uuid.uuid4().hex[:8]
        materiaal.status = MateriaalStatus.ACTIEF
        self._materialen[materiaal.id] = materiaal
        self._persisteer(materiaal)
        return materiaal

    def bijwerken(self, materiaal: Materiaal) -> Materiaal:
        if materiaal.id not in self._materialen:
            raise KeyError(f"Onbekend materiaal-id: {materiaal.id!r}")
        fouten = valideer(materiaal)
        if fouten:
            raise ValueError("; ".join(fouten))
        self._materialen[materiaal.id] = materiaal
        self._persisteer(materiaal)
        return materiaal

    def ophalen(self, materiaal_id: str) -> Materiaal:
        return self._materialen[materiaal_id]

    def archiveren(self, materiaal_id: str) -> Materiaal:
        materiaal = self._materialen[materiaal_id]
        if materiaal.status != MateriaalStatus.ACTIEF:
            raise OngeldigeStatusOvergangError("Alleen actieve materialen kunnen gearchiveerd worden.")
        materiaal.status = MateriaalStatus.GEARCHIVEERD
        self._persisteer(materiaal)
        return materiaal

    def heractiveren(self, materiaal_id: str) -> Materiaal:
        materiaal = self._materialen[materiaal_id]
        if materiaal.status != MateriaalStatus.GEARCHIVEERD:
            raise OngeldigeStatusOvergangError("Alleen gearchiveerde materialen kunnen heractiveerd worden.")
        materiaal.status = MateriaalStatus.ACTIEF
        self._persisteer(materiaal)
        return materiaal

    def verwijderen_definitief(self, materiaal_id: str) -> None:
        materiaal = self._materialen[materiaal_id]
        if materiaal.status != MateriaalStatus.GEARCHIVEERD:
            raise OngeldigeStatusOvergangError(
                "Definitief verwijderen kan alleen vanuit het archief."
            )
        del self._materialen[materiaal_id]
        if self._db is not None:
            opslag.verwijderen(self._db, materiaal_id)

    def _persisteer(self, materiaal: Materiaal) -> None:
        if self._db is not None:
            opslag.opslaan(self._db, materiaal)

    def lijst(
        self,
        status: MateriaalStatus | None = None,
        type_filter: MateriaalType | None = None,
        zoekterm: str = "",
    ) -> list[Materiaal]:
        resultaat = list(self._materialen.values())
        if status is not None:
            resultaat = [m for m in resultaat if m.status == status]
        if type_filter is not None:
            resultaat = [m for m in resultaat if m.type == type_filter]
        termen = zoekterm.lower().split()
        if termen:
            resultaat = [
                m for m in resultaat if all(_materiaal_matcht_term(m, term) for term in termen)
            ]
        return sorted(resultaat, key=lambda m: m.naam.lower())
