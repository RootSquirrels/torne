"""Empreinte canonique d'une structure de données.

Une empreinte doit être **stable** : deux exécutions qui produisent la même
structure produisent la même empreinte, sur n'importe quelle machine et dans
n'importe quel ordre d'insertion. La forme canonique est donc triée, sans
dépendance à l'ordre des clés, et explicite sur le type des nombres.

`bool` est traité avant `int` : en Python, `True` est un `int`, et une
empreinte qui confondrait les deux serait fausse.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import date, datetime
from enum import Enum


def canonical(value: object) -> str:
    """Renvoie la forme canonique textuelle d'une valeur Python.

    La forme est un JSON sans espaces, dont les clés sont triées et dont les
    types sont discriminés (`true` ≠ `1` ≠ `"1"`).
    """
    if value is None:
        return "null"
    if isinstance(value, Mapping):
        items = sorted(value.items(), key=lambda pair: str(pair[0]))
        corps = ",".join(
            f"{json.dumps(str(k), ensure_ascii=False)}:{canonical(v)}" for k, v in items
        )
        return "{" + corps + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(canonical(v) for v in value) + "]"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return canonical(value.value)

    # Les scalaires numériques d'un tableau (numpy) ne sont pas des `int` ni
    # des `float` Python : on les ramène à leur valeur Python avant de continuer.
    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        return canonical(tolist())

    raise TypeError(f"valeur non sérialisable dans une empreinte : {type(value).__name__}")


def fingerprint(value: object) -> str:
    """Renvoie l'empreinte SHA-256 de la forme canonique de `value`."""
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def fingerprint_bytes(payload: bytes) -> str:
    """Renvoie l'empreinte SHA-256 de contenus bruts (preuve brute)."""
    return hashlib.sha256(payload).hexdigest()


__all__ = ["canonical", "fingerprint", "fingerprint_bytes"]
