"""RESOURCE-002 — la latence de publication de la reference Enagas.

La question n'est pas « quelle est la statistique » mais « **a partir de
quand est-elle connue** ». C'est cela qui decide si une estimation est en
avance ou si elle arrive apres coup.
"""

from __future__ import annotations

import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

BASE = (
    "https://www.enagas.es/content/dam/enagas/es/ficheros/gestion-tecnica-sistema"
    "/energy-data/publicaciones/boletin-estadistico-del-gas/"
)

MOIS = {
    "ene26": "2026-01",
    "feb26": "2026-02",
    "mar26": "2026-03",
    "abr26": "2026-04",
    "may26": "2026-05",
    "jun26": "2026-06",
    "jul26": "2026-07",
    "ago26": "2026-08",
    "sep26": "2026-09",
    "oct26": "2026-10",
}

print("=" * 90)
print("La reference Enagas : quels bulletins existent, et jusqu'a quand ?")
print(f"({'mois du bulletin':<16} {'HTTP':<6} {'taille':>10}  fichier)")
for cle, mois in MOIS.items():
    nom = f"Boletín Estadístico_{cle}.pdf"
    url = BASE + urllib.parse.quote(nom)
    demande = urllib.request.Request(url, headers={"User-Agent": "torne-resource-002"})
    try:
        with urllib.request.urlopen(demande, timeout=90, context=CTX) as reponse:
            corps = reponse.read()
        print(f"{mois:<16} {'200':<6} {len(corps):>10}  {nom}")
    except urllib.error.HTTPError as erreur:
        print(f"{mois:<16} {erreur.code:<6} {'':>10}  {nom}")
    except Exception as erreur:
        print(f"{mois:<16} {'ECHEC':<6} {'':>10}  {type(erreur).__name__}")
