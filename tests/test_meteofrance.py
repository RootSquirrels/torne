"""La voie Météo-France, et la place du secret dans la chaîne.

Rien dans ce fichier ne touche le réseau : les réponses sont **préparées**.
Le point testé n'est pas la source — c'est le **secret**, et le fait qu'il ne
franchit jamais une frontière qui n'est pas la sienne.
"""

from __future__ import annotations

import json
from pathlib import Path

from torne.acquisition.adapters.meteofrance import (
    CHEMIN_STATIONS,
    CREDENTIAL_REF,
    KEY_HEADER,
    DailyClimatologyAdapter,
    MeteoFranceAdapter,
)
from torne.acquisition.contracts import Conformite, HttpResponse
from torne.acquisition.credentials import (
    EnvironmentToken,
    FichierEnvToken,
    lire_fichier_env,
)

SECRET = "un-jeton-qui-ne-doit-pas-circuler"


def _json(corps: dict) -> HttpResponse:
    return HttpResponse(
        status_code=200,
        headers={"content-type": "application/json"},
        body=json.dumps(corps).encode("utf-8"),
    )


# --------------------------------------------------------------------------
# Le secret : une référence, jamais une valeur
# --------------------------------------------------------------------------


def test_le_jeton_ne_dans_le_requete_consignee():
    """La demande porte un nom, pas la valeur."""
    adaptateur = MeteoFranceAdapter(chemin=CHEMIN_STATIONS)
    demande = adaptateur.initial_request()
    assert demande.credential_ref == CREDENTIAL_REF
    assert not demande.headers
    consigne = {
        "url": demande.url,
        "params": dict(demande.params),
        "credential_ref": demande.credential_ref,
        "headers": dict(demande.headers),
    }
    assert SECRET not in json.dumps(consigne)


def test_un_jeton_de_l_environnement_est_rendu_au_demandeur_legitime():
    fournisseur = EnvironmentToken(CREDENTIAL_REF, variable="TORNE_TEST_JETON")
    import os

    os.environ["TORNE_TEST_JETON"] = SECRET
    try:
        assert fournisseur.credentials_for(CREDENTIAL_REF) == {"Authorization": f"Bearer {SECRET}"}
    finally:
        del os.environ["TORNE_TEST_JETON"]


def test_une_reference_inconnue_ne_recoit_rien():
    """Un fournisseur ne passe pas le jeton d'un autre à une autre origine."""
    fournisseur = EnvironmentToken(CREDENTIAL_REF, variable="TORNE_TEST_JETON")
    import os

    os.environ["TORNE_TEST_JETON"] = SECRET
    try:
        assert fournisseur.credentials_for("autre.source") == {}
    finally:
        del os.environ["TORNE_TEST_JETON"]


def test_une_variable_absente_ne_donne_pas_d_en_tete():
    fournisseur = EnvironmentToken(CREDENTIAL_REF, variable="TORNE_TEST_JETON_ABSENTE")
    assert fournisseur.credentials_for(CREDENTIAL_REF) == {}


def test_un_fichier_env_est_lu_sans_dependance(tmp_path: Path):
    fichier = tmp_path / ".env"
    fichier.write_text(
        "\n".join(
            [
                "# un commentaire",
                "",
                "METEOFRANCE_TOKEN=un-valeur",
                'AUTRE="avec des guillemets"',
                "ligne_sans_egal",
                "ESPACES= Trimme  ",
            ]
        ),
        encoding="utf-8",
    )
    valeurs = lire_fichier_env(fichier)
    assert valeurs["METEOFRANCE_TOKEN"] == "un-valeur"
    assert valeurs["AUTRE"] == "avec des guillemets"
    assert valeurs["ESPACES"] == "Trimme"
    assert "ligne_sans_egal" not in valeurs


def test_l_environnement_prime_sur_le_fichier(tmp_path: Path):
    """Un choix explicite prime sur un commodité local."""
    import os

    fichier = tmp_path / ".env"
    fichier.write_text("TORNE_TEST_JETON=depuis-le-fichier\n", encoding="utf-8")
    os.environ["TORNE_TEST_JETON"] = "depuis-l-environnement"
    try:
        fournisseur = FichierEnvToken(CREDENTIAL_REF, variable="TORNE_TEST_JETON", chemin=fichier)
        assert fournisseur.credentials_for(CREDENTIAL_REF) == {
            "Authorization": "Bearer depuis-l-environnement"
        }
    finally:
        del os.environ["TORNE_TEST_JETON"]


def test_le_fichier_est_utilise_quand_l_environnement_est_vide(tmp_path: Path):
    fichier = tmp_path / ".env"
    fichier.write_text("TORNE_TEST_JETON=depuis-le-fichier\n", encoding="utf-8")
    fournisseur = FichierEnvToken(CREDENTIAL_REF, variable="TORNE_TEST_JETON", chemin=fichier)
    assert fournisseur.credentials_for(CREDENTIAL_REF) == {
        "Authorization": "Bearer depuis-le-fichier"
    }


def test_un_fichier_inexistant_ne_leve_pas(tmp_path: Path):
    fournisseur = FichierEnvToken(
        CREDENTIAL_REF, variable="TORNE_TEST_JETON", chemin=tmp_path / "absent.env"
    )
    assert fournisseur.credentials_for(CREDENTIAL_REF) == {}


# --------------------------------------------------------------------------
# L'adaptateur : ce que la source a dit de la demande
# --------------------------------------------------------------------------


