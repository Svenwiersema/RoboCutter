# Overdracht — van ontwerp (Cowork) naar bouwen (Claude Code)

Dit bestand is voor een Claude Code-sessie die het bouwen van
RoboCutter oppakt, na een uitgebreid ontwerptraject dat in een Cowork-
sessie is doorlopen. Lees dit eerst, samen met
[`design/README.md`](design/README.md) en
[`design/checklist.md`](design/checklist.md) — dat zijn de
bronwaarheid voor alle productbeslissingen.

## Status

- **Ontwerp (hoofdstuk 0 t/m 13): volledig afgerond.** Elk hoofdstuk
  staat in `design/chapters/`, met een samenvatting per module in
  `design/checklist.md`. Enige uitzondering: hoofdstuk 9
  (ERP-integratie) staat bewust op 🟡 — Sven stelt zelf nog een lijst
  samen van geschikte ERP-systemen; dit hoofdstuk mag voorlopig
  blijven liggen.
- **Logo & branding**: definitief vastgesteld, bestanden in
  `design/assets/logo/` (met tekst, zonder tekst, werkbalk-icoon).
- **Code**: de eerste echte module is gebouwd:
  `src/robocutter/optimalisatie/` — de zaagplan-optimalisatie-motor
  (hoofdstuk 5), los van de UI, met een volledige pytest-suite
  (`tests/test_engine.py`, 14 tests, allemaal groen) en
  visuele voorbeelden (`scripts/demo_render.py` → `output/*.png`).
  Zie `README.md` in de repo-root voor hoe je dit draait.
- **Werkwijze UI (nieuw, vastgesteld):** voor élk UI-scherm eerst een
  HTML-conceptmockup (Artifact) bouwen en laten goedkeuren door Sven,
  pas daarna de echte PySide6-implementatie maken. Niet meer direct in
  PySide6 beginnen.
- **UI — eerste scherm gebouwd:** de home pagina (Projecten-overzicht,
  de landingspagina van de hele app) is uitgewerkt volgens deze
  werkwijze: eerst een goedgekeurde HTML-mockup, daarna
  `src/robocutter/ui/` (PySide6) — header met de vier hoofdonderdelen,
  VS Code-stijl tabbalk, contextuele zijbalk, KPI-tegels, project-
  kaarten met statuschips/voortgangsbalk, inline waarschuwingspaneel
  (geen pop-up), licht/donker thema-toggle. Draait via
  `python -m robocutter.ui.app` (dependency: `pip install -e ".[ui]"`).
  Gebruikt vaste voorbeeldprojecten uit `src/robocutter/ui/sample_data.py`
  — nog geen echte database-koppeling (Module 1/4 backend bestaat nog
  niet). Iconen zijn handgetekende SVG's in Phosphor Bold-stijl
  (`src/robocutter/ui/icons.py`) — Phosphor's eigen bestand kon niet via
  een toegestane bron ingeladen worden voor de HTML-mockup, dus is
  dezelfde aanpak in PySide6 aangehouden voor visuele consistentie.
  Inter (het vastgestelde lettertype) is nog niet als font-bestand
  gebundeld; de UI valt voorlopig terug op Segoe UI.
- **UI — tweede scherm gebouwd: Materialenbibliotheek.** Eerst de
  functie/logica zelf gebouwd (`src/robocutter/materialen/`: datamodel
  in `models.py`, de bibliotheeklogica in `bibliotheek.py` uit
  hoofdstuk 3 — live validatie en de archiveer-/verwijderworkflow
  (actief → gearchiveerd → definitief verwijderen, dat laatste alleen
  vanuit het archief) — en SQLite-opslag in `opslag.py`, hoofdstuk 8:
  Demo/Hobby = één lokaal SQLite-bestand). Gedekt door
  `tests/test_materialen.py` (16 tests, allemaal groen, incl. een test
  die een "herstart" simuleert door een tweede verbinding op hetzelfde
  bestand te openen, en een test voor de zoekfunctie hieronder).
  Daarna, op Svens verzoek, eerst getest met een ruwe, ongestylede
  PySide6 test-ui (`scripts/test_materialen_ui.py`, schrijft naar
  `data/materialen_test.db`) *voordat* de HTML-mockup-workflow werd
  gevolgd voor het uiteindelijke scherm — dat is bewust een uitzondering
  op de vaste volgorde, voor deze ene functie-gerichte tussenstap.
  Vervolgens: een goedgekeurde HTML-conceptmockup (met twee
  correctierondes — zoeken moest ook op afmetingen kunnen combineren
  met tekst, en materiaalfamilies moesten klikbaar zijn als filter, incl.
  een "toon alle families"-uitklap), en daarna de echte PySide6-pagina
  in `src/robocutter/ui/materialen_page.py`: contextuele zijbalk
  (Overzicht/Archief, type- en familiefilters), een doorzoekbare/
  sorteerbare tabel, en een uitklapbaar zijpaneel (geen pop-up) om een
  materiaal toe te voegen of te bewerken met alle hoofdstuk 3-velden en
  live validatie. Klikken op "Projecten" of "Materialenbibliotheek" in
  de header wisselt nu ook echt van pagina (`MainWindow._switch_page`);
  de `MaterialenPage`-instantie (en haar SQLite-verbinding) blijft
  daarbij en bij een thema-wissel in leven — zie de code-commentaren in
  `main_window.py` bij `_rebuild_content`/`_toggle_theme` voor waarom.
  Schrijft naar `data/robocutter.db` (het "echte" app-databestand,
  apart van de test-ui's `materialen_test.db`; beide lokaal,
  `.gitignore`d).
  De verbeterde zoekfunctie (elke los getypte term moet ergens matchen;
  een puur getal matcht exact op een afmeting/technische maat, bv.
  "multiplex 2800 18") zit nu ook in `MaterialenBibliotheek.lijst()`
  zelf, niet alleen in de mockup — dus ook beschikbaar voor toekomstige
  code die de bibliotheek gebruikt.
  **Nog geen multi-gebruiker-opslag**: Sven vroeg expliciet of dit al
  op bv. een NAS gezet kan worden zodat meerdere gebruikers hetzelfde
  materiaal zien — dat kan nog niet. Hoofdstuk 8 legt uit waarom een
  gedeeld SQLite-bestand op een netwerkschijf niet geschikt is bij
  gelijktijdig schrijven (corruptierisico); de geplande oplossing voor
  Pro/Enterprise is één lokale netwerk-server-pc waar de andere
  werkplekken via het lokale netwerk mee verbinden — die server en het
  bijbehorende protocol bestaan nog niet.
  **Update**: deze instelbare opslaglocatie is inmiddels gebouwd — zie
  de Opties/instellingen-sectie verderop in dit document
  (`robocutter.instellingen`, `InstellingenBeheer.effectieve_db_pad()`).
- **Echte VS Code-stijl tabbalk (nieuw):** `MainWindow` houdt nu
  `self._open_tabs` (volgorde van openen) en `self._active_tab` bij i.p.v.
  één actieve pagina. Klikken op "Projecten"/"Materialenbibliotheek" in
  de header opent het als tabblad (of activeert het als het al open
  staat) — beide kunnen dus tegelijk open staan en je wisselt ertussen
  door op een tabblad te klikken. Elk tabblad heeft een sluitkruisje
  behalve het vaste "Projecten"-tabblad (net als in VS Code niet te
  sluiten). Materialenbibliotheek kan, net als in VS Code, maar in één
  instantie tegelijk open staan (nogmaals op de knop klikken activeert
  het bestaande tabblad i.p.v. een tweede te openen).
  Losse project-/modeltabbladen en een Modellenbibliotheek-tabblad
  passen straks in dezelfde `_open_tabs`/`_PAGE_TAB`-mechaniek zodra die
  schermen bestaan (Sven heeft bevestigd dat de tab-mechaniek zelf nu
  gebouwd mag worden, maar de bijbehorende schermen nog niet — die
  volgen pas na een eigen HTML-mockup).
  **Bouwkundig detail dat het proberen waard is te onthouden:** een
  kale `QPushButton` met alleen kind-widgets in een eigen layout (geen
  `setText`/`setIcon`) berekent zijn `sizeHint()` op basis van
  Qt's knop-stijl en negeert daarbij die kind-layout — kromp in de
  praktijk naar een paar pixels. De tabs gebruiken daarom een gewone
  klikbare `QWidget`-subklasse (`_KlikbareTab`, met een eigen
  `mousePressEvent`) i.p.v. `QPushButton`.
  Nog te doen voor de UI in het algemeen: Modellen (navigatieknop staat
  er al, bewust uitgeschakeld met tooltip "Nog niet gebouwd" —
  Reststukkenbibliotheek is inmiddels wél gebouwd, zie hieronder), en
  het bundelen van Inter.
- **Vier bugs gemeld en gefixt na de tabbalk (Sven testte de app zelf):**
  1. Het toevoegen/bewerken-paneel toonde in het lichte thema toch een
     donkere achtergrond. Oorzaak: de `QScrollArea`/viewport binnen de
     drawer had geen eigen stylesheet-achtergrond, waardoor Qt op
     Windows het systeembrede (donkere) thema van die viewport liet
     doorschijnen i.p.v. de kleur van de drawer erachter. Fix: de
     scroll-viewport en het scroll-content-widget expliciet
     `background: transparent` geven in `theme.py`.
  2. Een `QWidget`-subklasse (zoals de nieuwe `_KlikbareTab`) schildert
     `background: ...` uit een stylesheet niet vanzelf — dat doen alleen
     QFrame/QPushButton/QLabel e.d. standaard. Fix:
     `setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)` in
     `_KlikbareTab.__init__`.
  3. In de materialenbibliotheek verdwenen materialen (of bleef oude en
     nieuwe tekst over elkaar heen staan) bij het wisselen van
     type-filter. Oorzaak: `QTableWidget.setCellWidget()` op een rij die
     al een widget bevatte (omdat filteren de rij-index van een ander
     materiaal oplevert) verving de content niet altijd schoon. Fix:
     `self._table.clearContents()` vóór het herbouwen van de tabelrijen
     in `materialen_page.py::_ververs_tabel`.
  Vierde bug, later gemeld door Sven na het testen van het Opties-scherm:
  de tekst in de statusbalk onderin ("Offline modus — lokale database")
  werd afgesneden. Oorzaak: `_build_status_bar` in `main_window.py` zette
  de statusbalk op een vaste hoogte van 26px, terwijl de werkelijk
  benodigde hoogte (met de geneste dot+tekst-widget erin) 35px was —
  Qt loste dat tekort op door het meest flexibele label te knijpen tot
  3px hoog i.p.v. de normale 12px, in plaats van de vaste-grootte
  stip ernaast aan te passen. Fix: `setFixedHeight(26)` verwijderd (de
  statusbalk sizet zichzelf nu naar zijn content) en de overbodige
  geneste `offline_row`/`offline_widget`-laag opgeruimd tot één platte
  `QHBoxLayout`. Geverifieerd door de werkelijke widget-geometrie op te
  vragen (hoogtes matchten daarna hun `sizeHint()`) i.p.v. alleen
  visueel te beoordelen.
  Alle vier geverifieerd met échte pixel-sampling/knop-klik-simulatie
  i.p.v. alleen visueel screenshots beoordelen — dat laatste bleek
  eerder deze sessie onbetrouwbaar door een schermafdruk-timingprobleem
  in het scriptmatig testen (zie git-geschiedenis), dus nu bewust
  geverifieerd via de widget-eigenschappen/pixels zelf.
- **Reststukkenbibliotheek — derde scherm gebouwd, dit keer zonder
  HTML-mockup:** eerst weer de functie/logica zelf (zelfde aanpak als
  bij de materialenbibliotheek), en daarna, op Svens expliciete
  verzoek, meteen het echte PySide6-scherm gebouwd — géén HTML-mockup
  deze keer, omdat dit tabblad "praktisch hetzelfde is als de
  materialen bibliotheek" (Svens woorden). `src/robocutter/reststukken/`
  bevat het datamodel (`models.py`: `Reststuk` met resterende
  lengte/breedte, herkomst-project/-model, en status
  beschikbaar/gebruikt), bibliotheeklogica (`bibliotheek.py`: live
  validatie en de beschikbaar/gebruikt-workflow — hoofdstuk 3 noemt
  geen archiveerstap voor reststukken, dus verwijderen kan direct,
  anders dan bij materialen) en SQLite-opslag (`opslag.py`, eigen
  `reststukken`-tabel in hetzelfde `data/robocutter.db`-bestand). Een
  `Reststuk` slaat bewust *niet* zijn eigen kerf/nerfrichting/type/
  familie/kleur op — die "neemt het over" van het gekoppelde materiaal
  (hoofdstuk 3) via `materiaal_id`, opgezocht in de
  `MaterialenBibliotheek` (`ReststukkenBibliotheek.materiaal_van`) — zo
  kan het nooit uit de pas lopen als het materiaal zelf wijzigt.
  Zoeken/filteren op type werkt daarom ook via die koppeling. Gedekt
  door `tests/test_reststukken.py` (12 tests, allemaal groen).
  Het echte scherm, `src/robocutter/ui/reststukken_page.py`, is qua
  opzet een zusje van `materialen_page.py`: contextuele zijbalk
  (Beschikbaar/Gebruikt i.p.v. Overzicht/Archief, type- en
  familiefilters), dezelfde doorzoekbare/sorteerbare tabel-look, en een
  uitklapbaar zijpaneel (geen pop-up) met live validatie. Het scherm
  hergebruikt bewust de bestaande `MaterialenBibliotheek`-instantie van
  `MaterialenPage` (`self._reststukken_page = ReststukkenPage(self._materialen_page.bibliotheek, ...)`
  in `main_window.py`) i.p.v. een eigen tweede verbinding te openen —
  zo blijft materiaaldata (incl. archiefstatus) in beide schermen
  altijd consistent. Tijdens het bouwen bleek een `QComboBox` in de
  drawer (materiaalkeuze) volledig onzichtbaar te worden: zonder eigen
  `role="field"`-stylesheet leunde hij op de achtergrond van een
  voorouder-widget die elders bewust `transparent` was gemaakt (zie de
  drawer-scroll-fix hierboven) — fix: `QComboBox[role="field"]` kreeg in
  `theme.py` dezelfde expliciete achtergrond/rand/dropdown-styling als
  de tekstvelden. Ruwe test-ui: `scripts/test_reststukken_ui.py`, deelt
  het materialen-testbestand (`data/materialen_test.db`) met
  `test_materialen_ui.py` en heeft een eigen
  `data/reststukken_test.db` (beide lokaal, `.gitignore`d) — apart van
  het echte scherm, dat net als Materialenbibliotheek naar
  `data/robocutter.db` schrijft.
