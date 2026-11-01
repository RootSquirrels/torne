"""Coherent error responses.

Every failure the API returns carries the same shape:

```json
{
  "detail": "unknown mission 'NOPE'",
  "error": {"code": "not_found", "message": "unknown mission 'NOPE'", "details": null}
}
```

`detail` keeps the field FastAPI has always returned, so a consumer written
against the previous API keeps working unchanged. `error` adds the stable,
machine-readable code that a new consumer can branch on.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .schemas.common import ErrorBody, ErrorResponse

__all__ = ["ErrorResponse", "install_error_handlers"]

_CODES: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "bad_request",
    status.HTTP_401_UNAUTHORIZED: "unauthorized",
    status.HTTP_403_FORBIDDEN: "forbidden",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
    status.HTTP_409_CONFLICT: "conflict",
    422: "unprocessable_entity",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "internal_error",
    status.HTTP_503_SERVICE_UNAVAILABLE: "service_unavailable",
}
"""The stable code for each HTTP status.

422 is written as a literal: Starlette renamed its constant and the old name
now warns, while the number has not changed.
"""


def _code_for(status_code: int) -> str:
    return _CODES.get(status_code, "error")


def _message(detail: Any) -> str:
    """A readable message, whether the detail is a string or a structure."""
    if isinstance(detail, str):
        return detail
    return str(detail)


def install_error_handlers(app: FastAPI) -> None:
    """Give every failure of the application the same shape."""

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = _message(exc.detail)
        body = ErrorResponse(
            detail=message,
            error=ErrorBody(code=_code_for(exc.status_code), message=message),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=body.model_dump(),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        message = "the request does not match the API's expectations"
        body = ErrorResponse(
            detail=message,
            error=ErrorBody(
                code="validation_error",
                message=message,
                details={"errors": _safe_errors(exc)},
            ),
        )
        return JSONResponse(status_code=422, content=body.model_dump())


def _safe_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    """The validation errors, with anything unserialisable turned into text."""
    safe: list[dict[str, Any]] = []
    for error in exc.errors():
        entry = {key: value for key, value in error.items() if key != "ctx"}
        entry["ctx"] = {key: str(value) for key, value in (error.get("ctx") or {}).items()}
        safe.append(entry)
    return safe


def not_found(what: str, value: str) -> HTTPException:
    """The error for an identifier the catalogue does not hold."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"unknown {what} {value!r}")


def unprocessable(message: str) -> HTTPException:
    """The error for a request the API understands but cannot answer."""
    return HTTPException(status_code=422, detail=message)
