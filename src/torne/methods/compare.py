"""Comparaison appariée d'une prévision à une référence, et rupture de régime.

Ce module répond à deux questions distinctes, sur les mêmes primitives
statistiques :

1. **Une prévision vaut-elle mieux qu'une référence ?** — test de Diebold-Mariano
   apparié (Diebold & Mariano 1995) sur les différences de pertes, avec variance
   de long terme HAC (Newey-West 1987) : l'appariement et la correction de
   l'autocorrélation sont le cœur de la méthode, pas un raffinement.
2. **Le régime a-t-il changé ?** — rupture de moyenne par CUSUM
   (Ploberger & Krämer 1992) sur les résidus.

Les primitives utilisées (`diebold_mariano`, `newey_west_variance`,
`cusum_break_test`, `power_at`, `minimum_detectable_effect`, `ols`) sont les
portages d'un dépôt historique privé, réécrits dans `torne.methods` : voir
l'en-tête de chaque module pour l'origine exacte (dépôt, commit, licence,
référence scientifique).

Prudence assumée
----------------
Un test sans puissance qui ne trouve rien n'est pas une absence d'effet : c'est
une absence de test. `compare_forecasts` distingue donc explicitement trois
conclusions — « différence détectée », « pas de différence détectée » et « pas de
puissance » — et ne dit jamais « significatif » sans préciser la taille de
l'effet mesurée.

La puissance et l'effet minimal détectable annoncés décrivent **le test
exécuté** : la même loi que celle de la p-valeur — Student à `n - 1` degrés de
liberté, avec la correction de Harvey, Leybourne & Newbold (1997) — et non
l'approximation normale, qui décrirait un autre test et annoncerait un effet
minimal détectable plus petit que celui que le test peut détecter.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .breaks import bartlett_lags, cusum_break_test
from .calibration import Alternative, diebold_mariano, newey_west_variance
from .power import minimum_detectable_effect, power_at
from .regression import ols

_ALPHA = 0.05
_TARGET_POWER = 0.80


@dataclass(frozen=True, slots=True)
class ComparisonReport:
    """Résultat d'une comparaison appariée de deux prévisions.

    `loss_differences` sont les pertes du modèle **moins** les pertes de la
    référence, observation par observation : leur moyenne est la taille de
    l'effet, et non seulement l'objet du test. `power` est la puissance du test
    à l'effet observé (`None` si elle n'est pas définissable).
    """

    test_name: str
    statistic: float
    p_value: float
    n_pairs: int
    conclusion: str
    loss_differences: tuple[float, ...]
    power: float | None = None


@dataclass(frozen=True, slots=True)
class RegimeChangeReport:
    """Résultat de la recherche d'une rupture de régime dans une série de résidus.

    `break_index` est le dernier indice du premier régime (l'argument de
    `cusum_break_test`) ; `-1` et des `NaN` signalent un test non applicable.
    """

    detected: bool
    statistic: float
    p_value: float
    break_index: int
    mean_before: float
    mean_after: float
    n_observations: int
    lags: int
    conclusion: str


def _losses(actual: np.ndarray, forecast: np.ndarray, loss: str) -> np.ndarray:
    """Pertes par observation : quadratique ou absolue."""
    errors = actual - forecast
    if loss == "squared":
        return errors**2
    if loss == "absolute":
        return np.abs(errors)
    raise ValueError(f"perte inconnue : « {loss} » (attendu « squared » ou « absolute »)")


def compare_forecasts(
    actual: Sequence[float],
    model_forecast: Sequence[float],
    baseline_forecast: Sequence[float],
    *,
    loss: str = "squared",
) -> ComparisonReport:
    """Compare une prévision à une référence, sur les **mêmes** observations.

    Test de Diebold-Mariano apparié sur les différences de pertes
    `d_t = perte_modèle(t) - perte_référence(t)`, avec variance de long terme
    HAC de Newey-West (fenêtre de Bartlett automatique de Newey & West 1994,
    `floor(4 (n/100)^(2/9))`). La correction de petit échantillon de Harvey,
    Leybourne & Newbold (1997) est conservée, comme dans le portage d'origine.

    La conclusion distingue trois cas, et jamais « significatif » sans la
    taille de l'effet :

    - « différence détectée » : l'effet observé est rejeté au seuil de 5 % ;
    - « pas de puissance » : l'écart observé est plus petit que le plus petit
      écart que ce test aurait pu détecter avec 80 % de puissance — l'absence
      de différence détectée ne dit alors rien de l'absence d'effet ;
    - « pas de différence détectée » : le test avait la puissance de voir un
      écart de cette taille, et n'en voit pas.
    """
    a = np.asarray(actual, dtype=np.float64)
    m = np.asarray(model_forecast, dtype=np.float64)
    b = np.asarray(baseline_forecast, dtype=np.float64)
    if a.ndim != 1 or m.ndim != 1 or b.ndim != 1:
        raise ValueError("actual, model_forecast et baseline_forecast doivent être des vecteurs 1D")
    if not a.size == m.size == b.size:
        raise ValueError(
            "actual, model_forecast et baseline_forecast doivent avoir la même longueur "
            f"({a.size}, {m.size}, {b.size})"
        )
    if a.size < 2:
        raise ValueError("au moins 2 observations appariées sont requises")
    if not (np.isfinite(a).all() and np.isfinite(m).all() and np.isfinite(b).all()):
        raise ValueError("les séries comparées contiennent une valeur non finie")

    losses_model = _losses(a, m, loss)
    losses_baseline = _losses(a, b, loss)
    differences = losses_model - losses_baseline
    n = int(a.size)
    lag = bartlett_lags(n)

    test = diebold_mariano(
        losses_model, losses_baseline, alternative=Alternative.TWO_SIDED, lag=lag
    )
    mean_diff = test.mean_diff
    mean_loss_model = float(losses_model.mean())
    mean_loss_baseline = float(losses_baseline.mean())

    # Puissance du test à l'effet observé : la variance HAC sert d'écart-type
    # effectif, et l'écart-type ordinaire des différences de pertes de « deff ».
    #
    # La puissance et l'effet minimal détectable décrivent **le test exécuté** :
    # même loi que celle de la p-value (Student à `test.df` degrés de liberté,
    # ou normale si la correction de petit échantillon est désactivée) et même
    # facteur de correction de Harvey, Leybourne & Newbold (1997). La statistique
    # du test vaut `mean_diff * facteur / erreur-type de la moyenne` : l'effet
    # porté par la non-centralité est donc l'écart moyen multiplié par ce
    # facteur, et l'effet minimal détectable se rapporte à l'écart moyen
    # lui-même — d'où la division par le facteur en aval.
    variance_iid = newey_west_variance(differences, 0)
    power: float | None = None
    mde = 0.0
    if variance_iid > 0.0:
        sd = math.sqrt(variance_iid)
        design_effect = test.variance / variance_iid
        facteur = test.small_sample_factor
        power = power_at(
            n,
            mean_diff * facteur,
            sd,
            design_effect=design_effect,
            alpha=_ALPHA,
            alternative=Alternative.TWO_SIDED,
            df=test.df,
        )
        mde = (
            minimum_detectable_effect(
                n,
                sd,
                design_effect=design_effect,
                alpha=_ALPHA,
                power=_TARGET_POWER,
                alternative=Alternative.TWO_SIDED,
                df=test.df,
            )
            / facteur
        )

    relative = ""
    if mean_loss_baseline > 0.0:
        relative = (
            f" ({100.0 * (mean_loss_model - mean_loss_baseline) / mean_loss_baseline:+.2f} % "
            "de la perte moyenne de la référence)"
        )

    if test.p_value < _ALPHA:
        direction = "inférieure" if mean_diff < 0 else "supérieure"
        conclusion = (
            f"différence détectée : la perte moyenne du modèle est {direction} à celle de la "
            f"référence de {abs(mean_diff):.6g} par observation{relative} "
            f"(p = {test.p_value:.4g}, test bilatéral, seuil {_ALPHA:g})"
        )
    elif power is None:
        conclusion = (
            "pas de différence détectée : les pertes du modèle et de la référence sont identiques "
            "sur toutes les observations appariées (aucune variance des différences)"
        )
    elif abs(mean_diff) < mde:
        conclusion = (
            "pas de puissance : l'écart moyen observé ("
            f"{abs(mean_diff):.6g}) est plus petit que le plus petit écart que ce test aurait pu "
            f"déceler avec {_TARGET_POWER:.0%} de puissance ({mde:.6g}) ; l'absence de différence "
            "détectée n'est pas une absence d'effet"
        )
    else:
        conclusion = (
            "pas de différence détectée : le test avait la puissance de voir un écart de cette "
            f"taille ({mde:.6g} à {_TARGET_POWER:.0%} de puissance) et n'en voit pas "
            f"(p = {test.p_value:.4g})"
        )

    return ComparisonReport(
        test_name=f"diebold_mariano_hac_{loss}",
        statistic=test.statistic,
        p_value=test.p_value,
        n_pairs=n,
        conclusion=conclusion,
        loss_differences=tuple(float(value) for value in differences),
        power=power,
    )


def detect_regime_change(
    residuals: Sequence[float], *, threshold: float = _ALPHA
) -> RegimeChangeReport:
    """Cherche un changement de régime dans une série de résidus (CUSUM).

    Le test retenu est l'OLS-CUSUM de Ploberger & Krämer (1992) : la
    statistique vaut `max |S_k| / (sigma_lr sqrt(n))` et sa loi asymptotique est
    celle du supremum du pont brownien. La variance de long terme est celle de
    Bartlett avec fenêtre automatique de Newey & West (1994) (`lags = None` dans
    le portage d'origine) : c'est l'option prudente sous autocorrélation, qui
    est le cas attendu des résidus d'un filtre.

    `threshold` est le seuil de décision **sur la p-valeur**. Un test non
    applicable (moins de 16 observations, série constante ou non finie) est
    rapporté comme tel, jamais comme une absence de rupture.
    """
    if not 0.0 < threshold < 1.0:
        raise ValueError(f"seuil hors de ]0, 1[ : {threshold}")
    values = np.asarray(residuals, dtype=np.float64)
    if values.ndim != 1:
        raise ValueError("les résidus doivent former un vecteur 1D")
    result = cusum_break_test(values, lags=None)
    applicable = not math.isnan(result.p_value)
    detected = bool(applicable and result.p_value <= threshold)

    if not applicable:
        conclusion = (
            "non concluante : le test CUSUM n'est pas applicable "
            f"({result.n_observations} observations, variance nulle ou série constante)"
        )
    elif detected:
        conclusion = (
            f"rupture de régime détectée à l'indice {result.break_index} : la moyenne des résidus "
            f"passe de {result.mean_before:.6g} à {result.mean_after:.6g} "
            f"(statistique = {result.statistic:.6g}, p = {result.p_value:.4g})"
        )
    else:
        conclusion = (
            f"aucune rupture de régime détectée (statistique = {result.statistic:.6g}, "
            f"p = {result.p_value:.4g} > {threshold:g}) ; un seuil plus bas détecterait plus "
            "vite, et un seuil plus haut exigerait un changement plus net"
        )

    return RegimeChangeReport(
        detected=detected,
        statistic=result.statistic,
        p_value=result.p_value,
        break_index=result.break_index,
        mean_before=result.mean_before,
        mean_after=result.mean_after,
        n_observations=result.n_observations,
        lags=result.lags,
        conclusion=conclusion,
    )


def ols_trend_forecast(values: Sequence[float], *, fit_length: int) -> tuple[float, ...]:
    """Prévision d'une tendance linéaire ajustée par moindres carrés.

    La tendance `y = a + b t` est ajustée sur les `fit_length` premières
    valeurs, puis appliquée à toute la série : les premières valeurs sont
    ajustées (in-sample), les suivantes sont des prévisions hors échantillon.
    C'est la **référence déterministe** contre laquelle une prévision
    (filtre, moyenne mobile…) peut être comparée.
    """
    v = np.asarray(values, dtype=np.float64)
    if v.ndim != 1 or v.size == 0:
        raise ValueError("values doit être un vecteur 1D non vide")
    if not np.isfinite(v).all():
        raise ValueError("values contient une valeur non finie")
    if not 3 <= fit_length <= v.size:
        raise ValueError(f"fit_length doit être compris entre 3 et {v.size} (reçu {fit_length})")
    times = np.arange(v.size, dtype=np.float64)
    fit = ols(times[:fit_length], v[:fit_length])
    if not math.isfinite(fit.slope) or not math.isfinite(fit.intercept):
        raise ValueError("la tendance n'est pas estimable sur cette fenêtre")
    return tuple(float(fit.intercept + fit.slope * t) for t in times)


__all__ = [
    "ComparisonReport",
    "RegimeChangeReport",
    "compare_forecasts",
    "detect_regime_change",
    "ols_trend_forecast",
]
