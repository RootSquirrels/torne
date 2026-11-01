# MARINE-001 — Reconnaissance des données marine et côtières

> **Mission de reconnaissance.** Ce dossier ne construit pas de moteur marin, ne publie **aucun
> produit de connaissance** et ne tire **aucune conclusion** sur l'océan. Il fait ce que la mission
> demande : **qualifier les sources**, **trouver un phénomène physique intéressant**, **vérifier
> qu'une observation indépendante existe**, et **identifier une première grandeur nouvelle** à
> reconstruire. Le reste — module de domaine, contrat, abstraction — est explicitement **différé**,
> et le §6 explique pourquoi.
>
> Toutes les mesures ci-dessous ont été faites **par exécution**, le **1ᵉʳ novembre 2026**, sur des
> données réelles.

**Règle de preuve.** **[FAIT]** (observé sur une requête ou sur les octets reçus), **[INFÉRENCE]**
(lecture plausible d'un fait observé), **[NON VÉRIFIÉ]** (non vérifié, avec la marche à suivre).

**Reproduction.**

```bash
uv run python experiments/marine_001_sources_probe.py            # l'inventaire d'accessibilité
uv run python experiments/marine_001_atlas_stations.py           # l'atlas des stations, et la carte de capacité
uv run python experiments/marine_001_premier_acquisition.py       # l'acquisition et le profil
```

---

## 0. Ce que la mission a changé

1. **Une réanalyse européenne est derrière un compte ; l'in situ européen ne l'est pas.**
   Le catalogue STAC de Copernicus Marine est **ouvert** — 319 produits, en format ARCO — mais les
   données répondent **403 AccessDenied**. C'est le **même motif** que Météo-France, observé deux
   fois : le chemin d'accès institutionnel européen passe par un compte, et la partie « ouvert » du
   web institutionnel est le catalogue, pas les données.
   **Mais la distinction est réelle et elle compte** : le GDAC Argo d'Ifremer sert les **profils
   netCDF réels** en accès direct et sans secret (`200 application/x-netcdf`, 18 704 octets). Ce
   n'est pas « l'Europe est fermée » ; c'est « **la réanalyse** est fermée, l'**observation** est
   ouverte ».

2. **L'obstacle n'est pas géographique, il est de nature.** La source ouverte qui porte la physique
   du panache — l'archive océanographique de NOAA/NDBC — est américaine, et son atlas le confirme
   précisément : sur les **344 stations** qui ont une archive de salinité, **zéro** n'est dans
   l'Atlantique Nord-Est. Les **11** stations du référentiel qui *sont* dans ce carré — dont la
   bouée **Gascogne** de Météo-France et les bouées et bâbord-lightships du **UK Met Office** —
   sont **météorologiques** (`waterquality=n`, `currents=n`) : pas une salinité.
   Autrement dit : **la salinité mesurée en Europe, en source ouverte, n'existe pas** dans ce
   réseau. Ce n'est pas une absence de mesures — c'est une absence de **capacité déclarée**.

3. **La physique du panache est démontrable en données ouvertes** — et elle est conforme à
   l'intuition : sur l'estuaire du Potomac, la salinité passe de 8,00 à 19,70 psu, le cycle annuel
   est net (minimum en juin, maximum en décembre), les **épisodes de dessalement** atteignent
   **−2,30 psu en 24 h**, et la salinité est anticorrélée à la température (**−0,803**). Ce sont les
   signatures d'un panache.

4. **Le constat de fond : le panache n'est pas un phénomène marin.** C'est un **couplage à quatre
   périmètres** — hydrologie (les apports), atmosphère (le vent), observation terrestre (la
   turbidité), océanographie (la salinité et le courant). La question marine ne peut donc pas être
   posée par l'océanographie seule ; et **deux des quatre sources institutionnelles sont
   aujourd'hui derrière un compte**. C'est le résultat le plus important de la mission, et il
   détermine la suite.

---

## 1. Inventaire des sources

La sonde a posé **quinze** questions à quinze points d'accès, le 1ᵉʳ novembre 2026, et a classé
chaque réponse en cinq états distincts — dont `contenu_inattendu`, qui n'existait pas avant cette
mission (une page d'erreur servie avec le code 200 n'est pas un accès).

| Source | Point d'accès | État | Ce que c'est |
|---|---|---|---|
| **Copernicus Marine** | `stac.marine.copernicus.eu/metadata/catalog.stac.json` | **accessible** | le catalogue STAC du Data Store, **319 produits** en format ARCO, ouvert |
| **Copernicus Marine** | fiche produit `GLOBAL_MULTIYEAR_PHY_001_030` (GLORYS12) | **accessible** | la description de la réanalyse globale : 1/12°, 50 niveaux, 1993→, assimilation altimétrie et observations |
| **Copernicus Marine** | paquet ARCO zarr (`mdl-arco-time-025`) | **sur_tunnel** | **403 AccessDenied** — le bucket existe, l'accès est refusé |
| **Copernicus Marine** | paquet netCDF natif (`mdl-native-14`) | **absente** | **404 NoSuchKey** — l'objet n'est pas à cette adresse |
| **Copernicus Marine** | `data.marine.copernicus.eu` | **accessible** | le portail (HTML) |
| **Argo (GDAC Ifremer)** | `ar_index_global_prof.txt` | **accessible** | l'index global des profils : fichier, date, latitude, longitude, **date de mise à jour** — **318 Mo** de texte |
| **Argo (GDAC Ifremer)** | `ar_index_global_meta.txt` | **accessible** | l'index global des métadonnées de flotteurs |
| **Argo (GDAC Ifremer)** | `dac/aoml/13857/profiles/D13857_001.nc` | **accessible** | **un profil netCDF réel**, 18 704 octets, tel que l'index le désigne |
| **NOAA/NDBC** | `data/realtime2/14049.txt` | **accessible** | le relevé temps réel d'une bouée : vent, pression, température — texte brut |
| **NOAA/NDBC** | `data/historical/ocean/` | **accessible** | l'index des archives océanographiques : **344 stations**, fichiers `{station}o{année}.txt.gz` |
| **NOAA/NDBC** | `data/historical/ocean/44042o2025.txt.gz` | **accessible** | l'archive océanographique annuelle, gzipippée |
| **NOAA/NDBC** | `activestations.xml` | **accessible** | le référentiel des stations actives : position, type, et **quelles grandeurs la station rapporte** |
| **EMODnet Physics** | `erddap.emodnet-physics.eu` | **injoignable** | **délai dépassé** (tentatives à 45 s et 90 s) ; le site principal répond et redirige vers `portal.emodnet-physics.eu` |
| **data.gouv.fr** | API catalogue, `q=maritime` | **accessible** | le catalogue national : **906** jeux de données « maritime » |
| **Ifremer** | `data.ifremer.fr` | **accessible** | le « Portail des données marines » : catalogue et accès aux jeux de données |

**Bilan de la sonde : 12 accessibles · 1 sur_tunnel · 1 absente · 1 injoignable.**

**[FAIT] Sur les 15 points interrogés, un seul échoue par le compte** (Copernicus Marine). Le
« chemin d'accès institutionnel européen passe par un compte » est donc établi **pour la
réanalyse**, pas pour l'observation in situ.

### 1.1 L'atlas des stations : la carte de capacité

Le référentiel `activestations.xml` se déclare lui-même : `count="1352"`, `created="2026-11-01"`.
Il porte, station par station, **les grandeurs réellement rapportées** — `met`, `currents`,
`waterquality`, `dart`, chacun à `y` ou `n`.

**[FAIT]**

| Mesure | Compte |
|---|---|
| stations au référentiel | **1 352** (710 fixes, 438 bouées, 76 DART, 54 plateformes, 48 TAO, 24 autres, 2 USV) |
| rapportent `met` | 863 |
| rapportent `currents` | **42** |
| rapportent `waterquality` | **138** |
| **rapportent l'eau** (courants ou qualité de l'eau) | **167** |

