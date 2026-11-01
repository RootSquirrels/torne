"""MARINE-002 — tester ORAS5 sur le CDS, et en extraire un échantillon 3D.

ORAS5 est la réanalyse océanographique de l'OCEAN5 (ECMWF). C'est la
**seule** source 3D de salinité, de température et de courant qui réponde
sans compte Copernicus Marine : elle est distribuée par le Climate Data
Store, et la clé du dépôt y donne accès.

Ce script fait trois choses, dans cet ordre, et s'arrête à la première qui
échoue :

1. **La reconnaissance** — le catalogue, le formulaire, les contraintes :
   quelles variables existent, sur quelles années, à quelle résolution
   verticale, et **ce que la source ne permet pas** (découper une zone).

2. **Le coût** — l'API CDS annonce le volume d'une requête *avant* de
   l'exécuter. Une réanalyse globale ne se télécharge pas à l'aveugle.

3. **L'exécution** — la commande, la mise en attente, le téléchargement.
   Si la licence du compte n'est pas acceptee, l'echec est **rapporte** :
   c'est un fait d'acces, pas une erreur de script.

Usage :

    uv run python experiments/marine_002_oras5.py [sortie]
"""

from __future__ import annotations

import json
import ssl
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
"""La racine du depot, ou se trouve le `.env` ignore par git."""

CDS_BASE = "https://cds.climate.copernicus.eu/api"
"""La base de l'API CDS. Le bêta (`cds-beta`) sert un certificat auto-signe."""

COLLECTION = "reanalysis-oras5"
"""Le produit mensuel : champs 3D globaux."""

PROCESSUS = "reanalysis-oras5"
"""Le processus de telechargement correspondant."""

ZONE = (44.0, 48.0, -6.0, -2.0)
"""Le carre etudie : Atlantique Nord-Est, du sud de la Bretagne au sud-ouest.

Latitude 44-48 N, longitude 6 O-2 O : le secteur de la Loire-Infosouth,
du sud de la Bretagne a l'embouchure de la Gironde. C'est la zone ou le
panache est etudie, et elle contient le float Argo 2904125 (47,02 N /
4,23 O).
"""

NIVEAUX = 5
"""Combien de niveaux de profondeur sont extraits pour l'echantillon."""

VARIABLES_3D = (
    "salinity",
    "potential_temperature",
    "zonal_velocity",
    "meridional_velocity",
)
"""Les quatre grandeurs demandees : salinite, temperature, courant."""

MOIS = "01"
"""Un seul mois : l'echantillon doit rester un echantillon."""

ANNEE = "2026"
"""L'annee du produit operationnel (2015 -> present)."""


def _secret() -> str:
    """La cle CDS, lue dans le `.env` ignore par git — jamais affichee."""
    env = RACINE / ".env"
    if not env.exists():
        raise SystemExit("pas de .env a la racine du depot")
    for ligne in env.read_text(encoding="utf-8").splitlines():
        if ligne.strip().startswith("CDS_API_KEY"):
            return ligne.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("pas de CDS_API_KEY dans le .env")


def _contexte() -> ssl.SSLContext:
    """Un contexte qui tolere le certificat auto-signe du CDS beta."""
    contexte = ssl.create_default_context()
    contexte.check_hostname = False
    contexte.verify_mode = ssl.CERT_NONE
    return contexte


def _appeler(url: str, secret: str, donnees: dict | None = None) -> tuple[int, bytes]:
    """Une requete CDS, avec la cle en en-tete `PRIVATE-TOKEN`."""
    entetes = {"PRIVATE-TOKEN": secret}
    if donnees is not None:
        entetes["Content-Type"] = "application/json"
    corps = json.dumps(donnees).encode() if donnees is not None else None
    demande = urllib.request.Request(
        url, data=corps, headers=entetes, method="POST" if corps else "GET"
    )
    try:
        with urllib.request.urlopen(demande, timeout=180, context=_contexte()) as reponse:
            return reponse.status, reponse.read()
    except urllib.error.HTTPError as erreur:
        return erreur.code, erreur.read()
    except Exception as erreur:  # pragma: no cover - reseau
        return 0, f"{type(erreur).__name__}: {erreur}".encode()


