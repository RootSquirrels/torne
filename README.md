# TORNE

**Plateforme d'intelligence du monde physique.** TORNE transforme des sources hétérogènes — hydrologiques,
satellitaires, économiques — en connaissances propriétaires, traçables et validables : des **états reconstruits**
du monde physique, des **variables dérivées** qui ne figurent dans aucune source, et des produits de connaissance
versionnés et auditables.

> **Aucune performance n'est démontrée à ce jour.** Le dépôt est un socle exécutable : il acquiert, conserve,
> exécute et évalue. Il ne produit encore aucun résultat scientifique. Ce qui est fait, ce qui ne l'est pas, et ce
> qui vient ensuite : [`docs/PROGRAMME.md`](docs/PROGRAMME.md).

## Ce qui distingue TORNE

TORNE n'est pas une plateforme d'intégration de données. Il occupe l'espace entre la donnée et le résultat, et il
distingue trois choses qu'il ne faut pas confondre :

| | Ce que c'est | Exemple |
|---|---|---|
| **TORNE, la plateforme** | sa capacité à acquérir, comprendre, rapprocher, reconstruire et documenter des informations sur le monde physique | le socle d'acquisition, les contrats, la lignée |
| **Les domaines de connaissance** | hydrologie, énergie, météorologie, logistique, agriculture, industrie, infrastructures | ce qu'un domaine définit comme objets, unités, référentiels, relations |
| **Les expériences scientifiques** | des questions particulières auxquelles TORNE répond à partir de ses données et de ses modèles | la cohérence inter-agences de l'état du Rhin |

Confondre les trois, c'est construire une plateforme sur mesure d'une expérience. TORNE les distingue, et les
rapports de résultat les distinguent encore : **une affirmation physique n'est jamais une affirmation financière**.

## Deux objectifs, deux tableaux de bord

Deux enjeux coexistent, et ils ne sont pas mutuellement conditionnels. Ils sont mesurés et rapportés
**séparément** : un score agrégé qui masquerait l'échec de l'un par la réussite de l'autre est interdit.

**A — Produire une valeur d'intelligence.** Collecter et qualifier des sources diverses, surtout publiques ;
reconstruire des états physiques, géographiques, industriels ou institutionnels ; coupler des sources et des
modèles ; créer des variables absentes des sources ; simuler des trajectoires et des contraintes ; rendre les
résultats interrogeables, cartographiables et auditables. Cette activité est un actif autonome.

**B — Chercher un avantage financier.** Utiliser ces connaissances pour anticiper une conséquence économique
réelle, identifier les entités et actifs exposés, estimer le moment où la conséquence devient observable, puis
tester si le prix des instruments concernés l'intègre avec retard ou incomplètement — et si l'écart est
négociable après coûts, risques et contraintes d'exécution. C'est une hypothèse de recherche.

