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

**Nog open, kandidaten voor een volgende stap:** de PDF-generator
hierboven écht bouwen (zie direct hierboven — mockup is af en
goedgekeurd, alleen de `QPainter`-implementatie moet nog); of de
bijgewerkte Zaagplan Generator-schérm-mockup (het scherm zelf, niet de
PDF) alsnog laten goedkeuren door Sven; of revisiegeschiedenis/sandboxes
voor projecten in het algemeen (module 1/4, bewust uitgesteld bij het
bouwen van de functie — zie `assets/mockups/projectoverzicht-concept.png`
voor een eerder concept van de projectenlijst zelf); of
mes/groef-plaatsingsregels in de motor.

## Werkwijze die Sven prettig vindt

- Bij ambiguïteit of ruimte voor aannames: **eerst vragen, niet
  gokken** — vooral belangrijk bij technisch werk met echte
  consequenties.
- Gerichte wijzigingen in plaats van herschrijvingen.
- Nieuwe functies mogen gebouwd worden met de commerciële laag uit
  (zie hierboven), zodat hij zelf onbeperkt kan testen.
