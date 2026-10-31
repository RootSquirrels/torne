"""Tests des contrats fondamentaux — la forme exécutable de `docs/CONTRATS_FONDAMENTAUX.md`.

Ces tests ne portent sur aucun modèle : ils portent sur les invariants que le
contrat déclare vérifiables (INV-07 à INV-19) et que le reste du dépôtreuse.

Chaque test est une **question** à laquelle le contrat doit répondre par oui
ou par non. Aucun test ne vérifie une valeur au hasard.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import UTC, datetime, timedelta, timezone

import pytest

from torne.contracts.fingerprint import canonical, fingerprint
from torne.contracts.model import (
    ExecutionConfig,
    ModelInputs,
    ModelParameters,
    ModelResult,
    ModelSpec,
    ResultNature,
)
from torne.contracts.time import (
    AcquisitionKind,
    PublicationState,
    ReplayMode,
    TemporalStamp,
    civil_day_to_instant,
    to_utc,
)
from torne.contracts.validity import MissingReason, PointValidity, validity_of


def _instant(text: str) -> datetime:
    return datetime.fromisoformat(text)


# --------------------------------------------------------------------------
# Temporalité
# --------------------------------------------------------------------------


def test_usable_at_est_derive_et_non_stocke():
    """INV-08 : `usable_at` est une fonction, jamais un champ stocké."""
    champs = {champ.name for champ in dataclasses.fields(TemporalStamp)}
    assert "usable_at" not in champs
    assert isinstance(TemporalStamp.usable_at, property)


def test_usable_at_vaut_le_maximum_de_known_at_et_ingested_at():
    """INV-09 : `usable_at = max(KNOWN_AT, INGESTED_AT)`."""
    stamp = TemporalStamp(
        valid_time=_instant("2026-10-01T00:00:00+00:00"),
        known_at=_instant("2026-10-05T08:00:00+00:00"),
        ingested_at=_instant("2026-10-21T10:00:00+00:00"),
        publication=PublicationState.ESTABLISHED,
    )
    assert stamp.usable_at == max(stamp.known_at, stamp.ingested_at)


def test_usable_at_prend_le_maximum_quand_la_borne_domine_l_ingestion():
    """INV-09 et INV-11 : la borne conservatrice peut dominer l'ingestion."""
    stamp = TemporalStamp(
        ingested_at=_instant("2026-10-01T00:00:00+00:00"),
        publication=PublicationState.BOUNDED,
        publication_lower_bound=_instant("2026-10-10T00:00:00+00:00"),
    )
    assert stamp.usable_at == max(stamp.publication_lower_bound, stamp.ingested_at)


def test_publication_inconnue_nest_jamais_admissible():
    """INV-10 : une publication inconnue n'est jamais remplacée par l'ingestion."""
    stamp = TemporalStamp(
        valid_time=_instant("2026-10-01T00:00:00+00:00"),
        ingested_at=_instant("2026-10-02T09:00:00+00:00"),
        publication=PublicationState.UNKNOWN,
    )
    assert stamp.usable_at is None
    assert not stamp.is_visible_at(_instant("2030-01-01T00:00:00+00:00"))


def test_publication_inconnue_refuse_de_porter_un_instant():
    """INV-10 : l'ignorance ne peut pas être contredite par une date."""
    with pytest.raises(ValueError, match="inconnue"):
        TemporalStamp(
            known_at=_instant("2026-10-05T08:00:00+00:00"),
            publication=PublicationState.UNKNOWN,
        )


def test_publication_bornee_est_admissible_a_partir_de_la_borne_seulement():
    """INV-11 : une borne conservatrice n'autorise pas une admission antérieure."""
    stamp = TemporalStamp(
        ingested_at=_instant("2026-10-01T00:00:00+00:00"),
        publication=PublicationState.BOUNDED,
        publication_lower_bound=_instant("2026-10-10T00:00:00+00:00"),
    )
    assert not stamp.is_visible_at(_instant("2026-10-09T23:59:59+00:00"))
    assert stamp.is_visible_at(_instant("2026-10-10T00:00:00+00:00"))
    assert stamp.usable_at == _instant("2026-10-10T00:00:00+00:00")


def test_publication_bornee_exige_une_borne():
    """INV-11 : « bornée » sans borne n'est pas un état valide."""
    with pytest.raises(ValueError, match="bornée"):
        TemporalStamp(publication=PublicationState.BOUNDED)


