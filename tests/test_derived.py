"""Tests de la grandeur dérivée — le cinquième objet du contrat.

Ces tests portent sur `docs/CONTRATS_FONDAMENTAUX.md` §2.4 (la grandeur
dérivée), §3.7 (les informations provisoires) et §4.3-§4.4 (INV-17, INV-21,
INV-22, INV-29).

Chaque test est une **question** à laquelle le contrat doit répondre par oui
ou par non :

- la variable dérivée porte-t-elle sa **propre** temporalité, celle du calcul
  et jamais celle de la source (INV-17) ;
- cite-t-elle ses entrées transitivement jusqu'aux preuves brutes, et
  `verify_lineage` le vérifie-t-il (INV-29) ;
- peut-elle se présenter comme une observation de source (§2.4) ;
- une information provisoire est-elle conservée, porte-t-elle son statut, et
  le produit qui la consomme la distingue-t-il d'une information approuvée
  (INV-21, INV-22) ;
- les six catégories restent-elles distinctes : observation de source,
  estimation statistique, état reconstruit, prévision, simulation, produit de
  connaissance publié.

Aucun test de ce fichier ne dépend du réseau ni d'une API externe.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from torne.contracts.derived import DerivedVariable, Uncertainty, UncertaintyForm
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
from torne.contracts.validity import MissingReason
from torne.execution.runner import execute
from torne.knowledge.record import build_record, verify_lineage

# --------------------------------------------------------------------------
# Fixtures de test
# --------------------------------------------------------------------------

# La source publie le 18 octobre ; le calcul a lieu le 21 octobre. C'est le
# scenario du « point de fuite principal » du contrat (§2.4).
PUBLICATION = "2026-10-18T08:00:00+00:00"
INGESTION = "2026-10-19T09:00:00+00:00"
CALCUL = "2026-10-21T09:00:00+00:00"
EXECUTION = "2026-10-21T09:05:00+00:00"
EXPRESSION = "2026-10-18T00:00:00+00:00"


def _instant(texte: str) -> datetime:
    return datetime.fromisoformat(texte)


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
    key="2026-10-18",
)


def _observation(**champs: object) -> Observation:
    defauts: dict[str, object] = {
        "observation_id": "obs-2026-10-18",
        "source_id": "src-station",
        "quantity": "niveau",
        "unit": "m",
        "temporal": TemporalStamp(
            valid_time=_instant(EXPRESSION),
            known_at=_instant(PUBLICATION),
            ingested_at=_instant(INGESTION),
            publication=PublicationState.ESTABLISHED,
        ),
        "evidence_id": "a" * 64,
        "value": 3.25,
        "spatial_ref": "station:1234",
        "key": "niveau",
    }
    defauts.update(champs)
    return Observation(**defauts)  # type: ignore[arg-type]


OBSERVATION_PROVISOIRE = _observation(quality_status=QualityStatus.PROVISIONAL)
OBSERVATION_APPROUVEE = _observation(
    observation_id="obs-2026-10-18-approuvee",
    quality_status=QualityStatus.APPROVED,
)

PARAMETRES = ModelParameters(values={"fenetre": 3})

INCERTITUDE = Uncertainty.from_interval(
    "l'intervalle de l'état filtré, au niveau de confiance 95 %",
    (3.20, 3.30),
)


def _variable(**champs: object) -> DerivedVariable:
    defauts: dict[str, object] = {
        "variable_id": "var-niveau",
        "quantity": "niveau filtré",
        "unit": "m",
        "nature": ResultNature.RECONSTRUCTED,
        "method": "Filtre de Kalman en espace d'état",
        "method_version": "1.0.0",
        "parameters": PARAMETRES,
        "computed_at": _instant(CALCUL),
        "uncertainty": INCERTITUDE,
        "inputs": (OBSERVATION_PROVISOIRE,),
        "value": 3.25,
        "valid_time": _instant(EXPRESSION),
        "spatial_ref": "station:1234",
        "key": "niveau",
    }
    defauts.update(champs)
    return DerivedVariable(**defauts)  # type: ignore[arg-type]


VARIABLE = _variable()

SPEC = ModelSpec(
    model_id="filtre",
    version="2.0.0",
    question="Quel est l'état latent de la série, et que peut-on prévoir ?",
    method="Filtre d'état en espace d'état",
    natures=(ResultNature.RECONSTRUCTED, ResultNature.PREDICTED),
)

ENTREES = ModelInputs(series={"niveau": (3.25, 3.30, 3.28)})


class ModeleFiltre:
    """Modèle de test : restitue un état et émet une prévision."""

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
            nature=ResultNature.RECONSTRUCTED,
            parameters=params,
            produced_at=_instant(CALCUL),
            outputs={"level": (3.25,), "forecast": (3.40,)},
            output_natures={
                "level": ResultNature.RECONSTRUCTED,
                "forecast": ResultNature.PREDICTED,
            },
        )


def _issue():
    return execute(
        ModeleFiltre(),
        ENTREES,
        PARAMETRES,
        seed=7,
        now=_instant(EXECUTION),
    )


def _record(*, variables: tuple[DerivedVariable, ...] = (VARIABLE,), observations=None):
    return build_record(
        _issue(),
        record_id="enr-001",
        input_observations=(
            (OBSERVATION_PROVISOIRE, OBSERVATION_APPROUVEE)
            if observations is None
            else observations
        ),
        evidence=(PREUVE,),
        sources=(SOURCE,),
        inputs=ENTREES,
        derived_variables=variables,
    )


def _produit(record, *, product_id: str = "produit-niveau"):
    return record.to_product(
        product_id=product_id,
        version="1.0.0",
        status=ProductStatus.USABLE,
        domain_of_validity="stations du bassin moyen, campagne 2026",
        uncertainty="incertitude de l'état filtré, qualifiée en intervalle",
    )


# --------------------------------------------------------------------------
# Temporalité propre (INV-17, §2.4)
# --------------------------------------------------------------------------


def test_une_variable_derivee_n_est_connue_qu_a_l_instant_du_calcul():
    """INV-17 : la variable porte le `KNOWN_AT` du calcul, jamais celui des entrées.

    Une variable calculée le 21 octobre à partir d'observations publiées le
    18 octobre n'est connue que du 21 octobre.
    """
    assert VARIABLE.temporal.known_at == _instant(CALCUL)
    assert VARIABLE.temporal.known_at != OBSERVATION_PROVISOIRE.temporal.known_at
    assert VARIABLE.temporal.known_at != OBSERVATION_APPROUVEE.temporal.known_at
    assert VARIABLE.temporal.usable_at == _instant(CALCUL)


def test_une_variable_derivee_n_est_pas_visible_avant_son_calcul():
    """Une reconstruction postérieure ne se présente pas comme disponible en temps réel."""
    assert not VARIABLE.temporal.is_visible_at(_instant("2026-10-18T23:00:00+00:00"))
    assert VARIABLE.temporal.is_visible_at(_instant(CALCUL))


def test_le_valid_time_decrit_le_phenomene_et_non_le_calcul():
    """`VALID_TIME` est le temps du phénomène décrit ; `KNOWN_AT`, celui du calcul."""
    assert VARIABLE.temporal.valid_time == _instant(EXPRESSION)
    assert VARIABLE.temporal.valid_time != VARIABLE.temporal.known_at


def test_le_known_at_est_derive_et_non_declarable():
    """`KNOWN_AT` n'est pas un champ que l'appelant puisse remplir : il vient du calcul."""
    assert "known_at" not in {champ.name for champ in VARIABLE.__dataclass_fields__.values()}
    assert "temporal" not in {champ.name for champ in VARIABLE.__dataclass_fields__.values()}


def test_une_grandeur_acquise_avant_son_calcul_est_refusee():
    """Une grandeur ne peut pas être acquise avant d'être calculée."""
    with pytest.raises(ValueError, match="avant d'être calculée"):
        _variable(ingested_at=_instant("2026-10-20T00:00:00+00:00"))


