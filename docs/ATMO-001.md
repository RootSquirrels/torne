# ATMO-001 — Le périmètre atmosphère et météorologie

> **Exploration contrôlée.** Ce dossier ne publie **aucun produit de connaissance** et ne tire
> **aucune conclusion** sur le climat français. Il fait trois choses : il **inventorie** ce qui est
> réellement accessible, il **mesure** ce que les sources contiennent, et il en **dégage une question
> testable** — avec le protocole qui permettra d'y répondre, et la liste des adaptations que ce
> périmètre exige du socle.
>
> Toutes les mesures ci-dessous ont été faites **par exécution**, le **1ᵉʳ novembre 2026**, sur des
> données réelles. Rien n'est reprise de mémoire.

**Règle de preuve.** Chaque affirmation est classée **[FAIT]** (observé sur une requête ou sur les
octets reçus), **[INFÉRENCE]** (lecture plausible d'un fait observé) ou **[NON VÉRIFIÉ]** (non vérifié,
avec la marche à suivre).

**Reproduction.**

```bash
uv run python experiments/atmo_001_sources_probe.py          # l'inventaire d'accessibilité
uv run python experiments/atmo_001_premiere_acquisition.py    # l'acquisition et le profil
uv run pytest tests/test_atmosphere.py                        # les règles, sans réseau
```

---

## 0. Ce que la mission a Change

Trois choses que la mission ne pouvait pas savoir avant d'être exécutée, et qui décide de la suite :

1. **La source institutionnelle française est fermée à la clé.** Les trois voies Météo-France
   documentées répondent `401`. Aucune donnée d'observation française n'est donc accessible par la
   voie officielle depuis ce poste — sauf si un compte est fourni.
2. **Une source d'observation réelle, complète et documentée est accessible sans compte** : GHCN-Daily
   (NOAA/NCEI). 109 stations françaises, de 1921 à 2026, avec les **drapeaux de qualité du
   producteur**. C'est elle qui a servi de base à la première acquisition.
3. **Aucune de ces observations n'est admissible en reconstitution point-in-time.** GHCN-Daily ne
   publie jamais la date de publication d'une valeur. La publication est donc **inconnue** (classe N),
   et `usable_at` vaut `None` pour chaque observation. C'est une contrainte structurelle, pas un
   réglage : elle ne se contourne pas, elle se constate et se déclare.

---

## 1. Inventaire des sources réellement accessibles

La sonde (`experiments/atmo_001_sources_probe.py`) a posé 17 questions à 17 points d'accès, le
1ᵉʳ novembre 2026, et a classé chaque réponse selon **quatre états distincts** : `accessible`,
`sur_tunnel` (le fournisseur exige un compte), `absente` (le point d'accès n'existe pas),
`injoignable` (le transport a échoué) — plus `contenu_inattendu`, qui n'existait pas avant cette
mission et qui vaut d'être expliqué.

| État | Nombre | Sources |
|---|---|---|
| `accessible` | 6 | data.gouv.fr (catalogue), catalogue CDS (STAC), Open-Meteo archive (ERA5), GHCN-Daily (fichier de station, readme, index) |
| `sur_tunnel` | 3 | Météo-France observation ×2, Météo-France climatologie |
| `absente` | 3 | API timeseries CDS, objet ARCO-ERA5, Open-Meteo previous-runs |
| `injoignable` | 2 | `donnees.meteofrance.fr` (DNS), DWD (chaîne TLS) |
| `contenu_inattendu` | 2 | NOAA ISD, OGIMET |
| `erreur_http_405` | 1 | exécution CDS (POST uniquement) |

### 1.1 Météo-France — derrière un compte, partout

**[FAIT]** Les trois voies documentées répondent `401`, et **le corps de la réponse dit pourquoi** :

| Voie | Statut | Corps |
|---|---|---|
| `public-api.meteofrance.fr/public/DPPaquetObs/liste-stations` | 401 | `{"code":"900902","message":"Missing Credentials",…}` |
| `public-api.meteofrance.fr/public/DPPaquetObs/paquet/stations/infrahoraire-6m` | 401 | idem |
| `webservice.meteofrance.com/climatologie` | 401 | `you must provide a token` |

> **[FAIT]** Le chemin `DPPaquetV1/observation/France/{ville}/{début}/{fin}`, longtemps cité, répond
> désormais `404` : la base du chemin est passée à `DPPaquetObs`. **[NON VÉRIFIÉ]** — la forme exacte
> des routes actuelles n'a pas été vérifiée au-delà de celles documentées, faute de jeton.

