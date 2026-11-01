"""LNG-002 — la couche terminals europeenne, et la confrontation avec l'exploitant.

La mission a etabli qu'au niveau **pays**, la grandeur reconstruite etait
deja publiee par GIE : l'autonomie publiee est une fonction deterministe du
stock et de la consommation. Le terrain restant est le niveau
**installation** : l'autonomie publiee est un agregat national, elle ne dit
pas quelle installation est tendue.

Ce script construit donc la serie quotidienne **par terminal** sur toute
l'Europe (ALSI), puis :

1. il en tire la **concentration** et la **dependance** — la reserve
   europeenne est-elle portee par un petit nombre d'installations ? ;
2. il **derive le dechargement** des cargaisons, que la source ne publie pas,
   mais que l'equation du stock rend lisible ;
3. il simule la **perte** d'une installation : que reste-t-il ? ;
4. il **confronte** les terminals espagnols au rapport quotidien de
   l'exploitant (Enagas) — deux sources independantes, les memes
   installations, les memes jours. C'est la porte de validation physique,
   enfin ouverte au bon niveau.

Ce que la confrontation mesure
------------------------------

Les deux sources ne publient pas les memes grandeurs : l'exploitant donne le
stock en **GWh** et en **m3 liquides**, GIE donne le stock en **GWh** et en
**milliers de m3**. La confrontation se fait donc **sur le GWh publie de
chaque source**, sans conversion de la part de TORNE : c'est la seule
comparaison qui ne depende pas d'un facteur que l'on aurait construit. Les
volumes (m3) sont compares a titre de controle, et les debits sortants
(ALSI `sendOut` contre Enagas `regasificationGWh`) a titre de coherence.

L'alignement des jours de gaz est **mesure**, pas suppose : le script essaie
les decalages possibles et retient celui qui minimise l'ecart. Ce decalage
lui-meme est un resultat : il dit si les deux sources decrivent la meme
fenetre de temps.

Usage :

    uv run python experiments/lng_002_lng_terminals.py [debut] [fin] [sortie]
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

# Le socle verifie les certificats — il a raison. Mais cette machine n'a
# aucun magasin CA configure pour OpenSSL, et la verification echoue donc sur
# *toute* source HTTPS. Le remede est d'indiquer le magasin de `certifi`, qui
# est installe : la verification reste **complete**, on ne desactive rien.
try:  # pragma: no cover - dependance d'environnement
    import certifi

    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
except ImportError:  # pragma: no cover
    pass

from torne.acquisition import FileRawStore, HttpTransport
from torne.acquisition.adapters.enagas import EnagasDailyAdapter
from torne.acquisition.adapters.gie import CREDENTIAL_REF, GieAdapter
from torne.acquisition.credentials import FichierEnvToken
from torne.acquisition.fetcher import Fetcher
from torne.supply.enagas import decoder_json
from torne.supply.gas import GasDay
from torne.supply.gie import decoder_alsi
from torne.supply.terminals import (
    SEUIL_TENSION_JOURS,
    concentration_geographique,
    concentration_reserve,
    couverture_systeme,
    dechargement_derive,
    degradation_installation,
    dependance_pays,
    etats_reference,
    jours_en_tension,
    marge_installation,
    scenario_perte,
    serie_par_installation,
)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
"""La sortie doit porter l'ecriture des caracteres accentues, sans quoi la
sortie du script serait illisible sur une console Windows."""

RACINE = Path(__file__).resolve().parent.parent
"""La racine du depot, ou se trouve le `.env` ignore par git."""

VARIABLE = "AGSI_API_KEY"
"""La variable d'environnement qui porte la cle GIE."""

REFERENCE_EC = (
    "https://raw.githubusercontent.com/ec-jrc/eurogastp/main/src/eurogastp/topo/Dataproviders.csv"
)
"""La liste des installations LNG de l'Europe, avec leurs codes EIC.

C'est une **reference d'identifiants** : elle dit quelle installation a
quel code EIC et quel code d'exploitant. Les **donnees** viennent de GIE, par
l'API ALSI. La liste est publique (Commission europeenne, projet eurogastp) ;
sa provenance est consignee dans les sorties.
"""

FENETRE_JOURS = 30
"""La fenetre traileresse, en jours de gaz, pour le debit de sortie moyen."""

IGNORES = {
    "PRIOR_MUS_000001": "identifiant anterieur du Musel, remplace par 21W0000000000346",
    "18W000000000GVMT": "cuve virtuelle de équilibrage (TVB) : pas d'installation physique",
}
"""Les codes de la reference EC qu'on ne traite pas, et pourquoi."""

CORRESPONDANCE_ENAGAS = {
    "BARCELONA": "21W000000000039X",
    "CARTAGENA": "21W000000000038Z",
    "BBG": "21W0000000000362",
    "HUELVA": "21W0000000000370",
    "SAGUNTO": "21W0000000000354",
    "MUSEL": "21W0000000000346",
    "REGANOSA": "21W0000000000338",
}
"""Le nom de terminal chez l'exploitant, et le code EIC du meme terminal chez
GIE. Les noms ne se ressemblent pas (`REGANOSA` et `Mugardos` designent la
meme installation ; l'exploitant ecrit `BBG` pour Bilbao) : c'est la
correspondance qu'il faut, et elle est ecrite, pas devinee."""

