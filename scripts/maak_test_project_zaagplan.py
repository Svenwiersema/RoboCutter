"""Zet een testproject in de échte database (dezelfde
``InstellingenBeheer().effectieve_db_pad()`` als de draaiende app) om
het nieuwe Zaagplannen-scherm en de motor er verder mee te kunnen
testen — de motor zelf is nog niet helemaal goed (zie OVERDRACHT.md),
dus dit script bouwt bewust een paar lastige gevallen in: een
fabriekskantenband-eis, een onderdeel met een vereiste nerfrichting
(het Werkblad, "lange_zijde" — mag dus nooit roteren), een groep
(doorlopende nerf) die expliciet NIET op zijn (te kleine) plaat past,
en drie materialen tegelijk zodat het scherm meerdere platen/kaarten
tegelijk moet tonen.

Materialen, model én project worden bij elke run verwijderd (indien
aanwezig) en vers opnieuw opgebouwd volgens de huidige scriptdefinitie
hierboven — zo geeft opnieuw draaien na een wijziging in dit script
altijd de bijgewerkte testdata, in plaats van een wijziging stilzwijgend
te negeren omdat er al een gelijknamig materiaal/model/project bestond.
De materiaalnamen dragen daarom bewust een "(testmateriaal
zaagplan)"-suffix — zonder die suffix zou de naam-lookup per ongeluk een
gelijknamig ECHT materiaal van Sven kunnen raken (precies wat de eerste
versie van dit script deed, met "Eiken multiplex 18mm" i.p.v. een eigen
testmateriaal: de fabriekskantenband-eis hieronder kwam toen niet op de
gegenereerde plaat terecht omdat het echte materiaal die instelling niet
had). **Belangrijke les**: vóór deze full-resync-aanpak werden materialen
alleen hergebruikt-op-naam (nooit opnieuw aangemaakt) — Sven had deze
testmaterialen zelf een keer aangepast tijdens het los verkennen van de
Materialenbibliotheek-UI (o.a. de MDF-breedte en de
fabriekskantenband-rand), waardoor latere reruns van dit script stilletjes
die handmatige wijzigingen bleven hergebruiken i.p.v. de eigen
scriptdefinitie — met als zichtbaar gevolg dat de MDF-plaat niet meer
"bewust te klein" was en de bedoelde niet-geplaatst-testcase niet meer
reproduceerde. Nu geeft elke run gegarandeerd exact de hierboven
gedefinieerde afmetingen/instellingen.

Gebruik:
    python scripts/maak_test_project_zaagplan.py
"""

from __future__ import annotations

from robocutter.instellingen.beheer import InstellingenBeheer
from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.materialen.models import Materiaal, MateriaalStatus, MateriaalType
from robocutter.materialen.opslag import open_verbinding as materialen_open_verbinding
from robocutter.modellen.bibliotheek import ModellenBibliotheek
from robocutter.modellen.models import Model, ModelOnderdeel, Nerfrichting, Rand
from robocutter.modellen.opslag import open_verbinding as modellen_open_verbinding
from robocutter.projecten.bibliotheek import ProjectenBibliotheek
from robocutter.projecten.models import Project, ProjectStatus
from robocutter.projecten.opslag import open_verbinding as projecten_open_verbinding

_PROJECT_NAAM = "Keuken Jansen (testproject zaagplan)"


def _materiaal_vers_aanmaken(materialen: MaterialenBibliotheek, **velden) -> Materiaal:
    """Verwijdert een bestaand materiaal met deze naam (indien aanwezig)
    en maakt 'm opnieuw aan volgens ``velden``. Zie de moduledocstring
    hierboven voor waarom dit script materialen niet langer alleen
    hergebruikt-op-naam laat staan."""

    bestaand = next((m for m in materialen.lijst() if m.naam == velden["naam"]), None)
    if bestaand is not None:
        if bestaand.status == MateriaalStatus.ACTIEF:
            materialen.archiveren(bestaand.id)
        materialen.verwijderen_definitief(bestaand.id)
    return materialen.toevoegen(Materiaal(id="", type=MateriaalType.PLAAT, **velden))


def _model_vers_aanmaken(modellen: ModellenBibliotheek, naam: str, **velden) -> Model:
    """Verwijdert een bestaand model met deze naam (indien aanwezig) en
    maakt 'm opnieuw aan volgens ``velden`` — zo geeft een gewijzigde
    onderdelenlijst in dit script altijd de bijgewerkte testdata, i.p.v.
    dat een oud model van een vorige run stilzwijgend blijft hangen."""

    bestaand = next((m for m in modellen.lijst() if m.naam == naam), None)
    if bestaand is not None:
        modellen.verwijderen(bestaand.id)
    return modellen.toevoegen(Model(id="", naam=naam, **velden))


