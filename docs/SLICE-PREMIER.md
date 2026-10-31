# TORNE — Premier vertical slice

**Proposition — 31 octobre 2026**
**Statut : recommandation argumentée. Elle attend la décision du propriétaire.**
**Ce document remplace la proposition du même jour fondée sur le critère MISSISSIPPI/RHIN : cette
proposition ne survit pas au test de sélection appliqué ci-dessous. Le raisonnement antérieur est
conservé en §9, pour que le changement de critère soit traçable.**

## 1. Ce qui a changé : le critère de sélection

La proposition précédente choisissait un bassin par un critère de **témoin économique** : un terrain
où la conséquence économique de la donnée physique est mesurée publiquement, à fréquence
infra-mensuelle. Ce critère est **relativisé**. Il ne disparaît pas — il devient une question de
coût du terrain, non le critère de sélection d'une expérience.

Le critère de sélection est désormais celui du **paquet de référence V2.0**, qu'une revue
transversale de sept candidats sur six domaines a appliqué et vérifié :

- **T1 — Latent, pas tabulé.** La cible est-elle une grandeur que **aucun éditeur ne publie
  directement**, mais qui est déterminée par des observations publiques ? Si la variable cible
  apparaît telle quelle dans un flux public, le candidat n'est pas une expérience : c'est un
  tableau de bord. Un produit public qui fournit déjà la quantité cible est une **référence** ou un
  **juge**, jamais la découverte.
- **T2 — Un juge véritablement indépendant.** Un juge qui partage le réseau de mesure, le
  forçage, le modèle, le post-traitement, la géographie ou la période du candidat n'est pas une
  confirmation (ADR-014, ADR-023, SPEC-003 §10).
- **Identifiabilité.** La question est-elle répondable avec les sources disponibles, et qu'est-ce
  qui rendrait le résultat infalsifiable ? Une question que presque n'importe quel choix de modèle
  peut reproduire n'est pas une expérience.

Ces trois portes sont dures : elles éliminent, elles ne se pondèrent pas. Le classement final
porte sur douze critères notés, mais **aucun score ne rachète l'échec à T1 ou T2**.

## 2. La proposition précédente échoue à T1 et à T2

Appliquons le critère à la proposition Mississippi du 31 octobre 2026, qui était la version
antérieure du présent document :

| Élément de la proposition | Verdict |
|---|---|
| **Fermetures d'écluses USACE** comme fait physique | **Échec T1.** Les heures de fermeture sont *directement publiées* par l'USACE (LPMS). Ce n'est pas un latent : c'est un produit public. Il devient une **référence**, pas la découverte. |
| **Taux de fret hebdomadaire USDA/AMS** comme témoin économique | **Échec T2.** Ce sont des moyennes hebdomadaire *d'État* d'un marché du transport fluvial — le même marché que le produit explique. Un témoin dépendant du mécanisme qu'il devrait confirmer. |
| **Décalage entre contrainte physique et témoin économique** comme métrique | Devient infaisable : le témoin est à la fois la référence et la mesure, il n'y a plus rien à comparer. |

Autrement dit : la proposition précédente mesurait un décalage entre une grandeur **déjà publiée**
et un témoin **issu du même marché**. C'est précisément le motif que la doctrine interdit de
présenter comme une confirmation.

**Cette constatation ne disqualifie pas le bassin** — elle disqualifie le **juge** qu'il proposait.
C'est une correction de fond, et c'est la raison pour laquelle la sélection est refaite.

## 3. L'expérience recommandée — Expérience 001

> **Quelle est l'amplitude de la divergence entre les reconstructions hydrométriques française,
> allemande et néerlandaise de l'état du Rhin, et à quel point cette divergence déplace-t-elle le
> nombre de jours de basses eaux — la grandeur opérationnelle sur laquelle le fret fluvial, les
> autorisations et la politique climatique du bassin sont écrits ?**

- **Identifiant** : `TORNE-EXP-001`
- **Programme de recherche** : `physical_discovery`
- **Nature de l'affirmation** : **reconstruction** et **explication** (attribution de la divergence à
  un mécanisme). Ni prédiction, ni causalité, ni performance financière.
- **État latent inféré** : (i) un **état harmonisé** de niveau et de débit du Rhin, par section,
   segmenté par vintage de station et de courbe de tarage, avec une incertitude par observation ;
   (ii) la **dispersion inter-agences** du compte de jours de basses eaux à chaque section de
   référence ; (iii) l'**attribution** de cette dispersion à un mécanisme : décalage de datum,
   révision de courbe de tarage, changement de capteur, règle d'agrégation, traitement des trous
   de réseau.
