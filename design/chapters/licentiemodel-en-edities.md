# Licentiemodel & Commerciële Edities

**Status:** ✅ Afgerond

## Kernprincipe

Edities verschillen in **capaciteit en prijs**, niet in **functionaliteit**.
Op de projectlimiet van Demo na (bewust beperkt om te testen) heeft elke
editie dezelfde volledige functieset, inclusief de optionele ERP-koppeling
— nooit een functie die achter een hoger plan verstopt zit. (Zie ook
`principles.md`.)

## Edities

Vier edities: **Demo**, **Hobby**, **Pro**, **Enterprise**.

### Demo — gratis

- **Permanent gratis** (geen proefperiode, geen verlopen).
- Harde limiet: **maximaal 5 projecten**.
- Verder dezelfde functionaliteit als de andere edities (incl. optionele
  ERP-koppeling).
- Kleine tekst onderin de zaagplan-PDF (bv. "gemaakt met Demo-versie").
- Geen eigen bedrijfslogo — toont het RoboCutter-logo.
- 1 werkplek (bevestigd, net als Hobby).

### Hobby — €79 eenmalig

- Doelgroep: hobbyisten en zzp'ers.
- 1 werkplek.
- **Eenmalige betaling van €79** (geen abonnement).
- Eigen bedrijfslogo toegestaan, geen kleine tekst onderin de PDF, geen
  projectlimiet.
- **Persoonlijke licentie (bevestigd):** Hobby is gebonden aan één
  individu/zzp'er voor eigen gebruik, niet bedoeld om een bedrijf met
  meerdere medewerkers mee te bemannen — ongeacht hoeveel losse
  Hobby-licenties daarvoor gekocht worden. Zodra een bedrijf meer dan één
  persoon toegang wil geven, is Pro verplicht. Dit voorkomt dat het
  goedkoper is om bijvoorbeeld 3× Hobby te kopen dan een Pro-abonnement
  (dat zou bij de huidige prijzen anders wél het geval zijn: 3×€79 = €237
  eenmalig tegenover €29×12 = €348 per jaar). Dit staat in de
  licentievoorwaarden; het is geen functieverschil (zie kernprincipe) en
  ook geen waterdichte technische blokkade, maar maakt het overtreden
  ervan een contractbreuk in plaats van een slimme besparing.
- **Actiepunt voor technische architectuur:** Keygen kan bijhouden of
  dezelfde factuurgegevens/e-mail meerdere Hobby-licenties aanschaft, als
  signaal om iemand actief door te verwijzen naar Pro (optionele
  technische rugdekking bij de voorwaarden hierboven).

### Pro — €29 / maand

- Doelgroep: kleine bedrijven met 1 à 2 tekenaars.
- Abonnement, **€29 per maand** (bevestigd).
- **Max. 3 gelijktijdige werkplekken — bevestigd.**
- Eigen bedrijfslogo toegestaan, volledige functionaliteit.

### Enterprise — abonnement, op aanvraag

- Doelgroep: grote bedrijven.
- Abonnement; aantal werkplekken op aanvraag / instelbaar per licentie.
- Prijs schaalt mee met het aantal gebruikers, tot een **maximumprijs van
  €150/maand** (bevestigd als plafond — hoeft niet geadverteerd te
  worden, dit is een op-aanvraag-traject).
- **Schaalschema (bevestigd):** €10 per werkplek per maand, tot het
  maximum van €150/maand — dat plafond wordt bereikt vanaf 15
  werkplekken, waarna extra werkplekken niets meer kosten.
- Eigen bedrijfslogo toegestaan, volledige functionaliteit.

## Wat is een "werkplek"? (bevestigd)

- Een werkplek = een gelijktijdig actieve gebruiker/account, geen
  installatie. Onbeperkt installeren op meerdere computers is toegestaan;
  alleen het aantal gelijktijdig actieve gebruikers wordt geteld en
  beperkt.

## Handhaving — Keygen (bevestigd)

- Licentiehandhaving via [Keygen](https://keygen.sh/pricing/): floating/
  concurrent licenties met offline-ondersteuning.
- Start op de gratis tier (tot 100 actieve licenties) of de zelf te
  hosten open-source variant (Keygen CE) — geen eigen licentieserver
  bouwen, geen verplichte doorlopende cloudkosten in het begin.
- Werking: de app checkt in bij het inloggen en stuurt daarna periodiek
  een heartbeat; een werkplek komt vrij zodra de heartbeat wegvalt.
  Zonder internetverbinding blijft de software nog **3 dagen** bruikbaar
  op de laatst bekende, lokaal opgeslagen licentiestatus
  (offline-grace-periode), daarna moet hij weer even online komen.

## Openstaande vragen

Geen — dit hoofdstuk is afgerond.
