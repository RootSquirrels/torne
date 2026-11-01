# RESOURCE-002 — Correction de la faisabilité

> **Cette note corrige `docs/RESOURCE-002.md`.** Elle est écrite à la suite d'une revue physique
> qui a deux graves raisons de suspendingre le GO : une erreur de calcul de ma part, et un
> renversement du sens de la méthode elle-même.
>
> **Deux constats d'ouverture, avant tout le reste.**
>
> 1. **J'ai publié une erreur de calcul.** Le dossier annonçait **3,5 tonnes de GNL par centimètre
>    de tirant d'eau** et **0,001 %** d'incertitude. La valeur correcte est **111,3 t/cm**, et
>    l'incertitude **1,4 %**. L'erreur venait d'une division par le tirant d'eau dans la formule du
>    déplacement, qui n'a rien à faire là. Le dossier d'origine est corrigé ; cette note en tire les
>    conséquences.
> 2. **La méthode ne peut pas être ce qu'elle était.** Le tirant d'eau n'est pas une grandeur que
>    Sentinel-1 sait mesurer, et, pour une part importante de la flotte, **le tirant d'eau ne
>    change pas pendant le déchargement** parce que le navire le compense par le ballast. La
>    cargaison, elle, **est déjà mesurée** — trois fois, par trois parties. Reconstruire une
>    grandeur déjà mesurée n'est pas une contribution.
>
> **Règle de preuve.** **[FAIT]** (observé), **[INFÉRENCE]** (lecture plausible), **[NON VÉRIFIÉ]**.

---

## 1. La conversion hydrostatique, refaite

**[FAIT]** Le déplacement d'un navire est le poids d'eau de mer qu'il déplace :

```
déplacement (t) = ρ_sw · Cb · Lpp · B · T
```

Donc, à dimensions données, la sensibilité est :

```
d(déplacement)/dT = ρ_sw · Cb · Lpp · B        [tonnes par mètre]
TPC = 0,01 · ρ_sw · Cb · Lpp · B                [tonnes par centimètre]
```

**La division par `T` n'a rien à faire là.** C'est de là que venait l'erreur.

**[FAIT] Cas de référence** (méthanier 177 000 m³, Lpp 280 m, largeur 52 m, tirant d'eau 11,7 m,
déplacement plein 130 233 t, eau de mer à 1,025 t/m³) :

| Grandeur | Valeur |
|---|---|
| volume déplacé | 127 057 m³ |
| coefficient de bloc **déduit** | **0,746** |
| **TPC** | **111,3 t/cm** (283 t/pouce) |
| contrôle d'ordre de grandeur (déplacement / (T × 100)) | 111,3 t/cm — **concordant à 0,01 %** |

**[FAIT] Le budget d'erreur corrigé** (cargaison de 80 000 t, soit ≈ 682 GWh) :

| Écart de tirant d'eau | Masse | Sur une cargaison de 80 000 t |
|---|---|---|
| ±0,10 m | ±1 110 t | **1,39 %** |
| ±0,20 m | ±2 220 t | 2,78 % |
| ±0,30 m | ±3 330 t | **4,17 %** |
| ±0,50 m | ±5 550 t | 6,94 % |

**[FAIT] Conséquence sur les seuils de la mission.** Pour tenir **1 %** de cargaison, il faut un
écart de tirant d'eau mesuré à **±7,2 cm** — pas ±0,3 m. Et ±0,3 m ne donne pas 0,001 % : il
donne **4,17 %**.

**[FAIT] La conversion énergie ↔ masse, à la base du bulletin** (PC supérieur à 0 °C, volume à
0 °C / 1,01325 bar) :

```
1 GWh = 3600 MJ  →  3600 / 13,99 = 257,3 m³ de GNL  →  × 0,456 t/m³  =  117,3 t
```

Soit **1 GWh ≈ 117,3 kt de GNL**. Contrôle : l'Espagne a déchargé **16 651 GWh** en avril 2026,
soit **1,95 Mt** — l'ordre de grandeur attendu pour l'Espagne. ✓

