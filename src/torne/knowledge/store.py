"""The published knowledge records: what is on disk, and how it is read.

A knowledge product is published by writing it down. The format is deliberately
plain: one JSON file per version, carrying the `KnowledgeProduct` contract,
and beside it the payload the record points at.

Three rules shape the store:

1. **A published product is never rewritten** (INV-31). A correction produces a
   **new** version, and the old one stays consultable. Writing over a version
   whose payload or whose record differs is refused; writing the same
   publication again is a no-op, so a publication can be re-run without ceremony
   and without ceremony breaking the rule that matters.
2. **The store computes nothing and calls no provider.** It reads and writes
   files. A product that is not on disk is not a product.
3. **An absent product is an absence**, never an empty value: asking for a
   product or a version that was never published raises `RecordNotFound`. A
   reader is never handed an empty series that looks like a measurement.

The store is the first application-independent half of the publication chain.
It knows nothing about gas, nothing about hydrology and nothing about the
Explorer: it holds products, and it holds them the way `KnowledgeProduct`
says they must be held.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..contracts.fingerprint import fingerprint, fingerprint_bytes
from ..contracts.knowledge import KnowledgeProduct, ProductStatus, ProvenanceKind, ProvenanceRef
from ..contracts.model import ResultNature
from ..contracts.observation import QualityStatus

__all__ = [
    "RECORD_FILE",
    "RECORD_FORMAT",
    "RecordExists",
    "RecordNotFound",
    "StoredRecord",
    "list_products",
    "list_versions",
    "load_record",
    "read_record",
    "records_root",
    "write_record",
]

RECORD_FILE = "record.json"
"""The name of the file that carries the record itself."""

RECORD_FORMAT = 1
"""The version of the on-disk format.

