"""Enregistrement d'une exécution et vérification de sa lignée.

Ce module est le maillon « preuve et intégration » de la chaîne de TORNE :
il lie une exécution de modèle aux objets qui portent la preuve, et il
permet de remonter du résultat publié jusqu'aux preuves brutes.

Il ne crée ni registre, ni service, ni moteur, ni format de stockage : ce sont
des fonctions et deux dataclasses. L'enregistrement est **figé** : il porte
ce qui a été fait, pas ce qu'il reste à faire.

Quatre règles structurantes :

1. **La nature du produit est dérivée des sorties publiées, jamais de
   l'appelant.** Une sortie de modèle ne peut pas être présentée comme une
   observation directe (`docs/ARCHITECTURE.md` §3), et les sorties publiées
   doivent partager une seule et même nature : un état reconstruit et une
   prévision sont deux produits distincts, pas un produit étiqueté
   (SPEC-009 §3). Le refus est explicite.
2. **Une publication est contrôlée, pas déclarée.** `to_product` vérifie la
   lignée à l'instant effectif de publication et **refuse** de publier un
   enregistrement inadmissible : omettre l'appel à `verify_lineage` ne peut
   pas produire un produit qui ment sur sa provenance.
3. **Aucune observation non admissible n'est admise dans la lignée**
   (INV-30). `verify_lineage` contrôle, à l'instant d'établissement du
   produit, que chaque observation citée était admissible : une publication
   inconnue la rend non admissible, et une observation postérieure au produit
   n'a pas pu l'alimenter. Le même contrôle s'applique aux grandeurs
   dérivées : une grandeur calculée avant que ses entrées ne soient
   utilisables, ou après l'instant du produit, est signalée (INV-17).
4. **Rien n'est réécrit** (INV-31). Une correction produit une version
   nouvelle ; l'ancienne reste consultable. C'est le champ `version` du
   produit qui l'exprime.

L'enregistrement porte les **grandeurs dérivées produites** par l'exécution :
elles relient le résultat aux observations qui l'ont nourci, et c'est par
elles que la lignée remonte du produit jusqu'aux preuves brutes — produit →
variable dérivée → observations → preuves brutes → source (INV-29).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType

from ..contracts.derived import DerivedVariable
from ..contracts.fingerprint import fingerprint
from ..contracts.knowledge import (
    KnowledgeProduct,
    ProductStatus,
    ProvenanceKind,
    ProvenanceRef,
    to_serialisable,
)
from ..contracts.model import (
    ExecutionConfig,
    ModelInputs,
    ModelParameters,
    ModelResult,
    ModelSpec,
    ResultNature,
)
from ..contracts.observation import Observation, QualityStatus, RawEvidence, Source
from ..contracts.time import PublicationState, to_utc
from ..contracts.validity import PointValidity
from ..execution.runner import ExecutionOutcome


@dataclass(frozen=True, slots=True)
class ExecutionRecord:
    """Ce qu'une exécution a produit, et sur quelles entrées.

    L'enregistrement réunit tout ce qui est nécessaire pour rejouer une
    affirmation et pour l'auditer : le modèle (identité **et** version), la
    configuration reproductible, les paramètres, les entrées, le résultat, les
    observations d'entrée, les **grandeurs dérivées produites**, les preuves
    brutes et les sources citées, l'instant d'établissement, et l'évaluation
    si elle existe.

    Il est figé : le corriger consiste à produire un autre enregistrement ou une
    version nouvelle de produit, jamais à muter celui-ci.

    `derived_variables` est le produit de l'exécution au sens du contrat : les
    grandeurs calculées par le modèle, qui cite chacune ses entrées. C'est
    par elles que la lignée remonte du produit jusqu'aux preuves brutes
    (INV-29) : produit → grandeur dérivée → observations → preuves brutes →
    source.
    """

    record_id: str
    spec: ModelSpec
    config: ExecutionConfig
    parameters: ModelParameters
    inputs: ModelInputs
    result: ModelResult
    input_observations: tuple[Observation, ...]
    evidence: tuple[RawEvidence, ...]
    sources: tuple[Source, ...]
    produced_at: datetime
    evaluation: Mapping[str, object] | None = None
    derived_variables: tuple[DerivedVariable, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.record_id, str) or not self.record_id.strip():
            raise ValueError("ExecutionRecord.record_id est obligatoire et non vide")
        object.__setattr__(self, "input_observations", tuple(self.input_observations))
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(self, "sources", tuple(self.sources))
        object.__setattr__(self, "derived_variables", tuple(self.derived_variables))
        for variable in self.derived_variables:
            if not isinstance(variable, DerivedVariable):
                raise TypeError(
                    "ExecutionRecord.derived_variables ne contient que des grandeurs dérivées"
                )
        object.__setattr__(
            self,
            "produced_at",
            to_utc(self.produced_at, name="ExecutionRecord.produced_at"),
        )
        if self.evaluation is not None:
            object.__setattr__(self, "evaluation", MappingProxyType(dict(self.evaluation)))

    def lineage(self) -> tuple[ProvenanceRef, ...]:
        """La lignée complète de l'enregistrement (INV-27, INV-29).

        Elle énumère, dans cet ordre : le **modèle** (identifiant et version),
        les **paramètres** (empreinte), les **observations** d'entrée, les
        **grandeurs dérivées** produites, les **preuves brutes** citées, les
        **sources** citées, et l'**évaluation** lorsqu'elle existe.

        Chaque référence est une `ProvenanceRef` : un type, un identifiant
        stable, un libellé et, quand elle est connue, la version de l'objet
        cité. La lignée permet de remonter du résultat jusqu'aux preuves
        brutes : les preuves et les sources citées portent elles-mêmes les
        identifiants qui permettent de les retrouver.

        Les grandeurs dérivées occupent une place à part entière : chacune cite
        ses entrées, et ces entrées sont, elles aussi, dans la lignée. C'est ce
        qui rend la remontée « produit → variable dérivée → observations →
        preuves brutes → source » possible.
        """
        references: list[ProvenanceRef] = [
            ProvenanceRef(
                kind=ProvenanceKind.MODEL,
                identifier=self.spec.model_id,
                label=self.spec.question,
                revision=self.spec.version,
            ),
            ProvenanceRef(
                kind=ProvenanceKind.PARAMETER,
                identifier=self.parameters.fingerprint(),
                label="paramètres de l'exécution",
            ),
        ]
        references.extend(
            ProvenanceRef(
                kind=ProvenanceKind.OBSERVATION,
                identifier=observation.observation_id,
                label=f"{observation.quantity} ({observation.unit})",
                revision=observation.revision_of,
            )
            for observation in self.input_observations
        )
        references.extend(
            ProvenanceRef(
                kind=ProvenanceKind.DERIVED_VARIABLE,
                identifier=variable.variable_id,
                label=f"{variable.quantity} ({variable.unit}) — {variable.nature.value}",
                revision=variable.method_version,
            )
            for variable in self.derived_variables
        )
        references.extend(
            ProvenanceRef(
                kind=ProvenanceKind.EVIDENCE,
                identifier=preuve.evidence_id,
                label=preuve.key or preuve.media_type,
            )
            for preuve in self.evidence
        )
        references.extend(
            ProvenanceRef(
                kind=ProvenanceKind.SOURCE,
                identifier=source.source_id,
                label=f"{source.producer} — {source.dataset}",
            )
            for source in self.sources
        )
        if self.evaluation is not None:
            references.append(_evaluation_ref(self.evaluation))
        return tuple(references)

    def to_product(
        self,
        *,
        product_id: str,
        version: str,
        status: ProductStatus,
        domain_of_validity: str,
        uncertainty: str,
        produced_at: datetime | None = None,
        outputs: Sequence[str] | None = None,
        **extras: object,
    ) -> KnowledgeProduct:
        """Publie l'enregistrement sous forme de produit de connaissance.

        La publication est **contrôlée**, pas déclarée : `to_product` ne se
        contente pas de fabriquer un produit, il vérifie d'abord que la lignée
        est admissible **à l'instant effectif de publication** — l'instant
        `produced_at` fourni s'il y en a un, sinon celui de l'enregistrement.
        Une lignée invalide **refuse** la publication, et le refus nomme les
        écarts : omettre l'appel à `verify_lineage` ne peut pas publier un
        enregistrement incohérent.

        La **nature** du produit est **dérivée des sorties publiées** : elle
        n'est pas un argument de l'appelant, et `nature=...` reste refusé. Les
        sorties publiées doivent en outre partager **une seule et même nature** :
        un paquet de sorties de natures différentes n'est pas un produit, ce sont
        deux produits distincts (SPEC-009 §3 : `state_estimate_product` et
        `forecast_product` sont deux types de produits, pas un produit étiqueté).
        `outputs` désigne les sorties publiées — toutes par défaut.

        Le produit est **nouveau** : il ne modifie ni l'enregistrement ni son
        résultat. Une correction se publie sous une `version` nouvelle, et
        l'ancienne reste consultable (INV-31).

        Le produit porte la **qualification de ses entrées** : le statut de
        qualité de chaque observation et de chaque grandeur dérivée qu'il
        consomme. Une information provisoire est conservée, porte son statut,
        et ce statut arrive jusqu'ici : le produit qui la consomme la
        distingue d'une information approuvée (§3.7, INV-22).
        """
        if "nature" in extras:
            refuse = extras.pop("nature")
            nature_refusee = refuse.value if isinstance(refuse, ResultNature) else str(refuse)
            raise ValueError(
                "la nature d'un produit n'est jamais déclarée par l'appelant : elle est "
                f"dérivée des sorties publiées ; « {nature_refusee} » est refusé"
            )
        if extras:
            raise TypeError(f"argument(s) inconnu(s) : {', '.join(sorted(extras))}")

        instant = (
            self.produced_at if produced_at is None else to_utc(produced_at, name="produced_at")
        )

        rapport = verify_lineage(self, asof=instant)
        if not rapport.ok:
            raise ValueError(
                f"l'enregistrement « {self.record_id} » n'a pas une lignée admissible à "
                f"l'instant de publication « {instant.isoformat()} » : "
                + " ; ".join(rapport.problems)
            )

        publiees, nature = self._sorties_publiees(outputs)

        return KnowledgeProduct(
            product_id=product_id,
            version=version,
            nature=nature,
            produced_at=instant,
            status=status,
            domain_of_validity=domain_of_validity,
            uncertainty=uncertainty,
            lineage=self.lineage(),
            summary=self._summary(publiees, nature),
            input_statuses=self._input_statuses(),
        )

    def _sorties_publiees(
        self,
        outputs: Sequence[str] | None,
    ) -> tuple[tuple[str, ...], ResultNature]:
        """Les sorties publiées, et la nature qu'elles portent.

        Les sorties publiées doivent partager **une seule et même nature**. Un
        paquet qui mêle un état reconstruit et une prévision ne peut pas être
        étiqueté d'une nature unique : il faut deux produits (SPEC-009 §3).
        La nature retenue est donc **dérivée** des sorties publiées.

        `outputs` absent signifie « toutes les sorties ». À défaut de sortie
        publiée — un résultat sans sortie — la nature du résultat est reprise :
        il n'y a rien à dériver.
        """
        noms = tuple(self.result.outputs) if outputs is None else tuple(outputs)
        inconnues = [nom for nom in noms if nom not in self.result.outputs]
        if inconnues:
            raise ValueError(
                f"sortie(s) inconnue(s) du résultat : {', '.join(inconnues)} "
                f"(sorties disponibles : {', '.join(self.result.outputs)})"
            )
        natures = {self.result.output_nature(nom) for nom in noms}
        if len(natures) > 1:
            detail = ", ".join(f"{nom} : {self.result.output_nature(nom).value}" for nom in noms)
            raise ValueError(
                "les sorties publiées doivent partager une seule et même nature ; natures en "
                f"présence : {detail}. Un état reconstruit et une prévision sont deux produits "
                "distincts (SPEC-009 §3), pas un produit étiqueté d'une seule nature"
            )
        if not natures:
            return noms, self.result.nature
        return noms, next(iter(natures))

    def _input_statuses(self) -> dict[str, QualityStatus]:
        """Statut de qualité de chaque entrée citée par le produit (§3.7).

        Une observation porte le sien ; une grandeur dérivée porte celui que
        ses entrées lui imposent — une grandeur calculée sur une information
        provisoire reste provisoire.
        """
        statuts = {
            observation.observation_id: observation.quality_status
            for observation in self.input_observations
        }
        for variable in self.derived_variables:
            statuts[variable.variable_id] = variable.status
        return statuts

    def _summary(self, publiees: tuple[str, ...], nature: ResultNature) -> dict[str, object]:
        """Contenu du produit : ce que le produit dit, hors lignée.

        Le résumé décrit **ce qui est publié** : les sorties retenues, leurs
        intervalles, et la nature de **chacune** d'elles. La nature globale du
        produit n'y remplace pas la nature par sortie — c'est l'inverse.
        """
        return {
            "record_id": self.record_id,
            "model_id": self.spec.model_id,
            "model_version": self.spec.version,
            "config_fingerprint": self.config.fingerprint(),
            "inputs_fingerprint": self.inputs.fingerprint(),
            "parameters_fingerprint": self.parameters.fingerprint(),
            "result": {
                "nature": nature.value,
                "produced_at": self.result.produced_at.isoformat(),
                "outputs": {nom: list(self.result.outputs[nom]) for nom in publiees},
                "intervals": {
                    nom: [list(paire) for paire in self.result.intervals[nom]]
                    for nom in publiees
                    if nom in self.result.intervals
                },
                "output_natures": {nom: self.result.output_nature(nom).value for nom in publiees},
                "outputs_using_future": list(self.result.outputs_using_future),
                # Les paramètres **effectivement utilisés** par la méthode, qui
                # peuvent avoir été estimés sur les données d'entraînement : ils
                # ne sont pas nécessairement ceux de la configuration.
                "used_parameters": dict(self.result.parameters.as_dict()),
                "diagnostics": dict(self.result.diagnostics),
            },
            "derived_variables": [variable.as_dict() for variable in self.derived_variables],
            "input_qualification": self._qualification_des_entrees(),
            "evaluation": (None if self.evaluation is None else to_serialisable(self.evaluation)),
        }

    def _qualification_des_entrees(self) -> dict[str, object]:
        """Ce que le produit dit de la qualité de ce qu'il consomme (§3.7).

        Un produit qui consomme des observations provisoires le dit : la
        qualification est dans le résumé, donc dans le produit publié, et non
        dans un registre extérieur.
        """
        statuts = self._input_statuses()
        comptes: dict[str, int] = {}
        for statut in statuts.values():
            comptes[statut.value] = comptes.get(statut.value, 0) + 1
        return {
            "counts": dict(sorted(comptes.items())),
            "provisional": sorted(
                identifiant
                for identifiant, statut in statuts.items()
                if statut is QualityStatus.PROVISIONAL
            ),
            "unknown_status": sorted(
                identifiant
                for identifiant, statut in statuts.items()
                if statut is QualityStatus.UNKNOWN
            ),
        }


@dataclass(frozen=True, slots=True)
class LineageReport:
    """Issue d'une vérification de lignée : ce qui a été contrôlé, ce qui cloche.

    `checks` énumère les contrôles **effectués** — la liste est stable, que les
    contrôles passent ou non. `problems` énumère les écarts constatés, un par
    écart, avec la pièce concernée. `ok` ne vaut vrai que si `problems` est
    vide.
    """

    ok: bool
    checks: tuple[str, ...]
    problems: tuple[str, ...]


def build_record(
    outcome: ExecutionOutcome,
    *,
    record_id: str,
    input_observations: Sequence[Observation],
    evidence: Sequence[RawEvidence],
    sources: Sequence[Source],
    produced_at: datetime | None = None,
    evaluation: Mapping[str, object] | None = None,
    inputs: ModelInputs | None = None,
    derived_variables: Sequence[DerivedVariable] = (),
) -> ExecutionRecord:
    """Enregistre une issue d'exécution avec la preuve qui l'a nourrie.

    L'issue d'exécution porte le résultat et la configuration, mais **pas** les
    entrées numériques : elle n'en conserve que l'empreinte. Les observations
    d'entrée sont donc transmises explicitement, avec les preuves brutes et les
    sources qu'elles citent.

    `derived_variables` porte les **grandeurs dérivées produites** par
    l'exécution : chacune cite ses entrées, et c'est par elles que la lignée
    remonte du produit jusqu'aux preuves brutes (INV-29).

    `inputs` permet de transmettre les entrées exactes de l'exécution, telles
    qu'elles ont été fournies au modèle. À défaut, elles sont **reconstruites**
    depuis les observations citées — une série par clé de source, dans l'ordre
    des observations, les points sans valeur n'y entrant pas (une série ne
    contient que des valeurs définies). Cette reconstruction est un repli : dès
    que l'empreinte des entrées transmises diffère de celle de la
    configuration, `verify_lineage` le signale.

    `produced_at` vaut, par défaut, la fin de l'exécution : c'est l'instant
    d'établissement de l'enregistrement, donc l'instant auquel se juge
    l'admissibilité des observations citées.
    """
    observations = tuple(input_observations)
    return ExecutionRecord(
        record_id=record_id,
        spec=outcome.result.spec,
        config=outcome.config,
        parameters=outcome.config.parameters,
        inputs=inputs if inputs is not None else _inputs_from_observations(observations),
        result=outcome.result,
        input_observations=observations,
        evidence=tuple(evidence),
        sources=tuple(sources),
        produced_at=outcome.ended_at if produced_at is None else to_utc(produced_at),
        evaluation=evaluation,
        derived_variables=tuple(derived_variables),
    )


def verify_lineage(record: ExecutionRecord, *, asof: datetime | None = None) -> LineageReport:
    """Vérifie que la lignée de l'enregistrement est complète et admissible.

    Les contrôles effectués sont :

    1. **Existence des preuves brutes citées** — toute observation citée se
       rattache à une preuve brute présente dans l'enregistrement (INV-25) ;
    2. **Existence des sources citées** — toute preuve brute et toute
       observation citée se rattachent à une source présente ;
    3. **Admissibilité des observations citées** — chaque observation citée
       était admissible à l'instant d'établissement du produit : une
       publication inconnue la rend non admissible, et une observation
       postérieure au produit n'a pas pu l'alimenter (INV-30) ;
    4. **Antériorité de la publication** — l'instant effectif de publication ne
       précède ni la production du résultat publié, ni l'établissement de
       l'enregistrement : un produit ne peut pas précéder ce qu'il publie ;
    5. **Cohérence des révisions** — une révision pointe vers une observation
       présente dans le jeu cité et lui est postérieure ;
    6. **Unicité des identifiants cités** ;
    7. **Cohérence de la configuration d'exécution** — modèle, version,
       paramètres et entrées correspondent à ce qui a été exécuté ;
    8. **Cohérence de l'évaluation citée** — l'évaluation porte le même modèle
       et la même version que l'enregistrement ;
    9. **Existence des entrées citées par les grandeurs dérivées** — chaque
       grandeur dérivée produite cite des observations et des grandeurs
       dérivées **présentes** dans l'enregistrement (INV-29) ;
    10. **Identité des entrées citées** — l'entrée citée est l'objet
       **canonique** de l'enregistrement : un même identifiant ne peut pas
       désigner un autre contenu (INV-29) ;
    11. **Fermeture transitive de la lignée** — l'ensemble des observations
       consommées transitivement par les grandeurs dérivées est reconstructible
       depuis l'enregistrement, jusqu'aux preuves brutes (INV-29) ;
    12. **Temporalité du calcul** — une grandeur dérivée n'est pas calculée
       avant que ses entrées ne soient utilisables, et n'est pas calculée
       après l'instant du produit (INV-17, INV-30).

    `asof` est l'instant auquel se pose la question d'admissibilité : par
    défaut, l'instant d'établissement de l'enregistrement.
    """
    moment = (
        to_utc(record.produced_at, name="produced_at")
        if asof is None
        else to_utc(asof, name="asof")
    )

    checks: tuple[str, ...] = (
        "existence des preuves brutes citées (INV-25)",
        "existence des sources citées",
        "admissibilité des observations citées à l'instant du produit (INV-30)",
        "antériorité de l'instant de publication (INV-30)",
        "cohérence des révisions (INV-13)",
        "unicité des identifiants cités",
        "cohérence de la configuration d'exécution",
        "cohérence de l'évaluation citée",
        "existence des entrées citées par les grandeurs dérivées (INV-29)",
        "identité des entrées citées par les grandeurs dérivées (INV-29)",
        "fermeture transitive de la lignée des grandeurs dérivées (INV-29)",
        "temporalité du calcul des grandeurs dérivées (INV-17)",
    )
    problems: list[str] = _problemes_anteriorite_publication(record, moment)

    ids_preuve = {preuve.evidence_id for preuve in record.evidence}
    ids_source = {source.source_id for source in record.sources}
    par_observation = {obs.observation_id: obs for obs in record.input_observations}

    for observation in record.input_observations:
        if observation.evidence_id not in ids_preuve:
            problems.append(
                f"observation « {observation.observation_id} » cite la preuve brute "
                f"inconnue « {observation.evidence_id} »"
            )
        if observation.source_id not in ids_source:
            problems.append(
                f"observation « {observation.observation_id} » cite la source inconnue "
                f"« {observation.source_id} »"
            )

    for preuve in record.evidence:
        if preuve.source_id not in ids_source:
            problems.append(
                f"preuve brute « {preuve.evidence_id} » cite la source inconnue "
                f"« {preuve.source_id} »"
            )

    for observation in record.input_observations:
        problems.extend(_problemes_admissibilite(observation, moment))

    for observation in record.input_observations:
        if observation.revision_of is None:
            continue
        remplacee = par_observation.get(observation.revision_of)
        if remplacee is None:
            problems.append(
                f"observation « {observation.observation_id} » est la révision de "
                f"« {observation.revision_of} », absente des observations citées"
            )
            continue
        instant_revision = observation.temporal.usable_at
        instant_remplacee = remplacee.temporal.usable_at
        if instant_revision is None or instant_remplacee is None:
            # Non comparable : la publication inconnue est déjà signalée par le
            # contrôle d'admissibilité. On n'invente pas de comparaison.
            continue
        if instant_revision <= instant_remplacee:
            problems.append(
                f"observation « {observation.observation_id} » n'est pas postérieure à la "
                f"version qu'elle remplace « {observation.revision_of} »"
            )

    problems.extend(_problemes_unicite(record))
    problems.extend(_problemes_grandeurs_derivees(record, moment))

    if record.config.model_id != record.spec.model_id:
        problems.append(
            f"la configuration exécute le modèle « {record.config.model_id} », "
            f"l'enregistrement porte « {record.spec.model_id} »"
        )
    if record.config.model_version != record.spec.version:
        problems.append(
            f"la configuration exécute la version « {record.config.model_version} », "
            f"l'enregistrement porte « {record.spec.version} »"
        )
    if record.config.parameters.fingerprint() != record.parameters.fingerprint():
        problems.append("les paramètres de l'enregistrement ne sont ceux de la configuration")
    if record.config.inputs_fingerprint != record.inputs.fingerprint():
        problems.append(
            "les entrées de l'enregistrement ne sont pas celles de l'exécution "
            "(empreintes différentes)"
        )

    if record.evaluation is not None:
        model_id = record.evaluation.get("model_id")
        model_version = record.evaluation.get("model_version")
        if isinstance(model_id, str) and model_id != record.spec.model_id:
            problems.append(f"l'évaluation citée porte le modèle « {model_id} »")
        if isinstance(model_version, str) and model_version != record.spec.version:
            problems.append(f"l'évaluation citée porte la version « {model_version} »")

    return LineageReport(ok=not problems, checks=checks, problems=tuple(problems))


def _problemes_anteriorite_publication(record: ExecutionRecord, moment: datetime) -> list[str]:
    """Antériorité de la publication : un produit ne précède pas ce qu'il publie.

    L'instant effectif de publication ne peut être **ni antérieur à la
    production du résultat publié**, **ni antérieur à l'établissement de
    l'enregistrement** qui le porte.

    Un produit daté avant le résultat qu'il contient n'est pas un produit
    antédaté par inadvertance : c'est un produit faux. Il le serait d'autant
    plus qu'il rendrait la lignée vérifiable — les contrôles d'admissibilité
    seraient instruits à un instant où ce qui est publié n'existait pas encore.
    """
    problems: list[str] = []

    production = record.result.produced_at
    if moment < production:
        problems.append(
            f"le produit est établi au « {moment.isoformat()} », avant la production du "
            f"résultat qu'il publie (« {production.isoformat()} ») : un produit ne "
            "précède pas ce qu'il publie"
        )

    etablissement = to_utc(record.produced_at, name="produced_at")
    if moment < etablissement:
        problems.append(
            f"le produit est établi au « {moment.isoformat()} », avant l'établissement de "
            f"l'enregistrement qui le porte (« {etablissement.isoformat()} »)"
        )

    return problems


def _problemes_admissibilite(observation: Observation, moment: datetime) -> list[str]:
    """Contrôle d'admissibilité d'une observation à un instant (INV-30)."""
    stamp = observation.temporal
    if stamp.publication is PublicationState.UNKNOWN:
        return [
            f"observation « {observation.observation_id} » : publication inconnue, "
            "donc non admissible (INV-10, INV-30)"
        ]
    if stamp.has_temporal_incoherence:
        return [
            f"observation « {observation.observation_id} » : incohérence temporelle "
            "(acquisition antérieure à la publication)"
        ]
    if stamp.ingested_at is None:
        return [
            f"observation « {observation.observation_id} » : acquisition non datée, "
            "donc non admissible (INV-07, INV-30)"
        ]
    usable = stamp.usable_at
    if usable is None:
        return [
            f"observation « {observation.observation_id} » : aucun instant d'utilisabilité "
            "dérivable, donc non admissible (INV-30)"
        ]
    if usable > moment:
        return [
            f"observation « {observation.observation_id} » n'était pas admissible à "
            f"l'instant du produit : utilisable à « {usable.isoformat()} », "
            f"produit établi à « {moment.isoformat()} » (INV-30)"
        ]
    return []


def _problemes_unicite(record: ExecutionRecord) -> list[str]:
    """Contrôle d'unicité des identifiants cités."""
    problems: list[str] = []
    for pluriel, identifiants in (
        ("observations", [obs.observation_id for obs in record.input_observations]),
        ("grandeurs dérivées", [var.variable_id for var in record.derived_variables]),
        ("preuves brutes", [preuve.evidence_id for preuve in record.evidence]),
        ("sources", [source.source_id for source in record.sources]),
    ):
        vus: set[str] = set()
        for identifiant in identifiants:
            if identifiant in vus:
                problems.append(f"deux {pluriel} portent le même identifiant « {identifiant} »")
            vus.add(identifiant)
    return problems


