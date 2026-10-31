# TORNE — Recherche et validation

**Doctrine de preuve — 31 octobre 2026**
**Statut : principes applicables. Aucune validation n'a encore été conduite : le dépôt ne
contient ni modèle, ni données, ni résultat.**

## 1. Principe

La preuve est proportionnée à l'affirmation. Aucun mode de validation n'est universellement
supérieur, et il n'existe pas de méthode unique qui prouve tout.

Une connaissance construite sur le passé peut être testée sur des événements historiques
ultérieurs. Cette approche est légitime à condition que les périodes, les données, les choix et
les informations disponibles soient séparés proprement.

Chaque affirmation doit donc être formulée avant d'être testée : ce que l'on avance, sur quel
domaine, sur quelle période, avec quelles données, comparé à quoi, et avec quels critères de
réussite ou d'échec.

## 2. Les cinq modes de validation

| Mode | Ce qu'il teste | Ce qu'il ne prouve pas |
|---|---|---|
| **Rétrospective descriptive** | comparer une reconstruction ou une description à des observations indépendantes de la période étudiée | que l'information était disponible à l'époque, ni aucune capacité prédictive |
| **Temporel hors échantillon** | construire sur une période ancienne, figer, puis tester sur une période postérieure | ce qui était disponible au moment de la construction, si les archives ont été consolidées après coup |
| **Replay point-in-time** | avancer chronologiquement en ne fournissant que l'information disponible à chaque date | que le système réel avait effectivement reçu cette information |
| **Indépendant / mécanistique** | comparer à des mesures, expériences, documents opérationnels, invariants ou références indépendantes | la généralisation à d'autres périodes, régimes ou domaines |
| **Prospectif** | enregistrer avant le résultat et évaluer lorsque l'observation arrive | la validité d'autres périodes ou d'autres domaines que ceux observés |

Ces cinq modes ne sont ni cinq étapes successives, ni une check-list obligatoire. On en choisit
un ou plusieurs selon la nature de l'affirmation.

### 2.1 Ce qui rend une expérience temporelle valable

Construire sur 2000-2015 puis tester sur 2015-2020 est une expérience temporelle légitime si :

- les variables cibles, les métriques et les critères sont définis avant de lire la période test ;
- le code, les paramètres, les règles, les variables et les références sont figés ;
- les résultats de la période test ne servent ni à choisir ni à régler le modèle ;
- les versions et révisions des données sont conservées ;
- le fait que les données de construction soient des archives révisées a posteriori est signalé.

Cette expérience ne démontre pas ce que le système aurait su en 2015 si les archives de
construction ont été consolidées après cette date.

## 3. Choisir le mode selon l'affirmation

Le mode se choisit en fonction de ce que l'on prétend, jamais par défaut ni par commodité.

| Si l'affirmation est… | Mode minimal crédible |
|---|---|
| « mon état reconstruit correspond à ce qui a été observé » | rétrospective descriptive, avec référence indépendante |
| « mon modèle généralise dans le temps » | temporel hors échantillon, avec gel explicite |
| « mon système n'aurait su que ce qui était disponible à la date t » | replay point-in-time |
| « mon mécanisme produit effectivement cet effet » | indépendant ou mécanistique |
| « mon signal prédit la révélation à venir » | prospectif |

Une étude qui ne peut rien changer n'est pas ouverte. Une étude dont la preuve possible est
hors de portée doit être ajournée, non simulée par une méthode plus faible présentée comme
équivalente.

**Aucune validation prospective n'est imposée par défaut.** Elle est exigeante : elle suppose un
protocole scellé, une période d'attente, une définition de l'échec à l'avance et l'acceptation
d'un résultat négatif. Elle se justifie pour une affirmation sur l'avenir ; elle n'a pas de sens
pour qualifier un procédé de calcul, une convention de nommage ou une propriété de format.

## 4. Trois lectures temporelles à ne pas confondre

- **Replay opérationnel** : ce que le système avait effectivement reçu et rendu utilisable.
- **Replay public** : ce qui était publiquement accessible, sur preuve ou borne conservatrice.
- **Descriptif rétrospectif** : ce que les archives consolidées permettent de reconstituer
  aujourd'hui.

Un replay public ne prouve pas que le système avait reçu l'information. Une archive révisée ne
prouve pas qu'elle était disponible à l'époque. Ces trois lectures ne sont jamais interchangeables
dans un rapport de résultat.

