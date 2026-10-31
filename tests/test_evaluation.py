"""Tests de l'évaluation : découpage, anti-fuite, métriques, reproductibilité.

La forme canonique du test d'anti-fuite est celle du store synthétique
(`boree/tests/fabrique.py`, INV-32/33) : **la valeur d'un point est son propre
index**, de sorte qu'une fuite temporelle se lise comme un nombre faux et non
comme une subtilité de code.

Les valeurs attendues des métriques sont recalculées à la main et écrites
explicitement : elles ne sont pas produites par la fonction testée.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from torne.contracts.validity import PointValidity
from torne.evaluation.baselines import drift_forecast, mean_forecast, persistence_forecast
from torne.evaluation.metrics import bias, coverage, evaluate_all, mae, rmse
from torne.evaluation.report import evaluate_walk_forward
from torne.evaluation.splits import temporal_split, walk_forward

INSTANT = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)


def serie_anti_fuite(longueur: int) -> tuple[float, ...]:
    """Série synthétique anti-fuite : la valeur d'un point est son propre index.

    Forme canonique du store synthétique : une fuite temporelle se lit alors
    comme un **nombre faux** (une valeur trop grande), pas comme une
    subtilité de code.
    """
    return tuple(float(index) for index in range(longueur))


def prevoir(train: tuple[float, ...]) -> tuple[float, ...]:
    """Prédicteur de test : reconduit la dernière valeur du bloc d'entraînement."""
    return (train[-1],) * 2


def prevoir_pas(pas: int) -> Callable[[tuple[float, ...]], tuple[float, ...]]:
    """Prédicteur qui renvoie un nombre de valeurs égal au pas du pli.

    Les plis de pas différents n'exigent pas le même nombre de prévisions :
    le prédicteur doit s'ajuster, sinon l'évaluation le refuse.
    """

    def predicteur(train: tuple[float, ...]) -> tuple[float, ...]:
        return (0.0,) * pas

    return predicteur


def prevoir_sans_absence(train: tuple[float | None, ...]) -> tuple[float, ...]:
    """Prédicteur qui ajuste sur les seules valeurs observées du bloc.

    Il montre ce que doit faire un modèle devant une série incomplète : ne
    pas lire un zéro à la place d'une absence.
    """
    observees = [valeur for valeur in train if valeur is not None]
    return (observees[-1],) * 2


def pertes_autocorrelees(longueur: int) -> tuple[float, ...]:
    """Pertes autocorrélées, construites sans hasard.

    La série est une sinusoïde lente : les pertes consécutives sont très
    corrélées, comme le sont les erreurs de marche avant.
    """
    return tuple(math.sin(0.2 * index) for index in range(longueur))


def variance_hac(pertes: tuple[float, ...], lag: int) -> float:
    """Variance de long terme HAC, recalculée ici sans l'implémentation du dépôt.

    `gamma_0 + 2 * somme_{k=1..lag} (1 - k/(lag+1)) * gamma_k`, avec les
    covariances estimées en 1/n (Newey & West 1987, noyau de Bartlett).
    """
    n = len(pertes)
    moyenne = math.fsum(pertes) / n
    ecarts = tuple(perte - moyenne for perte in pertes)
    total = math.fsum(ecart * ecart for ecart in ecarts) / n
    for k in range(1, min(lag, n - 1) + 1):
        covariance = math.fsum(ecarts[index] * ecarts[index - k] for index in range(k, n)) / n
        total += 2.0 * (1.0 - k / (lag + 1.0)) * covariance
    return total


def fenetre_bartlett(n: int) -> int:
    """Fenêtre de Newey & West (1994) : `floor(4 (n / 100)^(2/9))`."""
    return math.floor(4.0 * (n / 100.0) ** (2.0 / 9.0))


# --- Découpages -------------------------------------------------------------


def test_temporal_split_par_train_size_est_strictement_chronologique():
    valeurs = serie_anti_fuite(10)
    coupe = temporal_split(valeurs, train_size=4)
    assert coupe.train == (0.0, 1.0, 2.0, 3.0)
    assert coupe.test == (4.0, 5.0, 6.0, 7.0, 8.0, 9.0)
    assert coupe.train_end == 4
    assert coupe.test_start == 4
    assert coupe.test_end == 10


def test_temporal_split_par_fraction_est_strictement_chronologique():
    valeurs = serie_anti_fuite(10)
    coupe = temporal_split(valeurs, train_fraction=0.4)
    # le seuil retenu est la partie entière de 10 * 0.4
    assert coupe.train_end == 4
    assert coupe.test_start == 4
    assert coupe.train == valeurs[:4]
    assert coupe.test == valeurs[4:]


def test_temporal_split_ne_melange_rien():
    valeurs = serie_anti_fuite(10)
    coupe = temporal_split(valeurs, train_size=6)
    assert len(coupe.train) == coupe.train_end
    assert len(coupe.test) == coupe.test_end - coupe.test_start
    assert coupe.train_end == coupe.test_start
    assert coupe.train[-1] < coupe.test[0]


def test_temporal_split_refuse_deux_seuils():
    with pytest.raises(ValueError, match="exclusifs"):
        temporal_split(serie_anti_fuite(10), train_size=4, train_fraction=0.4)


