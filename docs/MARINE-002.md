# MARINE-002 — Tester les sources 3D, et chiffrer les besoins

> **Mission de qualification.** Cette mission demandait cinq choses : **tester ORAS5** et en extraire
> un échantillon tridimensionnel de salinité, température et courant sur une zone définie ; **ouvrir un
> profil Argo réel** et qualifier ses coordonnées verticales, ses unités, ses indicateurs de qualité et
> sa structure ; **tester GLORYS12** et vérifier un sous-ensemble quotidien sur la zone étudiée ;
> **arbitrer M2, M4 et M5** sur ces fichiers réels ; et **documenter les besoins exacts avant de modifier
> les contrats partagés**.
>
> Ce dossier ne modifie **aucun** contrat partagé. Il en **chiffre** le besoin.
>
> Toutes les mesures ci-dessous ont été faites **par exécution**, le **1ᵉʳ novembre 2026**, sur des
> données réelles.

**Règle de preuve.** **[FAIT]** (observé sur une requête ou sur les octets reçus), **[INFÉRENCE]**
(lecture plausible d'un fait observé), **[NON VÉRIFIÉ]** (non vérifié, avec la marche à suivre).

**Reproduction.**

```bash
uv run python experiments/marine_002_profil_argo.py   # ouvrir et qualifier un profil Argo réel
uv run python experiments/marine_002_oras5.py          # tester ORAS5 : reconnaissance, coût, exécution
```

---

## 0. Ce que la mission a changé

1. **Une source 3D européenne répond sans compte Copernicus Marine** : ORAS5 passe par le Climate
   Data Store, et la clé CDS du dépôt y donne accès — à une condition : la **licence CC-BY doit être
   acceptée dans le compte**. La commande elle-même est **validée** par l'API (le coût est calculé,
   la combinaison est jugée valide) ; c'est l'acceptation qui manque. Le téléchargement d'ORAS5 est
   donc **bloqué par un geste du propriétaire du compte**, pas par un défaut de la source.

2. **M2 et M4 ne sont plus des hypothèses.** Un profil Argo **réel** a été ouvert : l'axe vertical y
   est une **pression en decibar** (`axis="Z"`), à **niveaux irréguliers**, et la qualité y est un
   **code caractère dont le vocabulaire est documenté ailleurs**. Un contrat qui ne sait pas dire
   « à 47,02 N / 4,23 O, à 12,3 décibars, à cet instant » ne sait pas dire ce que la source dit.

3. **M5 n'est pas « installer un lecteur netCDF ».** Ce sont **deux familles de fichiers** :
   Argo sert du **netCDF-3 classique**, lisible par `scipy.io.netcdf_file` — et **scipy est déjà une
   dépendance déclarée** du dépôt ; ORAS5 sert du **NetCDF4 (HDF5)**, que `scipy` **ne lit pas** et
   qui exige `h5py` ou `netCDF4`. Une seule dépendance nouvelle, optionnelle — et une voie **CSV**
   qui, elle, ne demande rien.

4. **La zone ne se demande pas à la source.** ORAS5 est un produit **global**, et son formulaire n'a
   **aucun paramètre de zone** : un sous-ensemble géographique se **découpe après téléchargement**.
   C'est un fait d'architecture de la source, pas une limite de l'outil — et cela a un coût : on
   télécharge l'océan entier pour lire une baie.

5. **GLORYS12 reste hors d'atteinte.** Aucun identifiant Copernicus Marine n'est présent dans le dépôt,
   et l'API d'observation Météo-France refuse déjà la clé dont nous disposons. L'accès à GLORYS12
   passe par un compte **distinct**, avec une **clé distincte** — voir le §3.

---

## 1. ORAS5 — la réanalyse 3D qui répond

### 1.1 Ce que le catalogue expose

**[FAIT]** ORAS5 est distribué par le Climate Data Store sous deux entrées :

| Entrée | Identifiant | Nature |
|---|---|---|
| Champs mensuels globaux | `reanalysis-oras5` | la réanalyse, en 3D, sur 75 niveaux |
| Séries ponctuelles | `reanalysis-oras5-timeseries` | l'accès **par point**, prioritaire |

