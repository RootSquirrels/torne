# Mississippi — qualification des sources de données

**Statut** : document de travail, rédigé le 31 octobre 2026 par requêtes réelles sur les API et pages publiques.
**Portée** : documenter ce que TORNE peut réellement ingérer pour reconstruire les états hydrologiques et
opérationnels du Mississippi et étudier leurs conséquences sur le transport fluvial.
**Règle de preuve** : chaque affirmation est classée **[FAIT]** (observé sur une requête), **[INFÉRENCE]**
(lecture plausible d'un fait observé) ou **[NON VÉRIFIÉ]** (non vérifié — avec la marche à suivre).
Toutes les URL ont été consultées le **31 octobre 2026** ; le statut HTTP et un extrait représentatif sont
donnés pour chaque appel.

---

## 1. Cartographie des sources

| # | Source | Nature | Identifiant / endpoint | Période observée | Rôle dans le slice |
|---|--------|--------|------------------------|------------------|--------------------|
| S1 | USDA/AMS — taux de fret avan aval (« percent-of-tariff ») | Base de données Socrata | `deqi-uken` | 2004-01-07 → 2026-10-27 (1 191 semaines) | Témoin économique : le prix du transport |
| S2 | USDA/AMS — prix par tonne, par tronçon | Base de données Socrata | `7spn-fbua` | idem S1 | Conversion du témoin économique en dollars/tonne |
| S3 | USDA/AMS — taux à 1 mois / 3 mois (forward) | Base de données Socrata | `svms-9yya`, `uuhv-5etw` | idem S1 | Anticipation : ce que le marché Futures regardait |
| S4 | USDA/AMS (source USACE) — mouvements de grains par écluse | Base de données Socrata | `n4pw-9ygw` | 2003-01-04 → 2026-10-24 (1 243 semaines) | Témoin de volume : ce qui a réellement transité |
| S5 | USDA/AMS (source USACE) — comptage de barges vides/chargées | Base de données Socrata | `w6ip-grsn` | 2005-08-27 → 2026-10-24 | Témoin de capacité / retour à vide |
| S6 | USDA/AMS — Table 9 / Figure 10 du *Grain Transportation Report* | Fichiers XLSX | `GTRFigure10Table9.xlsx` | non vérifié | Version « papier » de S1/S3 |
| S7 | USDA/AMS — Table 10 du *Grain Transportation Report* | Fichiers XLSX | `GTRTable10.xlsx` | non vérifié | Version « papier » de S4 |
| S8 | USACE — Lock Performance Monitoring System (LPMS) | API Oracle APEX | `ndc.ops.usace.army.mil/ords/lpms/` | courant (fenêtre 30 j) | État opérationnel : écluses, tirant d'eau, fermetures |
| S9 | USGS — nouvelle API OGC (Water Data for the Nation) | API OGC Features | `api.waterdata.usgs.gov/ogcapi/v1` | 1851 → courant | Témoin hydrologique : hauteur et débit |
| S10 | USGS — anciennes API WaterServices | API REST (dépréciée) | `waterservices.usgs.gov/nwis/*` | jusqu'à 2027-02-22 | **Non retenue** — voir §4 et §8 |

### Chaîne causale que le slice doit observer

```
hydrologie (S9)  ──►  navigabilité (S8)  ──►  volume transporté (S4/S5)  ──►  prix (S1 → S2)
     │                                                                 ▲
     └──►  contexte (gabarit, pluie, glace) ───────────────────────────┘
```

Le **prix** (S1) est le résultat ; l'**hydrologie** (S9) en est la cause ; le **volume** (S4) est le
mécanisme intermédiaire. Sans les trois, on ne peut rien conclure sur « les conséquences du transport
fluvial sur les prix » : il faut au minimum une variable hydrologique *et* une variable de volume.

---

## 2. Fiches techniques

### S1 — USDA/AMS, taux de fret avan aval (percent-of-tariff)

**Identité et provenance.** Base Socrata hébergée par USDA/AMS, domaine `agtransport.usda.gov`,
identifiant `deqi-uken`, catégorie « Barge », `provenance: official`, `publicationStage: published`,
`scope: public`, `useRestriction: Unrestricted`, `attribution: USDA/AMS`, contact `agtransport@usda.gov`.
**[FAIT]** — métadonnées : `https://agtransport.usda.gov/api/views/deqi-uken.json` (statut 200).

**Les sept zones et leur barème.** La description de la source énonce : *« Twin Cities = 619;
Mid-Mississippi = 532; St. Louis = 399; Illinois = 464; Cincinnati = 469; Lower Ohio = 446; and
Cairo-Memphis = 314 »*, et *« To calculate the rate in dollars per ton, multiply the percent of tariff
rate by the 1976 benchmark and divide by 100: (Rate * 1976 tariff benchmark rate per ton)/100. As an
example, a 271 percent tariff for a St. Louis grain barge would equal 271 percent of the St. Louis
benchmark rate of $3.99, or $10.81 per ton. »* **[FAIT]** — ces valeurs sont vérifiées *dans la source*,
pas reprises de mémoire. Elles sont en **cents par tonne** : 399 cents = $3,99.

**Les sept `location` réels dans les données.** `Twin Cities`, `Mid-Mississippi`, `Lower Illinois`,
`St. Louis`, `Cincinnati`, `Lower Ohio`, `Cairo-Memphis` — 1 191 valeurs chacun.
**[FAIT]** — `?$select=location,count(*)…&$group=location`.
> ⚠ **Piège de nommage.** La description parle de *« Illinois River »* et le barème de *« Illinois = 464 »*,
> mais la **valeur de la colonne `location` est `Lower Illinois`**. Une jointure par libellé écrit
> « Illinois River » échoue. **[FAIT]** (deux sources : description et valeurs observées).

**Convention de date.** La colonne `date` est décrite comme *« Week ending date, ranging from 2004 to the
present »*. **[FAIT]**. Les colonnes `week`, `month`, `year` sont **calculées**, pas brutes : `week` =
*« Week number calculated from the reported week ending date… Week 1 is the first week of the year with a
week ending date falling on or after January 4 »* ; `month` = *« Week ending dates falling before the
fourth day of the month are assigned to the previous month »*. **[FAIT]**.
**[FAIT]** — jour de la semaine réellement observé : `2004-01-07` = **mercredi**, `2026-10-27` = **mardi** ;
la bascule se situe autour de `2006-09-20` (mercredi) → `2006-09-26` (mardi). **[INFÉRENCE]** la source
raisonne en semaines *finissant* le mardi sur la période récente et le mercredi avant 2006 ; le libellé
de champ reste « week ending date » dans les deux cas.

**Granularité du `rate`.** Le champ est numérique et **rarement entier** : valeurs observées
`782`, `564.0625`, `731.25`, `706.25`, `814.2857`, `723.2142`, `158.3333`, `326.6666`.
**[FAIT]**. Contrôle arithmétique : **1 219** valeurs sur 7 563 ne sont pas multiples de 1/16 ;
**1 585** ne sont pas multiples de 1/28 ; **2 679** ne sont pas multiples de 1/3. **[FAIT]** (trois requêtes
de comptage distinctes).
> **[INFÉRENCE]** les fractions observées ont des dénominateurs 3, 7, 16 et 28 : cela correspond à des
> **moyennes de cotations sur un nombre variable de jours** (3 j, 1 semaine, 2 semaines, 4 semaines).
> Autrement dit, `rate` est un **moyennage**, pas une cotation ponctuelle de fin de semaine. Cela n'est écrit
> nulle part dans la source. À confirmer auprès d'AMS.
> Conséquence pratique : **`rate` n'est pas une observation du dernier jour de la semaine.** Un modèle
> qui veut la date « d'observation » ne peut pas l'assumer ; il ne dispose que de la fin de semaine.

**Valeurs manquantes — le point le plus important de la fiche.**
774 lignes sur 8 337 n'ont pas de `rate` (9,3 %). **[FAIT]**.
Répartition par localisation : `Twin Cities` **426**, `Mid-Mississippi` **303**, `Lower Illinois` 25,
`St. Louis` 7, `Cairo-Memphis` 3, `Cincinnati` 5, `Lower Ohio` 5. **[FAIT]**.
Répartition par mois : janvier 199, février 181, mars 114, décembre 167, avril 33, novembre 25, mai 19,
juin 16, juillet 9, août 5, septembre 5, octobre 1. **[FAIT]**.
> **[INFÉRENCE forte]** la concentration hivernale (déc.–mars : 661 des 774, soit 85 %) et la concentration
> sur les deux zones les plus amont traduisent la **fermeture hivernale de la navigation sur le Haut-Mississippi**
> (fermeture de saison, glace). Ce n'est pas une absence aléatoire : c'est un **structural**, et il est
> **saisonnier**, donc il ne doit jamais être traité comme un zéro ni comme une panne de collecte.
> Le champ `Rate` le dit d'ailleurs : *« Note: Empty cells indicate no rate record for that week at that
> location »*. **[FAIT]**

**Profondeur et intégrité.** 1 191 dates distinctes × 7 localisations = 8 337 lignes — le panneau est
**complet**, aucune date manquante, aucune localisation manquante. **[FAIT]** (`count(distinct date)=1191`,
`count(*)=8337`, `count(rate)=7563`, et un contrôle `$group=date&$having=n<7` ne renvoie **aucune** ligne).
De 2004-01-07 à 2006-09-20 les semaines sont complètes ; à partir de 2006-09-26 le rythme est
hebdomadaire sans trou. **[FAIT]**.

**Révision.** `rowsUpdatedAt = 1793290350` → **2026-10-29T16:12:30Z**, `rowsUpdatedBy = aiqt-4thn`,
`lastUpdatedAt = 2026-10-29T16:12:30Z`, `createdAt = 1550251187` (2019-02-15), `publicationDate = 1558726744`
(2019-05-24), `publicationStage = published`, `viewCount = 150511`, `downloadCount = 179831`.
**[FAIT]** — métadonnées de la source.
> **[FAIT]** la publication est **révisée en continu** : le `rowsUpdatedAt` du 31 octobre 2026 est postérieur
> de 4 jours à la dernière date de données (2026-10-27). L'historique peut donc être corrigé après coup.
> **[NON VÉRIFIÉ]** s'il existe un journal des révisions par ligne. Aucun n'est exposé par l'API.

**Licence / attribution.** `useRestriction: Unrestricted`, `attribution: USDA/AMS`, `licenseName: null`,
`licenseLink: null`, `licenseLogo: null`. **[FAIT]**.
> ⚠ **[FAIT]** `licenseName` et `licenseLink` sont **explicitement nuls** : il n'y a pas de licence
>arborescence (CC-BY…) déclarée dans les métadonnées. L'attribution `USDA/AMS` + `useRestriction:
> Unrestricted` est tout ce qui est documenté. **Non vérifié** : la licence applicable au *contenu*
> (les taux eux-mêmes, hérités des tarifs ICC de 1976) — la source indique que le DOJ a fait des tarifs
> de l'ICC de 1976 la référence, sans préciser le statut de droit de la réutilisation.
> Pour le dépôt : mentionner « USDA/AMS, Ag Transportation Open Data ».

---

### S2 — USDA/AMS, prix par tonne par tronçon (`7spn-fbua`)

**Identité.** Même portail Socrata USDA/AMS, identifiant `7spn-fbua`, colonnes `date`,
`river_system_location`, `price_per_ton`. 26 tronçons (sections de rivière) ; même calendrier de dates
que S1 (1 191 semaines). **[FAIT]**.

**Rôle.** C'est la **contrepartie en dollars** de S1. La description de la source explique que le barème
varie **selon l'origine exacte et la distance au Golfe**, et renvoie à un fichier Excel annexé
(« Rate Data by Segment ») pour les barèmes par tronçon. **[FAIT]**.

**Contrôle arithmétique décisif.** J'ai reconstitué le prix à partir du taux de S1 et d'un barème par
tronçon, pour la semaine du 2026-10-27, sur les 26 tronçons :
`price_per_ton = rate × benchmark_cents / 10000`. **24 tronçons sur 26** se résolvent exactement avec un
barème en **cents entier** ; les deux restants (« Desoto Landing - Hurricane Point », « Letsworth -
Greenville ») ne se résolvent avec aucun taux de la semaine. **[FAIT]** (calcul reproductible).
Exemples vérifiés : `Memphis - West Memphis` = 481,25 × 314/10000 = 15,11125 $ ; `Chicago` = 731,25 ×
578/10000 = 42,26625 $ ; `Louisville - Jeffersonville` = 706,25 × 446/10000 = 31,49875 $.
> **[INFÉRENCE]** les prix de S2 sont bien « taux de S1 × barème du tronçon », ce qui confirme la formule
> documentée et donne un barème par tronçon. Mais **deux tronçons résistent** : soit leur barème n'est pas
> un nombre entier de cents, soit leur prix dépend d'une autre série de taux. **[NON VÉRIFIÉ]** — il faut
> le fichier « Rate Data by Segment » (annexé à la page de la source, non téléchargé : c'est un XLSX
> binaire, hors périmètre des appels JSON).
> **Conséquence pour le slice : utiliser S2 directement pour les dollars**, et ne pas recalculer depuis S1
> sauf pour vérifier. La règle de conversion « barème de zone » de S1 est **insuffisante** : elle marche
> pour 4 tronçons sur 26 testés.

**Comparaison de granularité.** S2 donne **26 tronçons** là où S1 donne **7 zones**.
**[FAIT]**. S2 est donc **plus fins géographiquement** mais **moins universellement peuplés** : certaines
zones de S1 (Cairo-Memphis, St. Louis) ont des taux robustes, tandis que les tronçons du Haut et de
l'Illinois peuvent avoir des prix plus dispersés.

**Moyennes de cotations.** Un constat qui traverse S1 et S2 : les fractions décimales observées
(`814.2857`, `723.2142`, `158.3333`) impliquent un **moyennage sur un nombre variable de jours**.
**[FAIT]** (valeurs observées) + **[INFÉRENCE]** (moyennage).
> **[NON VÉRIFIÉ]** le nombre exact de jours agrégés et la règle de pondération.

---

### S3 — USDA/AMS, taux forward à 1 mois et 3 mois

`svms-9yya` (« One Month Future Rates ») et `uuhv-5etw` (« Three Month Future Rates ») existent dans le même
portail, avec une colonne supplémentaire `rate_month`. **[FAIT]** (colonnes observées via une requête
`$select` qui a renvoyé les enregistrements).
Valeurs observées au 2026-10-27 : `rate_month = 11` pour le taux à un mois (novembre) et
`rate_month = 1` pour le taux à trois mois (janvier 2027). **[FAIT]**.
Complétude : à trois mois, `Twin Cities` 796 valeurs sur 1 191 et `Mid-Mississippi` 862 — soit **environ
un tiers des semaines sans cote en amont**. **[FAIT]**.
> **[INFÉRENCE]** l'amont du fleuve est **beaucoup moins bien couvert en forward** qu'en spot : c'est
> cohérent avec une liquidité moindre pour les cargaisons longues. Utile comme variable de confiance.
> La série « nearby » de S1 est le seul repère de prix sûr sur toute la période.

---

### S4 — USDA/AMS (source USACE), mouvements de grains par écluse (`n4pw-9ygw`)

**Identité et provenance.** Portail Socrata USDA/AMS, `n4pw-9ygw`, `attribution: U.S. Army Corps of
Engineers`, `attribution_link: https://corpslocks.usace.army.mil/lpwb/f?p=121:1:1`, `provenance: official`.
Les données proviennent donc du **LPMS de l'USACE**, rediffusées par USDA/AMS.
**[FAIT]** — métadonnées.

**Schéma réel.** Colonnes : `date`, `week`, `month`, `year`, `commodity`, `lock`, `tons`.
**[FAIT]** — vérifié de deux façons : requête `$select` avec projection invalide (le message d'erreur du
moteur SoQL **énumère les colonnes réelles** : `SELECT \`date\`, \`week\`, \`month\`, \`year\`, \`commodity\`,
\`lock\`, \`tons\``) et lecture directe des lignes.

**Volume.** 26 452 lignes, 26 344 valeurs non nulles de `tons`, 1 243 dates distinctes.
**[FAIT]**.

**Les sept écluses.** `AK Lock 1`, `IL La Grange`, `MS Lock 15`, `MS Lock 25`, `MS Lock 26`,
`MS Locks 27`, `OH Olmsted` — 7 valeurs distinctes. **[FAIT]**.
> ⚠ **Écart métadonnées / données, à signaler.** La description de la source ne décrit que **« three
> major points »** (Miss Locks 27, Ohio Olmsted, Ark Lock 1) et la page AMS annonce Table 10 comme
> « Weekly barged grain movements through specific locks and dams ». Or **les données contiennent sept
> écluses**, pas trois. **[FAIT]** — la description est en retard sur la donnée.
> **Conséquence : ne jamais piloter le schéma depuis la description ; piloter depuis les valeurs.**

**Rupture de profondeur — le point critique.** Trois écluses (`AK Lock 1`, `MS Locks 27`, `OH Olmsted`)
remontent au **2003-01-04** (1 243 semaines, 4 972 lignes chacune). Les quatre autres (`IL La Grange`,
`MS Lock 15`, `MS Lock 25`, `MS Lock 26`) ne commencent qu'au **2013-01-05** (721 semaines, 2 884 lignes
chacune). **[FAIT]**.
> **[INFÉRENCE]** le passage à sept écluses est daté de **janvier 2013** (ouverture d'IL La Grange et
> instrumentation de L/D 15-25-26). Une série temporelle « touschlüssel » par écluse sur 2003-2013
> serait **faux** : il faut traiter la profondeur comme une **propriété de l'écluse**, pas de la table.

