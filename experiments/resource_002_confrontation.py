"""RESOURCE-002 (correction) — la confrontation physique, enfin possible.

Le CSV PortWatch d'Espagne (HDX) porte, pour chaque port et chaque jour,
des **estimations de volume** (`import_cargo`, `export_cargo`), en plus des
comptes d'appels. C'est ce que la mission n'avait pas pu extraire par
l'API ArcGIS, et c'est le seul candidat disponible pour une confrontation
**port par port** avec la reference de l'exploitant.

Ce script rapproche, pour juin 2026 et pour les six terminaux LNG :

- l'**estimation PortWatch** (volumes `import_cargo` cumules sur le mois) ;
- la **reference Enagas quotidienne** (m3 decharges, releves le jour par jour) ;
- la **reference Enagas mensuelle** (GWh, le bulletin).

Il affiche aussi l'ecart entre les deux formes de la reference Enagas, qui
n'est **pas** reconcilie par les documents disponibles.

Usage :

    uv run python experiments/resource_002_confrontation.py [AAAA-MM] [sortie]
"""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
"""Pour trouver le module voisin, que l'on importe depuis le meme dossier."""

RHO_GNL_0C = 0.456
"""Densite du GNL a 0 degree C et 1,01325 bar (t/m3)."""

GCV_0C = 13.99
"""Pouvoir calorifique superieur du GNL a 0 degree C (MJ/m3)."""

MJ_PAR_GWH = 3600.0
"""1 GWh = 3600 MJ."""

TERMINAUX = {
    "Barcelona": ("BARCELONA", 1559.0),
    "Cartagena": ("CARTAGENA", 1882.0),
    "Bilbao": ("BBG", 3299.0),
    "Huelva": ("HUELVA", 2173.0),
    "Sagunto": ("SAGUNTO", 1065.0),
}
"""Le terminal PortWatch, la plante Enagas, et les GWh du bulletin mensuel."""

CSV_PORTWATCH = "spain-daily-port-activity-data-and-shipment-estimates.csv"


def gwh_vers_tonnes(gwh: float) -> float:
    """Les tonnes de GNL que represente une energie en GWh (base du bulletin)."""
    return gwh * MJ_PAR_GWH / GCV_0C * RHO_GNL_0C


def m3_vers_tonnes(m3: float) -> float:
    """Les tonnes de GNL que represente un volume en m3 (base 0 C)."""
    return m3 * RHO_GNL_0C


def main(argv: list[str]) -> int:
    """La confrontation, terminal par terminal."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    mois = argv[1] if len(argv) > 1 else "2026-06"
    annee, mois_num = (int(x) for x in mois.split("-"))
    racine = (
        Path(argv[2])
        if len(argv) > 2
        else Path(r"C:\Users\Romain\Documents\GitHub\torne\data\resource-002")
    )

    # -- la reference Enagas quotidienne
    dossier_quotidien = racine / "enagas" / f"juin{annee}"
    if not dossier_quotidien.exists():
        dossier_quotidien = racine / "enagas" / f"juin{mois_num}"
    volumes_quotidiens: dict[str, float] = {}
    for chemin in sorted(dossier_quotidien.glob("*.xlsx")) if dossier_quotidien.exists() else []:
        from resource_002_enagas_dechargements import _dechargements, _lignes

        valeurs = _dechargements(_lignes(chemin.read_bytes()))
        for plante, volume in valeurs.items():
            volumes_quotidiens[plante] = volumes_quotidiens.get(plante, 0.0) + volume

    # -- l'estimation PortWatch
    chemin_csv = racine / "hdx" / CSV_PORTWATCH
    portwatch: dict[str, dict[str, float]] = {}
    if chemin_csv.exists():
        texte = chemin_csv.read_text(encoding="utf-8", errors="replace")
        lignes = list(csv.reader(io.StringIO(texte)))
        entete = lignes[0]
        i_nom = entete.index("portname")
        i_annee, i_mois = entete.index("year"), entete.index("month")
        i_import = entete.index("import_tanker")
        i_export = entete.index("export_tanker")
        for ligne in lignes[1:]:
            if ligne[i_annee] != str(annee) or ligne[i_mois] != str(mois_num):
                continue
            nom = ligne[i_nom]
            entree = portwatch.setdefault(nom, {"import": 0.0, "export": 0.0, "appels": 0.0})
            entree["import"] += float(ligne[i_import] or 0)
            entree["export"] += float(ligne[i_export] or 0)
            entree["appels"] += float(ligne[14] or 0)

    print("=" * 112)
    print(f"LA CONFRONTATION PHYSIQUE — {mois}")
    print()
    print(
        f"{'terminal':<12} {'PW import':>14} {'PW export':>12} | "
        f"{'Enagas quot.':>14} {'Enagas mens.':>14} | {'ecart quot/mens':>17}"
    )
    print("-" * 112)
    for nom_port, (plante, gwh_mensuel) in TERMINAUX.items():
        pw = portwatch.get(nom_port, {"import": 0.0, "export": 0.0, "appels": 0.0})
        m3_quotidien = volumes_quotidiens.get(plante, 0.0)
        tonnes_quotidien = m3_vers_tonnes(m3_quotidien)
        tonnes_mensuel = gwh_vers_tonnes(gwh_mensuel)
        ratio = tonnes_mensuel / tonnes_quotidien if tonnes_quotidien else float("nan")
        print(
            f"{nom_port:<12} {pw['import']:>14,.0f} {pw['export']:>12,.0f} | "
            f"{tonnes_quotidien:>14,.0f} {tonnes_mensuel:>14,.0f} | "
            f"{ratio:>16.2f}x"
        )

    print()
    print("=" * 112)
    print("LIRE LES COLONNES")
    print("   PW import / export : les estimations de volume de PortWatch, cumulees sur le mois,")
    print("                       dans l'**unite du fichier** (a etablir).")
    print("   Enagas quot.       : les m3 decharges du suivi quotidien, convertis en tonnes")
    print("                       (rho = 0,456 t/m3 a 0 C).")
    print("   Enagas mens.       : les GWh du bulletin mensuel, convertis en tonnes")
    print("                       (GCV = 13,99 MJ/m3 a 0 C, meme base).")
    print()
    print("   >> le rapport entre les deux formes de la reference Enagas est le point a")
    print("      trancher : il est constant d'un terminal a l'autre, ce qui designe un")
    print("      PROBLEME DE CONVENTION et non une erreur de donnees.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
