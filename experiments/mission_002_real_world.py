"""Mission 002 — the real world: one river, one station, one statement.

This script is the milestone the audit asked for: **not** a demonstration on
synthetic data, but a statement about a real river, built from the source's
own records, checked against the source's own statistics.

    python experiments/mission_002_real_world.py
    USGS_API_KEY=<key> python experiments/mission_002_real_world.py

The key is optional. The anonymous quota is 1000 requests per hour, and the
provider refuses beyond it with a 429 and a `Retry-After` — a key has its
own bucket. It is read from the environment and never written anywhere: the
socle resolves it at the last moment, and it never enters the recorded
request.

What the script does, in order:

1. **asks the source what it knows about the station** — the site, its
   timezone, its catchment;
2. **asks the source which series exist there**, and picks the daily mean
   discharge — by its identifier, never by guessing;
3. **acquires the whole record** of that series, and keeps every byte as raw
   evidence;
4. **reads the records as observations** — value, unit, day, declared quality;
5. **checks its own work against the source's published statistics**, which
   the agency computes over its own period of record: the day-of-year
   climatology computed here must reproduce theirs;
6. **computes what no source publishes** — the standardised anomaly of the
   last year against the day-of-year climatology of the whole record;
7. **runs the model on the real series**, evaluates it out of sample, and
   **publishes a knowledge product** whose lineage is verified back to the
   raw evidence.

The station is the Mississippi at Grafton, Illinois (USGS-05587450). It was
chosen because it is a long, well-documented record of a large river, and
because its statistics are published.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from torne.acquisition.adapters.usgs_ogc import (
    CREDENTIAL_REF,
    UsgsObservationNormalsAdapter,
    UsgsOgcItemsAdapter,
)
from torne.acquisition.contracts import AcquisitionOutcome, CredentialProvider
from torne.acquisition.fetcher import Fetcher
from torne.acquisition.store import FileRawStore
from torne.acquisition.transport import HttpTransport
from torne.contracts.knowledge import ProductStatus
from torne.contracts.model import ModelInputs, ModelParameters
from torne.contracts.observation import Observation
from torne.evaluation.report import evaluate_walk_forward
from torne.execution.runner import execute
from torne.hydrology import (
    anomaly_index,
    climatology,
    compare_with_published_normals,
    mean_anomaly,
    observation_from_feature,
    published_normals_by_day,
    station_from_feature,
    time_series,
)
from torne.knowledge.record import build_record, verify_lineage
from torne.methods.kalman import LocalLinearTrendModel

STATION = "USGS-05587450"
"""Mississippi River at Grafton, IL — a long, well-documented record."""

DEBIT_PARAMETER = "00060"
"""Discharge, cubic feet per second."""

MEAN_STATISTIC = "00003"
"""Daily mean."""

ZONE = ZoneInfo("America/Chicago")
"""The station's local zone.

