# TORNE

**Plateforme computationnelle de connaissance du monde réel.**
Socle initial — 31 octobre 2026.

## Ce qu'est TORNE

TORNE est une plateforme de calcul scientifique appliquée au monde réel. Elle doit transformer des
informations hétérogènes, principalement publiques, en représentations, estimations, prévisions,
mécanismes et conséquences économiques documentés, que plusieurs applications peuvent consommer.

Le nom vient du fleuve Torne, qui sépare la Finlande de la Suède : le fleuve constituait un axe
important pour le commerce, le transport et les activités locales, et connaître la date de sa
débâcle était une information concrètement utile. Au fil des siècles, cette observation physique
est devenue une archive climatique exploitable scientifiquement : du phénomène à la connaissance,
sans nommer le domaine ni promettre un usage particulier.

## Les deux objectifs

TORNE porte deux objectifs **autonomes**, avec deux tableaux de bord distincts. Aucun score
agrégé ne doit masquer l'échec de l'un par la réussite de l'autre.

### A. World Intelligence

Produire des connaissances nouvelles à partir de sources diverses : collecter et qualifier des
données, reconstruire des états physiques, produire des variables et estimations dérivées,
modéliser des phénomènes et des contraintes, simuler des évolutions, publier des produits de
connaissance réutilisables par plusieurs applications.

Cette activité a une valeur **indépendante de toute application financière**. Si la thèse
financière échoue ou change, les données qualifiées, les modèles et les produits validés
demeurent.

### B. World-to-Market Intelligence

Utiliser les connaissances produites, ainsi que d'autres informations pertinentes, pour
anticiper les conséquences économiques et financières d'événements réels : identifier ce qui va
se produire, estimer son calendrier de révélation, repérer les instruments exposés, puis tester
si le marché intègre la conséquence tardivement ou incomplètement.

Cet objectif est une **hypothèse de recherche**, pas un acquis. Il consomme A ; A ne dépend pas
de lui.

## État réel : ce qui est construit, ce qui est envisagé

| Construit aujourd'hui | Envisagé, pas implémenté |
|---|---|
| Socle documentaire : vision, architecture, doctrine de validation, journal de décisions | Connecteurs vers des sources réelles, acquisition de données |
| **Contrats fondamentaux exécutables** : cinq objets, trois dimensions temporelles, invariants appliqués à la construction | Règles temporelles propres à chaque source, et les six décisions bloquantes à lever avant le premier connecteur |
| **Capacité d'exécution** : entrées et paramètres explicites, graine contrôlée, configuration reproductible, rejeu depuis la configuration | Simulation d'évolutions, modèles physiques opérationnels |
| **Capacité d'évaluation** : séparation temporelle stricte, marche avant, références, métriques, couverture d'intervalles, comparaison appariée | Modèles économiques ou financiers |
| **Preuve et provenance** : source, preuve brute, observation, enregistrement d'exécution, produit de connaissance versionné | Connecteurs, secrets, magasin brut |
| **Une méthode scientifique réelle et vérifiée** : filtre de Kalman en espace d'état « tendance linéaire locale » | D'autres modèles, d'autres domaines |
| **Quatre primitives statistiques intégrées sous des noms TORNE** : OLS + CR1, Diebold-Mariano apparié + HAC, CUSUM, puissance — avec l'origine tracée en tête de module | Les huit autres primitives d'Athanor, non nécessaires ici |
| Paquet Python installable et construisible ; deux dépendances runtime (`numpy`, `scipy`), chacune au premier import réel | Dépendances de stockage, de connecteurs, d'outillage |
| Point d'entrée console qui énonce l'état du paquet | Reconstruction d'états sur données réelles, assimilation |
| **Les cinq objets du contrat, exécutables** : source, preuve brute, observation, grandeur dérivée, produit de connaissance | Règles temporelles propres à chaque source |
| **Oracles indépendants** : `statsmodels` (dépendance de développement) confronte le filtre d'état, la variance HAC et les écarts-types groupés | D'autres oracles : SciPy pour les distributions, une base de référence pour l'hydrologie |
| 306 tests, linting, formatage, test d'intégration bout en bout | Produits de connaissance sur sources qualifiées |
| Environnement verrouillé (`uv.lock` versionné) et gate de qualité exécuté sur Python 3.12 | Exécution de la CI sur d'autres matrices (versions de Python, platforms) |
| **Matrice de réutilisation consolidée** : trois audits d'archéologie, une décision par composant | Première application financière, edge démontré, capacité de déploiement |
| **Proposition argumentée du premier vertical slice** (Mississippi) et ses conditions d'échec | — |
| **Publication contrôlée** : la lignée est vérifiée au moment de la publication, pas seulement quand on le demande ; un enregistrement invalide ne peut pas produire de produit | — |
| **Nature par sortie** : un produit publie une seule nature, et chaque sortie garde la sienne à travers la sérialisation | — |
| **Absences respectées** : une absence reste une absence de la donnée à l'entrée jusqu'au rapport de métriques ; elle n'est jamais remplacée par un zéro | — |
| **Lignée temporelle fermée** : un produit ne peut pas être daté avant ce qu'il publie, et une entrée citée est l'objet canonique de l'enregistrement — un même identifiant ne peut pas désigner un autre contenu | — |
| **Première expérience définie** : question falsifiable, hypothèse nulle pré-enregistrée, sources et témoins qualifiés, critères d'arrêt — le pré-enregistrement est écrit avant le premier calcul | Acquisition des sources de l'expérience, puis exécution |
| **Socle d'acquisition** : récupérer une API ou un fichier, suivre la pagination, conserver la réponse brute et son empreinte, consigner ce qui a été demandé et ce qui a échoué — le secret ne passe jamais dans ce qui est consigné | Les intégrations de sources réelles, puis l'observatoire |

