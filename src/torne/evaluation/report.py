"""Rapport d'évaluation reproductible : modèle, références, découpe.

Le rapport est l'enregistrement de ce qui a été évalué : l'identité du modèle,
la découpe (rejouable par ses indices), le pas des plis, les métriques du
modèle, les métriques des trois références calculées **sur les mêmes plis**,
et l'instant d'évaluation.

Aucune dépendance n'est cachée : l'horodatage est injectable, le prédicteur
est un argument explicite, et le contenu du rapport ne provient que des
modules `splits`, `metrics`, `baselines` et `uncertainty`.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType

from ..contracts.time import to_utc
from ..contracts.validity import PointValidity
from .baselines import drift_forecast, mean_forecast, persistence_forecast
from .metrics import MetricReport, evaluate_all
from .splits import Split, walk_forward


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    """Résultat d'une évaluation, avec les métriques du modèle et des références.

    `split` enregistre les indices de découpe : la **période** évaluée est
    rejouable à partir du rapport. `step` enregistre le pas des plis du
    walk-forward : avec `split`, il rend la décomposition en plis rejouable
    elle aussi, et distingue deux évaluations de même période mais de plis
    différents. `n_excluded` compte les points de la série qui ne tombent dans
    aucun pli — ni entraînement, ni test : ils ne sont pas évalués, et le
    rapport le dit au lieu de les perdre en silence. `evaluated_at` est
    l'instant d'évaluation, injectable pour qu'un test soit déterministe ; il
    porte toujours un fuseau (INV-15). `comparison` accueille un résultat de
    comparaison calculé ailleurs (test de Diebold-Mariano, par exemple) : son
    contenu est libre et sérialisable, et il ne crée aucune dépendance entre
    modules.
    """

    model_id: str
    model_version: str
    split: Split
    metrics: Mapping[str, MetricReport]
    baseline_metrics: Mapping[str, Mapping[str, MetricReport]]
    step: int
    n_excluded: int
    evaluated_at: datetime
    comparison: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.step < 1:
            raise ValueError(f"step doit valoir au moins 1, il vaut {self.step}")
        if self.n_excluded < 0:
            raise ValueError(f"n_excluded ne peut pas être négatif, il vaut {self.n_excluded}")
        object.__setattr__(self, "metrics", MappingProxyType(dict(self.metrics)))
        object.__setattr__(
            self,
            "baseline_metrics",
            MappingProxyType(
                {
                    name: MappingProxyType(dict(reports))
                    for name, reports in self.baseline_metrics.items()
                }
            ),
        )
        object.__setattr__(self, "comparison", MappingProxyType(dict(self.comparison)))
        object.__setattr__(self, "evaluated_at", to_utc(self.evaluated_at, name="evaluated_at"))

    def with_comparison(self, comparison: Mapping[str, object]) -> EvaluationReport:
        """Renvoie une copie du rapport portant le résultat de comparaison fourni.

        Le rapport d'origine n'est pas modifié. Les clés déjà présentes sont
        remplacées par les nouvelles valeurs ; les autres sont conservées.
        """
        return EvaluationReport(
            model_id=self.model_id,
            model_version=self.model_version,
            split=self.split,
            metrics=dict(self.metrics),
            baseline_metrics={
                name: dict(reports) for name, reports in self.baseline_metrics.items()
            },
            step=self.step,
            n_excluded=self.n_excluded,
            evaluated_at=self.evaluated_at,
            comparison={**self.comparison, **comparison},
        )

    def as_dict(self) -> dict[str, object]:
        """Vue sérialisable du rapport : dictionnaires ordinaires, aucun proxy.

        Le rapport est figé, et ses mappings sont des vues en lecture seule :
        c'est cette vue qu'un enregistreur écrit. L'horodatage est rendu en
        ISO 8601, fuseau compris.
        """
        return {
            "model_id": self.model_id,
            "model_version": self.model_version,
            "split": asdict(self.split),
            "step": self.step,
            "n_excluded": self.n_excluded,
            "metrics": {name: _metric_as_dict(report) for name, report in self.metrics.items()},
            "baseline_metrics": {
                name: {metric: _metric_as_dict(report) for metric, report in reports.items()}
                for name, reports in self.baseline_metrics.items()
            },
            "evaluated_at": self.evaluated_at.isoformat(),
            "comparison": dict(self.comparison),
        }


def _metric_as_dict(report: MetricReport) -> dict[str, object]:
    """Vue sérialisable d'une métrique, incertitude comprise.

    L'incertitude est rendue par sa propre vue : c'est un objet du contrat,
    et son énumération doit devenir une chaîne.
    """
    data = asdict(report)
    data["uncertainty"] = report.uncertainty.as_dict() if report.uncertainty is not None else None
    return data


def evaluate_walk_forward(
    values: Sequence[float],
    predictor: Callable[[tuple[float, ...]], Sequence[float]],
    *,
    initial_size: int,
    step: int,
    validity: Sequence[PointValidity] | None = None,
    model_id: str = "",
    model_version: str = "",
    now: datetime | None = None,
) -> EvaluationReport:
    """Évalue un modèle et trois références sur exactement les mêmes plis.

    `predictor` reçoit le bloc `train` d'un pli et renvoie les `step`
    prévisions du bloc `test` qui suit. Il ne voit jamais la période test :
    seul le bloc d'entraînement lui est transmis.

    Les trois références (persistance, moyenne, dérive) sont ajustées
    **uniquement** sur le bloc `train` de chaque pli, puis évaluées sur le même
    bloc `test` que le modèle : les compteurs `n_total` et `n_used` sont donc
    identiques pour le modèle et pour toutes les références.

    Les métriques sont calculées sur les points test de tous les plis réunis,
    dans l'ordre chronologique. `now` injectable rend le rapport déterministe.

    Le rapport retient le `step` du walk-forward et le nombre de points de la
    série qui ne tombent dans aucun pli : les plis sont rejouables à partir du
    rapport, et les points écartés sont comptés au lieu d'être perdus.
    """
    series = tuple(values)
    if validity is not None and len(validity) != len(series):
        raise ValueError(
            f"validity doit porter un état par point de la série : "
            f"{len(validity)} pour {len(series)}"
        )

    folds = walk_forward(series, initial_size=initial_size, step=step)

    actuals: list[float] = []
    predictions: list[float] = []
    states: list[PointValidity] = []
    baselines = {
        "persistence": persistence_forecast,
        "mean": mean_forecast,
        "drift": drift_forecast,
    }
    baseline_predictions: dict[str, list[float]] = {name: [] for name in baselines}

    for fold in folds:
        expected = fold.test_end - fold.test_start
        predicted = tuple(predictor(fold.train))
        if len(predicted) != expected:
            raise ValueError(
                f"le prédicteur doit renvoyer {expected} valeurs pour le pli "
                f"{fold.index}, il en a renvoyé {len(predicted)}"
            )
        actuals.extend(fold.test)
        predictions.extend(predicted)
        if validity is not None:
            states.extend(validity[fold.test_start : fold.test_end])
        for name, baseline in baselines.items():
            try:
                forecast = baseline(fold.train, expected)
            except ValueError as exc:
                raise ValueError(
                    f"la référence « {name} » n'est pas applicable au pli {fold.index} : {exc}"
                ) from exc
            baseline_predictions[name].extend(forecast)

    evaluated_validity = tuple(states) if validity is not None else None
    metrics = evaluate_all(tuple(actuals), tuple(predictions), validity=evaluated_validity)
    baseline_metrics = {
        name: evaluate_all(tuple(actuals), tuple(forecasts), validity=evaluated_validity)
        for name, forecasts in baseline_predictions.items()
    }

    first = folds[0]
    last = folds[-1]
    split = Split(
        train=series[: first.train_end],
        test=series[first.test_start : last.test_end],
        train_end=first.train_end,
        test_start=first.test_start,
        test_end=last.test_end,
    )

    return EvaluationReport(
        model_id=model_id,
        model_version=model_version,
        split=split,
        metrics=metrics,
        baseline_metrics=baseline_metrics,
        step=step,
        n_excluded=len(series) - last.test_end,
        evaluated_at=datetime.now(UTC) if now is None else to_utc(now, name="now"),
    )


__all__ = ["EvaluationReport", "evaluate_walk_forward"]
