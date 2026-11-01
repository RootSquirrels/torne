# RESOURCE-002 — Faisabilité d'observation du volume LNG déchargé

> ### ⚠️ Ce dossier est **partiellement superseded** par `docs/RESOURCE-002-CORRECTION.md`.
>
> Une revue physique a montré que **la conversion hydrostatique publiée ici était fausse**
> (3,5 t/cm au lieu de **111,3 t/cm**, soit 0,001 % au lieu de **1,4 %** d'incertitude), que
> **Sentinel-1 ne mesure pas le tirant d'eau**, que le tirant d'eau des méthaniers qui ballastent
> simultanément est **constant par construction**, et que **la cargaison est déjà mesurée** trois
> fois par trois parties. **La recommandation « GO sous condition » du §6 est donc caduque** : la
> note de correction conclut à un **NO-GO** sur la reconstruction de la cargaison par tirant d'eau,
> et à un **changement de grandeur visée** plutôt qu'à l'abandon de la piste.
>
> Ce qui reste valable ici : le périmètre, l'échantillon, la référence mensuelle et sa latence,
> l'opportunité d'observation radar et son coût. **La note de correction corrige le reste.**

> **Mission bornée.** Elle ne construit **ni modèle ni produit**. Elle mesure, sur un échantillon de
> terminaux d'importation de GNL, ce qu'il faut pour **reconstruire le volume effectivement
> déchargé** — et elle rend sa mesure rejouable. Le livrable est un **rapport de coût
> d'observation** et une **recommandation go/no-go**.
>
> La mission suit `docs/FILTRE-MISSION.md` : la grandeur visée est la **cargaison déchargée**, et sa
> validation est **physique** d'abord, économique ensuite. Cette mission s'arrête à la porte
> physique.
>
> Toutes les mesures ci-dessous ont été faites **par exécution**, le **1ᵉʳ novembre 2026**, sur des
> sources réelles.

**Règle de preuve.** **[FAIT]** (observé sur une requête ou sur les octets reçus), **[INFÉRENCE]**
(lecture plausible d'un fait observé), **[NON VÉRIFIÉ]** (non vérifié, avec la marche à suivre).

**Reproduction.**

```bash
uv run python experiments/resource_002_faisabilite_lng.py       # la mesure et la confrontation
uv run python experiments/resource_002_latence_reference.py     # la latence de publication de la reference
```

---

## 0. Ce que la mission a changé

1. **La cargaison n'est dans aucune source ouverte.** L'archive portuaire du FMI — PortWatch — ne
   publie que des **comptes** de mouvements par type de cargaison. Sur les **211 services** de son
   dossier ArcGIS, **sept** ont des couches, et **aucun** n'est au niveau du navire : ni identité,
   ni numéro OMI, ni capacité, ni **tirant d'eau**. Les services `Daily_Trade_Data_*` et
   `portsfacts` sont des **coquilles vides**. **[FAIT]**

2. **La voie d'observation ouverte qui reste est l'observation radar**, et elle est **plus rare et
   plus chère** qu'il n'y paraît. Le catalogue Copernicus Data Space donne, pour une emprise de
   12 km autour d'un terminal, **18 à 31 passages** Sentinel-1 réels par mois (et non les 120 à
   166 *produits* : un passage est découpé en produits dont les horodatages diffèrent de quelques
   millisecondes). Une escale de 24 h contient **une** image dans **36 à 70 %** des cas, et
   **deux images distinctes** — les seules qui donnent une différence de tirant d'eau — dans
   **2 à 15 %** seulement. Le volume à télécharger est de **263 à 486 Go par terminal et par
   mois**. **[FAIT]**

3. **La référence existe, elle est datée, et elle est de grande qualité.** L'exploitant publie
   chaque mois, **par plante**, les GWh déchargés, le **nombre de navires** déchargés, les
   expéditions et les tirages cisternes — et, sur une autre page, les capacités de regazéification.
   **La porte de validation physique est donc ouverte** : la référence contre laquelle confronter
   l'estimation existe, elle est datée, et elle est par terminal. **[FAIT]**

4. ~~L'incertitude de la méthode n'est pas le verrou.~~ **CORRIGÉ** — voir la note de correction :
   un centimètre de tirant d'eau vaut **111,3 tonnes** de GNL, pas 3,5 ; l'incertitude est de
   **1,4 %** pour ±10 cm, pas 0,001 %. Et surtout, le verrou n'est ni la mesure ni le coût :
   c'est que **Sentinel-1 ne mesure pas le tirant d'eau**, que le tirant d'eau est **constant par
   construction** sur les méthaniers qui ballastent simultanément, et que **la cargaison est déjà
   mesurée**. **[FAIT] et [INFÉRENCE] — voir `docs/RESOURCE-002-CORRECTION.md` §1, §2 et §6.**

5. **La source maritime qui semblait la fondation est la moins commode à utiliser au niveau du
   terminal.** L'interface ouverte de PortWatch refuse les filtres par nom de port, refuse les
   statistiques, expire sur les `LIKE`, et plafonne le nombre de lignes : **extraire les appels
   d'un terminal n'est pas possible par son API de requête**. La voie utilisable est le
   **téléchargement en masse** des fichiers CSV du FMI — qui reste à localiser et à extraire. **[FAIT]**

6. **Le piège de la mission est la confusion des grandeurs**, et il est réel : le bulletin mensuel
   publie côte à côte les **GWh déchargés**, les **GWh réexpédiés**, les **GWh en citerne** et la
   **regazéification en GWh**. Ce sont **quatre** grandeurs. Les confondre, c'est produire une
   cargaison qui n'est pas une cargaison. La mission les tient séparées, et la nomenclature le
   dit. **[FAIT]**

---

## 1. Le protocole

### 1.1 Les grandeurs, tenues séparées

C'est la première précaution de la mission, et elle est structurante.

| Grandeur | Ce que c'est | Unité | **Jamais** assimilée à |
|---|---|---|---|
| **Cargaison déchargée** | le GNL effectivement déchargé du navire | GWh/mois, et nombre de navires | — |
| **Expédition** | le GNL **rechargé** sur un navire (ré-export) | GWh/mois | la cargaison |
| **Tirage citerne** | le GNL chargé sur une **citerne** (route) | GWh/mois | la cargaison |
| **Regazéification** | le débit **sortant** vers le réseau | GWh/mois | la cargaison |
| **Capacité de regazéification** | nominale / contractualisée / disponible | GWh/mois | un débit observé |

> **[FAIT] La confusion serait chiffrable.** En juin 2026, Barcelone a **déchargé 1 559 GWh**,
> **réexpédié 167 GWh** et **chargé 207 GWh** en citerne. additionner les trois — ou prendre le
> débit de regazéification (13 505 GWh/mois pour tout le pays) — donnerait un chiffre **sans
> commune mesure** avec la cargaison. C'est pour cela que la mission refuse d'inférer une cargaison
> d'un taux d'utilisation.

### 1.2 L'échantillon

Six terminaux d'importation du système gaziste espagnol, choisis parce que l'**exploitant publie
leurs chiffres individuellement et mensuellement** — condition d'une confrontation possible :

| Terminal | Plante | Enagás | Coordonnées |
|---|---|---|---|
| Barcelona | BARCELONA | Enagás | 41,350 N / 2,165 E |
| Cartagena | CARTAGENA | Enagás | 37,595 N / 0,950 O |
| Bilbao | BILBAO | Enagás | 43,355 N / 3,035 O |
| Sagunto | SAGUNTO | Enagás | 39,680 N / 0,265 O |
| Huelva | HUELVA | Enagás | 37,200 N / 6,930 O |
| Mugardos | MUGARDOS | Enagás | 43,500 N / 8,255 O |

Deux pays, deux opérateurs, six sites, une seule campagne de référence : **avril, mai et juin 2026**.

---

## 2. Ce qui a été mesuré

### 2.1 La source des escales : PortWatch, et pourquoi elle ne suffit pas

**[FAIT]** `Daily_Ports_Data` compte **1 852 864 lignes** : un enregistrement par port et par jour,
avec `portcalls` et sa décomposition par type (`portcalls_container`, `portcalls_dry_bulk`,
`portcalls_general_cargo`, `portcalls_roro`, `portcalls_tanker`, `portcalls_cargo`) et les flux
`import_*` / `export_*`. C'est un **décompte**, sans identité de navire.

**[FAIT] L'interface de requête refuse ce qu'on lui demande.** Cinq formes, cinq échecs :

| Forme tentée | Réponse |
|---|---|
| `where=portname='Barcelona' AND year=2026 AND month=4` | **504** — le balayage de 1,85 M lignes expire |
| `where=portname LIKE '%Barcelona%' AND …` | **504** |
| `where=portid='port118' AND …` | **aucune ligne** — l'identifiant du registre n'est pas celui de la table |
| `outStatistics` (somme, ou groupée par jour) | **« Invalid query parameters »** |
| `orderByFields` sans `resultRecordCount`, ou `resultRecordCount` > 1 000 | refusé, ou **aucune ligne** |

**[FAIT]** Ce qui marche : le filtre sur `year`, `month`, `day` — le champ `date` est un
**`esriFieldTypeDateOnly`** — mais alors le service **plafonne le nombre de lignes renvoyées** et
la fenêtre obtenue ne couvre pas les terminaux cherchés. Les noms exacts des ports ne sont pas
« Barcelona » mais **« … LNG Terminal »** dans la table quotidienne, et le référentiel des ports
(2 065 entrées) ne les relie pas.

> **Ce que cela signifie.** La confrontation PortWatch ↔ Enagás **n'est pas faisable par l'API
> ouverte**, et c'est un résultat, pas un oubli. La voie est le **téléchargement en masse** des
> fichiers CSV du FMI. Cela n'empêche pas la porte de validation : la référence de la porte est
> l'**exploitant**, pas PortWatch.

### 2.2 La référence : le bulletin de l'exploitant

**[FAIT]** Le *Boletín Estadístico* est publié **chaque mois**, à une adresse datable, et sa page 17
porte le tableau **« Actividad en planta de Regasificación »** : pour chaque plante, les GWh
déchargés, le nombre de navires déchargés, les GWh réexpédiés et les GWh en citerne, avec la
colonne de l'année précédente et la variation. La page 15 porte les **capacités de regazéification**
et le débit commercial. Les trois bulletins de la campagne ont été téléchargés et conservés comme
preuve.

**[FAIT] La référence retenue, en navires GNL déchargés (GWh entre parenthèses) :**

| Plante | avril 2026 | mai 2026 | juin 2026 |
|---|---|---|---|
| BARCELONA | 6 (4 590) | 3 (2 493) | 2 (1 559) |
| HUELVA | 3 (3 182) | 2 (1 560) | 2 (2 173) |
| CARTAGENA | 2 (401) | 3 (2 586) | 2 (1 882) |
| BILBAO | 4 (4 417) | 5 (5 472) | 3 (3 299) |
| SAGUNTO | 4 (1 869) | 4 (4 224) | 1 (1 065) |
| MUGARDOS | 2 (2 192) | 2 (2 198) | 2 (2 132) |
| MUSEL | 0 (0) | 0 (0) | 0 (0) |
| **Espagne (total)** | **21 (16 651)** | **19 (18 533)** | **12 (12 112)** |

**[FAIT] Les autres flux, pour la même campagne** — les grandeurs qu'il ne faut pas confondre :

| Plante | avril : déchargé / réexpédié / citerne | mai | juin |
|---|---|---|---|
| BARCELONA | 4 590 / 303 / 213 | 2 493 / 434 / 203 | 1 559 / 167 / 207 |
| HUELVA | 3 182 / 319 / 117 | 1 560 / 543 / 139 | 2 173 / 455 / 140 |
| CARTAGENA | 401 / 205 / 200 | 2 586 / 49 / 183 | 1 882 / 397 / 171 |
| BILBAO | 4 417 / 645 / 107 | 5 472 / 0 / 115 | 3 299 / 0 / 113 |
| SAGUNTO | 1 869 / 191 / 164 | 4 224 / 0 / 172 | 1 065 / 0 / 169 |
| MUGARDOS | 2 192 / 86 / 83 | 2 198 / 151 / 76 | 2 132 / 0 / 79 |
| **Total** | 16 651 / 1 748 / 952 | 18 533 / 1 177 / 957 | 12 112 / 1 019 / 947 |

**[FAIT] Et les capacités**, juin 2026, pour tout le système : capacité de regazéification **totale
58 350 GWh/mois**, **contractualisée 14 252**, **disponible 44 098**, regazéification commerciale
**13 505 GWh/mois**.

**[FAIT] Une réserve inscrite dans le bulletin lui-même** : *« Las operaciones reflejadas son
aquellas llevadas a cabo en el régimen de acceso regulado »*. La référence ne couvre que les
opérations en **accès régulé** — ce n'est pas le trafic total du terminal.

### 2.3 L'opportunité d'observation : Sentinel-1

**[FAIT]** Le catalogue Copernicus Data Space donne, pour une emprise de 12 km autour du terminal, et
par mois :

| Terminal | mois | Passages | Écart médian | P(1 image / 24 h) | **P(2 images distinctes / 24 h)** | P(1 image / 48 h) |
|---|---|---|---|---|---|---|
| Barcelona | avr. 2026 | 19 | 23,8 h | 52 % | **4 %** | 67 % |
| Barcelona | mai 2026 | 22 | 23,9 h | 50 % | **2 %** | 67 % |
| Barcelona | juin 2026 | 19 | 18,0 h | 49 % | **6 %** | 69 % |
| Cartagena | avr. 2026 | 18 | 12,0 h | 36 % | **8 %** | 52 % |
| Cartagena | mai 2026 | 23 | 12,0 h | 43 % | **12 %** | 60 % |
| Cartagena | juin 2026 | 18 | 12,0 h | 43 % | **10 %** | 61 % |
| Bilbao | mai 2026 | 30 | 12,1 h | 70 % | **4 %** | 85 % |
| Sagunto | mai 2026 | 31 | 11,9 h | 54 % | **13 %** | 70 % |
| Huelva | mai 2026 | 23 | 12,0 h | 46 % | **15 %** | 61 % |
| Mugardos | mai 2026 | 30 | 12,1 h | 70 % | **4 %** | 85 % |

**[FAIT] Un passage est découpé en produits dont les horodatages diffèrent de quelques
millisecondes** — 1ᵉʳ avril : 06:01:19.988 / 06:01:22.346 / 06:01:23.686. Compter les produits
comme des passages surestime l'opportunité d'un facteur **quatre à cinq**. Un écart médian de
« 0,00 h » ne dit pas que le satellite passe toutes les minutes : il dit qu'une passe est
découpée.

**[FAIT] La structure réelle des passages** — à Barcelone, avril 2026 :

```
1ᵉʳ avril  06:01      (passage du matin)
2 avril   05:51      (+23,8 h)   ·   2 avril 17:46  (+11,9 h)
7 avril   06:00      (+108,2 h)  ·   8 avril 05:53  (+23,9 h)  ·  8 avril 17:45  (+11,9 h)
```

Soit **deux passages par jour** (un vers 06:00, un vers 17:45), sur **deux jours consécutifs**,
puis un trou de **≈ 4,5 jours**. L'écart médian de **12 h** est celui des deux passages d'un même
jour — et c'est lui qui rend possible une mesure de tirant d'eau **avant et après** le
déchargement, puisque la durée d'une escale est de l'ordre de la journée.

### 2.4 Le coût d'acquisition

**[FAIT]** Le volume à télécharger pour disposer de toutes les images Sentinel-1 au-dessus d'un
terminal, sur un mois : **263 à 486 Go**, soit **10,4 à 20,6 Go par passage**.

**[FAIT]** Chaque produit Sentinel-1 pèse environ **3,1 Go**, alors qu'un produit couvre **250 km le
long de la trace** : la plus grande part du volume téléchargé ne concerne pas le terminal.

> **Ce que cela signifie.** L'observation est **possible** et **assez fréquente**. Elle est
> **coûteuse**, et elle l'est d'autant plus que la probabilité d'obtenir **deux** passages distincts
> dans une escale de 24 h n'est que de **2 à 15 %**. Pour couvrir toutes les escales d'un terminal,
> il faudrait multiplier les acquisitions par **un ordre de grandeur** — soit plusieurs **téraoctets**
> par terminal et par an.
>
> **Ce coût est le principal frein mesuré de la piste**, et il est *réductible* : un téléchargement
> par tuile, ou la lecture du seul *burst* utile, ferait tomber la facture d'un facteur 4 à 5. Ce
> travail d'optimisation n'a pas été fait ici — c'est le **coût de traitement**, encore **inconnu**.

### 2.5 L'incertitude de la méthode

> ⚠️ **Cette section était fausse et est corrigée par `docs/RESOURCE-002-CORRECTION.md` §1.**
> La relation n'est pas `ΔV = Cb · L · B · Δd / d` — la division par le tirant d'eau n'a rien à
> faire là. La relation correcte est :
>
> ```
> d(déplacement)/dT = ρ_sw · Cb · Lpp · B        [tonnes par mètre]
> ```
>
> Pour un méthanier de 177 000 m³ (Lpp 280 m, B 52 m, tirant d'eau 11,7 m, déplacement plein
> 130 233 t), cela donne **111,3 t/cm** — et non 3,5 t/cm. L'incertitude sur une cargaison de
> 80 000 t est donc de **1,39 %** pour ±10 cm et de **4,17 %** pour ±0,3 m.
>
> **[FAIT] Trois inconnues structurelles dominent de loin la précision de la conversion** : la
> compensation par le ballast (qui **annule** le signal sur une part de la flotte), l'état des
> autres compartiments (ballast, combustibles, eau douce, stores) et l'assiette. Elles ne sont pas
> couvertes par la conversion. Et **Sentinel-1 ne mesure pas le tirant d'eau** : à 20 m de
> résolution, il détecte les navires et estime leur longueur à ±15 %, mal leur largeur.
>
> **[NON VÉRIFIÉ]** l'exactitude d'une mesure de tirant d'eau par Sentinel-1 au mouillage, et
> l'incertitude qu'on peut en attendre. **La marche à suivre** : la littérature SAR sur le tirant
> d'eau (méthode de la houle, signature en avant du navire) donne des ordres de grandeur ; il faut
> les confronter à une mesure de référence — le tirant d'eau publié par l'armateur, ou un relevé de
> tirant d'eau à l'arrivée.

### 2.6 La latence de la référence

**[FAIT]** Au 1ᵉʳ novembre 2026, les bulletins disponibles sont ceux d'**avril**, **mai**, **juin**,
**août** et **septembre** 2026 ; ceux de **juillet** et d'**octobre** ne le sont pas. La référence
mensuelle existe donc avec **environ un mois de retard** sur son édition « AVANCE » — c'est-à-dire
qu'à la fin du mois M, la statistique du mois M est déjà connue.

> **Ce que cela signifie pour la mission.** Une estimation de cargaison n'a pas à être « en avance »
> sur la référence **annuelle** : elle a à être en avance sur la référence **mensuelle**, donc à
> être disponible à un moment où la statistique du mois n'existe pas encore. Avec un retard
> d'environ un mois sur le bulletin, la fenêtre utile pour une estimation « en avance » est
> **l'intervalle entre la fin du mois observé et la publication du bulletin suivant** — soit
> **quelques semaines**.

---

## 3. La porte de validation physique

La porte exige : *« confronter les cargaisons estimées à des statistiques indépendantes et datées de
terminal ou d'exploitant, partout où elles existent »*.

**[FAIT] La référence de cette porte existe**, et elle est complète : les GWh déchargés **et** le
nombre de navires, **par plante**, **par mois**, avec la colonne de l'année précédente et la
variation. Elle est compilée au §2.2 et les trois bulletins sont conservés comme preuve.

**[FAIT] Ce qui manque n'est pas la référence, c'est l'estimation.** La porte ne peut pas être
franchie tant qu'il n'existe pas **une seule** cargaison estimée. Et les deux chiffres à confronter
ne sont pas de même nature : le bulletin donne une **énergie** (GWh), l'observation radar donne une
**masse** (tonnes). La confrontation suppose donc une conversion — la masse volumique du GNL
(≈ 450 kg/m³) — **et** le rendement de la conversion d'énergie, qui dépend de la composition du
GNL et du terminal. **C'est un point de conversion à établir explicitement**, et il n'est pas
négligeable.

**[FAIT] La comparaison des *comptes* d'escales, elle, n'a pas pu être faite** — non par manque de
référence, mais parce que l'interface ouverte de PortWatch refuse l'extraction terminale (§2.1).
L'écart de la confrontation ci-dessous est donc **nul par défaut**, et non un écart mesuré :
il ne dit rien du désaccord entre les deux sources, il dit que l'une n'a pas pu être extraite.

| Terminal | mois | Passages SAR | P(2 images / 24 h) | Navires GNL (Enagás) | GWh déchargés (Enagás) | Escales PortWatch |
|---|---|---|---|---|---|---|
| Barcelona | avr. 2026 | 19 | 4 % | 6 | 4 590 | non extractible |
| Barcelona | mai 2026 | 22 | 2 % | 3 | 2 493 | non extractible |
| Barcelona | juin 2026 | 19 | 6 % | 2 | 1 559 | non extractible |
| Cartagena | mai 2026 | 23 | 12 % | 3 | 2 586 | non extractible |
| Bilbao | mai 2026 | 30 | 4 % | 5 | 5 472 | non extractible |
| Sagunto | mai 2026 | 31 | 13 % | 4 | 4 224 | non extractible |
| Huelva | mai 2026 | 23 | 15 % | 2 | 1 560 | non extractible |
| Mugardos | mai 2026 | 30 | 4 % | 2 | 2 198 | non extractible |

**[FAIT] Un signal tout de même, dans les ordres de grandeur** : le nombre de navires GNL
déchargés en Espagne est de **12 à 21 par mois** pour l'ensemble du pays, soit **2 à 6 par terminal
et par mois**. C'est le **nombre de cibles** que la voie radar devrait couvrir. Une couverture de
**2 à 15 %** par escale de 24 h signifie qu'il faudrait observer **sept à cinquante escales** pour
en capturer **une** — et, dans le même temps, cela signifie que **le nombre de cargos à observer
est très faible**. C'est un point favorable pour la piste, et il est mesuré.

---

## 4. Les six métriques de faisabilité

| # | Métrique demandée | Mesure | Verdict |
|---|---|---|---|
| 1 | **Appels de navires identifiables et rattachables à un terminal** | PortWatch donne un **compte** par port et par jour, par type de cargaison — **sans identité de navire**, et l'extraction terminale est **refusée par l'API**. L'exploitant donne le **nombre de navires** par plante, sans identité non plus | **partiel** : le décompte existe des deux côtés, l'identification non |
| 2 | **Proportion d'escales avec tirant d'eau exploitable avant et après** | SAR : **18 à 31 passages** par terminal et par mois, écart médian **12 h** ; P(1 image / 24 h) **36–70 %** ; **P(2 images distinctes / 24 h) = 2–15 %** ; P(1 image / 48 h) **52–85 %** | **défavorable pour la différence**, favorable pour un tirant d'eau **absolu** |
| 3 | **Proportion d'escales avec caractéristiques de navire suffisantes** | aucune source ouverte de caractéristiques par navire ; la flotte GNL est petite et les opérateurs publient leurs **flottes affrétées** — voie à vérifier ; Equasis est accessible mais sur inscription | **non établi** |
| 4 | **Incertitude de chaque cargaison estimée** | **1,4 %** (AIS, ±10 cm) à **4,2 %** (SAR, ±0,3 m) — mais le signal est **annulé** sur les méthaniers qui ballastent simultanément, et le capteur ne sait pas mesurer le tirant d'eau | **défavorable** — et le verrou est ailleurs (voir la note de correction) |
| 5 | **Coût d'acquisition et de traitement** | **263–486 Go** par terminal et par mois ; **10,4–20,6 Go** par passage ; **~75 Go** utiles | **défavorable** — c'est le frein mesuré |
| 6 | **Lacunes, latence, disponibilité historique** | référence : **~1 mois** de retard, disponible par mois ; SAR : catalogue sur toute l'historique, coût d'archive croissant linéairement ; PortWatch : historique quotidien sur 1,85 M lignes, extraction terminale **impossible par l'API** | **favorable pour la référence**, à chiffrer pour l'historique SAR |

---

## 5. Ce qui n'a pas pu être vérifié

- **[NON VÉRIFIÉ]** l'**exactitude** d'une mesure de tirant d'eau par Sentinel-1 au mouillage, et
  l'incertitude qu'on peut en attendre. **La marche à suivre** : confronter une mesure SAR à un
  tirant d'eau de référence (armateur, ou relevé à l'arrivée).