**[FAIT]** La fiche produit (collection `reanalysis-oras5`) décrit : projection **tripolaire**,
résolution horizontale **0,25° × 0,25°**, couverture **globale**, **75 niveaux** de modèle pour les
variables 3D, de **0 m** (surface) à **≈ 5 500 m**, l'espacement croissant de **1 m** en surface à
**200 m** en profondeur, et une **moyenne mensuelle**. Le format livré est **NetCDF4 (CF-1.4)**.

**[FAIT]** Le catalogue CDS est **public** : la lecture des fiches ne demande aucun secret. Seule
l'exécution en demande un.

### 1.2 Les deux produits, et la frontière 2015

**[FAIT]** Les contraintes de la source distinguent deux produits :

| Produit | Période | Variables 3D disponibles | Mois publiés |
|---|---|---|---|
| `consolidated` | **1958 → 2014** | `salinity`, `potential_temperature`, `zonal_velocity`, `meridional_velocity` | 01 → 12 |
| `operational` | **2015 → présent** | les quatre, **plus** `rotated_zonal_velocity` et `rotated_meridional_velocity` | **01 → 09** (puis 10 → 12 pour 2015-2025) |

**[FAIT]** La frontière a été **observée par le refus de l'API** : `consolidated` avec l'année 2025
renvoie « Request has not produced a valid combination of values », avec 2014 il passe à l'étape
suivante. Le produit opérationnel s'actualise mensuellement avec 15 jours de retard — c'est pourquoi
octobre 2026 n'était pas encore publié le 1ᵉʳ novembre 2026.

> **[INFÉRENCE]** Les deux produits ne sont pas interchangeables : le consolidé est forcé par ERA-40
> puis ERA-Interim, l'opérationnel par l'analyse opérationnelle de l'ECMWF. La fiche indique que,
> **pour 2015-aujourd'hui, les données du CDS diffèrent de celles de CMEMS**, parce que le forçage
> atmosphérique et les observations diffèrent. Comparer une série ORAS5-CDSc à une série
> ORAS5-CMEMS, c'est comparer deux produits différents.

### 1.3 Ce que la source ne permet pas : la zone

**[FAIT]** Le formulaire du produit mensuel compte **six** paramètres — `product_type`,
`vertical_resolution`, `variable`, `year`, `month`, `licences` — et **aucun paramètre de zone**.
Le produit est **global**, et le coût de l'API le confirme : il vaut **1 par variable et par mois**,
quelle que soit la résolution verticale demandée.

> **Conséquence pour la mission.** « Un petit échantillon sur une zone » n'est pas une propriété que
> l'on demande à ORAS5 : c'est une découpe que l'on fait **après** avoir téléchargé le champ global.
> Le sous-ensemble demandé (44–48 °N, 6–2 °O) représente quelques centaines de points sur 0,25° —
> pour un téléchargement de l'océan entier. C'est le premier argument chiffré pour une voie
> **ponctuelle** plutôt que globale.

### 1.4 La voie ponctuelle, et ce qu'elle ne donne pas

**[FAIT]** L'entrée `reanalysis-oras5-timeseries` organise l'accès **par point** : son formulaire porte
un widget `location`, et l'aide du producteur est explicite — *« The returned data will contain the
closest data point on the native grid **with no interpolation** »*. Deux conséquences :

- le point demandé n'est pas un point arbitraire : c'est **le point de la grille native le plus
  proche**, et il faut le savoir ;
- l'entrée ne propose que **15 variables**, dont `salinity`, `sea_surface_temperature`,
  `sea_surface_salinity`, `sea_surface_height` — **pas** de température en profondeur, **pas** de
  courant.

> **Conclusion de la qualification.** La voie ponctuelle donne la **salinité** au point, pas la
> température en profondeur ni le courant : elle ne satisfait pas, seule, la commande de la mission.
> La voie 3D est le produit mensuel global. Les deux sont complémentaires, et c'est un fait
> d'architecture : le CDS a fait le choix de la.globalité pour ORAS5.

### 1.5 Le coût, et le blocage

**[FAIT]** L'API CDS calcule le coût **avant** l'exécution :

| Commande | Coût annoncé | Limite |
|---|---|---|
| 1 variable, 1 mois, tous niveaux | 1,0 | 360,0 |
| 1 variable, 1 mois, niveau unique | 1,0 | 360,0 |
| **4 variables 3D, 1 mois** | **4,0** | 360,0 |
| 4 variables 3D, 12 mois | 48,0 | 360,0 |

**[FAIT]** Le coût est **1 par variable et par mois** — il ne dit **rien** du volume réel en octets,
puisque `all_levels` et `single_level` coûtent pareil. C'est une unité de requête, pas une taille.

