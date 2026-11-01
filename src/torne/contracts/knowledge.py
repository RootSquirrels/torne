"""Provenance et produit de connaissance.

Ce module est la forme exécutable de `docs/CORE_CONTRACTS.md` §1.3,
§2.5 et §4.4 : il fixe **ce que c'est qu'une référence de provenance** et **ce
qu'est un produit de connaissance**.

Trois règles structurantes :

1. **La nature d'un produit n'est jamais déclarée par l'appelant.** Elle est
   tirée du résultat du modèle : un résultat estimé ne peut pas produire un
   produit présenté comme une observation directe (`docs/ARCHITECTURE.md` §3).
2. **Un produit n'est publiable que si sa lignée est complète.** La lignée est
   ici une **suite de références** (`ProvenanceRef`), pas une chaîne
   d'objets : elle permet de remonter du résultat publié jusqu'aux preuves
   brutes (INV-27, INV-29). Elle cite les observations, les grandeurs dérivées,
   les preuves brutes et les sources.
3. **Un produit ne se réécrit pas** (INV-31). Une correction produit une
   version **nouvelle** ; l'ancienne reste consultable. C'est la version
   portée par le produit qui l'exprime — jamais une mutation.

Le produit porte une incertitude **qualifiée en clair** (une chaîne, jamais un
nombre) : le contrat impose de décrire l'incertitude selon ce qui est
réellement connu, et un scalaire ne dit pas de quoi il s'agit
(`docs/RESEARCH_AND_VALIDATION.md` §6).

Le produit porte aussi le **statut de qualité de ses entrées**
(`input_statuses`) : un produit qui consomme des observations provisoires le
dit, et ne présente pas l'ensemble comme s'il était acquis (§3.7, INV-22).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import date, datetime
from enum import Enum, StrEnum
from types import MappingProxyType

from .model import ResultNature
from .observation import QualityStatus
from .time import to_utc


class ProvenanceKind(StrEnum):
    """Nature d'une référence de provenance. Vocabulaire fermé."""

    SOURCE = "source"
    EVIDENCE = "evidence"
    OBSERVATION = "observation"
    DERIVED_VARIABLE = "derived_variable"
    MODEL = "model"
    PARAMETER = "parameter"
    EVALUATION = "evaluation"
    PRODUCT = "product"


@dataclass(frozen=True, slots=True)
class ProvenanceRef:
    """Une référence de provenance : un type, un identifiant, un libellé.

    `identifier` est l'identifiant stable de l'objet cité (identifiant de
    source, empreinte de preuve brute, identifiant d'observation, empreinte de
    paramètres...). `revision` porte la version de cet objet lorsqu'elle est
    connue : la version d'un modèle, la date d'une évaluation, l'observation
    qu'une révision remplace.

    `label` est un libellé humain : il n'est jamais porteur de sens
    contractuel, et son absence n'est pas un défaut.
    """

    kind: ProvenanceKind
    identifier: str
    label: str | None = None
    revision: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ProvenanceKind):
            raise TypeError("ProvenanceRef.kind doit être une ProvenanceKind")
        if not isinstance(self.identifier, str) or not self.identifier.strip():
            raise ValueError("ProvenanceRef.identifier est obligatoire et non vide")


class ProductStatus(StrEnum):
    """Statut d'un produit de connaissance (§2.5). Vocabulaire fermé.

    `INCONCLUSIVE` n'est pas un échec : un résultat inconclusif est un
    résultat valide, rapporté comme tel, avec sa cause
    (`docs/RESEARCH_AND_VALIDATION.md` §8).
    """

    USABLE = "usable"
    DEGRADED = "degraded"
    WITHDRAWN = "withdrawn"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True, slots=True)
