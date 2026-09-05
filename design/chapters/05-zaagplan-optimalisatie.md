# Zaagplan-optimalisatie & Zaagplan-lay-out

**Status:** ✅ Afgerond (lay-out wordt later verder verfijnd aan de hand
van gegenereerde voorbeelden — zie onderaan).

## Optimalisatie-instellingen (door de gebruiker configureerbaar)

- **Prioriteit** is instelbaar door de gebruiker: bijvoorbeeld zo min
  mogelijk afval, of een zaagstrategie zoals "lange sneden eerst, daarna
  opdelen in kortere sneden" versus "meest efficiënte plaatsing".
- **Zaagsnede (kerf)** wordt ingesteld **per materiaal** in de
  materialenbibliotheek (Module 3).
- **Randafzagen**: per materiaal instelbaar of er een marge (bv. 5mm) van
  bepaalde randen van de plaat afgezaagd moet worden, en welke randen dat
  betreft.
- **Minimale reststukgrootte**: bepaalt wanneer een stuk als bruikbaar
  reststuk geldt in plaats van als afval — dit wordt **per materiaal**
  ingesteld in de materialenbibliotheek.

## Materiaal-specifieke regels

- **Mes/groef**: de optimizer houdt rekening met de positie van het
  mes/groef-profiel bij het plaatsen en oriënteren van onderdelen (verder
  te detailleren zodra dit technisch wordt uitgewerkt).
- **Kantenband**: per onderdeel geeft de gebruiker in de zaaglijst aan op
  welke rand(en) kantenband nodig is. Dit is niet alleen informatief voor
  de labels, maar **beïnvloedt ook de zaagvolgorde** — vergelijkbaar met
  de fabrieksrand-regel hieronder.
- **Fabrieks-kantenband**: mag nooit worden afgezaagd.
  - Onderdelen die een fabrieksrand nodig hebben, worden er automatisch
    tegenaan geplaatst.
  - De eerste zaagsnede ligt altijd na/onder die rand.
  - De rand blijft zichtbaar op het uiteindelijke onderdeel.
  - De visualisatie van het zaagplan toont welke onderdelen de
    fabrieksrand hebben overgenomen (niet alleen de bronplaat).
- **Nerfrichting** is optioneel — niet elk materiaal heeft een nerf.
  Wanneer een materiaal wel een nerfrichting heeft, kent dit **drie
  opties**: **lange zijde**, **korte zijde**, of **geen** (geen
  nerfrichting van toepassing).

## Groeperen van onderdelen — vaste volgorde voor doorlopende nerf

- De gebruiker kan een aantal onderdelen **binnen hetzelfde model**
  markeren als een groep met een vaste onderlinge volgorde en oriëntatie.
  Voorbeeld: 3 ladefronten die in de kast boven elkaar komen te zitten en
  een nerfrichting hebben — die moeten dan ook in die volgorde onder
  elkaar gezaagd worden, zodat de nerf over de onderdelen heen doorloopt
  (alsof ze uit één stuk gezaagd zijn).
- De optimizer bepaalt nog steeds zelf **waar** zo'n groep op de plaat
  wordt geplaatst; alleen de **onderlinge volgorde/oriëntatie binnen de
  groep** ligt vast — de groep wordt altijd aaneengesloten geplaatst.
  Dit is dus een aanvulling op de normale optimalisatie, geen volledig
  handmatige plaatsing.
- Groepen zijn beperkt tot onderdelen **binnen hetzelfde model** (een
  model is al de kleinste herbruikbare eenheid); ze kunnen niet
  onderdelen uit verschillende modellen binnen een project combineren.
- Dit heeft alleen zin bij een materiaal met een nerfrichting — bij
  materialen zonder nerf is groeperen op deze manier niet nodig.

## Lay-out van het zaagplan-document

Uit een eerder gesprek, hier bevestigd — met de kanttekening dat dit
verder verfijnd wordt zodra we concrete voorbeelden genereren (dan is
gerichte feedback makkelijker te geven):

- De plaat neemt 70–80% van de pagina in beslag; daaronder een
  onderdelentabel over de volledige breedte; onderaan een smalle footer
  met projectgegevens + QR-code. Geen zijpanelen, geen aparte vakken —
  alles draait om de plaat, zodat een operator de pagina op een paar
  meter afstand nog kan lezen.
- **Geen legenda** — de symbolen moeten vanzelf spreken.
- Iconen alleen waar ze iets toevoegen: ✅ op de plaat zelf, ♻ voor een
  herbruikbaar reststuk, 🗑 voor afval — **geen** iconen in de footer,
  die blijft strak en tekstueel (bv. kolommen als Bronmateriaal,
  Materiaal, Formaat, Dikte, Benutting, Nerfrichting, QR).
- **Benutting alleen als percentage** (bv. "89,7%"), niet als m².
- **Zaagsnede-nummering volgt de werkelijke zaagvolgorde**: één volledige
  zaagbeweging = één nummer, geen aparte nummers voor deelsegmenten van
  dezelfde snede.

## Voorbeeld

Twee voorbeeld-zaagplannen (PDF) volgens deze lay-outregels, voor dezelfde
plaat/project maar met een verschillende zaagstrategie — zodat Sven ze kan
vergelijken en gericht feedback kan geven:

- **Variant A — "meest efficiënte plaatsing"**:
  [`../voorbeelden/zaagplan-voorbeeld-v1.pdf`](../voorbeelden/zaagplan-voorbeeld-v1.pdf)
  ([`generate_zaagplan.py`](../voorbeelden/generate_zaagplan.py)). Onderdelen
  worden gemengd horizontaal/verticaal geplaatst ("zigzag") voor een zo hoog
  mogelijke benutting.
- **Variant B — "lange zijdes eerst"**:
  [`../voorbeelden/zaagplan-voorbeeld-v2.pdf`](../voorbeelden/zaagplan-voorbeeld-v2.pdf)
  ([`generate_zaagplan_v2.py`](../voorbeelden/generate_zaagplan_v2.py)). Het
  programma zoekt eerst onderdelen met gelijke breedte/hoogte en groepeert ze
  in volledige-breedte rijen over de lange zijde van de plaat; de eerste
  zaagsneden zijn dan ook de volledige-breedte sneden die de rijen scheiden,
  pas daarna volgen de kortere sneden die een rij in losse onderdelen
  verdelen.

Beide dienen als visuele referentie voor Sven om op te reageren én als basis
voor de latere implementatie.

## Openstaande vragen

- Geen op dit moment voor de functionele/regel-kant. De lay-out wordt
  verder aangescherpt op basis van feedback op het voorbeeld hierboven.
