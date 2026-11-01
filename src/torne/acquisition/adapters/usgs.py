"""Adaptateur USGS NWIS — valeurs instantanées (instantaneous values).

**Déprécié — ne plus l'utiliser.** Les API WaterServices sont déclassées :
dégradation des paquets à partir du **1er février 2027**, **mise hors service
le 22 février 2027**. L'adaptateur qui les remplace est `usgs_ogc.py`
(« Water Data for the Nation », API OGC Features), et c'est la cible du
jalon « données réelles ». Cet adaptateur reste dans le dépôt, testé, pour
que le chemin historique reste rejouable ; il ne doit plus recevoir de
nouveau code, et il disparaîtra avec la bascule des paquets.

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

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from ...contracts.observation import Source
from ..contracts import (
    AcquisitionRequest,
    Conformite,
    CritereConformite,
    HttpResponse,
    PaginationStrategy,
    VerdictConformite,
)

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

    def verdict_conformite(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> VerdictConformite:
        """Les séries reçues sont-elles bien celles qui ont été demandées ?

        Prédicat propre à cette source. Deux critères vérifiables ici, tous
        deux portés par la réponse elle-même : la **station** et le **code de
        grandeur**. Mesuré le 31 octobre 2026, ce fournisseur applique
        effectivement `sites` — une station inexistante rend zéro série —
        et le contrôle le vérifie plutôt que de le supposer.
        """
        charge = _charger_json(response, "USGS")
        valeur = charge.get("value")
        if not isinstance(valeur, dict):
            raise ValueError("réponse USGS inattendue : le champ « value » n'est pas un objet")
        series = valeur.get("timeSeries")
        if series is None:
            series = []
        if not isinstance(series, list):
            raise ValueError("réponse USGS inattendue : « timeSeries » n'est pas une liste")

        criteres: dict[str, CritereConformite] = {
            "sites": self._criteres_identite(series, "sourceInfo.siteCode", self._sites),
            "parameter_cd": self._criteres_identite(
                series, "variable.variableCode", self._parameter_cd
            ),
        }

        echecs = [nom for nom, critere in criteres.items() if critere.conforme is False]
        if not echecs:
            return VerdictConformite(conformite=Conformite.CONFORME, criteres=criteres)

        details = " ; ".join(
            f"{nom} demandé « {criteres[nom].demande} », reçu « {criteres[nom].recu} »"
            for nom in echecs
        )
        return VerdictConformite(
            conformite=Conformite.NON_CONFORME,
            motif=(f"la source a renvoyé des séries qui ne sont pas celles demandées : {details}"),
            criteres=criteres,
        )

    def _criteres_identite(
        self,
        series: list[object],
        chemin: str,
        attendus: tuple[str, ...],
    ) -> CritereConformite:
        """Un critère d'identité, lu dans les séries reçues.

        `chemin` nomme le chemin de l'identifiant dans la réponse :
        `sourceInfo.siteCode` pour la station, `variable.variableCode` pour
        la grandeur. Une série qui ne porte pas cet identifiant est une série
        qui ne peut pas être attribuée à la question posée : elle compte
        comme un écart.
        """
        demande = ", ".join(attendus)
        if not series:
            return CritereConformite(demande=demande, verifie=False)

        recues: list[str] = []
        sans = 0
        for serie in series:
            valeurs = _valeurs_du_chemin(serie, chemin)
            if not valeurs:
                sans += 1
                continue
            for valeur in valeurs:
                if valeur not in recues:
                    recues.append(valeur)

        if not recues:
            return CritereConformite(
                demande=demande,
                verifie=False,
                recu=f"{sans} série(s) sans « {chemin} »",
            )
        ecarts = [valeur for valeur in recues if valeur not in attendus]
        recu = ", ".join(recues)
        if sans:
            recu = f"{recu} (+{sans} sans « {chemin} »)"
        return CritereConformite(
            demande=demande,
            verifie=True,
            recu=recu,
            conforme=not ecarts and not sans,
        )


def _iso_utc(instant: datetime | None) -> str:
    """L'instant en ISO 8601 UTC, le format que le fournisseur a honoré."""
    if instant is None:
        raise ValueError("instant attendu")
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


def _valeurs_du_chemin(serie: object, chemin: str) -> list[str]:
    """Les valeurs d'un identifiant dans une série : `siteCode`, `variableCode`."""
    if not isinstance(serie, dict):
        return []
    noeud: Any = serie
    for fragment in chemin.split("."):
        if not isinstance(noeud, dict):
            return []
        noeud = noeud.get(fragment)
    if not isinstance(noeud, list):
        return []
    valeurs: list[str] = []
    for element in noeud:
        if isinstance(element, dict) and element.get("value") is not None:
            valeurs.append(str(element["value"]))
    return valeurs


__all__ = ["SOURCE_ID", "URL_IV", "UsgsInstantaneousValuesAdapter"]
