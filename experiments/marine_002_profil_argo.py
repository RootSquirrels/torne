"""MARINE-002 — ouvrir un profil Argo réel, et qualifier ce qu'il porte.

MARINE-001 a établi qu'une observation océanographique est un **profil**, et
que le socle n'a pas de place pour le dire. Ce script ne rebuild pas de
socle : il ouvre **un fichier réel**, téléchargé du GDAC d'Ifremer, et il
mesure ce qu'il y trouve.

Ce qu'il regarde, et pourquoi
-----------------------------

- **La coordonnée verticale** — l'axe `Z` d'un profil Argo n'est ni une
  profondeur en mètres ni une grille fixe : c'est une **pression** (decibar),
  et les niveaux sont **irréguliers** et propres à chaque profil. Une
  observation qui n'emporte pas son niveau ne dit rien.

- **Les unités** — température *in situ* ITS-90, salinité *pratique* (psu),
  pression. Ce sont des unités **de mesure**, et le passage à la température
  potentielle (ORAS5) ou à la salinité absolue (g/kg) n'est pas neutre.

- **La convention d'absence, par variable** — chaque variable porte son
  propre `_FillValue`. Sur un profil en temps réel, les variables ajustées
  (`*_ADJUSTED`) sont **entièrement** en valeur de remplissage : ce n'est pas
  une valeur mesurée, c'est une valeur qui n'existe pas encore. Les compter
  comme des mesures serait une faute de lecture.

- **Les indicateurs de qualité** — un **code caractère** par niveau, dont le
  vocabulaire est **documenté ailleurs** (Argo reference table 2) et non dans
  le fichier. Les valeurs « bonnes » sont 1, 2, 5 et 8 ; 9 est l'absence ;
  le calcul du flag de profil ignore 9 et rejette le reste.

- **La structure du profil** — `featureType = trajectoryProfile`, un
  fichier portant `N_PROF` profils et `N_LEVELS` niveaux, chacun avec sa
  valeur **brute** et, en mode différé seulement, sa valeur **ajustée** et
  son erreur.

Usage :

    uv run python experiments/marine_002_profil_argo.py [chemin_ou_url] [sortie]
"""

from __future__ import annotations

import collections
import itertools
import sys
import tempfile
import urllib.request
from pathlib import Path

PROFIL_PAR_DEFAUT = "https://data-argo.ifremer.fr/dac/coriolis/2904125/profiles/R2904125_164.nc"
"""Un profil réel, en Atlantique Nord-Est, opéré par l'Ifremer."""

# Argo reference table 2 — quality control flag scale.
# Source : « Argo User's Manual », section 3.2.1, et « Argo Quality Control
# Manual for CTD and Trajectory Data », annexe 4.1. Le fichier ne porte que
# l'attribut `conventions = "Argo reference table 2"` : le vocabulaire est
# **externe**, comme la table des sentinelles NDBC.
VOCABULAIRE_QC = {
    "0": "aucun controle qualite effectue",
    "1": "bonne donnee",
    "2": "probablement bonne donnee",
    "3": "mauvaise donnee potentiellement corrigeable",
    "4": "mauvaise donnee, non corrigeable",
    "5": "valeur modifiee",
    "8": "valeur estimee (interpolee, extrapolee)",
    "9": "valeur absente",
}
"""Le vocabulaire des indicateurs de qualite, et sa source."""


def _telecharger(url: str, sortie: Path) -> tuple[bytes, str]:
    """Le corps de la reponse, conserve comme preuve brute."""
    demande = urllib.request.Request(url, headers={"User-Agent": "torne-marine-002"})
    with urllib.request.urlopen(demande, timeout=120) as reponse:
        corps = reponse.read()
        media = reponse.headers.get("Content-Type", "unknown")
    sortie.mkdir(parents=True, exist_ok=True)
    nom = sortie / Path(url).name
    nom.write_bytes(corps)
    return corps, media


def _aplatir(tableau):
    """Un tableau, quel que soit son conteneur, vu a plat."""
    if hasattr(tableau, "ravel"):
        return tableau.ravel()
    return tableau