## 5. Six affirmations distinctes

| Affirmation | Ce qu'elle exige | Ce qu'elle ne prouve pas |
|---|---|---|
| **Reconstruction** | un état restitué, daté, localisé, avec sa provenance | que l'état était connu à l'époque, ni qu'il est prédictif |
| **Estimation** | une grandeur non directement observée, avec sa méthode et son incertitude | une observation directe, ni un mécanisme causal |
| **Prédiction** | une valeur future, émise à une date donnée, avec un intervalle | un mécanisme causal, ni une réalité future |
| **Explication** | un mécanisme testable reliant un changement à un effet | que l'effet est causal identifié |
| **Causalité** | une stratégie d'identification explicite et ses hypothèses | la généralisation hors du cadre d'identification |
| **Simulation** | un résultat conditionnel à un scénario imposé | que le scénario se réalisera |

Les implications sont asymétriques et doivent être respectées : une reconstruction validée
n'est pas automatiquement prédictive ; une prédiction exacte ne démontre pas le mécanisme causal ;
un mécanisme plausible n'est pas un effet causal identifié ; une simulation cohérente ne prouve
pas que le scénario se réalisera ; une relation documentée ne quantifie pas sa propagation ; une
bonne performance financière ne valide pas rétroactivement les modèles physiques.

## 6. Référence, calibration, incertitude, abstention

Ces quatre notions accompagnent chaque affirmation. Elles ne se substituent pas l'une à l'autre.

**Référence.** Chaque évaluation se compare à une référence : une référence simple (la
persistance, la moyenne, une baseline naïve) ou une méthode concurrente, si une comparaison est
pertinente. Une performance sans référence n'est pas interprétable. La référence est choisie
avant le test.

**Calibration.** Les probabilités annoncées doivent correspondre aux fréquences observées.
L'évaluation d'une incertitude ne se limite pas à une erreur moyenne : elle vérifie que
l'intervalle annoncé contient l'observation attendue à la fréquence promise. Une incertitude
surdimensionnée n'est pas une certitude : c'est une imprécision qui se présente comme une
précision.

**Incertitude.** Elle est décrite selon ce qui est connu : données, paramètres, structure du
modèle, conditions initiales, approximation numérique, scénario. La forme est adaptée au
contexte : intervalle, distribution, scénarios, borne, sensibilité, ou conclusion qualitative. Une
distribution sophistiquée n'est pas requise si les données ne la justifient pas. Les modèles
couplés signalent les données, hypothèses et erreurs partagées ; des sorties dépendantes ne sont
pas des confirmations indépendantes.

**Abstention.** Un système déclare ce qu'il ne sait pas faire. Chaque étude déclare ses
conditions d'abstention, d'arrêt et d'invalidation ; chaque sortie peut porter une politique
d'abstention explicite. Une valeur absente porte la raison de son absence et n'est jamais zéro.
L'abstention est une qualité, pas un échec : un système qui ne s'abstient jamais sur des
données hors domaine est un système dont les performances hors domaine ne veulent rien dire.

## 7. Identifiabilité

Avant d'interpréter fortement une estimation, vérifier que les données permettent réellement de
distinguer les états ou paramètres possibles. Si plusieurs explications restent compatibles,
préserver l'ambiguïté plutôt que de choisir arbitrairement une valeur précise. La précision
numérique n'est ni l'identifiabilité ni la validité.

## 8. Résultats inconclusifs

Une conclusion inconclusive est un résultat valide. Elle peut refléter des observations
insuffisantes, un état non identifiable, une référence inadéquate, une faible puissance
statistique ou un domaine trop étroit. Elle se rapporte comme telle, avec sa cause. L'absence de
preuve ne se remplace jamais par un proxy non justifié.

Tout essai lancé est enregistré, y compris son erreur, ses variantes négatives et son abandon.

## 9. Garde-fou contre la surcomplexité

Aucune métrique, méthode, couche, registre ou artefact n'est ajouté sans montrer quelle
affirmation il aide à tester. La baseline simple est privilégiée lorsqu'elle répond à la question.
Les exigences de preuve sont proportionnées à l'usage et au risque de la décision visée.

La doctrine choisit le mode de preuve. Elle ne crée pas un second système d'évaluation, ni une
validation qui duplique la logique scientifique.
