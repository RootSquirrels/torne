"""Tests de l'exécution de modèle : validation, configuration, reproductibilité.

Les modèles de test sont écrits ici, à la main : un modèle de test maison
permet de vérifier ce qu'un modèle tiers ne garantit pas — l'empreinte stable,
la graine transmise, l'erreur non masquée.

Aucun test de ce fichier ne dépend du réseau ni d'une API externe.
"""

from __future__ import annotations

import random
from dataclasses import replace
from datetime import UTC, datetime

import numpy as np
import pytest

from torne.contracts.model import (
    ModelInputs,
    ModelParameters,
    ModelResult,
    ModelSpec,
    ResultNature,
)
from torne.execution.errors import (
    ConfigurationMismatchError,
    InvalidInputError,
    InvalidParameterError,
)
from torne.execution.runner import execute, library_versions, reproduce

SPEC_STUB = ModelSpec(
    model_id="stub",
    version="1.0.0",
    question="Quelle est la moyenne pondérée de la série ?",
    method="Moyenne pondérée des séries",
    natures=(ResultNature.ESTIMATED,),
)

SPEC_ALEATOIRE = ModelSpec(
    model_id="aleatoire",
    version="0.1.0",
    question="Que tire un générateur aléatoire de graine donnée ?",
    method="Tir gaussien par graine",
    natures=(ResultNature.SIMULATED,),
)

SPEC_ECHEC = ModelSpec(
    model_id="en_echec",
    version="1.0.0",
    question="Que se passe-t-il quand le modèle échoue ?",
    method="Échec contrôlé",
    natures=(ResultNature.ESTIMATED,),
)


class StubModel:
    """Modèle déterministe : moyenne pondérée d'une série.

    Il déclare `required_parameters` : le runner peut donc vérifier que les
    paramètres fournis sont exactement ceux qu'il attend.
    """

    required_parameters = ("poids", "offset")

    def __init__(self, spec: ModelSpec = SPEC_STUB) -> None:
        self.spec = spec

    def run(
        self,
        inputs: ModelInputs,
        params: ModelParameters,
        *,
        seed: int | None = None,
    ) -> ModelResult:
        poids = float(params.values["poids"])
        offset = float(params.values["offset"])
        moyennes = tuple(
            offset + poids * float(np.mean(valeurs)) for valeurs in inputs.series.values()
        )
        return ModelResult(
            spec=self.spec,
            nature=ResultNature.ESTIMATED,
            parameters=params,
            produced_at=datetime.now(UTC),
            outputs={"moyenne": moyennes},
        )


class ModelAvecParametresOptionnels(StubModel):
    """Modèle qui déclare des paramètres optionnels en plus des requis.

    Les optionnels sont acceptés quand ils sont fournis, et leur valeur par
    défaut s'applique sinon ; ils ne sont jamais exigés.
    """

    optional_parameters = ("amplitude",)


class StochasticModel:
    """Modèle stochastique : le modèle fabrique son propre générateur.

    Il n'expose pas `required_parameters` : le runner ne doit donc rien lui
    imposer sur ses paramètres.
    """

    spec = SPEC_ALEATOIRE

    def run(
        self,
        inputs: ModelInputs,
        params: ModelParameters,
        *,
        seed: int | None = None,
    ) -> ModelResult:
        generateur = np.random.default_rng(seed)
        tirages = tuple(
            float(valeur) for valeur in generateur.standard_normal(len(inputs.series["mesures"]))
        )
        return ModelResult(
            spec=self.spec,
            nature=ResultNature.SIMULATED,
            parameters=params,
            produced_at=datetime.now(UTC),
            outputs={"tirage": tirages},
        )


class FailingModel:
    """Modèle qui échoue : l'erreur doit remonter intacte."""

    spec = SPEC_ECHEC

    def run(
        self,
        inputs: ModelInputs,
        params: ModelParameters,
        *,
        seed: int | None = None,
    ) -> ModelResult:
        raise ValueError("échec contrôlé")


def _entrees() -> ModelInputs:
    return ModelInputs(series={"mesures": (1.0, 2.0, 3.0), "reference": (2.0, 2.0, 2.0)})


def _parametres() -> ModelParameters:
    return ModelParameters(values={"poids": 2.0, "offset": 1.0})


def _etat_numpy() -> tuple[str, bytes, int, int, float]:
    """Rend l'état du générateur global de numpy sous une forme comparable."""
    nom, tableau, position, gaussien, cache = np.random.get_state()
    return (nom, tableau.tobytes(), position, gaussien, cache)


def test_deux_executions_identiques_partagent_la_meme_empreinte_et_le_meme_resultat():
    """Même entrées, mêmes paramètres, même graine : même empreinte, mêmes sorties."""
    premier = execute(StubModel(), _entrees(), _parametres(), seed=7)
    second = execute(StubModel(), _entrees(), _parametres(), seed=7)

    assert premier.config.fingerprint() == second.config.fingerprint()
    assert premier.result.outputs == second.result.outputs