**Aucune performance n'est démontrée sur le monde réel.** Le dépôt contient désormais un modèle
scientifique — un filtre de Kalman en espace d'état — dont **l'implémentation** est vérifiée :
concordance à 1e-10 avec une implémentation de référence indépendante, cas à deux observations
calculé à la main, propriétés d'un estimateur d'état contrôlées sur un processus synthétique dont
l'état latent est connu par construction, et intervalle prédictif dont la couverture empirique
retrouve le 95 % nominal. Cela établit que **le code est correct**, pas qu'il prédit quoi que ce
soit du monde réel : la série de démonstration est synthétique. Les sources
réelles, elles, **sont qualifiées** — le gate P1 a établi dix sources, leurs
stations et leurs paramètres (`docs/MISSISSIPPI_DATA_SOURCES.md`) — mais la
mission 001 n'implémente pas de connecteur, et les règles temporelles par
source restent à fixer avant d'écrire le premier. La démonstration avait en
outre besoin d'un état latent **connu par construction**, ce qu'aucune série
publique ne donne. L'évaluation conduite compare le modèle à des références sur
ces mêmes données synthétiques — un écart observé, sous la puissance du test
disponible. Aucun chiffre de ce dépôt n'est une performance revendicable.

## Installation et tests

Le dépôt utilise `uv`, qui gère l'environnement Python et le verrou des dépendances. La version
de référence est **Python 3.12**, le plancher déclaré par le projet.

```bash
uv sync --locked              # installe l'environnement à partir de uv.lock, sans le modifier
uv run pytest -q              # exécute la suite de tests
uv run ruff check .           # contrôle de style et d'erreurs
uv run ruff format --check .  # contrôle de formatage
uv build                      # construit la sdist et le wheel
```

Si `uv` n'est pas dans le `PATH`, l'appeler par son chemin absolu ou l'ajouter au `PATH` de la
commande.

`uv.lock` est volontairement versionné : c'est lui qui rend l'environnement reproductible.
`uv sync --locked` échoue si le verrou ne correspond plus à `pyproject.toml` : c'est le premier
garde-fou contre la dérive des dépendances.

