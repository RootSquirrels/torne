"""Le profil exploratoire d'une série atmosphérique.

Ce module décrit une série **sans l'interpréter** : il mesure ce qu'elle
contient, ce qu'elle ne contient pas, et comment elle se comporte dans le
temps. C'est l'instrument de lecture qui précède toute question scientifique :
on ne pose pas une question sur une série dont on ignore la couverture.

Ce qu'il mesure
---------------

- **La couverture** — combien de jours la série couvre sur la période qu'elle
  prétend couvrir, et quelles sont les dates exactes de ses extremités. La
  période de record d'une station n'est pas la période qu'on croit : elle
  commence souvent par des années à moitié peuplées.
- **Les lacunes** — les trous, leur longueur, et les plus longs d'entre eux.
  Une série de 18 000 jours qui a dix ans de trou au milieu n'est pas une
  série de 18 000 jours.
- **La distribution** —.minimum, maximum, médiane, quartiles, et la part des
  valeurs que le producteur a signalées comme ayant échoué à un contrôle.
- **La structure temporelle** — l'autocorrélation des anomalies à quelques
  retards, et la **taille effective d'échantillon** : combien de jours
  indépendants la série contient réellement. C'est le nombre qui décide de
  la puissance d'un test, et il est très inférieur au nombre de jours.

Le profil ne conclut rien. Il rend des mesures, avec leur règle.
"""

from __future__ import annotations

import itertools
import statistics
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import numpy as np

from ..contracts.observation import Observation
from ..methods.breaks import BreakResult, cusum_break_test
from ..methods.dependence import EffectiveSampleSize, effective_sample_size
from .observations import Ligne


@dataclass(frozen=True, slots=True)
class Couverture:
    """Ce que la série couvre, et ce qu'elle ne couvre pas."""

    debut: date | None
    fin: date | None
    jours_attendus: int
    """Les jours calendaires entre le début et la fin de la période."""
    jours_observes: int
    """Les jours où la série porte une valeur."""
    taux: float
    """La part des jours attendus où la série porte une valeur."""

    def as_dict(self) -> dict[str, Any]:
        """Une vue sérialisable de la couverture."""
        return {
            "debut": self.debut.isoformat() if self.debut else None,
            "fin": self.fin.isoformat() if self.fin else None,
            "jours_attendus": self.jours_attendus,
            "jours_observes": self.jours_observes,
            "taux": self.taux,
        }


@dataclass(frozen=True, slots=True)
class Lacune:
    """Un trou dans la série."""

    debut: date
    fin: date
    longueur: int

    def as_dict(self) -> dict[str, Any]:
        """Une vue sérialisable de la lacune."""
        return {
            "debut": self.debut.isoformat(),
            "fin": self.fin.isoformat(),
            "longueur": self.longueur,
        }


@dataclass(frozen=True, slots=True)
class ProfilVariable:
    """Le profil d'une variable, sur une station."""

    quantity: str
    unit: str | None
    couverture: Couverture
    lacunes: tuple[Lacune, ...]
    minimum: float | None
    maximum: float | None
    mediane: float | None
    moyenne: float | None
    ecart_type: float | None
    moyennes_mensuelles: dict[int, float]
    """La moyenne par mois calendaire — la saisonnalité, en douze nombres."""
    drapeaux_qualite: dict[str, int]
    """Le compte des drapeaux de qualité : ce que le producteur a signalé."""
    drapeaux_mesure: dict[str, int]
    sources: dict[str, int]
    """Le compte des drapeaux de source : d'où viennent les valeurs."""
    valeurs_rejetees: int
    """Les valeurs mesurées dont un contrôle a échoué."""

    def as_dict(self) -> dict[str, Any]:
        """Une vue sérialisable du profil."""
        return {
            "quantity": self.quantity,
            "unit": self.unit,
            "couverture": self.couverture.as_dict(),
            "lacunes": [lacune.as_dict() for lacune in self.lacunes],
            "minimum": self.minimum,
            "maximum": self.maximum,
            "mediane": self.mediane,
            "moyenne": self.moyenne,
            "ecart_type": self.ecart_type,
            "moyennes_mensuelles": dict(sorted(self.moyennes_mensuelles.items())),
            "drapeaux_qualite": dict(sorted(self.drapeaux_qualite.items())),
            "drapeaux_mesure": dict(sorted(self.drapeaux_mesure.items())),
            "sources": dict(sorted(self.sources.items())),
            "valeurs_rejetees": self.valeurs_rejetees,
        }


