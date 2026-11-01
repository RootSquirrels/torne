"""Les tests du lecteur de tableur.

Le lecteur doit restituer les chaines **a leur place** : une cellule vide
laisse un trou, sinon la colonne d'un code EIC se decale et la reference
devient fausse.
"""

from __future__ import annotations

import io
import zipfile

import pytest

from torne.acquisition.xlsx import lire_xlsx


def _classeur() -> bytes:
    """Un `.xlsx` minimal, construit a la main : deux chaines, trois lignes."""
    shared = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        ' count="3" uniqueCount="3">'
        "<si><t>Country</t></si>"
        "<si><t>Code</t></si>"
        "<si><t>21W000000000057V</t></si>"
        "</sst>"
    )
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>"
        '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>'
        '<row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2"/></row>'
        '<row r="3"><c r="A3" t="inlineStr"><is><t>AT</t></is></c>'
        '<c r="B3"><v>42</v></c></row>'
        "</sheetData></worksheet>"
    )
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as archive:
        archive.writestr("xl/sharedStrings.xml", shared)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
        archive.writestr("xl/workbook.xml", "<workbook/>")
    return tampon.getvalue()


def test_il_lit_les_chaines_partagees() -> None:
    lignes = lire_xlsx(_classeur())
    assert lignes[0] == ["Country", "Code"]
    assert lignes[1][0] == "21W000000000057V"


def test_une_cellule_vide_laisse_sa_place() -> None:
    lignes = lire_xlsx(_classeur())
    # La deuxieme colonne de la ligne 2 est vide : elle ne doit pas disparaitre.
    assert lignes[1] == ["21W000000000057V", ""]
    assert len(lignes[1]) == 2


def test_il_lit_les_chaines_en_ligne_et_les_nombres() -> None:
    lignes = lire_xlsx(_classeur())
    assert lignes[2] == ["AT", "42"]


def test_un_classeur_sans_chaine_partagee_ne_echoue_pas() -> None:
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as archive:
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>x</t></is></c></row>'
            "</sheetData></worksheet>",
        )
    assert lire_xlsx(tampon.getvalue()) == [["x"]]


def test_un_classeur_sans_feuille_echoue_nettoyement() -> None:
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as archive:
        archive.writestr("xl/workbook.xml", "<workbook/>")
    with pytest.raises(ValueError, match="aucune feuille"):
        lire_xlsx(tampon.getvalue())
