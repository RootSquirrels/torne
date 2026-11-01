"""MARINE-002 — verifier un sous-ensemble quotidien de GLORYS12 sur la zone.

GLORYS12 est la réanalyse physique globale de Copernicus Marine : 1/12°,
50 niveaux, mise à jour quotidienne. C'est la source **quotidienne** — donc
la seule des deux réanalyses testées qui parle au pas de temps des
épisodes de panache.

Ce script ne demande pas « est-ce que la source répond ? ». Il demande
**« est-ce que la source a donné ce que j'ai demandé ? »**, et il y a trois
pièges qu'il vérifie un par un :

1. **La fenêtre temporelle.** Le client officiel accepte une période et
   peut en livrer une autre. L'attribut racine `field_date` du fichier
   vaut, dans le fichier obtenu, une date **fausse** : c'est un résidu de
   gabarit du producteur. La vérité est dans la **variable** `time`. La
   vérification se fait donc sur la variable, jamais sur l'attribut.

2. **La valeur de remplissage, avant le changement d'échelle.** Les
   grandeurs sont stockées en entiers comprimés : `so` a un facteur
   d'échelle de 0,00152593 et un décalage de -0,00152593, et la valeur de
   remplissage est **-32767**. Appliquer l'échelle *avant* d'écarter le
   remplissage transforme une absence en **mesure plausible** — pour la
   température potentielle, -32767 devient -2,99 °C. L'ordre des opérations
   n'est pas un détail.

3. **La grille.** GLORYS12 est en grille **régulière** (1/12°) — contrairement
   à ORAS5, dont la grille est **curviligne**. Une coupe « par indices »
   qui marche pour l'une ne marche pas pour l'autre.

Usage :

    uv run python experiments/marine_002_glorys12.py [sortie]
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import h5py
import numpy as np

RACINE = Path(__file__).resolve().parent.parent
"""La racine du depot, ou se trouve le `.env` ignore par git."""

ZONE = (44.0, 48.0, -6.0, -2.0)
"""Latitude 44-48 N, longitude 6 O-2 O : le secteur etudie."""

POINT_ARGO = (47.019115, -4.228885)
"""La position du float Argo 2904125 : le point de comparaison in situ."""

DEBUT = "2026-09-01"
FIN = "2026-09-03"
"""La fenetre demandee — trois jours, la plus proche possible du profil Argo."""

VARIABLES = ("thetao", "so", "uo", "vo")
"""Temperature potentielle, salinite, courant zonal, courant meridional."""

PROFONDEUR_MAX = 1000.0
"""La profondeur demandee, en metres."""


def _identifiants() -> tuple[str, str]:
    """Les identifiants Marine, lus dans le `.env` — jamais affiches, jamais ecrits."""
    env = RACINE / ".env"
    if not env.exists():
        raise SystemExit("pas de .env a la racine du depot")
    valeurs: dict[str, str] = {}
    for ligne in env.read_text(encoding="utf-8").splitlines():
        if "=" in ligne and not ligne.strip().startswith("#"):
            cle, valeur = ligne.split("=", 1)
            valeurs[cle.strip()] = valeur.strip().strip('"').strip("'")
    for cle in ("COPERNICUS_MARINE_USERNAME", "COPERNICUS_MARINE_PASSWORD"):
        if cle not in valeurs:
            raise SystemExit(f"pas de {cle} dans le .env")
    return valeurs["COPERNICUS_MARINE_USERNAME"], valeurs["COPERNICUS_MARINE_PASSWORD"]


def main(argv: list[str]) -> int:
    """Le sous-ensemble, demande puis verifie."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    sortie = Path(argv[1]) if len(argv) > 1 else Path(tempfile.mkdtemp(prefix="torne-marine-002-"))
    sortie.mkdir(parents=True, exist_ok=True)
    fichier = sortie / f"glorys12_daily_{DEBUT}_{FIN}.nc"

    print("TORNE — MARINE-002, sous-ensemble quotidien GLORYS12 sur la zone")
    print(f"zone   : {ZONE[0]}-{ZONE[1]} N, {ZONE[2]}-{ZONE[3]} E")
    print(f"fenetre demandee : {DEBUT} -> {FIN} | profondeur 0-{PROFONDEUR_MAX} m")
    print("identifiants : lus dans le .env, jamais affiches, jamais ecrits sur le disque")
    print()

    if not fichier.exists():
        _demander(fichier)
    else:
        print(f"fichier deja present : {fichier}")
    print()

    _verifier(fichier)
    return 0


def _demander(fichier: Path) -> None:
    """La requete, avec le client officiel de Copernicus Marine."""
    import copernicusmarine

    utilisateur, mot_de_passe = _identifiants()
    print(f"1. la requete (client officiel, version {copernicusmarine.__version__})")
    copernicusmarine.subset(
        dataset_id="cmems_mod_glo_phy_my_0.083deg_P1D-m",
        username=utilisateur,
        password=mot_de_passe,
        variables=list(VARIABLES),
        minimum_longitude=ZONE[2],
        maximum_longitude=ZONE[3],
        minimum_latitude=ZONE[0],
        maximum_latitude=ZONE[1],
        minimum_depth=0.0,
        maximum_depth=PROFONDEUR_MAX,
        start_datetime=DEBUT,
        end_datetime=FIN,
        output_directory=str(fichier.parent),
        output_filename=fichier.stem,
        file_format="netcdf",
        coordinates_selection_method="inside",
        overwrite=True,
    )
    print(f"   fichier : {fichier} ({fichier.stat().st_size} octets)")