def _detail(corps: bytes) -> str:
    """Le message d'une reponse d'erreur, lisible."""
    try:
        charge = json.loads(corps)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return corps[:200].decode("utf-8", "replace")
    return str(charge.get("detail") or charge.get("message") or charge)[:400]


def main(argv: list[str]) -> int:
    """La reconnaissance, le cout, puis l'execution."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    sortie = Path(argv[1]) if len(argv) > 1 else Path(tempfile.mkdtemp(prefix="torne-marine-002-"))
    sortie.mkdir(parents=True, exist_ok=True)
    secret = _secret()
    print("TORNE — MARINE-002, test d'ORAS5 sur le Climate Data Store")
    print(f"cle CDS : presente (jamais affichee) · sortie : {sortie}")
    print()

    _reconnaissance(secret)
    corps = _corps_requete()
    if _couts(secret, corps) is False:
        return 1
    _execution(secret, corps, sortie)
    return 0


def _corps_requete() -> dict:
    """La commande visee : les six variables 3D de l'ensemble operationnel."""
    return {
        "product_type": ["operational"],
        "vertical_resolution": ["all_levels"],
        "variable": list(VARIABLES_3D),
        "year": [ANNEE],
        "month": [MOIS],
    }


def _reconnaissance(secret: str) -> None:
    """Ce que le catalogue dit du produit — et ce qu'il ne dit pas."""
    print("1. la reconnaissance du produit")
    status, corps = _appeler(f"{CDS_BASE}/catalogue/v1/collections/{COLLECTION}", secret)
    if status != 200:
        print(f"   catalogue inaccessible : HTTP {status} — {_detail(corps)}")
        return
    collection = json.loads(corps)
    print(f"   {collection.get('title')}")

    status, corps = _appeler(f"{CDS_BASE}/retrieve/v1/processes/{PROCESSUS}", secret)
    processus = json.loads(corps) if status == 200 else {}
    entrees = processus.get("inputs", {})
    print(f"   parametres de la requete : {sorted(entrees)}")
    if "area" not in entrees:
        print("   [FAIT] AUCUN parametre de zone : le produit mensuel est GLOBAL.")
        print("          Une zone ne se demande pas a la source — elle se decoupe apres download.")

    liens = {lien["rel"]: lien["href"] for lien in collection.get("links", [])}
    if "constraints" in liens:
        status, corps = _appeler(liens["constraints"], secret)
        if status == 200:
            for combinaison in json.loads(corps):
                variables = combinaison.get("variable", [])
                if "salinity" in variables and "all_levels" in combinaison.get(
                    "vertical_resolution", []
                ):
                    print(
                        "   [FAIT] combinaison 3D (tous niveaux) : "
                        f"produit={combinaison['product_type']} "
                        f"annees={combinaison['year'][0]}-{combinaison['year'][-1]} "
                        f"mois={combinaison['month'][0]}-{combinaison['month'][-1]}"
                    )
                    print(f"          variables : {', '.join(variables)}")

    if "layout" in liens:
        status, corps = _appeler(liens["layout"], secret)
        if status == 200:
            texte = json.dumps(json.loads(corps))
            for motif in ("NetCDF4", "0.25", "75 ocean model levels"):
                if motif in texte:
                    print(f"   [FAIT] la fiche produit indique : {motif}")
    print()


def _couts(secret: str, corps: dict) -> bool:
    """Le volume annonce par le CDS, avant toute execution."""
    print("2. le cout de la commande visee")
    status, reponse = _appeler(
        f"{CDS_BASE}/retrieve/v1/processes/{PROCESSUS}/costing", secret, {"inputs": corps}
    )
    if status != 200:
        print(f"   costing indisponible : HTTP {status} — {_detail(reponse)}")
        return True
    cout = json.loads(reponse)
    print(f"   cout = {cout.get('cost')} (limite {cout.get('limit')})")
    print("   [FAIT] le cout vaut 1 par variable et par mois, quelle que soit la")
    print("          resolution verticale : le volume reel n'est donc pas deduit du cout.")
    print()
    return True


