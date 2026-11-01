"""La grandeur dérivée — le cinquième objet du contrat (`docs/CORE_CONTRACTS.md` §2.4).

Ce module est la forme exécutable de §2.4. La grandeur dérivée est le seul
garant de la **règle de calcul** : une valeur calculée ou estimée à partir
d'une ou plusieurs observations, dont la méthode, les paramètres, les entrées
et l'incertitude sont connus.

| Objet | Question à laquelle il répond seul |
|---|---|
| `DerivedVariable` | que vaut la grandeur calculée à partir de ces observations ? |

Quatre règles structurantes, toutes vérifiables :

1. **La temporalité est propre, et elle est dérivée, pas déclarée.** Le
   `KNOWN_AT` d'une grandeur dérivée est l'instant **du calcul** — jamais celui
   de la source (INV-17). Il n'est donc pas un champ que l'appelant peut
   remplir : il est calculé depuis `computed_at`. Une variable calculée le
   21 octobre à partir d'observations publiées le 18 octobre n'est connue que
   du 21 octobre.
2. **La lignée est citée, pas devinée.** `inputs` cite les observations et les
   grandeurs dérivées consommées ; la fermeture transitive
   (`transitive_observations`) descend jusqu'aux preuves brutes, et
   `torne.knowledge.record.verify_lineage` la vérifie (INV-29).
3. **L'incertitude est qualifiée selon ce qui est réellement connu.**
   `Uncertainty` porte une forme — intervalle, distribution, scénarios, borne,
   sensibilité ou conclusion qualitative — et la forme n'est acceptée que si
   sa charge utile correspond. Une distribution sophistiquée n'est pas requise
   si les données ne la justifient pas
   (`docs/RESEARCH_AND_VALIDATION.md` §6).
4. **Elle ne se présente jamais comme une observation de source.** Le type est
   distinct d'`Observation`, il ne porte ni identifiant d'observation, ni
   identifiant de source, ni identifiant de preuve brute, et sa nature est
   une `ResultNature` — un vocabulaire dont la valeur « observée » a
   délibérément disparu : une observation de source a son propre objet et son
   propre statut de qualité.

> **Le point de fuite principal** (§2.4). Une variable calculée le 21 octobre à
> partir d'observations publiées le 18 octobre n'est connue que du 21 octobre.
> Lui attribuer le `KNOWN_AT` de ses entrées fait passer une reconstruction
> postérieure pour une reconstruction disponible en temps réel.

Le module ne crée ni registre, ni service, ni moteur, ni format de stockage :
ce sont des dataclasses, et une fonction de dérivation depuis un résultat de
modèle.

> **Ce n'est pas l'incertitude d'une métrique d'évaluation.** `Uncertainty`
> qualifie l'incertitude d'une **grandeur dérivée** — ce que l'on sait de sa
> valeur, et ce que l'on n'en sait pas. L'intervalle numérique d'une métrique
> d'évaluation (`torne.evaluation.uncertainty`) est une autre chose, dans une
> autre couche : il mesure une erreur, il ne qualifie pas une grandeur.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .model import ModelParameters, ModelResult, ResultNature
from .observation import Observation, QualityStatus
from .time import PublicationState, TemporalStamp, to_utc
from .validity import MissingReason


class UncertaintyForm(StrEnum):
    """Forme de la qualification d'incertitude (contrat §2.4).

    La forme est **adaptée à ce qui est réellement connu**
    (`docs/RESEARCH_AND_VALIDATION.md` §6). Le vocabulaire est fermé, et
    chaque forme a une exigence propre : une forme qui ne correspond pas à sa
    charge utile est refusée à la construction.

    - `INTERVAL` — un intervalle est connu ;
    - `DISTRIBUTION` — une distribution est connue ;
    - `SCENARIOS` — des scénarios sont énoncés ;
    - `BOUND` — une borne est connue ;
    - `SENSITIVITY` — une analyse de sensibilité est connue ;
    - `QUALITATIVE` — rien de plus n'est connu qu'une conclusion en clair.
    """

    INTERVAL = "interval"
    DISTRIBUTION = "distribution"
    SCENARIOS = "scenarios"
    BOUND = "bound"
    SENSITIVITY = "sensitivity"
    QUALITATIVE = "qualitative"


def _exiger_texte(valeur: str, nom: str) -> str:
    """Refuse un champ d'identité vide ou non textuel."""
    if not isinstance(valeur, str) or not valeur.strip():
        raise ValueError(f"{nom} est obligatoire et non vide")
    return valeur


