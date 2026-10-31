"""Vérifications scientifiques du filtre de Kalman en tendance linéaire locale.

Chaque résultat est confronté à une **référence indépendante** :

- une réécriture **scalaire** de la récursion de Kalman, écrite dans ce fichier
  et manipulant directement les trois éléments distincts de la covariance
  (aucune matrice 2x2 n'y apparaît) ;
- un cas à deux observations dont toutes les valeurs sont calculées **à la
  main** et commentées ;
- des propriétés statistiques vérifiées sur séries simulées à graine fixe
  (convergence, réduction de variance, calibration de l'intervalle prédictif) ;
- le déterminisme de l'exécution (la graine est ignorée par construction).
"""

from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np
import pytest

from torne.contracts.model import ModelInputs, ModelParameters, ResultNature
from torne.methods.compare import (
    compare_forecasts,
    detect_regime_change,
    ols_trend_forecast,
)
from torne.methods.kalman import LocalLinearTrendModel

MODELE = LocalLinearTrendModel()

# Quantile normal à 97,5 % : borne de l'intervalle prédictif à 95 %.
Z95 = NormalDist().inv_cdf(0.975)

# Série de référence fixe (non simulée) : croissance par paliers, avec un
# bruit de mesure et deux observations en dents de scie.
SERIE_REFERENCE = (2.0, 4.0, 3.5, 6.0, 7.25, 7.0, 9.5, 11.0, 10.5, 13.0)

PARAMETRES = {
    "measurement_variance": 1.0,
    "level_process_variance": 0.1,
    "slope_process_variance": 0.01,
}


def _executer(serie, **parametres):
    """Exécute le modèle sur une série et rend le résultat."""
    return MODELE.run(
        ModelInputs(series={"y": tuple(float(v) for v in serie)}),
        ModelParameters(values={**PARAMETRES, **parametres}),
    )


def _reference_filtre(serie, *, r, q_niveau, q_pente, niveau_initial, pente_initiale):
    """Réécriture scalaire de la récursion de Kalman (aucune matrice 2x2).

    La covariance est tenue par ses trois éléments distincts (p00, p01, p11) et
    la transition T = [[1, 1], [0, 1]] est appliquée par ses formules :

        (T P T')[0,0] = p00 + 2 p01 + p11
        (T P T')[0,1] = (T P T')[1,0] = p01 + p11
        (T P T')[1,1] = p11

    La mise à jour est celle du texte : P = (I - K Z) P prédite, avec
    Z = [1, 0], donc p00 <- a - K0 a, p01 <- b - K0 b, p11 <- c - K1 b.
    """
    p00, p01, p11 = r, 0.0, r
    niveau, pente = niveau_initial, pente_initiale
    niveaux: list[float] = []
    pentes: list[float] = []
    previsions: list[float] = []
    variances: list[float] = []
    for observation in serie:
        niveau_predit = niveau + pente
        a = p00 + 2.0 * p01 + p11 + q_niveau
        b = p01 + p11
        c = p11 + q_pente
        f = a + r
        innovation = observation - niveau_predit
        k0 = a / f
        k1 = b / f
        niveau = niveau_predit + k0 * innovation
        pente = pente + k1 * innovation
        p00 = a - k0 * a
        p01 = b - k0 * b
        p11 = c - k1 * b
        niveaux.append(niveau)
        pentes.append(pente)
        previsions.append(niveau + pente)
        variances.append(p00 + 2.0 * p01 + p11 + q_niveau + r)
    return niveaux, pentes, previsions, variances


# --- contrat du modèle -------------------------------------------------------------------------------------------


def test_le_modele_declare_son_identite_et_ses_hypotheses():
    """La spec doit porter une identité versionnée, des natures et un domaine de validité."""
    spec = MODELE.spec
    assert spec.model_id == "torne.methods.kalman.local_linear_trend"
    assert spec.version == "0.1.0"
    assert ResultNature.ESTIMATED in spec.natures
    assert ResultNature.PREDICTED in spec.natures
    assert spec.assumptions
    assert spec.domain_of_validity
    assert MODELE.required_parameters == (
        "measurement_variance",
        "level_process_variance",
        "slope_process_variance",
    )


