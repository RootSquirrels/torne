"""Vocabulaire de validité : absence, invalidité, hors-domaine.

Deux listes distinctes, à ne jamais confondre :

- `MissingReason` décrit **ce qui manque** dans la source (contrat §3.8). Elle
  ne décrit jamais un échec de récupération : « la source ne publie pas » et
  « TORNE n'a pas été chercher » sont deux faits différents (INV-20).
- `PointValidity` décrit **l'état d'un point** au moment de son utilisation : une
  absence qualifiée n'est ni une valeur invalide, ni une valeur hors domaine.

`INV-19` : une absence et un zéro sont distinguables, et l'une ne se convertit
jamais en l'autre.
"""

from __future__ import annotations

from enum import StrEnum


class MissingReason(StrEnum):
    """Raison de l'absence d'une valeur (contrat §3.8). Liste contrôlée.

    Les valeurs propres à une source précise sont différées au gate P1 : une
    source inconnue ne se devine pas.
    """

    NOT_MEASURED = "not_measured"
    NOT_YET_PUBLISHED = "not_yet_published"
    NOT_ATTEMPTED = "not_attempted"


class PointValidity(StrEnum):
    """État d'un point au moment de son utilisation."""

    VALID = "valid"
    MISSING = "missing"
    INVALID = "invalid"
    OUT_OF_DOMAIN = "out_of_domain"


def validity_of(value: float | None, missing_reason: MissingReason | None) -> PointValidity:
    """Déduit la validité d'un point à partir de sa valeur et de sa raison.

    Une valeur présente est valide. Une valeur absente porte une raison
    d'absence (INV-18) et n'est jamais convertie en zéro.
    """
    if value is not None:
        return PointValidity.VALID
    if missing_reason is None:
        raise ValueError("une valeur absente porte une raison d'absence (INV-18)")
    return PointValidity.MISSING


__all__ = ["MissingReason", "PointValidity", "validity_of"]
