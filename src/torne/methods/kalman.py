"""Filtre de Kalman en espace d'état : tendance linéaire locale.

Le modèle reconstruit un **état latent** — un niveau et une pente — à partir
d'une série observée bruitée, et publie une prévision à un pas de l'observation
suivante, assortie de son intervalle prédictif.

Modèle
------
    y_t         = mu_t + eps_t,            eps_t ~ N(0, R)
    mu_{t+1}    = mu_t + beta_t + eta_t,    eta_t ~ N(0, q_mu)
    beta_{t+1}  = beta_t + zeta_t,         zeta_t ~ N(0, q_beta)

soit, en matrices (état `alpha_t = (mu_t, beta_t)`) :

    alpha_{t+1} = T alpha_t + w_t,   T = [[1, 1], [0, 1]],   Q = diag(q_mu, q_beta)
    y_t         = Z alpha_t + eps_t,   Z = [1, 0],          H = R

`R` est `measurement_variance`, `q_mu` est `level_process_variance` et `q_beta`
est `slope_process_variance`. Les innovations du niveau et de la pente sont
indépendantes : c'est une convention de paramétrage explicite, choisie pour que
les trois variances soient identifiables séparément.

Référence scientifique
----------------------
Durbin, J. & Koopman, S. J. (2012), *Time Series Analysis by State Space
Methods*, 2e éd., Oxford University Press — chapitre 4, « Filtering, smoothing
and forecasting » (§4.3 « Filtering » : dérivation et récursion du filtre de
Kalman) ; le **modèle** de tendance linéaire locale est posé au chapitre 3,
§3.2.1 « Trend component ».

Initialisation
--------------
L'état initial est centré sur `initial_level` (par défaut la première
observation) et `initial_slope` (par défaut 0), avec une covariance antérieure
`diag(R, R)` : l'état initial est donc supposé connu à la précision d'une
mesure. C'est une **convention explicite**, pas une estimation : elle est
documentée ici, vérifiée par le test de référence et appliquée à l'identique à
chaque exécution. L'innovation à t = 0 est nulle par construction (l'état
initial est centré sur y_0) ; le filtre n'apprend qu'à partir de t = 1.

Déterminisme
------------
Le modèle ne tire aucun nombre aléatoire : `seed` est accepté par la signature
du contrat et **ignoré**. Deux exécutions sur les mêmes entrées et les mêmes
paramètres donnent exactement le même résultat. Aucun état global de `numpy` n'est
utilisé.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import NormalDist

import numpy as np

from ..contracts.model import (
    ModelInputs,
    ModelParameters,
    ModelResult,
    ModelSpec,
    ResultNature,
)

# Quantile normal à 97,5 % : borne de l'intervalle prédictif à 95 %.
_Z_95 = NormalDist().inv_cdf(0.975)

_SERIES_NAME = "y"


@dataclass(frozen=True, slots=True)
class _Settings:
    """Paramètres d'une exécution, une fois validés."""

    measurement_variance: float
    level_process_variance: float
    slope_process_variance: float
    initial_level: float
    initial_slope: float