def test_l_empreinte_de_configuration_ne_depend_pas_du_temps():
    """Les horodatages changent, l'empreinte de configuration reste la même."""
    premier = execute(
        StubModel(), _entrees(), _parametres(), seed=7, now=datetime(2026, 1, 1, tzinfo=UTC)
    )
    second = execute(
        StubModel(), _entrees(), _parametres(), seed=7, now=datetime(2027, 6, 30, tzinfo=UTC)
    )

    assert premier.started_at != second.started_at
    assert premier.ended_at != second.ended_at
    assert premier.config.fingerprint() == second.config.fingerprint()


def test_la_configuration_ne_porte_aucun_horodatage():
    """Le temps est une métadonnée de l'issue, jamais une donnée de configuration."""
    issue = execute(
        StubModel(), _entrees(), _parametres(), seed=7, now=datetime(2026, 1, 1, tzinfo=UTC)
    )

    assert not hasattr(issue.config, "started_at")
    assert not hasattr(issue.config, "ended_at")
    assert issue.duration_seconds == 0.0


def test_les_horodatages_de_l_issue_sont_en_utc():
    """Sans horloge injectée, l'issue porte deux instants UTC datés."""
    issue = execute(StubModel(), _entrees(), _parametres(), seed=7)

    assert issue.started_at.tzinfo is not None
    assert issue.ended_at.tzinfo is not None
    assert issue.ended_at >= issue.started_at
    assert issue.duration_seconds >= 0.0


def test_une_horloge_injectee_sans_fuseau_est_refusee():
    """Un instant sans fuseau est refusé à l'entrée (INV-15)."""
    with pytest.raises(ValueError, match="fuseau"):
        execute(StubModel(), _entrees(), _parametres(), seed=7, now=datetime(2026, 1, 1))


def test_un_parametre_manquant_est_refuse():
    """Un paramètre attendu par le modèle et absent est un paramètre manquant."""
    with pytest.raises(InvalidParameterError, match="manquant"):
        execute(StubModel(), _entrees(), ModelParameters(values={"poids": 2.0}), seed=1)


def test_un_parametre_inconnu_est_refuse():
    """Un paramètre que le modèle n'attend pas est un paramètre inconnu."""
    with pytest.raises(InvalidParameterError, match="inconnu"):
        execute(
            StubModel(),
            _entrees(),
            ModelParameters(values={"poids": 2.0, "offset": 1.0, "prime": 3.0}),
            seed=1,
        )


def test_modifier_un_parametre_change_l_empreinte_de_configuration():
    """Un paramètre différent produit une configuration différente."""
    base = execute(StubModel(), _entrees(), _parametres(), seed=1)
    modifie = execute(
        StubModel(),
        _entrees(),
        ModelParameters(values={"poids": 2.5, "offset": 1.0}),
        seed=1,
    )

    assert base.config.fingerprint() != modifie.config.fingerprint()


def test_un_modele_sans_domaine_declare_n_est_pas_contraint():
    """Sans `required_parameters`, le runner ne devine rien et laisse le modèle valider."""
    issue = execute(StochasticModel(), _entrees(), ModelParameters(values={"libre": 1.0}), seed=3)

    assert issue.result.outputs["tirage"]


def test_une_serie_vide_est_refusee():
    """Une série vide ne dit rien : elle n'est pas une série."""
    with pytest.raises(InvalidInputError, match="vide"):
        execute(StubModel(), ModelInputs(series={"mesures": ()}), _parametres(), seed=1)


def test_une_serie_contenant_nan_est_refusee():
    """Un `NaN` n'est pas une mesure : il n'est pas remplacé par une valeur de repli."""
    with pytest.raises(InvalidInputError, match="pas finie"):
        execute(
            StubModel(),
            ModelInputs(series={"mesures": (1.0, float("nan"))}),
            _parametres(),
            seed=1,
        )


def test_une_serie_contenant_l_infini_est_refusee():
    """Un infini n'est pas une mesure non plus."""
    with pytest.raises(InvalidInputError, match="pas finie"):
        execute(
            StubModel(),
            ModelInputs(series={"mesures": (1.0, float("inf"))}),
            _parametres(),
            seed=1,
        )


def test_l_erreur_du_modele_remonte_intacte():
    """Une erreur de modèle n'est ni rattrapée, ni transformée, ni remplacée."""
    with pytest.raises(ValueError, match="échec contrôlé"):
        execute(FailingModel(), _entrees(), _parametres(), seed=1)


def test_reproduce_rend_le_meme_resultat_et_ne_change_pas_l_empreinte():
    """Rejouer une configuration rend le même résultat et n'altère pas l'empreinte."""
    model = StubModel()
    inputs = _entrees()
    params = _parametres()
    issue = execute(model, inputs, params, seed=11)
    empreinte_avant = issue.config.fingerprint()

    rejoue = reproduce(model, inputs, params, issue.config)

    assert rejoue.outputs == issue.result.outputs
    assert issue.config.fingerprint() == empreinte_avant


