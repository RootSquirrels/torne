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

  **Mesuré de nouveau le 31 octobre 2026 à 23:29, sur cette instance.** Une
  requête portant `code_station=O919001001` et `grandeur_hydro=H` rend le
  même `count` (17 350 477) et les mêmes stations qu'une requête sans filtre
  de station ; une station **inexistante** (`ZZZZZZZZZZ`) rend cette
  réponse-là encore, identique. Le filtre est **écho** dans l'URL, il
  n'agit pas sur la population. Un filtre `date_debut`/`date_fin` est
  ignoré de la même manière : la requête sans `grandeur_hydro` rend alors le
  `count` du référentiel entier.

  C'est pourquoi le prédicat de conformité de cet adaptateur **vérifie les
  identifiants présents dans les lignes réellement reçues** : il ne suppose
  pas que le fournisseur a obéi. Sur cette instance, il rend un verdict
  `non_conforme`, et l'acquisition est bloquée — la preuve brute, elle, est
  conservée, et c'est bien l'intérêt d'une réponse qui a répondu à côté.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from ...contracts.observation import Source
from ..contracts import (
    AcquisitionRequest,
    CritereConformite,
    HttpResponse,
    PaginationStrategy,
    VerdictConformite,
    verdict_from_criteria,
)

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

    def verdict_conformite(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> VerdictConformite:
        """Les lignes reçues sont-elles bien celles qui ont été demandées ?

        C'est le prédicat propre à cette source. Il confronte ce que la
        demande a demandé aux identifiants **présents dans les lignes
        réellement reçues** — il ne suppose pas que le fournisseur a obéi à
        ses filtres, et il a des raisons de ne pas le supposer : mesuré le
        31 octobre 2026, ce point d'accès accepte `code_station` sans
        l'appliquer (voir la docstring du module).

        Trois critères vérifiables ici : la **station**, la **grandeur**, et la
        **fenêtre temporelle**. Le **cours d'eau**, lui, n'est pas exposé par
        les lignes de ce point d'accès : le critère est donc consigné comme
        **non vérifiable** — jamais comme satisfait. Le référentiel de la
        station porte son cours d'eau, et c'est la station qui est vérifiée.

        Consequence: asking for a water course renders the verdict
        **indeterminate**, and not a favourable one. It is an abstention, not
        a finding: conformity is established neither way, and the outcome is
        therefore not exploitable. That is the intended behaviour — nothing is
        certified that could not be verified.
        """
        lignes, _ = self._lire_page(response)
        criteres: dict[str, CritereConformite] = {}

        if self._code_station:
            criteres["code_station"] = self._criteres_identite(
                lignes, "code_station", ", ".join(self._code_station), self._code_station
            )

        if self._grandeur_hydro:
            criteres["grandeur_hydro"] = self._criteres_identite(
                lignes, "grandeur_hydro", self._grandeur_hydro, (self._grandeur_hydro,)
            )

        if self._date_debut is not None or self._date_fin is not None:
            criteres["fenetre_temporelle"] = self._criteres_fenetre(lignes)

        if self._code_cours_eau:
            # Ce point d'accès n'expose pas le code de cours d'eau dans ses
            # lignes : le critère demandé ne peut pas être vérifié. La
            # conformité n'est donc **pas établie**, et c'est ce que dit le
            # verdict : une absence de vérification n'est jamais une
            # vérification réussie.
            criteres["code_cours_eau"] = CritereConformite(
                demande=", ".join(self._code_cours_eau),
                verifie=False,
                recu="ce point d'accès n'expose pas ce champ dans ses lignes",
            )

        # The truth table is the socle's: the adapter collects the criteria,
        # it does not decide the verdict.
        return verdict_from_criteria(criteres)

    def _criteres_identite(
        self,
        lignes: list[Any],
        champ: str,
        demande: str,
        attendus: tuple[str, ...],
    ) -> CritereConformite:
        """Un critère d'identité : les lignes portent-elles l'identifiant demandé ?

        Une ligne qui ne porte pas l'identifiant est une ligne qui ne peut
        pas être attribuée à la question posée : elle compte comme un écart.
        """
        if not lignes:
            return CritereConformite(
                demande=demande, verifie=False, recu="(aucune ligne à vérifier)"
            )
        recues, sans = _champ(lignes, champ)
        if not recues:
            return CritereConformite(
                demande=demande, verifie=False, recu=f"{sans} ligne(s) sans « {champ} »"
            )
        ecarts = [valeur for valeur in recues if valeur not in attendus]
        recu = _rendre(recues)
        if sans:
            recu = f"{recu} (+{sans} sans « {champ} »)"
        return CritereConformite(
            demande=demande,
            verifie=True,
            recu=recu,
            conforme=not ecarts and not sans,
        )

    def _criteres_fenetre(self, lignes: list[Any]) -> CritereConformite:
        """Le critère de fenêtre temporelle, d'après les `date_obs` reçues."""
        instants: list[datetime] = []
        illisibles = 0
        for ligne in lignes:
            instant = _instant_utc(ligne.get("date_obs"))
            if instant is None:
                illisibles += 1
            else:
                instants.append(instant)

        borne_debut = self._date_debut
        borne_fin = self._date_fin
        demande = (
            f"de {_iso_utc(borne_debut)} à {_iso_utc(borne_fin)}"
            if borne_debut is not None and borne_fin is not None
            else (
                f"depuis {_iso_utc(borne_debut)}"
                if borne_debut is not None
                else f"jusqu'à {_iso_utc(borne_fin)}"
            )
        )

        if not instants:
            return CritereConformite(
                demande=demande,
                verifie=False,
                recu="(aucune date lisible)",
            )
        if illisibles:
            return CritereConformite(
                demande=demande,
                verifie=False,
                recu=f"{illisibles} date(s) illisible(s)",
            )

        hors = [
            instant
            for instant in instants
            if (borne_debut is not None and instant < borne_debut)
            or (borne_fin is not None and instant > borne_fin)
        ]
        recu = f"{min(instants).isoformat()} .. {max(instants).isoformat()}"
        if hors:
            recu = f"{recu} (dont {len(hors)} hors fenêtre)"
        return CritereConformite(
            demande=demande,
            verifie=True,
            recu=recu,
            conforme=not hors,
        )


def _iso_utc(instant: datetime) -> str:
    """L'instant en ISO 8601 UTC, le format honoré par le point d'accès."""
    return instant.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rendre(valeurs: list[str], maximum: int = 5) -> str:
    """Les valeurs, rendues lisiblement : les premières, et le compte du reste.

    Une réponse peut porter des dizaines de stations : en garder toutes rendrait
    le motif illisible, et un motif illisible n'est pas un motif auditable.
    """
    if len(valeurs) <= maximum:
        return ", ".join(valeurs)
    return f"{', '.join(valeurs[:maximum])} (+{len(valeurs) - maximum} autres)"


def _champ(lignes: list[Any], nom: str) -> tuple[list[str], int]:
    """Les valeurs distinctes d'un champ, et combien de lignes n'en portent pas."""
    valeurs: list[str] = []
    sans = 0
    for ligne in lignes:
        if not isinstance(ligne, dict):
            sans += 1
            continue
        brut = ligne.get(nom)
        if brut is None:
            sans += 1
            continue
        valeur = str(brut)
        if valeur not in valeurs:
            valeurs.append(valeur)
    return valeurs, sans


def _instant_utc(brut: object) -> datetime | None:
    """L'instant ISO 8601 d'une valeur de source, ou `None` s'il est illisible."""
    if not isinstance(brut, str) or not brut.strip():
        return None
    texte = brut.strip()
    if texte.endswith("Z"):
        texte = f"{texte[:-1]}+00:00"
    try:
        instant = datetime.fromisoformat(texte)
    except ValueError:
        return None
    if instant.tzinfo is None:
        return instant.replace(tzinfo=UTC)
    return instant.astimezone(UTC)


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