def test_etablie_exige_l_instant_de_publication():
    """INV-10 : « établie » sans instant de publication est contradictoire."""
    with pytest.raises(ValueError, match="établie"):
        TemporalStamp(publication=PublicationState.ESTABLISHED)


def test_un_instant_sans_fuseau_est_refuse_a_l_entree():
    """INV-15 : le refus est à l'entrée, pas un correctif a posteriori."""
    with pytest.raises(ValueError, match="fuseau"):
        to_utc(datetime(2026, 10, 1, 12, 0, 0))
    with pytest.raises(ValueError, match="fuseau"):
        TemporalStamp(
            known_at=datetime(2026, 10, 5, 8, 0, 0),
            publication=PublicationState.ESTABLISHED,
        )


def test_le_resultat_ne_depend_pas_du_fuseau_de_l_executant():
    """INV-16 : le même instant, exprimé dans deux fuseaux, est le même instant."""
    paris = datetime(2026, 10, 5, 10, 0, 0, tzinfo=timezone(timedelta(hours=2)))
    utc = datetime(2026, 10, 5, 8, 0, 0, tzinfo=UTC)
    assert to_utc(paris) == to_utc(utc)


def test_une_date_civile_ne_se_degrade_en_instant_sans_fuseau_explicite():
    """§3.3 : le fuseau est un paramètre de la décision, pas une convention."""
    from datetime import date

    instant = civil_day_to_instant(date(2026, 10, 5), UTC)
    assert instant == datetime(2026, 10, 5, 0, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="fuseau"):
        civil_day_to_instant(date(2026, 10, 5), None)


def test_une_revision_est_invisible_avant_sa_date_de_revision():
    """INV-12 : interroger l'état à `t` rend la version qu'on croyait ce jour-là."""
    revision = TemporalStamp(
        valid_time=_instant("2026-10-01T00:00:00+00:00"),
        known_at=_instant("2026-10-25T08:00:00+00:00"),
        ingested_at=_instant("2026-10-25T09:00:00+00:00"),
        publication=PublicationState.ESTABLISHED,
    )
    assert not revision.is_visible_at(_instant("2026-10-15T00:00:00+00:00"))
    assert revision.is_visible_at(_instant("2026-10-25T09:00:00+00:00"))


def test_un_reimport_d_archive_est_exclu_du_replay_operationnel():
    """INV-14 : un réimport ne se présente pas comme acquis par TORNE à cette date."""
    stamp = TemporalStamp(
        known_at=_instant("2026-10-01T00:00:00+00:00"),
        ingested_at=_instant("2026-10-02T00:00:00+00:00"),
        publication=PublicationState.ESTABLISHED,
        acquisition=AcquisitionKind.ARCHIVE_REIMPORT,
    )
    asof = _instant("2026-10-03T00:00:00+00:00")
    assert not stamp.is_visible_at(asof, mode=ReplayMode.OPERATIONAL)
    assert stamp.is_visible_at(asof, mode=ReplayMode.PUBLIC)


def test_une_ingestion_anterieure_a_la_publication_est_signalee_et_non_exploitee():
    """§3.2 : `INGESTED_AT < KNOWN_AT` est un cas d'erreur, pas un cas d'exploit."""
    stamp = TemporalStamp(
        known_at=_instant("2026-10-05T08:00:00+00:00"),
        ingested_at=_instant("2026-10-02T09:00:00+00:00"),
        publication=PublicationState.ESTABLISHED,
    )
    assert stamp.has_temporal_incoherence
    assert stamp.usable_at is None
    assert not stamp.is_visible_at(_instant("2030-01-01T00:00:00+00:00"))


# --------------------------------------------------------------------------
# Absence, invalidité, hors-domaine
# --------------------------------------------------------------------------


def test_une_absence_porte_une_raison_et_jamais_zero():
    """INV-18, INV-19 : l'absence est qualifiée, et n'est pas un zéro."""
    assert validity_of(None, MissingReason.NOT_MEASURED) is PointValidity.MISSING
    assert validity_of(0.0, None) is PointValidity.VALID
    assert PointValidity.MISSING is not PointValidity.VALID
    with pytest.raises(ValueError, match="raison d'absence"):
        validity_of(None, None)


def test_les_quatre_etats_de_validite_sont_distincts():
    """INV-18 : absent, invalide et hors-domaine ne se confondent pas."""
    etats = {
        PointValidity.VALID,
        PointValidity.MISSING,
        PointValidity.INVALID,
        PointValidity.OUT_OF_DOMAIN,
    }
    assert len(etats) == 4


# --------------------------------------------------------------------------
# Empreinte
# --------------------------------------------------------------------------