def test_temporal_split_refuse_l_absence_de_seuil():
    with pytest.raises(ValueError, match="train_size ou train_fraction"):
        temporal_split(serie_anti_fuite(10))


def test_temporal_split_refuse_un_bloc_de_test_vide():
    with pytest.raises(ValueError, match="au moins un point"):
        temporal_split(serie_anti_fuite(4), train_size=4)


def test_temporal_split_refuse_un_bloc_d_entrainement_vide():
    with pytest.raises(ValueError, match="train_size doit valoir au moins 1"):
        temporal_split(serie_anti_fuite(4), train_size=0)


# --- Walk-forward -----------------------------------------------------------


def test_walk_forward_chaque_pli_a_train_end_egal_test_start():
    valeurs = serie_anti_fuite(10)
    plis = walk_forward(valeurs, initial_size=4, step=2)
    assert len(plis) == 3
    for pli in plis:
        assert pli.train_end == pli.test_start
        assert pli.test_end - pli.test_start == 2
        assert pli.test == valeurs[pli.test_start : pli.test_end]


def test_walk_forward_le_train_est_strictement_anterieur_au_test():
    for pli in walk_forward(serie_anti_fuite(10), initial_size=4, step=2):
        # les valeurs sont les index : la valeur dit de quel point elle vient
        assert max(pli.train) < pli.test_start
        assert min(pli.test) >= pli.test_start


def test_walk_forward_le_train_cumulatif_contient_toutes_les_valeurs_anterieures():
    valeurs = serie_anti_fuite(10)
    for pli in walk_forward(valeurs, initial_size=4, step=2):
        # un train cumulatif, pas une fenêtre glissante
        assert pli.train == valeurs[: pli.train_end]
        assert len(pli.train) == pli.train_end


def test_walk_forward_refuse_une_serie_sans_pli_complet():
    with pytest.raises(ValueError, match="aucun pli"):
        walk_forward(serie_anti_fuite(3), initial_size=2, step=5)


# --- Anti-fuite par la donnée -----------------------------------------------


def test_anti_fuite_aucun_point_du_test_n_entra_dans_un_train():
    valeurs = serie_anti_fuite(10)
    for pli in walk_forward(valeurs, initial_size=4, step=2):
        assert pli.train == valeurs[: pli.train_end]
        assert pli.test == valeurs[pli.test_start : pli.test_end]
        # toute valeur du train est antérieure au début du test
        assert max(pli.train) < pli.test_start


def test_le_controle_anti_fuite_detecte_une_fuite_construite():
    """Le contrôle n'est pas vide : un train qui déborde sur le test serait vu."""
    valeurs = serie_anti_fuite(10)
    fuite = valeurs[:6]  # un train qui englobe la période test
    assert max(fuite) >= 4


def test_modifier_le_futur_ne_change_pas_les_previsions_passees():
    valeurs = serie_anti_fuite(12)
    modifies = [*valeurs[:6], *(-1000.0 - index for index in range(6, 12))]
    plis_a = walk_forward(valeurs, initial_size=4, step=2)
    plis_b = walk_forward(modifies, initial_size=4, step=2)
    assert len(plis_a) == len(plis_b)
    for pli_a, pli_b in zip(plis_a, plis_b, strict=True):
        if pli_a.train_end > 6:
            continue  # ce pli voit le futur modifié : il doit changer
        assert pli_a.train == pli_b.train
        assert prevoir(pli_a.train) == prevoir(pli_b.train)
        assert persistence_forecast(pli_a.train, 2) == persistence_forecast(pli_b.train, 2)
        assert mean_forecast(pli_a.train, 2) == mean_forecast(pli_b.train, 2)
        assert drift_forecast(pli_a.train, 2) == drift_forecast(pli_b.train, 2)


def test_les_plis_anterieurs_sont_inchanges_apres_modification_du_futur():
    valeurs = serie_anti_fuite(12)
    modifies = [*valeurs[:6], *(-1000.0 - index for index in range(6, 12))]
    blocs_a: list[tuple[float, ...]] = []
    blocs_b: list[tuple[float, ...]] = []

    def predicteur_a(train: tuple[float, ...]) -> tuple[float, ...]:
        blocs_a.append(train)
        return prevoir(train)

    def predicteur_b(train: tuple[float, ...]) -> tuple[float, ...]:
        blocs_b.append(train)
        return prevoir(train)

    evaluate_walk_forward(valeurs, predicteur_a, initial_size=4, step=2, now=INSTANT)
    evaluate_walk_forward(modifies, predicteur_b, initial_size=4, step=2, now=INSTANT)

    assert len(blocs_a) == len(blocs_b)
    for bloc_a, bloc_b in zip(blocs_a, blocs_b, strict=True):
        if len(bloc_a) <= 6:
            assert bloc_a == bloc_b
            # la prédiction du passé ne dépend que du train : elle est inchangée
            assert prevoir(bloc_a) == prevoir(bloc_b)


def test_une_reference_ajustee_sur_le_train_ignore_la_periode_test():
    valeurs = serie_anti_fuite(10)
    pli = walk_forward(valeurs, initial_size=4, step=2)[0]
    # la période test n'existe pas : la série s'arrête à la fin du train
    sans_test = valeurs[: pli.train_end]
    for reference in (persistence_forecast, mean_forecast, drift_forecast):
        assert reference(pli.train, 2) == reference(sans_test, 2)