# --------------------------------------------------------------------------
# Lignée transitive (INV-29)
# --------------------------------------------------------------------------


def test_une_variable_derivee_cite_ses_entrees_transitivement_jusqu_aux_bruts():
    """INV-29 : l'ensemble des observations consommées est reconstructible."""
    derivee = VARIABLE
    assert derivee.input_observations == (OBSERVATION_PROVISOIRE,)
    assert derivee.transitive_observations == (OBSERVATION_PROVISOIRE,)


def test_une_grandeur_derivee_d_une_grandeur_derivee_remonte_jusqu_aux_observations():
    """La fermeture transitive descend de grandeur en grandeur jusqu'aux observations."""
    intermediaire = _variable(
        variable_id="var-intermediaire",
        nature=ResultNature.DERIVED,
        inputs=(VARIABLE,),
    )
    finale = _variable(
        variable_id="var-finale",
        nature=ResultNature.ESTIMATED,
        inputs=(intermediaire,),
    )

    assert finale.transitive_observations == (OBSERVATION_PROVISOIRE,)
    assert finale.transitive_variables == (intermediaire, VARIABLE)
    assert finale.input_observations == ()


def test_la_ligne_du_produit_remonte_jusqu_aux_bruts():
    """Produit → variable dérivée → observations → preuves brutes → source."""
    record = _record()
    produit = _produit(record)

    genres = {ref.kind for ref in produit.lineage}
    assert ProvenanceKind.DERIVED_VARIABLE in genres
    assert ProvenanceKind.OBSERVATION in genres
    assert ProvenanceKind.EVIDENCE in genres
    assert ProvenanceKind.SOURCE in genres

    variables = [ref for ref in produit.lineage if ref.kind is ProvenanceKind.DERIVED_VARIABLE]
    assert [ref.identifier for ref in variables] == [VARIABLE.variable_id]
    assert variables[0].revision == VARIABLE.method_version