def test_le_resultat_expose_les_sorties_nommees():
    """Les noms de sorties sont figés : niveau, pente, prévision, intervalle, diagnostics."""
    resultat = _executer(SERIE_REFERENCE)
    assert set(resultat.outputs) == {"level", "slope", "forecast_level"}
    assert set(resultat.intervals) == {"forecast_level"}
    assert len(resultat.outputs["level"]) == len(SERIE_REFERENCE)
    assert len(resultat.outputs["slope"]) == len(SERIE_REFERENCE)
    assert len(resultat.outputs["forecast_level"]) == len(SERIE_REFERENCE)
    assert len(resultat.intervals["forecast_level"]) == len(SERIE_REFERENCE)
    assert set(resultat.diagnostics) == {"n", "log_likelihood", "initial_level", "initial_slope"}
    assert resultat.diagnostics["n"] == len(SERIE_REFERENCE)
    assert resultat.diagnostics["initial_level"] == SERIE_REFERENCE[0]
    assert resultat.diagnostics["initial_slope"] == 0.0


# --- référence indépendante --------------------------------------------------------------------------------------


def test_la_recursion_de_reference_reproduit_le_filtre():
    """Le filtre doit coïncider avec la récursion scalaire écrite à part, à 1e-10."""
    resultat = _executer(SERIE_REFERENCE)
    niveaux, pentes, previsions, variances = _reference_filtre(
        SERIE_REFERENCE,
        r=PARAMETRES["measurement_variance"],
        q_niveau=PARAMETRES["level_process_variance"],
        q_pente=PARAMETRES["slope_process_variance"],
        niveau_initial=SERIE_REFERENCE[0],
        pente_initiale=0.0,
    )
    assert resultat.outputs["level"] == pytest.approx(niveaux, abs=1e-10)
    assert resultat.outputs["slope"] == pytest.approx(pentes, abs=1e-10)
    assert resultat.outputs["forecast_level"] == pytest.approx(previsions, abs=1e-10)

    # La variance prédictive n'est pas une sortie : elle se déduit de la
    # demi-largeur de l'intervalle à 95 %, qui vaut z * sigma.
    demi_largeurs = [(haut - bas) / 2.0 for bas, haut in resultat.intervals["forecast_level"]]
    variances_deduites = [(demi / Z95) ** 2 for demi in demi_largeurs]
    assert variances_deduites == pytest.approx(variances, abs=1e-10)


def test_cas_a_main_deux_observations():
    """Cas à deux observations, entièrement calculé à la main.

    Paramètres : R = 1, q_niveau = 0,1, q_pente = 0,01 ; série y = (2, 4) ;
    état initial (2, 0) — la première observation, convention par défaut — et
    covariance antérieure P = diag(R, R).

    Étape 0 (y_0 = 2) :
      P antérieure : p00 = p11 = 1, p01 = 0.
      P prédite = T P T' + Q = [[2, 1], [1, 1]] + [[0,1], [0, 0,01]]
                = [[2,1], [1, 1,01]] ;
      F = 2 + R = 3,1 ; innovation = 2 - (2 + 0) = 0 ;
      K = ([2, 1] / 3,1) = (0,677419..., 0,322581...) ;
      niveau = 2 + 0,677419... x 0 = 2 ; pente = 0 + 0,322581... x 0 = 0 ;
      covariance a posteriori : p00 = 2 - 0,677419... x 2 = 0,677419... ;
        p01 = 1 - 0,677419... x 1 = 0,322581... ;
        p11 = 1,01 - 0,322581... x 1 = 0,687419... ;
      variance prédictive de y_1 : (p00 + 2 p01 + p11 + 0,1) + R = 2,11 + 1 = 3,11.

    Étape 1 (y_1 = 4) :
      P prédite = [[2,11, 1,01], [1,01, 0,697419...]] ; F = 3,11 ;
      innovation = 4 - 2 = 2 ;
      K = ([2,11, 1,01] / 3,11) = (0,678457..., 0,324759...) ;
      niveau = 2 + 0,678457... x 2 = 3,356913... ;
      pente = 0 + 0,324759... x 2 = 0,649518... ;
      prévision de y_2 = niveau + pente = 4,006431... ;
      covariance a posteriori : p00 = 0,678457... ; p01 = 0,324758... ;
        p11 = 0,697419... - 0,324759... x 1,01 = 0,369413... ;
      variance prédictive : (0,678457... + 2 x 0,324758... + 0,369413... + 0,1) + 1
        = 2,797387...

    Vraisemblance gaussienne :
      logL = -1/2 [ log(2 pi x 3,1) + 0 / 3,1 + log(2 pi x 3,11) + 4 / 3,11 ]
           = -3,613976...
    """
    resultat = _executer((2.0, 4.0))
    assert resultat.outputs["level"] == pytest.approx((2.0, 3.356913183), abs=1e-9)
    assert resultat.outputs["slope"] == pytest.approx((0.0, 0.649517685), abs=1e-9)
    assert resultat.outputs["forecast_level"] == pytest.approx((2.0, 4.006430868), abs=1e-9)
    assert resultat.diagnostics["log_likelihood"] == pytest.approx(-3.613976302, abs=1e-9)

    # La variance prédictive de y_1 vaut 3,11 : la demi-largeur de l'intervalle
    # vaut z x racine(3,11) = 3,456434135...
    bas, haut = resultat.intervals["forecast_level"][0]
    assert (haut - bas) / 2.0 == pytest.approx(3.456434135, abs=1e-9)
    # Celle de y_2 vaut 2,797387... : demi-largeur 3,278116492...
    bas, haut = resultat.intervals["forecast_level"][1]
    assert (haut - bas) / 2.0 == pytest.approx(3.278116492, abs=1e-9)


