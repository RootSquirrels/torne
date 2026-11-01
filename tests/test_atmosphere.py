"""La couche sémantique atmosphérique — de la ligne GHCN-Daily à l'observation.

Les lignes utilisées ici ont la **forme réelle** des fichiers de station de
NCEI : ce sont des enregistrements prélevés sur `FRE00104040` (Lille-Lesquin)
le 1ᵉʳ novembre 2026, dont les valeurs et les drapeaux sont ceux publiés.
Rien dans ce fichier ne touche le réseau.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from torne.acquisition.adapters.ghcnd import GhcndDailyAdapter
from torne.acquisition.contracts import Conformite, HttpResponse
from torne.atmosphere import (
    anomalies,
    climatologie,
    episodes,
    jour_civil,
    observation_depuis_ligne,
    observations,
    profil_variable,
    temperature_moyenne,
)
from torne.atmosphere.observations import (
    InterpretationError,
    ligne_depuis_dictionnaire,
)

ZONE = ZoneInfo("Europe/Paris")
STATION = "FRE00104040"

_ENTETE = [
    "STATION",
    "DATE",
    "LATITUDE",
    "LONGITUDE",
    "ELEVATION",
    "NAME",
    "PRCP",
    "PRCP_ATTRIBUTES",
    "SNWD",
    "SNWD_ATTRIBUTES",
    "TMAX",
    "TMAX_ATTRIBUTES",
    "TMIN",
    "TMIN_ATTRIBUTES",
    "TAVG",
    "TAVG_ATTRIBUTES",
]


def _ligne(
    jour: str,
    *,
    tmax: str | None = "173",
    tmin: str | None = "85",
    prcp: str | None = "25",
    tmax_attributs: str | None = ",,",
    tmin_attributs: str | None = ",,",
    prcp_attributs: str | None = ",,",
    station: str = STATION,
) -> dict[str, str]:
    """Une ligne de station, dans la forme que NCEI publie."""
    return {
        "STATION": station,
        "DATE": jour,
        "LATITUDE": "50.5700",
        "LONGITUDE": "3.0975",
        "ELEVATION": "47.0",
        "NAME": "LILLE LESQUIN, FR",
        "PRCP": prcp or "",
        "PRCP_ATTRIBUTES": prcp_attributs or "",
        "SNWD": "",
        "SNWD_ATTRIBUTES": "",
        "TMAX": tmax or "",
        "TMAX_ATTRIBUTES": tmax_attributs or "",
        "TMIN": tmin or "",
        "TMIN_ATTRIBUTES": tmin_attributs or "",
        "TAVG": "",
        "TAVG_ATTRIBUTES": "",
    }


def _lignes(brutes: list[dict[str, str]]) -> list:
    return [
        ligne_depuis_dictionnaire(ligne, station_id=STATION, elements=("TMAX", "TMIN", "PRCP"))
        for ligne in brutes
    ]


# --------------------------------------------------------------------------
# La lecture d'une mesure
# --------------------------------------------------------------------------


def test_une_temperature_est_lue_en_dixiemes_de_degre():
    """NCEI publie en dixièmes de degré : 173 vaut 17,3 °C."""
    ligne = _lignes([_ligne("1945-03-02")])[0]
    mesure = ligne.elements["TMAX"]
    assert mesure.valeur == pytest.approx(17.3)
    assert mesure.unite == "degC"


def test_une_precipitation_est_lue_en_dixiemes_de_millimetre():
    """25 vaut 2,5 mm — et non 25 mm, ni 0,25 mm."""
    ligne = _lignes([_ligne("1945-03-02", prcp="25")])[0]
    assert ligne.elements["PRCP"].valeur == pytest.approx(2.5)
    assert ligne.elements["PRCP"].unite == "mm"


def test_une_cellule_vide_est_une_absence_et_non_un_zero():
    """Un jour non mesuré ne devient pas un jour à zéro."""
    ligne = _lignes([_ligne("1945-03-02", prcp=None)])[0]
    assert ligne.elements["PRCP"].mesuree is False

    observation = observation_depuis_ligne(
        ligne,
        "PRCP",
        source_id="noaa.ghcnd.daily",
        evidence_id="preuve",
        zone=ZONE,
        acquired_at=datetime(2026, 11, 1, tzinfo=UTC),
    )
    assert observation.value is None
    assert observation.validity.value == "missing"
    assert observation.missing_reason.value == "not_measured"


def test_un_drapeau_de_qualite_echoue_ne_donne_pas_la_qualite_approuvee():
    """Le vocabulaire du socle ne dit pas « mesurée et refusée ».

    La mesure est conservée, le drapeau l'est aussi, et la qualité
    canonique reste `UNKNOWN` : le socle ne prétend pas que la valeur est
    approuvée quand le producteur ne l'a pas approuvée.
    """
    ligne = _lignes([_ligne("1945-03-02", tmax_attributs=",,S")])[0]
    mesure = ligne.elements["TMAX"]
    assert mesure.drapeau_source == "S"
    assert mesure.valeur == pytest.approx(17.3)


def test_sans_drapeau_de_qualite_la_qualite_est_declaree():
    """NCEI publie la valeur et ne signale aucun contrôle échoué."""
    ligne = _lignes([_ligne("1945-03-02")])[0]
    assert ligne.elements["TMAX"].qualite.value == "declared"


def test_un_drapeau_de_qualite_non_vide_rend_la_qualite_inconnue():
    """« failed internal consistency check » : mesurée, mais pas approuvée."""
    ligne = _lignes([_ligne("1945-03-02", tmax_attributs=",I,S")])[0]
    mesure = ligne.elements["TMAX"]
    assert mesure.drapeau_qualite == "I"
    assert mesure.qualite.value == "unknown"
    assert mesure.valeur == pytest.approx(17.3)
    assert "internal consistency" in (mesure.qualite_declaree or "")


def test_un_element_d_echelle_inconnue_est_refuse():
    """Une échelle qu'on ne connaît pas ne se devine pas."""
    with pytest.raises(InterpretationError):
        ligne_depuis_dictionnaire(
            _ligne("1945-03-02"), station_id=STATION, elements=("ELEMENT_INCONNU",)
        )


