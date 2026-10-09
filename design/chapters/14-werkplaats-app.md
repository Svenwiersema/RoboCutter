# Module 14 — Werkplaats-app (scannen in de werkplaats)

**Status:** 🟡 Kernkeuzes vastgesteld (2026-10-09), verdere uitwerking
later. **Wordt pas gebouwd tegen het einde van het project**, als de
computer-app (RoboCutter zelf) werkt — Sven: "deze app ontwikkelen komt
pas later in het project tegen het einde als we een werkende computer app
hebben".

## Kernconcept

Een aparte, kleine app voor de mensen in de werkplaats. Die heeft **niet**
alle functionaliteit van RoboCutter, maar alleen wat je bij de zaag en bij
de reststukkenopslag nodig hebt: labels scannen, onderdelen afvinken en
reststukken scannen en aanpassen. Alle ontwerp, zaagplannen genereren,
bibliotheken beheren enz. blijft in RoboCutter op de computer.

Dit haalt de "Mobiele app" uit de geparkeerde ideeën (hoofdstuk 13) terug,
maar in deze beperkte vorm.

## Vastgestelde keuzes

- **Apparaat:** telefoon of tablet; scannen met de **camera** (geen losse
  handscanner nodig).
- **Soort app:** een **echte app** uit de app stores (Android en iOS), geen
  webpagina en geen uitgeklede Windows-versie.
- **Licentie:** werkplaats-apparaten tellen **niet** als werkplek; de app is
  gratis bij elke editie. Past bij het principe "edities verschillen in
  capaciteit/prijs, niet in functionaliteit" (hoofdstuk 7).

## Functies

1. **Onderdeel-label scannen → gezaagd.** Je ziet welk onderdeel het is
   (naam, maat, project, plaat) en vinkt het af als gezaagd; een vergissing
   kun je terugdraaien. Dit is hetzelfde "gezaagd"-vinkje per plaatsing dat
   RoboCutter al heeft (zaagplan bijwerken tijdens productie), dus een
   revisie tijdens productie werkt daarna gewoon met wat in de werkplaats is
   afgevinkt.
2. **Reststuk-label scannen → maat/status aanpassen.** Bijvoorbeeld de maat
   bijstellen nadat er een stuk af is gezaagd, of het reststuk op gebruikt /
   afgeschreven zetten.
3. **Zaagplan per plaat bekijken.** De tekening van een plaat (via een scan
   of uit een lijst), zodat je bij de zaag ziet wat eruit moet en wat al
   gezaagd is. Zelfde weergave als in RoboCutter: y loopt omhoog, onderkant
   van de plaat onderaan.
4. **Reststuk zoeken.** Op materiaal en (minimale) maat zoeken of er een
   passend reststuk op voorraad is.

## Wat er al ligt

- De scancodes op de labels bestaan al en hoeven niet te veranderen:
  `RC:onderdeel:<project>:<materiaal>:<plaat>:<onderdeel>:<n>` voor
  onderdelen en `RC:reststuk:<id>` voor reststukken (die blijft na
  vrijgeven geldig). Zie `projecten/labels.py`.
- Gezaagd per plaatsing (`PlaatZaagplan.gezaagd`) en de
  reststukken-bibliotheken (per project en gedeeld) bestaan al in de
  backend.

## Technische richting (voorstel Claude, nog te bevestigen bij de bouw)

- **Framework:** Flutter (één codebase voor Android en iOS, goede
  QR-/barcodescanners, eigen tekenlaag voor de plaattekening). Python is
  voor een telefoon-app met camerascannen geen goede keuze. Dit wordt dus
  een tweede codebase naast de Python-app.
- **Verbinding:** de app praat over het lokale netwerk (wifi) met
  RoboCutter op de computer. RoboCutter krijgt daarvoor een kleine
  ingebouwde server — het begin van de lokale server uit hoofdstuk 8.
  - De bibliotheken in RoboCutter houden hun data in het geheugen; de
    server moet daarom **binnen het draaiende RoboCutter** lopen en
    dezelfde bibliotheken gebruiken, zodat iets dat in de werkplaats wordt
    afgevinkt meteen op kantoor zichtbaar is (en andersom).
  - Gevolg: de app werkt alleen **zolang RoboCutter op die computer open
    staat** — in lijn met hoofdstuk 8 ("die pc moet aanstaan").
  - Bij Pro/Enterprise (meerdere werkplekken) verbindt de app met de
    lokale server uit hoofdstuk 8; hoe dat precies samenvalt, volgt bij de
    uitwerking van die server.
- **Koppelen:** in de instellingen van RoboCutter staat een QR-code; die
  scan je één keer met de app, daarna weet de app waar RoboCutter te
  vinden is (en heeft hij een sleutel, zodat niet elk apparaat op het
  netwerk zomaar kan schrijven).
- **App stores:** Apple kost €99 per jaar en keurt elke versie; Google
  eenmalig $25. Voor eigen tests kan Android zonder store.
- **Volgorde bij de bouw** (zelfde werkwijze als de rest): eerst de server
  in RoboCutter + tests, dan een HTML-mockup van de app-schermen ter
  goedkeuring, dan de app zelf.

## Openstaande vragen

- **Eerst alleen Android?** Scheelt de Apple-kosten en -keuring tijdens het
  testen.
- **Wifi in de werkplaats:** overal goed genoeg, of moet de app ook zonder
  verbinding kunnen afvinken en later bijwerken? Zonder verbinding werken
  maakt het flink complexer (wat als kantoor intussen een revisie maakte?).
- **Wie heeft het gedaan?** Moet zichtbaar zijn wie iets heeft afgevinkt of
  aangepast (dan heeft elk apparaat/elke persoon een naam nodig), of is dat
  niet nodig? Raakt aan de geparkeerde gebruikersrollen (hoofdstuk 13).
- **Reststuk-statussen in de app:** precies welke overgangen mag de
  werkplaats doen (bv. gebruikt, afgeschreven, maat wijzigen — ook
  vrijgeven, verplaatsen)?
- **Nieuw reststuk vanuit de werkplaats:** moet je in de app ook een nieuw
  reststuk kunnen aanmaken (en dan een label laten printen op kantoor)?
- **Zaagplan "Niet gecontroleerd":** wat toont de app als het zaagplan op
  kantoor niet meer klopt met het project (rode balk, afvinken blokkeren)?
- **Taal:** net als RoboCutter alleen Nederlands?
