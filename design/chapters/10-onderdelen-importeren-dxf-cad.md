# Module 10 — Onderdelen importeren (DXF & Vectorworks)

**Status:** ✅ Kernidee vastgesteld voor de eerste versie (rechthoekige
verwerking); vormgetrouw zagen/nesten van niet-rechthoekige onderdelen is
een bewust geparkeerde toekomstige uitbreiding (zie hoofdstuk 13).

## Kernconcept

Naast handmatig invoeren en CSV/Excel-import (materialen, zie Module 3)
komen er **twee losstaande importmogelijkheden** bij voor onderdelen —
dit voorkomt dubbel werk voor een ontwerper die de onderdelen al ergens
anders getekend heeft:

- **DXF-import** — generiek, werkt met een DXF-bestand ongeacht de
  bron-software.
- **Vectorworks-import** — een aparte, specifieke koppeling met
  Vectorworks (veelgebruikte CAD-software in de branche), **los van** de
  DXF-import.

Deze twee staan dus **los van elkaar**, niet als "DXF, vooral handig
vanuit Vectorworks" — het zijn twee aparte importroutes.

## DXF-import

- Werkt met een DXF-bestand, ongeacht welk programma het gemaakt heeft.
- DXF-tekeningen kunnen ook **niet-rechthoekige** onderdelen bevatten
  (afgeronde hoeken, uitsparingen, schuine kanten).
- In de eerste versie werkt RoboCutter uitsluitend met **rechthoekige**
  onderdelen: bij een niet-rechthoekig onderdeel wordt de **bounding
  box** gebruikt — de grootste breedte- en lengtemaat van de vorm bepaalt
  de rechthoekige afmeting waarmee gezaagd/genest wordt.
- **Vormgetrouw zagen/nesten** van niet-rechthoekige onderdelen (dus
  daadwerkelijk de vorm uit de tekening overnemen in plaats van de
  bounding box) is een bewust geparkeerde toekomstige uitbreiding, omdat
  dit een veel geavanceerdere (2D-vormen) nesting-engine vereist dan de
  huidige rechthoekige zaagoptimalisatie — zie hoofdstuk 13 (Toekomstige
  uitbreidingen).

## Vectorworks-import

- Vectorworks heeft zelf al **zaaglijst-exportmogelijkheden** richting
  bepaalde (andere) programma's.
- Om dit met RoboCutter te laten werken, is vermoedelijk een eigen
  **Vectorworks-plugin** nodig (input van Sven) — dit is losstaand van de
  generieke DXF-import hierboven.
- De bounding-box-regel voor niet-rechthoekige onderdelen (zie hierboven
  bij DXF-import) geldt hier op dezelfde manier.

## RoboCutter-importformaat (bevestigd 2026-11-08)

Afgesproken met Sven: RoboCutter krijgt **één eigen importformaat**. Een
latere Vectorworks-plugin (en eventueel een DXF-omzetter) schrijft dat
formaat, zodat RoboCutter maar één importroute heeft en het slimme werk
(materiaal koppelen, balken herkennen, waarschuwen) in RoboCutter zit.
Het formaat is ook met de hand in Excel in te vullen.

**Bevestigd door Sven:**

- Bestand: **CSV én Excel (.xlsx)**, met dezelfde kolommen. RoboCutter
  levert een leeg Excel-sjabloon mee.
- Bestemming: de kolom **Model** bepaalt het. Bij importeren in een
  project worden regels met dezelfde modelnaam samen één model in het
  project; regels zonder modelnaam worden losse onderdelen. Bij
  importeren in een model worden alle regels onderdeel van dat model.
- Materiaal: herkend op **productcode, anders naam** (hoofdletters en
  spaties tellen niet). Wat niet herkend wordt, koppel je één keer in het
  importscherm, met "bedoelde je…?"-suggesties; RoboCutter onthoudt die
  koppeling voor de volgende import.

**Kolommen (bevestigd 2026-11-08):** eerste regel is de kop, één
onderdeel per regel, maten in mm (komma of punt als decimaalteken).
Kolomnamen maken niet uit voor hoofdletters; de volgorde van de kolommen
is vrij.

| Kolom | Verplicht | Inhoud |
|---|---|---|
| Naam | ja | Naam van het onderdeel, bv. "Zijkant links" |
| Materiaal | ja | Productcode of naam uit de materialenbibliotheek |
| Lengte | ja | mm; horizontaal in de tekening (langs de randen B en O) |
| Breedte | ja, behalve bij een balk | mm; verticaal (langs de randen L en R). Een balk heeft alleen een lengte |
| Aantal | nee (standaard 1) | aantal stuks per model (of totaal bij een los onderdeel) |
| Model | nee | modelnaam; leeg = los onderdeel |
| Modelaantal | nee (standaard 1) | hoe vaak dit model in het project zit; hoort per model gelijk te zijn (anders een waarschuwing). De Vectorworks-plugin vult dit zelf in |
| Nerf | nee | `lang`, `kort` of leeg (= geen eis): welke zijde langs de nerf |
| Kantenband | nee | randen met kantenband: letters `B` (boven), `O` (onder), `L` (links), `R` (rechts), bv. `BO` |
| Fabriekskantenband | nee | `ja` als het onderdeel een fabriekskantenband nodig heeft |
| Groep | nee | groepsnaam (vaste volgorde, doorlopende nerf) |
| Volgorde | nee | plaats binnen de groep |

Sven koos **Lengte × Breedte** (gangbaar in zaaglijsten) i.p.v. de
Breedte × Hoogte van de onderdeelformulieren in de app. Bij het inlezen
wordt Lengte de breedte (x) en Breedte de hoogte (y) van het onderdeel in
RoboCutter, zodat de kantenbandletters op dezelfde randen blijven.

## Waar dit gebruikt wordt

Beide importroutes gelden op dezelfde plekken waar onderdelen voorkomen:

- Bij het samenstellen van onderdelen binnen een **model** (Module 2).
- Bij losse onderdelen binnen een **project** (Module 4).

## Openstaande vragen

- Technische aanpak voor het inlezen van DXF-bestanden (welke
  bibliotheek/aanpak) — hoort bij hoofdstuk 8 (Technische architectuur)
  wanneer dit geïmplementeerd wordt.
- Haalbaarheid en scope van een eigen Vectorworks-plugin (wat Vectorworks
  precies aan zaaglijst-exportdata kan aanleveren, en hoe een plugin dit
  naar het RoboCutter-importformaat hierboven vertaalt) — verder te
  onderzoeken zodra dit relevant wordt.