> **[INFÉRENCE] Trois pièges que la formule ne couvre pas, et que le dossier doit porter.**
> 1. **Déplacement n'est pas cargaison** : la masse l'est, mais le *volume* de LNG déchargé n'est
>    pas la variation de volume de coque — le GNL (450 kg/m³) n'a pas la densité de l'eau de mer.
> 2. **Le tirant d'eau ne bouge pas toujours** : voir §2.
> 3. **La masse n'est pas la cargaison** : ballast, combustibles, eau douce, stores et assiette
>    évoluent indépendamment du cargo. La conversion exige les **tables hydrostatiques du navire**
>    (Cb, Lpp, B, tirants de référence), la correction d'assiette, et l'état des autres
>    compartiments.

---

## 2. Capacité capteur → grandeur observable

C'est la matrice que la mission demandait, et elle est **négative pour la méthode envisagée**.

| Grandeur observable | Sentinel-1 IW-GRDH (20 m) | AIS, message type 5 | CTMS / custode de l'exploitant | Suivi quotidien Enagás |
|---|---|---|---|---|
| **présence** du navire | oui — F1 ≈ 0,97 | oui | oui | — |
| **identité** (OMI) | non | oui | oui | non |
| **longueur** | oui, **±15–17 %** (30–40 m) | oui | oui | — |
| **largeur** | **mauvaise** — ±35–130 % (10–50 m) | oui | oui | — |
| **tirant d'eau absolu** | **non démontré** | **déclaré**, statique, 1/10 m, rediffusé toutes les 6 min | oui (mesuré) | indirect (existences) |
| **variation** de tirant d'eau | **non** | **non** | oui | **oui** (m³ par jour) |
| **masse de cargaison** | **non** | **non** | **oui** | oui (m³) |

**[FAIT] Sentinel-1 ne mesure pas le tirant d'eau.** La résolution des produits IW-GRDH est de
**20 m** ; les évaluations publiées donnent une erreur de longueur de l'ordre de **15 % (30 m)** et
une erreur de largeur de **35 % (11 m)**, la largeur restant « un problème non résolu » à cette
résolution. Le tirant d'eau est une dimension **verticale** : rien dans la signature radar d'un
navire à 20 m ne la donne. Exiger ±0,3 m d'un capteur de 20 m est **trois ordres de grandeur**
au-delà de ce qu'il sait faire.

**[FAIT] Le tirant d'eau AIS est un maximum déclaré, pas une mesure.** Le champ « Maximum present
static draught » (message type 5) tient sur **8 bits, en 1/10 m**, est rediffusé **toutes les
6 minutes**, et sa valeur par défaut est « non disponible ». Les notes NOAA rappellent que les
saisies modernes reportent typiquement le **tirant d'eau statique maximal** — c'est-à-dire ce que
l'armateur déclare pour l'entrée au port, **pas** le tirant d'eau instantané de l'instant. Il ne
peut donc pas servir à mesurer une variation pendant un déchargement.

**[FAIT] Et surtout : pour une part de la flotte, le tirant d'eau ne varie pas.** La pratique
documentée des méthaniers est de **ballaster simultanément au déchargement**, pour conserver un
tirant d'eau constant et éviter les contraintes sur les bras de quai, les contraintes de tirant
d'eau, d'assiette, de contrainte de coque et de stabilité. Le signal que la méthode cherche est
donc **annulé par construction** pour ces navires — et le stripping se fait par **assiette sur
l'arrière**, ce qui fausse la lecture du tirant d'eau.

> **[INFÉRENCE] La cargaison n'a donc pas besoin d'être reconstruite : elle est déjà mesurée.**
> Le **CTMS** du navire (custody transfer measurement system) mesure le volume cargo, corrigé de
> l'assiette et de la gîte, exprimé en m³ à −160 °C ; la **custode de transfert** au terminal
> reprend ces valeurs ; le **suivi quotidien de l'exploitant** les publie en m³ **par jour et par
> terminal**. Trois mesures indépendantes du même objet, dont deux déjà publiques. Reconstruire
> la cargaison par télédétection n'ajouterait rien — et la « validation physique » se ferait
> contre un nombre que l'exploitant publie le jour même.

---

## 3. La granularité réelle de la référence

**[FAIT] Il existe une référence *quotidienne*, et elle est bien plus fine que le bulletin.**

Le *Seguimiento Diario del Sistema* d'Enagás est téléchargeable **pour n'importe quelle date** (URL
datée), et sa feuille « Resumen » donne, **par jour de gaz et par terminal** :

