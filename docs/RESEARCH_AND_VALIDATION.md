# TORNE — Recherche et validation

**Doctrine de preuve**
**Statut : principes applicables.** Le dépôt contient un modèle, son exécution, son évaluation et une preuve
rejouable ; il ne contient **aucun résultat scientifique**. La distinction est nette : ce document dit comment
une affirmation doit être testée, et le dépôt ne prétend encore rien avoir démontré sur le monde réel.

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

### 2.2 Exploration et confirmation : deux régimes, pas deux niveaux de rigueur

Une exploration et une confirmation ne diffèrent pas par le soin apporté, mais par ce qui est **consommé**.

- **En exploration**, la fenêtre regardée est **consommée** pour toutes les hypothèses du même ensemble. Une règle
  trouvée en la regardant ne pourra plus être confirmée sur ces données : elle devra l'être sur des données
  **neuves**.
- **En confirmation**, la fenêtre est intacte au moment où la règle est formulée, et le test se fait sur des
  données qui n'ont pas servi à la trouver.

Trois conséquences pratiques :

1. **Un regard brûle.** Chercher dans une période, c'est renoncer à y établir quoi que ce soit de neuf. Une
   exploration mal bornée réduit d'autant la confirmation possible.
2. **Le meilleur des variantes se lit rétréci.** Quand K variantes sont essayées sur les mêmes données, la
   meilleure est un estimateur biaisé vers le haut. Elle se lit ensuite **rétréci** — l'estimation est ramenée
   vers zéro par le rétrécissement empirique — pour contrer la malédiction du gagnant.
3. **La correction de multiplicité vient après**, et s'applique à la famille entière des variantes essayées,
   jamais à la seule variante retenue.

Un dépôt qui ne distingue pas ces deux régimes produit des résultats qui ne sont pas confirmables, même quand
les chiffres sont bons.

### 2.3 La multiplicité est fixée avant l'observation

Le nombre d'hypothèses que l'on a regardées fait partie de la **méthode**, et il se déclare avant qu'on regarde
les résultats. Deux règles, non négociables :

1. **La correction est fixée à l'avance.** La méthode de correction — et son niveau — est choisie dans le
   pré-enregistrement, pas après avoir vu les p-valeurs.
2. **Choisir la correction après coup, en fonction du résultat, n'est pas une correction.** C'est de
   l'**α-shopping**, et le résultat n'est plus interprétable.

Le choix de la méthode doit correspondre à ce que la structure des données permet réellement :

| Structure des données | Ce qui est garanti | Ce qui ne l'est pas |
|---|---|---|
| hypothèses indépendantes | le contrôle du taux de faux positifs, par famille | rien au-delà |
| dépendance arbitraire (e-values, LOND) | le contrôle du FDR sous dépendance arbitraire | que l'hypothèse porte sur l'**espérance conditionnelle** de chaque unité, et que les unités corrélées soient **agrégées par grappe** avant le test |
| rétrécissement par bootstrap | le FDR sous indépendance, ou sous PRDS | **rien** sous dépendance arbitraire |

La troisième ligne est la nuance qu'on perd le plus souvent : un rétrécissement bootstrap « corrige » la
multiplicité sous des conditions plus étroites que l'e-value qu'il remplace souvent. Et l'agrégation par grappe
n'est pas une option : sans elle, aucune de ces garanties ne tient.

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

**Ces six affirmations sont la nature d'une affirmation scientifique, et rien d'autre.** Elles ne disent rien
du **statut opérationnel** d'un produit de connaissance : un produit utilisable peut porter une estimation, et un
produit inconclusif peut porter une reconstruction. Les deux notions sont distinctes, et l'une ne se déduit pas
de l'autre (`docs/CONTRATS_FONDAMENTAUX.md` §4.10).

Le vocabulaire de nature du dépôt est plus étroit que ces six affirmations : une grandeur dérivée y est
`estimated`, `reconstructed`, `predicted`, `simulated` ou `derived`. L'explication et la causalité ne sont pas
des natures de grandeur, mais des **niveaux d'affirmation** : ils se portent dans le rapport, pas dans le type
du produit.

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

## 10. Le pré-enregistrement, et ce qu'il reste à outiller

Un pré-enregistrement n'est pas un document que l'on écrit pour s'en acquitter : c'est un **verrou** qui rend le
résultat interprétable. Un pré-enregistrement existe dès qu'il contient, figés avant l'observation :