**[FAIT]** Les 167 stations qui mesurent l'eau sont **nord-américaines** : National Estuarine
Research Reserve System (48), Everglades National Park (37), Scripps (13), Pacific Islands Ocean
Observing System (8), CORMP (7), Limno Tech (7)… **Aucun producteur européen** dans la liste.

**[FAIT] L'Atlantique Nord-Est (43–52 °N, 20 °O–0 °E) compte 11 stations au référentiel** :

| Station | Position | Type | `met` | `currents` | `waterquality` | Propriétaire |
|---|---|---|---|---|---|---|
| 62001 | 45,23 N 5,00 O | bouée | n | n | n | **Météo-France** (Gascogne) |
| 62027 | 49,08 N 2,22 O | bouée | n | n | n | Jersey |
| 62029 | 48,72 N 12,43 O | bouée | y | n | n | UK Met Office (K1) |
| 62030 | 50,25 N 4,22 O | bouée | y | n | n | UK Met Office (L4) |
| 62050 | 50,00 N 4,40 O | bouée | y | n | n | UK Met Office (E1) |
| 62081 | 51,00 N 13,55 O | bouée | y | n | n | UK Met Office (K2) |
| 62103 | 49,90 N 2,90 O | fixe | y | n | n | UK Met Office (Channel Lightship) |
| 62107 | 50,10 N 6,10 O | fixe | y | n | n | UK Met Office (Sevenstones) |
| 62163 | 47,55 N 8,47 O | bouée | y | n | n | UK Met Office (**Brittany**) |
| 62305 | 50,40 N 0,00 | fixe | y | n | n | UK Met Office (Greenwich) |
| 62442 | 49,00 N 16,50 O | bouée | y | n | n | UK Met Office (Pap) |

