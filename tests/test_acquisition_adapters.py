"""Tests des adaptateurs de source — poser la question, et rien de plus.

Aucun test ne touche le réseau : chaque adaptateur est interrogé avec une
`HttpResponse` synthétique, et l'on ne regarde que la **question** qu'il pose
ensuite. C'est tout ce qu'un adaptateur sait faire.

Les réponses synthétiques reprennent la forme réellement observée sur les
points d'accès (2026-10-31) : le lien de page suivante de Hub'EAU, le
`@odata.nextLink` de Copernicus, l'enveloppe `value` du catalogue.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from torne.acquisition.adapters.copernicus import (
    URL_PRODUCTS,
    CopernicusProductsAdapter,
)
from torne.acquisition.adapters.hubeau import (
    URL_OBSERVATIONS_TR,
    HubeauObservationsAdapter,
)
from torne.acquisition.adapters.usgs import URL_IV, UsgsInstantaneousValuesAdapter
from torne.acquisition.contracts import HttpResponse, PaginationStrategy

LIEN_SUIVANT_HUBEAU = (
    "https://hubeau.eaufrance.fr/api/v2/hydrometrie/observations_tr"
    "?code_station=O919001001&cursor=AoJw%2BuT4yaEDPwpPOTE5MDAxMF9POTE5MDAxMDAxX0hf"
    "MjAyNi0xMC0zMVQyMTozNTowMA%3D%3D&size=1"
)
"""Le lien `next` observé sur Hub'EAU : c'est un curseur, pas un numéro de page."""

LIEN_SUIVANT_COPERNICUS = (
    "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
    "?%24top=1&%24filter=startswith%28Name%2C%27Sentinel-2%27%29&%24skip=1"
)
"""Le `@odata.nextLink` observé : les paramètres OData y sont encodés."""


def _reponse(charge: dict[str, object]) -> HttpResponse:
    """Une réponse HTTP synthétique, comme le transport en rendrait une."""
    return HttpResponse(
        status_code=200,
        headers={"content-type": "application/json"},
        body=json.dumps(charge).encode("utf-8"),
        url="https://exemple.test/",
    )


def _page_hubeau(*, donnees: list[dict[str, object]], suivant: str | None) -> HttpResponse:
    return _reponse(
        {"count": 41679638, "first": None, "prev": None, "next": suivant, "data": donnees}
    )


def _adaptateur_hubeau(**kwargs: object) -> HubeauObservationsAdapter:
    defauts: dict[str, object] = {
        "code_station": ["O919001001"],
        "page_size": 100,
        "max_pages": 5,
    }
    return HubeauObservationsAdapter(**{**defauts, **kwargs})


# --------------------------------------------------------------------------
# Hub'EAU
# --------------------------------------------------------------------------


def test_hubeau_la_premiere_demande_porte_les_filtres():
    """La première question porte la taille de page et les filtres choisis."""
    adaptateur = _adaptateur_hubeau(
        code_cours_eau=["O919"],
        date_debut=datetime(2026, 10, 1, tzinfo=UTC),
        date_fin=datetime(2026, 10, 31, 23, 59, 59, tzinfo=UTC),
    )

    demande = adaptateur.initial_request()

    assert demande.url == URL_OBSERVATIONS_TR
    assert demande.method == "GET"
    assert demande.params["size"] == "100"
    assert demande.params["code_station"] == "O919001001"
    assert demande.params["code_cours_eau"] == "O919"
    assert demande.params["date_debut"] == "2026-10-01T00:00:00Z"
    assert demande.params["date_fin"] == "2026-10-31T23:59:59Z"
    assert demande.pagination is PaginationStrategy.CURSOR
    assert demande.max_pages == 5


def test_hubeau_les_parametres_ne_sont_pas_concatenes_dans_l_url():
    """Les paramètres sont portés par la demande, jamais à la main dans l'URL."""
    demande = _adaptateur_hubeau(code_cours_eau=["O919"]).initial_request()

    assert "?" not in demande.url
    assert "code_cours_eau" not in demande.url
    assert "code_cours_eau=O919" in demande.effective_url


