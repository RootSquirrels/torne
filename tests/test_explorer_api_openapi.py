"""The frontend's types are generated from the document the API actually serves.

The OpenAPI document is committed at `frontend/src/types/api/openapi.json`, and
the TypeScript types are generated from it. This test refuses a committed
document that the application no longer builds: without it, the frontend's
types would drift from the API the first time a field changed, and nothing
would say so.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "frontend" / "src" / "types" / "api" / "openapi.json"
SCRIPT = ROOT / "scripts" / "dump_openapi.py"


def test_the_committed_openapi_document_is_the_one_the_application_serves() -> None:
    assert DOCUMENT.exists(), f"{DOCUMENT} is missing; run scripts/dump_openapi.py {DOCUMENT}"

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check", str(DOCUMENT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        "the committed OpenAPI document is not the document the application builds; "
        f"run scripts/dump_openapi.py {DOCUMENT}\n{result.stdout}{result.stderr}"
    )


def test_the_openapi_document_declares_every_response_model() -> None:
    """A route without a response model leaves the document a guess."""

    document = json.loads(DOCUMENT.read_text(encoding="utf-8"))

    schemas = document.get("components", {}).get("schemas", {})
    for name in ("Manifest", "CountryDetail", "Mission", "CoverageEntry", "Results"):
        assert name in schemas, f"the schema {name} is not declared in the OpenAPI document"

    for path, operations in document.get("paths", {}).items():
        for method, operation in operations.items():
            if method not in {"get", "post", "put", "delete", "patch"}:
                continue
            responses = operation.get("responses", {})
            assert responses, f"{method.upper()} {path} declares no response"
            for status, response in responses.items():
                if not status.startswith("2"):
                    continue
                assert "content" in response, (
                    f"{method.upper()} {path} answers {status} without a body"
                )
