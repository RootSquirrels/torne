"""LNG-003 — recolte de la reference des installations de stockage.

Le stockage n'a pas d'equivalent du fichier de la Commission europeenne qui
avait suffi pour les terminaux. Cette reconnaissance etablit ce qui est
atteignable, et produit la reference utilisee par la mission.

La reference : la table de correspondance des codes EIC publiee par GIE
(`torne.acquisition.references`), qui donne pour chaque pays le code
d'exploitant et le code d'installation — exactement le couple que la
plateforme exige pour distinguer une installation d'un agregat national.

Ce que la reconnaissance verifie
---------------------------------

1. Quels codes d'exploitant la plateforme **reconnait** (l'agregat
   d'exploitant est alors servi et nomme) ;
2. Quelles installations elle **sert** reellement ;
3. Ce qui reste **non attribue** : l'ecart entre la somme des sites servis et
   l'agregat du pays.

Ce script est la provenance de la reference : il est rejouable.
"""

from __future__ import annotations

import contextlib
import csv
import datetime as dt
import json
import os
import pathlib
import ssl
import sys
import urllib.parse
import urllib.request

from torne.acquisition.credentials import FichierEnvToken
from torne.acquisition.references import TABLE_ACER_GIE, lire_reference_stockage

# Le socle verifie les certificats — il a raison. Mais cette machine n'a aucun
# magasin CA configure pour OpenSSL : on designe celui de `certifi`, qui est
# installe. La verification reste complete.
try:
    import certifi

    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
except ImportError:
    pass

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
"""La sortie doit porter l'ecriture des caracteres accentues."""

RACINE = pathlib.Path(r"C:\Users\Romain\Documents\GitHub\torne")
CTX = ssl.create_default_context(cafile=certifi.where())

PAYS_CIBLES = ["IT", "DE", "FR", "NL", "AT"]
"""Les pays vises en premier : ils portent 74 % du stock souterrain europeen."""

fournisseur = FichierEnvToken(
    "gie.apikey",
    variable="AGSI_API_KEY",
    chemin=RACINE / ".env",
    header="x-key",
    scheme="",
)
CLE = fournisseur.credentials_for("gie.apikey").get("x-key", "")


def get(params: dict) -> dict:
    """Un appel a la plateforme, sans exception si la reponse n'est pas un JSON."""
    q = urllib.parse.urlencode(params)
    requete = urllib.request.Request(
        f"https://agsi.gie.eu/api?{q}", headers={"User-Agent": "torne-probe", "x-key": CLE}
    )
    try:
        with urllib.request.urlopen(requete, timeout=60, context=CTX) as reponse:
            return json.loads(reponse.read().decode("utf-8", "replace"))
    except Exception:
        return {}


def charger_reference():
    """La table ACER, telechargee et resolue."""
    demande = urllib.request.Request(TABLE_ACER_GIE, headers={"User-Agent": "torne-probe"})
    with urllib.request.urlopen(demande, timeout=120, context=CTX) as reponse:
        return lire_reference_stockage(reponse.read())


