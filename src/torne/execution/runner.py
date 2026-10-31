"""Exécution d'un modèle : valider, configurer, exécuter, restituer.

Ce module est le maillon « exécution » de la chaîne
`preuve → observation → exécution → résultat → évaluation → enregistrement`.
Il ne fait rien d'autre : ni service, ni registre, ni moteur, ni bus. C'est une
fonction, et elle reste une fonction.

Trois règles structurantes, toutes vérifiables :

1. **Aucune erreur masquée.** Les exceptions du modèle remontent intactes. Le
   runner ne fabrique jamais de résultat par défaut, ne rattrape rien, ne
   remplace rien par une valeur nulle : un échec reste un échec, et il est
   visible. Un résultat inexploitable — sortie non finie, ou résultat qui
   n'est pas celui du modèle exécuté — est de même refusé et jamais rendu :
   une défaillance ne passe pas pour un résultat.
2. **Aucun état global caché.** La graine est transmise au modèle, qui fabrique
   son propre générateur (`numpy.random.default_rng(seed)`). Le runner n'appelle
   jamais `random.seed()` ni `numpy.random.seed()` : l'état aléatoire global de
   la machine n'appartient pas à une exécution, et une exécution ne doit pas
   pouvoir en dépendre par accident.
3. **La configuration ne porte pas le temps.** `ExecutionConfig` décrit ce qui
   détermine le résultat (modèle, version, graine, paramètres, empreinte des
   entrées, versions de bibliothèques) ; les instants de début et de fin vivent
   dans `ExecutionOutcome`. C'est cette séparation qui rend l'empreinte de
   configuration **stable d'une exécution à l'autre**, donc la reproduction
   vérifiable : deux exécutions de la même chose ont la même empreinte, quel que
   soit le jour où elles ont eu lieu.

Le temps de la reproduction est donc explicite : `reproduce` ne rejoue pas « ce
qui s'est passé un jour », mais « ce que la configuration décrit ».
"""

from __future__ import annotations

import math
import platform
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import metadata

from ..contracts.model import (
    ExecutionConfig,
    Model,
    ModelInputs,
    ModelParameters,
    ModelResult,
)
from ..contracts.time import to_utc
from .errors import (
    ConfigurationMismatchError,
    InvalidInputError,
    InvalidParameterError,
    InvalidResultError,
)

_VERSION_INCONNUE = "inconnue"


@dataclass(frozen=True, slots=True)
class ExecutionOutcome:
    """Ce qu'une exécution produit : le résultat, sa configuration et son temps.

    Les deux horodatages sont des **métadonnées d'exécution**, pas des
    données de configuration : ils décrivent quand l'exécution a eu lieu, pas
    ce qui la détermine. Ils sont donc hors de `ExecutionConfig`, dont
    l'empreinte reste stable.
    """

    result: ModelResult
    config: ExecutionConfig
    started_at: datetime
    ended_at: datetime

    @property
    def duration_seconds(self) -> float:
        """Durée de l'exécution, en secondes."""
        return (self.ended_at - self.started_at).total_seconds()


def _version_distr(distribution: str) -> str:
    """Renvoie la version d'un paquet installé, ou « inconnue » s'il est absent.

    L'absence d'un paquet n'est pas une erreur : elle est signalée comme telle
    plutôt que plaquée sur une valeur inventée.
    """
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return _VERSION_INCONNUE


def library_versions() -> dict[str, str]:
    """Renvoie les versions des bibliothèques qui déterminent le résultat.

    L'environnement fait partie de la reproduction : deux exécutions sous des
    versions différentes ne sont pas la même exécution, et le dire fait partie
    de la traçabilité. Le paquet absent est signalé comme « inconnue », jamais
    omis.
    """
    return {
        "python": platform.python_version(),
        "numpy": _version_distr("numpy"),
        "torne": _version_distr("torne"),
    }


def _instant(now: datetime | None) -> datetime:
    """Renvoie l'instant UTC courant, ou l'instant injecté par l'appelant.

    Un instant injecté sans fuseau est refusé (INV-15) : la convention
    temporelle du dépôt vaut aussi pour l'horloge d'un test.
    """
    if now is None:
        return datetime.now(UTC)
    return to_utc(now, name="now")


def _valider_entrees(inputs: ModelInputs) -> None:
    """Vérifie que chaque série est non vide et entièrement finie.

    Une série vide n'est pas une série : elle ne dit rien. Un `NaN` ou un
    infini n'est pas une mesure : il ne peut pas être moyenné, interpolé ni
    propagé. Ni l'un ni l'autre n'est remplacé par une valeur de repli : une
    absence se qualifie, elle ne se comble pas.
    """
    for nom, valeurs in inputs.series.items():
        if not valeurs:
            raise InvalidInputError(f"entrée « {nom} » : la série est vide")
        for indice, valeur in enumerate(valeurs):
            try:
                finie = math.isfinite(valeur)
            except TypeError as exc:
                raise InvalidInputError(
                    f"entrée « {nom} » : la valeur à l'indice {indice} n'est pas un nombre"
                ) from exc
            if not finie:
                raise InvalidInputError(
                    f"entrée « {nom} » : la valeur à l'indice {indice} n'est pas finie ({valeur!r})"
                )


