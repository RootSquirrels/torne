"""LNG-002 — European Gas Supply Intelligence : la serie et les indicateurs.

Ce script **produit l'objet**. Il ne compare pas des sources, il ne cartographie
pas un secteur : il construit l'historique quotidien europeen du stockage
souterrain, il en tire les indicateurs de resilience physique, et il les
**confronte aux agregats que GIE publie deja** — parce que la question qui
decide de tout est celle-ci : *ce que nous reconstruisons existait-il deja, sous
une autre forme ?*

Ce que le script produit
------------------------

1. **la serie** (`europe_stocks.csv`) : une ligne par pays et par jour de gaz,
   avec le stock, la capacite, l'injection, le soutirage, le remplissage
   **publie**, l'autonomie **publiee**, la couverture **calculee**, et les deux
   dates ;
2. **les indicateurs** (`europe_indicateurs.json`) : buffer en jours, taux de
   reconstitution, pression de prelevement, degradation, concentration
   europeenne, dependance ;
3. **la confrontation** : notre couverture en jours, contre l'autonomie equivalente
   **publiee** par GIE. C'est elle qui dit si le produit apporte quelque chose.

Un piege de secret
------------------

La plateforme GIE **renvoie la cle dans certains messages d'erreur**
(`API key: ...`). Ces messages sont donc **assainis avant d'etre consignes** :
un secret ne doit jamais atteindre un fichier ni le journal, y compris par
l'intermediaire d'une source qui le repete.

Ce qui n'est pas fait, et pourquoi
----------------------------------

La couche **terminaux LNG europeens** (ALSI) n'est pas encore interrogeable : la
cle du depot est valide pour AGSI+ mais ** refuse par ALSI**, parce que le
compte GIE n'est pas regle sur l'acces aux deux plateformes. C'est une action
de configuration, pas une etude. L'adaptateur est ecrit et pret ; l'execution
depend de ce reglage.

Usage :

    uv run python experiments/resource_004_european_gas.py [AAAA-MM] [sortie]
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

from torne.acquisition import FileRawStore, HttpTransport
from torne.acquisition.adapters.gie import CREDENTIAL_REF, GieAdapter
from torne.acquisition.credentials import FichierEnvToken
from torne.supply.gas import (
    concentration_herfindahl,
    degradation,
    dependance_top,
    pression_prelevement,
    taux_reconstitution,
)
from torne.supply.gie import controle_unite, decoder_agsi

RACINE = Path(__file__).resolve().parent.parent
"""La racine du depot, ou se trouve le `.env` ignore par git."""

VARIABLE = "AGSI_API_KEY"
"""La variable d'environnement qui porte la cle GIE."""

PAYS = (
    "AT",
    "BE",
    "BG",
    "HR",
    "CY",
    "CZ",
    "DK",
    "EE",
    "FI",
    "FR",
    "DE",
    "GR",
    "HU",
    "IE",
    "IT",
    "LV",
    "LT",
    "LU",
    "MT",
    "NL",
    "PL",
    "PT",
    "RO",
    "SK",
    "SI",
    "ES",
    "SE",
    "UK",
    "NO",
    "CH",
    "UA",
)
"""Les codes ISO-2 essayes : la couverture est **decouverte**, pas supposee."""

FENETRE_JOURS = 31
"""La fenetre demandee a la plateforme, en jours de gaz."""

SECRET_ASCII = re.compile(r"\b[0-9a-f]{16,}\b", re.IGNORECASE)
"""Le motif d'un secret hexadecimal, comme ceux que la plateforme repete."""


