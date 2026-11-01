"""LNG-003 — la couche stockage au niveau installation, et ses indicateurs.

La mission LNG-002 a etabli que, **au niveau pays**, la couche stockage
n'apportait rien : l'autonomie publiee par GIE est une fonction deterministe
du stock et de la consommation (rapport 0,100 sur dix-neuf pays). Elle
n'est un produit qu'au niveau **installation** — et ce niveau n'existait pas
dans notre produit, alors qu'il pese **vingt-quatre fois** la couche
terminals.

Ce script construit donc la serie quotidienne **par site de stockage**, et en
tire :

1. la **reserve** de chaque site (stock au-dessus du minimum technique) ;
2. la **couverture de soutirage** du pays : combien de jours le pays
   pourrait encore soutirer a son rythme observe — une grandeur que la
   plateforme ne publie pas (elle publie l'autonomie *basee sur la
   consommation*, qui est une autre chose) ;
3. la **repartition** de cette reserve entre les sites, et ce qui n'est
   **pas attribue** ;
4. la **concentration** (par site, par pays) et la **dependance** ;
5. le **scenario de perte** d'un site, sur la couverture du pays.

Trois controles, parce que trois choses peuvent mentir
-------------------------------------------------------

- **L'identifiant.** Un `facility` inconnu retombe **silencieusement** sur
  l'agregat du pays : la reponse porte alors le code du pays, et rien ne le
  signale dans le corps. Le produit compare donc le code recu a celui
  demande, et jette la reponse qui ne correspond pas.
- **L'unite.** Le remplissage publie (`full`, en %) doit etre retrouve par le
  rapport stock / capacite. C'est ce controle qui permet d'affirmer l'unite
  au lieu de la supposer.
- **La somme.** La somme des sites d'un pays doit retrouver l'agregat publie
  pour ce pays. Ce qui manque est la **reserve non attribuee** : elle est
  chiffree, jamais masquee.

Un point de vocabulaire, qui n'est pas un detail
------------------------------------------------

Un site qui ne publie **aucun soutirage** n'a pas une couverture de zero
jour : il n'a **pas de couverture mesurable**. La reponse est `None`, et le
produit le dit. Publier zero pour une cuve **pleine et inactive** dirait
l'inverse de la verite — et c'est le cas reel de plusieurs sites de stockage
europeens au 31 octobre 2026.

Usage :

    uv run python experiments/lng_003_storage_facilities.py 2026-06-01 2026-10-31 data/resource-005
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import os
import pathlib
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request

from torne.acquisition import FileRawStore, HttpTransport
from torne.acquisition.adapters.gie import CREDENTIAL_REF, GieAdapter
from torne.acquisition.credentials import FichierEnvToken
from torne.acquisition.fetcher import Fetcher
from torne.acquisition.references import TABLE_ACER_GIE, lire_reference_stockage
from torne.supply.gas import GasDay
from torne.supply.gie import decoder_agsi
from torne.supply.terminals import (
    SEUIL_TENSION_JOURS,
    STOCK_MINI_FRAC,
    concentration_reserve,
    marge_installation,
    reserve_operationnelle,
    scenario_perte_site,
    serie_par_installation,
)

# Le socle verifie les certificats — il a raison. Mais cette machine n'a aucun
# magasin CA configure pour OpenSSL : on designe celui de `certifi`, qui est
# installe. La verification reste complete.
try:
    import certifi

    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
except ImportError:
    pass

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RACINE = pathlib.Path(r"C:\Users\Romain\Documents\GitHub\torne")
VARIABLE = "AGSI_API_KEY"

PAYS_CIBLES = ["IT", "DE", "FR", "NL", "AT"]
"""Les pays vises en premier : ils portent 74 % du stock souterrain europeen.

