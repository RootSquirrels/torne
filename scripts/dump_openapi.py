"""Write the API's OpenAPI document to a file.

The frontend's types are generated from this document, so it has to be written
by the application itself: the document FastAPI builds *is* the contract, not
a description of it. A hand-written copy of it would drift the first time a
field changed.

    python scripts/dump_openapi.py frontend/src/types/api/openapi.json
    python scripts/dump_openapi.py --check frontend/src/types/api/openapi.json

The second form is what the test suite runs: it refuses a committed document
that the application no longer builds.
"""

import argparse
import json
import sys
from pathlib import Path


def build_document() -> str:
    """The document the application serves, as text."""
    from torne.explorer.api.application import app

    return json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", help="where the OpenAPI document is written")
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when the file differs from the document the application builds",
    )
    args = parser.parse_args(argv)

    document = build_document()
    target = Path(args.output)

    if args.check:
        if not target.exists():
            print(f"{target} does not exist")
            return 1
        if target.read_text(encoding="utf-8") != document:
            print(
                f"{target} is not the document the application builds; "
                f"run scripts/dump_openapi.py {target}"
            )
            return 1
        print(f"{target} is the document the application builds")
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(document, encoding="utf-8")
    print(f"{target} written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
