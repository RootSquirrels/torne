"""The hydrology semantic layer — what the numbers of a stream mean.

The socle acquires and keeps raw evidence, and says whether what came back
answers the question asked. This package is the layer above it: it reads a
provider's records as **observations** of a physical quantity, and computes
the first derived quantity of the real world from them.

It is the first package of the domain. It knows about discharge, gage
height, water days and flow anomalies. The socle knows about none of it, and
the domain knows about no particular provider's query format — the two meet
at the adapter.
"""

from .anomaly import (
    Climatology,
    ClimatologyDay,
    NormalsGap,
    anomalies,
    anomaly_index,
    climatology,
    compare_with_published_normals,
    mean_anomaly,
    published_normals_by_day,
)
from .observations import (
    DAY_CONVENTION,
    MISSING_VALUE,
    InterpretationError,
    Station,
    continuous_observation,
    observation_from_feature,
    station_from_feature,
    time_series,
)

__all__ = [
    "DAY_CONVENTION",
    "MISSING_VALUE",
    "Climatology",
    "ClimatologyDay",
    "InterpretationError",
    "NormalsGap",
    "Station",
    "anomalies",
    "anomaly_index",
    "climatology",
    "compare_with_published_normals",
    "continuous_observation",
    "mean_anomaly",
    "observation_from_feature",
    "published_normals_by_day",
    "station_from_feature",
    "time_series",
]
