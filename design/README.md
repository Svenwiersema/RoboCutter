# RoboCutter — Design Document

Dit is het centrale design document voor RoboCutter. Het wordt hoofdstuk voor
hoofdstuk samen met Sven uitgewerkt, vóórdat er gecodeerd wordt.

## Wat is RoboCutter (kort)

RoboCutter is een programma dat zaagplannen genereert en optimaliseert voor
zowel platen als balken, rekening houdend met nerfrichting. Het beheert een
materiaalbibliotheek en een reststukkenbibliotheek, genereert labels voor
onderdelen en reststukken, en laat gebruikers herbruikbare "kasten"
samenvoegen tot een project (bijvoorbeeld een keuken). Het houdt projectstatus
bij (geen planning), kan optioneel met een ERP-systeem samenwerken maar werkt
ook volledig standalone, en wordt uiteindelijk een commercieel product met
meerdere edities en licentiecontrole.

"Robo" in RoboCutter is Svens eigen merk/branding — geen letterlijke robot.

Zie [chapters/01-visie-en-scope.md](chapters/01-visie-en-scope.md) voor de
volledige uitwerking.

## Hoe we dit document gebruiken

- We werken **hoofdstuk voor hoofdstuk** samen uit, in gesprek — niet alles in
  één keer.
- Claude leest dit document, `principles.md` en `checklist.md` aan het begin
  van elke sessie om consistent te blijven.
- Wijzigingen worden **gericht** doorgevoerd (target edits), nooit een
  volledige herschrijving van een hoofdstuk of document — dit was het
  probleem waar Sven eerder tegenaan liep.
- Bij twijfel of aannames vraagt Claude eerst door in plaats van te gokken.
- Claude denkt actief mee en mag met eigen voorstellen komen; die worden apart
  gemarkeerd (zie `checklist.md`) zodat duidelijk is wat een voorstel is en
  wat een vastgestelde keuze.
- Elk hoofdstuk krijgt een eigen bestand onder `chapters/`, zodat wijzigingen
  aan één hoofdstuk niet het risico lopen het hele document te laten
  herschrijven.

## Hoofdstukken

We gebruiken vanaf nu dezelfde module-indeling als het eerdere gesprek met
ChatGPT (dat scheelt verwarring), aangevuld met een aantal cross-cutting
hoofdstukken. Deze indeling wordt samen bijgesteld naarmate we verder komen.

| # | Hoofdstuk | Status |
|---|-----------|--------|
| 0 | [Visie & Scope](chapters/01-visie-en-scope.md) | ✅ eerste versie klaar |
| 1 | [Module 1 — Projectbeheer](chapters/module-1-projectbeheer.md) | ✅ gevalideerd |
| 2 | [Module 2 — Modellen](chapters/module-2-modellen.md) (incl. "kasten") | ✅ gevalideerd |
| 3 | [Module 3 — Materialen](chapters/module-3-materialen.md) | ✅ gevalideerd |
| 4 | [Module 4 — Projecten](chapters/module-4-projecten.md) (samenstellen uit modellen) | ✅ afgerond |
| 5 | [Zaagplan-optimalisatie & lay-out](chapters/05-zaagplan-optimalisatie.md) | ✅ afgerond |
| 6 | [Labels & identificatie](chapters/06-labels-en-identificatie.md) | ✅ afgerond |
| 7 | [Licentiemodel & commerciële edities](chapters/licentiemodel-en-edities.md) | ✅ afgerond |
| 8 | [Technische architectuur & tech stack](chapters/08-technische-architectuur.md) | ✅ afgerond |
| 9 | [ERP-integratie](chapters/09-erp-integratie.md) | 🟡 kernarchitectuur afgerond |
| 10 | [Onderdelen importeren (DXF & Vectorworks)](chapters/10-onderdelen-importeren-dxf-cad.md) | ✅ kernidee vastgesteld (v1: rechthoekig) |
| 11 | [UX/UI](chapters/11-ux-ui.md) | ✅ afgerond |
| 12 | [Niet-functionele eisen](chapters/12-niet-functionele-eisen.md) | ✅ afgerond |
| 13 | [Toekomstige uitbreidingen / expliciet buiten scope](chapters/13-toekomstige-uitbreidingen.md) | ✅ afgerond |

Let op de begripsverwarring die we hebben rechtgezet: een **model** is een
los, herbruikbaar ontwerp (dit is ook waar een "kast" onder valt) en mag
andere modellen bevatten; een **project** is het klantwerk zelf, met
revisies, één klant/contactpersoon en een start-/opleverdatum, maar zonder
planning.

Zie [checklist.md](checklist.md) voor de actuele status per onderwerp.
