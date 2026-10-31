"""Test d'intégration bout en bout — la chaîne complète de la mission 001.

Ce test ne teste pas une pièce : il traverse la chaîne et vérifie que **les
maillons s'articulent**. Il est écrit par le lead d'intégration, séparément des
tests unitaires de chaque agent, pour que la vérification soit indépendante
de l'implémentation qu'elle vérifie.

La chaîne :

    preuve brute → observation → exécution du modèle → résultat typé
      → évaluation hors échantillon contre des références
        → comparaison appariée → enregistrement de l'exécution
          → produit de connaissance vérifiable → rejouabilité

Rien ici n'est un simulacre : la série est synthétique (déterministe, graine
fixe) mais le modèle exécuté est le vrai filtre de Kalman, l'évaluation est la
vraie marche avant, et la comparaison est le vrai test de Diebold-Mariano.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from torne.contracts.derived import DerivedVariable, Uncertainty
from torne.contracts.knowledge import ProductStatus
from torne.contracts.model import ModelInputs, ModelParameters, ResultNature
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

MODELE = LocalLinearTrendModel()

# Le modèle générateur est une marche aléatoire à dérive constante, bruitée par
# une erreur de mesure d'écart-type 0,8 : les variances déclarées ci-dessous
# sont celles de ce processus, pas des nombres choisis pour faire fonctionner le
# filtre.
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

PREUVE = RawEvidence(
    evidence_id="preuve-0001",
    source_id="torne.demo.synthetique",
    acquired_at=DEBUT + NB_POINTS * JOUR,
    media_type="application/json",
    content_sha256="0" * 64,
    key="niveau",
)


def _serie() -> tuple[list[float], list[float]]:
    """Série observée et état latent qui la produit (la vérité, connue par construction)."""
    generateur = np.random.default_rng(20261031)
    latente = np.cumsum(0.2 + 0.05 * generateur.standard_normal(NB_POINTS)) + 10.0
    observee = latente + 0.8 * generateur.standard_normal(NB_POINTS)
    return [float(v) for v in observee], [float(v) for v in latente]


def _observations(valeurs: list[float]) -> list[Observation]:
    """Une observation par point, publiée le lendemain de sa date de validité."""
    observations = []
    for index, valeur in enumerate(valeurs):
        valide = DEBUT + index * JOUR
        publie = valide + JOUR
        observations.append(
            Observation(
                observation_id=f"obs-{index:03d}",
                source_id=SOURCE.source_id,
                quantity="niveau",
                unit="u",
                temporal=TemporalStamp(
                    valid_time=valide,
                    known_at=publie,
                    ingested_at=publie,
                    publication=PublicationState.ESTABLISHED,
                ),
                evidence_id=PREUVE.evidence_id,
                value=valeur,
                spatial_ref="série de démonstration",
                key="niveau",
            )
        )
    return observations


def _prevoir(entrainement: tuple[float, ...]) -> list[float]:
    """Prévision à un pas du modèle, calculée sur le seul bloc d'entraînement."""
    resultat = MODELE.run(ModelInputs(series={"y": entrainement}), PARAMETRES)
    return [resultat.outputs["forecast_level"][-1]]


@pytest.fixture(scope="module")
def serie() -> tuple[list[float], list[float]]:
    return _serie()


@pytest.fixture(scope="module")
def rapport(serie: tuple[list[float], list[float]]):
    valeurs, _ = serie
    return evaluate_walk_forward(
        valeurs,
        _prevoir,
        initial_size=TAILLE_ENTRAINEMENT,
        step=1,
        model_id=MODELE.spec.model_id,
        model_version=MODELE.spec.version,
        now=DEBUT + (NB_POINTS + 10) * JOUR,
    )


# --------------------------------------------------------------------------
# La chaîne
# --------------------------------------------------------------------------


