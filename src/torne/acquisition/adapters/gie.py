"""Ladaptateur des plateformes de transparence GIE : AGSI+ et ALSI.

GIE (Gas Infrastructure Europe) publie, sur deux plateformes transparency,
l'etat physique du gaz en Europe :

- **AGSI+** (`https://agsi.gie.eu/api`) : les **stockages souterrains** —
  stock, injection, soutirage, capacite technique, par pays et par
  installation ;
- **ALSI** (`https://alsi.gie.eu/api`) : les **terminaux LNG** — stock,
  reception, regazification, expeditions, capacite, par terminal.

Les deux partagent la meme forme : une API REST, du JSON, un en-tete
`x-key`, et une pagination par `page`/`size`. Une seule cle personnelle
couvre les deux plateformes — **a condition que le compte soit regle sur
l'acces aux deux** ; sinon, la plateforme non comprise refuse la cle avec
`Invalid or missing API key`.

Comme tout adaptateur du depot, celui-ci **pose une question** et **verifie
la forme de ce qu'il a recu** ; il n'interprete rien. C'est le decodeur
(`torne.supply.gie`) qui transforme la reponse en etat physique.

Un refus deguise
-----------------

La plateforme refuse une cle absente ou invalide **avec le code 200** et un
corps qui contient `error` et `message`. C'est la raison pour laquelle le
critere de conformite regarde ces deux champs, et pas seulement le code
retour : un `200` ne prouve rien ici.

Le meme piege attend la requete par installation : ALSI exige le **couple**
`country` + `company` + `facility`. Un `company` faux ne vide pas la reponse,
il la **refuse** : le corps porte alors `error: invalid` et `message: invalid
data`, toujours avec le code 200. Un filtre `facility` seul, ou un code EIC
qui n'existe pas, retombe silencieusement sur l'agregat du pays — la reponse
est alors celle du pays, pas celle du terminal, et rien ne le signale dans le
corps. C'est pourquoi la confrontation des agregats est un **controle**
obligatoire, et non une option.
"""

from __future__ import annotations

from ...contracts.observation import Source
from ..contracts import (
    AcquisitionRequest,
    CritereConformite,
    HttpResponse,
    PaginationStrategy,
    VerdictConformite,
    verdict_from_criteria,
)

BASE_AGSI = "https://agsi.gie.eu/api"
"""Le point d'acces du stockage souterrain."""

BASE_ALSI = "https://alsi.gie.eu/api"
"""Le point d'acces des terminaux LNG."""

SOURCE_AGSI = "gie.agsi"
SOURCE_ALSI = "gie.alsi"

CREDENTIAL_REF = "gie.apikey"
"""La reference du secret — un nom, jamais la valeur."""

PRODUCTEUR = "Gas Infrastructure Europe (GIE)"
DATASET_AGSI = "AGSI+ Transparency Platform"
DATASET_ALSI = "ALSI Transparency Platform"

TAILLE_MAX = 128
"""Le nombre maximal d'enregistrements par page, selon la documentation."""


