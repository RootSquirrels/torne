"""Acquisition réelle : trois sources, une seule page chacune.

Ce script n'est pas une démonstration simulée. Il **interroge réellement** trois
points d'accès publics, conserve ce qu'ils renvoient comme preuves brutes, et
affiche la chaîne complète : ce qui a été demandé, ce qui a été reçu, l'empreinte
qui nomme la preuve, et le journal d'acquisition.

C'est la preuve que le socle transversal d'acquisition fonctionne sur le monde
réel — et non seulement en test hors ligne. Les tests du dépôt ne touchent
jamais le réseau ; ce script, si.

Trois sources sont interrogées, choisies pour la **diversité de leur mode
d'accès** — c'est le but, pas l'exhaustivité :

| Source | Mode d'accès | Ce qu'elle montre |
|---|---|---|
| **Hub'EAU v2** (FR) | API JSON, pagination **par curseur** | un lien de page suivant fourni par le fournisseur |
| **USGS NWIS IV** (US) | API JSON, **sans** pagination, fenêtre temporelle | une source qui rend tout d'un coup |
| **Copernicus Data Space** | catalogue **OData**, `$top`/`$skip`/`$filter` | une pagination portée par un lien encodé |

Les paramètres sont minimaux et explicites : une station, une grandeur, une
fenêtre. Rien n'est balayé, rien n'est téléchargé en masse.

Usage :

    uv run python experiments/acquisition_demo.py [répertoire_de_sortie]
"""

from __future__ import annotations

import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from torne.acquisition import Fetcher, FileRawStore, HttpTransport, RetryPolicy
from torne.acquisition.adapters import (
    CopernicusProductsAdapter,
    HubeauObservationsAdapter,
    UsgsInstantaneousValuesAdapter,
)
from torne.acquisition.store import NOM_MANIFESTE

# Station de jauge du Rhin — le code de station est celui publié par Hub'EAU
# pour la station de Maxé ; il est explicite ici pour que la démonstration soit
# rejouable et que rien ne soit deviné.
CODE_STATION_RHIN = "O919001001"
CODE_COURS_EAU_RHIN = "O919"

# Station américaine du Mississippi (Natchez, MS) — l'autre bassin, pour montrer
# que le socle ne dépend d'aucun domaine.
SITE_NATCHEZ = "07381600"
GRANDEUR_DEBIT = "00060"  # débit instantané, en pieds cubes par seconde


def _titre(numero: int, texte: str) -> None:
    print()
    print(f"{numero}. {texte}")
    print("-" * len(texte))


def _decrire(issue, magasin: FileRawStore) -> None:
    """Affiche la chaîne complète d'une acquisition."""
    print(f"source       : {issue.request.source_id}")
    print(f"demande      : {issue.request.method} {issue.request.effective_url}")
    print(f"issue        : {issue.status.value}")
    print(f"exhaustivité : {issue.exhaustiveness.value}")
    print(f"pages        : {issue.page_count}")
    for tentative in issue.attempts:
        code = tentative.status_code if tentative.status_code is not None else "—"
        cause = tentative.error_kind.value if tentative.error_kind else "ok"
        duree = f"{tentative.elapsed_ms} ms" if tentative.elapsed_ms else "—"
        print(f"  tentative  : page {tentative.page_index} · HTTP {code} · {cause} · {duree}")
    if issue.error_kind is not None:
        print(f"erreur       : {issue.error_kind.value} — {issue.error_detail}")
    for preuve in issue.evidence:
        chemin = magasin.content_path(preuve.evidence_id)
        print(f"  preuve     : {preuve.evidence_id[:16]}… · {preuve.media_type}")
        print(f"               {chemin}")
        print(f"               connue depuis le {preuve.acquired_at.isoformat()}")


def _magasin(racine: Path) -> FileRawStore:
    return FileRawStore(racine)


def _fichiers_de_contenu(racine: Path) -> list[Path]:
    """Les fichiers de contenu conservés, journal mis à part.

    C'est le nombre de **contenus distincts** : il ne bouge pas quand on
    récupère deux fois la même chose.
    """
    return sorted(
        chemin for chemin in racine.rglob("*") if chemin.is_file() and chemin.name != NOM_MANIFESTE
    )


