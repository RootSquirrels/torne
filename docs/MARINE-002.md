# MARINE-002 — Tester les sources 3D, et chiffrer les besoins

> **Mission de qualification.** Cette mission demandait cinq choses : **tester ORAS5** et en extraire
> un échantillon tridimensionnel de salinité, température et courant sur une zone définie ; **ouvrir un
> profil Argo réel** et qualifier ses coordonnées verticales, ses unités, ses indicateurs de qualité et
> sa structure ; **tester GLORYS12** et vérifier un sous-ensemble quotidien sur la zone étudiée ;
> **arbitrer M2, M4 et M5** sur ces fichiers réels ; et **documenter les besoins exacts avant de modifier
> les contrats partagés**.
>
> **Version 2 — les deux blocages de la version 1 sont levés.** La licence CC-BY d'ORAS5 a été acceptée
> et les identifiants Copernicus Marine ont été ajoutés au `.env` ignoré. Les conclusions de la
> version 1 sur ORAS5 et sur GLORYS12 sont **réévaluées à la lumière des fichiers réels** ; le
> §6 dit précisément ce qui a changé.
>
> Ce dossier ne modifie **aucun** contrat partagé. Il en **chiffre** le besoin.
>
> Toutes les mesures ci-dessous ont été faites **par exécution**, le **1ᵉʳ novembre 2026**, sur des
> données réelles.