def profil_variable(lignes: Sequence[Ligne], element: str) -> ProfilVariable:
    """Le profil d'un élément, sur les lignes d'une station.

    Les jours où la série ne porte **pas** de valeur ne sont pas comptés
    comme des valeurs nulles : ils sont comptés comme des manques, et
    c'est ce qui fait la différence entre une série sèche et une série nulle.
    """
    mesures = [ligne.elements[element] for ligne in lignes if element in ligne.elements]
    valeurs = [mesure.valeur for mesure in mesures if mesure.valeur is not None]

    jours_presents = {ligne.jour for ligne in lignes if ligne.elements[element].valeur is not None}
    couverture = _couverture(jours_presents)
    lacunes = _lacunes(jours_presents)

    par_mois: dict[int, list[float]] = {}
    for ligne in lignes:
        mesure = ligne.elements.get(element)
        if mesure is None or mesure.valeur is None:
            continue
        par_mois.setdefault(ligne.jour.month, []).append(mesure.valeur)

    drapeaux_qualite = Counter(
        (mesure.drapeau_qualite or "").strip() for mesure in mesures if mesure.valeur is not None
    )
    drapeaux_mesure = Counter(
        (mesure.drapeau_mesure or "").strip() for mesure in mesures if mesure.valeur is not None
    )
    sources = Counter(
        (mesure.drapeau_source or "").strip() for mesure in mesures if mesure.valeur is not None
    )

    return ProfilVariable(
        quantity=element,
        unit=mesures[0].unite if mesures else None,
        couverture=couverture,
        lacunes=lacunes,
        minimum=min(valeurs) if valeurs else None,
        maximum=max(valeurs) if valeurs else None,
        mediane=statistics.median(valeurs) if valeurs else None,
        moyenne=statistics.fmean(valeurs) if valeurs else None,
        ecart_type=statistics.stdev(valeurs) if len(valeurs) > 1 else None,
        moyennes_mensuelles={mois: statistics.fmean(vals) for mois, vals in par_mois.items()},
        drapeaux_qualite={code: n for code, n in drapeaux_qualite.items() if code},
        drapeaux_mesure={code: n for code, n in drapeaux_mesure.items() if code},
        sources={code: n for code, n in sources.items() if code},
        valeurs_rejetees=sum(n for code, n in drapeaux_qualite.items() if code),
    )


def _couverture(jours: set[date]) -> Couverture:
    """La couverture d'un ensemble de jours observés."""
    if not jours:
        return Couverture(debut=None, fin=None, jours_attendus=0, jours_observes=0, taux=0.0)
    debut = min(jours)
    fin = max(jours)
    attendus = (fin - debut).days + 1
    return Couverture(
        debut=debut,
        fin=fin,
        jours_attendus=attendus,
        jours_observes=len(jours),
        taux=len(jours) / attendus if attendus else 0.0,
    )


def _lacunes(jours: set[date]) -> tuple[Lacune, ...]:
    """Les trous d'un ensemble de jours, du plus ancien au plus récent."""
    if not jours:
        return ()
    ordonnes = sorted(jours)
    trous: list[Lacune] = []
    for precedent, suivant in itertools.pairwise(ordonnes):
        ecart = (suivant - precedent).days
        if ecart > 1:
            trous.append(
                Lacune(
                    debut=precedent + timedelta(days=1),
                    fin=suivant - timedelta(days=1),
                    longueur=ecart - 1,
                )
            )
    return tuple(trous)


def autocorrelation(series: Sequence[float], *, lags: int = 10) -> tuple[float, ...]:
    """L'autocorrélation d'une série, aux retards demandés.

    Le retard 0 vaut 1 par convention ; les retards suivants sont les
    corrélations usuelles. Une série trop courte pour un retard n'est pas
    notée `NaN` : elle est **absente** de la sortie, parce qu'une absence de
    mesure et une mesure de l'absence ne sont pas la même chose.
    """
    valeurs = np.asarray([v for v in series if v is not None], dtype=np.float64)
    n = valeurs.size
    if n < 2:
        return ()
    centre = valeurs - valeurs.mean()
    denom = float(np.dot(centre, centre))
    if denom <= 0.0:
        return ()
    resultat: list[float] = []
    for retard in range(1, lags + 1):
        if n <= retard:
            break
        num = float(np.dot(centre[retard:], centre[:-retard]))
        resultat.append(num / denom)
    return tuple(resultat)


def structure_temporelle(
    notes: Sequence[tuple[Observation, float]],
    *,
    lags: int = 10,
) -> tuple[tuple[float, ...], EffectiveSampleSize | None]:
    """La structure temporelle des anomalies : autocorrélation et taille effective.

    La taille effective d'échantillon est le nombre de jours **indépendants**
    que la série contient : c'est lui, et non le nombre de jours, qui
    dimensionne la puissance d'un test sur cette série.
    """
    series = [score for _, score in notes]
    auto = autocorrelation(series, lags=lags)
    if len(series) < 2:
        return auto, None
    try:
        taille = effective_sample_size(series)
    except ValueError:
        return auto, None
    return auto, taille


def coupure_moyenne(notes: Sequence[tuple[Observation, float]]) -> BreakResult | None:
    """La rupture de moyenne la plus probable dans la série d'anomalies.

    Le test est celui du dépôt (`OLS-CUSUM`, Ploberger & Krämer) : la
    variance de long terme est celle de Bartlett, plus prudente sous
    autocorrélation — ce qui est précisément le cas d'une série d'anomalies
    quotidiennes. `None` quand le test n'est pas applicable : une série trop
    courte ou constante ne produit pas de rupture, elle produit une absence
    de rupture.
    """
    series = [score for _, score in notes]
    if len(series) < 16:
        return None
    resultat = cusum_break_test(series, lags=None)
    if resultat.n_observations == 0:
        return None
    return resultat


def explicer_drapaux(compteur: dict[str, int], table: dict[str, str]) -> dict[str, str]:
    """Le compte des drapeaux, avec la signification que NCEI leur donne."""
    return {code: table.get(code, "signification non publiée") for code in compteur}


__all__ = [
    "Couverture",
    "Lacune",
    "ProfilVariable",
    "autocorrelation",
    "coupure_moyenne",
    "explicer_drapaux",
    "profil_variable",
    "structure_temporelle",
]
