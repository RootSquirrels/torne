"""The first derived variable of the real world: a standardised flow anomaly.

A discharge series is a list of numbers. What a reader wants is not the list
but the **statement**: *is this period wetter or drier than the norm, and by
how much?* The number that carries that statement is not in any source — the
provider publishes the values and, separately, its own statistics of record.
The anomaly index is computed here, from the values themselves, and it is
checked against the provider's statistics.

The index is the standardised deviation of a daily value from the
**day-of-year climatology** computed over the acquired record:

    z(t) = (Q(t) - mean(day-of-year of t)) / sd(day-of-year of t)

Two conventions are declared, never assumed:

- the climatology is keyed on the **local civil day**, so it is built in the
  station's zone;
- the reference is the **whole acquired record**, and the window being
  scored is inside it. A day scored against a reference that contains it
  would be scored against itself.

The uncertainty is what is really known: the interval is the confidence
interval of the **mean** index over the window, and its statement says
plainly what it does not cover — the uncertainty of the reference itself.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..contracts.derived import DerivedVariable, Uncertainty
from ..contracts.model import ModelParameters, ResultNature
from ..contracts.observation import Observation
from ..contracts.validity import PointValidity

METHOD = "day-of-year standardised anomaly index"
VERSION = "1.0.0"
"""Version of the calculation rule.