## Qualité

Le gate tient en cinq commandes. Elles ont toutes été exécutées et ont toutes passé le
31 octobre 2026 sur Python 3.12. Les sorties réelles du **socle initial** sont dans
`docs/P0-RAPPORT.md` ; après la mission 001, le gate est rejoué à l'identique et passe de nouveau,
avec 256 tests au lieu de 2 ; après la remédiation d'acceptation, il est rejoué encore, et passe
avec 301 tests ; après la fermeture de la lignée temporelle, il est rejoué une dernière fois, et
passe avec **306 tests**.

| Commande | Ce qu'elle garantit |
|---|---|
| `uv sync --locked` | L'environnement correspond exactement au verrou versionné, et le verrou est à jour vis-à-vis de `pyproject.toml`. |
| `uv run pytest -q` | La suite de tests passe. |
| `uv run ruff check .` | Aucune erreur de lint (style, imports, modernité). |
| `uv run ruff format --check .` | Le code est formaté selon la règle du projet. |
| `uv build` | La sdist et le wheel se construisent : le paquet est publiable. |

`.github/workflows/ci.yml` (GitHub Actions) rejoue ce gate à l'identique, sur Python 3.12.
**Ce workflow a été exécuté et a réussi** : chaque exécution déclenchée sur `main` s'est terminée
avec le verdict `success`, vérifié par l'API GitHub. Il rejoue le gate à chaque poussée.

Le dépôt est **public** (`github.com/RootSquirrels/torne`) : le code y est lisible par
quiconque. C'est un fait vérifiable par l'API GitHub, et il a une conséquence à trancher
par le propriétaire — voir `docs/DECISIONS.md`, « Licence du dépôt TORNE ».

## Documents de référence

| Document | Contenu |
|---|---|
| [`docs/VISION.md`](docs/VISION.md) | thèse, problème, deux objectifs et leurs critères, limites, non-objectifs |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | les quatre frontières, les préoccupations transversales, les responsabilités |
| [`docs/RESEARCH_AND_VALIDATION.md`](docs/RESEARCH_AND_VALIDATION.md) | cinq modes de validation et hiérarchie des affirmations |
| [`docs/REUSE_AUDIT.md`](docs/REUSE_AUDIT.md) | **matrice de réutilisation consolidée** : une décision par composant, le blocage de licence, les doublons à ne pas réimplémenter, ce qu'il faut extraire en premier |
| [`docs/SLICE-PREMIER.md`](docs/SLICE-PREMIER.md) | **piste de recherche documentée** (`TORNE-EXP-001`) : le critère de sélection relu, l'ambition hydrologique en quatre couches, la réutilisabilité multi-fleuves, et ce qui est demandé au propriétaire |
| [`docs/PRE-ENREGISTREMENT-001.md`](docs/PRE-ENREGISTREMENT-001.md) | **pré-enregistrement de la piste 001**, statut `planned` : question falsifiable, sources et témoins, modes de validation, hypothèse nulle, critères d'arrêt, conditions de gel — écrit avant tout calcul |
| [`docs/MISSISSIPPI_DATA_SOURCES.md`](docs/MISSISSIPPI_DATA_SOURCES.md) | **qualification des sources du Mississippi** : neuf sources, schémas réels, état de chaque API, ruptures méthodologiques, jeu de données minimal — et ce qu'il ne permet pas de mesurer |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | journal daté des décisions prises et des points ouverts |
| [`docs/PROGRAMME.md`](docs/PROGRAMME.md) | le programme d'ingénierie : les gates P0/P1/P2/P3, les principes, la répartition du travail |
| [`docs/CONTRATS_FONDAMENTAUX.md`](docs/CONTRATS_FONDAMENTAUX.md) | les cinq objets, les trois dimensions temporelles, 34 invariants vérifiables |
| [`docs/P0-RAPPORT.md`](docs/P0-RAPPORT.md) | le rapport du socle de build : sorties réelles des cinq commandes, décisions, limites |
| [`docs/MISSISSIPPI_DATA_SOURCES.md`](docs/MISSISSIPPI_DATA_SOURCES.md) | **qualification des sources** (gate P1) : dix sources, stations, paramètres, pièges méthodologiques, décisions bloquantes avant tout connecteur |
| [`docs/audit/ATHANOR.md`](docs/audit/ATHANOR.md) | audit d'`athanor` : estimateurs, juge, machine à états, licence, doublons |
| [`docs/audit/CRIN.md`](docs/audit/CRIN.md) | audit de SquirrelBetting / C.R.I.N. : discipline expérimentale, métriques, ce qui est hippique |
| [`docs/audit/LEGACY-BOREE.md`](docs/audit/LEGACY-BOREE.md) | audit de l'ancien BORÉE : point-in-time, lac, scellés, anti-fuite, ce qui est électrique |
| [`docs/audit/REVUE-CONSISTENCE.md`](docs/audit/REVUE-CONSISTENCE.md) | revue indépendante de la matrice de réutilisation : 25 écarts relevés et corrigés |
| [`experiments/README.md`](experiments/README.md) | ce qui a le droit d'être jetable |