# --- Métriques --------------------------------------------------------------


def test_rmse_mae_et_biais_sont_recalcules_a_la_main():
    """actual = (1, 2, 3), predicted = (1, 2, 5) ; erreurs signées (0, 0, -2)."""
    # RMSE = sqrt((0 + 0 + 4) / 3) = sqrt(4/3)
    assert rmse((1, 2, 3), (1, 2, 5)).value == pytest.approx(math.sqrt(4 / 3))
    # MAE = (0 + 0 + 2) / 3 = 2/3
    assert mae((1, 2, 3), (1, 2, 5)).value == pytest.approx(2 / 3)
    # biais = (0 + 0 - 2) / 3 = -2/3
    assert bias((1, 2, 3), (1, 2, 5)).value == pytest.approx(-2 / 3)


def test_biais_d_un_ecart_unique_vaut_moins_un_tiers():
    """actual = (1, 2, 3), predicted = (1, 2, 4) ; erreurs (0, 0, -1)."""
    assert bias((1, 2, 3), (1, 2, 4)).value == pytest.approx(-1 / 3)


def test_le_biais_est_negatif_quand_le_modele_sur_predit():
    assert bias((1, 2, 3), (2, 3, 4)).value < 0
    assert bias((2, 3, 4), (1, 2, 3)).value > 0


def test_couverture_compte_les_points_couverts():
    """actual = (1, 2, 3) ; intervalles ((0, 2), (1, 3), (0, 10)).

    1 ∈ [0, 2], 2 ∈ [1, 3] et 3 ∈ [0, 10] : les trois points sont couverts.
    """
    rapport = coverage((1, 2, 3), ((0, 2), (1, 3), (0, 10)))
    assert rapport.value == pytest.approx(1.0)
    assert rapport.n_used == 3
    assert rapport.n_total == 3


def test_couverture_partielle_vaut_deux_tiers():
    """actual = (1, 2, 3) ; intervalles ((0, 2), (1, 3), (0, 2)).

    1 ∈ [0, 2] et 2 ∈ [1, 3] sont couverts, 3 ∉ [0, 2] ne l'est pas : 2/3.
    """
    rapport = coverage((1, 2, 3), ((0, 2), (1, 3), (0, 2)))
    assert rapport.value == pytest.approx(2 / 3)
    assert rapport.n_used == 3


def test_exclusions_comptees_qualifient_chaque_point_ecarte():
    validite = [
        PointValidity.VALID,
        PointValidity.MISSING,
        PointValidity.INVALID,
        PointValidity.OUT_OF_DOMAIN,
        PointValidity.VALID,
    ]
    rapport = rmse((1, None, 3, 4, 5), (1, None, 0, 0, 5), validite)
    assert rapport.n_total == 5
    assert rapport.n_used == 2
    assert rapport.n_missing == 1
    assert rapport.n_invalid == 1
    assert rapport.n_out_of_domain == 1
    total = rapport.n_used + rapport.n_missing + rapport.n_invalid + rapport.n_out_of_domain
    assert total == rapport.n_total
    # seuls les points valides entrent dans le calcul : erreurs (0, 0) → RMSE nul
    assert rapport.value == pytest.approx(0.0)


def test_une_absence_n_est_pas_un_zero():
    validite = [PointValidity.VALID, PointValidity.MISSING, PointValidity.VALID]
    rapport = rmse((1, None, 3), (1, None, 5), validite)
    # seuls (1, 1) et (3, 5) entrent : erreurs (0, -2) → RMSE = sqrt(4/2)
    assert rapport.value == pytest.approx(math.sqrt(4 / 2))
    # si le point manquant était traité comme un zéro, l'erreur serait nulle
    # et le RMSE vaudrait sqrt(4/3) : la valeur observée tranche
    assert rapport.value != pytest.approx(math.sqrt(4 / 3))
    assert rapport.n_missing == 1
    assert rapport.n_used == 2


def test_une_metrique_sans_point_valide_vaut_nan_et_non_zero():
    validite = [PointValidity.MISSING, PointValidity.INVALID]
    rapport = rmse((None, 2), (None, 2), validite)
    assert math.isnan(rapport.value)
    assert rapport.n_used == 0
    assert rapport.n_total == 2


def test_evaluate_all_renvoie_les_quatre_metriques():
    rapports = evaluate_all((1, 2, 3), (1, 2, 5), intervals=((0, 2), (1, 3), (0, 10)))
    assert list(rapports) == ["rmse", "mae", "bias", "coverage"]


def test_les_sequences_de_longueurs_differentes_sont_refusees():
    with pytest.raises(ValueError, match="un point chacun"):
        rmse((1, 2, 3), (1, 2))


def test_une_validite_de_longueur_incoherente_est_refusee():
    with pytest.raises(ValueError, match="un état par point"):
        rmse((1, 2, 3), (1, 2, 3), [PointValidity.VALID])


# --- Absences : l'interface, la cohérence, le comptage ----------------------


