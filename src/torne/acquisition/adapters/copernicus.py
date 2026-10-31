"""Adaptateur Copernicus Data Space — catalogue des produits.

Cet adaptateur **pose des questions** au catalogue OData de Copernicus et ne
sait rien du domaine : il ne connaît ni Sentinel, ni Sentinel-2, ni la
surface d'un produit. Il construit une URL, pose un filtre, dit comment le
catalogue se parcourt, et rend la question suivante ou `None`.

Ce qui a été **vérifié sur le réseau** (2026-10-31, poste de
développement) :

- le point d'accès est une API **OData v4** : la réponse porte les
  produits sous `value`, et l'indicateur `@odata.nextLink` donne l'URL de la
  page suivante ;
- la pagination est portée par `$top` (taille de page) et `$skip` (décalage),
  et le filtre par `$filter` : les trois sont acceptés et appliqués ;
- le lien de page suivante est une URL **absolue**, dont les paramètres sont
  encodés (`%24top`, `%24filter`, `%24skip`) : l'adaptateur le décode et
  reporte ses paramètres dans la demande suivante, pour que les paramètres
  restent toujours portés par la demande et jamais concaténés à la main ;
- le catalogue ne publie pas de licence par produit : les conditions
  d'usage sont donc portées par la source, pas par le produit.
"""

from __future__ import annotations

import json
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from ...contracts.observation import Source
from ..contracts import AcquisitionRequest, HttpResponse, PaginationStrategy

URL_PRODUCTS = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
"""Point d'accès OData du catalogue Copernicus Data Space."""

SOURCE_ID = "copernicus.dataspace.products"
"""Identifiant de la source, stable et sans ambiguïté."""


class CopernicusProductsAdapter:
    """Les questions à poser au catalogue Copernicus Data Space.

    Le filtre est une expression OData, écrite par l'appelant : l'adaptateur
    ne la comprend pas, il la transmet. Elle est écrite en syntaxe
    OData (`startswith(Name,'Sentinel-2')`), et non en Python.
    """

    def __init__(
        self,
        *,
        filter_expression: str,
        page_size: int,
        max_pages: int,
        order_by: str | None = None,
    ) -> None:
        """Fixe la question à poser.

        `filter_expression`, `page_size` et `max_pages` n'ont pas de valeur
        par défaut : un filtre absent ramènerait le catalogue entier, et la
        taille de page comme la profondeur sont des choix, pas des
        conventions.
        """
        if not isinstance(filter_expression, str) or not filter_expression.strip():
            raise ValueError("filter_expression est obligatoire et non vide")
        if page_size < 1:
            raise ValueError("page_size doit valoir au moins 1")
        if max_pages < 1:
            raise ValueError("max_pages doit valoir au moins 1")

        self._filtre = filter_expression
        self._page_size = page_size
        self._max_pages = max_pages
        self._order_by = order_by

    @property
    def source(self) -> Source:
        """La source interrogée : l'origine, et ses conditions d'usage."""
        return Source(
            source_id=SOURCE_ID,
            producer="European Space Agency — Copernicus Data Space Ecosystem",
            dataset="Catalogue des produits (OData)",
            access_point=URL_PRODUCTS,
            license=(
                "Accès gratuit ; la licence est propre à chaque produit et n'est pas "
                "publiée par le catalogue"
            ),
            revision_policy=(
                "Chaque produit porte ses dates d'origine, de publication et de "
                "modification (OriginDate, PublicationDate, ModificationDate)"
            ),
            unit=None,
            timezone="UTC",
            quality_status=None,
        )

    @property
    def declares_exhaustion(self) -> bool:
        """Cette source **déclare** l'épuisement de son parcours.

        Le catalogue indique lui-même la page suivante par `@odata.nextLink` :
        quand ce lien disparaît, il dit qu'il n'a plus rien à donner. Une
        réponse 200 signifie donc ici « le parcours est terminé », et non
        « j'ai rendu tout ce que j'avais » : c'est une déclaration, et le
        socle peut la consigner comme telle.
        """
        return True

    def initial_request(self) -> AcquisitionRequest:
        """La première question : la première page du catalogue filtré."""
        return AcquisitionRequest(
            source_id=SOURCE_ID,
            url=URL_PRODUCTS,
            method="GET",
            params=self._params_filtres(),
            pagination=PaginationStrategy.CURSOR,
            max_pages=self._max_pages,
            label="copernicus:products",
        )

    def next_request(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> AcquisitionRequest | None:
        """La question suivante, ou `None` quand il n'y en a plus.

        Le catalogue indique lui-même la page suivante par `@odata.nextLink`.
        Il n'y en a plus quand il ne donne plus de lien.

        Le **budget** de pages n'est pas porté par cet adaptateur : c'est au
        socle de l'arrêter, qui en fera une acquisition `partial` — et non une
        acquisition complète. Un adaptateur qui s'arrêterait lui-même ne
        pourrait plus distinguer « la source est épuisée » de « le parcours a
        été tronqué ».
        """
        suivant = self._lire_lien_suivant(response)
        if suivant is None:
            return None

        url, params = _decouper_url(suivant)
        if url != URL_PRODUCTS:
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
        params: dict[str, str] = {"$top": str(self._page_size), "$filter": self._filtre}
        if self._order_by:
            params["$orderby"] = self._order_by
        return params

    def _lire_lien_suivant(self, response: HttpResponse) -> str | None:
        """Le lien de page suivante donné par le catalogue, s'il y en a un."""
        try:
            charge = json.loads(response.body)
        except (json.JSONDecodeError, UnicodeDecodeError) as erreur:
            raise ValueError(f"réponse Copernicus illisible : {erreur}") from erreur
        if not isinstance(charge, dict):
            raise ValueError("réponse Copernicus inattendue : la racine n'est pas un objet JSON")
        if "value" not in charge:
            raise ValueError("réponse Copernicus inattendue : le champ « value » est absent")
        suivant = charge.get("@odata.nextLink")
        if suivant is None:
            return None
        if not isinstance(suivant, str):
            raise ValueError(
                "réponse Copernicus inattendue : « @odata.nextLink » n'est pas une URL"
            )
        return suivant


def _decouper_url(url: str) -> tuple[str, dict[str, str]]:
    """Découpe une URL absolue en base et paramètres.

    Le lien du fournisseur est réécrit en base + paramètres : les paramètres
    restent portés par la demande, jamais concaténés à la main dans l'URL.
    """
    morceaux = urlsplit(url)
    base = urlunsplit((morceaux.scheme, morceaux.netloc, morceaux.path, "", ""))
    params = dict(parse_qsl(morceaux.query, keep_blank_values=True))
    return base, params


__all__ = ["SOURCE_ID", "URL_PRODUCTS", "CopernicusProductsAdapter"]