La spécification conceptuelle de TORNE est le paquet de référence
`BOREE_W2M_Greenfield_Reference_V2.0` (76 fichiers, empreintes SHA-256 dans `SHA256SUMS.txt`),
conservé **en lecture seule** dans le dépôt voisin. C'est une spécification, pas une
implémentation : il ne prouve pas que des connecteurs, modèles, méthodes, validations ou
résultats existent.

Les dépôts historiques (`boree`, `athanor`, `SquirrelBetting`) restent **en lecture seule** et ne
sont pas des dépendances de TORNE. Ce qui en est repris est réécrit ou réadapté ici, jamais
référencé. L'observatoire Borée H3 et son protocole prospectif scellé sont hors périmètre :
strictement inchangés.

## Arborescence

```text
torne/
├── pyproject.toml          # paquet, dépendances minimales, configuration pytest et ruff
├── uv.lock                 # verrou des dépendances, versionné
├── README.md               # ce document
├── .gitignore
├── .github/workflows/ci.yml # gate de qualité en GitHub Actions
├── src/torne/
│   ├── __init__.py         # version et point d'entrée console provisoire
│   ├── contracts/          # contrats fondamentaux, exécutables : temps, validité, modèle, observation, grandeur dérivée, produit
│   ├── acquisition/        # socle transversal : récupération, pagination, conservation des preuves brutes
│   ├── execution/          # exécution d'un modèle : configuration, reproductibilité, rejeu
│   ├── methods/            # méthodes scientifiques : filtre d'état, comparaison, régression, CUSUM, puissance
│   ├── evaluation/         # séparation temporelle, métriques, références, rapport
│   └── knowledge/          # enregistrement d'exécution, lignée, produit de connaissance
├── tests/                  # tests des contrats, des maillons, et test d'intégration bout en bout
├── docs/                   # vision, architecture, validation, audit de réutilisation, décisions
└── experiments/            # explorations jetables, hors paquet
```

Il n'y a ni moteur, ni service, ni registre, ni répertoire vide : ils apparaîtront lorsqu'un
besoin concret les justifiera. Les quatre sous-paquets correspondent à quatre responsabilités
réellement exercées, pas à des couches prévues pour l'avenir.

## État du projet

**31 octobre 2026 — socle documentaire créé.** Le dépôt contient la vision, l'architecture, la
doctrine de validation, le journal de décisions, le format de la matrice de réutilisation, un
paquet Python sans code métier et un point d'entrée console provisoire.

**31 octobre 2026 — socle d'ingénierie en place et vérifié.** L'environnement est verrouillé
(`uv.lock` versionné), le paquet s'installe, se construit et s'importe, et le gate de qualité
(synchronisation, tests, lint, format, construction) passe sur Python 3.12. Le workflow GitHub
Actions qui rejoue ce gate **a été exécuté et a réussi**.

