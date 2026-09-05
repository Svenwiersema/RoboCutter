# RoboCutter — Checklist

Bijgehouden overzicht van wat besproken/vastgesteld is en wat nog open staat.
Wordt elke sessie bijgewerkt.

_Laatst bijgewerkt: 2026-09-05 — zie ook `OVERDRACHT.md` voor de
actuele codestatus (dit bestand blijft de bronwaarheid voor
ontwerpbeslissingen, `OVERDRACHT.md` voor bouwvoortgang)._

## Herkomst van eerder werk

Sven had dit ontwerp al eerder met ChatGPT uitgewerkt (Module 1
Projectbeheer, Module 2 Modellen en Module 3 Materialen waren daar
"afgerond", Module 4 Projecten was net begonnen). We gebruiken die
documenten niet als werkdocument (dat was precies het probleem — ChatGPT
herschreef het steeds), maar lopen de inhoud hier bewust na, module voor
module, en zetten alleen bevestigde punten over in de documenten in deze
map.

## ✅ Besproken / vastgesteld

- Kernfunctionaliteit: zaagplannen genereren voor **platen én balken**
- Programma berekent zelf de optimale zaagmethode/-volgorde
- Rekening houden met **nerfrichting** bij het genereren van zaagplannen
- Zaagplannen worden opgeslagen in een bibliotheek
- **Reststukken** worden onthouden en in een bibliotheek geplaatst
  (herbruikbaar)
- **Labels** worden gegenereerd voor zowel onderdelen als reststukken
- Een **materiaalbibliotheek** wordt bijgehouden
- **"Kasten"** kunnen los opgeslagen en samengevoegd worden tot een project
  (bv. een keuken)
- **Projectstatus** wordt bijgehouden; planning/scheduling valt expliciet
  **buiten scope**
- Optionele koppeling met een **ERP-systeem**, met verplichte standalone-
  werking zonder ERP
- Wordt een **commercieel product**: meerdere versies/edities +
  licentiecontrole (verifiëren dat het programma legaal is verkregen)
- Naam "RoboCutter": **"Robo" is branding/merk** van Sven, geen letterlijke
  robotaansturing
- Werkwijze: **hoofdstuk voor hoofdstuk** samen uitwerken vóór er gecodeerd
  wordt, met gerichte edits i.p.v. herschrijvingen
- Claude denkt actief mee met eigen voorstellen tijdens het proces
- **Module 8 — Technische architectuur & tech stack: volledig
  vastgesteld** ✅ (zie `chapters/08-technische-architectuur.md`) —
  Windows-only, Python, PySide6 (GUI), Nuitka (bundelen) + Inno Setup
  (installer), updates via Keygen, licentie-validatie verspreid +
  periodiek herverifieerd i.p.v. alleen bij opstarten; database: lokaal
  SQLite voor Demo/Hobby, één lokale netwerk-server-pc voor Pro/
  Enterprise (geen cloud-afhankelijkheid); betaalverwerking via Lemon
  Squeezy (merchant-of-record, regelt internationale BTW), gekoppeld aan
  Keygen via webhooks — maakt ook de Hobby-detectie uit hoofdstuk 7
  technisch mogelijk. Alle commerciële/licentie-functionaliteit (Keygen-
  validatie, editielimieten, watermerk/logo-restricties, werkplek-
  telling) wordt tijdens ontwikkeling wel gebouwd maar staat standaard
  uit, zodat Sven de volledige app zonder restricties op zijn eigen werk
  kan testen vóór activering — geldt alleen voor de commerciële laag,
  niet voor functionaliteit in het algemeen. Openstaande actiepunten (te
  verifiëren tijdens implementatie): Keygen-tier voor releases/updates,
  precieze licentie-validatielogica, definitieve keuze Lemon Squeezy vs.
  Paddle
- Design bestanden worden bijgehouden in
  `C:\Users\stenw\Documents\GitHub\RoboCutter\design`
- **Module 1 — Projectbeheer: volledig gevalideerd** ✅ (zie
  `chapters/module-1-projectbeheer.md`) — revisies (Rev A/B/C, altijd
  handmatig), sandboxes slaan alleen delta's op, 1 klant + 1
  contactpersoon per project, alleen start-/opleverdatum (geen
  planning), reststukken pas ná afronding vrijgegeven, geen apart
  "RoboDocument" (PDF/labels genereert RoboCutter zelf), gegenereerde
  zaagplannen/labels blijven gekoppeld aan het model en krijgen bij
  wijziging de status "Niet gecontroleerd" (zelfde mechanisme als
  werktekeningen in Module 2)
