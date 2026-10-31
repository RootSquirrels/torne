"""Tests de la preuve et de l'intégration du résultat.

Ces tests portent sur trois objets — la source, la preuve brute, l'observation
— sur l'enregistrement d'une exécution, et sur le produit de connaissance qui
en est issu.

Chaque test est une **question** à laquelle le contrat doit répondre par oui
ou par non : les invariants d'observation, la complétude de la lignée,
l'admissibilité des observations citées (INV-30), la cohérence des révisions,
la nature du produit, la coexistence des versions, et la sérialisation.

Aucun test de ce fichier ne dépend du réseau ni d'une API externe.
"""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace
from datetime import datetime

import pytest

from torne.contracts.derived import DerivedVariable, Uncertainty
from torne.contracts.knowledge import KnowledgeProduct, ProductStatus, ProvenanceKind
from torne.contracts.model import (
    ModelInputs,
    ModelParameters,
    ModelResult,
    ModelSpec,
    ResultNature,
)
from torne.contracts.observation import Observation, QualityStatus, RawEvidence, Source
from torne.contracts.time import PublicationState, TemporalStamp
from torne.contracts.validity import MissingReason, PointValidity
from torne.evaluation.report import evaluate_walk_forward
from torne.execution.runner import execute
from torne.knowledge.record import build_record, verify_lineage

# --------------------------------------------------------------------------
# Fixtures de test
# --------------------------------------------------------------------------

SPEC = ModelSpec(
    model_id="niveau",
    version="1.2.0",
    question="Quel est le niveau de la station de mesure ?",
    method="Moyenne glissante sur la fenêtre déclarée",
    natures=(ResultNature.ESTIMATED,),
)

ENTREES = ModelInputs(series={"niveau": (3.25, 3.30, 3.28)})
PARAMETRES = ModelParameters(values={"fenetre": 3})

EXPRESSION = "2026-10-01T00:00:00+00:00"
PUBLICATION = "2026-10-05T08:00:00+00:00"
INGESTION = "2026-10-06T09:00:00+00:00"
EXECUTION = "2026-10-07T12:00:00+00:00"


def _instant(texte: str) -> datetime:
    return datetime.fromisoformat(texte)


def _stamp(
    *,
    publication: str = PUBLICATION,
    ingestion: str = INGESTION,
    etat: PublicationState = PublicationState.ESTABLISHED,
) -> TemporalStamp:
    return TemporalStamp(
        valid_time=_instant(EXPRESSION),
        known_at=_instant(publication),
        ingested_at=_instant(ingestion),
        publication=etat,
    )


SOURCE = Source(
    source_id="src-station",
    producer="Service hydrométrique",
    dataset="niveaux",
    access_point="https://exemple.invalid/flux",
    license="ODbL",
    revision_policy="révision à trente jours",
    unit="m",
    timezone="Europe/Paris",
    quality_status="contrôlé",
)

PREUVE = RawEvidence(
    evidence_id="a" * 64,
    source_id="src-station",
    acquired_at=_instant(INGESTION),
    media_type="application/json",
    content_sha256="a" * 64,
    key="2026-10-01",
)


def _observation(**champs: object) -> Observation:
    defauts: dict[str, object] = {
        "observation_id": "obs-2026-10-01",
        "source_id": "src-station",
        "quantity": "niveau",
        "unit": "m",
        "temporal": _stamp(),
        "evidence_id": "a" * 64,
        "value": 3.25,
        "validity": PointValidity.VALID,
        "spatial_ref": "station:1234",
        "key": "niveau",
        "quality_status": QualityStatus.APPROVED,
    }
    defauts.update(champs)
    return Observation(**defauts)  # type: ignore[arg-type]


class ModeleMoyenne:
    """Modèle de test : une moyenne des séries fournies."""

    spec = SPEC
    required_parameters = ("fenetre",)

    def run(
        self,
        inputs: ModelInputs,
        params: ModelParameters,
        *,
        seed: int | None = None,
    ) -> ModelResult:
        return ModelResult(
            spec=self.spec,
            nature=ResultNature.ESTIMATED,
            parameters=params,
            produced_at=_instant(EXECUTION),
            outputs={"moyenne": (3.27,)},
            diagnostics={"fenetre": int(params.values["fenetre"])},
        )