def test_une_serie_comportant_une_absence_est_acceptee_par_les_metriques():
    """Une absence est `None` : la métrique l'accepte, la compte, l'ignore."""
    rapport = rmse((1.0, None, 3.0), (1.0, 2.0, 5.0))

    assert rapport.n_total == 3
    assert rapport.n_used == 2
    assert rapport.n_missing == 1
    # seuls (1, 1) et (3, 5) entrent : erreurs (0, -2) → RMSE = sqrt(4/2)
    assert rapport.value == pytest.approx(math.sqrt(4 / 2))


def test_une_absence_n_est_jamais_remplacee_par_un_zero():
    """La valeur observée 0,0 et l'absence donnent des résultats distincts.

    Si l'absence était convertie en zéro, les deux appels seraient
    confondus. Ici, ils ne le sont pas : c'est le point manquant qui les
    sépare, et lui seul.
    """
    observee = rmse((1.0, 0.0, 3.0), (1.0, 2.0, 5.0))
    absente = rmse((1.0, None, 3.0), (1.0, 2.0, 5.0))

    assert observee.n_missing == 0
    assert observee.n_used == 3
    assert absente.n_missing == 1
    assert absente.n_used == 2
    # recalculs à la main : erreurs (0, -2, -2) → RMSE sqrt(8/3) ; (0, -2) → sqrt(2)
    assert observee.value == pytest.approx(math.sqrt(8 / 3))
    assert absente.value == pytest.approx(math.sqrt(4 / 2))
    assert observee.value != pytest.approx(absente.value)


def test_l_absence_et_le_zero_ne_se_confondent_dans_chaque_metrique():
    """Le contrôle vaut pour le RMSE, le MAE et le biais."""
    for calcul in (rmse, mae, bias):
        observee = calcul((1.0, 0.0, 3.0), (1.0, 2.0, 5.0))
        absente = calcul((1.0, None, 3.0), (1.0, 2.0, 5.0))
        assert observee.value != pytest.approx(absente.value)
        assert observee.n_missing == 0
        assert absente.n_missing == 1


def test_une_absence_declaree_valide_est_refusee():
    """Absent et valide à la fois : l'incohérence est refusée, pas écartée."""
    with pytest.raises(ValueError, match="incohérence"):
        rmse((1.0, None, 3.0), (1.0, 2.0, 5.0), [PointValidity.VALID] * 3)


def test_une_absence_placee_par_une_valeur_inventee_est_refusee():
    """L'absence se déclare par `None`, jamais par un nombre de remplacement."""
    validite = [PointValidity.VALID, PointValidity.MISSING, PointValidity.VALID]
    with pytest.raises(ValueError, match="jamais par une valeur inventée"):
        rmse((1.0, 2.0, 3.0), (1.0, 2.0, 5.0), validite)


def test_l_invariant_des_compteurs_tient_avec_des_absences():
    """Les quatre compteurs se partagent tous les points, absences comprises."""
    validite = [
        PointValidity.VALID,
        PointValidity.MISSING,
        PointValidity.INVALID,
        PointValidity.OUT_OF_DOMAIN,
        PointValidity.VALID,
    ]
    rapport = rmse((1.0, None, 3.0, 4.0, 5.0), (1.0, None, 0.0, 0.0, 5.0), validite)

    assert rapport.n_total == 5
    assert rapport.n_used == 2
    assert rapport.n_missing == 1
    assert rapport.n_invalid == 1
    assert rapport.n_out_of_domain == 1
    total = rapport.n_used + rapport.n_missing + rapport.n_invalid + rapport.n_out_of_domain
    assert total == rapport.n_total


def test_un_point_sans_intervalle_annonce_est_compte_comme_absent():
    """Pas d'intervalle, pas de couverture à vérifier : le point est absent."""
    rapport = coverage((1.0, None, 3.0), ((0.0, 2.0), None, (0.0, 4.0)))

    assert rapport.n_total == 3
    assert rapport.n_used == 2
    assert rapport.n_missing == 1
    assert rapport.value == pytest.approx(1.0)


def test_un_appel_sans_absence_rend_les_memes_resultats_qu_avant():
    """Compatibilité : une série finie donne exactement les mêmes résultats.

    Les valeurs, les compteurs et les bornes d'incertitude sont épinglés :
    ils viennent de l'implémentation antérieure à l'interface des absences.
    """
    actual = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
    predicted = (1.5, 2.0, 3.5, 3.0, 6.0, 4.5)
    intervalles = ((0.0, 2.0), (1.0, 3.0), (0.0, 4.0), (3.0, 5.0), (5.0, 7.0), (4.0, 6.0))
    rapports = evaluate_all(actual, predicted, intervals=intervalles)

    rapport_rmse = rapports["rmse"]
    assert rapport_rmse.value == pytest.approx(0.8897565210026093)
    assert (rapport_rmse.n_total, rapport_rmse.n_used, rapport_rmse.n_missing) == (6, 6, 0)
    assert rapport_rmse.uncertainty is not None
    assert rapport_rmse.uncertainty.interval is not None
    bas, haut = rapport_rmse.uncertainty.interval
    assert bas == pytest.approx(0.23291132550425797)
    assert haut == pytest.approx(1.2365620274718057)
    assert rapport_rmse.n_effective == pytest.approx(4.03497615262321)

    assert rapports["mae"].value == pytest.approx(0.75)
    assert rapports["bias"].value == pytest.approx(1 / 12)
    assert rapports["coverage"].value == pytest.approx(1.0)
    assert rapports["coverage"].n_used == 6


