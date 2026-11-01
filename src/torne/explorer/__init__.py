"""TORNE Explorer — a read-only view of what the repository has really produced.

The explorer is an **application** (`docs/ARCHITECTURE.md` §5). Three
constraints bind it:

1. it performs no scientific computation and never calls a data provider;
2. it only shows metadata and results the repository has actually established;
3. it never shapes the scientific engines to its own display needs.

It is made of three parts:

- `catalogue` — the established facts the explorer shows: missions, their
  nature and status, the physical assets they touched, the sources they read.
  Every entry is checked against the code it points to;
- `manifest` — a JSON projection of the catalogue, of the surface-product
  registry (`torne.eo`) and of the adapters, built with the standard library
  only;
- `api` — a FastAPI application serving the manifest and the map front end. It
  requires the optional `explorer` extra.
"""

from .catalogue import ASSETS, MISSIONS, MODELS, SOURCES, Status
from .manifest import build_manifest

__all__ = ["ASSETS", "MISSIONS", "MODELS", "SOURCES", "Status", "build_manifest"]