def test_hubeau_la_pagination_suit_le_lien_suivant():
    """La page suivante vient du lien `next` du fournisseur."""
    adaptateur = _adaptateur_hubeau()
    demande = adaptateur.initial_request()

    suivante = adaptateur.next_request(
        demande,
        _page_hubeau(donnees=[{"code_station": "O919001001"}], suivant=LIEN_SUIVANT_HUBEAU),
    )

    assert suivante is not None
    assert suivante.url == URL_OBSERVATIONS_TR
    assert suivante.params["cursor"].startswith("AoJw+")
    assert suivante.params["code_station"] == "O919001001"
    assert suivante.params["size"] == "1"
    assert suivante.label == demande.label


def test_hubeau_une_page_vide_epuise_la_pagination():
    """Une page vide : il n'y a plus rien à demander."""
    adaptateur = _adaptateur_hubeau()
    demande = adaptateur.initial_request()

    assert (
        adaptateur.next_request(demande, _page_hubeau(donnees=[], suivant=LIEN_SUIVANT_HUBEAU))
        is None
    )


def test_hubeau_l_absence_de_lien_suivant_epuise_la_pagination():
    """Sans lien suivant, la source n'a plus de page à donner."""
    adaptateur = _adaptateur_hubeau()
    demande = adaptateur.initial_request()

    assert (
        adaptateur.next_request(
            demande, _page_hubeau(donnees=[{"code_station": "O"}], suivant=None)
        )
        is None
    )


def test_hubeau_le_budget_de_pages_appartient_au_socle():
    """L'adaptateur ne plafonne pas : le socle arrête, et sait qu'il a tronqué.

    Un adaptateur qui s'arrêterait lui-même confondrait « la source est
    épuisée » et « le parcours a été tronqué » — deux issues qu'il faut
    pouvoir rapporter différemment.
    """
    adaptateur = _adaptateur_hubeau(max_pages=2)
    demande = adaptateur.initial_request()

    suivante = adaptateur.next_request(
        demande,
        _page_hubeau(donnees=[{"code_station": "O"}], suivant=LIEN_SUIVANT_HUBEAU),
    )

    assert suivante is not None
    assert suivante.max_pages == 2
    # L'adaptateur propose toujours la suite : c'est le budget, porté par la
    # demande, qui l'arrêtera.
    encore = adaptateur.next_request(
        suivante,
        _page_hubeau(donnees=[{"code_station": "O"}], suivant=LIEN_SUIVANT_HUBEAU),
    )
    assert encore is not None


def test_hubeau_un_lien_suivant_etranger_est_refuse():
    """Le lien du fournisseur ne peut pas emmener ailleurs."""
    adaptateur = _adaptateur_hubeau()
    demande = adaptateur.initial_request()
    etrangere = "https://ailleurs.test/renvoi?cursor=x"

    with pytest.raises(ValueError, match="point d'accès"):
        adaptateur.next_request(
            demande, _page_hubeau(donnees=[{"code_station": "O"}], suivant=etrangere)
        )


def test_hubeau_un_instant_naif_est_refuse():
    """INV-15 : pas de fenêtre temporelle sans fuseau."""
    with pytest.raises(ValueError, match="sans fuseau"):
        _adaptateur_hubeau(date_debut=datetime(2026, 10, 1))


def test_hubeau_declare_l_epuisement_de_son_parcours():
    """La source paginée dit elle-même quand il n'y a plus rien.

    Le lien `next` disparaissant, Hub'EAU déclare la fin du parcours : une
    réponse 200 signifie alors « c'est tout », et non « j'ai rendu ce que
    j'avais ». Le socle peut donc consigner cette exhaustivité comme
    déclarée.
    """
    assert _adaptateur_hubeau().declares_exhaustion is True


# --------------------------------------------------------------------------
# USGS
# --------------------------------------------------------------------------


def test_usgs_la_premiere_demande_borne_la_fenetre():
    """La fenêtre est portée par la demande, en ISO 8601 UTC."""
    adaptateur = UsgsInstantaneousValuesAdapter(
        sites=["03339000"],
        parameter_cd=["00060"],
        start_dt=datetime(2026, 10, 25, tzinfo=UTC),
        end_dt=datetime(2026, 10, 26, tzinfo=UTC),
    )

    demande = adaptateur.initial_request()

    assert demande.url == URL_IV
    assert demande.params["format"] == "json"
    assert demande.params["sites"] == "03339000"
    assert demande.params["parameterCd"] == "00060"
    assert demande.params["startDT"] == "2026-10-25T00:00:00Z"
    assert demande.params["endDT"] == "2026-10-26T00:00:00Z"
    assert demande.pagination is PaginationStrategy.NONE
    assert demande.max_pages == 1


