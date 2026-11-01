"""HYDRO-001 — the first knowledge product of TORNE about a real French river.

The script runs the whole milestone in the order the milestone asks for:

1. **Acquire** the two feeds this access point is able to deliver — the height
   and the discharge of the whole network — and keep every byte as raw
   evidence, addressed by its fingerprint.
2. **Read** the acquired rows into TORNE's canonical observations, without
   manufacturing a station, a value, or a unit.
3. **Select** one station, by criteria that are declared before any value is
   looked at.
4. **Explore** the record of that station: coverage, completeness,
   distributions, variability, and whether anything structural changed.
5. **Fit** the relation between the published stage and the published
   discharge, and evaluate it **out of sample** — on instants the fit never
   saw — against the baselines the socle owns, with the uncertainty stated.
6. **Publish** one knowledge product: its provenance, its lineage, its
   methods, its uncertainty, its limitations, and an explicit verdict.

The protocol of step 5 is fixed **before** the results are read: it is
written in `docs/PRE-REGISTRATION-HYDRO-001.md`, and the decision rule of the
verdict is part of it. The script follows the protocol; it does not adapt it
to what it finds.

The run is reproducible: the acquisition is bounded and declared, the raw
evidence is kept, and the only inputs are the source, the criteria and the
protocol.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
import tempfile
from collections import Counter
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    # The Windows console does not default to UTF-8, and this script prints
    # instants and relations that deserve to be readable.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from torne.acquisition.adapters.hubeau_feed import SOURCE_ID, HubeauFeedAdapter
from torne.acquisition.contracts import AcquisitionOutcome, RetryPolicy
from torne.acquisition.fetcher import Fetcher
from torne.acquisition.store import FileRawStore
from torne.acquisition.transport import HttpTransport
from torne.contracts.knowledge import ProductStatus
from torne.contracts.model import ModelInputs, ModelParameters
from torne.contracts.observation import Observation
from torne.evaluation.report import evaluate_walk_forward
from torne.evaluation.uncertainty import confidence_interval
from torne.execution.runner import execute
from torne.hydrology.hubeau import (
    StationCriteria,
    observation_from_row,
    profile_stations,
    select_station,
    series_of,
    station_from_row,
)
from torne.hydrology.rating import RatingCurveModel, fit_rating_curve
from torne.knowledge.record import build_record, verify_lineage
from torne.methods.breaks import cusum_break_test
from torne.methods.calibration import Alternative, diebold_mariano

PAGE_SIZE = 2000
"""The size of a page, in rows.

The instance accepts up to 10 000 rows in a page and answers 503 when it is
asked for too much too quickly; 2 000 rows per page and the socle's patient
retry policy were measured to go through the throttle (2026-11-01).
"""

MAX_PAGES = 40
"""The depth of the walk, in pages.

It bounds the acquisition: the walk stops there, whether or not the source
would have gone on. The budget belongs to the socle, which records that the
acquisition stopped on a budget rather than on the exhaustion of the source.
"""

CRITERES = StationCriteria(
    minimum_paired_instants=16,
    minimum_completeness=0.90,
    require_single_datum=True,
    require_coordinates=True,
    require_no_missing_value=True,
    require_single_status=True,
)
"""The criteria a station must meet to be selected.

They are read on the **metadata and on the completeness** of the record, and
never on the values the station published: a station whose discharge looks
interesting is not a selected station. The number of instants is set by what
the experiment needs — a relation fitted on a window and applied to another —
and not by what any station happens to offer.
"""

TRAIN_FRACTION = 2 / 3
"""The share of the paired instants the relation is fitted on.

The remaining third is the **test window**: instants the fit never saw, which
is what makes the evaluation out of sample.
"""

MIN_TRAIN = 8
"""The smallest training window a fit is attempted on."""

RELATIVE_ERROR_LIMIT = 0.05
"""The relative reproduction error below which the relation is said to work.