**[FAIT]** L'exécution de la commande visée (4 variables 3D, janvier 2026, produit opérationnel)
renvoie **HTTP 403** : *« required licences not accepted »*. Le corps de la réponse n'est **pas**
conservé par le socle — c'est l'adaptation A9, déjà signalée par ATMO-002, qui se re-manifeste.

**[FAIT]** La licence requise est unique : **`cc-by`**, révision 1, **CC-BY-4.0**. Elle doit être
acceptée par le titulaire du compte ; l'API ne la contourne pas — passer `licences` dans le corps de
la requête ne change rien au 403.

> **[NON VÉRIFIÉ]** le fichier lui-même. L'**échantillon tridimensionnel** n'a pas pu être extrait :
> la commande est validée, mais l'acceptation de la licence manque. **La marche à suivre** : accepter
> la licence sur
> `https://cds.climate.copernicus.eu/datasets/reanalysis-oras5?tab=download#manage-licences`,
> puis rejouer `experiments/marine_002_oras5.py`, qui enchaîne alors exécution, mise en attente,
> téléchargement et lecture de la signature du fichier.

---

## 2. Argo — un profil réel, ouvert et qualifié

**[FAIT]** Le profil ouvert est `coriolis/2904125/profiles/R2904125_164.nc`, downloadable sans
secret sur `https://data-argo.ifremer.fr/dac/<chemin de l'index>` — **23 296 octets**, signature
`CDF\x01`, soit du **netCDF-3 classique**. Il a été **localisé dans l'index global** par
position : 47,019 N / 4,229 O, projet **ASPEX**, floatter **ARVOR_C** de l'**Ifremer**, cycle 164,
le **1ᵉʳ novembre 2026**.

### 2.1 La coordonnée verticale

**[FAIT]** L'axe `Z` est porté par `PRES`, dont l'unité est **`decibar`** et dont l'attribut
`long_name` est *« Sea water pressure, equals 0 at sea-level »*. Les niveaux sont :

```
0,30 · 1,30 · 2,30 · 3,30 · 4,30 · 5,30 · 6,30 · 7,30 … 24,30 … 36,40 … 48,40 … 60,60 …
72,60 … 84,30 … 96,30 … 108,00 … 120,00 … 126,00 … 127,00 … 128,00 · 129,00
```

Les écarts vont de **0,70** à **1,20 dbar** : la grille est **irrégulière**, et l'attribut
`VERTICAL_SAMPLING_SCHEME` vaut *« Primary sampling: averaged [] »*.

> **Ce que cela interdit.** Toute hypothèse du type « le niveau 25 est à 50 mètres » est fausse ici :
> le 26ᵉ niveau est à 24,30 dbar, le 37ᵉ à 36,40. Et la pression n'est pas une profondeur : la
> conversion passe par la masse volumique de l'eau de mer, qui dépend de la température, de la
> salinité et de la pression elle-même. **La verticale est une coordonnée, pas un indice.**

### 2.2 Les unités

**[FAIT]**

| Grandeur | Unité | Portée observée | Nature |
|---|---|---|---|
| `PRES` | `decibar` | 0,30 → 129,00 | pression *in situ* |
| `TEMP` | `degree_Celsius` | 12,573 → 15,263 | température **in situ**, échelle ITS-90 |
| `PSAL` | `psu` | 35,438 → 35,563 | salinité **pratique** |

> **À quoi cela oblige.** La température Argo est **in situ** (ITS-90) ; ORAS5 publie une
> **température potentielle**. Ce sont deux grandeurs différentes, et la conversion n'est pas
> neutre : elle dépend de la pression et de la salinité, donc du niveau. De même, la salinité pratique
> (psu) n'est pas la salinité absolue (g/kg). Comparer une série Argo à une série de modèle
> suppose de **dire** laquelle des deux on compare.

### 2.3 La convention d'absence, par variable

**[FAIT]** Chaque variable porte son **propre** `_FillValue` : `99999.0` pour les variables
numériques, et **`" "`** (un espace) pour les variables de qualité — ce sont des codes caractère.
Sur ce profil en temps réel, les trois variables ajustées (`PRES_ADJUSTED`, `TEMP_ADJUSTED`,
`PSAL_ADJUSTED`) sont **entièrement** en valeur de remplissage : **130 niveaux sur 130**.

