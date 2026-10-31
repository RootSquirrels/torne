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
| Composant | Nom et fonction réelle |
| Origine | Dépôt, chemin, commit |
| État | Implémenté, documenté, expérimental, obsolète |
| Tests | Tests existants et résultats |
| Dépendances | Bibliothèques et contraintes |
| Domaine | Général ou spécifique |
| Licence | Vérifiée ou inconnue |
| Valeur pour TORNE | Besoin concret couvert |
| Coût de reprise | Faible, moyen, élevé |
| Décision | Reprendre, adapter, réimplémenter, écarter |
| Justification | Raisonnement vérifiable |

Règles de remplissage :

- Un composant n'est retenu que si son **origine** est vérifiable : chemin exact et commit.
  Un composant dont l'origine ne peut être établie est écarté, même s'il paraît prometteur.
- L'**état** distingue ce qui est implémenté et vérifié de ce qui n'est que spécifié dans un
  document. Un document d'architecture n'est pas une implémentation.
- Les **tests** citent les tests existants et leur résultat observé, pas une intention.
- La **licence** est notée « vérifiée » seulement si le fichier de licence a été lu ; sinon
  « inconnue », et le composant est traité comme non réutilisable en l'état.
- La **décision** est unique : un composant ne peut pas être à la fois repris et écarté. Les
  ambiguïtés se tranchent par un argument supplémentaire, pas par une case « à étudier ».

Les tables ci-dessous condensent les onze champs en six colonnes ; les champs omis (tests, dépendances, domaine,
licence, valeur) sont détaillés dans les trois rapports d'origine, qui font foi.

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

