# TORNE — Pré-enregistrement 001

**État : `planned` — non gelé, et en attente.**
**Ce pré-enregistrement n'est pas l'expérience fondatrice de TORNE pour l'instant.** Il est conservé
tel quel, avec ses inconnues nommées, comme **piste de recherche documentée** : le programme a été
réordonné le 31 octobre 2026 pour construire d'abord la capacité à observer un domaine physique
(`docs/PROGRAMME.md`, séquence S2→S5).

**Ce que cela change, et ce que cela ne change pas.** Un pré-enregistrement est indispensable avant
l'analyse confirmatoire ; il ne doit pas empêcher l'exploration préalable des données, et il n'a pas à
la précéder. L'exploration qui rendra cette hypothèse confirmable ou réfutable est **explicitement
autorisée** — et elle n'est pas une analyse confirmatoire : elle ne teste pas H1 (§B.3), elle ne fixe
aucun seuil, et elle ne consomme pas la période réservée (§C.5). Un pré-enregistrement consulté après
exploration reste pré-enregistré ; c'est ce qui lui vaut. Ce qui est interdit reste interdit : la
réservation de données, la définition du seuil, et le choix des variantes se font **avant** la lecture
de la période test, et toute dérogation crée un amendement append-only (ADR-012 §4).

Ce document est rédigé **avant** tout calcul sur les données de l'expérience : il ne le sera plus
jamais après. Il suit le gabarit `protocol/PREREGISTRATION-TEMPLATE.md` et la fiche
`protocol/PREREG_PHYSIQUE.md` du paquet de référence V2.0.

**Convention de libellé.** `[FAIT]` vérifié par exécution ou lecture directe de la source ;
`[INFÉRENCE]` déduit de faits vérifiés ; `[CLAIMÉ]` l'éditeur ou la documentation l'affirme, sans
vérification indépendante ; `[INCONNU]` non déterminé. Un champ non applicable porte `N/A` **avec
justification** : il n'est jamais supprimé silencieusement.

## A. Identité et gouvernance

### A.1 Identifiants

- `research_lineage_id` : `TORNE-LINEAGE-EXP-001`
- `preregistration_id` : `TORNE-PREREG-001`
- `research_programme` : `physical_discovery`
- `trial_family_id` : `TORNE-PTF-001` (famille : cohérence inter-agences de l'état hydrologique)
- `owner` : propriétaire du dépôt `github.com/RootSquirrels/torne`
- `created_at_utc` : 2026-10-31
- `freeze_at_utc` : *à fixer* — au plus tard le jour du premier calcul sur les données de l'expérience
- `protocol_version` : 1.0
- `parent_preregistration_id` : N/A — premier pré-enregistrement du dépôt
- `code_commit` et environnement : `c535011` (branche `main`), Python 3.12, `uv` 0.13.6, verrou `uv.lock`
- Statut : `planned`

### A.2 Ce qui a motivé cette expérience

La sélection a suivi trois portes dures du paquet de référence — **T1** (cible latente, non
publiée), **T2** (juge indépendant), **identifiabilité** — appliquées à sept candidats sur six
domaines. La proposition Mississippi antérieure échoue à T1 (heures de fermeture USACE publiées
directement) et à T2 (taux de fret USDA/AMS issus du même marché que le produit explique). Le
raisonnement complet est dans `docs/SLICE-PREMIER.md`.

### A.3 Ce qui est demandé au propriétaire

- **Accepter la correction** de la latence `available_transport_capacity` de SPEC-003 §131, non
  identifiable depuis des sources publiques (flotte et mix de cargaison non accessibles), et la
  **remplacer** par la formulation retenue ici. C'est une correction du **paquet de référence** :
  elle n'est pas appliquée dans le dépôt, et le paquet reste en lecture seule.

### A.4 Conditions de gel

Ce pré-enregistrement ne passe à `preregistered` qu'une fois :

1. le **socle d'acquisition** est opérationnel et les sources de l'expérience sont intégrées — sans
   cela, il n'y a rien à explorer ni à confirmer ;
2. les **tests d'accès** leveurs (§C.4) rendus, avec leur verdict ;
3. l'**instanciation par source** de la procédure `usable_at` (`docs/CONTRATS_FONDAMENTAUX.md`
   §3.10 et §3.11) écrite pour chaque source retenue ;
