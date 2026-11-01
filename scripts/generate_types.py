"""Generate the frontend's TypeScript types from the API's OpenAPI document.

The document is committed at `frontend/src/types/api/openapi.json` and is
written by the application itself. The types are written from that document,
so they cannot drift from the API: a field that changes in the API changes
here too.

    python scripts/generate_types.py                      # write the types
    python scripts/generate_types.py --check              # fail when they are stale

Why this is written here rather than taken from a package: the standard
generator declares a peer dependency on TypeScript 5, and the project is on
TypeScript 6; and it reads a fixed-length array as an array of any length,
where the document says exactly how long it is. Both are small, and both
matter more than the convenience of a dependency.
"""

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "frontend" / "src" / "types" / "api" / "openapi.json"
TYPES = ROOT / "frontend" / "src" / "types" / "api" / "generated.ts"

HEADER = """/**
 * The API's types, generated from the OpenAPI document.
 *
 * This file is written by `scripts/generate_types.py` from
 * `frontend/src/types/api/openapi.json`, which the application itself writes.
 * It must not be edited by hand: the test suite refuses a file that the
 * document no longer produces.
 *
 * The document's own descriptions are carried over, so the contract the
 * reader sees is the contract the API publishes.
 */
"""


def reference(name: str) -> str:
    """A reference to another schema of the document."""
    return f'components["schemas"]["{name}"]'


def ts_type(schema: Any) -> str:
    """The TypeScript type of an OpenAPI schema."""
    if not isinstance(schema, dict) or schema == {}:
        return "unknown"

    if "$ref" in schema:
        return reference(str(schema["$ref"]).rsplit("/", 1)[-1])

    if "enum" in schema:
        return " | ".join(json.dumps(value) for value in schema["enum"])

    if "anyOf" in schema:
        return " | ".join(ts_type(option) for option in schema["anyOf"])

    kind = schema.get("type")

    if kind == "array":
        if "prefixItems" in schema:
            # A fixed-length array: the document says how long it is.
            return "[{}]".format(", ".join(ts_type(item) for item in schema["prefixItems"]))
        item = ts_type(schema.get("items", {}))
        if " | " in item:
            item = f"({item})"
        return f"{item}[]"

    if kind == "object":
        properties = schema.get("properties")
        if not properties:
            return "Record<string, unknown>"
        required = set(schema.get("required", []))
        members = []
        for name, member in properties.items():
            optional = "" if name in required else "?"
            members.append(f"{name}{optional}: {ts_type(member)};")
        return "{ " + " ".join(members) + " }"

    if kind in {"integer", "number"}:
        return "number"
    if kind == "boolean":
        return "boolean"
    if kind == "null":
        return "null"
    if kind == "string":
        return "string"

    return "unknown"


def documentation(schema: dict, indent: str) -> list[str]:
    """The doc comment of a schema or of one of its members."""
    description = schema.get("description")
    title = schema.get("title")
    if not description and not title:
        return []

    lines = [f"{indent}/**"]
    if description:
        for line in str(description).splitlines():
            lines.append(f"{indent} * {line}")
    elif title:
        lines.append(f"{indent} * {title}")
    lines.append(f"{indent} */")
    return lines


def emit_member(name: str, schema: dict, required: list[str], indent: str) -> list[str]:
    """One member of an object schema."""
    lines = documentation(schema, indent)
    optional = "" if name in required else "?"
    lines.append(f"{indent}{name}{optional}: {ts_type(schema)};")
    return lines


def emit_object(properties: dict, required: list[str], indent: str) -> list[str]:
    """The body of an object schema."""
    lines: list[str] = []
    for name, member in properties.items():
        lines.extend(emit_member(name, member, required, indent))
    return lines


def emit_schemas(schemas: dict) -> list[str]:
    """Every schema of the document, as TypeScript."""
    lines: list[str] = ["export interface components {", "    schemas: {"]
    for name in sorted(schemas):
        schema = schemas[name]
        lines.extend(documentation(schema, "        "))
        properties = schema.get("properties")
        if properties:
            lines.append(f"        {name}: {{")
            lines.extend(emit_object(properties, schema.get("required", []), "            "))
            lines.append("        };")
        else:
            lines.append(f"        {name}: {ts_type(schema)};")
    lines.append("    };")
    lines.append("}")
    return lines


def render(document: dict) -> str:
    """The whole generated file."""
    lines = [HEADER]
    lines.extend(emit_schemas(document.get("components", {}).get("schemas", {})))
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    check = "--check" in (argv if argv is not None else sys.argv[1:])

    document = json.loads(DOCUMENT.read_text(encoding="utf-8"))
    content = render(document)

    if check:
        if not TYPES.exists():
            print(f"{TYPES} does not exist")
            return 1
        if TYPES.read_text(encoding="utf-8") != content:
            print(f"{TYPES} is not what the document produces; run scripts/generate_types.py")
            return 1
        print(f"{TYPES} is what the document produces")
        return 0

    TYPES.parent.mkdir(parents=True, exist_ok=True)
    TYPES.write_text(content, encoding="utf-8")
    print(f"{TYPES} written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