def test_verify_lineage_accepte_un_enregistrement_sain_avec_une_grandeur_derivee():
    """Un enregistrement complet, avec sa grandeur dérivée, ne porte aucun écart."""
    rapport = verify_lineage(_record())
    assert rapport.ok, rapport.problems


def test_une_entree_non_citee_est_signalee():
    """Une grandeur dérivée qui consomme une observation absente des entrées citées."""
    orpheline = _variable(inputs=(_observation(observation_id="obs-absente"),))
    rapport = verify_lineage(_record(variables=(orpheline,)))

    assert not rapport.ok
    assert any("absente des observations citées" in probleme for probleme in rapport.problems)


def test_un_calcul_anterieur_a_l_utilisabilite_de_ses_entrees_est_signale():
    """Une grandeur calculée avant que son entrée ne soit utilisable est impossible."""
    prematuree = _variable(computed_at=_instant("2026-10-17T00:00:00+00:00"))
    rapport = verify_lineage(_record(variables=(prematuree,)))

    assert not rapport.ok
    assert any("avant l'utilisabilité" in probleme for probleme in rapport.problems)


def test_un_calcul_posterieur_a_l_instant_du_produit_est_signale():
    """Une grandeur calculée après l'établissement du produit n'a pas pu l'alimenter."""
    tardive = _variable(computed_at=_instant("2026-10-25T00:00:00+00:00"))
    rapport = verify_lineage(_record(variables=(tardive,)))

    assert not rapport.ok
    assert any("après l'instant du produit" in probleme for probleme in rapport.problems)


# --------------------------------------------------------------------------
# Une grandeur dérivée n'est pas une observation de source (§2.4)
# --------------------------------------------------------------------------


def test_une_variable_derivee_ne_se_presente_pas_comme_une_observation_de_source():
    """Le type est distinct, et rien ne lui permet de porter l'identité d'une source."""
    assert not isinstance(VARIABLE, Observation)
    assert not isinstance(OBSERVATION_PROVISOIRE, DerivedVariable)
    for attribut in ("observation_id", "source_id", "evidence_id", "quality_status"):
        assert not hasattr(VARIABLE, attribut)


def test_le_vocabulaire_des_natures_ne_contient_pas_de_valeur_observee():
    """Une observation de source a son propre objet : le vocabulaire des natures l'ignore."""
    assert not hasattr(ResultNature, "OBSERVED")
    assert {nature.value for nature in ResultNature} == {
        "estimated",
        "reconstructed",
        "predicted",
        "simulated",
        "derived",
    }


def test_une_nature_hors_vocabulaire_est_refusee():
    """La nature d'une grandeur dérivée vient du vocabulaire fermé."""
    with pytest.raises(TypeError, match="ResultNature"):
        _variable(nature="observed")


# --------------------------------------------------------------------------
# Statut de qualité (§3.7, INV-21, INV-22)
# --------------------------------------------------------------------------


def test_une_observation_provisoire_est_conservee_et_porte_son_statut():
    """INV-21 : l'information provisoire est conservée, complète, et qualifiée."""
    provisoire = OBSERVATION_PROVISOIRE

    assert provisoire.value == 3.25
    assert provisoire.quality_status is QualityStatus.PROVISIONAL
    assert provisoire.quality_status is not QualityStatus.APPROVED


def test_le_produit_distingue_une_entree_provisoire_d_une_entree_approuvee():
    """INV-22 : le produit qui les consomme les distingue-t-il ? Oui."""
    produit = _produit(_record())

    assert produit.input_statuses[OBSERVATION_PROVISOIRE.observation_id] is (
        QualityStatus.PROVISIONAL
    )
    assert produit.input_statuses[OBSERVATION_APPROUVEE.observation_id] is (QualityStatus.APPROVED)
    assert OBSERVATION_PROVISOIRE.observation_id in produit.provisional_inputs
    assert OBSERVATION_APPROUVEE.observation_id in produit.approved_inputs
    assert OBSERVATION_APPROUVEE.observation_id not in produit.provisional_inputs
    assert produit.has_provisional_inputs


