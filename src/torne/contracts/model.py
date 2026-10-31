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

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol

from .fingerprint import fingerprint

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
            "outputs",
            MappingProxyType({name: tuple(values) for name, values in self.outputs.items()}),
        )
        object.__setattr__(
            self,
            "intervals",
            MappingProxyType({name: tuple(pairs) for name, pairs in self.intervals.items()}),
        )
        object.__setattr__(self, "diagnostics", MappingProxyType(dict(self.diagnostics)))
        if self.output_natures:
            if set(self.output_natures) != set(self.outputs):
                raise ValueError(
                    "les natures déclarées ne correspondent pas aux sorties : "
                    f"sorties {sorted(self.outputs)}, natures {sorted(self.output_natures)}"
                )
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
