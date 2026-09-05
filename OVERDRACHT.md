# Overdracht — van ontwerp (Cowork) naar bouwen (Claude Code)

Dit bestand is voor een Claude Code-sessie die het bouwen van
RoboCutter oppakt, na een uitgebreid ontwerptraject dat in een Cowork-
sessie is doorlopen. Lees dit eerst, samen met
[`design/README.md`](design/README.md) en
[`design/checklist.md`](design/checklist.md) — dat zijn de
bronwaarheid voor alle productbeslissingen.

## Status

- **Ontwerp (hoofdstuk 0 t/m 13): volledig afgerond.** Elk hoofdstuk
  staat in `design/chapters/`, met een samenvatting per module in
  `design/checklist.md`. Enige uitzondering: hoofdstuk 9
  (ERP-integratie) staat bewust op 🟡 — Sven stelt zelf nog een lijst
  samen van geschikte ERP-systemen; dit hoofdstuk mag voorlopig
  blijven liggen.
- **Logo & branding**: definitief vastgesteld, bestanden in
  `design/assets/logo/` (met tekst, zonder tekst, werkbalk-icoon).
- **Code**: de eerste echte module is gebouwd:
  `src/robocutter/optimalisatie/` — de zaagplan-optimalisatie-motor
  (hoofdstuk 5), los van de UI, met een volledige pytest-suite
  (`tests/test_engine.py`, 14 tests, allemaal groen) en
  visuele voorbeelden (`scripts/demo_render.py` → `output/*.png`).
  Zie `README.md` in de repo-root voor hoe je dit draait.
- **Werkwijze UI (nieuw, vastgesteld):** voor élk UI-scherm eerst een
  HTML-conceptmockup (Artifact) bouwen en laten goedkeuren door Sven,
  pas daarna de echte PySide6-implementatie maken. Niet meer direct in
  PySide6 beginnen.
- **UI — eerste scherm gebouwd:** de home pagina (Projecten-overzicht,
  de landingspagina van de hele app) is uitgewerkt volgens deze
  werkwijze: eerst een goedgekeurde HTML-mockup, daarna
  `src/robocutter/ui/` (PySide6) — header met de vier hoofdonderdelen,
  VS Code-stijl tabbalk, contextuele zijbalk, KPI-tegels, project-
  kaarten met statuschips/voortgangsbalk, inline waarschuwingspaneel
  (geen pop-up), licht/donker thema-toggle. Draait via
  `python -m robocutter.ui.app` (dependency: `pip install -e ".[ui]"`).
  Gebruikt vaste voorbeeldprojecten uit `src/robocutter/ui/sample_data.py`
  — nog geen echte database-koppeling (Module 1/4 backend bestaat nog
  niet). Iconen zijn handgetekende SVG's in Phosphor Bold-stijl
  (`src/robocutter/ui/icons.py`) — Phosphor's eigen bestand kon niet via
  een toegestane bron ingeladen worden voor de HTML-mockup, dus is
  dezelfde aanpak in PySide6 aangehouden voor visuele consistentie.
  Inter (het vastgestelde lettertype) is nog niet als font-bestand
  gebundeld; de UI valt voorlopig terug op Segoe UI.
  Nog te doen voor de UI: de overige hoofdonderdelen
  (Materialenbibliotheek, Reststukkenbibliotheek, Modellen), een los
  projecttabblad (met de zijbalk uit `assets/mockups/projectoverzicht-
  concept.png`), écht meerdere tabbladen tegelijk open, en het
  bundelen van Inter.

## Aannames in de code die Sven nog moet bevestigen

Deze staan ook als docstring bovenaan `engine.py`, maar zijn
belangrijk genoeg om hier te herhalen — vraag Sven hiernaar voordat je
er verder op bouwt, in lijn met zijn voorkeur om bij twijfel te vragen
in plaats van aan te nemen:

