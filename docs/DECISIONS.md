# TORNE — Journal des décisions

**31 octobre 2026.** Ce journal est court et daté. Ce n'est pas une série d'ADR : un ADR formel ne sera écrit que pour
une décision structurante, non évidente et susceptible d'évoluer. Les choix de programmation ordinaires restent ici.

| Date | Décision | Motif | Statut |
|---|---|---|---|
| 2026-10-31 | La plateforme s'appelle **TORNE**. | Le fleuve Torne était un axe de commerce et de transport ; connaître la date de sa débâcle était une information concrètement utile, devenue archive climatique exploitable. Le nom dit le trajet complet, de la physicalité à la connaissance, sans nommer le domaine ni promettre un usage. | Actif |
| 2026-10-31 | **Repository neuf et indépendant** ; les dépôts historiques restent en lecture seule. | Aucune fusion, aucune migration globale, aucune copie de répertoire depuis `boree`, `athanor` ou `SquirrelBetting`. Ce qui est repris est réécrit ou réadapté dans TORNE, jamais référencé comme une dépendance. | Actif |
| 2026-10-31 | Le paquet `BOREE_W2M_Greenfield_Reference_V2.0` est retenu comme **référence conceptuelle** ; son implémentation est **reportée**. | Le paquet est une spécification de conception, pas une implémentation. Il fixe la thèse, les frontières et le vocabulaire, mais il ne prouve l'existence d'aucun connecteur, modèle, méthode ou résultat. On s'en sert comme référentiel, on ne le transpose pas. | Actif |
| 2026-10-31 | **Python 3.12+**, environnement verrouillé par `uv`, tests avec **pytest**, linting et formatage avec **ruff**. | Python est l'écosystème scientifique dominant et permet de réutiliser les bibliothèques éprouvées plutôt que de réimplémenter les mathématiques. `uv` fournit un verrou reproductible. `pytest` et `ruff` couvrent le besoin de vérification sans introduire d'outillage supplémentaire. | Actif |
| 2026-10-31 | **Aucune performance n'est démontrée.** | Le dépôt ne contient ni modèle, ni données, ni évaluation. Toute affirmation chiffrée serait infondée. Le README et la vision distinguent explicitement ce qui est construit de ce qui est envisagé. | Actif |
| 2026-10-31 | Aucun moteur, service, registre, bus, graphe ni répertoire de packages vides n'est créé. | Une abstraction n'est justifiée que par un problème réel ou un besoin de réutilisation démontré. Les sous-packages vides sont une architecture cible, pas une capacité. | Actif |
| 2026-10-31 | **Huit dépendances, ancrées par capacité et non par convention.** | Chaque bibliothèque est justifiée par une capacité démontrée dans au moins deux documents du paquet V2.0 : calcul numérique, données tabulaires, schéma colonnaire Parquet, requête analytique locale, estimateurs et évaluation hors échantillon, acquisition HTTP/REST, déclaration YAML des contrats, modèles de contrat validés. `numpy`, `pandas`, `pyarrow`, `duckdb`, `pyyaml` et `pydantic` sont nommés dans le paquet ; `scikit-learn` et `requests` n'y sont désignés que par leur capacité — aucun document du paquet ne nomme ces deux bibliothèques. | Actif |
| 2026-10-31 | **Le noyau statistique sera repris d'`athanor.stats`**, une fois la licence clarifiée. | Douze primitives sont implémentées et testées contre les définitions publiées : e-processus et suites de confiance, e-LOND et budget d'alpha, multiplicité (FWER/FDR/Romano-Wolf), sur-apprentissage (SPA/PBO/DSR), puissance, calibration et Diebold-Mariano, intervalles de proportion, CUPED, scoring, CUSUM, régression. C'est le juge dont TORNE a besoin, et il existe déjà. | **Bloqué par la licence** |
| 2026-10-31 | **Un seul magasin brut, un seul registre de modèles, un seul contrat de connecteur, une seule gestion de secrets.** | L'archéologie établit que ces quatre besoins ont été construits deux fois : `athanor.data.rawstore` / `boree.archive.py`, `athanor.research.registry` / `boree.registre`, `athanor.data.source` / `boree.ingest.sources`, `athanor.kernel.secrets` / `boree.archive.py:312-314`. TORNE n'en adoptera qu'une version — celle d'Athanor, plus robuste — et n'en réécrira aucune avant d'avoir un besoin propre. | Actif |
| 2026-10-31 | **Le store synthétique anti-fuite est posé dès la première table.** | La technique de l'ancien BORÉE — chaque valeur du store encode sa date, le réalisé interdit vaut −1 — est la plus directe qui ait été observée. Elle est le garde-fou du point de vue à la décision, et il n'y a pas de table sans lui. | Actif |
| 2026-10-31 | **Le pré-enregistrement sera outillé**, pas seulement écrit. | L'ancien BORÉE écrit la discipline (amendements datés, notes de résultat) mais ne l'outille pas ; C.R.I.N. l'outille (gates, kill-switch, statut) mais sur une autre forme. TORNE prend les deux : la forme d'amendement daté, l'outillage de gate. | Actif |
| 2026-10-31 | **Le premier slice vertical est le Mississippi**, pas le Rhin. | Décision du critère le plus rare : la disponibilité d'un témoin économique **public** à fréquence infra-mensuelle sur toute la période. L'USDA/AMS publie des taux de fret fluvial aval hebdomadaires depuis 2004 sur sept tronçons du Mississippi, et les tonnages hebdomadaires par écluses. Sur le Rhin, tous les témoins infra-mensuels sont commerciaux et les publics sont annuels ou trimestriels — un témoin trimestriel ne date pas un décalage de quelques semaines. Détail : `docs/SLICE-PREMIER.md`. | **Proposition — attend la décision du propriétaire** |
| 2026-10-31 | **La décision « refus outillé » est retenue comme patron.** | `boree deploiement garder` et `athanor.tools.guardrails` sont deux implémentations du même principe : un script refuse une modification hors périmètre. Le principe est repris ; les règles sont réécrites sur les invariants de TORNE. | Actif |
| 2026-10-31 | **Le volet hippique, PMU, pool odds, Kelly, settlement et les 43 adaptateurs de domaine sont écartés.** | Aucun rapport avec la reconstitution d'états physiques. Trois *principes* sont conservés : le règlement au moment de vérité, l'évaluation sur l'information disponible à la décision, la discipline de gate. | Actif |