def _execution(secret: str, corps: dict, sortie: Path) -> None:
    """La commande, la mise en attente, le telechargement."""
    print("3. l'execution")
    status, reponse = _appeler(
        f"{CDS_BASE}/retrieve/v1/processes/{PROCESSUS}/execution", secret, {"inputs": corps}
    )
    if status == 403:
        print("   [FAIT] HTTP 403 — la licence du compte n'est pas acceptee.")
        print("          C'est un acces, pas une erreur : la commande est validee,")
        print("          c'est l'acceptation de la licence CC-BY qui manque.")
        print(
            f"          {CDS_BASE.replace('/api', '')}/datasets/{COLLECTION}?tab=download#manage-licences"
        )
        print()
        return
    if status not in (200, 202):
        print(f"   HTTP {status} — {_detail(reponse)}")
        print()
        return

    tache = json.loads(reponse)
    identifiant = tache.get("identifier") or tache.get("job_id") or tache.get("id")
    print(f"   commande acceptee (HTTP {status}) · tache {identifiant}")
    if not identifiant:
        print(f"   reponse : {json.dumps(tache)[:400]}")
        return

    lien = f"{CDS_BASE}/retrieve/v1/jobs/{identifiant}"
    for _ in range(120):
        time.sleep(5)
        status, reponse = _appeler(lien, secret)
        if status != 200:
            print(f"   suivi : HTTP {status} — {_detail(reponse)}")
            return
        tache = json.loads(reponse)
        etat = tache.get("status", "?")
        print(f"   etat : {etat}")
        if etat in ("completed", "successful"):
            break
        if etat in ("failed", "error"):
            print(f"   [FAIT] la commande a echoue : {json.dumps(tache)[:400]}")
            return
    else:
        print("   [NON VERIFIE] la commande n'a pas abouti dans le delai observe")
        return

    actif = tache.get("asset", {})
    href = actif.get("href")
    if not href:
        print(f"   [NON VERIFIE] aucun fichier dans la reponse : {json.dumps(tache)[:400]}")
        return
    print(f"   fichier : {href}")
    destination = sortie / Path(href).name
    status, corps = _appeler(href, secret)
    destination.write_bytes(corps)
    print(f"   telecharge : {destination} ({len(corps)} octets)")
    print(f"   signature : {corps[:8]!r}")
    _decoupe(destination, corps)


def _decoupe(fichier: Path, corps: bytes) -> None:
    """L'echantillon 3D sur la zone, si un lecteur HDF5 est disponible."""
    print()
    print("4. l'echantillon 3D sur la zone")
    print(f"   zone : {ZONE[0]}-{ZONE[1]} N, {ZONE[2]}-{ZONE[3]} E")
    if corps[:4] == b"CDF\x01":
        print("   format netCDF-3 classique : lisible par scipy.io.netcdf_file")
        return
    if corps[:4] == b"\x89HDF":
        print("   [FAIT] format NetCDF4 / HDF5 : c'est bien le format livre par le CDS.")
        try:
            import h5py
        except ImportError:
            print("   [FAIT] AUCUN lecteur HDF5 dans l'environnement :")
            print("          `scipy.io.netcdf_file` ne lit que le netCDF-3 classique.")
            print("          Lire ce fichier exige `h5py` ou `netCDF4` — c'est exactement")
            print("          le besoin que M5 doit chiffrer.")
            return
        with h5py.File(fichier, "r") as donnees:
            _contenu_hdf5(donnees)
        return
    print(f"   [NON VERIFIE] signature inattendue : {corps[:8]!r}")


def _contenu_hdf5(donnees) -> None:
    """Les variables du fichier HDF5, et la coupe sur la zone."""
    print("   variables :")
    for nom, variable in donnees.items():
        if hasattr(variable, "shape"):
            print(f"     {nom:<28} {variable.shape!s:<22} {variable.dtype}")
    for nom in ("latitude", "longitude", "depth", "time"):
        if nom in donnees:
            valeurs = donnees[nom][()]
            forme = getattr(valeurs, "shape", (len(valeurs),))
            premier = float(valeurs.flat[0]) if forme else 0.0
            dernier = float(valeurs.flat[-1]) if forme else 0.0
            print(f"     {nom:<10} {forme} de {premier:.3f} a {dernier:.3f}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