def _exiger_nombre(valeur: float, nom: str) -> float:
    """Refuse un nombre non fini : il ne peut être ni moyenné ni propagé."""
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)):
        raise TypeError(f"{nom} doit être un nombre")
    if not math.isfinite(float(valeur)):
        raise ValueError(f"{nom} doit être un nombre fini")
    return float(valeur)


@dataclass(frozen=True, slots=True)
class Uncertainty:
    """Qualification d'incertitude d'une grandeur dérivée (contrat §2.4).

    `statement` est toujours la qualification **en clair** : ce que l'on sait,
    et ce que l'on ne sait pas. Les champs structurés ne sont présents que si
    la forme les exige — une forme « interval » sans bornes, ou une forme
    « qualitative » qui porterait une distribution, sont refusées.

    | Forme | Charge utile requise |
    |---|---|
    | `INTERVAL` | `interval` — un couple `(bas, haut)`, ordonné |
    | `DISTRIBUTION` | `distribution` — la distribution, décrite |
    | `SCENARIOS` | `scenarios` — au moins un scénario |
    | `BOUND` | `bound` — la borne |
    | `SENSITIVITY` | `sensitivity` — ce à quoi la grandeur est sensible |
    | `QUALITATIVE` | aucune : la conclusion en clair suffit |
    """

    form: UncertaintyForm
    statement: str
    interval: tuple[float, float] | None = None
    distribution: str | None = None
    scenarios: tuple[str, ...] = ()
    bound: float | None = None
    sensitivity: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.form, UncertaintyForm):
            raise TypeError("Uncertainty.form doit être une UncertaintyForm")
        _exiger_texte(self.statement, "Uncertainty.statement")
        object.__setattr__(self, "scenarios", tuple(self.scenarios))

        if self.interval is not None:
            bas, haut = self.interval
            bas = _exiger_nombre(bas, "Uncertainty.interval")
            haut = _exiger_nombre(haut, "Uncertainty.interval")
            if bas > haut:
                raise ValueError("un intervalle d'incertitude est ordonné (bas ≤ haut)")
            object.__setattr__(self, "interval", (bas, haut))
        if self.bound is not None:
            object.__setattr__(self, "bound", _exiger_nombre(self.bound, "Uncertainty.bound"))
        if self.distribution is not None:
            _exiger_texte(self.distribution, "Uncertainty.distribution")
        if self.sensitivity is not None:
            _exiger_texte(self.sensitivity, "Uncertainty.sensitivity")
        for scenario in self.scenarios:
            _exiger_texte(scenario, "Uncertainty.scenarios")

        presentes = {
            "interval": self.interval is not None,
            "distribution": self.distribution is not None,
            "scenarios": bool(self.scenarios),
            "bound": self.bound is not None,
            "sensitivity": self.sensitivity is not None,
        }
        requises = {
            UncertaintyForm.INTERVAL: {"interval"},
            UncertaintyForm.DISTRIBUTION: {"distribution"},
            UncertaintyForm.SCENARIOS: {"scenarios"},
            UncertaintyForm.BOUND: {"bound"},
            UncertaintyForm.SENSITIVITY: {"sensitivity"},
            UncertaintyForm.QUALITATIVE: set(),
        }[self.form]
        charge = {nom for nom, presente in presentes.items() if presente}
        if charge != requises:
            raise ValueError(
                f"forme d'incertitude « {self.form.value} » : charge utile "
                f"{sorted(charge)}, attendue {sorted(requises)}"
            )

    @classmethod
    def from_interval(cls, statement: str, bounds: tuple[float, float]) -> Uncertainty:
        """Incertitude exprimée par un intervalle."""
        return cls(form=UncertaintyForm.INTERVAL, statement=statement, interval=bounds)

    @classmethod
    def from_distribution(cls, statement: str, distribution: str) -> Uncertainty:
        """Incertitude exprimée par une distribution."""
        return cls(
            form=UncertaintyForm.DISTRIBUTION, statement=statement, distribution=distribution
        )

    @classmethod
    def from_scenarios(cls, statement: str, scenarios: Sequence[str]) -> Uncertainty:
        """Incertitude exprimée par des scénarios."""
        return cls(form=UncertaintyForm.SCENARIOS, statement=statement, scenarios=tuple(scenarios))

    @classmethod
    def from_bound(cls, statement: str, bound: float) -> Uncertainty:
        """Incertitude exprimée par une borne."""
        return cls(form=UncertaintyForm.BOUND, statement=statement, bound=bound)

    @classmethod
    def from_sensitivity(cls, statement: str, sensitivity: str) -> Uncertainty:
        """Incertitude exprimée par une analyse de sensibilité."""
        return cls(form=UncertaintyForm.SENSITIVITY, statement=statement, sensitivity=sensitivity)

    @classmethod
    def qualitative(cls, statement: str) -> Uncertainty:
        """Incertitude exprimée par une conclusion qualitative, et rien de plus."""
        return cls(form=UncertaintyForm.QUALITATIVE, statement=statement)

    def as_dict(self) -> dict[str, object]:
        """Vue sérialisable de la qualification d'incertitude."""
        return {
            "form": self.form.value,
            "statement": self.statement,
            "interval": list(self.interval) if self.interval is not None else None,
            "distribution": self.distribution,
            "scenarios": list(self.scenarios),
            "bound": self.bound,
            "sensitivity": self.sensitivity,
        }