def _texte(tableau) -> str:
    """Un tableau de caracteres netCDF, lu comme une chaine."""
    morceaux: list[str] = []
    for caractere in _aplatir(tableau):
        if isinstance(caractere, bytes):
            morceaux.append(caractere.decode("ascii", "replace"))
        else:
            morceaux.append(str(caractere))
    return "".join(morceaux).strip()


def _valeurs(variable) -> tuple[list[float], int]:
    """Les valeurs mesures, et le compte des valeurs de remplissage.

    Le `_FillValue` est **propre a chaque variable** : c'est la convention
    d'absence de ce fichier, et elle ne se devine pas.
    """
    donnees = [float(v) for v in variable[:].ravel()]
    remplissage = variable._attributes.get("_FillValue")
    if remplissage is None:
        return donnees, 0
    seuil = float(remplissage)
    valides = [v for v in donnees if v != seuil]
    return valides, len(donnees) - len(valides)


def main(argv: list[str]) -> int:
    """Le profil, ouvert et qualifie."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    url = argv[1] if len(argv) > 1 else PROFIL_PAR_DEFAUT
    sortie = Path(argv[2]) if len(argv) > 2 else Path(tempfile.mkdtemp(prefix="torne-marine-002-"))

    print("TORNE — MARINE-002, ouverture d'un profil Argo reel")
    print(f"source : {url}")
    corps, media = _telecharger(url, sortie)
    print(f"recu   : {media} · {len(corps)} octets")
    print(f"preuve : {sortie / Path(url).name}")
    print()

    if corps[:4] != b"CDF\x01":
        print(f"  ATTENTION : signature {corps[:4]!r} — ce n'est pas du netCDF-3 classique")
        return 1
    print("  [FAIT] format netCDF-3 classique (signature CDF\\x01)")

    from scipy.io import netcdf_file

    fichier = netcdf_file(str(sortie / Path(url).name), "r", mmap=False)
    try:
        _rapport(fichier)
    finally:
        fichier.close()
    return 0


def _rapport(fichier) -> None:
    """Le contenu du profil, et ce qu'il autorise a dire."""
    variables = fichier.variables
    attributs = fichier._attributes

    mode = _texte(variables["DATA_MODE"][:])
    print("1. l'identite du profil")
    print(f"   conventions : {attributs.get('Conventions', b'').decode()}")
    print(f"   featureType : {attributs.get('featureType', b'').decode()}")
    print(f"   projet      : {_texte(variables['PROJECT_NAME'][:])}")
    print(
        f"   float       : {_texte(variables['PLATFORM_NUMBER'][:])} "
        f"(type {_texte(variables['PLATFORM_TYPE'][:])})"
    )
    print(f"   cycle       : {int(variables['CYCLE_NUMBER'][0])}")
    print(
        f"   mode        : {mode} — "
        + (
            "temps reel : les valeurs seront REMPLACEES en mode differe"
            if mode == "R"
            else "mode differe : les valeurs sont figees"
        )
    )
    print(f"   cree le     : {_texte(variables['DATE_CREATION'][:])}")
    print(f"   mis a jour  : {_texte(variables['DATE_UPDATE'][:])}")
    print(f"   historique  : {attributs.get('history', b'').decode()[:90]}")

    print("\n2. la position")
    latitude = float(variables["LATITUDE"][0])
    longitude = float(variables["LONGITUDE"][0])
    flag_position = _texte(variables["POSITION_QC"][:])
    print(f"   {latitude:.5f} N  {longitude:.5f} E")
    print(
        f"   qualite de position : {flag_position} "
        f"({VOCABULAIRE_QC.get(flag_position, 'hors vocabulaire documente')})"
    )
    print(
        f"   schema d'echantillonnage vertical : "
        f"{_texte(variables['VERTICAL_SAMPLING_SCHEME'][:])[:60]}"
    )

    print("\n3. la structure du fichier")
    for nom, taille in sorted(fichier.dimensions.items()):
        if nom.startswith("STRING"):
            continue
        print(f"   {nom:<16} {taille}")

    print("\n4. la coordonnee verticale")
    for nom in ("PRES", "PRES_ADJUSTED"):
        if nom not in variables:
            continue
        valeurs, absents = _valeurs(variables[nom])
        attributs_pression = variables[nom]._attributes
        if not valeurs:
            print(
                f"   {nom} : aucune valeur mesuree "
                f"({absents} valeurs de remplissage {attributs_pression.get('_FillValue')})"
            )
            continue
        ecarts = [b - a for a, b in itertools.pairwise(valeurs)]
        print(
            f"   {nom} : unite={attributs_pression.get('units', b'').decode()} "
            f"axis={attributs_pression.get('axis', b'').decode()} "
            f"min={min(valeurs):.2f} max={max(valeurs):.2f}"
        )
        print(
            f"      niveaux={len(valeurs)} · ecarts: min {min(ecarts):.2f} max {max(ecarts):.2f} "
            f"→ grille {'FIXE' if max(ecarts) - min(ecarts) < 1e-9 else 'IRREGULIERE'}"
        )
        print(f"      premiers niveaux : {', '.join(f'{v:.2f}' for v in valeurs[:8])}")
        print(f"      derniers niveaux : {', '.join(f'{v:.2f}' for v in valeurs[-4:])}")

    print("\n5. les grandeurs mesurees")
    for nom in ("PRES", "TEMP", "PSAL"):
        if nom not in variables:
            continue
        variable = variables[nom]
        attributs_valeur = variable._attributes
        valeurs, absents = _valeurs(variable)
        remplissage = attributs_valeur.get("_FillValue", "aucun")
        print(
            f"   {nom:<5} unite={attributs_valeur.get('units', b'').decode():<20} "
            f"min={min(valeurs):.3f} max={max(valeurs):.3f} "
            f"({attributs_valeur.get('long_name', b'').decode()[:38]})"
        )
        print(
            f"        {len(valeurs)} valeur(s) mesuree(s) · {absents} remplissage "
            f"(seuil {remplissage})"
        )
        ajustee = f"{nom}_ADJUSTED"
        if ajustee in variables:
            valeurs_ajustees, absents_ajustes = _valeurs(variables[ajustee])
            if valeurs_ajustees:
                ecarts = [
                    b - a
                    for a, b in zip(valeurs, valeurs_ajustees, strict=False)
                    if abs(b - a) > 1e-9
                ]
                print(
                    f"        ajustee : {len(ecarts)} niveau(s) reellement modifie(s) "
                    f"sur {len(valeurs_ajustees)}"
                )
            else:
                print(
                    f"        ajustee : AUCUNE valeur — les {absents_ajustes} niveaux sont "
                    f"en valeur de remplissage (l'ajustement en mode differe n'est pas publie)"
                )

    print("\n6. les indicateurs de qualite")
    for nom in ("PRES_QC", "TEMP_QC", "PSAL_QC"):
        if nom not in variables:
            continue
        flags = collections.Counter(_texte([c]) for c in variables[nom][0].ravel())
        attributs_flag = variables[nom]._attributes
        print(
            f"   {nom} : conventions={attributs_flag.get('conventions', b'').decode()!r} "
            f"_FillValue={attributs_flag.get('_FillValue', b'').decode()!r}"
        )
        for flag, nombre in sorted(flags.items()):
            print(f"      {flag} : {nombre:>4} niveau(s) — {VOCABULAIRE_QC.get(flag, 'INCONNU')}")
        hors = set(flags) - set(VOCABULAIRE_QC)
        if hors:
            print(f"      [NON VERIFIE] flags hors vocabulaire documente : {sorted(hors)}")

    print("\n7. ce que le profil autorise a dire")
    print("   - l'axe vertical est une PRESSION en decibar, portee par l'observation elle-meme ;")
    print("     la profondeur n'en decoule que par une conversion d'air de mer ;")
    print("   - les niveaux sont IRREGULIERS : une observation marine emporte son niveau,")
    print("     il n'est pas derivable d'une grille ;")
    print("   - le vocabulaire de qualite est DOCUMENTE AILLEURS (table 2 de l'Argonaut) ;")
    print("   - l'absence est codee PAR VARIABLE (_FillValue), et non par une convention globale ;")
    print(f"   - le mode '{mode}' dit si ces valeurs sont definitives ou provisoires.")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
