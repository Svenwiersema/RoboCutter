# Module 12 — Niet-functionele eisen

**Status:** ✅ Afgerond.

## Platform

**Windows 10 én 11** (bevestigd) — breder bereik dan alleen Windows 11,
omdat sommige werkplaatsen nog wat oudere pc's draaien. (De platformkeuze
zelf — Windows-only, geen macOS/Linux — staat al vast in hoofdstuk 8.)

## Prestaties

- Ter referentie: een complete keuken bestaat uit ongeveer **100–150**
  losse onderdelen (panelen, deuren, laden, planken, etc.).
- RoboCutter moet soepel werken tot pakweg **500 onderdelen** in één
  project — ruim boven een enkele keuken, zodat ook een combinatie van
  meerdere keukens of een groot maatwerkproject geen probleem vormt.
- Mocht een project daar ver overheen gaan en de zaagoptimalisatie
  merkbaar traag worden, dan geldt de eerder afgesproken aanpak
  (hoofdstuk 8): dat specifieke onderdeel later versnellen (bv. Cython
  of een stuk in Rust) zonder de rest van de applicatie te herschrijven.

## Betrouwbaarheid

- **Auto-save/crash-herstel**: werk mag nooit verloren gaan bij een
  crash.
- Bij twijfel of een randgeval (bv. onvoldoende materiaal, een
  onmogelijke maat) **waarschuwt** het programma expliciet in plaats van
  stilzwijgend een mogelijk onjuist zaagplan te genereren — zelfde geest
  als principe 6 (nerfrichting/zaagsnede nooit optioneel).
- Bij een wegvallende verbinding met de lokale server (meerdere
  werkplekken, zie hoofdstuk 8) mag dit nooit tot corrupte of verloren
  data leiden.
- **Automatische periodieke back-up van de lokale database** (bevestigd
  als concrete v1-functie, geen toekomstige uitbreiding): omdat bij Pro/
  Enterprise alle bedrijfsdata op één pc staat (de lokale server, zie
  hoofdstuk 8), is dataverlies bij een schijfstoring een reëel risico
  dat niet moet wachten op een latere versie.

## Offline-gebruik

- Kernfunctionaliteit (zaagplan genereren, modellen/projecten/materialen
  beheren) werkt volledig offline — sluit aan bij het
  "standalone-first"-principe.
- Enige internetafhankelijkheid: de licentie-heartbeat (met de al
  afgesproken 3-dagen offline-grace, hoofdstuk 7/8) en eventuele actieve
  ERP-sync, die sowieso optioneel is (hoofdstuk 9).
- Bij Pro/Enterprise blijft het verkeer tussen werkplekken binnen het
  lokale netwerk — ook dat vereist dus geen internet, alleen de
  licentiecheck af en toe.

## Openstaande vragen

Geen — dit hoofdstuk is afgerond.
