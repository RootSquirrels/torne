"""The static files of the compiled application.

The application has real routes — `/country/FR`, `/mission/ATMO-001`,
`/workbench` — and a route the browser asks for directly must answer with
the application, not with a 404: the application then reads the path and
renders the right view.

The fallback is deliberately narrow:

- a file that exists is served as it is;
- an **API** path is never answered with the application. A request for an
  unknown endpoint is an error, and it is answered as one;
- a path that names a file is an error too: a missing asset is not a page;
- anything else is answered with the application itself.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import Scope

__all__ = ["ApplicationFiles", "mount_frontend"]

ASSET_CACHE_CONTROL = "public, max-age=31536000, immutable"
"""The rule of the files under `/assets/`.

Their name carries a hash of their content: a new build ships a new name, so
the file behind that name never changes and may be kept for a year. The
browser is told so, because a browser that knows a file never changes does
not ask for it again.
"""

REVALIDATE_CACHE_CONTROL = "no-cache"
"""The rule of every other file the application serves.

The HTML names the hashed assets: a stale HTML would name assets that no
longer exist. The icon and the map data are replaced under the same name by a
new build. None of them may be kept without asking, so the browser asks —
and the file answers with its own ETag, which makes the answer a cheap
`304` rather than a download.
"""


class ApplicationFiles(StaticFiles):
    """The compiled application, with the fallback of a single-page application."""

    def __init__(self, *args: object, api_prefixes: tuple[str, ...] = (), **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self._api_prefixes = api_prefixes

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as error:
            if error.status_code != 404:
                raise
            if not self._is_page(scope):
                # An unknown endpoint or a missing asset is an error, not a page.
                raise
            response = await super().get_response("index.html", scope)
            response.headers["Cache-Control"] = REVALIDATE_CACHE_CONTROL
            return response
        response.headers["Cache-Control"] = _cache_control_for(path)
        return response

    def _is_page(self, scope: Scope) -> bool:
        """Whether the request asks for a page of the application.

        The path is read from the scope, not from the argument of
        `get_response`: inside a mount, that argument is relative to the
        mount and carries the separator of the operating system.
        """
        path = scope.get("path", "")
        if any(path == prefix or path.startswith(f"{prefix}/") for prefix in self._api_prefixes):
            return False
        return not _names_a_file(path)


def _names_a_file(path: str) -> bool:
    """Whether the path names a file rather than a page.

    `/country/FR` names a page; `/assets/app.js` names a file. The extension
    is the only difference, and it is the difference the browser cares about:
    a missing script must fail as a missing script.
    """
    return "." in path.rsplit("/", 1)[-1]


def _cache_control_for(path: str) -> str:
    """The cache rule of a file the application serves.

    The path is relative to the mount and carries the separator of the
    operating system, so it is normalised before it is read.
    """
    normalised = path.replace("\\", "/")
    if normalised.startswith("assets/"):
        return ASSET_CACHE_CONTROL
    return REVALIDATE_CACHE_CONTROL


def mount_frontend(
    application: FastAPI,
    static_dir: Path,
    *,
    api_prefixes: tuple[str, ...] = ("/api",),
) -> bool:
    """Serve the compiled application at the root. Returns whether it was mounted."""
    if not static_dir.is_dir():
        return False
    application.mount(
        "/",
        ApplicationFiles(directory=static_dir, html=True, api_prefixes=api_prefixes),
        name="frontend",
    )
    return True