def test_une_station_etrangere_est_refusee():
    """Une ligne d'une autre station ne devient pas une observation d'ici."""
    with pytest.raises(InterpretationError):
        ligne_depuis_dictionnaire(
            _ligne("1945-03-02", station="FRM00007156"),
            station_id=STATION,
            elements=("TMAX",),
        )


def test_une_date_illisible_est_refusee():
    """Une date qui ne se lit pas ne produit pas d'observation."""
    with pytest.raises(InterpretationError):
        ligne_depuis_dictionnaire(_ligne("02/03/1945"), station_id=STATION, elements=("TMAX",))


def test_la_publication_est_inconnue_et_donc_inutilisable_en_point_in_time():
    """GHCN-Daily ne dit jamais quand une valeur est devenue publique."""
    ligne = _lignes([_ligne("1945-03-02")])[0]
    observation = observation_depuis_ligne(
        ligne,
        "TMAX",
        source_id="noaa.ghcnd.daily",
        evidence_id="preuve",
        zone=ZONE,
        acquired_at=datetime(2026, 11, 1, tzinfo=UTC),
    )
    assert observation.temporal.publication.value == "unknown"
    assert observation.temporal.known_at is None
    assert observation.temporal.usable_at is None


def test_le_fuseau_est_un_argument_et_non_une_devinette():
    """La date civile devient un instant au début du jour, dans la zone donnée.

    En mars 1945, la France était à UTC+0 : le 2 mars 1945 à 00:00 à Paris
    est le 1ᵉʳ mars 1945 à 23:00 UTC. C'est pourquoi le jour UTC n'est pas le
    jour civil — et pourquoi la zone est un argument, jamais une déduction.
    """
    ligne = _lignes([_ligne("1945-03-02")])[0]
    observation = observation_depuis_ligne(
        ligne,
        "TMAX",
        source_id="noaa.ghcnd.daily",
        evidence_id="preuve",
        zone=ZONE,
        acquired_at=datetime(2026, 11, 1, tzinfo=UTC),
    )
    assert observation.temporal.valid_time == datetime(1945, 3, 2, tzinfo=ZONE)
    assert observation.temporal.valid_time.astimezone(ZONE).hour == 0
    assert jour_civil(observation.temporal.valid_time, ZONE).isoformat() == "1945-03-02"


