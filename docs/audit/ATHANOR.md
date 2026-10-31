# Audit d'Archéologie — Athanor

**Date :** 31 octobre 2026
**Auditeur :** Agent B — Athanor Archaeology
**Dépôt audité :** `C:\Users\Romain\Documents\GitHub\athanor\` (lecture seule stricte — aucune modification effectuée)
**Référentiel de mission :** `torne/MISSION.md` (§ 1, 5.1, 6, 9, 11)
**État git observé :** branche `master`, HEAD `6dacc87` (« feat(rawstore): support réplication S3 pour le lakehouse Garage », 2026-10-28), 227 commits, 451 fichiers suivis, arbre de travail propre.

---

## Périmètre effectivement lu

Fichiers **lus intégralement** :

| Domaine | Fichiers |
|---|---|
| Racine | `README.md`, `AGENTS.md`, `charter.toml`, `pyproject.toml`, `.gitignore` |
| Noyau | `src/athanor/kernel/journal.py`, `hashing.py`, `clock.py` |
| Statistique | `stats/resampling.py`, `evalues.py`, `online_fdr.py`, `multiplicity.py`, `overfitting.py`, `calibration.py`, `intervals.py`, `power.py`, `variance_reduction.py`, `regression.py`, `scoring.py`, `spreads.py` (en-têtes + signatures pour les 14) |
| Recherche | `research/charter.py`, `protocol.py`, `verdict.py`, `registry.py`, `explore.py` |
| Livre | `book/risk.py` |
| Mesures | `measures/correlation/model.py` (intégral) |
| Données | `data/rawstore.py` (en-tête + schéma) |
| Outils | `tools/guardrails.py` |
| Tests | `tests/test_stats.py`, `tests/test_evalues.py`, `tests/test_overfitting.py`, `tests/conftest.py` (partiel), inventaire des 94 fichiers |
| Docs | `docs/DOCTRINE.md`, `docs/PORTING.md` (§ « Déjà dans le noyau », « Hypothèses face à la charte », « Sort des anciens dépôts »), `docs/ARCHITECTURE.md`, en-têtes `docs/METHODES.md` |

Fichiers **inspectés par inventaire automatisé** (noms, tailles, métriques, mais non lus ligne à ligne) : les 132 fichiers `.py` de `src/athanor/`, les 94 de `tests/`, `ledger/journal.jsonl`, `uv.lock`, les 23 ADR, les 80 fixtures de `tests/fixtures/`, les 7 études de `studies/`.

**Commandes exécutées :** inventaire récursif (PowerShell), `git log/branch/status/ls-files` (git de GitHub Desktop, `app-3.6.10`), décompte des tests par fichier, statistiques des événements du journal, lecture des en-têtes de `docs/METHODES.md` et `docs/PORTING.md`, recherche de marqueurs d'obsolescence (`REJEU SEULEMENT`, `ABANDONN`, …), croisement des imports de `stats/`.

---

## 1. Cartographie des modules

### 1.1 Architecture en couches

Athanor est organisé en couches strictes, du plus générique au plus métier :

```
kernel/   (546 l.)   horloge, journal chaîné, empreintes, secrets, chemins, verrous
stats/   (2237 l.)   statistique pure — n'importe RIEN du reste du dépôt
research/(2982 l.)   protocole, juge, registre, exploration, provenance
measures/(4308 l.)   règles de mesure métier (marchés, crypto, hippique, météo…)
data/    (6812 l.)   collecte, magasin brut point-in-time, entrepôt DuckDB, 22 sources
markets/  (518 l.)   cotes, pari mutuel
book/     (613 l.)   carnet d'ordres, gestion du risque (Kelly, drawdown, alarmes)
forge/    (892 l.)   gabarits d'hypothèses pré-enregistrés
ops/     (1796 l.)   battement, collectes, vues, tick
```

**Preuve majeure de la cartographie :** `grep '^from athanor\.'` sur `src/athanor/stats/` ne retourne que des imports internes à `stats/` (10 occurrences, toutes `from athanor.stats.resampling import ...`). Le paquet `stats/` est **autonome** — c'est la propriété la plus importante de cet audit.

### 1.2 Inventaire par composant

| Chemin | Rôle réel | État | Preuve |
|---|---|---|---|
| `stats/resampling.py` | Métrique ratio, bootstrap studentisé par grappes, robustesse « sans le top-k », découpage temporel | **Implémenté et vérifié** | 190 l. ; `tests/test_stats.py:22` (détecte l'effet / ne détecte pas le bruit), `:31` (déterminisme à graine), `:38` (jackpot ne survit pas au drop-top-k) ; `tests/test_dependence.py:139` |
| `stats/evalues.py` | e-processus aGRAPA, suites de confiance « grid Kelly », e-détecteur de décroissance, p anytime | **Implémenté et vérifié** | 412 l. ; 37 tests dans `tests/test_evalues.py` (dont validité à tout instant sous H0, couverture uniforme en t, contrat de bornage strict) ; `tests/test_decay.py` |
| `stats/online_fdr.py` | Budget d'alpha en ligne (alpha-investing) + e-LOND | **Implémenté et vérifié** | 97 l. ; `tests/test_stats.py:45` (richesse et mises), `:59` (richesse jamais négative) ; `tests/test_elond.py` (4 tests) ; `tests/test_endpoints.py:73,84` |
| `stats/multiplicity.py` | Bonferroni, Holm, Benjamini-Hochberg, Romano-Wolf stepdown (FWER par bootstrap) | **Implémenté et vérifié** | 108 l. ; `tests/test_multiplicity.py` (15 tests) |
| `stats/overfitting.py` | SPA (Hansen), PBO (CSCV), Sharpe dégonflé, bootstrap stationnaire | **Implémenté et vérifié** | 287 l. ; `tests/test_overfitting.py` (27 tests, dont valeurs de référence des définitions publiées) |
| `stats/power.py` | MDE, taille d'échantillon, effet de plan de Kish, puissance simulée d'e-processus | **Implémenté et vérifié** | 176 l. ; `tests/test_power.py` (14 tests) ; `tests/test_loss_floor.py` |
| `stats/calibration.py` | Brier, log-loss, diagramme de fiabilité, ECE, Brier-ratio vs référence, Diebold-Mariano (HAC Newey-West) | **Implémenté et vérifié** | 198 l. ; `tests/test_calibration.py` (18 tests) |
| `stats/intervals.py` | Wilson, Clopper-Pearson, Jeffreys, Newcombe, beta-binomial, différences stratifiées | **Implémenté et vérifié** | 293 l. ; `tests/test_intervals.py` (28 tests) |
| `stats/variance_reduction.py` | Régression sur variables de contrôle, CUPED, borne inférieure ajustée | **Implémenté et vérifié** | 151 l. ; `tests/test_variance_reduction.py` (10 tests) |
| `stats/scoring.py` | Brier multi-classes et log-score différentiels **par unité**, normalisés par portée prévisible | **Implémenté et vérifié** | 131 l. ; `tests/test_scoring.py` (10 tests) ; `tests/test_racing_information.py:22` |
| `stats/regression.py` | OLS (+ erreur-type CR1 par grappes), bêta de couverture borné | **Implémenté et vérifié** | 52 l. ; `tests/test_t90_stats.py:17` |
| `stats/spreads.py` | Écart acheteur-vendeur OHLC (estimateur EDGK 2024) | **Implémenté et vérifié** | 66 l. ; `tests/test_spreads.py`, `tests/test_costs.py:43` ; valeur publiée `0,0101849034905478` testée sur `tests/fixtures/edge/ohlc.csv` (675 Ko) |
| `stats/breaks.py` | Test de rupture CUSUM, variance long-run, lags de Bartlett | **Implémenté et vérifié** | 75 l. ; `tests/test_breaks.py` (7 tests) |
| `kernel/journal.py` | Journal append-only chaîné par empreintes SHA-256, verrous inter-processus | **Implémenté et vérifié** | 185 l. ; `tests/test_kernel.py` ; `tests/test_import_legacy.py` (17 tests) |
| `kernel/hashing.py` | SHA-256, JSON canonique, normalisation CRLF→LF | **Implémenté et vérifié** | 37 l. ; `tests/test_warehouse_digest.py` |
| `kernel/clock.py` | Horloge UTC unique | **Implémenté et vérifié** | `tests/test_kernel.py` ; usage vérifié : `AGENTS.md:16` l'interdit hors `kernel/clock.py` |
| `research/protocol.py` | Protocole figé : fenêtres à trous, sections `[power]`, `[robustness]`, dépendances, auxiliaires | **Implémenté et vérifié** | 515 l. ; `tests/test_protocol.py` (11) ; `tests/test_window_holes.py` ; `tests/test_verdict_deadline.py` |
| `research/verdict.py` | **Le juge** : bootstrap par grappes + e-processus, structures concurrentes, auxiliaires | **Implémenté et vérifié** | 376 l. ; `tests/test_verdict*`, `tests/test_endpoints.py` ; `AGENTS.md:11` en fait le lieu unique de calcul des verdicts |
| `research/registry.py` | Machine à états des hypothèses, application d'événements, budget par critère | **Implémenté et vérifié** | 424 l. ; `tests/test_import_legacy.py`, `tests/test_seen_windows.py` |
| `research/explore.py` | Exploration journalisée : familles de variantes, malédiction du gagnant, SPA, PBO, DSR, rupture | **Implémenté et vérifié** | 411 l. ; `tests/test_explore.py` (18) ; `tests/test_explore_forward.py` |
| `research/provenance.py` | Empreinte du code de mesure, équivalence de règle figée | **Implémenté et vérifié** | `tests/test_provenance.py` (9) ; `tests/test_frozen_studies.py` |
| `research/charter.py` | Lecture de `charter.toml` → objet `Charter` | **Implémenté et vérifié** | 73 l. ; `tests/test_charter_sign.py` |
| `book/risk.py` | Kelly fractionnel sur borne basse, bankroll/drawdown, alarme de perte e-processus, e-détecteur de décroissance | **Implémenté et vérifié** | 22 tests dans `tests/test_risk.py` |
| `measures/correlation/model.py` | Moteur générique : ridge + λ par validation interne + CV par blocs purgés + embargo | **Implémenté et vérifié** | 255 l. ; `tests/test_correlation_model.py` (4) ; référence López de Prado ch. 7 citée en commentaire `:142` |
| `measures/detector.py` | Détecteur v1 (croisements codés en dur) | **Obsolète** | `measures/detector.py:21` — « REJEU SEULEMENT — remplacé par `measures/correlation` (ADR 0022) » ; encore importé par `measures/reaction.py:27` |
| `measures/token_unlocks.py` | Déblocages crypto v1 | **Obsolète** | `:23` — « REJEU SEULEMENT — piste crypto arrêtée (T95) » |
| `measures/token_unlocks_v2.py` | Déblocages crypto v2 | **Obsolète** | `:16` — « REJEU SEULEMENT — piste crypto arrêtée (T95) » ; `:29` importe la v1 |
| `measures/insiders.py` | Achats de dirigeants FR/USA | **Obsolète** | `:38` — « REJEU SEULEMENT — études françaises REJETÉES » |
| `measures/nhtsa_events.py` | Plaintes NHTSA | **Obsolète** | `:16` — « REJEU SEULEMENT — famille `nhtsa_spikes` consignée (rien trouvé) » |
| `measures/racing_executable.py` | Règle PMU/ATG exécutable | **Obsolète** | `:20` — « REJEU SEULEMENT — piste suédoise arrêtée (T95) » |
| `measures/racing_information.py` | Règle d'information PMU/ATG | **Obsolète** | `:28` — « REJEU SEULEMENT — piste suédoise arrêtée (T95) » |
| `data/sources/*.py` (22 fichiers) | Collecteurs : SEC, AMF, PMU, ATG, Yahoo, Binance, Coinbase, Kalshi, Polymarket, NHTSA, Wikipedia, météo, Sharadar… | **Implémenté et vérifié** (pour la plupart) | 74 fichiers de test dédiés (`test_yahoo.py` 29, `test_markets_parimutuel.py` 34, `test_amf_bdif.py` 18, `test_sources_pmu_atg.py` 23…) ; chaque source testée sur un brut figé dans `tests/fixtures/` |
| `data/rawstore.py` | Magasin brut point-in-time, index SQLite en WAL, lots, réplication S3 | **Implémenté et vérifié** | 455 l. ; `tests/test_rawstore.py` (9), `tests/test_rawstore_s3.py` (6) ; HEAD `6dacc87` |
| `ops/*` (17 fichiers) | Battement, tick, collectes, vues, risk_watch | **Implémenté** | `tests/test_anchor.py`, `test_micro_live.py`, `test_decision_view.py` |
| `forge/*` (6 fichiers) | Gabarits d'hypothèses pré-enregistrés | **Implémenté** | `tests/test_forge_templates.py` (26) |
| `tools/guardrails.py` | Garde-fous de dépôt : règles d'architecture vérifiées statiquement | **Implémenté et vérifié** | Lancé par `AGENTS.md:41` ; vérifie les invariants de structure |
| `studies/*` (7 études) | Fiches + protocoles + mesures | **Documenté et cadré, non conclu** | Aucun fichier `VERDICT*` dans `studies/` ; `ledger/journal.jsonl` ne contient **qu'un seul** `VERDICT_RENDERED` |

### 1.3 Ce que `charter.toml` et `ledger/` contraignent réellement

**`charter.toml`** est lu par `research/charter.py` (`Charter.load`, 73 l.) et appliqué par le moteur. Ce n'est pas décoratif :

- `[objective]` (rendement net 15 %/an, cible 25 %, plancher 1 €/jour) → porte d'entrée économique qui **refuse une fiche sans test** (`research/charter.py:56-59`) ;
- `[capital]` (amorce 5 000 €, prouvé 50 000 €) → `capital_available_eur` calculé depuis la phase ;
- `[risk]` (`kelly_fraction=0.25`, `max_drawdown=0.20`, `loss_alarm_alpha=0.05`) → consommé par `book/risk.py` (Kelly fractionnel **sur la borne basse**, jamais sur le point) ;
- `[constraints]` (`max_verdict_days=31`, `physical_presence=false`, `max_lockup_days=365`) → `research/charter.py:12-13` fixe `MAX_VERDICT_DAYS=31` ; `research/scout.py:190` et `forge/explore_forward.py:132` **abandonnent** toute piste dont le premier verdict tarde plus de 31 jours ;
- `[statistics]` (`fdr_target=0.10`, `bid_min_fraction=0.02`, `bid_max_fraction=0.50`, `default_drop_top_k=5`, `default_min_positive_splits=2`) → `charter.py:65-68` les convertit en `BudgetPolicy` et en règles de robustesse ; le FDR à vie est garanti par e-LOND.

**Contrainte supplémentaire :** toute modification de `charter.toml` doit être signée au journal (`athanor charter-sign`), sinon un gel est refusé (`charter.toml:3`, `AGENTS.md:15`).

**`ledger/journal.jsonl`** est la mémoire unique, **append-only et chaînée** (`kernel/journal.py` : chaque événement porte `prev` et `digest` SHA-256 ; `verify()` détecte toute modification a posteriori). L'état du registre des hypothèses n'est stocké nulle part ailleurs — il se recalcule en rejouant le journal (`kernel/journal.py:3-5`). `AGENTS.md:12` interdit d'écrire dans le journal autrement que par `research/registry.py`.

État observé du journal : **117 lignes** — 50 `LEGACY_VERDICT` (import d'anciens dépôts, `research/legacy.py`), 33 `EXPLORED`, 10 `CARD_FILED`, 8 `CARD_ACCEPTED`, 5 `PARKED`, 3 `PROTOCOL_FROZEN`, 2 `CARD_REJECTED`, 2 `DISCOVERY_RUN`, 1 chacun de `CHARTER_SIGNED`, `UNPARKED`, `CODE_PINNED`, **`VERDICT_RENDERED`**.

> **Fait observé, à ne pas surinterpréter :** 50 des 117 entrées sont un import de verdicts hérités d'autres dépôts (mémoire, pas preuve — `research/registry.py:48` classe ces verdicts en `ARCHIVED`). Il reste **un seul** verdict rendu par le moteur, plus 3 protocoles figés. Le dépôt est donc **architecturellement mûr et empiriquement peu exercé**. La doctrine revendique « une soixantaine de verdicts » (`docs/DOCTRINE.md:3`) : ce chiffre vient des anciens dépôts, pas du registre propre.

---

## 2. Les briques réutilisables

### 2.1 Ce qui est transposable tel quel (couche `stats/`)

`stats/` est autonome : il n'importe rien du reste d'Athanor et ne connaît ni le pari, ni le tick, ni la finance. C'est le cœur le plus directement réutilisable de tout le dépôt.

| Brique | Fait | Signature | Dépendance | Coût de reprise | Transposable à TORNE | Lié au domaine |
|---|---|---|---|---|---|---|
| **e-processus / suites de confiance** | Test anytime-valid : e-valeur, e-processus aGRAPA, suite de confiance « grid Kelly », p-val anytime | `e_process(xs, *, null=0.0, lower=-1.0, upper=None, alternative=..., truncation=0.5)` ; `confidence_sequence(xs, *, lower, upper, alpha, alternative)` | numpy seul | **Très faible** (~400 l., 1 fichier) | **Oui, intégralement** | Aucune. Hypothèse : H0 sur l'espérance **conditionnelle** ; les unités corrélées doivent être agrégées par grappe avant (`cluster_returns`). |
| **Budget d'alpha / e-LOND** | Dépense d'alpha en ligne ; FDR ≤ α sous dépendance arbitraire pour e-valeurs | `bid(policy, history, prior) -> Bid` ; `elond_bid(policy, history, prior) -> Bid` ; `wealth(policy, history) -> float` | stdlib seul | **Très faible** (~100 l.) | **Oui, intégralement** | Aucune. Le `prior` est un a priori *de fiche*, à re-brancher chez TORNE. |
| **Bootstrap par grappes** | IC et p-valeur studentisés, rééchantillonnage des **grappes** (jamais des unités) | `cluster_bootstrap(values, weights, clusters, *, rng, draws=2000, null, alternative, level)` | numpy | **Très faible** | **Oui** | Aucune — mais le **contrat ratio** (`Σ valeur / Σ poids`) impose la convention d'Athanor ; à garder ou assumer. |
| **Sur-apprentissage / sélection** | SPA, PBO/CSCV, Sharpe dégonflé, bootstrap stationnaire | `spa_test(bench, models, *, rng, n_bootstrap, clusters)` ; `probability_of_backtest_overfitting(returns, *, n_blocks)` ; `deflated_sharpe_ratio(returns, n_trials, ...)` | numpy, stdlib | **Faible** (~290 l.) | **Oui** | Aucun. |
| **Multiplicité** | Bonferroni, Holm, BH, Romano-Wolf stepdown | `bonferroni/holm/benjamini_hochberg(pvalues, alpha)` ; `romano_wolf_stepdown(test_stats, null_stats, alpha)` | numpy | **Très faible** | **Oui** | Aucune. |
| **Puissance** | MDE, n requis, effet de plan de Kish, puissance simulée d'e-processus | `minimum_detectable_effect(n, sd, *, design_effect, alpha, alternative)` ; `estimate_design_effect(values, weights, clusters)` | numpy, stdlib | **Très faible** | **Oui** | Aucune. |
| **Calibration** | Brier, log-loss, fiabilité, ECE, Brier-ratio, Diebold-Mariano (HAC) | `brier_score`, `log_loss`, `expected_calibration_error`, `brier_ratio`, `diebold_mariano(losses_a, losses_b, *, alternative)` | numpy | **Faible** | **Oui** | Aucune. |
| **Intervalles de proportion** | Wilson, Clopper-Pearson, Jeffreys, Newcombe, beta-binomial | `wilson(k, n, level)`, `clopper_pearson`, `jeffreys`, `newcombe_difference` | stdlib | **Très faible** | **Oui** | Aucune. |
| **Variance réduite** | Régression sur contrôles, CUPED, borne inférieure ajustée | `fit_theta(y, z)`, `control_variate_mean(y, z, *, theta, z_mean, ...)`, `cuped_difference(...)` | numpy | **Faible** | **Oui** | Aucune. |
| **Scoring différentiel** | Brier/log-score multi-classes par unité, normalisés par portée prévisible | `normalized_brier_difference(target, reference, outcome)`, `brier_difference_range(...)` | numpy | **Faible** | **Oui** | Aucune. |
| **Ruptures** | CUSUM, variance long-run, lags de Bartlett | `cusum_break_test(xs, *, lags=0)` | numpy, stdlib | **Très faible** | **Oui** | Aucune. |
| **Régression simple** | OLS + CR1, bêta de couverture borné | `ols(x, y, *, clusters=None)`, `hedge_ratio(asset, hedge, *, low, high)` | numpy | **Très faible** | **Oui** | Faible : `hedge_ratio` est financier mais trivial à adapter. |
| **Écart acheteur-vendeur OHLC** | Estimateur EDGK 2024, sans biais, variance minimale | `edge(open_, high, low, close, *, sign=False)` | numpy | **Très faible** | **Oui** (coûts de transaction) | **Financier** par nature (cours OHLC). |

### 2.2 Ce qui est transposable mais à adapter

| Brique | Fait | Coût | Ce qui reste lié au domaine |
|---|---|---|---|
| **Moteur de corrélation** (`measures/correlation/model.py`) | Ridge + λ par validation interne (blocs purgés) + validation externe par blocs d'années + embargo 30 j ; seuil sur signaux **centrés hors pli** | **Moyen** (~255 l. à extraire ; dépend de `research.observations.Observation`) | `FOLDS` (`{2017:0, … 2026:5}`) est **codé en dur sur les années d'ATHANOR** : à refaire. `Outcome.net(side, borrow)` est une interface de **pari**. `MIN_SIGNAL = 1e-4` est en unités de rendement. Le **noyau algorithmique** (ridge, purge, embargo, seuil hors pli) est parfaitement générique et très bien conçu : c'est la brique de *validation hors échantillon* la plus aboutie du dépôt. |
| **Journal chaîné** (`kernel/journal.py`) | Append-only, chaîné par SHA-256, verrous inter-processus, cache de lecture, rejouable | **Faible** (~185 l., autonome, 2 dépendances kernel) | Aucune : c'est de l'infrastructure pure. Le format d'événement est générique. **Fort candidat.** |
| **Empreintes** (`kernel/hashing.py`) | SHA-256, JSON canonique, normalisation CRLF→LF | **Très faible** (37 l.) | Aucune. |
| **Horloge** (`kernel/clock.py`) | Point d'entrée unique au temps | **Très faible** | Aucune. |
| **Garde-fous de dépôt** (`tools/guardrails.py`) | Vérifie statiquement les invariants d'architecture | **Faible** | Aucun. À **réécrire** pour les règles de TORNE, mais le *principe* (un script vérifie l'architecture, pas les humains) est excellent. |

### 2.3 Ce qui n'est pas transposable (lié au domaine d'origine)

| Domaine | Éléments | Preuve |
|---|---|---|
| **Couche données** (6812 l., 22 sources) | `data/sources/*` : SEC EDGAR, AMF/BDIF, PMU, ATG, Yahoo, Binance, Coinbase, Kalshi, Polymarket, NHTSA, Wikipedia, Dukascopy, Weather, Sharadar, Alpaca, emissions | Noms de fichiers ; `data/datasets.py` (26 constructeurs de lignes, `build_pmu_runners`, `build_yahoo_daily`, `build_edgar_filings`…) — 100 % spécifiques aux marchés financiers/hippiques/crypto étudiés |
| **Entrepôt DuckDB** | `data/warehouse.py` | Schéma orienté prix/marchés |
| **Magasin brut** | `data/rawstore.py` (455 l.) | **En réalité générique** — point-in-time, `known_at` posé par le magasin et jamais par l'appelant (« on ne peut pas antidater », `:9`), blobs adressés par contenu, S3. **Candidat `ADAPT` fort** pour TORNE : la sémantique point-in-time est exactement ce qu'il faut pour des reconstitution d'états physiques. |
| **Mesures métier** | `measures/*` (30 fichiers, 4308 l.) | 7 modules marqués « REJEU SEULEMENT » ; les 23 autres sont des règles de mesure hyper-spécifiques (`reaction.py`, `technicals.py`, `intraday_momentum.py`, `gas_markets.py`, `weather_markets.py`…) |
| **Marchés** | `markets/odds.py`, `markets/parimutuel.py` | Cotes décimales, dividendes mutuels, impact sur le pool |
| **Livre** | `book/ledger.py` | Carnet d'ordres et tickets |
| **Gestion du risque** | `book/risk.py` | Kelly sur cote décimale, `BetEdge.decimal_odds`, `RealSettlement`, `gain_upper` dépendant des cotes réelles. **Mais** : la mécanique (Kelly sur **borne basse**, jamais sur le point ; alarme e-processus ; e-détecteur de décroissance ; drawdown) est **transposable à TORNE** pour la couche financière aval. |
| **Registre** | `research/registry.py` | Machine à états des hypothèses **marchandes** (CARDED→FROZEN→PROMISING→CONFIRMED→LIVE→PARKED), notions de *fiche*, *a priori*, *mécanisme structurel*, *mise d'alpha*. La **mécanique** est bonne ; le **vocabulaire** est celui du pari. |
| **Protocole** | `research/protocol.py` | `[power]`, `[robustness]`, `[[auxiliary]]`, fenêtres à trous : excellent squelette, mais phases `DISCOVERY/CONFIRMATION/FORWARD` et endpoints `MONEY/INFORMATION` sont calibrés sur le marché. |
| **Forge** | `forge/template.py`, `forge/templates/two_crowds.py` | Gabarits de mécanismes de pari (`two_crowds`, `pool_overlay`) |

### 2.4 Reproductibilité numérique

| Élément | Constat |
|---|---|
| **Graines** | `np.random.default_rng(...)` partout ; jamais d'aléa global. `AGENTS.md:16` interdit `random` et `np.random.*`. Le juge dérive des graines déterministes : `np.random.default_rng([protocol.seed, 100 + index])` (`research/verdict.py:273`), `[protocol.seed, 200 + index]` (`:257`), `protocol.seed` pour la grappe (`:296`). Le protocole porte `seed` et `draws` (`research/protocol.py:436`). |
| **Déterminisme vérifié par test** | `tests/test_stats.py:31` — `test_bootstrap_is_deterministic_given_seed` : deux boots à graine 7 doivent être **égaux** (`assert a == b`). `tests/test_overfitting.py:33` — idem pour le bootstrap stationnaire. |
| **Verrouillage de l'environnement** | `uv.lock` présent : **633 lignes**, `version = 1`. Versions pinnées : numpy **2.5.3**, scipy **1.18.1**, duckdb **1.5.6**, pytest **9.1.1**, pytest-xdist **3.8.0**, ruff **0.16.10**, mypy **2.4.0**, truststore **0.10.4**, tomli-w **1.2.0**. |
| **Threads** | `pytest` est lancé avec `-n auto` (`pyproject.toml:36`) et `pytest-xdist` est en dépendance de dev. **Point de vigilance** : le déterminisme sous `-n auto` repose sur l'isolation par test, pas sur un verrou global ; je n'ai pas pu vérifier l'absence d'un test instable (*inconnu à confirmer*). |
| **Typage** | `mypy` **strict** (`pyproject.toml:50-52`) sur `src/athanor`, `studies`, `tools` ; `ruff` avec `line-length = 130` et un jeu de règles exigeant les annotations (`ANN`). |

---

## 3. Le juge

C'est le point de jonction majeur avec TORNE. Athanor porte trois niveaux de jugement, à distinguer nettement.

### 3.1 Niveau 1 — Les primitives statistiques (réutilisables telles quelles)

Ce sont des fonctions **pures**, sans sémantique Athanor :

```python
# stats/evalues.py
e_process(xs, *, null=0.0, lower=-1.0, upper=None, alternative=..., truncation=0.5) -> FloatArray
confidence_sequence(xs, *, lower=None, upper=None, alpha=0.05, alternative=...) -> Sequence
p_value_from_e(e: float) -> float
first_crossing(e_values, alpha: float) -> int | None

# stats/online_fdr.py
wealth(policy: BudgetPolicy, history: Iterable[Ledgered]) -> float
bid(policy: BudgetPolicy, history: Iterable[Ledgered], prior: float) -> Bid
elond_bid(policy: ELondPolicy, history: Iterable[ELondLedgered], prior: float) -> Bid

# stats/resampling.py
cluster_bootstrap(values, weights, clusters, *, rng, draws=2000, null=0.0, alternative=..., level=0.95) -> BootstrapResult
without_top_k(values, weights, k, alternative) -> float
```

**Ce qui les rend transplantables telles quelles :** elles ne reçoivent ni hypothèse, ni marché, ni fiche — seulement des tableaux de valeurs, de poids et d'indices de grappe, plus une graine et un seuil. Un juge TORNE peut les appeler sans rien réécrire.

**Contrat à respecter lors de la reprise :**
- L'e-processus exige une **borne inférieure** (`lower`) ; sous `lower` il lève `ValueError` au lieu d'écrêter (`stats/evalues.py:25-27` — le module d'origine de SquirrelBetting le faisait silencieusement, ce qui *casse la validité* : c'est une correction, pas un détail).
- L'hypothèse porte sur l'**espérance conditionnelle** de chaque unité sachant les précédentes : les unités corrélées doivent être agrégées par grappe d'abord (`cluster_returns`).
- Le couple `(valeur, poids)` est la convention Athanor : `valeur = gain net, poids = mise`. TORNE devra fournir un mapping explicite vers ce couple (pour une reconstitution d'état physique : valeur = écart reconstruit, poids = incertitude ou volume).

### 3.2 Niveau 2 — Le moteur de verdict (sémantique Athanor forte)

`research/verdict.py` (376 l.) est le cœur du jugement. `AGENTS.md:11` en fait le **lieu unique** autorisé : « Calculer ou écrire un verdict ailleurs que dans research/verdict.py » est interdit.

Fonctions clés :

```python
assess(protocol, observations, alpha_level, *, coverage=None, auxiliary=()) -> Assessment
```

Ce qu'il fait (`research/verdict.py:281-340`) :
1. Évalue **plusieurs structures de dépendance concurrentes** (grappe déclarée, groupe, blocs temporels) et retient la plus prudente (la p la plus grande) — ADR 0011 : « la structure la plus prudente » ;
2. Pour chaque structure, calcule un bootstrap par grappes (méthode `BOOTSTRAP`) **et**, si le protocole le demande, un e-processus (méthode `EPROCESS`, ADR 0008) ;
3. **Lie** une structure déclarée mais non inférable (trop peu de grappes) à `p = 1` plutôt que de la remplacer par une structure plus optimiste (`:322-324`) ;
4. Combine les **prédictions auxiliaires** (dose-réponse, placebo, témoin apparié) — une structure doit être confirmée par ce que son mécanisme implique d'autre (`:244-278`) ;
5. Vérifie le **plancher de perte** (`_check_floor`, `:233`) — sans plancher, l'e-processus bride la mise de façon pathologique ;
6. Vérifie la **couverture** (unités éligibles vs mesurées) sous `min_coverage` — des données manquantes peuvent porter l'issue (`:285-286`) ;
7. Exige la **robustesse** : le résultat doit survivre sans ses `k` plus grosses contributions et garder le même signe sur ≥ 2 périodes disjointes (`charter.toml:36-37`).

**Sémantique propre à Athanor (non transposable telle quelle) :**
- Les `Verdict` : `KILL`, `KILL_DATA`, `MARGINAL`, `PROMISING`, `CONFIRMED` (`research/protocol.py:72-78`) — une échelle orientée *mise en production d'argent* ;
- Les `Phase` : `DISCOVERY`, `CONFIRMATION`, `FORWARD` — un cycle de validation à trois temps calé sur l";
- Les `Endpoint` : `MONEY`, `INFORMATION` — une distinction binaire sur la nature de ce qui est jugé ;
- La notion de **fiche** (`card.toml`) : `counterparty`, `constraint`, `friction`, `my_edge`, `capacity`, `capture_costs`, `kill` — un cadre d'analyse *d'avantage économique* ;
- Le partage du budget d'alpha entre endpoints `ENDPOINT_SHARES = {MONEY: 0.7, INFORMATION: 0.3}` (`research/registry.py:83`) ;
- Le `max_verdict_days = 31` : une piste qui demande plus d'attente est **abandonnée**.

**Transposition proposée pour TORNE :** le juge physique puis financier de TORNE a besoin d'une échelle de verdicts à **deux axes** (physique / financier) et non une échelle unique orientée argent. La mécanique de `assess()` est à reprendre ; l'échelle de verdicts et les endpoints sont à réécrire.

### 3.3 Niveau 3 — La gouvernance de la multiplicité

C'est le cœur de la méthode Athanor et la partie la plus difficile à refaire ailleurs :

| Mécanisme | Référence | Implémentation | Garantie |
|---|---|---|---|
| **Alpha-investing** | Foster & Stine, JRSS-B 2008 | `stats/online_fdr.py:26-92` | mFDR_η ≤ α sur **toute la vie** du projet, quel que soit le nombre de tests |
| **e-LOND** | Xu & Ramdas 2024, AISTATS | `stats/online_fdr.py:95-126` | FDR ≤ α sous dépendance **arbitraire** pour des e-valeurs |
| **LOND** (bootstrap) | Javanmard & Montanari 2018 | même seuil, chemin p-valeur | FDR garanti sous indépendance ou PRDS, **pas** sous dépendance arbitraire |
| **Multiplicité intra-famille** | Romano & Wolf 2005, Econometrica 73(4) | `stats/multiplicity.py:108` | FWER par bootstrap, plus puissant que Holm sur une famille corrélée |
| **Partage d'alpha** | ADR 0014, amendement T34 | `BudgetPolicy.share(fraction)` (`online_fdr.py:37-48`) | mFDR de l'union ≤ α, chaque famille contrôlée à α_f |

**La garantie la plus forte est implicite et importante :** `stats/multiplicity.py:11-13` pose que *le choix de la correction est figé au protocole AVANT de regarder* — « prendre Romano-Wolf "parce que Holm tue", c'est de l'alpha-shopping ». C'est une discipline, pas une fonction.

### 3.4 Le cycle d'exploration (probablement le plus transposable pour TORNE)

`research/explore.py` (411 l.) formalise une idée que TORNE devra avoir pour explorer l'espace des modèles :

- une **famille** de variantes (règles candidates) mesurée sur une fenêtre **passée** d'un périmètre de marché ;
- **tout regard est consigné** (un seul événement `EXPLORED` au journal : périmètre, fenêtre, nombre de variantes, empreinte du code, meilleurs résultats) ; un regard hors moteur se déclare (`declare_look`) ;
- **tout regard brûle** : la fenêtre explorée est réputée vue pour toute hypothèse du même marché — une règle trouvée ici ne se confirme que sur des données neuves ;
- le meilleur de K variantes est lu **RÉTRÉCI** (estimation rétrécie Bayes empirique normal-normal, `tau² = max(0, var des estimations − moyenne des se²)`) — malédiction du gagnant ;
- p ajustée sur la famille (Romano-Wolf pas à pas), plus SPA, PBO, Sharpe dégonflé, et test de rupture CUSUM avec le régime d'après-rupture.

**Transposable à TORNE :** oui, presque intégralement. Le vocabulaire (marché, cote, fenêtre) est à remplacer ; la mécanique (famille → consigne → brûle → rétréci → validation sur données neuves) est exactement ce qu'il faut pour chercher des modèles de reconstitution d'états physiques. **C'est le second candidat `REUSE` majeur après `stats/`.**

---

## 4. Les tests

### 4.1 Volume et répartition

**94 fichiers de test**, ~950 fonctions `test_` (somme des décomptes par `^def test_`). Répartition :

| Domaine | Fichiers | Tests | Fichiers clés |
|---|---|---|---|
| Statistique pure | 13 | ~200 | `test_evalues.py` (37), `test_intervals.py` (28), `test_overfitting.py` (27), `test_calibration.py` (18), `test_multiplicity.py` (15), `test_power.py` (14), `test_stats.py` (11), `test_variance_reduction.py` (10) |
| Recherche / juge | 9 | ~100 | `test_engine.py` (22), `test_explore.py` (18), `test_protocol.py` (11), `test_provenance.py` (9), `test_seen_windows.py` (9) |
| Livre / risque | 3 | ~30 | `test_risk.py` (22), `test_book.py` (4) |
| Données & sources | ~45 | ~450 | `test_yahoo.py` (29), `test_markets_parimutuel.py` (34), `test_sources_pmu_atg.py` (23), `test_sec_edgar.py` (16), `test_amf_bdif.py` (18), `test_warehouse.py` (18) |

### 4.2 Ce qui est réellement testé — et comment

**Propriétés statistiques, pas seulement des valeurs figées.** C'est le point fort du dépôt.

- `tests/test_evalues.py:1-8` (en-tête) annonce quatre niveaux : valeurs calculées à la main, **validité à tout instant** (sous H0, la richesse franchit 1/α dans au plus ~α des suites — Ville), **puissance** sous avantage net, et **couverture uniforme en t** de la suite de confiance, « y compris sur un long horizon (là où l'intervalle de Hoeffding à n fixe de l'ancien module échoue) » ;
- `tests/test_stats.py:22` vérifie le **taux de rejet** sous l'alternative et l'absence de faux positif sous H0 ; `:38` vérifie qu'un **jackpot isolé** ne survit pas au drop-top-k (le piège L6 de la doctrine) ; `:31` le déterminisme à graine fixe ; `:45-65` les propriétés de la richesse d'alpha (jamais négative, plafonds min/max) ;
- `tests/test_overfitting.py:1-2` : « adaptés aux définitions publiées, + valeurs de référence ».

**Valeurs de référence publiées.** `stats/spreads.py:6-7` déclare l'estimateur EDGK (Ardia, Guidotti & Kroencke 2024, *Journal of Financial Economics* 161, 103916) « porté fidèlement du paquet de référence des auteurs (`bidask`) et testé contre ses valeurs publiées (`tests/fixtures/edge/ohlc.csv` : `0,0101849034905478`) ». Le fixture fait 675 Ko de données réelles.

**Tests sur brut figé, jamais sur le réseau.** `AGENTS.md:29` : « Toute source : tests sur un brut figé dans `tests/fixtures/`, jamais sur le réseau ». **80 fixtures** couvrent SEC, AMF, PMU, ATG, Yahoo, Binance, Coinbase, Kalshi, Polymarket, NHTSA, Wikipedia, Dukascopy, Sharadar, météo, et `edge/ohlc.csv`.

**Ce que les tests garantissent :**
1. **Reproductibilité** : déterminisme à graine (test explicite) ;
2. **Propriétés statistiques** : validité à tout instant, calibration du taux de rejet, non-négativité de la richesse d'alpha ;
3. **Robustesse de la mesure** : le résultat ne doit pas porter sur quelques jackpots ;
4. **Intégrité de la mémoire** : le journal se rejoue et se vérifie (`test_import_legacy.py`, 17 tests) ;
5. **Architecture** : `tools/guardrails.py` vérifie statiquement les invariants de dépôt (invocations en `AGENTS.md:41`).

### 4.3 Ce qui n'est PAS testé (lacunes)

| Lacune | Preuve | Risque pour TORNE |
|---|---|---|
| **Aucun test d'intégration bout-en-bout** sur une étude complète | Aucun fichier `VERDICT*` dans `studies/` ; un seul `VERDICT_RENDERED` au journal | Le juge n'a été exercé **qu'une fois** dans tout l'historique du dépôt. Reprendre `research/verdict.py` sans le ré-exercer serait prendre un code « vérifié par construction » mais non « vérifié par usage ». |
| **Le moteur de corrélation n'a que 4 tests** | `tests/test_correlation_model.py` (4) pour 255 lignes, contre 22 tests pour `research/engine.py` (dans le même ordre de grandeur de code) | La brique de validation hors échantillon la plus importante est **sous-testée**. `FOLDS` codé en dur et `EMBARGO_DAYS=30` ne sont pas validés par test. |
| **Aucune vérification de déterminisme sous `-n auto`** | `pyproject.toml:36` lance pytest en parallèle ; aucun test ne vérifie la stabilité en exécution parallèle | *Inconnu à confirmer* : risque d'instabilité non détecté. |
| **Pas de test de la `charter.toml` contre le `charter.toml` réel** | `tests/test_charter_sign.py` (2 tests) | La signature de charte est un garde-fou important ; sa couverture est mince. |
| **Les mesures « REJEU SEULEMENT » restent testées** | `test_token_unlocks.py` (4), `test_token_unlocks_v2.py` (3), `test_detector.py` (5) | Elles tournent encore en CI alors que les pistes sont arrêtées : **coût de CI inutile**. |
| **Pas de test de non-régression de la chaîne complète** (ingestion → mesure → gel → verdict → journal) | Absence de fichier de test de bout-en-bout | Le seul vrai risque de régression. |

---

## 5. Licence, dépendances, versions

### 5.1 Licence — **point bloquant à résoudre avant toute reprise**

| Élément | Constat |
|---|---|
| Fichier `LICENSE` / `LICENCE` / `COPYING` dans le dépôt | **ABSENT** (recherche récursive : aucun résultat) |
| Champ `license` dans `pyproject.toml` | **ABSENT** (`pyproject.toml` ne contient aucune mention de `license` — ni `license =`, ni `license-files`, ni classifiers de licence) |
| Licence implicite | Aucune. En l'absence de licence, le code est **« tous droits réservés »** par défaut : l'auteur conserve tous les droits et l'accord de redistribution/licence n'est pas donné. |

> **Conséquence directe :** la copie de code d'Athanor vers TORNE n'est pas juridiquement acquise en l'état. Il faut soit (a) obtenir de l'auteur une licence explicite (MIT / Apache-2.0), soit (b) obtenir son accord écrit de reprise, soit (c) réécrire les briques à partir des **publications scientifiques** sous-jacentes (les références sont citées dans les docstrings : WSR 2023, Howard 2021, Ramdas 2023, Foster & Stine 2008, Xu & Ramdas 2024, Romano & Wolf 2005, Bailey & López de Prado 2014, Hansen 2005, Politis & Romano 1994, Brier 1950, Gneiting & Raftery 2007, Diebold & Mariano 1995, Ardia 2024, Kish 1965, López de Prado 2018, Gneiting & Raftery). **L'option (c) est souvent la plus propre** : une publication décrit l'estimateur ; la réimplémentation depuis le papier évite tout problème de licence.
>
> Les dépendances sont par ailleurs **toutes libres** (numpy BSD-3, scipy BSD-3, duckdb MIT, pytest MIT, ruff MIT, mypy MIT) — le risque de licence ne vient pas d'elles.

### 5.2 Dépendances

**Runtime** (`pyproject.toml:7-13`) : `duckdb>=1.1`, `numpy>=2.0`, `scipy>=1.13`, `tomli-w>=1.0`, `truststore>=0.10`. **Cinq dépendances, toutes BSD/MIT.** Le cœur statistique n'utilise **que numpy** (scipy n'est importé que ponctuellement : `research/explore.py:40` pour la loi de Student ; `stats/calibration.py:228` pour `scipy.special.stdtr`). `statistics.NormalDist` (stdlib) est utilisé partout ailleurs — **choix notable** : les quantiles normaux ne dépendent pas de scipy.

**Dev** (`pyproject.toml:16-22`) : `pytest>=8`, `ruff>=0.6`, `mypy>=1.11`, `scipy-stubs`, `pytest-xdist>=3.6`.

**Build** : `hatchling` (`:27-29`).

### 5.3 Verrouillage de l'environnement

`uv.lock` : **633 lignes**, format `version = 1`. Versions effectivement pinnées :

| Paquet | Version verrouillée |
|---|---|
| numpy | 2.5.3 |
| scipy | 1.18.1 |
| duckdb | 1.5.6 |
| pytest | 9.1.1 |
| pytest-xdist | 3.8.0 |
| ruff | 0.16.10 |
| mypy | 2.4.0 |
| scipy-stubs | 1.18.1.1 |
| tomli-w | 1.2.0 |
| truststore | 0.10.4 |
| numpy-typing-compat | 20260602.2.5 |
| typing-extensions | 4.16.0 |

**Verdict :** l'environnement **est** verrouillé, de façon stricte et reproductible. `pyproject.toml` exige Python `>=3.12`. `truststore` est un point d'attention mineur : il s'appuie sur le magasin de certificats du système — le comportement de TLS dépend donc de la machine, ce qui weakens la reproductibilité bit-à-bit des collectes réseau (sans effet sur la statistique).

### 5.4 Dépendances non libres ou à risque

**Aucune dépendance non libre.** Pas de Numba, pas de GPU, pas de service payant, pas de binaire embarqué. `duckdb` est un moteur analytique embarqué (fichier unique, pas de serveur) — cohérent avec l'architecture « un seul dépôt, tout local ». Risque faible et maîtrisé.

---

## 6. Doublons et impasses

### 6.1 Doublons

| Doublon | Preuve | Statut |
|---|---|---|
| **`token_unlocks` v1 / v2** | `measures/token_unlocks.py` (23 l. de docstring) et `measures/token_unlocks_v2.py` ; ce dernier importe l'autre : `token_unlocks_v2.py:29` → `from athanor.measures import token_unlocks as v1`. Les deux sont marqués « REJEU SEULEMENT — piste crypto arrêtée (T95) » | **Dette assumée** (T122) — le doublon est documenté, pas subi |
| **`detector.py` v1 vs `measures/correlation/model.py`** | `measures/detector.py:21` : « REJEU SEULEMENT — remplacé par `measures/correlation` (ADR 0022) ». Le v1 code en dur ses croisements ; le v2 est générique (catégories × mesures × interactions) | **Dette assumée**, mais `measures/reaction.py:27` importe encore le v1 → **le code mort reste couplé** |
| **Deux estimateurs de bootstrap** | `stats/resampling.py` (bootstrap par grappes) et `stats/overfitting.py:38` (bootstrap stationnaire) | **Pas un doublon** : ce sont deux schéma-différents (grappes vs blocs stationnaires), et `overfitting.py:18` le dit explicitement : « Le bootstrap par grappes uniforme vient de `resampling` ; il n'est pas dupliqué ici » |
| **Correction de multiplicité en deux endroits** | `stats/multiplicity.py` (intra-famille) et `stats/online_fdr.py` (inter-hypothèses) | **Pas un doublon** : les granularités diffèrent, et c'est explicitement documenté (`multiplicity.py:11-12` : « Entre hypothèses successives, le budget d'alpha en ligne fait foi ») |

### 6.2 Code mort et chemins expérimentaux

| Chemin | Preuve | Coût |
|---|---|---|
| 7 modules `measures/` marqués « REJEU SEULEMENT » | `detector.py:21`, `insiders.py:38`, `nhtsa_events.py:16`, `racing_executable.py:20`, `racing_information.py:28`, `token_unlocks.py:23`, `token_unlocks_v2.py:16` | ~1 500 l. de code non vivant, **encore couvert par 12 tests** (`test_detector.py` 5, `test_token_unlocks.py` 4, `test_token_unlocks_v2.py` 3) → coût de CI inutile |
| `data/quality.py:19` | « T124 : plus aucune source n'est tenue par le battement (hippique arrêté sur décision de l'opérateur, crypto en T95) » | Le module n'a plus d'objet ; son contrat de qualité n'est plus exercé par le battement |
| `ops/` — 17 fichiers dont `racing_live.py` | `ops/racing_live.py:2` : « Suédoises sont arrêtées, T95 » | Code opérationnel pour une piste morte |
| `cli.py:68` | « hebdomadaire n'y sont plus (piste abandonnée, aucun consommateur) ; leur code et le brut restent (rejeu, `athanor …` » | Le code mort est **délibérément conservé pour le rejeu** — c'est une décision, pas un oubli |
| `studies/_proposals/` (avec `rotation/`, `ia_labour/`) | `mypy` exclut explicitement `studies/_proposals/` (`pyproject.toml:53`) | Propositions non promues, hors typage |

### 6.3 Dette structurelle

1. **Le juge n'a jamais été exercé en série.** Un seul `VERDICT_RENDERED` au journal, 3 `PROTOCOL_FROZEN`, 7 études sans verdict rendu. La rigueur est **architecturale**, l'expérience terrain est **minimale**. C'est le paradoxe central d'Athanor : la discipline est extrême, le rendement empirique faible.
2. **Le coût de la discipline.** `AGENTS.md` impose mypy strict + ruff annoté + garde-fous + journal chaîné + empreintes + sources figées + tests de référence. C'est ≈ 1 500–2 000 lignes d'infrastructure pour ~2 200 lignes de statistique. **Pour TORNE, ce ratio doit être revu** : la discipline de *traçabilité* vaut d'être reprise ; l'infrastructure de *chaînage* peut être simplifiée.
3. **Vocabulaire métier profond dans les couches hautes.** `research/registry.py`, `research/protocol.py`, `book/` sont imprégnés de notions de marché, de mise, de cote et de fiche. Toute la couche `research/` est **semi-transposable seulement**.
4. **`charter.toml` est à la fois une contrainte économique et un paramètre statistique.** `fdr_target=0.10`, `bid_min_fraction`, `bid_max_fraction` sont des **constantes statistiques rangées dans un fichier d'objectifs business**. C'est un couplage à défaire : chez TORNE, le FDR cible est un invariant de la plateforme, pas une variable d'objectif économique.
5. **Le `FOLDS` codé en dur** dans `measures/correlation/model.py:31` (`{2017: 0, …, 2026: 5}`) est un artefact du calendrier d'Athanor : toute reprise exige de le refaire.
6. **Le test en avant n'a pas de période de rodage.** Sur le test en avant, le protocole est exigeant (power plan obligatoire, ADR 0009 : « pas de gel sans puissance »), mais rien n'organise une phase de rehearsal. La doctrine le dit : « une hypothèse PROMISING qui attend son test en avant passe avant toute nouvelle exploration » (`docs/DOCTRINE.md:93-94`).

---

## 7. Verdict par composant

| Composant | Chemin | État | Décision | Justification | Coût de reprise |
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

---

## 8. Ce que je n'ai pas pu faire

**Aucune exécution de code n'a été possible.** L'environnement de ce poste est incomplet :

| Manque | Constat |
|---|---|
| `uv` | absent du PATH (`Get-Command uv` → rien) |
| Python 3.12 avec dépendances | `C:\Users\Romain\AppData\Local\Programs\Python\Python312\python.exe` existe (3.12.3) mais **numpy, scipy, duckdb, pytest, tomli_w, truststore sont tous ABSENTS** (vérifié par `importlib.util.find_spec`) |
| Python par défaut | `C:\Python314\python.exe` (3.14.3) — **numpy absent** ; de plus le dépôt exige `>=3.12` et 3.14 n'est pas dans la matrice testée |
| Venv du dépôt | `C:\Users\Romain\Documents\GitHub\athanor\.venv` **inexistant** |
| Réseau / installation | non tentée (l'installation de paquets sort du périmètre lecture-seule de cet audit) |

**Conséquences, à énoncer sans détour :**

1. **La suite de tests n'a PAS été exécutée.** Les ~950 tests d'Athanor n'ont pas tourné. Mon affirmation « implémenté et vérifié » repose sur **l'existence et le contenu des fichiers de test** (lus), **pas** sur une exécution observée. C'est une distinction importante : je n'affirme pas que les tests passent aujourd'hui, seulement qu'ils existent et qu'ils testent ce qu'ils prétendent tester.
2. **Aucun résultat numérique n'a été reproduit.** Je n'ai pas rejoué le test EDGK (`0,0101849034905478`), ni vérifié le déterminisme, ni rejoué un e-processus. Ces valeurs sont **rapportées depuis le code et les fixtures**, pas recalculées.
3. **`tools/guardrails.py` n'a pas été exécuté.** Ses conclusions sur l'architecture sont **lues**, pas vérifiées à l'exécution.
4. **`uv.lock` n'a pas été validé** par `uv lock --check` ; j'ai lu les versions pinnées dans le fichier.
5. **Le fichier `LICENSE` est absent** — j'ai vérifié par recherche récursive sur `LICENSE*`, `LICENCE*`, `COPYING*` (aucun résultat) et par lecture de `pyproject.toml`. C'est un constat **négatif** solide : il est peu probable qu'une licence soit définie ailleurs, mais je n'ai pas pu écarter un fichier caché ou une licence dans une documentation que je n'ai pas lue (docs/ non listés intégralement).
6. **Git a été lu avec la binaire de GitHub Desktop** (`app-3.6.10`), pas avec un `git` système. Les commandes `log`, `branch`, `status`, `ls-files` ont fonctionné ; `git status --short` n'a renvoyé aucune modification, donc l'arbre était propre au moment de l'audit.
7. **Le contenu des 132 modules `src/` n'a pas été lu ligne à ligne** : 40 environ l'ont été intégralement ou en grande partie ; les autres ont été caractérisés par leurs en-têtes de docstring, signatures, métriques et marqueurs d'obsolescence. Les affirmations « rôle réel » sur ces modules reposent sur leurs docstrings (qui, dans ce dépôt, sont très fiables et très détaillées) croisées avec les imports et les tests.
8. **Une partie de `docs/METHODES.md` (62 Ko) et `docs/PORTING.md` (75 Ko) n'a pas été lue** : j'en ai lu les en-têtes de sections et les sections citées. Ces documents contiennent probablement des précisions sur les briques que je n'ai pas reprises.

**Aucun commit, aucun fichier et aucune modification n'ont été produits dans le dépôt audité.** Le seul fichier écrit est `torne/docs/audit/ATHANOR.md` (ce rapport), créé dans le répertoire `torne/docs/audit/` qui n'existait pas.

---

## Ce qu'il faut reprendre, ce qu'il faut réécrire, ce qu'il faut laisser

### À REPRENDRE — la colonne vertébrale statistique, quasi telle quelle

1. **`stats/` en entier (2 237 lignes, 13 modules).** C'est le cœur le plus pratiquement réutilisable de tout le dépôt, parce qu'il n'importe rien du reste d'Athanor : e-processus et suites de confiance, budget d'alpha et e-LOND, bootstrap par grappes, multiplicité, sur-apprentissage, puissance, calibration, intervalles, variance réduite, scoring différentiel, ruptures, régression, écart de transaction. Chaque fonction est petite, testée contre des valeurs publiées ou des propriétés statistiques, et documentée avec sa référence scientifique dans sa docstring.
   - **Réserve licence** : à traiter (§ 5.1) — soit licence explicite de l'auteur, soit réimplémentation depuis les papiers cités.
2. **Le noyau `kernel/` (546 lignes)**, en particulier le **journal chaîné** : append-only, empreintes SHA-256 par événement, verrou inter-processus, état recalculé par rejeu. C'est exactement ce que TORNE verra « reconstitution d'états physiques » exige — la traçabilité de ce qui a été vu, quand et par quel code.
3. **La discipline d'exploration de `research/explore.py`** (adaptée) : toute famille de variantes est consignée, la fenêtre est brûlée, le gagnant est lu rétréci. Pour TORNE, qui doit chercher des modèles de reconstitution, c'est la règle qui empêche l'illusion de progrès.
4. **La notion de budget d'alpha par critère** (`ENDPOINT_SHARES`) : TORNE a besoin d'un juge **physique** puis **financier** — le partage d'un même budget entre deux endpoints est la bonne abstraction.
5. **Les 9 leçons de `docs/DOCTRINE.md`** comme matière : elles sont étayées par des verdicts, pas par des avis. L1 (« le plafond est l'information, pas l'estimateur ») et L6 (« un résultat porté par quelques jackpots n'est pas une preuve ») sont transposables telles quelles.

### À RÉÉCRIRE — l'adaptation, pas la reprise

6. **L'échelle de verdicts et les phases** : `KILL/KILL_DATA/MARGINAL/PROMISING/CONFIRMED` et `DISCOVERY/CONFIRMATION/FORWARD` sont calibrés sur « une piste passe-t-elle en production d'argent ? ». TORNE a besoin de deux axes (physique, financier) et d'une notion de « reconstitution d'état » distincte de « avantage ».
7. **Le moteur de corrélation** : extraire l'algorithme (ridge, λ par validation interne, purge, embargo, seuil hors pli), refaire `FOLDS` (codé en dur sur 2017-2026), remplacer `Outcome.net(side, borrow)` par une interface de TORNE, et **ajouter des tests** (4 aujourd'hui pour 255 lignes).
8. **Le noyau du juge** : la mécanique de `research/verdict.py` est excellente, mais elle n'a été exercée qu'une fois dans l'histoire du dépôt. La reprendre sans l'exercer en série serait une faute — il faut un banc d'essai qui produit plusieurs verdicts.
9. **La gestion du risque** (`book/risk.py`) : conserver le principe du Kelly sur **borne basse** (jamais sur le point) et l'e-détecteur de décroissance ; réécrire `BetEdge`, `RealSettlement` et `gain_upper` pour des produits financiers non-pari.
10. **Le magasin brut** : garder la sémantique point-in-time (`known_at` posé par le magasin, jamais par l'appelant) ; refaire le stockage et le S3 pour l'infrastructure de TORNE.
11. **Les garde-fous de dépôt** : réécrire les invariants pour TORNE (journal, empreintes, absence de fuite temporelle, tests de référence).
12. **La charte** : séparer l'objectif économique des constantes statistiques. Le FDR cible et les seuils de multiplicité sont des invariants de la plateforme TORNE, pas des variables de business.

### À LAISSER — à rejeter, avec justification

13. **Toute la couche données et les 22 sources** (`data/sources/*`, 6 812 lignes) :_sec_edgar, AMF/BDIF, PMU, ATG, Yahoo, Binance, Kalshi, Polymarket, NHTSA, Sharadar… — spécifiques aux marchés qu'Athanor étudiait. TORNE a ses propres sources (réseau électrique, énergie, météo, prix de l'électricité) : rien à transposer.
14. **Les mesures métier** (30 modules, 4 308 lignes) : y compris les 7 « REJEU SEULEMENT », y compris `token_unlocks` v1 *et* v2, y compris `detector.py` v1. Aucun rapport avec la reconstitution d'états physiques.
15. **Le pari** : `markets/odds.py`, `markets/parimutuel.py`, `book/ledger.py` — cotes, mutuel, tickets.
16. **La forge** (`forge/*`) : ses gabarits sont des mécanismes de pari (`two_crowds`, `pool_overlay`).
17. **Les opérations** (`ops/*`) : cycle de vie d'un système de trading.
18. **Les études et le legacy** : aucune n'a produit de verdict ; les pistes hippiques et crypto sont arrêtées par l'opérateur.
19. **Le code de `measures/` obsolète ne doit pas être « nettoyé » par TORNE** : Athanor le garde volontairement pour le rejeu (T122). C'est un choix assumé et il faut le respecter.

### Un dernier avertissement, chiffres à l'appui

Athanor est **architecturalement excellent et empiriquement peu exercé** : 227 commits, 2 237 lignes de statistique pure testée avec des références publiées, 13 000+ lignes d'infrastructure, et **un seul verdict rendu** au journal. La richesse de ce dépôt est dans ses **primitives statistiques et sa discipline**, pas dans son empirie.

Le risque principal pour TORNE n'est donc pas de mal copier : c'est de **sous-copier** — d'emporter la méthode en croyant qu'elle a déjà fait ses preuves. Elle n'a pas encore fait les siennes.