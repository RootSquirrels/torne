"""Les tests de la couche europeenne du gaz : decodeur et indicateurs.

Trois choses sont verifiees, et ce sont les trois qui peuvent mentir :

1. le **decodeur** traduit les unites comme il faut — les stocks d'AGSI+ sont
   en TWh, les flux en GWh/jour, et le controle par le remplissage publie
   le prouve ;
2. une **entree non publiee** reste inconnue : elle ne vaut pas zero ;
3. un **refus deguise en 200** est detecte par l'adaptateur.
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
        "gasDayStart": "2026-09-03",
        "updatedAt": "2026-10-16 13:38:28",
        "inventory": {"gwh": "1234.5", "lng": "89.7"},
        "dtmi": {"gwh": "2000.0", "lng": "145.4"},
        "sendOut": "45.6",
        "dtrs": "60.0",
        "status": "active",
    }


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
