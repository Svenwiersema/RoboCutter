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
heen-en-weer over deze naamgeving): ``"stroken"`` (vaste, gelijke
strookhoogte i.p.v. de per-rij aangepaste hoogte van ``"rijen"``) en
``"guillotine"`` (uitsluitend doorlopende zaagsnedes van rand tot rand
— een écht apart, strikter algoritme dan ``"efficient"``, ook al
gebruikt ``"efficient"`` zelf al een guillotine-stijl interne
splitsing, zie ``engine.py``). Bewust een tussenstap: eerst de
keuzelijst vastleggen, de motor zelf uitbreiden volgde in een latere
sessie — inmiddels gebeurd, alle vier de waarden hier sturen nu ook
echt een ander plaatsingsalgoritme aan.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["Instellingen", "GELDIGE_THEMAS", "GELDIGE_ZAAGSTRATEGIEEN"]

GELDIGE_THEMAS = ("licht", "donker", "systeem")
GELDIGE_ZAAGSTRATEGIEEN = ("efficient", "rijen", "stroken", "guillotine")


@dataclass
class Instellingen:
    opslag_map: str | None = None  # None = standaardlocatie (<repo>/data)
    thema: str = "licht"
    bedrijfslogo_pad: str | None = None
    standaard_zaagstrategie: str = "efficient"
    werkvoorbereider_naam: str = ""