It changes when the shape of the file changes in a way a reader would notice.
A reader that does not know the version refuses the file rather than guessing.
"""


class RecordNotFound(LookupError):
    """The product, or the version of it, was never published."""


class RecordExists(FileExistsError):
    """A version is already published, with a different payload.

    A product is not rewritten: a correction is a new version.
    """


@dataclass(frozen=True, slots=True)
class StoredRecord:
    """A published record, and where it lives on disk."""

    product_id: str
    version: str
    record: KnowledgeProduct
    directory: Path
    payload: Mapping[str, Path]
    payload_digest: str
    """The digest of the payload as it was published."""


def records_root() -> Path:
    """Where the published records live, inside the package."""
    return Path(__file__).resolve().parent / "records"


def _digest(payload: Mapping[str, bytes]) -> str:
    """The digest of a payload: the digest of each file, then of the set.

    The digest of a set is the digest of the digests, so it does not depend on
    the order the files were written in.
    """
    return fingerprint({name: fingerprint_bytes(payload[name]) for name in sorted(payload)})


def _product_directory(root: Path, product_id: str) -> Path:
    return root / product_id


def _version_directory(root: Path, product_id: str, version: str) -> Path:
    return _product_directory(root, product_id) / version


def write_record(
    root: Path,
    product: KnowledgeProduct,
    payload: Mapping[str, bytes],
) -> Path:
    """Publish a product, and write it under `root`.

    The payload is written beside the record, and its digest is written into
    the record, so a reader can tell whether the payload it reads is the one
    that was published.

    Writing a version that already exists with the **same** payload and the
    **same** record returns the path and changes nothing: publication is
    re-runnable. Writing it with a different payload raises `RecordExists`,
    and so does writing it with a different record: that is a rewrite, and a
    product is not rewritten — its description included.
    """
    directory = _version_directory(root, product.product_id, product.version)
    digest = _digest(payload)

    if directory.exists():
        existing = json.loads((directory / RECORD_FILE).read_text(encoding="utf-8"))
        existing_digest = str(existing["payload_digest"])
        if existing_digest != digest:
            raise RecordExists(
                f"{product.product_id} version {product.version} is already published with a "
                "different payload: a correction is a new version, not a rewrite"
            )
        if existing.get("product") != product.as_dict():
            raise RecordExists(
                f"{product.product_id} version {product.version} is already published with a "
                "different record: the product is not rewritten, its description included. "
                "A correction is a new version"
            )
        read_record(directory / RECORD_FILE)
        _verify_payload(directory, existing_digest)
        return directory

    directory.mkdir(parents=True, exist_ok=True)
    for name, content in sorted(payload.items()):
        (directory / name).write_bytes(content)

    document = {
        "format": RECORD_FORMAT,
        "payload_digest": digest,
        "product": product.as_dict(),
    }
    (directory / RECORD_FILE).write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return directory


def _read_digest(path: Path) -> str:
    document = json.loads(path.read_text(encoding="utf-8"))
    return str(document["payload_digest"])


def _verify_payload(directory: Path, digest: str) -> None:
    """Refuse a payload that is not the one that was published."""
    payload: dict[str, bytes] = {}
    for path in sorted(directory.iterdir()):
        if path.name == RECORD_FILE or not path.is_file():
            continue
        payload[path.name] = path.read_bytes()
    if _digest(payload) != digest:
        raise RecordNotFound(
            f"the payload published in {directory} does not match the digest its record carries"
        )


def read_record(path: Path) -> KnowledgeProduct:
    """Read a published record.

    The record is rebuilt into the contract, not into a dictionary: the
    contract's own checks run again on the way in, so a record whose lineage
    and input statuses no longer agree is refused rather than served.
    """
    document = json.loads(path.read_text(encoding="utf-8"))
    version = document.get("format")
    if version != RECORD_FORMAT:
        raise RecordNotFound(
            f"{path} is written in the on-disk format {version!r}, and this reader knows "
            f"{RECORD_FORMAT!r}"
        )
    product = document["product"]
    return KnowledgeProduct(
        product_id=str(product["product_id"]),
        version=str(product["version"]),
        nature=ResultNature(product["nature"]),
        produced_at=datetime.fromisoformat(product["produced_at"]),
        status=ProductStatus(product["status"]),
        domain_of_validity=str(product["domain_of_validity"]),
        uncertainty=str(product["uncertainty"]),
        lineage=tuple(
            ProvenanceRef(
                kind=ProvenanceKind(ref["kind"]),
                identifier=str(ref["identifier"]),
                label=ref.get("label"),
                revision=ref.get("revision"),
            )
            for ref in product["lineage"]
        ),
        summary=product["summary"],
        input_statuses={
            str(identifier): QualityStatus(status)
            for identifier, status in product["input_statuses"].items()
        },
    )


def list_products(root: Path) -> tuple[str, ...]:
    """The products that are published, in name order."""
    if not root.exists():
        return ()
    return tuple(
        sorted(
            path.name
            for path in root.iterdir()
            if path.is_dir() and any(child.is_dir() for child in path.iterdir())
        )
    )


def list_versions(root: Path, product_id: str) -> tuple[str, ...]:
    """The versions published for a product, oldest first.

    The versions are ordered by the order they were published, not by their
    text: a version is a date most of the time, but it does not have to be.
    """
    directory = _product_directory(root, product_id)
    if not directory.exists():
        return ()
    versions = [
        path.name
        for path in sorted(directory.iterdir())
        if path.is_dir() and (path / RECORD_FILE).exists()
    ]
    return tuple(versions)


def load_record(root: Path, product_id: str, version: str | None = None) -> StoredRecord:
    """Load a published product.

    Without a version, the **last published** one is loaded: the one whose
    directory sorts last, which is the version the publication wrote most
    recently in this repository.
    """
    versions = list_versions(root, product_id)
    if not versions:
        raise RecordNotFound(f"no product is published under {product_id!r}")
    chosen = versions[-1] if version is None else version
    if chosen not in versions:
        raise RecordNotFound(f"{product_id!r} has no published version {chosen!r}")

    directory = _version_directory(root, product_id, chosen)
    record_path = directory / RECORD_FILE
    if not record_path.exists():
        raise RecordNotFound(f"{product_id!r} version {chosen!r} has no record")

    digest = _read_digest(record_path)
    _verify_payload(directory, digest)

    payload = {
        path.name: path
        for path in sorted(directory.iterdir())
        if path.is_file() and path.name != RECORD_FILE
    }
    return StoredRecord(
        product_id=product_id,
        version=chosen,
        record=read_record(record_path),
        directory=directory,
        payload=payload,
        payload_digest=digest,
    )
