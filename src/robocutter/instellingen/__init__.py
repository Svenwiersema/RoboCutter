"""Opties/instellingen: app-brede voorkeuren die geen eigen ontwerp-
hoofdstuk hebben (de regels staan verspreid: bedrijfslogo in module 1,
zaagstrategie-keuze in hoofdstuk 5, label-vlaggen in hoofdstuk 6).

Anders dan de bibliotheken (materialen/reststukken/modellen/projecten)
is dit geen SQLite-tabel — de instelling die bepaalt wáár het
databasebestand staat, kan niet in diezelfde database leven. In plaats
daarvan een klein JSON-bestand op een vaste, van de databaselocatie
onafhankelijke plek (``%APPDATA%\\RoboCutter\\instellingen.json``).
"""
