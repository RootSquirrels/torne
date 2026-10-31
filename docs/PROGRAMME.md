# TORNE — Programme

**Situation, objectif prioritaire, critères de sortie**
Ce document dit ce que le dépôt sait faire aujourd'hui, ce qu'il ne sait pas encore faire, et ce qui doit être
vrai pour que le prochain jalon soit atteint. Il ne raconte pas les sprints passés : ce qui a été fait se lit
dans l'historique du dépôt et dans les tests.

## 1. Principes non négociables

1. La complexité scientifique est acceptable. La complexité organisationnelle injustifiée ne l'est pas.
2. Une fonction n'a pas besoin de devenir un service.
3. Une abstraction doit résoudre un problème concret.
4. Ne jamais confondre documentation, implémentation et validation.
5. Les données brutes et leurs preuves ne doivent jamais être écrasées silencieusement.
6. Toute reconstruction historique doit respecter les informations effectivement disponibles à la date considérée.
7. **Les dépôts historiques restent intacts.** Aucun protocole, module temporel ou règle d'un dépôt scellé n'est
   modifié. Ils restent consultables comme références de recherche, et leurs briques ne sont reprises qu'après
   classement explicite (`docs/CONTRATS_FONDAMENTAUX.md` §5).
8. **Une information inconnue reste inconnue.** Ne jamais combler une métadonnée manquante par une supposition,
   et ne jamais remplacer une observation absente par zéro.
9. **Une capacité n'est pas une preuve.** Un code qui existe ne démontre rien : la preuve vient d'une exécution,
   sur des données réelles, dont le résultat est consigné.

**Chaque mission se termine par** les modifications apportées, les tests exécutés et leurs résultats, les décisions
prises, les limitations constatées, les tâches non réalisées, et le commit associé. **Ne jamais déclarer une
mission validée sans preuves** : une commande exécutée et son résultat valent mieux qu'un raisonnement juste.

## 2. Ce que le dépôt sait faire aujourd'hui

Chaque ligne a un emplacement dans le code et une suite de tests qui la contrôle. La suite complète est verte.

| Capacité | Où | Ce qu'elle garantit |
|---|---|---|
| Transport HTTP durci | `src/torne/acquisition/transport.py` | plafond de redirections appliqué, durée mesurée, URL finale consignée, identifiants retirés dès qu'une redirection change de serveur, de port ou de schéma |
| Magasin brut | `src/torne/acquisition/store.py` | contenu dédupliqué par empreinte et jamais réécrit, **événement d'acquisition** journalisé à chaque récupération, instant de première conservation |
| Fetcher | `src/torne/acquisition/fetcher.py` | pagination par curseur, par décalage et par lien d'en-tête ; épuisement qualifié par source |
| Contrat de connecteur | `src/torne/acquisition/contracts.py` | quatre contrôles — transport, structure de la réponse, conformité à la question posée, exhaustivité du parcours — et un verdict de conformité **motivé** |
| Trois adaptateurs réels | `src/torne/acquisition/adapters/` | Hub'EAU v2 (curseur), USGS NWIS (sans pagination), catalogue Copernicus Data Space (OData) |
| Objets et temporalité | `src/torne/contracts/` | les cinq objets, les trois dimensions temporelles, `usable_at` dérivé, observation absente qualifiée |
| Méthodes | `src/torne/methods/` | filtre de Kalman en espace d'état, régression et erreur-type CR1, rupture de moyenne par CUSUM, puissance et effet minimal détectable, comparaison appariée à une référence |
| Exécution | `src/torne/execution/` | configuration conservée, rejeu depuis la configuration, graine transmise et jamais d'aléa global |
| Évaluation | `src/torne/evaluation/` | découpage temporel **cumulatif**, références simples, métriques, incertitude, rapport |
| Enregistrement | `src/torne/knowledge/` | produit figé, lignée vérifiable jusqu'aux preuves brutes |

Les primitives statistiques reprises d'un dépôt d'origine sont vérifiées contre les définitions publiées
(`scipy`, `statsmodels`), pas contre une réimplémentation interne.

**Ce qui a été vérifié sur le réseau, et non simulé :** le 31 octobre 2026, les trois adaptateurs ont été
interrogés pour de vrai, et leurs réponses sont conservées comme preuves brutes, avec leurs empreintes et leur
manifeste. C'est la seule performance démontrée à ce jour : **le socle acquiert et conserve**.

**Ce qui n'est pas démontré :** aucune performance sur le monde réel. Aucune observation issue de données
réelles n'a encore été produite : le dépôt a la capacité d'en obtenir, et le moyen de les tracer.

## 3. Ce qui n'est pas fait, et pourquoi

