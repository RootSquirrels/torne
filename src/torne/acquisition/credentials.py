"""Les secrets : une **référence**, jamais une valeur.

Le socle ne dit pas comment un secret est stocké (INV-41) : il dit seulement
qu'il **sort au dernier moment** et qu'il ne revient jamais dans un objet
consigné. Ce module est une manière de faire, pas la manière : un secret peut
vivre dans l'environnement, dans un fichier local ignoré par Git, dans un
gestionnaire de secrets — tant qu'il n'est écrit nulle part dans le dépôt et
n'entre dans aucune demande consignée.

Ce que ce module garantit :

- la demande d'acquisition porte une **référence** (`credential_ref`) — un
  nom, comme ``meteofrance.oauth2`` — et jamais la valeur ;
- la valeur n'est lue qu'au moment de l'envoi, et n'est renvoyée que si la
  référence demandée est bien celle que ce fournisseur connaît ;
- une référence inconnue ne reçoit **rien** : un fournisseur ne peut pas
  passer le jeton d'un autre fournisseur à une autre origine.

Ce que ce module ne garantit pas, et que le transport garantit ailleurs :
un identifiant ne franchit pas une origine (INV-42). Une redirection vers un
autre serveur voit ses en-têtes d'authentification retirés par le transport,
pas par ce module.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path


class EnvironmentToken:
    """Un secret lu dans l'environnement, sous un nom, et rendu au dernier moment.

    Le fournisseur de démonstration de `experiments/mission_002_real_world.py`
    lit la clé USGS de la même façon : c'est le motif du dépôt, et non une
    Lubie de ce module.

    `credential_ref` est le **nom** sous lequel la demande réclame le secret.
    Il est celui qui est consigné dans le journal — jamais la valeur.
    """

    def __init__(
        self,
        credential_ref: str,
        *,
        variable: str,
        header: str = "Authorization",
        scheme: str = "Bearer",
    ) -> None:
        if not credential_ref.strip():
            raise ValueError("credential_ref est obligatoire et non vide")
        if not variable.strip():
            raise ValueError("variable est obligatoire et non vide")
        self._credential_ref = credential_ref
        self._variable = variable
        self._header = header
        self._scheme = scheme

    @property
    def variable(self) -> str:
        """Le nom de la variable d'environnement — un nom, pas un secret."""
        return self._variable

    def credentials_for(self, credential_ref: str) -> Mapping[str, str]:
        """L'en-tête d'authentification, si cette référence est la nôtre."""
        if credential_ref != self._credential_ref:
            return {}
        valeur = os.environ.get(self._variable, "").strip()
        if not valeur:
            return {}
        if self._scheme:
            return {self._header: f"{self._scheme} {valeur}"}
        return {self._header: valeur}


def lire_fichier_env(chemin: Path) -> dict[str, str]:
    """Lit un fichier `.env` minimal : `CLE=valeur`, une par ligne.

    Le format est volontairement réduit — pas d'export`, pas d'interpolation,
    pas de guillemets échappés. Un secret n'a pas besoin d'un langage : il a
    besoin d'être **illisible par le dépôt**, et le dépôt l'ignore.

    Les lignes vides et celles qui commencent par `#` sont ignorées ; une
    ligne sans `=` est ignorée ; la valeur est prise telle quelle, sans
    guillemets, et **jamais journalisée**.
    """
    valeurs: dict[str, str] = {}
    if not chemin.is_file():
        return valeurs
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        propre = ligne.strip()
        if not propre or propre.startswith("#") or "=" not in propre:
            continue
        cle, _, valeur = propre.partition("=")
        valeurs[cle.strip()] = valeur.strip().strip('"').strip("'")
    return valeurs


class FichierEnvToken(EnvironmentToken):
    """Un secret lu dans l'environnement, puis dans un fichier local ignoré.

    L'ordre est délibéré : **l'environnement gagne**. Un fichier local est un
    commodité pour la machine de travail ; une variable d'environnement est
    un choix explicite, et elle prime.
    """

    def __init__(
        self,
        credential_ref: str,
        *,
        variable: str,
        chemin: Path,
        header: str = "Authorization",
        scheme: str = "Bearer",
    ) -> None:
        super().__init__(credential_ref, variable=variable, header=header, scheme=scheme)
        self._chemin = chemin

    def credentials_for(self, credential_ref: str) -> Mapping[str, str]:
        if credential_ref != self._credential_ref:
            return {}
        valeur = os.environ.get(self._variable, "").strip()
        if not valeur:
            valeur = lire_fichier_env(self._chemin).get(self._variable, "").strip()
        if not valeur:
            return {}
        if self._scheme:
            return {self._header: f"{self._scheme} {valeur}"}
        return {self._header: valeur}


__all__ = [
    "EnvironmentToken",
    "FichierEnvToken",
    "lire_fichier_env",
]
