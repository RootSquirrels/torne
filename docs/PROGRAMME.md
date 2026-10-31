# TORNE — Programme d'ingénierie

**Version : 1.0 — 31 octobre 2026**
Adapté du cahier des charges remis par le propriétaire. Ce document fixe les **gates** et la répartition du travail ;
il ne décrit pas le code, il dit ce qui doit être vrai avant d'écrire quoi que ce soit.

## Principes non négociables

1. La complexité scientifique est acceptable. La complexité organisationnelle injustifiée ne l'est pas.
2. Une fonction n'a pas besoin de devenir un service.
3. Une abstraction doit résoudre un problème concret.
4. Ne jamais confondre documentation, implémentation et validation.
5. Les données brutes et leurs preuves ne doivent jamais être écrasées silencieusement.
6. Toute reconstruction historique doit respecter les informations effectivement disponibles à la date considérée.
7. **Borée H3 reste un observatoire historique scellé.** Ne jamais modifier son protocole, son module temporel ou ses
   règles.
8. Athanor, C.R.I.N. et l'ancien BORÉE restent des sources candidates. Aucun dépôt historique ne doit être modifié.
9. **Une information inconnue reste inconnue.** Ne jamais combler une métadonnée manquante par une supposition, et
   ne jamais remplacer une observation absente par zéro.

## États des dépôts historiques au 31 octobre 2026

| Dépôt | État | Commit | Licence |
|---|---|---|---|
| `athanor` | intact, 0 fichier modifié | `6dacc87` | dépôt privé du propriétaire : réutilisable sans réserve |
| `SquirrelBetting` | intact, 0 fichier modifié | `015d263` | dépôt privé du propriétaire |
| `boree` | protocole scellé, non modifié | `4b6d130` | dépôt privé du propriétaire |

Le point de licence qui avait été ouvert sur Athanor est **close** : le code est à toi, la reprise est un acte de
réécriture interne, et la seule exigence est la **traçabilité** — chaque brique reprise laisse une trace de son
origine dans `docs/DECISIONS.md`.

## Chaque mission se termine par

- Les modifications apportées.
- Les tests exécutés et leurs résultats.
- Les décisions prises.
- Les limitations constatées.
- Les tâches non réalisées.
- Le commit associé.

**Ne jamais déclarer une mission validée sans preuves.** Une commande exécutée et son résultat valent mieux qu'un
raisonnement juste.

## Gates

| Gate | Condition de passage |
|---|---|
| **P0** | `uv sync --locked`, `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .` et `uv build` passent sur un environnement propre, et le verrou est versionné. **Aucune phase de développement métier ne commence avant.** |
| **P1** | Les sources réellement disponibles sont connues, qualifiées et datées. **Aucune conception générique de stockage ou de connecteur ne s'impose avant.** |
| **P2** | Les contrats d'objets et de temporalité sont écrits, testés, et le point de vue à la décision est implémenté. |
| **P3** | *Remplacé le 31 octobre 2026 par la séquence S2→S5 ci-dessous.* Le pré-enregistrement d'une expérience ne peut précéder la capacité à observer le domaine qui la rendrait possible. |

## Répartition

Les phases P0 et P1 sont **indépendantes** et se déroulent en parallèle : P0 est de l'outillage de build, P1 est de
la recherche de données. P2 dépend de P1 et se décompose :

- **P2-A — maintenant, en parallèle** : le modèle d'objets et la sémantique temporelle, écrits comme **contrats et
  décisions**. Ni schéma de stockage, ni connecteur, ni table : tout ce qui dépend d'une source précise reste un
  point ouvert, et le gate P1 interdit de le devancer.
- **P2-B — après P1** : l'implémentation des contrats, avec les règles par source.

---

# P0 — Socle d'ingénierie

**Rôle :** Principal Python Engineer / Build & Release Engineer.
**Objectif :** transformer le bootstrap documentaire en repository Python réellement reproductible et vérifiable.

Ce n'est pas encore le métier scientifique.

## Contenu

