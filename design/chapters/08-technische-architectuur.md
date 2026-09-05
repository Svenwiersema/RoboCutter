# Module 8 — Technische architectuur & tech stack

**Status:** ✅ Afgerond — met een paar concrete actiepunten die pas bij de
daadwerkelijke implementatie geverifieerd/afgerond kunnen worden (zie
onderaan).

## Platform

**Windows-only** (bevestigd). De meeste klanten (kleine meubel-/
keukenmakers) draaien al Windows naast CNC-/CAD-software. Dit versimpelt
de GUI-keuze, packaging en support flink. De architectuur sluit een
latere cross-platform-uitbreiding niet expliciet uit, maar daar wordt nu
niet actief op ontworpen.

## Taal: Python (bevestigd)

- Voor een solo/klein team veruit het snelst om een functierijke
  desktop-app in te bouwen en te onderhouden, met een grote bestaande
  bibliotheek voor de dingen die RoboCutter nodig heeft (PDF-generatie,
  geometrie, data-import/export).
- De zaagoptimalisatie hoeft niet real-time/frame-based te zijn (een
  berekening per project/model, geen game-loop), dus Python's
  rekensnelheid is voor de meeste projecten geen knelpunt. Mocht een heel
  groot project traag worden, kan dat specifieke onderdeel later alsnog
  versneld worden (bv. Cython of een stuk in Rust) zonder de rest van de
  app te herschrijven.
- Bekend nadeel: Python-apps zijn makkelijker te reverse-engineeren dan
  gecompileerde talen — hier wordt bewust rekening mee gehouden bij de
  keuzes voor bundelen en beveiliging hieronder.

## GUI-framework: PySide6

Qt voor Python, met een LGPL-licentie — geschikt voor closed-source
commerciële software (in tegenstelling tot PyQt, dat GPL of een betaalde
licentie vereist). Native uitstraling op Windows, ondersteunt licht/
donker thema, en heeft de tekenmogelijkheden (QPainter/QGraphicsView)
die nodig zijn voor de zaagplan-visualisatie.

## Bundelen & installer

- **Nuitka** compileert de Python-code naar C/machine-code, wat het een
  stuk lastiger maakt te decompileren dan het gangbaardere PyInstaller
  (dat Python-bytecode grotendeels intact in een zip verpakt) — sluit
  aan bij de wens om het niet te makkelijk te maken voor concurrenten om
  te kopiëren.
- **Inno Setup** voor de installer: gratis, veelgebruikt voor dit soort
  Windows-desktopsoftware, professionele uitstraling, ondersteunt code
  signing.

## Updates

Gekoppeld aan **Keygen** (die toch al gebruikt wordt voor licenties) —
Keygen heeft zelf functionaliteit voor het beheren/uitleveren van
releases en updates, wat een aparte update-server bouwen overbodig
maakt.

> **Actiepunt:** verifiëren of releases/updates in de gratis/self-hosted
> Keygen-laag zitten, of dat dit een hogere (betaalde) Keygen-tier
> vereist — dit weegt mee in de uiteindelijke Keygen-kosten.

## Bescherming tegen kopiëren/kraken

- Nuitka (zie boven) en **code signing** van installer + uitvoerbaar
  bestand — dit voorkomt ook dat Windows het installatiebestand als
  verdacht bestempelt, belangrijk voor een soepele installatie-ervaring.
- De licentie-validatielogica wordt **niet op één plek** in de code
  gezet maar verspreid, en **periodiek herverifieerd** tijdens gebruik in
  plaats van alleen bij het opstarten — dit maakt het patchen van "sla de
  licentiecheck over" een stuk lastiger.
- Realistische verwachting: 100% oncrackbaar bestaat niet, maar dit legt
  de lat voor "even snel kopiëren" flink hoger — voor dit soort
  branchesoftware is dat het realistische doel.

## Database & meerdere werkplekken (bevestigd)

- **Demo/Hobby (1 werkplek):** een lokaal SQLite-bestand, geen netwerk
  nodig.