def test_l_empreinte_ne_depend_pas_de_lordre_des_cles():
    """Une empreinte doit être stable, quel que soit l'ordre d'insertion."""
    assert fingerprint({"a": 1, "b": 2}) == fingerprint({"b": 2, "a": 1})


def test_la_forme_canonique_distingue_vrai_de_un():
    """`True` n'est pas `1` : une empreinte qui confondrait les deux serait fausse."""
    assert canonical(True) != canonical(1)
    assert canonical(True) == "true"
    assert canonical(1) == "1"


def test_l_absence_est_serialisable_dans_une_empreinte():
    """Une graine absente est une information, pas une panne.

    `None` doit avoir une forme canonique : une configuration sans graine est
    une configuration, et son empreinte doit se calculer.
    """
    assert canonical(None) == "null"
    assert fingerprint({"seed": None}) == fingerprint({"seed": None})
    assert fingerprint({"seed": None}) != fingerprint({"seed": 0})


def test_deux_parametres_differents_ont_deux_empreintes_differentes():
    """Un changement de paramètre change l'empreinte de rejouabilité."""
    a = ModelParameters({"variance": 1.0})
    b = ModelParameters({"variance": 2.0})
    assert a.fingerprint() != b.fingerprint()
    assert a.fingerprint() == ModelParameters({"variance": 1.0}).fingerprint()


def test_deux_executions_de_meme_configuration_ont_la_meme_empreinte():
    """C'est ce qui rend la rejouabilité vérifiable."""
    config_a = ExecutionConfig(
        model_id="torne.demo",
        model_version="0.1.0",
        seed=42,
        parameters=ModelParameters({"variance": 1.0}),
        inputs_fingerprint="abc",
        library_versions={"python": "3.12.3", "numpy": "2.5.4"},
    )
    config_b = ExecutionConfig(
        model_id="torne.demo",
        model_version="0.1.0",
        seed=42,
        parameters=ModelParameters({"variance": 1.0}),
        inputs_fingerprint="abc",
        library_versions={"numpy": "2.5.4", "python": "3.12.3"},
    )
    assert config_a.fingerprint() == config_b.fingerprint()


def test_l_empreinte_des_entrees_suit_le_contenu():
    """Deux séries différentes n'ont pas la même empreinte."""
    a = ModelInputs({"y": (1.0, 2.0, 3.0)})
    b = ModelInputs({"y": (1.0, 2.0, 4.0)})
    assert a.fingerprint() != b.fingerprint()


# --------------------------------------------------------------------------
# Frontière « Modèles »
# --------------------------------------------------------------------------


def _spec(*natures: ResultNature) -> ModelSpec:
    return ModelSpec(
        model_id="torne.demo.modele",
        version="0.1.0",
        question="Estimer un état latent",
        method="Filtre de Kalman",
        natures=natures,
    )


def test_un_modele_exige_une_identite_et_une_version():
    """Un modèle sans version n'est pas rejouable."""
    with pytest.raises(ValueError, match="version"):
        ModelSpec(
            model_id="torne.demo.modele",
            version="",
            question="q",
            method="m",
            natures=(ResultNature.ESTIMATED,),
        )


def test_la_nature_du_resultat_doit_etre_decleree_par_le_modele():
    """Un résultat porte la mention de ce qu'il est : rien d'autre n'est admis."""
    spec = _spec(ResultNature.ESTIMATED)
    with pytest.raises(ValueError, match="nature"):
        ModelResult(
            spec=spec,
            nature=ResultNature.PREDICTED,
            parameters=ModelParameters({}),
            produced_at=_instant("2026-10-05T08:00:00+00:00"),
        )


def test_les_sorties_et_intervalles_sont_immuables():
    """Un résultat typé ne se modifie pas après coup."""
    result = ModelResult(
        spec=_spec(ResultNature.ESTIMATED),
        nature=ResultNature.ESTIMATED,
        parameters=ModelParameters({}),
        produced_at=_instant("2026-10-05T08:00:00+00:00"),
        outputs={"level": (1.0, 2.0)},
        intervals={"level": ((0.0, 2.0), (1.0, 3.0))},
    )
    with pytest.raises(TypeError):
        result.outputs["level"] = (9.0,)  # type: ignore[index]
    assert result.output("level") == (1.0, 2.0)
    assert result.interval("level")[1] == (1.0, 3.0)


# --------------------------------------------------------------------------
# Frontière « Modèles » — validation du résultat à la construction
# --------------------------------------------------------------------------


