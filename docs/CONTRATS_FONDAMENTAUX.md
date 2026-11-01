# TORNE — Contrats fondamentaux

**Objets, temporalité, invariants**
**Statut : contrat.** Ce document fixe des responsabilités, des invariants et des formes vérifiables. Il ne
décrit aucun schéma de stockage, aucun connecteur, aucune table, aucun service. Tout ce qui dépend d'une source
précise est explicitement différé (§6).

---

## 0. Ce que ce document est, et ce qu'il n'est pas

Il est **un contrat**, au sens où il dit ce qui doit rester vrai quoi qu'il arrive au code. Il existe pour que
trois choses ne dépendent plus du style de l'implémenteur :

- ce qu'un objet garantit, et ce qu'il ne garantit pas ;
- à quel instant un fait est devenu vrai, connu et acquis ;
- quelle question un test doit pouvoir poser pour constater qu'une règle tient.

Il n'est **pas** une architecture de stockage. Il ne dit ni où vit une observation, ni sous quelle forme, ni
dans quel format elle circule. Le programme interdit d'imposer une conception générique avant de connaître les
données réellement disponibles (`docs/PROGRAMME.md`) ; ce document respecte cette interdiction en distinguant,
à chaque fois, ce qui est **contractuel** de ce qui est **différé**.

Il n'est **pas** une spécification d'implémentation. Le dépôt contient désormais une forme exécutable de ces
contrats, dans `src/torne/contracts/` et `src/torne/acquisition/` : ce document reste la **source**, le code en
est l'application, et il ne lui ajoute aucune brique. Quand le code et ce document divergent, c'est le document
qui a tort, et il est corrigé.

### 0.1 Ce qui est vérifié, et comment on le sait

Les affirmations de ce document sont de trois natures, et le lecteur doit pouvoir les distinguer :

| Nature | Ce qui la fonde | Comment on le vérifie |
|---|---|---|
| **Norme** | une décision prise par le projet | la décision est écrite ici, et son application est testée |
| **Pratique** | le comportement réel d'une source ou d'une dépendance | une observation, datée, rejouable |
| **Héritage** | le comportement d'un dépôt d'origine | le dépôt, le commit et le chemin exact du fichier, cités en tête de module |

Une affirmation d'héritage cite le dépôt, le commit et le chemin. Un dépôt d'origine n'est **pas** une
dépendance de TORNE : il n'est ni installé, ni importé, ni consultable depuis ce dépôt. Il n'est cité que pour
dire d'où vient une brique reprise, et pour tracer les écarts délibérés.

---

## 1. Le vocabulaire

### 1.1 Les cinq objets

Ce sont **cinq responsabilités distinctes**, pas cinq couches, pas cinq tables, pas cinq services. Une
implémentation peut les loger dans un même module, dans une même table, ou dans des processus distincts : cela ne
change rien aux obligations ci-dessous. Ce qui les distingue est la **question** à laquelle chacun répond
seul.

| Objet | Question à laquelle il répond seul |
|---|---|
| **Source** | D'où vient l'information, et sous quelles conditions était-elle disponible ? |
| **Raw Evidence** | Quel contenu brut a effectivement été récupéré, et est-ce encore là, intact ? |
| **Observation** | Qu'a mesuré ou rapporté la source, à cet instant et dans ces termes ? |
| **Derived Variable** | Que vaut la grandeur calculée à partir de ces observations ? |
| **Knowledge Product** | Quel résultat structuré, versionné et réutilisable en est sorti ? |

### 1.2 Les trois dimensions temporelles

| Dimension | Question |
|---|---|
| **VALID_TIME** | Quand le phénomène physique existe-t-il, ou quand le fait décrit est-il vrai ? |
| **KNOWN_AT** | Quand l'information devient-elle connue ou disponible **dans sa source** ? |
| **INGESTED_AT** | Quand TORNE l'acquiert-elle effectivement ? |

Les trois sont **independantes** et **non interchangeables**. Aucun champ ne peut servir de substitut d'un autre.

### 1.3 Les relations

Les relations sont une **lignée de données**, pas un pipeline d'étapes obligatoires.

```text
Source ──1:N──> Raw Evidence ──1:N──> Observation ──N:M──> Derived Variable ──N:M──> Knowledge Product
                                             ▲                      │                        │
                                             └──────────────────────┴────────────────────────┘
```

- Une **Source** a plusieurs **Raw Evidence** : une même source produit des contenus au fil du temps, sous des
  clés stables dans cette source.
- Un **Raw Evidence** donne plusieurs **Observation** : le décodage est déterministe et rejouable.
- Une **Observation** alimente plusieurs **Derived Variable** ; une **Derived Variable** consomme plusieurs
  observations, et peut consommer d'autres **Derived Variable**.
- Une **Knowledge Product** consomme des observations et des variables dérivées, et en cite la lignée complète.

Ce qui n'est **pas** imposé : qu'un produit de connaissance doive passer par tous les objets. Un produit peut
citer une preuve brute directement dans sa lignée ; une variable dérivée peut être produite à partir d'une
seule observation. La chaîne est un **ordre de dépendance**, pas une obligation de passage.

---

## 2. Les cinq objets

### 2.1 Source

**Responsabilité.** La Source est le seul garant de l'**identité** et des **conditions de disponibilité** d'une
information : institution productrice, jeu de données, point d'accès, document ou système. Elle décrit ce que
la source est, ce qu'elle publie, selon quelles unités, avec quelle politique de révision, et sous quelles
conditions d'accès.

**Elle garantit** que l'origine de toute information est nommée, que les conditions de son usage sont
consignées, et qu'un changement de format ou de politique de la source est visible comme un fait daté.

**Invariants.** Une Source est identifiée de façon stable et jamais fusionnée avec une autre. Sa politique de
révision, ses unités, son fuseau et son statut de qualité sont des propriétés de la **source**, pas des
propriétés d'une observation isolée. Toute information acquise est rattachée à une Source déclarée : une
acquisition dont la source n'est pas déclarée est un fait à corriger, pas une donnée à tolérer.

**Elle ne garantit pas** : que la source publie ce qu'elle annonce, ni à quelle date, ni que ses données sont
complètes ou exactes, ni que ses données ne seront pas révisées. Elle ne garantit pas non plus que la source
existe encore demain — la disparition d'une source est un risque que la provenance doit rendre visible
(`README.md`).

### 2.2 Raw Evidence

**Responsabilité.** Le Raw Evidence est le seul garant de la **conservation de la preuve brute** : le contenu
réellement récupéré, tel quel, adressable, vérifiable et jamais perdu. Il est la seule vérité d'origine : tout
le reste est reconstructible à partir de lui.

**Il garantit** que ce qui a été reçu est encore lisible, que son empreinte est stable, que son contenu n'a pas
été modifié après coup, et qu'une réponse « il n'y a rien ici » est conservée comme telle — avec sa date
d'acquisition — au lieu de disparaître.

**Invariants.** Un contenu brut est **écrit une fois**, sous son empreinte ; il n'est jamais réécrit. Quand le
contenu d'une clé change, c'est une **version nouvelle**, l'ancienne restant lisible et inchangée. Un contenu
re-collecté identique est idempotent. Une acquisition est consignée au journal, y compris son échec.

**Il ne garantit pas** : que le contenu brut soit compris, ni qu'il soit suffisant pour produire l'observation
que l'on voudra. Il ne garantit pas que la source ait renvoyé ce qu'elle aurait dû renvoyer. Il ne porte pas
l'interprétation : l'analyse n'y touche jamais, il se laisse re-parser.

> **Le brut ne s'écrase pas silencieusement** (`docs/PROGRAMME.md`). La forme vérifiable est l'existence d'un
> second enregistrement de version, jamais une mutation de l'ancien.

### 2.3 Observation

**Responsabilité.** L'Observation est le seul garant du **contenu sémantique** : une mesure ou une information
telle que fournie par sa source — sa valeur, son unité, son référentiel spatial, son statut de qualité, son
précision, et son appartenance temporelle.

**Elle garantit** que ce qui est affirmé est exactement ce que la source a dit, dans les termes de la source ;
que la valeur est reconstituable depuis la preuve brute ; que son statut (provisoire, approuvée, estimée) est
porté avec elle ; et qu'une absence est une absence **qualifiée**, jamais un zéro.

**Invariants.** Toute observation porte ses trois dimensions temporelles, ou l'état explicite de leur absence
(§3). Toute observation porte son unité et son référentiel spatial. Une observation absente porte une
`missing_reason` issue d'une liste contrôlée (§3.8). Une observation est rattachée à un Raw Evidence
identifiable, qui permet de la re-dériver.