def test_le_refus_de_la_source_est_un_constat_et_non_une_abstention():
    """« Missing Credentials » : la source l'a dit, c'est un fait."""
    adaptateur = MeteoFranceAdapter(chemin=CHEMIN_STATIONS)
    reponse = _json(
        {
            "code": "900902",
            "message": "Missing Credentials",
            "description": "Invalid Credentials. Make sure your API invocation call has a header",
        }
    )
    verdict = adaptateur.verdict_conformite(adaptateur.initial_request(), reponse)
    assert verdict.conformite is Conformite.NON_CONFORME
    assert "900902" in (verdict.motif or "")


def test_un_corps_qui_n_est_pas_du_json_est_viole():
    adaptateur = MeteoFranceAdapter(chemin=CHEMIN_STATIONS)
    reponse = HttpResponse(
        status_code=200, headers={"content-type": "text/html"}, body=b"<html>oops</html>"
    )
    verdict = adaptateur.verdict_conformite(adaptateur.initial_request(), reponse)
    assert verdict.conformite is Conformite.NON_CONFORME


def test_une_reponse_json_sans_forme_attendue_est_conforme():
    """Sans forme déclarée, il n'y a rien à contester : la porte s'ouvre."""
    adaptateur = MeteoFranceAdapter(chemin=CHEMIN_STATIONS)
    reponse = _json({"stations": [{"id": "LILLE"}]})
    verdict = adaptateur.verdict_conformite(adaptateur.initial_request(), reponse)
    assert verdict.conformite is Conformite.CONFORME


def test_une_forme_attendue_absente_est_un_critere_viole():
    adaptateur = MeteoFranceAdapter(chemin=CHEMIN_STATIONS, forme_attendue="features")
    reponse = _json({"stations": []})
    verdict = adaptateur.verdict_conformite(adaptateur.initial_request(), reponse)
    assert verdict.conformite is Conformite.NON_CONFORME
    assert "features" in (verdict.motif or "")


# --------------------------------------------------------------------------
# The API key and the climatological API (two steps: order, then file)
# --------------------------------------------------------------------------

CSV_LILLE = "POSTE;DATE;RR;TN;TX\n59343001;20260901;0.0;9.1;18.2\n59343001;20260902;1.2;8.0;16.5\n"


def _climatology() -> DailyClimatologyAdapter:
    return DailyClimatologyAdapter(
        station="59343001", start="2026-09-01T00:00:00Z", end="2026-09-30T00:00:00Z"
    )


def _csv(body: str) -> HttpResponse:
    return HttpResponse(status_code=201, headers={"content-type": "text/csv"}, body=body.encode())


def test_the_api_key_travels_in_a_header_without_a_scheme(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(f"METEOFRANCE_API_KEY={SECRET}\n", encoding="utf-8")
    provider = FichierEnvToken(
        CREDENTIAL_REF,
        variable="METEOFRANCE_API_KEY",
        chemin=env_file,
        header=KEY_HEADER,
        scheme="",
    )
    assert provider.credentials_for(CREDENTIAL_REF) == {"apikey": SECRET}


def test_the_order_carries_a_reference_and_not_the_key():
    request = _climatology().initial_request()
    assert request.credential_ref == CREDENTIAL_REF
    assert not request.headers
    assert request.params["id-station"] == "59343001"
    assert "DPClim" in request.url


def test_the_file_follows_the_order():
    adapter = _climatology()
    ack = _json({"elaboreProduitAvecDemandeResponse": {"return": "2026043074962"}})
    following = adapter.next_request(adapter.initial_request(), ack)
    assert following is not None
    assert following.params["id-cmde"] == "2026043074962"
    assert following.credential_ref == CREDENTIAL_REF
    verdict = adapter.verdict_conformite(adapter.initial_request(), ack)
    assert verdict.conformite is Conformite.CONFORME


def test_nothing_follows_the_file():
    adapter = _climatology()
    assert adapter.next_request(adapter.initial_request(), _csv(CSV_LILLE)) is None


def test_a_file_of_the_requested_station_is_conformant():
    adapter = _climatology()
    verdict = adapter.verdict_conformite(adapter.initial_request(), _csv(CSV_LILLE))
    assert verdict.conformite is Conformite.CONFORME


def test_a_file_of_another_station_is_a_violation():
    adapter = _climatology()
    other = _csv(CSV_LILLE.replace("59343001", "75114001"))
    verdict = adapter.verdict_conformite(adapter.initial_request(), other)
    assert verdict.conformite is Conformite.NON_CONFORME
    assert "75114001" in (verdict.motif or "")


def test_an_empty_file_is_a_violation():
    adapter = _climatology()
    empty = HttpResponse(status_code=204, headers={}, body=b"")
    verdict = adapter.verdict_conformite(adapter.initial_request(), empty)
    assert verdict.conformite is Conformite.NON_CONFORME


def test_an_html_page_served_as_200_is_not_a_file():
    adapter = _climatology()
    page = HttpResponse(
        status_code=200, headers={"content-type": "text/html"}, body=b"<html>oops</html>"
    )
    verdict = adapter.verdict_conformite(adapter.initial_request(), page)
    assert verdict.conformite is Conformite.NON_CONFORME


def test_la_demande_porte_le_chemin_et_les_parametres():
    adaptateur = MeteoFranceAdapter(
        chemin="/paquet/stations/infrahoraire-6m",
        params={"date": "2026-10-01T18:00:00Z", "format": "geojson"},
    )
    demande = adaptateur.initial_request()
    assert demande.url == (
        "https://public-api.meteofrance.fr/public/DPPaquetObs/paquet/stations/infrahoraire-6m"
    )
    assert demande.params["format"] == "geojson"
    assert demande.credential_ref == CREDENTIAL_REF
    assert adaptateur.declares_exhaustion is False