DECALAGES = (-2, -1, 0, 1, 2)
"""Les decalages de jour de gaz testes pour la confrontation."""

SECRET_ASCII = re.compile(r"\b[0-9a-f]{16,}\b", re.IGNORECASE)


def _assainir(texte: str) -> str:
    """Un message de la source, depourvu de tout secret.

    GIE renvoie la cle dans le message d'erreur : rien de ce qui est
    consigne ne doit la contenir.
    """
    return SECRET_ASCII.sub("***", texte)


def _fournisseur() -> FichierEnvToken:
    """Le fournisseur de secret : environnement d'abord, `.env` ensuite."""
    return FichierEnvToken(
        CREDENTIAL_REF,
        variable=VARIABLE,
        chemin=RACINE / ".env",
        header="x-key",
        scheme="",
    )


def _terminaux() -> list[dict[str, str]]:
    """Les installations LNG, lues dans la reference publique de la Commission.

    La reference fournit, pour chaque installation, le pays, le code EIC et
    le code d'exploitant — les trois parametres que la plateforme ALSI exige
    pour distinguer un terminal d'un agregat national.
    """
    with urllib.request.urlopen(REFERENCE_EC, timeout=60) as reponse:
        texte = reponse.read().decode("utf-8", "replace")
    lignes = list(csv.reader(io.StringIO(texte), delimiter=";"))
    entete = lignes[0]
    i_pays = entete.index("Country")
    i_type = entete.index("Type")
    i_eic = entete.index("EIC Code")
    i_url = entete.index("URL")
    i_nom = entete.index("Name")
    installations: list[dict[str, str]] = []
    vus: set[tuple[str, str]] = set()
    for ligne in lignes[1:]:
        if len(ligne) <= i_nom or ligne[i_type] != "LNG Terminal":
            continue
        eic = ligne[i_eic].strip()
        if eic in IGNORES:
            continue
        pays = ligne[i_pays].strip()
        # Les pays suffixes d'un astérisque sont les memes installations, vues
        # par GIE dans une autre numerotation (post-Brexit) : les garder deux
        # fois compterait la meme cuve deux fois.
        cle = (pays.rstrip("*"), eic)
        if cle in vus:
            continue
        vus.add(cle)
        installations.append(
            {
                "pays": pays,
                "eic": eic,
                "company": _company(ligne[i_url]),
                "nom_reference": ligne[i_nom].strip(),
            }
        )
    return installations


def _company(url: str) -> str:
    """Le code d'exploitant, tire de l'URL de reference."""
    trouve = re.search(r"company=([0-9A-Za-z\-*]+)", url)
    return trouve.group(1) if trouve else ""


def _fenetres(debut: str, fin: str, taille: int = FENETRE_JOURS) -> list[tuple[str, str]]:
    """Les fenetres demandees a la plateforme, decoupees pour la pagination."""
    premier = dt.date.fromisoformat(debut)
    dernier = dt.date.fromisoformat(fin)
    fenetres: list[tuple[str, str]] = []
    courant = premier
    while courant <= dernier:
        fin_fenetre = min(courant + dt.timedelta(days=taille - 1), dernier)
        fenetres.append((courant.isoformat(), fin_fenetre.isoformat()))
        courant = fin_fenetre + dt.timedelta(days=1)
    return fenetres


def _premier_mois(debut: str, fin: str) -> tuple[str, str]:
    """Le premier mois plein de la fenetre : celui de la confrontation."""
    premier = dt.date.fromisoformat(debut)
    dernier = dt.date.fromisoformat(fin)
    debut_mois = premier.replace(day=1)
    fin_mois = dt.date(
        debut_mois.year + (debut_mois.month == 12),
        1 if debut_mois.month == 12 else debut_mois.month + 1,
        1,
    )
    fin_mois = min(fin_mois - dt.timedelta(days=1), dernier)
    return debut_mois.isoformat(), fin_mois.isoformat()


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