- **Pré-enregistrement** : `docs/PRE-ENREGISTREMENT-001.md` (statut `planned`).

### 3.1 Pourquoi elle passe T1

Aucune agence ne publie un **compte de jours de basses eaux harmonisé, borné en incertitude et
 comparable entre agences**. Chacune publie sa série brute, dans son référentiel, avec ses règles.
La grandeur harmonisée et sa dispersion n'existent publiquement nulle part : il faut les construire.

### 3.2 Pourquoi elle passe T2

Les réseaux de jauges de la France, de l'Allemagne et des Pays-Bas mesurent la **même vérité
physique** avec des **instruments, des datums et des chaînes de courbes de tarage distincts**.
Aucun forçage partagé, aucun modèle partagé, aucun post-traitement partagé : la géographie est
partagée — c'est inévitable et c'est déclaré — mais le reste ne l'est pas. C'est exactement la
classe d'indépendance qu'ADR-014 demande.

L'altimétrie satellitaire **SWOT** est un arbitre externe à horizon long : elle ne partage aucune
chaîne de jauges, mais elle revisite en ~21 jours. Elle arbitre donc les **tendances longues**,
pas les comptes journaliers. La conséquence est inscrite dans le protocole : l'affirmation
**primaire** est **la dispersion**, mesurable par construction entre trois réseaux, et non « quelle
agence a raison », qui n'est arbitrable qu'à long horizon.

### 3.3 Le piège du domaine, et comment il est évité

Dans ce domaine, **la prévision publique est le juge, et non la découverte**. GloFAS et EFAS sont
un couple de la même famille de modèles (LISFLOOD) : ils ne se valident pas mutuellement. Toute
reconstitution hydrologique doit donc s'appuyer sur un **produit publié comme référence**
(EFAS, GloFAS, climatologie) et jamais le prendre pour un juge.

## 4. Ce que l'expérience démontre — et ce qu'elle ne démontre pas

**Elle démontre :**

1. Une **reconstruction** d'état hydrologique harmonisé, segmentée par vintage, avec incertitude
   et lignage complet, sur au moins trois sections et sur 1990–2025.
2. Une **quantification** de la divergence inter-agences sur une grandeur opérationnelle
   réglementaire, avec son attribution par mécanisme.
3. Un **produit de connaissance versionné** exposant son propre juge, ses versions et ses
   incertitudes.

**Elle ne démontre pas, et ne doit pas prétendre :**

- **Aucune causalité** : on mesure une divergence de mesure, pas une chaîne causale.
- **Aucune performance financière** : la lecture « fret » est un consommateur, jamais la
  justification. Un prix ne doit jamais pouvoir optimiser le choix scientifique.
- **Aucun arbitrage « qui a raison »** au-delà de l'horizon SWOT.
- **Aucune identifiabilité du débit absolu** sans transformations de datum documentées.

## 5. Le coût, et ce qui peut le faire basculer