- l'affirmation testée, le domaine, la période, les données ;
- la méthode, ses paramètres, et la règle de calcul ;
- la référence ;
- **la règle de correction de multiplicité** ;
- les critères de réussite, d'échec et d'abandon.

Le dépôt en tient un : `docs/PRE-ENREGISTREMENT-001.md`. Il est **écrit**, pas encore **outillé**.

Trois contrôles manquent aujourd'hui, et tant qu'ils manquent, le lien entre une expérience et son résultat
reste humain :

| # | Contrôle manquant | Ce qu'il détecterait |
|---|---|---|
| 1 | **Un rapport produit par un pré-enregistrement** — aucun rapport ne peut être publié sans le pré-enregistrement qui l'autorise. | Un résultat sans protocole, ou un protocole écrit après coup. |
| 2 | **Un amendement daté et commité avant le calcul** — tout changement du protocole porte une date et un commit, et précède le calcul. | Un protocole réécrit après avoir vu les données. |
| 3 | **Un pré-enregistrement sans rapport** — une expérience ouverte et jamais close est signalée. | Une expérience abandonnée en silence, ou une conclusion tirée ailleurs. |

Ces trois contrôles sont peu coûteux, et ils rendent le dispositif vérifiable **par l'exécution** et non par la
mémoire.

## 11. Nommer une méthode pour ce qu'elle est

Une méthode mal nommée continue de faire du mal tant qu'elle porte le nom d'une autre.

Le découpage temporel de l'évaluation en est l'exemple : ce que le dépôt implémente n'est pas une fenêtre
glissante, mais un découpage **cumulatif** — le bloc d'entraînement de chaque pli contient **toutes** les valeurs
antérieures, pas une fenêtre mobile. L'appeler « walk-forward » sans préciser lequel des deux est écrit induit en
erreur sur ce que l'évaluation mesure, et donc sur ce qu'elle prouve.

La règle : **le nom dit ce que la méthode fait, et le document de référence dit comment**. Si les deux ne peuvent
pas être confondus, le nom est trop général.

## 12. Quatre axes, et trois verdicts qui ne se confondent pas

Une affirmation scientifique traverse quatre questions distinctes. Les confondre est la source d'erreur la plus
fréquente en évaluation : un « non » mal situé devient soit un faux négatif, soit un refus de répondre.

| Axe | Question | Vocabulaire | Propriétaire |
|---|---|---|---|
| **1 — validité intrinsèque** | la valeur est-elle exploitable **en soi** ? | `VALID` · `MISSING` · `INVALID` | socle et adaptateur |
| **2 — applicabilité** | ce produit s'applique-t-il **à ce contexte** ? | `COMPATIBLE` · `INCOMPATIBLE` · `INDETERMINATE` | dossier d'évaluation |
| **3 — verdict d'affirmation** | que permettent les preuves **sur cette affirmation** ? | `NOT_EVALUATED` · `SUPPORTED` · `REFUTED` · `INCONCLUSIVE` | protocole d'évaluation |
| **4 — statut de produit** | cet objet publié **peut-il être utilisé** ? | `USABLE` · `DEGRADED` · `WITHDRAWN` · `INCONCLUSIVE` | contrat de publication |

Les axes 1 et 4 existent dans le dépôt (`src/torne/contracts/`). Les axes 2 et 3 sont ceux qui manquent, et ils
ne sont pas redondants : l'axe 2 porte sur la **relation entre une capacité et un contexte**, l'axe 3 sur **ce que
les preuves établissent sur une proposition**. Une affirmation peut être `SUPPORTED` dans son domaine et
`REFUTED` pour un transfert ; un produit peut être `USABLE` alors que son applicabilité ailleurs est
`INDETERMINATE`.

### 12.1 Les trois verdicts d'applicabilité, et la règle de non-contamination

| État des prédicats | Verdict | Ce que l'évaluation déclare |
|---|---|---|
| tous satisfaits | `COMPATIBLE` | l'applicabilité est **établie** pour ce contexte |
| au moins un violé | `INCOMPATIBLE` | la non-transportabilité est **établie** — et **dite** |
| aucun violé, au moins un inconnu | **`INDETERMINATE`** | la comparabilité n'est établie **ni dans un sens ni dans l'autre** |

> **Non-contamination : un constat « hors domaine » ne peut être produit que par un verdict `INCOMPATIBLE`.** Un
> verdict `INDETERMINATE` produit une **abstention**, jamais un constat d'hors-domaine.

