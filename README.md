# RoboCutter — broncode

Dit is de eerste, echte code van RoboCutter. Voor het ontwerpproces
en alle besluiten die hieraan ten grondslag liggen, zie
[`design/README.md`](design/README.md).

## Wat staat hier (nu)

Als eerste stap is bewust gekozen om **alleen de zaagplan-
optimalisatie-motor** (hoofdstuk 5) te bouwen, als losse, testbare
Python-module — nog zonder UI. Dit is de kern van het product, dus
die moet eerst kloppen voordat er UI overheen komt.

```
src/robocutter/optimalisatie/
    models.py   — datamodellen (Materiaal, Onderdeel, Plaatsing, ...)
    engine.py   — het eigenlijke algoritme (twee strategieën)
tests/
    test_engine.py — pytest-tests voor de kernregels uit hoofdstuk 5
scripts/
    demo_render.py — genereert PNG-voorbeelden ter visuele controle
src/robocutter/ui/
    app.py, main_window.py, theme.py, icons.py, sample_data.py,
    widgets/ — de echte UI (PySide6): de home pagina (Projecten-
    overzicht, voorbeelddata, geen database), de Materialenbibliotheek
    (materialen_page.py), de Reststukkenbibliotheek
    (reststukken_page.py) en de Modellenbibliotheek
    (modellen_page.py), alle drie met echte SQLite-data.
    Werkwijze: eerst een HTML-conceptmockup laten goedkeuren, pas dan
    de PySide6-versie bouwen (zie OVERDRACHT.md) — de
    Reststukkenbibliotheek is hier op Svens verzoek een uitzondering
    op. Klikken op "Projecten"/"Materialenbibliotheek"/
    "Reststukkenbibliotheek"/"Modellenbibliotheek" in de header wisselt
    van pagina; een los projecttabblad staat nog niet gebouwd.
src/robocutter/materialen/
    models.py, bibliotheek.py — de materialenbibliotheek-functie
    (hoofdstuk 3): datamodel, live validatie (incl. zoeken op tekst
    én afmetingen tegelijk) en de archiveer-/verwijderworkflow.
    opslag.py — SQLite-opslag (hoofdstuk 8: Demo/Hobby = één lokaal
    bestand). Nog geen multi-gebruiker-/netwerkopslag.
src/robocutter/reststukken/
    models.py, bibliotheek.py — de reststukkenbibliotheek-functie
    (hoofdstuk 3): een reststuk verwijst naar zijn materiaal
    (materiaal_id) i.p.v. kerf/nerfrichting/type/familie te
    dupliceren, en heeft een beschikbaar/gebruikt-workflow (geen
    archiveerstap, anders dan bij materialen).
    opslag.py — SQLite-opslag, eigen tabel in hetzelfde
    data/robocutter.db-bestand als de materialenbibliotheek.
src/robocutter/modellen/
    models.py, bibliotheek.py — de modellenbibliotheek-functie
    (hoofdstuk 2): een model bestaat uit onderdelen (elk met een eigen
    materiaalkeuze via materiaal_id) en/of andere modellen (nesting,
    met bescherming tegen cirkelverwijzingen).
    opslag.py — SQLite-opslag, eigen tabel in hetzelfde
    data/robocutter.db-bestand.
tests/
    test_materialen.py, test_reststukken.py, test_modellen.py —
    pytest-tests voor de drie bibliotheken.
scripts/
    test_materialen_ui.py, test_reststukken_ui.py, test_modellen_ui.py
    — ruwe, ongestylede PySide6 test-ui's, apart van de echte
    schermen, om de bibliotheek-functies te proberen tijdens het
    bouwen. Slaan op in data/materialen_test.db, data/reststukken_test.db
    resp. data/modellen_test.db (lokaal, .gitignore'd) — de echte
    Materialenbibliotheek-/Reststukkenbibliotheek-pagina's gebruiken
    data/robocutter.db.
```

Belangrijke aannames die in de code staan (zie ook de docstring
bovenaan `engine.py`) en die Sven graag mag controleren:

1. De nerf van een plaat loopt aangenomen altijd langs de lengte-as.
2. Kerf wordt verrekend als extra ruimte tussen onderdelen (niet aan
   de plaatrand).
3. Een groep (vaste volgorde/nerf) wordt behandeld als één blok dat
   niet roteert en verticaal stapelt — de optimizer kiest zelf waar
   dat blok op de plaat komt.
4. Een reststuk telt als "bruikbaar" als **zowel** breedte **als**
   hoogte minstens de ingestelde minimale reststukgrootte zijn.
5. Bij een fabriekskantenband-eis wordt de eerste geschikte
   plaatrand gebruikt (volgorde: links, onder, boven, rechts).
6. De zaagvolgorde-nummering is een eerste, redelijke benadering —
   dit wordt verder verfijnd zodra er meer voorbeelden beoordeeld
   zijn (zoals hoofdstuk 5 ook aangeeft).

## Draaien

```bash
# Eenmalig: dependencies installeren
pip install -e ".[dev]"

# Tests
pytest

# Visuele voorbeelden genereren (output/*.png)
python3 scripts/demo_render.py

# UI starten (PySide6)
pip install -e ".[ui]"
python -m robocutter.ui.app

# Materialen-/reststukken-/modellenbibliotheek-functie los testen (ruwe test-ui's)
python scripts/test_materialen_ui.py
python scripts/test_reststukken_ui.py
python scripts/test_modellen_ui.py
```

Nog niet gedaan (bewust, dit is iteratie 1):
- Mes/groef-plaatsingsregels (hoofdstuk 5 noemt dit zelf nog als
  "verder te detailleren").
- Meerdere platen tegelijk optimaliseren (nu: één plaat per aanroep).
- UI (PySide6): de home pagina, de Materialenbibliotheek, de
  Reststukkenbibliotheek en de Modellenbibliotheek staan er, zie
  `OVERDRACHT.md` voor wat daar nog aan ontbreekt (een los
  projecttabblad, écht meerdere tabbladen tegelijk open).