**[FAIT]** Aucune de ces 11 stations ne rapporte de courant ni de qualité de l'eau, et **aucune n'a
d'archive océanographique**. Le réseau européen de NDBC est un **relais météorologique** : ce n'est
pas un réseau d'observation de la mer.

**[FAIT]** L'index des archives océanographiques cite **344 stations** ; **175** sont encore au
référentiel actif, **169** en ont été retirées (archives conservées). **Zéro** des 344 n'est dans
le carré Atlantique Nord-Est.

> **[INFÉRENCE]** L'obstacle à l'étude du panache en Europe n'est pas l'accès au réseau, c'est la
> **capacité déclarée** du réseau. Un atlas de capacité vaut mieux qu'une liste de sources : il
> dit où la grandeur cherchée est **mesurée**, et non où l'on pourrait la mesurer. C'est la
> différence entre une source inaccessible et une grandeur **absente**.

### 1.2 Ce que l'archive océanographique NDBC contient réellement

**[FAIT]** En-tête du fichier (station 44042, estuaire du Potomac) :

```
#YY MM DD hh mm DEPTH OTMP COND SAL O2% O2PPM CLCON TURB PH EH
#yr mo dy hr mn m  degC mS/cm psu %  ppm ug/l FTU -  mv
```

**[FAIT] La sentinelle d'absence dépend de la colonne.** Sur ce fichier, `COND` ne contient que
`999.00`, `O2%` que `999.0`, `O2PPM` / `TURB` / `PH` / `EH` que `99` ou `99.00` — tandis que `SAL`
et `OTMP` portent des **mesures réelles** (116 et 287 valeurs distinctes respectivement). Traiter
`999.00` comme une mesure mettrait 999 psu dans une série marine.

> **[NON VÉRIFIÉ]** la table officielle des valeurs manquantes n'a pas été trouvée : la page
> « Measurement Descriptions and Units » du guide NDBC répond **404**, et le guide officiel
> (`ndbc_web_data_guide.pdf`, juin 2023) ne donne que l'**appendice A — correspondance entre
> extension de fichier et type de donnée**, sans la table des sentinelles. La règle appliquée est
> donc **observée**, pas documentée. **La marche à suivre** : interroger le producer.