- **Begripsverduidelijking:** "model" (los herbruikbaar ontwerp, mag
  andere modellen bevatten — hier valt ook "kast" onder) en "project"
  (het klantwerk met revisies) zijn twee aparte concepten, zoals in het
  oorspronkelijke ChatGPT-document
- **Module 2 — Modellen: volledig gevalideerd** ✅ (zie
  `chapters/module-2-modellen.md`) — centrale modellenbibliotheek met
  nesting, vrije mappen+tags, materiaal als aparte sectie, dupliceren
  maakt een zelfstandig model, "Niet gecontroleerd"-status na wijziging
  (software+export+watermerk), veilige standaardinstellingen met
  uitgebreide configuratie voor gevorderden; modellen hebben ook
  revisies (Rev A/B/C, handmatig, zelfde revisie-waardig-regel als
  projecten)
- **Module 3 — Materialen: volledig gevalideerd, inclusief velden en
  bibliotheekstructuur** ✅ (zie `chapters/module-3-materialen.md`) —
  automatische hiërarchie + materiaalfamilies, live validatie zonder
  pop-ups, autocomplete/fuzzy matching met bevestiging, archiveren vóór
  verwijderen (verwijderen kan alleen vanuit het archief), verplichte
  vervangingskeuze bij verwijderde materialen in bestaande projecten,
  CSV/Excel-import; **twee aparte bibliotheken** (materialen vs.
  reststukken), binnen elk platen+balken samengevoegd met filters;
  materiaal-velden: naam, type (plaat/balk), afmetingen,
  materiaalfamilie, kleur/afwerking, nerfrichting, kerf, randafzaag-
  marge, minimale reststukgrootte, mes/groef, **fabriekskantenband**
  (welke rand(en)), productcode, **leverancier**, vrije tags, status —
  nadrukkelijk géén voorraadaantal of prijs (ERP-taak); reststuk-record
  neemt materiaal-eigenschappen over, aangevuld met huidige afmetingen,
  herkomst (project/model) en status beschikbaar/gebruikt
- **Module 4 — Projecten: volledig ontworpen en vastgesteld** ✅ (zie
  `chapters/module-4-projecten.md`) — project = model + klantgegevens +
  status; modellen als vaste kopie toegevoegd (met handmatige update-
  actie die een projectrevisie triggert) en/of losse onderdelen; heel
  project in één keer opslaan als nieuw model (incl. revisiegeschiedenis);
  één gecombineerd zaagplan per project, opnieuw gegenereerd bij
  wijziging; status Werkvoorbereiding → In productie → Installatie →
  Afgerond; reststukken pas definitief vrij bij Afgerond; afgeronde
  projecten archiveren i.p.v. verwijderen (zelfde patroon als Module 3)
- **Revisie-waardig (geldt voor projecten én modellen):** een wijziging
  op verzoek van de klant is revisie-waardig, het corrigeren van een
  fout uit de werkvoorbereiding niet
- **Zaagplan-optimalisatie & lay-out — afgerond** ✅ (zie
  `chapters/05-zaagplan-optimalisatie.md`) — prioriteit/zaagstrategie
  instelbaar door gebruiker, zaagsnede + randafzagen + minimale
  reststukgrootte per materiaal ingesteld, mes/groef en kantenband
  beïnvloeden plaatsing/volgorde, fabrieks-kantenband nooit afzagen,
  nerfrichting optioneel met drie mogelijke waarden (lange zijde, korte
  zijde, geen); lay-out van het document vastgesteld (plaat
  70-80%, geen legenda, benutting als %, zaagsnede-nummering volgt
  werkelijke volgorde); gebruiker kan onderdelen **binnen hetzelfde
  model** groeperen met een vaste onderlinge volgorde/oriëntatie (bv. 3
  ladefronten onder elkaar) zodat de nerf over de onderdelen doorloopt —
  optimizer bepaalt nog wel zelf waar de groep op de plaat komt; twee
  voorbeeld-zaagplannen (variant A "meest efficiënte plaatsing" en
  variant B "lange zijdes eerst") staan in `voorbeelden/`