def _issue():
    return execute(
        ModeleMoyenne(),
        ENTREES,
        PARAMETRES,
        seed=7,
        now=_instant(EXECUTION),
    )


def _evaluation() -> dict[str, object]:
    """Une évaluation réelle, sérialisée, produite par le module d'évaluation."""
    rapport = evaluate_walk_forward(
        (1.0, 2.0, 3.0, 4.0, 5.0, 6.0),
        lambda bloc: (float(bloc[-1]), float(bloc[-1])),
        initial_size=2,
        step=2,
        model_id=SPEC.model_id,
        model_version=SPEC.version,
        now=_instant(EXECUTION),
    )
    return rapport.as_dict()


def _record(
    *,
    observations: tuple[Observation, ...] | None = None,
    preuves: tuple[RawEvidence, ...] | None = None,
    sources: tuple[Source, ...] | None = None,
    evaluation: dict[str, object] | None = None,
    variables: tuple[DerivedVariable, ...] = (),
):
    return build_record(
        _issue(),
        record_id="enr-001",
        input_observations=observations if observations is not None else (_observation(),),
        evidence=preuves if preuves is not None else (PREUVE,),
        sources=sources if sources is not None else (SOURCE,),
        evaluation=evaluation,
        inputs=ENTREES,
        derived_variables=variables,
    )


def _produit(record, *, version: str = "1.0.0", status: ProductStatus = ProductStatus.USABLE):
    return record.to_product(
        product_id="produit-niveau",
        version=version,
        status=status,
        domain_of_validity="stations du bassin moyen, campagne 2026",
        uncertainty="incertitude de mesure déclarée par la source, de l'ordre de deux centimètres",
    )


# --------------------------------------------------------------------------
# Invariants de l'observation
# --------------------------------------------------------------------------


def test_une_valeur_absente_sans_raison_est_refusee():
    """INV-18 : une valeur absente porte une raison d'absence issue d'une liste."""
    with pytest.raises(ValueError, match="raison d'absence"):
        _observation(value=None, missing_reason=None)


def test_une_observation_manquante_sans_raison_est_refusee():
    """INV-18 : `MISSING` sans raison d'absence n'est pas une observation."""
    with pytest.raises(ValueError, match="raison d'absence"):
        _observation(value=None, validity=PointValidity.MISSING, missing_reason=None)


def test_une_observation_valide_sans_valeur_est_refusee():
    """INV-19 : une observation valide porte une valeur."""
    with pytest.raises(ValueError, match="observation valide"):
        _observation(
            value=None, validity=PointValidity.VALID, missing_reason=MissingReason.NOT_MEASURED
        )


def test_une_observation_avec_une_valeur_et_une_raison_est_refusee():
    """INV-18 : une raison d'absence et une valeur ne se portent pas ensemble."""
    with pytest.raises(ValueError, match="raison d'absence"):
        _observation(value=3.25, missing_reason=MissingReason.NOT_MEASURED)


def test_une_unite_vide_est_refusee():
    """INV-23 : toute observation porte son unité."""
    with pytest.raises(ValueError, match="unit"):
        _observation(unit="   ")


def test_une_preuve_brute_vide_est_refusee():
    """INV-25 : toute observation se rattache à une preuve brute identifiable."""
    with pytest.raises(ValueError, match="evidence_id"):
        _observation(evidence_id="")


def test_un_referentiel_spatial_vide_est_refusee():
    """INV-23 : toute observation porte son référentiel spatial."""
    with pytest.raises(ValueError, match="spatial_ref"):
        _observation(spatial_ref="")


def test_une_absence_nest_pas_un_zero():
    """INV-19 : l'absence et le zéro sont distinguables, et non convertibles."""
    absente = _observation(
        value=None,
        validity=PointValidity.MISSING,
        missing_reason=MissingReason.NOT_MEASURED,
    )
    zero = _observation(value=0.0)

    assert absente.value is None
    assert absente.validity is PointValidity.MISSING
    assert absente.missing_reason is MissingReason.NOT_MEASURED
    assert zero.value == 0.0
    assert zero.validity is PointValidity.VALID
    assert absente.value != zero.value