It is written here, explicitly, because the provider publishes an
abbreviation (`CST`) and a daylight-saving flag, and neither of them is a
zone. The abbreviation alone is ambiguous: `CST` is also China Standard Time.
"""

MODEL_PARAMETERS = ModelParameters(
    values={
        "measurement_variance": 0.05**2,
        "level_process_variance": 0.01**2,
        "slope_process_variance": 1e-9,
    }
)
"""Explicit parameters of the model — no hidden configuration."""


class EnvironmentKey(CredentialProvider):
    """The API key, read from the environment and resolved at the last moment.

    The contract does not say how a secret is stored; it says that it leaves
    here, at the last moment, and that it never comes back into a recorded
    object. This provider is one way of doing it — the environment is the
    simplest place where a secret can live without being written down.
    """

    def __init__(self, variable: str = "USGS_API_KEY") -> None:
        self._variable = variable

    def credentials_for(self, credential_ref: str) -> Mapping[str, str]:
        if credential_ref != CREDENTIAL_REF:
            return {}
        cle = os.environ.get(self._variable, "").strip()
        if not cle:
            return {}
        return {"X-Api-Key": cle}


def _fetcher(magasin: FileRawStore) -> Fetcher:
    return Fetcher(
        transport=HttpTransport(timeout=60.0),
        store=magasin,
        credentials=EnvironmentKey(),
    )


def _acquer(fetcher: Fetcher, adaptateur, *, quoi: str) -> AcquisitionOutcome:
    """Acquire a source, and refuse to go on unless the answer is usable.

    The gate is the socle's: an outcome that is not exploitable does not
    become observations. The script says so and stops, rather than
    interpreting a response whose conformity was never established.
    """
    issue = fetcher.acquire(adaptateur)
    etat = issue.conformite.value if issue.verdict_conformite else "aucun verdict"
    print(
        f"  {quoi} : {issue.status.value}, {issue.page_count} page(s), "
        f"conformity {etat}, exploitable {issue.exploitable}"
    )
    if not issue.exploitable:
        motif = (
            issue.verdict_conformite.motif if issue.verdict_conformite else "no verdict rendered"
        )
        raise SystemExit(f"the answer to « {quoi} » is not usable: {motif}")
    return issue


def _features(issue: AcquisitionOutcome, magasin: FileRawStore) -> list[dict]:
    """The features of the acquired pages, read back from the raw evidence.

    The interpretation always starts from the proof that was kept: the
    bytes come back from the store, addressed by their fingerprint.
    """
    features: list[dict] = []
    for piece in issue.evidence:
        chemin = magasin.content_path(piece.evidence_id)
        payload = json.loads(chemin.read_text(encoding="utf-8"))
        for feature in payload.get("features") or []:
            if isinstance(feature, dict):
                features.append(feature)
    return features


def _premiere(features: Sequence[dict], *, quoi: str) -> dict:
    if not features:
        raise SystemExit(f"{quoi}: nothing was received")
    return features[0]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        # The Windows console does not default to UTF-8, and this script
        # prints dates and intervals that deserve to be readable.
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    racine = Path(tempfile.mkdtemp(prefix="torne-mission-002-"))
    print(f"raw evidence store: {racine}")
    magasin = FileRawStore(racine)
    fetcher = _fetcher(magasin)

    # -- 1. The station ---------------------------------------------------
    print("\n1. the station")
    site_adapter = UsgsOgcItemsAdapter(
        collection="monitoring-locations",
        monitoring_location_id=STATION,
        required_fields=("id", "monitoring_location_name"),
        limit=10,
        max_pages=2,
        location_param="id",
        location_field="id",
    )
    site_issue = _acquer(fetcher, site_adapter, quoi="the monitoring location")
    station = station_from_feature(_premiere(_features(site_issue, magasin), quoi="the station"))
    print(f"  {station.name} ({station.monitoring_location_id})")
    print(f"  site type {station.site_type}, datum {station.vertical_datum}")
    print(f"  local time {station.timezone_abbreviation}, DST {station.uses_daylight_savings}")
    if station.drainage_area is not None:
        unite = station.drainage_area_unit or "unit not declared by the provider"
        print(f"  catchment {station.drainage_area} ({unite})")

    # -- 2. The series catalogue ------------------------------------------
    print("\n2. the series catalogue")
    series_adapter = UsgsOgcItemsAdapter(
        collection="time-series-metadata",
        monitoring_location_id=STATION,
        required_fields=("id", "parameter_code", "unit_of_measure"),
        limit=100,
        max_pages=5,
    )
    series_issue = _acquer(fetcher, series_adapter, quoi="the time series catalogue")
    series = _features(series_issue, magasin)
    for feature in series:
        properties = feature.get("properties") or {}
        print(
            f"  {properties.get('id')}  parameter {properties.get('parameter_code')}  "
            f"statistic {properties.get('statistic_id')}  "
            f"unit {properties.get('unit_of_measure')}  "
            f"period {properties.get('computation_period_identifier')}  "
            f"computation {properties.get('computation_identifier')}"
        )
    choisie = _choisir_la_serie(series)
    print(f"  chosen series: {choisie.get('id')} ({choisie.get('unit_of_measure')})")

    # -- 3. The values ----------------------------------------------------
    print("\n3. the daily values, over the whole record")
    start = (choisie.get("begin") or "1986-01-01")[:10]
    end = datetime.now(UTC).date().isoformat()
    values_adapter = UsgsOgcItemsAdapter(
        collection="daily",
        monitoring_location_id=STATION,
        parameter_codes=(DEBIT_PARAMETER,),
        statistic_ids=(MEAN_STATISTIC,),
        datetime_range=(start, end),
        limit=50_000,
        max_pages=10,
    )
    values_issue = _acquer(fetcher, values_adapter, quoi="the daily values")
    records = _features(values_issue, magasin)
    print(f"  {len(records)} record(s) received")

    # -- 4. The observations ----------------------------------------------
    print("\n4. the observations")
    piece = values_issue.evidence[0]
    observations: list[Observation] = []
    refused = 0
    for record in records:
        try:
            observations.append(
                observation_from_feature(
                    record,
                    station=station,
                    source_id=values_adapter.source_id,
                    evidence_id=piece.evidence_id,
                    zone=ZONE,
                    acquired_at=piece.acquired_at,
                    quantity="discharge",
                    unit=str(choisie.get("unit_of_measure")),
                )
            )
        except ValueError:
            refused += 1
    valid = [observation for observation in observations if observation.value is not None]
    print(f"  {len(observations)} observation(s), {len(valid)} with a value, {refused} refused")
    # The provider does not sort its records. The chronology is established
    # here, once — a filter that expects an increasing series refuses
    # anything else.
    observations = list(time_series(observations))
    instants = [observation.temporal.valid_time for observation in observations]
    if instants:
        print(f"  from {min(instants).date().isoformat()} to {max(instants).date().isoformat()}")

    # -- 5. The independent reference -------------------------------------
    print("\n5. the independent reference: the provider's own statistics")
    normals_adapter = UsgsObservationNormalsAdapter(
        monitoring_location_id=STATION,
        parameter_codes=(DEBIT_PARAMETER,),
        page_size=100,
        max_pages=10,
    )
    normals_issue = _acquer(fetcher, normals_adapter, quoi="the published statistics")
    published_normals = published_normals_by_day(_charge(normals_issue, magasin))
    print(f"  {len(published_normals)} calendar day(s) published by the agency")

    # -- 6. The derived variable ------------------------------------------
    print("\n6. the climatology, and the check against the reference")
    reference = climatology(observations)
    print(f"  climatology over {reference.years} year(s), {len(reference)} calendar day(s)")
    gap = compare_with_published_normals(
        reference, published_normals, acquired_years=reference.years
    )
    print(
        f"  compared with the agency on {gap.days_compared} day(s): "
        f"median relative difference {gap.median_relative_gap:.2%}, "
        f"correlation {gap.correlation:.5f}"
    )
    print(f"  concordant: {gap.concordant}")

    print("\n7. the statement no source publishes")
    fin_fenetre = datetime.now(UTC).astimezone(ZONE)
    debut_fenetre = fin_fenetre - timedelta(days=365)
    series = anomaly_index(
        observations,
        reference,
        variable_id=f"{STATION}:anomalie:{debut_fenetre.date()}",
        spatial_ref=STATION,
        computed_at=datetime.now(UTC),
        fenetre=(debut_fenetre, fin_fenetre),
    )
    mean = mean_anomaly(
        series,
        variable_id=f"{STATION}:anomalie_moyenne:{debut_fenetre.date()}",
        computed_at=datetime.now(UTC),
    )
    bas, haut = mean.uncertainty.interval or (0.0, 0.0)
    print(
        f"  {debut_fenetre.date()} -> {fin_fenetre.date()}: "
        f"mean standardised anomaly {mean.value:+.3f} "
        f"[{bas:+.3f}, {haut:+.3f}] over {len(series.values)} day(s)"
    )

    # -- 8. The model on the real series ----------------------------------
    print("\n8. the model on the real series")
    values = [
        observation.value if observation.value is not None else None for observation in observations
    ]
    absences = sum(1 for value in values if value is None)
    observes = [value for value in values if value is not None]
    instants = [
        observation.temporal.valid_time
        for observation in observations
        if observation.value is not None
    ]
    print(f"  {len(values)} point(s), {absences} absence(s)")
    # The model is run on the observed points, with their **real times**: an
    # absence is not a zero, and the model refuses a non-finite value. The
    # times are the epoch seconds of the observations; the model normalises
    # them by their median gap, so the unit does not matter — the gaps do.
    model_inputs = ModelInputs(
        series={
            "y": tuple(observes),
            "t": tuple(instant.timestamp() for instant in instants),
        }
    )
    issue_model = execute(
        LocalLinearTrendModel(),
        model_inputs,
        MODEL_PARAMETERS,
        now=datetime.now(UTC),
    )
    print(f"  state reconstructed on {len(observes)} point(s)")

    # The evaluation runs on the last three years: a walk-forward over the
    # whole record would re-execute the model tens of thousands of times for
    # no additional evidence.
    evaluation_window = values[-1095:]
    evaluation = evaluate_walk_forward(
        evaluation_window,
        _prevoir,
        initial_size=365,
        step=1,
        model_id=issue_model.result.spec.model_id,
        model_version=issue_model.result.spec.version,
    )
    report = evaluation.as_dict()
    for name, metric in report["metrics"].items():
        print(
            f"  {name}: {metric.get('value')}, "
            f"{metric.get('n_used')} point(s) used out of {metric.get('n_total')}"
        )

    # -- 9. The knowledge product -----------------------------------------
    print("\n9. the knowledge product")
    record = build_record(
        issue_model,
        record_id=f"mission-002-{STATION}",
        input_observations=observations,
        evidence=values_issue.evidence,
        sources=(values_adapter.source, site_adapter.source),
        produced_at=datetime.now(UTC),
        evaluation=report,
        inputs=model_inputs,
        derived_variables=(series, mean),
    )
    control = verify_lineage(record, asof=datetime.now(UTC))
    print(f"  lineage verified: {control.ok} ({len(control.checks)} checks)")
    for problem in control.problems:
        print(f"    ! {problem}")
    product = record.to_product(
        product_id=f"torne.mission-002.{STATION}.anomalie",
        version="1.0.0",
        status=ProductStatus.USABLE if control.ok else ProductStatus.DEGRADED,
        domain_of_validity=(
            f"The Mississippi at Grafton, daily mean discharge, {start} to {end}, "
            "in the station's local civil days"
        ),
        uncertainty=mean.uncertainty.statement,
        # The published outputs must share a single nature: a reconstructed
        # state and a prediction are two distinct products, not one product
        # with two labels. The reconstructed state is published here; the
        # forecast is not.
        outputs=("level", "slope"),
    )
    print(f"  product {product.product_id} v{product.version} ({product.status.value})")
    print(f"  lineage: {len(product.lineage)} reference(s)")
    statuts: dict[str, int] = {}
    for status in product.input_statuses.values():
        statuts[status.value] = statuts.get(status.value, 0) + 1
    print(f"  quality of the inputs: {dict(sorted(statuts.items()))}")

    print(f"\nraw evidence kept in: {racine}")
    return 0


def _prevoir(bloc: tuple[float | None, ...]) -> Sequence[float | None]:
    """One-step-ahead forecast of the next value, from the training block only.

    The predictor is handed the training block and nothing else: the future
    never enters it. That is what the walk-forward evaluation is for.

    The block may carry absences — the provider did not measure some days —
    and the model refuses a non-finite value. The observed points are kept,
    and the absent ones are left absent: they are not filled with a zero.
    """
    observes = [value for value in bloc if value is not None]
    if not observes:
        return [None]
    issue = execute(
        LocalLinearTrendModel(),
        ModelInputs(series={"y": tuple(observes)}),
        MODEL_PARAMETERS,
    )
    return [issue.result.outputs["forecast_level"][-1]]


def _charge(issue: AcquisitionOutcome, magasin: FileRawStore) -> dict:
    """The JSON envelope of the acquired pages, read back from the raw evidence."""
    payload: dict = {}
    for piece in issue.evidence:
        chemin = magasin.content_path(piece.evidence_id)
        payload = json.loads(chemin.read_text(encoding="utf-8"))
    return payload


def _choisir_la_serie(series: Sequence[dict]) -> dict:
    """The daily mean discharge series, chosen by its declared identity.

    It is looked up by what the provider declares — the parameter code, the
    statistic code, the computation period — and not by position in the
    list.
    """
    for feature in series:
        properties = feature.get("properties") or {}
        if (
            properties.get("parameter_code") == DEBIT_PARAMETER
            and properties.get("statistic_id") == MEAN_STATISTIC
            and properties.get("computation_period_identifier") == "Daily"
        ):
            return properties
    raise SystemExit("the daily mean discharge series was not found in the catalogue")


if __name__ == "__main__":
    sys.exit(main())