def test_le_produit_dit_dans_son_contenu_qu_il_consomme_du_provisoire():
    """§3.7 : un produit qui consomme des observations provisoires le dit.

    Le provisoire se lit deux fois : sur l'observation elle-même, et sur la
    grandeur dérivée calculée à partir d'elle — le statut voyage avec la
    valeur, il ne s'arrête pas à la première citation.
    """
    produit = _produit(_record())
    qualification = produit.summary["input_qualification"]

    assert OBSERVATION_PROVISOIRE.observation_id in qualification["provisional"]
    assert VARIABLE.variable_id in qualification["provisional"]
    assert qualification["counts"]["provisional"] == 2
    assert qualification["counts"]["approved"] == 1


def test_un_produit_sans_statut_d_entree_est_refuse():
    """Un produit qui ne dit pas le statut de ce qu'il consomme n'est pas publiable."""
    record = _record()
    with pytest.raises(ValueError, match="statut de qualité"):
        KnowledgeProduct(
            product_id="produit-niveau",
            version="1.0.0",
            nature=ResultNature.RECONSTRUCTED,
            produced_at=_instant(EXECUTION),
            status=ProductStatus.USABLE,
            domain_of_validity="stations du bassin moyen, campagne 2026",
            uncertainty="incertitude de l'état filtré",
            lineage=record.lineage(),
            summary={},
        )


def test_le_statut_provisoire_remonte_de_l_observation_au_produit():
    """§3.7 : le statut voyage avec la valeur, jusqu'au produit de connaissance."""
    assert VARIABLE.status is QualityStatus.PROVISIONAL

    approuvee = _variable(
        variable_id="var-approuvee",
        inputs=(OBSERVATION_APPROUVEE,),
    )
    assert approuvee.status is QualityStatus.APPROVED

    produit = _produit(_record(variables=(approuvee,), observations=(OBSERVATION_APPROUVEE,)))
    assert produit.input_statuses[approuvee.variable_id] is QualityStatus.APPROVED
    assert not produit.has_provisional_inputs


def test_un_statut_inconnu_d_entree_reste_inconnu():
    """L'ignorance ne se transforme pas en approbation."""
    inconnue = _observation(
        observation_id="obs-inconnue",
        quality_status=QualityStatus.UNKNOWN,
    )
    assert _variable(inputs=(inconnue,)).status is QualityStatus.UNKNOWN


# --------------------------------------------------------------------------
# Les six catégories (MISSION : ne pas les collapse)
# --------------------------------------------------------------------------


def test_les_six_categories_restent_distinctes():
    """Observation, estimation, reconstruction, prévision, simulation, produit publié.

    Rien ne permet de déclarer un état reconstruit « estimation », ni une
    prévision « estimation » : la nature se déclare par sortie.
    """
    resultat = _issue().result
    niveau = DerivedVariable.from_result(
        result=resultat,
        output="level",
        variable_id="var-niveau",
        quantity="niveau filtré",
        unit="m",
        inputs=(OBSERVATION_APPROUVEE,),
        uncertainty=INCERTITUDE,
    )
    prevision = DerivedVariable.from_result(
        result=resultat,
        output="forecast",
        variable_id="var-prevision",
        quantity="niveau prévu",
        unit="m",
        inputs=(OBSERVATION_APPROUVEE,),
        uncertainty=INCERTITUDE,
    )

    # 1. l'observation de source est un objet à part, avec son statut
    assert isinstance(OBSERVATION_APPROUVEE, Observation)
    assert not isinstance(OBSERVATION_APPROUVEE, DerivedVariable)

    # 2. les cinq natures de grandeur dérivée sont distinctes
    assert len(set(ResultNature)) == 5

    # 3. un état reconstruit n'est pas une estimation, une prévision non plus
    assert niveau.nature is ResultNature.RECONSTRUCTED
    assert niveau.nature is not ResultNature.ESTIMATED
    assert prevision.nature is ResultNature.PREDICTED
    assert prevision.nature is not ResultNature.ESTIMATED
    assert prevision.nature is not niveau.nature

    # 4. la nature du résultat ne contamine pas ses sorties
    assert resultat.nature is ResultNature.RECONSTRUCTED
    assert resultat.output_nature("forecast") is ResultNature.PREDICTED