def _valider_parametres(model: Model, params: ModelParameters) -> None:
    """Confronte les paramètres fournis au domaine déclaré par le modèle.

    Un modèle qui expose `required_parameters` y déclare les paramètres sans
    lesquels il ne peut pas s'exécuter : un paramètre manquant est absent. S'il
    expose aussi `optional_parameters`, ceux-là sont acceptés **s'ils sont
    fournis** et leur valeur par défaut s'applique sinon. Tout autre nom est
    inconnu.

    Un modèle qui n'expose pas `required_parameters` n'est pas contraint : le
    runner ne devine pas son domaine et le laisse valider lui-même.
    """
    declares = getattr(model, "required_parameters", None)
    if declares is None:
        return
    requis = tuple(str(nom) for nom in declares)
    optionnels = tuple(str(nom) for nom in getattr(model, "optional_parameters", ()) or ())
    fournis = set(params.values)
    manquants = sorted(nom for nom in requis if nom not in fournis)
    if manquants:
        raise InvalidParameterError(
            f"modèle « {model.spec.model_id} » : paramètre(s) manquant(s) — {', '.join(manquants)}"
        )
    inconnus = sorted(fournis - set(requis) - set(optionnels))
    if inconnus:
        raise InvalidParameterError(
            f"modèle « {model.spec.model_id} » : paramètre(s) inconnu(s) — {', '.join(inconnus)}"
        )


def _valider_resultat(model: Model, result: object) -> ModelResult:
    """Vérifie que le résultat rendu est bien celui du modèle exécuté, et qu'il est fini.

    Deux défaillances ne doivent jamais passer pour un résultat :

    - un **résultat non fini** — une sortie ou une borne d'intervalle `NaN` ou
      infinie n'est pas une mesure, et la rendre comme telle fabriquerait un
      résultat à partir d'un échec ;
    - un **résultat qui ne vient pas du modèle exécuté** — la configuration
      annonce le modèle et sa version ; si le résultat en annonce un autre,
      la configuration ment sur ce qui a été exécuté, et la reproduction ne
      rejouerait pas la même chose.

    Les diagnostics ne sont pas contrôlés : une vraisemblance dégénérée peut
    légitimement valoir `-inf`. Seuls les **résultats** doivent être finis.
    """
    if not isinstance(result, ModelResult):
        raise InvalidResultError(
            f"le modèle « {model.spec.model_id} » n'a pas renvoyé un ModelResult "
            f"(reçu {type(result).__name__})"
        )

    if result.spec.model_id != model.spec.model_id or result.spec.version != model.spec.version:
        raise ConfigurationMismatchError(
            f"le résultat annonce le modèle « {result.spec.model_id} » version "
            f"« {result.spec.version} », le modèle exécuté est « {model.spec.model_id} » "
            f"version « {model.spec.version} »"
        )

    for nom, valeurs in result.outputs.items():
        for indice, valeur in enumerate(valeurs):
            if not _est_fini(valeur):
                raise InvalidResultError(
                    f"sortie « {nom} » : la valeur à l'indice {indice} n'est pas finie ({valeur!r})"
                )

    for nom, paires in result.intervals.items():
        for indice, paire in enumerate(paires):
            for position, borne in enumerate(paire):
                if not _est_fini(borne):
                    raise InvalidResultError(
                        f"intervalle « {nom} » : la borne {position} de l'intervalle "
                        f"{indice} n'est pas finie ({borne!r})"
                    )

    return result


def _est_fini(valeur: object) -> bool:
    """Dit si une valeur est un nombre fini ; une valeur qui n'est pas un nombre ne l'est pas."""
    try:
        return math.isfinite(valeur)
    except TypeError:
        return False