def _as_float(value: object, name: str) -> float:
    """Convertit un paramètre en flottant fini, ou refuse l'entrée."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"le paramètre « {name} » doit être un nombre, reçu {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"le paramètre « {name} » doit être fini, reçu {value!r}")
    return number


def _filter(
    y: np.ndarray,
    *,
    settings: _Settings,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
    """Récursion du filtre de Kalman.

    Renvoie niveaux, pentes, variances d'état filtrées, prévisions, variances
    prédictives et vraisemblance.
    """
    r = settings.measurement_variance
    transition = np.array([[1.0, 1.0], [0.0, 1.0]])
    observation = np.array([1.0, 0.0])
    process = np.diag([settings.level_process_variance, settings.slope_process_variance])
    identity = np.eye(2)

    state = np.array([settings.initial_level, settings.initial_slope])
    covariance = np.diag([r, r])

    n = int(y.size)
    levels = np.empty(n, dtype=np.float64)
    slopes = np.empty(n, dtype=np.float64)
    state_variances = np.empty(n, dtype=np.float64)
    forecasts = np.empty(n, dtype=np.float64)
    forecast_variances = np.empty(n, dtype=np.float64)
    log_likelihood = 0.0

    for t in range(n):
        # Prédiction : l'état advance d'un pas, le bruit de processus s'y ajoute.
        predicted_state = transition @ state
        predicted_covariance = transition @ covariance @ transition.T + process

        # Mise à jour : l'observation corrige l'état prédit.
        innovation = float(y[t] - observation @ predicted_state)
        innovation_variance = float(observation @ predicted_covariance @ observation.T) + r
        gain = (predicted_covariance @ observation) / innovation_variance
        state = predicted_state + gain * innovation
        covariance = (identity - np.outer(gain, observation)) @ predicted_covariance

        levels[t] = float(state[0])
        slopes[t] = float(state[1])
        # Variance **de l'état filtré** : c'est l'incertitude de l'état
        # reconstruit, distincte de la variance de l'observation (qui porte en
        # plus le bruit de mesure). C'est elle qui permet d'annoncer un
        # intervalle sur l'état reconstruit.
        state_variances[t] = float(covariance[0, 0])

        # Prévision à un pas : moyenne et variance prédictives de y_{t+1}.
        next_state = transition @ state
        next_covariance = transition @ covariance @ transition.T + process
        forecasts[t] = float(observation @ next_state)
        forecast_variances[t] = float(observation @ next_covariance @ observation.T) + r

        log_likelihood += -0.5 * (
            math.log(2.0 * math.pi * innovation_variance)
            + innovation * innovation / innovation_variance
        )

    return levels, slopes, state_variances, forecasts, forecast_variances, log_likelihood


class LocalLinearTrendModel:
    """Modèle de tendance linéaire locale (filtrage d'état par filtre de Kalman).

    Le modèle s'exécute par `run` ; il n'a aucun état entre deux exécutions.
    """

    required_parameters: tuple[str, ...] = (
        "measurement_variance",
        "level_process_variance",
        "slope_process_variance",
    )
    optional_parameters: tuple[str, ...] = ("initial_level", "initial_slope")

    @property
    def spec(self) -> ModelSpec:
        """Identité, question, hypothèses et domaine de validité du modèle."""
        return ModelSpec(
            model_id="torne.methods.kalman.local_linear_trend",
            version="0.1.0",
            question="Quel est l'état latent (niveau et pente) d'une série observée, et quelle "
            "valeur peut-on prévoir pour l'observation suivante ?",
            method="Filtre de Kalman en espace d'état, tendance linéaire locale "
            "(Durbin & Koopman 2012, chap. 3 §3.2.1 et chap. 4 §4.3)",
            natures=(ResultNature.RECONSTRUCTED, ResultNature.PREDICTED),
            assumptions=(
                "Le système latent suit une tendance linéaire locale : le niveau avance de la pente "
                "courante, la pente dérive aléatoirement.",
                "Le bruit d'observation est gaussien, de variance constante (variance de mesure).",
                "Les innovations de niveau et de pente sont indépendantes et gaussiennes.",
                "La variance de mesure est connue : elle n'est pas estimée par ce modèle.",
                "Les observations sont régulièrement espacées et leur ordre est le temps.",
            ),
            domain_of_validity="Série numérique scalaire, régulièrement espacée, de longueur suffisante "
            "(au moins 2 observations) ; l'état latent est supposé lisse et dérivant lentement. "
            "Le modèle ne dit rien d'un régime de rupture : il l'absorbe dans la pente.",
        )

    def run(
        self,
        inputs: ModelInputs,
        params: ModelParameters,
        *,
        seed: int | None = None,
    ) -> ModelResult:
        """Exécute le filtre sur la série `y`.

        `seed` est accepté pour respecter la signature du contrat et **ignoré** :
        le modèle est entièrement déterministe.

        Le résultat est de nature `RECONSTRUCTED` : le niveau et la pente filtrés
        **reconstruisent** l'état latent de la série observée, à partir des
        observations et d'un modèle d'état — ils ne sont pas une observation,
        qui a son propre objet et son propre statut de qualité. `forecast_level`
        est la **moyenne prédictive** de l'observation suivante, qualifiée par
        `intervals["forecast_level"]` ; la nature `PREDICTED` est déclarée par la
        spec, qui annonce les deux natures produites par ce modèle, et chaque
        sortie porte la sienne.
        """
        del seed  # le modèle ne tire aucun aléa : la graine n'a rien à piloter.
        series = inputs.series.get(_SERIES_NAME)
        if series is None:
            raise ValueError(
                f"la série « {_SERIES_NAME} » est absente des entrées "
                f"(séries présentes : {sorted(inputs.series)})"
            )
        if len(series) == 0:
            raise ValueError(f"la série « {_SERIES_NAME} » est vide")
        y = np.asarray(series, dtype=np.float64)
        if not np.isfinite(y).all():
            raise ValueError(f"la série « {_SERIES_NAME} » contient une valeur non finie")

        settings = self._settings(params, default_initial_level=float(y[0]))
        levels, slopes, state_variances, forecasts, variances, log_likelihood = _filter(
            y, settings=settings
        )

        intervals = tuple(
            (forecast - _Z_95 * math.sqrt(variance), forecast + _Z_95 * math.sqrt(variance))
            for forecast, variance in zip(forecasts, variances, strict=True)
        )
        # Intervalle de confiance sur l'**état reconstruit** : il porte la
        # variance de l'état filtré, non celle de l'observation. Il ne contient
        # donc pas l'observation elle-même — il contient l'état latent.
        state_intervals = tuple(
            (level - _Z_95 * math.sqrt(variance), level + _Z_95 * math.sqrt(variance))
            for level, variance in zip(levels, state_variances, strict=True)
        )
        return ModelResult(
            spec=self.spec,
            nature=ResultNature.RECONSTRUCTED,
            parameters=params,
            produced_at=datetime.now(UTC),
            outputs={
                "level": tuple(float(value) for value in levels),
                "slope": tuple(float(value) for value in slopes),
                "forecast_level": tuple(float(value) for value in forecasts),
            },
            output_natures={
                "level": ResultNature.RECONSTRUCTED,
                "slope": ResultNature.RECONSTRUCTED,
                "forecast_level": ResultNature.PREDICTED,
            },
            intervals={
                "forecast_level": intervals,
                "level": state_intervals,
            },
            diagnostics={
                "n": int(y.size),
                "log_likelihood": float(log_likelihood),
                "initial_level": settings.initial_level,
                "initial_slope": settings.initial_slope,
            },
        )

    def _settings(self, params: ModelParameters, *, default_initial_level: float) -> _Settings:
        """Valide les paramètres : présence, type, domaine de validité.

        `initial_level` vaut par défaut la première observation ;
        `initial_slope` vaut 0 par défaut.
        """
        values = params.as_dict()
        known = set(self.required_parameters) | set(self.optional_parameters)
        unknown = sorted(set(values) - known)
        if unknown:
            raise ValueError(
                f"paramètre(s) inconnu(s) pour le modèle {self.spec.model_id} : {', '.join(unknown)} ; "
                f"paramètres acceptés : {', '.join(sorted(known))}"
            )
        missing = [name for name in self.required_parameters if name not in values]
        if missing:
            raise ValueError(f"paramètre(s) requis absent(s) : {', '.join(missing)}")

        measurement_variance = _as_float(values["measurement_variance"], "measurement_variance")
        if measurement_variance <= 0.0:
            raise ValueError(
                "« measurement_variance » doit être strictement positive "
                f"(reçu {measurement_variance!r})"
            )
        level_process_variance = _as_float(
            values["level_process_variance"], "level_process_variance"
        )
        if level_process_variance < 0.0:
            raise ValueError(
                f"« level_process_variance » doit être positive ou nulle (reçu {level_process_variance!r})"
            )
        slope_process_variance = _as_float(
            values["slope_process_variance"], "slope_process_variance"
        )
        if slope_process_variance < 0.0:
            raise ValueError(
                f"« slope_process_variance » doit être positive ou nulle (reçu {slope_process_variance!r})"
            )

        initial_level = (
            _as_float(values["initial_level"], "initial_level")
            if "initial_level" in values
            else default_initial_level
        )
        initial_slope = (
            _as_float(values["initial_slope"], "initial_slope")
            if "initial_slope" in values
            else 0.0
        )
        return _Settings(
            measurement_variance=measurement_variance,
            level_process_variance=level_process_variance,
            slope_process_variance=slope_process_variance,
            initial_level=initial_level,
            initial_slope=initial_slope,
        )


__all__ = ["LocalLinearTrendModel"]