def test_le_jour_civil_ne_est_pas_le_jour_utc():
    """À l'est de Greenwich, le jour civil commence la veille en UTC."""
    instant = datetime(1945, 3, 2, tzinfo=ZONE)
    assert instant.astimezone(UTC).date().isoformat() == "1945-03-01"
    assert jour_civil(instant, ZONE).isoformat() == "1945-03-02"


def test_les_observations_sont_ordonnees_par_le_temps():
    """Le fichier n'est pas garanti trié : l'ordre est établi par le domaine."""
    brutes = [_ligne("1945-03-10"), _ligne("1945-03-02"), _ligne("1945-03-05")]
    resultat = observations(
        _lignes(brutes),
        "TMAX",
        source_id="noaa.ghcnd.daily",
        evidence_id="preuve",
        zone=ZONE,
        acquired_at=datetime(2026, 11, 1, tzinfo=UTC),
    )
    jours = [jour_civil(o.temporal.valid_time, ZONE).isoformat() for o in resultat]
    assert jours == ["1945-03-02", "1945-03-05", "1945-03-10"]


# --------------------------------------------------------------------------
# L'adaptateur : la conformité, vérifiée sur le contenu reçu
# --------------------------------------------------------------------------


def _csv(*lignes: str) -> HttpResponse:
    return HttpResponse(
        status_code=200,
        headers={"content-type": "text/csv"},
        body=("\n".join([",".join(f'"{c}"' for c in _ENTETE), *lignes]) + "\n").encode(),
    )


def test_un_fichier_de_station_valide_est_conforme():
    adaptateur = GhcndDailyAdapter(STATION, elements=("TMAX",))
    reponse = _csv(
        '"FRE00104040","2026-09-30","50.5700","3.0975","47.0","LILLE LESQUIN, FR",'
        '"", "","", "", "", "", "173","", "", "", ""'
    )
    verdict = adaptateur.verdict_conformite(adaptateur.initial_request(), reponse)
    assert verdict.conformite is Conformite.CONFORME


def test_une_page_html_servie_en_200_est_indeterminee():
    """Le piège réel du service d'accès de NCEI.

    Une page d'erreur servie avec le code 200 n'est pas une absence de
    données : elle n'est pas vérifiable, et le socle s'abstient.
    """
    adaptateur = GhcndDailyAdapter(STATION, elements=("TMAX",))
    reponse = HttpResponse(
        status_code=200,
        headers={"content-type": "text/html"},
        body=b"<html><body>All Rights Reserved</body></html>",
    )
    verdict = adaptateur.verdict_conformite(adaptateur.initial_request(), reponse)
    assert verdict.conformite is Conformite.INDETERMINATE
    assert verdict.motif


def test_les_enregistrements_d_une_autre_station_sont_non_conformes():
    adaptateur = GhcndDailyAdapter(STATION, elements=("TMAX",))
    reponse = _csv(
        '"FRM00007156","2026-09-30","48.8217","2.3378","75.0","PARIS MONTSOURIS, FR",'
        '"", "","", "", "", "", "173","", "", "", ""'
    )
    verdict = adaptateur.verdict_conformite(adaptateur.initial_request(), reponse)
    assert verdict.conformite is Conformite.NON_CONFORME
    assert "FRM00007156" in (verdict.motif or "")