| Ligne | Unité | Grandeur |
|---|---|---|
| **Descargas GNL** | **m³ GNL** | le **cargaison déchargée** |
| Cargas GNL | m³ GNL | le GNL réexpédié |
| Regasificación | GWh/jour **et m³ GNL** | le débit sortant |
| Carga Cisternas | GWh/jour | le tirage citerne |
| Exist. Tanques iniciales / finales | GWh/jour **et m³ GNL** | les existances en cuves |
| **% llenado** | fraction | le **remplissage des cuves** |

Sept terminals y figurent : BARCELONA, CARTAGENA, HUELVA, **BBG** (Bilbao), SAGUNTO, REGANOSA,
MUSEL.

**[FAIT] La granularité mesurée — juin 2026, 30 rapports quotidiens téléchargés :**

- **15 jours** sur 30 portent au moins un déchargement ;
- **13 jours sur 30 portent un déchargement à terminal unique** — le cas « un seul navire » est
  donc **identifiable** ;
- **17 déchargements** au total, de **4 357 m³** à **164 196 m³**, médiane **99 734 m³** ;
- **6** déchargements seulement tombent dans la fourchette 40 000–90 000 m³ d'un seul méthanier ;
  les autres (99 000–164 000 m³) correspondent à un **méthanier plein** (≈ 157 000 m³ pour un
  174 000 m³ à 90 %), et les petits volumes sont des **fins de déchargement** étalés sur plusieurs
  jours.

> **[FAIT] Deux conséquences qui changent la méthode de validation.**
> 1. **Un navire ne décharge pas en un jour.** Les volumes se répartissent sur plusieurs jours de
>    gaz, au rythme de déchargement. Une confrontation « un jour = un navire » est donc fausse, et
>    l'attribution d'un volume à un navire exige de connaître la cadence de déchargement.
> 2. **Les deux formes de la référence ne se réconcilient pas.** La référence quotidienne (m³) et la
>    référence mensuelle (GWh) diffèrent d'un **facteur constant de 1,73 à 1,77** — identique sur
>    les cinq terminaux. Ce n'est donc pas une erreur de données : c'est une **différence de
>    convention** (base de volume, base de PCS, ou périmètre), et elle **doit être tranchée par un
>    document de référence** avant toute confrontation. C'est exactement le point que la revue
>    signalait.

**[FAIT] La base maritime de PortWatch est accessible après tout — via HDX.** Le collecteur
OCHA-DAP republie les données par pays sur le Humanitarian Data Exchange, et **l'Espagne y est** :

| | |
|---|---|
| ressource | `spain-daily-port-activity-data-and-shipment-estimates.csv` |
| taille | **13 102 009 octets** |
| lignes | **108 414** |
| période | **2019-01-01 → 2026-10-23** |
| mise à jour | **hebdomadaire** (dernière : 2026-10-28) |
| ports | **38**, dont **Barcelona, Cartagena, Bilbao, Huelva, Sagunto** |
| unités | les volumes `import_*`/`export_*` sont **en tonnes métriques** (selon la fiche HDX) |

**[FAIT] Mais ses volumes ne sont pas un substitut de la cargaison.** Confrontation de juin 2026 :

| Terminal | PortWatch pétrole importé (t) | Enagás quotidien (t) | Enagás mensuel (t) | PW / Enagás |
|---|---|---|---|---|
| Barcelona | 848 854 | 104 566 | 182 935 | **7,7×** |
| Cartagena | 1 082 047 | 124 640 | 220 836 | **8,7×** |
| Bilbao (BBG) | 751 116 | 219 913 | 387 108 | **3,4×** |
| Huelva | 281 903 | 147 125 | 254 982 | **1,9×** |
| Sagunto | 104 669 | 71 087 | 124 968 | **1,5×** |

> **[FAIT]** L'estimation PortWatch du pétrole importé **surestime le GNL réellement déchargé d'un
> facteur 1,5 à 8,7**, et l'écart n'est pas constant. C'est attendu : l'estimation du FMI couvre
> **tous** les pétroliers (brut, produits, chimiques, GPL) et dérive de la **capacité** du navire,
> non de sa charge réelle. **Conclusion : PortWatch est une base d'ACTIVITÉ portuaire** — y a-t-il
> eu un mouvement, de quel type, quel jour — **et pas une mesure de cargaison.** C'est
> exactement le rôle qu'on peut lui donner, et il est utile ; mais il ne valide rien sur le volume.