**[FAIT]** `www.donnees.meteofrance.fr` **ne résout pas** depuis ce poste (`getaddrinfo failed`, pour
`www.` comme pour le domaine nu). **[NON VÉRIFIÉ]** — impossible de dire depuis ce poste si le portail
existe encore ailleurs ou s'il a changé d'adresse : le DNS ne répond pas.

### 1.2 Ce que Météo-France publie quand même, en ouvert

**[FAIT]** Le catalogue national `data.gouv.fr` reste accessible sans compte, et il contient des jeux
Météo-France. Deux d'entre eux sont importants pour la suite :

- « **Documents d'archives du climat numérisés : relevés d'observations météorologiques quotidiennes** »
  (Météo-France, 551 ressources) ;
- « **Documents d'archives du climat numérisés : tableaux climatologiques mensuels** » (45 ressources).

> ⚠ **[FAIT]** Ces deux jeux sont des **images numérisées** (`.jpg`, `.pdf`) et un **inventaire
> d'archives** (`.xml`) : **pas de données structurées**. Les faire passer par un OCR serait produire
> des chiffres qu'aucune source n'a publiés. **La voie ouverte de Météo-France ne donne donc pas de
> données exploitables telles quelles.** C'est un constat, pas une conclusion.

### 1.3 Réanalyse — trois voies, une seule vraiment ouverte

**[FAIT]** `cds.climate.copernicus.eu/api/retrieve/.../execution` répond **405 Method Not Allowed** en
GET : le point d'accès n'est pas une page, c'est une route POST, qui demande un compte. **[FAIT]**
`/api/timeseries/v1/collections/reanalysis-era5-single-levels` répond **404** (« Climate Data Store API
endpoint not found »). **[FAIT]** En revanche le **catalogue CDS** (STAC) est **ouvert** : 575 ko de
métadonnées de collections, dont ERA5, obtenues sans compte. C'est un inventaire de *ce qui existe*,
pas un accès aux *données*.

**[FAIT]** L'archive ERA5 **re-servie par Open-Meteo** répond sans clé ni compte, en JSON, et rend les
maxima et minima quotidiens. Elle rend aussi les coordonnées **de la cellule de grille** (50,65026 /
3,0319147 pour une demande faite à Lille) et l'altitude de cette cellule : la réanalyse est donc
explicitement ce qu'elle est — un **estimé de grille**, pas une mesure au point de la station.

### 1.4 Le piège que cette mission a failli encourager

**[FAIT]** `www.ncei.noaa.gov/data/global-hourly/access/2026/07014099999.csv` répond **HTTP 200** avec un
**document HTML d'erreur Amazon S3** (« All Rights Reserved… S3 »), de 36 822 octets. Un contrôle qui ne
regarde que le code HTTP lit cette page comme un jeu d'observations.

**[FAIT]** OGIMET fait la même chose autrement : HTTP 200, corps `Status: 403 Forbidden`.

> C'est pour cela que la sonde vérifie désormais **la forme du contenu** et pas seulement le statut.
> Les deux sources sont classées `contenu_inattendu` — un état qui n'existait pas avant.

### 1.5 La voie Météo-France : où poser le jeton

La source institutionnelle n'est pas hors d'atteinte : elle est **derrière un jeton OAuth2**. Le code
qui l'attend est en place (`src/torne/acquisition/adapters/meteofrance.py`,
`src/torne/acquisition/credentials.py`, `experiments/atmo_001_meteofrance.py`), et il respecte la
règle du dépôt : **INV-41 — un secret ne circule que par référence**.

**[FAIT]** Ce que le journal d'acquisition retient d'une demande à Météo-France, sans jeton (course
réelle du 1ᵉʳ novembre 2026) :

```json
{"credential_ref": "meteofrance.oauth2", "error_kind": "authentication",
 "error_detail": "HTTP 401", "status": "failed", "pages": [], "content_sha256": []}
```

La **référence** est consignée ; la valeur ne l'est pas, et ne le sera jamais.

**Où poser le jeton — deux emplacements, et aucun autre.**

| | Emplacement | Pourquoi |
|---|---|---|
| ✅ | variable d'environnement `METEOFRANCE_TOKEN` (PowerShell : `setx METEOFRANCE_TOKEN "…"` ) | rien n'entre dans le dépôt, même en fichier local |
| ✅ | fichier `.env` **à la racine du dépôt** | déjà ignoré par Git : `.gitignore:36` couvre `.env` et `.env.*` **[FAIT]** (`git check-ignore -v`) |
| ❌ | **dans cette conversation** | un message est conservé, et un secret collé dans un message est un secret copié |
| ❌ | **dans un fichier versionné** | le secret part dans l'historique, et l'historique se clone |

Dans les deux cas, la **variable d'environnement prime** sur le fichier `.env` : un choix explicite
prime sur un commodité local. Le jeton n'est écrit nulle part, et il n'est jamais journalisé.