**Elle ne garantit pas** : que la mesure soit juste, ni que la source soit exhaustive, ni que la valeur soit
définitive. Une observation provisoire est une observation complète, pas une observation dégradée. Elle ne
garantit pas non plus que l'observation soit la bonne unité d'analyse : une moyenne journalière et une mesure
horaire sont deux observations de granularités différentes, pas deux versions de la même observation.

### 2.4 Derived Variable

**Responsabilité.** La Derived Variable est le seul garant de la **règle de calcul** : une valeur calculée ou
estimée à partir d'une ou plusieurs observations, dont la méthode, les paramètres, les entrées et l'incertitude
sont connus.

**Elle garantit** que la valeur est reproductible à partir des observations consommées, que la règle de calcul
est identifiée et versionnée, et que la variable ne se présente jamais comme une observation de source.

**Invariants.** Une variable dérivée cite l'ensemble de ses entrées, transitivement jusqu'aux preuves brutes. Elle
porte sa propre temporalité : `VALID_TIME` est celui du phénomène qu'elle décrit ; `KNOWN_AT` et `INGESTED_AT`
sont ceux **du calcul**, jamais ceux de la source. Elle porte une qualification d'incertitude adaptée à ce qui
est réellement connu (`docs/RESEARCH_AND_VALIDATION.md` §6).

> **Point de fuite principal.** Une variable calculée le 21 octobre à partir d'observations publiées le 18 octobre
> n'est connue que du 21 octobre. Lui attribuer le `KNOWN_AT` de ses entrées fait passer une reconstruction
> postérieure pour une reconstruction disponible en temps réel.

**Elle ne garantit pas** : que le calcul soit correct, ni que les entrées soient les bonnes, ni que la variable
ait un sens physique. Elle ne garantit pas non plus la stabilité : deux exécutions sur les mêmes entrées
donnent le même résultat **seulement si** la règle de calcul, les paramètres et l'environnement sont identiques.

### 2.5 Knowledge Product

**Responsabilité.** Le Knowledge Product est le seul garant de la **version publiée** : un résultat structuré et
versionné, produit par un modèle ou une reconstruction, destiné à être réutilisé, audité ou consommé
indépendamment.

**Il garantit** une version, une date d'étatisation, une provenance complète jusqu'aux sources, un domaine de
validité, une incertitude qualifiée et un statut explicite : utilisable, dégradé, retiré, ou résultat
inconclusif (`docs/ARCHITECTURE.md` §4).

**Invariants.** Un produit n'est publiable que si sa lignée est complète et vérifiable. Un produit publié ne se
réécrit pas : une correction produit une **version nouvelle**, et l'ancienne reste consultable. Un produit
inconclusif est un résultat valide, rapporté comme tel, avec sa cause
(`docs/RESEARCH_AND_VALIDATION.md` §8). Un produit ne cite pas d'observation qui n'était pas admissible au
moment où il a été établi ; et son instant d'établissement ne précède ni la production du résultat qu'il
publie, ni l'établissement de l'enregistrement qui le porte : **un produit ne précède pas ce qu'il publie**.

**Il ne garantit pas** : que le produit soit vrai, ni qu'il reste vrai, ni qu'il soit réutilisable hors de son
domaine de validité. Il n'est pas un registre et ne catalogue pas l'existant
(`docs/ARCHITECTURE.md` §4). Il ne valide pas rétroactivement les modèles amont.

---

## 3. La sémantique temporelle

### 3.1 Les trois dimensions, et ce qui n'en est pas une

`docs/ARCHITECTURE.md` §6.2 évoque « la distinction canonique entre temps de validité, temps de publication,
temps de réception, temps de disponibilité et temps d'usage ». Ce contrat **n'en stocke que trois**, parce que
les autres notions sont soit dérivables, soit des paramètres de requête. Stocker une cinquième dimension
introduirait une redondance que rien ne gouverne.

| Notion de l'architecture | Traitement ici |
|---|---|
| Temps de validité | **Dimension stockée** : `VALID_TIME`. |
| Temps de publication | **Dimension stockée** : `KNOWN_AT`. |
| Temps de réception | **Dimension stockée** : `INGESTED_AT`. |
| Temps de disponibilité | **Fonction dérivée** : `usable_at`, jamais un champ libre (§3.2). |
| Temps d'usage | **Paramètre de requête** : l'instant de la décision, jamais porté par la donnée. |

Deux précisions qui affinent l'architecture :

- **La date déclarée par l'émetteur** n'est pas une sixième dimension. C'est une métadonnée de la source, qui
  alimente `KNOWN_AT` quand la source permet de l'établir, et qui doit rester distinguée de l'instant de
  *mise à disposition* quand la source les distingue (certains émetteurs horodatent un document qu'ils
  rendent disponible plus tard). Le contrat impose que les deux soient **nommés séparément** quand la source
  les fournit séparément ; leur valeur par source est différée (§6).
- **L'instant de décision** (« qu'est-ce qu'on savait à *t* ? ») n'est jamais stocké avec la donnée : c'est le
  `asof` de la requête. Une donnée qui porterait son propre instant d'usage serait un contresens.

### 3.2 Le point de vue à la décision

La règle centrale, sans ambiguïté :

> Une information est **utilisable** à l'instant *t* si et seulement si elle était **connue dans sa source**
> au plus tard à *t* **et** que TORNE l'avait **acquise** au plus tard à *t*.

Autrement dit, l'instant d'utilisabilité est le **maximum** des deux :

```text
usable_at = max(KNOWN_AT, INGESTED_AT)
```

Trois conséquences, chacune vérifiable :

1. **`usable_at` n'est jamais stocké.** C'est une fonction des deux dimensions, calculée à la requête. Un champ
   `usable_at` stocké serait une troisième copie susceptible de diverger.
2. **Une information acquise avant d'être connue est un cas d'erreur, pas un cas d'exploit.** Si
   `INGESTED_AT < KNOWN_AT`, c'est que l'une des deux est fausse : la donnée est douteuse et doit être signalée
   comme telle, pas exploitée.
3. **L'ordre naturel est `VALID_TIME` ≤ `KNOWN_AT` ≤ `INGESTED_AT`**, avec une exception nommée : le
   réimport d'une archive historique (§3.3) où `INGESTED_AT` est la date d'acquisition **d'origine**, et non
   celle du réimport.

La règle est identique, mot pour mot, à celle d'`athanor.kernel.clock`
(`athanor/src/athanor/kernel/clock.py:9-12`) : « un point est utilisable à `asof` <=>
`usable_from(published_at, known_at) <= asof`, avec `usable_from = max(published_at, known_at)`. Un point sans
`known_at` n'est jamais utilisable. » Le contrat reprend cette règle ; il en **change l'interprétation des
noms**, ce qui est le point 3.1 de §5.

### 3.3 Instants, dates civiles, intervalles, séries

**Instants.** Un instant est un point du temps. Il est stocké en **UTC**, en ISO 8601 avec décalage explicite.
Un instant sans fuseau est **interdit** : il n'est pas « supposé UTC », il est refusé à l'entrée. La conversion
vers UTC a lieu **une seule fois**, au moment du décodage, et elle est consignée.

