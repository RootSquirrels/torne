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

    description: str = (
        "Read-only view of what TORNE has really established.\n\n"
        "**The canonical prefix is `/api/v1`.** It is the only prefix this document describes.\n\n"
        "**The legacy prefix `/api` still answers.** It answers the same questions as "
        "`/api/v1`, marks every answer with `Deprecation: true`, and names its successor "
        "in a `Link` header. A consumer that follows the header has migrated itself.\n\n"
        "**The removal rule.** The legacy prefix will be removed in **one announced step**, "
        "once the first application published outside this repository consumes `/api/v1`. "
        "It is never removed as a side effect of another change: the step is announced in "
        "this document and recorded in the commit that makes it. Until then, the legacy "
        "prefix is a supported surface, and its answers carry the headers that say so."
    )

    @property
    def serves_frontend(self) -> bool:
        """Whether a compiled frontend is present to serve."""
        return self.static_dir.is_dir()


DEFAULT_SETTINGS = ExplorerSettings()
