"""Les tests de la couche europeenne du gaz : decodeur et indicateurs.

Trois choses sont verifiees, et ce sont les trois qui peuvent mentir :

1. le **decodeur** traduit les unites comme il faut — les stocks d'AGSI+ sont
   en TWh, les flux en GWh/jour, et le controle par le remplissage publie
   le prouve ;
2. une **entree non publiee** reste inconnue : elle ne vaut pas zero ;
3. un **refus deguise en 200** est detecte par l'adaptateur.

La couche **terminal** ajoute quatre verifications :

4. la **marge** se calcule sur la reserve au-dessus du minimum technique, et
   sur le debit **brut** ;
5. le **dechargement derive** de l'equation du stock ne vaut rien au premier
   jour, ni apres un trou dans la serie ;
6. une installation qui ne publie que des valeurs vides (`-`) **ne compte
   pas** comme une installation couverte ;
7. le **scenario de perte** se calcule sur la reserve et le debit, jamais
   sur une difference de pourcentages.
"""

from __future__ import annotations

import datetime as dt

import pytest

from torne.acquisition.adapters.gie import GieAdapter
from torne.acquisition.contracts import HttpResponse
from torne.supply.gas import (
    STOCKAGE_SOUTERRAIN,
    TERMINAL_LNG,
    GasDay,
    buffer_jours,
    concentration_herfindahl,
    degradation,
    dependance_top,
    pression_prelevement,
    taux_reconstitution,
)
from torne.supply.gie import controle_unite, decoder_agsi, decoder_alsi
from torne.supply.terminals import (
    STOCK_MINI_FRAC,
    concentration_geographique,
    concentration_reserve,
    couverture_systeme,
    dechargement_derive,
    degradation_installation,
    dependance_pays,
    etats_reference,
    jours_en_tension,
    marge_installation,
    reserve_operationnelle,
    scenario_perte,
    scenario_perte_site,
    serie_par_installation,
)


def _agsi() -> dict:
    """Un enregistrement AGSI+ : stock et capacite en TWh, flux en GWh/jour."""
    return {
        "name": "Germany",
        "code": "DE",
        "gasDayStart": "2026-09-03",
        "gasDayEnd": "2026-09-04",
        "updatedAt": "2026-10-16 13:38:28",
        "gasInStorage": "132.6277",
        "injection": "351.46",
        "withdrawal": "30.8",
        "workingGasVolume": "246.539",
        "full": "53.8",
        "consumptionFull": "14.67",
        "status": "C",
    }


def _alsi() -> dict:
    """Un enregistrement ALSI : un terminal LNG."""
    return {
        "code": "21Z000000000102A",
        "name": "Terminal LNG",
        "latitude": "43.3641",
        "longitude": "-3.0942",
        "gasDayStart": "2026-09-03",
        "updatedAt": "2026-10-16 13:38:28",
        "inventory": {"gwh": "1234.5", "lng": "89.7"},
        "dtmi": {"gwh": "2000.0", "lng": "145.4"},
        "sendOut": "45.6",
        "dtrs": "60.0",
        "status": "active",
    }


def _alsi_vide() -> dict:
    """Un enregistrement ALSI sans valeur : l'installation ne publie rien.

    C'est le cas reel des installations au statut `N` : la plateforme renvoie
    l'enregistrement, mais tous les champs portent `-`.
    """
    return {
        "code": "21W000000000099F",
        "name": "Terminal sans donnee",
        "gasDayStart": "2026-09-03",
        "updatedAt": "2026-10-16 13:38:28",
        "inventory": {"gwh": "-", "lng": "-"},
        "dtmi": {"gwh": "-", "lng": "-"},
        "sendOut": "-",
        "status": "N",
    }


def _jour_terminal(
    installation: str,
    pays: str,
    jour: dt.date,
    stock: float,
    capacite: float,
    sortie: float,
) -> GasDay:
    """Un etat de terminal, pour les tests d'indicateurs."""
    return GasDay(
        installation=installation,
        pays=pays,
        couche=TERMINAL_LNG,
        jour_gaz=jour,
        date_publication=dt.datetime(2026, 11, 1, tzinfo=dt.UTC),
        stock=stock,
        capacite=capacite,
        entree=None,
        sortie=sortie,
    )


