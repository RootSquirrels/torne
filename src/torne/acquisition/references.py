"""Les references d'identifiants des installations, et leur provenance.

Une plateforme ne sert une installation que si on lui donne **son** code, et
pas celui d'une autre : c'est le piege du repli silencieux, ou la reponse
revient avec le code du pays et personne ne s'en aperçoit.

Cette reference est donc une **donnee de reference**, publiee par le
producteur de la donnee elle-meme. Pour le stockage, c'est la **table de
correspondance des codes EIC** publiee par GIE : elle donne, pour chaque
pays, le code d'exploitant (`Company EIC X Code`) et le code d'installation
(`Facility EIC Z or W Code`).

**Provenance consignee.** La table est une publication de GIE (REMIT) :
elle est`telechargeable publiquement, elle date du 22 fevrier 2016, et elle
est volumineuse mais **partielle** — elle ne liste que les installations que
GIE attendait de voir declarer. Ce qui n'y figure pas n'existe pas dans la
plateforme, ou n'y est plus.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from .xlsx import lire_xlsx

TABLE_ACER_GIE = "https://www.gie.eu/REMIT/download/ACER_EIC_MAPPING_TABLE_25022016.xlsx"
"""La table de correspondance des codes EIC publiee par GIE (REMIT)."""

SOURCE_ACER_GIE = "GIE — ACER EIC CODE MAPPING TABLE, 22 fevrier 2016"
"""La provenance, telle qu'elle est consignee dans les sorties du produit."""


@dataclass(frozen=True, slots=True)
class InstallationReference:
    """Une installation, et les codes qui la designent."""

    pays: str
    type: str
    """`Storage Facility`, `Storage Group` ou `SSO`."""
    operateur: str
    site: str
    code_site: str
    """Le code d'installation (famille 21W / 21Z / 21Y), ou vide pour un operateur."""
    code_societe: str
    """Le code d'exploitant (famille 21X), qui qualifie l'installation."""


@dataclass(frozen=True, slots=True)
class ReferenceStockage:
    """La reference resolue, avec sa provenance."""

    source: str
    url: str
    consultee_le: str
    installations: tuple[InstallationReference, ...]
    exploitants: tuple[InstallationReference, ...]

    def par_pays(self) -> dict[str, list[InstallationReference]]:
        """Les installations, groupees par pays."""
        groupes: dict[str, list[InstallationReference]] = {}
        for installation in self.installations:
            groupes.setdefault(installation.pays, []).append(installation)
        return groupes


def lire_reference_stockage(donnees: bytes) -> ReferenceStockage:
    """La table ACER, lue et resolue en une reference utilisable.

    Les lignes `SSO` portent le **code d'exploitant** ; les lignes
    `Storage Facility` et `Storage Group` portent le **code d'installation**
    et le nom de l'exploitant qui la detient. C'est ce nom qui fait le lien
    entre les deux : sans lui, le code d'exploitant resterait inconnu.
    """
    lignes = lire_xlsx(donnees)
    entete_index = 0
    for index, ligne in enumerate(lignes):
        if ligne and ligne[0].strip() == "Country":
            entete_index = index
            break

    codes_operateur: dict[tuple[str, str], str] = {}
    installations: list[InstallationReference] = []
    exploitants: list[InstallationReference] = []

    for ligne in lignes[entete_index + 1 :]:
        if len(ligne) < 7:
            continue
        pays = ligne[0].strip()
        type_ = ligne[1].strip()
        code = ligne[2].strip()
        operateur = ligne[4].strip()
        nom_site = ligne[5].strip()
        code_site = ligne[6].replace("\xa0", " ").strip()
        if not pays:
            continue
        if type_ == "SSO":
            if code and "to be provided" not in code.lower():
                codes_operateur[(pays, operateur.lower())] = code
                exploitants.append(
                    InstallationReference(
                        pays=pays,
                        type=type_,
                        operateur=operateur,
                        site="",
                        code_site="",
                        code_societe=code,
                    )
                )
        elif code_site and "to be provided" not in code_site.lower():
            installations.append(
                InstallationReference(
                    pays=pays,
                    type=type_,
                    operateur=operateur,
                    site=nom_site,
                    code_site=code_site.split()[0],
                    code_societe=codes_operateur.get((pays, operateur.lower()), ""),
                )
            )

    return ReferenceStockage(
        source=SOURCE_ACER_GIE,
        url=TABLE_ACER_GIE,
        consultee_le=dt.date.today().isoformat(),
        installations=tuple(installations),
        exploitants=tuple(exploitants),
    )


__all__ = [
    "SOURCE_ACER_GIE",
    "TABLE_ACER_GIE",
    "InstallationReference",
    "ReferenceStockage",
    "lire_reference_stockage",
]