**[FAIT]** Le fichier est un **profil** : 57 662 lignes pour 57 662 instants distincts sur cette
station, `DEPTH = 1.0` partout — la station ne mesure qu'en surface. D'autres stations ont
plusieurs profondeurs.

### 1.3 Les sources européennes, une par une

**[FAIT]** Les points d'accès historiques de l'Ifremer **ne résolvent plus** en DNS :
`odc.ifremer.fr`, `thalia.ifremer.fr`, `gert.ifremer.fr`, `sismo.ifremer.fr`,
`www.marine.culture.gouv.fr`, `data.emodnet-physics.eu` — tous **NXDOMAIN**, alors que
`www.ifremer.fr` et `data.ifremer.fr` répondent. Ce ne sont pas des pannes de réseau : ce sont des
**hôtes qui n'existent plus sous ce nom**.

**[FAIT]** `data.ifremer.fr` est le « Portail des données marines » vivant. Il expose un point
d'entrée **OGC OpenSearch** (`opensearch.xml`, 475 octets) qui renvoie vers `search?t={termes}`.

> **[NON VÉRIFIÉ]** le chemin de téléchargement d'un jeu de données Ifremer. La recherche rend
> HTTP 200, mais le HTML servi est une **coquille** : les résultats sont rendus côté client, et la
> page ne contient **aucun lien de téléchargement** (`0` lien `/content/download/…` pour
> « salinité » comme pour « bouée »). **La marche à suivre** : interroger l'API du portail, ou
> suivre la chaîne catalogue → jeu de données → fichier, une fois le point d'entrée identifié.

**[FAIT]** Le catalogue national (data.gouv.fr) répond `q=maritime` avec **906** jeux — mais ils
sont **majoritairement cartographiques et administratifs** : zones maritimes réglementaires,
classements sanitaires de zones de production, pêcheries, planification maritime. Le mot
« maritime » y désigne une **qualification administrative**, pas une grandeur observée.

---

## 2. La première acquisition réelle

Station **44042 — Potomac, MD** (38,033 N / 76,335 O), archive **2025**, 244 805 octets gzip,
conformité **`conforme`**, preuve brute conservée.

### 2.1 La couverture

**[FAIT]** 57 662 instants du **2025-02-25T17:12Z** au **2025-12-31T23:48Z**, cadence observée :
**une mesure toutes les 6,0 minutes** (médiane). Les minutes ne sont pas rondes — l'archive
enregistre l'instant réel de la mesure, pas une grille horaire.

**[FAIT]** Valeurs traitées comme absentes, par grandeur : `salinite` 3, `temperature_eau` 3,
`turbidite` **57 662** — c'est-à-dire **toute la colonne**. Cette station ne mesure pas la
turbidité ; elle ne publie pas une turbidité nulle.

### 2.2 La salinité, et son cycle

**[FAIT]** Salinité : **min 8,00 · max 19,70 · médiane 15,40 psu** (n = 57 659).

**[FAIT]** Cycle mensuel moyen :

| Jan | Fév | Mar | Avr | Mai | Juin | Juil | Aoû | Sep | Oct | Nov | Déc |
|---|---|---|---|---|---|---|---|---|---|---|---|
| — | 15,24 | 16,77 | 15,49 | 13,61 | **11,02** | 11,50 | 12,81 | 15,18 | 16,87 | 18,14 | **18,98** |

**[FAIT]** Température de l'eau : min 3,60 °C · max 32,20 °C · médiane 19,80 °C. Corrélation
salinité–température : **−0,803** (57 659 instants appariés).

> **[INFÉRENCE]** La signature est celle d'un estuaire tempéré : **salé en hiver, douce en été**. Le
> minimum de juin (11,02 psu) coïncide avec le maximum de débit, le maximum de décembre
> (18,98 psu) avec l'étiage. La corrélation −0,803 entre salinité et température est **contemporaine
> et non décalée** : sur une année, elle dit surtout que l'été est à la fois plus chaud et plus
> douce. **Ce n'est pas** une preuve de forçage hydraulique amont : une variation advective
> produirait le même signe. C'est exactement ce qu'il faudra départager.

