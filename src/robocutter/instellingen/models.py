"""Datamodel voor de app-brede instellingen. Eén enkel record (geen
lijst/CRUD zoals de bibliotheken) — dit is letterlijk "de instellingen".

``thema`` hergebruikt bewust bestaande stringwaarden uit
``robocutter.ui.theme`` (``LICHT.naam``/``DONKER.naam``) in plaats van
een nieuwe enum te verzinnen voor iets dat al bestaat. ``"systeem"`` is
de uitzondering: geen ``Theme.naam``, maar een aparte waarde die
``robocutter.ui.theme.resolve_thema`` op het moment van toepassen omzet
naar licht/donker op basis van Windows' systeembrede voorkeur.

``standaard_zaagstrategie`` dekte oorspronkelijk 1-op-1
``robocutter.optimalisatie.engine.genereer_zaagplan``'s ``strategie``-
parameter (``"efficient"``/``"rijen"``, destijds de enige twee die de
motor daadwerkelijk uitvoerde). Op Svens verzoek is de keuzelijst hier
aangevuld met veelgebruikte zaagmethode-namen uit de paneelzaag-
praktijk (zie ``_STRATEGIE_LABEL``/``_STRATEGIE_OMSCHRIJVING`` in
``robocutter.ui.instellingen_page``, en OVERDRACHT.md voor de volledige
heen-en-weer over deze naamgeving): ``"guillotine"`` (uitsluitend
doorlopende zaagsnedes van rand tot rand — een écht apart, strikter
algoritme dan ``"efficient"``, ook al gebruikt ``"efficient"`` zelf al
een guillotine-stijl interne splitsing, zie ``engine.py``). Een vierde
optie, ``"stroken"`` (vaste, gelijke strookhoogte i.p.v. de per-rij
aangepaste hoogte van ``"rijen"``), is later weer geschrapt als
zichtbare keuze — Sven zag 'm in de praktijk niet gebruikt worden en
het resultaat verschilt zelden merkbaar van ``"rijen"`` (alleen als
onderdelen sterk in hoogte uiteenlopen). De onderliggende heuristiek
(``engine._pak_stroken``) bestaat nog wél en wordt nog steeds intern
door ``"efficient"`` meegewogen (zie ``_kies_beste_pakresultaat`` in
``engine.py``) — enkel de losse, door de gebruiker kiesbare optie is
weg.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["Instellingen", "GELDIGE_THEMAS", "GELDIGE_ZAAGSTRATEGIEEN", "GELDIGE_LABEL_SCANCODES"]

GELDIGE_THEMAS = ("licht", "donker", "systeem")
GELDIGE_ZAAGSTRATEGIEEN = ("efficient", "rijen", "guillotine")
# Hoofdstuk 6: de scancode-optie (QR/barcode/geen) is "één algemene
# instelling in het programma" — niet iets wat je telkens opnieuw kiest
# bij het printen van een labelvel.
GELDIGE_LABEL_SCANCODES = ("geen", "qr", "barcode")


@dataclass
class Instellingen:
    opslag_map: str | None = None  # None = standaardlocatie (<repo>/data)
    thema: str = "licht"
    bedrijfslogo_pad: str | None = None
    standaard_zaagstrategie: str = "efficient"
    werkvoorbereider_naam: str = ""
    # Hoofdstuk 6 (Labels & identificatie): de optionele labelvelden zijn
    # bewust app-brede instellingen, geen keuze per printactie.
    label_scancode: str = "qr"
    label_kantenband_indicatie: bool = True
    label_nerfrichting_pijl: bool = True
