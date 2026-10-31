"""Tests du transport HTTP : redirections, durée, URL finale, protection des secrets.

Aucun test de ce fichier ne contacte un service distant. Les redirections sont
exercées sur des objets `urllib` construits à la main, et le seul accès réel
est un refus de connexion **local**, immédiat et déterministe.
"""

from __future__ import annotations

import urllib.request

import pytest

from torne.acquisition import AcquisitionRequest, HttpTransport, TransportError
from torne.acquisition.transport import (
    ENTETES_SECRETS,
    _meme_origine,
    _RedirectionSecurisee,
)
from torne.acquisition.transport import (
    HttpTransport as HttpTransportClasse,
)


def _demande(url: str = "https://source.test/observations") -> AcquisitionRequest:
    return AcquisitionRequest(source_id="src-test", url=url, label="essai")


# --------------------------------------------------------------------------
# La protection des identifiants
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url_a", "url_b", "attendu"),
    [
        ("https://source.test/a", "https://source.test/b", True),
        ("https://source.test/a", "http://source.test/b", False),
        ("http://source.test/a", "https://source.test/b", True),
        ("https://source.test/a", "https://autre.test/b", False),
        ("https://source.test/a", "https://source.test:8443/b", False),
    ],
)
def test_meme_origine_distingue_le_changement_de_serveur(url_a: str, url_b: str, attendu: bool):
    """Un changement d'hôte, ou une dégradation, change l'origine."""
    assert _meme_origine(url_a, url_b) is attendu


def test_les_identifiants_ne_suivent_pas_un_changement_de_serveur():
    """Une redirection vers un autre serveur ne doit pas emporter le secret."""
    gestionnaire = _RedirectionSecurisee(max_redirections=5)
    native = urllib.request.Request(
        "https://source.test/observations", headers={"Authorization": "Bearer secret"}
    )

    redirigee = gestionnaire.redirect_request(
        native, None, 302, "Found", {}, "https://autre.test/observations"
    )

    assert redirigee is not None
    assert "Authorization" not in redirigee.headers


def test_les_identifiants_suivent_une_redirection_de_meme_serveur():
    """Une redirection chez le même serveur est légitime : le secret reste."""
    gestionnaire = _RedirectionSecurisee(max_redirections=5)
    native = urllib.request.Request(
        "https://source.test/observations", headers={"Authorization": "Bearer secret"}
    )

    redirigee = gestionnaire.redirect_request(
        native, None, 302, "Found", {}, "https://source.test/observations/v2"
    )

    assert redirigee is not None
    assert redirigee.headers["Authorization"] == "Bearer secret"


def test_une_degradation_https_vers_http_emporte_moins_le_secret():
    """Redescendre en clair n'est pas une origine identique."""
    gestionnaire = _RedirectionSecurisee(max_redirections=5)
    native = urllib.request.Request(
        "https://source.test/observations", headers={"Authorization": "Bearer secret"}
    )

    redirigee = gestionnaire.redirect_request(
        native, None, 302, "Found", {}, "http://source.test/observations"
    )

    assert redirigee is not None
    assert "Authorization" not in redirigee.headers


def test_les_entetes_de_secret_sont_bien_connus():
    """La liste des en-têtes protégés est explicite, pas implicite."""
    assert "authorization" in ENTETES_SECRETS
    assert "cookie" in ENTETES_SECRETS


# --------------------------------------------------------------------------
# Le transport
# --------------------------------------------------------------------------


def test_le_transport_refuse_un_delai_non_positif():
    """Un délai nul ou négatif n'est pas un délai."""
    with pytest.raises(ValueError, match="délai"):
        HttpTransport(timeout=0)


def test_le_transport_refuse_un_nombre_de_redirections_negatif():
    """Rediriger indéfiniment n'est pas une option."""
    with pytest.raises(ValueError, match="redirections"):
        HttpTransport(max_redirects=-1)


def test_le_plafond_de_redirections_est_applique():
    """Le plafond annoncé est celui qui est installé."""
    transport = HttpTransport(max_redirects=2)

    gestionnaire = transport._opener.handlers

    trouve = [h for h in gestionnaire if isinstance(h, _RedirectionSecurisee)]
    assert len(trouve) == 1
    assert trouve[0].max_redirections == 2


def test_une_erreur_de_transport_est_classee():
    """Un schéma que `urllib` ne sait pas traiter est une panne de transport.

    Aucune connexion n'est tentée : le refus est local et immédiat.
    """
    transport = HttpTransport(timeout=2.0)
    demande = AcquisitionRequest(
        source_id="src-test",
        url="ftp://source.test/observations",
        label="essai",
    )

    with pytest.raises(TransportError, match="transport impossible"):
        transport.send(demande)


def test_l_url_effective_porte_les_parametres():
    """Les paramètres sont portés par la demande, jamais concaténés à la main."""
    demande = AcquisitionRequest(
        source_id="src-test",
        url="https://source.test/observations",
        params={"size": "50", "code_station": "O1"},
    )

    assert demande.effective_url == ("https://source.test/observations?code_station=O1&size=50")


def test_une_url_qui_a_deja_une_requete_recoit_le_bon_separateur():
    """Un paramètre s'ajoute à une URL qui en a déjà, sans la casser."""
    demande = AcquisitionRequest(
        source_id="src-test",
        url="https://source.test/observations?cursor=abc",
        params={"size": "50"},
    )

    assert demande.effective_url == ("https://source.test/observations?cursor=abc&size=50")


def test_la_classe_du_transport_est_exposee():
    """Le module et le paquet exposent la même classe."""
    assert HttpTransport is HttpTransportClasse
