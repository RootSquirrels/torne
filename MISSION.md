# TORNE — GREENFIELD REPOSITORY BOOTSTRAP & TECHNICAL ARCHAEOLOGY

## Mission

Tu es le principal Software Architect et Technical Lead chargé de lancer une nouvelle implémentation de TORNE.

Tu dois créer un repository neuf, mettre en place son socle documentaire et technique minimal, puis examiner les anciens projets afin d'identifier les composants scientifiques, mathématiques et techniques qui méritent d'être réutilisés.

Tu travailles à partir de la référence conceptuelle **TORNE V2.0** (paquet `BOREE_W2M_Greenfield_Reference_V2.0`).

Ta mission n'est PAS de reproduire l'ancienne architecture, ni de fusionner plusieurs repositories, ni de construire immédiatement une plateforme complète.

Ta mission est de produire un nouveau socle propre, simple, extensible et scientifiquement rigoureux, en capitalisant sur les apprentissages des projets précédents.

---

# 0. Le nom, et ce qu'il faut distinguer

## 0.1 Pourquoi « TORNE »

Le fleuve constituait un axe important pour le commerce, le transport et les activités locales. Connaître la date de
débâcle était une information concrètement utile.

Une observation physique est ainsi devenue, au fil des siècles, une archive climatique exploitable scientifiquement.

C'est presque une illustration historique de la thèse World-to-Market :

1. Un phénomène physique se produit.
2. Il modifie les possibilités opérationnelles.
3. Il possède une conséquence économique.
4. Des acteurs ont intérêt à l'observer et à le documenter.
5. Les observations deviennent une source de connaissance réutilisable.

Tu ne trouverais pas une histoire plus pertinente pour expliquer l'ambition.

## 0.2 Deux systèmes, deux noms — ne jamais les confondre

| Nom | Désigne | Statut |
|---|---|---|
| **TORNE** | La plateforme nouvelle. World Intelligence, Market Intelligence, fondations partagées | À construire |
| **Borée H3** | L'observatoire de tension électrique déjà en production (dépôt `boree`), avec son protocole prospectif scellé | **Intact, en lecture seule** |
| **Athanor** | La bibliothèque de statistiques et d'économétrie (dépôt voisin `athanor`) | Composant candidat |
| **SquirrelBetting / C.R.I.N.** | Le système quantitatif de marchés de paris (dépôt voisin `SquirrelBetting`) | Composant candidat |

Le mot « BORÉE » reste le nom historique de TORNE et le nom actuel de l'observatoire en production. Dans le paquet de
référence conceptuelle, il désigne la même plateforme que TORNE sous son ancien nom ; **« Borée H3 » y désigne
toujours l'observatoire scellé, jamais la plateforme nouvelle**.

## 0.3 Règle de coexistence

- Les dépôts historiques sont **en lecture seule**. Les agents d'audit ne les modifient pas.
- Aucune fusion, aucune migration globale, aucune copie de répertoire depuis un dépôt historique.
- Ce qui est repris est **réécrit ou réadapté** dans TORNE, jamais référencé comme une dépendance.
- Le protocole scellé de Borée H3, son module temps et ses règles ne sont pas modifiés.

---

# 1. Vision à préserver

TORNE est une plateforme computationnelle de connaissance du monde réel.

Elle vise à reconstruire et modéliser des systèmes physiques, comprendre leurs contraintes, anticiper leurs évolutions et estimer leurs conséquences opérationnelles et économiques.

Deux objectifs autonomes doivent être préservés :

### A. World Intelligence

Produire des connaissances nouvelles à partir de sources diverses, notamment publiques :

- Collecter et conserver des données.
- Reconstruire des états physiques.
- Produire des variables et estimations dérivées.
- Modéliser des phénomènes et des contraintes.
- Combiner des modèles spécialisés.
- Simuler et prévoir des évolutions.
- Produire des connaissances réutilisables par plusieurs applications.

Cette activité possède une valeur indépendante de toute application financière.

### B. World-to-Market Intelligence

Utiliser les connaissances produites, ainsi que d'autres informations pertinentes, pour anticiper les conséquences économiques et financières d'événements réels.

La cible finale d'une application financière est notamment la probabilité de direction d'un actif à un horizon défini, son calendrier et son utilité économique.

Ne suppose pas qu'un modèle physique doit battre individuellement les modèles existants pour qu'une chaîne complète ait la valeur financière.

Inversement, un signal financier performant ne valide pas automatiquement la justesse scientifique de ses modèles intermédiaires.

Les deux objectifs doivent conserver leurs critères d'évaluation respectifs.

### Référence conceptuelle

