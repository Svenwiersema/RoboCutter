# Module 9 — ERP-integratie

**Status:** 🟡 Kernarchitectuur afgerond — specifieke ERP-koppelingen
volgen zodra Sven een lijst met geschikte ERP-systemen heeft
samengesteld.

## Kernprincipe

- Volgens principe 11 (standalone-first): ERP-koppeling is een
  **optionele laag**, RoboCutter werkt volledig zonder ERP.
- Beschikbaar in **alle edities** (geen editieverschil — zie
  `licentiemodel-en-edities.md` en principe 14). Dit lost de eerder
  openstaande vraag "in welke edities dit beschikbaar is" op.

## Richting van de koppeling (bevestigd)

**Tweerichtingsverkeer**: importeren van klant-/projectgegevens en
materiaalvoorraad vanuit het ERP, en exporteren van zaagplangegevens/
materiaalverbruik/reststukken terug naar het ERP (bv. voor facturatie/
voorraadbijwerking).

## Architectuuraanpak

- Generieke, uitbreidbare koppel-laag (principe 13:
  uitbreidbaarheid boven snelle hacks): een vaste interne
  uitwisselingsindeling, in eerste instantie via bestanden (CSV/Excel)
  als universele basis die altijd werkt, ongeacht of een specifiek ERP
  een API biedt.
- Deze opzet maakt het mogelijk om per ERP later een specifiekere
  koppeling (bv. een directe API) toe te voegen zonder de kern van
  RoboCutter te hoeven aanpassen.

## Prioritering van specifieke ERP's (input van Sven)

- **Express ERP** — eerste prioriteit: heeft zelf geen
  zaagplan-functionaliteit, dus een koppeling met RoboCutter vult hier
  een concreet gat.
- **Borm ERP** — lage prioriteit: heeft al een eigen
  zaagplan-generator, dus minder urgent.
- De technische koppelmogelijkheden van Express ERP (API vs.
  bestandsuitwisseling) konden niet publiek achterhaald worden — dit
  moet rechtstreeks bij de leverancier nagevraagd worden zodra dit
  relevant wordt.

## Openstaande vragen

- Sven stelt zelf een lijst samen van ERP-systemen die goed met
  RoboCutter zouden kunnen samenwerken. De specifieke koppelingen
  (welke data precies, welk technisch mechanisme per ERP) worden verder
  uitgewerkt zodra die lijst er is.
