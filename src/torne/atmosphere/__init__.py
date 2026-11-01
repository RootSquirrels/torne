"""La couche sémantique atmosphérique — ce que les nombres de l'air signifient.

Le socle acquiert et conserve des preuves brutes, et dit si ce qui est revenu
répond à la question posée. Ce paquet est la couche au-dessus : il lit les
relevés d'un fournisseur comme des **observations** d'une grandeur physique,
et il en calcule les premières grandeurs dérivées du monde réel.

C'est le **deuxième** paquet de domaine du dépôt. Il connaît la température,
la précipitation, la climatologie journalière, les anomalies et les régimes
thermiques. Il ne connaît ni le format d'une réponse HTTP, ni la grammaire
d'un fournisseur : le socle transverse s'occupe de l'un, l'adaptateur de
l'autre, et les deux se rencontrent à la frontière du domaine.

Ce que ce paquet **ne** fait pas, et qui est aussi important :

- il ne fabrique pas de **produit de connaissance** : les grandeurs qu'il
  calcule sont des grandeurs *calculées*, avec leur règle versionnée ;
- il ne prétend pas que la source est plus exacte qu'elle ne l'est : quand
  le producteur signale qu'un contrôle a échoué, le drapeau est conservé et
  la qualité canonique est `UNKNOWN` — le socle ne **prétend** jamais qu'une
  valeur est approuvée quand le producteur ne l'a pas approuvée ;
- il ne dates jamais : une observation dont la publication est inconnue reste
  une observation dont la publication est inconnue, et n'est donc jamais
  admissible en reconstitution point-in-time.
"""

from .anomaly import (
    LONGUEUR_MINIMALE_EPISODE,
    METHOD,
    SEUIL_CHAUD,
    SEUIL_EXTREME,
    SEUIL_FROID,
    VERSION,
    Climatologie,
    ClimatologieJour,
    Episode,
    anomalies,
    climatologie,
    episodes,
    jour_civil,
    regimes,
    temperature_moyenne,
)
from .observations import (
    DAY_CONVENTION,
    DRAPEAUX_MESURE,
    DRAPEAUX_QUALITE,
    ELEMENT_UNITES,
    MISSING_VALUE,
    QUALITE_INCONNUE,
    InterpretationError,
    Ligne,
    Measurement,
    Station,
    ligne_depuis_dictionnaire,
    observation_depuis_ligne,
    observations,
    station_depuis_ligne,
)
from .profile import (
    Couverture,
    Lacune,
    ProfilVariable,
    autocorrelation,
    coupure_moyenne,
    explicer_drapaux,
    profil_variable,
    structure_temporelle,
)

__all__ = [
    "DAY_CONVENTION",
    "DRAPEAUX_MESURE",
    "DRAPEAUX_QUALITE",
    "ELEMENT_UNITES",
    "LONGUEUR_MINIMALE_EPISODE",
    "METHOD",
    "MISSING_VALUE",
    "QUALITE_INCONNUE",
    "SEUIL_CHAUD",
    "SEUIL_EXTREME",
    "SEUIL_FROID",
    "VERSION",
    "Climatologie",
    "ClimatologieJour",
    "Couverture",
    "Episode",
    "InterpretationError",
    "Lacune",
    "Ligne",
    "Measurement",
    "ProfilVariable",
    "Station",
    "anomalies",
    "autocorrelation",
    "climatologie",
    "coupure_moyenne",
    "episodes",
    "explicer_drapaux",
    "jour_civil",
    "ligne_depuis_dictionnaire",
    "observation_depuis_ligne",
    "observations",
    "profil_variable",
    "regimes",
    "station_depuis_ligne",
    "structure_temporelle",
    "temperature_moyenne",
]