La règle jumelle ferme l'autre sens du raccourci : **un prédicat n'est jamais « violé » par la seule absence de
preuve**. « Satisfait » exige une preuve positive, « violé » exige une preuve de la violation ; ce qui n'a
l'une ni l'autre est **inconnu**.

Conséquence de programme : l'abstention devient une **sortie normale et valorisée**. Un référentiel inconnu ne
produit pas une comparaison approximative présentée comme valide : il produit une abstention documentée.

### 12.2 Ce qui est porté où

Les prédicats d'applicabilité vivent dans le **protocole d'évaluation**, pas comme des champs obligatoires de
chaque produit. Un produit de connaissance porte une **référence** à l'évaluation qui l'a établi, et une
**synthèse**. Les huit prédicats ne deviennent pas huit colonnes d'un JSON de produit : un produit ne porte pas
une grille qu'il ne remplit pas lui-même.

### 12.3 Une réfutation est une production de connaissance

**Le statut d'un produit n'est jamais dégradé parce qu'une applicabilité a été réfutée.** L'axe 3 est indépendant
de l'axe 4 : un produit `USABLE` dont l'applicabilité ailleurs est `REFUTED` **reste `USABLE`** ; c'est le
verdict `REFUTED` qui est publié, et lui seul.

« Réfuté » et « inconclusif » ne sont pas synonymes, et ne doivent pas le devenir : une réfutation est un
**résultat**, un inconclusif est une **absence de résultat**. Les confondre revient à ne pas pouvoir dire qu'une
méthode ne se transfère pas.

### 12.4 Le dénominateur, en sept éléments

« Combien de données ? » n'est pas une question à une seule réponse. Un dénominateur comporte sept éléments :

1. **population visée** ;
2. **unité d'observation indépendante** ;
3. **observations disponibles** ;
4. **observations effectivement utilisées** ;
5. **exclusions et leurs motifs** ;
6. **taille effective sous dépendance** ;
7. **dénominateur de la généralisation**.

La taille effective est un **diagnostic** : elle ne remplace jamais le nombre d'observations, et les épisodes ou
groupes restent l'unité de généralisation.

La distinction que ces sept éléments rendent visible : **précision de l'observation** et **force de la preuve de
transférabilité** sont deux choses. Dans un leave-one-basin-out, 500 000 relevés hydrométriques ne sont pas
500 000 systèmes physiques indépendants. Un produit peut être extrêmement précis sur ses observations et très
faiblement prouvé pour sa transférabilité — et aucun des deux ne doit masquer l'autre.

### 12.5 Les trois règles fondatrices

1. **Une plateforme, plusieurs physiques.** TORNE partage son épistémologie, sa provenance, sa temporalité, ses
   procédures d'évaluation et ses capacités computationnelles ; chaque domaine conserve sa physique, ses
   variables, ses juges et ses dénominateurs.
2. **L'inconnu ne devient jamais une certitude par commodité.**
3. **Une réfutation est une production de connaissance.**

Il en découle une décision de programme : **TORNE ne cherche pas un modèle universel du monde.** Il cherche une
plateforme capable de produire, d'évaluer et de réutiliser des connaissances scientifiques issues de plusieurs
physiques, sans confondre leurs structures. La généralisation devient une **affirmation testable**, jamais une
promesse implicite.


## 12. Quatre axes, et trois verdicts qui ne se confondent pas

Une affirmation scientifique traverse quatre questions distinctes. Les confondre est la source d'erreur la plus
fréquente en évaluation : un « non » mal situé devient soit un faux négatif, soit un refus de répondre.

| Axe | Question | Vocabulaire | Propriétaire |
|---|---|---|---|
| **1 — validité intrinsèque** | la valeur est-elle exploitable **en soi** ? | `VALID` · `MISSING` · `INVALID` | socle et adaptateur |
| **2 — applicabilité** | ce produit s'applique-t-il **à ce contexte** ? | `COMPATIBLE` · `INCOMPATIBLE` · `INDETERMINATE` | dossier d'évaluation |
| **3 — verdict d'affirmation** | que permettent les preuves **sur cette affirmation** ? | `NOT_EVALUATED` · `SUPPORTED` · `REFUTED` · `INCONCLUSIVE` | protocole d'évaluation |
| **4 — statut de produit** | cet objet publié **peut-il être utilisé** ? | `USABLE` · `DEGRADED` · `WITHDRAWN` · `INCONCLUSIVE` | contrat de publication |