def test_le_walk_forward_sans_absence_rend_les_memes_resultats_qu_avant():
    """Compatibilité du rapport lui-même : mêmes plis, mêmes métriques."""
    actual = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
    rapport = evaluate_walk_forward(actual, prevoir, initial_size=3, step=2, now=INSTANT)

    assert rapport.metrics["rmse"].value == pytest.approx(1.5811388300841898)
    assert rapport.metrics["mae"].value == pytest.approx(1.5)
    assert rapport.metrics["bias"].value == pytest.approx(1.5)
    assert rapport.metrics["rmse"].n_used == 2
    assert rapport.baseline_metrics["mean"]["rmse"].value == pytest.approx(2.5495097567963922)
    assert rapport.baseline_metrics["drift"]["rmse"].value == pytest.approx(0.0)
    assert rapport.n_excluded == 1
    assert rapport.split.train_end == 3
    assert rapport.split.test_end == 5


# --- Rapport ----------------------------------------------------------------


def test_deux_evaluations_identiques_donnent_le_meme_rapport():
    valeurs = serie_anti_fuite(10)
    rapport_a = evaluate_walk_forward(valeurs, prevoir, initial_size=4, step=2, now=INSTANT)
    rapport_b = evaluate_walk_forward(valeurs, prevoir, initial_size=4, step=2, now=INSTANT)
    assert rapport_a == rapport_b
    assert rapport_a.evaluated_at == INSTANT
    assert dict(rapport_a.metrics) == dict(rapport_b.metrics)
    assert dict(rapport_a.baseline_metrics) == dict(rapport_b.baseline_metrics)


def test_le_rapport_enregistre_la_decoupe_pour_rejeu():
    valeurs = serie_anti_fuite(10)
    rapport = evaluate_walk_forward(valeurs, prevoir, initial_size=4, step=2, now=INSTANT)
    assert rapport.split.train_end == rapport.split.test_start
    assert rapport.split.train == valeurs[: rapport.split.train_end]
    assert rapport.split.test == valeurs[rapport.split.test_start : rapport.split.test_end]
    assert rapport.split.test_end == 10


def test_le_modele_et_les_references_sont_evalues_sur_les_memes_plis():
    rapport = evaluate_walk_forward(
        serie_anti_fuite(10), prevoir, initial_size=4, step=2, now=INSTANT
    )
    assert set(rapport.baseline_metrics) == {"persistence", "mean", "drift"}
    compteurs = {nom: (r.n_total, r.n_used) for nom, r in rapport.metrics.items()}
    for rapports in rapport.baseline_metrics.values():
        for nom, rapport_reference in rapports.items():
            assert (rapport_reference.n_total, rapport_reference.n_used) == compteurs[nom]


def test_les_metriques_des_references_se_recalculent_a_la_main():
    valeurs = serie_anti_fuite(10)
    rapport = evaluate_walk_forward(valeurs, prevoir, initial_size=4, step=2, now=INSTANT)
    plis = walk_forward(valeurs, initial_size=4, step=2)
    actuals: list[float] = []
    prevus: list[float] = []
    for pli in plis:
        actuals.extend(pli.test)
        prevus.extend(persistence_forecast(pli.train, 2))
    attendu = rmse(tuple(actuals), tuple(prevus))
    assert rapport.baseline_metrics["persistence"]["rmse"] == attendu


def test_les_points_ecartes_sont_comptes_dans_le_rapport():
    validite = [PointValidity.VALID] * 10
    validite[5] = PointValidity.MISSING
    # le point absent est absent dans la série : il n'est pas un zéro déguisé
    valeurs = (*serie_anti_fuite(5), None, *serie_anti_fuite(10)[6:])
    rapport = evaluate_walk_forward(
        valeurs, prevoir_sans_absence, initial_size=4, step=2, validity=validite, now=INSTANT
    )
    # trois plis de deux points test : six points, dont un écarté
    assert rapport.metrics["rmse"].n_total == 6
    assert rapport.metrics["rmse"].n_used == 5
    assert rapport.metrics["rmse"].n_missing == 1


def test_le_walk_forward_accepte_une_serie_avec_absence():
    """La série porte une absence : elle est comptée, pas comblée."""
    serie = (1.0, 2.0, None, 4.0, 5.0, 6.0)
    rapport = evaluate_walk_forward(
        serie, prevoir_sans_absence, initial_size=2, step=2, now=INSTANT
    )

    # plis : test = indices 2-3 puis 4-5 ; l'absence est dans le premier test
    assert rapport.metrics["rmse"].n_total == 4
    assert rapport.metrics["rmse"].n_used == 3
    assert rapport.metrics["rmse"].n_missing == 1
    total = rapport.metrics["rmse"].n_used + rapport.metrics["rmse"].n_missing
    assert total == rapport.metrics["rmse"].n_total


