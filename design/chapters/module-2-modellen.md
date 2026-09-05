# Module 2 — Modellen

**Status:** ✅ Afgerond — oorspronkelijk uitgewerkt in een eerder gesprek,
hier opnieuw doorgenomen en bevestigd.

## Kernconcept

- Eén centrale modellenbibliotheek voor alle modellen.
- Modellen mogen **andere modellen bevatten** (nesting) — dit is ook waar
  een "kast" onder valt: een kast is een model, en een model kan op zijn
  beurt weer uit andere modellen zijn opgebouwd.
- Vrije mappenstructuur + tags, met uniform zoeken/filteren door de hele
  bibliotheek.
- Materiaal is een aparte sectie binnen een model.

## Dupliceren

- Dupliceren maakt een volledig nieuw, **zelfstandig** model — geen
  gedeelde/gekoppelde afhankelijkheid met het origineel.

## Model-revisies

- Modellen hebben, net als projecten (Module 1), een revisiegeschiedenis
  (Rev A, Rev B, ...), altijd **handmatig** aangemaakt — nooit
  automatisch.
- Wat revisie-waardig is, volgt dezelfde regel als bij projecten (zie
  Module 1): een wijziging op verzoek van de klant (bv. een kast
  toevoegen/verwijderen/aanpassen) is revisie-waardig; het corrigeren van
  een fout uit de werkvoorbereiding niet.
- Wanneer een project wordt opgeslagen als nieuw model (zie Module 4),
  gaat de revisiegeschiedenis van dat project mee het model in.

## Documentstatus

- Werktekeningen (en, zoals vastgesteld in Module 1, ook gegenereerde
  zaagplannen en labels) krijgen automatisch de status **"Niet
  gecontroleerd"** zodra er een relevante wijziging plaatsvindt in het
  onderliggende model. Ze worden pas opnieuw gegenereerd zodra ze weer
  worden opgevraagd/geëxporteerd.
- Waarschuwingen hierover verschijnen op drie plekken: in de software
  zelf, bij export, én als watermerk op de PDF — een gelaagde
  veiligheidsmaatregel zodat een verouderd document nooit onopgemerkt
  gebruikt wordt.

## Instellingen

- Veilige standaardinstellingen (safe defaults) voor beginners, met
  uitgebreide configuratiemogelijkheden voor gevorderde gebruikers — dit
  sluit aan bij het principe "makkelijk op te pakken, maar met diepgang"
  (zie `principles.md`).

## Openstaande vragen

- Geen op dit moment — dit hoofdstuk is inhoudelijk afgerond. Preciezere
  details over hoe modellen technisch samenhangen met projecten (Module
  4) volgen wanneer we daar zijn.
