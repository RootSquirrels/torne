"""MARINE-002 — extraire l'échantillon tridimensionnel ORAS5 sur la zone étudiée.

ORAS5 est un produit **global** : son formulaire ne demande pas de zone. Une
zone se **découpe** donc après téléchargement, sur un champ global de
1,8 Go. Ce script fait cette découpe, et il rend le résultat **inspectable** :
ce qui a été extrait, d'où, et à quoi cela ressemble.

Ce qu'il faut savoir de la grille avant de découper
----------------------------------------------------

La grille d'ORAS5 est **tripolaire**, donc **curviligne** : `nav_lat` et
`nav_lon` sont deux champs **2D** de la forme (1021, 1442), pas deux
vecteurs. Une zone ne se découpe donc **pas** par une tranche rectangulaire
d'indices : il faut trouver les indices dont les coordonnées *variables*
tombent dans le rectangle. Une coupe « à la longitude 4 °O » serait fausse.

Ce qu'il extrait
----------------

- **Quatre** grandeurs — salinité, température potentielle, courant zonal et
  courant méridional — sur les **niveaux** demandés, dans la zone.
- Un **échantillon netCDF** écrit avec `scipy.io.netcdf_file`, c'est-à-dire
  avec une dépendance **déjà déclarée** au dépôt.
- Un **profil vertical** au point du floatter Argo 2904125, pour que
  l'in situ et le modèle soient comparables au même endroit.

Usage :

    uv run python experiments/marine_002_echantillon_oras5.py [repertoire] [sortie]
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import h5py
import numpy as np
from scipy.io import netcdf_file

RACINE = Path(__file__).resolve().parent.parent
"""La racine du depot, ou se trouvent les fichiers telecharges."""

ZONE = (44.0, 48.0, -6.0, -2.0)
"""Latitude 44-48 N, longitude 6 O-2 O : le secteur etudie."""

POINT_ARGO = (47.019115, -4.228885)
"""La position du float Argo 2904125 : le point de comparaison in situ."""

NIVEAUX = (0.0, 10.0, 20.0, 50.0, 100.0, 200.0, 500.0, 1000.0)
"""Les profondeurs du genre, en metres, qu'on veut voir."""

GRANDEURS = {
    "salinite": ("vosaline", "vosaline", "psu"),
    "temperature_potentielle": ("votemper", "votemper", "degree_Celsius"),
    "courant_meridional": ("vomecrty", "vomecrty", "m s-1"),
    "courant_zonal_tourne": ("vozocrtx", "vozocrtx", "m s-1"),
}
"""La grandeur, le prefixe du fichier netCDF qui la porte, et son unite."""


def _fichiers(repertoire: Path) -> dict[str, Path]:
    """Les fichiers ORAS5 extraits, par grandeur."""
    trouves: dict[str, Path] = {}
    for chemin in sorted(repertoire.glob("*.nc")):
        for grandeur, (prefixe, _variable, _unite) in GRANDEURS.items():
            if chemin.name.startswith(prefixe) and grandeur not in trouves:
                trouves[grandeur] = chemin
    return trouves