4. la **revue de l'art antérieur** sur la dispersion inter-agences hydrométriques consultée (§B.5) ;
5. les **seuils et définitions** de §D et §G figés, avec les variantes autorisées énumérées ;
6. le **commit du code** qui exécutera l'expérience relevé.

Un changement ultérieur de population, d'admissibilité temporelle, de définition physique, de
juge, d'estimand ou de critère de décision crée un **amendement append-only** et une nouvelle
version de famille (ADR-012 §4).

## B. Question et hypothèse

### B.1 Question de recherche

> **Quelle est l'amplitude de la divergence entre les reconstructions hydrométriques française,
> allemande et néerlandaise de l'état du Rhin, et à quel point cette divergence déplace-t-elle le
> nombre de jours de basses eaux — la grandeur opérationnelle sur laquelle le fret fluvial, les
> autorisations et la politique climatique du bassin sont écrits ?**

### B.2 Affirmation, et ce qu'elle n'est pas

- **Nature de l'affirmation** : **reconstruction** (état harmonisé) et **explication** (attribution
  de la divergence à un mécanisme).
- **Ce n'est pas** une prédiction, ni une affirmation causale, ni une affirmation de performance
  financière, ni un arbitrage « quelle agence a raison » au-delà de l'horizon satellitaire.

### B.3 Hypothèse principale

**H1.** La divergence inter-agences sur le compte de jours de basses eaux est **non nulle et
mesurable** : il existe un seuil `δ` de divergence, fixé avant l'exécution, au-delà duquel le
compte de jours de basses eaux n'est pas invariant au choix de l'agence.

**H1 est réfutable**, et sa réfutation est un résultat publiable (§B.4).

### B.4 Hypothèse nulle — pré-enregistrée comme résultat valide

**H0.** « Les agences concordent » : la divergence résiduelle, une fois neutralisées les écarts de
datum et les révisions de courbe de tarage documentés, est inférieure au seuil `δ` sur toutes les
sections et toutes les années d'épisodes indépendants.

**H0 n'est pas un échec de l'expérience.** C'est un résultat : il signifierait que l'infrastructure
de mesure du bassin est plus cohérente qu'on ne le supposait, et que le compte de jours de basses
eaux est un invariant pratique. Un rapport qui publie H0 comme résultat est un rapport valide.

### B.5 Hypothèses alternatives et résultats qui réfuteraient H1

| Réfutation | Formulation |
|---|---|
| **R1 — dispersion non identifiable** | Les écarts de niveau entre agences ne sont pas interprétables faute de transformations de datum documentées. **Cette réfutation est en tête de liste** : elle rend le résultat non interprétable, pas négatif. |
| **R2 — dispersion déjà expliquée** | La divergence résiduelle est entièrement dominée par des révisions de courbe de tarage et des changements de capteur déjà documentés. Le résidu est alors le résultat, et la contribution de l'expérience est l'inventaire des révisions. |
| **R3 — dispersion non attribuable** | La divergence résiduelle ne se laisse pas décomposer par mécanisme, faute de métadonnées de révision. |
| **R4 — puissance insuffisante** | Le nombre d'épisodes indépendants est trop faible pour distinguer `δ` du bruit. → conclusion **inconclusive**, qui reste un résultat valide. |
| **R5 — accord apparent par convergence d'hydrologie partagée** | Les agences convergent sur les *niveaux* parce qu'elles partagent la même hydrologie amont, et non parce que leurs traitements concordent. Le test doit alors être **sensible au traitement, non à la physique partagée**. |

### B.6 Antériorité

Les affirmations « personne ne publie cette grandeur harmonisée » sont **[INFÉRENCE]**, déduites de
l'inspection des catalogues de sources et de la littérature du domaine connue — **pas** d'une revue
systématique de la littérature. Une revue ciblée précède le gel (§A.4.3).

## C. Données et temporalité

### C.1 Sources retenues, et statut de publication

