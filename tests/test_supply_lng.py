"""Les tests du produit `TORNE · LNG Terminal Intelligence`.

Trois choses sont verifiees, et ce sont les trois qui peuvent mentir :

1. le **decodeur** attribue chaque volume au bon terminal — verifie par le
   controle du total, qui doit refuser un rapport dont le total ne
   correspond pas a la somme des terminaux ;
2. la **conversion** energie-masse est mesuree, et non supposee ;
3. la **marge** est ce qu'elle doit etre : finie quand le terminal sort,
   absente quand il ne sort rien.
"""

from __future__ import annotations

import datetime as dt

import pytest

from torne.contracts.model import ModelInputs, ModelParameters
from torne.supply.enagas import decoder_json
from torne.supply.lng import (
    ModelMargeOperationnelle,
    TerminalDay,
    capacite_cuve_m3,
    marge_temporelle_jours,
    reserve_operationnelle,
    tension,
    tonnes_par_gwh,
)


def _rapport(
    *,
    plantes: dict[str, float] | None = None,
    remplissage: float = 50.0,
) -> dict:
    """Un rapport JSON minimal, avec ses totaux et ses sept grandeurs."""
    if plantes is None:
        plantes = {"BARCELONA": 600.0, "HUELVA": 400.0}

    def serie(valeurs: dict[str, float]) -> dict[str, str]:
        # Le total est la somme des terminaux : c'est ce que fait la source,
        # et c'est ce que le controle verifie.
        somme = sum(valeurs.values())
        return {
            "Total Plantas": f"{somme}",
            **{k: f"{v}" for k, v in valeurs.items()},
        }

    m3 = {k: v * 147.0 for k, v in plantes.items()}
    return {
        "lastDate": "02/06/2026 10:30",
        "gasSystemPPDDataReportPojo": {
            "tankInitialStocksGWh": serie(plantes),
            "tankInitialStocksM3": serie(m3),
            "loadsGNL": serie(dict.fromkeys(plantes, 0.0)),
            "downloadsGNL": serie(dict.fromkeys(plantes, 1000.0)),
            "regasificationGWh": serie(plantes),
            "regasificationM3": serie(m3),
            "cisternLoad": serie(dict.fromkeys(plantes, 10.0)),
            "tankFinalStocksGwh": serie(plantes),
            "tankFinalStocksM3": serie(m3),
            "tankFinalStocksFilling": {
                # Le remplissage n'est pas additif : son total est une moyenne.
                "Total Plantas": f"{remplissage}",
                **dict.fromkeys(plantes, f"{remplissage}"),
            },
        },
    }


class TestDecodeur:
    """Le decodeur attribue au bon terminal, et refuse un rapport casse."""

    def test_attribue_chaque_volume_a_son_terminal(self) -> None:
        lecture = decoder_json(_rapport(), dt.date(2026, 6, 1))
        assert lecture is not None
        assert lecture.jour_gaz == dt.date(2026, 6, 1)
        assert lecture.date_publication == dt.datetime(2026, 6, 2, 10, 30, tzinfo=dt.UTC)
        par_nom = {t.terminal: t for t in lecture.terminaux}
        assert set(par_nom) == {"BARCELONA", "HUELVA"}
        # Le stock final vaut 147 m3 par GWh, et le remplissage est un pourcentage.
        assert par_nom["BARCELONA"].stock_final_m3 == pytest.approx(600.0 * 147.0)
        assert par_nom["HUELVA"].stock_final_m3 == pytest.approx(400.0 * 147.0)
        assert par_nom["BARCELONA"].remplissage == pytest.approx(0.5)
        # Les citernes sont en GWh : elles sont converties par le facteur mesure.
        assert par_nom["BARCELONA"].sorties_citernes_m3 == pytest.approx(10.0 * 147.0)
        # La cargaison recue est en m3, telle quelle.
        assert par_nom["BARCELONA"].entrees_m3 == pytest.approx(1000.0)

    def test_refuse_un_rapport_ou_le_total_ne_tient_pas(self) -> None:
        rapport = _rapport()
        bloc = rapport["gasSystemPPDDataReportPojo"]
        bloc["tankFinalStocksM3"] = {
            "Total Plantas": "200000.0",
            "BARCELONA": "88200.0",
            "HUELVA": "58800.0",
        }
        assert decoder_json(rapport, dt.date(2026, 6, 1)) is None

    def test_refuse_un_rapport_vide(self) -> None:
        assert decoder_json({}, dt.date(2026, 6, 1)) is None

    def test_mesure_le_facteur_de_conversion(self) -> None:
        lecture = decoder_json(_rapport(), dt.date(2026, 6, 1))
        assert lecture is not None
        assert lecture.facteur_m3_par_gwh == pytest.approx(147.0, rel=1e-6)
        assert lecture.ecart_controle <= 1e-9