1. **Audit préalable** : `pyproject.toml`, `uv.lock` (s'il existe), `.gitignore`, `src/torne/`, `tests/`, `README.md`,
   workflow CI existant, documents architecturaux. Vérifier HEAD, branches et état Git — le commit de référence est
   `7153a29`, mais il faut le confirmer par inspection.
2. **Environnement** : version de Python principale explicitement choisie et justifiée ; `uv` pour l'environnement et
   le verrou ; `pytest` ; `ruff` ; installation propre depuis `src/`. Générer et versionner `uv.lock`. Vérifier qu'une
   installation depuis un environnement propre fonctionne avec le verrou.
3. **Qualité** : `uv sync --locked`, `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .`,
   `uv build`. Corriger les erreurs réelles. **Ne pas fabriquer du code pour faire passer un test.**
4. **CI** : workflow minimal. Le dépôt est hébergé sur `github.com/RootSquirrels/torne` — la CI qui s'exécute est donc
   GitHub Actions. En revanche, l'infrastructure de référence du propriétaire est en **Gitea Actions**
   (`boree/.gitea/workflows/ci.yml`) : s'inspirer de sa structure (version d'`uv` épinglée, `--locked`, ruff, pytest)
   sans recopier ses secrets ni la partie « application ». Le workflow doit : installer la version Python retenue,
   installer `uv`, synchroniser depuis le verrou, exécuter ruff, exécuter pytest, vérifier la construction du
   paquet. Pas de matrice de versions Python. Pas de seuil de couverture artificiel.