@dataclass(frozen=True, slots=True)
class DerivedVariable:
    """Une grandeur calculée à partir d'observations (contrat §2.4).

    Elle garantit que la valeur est reproductible à partir des observations
    consommées, que la règle de calcul est identifiée et versionnée, et qu'elle
    ne se présente jamais comme une observation de source.

    Les invariants appliqués à la construction :

    - `inputs` est non vide : une grandeur dérivée cite au moins une entrée ;
    - chaque entrée est une observation ou une autre grandeur dérivée ;
    - `nature` est une `ResultNature` : le vocabulaire ne contient pas de
      valeur « observée », et la variable ne porte ni identifiant
      d'observation, ni identifiant de source, ni identifiant de preuve brute ;
    - `method` et `method_version` sont non vides : la règle de calcul est
      identifiée et versionnée ;
    - `parameters` porte les paramètres du calcul, et leur empreinte ;
    - `uncertainty` est obligatoire : une grandeur sans qualification
      d'incertitude est une affirmation sans réserve ;
    - `computed_at` est un instant **avec fuseau**, et `ingested_at` ne peut pas
      lui être antérieur ;
    - la valeur est soit absente — et qualifiée par une `missing_reason` issue
      de la liste contrôlée —, soit présente, soit une série ; une absence
      n'est jamais un zéro (INV-19).

    > `valid_time` est le temps du **phénomène** décrit, pas celui du calcul.
    > Il est absent quand ce temps n'est pas établi : le contrat admet l'absence
    > qualifiée, il n'invente pas de date.
    """

    variable_id: str
    quantity: str
    unit: str
    nature: ResultNature
    method: str
    method_version: str
    parameters: ModelParameters
    computed_at: datetime
    uncertainty: Uncertainty
    inputs: tuple[Observation | DerivedVariable, ...]
    value: float | None = None
    values: tuple[float, ...] = ()
    valid_time: datetime | None = None
    ingested_at: datetime | None = None
    spatial_ref: str = "non_spatial"
    key: str | None = None
    missing_reason: MissingReason | None = None

    def __post_init__(self) -> None:
        _exiger_texte(self.variable_id, "DerivedVariable.variable_id")
        _exiger_texte(self.quantity, "DerivedVariable.quantity")
        _exiger_texte(self.unit, "DerivedVariable.unit")
        _exiger_texte(self.method, "DerivedVariable.method")
        _exiger_texte(self.method_version, "DerivedVariable.method_version")
        _exiger_texte(self.spatial_ref, "DerivedVariable.spatial_ref")

        if not isinstance(self.nature, ResultNature):
            raise TypeError("DerivedVariable.nature doit être une ResultNature")
        if not isinstance(self.parameters, ModelParameters):
            raise TypeError("DerivedVariable.parameters doit être des ModelParameters")
        if not isinstance(self.uncertainty, Uncertainty):
            raise TypeError("DerivedVariable.uncertainty doit être une Uncertainty")
        if self.missing_reason is not None and not isinstance(self.missing_reason, MissingReason):
            raise TypeError("DerivedVariable.missing_reason doit être une MissingReason")

        object.__setattr__(
            self, "computed_at", to_utc(self.computed_at, name="DerivedVariable.computed_at")
        )
        if self.valid_time is not None:
            object.__setattr__(
                self, "valid_time", to_utc(self.valid_time, name="DerivedVariable.valid_time")
            )
        if self.ingested_at is not None:
            object.__setattr__(
                self, "ingested_at", to_utc(self.ingested_at, name="DerivedVariable.ingested_at")
            )
            if self.ingested_at < self.computed_at:
                raise ValueError(
                    "une grandeur dérivée ne peut pas être acquise avant d'être calculée"
                )

        object.__setattr__(self, "inputs", tuple(self.inputs))
        if not self.inputs:
            raise ValueError("une grandeur dérivée cite au moins une entrée (contrat §2.4)")
        for item in self.inputs:
            if not isinstance(item, (Observation, DerivedVariable)):
                raise TypeError(
                    "DerivedVariable.inputs ne contient que des observations ou des "
                    "grandeurs dérivées"
                )

        object.__setattr__(
            self,
            "values",
            tuple(
                _exiger_nombre(valeur, f"DerivedVariable.values[{index}]")
                for index, valeur in enumerate(self.values)
            ),
        )
        if self.value is not None:
            object.__setattr__(self, "value", _exiger_nombre(self.value, "DerivedVariable.value"))

        if self.value is not None and self.values:
            raise ValueError("une grandeur dérivée porte une valeur ou une série, jamais les deux")
        if self.value is None and not self.values and self.missing_reason is None:
            raise ValueError("une valeur absente porte une raison d'absence (INV-18)")
        if self.value is not None and self.missing_reason is not None:
            raise ValueError("une valeur présente ne porte pas de raison d'absence (INV-18)")
        if self.values and self.missing_reason is not None:
            raise ValueError("une valeur présente ne porte pas de raison d'absence (INV-18)")

    # -- Temporalité --------------------------------------------------------

    @property
    def temporal(self) -> TemporalStamp:
        """La temporalité **propre** de la grandeur dérivée (contrat §2.4).

        `KNOWN_AT` est l'instant **du calcul** (`computed_at`), jamais celui de
        la source : c'est le point de fuite principal du contrat, et il est
        fermé par construction — `KNOWN_AT` n'est pas un champ que l'appelant
        puisse remplir. `INGESTED_AT` vaut `computed_at` par défaut, et ne
        peut pas lui être antérieur.

        `VALID_TIME` est le temps du phénomène décrit, et lui seul.
        """
        return TemporalStamp(
            valid_time=self.valid_time,
            known_at=self.computed_at,
            ingested_at=self.ingested_at if self.ingested_at is not None else self.computed_at,
            publication=PublicationState.ESTABLISHED,
        )

    # -- Lignée -------------------------------------------------------------

    @property
    def input_observations(self) -> tuple[Observation, ...]:
        """Les observations consommées **directement**."""
        return tuple(item for item in self.inputs if isinstance(item, Observation))

    @property
    def input_variables(self) -> tuple[DerivedVariable, ...]:
        """Les grandeurs dérivées consommées **directement**."""
        return tuple(item for item in self.inputs if isinstance(item, DerivedVariable))

    @property
    def transitive_observations(self) -> tuple[Observation, ...]:
        """Toutes les observations consommées, transitivement jusqu'aux bruts.

        C'est la forme vérifiable d'INV-29 : l'ensemble des observations
        consommées est reconstructible depuis la variable, et donc depuis le
        produit qui la cite.
        """
        return _observations_transitives(self)

    @property
    def transitive_variables(self) -> tuple[DerivedVariable, ...]:
        """Toutes les grandeurs dérivées consommées, transitivement."""
        return _variables_transitives(self)

    # -- Statut de qualité --------------------------------------------------

    @property
    def status(self) -> QualityStatus:
        """Le statut de qualité de la grandeur, déduit de ses entrées (§3.7).

        Le statut n'est pas déclaré : il est **calculé**. Une information
        provisoire est conservée et porte son statut (INV-21) ; ce statut
        remonte la chaîne, et une grandeur calculée sur une entrée provisoire
        ne peut pas se présenter comme acquise.

        - une entrée de statut inconnu → la grandeur est de statut inconnu ;
        - sinon une entrée provisoire → la grandeur est provisoire ;
        - sinon la grandeur est approuvée : rien dans ses entrées n'est
          provisoire.
        """
        statuts = [
            item.quality_status if isinstance(item, Observation) else item.status
            for item in self.inputs
        ]
        if QualityStatus.UNKNOWN in statuts:
            return QualityStatus.UNKNOWN
        if QualityStatus.PROVISIONAL in statuts:
            return QualityStatus.PROVISIONAL
        return QualityStatus.APPROVED

    # -- Construction depuis un résultat ------------------------------------

    @classmethod
    def from_result(
        cls,
        *,
        result: ModelResult,
        output: str,
        variable_id: str,
        quantity: str,
        unit: str,
        inputs: Sequence[Observation | DerivedVariable],
        uncertainty: Uncertainty,
        valid_time: datetime | None = None,
        ingested_at: datetime | None = None,
        spatial_ref: str = "non_spatial",
        key: str | None = None,
    ) -> DerivedVariable:
        """Construit une grandeur dérivée depuis une sortie de résultat.

        La nature est celle **de la sortie**, pas celle du résultat pris en
        bloc : une même exécution peut restituer un état reconstruit et émettre
        une prévision, et les deux grandeurs doivent le dire chacune de son
        côté (`ModelResult.output_natures`).

        L'instant du calcul est l'instant de production du résultat : c'est lui
        qui devient le `KNOWN_AT` de la grandeur.
        """
        return cls(
            variable_id=variable_id,
            quantity=quantity,
            unit=unit,
            nature=result.output_nature(output),
            method=result.spec.method,
            method_version=result.spec.version,
            parameters=result.parameters,
            computed_at=result.produced_at,
            uncertainty=uncertainty,
            inputs=tuple(inputs),
            values=tuple(result.outputs[output]),
            valid_time=valid_time,
            ingested_at=ingested_at,
            spatial_ref=spatial_ref,
            key=key,
        )

    def as_dict(self) -> dict[str, object]:
        """Vue sérialisable de la grandeur dérivée."""
        return {
            "variable_id": self.variable_id,
            "quantity": self.quantity,
            "unit": self.unit,
            "nature": self.nature.value,
            "method": self.method,
            "method_version": self.method_version,
            "parameters_fingerprint": self.parameters.fingerprint(),
            "computed_at": self.computed_at.isoformat(),
            "valid_time": self.valid_time.isoformat() if self.valid_time is not None else None,
            "ingested_at": self.ingested_at.isoformat() if self.ingested_at is not None else None,
            "known_at": self.temporal.known_at.isoformat(),
            "value": self.value,
            "values": list(self.values),
            "missing_reason": (
                self.missing_reason.value if self.missing_reason is not None else None
            ),
            "status": self.status.value,
            "uncertainty": self.uncertainty.as_dict(),
            "spatial_ref": self.spatial_ref,
            "key": self.key,
            "inputs": [_entree_vers_dict(item) for item in self.inputs],
        }