Consulter le paquet de référence V2.0 fourni avec la mission (`BOREE_W2M_Greenfield_Reference_V2.0`, 76 fichiers,
empreintes SHA-256 dans `SHA256SUMS.txt`). Il est la spécification conceptuelle de TORNE ; il n'est pas un
implémentation et ne doit pas être présenté comme telle.

Ne pas modifier le protocole scellé Borée H3, son module temporel ou ses règles.

---

# 2. Règles fondamentales de conception

Ces règles ont priorité sur toute préférence personnelle d'architecture.

## Sophistication sans complexité inutile

TORNE doit être sophistiqué dans ses méthodes, ses modèles et ses preuves.

Il ne doit pas être compliqué dans son organisation logicielle.

Respecter les règles suivantes :

1. Une fonction n'a pas besoin de devenir un service.
2. Un module n'a pas besoin de devenir un moteur.
3. Un échange de données n'a pas besoin d'un framework.
4. Une abstraction n'est justifiée que par un problème réel ou un besoin de réutilisation démontré.
5. Un concept doit avoir un sens distinct des concepts déjà existants.
6. Ne pas multiplier les couches qui accomplissent la même fonction.
7. Ne pas créer des interfaces génériques pour anticiper des besoins hypothétiques.
8. Réutiliser les bibliothèques scientifiques éprouvées avant de développer des implémentations propriétaires.
9. Ne pas introduire d'infrastructure distribuée prématurément.
10. Ne pas confondre architecture documentaire et capacité réellement implémentée.

Privilégier du code explicite, lisible, testable et facile à déboguer.

**La complexité scientifique est acceptable. La complexité organisationnelle injustifiée ne l'est pas.**

## Ne rien présumer

Chaque affirmation doit être qualifiée :

- Implémenté et vérifié.
- Implémenté mais non vérifié.
- Documenté uniquement.
- Proposition.
- À étudier.
- Abandonné.

Ne jamais présenter une fonctionnalité documentée comme existante dans le code.

Ne jamais présenter une méthode comme SOTA sans comparaison pertinente, reproductible et documentée.

---

# 3. Phase I — Création du nouveau repository

Créer un repository indépendant nommé :

`TORNE`

Ne pas modifier les repositories historiques.

Ne pas effectuer de merge, de migration globale ou de copie de répertoire.

Ne pas créer de repository distant ni publier de code sans autorisation explicite. Initialiser le repository local et préparer son premier commit.

## Socle technique initial

Privilégier :

- Python pour le développement scientifique et l'orchestration.
- Un environnement de dépendances verrouillé.
- Pytest pour les tests.
- Ruff pour le linting et le formatage.
- Typage explicite lorsque cela améliore réellement la fiabilité.
- Git pour la traçabilité.

Vérifier les versions logicielles et les compatibilités des dépendances avant de les fixer.

Ne pas installer une bibliothèque simplement parce qu'elle apparaît dans un document d'architecture.

Ne pas introduire Rust dans le premier socle sans besoin mesuré.

Ne pas introduire Go dans le calcul scientifique.

## Arborescence initiale

Créer une arborescence volontairement réduite :

```text
torne/
├── pyproject.toml
├── uv.lock
├── README.md
├── .gitignore
├── src/
│   └── torne/
│       └── __init__.py
├── tests/
│   └── test_package.py
├── docs/
│   ├── VISION.md
│   ├── ARCHITECTURE.md
│   ├── RESEARCH_AND_VALIDATION.md
│   ├── REUSE_AUDIT.md
│   └── DECISIONS.md
└── experiments/
    └── README.md
```

Cette structure est un point de départ, pas un contrat rigide.

Ne crée pas de sous-packages vides pour chaque futur moteur.

Ne crée pas de répertoires `core`, `engines`, `services`, `adapters`, `registry`, `orchestration` ou `plugins` simplement pour remplir une architecture cible.

Ils apparaîtront lorsqu'un besoin concret les justifiera.

## Premier résultat attendu

Le repository doit :

- S'installer correctement.
- Exécuter ses tests.
- Passer le linting.
- Posséder une configuration reproductible.
- Ne contenir aucun code métier artificiel.
- Ne contenir aucun secret ni donnée sensible.
- Disposer d'un README compréhensible en deux minutes.

---

# 4. Phase II — Mise en place documentaire

Écrire peu de documents, mais les rendre utiles.

### README.md

Présenter :

- Ce qu'est TORNE.
- Ses deux objectifs.
- Son état réel.
- Comment installer et tester le repository.
- Où trouver les documents de référence.

Le README doit distinguer clairement les capacités construites de celles encore envisagées.