class TestDecodeurAgsi:
    """Le stockage souterrain, traduit en etat."""

    def test_convertit_les_twh_en_gwh(self) -> None:
        etat = decoder_agsi(_agsi())
        assert etat is not None
        assert etat.pays == "DE"
        assert etat.couche == STOCKAGE_SOUTERRAIN
        assert etat.stock == pytest.approx(132_627.7)
        assert etat.capacite == pytest.approx(246_539.0)
        assert etat.entree == pytest.approx(351.46)
        assert etat.sortie == pytest.approx(30.8)

    def test_conserve_le_remplissage_et_l_autonomie_publies(self) -> None:
        etat = decoder_agsi(_agsi())
        assert etat is not None
        assert etat.rempli == pytest.approx(53.8)
        assert etat.autonomie_publiee == pytest.approx(14.67)
        assert etat.jour_gaz == dt.date(2026, 9, 3)
        assert etat.date_publication == dt.datetime(2026, 10, 16, 13, 38, 28, tzinfo=dt.UTC)

    def test_le_controle_d_unite_prouve_la_conversion(self) -> None:
        # 132,6277 TWh / 246,539 TWh = 53,80 %, ce que la source publie.
        assert controle_unite(_agsi()) == pytest.approx(0.0, abs=0.01)

    def test_refuse_un_enregistrement_incomplet(self) -> None:
        assert decoder_agsi({"code": "DE"}) is None


class TestDecodeurAlsi:
    """Le terminal LNG, traduit en etat."""

    def test_le_dechargement_n_est_publie_il_restent_inconnu(self) -> None:
        etat = decoder_alsi(_alsi())
        assert etat is not None
        assert etat.couche == TERMINAL_LNG
        assert etat.entree is None
        assert etat.sortie == pytest.approx(45.6)
        assert etat.stock == pytest.approx(1234.5)
        assert etat.capacite == pytest.approx(2000.0)
        # Une entree non publiee ne vaut pas zero : elle ne vaut rien.
        assert etat.solde is None

    def test_le_pays_vient_de_l_appelant_et_non_du_code(self) -> None:
        # L'element ALSI porte le code EIC du terminal, pas son pays : c'est
        # l'appelant qui sait de quel pays il s'agit.
        etat = decoder_alsi(_alsi(), "ES")
        assert etat is not None
        assert etat.pays == "ES"
        assert etat.installation == "21Z000000000102A"

    def test_lit_le_nom_et_la_position(self) -> None:
        etat = decoder_alsi(_alsi(), "ES")
        assert etat is not None
        assert etat.nom == "Terminal LNG"
        assert etat.latitude == pytest.approx(43.3641)
        assert etat.longitude == pytest.approx(-3.0942)

    def test_une_installation_sans_valeur_n_est_pas_un_etat(self) -> None:
        # Le statut `N` : la plateforme renvoie l'enregistrement, mais sans
        # valeur. L'installation ne doit pas compter comme couverte.
        assert decoder_alsi(_alsi_vide(), "GB") is None


class TestIndicateurs:
    """Les grandeurs derivees, et ce qu'elles signifient."""

    def test_buffer_en_jours(self) -> None:
        assert buffer_jours(1000.0, 2000.0, 100.0) == pytest.approx(10.0)
        assert buffer_jours(1000.0, 2000.0, 0.0) is None

    def test_pression_de_prelevement(self) -> None:
        assert pression_prelevement(150.0, 100.0) == pytest.approx(1.5)
        assert pression_prelevement(50.0, 100.0) == pytest.approx(0.5)
        assert pression_prelevement(50.0, 0.0) is None

    def test_concentration_herfindahl(self) -> None:
        # Uniforme : 1/n ; tout en un seul endroit : 1.
        assert concentration_herfindahl([100.0, 100.0, 100.0, 100.0]) == pytest.approx(0.25)
        assert concentration_herfindahl([100.0, 0.0, 0.0, 0.0]) == pytest.approx(1.0)
        assert concentration_herfindahl([]) == 0.0

    def test_dependance_aux_plus_gros(self) -> None:
        parts = [50.0, 30.0, 15.0, 5.0]
        assert dependance_top(parts, 1) == pytest.approx(0.5)
        assert dependance_top(parts, 3) == pytest.approx(0.95)

    def test_degradation(self) -> None:
        assert degradation([10.0, 8.0, 6.0]) == pytest.approx(-2.0)
        assert degradation([5.0]) is None

    def test_taux_de_reconstitution(self) -> None:
        suite = [
            GasDay(
                installation="DE",
                pays="DE",
                couche=STOCKAGE_SOUTERRAIN,
                jour_gaz=dt.date(2026, 9, 1 + i),
                date_publication=dt.datetime(2026, 10, 16, tzinfo=dt.UTC),
                stock=1000.0 + 100.0 * i,
                capacite=2000.0,
                entree=100.0,
                sortie=0.0,
            )
            for i in range(3)
        ]
        # +100 GWh par jour sur une capacite de 2 000 : 5 % par jour.
        assert taux_reconstitution(suite) == pytest.approx(0.05)