- **[NON VÉRIFIÉ]** la **faisabilité d'un pipeline SAR** de bout en bout : le traitement de la
  signature de houle et la reconstruction du tirant d'eau n'ont pas été mis en œuvre. **La marche à
  suivre** : une paire d'images sur un navire connu de tirant d'eau publié.
- **[NON VÉRIFIÉ]** l'existence d'une **source ouverte de caractéristiques de navire** (capacité,
  type) exploitable à l'échelle de la flotte GNL. **La marche à suivre** : les listes de flottes
  affrétées publiées par les opérateurs, et l'inscription à Equasis.
- **[NON VÉRIFIÉ]** le **coût d'une licence AIS commerciale** (MarineTraffic, VesselFinder) : les
  portails répondent, mais les **données** sont payantes et l'API MarineTraffic refuse les appels
  anonymes (403). **La marche à suivre** : chiffrer une licence sur le volume et la période
  nécessaires — c'est le **repli** de la voie radar.
- **[NON VÉRIFIÉ]** le **facteur de conversion** entre les GWh du bulletin et les tonnes de la
  cargaison : il dépend de la masse volumique du GNL et du **rendement** de la conversion
  d'énergie, propre au terminal. **La marche à suivre** : le demander à l'exploitant, ou le déduire
  des deux mois où l'on a **à la fois** les GWh et un nombre de navires.