def _acquerir_alsi(
    fetcher: Fetcher,
    magasin: FileRawStore,
    installations: list[dict[str, str]],
    debut: str,
    fin: str,
) -> tuple[list[GasDay], dict[tuple[str, str], dict], list[str]]:
    """La serie ALSI, installation par installation.

    Rend les etats traduits, les elements bruts (pour la confrontation, qui
    compare les grandeurs publiees, non une traduction), les refus, et le
    **statut** de chaque installation.

    Le statut est le champ `status` de la plateforme : `C` quand l'installation
    publie ses valeurs, `N` quand elle ne publie qu'un enregistrement vide
    (tous les champs a `-`). Une installation sans donnee n'est pas une
    installation qui n'existe pas : elle doit etre comptee comme telle.
    """
    etats: list[GasDay] = []
    bruts: dict[tuple[str, str], dict] = {}
    refus: list[str] = []
    statuts: dict[str, str] = {}
    for installation in installations:
        for debut_f, fin_f in _fenetres(debut, fin):
            adaptateur = GieAdapter(
                debut=debut_f,
                fin=fin_f,
                pays=installation["pays"],
                installation=installation["eic"],
                company=installation["company"],
                taille=128,
                plateforme="alsi",
            )
            issue = fetcher.acquire(adaptateur)
            # La plateforme refuse par intermittence certaines requetes (un
            # 200 et un corps qui porte la cle). Un refus laisse un trou
            # dans la serie, et le trou bouge d'une execution a l'autre :
            # une fenetre qui contient un refus est donc reprise.
            for _tentative in range(2):
                pages = _pages(magasin, issue)
                if pages and not any(erreur for erreur, _ in pages):
                    break
                if _tentative == 0:
                    time.sleep(3.0)
                    issue = fetcher.acquire(adaptateur)
            refus.extend(
                f"{installation['eic']} : refus de la plateforme — {_assainir(erreur)}"
                for erreur, _ in pages
                if erreur
            )
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
                        f"{installation['eic']} : refus de la plateforme — "
                        f"{_assainir(str(charge.get('message') or charge.get('error')))}"
                    )
                    continue
                for element in charge.get("data") or []:
                    code = str(element.get("code") or "")
                    jour = str(element.get("gasDayStart") or "")
                    # Un filtre ignore retombe sur l'agregat du pays : il faut
                    # le voir, sinon on croit avoir la serie d'un terminal.
                    if code != installation["eic"]:
                        refus.append(f"{installation['eic']} : la plateforme a repondu pour {code}")
                        continue
                    statuts[code] = str(element.get("status") or "")
                    bruts[(code, jour)] = element
                    etat = decoder_alsi(element, installation["pays"])
                    if etat is not None:
                        etats.append(etat)
    return etats, bruts, refus, statuts


def _agregats_pays(
    fetcher: Fetcher,
    magasin: FileRawStore,
    pays: list[str],
    debut: str,
    fin: str,
    installations: list[dict[str, str]],
    operateurs: list[str] | None = None,
) -> dict[tuple[str, str], dict]:
    """Les agregats publies, pour le controle de somme.

    C'est le meme controle que celui du produit espagnol (`Total Plantas`) :
    la somme des terminaux d'un pays doit retrouver l'agregat que la
    plateforme publie pour ce pays. S'il manque un terminal, l'ecart le dit.

    La meme question se pose au niveau de l'**exploitant** : la plateforme
    publie aussi un agregat par operateur, et la somme de ses installations
    doit le retrouver. C'est ce second controle qui localise un manque.
    """
    agregats: dict[tuple[str, str], dict] = {}
    for code_pays in pays:
        adaptateur = GieAdapter(
            debut=debut,
            fin=fin,
            pays=code_pays,
            taille=128,
            plateforme="alsi",
        )
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
                jour = str(element.get("gasDayStart") or "")
                agregats[(code_pays, jour)] = element
    for operateur in operateurs or []:
        pays_operateur = _pays_de_l_operateur(operateur, installations)
        if not pays_operateur:
            continue
        adaptateur = GieAdapter(
            debut=debut,
            fin=fin,
            pays=pays_operateur,
            company=operateur,
            taille=128,
            plateforme="alsi",
        )
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
                jour = str(element.get("gasDayStart") or "")
                agregats[(operateur, jour)] = element
    return agregats


INSTALLATIONS_PAYS: dict[str, str] = {}
"""Le pays de chaque code d'exploitant, deduit de la reference."""


def _pays_de_l_operateur(operateur: str, reference: list[dict[str, str]]) -> str:
    """Le pays d'un exploitant, d'apres la reference des installations."""
    for installation in reference:
        if installation["company"] == operateur:
            return installation["pays"]
    return ""