It is versioned because the rule is part of the product: a reader who finds
an index has to be able to know which rule produced it.
"""

NIVEAU_CONFIANCE = 0.95
"""The confidence level of the interval on the mean index."""


@dataclass(frozen=True, slots=True)
class ClimatologyDay:
    """The climatology of one calendar day.

    `count` is the number of years the day was observed: it is what makes
    the dispersion meaningful, and it is what tells the reader how thin the
    reference is.
    """

    month: int
    day: int
    mean: float
    standard_deviation: float
    count: int


@dataclass(frozen=True, slots=True)
class Climatology:
    """The day-of-year climatology computed over an acquired record."""

    by_day: Mapping[tuple[int, int], ClimatologyDay]
    reference_start: datetime
    reference_end: datetime
    years: int

    def __len__(self) -> int:
        return len(self.by_day)

    def pour(self, month: int, day: int) -> ClimatologyDay | None:
        """The climatology of a calendar day, when it was observed."""
        return self.by_day.get((month, day))


@dataclass(frozen=True, slots=True)
class NormalsGap:
    """The comparison with the provider's own statistics.

    This is the **independent reference**: the numbers published by the
    agency, computed over its period of record, against the numbers computed
    here from the acquired values.
    """

    days_compared: int
    median_absolute_gap: float
    median_relative_gap: float
    max_relative_gap: float
    correlation: float
    reference_years: int
    acquired_years: int

    @property
    def concordant(self) -> bool:
        """Is the reproduction close enough to be accepted?

        The threshold is deliberately coarse and declared: it is a check that
        the two computations tell the same story, not a proof of identity.
        """
        return self.median_relative_gap <= 0.05

    def as_dict(self) -> dict[str, Any]:
        """A serialisable view of the comparison."""
        return {
            "days_compared": self.days_compared,
            "median_absolute_gap": self.median_absolute_gap,
            "median_relative_gap": self.median_relative_gap,
            "max_relative_gap": self.max_relative_gap,
            "correlation": self.correlation,
            "reference_years": self.reference_years,
            "acquired_years": self.acquired_years,
            "concordant": self.concordant,
        }


def climatology(
    observations: Iterable[Observation],
    *,
    reference_start: datetime | None = None,
    reference_end: datetime | None = None,
) -> Climatology:
    """The day-of-year climatology of an acquired record.

    Only valid observations enter the statistics: a day the provider did not
    measure is not a day at the mean. The day is the **local civil day** of
    the observation's valid time, which the observation already carries.
    """
    groups: dict[tuple[int, int], list[float]] = {}
    for observation in observations:
        if observation.validity is not PointValidity.VALID or observation.value is None:
            continue
        instant = observation.temporal.valid_time
        if instant is None:
            continue
        groups.setdefault((instant.month, instant.day), []).append(float(observation.value))

    by_day: dict[tuple[int, int], ClimatologyDay] = {}
    for (month, day), values in groups.items():
        mean = statistics.fmean(values)
        standard_deviation = statistics.stdev(values) if len(values) > 1 else 0.0
        by_day[(month, day)] = ClimatologyDay(
            month=month,
            day=day,
            mean=mean,
            standard_deviation=standard_deviation,
            count=len(values),
        )

    instants = [
        observation.temporal.valid_time
        for observation in observations
        if observation.temporal.valid_time is not None
    ]
    start = reference_start or (min(instants) if instants else None)
    end = reference_end or (max(instants) if instants else None)
    years = _years(start, end)

    return Climatology(
        by_day=by_day,
        reference_start=start or datetime.min,
        reference_end=end or datetime.min,
        years=years,
    )


def anomalies(
    observations: Sequence[Observation],
    reference: Climatology,
) -> list[tuple[Observation, float]]:
    """The standardised anomalies of the observations, against the reference.

    A day whose climatology is unknown — a day never observed in the
    reference — is **not** scored: it would be scored against nothing.
    """
    scores: list[tuple[Observation, float]] = []
    for observation in observations:
        if observation.validity is not PointValidity.VALID or observation.value is None:
            continue
        instant = observation.temporal.valid_time
        if instant is None:
            continue
        day = reference.pour(instant.month, instant.day)
        if day is None or day.standard_deviation <= 0.0:
            continue
        scores.append((observation, (float(observation.value) - day.mean) / day.standard_deviation))
    return scores


def anomaly_index(
    observations: Sequence[Observation],
    reference: Climatology,
    *,
    variable_id: str,
    spatial_ref: str,
    computed_at: datetime,
    fenetre: tuple[datetime, datetime] | None = None,
) -> DerivedVariable:
    """The anomaly series over the window, as a derived variable.

    The series is a `DerivedVariable` of nature `DERIVED`: it is a computed
    quantity, and it never presents itself as an observation of the source.
    """
    scores = anomalies(observations, reference)
    if fenetre is not None:
        start, end = fenetre
        scores = [
            (observation, score)
            for observation, score in scores
            if observation.temporal.valid_time is not None
            and start <= observation.temporal.valid_time <= end
        ]
    if not scores:
        raise ValueError("no observation could be scored against the reference")

    values = [score for _, score in scores]
    inputs = tuple(observation for observation, _ in scores)
    mean_standard_deviation = statistics.stdev(values) if len(values) > 1 else 0.0
    erreur = mean_standard_deviation / (len(values) ** 0.5) if len(values) > 1 else 0.0
    half_width = 1.96 * erreur

    return DerivedVariable(
        variable_id=variable_id,
        quantity="standardised discharge anomaly",
        unit="1",
        nature=ResultNature.DERIVED,
        method=METHOD,
        method_version=VERSION,
        parameters=ModelParameters(
            values={
                "reference_start": reference.reference_start.isoformat(),
                "reference_end": reference.reference_end.isoformat(),
                "reference_annees": reference.years,
                "jours_reference": len(reference),
                "fenetre_debut": fenetre[0].isoformat() if fenetre else "",
                "fenetre_fin": fenetre[1].isoformat() if fenetre else "",
                "observations_scorees": len(inputs),
                "convention_jour": "local civil day",
            }
        ),
        computed_at=computed_at,
        uncertainty=Uncertainty.from_interval(
            (
                "The interval is the 95% confidence interval of the mean of the "
                "standardised daily anomalies over the window, under the assumption "
                "that the daily anomalies are independent. It does not cover the "
                "uncertainty of the reference climatology itself, nor the "
                "uncertainty of the values published by the source."
            ),
            (
                statistics.fmean(values) - half_width,
                statistics.fmean(values) + half_width,
            ),
        ),
        inputs=inputs,
        values=tuple(values),
        valid_time=fenetre[1] if fenetre else None,
        spatial_ref=spatial_ref,
    )


def mean_anomaly(
    series: DerivedVariable,
    *,
    variable_id: str,
    computed_at: datetime,
) -> DerivedVariable:
    """The mean anomaly over the window, as a single number.

    It is a **separate** variable from the series, because the contract
    admits one or the other and never both: the series is what was computed
    point by point, the mean is what it means.
    """
    if not series.values:
        raise ValueError("the series carries no value")
    mean = statistics.fmean(series.values)
    bas, haut = series.uncertainty.interval or (mean, mean)
    return DerivedVariable(
        variable_id=variable_id,
        quantity="mean standardised discharge anomaly",
        unit="1",
        nature=ResultNature.DERIVED,
        method=METHOD,
        method_version=VERSION,
        parameters=ModelParameters(values=series.parameters.as_dict()),
        computed_at=computed_at,
        uncertainty=Uncertainty.from_interval(
            (
                "The interval is carried unchanged from the series it summarises; it "
                "covers the sampling uncertainty of the mean, and not the "
                "uncertainty of the reference climatology."
            ),
            (bas, haut),
        ),
        inputs=(series,),
        value=mean,
        valid_time=series.valid_time,
        spatial_ref=series.spatial_ref,
    )


def compare_with_published_normals(
    reference: Climatology,
    published_normals: Mapping[tuple[int, int], float],
    *,
    acquired_years: int | None = None,
) -> NormalsGap:
    """Compare the climatology computed here with the provider's own statistics.

    `published_normals` maps a calendar day to the mean the provider publishes for it.
    The comparison is honest about what it is: the provider computes over its
    period of record, and this computation covers the acquired window. The
    numbers are close when the two periods are close, and the report says how
    many years each of them covers.
    """
    deviations: list[float] = []
    absolute_gaps: list[float] = []
    pairs_x: list[float] = []
    pairs_y: list[float] = []
    reference_years = 0

    for (month, day), expected in published_normals.items():
        jour_reference = reference.pour(month, day)
        if jour_reference is None:
            continue
        if expected == 0.0:
            continue
        deviations.append(abs(jour_reference.mean - expected) / abs(expected))
        absolute_gaps.append(abs(jour_reference.mean - expected))
        pairs_x.append(jour_reference.mean)
        pairs_y.append(expected)
        reference_years = max(reference_years, jour_reference.count)

    if not deviations:
        raise ValueError("no day could be compared with the reference statistics")

    correlation = 0.0
    if len(pairs_x) > 1 and statistics.pstdev(pairs_x) > 0 and statistics.pstdev(pairs_y) > 0:
        correlation = statistics.correlation(pairs_x, pairs_y)

    return NormalsGap(
        days_compared=len(deviations),
        median_absolute_gap=statistics.median(absolute_gaps),
        median_relative_gap=statistics.median(deviations),
        max_relative_gap=max(deviations),
        correlation=correlation,
        reference_years=reference_years,
        acquired_years=acquired_years if acquired_years is not None else reference.years,
    )


def published_normals_by_day(
    payload: Mapping[str, Any],
    *,
    computation: str = "arithmetic_mean",
    parameter_code: str = "00060",
) -> dict[tuple[int, int], float]:
    """The provider's published statistics, read as a day-of-year mapping.

    The statistics service publishes one value per calendar day per
    computation. Only the arithmetic mean is read here: the median and the
    percentiles are other statistics, and mixing them into one comparison
    would compare two different things.
    """
    resultat: dict[tuple[int, int], float] = {}
    features = payload.get("features")
    if not isinstance(features, list):
        return resultat
    for feature in features:
        if not isinstance(feature, Mapping):
            continue
        properties = feature.get("properties")
        if not isinstance(properties, Mapping):
            continue
        blocks = properties.get("data")
        if not isinstance(blocks, list):
            continue
        for bloc in blocks:
            if not isinstance(bloc, Mapping):
                continue
            if bloc.get("parameter_code") != parameter_code:
                continue
            values = bloc.get("values")
            if not isinstance(values, list):
                continue
            for entree in values:
                if not isinstance(entree, Mapping):
                    continue
                if entree.get("computation") != computation:
                    continue
                if entree.get("time_of_year_type") != "day_of_year":
                    continue
                day = entree.get("time_of_year")
                value = entree.get("value")
                if not isinstance(day, str) or not isinstance(value, (str, int, float)):
                    continue
                try:
                    month, jour_du_mois = (int(part) for part in day.split("-"))
                    nombre = float(value)
                except ValueError:
                    continue
                resultat[(month, jour_du_mois)] = nombre
    return resultat


def _years(start: datetime | None, end: datetime | None) -> int:
    if start is None or end is None:
        return 0
    return (end.year - start.year) + 1


__all__ = [
    "METHOD",
    "NIVEAU_CONFIANCE",
    "VERSION",
    "Climatology",
    "ClimatologyDay",
    "NormalsGap",
    "anomalies",
    "anomaly_index",
    "climatology",
    "compare_with_published_normals",
    "mean_anomaly",
    "published_normals_by_day",
]
