# Revue de cohérence — `docs/REUSE_AUDIT.md` face aux trois rapports d'archéologie

**Date :** 31 octobre 2026
**Vérificateur :** agent Vérificateur (relecture indépendante, lecture seule sur les sources)
**Document vérifié :** `docs/REUSE_AUDIT.md` (243 lignes, version de l'arbre de travail)
**Sources faisant foi :** `docs/audit/ATHANOR.md` (489 l.), `docs/audit/CRIN.md` (606 l.), `docs/audit/LEGACY-BOREE.md` (857 l.)

**Périmètre :** conformité ligne à ligne des tableaux §3, §4 et §5 ; contrôle des §6, §7, §8 et §9.
Aucun fichier du dépôt n'a été modifié, à l'exception du présent rapport.

---

## 1. Verdict

**Verdict global : FAIL.**

La transcription est **fiable sur ce qu'elle transcrit** : sur les 84 lignes de la matrice, la décision attribuée à
chaque composant est exactement celle du rapport source, et aucune justification ne contredit son rapport. Mais la
matrice est **incomplète sur un tiers de son périmètre** (24 lignes de verdict des rapports n'ont pas de ligne
correspondante) et **surreprésentée sur deux sections normatives** (§6, §8), dont une inverse le sens d'une des deux
disciplines qu'elle met en avant.

| Mesure | Résultat |
|---|---|
| Lignes de la matrice vérifiées une à une | **84** (§3 : 30, §4 : 14, §5 : 40) |
| Lignes de verdict confrontées dans les rapports | **111** (ATHANOR §7 : 30, CRIN §8 : 39, LEGACY §9 : 42) |
| **Décisions inversées** (REUSE ↔ ADAPT ↔ REIMPLEMENT ↔ REJECT) | **0** |
| **Composants inventés** (dans la matrice, absents des rapports) | **0** |
| **Lignes de verdict source sans ligne dans la matrice** | **24** (22 CRIN + 2 LEGACY) |
| Lignes de tableau à retoucher | **14** (§3 : 4, §4 : 5, §5 : 5) + 2 titres de section ; §6, §7, §8 et §9 à corriger ; **24 lignes à ajouter** (22 au §4, 2 au §5) |
| **Écarts relevés** | **25** : 2 bloquants, 9 majeurs, 14 mineurs |

Répartition par section :

| Section | Lignes | Fidélité | Réserve principale |
|---|---|---|---|
| §3 Athanor | 30 | **bonne** — 30 décisions sur 30 conformes | 1 durcissement (§3 l. 93), compte de lignes faux (l. 73) |
| §4 C.R.I.N. | 14 | **insuffisante** — 14 décisions sur 14 conformes, mais 22 composants du rapport n'ont pas de ligne | 1 état durci, 1 chemin faux, 2 origines perdues |
| §5 ancien BORÉE | 40 | **bonne** — 40 décisions sur 40 conformes | 2 lignes du rapport absentes, 2 origines incomplètes |
| §6 statut juridique | — | **non conforme** | la clôture d'Athanor est étendue à toute la matrice, C.R.I.N. n'est pas traité |
| §7 doublons | 7 | **6 sur 7 attestés** | le 7ᵉ n'est pas attesté et ne cite qu'une occurrence |
| §8 ordre d'extraction | 6 | **partiellement étayé** | point 5 : sens inversé + « outillé » ; précondition juridique contredite |
| §9 ce qu'il faut laisser | 4 | **partiellement étayé** | liste exhaustive en apparence, 9 omissions explicites des rapports |

**Ce qui est acquis :** aucune décision n'est inversée, aucun composant n'est inventé, les chemins cités ont été
recontrôlés directement dans les dépôts audités — un seul ne correspond pas (`crin/ingest`, cf. M4) —, les comptes
de tests d'Athanor repris par la matrice sont exacts (recomptage direct), et la ligne « le premier commit ne contient
que le socle documentaire » est exacte (1 commit, `src/torne/__init__.py` et `tests/test_package.py` sont des amorces).

**Ce qui manque :** la moitié de la valeur de C.R.I.N. selon son propre rapport — y compris 4 des 6 mécanismes que
`CRIN.md` §10.4 désigne comme « réutilisables tels quels ».

---

## 2. Les écarts trouvés

Gravité : **bloquant** = fausse la décision ou la rend non actionnable ; **majeur** = contredit ou durcit la source ;
**mineur** = imprécision, chemin abrégé, omission de détail secondaire.

### 2.1 Bloquants

| # | Point vérifié | Ligne matrice | Ce que dit le rapport source | Ce que dit la matrice | Gravité |
|---|---|---|---|---|---|
| B1 | Périmètre C.R.I.N. | §4 (l. 114-127) | `CRIN.md` §8 énumère **39** composants avec décision ; §10.4 résume la valeur du dépôt en **six mécanismes réutilisables tels quels** (registre de prereg, test anti-fuite, artefact auto-porteur, gouvernance de multiplicité, outillage overfitting, point-in-time) ; §2.8 : « c'est le cœur le plus transposable du dépôt » | **14 lignes seulement.** 22 composants du rapport n'ont **aucune** ligne — dont **11 `REUSE`** et 4 des 6 mécanismes cités en §10.4 (test anti-fuite, artefact auto-porteur, gouvernance de multiplicité, outillage overfitting SPA/PBO/DSR). Aucun n'est couvert par le §8 ni par le §9 | **Bloquant** |
| B2 | §6 — statut juridique | §6 l. 178-192 | `CRIN.md` §6.1 : licence **absente** ; « aucune reprise de code, même partielle, ne peut être considérée comme sûre tant que le propriétaire n'a pas explicité la licence ». `ATHANOR.md` §5.1 et `LEGACY-BOREE.md` §6.1 : idem pour les deux autres dépôts | « Athanor … son code est réutilisable sans réserve » puis « Les décisions `REUSE` de la matrice sont donc **actionnables immédiatement** ». La clôture n'est argumentée que pour `athanor` (et l'ancien `boree`) ; **C.R.I.N. n'est pas traité** alors que 4 lignes `REUSE` le concernent (l. 114, 115, 117, 118) et que la règle propre de la matrice (§1 l. 36-37 : licence inconnue ⇒ « traité comme non réutilisable en l'état ») est contredite | **Bloquant** |

### 2.2 Majeurs

| # | Point vérifié | Ligne matrice | Ce que dit le rapport source | Ce que dit la matrice | Gravité |
|---|---|---|---|---|---|
| M1 | Moteur de validation hors échantillon | §3 l. 93 | `ATHANOR.md` l. 410 : « … et **seulement 4 tests** » ; §4.3 : « La brique de validation hors échantillon la plus importante est **sous-testée** » | « conception intègre » ; la réserve de couverture est **supprimée**. Recomptage direct : `tests/test_correlation_model.py` = 4 fonctions `def test_` — la suppression est aggravée par la source | Majeur |
| M2 | Framework de gates | §4 l. 117 | `CRIN.md` l. 507 et l. 509 : état « **documenté uniquement** » ; §2.10 : « Testé / outillé — non … le lien prereg → exécution → verdict → kill est **humain** » ; §2.14 : « Aucun lien outillé prereg → rapport » | État « **Exercé en série** » ; l'origine `docs/concepts/GATES.md` (progression G0→G7) est remplacée par les registres de preregs. Le rapport ne dit nulle part que les gates ont été « exercés en série » : il constate l'inverse (lien humain, non outillé) | Majeur |
| M3 | Boucle prereg → verdict chiffré → kill | §4 l. 119 | `CRIN.md` l. 528 : `crin/pipeline.py` (**1 765 l.**), coût de reprise « **Élevé** » ; l. 529 : `crin/gate_phase2.py` (315 l.), `REIMPLEMENT`, coût « Moyen » | Origine « Pattern, non isolé » : **les deux chemins concrets sont perdus**, l'un des deux (`gate_phase2.py`) disparaît entièrement ; Coût « **~150 l. estimés** » — contredit le « Élevé » de la source et sous-estime une réimplémentation de 1 765 lignes | Majeur |
| M4 | Contrats d'ingestion (streak, null-rate) | §4 l. 120 | `CRIN.md` l. 524 : origine `crin/contracts.py` (+ `contracts_pmu.py`, `contracts_letrot.py`, `contracts_fred.py`) ; l. 220 détaille les cinq dimensions | Origine « `crin/ingest` / contrats » — **ce chemin n'existe pas**. Contrôle direct : `crin/ingest` est absent, `crin/contracts.py` est présent. Le composant reste correctement rattaché au dépôt C.R.I.N., mais à un faux chemin | Majeur |
| M5 | Deux lignes du rapport LEGACY absentes | §5 | `LEGACY-BOREE.md` l. 766 : « Flux vide type, instant jamais NaT » (I+, **ADAPT**, commits `c6290a9`, `725d2e0`, coût Faible) ; l. 775 : « Paquet de référence greenfield V2.0 » (`BOREE_W2M_Greenfield_Reference_V2.0/`, D, **REJECT**, « zéro fichier de code ») | **Aucune ligne** pour l'une ni pour l'autre ; ni le §8 ni le §9 ne les couvrent. Contrôle direct : le répertoire `BOREE_W2M_Greenfield_Reference_V2.0/` existe bien dans le dépôt audité. La règle « flux vide garde ses types » est explicitement listée comme transposable par le rapport (§2.12, §4.5) | Majeur |
| M6 | Doublon « Statistiques de judge » | §7 l. 207 | `LEGACY-BOREE.md` l. 762 atteste que `boree` utilise `athanor.stats` ; l. 636 : `athanor` est une dépendance éditable de `boree` (« statistiques » incluses). **Aucun** rapport ne rattache C.R.I.N. à `athanor` : `CRIN.md` documente des réimplémentations propres (`crin/evalues.py`, `crin/multiple_testing.py`, `crin/quant_fund_validation.py`) sans mentionner Athanor | « **C.R.I.N. l'ignore, ce qui est son erreur** » — **affirmation non attestée**, présentée comme un fait ; et le tableau n'énumère **qu'une seule occurrence** là où les six autres doublons en citent deux. C'est aussi le seul doublon qui fonde la thèse « trois dépôts ont construit la même chose » (l. 196) | Majeur |
| M7 | §8 point 5 — sens inversé | §8 l. 221-222 | `CRIN.md` l. 213 et §10.1 : le format BORÉE (« amendement daté, commité avant le premier calcul ») est **plus strict** que celui de C.R.I.N. ; C.R.I.N. est « à durcir » **dans le sens BORÉE**. `LEGACY-BOREE.md` l. 773 : la règle BORÉE est « **écrite**, pas outillée » | « l'un donne la discipline, **l'autre le format** » — **sens inversé** : C.R.I.N. ne fournit pas le format, il fournit une pratique à durcir. En-tête « Le cadre de pré-enregistrement **outillé** » alors que les deux sources disent l'inverse ; « les gates de C.R.I.N. (**exercés**) » alors que le rapport dit « documenté uniquement » | Majeur |
| M8 | §8 — précondition juridique | §8 l. 211 | Le §6 l. 191-192 tranche : « L'ordre d'extraction du §8 ne change pas ; **seule la réserve juridique disparaît** » | « Par ordre de valeur par unité de coût, **une fois la licence clarifiée** » — **contradiction interne** entre deux sections du même document sur la précondition de la liste d'action | Majeur |
| M9 | §9 — liste exhaustive en apparence | §9 l. 228-234 | `CRIN.md` §10.3 : sont aussi à laisser TabPFN/TabICL, `crin/polymarket/`, `crin/execution/provider.py`, `scripts/crin/` (projet Stranger), les 108 scripts d'exploration. `LEGACY-BOREE.md` §10.3 : aussi le paquet de référence V2.0, la salle de commandement (frontend), le jumeau retiré, le marché EEX / quotas / TTF | §9 ne cite **aucun** de ces éléments ; la section se lit comme une liste complète alors qu'elle omet **9 rejets explicites** des rapports | Majeur |

### 2.3 Mineurs et formulations

| # | Point vérifié | Ligne matrice | Ce que dit le rapport source | Ce que dit la matrice | Gravité |
|---|---|---|---|---|---|
| m1 | Volume du rapport ATHANOR | §3 l. 73 | — | « Rapport complet : `docs/audit/ATHANOR.md` (**374 lignes**) » — le fichier fait **489 lignes** (374 non vides). Erreur factuelle sur le document de référence lui-même | Mineur |
| m2 | Commits absents des titres | §4 l. 108, §5 l. 129 | `LEGACY-BOREE.md` l. 6 : `boree` = `4b6d130ebc9068fbd7cba0de8611737a6d9cfc18` ; `CRIN.md` l. 34 : `SquirrelBetting` = `015d263e6a3e4a56bc395a0ef0dd43c595067e60` | Les titres §4 et §5 ne portent **aucun commit**, alors que la règle §1 l. 31 de la matrice impose « chemin exact **et commit** ». Seul §3 porte `athanor@6dacc87` | Mineur |
| m3 | Vocabulaire d'état | §3 à §5 | `LEGACY-BOREE.md` §1 : « **I+** = implémenté et vérifie (**un test nommé le couvre**) » | §1 l. 19 annonce « Implémenté, documenté, expérimental, obsolète » ; les tableaux emploient 28 fois « Implémenté **et testé** » et des états hors nomenclature (« Dans `athanor` », « Absent », « Écrit », « Exercé en série », « Retiré », « Majoritairement obsolètes », « Pattern, code non testé ») | Mineur |
| m4 | « Implémenté et testé » | 28 lignes | `LEGACY-BOREE.md` §8 : « Les états "implémenté et vérifie" signifient "couvert par un test nommé", **pas "test passe"** » ; `CRIN.md` §9.2 : « jamais sur une exécution » | « Implémenté et **testé** » se lit comme « les tests passent ». Le préambule de la matrice (l. 7-9) couvre la réserve, mais la nuance n'est pas portée dans la matrice elle-même | Mineur |
| m5 | Unité de la colonne « Coût » | §4 | `CRIN.md` §8 : « Coût de reprise » qualitatif (Faible / Moyen / Élevé) | §4 mêle des volumes (« ~200 l. », « ~150 l. », « ~120 l. », « ~60 l. ») et des mentions qualitatives (Moyen / Élevé / Nul / Faible) : la colonne n'est pas comparable et ne recoupe pas la source | Mineur |
| m6 | Connecteurs : liste tronquée | §5 l. 157 | `LEGACY-BOREE.md` l. 746 : `entsoe_api.py`, `ecmwf_direct.py`, `eua.py`, **`europe.py`**, `runs.py` | « `src/boree/ingest/*` » — `europe.py` disparaît de la liste | Mineur |
| m7 | Justification amputée (collecteur) | §5 l. 158 | `LEGACY-BOREE.md` l. 747 : « Doublon de `athanor.data.source` (**+ `data/compliance.py` pour robots.txt et conditions d'usage**) » | « Doublon de `athanor.data.source` » — la mention est conservée au §7 l. 203, pas ici | Mineur |
| m8 | Justification amputée (Parquet) | §5 l. 137 | `LEGACY-BOREE.md` §2.5 : « la lecture DuckDB **locale, sans serveur** » est explicitement listée comme transposable | « partitionnement `annee=/mois=`, réécriture atomique » — la propriété DuckDB local disparaît | Mineur |
| m9 | Origine incomplète (H2/H3/H4) | §5 l. 166 | `LEGACY-BOREE.md` l. 761 : `src/boree/modeles.py`, `chaine/modeles.py`, **`registre/familles/`** | `registre/familles/` omis — le répertoire existe dans le dépôt audité | Mineur |
| m10 | Origine incomplète (juge d'hiver) | §5 l. 167 | `LEGACY-BOREE.md` l. 762 : `src/boree/chaine/juger_hiver.py`, **`evaluation/juge.py`** | `evaluation/juge.py` omis — le fichier existe dans le dépôt audité | Mineur |
| m11 | Justification amputée (doctrine) | §3 l. 106 | `ATHANOR.md` l. 423 : « 9 leçons étayées par des verdicts (L1–L9) **+ 5 familles de mécanismes + les règles du jugement** » | « 9 leçons étayées par des verdicts » | Mineur |
| m12 | Nuance de l'exploration | §3 l. 92 | `ATHANOR.md` §3.4 : « Transposable à TORNE : oui, **presque intégralement** … C'est le **second candidat `REUSE` majeur** après `stats/` » | « la brique **la plus** transposable pour chercher des modèles » — plus affirmatif que « presque intégralement ». La décision `ADAPT` du tableau de verdict (l. 409) est bien reprise | Mineur |
| m13 | Chemin inexistant (§8) | §8 l. 219 | `LEGACY-BOREE.md` l. 418 et l. 772 : le fichier est `tests/fabrique.py`, à la racine du dépôt `boree` (hors paquet `boree`) | « `boree.tests.fabrique.py` » — module inexistant. Contrôle direct : `src/boree/tests` est absent. La ligne 150 du même document écrit correctement `tests/fabrique.py` | Mineur |
| m14 | Fautes de copié-collé | §7 l. 203, §6 l. 186 | — | « **Athoran** » (l. 203) ; « ».Component réutilisable » » (l. 186, résidu d'un autre modèle de texte) | Mineur |

---

## 3. Les manquants

### 3.1 Ce qui figure dans un rapport et pas dans la matrice

**C.R.I.N. — 22 lignes de verdict sans ligne dans la matrice** (rapport : `docs/audit/CRIN.md` §8, l. 507-545).

| Rapport §8 | Composant | Chemin | Décision source |
|---|---|---|---|
| l. 508 | Gouvernance du choix de la correction de multiplicité | `crin/quant_fund_validation.py:64-70` | **REUSE** |
| l. 510 | Matrices déterministes (passe chronologique unique) | `crin/datasets.py:929`, `:1331` | **REUSE** |
| l. 511 | Test anti-fuite « une observation future ne change rien » | `tests/test_crin_datasets.py:263` | **REUSE** |
| l. 512 | Artefact de modèle auto-porteur | `crin/models.py:79-98` | **REUSE** |
| l. 513 | Alignement entraînement / inférence | `crin/models.py:141-149`, `:115-125` | **REUSE** |
| l. 514 | Manifeste d'expérience | `crin/manifest.py:24,44,66` | **REUSE** |
| l. 515 | Corrections de multiplicité (BH, Bonferroni, Romano-Wolf) | `crin/multiple_testing.py:109,142,149` | **REUSE** |
| l. 516 | SPA, PBO/CSCV, Deflated Sharpe, bootstrap cluster | `crin/quant_fund_validation.py:172,403,604`, `:138` | **REUSE** |
| l. 517 | e-values et confidence sequences | `crin/evalues.py:64,146,194` | **REUSE** |
| l. 522 | Détection de dérive par PSI | `crin/drift.py:147,171` | **REUSE** |
| l. 531 | Pattern « payload brut immuable » | `crin/db.py:9-11` | **REUSE** |
| l. 518 | Moniteur de flux (ROI) et déviation Brier | `crin/evalues.py:239,454` | **ADAPT** |
| l. 523 | Pont Bronze → features pour la dérive | `crin/drift_bridge.py:273,331` | **ADAPT** |
| l. 526 | Comparaison de K estimateurs + harnais de sanité | `crin/sota_estimators.py:209,245,449,539` | **ADAPT** |
| l. 530 | Journal d'audit append-only | `crin/execution/audit.py:39-61` | **ADAPT** |
| l. 532 | Runner long, heartbeat, arrêt gracieux | `crin/runner.py:91` | **ADAPT** |
| l. 533 | Processus Hawkes (baseline inhomogène figée) | `crin/hawkes.py:1-21` | **ADAPT** |
| l. 534 | Pipeline HTML → embeddings | `crin/text_embeddings.py` | **ADAPT** |
| l. 529 | Gate Phase 2 (modèle vs référentiel) | `crin/gate_phase2.py` | **REIMPLEMENT** |
| l. 527 | Estimateurs TabPFN / TabICL | `crin/sota_estimators.py:280,355` | **REJECT** |
| l. 535 | Ingestion on-chain / marché prédictif | `crin/polymarket/` | **REJECT** |
| l. 545 | Interface d'exécution (3 impls annoncées) | `crin/execution/provider.py:3` | **REJECT** |

*Mention groupée qui les couvre : **aucune**.* Le §8 de la matrice ne cite de C.R.I.N. que « les gates de C.R.I.N. »
(l. 222) ; le §9 (l. 228-229) ne couvre que le volet hippique, le pool/Shin, Kelly, le settlement, les règles de
marché et les 43 domain adapters — donc ni les 11 `REUSE`, ni les 7 `ADAPT`, ni le `REIMPLEMENT` ci-dessus, ni les
trois `REJECT` (TabPFN/TabICL, polymarket, `crin/execution/provider.py`).

**C.R.I.N. — 2 lignes fusionnées avec perte d'information :**

- l. 509 « Gates G0 → G7 » (`docs/concepts/GATES.md`, `REUSE`) : fusionnée dans la ligne 117 du §4, dont l'origine a été
  remplacée par les registres de preregs — `docs/concepts/GATES.md` disparaît de la matrice.
- l. 528 « Pipeline d'hypothèses preregistrées + kill-switch » (`crin/pipeline.py`, `REIMPLEMENT`) : fusionnée dans la
  ligne 119, dont l'origine « Pattern, non isolé » perd le chemin et le coût.

**Ancien BORÉE — 2 lignes sans ligne dans la matrice** (rapport : `docs/audit/LEGACY-BOREE.md` §9).

| Rapport §9 | Composant | Chemin | Décision source | Couverture |
|---|---|---|---|---|
| l. 766 | Flux vide type, instant jamais NaT | commits `c6290a9`, `725d2e0` | **ADAPT** | *partielle* — la ligne 144 (§5) évoque « la règle de l'absence explicite », qui est une **autre** règle ; la discipline « flux vide garde ses types » (LEGACY §2.12, §4.5) n'est pas reprise |
| l. 775 | Paquet de référence greenfield V2.0 | `BOREE_W2M_Greenfield_Reference_V2.0/` | **REJECT** | *aucune* — ni §5, ni §8, ni §9 |

### 3.2 Ce qui figure dans la matrice et pas dans les rapports

**Aucun.** Les 84 lignes de la matrice se rattachent toutes à une ligne de verdict des trois rapports : aucun composant
n'est inventé, aucune décision n'est orpheline. C'est le point le plus solide de la transcription.

### 3.3 Effet net sur le §8

Le §8 (ordre d'extraction) est cohérent avec les rapports pour ses points 1, 2, 3 et 6 :

- point 1 (noyau statistique `athanor.stats`) ← `ATHANOR.md` §7 « À REPRENDRE » 1-2 ;
- point 2 (`athanor.data.source`, `athanor.data.rawstore`) ← `LEGACY-BOREE.md` §2.1 et §2.6 ;
- point 3 (discipline d'ingestion BORÉE) ← `LEGACY-BOREE.md` §10.2 items 1, 2, 3, 5 ;
- point 6 (« refus outillé ») ← `LEGACY-BOREE.md` §4.11 et §10.2 item 7, `ATHANOR.md` §2.2.

Il est en revanche **en défaut sur le point 5** (voir M7) et il **oublie le cœur de C.R.I.N.** : le rapport CRIN
§10.4 dit que la valeur du dépôt tient en six mécanismes réutilisables tels quels, dont quatre ne figurent nulle part
dans la matrice ni dans l'ordre d'extraction.
---

## 4. Formulations à durcir

Phrases de la matrice qui affirment **plus** que leur source, ou qui en inversent le sens. La colonne de droite donne
la formulation source, la colonne de gauche celle à employer.

| Ligne | Formulation de la matrice (à durcir) | Formulation que la source permet |
|---|---|---|
| §4 l. 117 | « **Exercé en série** » | « **Documenté uniquement** » — `CRIN.md` l. 507 et l. 509. Et l'origine doit mentionner `docs/concepts/GATES.md` |
| §3 l. 93 | « conception intègre » (sans réserve de couverture) | « conception intègre, mais **seulement 4 tests pour 255 lignes** » — `ATHANOR.md` l. 410 et §4.3 |
| §4 l. 118 | « Implémenté et testé » pour `crin/tritemporal.py` | « Implémenté et **vérifié** (couvert par un test nommé ; test non exécuté) » — `LEGACY-BOREE.md` §1 et §8, `CRIN.md` §9.2 |
| §8 l. 221 | « Le cadre de pré-enregistrement **outillé** » | « Le cadre de pré-enregistrement — **écrit, non outillé** des deux côtés » — `LEGACY-BOREE.md` l. 773, `CRIN.md` §2.10 |
| §8 l. 222 | « les gates de C.R.I.N. (**exercés**) » | « les gates de C.R.I.N. (**documentées, jamais outillées** : le lien prereg → exécution → verdict est humain) » — `CRIN.md` l. 509, §2.10, §2.14 |
| §8 l. 222 | « l'un donne la discipline, **l'autre le format** » | « **le format BORÉE est le plus strict des deux** et doit être appliqué à C.R.I.N. » — `CRIN.md` l. 213 et §10.1 |
| §7 l. 207 | « `C.R.I.N.` l'ignore, ce qui est son erreur » | « `C.R.I.N.` réimplémente les mêmes primitives sans connaître `athanor` — **constat de comparaison, non attesté par le rapport CRIN** » |
| §6 l. 191 | « Les décisions `REUSE` de la matrice sont donc **actionnables immédiatement** » | « Les décisions `REUSE` portant sur **`athanor`** sont actionnables ; **celles portant sur C.R.I.N. ne le sont pas** tant que le statut de ce dépôt n'est pas établi » — `CRIN.md` §6.1 |
| §8 l. 211 | « **une fois la licence clarifiée** » | à supprimer : le §6 l. 191-192 déclare la réserve juridique levée pour Athanor |
| §4 l. 114 | « la référence pour **la couche financière** » | la source ne dit rien de la couche financière pour `crin/calibration.py` : rattacher à `CRIN.md` §2.7 ou retirer |
| §9 l. 228 | liste présentée comme exhaustive | introduire par « **notamment** », ou compléter par les 9 rejets listés au §3.1 ci-dessus |
| §3 l. 92 | « la brique **la plus** transposable » | « transposable **presque intégralement** » — `ATHANOR.md` §3.4 |

---

## 5. Ce qui est correct

### 5.1 Par dépôt

| Dépôt | Lignes de la matrice | Décisions conformes à la source | Chemins et coûts | Réserves |
|---|---|---|---|---|
| `athanor` (§3) | 30 | **30 / 30** | conformes (volumes de lignes repris à l'identique : 190, 412, 97, 108, 287, 176, 198, 293, 151, 131, 75, 52, 66, 270, 455, 411, 255, 376, 515, 424, 450, 73, ~300, 110) | l. 73 (compte de lignes), l. 92 (nuance), l. 93 (durcissement), l. 106 (amputation) |
| `SquirrelBetting` / C.R.I.N. (§4) | 14 | **14 / 14** | 12 / 14 conformes | l. 117 (état durci + origine), l. 119 (origines + coût), l. 120 (chemin), l. 122 (nuance `BenchmarkProvider` omise) |
| ancien `boree` (§5) | 40 | **40 / 40** | 38 / 40 (origines l. 166 et l. 167 incomplètes) | l. 137 et l. 158 (justifications amputées) ; 2 lignes du rapport absentes (M5) |

### 5.2 Conformités de fond, confirmées

- **Aucune décision inversée** sur les 84 lignes. Les 15 lignes `REUSE` d'Athanor, les 6 lignes `REUSE` de C.R.I.N. et
  les 0 ligne `REUSE` de l'ancien BORÉE sont cohérentes avec les tableaux de verdict respectifs. Le choix de ne
  prononcer aucun `REUSE` sur l'ancien `boree` est conforme à `LEGACY-BOREE.md` §7 principe 1 (« aucun composant
  n'est réutilisable en l'état », pas de fichier de licence).
- **Aucun composant inventé** : les 84 lignes se rattachent toutes à une ligne de source.
- **Les comptes de tests d'Athanor repris par la matrice sont exacts** — recomptage direct des fonctions `def test_`
  dans `athanor/tests/` : `test_evalues.py` 37, `test_multiplicity.py` 15, `test_overfitting.py` 27,
  `test_power.py` 14, `test_calibration.py` 18, `test_intervals.py` 28, `test_variance_reduction.py` 10,
  `test_scoring.py` 10, `test_breaks.py` 7 — identiques aux chiffres du rapport et de la matrice.
- **Les chemins cités existent** dans les dépôts audités — contrôle direct : `crin/contracts.py` présent et
  `crin/ingest` absent ; `boree/tests/fabrique.py` présent et `boree/src/boree/tests` absent ;
  `boree/src/boree/registre/familles/` présent ; `boree/src/boree/evaluation/juge.py` présent ;
  `boree/BOREE_W2M_Greenfield_Reference_V2.0/` présent ; `athanor` à `6dacc87`, `boree` à `4b6d130e`.
- **Aucun fichier de licence** dans `athanor`, `SquirrelBetting` ni `boree` (recherche récursive `LICENSE*`,
  `LICENCE*`, `COPYING*`, `NOTICE*`, venv exclus) — confirme les trois rapports.
- **Le préambule de la matrice est exact** : `torne` compte **1 commit** (`7153a29`), `src/torne/__init__.py` est une
  amorce documentaire et `tests/test_package.py` un test de fumée ; aucune brique extraite n'est dans le dépôt. La
  mention « `uv` est absent du poste de construction et le paquet `athanor` n'y est pas installé » est cohérente avec
  les trois rapports.
- **Les six doublons attestés du §7** le sont bien, avec leurs deux occurrences :
  magasin brut (`ATHANOR.md` §2.3 + `LEGACY-BOREE.md` §2.1) ; registre de modèles (`ATHANOR.md` §2.3 §registre +
  `LEGACY-BOREE.md` §2.8) ; contrat de connecteur (`LEGACY-BOREE.md` §2.6) ; gestion des secrets
  (`LEGACY-BOREE.md` §6.5) ; client S3 (`LEGACY-BOREE.md` §2.10) ; fermeture du code de mesure
  (`ATHANOR.md` §1.2 `research/provenance.py` + `LEGACY-BOREE.md` §2.4).
- **Le §10** (règle de coexistence) est cohérent avec `LEGACY-BOREE.md` §6.3 (« jamais référencé comme une dépendance
  externe ») et §10.3 (protocole scellé hors périmètre).

### 5.3 Les arbitrages du principal qui sont légitimes

Trois éléments de la matrice ne viennent pas des rapports mais sont des décisions du principal, clairement assumées
comme telles et sans contradiction avec les sources : la clôture juridique du §6 (autorité du propriétaire sur son
propre dépôt privé), la granularité de six colonnes du §1 (« les champs omis … sont détaillés dans les trois
rapports d'origine, qui font foi » — ce qui est exact), et le fait de retenir `athanor` comme socle de référence.
Ils signalent la seule chose à corriger : le §6 doit être explicite sur le périmètre qu'il couvre.

---

## 6. Vérifications impossibles à faire

1. **Aucun test n'a été exécuté**, ni par moi ni par les trois rapports (absence de `uv` et des dépendances). « Implémenté
   et testé » ne dit rien de l'état d'exécution : je n'ai recompté que des *fonctions de test*, pas des résultats.
2. **Les totaux globaux n'ont pas été recomptés** : « 457 fonctions de test » (boree), « 1 580 » (C.R.I.N.),
   « ~950 » (Athanor), ni les inventaires de 48 / 84 / 94 fichiers de test. Seuls les fichiers cités par la matrice
   ont été recomptés.
3. **`PREREG.md` (275 Ko) et ses 48 amendements n'ont pas été lus**, ni `PREREG_DE/ES/NL` — `LEGACY-BOREE.md` §8 le
   signale. L'état « Écrit, non outillé » de la ligne 151 est donc repris tel quel, non vérifié.
4. **Le statut de `SquirrelBetting` n'est établi nulle part** : le dossier `.git/config` donne la remote
   `https://github.com/RootSquirrels/SquirrelBetting.git`, sans dire si le dépôt est privé ni à qui il appartient. Ni le
   rapport CRIN ni la matrice ne tranchent. **C'est la question à poser au principal** : le dépôt est-il bien privé et
   du même propriétaire ? Sans réponse, les lignes `REUSE` de C.R.I.N. (§4 l. 114, 115, 117, 118) ne sont pas
   actionnables, et le §6 doit les exclure explicitement.
5. **L'affirmation « Exercé en série » (§4 l. 117) n'est ni confirmable ni infirmable** : 82 fichiers `docs/` de C.R.I.N.
   n'ont pas été lus, dont les 15 preregs actives et les 9 tuées en entier (`CRIN.md` §9.5). Le seul fait établi est
   le décompte : 16 preregs actives, 9 tuées.
6. **Les parties non lues des rapports eux-mêmes** : `ATHANOR.md` §8.8 signale `docs/METHODES.md` (62 Ko) et
   `docs/PORTING.md` (75 Ko) non lus ; `CRIN.md` §9.6 signale 204 scripts non lus ; `LEGACY-BOREE.md` §0.2 signale
   18 modules `evaluation/` non lus. Une décision prise sur un en-tête peut être rectifiée par une lecture intégrale.
7. **L'historique complet de `torne` n'a pas été fouillé** : `git` est absent du PATH (binaire de GitHub Desktop
   utilisé en lecture seule). L'arbre de travail contenait des modifications non commitées (`docs/REUSE_AUDIT.md`,
   `docs/DECISIONS.md`, `pyproject.toml` modifiés ; `docs/PROGRAMME.md` et `uv.lock` non suivis) : **la version
   vérifiée est celle de l'arbre de travail, pas celle du commit `7153a29`**.
8. **La LICENSE de `athanor` n'a pas été « lue »** parce qu'elle n'existe pas : la clôture du §6 repose donc sur une
   qualité de propriétaire (dépôt privé), pas sur un fichier — ce que la règle §1 l. 36-37 de la matrice ne prévoit
   pas. C'est une décision à assumer explicitement, pas un oubli.
---

## 7. Corrections proposées (NON appliquées)

Les textes ci-dessous sont des **propositions** ; `docs/REUSE_AUDIT.md` n'a pas été modifié.

### 7.1 Corrections ponctuelles

| Ligne | Actuel | Proposé |
|---|---|---|
| §3 l. 73 | « Rapport complet : `docs/audit/ATHANOR.md` (374 lignes). » | « Rapport complet : `docs/audit/ATHANOR.md` (489 lignes). » |
| §3 l. 92 | « … la brique la plus transposable pour chercher des modèles ; vocabulaire à refaire » | « … transposable presque intégralement (le second candidat `REUSE` après `stats/`) ; vocabulaire à refaire » |
| §3 l. 93 | « Ridge + λ interne, purge, embargo 30 j : conception intègre ; mais `FOLDS` codé en dur (`:31`) et `Outcome.net(side, borrow)` est une interface de pari » | « Ridge + λ interne, purge, embargo 30 j : conception intègre ; mais `FOLDS` codé en dur (`:31`), `Outcome.net(side, borrow)` est une interface de pari, et **seulement 4 tests pour 255 lignes — brique sous-testée** » |
| §3 l. 106 | « 9 leçons étayées par des verdicts : actif de **raisonnement**, à réécrire en français avec d'autres preuves » | « 9 leçons étayées par des verdicts, + 5 familles de mécanismes + les règles du jugement : actif de **raisonnement**, à réécrire en français avec d'autres preuves » |
| §4 l. 114 | « Le cœur de l'évaluation, sans jargon hippique ; la référence pour la couche financière » | « Le cœur de l'évaluation, sans jargon hippique ; la métrique de comparaison entre deux modèles » |
| §4 l. 117 | Origine : « `docs/hypotheses/active/` (16 preregs) + `killed/` (9) » ; État : « Exercé en série » | Origine : « `docs/concepts/GATES.md` (gates G0→G7) + `docs/hypotheses/active/` (16 preregs) + `killed/` (9) » ; État : « Documenté uniquement — le lien prereg → exécution → verdict n'est pas outillé » |
| §4 l. 119 | Origine : « Pattern, non isolé » ; Coût : « ~150 l. estimés » | Origine : « `crin/pipeline.py` (1 765 l.) + `crin/gate_phase2.py` (315 l.) » ; Coût : « Élevé » |
| §4 l. 120 | Origine : « `crin/ingest` / contrats » | Origine : « `crin/contracts.py` (+ `contracts_pmu.py`, `contracts_letrot.py`, `contracts_fred.py`) » |
| §4 l. 122 | « Spécifique aux marchés de mutualité » | « Spécifique aux marchés de mutualité ; le patron d'abstraction « référentiel de comparaison » (`BenchmarkProvider`) reste REUSE, reformulé » |
| §5 l. 137 | « Brut = vérité, dérivé = reconstructible ; partitionnement `annee=/mois=`, réécriture atomique » | « Brut = vérité, dérivé = reconstructible ; partitionnement `annee=/mois=`, lecture DuckDB locale sans serveur, réécriture atomique » |
| §5 l. 157 | Origine : « `src/boree/ingest/*` » | Origine : « `src/boree/ingest/{entsoe_api,ecmwf_direct,eua,europe,runs}.py` » |
| §5 l. 158 | « Doublon de `athanor.data.source` » | « Doublon de `athanor.data.source` (+ `data/compliance.py` : robots.txt et conditions d'usage) » |
| §5 l. 166 | Origine : « `src/boree/modeles.py`, `chaine/modeles.py` » | Origine : « `src/boree/modeles.py`, `chaine/modeles.py`, `registre/familles/` » |
| §5 l. 167 | Origine : « `src/boree/chaine/juger_hiver.py` » | Origine : « `src/boree/chaine/juger_hiver.py`, `evaluation/juge.py` » |
| §4 l. 108 / §5 l. 129 | « ## 4. SquirrelBetting / C.R.I.N. » / « ## 5. Ancien BORÉE — `boree` » | « ## 4. SquirrelBetting / C.R.I.N. — `SquirrelBetting@015d263` » / « ## 5. Ancien BORÉE — `boree@4b6d130` » |
| §6 l. 186 | « La frontière entre « code à moi » et «.Component réutilisable » doit rester explicite. » | « La frontière entre « code à moi » et « composant réutilisable » doit rester explicite. » |
| §6 l. 191-192 | « Les décisions `REUSE` de la matrice sont donc **actionnables immédiatement**. L'ordre d'extraction du §8 ne change pas ; seule la réserve juridique disparaît. » | « Les décisions `REUSE` portant sur **`athanor`** (et sur l'ancien `boree`) sont actionnables immédiatement. **Celles portant sur C.R.I.N. ne le sont pas** : tant que le statut de `SquirrelBetting` n'est pas établi par le propriétaire, elles restent bloquées, comme le dit `CRIN.md` §6.1. » + alinéa : « **C.R.I.N. n'est pas couvert par la présente clôture** : aucun fichier de licence dans le dépôt (`CRIN.md` §6.1) ; la remote est `github.com/RootSquirrels/SquirrelBetting`, dont la propriété et la visibilité ne sont établies par aucun document du dépôt. » |
| §7 l. 203 | « **Un seul.** Athoran couvre aussi robots.txt et conditions d'usage. » | « **Un seul.** Athanor couvre aussi robots.txt et conditions d'usage. » |
| §7 l. 207 | « **Un seul.** `boree` l'utilise déjà ; `C.R.I.N.` l'ignore, ce qui est son erreur. » | « **Un seul.** `boree` l'utilise déjà (`athanor` y est une dépendance éditable, `LEGACY-BOREE.md` §6.2-6.3). C.R.I.N. réimplémente les mêmes primitives (`crin/evalues.py`, `crin/multiple_testing.py`, `crin/quant_fund_validation.py`) sans les connaître — **constat de comparaison, non attesté par le rapport CRIN**. » |
| §8 l. 211 | « Par ordre de valeur par unité de coût, **une fois la licence clarifiée** : » | « Par ordre de valeur par unité de coût : » |
| §8 l. 219 | « Le store synthétique anti-fuite (`boree.tests.fabrique.py`) » | « Le store synthétique anti-fuite (`boree` : `tests/fabrique.py`) » |
| §8 l. 221-222 | « **Le cadre de pré-enregistrement outillé** : les amendements datés de `boree` (écrits) et les gates de C.R.I.N. (exercés) — l'un donne la discipline, l'autre le format. » | « **Le cadre de pré-enregistrement — règle écrite, à outiller** : les amendements datés de `boree` (le format le plus strict des deux, à reprendre tel quel) et le registre de preregs de C.R.I.N. (même mécanique, format à durcir — date + commit — et lien prereg → exécution non outillé). » |

### 7.2 Lignes à ajouter

- **§4 — 22 lignes** reprenant mot pour mot les 22 lignes de verdict du tableau §3.1 ci-dessus (colonnes
  « Composant / Origine / État / Décision / Justification / Coût » construites à partir de `CRIN.md` §8), en
  particulier les 11 `REUSE` : gouvernance de la correction de multiplicité, matrices déterministes, test anti-fuite,
  artefact auto-porteur, alignement entraînement/inférence, manifeste, corrections de multiplicité,
  SPA/PBO/DSR, e-values et confidence sequences, PSI de dérive, payload brut immuable.
  Les quatre mécanismes nommés par `CRIN.md` §10.4 doivent y figurer explicitement, pour que le §8 puisse s'appuyer
  dessus.
- **§5 — 2 lignes** : « Flux vide type, instant jamais NaT » (`ADAPT`) et « Paquet de référence greenfield V2.0 »
  (`REJECT`).
- **§8** : un point pour le test anti-fuite de C.R.I.N. (`tests/test_crin_datasets.py:263`), qui est l'exact
  équivalent du store synthétique déjà prévu au point 4, et un point pour la gouvernance de la correction de
  multiplicité (`CRIN.md` §2.8 : « le cœur le plus transposable du dépôt »).
- **§9** : ajouter TabPFN/TabICL, `crin/polymarket/`, `crin/execution/provider.py`, `scripts/crin/` (projet Stranger),
  les 108 scripts d'exploration, le paquet de référence V2.0, la salle de commandement (frontend), le jumeau retiré et
  le marché EEX / quotas / TTF ; ou introduire la section par « notamment ».

### 7.3 Correction systémique

- **Vocabulaire d'état** (§1 l. 19 et les 28 occurrences de « Implémenté et testé ») : soit remplacer partout par
  « Implémenté et vérifié (couvert par un test nommé ; test non exécuté) », soit ajouter à §1 une ligne explicite :
  « « Implémenté et testé » signifie *couvert par un test nommé*, jamais *test exécuté et passé* — aucun code n'a été
  exécuté lors de cette phase. »
- **Colonne « Coût » du §4** : choisir une seule unité (volume de lignes **ou** coût de reprise qualitatif), et
  l'annoncer dans le format de la matrice.

---

## 8. Méthode de la revue

- Lecture intégrale des quatre documents (243 + 489 + 606 + 857 lignes).
- Confrontation ligne à ligne des 84 lignes de la matrice avec les 111 lignes de verdict des trois rapports
  (`ATHANOR.md` §7, `CRIN.md` §8, `LEGACY-BOREE.md` §9), décision, chemin, état, justification et coût.
- Contrôle indépendant sur les dépôts audités, en lecture seule :
  - recomptage des fonctions `def test_` dans les fichiers de test d'Athanor cités par la matrice ;
  - existence des chemins cités (`crin/contracts.py`, `crin/ingest`, `tests/fabrique.py`, `registre/familles/`,
    `evaluation/juge.py`, `BOREE_W2M_Greenfield_Reference_V2.0/`) ;
  - recherche récursive des fichiers `LICENSE*` / `LICENCE*` / `COPYING*` / `NOTICE*` dans les trois dépôts ;
  - lecture de `.git/config` de `SquirrelBetting` ;
  - état du dépôt `torne` (1 commit, `src/`, `tests/`) via le binaire `git` de GitHub Desktop, en lecture seule.
- Aucun fichier du dépôt n'a été modifié, à l'exception du présent rapport.