- **Modellenbibliotheek — functie én scherm gebouwd (module 2):** zelfde
  aanpak als eerder bij Materialen/Reststukken: eerst de functie/logica,
  daarna een goedgekeurde HTML-conceptmockup, en tot slot het echte
  PySide6-scherm (`src/robocutter/ui/modellen_page.py`). Bij het
  goedkeuren van de mockup liet Sven twee dingen rechtzetten tijdens het
  uitwerken naar PySide6:
  1. De pijltjes van getalvelden (aantal, groepsvolgorde) gebruiken de
     eigen chevron-stapknoppen uit `materialen_page.py`/
     `reststukken_page.py` i.p.v. onbetrouwbare native pijltjes ("de
     pijlen hebben weer geen style" — zelfde Qt-eigenaardigheid als
     eerder bij `QDoubleSpinBox`, nu ook opgelost voor het nieuwe
     `QSpinBox`-gebruik via `QSpinBox[role="fieldSpin"]` in `theme.py`).
  2. De headernavigatie in `main_window.py` noemde dit onderdeel
     "Modellen" i.p.v. "Modellenbibliotheek", een inconsistentie met
     Materialenbibliotheek/Reststukkenbibliotheek — rechtgezet in
     `_NAV_ITEMS`/`_PAGE_TAB`.
  Het scherm is qua opzet een zusje van `materialen_page.py`: een
  zijbalk met Mappen- en Tags-filters (geen Overzicht/Archief — module 2
  kent geen archiveerstap voor modellen), een doorzoekbare/sorteerbare
  tabel (kolommen Model/Map/Onderdelen/Submodellen/Tags), en een
  uitklapbaar paneel om een model toe te voegen of te bewerken. Dat
  paneel is breder dan bij Materialen/Reststukken (480px i.p.v. 420px)
  omdat het, naast de basisgegevens, ook de onderdelen- en
  submodellen-lijst van het model beheert: onderdelen krijgen een eigen
  rij (materiaal, afmetingen, nerf, kantenband, groep-badge) met een
  inline toevoeg-/bewerkformulier eronder (hergebruikt bewust
  `_segmented`/`_rand_chip_rij` uit `materialen_page.py` voor
  nerfrichting/kantenband i.p.v. een nieuw widget te bouwen), en
  submodellen krijgen een eigen rijenlijst met een keuzelijst waarin
  modellen die een cirkelverwijzing zouden veroorzaken uitgeschakeld
  staan (`ModellenPage._zou_cirkel_veroorzaken`, dezelfde graafdoorloop
  als de backend). Verwijderen van een model dat nog als submodel in
  gebruik is, toont — i.p.v. de gebruikelijke "Verwijderen?"-bevestiging
  — een inline melding welk ander model het nog gebruikt.
  `src/robocutter/modellen/`
  bevat het datamodel (`models.py`: `Model` met naam/omschrijving, een
  vrije map-string ("Map" = een vrije, zelfgekozen mapnaam/pad om
  modellen in te organiseren en op te filteren in de bibliotheek, bv.
  "Keukens/Onderkasten" — puur voor overzicht, geen invloed op het
  zagen zelf) en tags voor zoeken/filteren, een lijst `ModelOnderdeel`
  en een lijst `SubModelVerwijzing`), bibliotheeklogica
  (`bibliotheek.py`) en SQLite-opslag (`opslag.py`, eigen
  `modellen`-tabel in hetzelfde `data/robocutter.db`-bestand,
  onderdelen/submodellen als JSON in de rij, zelfde aanpak als `tags`
  bij Materialen). Elk `ModelOnderdeel` heeft, net als de
  optimalisatie-motor (hoofdstuk 5), een `nerfrichting_vereist`
  (lange_zijde/korte_zijde/geen — hoe dat ene onderdeel zelf t.o.v. de
  nerf van de plaat georiënteerd moet staan, geen uitspraak over de
  positie t.o.v. ándere onderdelen) en `kantenband_randen`
  (boven/onder/links/rechts). Vier ontwerpvragen die open stonden na
  hoofdstuk 2 zijn met Sven kortgesloten vóór/tijdens het bouwen:
  1. **Scope**: alleen de Modellenbibliotheek zelf nu; Projecten
     (module 1/4, met het snapshot-mechanisme project↔model) is een
     aparte, latere stap.
  2. **Materiaal per onderdeel, niet per model**: elk `ModelOnderdeel`
     kiest zijn eigen `materiaal_id` (zelfde referentiepatroon als
     `Reststuk` → `Materiaal`), zodat een model gemengde materialen mag
     bevatten (bv. kastromp in spaanplaat, deurtjes in mdf).
  3. **Nesting meteen meegenomen**: een model mag andere modellen
     bevatten via `submodellen` (`SubModelVerwijzing`, met een aantal)
     — dit is in hoofdstuk 2 wezenlijk voor het begrip ("dit is ook
     waar een kast onder valt"). `ModellenBibliotheek.valideer()`
     controleert daarom, naast de gebruikelijke veld- en
     materiaal-checks, ook op **cirkelverwijzingen**: een model mag
     zichzelf niet direct of via een keten van submodellen bevatten
     (`_bevat_cirkelverwijzing`, een graafdoorloop over de al
     opgeslagen submodel-ketens). `verwijderen()` blokkeert bovendien
     (met `ModelInGebruikError`) zolang een ander model dit model nog
     als submodel bevat.
  4. **Groep-koppeling nu al op het model** (n.a.v. Svens vraag of
     onderdelen "perse in de nerfrichting onder elkaar of naast elkaar
     moeten"): hoofdstuk 5 kent het concept "groep" — een vaste set
     onderdelen (zelfde `groep_id`) die niet los van elkaar roteren en
     als één blok verticaal gestapeld blijven, in de volgorde van
     `groep_volgorde`. Dat zat al in de optimalisatie-motor zelf
     (`optimalisatie.models.Onderdeel.groep_id`/`groep_volgorde`), en
     zit nu ook op `ModelOnderdeel` (zelfde velden/semantiek) — de
     modellenbibliotheek wordt net als Materialen/Reststukken gewoon in
     zijn geheel opgeslagen, dus dit hoeft niet apart op projectniveau
     geregeld te worden.
  Bewust uitgesteld (net als eerder de CSV-import bij Materialen): een
  archiveer-/verwijderworkflow zoals bij Materialen (hoofdstuk 2 noemt
  dit niet expliciet voor modellen, v1 verwijdert direct met alleen de
  in-gebruik-check hierboven), en de revisiegeschiedenis (Rev A, Rev
  B, ...) die hoofdstuk 2 wel noemt maar die een eigen substantieel
  stuk werk is. Gedekt door `tests/test_modellen.py` (16 tests,
  allemaal groen: validatie, directe én indirecte
  cirkelverwijzing-detectie, het verwijder-blokkade-gedrag, zoeken,
  groep-velden, en een SQLite-persistentie-roundtrip). Ruwe test-ui
  (`scripts/test_modellen_ui.py`, deelt het materialen-testbestand
  `data/materialen_test.db` met de andere test-ui's en heeft een eigen
  `data/modellen_test.db`) bestaat nog als losse testtool, maar het
  echte scherm (`modellen_page.py`) is nu de manier waarop Modellen in
  de app zelf gebruikt wordt — geverifieerd met een los smoke-testscript
  dat het paneel end-to-end aanstuurt (model + onderdeel + submodel
  aanmaken/opslaan/teruglezen, cirkelverwijzing- en
  in-gebruik-detectie, thema-wissel), naast de bestaande pytest-suite.
- **Projectenbeheer — functie gebouwd (module 1 + 4, nog geen mockup/
  scherm):** het laatste van de vier hoofdonderdelen, zelfde aanpak als
  steeds: eerst alleen de functie/logica. `src/robocutter/projecten/`
  bevat het datamodel (`models.py`: `Project` met klantgegevens,
  status en twee manieren om onderdelen te verzamelen — modellen als
  vaste kopie via `ProjectModelInstantie`, en losse onderdelen), de
  bibliotheeklogica (`bibliotheek.py`: het snapshot-mechanisme en de
  archiveerworkflow) en een aparte `zaaglijst.py` voor de gecombineerde
  onderdelenlijst met sortering. Vier dingen zijn met Sven kortgesloten
  vóór het bouwen:
  1. **Klantgegevens zijn vrije tekstvelden** (`klant`, `contactpersoon`,
     `email`, `telefoon`) i.p.v. een aparte klantenbibliotheek — die
     noemt hoofdstuk 1 wel ("centraal in bibliotheken beheerd") maar
     bestaat nergens (geen ontwerphoofdstuk, geen code). Sven: RoboCutter
     onderhoudt dit zelf niet, dat wordt later met een ERP-koppeling
     (hoofdstuk 9) opgelost.
  2. **Model-snapshot**: `ProjectenBibliotheek.model_toevoegen` haalt
     een model op en slaat het plat via `_platslaan` — een recursieve
     helper die ook geneste submodellen (hoofdstuk 2) meeneemt en
     aantallen doorvermenigvuldigt. Die platte kopie leeft daarna
     onafhankelijk van de bibliotheek (`model_id` blijft bewaard voor de
     expliciete `model_bijwerken_naar_laatste_versie`-actie, die opnieuw
     platslaat — géén revisieregistratie, zie punt 3).
  3. **Scope nu**: CRUD + samenstelling (model-snapshots + losse
     onderdelen) + zaaglijst + archiveren horen er nu bij.
     Revisiegeschiedenis/sandboxes, "project opslaan als nieuw model",
     en écht een zaagplan genereren (+ de daarvan afhankelijke
     "reststukken pas vrijgeven bij Afgerond") zijn expliciet door Sven
     uitgesteld — net als bij Modellen, eigen substantieel werk dat nog
     nergens in de app bestaat.
  4. **Zaaglijst met multi-criteria sortering** (Svens eigen toevoeging
     aan deze taak: "de gebruiker moet de zaaglijst kunnen sorteren op
     meerdere criteria zoals materiaal en dan breedte"): `zaaglijst.py`
     bouwt één `ZaaglijstRegel`-lijst uit alle model-snapshots en losse
     onderdelen (`bouw_zaaglijst`), en `sorteer_zaaglijst(regels,
     ["materiaal", "breedte"], materialen)` sorteert op een samengestelde
     sleutel uit een geordende lijst sleutelnamen (`SORTEERSLEUTELS`:
     materiaal, naam, breedte, hoogte, aantal, herkomst) — precies
     "eerst op materiaal, dan op breedte". Onbekende sleutel geeft een
     duidelijke `OnbekendeSorteersleutelError`.
  Archiveren volgt het Materialen-patroon (`OngeldigeStatusOvergangError`):
  alleen mogelijk vanuit status `AFGEROND`, definitief verwijderen alleen
  vanuit gearchiveerd. De vier statusfasen (Werkvoorbereiding → In
  productie → Installatie → Afgerond) zijn vrij instelbaar — het ontwerp
  geeft geen overgangsregels tussen fasen. Kleine opgeruimde duplicatie
  onderweg: `robocutter.modellen.opslag`'s onderdeel-(de)serialisatie
  (`onderdeel_naar_dict`/`dict_naar_onderdeel`) is publiek gemaakt zodat
  Projecten die kan hergebruiken i.p.v. dupliceren; `sample_data.py`
  importeert `ProjectStatus` nu vanuit `robocutter.projecten.models`
  i.p.v. een eigen kopie te definiëren. Gedekt door
  `tests/test_projecten.py` (15 tests: validatie, platslaan incl.
  geneste submodellen, bijwerken-naar-laatste-versie, archief-workflow,
  zaaglijst-opbouw én de multi-sort-test die specifiek bewijst dat
  `["materiaal", "breedte"]` eerst op materiaal groepeert en daarbinnen
  op breedte sorteert, en een SQLite-persistentie-roundtrip). Ruwe
  test-ui: `scripts/test_projecten_ui.py`, deelt de materialen-/
  modellen-testbestanden met de andere test-ui's en heeft een eigen
  `data/projecten_test.db`, met een zaaglijst-paneel met twee
  sorteer-keuzelijsten om de multi-criteria-sortering live te
  proberen. **Geen HTML-mockup of PySide6-scherm in deze stap** — dat
  volgt later, zelfde mockup-first-werkwijze als steeds.
- **Opties/instellingen — functie gebouwd, en al echt gekoppeld:**
  op Svens verzoek gebouwd vóórdat het Projecten-scherm verder werd
  opgepakt. Hier bestaat geen eigen ontwerphoofdstuk voor — regels
  staan verspreid (bedrijfslogo in module 1, zaagstrategie in
  hoofdstuk 5, label-vlaggen in hoofdstuk 6) en er was nergens een
  opslagmechanisme voor app-brede voorkeuren (geen `QSettings`, geen
  configbestand). `src/robocutter/instellingen/` bevat het datamodel
  (`models.py`: `Instellingen` — één enkel record, geen lijst/CRUD
  zoals de bibliotheken: `opslag_map`, `thema`, `bedrijfslogo_pad`,
  `standaard_zaagstrategie`, `werkvoorbereider_naam`), opslag
  (`opslag.py`: bewust GEEN SQLite-tabel in `data/robocutter.db` —
  circulair, want de instelling die bepaalt wáár die database staat kan
  niet in diezelfde database leven — maar een klein JSON-bestand op
  `%APPDATA%\RoboCutter\instellingen.json`) en beheer (`beheer.py`:
  validatie en `InstellingenBeheer`, met `effectieve_data_map()`/
  `effectieve_db_pad()` en `wijzig_opslaglocatie()`). Sven koos de
  scope (naast de expliciet gevraagde instelbare opslaglocatie ook
  thema-voorkeur, bedrijfslogo, standaard zaagstrategie en
  werkvoorbereider-naam; label-layout-opties komen later, labels
  bestaan nog niet als feature) en bevestigde: bij het wijzigen van de
  opslaglocatie moet een bestaand databasebestand **automatisch mee
  verhuizen** (`wijzig_opslaglocatie` gebruikt `shutil.move`, met een
  duidelijke fout als de doelmap al een databasebestand heeft). Bewuste
  vereenvoudiging: dit herlaadt geen al-open SQLite-verbindingen elders
  in de app — een lopende sessie moet herstart worden voordat andere
  schermen de nieuwe locatie gebruiken.
  **Dit is meteen echt gekoppeld, geen los backend-stukje:**
  `materialen_page.py`, `reststukken_page.py` en `modellen_page.py`
  hadden elk onafhankelijk dezelfde `_DB_PAD`-constante — die is nu
  vervangen door `InstellingenBeheer().effectieve_db_pad()` (lost meteen
  de bestaande verdrievoudiging op, en zal ook `projecten_page.py`
  straks gebruiken). `main_window.py` leest bij opstarten
  `InstellingenBeheer().huidige.thema` (i.p.v. altijd hardcoded
  `LICHT`) en slaat de keuze op in `_toggle_theme()` — het thema wordt
  dus nu voor het eerst echt onthouden tussen herstarts. Geverifieerd
  met de echte app: thema wisselen, opnieuw opvragen via een losse
  `InstellingenBeheer()`-instantie bevestigt dat het bestand
  (`%APPDATA%\RoboCutter\instellingen.json`) correct wordt weggeschreven
  en teruggelezen. `bedrijfslogo_pad`, `standaard_zaagstrategie` en
  `werkvoorbereider_naam` hebben nog geen consumerende feature
  (documentgeneratie/zaagplan-vanuit-project bestaan nog niet) en zijn
  dus voorlopig alleen op te slaan/uit te lezen.
  **Belangrijke les tijdens het bouwen (zie ook de opgeslagen memory
  hierover)**: een vroege versie van de tests maakte een
  `InstellingenBeheer` aan zonder de standaard-datamap te overschrijven,
  waardoor `wijzig_opslaglocatie()` per ongeluk het **echte**
  ontwikkel-databasebestand (`data/robocutter.db`, met Svens eigen
  materialen/modellen) verplaatste naar een pytest-tmp-map. Dit werd
  direct opgemerkt (de test faalde erop) en het bestand is teruggezet
  vanuit de nog-niet-opgeruimde tmp-directory — geen dataverlies, maar
  wel de aanleiding om `InstellingenBeheer` een expliciete
  `standaard_data_map`-parameter te geven, zodat tests nooit meer
  stilzwijgend op de echte datamap kunnen aangrijpen. Gedekt door
  `tests/test_instellingen.py` (11 tests: laden/opslaan-roundtrip,
  validatie, `wijzig_opslaglocatie` met en zonder bestaand bestand, en
  het conflict-scenario). Ruwe test-ui: `scripts/test_instellingen_ui.py`
  — gebruikt bewust eigen testbestanden (nooit de echte
  `%APPDATA%`-instellingen of `data/robocutter.db`).

- **Opties/instellingen — nu ook een echt scherm:** op Svens
  expliciete verzoek rechtstreeks in PySide6 gebouwd, zonder
  HTML-mockup ("dit moet een simpel ui zijn"). `src/robocutter/ui/instellingen_page.py`
  is bewust géén zusje van de bibliotheek-schermen (geen sidebar,
  tabel of drawer) — `Instellingen` is één enkel record, dus gewoon
  twee kaarten op de pagina zelf: "Algemeen" (thema, standaard
  zaagstrategie en werkvoorbereider-naam als segmented controls/
  tekstvelden, bedrijfslogo met bestandskiezer) en "Opslaglocatie
  databasebestand" (huidige locatie, mapkiezer, wijzigknop — hergebruikt
  `InstellingenBeheer.wijzig_opslaglocatie()`). Foutmeldingen/bevestiging
  verschijnen inline in een banner (geen `QMessageBox`-pop-ups, zelfde
  principe als de bibliotheekschermen), anders dan de ruwe
  `scripts/test_instellingen_ui.py` die nog wel `QMessageBox` gebruikte.
  Bereikbaar via een nieuw schuifknoppen-icoon (`"sliders"`, toegevoegd
  aan `icons.py`) in de header naast de thema-toggle, dat het scherm als
  gewoon (sluitbaar) tabblad opent via dezelfde `_open_tab`-mechaniek als
  de hoofdonderdelen — geen vijfde knop in de hoofdnavigatie, want
  Instellingen is geen bibliotheekmodule.
  `MainWindow` en `InstellingenPage` delen dezelfde `InstellingenBeheer`-
  instantie (zelfde patroon als de gedeelde `MaterialenBibliotheek`
  tussen Materialen/Reststukken/Modellen); na het opslaan van een
  gewijzigd thema roept de pagina `on_gewijzigd()` aan zodat `MainWindow`
  meteen de rest van de chrome/tabbladen laat meewisselen i.p.v. dat pas
  na een herstart te doen — geverifieerd met een los smoke-testscript
  (thema wisselen via de header-knop, dan via het Opties-scherm
  terugzetten, en de opslaglocatie wijzigen naar een tijdelijke map).
  Zelfde bewuste vereenvoudiging als eerder gedocumenteerd: een
  opslaglocatie-wijziging herlaadt geen al-open SQLite-verbindingen
  elders in de app.
  **Direct daarna, op Svens verzoek:** de losse thema-toggle-knop
  (zon/maan) in de header is verwijderd — thema kiezen hoort nu
  uitsluitend bij het Opties-scherm. Daar is thema ook de bewuste
  uitzondering op "alles achter de Opslaan-knop": de segmented control
  past meteen live toe zodra je erop klikt (`InstellingenPage.
  _thema_live_gewijzigd`), i.p.v. pas na een aparte opslaan-actie. Er is
  een derde optie "Systeem" bijgekomen (`GELDIGE_THEMAS` uitgebreid),
  die Windows' eigen licht/donker-voorkeur volgt via de nieuwe
  `robocutter.ui.theme.resolve_thema()`/`systeem_is_donker()` (Qt's
  `styleHints().colorScheme()`, Qt 6.5+) — dit wordt op het moment van
  toepassen opgelost, geen live meeluisteren naar een OS-thema-wissel
  terwijl de app open staat (bewust uitgesteld voor een latere
  iteratie).
  **Ook, op Svens verzoek:** "standaard zaagstrategie" had nog maar 2
  opties (dezelfde 2 die `engine.genereer_zaagplan` daadwerkelijk
  uitvoert). Bewust in twee stappen opgepakt — Sven koos expliciet
  "eerst alleen keuze-opties aanvullen, later toevoegen aan de
  zaagmotor" toen ik vroeg of hij ook meteen nieuwe algoritmes in
  `engine.py` wilde. Het kiezen van de juiste 4 namen kostte een paar
  correctierondes (zie git-geschiedenis voor het volledige verloop) —
  eindresultaat: `GELDIGE_ZAAGSTRATEGIEEN` = `"efficient"`
  ("Efficiënt": vrije plaatsing voor maximale opbrengst, best-fit — de
  methode die de motor nu al uitvoert), `"rijen"` (rijhoogte past zich
  per rij aan aan het grootste stuk erin), `"stroken"` (zoals Rijen,
  maar overal dezelfde vaste strookbreedte — subtiel maar reëel
  verschil, op Svens verzoek apart gehouden) en `"guillotine"`
  (uitsluitend doorlopende zaagsnedes van rand tot rand — een écht
  apart, strikter algoritme dan Efficiënt, óók al gebruikt Efficiënt's
  huidige implementatie zelf intern ook al een guillotine-stijl
  splitsing). Sven corrigeerde onderweg zelf een eerdere, foute
  aanname van mij dat "efficient" en "guillotine" hetzelfde zouden zijn
  (dat zijn ze dus niet) en dat "efficient" iets anders zou zijn dan
  wat toen apart "vrije_plaatsing"/"Nesting" heette (dat was júist wel
  hetzelfde, dus samengevoegd tot alleen "efficient"). Bewust ook niet
  "Nesting" genoemd: die term is in de designdocs al gereserveerd voor
  een heel andere, grote toekomstige feature (2D-vormen-nesting uit
  DXF-import, hoofdstuk 10/13). Alleen `"efficient"`/`"rijen"` worden
  nog echt uitgevoerd door de motor; `instellingen_page.py`'s
  `_STRATEGIE_OMSCHRIJVING` vermeldt dat expliciet bij Stroken/
  Guillotine, en de segmented control toont een live hint-tekst met de
  omschrijving van de aangeklikte optie (nuttig, want dit zijn minder
  vanzelfsprekende vaktermen dan Licht/Donker).
  **Bijvangst tijdens het testen**: het herbenoemen liet zien dat een
  eerder opgeslagen (inmiddels ongeldige) strategienaam een `KeyError`
  gaf bij het openen van het Opties-scherm — overkwam de echte
  `%APPDATA%\RoboCutter\instellingen.json` op deze dev-machine even
  écht (per ongeluk weggeschreven tijdens het testen van een
  tussenversie), hersteld naar `"efficient"`. Nu opgevangen met een
  expliciete fallback naar de eerste geldige waarde
  (`GELDIGE_ZAAGSTRATEGIEEN[0]`) in plaats van een crash, zodat een
  toekomstige hernoeming dit niet opnieuw breekt.
- **Dashboard/Projecten gesplitst + Projectenbibliotheek nu ook een
  echt scherm:** vóór deze wijziging was er maar één "Projecten"-tabblad
  dat zowel de KPI-/overzichtspagina als (impliciet) de rol van
  projectenbeheer vervulde. Op Svens verzoek nu twee aparte dingen: de
  vaste, niet-sluitbare eerste tab heet nu "Dashboard" (tabsleutel
  `"dashboard"`, opent nog steeds automatisch bij opstarten, inhoud
  ongewijzigd — nog steeds `sample_data.py`-gedreven), en "Projecten" is
  nu een écht, SQLite-opgeslagen scherm (`projecten_page.py`,
  tabsleutel `"projecten"`, bereikbaar via de header-navigatieknop) —
  op Svens verzoek zonder HTML-mockup ("net zoals met
  materiaalbibliotheek") gebouwd als zusje van `materialen_page.py`:
  zijbalk (Overzicht/Archief + status-snelfilters met dezelfde
  chip-kleuren als de Dashboard-kaarten), doorzoekbare/sorteerbare
  tabel, en een paneel voor klantgegevens/status/planning (archiveren
  alleen vanuit status Afgerond, zelfde regel als de backend). Bewust
  nog GEEN model-instanties/losse-onderdelen-beheer of zaaglijst-view
  in dit paneel — dat hoort bij het latere, aparte detailtabblad per
  project (wél met een eigen HTML-mockup, want dat scherm heeft geen
  bestaand scherm om op te lijken en is rijk: klantgegevens, status,
  gekoppelde modellen/onderdelen, zaaglijst); tot die tijd is dit paneel
  de enige manier om een project te bewerken. Tijdens het bouwen bleek
  het statusveld als segmented control (4 lange labels) het 420px-brede
  paneel horizontaal te laten overlopen — vervangen door een
  `QComboBox`, zoals de ruwe `scripts/test_projecten_ui.py` daar ook al
  voor koos.
  **Ook, op Svens verzoek:** tabbladen zijn nu sleepbaar om de volgorde
  te wijzigen (zelfde interactie als VS Code) — een eigen Qt-drag met
  `QMimeData` op `_KlikbareTab` (`mousePressEvent`/`mouseMoveEvent`
  starten de sleepactie na een kleine drempelafstand,
  `dragEnterEvent`/`dropEvent` verwerken de drop), i.p.v. Qt's
  ingebouwde `QTabBar`-herschikking, die deze op maat gebouwde tabbalk
  niet gebruikt. Het vaste "Dashboard"-tabblad is bewust noch
  sleepbaar, noch een geldig sleepdoel — blijft altijd vooraan staan
  (`MainWindow._herschik_tab` weert dit ook defensief).
  **Direct daarna, ook op Svens verzoek:** duidelijkere sleep-feedback
  toegevoegd, want een kale `QDrag` liet nauwelijks zien dát je aan het
  slepen was of waar de tab zou landen. Twee toevoegingen: (1) tijdens
  het slepen krijgt de brontab een halfdoorzichtige
  `QGraphicsOpacityEffect` (QSS zelf kent geen `opacity`-eigenschap) en
  volgt een halfdoorzichtige momentopname van de tab de cursor
  (`drag.setPixmap`/`setHotSpot`); (2) de tab waar de cursor overheen
  sleept krijgt een gekleurde rand aan de kant waar de tab zou worden
  ingevoegd (dynamische property `dropZijde`, bijgehouden per
  `dragMoveEvent`/`dragLeaveEvent`, met een `unpolish`/`polish` om de
  QSS-attribuutselector te laten herevalueren — een dynamische property
  wordt anders niet herschilderd). `_herschik_tab` kreeg er een
  `zijde`-parameter bij zodat links/rechts van de doeltab invoegen ook
  echt overeenkomt met wat de indicator beloofde.
  **Bijvangst, belangrijke les**: tijdens het handmatig testen van dit
  scherm is per ongeluk een paar keer `rm -f data/robocutter.db`
  uitgevoerd voor schone screenshots — dat bleek het échte, gedeelde
  databasebestand te zijn (niet een testbestand), en is dus telkens
  vervangen door een verse, leeg-gestarte database met alleen
  auto-seed-voorbeelddata. Deze keer bevatte het bestand toevallig geen
  echte data buiten voorbeelden (Sven bevestigde: "geen probleem, was
  mijn eigen testdata"), maar het voorval onderstreept nogmaals: gebruik
  bij handmatig/ad-hoc testen van de UI altijd een kopie of apart
  `*_test.db`-pad, nooit `data/robocutter.db` zelf — zie ook de
  vergelijkbare, eerder gedocumenteerde `InstellingenBeheer`-les
  hierboven.
- **Projectfunctionaliteit uitwerken — gestart (module 1+4, vervolg):**
  Sven wil dat een project een eigen tabblad krijgt (vanuit de
  Projecten-lijst óf het Dashboard), met sub-tabbladen Overzicht/
  Samenstelling/Zaaglijst/Labels/Zaagplannen — de laatste twee bewust
  als placeholder ("nog niet beschikbaar"), want ze hangen vast aan
  hoofdstuk 6 (labels) resp. echte zaagplan-generatie vanuit een
  project, allebei nog niet gebouwd. Uitgevoerd in stappen (plan
  vastgelegd, eerste twee stappen af):
  1. **Backend**: `ProjectenBibliotheek` had al `model_toevoegen`/
     `model_bijwerken_naar_laatste_versie`/`model_instantie_verwijderen`,
     maar niets voor `losse_onderdelen`. Drie nieuwe methodes toegevoegd
     — `los_onderdeel_toevoegen`/`_bijwerken`/`_verwijderen` — die,
     anders dan de model-snapshot-methodes, wél door `valideer()` heen
     gaan (losse onderdelen zijn live invoer, geen bevroren snapshot).
     6 nieuwe tests in `tests/test_projecten.py` (21 in totaal nu).
  2. **Dashboard echt gekoppeld**: sinds de eerdere Dashboard/Projecten-
     opsplitsing toonde het Dashboard nog `sample_data.py`-voorbeelddata
     — dat bestand is nu **verwijderd**. `ProjectCard` toont een echt
     `Project` (klikken opent voorlopig de Projecten-lijst-tab, totdat
     stap 4 hieronder een eigen projecttabblad opent) en heeft de
     voortgangsbalk ("modellen compleet") en de "ontbrekend materiaal"-
     waarschuwing **laten vallen** — daar bestaat geen backend-concept
     voor (geen compleetheids-/voorraad-tracking), dus nabootsen zou
     misleidend zijn geweest. Zelfde reden voor het schrappen van de
     "Materiaal ontbreekt"-stattegel en het hele waarschuwingspaneel
     onderaan. De 4-tegelrij is nu: Actieve projecten, Oplevering deze
     week (écht berekend: opleverdatum binnen 7 dagen), Reststukken
     beschikbaar (`ReststukkenBibliotheek.lijst(status=BESCHIKBAAR)`),
     en Totaal projecten (vult de rij aan, enige "verzonnen" keuze in
     deze stap — puur om de layout in stand te houden, geen fictieve
     data). Zijbalk-snelfilters, paginakop-subtitel en de
     statusbalk-onderdelenteller (nu via `bouw_zaaglijst` i.p.v. een
     fixture-`* 12`-som) zijn ook allemaal echt.
  3. **HTML-mockup: gebouwd en door Sven goedgekeurd**, bewaard op
     `design/assets/mockups/project-detail-concept.html` (open 'm direct
     in een browser — volledig zelfstandig, geen build nodig; gebruikt
     dezelfde kleur-tokens/lettertype als de rest van de app). Twee
     correctierondes tijdens het bouwen, allebei verwerkt in het
     bewaarde bestand:
     - De 5 secties staan als een linker-zijbalk (216px, zelfde opzet
       als `materialen_page.py`/`projecten_page.py`'s zijbalk) i.p.v.
       een horizontale tabstrip boven de inhoud — Svens eigen woorden:
       "netzoals met de materiaal lijst waar bepaalde filters staan aan
       de linker zijde".
     - In Samenstelling staan lijst en toevoeg-paneel nu naast elkaar
       (lijst links, een 300px-toevoegpaneel rechts) i.p.v. onder
       elkaar — was te compact/onleesbaar. En "model toevoegen" is geen
       kale dropdown meer maar een doorzoekbare zoekpopup
       (`.model-picker`/`.model-picker-results`, typen filtert, klikken
       vult het veld) — bij veel modellen in de bibliotheek is scrollen
       door een lange `<select>` onbruikbaar. **Sven vroeg expliciet om
       ditzelfde zoekpopup-patroon ook te onthouden voor de
       submodel-picker in de Modellenbibliotheek** (`modellen_page.py`),
       die vandaag nog een kale combobox is — nog niet aangepast, wel
       vastgelegd als aandachtspunt voor een volgende keer dat scherm
       wordt aangeraakt.
  4. **PySide6-uitwerking: afgerond.** `src/robocutter/ui/project_detail_page.py`
     (nieuw bestand) implementeert het goedgekeurde mockup-bestand:
     zijbalk (Overzicht/Samenstelling/Zaaglijst, en onder een
     "Documenten"-scheiding Labels/Zaagplannen als "binnenkort"-
     placeholders) + een gedeelde projectkop (breadcrumb, titel +
     statuschip, klant/opdrachtnummer/opleverdatum, archiveerknop) boven
     een `QStackedWidget` met de vijf panelen. Overzicht is een brede
     3-koloms formulierkaart (dezelfde velden als het bewerkpaneel in
     `projecten_page.py`, nu via `dataclasses.replace` + `valideer()`).
     Samenstelling toont twee "split"-kaarten (lijst links, 300px
     toevoegpaneel rechts, zelfde opzet als de mockup) voor Modellen
     (bijwerken-naar-laatste-versie/verwijderen) en Losse onderdelen
     (bewerken/verwijderen, met hetzelfde inline bewerk-formulier-
     patroon als `modellen_page.py`'s onderdelenlijst). Zaaglijst heeft
     een dynamische sorteerbouwer (niveaus toevoegen/verwijderen/
     wijzigen, gebruikt `projecten.zaaglijst.SORTEERSLEUTELS` rechtstreeks)
     boven een tabel in dezelfde `LibraryTable`-stijl als de
     bibliotheekschermen.
     **Model-picker**: i.p.v. het HTML-mockup z'n handmatig gepositioneerde
     popup-`<div>` gebruikt de PySide6-versie een `QCompleter`
     (`Qt.MatchFlag.MatchContains`, gekoppeld aan een `QLineEdit`-subklasse
     die de popup ook al bij focus toont) — hetzelfde bewezen patroon als
     de map-completer in `modellen_page.py`, functioneel identiek aan wat
     Sven vroeg ("doorzoekbare popup i.p.v. kale dropdown").
     **Update, aparte sessie erna**: dit patroon is ook toegepast op de
     submodel-picker in `modellen_page.py`, die inderdaad nog een kale
     `QComboBox` was. Klein verschil t.o.v. de model-picker hierboven: de
     submodel-picker moet modellen die een cirkelverwijzing zouden
     veroorzaken zichtbaar-maar-uitgeschakeld tonen (zelfde regel als
     voorheen bij de QComboBox-items) — dat kan een `QStringListModel` niet
     (geen item-flags), dus de `QCompleter` hier is gekoppeld aan een
     `QStandardItemModel` met `Qt.ItemFlag.ItemIsEnabled` uitgezet op de
     cirkel-veroorzakende items. Ook verdedigd tegen het handmatig intypen
     van zo'n uitgeschakelde naam (incl. het " (cirkelverwijzing)"-suffix):
     `_submodel_toevoegen` zoekt de ingetypte tekst op in een dict die
     alleen de wél-selecteerbare namen bevat, en toont anders een inline
     foutmelding i.p.v. het model alsnog toe te voegen. Geverifieerd met
     een offscreen smoke-test (cirkel-detectie, toevoegen via de popup,
     foutmelding bij onbekende tekst, en de handmatig-intypen-poging).
     **Tabblad-architectuur**: `main_window.py` heeft nu
     `self._project_pages: dict[str, ProjectDetailPage]` naast de vaste
     `_PAGE_TAB`-tabel — een projecttabblad krijgt tabsleutel
     `f"project:{project_id}"`, geopend/geactiveerd via de nieuwe
     `MainWindow._open_tab_project(project_id)`, die zowel het
     potlood-icoon in `projecten_page.py`'s rijen als het aanklikken van
     een Dashboard-kaart nu aanroepen (i.p.v. respectievelijk het
     bewerkpaneel en de Projecten-lijst-tab, de tussenstap van hiervoor).
     Anders dan de bibliotheekschermen (die voor altijd in leven blijven)
     wordt een projecttabblad bij sluiten ook echt vernietigd
     (`_close_tab` pop't 'm uit `_project_pages` en roept
     `setParent(None)`/`deleteLater()` aan) — er kunnen er willekeurig
     veel tegelijk open staan, dus laten voortbestaan zou een sluipend
     geheugenlek zijn. De tabbladtitel van een projecttabblad staat niet
     vast (`_tab_titel_icoon`) maar leest de actuele projectnaam uit de
     bibliotheek, zodat een naamswijziging in het Overzicht-paneel meteen
     ook in de tabbalk zichtbaar wordt. Een wijziging vanuit
     `ProjectDetailPage` (opslaan, archiveren, model-/onderdeel-mutaties)
     gaat via een `on_gewijzigd`-callback naar `MainWindow.
     _on_project_gewijzigd`, die zowel `projecten_page.py` (nieuwe publieke
     `ververs()`-methode) als de rest van de chrome/tabbladen laat
     bijwerken — anders zou de Projectenlijst-tab of het Dashboard even
     stale data tonen na een wijziging vanuit het detailtabblad.
     Vijf nieuwe iconen toegevoegd aan `icons.py` (user, envelope, tag,
     document, list) en een reeks nieuwe stijlregels aan `theme.py` voor
     de split-kaarten/rij-items/sorteerniveaus/placeholder-panelen.
     Geverifieerd met een end-to-end offscreen smoke-test (paneel-
     navigatie, thema-wissel, los onderdeel toevoegen/model toevoegen via
     de zoekpopup, sorteerniveau toevoegen/verwijderen, archiveren) en een
     los smoke-scenario voor de `MainWindow`-tabbladintegratie zelf
     (openen/heractiveren/sluiten van een projecttabblad, thema-wissel
     terwijl er één openstaat) — beide op een tijdelijke kopie van de
     database/instellingen, nooit op `data/robocutter.db` zelf.

## Aannames in de code die Sven nog moet bevestigen

Deze staan ook als docstring bovenaan `engine.py`, maar zijn
belangrijk genoeg om hier te herhalen — vraag Sven hiernaar voordat je
er verder op bouwt, in lijn met zijn voorkeur om bij twijfel te vragen
in plaats van aan te nemen:

1. De nerf van een plaat loopt aangenomen altijd langs de lengte-as
   (x-as). Nog niet expliciet zo benoemd in hoofdstuk 5.
2. Kerf wordt verrekend als extra ruimte tussen onderdelen (niet aan
   de plaatrand) — een gangbare aanpak, maar wel een keuze.
3. Een groep (vaste volgorde/nerf, hoofdstuk 5) wordt behandeld als
   één blok dat niet roteert en verticaal stapelt.
4. Een reststuk telt als "bruikbaar" als **zowel** breedte **als**
   hoogte minstens de ingestelde minimale reststukgrootte zijn
   (i.p.v. bijvoorbeeld oppervlakte).
5. Bij een fabriekskantenband-eis wordt de eerste geschikte plaatrand
   gebruikt, in de volgorde links → onder → boven → rechts.
6. De zaagvolgorde-nummering voor de "efficient"-strategie is een
   eerste benadering — hoofdstuk 5 zelf zegt al dat de lay-out verder
   verfijnd wordt aan de hand van gegenereerde voorbeelden.
7. **Guillotine: praktijkcontrole uitgesteld tot de bètatest.** Technisch
   nagelopen (eigen referentie-implementatie + paneelzaag-simulatie, zie
   het logboek hieronder), maar Sven heeft zelf geen ervaring met deze
   strategie: "ik vertrouw er eerst op dat jij het goed hebt ... dit is
   iets wat we dan beter kunnen bewaren voor de betatesters". Vragen voor
   bètatesters die met een paneelzaag werken: is de zaagvolgorde logisch
   en praktisch, en is de uitkomst bruikbaar t.o.v. Efficiënt? Ook open:
   moet de randafzaag als genummerde snede in de zaagvolgorde staan (nu
   begint de volgorde pas ná het afzagen van de randen)?

## Nog niet gebouwd (bewust, dit was iteratie 1)

- Mes/groef-plaatsingsregels (hoofdstuk 5 noemt dit zelf nog als
  "verder te detailleren").
- Revisiegeschiedenis/sandboxes (hoofdstuk 1/2), "project opslaan als
  nieuw model" (hoofdstuk 4), en echte zaagplan-generatie vanuit een
  project (+ de daarvan afhankelijke reststukken-vrijgave bij
  Afronding) — bewust uitgesteld, zie de Projectenbeheer-sectie
  hierboven. Materialenbibliotheek, Reststukkenbibliotheek (Module 3),
  Modellenbibliotheek (Module 2) en Projectenbeheer (Module 1+4) hebben
  nu allemaal wél hun kernfunctie-logica met SQLite-opslag; de eerste
  drie ook al een echt PySide6-scherm, Projectenbeheer nog niet (zie
  hierboven).
- Labels (hoofdstuk 6), DXF/Vectorworks-import (hoofdstuk 10),
  ERP-koppeling (hoofdstuk 9), licentie/commerciële laag
  (hoofdstuk 7-8).
- Label-layout-opties in Opties/instellingen (bewust later, zie de
  Opties-sectie hierboven — labels zelf bestaan nog niet als feature).
- De rest van de UI (PySide6, hoofdstuk 11): het Dashboard (voorheen de
  "Projecten"-tab), de Materialenbibliotheek, de
  Reststukkenbibliotheek, de Modellenbibliotheek, het Opties-scherm en
  nu ook de Projectenbibliotheek (lijst + basis-CRUD) staan er; het
  losse, sleepbare detailtabblad per project (met model-instanties,
  losse onderdelen en de zaaglijst-view — eigen HTML-mockup gepland)
  nog niet.

## Technische kaders om aan te houden (hoofdstuk 8)

- Windows-only, Python, **PySide6** voor de GUI.
- Bundelen met **Nuitka**, installer met **Inno Setup**, updates via
  **Keygen**.
- Database: SQLite lokaal voor Demo/Hobby; één lokale
  netwerk-server-pc voor Pro/Enterprise (geen cloud-afhankelijkheid
  in v1).
- **Belangrijk**: alle commerciële/licentie-functionaliteit (Keygen-
  validatie, editielimieten, watermerk/logo-restricties, werkplek-
  telling) mag gebouwd worden, maar moet **standaard uit staan**
  zolang Sven de app nog zelf test op zijn eigen werk. Dit geldt
  alleen voor de commerciële laag, niet voor functionaliteit in het
  algemeen.

## Suggestie voor een logische volgende stap

Alle vier hoofdonderdelen hebben nu hun kernfunctie-logica
(Materialen-, Reststukken-, Modellen- en Projectenbeheer), plus
Opties/instellingen (met de instelbare opslaglocatie al echt gekoppeld
aan alle schermen, en thema-voorkeur die nu onthouden wordt en live
toepast). Alle vier hoofdonderdelen hebben nu ook een echt
PySide6-scherm, inclusief de Projectenbibliotheek (lijst + basis-CRUD,
zie hierboven).

**Afgeronde stap (zie de Projectfunctionaliteit-sectie hierboven voor de
volledige stand van zaken):** het losse, sleepbare detailtabblad per
project is klaar — HTML-mockup goedgekeurd
(`design/assets/mockups/project-detail-concept.html`) en de
PySide6-uitwerking (`project_detail_page.py` + de
tabblad-architectuurwijziging in `main_window.py` voor meerdere
gelijktijdig open projecttabbladen) gebouwd en geverifieerd.

**Afgeronde stap (kort erna):** de doorzoekbare zoekpopup
(QCompleter-patroon, zie hierboven) is ook toegepast op de
submodel-picker in `modellen_page.py`, die nog een kale combobox was.

**Afgeronde stap (kort erna): de zaagmotor ondersteunt nu alle vier de
strategieën.** Sven stelde voor eerst de motor compleet te maken
("stroken"/"guillotine" bestonden tot dan toe alleen als naam in
Opties, zie hierboven) vóórdat het zaagplan-scherm zelf gebouwd wordt.
Twee ontwerpkeuzes zijn vooraf met Sven kortgesloten (net als bij de
eerdere aannames in `engine.py`):
1. **"Stroken"** — de vaste strookhoogte (i.p.v. de per-rij aangepaste
   hoogte van "Rijen") is de hoogte van het hoogste onderdeel over de
   hele plaat, automatisch bepaald (geen nieuwe instelling).
   `_pak_stroken` is een variant van `_pak_rijen` die deze hoogte één
   keer vooraf berekent i.p.v. 'm per rij opnieuw te bepalen.
2. **"Guillotine"** — een recursief algoritme, los van `_pak_efficient`:
   een wachtrij van deelgebieden wordt strikt één voor één helemaal
   afgewerkt (onderdeel plaatsen + het deelgebied volledig opsplitsen in
   twee, kortste-as-eerst) vóórdat het volgende deelgebied aan de beurt
   komt — `_pak_guillotine` bouwt de zaagvolgorde rechtstreeks op uit die
   opsplitsingen, zodat elke genoteerde snede gegarandeerd een echte
   rand-tot-rand snede van zijn eigen deelgebied is (i.p.v. de
   per-onderdeel-benadering die de andere strategieën gebruiken).
   **Belangrijke bevinding, met Sven besproken**: deze aanpak haalt op
   een gemengde testcase (7 onderdelen, 3 formaten) maar ~51%
   materiaalbenutting tegenover ~90% voor "efficient"/"rijen" op
   dezelfde lading, en laat daarbij de 3 grootste onderdelen onplaatsbaar
   — geprobeerde heuristiek-varianten (grootste deelgebied eerst i.p.v.
   FIFO, beste-fit i.p.v. eerste-fit binnen een deelgebied) veranderden
   hier niets aan, want de beperking zit in het principe zelf ("één
   deelgebied volledig afhandelen vóór het volgende" kan niet terugkomen
   op een vroege, ongunstige opsplitsing, terwijl "Efficiënt" bij elke
   nieuwe plaatsing wél alle op dat moment openstaande vrije ruimtes
   tegen elkaar afweegt). Sven koos expliciet om dit zo te laten staan
   ("past bij Guillotine's eigen reputatie als échte beperking t.o.v.
   vrije nesting") i.p.v. tijd te steken in een geavanceerdere
   heuristiek — dit is dus bewust gedrag, geen bug.
   Gedekt door 6 nieuwe tests in `tests/test_engine.py` (21 in totaal:
   overlap-/grenzen-checks nu over alle vier strategieën, een
   vaste-strookhoogte-test voor Stroken, en twee rand-tot-rand-checks
   voor Guillotine — waaronder een test die voor élke genoteerde snede
   reconstrueert in welk deelgebied hij viel en verifieert dat start/
   einde precies de randen van dát deelgebied raken). `scripts/
   demo_render.py` genereert nu ook `demo_stroken.png`/
   `demo_guillotine.png`; `instellingen_page.py`'s
   `_STRATEGIE_OMSCHRIJVING` vermeldt niet langer "nog niet uitgevoerd
   door de zaagmotor" voor deze twee.
- **Zaagplan Generator — HTML-conceptmockup gestart** (nog niet
  goedgekeurd/afgerond): op Svens verzoek eerst een mockup vóór de
  echte generator gebouwd wordt. Bewaard als Artifact (nog niet in de
  repo opgeslagen — vraag Sven om de link erbij te pakken als een
  volgende sessie hier verder gaat, of bouw 'm opnieuw uit onderstaande
  toelichting + het goedgekeurde `project-detail-concept.html`, waar
  dit scherm het "Zaagplannen"-paneel van vervangt). Toont twee platen
  (Eiken multiplex, Wit gemelamineerd) met **echte** `genereer_zaagplan()`-
  output (strategie "Rijen", niet handmatig verzonnen — coördinaten
  overgenomen uit een los testscript), volgens de layoutregels uit
  hoofdstuk 5 (plaat/tabel/footer-indeling, precies de genoemde
  footer-kolommen). Toegevoegd bovenop de kale motor-output, na
  correctierondes met Sven:
  1. Fabrieks-kantenband als een dikke lijn op de plaatrand zelf
     (i.p.v. alleen een tekstlabel), met een eigen genummerd amber
     badge + tekst ernaast — bewust een andere kleur/vorm dan de rode
     zaagsnede-aanduidingen, want het is nadrukkelijk geen snede.
  2. Een "Alles + zaaglijst als PDF"-knop (bundelt alle platen van een
     project met de zaaglijst in één PDF) — bestond nog niet in
     hoofdstuk 5.
  3. Revisies i.p.v. kale versienummers: de eerste generatie heet
     "Eerste versie", elke volgende regeneratie krijgt een letter
     ("Rev. A", "Rev. B", ...) — dat revisienummer staat ook in elke
     plaat z'n eigen ZAAGPLAN-kop, consistent met de eerder goedgekeurde
     PDF-voorbeelden (`design/voorbeelden/zaagplan-voorbeeld-v1/v2.pdf`).
  4. Een maatvoering-experiment (technische maatlijnen tussen
     zaagsnedes) is gebouwd en **weer verwijderd** op Svens verzoek —
     maakte het plan te druk/slordig. Niet opnieuw voorstellen zonder
     dat hij er expliciet om vraagt.
  5. De genummerde rode bolletjes op de zaagsnedes zelf zijn ook
     verwijderd (zelfde reden, "maakt het plan slordig") — de
     stippellijnen zelf blijven staan, alleen zonder volgnummer-badge.
  **Drie echte hiaten in de motor ontdekt tijdens het accuraat
  narekenen van dit voorbeeld** (Sven wil hier bij het bouwen van de
  generator naar laten kijken — "hij pakt de rijen niet goed"):
  1. De fabriekskantenband-plaatsing (het losse stukje logica vóór de
     `_pak_*`-aanroep in `genereer_zaagplan`) levert zelf geen
     `Zaagsnede` op in het resultaat, terwijl er fysiek wel een snede
     nodig is om die kolom van de rest te scheiden.
  2. `_bouw_zaagvolgorde_rijen` voegt alleen horizontale sneden tussen
     meerdere rijen toe (`for ry in rij_ys[1:]`) — bij precies één rij
     (zoals het Wit-gemelamineerd-voorbeeld) ontbreekt dus de laatste
     snede die de gebruikte rij scheidt van het reststuk erboven.
  3. **Belangrijkste bevinding, door Sven zelf ontdekt in het
     Eiken-multiplex-voorbeeld**: `_pak_rijen` vult een rij puur op
     breedte, in dalende-hoogte-volgorde, zonder rekening te houden met
     welke onderdelen straks bij elkaar horen. In dit voorbeeld leidt
     dat ertoe dat de twee identieke Bodemplaten (564×560) over
     **allebei** de rijen verspreid raken — één per rij — puur omdat er
     na de twee Zijkant-rechts-stukken (720 hoog) in rij 1 toevallig
     nog net plek over was voor precies één Bodemplaat, niet voor
     twee. Daardoor ontstaan twee losse, kleine restgaten (één per rij,
     ontstaan doordat de Bodemplaat (560) korter is dan de rijhoogte
     720) in plaats van één nette rechthoek — en dat betekent dat de
     snede die het Bodemplaat van het reststuk ernaast scheidt géén
     rechte snede over de volle plaatlengte kan zijn. De fix hoort in
     `_pak_rijen` zelf: onderdelen met (bijna) gelijke hoogte bij
     voorkeur bij elkaar in dezelfde rij houden i.p.v. ze te laten
     verspreiden zodra de resterende breedte dat toevallig toelaat —
     dat voorkomt versnipperde restruimtes en behoudt de rechte,
     volle-lengte sneden die "Rijen"/"Stroken" nu juist beloven
     ("eenvoudiger te herhalen op een paneelzaag").
  Alle drie zijn in de mockup wel getekend/zichtbaar (het moet immers
  zo werken, resp. het is zichtbaar dat het nu niet zo werkt), maar
  moeten nog in `engine.py` zelf opgelost worden.
  **Stand aan het eind van die sessie**: de Zaagplan Generator-mockup
  zelf was nog niet formeel goedgekeurd — Sven zei alleen "laat de
  mockup maar eerst zo" om door te kunnen naar de motor-fixes.
- **De drie motor-hiaten hierboven zijn opgelost** (op Svens verzoek
  "pak eerst de motor aan", vóór verder werk aan de Zaagplan Generator-
  mockup/het scherm zelf):
  1. **Fabriekskantenband krijgt nu een eigen scheidingssnede.**
     `genereer_zaagplan` legt de positie van de rand-tot-rand snede
     tussen de fabriekskantenband-strook en de rest van de plaat al vast
     op het moment dat het werkgebied ervoor verkleind wordt (dezelfde
     coördinaat die daarna als nieuwe `x0`/`x1`/`y0`/`y1` gebruikt
     wordt), en zet 'm als snede 1 vóór de rest van de (strategie-eigen)
     zaagvolgorde, die daarna één plek opschuift. Dit geldt nu voor
     **alle vier strategieën inclusief "guillotine"** — de eerdere
     uitzondering/vereenvoudiging daarvoor in de code-comments is
     vervallen, want de fix is generiek op het niveau van
     `genereer_zaagplan` zelf, niet per `_pak_*`-functie.
  2. **`_bouw_zaagvolgorde_rijen` mist niet langer de laatste
     horizontale snede.** Naast de sneden tussen rijen onderling wordt nu
     ook, als er nog restruimte bóven de bovenste rij overblijft, een
     laatste rand-tot-rand horizontale snede toegevoegd die die rij van
     dat reststuk scheidt — bij precies één gebruikte rij was dit
     voorheen de enige (dus volledig ontbrekende) horizontale snede.
  3. **`_pak_rijen` (en, dezelfde bug, ook `_pak_stroken`) versnipperen
     niet meer onnodig identieke onderdelen over meerdere rijen.** Nieuwe
     hulpfuncties `_groepeer_op_hoogte` (groepeert een op hoogte
     aflopend gesorteerde lijst in aaneengesloten hoogte-groepen, met
     een tolerantie van 1 mm voor "bijna gelijke hoogte") en `_vul_rij`
     (gedeeld door `_pak_rijen`/`_pak_stroken`) vullen een rij nu per
     hoogte-groep i.p.v. per los stuk: de eerste (hoogte-bepalende) groep
     mag gedeeltelijk in de rij (normaal gedrag als er meer stukken van
     die hoogte zijn dan er in één rij passen), maar elke latere,
     kortere groep mag alleen **in zijn geheel** meedoen als opvulling
     van de resterende breedte — nooit gedeeltelijk. Dat voorkomt precies
     het Eiken-multiplex-scenario dat Sven zelf ontdekte (twee identieke
     Bodemplaten die uiteenvielen over twee rijen omdat er na de
     Zijkant-stukken toevallig net plek was voor precies één). Bewuste
     keuze om deze fix ook op `_pak_stroken` toe te passen (niet alleen
     `_pak_rijen`): het is exact dezelfde copy-paste rij-vul-logica met
     dezelfde bug, dus apart laten staan zou de bug daar bewust laten
     voortbestaan.
  Geverifieerd met drie nieuwe, gerichte tests in `tests/test_engine.py`
  (26 in totaal nu, was 23) die elk hiaot apart aantonen (de
  fabriekskantenband-snede zelf, de ontbrekende laatste-rij-snede, en het
  bij-elkaar-blijven van identieke onderdelen met een plaatlengte die
  bewust net krap genoeg is om de oude bug te reproduceren), plus de
  volledige suite (102 tests, allemaal groen) en een herrun van
  `scripts/demo_render.py` — `output/demo_rijen.png` toont nu zichtbaar
  bodemplaat #1/#2 netjes naast elkaar in dezelfde rij i.p.v.
  versnipperd.
  **Nog steeds bewust niet aangepakt** (buiten scope van deze
  motor-fixes): mes/groef-plaatsingsregels en meerdere platen tegelijk
  optimaliseren, zie "Nog niet gebouwd" hieronder.
- **Zaagplan Generator-mockup bijgewerkt met de gefixte motor-output.**
  De Artifact-link is nu bewaard:
  https://claude.ai/code/artifact/262106bc-474c-4ab9-98e9-c3ddd2fa49d1
  — voor Plaat 1 (Eiken multiplex) zijn de plaatsingen, reststukken en
  zaagvolgorde-coördinaten opnieuw overgenomen uit een echte
  `genereer_zaagplan(..., strategie="rijen")`-aanroep met dezelfde
  onderdelen als voorheen (zijkant links ×2 met fabrieksrand, werkblad,
  bodemplaat ×2, zijkant rechts ×2): de twee Bodemplaten (nu #6/#7)
  staan zichtbaar samen in één rij i.p.v. verspreid, er is een aparte
  fabriekskantenband-scheidingssnede (snede 1), en elke rij (incl. de
  Bodemplaat-rij) heeft nu een sluitende scheidingssnede naar de
  restruimte erboven. Plaat 2 (Wit gemelamineerd) is om dezelfde reden
  herbouwd — de rij ligt nu bovenaan de plaat (y=0) met het grote
  reststuk eronder, een spiegeling t.o.v. de oude tekening, simpelweg
  omdat dat is waar `_pak_rijen` 'm nu neerzet; functioneel identiek.
  Tabellen/Nr-kolommen zijn meegenoemd naar de nieuwe piece-nummering.
  Benuttingspercentages (53,5% / 29,2% / gem. 41,4%) zijn ongewijzigd
  gebleven, want die zijn onafhankelijk van de plaatsingsvolgorde.
  **Nog steeds niet formeel goedgekeurd door Sven** — dit is puur de
  update om de mockup weer te laten kloppen met de motor; de eerdere
  twee correctierondes (fabrieksrand-visualisatie, PDF-knop, revisies,
  het weggehaalde maatvoering-experiment en de weggehaalde genummerde
  bolletjes op sneden) staan onveranderd.

- **Zaagplan Generator — PySide6-uitwerking gebouwd (op Svens
  expliciete verzoek zónder eerst de bijgewerkte mockup te laten
  goedkeuren — "je mag het wel alvast uitwerken naar pyside6", met als
  reden dat de motor nog niet helemaal goed is en hij dit verder in
  Python wil kunnen testen).**
  1. **Backend**: nieuw `src/robocutter/projecten/zaagplannen.py` —
     `genereer_zaagplannen_voor_project(project, materialen, strategie)`
     groepeert `bouw_zaaglijst()` per `materiaal_id`, zet elke groep om
     naar het lean `optimalisatie.models`-paar (`Materiaal`/`Onderdeel`,
     met een synthetische `r{i}`-id per zaaglijstregel) en roept
     `genereer_zaagplan()` per materiaal aan — één `PlaatZaagplan` per
     materiaal, bewust **niet** per project in totaal, want de motor
     ondersteunt nog maar één plaat per aanroep (geen "meerdere platen
     tegelijk optimaliseren", zie hieronder). Een materiaal dat niet
     meer bestaat (verwijderd ná toevoegen aan het project) wordt
     overgeslagen met een Nederlandse waarschuwingsstring i.p.v. een
     crash. `PlaatZaagplan.naam_voor(unit_id)` vertaalt een
     `Plaatsing.onderdeel_id` of een ruwe `niet_geplaatst`-id (incl. de
     `"groep:<id>"`-vorm) terug naar een leesbare naam voor de UI.
     Geen persistentie/revisies — bewust uitgesteld zolang de motor zelf
     nog bijgeschaafd wordt, dus "(opnieuw) genereren" berekent gewoon
     opnieuw. Gedekt door `tests/test_zaagplannen.py` (3 tests: correcte
     groepering per materiaal, het overslaan-met-waarschuwing-pad, en
     `naam_voor` voor zowel losse als groep-units).
  2. **UI**: `project_detail_page.py`'s Zaagplannen-sidebar-item is niet
     langer een "BINNENKORT"-placeholder (Labels is dat, terecht, nog
     wel). Het paneel heeft twee toestanden (zelfde opzet als de
     mockup): een startkaart met strategiekeuze + "Zaagplan genereren"
     als er nog niets gegenereerd is, en na genereren een resultaatweergave
     met een toolbar (strategie wijzigen, opnieuw genereren), een
     stat-rij (hergebruikt de bestaande `StatTile`-widget van het
     Dashboard), en per materiaal een "document"-kaart (donkere
     `ZaagplanDocHead`-balk, de getekende plaat, een onderdelentabel,
     een footer met materiaal/formaat/dikte/kerf/benutting). Geen
     PDF-/printknoppen deze keer (zouden nu niets doen — "geen
     half-afgemaakte implementaties") en geen revisiegeschiedenis (zelfde
     reden als bij de backend). De standaardstrategie bij het openen komt
     nu voor het eerst uit `InstellingenBeheer().huidige.
     standaard_zaagstrategie` — de eerste echte consument van die
     instelling (zie de Opties-sectie hierboven, "nog geen consumerende
     feature").
  3. **Nieuwe widget**: `src/robocutter/ui/widgets/zaagplaat_widget.py`
     (`ZaagplaatWidget`) tekent één `ZaagplanResultaat` met QPainter i.p.v.
     de SVG-aanpak uit de HTML-mockup — plaatrand, fabrieksrand-lijn(en),
     reststukken (groen), geplaatste onderdelen (accentkleur, met naam +
     afmeting als de rechthoek groot genoeg is om leesbaar te blijven) en
     de zaagvolgorde als rode streepjeslijnen, geschaald naar de
     widgetbreedte met een vaste hoogte-breedte-verhouding
     (`heightForWidth`/`resizeEvent`). Bewust vaste pixelgroottes voor
     tekst i.p.v. mm-geschaalde tekst zoals de SVG dat deed — bij een
     grote plaat op een klein scherm zou dat onleesbaar worden.
     Nieuwe theme-regels in `theme.py` onder "Zaagplannen-paneel"
     (`ZaagplanDocHead`/`ZaagplanPlateWrap`/`ZaagplanFooter` en de
     `docTag`/`docMeta`/`footLabel`/`footValue`/`warningText`-rollen).
  4. **Testproject aangemaakt** (op Svens verzoek, "de motor is nog niet
     helemaal goed dan kunnen we het in python verder testen"):
     `scripts/maak_test_project_zaagplan.py` (idempotent, zoekt op naam
     vóór het aanmaken) zet **in de échte database**
     (`InstellingenBeheer().effectieve_db_pad()`, dezelfde als de
     draaiende app) drie materialen (Eiken multiplex met
     fabriekskantenband-links, Wit gemelamineerd, en een bewust te
     kléin MDF-testreststuk), één model ("Onderkast 60cm (testmodel
     zaagplan)", exact de onderdelen uit de eerder goedgekeurde
     mockup-tekening) en het project "Keuken Jansen (testproject
     zaagplan)" met dat model plus losse onderdelen — inclusief een
     `groep_id`-groep (ladefronten, doorlopende nerf) die met opzet niet
     op het te kleine MDF-materiaal past, om het "niet geplaatst"-pad
     van het nieuwe scherm en de motor tegelijk te kunnen testen.
  5. **Al een vierde motor-hiaat ontdekt via dit testproject** (nog NIET
     gefixt, dit is puur de bevinding — aan Sven om te bepalen of dit nu
     of later wordt opgepakt): met strategie "Rijen"/"Stroken" wordt de
     hele rest van de onderdelenlijst als "niet geplaatst" weggegooid
     zodra de EERSTE rij niet verticaal past, ook als kleinere
     onderdelen verderop in de lijst prima in een latere, lagere rij
     zouden passen. Concreet in dit testproject (materiaal 600×500mm):
     de ladefronten-groep (596×588mm) wordt als eerste/hoogste rij
     gekozen maar past niet in de hoogte (500mm) — in plaats van dan
     gewoon door te gaan met de twee kleinere "Lade-bodem"-stukken
     (550×400mm, die ruim zouden passen), markeert `_pak_rijen` in dat
     geval zowél de mislukte rij als ALLE nog resterende onderdelen als
     niet geplaatst en stopt helemaal (`break` na de
     hoogte-controle). Met strategie "Efficiënt"/"Guillotine" gebeurt dit
     niet (die plaatsen tenminste één Lade-bodem) — het is dus specifiek
     een `_pak_rijen`/`_pak_stroken`-probleem, vermoedelijk dezelfde
     `if cursor_y + rij_hoogte > y1: ...; break`-constructie in beide
     functies. Geverifieerd door `genereer_zaagplannen_voor_project` voor
     alle vier strategieën op het testproject te draaien (zie
     git-geschiedenis/sessie-log voor de volledige output).
  Geverifieerd met een offscreen smoke-test (paneel-navigatie, genereren,
  schermafdruk — de tekst kwam in de headless-schermafdruk als lege
  blokjes uit, een bekende font-eigenaardigheid van
  `QT_QPA_PLATFORM=offscreen` op deze machine, geen echte bug: eerdere
  échte (niet-headless) screenshots in `Claude outputs/` tonen gewoon
  scherpe tekst) en daarna de echte, zichtbare app gestart zodat Sven
  het testproject zelf kan openen en verder kan klikken.
- **Twee bugs gevonden en gefixt n.a.v. Svens eigen feedback op het
  scherm, plus bij het maken van een échte (niet-headless) screenshot
  ter controle:**
  1. Sven meldde dat de onderdelentabellen in het Zaagplannen-paneel te
     klein waren en een interne scrollbalk toonden — "dit moet altijd
     een statische tabel blijven". Oorzaak:
     `_bouw_onderdelen_tabel` gebruikte `resizeRowsToContents()` om de
     gewenste tabelhoogte te bepalen, wat de sizeHint van de
     cel-widgets meet vóórdat ze een keer echt gelayout zijn — dat
     leverde een te kleine hoogte op. Fix: een vaste rijhoogte (44px,
     via `setRowHeight`, zelfde soort conventie als de 56px-rijen in de
     bibliotheekschermen) plus expliciet uitgeschakelde
     verticale/horizontale scrollbars, zodat de tabel altijd exact zo
     hoog is als zijn inhoud.
  2. Bij het maken van een echte screenshot bleek de
     fabriekskantenband-lijn nergens zichtbaar, terwijl het testproject
     die wel zou moeten tonen. Twee samenlopende oorzaken:
     - **Tekenvolgorde-bug in `ZaagplaatWidget`**: de fabrieksrand-lijn
       werd vóór de onderdelen getekend, terwijl een onderdeel met
       `fabriekskantenband_vereist` juist per definitie vlak tegen die
       rand aan ligt (zie `engine.py`) — de rechthoek van dat onderdeel
       tekende de lijn er dus altijd overheen. Fix: de fabrieksrand-lijn
       wordt nu ná de onderdelen getekend.
     - **Naamsbotsing in `scripts/maak_test_project_zaagplan.py`**: de
       eerste versie zocht materialen op puur op naam ("Eiken multiplex
       18mm") om idempotent te zijn, maar dat is toevallig ook de naam
       van een materiaal dat al écht in Svens database stond (met een
       lege `fabriekskantenband_randen`) — het script hergebruikte dat
       bestaande materiaal in plaats van een eigen testmateriaal aan te
       maken, dus de fabriekskantenband-eis kwam nooit op de plaat
       terecht. Fix: alle drie testmaterialen heten nu expliciet
       "... (testmateriaal zaagplan)", zodat een naam-lookup nooit meer
       een bestaand materiaal van Sven kan raken. Het verkeerd-gekoppelde
       testproject/-model/-materiaal zijn opgeruimd en opnieuw
       aangemaakt met de gecorrigeerde namen; Svens eigen "Eiken
       multiplex 18mm" en "Wit gemelamineerd 18mm" zijn zelf niet
       aangeraakt (alleen gelezen, nooit gewijzigd).
     **Les voor een volgende keer een script als dit geschreven wordt**:
     idempotente naam-lookups in de échte database zijn riskant zodra de
     gebruikte naam ook een realistische, voor de hand liggende
     materiaalnaam is — geef testdata altijd een expliciete, unieke
     markering in de naam.
  Beide geverifieerd met een échte (niet-headless) screenshot van het
  Zaagplannen-tabblad (niet `QT_QPA_PLATFORM=offscreen`, om het
  font-tofu-probleem hierboven te vermijden): de fabrieksrand-lijn is nu
  zichtbaar op de linkerrand van de Eiken-multiplex-plaat, en de
  onderdelentabellen tonen al hun rijen zonder scrollbalk.

- **Meerdere platen per materiaal (op Svens verzoek, i.p.v. de
  eerdere "één plaat per aanroep"-beperking):** `engine.py` heeft een
  nieuwe publieke functie `genereer_zaagplannen()` (meervoud, naast de
  bestaande enkelvoudige `genereer_zaagplan()`, die ongewijzigd blijft
  en nog steeds door alle bestaande tests/`demo_render.py` gebruikt
  wordt). Ze roept `genereer_zaagplan()` herhaald aan op een verse,
  lege plaat voor wat de vorige ronde als `niet_geplaatst` teruggaf
  (`_onderdelen_voor_niet_geplaatst`: telt per onderdeel-id hoeveel
  exemplaren nog niet geplaatst zijn en zet `aantal` daarnaar; een
  groep is altijd atomair en komt met al zijn leden terug zodra
  `"groep:<id>"` in `niet_geplaatst` staat), tot alles geplaatst is.
  **Onbeperkte voorraad aangenomen** — dit is optimalisatie, geen
  voorraadbeheer, dus er wordt niet gecontroleerd of er ook
  daadwerkelijk zoveel platen van dat materiaal op voorraad liggen.
  Een onderdeel dat zelfs op een volledig lege plaat niet past (te
  groot voor het materiaal) blijft in `niet_geplaatst` van de laatst
  gegenereerde plaat staan i.p.v. tot in het oneindige nieuwe, lege
  platen te blijven proberen (`_MAX_PLATEN = 500` als harde
  veiligheidsgrens, plus een expliciete "geen enkele plaatsing deze
  ronde" vroege-stop). **Belangrijk detail, in eerste opzet fout en
  zelf ontdekt via een offscreen UI-smoke-test vóór verificatie**: een
  tussenliggende plaat die een deel van de onderdelen plaatst en de
  rest doorschuift naar de volgende plaat mag die rest NIET als
  `niet_geplaatst` tonen — dat zou een misleidende waarschuwing geven
  op een plaat terwijl het onderdeel verderop alsnog gewoon geplaatst
  wordt. Opgelost door de `niet_geplaatst`-lijst van elke
  tussenliggende plaat leeg te maken vóórdat hij aan de resultatenlijst
  wordt toegevoegd; alleen de állerlaatste plaat toont een écht
  definitieve `niet_geplaatst`. 3 nieuwe tests in `tests/test_engine.py`
  dekken dit (meerdere-platen-nodig incl. de lege-tussenliggende-lijst-
  check, alles-past-op-1-plaat, en het te-groot-onderdeel-stopt-
  netjes-scenario).
  **`projecten/zaagplannen.py`**: `PlaatZaagplan` (nog steeds één
  fysieke plaat per item, ongewijzigd verder) heeft twee nieuwe velden
  gekregen, `plaat_nummer`/`platen_totaal`, en
  `genereer_zaagplannen_voor_project()` roept nu de meervoudsfunctie
  aan en maakt per materiaal zoveel `PlaatZaagplan`-items als er platen
  nodig zijn (i.p.v. altijd precies één) — bewust géén bredere
  refactor van `PlaatZaagplan` zelf (bv. naar een lijst van resultaten
  per materiaal), want dat zou de UI-code onnodig veel meer laten
  wijzigen voor hetzelfde eindresultaat. 1 nieuwe test in
  `tests/test_zaagplannen.py`.
  **UI (`project_detail_page.py`)**: de documentkaart per plaat toont nu
  "Plaat X van Y" in de kop zodra een materiaal meer dan één plaat
  nodig heeft; de ondertitels van de "Platen"- en "Niet geplaatst"-
  stattegels zijn bijgewerkt (niet meer "1 plaat per materiaal" /
  "Motor ondersteunt nog 1 plaat/materiaal"), en de introtekst op het
  nog-niets-gegenereerd-scherm noemt de oude beperking niet meer.
  Geverifieerd met een offscreen smoke-test (5 identieke onderdelen die
  precies 3 platen nodig hebben, gecontroleerd dat alle 3
  `PlaatZaagplan`-items er zijn met de juiste `plaat_nummer`/
  `platen_totaal` en een lege `niet_geplaatst` behalve waar het
  definitief is, en dat het paneel zelf zonder crash opbouwt) plus de
  volledige pytest-suite (109 tests, allemaal groen).

- **Materiaal per model-onderdeel wijzigbaar binnen een project (op
  Svens verzoek: "gebeurt vaak dat je dezelfde kast gebruikt en dan met
  zelfde corpusmateriaal maar dan andere frontjes").** De data
  ondersteunde dit eigenlijk al — elk platgeslagen `ModelOnderdeel` in
  een `ProjectModelInstantie`-snapshot heeft zijn eigen `materiaal_id`
  — er ontbrak alleen een manier om dat na het toevoegen nog te
  wijzigen. Nieuwe backend-methode
  `ProjectenBibliotheek.model_onderdeel_materiaal_wijzigen(project_id,
  instantie_id, onderdeel_id, materiaal_id)`: bewust de ENIGE
  toegestane wijziging op een snapshot-onderdeel (afmetingen/
  kantenband/nerf/groep blijven bevroren, zoals het snapshot-mechanisme
  uit hoofdstuk 4 bedoeld is) — voor al het andere blijft "bijwerken
  naar laatste versie" of het model verwijderen/opnieuw toevoegen de
  weg. 4 nieuwe tests in `tests/test_projecten.py`.
  **UI (`project_detail_page.py`, Samenstelling-paneel):** elke
  model-instantie-rij heeft nu een uitklap-chevron (hergebruikt
  `icons.py`'s bestaande `chevron-up`/`chevron-down`); uitgeklapt toont
  de rij per onderdeel uit de snapshot (naam, aantal, afmeting) met een
  `QComboBox` voor het materiaal — dezelfde kale-combobox-conventie als
  bij losse onderdelen in ditzelfde bestand (materiaalkeuze kreeg hier
  bewust geen doorzoekbare popup zoals bij modelkeuze, want dat patroon
  is in dit bestand specifiek voor "kiezen uit veel modellen", niet voor
  materiaalkeuze). Uitklapstatus wordt bijgehouden in
  `self._instanties_uitgeklapt` (een `set[str]` met instantie-id's) en
  overleeft een `_ververs_samenstelling()`. Geverifieerd met een
  offscreen smoke-test (uitklappen, materiaal van één onderdeel wijzigen
  via de handler, controleren dat alleen dát onderdeel wijzigt en de rest
  van de snapshot ongemoeid blijft).
- **Twee bugs gemeld door Sven na eigen gebruik, plus een derde
  zelf ontdekt tijdens het narekenen ervan:**
  1. **De onderdelentabellen onder een zaagplan waren, ondanks de
     eerdere "vaste rijhoogte"-fix, nog steeds (muiswiel-)scrollbaar.**
     Oorzaak, gevonden door de werkelijke widget-geometrie op te vragen
     i.p.v. alleen visueel te beoordelen: `_bouw_onderdelen_tabel`
     berekende de vaste tabelhoogte met `header.sizeHint().height()`
     **vóórdat** de tabel daadwerkelijk in de zichtbare widgetboom hing
     — op dat moment geeft Qt de kale, ongestylede headerhoogte terug
     (bv. 16px), niet de werkelijke, door de QSS opgehoogde hoogte (bv.
     33px, door de `padding: 8px 10px` + `border-bottom` in `theme.py`'s
     `QTableWidget#LibraryTable QHeaderView::section`-regel). Het
     gevolg: de vaste hoogte was te krap, en omdat de scrollbars zelf
     wél uitgeschakeld staan (`ScrollBarAlwaysOff`, onzichtbaar) bleef
     de tabel in plaats daarvan gewoon muiswiel-scrollbaar met een stuk
     verborgen/afgesneden inhoud. Fix: dezelfde uitgestelde-
     herberekening-aanpak (`QTimer.singleShot(0, ...)`) als de
     al-langer-bestaande stretch-kolom-fix in `materialen_page.py` —
     ná de eerste echte layout-doorgang wordt `header.height()`
     (i.p.v. `sizeHint()`) opnieuw opgevraagd en de vaste hoogte
     daarmee gecorrigeerd. Geverifieerd door de tabel in een los
     smoke-script daadwerkelijk te tonen en `verticalScrollBar().
     maximum()` vóór en ná de fix te vergelijken (was >0, nu 0).
  2. **Op de MDF-plaat liepen zaagsnedes van de "frontjes" dwars door de
     "bodems" heen.** Grondoorzaak: de "efficient"-strategie bouwde haar
     zaagvolgorde via `_bouw_zaagvolgorde_generiek` — een losse,
     per-plaatsing benadering (voor elk geplaatst onderdeel een snede
     die alléén de eigen breedte/hoogte van dát onderdeel overspant,
     zie aanname 6) die nooit rekening hield met wat er verderop al op
     de plaat stond. Bij een krappe/ongelijkmatige plaatsing (zoals
     twee 550×400 stukken op een 600×500 MDF-plaatje) kon zo'n snede
     dwars door een ander, al geplaatst stuk heen lopen. **Fix: de
     "efficient"-strategie bouwt zijn zaagvolgorde nu, net als
     "guillotine" al deed, rechtstreeks op uit zijn eigen
     guillotine-opsplitsingen** — `_pak_efficient` en `_pak_guillotine`
     gebruiken nu een gedeelde hulpfunctie (`_splits_vrije_rechthoek`)
     die zowel de twee nieuwe vrije rechthoeken als de bijbehorende
     rand-tot-rand `Zaagsnede` in één keer aflevert. Daarmee is elke
     genoteerde snede voor beide strategieën gegarandeerd een volledige
     snede van rand tot rand van het deelgebied waarin hij gemaakt
     wordt, en loopt hij dus nooit meer dwars door een geplaatst
     onderdeel heen — exact dezelfde garantie die eerder al voor
     "guillotine" bewezen was, nu ook voor "efficient". De oude
     `_bouw_zaagvolgorde_generiek` is verwijderd (geen enkele aanroeper
     meer over). 2 bestaande guillotine-only rand-tot-rand-tests zijn
     geparametriseerd over `["efficient", "guillotine"]` om dit te
     bewijzen (nu 111 tests i.p.v. 109). `demo_render.py`'s
     `demo_efficient.png` opnieuw gegenereerd ter visuele controle —
     alle sneden lopen nu netjes rand-tot-rand.
  3. **Bijvangst tijdens het narekenen van bug 2 met het testproject-
     script**: het MDF-testmateriaal (`scripts/
     maak_test_project_zaagplan.py`) bleek in de échte database allang
     niet meer de "bewust te krappe" 600×500mm te zijn die het script
     declareert — 2800×2150mm met randafzaag op alle randen, duidelijk
     ooit door Sven zelf aangepast tijdens het los verkennen van de
     Materialenbibliotheek-UI. Het script hergebruikte materialen tot
     nu toe alleen-op-naam (nooit opnieuw aangemaakt), dus zo'n
     handmatige wijziging bleef bij elke rerun stilzwijgend hangen — met
     als gevolg dat de bedoelde "niet geplaatst"-testcase (de
     ladefronten-groep past expres niet op de te kleine MDF-plaat) niet
     meer reproduceerde, en dat bug 2 hierboven op de échte, veel grotere
     MDF-plaat waarschijnlijk makkelijker zichtbaar werd. **Fix:**
     `scripts/maak_test_project_zaagplan.py` verwijdert en herbouwt nu
     bij elke run niet alleen het testmodel/-project (al zo sinds de
     vorige sessie) maar ook alle drie testmaterialen
     (`_materiaal_vers_aanmaken`, archiveren + definitief verwijderen +
     opnieuw aanmaken) — een rerun geeft dus altijd gegarandeerd exact
     de in het script gedefinieerde afmetingen/instellingen, ook als
     iemand ze handmatig heeft aangepast. Zelfde les als de eerdere
     naamsbotsing-bevinding in dit script: testdata die "idempotent op
     naam" hergebruikt wordt, drift onopgemerkt weg zodra iemand de UI
     gebruikt op diezelfde records.
  **Tegelijk ook gevraagd en toegevoegd**: een nerfrichting-testgeval in
  hetzelfde script (`Werkblad`, `nerfrichting_vereist=LANGE_ZIJDE` — mag
  dus nooit roteren), zodat dit gedrag ook via de UI met echte
  projectdata te verifiëren is, niet alleen via de pytest-suite.
  Alles geverifieerd met de volledige pytest-suite (115 tests, allemaal
  groen) en met het testproject-script twee keer achter elkaar
  gedraaid (bewijst dat de volledige resync-aanpak ook echt idempotent
  herhaalbaar is) plus een handmatige controle van de gegenereerde
  zaagvolgordes/materiaalgeometrie per plaat.

- **Zaagsnede-lijnen die dwars door een ander onderdeel liepen — óók nog
  bij "Rijen"/"Stroken" (Sven meldde dit als nog steeds aanwezig ná de
  "efficient"-fix hierboven: "hij doet het probleem met de rode
  stippellijn nogsteeds").** Andere grondoorzaak dan de eerdere
  "efficient"-bug, in `_bouw_zaagvolgorde_rijen` (nu verwijderd, zie
  onder): die functie leidde "welke y-waardes zijn een rijgrens" simpelweg
  af uit **alle** losse `Plaatsing`-y-coördinaten in de platte
  plaatsingenlijst. Een gestapelde groep (bv. drie ladefronten) expandeert
  in `_Eenheid.expand()` echter naar meerdere `Plaatsing`-records op
  verschillende y's **binnen één en dezelfde rij** — die interne
  naad-y's werden dus onterecht óók als "rijgrens" behandeld, wat een
  volledige-plaatbreedte horizontale snede opleverde die dwars door elk
  ánder onderdeel in diezelfde rij heen liep (gereproduceerd met een
  groep naast een los onderdeel van een heel andere hoogte: 2 van de 4
  gegenereerde sneden kruisten het losse onderdeel). **Fix**: `_pak_rijen`
  en `_pak_stroken` bouwen hun zaagvolgorde nu zelf op tijdens het
  plaatsen (nieuwe gedeelde hulpfuncties `_bouw_rij_kolom_sneden` +
  `_bouw_zaagvolgorde_uit_rijen`), met de daadwerkelijke rijgrenzen
  (`rij_grenzen`, bijgehouden in de plaatsingslus zelf) als enige bron
  voor de volledige-breedte sneden tussen rijen — nooit meer afgeleid uit
  losse plaatsings-y's. Een groep krijgt zijn interne naad-sneden nog
  steeds (nodig, want de leden moeten wel degelijk van elkaar gescheiden
  worden), maar nu correct **begrensd tot de breedte van de groep-kolom
  zelf** i.p.v. de volle plaatbreedte. Bijkomend voordeel: fabrieks-
  kantenband-plaatsingen (die hun eigen, aparte snede al krijgen, zie
  eerder) konden er tot nu toe óók ongemerkt spurieuze "rijgrenzen"
  doorheen laten glippen als er meer dan één fabriekskantenband-stuk
  gestapeld stond — dat kan nu niet meer, want de zaagvolgorde-opbouw
  raakt de fabriek-plaatsingen sowieso niet meer aan. De oude,
  post-hoc-reconstruerende `_bouw_zaagvolgorde_rijen` is volledig
  verwijderd (zelfde soort opschoning als eerder bij
  `_bouw_zaagvolgorde_generiek`). 2 nieuwe, gerichte tests (een groep
  naast een los onderdeel, met een expliciete check dat de interne
  groep-sneden precies de kolombreedte raken) plus 1 brede test die over
  alle vier strategieën tegelijk controleert dat geen enkele snede door
  een plaatsing heen loopt (nu 121 tests i.p.v. 115).
  `demo_groepering.png` opnieuw gegenereerd ter visuele controle — de
  interne ladefronten-naad blijft nu netjes binnen de eigen kolom i.p.v.
  door te lopen in het reststuk ernaast.

- **Het vierde motor-hiaat is opgelost:** met strategie "Rijen" gooide
  `_pak_rijen` voorheen de HELE rest van de onderdelenlijst als
  "niet geplaatst" weg zodra de als-eerste-gekozen (hoogste) rij niet
  verticaal paste, ook als kleinere onderdelen verderop in de lijst
  prima in een lagere rij zouden passen — precies het scenario uit het
  testproject (de ladefronten-groep past niet op de 500mm-hoge
  MDF-plaat, maar de Lade-bodems ernaast wel). **Fix**: nieuwe helper
  `_vind_plaatsbare_rij` doorloopt de hoogte-groepen (`_groepeer_op_hoogte`,
  al aflopend gesorteerd: hoogste eerst) en slaat een groep die niet
  binnen de resterende hoogte (`y1 - cursor_y`) past definitief over —
  die groep wordt METEEN als niet-geplaatst gemarkeerd (nooit meer
  opnieuw geprobeerd, want `cursor_y` loopt alleen maar op, dus de
  resterende hoogte wordt nooit groter) — en gaat door naar de volgende,
  lagere hoogte-groep om daarmee alsnog een rij te vullen. Dezelfde
  aanpak vangt ook een analoog breedte-probleem op (een groep die wél in
  de hoogte past maar zelfs als enige, dominante kolom te breed is voor
  de plaat). Pas als zelfs de laagste resterende groep nergens meer past,
  stopt de plaatsing pas echt (`_pak_rijen`'s while-lus breekt af).
  **Bewust NIET toegepast op `_pak_stroken`** (de docstring legt dit nu
  expliciet uit): bij "Stroken" ligt de strookhoogte voor de hele plaat
  vast op het hoogste onderdeel, dus zodra één strook niet meer past,
  past er — anders dan bij "Rijen" — ECHT niets meer, hoe klein ook (elke
  strook is immers altijd even hoog). Het vroegtijdig stoppen was voor
  "Stroken" dus nooit een bug, alleen voor "Rijen".
  4 nieuwe tests (twee voor de fix zelf — de te-hoge-groep-wordt-
  overgeslagen-case en de tegenhanger waarbij zelfs de laagste groep niet
  meer past — en een expliciete test die bevestigt dat "Stroken" bewust
  wél meteen stopt), nu 124 tests in totaal. Geverifieerd met het exacte
  testproject-scenario (via het herbouwde testscript, zie hierboven): de
  twee Lade-bodems worden nu wél geplaatst (verdeeld over 2 platen dankzij
  de eerdere meerdere-platen-functionaliteit), de ladefronten-groep blijft
  terecht definitief niet geplaatst, en er treedt geen enkele
  snede-kruising op.
  **Bijvangst tijdens het verifiëren**: het MDF-testmateriaal in de échte
  database bleek wéér afgeweken te zijn van de scriptdefinitie (terug naar
  2800×2150mm met randafzaag) — Sven had het kennelijk opnieuw handmatig
  aangepast tijdens het testen van een eerdere stap in deze sessie. Geen
  bug, gewoon de al gedocumenteerde drift; het testproject-script opnieuw
  gedraaid loste dit meteen op (bevestigt dat de resync-aanpak precies
  doet waarvoor hij bedoeld is).

- **PDF-export voor zaagplannen, twee UI-opschoningen in Projecten/
  Dashboard.** Op Svens verzoek na de vraag of er al genoeg functie is
  voor een eerste proef/demo — antwoord: ja voor een interne demo, met
  als kanttekening dat er nog geen PDF-export was en het
  Zaagplannen-scherm zelf nog geen polish-ronde had gehad. Sven ging
  akkoord met alle drie:
  1. **PDF-export** (`_bouw_zaagplan_resultaat`'s toolbar, nieuwe
     primaire knop "Alles + zaaglijst als PDF", nieuw `download`-icoon in
     `icons.py`): `ProjectDetailPage._schrijf_zaagplannen_pdf` gebruikt
     `QtPrintSupport.QPrinter` (A4 liggend) en tekent voor élke plaat
     gewoon de bestaande `_bouw_zaagplan_document(plan)`-kaart
     (`QWidget.render()` op een nooit-getoonde widget, geschaald en
     gecentreerd per pagina) — bewust hergebruik van dezelfde opmaak als
     het scherm zelf i.p.v. een aparte PDF-lay-out, zodat de twee nooit
     uit de pas kunnen lopen. De laatste pagina is de volledige
     zaaglijst, via een nieuwe, PDF-eigen `_bouw_pdf_zaaglijst_tabel()`
     (bewust NIET de levende `self._zaaglijst_table` hergebruikt, want
     die zou dan eerst uit zijn eigen paneel-layout gehaald moeten
     worden om 'm elders te tekenen — dat zou 'm blijvend uit het
     Zaaglijst-paneel laten verdwijnen).
     **Twee geverifieerde/opgeloste valkuilen tijdens het bouwen**:
     (a) `widget.resize(breedte, ...)` gevolgd door `adjustSize()` zet de
     widget meteen terug naar zijn eigen (veel kleinere) `sizeHint()` —
     dus bewust GEEN `adjustSize()` na de resize, `resize()` zelf
     activeert de layout al synchroon (geverifieerd door de
     widget-afmetingen vóór/na te vergelijken: 648×533 mét de foute
     `adjustSize()`-aanroep, ~1400×800+ zonder). (b) tabellen erin
     kregen hun vaste hoogte oorspronkelijk berekend voor het scherm,
     waar een uitgestelde `QTimer.singleShot`-correctie (zie de
     tabel-scrollbug-fix van eerder deze sessie) de kale
     header-`sizeHint()` ophoogt zodra de tabel écht getoond wordt — bij
     PDF-export wordt niets getoond, dus die correctie loopt nooit, dus
     krijgt elke tabel in `_render_widget_op_pagina` een eigen, royale
     vaste veiligheidsmarge (+24px) in plaats daarvan.
  2. **Projectenlijst: geen los potlood-icoon meer om te openen — de
     hele rij is nu klikbaar** (Sven: "het zou mooier zijn om deze
     potlood weg te halen en naar het bewerken gaat als je er al op
     drukt"). Nieuwe kleine widget `_KlikbareCel` (`projecten_page.py`)
     wikkelt elke niet-actiekolomcel in en stuurt een klik ergens
     binnenin door naar `_on_open_project`/`_open_drawer` — zonder dat
     de kind-labels expliciet "transparent for mouse events" hoeven te
     worden: een muisklik op een child-widget dat 'm niet zelf afhandelt
     (zoals een kale `QLabel`) propageert in Qt automatisch naar de
     ouder (geverifieerd met een gerichte `QMouseEvent`-test: een klik
     op de naam- én de status-cel opent allebei het project, een klik op
     een actieknop in de laatste kolom doet dat terecht NIET). De
     actiekolom zelf (archiveren/verwijderen) blijft ongewijzigd, met
     zijn eigen klikgebied.
  3. **Dashboard: status snel wijzigen vanaf een projectkaart** (Svens
     eigen toevoeging: "ik zou in de dashboard ook de mogelijkheid geven
     om een project snel van status te kunnen veranderen"). De statische
     statuschip op `ProjectCard` is vervangen door een echte
     `QComboBox` (`_status_combo` in `widgets/project_card.py`, met
     dezelfde statuskleur als accentkleur voor tekst/rand), die
     `ProjectenBibliotheek.zet_status()` aanroept en daarna
     `MainWindow._on_project_gewijzigd()` — dezelfde refresh-hook als een
     wijziging vanuit het projectdetailtabblad. **Belangrijke, bijna
     gemiste bug**: `ProjectStatus` is een `str`-Enum, en
     `QComboBox.currentData()` geeft zo'n enum-lid bij het uitlezen altijd
     als kale `str` terug i.p.v. het oorspronkelijke enum-lid (zelfde
     Qt/PySide6-eigenaardigheid als eerder gedocumenteerd in dit bestand
     voor `setProperty`/combobox-userData) — zonder fix zou dit een kale
     string in `project.status` opslaan, die bij de eerstvolgende
     SQLite-persistering zou crashen op `project.status.value`
     (`opslag.py` verwacht een echt enum-lid). Fix: userData wordt met
     `.value` opgeslagen en bij het teruglezen expliciet met
     `ProjectStatus(...)` gereconstrueerd. Geverifieerd met een
     end-to-end smoke-test die ook een "herstart" simuleert (nieuwe
     bibliotheek-instantie op hetzelfde db-bestand) om zeker te weten dat
     de status niet alleen in het geheugen maar ook op schijf een echt
     enum-lid blijft.
  **Kleine polish-ronde op het Zaagplannen-paneel zelf** (n.a.v. Svens
  verzoek): consistente `10px`-toolbarspacing (matchte de rest van het
  paneel al niet helemaal), en de losse "Plaat X van Y"-meta-tekst in de
  documentkaart-kop samengevoegd met de afmeting-tekst achter hetzelfde
  "·"-scheidingsteken-patroon dat de rest van de app al gebruikt, i.p.v.
  twee losse labels naast elkaar.
  Alles geverifieerd met offscreen smoke-tests (PDF-bestand daadwerkelijk
  weggeschreven met de juiste paginastructuur — geverifieerd door het
  bestand te lezen/bekijken; rij-klik opent het project maar een
  actieknop-klik niet; dashboard-statuswissel persisteert correct en
  overleeft een "herstart") plus de volledige pytest-suite (124 tests,
  onveranderd — dit was allemaal UI-werk zonder backend-testdekking per
  de conventie in dit bestand).

- **PDF-export van hierboven afgekeurd door Sven — opnieuw van de grond
  af, ditmaal écht mockup-first.** De `_schrijf_zaagplannen_pdf`-aanpak
  hierboven rendert gewoon de bestaande, DONKER-getinte scherm-widgets
  (`_bouw_zaagplan_document`) naar de printer — dat gaf een donkere
  achtergrond op een verder wit PDF-document. Sven: "ik wil echt dat hij
  de pdfs eigenlijk van de grond opbouwt". **Belangrijke vondst**: er
  bestonden al eerder door Sven goedgekeurde PDF-referenties uit de
  Cowork-ontwerpfase, die ik over het hoofd had gezien —
  `design/voorbeelden/zaagplan-voorbeeld-v1.pdf`/`-v2.pdf` (en de
  bijbehorende `generate_zaagplan*.py`-scripts, gebouwd met
  `reportlab`): donkere titelbalk, rode stippellijn-zaagsnedes met
  genummerde cirkels, groen gemarkeerde herbruikbare reststukken, een
  onderdelentabel en een footer-strook met QR-placeholder — een volledig
  losstaand, wit print-ontwerp, nooit gekoppeld aan de scherm-widgets.
  Op Svens verzoek eerst een nieuwe HTML-mockup gebouwd (Artifact) die
  deze visuele taal aanhoudt maar met het huidige veldenpalet van de
  app, vóórdat de echte generator herbouwd wordt. Meerdere
  correctierondes, alle verwerkt:
  1. Geen revisienummer/QR/"Bronmateriaal"-veld (bestaan nog niet als
     features), "Opmerkingen"-kolom vervangen door "Herkomst" (sluit aan
     op het scherm), strategie-label en "Plaat X van Y" toegevoegd.
  2. **Logo rechtsboven** (Svens verzoek): uit `Instellingen →
     bedrijfslogo_pad`; staat dat leeg of is dit de demo-versie, dan
     valt de PDF terug op het RoboCutter-eigen logo
     (`design/assets/logo/robocutter_logo_met_tekst.png`). **Werkvoor-
     bereider-naam ernaast** (Svens verzoek): uit `Instellingen →
     werkvoorbereider_naam` — tijdelijk, tot er een echt
     gebruikerssysteem is (Sven noemde dit expliciet als toekomstplan).
     Dit worden de eerste twee echte consumenten van die twee
     Instellingen-velden (zie de Opties-sectie hierboven, "nog geen
     consumerende feature").
  3. **Titelbalk niet langer een volle donkere vlak** (Svens verzoek,
     inktbesparend bij printen): wit met een dunne onderrand i.p.v. een
     dichtgevulde balk.
  4. **Modelnaam uit de titelbalk gehaald** (Svens verzoek): een plaat
     kan onderdelen van meerdere modellen of losse onderdelen door
     elkaar bevatten, dus één modelnaam erboven zou misleidend zijn — de
     herkomst per onderdeel staat toch al in de tabelkolom "Herkomst".
  5. **Zaaglijst-paginering**: op Svens vraag "wat gebeurt er als de
     zaaglijst langer is dan één pagina" toegevoegd/gevisualiseerd —
     loopt de tabel over meerdere pagina's, dan herhaalt de kolomkop
     zich op elke vervolgpagina (zelfde principe als "Plaat X van Y"),
     en de "Totaal"-regel verschijnt alleen op de állerlaatste
     zaaglijst-pagina. De mockup toont dit concreet door de 10
     voorbeeldregels kunstmatig te splitsen over 2 pagina's.
  6. **Afvinkkolom** (Svens verzoek, "zodat ze dit in de werkplaats op
     papier kunnen doen"): een leeg, echt getekend vierkantje (geen
     font-checkbox-symbool — zelfde "geen font-emoji"-principe als het
     oude v1/v2-referentiescript) als eerste kolom in zowel elke
     onderdelentabel als de zaaglijst.
  **Definitief goedgekeurd door Sven ("dit ziet er goed uit").** Mockup:
  https://claude.ai/code/artifact/82f02781-36e3-45b3-a179-26a97fd0c0c1
  (4 pagina's: Eiken-multiplexplaat volledig geplaatst, MDF-plaat met de
  "niet geplaatst"-waarschuwingsbalk, en de zaaglijst in 2 vervolgpagina's
  — alle plaat-/zaagsnede-coördinaten zijn échte
  `genereer_zaagplan()`-uitvoer, geen verzonnen getallen).
  **Volgende sessie: de echte generator bouwen volgens deze mockup** —
  dit vervangt `_schrijf_zaagplannen_pdf`'s huidige
  `QWidget.render()`-aanpak volledig door directe `QPainter`-tekencode
  (rechthoeken/lijnen/tekst, zoals het oude reportlab-referentiescript
  dat ook deed) tegen een eigen, van het schermthema losstaand wit
  PDF-palet — nooit meer een scherm-widget naar de printer renderen.
  De HTML-mockup hierboven is de bron van waarheid voor kleuren/
  lay-outverhoudingen/kolomstructuur.

- **PDF-generator écht gebouwd (nieuwe sessie, vervolg op de
  goedgekeurde mockup hierboven).** Nieuw bestand
  `src/robocutter/ui/zaagplan_pdf.py`: één functie
  `schrijf_zaagplannen_pdf(pad, project, zaagplannen, strategie_label,
  materialen, sort_niveaus)`, losstaand van `ProjectDetailPage` (die
  roept 'm nu alleen nog aan) zodat de generator ook zonder een geopend
  projecttabblad te testen is. `_schrijf_zaagplannen_pdf`,
  `_bouw_pdf_zaaglijst_tabel` en `_render_widget_op_pagina` in
  `project_detail_page.py` zijn volledig verwijderd, met hen de
  `QWidget.render()`-aanpak en de bijbehorende Qt-print-imports
  (`QPrinter`/`QPageLayout`/`QPageSize`/`QPainter`/`QPoint`/`QRectF`
  daar nu ongebruikt en dus ook weg).
  Alle tekstblokken/rechthoeken/lijnen/cirkels van de mockup worden nu
  echt met `QPainter` getekend in millimeters (omgerekend naar
  apparaatpixels via de printer-DPI, net als het oude reportlab-
  referentiescript deed) — geen enkele scherm-widget wordt meer naar de
  printer gerenderd. Hergebruikt bewust dezelfde geometrische
  ``ZaagplanResultaat``-data (`plaatsingen`/`reststukken`/
  `zaagvolgorde`) als `ZaagplaatWidget` (het scherm), maar met een eigen
  print-kleurenpalet en eigen labelstijl (genummerde groene cirkel per
  geplaatst onderdeel, ongekaderde vetgedrukt-groene "R#" per
  reststuk — zonder cirkel, exact zoals de mockup).
  **Regel voor de genummerde zaagsnede-badges** (niet letterlijk zo in
  hoofdstuk 5 vastgelegd, afgeleid uit de goedgekeurde mockup zelf): een
  verticale snede krijgt zijn badge aan het einde (de kant met de
  grootste y) van zijn eigen segment, een horizontale snede aan het
  begin (de kant met de kleinste x) — dat kwam letterlijk overeen met
  alle badge-posities in de mockup toen ze zijn nagerekend.
  De fabriekskantenband-indicator (dikke donkere lijn net buiten de
  betreffende plaatrand) tekent voor elke rand een simpel
  niet-geroteerd bijschrift in plaats van de tekst mee te roteren met
  verticale randen — een bewuste vereenvoudiging t.o.v. wat in theorie
  mooier zou kunnen, maar de mockup zelf roteert het bijschrift ook niet
  mee met zijn eigen (linker) fabrieksrand-voorbeeld.
  De zaaglijst-pagina's herhalen de kolomkop op elke vervolgpagina en
  tonen de "Totaal"-rij alleen op de allerlaatste pagina — als de
  laatste pagina al vol zit (evenveel rijen als er per pagina passen)
  krijgt de totaalregel een eigen extra pagina in plaats van de tabel te
  laten overlopen.
  **Geverifieerd** met een los smoke-script (in-memory bibliotheken,
  nooit `data/robocutter.db` aangeraakt) dat een PDF wegschrijft voor
  een scenario met een volledig geplaatste plaat, een "niet
  geplaatst"-scenario (amberkleurige balk) en een kunstmatig lange
  zaaglijst (30+ regels) om de paginering/totaalregel-logica te
  triggeren — gecontroleerd door zowel de pagina's naar PNG te renderen
  (`QPdfDocument.render`) als de ingebedde tekst terug uit te lezen
  (`QPdfDocument.getAllText`, om zeker te weten dat de content zelf
  klopt, los van een renderingseigenaardigheid van die preview-tool die
  bij een lange tabel af en toe losse rijen als effen zwarte blokken
  liet zien — de onderliggende PDF-tekst zelf bleek daarbij steeds
  correct, dus dat bleek een eigenaardigheid van het preview-pad, geen
  fout in de generator). Leverde ook nog een lastig te vinden bug op:
  een losstaande `QFontMetricsF(font)` (zonder gekoppeld apparaat) meet
  in scherm-DPI terwijl de tabel/kop-rechthoeken al in printer-DPI-
  pixels stonden — daardoor zou eliding van te lange tekst nooit
  triggeren. Fix: `painter.fontMetrics()` gebruiken (gekoppeld aan de
  actieve printer als paint device) i.p.v. een losse `QFontMetricsF`.
  Logo/werkvoorbereider komen nu ook echt uit `Instellingen` (met
  terugval op het RoboCutter-logo als `bedrijfslogo_pad` leeg is), zoals
  in de mockup afgesproken.

- **Eerste exe + installer (demo-build), op Svens verzoek na het zien
  van de PDF-export.** Hoofdstuk 8 legt Nuitka + Inno Setup vast als
  definitieve bundel-/installer-keuze voor de echte commerciële
  release, maar Nuitka vereist eenmalig een C-compiler-download en een
  aanmerkelijk langere buildtijd — voor déze eerste, interne demo koos
  Sven expliciet voor de snellere **PyInstaller**-route nu, met Nuitka
  als bewuste vervolgstap vóór een echte release (zie de vraag/
  antwoord hierover in de sessie).
  1. **Padresolutie frozen-bewust gemaakt** — drie plekken gingen ervan
     uit dat de code altijd vanuit de broncode draait
     (`Path(__file__).resolve().parents[3]` om bij de repo-root te
     komen): `main_window.py` (het werkbalk-logo),
     `zaagplan_pdf.py` (het RoboCutter-terugvallogo in de PDF) en
     `instellingen/beheer.py` (de standaard datamap voor
     `data/robocutter.db`). Alle drie krijgen nu een `sys.frozen`-tak:
     de eerste twee lezen in een PyInstaller-build hun pad relatief aan
     `sys._MEIPASS` (onefile) of de map naast de exe (onedir); de derde
     valt in een gebundelde build terug op `%APPDATA%\RoboCutter\data`
     in plaats van een map naast de exe, omdat een exe meestal in een
     niet-schrijfbare map als Program Files staat — dezelfde
     `%APPDATA%\RoboCutter`-basis die `instellingen.json` toch al
     gebruikt, dus geen nieuwe locatie verzonnen.
  2. **`scripts/build_exe.ps1`**: bouwt `dist/RoboCutter.exe` (één
     bestand, `--onefile --windowed`, met het nieuwe
     `design/assets/logo/robocutter_icon.ico` — een multi-resolutie
     ico, met Pillow gegenereerd uit de bestaande
     `robocutter_icon_toolbar.png`, want Windows-exe's hebben een
     `.ico` nodig, geen `.png`) en bundelt `design/assets` mee als data
     zodat de logo's/het icoon ook buiten de broncode te vinden zijn.
     Nieuwe `build`-extra in `pyproject.toml` (`pip install -e
     ".[build]"`) voor PyInstaller.
  3. **`installer/robocutter.iss`** (Inno Setup) + wrapper-script
     `installer/build_installer.ps1` (bouwt eerst de exe, compileert
     daarna de installer): per-user of per-machine installatie (geen
     verplichte adminrechten), Nederlandstalige wizard, Start Menu- en
     optionele bureaublad-snelkoppeling, standaard Inno-uninstaller.
     **Bewust nog geen code signing** (hoofdstuk 8 noemt dit wel, ook
     om Windows' "onbekende uitgever"-waarschuwing te voorkomen) — er
     is nog geen certificaat; dit is een openstaand punt voor vóór een
     echte release, niet voor deze interne demo.
  4. **Geverifieerd**: de exe los gestart (blijft draaien, schrijft
     `%APPDATA%\RoboCutter\data\robocutter.db` aan zoals verwacht) en
     de installer met een stille testinstallatie
     (`/VERYSILENT /CURRENTUSER /DIR=...`) naar een tijdelijke map,
     daarna gestart vanuit die installatiemap en weer succesvol
     verwijderd via de gegenereerde `unins000.exe` — geen sporen
     achtergelaten op de echte machine buiten de gedeelde
     `%APPDATA%\RoboCutter\instellingen.json`/`data`, die de gewone
     dev-app toch al gebruikt.
  Nieuwe `.gitignore`-regels voor de buildartefacten: `/build/`,
  `/dist/`, `*.spec`, `/installer/Output/`.

- **Nog een zaagmotor-iteratie, op Svens verzoek** ("hij maakt
  nogsteeds fouten als onderdelen op platen zetten wat helemaal niet
  past, hij kan nog geen items roteren, en hij maakt nog foutjes met
  oog op efficient zijn") — drie afzonderlijke problemen, gevonden en
  bevestigd met een fuzz-script (willekeurige platen/onderdelen/
  groepen/fabriekskantenband-combinaties over alle vier strategieën,
  met controles op overlap/buiten-de-plaat/aantal-klopt) vóór het
  schrijven van een fix, zodat elke fix ook meetbaar geverifieerd kon
  worden i.p.v. op het oog:
  1. **Onderdelen buiten de plaat geplaatst — de fabriekskantenband-
     strook.** `genereer_zaagplan` stapelde alle fabriek-eenheden
     blindelings in ÉÉN kolom (LINKS/RECHTS) of rij (ONDER/BOVEN) langs
     de gekozen rand, zonder ooit te checken of dat nog binnen de plaat
     paste — bij een paar stuks te veel (of gewoon een paar grote
     stuks) liep de stapel simpelweg door tot ver buiten de plaat, in
     het fuzz-script tot duizenden mm buiten de plaatgrens, soms zelfs
     met een NEGATIEVE x/y aan de andere kant. Fix: nieuwe helper
     `_plaats_fabriek_rand` plaatst ze nu in kolommen/rijen met
     wraparound zodra de huidige kolom/rij vol is; onderdelen die ook
     dan nergens meer in de resterende rand-strook passen komen terecht
     in `niet_geplaatst` (schuiven net als elk ander niet-geplaatst
     onderdeel door naar een volgende, verse plaat) i.p.v. buiten de
     plaat geplaatst te worden. Dit was de kern van "onderdelen op
     platen zetten wat helemaal niet past" — het fuzz-script vond 'm
     pas zodra ook groepen/fabriekskantenband meegenomen werden (de
     eerdere, kalere fuzz-ronde zonder die twee vond niets).
  2. **Geen rotatie in "Rijen"/"Stroken".** Beide strategieën gebruikten
     voor een vrij-roteerbaar onderdeel (geen nerf-eis) altijd de
     invoer-oriëntatie van het onderdeel, zonder ooit te roteren — dit
     terwijl "Rijen" zelf letterlijk "lange zijdes eerst" heet.
     `_pak_efficient`/`_pak_guillotine` deden dit al langer goed (eigen
     best-fit-zoektocht over beide oriëntaties). Fix: nieuwe helper
     `_landschap_indien_vrij` legt een vrij-roteerbaar onderdeel nu met
     zijn langste zijde langs de x-as, zoals de strategienaam belooft
     — twee bestaande tests die specifiek op de oude (nooit-roteren)
     geometrie leunden zijn aangepast met een nerf-eis om hun bedoelde
     scenario (twee even hoge stukken die gedwongen in dezelfde
     rij/kolom moeten vallen) overeind te houden.
  3. **"Efficient" soms minder efficiënt dan "Guillotine".** Fuzz-
     vergelijking liet zien dat de greedy best-area-fit-heuristiek van
     `_pak_efficient` op sommige platen aantoonbaar MINDER onderdelen
     plaatste dan de eenvoudigere FIFO-wachtrij-aanpak van
     `_pak_guillotine` — een bekende zwakte van greedy bin-packing (de
     lokaal beste keuze voor het huidige stuk is niet altijd de beste
     keuze op de lange termijn). Fix: "efficient" probeert nu ALTIJD
     ook de guillotine-heuristiek en gebruikt via nieuwe helper
     `_kies_beste_pakresultaat` gewoon de beste van de twee uitkomsten
     (minste niet-geplaatst, bij gelijke stand het minste afval) i.p.v.
     blind op één heuristiek te vertrouwen.
  Geverifieerd: volledige testsuite groen (twee tests aangepast, zie
  boven, verder geen regressies), plus het fuzz-script zelf op nul
  fouten over meerdere seeds/duizenden runs (los, niet in de pytest-
  suite opgenomen — puur gebruikt om deze iteratie te sturen/verifiëren).
  `scripts/demo_render.py` opnieuw gedraaid en de vier `output/demo_*.png`
  visueel gecontroleerd, geen regressie in de bestaande voorbeelden.

- **Diezelfde zaagmotor-iteratie bleek zelf twee nieuwe bugs te hebben
  geïntroduceerd — Sven meldde dit meteen na het testen** ("hij houdt
  nu geen rekening met fabriekskantenband in rijen en hij plaatst ook
  niet alles terwijl daar wel ruimte voor is of dat hij gewoon een
  nieuwe plaat kan pakken"). Weer eerst met een uitgebreider fuzz-script
  bevestigd vóór het fixen (dit keer óók met fabriekskantenband +
  groepen samen, en met een multi-plaat-volledigheidscheck: "moet alles
  wat past ooit ergens landen").
  1. **Fabriekskantenband-strook: de wraparound-fix hierboven bleek zelf
     fout.** Een tweede kolom/rij "verder de plaat in" voorkwam de
     buiten-de-plaat-bug wel, maar raakt de vereiste rand niet meer —
     wat de hele fabriekskantenband-eis zelf schendt (het punt van een
     fabriekskantenband is nu juist dat het stuk PLAT tegen die ene rand
     ligt). Fix: `_plaats_fabriek_rand` doet nu bewust GEEN wraparound
     meer — gewoon één rechte lijn tegen de rand, en wat daar niet meer
     bij past wordt echt `niet_geplaatst` (schuift door naar een
     volgende, verse plaat met een weer volledig lege rand).
  2. **Fabriekskantenband-stuk permanent niet geplaatst, ook op een
     verse plaat, als de invoer-oriëntatie toevallig niet past.**
     `_plaats_fabriek_rand` probeerde nooit de geroteerde oriëntatie van
     een vrij-roteerbaar stuk (geen nerf-eis) — als de rauwe
     breedte/hoogte uit de onderdelenlijst niet in het beschikbare
     werkgebied paste terwijl de andere kant om wél zou passen, sneuvelde
     het stuk voorgoed. Fix: probeert nu, net als `_pak_efficient`/
     `_pak_guillotine`, de geroteerde oriëntatie als de natuurlijke niet
     past.
  3. **De "lange zijdes eerst"-rotatiefix (zie hierboven) was zelf ook
     te rigide.** `_landschap_indien_vrij` koos altijd de lange zijde
     langs x, zónder te checken of dat wel binnen de plaatbreedte paste
     — een onderdeel dat liggend te breed is voor de plaat maar staand
     prima zou passen, eindigde zo blijvend als niet-geplaatst, ook op
     een verse plaat, puur door deze voorkeur zelf (exact Svens tweede
     klacht: "hij plaatst ook niet alles terwijl daar wel ruimte voor
     is"). Fix: valt nu terug op de staande oriëntatie zodra landschap
     niet past maar staand wel.
  Alle drie de bugs zaten dus in dezelfde categorie: een fix die correct
  leek voor het gemelde probleem, maar zelf een net iets te absolute
  regel introduceerde ("altijd wraparound", "nooit roteren in de
  fabriekstrook", "altijd landschap") zonder een terugvaloptie voor de
  gevallen waarin die regel het tegenovergestelde effect had. Geverifieerd
  met het uitgebreide fuzz-script (7 seeds × 400 runs, incl. groepen +
  fabriekskantenband + multi-plaat-volledigheid): 0 fouten, tegen 1131
  vóór deze fix (waarvan de meeste overigens fuzz-scriptfouten bleken —
  onderdelen die door hun EIGEN nerf-eis simpelweg te groot zijn voor het
  materiaal horen terecht permanent niet-geplaatst te blijven; het script
  is aangescherpt om dat te onderscheiden van een echte motor-bug).
  Volledige testsuite blijft groen, `demo_render.py` opnieuw gecontroleerd.

- **Nog een efficiëntie-iteratie plus zaagplan-persistentie, op Svens
  verzoek** ("nog steeds dingetjes waarvan ik zie dit kan beter
  georganiseerd worden qua efficiëntie, en zorg er ook voor dat
  zaagplannen binnen een project worden opgeslagen").
  1. **"Efficient" probeert nu alle vier heuristieken, niet meer twee.**
     Fuzz-vergelijking liet zien dat "efficient" (best-area-fit +
     guillotine, zie de vorige iteratie) in zo'n 10% van de gevallen nog
     steeds werd verslagen door "rijen" of "stroken" — dus toegevoegd
     aan de kandidatenlijst in `_kies_beste_pakresultaat`. "Efficient"
     betekent nu letterlijk "het beste resultaat van alle beschikbare
     aanpakken", niet één vaste slimme aanpak.
  2. **Latente bug gevonden door die uitbreiding: `_pak_rijen`/
     `_pak_stroken`'s tussen-kolom-sneden stopten 1 kerf te vroeg.**
     Zodra "efficient" voortaan ook op de uitkomst van "rijen"/"stroken"
     kon uitkomen, faalde de bestaande strikte rand-tot-rand-
     reconstructietest (die eerder alleen voor "efficient"/"guillotine"
     draaide) meteen. Grondoorzaak: een tussen-kolom-snede binnen een
     rij liet zijn bovengrens stoppen bij de CONTENT-hoogte van de rij
     (zonder kerf), terwijl de rij als fysiek stuk plaat, zodra er nóg
     een rij op volgt, in werkelijkheid net zo hoog is als waar de
     horizontale scheidingssnede naar die volgende rij ligt (mét kerf)
     — een snede die daar te vroeg stopt is geen echte rand-tot-rand
     snede van het fysieke rij-stuk meer (in de praktijk een verschil
     van maar een paar mm, maar wel een reële onnauwkeurigheid in de
     zaagvolgorde). Fix: `_bouw_zaagvolgorde_uit_rijen` bouwt de
     tussen-kolom-sneden nu pas ná afloop van de hele rij-lus, als de
     ECHTE rijgrenzen bekend zijn (nieuwe helper `_plaats_rij`
     losgetrokken uit het oude `_bouw_rij_kolom_sneden`, dat nu alleen
     nog plaatsingen/groep-naadsneden/kolomranden teruggeeft). De
     rand-tot-rand-reconstructietest draait nu ook voor "rijen"/
     "stroken" (was tot dan toe ongedekt, want "efficient" kon er tot
     deze iteratie nooit intern op uitkomen).
  3. **Zaagplannen worden nu opgeslagen per project.** Nieuw:
     `robocutter.projecten.zaagplannen_opslag` (`ZaagplannenOpslag`,
     eigen `zaagplannen`-tabel in hetzelfde db-bestand) bewaart, per
     project, het LAATST gegenereerde zaagplan als één JSON-blob (net
     als `modelinstanties`/`losse_onderdelen` in `projecten/opslag.py`)
     — bewust GEEN volledige revisiegeschiedenis (Rev A/B/C...), dat
     blijft een apart, groter onderwerp (zie hieronder). `main_window.py`
     opent de verbinding één keer (gedeeld tussen alle open
     projecttabbladen, want die kunnen dezelfde tabel tegelijk lezen/
     schrijven) en injecteert 'm in elke `ProjectDetailPage`, die bij het
     openen een eerder opgeslagen zaagplan herlaadt (i.p.v. altijd leeg
     te beginnen) en bij elke (opnieuw-)generatie meteen opslaat. Geen
     "is dit zaagplan nog actueel?"-detectie als de projectsamenstelling
     ná het genereren verandert — "opnieuw genereren" blijft de manier
     om een verouderde opgeslagen stand te vervangen. Geen automatische
     opruiming van een wees-rij als een project definitief verwijderd
     wordt (bewust, klein en onschadelijk: een ongebruikte rij kost
     alleen wat schijfruimte) — kandidaat voor een latere opschoning.
     4 nieuwe tests (`tests/test_zaagplannen_opslag.py`): herstart-
     round-trip (incl. fabriekskantenband/kantenband-velden), lege
     opslag geeft `None`, opnieuw opslaan overschrijft i.p.v. een tweede
     rij toe te voegen, en verwijderen.
  Geverifieerd: volledige testsuite groen (132 tests, was 124), een
  breder fuzz-script (7 seeds × 400 runs, overlap/buiten-plaat/
  fabrieksrand/snede-kruist-plaatsing/multi-plaat-volledigheid) op 0
  fouten, `demo_render.py` opnieuw visueel gecontroleerd, en een
  offscreen smoke-test van de volledige opslaan→nieuw-tabblad-openen→
  automatisch-herladen-cyclus op een kopie van de echte database.

- **Modeldetailtabblad afgemaakt: ook "nieuw model" opent nu een
  tabblad, en het onderdelenformulier staat voortaan naast de lijst
  i.p.v. eronder.** De vorige sessie had `model_detail_page.py`
  (`ModelDetailPage`) al gebouwd voor het BEWERKEN van een bestaand
  model (zelfde losse-tabblad-patroon als `ProjectDetailPage`), maar
  "nieuw model toevoegen" in `modellen_page.py` viel toen nog terug op
  het oude uitklappaneel. Op Svens verzoek ("ik wil ook dat met eerste
  instantie als je nieuw model toevoegd dat hij een tab opent inplaats
  van het oude menu dat rechts verschijnt") is dat nu gelijkgetrokken:
  `MainWindow._open_tab_model(model_id=None)` opent ook voor een nieuw
  model hetzelfde tabblad, met een tijdelijke tabsleutel `"model:new"`
  zolang er nog niet voor het eerst is opgeslagen. Zodra de eerste
  `bibliotheek.toevoegen()` gelukt is, hangt `_model_nieuw_aangemaakt`
  het tabblad in `MainWindow._model_pages`/`_open_tabs` om naar het
  definitieve `f"model:{id}"` (anders zou een latere rijklik op
  datzelfde model een tweede, duplicaat tabblad openen). Annuleren
  vóór die eerste keer opslaan sluit het tabblad direct
  (`on_annuleren_nieuw`) i.p.v. terug te vallen op `_laad_model` (er is
  dan nog niets om naar terug te vallen). Dit wijkt bewust af van
  Projecten, waar nieuw toevoegen nog wél het uitklappaneel gebruikt —
  Sven vroeg dit specifiek voor Modellen, niet als algemene regel.
  Daarnaast, op hetzelfde verzoek ("niet dat dat hele menu eronder
  staat maar dat er dan een menu rechts verschijnt waar je de info kan
  invullen" — Sven corrigeerde zijn eigen eerste "links" expliciet naar
  "rechts"): het onderdeel-toevoeg/bewerkformulier in `ModelDetailPage`
  stond nog inline onder de onderdelenlijst (ongewijzigd overgenomen
  uit het oude uitklappaneel). Herbouwd als split-kaart (lijst links,
  een vaste 300px-formulierkaart rechts, altijd zichtbaar en wisselt
  tussen "NIEUW ONDERDEEL" en "ONDERDEEL BEWERKEN: ...") — hetzelfde
  patroon als de Losse onderdelen-kaart op de projectdetailpagina
  (`project_detail_page.py::_build_losse_onderdelen_kaart`), zie
  `ModelDetailPage._build_onderdelen_kaart`. Submodellen (nesting)
  bleven bewust het eenvoudigere inline-formulier onder de lijst — Sven
  vroeg alleen over onderdelen, en dat formulier is klein (picker +
  aantal) vergeleken met het onderdelenformulier. Het oude
  uitklappaneel in `modellen_page.py` is niet verwijderd (het blijft
  een defensieve terugval als de pagina ooit zonder
  `on_open_model`-callback geconstrueerd wordt) maar wordt door de
  echte app niet meer aangeroepen — beide knoppen ("Model toevoegen" in
  de zijbalk én de hoofdknop) routeren nu via `_nieuw_model_klik` naar
  de tab-callback. Geverifieerd met een offscreen smoke-test
  (`ModelDetailPage` los, in-memory bibliotheken): titel toont "Nieuw
  model", onderdeel toevoegen/bewerken via het rechterpaneel, opslaan
  roept `toevoegen()` aan en triggert `on_aangemaakt`, annuleren vóór
  opslaan triggert `on_annuleren_nieuw`, en een bestaand model laadt
  nog steeds correct — plus de volledige testsuite (132 tests,
  onveranderd, want dit is UI-werk zonder pytest-dekking per de
  conventie in dit bestand).

**Nog open, kandidaten voor een volgende stap:** vóór een echte
(betaalde) release alsnog overstappen op Nuitka + code signing voor de
exe/installer (zie hierboven, bewust uitgesteld voor deze eerste demo);
of revisiegeschiedenis/sandboxes voor projecten in het algemeen (module
1/4, bewust uitgesteld bij het bouwen van de functie — zie
`assets/mockups/projectoverzicht-concept.png` voor een eerder concept
van de projectenlijst zelf); of mes/groef-plaatsingsregels in de motor.
De greedy-heuristieken in de motor ("efficient" incluis, ondanks de
fix hierboven) zijn nog steeds geen bewezen-optimale bin-packing —
voor complexere/grotere projecten kan een geavanceerdere aanpak
(bijv. meerdere heuristieken/volgordes proberen en de beste kiezen,
zoals nu al voor "efficient" gebeurt, maar breder toegepast) nog meer
winst opleveren; bewust niet nu gedaan om de scope beheersbaar te
houden.

- **"Stroken" geschrapt als losse keuze in Opties, motor blijft 'm
  intern gebruiken.** Sven zag "Rijen" en "Stroken" in de praktijk
  steeds hetzelfde zaagplan opleveren en vroeg zich af of dat niet
  hetzelfde is — klopt: het enige verschil zit in de rijhoogte
  (per-rij aangepast bij "Rijen", overal vast bij "Stroken"), niet in
  richting; bij ongeveer even hoge onderdelen komt dat op hetzelfde
  neer. Op zijn bevestiging geschrapt als keuze in
  `GELDIGE_ZAAGSTRATEGIEEN` (`instellingen/models.py`) en uit de
  label-/omschrijving-dicts in `instellingen_page.py`/
  `project_detail_page.py`. De motor zelf (`engine.py`) ondersteunt
  `strategie="stroken"` nog steeds rechtstreeks (`_GELDIGE_STRATEGIEEN`
  ongewijzigd) — "Efficiënt" gebruikt `_pak_stroken` nog steeds als een
  van de vier interne kandidaten (`_kies_beste_pakresultaat`), en de
  bestaande `_pak_stroken`-tests/`demo_render.py` blijven daardoor
  ongewijzigd werken. `project_detail_page.py` kreeg een fallback
  (`_standaard_zaagstrategie()`) voor het geval een project ooit een
  zaagplan had opgeslagen met de inmiddels afgeschafte "stroken"-
  strategie (bleek niet nodig in de echte database, maar voorkomt een
  KeyError-crash mocht dat elders wel zo zijn — zelfde soort
  verdediging als eerder al bestond voor een ongeldige
  `standaard_zaagstrategie`-waarde).
- **Twee motorverbeteringen op Svens verzoek: verticale rij-opvulling
  en meerdere fabriekskantenband-randen.** Beide eerst kort
  afgestemd (AskUserQuestion) omdat de letterlijke formulering
  ("180 graden draaien om de kantenband onder te gebruiken") op het
  eerste gezicht op een echte rotatie leek, terwijl het datamodel geen
  "boven"/"onder"-kant per onderdeel voor fabriekskantenband kent
  (`Onderdeel.fabriekskantenband_vereist` is een simpel ja/nee) — Sven
  bevestigde dat hij bedoelde: als de plaat op meerdere randen
  fabriekskantenband heeft, moet de motor die allemaal benutten.
  1. **Verticale restruimte in een rij/strook wordt nu benut.** Een rij
     werd nooit hoger gevuld dan het grootste stuk erin; de ruimte
     boven een korter onderdeel in diezelfde rij bleef bewust leeg
     (stond letterlijk zo als vereenvoudiging in de code). Nieuwe
     helper `_vul_verticale_restruimte` (engine.py, gebruikt door zowel
     `_pak_rijen` als `_pak_stroken` — gedeeld omdat ze exact dezelfde
     rij-opbouw hebben, zelfde reden als bij `_plaats_rij`): voor elke
     kolom in de zojuist gevulde rij die lager is dan de rijhoogte,
     wordt het eerste nog niet geplaatste onderdeel (hoogte-aflopend
     gesorteerd, zoals de rest van dit bestand al sorteert) dat er —
     eventueel geroteerd als het onderdeel vrij mag roteren — nog in
     past, er bovenop gestapeld, met een eigen horizontale
     scheidingssnede begrensd tot die ene kolom (dus altijd
     rand-tot-rand van zijn eigen deelgebied, net als de rest van de
     motor garandeert). Bewuste vereenvoudiging, met opzet zo
     gedocumenteerd in de code: dit houdt geen rekening met de
     hoogte-groepering uit `_vul_rij`/`_groepeer_op_hoogte` (die
     voorkomt dat identieke onderdelen zonder aanleiding over meerdere
     RIJEN versnipperen) — deze opvulling gebeurt binnen dezelfde rij,
     dus een andere situatie, en een los onderdeel uit een hoogte-groep
     kan hierdoor als eerste van die groep in een kolomgat belanden
     terwijl de rest pas in de volgende rij komt. Efficiëntie krijgt
     hier bewust voorrang boven groepscohesie, want dat laatste is een
     esthetische heuristiek, geen harde eis. Vult per kolom hooguit één
     extra onderdeel (geen recursieve verdere opvulling van het gat dat
     daarna nog overblijft).
  2. **Meerdere fabriekskantenband-randen worden nu allemaal gebruikt.**
     Voorheen koos `genereer_zaagplan` altijd maar één rand uit
     `materiaal.fabriekskantenband_randen` (de eerste match in de
     vaste volgorde links/onder/boven/rechts), ook als de plaat er
     meerdere had — de tweede rand bleef dan altijd ongebruikt, ook als
     de eerste strook al vol zat. Nu wordt een lus over alle
     beschikbare randen in die volgorde gedaan: wat niet meer in de
     eerste rand-strook past, schuift door naar de volgende beschikbare
     rand-strook op dezelfde plaat, vóór het pas echt niet-geplaatst
     raakt (en dus doorschuift naar een volgende, verse plaat). Elke
     gebruikte strook krijgt zijn eigen scheidingssnede, in volgorde
     als eerste sneden op de plaat.
  Geverifieerd met 4 nieuwe pytest-tests in `tests/test_engine.py`
  (verticale opvulling met en zonder rotatie, voor zowel "rijen" als
  "stroken"; meerdere fabriekskantenband-randen vs. maar één rand) —
  volledige testsuite 136 tests, allemaal groen — en een los
  fuzz-script (7 seeds × 300 runs × 4 strategieën, met platen/
  onderdelen/groepen/fabriekskantenband-combinaties, gecontroleerd op
  overlap/buiten-de-plaat/dubbele plaatsing): 0 fouten voor "rijen"/
  "stroken" (de twee aangepaste strategieën), zowel vóór als na de
  wijziging.
  **Bijvangst, apart gemeld aan Sven, NIET meegenomen in deze
  sessie:** datzelfde fuzz-script vond een kleine, al langer bestaande
  bug in `_pak_guillotine` (en dus soms ook in "efficient", wanneer die
  intern de guillotine-uitkomst kiest als beste) — in een enkel
  percent van de fuzz-combinaties plaatst die strategie een onderdeel
  net buiten de plaat of licht overlappend met een ander onderdeel.
  Bevestigd dat dit al bestond vóór deze sessie (gereproduceerd op de
  ongewijzigde code via `git stash`), dus losstaand van het werk
  hierboven — kandidaat voor een volgende sessie.
- **Echte bug gevonden door Sven in het testproject: fabriekskantenband
  hield geen rekening met wélke rand van het onderdeel zelf de band
  nodig had.** Concreet gemeld: op plaat 1 van "Meubelpaneel wit 18"
  (testproject "Keuken Jansen") stond "Dwarsbalk voor" (564×100,
  `kantenband_randen=["boven"]` — de lange 564-zijde moet de band
  raken) 90° geroteerd, waardoor juist de korte kant tegen de rand lag.
  Grondoorzaak: `genereer_zaagplan` gooide alle onderdelen met
  `fabriekskantenband_vereist=True` op één hoop en propte ze tegen
  welke beschikbare rand er toevallig het eerst aan de beurt kwam
  (inclusief roteren indien nodig om te passen) — de eigenlijke
  `kantenband_randen`-eis van het onderdeel (welke van ZIJN randen de
  band nodig heeft) werd nergens gebruikt, dus zowel de verkeerde rand
  als een verkeerde oriëntatie waren mogelijk. Bevestigd met Sven
  (AskUserQuestion) dat de juiste fix is: exact matchen op de
  aangewezen rand, en nooit meer roteren voor zo'n onderdeel. Drie
  onderdelen van de fix, allemaal in `engine.py`:
  1. **`_Eenheid` draagt nu ook `kantenband_randen` mee** (nieuw veld,
     gevuld in `_bouw_eenheden`; voor een groep de unie van alle leden —
     groepen roteren toch al nooit).
  2. **`genereer_zaagplan`'s fabriekskantenband-lus matcht nu per
     onderdeel op de juiste rand(en)**: een onderdeel met
     `kantenband_randen={boven}` wordt alleen aangeboden aan de
     boven-strook, nooit aan onder/links/rechts, ook al heeft de plaat
     die ook. Wijst het onderdeel meerdere randen aan (bv.
     `{onder, boven}`) die de plaat allebei heeft, dan krijgt het een
     kans bij elke van de twee (schuift door naar de volgende als de
     eerste vol zit). Heeft het onderdeel geen enkele rand opgegeven
     (kale, oudere data) of wijst het een rand aan die de plaat niet
     heeft, dan valt het terug op gewoon-onderdeel-plaatsing (oude,
     minder strikte gedrag) — de fabrieksband-route kan dan toch niets
     garanderen.
  3. **`_plaats_fabriek_rand` roteert nooit meer een onderdeel met een
     specifieke `kantenband_randen`-eis**, ook niet als het anders niet
     zou passen (dan is het gewoon niet-geplaatst op déze plaat, net als
     wanneer het te groot is). Onderdelen zonder specifieke rand-eis
     mogen nog wel roteren om te passen, zoals voorheen.
  **Subtielere vervolgvondst tijdens het fuzz-testen van deze fix**: een
  onderdeel met zowel `kantenband_randen` als een eigen
  `nerfrichting_vereist` kan door `_kies_afmeting` alsnog GEDWONGEN
  geroteerd worden om die nerf-eis te respecteren (nerf gaat voor) — dat
  zou de net toegevoegde rand-garantie stiekem weer doorbreken. Nieuwe
  helper `_kantenband_positie_gegarandeerd` sluit zo'n onderdeel daarom
  uit van de rand-matching (valt terug op gewoon-onderdeel-plaatsing,
  net als bij een niet-beschikbare rand hierboven) — in de praktijk
  raakt dit zelden iets, want fabriekskantenband-materialen zijn
  doorgaans nerfrichting "geen" (zoals ook "Meubelpaneel wit 18" hier).
  Geverifieerd met 2 nieuwe pytest-tests (rand-matching zonder rotatie
  met twee onderdelen die ieder een andere rand nodig hebben; het
  nerf-conflict-scenario) — volledige testsuite 138 tests, groen — en
  een uitgebreider fuzz-script (kantenband_randen + nerfrichting +
  fabriekskantenband_randen willekeurig gecombineerd, met een
  toegevoegde controle "een onderdeel met een kantenband-eis die de
  plaat ook echt aanbiedt mag nooit geroteerd staan"): 0 schendingen van
  die controle. Ook geverifieerd tegen de échte testproject-data
  ("Keuken Jansen"): "Dwarsbalk voor" staat nu ongeroteerd met zijn
  lange (564mm) zijde tegen de boven-rand, zoals bedoeld.
- **Nog een echte bug uit hetzelfde testproject: "Rijen"/"Stroken"
  gaven kortere onderdelen elk hun eigen kolom naast elkaar, ook als ze
  samen (gestapeld) ruim in één kolom hadden gepast.** Sven, kijkend
  naar "Melamine grijs 18": twee "Lade rug korf"-stukken (170mm hoog)
  kregen allebei hun eigen kolom (506mm breed), terwijl ze — met een
  derde, nog kortere "Lade rug bestek" (70mm) erbij — samen (170+170+70
  + 2×kerf ≈ 419mm) ruim onder de 500mm rijhoogte van "Lade bodem"
  pasten: "dan zouden alle ruggen toch onder elkaar kunnen en dan nog
  in de rij passen". Bevestigd met Sven (AskUserQuestion) dat dit een
  grotere wijziging in `_vul_rij` zelf rechtvaardigt (onderdelen eerst
  proberen te combineren tot één gestapelde kolom, niet pas achteraf
  opvullen) — dit vervangt meteen ook de eerdere "verticale
  restruimte"-toevoeging van hierboven, die nu overbodig is geworden.
  1. **`_vul_rij` en `_plaats_rij` werken nu met KOLOMMEN i.p.v. een
     platte lijst van losse stukken.** Een kolom is een lijst van één
     of meer op elkaar gestapelde stukken. De eerste (hoogte-bepalende)
     hoogte-groep start nog steeds, lid voor lid, een eigen nieuwe
     kolom (ongewijzigd). Elke latere, kortere hoogte-groep mag nog
     steeds alleen als GEHEEL meedoen (nooit gedeeltelijk — voorkomt
     dat identieke onderdelen zonder aanleiding over meerdere RIJEN
     versnipperen, ongewijzigde regel), maar elk lid ervan wordt nu
     eerst geprobeerd te stapelen bovenop een bestaande kolom (moet
     qua resterende hoogte én breedte passen) vóórdat het, als dat
     nergens lukt, alsnog een nieuwe kolom ernaast krijgt — dit wordt
     eerst voor de HELE groep gesimuleerd (geen echte kolomstaat-
     mutatie) zodat een groep die maar deels ergens past alsnog in zijn
     geheel wordt overgeslagen, dezelfde alles-of-niets-regel als
     voorheen. De functie `_vul_verticale_restruimte` (de eerdere
     toevoeging) en haar losse aanroepen in `_pak_rijen`/`_pak_stroken`
     zijn hierdoor volledig komen te vervallen — dezelfde uitkomst zit
     nu al in `_vul_rij` zelf, en meer (meerdere stukken per kolom
     i.p.v. hooguit één).
  2. **Nieuwe, subtiele bug tijdens het bouwen zelf gevonden door het
     fuzz-script** (dus vóórdat dit bij Sven terechtkwam): als de
     allereerste (hoogte-bepalende) groep zelf geen enkel lid kwijt kon
     (bv. te breed voor wat er nog van de rij over was), bleef
     `rij_hoogte` op 0 staan — die wordt alleen door de eerste groep
     bijgewerkt — terwijl latere, kortere groepen wél gewoon als nieuwe
     kolommen werden toegevoegd. Gevolg: de aanroeper
     (`_pak_rijen`/`_pak_stroken`) dacht dat de rij 0mm hoog was en
     legde de volgende rij vrijwel bovenop de vorige, wat in de fuzz-
     run tot dan toe onopgemerkte overlappende plaatsingen gaf. De
     oorspronkelijke code voorkwam dit met een `if rij and ...`-
     voorwaarde (een latere groep mocht alleen meedoen als de rij al
     niet leeg was) — die voorwaarde was in de nieuwe kolom-gebaseerde
     versie per ongeluk weggevallen; teruggezet als een expliciete
     `if not kolommen: overig.extend(groep); continue`-check vóór een
     latere groep wordt geprobeerd.
  3. **"Stroken" kreeg een aparte parameter** (`beschikbare_hoogte` op
     `_vul_rij`) omdat de vaste, plaatbrede strookhoogte vaak groter is
     dan het hoogste stuk in één specifieke strook — zonder deze
     parameter zou stapelen daar eerder stoppen dan waar de strook in
     werkelijkheid nog ruimte heeft. "Rijen" laat dit leeg (de rij is
     letterlijk zo hoog als zijn hoogste stuk, dus daar is geen verschil).
  Geverifieerd met de bestaande testsuite (138 tests, ongewijzigd
  gebleven — de eerdere "verticale opvulling"-tests dekken toevallig
  ook dit iets algemenere gedrag correct af) en een breder fuzz-script
  (nu ook met willekeurige `kantenband_randen`, zie hierboven, plus een
  check op dubbele plaatsingen) dat de nieuwe "rij_hoogte=0"-bug ving
  vóórdat 'ie ooit bij Sven terechtkwam, en na de fix weer terug was op
  exact dezelfde (drie, al bekende, `_pak_guillotine`-gerelateerde)
  fouten als vóór dit hele iteratieblok. Ook geverifieerd tegen de
  échte testproject-data: alle drie "Lade rug"-onderdelen staan nu in
  één gestapelde kolom i.p.v. twee aparte kolommen, voor alle van
  "rijen" afgeleide strategieën (`rijen`, `stroken`, `efficient`).
- **Labels — module 6, v1 gebouwd: onderdeel-labels vanuit een
  gegenereerd projectzaagplan, met QR-/barcode.** Op Svens verzoek
  vóór verder motorwerk opgepakt. Hoofdstuk 6 was al volledig
  ontworpen maar liet een paar dingen bewust open ("verder uit te
  werken bij hoofdstuk 8" — dat hoofdstuk noemt labels/scancodes
  echter nergens) — drie scope-keuzes eerst met Sven kortgesloten
  (AskUserQuestion):
  1. **Alleen onderdeel-labels in v1**, geen reststuk-labels. Een
     reststuk-label (hoofdstuk 6: zelfde velden, zonder
     projectnummer) is een aparte, latere stap — er bestaat ook nog
     geen "reststukken vrijgeven vanuit een zaagplan"-koppeling (zie
     "Nog niet gebouwd" verderop), dus reststuk-labels zouden voorlopig
     toch alleen aan handmatig in de Reststukkenbibliotheek ingevoerde
     reststukken kunnen hangen.
  2. **Scancode nu al echt bouwen**, niet uitstellen. Nieuwe
     dependencies: `qrcode` (voor de QR-optie — `get_matrix()` geeft
     een boolean-rooster, vereist geen Pillow) en `python-barcode`
     (voor de barcode-optie — `Code128(...).build()` geeft een
     "1010..."-string op module-resolutie; Code128 i.p.v. Code39 omdat
     het gewoon alle ASCII aankan, dus geen sanitizen van de
     scancode-waarde nodig). Beide alleen als rechthoekjes getekend
     met dezelfde `QPainter`-aanpak als de rest van de PDF-export —
     geen afbeeldingsbestand, geen Pillow-afhankelijkheid. De
     scancode-inhoud is bewust alléén een uniek record-ID (bv.
     `RC:onderdeel:<project_id>:<materiaal_id>:<onderdeel_id>:<instantie>`),
     geen URL/online schema — logisch voor een offline, single-user app
     zoals RoboCutter nu is; er is ook nog geen "scan om record te
     openen"-functie, dit is puur het label zelf.
  3. **PDF-vel voor een gewone A4-printer**, net als de zaagplan-PDF
     van de grond af opgebouwd met `QPainter` — géén specifiek
     labelprinter-formaat (hoofdstuk 6 noemt dat expliciet als open
     vraag, later te bepalen met een echte printer erbij).
  Gebouwd, backend-eerst zoals gebruikelijk:
  - `src/robocutter/projecten/labels.py` (nieuw): `OnderdeelLabel` +
    `genereer_labels_voor_project(project, plannen)` — één label per
    `Plaatsing` in de `PlaatZaagplan`-lijst van `zaagplannen.py` (dus
    ook meerdere labels voor meerdere exemplaren van hetzelfde
    onderdeel; niet-geplaatste onderdelen krijgen terecht geen label).
    Puur data, geen QR/barcode-afhankelijkheid hier — dat zit alleen in
    de renderer, zodat dit bestand net als `zaaglijst.py`/
    `zaagplannen.py` zonder UI-dependencies test-baar blijft.
  - `zaagplannen.py`'s `OnderdeelInfo` kreeg er een veld
    `nerfrichting_vereist` bij (voorheen ontbrak dat — de
    nerfrichting-pijl op een label heeft dit nodig). `zaagplannen_opslag.py`
    is meegewerkt met een `.get(..., "geen")`-fallback bij het
    terugladen, zodat een vóór deze stap opgeslagen zaagplan (zonder
    dit veld) niet crasht.
  - `src/robocutter/instellingen/models.py`: drie nieuwe velden —
    `label_scancode` (`GELDIGE_LABEL_SCANCODES` = "geen"/"qr"/"barcode",
    default "qr"), `label_kantenband_indicatie` en
    `label_nerfrichting_pijl` (beide default `True`) — "één algemene
    instelling", niet iets wat je telkens opnieuw kiest bij het
    printen, exact zoals hoofdstuk 6 voorschrijft. `beheer.py`/`opslag.py`
    bijgewerkt (validatie resp. JSON-serialisatie); een nieuwe kaart
    "LABELS" in `instellingen_page.py` (segmented control voor de
    scancode, twee checkboxes) tussen de bestaande "Algemeen"- en
    "Opslaglocatie"-kaarten, met een eigen Opslaan-knop/banner (zelfde
    patroon als de andere kaarten daar).
  - `src/robocutter/ui/label_pdf.py` (nieuw): `schrijf_labels_pdf` —
    een rooster van labels (64×38mm, ruim voldoende leesbaar formaat
    zonder aan een specifiek printermerk vast te zitten) over zoveel
    A4-pagina's als nodig. Elk label toont onderdeelnaam, materiaal,
    afmeting (mono, groot) en projectnummer altijd; kantenband-indicatie
    en de nerfrichting-pijl (een klein zelfgetekend pijl-icoontje —
    horizontaal voor "lange zijde", verticaal voor "korte zijde", geen
    pijl bij "geen") alleen als de bijbehorende instelling aan staat;
    scancode rechtsboven (QR, vierkant) of als volle-breedte strook
    onderaan (barcode) als die instelling niet op "geen" staat.
  - `project_detail_page.py`: de "Labels"-tab in het projectdetailscherm
    was tot nu toe een "binnenkort"-placeholder — vervangen door een
    echt paneel, opgezet als zusje van het Zaagplannen-paneel ernaast
    (zelfde `_labels_content`/`_ververs_labels_paneel()`-patroon): zolang
    er nog geen zaagplan is, dezelfde placeholder-stijl met een
    doorverwijzing naar Zaagplannen; zodra er wel een zaagplan is, een
    tabel (Onderdeel/Materiaal/Afmeting/Kantenband/Nerfrichting) plus een
    "Labels als PDF"-knop. Labels worden **niet** los opgeslagen — ze
    worden, net als het zaagplan zelf, telkens opnieuw afgeleid
    (`genereer_labels_voor_project`) van het laatst opgeslagen/
    gegenereerde zaagplan, en het paneel ververst zichzelf meteen mee
    zodra er een (nieuw) zaagplan gegenereerd wordt.
  Gedekt door `tests/test_labels.py` (4 nieuwe tests: één label per
  geplaatst exemplaar, kantenband/nerfrichting-overname, geen label
  voor niet-geplaatste onderdelen, leeg project geeft lege lijst) en een
  uitgebreide `test_instellingen.py` (nieuwe labelvelden in de
  opslaan/laden-roundtrip, plus een validatie-test voor een onbekende
  scancode-waarde) — volledige testsuite 143 tests, allemaal groen.
  Los geverifieerd met een offscreen smoke-test: labelgeneratie en
  PDF-export voor alle drie scancode-standen (geen/qr/barcode), het
  Labels-paneel in `ProjectDetailPage` (navigeren, zaagplan genereren,
  thema-wissel) en de nieuwe LABELS-kaart in `InstellingenPage`
  (waarden wijzigen, opslaan, thema-wissel) — telkens op een tijdelijke
  in-memory/tmp-opzet, nooit op `data/robocutter.db` zelf.
  **Bewust nog niet gedaan**: reststuk-labels (zie boven), een
  "niet gecontroleerd"-detectie zodra de onderliggende data wijzigt na
  het genereren (hoofdstuk 6 noemt dit, maar dat mechanisme bestaat ook
  voor zaagplannen zelf nog niet — zie `zaagplannen_opslag.py`), en
  ondersteuning voor een specifiek labelprinter-formaat (alleen het
  A4-vel).

- **Echte zaagmotor-bug gevonden en gefixt via fuzz-testen, op Svens
  verzoek** ("alle platen geven nog veel bugs en zijn niet efficiënt
  genoeg"). Een uitgebreid fuzz-script (20 seeds × 1000 runs × 4
  strategieën, incl. willekeurige randafzaag/min-reststukgrootte/
  fabriekskantenband/nerfrichting-combinaties — zie de aanpak in
  eerdere iteraties hierboven) liet zien dat "efficient" en
  "guillotine" in ongeveer 0,05% van de gevallen een onderdeel net
  buiten de plaatrand plaatsten. **Grondoorzaak, in zowel
  `_pak_efficient` als `_pak_guillotine` (`engine.py`)**: na een
  plaatsing werd bepaald of er nog een kerf verrekend moest worden
  door te toetsen aan de rand van de HELE plaat (`x1`/`y1`) in plaats
  van aan de rand van het op dat moment behandelde vrije rechthoek zelf
  (`fw`/`fh`) — bij een intern vrij rechthoek dat al eerder ophoudt dan
  de plaatrand is dat verschil onschuldig, maar zodra de resterende
  marge kleiner was dan de kerf zelf (bv. nog maar 1mm over terwijl de
  kerf 4mm is) werd er alsnog een volle kerf afgetrokken, zonder dat
  `genomen_b`/`genomen_h` afgetopt werden op `fw`/`fh` — het
  resulterende "vrije" rechthoek ernaast/eronder werd daardoor een fractie
  te BREED/HOOG berekend, waardoor een net iets te groot onderdeel er
  alsnog in "paste" en over de plaatrand heen kwam te staan. Fix: de
  kerf-toets gebruikt nu `fw`/`fh` i.p.v. `x1`/`y1`, en `genomen_b`/
  `genomen_h` worden expliciet afgetopt op `fw`/`fh` (`min(b + kerf_r,
  fw)`). Nieuwe regressietest `test_krappe_restmarge_kleiner_dan_de_kerf_geeft_geen_plaatsing_buiten_de_plaat`
  (`tests/test_engine.py`, geparametriseerd over "efficient"/
  "guillotine") gebruikt het exacte, met fuzz-testen teruggevonden
  scenario (materiaal 2620×1552mm, kerf 4mm, 10 onderdeeltypes) —
  bevestigd dat deze test faalt op de ongewijzigde code (`git stash`)
  en slaagt na de fix. Volledige testsuite nu 145 tests, allemaal
  groen. Een vervolg-fuzzrun van 20 seeds × 1000 runs × 4 strategieën
  (80.000 runs totaal) na de fix: **0 fouten** (was voorheen enkele
  tientallen over eenzelfde schaal, geconcentreerd in "efficient"/
  "guillotine" — "rijen" en "stroken" hadden deze bug niet, want die
  gebruiken een andere kolom-gebaseerde plaatsingsroute).
  **Efficiëntie, ter info (nog niet aangepakt)**: gemiddelde benutting
  over dezelfde fuzzrun was efficient 73%, guillotine 76%, rijen 71%,
  stroken 33% (stroken's vaste, plaatbrede strookhoogte is hier
  duidelijk de boosdoener bij ongelijk hoge onderdelen — geen bug, wel
  een reëel efficiëntieverschil, en "stroken" is toch al geen
  gebruikerskeuze meer, alleen nog een interne kandidaat voor
  "efficient"). Sven wil de zaagmotor nog verder onder de loep nemen op
  efficiëntie — dit is de eerste, geverifieerde bugfix-stap daarvan;
  een bredere efficiëntie-iteratie (bv. meer/betere heuristieken
  proberen) is een vervolgstap.

- **Zaagmotor: optioneel "zoekbudget" toegevoegd, op Svens verzoek**
  ("ik heb liever dat je het zo aanpakt dat ie het goed doet en dat je
  dan even moet wachten op het resultaat zodat ie goed kijkt waar alle
  items kunnen en wat het beste is rekening houdend met de
  zaagstrategie" — scope bevestigd via AskUserQuestion: alle drie
  gebruikerskeuzes (Efficiënt/Rijen/Guillotine), max ongeveer een
  minuut).
  1. **`genereer_zaagplan`/`genereer_zaagplannen` (`engine.py`) kregen
     een nieuwe, optionele parameter `zoek_tijdsbudget`** (seconden,
     standaard `0.0` = uitgeschakeld, exact het oude gedrag). Met een
     budget > 0 blijft de motor, ná de bestaande deterministische
     plaatsing, extra verwerkingsvolgordes proberen (nieuwe helper
     `_ruis_sleutel` voor "efficient"/"guillotine": vermenigvuldigt de
     grootte-sorteersleutel met een kleine willekeurige factor) en houdt
     steeds de beste uitkomst (`_kies_beste_pakresultaat`, ongewijzigd)
     — een nieuwe poging vervangt de tot dan toe beste alleen bij een
     STRIKTE verbetering, nooit bij een gelijke stand, zodat een
     triviaal zaagplan zonder betere volgorde exact hetzelfde resultaat
     oplevert als zonder budget. Stopt vanzelf eerder dan het budget
     zodra `_MAX_POGINGEN_ZONDER_VERBETERING` (300) pogingen op rij
     niets beters meer opleveren. `genereer_zaagplannen` (meerdere
     platen) behandelt het budget als TOTAAL over alle platen van die
     aanroep samen (aftellend per plaat), niet per plaat afzonderlijk —
     anders zou een project met meerdere platen een veelvoud van het
     ingestelde budget kunnen gaan duren.
  2. **Belangrijke bug gevonden tijdens het testen van deze feature
     zelf** (dus vóórdat dit bij Sven terechtkwam): dezelfde
     `_ruis_sleutel`-aanpak toegepast op "Rijen"/"Stroken" bleek
     rijen te kunnen opleveren die HOGER waren dan de resterende
     plaathoogte toestond (dus buiten de plaat, of overlappend met de
     volgende rij) — grondoorzaak: `_pak_rijen`/`_pak_stroken` (en de
     helpers `_vul_rij`/`_vind_plaatsbare_rij` eronder) gaan er
     STRUCTUREEL van uit dat de sortering op hoogte strikt aflopend is
     (een latere hoogte-groep is nooit hoger dan een eerdere) — ruis op
     de sorteersleutel zelf kan die aanname breken (een kort onderdeel
     dat door ruis toevallig vóór een lang onderdeel komt). Fix: nieuwe,
     veiligere helper `_sorteer_op_hoogte_met_ruis` sorteert eerst
     gewoon exact op hoogte (ongewijzigd), en husselt daarna alleen de
     volgorde BINNEN elke (bijna) gelijke-hoogte-groep (``_HOOGTE_TOLERANTIE``)
     door elkaar — dat is altijd veilig, want de leden van zo'n groep
     verschillen per definitie nauwelijks in hoogte. "efficient" en
     "guillotine" gebruiken nog steeds de vrijere `_ruis_sleutel` op hun
     eigen (structureel ongevoelige) grootte-sortering.
  3. **UI (`project_detail_page.py`)**: "Zaagplan genereren"/"Opnieuw
     genereren" roepen `genereer_zaagplannen_voor_project` nu aan met
     `zoek_tijdsbudget=60.0` (nieuwe module-constante
     `_ZOEK_TIJDSBUDGET_SECONDEN`). Omdat dit de UI tot een minuut kan
     laten "hangen" zonder feedback, toont `_genereer_zaagplannen` eerst
     meteen een "Bezig met zoeken naar het beste zaagplan…"-kaart
     (`_bouw_zaagplan_bezig`, zelfde kaart-stijl als de bestaande
     "Nog geen zaagplan"-placeholder) en zet een wachtcursor
     (`QApplication.setOverrideCursor`) voor de duur van de berekening.
     Geen aparte achtergrond-thread — een bewuste vereenvoudiging, dus
     de rest van de UI is écht bevroren tijdens het zoeken (acceptabel
     voor v1, gegeven dat Sven expliciet aangaf te willen wachten op het
     resultaat); een achtergrond-thread met voortgang is een kandidaat
     voor een latere iteratie als dit in de praktijk hinderlijk blijkt.
  Geverifieerd: volledige testsuite nu 149 tests (4 nieuwe: budget=0
  geeft bewijsbaar exact hetzelfde resultaat als voorheen; drie
  scenario's — één per strategie, teruggevonden via fuzz-zoeken — waar
  een budget aantoonbaar minder niet-geplaatste onderdelen oplevert dan
  zonder budget), plus een brede geometrie-fuzzrun (450 runs, gevarieerde
  materiaal-/onderdeel-parameters incl. fabriekskantenband/nerfrichting,
  mét budget ingeschakeld): **0 fouten**. Een losse verbeter-zoekscript
  liet op willekeurige scenario's concrete winst zien binnen de
  stagnatie-grens (bijv. 33→27 en 13→11 niet-geplaatste stuks op
  dezelfde plaat), typisch binnen een fractie van een seconde tot een
  paar tellen — het volle budget wordt dus alleen echt volledig benut
  bij grotere/lastigere zaagplannen waar steeds weer een betere volgorde
  te vinden is. Ook geverifieerd met een end-to-end offscreen smoke-test
  van de echte UI-flow (`ProjectDetailPage._genereer_zaagplannen` met
  een tijdelijke database): bezig-kaart, generatie, opslaan, geen
  crash.
  **Status na het zelf uitproberen: Sven is nog niet helemaal tevreden**
  met het resultaat van de zaagmotor — geen concreet gemelde bug dit
  keer, meer een algemeen gevoel dat het nog beter kan. Bewust
  gepauzeerd ("dit pakken we een andere keer weer op") in plaats van
  blind door te itereren zonder concrete richting; wacht op verdere
  feedback/een concreet voorbeeld van Sven voordat hier verder aan
  gewerkt wordt.

- **Zaagmotor-vervolg: "waarom niet geplaatst"-redenen, laad-animatie
  met minimale denktijd, en twee echte "Rijen"-bugs gevonden via Svens
  eigen testproject.** Vervolg op de pauze hierboven — dit keer wél met
  concrete voorbeelden.
  1. **`ZaagplanResultaat` kreeg een nieuw veld `niet_geplaatst_redenen`**
     (`dict[unit_id, Nederlandse uitleg]`, `engine.py`'s nieuwe
     `_reden_niet_geplaatst`) — op Svens verzoek ("ik wil ook een functie
     als hij niks plaatst dat ie aangeeft ... waarom hij deze item niet
     heeft geplaatst"). Drie categorieën: (a) te groot voor de plaat, ook
     na roteren; (b) past alleen geroteerd maar nerf/groep verbiedt dat;
     (c) past qua afmeting wel maar kreeg toch geen plek (wijst op een
     zwakte in de plaatsingsstrategie, geen afmetingsprobleem). Later
     uitgebreid met een vierde: (d) een onderdeel met een
     `kantenband_randen`-eis op een rand die het materiaal al als
     fabriekskantenband heeft roteert daar NOOIT (bestaande regel, zie
     `_plaats_fabriek_rand`) — past het dan niet, dan is (c)'s "probeer
     opnieuw"-advies misleidend, want geen zoekbudget of extra plaat
     helpt hier ooit. `PlaatZaagplan.reden_voor()` (zaagplannen.py) en
     `zaagplannen_opslag.py` (serialisatie, met `.get(...,{})`-terugval
     voor oudere opgeslagen plannen) sluiten hierop aan.
  2. **UI**: de kale "⚠ Niet geplaatst: naam, naam"-tekst in
     `project_detail_page.py`'s Zaagplannen-paneel is vervangen door een
     getinte waarschuwings-kaart (`_bouw_niet_geplaatst_banner`, nieuwe
     `NietGeplaatstBanner`-stijlregels in `theme.py`) met per item de
     naam (×aantal) én de reden op een eigen regel — op Svens verzoek
     ("de foutmelding mag wel wat netter en cleaner geshowt worden").
  3. **Laad-animatie + minimale denktijd**: het zoekbudget draaide tot nu
     toe synchroon op de UI-thread (bewuste vereenvoudiging, zie hoger in
     dit document) — Sven vroeg nu expliciet om een echte laad-animatie
     tijdens het genereren én een minimale denktijd van "10 seconden
     ofzo", ook als het zaagplan feitelijk al meteen klaar zou zijn.
     Beide zijn nu gebouwd: `engine.genereer_zaagplan`/`genereer_zaagplannen`
     kregen een nieuwe parameter `min_zoek_tijdsbudget` — de zoeklus stopt
     niet meer vanwege `_MAX_POGINGEN_ZONDER_VERBETERING`-stagnatie vóórdat
     die minimumtijd verstreken is (begrensd door het totale
     `zoek_tijdsbudget` zelf). `project_detail_page.py`'s
     "(Opnieuw) genereren" draait nu op een eigen thread
     (`_ZaagplanWorker(QThread)`, nieuwe module-constante
     `_MIN_ZOEK_TIJDSBUDGET_SECONDEN = 10.0`) i.p.v. de UI te blokkeren —
     de eerder gedocumenteerde "geen achtergrond-thread"-vereenvoudiging
     is dus nu ingehaald. Een nieuw draaiend laad-icoontje
     (`_ZaagplanSpinner`, nieuw "loader"-icoon in `icons.py`, geroteerd via
     een `QTimer`) toont daadwerkelijk beweging tijdens het wachten i.p.v.
     de eerdere statische "Bezig..."-tekst.
  4. **Bug 1 (band-batching regressie)**: bij het uitbreiden van
     `_vul_rij`/`_plaats_rij` om meerdere onderdelen side-by-side in één
     kolom-"band" te laten passen (Svens concrete "bodem 500mm + 4
     dwarsbalken in een strook van 100mm"-voorbeeld — nu een kolom bevat
     een lijst van banden, en een band zelf een lijst van side-by-side
     leden), bleek een TWEEDE lid van dezelfde (kortere) hoogte-groep dat
     nergens op een bestaande kolom paste altijd zijn eigen, nieuwe kolom
     te krijgen — ook als hij prima op de kolom van het EERSTE lid van
     diezelfde groep had gepast (Svens eigen "melamine grijs"-voorbeeld:
     een tweede "lade rug korf" die niet stapelde op de kolom van de
     eerste, terwijl dat wél had gepast — een regressie t.o.v. het
     eerdere, sequentiële per-item-kolomzoeken). Fix: de kolomronde wordt
     nu herhaald ("fixed point"-lus) na elke nieuw aangemaakte kolom, dus
     ook latere leden van dezelfde groep krijgen een kans op die kolom te
     stapelen.
  5. **Bug 2 (geen bug, een datafoutje)**: Svens andere gemelde geval
     ("plaat 5/8 van Meubelpaneel wit 18, stijlen passen makkelijk achter
     het passtuk") bleek bij nader onderzoek (op een kopie van
     `data/robocutter.db`, alleen-lezend, project "Keuken Jansen") geen
     algoritme-bug: het materiaal is 600mm breed met fabriekskantenband op
     onder/boven, en twee onderdelen ("Bodem"/"Dwarsbalk vooraan") eisen
     kantenband op "Onder" terwijl ze ongeroteerd 864mm diep zijn — meer
     dan de plaat breed is, op ELKE plaat van dat materiaal. Sven
     bevestigde dit zelf ("oke dus de fout ligt bij de gebruiker").
  6. **Verificatie**: volledige testsuite (161 tests, waarvan 9 nieuw op
     deze twee stappen: reden-categorieën, `min_zoek_tijdsbudget`-gedrag,
     en Svens twee exacte scenario's als regressietests) en een ad-hoc
     fuzz-script (25 seeds × 400 random scenario's × 4 strategieën =
     40.000 runs, overlap/rand/snede-checks) vóór en na de band-batching-
     wijziging: **0 fouten**, geen regressie t.o.v. de bestaande code.

- **Kantenband-/randafzaag-randen als klikbare tekening (n.a.v. het
  datafoutje hierboven).** Svens datafoutje (kantenband op de verkeerde
  rand voor de opgegeven afmetingen) bracht 'm op een UX-idee om dit soort
  fouten te voorkomen: i.p.v. vier losse "Links/Rechts/Onder/Boven"-
  knoppen zonder enig verband met de vorm, een rechthoek-tekening met de
  echte afmetingen als maatlijn, waarbij je de rand rechtstreeks op de
  tekening zelf aanklikt. Eerst een HTML/Artifact-mockup gebouwd en door
  Sven goedgekeurd (twee voorbeelden met zijn eigen "Keuken Jansen"-data:
  het "Bodem"-onderdeel en materiaal "Meubelpaneel wit 18", inclusief een
  live waarschuwing die precies het net gevonden datafoutje laat zien).
  Daarna uitgewerkt in PySide6:
  - Nieuw, herbruikbaar widget `src/robocutter/ui/widgets/randen_diagram.py`
    (`RandenDiagram`, met QPainter voor de rechthoek/maatlijnen en vier
    absoluut-gepositioneerde `QToolButton`s als klikbare randzones) —
    bewust in `widgets/` i.p.v. per-bestand gedupliceerd zoals de oude
    `_rand_chip_rij` (zie de "Shared helpers"-conventie): dit is een
    complete, custom-getekende widget, geen klein one-linertje, dus hier
    is hergebruik de betere afweging.
  - Vervangt `_rand_chip_rij` op alle drie de plekken waar dat nog echt
    gebruikt werd: `materialen_page.py` (`randafzaag_randen` én
    `fabriekskantenband_randen`, rechthoek = lengte×breedte),
    `model_detail_page.py` (`kantenband_randen` per onderdeel, rechthoek =
    breedte×hoogte — dit is het échte, actieve modeldetail-tabblad;
    `modellen_page.py`'s eigen kopie is een niet meer aangeroepen
    defensieve terugval en is bewust ongemoeid gelaten) en
    `project_detail_page.py` (losse onderdelen, zelfde patroon). Elk
    scherm verversd de getoonde afmetingen live zodra de bijbehorende
    lengte/breedte- of breedte/hoogte-velden wijzigen.
  - **Ook, op Svens verzoek** ("een knop bij lengte en breedte waar je
    makkelijk lengte en breedte kan omdraaien als je het per ongeluk net
    andersom hebt ingevuld"): een omwissel-knop (nieuw "swap"-icoon in
    `icons.py`) naast elk lengte/breedte- resp. breedte/hoogte-veldpaar in
    diezelfde drie schermen, die de twee waarden in één klik verwisselt —
    precies de fix voor het soort datafoutje dat tot dit alles leidde.
  Geverifieerd met offscreen smoke-tests per scherm (widget opbouwen,
  afmetingen live bijwerken, rand aan-/uitklikken, omwisselen, opslaan/
  teruglezen, thema-wissel) op tijdelijke databases; volledige testsuite
  ongewijzigd 161 tests groen (dit is UI-werk zonder pytest-dekking, zie
  Architectuur-sectie).

- **Zaagplan genereren: bevriezing bij start opgelost + voortgangsbalk.**
  Svens twee openstaande punten bij het laadscherm ("het moment je op
  zaagplan genereren drukt hij even vastloopt" en "een laadbalk ... zodat
  de gebruiker kan zien hoelang het ongeveer gaat duren en hoe ver hij
  is"):
  1. **Bevriezing**: gemeten (offscreen, op een kopie van de db) — de
     Qt-event loop stond ~3,2 s stil direct na de klik, terwijl de
     worker-thread meteen startte. Oorzaak: GIL-contentie, niet de motor
     zelf. Qt heeft voor het eerste opbouwen/tekenen van de "bezig"-kaart
     honderden keren kort de GIL nodig (PySide6 checkt per virtuele
     methode van een Python-widget-subklasse op een Python-override) en
     wachtte telkens tot het standaard-wisselinterval van 5 ms voorbij
     was, omdat de worker onafgebroken rekende. De gap schaalde lineair
     met `sys.setswitchinterval` (5 ms → 3,2 s, 1 ms → 0,7 s, 0,2 ms →
     niet meer merkbaar). Fix: `_ZaagplanWorker` zet het interval op
     `_GIL_WISSELINTERVAL_TIJDENS_GENEREREN = 0.0002` zolang er minstens één
     worker draait (teller met lock, want meerdere projecttabbladen kunnen
     tegelijk genereren) en zet het daarna terug. Grootste UI-stilstand
     tijdens genereren is nu ~50 ms.
  2. **Voortgangsbalk**: `engine.genereer_zaagplan` kreeg een optionele
     `voortgang(fractie)`-callback (max. elke 0,1 s tijdens de zoeklus,
     nooit dalend, altijd afgesloten met 1.0 — schatting via
     `_zoek_fractie`: 90% van de balk voor de minimale denktijd, de rest
     voor de staart tot het pogingen- of tijdsplafond);
     `genereer_zaagplannen` geeft die door als `(plaat_nummer, fractie)`;
     nieuwe `engine.schat_aantal_platen` (oppervlakte / werkgebied bij 80%
     benutting). `projecten.zaagplannen.genereer_zaagplannen_voor_project`
     combineert dit tot een `ZaagplanVoortgang` over álle materialen
     samen, waarbij elke plaat even zwaar weegt (elke plaat kost
     ongeveer de minimale denktijd) — geschat aantal platen tot een
     materiaal klaar is, daarna het echte aantal. De "bezig"-kaart toont
     nu een balk, "Materiaal X van Y: naam · plaat N" en "NN% · nog
     ongeveer … " (lineair doorgetrokken uit de verstreken tijd, afgerond
     op 5 s, pas vanaf 3%). Blijft een schatting: als een materiaal meer
     platen nodig heeft dan geschat staat de balk even stil. De kaart
     wordt bij een thema-wissel tijdens het genereren nu ook correct
     herbouwd (voorheen verving `_ververs_alles` 'm door het start- of
     oude resultaatscherm), en een tweede klik tijdens het genereren
     start geen tweede worker meer.
  Geen HTML-mockup vooraf: aanpassing van een bestaande laadkaart, geen
  nieuw scherm. 5 nieuwe tests (166 totaal, groen).
  3. **Minimale denktijd 10 s → 3 s, tijdsplafond weg.** Een meting per
     plaat op "Keuken Jansen" (Efficiënt) liet zien dat (a) álle
     verbeteringen binnen ~2,1 s gevonden werden (10.000–20.000 pogingen
     per plaat in 2 s, 15.000–30.000 in 3 s) en (b) het gedeelde 60 s-
     budget per materiaal na 6 platen × 10 s op was, waardoor plaat 7 en 8
     van Meubelpaneel wit 18 geen enkele zoekpoging kregen. Op Svens
     besluit ("minimaal op 3 zetten en maximaal weglaten"):
     `_MIN_ZOEK_TIJDSBUDGET_SECONDEN = 3.0`, `_ZOEK_TIJDSBUDGET_SECONDEN =
     math.inf` (de motor ondersteunde dat al; nu gedocumenteerd + getest).
     Zonder plafond stopt elke plaat na de 3 s zodra
     `_MAX_POGINGEN_ZONDER_VERBETERING` pogingen op rij niets opleveren —
     in de meting telkens binnen milliseconden na die 3 s. Resultaat op
     Keuken Jansen: ~90 s → ~30 s, en 10 i.p.v. 11 platen (de vroeger
     overgeslagen plaat 7 krijgt nu wél zoektijd en neemt de rest mee).
     Bewust risico: zonder plafond is er geen harde bovengrens meer als
     een plaat heel lang blijft verbeteren — in de praktijk niet gezien
     (max. 3 verbeteringen per plaat). 1 nieuwe test (167 totaal).

- **Fabriekskantenband: onderdelen draaien nu naar de juiste rand.**
  Sven: "de stijlen hebben een fabrieksrand maar liggen niet tegen een
  fabrieksrand" (Keuken Jansen, Meubelpaneel wit 18: 2800×600,
  fabrieksband onder/boven). Oorzaak: de fabrieksband-route probeerde
  alleen de ongedraaide stand — een onderdeel moest de plaatrand zelf
  letterlijk in zijn `kantenband_randen` hebben. Een stijl (60×802, band
  "links" = lange zijde) of zijkant (band "links") matchte dus nooit
  met onder/boven en viel terug op een gewone plaatsing; dat de zijkanten
  toch tegen de onderrand lagen was toeval (Rijen vult van onder af).
  Ook een dwarsbalk met band "onder" kon niet naar de (lege)
  bovenstrook als de onderstrook vol was, en schoof door naar een nieuwe
  plaat. Fix: nieuwe `_fabriek_orientaties(eenheid, plaat_rand)` in
  `engine.py` (vervangt `_kantenband_positie_gegarandeerd`) bepaalt welke
  stand(en) een van de eigen band-zijdes tegen die plaatrand leggen:
  halve slag altijd toegestaan (afmetingen/nerf veranderen niet), een
  kwartslag alleen als het onderdeel vrij mag roteren, anders alleen de
  door de nerf afgedwongen stand; groepen draaien nooit. Een halve slag
  hoeft niet apart in `Plaatsing` vastgelegd te worden: niets tekent de
  band per onderdeel op de plaat (alleen als tekst), en de band zit na
  het zagen hoe dan ook op de juiste zijde. Gecontroleerd op een kopie van
  de db (Rijen): alle fabrieksband-onderdelen raken nu met de juiste zijde
  een fabrieksrand, Meubelpaneel wit 18 van 9 naar 8 platen. 2 nieuwe
  tests + 1 aangepast (169 totaal).
  **Bekende eigenschap (door Sven geaccepteerd)**: een fabrieksband-
  strook claimt de volle plaatlengte ter diepte van zijn diepste stuk,
  ook als hij maar deels gevuld is — gewone onderdelen kunnen daar dus
  niet in (bv. plaat 6: Bodem 564×540 + Dwarsbalk 564×100 op 21%).
  Sven: "dat is iets wat helaas kan gebeuren met deze strategie de rest
  moet gewoon als rest stuk bewaard worden". Tot dan telde die ruimte
  nergens mee (geen reststuk, geen afval) en zaagde geen snede 'm af.
  Fix: nieuw `_strook_restruimte` in `engine.py` levert de lege ruimte
  binnen elke strook (achter het laatste stuk, en boven stukken die
  ondieper zijn dan de strook) als vrije rechthoeken voor
  `_classificeer_restruimte`, plus de sneden daarbinnen (dwars tussen de
  stukken en voor het eindstuk, evenwijdig boven ondiepere stukken) — die
  sneden bestonden eerder ook tussen de strookstukken onderling niet.
  `_plaats_fabriek_rand` geeft daarvoor nu 8 waarden terug. Plaat 6 heeft
  nu reststukken 1666×540 en 564×437. 5 nieuwe tests (174 totaal) + fuzz
  uitgebreid met reststuk-checks (binnen de plaat, geen overlap met
  onderdelen of elkaar): 4500 runs, 0 fouten.

- **Strategie "Rijen" heet nu "Horizontaal", nieuwe strategie "Verticaal".**
  Sven: "rijen hernoemen naar horizontaal en dan een extra strategie
  genaamd verticaal die hetzelfde doet maar dan in plaats van de hoofd
  zaagsnedes horizontaal over de plaat verticaal over de plaat".
  - Hernoeming overal (`GELDIGE_ZAAGSTRATEGIEEN` = efficient/horizontaal/
    verticaal/guillotine, engine, UI-labels + omschrijving in Opties,
    tests, `demo_render.py`). Oude opgeslagen waarde `"rijen"` (Svens
    eigen opgeslagen zaagplan stond er zo in; `instellingen.json` van
    eerdere demo-installaties kan het ook bevatten) wordt bij het laden
    omgezet via nieuw `instellingen.models.normaliseer_zaagstrategie`
    (in `instellingen/opslag.py` en `projecten/zaagplannen_opslag.py`).
    Designdocs gecontroleerd op botsende terminologie: "horizontaal/
    verticaal" komt in hoofdstuk 5 alleen voor als beschrijving van
    gemengd liggende/staande onderdelen, niet als strategienaam.
  - "Verticaal" = `_pak_kolommen` in `engine.py`: spiegelt het werkgebied
    en elke eenheid (x↔y, én nerf-eis lange↔korte zijde, want de
    plaatnerf blijft langs de echte x-as), laat `_pak_rijen` het werk
    doen en spiegelt vrije ruimte en sneden terug. Plaatsingen worden via
    `_GespiegeldeEenheid.expand` door de echte eenheid gemaakt, zodat een
    groep (doorlopende nerf) exact ligt zoals bij elke andere strategie.
    Bewust geen tweede kopie van de rij-logica: verbeteringen aan
    Horizontaal gelden zo vanzelf ook voor Verticaal. Fabrieksband-
    stroken gaan zoals altijd vóór de strategie (dus op een plaat met
    fabrieksband onder/boven blijven die stroken horizontaal). Niet
    toegevoegd aan de kandidaten van "efficient" (niet gevraagd).
  - 7 nieuwe tests (181 totaal): kolommen/eerste snede verticaal over de
    volle hoogte, nerf, groep, fabrieksband + randafzaag, en het omzetten
    van "rijen" in instellingen en opgeslagen zaagplannen. Fuzz: 1500
    scenario's × efficient/horizontaal/verticaal/guillotine (10% met
    zoekbudget) = 6000 runs, 0 fouten.
  - **Bugfix direct daarna** (Sven: "een rode zaaglijn door een
    onderdeel" op de MDF-plaat van Keuken Jansen, strategie Verticaal):
    de snede tussen twee groepsleden (Front 1/Front 2) liep verticaal
    dwars door een Deur. Oorzaak: `_GespiegeldeEenheid.expand` gaf de
    ECHTE plaatsingen terug, waarna `_plaats_rij` de groepssneden met
    echte coördinaten in het gespiegelde assenstelsel uitrekende. Fix:
    `expand` geeft nu gespiegelde plaatsingen terug (`_pak_kolommen`
    spiegelt ze aan het eind terug), en `_plaats_rij` herkent een groep
    die in zijn assenstelsel naast elkaar ligt i.p.v. boven elkaar en
    zet er dan verticale sneden tussen. De fuzz had geen groepen, vandaar
    gemist — nu wel (50% van de scenario's). 4 nieuwe tests (185 totaal);
    alle drie projecten × vier strategieën op een db-kopie: geen enkele
    snede door een onderdeel.
    **Bestaande beperking, niet aangepast**: Efficiënt en Guillotine
    noteren tussen groepsleden helemaal geen snede (de leden worden wel
    goed geplaatst, maar de zaagvolgorde mist die naad).

- **Zaagvolgorde compleet + alle restruimte telt mee.** Op Svens vraag
  "hoe bereken je wat hergebruikt kan worden" liet narekenen op Keuken
  Jansen (db-kopie) twee gaten zien, die Sven liet oplossen ("ja doe
  dit"):
  1. **Restruimte die nergens meetelde** (Horizontaal/Verticaal, en dus
     ook Efficiënt als die die indeling koos): ruimte boven een stuk dat
     lager is dan zijn rij/band telde niet als reststuk én niet als afval
     (MDF-plaat ~1800×250; bewuste vereenvoudiging uit een eerdere
     versie, "dat zou allemaal losse, smalle reepjes worden" — met de
     `min_reststukgrootte`-regel worden smalle reepjes nu gewoon afval).
  2. **Randen van onderdelen zonder snede** in de genummerde
     zaagvolgorde (Efficiënt 10, Horizontaal 15, Verticaal 21, Guillotine
     2 op Keuken Jansen): de rechterrand van het laatste stuk in een rij,
     de bovenkant van lagere stukken, reepjes smaller dan de kerf, en de
     naden tussen groepsleden bij Efficiënt/Guillotine/fabrieksband-
     stroken.
  Fixes in `engine.py`:
  - `_plaats_rij` krijgt `rij_hoogte` en maakt sneden + vrije rechthoeken
    boven een stuk lager dan zijn band, rechts van een band smaller dan
    zijn kolom, en boven een kolom lager dan zijn rij. Volgorde binnen
    een kolom: bandnaden → naden tussen stukken → per stuk.
  - `_bouw_zaagvolgorde_uit_rijen`: ook de rechterrand van de laatste
    kolom (als er rechts iets overblijft), en eerst de kolomsneden, dán
    pas de sneden binnen een kolom (andersom kan een paneelzaag niet — de
    bestaande rand-tot-rand-test ving precies dat).
  - Nieuw `_zet_sneden_op_deelgebieden`: loopt de zaagvolgorde na zoals
    een paneelzaag en zet elke snede exact op de randen van zijn
    deelgebied (de pak-functies noteren sneden niet overal op dezelfde
    manier: vóór/na de kerf, begrensd tot stuk of kolom). Toegepast op
    rijen/stroken/kolommen, Efficiënt en Guillotine.
  - `_splits_vrije_rechthoek`: bij een reepje smaller dan de kerf toch
    een snede, maar pas NA de gewone opsplitsing en alleen binnen het
    blok van het stuk (een eerste versie liet 'm over het hele vrije
    rechthoek lopen en sneed zo door een later, hoger stuk — gevonden
    door de fuzz).
  - Nieuw `_groepssneden` (gedeeld door alle strategieën en de
    fabrieksband-strook); `_strook_restruimte` zaagt ook reepjes smaller
    dan de kerf (stuk net minder diep dan de strook, of net vóór het
    einde van de rand).
  Nieuwe test-hulpfuncties in `test_engine.py`: `_randen_zonder_snede`
  (elke rand van elk onderdeel ligt op de plaatrand of wordt over zijn
  volle lengte door een snede gemaakt) en `_onverantwoord_oppervlak`
  (plaat − onderdelen − reststukken − afval − kerf×snedelengte −
  randafzaag ≤ 0). 16 nieuwe/uitgebreide tests (202 totaal). Fuzz met
  beide controles erbij (+ groepen, 4 strategieën, 10% met zoekbudget):
  6000 runs, 0 fouten. Keuken Jansen (alle 4 strategieën): 0 randen
  zonder snede, 0 onverantwoorde ruimte, geen snede door een onderdeel.

- **Guillotine nagelopen met een eigen simulatie.** Sven: "kan je deze
  strategie simuleren en zelf controleren of alles klopt".
  1. Een losse referentie-implementatie, geschreven vanuit de beschrijving
     (grootste eerst, wachtrij van vakken strikt op volgorde, eerste
     passende onderdeel linksonder, splitsen langs de kant waar het minst
     overblijft) i.p.v. vanuit de code: 2000/2000 willekeurige scenario's
     (zonder zoekbudget) exact dezelfde indeling als de motor.
  2. Paneelzaag-simulatie (zaagvolgorde snede voor snede uitvoeren vanaf
     de plaat na randafzaag; elke snede moet rand-tot-rand door één stuk
     plaat, aan het eind hoogstens één onderdeel per stuk) + regels
     (overlap, nerf, fabrieksrand of terechte terugval, reststuk-drempel,
     aantallen, randen gezaagd, oppervlakte verantwoord).
  Twee echte bevindingen, beide opgelost in `engine.py`:
  - De sneden binnen een fabrieksband-strook liepen tot de rand van het
    stuk, niet tot de scheidingssnede (één kerf verschil) en gingen niet
    door `_zet_sneden_op_deelgebieden` — nu wel: `genereer_zaagplan` zet
    de hele gecombineerde volgorde (fabrieksband + strategie) aan het eind
    op de deelgebied-randen van het werkgebied.
  - Scheidingssneden van fabrieksband-stroken worden nu op de rand van de
    strook zelf genoteerd (vóór de kerf; LINKS: `nieuw_x0 - kerf` enz.),
    zoals de kolomranden bij rijen. Voorheen stonden ze na de kerf, en
    vielen de sneden van twee precies aansluitende stroken (onder én boven
    op een smalle plaat) op dezelfde coördinaat — de tweede werd als
    dubbel weggelaten en een stuk bleef een kerf te groot.
    `test_fabriekskantenband_strook_krijgt_eigen_scheidingssnede` verwacht
    daarom nu positie 500 i.p.v. 500 + kerf.
  Daarna: 1500 scenario's × alle 5 strategieën door paneelzaag + regels:
  0 fouten; Keuken Jansen met Guillotine (echte instellingen): alle 11
  platen OK. Nieuwe test `test_paneelzaag_simulatie_op_willekeurige_scenarios`
  (120 vaste scenario's × 5 strategieën, helper `_paneelzaag_fouten`) —
  207 tests totaal.
  **Randafzaag staat niet als genummerde snede in de zaagvolgorde** (de
  zaagvolgorde begint na het afzagen van de randen) — zo was het al; niet
  aangepast.

- **Teruggedraaid: "eindkolom" in Rijen.** Sven meldde dat op plaat 7
  nog "precies een 5e losse legger naast past"; narekenen gaf 536 mm vrij
  tegen 563 mm nodig. Er werd toch een wijziging gebouwd die zo'n legger
  gedraaid in een kolom rechts van de rijen zette — dat klopte niet met
  de kantenband en Sven liet het terugdraaien: zijn meting was fout, niet
  de motor. Les (Sven): als een melding op een verkeerde maat of
  instelling berust, dat zeggen i.p.v. de code aan te passen.

- **Opslagmeldingen + model bewerken vanuit een project.** Sven: een
  melding na opslaan ("nu druk je op de knop en moet je erop vertrouwen
  dat ie het opgeslagen heeft") en "rechtstreeks vanuit projecten een
  model kunnen bewerken en dit dan binnen een project houden of opslaan in
  modellen bibliotheek en ook optie om op te slaan als nieuwe model".
  Keuzes van Sven (via vragen vooraf): onderdeel-opslaan in het
  modelscherm slaat meteen echt op; meldingen bij álle opslaan-knoppen;
  bewerken als eigen tabblad; terugschrijven naar de bibliotheek niet bij
  een model met submodellen. HTML-mockup goedgekeurd
  (https://claude.ai/artifact/9YCmeygKv5GDneSDVmBH6Q).
  - Nieuw widget `ui/widgets/opslag_melding.py` (`OpslagMelding`): groene
    melding rechtsonder in de pagina, verdwijnt na 3 s (klik sluit), geen
    pop-up. Ingebouwd bij: model opslaan + onderdeel opslaan
    (modeldetail), materiaal, reststuk, project (drawer), projectgegevens
    en los onderdeel (projectdetail), instellingen algemeen/labels (die
    hadden een inline succes-balk; fouten blijven in de balk). Niet in het
    ongebruikte terugval-uitklappaneel van `modellen_page.py`.
  - Modeldetail: "Onderdeel toevoegen"/"Wijzigingen opslaan" slaat bij een
    bestaand model meteen de onderdelen op (naam/omschrijving/map/tags pas
    bij "Model opslaan"); een nieuw, nooit opgeslagen model blijft tot
    "Model opslaan". Een onderdeel **verwijderen** in het modelscherm gaat
    nog steeds alleen uit de lijst op het scherm tot "Model opslaan" (niet
    gevraagd; mogelijk later gelijktrekken). Nieuwe publieke `herlaad()`.
  - Backend (`projecten/bibliotheek.py`): `model_instantie_onderdelen_opslaan`
    (met dezelfde controle als losse onderdelen, gedeeld via
    `_valideer_onderdelen`), `model_instantie_afwijkingen` (op onderdeel-id,
    terugval op volgorde bij lege/dubbele id's),
    `model_instantie_naar_bibliotheek` (nieuw `ModelHeeftSubmodellenError`),
    `model_instantie_als_nieuw_model` (verse onderdeel-id's, kopie wordt
    aan het nieuwe model gekoppeld). 10 nieuwe tests.
  - UI: nieuw `ui/project_model_page.py` (`ProjectModelPage`), tabsleutel
    `projectmodel:{project_id}:{instantie_id}` in `main_window.py`
    (`_projectmodel_pages`), geopend via een potlood bij elk model in de
    Samenstelling. Onderdelen opslaan/toevoegen/verwijderen gaat meteen de
    projectkopie in; "gewijzigd"-label t.o.v. het bibliotheekmodel; onderaan
    de drie keuzes met inline bevestiging/naamveld. `ProjectDetailPage`
    kreeg `on_open_modelkopie` + publieke `ververs()`; open modelkopie-
    tabbladen volgen wijzigingen vanuit het project
    (`herlaad_als_gewijzigd`), en een open modeltabblad wordt herladen als
    een kopie naar de bibliotheek teruggeschreven is.
  - `theme.py`: uitgeschakelde primary/ghost-knoppen zien er nu ook
    uitgeschakeld uit.
  - Designdoc module 4 bijgewerkt (nieuwe paragraaf onder Samenstelling).
  Geverifieerd met een offscreen rookproef van de echte `MainWindow` op
  een db-kopie (APPDATA naar een tijdelijke map met een instellingen.json
  die de opslaglocatie naar de kopie zet; echte db-hash vóór/na gelijk):
  potlood → tabblad, onderdeel wijzigen → kopie gewijzigd + bibliotheek
  niet + melding + status, overschrijven, als nieuw model, uitgeschakelde
  keuze bij submodellen, modeldetail-onderdeel direct opgeslagen,
  thema-wissel, model uit project verwijderd terwijl tabblad open staat.
  217 tests.

- **Eigen titelbalk i.p.v. de standaard Windows-titelbalk.** Sven: "het
  frame van de venster zelfde style maken als de app in plaats van
  standaard windows". Keuze van Sven (vooraf gevraagd): de knoppen in de
  bestaande donkere header, zoals VS Code, i.p.v. een aparte dunne balk.
  - Nieuw `ui/vensterframe.py`: Qt krijgt `FramelessWindowHint`, het
    native venster krijgt de gewone stijlbits terug (`WS_CAPTION`/
    `WS_THICKFRAME`/min/max), en via `MainWindow.nativeEvent` handelt het
    `WM_NCCALCSIZE` (geen Windows-rand; gemaximaliseerd de randdikte eraf,
    anders valt het venster buiten het scherm) en `WM_NCHITTEST` af
    (onzichtbare resize-randen van 6 px, en de header telt als titelbalk
    behalve op knoppen). Zo blijven schaduw, afgeronde hoeken (Win 11),
    Aero Snap, dubbelklik = maximaliseren, rechtsklik = systeemmenu,
    animaties en minimaliseren via de taakbalk gewoon van Windows zelf.
    Buiten het Windows-platform van Qt (offscreen-rooktests) doet het
    niets.
  - Nieuw `ui/widgets/vensterknoppen.py`: drie zelf getekende knoppen
    (dunne lijnen zoals Windows 11, sluiten rood bij hover), max-icoon
    wisselt naar "vorige grootte" bij gemaximaliseerd (`changeEvent`).
    Hover wordt na een vensterwissel opnieuw bepaald (anders bleef de
    knop die onder de muis vandaan schoof "gehoverd").
  - Gecontroleerd met een echte (niet-offscreen) venstertest op een
    db-kopie: hit-tests, maximaliseren (client = beschikbaar scherm),
    herstellen, screenshots.
  - **Daarna, op Svens verzoek ("je mag van mij die functionaliteit nu wel
    toevoegen"):** de Windows 11-schermindelingen-popup (snap layouts) bij
    hover over de maximaliseerknop, en een automatisch verbergende
    taakbalk. De maximaliseerknop meldt zich als `HTMAXBUTTON`; hover/
    ingedrukt/klik komen dan binnen als niet-client-berichten en worden in
    `vensterframe.py` naar de knop vertaald (`VensterKnop.zet_native_toestand`).
    Gemaximaliseerd blijft aan de kant van een automatisch verbergende
    taakbalk 2 px vrij. **Lessen (gemeten, met een kaal ctypes-Win32-venster
    als referentie, waarin de popup wél werkte):** de popup verschijnt níet
    met `DwmExtendFrameIntoClientArea` (eerder toegevoegd voor de schaduw
    op Windows 10, nu weggehaald — op Windows 11 blijven schaduw en
    afgeronde hoeken ook zonder) en niet bij de `WS_POPUP`-stijl die Qt een
    frameloos venster geeft (nu weggehaald). `WM_NCHITTEST` rekent nu met
    het punt uit `lParam` i.p.v. `QCursor.pos()`. Geverifieerd met echte
    (vanuit een ander proces gegenereerde) muisbewegingen + screenshot:
    popup verschijnt; klikken op de knop maximaliseert/herstelt; hover
    verdwijnt bij verlaten. De automatisch verbergende taakbalk is niet
    live getest (zou Svens eigen taakbalkinstelling wijzigen).

## Werkwijze die Sven prettig vindt

- Bij ambiguïteit of ruimte voor aannames: **eerst vragen, niet
  gokken** — vooral belangrijk bij technisch werk met echte
  consequenties.
- Gerichte wijzigingen in plaats van herschrijvingen.
- Nieuwe functies mogen gebouwd worden met de commerciële laag uit
  (zie hierboven), zodat hij zelf onbeperkt kan testen.
