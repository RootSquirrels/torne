# RESOURCE-003 — TORNE · LNG Terminal Intelligence

> **Le produit.** Une série quotidienne, par terminal et par jour de gaz, de l'état physique des
> terminaux d'importation de GNL, et une grandeur **dérivée** que personne ne publie : la **marge
> temporelle** — combien de jours le terminal peut encore fonctionner, au rythme de sortie observé,
> sans nouvelle réception.
>
> Ce n'est pas un dossier comparant des capteurs. C'est l'objet, son schéma, ses contrôles, son
> premier résultat, et la seule question qui reste ouverte.

---

## 1. Ce que le produit est

**L'unité d'observation** est le couple **terminal × jour de gaz**. Sept terminaux du système
gaziste espagnol : BARCELONA, CARTAGENA, HUELVA, BBG (Bilbao), SAGUNTO, REGANOSA, MUSEL.

**Ce qui est observé** — la source publie, chaque jour, par terminal : les volumes de GNL **déchargés**
des navires, ceux **régazéifiés** vers le réseau, ceux **chargés sur citernes** routières, ceux
**réexpédiés** sur un navire, les **existances en cuves** en début et fin de journée, le **taux de
remplissage**, et — c'est ce qui fait la valeur — les **deux dates** : celle du jour de gaz et celle
de la publication.

**Ce qui est reconstruit** : la **réserve opérationnelle** (le stock au-dessus du minimum technique)
puis la **marge** (cette réserve divisée par le débit de sortie brut observé sur une fenêtre
traileresse), puis l'**indicateur de tension** (la marge passe-t-elle sous trois jours ?).

> **Pourquoi ce n'est pas une copie de la source.** L'exploitant publie l'**état** ; il ne publie ni
> la réserve, ni la marge, ni la tension. Il publie l'**autonomie équivalente** du *système*
> entier — et c'est précisément là que l'information se perd : un système peut afficher vingt-trois
> jours d'autonomie alors qu'un de ses terminaux en a moins de deux.

---

## 2. Ce que la série contient

`data/resource-003/terminal_quotidien.csv` — **210 lignes** (7 terminaux × 30 jours de juin 2026) :

| Champ | Unité | Nature |
|---|---|---|
| `terminal`, `jour_gaz` | — | l'observation |
| `date_publication` | — | **quand on a pu le savoir** |
| `entrees_m3`, `regas_m3`, `sorties_citernes_m3`, `reexport_m3` | m³ GNL liquide | observé |
| `stock_final_m3`, `stock_final_t` | m³, t | observé |
| `remplissage` | fraction | observé |
| `reserve_m3` | m³ | **dérivé** |
| `marge_jours`, `marge_bas`, `marge_haut` | jours | **dérivé**, avec son intervalle |
| `tension` | 0/1 | **dérivé** |

---

## 3. Les contrôles, tous passés

| Contrôle | Résultat |
|---|---|
| Rapports lus / demandés | **30 / 30**, aucun refusé |
| Écart maximal entre le `Total Plantas` et la somme des sept terminaux | **9,7 × 10⁻⁴** (tolérance 10⁻³) |
| Facteur de conversion, mesuré sur le document | **146,98 m³ liquides par GWh** (146,979 – 146,985 sur 30 jours × 7 terminaux), soit **67,02 t de GNL par GWh** |
| Réconciliation avec le bulletin mensuel | **< 0,6 %** (Barcelone 1 560 GWh reconstruits contre 1 559 publiés ; Bilbao 3 281 contre 3 299 ; Carthagène 1 859 contre 1 882 ; Huelva 2 195 contre 2 173 ; Sagonte 1 061 contre 1 065 ; Musel 0 contre 0) |
| Délai de publication | **25,2 à 73,5 heures** après le jour de gaz |

> **[FAIT] Le facteur 1,75 qui bloquait la confrontation était notre erreur.** Nous avions divisé un
> pouvoir calorifique **par gaz à 0 °C** (13,99 MJ/m³) par une masse volumique **de GNL liquide**
> (0,456 t/m³). La source publie la même grandeur en GWh **et** en m³ liquides : le facteur se
> **mesure**, il ne se suppose pas. **Aucun échange technique n'est nécessaire pour la conversion.**

> **[FAIT] Le stock n'a pas besoin d'être estimé : il est observé.** La question posée — « peut-on
> estimer le stock ? » — est **close positivement**. Ce qui reste à reconstruire, c'est la marge.

---

## 4. Le premier résultat

**Juin 2026, tension sur le seuil de trois jours de couverture :**