class KnowledgeProduct:
    """Un résultat structuré, versionné, destiné à être réutilisé (§2.5).

    Il porte : un identifiant, une **version**, la nature du résultat, l'instant
    d'établissement, un statut, un domaine de validité, une incertitude
    qualifiée en clair, la lignée complète et un résumé.

    Il porte aussi la **qualification de ses entrées** (`input_statuses`) : le
    statut de qualité de chaque observation et de chaque grandeur dérivée
    qu'il consomme (§3.7). Un produit qui consomme des observations
    provisoires le dit ; il ne présente pas l'ensemble comme s'il était acquis
    (INV-22). La qualification est **obligatoire** pour toute entrée citée :
    un produit qui ne dit pas le statut de ce qu'il consomme ne peut pas être
    construit.

    Il ne garantit pas que le produit soit vrai, ni qu'il reste vrai, ni qu'il
    soit réutilisable hors de son domaine de validité. Il n'est pas un
    registre : il ne catalogue pas l'existant (`docs/ARCHITECTURE.md` §4).
    """

    product_id: str
    version: str
    nature: ResultNature
    produced_at: datetime
    status: ProductStatus
    domain_of_validity: str
    uncertainty: str
    lineage: tuple[ProvenanceRef, ...]
    summary: Mapping[str, object]
    input_statuses: Mapping[str, QualityStatus] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.product_id, str) or not self.product_id.strip():
            raise ValueError("KnowledgeProduct.product_id est obligatoire et non vide")
        if not isinstance(self.version, str) or not self.version.strip():
            raise ValueError("KnowledgeProduct.version est obligatoire et non vide")
        if not isinstance(self.nature, ResultNature):
            raise TypeError("KnowledgeProduct.nature doit être une ResultNature")
        if not isinstance(self.status, ProductStatus):
            raise TypeError("KnowledgeProduct.status doit être un ProductStatus")
        if not isinstance(self.domain_of_validity, str) or not self.domain_of_validity.strip():
            raise ValueError("KnowledgeProduct.domain_of_validity est obligatoire et non vide")
        if not isinstance(self.uncertainty, str) or not self.uncertainty.strip():
            raise ValueError("KnowledgeProduct.uncertainty est obligatoire et non vide")
        if not isinstance(self.lineage, (tuple, list)):
            raise TypeError("KnowledgeProduct.lineage doit être une suite de ProvenanceRef")
        if not self.lineage:
            raise ValueError(
                "un produit n'est publiable que si sa lignée est complète : la lignée est vide"
            )

        object.__setattr__(
            self,
            "produced_at",
            to_utc(self.produced_at, name="KnowledgeProduct.produced_at"),
        )
        object.__setattr__(self, "lineage", tuple(self.lineage))
        object.__setattr__(self, "summary", MappingProxyType(dict(self.summary)))
        object.__setattr__(self, "input_statuses", MappingProxyType(dict(self.input_statuses)))
        self._verifier_qualification_des_entrees()

    def _verifier_qualification_des_entrees(self) -> None:
        """Vérifie que toute entrée citée porte son statut de qualité (§3.7).

        C'est la forme vérifiable d'INV-22 : le produit qui consomme des
        observations provisoires et approuvées les **distingue**, et il ne
        peut pas être construit sans les distinguer.
        """
        for identifiant, statut in self.input_statuses.items():
            if not isinstance(statut, QualityStatus):
                raise TypeError(
                    "KnowledgeProduct.input_statuses doit porter des QualityStatus, "
                    f"« {identifiant} » porte « {type(statut).__name__} »"
                )
        citees: dict[str, ProvenanceKind] = {}
        for ref in self.lineage:
            if ref.kind not in (ProvenanceKind.OBSERVATION, ProvenanceKind.DERIVED_VARIABLE):
                continue
            if ref.identifier in citees:
                raise ValueError(
                    f"« {ref.identifier} » est cité comme {citees[ref.identifier].value} "
                    f"et comme {ref.kind.value} : deux entrées distinctes ne peuvent pas "
                    "porter le même identifiant"
                )
            citees[ref.identifier] = ref.kind
        for identifiant, kind in citees.items():
            if identifiant not in self.input_statuses:
                raise ValueError(
                    f"l'entrée citée « {identifiant} » ({kind.value}) ne porte pas son "
                    "statut de qualité : un produit dit ce qu'il consomme (§3.7)"
                )
        for identifiant in self.input_statuses:
            if identifiant not in citees:
                raise ValueError(f"le statut « {identifiant} » ne correspond à aucune entrée citée")

    @property
    def provisional_inputs(self) -> tuple[str, ...]:
        """Identifiants des entrées provisoires consommées par le produit."""
        return tuple(
            sorted(
                identifiant
                for identifiant, statut in self.input_statuses.items()
                if statut is QualityStatus.PROVISIONAL
            )
        )

    @property
    def unknown_status_inputs(self) -> tuple[str, ...]:
        """Identifiants des entrées dont le statut de qualité est inconnu."""
        return tuple(
            sorted(
                identifiant
                for identifiant, statut in self.input_statuses.items()
                if statut is QualityStatus.UNKNOWN
            )
        )

    @property
    def approved_inputs(self) -> tuple[str, ...]:
        """Identifiants des entrées approuvées consommées par le produit."""
        return tuple(
            sorted(
                identifiant
                for identifiant, statut in self.input_statuses.items()
                if statut is QualityStatus.APPROVED
            )
        )

    @property
    def has_provisional_inputs(self) -> bool:
        """Le produit consomme-t-il au moins une information provisoire ?"""
        return bool(self.provisional_inputs)

    def as_dict(self) -> dict[str, object]:
        """Vue sérialisable du produit : dictionnaires ordinaires, aucun proxy.

        Le produit est figé et ses mappings sont des vues en lecture seule :
        c'est cette vue qu'un enregistreur écrit. Le résumé est converti
        récursivement — un `MappingProxyType` ou un rapport d'évaluation
        imbriqué ne doit jamais fuir dans la structure produite.
        """
        return {
            "product_id": self.product_id,
            "version": self.version,
            "nature": self.nature.value,
            "produced_at": self.produced_at.isoformat(),
            "status": self.status.value,
            "domain_of_validity": self.domain_of_validity,
            "uncertainty": self.uncertainty,
            "lineage": [ref_vers_dict(ref) for ref in self.lineage],
            "input_statuses": {
                identifiant: statut.value
                for identifiant, statut in sorted(self.input_statuses.items())
            },
            "provisional_inputs": list(self.provisional_inputs),
            "summary": to_serialisable(self.summary),
        }