class TestAdaptateur:
    """L'adaptateur voit le refus que le code 200 cache."""

    def _reponse(self, corps: bytes) -> HttpResponse:
        return HttpResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body=corps,
        )

    def test_detecte_le_refus_deguise(self) -> None:
        adaptateur = GieAdapter(debut="2026-09-01", fin="2026-09-03", pays="DE")
        demande = adaptateur.initial_request()
        corps = (
            b'{"last_page":0,"total":0,"dataset":"storage ERROR","error":"access denied",'
            b'"message":"Invalid or missing API key","data":[]}'
        )
        verdict = adaptateur.verdict_conformite(demande, self._reponse(corps))
        assert verdict is not None
        assert not verdict.conforme
        assert "refus" in verdict.motif.lower()

    def test_accepte_une_reponse_avec_des_donnees(self) -> None:
        adaptateur = GieAdapter(debut="2026-09-01", fin="2026-09-03", pays="DE")
        demande = adaptateur.initial_request()
        corps = b'{"dataset":"DE","total":3,"last_page":1,"data":[{"code":"DE"}]}'
        verdict = adaptateur.verdict_conformite(demande, self._reponse(corps))
        assert verdict is not None
        assert verdict.conforme

    def test_la_demande_porte_la_reference_du_secret_pas_le_secret(self) -> None:
        adaptateur = GieAdapter(debut="2026-09-01", fin="2026-09-03", pays="DE")
        demande = adaptateur.initial_request()
        assert demande.credential_ref == "gie.apikey"
        assert "x-key" not in demande.headers
        assert demande.params["country"] == "de"

    def test_la_pagination_commence_a_la_page_1(self) -> None:
        # Les deux plateformes sont base 1 : la page 0 est un alias de la
        # page 1, et une page superieure a `last_page` est renvoyee a
        # l'identique. Demander la page 0 redemanderait la page 1.
        adaptateur = GieAdapter(debut="2026-09-01", fin="2026-09-03", pays="DE")
        demande = adaptateur.initial_request()
        assert demande.params["page"] == "1"

    def test_la_page_suivante_arrete_a_last_page(self) -> None:
        adaptateur = GieAdapter(debut="2026-09-01", fin="2026-09-03", pays="DE")
        demande = adaptateur.initial_request()
        reponse = self._reponse(b'{"last_page":2,"total":50,"data":[{"code":"DE"}]}')
        suivante = adaptateur.next_request(demande, reponse)
        assert suivante is not None
        assert suivante.params["page"] == "2"
        # La page 2 est la derniere : il n'y en a pas de troisieme.
        assert adaptateur.next_request(suivante, reponse) is None

    def test_une_requete_par_installation_exige_le_triplet(self) -> None:
        # ALSI distingue un terminal d'un agregat national par le couple
        # `country` + `company` + `facility` : sans l'exploitant, la
        # plateforme ne sait pas quel terminal est demande.
        adaptateur = GieAdapter(
            debut="2026-06-01",
            fin="2026-06-30",
            pays="ES",
            installation="21W0000000000370",
            company="21X000000001254A",
            plateforme="alsi",
        )
        demande = adaptateur.initial_request()
        assert demande.params["country"] == "es"
        assert demande.params["facility"] == "21W0000000000370"
        assert demande.params["company"] == "21X000000001254A"


