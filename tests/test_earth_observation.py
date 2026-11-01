"""The earth-observation contract — a field, not a value.

`Observation` says what a source measured, at an instant, in its own terms.
An earth observation says the same thing about something that covers a
**surface**: a footprint, a grid, a window of integration, and assets that have
to be fetched before anything can be read.

These tests check that the contract refuses what it cannot describe, and
describes what it accepts. The refusals are the point: an observation of
surface that carried a scalar value would say something false about the data,
and an observation of surface without a window would say nothing at all.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from torne.contracts.earth_observation import (
    Asset,
    EarthObservation,
    ObservationNature,
)
from torne.contracts.observation import QualityStatus
from torne.contracts.spatial import BoundingBox, Footprint, RasterGrid, SpatialRef
from torne.contracts.time import PublicationState, TemporalStamp

VALIDITE = datetime(2023, 6, 30, 12, 0, 1, tzinfo=UTC)
CONSERVE = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
PUBLIE = datetime(2025, 3, 26, tzinfo=UTC)


def _empreinte() -> Footprint:
    return Footprint.from_bounding_box(
        BoundingBox(west=5.5, south=43.5, east=10.5, north=51.0),
        ref=SpatialRef.epsg("4326"),
    )


def _actif() -> Asset:
    return Asset(key="swi010", href="https://exemple.test/swi010.tif", media_type="image/tiff")


def _observation(**kwargs) -> EarthObservation:
    defauts: dict[str, object] = {
        "observation_id": "elt-1",
        "source_id": "copernicus.dataspace.stac",
        "quantity": "soil_water_index",
        "unit": "1",
        "temporal": TemporalStamp(
            valid_time=VALIDITE,
            known_at=PUBLIE,
            ingested_at=CONSERVE,
            publication=PublicationState.ESTABLISHED,
        ),
        "evidence_id": "ev-1",
        "footprint": _empreinte(),
        "window_start": VALIDITE,
        "window_end": VALIDITE + timedelta(days=1),
        "assets": (_actif(),),
    }
    defauts.update(kwargs)
    return EarthObservation(**defauts)


# --------------------------------------------------------------------------
# What it refuses
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "champ",
    ["observation_id", "source_id", "quantity", "unit", "evidence_id"],
)
def test_an_observation_needs_an_identity(champ):
    with pytest.raises(ValueError, match="is required and non-empty"):
        _observation(**{champ: "  "})


def test_a_window_that_runs_backwards_is_refused():
    with pytest.raises(ValueError, match="does not run backwards"):
        _observation(
            window_start=VALIDITE,
            window_end=VALIDITE - timedelta(days=1),
        )


def test_the_validity_instant_and_the_window_must_say_the_same_thing():
    """One truth about the instant: the two cannot contradict each other."""
    with pytest.raises(ValueError, match="cannot diverge"):
        _observation(
            temporal=TemporalStamp(
                valid_time=VALIDITE - timedelta(days=5),
                known_at=PUBLIE,
                ingested_at=CONSERVE,
                publication=PublicationState.ESTABLISHED,
            ),
        )


def test_an_observation_without_a_validity_instant_is_refused():
    with pytest.raises(ValueError, match="carries its validity instant"):
        _observation(
            temporal=TemporalStamp(
                valid_time=None,
                known_at=PUBLIE,
                ingested_at=CONSERVE,
                publication=PublicationState.ESTABLISHED,
            ),
        )


def test_an_observation_without_an_asset_is_a_promise_not_an_observation():
    with pytest.raises(ValueError, match="at least one asset"):
        _observation(assets=())


def test_an_observation_cannot_be_the_revision_of_itself():
    with pytest.raises(ValueError, match="revision of itself"):
        _observation(revision_of="elt-1")


def test_an_observation_refuses_an_unknown_quality_status():
    with pytest.raises(TypeError):
        _observation(quality_status="approuve")


def test_an_observation_refuses_a_nature_it_does_not_know():
    with pytest.raises(TypeError):
        _observation(nature="mesure")


# --------------------------------------------------------------------------
# What it says
# --------------------------------------------------------------------------


def test_an_observation_states_its_spatial_reference_in_the_source_terms():
    assert _observation().spatial_ref == "EPSG:4326"


def test_an_observation_covers_the_period_it_integrates_not_only_its_instant():
    observation = _observation()

    assert observation.covers_instant(VALIDITE + timedelta(hours=6))
    assert not observation.covers_instant(VALIDITE - timedelta(days=1))
    assert not observation.covers_instant(VALIDITE + timedelta(days=2))


def test_an_observation_is_usable_only_once_its_publication_is_established():
    """`usable_at` is derived, never stored, and it needs the conservation instant."""
    assert _observation().is_usable is True

    sans_conservation = _observation(
        temporal=TemporalStamp(
            valid_time=VALIDITE,
            known_at=PUBLIE,
            ingested_at=None,
            publication=PublicationState.ESTABLISHED,
        )
    )
    assert sans_conservation.is_usable is False


def test_the_lateness_of_publication_is_visible_on_the_observation():
    """A product published in 2025 describes 2023: that delay is the point."""
    observation = _observation()

    assert observation.temporal.known_at == PUBLIE
    assert observation.temporal.known_at - observation.window_start == timedelta(
        days=634, hours=11, minutes=59, seconds=59
    )


def test_the_nature_of_a_measurement_is_left_unclassified_by_default():
    assert _observation().nature is None
    assert _observation(nature=ObservationNature.DERIVED).nature is ObservationNature.DERIVED


# --------------------------------------------------------------------------
# The assets
# --------------------------------------------------------------------------


def test_an_asset_needs_a_key_and_an_address():
    with pytest.raises(ValueError, match=r"Asset\.key is required"):
        Asset(key="", href="https://exemple.test/a.tif")
    with pytest.raises(ValueError, match=r"Asset\.href is required"):
        Asset(key="a", href="")


def test_an_asset_declares_when_it_needs_a_credential():
    """The deposit holds no secret: a protected asset is declared, not fetched."""
    protege = Asset(key="Product", href="https://exemple.test/p.zip", requires_authentication=True)

    assert protege.requires_authentication is True


def test_an_asset_refuses_a_negative_size():
    with pytest.raises(ValueError, match="cannot be negative"):
        Asset(key="a", href="https://exemple.test/a.tif", size_bytes=-1)


def test_an_asset_carries_its_own_grid():
    grid = RasterGrid.from_transform(
        ref=SpatialRef.epsg("4326"),
        transform=[0.0089285714285712, 0.0, -11.0, 0.0, -0.0089285714285694, 71.9999999999916],
        shape=[4144, 6832],
    )

    actif = Asset(key="swi010", href="https://exemple.test/a.tif", grid=grid)

    assert actif.grid is not None
    assert actif.grid.width == 6832


def test_the_quality_status_of_an_observation_is_unknown_until_the_producer_says():
    """The safe choice is the one that does not flatter the source."""
    assert _observation().quality_status is QualityStatus.UNKNOWN