### 2.3 Les épisodes de dessalement — la signature du panache

**[FAIT]** Les baisses de salinité les plus fortes sur 24 h :

| Date | Δ salinité |
|---|---|
| 2025-06-21 → 22 | **−2,30 psu** |
| 2025-05-18 → 19 | −1,60 psu |
| 2025-09-27 → 28 | −1,60 psu |
| 2025-09-16 → 17 | −1,40 psu |
| 2025-06-30 → 07-01 | −1,40 psu |

**[FAIT]** Les cinq plus forts dessalements tombent **tous entre le 18 mai et le 27 septembre**,
c'est-à-dire dans la fenêtre du minimum saisonnier de salinité. Ce ne sont pas des événements
isolés : ce sont des **épisodes de faible salinité** réguliers, dont le maximum d'intensité
(double de la médiane du cycle) est l'indice d'un forçage pulsé.

---

## 3. Le phénomène physique

Le **panache fluvial** est un volume d'eau douce injecté dans un milieu salé, dont la géométrie
résulte de l'**advection par le courant**, de la **diffusion**, et de la **stratification**. Sa
signature observable est triple :

1. un **gradient** de salinité (ici 8 → 19,7 psu sur la station) ;
2. une **chronologie** — le panache est **pulsé** (les apports), pas permanent ;
3. une **dépendance au forçage amont** — le débit du fleuve.

**[FAIT]** Les trois signatures sont présentes dans les données ouvertes : le gradient, le cycle
annuel, et les épisodes de dessalement. **La physique est démontrable sans compte** — c'est un
résultat de la mission, et il n'est pas banal : il signifie que **le besoin d'un compte CMEMS
n'est pas un besoin de physique, mais un besoin de géographie**.

---

## 4. La première grandeur nouvelle à reconstruire

> **Le panache est-il sous la contrainte du fleuve (forçage hydraulique amont) ou sous la
> contrainte de l'océan (forçage advectif : courant et vent) ?**

Autrement dit : **quelle part de l'anomalie de salinité est-elle expliquée par le débit, et quelle
part par le transport ?**

**Pourquoi c'est une grandeur *nouvelle*.** Une source publie la salinité ; une autre publie le
débit ; une autre publie le courant ; une autre publie le vent. **Aucune ne publie leur rapport** —
et c'est ce rapport qui décide si un estuaire est un conduit de débit ou un piège à eau douce.
Un modèle de panache fournit des cartes ; cette grandeur est **scalaire, datée, et attribuable** :
elle dit, pour chaque épisode, d'où vient l'eau.

**Comment elle se calcule.** Sur la série `A(t) = S(t) − S_clim(t)` (anomalie de salinité par
rapport à la climatologie saisonnière calculée par TORNE) :

| Terme | Source | Périmètre |
|---|---|---|
| `A(t)` | salinité de surface in situ | océanographie |
| `Q(t)` et `Q(t−τ)` | débit du fleuve | hydrologie (BASIN-001) |
| `u(t)` | courant le long de l'estuaire | océanographie |
| `τ_wind(t)` | tension de vent → transport d'Ekman | atmosphère (ATMO-001) |
| `T(t)` | turbidité de surface | observation terrestre (EO) |

