# TORNE — Premier vertical slice

**Piste de recherche documentée — 31 octobre 2026**
**Statut : `planned`. Ce n'est pas l'expérience fondatrice de TORNE pour l'instant.**
**Le programme a été réordonné le 31 octobre 2026 : la capacité à observer un domaine physique
vient avant le choix d'une expérience. Voir `docs/PROGRAMME.md`, séquence S2→S5.**

## 1. Ce que ce document est, et ce qu'il n'est plus

Ce document ne **propose plus** un premier vertical slice : il **conserve** une piste de recherche
argumentée, son pré-enregistrement, et le raisonnement qui l'a produite. Rien n'est jeté : la
réorganisation a déplacé le moment où l'on fixe l'hypothèse, pas la qualité de ce qui a été pensé.

La distinction qui governera désormais le programme :

- **démarche exploratoire** — collecter, comprendre les sources, examiner les relations, découvrir des
  régularités et des lacunes ;
- **démarche confirmatoire** — hypothèse précise, variables et seuils fixés, protocole pré-enregistré,
  puis tests.

Un pré-enregistrement est indispensable avant l'analyse confirmatoire. Il **ne doit pas empêcher
l'exploration préalable des données**, et il n'a pas à la précéder. `docs/PRE-ENREGISTREMENT-001.md`
est donc conservé tel quel, statut `planned`, avec ses inconnues nommées.

## 2. Ce que la revue transversale a permis d'établir

Sept candidats d'expérience sur six domaines ont été comparés sur douze critères, avec trois portes
dures qui éliminent et ne se pondèrent pas :

- **T1 — Latent, pas tabulé.** La cible est-elle une grandeur qu'**aucun éditeur ne publie
  directement**, mais qui est déterminée par des observations publiques ? Si oui, le candidat est une
  expérience ; sinon c'est un tableau de bord. Un produit public qui fournit déjà la grandeur cible est
  une **référence** ou un **juge**, jamais la découverte.
- **T2 — Un juge véritablement indépendant.** Un juge qui partage le réseau de mesure, le forçage, le
  modèle, le post-traitement, la géographie ou la période du candidat n'est pas une confirmation
  (ADR-014, ADR-023, SPEC-003 §10).
- **Identifiabilité.** La question est-elle répondable avec les sources disponibles, et qu'est-ce qui
  rendrait le résultat infalsifiable ?

### 2.1 Pourquoi l'ancienne proposition Mississippi a été retirée

La proposition du 31 octobre 2026, fondée sur le critère MISSISSIPPI/RHIN — un témoin économique
public à fréquence infra-mensuelle — **ne survit pas à ce test** :

| Élément | Verdict |
|---|---|
| **Fermetures d'écluses USACE** comme fait physique | **Échec T1.** Les heures de fermeture sont *directement publiées*. Ce n'est pas un latent : c'est un produit public, donc une référence. |
| **Taux de fret hebdomadaire USDA/AMS** comme témoin économique | **Échec T2.** Ce sont des moyennes hebdomadaires *d'État* d'un marché du transport fluvial — le même marché que le produit explique. |
| **Décalage entre contrainte physique et témoin économique** comme métrique | Devient infaisable : le témoin est à la fois la référence et la mesure. |

Le critère MISSISSIPPI/RHIN n'est pas supprimé : il devient un **coût du terrain**, plus le critère de
sélection d'une expérience. Ce n'est pas le bassin qui était disqualifié, c'est son juge.

### 2.2 Le piège du domaine, et comment il est évité

Dans ce domaine, **la prévision publique est le juge, et non la découverte**. GloFAS et EFAS sont un
couple de la même famille de modèles (LISFLOOD) : ils ne se valident pas mutuellement. Toute
reconstitution hydrologique doit s'appuyer sur un produit publié comme **référence**, jamais le prendre
pour un juge.

## 3. La piste `TORNE-EXP-001`

> **Quelle est l'amplitude de la divergence entre les reconstructions hydrométriques française,
> allemande et néerlandaise de l'état du Rhin, et à quel point cette divergence déplace-t-elle le
> nombre de jours de basses eaux ?**

- **Nature de l'affirmation** : reconstruction et explication. Ni prédiction, ni causalité, ni
  performance financière.
- **Ce qu'elle démontre, honnêtement** : principalement une **capacité de réconciliation et d'audit
  des systèmes de mesure**. C'est une valeur réelle — un compte de jours de basses eaux cité comme un
  nombre unique repose sur des systèmes qui ne sont peut-être pas d'accord — mais c'est une capacité
  d'audit, pas une découverte physique.
- **Ce qui la fragilise** : le nombre de jours de basses eaux reste une **grandeur dérivée dépendante
  d'un seuil opérationnel**. Ce n'est pas une propriété physique universelle du fleuve.

C'est pourquoi cette piste est conservée comme hypothèse documentée, et non comme point de départ
fondateur : elle est plus facile à confirmer qu'à découvrir.

## 4. L'ambition qui la remplace — une représentation de l'état hydrologique

Construire **progressivement** une véritable représentation de l'état hydrologique d'un système fluvial.
Quatre couches, par ordre de dépendance :

| Couche | Contenu |
|---|---|
| **État hydrométrique** | niveaux, débits, vitesses, incertitudes, observations manquantes, reconstruction de l'état du cours d'eau |
| **Dynamique du réseau fluvial** | propagation des variations de débit, relations amont-aval, apports des affluents, temps de transfert, régimes |
| **État physique spatial** | extension des zones inondées, largeur du cours d'eau, évolution des surfaces en eau, observations satellitaires |
| **Régimes et événements** | crues, étiages, ruptures de régime, anomalies, saisonnalité, évolution des états hydrologiques |

