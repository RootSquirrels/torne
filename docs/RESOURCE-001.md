# RESOURCE-001 — Physical Supply Intelligence : reconnaissance

> **Mission de reconnaissance.** Elle ne développe rien. Elle compare trois pistes — **LNG et
> pétrole**, **minerais et métaux**, **céréales et oléagineux** — et pour chacune elle doit dire :
> quelles sources sont **réellement** accessibles, ce qu'elles portent, ce qui **n'est pas déjà
> couvert** par les produits existants, et quelle **donnée dérivée** dont la valeur économique est
> explicite on pourrait produire.
>
> Elle applique le **filtre à six questions** et les **deux validations** définis dans
> `docs/FILTRE-MISSION.md`.
>
> Toutes les mesures ci-dessous ont été faites **par exécution**, le **1ᵉʳ novembre 2026**, sur des
> sources réelles.

**Règle de preuve.** **[FAIT]** (observé sur une requête ou sur les octets reçus), **[INFÉRENCE]**
(lecture plausible d'un fait observé), **[NON VÉRIFIÉ]** (non vérifié, avec la marche à suivre).

**Reproduction.**

```bash
uv run python experiments/resource_001_sources_probe.py   # l'inventaire d'accessibilité, rejouable
```

---

## 0. Ce que la mission a changé

1. **Le versant maritime de la stratégie est déjà largement couvert — et c'est le FMI qui le
   couvre.** PortWatch n'est pas un jeu de données parmi d'autres : c'est un **système** de quatre
   services publics qui publie les appels de navires par port et par jour (**1 852 864 lignes**), les
   transits par goulot d'étranglement (**79 940 lignes**), le référentiel des **2 065 ports**, les
   **28 goulets**, et **132 perturbations** de ports déclarées — auxquels s'ajoutent un *Disruption
   Monitor*, un *Trade Nowcast* et un **simulateur d'impact sur la chaîne d'approvisionnement**
   (au port, au pays, à la chaîne). **[FAIT]**

2. **Mais PortWatch donne des *comptes de mouvements*, pas des volumes.** Les champs sont
   `portcalls_container`, `portcalls_dry_bulk`, `import_cargo`, `export_cargo` — ce sont des
   **dénombrements**, par type de cargaison et par sens. Aucun champ ne dit de **tonnes**. **[FAIT]**
   C'est exactement le point que la note stratégique pose : *« un simple suivi AIS des ports ne serait
   pas suffisamment différenciant »*. **La note a raison, et la source le confirme par sa structure
   même.**

3. **La frontière de l'innovation n'est donc pas la donnée : c'est l'estimation.** Ce qui n'existe
   nulle part, et que la mission doit viser, c'est le **volume effectif** et l'**écart au régime
   normal** d'une installation ou d'un corridor — avec une **incertitude quantifiée**, et **avant**
   que la statistique publiée ne le dise. **[INFÉRENCE]**

4. **La « économie physique de l'offre » est servie par des portails ouverts, mais ses API sont
   derrière des clés.** Sur les 29 sources sondées : **23 accessibles sans secret**, 2 refus
   explicites (403 USDA PSD, 403 EIA), 1 réponse en 200 qui porte en réalité un refus
   (« Invalid or missing API key », AGSI+), 2 injoignables. **[FAIT]**

5. **Le stock de données ouvertes est plus large que ce que la note suggère**, et il est
   *inégalement utilisable* : UN Comtrade fonctionne **sans clé** sur les codes HS qui comptent
   (271112 GNL, 260111 minerai de fer, 1001 blé) ; Global Energy Monitor tient le **catalogue des
   installations** (25 projets) ; GEOGLAM tient le **suivi des cultures** des grands exportateurs ;
   GDACS, Eurostat et la Pink Sheet de la Banque mondiale sont ouverts. **[FAIT]**

---

## 1. L'inventaire d'accessibilité

La sonde a posé **29** questions à **29** points d'accès, et a classé chaque réponse en cinq états.

**Bilan : 23 accessibles · 2 sur tunnel · 2 contenu inattendu · 2 injoignables.**

### 1.1 Piste 1 — LNG et pétrole

| Source | État | Ce que c'est | Ce qu'on y mesure |
|---|---|---|---|
| **IMF PortWatch — appels quotidiens** | **accessible** — **1 852 864 lignes** | appels de navires par port et par jour, par type de cargaison, par sens | **des comptes**, pas des tonnes |
| **IMF PortWatch — goulets** | **accessible** — **79 940 lignes** | transits par goulot et par jour | intensité du transit |
| **IMF PortWatch — ports** | accessible | référentiel : **2 065 ports**, position, types de navires, part des importations et exportations | le parc, pas l'usage |
| **IMF PortWatch — perturbations** | **accessible** — **132 événements** | fermetures, capacités réduites, avec dates et ports affectés | la rupture, déclarée |
| **IMF PortWatch — simulateur** | accessible | impact d'une perturbation sur la chaîne d'approvisionnement | ce que le FMI sait déjà faire |
| GIE AGSI+ (stocks de gaz UE) | **refus en 200** — « Invalid or missing API key » | stocks hebdomadaires européens | **la capacité réellement disponible** |
| USDA FAS PSD (bilans) | **403** | bilans de production et d'échanges par produit | le chiffre **déclaré** |
| US EIA (stocks) | **403** | stocks et flux de pétrole et de GNL américains | le chiffre **déclaré** |
| UN Comtrade — HS 271112 | **accessible** (2 enregistrements en aperçu) | flux mensuels de GNL | le flux **déclaré** |

### 1.2 Piste 2 — minerais et métaux

| Source | État | Ce que c'est |
|---|---|---|
| **Global Energy Monitor — mines de fer** | **accessible** | `global-iron-ore-mines-tracker` : capacité, statut, coordonnées des mines |
| **Global Energy Monitor — infrastructure gaz** | **accessible** | `global-gas-infrastructure-tracker` : **terminaux GNL**, capacité, mise en service |
| **Global Energy Monitor — infrastructure pétrole** | **accessible** | `global-oil-infrastructure-tracker` : raffineries, terminaux, pipelines |
| **Global Energy Monitor — sidérurgie** | **accessible** | `global-iron-steel-tracker` : **le côté demande** |
| **Global Energy Monitor — terminaux charbon** | **accessible** | `global-coal-terminals-tracker` : le second corridor minier |
| USGS (Mineral Commodity Summaries) | **accessible** | production mondiale par minéral, annuelle |
| UN Comtrade — HS 260111 | **accessible** (2 enregistrements en aperçu) | flux mensuels de minerai de fer |
| OpenStreetMap / Overpass | **injoignable** — 502 | les installations localisées — *serveur à saturation* |

**[FAIT]** Global Energy Monitor publie **25 projets**, dont cinq qui touchent directement cette
piste : les mines de fer, l'infrastructure gaz (donc les terminaux GNL), l'infrastructure pétrole,
la sidérurgie et les terminaux à charbon. **[FAIT]** L'adresse du projet se lit **sans slash final**
— la forme `/projects/global-iron-ore-tracker/` répond **404**, la forme
`/projects/global-iron-ore-mines-tracker` répond **200**.

### 1.3 Piste 3 — céréales et oléagineux

| Source | État | Ce que c'est |
|---|---|---|
| **GEOGLAM / Crop Monitor for AMIS+** | **accessible** | conditions des cultures des grands exportateurs — blé, maïs, soja |
| FAO GIEWS | **accessible** | conditions et perspectives de récolte |
| JRC MARS | **accessible** | suivi des cultures : conditions, débouchés, prévisions |
| USDA PSD Online | **accessible** (portail ; l'API exige une clé) | bilans céréaliers par pays |
| UN Comtrade — HS 1001 | **accessible** (2 enregistrements en aperçu) | flux mensuels de blé |
| NASA LP DAAC (MODIS MCD43A4) | **accessible** (compte Earthdata requis pour les données) | indices de végétation : la surface réellement cultivée |

### 1.4 Transverse

| Source | État | Ce que c'est |
|---|---|---|
| GDACS (JRC) | **accessible** (RSS XML) | événements et catastrophes : les perturbations de production |
| Eurostat | **accessible** | prix et échanges énergétiques européens |
| World Bank Pink Sheet | **accessible** (XLSX) | cours des commodities |
| Global Fishing Watch | **accessible** (portail ; **jeton requis** pour l'AIS) | mouvements AIS de navires |
| Copernicus Data Space | **accessible** | catalogue Sentinel — la voie déjà explorée par le périmètre EO |
| US NGA / NAVTEX | **injoignable** — 503 | avertissements aux navigateurs |

### 1.5 Les trois pièges que la sonde a rencontrés

**[FAIT]** Trois pièges récurrents, qui expliquent pourquoi un `curl` ne suffit pas :

1. **Une API qui répond 200 en refusant.** AGSI+ répond `200` avec
   `{"error": "access denied", "message": "Invalid or missing API key"}`. Ce n'est pas un accès.
2. **Une grande table servie par ArcGIS ne se lit pas comme une petite.** Sur
   `Daily_Ports_Data` (1,85 M lignes), `returnCountOnly=true` renvoie `{"count":1852864}`, mais une
   requête de lignes exige `resultRecordCount` **et** un `orderByFields` explicite, faute de quoi elle
   expire ; et le service **refuse** `returnDistinctValues` (« Invalid query parameters »). La forme
   qui fonctionne pour agréger est la **statistique groupée** (`outStatistics`).
3. **Un espace non encodé casse l'URL avant la requête.** C'est le piège le plus coûteux de cette
   mission, parce que l'erreur ressemble à un défaut de la source : `urllib` refuse une URL
   contenant une espace brute (« URL can't contain control characters »), alors que la source est
   parfaitement saine. `=` n'a pas besoin d'être encodé ; **l'espace, si**. Attention : une version
   antérieure de ce dossier attribuait l'échec à l'encodage de `=` — **c'était faux**, et le
   corriger a ouvert l'accès aux statistiques.
4. **Une URL de service ne se déduit pas du titre de l'item.** Les services PortWatch sont publiés
   par l'équipe `IMF-portwatch_imf_dataviz` sous
   `services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/…` ; l'URL se lit dans le JSON de
   l'item ArcGIS, pas dans son nom. Et sur les **211 services** du dossier, **sept seulement** ont
   des couches : `Daily_Ports_Data`, `Daily_Chokepoints_Data`, `PortWatch_ports_database`,
   `PortWatch_chokepoints_database`, `portwatch_disruptions_database`, `PortWatch_boundaries` et
   `PortWatch_ports`. Les autres — dont `Daily_Trade_Data_WLD` et `portsfacts` — sont des
   **coquilles vides**.

> **[NON VÉRIFIÉ]** l'**extraction d'une ligne réelle** de `Daily_Ports_Data` : le compte est établi,
> mais la lecture de lignes sur un service de 1,85 M lignes n'a pas abouti dans cette session (le
> paramétrage de *big data* n'a pas été stabilisé, et une tentative a expiré après 240 s).
> **La marche à suivre** : la forme `outStatistics` (voir `experiments/resource_002_faisabilite_lng.py`),
> qui agrège le service sans lire les lignes.

---

## 2. Ce qui est déjà couvert — et ce qui ne l'est pas

C'est la question centrale de la mission, et elle a une réponse nette.

### 2.1 Ce qui est déjà couvert

**[FAIT]** Les produits existants couvrent **quatre couches** :

| Couche | Couvert par | Statut |
|---|---|---|
| Les **flux déclarés** | Comtrade, USDA FAS, USDA PSD, USGS, Eurostat | ouvert, avec retard, et **déclaratif** |
| Les **mouvements physiques** | IMF PortWatch (appels, goulets), Global Fishing Watch | ouvert (PortWatch) ou à jeton (GFW) |
| L'**état des installations** | Global Energy Monitor (25 projets) | ouvert |
| Les **ruptures déclarées** | PortWatch (132 perturbations), GDACS | ouvert |

**[FAIT]** Et le FMI a déjà construit les **moteurs** que la note stratégique décrit : un *Disruption
Monitor*, un *Trade Nowcast*, un simulateur d'impact au port, au pays et à la chaîne d'approvisionnement,
et des cartes d'impact supply-chain à 7, 14, 30 et 90 jours. **[FAIT]**

### 2.2 Ce qui n'est couvert par personne

**[INFÉRENCE]** Trois manques, qui se tiennent :

1. **Le volume effectif.** PortWatch donne des **comptes** de mouvements par type de cargaison ;
   Comtrade donne des **tonnes déclarées** à la frontière, avec retard. **Entre les deux, il n'y a
   rien.** Les tonnages de PortWatch sont *estimés* à partir de la **capacité maximale** du navire —
   un *proxy* statique, pas la charge réelle, et il est borné par le plein du navire.
2. **Le régime effectif d'une installation.** GEM donne la capacité **nominale** et le **statut**
   déclaré ; rien ne donne le **facteur d'utilisation** observé, ni son écart au régime normal.
3. **La confrontation datée aux chiffres publiés.** Personne ne publie l'écart entre son estimation
   et la statistique officielle **au moment où cette statistique paraît**. C'est la seule preuve
   qu'une donnée est **en avance** — et c'est ce que la note demande : *« ce changement n'est pas
   encore visible dans les statistiques publiées »*.

> **La position de TORNE.** L'océan, l'atmosphère, l'hydrologie et l'observation de la Terre sont
> les **moyens** de cette reconstruction ; ils ne sont pas l'application. C'est exactement ce que dit
> la note : *« ils ne sont pas nécessairement les applications finales »*.

---

## 3. La grandeur proposée, piste par piste

Chaque piste est formulée dans la langue de la note : **une estimation, un écart au régime normal, une
incertitude quantifiée, et un décalage temporel avec la publication officielle**.

### 3.1 Piste 1 — LNG et pétrole : le taux d'utilisation effectif des terminaux

> **« Nous estimons que le terminal X a chargé N tonnes par semaine, soit p % de sa capacité
> nominale, avec une incertitude de ±q %, et cet écart n'est pas encore visible dans les statistiques
> publiées. »**

**Le difficile.** Passer d'un **compte de mouvements** à un **tonnage effectif** exige d'associer au
mouvement la **charge réelle** du navire — et celle-ci ne se déduit pas du comptage. Elle est
**observable** : tirant d'eau à l'arrivée et au départ, jauge, tirant d'eau maximal autorisé du
terminal, et le tirant d'eau a la charge maximale du navire. C'est un problème d'**observation**, pas de données.

**La chaîne qui rendrait cela faisable.** PortWatch donne le mouvement (port, date, type) ; GEM donne
le terminal (capacité nominale, tirant d'eau maximal, coordonnées) ; le **tirant d'eau** et la
**géométrie du navire** viennent de l'observation (AIS étendu, imagerie satellite, ou inspection
portuaire) ; l'atmosphère et l'océan donnent le **forcing** (vent, courant, hauteur de mer) qui
explique l'écart.

### 3.2 Piste 2 — minerais et métaux : la production effective par installation

> **« Nous estimons que la production effective de cette installation a diminué de 18 % par rapport à
> son régime normal, avec une incertitude quantifiée, et que ce changement n'est pas encore visible
> dans les statistiques publiées. »**

**Le difficile.** Ici, l'installation **est** visible : une mine ou un terminal à minerai a une
signature en imagerie satellite (halos, terrasses, stocks de stérile, poussières`). Le régime normal
s'apprend **sur l'installation elle-même**, par son propre historique — c'est une force du cadre :
la référence est interne, elle n'est pas un chiffre publié qu'on essaie de deviner.

**Pourquoi cette piste est la plus forte.** L'exemple même de la note — *« nous avons une image
satellite d'une mine »* n'est pas la donnée nouvelle — tient : l'image n'est pas la donnée, **l'écart
au régime propre de l'installation, avec son incertitude** l'est. Et l'**incertitude est
quantifiable** : elle vient du nombre d'images exploitables, de la couverture nuageuse, et de la
variabilité naturelle de l'installation.

### 3.3 Piste 3 — céréales et oléagineux : le volume de récolte attendu, et son avance

> **« Nous estimons que la récolte de la région R sera de X millions de tonnes, avec une
> incertitude de ±Y %, à la date Z — trois semaines avant la publication officielle. »**

**Le difficile.** La note le dit elle-même : *« l'estimation satellitaire des rendements est déjà un
domaine de recherche et de concurrence active »*, et la validation au sol et la précision assez
précoce restent difficiles. **Cette piste est donc la plus risquée** — mais elle a l'avantage
décisif que les deux autres n'ont pas : **la date de publication est connue et fixe** (les campagnes
de l'USDA), donc **l'avance** se mesure exactement.

**Le moyen, dans le dépôt.** Le périmètre EO existe déjà (GLORYS12 et le catalogue Copernicus Data
Space sont accessibles), et MCD43A4 (indice de végétation) est le produit de référence pour la
**surface réellement cultivée** — pas le rendement.

---

## 4. Le filtre à six questions, appliqué

| Question | Piste 1 — LNG et pétrole | Piste 2 — minerais et métaux | Piste 3 — céréales |
|---|---|---|---|
| **Quelle information manque ?** | le tonnage effectivement chargé, par terminal et par semaine | la production effective, par installation | le volume de récolte attendu, par région, et son avance |
| **Pourquoi est-elle mal connue ?** | les ports publient des **comptes** de mouvements ; les tonnages publiés ont un retard et sont déclaratifs | la capacité est **nominale** et le statut est déclaratif ; aucun facteur d'utilisation n'est publié | le rendement satellite existe mais n'est ni validé au sol ni assez précoce |
| **Qui est concerné ?** | producteurs, négociants, utilities, fonds énergie | minerai, sidérurgie, aciéristes, transporteurs | producteurs, négociants, assureurs, agricultures |
| **Quelle variable économique est affectée ?** | l'offre de GNL disponible sur le marché | la production effective de minerai, donc le prix et l'offre d'acier | le volume de récolte, donc le prix et la sécurité alimentaire |
| **Quelle donnée nouvelle produisons-nous ?** | la charge réelle par mouvement, reconstituée, et son écart à la capacité nominale | l'écart au régime propre de l'installation, avec son incertitude | la surface réellement cultivée et le rendement attendu, datés |
| **Comment vérifier sa valeur ?** | confrontation aux chargements connus (déclarations de arrives), aux statistiques portuaires et à la Pink Sheet | confrontation aux bilans de production et aux flux Comtrade du même mois | confrontation au bulletin USDA et à la publication de la campagne |

### 4.1 Les deux validations, par piste

**[FAIT]** elles sont distinctes, et la note est explicite : *« on ne doit pas utiliser un bon
backtest financier pour masquer une estimation physique incorrecte »*.

| | **Validation physique** — l'estimation décrit-elle le monde ? | **Validation économique** — apporte-t-elle de l'information ? |
|---|---|---|
| **Piste 1** | la charge reconstituée est-elle compatible avec la capacité du navire et du terminal ? (l'erreur doit être bornée par la physique) | l'écart au régime change-t-il la prévision de l'offre disponible, **par rapport** aux données déjà publiées ? |
| **Piste 2** | l'écart détecté correspond-il à un changement observable (arrêt, incapacity, travaux) et non à un artefact d'observation ? | la variation estimée explique-t-elle une part de la variation du prix, **au-delà** de ce qu'expliquent déjà les bilans publiés ? |
| **Piste 3** | la surface détectée correspond-elle à l'usage du sol observé et aux statements des producteurs ? | l'avance estimée réduit-elle l'erreur de prévision de récolte, **par rapport** au bulletin USDA ? |

---

## 5. Ce que la mission ne tranche pas

- **Quel produit de référence pour le "régime normal" ?** La note suggère l'idée d'un écart au régime
  propre ; mais un régime se mesure sur **au moins une ou deux campagnes complètes**, ce qui change
  l'horizon de chaque mission.
- **La question du *tonnage* : observation ou inférence ?** Pour la piste 1, la charge réelle
  d'un navire est **observable** (tirant d'eau) mais l'observation est coûteuse ; l'inférence à
  partir du type de navire et du comptage est **gratuite** mais biaisée par le taux de remplissage.
  Ce choix détermine la faisabilité de la piste 1 et il n'appartient pas à cette mission.
- **La piste 3 est-elle une piste ou un pari ?** La note le dit : c'est un domaine de concurrence
  active. Elle mérite d'être **comparée** aux deux autres, pas d'être menée de front.
- **Le sort de MARINE-003** : la note propose de le suspendre, et de garder l'océan 3D comme
  **capacité complémentaire**. C'est une décision d'orientation, pas une preuve — mais elle est
  **cohérente** avec ce que MARINE-001 et MARINE-002 ont établi.

---

## 6. Ce qui n'a pas pu être vérifié

- **[NON VÉRIFIÉ]** l'**extraction d'une ligne réelle** de `Daily_Ports_Data` (le compte est établi,
  la lecture ne l'est pas) — voir §1.5.
- **[NON VÉRIFIÉ]** les **fichiers de données** de Global Energy Monitor : les pages de suivi sont
  ouvertes, mais les **fichiers** eux-mêmes (XLSX/CSV) n'ont pas été localisés ni ouverts.
- **[NON VÉRIFIÉ]** les **contenus** de GEOGLAM / Crop Monitor for AMIS+ et de JRC MARS : les portails
  sont ouverts, mais leurs **séries** n'ont pas été interrogées.
- **[NON VÉRIFIÉ]** l'accès aux **données** de LP DAAC (compte Earthdata) et de GFW (jeton) : les
  portails répondent, les données demandent une inscription.
- **[NON VÉRIFIÉ]** le **décret de l'AGSI+**, d'USDA PSD et d'EIA : les trois exigent une clé, et
  l'inscription n'a pas été faite.
- **[NON VÉRIFIÉ]** l'**état de NAVTEX** (503 à la date de la mesure) — il s'agit d'un service
  gouvernemental, et un 503 peut être une indisponibilité momentanée.

---

## 7. La suite proposée

1. **Décider laquelle des trois pistes on mène** — et pour cela, une seule chose manque, et elle est
   mesurable : **le coût de l'observation** de la charge réelle (piste 1) et de l'activité d'une
   installation (piste 2). C'est la seule question que la mission n'a pas encore tranchée, et elle
   se tranche par un test de faisabilité, pas par une réunion.
2. **Inscrire les trois clés** (AGSI+, USDA PSD, EIA) — elles sont gratuites, et elles ouvrent la
   partie **déclarée**, qui sert de **référence** pour les validations physique et économique.
3. **Poursuivre MARINE comme capacité**, pas comme finalité : l'océan 3D sert désormais à estimer
   les **contraintes de navigation** (profondeur, courant, hauteur de mer) et les **délais** — ce que
   la note relie explicitement à l'inflation via les durées de transport.

---

## 8. Les produits

| Fichier | Rôle |
|---|---|
| `experiments/resource_001_sources_probe.py` | l'inventaire d'accessibilité des 29 sources, rejouable, avec vérification de la forme du contenu |
| `data/resource-001/probe*/sonde_resource_001.jsonl` | la preuve brute, une ligne par source (dossier ignoré par git) |

**État.** `ruff check` et `ruff format` propres. **Aucun contrat partagé n'a été modifié.**