- **Module 6 — Labels & identificatie: volledig ontworpen en vastgesteld**
  ✅ (zie `chapters/06-labels-en-identificatie.md`) — fysiek label met
  scanbare code, gegenereerd tegelijk met het zaagplan, zelfde "Niet
  gecontroleerd"-mechanisme, los herprintbaar; onderdeel-label toont
  onderdeel-ID/materiaal/projectnummer/afmeting, reststuk-label hetzelfde
  zonder projectnummer (geen magazijnlocatie); QR-code, barcode,
  kantenband-indicatie en nerfrichting-pijl zijn optioneel en samen één
  programmabrede instelling (geen keuze per printmoment); zowel dedicated
  labelprinters als gewone A4/A3-printers worden ondersteund
- **Module 9 — ERP-integratie: kernarchitectuur afgerond** 🟡 (zie
  `chapters/09-erp-integratie.md`) — optionele laag (standalone-first),
  beschikbaar in alle edities, tweerichtingsverkeer (import klant-/
  projectgegevens + materiaalvoorraad, export zaagplan/verbruik/
  reststukken), generieke/uitbreidbare koppel-laag (CSV/Excel als
  universele basis, later per ERP uit te breiden met een directe API);
  Express ERP heeft prioriteit (geen eigen zaagplan-functie), Borm lage
  prioriteit (heeft dat al); Sven stelt zelf een lijst samen van verder
  geschikte ERP's, koppelingen worden per stuk uitgewerkt zodra die lijst
  er is
- **Module 10 — Onderdelen importeren (DXF & Vectorworks): kernidee
  vastgesteld** ✅ (zie `chapters/10-onderdelen-importeren-dxf-cad.md`)
  — naast handmatig en CSV/Excel ook onderdelen importeren via **twee
  losstaande routes**: generieke DXF-import, en een aparte
  Vectorworks-import (vermoedelijk via een eigen te schrijven
  Vectorworks-plugin, gebruikmakend van Vectorworks' eigen
  zaaglijst-exportmogelijkheden) — dit zijn dus twee aparte
  importmogelijkheden, niet DXF "vooral vanuit Vectorworks"; DXF/
  Vectorworks-tekeningen kunnen niet-rechthoekige vormen bevatten, maar
  v1 van RoboCutter werkt alleen rechthoekig — bij een niet-rechthoekig
  onderdeel wordt de bounding box (grootste breedte/lengte) gebruikt;
  geldt zowel bij onderdelen in een model (Module 2) als losse
  onderdelen in een project (Module 4); vormgetrouw zagen/nesten van
  niet-rechthoekige onderdelen is een geparkeerde toekomstige uitbreiding
- **Module 12 — Niet-functionele eisen: volledig afgerond** ✅ (zie
  `chapters/12-niet-functionele-eisen.md`) — Windows 10 én 11; richtgetal
  voor prestaties: soepel tot ~500 onderdelen per project (een complete
  keuken is ~100-150 onderdelen); auto-save/crash-herstel, expliciet
  waarschuwen i.p.v. stilzwijgend een mogelijk onjuist zaagplan
  genereren, geen corrupte/verloren data bij wegvallende
  serververbinding, automatische periodieke back-up van de lokale
  database (concrete v1-functie, gezien het dataverliesrisico bij de
  lokale-server-architectuur van hoofdstuk 8); kernfunctionaliteit
  volledig offline, enige internetafhankelijkheid is de
  licentie-heartbeat en optionele ERP-sync
- **Module 13 — Toekomstige uitbreidingen / buiten scope: afgerond** ✅
  (zie `chapters/13-toekomstige-uitbreidingen.md`) — uitbreiding naar
  metaal/kozijnen blijft mogelijk (kern blijft zaag-optimalisator); uit
  het oude Ideeënboek: AI-ondersteunde optimalisatie, cloud-
  synchronisatie, mobiele app, CNC-export, plugin-systeem, API,
  webshopkoppelingen, 3D-weergave, kosten-/CO₂-besparing,
  productiestatistieken, machinekoppelingen, website/kennisbank/
  documentatie (tot de commerciële fase) — allemaal bewust geparkeerd;
  ERP-koppelingen stond hier ook op maar is inmiddels hoofdstuk 9
  geworden; verder geparkeerd: een cloud-gehoste database-optie
  (mogelijk Enterprise-only, hoofdstuk 8), vormgetrouw zagen/nesten van
  niet-rechthoekige onderdelen (hoofdstuk 10), en gebruikersrollen/
  -rechten (voor v1 heeft iedereen dezelfde rechten)