def _entree_vers_dict(item: Observation | DerivedVariable) -> dict[str, object]:
    """Vue sérialisable d'une entrée citée par une grandeur dérivée."""
    if isinstance(item, Observation):
        return {
            "kind": "observation",
            "identifier": item.observation_id,
            "quality_status": item.quality_status.value,
        }
    return {
        "kind": "derived_variable",
        "identifier": item.variable_id,
        "nature": item.nature.value,
        "status": item.status.value,
    }


def _observations_transitives(variable: DerivedVariable) -> tuple[Observation, ...]:
    """Observations consommées par `variable`, transitivement, sans doublon."""
    vues: set[str] = set()
    resultat: list[Observation] = []
    for item in variable.inputs:
        for observation in (
            (item,) if isinstance(item, Observation) else item.transitive_observations
        ):
            if observation.observation_id not in vues:
                vues.add(observation.observation_id)
                resultat.append(observation)
    return tuple(resultat)


def _variables_transitives(variable: DerivedVariable) -> tuple[DerivedVariable, ...]:
    """Grandeurs dérivées consommées par `variable`, transitivement, sans doublon.

    L'ordre est celui de la citation : une grandeur consommée directement
    vient avant celles qu'elle consomme à son tour.
    """
    vues = {variable.variable_id}
    resultat: list[DerivedVariable] = []
    for item in variable.inputs:
        if isinstance(item, DerivedVariable):
            if item.variable_id not in vues:
                vues.add(item.variable_id)
                resultat.append(item)
            for sous in item.transitive_variables:
                if sous.variable_id not in vues:
                    vues.add(sous.variable_id)
                    resultat.append(sous)
    return tuple(resultat)


__all__ = [
    "DerivedVariable",
    "Uncertainty",
    "UncertaintyForm",
]