def _objet_canonique(
    item: Observation | DerivedVariable,
    par_observation: Mapping[str, Observation],
    par_variable: Mapping[str, DerivedVariable],
) -> Observation | DerivedVariable | None:
    """L'objet canonique de l'enregistrement portant l'identifiant cité.

    Une entrée citée est un **identifiant** ; c'est l'objet canonique de
    l'enregistrement qui fait foi. Sans ce rapprochement, un même identifiant
    pourrait désigner un autre contenu — une observation utilisable plus tôt,
    par exemple — et les contrôles s'exerceraient sur le substitut et non sur
    la vérité.

    Renvoie `None` si l'identifiant cité n'existe pas dans l'enregistrement :
    l'absence est alors signalée par l'appelant.
    """
    if isinstance(item, Observation):
        return par_observation.get(item.observation_id)
    return par_variable.get(item.variable_id)


def _libelle_entree(item: Observation | DerivedVariable) -> str:
    """Le nom d'une entrée citée, avec son genre grammatical."""
    if isinstance(item, Observation):
        return f"l'observation « {item.observation_id} »"
    return f"la grandeur dérivée « {item.variable_id} »"


def _problemes_grandeurs_derivees(record: ExecutionRecord, moment: datetime) -> list[str]:
    """Contrôles propres aux grandeurs dérivées produites par l'exécution.

    Quatre questions, toutes vérifiables :

    1. **Existence des entrées citées** — une grandeur dérivée qui consomme
       une observation ou une autre grandeur dérivée absente de
       l'enregistrement a une lignée incomplète (INV-29) ;
    2. **Identité des entrées citées** — l'entrée citée est l'objet
       **canonique** de l'enregistrement : le même identifiant ne peut pas
       désigner un autre contenu (INV-29) ;
    3. **Fermeture transitive** — l'ensemble des observations consommées
       transitivement est reconstructible depuis l'enregistrement, jusqu'aux
       preuves brutes (INV-29) ;
    4. **Temporalité du calcul** — le calcul n'est pas antérieur à
       l'utilisabilité de ses entrées, ni postérieur à l'instant du produit
       (INV-17, INV-30).

    Les contrôles temporels s'exercent sur les objets **canoniques** : la
    substitutedité d'un objet ne peut pas rendre un calcul admissible avant
    que sa véritable entrée ne soit utilisable.
    """
    problems: list[str] = []
    par_observation = {obs.observation_id: obs for obs in record.input_observations}
    par_variable = {var.variable_id: var for var in record.derived_variables}
    ids_observation = set(par_observation)

    for variable in record.derived_variables:
        for item in variable.inputs:
            canonique = _objet_canonique(item, par_observation, par_variable)
            if canonique is None:
                if isinstance(item, Observation):
                    problems.append(
                        f"grandeur dérivée « {variable.variable_id} » consomme l'observation "
                        f"« {item.observation_id} », absente des observations citées"
                    )
                else:
                    problems.append(
                        f"grandeur dérivée « {variable.variable_id} » consomme la grandeur dérivée "
                        f"« {item.variable_id} », absente des grandeurs citées"
                    )
                continue
            if item != canonique:
                problems.append(
                    f"grandeur dérivée « {variable.variable_id} » consomme "
                    f"{_libelle_entree(item)}, qui n'est pas "
                    f"{_libelle_entree(canonique)} de l'enregistrement : un même "
                    "identifiant ne peut pas désigner un autre contenu"
                )

        for observation in variable.transitive_observations:
            if observation.observation_id not in ids_observation:
                problems.append(
                    f"grandeur dérivée « {variable.variable_id} » : l'observation "
                    f"« {observation.observation_id} » n'est pas dans les observations citées"
                )

        for item in variable.inputs:
            canonique = _objet_canonique(item, par_observation, par_variable)
            if canonique is None:
                continue
            usable = canonique.temporal.usable_at
            if usable is None:
                continue
            if variable.computed_at >= usable:
                continue
            if isinstance(canonique, Observation):
                problems.append(
                    f"grandeur dérivée « {variable.variable_id} » est calculée le "
                    f"« {variable.computed_at.isoformat()} », avant l'utilisabilité de "
                    f"l'observation « {canonique.observation_id} » "
                    f"(« {usable.isoformat()} »)"
                )
            else:
                # L'entrée est une autre grandeur dérivée : ce qui compte est
                # l'instant où elle **devient utilisable**, pas celui où elle a
                # été calculée — une grandeur acquise plus tard n'a pas pu
                # alimenter un calcul antérieur.
                problems.append(
                    f"grandeur dérivée « {variable.variable_id} » est calculée le "
                    f"« {variable.computed_at.isoformat()} », avant l'utilisabilité de "
                    f"la grandeur dérivée « {canonique.variable_id} » qu'elle consomme "
                    f"(« {usable.isoformat()} »)"
                )

        if variable.computed_at > moment:
            problems.append(
                f"grandeur dérivée « {variable.variable_id} » est calculée le "
                f"« {variable.computed_at.isoformat()} », après l'instant du produit "
                f"(« {moment.isoformat()} »)"
            )
    return problems


