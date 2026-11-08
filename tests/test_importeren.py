"""RoboCutter-importformaat (hoofdstuk 10): lezen, materialen koppelen en
importeren in een project of model."""

from __future__ import annotations

import pytest

from robocutter.importeren.koppelen import MateriaalKoppelingen, normaliseer, stel_koppeling_voor, suggesties
from robocutter.importeren.lezen import KOLOMMEN, lees_bestand, lees_regel, lees_rijen, schrijf_sjabloon
from robocutter.importeren.models import Ernst
from robocutter.importeren.opslag import open_verbinding
from robocutter.importeren.toepassen import controleer, importeer_in_model, importeer_in_project
from robocutter.materialen.bibliotheek import MaterialenBibliotheek
from robocutter.materialen.models import Materiaal, MateriaalType
from robocutter.modellen.bibliotheek import ModellenBibliotheek
from robocutter.modellen.models import Model, Nerfrichting, Rand
from robocutter.projecten.bibliotheek import ProjectenBibliotheek
from robocutter.projecten.models import Project
from robocutter.projecten.zaaglijst import bouw_zaaglijst

KOP = ["Naam", "Materiaal", "Lengte", "Breedte", "Aantal", "Model", "Modelaantal", "Nerf", "Kantenband", "Fabriekskantenband", "Groep", "Volgorde"]


def _bibliotheken():
    materialen = MaterialenBibliotheek()
    eiken = materialen.toevoegen(Materiaal(
        id="", naam="Eiken multiplex 18 mm", type=MateriaalType.PLAAT, lengte=2800, breedte=2070,
        derde_afmeting=18, productcode="EMP18",
    ))
    regel = materialen.toevoegen(Materiaal(
        id="", naam="Vuren regel 44×68", type=MateriaalType.BALK, lengte=3000, breedte=68, derde_afmeting=44,
    ))
    modellen = ModellenBibliotheek(materialen)
    projecten = ProjectenBibliotheek(modellen, materialen)
    return materialen, modellen, projecten, eiken, regel


# ----------------------------------------------------------------------
# Lezen
# ----------------------------------------------------------------------


def test_volledige_regel_wordt_gelezen():
    resultaat = lees_rijen([
        KOP,
        ["Zijkant", "EMP18", "720", "560,5", "2", "Onderkast 60", "3", "lang", "B O", "ja", "Laden", "2"],
    ])
    assert resultaat.meldingen == []
    r = resultaat.regels[0]
    assert (r.regelnummer, r.naam, r.materiaal, r.lengte, r.breedte, r.aantal) == (2, "Zijkant", "EMP18", 720, 560.5, 2)
    assert (r.model, r.modelaantal, r.nerf) == ("Onderkast 60", 3, Nerfrichting.LANGE_ZIJDE)
    assert r.kantenband == frozenset({Rand.BOVEN, Rand.ONDER})
    assert r.fabriekskantenband and (r.groep, r.volgorde) == ("Laden", 2)


def test_kolomnamen_hoofdletters_spaties_volgorde_en_standaardwaarden():
    resultaat = lees_rijen([
        ["  MATERIAAL ", "lengte", "naam", "Fabrieks kantenband", "Opmerking"],
        ["EMP18", 1200, "Plank", "", "iets"],
        ["", "", "", "", ""],
    ])
    assert [m.tekst for m in resultaat.meldingen] == ["Kolom 'Opmerking' wordt niet gebruikt."]
    r = resultaat.regels[0]
    assert (r.naam, r.lengte, r.breedte, r.aantal, r.modelaantal, r.model) == ("Plank", 1200, None, 1, 1, "")
    assert r.nerf == Nerfrichting.GEEN and r.kantenband == frozenset() and not r.fabriekskantenband


def test_ontbrekende_verplichte_kolom_geeft_geen_regels():
    resultaat = lees_rijen([["Naam", "Breedte"], ["Plank", "300"]])
    assert resultaat.regels == []
    assert resultaat.heeft_fouten
    assert "Materiaal, Lengte" in resultaat.meldingen[0].tekst