> **Ce que cela interdit.** Une version antérieure de ce script comptait « 130 niveaux modifiés » en
> comparant `PRES` et `PRES_ADJUSTED` — c'était faux : c'était 130 **valeurs de remplissage**. La
> valeur ajustée **n'existe pas encore** sur un profil en temps réel ; elle n'est pas « nulle », elle
> est **absente**, et son absence a une cause : l'ajustement en mode différé n'est pas encore
> publié. C'est l'adaptation **M3** — la convention d'absence est **par variable** — qui se vérifie
> ici sur un deuxième périmètre.

### 2.4 Les indicateurs de qualité

**[FAIT]** La qualité est un **code caractère** par niveau. L'attribut `conventions` vaut
`"Argo reference table 2"` et `_FillValue` vaut `" "` : le fichier **ne contient pas** le
vocabulaire, il **renvoie** vers une table externe. Sur ce profil, `PRES_QC`, `TEMP_QC` et `PSAL_QC`
valent **`1` sur les 130 niveaux**.

**[FAIT]** La table 2 de l'Argonaut (*Argo User's Manual* §3.2.1 et *Argo Quality Control Manual for
CTD and Trajectory Data*, annexe 4.1) donne le vocabulaire :

| Code | Signification |
|---|---|
| 0 | aucun contrôle qualité effectué |
| **1** | **bonne donnée** |
| 2 | probablement bonne donnée |
| 3 | mauvaise donnée potentiellement corrigeable |
| 4 | mauvaise donnée, non corrigeable |
| 5 | valeur modifiée |
| 6, 7 | non utilisés |
| 8 | valeur estimée (interpolée, extrapolée) |
| 9 | valeur absente |

**[FAIT]** Pour le flag **de profil** (table 2a), les flags **1, 2, 5 et 8** comptent comme « bons »,
le flag **9** est exclu du calcul, et **tous les autres sont « mauvais »**. Le profil porte
aussi `PROFILE_PRES_QC`, `PROFILE_TEMP_QC`, `PROFILE_PSAL_QC` (table 2a).

> **[INFÉRENCE]** Le vocabulaire est **externe**, comme la table des sentinelles NDBC. Un décodeur
> qui ne connaît pas la table **ne peut pas** qualifier une valeur : il peut seulement constater
> qu'un code est présent. C'est la même conclusion que pour NDBC, appliquée à un second périmètre.

### 2.5 La structure du profil

**[FAIT]** `featureType = trajectoryProfile`, `Conventions = Argo-3.1 CF-1.6`. Dimensions :
`N_PROF = 1`, `N_LEVELS = 130`, `N_PARAM = 3`, `N_CALIB = 1`, `N_HISTORY = 3`. Le fichier porte
`STATION_PARAMETERS = (PRES, TEMP, PSAL)`, la chaîne d'historique
`2026-11-01T12:31:22Z creation; 2026-11-01T12:31:25Z last update (coriolis COQC software)`, et
trois enregistrements d'historique de traitement (institution, action, pas de test appliqué).

**[FAIT]** `DATA_MODE = R` : temps réel. Les valeurs de ce profil **seront remplacées** par les
valeurs ajustées en mode différé. La source n'est donc **pas figée**, et le `DATE_UPDATE` du fichier
(12:31:25 le 1ᵉʳ novembre 2026) est l'instant où cette version a été connue.

---

## 3. GLORYS12 — la voie qui reste fermée

**[FAIT]** Ce que MARINE-001 avait établi tient : le catalogue STAC de Copernicus Marine est
**ouvert** et `GLOBAL_MULTIYEAR_PHY_001_030` (GLORYS12) y est décrit comme *« Global Ocean Physics
Reanalysis »*, 1/12°, 50 niveaux, altimétrie à partir de 1993, avec assimilation d'observations. Mais
la fiche produit **n'expose aucun actif de données** (seule une vignette), et le paquet de données
répond **403 AccessDenied** — l'accès passe par un compte MyOcean.

**[FAIT]** Aucun identifiant Copernicus Marine n'est présent dans le dépôt, et l'API d'observation
Météo-France répond **403 `900908 Resource forbidden`** avec la clé dont nous disposons : la clé
ouvre l'API **climatologique**, l'observation relève d'un **autre abonnement**. Le chemin marine
n'est donc pas un simple oubli de variable d'environnement : c'est un **abonnement distinct**.

