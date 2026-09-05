# Module 6 — Labels & identificatie

**Status:** ✅ Afgerond — dit hoofdstuk stond nog niet uitgewerkt bij
ChatGPT (alleen een losse vermelding dat er labels voor onderdelen en
reststukken moeten komen) en is hier vanaf nul samen ontworpen.

## Kernconcept

- Elk onderdeel en reststuk krijgt een **fysiek label** met een scanbare
  code, gekoppeld aan de digitale informatie in RoboCutter — dit is de
  concrete invulling van principe 9 ("Traceerbaarheid via labels").
- Labels worden **automatisch gegenereerd tegelijk met het zaagplan**.
  Ze blijven gekoppeld aan het model/project en volgen hetzelfde **"Niet
  gecontroleerd"-mechanisme** als andere gegenereerde documenten (zie
  Module 1/2): bij een wijziging in de onderliggende data wordt een
  label ongeldig totdat het opnieuw gegenereerd wordt.
- Labels kunnen op een later moment opnieuw geprint worden, en een
  **los label kan opnieuw geprint worden** (bv. bij beschadiging) zonder
  dat de rest van de set opnieuw geprint hoeft te worden.

## Inhoud van het label

**Vaste kernvelden — onderdeel-label:**

- Onderdeel-ID
- Materiaal
- Projectnummer
- Afmeting

**Vaste kernvelden — reststuk-label:**

- Zelfde als onderdeel-label, **behalve projectnummer** — een reststuk
  hoort niet meer bij een specifiek project zodra het is vrijgegeven aan
  de reststukkenbibliotheek.
- Geen magazijnlocatie op het label: locatiebeheer valt buiten de scope
  van RoboCutter.

**Optionele velden (aan/uit te zetten):**

- QR-code en/of barcode
- Kantenband-indicatie
- Nerfrichting-pijl

Deze aan/uit-keuzes zijn **één algemene instelling** in het programma
(niet iets wat je telkens opnieuw kiest bij het printen) — dit sluit aan
bij het principe "zo min mogelijk pop-ups". Een bedrijf dat bijvoorbeeld
geen barcodescanner gebruikt, zet de scancode één keer uit in de
instellingen en die keuze geldt daarna voor alle labels.

## Scancode

- Zowel **QR-code** als **barcode (1D)** worden ondersteund; de
  gebruiker/het bedrijf kiest via de instelling hierboven welke (of
  geen) er gebruikt wordt.
- Wat de code precies codeert (bv. een uniek onderdeel/reststuk-ID dat
  terugverwijst naar het record in RoboCutter) wordt verder uitgewerkt
  bij de technische architectuur (hoofdstuk 8).

## Printen

- Labels printen kan zowel via een **dedicated labelprinter** (kleine
  zelfklevende labels, direct op het onderdeel te plakken) als via een
  **gewone printer** (A4/A3, eventueel los te knippen) — beide worden
  ondersteund.
- Een individueel label moet **los herprint** kunnen worden, zonder de
  hele set opnieuw te hoeven printen.

## Openstaande vragen

- Preciezere technische invulling van de scancode-inhoud (welk
  ID-/URL-schema) — hoort bij hoofdstuk 8 (Technische architectuur).
- Exact label-formaat/-afmetingen per labelprinter-merk — later te
  bepalen bij technische uitwerking en testen met een echte printer.
