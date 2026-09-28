# Module 4 — Projecten

**Status:** ✅ Afgerond — dit hoofdstuk was nog niet af bij ChatGPT en is
hier vanaf nul samen ontworpen.

## Kernconcept

- Een project is in essentie een **model** (dezelfde onderliggende
  structuur: een verzameling onderdelen en/of modellen), aangevuld met
  **klantgegevens** en een **voortgangsstatus**.
- Een model bestaat vooral voor efficiëntie/hergebruik — bijvoorbeeld
  omdat een keukenonderkast vaak dezelfde afmetingen heeft, maar in
  verschillend materiaal wordt uitgevoerd. Een project heeft dat niet per
  se nodig: je kunt een project ook volledig opbouwen met losse
  onderdelen, zonder een model te gebruiken.

## Samenstelling

- Een project bevat een lijst van modellen (met aantallen, bv. 3×
  Onderkast 60cm) **én/of** losse onderdelen die rechtstreeks aan het
  project worden toegevoegd via een lijst.
- Bij het toevoegen van een model aan een project wordt een **vaste
  kopie/snapshot** gemaakt — een latere wijziging aan het model in de
  bibliotheek werkt niet automatisch door in het project.
- Er is een expliciete actie om die kopie bij te werken naar de laatste
  modelversie; dit **triggert een nieuwe projectrevisie** (zie Module 1
  voor wat revisie-waardig is).
- **Een modelkopie bewerken vanuit het project** (toegevoegd na
  goedkeuring door Sven, september 2026): de kopie kan in een eigen
  tabblad bewerkt worden (onderdelen wijzigen, toevoegen, verwijderen).
  Die wijzigingen blijven in het project. Daarnaast twee keuzes om ze in
  de modellenbibliotheek te bewaren:
  - **Opslaan in de modellenbibliotheek**: overschrijft het bronmodel
    (met bevestiging). Andere projecten houden hun eigen kopie. Kan niet
    als het bronmodel uit submodellen bestaat: de kopie is platgeslagen,
    dus overschrijven zou die opbouw wissen.
  - **Opslaan als nieuw model**: maakt een nieuw model (zonder
    submodellen); de kopie in het project hoort daarna bij dat nieuwe
    model.
  Dit is een uitbreiding op "Project → Model" hieronder, dat blijft gaan
  over het hele project in één keer; hier gaat het om één model uit het
  project.

## Project → Model

- Een (afgerond) project kan in zijn geheel worden opgeslagen als nieuw
  model — niet gedeeltelijk of een selectie, altijd het **hele project
  in één keer**.
- De revisiegeschiedenis van het project gaat hierbij mee het model in.
- Wil je daarna een deel eruit lichten of aanpassen, dan gebeurt dat in
  de modellenbibliotheek zelf (zie Module 2 — Model-revisies).

## Zaagoptimalisatie op projectniveau

- Alle onderdelen van alle modellen én losse onderdelen in een project
  worden samengevoegd tot **één gecombineerd zaagplan**, voor maximale
  materiaalefficiëntie over het hele project (bv. de hele keuken in één
  keer, niet per kast apart).
- Het zaagplan wordt **opnieuw gegenereerd** zodra de samenstelling van
  het project verandert — zelfde "Niet gecontroleerd"-mechanisme als bij
  Module 1/2.

## Projectstatus

Vier fasen: **Werkvoorbereiding → In productie → Installatie →
Afgerond.**

- Reststukken die het project heeft geproduceerd worden pas
  **definitief** aan de gedeelde reststukkenbibliotheek toegevoegd zodra
  het project "Afgerond" is — tijdens productie of installatie kunnen
  namelijk nog fouten optreden waardoor er alsnog meer gezaagd moet
  worden.

## Archiveren

Zelfde principe als bij Module 3 (Materialen) en zie ook Module 1: een
afgerond project wordt niet verwijderd maar verplaatst naar een
**projectenarchief**. Workflow: Afgerond → Archiveren → Gearchiveerd →
Definitief verwijderen (alleen vanuit het archief).

## Openstaande vragen

Geen op dit moment — dit hoofdstuk is inhoudelijk afgerond.