class TestCoucheTerminal:
    """La couche terminal : la marge, le dechargement derive, la concentration."""

    def _serie(self, jours: int = 5) -> list[GasDay]:
        """Une serie d'un terminal : 1 000 GWh de stock, 100 GWh/j de sortie."""
        return [
            _jour_terminal(
                "T1",
                "ES",
                dt.date(2026, 6, 1 + i),
                stock=1000.0,
                capacite=2000.0,
                sortie=100.0,
            )
            for i in range(jours)
        ]

    def test_la_reserve_ignore_le_stock_sous_le_minimum_technique(self) -> None:
        # 1 000 de stock, 2 000 de capacite, minimum technique a 10 %.
        assert reserve_operationnelle(1000.0, 2000.0) == pytest.approx(800.0)
        # Sous le minimum technique, la reserve exploitable est nulle.
        assert reserve_operationnelle(100.0, 2000.0) == pytest.approx(0.0)
        assert STOCK_MINI_FRAC == 0.10

    def test_la_marge_divise_la_reserve_par_le_debit_brut(self) -> None:
        # 800 GWh de reserve, 100 GWh/j de sortie : 8 jours de couverture.
        marges = marge_installation(self._serie())
        assert marges[-1] == pytest.approx(8.0)

    def test_une_installation_qui_ne_sort_rien_n_a_pas_de_marge(self) -> None:
        # Une cuve pleine et inactive n'a pas une couverture de zero jour :
        # elle n'a pas de couverture MESURABLE. Publier zero dirait l'inverse
        # de la verite, et c'est le cas reel de plusieurs sites de stockage.
        suite = [
            _jour_terminal("T1", "ES", dt.date(2026, 6, 1 + i), 1000.0, 2000.0, 0.0)
            for i in range(3)
        ]
        assert marge_installation(suite) == [None, None, None]

    def test_un_site_sans_soutirage_n_est_pas_compte_en_tension(self) -> None:
        # Un jour sans couverture mesurable n'est pas un jour de tension :
        # il n'est pas compte, il n'est pas traite comme un zero.
        suite = [
            _jour_terminal("T1", "ES", dt.date(2026, 6, 1 + i), 1000.0, 2000.0, 0.0)
            for i in range(5)
        ]
        assert jours_en_tension(marge_installation(suite)) == 0

    def test_la_degradation_ignore_les_jours_sans_couverture(self) -> None:
        suite = [
            _jour_terminal("T1", "ES", dt.date(2026, 6, 1), 1000.0, 2000.0, 0.0),
            _jour_terminal("T1", "ES", dt.date(2026, 6, 2), 1200.0, 2000.0, 100.0),
            _jour_terminal("T1", "ES", dt.date(2026, 6, 3), 1400.0, 2000.0, 100.0),
        ]
        # Le premier jour n'a pas de couverture : il est ecarte. La
        # degradation se calcule alors sur les deux jours qui en ont une --
        # 20,0 jours puis 18,0 jours, parce que la fenetre traileresse
        # dilue le debit observe.
        assert degradation_installation(suite) == pytest.approx(-2.0)

    def test_le_scenario_de_perte_d_un_site_utilise_le_soutirage_du_pays(self) -> None:
        # Le denominateur est le soutirage PUBLIE DU PAYS : un site qui n'a
        # pas de debit propre ne doit pas faire disparaitre le flux du pays.
        resultat = scenario_perte_site(
            reserve_pays=20_000.0, reserve_site=5_000.0, debit_pays=500.0
        )
        assert resultat is not None
        assert resultat["couverture_avant_jours"] == pytest.approx(40.0)
        assert resultat["couverture_apres_jours"] == pytest.approx(30.0)
        assert resultat["jours_perdus"] == pytest.approx(10.0)
        assert resultat["part_reserve_perdue"] == pytest.approx(0.25)

    def test_un_scenario_sans_soutirage_n_a_pas_de_reponse(self) -> None:
        assert scenario_perte_site(20_000.0, 5_000.0, 0.0) is None

    def test_le_nombre_de_jours_en_tension(self) -> None:
        assert jours_en_tension([0.5, 2.9, 3.1, 10.0]) == 2

    def test_la_degradation_est_negative_quand_la_couverture_se_reserre(self) -> None:
        suite = [
            _jour_terminal("T1", "ES", dt.date(2026, 6, 1 + i), 1200.0 - 100.0 * i, 2000.0, 100.0)
            for i in range(4)
        ]
        assert degradation_installation(suite) == pytest.approx(-1.0)

    def test_le_dechargement_derive_suit_l_equation_du_stock(self) -> None:
        # Le stock tombe de 100 GWh, le terminal en sort 150 : il a donc
        # recu 50 GWh. entree = stock(j) - stock(j-1) + sortie(j).
        suite = [
            _jour_terminal("T1", "ES", dt.date(2026, 6, 1), 1000.0, 2000.0, 50.0),
            _jour_terminal("T1", "ES", dt.date(2026, 6, 2), 900.0, 2000.0, 150.0),
        ]
        derive = dechargement_derive(suite)
        assert derive[0] is None
        assert derive[1] == pytest.approx(50.0)

    def test_le_dechargement_derive_ne_vaut_rien_apres_un_trou(self) -> None:
        suite = [
            _jour_terminal("T1", "ES", dt.date(2026, 6, 1), 1000.0, 2000.0, 50.0),
            _jour_terminal("T1", "ES", dt.date(2026, 6, 4), 900.0, 2000.0, 40.0),
        ]
        derive = dechargement_derive(suite)
        assert derive[1] is None

    def test_la_reference_prend_le_jour_le_plus_recent_et_measure_la_fraicheur(self) -> None:
        series = serie_par_installation(
            [
                _jour_terminal("T1", "ES", dt.date(2026, 6, 30), 1000.0, 2000.0, 50.0),
                _jour_terminal("T2", "FR", dt.date(2026, 6, 28), 500.0, 1000.0, 20.0),
            ]
        )
        reference, etats, fraicheur = etats_reference(series)
        assert reference == dt.date(2026, 6, 30)
        assert etats["T1"].stock == pytest.approx(1000.0)
        assert fraicheur["T1"] == 0
        # T2 est restee deux jours en arriere : il faut le dire.
        assert fraicheur["T2"] == 2

    def test_la_concentration_de_la_reserve(self) -> None:
        etats = {
            "A": _jour_terminal("A", "ES", dt.date(2026, 6, 30), 500.0, 1000.0, 10.0),
            "B": _jour_terminal("B", "FR", dt.date(2026, 6, 30), 300.0, 1000.0, 10.0),
            "C": _jour_terminal("C", "DE", dt.date(2026, 6, 30), 200.0, 1000.0, 10.0),
        }
        concentration = concentration_reserve(etats)
        assert concentration["herfindahl"] == pytest.approx(0.38)
        assert concentration["part_premier"] == pytest.approx(0.5)
        assert concentration["part_trois"] == pytest.approx(1.0)
        assert concentration["total_gwh"] == pytest.approx(1000.0)

    def test_la_dependance_par_pays_separe_le_stock_du_debit(self) -> None:
        etats = {
            "A": _jour_terminal("A", "ES", dt.date(2026, 6, 30), 800.0, 1000.0, 10.0),
            "B": _jour_terminal("B", "FR", dt.date(2026, 6, 30), 200.0, 1000.0, 90.0),
        }
        par_pays = dependance_pays(etats)
        assert par_pays["ES"]["part_stock"] == pytest.approx(0.8)
        assert par_pays["ES"]["part_sortie"] == pytest.approx(0.1)
        # Un pays qui porte la reserve sans faire sortir le flux : c'est une
        # dependance, et elle n'est dans aucune publication.
        assert par_pays["FR"]["part_stock"] == pytest.approx(0.2)
        assert par_pays["FR"]["part_sortie"] == pytest.approx(0.9)

    def test_la_concentration_geographique_est_celle_des_pays(self) -> None:
        etats = {
            "A": _jour_terminal("A", "ES", dt.date(2026, 6, 30), 500.0, 1000.0, 10.0),
            "B": _jour_terminal("B", "ES", dt.date(2026, 6, 30), 300.0, 1000.0, 10.0),
            "C": _jour_terminal("C", "FR", dt.date(2026, 6, 30), 200.0, 1000.0, 10.0),
        }
        par_pays = dependance_pays(etats)
        # Peu concentree au sens du terminal (0,38), tres concentree au sens
        # du pays (0,68) : la lecture politique n'est pas la lecture technique.
        assert concentration_reserve(etats)["herfindahl"] == pytest.approx(0.38)
        assert concentration_geographique(par_pays) == pytest.approx(0.68)

    def test_la_couverture_du_systeme_et_le_scenario_de_perte(self) -> None:
        series = serie_par_installation(
            [
                _jour_terminal("T1", "ES", dt.date(2026, 6, 30), 1000.0, 2000.0, 100.0),
                _jour_terminal("T2", "FR", dt.date(2026, 6, 30), 1000.0, 2000.0, 100.0),
            ]
        )
        reserve, debit, couverture = couverture_systeme(series)
        # 2 x 800 GWh de reserve, 200 GWh/j de sortie : 8 jours.
        assert reserve == pytest.approx(1600.0)
        assert debit == pytest.approx(200.0)
        assert couverture == pytest.approx(8.0)

        scenario = scenario_perte(series, "T1")
        assert scenario is not None
        # Il reste 800 GWh pour 100 GWh/j : 8 jours... non, 800/100 = 8.
        assert scenario["couverture_apres_jours"] == pytest.approx(8.0)
        assert scenario["jours_perdus"] == pytest.approx(0.0)
        assert scenario["part_reserve_perdue"] == pytest.approx(0.5)

    def test_un_scenario_inconnu_ne_vaut_rien(self) -> None:
        series = serie_par_installation(
            [_jour_terminal("T1", "ES", dt.date(2026, 6, 30), 1000.0, 2000.0, 100.0)]
        )
        assert scenario_perte(series, "INCONNU") is None
