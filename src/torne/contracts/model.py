"""Contrat de la frontière « Modèles » (`docs/ARCHITECTURE.md` §3).

Un modèle possède une question précise, un domaine, des entrées, une sortie,
des hypothèses et des limites déclarées. Ce module fixe la **forme** de ces
éléments ; il ne fixe aucune méthode, aucun moteur, aucune interface de
service, aucun registre.

Un résultat porte toujours la mention de ce qu'il est : `ESTIMATED`,
`RECONSTRUCTED`, `PREDICTED`, `SIMULATED` ou `DERIVED`. Un modèle ne transforme
jamais une estimation en observation, ni une simulation en observation : une
observation de source a son propre objet, et son propre statut de qualité.

« Pas de configuration globale cachée » : les paramètres, les entrées, la
graine et l'empreinte de la configuration sont des **arguments explicites**.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol

from .fingerprint import fingerprint
from .time import to_utc

ParameterValue = float | int | str | bool | None


class ResultNature(StrEnum):
    """Nature d'une grandeur dérivée (contrat §2.4).

    Une **observation de source** n'a pas de nature ici : c'est l'objet
    `Observation` lui-même, qui porte son propre statut de qualité (§3.7).
    Une grandeur dérivée, elle, est l'une des cinq natures ci-dessous — et
    elles ne se confondent pas :

    - `ESTIMATED` — une estimation statistique ;
    - `RECONSTRUCTED` — un état reconstruit à partir d'observations ;
    - `PREDICTED` — une prévision ;
    - `SIMULATED` — une simulation ;
    - `DERIVED` — une autre grandeur calculée.

    Une même exécution peut produire des grandeurs de natures différentes : un
    filtre d'état restitue un état reconstruit **et** émet des prévisions. C'est
    pourquoi la nature se déclare **par sortie** (`ModelResult.output_natures`),
    et pas seulement au niveau du résultat.
    """

    ESTIMATED = "estimated"
    RECONSTRUCTED = "reconstructed"
    PREDICTED = "predicted"
    SIMULATED = "simulated"
    DERIVED = "derived"


@dataclass(frozen=True, slots=True)
class ModelSpec:
    """Identité, question et portée d'un modèle. La version est obligatoire."""

    model_id: str
    version: str
    question: str
    method: str
    natures: tuple[ResultNature, ...]
    assumptions: tuple[str, ...] = ()
    domain_of_validity: str = ""

    def __post_init__(self) -> None:
        for name in ("model_id", "version", "question", "method"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"ModelSpec.{name} est obligatoire et non vide")
        object.__setattr__(self, "natures", tuple(self.natures))
        object.__setattr__(self, "assumptions", tuple(self.assumptions))
        if not self.natures:
            raise ValueError("ModelSpec.natures doit déclarer au moins une nature de résultat")


@dataclass(frozen=True, slots=True)
class ModelParameters:
    """Paramètres explicites d'une exécution. Aucun paramètre caché."""

    values: Mapping[str, ParameterValue]

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))

    def as_dict(self) -> dict[str, ParameterValue]:
        return dict(self.values)

    def fingerprint(self) -> str:
        """Empreinte stable des paramètres (clé de rejouabilité)."""
        return fingerprint(self.as_dict())


@dataclass(frozen=True, slots=True)
class ModelInputs:
    """Entrées numériques explicites d'une exécution.

    Une série ne contient que des valeurs définies : une absence se traite au
    niveau de l'observation, qualifiée, et jamais par interpolation ni par
    substitution d'un zéro.
    """

    series: Mapping[str, tuple[float, ...]]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "series",
            MappingProxyType({name: tuple(values) for name, values in self.series.items()}),
        )

    def as_dict(self) -> dict[str, tuple[float, ...]]:
        return {name: tuple(values) for name, values in self.series.items()}

    def fingerprint(self) -> str:
        """Empreinte stable des entrées (clé de rejouabilité)."""
        return fingerprint(self.as_dict())