| Source | Ce qu'elle donne | Accès | Profondeur | Cadence | Sémantique temporelle | Libellé |
|---|---|---|---|---|---|---|
| **Hub'EAU v2** `observations_tr` (FR) | niveau et débit en temps réel, avec **méthode, qualification, statut, continuité, système de datum altimétrique** | API ouverte, sans clé | 41 650 597 obs [FAIT] | temps réel | Vivant, qualificatifs explicites | **[FAIT]** — interrogée le 31 octobre 2026, HTTP 206, `api_version` 2.0.1 |
| **Hub'EAU v2** `obs_elab` (FR) | historique élaboré | API ouverte | 275 750 201 lignes, plus ancien échantillon 2012-12-01 [FAIT] | irrégulier | **Remplissage a posteriori** : décrit, ne prouve pas la disponibilité passée | **[FAIT]** pour le volume ; **descriptif seul** |
| **ELWIS / PEGELONLINE** (DE) | réseau allemand, niveau et débit, courbes de tarage | web ouvert | site joignable ; **granularité du point d'accès en masse non confirmée** | quotidien / quasi temps réel | mixte | **[FAIT]** joignable ; **[INCONNU]** sur le reste |
| **Rijkswaterstaat** (NL) | réseau néerlandais, jauges de référence | **[INCONNU]** | — | — | — | **[INCONNU] — injoignable depuis ce poste.** « Injoignable ici » n'est pas « indisponible » |
| **NASA SWOT** (PO.DAC) | altimétrie d'eau de surface, rivière et lac | ouverte | depuis juillet 2022 | revisite ~21 jours | instrument stable, révision quasi nulle | **[FAIT]** page joignable ; **[INCONNU]** sur la jointure aux sections |
| **Copernicus Sentinel-1 / -2** | largeur de rivière, délimitation de surface | catalogue ouvert, téléchargement sous compte | S1 2014-04-02, S2 2015-06-22 | 6 / 12 jours | **Retraité** : `OriginDate` et `PublicationDate` séparés de plusieurs mois | **[FAIT]** |
| **DWD HYRAS-DE-PR** | précipitations grillées journalières (DE) | ouverte (inscription) | jusqu'à 1931 | quotidienne | grillé, dérivé de stations | **[CLAIMÉ]** |
| **GloFAS / EFAS** (CEMS) | prévisions et réanalyses de débit | inscription | — | quotidienne | prévision / réanalyse | **[CLAIMÉ]** — **référence et ligne de base, jamais juge** : même famille de modèles (LISFLOOD) |

### C.2 Témoins et références — le cœur de T2

| Rôle | Témoin | Classe d'indépendance | Statut |
|---|---|---|---|
| **Juge primaire** | série d'une **autre agence** à la **même section physique** (FR↔DE↔NL) | réseau, instrument, datum et chaîne de courbe de tarage distincts ; forçage, modèle et post-traitement distincts ; **géographie partagée, déclarée** | **[FAIT]** pour FR et DE ; **[INCONNU]** pour NL |
| **Arbitre à horizon long** | altimétrie satellitaire SWOT | aucune chaîne de jauges partagée ; **revisite ~21 jours** : n'arbitre pas les comptes journaliers | **[FAIT]** joignable ; jointure **[INCONNU]** |
| **Référence** | EFAS / GloFAS | modèle partagé → **non indépendant**, référence seulement | **[CLAIMÉ]** |
| **Référence** | climatologie de saison et persistance | référence simple | à fixer au gel |
| **Non indépendant — à proscrire** | toute série dérivée de la même chaîne de jauges que la reconstruction ; tout bulletin d'une agence qui serait aussi la source de la reconstruction | — | — |

### C.3 Mode de replay et preuves de disponibilité historique

- `evidence_origin` : `retrospective_reconstruction` pour la période historique ;
  `prospective_capture` pour le cycle hebdomadaire prospectif.
- Mode de replay principal : **`retrospective_descriptive`** tant que les instantanés d'agence ne
  sont pas archivés. **Aucun replay point-in-time n'est revendiqué** avant que les instantanés
  soient disponibles : la faisabilité du replay PIT est **[INCONNU]** et named access test.
- Cycle prospectif : `system_operational_replay` — TORNE n'utilise que ce qu'il a acquis, et
  publie chaque semaine.
- **Règle d'exclusion des dates inconnues** : une observation dont l'instant de publication est
  **inconnu** n'est pas admise dans une reconstitution point-in-time (§3.9 des contrats). Elle
  n'est admise qu'en **descriptif rétrospectif**, et le produit le déclare.

### C.4 Tests d'accès à lever avant le gel

1. **Source néerlandaise du Rhin** — existe-t-il un flux machine-lisible documentant le datum et
   l'historique de section ? ≈ 1 semaine. *Verdict en cours : [INCONNU].*
