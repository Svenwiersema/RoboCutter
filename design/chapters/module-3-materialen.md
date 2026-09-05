# Module 3 — Materialen

**Status:** ✅ Afgerond — oorspronkelijk uitgewerkt in een eerder gesprek,
hier opnieuw doorgenomen en bevestigd.

## Structuur

- Vaste materiaalstructuur met een **automatische hiërarchie**.
- Materialen kunnen in **losse materiaalfamilies** georganiseerd worden —
  varianten van hetzelfde basismateriaal (bv. dezelfde plaat in
  verschillende diktes/kleuren) horen bij elkaar.

## Invoer en validatie

- **Live validatie** zonder pop-ups — foutieve of onvolledige invoer
  wordt direct in het paneel getoond, geen blokkerende dialogen (sluit
  aan bij het "min pop-ups"-principe).
- **Autocomplete en fuzzy matching** bij het invoeren van materiaalnamen/
  -gegevens, met een bewuste bevestiging voordat een suggestie wordt
  overgenomen.

## Archiveren en verwijderen

Filosofie: **archiveren is de standaard, verwijderen is een bewuste,
definitieve actie.**

- Workflow: Actief → Archiveren → Gearchiveerd → Definitief verwijderen.
- Definitief verwijderen kan **alleen vanuit het archief** — dit voorkomt
  dat een veelgebruikt materiaal per ongeluk verdwijnt.
- Bij het kiezen van materialen in nieuwe projecten worden alleen actieve
  materialen getoond.
- Bij het openen/dupliceren van een bestaand project dat een
  **gearchiveerd** materiaal gebruikt: een melding met de keuze "zelfde
  materiaal blijven gebruiken" of "vervang door een actief materiaal".
- Bij een **definitief verwijderd** materiaal: een vervanging is
  verplicht, omdat de oorspronkelijke gegevens niet meer bestaan.

## Import

- CSV/Excel-import van materialen, met latere uitbreiding naar
  leveranciers-/ERP-import.

## Bibliotheekstructuur (bevestigd)

- **Twee aparte bibliotheken**: de materialenbibliotheek en de
  reststukkenbibliotheek staan los van elkaar.
- **Binnen elke bibliotheek** worden platen en balken **samengevoegd**
  in één doorzoekbare lijst, met filters om alleen platen of alleen
  balken te tonen (sluit aan bij principe 5: platen en balken zijn
  gelijkwaardig).

## Velden van een materiaal-record (bevestigd)

- Naam/omschrijving
- Type: plaat of balk
- Afmetingen (bij platen: lengte × breedte + dikte; bij balken: lengte +
  breedte × hoogte)
- Materiaalfamilie-koppeling
- Kleur/afwerking
- Nerfrichting: lange zijde / korte zijde / geen (zie hoofdstuk 5)
- Zaagsnede/kerf-breedte (zie hoofdstuk 5)
- Randafzaag-marge + welke randen (zie hoofdstuk 5)
- Minimale reststukgrootte (zie hoofdstuk 5)
- Mes/groef-eigenschappen (zie hoofdstuk 5 — technisch verder te
  detailleren)
- **Fabriekskantenband**: op welke rand(en) van de plaat/het materiaal
  een fabrieks-kantenband aanwezig is — wordt gebruikt door de optimizer
  (zie de fabrieksrand-regel in hoofdstuk 5).
- Productcode/artikelnummer
- Leverancier — ook nuttig voor bedrijven zonder ERP-koppeling, zodat
  toch valt terug te zien waar een materiaal besteld is.
- Vrije tags
- Status: actief / gearchiveerd / definitief verwijderd

**Nadrukkelijk géén velden:** voorraadaantal en prijs/kostprijs — beide
buiten scope, dit is een ERP-taak (zie hoofdstuk 9).

## Velden van een reststuk-record (bevestigd)

Een reststuk staat in de aparte reststukkenbibliotheek en neemt de
eigenschappen van zijn onderliggende materiaal over (kerf, nerfrichting,
randafzaag-marge, etc.), aangevuld met:

- **Huidige (resterende) afmetingen** — anders dan de standaardafmeting
  van het materiaal, omdat het al eerder gezaagd is.
- **Herkomst**: uit welk project/model dit reststuk is vrijgekomen.
- **Status**: beschikbaar / gebruikt.

## Openstaande vragen

- Geen op dit moment — dit hoofdstuk is inhoudelijk afgerond, inclusief
  de materiaal-/reststukvelden en de bibliotheekstructuur.