> **[NON VÉRIFIÉ]** le sous-ensemble quotidien GLORYS12 sur la zone étudiée. **La marche à suivre** :
> un compte Copernicus Marine gratuit, puis ses identifiants dans le `.env` ignoré, sous des noms
> **qui n'existent pas encore** dans le dépôt (`COPERNICUS_MARINE_USERNAME`,
> `COPERNICUS_MARINE_PASSWORD`), et le client officiel `copernicusmarine` — qui n'est pas installé.
> Tant que ces trois éléments manquent, **aucune** requête GLORYS12 n'est possible, et le
> sous-ensemble quotidien reste non vérifié.

---

## 4. L'arbitrage : M2, M4 et M5 sur des fichiers réels

### M2 — la dimension verticale

**[FAIT] Ce que les fichiers montrent.** L'océan est en volume, et l'axe vertical **n'est pas la
même chose** d'une source à l'autre :

| Source | Axe vertical | Unité | Grille |
|---|---|---|---|
| Argo (in situ) | `PRES`, `axis="Z"` | **decibar** (pression) | **irrégulière**, propre au profil (écarts 0,70–1,20) |
| ORAS5 (modèle) | profondeur de niveau | **mètres** | 75 niveaux de modèle, espacés de 1 m en surface à 200 m en profondeur |

**[FAIT] Ce que le contrat sait faire.** `SpatialRef` (autorité + code), `Point(x, y)` — **deux axes,
et rien d'autre**, les axes n'étant même pas nommés ; `BoundingBox(west, south, east, north)` ;
`Footprint` (surface) ; `RasterGrid` (raster 2D). **Aucun** de ces objets ne porte de verticale.
Et `Observation` non plus : elle ne porte qu'un `spatial_ref: str`, qui **pointe** vers un objet
spatial.

> **Arbitrage M2 — un besoin, pas une abstraction.** Il ne faut pas un « contrat 3D » : il faut que
> **l'observationmarine puisse dire où elle est dans le volume**. Deux formes sont possibles, et le
> choix appartient au propriétaire du contrat :
>
> 1. **une coordonnée verticale sur l'observation** — un objet `Vertical(value, unit, kind)` avec
>    `kind ∈ {pression, profondeur, niveau}` et son unité propre. Elle est **attachée à la
>    mesure**, ce qui est le seul endroit où elle est correcte : la pression d'un niveau ne vaut pas
>    pour le niveau voisin ;
> 2. **un troisième axe dans `Point`** — `(x, y, z)`. C'est plus elegant, mais `Point` est partagé
>    avec le périmètre EO, et un axe surnuméraire change le sens de toutes les constructions
>    existantes (boîtes, empreintes, grilles).
>
> **Le besoin minimal, établi par les fichiers** : l'observation doit pouvoir porter une **valeur
> verticale avec son unité et sa nature** (pression en dbar ≠ profondeur en m ≠ indice de niveau),
> **et** le calcul doit savoir qu'une profondeur en mètres n'est **pas** derivable d'une pression
> sans la masse volumique de l'eau de mer. **Signé, non appliqué.**

### M4 — le profil, pas la valeur

**[FAIT] Ce que le fichier montre.** Un profil Argo n'est pas une observation : c'est **390
observations** (3 grandeurs × 130 niveaux) qui partagent **le même instant**, **la même position**, et
**la même identité de profil**. Le contrat sait décomposer cela en observations distinctes — l'
`observation_id` les distingue — mais il n'a **rien** pour dire que ces 390 observations **forment un
profil**.

**[FAIT] Ce que le contrat sait faire.** `Observation` porte `observation_id`, `source_id`,
`quantity`, `unit`, `temporal`, `evidence_id`, `value`, `validity`, `missing_reason`, `spatial_ref`,
`key`, `revision_of`, `quality_status`. Le champ `key` est une **chaîne libre** ; c'est aujourd'hui
le seul endroit où une identité de profil pourrait se loger.