def execute(
    model: Model,
    inputs: ModelInputs,
    params: ModelParameters,
    *,
    seed: int | None = None,
    now: datetime | None = None,
) -> ExecutionOutcome:
    """Exécute `model` sur `inputs` avec `params`, et rend l'issue complète.

    La séquence est : validation des entrées, validation des paramètres,
    construction de la configuration, appel du modèle, **validation du
    résultat**, horodatage. Les erreurs du modèle ne sont pas rattrapées :
    elles remontent intactes, et rien n'est rendu à la place.

    Un résultat inexploitable — sortie non finie, ou résultat qui n'est pas
    celui du modèle exécuté — n'est pas rendu non plus : il est refusé par
    `InvalidResultError` ou `ConfigurationMismatchError`, pour qu'une
    défaillance ne passe jamais pour un résultat.

    `seed` est transmise au modèle telle quelle : le runner ne tire aucun
    nombre aléatoire et ne touche pas à l'état aléatoire global.

    `now` injecte l'horloge : les deux horodatages de l'issue valent alors cet
    instant. Il n'existe que pour les tests ; sans lui, l'horloge du système est
    utilisée.
    """
    _valider_entrees(inputs)
    _valider_parametres(model, params)

    config = ExecutionConfig(
        model_id=model.spec.model_id,
        model_version=model.spec.version,
        seed=seed,
        parameters=params,
        inputs_fingerprint=inputs.fingerprint(),
        library_versions=library_versions(),
    )

    started_at = _instant(now)
    result = _valider_resultat(model, model.run(inputs, params, seed=seed))
    ended_at = _instant(now)

    return ExecutionOutcome(
        result=result,
        config=config,
        started_at=started_at,
        ended_at=ended_at,
    )


def _verifier_modele(model: Model, config: ExecutionConfig) -> None:
    """Vérifie que la configuration décrit bien le modèle courant."""
    if config.model_id != model.spec.model_id:
        raise ConfigurationMismatchError(
            f"modèle attendu « {config.model_id} », modèle courant « {model.spec.model_id} »"
        )
    if config.model_version != model.spec.version:
        raise ConfigurationMismatchError(
            f"version de modèle attendue « {config.model_version} », "
            f"version courante « {model.spec.version} »"
        )


def _verifier_parametres(params: ModelParameters, config: ExecutionConfig) -> None:
    """Vérifie que les paramètres fournis sont ceux de la configuration."""
    attendu = config.parameters.fingerprint()
    fourni = params.fingerprint()
    if attendu != fourni:
        raise ConfigurationMismatchError(
            f"empreinte des paramètres : configuration « {attendu} », "
            f"paramètres fournis « {fourni} »"
        )


def _verifier_entrees(inputs: ModelInputs, config: ExecutionConfig) -> None:
    """Vérifie que les entrées fournies sont celles de la configuration."""
    fourni = inputs.fingerprint()
    if config.inputs_fingerprint != fourni:
        raise ConfigurationMismatchError(
            f"empreinte des entrées : configuration « {config.inputs_fingerprint} », "
            f"entrées fournies « {fourni} »"
        )


def _verifier_environnement(config: ExecutionConfig) -> None:
    """Vérifie que l'environnement courant est celui de l'exécution d'origine.

    Deux exécutions sous des versions de bibliothèques différentes ne sont pas
    la même exécution. La configuration conserve les versions utilisées ; si
    elles ont bougé, la reproduction ne serait pas exacte, et le fait doit être
    dit plutôt que passé sous silence.
    """
    actuel = library_versions()
    ecarts = sorted(
        nom for nom, version in config.library_versions.items() if actuel.get(nom) != version
    )
    if ecarts:
        detail = ", ".join(
            f"{nom} (enregistré « {config.library_versions[nom]} », "
            f"actuel « {actuel.get(nom, _VERSION_INCONNUE)} »)"
            for nom in ecarts
        )
        raise ConfigurationMismatchError(f"environnement de reproduction différent : {detail}")


def reproduce(
    model: Model,
    inputs: ModelInputs,
    params: ModelParameters,
    config: ExecutionConfig,
    *,
    strict_environment: bool = True,
) -> ModelResult:
    """Rejoue l'exécution décrite par `config` et rend son résultat.

    La configuration est confrontée au modèle courant, aux paramètres fournis
    et aux entrées fournies : au premier écart, `ConfigurationMismatchError` dit
    précisément ce qui diffère. La relecture ne masque rien non plus : une
    erreur du modèle remonte intacte, et un résultat par défaut n'est jamais
    produit à sa place.

    La graine rejouée est celle de la configuration : c'est elle qui rend le
    résultat reproductible, et elle seule.

    `strict_environment` (vrai par défaut) refuse en outre de rejouer sous des
    versions de bibliothèques différentes de celles enregistrées : la
    reproduction serait alors approchée, pas exacte. Le poser à faux permet de
    mesurer l'effet d'un changement d'environnement — question légitime, mais
    qui ne doit pas être la norme.
    """
    _verifier_modele(model, config)
    _verifier_parametres(params, config)
    _verifier_entrees(inputs, config)
    if strict_environment:
        _verifier_environnement(config)
    return execute(model, inputs, params, seed=config.seed).result


__all__ = ["ExecutionOutcome", "execute", "library_versions", "reproduce"]