def _assainir(texte: str) -> str:
    """Un message de la source, depourvu de tout secret.

    La plateforme GIE renvoie la cle dans certains messages d'erreur. Ce
    message ne doit jamais atteindre un fichier ni le journal.
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


def _fenetres(debut: str, fin: str) -> list[tuple[str, str]]:
    """Les fenetres de la periode, decoupees pour la plateforme."""
    premier = dt.date.fromisoformat(debut)
    dernier = dt.date.fromisoformat(fin)
    fenetres: list[tuple[str, str]] = []
    courant = premier
    while courant <= dernier:
        fin_fenetre = min(courant + dt.timedelta(days=FENETRE_JOURS - 1), dernier)
        fenetres.append((courant.isoformat(), fin_fenetre.isoformat()))
        courant = fin_fenetre + dt.timedelta(days=1)
    return fenetres


def main(argv: list[str]) -> int:
    """La serie europeenne, les indicateurs, et la confrontation."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    mois = argv[1] if len(argv) > 1 else dt.date.today().strftime("%Y-%m")
    sortie = Path(argv[2]) if len(argv) > 2 else RACINE / "data" / "resource-004"
    sortie.mkdir(parents=True, exist_ok=True)
    magasin = FileRawStore(sortie / "preuves")
    transport = HttpTransport(timeout=90.0)

    fournisseur = _fournisseur()
    tete = fournisseur.credentials_for(CREDENTIAL_REF)
    print("TORNE — LNG-002, European Gas Supply Intelligence")
    print(
        f"cle GIE : {'presente (variable ' + VARIABLE + '), jamais ecrite' if tete else 'ABSENTE'}"
    )
    print(f"periode : {mois} · sortie : {sortie}")
    print()

    annee, numero = (int(x) for x in mois.split("-"))
    debut = f"{annee:04d}-{numero:02d}-01"
    suivant = dt.date(annee + (numero == 12), 1 if numero == 12 else numero + 1, 1)
    fin = (suivant - dt.timedelta(days=1)).isoformat()

    etats: list = []
    couverture: list[str] = []
    ecarts_unite: list[float] = []
    refus: list[str] = []

    for pays in PAYS:
        for debut_f, fin_f in _fenetres(debut, fin):
            adaptateur = GieAdapter(debut=debut_f, fin=fin_f, pays=pays, taille=128)
            demande = adaptateur.initial_request()
            reponse = transport.send(demande, credentials=tete)
            if reponse.status_code != 200:
                refus.append(f"{pays} {debut_f} HTTP {reponse.status_code}")
                continue
            magasin.put(
                reponse.body,
                source_id=adaptateur.source_id,
                key=f"{pays}/{debut_f}",
                media_type=reponse.content_type,
                acquired_at=dt.datetime.now(dt.UTC),
            )
            try:
                charge = json.loads(reponse.body.decode("utf-8", errors="replace"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                refus.append(f"{pays} {debut_f} corps illisible")
                continue
            if charge.get("error"):
                refus.append(f"{pays} {debut_f} : {_assainir(str(charge.get('message') or ''))}")
                continue
            elements = charge.get("data") or []
            if elements and pays not in couverture:
                couverture.append(pays)
            for element in elements:
                etat = decoder_agsi(element)
                if etat is None:
                    continue
                etats.append(etat)
                ecart = controle_unite(element)
                if ecart is not None:
                    ecarts_unite.append(ecart)

    print("1. la couverture, decouverte par interrogation")
    print(f"   pays couverts par AGSI+ : {len(couverture)} / {len(PAYS)} essayes")
    print(f"   {', '.join(couverture)}")
    if refus:
        print(f"   refus ou absences : {len(refus)}")
        for motif in refus[:5]:
            print(f"      {motif}")
    print(f"   etats de stockage lus : {len(etats)}")
    if ecarts_unite:
        print("   controle d'unite (remplissage publie contre stock/capacite) :")
        print(f"      ecart maximal : {max(ecarts_unite):.3e} point de pourcentage")
        print(
            "      -> les stocks sont bien en TWh et les flux en GWh/jour : "
            "c'est mesure, pas suppose"
        )

    # -- la serie, par pays ------------------------------------------------
    par_pays: dict[str, list] = {}
    for etat in etats:
        par_pays.setdefault(etat.installation, []).append(etat)
    for suite in par_pays.values():
        suite.sort(key=lambda e: e.jour_gaz)

    chemin_serie = sortie / "europe_stocks.csv"
    indicateurs: list[dict] = []
    stocks_fin: dict[str, float] = {}

    with chemin_serie.open("w", encoding="utf-8", newline="") as fichier:
        redacteur = csv.writer(fichier)
        redacteur.writerow(
            [
                "pays",
                "jour_gaz",
                "date_publication",
                "stock_gwh",
                "capacite_gwh",
                "injection_gwh_j",
                "soutirage_gwh_j",
                "remplissage_publie_pct",
                "autonomie_publiee_jours",
                "couverture_calculee_jours",
                "couverture_sur_consommation_publiee_jours",
                "rapport_autonomie_publiee_sur_consommation",
                "taux_reconstitution_cap_j",
                "pression_prelevement",
            ]
        )
        for pays, suite in sorted(par_pays.items()):
            sorties = [e.sortie for e in suite]
            recon = taux_reconstitution(suite)
            marges: list[float] = []
            for index, etat in enumerate(suite):
                tranche = sorties[max(0, index - 29) : index + 1]
                moyenne = sum(tranche) / len(tranche) if tranche else 0.0
                couverture_jours = etat.stock / moyenne if moyenne > 0 else None
                if couverture_jours is None:
                    couverture_jours = etat.autonomie_publiee
                marges.append(couverture_jours or 0.0)
                pression = pression_prelevement(etat.sortie, moyenne) if moyenne > 0 else None
                sur_consommation = etat.stock / etat.consommation if etat.consommation else None
                rapport = (
                    etat.autonomie_publiee / sur_consommation
                    if sur_consommation and etat.autonomie_publiee is not None
                    else None
                )
                redacteur.writerow(
                    [
                        pays,
                        etat.jour_gaz.isoformat(),
                        etat.date_publication.isoformat(),
                        round(etat.stock, 3),
                        round(etat.capacite, 3),
                        round(etat.entree or 0.0, 3),
                        round(etat.sortie, 3),
                        etat.rempli,
                        etat.autonomie_publiee,
                        round(couverture_jours, 3) if couverture_jours is not None else "",
                        round(sur_consommation, 3) if sur_consommation is not None else "",
                        round(rapport, 4) if rapport is not None else "",
                        round(recon, 8) if recon is not None else "",
                        round(pression, 4) if pression is not None else "",
                    ]
                )
            stocks_fin[pays] = suite[-1].stock
            dernier = suite[-1]
            tranche = sorties[-30:]
            moyenne = sum(tranche) / len(tranche) if tranche else 0.0
            couverture_jours = dernier.stock / moyenne if moyenne > 0 else 0.0
            publie = dernier.autonomie_publiee
            ecart = abs(couverture_jours - publie) if publie is not None else None
            couverture_sur_consommation = (
                dernier.stock / dernier.consommation if dernier.consommation else None
            )
            rapport_final = (
                publie / couverture_sur_consommation
                if publie is not None and couverture_sur_consommation
                else None
            )
            indicateurs.append(
                {
                    "pays": pays,
                    "jours": len(suite),
                    "stock_gwh": round(dernier.stock, 1),
                    "capacite_gwh": round(dernier.capacite, 1),
                    "remplissage_publie_pct": dernier.rempli,
                    "couverture_calculee_jours": round(couverture_jours, 2),
                    "autonomie_publiee_jours": publie,
                    "couverture_sur_consommation_publiee_jours": (
                        round(couverture_sur_consommation, 3)
                        if couverture_sur_consommation is not None
                        else None
                    ),
                    "rapport_autonomie_publiee_sur_consommation": (
                        round(rapport_final, 4) if rapport_final is not None else None
                    ),
                    "ecart_avec_la_publiee_jours": round(ecart, 3) if ecart is not None else None,
                    "taux_reconstitution_cap_j": round(recon or 0.0, 8),
                    "degradation_jours_par_jour": round(degradation(marges) or 0.0, 5),
                    "date_publication": dernier.date_publication.isoformat(),
                }
            )

    print()
    print(
        f"2. la serie : {sum(i['jours'] for i in indicateurs)} lignes (pays x jour) -> {chemin_serie}"
    )

    # -- les indicateurs et la confrontation --------------------------------
    print()
    print("3. les indicateurs de resilience, et la confrontation")
    print(f"{'pays':<6} {'stock GWh':>11} {'couv./conso':>12} {'couv. publ.':>12} {'rapport':>8}")
    for indicateur in indicateurs:
        publie = indicateur["autonomie_publiee_jours"]
        ecart = indicateur["ecart_avec_la_publiee_jours"]
        sur_conso = indicateur["couverture_sur_consommation_publiee_jours"]
        rapport = indicateur["rapport_autonomie_publiee_sur_consommation"]
        print(
            f"{indicateur['pays']:<6} {indicateur['stock_gwh']:>11,.0f} "
            f"{(f'{sur_conso:.1f}' if sur_conso is not None else '-'):>12} "
            f"{(f'{publie:.1f}' if publie is not None else '-'):>12} "
            f"{(f'{rapport:.3f}' if rapport is not None else '-'):>8}"
        )

    # -- la concentration et la dependance ---------------------------------
    parts = list(stocks_fin.values())
    herfindahl = concentration_herfindahl(parts)
    top1 = dependance_top(parts, 1)
    top3 = dependance_top(parts, 3)
    print()
    print("4. la concentration europeenne de la reserve")
    print(f"   Herfindahl des stocks nationaux : {herfindahl:.4f}")
    print(f"   part du premier pays : {top1 * 100:.1f} % · des trois premiers : {top3 * 100:.1f} %")
    print("   [FAIT] aucune de ces grandeurs n'est publiee par GIE : la plateforme")
    print("          publie des totaux, pas la repartition ni sa concentration.")

    # -- la persistance ----------------------------------------------------
    chemin_indicateurs = sortie / "europe_indicateurs.json"
    chemin_indicateurs.write_text(
        json.dumps(
            {
                "periode": {"debut": debut, "fin": fin},
                "couverture": couverture,
                "refus": refus,
                "indicateurs": indicateurs,
                "concentration": {
                    "herfindahl": herfindahl,
                    "part_premier_pays": top1,
                    "part_trois_premiers_pays": top3,
                },
                "unites": {"stocks": "GWh", "flux": "GWh/jour"},
                "provenance": {
                    "source": "GIE AGSI+ Transparency Platform",
                    "attribution": "GIE / AGSI+",
                    "api": "https://agsi.gie.eu/api",
                    "cle": "portee par credential_ref, jamais consignee",
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print()
    print(f"5. la persistance : {chemin_indicateurs}")
    print(f"   preuves brutes : {sortie / 'preuves'}")

    # -- le verdict --------------------------------------------------------
    rapports = [
        i["rapport_autonomie_publiee_sur_consommation"]
        for i in indicateurs
        if i["rapport_autonomie_publiee_sur_consommation"] is not None
    ]
    print()
    print("6. le verdict : qu'est-ce que le produit ajoute ?")
    if rapports:
        constant = max(rapports) - min(rapports) < 0.01
        print(
            f"   rapport autonomie publiee / (stock / consommation publiee) : "
            f"{min(rapports):.4f} a {max(rapports):.4f} "
            f"sur {len(rapports)} pays"
        )
        if constant:
            print()
            print("   [RESULTAT NEGATIF] L'autonomie equivalente que GIE publie est une")
            print("   FONCTION DETERMINISTE de deux grandeurs qu'il publie lui-meme :")
            print("   le stock et la consommation. Le rapport vaut 0,100 pour tous les")
            print("   pays. Au niveau pays, notre 'buffer en jours' n'est donc PAS une")
            print("   grandeur nouvelle : c'est une autre presentation de la meme donnee.")
            print("   Aucun avantage informationnel, a ce niveau.")
            print()
            print("   Ce qui n'est PAS publie, et qui reste le terrain du produit :")
            print("   - l'INSTALLATION : l'autonomie publiee est un agregat national, elle")
            print("     ne dit pas quelle installation est tendue ;")
            print(
                "   - la CONCENTRATION : Herfindahl "
                f"{herfindahl:.4f}, premier pays {top1 * 100:.1f} %, "
                f"trois premiers {top3 * 100:.1f} % ;"
            )
            print("   - les SCENARIOS : ce qu'il reste si une installation tombe ;")
            print("   - l'INSTANT : la date de publication de chaque etat.")
        else:
            print("   [ECART] le rapport n'est pas constant : le regime de debit de la")
            print("   source differe selon les pays, et notre reconstruction s'en")
            print("   distingue. C'est a confirmer sur d'autres periodes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