> **Arbitrage M4 — deux besoins distincts, dont un seul est nouveau.**
>
> 1. **L'identité de profil** : quelles observations appartiennent au même profil. C'est un besoin
>    **nouveau** — un identifiant de profil, porté par l'observation, et non une convention sur une
>    chaîne libre. Le dépôt évite ailleurs l'inférence (« l'autorité et le code sont portés par la
>    donnée, jamais déduits du contexte ») : l'appliquer ici est cohérent.
> 2. **L'identité de niveau** : le rang du niveau dans le profil. C'est un besoin **déjà couvert** :
>    la **valeur de la coordonnée verticale** (M2) suffit, et un index de niveau serait une donnée
>    en double, derivable, donc fragile.
>
> **Point de vigilance — le partage d'instant.** Plusieurs observations partagent le même
> `TemporalStamp` et le même `spatial_ref`. C'est exact, mais **rien ne le dit** : un compteur qui
> compterait les observations par instant verrait « 390 observations à cet instant » et ne
> distinguerait pas un profil d'une anomalie. **Signé, non appliqué.**

### M5 — la lecture netCDF

**[FAIT] Ce que les fichiers montrent.** Il y a **deux** formats, et ils ne se lisent pas de la même
façon :

| Source | Format livré | Lecteur |
|---|---|---|
| Argo (GDAC Ifremer) | **netCDF-3 classique** (`CDF\x01`) | `scipy.io.netcdf_file` — **scipy est déjà déclaré** au dépôt |
| ORAS5 (CDS) | **NetCDF4 / HDF5** | `h5py` ou `netCDF4` — **absents** de l'environnement |
| ORAS5 (CDS, voie ponctuelle) | **CSV** disponible | bibliothèque standard |

**[FAIT]** Aucun des deux formats n'est couvert par les dépendances actuelles à l'exclusion de
`scipy` — et `scipy` couvre déjà le format d'Argo. `numpy` et `scipy` sont les seules dépendances
de runtime déclarées, avec un motif explicite dans `pyproject.toml` : *« une bibliothèque s'installe
quand un module du dépôt l'importe réellement »*.

> **Arbitrage M5 — une dépendance, optionnelle, et une règle de préférence.**
>
> 1. **Une** dépendance de plus, `h5py` (ou `netCDF4`), **optionnelle** — un extra, comme
>    `explorer`. Elle n'est justifiée que si un module du dépôt importe réellement du netCDF4 ;
>    aujourd'hui, **aucun module ne le fait**, et l'extraction d'ORAS5 reste au stade de la
>    reconnaissance.
> 2. **Une règle de format, pas de bibliothèque** : quand une source offre **plusieurs** formats,
>    **préférer celui qui n'ajoute pas de dépendance**. ORAS5 sert le CSV ; le CSV se lit avec la
>    bibliothèque standard. C'est une règle de sourcé, pas une préférence de goût.
> 3. **Ce que M5 n'est pas** : M5 n'est pas « installer un lecteur netCDF ». C'est « **deux familles
>    de fichiers, deux lecteurs** », dont un déjà présent.
>
> **Signé, non appliqué.**

### M3 — la convention d'absence, confirmée par un second périmètre

**[FAIT]** Argo confirme M3 sur des fichiers réels, et l'aggrave : la valeur de remplissage est
**par variable** (`99999.0` pour les numériques, `" "` pour les codes caractère), et elle **varie
selon la variable au sein d'un même fichier**. Les codes de qualité ont en outre un vocabulaire
**documenté à l'extérieur** du fichier.

> **Arbitrage M3 — inchangé, et renforcé.** Le socle n'a pas de place pour déclarer une convention
> d'absence : elle est **propre à la source**, et doit être **documentée** par l'adaptateur qui
> connaît la source. Un adaptateur qui ne connaît pas la table des sentinelles ne doit pas
> interpréter : il doit refuser le fichier, ou le signaler. **Signalée, non appliquée.**

---

## 5. Les besoins exacts, fichier par fichier