- **[NON VÉRIFIÉ]** le **téléchargement en masse** de PortWatch, qui est la voie d'extraction
  terminale identifiée : le portail est accessible, mais les adresses des fichiers CSV n'ont pas
  été localisées. **La marche à suivre** : les pages « Data & Methodology » du Hub ArcGIS.

---

## 6. La recommandation

> ⚠️ **SUPERSÉDÉDÉ — voir `docs/RESOURCE-002-CORRECTION.md` §6.**
> Le « GO sous condition » ci-dessous a été suspendu à la suite d'une revue physique : la conversion
> hydrostatique était fausse, Sentinel-1 ne mesure pas le tirant d'eau, le tirant d'eau est
> constant sur les méthaniers qui ballastent simultanément, et la cargaison **est déjà mesurée**.
> La conclusion corrigée est un **NO-GO sur la reconstruction de la cargaison par tirant d'eau**, et
> un **changement de grandeur visée** — la piste LNG reste la première candidate.
> Le raisonnement d'origine est conservé ci-dessous comme trace.

> **GO, sous condition.** La piste LNG n'est pas écartée : elle est **faisable**. La grandeur est
> spécifiable, la méthode est précise à mieux d'un pourcent, la **référence existe, datée, par
> terminal**, et le nombre de cargos à observer est **très faible** — 2 à 6 par terminal et par
> mois. Mais le **verrou mesuré est le coût d'observation**, et il est aggravé par un fait : la
> différence de tirants d'eau, qui est la mesure propre, n'est disponible que dans **2 à 15 %** des
> escales de 24 h.
>
> **La condition** est une seule : **produire une seule cargaison estimée sur un seul navire de
> tirant d'eau connu**, et la confronter aux GWh du bulletin. Tant que cette paire n'existe pas,
> rien ne se construit.
>
> **Ce qui ne doit pas être fait** : construire un modèle de cargaison, ou un indicateur, avant
> d'avoir **une seule** paire d'images SAR exploitable sur un navire dont on connaît le tirant
> d'eau. Tout le reste serait de la théorie.
>
> **Si la condition n'est pas remplie**, la piste des **minerais** devient la suivante, avec la
> réserve formulée dans l'arbitrage : l'activité visible d'une installation n'est pas sa production
> effective, et **les fichiers GEM n'ont pas encore été extraits** — il faut le faire avant de
> comparer.