| Ce qui manque | Pourquoi |
|---|---|
| Une couche sémantique et des objets de domaine | L'observatoire doit dire ce qu'il cherche avant que le code le fige. Le socle ne doit pas être modelé par une seule expérience. |
| Un moteur, un service, un registre, un bus | Une abstraction doit résoudre un problème concret ; aucun problème concret ne l'exige encore. |
| Un stockage distribué ou une base de données | Le magasin local fait le travail. La règle est « local d'abord, copie après » (`docs/CONTRATS_FONDAMENTAUX.md` §5.7) : une panne de la copie retarde la copie, elle ne perd rien. |
| Un framework supplémentaire | La bibliothèque standard suffit au transport ; une dépendance runtime ne s'ajoute qu'au premier import réel. |
| Une application « world-to-market » | Reportée tant que le socle d'intelligence physique n'est pas mature (`docs/ARCHITECTURE.md` §5). |

## 4. L'objectif prioritaire : l'observatoire des sources

### 4.1 La séquence

La séquence du programme n'est pas « trouver une question, puis chercher les données ». Elle est l'inverse :

> construire une capacité d'observation du monde → acquérir et comprendre des sources hétérogènes → reconstruire
> des états physiques → découvrir les connaissances que ces reconstructions rendent possibles → formuler et tester
> des hypothèses.

C'est la séquence **exploratoire** avant la séquence **confirmatoire**. Un pré-enregistrement n'est pas inutile :
il est indispensable avant l'analyse confirmatoire. Mais il ne doit pas empêcher l'exploration préalable des
données, et il n'a pas à la précéder. Le risque n'était pas théorique : pré-enregistrer une expérience précise
avant d'avoir un système d'acquisition opérationnel revenait à laisser les contraintes d'une seule expérience
déterminer prématurément toute l'architecture de la plateforme.

Cela ne signifie pas que l'acquisition est le but. L'acquisition n'est que la première étape. Le cœur de la
plateforme reste la transformation de données disparates en connaissances physiques nouvelles.

**Les trois niveaux, et ce qui les sépare** — socle transversal, couche sémantique, couche scientifique — sont
posés dans `docs/ARCHITECTURE.md` §1.1. Un adaptateur de source ne doit pas savoir reconstruire un état
physique ; un modèle physique ne doit pas savoir interroger l'API d'un fournisseur particulier.

### 4.2 Le prochain jalon

Constituer une première collection de sources physiques et en explorer les couvertures temporelles et
spatiales, les qualités, les révisions, les recouvrements et les relations entre observations.

Ce que ce jalon produit :

- un **inventaire** des sources, avec ce que chacune donne et ce qu'elle ne donne pas ;
- des **fiches de sources** portant leur statut de publication — établie, bornée, inconnue
  (`docs/CONTRATS_FONDAMENTAUX.md` §3.11) ;
- la **carte de ce qui est reconstituable** et de ce qui ne l'est pas ;
- les **questions scientifiques que ces données rendent possibles**, découvertes à partir de ce qu'on observe, pas
  imposées d'avance.

Le détail de la qualification par source est dans `docs/SOURCES.md`.

### 4.3 Critères de sortie

Le jalon est atteint quand **tout** ce qui suit est vrai, et vérifiable :

1. **Chaque source retenue a une fiche** qui porte son identité, sa couverture, son comportement observé et ses
   limites — et la fiche dit ce qui n'a pas pu être vérifié.
2. **Chaque source retenue est classée** dans une des quatre classes de publication (P, B, C, N), et la classe
   est établie **par exécution**, pas par supposition.
3. **La couverture temporelle de chaque source est mesurée** : ce qui est couvert, ce qui ne l'est pas, et ce qui
   ne le sera pas.
4. **La conformité sémantique de chaque source est établie**, avec son verdict motivé. Une source dont les
   filtres ne sont pas appliqués par le fournisseur est notée comme telle, et n'est pas traitée comme une source
   interrogeable par filtre.
5. **La carte de reconstitution est écrite**, et elle distingue ce qui est reconstituable de ce qui ne l'est pas.
6. **La liste des questions scientifiques possibles** est établie à partir de l'observation, et aucune n'est
   retenue au titre d'une intuition antérieure.
7. **Aucun point ouvert du §5 n'a été contourné** : les limites sont inscrites, pas lissées.

## 5. Les limites encore ouvertes

Ces points ne sont pas tranchables aujourd'hui, et aucun n'est une négligence.

1. **La licence du dépôt TORNE n'est pas choisie.** Le dépôt est hébergé publiquement sur GitHub ; la politique de
   propriété intellectuelle est gérée par le propriétaire, séparément. C'est une décision qui lui appartient, et
   elle n'est pas prise ici.
2. **Le registre d'unités et le référentiel spatial n'existent pas.** Aucun dépôt historique n'en apporte un :
   conservation dans les unités de la source ou conversion, et référence verticale pour les grandeurs
   hydrologiques, restent à trancher.