## Points ouverts

Ces points ne sont pas tranchés et ne doivent pas être présentés comme acquis.

- **Licence d'Athanor** : le dépôt `athanor@6dacc87` ne contient **aucun fichier de licence**. Tant que ce point n'est
  pas réglé, les décisions `REUSE` de `docs/REUSE_AUDIT.md` signifient « à réutiliser après clarification ». C'est le
  blocage numéro un.
- **`uv.lock`** : non généré. Le poste de construction ne disposait pas de `uv`. Le verrou doit être produit par
  `uv lock` puis commité, `uv.lock` étant volontairement versionné.
- **Installation, tests et linting** : non exécutés, pour la même raison. Les commandes attendues sont `uv sync
  --frozen`, `uv run pytest` et `uv run ruff check .`.
- **Licence du dépôt TORNE** : non choisie. Aucune affirmation de licence n'est faite tant que le propriétaire ne
  l'a pas fixée.
- **Procédure de calcul de `usable_at`** : c'est la décision qui manque le plus. Sans elle, la sémantique
  point-in-time n'est pas implémentable, et le slice ne peut pas démarrer.
- **Registre d'unités et référentiel spatial** : absent de tous les dépôts audités. À créer de zéro, avec une
  géométrie et un CRS — le « géospatial » de l'ancien BORÉE n'est qu'un ensemble de chaînes de caractères.
- **Point d'entrée console `torne`** : provisoire. Il énonce l'état du paquet et sera remplacé par le premier slice
  vertical ; il ne contient aucun code métier.
- **Temporalité** : les conventions temporelles propres à TORNE restent à définir. Les règles du protocole scellé
  Borée H3 sont hors périmètre et ne sont pas reprises.