def _inputs_from_observations(observations: tuple[Observation, ...]) -> ModelInputs:
    """Reconstruit les entrées numériques depuis les observations citées.

    Repli de `build_record` : l'issue d'exécution ne porte pas les entrées,
    seulement leur empreinte. Une série est créée par clé de source (la clé de
    l'observation, à défaut sa quantité), dans l'ordre des observations citées.
    Les observations sans valeur n'y entrent pas : une série ne contient que
    des valeurs définies, et l'absence reste qualifiée dans l'observation.
    """
    series: dict[str, list[float]] = {}
    for observation in observations:
        if observation.value is None or observation.validity is not PointValidity.VALID:
            continue
        nom = observation.key or observation.quantity
        series.setdefault(nom, []).append(float(observation.value))
    return ModelInputs(series={nom: tuple(valeurs) for nom, valeurs in series.items()})


def _evaluation_ref(evaluation: Mapping[str, object]) -> ProvenanceRef:
    """Référence de provenance pour une évaluation citée.

    L'identifiant est l'empreinte du contenu sérialisable de l'évaluation :
    deux évaluations identiques sont la même référence, deux évaluations
    différentes ne le sont pas. La version est l'instant d'évaluation quand il
    est présent.
    """
    charge = json.dumps(to_serialisable(evaluation), sort_keys=True, ensure_ascii=False)
    model_id = evaluation.get("model_id")
    model_version = evaluation.get("model_version")
    libelle = "évaluation"
    if isinstance(model_id, str) and isinstance(model_version, str):
        libelle = f"évaluation {model_id}@{model_version}"
    revision = evaluation.get("evaluated_at")
    return ProvenanceRef(
        kind=ProvenanceKind.EVALUATION,
        identifier=fingerprint(charge),
        label=libelle,
        revision=revision if isinstance(revision, str) else None,
    )


__all__ = [
    "ExecutionRecord",
    "LineageReport",
    "build_record",
    "verify_lineage",
]