def main(argv: list[str]) -> int:
    """La decoupe."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    repertoire = Path(argv[1]) if len(argv) > 1 else RACINE / "data" / "marine-002" / "oras5"
    sortie = Path(argv[2]) if len(argv) > 2 else Path(tempfile.mkdtemp(prefix="torne-marine-002-"))
    sortie.mkdir(parents=True, exist_ok=True)

    fichiers = _fichiers(repertoire)
    if not fichiers:
        print(f"aucun fichier ORAS5 dans {repertoire}")
        return 1

    print("TORNE — MARINE-002, decoupe de l'echantillon ORAS5 sur la zone")
    print(f"source : {repertoire}")
    print(f"zone   : {ZONE[0]}-{ZONE[1]} N, {ZONE[2]}-{ZONE[3]} E")
    print()

    with h5py.File(fichiers["salinite"], "r") as reference:
        nav_lat = reference["nav_lat"][()]
        nav_lon = reference["nav_lon"][()]
        profondeur = reference["deptht"][()]
        temps = reference["time_counter"][()]
        unite_temps = reference["time_counter"].attrs.get("units", b"")
        unite_temps = unite_temps.decode() if isinstance(unite_temps, bytes) else str(unite_temps)
        origine = unite_temps.split("since")[-1].strip() if "since" in unite_temps else ""
        date_champ = (
            np.datetime64(origine) + np.timedelta64(int(temps[0]), "s")
            if origine
            else np.datetime64("NaT")
        )
        print("1. la grille")
        print(f"   nav_lat/nav_lon : {nav_lat.shape} — grille CURVILIGNE (tripolaire)")
        print(
            f"   niveaux         : {profondeur.shape[0]} — de {profondeur[0]:.1f} m "
            f"a {profondeur[-1]:.1f} m"
        )
        print(f"   pas de temps    : {temps[0]} {unite_temps} -> {date_champ}")
        print("                   (le mois moyen est estampé AU MILIEU du mois)")
        attribus = reference["vosaline"].attrs
        for cle in ("units", "long_name", "standard_name", "coordinates"):
            if cle in attribus:
                valeur = attribus[cle]
                texte = valeur.decode() if isinstance(valeur, bytes) else str(valeur)
                print(f"   vosaline.{cle:<14} = {texte}")

        masque = (
            (nav_lat >= ZONE[0])
            & (nav_lat <= ZONE[1])
            & (nav_lon >= ZONE[2])
            & (nav_lon <= ZONE[3])
        )
        lignes, colonnes = np.nonzero(masque)
        if lignes.size == 0:
            print("   aucune maille de la zone")
            return 1
        i0, i1 = int(lignes.min()), int(lignes.max()) + 1
        j0, j1 = int(colonnes.min()), int(colonnes.max()) + 1
        print("\n2. la zone dans la grille")
        print(f"   mailles selectionnees : {int(masque.sum())}")
        print(f"   rectangle d'indices   : i[{i0}:{i1}] · j[{j0}:{j1}]")
        print(
            f"   latitude  du rectangle : {nav_lat[i0:i1, j0:j1].min():.3f} "
            f"a {nav_lat[i0:i1, j0:j1].max():.3f}"
        )
        print(
            f"   longitude du rectangle : {nav_lon[i0:i1, j0:j1].min():.3f} "
            f"a {nav_lon[i0:i1, j0:j1].max():.3f}"
        )

        indices_niveaux = []
        for cible in NIVEAUX:
            ecart = np.abs(profondeur - cible)
            position = int(np.argmin(ecart))
            indices_niveaux.append(position)
            print(
                f"   niveau {cible:7.1f} m -> index {position:2d} "
                f"(profondeur reelle {profondeur[position]:.2f} m)"
            )
        indices_niveaux = np.array(indices_niveaux)

        echantillon: dict[str, np.ndarray] = {}
        absents_par_grandeur: dict[str, int] = {}
        for grandeur, chemin in fichiers.items():
            _prefixe, variable, _unite = GRANDEURS[grandeur]
            with h5py.File(chemin, "r") as source:
                bloc = source[variable][0, indices_niveaux, i0:i1, j0:j1]
                remplissage = source[variable].attrs.get("_FillValue")
            valeurs = np.asarray(bloc, dtype="float32")
            if remplissage is not None:
                # La valeur de remplissage d'ORAS5 est 9,96921e+36 : elle marque
                # les niveaux **sous le fond marin**. C'est une absence, jamais
                # une mesure — et elle doit etre qualifiee, pas comptee.
                seuil = float(np.asarray(remplissage).ravel()[0])
                absents = int(np.sum(valeurs >= seuil * 0.5))
                valeurs = np.where(valeurs >= seuil * 0.5, np.nan, valeurs)
            else:
                absents = 0
            echantillon[grandeur] = valeurs
            absents_par_grandeur[grandeur] = absents
            print(f"   {grandeur:<32} {valeurs.shape} · {absents} valeur(s) de remplissage")

        _ecrire(
            echantillon,
            sortie,
            profondeur[indices_niveaux],
            nav_lat[i0:i1, j0:j1],
            nav_lon[i0:i1, j0:j1],
            temps[0],
        )
        _profil(
            echantillon, nav_lat[i0:i1, j0:j1], nav_lon[i0:i1, j0:j1], profondeur[indices_niveaux]
        )
    return 0


def _ecrire(
    echantillon: dict[str, np.ndarray],
    sortie: Path,
    profondeur: np.ndarray,
    lat: np.ndarray,
    lon: np.ndarray,
    temps: float,
) -> None:
    """L'echantillon, ecrit en netCDF-3 avec la dependance deja declaree."""
    cible = sortie / "echantillon_oras5_zone.nc"
    with netcdf_file(str(cible), "w") as f:
        f.title = "Echantillon 3D ORAS5 - zone Atlantique Nord-Est"
        f.Conventions = "CF-1.6"
        f.zone = f"{ZONE[0]}-{ZONE[1]}N {ZONE[2]}-{ZONE[3]}E"
        f.source = "ORAS5 monthly, CDS reanalysis-oras5"
        f.history = "decoupe par marine_002_echantillon_oras5.py"
        f.createDimension("niveaux", profondeur.size)
        f.createDimension("y", lat.shape[0])
        f.createDimension("x", lat.shape[1])
        f.createDimension("temps", 1)

        def ecrire(nom, donnees, unite):
            variable = f.createVariable(nom, "f4", ("niveaux", "y", "x"))
            variable.units = unite
            variable[:] = donnees

        ecrire("vosaline", echantillon["salinite"], "psu")
        ecrire("votemper", echantillon["temperature_potentielle"], "degree_Celsius")
        ecrire("vomecrty", echantillon["courant_meridional"], "m s-1")
        ecrire("vozocrtx", echantillon["courant_zonal_tourne"], "m s-1")

        def ecrire_axe(nom, donnees, unite):
            variable = f.createVariable(
                nom, "f4", ("niveaux",) if donnees.ndim == 1 else ("y", "x")
            )
            variable.units = unite
            variable[:] = donnees

        ecrire_axe("depth", profondeur, "m")
        ecrire_axe("nav_lat", lat, "degrees_north")
        ecrire_axe("nav_lon", lon, "degrees_east")
        chronologie = f.createVariable("time_counter", "f8", ("temps",))
        chronologie.units = "days since 1900-01-01"
        chronologie[:] = [temps]
    print(f"\n3. echantillon ecrit : {cible} ({cible.stat().st_size} octets)")