def test_une_observation_ne_peut_pas_etre_la_revision_d_elle_meme():
    """Une révision pointe vers une autre observation, jamais vers elle-même."""
    with pytest.raises(ValueError, match="révision d'elle-même"):
        _observation(revision_of="obs-2026-10-01")


# --------------------------------------------------------------------------
# Lignée
# --------------------------------------------------------------------------


def test_la_ligne_contient_le_modele_avec_sa_version_les_parametres_et_la_preuve():
    """INV-27, INV-29 : la lignée permet de remonter du résultat aux bruts."""
    record = _record(evaluation=_evaluation())
    refs = record.lineage()

    modeles = [ref for ref in refs if ref.kind is ProvenanceKind.MODEL]
    assert len(modeles) == 1
    assert modeles[0].identifier == SPEC.model_id
    assert modeles[0].revision == SPEC.version

    parametres = [ref for ref in refs if ref.kind is ProvenanceKind.PARAMETER]
    assert len(parametres) == 1
    assert parametres[0].identifier == record.parameters.fingerprint()

    observations = [ref for ref in refs if ref.kind is ProvenanceKind.OBSERVATION]
    assert [ref.identifier for ref in observations] == ["obs-2026-10-01"]

    preuves = [ref for ref in refs if ref.kind is ProvenanceKind.EVIDENCE]
    assert [ref.identifier for ref in preuves] == [PREUVE.evidence_id]

    sources = [ref for ref in refs if ref.kind is ProvenanceKind.SOURCE]
    assert [ref.identifier for ref in sources] == [SOURCE.source_id]

    evaluations = [ref for ref in refs if ref.kind is ProvenanceKind.EVALUATION]
    assert len(evaluations) == 1
    assert evaluations[0].identifier


def test_la_ligne_ne_porte_pas_evaluation_quand_il_n_y_en_a_pas():
    """Sans évaluation, la lignée ne cite pas d'évaluation."""
    refs = _record().lineage()
    assert [ref for ref in refs if ref.kind is ProvenanceKind.EVALUATION] == []


def test_un_enregistrement_sain_ne_porte_aucun_probleme():
    """La lignée complète et admissible ne produit aucun problème."""
    rapport = verify_lineage(_record(evaluation=_evaluation()))
    assert rapport.ok
    assert rapport.problems == ()
    assert rapport.checks


def test_un_enregistrement_construit_a_la_main_peut_etre_incoherent():
    """Un enregistrement construit à la main peut être incohérent : le garde-fou le voit.

    `build_record` pose toujours les paramètres de la configuration, donc le
    contrôle de cohérence des paramètres n'est pas atteignable par ce chemin.
    Un enregistrement fabriqué directement, lui, peut porter des paramètres
    qui ne sont pas ceux de la configuration exécutée : le contrôle doit alors
    le signaler. Sans ce test, ce contrôle resterait une branche morte.
    """
    record = _record()
    incoherent = replace(record, parameters=ModelParameters(values={"poids": 99.0}))

    rapport = verify_lineage(incoherent)

    assert not rapport.ok
    assert any("paramètres" in probleme for probleme in rapport.problems)


# --------------------------------------------------------------------------
# Cohérence des références
# --------------------------------------------------------------------------


def test_une_observation_citant_une_preuve_inconnue_est_signalee():
    """INV-25 : l'observation doit se rattacher à une preuve brute présente."""
    orpheline = _observation(evidence_id="b" * 64)
    rapport = verify_lineage(_record(observations=(orpheline,)))

    assert not rapport.ok
    assert any("preuve brute inconnue" in probleme for probleme in rapport.problems)


def test_une_preuve_brute_citant_une_source_inconnue_est_signalee():
    """Une preuve brute doit se rattacher à une source présente."""
    orpheline = RawEvidence(
        evidence_id="c" * 64,
        source_id="source-inconnue",
        acquired_at=_instant(INGESTION),
    )
    rapport = verify_lineage(_record(preuves=(orpheline,)))

    assert not rapport.ok
    assert any("source inconnue" in probleme for probleme in rapport.problems)


