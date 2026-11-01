"""RESOURCE-003 — la sensibilite de l'indicateur a ses parametres.

L'indicateur de tension repose sur deux parametres declares : le minimum
technique des cuves, et le seuil de tension. Ce script mesure ce qu'ils
changent, a partir de la serie deja construite — sans rien retelecharger.
"""

from __future__ import annotations

import collections
import csv
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RACINE = pathlib.Path(r"C:\Users\Romain\Documents\GitHub\torne")
CSV = RACINE / "data" / "resource-003" / "terminal_quotidien.csv"

if not CSV.exists():
    raise SystemExit(f"la serie n'est pas construite : {CSV}")

lignes = list(csv.DictReader(CSV.open(encoding="utf-8")))
par_terminal: dict[str, list[dict[str, float]]] = collections.defaultdict(list)
for ligne in lignes:
    par_terminal[ligne["terminal"]].append(
        {
            "stock": float(ligne["stock_final_m3"]),
            "sortie": float(ligne["regas_m3"]) + float(ligne["sorties_citernes_m3"]),
        }
    )
for suite in par_terminal.values():
    suite.sort(key=lambda d: d["stock"])  # l'ordre des jours n'importe pas ici

print("=" * 100)
print("LA SENSIBILITE DE L'INDICATEUR — jours en tension, par terminal")
print()
print(f"{'terminal':<12}", end="")
for fraction in (0.00, 0.05, 0.10, 0.15):
    print(f"mini {fraction:>5.0%}   ", end="")
print()
print("-" * 100)

capacite = {}
for terminal in par_terminal:
    remplissages = [
        float(ligne["remplissage"]) for ligne in lignes if ligne["terminal"] == terminal
    ]
    stocks = [float(ligne["stock_final_m3"]) for ligne in lignes if ligne["terminal"] == terminal]
    utiles = [s / r for s, r in zip(stocks, remplissages, strict=True) if r > 0]
    capacite[terminal] = sorted(utiles)[len(utiles) // 2] if utiles else 0.0

for terminal, suite in sorted(par_terminal.items()):
    capacite_cuve = capacite[terminal]
    sorties = [d["sortie"] for d in suite]
    moyenne = sum(sorties) / len(sorties) if sorties else 0.0
    print(f"{terminal:<12}", end="")
    for fraction in (0.00, 0.05, 0.10, 0.15):
        mini = capacite_cuve * fraction
        en_tension = 0
        for d in suite:
            reserve = max(d["stock"] - mini, 0.0)
            marge = reserve / moyenne if moyenne > 0 else 0.0
            if marge < 3.0:
                en_tension += 1
        print(f"{en_tension:>6}/{len(suite)}     ", end="")
    print()

print()
print("La colonne 'mini 10 %' est le parametre par defaut. Le classement des")
print("terminaux, lui, ne depend pas du minimum : il est structurel.")
print()
print("La sensibilite au SEUIL de tension (3 jours) sur le parametre par defaut :")
print(f"{'terminal':<12} {'marge mediane':>14} {'min':>8} {'j<1j':>6} {'j<3j':>6} {'j<7j':>6}")
print("-" * 100)
for terminal, suite in sorted(par_terminal.items()):
    capacite_cuve = capacite[terminal]
    sorties = [d["sortie"] for d in suite]
    moyenne = sum(sorties) / len(sorties) if sorties else 0.0
    mini = capacite_cuve * 0.10
    marges = []
    for d in suite:
        reserve = max(d["stock"] - mini, 0.0)
        marges.append(reserve / moyenne if moyenne > 0 else 0.0)
    marges.sort()
    mediane = marges[len(marges) // 2]
    print(
        f"{terminal:<12} {mediane:>11.1f} j {min(marges):>6.1f} j "
        f"{sum(1 for m in marges if m < 1):>6} {sum(1 for m in marges if m < 3):>6} "
        f"{sum(1 for m in marges if m < 7):>6}"
    )