**31 octobre 2026 — remédiation d'acceptation.** Cinq défauts d'acceptation du socle scientifique
ont été corrigés, chacun par un test qui échouait avant et passe après (47 tests rouge sur
l'ancien code, 301 verts sur le nouveau) : la lignée est vérifiée au moment de la publication et
un enregistrement invalide ne peut plus être publié ; un produit publie une seule nature et
chaque sortie garde la sienne ; `ModelResult` refuse un horodatage naïf, un intervalle sans
sortie correspondante, une longueur incohérente, des bornes non finies ou non ordonnées, et une
nature de sortie non déclarée ; la méthode d'incertitude des métriques est celle que la
référence V2.0 autorise (variance HAC de Newey-West, taille effective) — et non un bootstrap que
le message du précédent commit décrivait à tort ; une absence reste une absence jusqu'au rapport
de métriques, sans jamais devenir un zéro.

**31 octobre 2026 — fermeture de la lignée temporelle.** Deux failles d'intégrité subsistaient,
au-delà des cinq défauts ci-dessus. Un produit pouvait être daté **avant** la production de ce
qu'il publie — un produit antidaté, dont la lignée aurait été vérifiée à un instant où ce qu'il
contient n'existait pas encore. Et une grandeur dérivée pouvait citer une **autre instance** de
son entrée, de même identifiant mais de contenu différent : le contrôle de temporalité
s'exerçait alors sur le substitut, et laissait passer un calcul antérieur à l'utilisabilité de sa
véritable entrée. L'instant effectif de publication ne peut plus précéder ni la production du
résultat publié ni l'établissement de l'enregistrement ; chaque entrée citée est rapprochée de
son objet canonique dans l'enregistrement, et les contrôles temporels s'exercent sur cet objet.
Cinq tests de non-régression : ils échouent sur le code d'avant, ils passent sur le nouveau.

**31 octobre 2026 — première expérience physique définie.** Le critère de sélection du premier
slice a été **relu** : il n'est plus le critère MISSISSIPPI/RHIN — un témoin économique public à
fréquence infra-mensuelle — mais trois portes dures du paquet de référence : la cible doit être une
grandeur **latente qu'aucun éditeur ne publie**, le juge doit être **véritablement indépendant**, et
la question doit être **identifiable**. Appliqué à la proposition Mississippi, ce critère la
refuse : les heures de fermeture d'écluses sont publiées directement, et les taux de fret USDA/AMS
dérivent du même marché fluvial que le produit expliquerait. L'expérience recommandée est donc la
**cohérence inter-agences de l'état hydrologique du Rhin** : la divergence entre les reconstructions
française, allemande et néerlandaise, et le déplacement qu'elle produit sur le compte de jours de
basses eaux. Son pré-enregistrement est écrit — question, hypothèse nulle, sources, témoins, modes
de validation, critères d'arrêt, conditions de gel — **avant** tout calcul, comme l'exige ADR-012.
La règle d'établissement de `KNOWN_AT` par source est désormais écrite : quatre classes, et la
classe détermine l'admissibilité. Aucune donnée n'a été acquise, aucun connecteur créé, aucune
performance démontrée.

**31 octobre 2026 — programme réordonné, et socle d'acquisition commencé.** Le propriétaire a
corrigé l'ordre des étapes : pré-enregistrer une expérience précise avant de savoir acquérir une
seule donnée réelle revenait à laisser les contraintes d'une expérience dicter toute l'architecture.
La démarche **exploratoire** — collecter, comprendre les sources, découvrir des régularités et des
lacunes — précède désormais la démarche **confirmatoire** ; le pré-enregistrement reste indispensable
avant l'analyse confirmatoire, mais il ne doit pas empêcher l'exploration. `TORNE-EXP-001` passe en
**piste de recherche documentée**, statut `planned`, et son travail est conservé tel quel. La séquence
du programme devient : **acquisition** → **observatoire des sources** → **fondation d'intelligence de
domaine** → **découverte scientifique et premiers produits de connaissance**. Trois niveaux sont
distingués et séparés par des contrats explicites : le socle transversal acquiert et conserve, la
couche sémantique comprend, la couche scientifique transforme. Le socle transversal est **commencé** :
contrats, transport, pagination, reprises, conservation des preuves brutes et journal d'acquisition
sont écrits et testés.

**31 octobre 2026 — mission 001 livrée : exécution, évaluation, preuve.** Le dépôt n'est plus
un socle documentaire. Il contient une capacité d'exécution (entrées et paramètres explicites,
graine contrôlée, configuration conservée, rejeu depuis la configuration), une capacité
d'évaluation (séparation temporelle stricte, marche avant, références, métriques, comparaison
appariée), la preuve et la provenance (source, preuve brute, observation, enregistrement,
produit de connaissance versionné), et **une méthode scientifique réelle** : un filtre de Kalman
en espace d'état « tendance linéaire locale », vérifié contre une implémentation de référence
indépendante, contre un cas calculé à la main et contre les propriétés attendues d'un estimateur
d'état. Quatre primitives d'`athanor.stats` ont été extraites et attribuées. La chaîne complète
est testée de bout en bout (`tests/test_end_to_end.py`) et rejouable
(`experiments/mission_001_demo.py`).