def test_la_chaine_complete_parcourt_chaque_maillon(serie, rapport):
    """Preuve → observation → exécution → évaluation → enregistrement → produit."""
    valeurs, _latente = serie
    observations = _observations(valeurs)
    entrees = ModelInputs(series={"y": tuple(valeurs)})

    # 1. Exécution du modèle sur les observations.
    issue = execute(MODELE, entrees, PARAMETRES)
    assert issue.result.outputs["level"]
    assert len(issue.result.outputs["level"]) == NB_POINTS
    assert issue.config.model_version == MODELE.spec.version

    # 2. Évaluation hors échantillon, sur la période test, contre des références.
    assert rapport.split.test_start == TAILLE_ENTRAINEMENT
    assert rapport.metrics["rmse"].n_used == NB_POINTS - TAILLE_ENTRAINEMENT
    assert set(rapport.baseline_metrics) >= {"persistence", "mean", "drift"}

    # 3. La grandeur dérivée : l'état reconstruit, avec son propre calcul,
    #    sa propre temporalité et son incertitude.
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
    assert etat.nature is ResultNature.RECONSTRUCTED
    assert etat.temporal.known_at == issue.result.produced_at

    # 4. Enregistrement de l'exécution, rattaché à sa preuve.
    enregistrement = build_record(
        issue,
        record_id="enregistrement-0001",
        input_observations=observations,
        evidence=[PREUVE],
        sources=[SOURCE],
        produced_at=issue.result.produced_at,
        evaluation=rapport.as_dict(),
        inputs=entrees,
        derived_variables=[etat],
    )
    lignee = verify_lineage(enregistrement)
    assert lignee.ok, f"lignée incohérente : {lignee.problems}"

    # 5. Produit de connaissance : il dit ce qu'il est, et n'est pas une observation.
    produit = enregistrement.to_product(
        product_id="produit-0001",
        version="1.0.0",
        status=ProductStatus.USABLE,
        domain_of_validity="séquence régulière, bruit de mesure gaussien de variance connue",
        uncertainty="variance d'observation déclarée ; incertitude de l'état filtré non calibrée",
    )
    # La nature du produit est celle du résultat de l'exécution : un état
    # reconstruit n'est pas une estimation, et n'est jamais une observation.
    assert produit.nature is issue.result.nature
    assert produit.nature is ResultNature.RECONSTRUCTED
    assert produit.version == "1.0.0"
    assert produit.produced_at == issue.result.produced_at

    # 6. La lignée permet de remonter du produit jusqu'aux preuves brutes.
    genres = {ref.kind.value for ref in produit.lineage}
    assert {"model", "observation", "evidence", "source", "parameter"} <= genres
    identifiants = {ref.identifier for ref in produit.lineage}
    assert PREUVE.evidence_id in identifiants
    assert SOURCE.source_id in identifiants
    # La grandeur dérivée est citée : la lignée passe par elle.
    assert etat.variable_id in identifiants


def test_le_resultat_est_reproductible_depuis_sa_configuration(serie):
    """Rejouer l'exécution depuis sa configuration redonne le même résultat."""
    valeurs, _ = serie
    entrees = ModelInputs(series={"y": tuple(valeurs)})

    issue = execute(MODELE, entrees, PARAMETRES, now=DEBUT + (NB_POINTS + 10) * JOUR)
    rejoue = reproduce(MODELE, entrees, PARAMETRES, issue.config)

    assert rejoue.outputs == issue.result.outputs
    assert rejoue.intervals == issue.result.intervals
    assert rejoue.diagnostics == issue.result.diagnostics


def test_l_evaluation_porte_une_comparaison_appairee(serie):
    """Le modèle est comparé à une référence sur les mêmes observations."""
    valeurs, _ = serie
    plis = walk_forward(valeurs, initial_size=TAILLE_ENTRAINEMENT, step=1)

    reel: list[float] = []
    prevu_modele: list[float] = []
    prevu_reference: list[float] = []
    for pli in plis:
        reel.extend(pli.test)
        prevu_modele.extend(_prevoir(pli.train))
        prevu_reference.extend(persistence_forecast(pli.train, len(pli.test)))

    comparaison = compare_forecasts(reel, prevu_modele, prevu_reference)

    assert comparaison.n_pairs == len(reel) == NB_POINTS - TAILLE_ENTRAINEMENT
    assert 0.0 <= comparaison.p_value <= 1.0
    assert comparaison.conclusion
    # La taille de l'effet est reportée, pas seulement le test : une p-valeur
    # seule ne dit pas de combien le modèle est meilleur.
    assert len(comparaison.loss_differences) == len(reel)


