# Module 11 — UX/UI

**Status:** ✅ Afgerond — bewust als laatste hoofdstuk besproken, nadat
alle functionele modules (0 t/m 10, 12, 13) al vastlagen.

## Taal

- Interface is in eerste instantie **uitsluitend Nederlands**.
- Architectuur houdt rekening met latere uitbreiding naar andere
  taalpakketten, maar dit is geen v1-vereiste.

## Kleuren

- **Merkaccent**: `#5F7FFF` (blauw) — overgenomen uit Svens eigen
  RoboSten-merk (robosten.nl), gebruikt voor navigatie, koppen en
  knoppen.
- **Licht thema** (standaard): achtergrond `#F2F3F4`, panelen wit.
- **Donker thema** (optioneel, door gebruiker te kiezen): achtergrond
  `#1E2028`, met dezelfde accentkleur `#5F7FFF`.
- **Statuskleuren** (bewust pastelachtig, passend bij de rustige
  accentkleur — geen felle rood/groen/geel):
  - Succes/goed: `#6FCF97`
  - Waarschuwing: `#E8B84B`
  - Kritieke fout: `#E57373`

## Lettertype

- **Inter**, voor een strak en goed leesbaar interface-lettertype.

## UI-architectuur

Kernprincipe (letterlijk zoals geformuleerd tijdens het ontwerp):
**"je kan alleen de tools zien die je kan gebruiken."**

- Een **header bovenin** toont de hoofdonderdelen van het programma:
  Projecten, Materialenbibliotheek, Reststukkenbibliotheek en
  Modellen.
- Klikken op een hoofdonderdeel opent een **tabblad**, in de stijl van
  VS Code — meerdere tabbladen kunnen tegelijk open staan (bijv. een
  project naast de materialenbibliotheek) en de gebruiker kan er
  vrij tussen wisselen.
- Elk open tabblad heeft een **eigen contextuele zijbalk**, die alleen
  de functies/tools toont die binnen dát tabblad bruikbaar zijn (bijv.
  binnen een projecttabblad: Overzicht, Modellen, Zaagplan, Labels,
  Reststukken, Export).
- **Min pop-ups**-principe: status- en waarschuwingsinformatie wordt
  getoond in panelen binnen de pagina zelf, niet in blokkerende
  modale dialogen (sluit aan bij de live-validatie uit Module 3 en
  het "expliciet waarschuwen i.p.v. stil doorgaan"-principe uit
  hoofdstuk 12).

Zie de conceptafbeelding
[`assets/mockups/projectoverzicht-concept.png`](../assets/mockups/projectoverzicht-concept.png)
voor een visuele uitwerking van deze architectuur (projectoverzicht
met open tabbladen, contextuele zijbalk, statusbadges en een
waarschuwingspaneel in plaats van een pop-up). Dit is een concept ter
illustratie van de layout, geen pixel-perfect ontwerp.

## Logo & branding

- Het RoboCutter-logo is gebaseerd op Svens bestaande RoboSten-
  robotmascotte, uitgebreid met een zaagmachine in dezelfde stijl.
- **Twee varianten**, beide definitief vastgesteld:
  - **Met tekst** ("RoboCutter" + tagline) — voor website en
    marketing.
  - **Zonder tekst** — voor zaagplandocumenten en het .exe-icoon.
- Een derde, afgeleide variant voor gebruik **in het programma zelf**:
  een vereenvoudigd icoon (alleen het robotgezicht, zonder machine)
  voor de werkbalk/systemtray, omdat de volledige illustratie bij
  kleine formaten (16–32px) niet meer leesbaar is.
- Bestanden staan in `assets/logo/` (`robocutter_logo_met_tekst.png`,
  `robocutter_logo_zonder_tekst.png`, `robocutter_icon_toolbar.png`).

## Iconen

- **Stijl**: dikke, afgeronde lijnstijl (outline) — sluit qua gewicht
  en vorm aan bij de robotmascotte en het logo (geen dunne
  haarlijntjes, geen volledig gevulde iconen).
- **Bron**: een bestaande open-source icon-set, in plaats van elk
  icoon los laten ontwerpen — sneller, consistent, en dekt direct alle
  benodigde iconen (map, zaag, label, export, materiaal, enzovoort).
  Voorstel: **Phosphor Icons**, gewicht "Bold" — heeft van huis uit
  dikke, afgeronde lijnen in dezelfde geest als het logo, is MIT-
  gelicenseerd (vrij te gebruiken in een commercieel product), en
  heeft met duizenden iconen vrijwel altijd een passende optie.
- **Kleurgebruik**: iconen volgen dezelfde thema-/statuskleuren als de
  rest van de UI (donkere/lichte tekstkleur afhankelijk van het thema,
  accentkleur `#5F7FFF` voor een geselecteerd item in de zijbalk —
  zoals in de conceptmockup).

## Openstaande vragen

- Geen — dit hoofdstuk is inhoudelijk afgerond, inclusief de
  iconenstijl en -bron.