def ref_vers_dict(ref: ProvenanceRef) -> dict[str, object]:
    """Vue sérialisable d'une référence de provenance."""
    return {
        "kind": ref.kind.value,
        "identifier": ref.identifier,
        "label": ref.label,
        "revision": ref.revision,
    }


def to_serialisable(valeur: object) -> object:
    """Convertit une valeur en structure sérialisable (JSON).

    La conversion est récursive et **totale** pour les types que TORNE
    manipule : mappings (y compris les vues en lecture seule), suites, ensembles,
    dataclasses, énumérations, dates et instants, et scalaires numériques
    (numpy compris). Un type inconnu est signalé, jamais transformé en silence
    dans une chaîne qui dirait autre chose que la donnée.
    """
    if valeur is None or isinstance(valeur, (str, bool, int, float)):
        return valeur
    if isinstance(valeur, Enum):
        return valeur.value
    if isinstance(valeur, (datetime, date)):
        return valeur.isoformat()
    if is_dataclass(valeur) and not isinstance(valeur, type):
        return {
            champ.name: to_serialisable(getattr(valeur, champ.name)) for champ in fields(valeur)
        }
    if isinstance(valeur, Mapping):
        return {str(cle): to_serialisable(item) for cle, item in valeur.items()}
    if isinstance(valeur, (set, frozenset)):
        return sorted((to_serialisable(item) for item in valeur), key=repr)
    if isinstance(valeur, (list, tuple)):
        return [to_serialisable(item) for item in valeur]

    tolist = getattr(valeur, "tolist", None)
    if callable(tolist):
        return to_serialisable(tolist())

    raise TypeError(f"valeur non sérialisable : {type(valeur).__name__}")


__all__ = [
    "KnowledgeProduct",
    "ProductStatus",
    "ProvenanceKind",
    "ProvenanceRef",
    "ref_vers_dict",
    "to_serialisable",
]