2. **Jointure SWOT aux sections** — le produit satellitaire peut-il être rattaché aux sections de
   référence, et avec quelle incertitude de datum ? ≈ 1 semaine.
3. **Point d'accès en masse ELWIS** — existe-t-il un export historique automatisable ? ≈ 2 jours.

### C.5 Géographie, population et fenêtres

- Géographie : corridor du Rhin, **au moins trois sections** avec une paire **inter-agences** par
  section. Les sections sont retenues par la procédure de sélection documentée au gel.
- Population : **épisodes indépendants de basses eaux**, sur 1990–2025.
- Construction / harmonisation : 1990–2015. **Test hors échantillon : 2016–2025**, qui contient les
  années de basses eaux 2018 et 2022.
- **Le dénominateur de généralisation est le nombre d'épisodes indépendants, pas le nombre de
  jours** (SPEC-003 §11 et §15 ; l'outil de puissance d'épisodes existant est utilisé).
- Données réservées à la confirmation : **la période 2016–2025 n'est consultée qu'après gel**,
  et n'a pas servi à choisir le seuil `δ`, les sections ni les règles d'harmonisation.

### C.6 Licences, rétention et restrictions

Hub'EAU, ELWIS, Copernicus et PO.DAC sont d'accès ouvert ; chaque conditions d'utilisation et
d'attribution sont vérifiées **avant** ingestion et consignées dans la fiche de source. Aucune
donnée acquise avant la vérification de licence n'est conservée au-delà de l'inspection.

## D. Branche physique — PTL

- `physical_trial_id` : `TORNE-PT-001`
- `physical_trial_family_id` : `TORNE-PTF-001`
- **Phénomène visé** : l'état hydrologique du Rhin (niveau et débit) au sens de l'harmonisation
  inter-agences, et la divergence entre reconstructions.
- **Variables sources et `feature_id`** : niveau d'eau, débit, métadonnées de station (méthode de
  mesure, qualification, statut, continuité, système de datum altimétrique, historique de
  section et de courbe de tarage). Les `feature_id` et leurs versions sont figés au gel.
- **Nature de chaque mesure** : **observation** pour les mesures d'agence ; **reconstruction**
  pour l'état harmonisé ; **explication** pour l'attribution de la divergence. Aucune estimation
  présentée comme observation.
- **Référentiel spatial et unités** : le référentiel vertical est **propre à chaque agence** ;
  les unités (m, m³/s) et le système de datum altimétrique sont portés par la source et
  **convertis seulement si la transformation est documentée**. Sans transformation documentée, les
  niveaux absolus ne sont pas comparables — c'est la réfutation **R1**.
- **Fenêtre de référence / climatologie** : à fixer au gel.
- **Ajustement saisonnier** : à fixer au gel ; toute variante est listée en §G.5.
- **Seuils, formules et paramètres** : le **seuil de basses eaux est spécifique à l'agence et à
  l'usage**. Il est fixé comme **candidat**, pas automatiquement, et figé avant le test. La
  **dispersion** est la grandeur primaire ; le **déplacement du compte de jours** en est la
  grandeur dérivée.
- **Lissage, agrégation, données manquantes** : règles fixées au gel ; une absence n'est jamais
  convertie en zéro (INV-33, §3.8 des contrats).
- **Règle de début/fin d'événement** : un épisode de basses eaux est une suite **continue** de
  jours sous le seuil ; une interruption au-delà d'une durée maximale réinitialise l'épisode.
- **Regroupement en épisodes indépendants** : deux jours non consécutifs n'appartiennent jamais au
  même épisode ; la durée maximale d'une interruption est fixée au gel.
- **Incertitude et conditions d'abstention** : incertitude par observation, propagée au compte de
  jours ; **abstention** si l'harmonisation du datum n'est pas documentée pour une section.
- **Variantes autorisées dans cette famille** : listées en §G.5, avant exécution.

## E. Branche financière — FTL

**N/A.** L'expérience est `physical_discovery` et ne comporte aucune branche financière. La
justification est donnée au §B.2 : la lecture économique du Rhin est un consommateur ultérieur du
produit, jamais sa justification, et aucun marché n'est observé dans le périmètre de ce
pré-enregistrement.

## F. Confirmation par exposition