def test_une_sortie_sans_nature_declaree_prend_celle_du_resultat():
    """Une sortie non déclarée prend la nature du résultat — et le dit."""
    spec = ModelSpec(
        model_id="simple",
        version="1.0.0",
        question="Quelle grandeur ?",
        method="Moyenne",
        natures=(ResultNature.ESTIMATED,),
    )
    resultat = ModelResult(
        spec=spec,
        nature=ResultNature.ESTIMATED,
        parameters=PARAMETRES,
        produced_at=_instant(CALCUL),
        outputs={"moyenne": (3.27,)},
    )
    assert resultat.output_nature("moyenne") is ResultNature.ESTIMATED


def test_une_nature_non_declaree_pour_une_sortie_inexistante_est_refusee():
    """Une sortie absente n'a pas de nature : le dire est preferable à l'inventer."""
    with pytest.raises(KeyError):
        _issue().result.output_nature("inexistante")


# --------------------------------------------------------------------------
# Qualification d'incertitude (§2.4, RESEARCH §6)
# --------------------------------------------------------------------------


def test_l_incertitude_adapte_sa_forme_a_ce_qui_est_connu():
    """La forme est adaptée au contexte ; une distribution n'est pas requise."""
    intervalle = Uncertainty.from_interval("intervalle", (1.0, 2.0))
    assert intervalle.form is UncertaintyForm.INTERVAL
    assert intervalle.interval == (1.0, 2.0)

    qualitative = Uncertainty.qualitative("la variabilité inter-annuelle n'est pas quantifiable")
    assert qualitative.form is UncertaintyForm.QUALITATIVE
    assert qualitative.interval is None

    scenarios = Uncertainty.from_scenarios("deux scénarios", ("sec", "humide"))
    assert scenarios.form is UncertaintyForm.SCENARIOS
    assert scenarios.scenarios == ("sec", "humide")


def test_une_forme_d_incertitude_incompatible_est_refusee():
    """Une charge utile qui ne correspond pas à la forme est refusée à la construction."""
    with pytest.raises(ValueError, match="charge utile"):
        Uncertainty(form=UncertaintyForm.QUALITATIVE, statement="rien", interval=(1.0, 2.0))
    with pytest.raises(ValueError, match="charge utile"):
        Uncertainty(form=UncertaintyForm.INTERVAL, statement="intervalle")


def test_un_intervalle_non_ordonne_est_refuse():
    """Un intervalle dont les bornes sont inversées n'est pas un intervalle."""
    with pytest.raises(ValueError, match="ordonné"):
        Uncertainty.from_interval("intervalle", (2.0, 1.0))


def test_une_grandeur_derivee_sans_incertitude_est_refusee():
    """§2.4 : la grandeur porte une qualification d'incertitude."""
    with pytest.raises(TypeError, match="Uncertainty"):
        _variable(uncertainty="intervalle")


# --------------------------------------------------------------------------
# Construction de la grandeur
# --------------------------------------------------------------------------


def test_une_grandeur_derivee_sans_entree_est_refusee():
    """§2.4 : une grandeur dérivée cite au moins une entrée."""
    with pytest.raises(ValueError, match="au moins une entrée"):
        _variable(inputs=())


def test_une_entree_qui_n_est_ni_une_observation_ni_une_grandeur_est_refusee():
    """Les entrées sont typées : une entrée muette ne prouve rien."""
    with pytest.raises(TypeError, match="observations ou des grandeurs dérivées"):
        _variable(inputs=("obs-2026-10-18",))


def test_une_grandeur_derivee_ne_porte_ni_valeur_ni_serie_avec_une_raison_d_absence():
    """Absent ≠ zéro : une absence porte sa raison (INV-18, INV-19)."""
    with pytest.raises(ValueError, match="raison d'absence"):
        _variable(value=None, values=())

    absente = _variable(
        value=None,
        values=(),
        missing_reason=MissingReason.NOT_MEASURED,
    )
    assert absente.value is None
    assert absente.missing_reason is MissingReason.NOT_MEASURED


def test_une_grandeur_derivee_ne_porte_pas_a_la_fois_une_valeur_et_une_serie():
    """Une valeur ou une série, jamais les deux."""
    with pytest.raises(ValueError, match="jamais les deux"):
        _variable(value=3.25, values=(3.25, 3.26))


def test_la_regle_de_calcul_est_identifiee_et_versionnee():
    """§2.4 : la règle de calcul est identifiée et versionnée."""
    assert VARIABLE.method
    assert VARIABLE.method_version
    assert VARIABLE.parameters.fingerprint()

    with pytest.raises(ValueError, match="method_version"):
        _variable(method_version="  ")
