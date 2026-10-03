"""Zet een set test-reststukken in de échte Reststukkenbibliotheek
(dezelfde ``InstellingenBeheer().effectieve_db_pad()`` als de draaiende
app), om te testen hoe de zaagmotor reststukken eerst gebruikt voordat
hij volle platen pakt (zie ``projecten/zaagplannen.py``).

De maten zijn afgestemd op de onderdelen van Svens project "Keuken
Jansen" (Meubelpaneel wit 18, MDF water werend 18, Melamine grijs 18,
HDF wit 5): per materiaal een paar stukken waar onderdelen op passen,
plus een paar die voor alles te klein zijn (die moet de motor laten
liggen). De stukken Meubelpaneel wit hebben nog fabriekskantenband: de
plaat heeft die boven en onder, dus een stuk over de volle breedte (600)
heeft beide randen nog, een smaller stuk alleen de onderrand.

Elke run verwijdert eerst de test-reststukken van een vorige run
(herkenbaar aan herkomst "Testreststuk (script)") en maakt ze opnieuw
aan — ook als een zaagplan ze intussen had gereserveerd; genereer dat
zaagplan dan opnieuw. Materialen die niet (meer) bestaan worden
overgeslagen. Sluit RoboCutter voordat je dit draait.

Gebruik:
    python scripts/maak_test_reststukken.py
"""

from __future__ import annotations

from robocutter.instellingen.beheer import InstellingenBeheer
from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.materialen.opslag import open_verbinding as materialen_open_verbinding
from robocutter.optimalisatie.models import Rand
from robocutter.reststukken.bibliotheek import ReststukkenBibliotheek
from robocutter.reststukken.models import Reststuk
from robocutter.reststukken.opslag import open_verbinding as reststukken_open_verbinding

_HERKOMST = "Testreststuk (script)"

_BEIDE = frozenset({Rand.ONDER, Rand.BOVEN})
_ONDER = frozenset({Rand.ONDER})

# materiaalnaam -> [(lengte, breedte, wat erop zou moeten passen[, fabrieksranden])]
_RESTSTUKKEN: dict[str, list[tuple]] = {
    "Meubelpaneel wit 18": [
        (1200, 600, "groot: bv. zijkanten 560×838 of bodem 864×540", _BEIDE),
        (900, 600, "bv. bodem 564×540 of zijkant 360×880", _BEIDE),
        (700, 380, "bv. legger 563×318 of bodem 564×360", _ONDER),
        (400, 250, "te klein voor alle onderdelen", _ONDER),
    ],
    "MDF water werend 18": [
        (1300, 950, "bv. twee deuren 594×895 of de Front-groep 594×835"),
        (650, 450, "lijkt te passen voor Front 1/2, maar die zijn een groep (594×835): blijft liggen"),
        (300, 200, "te klein voor alle onderdelen"),
    ],
    "Melamine grijs 18": [
        (1100, 600, "twee ladebodems 506×500"),
        (520, 200, "lade rug korf 506×170"),
    ],
    "HDF wit 5": [
        (900, 850, "achterwand 881×829"),
        (250, 250, "te klein voor alle onderdelen"),
    ],
}


def main() -> None:
    db_pad = InstellingenBeheer().effectieve_db_pad()
    materialen = MaterialenBibliotheek(materialen_open_verbinding(db_pad))
    reststukken = ReststukkenBibliotheek(materialen, reststukken_open_verbinding(db_pad))

    oud = [r for r in reststukken.lijst() if r.herkomst_project == _HERKOMST]
    for r in oud:
        reststukken.verwijderen(r.id)
    print(f"{len(oud)} oude test-reststukken verwijderd.")

    op_naam = {m.naam: m for m in materialen.lijst()}
    for naam, stukken in _RESTSTUKKEN.items():
        materiaal = op_naam.get(naam)
        if materiaal is None:
            print(f"Materiaal '{naam}' niet gevonden — overgeslagen.")
            continue
        for lengte, breedte, toelichting, *randen in stukken:
            fabrieksranden = randen[0] if randen else frozenset()
            reststukken.toevoegen(
                Reststuk(
                    id="",
                    materiaal_id=materiaal.id,
                    lengte=lengte,
                    breedte=breedte,
                    herkomst_project=_HERKOMST,
                    herkomst_model=toelichting,
                    fabriekskantenband_randen=fabrieksranden,
                )
            )
            rand_tekst = f", fabrieksrand {'/'.join(sorted(r.value for r in fabrieksranden))}" if fabrieksranden else ""
            print(f"  {naam}: {lengte:g} × {breedte:g} mm  ({toelichting}{rand_tekst})")


if __name__ == "__main__":
    main()
