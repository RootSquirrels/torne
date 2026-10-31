# TORNE — Matrice de réutilisation

**Consolidée — 31 octobre 2026**
**Statut : décision.** Les trois rapports d'archéologie sont produits (`docs/audit/ATHANOR.md`,
`docs/audit/CRIN.md`, `docs/audit/LEGACY-BOREE.md`) ; cette page les.reduce à une seule décision par composant.

**Aucun code n'a été exécuté pendant cette phase** : `uv` est absent du poste de construction et le paquet
`athanor` n'y est pas installé. Les états reposent sur la lecture du code et des tests, pas sur une exécution. Le
premier commit ne contient donc que le socle documentaire — aucune brique extraite n'est encore dans le dépôt.

## 1. Format de la matrice

Chaque composant candidat occupe une entrée portant exactement les onze champs suivants.

| Champ | Description |
|---|---|
| Composant | Origine | Ã‰tat | Décision | Justification | Coût de reprise |
|---|---|---|---|---|---|
| Composant | Nom et fonction réelle |

Règles de remplissage :

- Un composant n'est retenu que si son **origine** est vérifiable : chemin exact et commit.
  Un composant dont l'origine ne peut être établie est écarté, même s'il paraît prometteur.
- L'**état** distingue ce qui est implémenté et vérifié de ce qui n'est que spécifié dans un
  document. Un document d'architecture n'est pas une implémentation.
- Les **tests** citent les tests existants et leur résultat observé, pas une intention.
- La **licence** est notée « vérifiée » seulement si le fichier de licence a été lu ; sinon
  « inconnue », et le composant est traité comme non réutilisable en l'état.
- « Implémenté et testé » signifie **couvert par un test nommé**, jamais « exécuté et passé » : aucun code n'a été exécuté pendant cette phase.
- La colonne « Coût » exprime le **volume de lignes à reprendre** lorsqu'il est connu, et « — » lorsqu'il ne l'est pas.
- La **décision** est unique : un composant ne peut pas être à la fois repris et écarté. Les
  ambiguïtés se tranchent par un argument supplémentaire, pas par une case « à étudier ».

Les tables ci-dessous reprennent **verbatim** les tableaux de verdict des trois rapports : les six colonnes correspondent aux onze champs,
les champs omis (tests, dépendances, domaine, licence, valeur) sont détaillés dans la justification et dans les
rapports d'origine, qui font foi.

## 2. Les quatre décisions possibles

### REUSE

Le composant fonctionne, est suffisamment indépendant et peut être repris avec un coût
raisonnable. Il est repris tel quel, ou recopié et adapté au nouveau contexte sans changement
de comportement. Cette décision n'exige pas de réécriture.

### ADAPT

Le principe est bon, mais l'implémentation doit être simplifiée ou adaptée : dépendances
réduites, périmètre restreint, conventions de données du socle, suppression d'une couche
superflue. Ce qui est conservé est nommé ; ce qui est retiré est nommé.

### REIMPLEMENT

Le comportement est utile, mais le code est trop imbriqué, trop complexe ou insuffisamment
fiable pour être repris tel quel. Le comportement est réécrit proprement dans TORNE, à partir
de la spécification observée et non de l'implémentation existante. Le comportement de référence
reste la source de vérifiabilité du résultat.

### REJECT

Le composant ne correspond pas à TORNE, fait double emploi, ou n'apporte pas de valeur
démontrée. Il est écarté, et la raison est consignée : le rejet est une décision documentée,
pas un oubli.

## 3. Athanor — `athanor@6dacc87`

Rapport complet : `docs/audit/ATHANOR.md` (374 lignes).