def _acquerir_enagas(
    fetcher: Fetcher,
    magasin: FileRawStore,
    debut: str,
    fin: str,
) -> tuple[dict[str, dict[str, object]], list[str]]:
    """Les rapports quotidiens de l'exploitant espagnol.

    Rend, par terminal et par jour de gaz, l'etat tel que l'exploitant le
    publie — en GWh **et** en m3 — et la liste des rapports illisibles.
    """
    par_jour: dict[str, dict[str, object]] = {}
    refus: list[str] = []
    courant = dt.date.fromisoformat(debut)
    dernier = dt.date.fromisoformat(fin)
    while courant <= dernier:
        adaptateur = EnagasDailyAdapter(courant)
        issue = fetcher.acquire(adaptateur)
        lu = False
        for preuve in issue.evidence:
            chemin = magasin.content_path(preuve.evidence_id)
            if not chemin.exists():
                continue
            try:
                charge = json.loads(chemin.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            lu = True
            par_jour[courant.isoformat()] = charge
        if not lu:
            refus.append(courant.isoformat())
        courant += dt.timedelta(days=1)
    return par_jour, refus


def _main(argv: list[str]) -> int:
    """La serie par terminal, les indicateurs, le scenario, et la confrontation."""
    debut = argv[1] if len(argv) > 1 else "2026-06-01"
    fin = argv[2] if len(argv) > 2 else "2026-10-31"
    sortie = Path(argv[3]) if len(argv) > 3 else RACINE / "data" / "resource-004"
    sortie.mkdir(parents=True, exist_ok=True)
    magasin_alsi = FileRawStore(sortie / "preuves_terminals")
    magasin_enagas = FileRawStore(sortie / "preuves_enagas")
    transport = HttpTransport(timeout=120.0)
    fournisseur = _fournisseur()
    tete = fournisseur.credentials_for(CREDENTIAL_REF)
    fetcher_alsi = Fetcher(transport=transport, store=magasin_alsi, credentials=fournisseur)
    fetcher_enagas = Fetcher(transport=transport, store=magasin_enagas, credentials=fournisseur)

    print("=" * 100)
    print("TORNE · LNG-002 — la couche terminals europeenne")
    print(
        f"cle GIE : {'presente (variable ' + VARIABLE + '), jamais ecrite' if tete else 'ABSENTE'}"
    )
    print(f"fenetre : {debut} -> {fin} · sortie : {sortie}")
    print()

    installations = _terminaux()
    print("1. la reference des installations (Commission europeenne, eurogastp)")
    print(f"   installations retenues : {len(installations)}")
    print(f"   ignores et pourquoi     : {len(IGNORES)}")
    for code, motif in IGNORES.items():
        print(f"      {code} : {motif}")

    etats, bruts, refus_alsi, statuts = _acquerir_alsi(
        fetcher_alsi, magasin_alsi, installations, debut, fin
    )
    series = serie_par_installation(etats)
    print()
    print("2. la serie ALSI")
    print(f"   etats de terminal lus : {len(etats)}")
    print(f"   installations couvertes : {len(series)} / {len(installations)}")
    sans_donnee = sorted(code for code in statuts if code not in series)
    if sans_donnee:
        print(f"   installations listees mais sans valeur publiee (statut N) : {len(sans_donnee)}")
        for code in sans_donnee:
            nom = next(
                (i["nom_reference"] for i in installations if i["eic"] == code),
                code,
            )
            print(f"      {code} : {nom[:44]}")
    if refus_alsi:
        print(f"   refus ou reponses hors installation : {len(refus_alsi)}")
        for ligne in refus_alsi[:5]:
            print(f"      {ligne}")

    if not etats:
        print("   aucune donnee exploitable : le produit ne peut pas etre construit")
        return 1

    reference, etats_ref, fraicheur = etats_reference(series)
    print(f"   date de reference : {reference.isoformat()}")
    ages = sorted(fraicheur.values())
    print(f"   fraicheur des donnees : {ages[0]} a {ages[-1]} jours")

    # -- les indicateurs par installation --------------------------------
    couverture: dict[str, float] = {}
    print()
    print("3. la couverture par installation (reserve / debit de sortie observe)")
    lignes_csv: list[dict[str, object]] = []
    resumes: list[tuple[str, float, int, float, float, float]] = []
    for code, suite in series.items():
        marges = marge_installation(suite, FENETRE_JOURS)
        dechargements = dechargement_derive(suite)
        etat = suite[-1]
        tension = jours_en_tension(marges, SEUIL_TENSION_JOURS)
        pente = degradation_installation(suite, FENETRE_JOURS) or 0.0
        couverture[code] = marges[-1] if marges else 0.0
        derive_total = sum(v for v in dechargements if v is not None)
        resumes.append((code, couverture[code], tension, pente, derive_total, etat.stock))
        for index, jour in enumerate(suite):
            lignes_csv.append(
                {
                    "terminal_eic": code,
                    "nom": jour.nom,
                    "pays": jour.pays,
                    "jour_gaz": jour.jour_gaz.isoformat(),
                    "date_publication": jour.date_publication.isoformat(),
                    "stock_gwh": round(jour.stock, 3),
                    "capacite_gwh": round(jour.capacite, 3),
                    "sortie_gwh_j": round(jour.sortie, 3),
                    # Une installation qui ne sort rien n'a pas de couverture
                    # mesurable : elle n'a pas une couverture de zero jour.
                    "marge_jours": (round(marges[index], 3) if marges[index] is not None else ""),
                    "tension": (
                        int(marges[index] < SEUIL_TENSION_JOURS)
                        if marges[index] is not None
                        else ""
                    ),
                    # L'entree derivee dans les cuves : cargaisons ET
                    # transferts par gazoduc, moins les sorties par camion et
                    # par navire que la plateforme ne publie pas. Ce n'est
                    # donc pas un flux d'importation : c'est une entree nette.
                    "entree_derivee_gwh": (
                        round(dechargements[index], 3) if dechargements[index] is not None else ""
                    ),
                    "latitude": jour.latitude if jour.latitude is not None else "",
                    "longitude": jour.longitude if jour.longitude is not None else "",
                }
            )
    for code, marge, tension, pente, derive_total, _stock in sorted(resumes, key=lambda r: r[1]):
        nom = next((e.nom for e in etats if e.installation == code), code)
        marque = "  <<< TENDUE" if tension else ""
        print(
            f"   {nom[:34]:<36} {marge if marge is not None else float('nan'):>7.1f} j  "
            f"tension {tension:>3} j  "
            f"pente {pente:+.3f} j/j  decharge {derive_total:>9,.0f} GWh{marque}"
        )

    # -- la concentration et la dependance -------------------------------
    concentration = concentration_reserve(etats_ref)
    par_pays = dependance_pays(etats_ref)
    geo = concentration_geographique(par_pays)
    print()
    print("4. la concentration de la reserve LNG europeenne")
    print(f"   Herfindahl (installations) : {concentration['herfindahl']:.4f}")
    print(f"   part du premier terminal   : {concentration['part_premier'] * 100:.1f} %")
    print(f"   part des trois premiers    : {concentration['part_trois'] * 100:.1f} %")
    print(f"   Herfindahl (par pays)      : {geo:.4f}")
    print(f"   reserve totale             : {concentration['total_gwh']:,.0f} GWh")
    print()
    print("   la dependance par pays :")
    for pays, bloc in sorted(par_pays.items(), key=lambda p: -p[1]["part_stock"]):
        print(
            f"      {pays:<4} {bloc['terminaux']:>4.0f} terminal(aux)  "
            f"stock {bloc['part_stock'] * 100:>5.1f} %  "
            f"capacite {bloc['part_capacite'] * 100:>5.1f} %  "
            f"debit {bloc['part_sortie'] * 100:>5.1f} %"
        )

    # -- le controle : la somme des terminaux contre l'agregat publie ------
    print()
    print("5. le controle : la somme des terminaux contre l'agregat du pays")
    pays_couverts = sorted({etat.pays for etat in etats_ref.values()})
    agregats = _agregats_pays(fetcher_alsi, magasin_alsi, pays_couverts, debut, fin, installations)
    controles_somme: list[tuple[str, float, float, int]] = []
    for pays in pays_couverts:
        jours_agregat = sorted(jour for (code_pays, jour) in agregats if code_pays == pays)
        if not jours_agregat:
            continue
        # On compare au **dernier** jour publie par l'agregat : c'est le seul
        # jour ou la comparaison des deux series a un sens.
        jour_agregat = jours_agregat[-1]
        element = agregats[(pays, jour_agregat)]
        try:
            stock_agregat = float(element.get("inventory", {}).get("gwh"))
        except (TypeError, ValueError):
            continue
        somme = 0.0
        comptes = 0
        for suite in series.values():
            if suite[-1].pays != pays:
                continue
            elegibles = [e for e in suite if e.jour_gaz.isoformat() == jour_agregat]
            if not elegibles:
                continue
            somme += elegibles[-1].stock
            comptes += 1
        if stock_agregat > 0:
            controles_somme.append((pays, somme, stock_agregat, comptes))
    for pays, somme, agregat, comptes in controles_somme:
        ecart = (somme - agregat) / agregat * 100
        marque = "" if abs(ecart) < 2.0 else "   <<< RESERVE NON ATTRIBUEE"
        print(
            f"      {pays:<4} somme des {comptes} terminaux {somme:>10,.0f} GWh  "
            f"agregat publie {agregat:>10,.0f} GWh  ecart {ecart:>+6.2f} %{marque}"
        )
    if controles_somme:
        ecarts_somme = [abs(s - a) / a for _, s, a, _ in controles_somme if a]
        print(
            f"   ecart relatif maximal sur {len(ecarts_somme)} pays : "
            f"{max(ecarts_somme) * 100:.2f} %"
        )

    # -- le meme controle, au niveau de l'exploitant ------------------------
    operateurs = sorted({i["company"] for i in installations if i["company"]})
    agregats_operateur = _agregats_pays(
        fetcher_alsi, magasin_alsi, [], debut, fin, installations, operateurs=operateurs
    )
    controles_operateur: list[tuple[str, float, float, int]] = []
    for operateur in operateurs:
        jours = sorted(jour for (code, jour) in agregats_operateur if code == operateur)
        if not jours:
            continue
        jour_operateur = jours[-1]
        element = agregats_operateur[(operateur, jour_operateur)]
        try:
            stock_operateur = float(element.get("inventory", {}).get("gwh"))
        except (TypeError, ValueError):
            continue
        somme = 0.0
        comptes = 0
        for installation in installations:
            if installation["company"] != operateur:
                continue
            suite = series.get(installation["eic"])
            if not suite:
                continue
            elegibles = [e for e in suite if e.jour_gaz.isoformat() == jour_operateur]
            if not elegibles:
                continue
            somme += elegibles[-1].stock
            comptes += 1
        if stock_operateur > 0:
            controles_operateur.append((operateur, somme, stock_operateur, comptes))
    ecarts_operateur = [
        (op, s, a, n) for op, s, a, n in controles_operateur if abs(s - a) / a > 0.02
    ]
    if ecarts_operateur:
        print("   le manque est localise a l'exploitant :")
        for operateur, somme, agregat, comptes in sorted(
            ecarts_operateur, key=lambda r: -abs(r[1] - r[2])
        ):
            print(
                f"      {operateur:<20} somme des {comptes} terminaux {somme:>9,.0f} GWh  "
                f"agregat de l'exploitant {agregat:>9,.0f} GWh  "
                f"non attribue {agregat - somme:>8,.0f} GWh"
            )

    # -- le scenario : la perte d'une installation ------------------------
    reserve, debit, couverture_system = couverture_systeme(series, FENETRE_JOURS)
    print()
    print("6. le scenario : la perte d'une installation")
    print(
        f"   le systeme europeen : {reserve:,.0f} GWh de reserve, "
        f"{debit:,.0f} GWh/j de sortie, soit {couverture_system:,.1f} jours de couverture"
    )
    scenarios: list[dict[str, float]] = []
    for code in series:
        resultat = scenario_perte(series, code, FENETRE_JOURS)
        if resultat is not None:
            scenarios.append(resultat)
    for resultat in sorted(scenarios, key=lambda r: -r["jours_perdus"])[:6]:
        nom = next((e.nom for e in etats if e.installation == resultat["installation"]), "")
        print(
            f"   perte de {nom[:34]:<36} -> {resultat['couverture_apres_jours']:>7.1f} j "
            f"(-{resultat['jours_perdus']:>6.1f} j, "
            f"{resultat['part_reserve_perdue'] * 100:>4.1f} % de la reserve)"
        )

    # -- la confrontation avec l'exploitant espagnol -----------------------
    print()
    print("7. la confrontation physique : GIE (ALSI) contre l'exploitant (Enagas)")
    debut_mois, fin_mois = _premier_mois(debut, fin)
    print(f"   periode de confrontation : {debut_mois} -> {fin_mois}")
    rapports, refus_enagas = _acquerir_enagas(fetcher_enagas, magasin_enagas, debut_mois, fin_mois)
    jours_attendus = (dt.date.fromisoformat(fin_mois) - dt.date.fromisoformat(debut_mois)).days + 1
    print(f"   rapports de l'exploitant lus : {len(rapports)} / {jours_attendus}")
    if refus_enagas:
        print(f"   rapports illisibles : {len(refus_enagas)}")

    enagas: dict[tuple[str, str], dict[str, float]] = {}
    for jour, charge in rapports.items():
        lecture = decoder_json(charge, dt.date.fromisoformat(jour))
        if lecture is None:
            continue
        for etat in lecture.terminaux:
            enagas[(etat.terminal, jour)] = {
                "stock_gwh": etat.stock_final_gwh,
                "stock_m3": etat.stock_final_m3,
                "stock_t": etat.stock_final_t,
                "regas_gwh": etat.regas_gwh,
                "citernes_gwh": etat.sorties_citernes_gwh,
                "reexport_gwh": etat.reexport_m3 / lecture.facteur_m3_par_gwh,
                "remplissage": etat.remplissage,
                # Le dechargement publie par l'exploitant, converti avec le
                # facteur mesure par le produit espagnol.
                "decharge_gwh": etat.entrees_m3 / lecture.facteur_m3_par_gwh,
            }

    # L'alignement des jours de gaz est mesure : on essaie les decalages.
    trouves = {terminal for terminal, _ in enagas}
    absents = sorted(set(CORRESPONDANCE_ENAGAS) - trouves)
    if absents:
        print(f"   terminaux de la correspondance absents du rapport : {absents}")
    meilleur: tuple[float, int, list[dict[str, object]]] | None = None
    for decalage in DECALAGES:
        ecarts: list[dict[str, object]] = []
        for terminal_enagas, eic in CORRESPONDANCE_ENAGAS.items():
            for (code, jour), element in bruts.items():
                if code != eic:
                    continue
                cible = (dt.date.fromisoformat(jour) + dt.timedelta(days=decalage)).isoformat()
                reference_enagas = enagas.get((terminal_enagas, cible))
                if reference_enagas is None:
                    continue
                stock_alsi = float(element["inventory"]["gwh"])
                ecarts.append(
                    {
                        "terminal_enagas": terminal_enagas,
                        "terminal_eic": eic,
                        "jour_alsi": jour,
                        "jour_enagas": cible,
                        "stock_alsi_gwh": stock_alsi,
                        "stock_enagas_gwh": reference_enagas["stock_gwh"],
                        "ecart_abs_gwh": abs(stock_alsi - reference_enagas["stock_gwh"]),
                        "ecart_rel": (
                            abs(stock_alsi - reference_enagas["stock_gwh"])
                            / reference_enagas["stock_gwh"]
                            if reference_enagas["stock_gwh"]
                            else 0.0
                        ),
                    }
                )
        if not ecarts:
            continue
        mediane = sorted(e["ecart_rel"] for e in ecarts)[len(ecarts) // 2]
        if meilleur is None or mediane < meilleur[0]:
            meilleur = (mediane, decalage, ecarts)

    if meilleur is None:
        print("   aucune comparaison possible sur la periode")
    else:
        mediane, decalage, ecarts = meilleur
        print(
            f"   alignement mesure : ALSI jour D = Enagas jour D{decalage:+d} "
            f"(ecart relatif median {mediane * 100:.2f} %)"
        )
        par_terminal: dict[str, list[float]] = {}
        for ecart in ecarts:
            par_terminal.setdefault(str(ecart["terminal_enagas"]), []).append(
                float(ecart["ecart_rel"])
            )
        print("   ecart relatif sur le stock, par terminal :")
        for terminal, valeurs in sorted(par_terminal.items()):
            triees = sorted(valeurs)
            print(
                f"      {terminal:<12} n={len(valeurs):>3}  median {triees[len(triees) // 2] * 100:>6.2f} %"
                f"  max {max(valeurs) * 100:>6.2f} %"
            )
        tous = sorted(e["ecart_rel"] for e in ecarts)
        print(
            f"   toutes installations : n={len(ecarts)}  median {tous[len(tous) // 2] * 100:.2f} %"
            f"  max {max(tous) * 100:.2f} %"
        )

        # -- le controle sur les volumes et les debits ---------------------
        controles: list[tuple[str, float, float]] = []
        flux: list[tuple[str, float, float]] = []
        for (code, jour), element in bruts.items():
            terminal_enagas = next((k for k, v in CORRESPONDANCE_ENAGAS.items() if v == code), None)
            if terminal_enagas is None:
                continue
            cible = (dt.date.fromisoformat(jour) + dt.timedelta(days=decalage)).isoformat()
            reference_enagas = enagas.get((terminal_enagas, cible))
            if reference_enagas is None:
                continue
            lng_alsi = float(element["inventory"]["lng"]) * 1000.0
            controles.append((terminal_enagas, lng_alsi, reference_enagas["stock_m3"]))
            flux.append(
                (
                    terminal_enagas,
                    float(element["sendOut"]),
                    # Le flux Reseau de la plateforme se compare a la
                    # regazification de l'exploitant, et a rien d'autre : les
                    # citernes et les navires sortent aussi des cuves, mais
                    # la plateforme ne publie aucun champ pour eux.
                    reference_enagas["regas_gwh"],
                )
            )
        if controles:
            ecarts_m3 = [abs(a - b) / b for _, a, b in controles if b]
            print(
                f"   controle des volumes : ecart relatif median "
                f"{sorted(ecarts_m3)[len(ecarts_m3) // 2] * 100:.2f} % sur {len(ecarts_m3)} paires"
            )
            ecarts_flux = [abs(a - b) / b for _, a, b in flux if b]
            if ecarts_flux:
                print(
                    f"   controle des flux RESEAU : ecart relatif median "
                    f"{sorted(ecarts_flux)[len(ecarts_flux) // 2] * 100:.2f} % sur {len(ecarts_flux)} paires"
                )

        chemin_confrontation = sortie / "confrontation_alsi_enagas.csv"
        with chemin_confrontation.open("w", encoding="utf-8", newline="") as fichier:
            redacteur = csv.DictWriter(fichier, fieldnames=list(ecarts[0].keys()))
            redacteur.writeheader()
            for ecart in sorted(ecarts, key=lambda e: (e["terminal_enagas"], e["jour_alsi"])):
                redacteur.writerow(
                    {
                        **ecart,
                        "ecart_abs_gwh": round(float(ecart["ecart_abs_gwh"]), 3),
                        "ecart_rel": round(float(ecart["ecart_rel"]), 6),
                        "stock_alsi_gwh": round(float(ecart["stock_alsi_gwh"]), 3),
                        "stock_enagas_gwh": round(float(ecart["stock_enagas_gwh"]), 3),
                    }
                )
        print(f"   la confrontation detaillee -> {chemin_confrontation}")

        # -- le controle de PERIMETRE : ce que la plateforme compte -------
        # Le flux reseau de la plateforme et la regazification publiee par
        # l'exploitant se comparent sur le MOIS : le cumul neutralise le
        # decalage eventuel d'un jour et donne un signal fort.
        # Ce que l'exploitant publie en plus -- le chargement sur citernes
        # et le LNG charge sur navire -- sort aussi des cuves, mais la
        # plateforme ne publie aucun champ pour cela.
        perimetre: list[dict[str, object]] = []
        for terminal_enagas, code in CORRESPONDANCE_ENAGAS.items():
            # Le cumul se fait sur le MOIS de confrontation, pas sur la
            # fenetre entiere : les deux series doivent porter la meme
            # periode pour que la comparaison ait un sens.
            serie = sorted(
                (
                    (jour, element)
                    for (c, jour), element in bruts.items()
                    if c == code and debut_mois <= jour <= fin_mois
                ),
                key=lambda paire: paire[0],
            )
            if len(serie) < 2:
                continue
            envois = sum(float(element["sendOut"]) for _, element in serie)
            stocks = [float(element["inventory"]["gwh"]) for _, element in serie]
            if not any(k[0] == terminal_enagas for k in enagas):
                continue
            regas = sum(v["regas_gwh"] for k, v in enagas.items() if k[0] == terminal_enagas)
            citernes = sum(v["citernes_gwh"] for k, v in enagas.items() if k[0] == terminal_enagas)
            navires = sum(v["reexport_gwh"] for k, v in enagas.items() if k[0] == terminal_enagas)
            decharge = sum(v["decharge_gwh"] for k, v in enagas.items() if k[0] == terminal_enagas)
            derive = stocks[-1] - stocks[0] + envois
            perimetre.append(
                {
                    "terminal_enagas": terminal_enagas,
                    "terminal_eic": code,
                    "sendout_alsi_gwh": round(envois, 3),
                    "regas_exploitant_gwh": round(regas, 3),
                    "ecart_reseau_pct": round((envois - regas) / regas * 100, 3) if regas else 0.0,
                    "citernes_gwh": round(citernes, 3),
                    "navires_gwh": round(navires, 3),
                    "decharge_publiee_gwh": round(decharge, 3),
                    "decharge_derivee_gwh": round(derive, 3),
                    "ecart_decharge_pct": (
                        round((derive - decharge) / decharge * 100, 3) if decharge else 0.0
                    ),
                    "sorties_non_publiees_gwh": round(citernes + navires, 3),
                }
            )
        if perimetre:
            print()
            print("   le controle de PERIMETRE (cumul du mois) :")
            print(
                f"      {'terminal':<12}{'sendOut ALSI':>13}{'regas':>10}{'ecart':>9}"
                f"{'citernes':>10}{'navires':>9}{'entree publiee':>17}"
                f"{'entree derivee':>17}{'ecart':>9}"
            )
            for ligne in perimetre:
                print(
                    f"      {ligne['terminal_enagas']!s:<12}"
                    f"{float(ligne['sendout_alsi_gwh']):>13,.0f}"
                    f"{float(ligne['regas_exploitant_gwh']):>10,.0f}"
                    f"{float(ligne['ecart_reseau_pct']):>8.2f} %"
                    f"{float(ligne['citernes_gwh']):>10,.0f}"
                    f"{float(ligne['navires_gwh']):>9,.0f}"
                    f"{float(ligne['decharge_publiee_gwh']):>17,.0f}"
                    f"{float(ligne['decharge_derivee_gwh']):>17,.0f}"
                    f"{float(ligne['ecart_decharge_pct']):>8.2f} %"
                )
            ecarts_reseau = [float(ligne["ecart_reseau_pct"]) for ligne in perimetre]
            ecarts_decharge = [float(ligne["ecart_decharge_pct"]) for ligne in perimetre]
            print(
                f"      le flux RESEAU concorde a {max(abs(v) for v in ecarts_reseau):.2f} % "
                f"au maximum ; l'ecart de dechargement atteint {min(ecarts_decharge):+.2f} %"
            )
            print(
                "      => la plateforme ne publie QUE l'injection reseau : l'entree derivee "
                "est une BORNE INFERIEURE"
            )
            chemin_perimetre = sortie / "confrontation_perimetre_alsi_enagas.csv"
            with chemin_perimetre.open("w", encoding="utf-8", newline="") as fichier:
                redacteur = csv.DictWriter(fichier, fieldnames=list(perimetre[0].keys()))
                redacteur.writeheader()
                redacteur.writerows(perimetre)
            print(f"      le controle de perimetre -> {chemin_perimetre}")

    # -- les sorties -------------------------------------------------------
    chemin_serie = sortie / "europe_lng_terminals.csv"
    with chemin_serie.open("w", encoding="utf-8", newline="") as fichier:
        redacteur = csv.DictWriter(fichier, fieldnames=list(lignes_csv[0].keys()))
        redacteur.writeheader()
        redacteur.writerows(lignes_csv)
    print()
    print("8. les sorties")
    print(f"   serie par installation : {len(lignes_csv)} lignes -> {chemin_serie}")

    indicateurs = {
        "produit": "TORNE · LNG-002 — European Gas Supply Intelligence, couche terminaux",
        "genere_le": dt.datetime.now(dt.UTC).isoformat(),
        "fenetre": {"debut": debut, "fin": fin},
        "date_reference": reference.isoformat(),
        "sources": [
            {
                "source_id": "gie.alsi",
                "producteur": "Gas Infrastructure Europe (GIE)",
                "dataset": "ALSI Transparency Platform",
                "unites": "stock et capacite en GWh ; volume en milliers de m3 ; debit en GWh/jour",
                "acces": "https://alsi.gie.eu/api (en-tete x-key)",
                "reference_identifiants": REFERENCE_EC,
            },
            {
                "source_id": "enagas.seguimiento_diario",
                "producteur": "Enagas",
                "dataset": "Seguimiento Diario del Sistema",
                "unites": "stock en GWh et en m3 liquides ; flux en GWh",
                "acces": "https://www.enagas.es/.../dailysystemtracking.dailysystemtrackingdto.json",
            },
        ],
        "concentration": concentration,
        "concentration_par_pays": geo,
        "dependance_par_pays": par_pays,
        "controle_somme_agregat": [
            {
                "pays": pays,
                "terminaux_comptes": comptes,
                "somme_terminaux_gwh": round(somme, 3),
                "agregat_publie_gwh": round(agregat, 3),
                "ecart_relatif": round((somme - agregat) / agregat, 6) if agregat else 0.0,
            }
            for pays, somme, agregat, comptes in controles_somme
        ],
        "installations_sans_donnee": sans_donnee,
        "couverture_systeme_jours": couverture_system,
        "reserve_systeme_gwh": reserve,
        "debit_systeme_gwh_j": debit,
        "scenarios_perte": sorted(scenarios, key=lambda r: -r["jours_perdus"])[:10],
        "installations": len(series),
        "etats": len(etats),
    }
    chemin_indicateurs = sortie / "terminaux_indicateurs.json"
    chemin_indicateurs.write_text(
        json.dumps(indicateurs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"   indicateurs : {chemin_indicateurs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