def _project_verwijderen_indien_aanwezig(projecten: ProjectenBibliotheek, naam: str) -> None:
    bestaand = next((p for p in projecten.lijst() if p.naam == naam), None)
    if bestaand is None:
        return
    if bestaand.status != ProjectStatus.AFGEROND:
        projecten.zet_status(bestaand.id, ProjectStatus.AFGEROND)
    if not bestaand.gearchiveerd:
        projecten.archiveren(bestaand.id)
    projecten.verwijderen_definitief(bestaand.id)


def main() -> None:
    db_pad = InstellingenBeheer().effectieve_db_pad()
    materialen = MaterialenBibliotheek(materialen_open_verbinding(db_pad))
    modellen = ModellenBibliotheek(materialen, modellen_open_verbinding(db_pad))
    projecten = ProjectenBibliotheek(modellen, materialen, projecten_open_verbinding(db_pad))

    _project_verwijderen_indien_aanwezig(projecten, _PROJECT_NAAM)

    hout = _materiaal_vers_aanmaken(
        materialen, naam="Eiken multiplex 18mm (testmateriaal zaagplan)", lengte=2800, breedte=2070, derde_afmeting=18,
        familie="Eiken multiplex", kerf=4, min_reststukgrootte=300,
        fabriekskantenband_randen=frozenset({Rand.LINKS}),
    )
    wit = _materiaal_vers_aanmaken(
        materialen, naam="Wit gemelamineerd 18mm (testmateriaal zaagplan)", lengte=2800, breedte=2070, derde_afmeting=18,
        familie="Gemelamineerd", kerf=4, min_reststukgrootte=300,
    )
    # Klein restant-formaat MDF, bewust te krap voor de ladefronten-groep
    # hieronder -> test het "niet geplaatst"-pad van het nieuwe scherm.
    mdf = _materiaal_vers_aanmaken(
        materialen, naam="MDF 16mm (testmateriaal zaagplan)", lengte=600, breedte=500, derde_afmeting=16,
        familie="MDF", kerf=4, min_reststukgrootte=150,
    )

    onderkast = _model_vers_aanmaken(
        modellen, "Onderkast 60cm (testmodel zaagplan)", map="Keukens/Onderkasten",
        onderdelen=[
            ModelOnderdeel(id="", naam="Zijkant links", materiaal_id=hout.id, breedte=600, hoogte=720, aantal=2, fabriekskantenband_vereist=True),
            # Werkblad-nerf loopt over de lange kant -> test dat de motor
            # dit onderdeel nooit roteert (i.p.v. het, zoals een vrij
            # onderdeel, ook liggend te proberen als dat beter zou passen).
            ModelOnderdeel(id="", naam="Werkblad", materiaal_id=hout.id, breedte=1200, hoogte=620, aantal=1, nerfrichting_vereist=Nerfrichting.LANGE_ZIJDE),
            ModelOnderdeel(id="", naam="Bodemplaat", materiaal_id=hout.id, breedte=564, hoogte=560, aantal=2),
            ModelOnderdeel(id="", naam="Zijkant rechts", materiaal_id=hout.id, breedte=600, hoogte=720, aantal=2),
        ],
    )

    project = projecten.toevoegen(
        Project(
            id="", naam=_PROJECT_NAAM, klant="Test (script)",
            contactpersoon="", opdrachtnummer="TEST-ZAAGPLAN-1",
            losse_onderdelen=[
                ModelOnderdeel(id="", naam="Achterwand", materiaal_id=wit.id, breedte=1180, hoogte=720, aantal=1),
                ModelOnderdeel(id="", naam="Deur", materiaal_id=wit.id, breedte=300, hoogte=700, aantal=4, kantenband_randen=frozenset({Rand.LINKS})),
                # Groep: moet als één blok (588mm hoog incl. kerf) op een
                # plaat van maar 500mm hoog -> hoort niet geplaatst te
                # worden. Zelfde voorbeeld als scripts/demo_render.py.
                ModelOnderdeel(id="", naam="Ladefront onder", materiaal_id=mdf.id, breedte=596, hoogte=220, groep_id="lades-onderkast", groep_volgorde=1),
                ModelOnderdeel(id="", naam="Ladefront midden", materiaal_id=mdf.id, breedte=596, hoogte=180, groep_id="lades-onderkast", groep_volgorde=2),
                ModelOnderdeel(id="", naam="Ladefront boven", materiaal_id=mdf.id, breedte=596, hoogte=180, groep_id="lades-onderkast", groep_volgorde=3),
                ModelOnderdeel(id="", naam="Lade-bodem", materiaal_id=mdf.id, breedte=550, hoogte=400, aantal=2),
            ],
        )
    )
    projecten.model_toevoegen(project.id, onderkast.id, aantal=1)

    print(f"Testproject aangemaakt: '{_PROJECT_NAAM}' (id={project.id})")
    print(f"  Materialen: {hout.naam}, {wit.naam}, {mdf.naam}")
    print(f"  Model: {onderkast.naam}")
    print("Open de app en klik het project open -> tabblad Zaagplannen om te genereren.")


if __name__ == "__main__":
    main()
