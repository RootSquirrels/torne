"""Tests for the evolved Kalman filter: irregular time, estimated parameters, smoothing.

The reference implementation (the regularly spaced local linear trend) is
checked in `tests/test_methods.py` against a scalar reimplementation and against
`statsmodels`. These tests cover what the evolutions added on top of it:

- an irregular grid changes the dynamics, and a regular grid does not;
- the variances can be estimated by maximum likelihood on the training series
  alone, and the estimates are carried in the result;
- the smoothed state is separated from the filtered state, and is declared as
  using information from the future.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

import numpy as np
import pytest

from torne.contracts.model import (
    ModelInputs,
    ModelParameters,
    ModelResult,
    ModelSpec,
    ResultNature,
)
from torne.methods.kalman import LocalLinearTrendModel

MODELE = LocalLinearTrendModel()

PARAMETRES = {
    "measurement_variance": 1.0,
    "level_process_variance": 0.1,
    "slope_process_variance": 0.01,
}


def _serie(n: int = 40, *, graine: int = 7) -> list[float]:
    """A noisy series with a slow linear drift."""
    rng = np.random.default_rng(graine)
    trend = np.linspace(0.0, 4.0, n)
    return [float(v) for v in trend + rng.normal(0.0, 0.5, n)]


def _executer(
    serie,
    *,
    temps=None,
    **parametres,
) -> ModelResult:
    """Runs the model on a series, optionally with a time series."""
    series = {"y": tuple(float(v) for v in serie)}
    if temps is not None:
        series["t"] = tuple(float(v) for v in temps)
    values = {**PARAMETRES, **parametres}
    return MODELE.run(
        ModelInputs(series=series),
        ModelParameters(values=values),
    )


# --------------------------------------------------------------------------
# Irregular time
# --------------------------------------------------------------------------


def test_une_serie_reguliere_avec_des_temps_donne_le_meme_resultat():
    """A regular grid must not change anything: the model has no absolute time scale."""
    serie = _serie()
    sans = _executer(serie)
    avec = _executer(serie, temps=[float(i) for i in range(len(serie))])

    assert avec.outputs == sans.outputs
    assert avec.intervals == sans.intervals
    assert avec.diagnostics["log_likelihood"] == pytest.approx(
        sans.diagnostics["log_likelihood"], abs=1e-12
    )
    assert avec.diagnostics["irregular_time"] is True


def test_une_serie_sans_temps_est_declaree_reguliere():
    resultat = _executer(_serie())

    assert resultat.diagnostics["irregular_time"] is False
    assert "time_scale" not in resultat.diagnostics


def test_une_irr_regularite_change_la_dynamique():
    """An uneven grid must actually change the transition, not be silently ignored."""
    serie = _serie(30)
    regulier = _executer(serie)
    irregulier = _executer(
        serie,
        temps=[0.0, 1.0, 2.0, 3.0, 4.0, 30.0, 31.0, 32.0]
        + [33.0 + i for i in range(len(serie) - 8)],
    )

    assert irregulier.outputs["level"] != regulier.outputs["level"]
    assert irregulier.diagnostics["time_scale"] == pytest.approx(1.0)
    assert irregulier.diagnostics["max_gap"] == pytest.approx(26.0)


def test_le_lissage_et_la_dynamique_suivent_la_cible():
    """The gap statistics are reported, so the normalisation is auditable."""
    serie = _serie(20)
    resultat = _executer(
        serie, temps=[0.0, 1.0, 2.0, 10.0, 11.0, 12.0, 13.0] + [14.0 + i for i in range(13)]
    )

    assert resultat.diagnostics["irregular_time"] is True
    assert resultat.diagnostics["min_gap"] == pytest.approx(1.0)
    assert resultat.diagnostics["max_gap"] == pytest.approx(8.0)
    assert resultat.diagnostics["time_scale"] == pytest.approx(1.0)


def test_une_serie_de_temps_invalide_est_refusee():
    """Wrong length, non-monotonic times and non-finite times are all refused."""
    serie = _serie(10)

    with pytest.raises(ValueError, match="values"):
        _executer(serie, temps=[0.0, 1.0])

    with pytest.raises(ValueError, match="strictly increasing"):
        _executer(serie, temps=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 3.0])

    with pytest.raises(ValueError, match="non-finite"):
        _executer(serie, temps=[float(i) for i in range(9)] + [float("nan")])


# --------------------------------------------------------------------------
# Estimated parameters
# --------------------------------------------------------------------------


def test_les_variances_peuvent_estimees_par_maximum_de_vraisemblance():
    """The estimation runs on the training series, and reports what it found."""
    serie = _serie(60)
    impose = _executer(serie)
    estime = _executer(serie, estimate_parameters=True)

    assert estime.diagnostics["parameters_estimated"] is True
    assert impose.diagnostics["parameters_estimated"] is False

    # The estimation cannot lower the likelihood: it starts from the imposed
    # parameters and only moves uphill.
    assert estime.diagnostics["log_likelihood"] >= impose.diagnostics["log_likelihood"] - 1e-9

    for nom in (
        "estimated_measurement_variance",
        "estimated_level_process_variance",
        "estimated_slope_process_variance",
    ):
        assert estime.diagnostics[nom] > 0.0


def test_les_parametres_estimes_sont_portes_par_le_resultat():
    """The estimates are part of the artefact, not a side effect."""
    serie = _serie(60)
    estime = _executer(serie, estimate_parameters=True)

    valeurs = estime.parameters.as_dict()
    assert valeurs["measurement_variance"] == pytest.approx(
        estime.diagnostics["estimated_measurement_variance"]
    )
    assert valeurs["level_process_variance"] == pytest.approx(
        estime.diagnostics["estimated_level_process_variance"]
    )
    assert valeurs["slope_process_variance"] == pytest.approx(
        estime.diagnostics["estimated_slope_process_variance"]
    )


def test_l_estimation_est_deterministe():
    """Same data, same parameters, same result."""
    serie = _serie(50)
    premier = _executer(serie, estimate_parameters=True)
    second = _executer(serie, estimate_parameters=True)

    assert premier.outputs == second.outputs
    assert premier.parameters.as_dict() == second.parameters.as_dict()


def test_le_lissage_n_altere_pas_le_filtrage():
    """Smoothing is an addition, never a modification of the filtered state."""
    serie = _serie(40)
    filtre = _executer(serie)
    lisse = _executer(serie, smooth=True)

    assert lisse.outputs["level"] == filtre.outputs["level"]
    assert lisse.outputs["slope"] == filtre.outputs["slope"]
    assert lisse.outputs["forecast_level"] == filtre.outputs["forecast_level"]


# --------------------------------------------------------------------------
# Filtering and smoothing
# --------------------------------------------------------------------------


def test_le_lissage_produit_des_sorties_separees_et_declarees():
    """The smoothed outputs exist, and they say they use the future."""
    resultat = _executer(_serie(40), smooth=True)

    assert "smoothed_level" in resultat.outputs
    assert "smoothed_slope" in resultat.outputs
    assert resultat.outputs_using_future == ("smoothed_level", "smoothed_slope")
    assert resultat.output_nature("smoothed_level") is ResultNature.RECONSTRUCTED
    assert len(resultat.intervals["smoothed_level"]) == 40


def test_sans_lissage_aucune_sortie_n_est_declaree_comme_utilisant_le_futur():
    resultat = _executer(_serie(40))

    assert resultat.outputs_using_future == ()


def test_le_lissage_utilise_reellement_le_futur():
    """Perturbing a late observation must move the smoothed state, not the filtered one.

    This is the property that separates the smoother from the filter: the
    smoothed state of an early instant improves when later observations arrive.
    """
    serie = _serie(40)
    altere = list(serie)
    altere[-1] = altere[-1] + 50.0

    filtre = _executer(serie, smooth=True)
    filtre_altere = _executer(altere, smooth=True)

    # The filtered state at the first instant only depends on the first
    # observation: it does not move.
    assert filtre.outputs["level"][0] == pytest.approx(filtre_altere.outputs["level"][0])

    # The smoothed state at the same instant does move: it used the future.
    assert filtre.outputs["smoothed_level"][0] != pytest.approx(
        filtre_altere.outputs["smoothed_level"][0], abs=1e-6
    )


def test_le_lissage_reduit_ou_egale_l_ecart_a_l_etat_vrai():
    """On a clean series, smoothing must not be worse than filtering."""
    truth = np.linspace(0.0, 5.0, 60)
    noisy = [float(v) for v in truth + np.random.default_rng(3).normal(0.0, 0.3, 60)]

    filtre = _executer(noisy, smooth=True)
    lisse = _executer(noisy, smooth=True)

    erreur_filtree = np.mean(
        [abs(f - t) for f, t in zip(filtre.outputs["level"], truth, strict=True)]
    )
    erreur_lisse = np.mean(
        [abs(s - t) for s, t in zip(lisse.outputs["smoothed_level"], truth, strict=True)]
    )

    assert erreur_lisse <= erreur_filtree


def test_une_sortie_utilisant_le_futur_inconnue_est_refusee():
    """A declaration that describes nothing is refused."""
    with pytest.raises(ValueError, match="futur"):
        ModelResult(
            spec=ModelSpec(
                model_id="test.model",
                version="0.1.0",
                question="q",
                method="m",
                natures=(ResultNature.DERIVED,),
            ),
            nature=ResultNature.DERIVED,
            parameters=ModelParameters(values={}),
            produced_at=datetime.now(UTC),
            outputs={"x": (1.0,)},
            outputs_using_future=("y",),
        )


def test_le_modele_refuse_un_parametre_booleen_non_booleen():
    with pytest.raises(ValueError, match="boolean"):
        _executer(_serie(10), smooth="oui")


def test_les_parametres_inconnus_sont_refuses():
    with pytest.raises(ValueError, match="unknown"):
        _executer(_serie(10), variance_du_bruit=1.0)


def test_le_niveau_fini_est_verifie():
    serie = _serie(10)
    serie[3] = float("inf")
    with pytest.raises(ValueError, match="non-finite"):
        _executer(serie)


def test_le_modele_reste_deterministe():
    """The model draws no randomness, even with estimation enabled."""
    serie = _serie(30)
    with_graine = MODELE.run(
        ModelInputs(series={"y": tuple(serie)}),
        ModelParameters(values={**PARAMETRES, "estimate_parameters": True}),
        seed=1234,
    )
    sans_graine = MODELE.run(
        ModelInputs(series={"y": tuple(serie)}),
        ModelParameters(values={**PARAMETRES, "estimate_parameters": True}),
    )

    assert with_graine.outputs == sans_graine.outputs
    assert math.isclose(
        with_graine.diagnostics["log_likelihood"],
        sans_graine.diagnostics["log_likelihood"],
        rel_tol=0.0,
        abs_tol=0.0,
    )