L'ordre est celui de l'ampleur : l'Italie 169 TWh, l'Allemagne 132, la France
89, les Pays-Bas 69, l'Autriche 67 — sur 742 TWh au total.
"""

FENETRE_JOURS = 30
"""La fenetre traileresse, en jours de gaz, pour le debit de soutirage moyen."""


def charger_reference():
    """La reference ACER, telechargee et resolue."""
    demande = urllib.request.Request(TABLE_ACER_GIE, headers={"User-Agent": "torne-probe"})
    with urllib.request.urlopen(demande, timeout=120, context=ssl.create_default_context()) as r:
        return lire_reference_stockage(r.read())


FENETRE_FENETRE = 30
"""La fenetre demandee a la plateforme, en jours de gaz.

Une requete large peut renvoyer l'agregat du pays sur sa premiere page --
observe sur Katharina (Allemagne) : le controle d'identite l'ecarte alors, et
215 jours legitimes sont perdus. Une requete courte n'a qu'une page, et le
controle reste net.
"""


def _fenetres(debut: str, fin: str, taille: int = FENETRE_FENETRE) -> list[tuple[str, str]]:
    """Les fenetres a demander, en jours de gaz."""
    premier = dt.date.fromisoformat(debut)
    dernier = dt.date.fromisoformat(fin)
    fenetres: list[tuple[str, str]] = []
    courant = premier
    while courant <= dernier:
        fin_fenetre = min(courant + dt.timedelta(days=taille - 1), dernier)
        fenetres.append((courant.isoformat(), fin_fenetre.isoformat()))
        courant = fin_fenetre + dt.timedelta(days=1)
    return fenetres


SECRET_ASCII = re.compile(r"\b[0-9a-f]{16,}\b", re.IGNORECASE)


def _assainir(texte: str) -> str:
    """Un message de la source, depourvu de tout secret.

    GIE renvoie la cle dans le message d'erreur : rien de ce qui est
    consigne ne doit la contenir.
    """
    return SECRET_ASCII.sub("***", texte)


def _pages(magasin: FileRawStore, issue) -> list[tuple[str, bool]]:
    """Les pages d'une reponse, avec le refus qu'elles portent eventualement."""
    pages: list[tuple[str, bool]] = []
    for preuve in issue.evidence:
        chemin = magasin.content_path(preuve.evidence_id)
        if not chemin.exists():
            continue
        try:
            charge = json.loads(chemin.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        message = ""
        if charge.get("error"):
            message = str(charge.get("message") or charge.get("error"))
        pages.append((message, bool(message)))
    return pages


def _acquerir(
    fetcher: Fetcher,
    magasin: FileRawStore,
    cible: dict[str, str],
    debut: str,
    fin: str,
) -> tuple[list[GasDay], list[str]]:
    """La serie d'une installation, et les reponses refusees.

    `cible` porte le pays, le code d'exploitant et le code d'installation.
    Le controle d'identifiant est fait ici : une reponse dont le code n'est
    pas celui demande **retombe sur l'agregat**, et elle est jetee.
    """
    etats: list[GasDay] = []
    refus: list[str] = []
    adaptateur = GieAdapter(
        debut=debut,
        fin=fin,
        pays=cible["pays"],
        installation=cible.get("code_site") or None,
        company=cible["code_societe"],
        taille=128,
        plateforme="agsi",
    )
    issue = fetcher.acquire(adaptateur)
    # La plateforme refuse par intermittence certaines requetes (un 200 et un
    # corps qui porte la cle). Un refus laisse un trou dans la serie, et le
    # trou bouge d'une execution a l'autre : une fenetre qui contient un
    # refus est donc reprise.
    for _tentative in range(2):
        pages = _pages(magasin, issue)
        if pages and not any(erreur for erreur, _ in pages):
            break
        if _tentative == 0:
            time.sleep(3.0)
            issue = fetcher.acquire(adaptateur)
    refus_fenetre = [
        f"{cible.get('nom') or cible.get('code_site')} : refus de la plateforme — "
        f"{_assainir(erreur)}"
        for erreur, _ in pages
        if erreur
    ]
    refus.extend(refus_fenetre)
    for preuve in issue.evidence:
        chemin = magasin.content_path(preuve.evidence_id)
        if not chemin.exists():
            continue
        try:
            charge = json.loads(chemin.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if charge.get("error"):
            refus.append(
                f"{cible.get('nom') or cible['code_site']} : "
                f"{str(charge.get('message') or charge.get('error'))[:120]}"
            )
            continue
        for element in charge.get("data") or []:
            code = str(element.get("code") or "")
            attendu = cible.get("code_site") or cible["code_societe"]
            if code != attendu:
                # Le filtre a ete ignore : la reponse est celle du pays.
                refus.append(f"{cible.get('nom') or attendu} : la plateforme a repondu pour {code}")
                continue
            etat = decoder_agsi(element, cible["pays"])
            if etat is not None:
                etats.append(etat)
    return etats, refus


def _debit_moyen(suite: list[GasDay], fenetre: int = FENETRE_JOURS) -> float:
    """Le soutirage moyen sur la fenetre traileresse."""
    sorties = [etat.sortie for etat in suite]
    if not sorties:
        return 0.0
    tranche = sorties[-fenetre:]
    return sum(tranche) / len(tranche)


def main(argv: list[str]) -> int:
    """La serie par site, les indicateurs, les controles."""
    debut = argv[1] if len(argv) > 1 else "2026-06-01"
    fin = argv[2] if len(argv) > 2 else "2026-10-31"
    sortie = pathlib.Path(argv[3]) if len(argv) > 3 else RACINE / "data" / "resource-005"
    sortie.mkdir(parents=True, exist_ok=True)
    magasin = FileRawStore(sortie / "preuves")
    transport = HttpTransport(timeout=120.0)
    fournisseur = FichierEnvToken(
        CREDENTIAL_REF,
        variable=VARIABLE,
        chemin=RACINE / ".env",
        header="x-key",
        scheme="",
    )
    fetcher = Fetcher(transport=transport, store=magasin, credentials=fournisseur)

    print("=" * 100)
    print("TORNE · LNG-003 — la couche stockage au niveau installation")
    print(f"fenetre : {debut} -> {fin} · sortie : {sortie}")
    print()

    reference = charger_reference()
    print("1. la reference des installations")
    print(f"   source : {reference.source} · consultee le {reference.consultee_le}")
    par_pays_reference = reference.par_pays()
    cibles: list[dict[str, str]] = []
    for pays in PAYS_CIBLES:
        for installation in par_pays_reference.get(pays, []):
            if installation.code_site and installation.code_societe:
                cibles.append(
                    {
                        "pays": pays,
                        "code_site": installation.code_site,
                        "code_societe": installation.code_societe,
                        "nom": installation.site,
                        "operateur": installation.operateur,
                    }
                )
    print(f"   sites candidats pour {PAYS_CIBLES} : {len(cibles)}")

    # --- l'acquisition ---------------------------------------------------
    etats: list[GasDay] = []
    noms: dict[str, str] = {}
    operateurs: dict[str, str] = {}
    refus: list[str] = []
    for cible in cibles:
        etats_site: list[GasDay] = []
        for debut_f, fin_f in _fenetres(debut, fin):
            etats_fenetre, refus_fenetre = _acquerir(fetcher, magasin, cible, debut_f, fin_f)
            refus.extend(refus_fenetre)
            etats_site.extend(etats_fenetre)
        if not etats_site:
            continue
        noms[cible["code_site"]] = cible["nom"]
        operateurs[cible["code_site"]] = cible["operateur"]
        etats.extend(etats_site)

    if not etats:
        print("   aucune installation servie : le produit ne peut pas etre construit")
        return 1

    series = serie_par_installation(etats)
    print()
    print("2. la serie")
    print(f"   installations servies : {len(series)} / {len(cibles)}")
    print(f"   etats de site lus     : {len(etats)}")
    if refus:
        print(f"   reponses refusees ou hors installation : {len(refus)}")

    # --- les agregats de pays (publies) ----------------------------------
    agregats: dict[str, list[GasDay]] = {}
    for pays in PAYS_CIBLES:
        etats_pays: list[GasDay] = []
        for debut_f, fin_f in _fenetres(debut, fin):
            adaptateur = GieAdapter(
                debut=debut_f, fin=fin_f, pays=pays, taille=128, plateforme="agsi"
            )
            issue = fetcher.acquire(adaptateur)
            if not issue.evidence:
                time.sleep(2.0)
                issue = fetcher.acquire(adaptateur)
            for preuve in issue.evidence:
                chemin = magasin.content_path(preuve.evidence_id)
                if not chemin.exists():
                    continue
                try:
                    charge = json.loads(chemin.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                for element in charge.get("data") or []:
                    etat = decoder_agsi(element, pays)
                    if etat is not None:
                        etats_pays.append(etat)
        etats_pays.sort(key=lambda e: e.jour_gaz)
        if etats_pays:
            agregats[pays] = etats_pays

    # --- les controles ---------------------------------------------------
    print()
    print("3. les controles")
    mauvais = [e for e in etats if e.installation not in noms]
    print(f"   identite : {len(mauvais)} etat(s) hors des codes demandes")
    ecarts_unite = []
    for etat in etats:
        if etat.rempli is None:
            continue
        ecarts_unite.append(abs(etat.taux_remplissage * 100.0 - etat.rempli))
    if ecarts_unite:
        print(
            f"   unite    : ecart maximal entre remplissage calcule et publie : "
            f"{max(ecarts_unite):.3f} point (sur {len(ecarts_unite)} etats)"
        )
    ecarts_unite_pays = []
    for _pays, suite in agregats.items():
        for etat in suite:
            if etat.rempli is None:
                continue
            ecarts_unite_pays.append(abs(etat.taux_remplissage * 100.0 - etat.rempli))
    if ecarts_unite_pays:
        print(
            f"   unite (pays) : ecart maximal {max(ecarts_unite_pays):.3f} point "
            f"(sur {len(ecarts_unite_pays)} etats)"
        )

    # --- le pays : la couverture de soutirage, jour par jour --------------
    # Le soutirage d'un stockage est FORTEMENT saisonnier : l'Italie soutire
    # 0 GWh/j en octobre et 1 148 GWh/j en janvier. Une moyenne sur la
    # fenetre ne veut donc rien dire : la couverture se lit SUR LA SERIE, et
    # ce qui compte est son MINIMUM, le moment ou le systeme est le plus
    # tendu de l'annee.
    print()
    print("4. la couverture de soutirage des pays, et la part qui est attribuee")
    pays_indicateurs: list[dict[str, object]] = []
    couverture_csv: list[dict[str, object]] = []
    for pays in PAYS_CIBLES:
        suite = agregats.get(pays)
        if not suite:
            continue
        series_pays: list[tuple[str, float, float, float, float | None]] = []
        for index, etat in enumerate(suite):
            reserve = reserve_operationnelle(etat.stock, etat.capacite)
            fenetre = [e.sortie for e in suite[max(0, index - FENETRE_JOURS + 1) : index + 1]]
            debit_moyen = sum(fenetre) / len(fenetre) if fenetre else 0.0
            couverture = reserve / debit_moyen if debit_moyen > 0 else None
            series_pays.append(
                (
                    etat.jour_gaz.isoformat(),
                    reserve,
                    etat.sortie,
                    debit_moyen,
                    couverture,
                    etat.rempli,
                    etat.autonomie_publiee,
                )
            )
            couverture_csv.append(
                {
                    "pays": pays,
                    "jour_gaz": etat.jour_gaz.isoformat(),
                    "date_publication": etat.date_publication.isoformat(),
                    "stock_gwh": round(etat.stock, 3),
                    "capacite_utile_gwh": round(etat.capacite, 3),
                    "reserve_gwh": round(reserve, 3),
                    "soutirage_gwh_j": round(etat.sortie, 3),
                    "soutirage_moyen_30j_gwh_j": round(debit_moyen, 3),
                    "couverture_jours": round(couverture, 3) if couverture is not None else "",
                    "autonomie_publiee_jours": (
                        round(etat.autonomie_publiee, 2)
                        if etat.autonomie_publiee is not None
                        else ""
                    ),
                    "remplissage_publie_pct": (
                        round(etat.rempli, 3) if etat.rempli is not None else ""
                    ),
                }
            )
        mesurables = [s for s in series_pays if s[4] is not None]
        if not mesurables:
            continue
        tendu = min(mesurables, key=lambda s: float(s[4]))
        dernier = suite[-1]
        remplissage_tendu = tendu[5]
        autonomie_tendue = tendu[6]
        reserve_pays = float(tendu[1])
        debit_tendu = float(tendu[3])
        couverture_tendue = float(tendu[4])
        stock_tendu = 0.0
        for etat in suite:
            if etat.jour_gaz.isoformat() == tendu[0]:
                stock_tendu = etat.stock
                break
        serie_pays = {code: s for code, s in series.items() if s[0].pays == pays}
        attribue = 0.0
        parts: list[dict[str, object]] = []
        for code, serie_site in serie_pays.items():
            # La part d'un site se mesure AU MEME JOUR que la reserve du
            # pays : la reserve d'un site au 31 octobre et celle du pays le
            # 5 fevrier ne se comparent pas.
            jour_tendu = tendu[0]
            etats_jour = [e for e in serie_site if e.jour_gaz.isoformat() == jour_tendu]
            if etats_jour:
                etat_site = etats_jour[-1]
                retard = 0
            else:
                anterieurs = [e for e in serie_site if e.jour_gaz.isoformat() < jour_tendu]
                if not anterieurs:
                    continue
                etat_site = anterieurs[-1]
                retard = (dt.date.fromisoformat(jour_tendu) - etat_site.jour_gaz).days
            reserve_site = reserve_operationnelle(etat_site.stock, etat_site.capacite)
            attribue += reserve_site
            parts.append(
                {
                    "code_site": code,
                    "nom": noms.get(code, etat_site.nom),
                    "operateur": operateurs.get(code, ""),
                    "jour": etat_site.jour_gaz.isoformat(),
                    "retard_jours": retard,
                    "reserve_gwh": round(reserve_site, 1),
                    "stock_gwh": round(etat_site.stock, 1),
                    "capacite_utile_gwh": round(etat_site.capacite, 1),
                    "remplissage_publie_pct": (
                        round(etat_site.rempli, 2) if etat_site.rempli is not None else None
                    ),
                    "soutirage_gwh_j": round(etat_site.sortie, 2),
                    "part_reserve_pays_pct": (
                        round(reserve_site / reserve_pays * 100, 1) if reserve_pays > 0 else 0.0
                    ),
                }
            )
        non_attribue = reserve_pays - attribue
        pays_indicateurs.append(
            {
                "pays": pays,
                "jour_le_plus_tendu": tendu[0],
                "stock_au_point_tendu_gwh": round(stock_tendu, 1),
                "capacite_utile_gwh": round(dernier.capacite, 1),
                "remplissage_au_point_tendu_pct": (
                    round(remplissage_tendu, 2) if remplissage_tendu is not None else None
                ),
                "reserve_au_point_tendu_gwh": round(reserve_pays, 1),
                "soutirage_au_point_tendu_gwh_j": round(debit_tendu, 2),
                "couverture_au_point_tendu_jours": round(couverture_tendue, 1),
                "autonomie_publiee_au_point_tendu_jours": (
                    round(autonomie_tendue, 2) if autonomie_tendue is not None else None
                ),
                "stock_gwh": round(dernier.stock, 1),
                "autonomie_publiee_jours": (
                    round(dernier.autonomie_publiee, 1)
                    if dernier.autonomie_publiee is not None
                    else None
                ),
                "reserve_attribuee_gwh": round(attribue, 1),
                "reserve_non_attribuee_gwh": round(non_attribue, 1),
                "part_attribuee_pct": (
                    round(attribue / reserve_pays * 100, 1) if reserve_pays > 0 else 0.0
                ),
                "sites": parts,
            }
        )
        print(
            f"   {pays}  point le plus tendu {tendu[0]}  "
            f"remplissage {remplissage_tendu or 0:>5.1f} %  "
            f"couverture {couverture_tendue:>7,.1f} j  "
            f"(autonomie PUBLIEE ce jour-la : {autonomie_tendue or 0:,.2f} j)  "
            f"attribue {attribue / reserve_pays * 100 if reserve_pays else 0:>5.1f} %"
        )

    # --- les sites : leur part de la reserve du pays ----------------------
    print()
    print("5. les sites : la part qu'ils portent de la reserve du pays")
    lignes_csv: list[dict[str, object]] = []
    for code, suite in sorted(series.items()):
        marges = marge_installation(suite, FENETRE_JOURS)
        mesurables = [m for m in marges if m is not None]
        for index, etat in enumerate(suite):
            lignes_csv.append(
                {
                    "code_site": code,
                    "nom": noms.get(code, etat.nom),
                    "operateur": operateurs.get(code, ""),
                    "pays": etat.pays,
                    "jour_gaz": etat.jour_gaz.isoformat(),
                    "date_publication": etat.date_publication.isoformat(),
                    "stock_gwh": round(etat.stock, 3),
                    "capacite_utile_gwh": round(etat.capacite, 3),
                    "reserve_gwh": round(reserve_operationnelle(etat.stock, etat.capacite), 3),
                    "injection_gwh_j": round(etat.entree, 3) if etat.entree is not None else "",
                    "soutirage_gwh_j": round(etat.sortie, 3),
                    "remplissage_publie_pct": (
                        round(etat.rempli, 3) if etat.rempli is not None else ""
                    ),
                    "remplissage_calcule_pct": round(etat.taux_remplissage * 100, 3),
                    "marge_jours_au_soutirage_propre": (
                        round(marges[index], 3) if marges[index] is not None else ""
                    ),
                    "tension": (
                        int(marges[index] < SEUIL_TENSION_JOURS)
                        if marges[index] is not None
                        else ""
                    ),
                }
            )
    for bloc in pays_indicateurs:
        print(f"   {bloc['pays']} :")
        for part in sorted(bloc["sites"], key=lambda p: -float(p["reserve_gwh"])):
            marque = ""
            if float(part["soutirage_gwh_j"]) <= 0:
                marque = "   <<< reserve immobile : la cuve est pleine, et rien ne sort"
            print(
                f"      {str(part['nom'])[:44]:<46} reserve {float(part['reserve_gwh']):>9,.0f} GWh"
                f"  {float(part['part_reserve_pays_pct']):>5.1f} % du pays"
                f"  remplissage {float(part['remplissage_publie_pct'] or 0):>5.1f} %"
                f"  soutirage {float(part['soutirage_gwh_j']):>7,.1f} GWh/j{marque}"
            )

    # --- la concentration -------------------------------------------------
    print()
    print("6. la concentration de la reserve attribuee")
    concentration = concentration_reserve({code: suite[-1] for code, suite in series.items()})
    print(f"   Herfindahl (installations) : {concentration['herfindahl']:.4f}")
    print(f"   part du premier site       : {concentration['part_premier'] * 100:.1f} %")
    print(f"   part des trois premiers     : {concentration['part_trois'] * 100:.1f} %")
    print(f"   reserve attribuee totale   : {concentration['total_gwh']:,.0f} GWh")
    parts_globales: list[dict[str, object]] = []
    for bloc in pays_indicateurs:
        for part in sorted(bloc["sites"], key=lambda p: -float(p["reserve_gwh"])):
            parts_globales.append(
                {
                    "pays": bloc["pays"],
                    "nom": part["nom"],
                    "reserve_gwh": part["reserve_gwh"],
                    "part_pays_pct": part["part_reserve_pays_pct"],
                }
            )
    parts_globales.sort(key=lambda p: -float(p["reserve_gwh"]))
    print("   les trois plus gros sites de la reserve attribuee :")
    for part in parts_globales[:3]:
        print(
            f"      {part['pays']}  {str(part['nom'])[:42]:<44} "
            f"{float(part['reserve_gwh']):>9,.0f} GWh  "
            f"({float(part['part_pays_pct']):>4.1f} % de la reserve du pays)"
        )

    # --- le scenario ------------------------------------------------------
    print()
    print("7. le scenario : la perte d'un site, sur la couverture du pays")
    scenarios: list[dict[str, object]] = []
    for bloc in pays_indicateurs:
        # Le scenario se joue au POINT LE PLUS TENDU de l'annee : c'est la
        # que le soutirage est eleve, et c'est la que la perte d'un site
        # ferait mal. L'evaluer au rythme d'ete ne dirait rien.
        reserve_pays = float(bloc["reserve_au_point_tendu_gwh"])
        debit_pays = float(bloc["soutirage_au_point_tendu_gwh_j"])
        for part in bloc["sites"]:
            resultat = scenario_perte_site(reserve_pays, float(part["reserve_gwh"]), debit_pays)
            if resultat is None:
                continue
            scenarios.append(
                {
                    "pays": bloc["pays"],
                    "site": part["nom"],
                    "code_site": part["code_site"],
                    **resultat,
                }
            )
    for resultat in sorted(scenarios, key=lambda r: -float(r["jours_perdus"]))[:10]:
        print(
            f"   {resultat['pays']}  perte de {str(resultat['site'])[:38]:<40} -> "
            f"{float(resultat['couverture_apres_jours']):>7.1f} j "
            f"(-{float(resultat['jours_perdus']):>5.1f} j, "
            f"{float(resultat['part_reserve_perdue']) * 100:>4.1f} % de la reserve)"
        )

    # --- les sorties ------------------------------------------------------
    chemin_couverture = sortie / "europe_storage_coverage.csv"
    with chemin_couverture.open("w", encoding="utf-8", newline="") as fichier:
        redacteur = csv.DictWriter(fichier, fieldnames=list(couverture_csv[0].keys()))
        redacteur.writeheader()
        redacteur.writerows(couverture_csv)
    chemin_serie = sortie / "europe_storage_sites.csv"
    with chemin_serie.open("w", encoding="utf-8", newline="") as fichier:
        redacteur = csv.DictWriter(fichier, fieldnames=list(lignes_csv[0].keys()))
        redacteur.writeheader()
        redacteur.writerows(lignes_csv)
    indicateurs = {
        "produit": "TORNE · LNG-003 — European Storage Facility Intelligence",
        "genere_le": dt.datetime.now(dt.UTC).isoformat(),
        "fenetre": {"debut": debut, "fin": fin},
        "sources": [
            {
                "source_id": "gie.agsi",
                "producteur": "Gas Infrastructure Europe (GIE)",
                "dataset": "AGSI+ Transparency Platform",
                "unites": "stock et capacite utile en TWh (convertis en GWh) ; flux en GWh/jour",
                "acces": "https://agsi.gie.eu/api (en-tete x-key)",
            },
            {
                "source_id": "gie.acer_eic_mapping",
                "producteur": "GIE",
                "dataset": "ACER EIC CODE MAPPING TABLE",
                "role": "reference d'identifiants (codes d'exploitant et d'installation)",
                "url": TABLE_ACER_GIE,
                "source": reference.source,
                "consultee_le": reference.consultee_le,
            },
        ],
        "pays": PAYS_CIBLES,
        "installations_servies": len(series),
        "etats": len(etats),
        "minimum_technique_frac": STOCK_MINI_FRAC,
        "fenetre_jours": FENETRE_JOURS,
        "seuil_tension_jours": SEUIL_TENSION_JOURS,
        "concentration": concentration,
        "pays_indicateurs": pays_indicateurs,
        "scenarios_perte": sorted(scenarios, key=lambda r: -float(r["jours_perdus"]))[:15],
        "refus": refus[:50],
    }
    chemin_indicateurs = sortie / "storage_indicators.json"
    chemin_indicateurs.write_text(
        json.dumps(indicateurs, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print()
    print("8. les sorties")
    print(f"   couverture pays : {len(couverture_csv)} lignes -> {chemin_couverture}")
    print(f"   serie par site  : {len(lignes_csv)} lignes -> {chemin_serie}")
    print(f"   indicateurs    : {chemin_indicateurs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