| Poste | Évaluation |
|---|---|
| Accès | Un point d'entrée ouvert vérifié (Hub'EAU v2), un réseau ouvert accessible (ELWIS), un produit satellitaire ouvert. **Friction faible.** |
| Volume | ~10⁶–10⁷ observations ponctuelles pour le corridor. **Pas de raster dans le cœur du dispositif.** |
| Modélisation | Aucun modèle physique nouveau : les primitives existent (lissage, ruptures, puissance, comparaison appariée). |
| Charge | 3 à 6 semaines à ≤ 0,5 ETP pour un prototype monobassin (Hub'EAU + ELWIS). L'arbitrage SWOT ajoute 4 à 6 semaines. **Ordre de grandeur : faible.** |

**Ce qui ferait basculer le classement.** Si la source néerlandaise demeurerait inaccessible **et**
que SWOT ne pouvait être joint aux sections, l'affirmation se dégraderait en « dispersion sans
arbitrage externe ». Ce n'est pas un échec, mais c'est une dégradation qui doit être déclarée dans
le rapport — et le candidat suivant deviendrait le premier.

## 6. Les deux tests d'accès à lever avant toute sélection définitive

Ce ne sont pas des questions de préférence, et ils ne coûtent qu'une semaine chacun :

1. **Une source néerlandaise du Rhin** (Rijkswaterstaat) : existe-t-il un flux machine-lisible
   documentant le datum et l'historique de section ? *Statut : INCONNU — injoignable depuis ce poste.
   « Injoignable ici » n'est pas « indisponible ».*
2. **Le contrat ENTSO-E courant**, pour le candidat de réserve : la base impose-t-elle un jeton,
   et les documents historiques restent-ils accessibles en masse ? *Statut : INCONNU.*

## 7. Ce qui est requis avant le premier calcul

1. **La procédure de calcul de `usable_at`** : la forme est écrite
   (`docs/CONTRATS_FONDAMENTAUX.md` §3.10) ; son **instanciation par source** reste à faire, et
   elle est la condition du démarrage. C'est le dernier blocage de fond.
2. **Les tests d'accès** du §6.
3. **Un pré-enregistrement gelé** : `docs/PRE-ENREGISTREMENT-001.md`, à l'état `preregistered`,
   avec ses seuils, son juge, sa population d'épisodes et sa condition d'arrêt — **avant** le
   premier calcul, comme l'exige ADR-012 §8.1.
4. **La liste des sources retenues et écartées**, avec pour chacune son statut de publication
   (établie / bornée / inconnue), qui décide de son caractère reconstituable ou descriptif.
5. **Le store synthétique anti-fuite** : chaque valeur encode sa date, le réalisé interdit vaut −1
   (INV-32, INV-33).
6. **Une revue de l'art antérieur** sur ce qui est publié sur la dispersion inter-agences
   hydrométriques : les affirmations « personne ne publie cela » de la revue sont **inférées**, pas
   établies par une revue systématique de la littérature. C'est le maillon faible du dossier, et il
   est peu coûteux à fermer.

## 8. Ce qui est demandé au propriétaire, et ce qui ne l'est pas

| Décision | Recommandation | Caractère |
|---|---|---|
| Retenir `TORNE-EXP-001` comme première expérience physique | **Oui**, sous les conditions du §5 | **Recommandation argumentée** — la décision reste au propriétaire |
| Accepter la correction de la latence `available_transport_capacity` de SPEC-003 §131, non identifiable depuis des sources publiques | **Oui**, en la documentant comme correction du paquet de référence et non comme réinterprétation | Décision du propriétaire : c'est le paquet de référence, pas le dépôt |
| Lancer les deux tests d'accès du §6 | **Oui**, avant toute sélection définitive | Décision technique réversible |
| Écrire l'instanciation par source de la procédure `usable_at` | **Oui** | Décision technique réversible |
| Licence du dépôt public, validation sur données réelles | **Hors périmètre** de ce document | Décision du propriétaire, déjà signalée |

**Ce n'est pas une décision du propriétaire :** le choix du critère de sélection (T1/T2), la
correction du juge de la proposition Mississippi, et l'écriture de la forme de la procédure
`usable_at`. Ce sont des corrections de fond, décidées ici, motivées et réversibles.

## 9. Ce que la proposition précédente avait raison de dire, et qui reste vrai

- **Le Rhin est le meilleur terrain d'intégration technique du paquet de référence** : sources
  publiques, plusieurs décennies d'historique, références indépendantes, modèle de référence
  physique déjà spécifié. Cela reste vrai, mais ce n'est plus le critère : c'est un constat de
  faisabilité, pas un motif de sélection.
- **Le Rhin reste le bon terrain pour les adjudications** — les releases de l'EWL sont le
  contre-exemple documenté d'une décision dont la justification est elle-même un enjeu.
- **La qualification des sources du Mississippi (P1, `docs/MISSISSIPPI_DATA_SOURCES.md`) reste
  valable** : six sources vérifiées, fenêtre commune 2004–2026, pièges d'identification relevés,
  décalages de publication structurels, question bloquante sur la moyenne des taux. Ce travail
  n'est pas perdu ; il redevient simplement un **coût de terrain** et non un critère, et il n'a
  plus de juge indépendant disponible.
- **Le Rhin n'a pas de témoin économique public infra-mensuel** : cela reste vrai, et cela
  devient un argument *pour* la première expérience, qui ne porte pas de témoin économique.

## 10. Sources citées

- Revue transversale des candidats d'expérience, sept candidats sur six domaines, douze critères,
  vérifications HTTP du 31 octobre 2026 — dossier de recherche hors dépôt :
  `C:\Users\Romain\Documents\TORNE_Recherche_2026-10-31\FLEET-B_Experiences-scientifiques-candidats.md`
  et sa synthèse `00-SYNTHESE-ET-DECISIONS.md`.
- Paquet de référence V2.0, en lecture seule : `specifications/SPEC-003` (§10 jugement, ligne 131 latence, ligne 54 segments de station),
  `specifications/SPEC-004`, `adrs/ADR-012`, `adrs/ADR-014`, `adrs/ADR-023`, `protocol/RESEARCH-PROTOCOL.md`,
  `protocol/PREREG_PHYSIQUE.md`, `protocol/PREREGISTRATION-TEMPLATE.md`, `docs/10-VALIDATION-DOCTRINE.md`.
- Sources publiques citées et leur statut de vérification au 31 octobre 2026 : §3 du pré-enregistrement.
