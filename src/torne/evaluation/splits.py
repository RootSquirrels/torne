"""Découpages temporels stricts : le passé n'apprend jamais du futur.

Une seule règle gouverne ce module : la séparation est **strictement
chronologique**. `train_end == test_start`, aucun recouvrement, aucun
mélange, aucun tirage aléatoire, aucun ordre réordonné. Un point d'indice `i`
n'entre dans un bloc d'entraînement que si `i < train_end`.

Le walk-forward est **cumulatif** : le bloc d'entraînement de chaque pli
contient *toutes* les valeurs antérieures, pas une fenêtre glissante. C'est ce
qui permet à un modèle de rafraîchir son état sans jamais voir la période
test.

Ces découpages sont posés ici, et nulle part ailleurs : aucun service, aucun
registre, aucun moteur. Une fonction suffit.

**Une absence reste une absence dans les blocs.** Une série peut porter des
absences (`None`) : elles sont découpées comme les autres points, à leur
place, et ne sont jamais remplacées par un zéro ni par une valeur inventée.
Un bloc d'entraînement montre donc au modèle les trous qu'il doit traiter.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Split:
    """Découpage chronologique d'une série en deux blocs disjoints.

    `train` couvre les indices `[0, train_end)`, `test` couvre les indices
    `[test_start, test_end)`. L'invariant `train_end == test_start` garantit
    qu'aucun point n'appartient aux deux blocs, et qu'aucun point du test
    n'est antérieur au train.

    Les blocs portent les absences telles quelles (`None`) : un bloc n'invente
    aucune valeur, et son découpage reste rejouable.
    """

    train: tuple[float | None, ...]
    test: tuple[float | None, ...]
    train_end: int
    test_start: int
    test_end: int


@dataclass(frozen=True, slots=True)
class Fold:
    """Un pli de walk-forward : un bloc d'entraînement et le bloc qui suit.

    Un pli **est** une découpe (`Split`) numérotée : il n'en duplique pas les
    champs. Les attributs de la découpe restent accessibles tels quels.

    Mêmes invariants qu'un `Split` : `train_end == test_start`, et le train
    contient toutes les valeurs antérieures au test.
    """

    index: int
    split: Split

    @property
    def train(self) -> tuple[float | None, ...]:
        return self.split.train

    @property
    def test(self) -> tuple[float | None, ...]:
        return self.split.test

    @property
    def train_end(self) -> int:
        return self.split.train_end

    @property
    def test_start(self) -> int:
        return self.split.test_start

    @property
    def test_end(self) -> int:
        return self.split.test_end


def temporal_split(
    values: Sequence[float | None],
    *,
    train_size: int | None = None,
    train_fraction: float | None = None,
) -> Split:
    """Découpe une série en un bloc d'entraînement puis un bloc de test.

    Le seuil est **explicite** : `train_size` (nombre de points) ou
    `train_fraction` (part de la série), jamais les deux, jamais aucun. Pour
    une fraction, le seuil retenu est la partie entière de
    `len(values) * train_fraction` : la convention est écrite, pas implicite.

    Le découpage refuse un bloc vide : il doit rester au moins un point
    d'entraînement et au moins un point de test.
    """
    total = len(values)
    if train_size is not None and train_fraction is not None:
        raise ValueError(
            "train_size et train_fraction sont exclusifs : un découpage n'a qu'un seul seuil"
        )
    if train_size is None and train_fraction is None:
        raise ValueError("un découpage exige train_size ou train_fraction")

    if train_size is None:
        fraction = train_fraction
        if fraction is None or not 0.0 < fraction < 1.0:
            raise ValueError("train_fraction doit appartenir à l'intervalle ]0, 1[")
        train_end = int(total * fraction)
    else:
        if train_size < 1:
            raise ValueError("train_size doit valoir au moins 1")
        train_end = train_size

    if not 1 <= train_end <= total - 1:
        raise ValueError(
            "le découpage doit laisser au moins un point d'entraînement "
            f"et un point de test : train_end={train_end}, longueur={total}"
        )

    return Split(
        train=tuple(values[:train_end]),
        test=tuple(values[train_end:]),
        train_end=train_end,
        test_start=train_end,
        test_end=total,
    )


def walk_forward(
    values: Sequence[float | None], *, initial_size: int, step: int
) -> tuple[Fold, ...]:
    """Construit des pli cumulatifs strictement chronologiques.

    Le pli `i` s'entraîne sur `values[:initial_size + i * step]` et se teste
    sur les `step` points suivants. Les blocs de test sont contigus : le
    premier pli commence à `initial_size`, le suivant à `initial_size + step`.

    Un reste de série plus court que `step` à la fin n'est **pas** évalué :
    aucun pli partiel n'est créé, car le prédicteur doit produire exactement
    `step` valeurs. Ce reste est visible dans le rapport, dont le `test_end`
    s'arrête au dernier pli complet.
    """
    total = len(values)
    if initial_size < 1:
        raise ValueError("initial_size doit valoir au moins 1")
    if step < 1:
        raise ValueError("step doit valoir au moins 1")
    if initial_size >= total:
        raise ValueError(
            f"la série ne permet aucun pli : initial_size={initial_size}, longueur={total}"
        )
    if initial_size + step > total:
        raise ValueError(
            f"la série ne permet aucun pli complet : initial_size={initial_size} "
            f"et step={step} dépassent la longueur {total}"
        )

    folds: list[Fold] = []
    test_start = initial_size
    while test_start + step <= total:
        test_end = test_start + step
        folds.append(
            Fold(
                index=len(folds),
                split=Split(
                    train=tuple(values[:test_start]),
                    test=tuple(values[test_start:test_end]),
                    train_end=test_start,
                    test_start=test_start,
                    test_end=test_end,
                ),
            )
        )
        test_start = test_end
    return tuple(folds)


__all__ = ["Fold", "Split", "temporal_split", "walk_forward"]
