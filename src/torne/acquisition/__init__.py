"""Socle transversal d'acquisition.

Ce paquet sait **récupérer et conserver** des informations du monde physique.
Il ne sait pas ce qu'elles signifient.

Trois niveaux, séparés par des contrats explicites :

- **Socle transversal** (ce paquet) : poser une question sur le réseau,
  suivre la pagination, conserver la réponse brute, saigner son empreinte, et
  consigner ce qui a été demandé et ce qui a échoué.
- **Couche sémantique** : comprendre ce qui a été collecté — objets, unités,
  référentiels, relations — en laissant chaque domaine définir les siens.
- **Couche scientifique** : transformer les observations en connaissances.

Un adaptateur de source appartient au premier niveau par ses moyens et au
deuxième par sa méthode : il sait *comment* interroger un fournisseur, et
jamais *ce que* les données veulent dire. C'est la séparation que le
programme impose : « Un connecteur ne doit pas savoir reconstruire un état
hydrologique. Un modèle hydrologique ne doit pas savoir comment interroger
l'API d'un fournisseur particulier. » (`docs/PROGRAMME.md`).
"""

from .contracts import (
    AcquisitionAttempt,
    AcquisitionErrorKind,
    AcquisitionOutcome,
    AcquisitionRequest,
    AcquisitionStatus,
    CredentialProvider,
    HttpResponse,
    PaginationStrategy,
    SourceAdapter,
)
from .fetcher import Fetcher, RetryPolicy, classer_statut
from .store import FileRawStore, RawStore
from .transport import HttpTransport, RecordingTransport, Transport, TransportError

__all__ = [
    "AcquisitionAttempt",
    "AcquisitionErrorKind",
    "AcquisitionOutcome",
    "AcquisitionRequest",
    "AcquisitionStatus",
    "CredentialProvider",
    "Fetcher",
    "FileRawStore",
    "HttpResponse",
    "HttpTransport",
    "PaginationStrategy",
    "RawStore",
    "RecordingTransport",
    "RetryPolicy",
    "SourceAdapter",
    "Transport",
    "TransportError",
    "classer_statut",
]