Les axes 1 et 4 existent dans le dépôt (`src/torne/contracts/`). Les axes 2 et 3 sont ceux qui manquent, et ils
ne sont pas redondants : l'axe 2 porte sur la **relation entre une capacité et un contexte**, l'axe 3 sur **ce que
les preuves établissent sur une proposition**. Une affirmation peut être `SUPPORTED` dans son domaine et
`REFUTED` pour un transfert ; un produit peut être `USABLE` alors que son applicabilité ailleurs est
`INDETERMINATE`.

### 12.1 Les trois verdicts d'applicabilité, et la règle de non-contamination

| État des prédicats | Verdict | Ce que l'évaluation déclare |
|---|---|---|
| tous satisfaits | `COMPATIBLE` | l'applicabilité est **établie** pour ce contexte |
| au moins un violé | `INCOMPATIBLE` | la non-transportabilité est **établie** — et **dite** |
| aucun violé, au moins un inconnu | **`INDETERMINATE`** | la comparabilité n'est établie **ni dans un sens ni dans l'autre** |

> **Non-contamination : un constat « hors domaine » ne peut être produit que par un verdict `INCOMPATIBLE`.** Un
> verdict `INDETERMINATE` produit une **abstention**, jamais un constat d'hors-domaine.

La règle jumelle ferme l'autre sens du raccourci : **un prédicat n'est jamais « violé » par la seule absence de
preuve**. « Satisfait » exige une preuve positive, « violé » exige une preuve de la violation ; ce qui n'a
l'une ni l'autre est **inconnu**.

Conséquence de programme : l'abstention devient une **sortie normale et valorisée**. Un référentiel inconnu ne
produit pas une comparaison approximative présentée comme valide : il produit une abstention documentée.

### 12.2 Ce qui est porté où

Les prédicats d'applicabilité vivent dans le **protocole d'évaluation**, pas comme des champs obligatoires de
chaque produit. Un produit de connaissance porte une **référence** à l'évaluation qui l'a établi, et une
**synthèse**. Les huit prédicats ne deviennent pas huit colonnes d'un JSON de produit : un produit ne porte pas
une grille qu'il ne remplit pas lui-même.

### 12.3 Une réfutation est une production de connaissance

**Le statut d'un produit n'est jamais dégradé parce qu'une applicabilité a été réfutée.** L'axe 3 est indépendant
de l'axe 4 : un produit `USABLE` dont l'applicabilité ailleurs est `REFUTED` **reste `USABLE`** ; c'est le
verdict `REFUTED` qui est publié, et lui seul.

« Réfuté » et « inconclusif » ne sont pas synonymes, et ne doivent pas le devenir : une réfutation est un
**résultat**, un inconclusif est une **absence de résultat**. Les confondre revient à ne pas pouvoir dire qu'une
méthode ne se transfère pas.

### 12.4 Le dénominateur, en sept éléments

« Combien de données ? » n'est pas une question à une seule réponse. Un dénominateur comporte sept éléments :

1. **population visée** ;
2. **unité d'observation indépendante** ;
3. **observations disponibles** ;
4. **observations effectivement utilisées** ;
5. **exclusions et leurs motifs** ;
6. **taille effective sous dépendance** ;
7. **dénominateur de la généralisation**.

La taille effective est un **diagnostic** : elle ne remplace jamais le nombre d'observations, et les épisodes ou
groupes restent l'unité de généralisation.

La distinction que ces sept éléments rendent visible : **précision de l'observation** et **force de la preuve de
transférabilité** sont deux choses. Dans un leave-one-basin-out, 500 000 relevés hydrométriques ne sont pas
500 000 systèmes physiques indépendants. Un produit peut être extrêmement précis sur ses observations et très
faiblement prouvé pour sa transférabilité — et aucun des deux ne doit masquer l'autre.

### 12.5 Les trois règles fondatrices

1. **Une plateforme, plusieurs physiques.** TORNE partage son épistémologie, sa provenance, sa temporalité, ses
   procédures d'évaluation et ses capacités computationnelles ; chaque domaine conserve sa physique, ses
   variables, ses juges et ses dénominateurs.
2. **L'inconnu ne devient jamais une certitude par commodité.**
3. **Une réfutation est une production de connaissance.**

Il en découle une décision de programme : **TORNE ne cherche pas un modèle universel du monde.** Il cherche une
plateforme capable de produire, d'évaluer et de réutiliser des connaissances scientifiques issues de plusieurs
physiques, sans confondre leurs structures. La généralisation devient une **affirmation testable**, jamais une
promesse implicite.