- **Pro/Enterprise (meerdere gelijktijdige werkplekken):** een
  SQLite-bestand op een netwerkschijf geeft problemen bij gelijktijdig
  schrijven, dus hier draait één pc bij de klant een lichte lokale
  server (wordt gewoon meegeïnstalleerd — de klant hoeft er verder niets
  voor te beheren); de andere werkplekken verbinden daarmee via het
  lokale netwerk. Geen cloud-afhankelijkheid, blijft zo in lijn met het
  "standalone-first"-principe.
- Praktische consequentie voor de klant: bij Pro/Enterprise moet er één
  pc aangewezen worden die aan moet staan zolang andere werkplekken
  willen werken.
- **Toekomstige overweging (bewust geparkeerd, geen besluit):** zodra
  RoboCutter een goedlopend product is, eventueel een cloud-gehoste
  database-optie aanbieden — vermoedelijk (nog) alleen voor Enterprise,
  tegen een hogere prijs. Zie ook hoofdstuk 13 (Toekomstige
  uitbreidingen).

## Licentiehandhaving — technische flow

De voorwaarden (edities, prijzen, Keygen, offline-grace-periode van 3
dagen) staan al vast in hoofdstuk 7. Technisch komt daar het volgende
bij:

- Bij eerste gebruik activeert de klant de licentie in de app (bv. een
  licentiesleutel invoeren); de app valideert dit bij Keygen en slaat een
  **ondertekende** licentiestatus lokaal op.
- Daarna periodieke heartbeats naar Keygen; een werkplek komt vrij zodra
  de heartbeat wegvalt (zie hoofdstuk 7).
- Zonder verbinding blijft de laatst bekende, lokaal opgeslagen en
  ondertekende licentiestatus tot 3 dagen geldig.

## Uitrol van commerciële/licentie-functionaliteit tijdens ontwikkeling

Alle functionaliteit die met de **commerciële/licentie-kant** te maken
heeft — Keygen-validatie, editielimieten (bv. Demo's projectlimiet),
watermerk/logo-restricties, werkplek-telling — wordt tijdens de
ontwikkeling wél gebouwd, maar staat **standaard uit** (bv. via een
eenvoudige feature-flag/config-instelling in de build). Zo kan Sven de
volledige applicatie zonder enige restrictie uitgebreid testen op zijn
eigen werk. Pas nadat dit naar tevredenheid getest is, wordt de
handhaving geactiveerd.

Dit geldt specifiek voor de commerciële/licentielaag — niet voor
functionaliteit in het algemeen.

## Betaalverwerking

**Lemon Squeezy** (voorstel — Paddle is een vergelijkbaar alternatief):
een "merchant of record", wat betekent dat Sven aan Lemon Squeezy
verkoopt en zij aan de klant — zij regelen dan automatisch de
internationale BTW-afdracht. Dat scheelt aanzienlijke administratieve
rompslomp voor een zelfstandige verkoper, tegen iets hogere
transactiekosten (~5%) dan bijvoorbeeld Stripe (~1,5% + €0,25, waarbij
Sven zelf verantwoordelijk zou zijn voor correcte BTW-afdracht per
land).

Lemon Squeezy koppelt via webhooks met Keygen: bij een succesvolle
betaling (eenmalige Hobby-aankoop of een nieuwe Pro/Enterprise-
abonnee) wordt automatisch een Keygen-licentie aangemaakt.

> **Actiepunt:** de Hobby-detectie uit hoofdstuk 7 (meerdere
> Hobby-licenties op dezelfde factuurgegevens/e-mail signaleren) wordt
> hiermee technisch mogelijk: Lemon Squeezy-klantgegevens (e-mail)
> matchen tegen meerdere Hobby-aankopen.

## Openstaande actiepunten (te verifiëren tijdens implementatie)

- Keygen: gratis/self-hosted laag vs. betaalde tier voor releases/
  updates.
- Precieze uitwerking van de licentie-validatielogica (waar in de code,
  hoe vaak herverifiëren).
- Definitieve keuze Lemon Squeezy vs. Paddle (voorlopig Lemon Squeezy).