> **[NON VÉRIFIÉ]** la durée de vie du jeton et l'existence d'un jeton de rafraîchissement n'ont pas pu
> être vérifiées — le compte n'est pas ouvert. Si le jeton est court, l'éclairement non interactif
> demandera un second secret (`METEOFRANCE_REFRESH_TOKEN`), qui devra être stocké de la même façon.

**[FAIT]** Le chemin Météo-France est **vérifié de bout en bout jusqu'au refus** : sans jeton, les deux
appels partent, la source répond `401`, le socle classe l'échec en `authentication`, et rien n'est
interprété. C'est le comportement attendu, et il est le même que celui d'une panne : l'échec est un
résultat, consigné.

> ⚠ **[FAIT] Une constatation sur le socle, à arbitrer.** Le corps du refus — 234 octets où Météo-France
> écrit *« Make sure your API invocation call has a header: 'Authorization : Bearer ACCESS_TOKEN' »* —
> **n'est pas conservé** : `pages: []`, `content_sha256: []`. Le socle garde le statut et le type de
> contenu, pas la parole de la source. C'est cohérent avec « un 4xx est un échec d'acquisition », mais
> une source qui explique son refus voit son explication perdue de la piste d'audit (voir A9).

---

## 2. La source retenue, et ce qu'elle contient

### 2.1 GHCN-Daily — ce que la source est

| | |
|---|---|
| Producteur | NOAA National Centers for Environmental Information (NCEI) |
| Jeu | GHCN-Daily, **version 3.35-upd-2026103017** **[FAIT]** (`ghcnd-version.txt`, lisible sans compte) |
| Point d'accès | `…/global-historical-climatology-network-daily/access/{station}.csv` |
| Accès | **aucun compte, aucun secret** **[FAIT]** |
| Unité | **aucune, au niveau de la source** : la source publie des températures en dixièmes de degré, des précipitations en dixièmes de millimètre et des pressions en dixièmes de hectopascal **[FAIT]** |
| Fuseau | **aucun publié** : la source publie des dates civiles **[FAIT]** |
| Publication | **aucune, par valeur** **[FAIT]** |
| Documentation | `readme.txt` v3.35 : unités, et le vocabulaire complet des drapeaux **[FAIT]** |

**[FAIT] 109 stations françaises.** Relevé de `ghcnd-stations.txt` : Lille-Lesquin (50,5700 /
3,0975 / 47 m), Paris-Montsouris (48,8217 / 2,3378 / 75 m), Toulouse-Blagnac (43,6208 / 1,3789 /
151 m), Marseille-Marignane (43,4378 / 5,2158 / 9 m), Nantes-Bouguenais, Strasbourg-Entzheim,
Bordeaux-Mérignac, Rennes-Saint-Jacques, Nice, Lyon-Saint-Exupéry…

> **[FAIT]** La source ne publie **aucun datum** pour les coordonnées : il est déclaré absent, pas
> supposé WGS 84.

### 2.2 La provenance, qui n'est pas celle du producteur

**[FAIT]** Le drapeau de source de NCEI dit d'où vient chaque valeur. Sur les quatre stations lues :

| Station | Drapeaux de source | Signification |
|---|---|---|
| Lille-Lesquin | `E` sur 29 889 jours | ECA&D — European Climate Assessment & Dataset |
| Toulouse-Blagnac | `E` sur 29 128 jours | idem |
| Marseille-Marignane | `E` sur 37 829 jours | idem |
| Paris-Montsouris | `S` sur 9 569 jours, `2` sur 195 | GSOD (Global Summary of the Day), puis source `2` |

> ⚠ **[FAIT]** **Pour la France, GHCN-Daily est un redistributeur, et sa source amont est ECA&D** —
> pas Météo-France. **[NON VÉRIFIÉ]** le lien ECA&D → Météo-France n'est établi par aucune des
> métadonnées lues : la chaîne de provenance **s'arrête à ECA&D**. Une affirmation de provenance
> « Météo-France » fondée sur GHCN-Daily serait donc **infondée** pour la France.

### 2.3 La qualité déclarée par le producteur

**[FAIT]** NCEI publie trois drapeaux par mesure : *measurement*, *quality*, *source*. Le vocabulaire
*quality* compte 14 valeurs, dont « failed spatial consistency check », « failed climatological
outlier check », « failed internal consistency check ». Ce qui a été **effectivement observé** :

