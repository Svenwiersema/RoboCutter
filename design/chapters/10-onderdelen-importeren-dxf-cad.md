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
  naar RoboCutter's importformaat vertaalt) — verder te onderzoeken zodra
  dit relevant wordt.
