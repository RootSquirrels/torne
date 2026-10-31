"""Démonstration bout en bout de la mission 001 — exécution, évaluation, preuve.

Ce script ne contient aucune logique métier : il ne fait qu'ordonner les
maillons livrés par le paquet et afficher ce qu'ils produisent. Il est
reproductible (graine fixe, horloge injectée) et ne touche au réseau ni au
disque.

    uv run python experiments/mission_001_demo.py

Ce qu'il montre, dans l'ordre :

1. une preuve brute et les observations qu'elle fonde ;
2. l'exécution d'un modèle — filtre de Kalman, tendance linéaire locale ;
3. l'évaluation hors échantillon, contre trois références ;
4. la comparaison appariée du modèle et d'une référence (Diebold-Mariano) ;
5. l'enregistrement de l'exécution et son produit de connaissance ;
6. la rejouabilité depuis la configuration conservée.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta

import numpy as np

from torne.contracts.derived import DerivedVariable, Uncertainty
from torne.contracts.knowledge import ProductStatus
from torne.contracts.model import ModelInputs, ModelParameters
from torne.contracts.observation import Observation, RawEvidence, Source
from torne.contracts.time import PublicationState, TemporalStamp
from torne.evaluation.baselines import persistence_forecast
from torne.evaluation.report import evaluate_walk_forward
from torne.evaluation.splits import walk_forward
from torne.execution.runner import execute, reproduce
from torne.knowledge.record import build_record, verify_lineage
from torne.methods.compare import compare_forecasts
from torne.methods.kalman import LocalLinearTrendModel

JOUR = timedelta(days=1)
DEBUT = datetime(2026, 1, 1, tzinfo=UTC)
NB_POINTS = 60
TAILLE_ENTRAINEMENT = 40
INSTANT_PRODUIT = DEBUT + (NB_POINTS + 10) * JOUR

MODELE = LocalLinearTrendModel()
PARAMETRES = ModelParameters(
    values={
        "measurement_variance": 0.8**2,
        "level_process_variance": 0.05**2,
        "slope_process_variance": 1e-6,
    }
)

SOURCE = Source(
    source_id="torne.demo.synthetique",
    producer="TORNE (démonstration)",
    dataset="série synthétique de niveau",
    access_point="générateur déterministe",
    license="CC0-1.0",
    revision_policy="aucune révision",
    unit="u",
    timezone="UTC",
    quality_status="simulé",
)


def _serie() -> tuple[list[float], list[float]]:
    """Série observée et état latent qui la produit : la vérité est connue."""
    generateur = np.random.default_rng(20261031)
    latente = np.cumsum(0.2 + 0.05 * generateur.standard_normal(NB_POINTS)) + 10.0
    observee = latente + 0.8 * generateur.standard_normal(NB_POINTS)
    return [float(v) for v in observee], [float(v) for v in latente]


def _observations(valeurs: list[float]) -> list[Observation]:
    """Une observation par point, publiée le lendemain de sa date de validité."""
    return [
        Observation(
            observation_id=f"obs-{index:03d}",
            source_id=SOURCE.source_id,
            quantity="niveau",
            unit="u",
            temporal=TemporalStamp(
                valid_time=DEBUT + index * JOUR,
                known_at=DEBUT + (index + 1) * JOUR,
                ingested_at=DEBUT + (index + 1) * JOUR,
                publication=PublicationState.ESTABLISHED,
            ),
            evidence_id="preuve-0001",
            value=valeur,
            spatial_ref="série de démonstration",
            key="niveau",
        )
        for index, valeur in enumerate(valeurs)
    ]


def _prevoir(entrainement: tuple[float, ...]) -> list[float]:
    resultat = MODELE.run(ModelInputs(series={"y": entrainement}), PARAMETRES)
    return [resultat.outputs["forecast_level"][-1]]


def _titre(numero: str, texte: str) -> None:
    print(f"\n{numero} {texte}")
    print("-" * len(texte))


def main() -> None:
    # La console Windows n"encoding pas toujours l'UTF-8 : on ne veut pas qu'un
    # caractère d'affichage interrompe la démonstration.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    valeurs, latente = _serie()
    observations = _observations(valeurs)
    entree = ModelInputs(series={"y": tuple(valeurs)})
    preuve = RawEvidence(
        evidence_id="preuve-0001",
        source_id=SOURCE.source_id,
        acquired_at=DEBUT + NB_POINTS * JOUR,
        media_type="application/json",
        content_sha256="0" * 64,
        key="niveau",
    )

    _titre("1.", "Preuve brute et observations")
    print(f"source       : {SOURCE.producer} — {SOURCE.dataset}")
    print(f"preuve       : {preuve.evidence_id} ({preuve.media_type})")
    print(f"observations : {len(observations)} — unité « {observations[0].unit} »")
    print(f"première     : {observations[0].observation_id} = {observations[0].value:.3f}")
    print(
        f"publiée le   : {observations[0].temporal.known_at:%Y-%m-%d} "
        f"(validité {observations[0].temporal.valid_time:%Y-%m-%d})"
    )

    _titre("2.", "Exécution du modèle")
    issue = execute(MODELE, entree, PARAMETRES)
    print(f"modèle       : {issue.config.model_id} v{issue.config.model_version}")
    print(f"question     : {MODELE.spec.question}")
    print(f"méthode      : {MODELE.spec.method}")
    print(f"paramètres   : {issue.config.parameters.as_dict()}")
    print(f"niveau filtré : {issue.result.outputs['level'][-1]:.3f}")
    print(f"état latent   : {latente[-1]:.3f} (connu par construction)")
    print(f"log-vraisemblance : {issue.result.diagnostics['log_likelihood']:.3f}")

    _titre("3.", "Évaluation hors échantillon")
    rapport = evaluate_walk_forward(
        valeurs,
        _prevoir,
        initial_size=TAILLE_ENTRAINEMENT,
        step=1,
        model_id=MODELE.spec.model_id,
        model_version=MODELE.spec.version,
        now=INSTANT_PRODUIT,
    )
    print(f"entraînement  : {rapport.split.train_end} points")
    print(f"test         : {rapport.split.test_start} -> {rapport.split.test_end} points")
    print(f"points utilisés : {rapport.metrics['rmse'].n_used}")
    print(f"{'méthode':<16}{'RMSE':>10}{'MAE':>10}{'biais':>10}")
    ligne = rapport.metrics
    print(
        f"{'modèle':<16}{ligne['rmse'].value:>10.4f}"
        f"{ligne['mae'].value:>10.4f}{ligne['bias'].value:>10.4f}"
    )
    for nom, metriques in rapport.baseline_metrics.items():
        print(
            f"{nom:<16}{metriques['rmse'].value:>10.4f}"
            f"{metriques['mae'].value:>10.4f}{metriques['bias'].value:>10.4f}"
        )

    _titre("4.", "Comparaison appariée du modèle et de la persistance")
    reel: list[float] = []
    prevu_modele: list[float] = []
    prevu_reference: list[float] = []
    for pli in walk_forward(valeurs, initial_size=TAILLE_ENTRAINEMENT, step=1):
        reel.extend(pli.test)
        prevu_modele.extend(_prevoir(pli.train))
        prevu_reference.extend(persistence_forecast(pli.train, len(pli.test)))
    comparaison = compare_forecasts(reel, prevu_modele, prevu_reference)
    print(f"test        : {comparaison.test_name}")
    print(f"statistique : {comparaison.statistic:.4f}")
    print(f"p-valeur    : {comparaison.p_value:.4f}")
    print(f"paires      : {comparaison.n_pairs}")
    print(f"conclusion  : {comparaison.conclusion}")

    _titre("5.", "Grandeur dérivée, enregistrement et produit de connaissance")
    etat = DerivedVariable.from_result(
        result=issue.result,
        output="level",
        variable_id="etat-niveau-0001",
        quantity="niveau",
        unit="u",
        inputs=observations,
        uncertainty=Uncertainty.from_interval(
            "intervalle de confiance à 95 % sur l'état filtré",
            issue.result.intervals["level"][-1],
        ),
        valid_time=observations[-1].temporal.valid_time,
    )
    print(f"grandeur dérivée : {etat.variable_id}")
    print(f"nature           : {etat.nature} — l'état latent reconstruit, pas l'observation")
    print(f"calculée le      : {etat.temporal.known_at:%Y-%m-%d %H:%M:%S} (instant du calcul)")
    print(f"incertitude      : {etat.uncertainty.form.value} — {etat.uncertainty.statement}")

    enregistrement = build_record(
        issue,
        record_id="enregistrement-0001",
        input_observations=observations,
        evidence=[preuve],
        sources=[SOURCE],
        produced_at=issue.result.produced_at,
        evaluation=rapport.as_dict(),
        inputs=entree,
        derived_variables=[etat],
    )
    lignee = verify_lineage(enregistrement)
    print(f"enregistrement : {enregistrement.record_id}")
    print(f"lignée vérifiée : {lignee.ok} ({len(lignee.checks)} contrôles)")
    for probleme in lignee.problems:
        print(f"  écart : {probleme}")
    produit = enregistrement.to_product(
        product_id="produit-0001",
        version="1.0.0",
        status=ProductStatus.USABLE,
        domain_of_validity="séquence régulière, bruit de mesure gaussien de variance connue",
        uncertainty="variance d'observation déclarée ; incertitude de l'état filtré non calibrée",
    )
    print(f"produit     : {produit.product_id} v{produit.version}")
    print(f"nature      : {produit.nature} — ce n'est pas une observation")
    print(f"statut      : {produit.status}")
    print(f"lignée      : {len(produit.lineage)} références")
    for reference in produit.lineage[:6]:
        print(f"  {reference.kind.value:<12} {reference.identifier}")

    _titre("6.", "Rejouabilité")
    rejoue = reproduce(MODELE, entree, PARAMETRES, issue.config)
    identique = rejoue.outputs == issue.result.outputs
    print(f"empreinte de configuration : {issue.config.fingerprint()[:16]}…")
    print(f"résultat rejoué identique  : {identique}")
    print(f"temps d'exécution           : {issue.duration_seconds:.4f} s")


if __name__ == "__main__":
    main()