**N/A.** Aucun actif, aucune exposition financière, aucun groupe exposé n'entre dans le périmètre.
La confirmation de ce qui est affirmé est **inter-agences**, dans le §C.2, non par exposition.

## G. Rééchantillonnage et inférence

### G.1 Hypothèse nulle et unité indépendante

- H0 : la divergence résiduelle inter-agences est inférieure au seuil `δ` (§B.4).
- **Unité indépendante** : l'**épisode indépendant de basses eaux**, non le jour.
- **Structure de clustering** : les observations d'un même épisode ne sont pas indépendantes ;
  l'analyse est au niveau de l'épisode.

### G.2 Méthode

Estimation de la divergence inter-agences par section et par année d'épisodes, avec intervalle
d'incertitude. Le **HAC de Newey-West** (variance HAC, taille effective) est utilisé pour
l'incertitude des métriques agrégées, conformément à `SPEC-010:139` (« intervalles de confiance
ou bootstrap adapté à la dépendance, et taille effective »). **Aucun bootstrap n'est implémenté** :
la méthode déterministe suffit et satisfait la référence.

### G.3 Placebos et contrôles

- **Placebo de décalage** : comparer des sections **non** appariées, censées diverger.
- **Placebo de segment** : comparer la même agence à elle-même entre deux segments voisins.
- **Contrôle de convergence** : vérifier que la divergence n'est pas simplement un artefact de
  l'hydrologie amont partagée (R5) — en testant la sensibilité de la métrique au **traitement**.

### G.4 Puissance et MDE

La puissance est calculée sur le **nombre d'épisodes indépendants** disponibles dans 2016–2025,
et non sur le nombre de jours. Le seuil `δ` est choisi de sorte que l'expérience atteigne une
puissance cible fixée au gel. Si le seuil `δ` ne peut pas être atteint, le résultat est
**inconcluant**, et c'est écrit comme tel (R4).

### G.5 Multiplicité et variantes

- Toute variante — seuil, section, fenêtre, lissage, méthode d'harmonisation, découpage
  d'épisodes — est **enregistrée** avant exécution, avec le commit du code qui l'a produite
  (ADR-001, `RESEARCH-PROTOCOL.md` §5).
- La **métrique primaire** est unique : la divergence inter-agences sur le compte de jours de
  basses eaux. Toute autre métrique est **exploratoire** et déclarée comme telle.
- La correction de multiplicité s'applique à la famille de variantes autorisées ; elle est fixée
  au gel.
- `N_eff` (taille effective) est un **diagnostic** ; il ne remplace jamais `N` (protocole §5).

## H. Coûts et exécution

**N/A pour la branche financière** (aucun instrument, aucun coût d'exécution de marché). Les
coûts d'ingestion et de rétention sont traités au §C.6 et dans la fiche de source.

## I. Règles d'arrêt et données manquantes

### I.1 Conditions d'arrêt technique

- Ingestion interrompue ou incohérente sur une source primaire : le cycle est suspendu, les
  observations acquises sont conservées avec leur état, le produit n'est pas publié.
- Perte d'accès à une source primaire (migration d'API, retirement de version) : arrêt de la
  capture sur cette source, **archivage des derniers instantanés**, et inscription de l'incident.

### I.2 Conditions d'invalidation scientifique

- Un **test d'accès** tourne négatif de façon non réversible : invalidation de la partie de
  l'expérience qui en dépend, avec aménagement explicite (par exemple, perte de l'arbitrage SWOT →
  « dispersion sans arbitrage externe », qui est une dégradation **déclarée**, pas une invalidation
  de la dispersion elle-même).
- Découverte qu'une source retenue est un **remplissage a posteriori** portant un horodatage de
  publication absent : la source est reclassée en descriptif, et les reconstitution PIT la
  utilisant sont invalidées.

### I.3 Gestion des données manquantes et révisées

- Une absence reste une absence, avec son motif (`missing_reason`) : jamais un zéro, jamais une
  valeur inventée (INV-33, §3.8).
- Une révision crée une **version nouvelle** ; l'ancienne n'est jamais réécrite (INV-12, INV-13).
- Une observation dont la publication est inconnue n'est pas admise en reconstitution
  point-in-time ; elle l'est en descriptif, et le produit le déclare.

### I.4 Écarts au protocole et statut associé