def test_le_bloc_d_entrainement_montre_les_absences_au_predicteur():
    """Le prédicteur voit le trou : aucun zéro ne le remplace."""
    blocs: list[tuple[float | None, ...]] = []

    def predicteur(train: tuple[float | None, ...]) -> tuple[float, ...]:
        blocs.append(train)
        return prevoir_sans_absence(train)

    serie = (1.0, 2.0, None, 4.0, 5.0, 6.0)
    evaluate_walk_forward(serie, predicteur, initial_size=2, step=2, now=INSTANT)

    assert blocs[0] == (1.0, 2.0)
    assert blocs[1] == (1.0, 2.0, None, 4.0)
    # l'absence est restée une absence : aucun zéro ne l'a remplacée
    assert 0.0 not in blocs[1]


def test_le_walk_forward_refuse_une_absence_declaree_valide():
    """La cohérence entre la série et l'état déclaré est exigée d'emblée."""
    with pytest.raises(ValueError, match="incohérence"):
        evaluate_walk_forward(
            (1.0, None, 3.0, 4.0),
            prevoir_sans_absence,
            initial_size=2,
            step=2,
            validity=[PointValidity.VALID] * 4,
            now=INSTANT,
        )


def test_les_references_sajustent_sur_les_valeurs_observees():
    """Une absence dans l'historique n'entre pas dans l'ajustement."""
    historique = (2.0, None, 6.0)

    # persistance : la dernière valeur observée (6,0)
    assert persistence_forecast(historique, 1) == (6.0,)
    # moyenne : (2 + 6) / 2 = 4,0 — l'absence n'entre pas comme un zéro
    assert mean_forecast(historique, 1) == (4.0,)
    assert mean_forecast(historique, 1) != mean_forecast((2.0, 0.0, 6.0), 1)
    # dérive : pente (6 - 2) / 2 = 2,0 sur l'écart d'indice, non de nombre
    assert drift_forecast(historique, 1) == (8.0,)


def test_une_reference_refuse_un_bloc_sans_valeur_observee():
    """Un historique entièrement absent n'est pas un historique vide de mesure."""
    with pytest.raises(ValueError, match="sans valeur observée"):
        mean_forecast((None, None), 1)


def test_un_predicteur_qui_renvoie_trop_de_valeurs_est_refuse():
    with pytest.raises(ValueError, match="doit renvoyer 2 valeurs"):
        evaluate_walk_forward(
            serie_anti_fuite(10),
            lambda train: (train[-1],) * 3,
            initial_size=4,
            step=2,
            now=INSTANT,
        )


def test_une_reference_inapplicable_est_signalee():
    with pytest.raises(ValueError, match="dérive"):
        evaluate_walk_forward(serie_anti_fuite(10), prevoir, initial_size=1, step=2, now=INSTANT)


def test_un_horodatage_naif_est_refuse():
    with pytest.raises(ValueError, match="fuseau"):
        evaluate_walk_forward(
            serie_anti_fuite(10),
            prevoir,
            initial_size=4,
            step=2,
            now=datetime(2026, 10, 31, 12, 0),
        )


# --------------------------------------------------------------------------
# Définitions des références
#
# Ces tests épinglent la **définition** de chaque référence, par des valeurs
# calculées à la main et écrites en clair. Sans eux, une référence qui
# renverrait autre chose que ce qu'elle annonce passerait tous les autres
# tests : le test « les métriques des références se recalculent à la main »
# réutilise `persistence_forecast` lui-même, et ne vérifie donc que le
# raccordement, pas la définition.
# --------------------------------------------------------------------------

# Sur cet historique, les trois références donnent trois valeurs distinctes :
# une référence qui confondrait deux définitions serait détectée.
HISTORIQUE = (2.0, 4.0, 6.0)


def test_la_persistance_reconduit_la_derniere_valeur():
    """Persistance : la dernière valeur observée, reconduite sur l'horizon.

    Attendu, écrit à la main : dernier = 6,0 → (6,0 ; 6,0 ; 6,0).
    """
    assert persistence_forecast(HISTORIQUE, 3) == (6.0, 6.0, 6.0)


def test_la_moyenne_reconduit_la_moyenne_de_l_historique():
    """Moyenne : (2 + 4 + 6) / 3 = 4,0 → (4,0 ; 4,0).

    Attendu, écrit à la main : la moyenne n'est ni la dernière valeur (6,0)
    ni la première (2,0).
    """
    assert mean_forecast(HISTORIQUE, 2) == (4.0, 4.0)


def test_la_derive_reconduit_la_derniere_valeur_ajoutee_de_la_pente():
    """Dérive : pente = (6 - 2) / (3 - 1) = 2,0 ; puis 6 + 1x2 = 8,0 et 6 + 2x2 = 10,0.

    Attendu, écrit à la main : la dérive n'est ni la persistance (6,0) ni la
    moyenne (4,0).
    """
    assert drift_forecast(HISTORIQUE, 2) == (8.0, 10.0)


def test_les_trois_references_sont_distinctes_sur_le_meme_historique():
    """Aucune des trois références ne se confond avec une autre.

    C'est ce test qui rend signifiante la comparaison du modèle à ses
    références : si les trois renvoyaient la même chose, la comparaison ne
    comparerait rien.
    """
    assert len({persistence_forecast(HISTORIQUE, 1)[0], mean_forecast(HISTORIQUE, 1)[0]}) == 2
    assert len({persistence_forecast(HISTORIQUE, 1)[0], drift_forecast(HISTORIQUE, 1)[0]}) == 2
    assert len({mean_forecast(HISTORIQUE, 1)[0], drift_forecast(HISTORIQUE, 1)[0]}) == 2


