"""Vérification du comportement préservé des primitives reprises d'`athanor@6dacc87`.

Chaque test rejoue un **cas de référence d'Athanor** : mêmes données, mêmes
valeurs attendues, avec le fichier et la ligne d'origine cités en commentaire.
Le but n'est pas de re-tester une mathematics connue, mais de prouver que le
portage n'a rien changé au comportement.

L'écart qui avait été assumé — Athanor appelle `scipy.special.stdtr` pour la loi
de Student, TORNE la réimplémentait par la bêta incomplète régulière — a
disparu : `torne.methods.calibration` appelle désormais `scipy.stats.t.cdf`, et
`scipy` est une dépendance de runtime. Les valeurs de référence du test
`athanor/tests/test_calibration.py:91-99` (jeu `sleep` de R, test t apparié
publié) et `:161-182` (formes fermées et quantiles de table) sont donc
reproduites ici par cette voie, avec une précision supérieure.

Les références indépendantes ajoutees à la suite de l'audit.compare chaque
primitive à une bibliothèque établie : `scipy.stats` pour la loi de Student, la
loi de Kolmogorov et la régression linéaire, `statsmodels` pour la variance de
long terme HAC et l'erreur-type CR1 groupée. `statsmodels` est une dépendance
de développement seule : le paquet installé n'en dépend pas.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.sandwich_covariance import cov_hac, weights_bartlett

from torne.methods.breaks import bartlett_lags, cusum_break_test, kolmogorov_sf
from torne.methods.calibration import (
    Alternative,
    diebold_mariano,
    newey_west_variance,
    student_t_cdf,
)
from torne.methods.power import (
    mde_from_se,
    minimum_detectable_effect,
    power_at,
    required_units,
    z_alpha,
)
from torne.methods.regression import ols

# =====================================================================================================================
# OLS — `athanor/src/athanor/stats/regression.py`
# Référence de données : jeu `anscombe` de R (11 observations ; source Tufte
# 1990, d'après Anscombe 1973). Les jeux I, II et III sont identiques à la
# transcription du fichier de test d'Athanor `athanor/tests/test_t90_stats.py:21-22`.
# =====================================================================================================================

ANSCOMBE_X = (10, 8, 13, 9, 11, 14, 6, 4, 12, 7, 5)
ANSCOMBE_I = (8.04, 6.95, 7.58, 8.81, 8.33, 9.96, 7.24, 4.26, 10.84, 4.82, 5.68)
ANSCOMBE_II = (9.14, 8.14, 8.74, 8.77, 9.26, 8.10, 6.13, 3.10, 9.13, 7.26, 4.74)
ANSCOMBE_III = (7.46, 6.77, 12.74, 7.11, 7.81, 8.84, 6.08, 5.39, 8.15, 6.42, 5.73)
ANSCOMBE_IV_X = (8, 8, 8, 8, 8, 8, 8, 19, 8, 8, 8)
ANSCOMBE_IV = (6.58, 5.76, 7.71, 8.84, 8.47, 7.04, 5.25, 12.50, 5.56, 7.91, 6.89)


def _rss(x, y, intercept: float, slope: float) -> float:
    """Somme des carrés des résidus, recalculée à partir des coefficients."""
    residuals = np.asarray(y, float) - (intercept + slope * np.asarray(x, float))
    return float((residuals**2).sum())


def test_anscombe_jeux_publies_les_quatre_stats_reproduisent_le_referentiel():
    """Le quatuor d'Anscombe sur données réelles publiées.

    Valeurs **imprimées** par Anscombe (F. J. Anscombe, 1973, « Graphs in
    Statistical Analysis », *The American Statistician* 27(1), 17-21, p. 19) :
    n = 11, moyenne de x = 9,0, moyenne de y = 7,5, pente b1 = 0,5, droite
    `y = 3,00 + 0,50 x`, somme des carrés de x = 110,0, somme des carrés de la
    régression = 27,50, **somme des carrés des résidus = 13,75**, erreur type de
    la pente SE = 0,118, `Multiple R² = 0,667`.

    Les quatre jeux ont été publiés pour avoir **les mêmes** statistiques
    sommaires ; les valeurs ci-dessous sont celles calculées sur la
    transcription canonique à 11 observations, et non des valeurs recopiées.

    Tolérances : 1e-6 sur les coefficients, 1e-4 sur les sommes de carrés et
    les erreurs types.
    """
    jeux = (
        ("I", ANSCOMBE_X, ANSCOMBE_I),
        ("II", ANSCOMBE_X, ANSCOMBE_II),
        ("III", ANSCOMBE_X, ANSCOMBE_III),
        ("IV", ANSCOMBE_IV_X, ANSCOMBE_IV),
    )
    attendu = {
        # jeu : (moyenne x, moyenne y, SS x, pente, ordonnée, R², RSS, erreur type de pente)
        "I": (9.0, 7.500909, 110.0, 0.500091, 3.000091, 0.666542, 13.762690, 0.117906),
        "II": (9.0, 7.500909, 110.0, 0.500000, 3.000909, 0.666242, 13.776291, 0.117964),
        "III": (9.0, 7.500000, 110.0, 0.499727, 3.002455, 0.666324, 13.756192, 0.117878),
        "IV": (9.0, 7.500909, 110.0, 0.499909, 3.001727, 0.666707, 13.742490, 0.117819),
    }
    for nom, x, y in jeux:
        resultat = ols(x, y)
        moyenne_x, moyenne_y, ss_x, pente, ordonnee, r2, rss, erreur_type = attendu[nom]
        assert resultat.n == 11
        assert float(np.mean(x)) == pytest.approx(moyenne_x, abs=1e-6)
        assert float(np.mean(y)) == pytest.approx(moyenne_y, abs=1e-6)
        assert float(((np.asarray(x, float) - moyenne_x) ** 2).sum()) == pytest.approx(
            ss_x, abs=1e-6
        )
        assert resultat.slope == pytest.approx(pente, abs=1e-6)
        assert resultat.intercept == pytest.approx(ordonnee, abs=1e-6)
        assert resultat.r2 == pytest.approx(r2, abs=1e-6)
        assert resultat.slope_se == pytest.approx(erreur_type, abs=1e-4)
        assert _rss(x, y, resultat.intercept, resultat.slope) == pytest.approx(rss, abs=1e-4)


def test_anscombe_jeu_i_reproduit_les_valeurs_imprimees_par_anscombe():
    """Le jeu I, à lui seul, doit retrouver les valeurs imprimées par Anscombe.

    Référence : `athanor/tests/test_t90_stats.py:25-28` (mêmes assertions, en
    version Athanor) et l'imprimante d'Anscombe (1973, p. 19) citée ci-dessus.
    """
    resultat = ols(ANSCOMBE_X, ANSCOMBE_I)
    assert resultat.intercept == pytest.approx(3.0, abs=0.01)
    assert resultat.slope == pytest.approx(0.500, abs=0.001)
    assert resultat.slope_se == pytest.approx(0.118, abs=0.001)
    assert resultat.r2 == pytest.approx(0.667, abs=0.001)
    # Valeurs imprimées plus précisément : somme des carrés de x = 110,0 ;
    # somme des carrés de la régression = 27,50 ; résidus = 13,75.
    ss_x = float(((np.asarray(ANSCOMBE_X, float) - 9.0) ** 2).sum())
    assert ss_x == pytest.approx(110.0, abs=1e-6)
    assert resultat.slope * 55.01 == pytest.approx(27.50, abs=0.02)
    assert _rss(ANSCOMBE_X, ANSCOMBE_I, resultat.intercept, resultat.slope) == pytest.approx(
        13.75, abs=0.02
    )


def test_ols_refuse_les_entrees_incoherentes_et_ne_renvoie_nan_quand_non_estimable():
    """Cas limites d'`athanor/src/athanor/stats/regression.py:36-39`."""
    with pytest.raises(ValueError, match="tailles"):
        ols([1.0, 2.0], [1.0])
    trop_court = ols([1.0, 2.0], [1.0, 2.0])
    assert math.isnan(trop_court.slope)
    assert trop_court.n == 2
    x_constant = ols([1.0, 1.0, 1.0], [1.0, 2.0, 3.0])
    assert math.isnan(x_constant.slope)
    assert math.isnan(x_constant.r2)


