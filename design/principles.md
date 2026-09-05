# RoboCutter — Design Principles

**Status:** eerste concept — ter review en aanvulling door Sven.

Deze principes zijn richtlijnen waar we tijdens het ontwerp (en later de
bouw) van RoboCutter rekening mee houden. Ze worden samen bijgesteld
naarmate we meer hoofdstukken uitwerken.

## Proces-principes (hoe we samenwerken)

1. **Het design document is de bron van waarheid.** Wijzigingen worden
   gericht doorgevoerd; er wordt nooit een heel hoofdstuk of document in
   zijn geheel herschreven voor een kleine wijziging. (Dit was het probleem
   met de vorige aanpak in ChatGPT.)
2. **Vraag bij twijfel, neem geen aannames.** Als iets niet duidelijk is of
   er ruimte is voor interpretatie, wordt dit expliciet besproken voordat
   het wordt vastgelegd — zeker bij zaken met praktische consequenties
   (zoals berekeningen, materiaalgebruik, licentielogica).
3. **Hoofdstuk voor hoofdstuk.** Het functionele ontwerp wordt afgerond
   vóórdat er gecodeerd wordt; we springen niet vooruit naar implementatie
   voordat een hoofdstuk voldoende is uitgewerkt.
4. **Suggesties zijn gemarkeerd, geen besluiten.** Claude mag actief
   meedenken en voorstellen doen, maar deze worden apart aangemerkt
   (checklist) totdat Sven ze bevestigt.

## Domeinprincipes (specifiek voor RoboCutter)

5. **Platen én balken zijn gelijkwaardig.** Het domeinmodel en de
   optimalisatie-engine ondersteunen vanaf het begin zowel 2D-materiaal
   (platen) als 1D-materiaal (balken) — niet als latere toevoeging.
6. **Nerfrichting en zaagsnede zijn nooit optioneel.** Elke
   optimalisatieberekening houdt rekening met materiaaleigenschappen zoals
   nerfrichting en zaagsnede-breedte; dit is fundamenteel voor de
   betrouwbaarheid van een zaagplan.
7. **Reststukken zijn eersteklas objecten.** Reststukken worden niet
   weggegooid uit het model maar behandeld als herbruikbare
   bibliotheekitems, met dezelfde traceerbaarheid als nieuw materiaal.
8. **Herbruikbare bouwstenen.** "Kasten" worden los ontworpen en opgeslagen,
   en kunnen worden samengevoegd tot projecten; het domeinmodel ondersteunt
   deze compositie native.
9. **Traceerbaarheid via labels.** Elk onderdeel en reststuk is eenduidig
   identificeerbaar via een label, gekoppeld aan project en bibliotheek.
10. **Status, geen planning.** RoboCutter houdt bij in welke staat een
    project zich bevindt, maar bemoeit zich expliciet niet met planning of
    agendabeheer — dit voorkomt functiecreep richting projectmanagement-
    software.
11. **Standalone-first, ERP als optionele laag.** De applicatie is volledig
    functioneel zonder ERP-koppeling; ERP-integratie is een opt-in
    uitbreiding, nooit een harde afhankelijkheid.

## Architectuurprincipes (met het oog op een commercieel product)

12. **Licentie- en editiebewust vanaf dag 1.** Het onderscheid tussen
    versies/edities en licentievalidatie wordt vanaf het begin in de
    architectuur meegenomen, niet achteraf erin geforceerd.
13. **Uitbreidbaarheid boven snelle hacks.** Waar een keuze zowel snel-en-
    hardcoded als iets meer werk maar uitbreidbaar kan, kiezen we voor
    uitbreidbaar zodra dit past bij een programma dat voor meerdere klanten
    bedoeld is.
14. **Edities verschillen in capaciteit en prijs, niet in functionaliteit.**
    Op de gratis Demo-editie na (die bewust beperkt is om te testen) hebben
    alle edities dezelfde volledige functieset. Upgraden gaat om meer
    werkplekken/capaciteit, nooit om functies vrij te schakelen die eerder
    verstopt zaten — dit is een expliciete, principiële keuze van Sven.

---

*Openstaande vraag: klopt deze lijst, mist er iets, en zijn er principes die
juist geschrapt of afgezwakt moeten worden? Zie ook `checklist.md`.*