**Convention de date.** Ici la semaine **finit le samedi** : 2026-10-24, 2026-10-17, 2026-10-10, 2026-10-03,
2026-09-26. **[FAIT]**. S1/S2 finissent le **mardi**. **Les deux séries USDA ne sont donc pas
synchronisées** : la dernière semaine de grains disponible (samedi 2026-10-24) précède la dernière
semaine de taux (mardi 2026-10-27) de trois jours.
> ⚠ **Conséquence directe pour le slice : une jointure « même semaine » entre S1/S2 et S4/S5 produit un
> décalage temporel silencieux de trois jours.** C'est le piège d'intégration n°1 de ce dossier.

**Unités et zéros.** `tons` : minimum **0**, maximum **953 441**. **[FAIT]**. Un `tons = 0` est **une
valeur réelle** (aucun grain de cette catégorie n'a transité), pas une absence. **[INFÉRENCE forte]**
(dsn les 108 valeurs manquantes de `tons` existent aussi : 26 452 − 26 344).
**Zéro et manquant sont deux choses distinctes** et ne doivent pas être confondus dans le schéma.

**Catégories.** Exactement quatre : `Corn` (6 613 lignes), `Other Grain` (6 613), `Soybeans` (6 613),
`Wheat` (6 613). **[FAIT]** — 4 × 6 613 = 26 452 ✓.
> **[NON VÉRIFIÉ]** ce que recouvre exactement `Other Grain` (céréales secondaires ? sorgho ? orge ?) et
> si la catégorie a changé dans le temps. À demander à USDA/AMS ou au responsable USACE.

**Fréquence.** Hebdomadaire, sans exception observée sur 1 243 semaines. **[FAIT]**.

**Révision.** `rowsUpdatedAt = 1793290287` → 2026-10-29T16:11:27Z ; `rowsUpdatedBy = aiqt-4thn`.
**[FAIT]**. Même mécanisme de révision continue que S1 : la dernière semaine de données (2026-10-24) a été
mise à jour le 2026-10-29.

**Licence / attribution.** `useRestriction: Unrestricted`, `attribution: U.S. Army Corps of Engineers`.
**[FAIT]**. Mention obligatoire : « U.S. Army Corps of Engineers, via USDA AMS Ag Transportation ».

---

### S5 — USDA/AMS (source USACE), comptage de barges (`w6ip-grsn`)

**Schéma réel.** `date`, `week`, `month`, `year`, `lock`, `direction`, `type`, `barge_count`.
**[FAIT]** — Same technique : le message d'erreur SoQL énumère les colonnes réelles
(`SELECT \`date\`, \`week\`, \`month\`, \`year\`, \`lock\`, \`direction\`, \`type\`, \`barge_count\``).

**Contenu.** Trois écluses seulement : `Ark Lock 1`, `Miss Locks 27`, `Ohio Olmsted`. Deux sens :
`Down`, `Up`. Cinq types : `Empty`, `Grain, Loaded`, `Loaded`, `Non-Grain, Loaded`, plus `Loaded` (nu).
**[FAIT]**.

**Période.** Du **2005-08-27** au 2026-10-24 (fin de semaine **samedi**, comme S4). **[FAIT]**.
`Ark Lock 1` : `Empty` 1 105 semaines, `Grain, Loaded` 1 096, `Non-Grain, Loaded` 1 096, `Loaded` 9.

> ⚠ **Changement de taxonomie au 2005-10-29.** Le type `Loaded` (sans qualificatif) n'existe que sur
> **9 semaines** (2005-08-27 → 2005-10-22) et disparaît ensuite, remplacé par la paire
> `Grain, Loaded` / `Non-Grain, Loaded` (à partir du 2005-10-29). **[FAIT]**
> → **Piège n°2** : une jointure naïvement construite sur `type` perd 9 semaines et doit gérer une
> taxonomie qui a changé en cours de série. Il faut une table de correspondance, pas un `CASE` ad hoc.

**Ce que S5 apporte que S4 n'a pas.** S4 donne des **tonnes** ; S5 donne un **nombre de barges**.
**[INFÉRENCE]** le rapport tonnes/barge par_lock × commodity est une **densité de chargement** : il
distingue « peu de grain mais en barges pleines » de « beaucoup de grain en barges à moitié vides ».
C'est un signal opérationnel que les tonnes seules ne donnent pas.

---

### S8 — USACE, Lock Performance Monitoring System (LPMS)

**Identité.** Portail APEX : `https://ndc.ops.usace.army.mil/ords/r/lpms/corps-locks/`. Page « Data Web
Services » : `.../corps-locks/data-web-services`. **[FAIT]**.

**Ce que le portail promet.** Rapports listés sur la page d'accueil : *Lock Queue Flotilla* (30 derniers
jours, rafraîchi toutes les 15 min), *Lock Status Report* (condition opérationnelle courante de chaque
écluse, 30 derniers jours, 15 min), *River at a Glance* (24 h, 30 min), *Monthly Tonnage Report*
(2021-2026, quotidien 10 h ET), *Monthly Key Lock Report* (2016-2026, mensuel), *Annual Usage Report*
(2016-2025), *Annual Commodity Report* (2016-2025), *Annual Lock Unavailability Report* (2016-2025, heures
d'indisponibilité). **[FAIT]** — page d'accueil LPMS.

**Endpoints documentés et testés.**

| Endpoint | Test | Résultat |
|---|---|---|
| `json/lock_status_report?in_river_codes=MI` | 2026-10-31, 3 essais | **`SERVICE TEMPORARILY OFF`** —.body texte brut, pas de JSON |
| `lock_status_report_json?in_river_code=MI` | 2026-10-31 | **200, données complètes** |
| `lock_status_report_json?in_river_code=MS` | 2026-10-31 | 200 mais `{"riverName":"","locks":[]}` — code fluvial vide |
| `json/monthly_tons_report?in_river_name=OH&in_lock=79&in_month_year=102026` | 2026-10-31 | 200, 8 catégories de marchandises |
| `json/monthly_tons_report?in_river_name=MI&in_lock=27&in_month_year=102026` | 2026-10-31 | 200, 8 catégories |
| `json/traffic_report?in_river=MI&in_lock=27` | 2026-10-31 | 200 |
| `xml/lock_queue/MI02` | 2026-10-31 | 200, XML, file d'attente sur 30 jours |
| `stall_stoppage_json?begin_date=01102026&end_date=31122026` | 2026-10-31 | 200, JSON |

> ⚠ **Surprise majeure n°1.** **L'endpoint « moderne » et documenté (`json/lock_status_report`) était hors
> service le 31 octobre 2026** (réponse littérale `SERVICE TEMPORARILY OFF`), alors que **l'endpoint
> « hérité » (`lock_status_report_json`, non listé dans la documentation des web services) répondait
> parfaitement**. **[FAIT]** — trois tentatives, codes fluviaux `MI`, `MS`, `OH`, toutes identiques.
> **Conséquence : un connecteur doit implémenter les DEUX endpoints et basculer de l'un à l'autre sur
> erreur.** Le portail n'est pas un service à point unique. C'est un fait de fiabilité observé, pas une
> hypothèse.

**Le contenu de `lock_status_report_json?in_river_code=MI`** — **[FAIT]**, extrait représentatif :

```json
{"riverName": "MISSISSIPPI RIVER", "locks": [
  {"lockNumber":"02","lockMile":815,"lockName":"L/D 2","readingEntryDateTime":"103126:0600",
   "gageUpperElevation":687.70,"gageLowerElevation":675.22,"damCondition":"     2.5",
   "airTemparture":49,"precipitation":"   0.10","weatherCode":"RN",
   "totalPendingArrivals":1,"totalLocking":0,"totalLockedUp24Hours":2,"totalLockedDown24Hours":5,
   "average24HourDelay":"       0","waterTemperature":"56",
   "notes":"Current Flow is 7,010*\r Outdraft begins at 31,000\r \r *Upper gauge may be incorrect...",
   "stations":[{"stationName":"MI02"}]}]}
```

Champs observés : `riverName`, `locks[]` avec `lockNumber`, `lockMile`, `lockName`,
`readingEntryDateTime`, `gageUpperElevation`, `gageUpperElevationChange`, `gageLowerElevation`,
`gageLowerElevationChange`, `damCondition`, `airTemparture` *(sic — faute d'orthographe dans la source)*,
`precipitation`, `weatherCode`, `totalPendingArrivals`, `totalLocking`, `totalLockedUp24Hours`,
`totalLockedDown24Hours`, `average24HourDelay`, `waterTemperature`, `iceCover`, `notes`, `stations[].stationName`.

**Points de vigilance sur le schéma.**
- **Nombres et chaînes mélangés** : `damCondition` est la chaîne `"     2.5"` (espaces de remplissage),
  `precipitation` la chaîne `"   0.10"`, `average24HourDelay` la chaîne `"       0"`, alors que
  `gageUpperElevation` est le nombre `687.70`. **[FAIT]**. Le parseur doit normaliser ; ne pas supposer
  un type-homogène.
- **`readingEntryDateTime` a deux formats** : `"103126:0600"` (MMDDYY:HHMM) chez MI02/MI03/MI04/MI05, et
  **`":"`** chez MI01, MI51, MI52, MI55, MI06, MI07 — c'est-à-dire **une valeur vide**. **[FAIT]**.
  Les écluses sans relevé récent n'ont pas d'horodatage, pas zéro.
- **`notes` est du texte libre non structuré** — c'est là que se trouve l'information la plus utile
  *et* la plus fragile. Exemples réels : `"10/31/2026 CURRENT FLOW 9,090 Gates are in. PLEASE NOTE: We
  cannot pull loaded northbound barges with a notch on the port head when river flow exceeds 21,000 CFS
  (out draft) ICE: 0%"` (MI03) ; `"Flow is at 14,500 cfs Outdraft begins at 59,000 cfs Lock is open for nav
  traffic"` (MI04) ; `"Current flow 18,100 cubic feet per second... Out draft conditions start at 32,000
  cubic feet per second..."` (MI55). **[FAIT]**.
  > **[INFÉRENCE]** `notes` contient les **seuils d'outdraft** (tirant d'eau) et les **consignes
  d'exploitation** — exactement l'information de navigabilité manquante ailleurs. Mais c'est du texte libre
  : à parser, à versionner, et **jamais** à indexer comme donnée numérique fiable.
  > ⚠ **[FAIT]** le `notes` de MI01 porte la date **« 26FEB2024 »** alors que le relevé est daté d'octobre
  > 2026 : **le texte libre n'est pas rafraîchi à la même fréquence que les mesures**. Ne jamais dater un
  > fait opérationnel sur la seule foi de `notes`.

**Fermetures et restrictions de navigation — `stall_stoppage_json`.** **[FAIT]** — champs observés :
`eroc`, `riverCode`, `lockNumber`, `chamberNumber`, `beginStopDate`, `endStopDate`, `isScheduled`,
`reasonCode`, `numHwCycles`, `year`, `refreshDate`, `trafficStopped`.
`reasonCode` observés : `Maintaining lock or lock equipment`, `Repairing lock or lock hardware`,
`Bridge or other structure (i.e railway, pontoon, swing etc.)`, `Closed ( unmanned shift)`,
`River current or Outdraft condition`, `Lightning`, `Lock staff occupied with other duties`.
> ✔ **`River current or Outdraft condition`** est le code qui relie directement l'hydrologie à la
> fermeture. **[FAIT]** (observé sur GI-11, le 30 et le 31 octobre 2026).
> ✔ Les horodatages portent l'**abréviation de fuseau** (`CDT`, `EDT`) : l'USACE publie en heure locale,
> avec fuseau explicite. C'est une aubaine : pas d'ambiguïté. **[FAIT]**
> ⚠ `trafficStopped` vaut `Y` ou `N` : un arrêt peut être **sans** effet sur le trafic. **[FAIT]**

**Tonnage mensuel — `monthly_tons_report`.** **[FAIT]** : 8 catégories avec `commCode`, `commDesc`,
`upboundTons`, `downboundTons`, `totalTons` — `10 Coal, Lignite And Coke`, `20 Petroleum and Petroleum
Products`, `30 Chemicals and Related Products`, `40 Crude Materials, Inedible, except Fuels`,
`50 Primary Manufactured Goods`, `60 Food and Farm Products`, `70 All Manufactured Equipment and
Machinery`, `90 Others, NEC`. Sur MI/27/10-2026 : `downboundTons` = **null** pour la catégorie 70 et
`upboundTons` = **null** pour la catégorie 90. **[FAIT]**.
> Ici encore **null ≠ 0**, et le sens du trafic est explicitement séparé (amont/aval).

**Le point à ne pas manquer : LPMS ≠ archives.**
> ⚠ **Surprise majeure n°2.** L'API LPMS operationale donne l'**état courant** (30 jours) et des
> **agrégats mensuels depuis 2021**, **pas** l'historique hebdomadaire de grains par écluse sur 20 ans.
> L'historique long existe — mais **via USDA/AMS** (S4/S5, qui rediffusent le LPMS), pas via l'API
> opérationnelle USACE. **Les deux canaux ne sont pas équivalents et ne sont pas redondants** : l'un est
> l'archive, l'autre est l'état de l'instant. Un slice qui veut l'historique **doit** passer par S4/S5 ;
> un slice qui veut la navigabilité au jour le jour **doit** passer par S8.

---

### S9 — USGS, nouvelle API OGC (Water Data for the Nation)

**Identité.** `https://api.waterdata.usgs.gov/ogcapi/v1/`. Implémentation **OGC API Features** ; la
documentation existe en Markdown (`.html.md`) et un index `llms.txt` liste les pages.
**[FAIT]** — `https://api.waterdata.usgs.gov/llms.txt` (200) et
`https://api.waterdata.usgs.gov/docs/ogcapi/migration/index.html.md` (200).

**Collections** (constatées via `…/collections?f=json`) : `daily`, `latest-daily`, `continuous`,
`latest-continuous`, `monitoring-locations`, `time-series-metadata`, `field-measurements`,
`latest-field-measurements`, `parameter-codes`, `statistic-codes`, `site-types`, `states`, `reliability-codes`,
`topographic-codes`, `time-zone-codes`. **[FAIT]**.

**Schéma des valeurs quotidiennes — `…/collections/daily/items?f=csv`.** **[FAIT]**, en-tête exact :

```
x,y,time_series_id,monitoring_location_id,parameter_code,statistic_id,time,value,unit_of_measure,approval_status,qualifier,last_modified
```

`continuous` ajoute `method_category`. **[FAIT]**.
`monitoring-locations` expose notamment `monitoring_location_name`, `site_type_code`, `hydrologic_unit_code`,
`basin_code`, `drainage_area`, `contributing_drainage_area`, `altitude`, `vertical_datum`,
`vertical_datum_name`, `original_horizontal_datum`, `time_zone_abbreviation`, `uses_daylight_savings`.
**[FAIT]**.

**Le contrat de requête — et ses pièges.** Trois surprises, toutes vérifiées :

1. ⚠ **`monitoring_location_id` seul ne suffit pas.** La requête
   `daily/items?monitoring_location_id=USGS-07030000&limit=5` renvoie **zéro** feature ; la même avec
   `datetime=2026-10-20/2026-10-27` en renvoie zéro aussi, alors que
   `daily/items?monitoring_location_id=USGS-07020500&datetime=2026-10-25/2026-10-29` en renvoie 5.
   **[FAIT]**. Le filtre `monitoring_location_id` **fonctionne**, mais il faut aussi une contrainte
   temporelle ou de paramètre pour obtenir des lignes. Testé et reproduit sur 07030000, 07001000,
   07020500, 07022000, 05331000, 05592575.
2. ⚠ **`monitoring_location_number` n'est pas une propriété requête-able** sur `/daily` :
   `InvalidQuery — At least one requested property wasn't found`. **[FAIT]**. De même `ids=` et
   `time_series_id=` en paramètre de filtre sont refusés (`InvalidQuery`). Le passage par `bbox` + `datetime`
   fonctionne et **est la voie robuste** (testé sur 6 emboîtements, toujours des lignes).
3. ✔ `f=csv` renvoie une **ligne d'en-tête** exploitable telle quelle ; `f=json` renvoie un GeoJSON
   FeatureCollection. **[FAIT]**.

**Les paramètres ne sont pas homogènes d'une station à l'autre — c'est le cœur du problème.**
`…/collections/time-series-metadata/items` liste, par station et par série, `parameter_code`,
`statistic_id`, `begin`, `end`, `computation_period_identifier`, `computation_identifier`,
`thresholds`, `data_gap_interval`, `parent_time_series_id`. **[FAIT]**.

Comparaison de deux stations du même fleuve :

| Station | `00060` débit | `00065` hauteur | Remarque |
|---|---|---|---|
| `USGS-07020500` (Chester, IL) | `00003` Mean, **1942-07-01 → 2026-10-29** ; `00011` Points, 1989→ | `00011` Points 2007→ ; **`30800` SelectedValue Daily 1982→** | hauteur quotidienne = **statistic 30800**, pas 00003 |
| `USGS-07022000` (Thebes, IL) | `00003` Mean **1933-04-01 → 2026-10-29** ; `00011` Points 1989→ | `30800` Daily 1982→ | idem |
| `USGS-05331000` (St. Paul, MN) | `00003` Mean **1892-03-01 → 2026-10-29** ; `00011` Points 2015→ | `00011` Points 2013→ ; **pas de 30800** | **pas de hauteur quotidienne** |
| `USGS-07030000` (Hatchie River, TN) | `00003` Mean ; `Max At Event Time` 1930→2025-04-07 | — | **ce n'est pas le Mississippi** |

**[FAIT]** pour chaque ligne (valeurs de début observées par requêtes directes :
`…/daily/items?monitoring_location_id=USGS-07020500&parameter_code=00060&statistic_id=00003&datetime=1942-07-01/1942-07-03`
→ 3 lignes `Approved`, 600 000 / 584 000 / 560 000 ft³/s ;
`…/daily/items?monitoring_location_id=USGS-05331000&parameter_code=00060&statistic_id=00003&datetime=1892-03-01/1892-03-03`
→ 3 lignes `Approved`, 4 000 ft³/s).

> ⚠ **Surprise majeure n°3 — les numéros de station « évidents » sont faux.**
> `USGS-07030000` est le **Hatchie River near Stanton, TN**, pas le Mississippi à Cairo.
> `USGS-07001000` est **MISSISSIPPI RIVER AT EAST ST. LOUIS, ILL. (MO)** — la bonne station, mais elle
> **ne renvoie aucune donnée** sur `/daily` ni sur `/time-series-metadata` (déjà signalé), et l'ancienne
> API renvoie `No sites found matching all criteria` pour `dv` comme pour `iv`.
> `USGS-07010088` est **River Des Peres at Shrewsbury, MO** (un ruisseau urbain) ;
> `USGS-05592575` est **Hickory Creek near Brownstown, IL** ; `USGS-01010000` est le **St. John River
> (Maine)** ; `USGS-07005000` est **Maline Creek at Bellefontaine Neighbors, MO**.
> **[FAIT]** — Each réconcilié par recoupement entre `monitoring-locations` (nouvelle API) et
> `/nwis/site` (ancienne API). Les deux sources concordent sur chaque nom.
> **Conséquence : la sélection des stations doit se faire par `monitoring_location_name` + position, jamais
> par un numéro de station de mémoire.**

**Les vraies stations du Mississippi, vérifiées** (via `/nwis/site?siteName=MISSISSIPPI RIVER&siteType=ST&stateCd=17`) :
`05420400 MISSISSIPPI RIVER AT DAM 13 NEAR FULTON, IL` (superficie 856 000 acres, début 2015-10-01),
`05587450 Mississippi River at Grafton, IL` (171 300), `05587498 Mississippi River Pool Lock and Dam 26 at
Alton, IL` (385 314), `07020500 Mississippi River at Chester, IL` (708 600),
`07022000 Mississippi River at Thebes, IL` (713 200), `07001000 MISSISSIPPI RIVER AT EAST ST. LOUIS` (384 633),
`05331000 MISSISSIPPI RIVER AT ST. PAUL, MN`.
**[FAIT]**. D'autres existent hors IL/MN (Ohio : `03086000` Ohio River at Sewickley PA ; `03614500` Ohio
River at Cairo IL) — **à vérifier station par station**, la présence dans le catalogue ne valant pas
disponibilité des séries.