@dataclass(frozen=True, slots=True)
class ModelResult:
    """Résultat typé d'une exécution de modèle.

    `output_natures` déclare la nature de **chaque sortie**. Une sortie non
    déclarée prend la nature du résultat — ce qui convient quand toutes les
    sorties sont de même nature, et ne convient plus dès qu'elles diffèrent :
    dans ce cas, les natures doivent être déclarées une à une. C'est ce qui
    empêche d'exposer une prévision sous la nature d'un état reconstruit.

    Les invariants appliqués à la construction :

    - `produced_at` est un instant **avec fuseau**, normalisé en UTC
      (INV-15, INV-16) ;
    - chaque intervalle porte le nom d'une **sortie** du résultat, et compte
      autant de couples que la sortie a de valeurs ;
    - les bornes d'un intervalle sont **finies** et **ordonnées** (bas ≤ haut) ;
    - chaque nature déclarée par sortie est une nature **déclarée par le
      modèle** (`ModelSpec.natures`), et les natures déclarées portent
      exactement les noms des sorties.
    """

    spec: ModelSpec
    nature: ResultNature
    parameters: ModelParameters
    produced_at: datetime
    outputs: Mapping[str, tuple[float, ...]] = field(default_factory=dict)
    intervals: Mapping[str, tuple[tuple[float, float], ...]] = field(default_factory=dict)
    diagnostics: Mapping[str, float | int | str | bool] = field(default_factory=dict)
    output_natures: Mapping[str, ResultNature] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "produced_at",
            to_utc(self.produced_at, name="ModelResult.produced_at"),
        )
        object.__setattr__(
            self,
            "outputs",
            MappingProxyType({name: tuple(values) for name, values in self.outputs.items()}),
        )
        object.__setattr__(
            self,
            "intervals",
            MappingProxyType({name: tuple(pairs) for name, pairs in self.intervals.items()}),
        )
        object.__setattr__(self, "diagnostics", MappingProxyType(dict(self.diagnostics)))
        self._verifier_intervalles()
        if self.output_natures:
            if set(self.output_natures) != set(self.outputs):
                raise ValueError(
                    "les natures déclarées ne correspondent pas aux sorties : "
                    f"sorties {sorted(self.outputs)}, natures {sorted(self.output_natures)}"
                )
            self._verifier_natures_de_sortie()
            object.__setattr__(
                self,
                "output_natures",
                MappingProxyType(dict(self.output_natures)),
            )
        else:
            object.__setattr__(
                self,
                "output_natures",
                MappingProxyType(dict.fromkeys(self.outputs, self.nature)),
            )
        if self.nature not in self.spec.natures:
            raise ValueError(
                f"nature de résultat « {self.nature} » absente des natures déclarées "
                f"par le modèle {self.spec.model_id}"
            )

    def _verifier_intervalles(self) -> None:
        """Vérifie que chaque intervalle décrit une sortie existante.

        Un intervalle qui ne porte aucun nom de sortie ne décrit rien ; un
        intervalle dont le nombre de couples ne correspond pas à la sortie
        qu'il accompagne ne la décrit pas non plus. Les bornes, enfin, sont
        finies et ordonnées : un intervalle inversé n'est pas un intervalle.
        """
        for nom, paires in self.intervals.items():
            if nom not in self.outputs:
                raise ValueError(
                    f"intervalle « {nom} » : aucune sortie de ce nom dans le résultat "
                    f"(sorties : {sorted(self.outputs)})"
                )
            longueur = len(self.outputs[nom])
            if len(paires) != longueur:
                raise ValueError(
                    f"intervalle « {nom} » : {len(paires)} intervalle(s) pour une sortie "
                    f"de {longueur} valeur(s)"
                )
            for indice, paire in enumerate(paires):
                if len(paire) != 2:
                    raise ValueError(
                        f"intervalle « {nom} » : l'intervalle {indice} ne porte pas deux bornes"
                    )
                bas, haut = paire
                try:
                    finies = math.isfinite(bas) and math.isfinite(haut)
                except TypeError as exc:
                    raise ValueError(
                        f"intervalle « {nom} » : les bornes de l'intervalle {indice} "
                        "ne sont pas des nombres"
                    ) from exc
                if not finies:
                    raise ValueError(
                        f"intervalle « {nom} » : les bornes de l'intervalle {indice} "
                        "ne sont pas finies"
                    )
                if bas > haut:
                    raise ValueError(
                        f"intervalle « {nom} » : l'intervalle {indice} n'est pas ordonné "
                        f"({bas} > {haut})"
                    )

    def _verifier_natures_de_sortie(self) -> None:
        """Vérifie que chaque nature déclarée par sortie est une nature connue.

        Une nature que le modèle ne déclare pas n'est pas une nature de sortie :
        elle est refusée, et non ajoutée au vocabulaire.
        """
        for nom, nature in self.output_natures.items():
            if not isinstance(nature, ResultNature):
                raise TypeError(
                    f"ModelResult.output_natures : « {nom} » porte "
                    f"« {type(nature).__name__} », pas une ResultNature"
                )
            if nature not in self.spec.natures:
                raise ValueError(
                    f"nature de sortie « {nom} » : « {nature.value} » n'est pas déclarée "
                    f"par le modèle {self.spec.model_id} (natures déclarées : "
                    f"{', '.join(declaree.value for declaree in self.spec.natures)})"
                )

    def as_dict(self) -> dict[str, object]:
        """Vue sérialisable du résultat : sorties, intervalles et natures.

        La nature y est portée **par sortie** : un résultat qui restitue un
        état reconstruit et qui émet une prévision le dit sortie par sortie, et
        jamais sous une nature unique qui masquerait l'une des deux.
        """
        return {
            "nature": self.nature.value,
            "outputs": {nom: list(valeurs) for nom, valeurs in self.outputs.items()},
            "intervals": {
                nom: [list(paire) for paire in paires] for nom, paires in self.intervals.items()
            },
            "output_natures": {
                nom: nature.value for nom, nature in sorted(self.output_natures.items())
            },
        }

    def output(self, name: str) -> tuple[float, ...]:
        """Renvoie une sortie nommée. Lève `KeyError` si elle n'existe pas."""
        return self.outputs[name]

    def output_nature(self, name: str) -> ResultNature:
        """Renvoie la nature d'une sortie nommée."""
        return self.output_natures[name]

    def interval(self, name: str) -> tuple[tuple[float, float], ...]:
        """Renvoie les intervalles d'une sortie nommée."""
        return self.intervals[name]