5. **Hygiène** : absence de secrets, de données expérimentales, d'artefacts Python, de dépendances inutilisées ;
   cohérence du nom de package `torne`. **Ne pas ajouter de LICENSE** : la politique de propriété
   intellectuelle est gérée séparément, par le propriétaire. *(Correction du 31 octobre 2026 : le dépôt
   `github.com/RootSquirrels/torne` est en réalité **public** — l'API GitHub renvoie `private: false` ; la
   justification « le dépôt est privé » était fausse. Le point licence redevient donc une décision ouverte,
   il n'est pas tranché ici.)*
6. **README** : mettre à jour avec les commandes **réellement opérationnelles**, et dire plainly ce qui n'a pas pu
   être vérifié.

## Environnement de construction

`uv` est installé : `%APPDATA%\Python\Python314\Scripts\uv.exe` (version 0.13.6). Il n'est pas dans le `PATH` — l'appeler
en chemin absolu, ou l'ajouter au `PATH` de la commande. Python système : 3.14.3.

# P1 — Intelligence des sources de données du Mississippi

**Rôle :** Senior Hydrological Data Scientist / Data Acquisition Architect.
**Objectif :** établir l'inventaire scientifique et technique des sources qui permettront de reconstruire les états
hydrologiques et opérationnels du Mississippi et d'étudier leurs conséquences sur le transport fluvial.

Mission de **recherche et de qualification de données**. Ne pas construire les connecteurs de production.

## Périmètre

1. **USDA — taux de fret** (`https://agtransport.usda.gov/Barge/Downbound-Grain-Barge-Rates/deqi-uken`) : historique,
   fréquence réelle, sept zones géographiques, schéma des colonnes, unités et convention tarifaire, définition de la
   date d'observation, données absentes, révisions, métadonnées de publication, API OData, pagination et limites,
   conditions d'utilisation et attribution.
   - Les tarifs sont en **pourcentage du barème de 1976**, chaque zone ayant son propre barème : la conversion en
     dollars par tonne exige le bon barème géographique.
   - Ne jamais considérer une observation manquante comme une valeur zéro.
   - Ne pas confondre date de publication, date de collecte et date de fin de semaine.
2. **USDA / USACE — mouvements par écluses** (`https://www.ams.usda.gov/services/transportation-analysis/gtr-datasets`,
   notamment Table 10) : source USACE, écluses disponibles, catégories de marchandises, profondeur historique,
   fréquence, changements méthodologiques, téléchargement automatisé, API, métadonnées de provenance. Examiner aussi
   `https://ndc.ops.usace.army.mil/ords/r/lpms/corps-locks/home`.
   - L'API opérationnelle USACE et les fichiers historiques hebdomadaires publiés par USDA **ne sont pas deux accès
     équivalents** : déterminer exactement ce que chaque canal permet.
3. **USGS — hydrologie** (`https://api.waterdata.usgs.gov/`, documentation `https://api.waterdata.usgs.gov/docs/`) :
   stations pertinentes du Mississippi, stage, streamflow, débit moyen quotidien, mesures continues, stations amont
   et aval, métadonnées de station, références verticales et datums, unités, statut provisional / approved,
   historique, interruptions, changements d'instruments, révisions, horodatage et fuseaux.
   - **Ne pas utiliser les anciennes API WaterServices comme socle** : leur décommissionnement est annoncé pour le
     premier trimestre 2027.
   - Vérifier les paramètres réellement disponibles à chaque station au lieu de supposer que toutes les stations
     possèdent les mêmes séries.
4. **Autres sources, si et seulement si elles apportent une information supplémentaire** : fermetures d'écluses,
   restrictions de navigation, conditions de tirant d'eau, précipitations et météo, niveaux des réservoirs amont,
   trafic et congestion. Évaluer USACE et NOAA quand c'est pertinent. **Ne pas multiplier les sources pour gonfler le
   volume de données.**

## Dimensions à documenter pour chaque source

Temporalité · Disponibilité (quand la donnée devient-elle publiquement accessible) · Acquisition (quand TORNE peut
réellement la récupérer) · Qualité (provisoire, approuvée ou estimée) · Révision (corrigibility rétroactive) ·
Géographie · Unité · Provenance (source primaire) · Licence (usage autorisé) · Fiabilité (fréquence des
interruptions).

**Ne jamais inventer les métadonnées manquantes.**

## Livrable

`docs/MISSISSIPPI_DATA_SOURCES.md`, en dix parties : cartographie des sources, fiches techniques, schémas réels, état
de chaque API, qualité historique, conditions de conservation et de réutilisation, sources retenues, sources écartées,
risques et limitations, proposition du **jeu de données minimal** nécessaire au premier slice.

Aucun code de production.

# P2-A — Modèle d'objets et temporalité (conception)

**Rôle :** Principal Data Architect, spécialiste des systèmes scientifiques, de la provenance et de la
reconstruction temporelle.
**Objectif :** définir les contrats qui permettront à TORNE de conserver, interpréter et reconstruire des
connaissances à partir de données hétérogènes.

Cette étape ne commence pas l'implémentation : elle fixe les **responsabilités et les invariants**. Le gate P1
interdit d'imposer ici une conception de stockage ou de connecteur.

## Les cinq objets

**Source** — l'origine d'une information : institution, jeu de données, point d'accès, document ou système.
**Raw Evidence** — le contenu brut effectivement récupéré.
**Observation** — une mesure ou une information telle que fournie par sa source.
**Derived Variable** — une valeur calculée ou estimée à partir d'une ou plusieurs observations.
**Knowledge Product** — un résultat structuré et versionné, produit par un modèle ou une reconstruction.

**Ne pas transformer ces cinq concepts en cinq services.** Définir les responsabilités et les contrats nécessaires.

## Les trois dimensions temporelles

**VALID_TIME** — quand le phénomène physique existe, ou quand le fait décrit est vrai.
**KNOWN_AT** — quand l'information devient connue ou disponible dans sa source.
**INGESTED_AT** — quand TORNE l'acquiert effectivement.

Ne jamais confondre : une mesure du 15 octobre, une publication du 18 octobre, une acquisition du 21 octobre, une
correction rétroactive du 25 octobre. Si la source ne permet pas de connaître la date de publication initiale, **ne
pas l'inventer**.

## Points particuliers à traiter

Instants, dates civiles, intervalles, séries temporelles, fuseaux horaires, précision variable, observations révisées,
informations provisoires, informations absentes.

## Livrable

`docs/CONTRATS_FONDAMENTAUX.md` : les cinq objets et leurs responsabilités, les trois dimensions temporelles et leurs
règles, le traitement des révisions et des statuts provisoires, la règle « absent ≠ zéro », les invariants vérifiables,
et la liste explicite des points qui dépendent d'une source précise — donc différés au gate P1.

Aucun schéma de stockage. Aucun connecteur. Aucune table.

# S2 → S5 — La séquence du programme

**Réordonnancement du 31 octobre 2026, décidé par le propriétaire.**

## 1. Ce qui a été corrigé

Le programme précédant enchaînait : *trouver une question scientifique → rechercher les données qui
permettent d'y répondre → construire le système autour de cette expérience*. C'est la séquence de la
démarche **confirmatoire** : hypothèse précise, variables et seuils fixés, protocole pré-enregistré,
puis tests.

Elle a une contrepartie qui manquait : la démarche **exploratoire** — collecter des observations,
comprendre les sources, examiner les relations, découvrir des régularités, des lacunes et des
phénomènes potentiellement intéressants. Un pré-enregistrement n'est pas inutile : il est
indispensable avant l'analyse confirmatoire. Mais il ne doit pas empêcher l'exploration préalable des
données, et il n'a pas à la précéder.

Le risque n'était pas théorique : pré-enregistrer une expérience précise avant d'avoir un système
d'acquisition opérationnel et des sources réelles intégrées revenait à laisser les contraintes d'une
seule expérience déterminer prématurément toute l'architecture de la plateforme.

**La séquence devient :** construire une capacité d'observation du monde → acquérir et comprendre des
sources hétérogènes → reconstruire des états physiques → découvrir les connaissances que ces
reconstructions rendent possibles → formuler et tester des hypothèses.

Cela ne signifie pas que l'acquisition est le but. L'acquisition n'est que la première étape. Le cœur
de la plateforme reste la transformation de données disparates en connaissances physiques nouvelles.

## 2. Trois niveaux, et ce qui les sépare

| Niveau | Responsabilité | Ne sait pas |
|---|---|---|
| **Socle transversal** | récupérer (API, fichiers, flux, catalogues), gérer pagination et authentification, conserver les réponses brutes, leurs empreintes, les paramètres d'acquisition, les dates, les versions et les erreurs | ce que les données signifient |
| **Couche sémantique** | comprendre ce qui a été collecté : objets, unités, référentiels, relations — les contrats restent communs, chaque domaine définit les siens | comment interroger un fournisseur |
| **Couche scientifique** | transformer les observations en connaissances : reconstructions, estimations, états latents, détection de régimes, relations physiques, simulations, incertitudes, validation indépendante | comment le réseau a été interrogé |

**Un adaptateur de source ne doit pas savoir reconstruire un état physique. Un modèle physique ne doit
pas savoir interroger l'API d'un fournisseur particulier.** Les deux fonctionnent ensemble par des
contrats explicites, et par rien d'autre.

Ce que cela interdit : cinquante connecteurs abstraits construits à l'avance, et une usine à gaz de
framework. Ce que cela impose : un socle générique, puis **quelques intégrations concrètes
représentatives**, choisies pour leur diversité — assez pour découvrir les vrais besoins, pas plus.

## 3. Les quatre sprints

### Sprint 2 — Acquisition Foundation

**Objectif :** TORNE sait réellement acquérir et conserver des informations du monde physique.

Construire la capacité transversale de récupération et de conservation des sources, et implémenter les
premières intégrations réelles, avec des données brutes, des métadonnées et une provenance
irréprochable.

*Portée :* le socle transversal (transport, pagination, authentification, conservation, empreintes,
journal d'acquisition) ; quelques adaptateurs de source concrets ; une démonstration d'acquisition
réelle, pas simulée.
*Hors portée :* l'interprétation des données, les objets de domaine, tout modèle physique.

### Sprint 3 — Physical Data Observatory

**Objectif :** pouvoir regarder le monde à travers les données réellement disponibles, et comprendre ce
que l'on sait et ce que l'on ignore.

Constituer une première collection de sources physiques et en explorer les couvertures temporelles et
spatiales, les qualités, les révisions, les recouvrements et les relations entre observations.

*Ce que ce sprint produit :* un inventaire, des fiches de sources avec leur statut de publication
(établie / bornée / inconnue, `docs/CONTRATS_FONDAMENTAUX.md` §3.11), la carte de ce qui est
reconstituable et de ce qui ne l'est pas, et les **questions scientifiques que ces données rendent
possibles** — découvertes à partir de ce qu'on observe, pas imposées d'avance.

### Sprint 4 — Domain Intelligence Foundation

**Objectif :** passer de données brutes à des représentations physiques cohérentes et réutilisables.

Construire les premières représentations sémantiques et méthodes de reconstruction d'un domaine
physique, et **les tester sur plusieurs systèmes comparables**, pas sur un seul actif.

*Principe de transférabilité :* il ne s'agit pas de construire un modèle d'un fleuve pour le recopier
sur d'autres, mais de construire un socle hydrologique réutilisable et des instanciations propres à
chaque système fluvial. Un modèle ajusté sur un fleuve doit être évalué sur d'autres sans supposer que
ses paramètres restent valides ; la preuve la plus nette est un ajustement sur plusieurs fleuves puis
un test sur un bassin **entièrement laissé de côté**. C'est la différence entre réutiliser du code et
démontrer une capacité scientifique générale.

### Sprint 5 — Scientific Discovery & First Knowledge Products

**Objectif :** produire une première connaissance nouvelle, vérifiable et publiable sous forme de
Knowledge Product.

Identifier plusieurs questions intéressantes **à partir de ce que TORNE sait réellement observer**,
sélectionner les plus prometteuses, pré-enregistrer les expériences, construire les premiers modèles et
évaluer les résultats indépendamment.

*C'est ici, et seulement ici, que le pré-enregistrement prend sa valeur complète : il est écrit avant
l'analyse confirmatoire, et il n'a pas empêché l'exploration qui l'a rendu possible.*

## 4. Ce qui reste vrai de la proposition antérieure

`TORNE-EXP-001` — cohérence inter-agences de l'état hydrologique du Rhin — **n'est pas abandonnée** :
elle passe en **piste de recherche documentée**, statut `planned`. Son pré-enregistrement
(`docs/PRE-ENREGISTREMENT-001.md`) est conservé tel quel, avec ses inconnues nommées.

Ce n'est plus l'expérience fondatrice de TORNE pour l'instant : c'est une **hypothèse documentée** que
l'observatoire des sources pourra confirmer, nuancer ou infirmer. Un pré-enregistrement écrit à l'avance
et jamais consulté n'a rien prouvé ; un pré-enregistrement consulté après exploration reste
pré-enregistré, et c'est ce qui lui vaut.

## 5. Règles, inchangées

- **Aucun juge dépendant.** Un produit public qui fournit déjà la grandeur cible est une référence ou un
  juge, jamais la découverte ; un témoin qui dérive du mécanisme qu'il doit confirmer est proscrit.
- **Les inconnues sont nommées, pas comblées.** Une source injoignable est *inconnue*, pas
  *indisponible* ; un champ non applicable porte `N/A` avec justification.
- **Une absence reste une absence**, de la donnée au rapport.
- **Aucun résultat confirmatoire sans pré-enregistrement gelé** (ADR-012 §8.1).
- **Chaque sprint est guidé par une vision scientifique générale.** Ne pas attendre la fin de la
  séquence pour réfléchir : ce qui est différé, c'est l'*hypothèse précise*, pas la pensée.

## 6. Ce qui est livré au 31 octobre 2026

P0, P1 et P2 sont passés. Le socle d'acquisition (Sprint 2) est **commencé** : les contrats du socle
transversal sont écrits et testés, et le transport, le fetcher et la conservation des preuves brutes
sont implémentés. Les adaptateurs de source concrets et la démonstration d'acquisition réelle font
partie du même sprint et sont en cours.

Aucun résultat scientifique n'est produit. Aucune performance sur le monde réel n'est démontrée. Le
dépôt n'a toujours pas d'observation réelle : il a maintenant la capacité d'en obtenir.
