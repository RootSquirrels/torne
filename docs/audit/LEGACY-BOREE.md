# Audit d'archéologie logicielle : BOREE (plateforme legacy) vers TORNE

**Date :** 31 octobre 2026
**Agent :** D - Legacy BOREE Archaeology
**Depot audite :** `C:\Users\Romain\Documents\GitHub\boree\` - **lecture seule stricte, aucune modification**
**Commit audite :** `4b6d130ebc9068fbd7cba0de8611737a6d9cfc18` (branche `main`, 206 commits, auteur Romain BAILLEUL, 2026-10-31)
**Depot cible :** `C:\Users\Romain\Documents\GitHub\torne\`
**Methode :** revue statique du code réel. **La suite de tests n'a pas pu être exécutée** (voir section 8).

> Ce rapport est une source d'évidence pour la consolidation par l'agent principal. Il ne décide rien seul : les
> décisions `REUSE / ADAPT / REIMPLEMENT / REJECT` du tableau final suivent le format impose par
> `docs/REUSE_AUDIT.md`, section 1.

---

## 0. Perimetre effectivement lu

### 0.1 Ce que j'ai lu

| Domaine | Fichiers |
|---|---|
| Protocole | `PROTOCOLE.md` (205 lignes, lu en entier), `docs/adr/0002-un-seul-point-de-vue.md`, `docs/adr/0003-scelles.md` |
| Manifeste | `pyproject.toml`, `deploy/homelab/boree.env.exemple` (présence), `uv.lock` (présence) |
| Noyau temporel | `src/boree/temps.py` (95 premières lignes), `src/boree/config.py` (106 lignes) |
| Lac | `src/boree/lac/__init__.py`, `lac/catalogue.py` (95 l.), `lac/connu.py` (90 l.), `lac/parquet.py` (151 l., entier) |
| Archive | `src/boree/archive.py`, `src/boree/exploitation/garage.py` (110 l.) |
| Scelles / accès direct | `src/boree/scelles.py`, `src/boree/direct.py` (100 l.) |
| Ingestion | `src/boree/ingest/sources.py`, `ingest/entsoe_api.py` (95 l.), `ingest/ecmwf_direct.py` (90 l.) |
| Registre | `src/boree/registre/contrat.py`, `registre/chaine.py` (204 l., entier), `registre/verifier.py` (70 l., entier), `registre/*.toml` (boree-h2/h3/h4) |
| Physique | `src/boree/physique/__init__.py`, `physique/empilement.py` (269 l., entier), `physique/jumeau.py`, `physique/contexte.py` (70 l.) |
| Transformations | `src/boree/tables/horizon.py` (110 l.) |
| Sortie | `src/boree/flux.py` (entête), `docs/flux/` (inventaire : 10 JSON Schemas + README) |
| Exploitation | `src/boree/exploitation/lancement.py` (60 l.), `doctor.py` (91 l., entier), `cli.py` (253 l., entier) |
| Tests | `tests/fabrique.py` (121 l., entier), `tests/test_lac.py`, inventaire des 48 fichiers `test_*.py` (457 fonctions de test) |
| Docs | `docs/SYSTEME.md`, `docs/ARCHITECTURE.md`, `docs/LAC.md`, `docs/resultats/README.md`, `docs/resultats/RESULTAT_jumeau.md`, `docs/AUDIT_2026-10-31.md` (14 l.), inventaire de `docs/` |
| Référence | `BOREE_W2M_Greenfield_Reference_V2.0/` : inventaire complet, **zéro fichier de code** |
| Depot voisin | `../athanor` : `pyproject.toml`, arborescence `src/`, en-têtes de 10 modules (`data/rawstore.py`, `data/source.py`, `data/datasets.py`, `data/quality.py`, `research/protocol.py`, `research/card.py`, `research/provenance.py`, `research/registry.py`, `kernel/hashing.py`, `kernel/secrets.py`) |
| Cible | `torne/MISSION.md` (sections 1, 5.3, 6, 9, 11), `torne/docs/REUSE_AUDIT.md` |

### 0.2 Ce que je n'ai pas lu (donc ce que je n'affirme pas)

- `PREREG.md` (275 154 octets) au-delà de l'extraction des en-têtes d'amendements ; `PREREG_DE.md`, `PREREG_ES.md`, `PREREG_NL.md`.
- `docs/MARCHE.md` (30 Ko), `VALEUR.md`, `VALEUR_ETENDUE.md`, `ECMWF.md`, `FICHE_FROID.md`, `SOURCES.md`, `ROADMAP.md`, `VISION.md`.
- `docs/chantiers/` (16 fichiers) et `docs/resultats/` (30 fichiers) : inventaire et lecture de `README.md` seulement.
- `src/boree/evaluation/` (18 modules) : lus par têtes de grep et par le protocole, non lus intégralement.
- `src/boree/chaine/` (6 modules), `modeles.py`, `marche.py`, `final.py`, `salle.py`, `rendu.py`, `tableau.py`, `score_jour.py`, `calibration.py`, `verif_meteo.py`, `registre/familles/*.py`.
- `deploy/homelab/` (34 fichiers) et `frontend/` (Svelte/Vite) : inventaire ; `docs/flux/*.schema.json` : noms et tailles, non lus.
- Aucun fichier du dépôt audite n'a été modifié. Aucune commande d'écriture n'y a été lancee.

---

## 1. Cartographie des modules

Legende d'état : **I+** implémenté et vérifie (un test nommé le couvre) | **I-** implémenté mais non vérifie (aucun test dédié) | **D** documenté uniquement | **X** expérimental | **O** obsolète / retire.

### 1.1 Racine de `src/boree/`

| Module | Taille | Rôle | État | Preuve |
|---|---|---|---|---|
| `temps.py` | 6 042 | Point de vue "depuis la décision" : les règles de disponibilité, seules à y vivre | **I+** | `tests/test_temps.py` (6) ; ADR 0002 ; `PROTOCOLE.md:15-16` |
| `scelles.py` | 4 253 | Masque des journées scellées et accès machine unique | **I+** | `tests/test_scelles.py` (6) ; ADR 0003 |
| `direct.py` | 24 193 | Garde-fou d'accès direct : toute lecture passe par la, qui refuse les journées scellées | **I+** | `tests/test_direct.py` (11) |
| `doctor.py` | 4 828 | Controle de santé des données + empreinte SHA-256 du store | **I-** | aucun `test_doctor.py` ; `doctor.py:24-29` est la référence de reproductibilité citee par l'invariant 7 |
| `archive.py` | 32 573 | Magasin brut : index SQLite, versions, empreintes, `ref(asof=...)` | **I+** | `tests/test_archive.py` (23) |
| `lac/` | 3 fichiers | Catalogue des jeux, lecture point-in-time, forme dérivée Parquet/DuckDB | **I+** | `tests/test_lac.py` (16) ; `docs/LAC.md` vérifie par test (`lac/catalogue.py:13`) |
| `registre/` | 6 fichiers | Registre de modèles : contrats TOML, chaine générique en ombre, vérification d'empreintes | **X** | `tests/test_registre.py` (12), `test_registre_chaine.py` (10) ; `PROTOCOLE.md:154-156` : tourne en ombre, ne remplace rien avant le verdict |
| `physique/` | 5 fichiers | Jumeau physique, empilement prévu, contexte physique | **I+ / O** | `test_jumeau.py` (8), `test_empilement.py` (13), `test_contexte.py` (14) ; `docs/resultats/RESULTAT_jumeau.md` : résultat retire |
| `ingest/` | 7 fichiers | Collecte des sources, conservation brute, connecteurs | **I+** | `test_entsoe_api.py` (17), `test_ecmwf_direct.py` (9), `test_sources_nouvelles.py` (7), `test_ingest.py` (2) |
| `tables/` | 10 fichiers | Tables de variables disponibles à chaque horizon (feature store figé) | **I+** | `test_quotas.py` (4), `test_indispo.py` (4) ; gel déclare `PROTOCOLE.md:180` |
| `chaine/` | 7 fichiers | Chaine quotidienne : prévoir, juger, juger_hiver, rodage, ligne, modèles | **I+** | `test_juger.py` (12), `test_juger_hiver.py` (25), `test_rodage.py` (4), `test_chaine_bout_en_bout.py` (3), `test_reentrainer.py` (5) |
| `evaluation/` | 19 fichiers | Etudes rétrospectives (banque, H4, valeur, marché, fiche, juge) | **mixte** | `test_evaluation_marche.py` (24), `test_h4.py` (20), `test_valeur_etendue.py` (12) ; certaines closes (`docs/resultats/README.md:33-43`) |
| `exploitation/` | 6 fichiers | Garage (S3), revue de lancement, périmètre gelé, santé, métriques | **I+** | `test_lancement.py` (38), `test_deploiement_unites.py` (8), `test_garage.py` (5), `test_sante.py` (7) |
| `flux.py` | 30 239 | Écriture des flux JSON pour la salle de commandement | **I+** | `tests/test_flux.py` (18), `test_fiche_flux.py` (13) ; contrat dans `docs/flux/` |
| `marche.py` | 12 765 | Capture du marché EEX | **I+** | `test_marche.py` (7) |
| `modeles.py` | 3 137 | Specification du modèle gelé (interdit de modification) | **D** | `PROTOCOLE.md:180` |
| `calibration.py` | 7 640 | Cartes de calibration (Platt) | **I+** | `test_calibration.py` (10) |
| `score_jour.py` | 1 473 | x_D : écart de Brier normalise, unité de jugement | **I-** | aucun test dédié ; `PROTOCOLE.md:38` |
| `salle.py` | 14 665 | Ancienne page de contrôle (Python) | **O** | `docs/resultats/README.md:36` : l'ancien rendu est retiré |
| `tableau.py` / `rendu.py` | 10 877 / 6 729 | Serveur de tableau et rendu HTML | **I+ / O** | `test_serveur_tableau.py` (8), `test_rendu.py` (5) ; ancien rendu retiré |
| `final.py` | 4 974 | Ouverture unique des scellés (`boree final --ouvrir-scelles`) | **I-** | aucun `test_final.py` ; ADR 0003 |
| `verif_meteo.py` | 12 857 | Verification des runs météo (anti-fuite) | **I-** | couvert indirectement |
| `cli.py` | 13 967 | CLI `boree`, table `ETUDES` | **I+** | `tests/` sans test dédié ; commande `boree etude <nom>` documentée dans `PROTOCOLE.md` |

### 1.2 Ce qui vit à côté du code

- `frontend/` : application Svelte/Vite, 9 écrans (`Journal`, `Marche`, `Mission`, `Monde`, `Radar`, `Registre`, `Rejeu`, `Telemetrie`), tests Playwright avec jeux de fixtures `fixtures-scelles/` et `fixtures-doublons/`. La discipline "le vide et le doublon sont testés" est visible dans l'arborescence.
- `deploy/homelab/` : 13 unités systemd (`.service` + `.timer`), `installer.sh`, `mettre-a-jour.sh`, `RUNBOOK.md`, `chemins.env`.
- `docs/flux/` : 10 JSON Schemas (`etat`, `journal`, `marche`, `monde`, `previsions`, `registre`, `sante`, `test`, `fiche`, `empilement`) : le contrat de la salle de commandement est **machine-vérifiable**.
- `docs/adr/` : 3 ADR. `0002-un-seul-point-de-vue` et `0003-scelles` sont les deux justifications théoriques les plus transposables du dépôt.
- `registre/*.toml` : un fichier par modèle (`boree-h2.toml`, `boree-h3.toml`, `boree-h4.toml`).

### 1.3 État d'ensemble

Le dépôt est **un produit en production, pas une maquette** : 81 modules Python, 48 fichiers de test (457 fonctions),
un contrat de flux en JSON Schema, une revue de lancement de 12 critères, un store synthétique ou chaque valeur encode
sa date. En revanche il y a **deux zones explicitement hors production** : le registre (ombre) et la couche physique
(pre-calcul, hors chaine). Et **une zone explicitement cassee puis corrigée** : le jumeau.
---

## 2. Les briques réutilisables

Pour chaque brique : chemin, rôle, tests existants, coût de reprise, et la séparation demandée entre ce qui est
**transposable tel quel** et ce qui est **lié à la tension électrique FR/DE**.

### 2.1 Ingestion, conservation des payloads bruts, hashing, déduplication

**Chemins :** `src/boree/ingest/sources.py` (17 693 o), `src/boree/archive.py` (32 573 o), `src/boree/ingest/entsoe_api.py`, `ingest/ecmwf_direct.py`, `ingest/eua.py`, `ingest/europe.py`, `ingest/runs.py`.
**Rôle :** aller chercher une source, conserver le **payload brut tel quel**, l'addresser par son empreinte, et pouvoir
relire plus tard la version qui était connue à un instant donné.
**Tests :** `test_entsoe_api.py` (17), `test_ecmwf_direct.py` (9), `test_sources_nouvelles.py` (7), `test_ingest.py` (2),
`test_archive.py` (23).

**Constat majeur : BOREE réimplémente une brique qui existe déjà dans le dépôt voisin.**
`../athanor/src/athanor/data/rawstore.py` documenté un `RawStore` qui fait exactement cela, et mieux :

| Capacité | `athanor.data.rawstore.RawStore` | `boree/archive.py` |
|---|---|---|
| Conservation brute compressée, adressée par empreinte | oui (`<data>/raw/<source>/<aa>/<sha256>.gz`) | oui, même disposition de chemin (`garage.py:41-44`) |
| Reprise d'une collecte coupée | `has(source, key)` | équivalent côté boree |
| Versions multiples par clé, l'ancienne reste lisible | oui | oui |
| Lecture point-in-time | `get(source, key, asof=...)` | `ref(..., asof=...)` |
| **Qui pose `known_at`** | **le magasin, jamais l'appelant : on ne peut pas antidater** | `archive.py` s'appuye sur le même contrat |
| Écritures groupées, index WAL, `busy_timeout` | oui | hérite |

**Transposable tel quel :** rien de `boree/archive.py` -- c'est un doublon. Le comportement de référence est déjà
disponible et **plus robuste**.
**Lie à l'électricité FR/DE :** non pour le mécanisme ; oui pour le *contenu* (les sources ENTSO-E, Open-Météo, Hub Eau).
**Coût de reprise :** **faible** si on utilise `athanor` ; **élevé et sans valeur** si on recopie.
**Verdict : REJECT** pour le code, **REUSE** pour le comportement (voir section 6 pour le volet licence).

### 2.2 Normalisation des observations, unités, références spatiales

**Chemins :** `src/boree/temps.py:86-95` (`horaire`, `local`), `src/boree/physique/empilement.py:78-84`, `physique/contexte.py`, `physique/jumeau.py`.
**Rôle :** ramener les observations hétérogènes a un format commun.
**Tests :** `test_temps.py` (6), `test_empilement.py` (13), `test_contexte.py` (14).

Ce qui existe, et qui est solide :
- `temps.horaire` agrège les quarts d'heure en heures UTC ; `temps.local` bascule en heure de Paris et **fusionne les deux heures UTC qui tombent sur 2 h locale** (`temps.py:93-95`).
- `empilement._heures_de_paris` explicite la distinction **quantité vs filière** : les documents ENTSO-E sont au pas quart-horaire, l'heure est la moyenne de ses quatre quarts (ce sont des quantités, pas des filières à additionner) (`empilement.py:78-84`).

Ce qui **n'existe pas** :
- **Aucune couche d'unités.** Les unités vivent dans les noms de colonnes importés (`Day-ahead Price (EUR/MWh)`, `Physical Flow (MW)`, `Forecast min [MW]`). Aucun registre, aucune conversion, aucun contrôle.
- **Aucune référence spatiale.** Les zones sont des chaînes (`FR`, `DE-LU`, `BZN|FR`, `BZN|BE`), les points météo sont des noms (`A` a `F` dans le store de test, 26 points en production), les centrales sont des noms (`Chinon`, `Loire`). Aucune géométrie, aucun CRS, aucune bibliothèque géospatiale dans `pyproject.toml`.

**Transposable tel quel :** les deux fonctions de normalisation horaire (elles sont génériques et testées).
**Lie à l'électricité :** les schémas et les zones.
**Coût de reprise :** **faible** pour l'horaire, **à créer** pour unités et spatial.
**Verdict : ADAPT** ( horaire ) + **REJECT** pour le reste.

### 2.3 Temporalite et point-in-time : le coeur

**Chemins :** `src/boree/temps.py` (6 042 o), `src/boree/lac/connu.py` (10 301 o), `src/boree/lac/catalogue.py` (10 256 o), `docs/adr/0002-un-seul-point-de-vue.md`.
**Rôle :** repondre à la seule question qui compte en recherche prospective : *que savait-on à cet instant ?*
**Tests :** `test_temps.py` (6), `test_lac.py` (16) -- dont un test qui vérifie que `docs/LAC.md` et le catalogue
disent la même chose (`lac/catalogue.py:13`).

Le mécanisme est en trois pièces, et il est **exemplaire** :

1. **Un seul maître.** Toutes les règles de disponibilité vivent dans `boree/temps.py` et nulle part ailleurs
   (`PROTOCOLE.md:15-16`, ADR 0002). Le catalogue ne recopie pas la règle : il la **nommé**
   (`lac/catalogue.py:7-9` : "la disponibilité est une règle de `boree.temps`, NOMMEE ici (`regle`) et jamais recopiée").
2. **Le catalogue appelle la règle.** `lac/connu.py:74-76` fait `getattr(temps, regle)(0)` : un décalage de jours du
   dernier jour connu à la décision, évalué à k = 0. Aucune duplication possible.
3. **Une seule fonction de lecture.** `tel_que_connu(jeu, periode, instant)` (`lac/connu.py:1-16`) rend la table
   restreinte aux événements de la période **telle qu'elle était connue à l'instant**. Pour l'archive brute, la règle
   est celle d `athanor.kernel.clock` : utilisable des `max(publication, capture)` (`lac/connu.py:11-13`).
   `jour_de_connaissance` (ligne 48-51) applique la règle inverse : avant 10 h, on ne sait pas ce que les règles
   diraient, donc on prend la veille -- "le lac peut être en retard sur la réalité, jamais en avance".

**Transposable tel quel :** le *pattern* (autorite unique + règle nommée + point-in-time = une requête, pas une copie de
données). Il est indépendant du domaine.
**Lie à l'électricité :** **tout le contenu** des règles (`lag_prix`, `lag_gaz`, `lag_quota`, `echeance_meteo`,
`hebdo_publiee`, les seuils EWL/RTE). Ces valeurs-la sont explicitement **hors périmètre** pour TORNE
(`torne/docs/REUSE_AUDIT.md:88-89` : "Le protocole scellé Borée H3, son module temporel et ses règles sont hors
périmètre : ils ne sont ni modifiés, ni extraits, ni réimplémentés").
**Coût de reprise :** le pattern est **gratuit** à copier ; le module `temps.py` lui-même est **hors périmètre**.
**Verdict : REJECT** pour `boree/temps.py` et son contenu ; **ADAPT** pour le pattern, qui doit être reconstruit par
TORNE sur ses propres domaines (et non dérivé des constantes BOREE).

### 2.4 Transformations analytiques, provenance, linéage

**Chemins :** `src/boree/lac/parquet.py`, `src/boree/lac/connu.py:32` (`LIGNAGE`), `src/boree/physique/empilement.py:245-247`, `src/boree/registre/contrat.py`.
**Rôle :** pouvoir dire d'ou vient chaque ligne, et la relier à sa source.
**Tests :** `test_lac.py` (16), `test_registre.py` (12).

Le **lignage a quatre colonnes** est simple et efficace : `_source`, `_cle`, `_empreinte`, `_connu_a`
(`lac/connu.py:32`), posées à chaque version analysee (`lac/parquet.py:42-43`). L'empilement fait de même pour ses
sources : `nom`, `cle`, `empreinte`, `capture` (`empilement.py:245-247`). Le registre empreinte les fichiers de
l'algorithme d'un modèle.

**Ce que BOREE n'a pas :** le gel de la **fermeture du code de mesure**. `../athanor/src/athanor/research/provenance.py`
documenté une empreinte qui couvre, en plus de la table de jugement, "la fermeture du code de mesure : les fichiers
`.py` du dossier de l'étude, plus chaque module `athanor.*` qu'ils importent, transitivement (analyse statique des
imports, sans rien exécuter)", avec une preuve d'équivalence, un blocant et un signalé distincts, et deux empreintes
consignees (le juge, l'environnement `uv.lock`). **C'est plus complet que BOREE.**

**Transposable tel quel :** les 4 colonnes de lignage -- oui, elles sont triviales et générales.
**Lie à l'électricité :** non.
**Coût de reprise :** **faible** pour le lignage ; **nul** si on hérite de `athanor.research.provenance`.
**Verdict : ADAPT** ( lignage ), **REJECT** ( toute mécanique de gel qui ferait doublon avec athanor ).

### 2.5 Snapshots et reconstitution historique

**Chemins :** `src/boree/archive.py`, `src/boree/lac/parquet.py:50-70` (`materialiser`), `lac/parquet.py:5-6`.
**Rôle :** pouvoir reconstruire l'état du monde à une date donnée, à partir des seules données brutes.
**Tests :** `test_archive.py` (23), `test_lac.py` (16).

C'est la brique **la plus transposable de tout le dépôt**. Le principe est explicite :
"le Parquet garde **toutes** les versions analysees, avec leur lignage : la question "telle que connue à t" devient
une requête (dernière version de chaque clé dont `_connu_a` <= t). **Il se reconstruit à tout moment depuis l'archive
brute, qui reste la seule source de vérité.**" (`lac/parquet.py:4-6`). La forme dérivée est **reconstruite**, jamais
considerée comme la source : `materialiser` redérive les partitions par mois depuis le magasin brut
(`lac/parquet.py:50-70`).

Le détail d'écriture est propre : écriture dans un fichier temporaire puis renomme -- "une lecture concurrente voit
l'ancienne partition ou la nouvelle, jamais une moitié" (`lac/parquet.py:53-54`, `67-68`).

**Transposable tel quel :** le principe (brut = vérité, dérivé = reconstructible), le format de partitionnement
`annee=/mois=`, la lecture DuckDB **locale, sans serveur** (`lac/parquet.py:8-9` : "DuckDB lit les fichiers locaux,
sans serveur"), et la réécriture atomique des partitions.
**Lie à l'électricité :** non.
**Coût de reprise :** **moyen** -- le code est générique, mais il s'appuie sur `RawStore` et sur le vocabulaire du lac BOREE.
**Verdict : ADAPT** -- c'est la brique à porter en priorité, en la reecrivant sur le socle TORNE.

### 2.6 Connecteurs réels et leurs tests

**Chemins :** `ingest/entsoe_api.py` (25 410 o), `ingest/ecmwf_direct.py` (22 916 o), `ingest/eua.py`, `ingest/europe.py`, `ingest/runs.py`.
**Rôle :**Brancher des APIs externes.
**Tests :** `test_entsoe_api.py` (17), `test_ecmwf_direct.py` (9), `test_quotas.py` (4), `test_europe.py` (6).

Les connecteurs sont **réels et bien testés** : ENTSO-E Transparency Platform (REST, jeton d'environnement, pagination),
Open-Météo / runs ECMWF IFS (archives de runs anciens, variables `previous_day1..7`), EEX (enchères de quotas CO2),
Europe (NL/ES). C'est un très bon example de couverture.

**Transposable tel quel :** **aucun connecteur** -- ils sont tous lies au marché de l'électricité.
**Transposable comme modèle :** le *contrat de connecteur*. Mais `../athanor/src/athanor/data/source.py` le fait déjà,
et mieux : `plan()` énoncé les requêtes (clés stables), `collect()` télécharge ce qui manque dans le magasin brut,
`parse()` transformé un brut en lignes horodatées ; "l'analyse ne touche jamais le réseau ; on peut re-parser tout le
brut sans rien re-télécharger". Y ont ajouté `data/compliance.py` (robots.txt, conditions d'utilisation, ce qui a été
lu et quand ; une source RESTREINTE refuse de collecter tant qu'une décision humaine n'est pas prise) et un dossier
`data/sources/` de 20+ collecteurs déjà écrits, dont `weather.py`.
**Coût de reprise :** **nul** si on utilise athanor.
**Verdict : REJECT** ( les connecteurs BOREE ) + **REUSE** ( le contrat `athanor.data.source` ).

### 2.7 Donnees géospatiales et multidimensionnelles

**Chemins :** `src/boree/physique/contexte.py` (12 904 o), `physique/jumeau.py` (9 829 o), `physique/empilement.py` (13 032 o), `ingest/ecmwf_direct.py`.
**Rôle :**reconstituer un état physique à partir de grandeursObservees.
**Tests :** `test_contexte.py` (14), `test_jumeau.py` (8), `test_empilement.py` (13).

Ce qui est réellement la :
- **Points météo nominaux** : 26 points, chacun avec un `role` (temp / éolien / solaire) et un `pays` (`contexte.py`,
  `tests/fabrique.py:49-56`). Aucune coordonnée géographique dans le store de production (les colonnes `lat`/`lon`
  sont exclues explicitement du traitement chiffre, `lac/connu.py:88`).
- **Grille ECMWF** : lecture des runs IFS par des variables named `previous_day1|2|4|7` -- l'échéance est codee dans le
  **nom de la colonne** (`lac/connu.py:33`, `RE_ECHEANCE`). C'est elegant et fragile.
- **Multidimensionnalite réelle** : l'empilement est un tableau `heure x composante` (charge, éolien, offshore, solaire,
  nucléaire, offre, marge, filière, cout_bas, cout_haut) -- `empilement.py:217-244`.

**Ce qui n'existe pas :** **aucune géométrie, aucun CRS, aucune jointure spatiale, aucune rastérisation, aucun
geopandas/shapely** dans `pyproject.toml`. La "géospatialité" de BOREE est un ensemble de chaînes de caracteres.
**Transposable tel quel :** la technique du **multi-dimensionnel en colonnes nommées** (échéance dans le nom) et la
table `heure x composante`.
**Lie à l'électricité :** les grandeurs physiques (pression, refroidissement éolien, decroche tempête, angle zénithal).
**Coût de reprise :** **nul** pour ce que BOREE a ; **entièrement à faire** pour le vrai géospatial de TORNE.
**Verdict : REJECT** pour la couche physique ; **REIMPLEMENT** pour le géospatial (BOREE n'offre rien).

### 2.8 Le registre de modèles et ses contrats

**Chemins :** `src/boree/registre/contrat.py` (4 735 o), `registre/chaine.py` (10 752 o), `registre/verifier.py` (3 134 o), `registre/familles/`, `registre/*.toml`.
**Rôle :** déclarer des modèles (statuts, horizons, juge), les faire tourner, comparer, et consigner les empreintes.
**Tests :** `test_registre.py` (12), `test_registre_chaine.py` (10), `test_flux_registre.py` (5).

Le contrat est propre : `Contrat` (nom, famille, statut, horizons, limite, fuseau, code{famille, fichiers, empreinte},
juge{code, référence}) ; statuts `EN_AVANT` = ombre / en test / en service. La chaine générique prépare, prévoit,
archive, compare, juge, publié. Le **contrôle** est outille : `boree verifier registre` relit chaque contrat, vérifie que
l'empreinte déclarée est celle des fichiers du dépôt, et sort en code 1 si elle ne correspond plus
(`registre/verifier.py:50-66`).

Deux éléments de **méthode** qui valent d'être repris :
- **La parité au bit pres** entre la chaine générique et la chaine de référence : statut `conforme` / `differente` /
  `non compare`, avec "un enregistrement manque d'un côté (jamais compte comme conforme)" (`registre/chaine.py:89-110`).
- **Le critère de bascule explicite et chiffre** : au moins `PARITE_MIN = 14` jours conformes sur 16 jours de rodage,
  aucun écart (`registre/chaine.py:31, 113-121`). "Ce n'est pas une bascule : seulement l'état du critère."

**Mais :** `../athanor/src/athanor/research/registry.py` fait déjà cela, et en plus. C'est une **machine à états rejouée
depuis le journal** (event sourcing), sans fichier d'état (`REGISTRY.md` est une vue générée), avec des transitions
vérifiées et une transition `LEGACY_VERDICT --> ARCHIVED` explicitement prévue pour reprendre un verdict d'un ancien
dépôt. C'est **le mécanisme que TORNE devrait utiliser pour adopter BOREE comme héritage**.

**Transposable tel quel :** la **méthode de parité bit-a-bit** et l'idée d'un critère de bascule chiffre.
**Lie à l'électricité :** les contrats eux-memes (H2/H3/H4).
**Coût de reprise :** **moyen** -- le code est simple mais fait doublon ; la méthode est réutilisable telle quelle.
**Verdict : REJECT** pour le registre lui-même (doublon `athanor.research.registry`) ; **ADAPT** pour la méthode de parité.

### 2.9 Le lac : catalogue, formats, requêtage

**Chemins :** `src/boree/lac/catalogue.py`, `lac/connu.py`, `lac/parquet.py`, `docs/LAC.md`.
**Rôle :** repondre uniformément a "que savait-on à tel instant", quel que soit le jeu de données.
**Tests :** `test_lac.py` (16).

Le catalogue est une **déclaration**, pas une implémentation : la dataclass `Jeu` (nom, régime, source, description,
granularité, publication, **règle**, colonne_temps, schéma, prix, analyseur, emplacement) -- `lac/catalogue.py:25-40`.
15 jeux du store + les jeux de l'archive brute. Chaque entrée déclare sa granularité ("15 min ou 1 h", "jour", "jour
ouvre"), sa publication ("D-1 vers 13 h", "vendredi pour la semaine suivante", "18 h la veille"), sa règle de
disponibilité **nommée**, son schéma de colonnes, et si c'est un **jeu de prix** (donc soumis aux scellés,
`lac/catalogue.py:38`).

Le format du lac dérivé est propre : Parquet partitionné `annee=AAAA/mois=MM/versions.parquet`, lu par DuckDB en
local sans serveur, avec le lignage 4 colonnes, et une réécriture atomique par partition. Le rechargement vers Garage
est incremental (clé portant la date de modification du fichier) -- `lac/parquet.py:138-151`.

**Transposable tel quel :** la **structure** du catalogue (un objet déclaratif par jeu, avec règle nommée, granularité,
publication, schéma) et le **format dérivé**. Ces deux choses sont génériques a un point d'être domaine-independent.
**Lie à l'électricité :** **le contenu intégral** du catalogue (prix day-ahead FR/DE-LU, quotas EUA, TTF, debits
Hub Eau, bilan RTE eco2mix, avis EDF).
**Coût de reprise :** **moyen** -- code générique, a réécrire sur le vocabulaire TORNE.
**Verdict : ADAPT** -- **brique prioritaire**. C'est la que se trouve le plus de valeur transposable de tout le dépôt.

### 2.10 Archivage et empreintes (`archive.py`, Garage S3)

**Chemins :** `src/boree/archive.py`, `src/boree/exploitation/garage.py` (13 369 o).
**Rôle :** garantir que la donnée irremplaçable survit à la machine.
**Tests :** `test_archive.py` (23), `test_garage.py` (5).

Trois mécanismes de qualité, tous réutilisables comme **règles** :
1. **Local d'abord, copie après.** La docstring de `garage.py:3-7` est un post-mortem : dans `RawStore.put`, chaque blob
   part sur S3 au fil de l'eau ; si Garage ne repond pas, l'exception sort du lot et **annule les lignes d'index du
   passage**, donc une panne de Garage ferait perdre la collecte locale du jour. D'ou : collecte locale d'abord
   (`sync_s3=False`), puis `repliquer` envoie ce qui manque et note ce qui est parti (`repliques.txt`) -- "une panne de
   Garage **retardé** la copie, elle ne **perd** rien".
2. **Integrity par empreinte, jamais par décodage.** `sain()` vérifie que le blob compresse redonne bien son empreinte
   (`garage.py:47-53`) ; la règle explicite : "on compare des empreintes et des octets, **on ne décode jamais** un
   document (l'archive contient des prix postérieurs au gel)" (`garage.py:12-13`).
3. **Instantane cohérent.** `instantane()` fait une sauvegarde SQLite pour inclure le WAL, "l'index publié est un
   instantané cohérent" (`garage.py:9-10, 71-82`).

**Transposable tel quel :** les trois règles ci-dessus. Elles sont **indépendantes du domaine** et nouvelles pour TORNE.
**Lie à l'électricité :** le mécanisme S3 lui-même est déjà dans `athanor.data.s3`.
**Coût de reprise :** **faible** pour les règles (à écrire dans TORNE) ; **nul** pour le client S3.
**Verdict : REJECT** pour le code (doublon `athanor.data.s3`) ; **ADAPT** pour les trois règles -- **priorité élevée**.

### 2.11 Les scellés et l'accès machine

**Chemins :** `src/boree/scelles.py`, `src/boree/direct.py`, `src/boree/final.py`, `docs/adr/0003-scelles.md`.
**Rôle :** garantir qu'un regard sur des données de test les use -- et que cela soit impossible, pas seulement interdit.
**Tests :** `test_scelles.py` (6), `test_direct.py` (11).

Le mécanisme est en quatre points (ADR 0003) :
- l'ingestion écrit les prix postérieurs au 2026-04-28 dans `store/scelles/` ; **aucun module ne les lit sauf `boree.final`** ;
- `boree final` refuse de tourner sans `--ouvrir-scelles`, refuse une seconde exécution, et consigne **AVANT** la
  lecture l'empreinte SHA-256 du pre-enregistrement et de chaque fichier du code ;
- le masque (`scelles.py`) est appele par `doctor.py:58-59` pour vérifier qu'aucune journée scellée n'est dans le store principal ;
- `direct.py` est le point de passage obligatoire de toute lecture.

Le principe est **le** résultat le plus important de BOREE pour TORNE : **rendre la fuite impossible par construction**
(une porte unique, refusée par défaut, vérifiée par tests) plutôt que par discipline ou par documentation.

**Transposable tel quel :** le **principe** (barriere d'accès unique, testée, qui refuse par défaut ; l'empreinte du
protocole et du code consignee avant toute ouverture).
**Lie à l'électricité :** **tout** -- les journées scellées sont les journées de livraison FR/DE, et le protocole
prospectif est le sien.
**Coût de reprise :** **moyen** pour transposer le principe dans le cadre de TORNE.
**Verdict : REJECT** pour le code ; **ADAPT** pour le principe (à prioriser).

### 2.12 Le flux de sortie et le contrat de la salle de commandement

**Chemins :** `src/boree/flux.py` (30 239 o), `docs/flux/` (10 JSON Schemas + README), `frontend/` (Svelte, 9 écrans).
**Rôle :** exposer l'état du système a un consommateur, sans que celui-ci ait à connaître le modèle.
**Tests :** `test_flux.py` (18), `test_fiche_flux.py` (13) ; frontend : Playwright avec fixtures `scelles` et `doublons`.

Ce qui est excellent et transposable :
- **Le contrat est machine-vérifiable** : un JSON Schema par flux (`docs/flux/*.schema.json`). Une salle de commandement
  peut évoluer sans que le modèle bouge.
- **L'enveloppe est uniforme** et porte `modele`, `decision`, `donnees`, `note`.
- **Un flux peut être absent, et cela se dit.** `PROTOCOLE.md:111-113` : "Le fichier **peut être absent** ... : l'écran
  le dit, il n'invente pas de valeur." Et les flux annexes `fiche.json` / `empilement.json` suivent la même règle
  (`PROTOCOLE.md:137-140`).
- **Un flux vide garde ses types**, et l'instant ne peut pas être NaT (commits `c6290a9`, `725d2e0`).

**Transposable tel quel :** l'enveloppe, les schémas, la règle de l'absence explicite, la discipline du flux vide type.
**Lie à l'électricité :** les contenus (`H2|t1`, `H3|t1`, `fiche du matin`, `empilement FR`).
**Coût de reprise :** **moyen**.
**Verdict : ADAPT** -- fort pour TORNE, qui a besoin d'une salle de commandement équivalente.

---

## 3. La discipline : écrite, outillee, ou seulement documentée

La distinction demandée est la plus utile de ce rapport : une règle **écrite** n'engage que l'auteur ; une règle
**outillee** est vérifiée par l'exécution ; une règle **documentée** n'engage que le lecteur.

### 3.1 Règles écrites (engageantes, mais non vérifiées par la machine)

| Règle | Ou | Preuve |
|---|---|---|
| Toute nouvelle variable, variante, cible, zone ou méthode d'évaluation s'écrit **d'abord** comme amendement date, **commité avant le premier calcul** | `CLAUDE.md` invariant 2 ; `PROTOCOLE.md:1-6` | amendements numérotés et dates ; le plus récent repere est le n 48 (commit `9ca2d9f`) |
| On ne modifie **jamais** un amendement passe ; les résultats sont ajoutes tels quels, "même mauvais" | `CLAUDE.md` invariant 2 | `PROTOCOLE.md:4-6` : "en cas de désaccord, le registre l'emporte" |
| Le même commit met `PROTOCOLE.md` à jour (amendement 27) | `CLAUDE.md` invariant 2 | `PROTOCOLE.md:5-6` |
| Les règles de disponibilité vivent dans `boree/temps.py` **et nulle part ailleurs** | invariant 3 ; ADR 0002 | `PROTOCOLE.md:15-16` |
| **Une étude qui ne peut rien changer ne s'ouvre pas** | `CLAUDE.md` invariant 2 | écrit, pas outille |
| Un résultat publié **ne se modifie jamais** | `docs/resultats/README.md:50-51` | écrit ; vérifie par la pratique (voir 4.3) |
| Une étude close dont le résultat ne sert plus à rien se retire, son résultat publié reste | `CLAUDE.md` Style ; `docs/resultats/README.md:33-43` | écrit |
| Modèle figé pendant le test en avant (rien ne change, sauf retraining mensuel) | invariant 4 | `PROTOCOLE.md:177-182` |
| Donnees publiques seulement ; rien de l'employeur | invariant 5 | - |
| Secrets jamais dans le dépôt, les journaux, les sorties de commande ou les messages | invariant 6 | `garage.py:37` ; `archive.py:312-314` |
| Determinisme : graine 20261028 ; `threadpool_limits(1)` ; parallélisme par plis (`BOREE_JOBS`) | invariant 7 | `PROTOCOLE.md:81` |

### 3.2 Règles outillees (vérifiées à l'exécution)

| Controle | Ou | Ce qu'il refuse |
|---|---|---|
| `boree doctor` | `doctor.py:41-91` | couverture de chaque source ; heures manquantes ; **exports ENTSO-E en double** (SHA-256 sur `data/entsoe/**`) ; journées scellées dans le store principal ; écrire `resultats/empreinte_store.json` ; **code de sortie 1** si un contrôle bloquant echoue |
| `boree verifier lac` | `registre/verifier.py:20-47` | lecture seule, compte de lignes et durée par jeu, **aucune valeur affichee** ("des comptes et des durées seulement") |
| `boree verifier registre` | `registre/verifier.py:50-66` | **code de sortie 1** si l'empreinte d'un contrat ne correspond plus aux fichiers du dépôt |
| `boree deploiement garder` | `exploitation/deploiement.py` | refuse tout fichier hors du périmètre gelé (`PROTOCOLE.md:180-182`) ; `tests/test_deploiement_unites.py` (8) |
| `boree final --ouvrir-scelles` | `final.py`, ADR 0003 | refuse de tourner sans le drapeau ; **refuse une seconde exécution** ; consigne l'empreinte du pre-enregistrement et du code **avant** la lecture |
| Le store synthétique anti-fuite | `tests/fabrique.py:1-2` | "chaque valeur ENCODE sa date : un test peut alors lire, dans chaque variable de la table, de quel jour vient l'information et vérifier qu'elle était connue à la décision" ; le réalisé interdit vaut **-1** (lignes 26, 34, 70, 104) |
| Les tests anti-fuite | `test_temps.py`, `test_direct.py`, `test_scelles.py` | ADR 0002 : "Toute nouvelle variable arrive avec sa ligne dans ce tableau et son cas dans `tests/test_temps.py`" |
| Le contrat du lac | `lac/catalogue.py:13` | un test vérifie que `docs/LAC.md` et le catalogue disent la même chose |
| La revue de lancement | `exploitation/lancement.py` (55 Ko), `docs/resultats/LANCEMENT_criteres.md` | 12 critères, `tests/test_lancement.py` (38) |
| Les codes de sortie de `boree archive` | `PROTOCOLE.md:162-165` | 0 nominal / 1 dégradé / 2 impossible / 3 impossible relancable ; l'unité ne relance que le 3 |
| L'empreinte du code du modèle | `PROTOCOLE.md:81-82` | H4 : `9a3c49dc...` (14 fichiers), `h4.py` : `516781b5...` ; "`h4.py` ne bouge plus" |
| Le profil calendaire figé | `PROTOCOLE.md:117-118` | `resultats/profil_calendaire.json`, "empreinte vérifiée à chaque lecture" |
| Les tests de déploiement | `tests/test_deploiement_unites.py` | vérifient que les unités systemd lancent `uv run --frozen --no-sync` |

### 3.3 Règles seulement documentées (ni outillees, ni vérifiées)

- **Le test en avant lui-même.** Le scellement est outille (masque, `final`, `doctor`), mais la *règle prospective* ne
  peut pas être outillee : on peut constater qu'on n'a pas regardé, pas prouver qu'on n'a pas regardé.
  `docs/adr/0003-scelles.md:14-15` le formule honnêtement : "Chaque regard sur des données de test les use."
- **"Une étude qui ne peut rien changer ne s'ouvre pas"** : écrit, jamais outille.
- **La traduction du protocole** dans `PREREG_DE.md`, `PREREG_ES.md`, `PREREG_NL.md` : non lus, non vérifiés.
- **Les États de santé "dégradé / impossible / relancable"** sont documentés dans `PROTOCOLE.md` et **oui** outilles par
  le code de sortie -- mais la distinction "une série qui s'arrete" vs "une série qui decroche" (amendement 47) est
  outillee par des seuils d'exploitation (`FRAICHEUR_HYDRO_JOURS`, `DECRO_HYDRO_JOURS`, `DECRO_HYDRO_MIN` dans
  `archive.py:83-87`), donc elle est à moitié outillee.
- ~~Le "dossier de travail" `resultats/` à la racine : non outille.~~ **Correction : cette règle EST outillee.**
  `.gitignore` exclut `resultats/*` et n'en conserve que cinq fichiers nommés (`cartes_calibration.json`,
  `profil_calendaire.json`, `rapport_h4.json`, `rapport_jumeau.json`, `rapport_ecmwf.json`) : la convention de
  `docs/resultats/README.md:53-54` ("rien n'y est versionné, tout y est régénérable") est appliquee par `.gitignore`.

### 3.4 Ce que la discipline BOREE ne couvre pas

- **Aucune trace d'exécution** des amendements (qui a décidé quoi, quand) au-delà des dates de commit.
- **Pas d'horodatage des décisions** dans le registre du code : le registre ne porte que `statut`, `empreinte`,
  `derniere_decision`, `en_retard` (`registre/chaine.py:144-150`).
- **Pas de test qui vérifie qu'aucune règle de disponibilité n'existe ailleurs** que dans `temps.py` : l'invariant 3
  est une règle écrite, pas un contrôle.
---

## 4. Ce qui a été appris à la dure

Chaque lesson est appuyee sur une preuve (chemin:ligne, commit, ou contenu d'un document de résultat).

### 4.1 Le temps doit avoir un seul maître

`boree/temps.py` est la **seule** source des règles de disponibilité, et le catalogue ne la recopie pas : il la nommé
(`lac/catalogue.py:7-9`) et l'appelle (`lac/connu.py:74-76`, `getattr(temps, regle)(0)`).

*Preuve :* `docs/adr/0002-un-seul-point-de-vue.md:6-10`, `PROTOCOLE.md:15-16`.
*Lecon pour TORNE :* une règle de disponibilité dupliquee est une fuite qui n'attend pas son heure. Le point-in-time doit
avoir une seule autorite, et il faut un test qui **détecte** les copies (BOREE ne l'a pas : voir 3.4).

### 4.2 La moyenne au lieu de la somme : le jumeau était faux

*Preuve :* `docs/resultats/RESULTAT_jumeau.md` -- "**Retire : les chiffres étaient faux** (la production était
moyennee par filière au lieu d'être sommée)". Le résultat corrigé (`RESULTAT_jumeau_corrige.md`) dit : "le classement
tient (AUC 0,942), le niveau non -- dans 86 % des heures de tension, le parc couvre la charge".
*Le code le dit désormais en toutes lettres :* `physique/empilement.py:97-101` -- "Les filières d'un même groupe
s'additionnent : une moyenne diviserait la production par le nombre de filières (**le défaut trouve le 2026-10-30**)."
*Commits :* `46e0ab2` "L'empilement : une composante manquante n'est pas un zéro, et le protocole dit ce qu'il est" ;
`2180a4d` "Un zéro est une mesure, pas une valeur manquante".
*Lecon pour TORNE :* le sens d'une agregation est une **décision de modèle**, pas un détail d'implémentation. Et le
premier résultat porte l'erreur : il est retire, pas réécrit.

### 4.3 Un résultat publié ne se réécrit jamais

*Preuve :* `docs/resultats/README.md:50-51` -- "Un résultat publié **ne se modifie jamais** : s'il est faux ou périmé,
on en écrit un autre à côté (ou on le retire comme ci-dessus), **on ne le réécrit pas**." Concretement,
`RESULTAT_jumeau.md` (faux) et `RESULTAT_jumeau_corrige.md` coexistent dans le même dossier.
*Lecon pour TORNE :* c'est la discipline la plus directement transposable de tout le dépôt. Elle se combine avec
l'usage de git : les comptes rendus retirés restent dans l'historique (`docs/resultats/README.md:41-43` donne la
commande `git log --diff-filter=D --name-only -- docs/resultats/`).

### 4.4 Une étude close se retire, son résultat reste

*Preuve :* `docs/resultats/README.md:33-43` liste ce qui a été retire le 2026-10-30 (fusion à J-1, premier tour
d'amélioration, les horizons, l'ancien rendu de la salle, les quotas de CO2, les tests DE/NL/ES) et explique que les
comptes rendus restent dans l'historique git.
*Lecon pour TORNE :* un dossier de résultats qui ne contient que ce qui **décide encore quelque chose** est un
dossier dont la taille est un indicateur de santé du projet.

### 4.5 Le vide est une information, et il a deux formes

Deux règles distinctes, souvent confondues :
- **Un flux absent** : "l'écran le dit, il n'invente pas de valeur" (`PROTOCOLE.md:111-113` et `139-140`).
- **Une composante manquante n'est pas un zéro** : `empilement.py:221-223` -- `sum(axis=1, min_count=len(composants))`,
  et le commentaire "Une composante manquante n'est pas un zéro : l'heure est **inconnue**, pas fausse."
*Commits :* `2180a4d` ("Un zéro est une mesure, pas une valeur manquante"), `725d2e0` ("Un flux vide sans un mot :
l'instant des flux ne peut plus être NaT"), `c6290a9` ("Le flux vide garde ses types, et le test ne dépend plus du store
de la machine").
*Lecon pour TORNE :* distinguer "pas d'observation" de "observation nulle" -- dans les interfaces **et** dans les
calculs. Un flux vide reste type.

### 4.6 Une panne de stockage ne doit pas perdre la collecte

*Preuve :* `exploitation/garage.py:3-7` -- "dans athanor, `put` envoie chaque blob sur S3 au fil de l'eau ; si Garage
ne repond pas, l'exception sort du lot et annule les lignes d'index du passage, donc **une panne de Garage ferait
perdre la collecte locale du jour**. Ici la collecte est locale d'abord (`sync_s3=False`), puis `repliquer` envoie tout
ce qui manque et note ce qui est parti (`repliques.txt`) : une panne de Garage **retardé** la copie, elle **ne perd
rien**." Même logique côté blobs : "le blob est toujours écrit **AVANT** sa ligne" (`athanor.data.rawstore`).
*Lecon pour TORNE :* le réseau ne doit jamais être dans le chemin critique de l'écriture locale. C'est une contrainte
d'architecture, pas une optimisation.

### 4.7 Un quota n'est pas une panne ; une source morte sort du code

*Preuve :* `PROTOCOLE.md:166-169` -- les appels Open-Météo sont espaces, un 429 est repris après un delai, nombre
d'essais borne ; si le quota tient malgré tout, le passage est **dégradé**, jamais impossible. Et "les
indisponibilités d'unités ENTSO-E pour la Belgique (A77) ne sont plus demandées, **et un test le vérifie** (45 e)".
*Lecon pour TORNE :* quatre états de santé distincts (nominal / dégradé / impossible / impossible relancable) encodes
dans le code de sortie -- et une source qui ne sert plus **sort du code**, avec un test qui le prouve.

### 4.8 Une série qui s'arrete et une série qui decroche ne demandent pas la même chose

*Preuve :* `PROTOCOLE.md:170-173` -- "une station hydro dont la série s'arrete est signalée par la **dernière date de
la série stockée**, même quand les jours de prix sont la ; une station qui publié encore mais ne livre plus de
valeurs exploitables est signalée à part (47) -- **l'une est un fait structurel, l'autre transitoire**, et les décisions
qui s'en suivent sont différentes." Commit `d1a0e72` (amendement 47).
*Parametres :* `archive.py:83-87` (`FRAICHEUR_HYDRO_JOURS`, `DECRO_HYDRO_JOURS`, `DECRO_HYDRO_MIN`).
*Lecon pour TORNE :* dans une reconstitution d'état, la **cause** d'une absence de donnée change l'interprétation.

### 4.9 La salle de commandement ne doit pas lire une autre source que le modèle

*Preuve :* commit `2d87859` -- "La salle lisait le store du clone : les tables figées lui manquaient, **sans un
mot**." Le symptôme n'était visible nulle part ; la salle était simplement incomplete.
*Lecon pour TORNE :* c'est une **erreur de topologie**, pas de code. Si la salle lit une source différente du modèle,
elle ment silencieusement. Meme famille : commit `90da50f` "Deux bascules ne peuvent plus s'écraser : verrou de
déploiement et candidat unique".

### 4.10 Une copie non tentée est dite avec sa raison, pas comme une copie absente

*Preuve :* commit `58a99dd` -- "La copie non tentée est dite avec sa raison, pas comme une copie absente."
Complete par `garage.py:96-98` ("s'arrete à la première erreur de Garage : le reste part au passage suivant
(`en_attente`)") et `garage.py:104-107` (un blob référence mais absent du disque local est compte `absents_locaux`
sans bloquer les autres).
*Lecon pour TORNE :* dans une chaine aval (conséquences économiques et financières), la distinction entre "absent",
"non tente" et "en attente" doit être portée par les données, pas devinée par le consommateur.

### 4.11 Une règle d'interdiction doit être outillee, pas seulement écrite

*Preuve :* commit `295edbf` -- "Un alias de regexp en toutes lettres : **la bascule n'était pas bloquee par le code**."
Autrement dit : la règle existait, mais l'outil qui devait l'appliquer laissait passer.
*Preuve complémentaire :* `PROTOCOLE.md:180-182` liste le "périmètre refuse par `boree deploiement garder`" -- un outil,
pas une prière.
*Lecon pour TORNE :* toute règle critique de TORNE (pas de fuite, pas de double comptage, pas de réutilisation d'une
donnée non disponible à la décision) doit avoir un **contrôle exécutable** et un **test qui echoue** quand elle est
violée.

### 4.12 Defauts de qualité constatés dans le code (à ne pas recopier)

- **Initialisation en double** dans `src/boree/ingest/sources.py:25-33` : `JOURNAL`, `S = requests.Session()` et
  `TODAY` sont définis deux fois dans le même module (lignes 25-28 puis 31-33). La seconde `Session` écrase la
  première ; `FORCE = False` (ligne 29) n'existe que dans le premier bloc. Sans effet fonctionnel immédiat, mais c'est
  exactement le genre de code qui produit un bug plus tard.
- **Trois chemins vers la même donnée brute** : `archive.py` (magasin), `direct.py` (accès direct), `lac/` (point
  d'entrée normalise). `lac/` est le point d'entrée à privilégier ; les deux autres sont des cas particuliers.
- **Un module de 55 Ko** : `exploitation/lancement.py` (55 432 o), suivi de `archive.py` (32 573), `flux.py` (30 239),
  `juger_hiver.py` (26 896), `entsoe_api.py` (25 410), `direct.py` (24 193). Un module de cette taille est un signal
  que la frontière de responsabilité n'est pas établie.
- **Couplage par import de fonctions** : `physique/empilement.py` importe `physique/jumeau.py`
  (`filiere_marginale`, `plancher_prix`) et `tables/horizon.py` + `tables/quotas.py` ; `registre/chaine.py` importe
  `registre/familles/boree.py`. Pas d'interface, pas de protocole : juste des imports.

---

## 5. Ce qui ne se transposé pas

### 5.1 Le domaine de la tension électrique FR/DE

| Element | Ou | Pourquoi c'est spécifique |
|---|---|---|
| Prix day-ahead FR et DE-LU, en EUR/MWh, au pas 15 min ou 1 h | `lac/catalogue.py:60-62`, `tables/horizon.py:80-85` | produit d'un marché unique europeen ; TORNE ne prédit pas de prix d'électricité |
| Seuil **T1** (pic) : prix horaire au-dessus du **95e centile des 365 jours** finissant à D-k | `tables/horizon.py:27-37, 82-83` ; `PROTOCOLE.md:17` | définition de cible propre au marché FR/DE ; le seuil lui-même est un **seuil EWL/RTE** |
| Seuil **T2** : prix <= 0 EUR/MWh | `tables/horizon.py:84` ; `PROTOCOLE.md:18` | idem |
| Zones `FR`, `DE-LU`, `BZN|FR`, `BZN|BE` | `lac/catalogue.py:62-78`, `tests/fabrique.py:24-25, 44-45` | nomenclature ENTSO-E |
| Modèles **H2** (référence publique), **H3** (Borée), **H4** (v2) | `PROTOCOLE.md:12-14, 67-85` ; `registre/boree-h2/h3/h4.toml` | variables, hyperparamètres et **empreintes de code** figés ; aucun rapport avec les objets de TORNE |
| Le **juge d'hiver** : e-processus aGRAPA, E = (E_J-3 + E_J-6)/2, e-LOND alpha = 0,03, seuil 33,3, usure e-CUSUM | `PROTOCOLE.md:35-48` ; `chaine/juger_hiver.py` | protocole de décision propre à la comparaison FR/DE |
| Le **test du printemps** (T2) et la **découverte de la valeur** | `PROTOCOLE.md:61-65` | idem |
| La **fiche du matin** : probabilité de pic > 0,5, au plus **trois heures** par jour, prix = profil calendaire + **50 EUR/MWh** x probabilité, seuil = prix de la nuit + **20 EUR/MWh** | `PROTOCOLE.md:107-122` ; `evaluation/fiche.py` | chiffrage d'exploitation propre à un site froid |
| L **empilement** : demande prévue, offre, marge, filière marginale, plancher de prix | `physique/empilement.py` | modèle physique du marché FR ; "l'Allemagne n'y est pas : il n'y a pas de production par filière allemande dans le store" (`PROTOCOLE.md:142-143`) |
| Le **contexte physique** : pression, refroidissement éolien, decroche tempête, angle zénithal | `PROTOCOLE.md:87-105` | grandeurseteorologiques expliquées, mais **hors modèle** |
| Le **marché EEX** : prix de règlement, adjudication, quota de CO2 | `marche.py`, `tables/quotas.py`, `PROTOCOLE.md:59` | marché spécifique |
| Les **niveaux de prix du gaz** (TTF) et des quotas (EUA) comme variables | `tables/horizon.py:40-54` | idem |
| Le **protocole scellé** : journées du 2026-04-28 au 2026-11-14, rodage 2026-11-15 -> 2026-11-30, test d'hiver 2026-12-01 -> 2027-03-31 | `PROTOCOLE.md:22-30` ; ADR 0003 | calendrier et enjeu propres à BOREE |

### 5.2 Remarques sur deux termes du mandat

- **"le front"** : dans le dépôt audite, le mot n'apparait que dans le paquet de référence V2.0, ou il signifie
  "Front minimal/existant" (un écran) et "Frontieres architecturales". Ce n'est pas un artefact de BOREE.
- **"l'EMM"** : la chaine `EMM` **n'apparait nulle part** dans le dépôt audite (recherche sur les `.py` et les `.md`).
  Je ne peux donc pas l'identifier ; je ne l'invente pas. Les équivalents les plus proches sont le flux
  `monde.json` (`docs/flux/monde.schema.json`) et le panneau `Monde` du frontend.

### 5.3 Pourquoi ces éléments ne se transposent pas -- la raison de fond

TORNE doit produire des connaissances **sur le monde réel** (reconstitution d'états, variables dérivées, prédictions)
puis des conséquences économiques et financières. Les éléments ci-dessus sont des **calibrages d'un marché unique** :
ils encodent une économie physique (offre, demande, prix marginal, quotas) et un calendrier de décision. Les transposer
reintroduirait dans TORNE un modèle du marché de l'électricité, ce qui est le contraire du besoin. Ce qui est
réutilisable, c'est la **machinerie** (point-in-time, lignage, catalogue, protocoles), pas les **valeurs**.

---

## 6. Licence, dépendances, versions, secrets

### 6.1 Licence : **inconnue**, et c'est bloquant

- `git ls-files` du dépôt audite, filtre `LICEN|COPYING|NOTICE` : **aucun résultat**. Il n'existe **aucun fichier de
  licence** dans `C:\Users\Romain\Documents\GitHub\boree\`.
- Meme vérification sur `C:\Users\Romain\Documents\GitHub\athanor` : **aucun fichier de licence**.
- La seule mention de licence dans les `.md` du dépôt audite porte sur les **données** (conditions d'usage des sources),
  pas sur le code.
- Consequence directe : selon la règle de `torne/docs/REUSE_AUDIT.md:33-34`, "la licence est notee **vérifiée** seulement
  si le fichier de licence a été lu ; sinon **inconnue**, et le composant est traité comme **non réutilisable en l'état**".
  **Aucun composant de BOREE n'est donc réutilisable en l'état.** C'est le premier filtre à appliquer à tout le tableau
  final, et il pousse mécaniquement vers `REIMPLEMENT` plutôt que `REUSE` pour ce qui doit quand même être repris.
- Pour `athanor` non plus : la licence est inconnue. A traiter de même.

### 6.2 Dépendances déclarées

`pyproject.toml` (`requires-python = ">=3.12"`):

| Dépendance | Version | Rôle | Licence |
|---|---|---|---|
| `athanor` | éditable, chemin `../athanor` | socle : hashing, rawstore, S3, statistiques, recherche | non vérifiée (absente) |
| `duckdb` | `>=1.1` | lecture de la forme Parquet du lac, sans serveur | non vérifiée ici |
| `eccodes` | `>=2.50.0` | codes météo GRIB | non vérifiée ici |
| `numpy` | `>=2.0` | calcul | non vérifiée ici |
| `openpyxl` | `>=3.1` | rapports d'enchères de quotas de CO2 (EEX) | non vérifiée ici |
| `pandas` | `>=2.2` | tables | non vérifiée ici |
| `pyarrow` | `>=16` | écriture Parquet | non vérifiée ici |
| `requests` | `>=2.31` | HTTP | non vérifiée ici |
| `scikit-learn` | `>=1.5` | classifieurs H3/H4 | non vérifiée ici |
| `yfinance` | `>=0.2.40` (extra `gaz`) | cotation TTF | non vérifiée ici |

Les licences des dépendances **n'ont pas été vérifiées dans ce poste** (les fichiers ne sont pas présents localement et
je n'ai pas eu à les lire) ; conformément à la règle de `REUSE_AUDIT.md`, elles restent **inconnues**.

### 6.3 `athanor` en dépendance éditable -- un risque à documenter

`pyproject.toml:28-29` :
```
[tool.uv.sources]
athanor = { path = "../athanor", editable = true }
```

Consequences :
- **Aucune contrainte de version** sur `athanor` : le code de BOREE peut appeler une API d `athanor` qui change, et
  rien ne le signale. Le couplage est **fort et muet**.
- `boree` **modifie** le comportement de `athanor` dans deux cas documentés :
  `exploitation/garage.py:3-7` (le `put` de `RawStore` envoie sur S3 au fil de l'eau, ce qui est contraire à la
  stratégie retenue par BOREE) et le régime `sync_s3=False`.
- `athanor` est donc **une dépendance éditable, pas une dépendance vérifiée**. Pour TORNE, la règle de
  `REUSE_AUDIT.md:84-86` ("Ce qui est repris est réécrit ou readapté dans TORNE, **jamais référence comme une
  dépendance externe**") impose de ne pas recopier ce schéma tel quel.
- `uv.lock` (273 033 o) verrouillé les versions des bibliothèques de calcul ; `uv` n'est **pas installé** sur ce poste.

### 6.4 Versions et reproductibilité

- Graine : **20261028** (`PROTOCOLE.md:81`) ; ajustements sous `threadpool_limits(1)` ; parallélisme par plis (`BOREE_JOBS`).
- Empreinte du store : `doctor.py:24-29` (SHA-256 de chaque `*.parquet` du store, hors scellés) -> `resultats/empreinte_store.json`.
- Empreinte du code : `PROTOCOLE.md:81-82` (`9a3c49dc...` pour 14 fichiers ; `516781b5...` pour `h4.py`).
- Empreinte des contrats : `registre/contrat.py` ; vérifiée par `boree verifier registre`.
- **Ce qui manque :** aucune trace d'exécution, aucun journal de décision horodaté (voir 3.4).

### 6.5 Secrets

- Règle : invariant 6 -- "Jamais dans le dépôt, les journaux, les sorties de commande ou les messages. Ils viennent de
  l'environnement (`ENTSOE_TOKEN`, `ATHANOR_S3_*`), sur le homelab dans `/etc/boree/boree.env` (640, root:boree). Une URL
  qui porte un jeton ne s'écrit jamais dans un journal."
- Vérifie dans le code : `archive.py:312-314` lit `ENTSOE_TOKEN` depuis l'environnement et, s'il est absent, **renvoie un
  message** au lieu d'échouer bruyamment ; `archive.py:459` idem pour `AGSI_KEY` ; `garage.py:32-38` lit `BOREE_S3`,
  `BOREE_S3_PREFIX` et `S3Config.discover()` (`ATHANOR_S3_ENDPOINT`, `ATHANOR_S3_KEY_ID`, `ATHANOR_S3_SECRET`).
- Cote voisin, `athanor.kernel.secrets` lit `<data>/secrets.toml` **hors git** ou les variables d'environnement, et
  "les valeurs ne sont jamais écrites dans un journal, un rapport ou un message d'erreur (`data.http` masque `api_key=`
  dans les URL)".
- **Aucun secret en clair** n'a été trouvé dans les fichiers que j'ai lus. `deploy/homelab/boree.env.exemple` est un
  exemple.
- **Point de vigilance pour TORNE :** la règle est écrite et appliquee par convention, mais je n'ai pas trouvé de
  **contrôle exécutable** qui echoue si un secret atterrit dans un journal ou un message d'erreur. C'est un candidat
  direct à un test automatique (voir 4.11).

---

## 7. Verdict par composant -- lecture rationale

Les décisions sont dans le tableau final (section 9). Trois principes les expliquent :

1. **Aucun composant n'est réutilisable en l'état** : pas de fichier de licence (6.1), et `REUSE_AUDIT.md:33-34` impose
   alors de traiter le composant comme non réutilisable. Quand le comportement est bon, la décision est donc
   `ADAPT` (réécrire en levant la licence) ou `REIMPLEMENT`, et `REUSE` ne peut être prononcé que pour un composant dont
   la **licence** serait établie -- ce qui n'est le cas d'aucun fichier de BOREE.
2. **Une grande partie du générique fait doublon avec `../athanor`**, qui est le socle naturel de TORNE : le magasin
   brut, le contrat de source, la compliance, la provenance, le registre d'hypothèses, les statistiques. Reprendre le
   code de BOREE serait recopier un doublon plus faible. La décision est `REJECT` avec la raison "fait double emploi",
   ce que `REUSE_AUDIT.md:61-63` prévoit explicitement.
3. **Le non-transposable est le domaine, pas la discipline.** Tout ce qui est un calibrage du marché FR/DE est
   `REJECT` sans hésitation ; tout ce qui est une discipline (point-in-time, lignage, catalogue, absence explicite,
   parité bit-a-bit, local-d-abord) est `ADAPT` et doit être reconstruit par TORNE sur ses propres objets.

---

## 8. Ce que je n'ai pas pu faire

| Limite | Detail | Consequence |
|---|---|---|
| **Suite de tests non exécutée** | `uv` absent du poste ; `python` disponible mais **3.14.3** sans `pandas`, `numpy`, `pyarrow`, `scikit-learn`, `eccodes` ni `athanor` (seuls `duckdb`, `requests`, `pytest` sont importables). Le projet exige `>=3.12` | **Aucun état de test n'est affirme.** Toutes les mentions « test X (n) » désignent des **tests existants**, dont je n'ai pas vérifie le résultat. Les états « implémenté et vérifie » signifient « couvert par un test nommé », pas « test passe » |
| **Marqueur `store`** | `pyproject.toml:41` déclare le marqueur `store` ("a besoin du store réel (`BOREE_STORE`)") | une partie des tests dépend d'un store que je n'ai pas ; je ne sais pas lesquels |
| **Historique git** | **accessible** : `C:\Users\Romain\AppData\Local\GitHubDesktop\app-3.6.10\resources\app\git\cmd\git.exe` fonctionne. 206 commits, branche `main`, HEAD `4b6d130ebc9068fbd7cba0de8611737a6d9cfc18` ("w2m update", Romain BAILLEUL, 2026-10-31) | j'ai pu confirmer des commit cites dans ce rapport ; je n'ai pas élargi à une lecture exhaustive de l'historique |
| **PREREG.md** | 275 154 octets ; seul l'en-tête des amendements a été extrait | le **contenu** des 48 amendements n'a pas été lu ; un amendement peut contenir une nuance qui contredit ce que je résumé |
| **Paquet de référence V2.0** | **zéro fichier de code** (recherche `*.py`, `*.js`, `*.ts`, `*.toml`, `*.sh` : aucun résultat) -- uniquement `.md`, `.yaml`, `.sql`, `.txt` | c'est une **spécification**, pas une implémentation : aucune de ses propositions n'est un composant existant. Je ne l'ai pas évaluée comme source de code |
| **`atanor` non installé** | le dépôt voisin existe (`src/`, `tests/`, `pyproject.toml`) mais le paquet n'est pas importable | j'ai évalué `athanor` par **lecture de ses en-têtes de modules** (10 modules lus) et par l'inventaire de ses 130+ modules, **pas par exécution** |
| **Depot audite non modifié** | aucune écriture, aucune commande mutante lancee dans `C:\Users\Romain\Documents\GitHub\boree\` | l'état audite est celui du commit `4b6d130` |
| **Preuve de lecture seule** | `git status --porcelain -- src tests docs PROTOCOLE.md PREREG.md PREREG_DE.md pyproject.toml registre deploy frontend` ne renvoie **rien** : le code audite est intact. HEAD est reste `4b6d130` du début à la fin | L'arbre de travail du dépôt audite contenait déjà des modifications **hors périmètre audite** (`BOREE_W2M_Greenfield_Reference_V2.0/**` et un `BOREE_W2M_AUDIT_2026-10-31.md` non suivi), horodatées **15:23:03**, soit **avant** le début de ma session (15:41). Elles ne sont pas de moi et ne concernent aucun fichier audite |
| **`docs/audit/ATHANOR.md`** | dans le dépôt cible, ce fichier ne contient que `PROBE` (8 octets) au moment de mon passage | mon rapport ne s'aligne pas sur un audit athanor existant : la comparaison de la section 2 repose sur ma propre lecture de `../athanor` |
| **Non vérifie** | licences des dépendances, état d'exécution des tests, résultats des études (`evaluation/*`), schémas JSON de `docs/flux/` | ces points sont explicitement marques comme non vérifiés |
---

## 9. Tableau final -- verdict par composant

Format impose par `torne/docs/REUSE_AUDIT.md` section 1. **Licence : inconnue pour tous les composants** (6.1) --
donc aucun n'est réutilisable en l'état.

| Composant | Chemin | État | Décision | Justification | Coût de reprise |
|---|---|---|---|---|---|
| Règles de disponibilité (point de vue décision) | `src/boree/temps.py` | I+ | **REJECT** | Hors périmètre explicite (`REUSE_AUDIT.md:88-89`) et contenu 100 % électrique ; le pattern, lui, est repris | Faible (pattern) |
| Lecture point-in-time `tel_que_connu` | `src/boree/lac/connu.py` | I+ | **ADAPT** | Mécanique générique ("telle que connue à t" = une requête, pas une copie) ; dépend de `temps.py`, donc a réécrire | Moyen |
| Catalogue déclaratif des jeux | `src/boree/lac/catalogue.py`, `docs/LAC.md` | I+ | **ADAPT** | La structure `Jeu` (règle nommée, granularité, publication, schéma) est domaine-indépendante ; le contenu est 100 % FR/DE | Moyen |
| Forme dérivée Parquet/DuckDB du lac | `src/boree/lac/parquet.py` | I+ | **ADAPT** | Brut = vérité, dérivé = reconstructible ; partitionnement `annee=/mois=`, DuckDB local sans serveur, réécriture atomique | Moyen |
| Magasin brut versionné, empreintes, `ref(asof=)` | `src/boree/archive.py` | I+ | **REJECT** | Doublon de `athanor.data.rawstore.RawStore`, qui pose même `known_at`, même point-in-time, en plus robuste | Faible (rien à recopier) |
| Copie S3 / Garage, intégrité, instantané | `src/boree/exploitation/garage.py` | I+ | **REJECT** | Le client S3 fait doublon avec `athanor.data.s3` ; **en revanche les trois règles sont à porter** (voir 2.10) | Faible |
| Règle "local d'abord, copie après" | `exploitation/garage.py:3-7` | I+ | **ADAPT** | "une panne de Garage retarde la copie, elle ne perd rien" -- contrainte d'architecture indépendante du domaine | Faible |
| Règle "intégrité par empreinte, jamais par décodage" | `exploitation/garage.py:12-13, 47-53` | I+ | **ADAPT** | Verification par hash sans ouvrir le document : s'applique tel quel à tout stockage scellé | Faible |
| Scelles et accès machine unique | `src/boree/scelles.py`, `final.py`, `direct.py` | I+ | **REJECT** | Code entièrement lié au protocole prospectif BOREE ; le **principe** (barriere unique, refusée par défaut, testée) est à porter | Moyen |
| Connecteurs ENTSO-E / Open-Météo / EEX | `src/boree/ingest/entsoe_api.py`, `ecmwf_direct.py`, `eua.py`, `europe.py`, `runs.py` | I+ | **REJECT** | Tous lies au marché de l'électricité ; le contrat de connecteur équivalent existe dans `athanor.data.source` | Nul |
| Modèle de collecteur (plan / collect / parse) | `ingest/sources.py` | I+ | **REJECT** | Doublon de `athanor.data.source` (+ `data/compliance.py` pour robots.txt et conditions d'usage) | Faible |
| Normalisation horaire (quarts -> heures, 2 h local) | `src/boree/temps.py:86-95` | I+ | **ADAPT** | Generique et testé ; à porter comme brique isolée, sans les règles de disponibilité | Faible |
| Registre d'unités et référentiel spatial | -- | **absent** | **REIMPLEMENT** | Aucun registre d'unités, aucun CRS, aucune géométrie dans le dépôt : BOREE n'apporte rien la | Élevé |
| Lignage 4 colonnes (`_source`,`_cle`,`_empreinte`,`_connu_a`) | `src/boree/lac/connu.py:32`, `lac/parquet.py:42-43` | I+ | **ADAPT** | Trivial, générique, et la preuve que la version et son instant de connaissance voyagent ensemble | Faible |
| Gel de la fermeture du code de mesure | -- | dans `athanor` | **REJECT** | `athanor.research.provenance` fait déjà mieux (fermeture transitive des imports, preuve d'équivalence, juge et environnement) | Nul |
| Registre de modèles (contrats TOML, statuts) | `src/boree/registre/contrat.py`, `registre/*.toml` | X | **REJECT** | Doublon de `athanor.research.registry`, qui est une machine à états rejouée depuis le journal et prévoit déjà `LEGACY_VERDICT -> ARCHIVED` | Faible |
| Methode de parité bit-a-bit + critère de bascule | `src/boree/registre/chaine.py:89-121` | X | **ADAPT** | "conforme / différente / non compare", `PARITE_MIN = 14/16`, aucun écart : méthode de migration saine, à réutiliser telle quelle | Faible |
| Controle du registre (empreintes, code de sortie 1) | `src/boree/registre/verifier.py` | X | **ADAPT** | Pattern "un contrôle exécutable qui sort en 1" à généraliser ; à réécrire sur le registre de TORNE | Faible |
| Chaine générique en ombre | `src/boree/registre/chaine.py` | X | **REJECT** | Experimental, lié à H2/H3/H4, et sa valeur est dans la méthode de parité (ligne du dessus) | Faible |
| Jumeau physique | `src/boree/physique/jumeau.py` | O | **REJECT** | Résultat retiré : "les chiffres étaient faux (production moyennee au lieu d'être sommée)" (`RESULTAT_jumeau.md`) | Nul |
| Empilement prévu au soir de J-1 | `src/boree/physique/empilement.py` | I+ | **REJECT** | Modèle physique du marché FR, explicitement "hors modèle" (`PROTOCOLE.md:144-145`) | Nul |
| Contexte physique (pression, decroche, angle zénithal) | `src/boree/physique/contexte.py` | I+ | **REJECT** | Hors gel et hors modèle ; TORNE n'a pas ces grandeurs | Nul |
| Geospatial et multidimensionnel | `physique/contexte.py`, `lac/connu.py:33` | I+ | **REIMPLEMENT** | Aucune géométrie ni CRS : la "géospatialité" de BOREE est un ensemble de chaînes de caracteres | Élevé |
| Tables de variables figées par horizon | `src/boree/tables/` | I+ | **REJECT** | Feature store figé pour H3, hors périmètre (`PROTOCOLE.md:180`) | Nul |
| Modèles H2 / H3 / H4 | `src/boree/modeles.py`, `chaine/modeles.py`, `registre/familles/` | I+ | **REJECT** | Variables, hyperparamètres et empreintes de code figés pour un marché spécifique | Nul |
| Juge d'hiver / test du printemps | `src/boree/chaine/juger_hiver.py`, `evaluation/juge.py` | I+ | **REJECT** | Protocole de décision FR/DE (e-LOND alpha 0,03, seuil 33,3) ; les statistiques, elles, viennent d `athanor.stats` | Nul |
| Fiche du matin | `src/boree/evaluation/fiche.py` | I+ | **REJECT** | Chiffrage propre au marché FR (50 EUR/MWh x probabilité, seuil nuit + 20 EUR/MWh) | Nul |
| Enveloppe de flux + schémas JSON | `src/boree/flux.py`, `docs/flux/` | I+ | **ADAPT** | Contrat machine-vérifiable + règle de l'absence explicite : modèle d'interface idéal pour la salle de TORNE | Moyen |
| Règle "un flux absent se dit, ne s'invente pas" | `PROTOCOLE.md:111-113, 139-140` | I+ | **ADAPT** | Règle d'interface, indépendante du domaine ; à porter tel quel | Faible |
| Flux vide type, instant jamais NaT | commits `c6290a9`, `725d2e0` | I+ | **ADAPT** | Discipline d'interface à porter | Faible |
| Salle de commandement (frontend Svelte, 9 écrans) | `frontend/` | I+ | **REJECT** | Contenus électricité ; le **patrimoine de tests** (fixtures `scelles`, `doublons`, Playwright) est en revanche un modèle | Nul |
| Codes de sortie d'exploitation (0/1/2/3) | `PROTOCOLE.md:162-165` | I+ | **ADAPT** | Quatre états de santé distincts, dont "un quota n'est pas une panne" : à porter | Faible |
| Distinction "série arretee" / "série qui decroche" | `PROTOCOLE.md:170-173`, `archive.py:83-87` | I+ | **ADAPT** | Un fait structurel vs un fait transitoire : à porter pour toute reconstitution d'état | Faible |
| Garde du périmètre gelé (`deploiement garder`) | `src/boree/exploitation/deploiement.py` | I+ | **ADAPT** | Un outil, pas une prière : le modèle du "refus outille" est le modèle à retenir (cf. commit `295edbf`) | Moyen |
| Revue de lancement (12 critères) | `src/boree/exploitation/lancement.py` (55 Ko) | I+ | **ADAPT** | Methode de revue pre-production ; le module lui-même est trop gros pour être repris | Moyen |
| Store synthétique anti-fuite | `tests/fabrique.py` | I+ | **ADAPT** | "chaque valeur encode sa date", réalisé interdit = -1 : la technique anti-fuite la plus directe observee | Moyen |
| Discipline du pre-enregistrement | `PREREG.md` + amendements dates | I+ (écrit) | **ADAPT** | La règle est forte et appliquee ; elle est **écrite**, pas outillee -> à outiller chez TORNE | Moyen |
| Un résultat publié ne se réécrit jamais | `docs/resultats/README.md:50-51` | I+ (écrit) | **ADAPT** | La discipline la plus transposable du dépôt, avec une preuve dans le dossier même | Faible |
| Paquet de référence greenfield V2.0 | `BOREE_W2M_Greenfield_Reference_V2.0/` | **D** | **REJECT** | Zero fichier de code : c'est une **spécification**, pas une implémentation ; ne peut pas être un composant | Nul |
| CLI `boree` et table `ETUDES` | `src/boree/cli.py` | I+ | **REJECT** | Structure de commande propre à BOREE (contrainte maison : pas de nouvelle commande de premier niveau) | Faible |
| Gestion des secrets | `archive.py:312-314`, `garage.py:32-38` | I+ | **REJECT** | Le principe est bon et applique, mais `athanor.kernel.secrets` le fait déjà (et `data.http` masque `api_key=` dans les URL) | Nul |
| Controle exécutable anti-secret dans les journaux | -- | **absent** | **REIMPLEMENT** | La règle invariant 6 est écrite et appliquee par convention, sans contrôle automatique | Faible |

---

## 10. Ce qui est transposable, a réécrire, à laisser

### 10.1 Transposable tel quel (comportement à reprendre, pas le code)

1. **Le store synthétique ou chaque valeur encode sa date** (`tests/fabrique.py`) -- la technique anti-fuite la plus
   directe : le test lit dans la variable de quel jour vient l'information.
2. **La règle "local d'abord, copie après"** : le réseau hors du chemin critique de l'écriture locale.
3. **La règle "intégrité par empreinte, jamais par décodage"**.
4. **Le contrat machine-vérifiable des flux** (un JSON Schema par flux) et la règle de l'absence explicite.
5. **La méthode de parité bit-a-bit** et le critère de bascule chiffre (`PARITE_MIN`).
6. **Le patron "un seul module dit ce qui est connu à la décision"** (autorite unique, règles nommées, jamais recopiées).
7. **La discipline du résultat publié** : on écrit à côté, on ne réécrit pas ; l'étude close se retire, son résultat reste.
8. **Les quatre états de santé de l'exploitation** (nominal / dégradé / impossible / relancable), dont "un quota n'est
   pas une panne".
9. **La distinction "structurel / transitoire"** pour l'absence de donnée.
10. **Le modèle de rejet** : une étude close dont le résultat ne sert plus à rien se retire.

### 10.2 A réécrire dans TORNE (le bon principe, le mauvais code)

1. **Le catalogue du lac** : même structure `Jeu`, mais avec les jeux et les règles de TORNE. C'est la brique
   **prioritaire**.
2. **Le lecteur point-in-time** : réécrit sur le socle TORNE, avec une règle de disponibilité par jeu et un test qui
   détecte toute règle dupliquee (le trou de BOREE, 3.4).
3. **La forme dérivée Parquet/DuckDB** : même format, même réécriture atomique, mais sur le magasin brut de TORNE.
4. **L'enveloppe de flux et les schémas** : pour la salle de commandement de TORNE.
5. **Le store synthétique anti-fuite** : à porter tel quel, et à étendre à chaque nouvelle source.
6. **La revue de lancement** : la méthode (12 critères, exercices), pas le module de 55 Ko.
7. **Le garde-fou de périmètre** : l'idée de `deploiement garder` -- un outil qui refuse, avec un test.
8. **Le pre-enregistrement** : la règle est bonne, mais elle n'est **pas outillee** chez BOREE. Chez TORNE, il faut
   un contrôle automatique : un amendement date et commité avant le premier calcul, vérifiable par un script.
9. **Le registre d'hypothèses** : n'utiliser **pas** le registre de BOREE ; utiliser `athanor.research.registry`, qui
   prévoit déjà la transition `LEGACY_VERDICT -> ARCHIVED` -- c'est le chemin natural pour adopter BOREE comme héritage.

### 10.3 A laisser (hors périmètre, sans discussion)

- Tout le contenu **électricité FR/DE** : prix day-ahead, seuils T1/T2 (95e centile 365 j, prix <= 0), zones FR/DE-LU,
  quotas EUA, TTF, marché EEX, bilan RTE eco2mix, avis d'indisponibilité EDF, debits Hub Eau.
- Les modèles **H2 / H3 / H4**, leurs hyperparamètres, leur graine et leurs empreintes de code.
- Le **juge d'hiver**, le test du printemps, les seuils e-LOND.
- La **fiche du matin** et son chiffrage (50 EUR/MWh, seuil nuit + 20 EUR/MWh).
- L **empilement** et le **contexte physique**, qui sont des observations du marché FR, hors chaine.
- Le **protocole scellé** lui-même (journées, rodage, test d'hiver) : il n'est ni modifié, ni extrait, ni réimplémenté
  (`torne/docs/REUSE_AUDIT.md:88-89`).
- Le **paquet de référence V2.0** : une spécification sans code, sans valeur de composant.
- La **salle de commandement BOREE** (frontend et contenus) : TORNE aura la sienne.

### 10.4 Les cinq questions à poser à TORNE, que BOREE repond mal

1. **Comment éviter le double comptage entre une reconstitution d'état et une conséquence économique ?** BOREE ne se pose
   pas la question : elle a un seul sens de lecture (le prix). TORNE en à deux (le monde, puis l'argent).
2. **Comment garantir qu'une conséquence financière n'utilise que des états connus à la date de la décision ?** La
   discipline de `temps.py` repond à cette question pour le prix ; elle doit y répondre **une fois**, pour tout
   TORNE, avant tout modèle.
3. **Que vaut une observation absente dans une chaine aval ?** BOREE distingue "absent" et "non tente" (commit
   `58a99dd`) ; TORNE doit propager cette distinction dans les contrats d'interface aval.
4. **Comment rendre une décision opposable ?** BOREE à le juge d'hiver ; TORNE a `athanor.research.registry` et
   `research/protocol.py` (protocole écrit et figé **avant** de voir les données qui jugent). Il faut utiliser le socle
   voisin, pas reconstruire.
5. **Comment garantir qu'une règle critique ne soit pas seulement écrite ?** C'est le thème du commit `295edbf` : une
   règle d'interdiction que rien n'applique est une règle que l'on croit avoir.

---

## Annexe A -- Commandes de vérification utilisées

```
git -C .../boree log --oneline -20 ; rev-list --count HEAD ; branch --show-current
git -C .../boree ls-files | Select-String 'LICEN|COPYING|NOTICE'      -> vide
git -C .../athanor ls-files | Select-String 'LICEN|COPYING'           -> vide
Get-ChildItem .../boree/src/boree -Recurse -Filter *.py                -> 81 fichiers
Get-ChildItem .../boree/tests -Filter test_*.py                        -> 48 fichiers, 457 fonctions
Get-ChildItem .../boree/docs -Directory                                -> adr(3) chantiers(16) europe(1) flux(11) resultats(30)
glob .../BOREE_W2M_Greenfield_Reference_V2.0 **/*.{py,js,ts,toml,sh}  -> aucun resultat
python -c "import importlib.util ..."                                 -> pandas/numpy/pyarrow/sklearn/eccodes/athanor ABSENTS
Get-Command uv                                                        -> absent
```
