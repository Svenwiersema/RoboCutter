# Hoofdstuk 1 — Visie & Scope

**Status:** eerste opzet, gebaseerd op het startgesprek — ter bevestiging

## Kernvisie

RoboCutter is een programma waarmee gebruikers zaagplannen genereren voor het
verzagen van **platen** en **balken** (bijvoorbeeld voor meubel- en
kastenbouw). Naast het genereren van zaagplannen beheert het programma
materialen en reststukken, genereert het labels, en kan het losse "kasten"
samenvoegen tot complete projecten (bijvoorbeeld een nieuwe keuken).

De naam **RoboCutter** komt van "Robo", Svens eigen merk/branding — het
verwijst niet naar het aansturen van een fysieke robot of machine.

## Voor wie

- Primair gericht op vakmensen/bedrijven die platen en balken verzagen (bv.
  keuken- en kastenbouwers).
- Wordt uiteindelijk een **commercieel product** — dus geschikt voor gebruik
  door anderen dan Sven zelf, niet alleen een hobbyproject.
- Moet zowel **standalone** (zonder ERP) als **gekoppeld aan een ERP-systeem**
  kunnen functioneren; de ERP-koppeling is optioneel, nooit een vereiste.

## Kernfunctionaliteit (hoog niveau)

- Zaagplannen genereren voor zowel platen (2D) als balken (1D/lengtemateriaal).
- Automatisch de beste zaagmethode/-volgorde berekenen (optimalisatie).
- Rekening houden met **nerfrichting** van het materiaal bij het genereren van
  zaagplannen.
- Zaagplannen opslaan in een bibliotheek.
- **Reststukken** onthouden, opslaan in een bibliotheek en herbruiken in
  toekomstige zaagplannen.
- **Labels** genereren voor zowel onderdelen als reststukken.
- Een **materiaalbibliotheek** bijhouden.
- **"Kasten"** als herbruikbare bouwstenen opslaan, die samengevoegd kunnen
  worden tot een project (bv. alle kasten voor één keuken → één zaagplan).
- **Projectstatus** bijhouden — nadrukkelijk géén planning/scheduling.
- Optionele koppeling met een **ERP-systeem**.

## Expliciet buiten scope

- Planning/scheduling van projecten (wel status bijhouden, geen agenda/planning).
- (verder aan te vullen naarmate we dieper op de hoofdstukken ingaan)

## Commerciële opzet

- Uiteindelijk **meerdere versies/edities** van het programma.
- **Licentiecontrole**: verifiëren dat een gebruiker het programma legaal
  heeft verkregen.
- Verdere uitwerking (editie-indeling, licentiemechanisme) volgt in
  hoofdstuk 7.

## Werkwijze tijdens het ontwerp

- We werken dit document **hoofdstuk voor hoofdstuk samen** uit voordat er
  gecodeerd wordt.
- Claude denkt actief mee en doet suggesties die bij het programma passen;
  deze worden gemarkeerd als voorstel totdat Sven ze bevestigt (zie
  `checklist.md`).

## Openstaande vragen bij dit hoofdstuk

- Is de doelgroep breder dan platen-/kastenbouw (bv. ook algemene
  meubelmakerij, kozijnenbouw, metaalbewerking), of blijft de eerste versie
  gericht op kastenbouw/keukens?
- Zijn er al concurrerende/vergelijkbare programma's die als referentie
  dienen (bv. bestaande zaagoptimalisatie-software)?