def test_usgs_la_duree_relative_est_acceptee():
    """Une durée relative remplace les deux instants bornes."""
    adaptateur = UsgsInstantaneousValuesAdapter(
        sites=["03339000"],
        parameter_cd=["00060"],
        period="P7D",
    )

    demande = adaptateur.initial_request()

    assert demande.params["period"] == "P7D"
    assert "startDT" not in demande.params
    assert "endDT" not in demande.params


def test_usgs_la_source_ne_se_parcourt_pas_page_par_page():
    """Cette source rend tout en une réponse : il n'y a pas de page suivante."""
    adaptateur = UsgsInstantaneousValuesAdapter(
        sites=["03339000"],
        parameter_cd=["00060"],
        period="P7D",
    )
    demande = adaptateur.initial_request()

    assert adaptateur.next_request(demande, _reponse({"value": {"timeSeries": []}})) is None


def test_usgs_une_fenetre_ambigue_est_refusee():
    """Une durée et une plage à la fois : la question est mal posée."""
    with pytest.raises(ValueError, match="ambiguë"):
        UsgsInstantaneousValuesAdapter(
            sites=["03339000"],
            parameter_cd=["00060"],
            period="P7D",
            start_dt=datetime(2026, 10, 25, tzinfo=UTC),
            end_dt=datetime(2026, 10, 26, tzinfo=UTC),
        )


def test_usgs_une_fenetre_manquante_est_refusee():
    """Sans fenêtre, la source rendrait l'intégralité de son référentiel."""
    with pytest.raises(ValueError, match="manquante"):
        UsgsInstantaneousValuesAdapter(sites=["03339000"], parameter_cd=["00060"])


def test_usgs_sans_station_nest_pas_une_question():
    """Une station au moins, sinon la requête n'est pas bornée."""
    with pytest.raises(ValueError, match="sites est obligatoire"):
        UsgsInstantaneousValuesAdapter(sites=[], parameter_cd=["00060"], period="P7D")


def test_usgs_ne_declare_pas_l_epuisement_de_son_parcours():
    """Une source sans pagination ne déclare rien.

    Le fournisseur ne renvoie ni jeton de page suivante, ni en-tête de lien :
    il n'a aucun moyen de dire « il n'y a plus rien ». Une réponse 200 prouve
    que la requête a abouti, **pas** que toutes les observations attendues
    ont été rendues : l'exhaustivité reste indéclarée, et c'est le cas le
    plus fréquent.
    """
    adaptateur = UsgsInstantaneousValuesAdapter(
        sites=["03339000"],
        parameter_cd=["00060"],
        period="P7D",
    )

    assert adaptateur.declares_exhaustion is False


# --------------------------------------------------------------------------
# Copernicus
# --------------------------------------------------------------------------


def test_copernicus_la_premiere_demande_porte_le_filtre_odata():
    """La première question porte le filtre et la taille de page."""
    adaptateur = CopernicusProductsAdapter(
        filter_expression="startswith(Name,'Sentinel-2')",
        page_size=100,
        max_pages=5,
    )

    demande = adaptateur.initial_request()

    assert demande.url == URL_PRODUCTS
    assert demande.params["$top"] == "100"
    assert demande.params["$filter"] == "startswith(Name,'Sentinel-2')"
    assert demande.pagination is PaginationStrategy.CURSOR
    assert demande.max_pages == 5


def test_copernicus_les_parametres_odata_ne_sont_pas_concatenes_dans_l_url():
    """Les paramètres OData restent dans la demande, encodés au moment de l'envoi."""
    demande = CopernicusProductsAdapter(
        filter_expression="startswith(Name,'Sentinel-2')",
        page_size=100,
        max_pages=5,
    ).initial_request()

    assert "?" not in demande.url
    assert "%24top=100" in demande.effective_url
    assert "%24filter=startswith" in demande.effective_url


def test_copernicus_la_pagination_suit_le_next_link():
    """Le catalogue donne sa page suivante : l'adaptateur la décode et la suit."""
    adaptateur = CopernicusProductsAdapter(
        filter_expression="startswith(Name,'Sentinel-2')",
        page_size=1,
        max_pages=5,
    )
    demande = adaptateur.initial_request()

    suivante = adaptateur.next_request(
        demande,
        _reponse({"value": [{"Id": "abc"}], "@odata.nextLink": LIEN_SUIVANT_COPERNICUS}),
    )

    assert suivante is not None
    assert suivante.url == URL_PRODUCTS
    assert suivante.params["$skip"] == "1"
    assert suivante.params["$top"] == "1"
    assert suivante.params["$filter"] == "startswith(Name,'Sentinel-2')"