| Terminal | Marge médiane | Marge minimale | Jours en tension |
|---|---|---|---|
| **MUSEL** | **4,6 j** | **0,0 j** | **13 / 30** |
| REGANOSA | 17,0 j | 5,9 j | 0 / 30 |
| BBG | 25,2 j | 15,2 j | 0 / 30 |
| HUELVA | 30,5 j | 18,4 j | 0 / 30 |
| SAGUNTO | 34,1 j | 21,2 j | 0 / 30 |
| CARTAGENA | 36,9 j | 27,0 j | 0 / 30 |
| BARCELONA | 43,6 j | 33,1 j | 0 / 30 |

**La lecture.** Le 1ᵉʳ juin 2026, l'exploitant publie une **autonomie équivalente de 23,14 jours**
pour l'ensemble du système. Le même jour, **Musel n'a que 4,6 jours de couverture** et en aura zéro
à plusieurs reprises dans le mois. La tension **est** dans le système ; elle n'est pas dans l'agrégat.

**La robustesse.** Le résultat ne vient pas du paramètre : avec un minimum technique de **0 %** — un
terminal qui pourrait vider ses cuves — Musel reste en tension **9 jours sur 30** ; avec 15 %, ce
sont 15 jours. Les six autres terminaux ne franchissent le seuil **à aucun** réglage. Le classement
est **structurel**, pas paramétrique.

> **Ce que c'est, précisément.** Ce n'est pas une alerte : l'exploitant sait qu'un de ses terminaux
> est petit. C'est une **mesure datée, par terminal, du nombre de jours de couverture**, avec son
> intervalle et ses deux dates, là où la source ne publie qu'un chiffre système. C'est de l'information
> **nouvelle**, et elle est **reproductible**.

---

## 5. Le verdict

> ### Knowledge Product — le premier, avec une réserve.
>
> Le produit existe, il est rejouable, il est persisté, ses contrôles passent, et il produit une
> grandeur que personne ne publie. **La réserve** : la réserve opérationnelle dépend du **minimum
> technique des cuves**, qui est un paramètre — et la seule chose qu'il reste à demander à
> l'exploitant.
>
> Ce qui est **clos** : le stock est observé, la conversion est mesurée, la réconciliation avec la
> référence mensuelle est faite, et la question du facteur 1,75 est résolue.

**Ce qui reste à demander à l'exploitant** — une seule question :

> *Quel est le volume minimal de GNL qu'un terminal doit conserver dans ses cuves pour rester
> exploitable, par terminal ?*

Et, en passant, le **niveau de stock à partir duquel le terminal ne peut plus décharger** — c'est la
seule donnée qui manque pour que la réserve ne soit plus un paramètre mais une mesure.

**Ce que la mission a appris par ailleurs, et qui vaut d'être noté :**

- **Le point d'accès de la source a changé** pendant la mission : l'URL est passée de
  `/content/dam/enagas/…` à `/content/enagas/…`, et l'ancienne a cessé de répondre en quelques
  heures. Le site sert désormais un **JSON indexé par nom de terminal** — ce qui **supprime** le
  risque d'alignement de colonnes que la version tableur portait.
- **La machine n'avait aucun magasin CA** pour OpenSSL : la vérification TLS du socle échouait sur
  *toute* source HTTPS. Le remède (`SSL_CERT_FILE` pointant sur `certifi`) **conserve** la
  vérification complète. C'est un point de portabilité, pas une contournement.
- La **chaîne de l'URL** porte deux fois le paramètre `date` si l'adaptateur met le jour dans l'URL
  *et* dans les paramètres : le socle encode lui-même, et le doublon fait échouer la requête.

---

## 6. Reproduction

```bash
uv run python experiments/resource_003_lng_terminal_intelligence.py 2026-06 data/resource-003
uv run python experiments/resource_003_sensibilite.py
uv run pytest tests/test_supply_lng.py -q
```

| Fichier | Rôle |
|---|---|
| `src/torne/supply/lng.py` | le domaine : l'état quotidien du terminal, et le modèle de marge |
| `src/torne/supply/enagas.py` | le décodeur : le rapport JSON devient des états de terminal |
| `src/torne/acquisition/adapters/enagas.py` | l'adaptateur : la question posée, et la conformité vérifiée |
| `tests/test_supply_lng.py` | 13 tests, sans réseau |
| `experiments/resource_003_lng_terminal_intelligence.py` | la construction de la série |
| `experiments/resource_003_sensibilite.py` | la sensibilité de l'indicateur à ses paramètres |
| `data/resource-003/**` | la série et les preuves brutes (dossier ignoré par git) |

**État.** `ruff` propre ; **961 tests verts** ; aucun contrat partagé modifié, hormis
`src/torne/acquisition/adapters/__init__.py`, où l'adaptateur s'enregistre au registre des sources.