- **Licentiemodel & prijzen — volledig afgerond** (zie
  `chapters/licentiemodel-en-edities.md`): 4 edities: Demo (permanent
  gratis, 1 werkplek, max. 5 projecten, RoboCutter-logo + kleine tekst,
  verder volledige functionaliteit incl. ERP), Hobby (€79 eenmalig, 1
  werkplek, eigen logo, geen limieten), Pro (€29/maand, max. 3
  werkplekken), Enterprise (abonnement, €10/werkplek/maand tot max.
  €150/maand bij 15 werkplekken); handhaving via Keygen met een
  offline-grace-periode van 3 dagen
- **Principe: edities verschillen in capaciteit/prijs, niet in
  functionaliteit** — Sven wil nooit functies achter een hoger plan
  verstoppen (op Demo's projectlimiet na)
- Een "werkplek" = gelijktijdig actieve gebruiker/account, geen
  installatie; onbeperkt installeren toegestaan
- **Licentiehandhaving via Keygen** (floating/concurrent licenties +
  offline-ondersteuning, gratis tier/self-hosted CE om te beginnen)
- **Module 11 — UX/UI: volledig afgerond** ✅ (zie
  `chapters/11-ux-ui.md`) — interface uitsluitend Nederlands (later
  uitbreidbaar); accentkleur `#5F7FFF`, licht thema `#F2F3F4`
  (standaard), donker thema `#1E2028`, pastelachtige statuskleuren
  (succes `#6FCF97`, waarschuwing `#E8B84B`, kritiek `#E57373`);
  lettertype Inter; UI-architectuur: header met hoofdonderdelen
  (Projecten/Materialenbibliotheek/Reststukkenbibliotheek/Modellen)
  die als VS-Code-stijl tabbladen openen, elk met een eigen
  contextuele zijbalk ("je kan alleen de tools zien die je kan
  gebruiken"); min-pop-ups-principe: waarschuwingen in panelen i.p.v.
  modale dialogen; logo definitief vastgesteld (met tekst voor
  marketing, zonder tekst voor zaagplannen/exe-icoon, vereenvoudigd
  robotgezicht als werkbalk-/systemtray-icoon), gebaseerd op Svens
  bestaande RoboSten-merk; conceptmockup van het projectoverzicht
  vastgelegd in `assets/mockups/`; **iconenstijl**: dikke afgeronde
  lijnstijl, via de open-source icon-set Phosphor Icons (gewicht
  "Bold"), gekleurd volgens thema-/statuskleuren

## 🔲 Nog te bespreken (per hoofdstuk)

- ~~Materiaalbibliotheek~~ — ✅ afgerond, zie
  `chapters/module-3-materialen.md`
- ~~Labels & identificatie~~ — ✅ afgerond, zie
  `chapters/06-labels-en-identificatie.md`
- ~~Licentiemodel & edities~~ — ✅ afgerond, zie
  `chapters/licentiemodel-en-edities.md`
- ~~ERP-integratie~~ — 🟡 kernarchitectuur afgerond, zie
  `chapters/09-erp-integratie.md` (specifieke ERP-koppelingen volgen
  zodra Sven een lijst met geschikte systemen heeft samengesteld)
- ~~Technische architectuur & tech stack~~ — ✅ afgerond, zie
  `chapters/08-technische-architectuur.md`
- ~~UX/UI~~ — ✅ afgerond, zie `chapters/11-ux-ui.md`
- ~~Niet-functionele eisen~~ — ✅ afgerond, zie
  `chapters/12-niet-functionele-eisen.md`
- ~~Toekomstige uitbreidingen / buiten scope~~ — ✅ afgerond, zie
  `chapters/13-toekomstige-uitbreidingen.md`

## 💡 Suggesties van Claude (nog te bevestigen)

- Losse hoofdstukbestanden i.p.v. één groot document, zodat gerichte edits
  makkelijker blijven naarmate het document groeit (nu al zo toegepast)
- Materiaal- en kastdefinities los van elkaar houden zodat dezelfde
  materiaalbibliotheek voor meerdere projecten/kasten herbruikt kan worden
- Bij H11 een kort architectuur-besluit (ADR-achtig) vastleggen zodra de
  tech stack gekozen is, zodat de motivatie later terug te vinden is
- Bij H6 nadenken over zowel printbare labels als een digitale/QR-gekoppelde
  variant, met het oog op toekomstige ERP-koppeling (H9)
