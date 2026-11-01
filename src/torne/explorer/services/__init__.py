"""The read services of the explorer.

A service answers a question about the catalogue: what the missions are, what
a country holds, which periods are covered. It reads the derived projection
and answers; it never computes a scientific quantity and never calls a
provider.
"""

from .catalogue_service import UnknownStatus

__all__ = ["UnknownStatus"]