### VISION.md

Définir la thèse, le problème, les objectifs et les limites de TORNE.

Ne pas transformer la vision en catalogue de composants.

### ARCHITECTURE.md

Présenter uniquement les frontières fondamentales :

```text
Sources
   ↓
Modèles
   ↓
Produits de connaissance
   ↓
Applications
```

La provenance, la temporalité, l'incertitude et la validation sont des préoccupations transversales.

Les modèles physiques, opérationnels, économiques et financiers sont spécialisés et composables. Il n'existe aucune obligation de les organiser en une chaîne universelle.

Préciser les frontières de responsabilité sans inventer de nouveaux moteurs.

### RESEARCH_AND_VALIDATION.md

Formaliser les principes de validation :

- Validation rétrospective.
- Validation temporelle hors échantillon.
- Replay historique point-in-time.
- Validation indépendante et mécanistique.
- Validation prospective.

Les méthodes doivent être adaptées à la nature de la connaissance.

Distinguer reconstruction, estimation, prédiction, explication, causalité et simulation.

Conserver les notions de calibration, de référence, d'incertitude et d'abstention.

Ne pas imposer une validation prospective à toutes les expériences.

### REUSE_AUDIT.md

Document central de la phase d'archéologie technique.

Il contient la matrice des composants identifiés dans les anciens projets, leur état de vérification et la décision de réutilisation.

### DECISIONS.md

Journal court des décisions importantes.

Ne créer un ADR formel que lorsqu'une décision structurante, non évidente et susceptible d'évoluer le justifie.

Ne pas ouvrir une série d'ADR pour chaque choix de programmation.

---

# 5. Phase III — Archaeology des anciens repositories

Examiner les repositories disponibles, notamment :

- Athanor.
- SquirrelBetting / C.R.I.N.
- Ancien BORÉE (observatoire de tension électrique, dépôt `boree`).
- Tout autre repository contenant des composants scientifiques ou computationnels pertinents.

Première tâche : identifier précisément les repositories, leurs propriétaires, leurs branches, leurs commits et leurs relations.

Ne pas considérer Athanor et SquirrelBetting/C.R.I.N. comme un seul projet sans l'avoir vérifié.

Pour chacun :

1. Lire le README et l'architecture.
2. Examiner l'arborescence réelle.
3. Identifier les modules actifs, obsolètes et expérimentaux.
4. Examiner les tests et leur couverture pertinente.
5. Vérifier les dépendances et la licence.
6. Identifier les composants réutilisables.
7. Identifier les composants fortement liés au domaine d'origine.
8. Rechercher les implémentations alternatives et duplications.
9. Identifier les erreurs historiques et les leçons qui en ont été tirées.
10. Reproduire les résultats importants lorsque l'environnement le permet.

Ne pas limiter l'inspection aux documents d'architecture : examiner le code réel.

Si un repository n'est pas accessible, signaler le blocage. Ne pas inventer son contenu.

## 5.1 Athanor

Examiner notamment :

- Estimateurs statistiques et probabilistes.
- Méthodes d'identification et d'estimation des paramètres.
- Modèles de prévision.
- Calibration.
- Estimation d'incertitude.
- Traitement des séries temporelles.
- Prévisions probabilistes.
- Méthodes numériques réutilisables.
- Benchmarks et comparaisons d'estimateurs.
- Préparation et découpage des données.
- Validation hors échantillon.
- Reproductibilité des calculs.
- Utilisation de bibliothèques scientifiques externes.

Rechercher particulièrement les estimateurs et méthodes issus de recherches récentes.

Pour chaque méthode intéressante, identifier :

- Référence scientifique.
- Implémentation utilisée.
- Commit et version.
- Licence.
- Domaine de validité.
- Hypothèses.
- Entrées et sorties.
- Benchmarks existants.
- Résultats effectivement reproduits.
- Limites et conditions de réutilisation.

Ne pas retenir une méthode simplement parce qu'elle est récente ou présentée comme SOTA.

## 5.2 SquirrelBetting / C.R.I.N.

Examiner notamment :

- Construction déterministe des matrices de données.
- Artefacts de modèles autonomes.
- Alignement entre entraînement et inférence.
- Split temporel et walk-forward.
- Pipelines d'évaluation.
- Calibration.
- Tests de multiplicité.
- Inférence séquentielle lorsque pertinente.
- Pré-enregistrement et amendements.
- Contrôles de validité des résultats.
- Détection de dérive.
- Comparaison de plusieurs estimateurs.

Distinguer les méthodes générales des composants spécifiques aux marchés de paris.

Ne pas importer automatiquement :