def test_une_observation_citant_une_source_inconnue_est_signalee():
    """Une observation doit se rattacher à une source présente."""
    orpheline = _observation(source_id="source-inconnue")
    rapport = verify_lineage(_record(observations=(orpheline,)))

    assert not rapport.ok
    assert any("source inconnue" in probleme for probleme in rapport.problems)


def test_deux_observations_de_meme_identifiant_sont_signalees():
    """Deux observations citées ne peuvent pas porter le même identifiant."""
    doublon = _observation(observation_id="obs-2026-10-01")
    rapport = verify_lineage(_record(observations=(_observation(), doublon)))

    assert not rapport.ok
    assert any("même identifiant" in probleme for probleme in rapport.problems)


# --------------------------------------------------------------------------
# Admissibilité (INV-30)
# --------------------------------------------------------------------------


def test_une_observation_a_publication_inconnue_est_non_admissible():
    """INV-10, INV-30 : une publication inconnue n'est jamais admise."""
    obs = _observation(
        temporal=TemporalStamp(
            valid_time=_instant(EXPRESSION),
            ingested_at=_instant(INGESTION),
            publication=PublicationState.UNKNOWN,
        )
    )
    rapport = verify_lineage(_record(observations=(obs,)))

    assert not rapport.ok
    assert any("publication inconnue" in probleme for probleme in rapport.problems)


def test_une_observation_posterieure_au_produit_est_non_admissible():
    """INV-30 : le produit ne cite aucune observation qui n'était pas admissible."""
    obs = _observation(
        temporal=_stamp(
            publication="2026-10-20T08:00:00+00:00", ingestion="2026-10-21T09:00:00+00:00"
        )
    )
    rapport = verify_lineage(_record(observations=(obs,)))

    assert not rapport.ok
    assert any("n'était pas admissible" in probleme for probleme in rapport.problems)


def test_un_rejeu_a_un_instant_antérieur_signale_l_observation_trop_tardive():
    """L'admissibilité se juge à l'instant demandé, pas seulement à l'établissement."""
    obs = _observation(
        temporal=_stamp(
            publication="2026-10-05T08:00:00+00:00", ingestion="2026-10-06T09:00:00+00:00"
        )
    )
    record = _record(observations=(obs,))

    assert verify_lineage(record).ok
    rapport = verify_lineage(record, asof=_instant("2026-10-05T12:00:00+00:00"))
    assert not rapport.ok
    assert any("n'était pas admissible" in probleme for probleme in rapport.problems)


# --------------------------------------------------------------------------
# Révisions
# --------------------------------------------------------------------------


def test_une_revision_qui_pointe_vers_une_observation_absente_est_signalee():
    """Une révision doit pointer vers une observation du jeu cité."""
    revision = _observation(observation_id="obs-revision", revision_of="obs-absente")
    rapport = verify_lineage(_record(observations=(revision,)))

    assert not rapport.ok
    assert any("absente des observations citées" in probleme for probleme in rapport.problems)


def test_une_revision_anterieure_a_la_version_qu_elle_remplace_est_signalee():
    """Une révision est postérieure à la version qu'elle remplace."""
    originale = _observation(observation_id="obs-v1")
    revision = _observation(
        observation_id="obs-v2",
        revision_of="obs-v1",
        temporal=_stamp(
            publication="2026-09-01T08:00:00+00:00",
            ingestion="2026-09-02T09:00:00+00:00",
        ),
    )
    rapport = verify_lineage(_record(observations=(originale, revision)))

    assert not rapport.ok
    assert any("postérieure à la version" in probleme for probleme in rapport.problems)


def test_une_revision_posterieure_est_admissible():
    """Une révision cohérente ne produit aucun problème."""
    originale = _observation(observation_id="obs-v1")
    revision = _observation(
        observation_id="obs-v2",
        revision_of="obs-v1",
        temporal=_stamp(
            publication="2026-10-06T10:00:00+00:00",
            ingestion="2026-10-07T11:00:00+00:00",
        ),
    )
    rapport = verify_lineage(_record(observations=(originale, revision)))

    assert rapport.ok, rapport.problems


