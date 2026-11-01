"""The frontend's types are what the OpenAPI document produces.

The document is committed, the types are written from it, and this test
refuses a types file that the document no longer produces. Without it, the
frontend's types would drift from the API the first time a field changed,
and nothing would say so.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_types.py"
TYPES = ROOT / "frontend" / "src" / "types" / "api" / "generated.ts"


def test_the_generated_types_are_what_the_document_produces() -> None:
    assert TYPES.exists(), f"{TYPES} is missing; run scripts/generate_types.py"

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        "the frontend's types are not what the OpenAPI document produces; "
        f"run scripts/generate_types.py\n{result.stdout}{result.stderr}"
    )


def test_the_frontend_types_are_derived_from_the_generated_ones() -> None:
    """The frontend's own types are names for the generated schemas.

    A hand-written shape in `manifest.ts` would be a second contract, free to
    drift from the first. The only shapes written by hand are the two the
    document does not carry: the error envelope, which the exception handlers
    produce rather than a declared response model.
    """
    manifest = (ROOT / "frontend" / "src" / "types" / "api" / "manifest.ts").read_text(
        encoding="utf-8"
    )

    assert "components['schemas']" in manifest, (
        "the frontend's types must be derived from the generated schemas"
    )

    # The two shapes the document does not carry.
    assert "export interface ApiErrorBody" in manifest
    assert "export interface ApiErrorResponse" in manifest

    # No hand-written object shape is left in the file.
    for line in manifest.splitlines():
        stripped = line.strip()
        assert not stripped.startswith("export interface Api") or stripped in {
            "export interface ApiErrorBody {",
            "export interface ApiErrorResponse {",
        }, f"a hand-written shape is left in manifest.ts: {stripped}"
