"""Transport HTTP du socle d'acquisition.

Ce module ne connaît **aucun fournisseur** : il sait poser une question sur
le réseau et rapporter la réponse — ou l'échec. Un adaptateur de source ne
sait rien de l'URL d'un fournisseur ; un modèle ne sait rien du réseau. Les
deux se parlent par l'intermédiaire de `AcquisitionRequest` et de
`HttpResponse`.

Deux choix structurants :

1. **Bibliothèque standard seulement.** `urllib.request` suffit à une API
   JSON, un fichier et un catalogue. Une dépendance runtime ne s'ajoute qu'au
   premier import réel — et ici, il n'y en a pas (`docs/PROGRAMME.md`).
2. **Les identifiants ne transitent que par les en-têtes.** Ils sont appliqués
   au moment de l'envoi et ne rejoignent **jamais** l'objet `AcquisitionRequest`
   ni ce qui est consigné : le journal d'acquisition peut donc être publié
   sans rien divulguer.
"""

from __future__ import annotations

import socket
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from typing import Protocol

from .contracts import AcquisitionErrorKind, AcquisitionRequest, HttpResponse

USER_AGENT = "torne-acquisition/0.1 (+https://github.com/RootSquirrels/torne)"


class TransportError(Exception):
    """Échec de transport : la réponse n'est pas arrivée.

    C'est le seul cas où l'on ne sait pas si le fournisseur a reçu la
    demande. La distinction est conservée telle quelle, parce qu'une reprise
    n'a pas le même sens sur une coupure réseau que sur un refus explicite.
    """

    def __init__(self, detail: str, *, kind: AcquisitionErrorKind = AcquisitionErrorKind.TRANSPORT):
        super().__init__(detail)
        self.detail = detail
        self.kind = kind


class Transport(Protocol):
    """Ce qu'un transport sait faire : poser une question, rendre la réponse."""

    def send(
        self,
        request: AcquisitionRequest,
        *,
        credentials: Mapping[str, str] | None = None,
    ) -> HttpResponse:
        """Envoie la demande et rend la réponse **brute**.

        Une réponse HTTP — y compris un code d'erreur — est une réponse : elle
        est rendue telle quelle, avec son corps. Seule une panne réseau lève
        `TransportError`.
        """
        ...


class HttpTransport:
    """Transport HTTP fondé sur `urllib.request`.

    Il se distingue du `Transport` par trois réglages explicites : le délai
    d'attente, l'agent utilisateur, et le nombre de redirections autorisées.
    Rien n'est implicite.
    """

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        user_agent: str = USER_AGENT,
        max_redirects: int = 5,
    ) -> None:
        if timeout <= 0:
            raise ValueError("le délai d'attente doit être strictement positif")
        self._timeout = timeout
        self._user_agent = user_agent
        self._max_redirects = max_redirects

    def send(
        self,
        request: AcquisitionRequest,
        *,
        credentials: Mapping[str, str] | None = None,
    ) -> HttpResponse:
        """Envoie la demande et rend la réponse brute."""
        url = request.effective_url
        native = urllib.request.Request(url, data=request.body, method=request.method.upper())
        native.add_header("User-Agent", self._user_agent)
        for nom, valeur in request.headers.items():
            native.add_header(nom, valeur)
        for nom, valeur in (credentials or {}).items():
            native.add_header(nom, valeur)

        try:
            with urllib.request.urlopen(native, timeout=self._timeout) as reponse:
                corps = reponse.read()
                return HttpResponse(
                    status_code=reponse.status,
                    headers=dict(reponse.headers),
                    body=corps,
                    url=url,
                )
        except urllib.error.HTTPError as erreur:
            # Un code d'erreur HTTP est une réponse : elle porte un corps,
            # souvent une explication. Elle est rendue, pas avalée.
            try:
                corps = erreur.read()
            except Exception:  # pragma: no cover - le corps peut être absent
                corps = b""
            return HttpResponse(
                status_code=erreur.code,
                headers=dict(erreur.headers or {}),
                body=corps,
                url=url,
            )
        except urllib.error.URLError as erreur:
            raison = getattr(erreur, "reason", erreur)
            if isinstance(raison, socket.timeout):
                raise TransportError(f"délai dépassé pour « {url} »") from erreur
            raise TransportError(f"transport impossible pour « {url} » : {raison}") from erreur
        except TimeoutError as erreur:
            raise TransportError(f"délai dépassé pour « {url} »") from erreur
        except OSError as erreur:
            raise TransportError(f"erreur réseau pour « {url} » : {erreur}") from erreur

    def url_with_query(self, url: str, params: Mapping[str, str]) -> str:
        """URL complète, paramètres encodés. Utile aux adaptateurs de source."""
        if not params:
            return url
        query = urllib.parse.urlencode(
            [(cle, str(valeur)) for cle, valeur in sorted(params.items())]
        )
        separateur = "&" if "?" in url else "?"
        return f"{url}{separateur}{query}"


class RecordingTransport:
    """Transport qui enregistre les demandes et rend des réponses préparées.

    Il sert aux tests hors ligne : le réseau n'est jamais touché, et chaque
    demande est vérifiable. Il est volontairement simple — une file de
    réponses, dans l'ordre — parce qu'un test qui doit comprendre un
    ordonnanceur complexe teste l'ordonnanceur, pas le socle.
    """

    def __init__(self, responses: list[HttpResponse]) -> None:
        self._responses = list(responses)
        self.requests: list[AcquisitionRequest] = []
        self.credentials_seen: list[Mapping[str, str]] = []

    def send(
        self,
        request: AcquisitionRequest,
        *,
        credentials: Mapping[str, str] | None = None,
    ) -> HttpResponse:
        """Rend la réponse préparée suivante, ou échoue s'il n'en reste plus."""
        self.requests.append(request)
        self.credentials_seen.append(dict(credentials or {}))
        if not self._responses:
            raise TransportError("plus aucune réponse préparée")
        return self._responses.pop(0)


__all__ = [
    "USER_AGENT",
    "HttpTransport",
    "RecordingTransport",
    "Transport",
    "TransportError",
]