**B est reportée** tant que le socle d'intelligence physique n'est pas suffisamment mature
([`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §5). Si B échoue, A conserve ses données qualifiées, ses modèles,
ses variables et sa capacité à produire de l'intelligence : B peut être modifié ou remplacé sans reconstruire le
socle.

## Le problème que TORNE attaque

- Les sources sont hétérogènes, datées, révisées, parfois redondantes, rarement décrites par les conditions dans
  lesquelles elles étaient disponibles.
- Les phénomènes qui déterminent une conséquence économique sont rarement observés directement : ils doivent être
  reconstruits à partir de signaux indirects.
- Les conséquences ne sont pas visibles au moment où elles se produisent : il y a un décalage entre la réalité
  physique, la conséquence opérationnelle, sa révélation, et l'intégration financière.
- Les démonstrations disponibles mélangent des niveaux de preuve incompatibles : une reconstruction cohérente
  présentée comme une prédiction, une corrélation comme une causalité, une simulation comme un fait.

TORNE attaque les quatre points à la fois : qualifier les sources, reconstruire les états, dater les étapes, et
**nier l'affirmation plus forte que la preuve**.

## L'état réel

| Ce qui est en place | Ce qui ne l'est pas |
|---|---|
| Socle d'acquisition exécutable : transport durci, magasin brut adressé par le contenu, fetcher paginé, contrat de connecteur à quatre contrôles | Une seule source a produit des observations ; les deux autres restent à qualifier |
| **Trois sources réellement intégrées**, interrogées sur le réseau : Hub'EAU v2, USGS « Water Data for the Nation » (API OGC), catalogue Copernicus Data Space | Aucune source n'est qualifiée au sens de la classe de publication — établie, bornée, inconnue |
| Objets et temporalité : cinq objets, trois dimensions, `usable_at` dérivé, absence qualifiée | Pas de moteur, pas de registre ; la couche sémantique n'existe que pour l'hydrologie |
| **Première couche sémantique du domaine** (`hydrology/`) : enregistrement → observation, climatologie journalière, anomalie standardisée | Un seul domaine, une seule station : la généralisation n'est pas faite |
| Méthodes : filtre de Kalman en espace d'état, régression et erreur-type CR1, rupture CUSUM, puissance, comparaison appariée | Aucune performance démontrée : le modèle tourne sur des données réelles, mais aucune performance n'est *établie* |
| **Un jalon sur le monde réel** : 33 481 relevés quotidiens acquis, climatologie reproduisant les statistiques publiées de l'agence à 0,11 % près, premier produit de connaissance publié | Une seule variable dérivée ; aucune preuve prospective — le pré-enregistrement est écrit, mais pas outillé |
| Exécution rejouable, évaluation — découpage cumulatif, références, métriques, incertitude —, enregistrement avec lignée vérifiable | Aucune preuve prospective : le pré-enregistrement est écrit, mais pas outillé |
| Plus de 490 tests verts ; la CI construit le paquet, l'installe et le lance | Une source peut accepter un filtre sans l'appliquer — cas mesuré sur Hub'EAU, voir `docs/SOURCES.md` §I.1 |
| La conformité d'acquisition bloque ce qui n'est pas conforme, et la preuve brute est conservée | La licence du dépôt n'est pas choisie — c'est une décision du propriétaire |

Le détail — et surtout **ce qui manque** — sont dans [`docs/PROGRAMME.md`](docs/PROGRAMME.md).

## Les documents de référence

Sept documents, une responsabilité chacun.

| Document | Ce qu'il fixe |
|---|---|
| [`README.md`](README.md) | ce que TORNE est, et où l'on trouve quoi |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | les frontières, les responsabilités, les couches — **où** passe chaque chose |
| [`docs/CONTRATS_FONDAMENTAUX.md`](docs/CONTRATS_FONDAMENTAUX.md) | les objets, la temporalité, les invariants — **ce qui** doit rester vrai |
| [`docs/RESEARCH_AND_VALIDATION.md`](docs/RESEARCH_AND_VALIDATION.md) | la doctrine de preuve — **comment** une affirmation se teste |
| [`docs/SOURCES.md`](docs/SOURCES.md) | les sources intégrées et qualifiées — **ce que** chaque source donne, et ne donne pas |
| [`docs/PROGRAMME.md`](docs/PROGRAMME.md) | la situation, l'objectif prioritaire, les critères de sortie — **quoi** ensuite |
| [`docs/PRE-ENREGISTREMENT-001.md`](docs/PRE-ENREGISTREMENT-001.md) | le protocole d'une expérience confirmatoire, écrit avant de la regarder |

[`experiments/README.md`](experiments/README.md) explique ce qui a sa place dans `experiments/` : des scripts
d'exploration jetables, qui ne deviennent du code que s'ils survivent à la relecture.

## Installer et vérifier

```bash
uv sync --locked
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv build
```

Python 3.12, `uv` épinglé par la CI. Le point d'entrée console `torne` décrit l'état du paquet :

```console
$ torne
torne 0.1.0 — exécution, évaluation et preuve implémentées ; premier jalon sur données réelles publié ; aucune performance démontrée
```

## Structure du dépôt

```text
src/torne/
  acquisition/    socle transversal : transport, fetcher, magasin brut, contrat de connecteur, adaptateurs
  contracts/      objets et temporalité : source, preuve brute, observation, variable dérivée, produit
  methods/        couche scientifique : Kalman, régression, rupture, puissance, comparaison
  evaluation/     découpage temporel, références, métriques, incertitude, rapport
  execution/      exécution rejouable d'un modèle
  knowledge/      enregistrement d'un produit et vérification de sa lignée
  hydrology/      couche sémantique du domaine : enregistrement → observation, variable dérivée
docs/             les documents de référence
tests/            la suite de tests
experiments/      explorations jettables
```

## Limites et non-objectifs

TORNE ne cherche pas à construire : un modèle universel du monde ; un moteur causal universel ; un moteur
mathématique propriétaire réimplémentant l'écosystème scientifique ; une chaîne causale générique applicable sans
adaptation à tout domaine ; un graphe de connaissances qui prétend expliquer un système par la seule présence de
relations ; une architecture microservices, un bus d'événements, un framework de plugins, un système de workflow
généraliste ; une validation uniforme imposant les mêmes métriques à tous les modèles ; un outil de trading auquel
on aurait ajouté des données physiques ; une couche de métadonnées dupliquant les contrats de données.

Chacun de ces choix pourra être reconsidéré **uniquement en présence d'un besoin démontré**.

**Avec les systèmes existants :** TORNE est un système neuf et indépendant. Il ne modifie, ne migre et ne fusionne
aucun des dépôts historiques, qui restent en lecture seule et servent de références de recherche. Ce qui en est
repris est réécrit, avec son origine déclarée en tête de module
([`docs/CONTRATS_FONDAMENTAUX.md`](docs/CONTRATS_FONDAMENTAUX.md) §5).

## Licence

**Non choisie.** Le dépôt est hébergé publiquement sur GitHub ; la politique de propriété intellectuelle est gérée
par le propriétaire, séparément.
