"""RESOURCE-003 — TORNE · LNG Terminal Intelligence : la serie quotidienne.

Ce script **produit l'objet**. Il ne compare pas des capteurs, il ne
cartographie pas des sources : il assemble, jour par jour et terminal par
terminal, l'etat physique des terminaux d'importation de GNL, et il en
tire la grandeur que personne ne publie — la **marge temporelle**.

Ce que le script produit
------------------------

1. **La serie** (`terminal_quotidien.csv`) : une ligne par terminal et par
   jour de gaz, avec les volumes recus, regasifies, charges sur citernes,
   le stock, le remplissage, **la date de l'evenement et la date de
   publication**, et la marge derivee avec son intervalle.
2. **L'indicateur** : le nombre de jours de tension par terminal.
3. **Le verdict** sur la question posee — le stock est-il estimable avec
   les donnees disponibles ? — et sur ce qui reste a demander a
   l'exploitant.

Ce qui est mesure, et non suppose
----------------------------------

- la **conversion energie-masse** est lue sur le rapport lui-meme (le
  rapport publie la meme grandeur en GWh et en m3) ;
- l'**alignement des colonnes** est controle par le total : le total doit
  etre la somme des sept terminaux, chaque jour, chaque ligne.

Usage :

    uv run python experiments/resource_003_lng_terminal_intelligence.py [AAAA-MM] [sortie]
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import os
import sys
from pathlib import Path

# Le socle verifie les certificats — il a raison. Mais cette machine n'a
# aucun magasin CA configure pour OpenSSL (`ssl.get_default_verify_paths()`
# rend `cafile=None`), et la verification echoue donc sur *toute* source
# HTTPS. Le remede est d'indiquer le magasin de `certifi`, qui est installe :
# la verification reste **complete**, on ne desactive rien.
try:  # pragma: no cover - dependance d'environnement
    import certifi

    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
except ImportError:  # pragma: no cover
    pass

from torne.acquisition import FileRawStore, HttpTransport
from torne.acquisition.adapters.enagas import EnagasDailyAdapter
from torne.contracts.model import ModelInputs, ModelParameters
from torne.supply.enagas import decoder_json
from torne.supply.lng import (
    ModelMargeOperationnelle,
    TerminalDay,
    serie_par_terminal,
)

RACINE = Path(__file__).resolve().parent.parent
"""La racine du depot, ou se trouve le `.env` ignore par git."""

FENETRE_JOURS = 30
"""Le nombre de jours de gaz examines par defaut."""

SEUIL_TENSION_JOURS = 3.0
"""En dessous de ce nombre de jours de couverture, le terminal est en tension."""


def _fenetre(mois: str) -> list[dt.date]:
    """Les jours de gaz d'un mois."""
    annee, numero = (int(x) for x in mois.split("-"))
    premier = dt.date(annee, numero, 1)
    suivant = dt.date(annee + (numero == 12), 1 if numero == 12 else numero + 1, 1)
    jours: list[dt.date] = []
    courant = premier
    while courant < suivant:
        jours.append(courant)
        courant += dt.timedelta(days=1)
    return jours