# --- propriétés statistiques ------------------------------------------------------------------------------------


def test_un_signal_constant_converge_vers_sa_valeur():
    """Un niveau constant inconnu doit être retrouvé par le filtre.

    Le filtre est initialisé au loin de la vérité (niveau initial 0 pour un
    signal constant à 5) : la convergence n'est donc pas un artefact de
    l'initialisation.
    """
    resultat = _executer([5.0] * 60, initial_level=0.0, initial_slope=0.0)
    niveaux = resultat.outputs["level"]
    assert abs(niveaux[-1] - 5.0) < 1e-3
    assert abs(niveaux[-1] - 5.0) < abs(niveaux[0] - 5.0)
    assert abs(resultat.outputs["slope"][-1]) < 1e-3


def test_l_erreur_du_niveau_filtre_est_plus_faible_que_le_bruit_d_observation():
    """Le niveau filtré doit être plus juste que l'observation brute.

    Série simulée par le modèle lui-même (graine fixe) : la variance de l'erreur
    du niveau filtré (0,39 mesurée) est inférieure à la variance du bruit
    d'observation (0,98 mesurée).
    """
    graine = 20261031
    rng = np.random.default_rng(graine)
    r = 1.0
    q_niveau = 0.05
    q_pente = 0.01
    n = 400
    erreurs: list[float] = []
    bruits: list[float] = []
    for _ in range(60):
        niveau = float(rng.normal(0.0, math.sqrt(r)))
        pente = float(rng.normal(0.0, math.sqrt(r)))
        serie: list[float] = []
        niveaux_vrais: list[float] = []
        for _ in range(n):
            bruit = float(rng.normal(0.0, math.sqrt(r)))
            serie.append(niveau + bruit)
            niveaux_vrais.append(niveau)
            bruits.append(bruit)
            niveau = niveau + pente + float(rng.normal(0.0, math.sqrt(q_niveau)))
            pente = pente + float(rng.normal(0.0, math.sqrt(q_pente)))
        resultat = _executer(
            serie,
            measurement_variance=r,
            level_process_variance=q_niveau,
            slope_process_variance=q_pente,
            initial_level=0.0,
            initial_slope=0.0,
        )
        erreurs.extend(
            float(a) - float(b)
            for a, b in zip(resultat.outputs["level"], niveaux_vrais, strict=True)
        )
    variance_erreur = float(np.var(erreurs))
    variance_bruit = float(np.var(bruits))
    assert variance_erreur < variance_bruit
    assert variance_erreur < 0.75 * variance_bruit