**Comment elle se falsifie.** Les deux hypothèses donnent des signatures **opposées** : un forçage
hydraulique produit une covariance **instantanée** entre `A` et `Q` (au temps de propagation de
l'estuaire) ; un forçage advectif produit une covariance **décalée** de `A` avec le forçage
côtier, sans lien avec `Q`. Le test est donc une **comparaison de modèles** — et il a une issue
nulle possible : « ni l'un ni l'autre ne rend compte », ce qui serait un résultat.

---

## 5. Les références indépendantes

| Rôle | Ce qui est proposé | État |
|---|---|---|
| **Climatologie de référence** | la climatologie saisonnière de salinité **calculée par TORNE** sur la série elle-même | possible aujourd'hui |
| **Contrôle indépendant n° 1** | la **turbidité** satellite (périmètre EO) : un panache turbide doit être **co-localisé** avec l'anomalie de salinité | EO en cours |
| **Contrôle indépendant n° 2** | la **température de surface** d'ERA5 (réanalyse, ouverte via Open-Meteo) : le panache doit être **plus froid** en surface | accessible |
| **Contrôle indépendant n° 3** | le **débit** du fleuve, mesuré indépendamment de la salinité | hydrologie en cours |
| **Contre-exemple** | une station **sans** influence fluviale : le même calcul doit y produire une anomalie nulle | NDBC, ouvert |

> **La règle de la mission.** ERA5 est une **estimation**, pas une observation : la comparer à une
> station mesure un écart entre deux productions, et ne valide aucune des deux. Le débit et la
> turbidité sont les contrôles **indépendants** ; ERA5 est un contrôle de **cohérence**.

---

## 6. Ce qui n'est pas construit, et pourquoi

**Aucun module de domaine marin n'a été écrit.** Contrairement à ATMO-001, où le module
`torne.atmosphere` a été justifié par une source réglée, ici **la source côtière européenne n'est
pas réglée** : le seul jeu ouvert et lisible est américain, et l'atlas de capacité montre qu'il
n'y a pas de salinité européenne dans le réseau ouvert. Écrire `src/torne/marine/` sur cette base
produirait un module dont la géométrie — stations, variables, profondeurs, coordonnées
géographiques — ne correspondrait à rien de ce qu'on veut étudier. La mission le dit elle-même :
*« aucun nouveau framework, aucune abstraction générique »*.

Ce qui est écrit se limite donc à **trois scripts rejouables** et à ce dossier. La première
acquisition réelle est faite dans le script, avec le socle — mais **sans** adaptation du socle.

---

## 7. Mapping aux contrats, et les adaptations nécessaires

### 7.1 Ce qui existe déjà et ne doit pas être réinventé

**[FAIT]** Le périmètre EO construit en parallèle un **vocabulaire spatial** — `SpatialRef`,
`Point`, `BoundingBox`, `Footprint`, `RasterGrid` — et un contrat `EarthObservation` pour les
produits de surface, qui sont des **champs** et non des valeurs.

**[FAIT]** Le domaine marin a besoin exactement de ces choses : une bouée est un `Point` avec une
position et une altitude ; un produit CMEMS est un `RasterGrid` sur une `Footprint` ; une image de
turbidité est une `EarthObservation`.

> **Conséquence M1 — le domaine marin doit se brancher sur le contrat spatial de l'agent EO**, et
> ne pas créer le sien. **Signalé, non appliqué** : ce sont des fichiers partagés, en cours
> d'écriture par un autre agent.

### 7.2 Ce qui manque, et n'appartient à personne

| # | Adaptation | Pourquoi | État |
|---|---|---|---|
| **M1** | Brancher le domaine marin sur le contrat spatial existant | un vocabulaire spatial propre serait un doublon | **signalée, non appliquée** (fichiers partagés) |
| **M2** | **Une dimension verticale** | les contrats spatiaux sont **horizontaux** (point, boîte, empreinte, grille). L'océan est en **volume** : une observation est « à 1 m sous la surface, au point X, à l'instant T ». Ni `Observation` ni `SpatialRef` ne porte la profondeur — c'est le **besoin propre de l'océan**, et il n'appartient pas à un seul agent | **signalée, non appliquée** |
| **M3** | **La convention d'absence, par colonne** | la sentinelle d'absence est **propre à la source** et **variable selon la colonne** (`99` et `999` coexistent dans le même fichier). Le socle n'a pas de place pour la déclarer ; le décodeur doit l'apprendre de la source, ce qui veut dire la **documenter** | **signalée, non appliquée** |
| **M4** | **Un profil, pas une valeur** | une observation océanographique est souvent un **profil** (plusieurs profondeurs au même instant). `Observation` porte une valeur scalaire ; la décomposition en une observation par profondeur fonctionne et le contrat l'admet (l'identifiant distingue), mais **plusieurs observations partagent le même instant** — ce qui n'est écrit nulle part | **signalée, non appliquée** |
| **M5** | **Une dépendance de lecture netCDF** | Argo et EMODnet servent du netCDF ; le dépôt n'a pas de lecteur. La règle du dépôt est « une bibliothèque s'installe quand un module en a **réellement** besoin » : le besoin n'est pas encore établi, donc **rien n'est installé** | **signalée, non appliquée** |