**Règle de preuve.** **[FAIT]** (observé sur une requête ou sur les octets reçus), **[INFÉRENCE]**
(lecture plausible d'un fait observé), **[NON VÉRIFIÉ]** (non vérifié, avec la marche à suivre).

**Reproduction.**

```bash
uv run python experiments/marine_002_profil_argo.py        # ouvrir et qualifier un profil Argo réel
uv run python experiments/marine_002_oras5.py  <sortie> <annee> <mois>   # ORAS5 : reconnaissance, coût, exécution
uv run python experiments/marine_002_echantillon_oras5.py   # découper l'échantillon 3D sur la zone
uv run python experiments/marine_002_glorys12.py            # GLORYS12 : sous-ensemble quotidien, et sa conformité
```

> **Environnement.** `h5py` (3.16.0) et `copernicusmarine` (2.5.0) ont été installés **dans le venv
> local** pour mener cette qualification. **Ils ne sont pas déclarés** dans `pyproject.toml`, qui est un
> fichier partagé et n'a pas été touché : l'installation est une **preuve** du besoin de M5, pas sa
> réalisation. `numpy` (2.5.4) et `scipy` (1.18.1) sont restés inchangés.

---

## 0. Ce que la mission a changé

1. **Les deux sources 3D répondent, et l'une d'elles coûte 1 842 570 984 octets pour rendre la
   même information que l'autre livre en 2 049 966.** ORAS5 est un produit **global** sans paramètre de
   zone : l'« échantillon tridimensionnel sur une zone » s'obtient en téléchargeant l'océan entier
   (1,84 Go, 4 fichiers de 460,6 Mo) puis en découpant. GLORYS12 **sait** découper : la même zone, sur
   trois jours, pèse **2,05 Mo**. Ce n'est pas une question de débit : c'est une question
   d'**architecture de la source**, et c'est le premier élément de la décision.

2. **Trois géométries de grille, trois vocabulaires verticaux, quatre conventions d'absence** — le
   tout sur des fichiers réels. ORAS5 est **curviligne** (tripolaire, `nav_lat`/`nav_lon` en 2D) ;
   GLORYS12 est **régulier** (1/12°) ; Argo est un **profil**. Une coupe « par indices » qui marche
   pour l'une ne marche pas pour l'autre, et une convention d'absence copiée d'une source à l'autre
   produit des mesures fausses.

3. **M5 est maintenant chiffré, pas supposé.** Argo sert du **netCDF-3 classique** — lisible par
   `scipy.io.netcdf_file`, et `scipy` est **déjà déclaré** au dépôt. ORAS5 et GLORYS12 servent du
   **NetCDF4 (HDF5)** — illisible par `scipy`. Le besoin est donc **exactement une** dépendance
   nouvelle (`h5py` ou `netCDF4`), optionnelle, plus une règle de source.

4. **M3 est confirmé trois fois, et la troisième fois il est subtil.** La valeur de remplissage de
   GLORYS12 est **−32767 en entier compressé**, avec un facteur d'échelle et un décalage : appliquée
   avant d'écarter le remplissage, elle devient une **mesure plausible** — −2,99 °C pour la
   température potentielle. L'ordre des opérations n'est pas un détail, c'est une correction de
   données.

5. **Un attribut racine peut mentir.** Le fichier GLORYS12 obtenu porte `field_date = 2021-06-30` :
   c'est **faux**, c'est un résidu de gabarit du producteur. La période réellement livrée — trois pas
   quotidiens, 2026-09-01 à 2026-09-03 — est dans la **variable** `time`. La règle du dépôt
   (« l'autorité et le code sont portés par la donnée, jamais déduits du contexte ») s'applique ici
   sous une forme plus dure : **la donnée elle-même porte la vérité, l'attribut peut être un
   copier-coller**.

6. **Les deux réanalyses concordent entre elles, et l'in situ les confirme.** Au point du floatter
   Argo 2904125 : ORAS5 donne 35,298 psu et 19,747 °C (potentielle), GLORYS12 donne 35,307 g/kg et
   20,569 °C — **0,01 de salinité et 0,82 °C d'écart**, avec des courants de même signe et de même
   grandeur. Le profil Argo, deux mois plus tard et *in situ*, donne 15,26 °C en surface : c'est le
   refroidissement d'automne. Les trois se tiennent.

---

## 1. ORAS5 — la réanalyse 3D qui répond

### 1.1 Ce que le catalogue expose

**[FAIT]** ORAS5 est distribué par le Climate Data Store sous deux entrées :

| Entrée | Identifiant | Nature |
|---|---|---|
| Champs mensuels globaux | `reanalysis-oras5` | la réanalyse, en 3D, sur 75 niveaux |
| Séries ponctuelles | `reanalysis-oras5-timeseries` | l'accès **par point**, prioritaire |

**[FAIT]** La fiche produit décrit : projection **tripolaire**, résolution horizontale **0,25° ×
0,25°**, couverture **globale**, **75 niveaux** de modèle pour les variables 3D, de **0,51 m** à
**5 902 m**, l'espacement croissant de **1 m** en surface à **200 m** en profondeur, et une **moyenne
mensuelle**. Le format livré est **NetCDF4 (CF-1.6)**.

### 1.2 Les deux produits, et la frontière 2015

**[FAIT]** Les contraintes de la source distinguent deux produits :

| Produit | Période | Variables 3D disponibles | Mois publiés |
|---|---|---|---|
| `consolidated` | **1958 → 2014** | `salinity`, `potential_temperature`, `zonal_velocity`, `meridional_velocity` | 01 → 12 |
| `operational` | **2015 → présent** | les quatre, **plus** `rotated_zonal_velocity` et `rotated_meridional_velocity` | **01 → 09** (puis 10 → 12 pour 2015-2025) |

**[FAIT]** La frontière a été **observée par le refus de l'API** : `consolidated` avec l'année 2025
renvoie « Request has not produced a valid combination of values », avec 2014 il passe à l'étape
suivante.

> **[INFÉRENCE]** Les deux produits ne sont pas interchangeables : le consolidé est forcé par ERA-40
> puis ERA-Interim, l'opérationnel par l'analyse opérationnelle de l'ECMWF. La fiche indique que,
> **pour 2015-aujourd'hui, les données du CDS diffèrent de celles de CMEMS**, parce que le forçage
> atmosphérique et les observations diffèrent. Comparer une série ORAS5-CDSc à une série
> ORAS5-CMEMS, c'est comparer deux produits différents.

### 1.3 L'exécution — les trois temps du protocole

**[FAIT]** Le protocole du CDS est en **trois temps**, et chacun a son code de retour :

| Étape | Requête | Réponse observée |
|---|---|---|
| 1. valider | `POST /retrieve/v1/processes/reanalysis-oras5/execution` | **HTTP 201**, corps `{"jobID": …, "status": "accepted"}` |
| 2. suivre | `GET /retrieve/v1/jobs/<jobID>` | `status` : `accepted` → `running` → `successful` |
| 3. récupérer | `GET /retrieve/v1/jobs/<jobID>/results` | `asset.value.href` + `file:size` |

**[FAIT]** Deux pièges que la sonde a payés : l'identifiant s'appelle **`jobID`** (et non
`identifier`), et le fichier **n'est pas** dans `asset` de la réponse de suivi mais dans le lien
**`results`** — il faut y aller. Le code de retour de l'exécution est **201**, pas 202.

**[FAIT]** Le coût est annoncé **avant** l'exécution, et vaut **1 par variable et par mois** :

| Commande | Coût | Limite |
|---|---|---|
| 1 variable, 1 mois, tous niveaux | 1,0 | 360,0 |
| 1 variable, 1 mois, niveau unique | 1,0 | 360,0 |
| **4 variables 3D, 1 mois** | **4,0** | 360,0 |
| 4 variables 3D, 12 mois | 48,0 | 360,0 |

Le coût ne dit **rien** du volume réel en octets, puisque `all_levels` et `single_level` coûtent
pareil : c'est une unité de requête, pas une taille.

### 1.4 Ce que la source ne permet pas : la zone

**[FAIT]** Le formulaire du produit mensuel compte **six** paramètres — `product_type`,
`vertical_resolution`, `variable`, `year`, `month`, `licences` — et **aucun paramètre de zone**. Le
produit est **global**.

**[FAIT]** Le fichier livré est une **archive zip** de **1 842 570 984 octets**, contenant **quatre**
netCDF de **460,6 Mo** chacun, **stockés** (non compressés dans l'archive) :

```
vomecrty_control_monthly_highres_3D_202609_OPER_v0.1.nc
vosaline_control_monthly_highres_3D_202609_OPER_v0.1.nc
votemper_control_monthly_highres_3D_202609_OPER_v0.1.nc
vozocrtx_control_monthly_highres_3D_202609_OPER_v0.1.nc
```

Le téléchargement a pris **84 s** (1,84 Go, soit ≈ 22 Mo/s).

> **Conséquence de mission.** « Un petit échantillon sur une zone » n'est pas une propriété que l'on
> demande à ORAS5 : c'est une découpe que l'on fait **après** avoir téléchargé le champ global. Le
> sous-ensemble demandé représente 359 mailles sur 0,25° — pour 1,84 Go.

### 1.5 La découpe, et la géométrie réelle

**[FAIT]** La grille d'ORAS5 est **curviligne** : `nav_lat` et `nav_lon` sont deux champs **2D** de
forme **(1021, 1442)**, et `vosaline` a la forme **(1, 75, 1021, 1442)** — `(temps, niveau, y, x)`.
Une zone ne se découpe donc **pas** par une tranche rectangulaire d'indices : il faut trouver les
indices dont les coordonnées *variables* tombent dans le rectangle.

**[FAIT]** La découpe demandée (44–48 °N, 6–2 °O) donne **359 mailles**, dans le rectangle
`i[695:719] · j[1123:1140]`, couvrant en réalité 43,869–48,026 °N et 6,146–1,711 °O — c'est-à-dire
**plus large que la demande**, parce qu'une maille est un polygone, pas un point.

**[FAIT]** Les niveaux sont des **niveaux de modèle**, pas des profondeurs demandées : la demande
« 0, 10, 20, 50, 100, 200, 500, 1000 m » est servie par les indices 0, 7, 11, 17, 23, 30, 39 et 46,
dont les profondeurs réelles sont **0,51 · 9,82 · 19,43 · 47,21 · 97,04 · 199,79 · 508,64 · 1 045,85 m**.

**[FAIT]** L'échantillon extrait (8 niveaux × 24 × 17 × 4 grandeurs) est écrit en **netCDF-3** par
`scipy.io.netcdf_file` — **56 492 octets**, avec une dépendance **déjà déclarée** au dépôt.

### 1.6 Le profil vertical, et ce que l'absence y signifie

**[FAIT]** Valeurs ORAS5 de septembre 2026 au point le plus proche du floatter Argo
(47,0912 °N / 4,1082 °O, à 15,6 km) :

| Profondeur | Salinité (PSU) | Température potentielle (°C) | Courant méridional (m/s) |
|---|---|---|---|
| 0,51 m | 35,298 | 19,747 | −0,021 |
| 9,82 m | 35,299 | 19,693 | −0,018 |
| 19,43 m | 35,298 | 19,632 | −0,017 |
| 47,21 m | 35,345 | 14,827 | −0,019 |
| 97,04 m | 35,422 | 11,958 | −0,014 |
| 199,79 m et au-delà | **ABSENT** | **ABSENT** | **ABSENT** |

**[FAIT]** La valeur de remplissage d'ORAS5 est **`_FillValue` = `missing_value` = 9,96921e+36**, et
elle marque **les niveaux sous le fond marin** : à cet endroit, le fond est entre 97 et 200 m. Sur
l'ensemble de l'échantillon de surface, **879 des 3 264 valeurs** sont des remplissages.

**[FAIT]** Sur la couche de surface de la zone : salinité **34,842 à 35,762** (moyenne 35,410),
température potentielle **17,123 à 22,327** (moyenne 20,783) — 375 valeurs valides sur 408.

**[FAIT]** Le profil montre une **couche de mélange d'environ 20 m** (19,6 °C jusqu'à 19,4 m), puis
une **thermocline très nette** : 19,632 °C à 19,4 m et 14,827 °C à 47,2 m, soit **4,8 °C perdus en
28 mètres**. C'est la structure verticale qui rend la question du panache observable : le signal de
surface est isolé dans les vingt premiers mètres.

**[FAIT]** Le temps est `time_counter`, en **`seconds since 2026-01-01`**, valant 22 291 200 s pour
septembre 2026, soit le **2026-09-16** : le mois moyen est estampé **au milieu du mois**.

### 1.7 La voie ponctuelle, et ce qu'elle ne donne pas

**[FAIT]** L'entrée `reanalysis-oras5-timeseries` organise l'accès **par point** : son formulaire porte
un widget `location`, et l'aide du producteur est explicite — *« The returned data will contain the
closest data point on the native grid **with no interpolation** »*. L'entrée ne propose que **15
variables**, dont `salinity`, `sea_surface_temperature`, `sea_surface_salinity`,
`sea_surface_height` — **pas** de température en profondeur, **pas** de courant.

> **Conclusion de la qualification.** La voie ponctuelle donne la **salinité** au point, pas la
> température en profondeur ni le courant : elle ne satisfait pas, seule, la commande de la mission.
> La voie 3D est le produit mensuel global. Les deux sont complémentaires, et c'est un fait
> d'architecture : le CDS a fait le choix de la globalité pour ORAS5.

---

## 2. Argo — un profil réel, ouvert et qualifié

**[FAIT]** Le profil ouvert est `coriolis/2904125/profiles/R2904125_164.nc`, téléchargeable sans
secret sur `https://data-argo.ifremer.fr/dac/<chemin de l'index>` — **23 296 octets**, signature
`CDF\x01`, soit du **netCDF-3 classique**. Il a été **localisé dans l'index global** par position :
47,019 N / 4,229 O, projet **ASPEX**, floatter **ARVOR_C** de l'**Ifremer**, cycle 164, le
**1ᵉʳ novembre 2026**.

### 2.1 La coordonnée verticale

**[FAIT]** L'axe `Z` est porté par `PRES`, dont l'unité est **`decibar`** et dont l'attribut
`long_name` est *« Sea water pressure, equals 0 at sea-level »*. Les niveaux sont :

```
0,30 · 1,30 · 2,30 · 3,30 · 4,30 · 5,30 · 6,30 · 7,30 … 24,30 … 36,40 … 48,40 … 60,60 …
72,60 … 84,30 … 96,30 … 108,00 … 120,00 … 126,00 · 127,00 · 128,00 · 129,00
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

### 2.3 La convention d'absence, par variable

**[FAIT]** Chaque variable porte son **propre** `_FillValue` : `99999.0` pour les variables
numériques, et **`" "`** (un espace) pour les variables de qualité — ce sont des codes caractère.
Sur ce profil en temps réel, les trois variables ajustées (`PRES_ADJUSTED`, `TEMP_ADJUSTED`,
`PSAL_ADJUSTED`) sont **entièrement** en valeur de remplissage : **130 niveaux sur 130**.

> **Ce que cela interdit.** Une version antérieure de ce script comptait « 130 niveaux modifiés » en
> comparant `PRES` et `PRES_ADJUSTED` — c'était faux : c'était 130 **valeurs de remplissage**. La
> valeur ajustée **n'existe pas encore** sur un profil en temps réel ; elle n'est pas « nulle », elle
> est **absente**, et son absence a une cause : l'ajustement en mode différé n'est pas encore publié.

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

### 2.5 La structure du profil

**[FAIT]** `featureType = trajectoryProfile`, `Conventions = Argo-3.1 CF-1.6`. Dimensions :
`N_PROF = 1`, `N_LEVELS = 130`, `N_PARAM = 3`, `N_CALIB = 1`, `N_HISTORY = 3`. Le fichier porte
`STATION_PARAMETERS = (PRES, TEMP, PSAL)`, la chaîne d'historique
`2026-11-01T12:31:22Z creation; 2026-11-01T12:31:25Z last update (coriolis COQC software)`, et
trois enregistrements d'historique de traitement.

**[FAIT]** `DATA_MODE = R` : temps réel. Les valeurs de ce profil **seront remplacées** par les
valeurs ajustées en mode différé. La source n'est donc **pas figée**, et le `DATE_UPDATE` du fichier
(12:31:25 le 1ᵉʳ novembre 2026) est l'instant où cette version a été connue.

---

## 3. GLORYS12 — le sous-ensemble quotidien est vérifié

**[FAIT]** Le compte Copernicus Marine fonctionne : le sous-ensemble a été **obtenu** avec le client
officiel `copernicusmarine` 2.5.0, en passant les identifiants **en paramètres d'appel** — rien n'a
été écrit sur le disque, et rien n'a été journalisé.

**[FAIT]** La commande : jeu `cmems_mod_glo_phy_my_0.083deg_P1D-m` (« daily mean fields from Global
Ocean Physics Analysis and Forecast updated Daily », version 202311), variables `thetao`, `so`, `uo`,
`vo`, boîte 44–48 °N / 6–2 °O, profondeur 0–1000 m, **2026-09-01 → 2026-09-03**. Le client a
signalé que la sélection de profondeur excédait les coordonnées du jeu, et l'a **écrêtée**.

**[FAIT]** Le fichier obtenu : **2 049 966 octets**, signature **`\x89HDF`** (netCDF-4), conventions
**CF-1.4**, `source = MERCATOR GLORYS12V1`, `institution = MERCATOR OCEAN`, écrit par
`h5netcdf 1.8.2`.

**[FAIT] La grille** est **régulière** : **49 latitudes** de 44,000 à 48,000 (pas 0,083332°), **49
longitudes** de −6,000 à −2,000 (pas 0,083333°) — **1/12°**, contre la grille curviline d'ORAS5.

**[FAIT] Les profondeurs** sont **35 niveaux** de **0,494 m** à **902,3 m**, après écrêtage de la
demande à 1000 m.

### 3.1 La conformité — et l'attribut qui ment

**[FAIT]** La période demandée (2026-09-01 → 2026-09-03, 3 jours) est **conforme** à la période
livrée, lue dans la **variable** `time` (`hours since 1950-01-01`, valeurs 672 048 / 672 072 /
672 096) : 2026-09-01, 09-02, 09-03.

> **[FAIT] L'attribut racine `field_date` du même fichier vaut `2021-06-30 00:00:00`. Il est FAUX.**
> C'est un résidu de gabarit du producteur, recopié d'un fichier antérieur. Il ne signale pas une
> erreur de la source — il signale qu'**un attribut racine n'est pas une donnée**. La règle du dépôt
> s'applique sous une forme plus dure : la vérité est dans la variable, et c'est elle qu'il faut
> vérifier.

### 3.2 L'échelle, et l'ordre des opérations

**[FAIT]** Les grandeurs sont stockées en entiers compressés, avec facteur d'échelle et décalage :

| Grandeur | Unité | Échelle | Décalage | Remplissage | `valid_min` |
|---|---|---|---|---|---|
| `thetao` | `degrees_C` | 0,00073244 | +21,0 | **−32767** | −32766 |
| `so` | `1e-3` | 0,00152593 | −0,00152593 | **−32767** | 1 |
| `uo` | `m s-1` | 0,00061037 | 0,0 | **−32767** | −3123 |
| `vo` | `m s-1` | 0,00061037 | 0,0 | **−32767** | −3680 |

> **[FAIT] Le piège.** La valeur de remplissage est **à l'intérieur de la plage encodée**. Si l'on
> applique l'échelle *avant* d'écarter le remplissage, une absence devient une **mesure plausible** :
> −32767 chez `thetao` donne 21,0 + (−32767 × 0,00073244) = **−2,99 °C**, et chez `so` donne
> **−50,0 g/kg**. C'est l'ordre des opérations qui décide de la correction.

**[FAIT]** `so` est en **`1e-3`** : c'est de la **salinité absolue** (g/kg), et non la salinité
pratique (psu) d'Argo. Ce n'est pas la même grandeur.

### 3.3 Le profil au point du floatter

**[FAIT]** Au point le plus proche du floatter Argo (47,0000 °N / 4,2500 °O, à 2,1 km en latitude et
1,8 km en longitude), le **2026-09-01** :

| Profondeur | Salinité (g/kg) | Température potentielle (°C) | u (m/s) | v (m/s) |
|---|---|---|---|---|
| 0,494 m | 35,3069 | 20,5686 | −0,0183 | −0,0372 |
| 1,541 m | 35,3038 | 20,4690 | −0,0171 | −0,0378 |
| 2,646 m | 35,3023 | 20,4038 | −0,0171 | −0,0385 |
| 5,078 m | 35,3008 | 20,3708 | −0,0171 | −0,0366 |
| 9,573 m | 35,3008 | 20,3554 | −0,0177 | −0,0354 |
| 15,810 m | 35,3393 | 20,3393 | −0,0183 | −0,0342 |
| 18,496 m | 35,2977 | 20,3056 | −0,0177 | −0,0336 |

### 3.4 Les trois sources au même endroit

**[FAIT]** Au point du floatter Argo 2904125 (47,019 °N / 4,229 °O) :

| Source | Date | Salinité | Température | Courant | Vertical |
|---|---|---|---|---|---|
| **Argo** (in situ) | 2026-11-01 | 35,438 → 35,563 **psu** (pratique) | 12,573 → 15,263 °C (**ITS-90 in situ**) | — | `PRES` en dbar, 130 niveaux irréguliers |
| **ORAS5** (modèle) | 2026-09 (estampé 09-16) | 35,298 **PSU** | 19,747 °C (potentielle) | v = −0,021 m/s | 75 niveaux de modèle, 0,51 → 5 902 m |
| **GLORYS12** (modèle) | 2026-09-01 | 35,307 **g/kg** (absolue) | 20,569 °C (potentielle) | u = −0,018, v = −0,037 m/s | 35 niveaux, 0,49 → 902 m |

> **Ce que cette comparaison autorise à dire.** Les deux réanalyses concordent entre elles :
> **0,01** d'écart sur la salinité (et sur des grandeurs qui ne sont pas identiques — pratique contre
> absolue), **0,82 °C** sur la température potentielle, des courants de même signe et de même
> grandeur. L'observation in situ, **deux mois plus tard** et en température *in situ*, donne 15,26 °C
> en surface : c'est le refroidissement d'automne, et il est **cohérent** avec les 20 °C de septembre.
> **Ce n'est pas** une validation : les dates ne coïncident pas, et les grandeurs ne sont pas les
> mêmes. C'est une **cohérence de vocabulaire et d'ordre de grandeur** — et c'est déjà beaucoup :
> cela veut dire qu'un modèle et une mesure peuvent être **mis en regard**, à condition de dire
> lequel on compare à quoi.

---

## 4. L'arbitrage : M2, M4 et M5 sur des fichiers réels

### M2 — la dimension verticale

**[FAIT] Ce que les fichiers montrent.** L'océan est en volume, et l'axe vertical **n'est pas la
même chose** d'une source à l'autre :

| Source | Axe vertical | Unité | Grille |
|---|---|---|---|
| Argo (in situ) | `PRES`, `axis="Z"` | **decibar** (pression) | **irrégulière**, propre au profil (écarts 0,70–1,20) |
| ORAS5 (modèle) | profondeur de niveau | **mètres** | 75 niveaux, 1 m en surface → 200 m en profondeur |
| GLORYS12 (modèle) | profondeur de niveau | **mètres** | 35 niveaux, 0,49 → 5 727 m |

**[FAIT] Ce que le contrat sait faire.** `SpatialRef` (autorité + code), `Point(x, y)` — **deux axes,
et rien d'autre**, les axes n'étant même pas nommés ; `BoundingBox(west, south, east, north)` ;
`Footprint` (surface) ; `RasterGrid` (raster 2D). **Aucun** de ces objets ne porte de verticale.
Et `Observation` non plus : elle ne porte qu'un `spatial_ref: str`, qui **pointe** vers un objet
spatial.

> **Arbitrage M2 — un besoin, pas une abstraction.** Il ne faut pas un « contrat 3D » : il faut que
> **l'observation marine puisse dire où elle est dans le volume**. Deux formes sont possibles, et le
> choix appartient au propriétaire du contrat :
>
> 1. **une coordonnée verticale sur l'observation** — un objet `Vertical(value, unit, kind)` avec
>    `kind ∈ {pression, profondeur, niveau}` et son unité propre. Elle est **attachée à la mesure**,
>    ce qui est le seul endroit où elle est correcte : la pression d'un niveau ne vaut pas pour le
>    niveau voisin ;
> 2. **un troisième axe dans `Point`** — `(x, y, z)`. C'est plus élégant, mais `Point` est partagé
>    avec le périmètre EO, et un axe surnuméraire change le sens de toutes les constructions
>    existantes (boîtes, empreintes, grilles).
>
> **Le besoin minimal, établi par les fichiers** : l'observation doit pouvoir porter une **valeur
> verticale avec son unité et sa nature** (pression en dbar ≠ profondeur en m ≠ indice de niveau),
> **et** le calcul doit savoir qu'une profondeur en mètres n'est **pas** dérivable d'une pression
> sans la masse volumique de l'eau de mer. **Signalé, non appliqué.**

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
>    en double, dérivable, donc fragile.
>
> **Point de vigilance — le partage d'instant.** Plusieurs observations partagent le même
> `TemporalStamp` et le même `spatial_ref`. C'est exact, mais **rien ne le dit** : un compteur qui
> compterait les observations par instant verrait « 390 observations à cet instant » et ne
> distinguerait pas un profil d'une anomalie. **Signalé, non appliqué.**

### M5 — la lecture netCDF

**[FAIT] Ce que les fichiers montrent.** Il y a **deux** formats, et ils ne se lisent pas de la même
façon :

| Source | Format livré | Lecteur | Dépendance |
|---|---|---|---|
| Argo (GDAC Ifremer) | **netCDF-3 classique** (`CDF\x01`) | `scipy.io.netcdf_file` | **scipy — déjà déclarée** |
| ORAS5 (CDS) | **NetCDF4 / HDF5** | `h5py` ou `netCDF4` | **absente — à ajouter** |
| GLORYS12 (CMEMS) | **NetCDF4 / HDF5** | `h5py` ou `netCDF4` | **absente — à ajouter** |
| ORAS5 (CDS, voie ponctuelle) | **CSV** disponible | bibliothèque standard | **aucune** |

**[FAIT]** Aucune des deux réanalyses ne peut être lue par la dépendance déjà présente ; aucune des
deux ne peut l'être sans elle. `numpy` et `scipy` sont les seules dépendances de runtime déclarées,
avec un motif explicite dans `pyproject.toml` : *« une bibliothèque s'installe quand un module du
dépôt l'importe réellement »*.

> **Arbitrage M5 — une dépendance, optionnelle, et une règle de format.**
>
> 1. **Une** dépendance de plus, `h5py` (ou `netCDF4`), **optionnelle** — un extra, comme `explorer`.
>    Elle est **justifiée** maintenant : les deux réanalyses sont netCDF4, et l'échantillon ORAS5 a été
>    réellement extrait par `h5py`. Mais `pyproject.toml` est un fichier partagé et n'a pas été
>    touché : c'est une décision d'intégration.
> 2. **Une règle de format, pas de bibliothèque** : quand une source offre **plusieurs** formats,
>    **préférer celui qui n'ajoute pas de dépendance**. ORAS5 sert le CSV ; le CSV se lit avec la
>    bibliothèque standard. C'est une règle de source, pas une préférence de goût.
> 3. **Ce que M5 n'est pas** : M5 n'est pas « installer un lecteur netCDF ». C'est « **deux familles
>    de fichiers, deux lecteurs** », dont un déjà présent.
>
> **Signalé, non appliqué.**

### M3 — la convention d'absence, confirmée trois fois

**[FAIT]** Trois sources, trois conventions, et **aucune** qui se déduise d'une autre :

| Source | Convention d'absence | Particularité |
|---|---|---|
| NDBC | sentinelle **par colonne** (`99`, `999`, `999.00`) | **non documentée** par le producteur |
| Argo | `_FillValue` **par variable** (99999.0 pour les numériques, `" "` pour les codes caractère) | le vocabulaire de qualité est **externe** (table 2) |
| ORAS5 | `9,96921e+36` | marque les niveaux **sous le fond marin** |
| GLORYS12 | **−32767** en entier compressé | l'échelle en fait une **mesure plausible** si l'ordre est faux |

> **Arbitrage M3 — inchangé, et durci.** Le socle n'a pas de place pour déclarer une convention
> d'absence : elle est **propre à la source**, et doit être **documentée** par l'adaptateur qui
> connaît la source. Un adaptateur qui ne connaît pas la table des sentinelles ne doit pas
> interpréter : il doit refuser le fichier, ou le signaler. Et il doit connaître **l'ordre** des
> opérations — écarter l'absence **avant** de décompresser. **Signalé, non appliqué.**

---

## 5. Les besoins exacts, fichier par fichier

| # | Besoin | Où il se pose | Forme exacte | État |
|---|---|---|---|---|
| **M2** | Une **coordonnée verticale** portée par l'observation | `src/torne/contracts/observation.py` (et, si on l'y préfère, `spatial.py`) | un objet `Vertical(value, unit, kind)` avec `kind ∈ {pression, profondeur, niveau}` et son unité propre ; `Observation` le porte, ou `Point` gagne un troisième axe | **signalée, non appliquée** — contrat partagé |
| **M4** | Une **identité de profil** portée par l'observation | `src/torne/contracts/observation.py` | un `profile_id` explicite ; **pas** une convention sur la chaîne libre `key` | **signalée, non appliquée** — contrat partagé |
| **M5** | Un **lecteur netCDF4** | `pyproject.toml` (extra optionnel) | `h5py` (ou `netCDF4`), **optionnel**, dans un extra ; et une règle de source : **préférer le CSV** quand la source en propose un. **Chiffré** : les deux réanalyses sont netCDF4, Argo est netCDF-3 | **signalée, non appliquée** — `pyproject.toml` est partagé |
| **M3** | La **convention d'absence par variable** | `src/torne/acquisition/contracts.py` ou le décodeur de l'adaptateur | une déclaration par variable (valeur de remplissage, table des codes de qualité), apprise de la source, documentée, et **l'ordre des opérations** | **signalée, non appliquée** — contrat partagé |
| **M6** | Une **clé CMEMS** distincte | `.env` (ignoré par git) | `COPERNICUS_MARINE_USERNAME` / `COPERNICUS_MARINE_PASSWORD` | **résolue** — ne pas versionner |
| **M7** | L'**acceptation de la licence CC-BY** | compte CDS du propriétaire | un clic sur la page « manage-licences » du jeu `reanalysis-oras5` | **résolue** |

> **Rien de tout cela n'a été appliqué.** Les quatre premières lignes touchent des **contrats
> partagés**, dont deux sont des fichiers que d'autres périmètres sont en train d'écrire. La mission
> demande de **documenter avant de modifier** : c'est fait, et l'arbitrage appartient au propriétaire
> de l'intégration.

---

## 6. Ce qui a changé depuis la version 1 de ce dossier

| Point | Version 1 (41829a6) | Version 2 (présent) |
|---|---|---|
| ORAS5 | licence non acceptée, échantillon 3D **non extrait** | licence acceptée, commande exécutée, **1,84 Go** téléchargés, **échantillon extrait** (359 mailles, 8 niveaux, 4 grandeurs) |
| GLORYS12 | **bloqué**, aucun identifiant | **vérifié** : sous-ensemble quotidien obtenu, **2 049 966 octets**, conformité de la fenêtre contrôlée |
| M5 | « une dépendance optionnelle, à chiffrer » | **chiffré** : ORAS5 et GLORYS12 sont netCDF4, Argo est netCDF-3 — une dépendance, pas deux |
| M3 | confirmé par deux sources | confirmé par **quatre** sources, et le cas GLORYS12 ajoute un piège d'**ordre des opérations** |
| La zone | « se découpe après téléchargement » | **mesuré** : 1,84 Go pour ORAS5 contre 2,05 Mo pour GLORYS12, sur la même zone |
| Le tampon temporel | non examiné | ORAS5 estampille le mois **au milieu** ; GLORYS12 porte un `field_date` **faux** |
| La géométrie de grille | non examinée | **deux** géométries : curviline (ORAS5) et régulière (GLORYS12) |

---

## 7. Ce qui n'a pas pu être vérifié

- **[NON VÉRIFIÉ]** le **même mois** pour ORAS5 et GLORYS12 : ORAS5 ne publie que les mois **01 à 09**
  pour 2026, et le profil Argo est du **1ᵉʳ novembre**. Il n'existe donc **aucun** instant où les
  trois sources coïncident : la comparaison du §3.4 est une **cohérence**, pas une validation.
- **[NON VÉRIFIÉ]** le **profil GLORYS12** sous 902 m : la demande a été écrêtée par le client. Le
  message d'avertissement est explicite, mais il n'a pas été vérifié que l'écrêtage a porté sur les
  seuls niveaux hors demande.
- **[NON VÉRIFIÉ]** la **conversion pression → profondeur** : elle dépend de la masse volumique de
  l'eau de mer, donc de la température, de la salinité et de la pression. Aucun calcul n'a été fait
  ici, et c'est hors mission.
- **[NON VÉRIFIÉ]** le **tableau des flags de profil** (table 2a) sur d'autres profils : seul le
  profil ouvert a été qualifié.
- **[NON VÉRIFIÉ]** la **voie ponctuelle** d'ORAS5 (`reanalysis-oras5-timeseries`) : son schéma et
  sa contrainte de zone sont connus, mais la requête n'a pas été exécutée.
- **[NON VÉRIFIÉ]** la route ouverte **ICDC** (Hambourg) pour ORAS5 : `www.icdc.mpi-met.mpg.de` **ne
  résout pas en DNS** depuis ce poste.

---

## 8. La suite proposée

1. **Décider M2 et M4** — la forme exacte du besoin est §4 et §5 ; l'arbitrage est au propriétaire de
   l'intégration, pas à cette mission.
2. **Décider M5** — installer `h5py` en extra optionnel, ou adopter la règle « le CSV d'abord ».
   Le besoin est chiffré, la démonstration est faite.
3. **Choisir la source de réanalyse** — c'est désormais une décision argumentable : ORAS5 donne
   **75 niveaux** et 1958→présent, GLORYS12 donne **1/12°** et du **quotidien** pour 2 Mo. La
   question du panache de MARINE-001 se pose au pas de temps des épisodes : **le quotidien** est
   nécessaire, et c'est GLORYS12 qui l'a.
4. **Poser la question** quand les quatre entrées seront disponibles — et pas avant.

---

## 9. Les produits

| Fichier | Rôle |
|---|---|
| `experiments/marine_002_profil_argo.py` | ouvrir un profil Argo réel et le qualifier : verticale, unités, absence, qualité, structure |
| `experiments/marine_002_oras5.py` | ORAS5 : reconnaissance, coût, exécution, mise en attente, téléchargement, archive |
| `experiments/marine_002_echantillon_oras5.py` | découper l'échantillon 3D sur la zone et écrire l'échantillon netCDF |
| `experiments/marine_002_glorys12.py` | GLORYS12 : sous-ensemble quotidien, contrôle de la fenêtre, de l'échelle et du remplissage |
| `data/marine-002/**` | les preuves brutes et les échantillons extraits (dossier ignoré par git) |

**État.** `ruff check` et `ruff format` propres sur les quatre scripts. **Aucun contrat partagé n'a été
modifié** : les besoins sont chiffrés en §4 et §5, et soumis à arbitrage.
