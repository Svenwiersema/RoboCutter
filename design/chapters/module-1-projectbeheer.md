# Module 1 — Projectbeheer

**Status:** ✅ Afgerond — oorspronkelijk uitgewerkt in een eerder gesprek,
hier opnieuw doorgenomen en bevestigd.

## Kernconcept

- Een project bestaat uitsluitend uit revisies; het origineel zelf heeft
  geen revisie.
- Revisies heten Rev A, Rev B, Rev C, ...
- Revisies worden altijd **handmatig** aangemaakt via de toolbar —
  automatisch opslaan maakt nooit zelf een revisie.
- Elke revisie krijgt een automatische wijzigingssamenvatting plus
  optionele notities.
- "Sandboxes" (werkkopieën) slaan alleen de wijzigingen (delta's) op ten
  opzichte van de vorige stand.

## Projectgegevens

- Projectgegevens kunnen handmatig of via ERP/databron geïmporteerd
  worden, en blijven daarna altijd handmatig aanpasbaar.
- Eén project heeft precies één klant en één contactpersoon.
- Alleen startdatum en gewenste opleverdatum worden bijgehouden — géén
  verdere planning/scheduling (zie ook de principes in `principles.md`).
- Bedrijfslogo op documenten komt uit de algemene instellingen, met
  uitzondering van de Demo/Hobby-editie (zie
  `licentiemodel-en-edities.md`).
- Stamgegevens (klanten, contactpersonen, etc.) worden centraal in
  bibliotheken beheerd, niet los per project.

## Reststukken en revisies

- Reststukken van een project worden pas **ná afronding** van het project
  vrijgegeven naar de gedeelde reststukkenbibliotheek.

## Wat is "revisie-waardig"? (geldt ook voor modelrevisies, zie Module 2)

- Een wijziging **op verzoek van de klant** (bv. een aanpassing aan een
  kast of het project) is revisie-waardig.
- Het **corrigeren van een fout** die tijdens de werkvoorbereiding is
  gemaakt, is **niet** revisie-waardig — dat is geen nieuwe Rev, gewoon
  een correctie binnen de huidige stand.

## Archiveren van afgeronde projecten

Zelfde principe als bij Module 3 (Materialen): **archiveren is de
standaard, verwijderen is een bewuste actie.**

- Workflow: Afgerond → Archiveren (verplaatst naar het
  **projectenarchief**) → Gearchiveerd → Definitief verwijderen — dat
  laatste kan alleen vanuit het archief.
- Een afgerond project wordt dus nooit zomaar verwijderd.

## Gegenereerde documenten (zaagplannen, labels)

- Er is geen apart programma voor documentgeneratie (het eerder overwogen
  "RoboDocument" is geschrapt) — RoboCutter genereert zelf PDF's en
  labels.
- Een gegenereerd zaagplan-PDF of label wordt aan het model/project
  vastgehangen en onthouden — het wordt niet elke keer opnieuw
  gegenereerd.
- Zodra er een relevante wijziging plaatsvindt in het onderliggende
  model, krijgt het gekoppelde document (werktekening, zaagplan, label)
  de status **"Niet gecontroleerd"**; het wordt pas opnieuw gegenereerd
  zodra het weer wordt opgevraagd/geëxporteerd. Dit is hetzelfde
  mechanisme als bij werktekeningen in Module 2.

## Openstaande vragen

- Geen op dit moment — dit hoofdstuk is inhoudelijk afgerond. Eventuele
  aanvullingen komen terug zodra we bij het datamodel (Module 4 —
  Projecten) preciezer worden over hoe dit technisch samenhangt met
  modellen/kasten.
