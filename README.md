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
| Socle documentaire : vision, architecture, doctrine de validation, journal de décisions | Modèles physiques, opérationnels, économiques ou financiers |
| Paquet Python installable, sans aucun code métier | Connecteurs vers des sources réelles, acquisition de données |
| Point d'entrée console qui énonce l'état du paquet | Reconstruction d'états, assimilation de données, simulation |
| Tests de fumée et configuration de linting | Produits de connaissance versionnés, cartographie, lecture par API |
| **Matrice de réutilisation consolidée** : trois audits d'archéologie, une décision par composant | Première application financière, edge démontré, capacité de déploiement |
| **Proposition argumentée du premier vertical slice** (Mississippi) et ses conditions d'échec | Toute extraction de code des dépôts historiques, bloquée par la licence d'Athanor |

**Aucune performance n'est démontrée.** Aucun modèle n'existe dans ce dépôt : aucune puissance
prédictive, aucun alpha, aucune rentabilité, aucune position « state of the art » ne peut être
revendiquée. Toute affirmation chiffrée dans les documents de ce dépôt est une méthode ou un
objectif, jamais un résultat. Les documents présents décrivent une architecture et ses
conditions de validité, pas des capacités.

## Installation et tests

Le dépôt utilise `uv`, qui gère l'environnement Python et le verrou des dépendances.

```bash
uv sync --frozen        # installe l'environnement à partir de uv.lock
uv run pytest           # exécute la suite de tests
uv run ruff check .     # contrôle de style et de correction automatique
```

> **Ces commandes n'ont pas été exécutées sur le poste de construction.**
> Ce poste ne disposait ni de `uv` ni des dépendances Python : l'installation, l'exécution des
> tests et le linting n'ont donc pas pu être vérifiés. Le fichier `uv.lock` n'a pas pu être
> généré et reste à produire (`uv lock`) avant le premier commit.

`uv.lock` est volontairement versionné : c'est lui qui rend l'environnement reproductible.

## Documents de référence

| Document | Contenu |
|---|---|
| [`docs/VISION.md`](docs/VISION.md) | thèse, problème, deux objectifs et leurs critères, limites, non-objectifs |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | les quatre frontières, les préoccupations transversales, les responsabilités |
| [`docs/RESEARCH_AND_VALIDATION.md`](docs/RESEARCH_AND_VALIDATION.md) | cinq modes de validation et hiérarchie des affirmations |
| [`docs/REUSE_AUDIT.md`](docs/REUSE_AUDIT.md) | **matrice de réutilisation consolidée** : une décision par composant, le blocage de licence, les doublons à ne pas réimplémenter, ce qu'il faut extraire en premier |
| [`docs/SLICE-PREMIER.md`](docs/SLICE-PREMIER.md) | proposition argumentée du premier vertical slice (Mississippi), critères de succès et conditions d'échec |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | journal daté des décisions prises et des points ouverts |
| [`docs/audit/ATHANOR.md`](docs/audit/ATHANOR.md) | audit d'`athanor` : estimateurs, juge, machine à états, licence, doublons |
| [`docs/audit/CRIN.md`](docs/audit/CRIN.md) | audit de SquirrelBetting / C.R.I.N. : discipline expérimentale, métriques, ce qui est hippique |
| [`docs/audit/LEGACY-BOREE.md`](docs/audit/LEGACY-BOREE.md) | audit de l'ancien BORÉE : point-in-time, lac, scellés, anti-fuite, ce qui est électrique |
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
├── uv.lock                 # à générer (uv absent du poste de construction)
├── README.md               # ce document
├── .gitignore
├── src/torne/__init__.py   # version et point d'entrée console provisoire
├── tests/test_package.py   # tests de fumée
├── docs/                   # vision, architecture, validation, audit de réutilisation, décisions
└── experiments/            # explorations jetables, hors paquet
```

Il n'y a ni moteur, ni service, ni registre, ni répertoire vide : ils apparaîtront lorsqu'un
besoin concret les justifiera.

## État du projet

**31 octobre 2026 — socle documentaire créé.** Le dépôt contient la vision, l'architecture, la
doctrine de validation, le journal de décisions, le format de la matrice de réutilisation, un
paquet Python sans code métier et un point d'entrée console provisoire.

En cours : consolidation de la matrice de réutilisation à partir des trois rapports
d'archéologie, et choix du premier slice vertical.

Non fait : génération de `uv.lock`, installation, exécution des tests, linting — impossible sur
le poste de construction, qui n'avait ni `uv` ni dépendances. Aucune performance n'est
démontrée.