def test_intervalle_predictif_couvre_environ_95_pour_cent():
    """Calibration de l'intervalle prédictif à 95 %.

    Série simulée par le modèle lui-même, avec un état initial tiré de la loi
    antérieure que le filtre suppose (niveau et pente de variance R) : le
    filtre est alors le filtre de Bayes exact du modèle simulé, et chaque
    intervalle doit couvrir 95 % des observations suivantes.

    La tolérance de +/- 2 points est large devant l'erreur de Monte-Carlo :
    l'écart-type de la couverture moyenne sur 200 répétitions est d'environ
    0,0008 (écart-type d'une répétition 0,0105 divisé par la racine de 200), soit
    plus de vingt-cinq écarts-types. Un échec de ce test ne peut donc pas venir
    du seul hasard de simulation.
    """
    graine = 20261031
    rng = np.random.default_rng(graine)
    r = 1.0
    q_niveau = 0.05
    q_pente = 0.01
    n = 200
    couvertures: list[float] = []
    for _ in range(200):
        niveau = float(rng.normal(0.0, math.sqrt(r)))
        pente = float(rng.normal(0.0, math.sqrt(r)))
        serie: list[float] = []
        for _ in range(n):
            serie.append(niveau + float(rng.normal(0.0, math.sqrt(r))))
            niveau = niveau + pente + float(rng.normal(0.0, math.sqrt(q_niveau)))
            pente = pente + float(rng.normal(0.0, math.sqrt(q_pente)))
        resultat = _executer(
            serie,
            measurement_variance=r,
            level_process_variance=q_niveau,
            slope_process_variance=q_pente,
            initial_level=0.0,
            initial_slope=0.0,
        )
        intervalles = resultat.intervals["forecast_level"]
        touches = [
            1.0 if bas <= serie[t + 1] <= haut else 0.0
            for t, (bas, haut) in enumerate(intervalles[:-1])
        ]
        couvertures.append(float(np.mean(touches)))
    couverture = float(np.mean(couvertures))
    assert 0.93 <= couverture <= 0.97


# --- déterminisme et validité -----------------------------------------------------------------------------------


def test_deux_executions_identiques_donnent_le_meme_resultat():
    """Le modèle est déterministe, et la graine n'y change rien (elle est ignorée)."""
    premier = _executer(SERIE_REFERENCE)
    second = _executer(SERIE_REFERENCE)
    assert premier.outputs == second.outputs
    assert premier.intervals == second.intervals
    assert premier.diagnostics == second.diagnostics

    avec_graine = MODELE.run(
        ModelInputs(series={"y": SERIE_REFERENCE}),
        ModelParameters(values=PARAMETRES),
        seed=1234,
    )
    assert avec_graine.outputs == premier.outputs
    assert avec_graine.intervals == premier.intervals


def test_les_entrees_invalides_sont_refusees():
    """Une entrée absente, une variance hors domaine ou un paramètre inconnu sont refusés."""
    with pytest.raises(ValueError, match="y"):
        MODELE.run(ModelInputs(series={}), ModelParameters(values=PARAMETRES))
    with pytest.raises(ValueError, match="y"):
        MODELE.run(ModelInputs(series={"y": ()}), ModelParameters(values=PARAMETRES))
    with pytest.raises(ValueError, match="y"):
        MODELE.run(
            ModelInputs(series={"y": (1.0, float("nan"))}), ModelParameters(values=PARAMETRES)
        )
    with pytest.raises(ValueError, match="measurement_variance"):
        _executer(SERIE_REFERENCE, measurement_variance=0.0)
    with pytest.raises(ValueError, match="measurement_variance"):
        _executer(SERIE_REFERENCE, measurement_variance=-1.0)
    with pytest.raises(ValueError, match="level_process_variance"):
        _executer(SERIE_REFERENCE, level_process_variance=-0.1)
    with pytest.raises(ValueError, match="slope_process_variance"):
        _executer(SERIE_REFERENCE, slope_process_variance=-0.1)
    with pytest.raises(ValueError, match="inconnu"):
        _executer(SERIE_REFERENCE, variance_du_bruit=1.0)
    with pytest.raises(ValueError, match="absent"):
        MODELE.run(
            ModelInputs(series={"y": (1.0, 2.0)}),
            ModelParameters(values={"measurement_variance": 1.0}),
        )
    with pytest.raises(ValueError, match="fini"):
        _executer(SERIE_REFERENCE, measurement_variance=float("inf"))


# --- comparaison à une référence et rupture de régime ------------------------------------------------------------