| # | Besoin | Où il se pose | Forme exacte | État |
|---|---|---|---|---|
| **M2** | Une **coordonnée verticale** portee par l'observation | `src/torne/contracts/observation.py` (et, si on l'y préfère, `spatial.py`) | un objet `Vertical(value, unit, kind)` avec `kind ∈ {pression, profondeur, niveau}` et son unité propre ; `Observation` le porte, ou `Point` gagne un troisième axe | **signalée, non appliquée** — contrat partagé |
| **M4** | Une **identité de profil** portée par l'observation | `src/torne/contracts/observation.py` | un `profile_id` explicite ; **pas** une convention sur la chaîne libre `key` | **signalée, non appliquée** — contrat partagé |
| **M5** | Un **lecteur netCDF4** | `pyproject.toml` (extra optionnel) | `h5py` (ou `netCDF4`), **optionnel**, dans un extra ; et une règle de source : **préférer le CSV** quand la source en propose un | **signalée, non appliquée** — `pyproject.toml` est partagé |
| **M3** | La **convention d'absence par variable** | `src/torne/acquisition/contracts.py` ou le décodeur de l'adaptateur | une déclaration par variable (valeur de remplissage + table des codes de qualité), apprise de la source et documentée | **signalée, non appliquée** — contrat partagé |
| **M6** | Une **clé CMEMS** distincte | `.env` (ignoré par git) | `COPERNICUS_MARINE_USERNAME` / `COPERNICUS_MARINE_PASSWORD` | **nouvelle** — à créer, non versionné |
| **M7** | L'**acceptation de la licence CC-BY** | compte CDS du propriétaire | un clic sur la page « manage-licences » du jeu `reanalysis-oras5` | **nouvelle** — geste du propriétaire |

> **Rien de tout cela n'a été appliqué.** Les quatre premières lignes touchent des **contrats
> partagés**, dont deux sont des fichiers que d'autres périmètres sont en train d'écrire. La mission
> demande de **documenter avant de modifier** : c'est fait, et l'arbitrage appartient au propriétaire
> de l'intégration.

---

## 6. Ce qui n'a pas pu être vérifié

- **[NON VÉRIFIÉ]** l'**échantillon tridimensionnel ORAS5** : la commande est validée (coût 4,0,
  combinaison acceptée), mais la licence CC-BY du compte n'est pas acceptée. **La marche à suivre** :
  accepter la licence, puis rejouer `experiments/marine_002_oras5.py`.
- **[NON VÉRIFIÉ]** le **format réel du fichier livré** par le CDS pour ORAS5 : la fiche produit
  annonce NetCDF4 et le script le vérifiera sur les octets reçus, mais aucun octet n'a été reçu.
- **[NON VÉRIFIÉ]** le **sous-ensemble quotidien GLORYS12** sur la zone étudiée : il manque un compte
  Copernicus Marine, ses identifiants, et le client officiel.
- **[NON VÉRIFIÉ]** la **route ouverte ICDC** (Hambourg) pour ORAS5, mentionnée par la fiche produit :
  `www.icdc.mpi-met.mpg.de` **ne résout pas en DNS** depuis ce poste. **La marche à suivre** : réessayer
  depuis un autre réseau.
- **[NON VÉRIFIÉ]** la **conversion pression → profondeur** : elle dépend de la masse volumique de
  l'eau de mer, donc de la température, de la salinité et de la pression. Aucun calcul n'a été fait
  ici, et c'est hors mission.
- **[NON VÉRIFIÉ]** le **tableau des flags de profil** (table 2a) sur d'autres profils : seul le
  profil ouvert a été qualifier.

---

## 7. La suite proposée

1. **Accepter la licence CC-BY** d'ORAS5 (geste du propriétaire, une minute) et rejouer le script :
   la commande est déjà validée, le reste s'enchaîne.
2. **Décider M2 et M4** — la forme exacte du besoin est §4 et §5 ; l'arbitrage est au propriétaire de
   l'intégration, pas à cette mission.
3. **Ouvrir un compte Copernicus Marine** et renseigner `COPERNICUS_MARINE_USERNAME` et
   `COPERNICUS_MARINE_PASSWORD` dans le `.env` ignoré, pour tester GLORYS12 enfin — et pour
   trancher la question de la **fréquence** : ORAS5 est **mensuel**, GLORYS12 est **quotidien**, et la
   question du panache (§4 de MARINE-001) se pose au pas de temps des épisodes.
4. **Décider M5** : installer `h5py` en extra optionnel, ou adopter la règle « le CSV d'abord ».

---

## 8. Les produits

| Fichier | Rôle |
|---|---|
| `experiments/marine_002_profil_argo.py` | ouvrir un profil Argo réel et le qualifier : verticale, unités, absence, qualité, structure |
| `experiments/marine_002_oras5.py` | tester ORAS5 : reconnaissance du produit, coût, exécution, téléchargement, lecture de la signature |
| `data/marine-001/argo/R2904125_164.nc` | la preuve brute du profil Argo ouvert (dossier ignoré par git) |

**État.** `ruff check` et `ruff format` propres sur les deux scripts. **Aucun contrat partagé n'a été
modifié** : les besoins sont chiffrés en §4 et §5, et soumis à arbitrage.
