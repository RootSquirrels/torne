"""Source adapters — ask a question, and nothing more.

An adapter knows how to **ask** a provider: it builds a URL, says how the
source is walked, and returns the next question or `None`. It **interprets
nothing**: no hydrology, no meteorology, no surface observation. That is the
separation the programme imposes — "a connector must not know how to
reconstruct a physical state" (`docs/ARCHITECTURE.md`).

Each adapter verifies the response it receives against what it asked
(`verdict_conformite`), on the rows that came back, never on the URL:

- `hubeau` / `hubeau_feed`: Hub'EAU v2 real-time hydrometry (France), cursor
  pagination; `hubeau` asks for stations and windows the instance ignores,
  `hubeau_feed` asks only what the source can answer;
- `usgs` / `usgs_ogc`: USGS Water Services and the OGC API (United States);
- `copernicus` / `copernicus_stac`: Copernicus Data Space, the OData product
  catalogue and the STAC surface-observation catalogue;
- `enagas`: the Enagas daily system report (Spain) — one gas day per request,
  the state of the seven LNG import terminals;
- `ghcnd`: NOAA GHCN-Daily station records;
- `meteofrance`: Météo-France observation API and daily climatological API
  (DPClim), behind an API key held by reference (`torne.acquisition.credentials`).
"""

from __future__ import annotations

from .copernicus import CopernicusProductsAdapter
from .copernicus_stac import CopernicusStacAdapter
from .enagas import EnagasDailyAdapter
from .ghcnd import GhcndDailyAdapter
from .hubeau import HubeauObservationsAdapter
from .hubeau_feed import HubeauFeedAdapter
from .meteofrance import DailyClimatologyAdapter, MeteoFranceAdapter
from .usgs import UsgsInstantaneousValuesAdapter
from .usgs_ogc import UsgsObservationNormalsAdapter, UsgsOgcItemsAdapter

__all__ = [
    "CopernicusProductsAdapter",
    "CopernicusStacAdapter",
    "DailyClimatologyAdapter",
    "EnagasDailyAdapter",
    "GhcndDailyAdapter",
    "HubeauFeedAdapter",
    "HubeauObservationsAdapter",
    "MeteoFranceAdapter",
    "UsgsInstantaneousValuesAdapter",
    "UsgsObservationNormalsAdapter",
    "UsgsOgcItemsAdapter",
]
