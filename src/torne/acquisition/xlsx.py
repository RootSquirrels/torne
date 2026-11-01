"""Un lecteur de tableur minimal, sans dependance externe.

Les references d'identifiants dont TORNE a besoin sont publiees sous forme de
fichiers `.xlsx` : la Commission europeenne (le reseau ENTSOG) et GIE (la
table de correspondance des codes EIC). Ce module en extrait le contenu
utile — une liste de lignes de valeurs.

Ce n'est **pas** un tableur : ni style, ni formule, ni formatage, ni fusion de
cellules. C'est un **lecteur de reference**, et il fait ce qu'il annonce.

Le format `.xlsx` est un conteneur ZIP :

- `xl/sharedStrings.xml` porte les chaines, une par index ;
- `xl/worksheets/sheetN.xml` porte les cellules, chacune referencing une
  chaine par son index, ou portant sa propre valeur.

Les chaines peuvent etre ecrites en plusieurs morceaux (texte enrichi) : elles
sont alors concatenees.
"""

from __future__ import annotations

import re
import zipfile
from xml.etree import ElementTree

ESPACE_NOM = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

COLONNE = re.compile(r"([A-Z]+)")


def _index_de_colonne(reference: str) -> int:
    """L'index d'une colonne, a partir de sa reference (`"C5"` -> 2)."""
    trouve = COLONNE.match(reference or "")
    if not trouve:
        return 0
    index = 0
    for caractere in trouve.group(1):
        index = index * 26 + (ord(caractere) - ord("A") + 1)
    return index - 1


def _textes(element: ElementTree.Element) -> str:
    """Le texte d'un element, concatene s'il est ecrit en plusieurs morceaux."""
    morceaux = [noeud.text or "" for noeud in element.iter(f"{ESPACE_NOM}t") if noeud.text]
    return "".join(morceaux)


def _chaines_partagees(archive: zipfile.ZipFile) -> list[str]:
    """Les chaines du classeur, dans l'ordre de leurs index."""
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    racine = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    return [_textes(si) for si in racine.findall(f"{ESPACE_NOM}si")]


def _feuille(archive: zipfile.ZipFile, numero: int) -> str:
    """Le nom du membre qui porte la feuille demandee."""
    noms = [n for n in archive.namelist() if n.startswith("xl/worksheets/sheet")]
    if not noms:
        raise ValueError("le classeur ne contient aucune feuille")
    noms.sort()
    return noms[min(numero, len(noms)) - 1]


def lire_xlsx(donnees: bytes, feuille: int = 1) -> list[list[str]]:
    """Les lignes d'une feuille, sous forme de listes de valeurs textuelles.

    Les cellules vides sont des chaines vides : la position d'une valeur dans
    une ligne reste donc celle qu'elle a dans le fichier.
    """
    with zipfile.ZipFile(_flux(donnees)) as archive:
        chaines = _chaines_partagees(archive)
        racine = ElementTree.fromstring(archive.read(_feuille(archive, feuille)))

    lignes: list[list[str]] = []
    for ligne in racine.iter(f"{ESPACE_NOM}row"):
        valeurs: dict[int, str] = {}
        for cellule in ligne.findall(f"{ESPACE_NOM}c"):
            index = _index_de_colonne(cellule.get("r", ""))
            type_ = cellule.get("t")
            if type_ == "s":
                noeud = cellule.find(f"{ESPACE_NOM}v")
                if noeud is not None and noeud.text:
                    try:
                        valeurs[index] = chaines[int(noeud.text)]
                    except (ValueError, IndexError):
                        valeurs[index] = ""
            elif type_ == "inlineStr":
                valeurs[index] = _textes(cellule)
            else:
                noeud = cellule.find(f"{ESPACE_NOM}v")
                valeurs[index] = (noeud.text or "") if noeud is not None else ""
        if valeurs:
            largeur = max(valeurs) + 1
            lignes.append([valeurs.get(i, "") for i in range(largeur)])
        else:
            lignes.append([])
    return lignes


def _flux(donnees: bytes):
    """Les octets, comme un fichier en memoire."""
    import io

    return io.BytesIO(donnees)


__all__ = ["lire_xlsx"]