def test_copernicus_l_absence_de_next_link_epuise_la_pagination():
    """Sans `@odata.nextLink`, le catalogue n'a plus de page à donner."""
    adaptateur = CopernicusProductsAdapter(
        filter_expression="startswith(Name,'Sentinel-2')",
        page_size=1,
        max_pages=5,
    )
    demande = adaptateur.initial_request()

    assert adaptateur.next_request(demande, _reponse({"value": []})) is None


def test_copernicus_le_budget_de_pages_appartient_au_socle():
    """L'adaptateur ne plafonne pas : le socle arrête, et sait qu'il a tronqué."""
    adaptateur = CopernicusProductsAdapter(
        filter_expression="startswith(Name,'Sentinel-2')",
        page_size=1,
        max_pages=2,
    )
    demande = adaptateur.initial_request()

    suivante = adaptateur.next_request(
        demande,
        _reponse({"value": [{"Id": "abc"}], "@odata.nextLink": LIEN_SUIVANT_COPERNICUS}),
    )
    assert suivante is not None
    assert suivante.max_pages == 2
    encore = adaptateur.next_request(
        suivante,
        _reponse({"value": [{"Id": "abd"}], "@odata.nextLink": LIEN_SUIVANT_COPERNICUS}),
    )
    assert encore is not None


def test_copernicus_un_lien_suivant_etranger_est_refuse():
    """Le lien du catalogue ne peut pas emmener ailleurs."""
    adaptateur = CopernicusProductsAdapter(
        filter_expression="startswith(Name,'Sentinel-2')",
        page_size=1,
        max_pages=5,
    )
    demande = adaptateur.initial_request()

    with pytest.raises(ValueError, match="point d'accès"):
        adaptateur.next_request(
            demande,
            _reponse({"value": [], "@odata.nextLink": "https://ailleurs.test/renvoi"}),
        )


def test_copernicus_declare_l_epuisement_de_son_parcours():
    """Le catalogue déclare la fin du parcours par l'absence de `@odata.nextLink`.

    Une réponse 200 signifie alors « c'est tout », et non « j'ai rendu ce que
    j'avais » : le socle peut consigner cette exhaustivité comme déclarée.
    """
    adaptateur = CopernicusProductsAdapter(
        filter_expression="startswith(Name,'Sentinel-2')",
        page_size=10,
        max_pages=2,
    )

    assert adaptateur.declares_exhaustion is True


# --------------------------------------------------------------------------
# Ce que les trois adaptateurs ont en commun
# --------------------------------------------------------------------------


def test_chaque_adaptateur_nomme_son_origine():
    """Un adaptateur sait de qui il vient, et où il va le demander."""
    for adaptateur in (
        _adaptateur_hubeau(),
        UsgsInstantaneousValuesAdapter(sites=["03339000"], parameter_cd=["00060"], period="P7D"),
        CopernicusProductsAdapter(
            filter_expression="startswith(Name,'Sentinel-2')", page_size=10, max_pages=2
        ),
    ):
        assert adaptateur.source.source_id
        assert adaptateur.source.producer
        assert adaptateur.source.access_point
        assert adaptateur.initial_request().source_id == adaptateur.source.source_id


def test_chaque_adaptateur_expose_le_contrat_de_la_source():
    """Les trois adaptateurs exposent ce que le contrat exige.

    Dont `declares_exhaustion` : c'est par là que le socle sait si une
    source **déclare** la fin de son parcours, ou si elle se contente de
    répondre 200 — auquel cas l'exhaustivité reste indéclarée.
    """
    for adaptateur in (
        _adaptateur_hubeau(),
        UsgsInstantaneousValuesAdapter(sites=["03339000"], parameter_cd=["00060"], period="P7D"),
        CopernicusProductsAdapter(
            filter_expression="startswith(Name,'Sentinel-2')", page_size=10, max_pages=2
        ),
    ):
        assert adaptateur.source.source_id
        assert isinstance(adaptateur.declares_exhaustion, bool)
        assert callable(adaptateur.initial_request)
        assert callable(adaptateur.next_request)
