# TORNE — Contrats fondamentaux

**Objets, temporalité, invariants — 31 octobre 2026**
**Statut : contrat.** Ce document fixe des responsabilités, des invariants et des formes vérifiables. Il ne
décrit aucun schéma de stockage, aucun connecteur, aucune table, aucun service. Le gate P1 n'est pas franchi
par ce document : tout ce qui dépend d'une source précise est explicitement différé (§6).

---

## 0. Ce que ce document est, et ce qu'il n'est pas

Il est **un contrat**, au sens où il dit ce qui doit rester vrai quoi qu'il arrive au code. Il existe pour que
trois choses ne dépendent plus du style de l'implémenteur :

- ce qu'un objet garantit, et ce qu'il ne garantit pas ;
- à quel instant un fait est devenu vrai, connu et acquis ;
- quelle question un test doit pouvoir poser pour constater qu'une règle tient.

Il n'est **pas** une architecture de stockage. Il ne dit ni où vit une observation, ni sous quelle forme, ni
dans quel format elle circule. Le gate P1 (`docs/PROGRAMME.md:50`) interdit d'imposer une conception générique
avant de connaître les données réellement disponibles ; ce document respecte cette interdiction en distinguant,
à chaque fois, ce qui est **contractuel** de ce qui est **différé**.

Il n'est **pas** une spécification d'implémentation non plus : aucune brique n'est décrite comme acquise, et
aucune affirmation de ce document ne repose sur du code de TORNE — le dépôt n'en contient pas encore.
*(Mise à jour du 31 octobre 2026 : le dépôt contient désormais une forme exécutable de ces contrats,
dans `src/torne/contracts/`. Ce document reste la **source** : le code en est l'application, et il ne
lui ajoute aucune brique.)*

### 0.1 Ce qui est vérifié et ce qui est cité

Les affirmations sur les dépôts historiques portent un chemin de fichier et, quand c'est possible, une ligne.
Elles ont été relues dans les fichiers eux-mêmes, pas seulement dans les rapports d'audit. Les trois audits
(`docs/audit/ATHANOR.md`, `docs/audit/CRIN.md`, `docs/audit/LEGACY-BOREE.md`) restent la référence pour le
contexte ; lorsqu'une affirmation y est reprise ici, elle est signalée comme **revérifiée**.

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
(`docs/VISION.md:128`).

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

> **Le brut ne s'écrase pas silencieusement** (`docs/PROGRAMME.md:13`). La forme vérifiable est l'existence d'un
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
est réellement connu (`docs/RESEARCH_AND_VALIDATION.md:110-115`).

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
inconclusif (`docs/ARCHITECTURE.md:87-90`).

**Invariants.** Un produit n'est publiable que si sa lignée est complète et vérifiable. Un produit publié ne se
réécrit pas : une correction produit une **version nouvelle**, et l'ancienne reste consultable. Un produit
inconclusif est un résultat valide, rapporté comme tel, avec sa cause
(`docs/RESEARCH_AND_VALIDATION.md:130-135`). Un produit ne cite pas d'observation qui n'était pas admissible au
moment où il a été établi ; et son instant d'établissement ne précède ni la production du résultat qu'il
publie, ni l'établissement de l'enregistrement qui le porte : **un produit ne précède pas ce qu'il publie**.

**Il ne garantit pas** : que le produit soit vrai, ni qu'il reste vrai, ni qu'il soit réutilisable hors de son
domaine de validité. Il n'est pas un registre et ne catalogue pas l'existant
(`docs/ARCHITECTURE.md:92-95`). Il ne valide pas rétroactivement les modèles amont.

---

## 3. La sémantique temporelle

### 3.1 Les trois dimensions, et ce qui n'en est pas une

`docs/ARCHITECTURE.md:53-54` évoque « la distinction canonique entre temps de validité, temps de publication,
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
(`docs/REUSE_AUDIT.md:153`). Ce que TORNE en retient, c'est l'idée qu'une heure locale peut être ambiguë — et
donc que la conversion doit être faite et conservée, pas recalculée à la lecture.

### 3.5 Précision variable

Deux sources neymes pas la même chose par « précision », et le contrat les sépare :