**31 octobre 2026 — le dépôt acquiert de vraies données.** Le socle transversal d'acquisition est
en service : `experiments/acquisition_demo.py` interroge **réellement** trois points d'accès publics
— les observations hydrométriques de Hub'EAU v2, les valeurs instantanées du NWIS de l'USGS, le
catalogue OData de Copernicus Data Space — conserve chaque réponse comme preuve brute, l'empreinte,
et consigne l'échec comme le succès. Le 31 octobre, l'acquisition a réussi sur les trois :
deux pages Hub'EAU (25 848 et 25 845 octets), une page USGS (56 082 octets), une page Copernicus
(13 470 octets), quatre lignes de manifeste. La troncature par le budget de pages est reportée
`partial`, et l'épuisement de la source est reporté `success` : les deux ne se confondent pas.

**31 octobre 2026 — alignement sur les fondations scientifiques et nettoyage du namespace.**
Le paquet de référence V2.0 (`docs/08-SCIENTIFIC-COMPUTING-FOUNDATION-AND-EVALUATION.md`,
ADR-021, SPEC-010) a été appliqué, non recopié. Le namespace `athanor` a disparu du paquet :
les quatre primitives sont des modules TORNE, et la provenance reste en tête de module. La loi de
Student vient désormais de **SciPy** — elle était réimplémentée, ce qu'ADR-021 interdit
explicitement. `statsmodels` est ajouté comme **dépendance de développement seulement** : il sert
d'oracle indépendant au filtre d'état (3,6e-10), à la variance HAC (3,5e-15) et aux écarts-types
groupés CR1 (4,6e-15). L'audit a trouvé une **incohérence de puissance** — l'approximation
normale était optimiste de 16,7 % à n=8 —, corrigée sur la loi de Student et validée par
Monte-Carlo. Le contrat est désormais complet : les **cinq objets** existent en code, la grandeur
dérivée porte sa propre temporalité (le `KNOWN_AT` du calcul, pas celui de la source), et les
six catégories ne se confondent plus — un état reconstruit n'est pas une estimation, et une
observation de source a son propre objet et son propre statut de qualité.

Non fait : aucun connecteur, aucun modèle économique ou financier, aucune application, aucun
moteur par domaine, aucun registre. **Aucune performance sur le monde réel n'est démontrée.**

En cours : le socle d'acquisition — intégrations de sources réelles, conservation des preuves
brutes, et une démonstration d'acquisition réelle. Puis l'observatoire des sources, qui dira ce que
les données permettent réellement de reconstruire et où elles sont lacunaires.