@dataclass(frozen=True, slots=True)
class ExecutionConfig:
    """Configuration reproductible d'une exécution, horodatage exclu.

    Elle ne contient que ce qui détermine le résultat : le modèle et sa
    version, la graine, les paramètres, l'empreinte des entrées et les
    versions de bibliothèques utilisées. Les instants de début et de fin sont
    des métadonnées, pas de la configuration : les tenir ici rendrait
    l'empreinte instable d'une exécution à l'autre.
    """

    model_id: str
    model_version: str
    seed: int | None
    parameters: ModelParameters
    inputs_fingerprint: str
    library_versions: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "library_versions", MappingProxyType(dict(self.library_versions)))

    def fingerprint(self) -> str:
        """Empreinte stable de la configuration : deux exécutions identiques
        ont la même empreinte."""
        return fingerprint(
            {
                "model_id": self.model_id,
                "model_version": self.model_version,
                "seed": self.seed,
                "parameters": self.parameters.as_dict(),
                "inputs_fingerprint": self.inputs_fingerprint,
                "library_versions": dict(self.library_versions),
            }
        )


class Model(Protocol):
    """Ce qu'un modèle est : une identité déclarée et une exécution paramétrée.

    Une fonction Python ordinaire satisfait ce protocole dès lors qu'elle
    expose `spec` et respecte la signature de `run`. Aucun framework n'est
    requis, et aucun n'est interdit : la forme est celle d'une fonction.
    """

    @property
    def spec(self) -> ModelSpec: ...

    def run(
        self,
        inputs: ModelInputs,
        params: ModelParameters,
        *,
        seed: int | None = None,
    ) -> ModelResult: ...


__all__ = [
    "ExecutionConfig",
    "Model",
    "ModelInputs",
    "ModelParameters",
    "ModelResult",
    "ModelSpec",
    "ParameterValue",
    "ResultNature",
]