---

## 4. AIS : le champ, la couverture, et la question du devis

**[FAIT] Le champ.** « Maximum present static draught », message type 5, 8 bits, **1/10 m**,
255 = ≥ 25,5 m, 0 = non disponible ; rediffusé **toutes les 6 minutes**, sur demande, ou quand la
donnée change ; et il porte le **tirant d'eau statique maximal**, c'est-à-dire une **déclaration**.

**[FAIT] La couverture.** NOAA MarineCadastre distribue **gratuitement** des données AIS : les
**attributs de navires** (OMI, dimensions, tirant d'eau) et les **traces de navires**. Deux
réserves, tirées de sa propre FAQ :

- les données sont **reconstituées à partir de requêtes historiques trimestrielles** auprès de la
  Garde côtière américaine, **échantillonnées et filtrées** — ce n'est pas le flux brut ;
- **le retard total entre la collecte et la livraison est d'environ 145 à 165 jours**, et les
  données s'ajoutent tous les 90 jours.

**[FAIT]** Le portail `www.marinacadastre.gov` **ne résout pas en DNS** depuis ce poste ; seule la
FAQ (`coast.noaa.gov/data/marinecadastre/ais/faq.pdf`) a répondu, et la page de données n'a pas
été atteinte. C'est une limite d'accès à compter, pas une absence de la source.

**[NON VÉRIFIÉ] Je ne peux pas acheter, et je ne l'ai pas fait.** Je n'ai pas demandé de devis :
cela suppose un contact commercial et un engagement financier, qui vous appartiennent. Ce que je
peux faire, et que je fais dans ce dossier, c'est **le cahier des charges** :

> **Ce qu'il faudrait demander** — un devis **ponctuel** (pas d'abonnement annuel) pour :
> 1 à 2 terminaux LNG d'Espagne, **60 à 90 jours** d'historique, messages **bruts**, horodatés ;
> **numéro OMI, MMSI, nom, type et dimensions** de chaque navire ; **historique du champ tirant
> d'eau** (valeurs, dates, horodatages, et **durée de validité déclarée** de chaque valeur) ;
> métadonnées de couverture (satellitaire/terrestre, taux de réception, lacunes) ; et les **droits
> d'usage**.

**L'évaluation de couverture** ne peut pas se faire sans un échantillon : il faut mesurer, sur
l'échantillon, la **proportion de navires dont le tirant d'eau est exploitable** (valeur présente,
non périmée, et **réellement mise à jour** pendant le séjour à quai) — et il ne faut **pas** traiter
le tirant d'eau AIS comme une vérité terrain : c'est une déclaration, et le FMI lui-même ne
s'appuie pas dessus pour ses volumes.

---

## 5. Le budget d'erreur physique, révisé

| Source d'incertitude | Amplitude | Effet sur la cargaison (80 000 t) |
|---|---|---|
| Mesure du tirant d'eau (SAR 20 m) | **non mesurable** | **indéterminé** |
| Déclaration AIS (1/10 m, statique) | ±0,05 m sur la différence | ±560 t, soit 0,7 % — **mais le champ ne porte pas la variation** |
| Compensation par le ballast (BDL) | **signal annulé** | **indéterminé** pour ces navires |
| Ballast, combustibles, eau douce, stores | non quantifié sans l'état du navire | non couvert |
| Assiette | non couvert | non couvert |
| Cb, Lpp, B réels (tables hydrostatiques) | non documentés dans la source | non couvert |
| Conversion énergie ↔ masse (Enagás) | **facteur 1,75 non réconcilié** entre les deux formes | **facteur 1,75 sur toute confrontation** |
| PortWatch comme référence | surestimation × 1,5 à 8,7 | inutilisable pour la cargaison |

> **[FAIT] Le budget d'erreur n'est pas dominated par la mesure : il est dominé par trois
> inconnues structurelles** — la compensation par le ballast, l'état des autres compartiments, et
> la convention de conversion de l'exploitant. La précision de la méthode (0,7 % sur la
> conversion) n'a aucune importance tant que ces trois-là ne sont pas traitées.

---

## 6. Décision

