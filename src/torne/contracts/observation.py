"""Les trois objets de la preuve : Source, Raw Evidence, Observation.

Ce module est la forme exécutable de `docs/CONTRATS_FONDAMENTAUX.md` §2.1 à
§2.3. Les trois objets répondent à trois questions distinctes, et aucun ne
répond à la place d'un autre :

| Objet | Question à laquelle il répond seul |
|---|---|
| `Source` | d'où vient l'information, et sous quelles conditions était-elle disponible ? |
| `RawEvidence` | quel contenu brut a effectivement été récupéré, et est-ce encore là, intact ? |
| `Observation` | qu'a mesuré ou rapporté la source, à cet instant et dans ces termes ? |

Trois règles structurantes, toutes vérifiables :

1. **La temporalité n'est pas réinventée ici.** Une observation porte un
   `TemporalStamp` de `torne.contracts.time` : les trois dimensions, la règle
   `usable_at = max(KNOWN_AT, INGESTED_AT)` et les trois états de publication
   sont ceux du contrat, pas une seconde notion du temps.
2. **La validité n'est pas réinventée non plus.** `PointValidity` et
   `MissingReason` viennent de `torne.contracts.validity`. L'observation ne
   décide pas de la validité d'un point par elle-même : elle porte l'état, et
   l'absence est **qualifiée** (INV-18).
3. **Les invariants sont appliqués à la construction.** Une observation
   impossible est refusée à la construction, pas signalée plus tard : c'est ce
   qui rend la règle testable sans état global ni journal.

> **Absent ≠ zéro** (INV-19). Une observation sans valeur ne porte pas de
> zéro en guise d'absence : elle porte `value = None`, `validity = MISSING` et
> une `missing_reason` issue de la liste contrôlée. Une valeur `0.0` est une
> mesure ; elle n'est jamais une absence.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from .time import TemporalStamp, to_utc
from .validity import MissingReason, PointValidity


def _exiger_texte(valeur: str, nom: str) -> str:
    """Refuse un champ d'identité vide ou non textuel.

    Une identité vide n'identifie rien : la rattacher à une preuve ou à une
    source serait une illusion de traçabilité. Le refus est à l'entrée.
    """
    if not isinstance(valeur, str) or not valeur.strip():
        raise ValueError(f"{nom} est obligatoire et non vide")
    return valeur


@dataclass(frozen=True, slots=True)
class Source:
    """Identité et conditions de disponibilité d'une information (§2.1).

    La source est le seul garant de l'origine d'une information : institution
    productrice, jeu de données, point d'accès, conditions d'usage. Ses
    propriétés — politique de révision, unités, fuseau, statut de qualité —
    sont des propriétés **de la source**, pas d'une observation isolée.

    Elle ne garantit pas que la source publiera ce qu'elle annonce, ni que ses
    données sont complètes ou exactes : elle garantit seulement que l'origine
    est nommée et que ses conditions d'usage sont consignées.
    """

    source_id: str
    producer: str
    dataset: str
    access_point: str | None = None
    license: str | None = None
    revision_policy: str | None = None
    unit: str | None = None
    timezone: str | None = None
    quality_status: str | None = None

    def __post_init__(self) -> None:
        _exiger_texte(self.source_id, "Source.source_id")
        _exiger_texte(self.producer, "Source.producer")
        _exiger_texte(self.dataset, "Source.dataset")


@dataclass(frozen=True, slots=True)
class RawEvidence:
    """Contenu brut récupéré, daté, jamais réécrit (§2.2).

    `evidence_id` est l'empreinte du contenu brut : c'est ce qui permet de
    remonter d'une observation à la preuve qui l'a produite (INV-25) et de
    vérifier que le contenu n'a pas bougé depuis l'acquisition.

    `acquired_at` est un instant **avec fuseau** : il est normalisé en UTC à
    la construction (INV-15), jamais supposé. La date d'acquisition est
    conservée telle qu'elle a eu lieu, y compris pour un réimport d'archive :
    elle porte la marque de son origine (§3.10, INV-14).

    Le brut ne porte pas d'interprétation : il se laisse re-parser (§2.2).
    """

    evidence_id: str
    source_id: str
    acquired_at: datetime
    media_type: str | None = None
    content_sha256: str | None = None
    key: str | None = None

    def __post_init__(self) -> None:
        _exiger_texte(self.evidence_id, "RawEvidence.evidence_id")
        _exiger_texte(self.source_id, "RawEvidence.source_id")
        object.__setattr__(
            self,
            "acquired_at",
            to_utc(self.acquired_at, name="RawEvidence.acquired_at"),
        )


@dataclass(frozen=True, slots=True)
class Observation:
    """Ce que la source a mesuré ou rapporté, à cet instant et dans ses termes (§2.3).

    L'observation est le seul garant du **contenu sémantique** : sa valeur,
    son unité, son référentiel spatial, son état de validité, sa temporalité,
    et son rattachement à une preuve brute identifiable.

    Les invariants appliqués à la construction :

    - `validity == VALID` implique une valeur présente et aucune raison
      d'absence (INV-19) ;
    - `validity == MISSING` implique une valeur absente **et** une
      `missing_reason` issue de la liste contrôlée (INV-18, INV-19) ;
    - une valeur absente et une valeur présente ne peuvent pas se porter la
      raison d'absence l'une l'autre : la présence d'une raison signifie
      l'absence de la valeur, et réciproquement ;
    - l'unité et le référentiel spatial sont non vides (INV-23) ;
    - `evidence_id` est non vide : une observation sans preuve brute
      identifiable n'est pas traçable (INV-25) ;
    - `revision_of` est différent de `observation_id` : une observation n'est
      pas la révision d'elle-même.

    L'absence n'est jamais remplacée par zéro, jamais par une estimation et
    jamais par une interpolation : elle est qualifiée.
    """

    observation_id: str
    source_id: str
    quantity: str
    unit: str
    temporal: TemporalStamp
    evidence_id: str
    value: float | None = None
    validity: PointValidity = PointValidity.VALID
    missing_reason: MissingReason | None = None
    spatial_ref: str = "non_spatial"
    key: str | None = None
    revision_of: str | None = None

    def __post_init__(self) -> None:
        _exiger_texte(self.observation_id, "Observation.observation_id")
        _exiger_texte(self.source_id, "Observation.source_id")
        _exiger_texte(self.quantity, "Observation.quantity")
        _exiger_texte(self.unit, "Observation.unit")
        _exiger_texte(self.spatial_ref, "Observation.spatial_ref")
        _exiger_texte(self.evidence_id, "Observation.evidence_id")

        if not isinstance(self.temporal, TemporalStamp):
            raise TypeError("Observation.temporal doit être une TemporalStamp")
        if not isinstance(self.validity, PointValidity):
            raise TypeError("Observation.validity doit être une PointValidity")
        if self.missing_reason is not None and not isinstance(self.missing_reason, MissingReason):
            raise TypeError("Observation.missing_reason doit être une MissingReason")

        if self.value is not None and not isinstance(self.value, (int, float)):
            raise TypeError("Observation.value doit être un nombre ou None")
        if isinstance(self.value, bool):
            raise TypeError("Observation.value doit être un nombre, pas un booléen")
        if self.value is not None and not math.isfinite(float(self.value)):
            raise ValueError(
                "une valeur non finie n'est pas une mesure : elle ne peut être ni "
                "moyennée ni propagée"
            )

        if self.value is None and self.missing_reason is None:
            raise ValueError("une valeur absente porte une raison d'absence (INV-18)")
        if self.value is not None and self.missing_reason is not None:
            raise ValueError("une valeur présente ne porte pas de raison d'absence (INV-18)")
        if self.validity is PointValidity.VALID and self.value is None:
            raise ValueError("une observation valide porte une valeur (INV-19)")
        if self.validity is PointValidity.MISSING and self.value is not None:
            raise ValueError("une observation absente ne porte pas de valeur (INV-19)")

        if self.revision_of is not None:
            _exiger_texte(self.revision_of, "Observation.revision_of")
            if self.revision_of == self.observation_id:
                raise ValueError("une observation ne peut pas être la révision d'elle-même")


__all__ = ["Observation", "RawEvidence", "Source"]
