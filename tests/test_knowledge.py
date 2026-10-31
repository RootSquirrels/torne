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


SPEC_ETAT = ModelSpec(
    model_id="etat",
    version="1.0.0",
    question="Quel est l'état latent de la série, et que peut-on prévoir ?",
    method="Filtre d'état en espace d'état",
    natures=(ResultNature.RECONSTRUCTED, ResultNature.PREDICTED),
)


class ModeleEtatEtPrevision:
    """Modèle de test : restitue un état reconstruit et émet une prévision.

    Les deux natures sont **déclarées par le modèle** : le résultat est valide.
    C'est leur réunion dans un même paquet publié qui est interdite.
    """

    spec = SPEC_ETAT

    def run(
        self,
        inputs: ModelInputs,
        params: ModelParameters,
        *,
        seed: int | None = None,
    ) -> ModelResult:
        return ModelResult(
            spec=self.spec,
            nature=ResultNature.RECONSTRUCTED,
            parameters=params,
            produced_at=_instant(EXECUTION),
            outputs={"level": (3.25,), "forecast": (3.40,)},
            output_natures={
                "level": ResultNature.RECONSTRUCTED,
                "forecast": ResultNature.PREDICTED,
            },
        )


def _record_etat():
    return build_record(
        execute(
            ModeleEtatEtPrevision(),
            ENTREES,
            PARAMETRES,
            seed=7,
            now=_instant(EXECUTION),
        ),
        record_id="enr-etat",
        input_observations=(_observation(),),
        evidence=(PREUVE,),
        sources=(SOURCE,),
        inputs=ENTREES,
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
    produced_at: datetime | None = None,
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
        produced_at=produced_at,
    )


def _produit(record, *, version: str = "1.0.0", status: ProductStatus = ProductStatus.USABLE):
    return record.to_product(
        product_id="produit-niveau",
        version=version,
        status=status,
        domain_of_validity="stations du bassin moyen, campagne 2026",
        uncertainty="incertitude de mesure déclarée par la source, de l'ordre de deux centimètres",
    )