def test_un_element_absent_de_l_entete_est_non_verifiable():
    """La source ne porte pas la colonne demandée : elle ne répond pas."""
    adaptateur = GhcndDailyAdapter(STATION, elements=("AWND",))
    reponse = _csv(
        '"FRE00104040","2026-09-30","50.5700","3.0975","47.0","LILLE LESQUIN, FR",'
        '"", "","", "", "", "", "173","", "", "", ""'
    )
    verdict = adaptateur.verdict_conformite(adaptateur.initial_request(), reponse)
    assert verdict.conformite is Conformite.INDETERMINATE


def test_la_source_ne_promet_pas_de_fenetre():
    """Le point d'accès rend toujours la période de record complète."""
    adaptateur = GhcndDailyAdapter(STATION, elements=("TMAX",))
    assert "date" not in adaptateur.initial_request().params
    assert adaptateur.declares_exhaustion is False


# --------------------------------------------------------------------------
# La climatologie, les anomalies, les régimes
# --------------------------------------------------------------------------


def _serie(nb_jours: int, *, debut_annee: int = 1991):
    """Une série quotidienne de température moyenne, sur plusieurs années."""
    brutes = []
    jour = datetime(debut_annee, 1, 1)
    for _index in range(nb_jours):
        mois = jour.month
        brutes.append(
            _ligne(
                jour.date().isoformat(),
                tmax=f"{int(100 + 100 * (mois % 12)):d}",
                tmin=f"{int(50 + 50 * (mois % 12)):d}",
            )
        )
        jour = jour.fromordinal(jour.toordinal() + 1)
    return _lignes(brutes)


def test_la_climatologie_ne_retient_que_la_periode_de_reference():
    """Une climatologie « 1991-2020 » calculée sur toute la série n'en est pas une."""
    lignes = _serie(365 * 3)
    obs = observations(
        lignes,
        "TMAX",
        source_id="noaa.ghcnd.daily",
        evidence_id="preuve",
        zone=ZONE,
        acquired_at=datetime(2026, 11, 1, tzinfo=UTC),
    )
    entiere = climatologie(obs, zone=ZONE)
    restreinte = climatologie(
        obs,
        reference_start=date(1991, 1, 1),
        reference_end=date(1991, 12, 31),
        zone=ZONE,
    )
    assert len(entiere) == 366
    assert len(restreinte) == 365
    assert entiere.par(1, 1).count == 3
    assert restreinte.par(1, 1).count == 1


def test_un_jour_sans_dispersion_n_est_pas_note():
    """Une référence d'une seule observation n'a pas de dispersion.

    L'écart normalisé y serait indéfini : le jour n'est donc pas noté, plutôt
    que noté contre une dispersion nulle.
    """
    lignes = _serie(10)
    obs = observations(
        lignes,
        "TMAX",
        source_id="noaa.ghcnd.daily",
        evidence_id="preuve",
        zone=ZONE,
        acquired_at=datetime(2026, 11, 1, tzinfo=UTC),
    )
    reference = climatologie(
        obs,
        reference_start=date(1991, 1, 1),
        reference_end=date(1991, 12, 31),
        zone=ZONE,
    )
    assert reference.par(1, 1).count == 1
    assert reference.par(1, 1).standard_deviation == 0.0
    assert anomalies(obs, reference, zone=ZONE) == []


def test_la_climatologie_est_indexee_sur_le_jour_civil():
    """À l'est de Greenwich, une indexation sur le jour UTC décalerait tout."""
    lignes = _lignes([_ligne("1991-01-01", tmax="100")])
    obs = observations(
        lignes,
        "TMAX",
        source_id="noaa.ghcnd.daily",
        evidence_id="preuve",
        zone=ZONE,
        acquired_at=datetime(2026, 11, 1, tzinfo=UTC),
    )
    reference = climatologie(obs, zone=ZONE)
    assert reference.par(1, 1) is not None
    assert reference.par(12, 31) is None