| Composant | Origine | Ã‰tat | Décision | Justification | Coût de reprise |
|---|---|---|---|---|---|
| Bootstrap par grappes + ratio | `stats/resampling.py` | Implémenté et vérifié | **REUSE** | `tests/test_stats.py:22,31,38` prouvent détection, déterminisme et résistance au jackpot ; aucun import hors `stats/` | ~190 l., numpy seul |
| e-processus / suites de confiance | `stats/evalues.py` | Implémenté et vérifié | **REUSE** | 37 tests dont validité à tout instant (Ville) et couverture uniforme en t (`tests/test_evalues.py:1-8`) ; contrat de bornage strict corrigé (`:25-27`) | ~412 l., numpy seul |
| Budget d'alpha / e-LOND | `stats/online_fdr.py` | Implémenté et vérifié | **REUSE** | Garantie mFDR ≤ α à vie (Foster & Stine 2008) et FDR ≤ α sous dépendance arbitraire (Xu & Ramdas 2024) ; `tests/test_elond.py`, `tests/test_stats.py:45,59` | ~97 l., stdlib seul |
| Multiplicité (FWER/FDR/Romano-Wolf) | `stats/multiplicity.py` | Implémenté et vérifié | **REUSE** | 15 tests ; Romano-Wolf stepdown correctement implémenté (suffix max, `multiplicity.py:133`) | ~108 l. |
| Sur-apprentissage (SPA/PBO/DSR) | `stats/overfitting.py` | Implémenté et vérifié | **REUSE** | 27 tests contre les définitions publiées ; studentisation et recentrage corrects (`:5-7`) | ~287 l. |
| Puissance / effet de plan | `stats/power.py` | Implémenté et vérifié | **REUSE** | 14 tests ; permet le KILL_DATA honnête (« un test sans puissance n'est pas une absence d'effet », `:3-5`) | ~176 l. |
| Calibration + Diebold-Mariano | `stats/calibration.py` | Implémenté et vérifié | **REUSE** | 18 tests ; HAC Newey-West et comparaison appariée | ~198 l. |
| Intervalles de proportion | `stats/intervals.py` | Implémenté et vérifié | **REUSE** | 28 tests ; 6 estimateurs (Wilson, CP, Jeffreys, Newcombe, beta) | ~293 l. |
| Variance réduite / CUPED | `stats/variance_reduction.py` | Implémenté et vérifié | **REUSE** | 10 tests ; utile pour la reconstitution d'états (réduction de variance par contrôles) | ~151 l. |
| Scoring différentiel normalisé | `stats/scoring.py` | Implémenté et vérifié | **REUSE** | La normalisation par portée prévisible (`scoring.py:27-32`) est la bonne idée ; 10 tests | ~131 l. |
| Ruptures CUSUM | `stats/breaks.py` | Implémenté et vérifié | **REUSE** | 7 tests ; détecte un changement de régime (utile : dérive de modèle physique) | ~75 l. |
| OLS / bêta de couverture | `stats/regression.py` | Implémenté et vérifié | **REUSE** | 52 l., CR1 par grappes ; base de `variance_reduction` | ~52 l. |
| Écart acheteur-vendeur OHLC | `stats/spreads.py` | Implémenté et vérifié | **ADAPT** | EDGK 2024 testé contre la valeur publiée `0,0101849034905478` — excellent ; mais suppose des séries OHLC de marché financier | ~66 l. |
| Journal chaîné / empreintes / horloge | `kernel/journal.py`, `hashing.py`, `clock.py` | Implémenté et vérifié | **REUSE** | Autonome (2 imports kernel), append-only chaîné, verrous inter-processus ; le format d'événement est générique | ~270 l. |
| Magasin brut point-in-time | `data/rawstore.py` | Implémenté et vérifié | **ADAPT** | La sémantique point-in-time est exactement celle de TORNE (`known_at` posé par le magasin, `:9`) ; mais l'implémentation est couplée au format S3/lakehouse Garage d'Athanor | ~455 l. |
| Cycle d'exploration journalisée | `research/explore.py` | Implémenté et vérifié | **ADAPT** | La mécanique (famille → consigne → brûle → rétréci → validation sur données neuves) est la brique la plus transposable pour chercher des modèles ; 18 tests ; vocabulaire à remplacer | ~411 l. |
| Moteur de validation hors échantillon | `measures/correlation/model.py` | Implémenté et vérifié | **ADAPT** | Ridge + λ par validation interne + purge + embargo 30 j + seuil hors pli : conception intègre et éprouvée, mais `FOLDS` codé en dur (`model.py:31`), `Outcome.net(side, borrow)` est une interface de pari, et seulement 4 tests | ~255 l. à extraire |
| Noyau du juge | `research/verdict.py` | Implémenté et vérifié | **ADAPT** | Multi-structures prudentes, e-processus vs bootstrap, auxiliaires, plancher, couverture, robustesse :Excellent ; mais un seul `VERDICT_RENDERED` au journal → jamais exercé en série | ~376 l. |
| Échelle de verdicts et phases | `research/protocol.py` | Implémenté et vérifié | **ADAPT** | Le squelette `[power]`/`[robustness]`/`[[auxiliary]]`/fenêtres à trous est excellent ; mais `Verdict` (KILL→CONFIRMED) et `Phase` (DISCOVERY/CONFIRMATION/FORWARD) sont orientés « mise en argent » — TORNE a besoin d'un axe physique et d'un axe financier | ~515 l. |
| Registre d'hypothèses | `research/registry.py` | Implémenté et vérifié | **ADAPT** | Machine à états + application d'événements + budget par endpoint, très propre ; vocabulaire « fiche / a priori / mise / LIVE » à refaire | ~424 l. |
| Gestion du risque | `book/risk.py` | Implémenté et vérifié | **ADAPT** | Kelly sur **borne basse**, alarme e-processus, e-détecteur de décroissance, drawdown : principes transférables à la couche financière de TORNE ; `BetEdge.decimal_odds` et `RealSettlement` sont à réécrire | ~450 l. |
| Charte de l'opérateur | `research/charter.py` + `charter.toml` | Implémenté et vérifié | **ADAPT** | Le mécanisme de porte d'entrée (refuser une piste non rentable) est excellent ; mais `charter.toml` mélange objectifs business et constantes statistiques (`fdr_target=0.10`) | ~73 l. |
| Garde-fous de dépôt | `tools/guardrails.py` | Implémenté et vérifié | **REIMPLEMENT** | Le principe (un script vérifie l'architecture) est excellent, mais les règles portent sur la structure d'Athanor : le réécrire sur les invariants de TORNE | ~300 l. estimés |
| Couche données / 22 sources | `data/sources/*`, `data/warehouse.py`, `data/datasets.py` | Implémenté et vérifié | **REJECT** | 100 % spécifique aux marchés financiers, hippiques, crypto et météo étudiés par Athanor ; TORNE a ses propres sources (ENER, réseau électrique, météo…) | — |
| Mesures métier (30 modules) | `measures/*` | Majoritairement obsolètes | **REJECT** | 7 modules marqués « REJEU SEULEMENT », les 23 autres sont des règles de mesure hyper-spécifiques (`reaction.py`, `technicals.py`, `gas_markets.py`…) | — |
| Marchés / pari mutuel / carnet | `markets/*`, `book/ledger.py` | Implémenté et vérifié | **REJECT** | Cotes décimales, dividendes mutuels, impact sur le pool : aucun rapport avec la reconstitution d'états physiques | — |
| Forge (gabarits) | `forge/*` | Implémenté | **REJECT** | Gabarits de mécanismes de pari (`two_crowds`, `pool_overlay`) ; TORNE aura ses propres gabarits de reconstitution | — |
| Opérations (17 modules) | `ops/*` | Implémenté | **REJECT** | Battement, collectes PMU/crypto, risk_watch : cycle de vie d'un système de trading, pas d'une plateforme de connaissance | — |
| Études et legacy | `studies/*`, `research/legacy.py` | Documenté, non conclu | **REJECT** | Aucun verdict rendu, pistes hippiques/crypto arrêtées ; seule la **doctrine** garde de la valeur | — |
| La doctrine (leçons) | `docs/DOCTRINE.md` | Documenté | **ADAPT** | 9 leçons étayées par des verdicts (L1–L9) + 5 familles de mécanismes + les règles du jugement : c'est un actif de **raisonnement**, pas de code ; à réécrire en français pour TORNE, avec d'autres preuves | ~110 l. de texte |

## 4. SquirrelBetting / C.R.I.N. â€” `SquirrelBetting@015d263`

Rapport complet : `docs/audit/CRIN.md`.

| Composant | Origine | Ã‰tat | Décision | Justification | Coût de reprise |
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

## 5. Ancien BORÉE — `boree@4b6d130`

Rapport complet : `docs/audit/LEGACY-BOREE.md`.

| Composant | Origine | Ã‰tat | Décision | Justification | Coût de reprise |
|---|---|---|---|---|---|
| Règles de disponibilité (point de vue décision) | `src/boree/temps.py` | I+ | **REJECT** | Hors périmètre explicite (`REUSE_AUDIT.md:88-89`) et contenu 100 % électrique ; le pattern, lui, est repris | Faible (pattern) |
| Lecture point-in-time `tel_que_connu` | `src/boree/lac/connu.py` | I+ | **ADAPT** | Mécanique générique ("telle que connue à t" = une requête, pas une copie) ; dépend de `temps.py`, donc a réécrire | Moyen |
| Catalogue déclaratif des jeux | `src/boree/lac/catalogue.py`, `docs/LAC.md` | I+ | **ADAPT** | La structure `Jeu` (règle nommée, granularité, publication, schéma) est domaine-indépendante ; le contenu est 100 % FR/DE | Moyen |
| Forme dérivée Parquet/DuckDB du lac | `src/boree/lac/parquet.py` | I+ | **ADAPT** | Brut = vérité, dérivé = reconstructible ; partitionnement `annee=/mois=`, DuckDB local sans serveur, réécriture atomique | Moyen |
| Magasin brut versionné, empreintes, `ref(asof=)` | `src/boree/archive.py` | I+ | **REJECT** | Doublon de `athanor.data.rawstore.RawStore`, qui pose même `known_at`, même point-in-time, en plus robuste | Faible (rien à recopier) |
| Copie S3 / Garage, intégrité, instantané | `src/boree/exploitation/garage.py` | I+ | **REJECT** | Le client S3 fait doublon avec `athanor.data.s3` ; **en revanche les trois règles sont à porter** (voir 2.10) | Faible |
| Règle "local d'abord, copie après" | `exploitation/garage.py:3-7` | I+ | **ADAPT** | "une panne de Garage retarde la copie, elle ne perd rien" -- contrainte d'architecture indépendante du domaine | Faible |
| Règle "intégrité par empreinte, jamais par décodage" | `exploitation/garage.py:12-13, 47-53` | I+ | **ADAPT** | Verification par hash sans ouvrir le document : s'applique tel quel à tout stockage scellé | Faible |
| Scelles et accès machine unique | `src/boree/scelles.py`, `final.py`, `direct.py` | I+ | **REJECT** | Code entièrement lié au protocole prospectif BOREE ; le **principe** (barriere unique, refusée par défaut, testée) est à porter | Moyen |
| Connecteurs ENTSO-E / Open-Météo / EEX | `src/boree/ingest/entsoe_api.py`, `ecmwf_direct.py`, `eua.py`, `europe.py`, `runs.py` | I+ | **REJECT** | Tous lies au marché de l'électricité ; le contrat de connecteur équivalent existe dans `athanor.data.source` | Nul |
| Modèle de collecteur (plan / collect / parse) | `ingest/sources.py` | I+ | **REJECT** | Doublon de `athanor.data.source` (+ `data/compliance.py` pour robots.txt et conditions d'usage) | Faible |
| Normalisation horaire (quarts -> heures, 2 h local) | `src/boree/temps.py:86-95` | I+ | **ADAPT** | Generique et testé ; à porter comme brique isolée, sans les règles de disponibilité | Faible |
| Registre d'unités et référentiel spatial | -- | **absent** | **REIMPLEMENT** | Aucun registre d'unités, aucun CRS, aucune géométrie dans le dépôt : BOREE n'apporte rien la | Élevé |
| Lignage 4 colonnes (`_source`,`_cle`,`_empreinte`,`_connu_a`) | `src/boree/lac/connu.py:32`, `lac/parquet.py:42-43` | I+ | **ADAPT** | Trivial, générique, et la preuve que la version et son instant de connaissance voyagent ensemble | Faible |
| Gel de la fermeture du code de mesure | -- | dans `athanor` | **REJECT** | `athanor.research.provenance` fait déjà mieux (fermeture transitive des imports, preuve d'équivalence, juge et environnement) | Nul |
| Registre de modèles (contrats TOML, statuts) | `src/boree/registre/contrat.py`, `registre/*.toml` | X | **REJECT** | Doublon de `athanor.research.registry`, qui est une machine à états rejouée depuis le journal et prévoit déjà `LEGACY_VERDICT -> ARCHIVED` | Faible |
| Methode de parité bit-a-bit + critère de bascule | `src/boree/registre/chaine.py:89-121` | X | **ADAPT** | "conforme / différente / non compare", `PARITE_MIN = 14/16`, aucun écart : méthode de migration saine, à réutiliser telle quelle | Faible |
| Controle du registre (empreintes, code de sortie 1) | `src/boree/registre/verifier.py` | X | **ADAPT** | Pattern "un contrôle exécutable qui sort en 1" à généraliser ; à réécrire sur le registre de TORNE | Faible |
| Chaine générique en ombre | `src/boree/registre/chaine.py` | X | **REJECT** | Experimental, lié à H2/H3/H4, et sa valeur est dans la méthode de parité (ligne du dessus) | Faible |
| Jumeau physique | `src/boree/physique/jumeau.py` | O | **REJECT** | Résultat retiré : "les chiffres étaient faux (production moyennee au lieu d'être sommée)" (`RESULTAT_jumeau.md`) | Nul |
| Empilement prévu au soir de J-1 | `src/boree/physique/empilement.py` | I+ | **REJECT** | Modèle physique du marché FR, explicitement "hors modèle" (`PROTOCOLE.md:144-145`) | Nul |
| Contexte physique (pression, decroche, angle zénithal) | `src/boree/physique/contexte.py` | I+ | **REJECT** | Hors gel et hors modèle ; TORNE n'a pas ces grandeurs | Nul |
| Geospatial et multidimensionnel | `physique/contexte.py`, `lac/connu.py:33` | I+ | **REIMPLEMENT** | Aucune géométrie ni CRS : la "géospatialité" de BOREE est un ensemble de chaînes de caracteres | Élevé |
| Tables de variables figées par horizon | `src/boree/tables/` | I+ | **REJECT** | Feature store figé pour H3, hors périmètre (`PROTOCOLE.md:180`) | Nul |
| Modèles H2 / H3 / H4 | `src/boree/modeles.py`, `chaine/modeles.py`, `registre/familles/` | I+ | **REJECT** | Variables, hyperparamètres et empreintes de code figés pour un marché spécifique | Nul |
| Juge d'hiver / test du printemps | `src/boree/chaine/juger_hiver.py`, `evaluation/juge.py` | I+ | **REJECT** | Protocole de décision FR/DE (e-LOND alpha 0,03, seuil 33,3) ; les statistiques, elles, viennent d `athanor.stats` | Nul |
| Fiche du matin | `src/boree/evaluation/fiche.py` | I+ | **REJECT** | Chiffrage propre au marché FR (50 EUR/MWh x probabilité, seuil nuit + 20 EUR/MWh) | Nul |
| Enveloppe de flux + schémas JSON | `src/boree/flux.py`, `docs/flux/` | I+ | **ADAPT** | Contrat machine-vérifiable + règle de l'absence explicite : modèle d'interface idéal pour la salle de TORNE | Moyen |
| Règle "un flux absent se dit, ne s'invente pas" | `PROTOCOLE.md:111-113, 139-140` | I+ | **ADAPT** | Règle d'interface, indépendante du domaine ; à porter tel quel | Faible |
| Flux vide type, instant jamais NaT | commits `c6290a9`, `725d2e0` | I+ | **ADAPT** | Discipline d'interface à porter | Faible |
| Salle de commandement (frontend Svelte, 9 écrans) | `frontend/` | I+ | **REJECT** | Contenus électricité ; le **patrimoine de tests** (fixtures `scelles`, `doublons`, Playwright) est en revanche un modèle | Nul |
| Codes de sortie d'exploitation (0/1/2/3) | `PROTOCOLE.md:162-165` | I+ | **ADAPT** | Quatre états de santé distincts, dont "un quota n'est pas une panne" : à porter | Faible |
| Distinction "série arretee" / "série qui decroche" | `PROTOCOLE.md:170-173`, `archive.py:83-87` | I+ | **ADAPT** | Un fait structurel vs un fait transitoire : à porter pour toute reconstitution d'état | Faible |
| Garde du périmètre gelé (`deploiement garder`) | `src/boree/exploitation/deploiement.py` | I+ | **ADAPT** | Un outil, pas une prière : le modèle du "refus outille" est le modèle à retenir (cf. commit `295edbf`) | Moyen |
| Revue de lancement (12 critères) | `src/boree/exploitation/lancement.py` (55 Ko) | I+ | **ADAPT** | Methode de revue pre-production ; le module lui-même est trop gros pour être repris | Moyen |
| Store synthétique anti-fuite | `tests/fabrique.py` | I+ | **ADAPT** | "chaque valeur encode sa date", réalisé interdit = -1 : la technique anti-fuite la plus directe observee | Moyen |
| Discipline du pre-enregistrement | `PREREG.md` + amendements dates | I+ (écrit) | **ADAPT** | La règle est forte et appliquee ; elle est **écrite**, pas outillee -> à outiller chez TORNE | Moyen |
| Un résultat publié ne se réécrit jamais | `docs/resultats/README.md:50-51` | I+ (écrit) | **ADAPT** | La discipline la plus transposable du dépôt, avec une preuve dans le dossier même | Faible |
| Paquet de référence greenfield V2.0 | `BOREE_W2M_Greenfield_Reference_V2.0/` | **D** | **REJECT** | Zero fichier de code : c'est une **spécification**, pas une implémentation ; ne peut pas être un composant | Nul |
| CLI `boree` et table `ETUDES` | `src/boree/cli.py` | I+ | **REJECT** | Structure de commande propre à BOREE (contrainte maison : pas de nouvelle commande de premier niveau) | Faible |
| Gestion des secrets | `archive.py:312-314`, `garage.py:32-38` | I+ | **REJECT** | Le principe est bon et applique, mais `athanor.kernel.secrets` le fait déjà (et `data.http` masque `api_key=` dans les URL) | Nul |
| Controle exécutable anti-secret dans les journaux | -- | **absent** | **REIMPLEMENT** | La règle invariant 6 est écrite et appliquee par convention, sans contrôle automatique | Faible |

## 6. Le statut juridique des dépôts historiques — résolu

**Athanor et l'ancien `boree` sont des dépôts privés du propriétaire du projet : leur code est réutilisable sans réserve.** La question de licence qui avait été ouverte sur Athanor le 31 octobre 2026 est **close** : il n'y a pas de blocker juridique, et les décisions
`REUSE` portant sur `athanor` (et sur l'ancien `boree`) s'appliquent telles quelles. **Celles portant sur C.R.I.N. ne le sont pas** : tant que le statut de `SquirrelBetting` n'est pas établi par le propriétaire, elles restent bloquées, comme le dit `CRIN.md` §6.1.

Il reste deux points, de nature différente :

- **La politique de propriété intellectuelle de TORNE** n'est pas choisie. Le dépôt est privé ; aucune licence n'est
  ajoutée automatiquement. À traiter séparément, quand TORNE aura une existence propre à protéger.
- **La frontière entre « code à moi » et « composant réutilisable » doit rester explicite.** `athanor` et l'ancien
  `boree` sont des dépôts privés du même propriétaire : les réemployer est un acte de réécriture interne, à tracer
  dans le journal de décisions de TORNE, pas une question de licence externe. C'est précisément pourquoi le §7
  (doublons) et le §8 (ordre d'extraction) comptent : chaque brique reprise doit laisser une trace de son origine.

Les décisions `REUSE` portant sur `athanor` et sur l'ancien `boree` sont donc **actionnables immédiatement**. L'ordre d'extraction du §8 ne change pas ;
seule la réserve juridique disparaît.

## 7. Les doublons à ne pas réimplémenter

C'est le résultat le plus utile de l'archéologie : **trois dépôts ont construit la même chose**, et TORNE n'en a
besoin qu'une fois.

| Besoin | Doublons repérés | Décision |
|---|---|---|
| Magasin brut point-in-time | `athanor.data.rawstore.RawStore` / `boree.archive.py` | **Un seul.** Athanor est plus robuste (`:9`, `known_at` posé par le magasin) ; le `boree` est un doublon. |
| Registre de modèles avec contrats | `athanor.research.registry` / `boree.registre` | **Un seul.** Athanor rejoue une machine à états depuis le journal ; le registre de `boree` est expérimental. |
| Contrat de connecteur de source | `athanor.data.source` (+ `data/compliance.py`) / `boree.ingest.sources` | **Un seul.** Athanor couvre aussi robots.txt et conditions d'usage. |
| Gestion des secrets | `athanor.kernel.secrets` / `boree.archive.py:312-314` | **Un seul.** Athanor masque déjà `api_key=` dans les URL. |
| Client S3 | `athanor.data.s3` / `boree.exploitation.garage` | **Un seul.** Les trois *règles* de `boree` sont reprises, pas son client. |
| Fermeture du code de mesure | `athanor.research.provenance` / garde de `boree` | **Un seul.** Athanor fait la fermeture transitive des imports et la preuve d'équivalence. |
| Statistiques de judge | `athanor.stats` | **Un seul.** `boree` l'utilise déjà (`athanor` y est une dépendance éditable). C.R.I.N. réimplémente les mêmes primitives (`crin/evalues.py`, `crin/multiple_testing.py`, `crin/quant_fund_validation.py`) sans les connaître — **constat de comparaison, non attesté par le rapport CRIN**. |

## 8. Ce qu'il faut extraire en premier

*(Mise à jour du 31 octobre 2026, après la mission 001 : le point 1 est **partiellement fait**.
Quatre primitives d'`athanor.stats` ont été extraites et attribuées, et sont désormais des modules
TORNE — `src/torne/methods/regression.py` (OLS + CR1), `src/torne/methods/calibration.py`
(Diebold-Mariano apparié + HAC), `src/torne/methods/breaks.py` (CUSUM) et
`src/torne/methods/power.py` (puissance). Le nom de paquet `athanor` a disparu du dépôt ; la
provenance est conservée en tête de chaque module. Les huit autres primitives de la liste restent
non extraites : la mission 001 n'en avait pas besoin. Le point 2 — contrat d'ingestion et magasin
brut point-in-time — reste entièrement à faire et attend le gate P1.)*

Par ordre de valeur par unité de coût :

1. **Le noyau statistique** (`athanor.stats` : e-processus, e-LOND, multiplicité, sur-apprentissage, puissance,
   calibration, intervalles) — c'est le juge dont TORNE a besoin, déjà testé contre les définitions publiées.
2. **Le contrat d'ingestion et le magasin brut point-in-time** (`athanor.data.source`, `athanor.data.rawstore`) —
   le point de vue à la décision, une seule fois, correctement.
3. **La discipline d'ingestion** de l'ancien BORÉE : catalogue déclaratif, forme dérivée Parquet/DuckDB,
   lignage 4 colonnes, normalisation horaire.
4. **Le store synthétique anti-fuite** (`boree` : `tests/fabrique.py` ; équivalent exact côté C.R.I.N. : `tests/test_crin_datasets.py:263`, « une observation future ne change rien ») — la technique anti-fuite la plus directe
   observée, à porter dès le premier jour où une table entre.
5. **La gouvernance de la correction de multiplicité** (`C.R.I.N.` : `crin/quant_fund_validation.py:64-70`) — « le cœur le plus transposable du dépôt » : l'interdiction de l'« α-shopping » et le Bonferroni par défaut se portent tels quels dans `PREREG.md`.
6. **Le cadre de pré-enregistrement — règle écrite, à outiller** : les amendements datés de `boree` (le format le plus strict des deux, à reprendre tel quel) et le registre de preregs de
   C.R.I.N. (documentés, jamais outillés : le lien prereg → exécution → verdict est humain), dont le format est à durcir (date + commit).
7. **Le « refus outillé »** (`boree deploiement garder`, `athanor.tools.guardrails`) : la règle qui interdit de
   modifier une sous-partie du périmètre.

## 9. Ce qu'il faut laisser

- **notamment** tout le volet hippique et PMU, les pool odds et closing-Shin, Kelly, le settlement, les règles de marché
  C.R.I.N., les 43 domain adapters ; les estimateurs TabPFN/TabICL, `crin/polymarket/`, `crin/execution/provider.py`, les 108 scripts d'exploration et le projet Stranger ; la math de pool, le dé-vig Shin, l'écran Hausch-Ziemba, la normalisation des cotes et les endpoints ; le paquet de référence greenfield V2.0.
- Les 30 modules de mesures métier d'Athanor, les 22 sources, `markets/`, `forge/`, `ops/`.
- Tout le modèle métier de l'ancien BORÉE : H2/H3/H4, le juge d'hiver, la fiche du matin, l'empilement, le
  contexte physique, les tables de variables figées, la CLI.
- Les six mois de contexte électrique (le `temps.py` de `boree`), ses connecteurs, et le protocole prospectif scellé
  de Borée H3 — hors périmètre, non modifié.

## 10. Règle de coexistence

Les dépôts historiques restent en **lecture seule**. Aucun composant n'est intégré avant que sa
décision et ses dépendances ne soient établies. Ce qui est repris est réécrit ou réadapté dans
TORNE, jamais référencé comme une dépendance externe.

Le protocole scellé Borée H3, son module temporel et ses règles sont hors périmètre : ils ne sont
ni modifiés, ni extraits, ni réimplémentés.