def test_la_pente_de_la_derive_est_calculee_sur_les_extremes():
    """Dérive sur deux points seulement : pente = (4 - 0) / 1 = 4,0.

    Attendu, écrit à la main : 4 + 1x4 = 8,0 puis 4 + 2x4 = 12,0.
    """
    assert drift_forecast((0.0, 4.0), 2) == (8.0, 12.0)


def test_les_references_exigent_un_bloc_non_vide():
    """Une référence ne s'ajuste pas sur un historique vide."""
    for reference in (persistence_forecast, mean_forecast, drift_forecast):
        with pytest.raises(ValueError, match="vide"):
            reference((), 1)


def test_les_references_exigent_un_horizon_d_au_moins_un():
    """Un horizon nul ne veut rien dire."""
    for reference in (persistence_forecast, mean_forecast, drift_forecast):
        with pytest.raises(ValueError, match="horizon"):
            reference(HISTORIQUE, 0)


def test_la_derive_refuse_un_historique_d_un_seul_point():
    """Une dérive n'est pas estimable sur un point : la référence le dit."""
    with pytest.raises(ValueError, match="dérive"):
        drift_forecast((2.0,), 1)


def test_l_horodatage_par_defaut_est_un_instant_aware():
    rapport = evaluate_walk_forward(serie_anti_fuite(10), prevoir, initial_size=4, step=2)
    assert rapport.evaluated_at.tzinfo is not None


def test_with_comparison_attache_un_resultat_calcule_a_ailleurs():
    rapport = evaluate_walk_forward(
        serie_anti_fuite(10), prevoir, initial_size=4, step=2, now=INSTANT
    )
    compare = rapport.with_comparison({"diebold_mariano": {"statistique": -2.1, "p_valeur": 0.03}})
    assert compare.comparison["diebold_mariano"] == {"statistique": -2.1, "p_valeur": 0.03}
    assert rapport.comparison == {}
    assert compare.metrics == rapport.metrics


def test_le_rapport_admet_une_vue_serialisable():
    rapport = evaluate_walk_forward(
        serie_anti_fuite(10), prevoir, initial_size=4, step=2, now=INSTANT
    )
    vue = rapport.as_dict()
    assert vue["model_id"] == ""
    assert vue["evaluated_at"] == "2026-10-31T12:00:00+00:00"
    assert vue["split"]["train_end"] == 4
    assert vue["metrics"]["rmse"]["n_total"] == 6
    assert vue["baseline_metrics"]["persistence"]["rmse"]["n_used"] == 6
    # la vue est ce qu'un enregistreur écrit : elle est JSON-sérialisable
    assert json.loads(json.dumps(vue))["metrics"]["bias"]["n_used"] == 6


# --- Incertitude des métriques ----------------------------------------------


def test_chaque_metrique_porte_son_intervalle_de_confiance():
    """Une métrique n'est plus un nombre nu : elle porte son incertitude."""
    rapport = rmse((1.0, 2.0, 3.0, 4.0), (1.5, 2.0, 3.5, 3.0))

    assert rapport.uncertainty is not None
    assert rapport.uncertainty.form.value == "interval"
    assert rapport.uncertainty.interval is not None
    bas, haut = rapport.uncertainty.interval
    assert bas <= rapport.value <= haut
    assert rapport.n_effective is not None
    assert rapport.n_effective <= rapport.n_used
    assert "taille effective" in rapport.uncertainty.statement


def test_une_metrique_sans_deux_points_n_a_pas_d_intervalle():
    """Moins de deux points : l'incertitude est absente, jamais inventée."""
    rapport = rmse((1.0,), (2.0,))

    assert rapport.uncertainty is None
    assert rapport.n_effective is None
    assert rapport.n_used == 1


def test_la_dependance_temporelle_elargit_l_intervalle_et_reduit_la_taille_effective():
    """Des pertes autocorrélées : l'intervalle IID serait trop serré.

    L'intervalle HAC est comparé à l'intervalle IID que l'on peut recalculer à
    la main : le premier doit être plus large, et la taille effective doit
    tomber sous le nombre de points.
    """
    pertes = pertes_autocorrelees(60)
    rapport = bias(pertes, (0.0,) * len(pertes))

    assert rapport.uncertainty is not None
    assert rapport.uncertainty.interval is not None
    bas, haut = rapport.uncertainty.interval

    n = len(pertes)
    moyenne = math.fsum(pertes) / n
    variance_iid = math.fsum((perte - moyenne) ** 2 for perte in pertes) / n
    demi_largeur_iid = 1.959963984540054 * math.sqrt(variance_iid / n)

    assert (haut - bas) / 2 > demi_largeur_iid
    assert rapport.n_effective is not None
    assert rapport.n_effective < rapport.n_used