| Station | Drapeaux de qualité relevés | Valeurs rejetées | Mesures à partir de la source | Drapeaux de mesure relevés |
|---|---|---|---|---|
| Lille-Lesquin | `I` : 261 | 261 / 29 889 (0,9 %) | — | — |
| Toulouse-Blagnac | `I` : 192 | 192 / 29 128 (0,7 %) | — | — |
| Marseille-Marignane | `I` : 117, `O` : 1 | 118 / 37 829 (0,3 %) | — | — |
| Paris-Montsouris | `I` : 2 | 2 / 9 764 | `H` : 195 | `B` : 148, `D` : 989, `H` : 118 (précipitations) |

**[FAIT]** Le drapeau `H` sur TMAX/TMIN signifie « highest or lowest **hourly** temperature » : la valeur
n'est pas un maximum journalier, mais la plus haute (ou la plus basse) **horaire** de la journée. À
Paris-Montsouris, cela concerne 195 journées. **[FAIT]** Les drapeaux de précipitation `B` (somme de
deux totaux sur 12 h), `D` (somme de quatre totaux sur 6 h) et `H` (zéro rapporté) montrent que
**l'agrégation des précipitations n'est pas homogène** sur la série.

> **Ce que cela interdit.** Une série de précipitations ainsi construite n'est pas une série
> homogène : la comparer à une référence calculée sur des critères différents est un nonsens.
> **[FAIT]** la mesure est conservée, le drapeau aussi ; il est à l'analyse de les traiter.

### 2.4 La couverture, et ce qu'elle cache

**[FAIT]** Quatre stations, mesurées sur le fichier réel :

| Station | Période | Jours observés | Couverture | Lacunes | Plus longue lacune |
|---|---|---|---|---|---|
| Lille-Lesquin | 1944-12-01 → 2026-09-30 | 29 889 | 100,0 % | 0 | — |
| Toulouse-Blagnac | 1947-01-01 → 2026-09-30 | 29 128 | 100,0 % | 0 | — |
| Marseille-Marignane | 1921-01-01 → 2026-09-30 | 37 829 | 97,9 % | 2 | **793 j** (1943-07-01 → 1945-08-31) |
| Paris-Montsouris | 1983-12-18 → 2026-10-25 | 9 764 | **62,4 %** | 744 | **2 638 j** (1992-01-01 → 1999-03-22) |

> **[FAIT]** La lacune de Marseille tombe exactement sur la Seconde Guerre mondiale. **[INFÉRENCE]**
> l'occupation du territoire et la fermeture des réseaux explains ces 793 jours ; la lacune n'en est pas
> moins un **trou de données**, et c'est ainsi qu'elle est traitée.
>
> **[FAIT]** La lacune de Paris-Montsouris dure sept ans : une station ne publie pas pendant sept ans
> sans raison. **[NON VÉRIFIÉ]** la raison exacte (déplacement, fermeture, changement de série) n'est
> dans aucune des métadonnées lues.

---

## 3. Représentation dans les contrats canoniques

Ce qui a été vérifié, et comment.

| Élément | Décision | Fondement |
|---|---|---|
| **Unité** | portée par le couple (élément, mesure), **pas** par la source : `TMAX` → `degC` (diviseur 10), `PRCP` → `mm` (diviseur 10), `SNWD` → `mm`, `ASLP` → `hPa` (diviseur 10) | `readme.txt` v3.35 **[FAIT]** ; `Source.unit` reste `None`, comme le fait déjà le module hydrologique pour le bassin versant |
| **Espace** | `spatial_ref` = l'identifiant de station ; latitude, longitude, altitude portées par la `Station`, **datum déclaré absent** | la source répète les coordonnées sur chaque ligne **[FAIT]** |
| **Temps** | date civile → **début du jour civil local**, la zone étant un **argument** | la source ne publie aucun fuseau **[FAIT]** |
| **Publication** | `PublicationState.UNKNOWN`, `known_at = None` → `usable_at is None` | la source ne dit jamais quand une valeur est devenue publique **[FAIT]** |
| **Absence** | cellule vide → `PointValidity.MISSING` + `MissingReason.NOT_MEASURED`, **jamais** un zéro | le jour non mesuré n'est pas un jour à zéro |
| **Qualité** | sans drapeau → `DECLARED` ; avec drapeau de qualité → `UNKNOWN`, **la valeur et le drapeau étant conservés** | le vocabulaire canonique ne dit pas « mesurée et refusée » (voir §7, A1) |
| **Conformité** | `station` et `elements` vérifiés **sur le corps reçu** | une page HTML servie en 200 ne rend aucun critère vérifiable → abstention, jamais accord |

### 3.1 Le jour civil n'est pas le jour UTC

**[FAIT]** En mars 1945, la France était à UTC+0 : le 2 mars 1945 à 00:00 à Paris est le **1ᵉʳ mars
1945 à 23:00 UTC**. Une climatologie indexée sur le jour **UTC** compare donc chaque journée à
l'habitude du jour **précédent** — un décalage d'un jour, invisible à la lecture, qui fausse le signe
des anomalies en bordure de chaque année.

