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
- **Drie bugs gemeld en gefixt na de tabbalk (Sven testte de app zelf):**
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
  Alle drie geverifieerd met échte pixel-sampling/knop-klik-simulatie
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
- Meerdere platen tegelijk optimaliseren (nu: één plaat per aanroep;
  er is nog geen logica die onderdelen over meerdere platen van
  hetzelfde materiaal verdeelt).
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
- De rest van de UI (PySide6, hoofdstuk 11): de home pagina
  (Projecten-overzicht), de Materialenbibliotheek, de
  Reststukkenbibliotheek en de Modellenbibliotheek staan er; het echte
  Projecten-scherm (op de nu gebouwde functie-laag), een echt
  Opties-scherm (de functie is er, zie hierboven) en het losse
  projecttabblad nog niet.

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
(Materialen-, Reststukken-, Modellen- en Projectenbeheer), plus nu ook
Opties/instellingen (met de instelbare opslaglocatie al echt gekoppeld
aan alle drie bestaande schermen, en thema-voorkeur die nu onthouden
wordt). De eerste drie bibliotheken hebben ook al een echt
PySide6-scherm. Logische vervolgstappen, in overleg met Sven te
bepalen: het echte Projecten-scherm (HTML-mockup + PySide6, op de nu
gebouwde functie-laag — inclusief een zaaglijst-view met de
multi-criteria-sortering), revisiegeschiedenis/sandboxes en échte
zaagplan-generatie vanuit een project (module 1/4, bewust uitgesteld
bij het bouwen van de functie), het losse projecttabblad (zie
`assets/mockups/projectoverzicht-concept.png`), een echt
Opties-scherm, of de optimalisatie-motor verder afmaken (mes/groef,
meerdere platen). Nog niet gekozen als volgende stap.

## Werkwijze die Sven prettig vindt

- Bij ambiguïteit of ruimte voor aannames: **eerst vragen, niet
  gokken** — vooral belangrijk bij technisch werk met echte
  consequenties.
- Gerichte wijzigingen in plaats van herschrijvingen.
- Nieuwe functies mogen gebouwd worden met de commerciële laag uit
  (zie hierboven), zodat hij zelf onbeperkt kan testen.