- PMU et ses features.
- Pool odds et closing-Shin.
- Kelly et ses règles de sizing.
- Settlement hippique.
- Les règles de marché propres à C.R.I.N.
- Les domain adapters génériques avant qu'un besoin réel soit établi.

La philosophie de rigueur expérimentale peut être réutilisée sans importer toute l'architecture du projet.

## 5.3 Ancien BORÉE (observatoire de tension électrique)

Examiner :

- Ingestion et gestion des sources.
- Conservation des payloads bruts.
- Hashing et déduplication.
- Normalisation des observations.
- Unités et références spatiales.
- Temporalité et point-in-time.
- Transformations analytiques.
- Provenance et lineage.
- Snapshots et reconstitution historique.
- Connecteurs réels et leurs tests.
- Gestion des données géospatiales et multidimensionnelles.

Distinguer soigneusement ce qui était une spécification de ce qui était effectivement implémenté.

Ne pas recopier les contrats sans vérifier qu'ils sont adaptés au périmètre simplifié de TORNE.

---

# 6. Phase IV — Matrice de réutilisation

Pour chaque composant candidat, créer une entrée dans `docs/REUSE_AUDIT.md`.

Utiliser ce format :

| Champ | Description |
|---|---|
| Composant | Nom et fonction réelle |
| Origine | Repository, chemin, commit |
| État | Implémenté, documenté, expérimental, obsolète |
| Tests | Tests existants et résultats |
| Dépendances | Bibliothèques et contraintes |
| Domaine | Général ou spécifique |
| Licence | Vérifiée ou inconnue |
| Valeur pour TORNE | Besoin concret couvert |
| Coût de reprise | Faible, moyen, élevé |
| Décision | Reprendre, adapter, réimplémenter, écarter |
| Justification | Raisonnement vérifiable |

Chaque composant doit être classé dans l'une des quatre catégories suivantes :

### REUSE

Le composant fonctionne, est suffisamment indépendant et peut être repris avec un coût raisonnable.

### ADAPT

Le principe est bon, mais l'implémentation doit être simplifiée ou adaptée.

### REIMPLEMENT

Le comportement est utile, mais le code est trop imbriqué, trop complexe ou insuffisamment fiable pour être repris tel quel.

### REJECT

Le composant ne correspond pas à TORNE, fait double emploi ou n'apporte pas de valeur démontrée.

Ne pas intégrer un composant tant que sa décision et ses dépendances ne sont pas établies.

---

# 7. Phase V — Comparaison et recherche de méthodes

Ne pas limiter la recherche scientifique aux méthodes déjà utilisées dans les repositories.

À partir des problèmes identifiés dans TORNE, rechercher les méthodes et bibliothèques pertinentes.

Priorités de recherche :

1. Estimation des états de systèmes physiques.
2. Identifiabilité et observabilité.
3. Assimilation de données.
4. Estimation probabiliste et incertitude.
5. Systèmes dynamiques et modèles hybrides.
6. Simulation et méthodes numériques.
7. Modélisation de réseaux et de contraintes.
8. Modélisation de flux et systèmes économiques.
9. Prévision probabiliste.
10. Calibration et validation.

Pour chaque candidat :

- Partir d'un problème concret.
- Identifier les publications et références primaires.
- Examiner les logiciels disponibles.
- Comparer les alternatives.
- Vérifier l'activité et la maturité de l'implémentation.
- Examiner les licences et coûts.
- Évaluer la compatibilité avec le runtime envisagé.
- Éviter les dépendances redondantes.

Créer une synthèse courte dans `docs/REUSE_AUDIT.md` ou un document de recherche existant.

Ne pas créer un framework SCF propriétaire.

TORNE doit sélectionner, composer et évaluer les méthodes éprouvées, pas réimplémenter l'ensemble des mathématiques.

---

# 8. Phase VI — Définir le premier vertical slice

Ne pas choisir un cas uniquement parce qu'il est techniquement intéressant.

Comparer les candidats disponibles, notamment le Rhin et le Mississippi, sur :

- Disponibilité des données.
- Qualité de l'historique.
- Droits d'accès et de conservation.
- Possibilité de reconstruction historique.
- Existence de références indépendantes.
- Mesurabilité des conséquences physiques et opérationnelles.
- Possibilité de mesurer une conséquence économique.
- Difficulté d'implémentation.
- Valeur de connaissance obtenue.
- Possibilité d'une application financière ultérieure.

Proposer un premier cas, avec justification et risques.

Ne pas imposer dès maintenant un moteur hydrologique, un moteur causal ou un moteur financier.

Le premier vertical slice doit démontrer un chemin complet :