Là se construit quelque chose de plus puissant qu'une étude sur la divergence entre trois agences : un
domaine physique dont TORNE reconstruit progressivement différents aspects — et, à partir de ce qu'il
sait réellement observer, les phénomènes précis qui méritent d'être étudiés.

## 5. Comment rendre cette capacité réutilisable sur d'autres fleuves

C'est le point le plus important. Il ne faut **pas** construire un modèle du Rhin que l'on recopierait
sur le Rhône, la Seine ou le Mississippi : il faut construire un **socle hydrologique réutilisable**, puis
des **instanciations propres à chaque système fluvial**.

| Niveau | Commun à plusieurs fleuves | Spécifique à chaque fleuve |
|---|---|---|
| **Acquisition** | API, fichiers, archives, captures | Sources et fournisseurs |
| **Objets** | Stations, mesures, séries temporelles | Identifiants et localisation |
| **Sémantique** | Unités, temporalité, qualité | Datums, conventions, courbes de tarage |
| **Géographie** | Réseau fluvial, relations amont-aval | Géométrie et topologie locale |
| **Méthodes** | Estimation d'état, détection d'anomalies, propagation d'incertitude | Paramètres et calibration |
| **Connaissance** | Débits reconstruits, événements, régimes | Résultats et incertitudes propres au bassin |

La **transférabilité doit être testée** : un modèle ajusté sur un fleuve doit être évalué sur d'autres,
sans supposer que ses paramètres restent valides. La preuve la plus nette est un ajustement ou un
calibrage sur **plusieurs fleuves**, puis un test sur un bassin **entièrement laissé de côté**. C'est la
différence essentielle entre **réutiliser du code** et **démontrer une capacité scientifique générale** —
et c'est un test que le dépôt n'a pas encore passé.

## 6. Ce qui reste vrai de la proposition antérieure

- **Le Rhin est le meilleur terrain d'intégration technique du paquet de référence** : sources
  publiques, plusieurs décennies d'historique, références indépendantes. C'est un constat de
  faisabilité, plus un motif de sélection.
- **Le Rhin reste le bon terrain pour les adjudications** — les releases de l'EWL sont le contre-exemple
  documenté d'une décision dont la justification est elle-même un enjeu.
- **La qualification des sources du Mississippi (P1, `docs/MISSISSIPPI_DATA_SOURCES.md`) reste
  valable** : six sources vérifiées, fenêtre commune 2004–2026, pièges d'identification relevés,
  décalages de publication structurels. Ce travail devient un **coût de terrain** et non un critère, et
  son juge indépendant n'est plus disponible.
- **Le Rhin n'a pas de témoin économique public infra-mensuel** : cela reste vrai, et cela devient un
  argument *pour* la première capacité, qui ne porte pas de témoin économique.

## 7. Ce qui est requis avant que cette piste redevienne une expérience

1. **Un socle d'acquisition opérationnel**, et des sources réelles intégrées — c'est le Sprint 2 en cours.
2. **L'observatoire des sources** : ce que les données permettent réellement de reconstruire, et où
   elles sont lacunaires — Sprint 3.
3. **Les tests d'accès** : une source néerlandaise du Rhin (inconnue depuis ce poste) et la jointure
   satellitaire aux sections.
4. **La classe effective de chaque source** (établie / bornée / inconnue), établie par vérification et
   non par supposition (`docs/CONTRATS_FONDAMENTAUX.md` §3.11).
5. **Une revue d'art antérieur** sur la dispersion inter-agences : les affirmations « personne ne
   publie cela » sont inférées, pas établies par une revue systématique de la littérature.
6. **Le pré-enregistrement gelé**, et seulement alors l'analyse confirmatoire.

## 8. Ce qui est demandé au propriétaire

| Décision | Recommandation | Caractère |
|---|---|---|
| Maintenir `TORNE-EXP-001` en **piste de recherche documentée**, statut `planned` | **Oui** — le travail est conservé, le moment du gel est décalé | Décision du propriétaire, **prise** le 31 octobre 2026 |
| Accepter la correction de la latence `available_transport_capacity` de SPEC-003 §131, non identifiable depuis des sources publiques | **Oui**, en la documentant comme correction du paquet de référence | Décision du propriétaire : c'est le paquet de référence, pas le dépôt |
| Adopter la séquence S2→S5 | **Oui** | Décision du propriétaire, **prise** le 31 octobre 2026 |

**Ce n'est pas une décision du propriétaire** : le critère de sélection (T1/T2), le rejet du juge de la
proposition Mississippi, et l'adoption des quatre couches hydrologiques comme ambition. Ce sont des
corrections de fond, décidées ici, motivées et réversibles.

## 9. Sources citées

- Revue transversale des candidats d'expérience, sept candidats sur six domaines, douze critères,
  vérifications HTTP du 31 octobre 2026 — dossier de recherche hors dépôt :
  `C:\Users\Romain\Documents\TORNE_Recherche_2026-10-31\FLEET-B_Experiences-scientifiques-candidats.md`
  et sa synthèse `00-SYNTHESE-ET-DECISIONS.md`.
- Paquet de référence V2.0, en lecture seule : `specifications/SPEC-003` (§10 jugement, ligne 131
  latence, ligne 54 segments de station), `specifications/SPEC-004`, `adrs/ADR-012`, `adrs/ADR-014`,
  `adrs/ADR-023`, `protocol/RESEARCH-PROTOCOL.md`, `protocol/PREREG_PHYSIQUE.md`,
  `protocol/PREREGISTRATION-TEMPLATE.md`, `docs/10-VALIDATION-DOCTRINE.md`.
- Sources publiques citées et leur statut de vérification au 31 octobre 2026 : §C.1 du
  pré-enregistrement.