# --------------------------------------------------------------------------
# Nature du produit
# --------------------------------------------------------------------------


def test_un_resultat_estime_ne_produit_pas_un_produit_observe():
    """La nature d'un produit n'est jamais déclarée par l'appelant.

    Une observation de source n'a plus de nature dans le vocabulaire des
    grandeurs dérivées : elle a son propre objet, et son propre statut de
    qualité. Un produit ne peut donc pas se présenter comme une observation.
    """
    record = _record()

    with pytest.raises(ValueError, match="nature"):
        record.to_product(
            product_id="produit-niveau",
            version="1.0.0",
            status=ProductStatus.USABLE,
            domain_of_validity="stations du bassin moyen, campagne 2026",
            uncertainty="incertitude de mesure déclarée par la source",
            nature=ResultNature.RECONSTRUCTED,
        )


def test_la_nature_du_produit_vient_du_resultat_du_modele():
    """La nature du produit est celle du résultat, jamais celle de l'appelant."""
    produit = _produit(_record())
    assert produit.nature is ResultNature.ESTIMATED


# --------------------------------------------------------------------------
# Produit de connaissance
# --------------------------------------------------------------------------


def test_le_produit_porte_version_statut_domaine_de_validite_et_incertitude():
    """Le produit est versionné, daté, qualifié et borné."""
    produit = _produit(_record())

    assert produit.product_id == "produit-niveau"
    assert produit.version == "1.0.0"
    assert produit.status is ProductStatus.USABLE
    assert produit.domain_of_validity
    assert produit.uncertainty
    assert produit.produced_at == _instant(EXECUTION)


def test_un_produit_inconclusif_est_un_resultat_valide():
    """Un résultat inconclusif se construit et porte son statut."""
    produit = _produit(_record(), status=ProductStatus.INCONCLUSIVE)

    assert produit.status is ProductStatus.INCONCLUSIVE
    assert produit.lineage


def test_deux_versions_coexistent_et_ne_se_reecrivent_pas():
    """INV-31 : une correction produit une version nouvelle, l'ancienne reste."""
    record = _record()
    premiere = _produit(record, version="1.0.0")
    correction = _produit(record, version="2.0.0", status=ProductStatus.DEGRADED)

    assert premiere.version == "1.0.0"
    assert correction.version == "2.0.0"
    assert premiere is not correction
    assert premiere.status is ProductStatus.USABLE
    assert correction.status is ProductStatus.DEGRADED

    with pytest.raises(FrozenInstanceError):
        premiere.version = "3.0.0"


def test_le_produit_ne_modifie_pas_l_enregistrement():
    """Publier un produit ne réécrit ni le résultat ni la lignée."""
    record = _record()
    avant = record.lineage()
    _produit(record)

    assert record.lineage() == avant
    assert record.result.nature is ResultNature.ESTIMATED


# --------------------------------------------------------------------------
# Grandeurs dérivées et qualification des entrées
# --------------------------------------------------------------------------


def _variable(**champs: object) -> DerivedVariable:
    defauts: dict[str, object] = {
        "variable_id": "var-niveau",
        "quantity": "niveau filtré",
        "unit": "m",
        "nature": ResultNature.RECONSTRUCTED,
        "method": "Filtre de Kalman en espace d'état",
        "method_version": "1.0.0",
        "parameters": PARAMETRES,
        "computed_at": _instant(EXECUTION),
        "uncertainty": Uncertainty.from_interval("état filtré, intervalle à 95 %", (3.2, 3.3)),
        "inputs": (_observation(),),
        "value": 3.27,
        "valid_time": _instant(EXPRESSION),
        "spatial_ref": "station:1234",
        "key": "niveau",
    }
    defauts.update(champs)
    return DerivedVariable(**defauts)  # type: ignore[arg-type]


def test_la_ligne_cite_les_grandeurs_derivees_de_l_enregistrement():
    """La lignée cite les grandeurs dérivées au même titre que les observations."""
    variable = _variable()
    refs = _record(variables=(variable,)).lineage()

    variables = [ref for ref in refs if ref.kind is ProvenanceKind.DERIVED_VARIABLE]
    assert [ref.identifier for ref in variables] == [variable.variable_id]
    assert variables[0].revision == variable.method_version