def main() -> int:
    print("=" * 100)
    print("LNG-003 · recolte de la reference des installations de stockage")
    reference = charger_reference()
    print(f"source : {reference.source}")
    print(f"        {reference.url}")
    print(f"        consultee le {reference.consultee_le}")
    print()
    print("1. la reference")
    print(f"   operateurs (lignes SSO)  : {len(reference.exploitants)}")
    print(f"   installations referencees: {len(reference.installations)}")

    # --- les operateurs reconnus -----------------------------------------
    print()
    print("2. les operateurs reconnus par la plateforme")
    reconnus: dict[tuple[str, str], str] = {}
    for operateur in reference.exploitants:
        charge = get(
            {
                "country": operateur.pays,
                "company": operateur.code_societe,
                "from": "2026-09-01",
                "to": "2026-09-02",
                "size": 128,
            }
        )
        data = charge.get("data") or []
        if data and str(data[0].get("code")) == operateur.code_societe:
            reconnus[(operateur.pays, operateur.operateur.lower())] = operateur.code_societe
    for (pays, operateur), code in sorted(reconnus.items()):
        print(f"      {pays}  {operateur[:44]:<46} {code}")
    print(f"   reconnus : {len(reconnus)} / {len(reference.exploitants)}")

    # --- les installations servies ---------------------------------------
    print()
    print("3. les installations servies")
    servies: list[dict[str, str]] = []
    par_pays = reference.par_pays()
    for pays, installations in sorted(par_pays.items()):
        trouvees = 0
        for installation in installations:
            code = installation.code_societe or reconnus.get(
                (pays, installation.operateur.lower()), ""
            )
            if not code:
                continue
            charge = get(
                {
                    "country": pays,
                    "company": code,
                    "facility": installation.code_site,
                    "from": "2026-09-01",
                    "to": "2026-09-02",
                    "size": 128,
                }
            )
            data = charge.get("data") or []
            if data and str(data[0].get("code")) == installation.code_site:
                trouvees += 1
                servies.append(
                    {
                        "pays": pays,
                        "type": installation.type,
                        "operateur": installation.operateur,
                        "site": installation.site,
                        "code_site": installation.code_site,
                        "code_societe": code,
                        "nom": str(data[0].get("name")),
                    }
                )
        if pays in PAYS_CIBLES or trouvees:
            print(f"      {pays}  {trouvees:>3} / {len(installations):>3} installations servies")

    # --- le repli en zone d'exploitant -----------------------------------
    operateurs_seuls = [
        {"pays": pays, "operateur": operateur, "code_societe": code}
        for (pays, operateur), code in sorted(reconnus.items())
        if not any(
            s["pays"] == pays and s["operateur"].lower() == operateur.lower() for s in servies
        )
    ]
    print()
    print(f"4. le repli en zone d'exploitant : {len(operateurs_seuls)} operateurs")

    # --- la couverture des pays cibles -----------------------------------
    print()
    print("5. couverture des pays cibles (stock des sites contre agregat du pays)")
    for pays in PAYS_CIBLES:
        sites = [s for s in servies if s["pays"] == pays]
        operateurs = [o for o in operateurs_seuls if o["pays"] == pays]
        charge = get({"country": pays, "from": "2026-09-01", "to": "2026-09-01", "size": 128})
        data = charge.get("data") or []
        try:
            stock = float(data[0].get("gasInStorage") or 0) * 1000.0 if data else 0.0
        except (TypeError, ValueError):
            stock = 0.0
        couvert = 0.0
        for site in sites:
            charge = get(
                {
                    "country": pays,
                    "company": site["code_societe"],
                    "facility": site["code_site"],
                    "from": "2026-09-01",
                    "to": "2026-09-01",
                    "size": 128,
                }
            )
            data = charge.get("data") or []
            with contextlib.suppress(TypeError, ValueError):
                couvert += float(data[0].get("gasInStorage") or 0) * 1000.0 if data else 0.0
        print(
            f"      {pays}  {len(sites):>3} installation(s) + {len(operateurs):>2} exploitant(s)"
            f"   ·  sites {couvert:>8,.0f} GWh  sur {stock:>8,.0f} GWh d'agregat"
            f"   ({couvert / stock * 100 if stock else 0:>5.1f} % attribue)"
        )

    sortie = RACINE / "data" / "resource-005"
    sortie.mkdir(parents=True, exist_ok=True)
    chemin = sortie / "reference_storage_sites.csv"
    with chemin.open("w", encoding="utf-8", newline="") as fichier:
        redacteur = csv.DictWriter(
            fichier,
            fieldnames=[
                "pays",
                "granularite",
                "code_site",
                "code_societe",
                "site",
                "nom",
                "operateur",
                "type",
            ],
        )
        redacteur.writeheader()
        for ligne in servies:
            redacteur.writerow({**ligne, "granularite": "installation"})
        for ligne in operateurs_seuls:
            redacteur.writerow(
                {
                    "pays": ligne["pays"],
                    "granularite": "exploitant",
                    "code_site": "",
                    "code_societe": ligne["code_societe"],
                    "site": "",
                    "nom": "",
                    "operateur": ligne["operateur"],
                    "type": "SSO",
                }
            )
    print()
    print(f"6. la reference ecrite -> {chemin}")
    print(f"   {len(servies)} installations + {len(operateurs_seuls)} zones d'exploitant")
    print(
        f"   source : {reference.source} · consultee le {dt.datetime.now(dt.UTC).date().isoformat()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