---

## 8. Ce qui n'a pas pu être vérifié

- **[NON VÉRIFIÉ]** **EMODnet ERDDAP** : délai dépassé à 45 s puis 90 s, alors que le site principal
  répond. **La marche à suivre** : réessayer depuis un autre réseau ; c'est le serveur le plus
  prometteur pour l'in situ côtier européen, avec un accès en CSV sans dépendance.
- **[NON VÉRIFIÉ]** le **chemin de téléchargement d'un jeu de données Ifremer** : le portail est
  ouvert et expose OpenSearch, mais les résultats sont rendus côté client — aucun lien de fichier
  dans le HTML servi. **La marche à suivre** : identifier l'API du portail.
- **[NON VÉRIFIÉ]** la **table officielle des valeurs manquantes** NDBC (page en 404) : la règle est
  observée, pas documentée.
- **[NON VÉRIFIÉ]** le **débit de la Gironde** et les **données de turbidité satellite** : périmètres
  hydrologie et EO, non vérifiés ici.
- **[NON VÉRIFIÉ]** les **produits CMEMS ouverts** : le catalogue ne porte pas de marqueur d'accès
  ouvert exploitable dans les propriétés inspectées ; l'existence d'un sous-ensemble ouvert n'est
  pas établie.
- **[NON VÉRIFIÉ]** l'**homogénéité** des séries (déplacement de station, changement de capteur) :
  `stationmetadata.xml` existe et couvre l'historique depuis 2000, mais n'a pas été exploité.

---

## 9. La suite proposée

1. **Arbitrer l'accès Copernicus Marine** (compte) — c'est la source qui porte le plateau
   Nord-Est Atlantique. Le motif est établi deux fois (Météo-France, CMEMS) : le chemin
   institutionnel européen passe par un compte, et c'est un fait d'architecture à assumer, pas un
   accident.
2. **Localiser la source côtière européenne ouverte** : EMODnet depuis un autre réseau, le portail
   Ifremer (`data.ifremer.fr` — dont il faut trouver l'API), les jeux « maritime » du catalogue
   national (906 jeux, **majoritairement cartographiques** : à inspecter), ou **Thalia / Ifremer
   Coastal** sous leurs noms actuels — les anciens hôtes ne résolvent plus.
3. **Trancher la dimension verticale (M2)** : c'est le besoin propre de l'océan, il n'appartient à
   aucun agent en particulier, et il sera nécessaire à la première observation marine.
4. **Poser la question (§4)** quand les quatre entrées seront disponibles — et pas avant : elle est
   **multi-périmètre** par nature.
5. **Écrire la pré-registration** de cette question : hypothèses concurrentes, jeu de données,
   puissance attendue (dimensionnée par la **taille effective** de la série d'anomalies, comme en
   ATMO-001), critères de décision — avant de regarder le résultat.

---

## 10. Ce qui a été produit

| Fichier | Rôle |
|---|---|
| `experiments/marine_001_sources_probe.py` | l'inventaire d'accessibilité, rejouable, avec vérification de la forme du contenu |
| `experiments/marine_001_atlas_stations.py` | l'atlas des stations : qui mesure quoi, et où — la carte de capacité |
| `experiments/marine_001_premier_acquisition.py` | la première acquisition réelle (socle, preuve brute, conformité) et le profil |
| `data/marine-001/ndbc_web_data_guide.pdf` | le guide officiel NDBC (juin 2023), conservé comme référence |

**État.** `ruff check` et `ruff format` propres sur les trois scripts. Aucun fichier partagé n'a
été modifié : les cinq adaptations sont listées en §7 et soumises à arbitrage.
