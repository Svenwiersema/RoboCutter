# RoboCutter — broncode

Dit is de eerste, echte code van RoboCutter. Voor het ontwerpproces
en alle besluiten die hieraan ten grondslag liggen, zie
[`design/README.md`](design/README.md).

## Wat staat hier (nu)

Als eerste stap is bewust gekozen om **alleen de zaagplan-
optimalisatie-motor** (hoofdstuk 5) te bouwen, als losse, testbare
Python-module — nog zonder UI. Dit is de kern van het product, dus
die moet eerst kloppen voordat er UI overheen komt.

```
src/robocutter/optimalisatie/
    models.py   — datamodellen (Materiaal, Onderdeel, Plaatsing, ...)
    engine.py   — het eigenlijke algoritme (twee strategieën)
tests/
    test_engine.py — pytest-tests voor de kernregels uit hoofdstuk 5
scripts/
    demo_render.py — genereert PNG-voorbeelden ter visuele controle
```

Belangrijke aannames die in de code staan (zie ook de docstring
bovenaan `engine.py`) en die Sven graag mag controleren:

1. De nerf van een plaat loopt aangenomen altijd langs de lengte-as.
2. Kerf wordt verrekend als extra ruimte tussen onderdelen (niet aan
   de plaatrand).
3. Een groep (vaste volgorde/nerf) wordt behandeld als één blok dat
   niet roteert en verticaal stapelt — de optimizer kiest zelf waar
   dat blok op de plaat komt.
4. Een reststuk telt als "bruikbaar" als **zowel** breedte **als**
   hoogte minstens de ingestelde minimale reststukgrootte zijn.
5. Bij een fabriekskantenband-eis wordt de eerste geschikte
   plaatrand gebruikt (volgorde: links, onder, boven, rechts).
6. De zaagvolgorde-nummering is een eerste, redelijke benadering —
   dit wordt verder verfijnd zodra er meer voorbeelden beoordeeld
   zijn (zoals hoofdstuk 5 ook aangeeft).

## Draaien

```bash
# Tests
pytest

# Visuele voorbeelden genereren (output/*.png)
python3 scripts/demo_render.py
```

Nog niet gedaan (bewust, dit is iteratie 1):
- Mes/groef-plaatsingsregels (hoofdstuk 5 noemt dit zelf nog als
  "verder te detailleren").
- Meerdere platen tegelijk optimaliseren (nu: één plaat per aanroep).
- UI (PySide6) — volgt in een volgende stap.