def test_compare_forecasts_detecte_un_modele_nettement_meilleur():
    """Un modèle franchement meilleur doit être détecté, avec la taille de l'effet.

    La conclusion ne dit jamais « significatif » seule : elle donne l'écart moyen
    des pertes et la part de la perte moyenne de la référence.
    """
    reel = (2.0, 4.0, 3.0, 5.0, 4.5, 6.0, 7.0, 6.5, 8.0, 9.0)
    modele = tuple(reel)
    reference = tuple(valeur + 1.0 + 0.01 * i for i, valeur in enumerate(reel))

    rapport = compare_forecasts(reel, modele, reference)

    assert rapport.test_name == "diebold_mariano_hac_squared"
    assert rapport.n_pairs == len(reel)
    assert rapport.p_value < 1e-6
    assert rapport.statistic < 0.0  # le modèle perd moins que la référence
    assert len(rapport.loss_differences) == len(reel)
    assert "différence détectée" in rapport.conclusion
    assert "inférieure" in rapport.conclusion
    assert rapport.power is not None
    assert rapport.power > 0.95

    # La perte absolue est aussi testée : mêmes conclusions, nom de test distinct.
    rapport_absolu = compare_forecasts(reel, modele, reference, loss="absolute")
    assert rapport_absolu.test_name == "diebold_mariano_hac_absolute"
    assert rapport_absolu.p_value < 1e-6


def test_compare_forecasts_signale_le_manque_de_puissance():
    """Un écart trop petit pour être vu ne doit pas être lu comme une absence d'effet.

    Huit observations appariées, un écart moyen des pertes de 0,0026 et un
    plus petit écart décelable avec 80 % de puissance de 0,0028 : le test n'a
    pas la puissance de voir cet effet, et le dit.
    """
    rng = np.random.default_rng(42)
    reel = [float(v) for v in np.arange(1.0, 13.0)][:8]
    reference = list(reel)
    modele = [v + float(b) for v, b in zip(reel, rng.normal(0.0, 0.05, 8), strict=True)]

    rapport = compare_forecasts(reel, modele, reference)

    assert rapport.p_value >= 0.05
    assert "pas de puissance" in rapport.conclusion
    assert rapport.power is not None
    assert rapport.power < 0.80


def test_compare_forecasts_signale_des_previsions_identiques():
    """Deux prévisions identiques ne donnent aucune preuve, ni dans un sens ni dans l'autre."""
    reel = [float(v) for v in np.arange(1.0, 13.0)]
    rapport = compare_forecasts(reel, reel, reel)
    assert rapport.statistic == 0.0
    assert rapport.p_value == 1.0
    assert rapport.power is None
    assert "identiques" in rapport.conclusion


def test_compare_forecasts_refuse_les_series_incoherentes():
    """Longueurs différentes, séries trop courtes, valeurs non finies : tout est refusé."""
    reel = [1.0, 2.0, 3.0, 4.0]
    with pytest.raises(ValueError, match="longueur"):
        compare_forecasts(reel, reel[:3], reel)
    with pytest.raises(ValueError, match="2 observations"):
        compare_forecasts([1.0], [1.0], [1.0])
    with pytest.raises(ValueError, match="finie"):
        compare_forecasts([1.0, float("nan")], [1.0, 2.0], [1.0, 2.0])
    with pytest.raises(ValueError, match="perte inconnue"):
        compare_forecasts(reel, reel, reel, loss="log")


def test_detect_regime_change_detecte_une_rupture():
    """Un changement de régime net doit être localisé."""
    rng = np.random.default_rng(7)
    residus = np.concatenate([rng.normal(0.0, 1.0, 100), rng.normal(5.0, 1.0, 100)])

    rapport = detect_regime_change(residus)

    assert rapport.detected
    assert rapport.p_value < 0.01
    assert abs(rapport.break_index - 99) <= 15
    assert rapport.mean_before < 1.0
    assert rapport.mean_after > 3.0
    assert "rupture de régime détectée" in rapport.conclusion


def test_detect_regime_change_ne_conclut_pas_quand_le_test_est_inapplicable():
    """Une série trop courte ne doit pas être lue comme « aucune rupture »."""
    rapport = detect_regime_change([0.1, -0.2, 0.3])
    assert not rapport.detected
    assert math.isnan(rapport.p_value)
    assert "non concluante" in rapport.conclusion
    with pytest.raises(ValueError, match="seuil"):
        detect_regime_change([0.1, -0.2, 0.3], threshold=0.0)


def test_ols_trend_forecast_retrouve_une_tendance_lineaire():
    """La référence déterministe (tendance OLS) doit retrouver une droite connue."""
    valeurs = [2.0 + 3.0 * t for t in range(10)]
    prevision = ols_trend_forecast(valeurs, fit_length=5)
    assert len(prevision) == len(valeurs)
    assert prevision == pytest.approx(tuple(valeurs), abs=1e-9)
    with pytest.raises(ValueError, match="fit_length"):
        ols_trend_forecast(valeurs, fit_length=2)
