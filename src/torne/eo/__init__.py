"""The semantic layer of surface observation.

The acquisition socle can ask the Copernicus Data Space catalogue questions and
keep what it receives. It knows neither what a soil moisture index is, nor what
a footprint is, nor what a product owes to the reanalysis. This layer is there
for that.

It holds three modules:

- `products` — the **registry**: what each known collection is, what it covers,
  and what it depends on. The registry carries the *dependence ledger*: without
  it, a "one data family at a time" comparison would not compare independent
  families;
- `observations` — the **reading**: a catalogue item becomes an
  `EarthObservation`, or an `InterpretationError`;
- `coverage` — the **coverage**: what a product allows to reconstruct, and from
  when.

It depends only on the contracts (`torne.contracts`) and on the socle
(`torne.acquisition`): never the reverse. That is the repository's rule: a
connector does not know how to reconstruct a physical state, and a semantic
layer does not know what the data it reads are worth.
"""

from .observations import (
    CatalogueTimes,
    InterpretationError,
    catalogue_times,
    observation_from_item,
    publication_latency,
)
from .products import (
    SURFACE_PRODUCTS,
    MeteorologicalDependence,
    SurfaceProduct,
    known_product,
)

__all__ = [
    "SURFACE_PRODUCTS",
    "CatalogueTimes",
    "InterpretationError",
    "MeteorologicalDependence",
    "SurfaceProduct",
    "catalogue_times",
    "known_product",
    "observation_from_item",
    "publication_latency",
]