### 6.1 Les deux niveaux d'estimation, et lequel viser

**[INFÉRENCE]** Il y a deux niveaux d'estimation, et leur couverture est très différente :

| Niveau | Ce qu'on mesure | Ce qu'on en déduit | Couverture mesurée |
|---|---|---|---|
| **Niveau 1 — tirant d'eau absolu** | le tirant d'eau du navire à l'arrivée, par une seule image | la cargaison, **à un facteur de remplissage près** (le navire charge selon son contrat, pas à plein) | **52 à 85 %** des escales (fenêtre de 48 h) |
| **Niveau 2 — différence de tirant d'eau** | deux images, à l'arrivée et au départ | la cargaison **mesurée**, à ±0,4–1,5 % près | **2 à 15 %** des escales |

> **Le niveau 1 est le bon premier test.** Il demande une seule image, il est couvert dans plus de
> la moitié des cas, et son biais — le taux de remplissage — est **inconnu mais borné** : il peut
> être estimé sur les cargos dont on connaît le tonnage nominal. Le niveau 2 est plus propre mais
> trop rare pour commencer.

### 6.2 Le plan de test qui décide

Un test **borné**, comme la mission l'a demandé :

1. **Un** terminal (Barcelona), **un** mois, **un** navire connu — un cargo de la campagne
   d'avril 2026, par exemple.