def main(argv: list[str]) -> int:
    """Interroge les trois sources et affiche ce qui a été acquis."""
    sortie = Path(argv[1]) if len(argv) > 1 else Path(tempfile.mkdtemp(prefix="torne-acquisition-"))
    sortie.mkdir(parents=True, exist_ok=True)

    print("TORNE — acquisition réelle")
    print(f"sortie       : {sortie}")
    print(f"horodatage   : {datetime.now(UTC).isoformat()}")

    transport = HttpTransport(timeout=60.0)
    magasin = _magasin(sortie)
    fetcher = Fetcher(
        transport=transport,
        store=magasin,
        retry=RetryPolicy(max_attempts=3, initial_delay=1.0),
    )

    issues = []

    # ------------------------------------------------------------------
    _titre(1, "Hub'EAU v2 — observations hydrométriques (pagination par curseur)")
    # ------------------------------------------------------------------
    hubeau = HubeauObservationsAdapter(
        code_station=[CODE_STATION_RHIN],
        code_cours_eau=[CODE_COURS_EAU_RHIN],
        grandeur_hydro="H",
        page_size=50,
        max_pages=2,
    )
    issue_hubeau = fetcher.acquire(hubeau)
    issues.append(issue_hubeau)
    _decrire(issue_hubeau, magasin)
    if issue_hubeau.evidence:
        corps = issue_hubeau.evidence[0]
        print(f"  taille     : {magasin.content_path(corps.evidence_id).stat().st_size} octets")

    # ------------------------------------------------------------------
    _titre(2, "USGS NWIS — valeurs instantanées (sans pagination)")
    # ------------------------------------------------------------------
    fin = datetime.now(UTC)
    debut = fin - timedelta(days=7)
    usgs = UsgsInstantaneousValuesAdapter(
        sites=[SITE_NATCHEZ],
        parameter_cd=[GRANDEUR_DEBIT],
        start_dt=debut,
        end_dt=fin,
    )
    issue_usgs = fetcher.acquire(usgs)
    issues.append(issue_usgs)
    _decrire(issue_usgs, magasin)

    # ------------------------------------------------------------------
    _titre(3, "Copernicus Data Space — catalogue de produits (OData)")
    # ------------------------------------------------------------------
    copernicus = CopernicusProductsAdapter(
        filter_expression="startswith(Name,'Sentinel-2')",
        page_size=10,
        max_pages=1,
    )
    issue_copernicus = fetcher.acquire(copernicus)
    issues.append(issue_copernicus)
    _decrire(issue_copernicus, magasin)

    # ------------------------------------------------------------------
    _titre(4, "Journal d'acquisition")
    # ------------------------------------------------------------------
    entrees = magasin.read_manifest()
    print(f"lignes       : {len(entrees)}")
    for entree in entrees:
        empreintes = entree.get("content_sha256") or []
        apercu = ", ".join(str(empreinte)[:12] for empreinte in empreintes[:2]) or "—"
        print(
            f"  {entree['acquired_at']} · {entree['source_id']} · "
            f"{entree['status']}/{entree['exhaustiveness']} · {len(empreintes)} page(s) · "
            f"{apercu}… · {entree['media_type']} · {entree['size']} octets"
        )

    # ------------------------------------------------------------------
    _titre(5, "Reprise de la même question — contenu dédupliqué, acquisition journalisée")
    # ------------------------------------------------------------------
    avant = len(_fichiers_de_contenu(sortie))
    lignes_avant = len(magasin.read_manifest())
    issue_reprise = fetcher.acquire(usgs)
    apres = len(_fichiers_de_contenu(sortie))
    lignes_apres = len(magasin.read_manifest())
    memes_empreintes = [p.evidence_id for p in issue_usgs.evidence] == [
        p.evidence_id for p in issue_reprise.evidence
    ]
    print(f"fichiers de contenu : {avant} -> {apres}")
    print(f"lignes de journal   : {lignes_avant} -> {lignes_apres}")
    print(f"contenu identique   : {'oui' if memes_empreintes else 'non'}")
    if memes_empreintes:
        print(
            "-> le même contenu n'est pas réécrit : la même empreinte désigne le "
            "même fichier. Ce qui est nouveau, c'est l'événement journalisé."
        )
    else:
        print(
            "-> la même question a rendu un contenu différent : le fournisseur a "
            "publié des valeurs plus récentes. C'est exactement pourquoi chaque "
            "acquisition est journalisée séparément, et pourquoi l'instant d'un "
            "contenu est celui de sa première conservation."
        )
    for preuve in issue_reprise.evidence:
        print(f"   contenu connu depuis le {preuve.acquired_at.isoformat()}")
    print(f"exhaustivité        : {issue_reprise.exhaustiveness.value}")
    print("   (cette source ne déclare pas l'épuisement de son parcours : UNDECLARED)")

    # ------------------------------------------------------------------
    _titre(6, "Ce que cette démonstration prouve — et ce qu'elle ne prouve pas")
    # ------------------------------------------------------------------
    acquis = sum(1 for issue in issues if issue.succeeded)
    print(f"sources acquises : {acquis}/{len(issues)}")
    print()
    print("Elle prouve : que le socle transversal sait récupérer, suivre la pagination,")
    print("conserver la réponse brute, l'empreinter, et consigner l'échec comme le succès.")
    print("Elle prouve aussi : que le contenu est dédupliqué, que chaque acquisition est")
    print("journalisée, et que l'exhaustivité du parcours est qualifiée plutôt que supposée.")
    print()
    print("Elle ne prouve pas : que les données sont comprises, qu'elles sont justes, ni")
    print("que quoi que ce soit de scientifique. Aucun objet de domaine n'a été construit :")
    print("c'est le travail du Sprint 3, et la question du Sprint 4.")

    return 0 if acquis == len(issues) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