def test_reproduce_refuse_un_modele_qui_ne_correspond_plus():
    """Un changement de modèle est nommé, pas toléré."""
    model = StubModel()
    inputs = _entrees()
    params = _parametres()
    issue = execute(model, inputs, params, seed=11)
    config_etrange = replace(issue.config, model_id="autre_modele")

    with pytest.raises(ConfigurationMismatchError, match="autre_modele"):
        reproduce(model, inputs, params, config_etrange)


def test_reproduce_refuse_des_parametres_qui_ne_correspondent_plus():
    """Des paramètres différents de ceux de la configuration sont nommés."""
    model = StubModel()
    inputs = _entrees()
    params = _parametres()
    issue = execute(model, inputs, params, seed=11)
    config_etrange = replace(
        issue.config, parameters=ModelParameters(values={"poids": 9.0, "offset": 1.0})
    )

    with pytest.raises(ConfigurationMismatchError, match="paramètres"):
        reproduce(model, inputs, params, config_etrange)


def test_reproduce_refuse_des_entrees_qui_ne_correspondent_plus():
    """Des entrées différentes de celles de la configuration sont nommées."""
    model = StubModel()
    inputs = _entrees()
    params = _parametres()
    issue = execute(model, inputs, params, seed=11)
    config_etrange = replace(issue.config, inputs_fingerprint="0" * 64)

    with pytest.raises(ConfigurationMismatchError, match="entrées"):
        reproduce(model, inputs, params, config_etrange)


def test_la_graine_commande_le_resultat_stochastique():
    """Même graine, même résultat ; autre graine, autre résultat."""
    model = StochasticModel()
    inputs = _entrees()
    params = ModelParameters(values={})

    premier = execute(model, inputs, params, seed=1234).result.outputs
    meme_graine = execute(model, inputs, params, seed=1234).result.outputs
    autre_graine = execute(model, inputs, params, seed=4321).result.outputs

    assert premier == meme_graine
    assert premier != autre_graine


def test_le_runner_ne_touche_pas_l_etat_aleatoire_global():
    """Le runner ne tire aucun nombre : l'état global de la machine reste intact."""
    etat_numpy = _etat_numpy()
    etat_python = random.getstate()

    execute(StochasticModel(), _entrees(), ModelParameters(values={}), seed=5)

    assert _etat_numpy() == etat_numpy
    assert random.getstate() == etat_python


def test_library_versions_expose_le_python_et_torne():
    """Les versions des bibliothèques sont des chaînes, et couvrent le minimum attendu."""
    versions = library_versions()

    assert "python" in versions
    assert "numpy" in versions
    assert "torne" in versions
    assert all(isinstance(version, str) for version in versions.values())


def test_reproduce_refuse_un_environnement_deplace():
    """Deux exécutions sous des versions différentes ne sont pas la même exécution.

    La reproduction doit être **exacte** ou refusée : rejouer sous un environnement
    déplacé et le présenter comme une reproduction silencieuse serait un mensonge.
    """
    outcome = execute(StubModel(), _entrees(), _parametres())
    config_deplace = replace(
        outcome.config,
        library_versions={**outcome.config.library_versions, "numpy": "0.0.0-inventée"},
    )

    with pytest.raises(ConfigurationMismatchError, match="environnement"):
        reproduce(StubModel(), _entrees(), _parametres(), config_deplace)


def test_reproduce_accepte_un_environnement_deplace_si_le_caller_le_demande():
    """Mesurer l'effet d'un changement d'environnement est une question légitime.

    Elle doit être explicite, jamais le comportement par défaut.
    """
    outcome = execute(StubModel(), _entrees(), _parametres())
    config_deplace = replace(
        outcome.config,
        library_versions={**outcome.config.library_versions, "numpy": "0.0.0-inventée"},
    )

    resultat = reproduce(
        StubModel(), _entrees(), _parametres(), config_deplace, strict_environment=False
    )

    assert resultat.outputs == outcome.result.outputs


def test_un_parametre_optionnel_est_accepte_mais_jamais_exige():
    """Un paramètre optionnel ne bloque pas l'exécution quand il est absent."""
    sans_optionnel = execute(ModelAvecParametresOptionnels(), _entrees(), _parametres())
    avec_optionnel = execute(
        ModelAvecParametresOptionnels(),
        _entrees(),
        ModelParameters(values={**_parametres().values, "amplitude": 2.0}),
    )

    assert (
        sans_optionnel.config.parameters.fingerprint()
        != avec_optionnel.config.parameters.fingerprint()
    )
    assert avec_optionnel.result.outputs["moyenne"] == sans_optionnel.result.outputs["moyenne"]


def test_un_parametre_hors_domaine_du_modele_est_refuse():
    """Un nom que le modèle ne déclare ni comme requis ni comme optionnel est inconnu."""
    with pytest.raises(InvalidParameterError, match="inconnu"):
        execute(
            ModelAvecParametresOptionnels(),
            _entrees(),
            ModelParameters(values={**_parametres().values, "inexistant": 1.0}),
        )