def main(argv: list[str]) -> int:
    """La serie, l'indicateur, et le verdict."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    mois = argv[1] if len(argv) > 1 else dt.date.today().strftime("%Y-%m")
    sortie = Path(argv[2]) if len(argv) > 2 else RACINE / "data" / "resource-003"
    sortie.mkdir(parents=True, exist_ok=True)
    magasin = FileRawStore(sortie / "preuves")
    transport = HttpTransport(timeout=120.0)

    print("=" * 104)
    print(f"TORNE · LNG Terminal Intelligence — serie quotidienne, {mois}")
    print()

    jours: list[dt.date] = []
    etats: list[TerminalDay] = []
    refus: list[tuple[str, str]] = []
    facteurs: list[float] = []
    ecarts: list[float] = []
    delais: list[float] = []

    for jour in _fenetre(mois):
        adaptateur = EnagasDailyAdapter(jour)
        demande = adaptateur.initial_request()
        reponse = transport.send(demande)
        if reponse.status_code != 200:
            refus.append((jour.isoformat(), f"HTTP {reponse.status_code}"))
            continue
        magasin.put(
            reponse.body,
            source_id="enagas.seguimiento_diario",
            key=f"quotidien/{jour.isoformat()}",
            media_type=reponse.content_type,
            acquired_at=dt.datetime.now(dt.UTC),
        )
        try:
            charge = json.loads(reponse.body.decode("utf-8", errors="replace"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            refus.append((jour.isoformat(), "corps illisible"))
            continue
        lecture = decoder_json(charge, jour)
        if lecture is None:
            refus.append((jour.isoformat(), "rapport illisible ou controle par le total negatif"))
            continue
        etats.extend(lecture.terminaux)
        if lecture.facteur_m3_par_gwh:
            facteurs.append(lecture.facteur_m3_par_gwh)
        ecarts.append(lecture.ecart_controle)
        delais.extend(t.delai_publication_heures for t in lecture.terminaux)
        jours.append(jour)

    print("1. les rapports")
    print(f"   jours de gaz du mois      : {len(_fenetre(mois))}")
    print(f"   rapports lus              : {len(jours)}")
    print(f"   rapports refuses          : {len(refus)}")
    for jour, motif in refus[:8]:
        print(f"      {jour} : {motif}")
    if not etats:
        print("   aucune donnee exploitable : le produit ne peut pas etre construit")
        return 1

    print()
    print("2. les controles")
    print(f"   ecart maximal total/somme  : {max(ecarts):.2e}  (tolerance 1e-03)")
    print(
        f"   facteur m3 par GWh         : {min(facteurs):.3f} a {max(facteurs):.3f} "
        f"(moyenne {sum(facteurs) / len(facteurs):.3f})"
    )
    print(f"   soit, en tonnes par GWh    : {sum(facteurs) / len(facteurs) * 0.456:.3f} t")
    print(
        f"   delai de publication       : {min(delais):.1f} a {max(delais):.1f} h "
        f"apres le jour de gaz"
    )
    print("   [FAIT] le stock est OBSERVE : l'exploitant publie les existances en cuves,")
    print("          en m3 et en GWh, chaque jour, par terminal. La question posee")
    print("          n'est donc pas de l'estimer : elle est de l'UTILISER.")

    print()
    print("3. la serie")
    groupes = serie_par_terminal(etats)
    modele = ModelMargeOperationnelle()
    parametres = ModelParameters(
        values={
            "fenetre_jours": 30,
            "seuil_tension_jours": SEUIL_TENSION_JOURS,
            "stock_mini_frac": 0.10,
        }
    )
    lignes_csv: list[dict[str, object]] = []
    resumes: list[tuple[str, float, float, int, int]] = []
    for terminal, suite in sorted(groupes.items()):
        entrees = ModelInputs(
            series={
                "stock_final_m3": tuple(j.stock_final_m3 for j in suite),
                "regas_m3": tuple(j.regas_m3 for j in suite),
                "sorties_citernes_m3": tuple(j.sorties_citernes_m3 for j in suite),
                "entrees_m3": tuple(j.entrees_m3 for j in suite),
                "remplissage": tuple(j.remplissage for j in suite),
            }
        )
        resultat = modele.run(entrees, parametres)
        marges = resultat.output("marge_jours")
        tensions = resultat.output("tension")
        for position, jour in enumerate(suite):
            lignes_csv.append(
                {
                    "terminal": terminal,
                    "jour_gaz": jour.jour_gaz.isoformat(),
                    "date_publication": jour.date_publication.isoformat(),
                    "entrees_m3": round(jour.entrees_m3, 1),
                    "regas_m3": round(jour.regas_m3, 1),
                    "sorties_citernes_m3": round(jour.sorties_citernes_m3, 1),
                    "reexport_m3": round(jour.reexport_m3, 1),
                    "stock_final_m3": round(jour.stock_final_m3, 1),
                    "stock_final_t": round(jour.stock_final_t, 2),
                    "remplissage": round(jour.remplissage, 6),
                    "reserve_m3": round(resultat.output("reserve_m3")[position], 1),
                    "marge_jours": round(marges[position], 3),
                    "marge_bas": round(resultat.interval("marge_jours")[position][0], 3),
                    "marge_haut": round(resultat.interval("marge_jours")[position][1], 3),
                    "tension": int(tensions[position]),
                }
            )
        marges_triees = sorted(marges)
        resumes.append(
            (
                terminal,
                marges_triees[len(marges_triees) // 2],
                min(marges),
                int(sum(tensions)),
                len(suite),
            )
        )

    chemin_csv = sortie / "terminal_quotidien.csv"
    with chemin_csv.open("w", encoding="utf-8", newline="") as fichier:
        redacteur = csv.DictWriter(fichier, fieldnames=list(lignes_csv[0].keys()))
        redacteur.writeheader()
        redacteur.writerows(lignes_csv)
    print(f"   {len(lignes_csv)} lignes (terminal x jour) -> {chemin_csv}")

    print()
    print("4. l'indicateur de tension")
    print(f"   {'terminal':<12} {'marge mediane':>14} {'marge min':>11} {'jours en tension':>17}")
    for terminal, mediane, minimum, tension_jours, nombre in resumes:
        marque = "  <<<" if tension_jours else ""
        print(
            f"   {terminal:<12} {mediane:>11.1f} j {minimum:>8.1f} j {tension_jours:>10}/{nombre}{marque}"
        )

    print()
    print("5. le verdict")
    if etats:
        print("   [FAIT] Le stock n'a pas besoin d'etre estime : il est OBSERVE, chaque jour,")
        print("          par terminal, avec son remplissage et ses deux dates.")
        print("   [FAIT] Ce qui n'est pas publie, et que ce produit produit : la MARGE —")
        print("          le nombre de jours de couverture au rythme de sortie observe.")
        print("   [NON VERIFIE] Le minimum technique des cuves reste un parametre : il")
        print("          conditionne la reserve, et donc la marge. C'est la seule")
        print("          question qui reste a poser a l'exploitant — avec le facteur")
        print("          de conversion, qui, lui, est desormais mesure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