> ### NO-GO sur la reconstruction de la cargaison par tirant d'eau.
>
> Trois motifs **indépendants**, dont chacun suffirait :
>
> 1. **Capteur.** Sentinel-1 à 20 m ne mesure pas le tirant d'eau ; il détecte les navires et
>    estime leur longueur à ±15 %, mal leur largeur. ±0,3 m est hors de portée de trois ordres de
>    grandeur.
> 2. **Physique.** Pour les méthaniers qui ballastent simultanément, le tirant d'eau est
>    **constant par construction** pendant le déchargement : le signal recherché n'existe pas. Et
>    quand il existe, il faut les tables hydrostatiques du navire, la correction d'assiette et
>    l'état du ballast.
> 3. **Cible.** La cargaison est **déjà mesurée** — par le CTMS du navire, par la custode du
>    terminal, et par le suivi quotidien de l'exploitant, **en m³, par jour, par terminal**.
>    Reconstruire une grandeur déjà mesurée, et la valider contre le numéro que l'opérateur
>    publie le jour même, n'est pas une contribution.
>
> **Ce qui reste vrai, et qui a de la valeur.**
>
> - **La piste LNG reste la première candidate** — mais pour une **autre grandeur**. La question
>   n'est plus « combien de GNL a été déchargé », c'est **quelle grandeur, dans cette chaîne, n'est
>   mesurée par personne**. Le suivi quotidien ouvre précisément ce terrain : le **% de
>   remplissage** par terminal et par jour, les **existances**, la **répartition des flux** vers
>   les zones, et le **calage temporel** de l'événement physique par rapport à la publication des
>   agrégats.
> - **La référence est de qualité** et elle est **quotidienne**. C'est un acquis de la mission :
>   avant, on n'avait qu'un bulletin mensuel ; on a maintenant un relevé journalier, par terminal,
>   en m³, avec les existances et le remplissage — et **une anomalie à trancher** (le facteur 1,75
>   entre les deux formes de la référence).
> - **La base PortWatch est ouverte et extractible** (HDX, hebdomadaire, 2019→présent, 38 ports
>   espagnols dont les six terminaux), et son bon usage est établi : **l'activité portuaire**, pas
>   le volume.
>
> **Ce que je n'ai pas fait, et qui reste à faire :** je n'ai pas demandé de devis AIS, et je ne
> peux pas. Le cahier des charges est au §4.

---

## 7. La suite, dans cet ordre

1. **Trancher le facteur 1,75** avec un document de référence de l'exploitant (conventions de
   volume et de PCS). Sans cela, aucune confrontation chiffrée n'est légitime. *C'est le premier
   geste, et il ne coûte qu'un courriel.*
2. **Redéfinir la grandeur visée** sur la base de ce que le suivi quotidien montre et de ce que
   personne ne publie : le remplissage des cuves, la répartition des flux, le décalage temporel.
3. **Ne pas extraire les fichiers GEM** tant que LNG n'est pas Refermé — c'est la piste de repli,
   et l'arbitrage a demandé qu'on attende.
4. **Reprendre le filtre à six questions** sur la nouvelle grandeur : quelle information manque,
   pourquoi elle est mal connue, qui est concerné, quelle variable économique, quelle donnée
   nouvelle, et **comment on vérifie** — en gardant les **deux validations séparées**.

---

## 8. Les produits

| Fichier | Rôle |
|---|---|
| `experiments/resource_002_hydrostatique.py` | la conversion hydrostatique correcte, son contrôle, et le budget d'erreur |
| `experiments/resource_002_enagas_quotidien.py` | le suivi quotidien, lu avec la seule bibliothèque standard |
| `experiments/resource_002_enagas_dechargements.py` | le comptage des déchargements et des journées à terminal unique |
| `experiments/resource_002_portwatch_hdx.py` | la ressource HDX, téléchargée et inspectée |
| `experiments/resource_002_confrontation.py` | la confrontation PortWatch / Enagás, et le facteur 1,75 |
| `data/resource-002/**` | les preuves : 30 rapports quotidiens, le CSV HDX, les bulletins mensuels |

**État.** `ruff` propre. **Aucun contrat partagé n'a été modifié** ; aucune donnée n'a été extraite
vers un fichier suivi ; **aucune valeur du `.env` n'apparaît dans le dépôt**.