@pytest.mark.parametrize(
    "rij, kolom, verwacht",
    [
        (["", "EMP18", "100"], "Naam", "Naam is leeg."),
        (["A", "", "100"], "Materiaal", "Materiaal is leeg."),
        (["A", "EMP18", ""], "Lengte", "Lengte is leeg."),
        (["A", "EMP18", "abc"], "Lengte", "Lengte 'abc' is geen getal."),
        (["A", "EMP18", "-5"], "Lengte", "Lengte moet groter dan 0 zijn."),
        (["A", "EMP18", "100", "", "0"], "Aantal", "Aantal '0' moet een geheel getal van minstens 1 zijn."),
        (["A", "EMP18", "100", "", "1,5"], "Aantal", "Aantal '1,5' moet een geheel getal van minstens 1 zijn."),
        (["A", "EMP18", "100", "", "", "", "", "schuin"], "Nerf", "Nerf 'schuin' is onbekend: gebruik lang, kort of laat hem leeg."),
        (["A", "EMP18", "100", "", "", "", "", "", "BX"], "Kantenband", "Kantenband 'BX' is onbekend: gebruik de letters B, O, L en R."),
        (["A", "EMP18", "100", "", "", "", "", "", "", "misschien"], "Fabriekskantenband", "Fabriekskantenband 'misschien' is onbekend: gebruik ja of laat hem leeg."),
    ],
)
def test_foute_regel_blijft_bewaard_om_aan_te_vullen(rij, kolom, verwacht):
    # Sven: niet weigeren maar laten zien wat er mist en het laten invullen.
    resultaat = lees_rijen([KOP, ["Goed", "EMP18", "100", "100"], rij])
    assert [r.regelnummer for r in resultaat.regels] == [2, 3]
    assert resultaat.regels[0].is_compleet
    fout = resultaat.regels[1]
    assert fout.problemen == {kolom: verwacht}
    assert resultaat.onvolledig == [fout]
    assert not resultaat.heeft_fouten  # het bestand zelf is in orde


def test_aangevulde_regel_opnieuw_lezen():
    regel = lees_rijen([KOP, ["Zijkant", "EMP18", "", "560", "", "", "", "schuin"]]).regels[0]
    assert set(regel.problemen) == {"Lengte", "Nerf"}
    aangevuld = lees_regel(regel.regelnummer, {**regel.waarden, "Lengte": "720", "Nerf": "lang"})
    assert aangevuld.is_compleet and aangevuld.regelnummer == 2
    assert (aangevuld.lengte, aangevuld.breedte, aangevuld.nerf) == (720, 560, Nerfrichting.LANGE_ZIJDE)


def test_getallen_met_duizendtal_punt_en_decimale_komma():
    resultaat = lees_rijen([["Naam", "Materiaal", "Lengte", "Breedte"], ["A", "X", "1.200,5", "300.5"]])
    assert (resultaat.regels[0].lengte, resultaat.regels[0].breedte) == (1200.5, 300.5)


def test_verschillend_modelaantal_geeft_waarschuwing_en_eerste_telt():
    resultaat = lees_rijen([
        ["Naam", "Materiaal", "Lengte", "Breedte", "Model", "Modelaantal"],
        ["Zijkant", "X", 720, 560, "Kast", 2],
        ["Bodem", "X", 560, 500, "kast", 3],
    ])
    assert [r.modelaantal for r in resultaat.regels] == [2, 2]
    assert resultaat.meldingen[0].ernst == Ernst.WAARSCHUWING and resultaat.meldingen[0].regelnummer == 3


def test_leeg_bestand_en_alleen_een_kop():
    assert lees_rijen([]).meldingen[0].tekst == "Het bestand is leeg."
    assert lees_rijen([KOP]).meldingen[0].tekst == "Het bestand bevat geen onderdelen."


def test_csv_met_puntkomma_komma_en_windows_tekenset(tmp_path):
    puntkomma = tmp_path / "a.csv"
    puntkomma.write_text("Naam;Materiaal;Lengte;Breedte\nZijkant;EMP18;720;560,5\n", encoding="utf-8-sig")
    komma = tmp_path / "b.csv"
    komma.write_text('Naam,Materiaal,Lengte,Breedte\nZijkant,EMP18,720,"560,5"\n', encoding="utf-8")
    windows = tmp_path / "c.csv"
    windows.write_bytes("Naam;Materiaal;Lengte;Breedte\nTafelblad ×;Eiken;720;560\n".encode("cp1252"))
    for pad in (puntkomma, komma):
        regel = lees_bestand(pad).regels[0]
        assert (regel.naam, regel.lengte, regel.breedte) == ("Zijkant", 720, 560.5)
    assert lees_bestand(windows).regels[0].naam == "Tafelblad ×"


def test_sjabloon_en_xlsx_lezen(tmp_path):
    from openpyxl import load_workbook

    pad = tmp_path / "sjabloon.xlsx"
    schrijf_sjabloon(pad)
    boek = load_workbook(pad)
    assert [c.value for c in boek["Onderdelen"][1]] == list(KOLOMMEN)
    assert boek.sheetnames == ["Onderdelen", "Uitleg"]
    assert lees_bestand(pad).meldingen[0].tekst == "Het bestand bevat geen onderdelen."
    boek["Onderdelen"].append(["Zijkant", "EMP18", 720, 560.5, 2, "Kast", 1, "kort", "L", None, None, None])
    boek.save(pad)
    regel = lees_bestand(pad).regels[0]
    assert (regel.naam, regel.lengte, regel.breedte, regel.aantal, regel.nerf) == ("Zijkant", 720, 560.5, 2, Nerfrichting.KORTE_ZIJDE)