| Composant | Origine | État | Décision | Justification | Coût |
|---|---|---|---|---|---|
| Bootstrap par grappes + ratio | `stats/resampling.py` | Implémenté et testé | **REUSE** | `tests/test_stats.py:22,31,38` prouvent détection, déterminisme et résistance au jackpot ; aucun import hors `stats/` | ~190 l. |
| e-processus / suites de confiance | `stats/evalues.py` | Implémenté et testé | **REUSE** | 37 tests, dont validité à tout instant (Ville) et couverture uniforme en t ; contrat de bornage strict corrigé (`:25-27`) | ~412 l. |
| Budget d'alpha / e-LOND | `stats/online_fdr.py` | Implémenté et testé | **REUSE** | mFDR ≤ α à vie (Foster & Stine 2008), FDR ≤ α sous dépendance arbitraire (Xu & Ramdas 2024) | ~97 l., stdlib |
| Multiplicité (FWER/FDR/Romano-Wolf) | `stats/multiplicity.py` | Implémenté et testé | **REUSE** | 15 tests ; Romano-Wolf stepdown correct (suffix max, `:133`) | ~108 l. |
| Sur-apprentissage (SPA/PBO/DSR) | `stats/overfitting.py` | Implémenté et testé | **REUSE** | 27 tests contre les définitions publiées ; studentisation et recentrage corrects | ~287 l. |
| Puissance / effet de plan | `stats/power.py` | Implémenté et testé | **REUSE** | 14 tests ; permet le KILL_DATA honnête (« un test sans puissance n'est pas une absence d'effet ») | ~176 l. |
| Calibration + Diebold-Mariano | `stats/calibration.py` | Implémenté et testé | **REUSE** | 18 tests ; HAC Newey-West et comparaison appariée | ~198 l. |
| Intervalles de proportion | `stats/intervals.py` | Implémenté et testé | **REUSE** | 28 tests ; 6 estimateurs (Wilson, CP, Jeffreys, Newcombe, beta) | ~293 l. |
| Variance réduite / CUPED | `stats/variance_reduction.py` | Implémenté et testé | **REUSE** | 10 tests ; utile pour la reconstitution d'états | ~151 l. |
| Scoring différentiel normalisé | `stats/scoring.py` | Implémenté et testé | **REUSE** | Normalisation par portée prévisible (`:27-32`) ; 10 tests | ~131 l. |
| Ruptures CUSUM | `stats/breaks.py` | Implémenté et testé | **REUSE** | 7 tests ; détecte un changement de régime (dérive de modèle physique) | ~75 l. |
| OLS / bêta de couverture | `stats/regression.py` | Implémenté et testé | **REUSE** | 52 l., CR1 par grappes ; base de `variance_reduction` | ~52 l. |
| Écart acheteur-vendeur OHLC | `stats/spreads.py` | Implémenté et testé | **ADAPT** | EDGK 2024 testé contre la valeur publiée — excellent ; mais suppose des séries OHLC de marché financier | ~66 l. |
| Journal chaîné / empreintes / horloge | `kernel/journal.py`, `hashing.py`, `clock.py` | Implémenté et testé | **REUSE** | Autonome, append-only chaîné, verrous inter-processus ; format d'événement générique | ~270 l. |
| Magasin brut point-in-time | `data/rawstore.py` | Implémenté et testé | **ADAPT** | Sémantique point-in-time exactement celle de TORNE (`known_at` posé par le magasin, `:9`) ; couplée au format S3 de Garage | ~455 l. |
| Cycle d'exploration journalisée | `research/explore.py` | Implémenté et testé | **ADAPT** | Famille → consigne → brûle → rétréci → validation sur données neuves : la brique la plus transposable pour chercher des modèles ; vocabulaire à refaire | ~411 l. |
| Moteur de validation hors échantillon | `measures/correlation/model.py` | Implémenté et testé | **ADAPT** | Ridge + λ interne, purge, embargo 30 j : conception intègre ; mais `FOLDS` codé en dur (`:31`) et `Outcome.net(side, borrow)` est une interface de pari | ~255 l. |
| Noyau du juge | `research/verdict.py` | Implémenté, jamais exercé en série | **ADAPT** | Multi-structures prudentes, e-processus vs bootstrap, plancher, couverture : excellent ; mais un seul `VERDICT_RENDERED` au journal | ~376 l. |
| Échelle de verdicts et phases | `research/protocol.py` | Implémenté et testé | **ADAPT** | Squelette `[power]`/`[robustness]`/`[[auxiliary]]` excellent ; mais `Verdict` et `Phase` sont orientés « mise en argent » — TORNE a besoin d'un axe physique et d'un axe financier | ~515 l. |
| Registre d'hypothèses | `research/registry.py` | Implémenté et testé | **ADAPT** | Machine à états + application d'événements + budget par endpoint ; vocabulaire « fiche / a priori / mise / LIVE » à refaire | ~424 l. |
| Gestion du risque | `book/risk.py` | Implémenté et testé | **ADAPT** | Kelly sur **borne basse**, alarme e-processus, drawdown : transférable à la couche financière ; `BetEdge.decimal_odds` et `RealSettlement` à réécrire | ~450 l. |
| Charte de l'opérateur | `research/charter.py` + `charter.toml` | Implémenté et testé | **ADAPT** | Porte d'entrée (refuser une piste non rentable) ; mais `charter.toml` mélange objectifs business et constantes statistiques | ~73 l. |
| Garde-fous de dépôt | `tools/guardrails.py` | Implémenté | **REIMPLEMENT** | Le principe (un script vérifie l'architecture) est excellent ; les règles portent sur la structure d'Athanor | ~300 l. estimés |
| Couche données / 22 sources | `data/sources/*`, `warehouse.py`, `datasets.py` | Implémenté | **REJECT** | 100 % spécifique aux marchés financiers, hippiques, crypto et météo étudiés par Athanor | — |
| Mesures métier (30 modules) | `measures/*` | Majoritairement obsolètes | **REJECT** | 7 modules marqués « REJEU SEULEMENT », les autres sont hyper-spécifiques | — |
| Marchés / pari mutuel / carnet | `markets/*`, `book/ledger.py` | Implémenté | **REJECT** | Cotes décimales, dividendes mutuels : aucun rapport avec la reconstitution d'états physiques | — |
| Forge (gabarits) | `forge/*` | Implémenté | **REJECT** | Gabarits de mécanismes de pari ; TORNE aura les siens | — |
| Opérations (17 modules) | `ops/*` | Implémenté | **REJECT** | Cycle de vie d'un système de trading | — |
| Études et legacy | `studies/*`, `research/legacy.py` | Documenté, non conclu | **REJECT** | Aucun verdict rendu ; seule la **doctrine** garde de la valeur | — |
| La doctrine (leçons L1–L9) | `docs/DOCTRINE.md` | Documenté | **ADAPT** | 9 leçons étayées par des verdicts : actif de **raisonnement**, à réécrire en français avec d'autres preuves | ~110 l. de texte |

## 4. SquirrelBetting / C.R.I.N.

Rapport complet : `docs/audit/CRIN.md`.

| Composant | Origine | État | Décision | Justification | Coût |
|---|---|---|---|---|---|
| Métriques (Brier, log-loss, reliability bins, Diebold-Mariano apparié, ECE) | `crin/calibration.py` | Implémenté et testé | **REUSE** | Le cœur de l'évaluation, sans jargon hippique ; la référence pour la couche financière | ~200 l. |
| Recalibration (isotonique PAV, Platt, renormalisation intra-groupe) | `crin/recalibration.py` | Implémenté et testé | **REUSE** | Directement applicable à un produit de connaissance calibré | ~150 l. |
| Prédiction conforme (Venn-ABERS) | `crin/conformal.py:70,233` | Implémenté, couplé au Kelly | **ADAPT** | Le cœur Venn-ABERS est général ; l'habillage staking ne l'est pas | ~120 l. |
| Framework de gates (hypothèse → seuil → kill-switch → statut) | `docs/hypotheses/active/` (16 preregs) + `killed/` (9) | Exercé en série | **REUSE** | Gouvernance, pas code : chaque prereg porte conditions de validité, kill-switch et clause de non-réutilisation après peek | ~200 l. de texte |
| « Ne jamais évaluer une décision sur une information qui n'était pas disponible à la décision » | `crin/tritemporal.py:61` (`is_visible_asof`) | Implémenté et testé | **REUSE** | Principe transposable mot pour mot : une estimation produite à T ne peut être fulfilée par une observation postérieure à T | ~60 l. |
| Boucle prereg → verdict chiffré → rapport → décision de kill | Pattern, non isolé | Pattern, code non testé | **REIMPLEMENT** | Le patron est excellent et directement applicable ; l'implémentation est imbriquée dans le pool hippique | ~150 l. estimés |
| Contrats d'ingestion (streak, null-rate) | `crin/ingest` / contrats | Implémenté | **ADAPT** | La mécanique du streak est excellente ; le vocabulaire « null-rate par colonne » est celui d'un schéma tabulaire, à reformuler pour TORNE | Moyen |
| PMU et ses features | `crin/features.py` | Implémenté | **REJECT** | Spécifique aux courses | Nul |
| Pool odds et closing-Shin | `crin/pool_math.py`, `benchmark.py`, `pool_vs_sharp.py` | Implémenté | **REJECT** | Spécifique aux marchés de mutualité | Nul |
| Kelly et le sizing | `crin/policy.py`, `conformal.py:37,53` | Implémenté | **REJECT** | Le *principe* (« la mise découle de l'incertitude ») reste une référence de méthode | Nul |
| Settlement hippique | `crin/paper_bet.py`, `crin/edge.py` | Implémenté | **REJECT** | Spécifique ; le principe de règlement au moment de vérité reste REUSE | Nul |
| Règles de marché C.R.I.N. | `crin/units.py`, `hz_screen.py`, `domains/horse|tennis|lol|market_efficiency/` | Implémenté | **REJECT** | Aucun rapport | Nul |
| Domain adapters génériques | `crin/domains/base.py` + 43 fichiers | Implémenté | **REJECT** | Abstraction créée pour six verticales de paris ; contredit la MISSION §9 | Élevé |
| `crin/elo.py` | `crin/elo.py` | Implémenté | **ADAPT** | Rating générique de grandeurs ordonnées ; utilité non démontrée tant que TORNE n'a pas de slice | Faible |

## 5. Ancien BORÉE — `boree`

Rapport complet : `docs/audit/LEGACY-BOREE.md`.

| Composant | Origine | État | Décision | Justification | Coût |
|---|---|---|---|---|---|
| Lecture point-in-time « telle que connue à t » | `src/boree/lac/connu.py` | Implémenté et testé | **ADAPT** | Mécanique générique (une requête, pas une copie) ; dépend de `temps.py`, donc à réécrire | Moyen |
| Catalogue déclaratif des jeux | `src/boree/lac/catalogue.py`, `docs/LAC.md` | Implémenté et testé | **ADAPT** | La structure `Jeu` (règle nommée, granularité, publication, schéma) est domaine-indépendante ; le contenu est 100 % FR/DE | Moyen |
| Forme dérivée Parquet/DuckDB du lac | `src/boree/lac/parquet.py` | Implémenté et testé | **ADAPT** | Brut = vérité, dérivé = reconstructible ; partitionnement `annee=/mois=`, réécriture atomique | Moyen |
| Règle « local d'abord, copie après » | `src/boree/exploitation/garage.py:3-7` | Implémenté | **ADAPT** | « une panne de Garage retarde la copie, elle ne perd rien » : contrainte d'architecture indépendante du domaine | Faible |
| Règle « intégrité par empreinte, jamais par décodage » | `garage.py:12-13,47-53` | Implémenté | **ADAPT** | Vérification par hash sans ouvrir le document : s'applique tel quel à tout stockage scellé | Faible |
| Normalisation horaire (quarts → heures, 2 h local) | `src/boree/temps.py:86-95` | Implémenté et testé | **ADAPT** | Générique et testé ; à porter comme brique isolée, sans les règles de disponibilité | Faible |
| Lignage 4 colonnes (`_source`, `_cle`, `_empreinte`, `_connu_a`) | `lac/connu.py:32`, `lac/parquet.py:42-43` | Implémenté | **ADAPT** | Trivial, générique ; prouve que version et instant de connaissance voyagent ensemble | Faible |
| Méthode de parité bit-à-bit + critère de bascule | `src/boree/registre/chaine.py:89-121` | Implémenté | **ADAPT** | « conforme / différente / non comparée », `PARITE_MIN = 14/16` : méthode de migration saine, à réutiliser telle quelle | Faible |
| Contrôle du registre (empreintes, code de sortie 1) | `src/boree/registre/verifier.py` | Implémenté | **ADAPT** | Le pattern « un contrôle exécutable qui sort en 1 » est à généraliser | Faible |
| Enveloppe de flux + schémas JSON | `src/boree/flux.py`, `docs/flux/` | Implémenté | **ADAPT** | Contrat machine-vérifiable + règle de l'absence explicite : modèle d'interface idéal pour la salle de TORNE | Moyen |
| Règle « un flux absent se dit, ne s'invente pas » | `PROTOCOLE.md:111-113,139-140` | Écrit | **ADAPT** | Règle d'interface, indépendante du domaine | Faible |
| Codes de sortie d'exploitation (0/1/2/3) | `PROTOCOLE.md:162-165` | Implémenté | **ADAPT** | Quatre états de santé distincts, dont « un quota n'est pas une panne » | Faible |
| Distinction « série arrêtée » / « série qui décroche » | `PROTOCOLE.md:170-173`, `archive.py:83-87` | Implémenté | **ADAPT** | Un fait structurel contre un fait transitoire : à porter pour toute reconstitution d'état | Faible |
| Garde du périmètre gelé (`deploiement garder`) | `src/boree/exploitation/deploiement.py` | Implémenté | **ADAPT** | Un outil, pas une prière : le modèle du « refus outillé » est le modèle à retenir | Moyen |
| Revue de lancement (12 critères) | `src/boree/exploitation/lancement.py` | Implémenté | **ADAPT** | Méthode de revue pré-production ; le module lui-même est trop gros pour être repris | Moyen |
| Store synthétique anti-fuite | `tests/fabrique.py` | Implémenté | **ADAPT** | « chaque valeur encode sa date », réalisé interdit = −1 : la technique anti-fuite la plus directe observée | Moyen |
| Discipline du pré-enregistrement | `PREREG.md` + amendements datés | Écrit, non outillé | **ADAPT** | La règle est forte et appliquée ; elle est **écrite**, pas outillée — à outiller chez TORNE | Moyen |
| « Un résultat publié ne se réécrit jamais » | `docs/resultats/README.md:50-51` | Écrit | **ADAPT** | La discipline la plus transposable du dépôt | Faible |
| Règles de disponibilité (point de vue décision) | `src/boree/temps.py` | Implémenté | **REJECT** | Hors périmètre explicite et contenu 100 % électrique ; le *pattern* est repris | Faible (pattern) |
| Magasin brut versionné, empreintes, `ref(asof=)` | `src/boree/archive.py` | Implémenté | **REJECT** | Doublon de `athanor.data.rawstore.RawStore`, qui pose le même `known_at` et un point-in-time plus robuste | Faible |
| Copie S3 / Garage, intégrité, instantané | `src/boree/exploitation/garage.py` | Implémenté | **REJECT** | Doublon avec `athanor.data.s3` ; en revanche les trois règles sont portées (lignes plus haut) | Faible |
| Scellés et accès machine | `src/boree/scelles.py`, `final.py`, `direct.py` | Implémenté | **REJECT** | Entièrement lié au protocole prospectif ; le **principe** (barrière unique, refusée par défaut, testée) est à porter | Moyen |
| Connecteurs ENTSO-E / Open-Meteo / EEX | `src/boree/ingest/*` | Implémenté | **REJECT** | Liés au marché de l'électricité ; le contrat de connecteur équivalent existe dans `athanor.data.source` | Nul |
| Modèle de collecteur (plan / collect / parse) | `src/boree/ingest/sources.py` | Implémenté | **REJECT** | Doublon de `athanor.data.source` | Faible |
| Gel de la fermeture du code de mesure | — | Dans `athanor` | **REJECT** | `athanor.research.provenance` fait déjà mieux (fermeture transitive, preuve d'équivalence) | Nul |
| Registre de modèles (contrats TOML, statuts) | `src/boree/registre/contrat.py`, `registre/*.toml` | Expérimental | **REJECT** | Doublon de `athanor.research.registry`, qui rejoue une machine à états depuis le journal | Faible |
| Chaîne générique en ombre | `src/boree/registre/chaine.py` | Expérimental | **REJECT** | Lié à H2/H3/H4 ; sa valeur est dans la méthode de parité | Faible |
| Jumeau physique | `src/boree/physique/jumeau.py` | Retiré | **REJECT** | Résultat retiré : « les chiffres étaient faux » (`RESULTAT_jumeau.md`) | Nul |
| Empilement prévu au soir de J-1 | `src/boree/physique/empilement.py` | Implémenté | **REJECT** | Modèle physique du marché FR, explicitement hors modèle | Nul |
| Contexte physique (pression, décroche, angle zénithal) | `src/boree/physique/contexte.py` | Implémenté | **REJECT** | Hors gel et hors modèle | Nul |
| Tables de variables figées par horizon | `src/boree/tables/` | Implémenté | **REJECT** | Feature store figé pour H3, hors périmètre | Nul |
| Modèles H2 / H3 / H4 | `src/boree/modeles.py`, `chaine/modeles.py` | Implémenté | **REJECT** | Variables, hyperparamètres et empreintes figés pour un marché spécifique | Nul |
| Juge d'hiver / test du printemps | `src/boree/chaine/juger_hiver.py` | Implémenté | **REJECT** | Protocole FR/DE (e-LOND α = 0,03, seuil 33,3) ; les statistiques viennent d'`athanor.stats` | Nul |
| Fiche du matin | `src/boree/evaluation/fiche.py` | Implémenté | **REJECT** | Chiffrage propre au marché FR | Nul |
| Salle de commandement (frontend, 9 écrans) | `frontend/` | Implémenté | **REJECT** | Contenu électricité ; le **patrimoine de tests** (fixtures, Playwright) est un modèle | Nul |
| CLI `boree` et table `ETUDES` | `src/boree/cli.py` | Implémenté | **REJECT** | Structure propre à BORÉE | Faible |
| Gestion des secrets | `archive.py:312-314`, `garage.py:32-38` | Implémenté | **REJECT** | `athanor.kernel.secrets` le fait déjà (et `data.http` masque `api_key=` dans les URL) | Nul |
| Registre d'unités et référentiel spatial | — | **Absent** | **REIMPLEMENT** | Aucun registre d'unités, aucun CRS, aucune géométrie dans le dépôt : BORÉE n'apporte rien là | Élevé |
| Géospatial et multidimensionnel | `physique/contexte.py`, `lac/connu.py:33` | Implémenté | **REIMPLEMENT** | Aucune géométrie ni CRS : la « géospatialité » de BORÉE est un ensemble de chaînes de caractères | Élevé |
| Contrôle exécutable anti-secret dans les journaux | — | **Absent** | **REIMPLEMENT** | La règle est écrite et appliquée par convention, sans contrôle automatique | Faible |

## 6. Le blocage juridique qui conditionne tout le reste

**Athanor ne contient aucun fichier de licence.** Le dépôt `athanor@6dacc87` n'a ni `LICENSE`, ni `COPYING`, ni
mention de licence dans le `pyproject.toml` ou le `README.md`.

Conséquence : en l'état, `REUSE` signifie « copie de code sans base légale établie ». Ce n'est pas une question
théorique — c'est la seule chose qui distingue une réutilisation d'une copie de code propriétaire non autorisé.

Trois issues, par ordre de preference :

1. **Poser une licence explicite sur Athanor** (propriétaire ou MIT/BSD si l'intention est de le partager).
   L'audit note par ailleurs qu'Athanor est « le composant le plus proche d'une bibliothèque à part entière » :
   c'est le bon candidat pour devenir la brique statistique de TORNE. Une licence est une décision d'une ligne.
2. **Réécriture en salle blanche** des quelques primitives critiques (e-processus, e-LOND, multiplicité) à partir des
   publications citées — coût estimé : ~1 000 lignes, avec le risque classique de réintroduire des bugs.
3. **Athanor reste une dépendance externe** — contredit la règle de coexistence de `MISSION.md` §0.3.

La décision 1 est la plus simple et la moins coûteuse. Tant qu'elle n'est pas prise, les lignes `REUSE` du §3
signifient « à réutiliser **après** clarification de la licence ».

Le même point s'applique, à un degré moindre, à SquirrelBetting (pas de licence lue non plus) et à l'ancien BORÉE
(dépôt privé du propriétaire, donc réutilisable par lui, mais non publiable en l'état).

## 7. Les doublons à ne pas réimplémenter

C'est le résultat le plus utile de l'archéologie : **trois dépôts ont construit la même chose**, et TORNE n'en a
besoin qu'une fois.

| Besoin | Doublons repérés | Décision |
|---|---|---|
| Magasin brut point-in-time | `athanor.data.rawstore.RawStore` / `boree.archive.py` | **Un seul.** Athanor est plus robuste (`:9`, `known_at` posé par le magasin) ; le `boree` est un doublon. |
| Registre de modèles avec contrats | `athanor.research.registry` / `boree.registre` | **Un seul.** Athanor rejoue une machine à états depuis le journal ; le registre de `boree` est expérimental. |
| Contrat de connecteur de source | `athanor.data.source` (+ `data/compliance.py`) / `boree.ingest.sources` | **Un seul.** Athoran couvre aussi robots.txt et conditions d'usage. |
| Gestion des secrets | `athanor.kernel.secrets` / `boree.archive.py:312-314` | **Un seul.** Athanor masque déjà `api_key=` dans les URL. |
| Client S3 | `athanor.data.s3` / `boree.exploitation.garage` | **Un seul.** Les trois *règles* de `boree` sont reprises, pas son client. |
| Fermeture du code de mesure | `athanor.research.provenance` / garde de `boree` | **Un seul.** Athanor fait la fermeture transitive des imports et la preuve d'équivalence. |
| Statistiques de judge | `athanor.stats` | **Un seul.** `boree` l'utilise déjà ; `C.R.I.N.` l'ignore, ce qui est son erreur. |

## 8. Ce qu'il faut extraire en premier

Par ordre de valeur par unité de coût, **une fois la licence clarifiée** :

1. **Le noyau statistique** (`athanor.stats` : e-processus, e-LOND, multiplicité, sur-apprentissage, puissance,
   calibration, intervalles) — c'est le juge dont TORNE a besoin, déjà testé contre les définitions publiées.
2. **Le contrat d'ingestion et le magasin brut point-in-time** (`athanor.data.source`, `athanor.data.rawstore`) —
   le point de vue à la décision, une seule fois, correctement.
3. **La discipline d'ingestion** de l'ancien BORÉE : catalogue déclaratif, forme dérivée Parquet/DuckDB,
   lignage 4 colonnes, normalisation horaire.
4. **Le store synthétique anti-fuite** (`boree.tests.fabrique.py`) — la technique anti-fuite la plus directe
   observée, à porter dès le premier jour où une table entre.
5. **Le cadre de pré-enregistrement outillé** : les amendements datés de `boree` (écrits) et les gates de
   C.R.I.N. (exercés) — l'un donne la discipline, l'autre le format.
6. **Le « refus outillé »** (`boree deploiement garder`, `athanor.tools.guardrails`) : la règle qui interdit de
   modifier une sous-partie du périmètre.

## 9. Ce qu'il faut laisser

- Tout le volet hippique et PMU, les pool odds et closing-Shin, Kelly, le settlement, les règles de marché
  C.R.I.N., les 43 domain adapters.
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