**Statut de qualité — `approval_status`.** Deux valeurs observées : `Approved` et `Provisional`.
**[FAIT]**. Les valeurs de 2026-10-27/28/29 sur 07020500 et 07022000 sont `Provisional` ; les valeurs de
1942 et de 1892 sont `Approved`. `last_modified` est présent et horodaté en UTC
(ex. `2026-10-30 08:12:04.122915+00:00` pour une valeur du 2026-10-29).
**[FAIT]**.
> Règle d'ingestion : **ne jamais figer un `Provisional` sans le revalider** ; `last_modified` permet de
> détecter les révisions rétroactives.
> **[FAIT]** des `last_modified` postérieurs à la date de la valeur et datés de 2025 (ex. `2025-03-11`
> sur des séries de 1942) prouvent que **l'historique est révisé après coup**.

**Profondeur historique et trous.** Profondeur par série : 1851+ (St. Paul, séries d'étiage),
1892 (St. Paul, débit quotidien), 1933 (Thebes), 1942 (Chester). **[FAIT]**.
`data_gap_interval` vaut `1:12:00` sur les séries instantanées et `2:00:00` sur d'autres. **[FAIT]**.
> **[NON VÉRIFIÉ]** l'existence et la granularité des trous réels à l'intérieur des séries. `data_gap_interval`
> indique la tolérance de trou de l'équipement, pas la présence effective de trous.

**Repères verticaux et fuseaux.** `vertical_datum` = `NAVD88` pour les stations modernes
(07020500, 07022000, 05331000) mais **`NGVD29`** pour `USGS-07030000` et pour la série
`USCE-370000089094501` (Ohio River at Cairo, IL — fournies par l'USACE, `agency_code` = USCE, pas USGS).
**[FAIT]**. `time_zone_abbreviation` = `CST` avec `uses_daylight_savings` = `Y` sur les stations USGS
observées ; `EST` pour les stations à l'est. **[FAIT]**.
> ⚠ **Deux pièges de datation.** (a) L'API **ne convertit pas** vers un fuseau unique : les `time` sont en
> heure locale de station, `last_modified` est en UTC. **(b)** Le Mississippi traverse CST (hiver) et CDT
> (été) : une série « jour » n'est pas décalée de façon uniforme sur l'année.
> → **Règle : travailler en UTC à l'indexation, après conversion explicite par station.**

**Altitudes et surfaces de bassin.** `altitude` et `drainage_area` / `contributing_drainage_area` sont
disponibles par station. **[FAIT]**. Utiles pour pondérer une observation hydrologique par sa
représentativité.

**Documentation et clés.** Les pages de documentation sont en Markdown et indexées par `llms.txt` ;
`apis.json` est un catalogue machine. Une page « Get an API Key » existe (`/signup/`) : **la clé donne des
limites de débit plus élevées**. **[FAIT]**. Le nombre exact de requêtes par heure **sans** clé est
**non vérifié** — mais le mécanisme est documenté.

**Dépréciation — la date exacte, et elle est plus tardive que « T1 2027 ».** **[FAIT]**, texte source
(blog USGS « Intentional degradations to WaterServices ahead of final decommissioning », repris dans les
résultats de recherche) :
> « **WaterServices will be decommissioned on February 22nd, 2027.** » … « On January 27th, 2027, we will
> redirect all requests to waterservices.usgs.gov to this blog post for approximately 24 hours. … On
> February 1st, 2027, we will increase the delay to 60 seconds per request. On February 15th, 2027, we will
> redirect … for approximately 48 hours. … On February 22nd, 2027, we will redirect … **We do not anticipate
> delaying the February 22nd decommissioning date.** Users will need to migrate to the new Water Data APIs
> before **November 16th, 2026**, to avoid any impact. »

et, pour les paquets R/Python : « **ALL NWIS web services (readNWIS functions) will be retired Feb. 22,
2027.** Replace all readNWIS functions with read_waterdata functions as soon as possible. »
Campaign 3 (pages NWISWeb) s'étend de **novembre 2026 à février 2027**.
> ⚠ **Point d'attention daté.** La date de bascule opérationnelle pour les *utilisateurs de paquets* est
> **le 16 novembre 2026**, soit **seize jours après la date de ce document**. La fenêtre de migration est
> donc **ouverte et courte**, pas lointaine.
> **[FAIT]** le guide de migration `…/docs/ogcapi/migration/` **ne contient pas** ces échéances : il
> documente les correspondances d'endpoints (`/dv`→`/daily`, `/iv`→`/continuous`, `/site`→
> `/monitoring-locations` et `/time-series-metadata`, `/gwlevels` et `/measurements`→`/field-measurements`,
> `/peak`→`/peaks`). Les dates de coupure viennent du blog de dépréciation.

**Ce que la nouvelle API donne que l'ancienne ne donnait pas.** `thresholds` (seuils opérationnels et
civils par série), `data_gap_interval`, `parent_time_series_id` (chaîne de dérivation),
`computation_period_identifier` / `computation_identifier`, `revision_note`, `revision_created`,
`revision_modified` sur les stations. **[FAIT]**. `thresholds` contient par exemple
`National Weather Service Floodstage` (27 ft à Chester, 33 ft à Thebes), `Peak Stage, 49.74 ft, Aug 7,
1993`, `Operational limit (maximum) very high condition threshold` (55 ft). **[FAIT]**
→ **Ce sont des repères de navigabilité,文的, déjà codifiés.** Un gabarit de seuil de décision navigable
est donc disponible **dans la source**, sans le reconstruire.