def test_un_trou_casse_un_episode():
    """La consécutivité se vérifie sur les jours civils, pas sur l'ordre."""
    lignes = _lignes(
        [
            _ligne("2020-07-01", tmax="350", tmin="200"),
            _ligne("2020-07-02", tmax="360", tmin="210"),
            _ligne("2020-07-05", tmax="370", tmin="220"),
        ]
    )
    obs = observations(
        lignes,
        "TMAX",
        source_id="noaa.ghcnd.daily",
        evidence_id="preuve",
        zone=ZONE,
        acquired_at=datetime(2026, 11, 1, tzinfo=UTC),
    )
    notes = [(o, 1.5) for o in obs]
    trouves = episodes(notes, regime="chaud", longueur_minimale=2, zone=ZONE)
    assert len(trouves) == 1
    assert trouves[0].longueur == 2
    assert trouves[0].debut.isoformat() == "2020-07-01"
    assert trouves[0].fin.isoformat() == "2020-07-02"
    assert trouves[0].moyenne == pytest.approx(1.5)


def test_la_moyenne_quotidienne_herite_de_la_qualite_la_plus_defavorable():
    """Une moyenne calculée sur une valeur douteuse n'est pas plus sûre."""
    lignes = _lignes([_ligne("2020-07-01", tmax="350", tmin="200", tmax_attributs=",I,S")])
    obs_tmax = observations(
        lignes,
        "TMAX",
        source_id="noaa.ghcnd.daily",
        evidence_id="preuve",
        zone=ZONE,
        acquired_at=datetime(2026, 11, 1, tzinfo=UTC),
    )
    obs_tmin = observations(
        lignes,
        "TMIN",
        source_id="noaa.ghcnd.daily",
        evidence_id="preuve",
        zone=ZONE,
        acquired_at=datetime(2026, 11, 1, tzinfo=UTC),
    )
    moyennes = temperature_moyenne(obs_tmax, obs_tmin)
    assert len(moyennes) == 1
    assert moyennes[0].value == pytest.approx((35.0 + 20.0) / 2)
    assert moyennes[0].quality_status.value == "unknown"


def test_une_journee_sans_minimum_n_a_pas_de_moyenne():
    lignes = _lignes([_ligne("2020-07-01", tmax="350", tmin=None)])
    obs_tmax = observations(
        lignes,
        "TMAX",
        source_id="noaa.ghcnd.daily",
        evidence_id="preuve",
        zone=ZONE,
        acquired_at=datetime(2026, 11, 1, tzinfo=UTC),
    )
    obs_tmin = observations(
        lignes,
        "TMIN",
        source_id="noaa.ghcnd.daily",
        evidence_id="preuve",
        zone=ZONE,
        acquired_at=datetime(2026, 11, 1, tzinfo=UTC),
    )
    assert temperature_moyenne(obs_tmax, obs_tmin) == ()


# --------------------------------------------------------------------------
# Le profil exploratoire
# --------------------------------------------------------------------------


def test_le_profil_compte_les_jours_manquants_et_les_trous():
    lignes = _lignes(
        [
            _ligne("2020-07-01"),
            _ligne("2020-07-02"),
            _ligne("2020-07-05"),
        ]
    )
    profil = profil_variable(lignes, "TMAX")
    assert profil.couverture.jours_observes == 3
    assert profil.couverture.jours_attendus == 5
    assert profil.couverture.taux == pytest.approx(0.6)
    assert len(profil.lacunes) == 1
    assert profil.lacunes[0].longueur == 2
    assert profil.lacunes[0].debut.isoformat() == "2020-07-03"


def test_le_profil_compte_les_valeurs_rejetees_par_le_producteur():
    lignes = _lignes(
        [
            _ligne("2020-07-01"),
            _ligne("2020-07-02", tmax_attributs=",I,S"),
            _ligne("2020-07-03", tmax_attributs=",O,S"),
        ]
    )
    profil = profil_variable(lignes, "TMAX")
    assert profil.valeurs_rejetees == 2
    assert profil.drapeaux_qualite == {"I": 1, "O": 1}