- **La résolution déclarée** : ce que la source dit de son pas de mesure (horaire, quotidien, hebdomadaire).
- **L'incertitude réelle** : ce qui est connu de l'exactitude de la valeur.

Une valeur dont la résolution est horaire porte une incertitude qui n'est pas nulle simplement parce que la
source ne la publie pas. Le contrat impose qu'une observation **sans incertitude qualifiée** le dise
explicitement, plutôt que de laisser croire à une précision que personne n'a établie. La forme retenue est
l'adaptation de la forme à ce qui est connu (`docs/RESEARCH_AND_VALIDATION.md:110-115`) : intervalle,
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
`docs/ARCHITECTURE.md:130-131` (« Une donnée absente porte la raison de son absence ; elle ne porte jamais zéro
en guise d'absence ») et `docs/RESEARCH_AND_VALIDATION.md:119` (« Une valeur absente porte la raison de son
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
(`docs/PROGRAMME.md:18-19`).

### 3.9 Publication inconnue : une ignorance explicite et exploitable

C'est le point le plus exigeant du contrat, et celui que le cahier des charges pose frontalement
(`docs/PROGRAMME.md:180-181`) : **si la source ne permet pas de connaître la date de publication initiale, ne
pas l'inventer**.

Le contrat ne se contente pas de l'interdire. Il rend l'ignorance **exploitable**, en distinguant trois états de
la connaissance de publication, portés par l'observation :

| État | Ce qui est connu | Règle d'utilisabilité |
|---|---|---|
| **Établie** | l'instant de publication initial est connu | `usable_at = max(publication, ingestion)` |
| **Bornée** | un instant **borne inférieure** est connu : à partir de lui, l'information étaitcertainement disponible ; avant, on ne sait pas | admissible à partir de la borne, **pas avant** |
| **Inconnue** | ni instant ni borne | **non admissible** en reconstitution point-in-time, et l'observation le dit |

Pourquoi une borne plutôt qu'un refus sec : `docs/RESEARCH_AND_VALIDATION.md:70` admet un « replay public :
ce qui était publiquement accessible, **sur preuve ou borne conservatrice** ». Une borne conservatrice est donc
une réponse recevable, à condition d'être conservatrice — c'est-à-dire de ne jamais **surestimer** la
disponibilité. Elle produit un intervalle de censure, pas une date inventée : on sait que l'information était là
à partir de *t*, on ne sait pas si elle y était avant.

Et c'est ici que le contrat **diverge d'`athanor`** : `athanor/src/athanor/kernel/clock.py:39-46` fait
`usable_from(published_at=None, known_at=…) = known_at`, c'est-à-dire **remplacer une publication inconnue par
la date d'ingestion**. C'est exactement le comblement par supposition que `docs/PROGRAMME.md:18-19` interdit.
TORNE ne reprend pas ce repli : une publication inconnue reste inconnue, et l'observation n'est pas admise en
reconstitution point-in-time.

### 3.10 Replay opérationnel, replay public, descriptif rétrospectif

`docs/RESEARCH_AND_VALIDATION.md:67-76` pose trois lectures temporelles distinctes, « jamais interchangeables dans
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
de publication. Ce qui manquait — et que le dépôt qualifiait de « la décision qui manque le plus »
(`docs/DECISIONS.md`, repris en `docs/SLICE-PREMIER.md`) — est **comment établir `KNOWN_AT` selon ce que la
source expose réellement**.

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
des sources** (gate P1) et doit être établi par **exécution**, pas par supposition — une source dont le cycle
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
| **INV-04** | Le journal des acquisitions est append-only et chaîné. | Question : une modification a posteriori d'une entrée est-elle détectée ? Attendu : oui. |
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

> Le store synthétique est une **décide déjà prise** (`docs/DECISIONS.md:17` : « Le store synthétique anti-fuite
> est posé dès la première table »), et la technique de référence est celle de l'ancien BORÉE : chaque valeur
> encode sa date, le réalisé interdit vaut −1 (`boree/tests/fabrique.py:1-2`, `:26`, `:34`, `:70`). Ce document
> en fait un **invariant**, pas une bonne pratique.

### 4.6 La forme testable

La règle générale qui rend ces invariants utilisables : **un test d'anti-fuite n'est pas un test de valeurs, c'est
un test de dates.** Il ne vérifie pas qu'une valeur est correcte ; il vérifie qu'une valeur **n'a pas pu être
produite par une information postérieure au moment simulé**. La forme canonique est celle de
`boree/tests/fabrique.py` : écrire dans le store une donnée dont la **valeur** est la date dont elle est
issue, de sorte qu'une fuite temporelle se lise comme un nombre faux et non comme une subtilité de code.

---

## 5. Les arbitrages « un seul de chaque »

`docs/REUSE_AUDIT.md:194-207` a établi que **sept briques** ont été construites deux fois, dans trois dépôts.
Le gate P1 n'a rien à y voir : ces arbitrages-là sont **techniques**, pas liés à une source précise.

**Une précision de fond, tirée de `docs/REUSE_AUDIT.md:176-192`** : Athanor est un dépôt privé du propriétaire ;
il est réutilisable **sans réserve de licence**. L'arbitrage n'est donc pas juridique. Il est **technique** : le
quel des deux est le plus robuste, et lequel est lié au domaine d'origine. C'est le critère retenu ci-dessous.

| # | Besoin | Doublons | **Retenu par TORNE** | Pourquoi — en une phrase |
|---|---|---|---|---|
| 1 | Magasin brut point-in-time | `athanor.data.rawstore.RawStore` / `boree.archive.py` | **`athanor.data.rawstore`** | C'est le seul qui pose lui-même l'instant d'ingestion et refuse d'être antidaté (`athanor/src/athanor/data/rawstore.py:9`), et le seul dont la lecture `asof` applique la règle d'utilisabilité (`:297-303`) ; celui de `boree` en est un doublon moins robuste. |
| 2 | Registre de modèles (contrats, statuts) | `athanor.research.registry` / `boree.registre` | **`athanor.research.registry`** | Il rejoue une machine à états depuis le journal chaîné au lieu de stocker un état mutable qui dérive (`athanor/src/athanor/kernel/journal.py:4-5`), alors que le registre de `boree` est expérimental et tourne « en ombre » (`boree/PROTOCOLE.md:152-156`). |
| 3 | Contrat de connecteur | `athanor.data.source` (+ `data/compliance.py`) / `boree.ingest.sources` | **`athanor.data.source`** | Il couvre en plus robots.txt et conditions d'usage, et refuse par défaut une source restreinte tant qu'une décision humaine n'est pas prise (`athanor/src/athanor/data/source.py:7-11`) ; celui de `boree` est lié au marché électrique. |
| 4 | Gestion des secrets | `athanor.kernel.secrets` / `boree.archive.py:312-314` | **`athanor.kernel.secrets`** | L'environnement l'emporte, les valeurs ne sont jamais écrites dans un journal, un rapport ou un message, et `api_key=` est masqué dans les URL (`athanor/src/athanor/kernel/secrets.py:8-9`) ; celui de `boree` est une simple lecture d'une variable d'environnement. |
| 5 | Client S3 | `athanor.data.s3` / `boree.exploitation.garage` | **`athanor.data.s3`** | Un seul client pour un seul besoin ; le client de `boree` est écarté, mais **ses trois règles sont reprises** : local d'abord, copie après (`:5-7`), intégrité par empreinte et jamais par décodage (`:12-13`), instantané cohérent de l'index (`:9-10`). |
| 6 | Fermeture du code de mesure | `athanor.research.provenance` / garde de `boree` | **`athanor.research.provenance`** | Il fait la fermeture transitive des imports et la preuve d'équivalence ; l'ancien BORÉE n'a pas de module de provenance équivalent, et sa garde est propre à son architecture. |
| 7 | Statistiques du juge | `athanor.stats` | **`athanor.stats`** | Douze primitives testées contre les définitions publiées ; BORÉE les utilise déjà, et C.R.I.N. les ignore — ce qui est son erreur (`docs/REUSE_AUDIT.md:207`). |

### 5.1 Trois briques non listées dans les sept, mais arbitrées ici

- **Le journal chaîné** : `athanor.kernel.journal` est retenu comme **journal unique** — append-only, chaîné par
  empreintes, verrouillé entre processus (`athanor/src/athanor/kernel/journal.py:1-13`). Il n'y a pas de second
  journal dans TORNE.
- **Le lignage minimal** : le motif des quatre colonnes de BORÉE (`_source`, `_cle`, `_empreinte`, `_connu_a`,
  `boree/src/boree/lac/connu.py:32`) est retenu comme lignage minimum de toute ligne dérivée — voir INV-27 ; seul
  le nom du quatrième élément change (§5.2).
- **La forme dérivée** : le principe « le brut est la vérité, le dérivé est reconstructible » de
  `boree/src/boree/lac/parquet.py:4-6` est retenu ; la réécriture atomique des partitions (`:53-54`, `:67-68`)
  est retenue comme patron.

### 5.2 Le danger de nommage que cet arbitrage crée

En retenant `athanor.data.rawstore`, on importe un champ qui s'appelle `known_at` et qui signifie **notre
date d'ingestion** (`athanor/src/athanor/data/rawstore.py:9` ; `athanor/src/athanor/kernel/clock.py:7` : «
`known_at` quand NOTRE système l'a ingéré »).

Or, dans le vocabulaire de ce contrat, **`known_at` est l'instant de publication dans la source**. Les deux mots
désignent deux instants différents. Une reprise littérale du magasin ferait porter `INGESTED_AT` sous le nom
`KNOWN_AT` — un contresens silencieux, qui ne casserait aucun test existant et qui inverserait la sémantique
point-in-time.

**Arbitrage : TORNE n'importe pas le nom `known_at` d'Athanor.** Le magasin retenu sera réécrit ou adapté avec
la nomenclature du présent contrat, et la table de correspondance est :

| Athanor | TORNE | Sens |
|---|---|---|
| `event_time` | `VALID_TIME` | quand le fait s'est produit |
| `published_at` | `KNOWN_AT` | quand la source l'a rendu public |
| `known_at` | `INGESTED_AT` | quand TORNE l'a acquis |
| `usable_from(published_at, known_at)` | `usable_at(KNOWN_AT, INGESTED_AT)` | fonction dérivée |

De même, le `_connu_a` de `boree/src/boree/lac/connu.py:32-33` (posé depuis `ref.known_at`, donc l'ingestion)
devient `_ingeste_a` dans la nomenclature TORNE. Le principe — « la version et l'instant de connaissance
voyagent ensemble » — est conservé ; le nom est corrigé.

### 5.3 Une divergence assumée

`athanor/src/athanor/kernel/clock.py:39-46` fait `usable_from(published_at=None, known_at=…) = known_at`, donc
remplace une publication inconnue par la date d'ingestion. TORNE ne fait pas ce repli (§3.9) : il porte
l'état « publication inconnue » ou « bornée » et refuse l'admission point-in-time sans preuve ni borne
conservatrice.

C'est une divergence **délibérée** avec une brique retenue. Elle est justifiée par un invariant du programme
(`docs/PROGRAMME.md:18-19` : « Ne jamais combler une métadonnée manquante par une supposition ») et par
`docs/RESEARCH_AND_VALIDATION.md:70` (« sur preuve ou borne conservatrice »). Elle devra être visible dans
la réécriture du magasin.

---

## 6. Ce qui est différé au gate P1

Le gate P1 exige que « les sources réellement disponibles sont connues, qualifiées et datées » avant toute
conception générique de stockage ou de connecteur (`docs/PROGRAMME.md:50`). Ce contrat s'arrête donc avant tout
ce qui dépend d'une source précise.

### 6.1 Ce qui est contractuel, et se fait maintenant

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

### 6.2 Ce qui dépend d'une source précise, et attend P1

Chaque ligne indique **ce qu'il faudra** pour trancher.

| Point différé | Ce qu'il faudra pour trancher |
|---|---|
| **Établissement de `KNOWN_AT` par source** : d'où vient la date de publication (en-tête HTTP, métadonnée du document, champ de la charge utile, date du fichier) ? | Le contenu réel de la réponse et ses métadonnées, pour chaque source retenue — c'est précisément la qualification que P1 doit produire. |
| **La borne conservatrice, quand la publication est inconnue** : quelle borne est défendable par source ? | La granularité de publication observée et la fréquence de mise à jour de la source. |
| **Granularité retenue par source** : horaire, quotidien, hebdomadaire ; et la règle d'agrégation. | Les paramètres réels de chaque jeu de données. |
| **Convention de date civile par source** : une semaine « se terminant le samedi » se termine-t-elle en heure locale de l'émetteur ou en UTC ? Le décalage change la date d'appartenance d'une observation. | Le fuseau déclaré par l'émetteur et l'heure de coupure de son cycle de publication. |
| **Correspondance des statuts de qualité** : « provisional », « estimated », « approved », « provisional » de l'API hydrologique — à quoi se rattachent-ils dans le vocabulaire fermé de §3.7 ? | La documentation de qualité de chaque source, et non son nom de champ. |
| **Valeurs de `missing_reason` par source** : « non mesuré », « non publié », « série arrêtée », « instrument défaillant », « hors domaine » ? | L'inventaire des motifs d'absence réellement rencontrés dans les données de chaque source. |
| **Politique de révision par source** : une révision crée-t-elle une nouvelle version d'observation, ou seulement une nouvelle version de fichier ? La source date-t-elle ses révisions ? | La documentation et l'observation empirique du comportement de révision de chaque source. |
| **Registre d'unités et référentiel spatial** : quelle unité de conservation pour le débit, le niveau, le tonnage ? Quelle référence verticale ? | Un point ouvert déjà identifié dans le dépôt (`docs/DECISIONS.md:42-43`) : aucun des dépôts audités n'a de registre d'unités ni de CRS. |
| **Forme du « brut » par source** : un fichier, une réponse JSON, une ligne de tableau ? Y a-t-il une unité d'acquisition stable ? | L'observation directe des réponses réelles — donc P1. |
| **Procédure de calcul de `usable_at` par source** | **La règle de classification est donnée (§3.11)** : quatre classes de source, et la classe détermine l'état de publication et donc l'admissibilité. Son **instanciation par source** — la classe effective, les bornes, les cycles — dépend de l'établissement de `KNOWN_AT` ci-dessus, et relève de la qualification des sources. |

> **Ce qui a changé le 31 octobre 2026.** « Procédure de calcul de `usable_at` : c'est la décision qui manque le
> plus. Sans elle, la sémantique point-in-time n'est pas implémentable, et le slice ne peut pas démarrer » — la
> **règle** est désormais écrite (§3.11 : classes P, B, C et N, et l'effet de chacune sur l'admissibilité). Le
> blocage qui reste n'est plus la règle mais son **instanciation par source**, qui ne peut pas se faire par
> supposition : elle exige d'avoir **interrogé** chaque source et constaté ce qu'elle expose. Une source dont le
> cycle de publication est supposé mais non vérifié est une source de classe N.

---

## 7. Ce qui n'a pas pu être tranché

Trois points ne relèvent ni d'une erreur de conception ni d'une négligence : ils ne peuvent pas être tranchés
avant que les données soient connues.

1. **La reconstitution de l'historique des révisions est-elle possible ?** Le premier slice en fait un critère
   de succès (`docs/SLICE-PREMIER.md:102`, `:110-112`).Cela dépend entièrement de la source : une source qui
   date ses révisions permet la reconstitution ; une source qui ne les date pas ne la permet pas, et le contrat
   ne peut que le constater en qualifiant l'absence. **Ce n'est pas une question de conception.**
2. **La granularité commune entre sources.** Aligner un flux hebdomadaire de fret sur un flux horaire de débit
   suppose de choisir une règle d'agrégation et une convention de rattachement. La règle d'agrégation est
   contractuelle (§3.3) ; le **choix** de la granularité commune ne l'est pas.
3. **La qualité du point de vue opérationnel.** `docs/RESEARCH_AND_VALIDATION.md:69-72` distingue trois lectures
   temporelles. La question « jusqu'où TORNE peut-il affirmer ce qu'il savait *alors* » dépend de la fréquence
   réelle de collecte, qui est une donnée d'exploitation, pas une donnée de conception.

S'y ajoute un point de **méthode**, non de source : le contrat dit ce qui doit être vérifiable, mais ne dit pas
comment le tester. Un test d'anti-fuite suppose un harnais de dates simulées ; sa forme est celle de
`boree/tests/fabrique.py`, mais son écriture relève de P2-B.

---

## Les dix décisions que ce document prend

1. **Cinq objets, cinq responsabilités.** Les cinq concepts de `docs/PROGRAMME.md:163-171` ne deviennent ni cinq
   couches, ni cinq tables, ni cinq services ; ils deviennent cinq questions auxquelles un objet répond seul
   (§1.1), et les relations sont une lignée de données, pas un pipeline obligatoire (§1.3).

2. **Trois dimensions temporelles stockées, rien de plus.** Le temps de disponibilité devient une **fonction
   dérivée** (`usable_at`), le temps d'usage devient un **paramètre de requête** (`asof`), et la date déclarée
   par l'émetteur devient une **métadonnée de source** (§3.1).

3. **Le nom `known_at` d'Athanor est refusé tel quel.** `known_at` y signifie l'ingestion ; ici il signifie la
   publication. Une reprise littérale inverserait la sémantique point-in-time sans casser aucun test (§5.2).

4. **`usable_at = max(KNOWN_AT, INGESTED_AT)`, jamais stocké.** Règle identique à celle d'`athanor.kernel.clock`,
   mais avec trois conséquences explicites : fonction dérivée, ingestion antérieure à la publication = donnée
   douteuse, ordre naturel `VALID_TIME ≤ KNOWN_AT ≤ INGESTED_AT` (§3.2).

5. **Une publication inconnue n'est pas remplacée par la date d'ingestion.** Trois états — établie, bornée,
   inconnue — et une règle d'admission ; l'état « inconnue » **exclut** l'observation de la reconstitution
   point-in-time (§3.9). C'est une divergence assumée avec `athanor.kernel.clock:39-46` (§5.3).

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

10. **Les sept doublons sont arbitrés techniquement en faveur d'Athanor**, sur le critère « le plus robuste, et
    non lié au domaine » — avec la reprise des trois *règles* de `boree.exploitation.garage`, du lignage de
    `boree.lac.connu` et du principe « brut = vérité, dérivé = reconstructible » de `boree.lac.parquet` (§5).

---

## Les cinq questions qui restent ouvertes

1. **Comment `KNOWN_AT` est-il établi pour chaque source retenue** — quel champ, quelle métadonnée, quelle
   granularité de publication ? C'est la question qui conditionne tout le reste, et elle est close par la
   qualification des sources que P1 doit produire.

2. **Quelle borne conservatrice est défendable quand la publication est inconnue** — faut-il donner à chaque
   source sa propre borne, dérivée de son cycle de publication, ou une borne uniforme pour toutes ? Le repli
   `usable_at = INGESTED_AT`, écarté au §5.3, **n'est pas rouvert** : aucune source ne peut s'en servir à la
   place d'une preuve ou d'une borne.

3. **Quelle granularité commune, et quelle règle de rattachement entre sources de fréquences différentes**
   (agrégation, chevauchement, décalage de fin de semaine) ? La règle d'agrégation est posée (§3.3) ; le choix
   ne l'est pas.

4. **Quel registre d'unités et quel référentiel spatial** — conservation dans les unités de la source ou
   conversion, et quelle référence verticale pour les grandeurs hydrologiques ? Le point est déjà ouvert dans
   le dépôt (`docs/DECISIONS.md:42-43`) et aucun dépôt historique n'y apporte de réponse.

5. **Le statut de qualité des sources se rattache-t-il proprement au vocabulaire fermé de §3.7**, et quelles
   sont les valeurs de `missing_reason` réellement rencontrées ? Le vocabulaire est posé ; son instantiation
   par source ne l'est pas, et elle dépend des données.

---

*Ce document ne franchit pas le gate P1. Les points du §6 lui sont explicitement renvoyés, et les cinq questions
ci-dessus ne sont pas tranchables avant que les sources soient connues.*