class TestConversion:
    """La conversion se mesure, elle ne se suppose pas."""

    def test_une_fois_le_facteur_mesure(self) -> None:
        # 147 m3 liquides par GWh, a 456 kg/m3 : 67,0 tonnes par GWh.
        assert tonnes_par_gwh(147.0) == pytest.approx(67.032, rel=1e-6)

    def test_la_masse_du_stock(self) -> None:
        jour = TerminalDay(
            terminal="BARCELONA",
            jour_gaz=dt.date(2026, 6, 1),
            date_publication=dt.datetime(2026, 6, 2, 10, 30, tzinfo=dt.UTC),
            entrees_m3=0.0,
            regas_m3=1000.0,
            sorties_citernes_m3=500.0,
            reexport_m3=0.0,
            stock_initial_m3=200_000.0,
            stock_final_m3=198_500.0,
            remplissage=0.8,
        )
        assert jour.stock_final_t == pytest.approx(198_500.0 * 0.456)
        assert jour.sortie_m3 == pytest.approx(1500.0)
        assert jour.solde_m3 == pytest.approx(-1500.0)
        assert jour.capacite_cuve_m3 == pytest.approx(198_500.0 / 0.8)
        assert jour.delai_publication_heures == pytest.approx(34.5)


class TestMarge:
    """La marge : finie quand le terminal sort, absente quand il ne sort rien."""

    def test_reserve_au_dessus_du_minimum(self) -> None:
        assert reserve_operationnelle(100_000.0, 30_000.0) == pytest.approx(70_000.0)
        assert reserve_operationnelle(10_000.0, 30_000.0) == 0.0

    def test_marge_en_jours(self) -> None:
        assert marge_temporelle_jours(70_000.0, 10_000.0) == pytest.approx(7.0)
        assert marge_temporelle_jours(70_000.0, 0.0) is None

    def test_tension(self) -> None:
        assert tension(1.0, 3.0) == 1
        assert tension(10.0, 3.0) == 0
        assert tension(None, 3.0) == 0

    def test_capacite_deduite_du_remplissage(self) -> None:
        stock = (100_000.0, 110_000.0, 120_000.0)
        remplissage = (0.5, 0.5, 0.5)
        assert capacite_cuve_m3(stock, remplissage) == pytest.approx(220_000.0)


class TestModele:
    """Le modele : la marge, et son intervalle."""

    def _entrees(self, jours: int = 40) -> ModelInputs:
        return ModelInputs(
            series={
                "stock_final_m3": tuple(200_000.0 - 500.0 * i for i in range(jours)),
                "regas_m3": tuple(4_000.0 for _ in range(jours)),
                "sorties_citernes_m3": tuple(1_000.0 for _ in range(jours)),
                "entrees_m3": tuple(5_000.0 for _ in range(jours)),
                "remplissage": tuple(0.8 for _ in range(jours)),
            }
        )

    def test_produit_une_marge_et_un_intervalle(self) -> None:
        modele = ModelMargeOperationnelle()
        resultat = modele.run(
            self._entrees(),
            ModelParameters(values={"fenetre_jours": 30, "stock_mini_frac": 0.10}),
        )
        assert resultat.output("marge_jours")
        assert len(resultat.output("marge_jours")) == 40
        # La capacite des cuves est deduite du remplissage ; sur une serie
        # decroissante, c'est la mediane de stock/remplissage.
        attendus = sorted((200_000.0 - 500.0 * i) / 0.8 for i in range(40))
        assert resultat.diagnostics["capacilite_cuve_m3"] == pytest.approx(
            (attendus[19] + attendus[20]) / 2, rel=1e-6
        )
        # La reserve vaut le stock moins le minimum technique, qui est une
        # fraction de la capacite deduite.
        capacite = resultat.diagnostics["capacilite_cuve_m3"]
        assert resultat.output("reserve_m3")[0] == pytest.approx(200_000.0 - 0.10 * capacite)
        # Un intervalle est produit pour la marge.
        assert resultat.interval("marge_jours")[0][0] <= resultat.output("marge_jours")[0]
        assert resultat.interval("marge_jours")[0][1] >= resultat.output("marge_jours")[0]

    def test_un_terminal_qui_ne_sort_rien_n_a_pas_de_marge(self) -> None:
        modele = ModelMargeOperationnelle()
        entrees = ModelInputs(
            series={
                "stock_final_m3": (200_000.0, 200_000.0),
                "regas_m3": (0.0, 0.0),
                "sorties_citernes_m3": (0.0, 0.0),
                "entrees_m3": (0.0, 0.0),
                "remplissage": (0.8, 0.8),
            }
        )
        resultat = modele.run(entrees, ModelParameters(values={"fenetre_jours": 30}))
        assert resultat.output("marge_jours") == (0.0, 0.0)
        assert resultat.output("tension") == (0.0, 0.0)

    def test_des_series_de_longueurs_differentes_sont_refusees(self) -> None:
        modele = ModelMargeOperationnelle()
        entrees = ModelInputs(
            series={
                "stock_final_m3": (1.0, 2.0),
                "regas_m3": (1.0,),
                "sorties_citernes_m3": (1.0, 2.0),
                "remplissage": (0.5, 0.5),
            }
        )
        with pytest.raises(ValueError, match="meme longueur"):
            modele.run(entrees, ModelParameters(values={}))