def _resultat(**champs: object) -> ModelResult:
    defauts: dict[str, object] = {
        "spec": _spec(ResultNature.ESTIMATED),
        "nature": ResultNature.ESTIMATED,
        "parameters": ModelParameters({}),
        "produced_at": _instant("2026-10-05T08:00:00+00:00"),
        "outputs": {"niveau": (1.0, 2.0)},
    }
    defauts.update(champs)
    return ModelResult(**defauts)  # type: ignore[arg-type]


def test_un_resultat_sans_fuseau_est_refuse():
    """INV-15 : le refus est à l'entrée, pas un correctif a posteriori."""
    with pytest.raises(ValueError, match="fuseau"):
        _resultat(produced_at=datetime(2026, 10, 5, 8, 0, 0))


def test_un_resultat_non_normalise_est_normalise_en_utc():
    """INV-16 : le même instant, exprimé dans un autre fuseau, est le même instant."""
    resultat = _resultat(produced_at=_instant("2026-10-05T10:00:00+02:00"))

    assert resultat.produced_at == _instant("2026-10-05T08:00:00+00:00")
    assert resultat.produced_at.utcoffset() == timedelta(0)


def test_un_intervalle_sans_sortie_correspondante_est_refuse():
    """Un intervalle qui ne porte aucun nom de sortie ne décrit rien."""
    with pytest.raises(ValueError, match="aucune sortie de ce nom"):
        _resultat(intervals={"pression": ((0.0, 1.0), (1.0, 2.0))})


def test_un_intervalle_de_longueur_incoherente_est_refuse():
    """Un intervalle compte autant de couples que la sortie a de valeurs."""
    with pytest.raises(ValueError, match="intervalle"):
        _resultat(intervals={"niveau": ((0.0, 1.0),)})


def test_un_intervalle_a_borne_non_finie_est_refuse():
    """Une borne infinie n'est pas une borne."""
    with pytest.raises(ValueError, match="ne sont pas finies"):
        _resultat(intervals={"niveau": ((0.0, float("inf")), (1.0, 2.0))})


def test_un_intervalle_non_ordonne_est_refuse():
    """Un intervalle inversé n'est pas un intervalle."""
    with pytest.raises(ValueError, match="n'est pas ordonné"):
        _resultat(intervals={"niveau": ((2.0, 1.0), (1.0, 2.0))})


def test_une_nature_de_sortie_non_declaree_est_refusee():
    """Une nature que le modèle ne déclare pas n'est pas une nature de sortie."""
    with pytest.raises(ValueError, match="n'est pas déclarée par le modèle"):
        _resultat(output_natures={"niveau": ResultNature.PREDICTED})


def test_les_natures_de_sortie_doivent_corrpondre_aux_sorties():
    """Les natures déclarées portent exactement les noms des sorties."""
    with pytest.raises(ValueError, match="ne correspondent pas aux sorties"):
        _resultat(output_natures={"autre": ResultNature.ESTIMATED})


def test_un_modele_qui_reconstruit_et_prevoit_est_valide():
    """Un filtre d'état restitue un état et émet une prévision : les deux sont valides."""
    resultat = _resultat(
        spec=_spec(ResultNature.RECONSTRUCTED, ResultNature.PREDICTED),
        nature=ResultNature.RECONSTRUCTED,
        outputs={"level": (1.0,), "forecast": (1.2,)},
        output_natures={
            "level": ResultNature.RECONSTRUCTED,
            "forecast": ResultNature.PREDICTED,
        },
    )

    assert resultat.output_nature("level") is ResultNature.RECONSTRUCTED
    assert resultat.output_nature("forecast") is ResultNature.PREDICTED


def test_la_vue_serialisable_du_resultat_porte_les_natures_par_sortie():
    """La nature se lit sortie par sortie dans la vue sérialisable du résultat."""
    resultat = _resultat(
        spec=_spec(ResultNature.RECONSTRUCTED, ResultNature.PREDICTED),
        nature=ResultNature.RECONSTRUCTED,
        outputs={"level": (1.0,), "forecast": (1.2,)},
        output_natures={
            "level": ResultNature.RECONSTRUCTED,
            "forecast": ResultNature.PREDICTED,
        },
    )
    vue = resultat.as_dict()

    assert vue["nature"] == "reconstructed"
    assert vue["outputs"] == {"level": [1.0], "forecast": [1.2]}
    assert vue["output_natures"] == {"level": "reconstructed", "forecast": "predicted"}
    json.dumps(vue, ensure_ascii=False)
