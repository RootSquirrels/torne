"""Adaptateur Hub'EAU v2 — observations hydrométriques.

Cet adaptateur **pose des questions** à Hub'EAU et ne sait rien du
domaine : il ne connaît ni la hauteur d'eau, ni le débit, ni la notion de
série temporelle. Il construit une URL, dit comment la source se parcourt, et
rend la page suivante ou `None`.

Ce qui a été **vérifié sur le réseau** (2026-10-31, poste de
développement) :

- la réponse est un objet JSON
  `{"count", "first", "prev", "next", "api_version", "data"}`, et `data`
  porte les observations de la page ;
- la pagination effective est **par curseur** : `next` est une URL absolue
  portant un paramètre `cursor`, et `cursor` fait réellement avancer la page.
  Le paramètre `page` est accepté mais **ignoré** : la page demandée avec
  `page=2` est exactement celle de `page=1`. L'adaptateur suit donc le lien
  `next`, qui est le seul mécanisme qui fonctionne ;
- `size` est honoré, et `count` donne le nombre d'observations
  correspondant à la requête ;
- les filtres `code_station`, `code_cours_eau`, `date_debut` et `date_fin`
  sont acceptés par le serveur et renvoyés dans les liens `first`/`next`,
  mais **sur ce point d'accès seul `grandeur_hydro` et le curseur
  restreignent effectivement le résultat**. C'est une limite de l'instance
  observée, consignée ici pour que personne ne croie l'avoir vérifié à la
  place de quelqu'un d'autre ; l'adaptateur envoie malgré tout les filtres
  documentés, qui sont ceux de l'API publique.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from ...contracts.observation import Source
from ..contracts import AcquisitionRequest, HttpResponse, PaginationStrategy

URL_OBSERVATIONS_TR = "https://hubeau.eaufrance.fr/api/v2/hydrometrie/observations_tr"
"""Point d'accès Hub'EAU v2 des observations hydrométriques (temps réel)."""

SOURCE_ID = "hubeau.hydrometrie.observations_tr"
"""Identifiant de la source, stable et sans ambiguïté."""


class HubeauObservationsAdapter:
    """Les questions à poser à Hub'EAU sur les observations hydrométriques.

    Les paramètres sont explicites : rien n'est deviné. Le lecteur de
    l'instant refuse un instant sans fuseau (INV-15), et le format de date
    est l'ISO 8601 UTC — c'est le format que le point d'accès honorait lors
    de la vérification.
    """

    def __init__(
        self,
        *,
        code_station: Sequence[str],
        page_size: int,
        max_pages: int,
        code_cours_eau: Sequence[str] = (),
        date_debut: datetime | None = None,
        date_fin: datetime | None = None,
        grandeur_hydro: str | None = None,
    ) -> None:
        """Fixe la question à poser.

        `code_station` est obligatoire : une acquisition sans station
        ramènerait l'intégralité du référentiel hydrométrique national.
        `page_size` et `max_pages` n'ont pas de valeur par défaut : la taille
        de page et la profondeur de parcours sont des choix, pas des
        conventions.
        """
        if not code_station:
            raise ValueError("code_station est obligatoire : une station au moins")
        if page_size < 1:
            raise ValueError("page_size doit valoir au moins 1")
        if max_pages < 1:
            raise ValueError("max_pages doit valoir au moins 1")
        for instant, nom in ((date_debut, "date_debut"), (date_fin, "date_fin")):
            if instant is not None and not isinstance(instant, datetime):
                raise TypeError(f"{nom} doit être un instant")
            if instant is not None and instant.tzinfo is None:
                raise ValueError(f"{nom} : un instant sans fuseau est refusé (INV-15)")

        self._code_station = tuple(code_station)
        self._code_cours_eau = tuple(code_cours_eau)
        self._date_debut = date_debut
        self._date_fin = date_fin
        self._grandeur_hydro = grandeur_hydro
        self._page_size = page_size
        self._max_pages = max_pages

    @property
    def source(self) -> Source:
        """La source interrogée : l'origine, et ses conditions d'usage."""
        return Source(
            source_id=SOURCE_ID,
            producer="Eaufrance (Hub'EAU)",
            dataset="Observations hydrométriques (hauteur d'eau et débit)",
            access_point=URL_OBSERVATIONS_TR,
            license="Licence Ouverte / Open Licence 2.0 (Etalab)",
            revision_policy=(
                "Chaque relevé porte son propre statut de mesure et de qualification "
                "(libelle_statut, libelle_qualification_obs)"
            ),
            unit=None,
            timezone="UTC",
            quality_status=None,
        )

    @property
    def declares_exhaustion(self) -> bool:
        """Cette source **déclare** l'épuisement de son parcours.

        La pagination est portée par le lien `next` : quand il disparaît, le
        fournisseur dit lui-même qu'il n'y a plus rien à prendre. Une
        réponse 200 signifie donc ici « le parcours est terminé », et non
        « j'ai rendu tout ce que j'avais » : c'est une déclaration, et le
        socle peut la consigner comme telle.
        """
        return True

    def initial_request(self) -> AcquisitionRequest:
        """La première question : la première page, avec les filtres choisis."""
        return AcquisitionRequest(
            source_id=SOURCE_ID,
            url=URL_OBSERVATIONS_TR,
            method="GET",
            params=self._params_filtres(),
            pagination=PaginationStrategy.CURSOR,
            max_pages=self._max_pages,
            label="hubeau:observations_tr",
        )

    def next_request(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> AcquisitionRequest | None:
        """La question suivante, ou `None` quand il n'y en a plus.

        La pagination de cette source est portée par le lien `next` : on le
        suit tel que le fournisseur l'a donné. La pagination est épuisée
        quand la page est vide, ou quand le fournisseur ne donne plus de lien
        suivant.

        Le **budget** de pages n'est pas porté par cet adaptateur : c'est au
        socle de l'arrêter, qui en fera une acquisition `partial` — et non une
        acquisition complète. Un adaptateur qui s'arrêterait lui-même ne
        pourrait plus distinguer « la source est épuisée » de « le parcours a
        été tronqué », et les deux doivent être rapportés différemment.
        """
        donnees, suivant = self._lire_page(response)
        if not donnees:
            return None
        if suivant is None:
            return None

        url, params = _decouper_url(suivant)
        if url != URL_OBSERVATIONS_TR:
            raise ValueError(f"le lien suivant pointe ailleurs que le point d'accès : {url}")
        return AcquisitionRequest(
            source_id=request.source_id,
            url=url,
            method="GET",
            params=params,
            pagination=PaginationStrategy.CURSOR,
            max_pages=self._max_pages,
            label=request.label,
        )

    def _params_filtres(self) -> dict[str, str]:
        """Les paramètres de requête, portés par la demande et rien d'autre."""
        params: dict[str, str] = {"size": str(self._page_size)}
        if self._code_station:
            params["code_station"] = ",".join(self._code_station)
        if self._code_cours_eau:
            params["code_cours_eau"] = ",".join(self._code_cours_eau)
        if self._date_debut is not None:
            params["date_debut"] = _iso_utc(self._date_debut)
        if self._date_fin is not None:
            params["date_fin"] = _iso_utc(self._date_fin)
        if self._grandeur_hydro:
            params["grandeur_hydro"] = self._grandeur_hydro
        return params

    def _lire_page(self, response: HttpResponse) -> tuple[list[Any], str | None]:
        """Les observations de la page, et le lien vers la page suivante."""
        charge = _charger_json(response, "Hub'EAU")
        donnees = charge.get("data")
        if not isinstance(donnees, list):
            raise ValueError("réponse Hub'EAU inattendue : le champ « data » n'est pas une liste")
        suivant = charge.get("next")
        if suivant is not None and not isinstance(suivant, str):
            raise ValueError("réponse Hub'EAU inattendue : le champ « next » n'est pas une URL")
        return donnees, suivant


def _iso_utc(instant: datetime) -> str:
    """L'instant en ISO 8601 UTC, le format honoré par le point d'accès."""
    return instant.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _charger_json(response: HttpResponse, nom: str) -> dict[str, Any]:
    """Le corps de la réponse, lu comme un objet JSON."""
    try:
        charge = json.loads(response.body)
    except (json.JSONDecodeError, UnicodeDecodeError) as erreur:
        raise ValueError(f"réponse {nom} illisible : {erreur}") from erreur
    if not isinstance(charge, dict):
        raise ValueError(f"réponse {nom} inattendue : la racine n'est pas un objet JSON")
    return charge


def _decouper_url(url: str) -> tuple[str, dict[str, str]]:
    """Découpe une URL absolue en base et paramètres.

    Le lien du fournisseur est réécrit en base + paramètres : les paramètres
    restent portés par la demande, jamais concaténés à la main dans l'URL.
    """
    morceaux = urlsplit(url)
    base = urlunsplit((morceaux.scheme, morceaux.netloc, morceaux.path, "", ""))
    params = dict(parse_qsl(morceaux.query, keep_blank_values=True))
    return base, params


__all__ = ["SOURCE_ID", "URL_OBSERVATIONS_TR", "HubeauObservationsAdapter"]