> C'est un défaut trouvé **par les tests** de ce périmètre, et corrigé ici : le module
> `torne.atmosphere` indexe et filtre **en jours civils**, la zone étant un argument.
> **[FAIT]** Le module `torne.hydrology` **déclare** dans sa documentation que « the climatology is
> keyed on the **local civil day** », mais son code indexe sur `instant.month, instant.day`, c'est-à-dire
> le jour **UTC**. Les deux ne coïncident que pour les zones à l'ouest de Greenwich — c'est le cas du
> Mississippi (UTC−6, où minuit local tombe le même jour UTC), ce qui explique que l'écart soit resté
> invisible jusqu'ici. **Je n'ai pas modifié le module partagé** : c'est une adaptation à arbitrer (A3).

---

## 4. Profil exploratoire des variables et des régimes

### 4.1 Le profil des variables

**[FAIT]** Températures maximales, sur la période de record :

| Station | min | max | médiane | moyenne | moyennes mensuelles (jan → déc) |
|---|---|---|---|---|---|
| Lille-Lesquin | −11,3 °C | 41,5 °C | 14,4 °C | 14,49 °C | 5,7 · 7,0 · 10,5 · 14,1 · 17,9 · 20,9 · 23,0 · 23,0 · 19,9 · 15,2 · 9,6 · 6,6 |
| Paris-Montsouris | −6,9 °C | 42,6 °C | 17,3 °C | 17,26 °C | 7,7 · 9,3 · 12,9 · 17,2 · 20,6 · 24,1 · 26,7 · 25,9 · 22,4 · 17,5 · 11,6 · 8,5 |
| Toulouse-Blagnac | −9,6 °C | 42,4 °C | 18,2 °C | 18,40 °C | 9,2 · 11,1 · 14,4 · 17,0 · 20,8 · 25,0 · 27,8 · 27,7 · 24,5 · 19,5 · 13,2 · 10,0 |
| Marseille-Marignane | −9,2 °C | 40,5 °C | 19,6 °C | 19,92 °C | 11,0 · 12,4 · 15,4 · 18,4 · 22,5 · 26,8 · 29,8 · 29,3 · 25,6 · 20,8 · 15,2 · 11,6 |

**[FAIT]** Précipitations : Lille 0 → 62,8 mm/j, Paris 0 → 78,2, Toulouse 0 → 82,7, Marseille 0 → 212,3 ;
médiane nulle partout (plus de la moitié des jours sans pluie utile).

### 4.2 La structure temporelle — le résultat qui change la puissance des tests

**[FAIT]** Sur les anomalies de température moyenne quotidienne, rapportées à la climatologie
1991-2020 :

| Station | Autocorrélation (retards 1, 2, 3) | Taille effective | Ratio | Troncature |
|---|---|---|---|---|
| Lille-Lesquin | 0,783 · 0,584 · 0,454 | **2 028** | **6,8 %** | 45 |
| Paris-Montsouris | 0,709 · 0,484 · 0,348 | **914** | **11,3 %** | 39 |
| Toulouse-Blagnac | 0,773 · 0,569 · 0,437 | **2 017** | **6,9 %** | 45 |
| Marseille-Marignane | 0,770 · 0,601 · 0,488 | **2 023** | **5,3 %** | 45 |

> **La lecture qui compte.** Une série de 29 889 jours quotidiens ne contient que **≈ 2 000 jours
> indépendants**. Un test qui treat 29 889 observations comme indépendantes surestime sa puissance
> d'un facteur **14**. Tout calcul ultérieur doit être dimensionné par la **taille effective**, pas
> par le nombre de jours.

### 4.3 Les régimes

**[FAIT]** Sur la même base, avec des seuils déclarés (|anomalie| ≥ 1 = chaud/froid, ≥ 2 = extrême,
épisode = ≥ 3 jours **consécutifs**, la consécutivité étant vérifiée sur les jours civils) :

| Station | Jours notés | Épisodes froids | Épisodes chauds | Durée max (froid / chaud) |
|---|---|---|---|---|
| Lille-Lesquin | 29 889 | 720 | 343 | 12 j / 12 j |
| Paris-Montsouris | 8 057 | 135 | 106 | 8 j / 7 j |
| Toulouse-Blagnac | 29 128 | 673 | 375 | 12 j / 14 j |
| Marseille-Marignane | 37 829 | 918 | 380 | 16 j / 14 j |

> **[FAIT]** Les épisodes **froids** sont plus nombreux que les épisodes chauds — parce que la
> référence est 1991-2020 et que les séries commencent en 1944-1947. Ce déséquilibre est un fait de la
> référence choisie, pas une propriété du climat : il se renverserait avec une référence plus
> ancienne. C'est exactement le genre de résultat qui ne veut rien dire tout seul.