def _texte(valeur) -> str:
    """Un attribut HDF5, lu comme une chaine."""
    if isinstance(valeur, bytes):
        return valeur.decode("ascii", "replace")
    return str(valeur)


def _verifier(fichier: Path) -> None:
    """Ce que le fichier contient reellement, et non ce qu'il promet."""
    with h5py.File(fichier, "r") as donnees:
        print("2. la conformity du fichier")
        print(f"   conventions : {_texte(donnees.attrs.get('Conventions', b''))}")
        print(f"   source      : {_texte(donnees.attrs.get('source', b''))}")
        print(f"   signature   : {fichier.read_bytes()[:4]!r} (netCDF-4 / HDF5)")

        # -- la fenetre temporelle, lue dans la VARIABLE, pas dans l'attribut
        temps = np.array(donnees["time"][()]).ravel()
        unite = _texte(donnees["time"].attrs.get("units", ""))
        origine = unite.split("since")[-1].strip()
        deltas = np.array([np.datetime64(origine) + np.timedelta64(int(v), "h") for v in temps])
        demande = np.arange(np.datetime64(DEBUT), np.datetime64(FIN) + np.timedelta64(1, "D"))
        print(f"   fenetre demandee  : {DEBUT} -> {FIN} ({len(demande)} jours)")
        print(f"   fenetre livree    : {deltas[0]} -> {deltas[-1]} ({len(deltas)} pas)")
        conforme = len(deltas) == len(demande) and all(d in set(deltas) for d in demande)
        print(f"   [FAIT] fenetre conforme : {conforme}")
        print(
            f"   ATTENTION : l'attribut racine 'field_date' vaut "
            f"{_texte(donnees.attrs.get('field_date', b''))!r} — c'est FAUX."
        )
        print("               Un attribut racine peut etre un residu de gabarit :")
        print("               la date verifiee est celle de la variable 'time'.")

        # -- la grille
        latitude = np.array(donnees["latitude"][()]).ravel()
        longitude = np.array(donnees["longitude"][()]).ravel()
        profondeur = np.array(donnees["depth"][()]).ravel()
        print("\n3. la grille — REGULIERE, contrairement a ORAS5")
        print(
            f"   latitude  : {latitude.size} points, {latitude[0]:.3f} a {latitude[-1]:.3f} "
            f"(pas {latitude[1] - latitude[0]:.6f} deg)"
        )
        print(
            f"   longitude : {longitude.size} points, {longitude[0]:.3f} a {longitude[-1]:.3f} "
            f"(pas {longitude[1] - longitude[0]:.6f} deg)"
        )
        print(
            f"   profondeurs: {profondeur.size} niveaux, de {profondeur[0]:.3f} m "
            f"a {profondeur[-1]:.1f} m"
        )

        # -- les grandeurs : remplissage ecarte AVANT le changement d'echelle
        print("\n4. les grandeurs")
        for nom in VARIABLES:
            variable = donnees[nom]
            attributs = variable.attrs
            echelle = float(np.array(attributs.get("scale_factor", [1.0])).ravel()[0])
            decalage = float(np.array(attributs.get("add_offset", [0.0])).ravel()[0])
            remplissage = float(np.array(attributs.get("_FillValue", [-32767])).ravel()[0])
            valide_min = attributs.get("valid_min")
            print(
                f"   {nom:<7} unite={_texte(attributs.get('units', b'')):<14} "
                f"echelle={echelle:.8f} decalage={decalage:+.8f} "
                f"remplissage={remplissage:.0f}"
                + (f" valid_min={_texte(valide_min)}" if valide_min is not None else "")
            )

        # -- le profil au point du float Argo, dechiffre correctement
        ligne = int(np.argmin(np.abs(latitude - POINT_ARGO[0])))
        colonne = int(np.argmin(np.abs(longitude - POINT_ARGO[1])))
        print("\n5. le profil au point le plus proche du float Argo")
        print(
            f"   {latitude[ligne]:.4f} N  {longitude[colonne]:.4f} E "
            f"(a {abs(latitude[ligne] - POINT_ARGO[0]) * 111:.1f} km en lat, "
            f"{abs(longitude[colonne] - POINT_ARGO[1]) * 84:.1f} km en lon)"
        )
        print(f"   {'prof (m)':>10}  {'salinite':>10}  {'temp pot.':>10}  {'u':>10}  {'v':>10}")
        for niveau, p in enumerate(profondeur[:12]):
            valeurs = []
            for nom in VARIABLES:
                variable = donnees[nom]
                attributs = variable.attrs
                echelle = float(np.array(attributs.get("scale_factor", [1.0])).ravel()[0])
                decalage = float(np.array(attributs.get("add_offset", [0.0])).ravel()[0])
                remplissage = float(np.array(attributs.get("_FillValue", [-32767])).ravel()[0])
                brut = float(variable[0, niveau, ligne, colonne])
                if brut == remplissage:
                    valeurs.append("ABSENT")
                else:
                    valeurs.append(f"{brut * echelle + decalage:10.4f}")
            salinite, temperature, u, v = valeurs[1], valeurs[0], valeurs[2], valeurs[3]
            print(f"   {p:10.3f}  {salinite:>10}  {temperature:>10}  {u:>10}  {v:>10}")

        print("\n   « ABSENT » = la valeur de remplissage (-32767), ecartee AVANT")
        print("   d'appliquer l'echelle. Sans cela, une absence devient une mesure :")
        print("   -32767 chez thetao donnerait -2,99 degC.")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