def _produit_etat(record, *, outputs=None, product_id: str = "produit-etat"):
    return record.to_product(
        product_id=product_id,
        version="1.0.0",
        status=ProductStatus.USABLE,
        domain_of_validity="stations du bassin moyen, campagne 2026",
        uncertainty="incertitude de mesure déclarée par la source",
        outputs=outputs,
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
# Publication contrôlée : la lignée est vérifiée au moment de publier
# --------------------------------------------------------------------------


def test_un_enregistrement_invalide_ne_peut_pas_etre_publie():
    """Omettre l'appel à `verify_lineage` ne peut pas publier un enregistrement faux.

    La vérification manuelle est une commodité, pas une garantie : c'est
    `to_product` qui refuse, et qui nomme les écarts.
    """
    orpheline = _observation(evidence_id="b" * 64)
    record = _record(observations=(orpheline,))

    with pytest.raises(ValueError, match="preuve brute inconnue"):
        _produit(record)


def test_une_observation_a_publication_inconnue_empeche_la_publication():
    """INV-10, INV-30 : une publication inconnue n'est jamais admise."""
    obs = _observation(
        temporal=TemporalStamp(
            valid_time=_instant(EXPRESSION),
            ingested_at=_instant(INGESTION),
            publication=PublicationState.UNKNOWN,
        )
    )

    with pytest.raises(ValueError, match="publication inconnue"):
        _produit(_record(observations=(obs,)))


def test_une_observation_posterieure_a_l_instant_de_publication_empeche_la_publication():
    """INV-30 : le produit ne cite aucune observation qui n'était pas admissible."""
    obs = _observation(
        temporal=_stamp(
            publication="2026-10-20T08:00:00+00:00", ingestion="2026-10-21T09:00:00+00:00"
        )
    )

    with pytest.raises(ValueError, match="n'était pas admissible"):
        _produit(_record(observations=(obs,)))


def test_la_publication_juge_l_admissibilite_a_l_instant_effectif_de_publication():
    """L'instant `produced_at` fourni est celui où l'admissibilité se joue.

    L'observation est admissible à l'instant de l'enregistrement, mais pas à
    l'instant de publication demandé : elle n'y entre pas.
    """
    with pytest.raises(ValueError, match="n'était pas admissible"):
        _record().to_product(
            product_id="produit-niveau",
            version="1.0.0",
            status=ProductStatus.USABLE,
            domain_of_validity="stations du bassin moyen, campagne 2026",
            uncertainty="incertitude de mesure déclarée par la source",
            produced_at=_instant("2026-10-06T00:00:00+00:00"),
        )


def test_une_grandeur_derivee_calculee_avant_l_utilisabilite_de_ses_entrees_empeche_la_publication():
    """Une grandeur calculée avant que ses entrées ne soient utilisables ne publie rien."""
    matricule = _variable(
        variable_id="var-matrice",
        computed_at=_instant("2026-10-06T10:00:00+00:00"),
        ingested_at=_instant("2026-10-07T06:00:00+00:00"),
    )
    avale = _variable(
        variable_id="var-avale",
        computed_at=_instant("2026-10-07T05:00:00+00:00"),
        inputs=(matricule,),
    )

    with pytest.raises(ValueError, match="avant l'utilisabilité"):
        _produit(_record(variables=(matricule, avale)))


# --------------------------------------------------------------------------
# Une seule nature par produit (SPEC-009 §3)
# --------------------------------------------------------------------------


def test_une_selection_de_sorties_de_natures_differentes_est_refusee():
    """SPEC-009 §3 : un état reconstruit et une prévision sont deux produits."""
    with pytest.raises(ValueError, match="une seule et même nature") as refus:
        _produit_etat(_record_etat(), outputs=("level", "forecast"))

    message = str(refus.value)
    assert "reconstructed" in message
    assert "predicted" in message
    assert "SPEC-009" in message


def test_le_paquet_complet_de_sorties_de_natures_differentes_est_refuse():
    """Le défaut : toutes les sorties par défaut, deux natures, un seul produit."""
    with pytest.raises(ValueError, match="une seule et même nature"):
        _produit_etat(_record_etat())


def test_une_selection_de_sorties_de_meme_nature_est_acceptee():
    """Une sélection homogène se publie, et sa nature est celle des sorties."""
    produit = _produit_etat(_record_etat(), outputs=("level",))
    assert produit.nature is ResultNature.RECONSTRUCTED


def test_le_produit_publie_la_nature_derivee_des_sorties_publiees():
    """La nature du produit vient des sorties publiées, jamais de l'appelant."""
    prevision = _produit_etat(_record_etat(), outputs=("forecast",), product_id="produit-prevision")
    assert prevision.nature is ResultNature.PREDICTED


def test_la_nature_par_sortie_est_dans_la_serialisation_du_produit():
    """Le produit dit la nature de chacune de ses sorties."""
    produit = _produit_etat(_record_etat(), outputs=("level",))

    assert produit.summary["result"]["output_natures"] == {"level": "reconstructed"}


def test_la_nature_par_sortie_est_dans_la_serialisation_du_resultat():
    """Le résultat dit la nature de chacune de ses sorties."""
    vue = _record_etat().result.as_dict()

    assert vue["output_natures"] == {"level": "reconstructed", "forecast": "predicted"}
    assert vue["nature"] == "reconstructed"


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


# --------------------------------------------------------------------------
# Fermeture de la lignée temporelle
# --------------------------------------------------------------------------
# Un produit ne précède pas ce qu'il publie, et une entrée citée est l'objet
# canonique de l'enregistrement : un même identifiant ne peut pas désigner un
# autre contenu.


def test_une_publication_anterieure_a_la_production_du_resultat_est_refusee():
    """Un produit ne peut pas précéder ce qu'il publie.

    L'instant de publication demandé est postérieur à l'utilisabilité de
    l'observation citée — la lignée est donc admissible à cet instant — mais
    antérieur à la production du résultat publié. C'est un produit antidaté.
    """
    record = _record()

    with pytest.raises(ValueError, match="ne précède pas ce qu'il publie"):
        record.to_product(
            product_id="produit-antidate",
            version="1.0.0",
            status=ProductStatus.USABLE,
            domain_of_validity="stations du bassin moyen, campagne 2026",
            uncertainty="incertitude de mesure déclarée par la source",
            produced_at=_instant("2026-10-07T00:00:00+00:00"),
        )


def test_une_publication_anterieure_a_l_etablissement_de_l_enregistrement_est_refusee():
    """Un produit ne peut pas précéder l'enregistrement qui le porte.

    Ici l'instant de publication est postérieur à la production du résultat,
    mais antérieur à l'établissement de l'enregistrement : le produit
    serait daté d'avant l'acte qui l'établit.
    """
    record = _record(produced_at=_instant("2026-10-09T00:00:00+00:00"))

    with pytest.raises(ValueError, match="avant l'établissement de l'enregistrement"):
        record.to_product(
            product_id="produit-antidate",
            version="1.0.0",
            status=ProductStatus.USABLE,
            domain_of_validity="stations du bassin moyen, campagne 2026",
            uncertainty="incertitude de mesure déclarée par la source",
            produced_at=_instant("2026-10-08T00:00:00+00:00"),
        )


def test_une_observation_substituee_ne_peut_pas_rendre_un_calcul_admissible():
    """Un même identifiant ne peut pas désigner un autre contenu.

    L'enregistrement porte une observation utilisable à partir du 10 octobre.
    La grandeur dérivée en cite une autre instance, de même identifiant,
    utilisable depuis le 4 octobre, et est calculée le 9 octobre. Le contrôle
    de temporalité s'exercerait alors sur le substitut, et laisserait passer
    un calcul antérieur à l'utilisabilité de sa véritable entrée.
    """
    canonique = _observation(
        observation_id="obs-1",
        temporal=TemporalStamp(
            valid_time=_instant(EXPRESSION),
            known_at=_instant("2026-10-10T00:00:00+00:00"),
            ingested_at=_instant("2026-10-10T00:00:00+00:00"),
            publication=PublicationState.ESTABLISHED,
        ),
    )
    substitut = replace(
        canonique,
        temporal=TemporalStamp(
            valid_time=_instant(EXPRESSION),
            known_at=_instant("2026-10-04T00:00:00+00:00"),
            ingested_at=_instant("2026-10-04T00:00:00+00:00"),
            publication=PublicationState.ESTABLISHED,
        ),
    )
    variable = _variable(
        variable_id="var-substituee",
        computed_at=_instant("2026-10-09T00:00:00+00:00"),
        inputs=(substitut,),
    )
    record = _record(
        observations=(canonique,),
        variables=(variable,),
        produced_at=_instant("2026-10-12T00:00:00+00:00"),
    )

    with pytest.raises(ValueError, match="ne peut pas désigner un autre contenu"):
        _produit(record)


def test_le_controle_temporel_s_exerce_sur_l_entree_canonique():
    """La temporalité se juge sur l'entrée canonique, pas sur l'entrée citée."""
    canonique = _observation(
        observation_id="obs-1",
        temporal=TemporalStamp(
            valid_time=_instant(EXPRESSION),
            known_at=_instant("2026-10-10T00:00:00+00:00"),
            ingested_at=_instant("2026-10-10T00:00:00+00:00"),
            publication=PublicationState.ESTABLISHED,
        ),
    )
    substitut = replace(
        canonique,
        temporal=TemporalStamp(
            valid_time=_instant(EXPRESSION),
            known_at=_instant("2026-10-04T00:00:00+00:00"),
            ingested_at=_instant("2026-10-04T00:00:00+00:00"),
            publication=PublicationState.ESTABLISHED,
        ),
    )
    variable = _variable(
        variable_id="var-substituee",
        computed_at=_instant("2026-10-09T00:00:00+00:00"),
        inputs=(substitut,),
    )
    record = _record(
        observations=(canonique,),
        variables=(variable,),
        produced_at=_instant("2026-10-12T00:00:00+00:00"),
    )

    rapport = verify_lineage(record)

    assert not rapport.ok
    assert any(
        "avant l'utilisabilité de l'observation « obs-1 »" in probleme
        for probleme in rapport.problems
    )


def test_une_grandeur_derivee_substituee_ne_peut_pas_remplacer_sa_verite():
    """La même règle pour les grandeurs dérivées citées en entrée.

    La grandeur canonique est calculée le 10 octobre ; la grandeur qui la
    consomme en cite une copie calculée le 4 octobre, et est calculée le
    6 octobre. Le contrôle de temporalité, exercé sur la copie, laisserait
    passer un calcul antérieur à l'utilisabilité de sa véritable entrée.
    """
    canonique = _variable(
        variable_id="var-canonique",
        computed_at=_instant("2026-10-10T00:00:00+00:00"),
        ingested_at=_instant("2026-10-10T00:00:00+00:00"),
    )
    substitut = replace(
        canonique,
        computed_at=_instant("2026-10-04T00:00:00+00:00"),
        ingested_at=_instant("2026-10-04T00:00:00+00:00"),
    )
    consommatrice = _variable(
        variable_id="var-consommatrice",
        computed_at=_instant("2026-10-06T00:00:00+00:00"),
        ingested_at=_instant("2026-10-06T00:00:00+00:00"),
        inputs=(substitut,),
    )
    record = _record(
        variables=(canonique, consommatrice),
        produced_at=_instant("2026-10-12T00:00:00+00:00"),
    )

    with pytest.raises(ValueError, match="ne peut pas désigner un autre contenu"):
        _produit(record)