def test_le_produit_cite_les_grandeurs_derivees_qu_il_publie():
    """Le produit cite les grandeurs dérivées, et les qualifie."""
    variable = _variable()
    produit = _produit(_record(variables=(variable,)))

    variables = [ref for ref in produit.lineage if ref.kind is ProvenanceKind.DERIVED_VARIABLE]
    assert [ref.identifier for ref in variables] == [variable.variable_id]
    assert produit.input_statuses[variable.variable_id] is variable.status


def test_le_produit_qualifie_les_entrees_qu_il_consomme():
    """§3.7 : le produit dit le statut de qualité de ce qu'il consomme."""
    provisoire = _observation(
        observation_id="obs-provisoire",
        quality_status=QualityStatus.PROVISIONAL,
    )
    approuvee = _observation(observation_id="obs-approuvee")
    produit = _produit(_record(observations=(provisoire, approuvee)))

    assert produit.input_statuses["obs-provisoire"] is QualityStatus.PROVISIONAL
    assert produit.input_statuses["obs-approuvee"] is QualityStatus.APPROVED
    assert produit.has_provisional_inputs
    assert produit.provisional_inputs == ("obs-provisoire",)


def test_un_produit_ne_peut_pas_omettre_le_statut_d_une_entree_citee():
    """Une entrée citée sans statut : le produit n'est pas publiable (§3.7)."""
    record = _record()
    with pytest.raises(ValueError, match="statut de qualité"):
        KnowledgeProduct(
            product_id="produit-niveau",
            version="1.0.0",
            nature=ResultNature.ESTIMATED,
            produced_at=_instant(EXECUTION),
            status=ProductStatus.USABLE,
            domain_of_validity="stations du bassin moyen, campagne 2026",
            uncertainty="incertitude de mesure déclarée par la source",
            lineage=record.lineage(),
            summary={},
        )


# --------------------------------------------------------------------------
# Sérialisation
# --------------------------------------------------------------------------


def test_le_produit_est_serialisable_en_json():
    """`as_dict()` produit une structure JSON, sans proxy ni objet opaque."""
    produit = _produit(_record(evaluation=_evaluation()))
    charge = json.dumps(produit.as_dict(), ensure_ascii=False)

    relu = json.loads(charge)
    assert relu["version"] == "1.0.0"
    assert relu["nature"] == "estimated"
    assert relu["status"] == "usable"
    assert relu["lineage"]


def test_le_resume_ne_fuit_pas_de_proxy_en_lecture_seule():
    """Les vues en lecture seule sont converties, jamais exposées."""
    rapport = evaluate_walk_forward(
        (1.0, 2.0, 3.0, 4.0, 5.0, 6.0),
        lambda bloc: (float(bloc[-1]), float(bloc[-1])),
        initial_size=2,
        step=2,
        model_id=SPEC.model_id,
        model_version=SPEC.version,
        now=_instant(EXECUTION),
    )
    record = _record(
        evaluation={
            "model_id": SPEC.model_id,
            "model_version": SPEC.version,
            "evaluated_at": rapport.evaluated_at.isoformat(),
            "metrics": rapport.metrics,
        }
    )
    produit = _produit(record)
    vue = produit.as_dict()

    assert isinstance(vue["summary"], dict)
    assert isinstance(vue["summary"]["evaluation"], dict)
    assert isinstance(vue["summary"]["evaluation"]["metrics"], dict)
    json.dumps(vue, ensure_ascii=False)


def test_le_produit_refuse_une_incertitude_non_qualifiee():
    """L'incertitude est une chaîne qualifiée, pas un nombre."""
    record = _record()
    with pytest.raises(ValueError, match="uncertainty"):
        KnowledgeProduct(
            product_id="produit-niveau",
            version="1.0.0",
            nature=ResultNature.ESTIMATED,
            produced_at=_instant(EXECUTION),
            status=ProductStatus.USABLE,
            domain_of_validity="stations du bassin moyen, campagne 2026",
            uncertainty="   ",
            lineage=record.lineage(),
            summary={},
            input_statuses={"obs-2026-10-01": QualityStatus.APPROVED},
        )
