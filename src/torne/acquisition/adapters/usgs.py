"""Adaptateur USGS NWIS — valeurs instantanées (instantaneous values).

Cet adaptateur **pose des questions** au National Water Information System
de l'USGS et ne sait rien du domaine : il ne connaît ni le débit, ni la
surface d'eau, ni ce que signifie une valeur provisoire. Il construit une
URL, fixe la fenêtre temporelle demandée, et rend `None` à la question
suivante — cette source ne se parcourt pas page par page.

Ce qui a été **vérifié sur le réseau** (2026-10-31, poste de
développement) :

- le point d'accès ne rend du JSON que si `format=json` est demandé ; sinon
  il rend du XML ;
- la réponse est un objet JSON
  `{"name", "declaredType", "scope", "value"}`, et `value` porte
  `queryInfo` et `timeSeries` ;
- les paramètres `sites`, `parameterCd`, `period`, `startDT` et `endDT` sont
  acceptés et consignés par le fournisseur dans `queryInfo.criteria`, qui
  en confirme l'interprétation exacte ;
- `startDT`/`endDT` bornent une **plage** (`mode=RANGE`) : `endDT` inclut
  le jour entier ; `period` demande une durée relative ;
- il n'y a **aucune pagination** : la fenêtre demandée tient dans une seule
  réponse ;
- les valeurs les plus récentes sont marquées provisoires par le
  qualificatif `P` et par l'avertissement que le fournisseur joint à
  chaque réponse. Ce marqueur est **conservé tel quel** dans le brut : il
  appartient à la preuve, pas à l'interprétation.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from ...contracts.observation import Source
from ..contracts import AcquisitionRequest, HttpResponse, PaginationStrategy

URL_IV = "https://waterservices.usgs.gov/nwis/iv/"
"""Point d'accès des valeurs instantanées du NWIS."""

SOURCE_ID = "usgs.nwis.iv"
"""Identifiant de la source, stable et sans ambiguïté."""


class UsgsInstantaneousValuesAdapter:
    """Les questions à poser au NWIS sur les valeurs instantanées.

    La fenêtre temporelle est **explicite et unique** : soit une durée
    relative (`period`, par exemple `P7D`), soit deux instants bornes
    (`start_dt` et `end_dt`). Les deux à la fois, ou aucun des deux, sont
    refusés : une fenêtre ambiguë est une fenêtre fausse.
    """

    def __init__(
        self,
        *,
        sites: Sequence[str],
        parameter_cd: Sequence[str],
        period: str | None = None,
        start_dt: datetime | None = None,
        end_dt: datetime | None = None,
    ) -> None:
        """Fixe la question à poser.

        `sites` et `parameter_cd` sont obligatoires et non vides : une
        requête sans station ramènerait l'ensemble du référentiel du NWIS.
        """
        if not sites:
            raise ValueError("sites est obligatoire : une station au moins")
        if not parameter_cd:
            raise ValueError("parameter_cd est obligatoire : un code de grandeur au moins")
        if period is not None and (start_dt is not None or end_dt is not None):
            raise ValueError("fenêtre ambiguë : period exclut start_dt et end_dt")
        if period is None and (start_dt is None or end_dt is None):
            raise ValueError("fenêtre manquante : period, ou start_dt et end_dt")
        if period is not None and not str(period).strip():
            raise ValueError("period ne peut pas être vide")
        for instant, nom in ((start_dt, "start_dt"), (end_dt, "end_dt")):
            if instant is not None and not isinstance(instant, datetime):
                raise TypeError(f"{nom} doit être un instant")
            if instant is not None and instant.tzinfo is None:
                raise ValueError(f"{nom} : un instant sans fuseau est refusé (INV-15)")
        if start_dt is not None and end_dt is not None and end_dt < start_dt:
            raise ValueError("end_dt ne peut pas précéder start_dt")

        self._sites = tuple(sites)
        self._parameter_cd = tuple(parameter_cd)
        self._period = period
        self._start_dt = start_dt
        self._end_dt = end_dt

    @property
    def source(self) -> Source:
        """La source interrogée : l'origine, et ses conditions d'usage."""
        return Source(
            source_id=SOURCE_ID,
            producer="U.S. Geological Survey (USGS)",
            dataset="National Water Information System — valeurs instantanées",
            access_point=URL_IV,
            license="Données publiques (domaine public, U.S. Geological Survey)",
            revision_policy=(
                "Les valeurs les plus récentes sont marquées provisoires par le "
                "fournisseur (qualificatif « P ») et susceptibles d'être révisées"
            ),
            unit=None,
            timezone=None,
            quality_status=None,
        )

    @property
    def declares_exhaustion(self) -> bool:
        """Cette source **ne déclare rien** : elle ne se parcourt pas page par page.

        Le fournisseur ne renvoie ni jeton de page suivante, ni en-tête de
        lien : il n'a donc aucun moyen de dire « il n'y a plus rien ». Une
        réponse 200 prouve que la requête a abouti, **pas** que toutes les
        observations attendues ont été rendues.

        L'exhaustivité reste donc indéclarée (`Exhaustiveness.UNDECLARED`) :
        c'est le cas le plus fréquent, et il doit rester visible plutôt que
        d'être déguisé en parcours complet.
        """
        return False

    def initial_request(self) -> AcquisitionRequest:
        """La première question : la fenêtre demandée, en une seule requête."""
        params: dict[str, str] = {
            "format": "json",
            "sites": ",".join(self._sites),
            "parameterCd": ",".join(self._parameter_cd),
        }
        if self._period is not None:
            params["period"] = self._period
        else:
            params["startDT"] = _iso_utc(self._start_dt)
            params["endDT"] = _iso_utc(self._end_dt)
        return AcquisitionRequest(
            source_id=SOURCE_ID,
            url=URL_IV,
            method="GET",
            params=params,
            pagination=PaginationStrategy.NONE,
            max_pages=1,
            label="usgs:nwis_iv",
        )

    def next_request(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> AcquisitionRequest | None:
        """Toujours `None` : cette source ne se parcourt pas page par page.

        La fenêtre temporelle tient dans une seule réponse, et le
        fournisseur ne renvoie ni jeton de page suivante, ni en-tête de
        lien. Il n'y a donc rien à demander après la première réponse.
        """
        return None


def _iso_utc(instant: datetime | None) -> str:
    """L'instant en ISO 8601 UTC, le format que le fournisseur a honoré."""
    if instant is None:
        raise ValueError("instant attendu")
    return instant.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = ["SOURCE_ID", "URL_IV", "UsgsInstantaneousValuesAdapter"]