def test_ols_avec_grappes_reproduit_la_definition_de_c1():
    """L'erreur-type CR1 par grappes, recalculée par sa définition.

    Définition appliquée : `sqrt(correction * somme_c (somme_t (x_t - moyenne_x) e_t)^2) / Sxx`
    avec `correction = C/(C-1) * (n-1)/(n-2)`.
    """
    rng = np.random.default_rng(11)
    n = 120
    clusters = np.repeat(np.arange(6, dtype=np.int64), n // 6)
    x = rng.normal(0.0, 1.0, n)
    y = 1.5 + 0.8 * x + rng.normal(0.0, 0.5, n) + np.repeat(rng.normal(0.0, 0.4, 6), n // 6)

    grappes = ols(x, y, clusters=clusters)

    xm, ym = float(x.mean()), float(y.mean())
    sxx = float(((x - xm) ** 2).sum())
    pente = float(((x - xm) * (y - ym)).sum()) / sxx
    residus = y - (ym - pente * xm + pente * x)
    scores = np.array(
        [
            float(((x[clusters == g] - xm) * residus[clusters == g]).sum())
            for g in np.unique(clusters)
        ]
    )
    correction = scores.size / (scores.size - 1) * (n - 1) / (n - 2)
    attendu = math.sqrt(correction * float((scores**2).sum())) / sxx

    assert grappes.slope_se == pytest.approx(attendu, rel=1e-12)
    # Avec un choc commun par grappe, l'erreur-type robuste est plus grande que
    # l'erreur-type homoscédastique.
    homoscedastique = ols(x, y)
    assert grappes.slope_se > homoscedastique.slope_se


# =====================================================================================================================
# Diebold-Mariano — `athanor/src/athanor/stats/calibration.py`
# =====================================================================================================================

# Données `sleep` (Cushny & Peebles 1905, reprises par Student 1908) : gain de
# sommeil, 10 patients, deux somnifères. Référence publiée : R,
# `t.test(extra ~ group, data = sleep, paired = TRUE)` — documentation du jeu
# `sleep` : t = -4,0621, df = 9, p = 0,002833.
# (`athanor/tests/test_calibration.py:24-26` et `:91-99`.)
SLEEP_1 = (0.7, -1.6, -0.2, -1.2, -0.1, 3.4, 3.7, 0.8, 0.0, 2.0)
SLEEP_2 = (1.9, 0.8, 1.1, 0.1, -0.1, 4.4, 5.5, 1.6, 4.6, 3.4)


def test_dm_sur_le_jeu_publie_sleep_vaut_le_test_t_apparie():
    """Cas de référence `athanor/tests/test_calibration.py:91-99` (valeurs publiées de R)."""
    resultat = diebold_mariano(SLEEP_1, SLEEP_2, alternative=Alternative.TWO_SIDED)
    assert resultat.statistic == pytest.approx(-4.0621, abs=1e-4)
    assert resultat.df == 9
    assert resultat.p_value == pytest.approx(0.002833, abs=1e-6)
    unilatéral = diebold_mariano(SLEEP_1, SLEEP_2, alternative=Alternative.LESS)
    assert unilatéral.p_value == pytest.approx(0.002833 / 2, abs=1e-6)


def test_variance_newey_west_calculee_a_la_main():
    """Cas de référence `athanor/tests/test_calibration.py:119-124`.

    x = 1..4 : gamma_0 = 1,25, gamma_1 = 0,3125, poids de Bartlett 1/2 ->
    1,25 + 2 x 0,5 x 0,3125 = 1,5625.
    """
    assert newey_west_variance([1.0, 2.0, 3.0, 4.0], 1) == pytest.approx(1.5625)
    assert newey_west_variance([1.0, 2.0, 3.0, 4.0], 0) == pytest.approx(1.25)
    with pytest.raises(ValueError, match="lag"):
        newey_west_variance([1.0], -1)


def test_dm_previsions_identiques_ne_donnent_aucune_preuve():
    """Cas de référence `athanor/tests/test_calibration.py:84-88`."""
    pertes = np.random.default_rng(1).random(50)
    for alternative in Alternative:
        resultat = diebold_mariano(pertes, pertes.copy(), alternative=alternative, lag=3)
        assert resultat.statistic == 0.0
        assert resultat.p_value == 1.0
        assert resultat.mean_diff == 0.0


def test_dm_est_antisymetrique():
    """Cas de référence `athanor/tests/test_calibration.py:102-107`."""
    rng = np.random.default_rng(2)
    a, b = rng.random(200), rng.random(200) + 0.05
    ab = diebold_mariano(a, b, lag=2)
    ba = diebold_mariano(b, a, lag=2, alternative=Alternative.GREATER)
    assert ab.statistic == pytest.approx(-ba.statistic)
    assert ab.p_value == pytest.approx(ba.p_value)


def test_dm_detecte_un_gagnant_net():
    """Cas de référence `athanor/tests/test_calibration.py:110-116`."""
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 500)
    bon = (np.where(y == 1, 0.8, 0.2) - y) ** 2
    piece = (np.full(500, 0.5) - y) ** 2
    assert diebold_mariano(bon, piece).p_value < 1e-6
    assert diebold_mariano(piece, bon).p_value > 0.99


def test_dm_hac_elargit_la_variance_sur_pertes_autocorrelees():
    """Cas de référence `athanor/tests/test_calibration.py:127-133`."""
    rng = np.random.default_rng(3)
    bruit = rng.normal(size=600)
    d = 0.1 + np.convolve(bruit, np.ones(5), mode="same")  # MA(4)
    naif = diebold_mariano(d, np.zeros(600), alternative=Alternative.GREATER, small_sample=False)
    hac = diebold_mariano(
        d, np.zeros(600), alternative=Alternative.GREATER, lag=4, small_sample=False
    )
    assert hac.variance > 2 * naif.variance
    assert hac.p_value > naif.p_value
    assert hac.df is None


def test_dm_avec_grappes_uniques_vaut_le_test_t_apparie():
    """Cas de référence `athanor/tests/test_calibration.py:136-149`."""
    rng = np.random.default_rng(4)
    a, b = rng.random(60), rng.random(60)
    simple = diebold_mariano(a, b, alternative=Alternative.TWO_SIDED)
    singleton = diebold_mariano(
        a, b, alternative=Alternative.TWO_SIDED, clusters=np.arange(60, dtype=np.int64)
    )
    assert singleton.statistic == pytest.approx(simple.statistic)
    assert singleton.p_value == pytest.approx(simple.p_value)

    groupes = np.repeat(np.arange(6, dtype=np.int64), 50)
    d = 0.05 + np.repeat(rng.normal(0.0, 0.3, 6), 50) + rng.normal(0.0, 0.05, 300)
    naif = diebold_mariano(d, np.zeros(300), alternative=Alternative.GREATER)
    groupe = diebold_mariano(d, np.zeros(300), alternative=Alternative.GREATER, clusters=groupes)
    assert groupe.df == 5
    assert groupe.p_value > naif.p_value


def test_dm_refuse_les_entrees_incoherentes():
    """Cas de référence `athanor/tests/test_calibration.py:152-156` et `:148-149`."""
    with pytest.raises(ValueError, match="longueur"):
        diebold_mariano([1.0, 2.0], [1.0])
    with pytest.raises(ValueError, match="2 observations"):
        diebold_mariano([1.0], [1.0])
    with pytest.raises(ValueError, match="exclusifs"):
        diebold_mariano([1.0, 2.0], [1.0, 2.0], lag=1, clusters=np.arange(2, dtype=np.int64))


def test_dm_avec_des_differences_de_pertes_constantes_donne_une_statistique_infinie():
    """Cas limite du portage, comportement d'Athanor conservé tel quel.

    Quand toutes les différences de pertes sont constantes et non nulles, la
    variance estimée des différences est nulle : la statistique est infinie et
    la p-valeur nulle. Ce comportement vient de
    `athanor/src/athanor/stats/calibration.py:205-208` et n'est pas modifié par
    le portage ; il est signalé ici pour qu'il ne soit pas pris pour un
    défaut de TORNE.
    """
    resultat = diebold_mariano([1.0, 2.0, 3.0], [0.0, 1.0, 2.0], alternative=Alternative.TWO_SIDED)
    assert math.isinf(resultat.statistic)
    assert resultat.statistic > 0
    assert resultat.p_value == 0.0


def test_dm_sans_retard_est_exactement_le_test_t_apparie_de_scipy():
    """Référence indépendante : le test apparié de `scipy.stats.ttest_rel`.

    À `lag = 0`, la correction de Harvey, Leybourne & Newbold (1997) réduit la
    statistique du test de Diebold-Mariano à la statistique t appariée, et la
    p-valeur à celle que donne `scipy.stats.ttest_rel`. La correspondance est
    exacte, au-delà de la simple proximité.
    """
    rng = np.random.default_rng(17)
    for n in (10, 30, 200):
        d = rng.normal(0.4, 1.0, size=n)
        resultat = diebold_mariano(d, np.zeros(n), alternative=Alternative.TWO_SIDED, lag=0)
        statistique, p_valeur = stats.ttest_rel(d, np.zeros(n))
        assert resultat.statistic == pytest.approx(statistique, abs=1e-12)
        assert resultat.p_value == pytest.approx(p_valeur, abs=1e-12)
        assert resultat.df == n - 1


def test_le_facteur_de_correction_de_petit_echantillon_est_publie():
    """Le facteur de Harvey, Leybourne & Newbold (1997) fait partie du résultat.

    Il est nécessaire pour que la puissance annoncée soit exprimée dans la
    même échelle que la statistique du test ; le module `power` s'en sert.
    """
    resultat = diebold_mariano(
        np.arange(20.0), np.zeros(20), alternative=Alternative.TWO_SIDED, lag=0
    )
    assert resultat.small_sample_factor == pytest.approx(math.sqrt(19 / 20), rel=1e-12)
    sans_correction = diebold_mariano(
        np.arange(20.0), np.zeros(20), alternative=Alternative.TWO_SIDED, small_sample=False
    )
    assert sans_correction.small_sample_factor == 1.0
    assert sans_correction.df is None


@pytest.mark.parametrize("t", [-7.0, -1.5, -0.3, 0.0, 0.4, 2.0, 12.0])
def test_loi_de_student_formes_fermees(t: float):
    """Cas de référence `athanor/tests/test_calibration.py:161-165`.

    df = 1 : Cauchy, F(t) = 1/2 + atan(t)/pi ; df = 2 : F(t) = 1/2 + t / (2 racine(2 + t²)).
    """
    assert student_t_cdf(t, 1) == pytest.approx(0.5 + math.atan(t) / math.pi, abs=1e-15)
    assert student_t_cdf(t, 2) == pytest.approx(0.5 + t / (2.0 * math.sqrt(2.0 + t * t)), abs=1e-15)


def test_loi_de_student_quantiles_de_table():
    """Cas de référence `athanor/tests/test_calibration.py:168-173`.

    Quantiles des tables usuelles (Abramowitz & Stegun, table 26.10) :
    t_{0,975; 10} = 2,228139, t_{0,995; 30} = 2,749996.

    L'écart résiduel de l'ordre de 1e-8 vient de l'arrondi à six décimales des
    quantiles publiés, non de l'implémentation.
    """
    assert student_t_cdf(2.228139, 10) == pytest.approx(0.975, abs=2e-8)
    assert student_t_cdf(-2.749996, 30) == pytest.approx(0.005, abs=2e-8)
    assert student_t_cdf(1.959964, 1e7) == pytest.approx(0.975, abs=2e-8)
    assert student_t_cdf(1.959964, math.inf) == pytest.approx(0.975, abs=2e-8)


# =====================================================================================================================
# CUSUM — `athanor/src/athanor/stats/breaks.py`
# =====================================================================================================================


@pytest.mark.parametrize(("critique", "niveau"), [(1.224, 0.10), (1.358, 0.05), (1.628, 0.01)])
def test_quantiles_critiques_publies_du_test_cusum(critique: float, niveau: float):
    """Cas de référence `athanor/tests/test_breaks.py:11-14`.

    Valeurs critiques du supremum du pont brownien (Kolmogorov ; Ploberger &
    Krämer 1992, table 1).
    """
    assert kolmogorov_sf(critique) == pytest.approx(niveau, abs=6e-4)


def test_cusum_fenetre_de_newey_west():
    """Cas de référence `athanor/tests/test_breaks.py:25-26`."""
    assert bartlett_lags(100) == 4
    assert bartlett_lags(16) == 2


def test_cusum_a_la_bonne_taille_sous_moyenne_constante():
    """Cas de référence `athanor/tests/test_breaks.py:29-32`."""
    rng = np.random.default_rng(3)
    rejets = sum(cusum_break_test(rng.normal(0.2, 1.0, 200)).p_value <= 0.05 for _ in range(400))
    assert 0.02 <= rejets / 400 <= 0.08


def test_cusum_detecte_et_localise_un_changement_de_moyenne():
    """Cas de référence `athanor/tests/test_breaks.py:35-40`."""
    rng = np.random.default_rng(4)
    x = np.concatenate([rng.normal(0.6, 1.0, 100), rng.normal(-0.2, 1.0, 100)])
    resultat = cusum_break_test(x)
    assert resultat.p_value < 0.01
    assert abs(resultat.break_index - 99) <= 15
    assert resultat.mean_before > 0.3
    assert resultat.mean_after < 0.1


def test_cusum_la_variance_de_long_terme_est_l_option_prudente():
    """Cas de référence `athanor/tests/test_breaks.py:43-48`."""
    rng = np.random.default_rng(5)
    bruit = rng.normal(0, 1, 400)
    x = np.convolve(bruit, np.ones(5) / 5, mode="same")
    simple, prudent = cusum_break_test(x), cusum_break_test(x, lags=None)
    assert prudent.lags == bartlett_lags(400)
    assert prudent.statistic < simple.statistic


def test_cusum_serie_trop_courte_ou_constante_n_est_pas_inferable():
    """Cas de référence `athanor/tests/test_breaks.py:51-55`."""
    assert np.isnan(cusum_break_test(np.ones(50)).p_value)
    assert np.isnan(cusum_break_test(np.arange(10.0)).p_value)
    with pytest.raises(ValueError, match="unidimensionnelle"):
        cusum_break_test(np.zeros((3, 3)))


# =====================================================================================================================
# Puissance — `athanor/src/athanor/stats/power.py`
# =====================================================================================================================


def test_k_mde_est_la_somme_des_tables():
    """Cas de référence `athanor/tests/test_power.py:28-33`.

    Tables de la loi normale : z(0,975) = 1,959964 ; z(0,80) = 0,841621 ;
    z(0,95) = 1,644854 ; z(0,90) = 1,281552.
    """
    assert mde_from_se(1.0) == pytest.approx(1.959964 + 0.841621, abs=1e-6)
    assert mde_from_se(1.0, alternative=Alternative.GREATER) == pytest.approx(
        1.644854 + 0.841621, abs=1e-6
    )
    assert mde_from_se(2.0, power=0.90) == pytest.approx(2 * (1.959964 + 1.281552), abs=1e-6)
    assert z_alpha(0.05, Alternative.LESS) == z_alpha(0.05, Alternative.GREATER)


def test_taille_d_echantillon_de_lehr():
    """Cas de référence `athanor/tests/test_power.py:36-44`.

    Lehr R. (1992), « Sixteen S-squared over D-squared », *Statistics in
    Medicine* 11:1099-1102 : n ≈ 16 sigma² / delta² par bras à 80 % de puissance.
    """
    assert required_units(1.0, math.sqrt(2.0)) == 16
    assert required_units(0.5, math.sqrt(2.0)) == 63
    brut_90 = 2 * (z_alpha(0.05) + 1.2815515655446004) ** 2
    assert brut_90 == pytest.approx(21.0, abs=0.05)
    assert required_units(1.0, math.sqrt(2.0), power=0.90) == math.ceil(brut_90)


def test_exemple_de_manuel_echantillon_unique():
    """Cas de référence `athanor/tests/test_power.py:47-52`.

    Exemple d'école (moyenne d'un échantillon, approximation normale) :
    delta / sigma = 0,5, alpha = 5 % bilatéral, 80 % -> n = 32 ; unilatéral -> 25.
    """
    assert required_units(0.5, 1.0) == 32
    assert required_units(0.5, 1.0, alternative=Alternative.GREATER) == 25


@pytest.mark.parametrize("alternative", [Alternative.GREATER, Alternative.TWO_SIDED])
@pytest.mark.parametrize(
    ("effet", "ecart_type", "deff"), [(0.03, 1.2, 1.0), (0.05, 2.5, 1.8), (0.2, 1.0, 4.6)]
)
def test_coherence_entre_n_mde_et_puissance(alternative, effet, ecart_type, deff):
    """Cas de référence `athanor/tests/test_power.py:57-64`."""
    n = required_units(effet, ecart_type, design_effect=deff, alternative=alternative)
    assert (
        minimum_detectable_effect(n, ecart_type, design_effect=deff, alternative=alternative)
        <= effet
    )
    assert (
        minimum_detectable_effect(n - 1, ecart_type, design_effect=deff, alternative=alternative)
        > effet
    )
    assert power_at(n, effet, ecart_type, design_effect=deff, alternative=alternative) >= 0.80
    assert (
        power_at(n - 1, effet, ecart_type, design_effect=deff, alternative=alternative)
        < 0.80 + 1e-3
    )


def test_puissance_a_effet_nul_vaut_alpha_et_le_sens_compte():
    """Cas de référence `athanor/tests/test_power.py:74-77`."""
    assert power_at(500, 0.0, 1.0) == pytest.approx(0.05)
    assert power_at(500, 0.0, 1.0, alternative=Alternative.GREATER) == pytest.approx(0.05)
    assert power_at(500, -0.2, 1.0, alternative=Alternative.GREATER) < 0.05
    assert power_at(500, -0.2, 1.0, alternative=Alternative.LESS) > 0.05


def test_puissance_refuse_les_parametres_invalides():
    """Cas de référence `athanor/tests/test_power.py:80-85`."""
    cas = (
        (lambda: required_units(0.0, 1.0), "effet visé"),
        (lambda: required_units(0.1, 0.0), "écart-type"),
        (lambda: required_units(0.1, 1.0, alpha=1.5), "alpha"),
        (lambda: minimum_detectable_effect(0, 1.0), "effectif"),
        (lambda: power_at(10, 0.1, 1.0, design_effect=0.0), "paramètres"),
        (lambda: mde_from_se(-1.0), "erreur-type"),
    )
    for appel, motif in cas:
        with pytest.raises(ValueError, match=motif):
            appel()


# =====================================================================================================================
# Références indépendantes — audit de la fondation scientifique
#
# Chaque primitive conservée est comparée à une bibliothèque établie. L'audit
# a conduit à une seule substitution : la loi de Student, réimplémentée en
# bibliothèque standard, est désormais celle de SciPy. Les autres primitives
# sont conservées telles quelles, leur comparaison mesurée avec les
# bibliothèques de référence ne montrant aucun écart significatif.
# =====================================================================================================================


def test_loi_de_student_est_celle_de_scipy():
    """Référence indépendante : `scipy.stats.t.cdf`.

    La grille couvre les degrés de liberté dégénérés (Cauchy, df = 2), les
    usuels et la limite normale (df infini). L'écart est nul à la précision
    machine : la primitive n'est pas réimplémentée.
    """
    for t in (-50.0, -7.0, -1.5, -0.3, 0.0, 0.4, 2.0, 12.0, 50.0):
        for df in (1, 2, 3, 10, 30, 1000, 1e7, math.inf):
            assert student_t_cdf(t, df) == pytest.approx(float(stats.t.cdf(t, df)), abs=1e-15)


def test_loi_de_kolmogorov_est_celle_de_scipy():
    """Référence indépendante : `scipy.stats.kstwobign.sf` (loi de Kolmogorov)."""
    for x in np.linspace(0.05, 5.0, 200):
        assert kolmogorov_sf(float(x)) == pytest.approx(float(stats.kstwobign.sf(x)), abs=1e-14)


def test_ols_est_celle_de_scipy():
    """Référence indépendante : `scipy.stats.linregress`.

    Pente, ordonnée à l'origine et erreur-type sont identiques à la précision
    machine : les moindres carrés ordinaires de TORNE n'apportent rien de
    moins juste que la bibliothèque de référence, et n'ont pas à la remplacer.
    """
    rng = np.random.default_rng(7)
    for _ in range(50):
        n = int(rng.integers(10, 60))
        x = rng.normal(size=n)
        y = 2.0 + 0.7 * x + rng.normal(size=n)
        resultat = ols(x, y)
        reference = stats.linregress(x, y)
        assert resultat.slope == pytest.approx(reference.slope, abs=1e-12)
        assert resultat.intercept == pytest.approx(reference.intercept, abs=1e-12)
        assert resultat.slope_se == pytest.approx(reference.stderr, abs=1e-12)


def test_variance_hac_est_celle_de_statsmodels():
    """Référence indépendante : `statsmodels.stats.sandwich_covariance.cov_hac`.

    Sur une régression sur constante, `cov_hac` renvoie la variance de la
    moyenne, soit la variance de long terme divisée par `n` : c'est la
    grandeur que le test de Diebold-Mariano utilise par observation.
    """
    rng = np.random.default_rng(11)
    for _ in range(50):
        n = int(rng.integers(20, 400))
        bruit = rng.normal(size=n)
        d = 0.3 + np.convolve(bruit, np.ones(4), mode="same") + rng.normal(size=n)
        lag = int(rng.integers(0, 12))
        modele = sm.OLS(d, np.ones((n, 1))).fit()
        reference = float(
            cov_hac(modele, nlags=lag, weights_func=weights_bartlett, use_correction=False)[0, 0]
        )
        assert newey_west_variance(d, lag) == pytest.approx(reference * n, rel=1e-12)


def test_erreur_type_cr1_est_celle_de_statsmodels():
    """Référence indépendante : `statsmodels` en covariance groupée (CR1).

    La correction CR1 de `statsmodels` — `G/(G-1) * (N-1)/(N-K)` — est celle
    que le module applique ; les deux erreurs-types coïncident à la précision
    machine.
    """
    rng = np.random.default_rng(3)
    for _ in range(30):
        n = int(rng.integers(40, 300))
        g = int(rng.integers(3, 15))
        grappes = np.repeat(np.arange(g), int(np.ceil(n / g)))[:n]
        n = grappes.size
        x = rng.normal(size=n)
        y = 2.0 + 0.6 * x + rng.normal(size=n)
        reference = sm.OLS(y, sm.add_constant(x)).fit(
            cov_type="cluster",
            cov_kwds={"groups": grappes, "use_correction": True, "df_correction": True},
        )
        assert ols(x, y, clusters=grappes).slope_se == pytest.approx(
            float(reference.bse[1]), rel=1e-12
        )


# =====================================================================================================================
# Cohérence de la puissance avec le test exécuté
# =====================================================================================================================


def test_la_puissance_annoncee_a_le_mde_vaut_la_puissance_cible():
    """La puissance annoncée est celle du test dont on annonce l'effet minimal.

    L'effet minimal détectable est défini comme l'effet qui donne exactement
    la puissance cible : la puissance doit donc, à cet effet, valoir la cible.
    La route Student le donne par construction ; la route normale le donne à
    l'approximation usuelle près (elle néglige la queue opposée).
    """
    for n in (12, 40, 200):
        for deff in (1.0, 2.5):
            mde_student = minimum_detectable_effect(
                n, 1.0, design_effect=deff, alpha=0.05, power=0.80, df=n - 1
            )
            puissance_student = power_at(
                n, mde_student, 1.0, design_effect=deff, alpha=0.05, df=n - 1
            )
            assert puissance_student == pytest.approx(0.80, abs=1e-9)

            mde_normal = minimum_detectable_effect(
                n, 1.0, design_effect=deff, alpha=0.05, power=0.80
            )
            puissance_normal = power_at(n, mde_normal, 1.0, design_effect=deff, alpha=0.05)
            assert puissance_normal == pytest.approx(0.80, abs=1e-5)


def test_la_route_student_tend_vers_l_approximation_normale():
    """Les deux routes décrivent le même test quand les degrés de liberté divergent.

    La route Student remplace la loi normale par la loi de Student : quand les
    degrés de liberté tendent vers l'infini, les deux routes coïncident — à
    l'approximation propre à la route normale près (qui néglige la queue
    opposée en bilatéral).
    """
    for n in (40, 500):
        mde_normal = minimum_detectable_effect(n, 1.0, alpha=0.05, power=0.80)
        mde_student = minimum_detectable_effect(n, 1.0, alpha=0.05, power=0.80, df=10**7)
        assert mde_student == pytest.approx(mde_normal, rel=1e-5)
        puissance_normal = power_at(n, 0.3, 1.0, alpha=0.05)
        puissance_student = power_at(n, 0.3, 1.0, alpha=0.05, df=10**7)
        assert puissance_student == pytest.approx(puissance_normal, abs=1e-6)


def test_l_ecart_entre_les_deux_routes_decroit_avec_l_effectif():
    """L'incohérence corrigée est réelle, et sa taille est mesurable.

    L'approximation normale annonçait un effet minimal détectable plus petit
    que celui du test de Student effectivement exécuté : elle était donc
    optimiste, de 16,7 % à n = 8 et de 5,4 % à n = 20. L'écart se referme quand
    l'effectif grandit, ce qui explique qu'il soit resté inaperçu.
    """
    ecarts = {
        n: minimum_detectable_effect(n, 1.0, alpha=0.05, power=0.80, df=n - 1)
        / minimum_detectable_effect(n, 1.0, alpha=0.05, power=0.80)
        - 1.0
        for n in (8, 20, 120, 500)
    }
    assert ecarts[8] == pytest.approx(0.167, abs=0.01)
    assert ecarts[20] == pytest.approx(0.054, abs=0.01)
    assert ecarts[120] < 0.01
    assert ecarts[500] < 0.005
    assert all(ecarts[n] > ecarts[m] for n, m in ((8, 20), (20, 120), (120, 500)))


def test_la_puissance_annoncee_encadre_la_puissance_reelle_du_test_de_diebold_mariano():
    """Vérification par simulation du lien entre la puissance annoncée et le test.

    Le test de Diebold-Mariano de TORNE est un test de Student à `n - 1` degrés
    de liberté, assorti de la correction de Harvey, Leybourne & Newbold (1997).
    La puissance annoncée doit donc décrire ce test. La simulation le confirme
    par un encadrement mesuré : la puissance annoncée sous la loi de Student
    est **conservatrice** (inférieure au taux de rejet empirique), tandis que
    celle de l'approximation normale — l'ancienne route — était **optimiste**
    (supérieure au taux de rejet empirique). Elle décrivait un test plus
    puissant que celui exécuté.

    La loi réelle du test est intermédiaire entre les deux : la variance de
    long terme y est estimée sur l'échantillon, ce qui élargit la loi de la
    statistique par rapport aux deux approximations.
    """
    rng = np.random.default_rng(20261031)
    n, mu, seuil = 30, 0.30, 0.05
    lag = bartlett_lags(n)
    repetitions = 3000
    rejets = 0
    for _ in range(repetitions):
        d = rng.normal(mu, 1.0, size=n)
        resultat = diebold_mariano(d, np.zeros(n), alternative=Alternative.TWO_SIDED, lag=lag)
        if resultat.p_value < seuil:
            rejets += 1
    empirique = rejets / repetitions

    facteur = diebold_mariano(
        np.full(n, mu), np.zeros(n), alternative=Alternative.TWO_SIDED, lag=lag
    ).small_sample_factor
    annoncee_student = power_at(
        n,
        mu * facteur,
        1.0,
        design_effect=1.0,
        alpha=seuil,
        alternative=Alternative.TWO_SIDED,
        df=n - 1,
    )
    annoncee_normale = power_at(
        n, mu, 1.0, design_effect=1.0, alpha=seuil, alternative=Alternative.TWO_SIDED
    )

    assert annoncee_student < empirique < annoncee_normale
    # L'erreur de Monte-Carlo (≈ 0,9 %) reste inférieure aux deux écarts mesurés.
    assert empirique - annoncee_student > 0.02
    assert annoncee_normale - empirique > 0.02