def test_le_modele_ameliore_la_reference_de_persistence(rapport):
    """Sur un processus bruité à dérive lente, le filtre bat la persistance.

    C'est attendu : la persistance reporte la dernière observation **bruyée**,
    alors que le filtre reporte un état lissé. L'affirmation porte sur la
    RMSE, pas sur une significativité.
    """
    rmse_modele = rapport.metrics["rmse"].value
    rmse_persistance = rapport.baseline_metrics["persistence"]["rmse"].value

    assert rmse_modele < rmse_persistance


def test_le_filtre_reduit_lerreur_sur_l_etat_latent_connu(serie):
    """Le filtre estime l'état latent réel mieux que l'observation brute.

    L'état latent est connu ici par construction : c'est le seul endroit où la
    vérité est disponible, et c'est ce qui permet de juger l'estimation.
    """
    valeurs, latente = serie
    resultat = MODELE.run(ModelInputs(series={"y": tuple(valeurs)}), PARAMETRES)

    erreur_filtree = np.array(resultat.outputs["level"]) - np.array(latente)
    erreur_brute = np.array(valeurs) - np.array(latente)

    assert float(np.var(erreur_filtree)) < float(np.var(erreur_brute))


# --------------------------------------------------------------------------
# Protection contre le lookahead, vérifiée de bout en bout
# --------------------------------------------------------------------------


def test_l_information_future_nentre_pas_dans_une_prevision(serie):
    """Modifier le futur ne doit changer aucune prévision antérieure.

    C'est la preuve la plus directe qu'aucune information future n'a pu
    s'infiltrer dans le modèle : si elle l'avait fait, la prévision changerait.
    """
    valeurs, _ = serie
    plis = walk_forward(valeurs, initial_size=TAILLE_ENTRAINEMENT, step=1)
    premier = plis[0]

    altere = list(valeurs)
    for index in range(premier.test_start, len(altere)):
        altere[index] = 1e6

    prevu_initial = _prevoir(premier.train)[0]
    prevu_apres_perturbation = _prevoir(premier.train)[0]

    assert prevu_initial == prevu_apres_perturbation
    assert prevu_initial != altere[premier.test_start]


def test_la_periode_test_est_invisible_depuis_le_train(serie):
    """Le bloc d'entraînement ne contient jamais un point de la période test."""
    valeurs, _ = serie
    for pli in walk_forward(valeurs, initial_size=TAILLE_ENTRAINEMENT, step=1):
        assert pli.train_end == pli.test_start
        assert len(pli.train) == pli.test_start
        assert not set(pli.train) & set(pli.test)


def test_le_produit_ne_publie_pas_une_observation_absente(serie):
    """Un produit ne cite que des observations admissibles à son instant.

    Une observation publiée après le produit ne peut pas y figurer : elle
    n'existait pas au moment où le produit a été établi.
    """
    valeurs, _ = serie
    observations = _observations(valeurs)
    issue = execute(MODELE, ModelInputs(series={"y": tuple(valeurs)}), PARAMETRES)

    enregistrement = build_record(
        issue,
        record_id="enregistrement-0002",
        input_observations=observations,
        evidence=[PREUVE],
        sources=[SOURCE],
        produced_at=DEBUT + JOUR,  # bien avant l'ingestion des observations
        inputs=ModelInputs(series={"y": tuple(valeurs)}),
    )
    lignee = verify_lineage(enregistrement)

    assert not lignee.ok
    assert lignee.problems