1. De nerf van een plaat loopt aangenomen altijd langs de lengte-as
   (x-as). Nog niet expliciet zo benoemd in hoofdstuk 5.
2. Kerf wordt verrekend als extra ruimte tussen onderdelen (niet aan
   de plaatrand) — een gangbare aanpak, maar wel een keuze.
3. Een groep (vaste volgorde/nerf, hoofdstuk 5) wordt behandeld als
   één blok dat niet roteert en verticaal stapelt.
4. Een reststuk telt als "bruikbaar" als **zowel** breedte **als**
   hoogte minstens de ingestelde minimale reststukgrootte zijn
   (i.p.v. bijvoorbeeld oppervlakte).
5. Bij een fabriekskantenband-eis wordt de eerste geschikte plaatrand
   gebruikt, in de volgorde links → onder → boven → rechts.
6. De zaagvolgorde-nummering voor de "efficient"-strategie is een
   eerste benadering — hoofdstuk 5 zelf zegt al dat de lay-out verder
   verfijnd wordt aan de hand van gegenereerde voorbeelden.

## Nog niet gebouwd (bewust, dit was iteratie 1)

- Mes/groef-plaatsingsregels (hoofdstuk 5 noemt dit zelf nog als
  "verder te detailleren").
- Meerdere platen tegelijk optimaliseren (nu: één plaat per aanroep;
  er is nog geen logica die onderdelen over meerdere platen van
  hetzelfde materiaal verdeelt).
- Projecten/modellen/materialen-beheer (Modules 1-4) als echte,
  werkende functionaliteit — er is alleen een UI-schil met
  voorbeelddata (zie hierboven), geen database/opslag.
- Labels (hoofdstuk 6), DXF/Vectorworks-import (hoofdstuk 10),
  ERP-koppeling (hoofdstuk 9), licentie/commerciële laag
  (hoofdstuk 7-8).
- De rest van de UI (PySide6, hoofdstuk 11): alleen de home pagina
  (Projecten-overzicht) staat er, zie hierboven voor wat daar nog
  ontbreekt.

## Technische kaders om aan te houden (hoofdstuk 8)

- Windows-only, Python, **PySide6** voor de GUI.
- Bundelen met **Nuitka**, installer met **Inno Setup**, updates via
  **Keygen**.
- Database: SQLite lokaal voor Demo/Hobby; één lokale
  netwerk-server-pc voor Pro/Enterprise (geen cloud-afhankelijkheid
  in v1).
- **Belangrijk**: alle commerciële/licentie-functionaliteit (Keygen-
  validatie, editielimieten, watermerk/logo-restricties, werkplek-
  telling) mag gebouwd worden, maar moet **standaard uit staan**
  zolang Sven de app nog zelf test op zijn eigen werk. Dit geldt
  alleen voor de commerciële laag, niet voor functionaliteit in het
  algemeen.

## Suggestie voor een logische volgende stap

Sven heeft gekozen om eerst met de UI door te gaan (zie de
werkwijze hierboven). Logische vervolgstappen, in overleg met Sven te
bepalen: het volgende hoofdonderdeel als HTML-mockup uitwerken
(Materialenbibliotheek, Reststukkenbibliotheek, of Modellen), of het
losse projecttabblad (zie `assets/mockups/projectoverzicht-
concept.png`) — zelfde werkwijze: eerst mockup, dan pas PySide6.
Los daarvan staat de optimalisatie-motor (mes/groef, meerdere platen)
nog open, maar is niet gekozen als volgende stap.

## Werkwijze die Sven prettig vindt

- Bij ambiguïteit of ruimte voor aannames: **eerst vragen, niet
  gokken** — vooral belangrijk bij technisch werk met echte
  consequenties.
- Gerichte wijzigingen in plaats van herschrijvingen.
- Nieuwe functies mogen gebouwd worden met de commerciële laag uit
  (zie hierboven), zodat hij zelf onbeperkt kan testen.