class GieAdapter:
    """Une fenetre de donnees GIE : la question posee, et sa conformite.

    La fenetre est bornee : la plateforme sert des pages, et la fenetre
    elle-meme est bornee a quelques mois par le service.
    """

    def __init__(
        self,
        *,
        debut: str,
        fin: str,
        pays: str | None = None,
        installation: str | None = None,
        company: str | None = None,
        type_: str | None = None,
        plateforme: str = "agsi",
        taille: int = TAILLE_MAX,
        credential_ref: str = CREDENTIAL_REF,
    ) -> None:
        if not debut.strip() or not fin.strip():
            raise ValueError("la fenetre est obligatoire")
        if taille < 1 or taille > TAILLE_MAX:
            raise ValueError(f"la taille doit etre entre 1 et {TAILLE_MAX}")
        self.debut = debut.strip()
        self.fin = fin.strip()
        self.pays = pays.strip().lower() if pays else None
        self.installation = installation.strip() if installation else None
        self.company = company.strip() if company else None
        self.type_ = type_.strip() if type_ else None
        self.taille = taille
        self.credential_ref = credential_ref
        self.source_id = SOURCE_ALSI if plateforme == "alsi" else SOURCE_AGSI
        self.base = BASE_ALSI if plateforme == "alsi" else BASE_AGSI

    def _params(self, page: int) -> dict[str, str]:
        """Les parametres de la question, pour une page donnee."""
        params: dict[str, str] = {
            "from": self.debut,
            "to": self.fin,
            "size": str(self.taille),
            "page": str(page),
        }
        if self.pays:
            params["country"] = self.pays
        if self.installation:
            params["facility"] = self.installation
        if self.company:
            params["company"] = self.company
        if self.type_:
            params["type"] = self.type_
        return params

    @property
    def source(self) -> Source:
        """La source, telle que le socle la consigne."""
        return Source(
            source_id=self.source_id,
            producer=PRODUCTEUR,
            dataset=DATASET_ALSI if self.source_id == SOURCE_ALSI else DATASET_AGSI,
            access_point=self.base,
            license="API gratuite sur inscription ; l'attribution a GIE est obligatoire",
            revision_policy="quotidien ; le rapport remplace le rapport du meme jour de gaz",
            unit="TWh pour les stocks et les capacites, GWh/jour pour les flux",
            timezone="Europe/Brussels",
            publication_class="operational",
        )

    @property
    def declares_exhaustion(self) -> bool:
        """La plateforme annonce la fin des pages : elle expose `last_page`."""
        return True

    def initial_request(self) -> AcquisitionRequest:
        """La question : la premiere page de la fenetre demandee.

        La pagination des deux plateformes est **base 1** : la page 1 porte
        les enregistrements les plus recents de la fenetre, et la page `n` les
        plus anciens. La page 0 est un alias de la page 1, et une page
        superieure a `last_page` est renvoyee a l'identique : demander la
        page 0 ne perd rien, mais redemande la page 1.
        """
        return AcquisitionRequest(
            source_id=self.source_id,
            url=self.base,
            method="GET",
            params=self._params(1),
            credential_ref=self.credential_ref,
            pagination=PaginationStrategy.OFFSET,
            max_pages=40,
            label=f"{self.source_id}:{self.pays or self.installation or 'eu'}:{self.debut}",
        )

    def next_request(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> AcquisitionRequest | None:
        """La page suivante, si la plateforme en annonce une."""
        charge = _charge(response.body)
        if charge is None:
            return None
        page = int(request.params.get("page", "1") or 1)
        last = int(charge.get("last_page") or 0)
        if page >= last:
            return None
        return AcquisitionRequest(
            source_id=self.source_id,
            url=self.base,
            method="GET",
            params=self._params(page + 1),
            credential_ref=self.credential_ref,
            pagination=PaginationStrategy.OFFSET,
            max_pages=40,
            label=f"{self.source_id}:{self.pays or self.installation or 'eu'}:{self.debut}",
        )

    def verdict_conformite(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> VerdictConformite:
        """Ce que la plateforme a reellement repondu.

        Trois criteres : le corps est du JSON, il ne porte **pas** de refus,
        et il porte les enregistrements demandes.
        """
        return verdict_from_criteria(
            {
                "json": self._criterion_json(response),
                "refus": self._criterion_sans_refus(response),
                "donnees": self._criterion_donnees(response),
            }
        )

    def _criterion_json(self, response: HttpResponse) -> CritereConformite:
        """Le corps est-il du JSON ?"""
        demande = "un corps JSON"
        if _charge(response.body) is None:
            return CritereConformite(
                demande=demande, verifie=True, recu="corps illisible", conforme=False
            )
        return CritereConformite(demande=demande, verifie=True, recu="corps JSON", conforme=True)

    def _criterion_sans_refus(self, response: HttpResponse) -> CritereConformite:
        """Le corps porte-t-il un refus deguise en 200 ?

        C'est le piege de cette plateforme : une cle absente donne un 200
        avec `error` et `message`. Sans ce controle, une reponse vide
        passerait pour une absence de donnees.
        """
        demande = "un corps qui ne porte pas de refus"
        charge = _charge(response.body) or {}
        message = str(charge.get("message") or "")
        erreur = str(charge.get("error") or "")
        if "access denied" in erreur.lower() or "api key" in message.lower():
            return CritereConformite(
                demande=demande,
                verifie=True,
                recu=f"refus de la plateforme : {message or erreur}",
                conforme=False,
            )
        return CritereConformite(demande=demande, verifie=True, recu="corps JSON", conforme=True)

    def _criterion_donnees(self, response: HttpResponse) -> CritereConformite:
        """La plateforme a-t-elle rendu des enregistrements ?"""
        demande = "des enregistrements pour la fenetre demandee"
        charge = _charge(response.body) or {}
        donnees = charge.get("data")
        if not isinstance(donnees, list):
            return CritereConformite(
                demande=demande,
                verifie=True,
                recu="pas de liste de donnees",
                conforme=False,
            )
        if not donnees:
            return CritereConformite(
                demande=demande,
                verifie=True,
                recu="aucun enregistrement sur la fenetre demandee",
                conforme=False,
            )
        return CritereConformite(demande=demande, verifie=True, recu="corps JSON", conforme=True)


def _charge(corps: bytes) -> dict | None:
    """Le corps, lu comme du JSON — ou rien du tout."""
    import json

    try:
        charge = json.loads(corps.decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return charge if isinstance(charge, dict) else None


__all__ = [
    "BASE_AGSI",
    "BASE_ALSI",
    "CREDENTIAL_REF",
    "DATASET_AGSI",
    "DATASET_ALSI",
    "PRODUCTEUR",
    "SOURCE_AGSI",
    "SOURCE_ALSI",
    "TAILLE_MAX",
    "GieAdapter",
]