3. **Le statut de qualité des sources n'est pas apparié** au vocabulaire fermé des statuts
   (`docs/CONTRATS_FONDAMENTAUX.md` §3.7), et les valeurs de `missing_reason` rencontrées en vrai ne sont pas
   inventoriées.
4. **La borne conservatrice par source n'est pas choisie.** Quand la publication est inconnue, chaque source
   devrait pouvoir avoir sa propre borne, dérivée de son cycle de publication.
5. **La granularité commune entre sources n'est pas choisie.** Aligner un flux hebdomadaire sur un flux horaire
   suppose une règle d'agrégation et une convention de rattachement ; la règle d'agrégation est contractuelle, le
   choix ne l'est pas.
6. **La reconstitution de l'historique des révisions dépend de la source.** Une source qui date ses révisions le
   permet ; une source qui ne les date pas ne le permet pas, et le contrat ne peut que constater l'absence.
7. **Le déterminisme n'est vérifié que dans une exécution simple.** La CI lance `pytest -q` sans distribution ; le
   jour où la suite sera distribuée, le déterminisme sous cette configuration devra être vérifié séparément.
8. **La graine globale n'est pas journalisée dans le manifeste.** L'aléa global n'est jamais touché et la graine
   est transmise, mais elle n'est pas encore tracée dans la preuve.
9. **Le contrat de conformité a trois états, pas quatre.** Une source peut déclarer un critère demandé et le rendre
   non vérifiable : dans ce cas le verdict global reste `CONFORME`, et `NON_APPLICABLE` franchit la porte
   d'exploitabilité. La table de vérité retenue est : tous vérifiés et satisfaits → `CONFORME` ; au moins un vérifié
   et violé → `NON_CONFORME` ; aucun violé, mais au moins un critère demandé non vérifiable → **`INDETERMINATE`**, et
   l'issue ne doit alors pas être exploitable. `INDETERMINE` porte le même sens que l'axe d'applicabilité des
   Knowledge Products (`INDETERMINATE`) : la même règle, au même mot, à deux étages. Ce cas n'est pas implémenté :
   il est fermé par la piste d'acquisition, pas par la documentation.
10. **Une source peut accepter un filtre et ne pas l'appliquer.** C'est le cas mesuré de Hub'EAU `observations_tr`
    sur l'instance observée : une station inexistante rend exactement la même population qu'une station réelle.
    Le constat et sa mesure sont dans `docs/SOURCES.md` §I.1. Ce n'est pas une limite d'architecture — USGS `sites=`
    et Copernicus `$filter` appliquent bien leur filtre — mais c'est une **contrainte de source**, et elle
    conditionne le choix de la voie d'acquisition du Rhin.

## 6. Les règles qui ne changent pas

- **Aucun juge dépendant.** Un produit public qui fournit déjà la grandeur cible est une référence ou un juge,
  jamais la découverte ; un témoin qui dérive du mécanisme qu'il doit confirmer est proscrit.
- **Les inconnues sont nommées, pas comblées.** Une source injoignable est *inconnue*, pas *indisponible* ; un
  champ non applicable porte `N/A` avec justification.
- **Une absence reste une absence**, de la donnée au rapport.
- **Aucun résultat confirmatoire sans pré-enregistrement gelé.**
- **Chaque jalon est guidé par une vision scientifique générale.** Ce qui est différé, c'est l'*hypothèse précise*,
  pas la pensée.

**Les trois règles fondatrices** (`docs/RESEARCH_AND_VALIDATION.md` §12.5) :

1. **Une plateforme, plusieurs physiques.** TORNE partage son épistémologie, sa provenance, sa temporalité et ses
   procédures d'évaluation ; chaque domaine conserve sa physique, ses variables, ses juges et ses dénominateurs.
2. **L'inconnu ne devient jamais une certitude par commodité.** Un référentiel inconnu produit une abstention
   documentée, pas une comparaison approximative présentée comme valide.
3. **Une réfutation est une production de connaissance.** TORNE doit savoir publier qu'une méthode ne se transfère
   pas, sans dégrader ce qui a été correctement établi ailleurs.

## 7. La piste de recherche conservée

`TORNE-EXP-001` — cohérence inter-agences de l'état hydrologique du Rhin — **n'est pas abandonnée** : elle passe
en **piste de recherche documentée**, statut `planned`. Son pré-enregistrement
(`docs/PRE-ENREGISTREMENT-001.md`) est conservé tel quel, avec ses inconnues nommées.

Ce n'est plus l'expérience fondatrice de TORNE pour l'instant : c'est une **hypothèse documentée** que
l'observatoire des sources pourra confirmer, nuancer ou infirmer. Un pré-enregistrement écrit à l'avance et jamais
consulté n'a rien prouvé ; un pré-enregistrement consulté après exploration reste pré-enregistré, et c'est ce qui
lui vaut.