Five per cent of the mean published discharge, on instants the fit never saw.
"""

SKILL_RATIO = 2.0
"""How much better than the persistence baseline the relation must be."""

MODEL_PARAMETERS = ModelParameters(values={})
"""The model has no parameter to tune: the fit is deterministic."""


def _fetcher(store: FileRawStore) -> Fetcher:
    """The socle's fetcher, with a policy patient enough for this instance.

    The instance throttles: it answers 503 when it is asked for too much too
    quickly. The default policy gives up after three attempts and a second and
    a half; this one waits.
    """
    return Fetcher(
        transport=HttpTransport(timeout=90.0),
        store=store,
        retry=RetryPolicy(
            max_attempts=6,
            initial_delay=5.0,
            multiplier=2.0,
            max_delay=120.0,
        ),
    )


def _acquire(fetcher: Fetcher, adapter: HubeauFeedAdapter, *, what: str) -> AcquisitionOutcome:
    """Acquire a feed, and refuse to go on unless the answer is usable.

    The gate is the socle's: an outcome that is not exploitable does not
    become observations.
    """
    issue = fetcher.acquire(adapter)
    verdict = issue.verdict_conformite.conformite.value if issue.verdict_conformite else "none"
    print(
        f"  {what}: {issue.status.value}, {issue.page_count} page(s), "
        f"conformity {verdict}, exploitable {issue.exploitable}"
    )
    if not issue.exploitable:
        reason = (
            issue.verdict_conformite.motif if issue.verdict_conformite else "no verdict rendered"
        )
        raise SystemExit(f"the answer to « {what} » is not usable: {reason}")
    return issue


def _rows_of(issue: AcquisitionOutcome, store: FileRawStore) -> list[tuple[dict, str, datetime]]:
    """The rows of the acquired pages, and the evidence each page belongs to.

    The interpretation always starts from the proof that was kept: the bytes
    come back from the store, addressed by their fingerprint.
    """
    pages: list[tuple[dict, str, datetime]] = []
    for piece in issue.evidence:
        path = store.content_path(piece.evidence_id)
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload.get("data") or []:
            if isinstance(row, dict):
                pages.append((row, piece.evidence_id, piece.acquired_at))
    return pages


def _observations_of(
    pages: list[tuple[dict, str, datetime]],
) -> tuple[list[Observation], int]:
    """The canonical observations of the acquired rows.

    A row without a station code cannot be attributed to a station: it is
    refused, and the refusal is counted. An observation is ingested when its
    **own** page was acquired — that is the moment the source made it
    available to us, and no other.
    """
    stations = {}
    for row, _, _ in pages:
        code = row.get("code_station")
        if isinstance(code, str) and code.strip() and code.strip() not in stations:
            stations[code.strip()] = station_from_row(row)

    observations: list[Observation] = []
    refused = 0
    for row, evidence_id, acquired_at in pages:
        code = row.get("code_station")
        if not isinstance(code, str) or not code.strip():
            refused += 1
            continue
        station = stations[code.strip()]
        try:
            observations.append(
                _observation(row, station, evidence_id=evidence_id, acquired_at=acquired_at)
            )
        except ValueError:
            refused += 1
    return observations, refused


def _observation(row: dict, station, *, evidence_id: str, acquired_at: datetime) -> Observation:
    """One observation, read from one row."""
    return observation_from_row(
        row,
        station=station,
        source_id=SOURCE_ID,
        evidence_id=evidence_id,
        acquired_at=acquired_at,
    )


def _paired(
    observations: list[Observation],
    *,
    station: str,
) -> list[tuple[datetime, float, float]]:
    """The instants where the station published both a height and a discharge.

    The pairing is by instant, and **at one station**: the two quantities must
    describe the same moment of the same station. The chronology is the
    station's own.
    """
    hauteurs = dict(
        series_of(
            [o for o in observations if o.spatial_ref == station],
            quantity="stage",
        )
    )
    debits = dict(
        series_of(
            [o for o in observations if o.spatial_ref == station],
            quantity="discharge",
        )
    )
    return [
        (instant, hauteurs[instant], debits[instant])
        for instant in sorted(set(hauteurs) & set(debits))
    ]


def _quantiles(values: list[float]) -> dict[str, float]:
    """The distribution of a series, in a few readable numbers."""
    if not values:
        return {}
    ordered = sorted(values)

    def quantile(fraction: float) -> float:
        position = fraction * (len(ordered) - 1)
        low = math.floor(position)
        high = math.ceil(position)
        if low == high:
            return ordered[low]
        return ordered[low] + (ordered[high] - ordered[low]) * (position - low)

    return {
        "min": ordered[0],
        "q1": quantile(0.25),
        "median": quantile(0.5),
        "q3": quantile(0.75),
        "max": ordered[-1],
        "mean": statistics.fmean(ordered),
        "stdev": statistics.pstdev(ordered) if len(ordered) > 1 else 0.0,
    }


def main() -> int:
    racine = Path(tempfile.mkdtemp(prefix="torne-hydro-001-"))
    store = FileRawStore(racine)
    fetcher = _fetcher(store)

    print("1. the acquisition — the two feeds the source can actually deliver")
    hauteur = _acquire(
        fetcher,
        HubeauFeedAdapter(grandeur_hydro="H", page_size=PAGE_SIZE, max_pages=MAX_PAGES),
        what="the heights of the network",
    )
    debit = _acquire(
        fetcher,
        HubeauFeedAdapter(grandeur_hydro="Q", page_size=PAGE_SIZE, max_pages=MAX_PAGES),
        what="the discharges of the network",
    )

    print("\n2. the observations")
    pages = _rows_of(hauteur, store) + _rows_of(debit, store)
    observations, refusees = _observations_of(pages)
    print(f"  {len(pages)} row(s) acquired, {len(observations)} observation(s)")
    print(f"  {refusees} row(s) refused: no station code, or a value that cannot be read")
    quantites = Counter(observation.quantity for observation in observations)
    print(f"  by quantity: {dict(sorted(quantites.items()))}")

    print("\n3. the station — selected by declared criteria")
    profils = profile_stations(row for row, _, _ in pages)
    eligibles = [
        profile
        for profile in profils
        if profile.paired_instants >= CRITERES.minimum_paired_instants
        and (profile.completeness or 0.0) >= CRITERES.minimum_completeness
    ]
    print(f"  {len(profils)} station(s) in the acquired network, {len(eligibles)} eligible")
    if not eligibles:
        raise SystemExit("no station meets the declared criteria")
    retenue = select_station(profils, CRITERES)
    print(f"  selected: {retenue.code_station} (site {retenue.code_site})")
    print(f"  {retenue.paired_instants} paired instant(s), completeness {retenue.completeness:.2%}")
    print(f"  criteria: {json.dumps(CRITERES.as_dict(), sort_keys=True)}")

    print("\n4. the exploratory profile")
    appariees = _paired(observations, station=retenue.code_station)
    if len(appariees) < MIN_TRAIN + 2:
        raise SystemExit(
            f"the selected station carries {len(appariees)} paired instant(s): too few to fit and test"
        )
    instants = [instant for instant, _, _ in appariees]
    hauteurs = [stage for _, stage, _ in appariees]
    debits = [discharge for _, _, discharge in appariees]
    profil = _quantiles(debits)
    print(f"  window: {instants[0].isoformat()} .. {instants[-1].isoformat()}")
    print(f"  sampling: {retenue.sampling_interval_minutes:.1f} min between two instants")
    print(f"  heights: {min(hauteurs):.1f} .. {max(hauteurs):.1f}")
    print(
        "  discharges: median {median:.1f}, q1 {q1:.1f}, q3 {q3:.1f}, "
        "min {min:.1f}, max {max:.1f}".format(**profil)
    )
    etendue = (max(debits) - min(debits)) / statistics.fmean(debits)
    variations = [
        abs(later - earlier) / statistics.fmean(debits) for earlier, later in pairwise(debits)
    ]
    print(
        f"  relative range {etendue:.2%}, mean absolute change {statistics.fmean(variations):.3%}"
    )
    rupture = cusum_break_test(debits)
    if math.isnan(rupture.statistic):
        print("  structural change: the test does not apply to this short a series")
    else:
        print(
            f"  structural change: CUSUM p={rupture.p_value:.4f}, "
            f"break at index {rupture.break_index} "
            f"(mean before {rupture.mean_before:.1f}, after {rupture.mean_after:.1f})"
        )

    print("\n5. the relation, and its evaluation out of sample")
    n_total = len(appariees)
    n_train = max(MIN_TRAIN, int(TRAIN_FRACTION * n_total))
    n_train = min(n_train, n_total - 2)
    n_test = n_total - n_train
    print(f"  {n_total} paired instant(s): {n_train} to fit, {n_test} to test")

    def _prevoir(bloc: tuple[float | None, ...]) -> list[float | None]:
        """The discharge the relation assigns to the stages of the test window.

        The block it receives is the **training window only**: the test
        discharges are never shown to it, and the relation it fits is the one
        the pre-registration describes.
        """
        positions = [index for index, value in enumerate(bloc) if value is not None]
        if len(positions) < 3:
            return [None] * n_test
        try:
            ajustement = fit_rating_curve(
                [hauteurs[index] for index in positions],
                [bloc[index] for index in positions],
            )
        except ValueError:
            return [None] * n_test
        return [ajustement.discharge_of(stage) for stage in hauteurs[n_train : n_train + n_test]]

    evaluation = evaluate_walk_forward(
        debits,
        _prevoir,
        initial_size=n_train,
        step=n_test,
        model_id="torne.hydrology.rating_curve",
        model_version="1.0.0",
        now=datetime.now(UTC),
    )
    rapport = evaluation.as_dict()
    for nom, metrique in rapport["metrics"].items():
        print(
            f"  model {nom}: {metrique.get('value')}, "
            f"{metrique.get('n_used')} point(s) used out of {metrique.get('n_total')}"
        )
    for nom, metriques in rapport["baseline_metrics"].items():
        valeurs = {cle: val.get("value") for cle, val in metriques.items()}
        print(f"  baseline {nom}: {valeurs}")

    # -- the uncertainty, and the verdict -----------------------------------
    predictions = list(_prevoir(tuple(debits[:n_train])))
    couples = [
        (reel, predit)
        for reel, predit in zip(debits[n_train : n_train + n_test], predictions, strict=True)
        if predit is not None
    ]
    erreurs = [reel - predit for reel, predit in couples]
    pertes_modele = [(reel - predit) ** 2 for reel, predit in couples]
    derniere = debits[n_train - 1]
    pertes_persistence = [(reel - derniere) ** 2 for reel, _ in couples]
    intervalle = confidence_interval(pertes_modele)
    test = diebold_mariano(
        pertes_modele,
        pertes_persistence,
        alternative=Alternative.LESS,
    )
    moyenne_debit = statistics.fmean(debits) if debits else 0.0
    rmse_modele = math.sqrt(statistics.fmean(pertes_modele)) if pertes_modele else float("nan")
    rmse_persistence = (
        math.sqrt(statistics.fmean(pertes_persistence)) if pertes_persistence else float("nan")
    )
    erreur_relative = rmse_modele / moyenne_debit if moyenne_debit else float("nan")
    gain = rmse_persistence / rmse_modele if rmse_modele else float("inf")
    print(f"  relative reproduction error: {erreur_relative:.4%}")
    print(
        f"  mean signed error: {statistics.fmean(erreurs):.4f}"
        if erreurs
        else "  no error computed"
    )
    print(f"  persistence error: {rmse_persistence:.4f} (rmse {rmse_modele:.4f})")
    print(f"  gain over persistence: {gain:.2f}x")
    if intervalle is not None:
        print(
            f"  95% interval on the mean squared error: "
            f"[{intervalle.low:.6f}, {intervalle.high:.6f}]"
        )
    print(f"  Diebold-Mariano (model less loss than persistence): p={test.p_value:.4f}")

    if erreur_relative <= RELATIVE_ERROR_LIMIT and gain >= SKILL_RATIO and test.p_value < 0.05:
        verdict = "SUPPORTED"
    elif rmse_modele > rmse_persistence:
        verdict = "CONTRADICTED"
    else:
        verdict = "INCONCLUSIVE"
    print(f"  verdict: {verdict}")

    # -- the published relation --------------------------------------------
    print("\n6. the model, and the knowledge product")
    ajuste = fit_rating_curve(hauteurs[:n_train], debits[:n_train])
    model_inputs = ModelInputs(
        series={
            "stage": tuple(hauteurs[:n_train]),
            "discharge": tuple(debits[:n_train]),
        }
    )
    issue_model = execute(
        RatingCurveModel(
            question=(
                f"Is the discharge published for {retenue.code_station} a deterministic "
                "function of the height it publishes?"
            ),
            domain_of_validity=(
                f"Station {retenue.code_station} (site {retenue.code_site}), the "
                f"{n_train} instants of the training window, the stage in the source's own unit"
            ),
        ),
        model_inputs,
        MODEL_PARAMETERS,
        now=datetime.now(UTC),
    )
    print(f"  relation fitted: exponent {ajuste.slope:.4f}, r2 {ajuste.r2:.6f}")
    print(
        f"  model executed: {issue_model.result.spec.model_id} v{issue_model.result.spec.version}"
    )

    observations_station = [
        observation
        for observation in observations
        if observation.spatial_ref == retenue.code_station
    ]
    publie = datetime.now(UTC)
    record = build_record(
        issue_model,
        record_id=f"hydro-001-{retenue.code_station}",
        input_observations=observations_station,
        evidence=hauteur.evidence + debit.evidence,
        sources=(
            HubeauFeedAdapter(grandeur_hydro="H", page_size=PAGE_SIZE, max_pages=MAX_PAGES).source,
        ),
        produced_at=publie,
        evaluation=rapport,
        inputs=model_inputs,
    )
    control = verify_lineage(record, asof=publie)
    print(f"  lineage verified: {control.ok} ({len(control.checks)} checks)")
    for problem in control.problems:
        print(f"    ! {problem}")
    product = record.to_product(
        product_id=f"torne.hydro-001.hubeau.{retenue.code_station}.relation",
        version="1.0.0",
        status=ProductStatus.USABLE if control.ok else ProductStatus.DEGRADED,
        domain_of_validity=(
            f"Station {retenue.code_station} (site {retenue.code_site}), "
            f"the {n_train} instants of the training window; the stage is expressed in "
            "the source's own unit, which the source does not publish"
        ),
        uncertainty=(
            f"Out of sample on {n_test} instant(s) the relation reproduced the published "
            f"discharge with a relative error of {erreur_relative:.2%} "
            f"(rmse {rmse_modele:.3f} against {rmse_persistence:.3f} for the persistence "
            f"baseline); Diebold-Mariano p={test.p_value:.3f}. Verdict: {verdict}."
        ),
        outputs=("discharge_estimated",),
    )
    print(f"  product {product.product_id} v{product.version} ({product.status.value})")
    print(f"  lineage: {len(product.lineage)} reference(s)")
    print(f"\nraw evidence kept in: {racine}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