def test_onbekend_bestandstype(tmp_path):
    assert lees_bestand(tmp_path / "x.dxf").heeft_fouten


# ----------------------------------------------------------------------
# Koppelen
# ----------------------------------------------------------------------


def test_koppelen_op_productcode_en_naam_zonder_hoofdletters_en_spaties():
    materialen, _, _, eiken, regel = _bibliotheken()
    regels = lees_rijen([
        ["Naam", "Materiaal", "Lengte", "Breedte"],
        ["A", "emp18", 100, 100],
        ["B", "  eiken   MULTIPLEX 18 mm", 100, 100],
        ["C", "Vuren regel 44x68", 100, ""],
        ["D", "Beuken", 100, 100],
    ]).regels
    koppeling = stel_koppeling_voor(regels, materialen)
    assert koppeling == {
        "emp18": eiken.id, "eiken multiplex 18 mm": eiken.id, "vuren regel 44x68": regel.id, "beuken": None,
    }


def test_onthouden_koppeling_overleeft_herstart_maar_exacte_naam_of_code_gaat_voor(tmp_path):
    materialen, _, _, eiken, regel = _bibliotheken()
    db = tmp_path / "koppelingen.db"
    onthouden = MateriaalKoppelingen(open_verbinding(db))
    onthouden.onthoud("Beuken  18", eiken.id)
    onthouden.onthoud("EMP18", regel.id)  # productcode van eiken bestaat: die gaat voor

    herstart = MateriaalKoppelingen(open_verbinding(db))
    regels = lees_rijen([["Naam", "Materiaal", "Lengte"], ["A", "beuken 18", 100], ["B", "EMP18", 100]]).regels
    assert stel_koppeling_voor(regels, materialen, herstart) == {"beuken 18": eiken.id, "emp18": eiken.id}

    # Svens test: eerst aan een ander materiaal gekoppeld, daarna een
    # materiaal met precies die naam aangemaakt -> dat nieuwe wint.
    beuken = materialen.toevoegen(Materiaal(
        id="", naam="Beuken 18", type=MateriaalType.PLAAT, lengte=2500, breedte=1250, derde_afmeting=18,
    ))
    assert stel_koppeling_voor(regels, materialen, herstart)["beuken 18"] == beuken.id

    # Is het onthouden materiaal weg, dan geen koppeling.
    materialen.archiveren(beuken.id)
    materialen.verwijderen_definitief(beuken.id)
    materialen.archiveren(eiken.id)
    materialen.verwijderen_definitief(eiken.id)
    assert stel_koppeling_voor(regels, materialen, herstart)["beuken 18"] is None
    herstart.vergeet("beuken 18")
    assert MateriaalKoppelingen(open_verbinding(db)).materiaal_voor("Beuken 18") is None


def test_suggesties_bedoelde_je():
    materialen, _, _, eiken, regel = _bibliotheken()
    assert suggesties("Eiken multiplex 18", materialen)[0] == eiken.id
    assert suggesties("vuren regel 44x70", materialen)[0] == regel.id
    assert suggesties("Aluminium", materialen) == []
    assert normaliseer(" A  ×  B ") == "a x b"


# ----------------------------------------------------------------------
# Controleren en importeren
# ----------------------------------------------------------------------


def test_controleer_balk_plaat_en_niet_gekoppeld():
    materialen, _, _, eiken, regel = _bibliotheken()
    regels = lees_rijen([
        KOP,
        ["Stijl", "Vuren regel 44x68", 1000, 70, 1, "", "", "lang", "", "", "", ""],
        ["Lange stijl", "Vuren regel 44x68", 3500, "", 1, "", "", "", "", "", "", ""],
        ["Plank", "EMP18", 600, "", 1, "", "", "", "", "", "", ""],
        ["Blad", "EMP18", 3000, 2100, 1, "", "", "", "", "", "", ""],
        ["Front", "Beuken", 600, 400, 1, "", "", "", "", "", "", ""],
    ]).regels
    meldingen = controleer(regels, stel_koppeling_voor(regels, materialen), materialen)
    per_regel = {(m.regelnummer, m.ernst, m.kolom) for m in meldingen}
    assert (2, Ernst.WAARSCHUWING, None) in per_regel  # breedte en nerf vervallen bij een balk
    assert (3, Ernst.WAARSCHUWING, "Lengte") in per_regel  # langer dan de balk
    assert (4, Ernst.FOUT, "Breedte") in per_regel  # plaat zonder breedte
    assert (5, Ernst.WAARSCHUWING, None) in per_regel  # past niet op de plaat
    assert any(m.kolom == "Materiaal" and "Beuken" in m.tekst and "regel 6" in m.tekst for m in meldingen)