**Dates civiles.** Une date civile est un jour du calendrier, sans heure. C'est un type distinct d'un instant,
et les deux ne se convertissent pas l'un en l'autre sans décision explicite. Une date civile conservée est
toujours accompagnée du contexte civil qui la rend interprétable (le calendrier, et le fuseau quand elle
résultera d'un regroupement). Une date civile ne se dégrade jamais en instant par défaut : le passage
date → instant 00:00 est une **décision de source**, pas une commodité d'implémentation (§6).

**Intervalles.** Un intervalle est une paire `[début, fin)`, **semi-ouverte**, à bornes explicites, et
toujours de même granularité interne. Une fin-exclusive évite qu'une observation discrète servant à caractériser
une période n'appartienne à deux périodes voisines. Un intervalle dont les bornes sont inconnues n'est pas un
intervalle : c'est une absence qualifiée. Un intervalle ne se décompose en instants que si la source l'y autorise.

**Séries temporelles.** Une série est un **ensemble d'observations**, jamais une valeur. Chaque point garde son
propre statut, sa propre précision, sa propre révision. Une série **n'hérite pas** du statut de son dernier
point : une série dont les 90 derniers points sont approuvés et dont les 10 premiers sont provisoires reste une
série mixte, et le contrat exige qu'elle soit qualifiée comme telle.

**Regroupement.** Une agrégation (une moyenne journalière, un total hebdomadaire) produit une **observation
nouvelle**, pas une observation dérivée : sa valeur est celle d'une source. Elle porte donc son propre lignage,
ses propres dimensions temporelles et son propre statut.

### 3.4 Fuseaux horaires

La règle est en trois temps, et elle est **unique** :

1. Une date civile est interprétée avec le fuseau que **la source déclare** — jamais avec celui du poste, ni
   celui du contexte d'exécution.
2. La conversion vers UTC se fait à la frontière : au décodage, une fois, et le résultat est conservé.
3. L'instant civil d'origine est conservé à côté du résultat.

Un test de non-régression simple : la même donnée brute rejouée sur une machine dans un autre fuseau donne le
même résultat. C'est la forme vérifiable de « le fuseau ne dépend pas de l'exécutant ».

TORNE **n'hérite pas** des règles de fuseau de l'ancien BORÉE. `boree/src/boree/temps.py:86-95` (les fonctions
`horaire` et `local`, qui moyennent les quarts d'heure et fusionnent les deux heures UTC tombant sur 2 h locale)
est un pattern générique et testé, mais son **contenu** est lié au marché électrique et hors périmètre
(§5). Ce que TORNE en retient, c'est l'idée qu'une heure locale peut être ambiguë — et
donc que la conversion doit être faite et conservée, pas recalculée à la lecture.

### 3.5 Précision variable

Deux sources neymes pas la même chose par « précision », et le contrat les sépare :

- **La résolution déclarée** : ce que la source dit de son pas de mesure (horaire, quotidien, hebdomadaire).
- **L'incertitude réelle** : ce qui est connu de l'exactitude de la valeur.

Une valeur dont la résolution est horaire porte une incertitude qui n'est pas nulle simplement parce que la
source ne la publie pas. Le contrat impose qu'une observation **sans incertitude qualifiée** le dise
explicitement, plutôt que de laisser croire à une précision que personne n'a établie. La forme retenue est
l'adaptation de la forme à ce qui est connu (`docs/RESEARCH_AND_VALIDATION.md` §6) : intervalle,
distribution, scénario, borne, sensibilité, ou conclusion qualitative.

L'arrondi de présentation **n'est pas** une incertitude : arrondir à l'affichage ne réduit pas l'incertitude
de la valeur stockée.

### 3.6 Observations révisées

**Règle centrale : la révision ne réécrit pas l'historique.**

Une révision crée une **version nouvelle** de l'observation, pas la mutation de l'ancienne :

- même clé naturelle (source + entité + temps valide + grandeur) ;
- `KNOWN_AT` et `INGESTED_AT` postérieurs à ceux de la version qu'ils remplacent ;
- un lien explicite vers la version antérieure, pour que la chaîne de révision soit parcourable ;
- un statut propre (une révision peut passer une observation de provisoire à approuvée).

La version antérieure **reste lisible**. C'est ce qui rend la reconstitution point-in-time possible : interroger
l'état au 15 octobre rend la version qu'on croyait ce jour-là, pas celle du 25 octobre.

Une observation révisée est donc **deux observations**, pas une observation et son historique. Les agréger, les
moyener ou n'en garder que la dernière est une faute de reconstitution, pas une simplification.

**Ce que la révision ne dit pas.** Une révision prouve qu'une information a changé ; elle ne prouve pas **quand
ni pourquoi** elle a changé, sauf si la source l'indique. Une source qui ne date pas ses révisions ne permet pas
de reconstituer la chronologie des révisions : le contrat l'exige alors comme **absence qualifiée** (§3.8), et
la question de savoir si l'historique des révisions est reconstituable devient une question de source, pas de
conception (§6).

### 3.7 Informations provisoires

Une information provisoire est **une information**, pas une absence et pas une approximation tolérée. Trois
règles :

1. **Elle est conservée.** Une valeur provisoire est une observation complète ; elle n'est pas mise de côté
   jusqu'à l'approbation.
2. **Elle porte son statut.** Le statut est une propriété de la valeur et voyage avec elle, jusqu'au produit de
   connaissance.
3. **Elle ne se confond pas avec une valeur approuvée.** Un produit qui consomme des observations provisoires
   le dit ; il ne présente pas l'ensemble comme s'il était acquis.

La conséquence forte : la qualification d'un **produit** dépend de la qualification de ses entrées. Un produit
dont toutes les entrées sont approuvées n'est pas pour autant « approuvé » — le statut du produit est le sien.

Le vocabulaire de statut est **fermé et minimal** — une valeur déclarée, une valeur estimée par la source, une
valeur provisoire, une valeur approuvée, une valeur de statut inconnu — mais **l'appariement des statuts d'une
source vers ce vocabulaire est différé** (§6) : dire qu'un « provisional » USGS équivaut à « provisoire » est
une affirmation sur la source, pas sur le contrat.

### 3.8 Informations absentes

**Absent ≠ zéro.** C'est une règle du vocabulaire canonique, énoncée deux fois dans le dépôt :
`docs/ARCHITECTURE.md` §6.2 (« Une donnée absente porte la raison de son absence ; elle ne porte jamais zéro
en guise d'absence ») et `docs/RESEARCH_AND_VALIDATION.md` §6 (« Une valeur absente porte la raison de son
absence et n'est jamais zéro »).

Le contrat nomme le champ qui porte cette raison : **`missing_reason`**. C'est un choix de ce document ; la
notion, elle, est canonique. Sa liste de valeurs est **contrôlée** et stably grows — mais les valeurs
propres à une source sont différées (§6). Une raison d'absence décrit **ce qui manque**, jamais **ce qui a échoué
à la récupération** : c'est le point suivant.

**Trois absences distinctes, jamais confondues :**

| Absence | Ce qu'elle signifie | Ce qu'elle exige |
|---|---|---|
| **Non mesurée** | la source ne fournit pas de valeur pour ce fait | `missing_reason` |
| **Non encore publiée** | la valeur existera, pas encore | `missing_reason` + l'échéance attendue |
| **Collecte non tentée** | TORNE n'a pas été chercher | `missing_reason` + la trace de la non-tentative |

La troisième mérite un mot : l'ancien BORÉE a appris la différence à ses dépens. `boree/src/boree/exploitation/garage.py:95-121`
distingue `en_attente` (copie non envoyée, différée) de `absents_locaux` (présent à l'index, absent du disque) :
une copie **non tentée** est dite **avec sa raison**, pas comme une copie absente. Une absence de TORNE peut
avoir trois causes qu'il ne faut pas confondre : la donnée n'existe pas, la donnée n'est pas encore parue, la
donnée n'a pas été cherchée. Les confondre revient à annoncer une mesure de zéro.

Et l'inverse : **une absence n'est jamais comblée par une supposition**. Un `missing_reason` n'est jamais
remplacé par une estimation, une interpolation ou une valeur par défaut
(`docs/PROGRAMME.md`).

### 3.9 Publication inconnue : une ignorance explicite et exploitable

C'est le point le plus exigeant du contrat, et celui que le cahier des charges pose frontalement
(`docs/PROGRAMME.md`) : **si la source ne permet pas de connaître la date de publication initiale, ne
pas l'inventer**.

Le contrat ne se contente pas de l'interdire. Il rend l'ignorance **exploitable**, en distinguant trois états de
la connaissance de publication, portés par l'observation :

| État | Ce qui est connu | Règle d'utilisabilité |
|---|---|---|
| **Établie** | l'instant de publication initial est connu | `usable_at = max(publication, ingestion)` |
| **Bornée** | un instant **borne inférieure** est connu : à partir de lui, l'information étaitcertainement disponible ; avant, on ne sait pas | admissible à partir de la borne, **pas avant** |
| **Inconnue** | ni instant ni borne | **non admissible** en reconstitution point-in-time, et l'observation le dit |

Pourquoi une borne plutôt qu'un refus sec : `docs/RESEARCH_AND_VALIDATION.md` §4 admet un « replay public :
ce qui était publiquement accessible, **sur preuve ou borne conservatrice** ». Une borne conservatrice est donc
une réponse recevable, à condition d'être conservatrice — c'est-à-dire de ne jamais **surestimer** la
disponibilité. Elle produit un intervalle de censure, pas une date inventée : on sait que l'information était là
à partir de *t*, on ne sait pas si elle y était avant.

Et c'est ici que le contrat **diverge d'`athanor`** : `athanor/src/athanor/kernel/clock.py:39-46` fait
`usable_from(published_at=None, known_at=…) = known_at`, c'est-à-dire **remplacer une publication inconnue par
la date d'ingestion**. C'est exactement le comblement par supposition que `docs/PROGRAMME.md` interdit.
TORNE ne reprend pas ce repli : une publication inconnue reste inconnue, et l'observation n'est pas admise en
reconstitution point-in-time.

### 3.10 Replay opérationnel, replay public, descriptif rétrospectif

`docs/RESEARCH_AND_VALIDATION.md` §4 pose trois lectures temporelles distinctes, « jamais interchangeables dans
un rapport de résultat ». Le contrat les rend distinguished au niveau de la donnée, par un marqueur unique :

- **Replay opérationnel** : ce que TORNE avait effectivement reçu et rendu utilisable. Une observation acquise
  par réimport d'une archive historique **n'y appartient pas** au moment de l'import : elle appartient à la
  date d'acquisition d'origine, et elle est marquée comme telle.
- **Replay public** : ce qui était publiquement accessible, sur preuve ou borne conservatrice. C'est le mode par
  défaut d'une reconstitution.
- **Descriptif rétrospectif** : ce que les archives consolidées permettent de reconstituer aujourd'hui.

Le marqueur est indispensable : `athanor/src/athanor/data/rawstore.py:226-233` fait déjà la même chose par un
chemin dédié (`import_archived`, qui reçoit un `known_at` d'origine et marque la ligne `legacy`). TORNE reprend
le **besoin**, pas nécessairement la syntaxe.

### 3.11 Instanciation par source de `KNOWN_AT` — les quatre classes de source

Le §3.2 donne la **forme** de la règle d'utilisabilité ; le §3.9 donne les trois **états** de la connaissance
de publication. Ce qui manquait — et que le programme identifiait comme « la décision qui manque le plus » —
est **comment établir `KNOWN_AT` selon ce que la source expose réellement**.

Ce n'est pas un problème de fournisseur, et aucun flux payant ne le résout : la revue transversale du 31 octobre
2026 a constaté le même motif dans tous les domaines physiques examinés — une API de réseau électrique sans
horodatage de livraison, un catalogue satellitaire qui sépare la date d'origine de la date de publication de
plusieurs mois, un historique hydrologique explicitement **remplissé a posteriori**. La disponibilité doit
donc être **construite**, source par source, par la sémantique de TORNE.

**La règle unique.** Pour chaque source, on classe selon ce qu'elle expose, et la classe détermine l'état de
publication, donc l'admissibilité. On ne choisit jamais un état plus favorable que ce que la source permet.

| Classe | Ce que la source expose | État | Règle d'établissement de `KNOWN_AT` |
|---|---|---|---|
| **P — publication horodatée** | l'instant de publication de chaque version | **établie** | `KNOWN_AT` = cet instant. C'est le seul cas où `KNOWN_AT` est une date et non une borne. |
| **B — borne de publication** | une borne inférieure : « à partir de cet instant, l'information était certainement disponible », et rien de plus | **bornée** | `KNOWN_AT` = la borne. L'observation est admise **à partir** de la borne, pas avant (INV-11). L'intervalle de censure est conservé et rapporté. |
| **C — cycle de publication documenté** | un cycle de publication documenté (par exemple un bulletin hebdomadaire publié chaque mercredi) et une nominalisation des valeurs à ce cycle | **bornée** | `KNOWN_AT` = **l'instant le plus précoce possible** de publication du cycle concerné, déduit du calendrier de publication documenté. Conservateur par construction : surestimer la disponibilité est impossible. |
| **N — pas de publication** | ni instant, ni borne, ni cycle : historique rempli a posteriori, ou API sans horodatage de livraison | **inconnue** | Aucun `KNOWN_AT` n'est inventé. L'observation est **non admise** en reconstitution point-in-time. Elle reste utilisable en **descriptif rétrospectif**, et le produit qui l'emploie le déclare (`replay_mode`). |

**Trois conséquences non négociables.**

1. **La classe se déduit de la source, pas de la convenance.** Une source passe en classe N dès qu'elle
   n'expose pas d'horodatage exploitable, même si son contenu est excellent. Le repli
   `usable_at = INGESTED_AT` écarté au §5.3 **n'est pas rouvert** : aucune source ne s'en sert à la place d'une
   preuve ou d'une borne.
2. **Une source de classe N n'est pas disqualifiée** : elle est reclassée. Elle porte alors une information
   valuable — une description rétrospective — et son usage est déclaré, non dissimulé. C'est exactement la
   distinction entre « replay public », « replay opérationnel » et « descriptif rétrospectif » du §3.10.
3. **La classe est une propriété de la source, versionnée avec elle.** Un changement de format ou de cycle de
   publication est une révision de la source, pas un détail : il crée une version nouvelle de la fiche de
   source et peut faire basculer une observation de la classe C à la classe N.

**Ce qui reste à faire, et n'est pas fait ici.** Ce paragraphe donne la **règle de classification**. Il ne
donne pas, pour chaque source réelle, la classe Effective ni les bornes : cela relève de la **qualification
des sources** (qualification des sources) et doit être établi par **exécution**, pas par supposition — une source dont le cycle
de publication est supposé mais non vérifié est une source de classe N, pas une source de classe C. Le tableau
ci-dessus est donc la procédure, et chaque fiche de source en est une instantiation.

---

## 4. Les invariants vérifiables

Chaque invariant est formulé comme une règle qu'un test peut contrôler, ou comme une question à laquelle un
test doit répondre par **oui** ou **non**. Aucun test n'est écrit ici.

### 4.1 Conservation de la preuve brute

| Réf. | Invariant | Forme vérifiable |
|---|---|---|
| **INV-01** | Un contenu brut n'est écrit qu'une fois, sous son empreinte. | Question : re-collecter le même contenu crée-t-il une seconde entrée ? Réponse attendue : non. |
| **INV-02** | Un changement de contenu pour une même clé crée une version nouvelle ; l'ancienne reste lisible et inchangée. | Question : après modification de la source, les deux versions existent-elles et l'empreinte de l'ancienne est-elle inchangée ? Attendu : oui. |
| **INV-03** | Toute acquisition de brut est consignée, y compris son échec et son statut « rien ici ». | Question : l'acquisition a-t-elle produit une entrée de journal ? Attendu : oui, dans tous les cas. |
| **INV-04** | Le journal des acquisitions est append-only. Les contenus qu'il référence sont adressés par empreinte : un contenu modifié ne correspond plus à son empreinte. En revanche les lignes du journal ne sont pas chaînées entre elles, et la modification d'une ligne déjà écrite n'est pas détectée par le journal. | Question : une ligne ajoutée touche-t-elle les autres ? Un contenu modifié conserve-t-il son empreinte ? Attendu : non et non. La chaîne de lignes est une limite connue, pas une garantie. |
| **INV-05** | Aucun brut n'est supprimé parce qu'une version plus récente existe. | Question : l'ancienne version est-elle encore relisible ? Attendu : oui. |
| **INV-06** | La déduplication ne perd rien : un contenu identique déjà présent n'est ni réécrit ni perdu. | Question : deux acquisitions du même contenu aboutissent-elles à un seul contenu stocké et deux traces d'acquisition ? Attendu : oui. |

### 4.2 Temporalité

| Réf. | Invariant | Forme vérifiable |
|---|---|---|
| **INV-07** | Toute observation porte ses trois dimensions, ou l'état explicite de leur absence. | Question : existe-t-il une observation sans les trois champs renseignés ou sans état d'absence explicite ? Attendu : non. |
| **INV-08** | `usable_at` est une fonction dérivée, jamais un champ stocké. | Question : existe-t-il un champ `usable_at` dans les données ? Attendu : non. |
| **INV-09** | `usable_at = max(KNOWN_AT, INGESTED_AT)`. | Question : pour un couple de dates donné, le calcul rend-il le maximum ? Attendu : oui. |
| **INV-10** | Une publication inconnue n'est jamais remplacée par la date d'ingestion. L'état de publication se déduit de ce que la source **expose**, établi par vérification (§3.11). | Question : quand `KNOWN_AT` est inconnu, l'observation est-elle admise en reconstitution point-in-time ? Et la classe de la source est-elle établie par vérification, non par supposition ? Attendu : non admise, état « inconnue » ; et classe établie par exécution. |
| **INV-11** | Une publication bornée n'est admise qu'à partir de sa borne. | Question : une requête à `t` antérieur à la borne renvoie-t-elle l'observation ? Attendu : non. |
| **INV-12** | Une révision est invisible avant sa date de révision. | Question : interroger l'état à `t` antérieur à la révision rend-il la version antérieure ? Attendu : oui. |
| **INV-13** | Une version révisée coexiste avec la version qu'elle remplace. | Question : les deux versions sont-elles relisibles ? Attendu : oui. |
| **INV-14** | Une acquisition par réimport d'archive porte la marque de son origine et ne se présente pas comme acquise par TORNE à la date du réimport. | Question : une requête de replay opérationnel exclut-elle cette observation ? Attendu : oui. |
| **INV-15** | Aucun instant n'est stocké sans fuseau ; une date civile n'est jamais stockée comme un instant. | Question : existe-t-il un instant naive ? Attendu : non. Le refus est à l'entrée, pas un correctif a posteriori. |
| **INV-16** | Le résultat d'un calcul ne dépend pas du fuseau du poste qui l'exécute. | Question : le même brut rejoué dans deux fuseaux donne-t-il le même résultat ? Attendu : oui. |
| **INV-17** | Une variable dérivée porte comme `KNOWN_AT` le moment du calcul, jamais celui de ses entrées. | Question : une variable calculée le 21 octobre à partir d'entrées publiées le 18 octobre est-elle connue au 18 octobre ? Attendu : non, elle est connue au 21 octobre. |

### 4.3 Absence, statut, unité

| Réf. | Invariant | Forme vérifiable |
|---|---|---|
| **INV-18** | Une valeur absente porte une `missing_reason` issue d'une liste contrôlée. | Question : existe-t-il une valeur absente sans raison, ou une raison hors liste ? Attendu : non. |
| **INV-19** | Absent ≠ zéro. | Question : une absence et un zéro sont-ils distinguables, et une conversion peut-elle transformer l'un en l'autre ? Attendu : distinguables, et non convertible. |
| **INV-20** | L'absence et la non-tentative sont distinguées. | Question : l'entrée dit-elle laquelle des deux a eu lieu ? Attendu : oui, et les deux cas ne se recouvrent pas. |
| **INV-21** | Une information provisoire est conservée et porte son statut. | Question : l'observation provisoire existe-t-elle dans le corpus et porte-t-elle son statut ? Attendu : oui. |
| **INV-22** | Une valeur provisoire et une valeur approuvée ne sont jamais confondues dans un produit. | Question : le produit qui les consomme les distingue-t-il ? Attendu : oui. |
| **INV-23** | Toute observation porte son unité et son référentiel spatial. | Question : existe-t-il une observation sans unité ou sans référentiel spatial ? Attendu : non. |
| **INV-24** | Une série n'hérite pas du statut de son dernier point. | Question : une série à points mixtes est-elle qualifiée comme mixte ? Attendu : oui. |

### 4.4 Provenance et lignage

| Réf. | Invariant | Forme vérifiable |
|---|---|---|
| **INV-25** | Toute observation se rattache à une preuve brute identifiable. | Question : peut-on remonter de l'observation à l'empreinte du brut ? Attendu : oui. |
| **INV-26** | Re-parser le brut avec le même analyseur redonne la même observation. | Question : la re-parse produit-elle un résultat identique ? Attendu : oui. |
| **INV-27** | Toute ligne dérivée porte un lignage minimal : source, clé, empreinte, instant de connaissance. | Question : les quatre éléments sont-ils présents et non vides sur chaque ligne dérivée ? Attendu : oui. |
| **INV-28** | Le brut est la seule vérité ; le dérivé est reconstructible. | Question : la reconstruction depuis le brut redonne-t-elle le même résultat que le dérivé conservé ? Attendu : oui. |
| **INV-29** | Une variable dérivée connaît toutes ses entrées, transitivement jusqu'aux bruts. Chaque entrée citée est l'**objet canonique** de l'enregistrement : un même identifiant ne peut pas désigner un autre contenu. | Question : l'ensemble des observations consommées est-il reconstructible depuis le produit ? Et chaque entrée citée est-elle bien l'objet que l'enregistrement porte ? Attendu : oui. |
| **INV-30** | Un produit de connaissance ne cite aucune observation non admissible à son propre instant d'établissement. Cet instant ne précède ni la production du résultat publié, ni l'établissement de l'enregistrement qui le porte. | Question : toutes les observations citées ont-elles `usable_at ≤` l'instant du produit ? Et l'instant du produit est-il postérieur à ce qu'il publie ? Attendu : oui. |
| **INV-31** | Un produit publié ne se réécrit pas. | Question : une correction crée-t-elle une version nouvelle, l'ancienne restant consultable ? Attendu : oui. |

### 4.5 Anti-fuite

| Réf. | Invariant | Forme vérifiable |
|---|---|---|
| **INV-32** | Toute table entrée dans TORNE a un **store synthétique** dont chaque valeur encode sa date. | Question : dans le store synthétique, la valeur permet-elle de lire de quel jour elle vient ? Attendu : oui. |
| **INV-33** | Le réalisé interdit porte une valeur sentinelle distincte (par convention −1), jamais 0. | Question : la sentinelle est-elle distinguable d'une valeur légitimement nulle ? Attendu : oui. |
| **INV-34** | Une reconstitution point-in-time ne renvoie aucune observation non admissible. | Question : la requête à `t` renvoie-t-elle une observation dont `usable_at > t` ? Attendu : non, jamais. |

> Le store synthétique est une **décision déjà prise** : il est posé dès la première table, et la technique de
> référence est celle de l'ancien dépôt d'origine — chaque valeur encode sa date, le réalisé interdit vaut −1.
> Ce document en fait un **invariant**, pas une bonne pratique.

### 4.6 La forme testable

La règle générale qui rend ces invariants utilisables : **un test d'anti-fuite n'est pas un test de valeurs, c'est
un test de dates**. Il ne vérifie pas qu'une valeur est correcte ; il vérifie qu'une valeur **n'a pas pu être
produite par une information postérieure au moment simulé**.

La forme canonique est celle du **store synthétique** : écrire dans le store une donnée dont la **valeur** est la
date dont elle est issue, de sorte qu'une fuite temporelle se lise comme un nombre faux et non comme une
subtilité de code. C'est la forme qu'emploie la suite d'évaluation (`tests/test_evaluation.py`).

### 4.7 Reproductibilité numérique

| Réf. | Invariant | Forme vérifiable |
|---|---|---|
| **INV-35** | L'aléa global n'est jamais touché : la graine est transmise au composant, qui fabrique son propre générateur. | Question : une exécution à graine fixée produit-elle le même résultat qu'une autre exécution à la même graine ? Attendu : oui. |
| **INV-36** | Un composant qui échantillonne est déterministe à graine fixée. | Question : deux tirages du même composant, à la même graine, sont-ils identiques ? Attendu : oui. |

### 4.8 Conformité d'une acquisition

L'acquisition est le seul endroit où l'on peut confondre « j'ai obtenu des octets » et « j'ai obtenu la chose
demandée ». Le dépôt tient ces deux choses séparées, et c'est une exigence de contrat, pas une précaution
d'implémentation.

| Réf. | Invariant | Forme vérifiable |
|---|---|---|
| **INV-37** | **La présence de données brutes ne vaut pas conformité sémantique.** Un adaptateur confronte ce qu'il a reçu à ce qu'il a demandé : les identifiants demandés sont ceux qui reviennent, et il ne suppose pas que le fournisseur a obéi. **L'écho d'un filtre dans l'URL n'est pas une preuve de filtrage.** Un critère que la réponse ne permet pas de vérifier est consigné comme **non vérifiable**, jamais comme satisfait. | Question : une requête portant un identifiant inexistant revient-elle avec les lignes de cet identifiant ? Attendu : non, et le verdict est `non_conforme`. |
| **INV-38** | **L'exhaustivité est qualifiée par source.** Une réponse HTTP réussie ne prouve pas que le fournisseur a rendu toutes les observations attendues. | Question : l'issue porte-t-elle une exhaustivité — `declared_exhausted`, `truncated` ou `undeclared` ? Attendu : oui, toujours. |
| **INV-39** | **Une erreur d'adaptateur est un résultat, pas une exception.** Une réponse malformée produit une issue structurée (`failed` ou `partial`), jamais une exception qui sort de l'acquisition sans que rien ne soit consigné. | Question : une réponse malformée produit-elle une issue et une trace ? Attendu : oui, et l'issue est `failed` ou `partial`. |
| **INV-40** | **La conformité est qualifiée, pas supposée.** Un verdict de conformité est `conforme`, `non_conforme`, `indeterminate` ou `non_applicable`, il est établi par exécution, et il porte un motif. `indeterminate` est une **abstention** — un critère demandé n'a pas pu être vérifié — et non un constat. **La porte n'ouvre que sur `conforme`** : une abstention n'autorise pas plus qu'un constat de non-conformité. Le verdict ne parle que de la conformité : le statut d'acquisition, lui, ne parle que de l'acquisition, et la porte `exploitable` est la seule question à poser avant de construire des observations. | Question : un verdict est-il produit sans avoir interrogé la source ? Une issue dont la conformité est indéterminée est-elle exploitable ? Et une issue non conforme est-elle déclarée en échec d'acquisition ? Attendu : non, non, et non. |

### 4.9 Secrets et identifiants

| Réf. | Invariant | Forme vérifiable |
|---|---|---|
| **INV-41** | **Un secret ne circule que par référence.** Ce qui est consigné — journal, manifeste, empreinte, rapport, message — porte une référence d'identifiant, jamais la valeur. | Question : la valeur d'un secret apparaît-elle dans un support consigné ? Attendu : non. |
| **INV-42** | **Un identifiant ne franchit pas une origine.** Un changement de serveur, de port ou de schéma retire les identifiants ; une descente de `https` vers `http` les retire aussi. | Question : une redirection vers une autre origine transmet-elle l'identifiant ? Attendu : non. |

### 4.10 Nature d'un résultat et statut opérationnel

| Réf. | Invariant | Forme vérifiable |
|---|---|---|
| **INV-43** | **La nature d'un résultat et le statut opérationnel d'un produit sont deux choses distinctes, et ne se déduisent pas l'un de l'autre.** Une grandeur dérivée porte sa nature (`estimated`, `reconstructed`, `predicted`, `simulated`, `derived`) ; un produit de connaissance porte son statut opérationnel (`usable`, `degraded`, `withdrawn`, `inconclusive`). Le dépôt n'en distingue aujourd'hui que deux axes ; les deux autres, et la règle de non-contamination qui les gouverne, sont posés en doctrine (`docs/RESEARCH_AND_VALIDATION.md` §12). | Question : un produit `inconclusive` peut-il porter une nature d'estimation ? Et un produit `usable` porte-t-il toujours une nature ? Attendu : oui et oui. |

### 4.11 Ce qui utilise le futur, et ce qui a été estimé

| Réf. | Invariant | Forme vérifiable |
|---|---|---|
| **INV-44** | **Une sortie qui utilise l'information future est déclarée comme telle, et la déclaration est conservée avec le produit.** Le lissage de Rauch–Tung–Striebel reconstruit un état historique en employant les observations **postérieures** à l'instant qu'il estime : c'est une meilleure reconstruction, mais ce n'est pas une estimation qui était disponible à cet instant. Filtrer et lisser sont donc deux sorties distinctes, et la seconde est nommée dans `ModelResult.outputs_using_future`. Une sortie déclarée doit exister : la déclaration décrit un résultat, elle ne peut pas en désigner un qui n'y est pas. | Question : une sortie lissée est-elle déclarée comme utilisant le futur ? Et la déclaration est-elle conservée dans l'enregistrement ? Attendu : oui et oui. |
| **INV-45** | **Les paramètres qu'une méthode a estimés sont conservés avec le produit.** Les paramètres de la configuration sont les paramètres *demandés* ; les paramètres *utilisés* — estimés sur l'historique d'entraînement, lorsque la méthode le fait — sont portés par le résultat et conservés dans l'enregistrement. Un artefact qui ne dit pas quels paramètres ont servi ne permet pas de rejouer le calcul : l'estimation devient une affirmation non vérifiable. | Question : l'enregistrement porte-t-il les paramètres **utilisés** ? Et un paramètre estimé se distingue-t-il du paramètre demandé ? Attendu : oui, et la différence est visible. |

> Les deux invariants répondent à la même question sous deux formes : *ce qui a été calculé* est-il reproductible ?
> Une déclaration qui n'est pas conservée avec le produit ne protège personne ; elle protège seulement celui qui l'a écrite.

---

## 5. La politique de réutilisation, et les arbitrages « un seul de chaque »

### 5.1 La règle, et les quatre catégories

TORNE n'écrit pas ce qui existe déjà ailleurs quand l'existant est bon. Avant d'écrire une brique, on cherche :
elle a peut-être déjà été écrite, auditée et testée dans un dépôt que le projet contrôle.

Une brique candidate est classée dans **une seule** des quatre catégories, et la catégorie est écrite :

| Catégorie | Ce qu'elle signifie |
|---|---|
| **REUSE** | le code est repris tel quel, l'origine est déclarée en tête de fichier |
| **ADAPT** | le code est repris et modifié, la modification est justifiée |
| **REIMPLEMENT** | la brique est réécrite : le doublon est lié au domaine d'origine, ou l'original n'est pas réutilisable en l'état |
| **REJECT** | la brique n'est pas reprise, et la raison est écrite |

Quatre conditions pour qu'une brique entre en REUSE ou ADAPT :

1. **l'octet de licence** est lu dans le fichier lui-même, jamais supposé ;
2. **l'origine est vérifiable** — dépôt, commit et chemin exact sont notés en tête de module ;
3. **une seule décision par composant** — le dépôt n'héberge jamais deux implémentations de la même responsabilité ;
4. **l'import est réel** — une dépendance jamais importée n'est pas une dépendance.

Aucune brique n'entre dans TORNE sans avoir été, au moins, **classée**.

### 5.2 Ce que TORNE a repris, et d'où

Quatre primitives statistiques viennent d'un dépôt historique du propriétaire, **privé**, donc réutilisable sans
réserve de licence. Elles ont été reprises en réécriture interne : la seule exigence est la traçabilité de
l'origine.

| Besoin | Module TORNE | Référence publiée |
|---|---|---|
| Moindres carrés ordinaires, erreur-type robuste CR1 | `src/torne/methods/regression.py` | Cameron, Gelbach & Miller (2011), *REStat* 93(2) |
| Test de Diebold-Mariano apparié, variance de long terme HAC | `src/torne/methods/calibration.py` | Diebold & Mariano (1995), *JBES* 13(3) ; Newey & West (1987), *Econometrica* 55(3) |
| Rupture de moyenne par CUSUM | `src/torne/methods/breaks.py` | Ploberger & Krämer (1992), *Econometrica* 60(2) |
| Effet minimal détectable, taille d'échantillon, puissance | `src/torne/methods/power.py` | Lehr (1992), *Stat. Med.* 11(10) ; Kish (1965) |

Chaque fichier porte en tête le dépôt d'origine, le commit (`athanor@6dacc87`), le chemin exact, le statut de la
licence, les dépendances tierces et la référence publiée. Les tests correspondants vérifient les résultats contre
les définitions publiées — `scipy`, `statsmodels` — et **non** contre une réimplémentation interne : une brique
qui ne se distingue pas de sa référence n'est pas une brique.

**Écritures originales.** Sept modules ne viennent d'aucun dépôt historique : ils sont écrits contre la littérature,
qu'ils citent module par module. Ils obéissent aux mêmes exigences — une référence par routine, un test qui vérifie
le résultat contre la définition publiée et non contre une réimplémentation interne — mais leur provenance est
**une publication**, pas un commit.

| Besoin | Module TORNE | Référence publiée |
|---|---|---|
| Filtre de Kalman en espace d'état, tendance linéaire locale, lissage de Rauch–Tung–Striebel | `src/torne/methods/kalman.py` | Durbin & Koopman (2012), *Chapitre 4* ; Rauch, Tung & Striebel (1965), *AIAA Journal* 3(6) |
| Comparaison appariée d'une prévision et recherche de rupture de régime | `src/torne/methods/compare.py` | Diebold & Mariano (1995), *JBES* 13(3) ; Newey & West (1987), *Econometrica* 55(3) ; Ploberger & Krämer (1992), *Econometrica* 60(2) |
| CRPS, score d'intervalle, score pinball, PIT et diagnostics de calibration | `src/torne/methods/scores.py` | Gneiting & Raftery (2007), *JASA* 102(477) ; Winkler (1970), *JASA* 65(290) ; Ferro (2014), *QJRMS* 140(681) |
| Taille d'échantillon effective, bootstrap par blocs, bootstrap par grappes, sensibilité à l'unité indépendante | `src/torne/methods/dependence.py` | Politis & White (2004), *Econometric Reviews* 23(1) ; Künsch (1989), *Ann. Statist.* 17(3) ; Geyer (1992), *Biometrika* 79(3) |
| Contrôle de la multiplicité : Benjamini–Hochberg, Bonferroni, Romano–Wolf max-t | `src/torne/methods/multiplicity.py` | Benjamini & Hochberg (1995), *JRSS-B* 57(1) ; Romano & Wolf (2005), *Econometrica* 73(4) |

Toutes ces routines stochastiques — le bootstrap, le multiplicateur de Romano–Wolf — prennent une graine explicite et
construisent leur propre générateur : l'aléa global n'est jamais touché (INV-35, INV-36).


### 5.3 Une responsabilité, une implémentation

C'est l'arbitrage « un seul de chaque », énoncé sur l'état réel du dépôt et non sur celui d'un audit :

| Responsabilité | Implémentation unique dans TORNE |
|---|---|
| Magasin brut point-in-time | `src/torne/acquisition/store.py` |
| Contrat de connecteur et conformité | `src/torne/acquisition/contracts.py` |
| Client HTTP et transport | `src/torne/acquisition/transport.py`, `fetcher.py` |
| Empreinte canonique | `src/torne/contracts/fingerprint.py` |
| Journal d'acquisition | `src/torne/acquisition/store.py` (`manifeste.jsonl`) |
| Exécution rejouable d'un modèle | `src/torne/execution/runner.py` |
| Enregistrement d'un produit et vérification de sa lignée | `src/torne/knowledge/record.py` |
| Statistiques | `src/torne/methods/` |

### 5.4 Ce qui a été écarté, et ce qu'il ne faut pas réécrire à l'aveugle

Les autres briques vues dans les dépôts historiques ont été écartées, pour trois motifs distincts : elles étaient
liées au domaine d'origine, elles étaient déjà couvertes par une brique de TORNE, ou elles dépendaient d'une
infrastructure que le socle ne veut pas.

Le détail de ces verdicts n'a plus d'intérêt opérationnel : les dépôts audités ne sont **pas** des dépendances de
TORNE, et leur code n'y est plus consultable. Ce qui reste, c'est la règle du §5.1.

Trois familles restent volontairement **non réimplémentées** tant qu'aucun besoin ne les réclame. Elles sont
citées ici pour que leurs conditions soient connues le jour où le besoin vient :

- **e-values et LOND.** Une garantie de FDR sous dépendance arbitraire, mais **seulement** si l'hypothèse porte sur
  l'**espérance conditionnelle** de chaque unité et que les unités corrélées sont **agrégées par grappe** avant
  le test. L'agrégation par grappe est un prérequis, pas une option : sans elle, la garantie tombe. Le
  rétrécissement par bootstrap, lui, ne donne un FDR que sous indépendance ou PRDS — **pas** sous dépendance
  arbitraire. C'est la nuance à ne pas perdre.
- **Cycle d'exploration « brûle / rétréci ».** Un regard exploratoire **consomme** la fenêtre qu'il regarde, pour
  toutes les hypothèses du même ensemble : une règle y trouvée n'est ensuite confirmée que sur des données
  neuves. Le meilleur des K variantes se lit ensuite *rétréci*, pour contrer la malédiction du gagnant. Ce cycle
  n'a de sens que si l'ensemble des hypothèses est défini.
- **Budget d'alpha partagé.** Une répartition d'un alpha entre hypothèses d'un même ensemble, avec une
  gouvernance explicite de la part qui la consomme.

### 5.5 Le danger de nommage que cet arbitrage crée

Un dépôt d'origine porte souvent des noms qui ne veulent pas dire la même chose qu'ici. C'est ainsi qu'une brique
reprise peut inverser une sémantique **sans casser aucun test**.

L'exemple le plus net : dans le dépôt d'origine, `known_at` désigne **notre** date d'ingestion. Dans le présent
contrat, `KNOWN_AT` désigne la **publication dans la source**. Reprendre le nom tel quel ferait porter
`INGESTED_AT` sous l'étiquette `KNOWN_AT` — un contresens silencieux, qui inverserait la sémantique
point-in-time sans faire échouer un seul test.

**Arbitrage : aucun nom n'est repris quand son sens diffère.** La correspondance est explicite :

| Nom du dépôt d'origine | TORNE | Sens |
|---|---|---|
| `event_time` | `VALID_TIME` | quand le fait s'est produit |
| `published_at` | `KNOWN_AT` | quand la source l'a rendu public |
| `known_at` | `INGESTED_AT` | quand TORNE l'a acquis |
| `usable_from(published_at, known_at)` | `usable_at(KNOWN_AT, INGESTED_AT)` | fonction dérivée |

Une reprise qui n'a pas de table de correspondance n'est pas une reprise : c'est une copie.

### 5.6 Une divergence assumée

Le dépôt d'origine fait `usable_from(published_at=None, known_at=…) = known_at`, donc remplace une publication
inconnue par la date d'ingestion. TORNE ne fait pas ce repli (§3.9) : il porte l'état « publication inconnue » ou
« bornée », et refuse l'admission point-in-time sans preuve ni borne conservatrice.

C'est une divergence **délibérée** avec une brique retenue. Elle est justifiée par un invariant du programme
(« ne jamais combler une métadonnée manquante par une supposition ») et par `docs/RESEARCH_AND_VALIDATION.md` §4
(« sur preuve ou borne conservatrice »). Elle doit rester visible dans le code.

### 5.7 « Local d'abord, copie après »

Le magasin local est la vérité ; une copie distante est une copie. Une panne du stockage distant retarde la
copie, elle ne perd rien. Trois règles en découlent :

1. **Local d'abord, copie après** — la copie n'est jamais en amont de la vérité locale.
2. **Intégrité par empreinte, jamais par décodage** — on vérifie que l'empreinte correspond, pas que le contenu
   « se lit bien ».
3. **Instantané cohérent de l'index** — la copie porte un index cohérent, jamais une vue partielle.

### 5.8 Une règle n'est pas une garantie tant qu'elle n'est pas outillée

Trois statuts, à ne pas confondre :

| Statut | Ce qu'il engage |
|---|---|
| **écrite** | elle n'engage que son auteur |
| **outillée** | elle est vérifiée par l'exécution — un test la contrôle |
| **documentée** | elle n'engage que son lecteur |

Une règle qui n'est qu'**écrite** n'est pas une garantie. Chaque invariant du §4 est formulé comme une question à
laquelle un test doit répondre par oui ou non ; tant que le test n'existe pas, l'invariant est **écrit**, non
**outillé**. Le programme (`docs/PROGRAMME.md`) dit lesquels le sont.

## 6. Ce qui dépend d'une source précise

Le programme interdit d'imposer une conception générique de stockage ou de connecteur avant que « les sources
réellement disponibles soient connues, qualifiées et datées » (`docs/PROGRAMME.md`). Ce contrat s'arrête donc
avant tout ce qui dépend d'une source précise.

### 6.1 Ce qui est contractuel, et ne dépend d'aucune source

- Les cinq objets : responsabilités, invariants, ce qu'ils ne garantissent pas, relations (§1-§2).
- Les trois dimensions temporelles, leur ordre, et le fait que `usable_at` est dérivé (§3.1-§3.2).
- La règle d'utilisabilité `max(KNOWN_AT, INGESTED_AT)` et ses trois conséquences (§3.2).
- Le traitement de la publication inconnue : états *établie / bornée / inconnue* et règle d'admission (§3.9).
- La règle de révision : version nouvelle, historique non réécrit, invisibilité avant la date (§3.6).
- Le traitement des statuts provisoires (§3.7) et des absences, avec `missing_reason` (§3.8).
- La conservation de la preuve brute et l'interdiction de l'écrasement silencieux (§2.2, INV-01 à INV-06).
- Le lignage minimal à quatre éléments (INV-27) et la reconstructibilité du dérivé (INV-28).
- Le store synthétique anti-fuite comme invariant (INV-32 à INV-34).
- Les arbitrages « un seul de chaque » de §5, qui ne dépendent d'aucune source.
- La conformité d'une acquisition : conformité sémantique distincte de la présence de données, exhaustivité
  qualifiée par source, erreur d'adaptateur transformée en issue (INV-37 à INV-40).
- Les secrets et identifiants : un secret ne circule que par référence, et ne franchit pas une origine
  (INV-41, INV-42).
- L'aléa global n'est jamais touché, et un composant qui échantillonne est déterministe à graine fixée
  (INV-35, INV-36).
- La nature d'un résultat et son statut opérationnel sont deux choses distinctes (INV-43).
- La séparation entre une estimation disponible en temps réel et une reconstruction qui utilise le futur, et la
  conservation des paramètres estimés (INV-44, INV-45).

### 6.2 Ce qui attend la qualification des sources

Chaque ligne indique **ce qu'il faudra** pour trancher.

| Point différé | Ce qu'il faudra pour trancher |
|---|---|
| **Établissement de `KNOWN_AT` par source** : d'où vient la date de publication (en-tête HTTP, métadonnée du document, champ de la charge utile, date du fichier) ? | Le contenu réel de la réponse et ses métadonnées, pour chaque source retenue — c'est précisément la qualification des sources (`docs/SOURCES.md`). |
| **La borne conservatrice, quand la publication est inconnue** : quelle borne est défendable par source ? | La granularité de publication observée et la fréquence de mise à jour de la source. |
| **Granularité retenue par source** : horaire, quotidien, hebdomadaire ; et la règle d'agrégation. | Les paramètres réels de chaque jeu de données. |
| **Convention de date civile par source** : une semaine « se terminant le samedi » se termine-t-elle en heure locale de l'émetteur ou en UTC ? Le décalage change la date d'appartenance d'une observation. | Le fuseau déclaré par l'émetteur et l'heure de coupure de son cycle de publication. |
| **Correspondance des statuts de qualité** : « provisional », « estimated », « approved », « provisional » de l'API hydrologique — à quoi se rattachent-ils dans le vocabulaire fermé de §3.7 ? | La documentation de qualité de chaque source, et non son nom de champ. |
| **Valeurs de `missing_reason` par source** : « non mesuré », « non publié », « série arrêtée », « instrument défaillant », « hors domaine » ? | L'inventaire des motifs d'absence réellement rencontrés dans les données de chaque source. |
| **Politique de révision par source** : une révision crée-t-elle une nouvelle version d'observation, ou seulement une nouvelle version de fichier ? La source date-t-elle ses révisions ? | La documentation et l'observation empirique du comportement de révision de chaque source. |
| **Registre d'unités et référentiel spatial** : quelle unité de conservation pour le débit, le niveau, le tonnage ? Quelle référence verticale ? | Un point ouvert déjà identifié dans le dépôt (`docs/PROGRAMME.md`) : aucun des dépôts audités n'a de registre d'unités ni de CRS. |
| **Forme du « brut » par source** : un fichier, une réponse JSON, une ligne de tableau ? Y a-t-il une unité d'acquisition stable ? | L'observation directe des réponses réelles. |
| **Procédure de calcul de `usable_at` par source** | **La règle de classification est donnée (§3.11)** : quatre classes de source, et la classe détermine l'état de publication et donc l'admissibilité. Son **instanciation par source** — la classe effective, les bornes, les cycles — dépend de l'établissement de `KNOWN_AT` ci-dessus, et relève de la qualification des sources. |

> **Ce qui bloque encore.** La **règle** de calcul de `usable_at` est écrite (§3.11 : classes P, B, C et N, et
> l'effet de chacune sur l'admissibilité). Ce qui reste à faire n'est plus la règle mais son **instanciation par
> source**, qui ne peut pas se faire par supposition : elle exige d'avoir **interrogé** chaque source et constaté
> ce qu'elle expose. Une source dont le cycle de publication est supposé mais non vérifié est une source de
> classe N.

---

## 7. Ce qui n'a pas pu être tranché

Trois points ne relèvent ni d'une erreur de conception ni d'une négligence : ils ne peuvent pas être tranchés
avant que les données soient connues.

1. **La reconstitution de l'historique des révisions est-elle possible ?** Le premier slice en fait un critère
   de succès (`docs/PROGRAMME.md`). Cela dépend entièrement de la source : une source qui
   date ses révisions permet la reconstitution ; une source qui ne les date pas ne la permet pas, et le contrat
   ne peut que le constater en qualifiant l'absence. **Ce n'est pas une question de conception.**
2. **La granularité commune entre sources.** Aligner un flux hebdomadaire de fret sur un flux horaire de débit
   suppose de choisir une règle d'agrégation et une convention de rattachement. La règle d'agrégation est
   contractuelle (§3.3) ; le **choix** de la granularité commune ne l'est pas.
3. **La qualité du point de vue opérationnel.** `docs/RESEARCH_AND_VALIDATION.md` §4 distingue trois lectures
   temporelles. La question « jusqu'où TORNE peut-il affirmer ce qu'il savait *alors* » dépend de la fréquence
   réelle de collecte, qui est une donnée d'exploitation, pas une donnée de conception.

S'y ajoute un point de **méthode**, non de source : le contrat dit ce qui doit être vérifiable, mais ne dit pas
comment le tester. Un test d'anti-fuite suppose un harnais de dates simulées ; sa forme est celle du store
synthétique (§4.6), et son écriture relève du programme.

---

## Les dix décisions que ce document prend

1. **Cinq objets, cinq responsabilités.** Les cinq concepts de `docs/PROGRAMME.md` ne deviennent ni cinq
   couches, ni cinq tables, ni cinq services ; ils deviennent cinq questions auxquelles un objet répond seul
   (§1.1), et les relations sont une lignée de données, pas un pipeline obligatoire (§1.3).

2. **Trois dimensions temporelles stockées, rien de plus.** Le temps de disponibilité devient une **fonction
   dérivée** (`usable_at`), le temps d'usage devient un **paramètre de requête** (`asof`), et la date déclarée
   par l'émetteur devient une **métadonnée de source** (§3.1).

3. **Aucun nom n'est repris quand son sens diffère.** Dans le dépôt d'origine, `known_at` signifie l'ingestion ;
   ici il signifie la publication. Une reprise littérale inverserait la sémantique point-in-time sans casser
   aucun test (§5.5).

4. **`usable_at = max(KNOWN_AT, INGESTED_AT)`, jamais stocké.** Trois conséquences explicites : fonction dérivée,
   ingestion antérieure à la publication = donnée douteuse, ordre naturel
   `VALID_TIME ≤ KNOWN_AT ≤ INGESTED_AT` (§3.2).

5. **Une publication inconnue n'est pas remplacée par la date d'ingestion.** Trois états — établie, bornée,
   inconnue — et une règle d'admission ; l'état « inconnue » **exclut** l'observation de la reconstitution
   point-in-time (§3.9). C'est une divergence assumée avec le dépôt d'origine (§5.6).

6. **La révision ne réécrit pas l'historique.** Une révision est une version nouvelle, coexistant avec
   l'ancienne, invisible avant sa date de révision (§3.6, INV-12 et INV-13).

7. **Absent ≠ zéro, et l'absence a trois formes.** `missing_reason` est obligatoire et contrôlée ; l'absent, le
   non-encore-publié et le non-tenté sont distincts ; une absence n'est jamais comblée par une supposition
   (§3.8).

8. **Le brut ne s'écrase pas silencieusement.** Un contenu est écrit une fois, sous son empreinte ; un changement
   de contenu est une version nouvelle ; une acquisition est journalisée, y compris son échec et son statut
   « rien ici » (§2.2, INV-01 à INV-06).

9. **Le lignage minimal à quatre éléments et le store synthétique sont des invariants, pas des bonnes
   pratiques.** Toute ligne dérivée porte source, clé, empreinte et instant de connaissance ; toute table a un
   store synthétique où chaque valeur encode sa date et où le réalisé interdit vaut −1 (§4.4, §4.5).

10. **Une responsabilité, une implémentation.** Le dépôt n'héberge jamais deux briques de la même
    responsabilité, et toute brique reprise est classée (REUSE, ADAPT, REIMPLEMENT, REJECT) avant d'entrer
    (§5.1, §5.3). Le principe « brut = vérité, dérivé = reconstructible » est retenu, comme les trois règles
    « local d'abord, copie après » (§5.7).

---

## Les cinq questions qui restent ouvertes

1. **Comment `KNOWN_AT` est-il établi pour chaque source retenue** — quel champ, quelle métadonnée, quelle
   granularité de publication ? C'est la question qui conditionne tout le reste, et elle est close par la
   qualification des sources (`docs/SOURCES.md`).

2. **Quelle borne conservatrice est défendable quand la publication est inconnue** — faut-il donner à chaque
   source sa propre borne, dérivée de son cycle de publication, ou une borne uniforme pour toutes ? Le repli
   `usable_at = INGESTED_AT`, écarté au §5.6, **n'est pas rouvert** : aucune source ne peut s'en servir à la
   place d'une preuve ou d'une borne.

3. **Quelle granularité commune, et quelle règle de rattachement entre sources de fréquences différentes**
   (agrégation, chevauchement, décalage de fin de semaine) ? La règle d'agrégation est posée (§3.3) ; le choix
   ne l'est pas.

4. **Quel registre d'unités et quel référentiel spatial** — conservation dans les unités de la source ou
   conversion, et quelle référence verticale pour les grandeurs hydrologiques ? Le point est déjà ouvert dans
   le programme (`docs/PROGRAMME.md`) et aucun dépôt historique n'y apporte de réponse.

5. **Le statut de qualité des sources se rattache-t-il proprement au vocabulaire fermé de §3.7**, et quelles
   sont les valeurs de `missing_reason` réellement rencontrées ? Le vocabulaire est posé ; son instantiation
   par source ne l'est pas, et elle dépend des données.

---

*Les points du §6 lui sont explicitement renvoyés, et les cinq questions ci-dessus ne sont pas tranchables avant
que les sources soient qualifiées.*
