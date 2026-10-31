# Audit C.R.I.N. — Archéologie technique du dépôt `SquirrelBetting`

**Date** : 31 octobre 2026
**Dépôt audité** : `C:\Users\Romain\Documents\GitHub\SquirrelBetting\` — *lecture seule stricte : aucun fichier modifié, aucun script d'archivage ni `regen_test_set.py` exécuté, aucun état git touché.*
**Commanditaire** : `torne\MISSION.md` (§1 Vision, §5.2 périmètre, §6 matrice de réutilisation, §9 anti-complexité, §11 livrables).
**Objet** : évaluer C.R.I.N. comme **candidat au réemploi pour sa philosophie expérimentale**, et non comme une architecture à copier.

> Convention : toute affirmation porte une preuve (`chemin:ligne`, fichier de test, ou métadonnée git). Le **fait observé** est distingué de l'**inférence**, qui est explicitement signalée.

---

## 0. Périmètre effectivement lu

**Lu intégralement ou largement** (fichiers du dépôt audité) :

- `README.md`, `CHANGELOG.md` (142 ko), `crin/README.md`, `.gitignore`, `.gitattributes`, `.env.example`, les 4 scripts `.bat`/`run_backfill_2y.bat`, `regen_test_set.py` (lu sans l'exécuter).
- `docs/` : `INDEX.md`, `README.md`, `concepts/GATES.md`, `hypotheses/HYPOTHESES-TESTED.md`, `hypotheses/active/CRIN-DATA-prereg.md`, `hypotheses/active/H-FLOW-HAWKES-prereg.md`, `hypotheses/active/edge-hypotheses-v05b-prereg.md`, `hypotheses/killed/H-SOTA-ESTIMATOR-prereg.md`, `audits/BRONZE_LAYER_AUDIT.md`, `audits/A6-G0-SECTIONNELS-AUDIT.md`, `reviews/REVIEW_basket_sgo_ingest_2026-07-12.md`, plus l'inventaire des 90 `.md` par sous-dossier.
- `crin/` : les 48 modules racine lus en intégralité ou par sections (voir §1) ; les 43 modules de `crin/domains/` inventoriés par signature ; `crin/execution/` et `crin/polymarket/` inventoriés.
- `scripts/` : inventaire complet des 204 fichiers `.py` (taille + première ligne de docstring) ; lecture de `scripts/crin/adevinta_scanner.py`, `scripts/_audit_status_markers.py`.
- `tests/` : 84 fichiers, comptage des 1 580 fonctions `test_`, et relevé systématique des imports `from crin.X import …` (matrice de couverture).
- Métadonnées git lues directement : `.git/HEAD`, `.git/config`, `.git/refs/heads/main`, `.git/packed-refs`, `.git/logs/HEAD`, `.git/index`, `.git/objects/pack/`.

**Non lus** : le contenu intégral des 90 fichiers `docs/*.md` (seuls 8 ont été lus) ; le corps de `scripts/mavis_recon/` (94 fichiers) et `scripts/paper_audit/` (14 fichiers) ; `data/` (37 fichiers binaires/CSV, non lisibles utilement) ; l'historique git lui-même (220 Mo de pack, non décompressable sans binaire `git` — voir §9).

---

## 1. Cartographie

### 1.1 Identité et métriques du dépôt

| Élément | Valeur observée | Preuve |
|---|---|---|
| Remote | `https://github.com/RootSquirrels/SquirrelBetting.git` | `.git/config` |
| Branche / HEAD | `main` / `015d263e6a3e4a56bc395a0ef0dd43c595067e60` | `.git/HEAD`, `.git/refs/heads/main` |
| Clone local | 2026-10-31 13:54:51 UTC (reflog à **une seule** entrée : `clone`) | `.git/logs/HEAD` |
| Taille du pack git | 220 654 294 octets (~210 Mio) | `.git/objects/pack/pack-46148117….pack` |
| `crin/` | 100 fichiers `.py` (48 racine + 43 `domains/` + 3 `execution/` + 6 `polymarket/`), **28 759 lignes** | comptage |
| `scripts/` | 204 fichiers `.py`, **33 342 lignes** | comptage |
| `tests/` | 84 fichiers, **1 580** fonctions `def test_`, 22 795 lignes | comptage |
| `docs/` | 90 fichiers `.md` | comptage |
| `data/` (arbre de travail) | 37 fichiers, 51 761 891 octets | comptage |
| Licence | **absente** | glob sur le dépôt entier : aucun `LICENSE*`/`COPYING*` |
| Packaging | **absent** (`pyproject.toml`, `requirements*.txt`, `setup.py`, `uv.lock`, `poetry.lock` introuvables) | glob sur le dépôt entier |
| Outillage | `conftest.py`, `pytest.ini`, `ruff.toml`, `mypy.ini`, `Makefile`, `Dockerfile` : **absents** | glob sur le dépôt entier |

**Fait notable.** Le README annonce « 986 tests (12/07) » (`README.md:52`) et `crin/README.md:83` annonce « **777 tests verts** » ; le compte réel est de **1 580** fonctions de test. Les documents de statut sont donc **en retard sur le code** — la dernière entrée du `CHANGELOG.md` est datée du 2026-07-14, alors que le clone date du 2026-10-31. *Inférence* : environ trois mois et demi de développement ont eu lieu sans mise à jour du changelog ni des compteurs de tests.

### 1.2 Modules « cœur expérimental » — les candidats au réemploi

| Module | Rôle (une phrase) | État | Preuve |
|---|---|---|---|
| `crin/datasets.py` (1 291 l.) | Construit les matrices de features en une passe chronologique unique puis opère un split temporel strict train/val/test | implémenté et vérifié | `datasets.py:929`, `datasets.py:1058`; `tests/test_crin_datasets.py` (30 tests) |
| `crin/models.py` (635 l.) | Logit multinomial ridge (Newton-Raphson + backtracking) dont l'artefact embarque l'ordre des colonnes et la version du feature set | implémenté et vérifié | `models.py:60-98`; `tests/test_crin_models_artifact.py`, `tests/test_crin_models_ridge.py` |
| `crin/evalues.py` (481 l.) | e-values et confidence sequences anytime-valid, plus moniteurs de PnL et de déviation Brier | implémenté et vérifié | `evalues.py:64,146,239,454`; `tests/test_crin_evalues.py`; utilisé en production par `crin/paper_bet.py:523` |
| `crin/multiple_testing.py` (241 l.) | Corrections de multiplicité : Benjamini-Hochberg, Bonferroni, Romano-Wolf stepdown | implémenté et vérifié | `multiple_testing.py:109,142,149`; `tests/test_crin_multiple_testing.py` |
| `crin/quant_fund_validation.py` (657 l.) | SPA (Hansen), PBO/CSCV (Bailey-López de Prado), Deflated Sharpe, avec bootstrap cluster | implémenté et vérifié | `quant_fund_validation.py:172,403,604`; `tests/test_crin_quant_fund_validation.py` |
| `crin/calibration.py` (207 l.) | Brier, log-loss, reliability bins, test de Diebold-Mariano, ECE | implémenté et vérifié | `calibration.py:35,54,84,119,204`; testé via `tests/test_crin_models.py:24` |
| `crin/recalibration.py` (179 l.) | Recalibration des probabilités par PAV isotonique ou Platt, renormalisation intra-groupe | implémenté et vérifié | `recalibration.py:76,104,150,177`; `tests/test_crin_recalibration.py` |
| `crin/conformal.py` (285 l.) | Prédiction conforme : split conformal, Venn-ABERS, couplage à la dérive | implémenté et vérifié | `conformal.py:70,233`; `tests/test_crin_conformal.py` |
| `crin/drift.py` (293 l.) | Détection de dérive par PSI (Population Stability Index) par feature, états STABLE/WARN/DRIFT | implémenté et vérifié | `drift.py:56,147,171`; `tests/test_crin_drift.py` |
| `crin/drift_bridge.py` (401 l.) | Pont Bronze ↔ features : reconstruit la matrice de features sur une fenêtre pour mesurer la dérive | implémenté et vérifié | `drift_bridge.py:273,331`; `tests/test_crin_drift_bridge.py` |
| `crin/tritemporal.py` (63 l.) | Convention tritemporelle : `is_visible_asof` (temps de connaissance) et retard de publication | implémenté et vérifié | `tritemporal.py:61,73`; `tests/test_crin_tritemporal.py` |
| `crin/manifest.py` (61 l.) | Manifest d'expérience léger : commit git, indicateur `dirty`, version Python, config, facteurs | implémenté et vérifié | `manifest.py:24,44,66`; `tests/test_crin_manifest.py` |
| `crin/runner.py` (225 l.) | Runner standard des jobs longs : logging fichier horodaté, heartbeat, arrêt gracieux, boucle continue | implémenté et vérifié | `runner.py:91`; `tests/test_crin_runner.py`, `tests/test_crin_run_stats.py` |
| `crin/sota_estimators.py` (542 l.) | Compare plusieurs estimateurs (TabPFN, TabICL, logit) sur un même split, avec alignement et harnais de sanité | implémenté et vérifié | `sota_estimators.py:280,355,449`; `tests/test_crin_sota_estimators.py` |
| `crin/elo.py` (50 l.) | Elo générique (nommé « CRIN-Core ») | implémenté et vérifié | `tests/test_crin_elo.py` |
| `crin/contracts.py` (514 l.) | Framework de contrats d'ingestion : présence, type, null-rate, volume, streak de N jours consécutifs | implémenté et vérifié | `contracts.py:1-41`; `tests/test_crin_contracts.py` |
| `crin/pipeline.py` (1 765 l.) | Orchestrateur : refit, évaluation vs pool, et exécution des tests d'hypothèses preregistrées (H-BOUNCE, H-QUICK, H-MERCENAIRE, H-DAI-FRESH, H-ALLOCATION, H-GEO-SNIPER) avec conditions de validité et kill-switch | **implémenté mais non vérifié** | `pipeline.py:115,150,205,424,590,838,1023,1279`; **aucun fichier de `tests/` n'importe `crin.pipeline`** |
| `crin/gate_phase2.py` (315 l.) | « Gate Phase 2 réel » : modèle vs POOL (et non vs uniformes), DM apparié, autopsie du ridge | **implémenté mais non vérifié** | `gate_phase2.py:1-23`; aucun import dans `tests/` |
| `crin/features.py` (1 997 l.) | Schéma et construction des 58 colonnes skill + marché, versionnées par `FEATURE_SET_VERSION` | implémenté et vérifié | `features.py:245,402`; `tests/test_crin_features*.py` (6 fichiers) |

### 1.3 Modules « données / ingestion »

| Module | Rôle | État | Preuve |
|---|---|---|---|
| `crin/db.py` (550 l.) | Schéma SQLite (5 tables) et store typé, `CREATE TABLE IF NOT EXISTS` idempotent, WAL | implémenté et vérifié | `db.py:29`; `tests/test_crin_db.py`, `tests/test_crin_db_migrations.py` |
| `crin/training_data.py` (743 l.) | Scraping de l'historique PMU (Turfinfo) et parsing vers des dataclasses figées | implémenté et vérifié | `training_data.py:122,168,630`; `tests/test_crin_training_data.py` |
| `crin/training_pilot.py` (654 l.) | Pilote de validation du scraper historique | implémenté mais non vérifié | aucun import direct dans `tests/` |
| `crin/archive.py` (379 l.) | Pipeline d'archivage PMU (programme, cotes T-2, résultats) | implémenté et vérifié | `tests/test_crin_archive.py:13`, `tests/test_crin_archive_error_counter.py:21` |
| `crin/backfill.py` (370 l.) | Acquisition historique 2 ans avec throttling adaptatif | implémenté et vérifié | `tests/test_crin_backfill.py:14` |
| `crin/letrot_enrich.py` (595 l.) | Enrichissement WRITE : temps de passage, réduction kilométrique, commissaires | implémenté et vérifié | `tests/test_crin_letrot_enrich.py`, `tests/test_crin_letrot_commissaires.py` |
| `crin/letrot_pilot.py` (370 l.) | Pilote H1-bis d'acquisition LeTROT | implémenté et vérifié | `tests/test_crin_letrot_pilot.py` |
| `crin/units.py` (56 l.) | Normalisation des cotes et des enjeux selon la convention de chaque endpoint | implémenté et vérifié | `tests/test_crin_units.py` |
| `crin/collector.py`, `crin/provider.py` | Collectionneurs HTTP par source (PMU, LeTROT, macro, tennis, WNBA, MMA) ; hash d'idempotence (`sha1`/`sha256` tronqué) | implémenté et vérifié | `crin/domains/horse/collector.py`, `crin/execution/provider.py:22` |
| `crin/cache_rotation.py` (186 l.) | Politique de rotation du cache LeTROT | implémenté et vérifié | `tests/test_crin_cache_rotation.py` |
| `crin/daily_health.py` (103 l.) | CLI de contrôle quotidien des contrats d'ingestion | **implémenté mais non vérifié** | aucun import dans `tests/` |
| `crin/crin_probe.py` (83 l.) | Sonde de stabilité de l'API PMU sur les jours 2-7 | **implémenté mais non vérifié** | aucun import dans `tests/` |
| `crin/text_embeddings.py` (271 l.) | Pipeline HTML → embeddings (phrases) | implémenté et vérifié | `tests/test_crin_text_embeddings.py` |
| `crin/text_embeddings_run.py` (161 l.) | Exécution G1 : 100 fichiers LeTROT → parquet d'embeddings | **implémenté mais non vérifié** | aucun import dans `tests/` |

### 1.4 Modules « verticales métier » (spécifiques aux paris)

`crin/pool_math.py` (377 l., takeout et probabilités implicites du pool, Harville/Henery), `crin/benchmark.py` (199 l., dé-vig Shin/power/proportionnel), `crin/pool_vs_sharp.py` (75 l., divergence pool vs sharp), `crin/hz_screen.py` (251 l., screen Hausch-Ziemba), `crin/edge.py` (173 l., edge brut / takeout / edge net), `crin/policy.py` (440 l., sizing Kelly + garde-fous), `crin/paper_bet.py` (451 l., backtest avec règlement T-0), `crin/conformal.py:37,53` (Kelly robuste couplé au conformal), `crin/domains/horse/` (collecteur PMU), `crin/domains/market_efficiency/` (WNBA, MMA/UFC, basket, props).

### 1.5 Modules « hors sujet » pour TORNE

- `crin/execution/` (3 fichiers) : `ExecutionProvider` — **abstraction documentée sans implémentation**. `crin/execution/provider.py:3` l'écrit noir sur blanc : « *Aucun code d'implémentation ici : trois impls concrètes (`PaperExecutionProvider`, `PmuManuelProvider`, `BrokerAPIProvider`) sont gated sur un G6 PASS* ». Recherche dans tout le dépôt : ces trois classes n'existent que dans `provider.py` et dans `docs/operational/P10-EXECUTION-PROVIDER-DESIGN.md`. **État : documenté uniquement.**
- `crin/polymarket/` (6 fichiers, 1 908 l.) : ingestion on-chain, matching flou de marchés, VPIN. Aucun test correspondant dans `tests/`. **Implémenté mais non vérifié.**
- `crin/hflow.py`, `crin/hflow_anomaly.py` (219 l.), `crin/hflow_reflex.py` (175 l.), `crin/flb_scan.py` (190 l.) : modules d'analyse de flux et d'inefficiences structurelles ; `crin/hflow_common.py` est testé (`tests/test_hflow_common.py`), les autres ne le sont pas directement.
- `crin/domains/` (43 fichiers) : horse, lol, tennis, wnba, mma_ufc, basket, macro, esports, common, `_parked/props`. `crin/domains/esports/` ne contient qu'un `__init__.py` (package vide).
- `scripts/crin/` (9 fichiers) : **projet Stranger**. Ce sont des scanners de marketplaces de revente (Marktplaats/2ememain via Adevinta, eBay, Leboncoin, LBC) pour du LEGO, avec une « bronze immuable » et du polling jitter. Lecture : `scripts/crin/adevinta_scanner.py:1-18`. Aucune importation de `crin/` ; dépendance `curl_cffi` qui n'apparaît nulle part ailleurs.
- `scripts/mavis_recon/` (94 fichiers) et `scripts/paper_audit/` (14 fichiers) : scripts d'exploration ponctuels, non importés, non testés, non packagés. Exemple de dette : `scripts/_audit_status_markers.py:15` et `scripts/_changelog_*.py` encodent des chemins absolus vers la machine d'origine.

---

## 2. La discipline expérimentale — le cœur de l'audit

### 2.1 Vue d'ensemble

Le dépôt applique une discipline en **sept couches**, dont **cinq sont réellement outillées en code** et **deux sont purement documentaires**. C'est le résultat principal de cet audit : la philosophie est réelle, exigeante et rare — mais elle est **discontinue**. Rien ne relie automatiquement une preregistration à son exécution, et le module qui exécute les hypothèses preregistrées (`crin/pipeline.py`, 1 765 lignes) **n'est couvert par aucun test**.

| # | Mécanisme | Outillé en code ? | Testé ? | Transposable tel quel ? |
|---|---|---|---|---|
| 2.2 | Construction déterministe des matrices | oui | oui | **oui** |
| 2.3 | Artefacts de modèles autonomes | oui | oui | **oui** |
| 2.4 | Alignement entraînement / inférence | oui | partiellement | **oui** |
| 2.5 | Split temporel et walk-forward | oui (mais ce n'est pas un walk-forward) | oui | **mécanisme oui, nom non** |
| 2.6 | Pipelines d'évaluation | oui | **non** | **patron oui, code non** |
| 2.7 | Calibration (métriques / recalibration / conforme) | oui | oui | **partiellement** |
| 2.8 | Tests de multiplicité | oui | oui | **oui — cœur le plus transposable** |
| 2.9 | Inférence séquentielle | oui | oui | **oui (cœur)** |
| 2.10 | Pré-enregistrement et amendements | **non (documentaire)** | n/a | **oui, en priorité** |
| 2.11 | Contrôles de validité des résultats | oui | partiellement | **gates oui, contrats à adapter** |
| 2.12 | Détection de dérive | oui | oui | **oui** |
| 2.13 | Comparaison de plusieurs estimateurs | oui | oui | **patron oui, estimateurs non** |

### 2.2 Construction déterministe des matrices de données

**Ce qu'il fait.** `build_features_chronological` (`crin/datasets.py:929`) parcourt les courses **une seule fois, en ordre chronologique**, et met à jour les états cumulés (cumul par hippodrome, taux de victoire driver, jours depuis la dernière course…) **après** avoir calculé les features de la course courante. Le dépôt formule lui-même la règle : « *anti-leakage PAR CONSTRUCTION (le state est lu avant update)* » (`crin/README.md`, itération V0.4). La matrice est ensuite vidée en CSV par `dump_features_csv` (`datasets.py:1331`).

**Testé.** Oui, et c'est le meilleur bloc de tests du dépôt :
- `tests/test_crin_datasets.py:221 ChronologicalDeterminismTestCase` → `test_same_input_same_output` et `test_unordered_input_same_output` : l'ordre d'entrée n'affecte pas la sortie.
- `tests/test_crin_datasets.py:263 ChronologicalAntiLeakageTestCase` → `test_post_chronological_label_does_not_change_features` : **ajouter une course postérieure ne modifie aucune feature antérieure** ; `test_chronological_order_respected`.
- `tests/test_crin_datasets.py:102 ChronologicalEmissionTestCase` : une ligne par observation, shrinkage, etc.

**Transposable — oui, tel quel.** C'est exactement le test anti-fuite que le protocole BORÉE exige sur son store synthétique. La règle à importer : *une variable dérivée encode sa date ; un test prouve qu'une observation future ne peut pas la modifier.* Seule adaptation : la « course » comme groupe devient l'unité d'appartenance de l'observation (le site, la date, l'actif).

### 2.3 Artefacts de modèles autonomes

**Ce qu'il fait.** L'artefact sérialisé n'est pas un « modèle nu ». `MultinomialLogitModel` (`crin/models.py:79`) embarque `feature_cols` (l'ordre exact des colonnes au moment du fit) et `feature_set_version` (`models.py:92-98`, commentaire « *CONSOLIDATION 2026-07-11 : l'artefact devient auto-porteur* »), ainsi que `feature_means`/`feature_stds` (l'état de standardisation), le diagnostic de convergence (`n_iter`, `converged`) et les pertes train/val. `save_model` / `load_model` sérialisent l'ensemble.

**Testé.** Oui : `tests/test_crin_models_artifact.py` — dont un test qui importe `FEATURE_SET_VERSION` depuis `crin.features` (`test_crin_models_artifact.py:16`), c'est-à-dire qui vérifie la cohérence entre l'artefact et la version du schéma de features ; plus `tests/test_crin_models_ridge.py`.

**Transposable — oui, tel quel.** C'est, avec le test anti-fuite, le meilleur candidat au réemploi. Un artefact TORNE devrait porter : la version de son schéma d'entrée, l'ordre de ses colonnes, son état de normalisation, son horodatage, son commit, et son statut (« gelé pour test en avant »).

### 2.4 Alignement entraînement / inférence

**Ce qu'il fait.** Le défaut a été corrigé après un incident documenté. `load_features_csv` a pour `standardize` le défaut `False` (`crin/models.py:141-149`), avec le motif consigné : « *L'ancien défaut standardisait CHAQUE set sur lui-même (train, val, test chacun avec leurs propres moyennes) — pour une feature sparse comme ln_T_x_ln_q, la standardisation du test différait de celle du train et produisait des prédictions absurdes (Brier 0.107, refit LeTROT). Règle : charger BRUT, laisser le fit standardiser sur le train et le modèle appliquer SA standardisation stockée à la prédiction.* » Le fit standardise, l'artefact rejoue **sa** standardisation (`models.py:115` et `models.py:120-125`), et le pipeline lit le CSV brut (`crin/gate_phase2.py:60-62` : « *Aucune standardisation ici (le fit la fait en interne, état train réutilisé pour val/test)* »).

**Testé.** Partiellement : le comportement du fit est testé (`test_crin_models*.py`), mais je n'ai trouvé **aucun test** qui vérifie explicitement l'égalité entre la prédiction d'un modèle et celle rejouée depuis l'artefact sur le même échantillon.

**Transposable — oui, tel quel.** La règle est universelle : *une seule transformation d'entrée, apprise sur l'ensemble d'entraînement, conservée dans l'artefact et rejouée à l'inférence.* Pour TORNE, c'est la garantie que le modèle observé en production est bien le modèle qui a été évalué.

### 2.5 Split temporel et walk-forward

**Ce qu'il fait.** `split_walk_forward` (`crin/datasets.py:1058`) trie les courses par `heure_depart` croissant, coupe 70 / 15 / 15 (`train_frac=0.7`, `val_frac=0.15`), avec un garde-fou `min_test_n=100` (lève `ValueError` si `n < 3 × min_test_n`) et un refus des fractions invalides.

**Réserve importante.** Malgré son nom, **ce n'est pas un walk-forward** : c'est un split temporel à **trois blocs fixes**, sans repli, sans fenêtre glissante, sans ré-entraînement, sans recalage. Le nom est trompeur et ne doit pas être repris tel quel.

**Testé.** Oui : `tests/test_crin_datasets.py:336 SplitWalkForwardTestCase` — nominal, ordre temporel, dataset trop petit → lève, disjoint des groupes, fractions invalides → lève.

**Transposable — le mécanisme oui, le nom non.** Pour TORNE, un split temporel bloqué est un premier pas correct ; un **vrai** walk-forward (repli, ré-entraînement, recalage) est la forme attendue d'une plateforme qui produit des prévisions sur un flux. Recommendation : nommer la chose pour ce qu'elle est (`split_temporel_3_blocs`) et implémenter le repli séparément.

### 2.6 Pipelines d'évaluation

**Ce qu'il fait.** `crin/pipeline.py` (1 765 lignes) est le « producteur de métriques modèle » (`pipeline.py:1`). Il expose `evaluate_vs_pool` (`:115`), `run_refit` (`:150`) et six tests d'hypothèses : `run_h_bounce_test` (`:205`), `run_h_quick_test` (`:424`), `run_h_mercenaire_test` (`:590`), `run_h_dai_fresh_test` (`:838`), `run_h_allocation_test` (`:1023`), `run_h_geo_sniper_test` (`:1279`). Chacun est écrit comme un **protocole exécutable** : conditions de validité énoncées, seuil chiffré, rapport JSON écrit dans `docs/phase2-gate/`, et **kill-switch** — en cas d'échec, le verdict est écrit et l'hypothèse est déplacée vers `docs/hypotheses/killed/`.

**Testé — non.** Recherche exhaustive dans `tests/` : **aucun fichier de test n'importe `crin.pipeline`**. C'est le plus gros module non testé du dépôt, et c'est précisément celui qui porte la logique de verdict.

**Transposable — le patron oui, le code non.** Le patron — « une hypothèse preregistrée devient une fonction qui rend un verdict chiffré, un rapport, et une décision de kill » — est excellent et directement applicable à TORNE. L'implémentation, en revanche, est imbriquée dans les détails du pool hippique et n'est pas testée : **REIMPLEMENT**.

### 2.7 Calibration

Trois briques distinctes, à ne pas confondre :

1. **Métriques** (`crin/calibration.py`) : Brier (`:35`), log-loss (`:54`), reliability bins (`:84`), Diebold-Mariano apparié (`:119`), ECE (`:204`). → **REUSE**.
2. **Recalibration** (`crin/recalibration.py`) : isotonique par PAV (`_pav`, `:54` ; `isotonic_fit`, `:76`), Platt (`_fit_platt`, `:125` ; `PlattRecalibrator`, `:150`), renormalisation intra-groupe (`renormalize_by_group`, `:177`). → **REUSE**.
3. **Prédiction conforme** (`crin/conformal.py`) : Venn-ABERS en construction IPA (`VennAbersPredictor`, `:70`) et `ConformalPredictor` (`:233`). L'implémentation est **couplée au Kelly** (`kelly_fraction`, `:37` ; `conformal_kelly_stake`, `:53`) et à l'invalidation sur dérive (`subscribe_to_drift`, `:14-16`). → **ADAPT** : le cœur Venn-ABERS est général, l'habillage staking ne l'est pas.

**Testé.** Oui pour les trois (`tests/test_crin_models.py:24`, `tests/test_crin_recalibration.py`, `tests/test_crin_conformal.py`).

### 2.8 Tests de multiplicité

**Ce qu'il fait.** `crin/multiple_testing.py` implémente Benjamini-Hochberg (`:109`), Bonferroni (`:142`) et Romano-Wolf stepdown (`:149`, bootstrap sur vecteur de statistiques nulles **fourni par l'appelant**). `crin/quant_fund_validation.py` monte d'un cran : SPA de Hansen (`spa_test`, `:172`, avec bootstrap cluster optionnel `_cluster_bootstrap_indices`, `:138`), PBO/CSCV (`probability_of_backtest_overfitting`, `:403`) et Deflated Sharpe (`deflated_sharpe_ratio`, `:604`).

**Point le plus précieux de tout l'audit.** Le module documente explicitement la **gouvernance du choix de la correction** (`quant_fund_validation.py:64-70`) : « *le choix Bonferroni vs BH vs Romano-Wolf est figé dans la prereg avant tout test. Sélectionner Romano-Wolf parce que Bonferroni tue = α-shopping avec des outils SOTA. Convention : Bonferroni par défaut, RW autorisé si la prereg déclare ex-ante des hypothèses positivement corrélées sur le même dataset, BH réservé au screening exploratoire étiqueté comme tel.* » Il documente aussi le **piège** d'un bootstrap iid sur données corrélées (`quant_fund_validation.py:39-62`) et donne trois remèdes : cluster sur l'entité (`race_id`), statistiques nulles dont le bootstrap préserve la dépendance, agrégation temporelle avant DSR.

**Testé.** Oui : `tests/test_crin_multiple_testing.py`, `tests/test_crin_quant_fund_validation.py` (dont un test dédié à `deflated_sharpe_ratio`, `:523`).

**Transposable — oui, tel quel. C'est le cœur le plus transposable du dépôt.** La règle « la correction de multiplicité se choisit avant de regarder les résultats, sinon c'est de l'α-shopping » est exactement ce que le protocole BORÉE exige (amendement daté, méthode de correction figée avant le premier calcul). Les outils (SPA, PBO/CSCV, DSR) s'appliquent à toute famille de performances, pas seulement aux paris.

### 2.9 Inférence séquentielle

**Ce qu'il fait.** `crin/evalues.py` implémente l'e-value d'une moyenne bornée (`e_value_bounded_mean`, `:64`), la **confidence sequence** (`confidence_sequence_bounded_mean`, `:146`), la conversion e-value → p-value (`p_value_from_e`, `:194`), plus deux moniteurs : `ROIMonitor` (`:239`) et `BrierDeviationMonitor` (`:454`).

**Testé.** Oui, et c'est le module le mieux couvert en tests de propriété : `tests/test_crin_evalues.py` (> 600 lignes) utilise l'estimateur de Waudby-Smith comme référence (`:166`).

**Utilisé en production.** Oui : `crin/paper_bet.py:523` instancie `ROIMonitor` pour suivre le PnL d'une série de paris. Le module n'est donc pas décoratif. De plus, cinq scripts de recherche l'importent directement : `scripts/edge_hypotheses_v05.py:317`, `scripts/hflow_pmu_v1_hawkes.py:32`, `scripts/hflow_smell.py:36`, `scripts/h_xpool_kl_run.py:45`, `scripts/mma_hawkes_phase2.py:37`.

**Transposable — oui pour le cœur** (`e_value_bounded_mean`, `confidence_sequence_bounded_mean`, `p_value_from_e`), qui est agnostique du domaine. `ROIMonitor` est un wrapper de surveillance d'un flux : la mécanique se transpose, la sémantique de mise ne se transpose pas.
### 2.10 Pré-enregistrement et amendements

**Ce qu'il fait.** C'est la couche la plus **développée** et la plus **purement documentaire** du dépôt.

- Registre `docs/hypotheses/active/` — **16 preregs** : `CRIN-DATA-prereg.md`, `H-FLOW-HAWKES-prereg.md`, `H-XPOOL-KL-prereg.md`, `H-KELLY-AGG-prereg.md`, `H-DRIFT-CROSSBOOK-PROPS-prereg.md`, `H-TEXT-EMB-prereg.md`, `H-MMA-UFC-HAWKES-prereg.md`, `H-LOLa0-CLOSING-prereg.md`, `H-REFLEX-prereg.md`, `H-REGIME-prereg.md`, `H-ANOMALY-OVERLAY-prereg.md`, `H-PATCH-MONETIZATION.md`, `H-PATCH_ADAPTATION-prereg.md`, `edge-hypotheses-nlp-prereg.md`, `edge-hypotheses-v05b-prereg.md`, `edge-hypotheses-dai-fresh-v2-prereg.md`.
- Registre `docs/hypotheses/killed/` — **9 preregs** : `H-SOTA-ESTIMATOR-prereg.md`, `H-EVENT-RESIDUAL-prereg.md`, `H-HZ_PLACE-prereg.md`, `H-QUAL-SHARP-prereg.md`, `H-alpha0-props-v0-prereg.md`, `H-FLOW-basket.md`, `H-FLOW-family-D.md`, `H-MMA-UFC-INFO-PUBLIQUE-v2-prereg.md`, `H-SURFACE-ADAPTATION-prereg.md`.
- Chaque prereg contient : hypothèse, méthode, seuil, **conditions de validité**, **kill-switch**, statut. Exemple lu : `docs/hypotheses/active/CRIN-DATA-prereg.md` — régression des features sur données historiques, avec seuil de désactivation, conditions de validité explicites et clause de non-réutilisation après peek.
- **Amendements** : 35 occurrences d'« amendement » dans 16 fichiers de `docs/`. Le mécanisme est la **version incrémentée** de la prereg à toute déviation (ex. `edge-hypotheses-dai-fresh-v2-prereg.md` ; `H-FLOW-HAWKES-prereg.md` qui référence explicitement « *amendement v1.2* »).
- **Kill-switch** comme objet de gouvernance : `docs/concepts/GATES.md` définit une progression G0 → G7 où chaque gate a des conditions de passage ; l'échec d'un gate **tue** l'hypothèse correspondante.

**Testé / outillé — non.** Aucun code ne vérifie qu'un rapport a été produit par une prereg, ni qu'un amendement est daté et commité **avant** le calcul, ni qu'une prereg n'a pas de rapport. Le lien prereg → exécution → verdict → kill est **humain**.

**Transposable — oui, tel quel, et en priorité.** C'est le mécanisme même que TORNE revendique. Deux corrections à apporter en le transposant : (a) exiger une **date + commit** sur chaque amendement — le format BORÉE (amendement daté dans `PREREG.md`, commité avant le premier calcul) est plus strict que celui de C.R.I.N. ; (b) **outiller** le lien prereg → exécution, pour qu'un rapport orphelin ou une prereg sans rapport soit détectable par un contrôle automatique.

### 2.11 Contrôles de validité des résultats

Trois dispositifs distincts :

1. **Gates** — `docs/concepts/GATES.md` définit une progression G0 → G7 avec conditions de passage ; `crin/gate_phase2.py` est l'implémentation d'un de ces gates. Son en-tête documente la **correction d'un rapport antérieur invalidé** : « *Corrige le rapport Phase 2 du 2026-07-08 qui validait contre les mauvaises baselines (uniforme 1/N et random 0.5 — bannies par BENTER-PLAN §12.2/12.3)* » (`gate_phase2.py:1-14`). Le gate compare le modèle au **pool** et non à une baseline triviale. **Non testé.**
2. **Contrats d'ingestion** — `crin/contracts.py` : cinq dimensions fail-fast (champs présents, types, null-rate ≤ seuil, volume quotidien dans un intervalle, **streak** de null-rate ≥ seuil pendant N jours consécutifs — le streak est explicitement présenté comme le complément du seuil absolu et non son remplacement, `contracts.py:13-22`). Sévérité `critical=True` → `RAISE` au premier viol ; `False` → simple log. Écrit un marqueur de santé dans `docs/phase2-gate/contract_health/`. Déclinaisons `contracts_pmu.py`, `contracts_letrot.py`, `contracts_fred.py`. **Testé** (`tests/test_crin_contracts.py`).
3. **Contrôle a posteriori** — `crin/evalues.py` `BrierDeviationMonitor` (`:454`) surveille l'écart de Brier à une valeur de référence. **Testé.**

**Transposable.** Le **framework de gates** : oui, tel quel — c'est de la gouvernance, pas du code. Les **contrats d'ingestion** : ADAPT — la mécanique du streak est excellente et réutilisable pour les sources de TORNE, mais le vocabulaire « null-rate par colonne » est celui d'un schéma tabulaire ; pour TORNE, l'équivalent est « une grandeur dérivée présente, plausible et dans son domaine de validité ».

### 2.12 Détection de dérive

**Ce qu'il fait.** `crin/drift.py` calcule un **PSI par feature** (`psi`, `:147`) sur des bins d'**égale fréquence** (`_equal_frequency_bin_edges`, `:98`), avec seuils d'avertissement et de dérive (`_classify_psi`, `:337`) et trois états (`DriftState`, `:56`). `crin/drift_bridge.py` reconstruit la matrice de features depuis la couche Bronze sur une fenêtre donnée (`walk_bronze_window`, `:229` ; `build_feature_matrix`, `:273` ; `run_drift_check`, `:331`) et écrit un rapport d'audit.

**Testé.** Oui : `tests/test_crin_drift.py`, `tests/test_crin_drift_bridge.py` (qui importe aussi `crin.domains.horse.collector`).

**Transposable — oui, tel quel.** Le PSI est un standard de l'industrie, agnostique du domaine. Deux réserves : (a) le PSI **détecte** mais n'explique pas — il manque ici un lien vers l'hypothèse de changement sous-jacente (quelle grandeur a bougé, et pourquoi) ; (b) la documentation indique que les seuils par défaut sont repris de la littérature (`drift.py:44`, renvoi à Siddiqi 2006) **sans calibration propre** sur les données du projet. Pour TORNE : à reprendre, mais à re-calibrer et à coupler à une explication.

### 2.13 Comparaison de plusieurs estimateurs

**Ce qu'il fait.** `crin/sota_estimators.py` met les estimateurs sur un même footing : `align_p_to_groups` (`:209`, renormalisation intra-groupe obligatoire avant toute comparaison), `subsample_train` (`:245`, pour égaliser le budget d'entraînement), puis ajustement de TabPFN (`:280`) et TabICL (`:355`), comparaison via `evaluate` (`:449`) produisant un `Verdict` (`:414`). Deux **harnais de sanité** existent : `sanity_harness_turf` (`:539`) et `sanity_harness_tennis` (`:579`) — avant de croire un edge, on vérifie que le pipeline détecte un edge **injecté**. C'est un **contrôle négatif**, rare et précieux.

**Testé.** Oui : `tests/test_crin_sota_estimators.py`.

**Transposable — le patron oui, les estimateurs non.** Le patron « comparer K estimateurs sur un split et un budget identiques, avec un harnais de sanité à signal injecté » est excellent. TabPFN et TabICL ne le sont pas : dépendances lourdes, non pinnées (aucun `requirements.txt` ni `pyproject.toml` — §6), et une `BaselineConstantWarning` dans `crin/domains/market_efficiency/alpha0.py` montre que le cas « estimateur constant » n'a pas été traité partout.

### 2.14 Ce qui manque à la discipline (constats)

| Manque | Preuve | Conséquence pour TORNE |
|---|---|---|
| Aucune graine globale ni convention de reproductibilité | aucun `random.seed` global ; `crin/hawkes.py:61` crée un `np.random.default_rng()` **sans graine** ; `crin/quant_fund_validation.py:273,383` prennent une graine en argument | toute série aléatoire doit avoir une graine explicite **journalisée dans le manifeste** |
| Aucun hash d'artefact ni de jeu de données | `hashlib` n'apparaît que pour l'idempotence HTTP (`crin/domains/horse/collector.py`, `crin/execution/provider.py:22`) | `crin/manifest.py` ne suffit pas : il manque une empreinte de contenu |
| Aucune intégration continue, aucun lint configuré | absence de `conftest.py`, `pytest.ini`, `ruff.toml`, `.github/` | à créer dans TORNE dès le socle |
| Aucun packaging ni verrou de dépendances | §6 | à créer dans TORNE dès le socle |
| Le module qui produit les verdicts n'est pas testé | `crin/pipeline.py`, 1 765 lignes | ne pas le reprendre tel quel |
| Aucun lien outillé prereg → rapport | §2.10 | à outiller dans TORNE |
| Les documents de statut sont en retard sur le code | `README.md:52` (986 tests) vs 1 580 fonctions réelles ; dernier `CHANGELOG.md` au 2026-07-14 | chez TORNE, la documentation doit être générée ou contrôlée |

---

## 3. Ce qui est spécifique aux courses et ne doit pas être repris

La MISSION (§5.2) liste six interdits. Les six sont matérialisés dans le code, avec les chemins exacts.

### 3.1 PMU et ses features — `crin/features.py` (1 997 l.)

`FEATURE_SET` (`features.py:402`) fige **58 colonnes skill** + les colonnes de marché ; `FEATURE_SET_VERSION = "v0.6"` (`features.py:245`). Les variables sont hippiques : allure, corde, poids porté, musique, cumul par hippodrome, taux de victoire driver, jockey, entraîneur, distance, terrain, nombre de courses par an, jours de repos, réduction kilométrique, temps de passage… Les collecteurs de cumul sont dans `crin/domains/horse/collector.py`.

**Pourquoi ça ne se transpose pas** : ces variables n'ont aucun sens hors du galop et du trot. Leur *mécanique* (un schéma de features versionné, un collecteur de cumul générique) est en revanche réutilisable — mais un TORNE qui n'a pas de courses n'a aucune raison de reconstruire ce dictionnaire.

**Décision : REJECT.**

### 3.2 Pool odds et closing-Shin

- `crin/pool_math.py` (377 l.) : takeout du pool, probabilités implicites, construction de Harville et de Henery (`DEFAULT_HENERY_RATIOS`, testé par `tests/test_crin_hz_screen.py:19`).
- `crin/benchmark.py` (199 l.) : dé-vig **Shin** (`shin_probs`, `:155`), **power** (`power_probs`, `:122`), **proportionnel** (`proportional_probs`, `:111`), avec l'abstraction `BenchmarkProvider` (`:57`) et la distinction pari-mutuel / cote fixe (`:7-12`).
- `crin/sota_estimators.py:180 closing_shin_probs` ; `crin/pool_vs_sharp.py` (75 l., divergence pool vs sharp) ; `crin/domains/tennis/benchmark.py` (fournisseur Tennis).

**Pourquoi ça ne se transpose pas** : tout cela repose sur l'existence d'un **marché à cotes** dont on cherche à deviner la probabilité implicite. TORNE n'a pas de marché de paris ; son « référentiel » sera un **modèle de référence** ou une **observation directe de l'état du monde**, pas un overround à dé-viguer. Copier Shin serait importer une réponse à une question que TORNE ne pose pas.

**Décision : REJECT** pour les calculs de pool/Shin ; **REUSE** pour le *patron* d'abstraction « référentiel de comparaison » (`BenchmarkProvider`), reformulé.

### 3.3 Kelly et le sizing — `crin/policy.py` (440 l.), `crin/conformal.py:37,53`

`crin/policy.py` implémente le sizing Kelly et ses garde-fous ; `crin/conformal.py` couple l'intervalle conforme à la mise (`conformal_kelly_stake`, `:53`) et utilise l'OOD comme filtre gratuit (`p_lo × o ≤ 1`).

**Pourquoi ça ne se transpose pas** : Kelly suppose une bankroll, une cote et un terme de contrat. TORNE (mission §1) produit des **conséquences économiques et financières**, pas des mises. Le sizing n'a pas de sens tant que TORNE n'a pas défini son objet économique (probabilité de direction d'un actif, calendrier, utilité).

**Décision : REJECT.** *Nuance* : si et quand TORNE définit une utilité économique, la discipline « la mise découle de l'incertitude » (Kelly(p_lo)) est une **référence de méthode**, pas une brique à copier.

### 3.4 Settlement hippique — `crin/paper_bet.py` (451 l.), `crin/edge.py` (173 l.)

`crin/paper_bet.py` porte la « RÈGLE D'INTÉGRITÉ n°1 » : **décision aux cotes T-2, règlement aux cotes T-0**, avec le raisonnement consigné : « *L'argent tardif (cote T-0) est le plus informé […] Si on règle les paris sur la cote T-2 qu'on a observée au moment de la décision, on FABRIQUE du ROI fictif* » (`paper_bet.py:1-26`). `crin/edge.py` distingue edge brut, takeout effectif et edge net.

**Pourquoi ça ne se transpose pas** : les courses ont une **course** (un état final unique, une date de règlement) ; c'est le cas particulier, pas la généralité.

**Décision : REJECT** pour l'implémentation ; **REUSE** pour le **principe**, qui est général et se transpose mot pour mot : *ne jamais évaluer une décision sur une information qui n'était pas disponible à la décision ; régler au moment du vérité.* C'est la version métier de la règle tritemporelle de `crin/tritemporal.py:61` (`is_visible_asof`). Pour TORNE, cela devient : une estimation produite à l'instant T ne peut être fulfilie par une observation postérieure à T.

### 3.5 Les règles de marché propres à C.R.I.N.

- `crin/units.py` (56 l.) : normalisation des cotes et des enjeux **selon la convention par endpoint** (testé par `tests/test_crin_units.py`).
- `crin/hz_screen.py` (251 l.) : screen Hausch-Ziemba sur l'edge Placé depuis le pool Gagnant (testé par `tests/test_crin_hz_screen.py`).
- `crin/domains/horse/`, `crin/domains/tennis/`, `crin/domains/lol/`, `crin/domains/market_efficiency/` : règles de collecte propres à chaque verticale.
- `crin/elo.py` (50 l.) : Elo **générique**, explicitement étiqueté « CRIN-Core » et testé (`tests/test_crin_elo.py`).

**Pourquoi ça ne se transpose pas** : ce sont des conventions de collecte et des écrans d'inefficience propres à un marché. Le seul élément à discuter est `crin/elo.py`, qui est un rating générique réutilisable par TORNE pour des grandeurs ordonnées (classements, forces relatives) — mais dont l'utilité n'est pas démontrée tant que TORNE n'a pas de vertical slice. **Décision : REJECT** pour l'ensemble, **ADAPT** pour `elo.py` si un vertical slice le requiert.

### 3.6 Les domain adapters génériques — `crin/domains/base.py`

`crin/domains/base.py` définit un registre `DOMAIN_REGISTRY` et une interface `Domain` ; `crin/domains/` compte **43 fichiers** répartis en horse, lol, tennis, wnba, mma_ufc, basket, macro, esports, common, et `_parked/props`. `crin/domains/esports/` ne contient qu'un `__init__.py` (package vide). `crin/domains/_parked/props/_PARKED.md` matérialise le « rangement » d'une verticale abandonnée.

**Pourquoi ça ne se transpose pas** : c'est exactement ce que la MISSION (§9) interdit : « *Une abstraction générique anticipant des domaines non encore étudiés* » et « *Avant de créer une interface, vérifier qu'au moins deux implémentations concrètes en ont besoin* ». Ici, l'abstraction a été créée pour six verticales réelles — mais **six verticales de paris**, dont cinq sont des experiments football/e-sport/tennis sans rapport avec la reconstitution d'états physiques de TORNE. Le coût de reprise est celui d'une généralisation *et* d'un nettoyage.

**Décision : REJECT**, en notant que `crin/domains/_parked/` montre que le dépôt **sait** ranger une verticale morte — un réflexe à reprendre, mais sur un mécanisme plus simple (un dossier, pas un registre).

### 3.7 Récapitulatif

| Interdit par la MISSION | Chemin | Décision |
|---|---|---|
| PMU et ses features | `crin/features.py` | REJECT |
| Pool odds et closing-Shin | `crin/pool_math.py`, `crin/benchmark.py`, `crin/pool_vs_sharp.py`, `crin/sota_estimators.py:180` | REJECT |
| Kelly et le sizing | `crin/policy.py`, `crin/conformal.py:37,53` | REJECT |
| Settlement hippique | `crin/paper_bet.py`, `crin/edge.py` | REJECT (le **principe** est REUSE) |
| Règles de marché C.R.I.N. | `crin/units.py`, `crin/hz_screen.py`, `crin/domains/horse|tennis|lol|market_efficiency/` | REJECT |
| Domain adapters génériques | `crin/domains/base.py` + 43 fichiers | REJECT |
---

## 4. Les tests

### 4.1 Volume et style

- **84 fichiers**, **1 580 fonctions `def test_`**, 22 795 lignes dans `tests/`.
- Framework : `unittest` de la stdlib, classes `unittest.TestCase` (`tests/test_crin_datasets.py:102`, `:221`, `:263`, `:336`, `:402`). **Aucune fixture pytest, aucun `conftest.py`** — les jeux de données sont construits à la main dans chaque test.
- **Aucun test d'intégration bout-en-bout sur données réelles** : les tests utilisent des fixtures synthétiques et du `monkeypatch` (ex. `tests/test_crin_domains.py:145-187`, qui remplace `horse_domain.crin_archive.run_programme`).
- **Aucune configuration de lint, aucune CI** : pas de `.github/`, pas de `ruff.toml`, pas de `pytest.ini`.

### 4.2 Ce qui est réellement testé

| Domaine | Fichiers de test | État |
|---|---|---|
| Features (v0.1 → v0.6) | `test_crin_features.py`, `test_crin_features_v0_1.py`, `test_crin_features_v0_2.py`, `test_crin_features_v0_2_5.py`, `test_crin_features_v0_2_collectors.py`, `test_crin_features_v0_3.py`, `test_crin_features_v0_6.py` | testé |
| Datasets, split, anti-fuite | `test_crin_datasets.py` (30 tests), `test_crin_v0_6_parity.py` | testé |
| Modèles et artefact | `test_crin_models.py`, `test_crin_models_artifact.py`, `test_crin_models_ridge.py` | testé |
| Multiplicité, SPA/PBO/DSR | `test_crin_multiple_testing.py`, `test_crin_quant_fund_validation.py` | testé |
| Inférence séquentielle | `test_crin_evalues.py` (> 600 lignes, tests de propriété, estimateur de Waudby-Smith comme référence) | testé |
| Calibration / recalibration / conforme | `test_crin_models.py:24`, `test_crin_recalibration.py`, `test_crin_conformal.py` | testé |
| Dérive | `test_crin_drift.py`, `test_crin_drift_bridge.py` | testé |
| Multiplicité d'ingestions | `test_crin_contracts.py` | testé |
| Benchmark, pool, Elo, unités | `test_crin_benchmark.py`, `test_crin_pool_math*.py` (3), `test_crin_elo.py`, `test_crin_units.py` | testé |
| DB et migrations | `test_crin_db.py`, `test_crin_db_migrations.py` | testé |
| Collecteurs par verticale | `test_crin_pmu_bronze.py`, `test_crin_domains_lol_g0.py`, `test_crin_domains_lol_archive.py`, `test_crin_domains_tennis.py`, `test_crin_tennis_features.py`, `test_tennis_g0_runner.py`, `test_mma_ufc_skeleton.py`, `test_wnba_skeleton.py`, `test_wnba_collector.py`, `test_alpha0_framework.py`, `test_basket_hflow.py`, `test_fred_collector.py` | testé |
| Archive, backfill, LeTROT | `test_crin_archive.py`, `test_crin_archive_error_counter.py`, `test_crin_backfill.py`, `test_crin_letrot_enrich.py`, `test_crin_letrot_commissaires.py`, `test_crin_letrot_pilot.py`, `test_crin_training_data.py`, `test_crin_training_pilot.py` | testé |
| Manifeste, tritemporel, runner, cache | `test_crin_manifest.py`, `test_crin_tritemporal.py`, `test_crin_runner.py`, `test_crin_run_stats.py`, `test_crin_cache_rotation.py` | testé |
| Edge / paper bet / policy (Phase 3) | `test_crin_phase3.py` | testé |
| Estimateurs SOTA | `test_crin_sota_estimators.py` | testé |
| Hawkes, HZ screen, text embeddings | `test_crin_hawkes.py`, `test_crin_hz_screen.py`, `test_crin_text_embeddings.py`, `test_hflow_common.py` | testé |

### 4.3 Ce qui n'est PAS testé

| Module non testé | Taille | Pourquoi c'est important |
|---|---|---|
| `crin/pipeline.py` | 1 765 l. | **C'est le module qui produit les verdicts des hypothèses preregistrées.** Aucun test ne l'importe. |
| `crin/gate_phase2.py` | 315 l. | Le gate de comparaison modèle vs référentiel, non testé. |
| `crin/training_pilot.py` | 654 l. | Pilote de scraping historique. |
| `crin/polymarket/` (6 fichiers) | 1 908 l. | Ingestion on-chain, matching, VPIN. |
| `crin/hflow.py`, `crin/hflow_anomaly.py`, `crin/hflow_reflex.py`, `crin/flb_scan.py` | ~900 l. | Analyses de flux et d'inefficiences ; seul `hflow_common.py` est testé. |
| `crin/daily_health.py`, `crin/crin_probe.py`, `crin/text_embeddings_run.py` | 347 l. | Contrôles opérationnels. |
| `crin/domains/tennis/g1_runner.py`, `g2_runner.py`, `crin/domains/lol/sanity_harness.py`, `crin/domains/market_efficiency/basket/alpha0_props.py`, `basket/sgo_ingest.py` | — | Sous-domaines non couverts. |
| `crin/execution/provider.py` | 282 l. | Déclaré sans implémentation (§1.5). |

### 4.4 Ce qui n'est pas testé *sémantiquement*

- **Pas de test d'équivalence entraînement/inférence** : rien ne vérifie qu'un modèle rechargé depuis son artefact reproduit exactement les prédictions du fit (le défaut de standardisation corrigé en 2026-07-11, `crin/models.py:141-149`, n'a pas laissé de test de régression dédié).
- **Pas de test bout-en-bont de la chaîne** `features → datasets → models → pipeline → verdict`.
- **Pas de test de non-régression sur données réelles** : aucun golden file, aucun test de reproductibilité d'un chiffre publié.
- **Pas de test du lien prereg → rapport** (§2.10).

**Bilan tests.** La couverture *unitaire* est réelle et de bonne qualité (notamment les propriétés de déterminisme, d'anti-fuite et de monotonie). La couverture *de système* est faible : le code qui décide n'est pas testé. C'est le principal avertissement de cet audit.

---

## 5. Données et reproductibilité

### 5.1 Comment les données sont produites

| Flux | Producteur | Support |
|---|---|---|
| Programme, cotes T-2, résultats PMU | `crin/archive.py` via `crin_archive_morning.bat` / `crin_archive_evening.bat` (Task Scheduler Windows, 08:30) | SQLite `data/crin.db` |
| Historique 2 ans | `crin/backfill.py` (throttle adaptatif) puis `crin/training_data.py` (scraping Turfinfo) | `data/crin_2y.db` |
| Enrichissement LeTROT | `crin/letrot_enrich.py` | même DB |
| Cache réseau | `crin/training_data.py:73 DEFAULT_CACHE_DIR = Path("docs/cache-turfinfo")` | JSON |
| LoL / tennis / WNBA / MMA / basket | `crin/domains/*/archive.py` | SQLite par verticale |
| Polymarket | `crin/polymarket/ingest.py`, `live.py` (Alchemy), `markets.py` (Gamma) | `data/polymarket/` |
| FRED (macro) | `crin/domains/macro/` | `crin/contracts_fred.py` |

### 5.2 Versionnement

**Il n'y a pas de versionnement des données.** Ni `data version`, ni DVC, ni hash de contenu. Le seul versionnement est **git**, et il **exclut** les données : `.gitignore:11-15` (`*.db`, `*.db-wal`…), `:54-69` (`data/crin_features_*.csv`, `data/*.csv`, `data/crin_model_*.pkl`, `data/*/*/*.parquet`), `:85-89` (parquets d'embeddings).

*Inférence* : le pack git fait 210 Mio alors que le code source et la documentation totalisent quelques mégaoctets ; et l'arbre de travail contient `data/tennis_g1_features.csv` (436 ko), `data/crin_model_v0.pkl` (3,4 ko), `data/_odds_assessment.py` et `data/COORDINATION_sgo_paid_backfill.md` — des fichiers **exactement** visés par les règles d'ignore. Ces fichiers ayant été matérialisés par le clone, ils sont **suivis** par git : ils ont été commités avant l'introduction des règles d'ignore, qui ne dé-versionnent rien. *Corollaire : des données massives restent dans l'historique, et les jeux de données de travail sont hors de tout contrôle de version.*

### 5.3 Déterminisme des matrices

- **Oui pour les matrices** : passage chronologique unique (`crin/datasets.py:929`), tri par `heure_depart` (`datasets.py:1081-1083`), puis `dump_features_csv` (`datasets.py:1331`). Le groupe est identifié par `group_id` composé de date+hippodrome+`pmu_race_id` — un correctif daté du 2026-07-08 pour ne plus confondre des courses de jours différents partageant le même `pmu_race_id` (`crin/models.py:156-158`).
- **Partiellement pour le reste** :
  - **Aucune graine globale.** `crin/hawkes.py:61` : `rng = np.random.default_rng()` — **sans graine**, donc non reproductible. `crin/quant_fund_validation.py:273,383` prennent une graine en argument (bon), `crin/hflow.py:392` et `crin/domains/tennis/g1_runner.py:185` aussi.
  - **Aucun hash d'artefact ni de jeu de données.** `hashlib` n'est utilisé que pour l'idempotence HTTP (`crin/domains/horse/collector.py:148`, sha1 tronqué à 16 caractères ; `crin/execution/provider.py:148`, sha256 tronqué).
  - **Horodatage** : oui — `crin/manifest.py:55` (`created_at` UTC ISO), `git_commit` avec indicateur `dirty` (`:24-41`), `crin/db.py::utcnow_iso`, rapports de gate horodatés (`crin/gate_phase2.py:23`), heartbeats (`crin/runner.py:14-17`).

### 5.4 Réversible / volumineux / non versionné

- **Réversible** : le cache réseau est explicitement régénérable (`docs/cache-turfinfo/*.json`, `.gitignore:25-28` : « *pas une source de vérité — la vérité est dans crin.db* »), ainsi que les CSV de features et les parquets d'embeddings (« *regenerable* », `.gitignore:54,85`).
- **Non réversible** : les bases SQLite de travail (`data/crin.db`, `data/crin_2y.db`) ne sont **ni versionnées ni réversibles** ; `regen_test_set.py:26` crée même une base temporaire `data/crin_full.db` par fusion.
- **Volumineux** : `data/` = 37 fichiers / 51 761 891 octets, dominés par `data/lol/parquet` (37 399 185 o) et `data/mma_ufcstats` (10 577 692 o) ; plus le pack git de 210 Mio et le cache `docs/cache-turfinfo/`.

### 5.5 Une constatation de portabilité (fait observé)

Le dépôt a été développé sur une autre machine et **n'est pas portable en l'état** :

- `regen_test_set.py:23` : `REPO = Path("C:/Users/Drgal/Documents/GitHub/SquirrelBetting")`
- `crin_archive_morning.bat:17` : `cd /d "C:\Users\Drgal\Documents\GitHub\SquirrelBetting"`
- `scripts/_audit_status_markers.py:15` : `ROOT = Path(r"C:\Users\Drgal\Documents\GitHub\SquirrelBetting\docs\hypotheses")`

S'y ajoutent les scripts `.bat`, la Task Scheduler Windows, et un bug de fuseau horaire documenté dans `crin/runner.py:59-63` (« *sans tz explicite, datetime.now() retourne l'heure LOCALE du système (UTC sur Windows Server, Paris sur workstation), ce qui décalait until_hhmm de 2h en prod* »).

---

## 6. Licence, dépendances, secrets

### 6.1 Licence — **INCONNUE, point bloquant**

**Aucun fichier `LICENSE`, `LICENSE.md`, `LICENSE.txt`, `COPYING`** dans l'ensemble du dépôt (recherche par glob sur toute l'arborescence : aucun résultat). Il n'existe pas non plus de mention de licence dans le `README.md` ou le `CHANGELOG.md` (fichiers lus intégralement).

Conséquence : **aucune reprise de code, même partielle, ne peut être considérée comme sûre** tant que le propriétaire n'a pas explicité la licence. Par défaut, sans licence, le code relève du droit d'auteur et n'est pas réutilisable. *Ce n'est pas une « licence open source » : c'est une absence de licence.*

**Recommandation** : demander au propriétaire, avant toute extraction, (a) la licence du dépôt, (b) la licence de chaque dépendance tiers utilisée.

### 6.2 Dépendances — non gérées

**Aucune déclaration** : ni `pyproject.toml`, ni `requirements*.txt`, ni `setup.py`, ni `uv.lock`, ni `poetry.lock`, ni `Pipfile`. L'exécution se fait par `python -m crin.X` depuis la racine du dépôt.

Dépendances tiers relevées par analyse des imports dans `crin/` :

| Librairie | Fichiers qui l'importent | Remarque |
|---|---|---|
| `numpy` | 25 | socle numérique |
| `pandas` | 10 | |
| `scipy` | 8 | `crin/pool_math.py` (`scipy.optimize.minimize`), `crin/hawkes.py:28` (`scipy.optimize.minimize_scalar`) |
| `sklearn` | 2 | |
| `pyarrow` | 2 | |
| `lightgbm`, `xgboost`, `duckdb`, `openpyxl` | 1 chacun | |
| `tabpfn`, `tabicl` | 1 chacun | modèles tabulaires de fondation — **non déterministes sans verrou** |
| `sentence_transformers` | 1 | embeddings |
| `curl_cffi` (`scripts/crin/`) | 1 | hors package principal |

**Contradiction doctrinale constatée.** Le noyau revendique « *Stdlib only* » (`crin/benchmark.py:22`, `crin/contracts.py:37`, `crin/execution/provider.py:19`, `crin/quant_fund_validation.py:4`), mais `crin/pool_math.py` et `crin/hawkes.py` importent `scipy`. L'affirmation est **partiellement fausse** : elle vaut pour une partie du noyau, pas pour l'ensemble.

**Versions critiques : aucune n'est épinglée.** En particulier TabPFN, TabICL, `sentence_transformers`, `lightgbm` et `xgboost` sont des dépendances de modèles : sans verrou de versions, un résultat n'est pas reproductible.

### 6.3 Secrets

- **Structure déclarée** — `.env.example` (296 octets) déclare **quatre noms de variables** (conformément à la consigne, **aucune valeur n'est reproduite ici**) :
  - `ODDS_API_KEY` — clé d'API de cotes (le commentaire pointe vers `the-odds-api.com`, « clé gratuite (~500 req/mois) ») ;
  - `SQUIRREL_DB` — chemin du fichier SQLite ;
  - `TELEGRAM_BOT_TOKEN` — notification ;
  - `TELEGRAM_CHAT_ID` — destinataire.
- **Présence d'un `.env` réel : NON.** `Test-Path .env` → `False`. `.gitignore:6-8` ignore `.env` et `.env.*` sauf `.env.example`.
- **Pas de secret en clair observé.** Un balayage de motifs (`api_key`, `secret`, `token`, `bearer`, `password`, `private_key` suivis d'une valeur d'au moins 12 caractères) sur les `.py`, `.md`, `.bat`, `.json`, `.ps1` du dépôt donne **26 correspondances**, dont l'examen des formes montre **26 lectures d'environnement ou d'argument de ligne de commande**, et **zéro** valeur codée en dur : les affectations passent toutes par `os.environ.get` / `env.get` / des helpers `_load_api_key`, `_load_odds_api_key`, `_load_alchemy_key`, `_load_paid_key` (par exemple `crin/domains/horse/collector.py:454`, `crin/polymarket/live.py:254,386`).
- **Point d'attention** : `crin/execution/audit.py` est un « journal d'audit immuable » append-only JSONL dont le `details: dict` est sérialisé tel quel (`audit.py:39-61`). Il est propre et sans secret en l'état, mais un journal designed pour contenir des ordres réels devrait **redacter** toute valeur de jeton avant écriture. À traiter si TORNE adopte un journal d'audit.

---

## 7. Doublons, impasses, dette

### 7.1 Doublons et implémentations concurrentes

| Doublon | Emplacements | Observation |
|---|---|---|
| Dé-vig / Shin recalculé | `crin/sota_estimators.py:180 closing_shin_probs` vs `crin/benchmark.py:155 shin_probs` | **Doublon confirmé** : le module SOTA recalcule un Shin déjà implémenté dans le Core, au lieu de l'importer. |
| Référentiel de comparaison | `crin/benchmark.py` (Core), `crin/pool_vs_sharp.py:75`, `crin/domains/tennis/benchmark.py` | Le Core a été extrait explicitement (`crin/benchmark.py:17-20` : « *Shin/power/proportional vivent ICI (Core), pas sous domains/tennis/ […] Le domaine ne fait que choisir et câbler un provider* ») : le premier est une **correction assumée**, `pool_vs_sharp.py` reste un doublon partiel. |
| « Comparer un modèle au référentiel » | `crin/pipeline.py:115 evaluate_vs_pool`, `crin/gate_phase2.py`, `crin/sota_estimators.py:449 evaluate` | **Trois implémentations**, dont deux sans aucun test. |
| Pipeline « hflow » | `crin/hflow.py`, `crin/hflow_common.py`, `crin/hflow_anomaly.py`, `crin/hflow_reflex.py` | Quatre modules, un seul testé. |
| Collecteurs par verticale | `crin/domains/{horse,macro,tennis}/collector.py`, `crin/domains/market_efficiency/{mma_ufc,wnba}/collector.py` | Pattern répété (5 copies) plutôt qu'un socle commun. |
| Chaos de scripts | `scripts/hflow_basket_v3c.py`, `scripts/hflow_basket_v3c_nbaapi.py`, `scripts/hflow_basket_v3c_nbaapi_h0.py`, `scripts/mavis_recon/_v3c_offset_verify.py`, `_v3c_offset_verify2.py` | Versions successives jamais rangées. |
| Modifications de changelog scriptées | `scripts/mavis_recon/_changelog_prepend_v067.py`, `_v068.py`, `_changelog_insert_v055.py` | Le changelog est édité par script : fragile et non auditable. |

### 7.2 Code mort et chemins expérimentaux

- **`crin/execution/provider.py`** : trois implémentations annoncées, **aucune n'existe** dans le dépôt (recherche globale : seulement `provider.py` et `docs/operational/P10-EXECUTION-PROVIDER-DESIGN.md`). **Code mort par anticipation.**
- **`crin/domains/_parked/props/`** : verticale explicitement rangée (`_PARKED.md`) — **mais elle a encore un fichier de test** (`tests/test_props_archive.py`), donc du code mort entretenu.
- **`crin/domains/esports/`** : package vide (un seul `__init__.py`).
- **`scripts/mavis_recon/` (94 fichiers)** et **`scripts/paper_audit/` (14 fichiers)** : scripts d'exploration ponctuels, jamais importés, jamais testés, jamais packagés. Le préfixe `_` signale l'intention, mais ils restent dans l'arborescence et dégradent la lisibilité.
- **`scripts/crin/` (9 fichiers)** : **projet Stranger** — scanners de marketplaces de revente (Marktplaats/2ememain via Adevinta, eBay, Leboncoin, LBC) pour du LEGO, avec sa propre « bronze immuable », son polling jitter et `curl_cffi`. **Collision de nommage** avec le package `crin/` : quiconque parcourt le dépôt pour comprendre C.R.I.N. tombe sur un projet sans rapport.

### 7.3 Dette structurelle

1. **Aucun packaging, aucune dépendance déclarée, aucune version de package** (§6.2). Le dépôt n'est pas installable.
2. **Dépendances de modèles non pinnées** (`tabpfn`, `tabicl`, `sentence_transformers`, `lightgbm`, `xgboost`) : reproductibilité non garantie.
3. **Chemins absolus codés en dur** vers la machine d'origine (§5.5) : le dépôt ne tourne pas ailleurs.
4. **Windows-only** : `.bat`, Task Scheduler, chemins `C:\`, bug de fuseau documenté (`crin/runner.py:59-63`).
5. **Documentation en retard sur le code** : `README.md:52` (986 tests) contre 1 580 fonctions réelles ; dernier `CHANGELOG.md` au 2026-07-14 contre un clone du 2026-10-31.
6. **Contradiction interne dans `crin/README.md`** : la ligne « *FEATURE_SET (figé V0.3)* / FEATURE_SET_VERSION ("v0.3")* » contredit `crin/features.py:245 FEATURE_SET_VERSION = "v0.6"`.
7. **Doctrine « stdlib only » partiellement fausse** (§6.2).
8. **Le code qui décide n'est pas testé** (`crin/pipeline.py`) — dette de vérification, la plus coûteuse.
9. **Trace de génération assistée non relue** : `crin/drift.py:44` contient des caractères CJK (« 惯例金融 ») insérés au milieu d'un commentaire français sur les seuils PSI. *Fait observé* : les caractères sont là. *Inférence* : trace de copier-coller ou de génération IA non relue.
10. **Journal d'audit et exécution sans implémentation** : `crin/execution/audit.py` est propre et réutilisable, mais il est le satellite d'une abstraction qui n'a pas d'implémentation.
---

## 8. Verdict par composant

| Composant | Chemin | État | Décision | Justification (une phrase, vérifiable) | Coût de reprise |
|---|---|---|---|---|---|
| Registre de pré-enregistrement + amendements datés | `docs/hypotheses/active/` (16), `docs/hypotheses/killed/` (9) | documenté uniquement | **REUSE** | 25 preregs structurés (hypothèse, seuil, conditions de validité, kill-switch) ; à durcir en exigeant date + commit, comme le format BORÉE. | Faible |
| Gouvernance du choix de la correction de multiplicité | `crin/quant_fund_validation.py:64-70` | documenté uniquement | **REUSE** | Interdit explicitement l'« α-shopping » et fixe Bonferroni par défaut : règle directement transposable, à porter dans `PREREG.md`. | Faible |
| Gates G0 → G7 (conditions de passage, kill) | `docs/concepts/GATES.md` | documenté uniquement | **REUSE** | Gouvernance pure, sans code : recopiables tels quels dans la documentation TORNE. | Faible |
| Matrices déterministes (passe chronologique unique) | `crin/datasets.py:929`, `:1331` | implémenté et vérifié | **REUSE** | Une seule passe chronologique, état lu avant mise à jour ; déterminisme prouvé par `tests/test_crin_datasets.py:221`. | Faible |
| Test anti-fuite « une observation future ne change rien » | `tests/test_crin_datasets.py:263` | implémenté et vérifié | **REUSE** | `test_post_chronological_label_does_not_change_features` est exactement le test anti-fuite exigé par le protocole BORÉE. | Faible |
| Artefact de modèle auto-porteur | `crin/models.py:79-98` | implémenté et vérifié | **REUSE** | L'artefact embarque l'ordre des colonnes, la version du feature set et l'état de standardisation ; testé par `tests/test_crin_models_artifact.py`. | Faible |
| Alignement entraînement / inférence | `crin/models.py:141-149`, `:115-125` | implémenté et vérifié | **REUSE** | Standardisation apprise au fit et rejouée à l'inférence ; le bug qui l'avait motivé est documenté avec son Brier (0.107). | Faible |
| Manifeste d'expérience | `crin/manifest.py:24,44,66` | implémenté et vérifié | **REUSE** | Commit + indicateur `dirty` + version Python + config + facteurs : à compléter par une empreinte de contenu. | Faible |
| Corrections de multiplicité (BH, Bonferroni, Romano-Wolf) | `crin/multiple_testing.py:109,142,149` | implémenté et vérifié | **REUSE** | Stdlib pur, testé, et le choix est déjà gouverné par la prereg. | Faible |
| SPA, PBO/CSCV, Deflated Sharpe, bootstrap cluster | `crin/quant_fund_validation.py:172,403,604`, `:138` | implémenté et vérifié | **REUSE** | Outils agnostiques du domaine, avec l'avertissement documenté sur le bootstrap iid et ses trois remèdes. | Moyen |
| e-values et confidence sequences | `crin/evalues.py:64,146,194` | implémenté et vérifié | **REUSE** | Numpy seul, testé par propriétés avec l'estimateur de Waudby-Smith comme référence. | Faible |
| Moniteur de flux (ROI) et déviation Brier | `crin/evalues.py:239,454` | implémenté et vérifié | **ADAPT** | La mécanique de surveillance de flux est générique ; la sémantique de mise et de ROI ne l'est pas. | Faible |
| Métriques de calibration (Brier, log-loss, ECE, DM apparié) | `crin/calibration.py:35,54,84,119,204` | implémenté et vérifié | **REUSE** | Stdlib pur ; le DM apparié par course est le bon test de comparaison entre deux modèles. | Faible |
| Recalibration isotonique (PAV) et Platt | `crin/recalibration.py:76,104,150` | implémenté et vérifié | **REUSE** | Implémentation complète de PAV, testée, agnostique du domaine. | Faible |
| Prédiction conforme Venn-ABERS | `crin/conformal.py:70,233` | implémenté et vérifié | **ADAPT** | Le cœur Venn-ABERS est général, mais le module est couplé au Kelly et à la dérive. | Moyen |
| Détection de dérive par PSI | `crin/drift.py:147,171` | implémenté et vérifié | **REUSE** | PSI par feature sur bins d'égale fréquence, trois états, testé ; à re-calibrer et à coupler à une explication. | Faible |
| Pont Bronze → features pour la dérive | `crin/drift_bridge.py:273,331` | implémenté et vérifié | **ADAPT** | Le patron (reconstruire la matrice depuis la couche brute pour mesurer la dérive) est excellent ; la réalisation est liée au modèle hippique. | Moyen |
| Contrats d'ingestion (5 dimensions + streak N jours) | `crin/contracts.py` | implémenté et vérifié | **ADAPT** | La mécanique du streak est excellente ; le vocabulaire null-rate-par-colonne est celui d'un schéma tabulaire. | Moyen |
| Convention tritemporelle / point-in-time | `crin/tritemporal.py:61,73` | implémenté et vérifié | **REUSE** | `is_visible_asof` formalise la règle « une donnée n'est visible qu'à partir de son temps de connaissance » ; clé pour TORNE. | Faible |
| Comparaison de K estimateurs + harnais de sanité | `crin/sota_estimators.py:209,245,449,539` | implémenté et vérifié | **ADAPT** | Le patron (budget égalisé, renormalisation, edge injecté détecté) est excellent ; les estimateurs eux-mêmes sont à écarter. | Moyen |
| Estimateurs TabPFN / TabICL | `crin/sota_estimators.py:280,355` | implémenté et vérifié | **REJECT** | Dépendances de modèles non pinnées et sans verrou ; la comparaison d'estimateurs sera refaite sur des choix TORNE. | — |
| Pipeline d'hypothèses preregistrées + kill-switch | `crin/pipeline.py` (1 765 l.) | implémenté mais non vérifié | **REIMPLEMENT** | Aucun test ne l'importe, et il est imbriqué dans le pool hippique ; le patron doit être re-écrit proprement. | Élevé |
| Gate Phase 2 (modèle vs référentiel) | `crin/gate_phase2.py` | implémenté mais non vérifié | **REIMPLEMENT** | La comparaison avec une baseline triviale avait été invalidée : le principe de « référentiel » est bon, le code est à refaire et à tester. | Moyen |
| Journal d'audit append-only | `crin/execution/audit.py:39-61` | implémenté mais non vérifié | **ADAPT** | Écriture atomique ligne à ligne, stdlib ; à redactionner et à tester avant tout usage. | Faible |
| Pattern « payload brut immuable » | `crin/db.py:9-11` | implémenté et vérifié | **REUSE** | « *si la convention retenue se révèle fausse, la correction est rétroactive, rien n'est perdu* » : principe directement utile à TORNE. | Faible |
| Runner long, heartbeat, arrêt gracieux | `crin/runner.py:91` | implémenté et vérifié | **ADAPT** | Utile pour l'exploitation quotidienne, sans rapport avec la production de connaissance. | Faible |
| Processus Hawkes (baseline inhomogène figée) | `crin/hawkes.py:1-21` | implémenté et vérifié | **ADAPT** | Méthode agnostique (processus d'événements) ; à corriger (RNG sans graine, `scipy` non épinglé). | Moyen |
| Pipeline HTML → embeddings | `crin/text_embeddings.py` | implémenté et vérifié | **ADAPT** | Le besoin (extraire de l'information de pages) est réel pour TORNE, la dépendance `sentence_transformers` doit être verrouillée. | Moyen |
| Ingestion on-chain / marché prédictif | `crin/polymarket/` | implémenté mais non vérifié | **REJECT** | 1 908 lignes sans aucun test, API spécifique ; le concept (événement public on-chain) est à reconsidérer par ailleurs. | — |
| Elo générique | `crin/elo.py` | implémenté et vérifié | **ADAPT** | Rating générique réutilisable pour des grandeurs ordonnées, mais utilité non démontrée tant qu'il n'y a pas de vertical slice. | Faible |
| Math de pool (takeout, Harville, Henery) | `crin/pool_math.py` | implémenté et vérifié | **REJECT** | Répond à la question « quelle est la probabilité implicite d'un marché à cotes » : TORNE n'a pas de marché de paris. | — |
| Dé-vig Shin / power / proportionnel | `crin/benchmark.py:111,122,155` | implémenté et vérifié | **REJECT** | Dé-viguer un overround n'a de sens que face à un marché de cotes. | — |
| Kelly et le sizing | `crin/policy.py`, `crin/conformal.py:37,53` | implémenté et vérifié | **REJECT** | Suppose une bankroll, une cote et un contrat de pari : hors du périmètre de TORNE à ce stade. | — |
| Settlement hippique | `crin/paper_bet.py`, `crin/edge.py` | implémenté et vérifié | **REJECT** | Le code est hippique ; le **principe** (régler au moment du vérité) est repris comme règle tritemporelle. | — |
| Features PMU (58 colonnes) | `crin/features.py` | implémenté et vérifié | **REJECT** | Variables hippiques sans sens hors du galop et du trot. | — |
| Normalisation des cotes / enjeux par endpoint | `crin/units.py` | implémenté et vérifié | **REJECT** | Convention propre aux endpoints de cotes. | — |
| Screen Hausch-Ziemba | `crin/hz_screen.py` | implémenté et vérifié | **REJECT** | Écran d'inefficience d'un marché pari-mutuel. | — |
| Domain adapters génériques (43 fichiers) | `crin/domains/base.py` + `crin/domains/` | implémenté et vérifié | **REJECT** | Abstraction anticipant six verticales de paris : ce que la MISSION §9 interdit explicitement. | Élevé |
| Interface d'exécution (3 impls annoncées) | `crin/execution/provider.py:3` | documenté uniquement | **REJECT** | Aucune implémentation n'existe dans le dépôt : à ne pas hériter. | — |

---

## 9. Ce que je n'ai pas pu faire

1. **Aucun commit n'est vérifiable.** Il n'y a **pas de binaire `git`** sur ce poste (recherche sur `C:\Program Files\Git\cmd\git.exe`, `C:\Program Files\Git\bin\git.exe`, `C:\Program Files (x86)\Git\…`, `%LOCALAPPDATA%\Programs\Git\…`, et `Get-Command git.exe` → aucun résultat). J'ai donc lu `.git/HEAD`, `.git/config`, `.git/refs/heads/main`, `.git/packed-refs`, `.git/logs/HEAD` et `.git/objects/pack/` **en tant que fichiers**, sans pouvoir exécuter `git log`, `git show`, `git blame` ni `git status`. Conséquence : **aucun commit n'est cité comme preuve** dans ce rapport ; le seul identifiant de commit disponible est `015d263e6a3e4a56bc395a0ef0dd43c595067e60` (HEAD de `main`, lu dans `.git/refs/heads/main`), et le reflog ne contient qu'une entrée de clone (2026-10-31 13:54:51 UTC), donc **l'auteur et la date de chaque changement sont inconnus**.
2. **Aucun test n'a été exécuté.** Ni `pytest`, ni `unittest`, ni aucun script. Les affirmations « testé » reposent sur la **présence et le contenu** des fichiers de `tests/`, jamais sur une exécution. Je ne peux donc pas affirmer que les 1 580 tests passent ; le README dit « 986 tests (12/07) » et `crin/README.md:83` « 777 tests verts », sans horodatage de dernière exécution vérifiable.
3. **Le pack git (210 Mio) n'a pas été décompressé** : impossible sans binaire `git`, et sans intérêt pour l'audit demandé.
4. **`data/` n'a pas été inspecté** (37 fichiers binaires/CSV, ~52 Mo) : je n'ai pas vérifié le contenu des bases SQLite, ni le schéma réel des tables en production, ni les volumes de courses effectivement archivées. Les volumétries citées (`crin/training_data.py:33` : « ~36 000 courses FR en 2 ans / ~12 partants = ~430 000 ») sont des **estimations de commentaire de code**, pas des mesures.
5. **82 fichiers de `docs/` n'ont pas été lus** (90 au total, 8 lus) : en particulier le contenu complet des 15 preregs actives et des 9 preregs tuées. Je n'ai vérifié la structure d'une prereg (`CRIN-DATA-prereg.md`, `H-FLOW-HAWKES-prereg.md`) et compté le registre, sans auditer chaque protocole un par un.
6. **Les 204 scripts de `scripts/` n'ont pas été lus** : inventaire par signature et première ligne de docstring uniquement, plus lecture de 3 fichiers. Les 94 fichiers de `scripts/mavis_recon/` et les 14 de `scripts/paper_audit/` n'ont pas été analysés.
7. **L'index git n'a pas pu être décodé de façon fiable** (la lecture binaire du `.git/index` via l'API de fichiers du poste renvoie des octets que la recherche de chaînes ne retrouve pas) : je n'ai donc pas pu établir, fichier par fichier, ce qui est suivi par git. L'analyse de §5.2 sur les données versionnées est une **inférence**, signalée comme telle.
8. **Pas d'analyse de la qualité statistique réelle des résultats publiés** : les rapports de `docs/phase2-gate/` (7 fichiers JSON) et de `docs/reports/` n'ont pas été recalculés ni vérifiés.
9. **Pas d'audit de sécurité** : j'ai vérifié l'absence de `.env` et l'absence de secret en clair par motif, mais je n'ai pas audité les flux réseau, la validation des entrées, ni les dépendances (aucune n'est épinglée, donc pas d'audit de CVE possible).
10. **Aucun test de non-régression n'a pu être écrit ni exécuté** pour vérifier que le code audité se comporte comme le décrivent ses docstrings.
11. **`crin/execution/audit.py` a été lu** (64 lignes) mais **pas `crin/execution/__init__.py` ni le design P10** au-delà de la mention dans le module.

---

## 10. Ce qui est transposable, ce qui est à réécrire, ce qui est à laisser

### 10.1 Transposable tel quel — la philosophie expérimentale

1. **Le registre de pré-enregistrement** (prereg active / prereg tuée), avec pour chaque hypothèse : méthode, seuil, conditions de validité, kill-switch, amendements datés. *À durcir* : date + commit obligatoires sur chaque amendement, comme dans `PREREG.md` du protocole BORÉE.
2. **Le test anti-fuite** : « une observation future ne modifie aucune variable dérivée antérieure » (`tests/test_crin_datasets.py:263`). C'est le test que le protocole BORÉE exige déjà sur son store synthétique.
3. **L'artefact auto-porteur** : ordre des colonnes, version du schéma, état de normalisation, commit, horodatage (`crin/models.py:92-98`).
4. **La règle de standardisation unique** : apprise au fit, stockée dans l'artefact, rejouée à l'inférence (`crin/models.py:141-149`).
5. **Le manifeste d'expérience** : commit, `dirty`, version Python, configuration, facteurs (`crin/manifest.py:44`) — à compléter par une empreinte de contenu et une graine.
6. **Les corrections de multiplicité** et, surtout, **la gouvernance de leur choix** (`crin/quant_fund_validation.py:64-70`).
7. **Les outils d'overfitting** : SPA, PBO/CSCV, Deflated Sharpe, bootstrap cluster (`crin/quant_fund_validation.py`).
8. **Les e-values et confidence sequences** (`crin/evalues.py:64,146`).
9. **Les métriques de calibration** et la **recalibration isotonique** (`crin/calibration.py`, `crin/recalibration.py`).
10. **La convention tritemporelle** `is_visible_asof` (`crin/tritemporal.py:61`) — la brique la plus directement utile à la reconstitution d'états physiques de TORNE.
11. **Le PSI de dérive** (`crin/drift.py`), à re-calibrer et à coupler à une explication.
12. **Le pattern « payload brut immuable »** (`crin/db.py:9-11`) et le **journal d'audit append-only** (`crin/execution/audit.py`).
13. **Le harnais de sanité à signal injecté** (`crin/sota_estimators.py:539`) : vérifier qu'un pipeline détecte un edge qu'on a planté, avant de croire un edge qu'il a trouvé.

### 10.2 À réécrire

1. **Le pipeline d'hypothèses preregistrées** (`crin/pipeline.py`) : garder le patron (hypothèse → conditions de validité → seuil → rapport → kill), réécrire le code, et **le tester**.
2. **Le split temporel** : le renommer (`split_temporel_3_blocs`) et lui ajouter un vrai walk-forward avec repli, ré-entraînement et recalage — la discipline existe chez C.R.I.N. mais pas sous le nom qu'elle porte.
3. **Le lien prereg → exécution → verdict** : l'outiller, afin qu'un rapport orphelin ou une prereg sans rapport soit détectable automatiquement. C'est le seul manque structurel majeur de la discipline.
4. **Les contrats d'ingestion** : garder la mécanique du streak, remplacer le vocabulaire null-rate-par-colonne par une formulation adaptée aux grandeurs dérivées de TORNE.
5. **La normalisation et le provisioning des estimateurs** : refaire la comparaison sur des choix TORNE, sans TabPFN/TabICL.
6. **La convention de reproductibilité** : graine globale explicite et journalisée, empreinte de contenu des jeux de données et des artefacts, verrou de versions des dépendances — trois choses absentes du dépôt audité.

### 10.3 À laisser dans SquirrelBetting

1. **Tout `crin/features.py`** (58 colonnes hippiques) et `crin/domains/horse/`.
2. **Tout le pool et le dé-vig** : `crin/pool_math.py`, `crin/benchmark.py`, `crin/pool_vs_sharp.py`, `crin/sota_estimators.py:180`, `crin/hz_screen.py`.
3. **Le staking** : `crin/policy.py`, `crin/conformal.py:37,53`.
4. **Le settlement et l'edge** : `crin/paper_bet.py`, `crin/edge.py` — en ne gardant que le principe.
5. **Les domain adapters** (`crin/domains/`, 43 fichiers) et l'interface d'exécution (`crin/execution/provider.py`).
6. **La collection par verticale** (`crin/units.py`, `crin/domains/*/collector.py`) et le projet Stranger `scripts/crin/`.
7. **Les 108 fichiers de scripts d'exploration** (`scripts/mavis_recon/`, `scripts/paper_audit/`) : à ne pas importer, mais à traiter comme la preuve qu'une discipline produit beaucoup de code jetable — que TORNE doit prévoir d'héberger hors du paquet livré.

### 10.4 Le mot de la fin

C.R.I.N. est un **excellent laboratoire de rigueur expérimentale mal empaqueté**. Sa valeur pour TORNE n'est pas dans son architecture — qui est celle d'un système de paris à six verticales, sans packaging, sans dépendances déclarées, non portable, et dont le module de verdict n'est pas testé. Sa valeur est dans **cinq ou six mécanismes précis et éprouvés** : le registre de pré-enregistrement avec amendements et kills, le test anti-fuite, l'artefact auto-porteur, la gouvernance explicite de la correction de multiplicité, l'outillage de l'overfitting (SPA / PBO / DSR), et la point-in-time. Ces six choses sont **réutilisables telles quelles**, à condition de les porter dans le format BORÉE (amendement daté, commité avant calcul) et de les **tester** — ce que C.R.I.N. n'a pas toujours fait.

Ce qu'il ne faut pas faire, c'est hériter du **reste** : ni les features, ni le pool, ni Kelly, ni les domaines, ni le pipeline. Et il faut se garder de l'erreur inverse, qui serait de reconstruire un registre de preregs, un test anti-fuite et une discipline de multiplicité **en croyant que cela ne s'invente pas** : C.R.I.N. a mis trois mois et vingt-cinq hypothèses pour y arriver, dont neuf tuées.