### 4.4 Une rupture de moyenne, visible partout

**[FAIT]** Test de rupture OLS-CUSUM (variance de long terme de Bartlett) sur les anomalies :

| Station | p | moyenne avant → après |
|---|---|---|
| Lille-Lesquin | 1,2 × 10⁻⁵⁷ | −0,445 → +0,059 |
| Paris-Montsouris | 5,1 × 10⁻¹⁰ | −0,146 → +0,191 |
| Toulouse-Blagnac | 1,4 × 10⁻⁵⁸ | −0,444 → +0,062 |
| Marseille-Marignane | 5,5 × 10⁻⁸⁸ | −0,591 → +0,053 |

> **[FAIT]** Les quatre stations présentent une **rupture de moyenne** très significative, de même sens
> et de même ordre de grandeur (~0,5 écart-type). **[INFÉRENCE]** l'explication la plus économique est
> le réchauffement observé sur la période, la référence 1991-2020 se situant au milieu de la série.
> **[NON VÉRIFIÉ]** — la date de la rupture n'est pas estimée ici, et l'attribution à un forçage
> plutôt qu'à un artefact de la série (déplacement de station, changement d'instrument) **exige** le
> contrôle de l'homogénéité de la série, qui n'a pas été fait. Une station dont l'instrument a
> changé en 1990 et une série décalée de 0,5 σ produisent la même statistique.

---

## 5. La question testable

> **Les anomalies thermiques quotidiennes sont-elles persistantes au-delà du seul effet de l'inertie
> quotidienne, et cette persistance diffère-t-elle entre les régimes froids et les régimes chauds ?**

La question est **dimensionnée par la taille effective** (§4.2), pas par le nombre de jours : à
≈ 2 000 jours indépendants par station, et ≈ 8 000 sur quatre stations, on peut détecter une
différence d'autocorrélation entre régimes de l'ordre de quelques centièmes — et **pas** une
différence de 0,01.

**Pourquoi cette question et pas une autre.** Elle est apparue **du** profil, pas avant lui :

- la persistance est **forte** et mesurée (0,78 au retard 1) ;
- elle est **structurante** : elle détermine la taille effective, donc la puissance de tout test ;
- elle est **mesurable sur des données déjà acquises**, sans source nouvelle ;
- elle est **falsifiable** : un écart nul entre régimes froids et chauds est un résultat, pas un
  échec.

**Ce qu'il ne faut pas en faire.** Ce n'est pas une question sur le climat français : c'est une
question sur la **structure temporelle d'une série d'anomalies**, et les quatre stations n'en sont
qu'un terrain d'essai.

---

## 6. Références indépendantes et protocole d'évaluation

### 6.1 Les contrôles faits

| Contrôle | Nature | Résultat **[FAIT]** |
|---|---|---|
| **Cohérence spatiale** | les anomalies de stations françaises doivent se ressembler sans être identiques | corr(Lille, Paris) **0,877** · corr(Toulouse, Marseille) **0,748** · corr(Lille, Toulouse) **0,604** · les quatre autres entre 0,542 et 0,682 |
| **Écart à la réanalyse** | ERA5 (re-servie par Open-Meteo), 2015-2025 | Lille : biais **+0,78 °C**, corrélation **0,919** · Marseille : biais **+1,49 °C**, corrélation **0,943** |

> **Ce que ces contrôles ne disent pas.** ERA5 est une **estimation** produite par un modèle, pas une
> observation : la comparer à une station mesure **un écart entre deux productions**, et ne valide
> ni l'une ni l'autre. Le biais mesuré (+0,8 à +1,5 °C) est cohérent avec ce qu'on attend d'une
> cellule de grille plus lissée et plus basse que la station — **[INFÉRENCE]**, non vérifiée contre
> la topographie locale. La réanalyse **n'est pas** une vérité terrain : c'est un contrôle de
> cohérence.

### 6.2 Le protocole d'évaluation proposé

1. **Référentiel indépendant.** La référence de normales de Météo-France (1991-2020), lue via son API
   climatologique — **dès qu'un jeton est fourni**. En attendant, la comparaison sera faite contre
   la **climatologie calculée par TORNE** et contre **ERA5**, en tenant compte de la clause 6.1.