def test_l_intervalle_de_confiance_est_celui_de_la_variance_hac():
    """La méthode annoncée est la variance HAC : ce test la recalcule.

    Le recalcul est écrit ici, à la main, sans réutiliser
    `newey_west_variance` ni `bartlett_lags` : un intervalle de bootstrap, ou
    une variance IID, donnerait d'autres bornes.
    """
    pertes = pertes_autocorrelees(60)
    rapport = bias(pertes, (0.0,) * len(pertes))

    n = len(pertes)
    moyenne = math.fsum(pertes) / n
    variance = variance_hac(pertes, fenetre_bartlett(n))
    demi_largeur = 1.959963984540054 * math.sqrt(variance / n)

    assert rapport.uncertainty is not None
    assert rapport.uncertainty.interval is not None
    bas, haut = rapport.uncertainty.interval
    assert bas == pytest.approx(moyenne - demi_largeur, rel=1e-9)
    assert haut == pytest.approx(moyenne + demi_largeur, rel=1e-9)
    # la variance IID, elle, donnerait un intervalle plus serré
    variance_iid = variance_hac(pertes, 0)
    assert (haut - bas) / 2 > 1.959963984540054 * math.sqrt(variance_iid / n)


def test_la_taille_effective_est_n_sur_le_facteur_d_inflation():
    """La taille effective dit le nombre de points indépendants équivalents."""
    pertes = pertes_autocorrelees(60)
    rapport = bias(pertes, (0.0,) * len(pertes))

    n = len(pertes)
    variance = variance_hac(pertes, fenetre_bartlett(n))
    variance_iid = variance_hac(pertes, 0)

    assert rapport.n_effective is not None
    assert rapport.n_effective == pytest.approx(n * variance_iid / variance, rel=1e-9)
    assert rapport.n_effective < n


def test_une_serie_sans_dispersion_donne_un_intervalle_degenere():
    """Aucune dispersion observée, aucune largeur : l'intervalle le dit."""
    rapport = bias((5.0, 5.0, 5.0), (0.0, 0.0, 0.0))

    assert rapport.uncertainty is not None
    assert rapport.uncertainty.interval is not None
    bas, haut = rapport.uncertainty.interval
    assert bas == pytest.approx(5.0)
    assert haut == pytest.approx(5.0)
    assert rapport.n_effective == pytest.approx(3.0)


def test_le_calcul_de_l_incertitude_est_deterministe():
    """Aucune graine n'est employée : deux appels rendent le même intervalle."""
    pertes = pertes_autocorrelees(40)
    premier = bias(pertes, (0.0,) * len(pertes))
    second = bias(pertes, (0.0,) * len(pertes))

    assert premier.uncertainty == second.uncertainty
    assert premier.n_effective == second.n_effective
    assert "HAC" in premier.uncertainty.statement


def test_une_valeur_non_finite_est_refusee_par_la_metrique():
    """Un `NaN` n'est pas une mesure : la métrique le refuse au lieu de rendre `NaN`."""
    with pytest.raises(ValueError, match="n'est pas finie"):
        rmse((1.0, math.nan), (1.0, 2.0))


def test_un_intervalle_de_couverture_non_fini_est_refuse():
    """Une borne infinie n'est pas une borne : elle est refusée."""
    with pytest.raises(ValueError, match="bornes finies"):
        coverage((1.0, 2.0), ((0.0, math.inf), (0.0, 3.0)))


# --- Reproductibilité du rapport --------------------------------------------


def test_le_rapport_permet_de_rejouer_les_plis():
    """Le rapport retient le pas des plis : la décomposition est rejouable."""
    valeurs = serie_anti_fuite(10)
    rapport = evaluate_walk_forward(valeurs, prevoir, initial_size=4, step=2, now=INSTANT)

    assert rapport.step == 2
    plis = walk_forward(valeurs, initial_size=rapport.split.train_end, step=rapport.step)
    assert [pli.test_end for pli in plis] == [6, 8, 10]
    assert rapport.split.test == tuple(valeurs[4:10])


def test_deux_evaluations_de_meme_periode_mais_de_plis_differents_ne_sont_pas_confondues():
    """Série constante : mêmes métriques, mêmes références, plis différents.

    Sans le pas des plis dans le rapport, les deux évaluations seraient
    indiscernables — et le rapport dirait avoir évalué la même chose.
    """
    valeurs = (5.0,) * 10
    rapport_a = evaluate_walk_forward(valeurs, prevoir_pas(2), initial_size=4, step=2, now=INSTANT)
    rapport_b = evaluate_walk_forward(valeurs, prevoir_pas(1), initial_size=4, step=1, now=INSTANT)

    assert rapport_a.metrics == rapport_b.metrics
    assert rapport_a.baseline_metrics == rapport_b.baseline_metrics
    assert rapport_a.split == rapport_b.split
    assert rapport_a.step == 2
    assert rapport_b.step == 1
    assert rapport_a != rapport_b


def test_les_points_de_la_serie_hors_de_tout_pli_sont_comptes():
    """Un point que la découpe n'atteint pas n'est pas perdu en silence."""
    valeurs = serie_anti_fuite(11)
    rapport = evaluate_walk_forward(valeurs, prevoir_pas(3), initial_size=4, step=3, now=INSTANT)

    assert rapport.split.test_end == 10
    assert rapport.n_excluded == 1

    complet = evaluate_walk_forward(
        serie_anti_fuite(10), prevoir_pas(3), initial_size=4, step=3, now=INSTANT
    )
    assert complet.n_excluded == 0