2. **Une** image Sentinel-1 sur la passe qui encadre son arrivée, téléchargée **par tuile**.
3. Le tirant d'eau reconstruit, confronté au tirant d'eau de référence.
4. La cargaison déduite, comparée aux **4 590 GWh** déchargés à Barcelone en avril 2026.

**Critères d'arrêt** :

- si le tirant d'eau reconstruit n'est pas à **±0,3 m** près du tirant d'eau de référence, **la voie
  SAR est écartée** et la piste bascule sur les minerais ;
- si le coût de traitement d'un passage ne peut pas être ramené **sous 2 Go**, le levier du coût
  d'acquisition est épuisé et la voie devient une **licence AIS commerciale** — à chiffrer ;
- si la conversion GWh ↔ tonnes ne peut pas être établie à mieux de **±5 %**, la porte de validation
  physique ne peut pas être franchie, quelle que soit la qualité de l'observation.

---

## 7. La suite

1. **Exécuter le test borné du §6.2** — c'est lui qui décide, et il coûte quelques gigaoctets, pas
   quelques téraways.
2. **Localiser le téléchargement en masse de PortWatch** : c'est la voie d'extraction terminale, et
   elle sert aussi à la mission économique (les flux, pas seulement les appels).
3. **Chiffrer une licence AIS commerciale** en parallèle, comme repli du SAR : elle supprimerait la
   question de l'observation, mais coûterait de l'argent chaque mois.
4. **Extraire les fichiers GEM** (piste de repli) et **mesurer** ce qu'ils portent réellement —
   condition posée par l'arbitrage.

---

## 8. Les produits

| Fichier | Rôle |
|---|---|
| `experiments/resource_002_faisabilite_lng.py` | la mesure rejouable : escales, référence, passages SAR, coût, confrontation |
| `experiments/resource_002_latence_reference.py` | la mesure de la latence de publication de la référence |
| `data/resource-002/enagas/*.pdf` | les trois bulletins mensuels, conservés comme preuve (dossier ignoré par git) |
| `data/resource-002/faisabilite_lng.json` | la mesure brute, terminal par terminal et mois par mois |

**État.** `ruff check` et `ruff format` propres. **Aucun contrat partagé n'a été modifié**, et aucun
modèle ni produit n'a été développé — c'était la consigne.