def _profil(
    echantillon: dict[str, np.ndarray],
    lat: np.ndarray,
    lon: np.ndarray,
    profondeur: np.ndarray,
) -> None:
    """Le profil vertical au point du float Argo, pour comparaison in situ."""
    print("\n4. le profil vertical au point du float Argo 2904125")
    distance = (lat - POINT_ARGO[0]) ** 2 + (lon - POINT_ARGO[1]) ** 2
    ligne, colonne = np.unravel_index(int(np.argmin(distance)), distance.shape)
    ecart = float(np.sqrt(distance[ligne, colonne]))
    print(
        f"   maille la plus proche : {lat[ligne, colonne]:.4f} N "
        f"{lon[ligne, colonne]:.4f} E (a {ecart * 111:.1f} km)"
    )
    print(f"   {'prof (m)':>10}  {'salinite':>9}  {'temp (C)':>9}  {'v merid.':>9}")
    for niveau, p in enumerate(profondeur):
        salin = echantillon["salinite"][niveau, ligne, colonne]
        temp = echantillon["temperature_potentielle"][niveau, ligne, colonne]
        courant = echantillon["courant_meridional"][niveau, ligne, colonne]
        print(
            f"   {p:10.1f}  {_ou_absent(salin):>9}  {_ou_absent(temp):>9}  {_ou_absent(courant):>9}"
        )
    print("   « ABSENT » = valeur de remplissage ORAS5 (9,96921e+36) : niveau")
    print("   sous le fond marin a cet endroit. Ce n'est pas une mesure.")


def _ou_absent(valeur: float) -> str:
    """La valeur, ou la mention de son absence (sous le fond marin)."""
    if valeur != valeur:  # NaN : la valeur de remplissage, masquee
        return "ABSENT"
    return f"{valeur:.3f}"


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
