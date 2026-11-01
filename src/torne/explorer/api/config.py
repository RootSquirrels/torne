"""The configuration of the explorer application."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

__all__ = ["DEFAULT_SETTINGS", "PACKAGE_ROOT", "STATIC_DIR", "ExplorerSettings"]

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
"""The `torne.explorer` package directory."""

STATIC_DIR = PACKAGE_ROOT / "static"
"""Where the compiled frontend lives, inside the Python package."""


@dataclass(frozen=True, slots=True)
class ExplorerSettings:
    """What the application needs to know about itself.

    The defaults are the ones the package ships with; the dataclass exists so
    that a test can point the application at a different static directory
    without touching the filesystem layout.
    """

    static_dir: Path = STATIC_DIR
    """The directory the compiled frontend is served from."""

    api_prefix: str = "/api/v1"
    """The canonical API prefix."""

    legacy_api_prefix: str = "/api"
    """The prefix kept for compatibility during the transition to the canonical one."""

    title: str = "TORNE Explorer"
    description: str = "Read-only view of what TORNE has really established."

    @property
    def serves_frontend(self) -> bool:
        """Whether a compiled frontend is present to serve."""
        return self.static_dir.is_dir()


DEFAULT_SETTINGS = ExplorerSettings()