**Latence de publication.** `last_modified` sur une valeur du 2026-10-29 à `2026-10-30 08:12:04Z` → le
quotidien est publié **le lendemain matin**. **[FAIT]**. Sur 07022000, une valeur du 2026-10-30 est
modifiée le 2026-10-31 08:07:38Z → latence d'environ **1 jour**. Sur le continu, `last_modified` à
`2026-10-31 08:00:00Z` pour des mesures à `2026-10-31 08:00:00Z` → latence **quasi nulle** (le
`continuous` est rafraîchi en continu).
> **Règle d'acquisition : viser J+2 pour le quotidien, et pollir `continuous` pour l'intraday.**

---

## 3. Schémas réels

### 3.1 USDA/AMS `deqi-uken` — taux de fret
Colonnes réelles (ordre d'affichage) : `date` (calendar_date), `week` (number), `month` (number),
`year` (number), `location` (text), `rate` (number, nullable).
Type OData v4 vérifié dans `$metadata` : `date` → `Edm.String`, `week`/`month`/`year` → `Edm.Decimal`,
`location` → `Edm.String`, `rate` → `Edm.Decimal`. **[FAIT]**.
**[FAIT]** le SoQL renvoie `rate` sous forme de **chaîne** (`"782"`, `"564.0625"`) : le cast numérique est
à la charge du connecteur.

### 3.2 USDA/AMS `n4pw-9ygw` — mouvements de grains par écluse
`date`, `week`, `month`, `year`, `commodity` (text), `lock` (text), `tons` (number, nullable).
Valeurs observées de `commodity` : `Corn`, `Other Grain`, `Soybeans`, `Wheat`.
Valeurs observées de `lock` : `AK Lock 1`, `IL La Grange`, `MS Lock 15`, `MS Lock 25`, `MS Lock 26`,
`MS Locks 27`, `OH Olmsted`.
**[FAIT]**.

### 3.3 USDA/AMS `w6ip-grsn` — comptage de barges
`date`, `week`, `month`, `year`, `lock` (text), `direction` (text), `type` (text), `barge_count` (number).
`direction` ∈ {`Down`, `Up`} ; `type` ∈ {`Empty`, `Grain, Loaded`, `Loaded`, `Non-Grain, Loaded`}.
**[FAIT]**.

### 3.4 USDA/AMS `7spn-fbua` — prix par tonne
`date`, `river_system_location` (text, 26 tronçons), `price_per_ton` (number).
**[FAIT]**.

### 3.5 USACE `lock_status_report_json` — état des écluses
Voir §2, S8. Attention : **types mixtes** et `readingEntryDateTime` parfois `":"`.
**[FAIT]**.

### 3.6 USGS `/daily/items` — valeurs quotidiennes
En-tête CSV exact, voir §2 S9. `time` est une **date locale de station** (sans fuseau) ; `last_modified`
est un **instant UTC**. **[FAIT]**.
`approval_status` ∈ {`Approved`, `Provisional`} ; `unit_of_measure` ∈ {`ft`, `ft^3/s`, `tons/day`, `degC`,
`pH Units`, `mg/l`} selon les séries. **[FAIT]**.

### 3.7 USGS `/time-series-metadata/items` — catalogue des séries
En-tête CSV exact :
`x,y,id,unit_of_measure,parameter_name,parameter_code,statistic_id,last_modified,begin,end,computation_period_identifier,computation_identifier,thresholds,sublocation_identifier,primary,monitoring_location_id,web_description,parameter_description,parent_time_series_id,data_gap_interval,statistics_begin`.
**[FAIT]**.

### 3.8 Codes `statistic_id` relevés
`00003` = Mean (quotidien), `00011` = Points/Instantaneous, `30800` = SelectedValue (quotidien, hauteur),
`32400` = Max (instantané), vide = Max At Event Time (eau). **[FAIT]** pour `00003`, `00011`, `30800` ;
`32400` observé sur une série de température ; le `statistic_id` **vide** observé sur les séries
« Water Year / Max At Event Time ». **[NON VÉRIFIÉ]** : la table de codes complète
(`…/collections/statistic-codes`) n'a pas été dépouillée.

---

## 4. État de chaque API

| API | Endpoint exact | Auth | Pagination | Limites | Dépréciation |
|---|---|---|---|---|---|
| USDA/AMS SoQL | `https://agtransport.usda.gov/resource/deqi-uken.json` | aucune | `$offset`/`$limit` | `$limit=50000` accepté **[FAIT]** | aucune annoncée |
| USDA/AMS CSV | `https://agtransport.usda.gov/resource/deqi-uken.csv` | aucune | idem | idem | — |
| USDA/AMS OData v4 | `https://agtransport.usda.gov/api/odata/v4/deqi-uken` | aucune | `@odata.nextLink` + `$skiptoken` **[FAIT]** | non vérifié | — |
| USDA/AMS OData v4 métadonnées | `https://agtransport.usda.gov/api/odata/v4/$metadata` | aucune | — | — | — |
| USDA/AMS OData v3 | `https://agtransport.usda.gov/OData.svc/deqi-uken` | aucune | — | `$top`+$format=json → **HTTP 400 « Unsupported system parameter »** **[FAIT]** | obsolète |
| USDA/AMS catalogue | `https://agtransport.usda.gov/api/catalog/v1?q=…&search_context=agtransport.usda.gov` | aucune | `limit`, `offset` | — | — |
| USACE lock status (documenté) | `https://ndc.ops.usace.army.mil/ords/lpms/json/lock_status_report?in_river_codes={CH\|ALL}` | aucune | — | — | **indisponible le 2026-10-31** |
| USACE lock status (hérité) | `https://ndc.ops.usace.army.mil/ords/lpms/lock_status_report_json?in_river_code={CH\|CH:AG}` | aucune | — | — | non documenté mais **fonctionnel** |
| USACE tonnage mensuel | `…/ords/lpms/json/monthly_tons_report?in_river_name={}&in_lock={}&in_month_year={MMYYYY}` | aucune | — | — | — |
| USACE file d'attente | `…/ords/lpms/xml/lock_queue/{rivière}{écluse}` (ex. `OH79`, `MI02`) | aucune | — | 30 j glissants | — |
| USACE arrêts | `…/ords/lpms/stall_stoppage_json?begin_date={DDMMYYYY}&end_date={DDMMYYYY}` | aucune | fenêtre de dates | — | — |
| USGS OGC | `https://api.waterdata.usgs.gov/ogcapi/v1/collections/{daily\|continuous\|…}/items` | **clé optionnelle** (inscription `/signup/`, limites de débit accrues) **[FAIT]** | **curseur** (`next` + `cursor=`) **[FAIT]** | `limit` ; plafond exact non vérifié | **cible de remplacement** |
| USGS métadonnées de séries | `…/collections/time-series-metadata/items` | idem | curseur | — | — |
| USGS stations | `…/collections/monitoring-locations/items` | idem | curseur | — | — |
| USGS WaterServices (hérité) | `https://waterservices.usgs.gov/nwis/{dv\|iv\|site\|peak}/` | aucune | `startDT`/`endDT` | — | **coupure 2027-02-22** ; dégradation 60 s/req. dès 2027-02-01 ; redirections 2027-01-27 (24 h) et 2027-02-15 (48 h) **[FAIT]** |

**Deux notes de lecture.**
- Les limites de débit exactes ne sont documentées nulle part en clair : **non vérifié**. Le seul chiffre
  sûr est le mode dégradé de 2027 : **60 secondes par requête** sur WaterServices.
- Le portail USDA/AMS accepte `$limit=50000` sur une table de 8 337 lignes ; rien n'indique un plafond
  global. Un connecteur prudent devrait **paginer par blocs** plutôt que de tout demander.

---

## 5. Qualité historique

### 5.1 Profondeur

| Source | Début observé | Fin | Statut |
|---|---|---|---|
| S1/S2/S3 taux | 2004-01-07 | 2026-10-27 | continu, 1 191 semaines, **aucun trou de date** |
| S4 grains par écluse | 2003-01-04 (3 écluses) / 2013-01-05 (4 écluses) | 2026-10-24 | 1 243 / 721 semaines |
| S5 comptage barges | 2005-08-27 | 2026-10-24 | ~1 096 semaines |
| S9 débit quotidien | 1892 (St. Paul), 1933 (Thebes), 1942 (Chester) | courant | 100+ ans |
| S8 état opérationnel | 30 jours glissants | courant | **pas d'historique** |

**[FAIT]** pour les bornes ; voir §5.3 pour les ruptures.

### 5.2 Les trois ruptures méthodologiques à connaître

1. **Jour de fin de semaine (S1/S2)** : mercredi jusqu'au 2006-09-20, **mardi** à partir du 2006-09-26.
   **[FAIT]** — dates observées et calcul du jour de la semaine.
2. **Profondeur par écluse (S4)** : quatre écluses apparaissent en 2013-01-05. **[FAIT]**.
3. **Taxonomie des types de barges (S5)** : `Loaded` nu disparaît après le 2005-10-22 au profit de
   `Grain, Loaded` / `Non-Grain, Loaded`. **[FAIT]**.

S'y ajoute une rupture **de granularité** dans S1/S2 : les taux passent de cotations entières (2004-2006) à
des moyennes à décimales fractionnaires à partir de 2007 (dénominateurs 3, 7, 16, 28 observés).
**[FAIT]** (valeurs) + **[INFÉRENCE]** (moyennage).

### 5.3 Les trous et les « zéros » — la règle du dossier

Trois objets distincts qu'un ingestion naïve confond :

| Valeur observée | Sens | Exemple vérifié |
|---|---|---|
| `rate = null` (S1) | **absence de cotation** (fermeture hivernale amont) | 774 lignes ; Twin Cities 426 ; janv.–mars 661 **[FAIT]** |
| `rate = 0` | **pas de cotation** : `0` est aussi absent du jeu S1 | le champ ne prend pas 0 **[FAIT]** |
| `tons = 0` (S4) | **zéro réel** : aucun grain de cette catégorie n'a transité | `tons` min = 0 **[FAIT]** |
| `downboundTons = null` (S8) | **absence**, pas zéro | cat. 70 sur OH/79 **[FAIT]** |

> **Règle du dossier, à écrire dans le connecteur : un `null` n'est jamais converti en `0`, et un `0` n'est
> jamais traité comme un `null`.** C'est la seule façon de ne pas fabriquer de l'hydrologie.

### 5.4 Révisions

- **S1/S4** : `rowsUpdatedAt` ≈ 4-5 jours après la dernière donnée ; l'historique est révisé en continu,
  sans journal de révisions exposé. **[FAIT]** pour la date ; **[NON VÉRIFIÉ]** pour l'historique des
  corrections.
- **S9** : `last_modified` par valeur, en UTC. Des valeurs de 1942 portant `last_modified = 2025-03-11`
  prouvent une **révision rétroactive de l'historique**. **[FAIT]**. `revision_note`, `revision_created`,
  `revision_modified` existent sur les stations. **[FAIT]**.
  → **Sans historique de révisions, une reconstitution « à l'instant t » est impossible** : on ne peut pas
  savoir ce que la source disait le jour de la décision. C'est une limite structurelle, pas un bug.

### 5.5 Fiabilité / interruptions

- **USACE `json/lock_status_report` : hors service le 2026-10-31** (3 essais). **[FAIT]**. C'est la seule
  panne observée sur l'ensemble du dossier.
- **USACE `lock_status_report_json` : disponible**, mais **non documenté** dans la liste des web services.
  **[FAIT]**.
- **USGS OGC** : aucune interruption observée sur ~20 appels.
- **USDA/AMS** : aucune interruption observée sur ~20 appels.
- **NOAA NWPS (`api.water.noaa.gov/nwps/v1/gauges`)** : **5 tentatives, 5 expirations de délai (timeout)**,
  y compris sans paramètre, avec `limit`, avec `state=IL`, avec `bbox`, et par identifiant de station
  (`USGS-07001000`, `USGS-07030000`, `USGS-07022000`, `USGS-07020500`). Un identifiant de station USGS
  renvoie `could not find unknown ID` — donc l'identifiant NOAA n'est **pas** le numéro USGS.
  **[FAIT]**. Ce qui **a** répondu : `?bbox=-90.5,38.5,-89.5,39.0&limit=1` → erreur de parsing
  (« unsupported message type: BoundingBox »), et `?state=IL&limit=1` → timeout. Conclusion : l'API est
  **vivante mais pas interrogeable ainsi**, et l'identifiant NOAA n'est pas le numéro de station USGS.

---

## 6. Conditions de conservation et de réutilisation

| Source | Attribution exigée | Restriction déclarée | Statut |
|---|---|---|---|
| S1/S2/S3 USDA/AMS | `USDA/AMS` | `useRestriction: Unrestricted` | **[FAIT]** ; `licenseName`/`licenseLink` **nuls** |
| S4/S5 USDA/AMS ← USACE | `U.S. Army Corps of Engineers` (+ lien `corpslocks.usace.army.mil`) | `Unrestricted` | **[FAIT]** |
| S6/S7 fichiers GTR (xlsx) | `USDA/AMS` et `U.S. Army Corps of Engineers` selon la table | non vérifié | **[NON VÉRIFIÉ]** |
| S8 USACE LPMS | mention USACE ; `notes` contient des consignes d'exploitation | non vérifié | **[NON VÉRIFIÉ]** |
| S9 USGS | mention USGS + lien vers la page de la station | non vérifié | **[NON VÉRIFIÉ]** |

**Points de vigilance.**
- L'attribution doit être **par source**, pas par dataset : S4 et S5 sont **éditées par USDA/AMS** mais
  **produites par l'USACE**. Citer « USDA/AMS » seul serait incomplet ; citer « USACE » seul serait faux
  pour le portail de diffusion.
- `licenseName` étant **nul** partout, il n'existe **pas** de licence arborescence à afficher. Ne pas
  inventer de « CC BY ». **[FAIT]**
- **[NON VÉRIFIÉ]** pour tous : le statut de réutilisation commerciale et l'obligation de mention pour les
  fichiers GTR (XLSX) et pour le contenu textuel de `notes` (USACE). **À vérifier avant toute publication
  ou redistribution.**

---

## 7. Sources retenues

**Retenues pour le premier slice :**

| Source | Pourquoi | Colonnes retenues |
|---|---|---|
| **S1** `deqi-uken` | Témoin économique sur toute la période, 7 zones,Complet, sans trou de date | `date`, `location`, `rate` (+ `week`/`month`/`year` **calculés**, à ne pas redériver) |
| **S2** `7spn-fbua` | Dollars par tonne **sans** avoir à rejouer la règle de barème (24/26 tronçons vérifiés) | `date`, `river_system_location`, `price_per_ton` |
| **S4** `n4pw-9ygw` | Volume réel par écluse et par catégorie, 2003→, source USACE | `date`, `lock`, `commodity`, `tons` |
| **S9** USGS `/daily` | Cause hydrologique, profondeur > 130 ans, `approval_status` et `last_modified` | `monitoring_location_id`, `parameter_code`, `statistic_id`, `time`, `value`, `unit_of_measure`, `approval_status`, `last_modified` |
| **S9** USGS `/time-series-metadata` | **Nécessaire** : c'est la seule source qui dit quelles séries existent, depuis quand, et avec quels seuils | `monitoring_location_id`, `parameter_code`, `statistic_id`, `begin`, `end`, `thresholds` |
| **S9** USGS `/monitoring-locations` | Identité, position, **nom**, surface de bassin, **datum**, fuseau | `id`, `monitoring_location_name`, `site_type_code`, `drainage_area`, `vertical_datum`, `time_zone_abbreviation` |

**Retenues pour la phase 2 (ou en complément, selon le calendrier) :**

- **S5** `w6ip-grsn` — nombre de barges : donne la densité de chargement, information absente des tonnes.
- **S8** USACE — pour la navigabilité *courante* : `notes` (seuils d'outdraft), `stall_stoppage_json`
  (`reasonCode` = `River current or Outdraft condition`), `gageUpperElevation`/`gageLowerElevation`
  (niveau des retenues), `weatherCode`, `iceCover`. **Fenêtre 30 jours seulement** : incompatible avec une
  étude historique longue ; utile pour un *nowcasting* ou une **démo d'état actuel**.
- **S3** `svms-9yya` / `uuhv-5etw` — pour mesurer l'**anticipation** du marché (ce que le futures regardait),
  à condition de masquer les ~33 % de semaines sans cote en amont.

---

## 8. Sources écartées

| Source | Motif d'écartement |
|---|---|
| **S10** USGS WaterServices (`waterservices.usgs.gov`) | **Écartée comme cible d'ingestion** : coupure **2027-02-22**, dégradation à 60 s/req dès 2027-02-01, redirections. Elle reste utile **jusqu'en novembre 2026** comme filet de sécurité et pour le recoupement de station (c'est par elle qu'on a attrapé les numéros de station erronés). À n'utiliser que temporairement. |
| **S6/S7** fichiers GTR (XLSX) | Même contenu que S1/S3/S4 mais **binaire**, sans API, sans métadonnées de ligne. Utiles pour **vérifier** un point, pas pour ingérer. `GTRTable10.xlsx` et `GTRFigure10Table9.xlsx` répondent **HTTP 200** en HEAD **[FAIT]**, mais leur schéma interne n'a pas été ouvert. |
| **NOAA** NWPS (`api.water.noaa.gov/nwps/v1`) | **Écartée pour l'instant** : 5 tentatives, 5 timeouts ; identifiant incompatible avec le numéro de station USGS ; l'API répond mais pas de manière exploitable. À reconsidérer (précipitations, crues) **si et seulement si** un identifiant NOAA↔USGS est établi. **Ne pasDepends de cette source dans le premier slice.** |
| **USACE `annual_usage_report`, `monthly_key_lock_report`** | L'un renvoie une page d'erreur Oracle APEX (`annual_usage_report?in_river=MI&in_lock=27&in_year=2024` → HTML d'erreur), l'autre **HTTP 404** (`monthly_key_lock_report?in_year=2024&in_month=3`). **[FAIT]** — non vérifiés plus finement : d'autres noms de paramètres peuvent exister. |
| **USACE `json/lock_status_report`** (seul) | Écarté **comme unique chemin** : hors service le 2026-10-31. Reste souhaitable en *second* endpoint. |

---

## 9. Risques et limitations

1. **Décalage de trois jours entre les deux familles USDA.** S1/S2 finissent le **mardi**, S4/S5 le
   **samedi**. Une jointure naïve « par semaine » mélange deux semaines différentes. **[FAIT]** — mitigation :
   indexer par `date` (fin de semaine) et **joindre sur la semaine ISO qui englobe**, ou décaler
   explicitement de 3 jours, en documentant le choix.
2. **`rate` est un moyennage, pas une cote.** Les fractions à dénominateurs 3/7/16/28 le montrent ; le
   `rate` de la semaine du 2026-10-27 n'a pas été coté le 2026-10-27. **[INFÉRENCE forte]** → le modèle
   doit traiter S1 comme un **indicateur de la semaine**, pas comme une observation datée.
3. **Absence ≠ zéro.** 774 `rate` nuls (9,3 %), concentrés sur l'amont en hiver ; `tons = 0` est un zéro
   réel ; `downboundTons = null` est une absence. Confondre les trois **fabrique** de l'hydrologie.
   **[FAIT]**.
4. **Profondeur hétérogène par écluse** dans S4 (2003 vs 2013). Comparer l'écluse MI27 en 2005 et
   l'écluse La Grange en 2005 est impossible — elle n'existe pas. **[FAIT]**.
5. **Taxonomie de `type` changeante** dans S5 au 2005-10-29. **[FAIT]**.
6. **Les numéros de station de mémoire sont faux** : 07030000 = Hatchie River (TN), 07010088 = River Des
   Peres (MO), 01010000 = St. John River (ME), 07005000 = Maline Creek (MO), 05592575 = Hickory Creek (IL).
   Seul `07001000` est bien le Mississippi à East St. Louis — et **il ne renvoie rien**. **[FAIT]**.
   → **Toujours résoudre les stations par `monitoring_location_name` + `bbox`, jamais par un numéro
   memorized.**
7. **Les paramètres disponibles varient d'une station à l'autre.** Chester et Thebes ont une hauteur
   quotidienne (`30800`) ; St. Paul n'a qu'un instantané (`00011`). Un modèle « hauteur quotidienne partout »
   ne fonctionnera pas. **[FAIT]**.
8. **`monitoring_location_id` seul ne renvoie rien** sur `/daily` : il faut ajouter `datetime` (ou
   `parameter_code`+`statistic_id`, ou passer par `bbox`). Un connecteur écrit trop vite obtient zéro ligne
   **sans erreur** — c'est le mode de panne silencieux le plus dangereux du dossier. **[FAIT]**.
9. **Les écarts de numérotation des quatre datasets USDA** : `deqi-uken` (taux), `7spn-fbua` (prix/tonne),
   `svms-9yya`/`uuhv-5etw` (forward), `n4pw-9ygw` (grains), `w6ip-grsn` (barges) — ids non-devinables,
   il faut le catalogue. **[FAIT]**.
10. **Deux tronçons de S2 (Desoto Landing, Letsworth) ne se réconcilient** avec aucun taux de la semaine
    observée. **[FAIT]** → ne pas supposer la règle de conversion exhaustive.
11. **`notes` (USACE) est du texte libre, parfois périmé** (MI01 : note datée du 26/02/2024 sur un relevé
    d'octobre 2026). **[FAIT]** → jamais de timestamp fiable issu de `notes`.
12. **Types mixtes dans le JSON USACE** (`"     2.5"` vs `687.70`) et `readingEntryDateTime` valant `":"`.
    **[FAIT]** → parsing robuste obligatoire.
13. **Fuseaux** : heures locales de station pour `time`, UTC pour `last_modified`, CDT/EDT chez l'USACE.
    **[FAIT]** → convertir en UTC à l'indexation, en tenant compte du passage CST/CDT.
14. **Datum vertical** : NAVD88 pour les stations modernes, **NGVD29** pour `USGS-07030000` et pour les
    séries fournies par l'USACE (`agency_code = USCE`). **[FAIT]** → ne jamais comparer des hauteurs de
    stations de datum différents sans conversion.
15. **Pas d'historique de révisions** chez USDA/AMS ; chez USGS, `last_modified` mais pas d'historique.
    **[FAIT]/[NON VÉRIFIÉ]** → **reconstitution à l'instant t impossible** ; à assumer explicitement.
16. **La Fenêtre de migration USGS se referme le 2026-11-16** pour les paquets `readNWIS`/`read_waterdata`.
    **[FAIT]**.
17. **USACE `json/lock_status_report` était hors service** le 2026-10-31. **[FAIT]** → bascule d'endpoint
    obligatoire, avec nouvelle tentative et journalisation.

---

## 10. Proposition de jeu de données minimal

### 10.1 Ce qu'on retient

| Source | Jeu | Colonnes | Période | Fréquence |
|---|---|---|---|---|
| S1 | `deqi-uken` | `date`, `location`, `rate` | 2004-01-07 → 2026-10-27 | hebdomadaire (mardi) |
| S2 | `7spn-fbua` | `date`, `river_system_location`, `price_per_ton` | 2004-01-07 → 2026-10-27 | hebdomadaire |
| S4 | `n4pw-9ygw` | `date`, `lock`, `commodity`, `tons` | 2003-01-04 → 2026-10-24 (2003-01-04 pour AK1/MS27/OH Olmsted) | hebdomadaire (samedi) |
| S9 | `daily` | `monitoring_location_id`, `parameter_code`, `statistic_id`, `time`, `value`, `unit_of_measure`, `approval_status`, `last_modified` | 1892 → courant | quotidienne |
| S9 | `time-series-metadata` | `monitoring_location_id`, `parameter_code`, `statistic_id`, `begin`, `end`, `thresholds` | — | au changement |
| S9 | `monitoring-locations` | `id`, `monitoring_location_name`, `site_type_code`, `drainage_area`, `vertical_datum`, `time_zone_abbreviation` | — | au changement |

**Stations USGS retenues** (toutes vérifiées comme portant des séries quotidiennes de débit `00060`/`00003`) :
- `USGS-05331000` MISSISSIPPI RIVER AT ST. PAUL, MN — **1892** → — Haut-Mississippi
- `USGS-07020500` Mississippi River at Chester, IL — **1942** → — Mississippi moyen
- `USGS-07022000` Mississippi River at Thebes, IL — **1933** → — Bas-Mississippi
- (+ `USGS-05420400` DAM 13 near Fulton, IL — à confirmer pour le débit quotidien ; non vérifié)

**Paramètres retenus** : `00060` (débit, `00003` Mean quotidien) en priorité ;
`00065` (hauteur) **seulement là où la série `30800` existe** — Chester et Thebes, pas St. Paul.
**`00065`/`00011` (instantané) en complément** si un pas de temps intrajournalier est requis.

**Fenêtre proposée pour le premier slice : 2004-01-07 → 2026-10-27** (durée commune de S1, S2, S4, S9).
Cette fenêtre a un avantage : elle **débute exactement au premier point de S1/S2**, donc aucune troncature
n'est nécessaire côté prix, et elle couvre 22 ans — assez pour voir au moins deux cycles de fermeture
hivernale.

### 10.2 Ce que cela permet de mesurer

1. **La saisonnalité du prix et sa réponse à l'hydrologie.** Sur 22 ans et 1 191 semaines, on peut estimer
   l'élasticité du taux (S1, en %) au débit et à la hauteur (S9) par zone, et comparer les 7 zones entre
   elles. C'est le cœur du premier slice.
2. **Le lien volume–prix.** La même semaine, `tons` par écluse (S4) et `rate` (S1) permettent de tester si
   le prix baisse quand le volume monte — la identifiable de la congestion.
3. **Les fenêtres de fermeture de l'amont.** Les semaines où `rate` est `null` pour `Twin Cities` et
   `Mid-Mississippi` (729 des 774 absences) **sont** les semaines de fermeture. On peut les recouper avec
   les semaines de débit minimal (S9) et avec l'absence de mouvement (S4). C'est un **test falsifiable** :
   si la fermeture était un artefact de publication, elle ne serait pas corrélée au débit.
4. **Les battements de cheville et les années extrêmes.** 2019 (crue record du Bassin du Middle
   Mississippi), 2011, 2008, 2022 (sécheresse), 2016 (crue de January 2016 à Thebes, pic 47,74 ft —
   `thresholds` de Thebes). Sur 22 ans, on a assez de extrêmes pour un conditionnement par régime.
5. **Le différentiel amont/aval.** `Twin Cities` (bénéficiaire des hauts débits) vs `Cairo-Memphis`
   (souvent zéro en fin d'été). Le différentiel de prix **est** un indicateur de tension sur le système.

### 10.3 Ce que cela ne permet PAS de mesurer

1. **Une causalité hydrologique fine sur le Haut-Mississippi.** Les taux d'amont manquent en hiver (fermeture)
   : là où le signal serait le plus fort, le prix n'existe pas. Le jeu permet d'étudier la **rupture**, pas
   la **réaction continue** de l'amont.
2. **Un effet causal de la fermeture sur les prix en aval.** Le problème est mécanique : `rate` est `null`
   pour l'amont précisément quand l'amont est fermé ; or c'est cette absence qui **fait monter** le prix en
   aval. On ne peut pas utiliser « l'amont a été fermé » comme variable explicative quand l'indicateur de
   prix amont est lui-même manquant par construction. **C'est le piège d'identification principal de ce
   dossier.** → l'identification devra reposer sur des **variations intra-amont** ou des **comparaisons
   entre semaines**, pas sur la présence/absence seule.
3. **Le tirant d'eau et les conditions de navigation en série longue.** `notes` (USACE) et
   `stall_stoppage_json` ne couvrent que **30 jours** ou la période courante. Les seuils d'outdraft
   historique **n'existent pas** dans une source accessible. Le jeu minimal **ne peut pas** quantifier la
   contrainte de tirant d'eau sur 22 ans.
4. **La congestion.** `totalPendingArrivals` et `average24HourDelay` (USACE) sont Limités à 30 jours ; S5
   (`barge_count`) est disponible historiquement mais **hors périmètre du jeu minimal**. Le jeu minimal ne
   mesure donc **pas** la congestion.
5. **Un point d'observation « au jour de la décision ».** `rate` est un moyennage sans date de cotation
   interne ; USGS donne `last_modified` mais pas d'historique de révisions. Aucune reconstitution
   « ce que le marché savait le jour J » n'est possible.
6. **Les débits « du moment » de la décision.** Le quotidien USGS est publié à J+1 ; le prix de la semaine
   est publié à J+4 environ ; les volumes de grains à J+5. Il y a donc un **décalage de publication
   structurel de 4-5 jours** entre l'hydrologie et le prix — invisible dans un modèle si l'on aligne
   naïvement sur `date`.
7. **La pluie, la météo, les réservoirs amont.** Aucune source retenue ne les apporte historiquement.
   `precipitation` et `weatherCode` (USACE) sont sur 30 jours. **Hors périmètre du premier slice.**
8. **Le Haut-Mississippi en amont de St. Paul.** Aucune station USGS du Haut-Mississippi au nord de
   St. Paul n'a été identifiée dans cette campagne. **Non vérifié.**
9. **La comparison inter-zones n'est pas homogène.** S2 a 26 tronçons, S1 7 zones ; le passage de l'un à
   l'autre n'est exact que pour 24 tronçons sur 26 testés.

### 10.4 Ordre d'exécution suggéré (à valider)

1. **Résoudre les stations par nom** (`monitoring-locations` + `bbox`), figer une liste de `monitoring_location_id`
   dans le code — **jamais** de numéro en dur.
2. **Télécharger `time-series-metadata`** d'abord : c'est la source de vérité sur ce qui existe
   (`begin`, `end`, `statistic_id`). Le `daily` doit être assemblé à partir de cette liste, pas deviné.
3. **Assembler le `daily`** par `bbox` + `datetime` + `parameter_code` + `statistic_id` (jamais
   `monitoring_location_id` seul), en format CSV, et **re-tester les paramètres à chaque station** (§9-7).
4. **Normaliser** : UTC partout, `null` ≠ `0`, valeurs en `Decimal`, dates de fin de semaine conservées
   telles quelles.
5. **Aligner les semaines USDA** (mardi vs samedi) **explicitement** et **documenter** la règle.
6. **Élaguer** : ne garder que `Approved` pour l'entraînement, garder les `Provisional` dans une table
   séparée pour la surveillance de révision.

---

## Ce qui n'a pas pu être vérifié

1. **Le fichier « Rate Data by Segment »** (barèmes par tronçon, annexé à la page S2) : non téléchargé
   (XLSX binaire). Deux tronçons de S2 résistent à la reconstitution. *Marche à suivre :* le télécharger
   et le lire ; il lèvera probablement la réserve.
2. **Les deux tronçons non réconciliés** — `Desoto Landing - Hurricane Point`, `Letsworth - Greenville` :
   barème inconnu. *Marche à suivre :* idem point 1.
3. **Le nombre exact de jours agrégés dans `rate`** et la règle de pondération : déduit des dénominateurs
   3/7/16/28, jamais documenté. *Marche à suivre :* demander à USDA/AMS.
4. **Le sens exact de `Other Grain`** dans S4, et l'existence d'un changement de catégorie dans le temps.
   *Marche à suivre :* documentation GTR / USACE.
5. **La présence et la granularité de trous réels** dans les séries USGS quotidiennes (le `data_gap_interval`
   décrit l'équipement, pas les données). *Marche à suivre :* comparer `count` attendu / observé par série.
6. **Les limites de débit** de l'API USGS sans clé, et celles du portail USDA/AMS. *Marche à suivre :*
   documentation de l'API ; le mécanisme de clé est documenté, pas les chiffres.
7. **Le statut de réutilisation commerciale** de tous les contenus (licences arborescence : `licenseName`
   est **nul** ; `useRestriction: Unrestricted` est la seule mention explicite). *Marche à suivre :* écrire
   à `agtransport@usda.gov` (contact publié) et au service de presse de l'USACE.
8. **Les conditions d'utilisation des fichiers GTR (XLSX)** et du texte de `notes` (USACE).
   *Marche à suivre :* idem point 7.
9. **L'identifiant NOAA ↔ numéro de station USGS** : l'API NOAA n'a pas répondu à une seule requête
   exploitable. *Marche à suivre :* gérer NOAA à part, avec sa propre table d'identifiants.
10. **Les paramètres quotidiens disponibles à `USGS-05420400` (Dam 13)**, vérifié comme station mais pas
    comme porteur de séries quotidiennes.
11. **Les stations du Haut-Mississippi au nord de St. Paul**, et les stations de l'Ohio en amont de
    Cincinnati (`03086000`) et au Cairo (`03614500`) comme porteurs de séries.
12. **Le schéma interne des XLSX GTR** (Table 9, Figure 10, Table 10) : répond 200 en HEAD, jamais ouvert.
13. **`USGS-07001000`** : pourquoi aucune donnée (déclassement ? reprise par un tiers ?). *Marche à suivre :*
    contacter USGS ; ne pas contourner.

## Ce qu'il faut vérifier avant d'écrire le moindre connecteur

**Bloquant — à lever avant de coder :**

1. **Confirmer par écrit la nature de `rate`** (moyennage sur combien de jours ?) auprès d'USDA/AMS.
   Sans cela, on ne sait pas de quoi on parle et on risque de modéliser un artefact de moyenne.
2. **Décider la règle d'alignement des semaines** (mardi ↔ samedi) et l'écrire dans le schéma.
3. **Décider si le premier slice travaille sur `deqi-uken` (7 zones, %) ou sur `7spn-fbua` (26 tronçons, $).**
   Recommandation : **`7spn-fbua` comme série de prix de référence** (déjà en dollars, 26 tronçons), avec
   `deqi-uken` en complément pour les zones où le tronçon n'est pas peuplé — **après** vérification du
   point 1 ci-dessus.
4. **Figer la liste des stations** par résolution nom + `bbox`, et **documenter** que `USGS-07001000` est
   écartée (aucune donnée).
5. **Décider le sort des `null` de `rate`** : les garder comme categorie explicite (« semaine non cotée »)
   plutôt que de les imputer. **Ne pas** les convertir en zéro.
6. **Décider l'usage de S8 dans le périmètre.** Si le slice vise l'historique, S8 n'y entre pas (30 jours).
   Si le slice vise une **démo d'état courant**, S8 est alors centrale — et il faut prévoir la bascule
   d'endpoint (`json/lock_status_report` → `lock_status_report_json`).

**Important — à vérifier pendant la construction :**

7. Que `daily` renvoie bien des lignes pour **chaque** couple (station, paramètre, statistic) retenu, en
   scolaire de contrôle (compter les semaines reçues contre `begin`/`end` de `time-series-metadata`).
8. Les `thresholds`naval de chaque station retenue (seuils de floodstage, limites opérationnelles) —
   à figer en table, car ils portent la sémantique de navigabilité.
9. La présence des séries `00065`/`30800` **et seulement elles** pour la hauteur quotidienne, station par
   station (§9-7).
10. Le comportement de `last_modified` sur les séries anciennes, pour dimensionner la surveillance des
    révisions USGS.

**Différé — mais à ne pas oublier :**

11. La bascule des paquets USGS `readNWIS`/`read_waterdata` **avant le 2026-11-16**.
12. La coupure de WaterServices **2027-02-22** : aucun code de production ne doit cibler
    `waterservices.usgs.gov` au-delà de cette date, et aucun ne doit en dépendre pour l'historique.
13. La reprise NOAA, si le slice devaittrait un jour les précipitations ou les crues.

---

*Toutes les URL citées ont été consultées le 31 octobre 2026. Les statuts HTTP et extraits
représentatifs sont given ci-dessus pour chaque famille d'appels. Les nombres « vus », « non nuls »,
« distincts » proviennent de requêtes de comptage directes sur les API, non d'estimations.*