def test_problemen_uit_het_lezen_tellen_mee_en_importeren_wacht_tot_alles_klopt():
    materialen, _, projecten, _, _ = _bibliotheken()
    project = projecten.toevoegen(Project(id="", naam="Keuken", klant="Jansen"))
    regels = lees_rijen([["Naam", "Materiaal", "Lengte", "Breedte"], ["A", "EMP18", "", 100], ["B", "EMP18", 300, 100]]).regels
    koppeling = stel_koppeling_voor(regels, materialen)
    assert [(m.regelnummer, m.kolom) for m in controleer(regels, koppeling, materialen)] == [(2, "Lengte")]
    with pytest.raises(ValueError, match="Lengte is leeg"):
        importeer_in_project(projecten, project.id, regels, koppeling, materialen)
    # Aanvullen of de regel overslaan, dan lukt het.
    regels[0] = lees_regel(2, {**regels[0].waarden, "Lengte": "400"})
    project = importeer_in_project(projecten, project.id, regels, koppeling, materialen)
    assert [o.breedte for o in project.losse_onderdelen] == [400, 300]


def test_importeren_in_project_maakt_modellen_en_losse_onderdelen():
    materialen, _, projecten, eiken, regel = _bibliotheken()
    project = projecten.toevoegen(Project(id="", naam="Keuken", klant="Jansen"))
    regels = lees_rijen([
        KOP,
        ["Zijkant", "EMP18", 720, 560, 2, "Onderkast 60", 3, "lang", "BO", "", "", ""],
        ["Bodem", "EMP18", 564, 540, 1, "onderkast 60", 3, "", "", "", "", ""],
        ["Front 1", "EMP18", 596, 180, 1, "Ladekast", 1, "", "", "ja", "Fronten", 1],
        ["Plintregel", "Vuren regel 44x68", 2400, "", 2, "", "", "", "", "", "", ""],
    ]).regels
    koppeling = stel_koppeling_voor(regels, materialen)

    project = importeer_in_project(projecten, project.id, regels, koppeling, materialen)

    assert [(i.model_naam, i.aantal, i.model_id, len(i.onderdelen)) for i in project.modelinstanties] == [
        ("Onderkast 60", 3, "", 2), ("Ladekast", 1, "", 1),
    ]
    zijkant = project.modelinstanties[0].onderdelen[0]
    # Lengte (horizontaal) -> breedte, Breedte (verticaal) -> hoogte.
    assert (zijkant.breedte, zijkant.hoogte, zijkant.aantal) == (720, 560, 2)
    assert zijkant.nerfrichting_vereist == Nerfrichting.LANGE_ZIJDE
    assert zijkant.kantenband_randen == frozenset({Rand.BOVEN, Rand.ONDER})
    front = project.modelinstanties[1].onderdelen[0]
    assert front.fabriekskantenband_vereist and (front.groep_id, front.groep_volgorde) == ("Fronten", 1)
    plint = project.losse_onderdelen[0]
    assert (plint.materiaal_id, plint.breedte, plint.hoogte, plint.aantal) == (regel.id, 2400, 68, 2)
    # De zaaglijst vermenigvuldigt met het modelaantal.
    aantallen = {r.onderdeel.naam: r.onderdeel.aantal for r in bouw_zaaglijst(project)}
    assert aantallen["Zijkant"] == 6 and aantallen["Bodem"] == 3 and aantallen["Plintregel"] == 2


def test_importeren_met_fout_verandert_niets():
    materialen, _, projecten, _, _ = _bibliotheken()
    project = projecten.toevoegen(Project(id="", naam="Keuken", klant="Jansen"))
    regels = lees_rijen([["Naam", "Materiaal", "Lengte", "Breedte"], ["A", "EMP18", 100, 100], ["B", "Beuken", 100, 100]]).regels
    with pytest.raises(ValueError, match="Beuken"):
        importeer_in_project(projecten, project.id, regels, stel_koppeling_voor(regels, materialen), materialen)
    assert projecten.ophalen(project.id).losse_onderdelen == []


def test_importeren_in_model_negeert_modelkolommen():
    materialen, modellen, _, eiken, _ = _bibliotheken()
    model = modellen.toevoegen(Model(id="", naam="Kast"))
    regels = lees_rijen([KOP, ["Zijkant", "EMP18", 720, 560, 2, "Iets anders", 4, "", "", "", "", ""]]).regels

    model = importeer_in_model(modellen, model.id, regels, stel_koppeling_voor(regels, materialen), materialen)

    assert [(o.naam, o.breedte, o.hoogte, o.aantal, o.materiaal_id) for o in model.onderdelen] == [("Zijkant", 720, 560, 2, eiken.id)]