2. **Homogénéité avant attribution.** Contrôler la continuité de la série autour de la rupture
   détectée (changement d'instrument, déplacement de station) : **sans ce contrôle, l'interprétation
   climatique de la rupture n'est pas recevable.**
3. **Dimensionnement.** Tous les tests par station seront dimensionnés par la **taille effective**
   (§4.2), avec le nombre de degrés de liberté effectif dans l'intervalle.
4. **Contrôle de multiplicité.** Quatre stations × plusieurs régimes : la correction (Holm) est
   obligatoire et sera déclarée.
5. **Réplication.** La question sera posée **d'abord** sur les séries d'anomalies **sans** référence
   1991-2020 (une référence mobile, p. ex. centering par fenêtre de 30 ans), pour vérifier que le
   résultat ne vient pas du choix de la référence.

### 6.3 Ce qui manque pour une validation pleine

- **[NON VÉRIFIÉ]** l'accès à l'API climatologique Météo-France, qui seule permettrait une comparaison
  normative officielle ;
- **[NON VÉRIFIÉ]** la chaîne de provenance ECA&D → Météo-France pour les stations françaises ;
- **[NON VÉRIFIÉ]** l'homogénéité instrumentale des séries ;
- **[NON VÉRIFIÉ]** une source **de classe P ou B** (publication datée) : sans elle, **aucune**
  reconstitution point-in-time n'est possible dans ce périmètre.

---

## 7. Les adaptations réellement nécessaires

Chacune est **exécutée dans le périmètre** quand elle est locale au domaine, et **signalée sans
être appliquée** quand elle touche le socle partagé.

| # | Adaptation | Pourquoi | État |
|---|---|---|---|
| **A1** | **Vocabulaire de qualité** : ajouter un état « mesurée, contrôle échoué » | le vocabulaire canonique est fermé à 5 états ; NCEI en publie 14 (mesure) et signale des valeurs **mesurées** dont un contrôle a échoué. Ces valeurs ne sont ni absentes, ni nulles, ni approuvées : le socle ne peut pas les dire. `UNKNOWN` + conservation du drapeau est le contournement disponible aujourd'hui | **appliquée localement** (domaine) — **à arbitrer** pour le socle |
| **A2** | **Borne supérieure de publication** | `TemporalStamp` porte `publication_lower_bound` (borne *inférieure*). GHCN-Daily donne l'inverse : la version de l'archive borne la publication **par le haut** (« au plus tard le 30/10/2026, la valeur était dans l'archive »). Le contrat ne sait pas le dire | **signalée, non appliquée** |
| **A3** | **Indexation en jour civil** dans `torne.hydrology` | le module hydrologique **déclare** un indexage sur le jour civil local, mais son code indexe sur le jour **UTC**. Les deux ne coïncident que pour une zone à l'ouest de Greenwich (le Mississippi, UTC−6) : l'écart est donc invisible tant qu'on n'a pas de station à l'est de Greenwich. Le module atmosphère indexe en jour civil | **signalée, non appliquée** (fichier partagé) |
| **A4** | **Filtre de période de référence** dans `torne.hydrology.climatologie` | `reference_start` / `reference_end` y sont acceptés mais **ne filtrent pas** : la « climatologie 1991-2020 » y est en réalité la climatologie de toute la série. Le module atmosphère filtre réellement | **signalée, non appliquée** (fichier partagé) |
| **A5** | **Adaptateur sans promesse de fenêtre** | le point d'accès GHCN rend toujours la période de record : un adaptateur qui promet une fenêtre promet une violation. Vérifié le 1ᵉʳ novembre 2026 — la demande 2015-2025 a rendu 1944-2026 et a été **refusée comme non conforme**. La fenêtre est un filtre après coup | **appliquée localement** |
| **A6** | **Dépendance `tzdata`** | `zoneinfo` n'a pas de base IANA sur Windows sans ce paquet ; le calcul en jour civil en dépend. `pyproject.toml` ne le déclare pas | **signalée, non appliquée** (fichier partagé) |
| **A7** | **Export de l'adaptateur** dans `torne.acquisition.adapters.__init__` | le module existe et fonctionne ; il n'est pas exporté, pour ne pas modifier un fichier partagé pendant que le périmètre HYDRO-01 travaille | **signalée, non appliquée** — une ligne |
| **A8** | **Fiche GHCN-Daily dans `docs/SOURCES.md`** | le dépôt qualifie ses sources dans un document unique ; la fiche GHCN y manque | **signalée, non appliquée** (fichier partagé) |
| **A9** | **Conserver le corps d'un refus** | quand une source répond `4xx`, le socle consigne le statut, le type et la durée, mais **pas le corps** — donc pas l'explication que la source donne de son refus (ici, le rappel de l'en-tête attendu). Une source qui explique son refus voit sa parole perdue de la piste d'audit | **signalée, non appliquée** (contrat transversal) |
| **A10** | **Exports des nouveaux modules** | `torne.acquisition.credentials` et l'adaptateur `meteofrance` fonctionnent mais ne sont pas exportés dans les `__init__` des paquets partagés, pour ne pas les modifier pendant que HYDRO-01 travaille | **signalée, non appliquée** — deux lignes |

> Les sept adaptations signalées sont **en attente d'arbitrage**, et **aucune** n'a été appliquée à un
> fichier partagé. C'est le respect de la règle : les deux périmètres ne modifient pas le socle en
> même temps.

---

## 8. Ce qui a été produit

| Fichier | Rôle |
|---|---|
| `src/torne/atmosphere/observations.py` | lecture d'une ligne GHCN-Daily → observation ; unités, drapeaux, temps, absence |
| `src/torne/atmosphere/anomaly.py` | climatologie, anomalies, régimes, épisodes ; tout indexé en **jour civil** |
| `src/torne/atmosphere/profile.py` | couverture, lacunes, distribution, autocorrélation, taille effective, rupture |
| `src/torne/acquisition/adapters/ghcnd.py` | l'adaptateur : l'URL, la lecture, et la **vérification de conformité sur le contenu** |
| `src/torne/acquisition/credentials.py` | les secrets : une référence, résolue au dernier moment (INV-41) |
| `src/torne/acquisition/adapters/meteofrance.py` | l'adaptateur de la voie institutionnelle, derrière jeton |
| `experiments/atmo_001_sources_probe.py` | l'inventaire d'accessibilité, rejouable |
| `experiments/atmo_001_premiere_acquisition.py` | l'acquisition réelle et le profil, rejouable |
| `experiments/atmo_001_meteofrance.py` | la voie institutionnelle, telle qu'elle répond avec ou sans jeton |
| `tests/test_atmosphere.py` | 26 tests, **sans réseau** |
| `tests/test_meteofrance.py` | 13 tests, **sans réseau** : le secret, et la place du refus |

**État de la suite.** 690 tests du dépôt passent ; `ruff check` et `ruff format` sont propres sur les
fichiers de ce périmètre.

---

## 9. Ce qui n'a pas pu être vérifié

- **[NON VÉRIFIÉ]** l'API d'observation Météo-France et l'API climatologique : elles exigent un jeton
  OAuth2. **La marche à suivre** : poser le jeton dans `METEOFRANCE_TOKEN` (variable d'environnement)
  ou dans un `.env` à la racine du dépôt — voir §1.5 — puis relancer
  `experiments/atmo_001_meteofrance.py`. Le secret n'a pas à être écrit dans le chat, et il n'a pas à
  être versionné.
- **[NON VÉRIFIÉ]** le portail `donnees.meteofrance.fr` : le DNS ne répond pas depuis ce poste. **La
  marche à suivre** : vérifier depuis un autre réseau, ou via le catalogue data.gouv.fr, si les
  fichiers d'observation publiés par Météo-France y sont référencés.
- **[NON VÉRIFIÉ]** l'API de séries temporelles du CDS, l'objet ARCO-ERA5, l'API *previous-runs* d'Open-Meteo
  : les trois points d'accès testés répondent `404`. **La marche à suivre** : documentation à jour,
  ou dédoublage des noms d'objets du bucket public.
- **[NON VÉRIFIÉ]** les observations horaires ISD (NCEI) et les messages SYNOP (OGIMET) : les points
  d'accès testés sont hors service ou refusent la requête. **La marche à suivre** : nouveaux points
  d'accès (ISD-lite, ou le format `.dly` brut de GHCN).
- **[NON VÉRIFIÉ]** DWD (opendata.dwd.de) : la chaîne TLS n'est pas vérifiable depuis ce poste
  (`CERTIFICATE_VERIFY_FAILED`). **La marche à suivre** : vérifier la chaîne sur un autre poste, ou
  confirmer que l'hôte sert une chaîne incomplète. **Aucune vérification TLS n'a été désactivée** pour
  contourner cela.
- **[NON VÉRIFIÉ]** l'homogénéité instrumentale des séries, et donc l'attribution de la rupture de
  moyenne à un forçage.

---

## 10. La suite proposée

1. **Arbitrer les deux accès** : un jeton Météo-France (pour la source institutionnelle et ses
   normales) et une voie ERA5 stabile (compte CDS, ou ARCO-ERA5 avec `zarr`).
2. **Contrôler l'homogénéité** des séries avant toute interprétation climatique de la rupture (§6.2).
3. **Poser la question** (§5) sur les anomalies mobiles, avec correction de multiplicité et
   dimensionnement par la taille effective.
4. **Écrire la pré-registration** de cette question : hypothèse, jeux de données, puissance attendue,
   critères de décision — avant de regarder le résultat.
5. **Ne pas** publier de produit de connaissance avant que ces quatre points soient faits.