Tout écart au protocole est inscrit comme **amendement append-only**, avec la mention explicite
des résultats déjà consultés. Un ajustement motivé par un résultat observé reste **exploratoire**
et ne peut jamais être décrit comme pré-enregistré (ADR-012 §4).

## J. Publication et résultats

### J.1 Métriques

- **Métrique primaire** : divergence inter-agences sur le compte de jours de basses eaux, par
  section, avec son intervalle d'incertitude.
- **Métriques secondaires, explicitement exploratoires** : déplacement du compte de jours selon
  l'agence retenue ; attribution par mécanisme ; dispersion des niveaux, des débits, des dates de
  révision et des qualifications de mesure.
- **Statuts séparés** : statistique, mécanisme, financier. **Le statut financier est vide** —
  aucune observation de marché n'est dans le périmètre.

### J.2 Rapports à produire

- Un rapport par famille d'essai, avec : versions et essais, nombre d'**épisodes indépendants**,
  métriques primaires et secondaires, dépendances, limites, résultats négatifs.
- Le rapport publie **aussi H0** s'il est le résultat, et il publie **les variantes** et leur
  famille complète.

### J.3 Divulgation des résultats négatifs

Tout essai lancé est enregistré, y compris son erreur, ses variantes négatives et son abandon
(§8 de la doctrine de preuve). Un essai invalidé n'est pas supprimé.

### J.4 Limites de généralisation

- Trois sections et trois agences ne valent pas pour un bassin. Les résultats ne se transposent
  pas à d'autres fleuves sans nouvel examen d'indépendance.
- Le décompte de jours de basses eaux est une **grandeur d'usage**, pas une grandeur physique : il
  dépend du seuil retenu, lui-même spécifique à l'agence et à l'usage.

## K. Amendements

Pour chaque amendement, enregistrer : date, auteur, motif, contenu avant/après, **résultats déjà
consultés ou non**, impact sur la confirmativité, nouvel identifiant de trial/famille, et le lien
vers l'événement append-only correspondant. Aucun amendement ne détruit une version antérieure.

## V1.6 — Provenance et décisions

- `evidence_origin` : `retrospective_reconstruction` (1990–2025) et `prospective_capture` (cycle
  hebdomadaire).
- Replay mode et preuves de disponibilité historique : **descriptif rétrospectif** tant que les
  instantanés d'agence ne sont pas archivés ; **replay opérationnel** pour le cycle prospectif.
- `physical_event_usable_at` : par observation, dérivé selon `docs/CONTRATS_FONDAMENTAUX.md` §3.2
  et §3.10 ; l'instanciation par source est une condition de gel (§A.4.2).
- `decision_published_at` : **N/A** — aucune décision publique administrative n'est dans le
  périmètre de cette expérience ; le Rhin et ses usages ne sont pas l'objet d'une décision
  datée que l'on cherche à dater ici.
- `witness_published_at` : le juge inter-agences publie selon son propre cycle ; sa périodicité
  est consignée par source et fait partie de la fiche de source.
- Deltas descriptifs et incertitude de datation : l'écart entre la publication par une agence et
  la reconstruction harmonisée est une **métrique descriptive distincte**, jamais qualifiée de
  retard cognitif (protocole §9).
- **Confirmation que l'essai n'affecte pas une fenêtre prospective scellée** : oui. Borée H3 reste
  hors périmètre, inchangé, et aucun de ses protocoles n'est consulté ni modifié ici.

## Sources consultées pour ce pré-enregistrement

- `C:\Users\Romain\Documents\TORNE_Recherche_2026-10-31\FLEET-B_Experiences-scientifiques-candidats.md`
  — revue transversale, sept candidats, vérifications HTTP du 31 octobre 2026.
- Paquet de référence V2.0, en lecture seule : `protocol/RESEARCH-PROTOCOL.md`,
  `protocol/PREREGISTRATION-TEMPLATE.md`, `protocol/PREREG_PHYSIQUE.md`,
  `specifications/SPEC-003`, `specifications/SPEC-010`, `adrs/ADR-001`, `adrs/ADR-012`,
  `adrs/ADR-014`, `adrs/ADR-023`, `docs/10-VALIDATION-DOCTRINE.md`.
- Dépôt TORNE : `docs/CONTRATS_FONDAMENTAUX.md`, `docs/RESEARCH_AND_VALIDATION.md`,
  `docs/SLICE-PREMIER.md`.