```text
Source réelle
    ↓
Observation exploitable
    ↓
Variable ou estimation construite
    ↓
Produit de connaissance
    ↓
Évaluation reproductible
```

Une application financière pourra ensuite consommer ce produit ou d'autres informations disponibles.

Le résultat doit être mesurable, reproductible et honnête sur ses limites.

---

# 9. Politique anti-complexité

Tout au long de cette mission, appliquer les contrôles suivants.

Avant de créer un module, demander si une fonction existante suffit.

Avant de créer une interface, vérifier qu'au moins deux implémentations concrètes en ont besoin.

Avant de créer un registre, vérifier qu'une donnée versionnée ou un simple fichier ne suffit pas.

Avant de créer un moteur, vérifier que sa responsabilité ne peut pas être clairement assumée par un modèle ou un module existant.

Avant de créer un vocabulaire, vérifier qu'il apporte une distinction indispensable.

Avant de reprendre un composant, vérifier qu'il n'introduit pas une abstraction inutile de son ancien projet.

Ne pas créer :

- Un moteur universel du monde.
- Un moteur causal universel.
- Une architecture microservices.
- Un framework de plugins.
- Un bus d'événements.
- Un graphe de connaissances obligatoire.
- Un système de workflow généraliste.
- Une couche de métadonnées qui duplique les contrats de données.
- Un système de validation parallèle à la logique scientifique.
- Une abstraction générique anticipant des domaines non encore étudiés.

Ces choix pourront être reconsidérés uniquement en présence d'un besoin démontré.

---

# 10. Organisation du travail en agents

Si plusieurs agents sont disponibles, répartir les travaux sans créer de dépendances circulaires.

### Agent A — Repository & Foundations

Responsable du nouveau repository, des outils, des tests et des documents initiaux.

### Agent B — Athanor Archaeology

Responsable de l'audit technique et scientifique d'Athanor et de ses méthodes réutilisables.

### Agent C — SquirrelBetting / C.R.I.N. Archaeology

Responsable de l'audit du code quantitatif, des estimateurs, des méthodes de validation et des composants transversaux.

### Agent D — Legacy BORÉE Archaeology

Responsable de l'audit des composants data, temporels, géospatiaux et physiques de l'ancien BORÉE.

### Agent principal — Integration & Architecture

Il consolide les rapports, tranche les décisions de réutilisation, évite les doublons et conserve une seule architecture de référence.

Les agents d'audit ne doivent pas modifier les repositories historiques.

Ils doivent produire des constats et des recommandations vérifiables, pas créer chacun leur propre architecture cible.

---

# 11. Livrables de fin de mission

La mission initiale est terminée lorsque les éléments suivants sont disponibles :

1. Repository TORNE créé et fonctionnel.
2. Environnement de développement verrouillé.
3. Tests et linting opérationnels.
4. README et documentation fondatrice.
5. Inventaire des repositories historiques.
6. Rapport d'audit technique d'Athanor.
7. Rapport d'audit technique de SquirrelBetting / C.R.I.N.
8. Rapport d'audit de l'ancien BORÉE.
9. Matrice de réutilisation consolidée.
10. Synthèse des méthodes scientifiques intéressantes et de leurs références.
11. Proposition argumentée du premier vertical slice.
12. Liste courte des composants à extraire dans la prochaine étape.
13. Liste explicite des éléments rejetés et pourquoi.

Pour chaque constat important, fournir un chemin de fichier, un commit, un test ou une référence scientifique lorsque c'est possible.

Ne pas confondre l'existence d'un document de conception avec une implémentation vérifiée.

---

# 12. Conditions d'arrêt

Ne commence pas à migrer massivement du code pendant cette première mission.

Ne commence pas à construire le système complet.

Ne transforme pas les résultats de l'audit en dizaines de nouveaux documents.

Ne propose pas une nouvelle architecture globale si V2.0 répond déjà au besoin.

La fin de mission doit aboutir à une décision simple :

**Quelles sont les quelques briques dont TORNE a réellement besoin pour commencer son premier développement, et quelles sont celles que nous avons intérêt à laisser dans les anciens projets ?**

La qualité de cette mission se mesure à la clarté de cette réponse, pas au volume de code produit.

---

# Instruction finale

Construis un TORNE neuf, mais conserve l'intelligence accumulée dans les projets précédents.

Sois exigeant dans l'analyse, conservateur dans les abstractions, pragmatique dans le code et rigoureux dans les preuves.

Ne cherche pas à impressionner par une architecture sophistiquée.

Cherche à construire le système le plus simple capable de produire une connaissance réellement utile, reproductible et défendable.
