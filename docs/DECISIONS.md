# TORNE — Journal des décisions

**31 octobre 2026.** Ce journal est court et daté. Ce n'est pas une série d'ADR : un ADR formel ne sera écrit que pour
une décision structurante, non évidente et susceptible d'évoluer. Les choix de programmation ordinaires restent ici.

| Date | Décision | Motif | Statut |
|---|---|---|---|
| 2026-10-31 | La plateforme s'appelle **TORNE**. | Le fleuve Torne était un axe de commerce et de transport ; connaître la date de sa débâcle était une information concrètement utile, devenue archive climatique exploitable. Le nom dit le trajet complet, de la physicalité à la connaissance, sans nommer le domaine ni promettre un usage. | Actif |
| 2026-10-31 | **Repository neuf et indépendant** ; les dépôts historiques restent en lecture seule. | Aucune fusion, aucune migration globale, aucune copie de répertoire depuis `boree`, `athanor` ou `SquirrelBetting`. Ce qui est repris est réécrit ou réadapté dans TORNE, jamais référencé comme une dépendance. | Actif |
| 2026-10-31 | Le paquet `BOREE_W2M_Greenfield_Reference_V2.0` est retenu comme **référence conceptuelle** ; son implémentation est **reportée**. | Le paquet est une spécification de conception, pas une implémentation. Il fixe la thèse, les frontières et le vocabulaire, mais il ne prouve l'existence d'aucun connecteur, modèle, méthode ou résultat. On s'en sert comme référentiel, on ne le transpose pas. | Actif |
| 2026-10-31 | **Python 3.12+**, environnement verrouillé par `uv`, tests avec **pytest**, linting et formatage avec **ruff**. | Python est l'écosystème scientifique dominant et permet de réutiliser les bibliothèques éprouvées plutôt que de réimplémenter les mathématiques. `uv` fournit un verrou reproductible. `pytest` et `ruff` couvrent le besoin de vérification sans introduire d'outillage supplémentaire. | Actif |
| 2026-10-31 | **Aucune performance n'est démontrée.** | Le dépôt ne contient ni modèle, ni données, ni évaluation. Toute affirmation chiffrée serait infondée. Le README et la vision distinguent explicitement ce qui est construit de ce qui est envisagé. | Actif |
| 2026-10-31 | Aucun moteur, service, registre, bus, graphe ni répertoire de packages vides n'est créé. | Une abstraction n'est justifiée que par un problème réel ou un besoin de réutilisation démontré. Les sous-packages vides sont une architecture cible, pas une capacité. | Actif |
| 2026-10-31 | **Aucune dépendance runtime dans le tout premier socle.** | Correction du 31 octobre, après le rapport P0 : les huit dépendances annoncées n'étaient importées par aucun fichier du paquet, et leur justification (« une capacité démontrée dans deux documents du paquet V2.0 ») était exactement le motif que le programme proscrit — une bibliothèque parce qu'elle apparaît dans un document. Elles sont retirées, le verrou passe de 32 à 8 paquets, et elles reviendront **au premier import réel**. Ear marking : `requests` → acquisition (P1/P2-B) ; `pyyaml`, `pydantic` → contrats ; `pyarrow`, `duckdb` → Parquet (P2-B) ; `numpy`, `pandas` → P2 si besoin ; `scikit-learn` → à instruire, le noyau statistique venant d'`athanor.stats`. | Actif |
| 2026-10-31 | **Le noyau statistique sera repris d'`athanor.stats`**, une fois la licence clarifiée. | Douze primitives sont implémentées et testées contre les définitions publiées : e-processus et suites de confiance, e-LOND et budget d'alpha, multiplicité (FWER/FDR/Romano-Wolf), sur-apprentissage (SPA/PBO/DSR), puissance, calibration et Diebold-Mariano, intervalles de proportion, CUPED, scoring, CUSUM, régression. C'est le juge dont TORNE a besoin, et il existe déjà. | **Bloqué par la licence** |
| 2026-10-31 | **Un seul magasin brut, un seul registre de modèles, un seul contrat de connecteur, une seule gestion de secrets.** | L'archéologie établit que ces quatre besoins ont été construits deux fois : `athanor.data.rawstore` / `boree.archive.py`, `athanor.research.registry` / `boree.registre`, `athanor.data.source` / `boree.ingest.sources`, `athanor.kernel.secrets` / `boree.archive.py:312-314`. TORNE n'en adoptera qu'une version — celle d'Athanor, plus robuste — et n'en réécrira aucune avant d'avoir un besoin propre. | Actif |
| 2026-10-31 | **Le store synthétique anti-fuite est posé dès la première table.** | La technique de l'ancien BORÉE — chaque valeur du store encode sa date, le réalisé interdit vaut −1 — est la plus directe qui ait été observée. Elle est le garde-fou du point de vue à la décision, et il n'y a pas de table sans lui. | Actif |
| 2026-10-31 | **Le pré-enregistrement sera outillé**, pas seulement écrit. | L'ancien BORÉE écrit la discipline (amendements datés, notes de résultat) mais ne l'outille pas ; C.R.I.N. l'outille (gates, kill-switch, statut) mais sur une autre forme. TORNE prend les deux : la forme d'amendement daté, l'outillage de gate. | Actif |
| 2026-10-31 | **Le premier slice vertical est le Mississippi**, pas le Rhin. | Décision du critère le plus rare : la disponibilité d'un témoin économique **public** à fréquence infra-mensuelle sur toute la période. L'USDA/AMS publie des taux de fret fluvial aval hebdomadaires depuis 2004 sur sept tronçons du Mississippi, et les tonnages hebdomadaires par écluses. Sur le Rhin, tous les témoins infra-mensuels sont commerciaux et les publics sont annuels ou trimestriels — un témoin trimestriel ne date pas un décalage de quelques semaines. Détail : `docs/SLICE-PREMIER.md`. | **Proposition — attend la décision du propriétaire** |
| 2026-10-31 | **La décision « refus outillé » est retenue comme patron.** | `boree deploiement garder` et `athanor.tools.guardrails` sont deux implémentations du même principe : un script refuse une modification hors périmètre. Le principe est repris ; les règles sont réécrites sur les invariants de TORNE. | Actif |
| 2026-10-31 | **Python 3.12 est la version de référence** ; le verrou reste multi-version. | 3.12 est le plancher déclaré, donc le seul cas contraignant. Le gate a été rejoué sous 3.12.3 système **et** 3.12.16 managé par `uv` : `uv sync --locked`, `pytest`, `ruff check`, `ruff format --check` et `uv build` passent à 5/5, et le paquet construit s'installe dans un environnement vierge. | Actif |
| 2026-10-31 | **CI GitHub Actions**, strukturée d'après le workflow Gitea de l'ancien `boree`. | Le dépôt est hébergé sur `github.com/RootSquirrels/torne` : c'est donc GitHub Actions qui s'exécute, pas Gitea. La structure de référence du propriétaire (version d'`uv` épinglée, synchronisation depuis le verrou, ruff, pytest) est reprise, sans ses secrets ni le job Node/Playwright. **Le workflow est écrit et syntaxiquement validé, mais il n'a pas été exécuté** : il ne tournera qu'à la première poussée. | Actif |
| 2026-10-31 | **`known_at` désigne la publication dans la source**, et non notre ingestion. | Piège de nommage vérifié dans le code d'Athanor : `athanor.kernel.clock` appelle `known_at` l'instant de **notre** ingestion. Reprendre le magasin tel quel inverserait la sémantique point-in-time **sans qu'aucun test ne casse**. La table de correspondance est posée dans `docs/CONTRATS_FONDAMENTAUX.md` ; le nom d'Athanor est refusé. | Actif |
| 2026-10-31 | **`usable_at` est une fonction dérivée, jamais un champ stocké** : `max(KNOWN_AT, INGESTED_AT)`. | Un `usable_at` stocké se dégrade silencieusement : il devient un fait figé au lieu d'une règle. La dérivation rend la sémantique visible et la permet de changer sans migration. | Actif |
| 2026-10-31 | **Le volet hippique, PMU, pool odds, Kelly, settlement et les 43 adaptateurs de domaine sont écartés.** | Aucun rapport avec la reconstitution d'états physiques. Trois *principes* sont conservés : le règlement au moment de vérité, l'évaluation sur l'information disponible à la décision, la discipline de gate. | Actif |

## Points ouverts

Ces points ne sont pas tranchés et ne doivent pas être présentés comme acquis.

- **Licence d'Athanor** : le dépôt `athanor@6dacc87` ne contient **aucun fichier de licence**. Tant que ce point n'est
  pas réglé, les décisions `REUSE` de `docs/REUSE_AUDIT.md` signifient « à réutiliser après clarification ». C'est le
  blocage numéro un.
- **`uv.lock`** : non généré au premier commit. `uv` a été installé depuis (0.13.6, portée utilisateur) ; le verrou est
  produit par `uv lock` puis commité, `uv.lock` étant volontairement versionné.
- **Installation, tests et linting** : non exécutés au premier commit, faute d'`uv` sur le poste de construction. Les
  commandes attendues sont `uv sync --locked`, `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .`
  et `uv build`.
- **Licence du dépôt TORNE** : non choisie. Le dépôt est privé ; aucune licence n'est ajoutée automatiquement, la
  politique de propriété intellectuelle est gérée séparément.
- **Statut juridique d'`athanor`** : **close**. Dépôt privé du propriétaire : son code est réutilisable sans réserve,
  et les décisions `REUSE` de `docs/REUSE_AUDIT.md` sont actionnables. Ce qui reste demandé, c'est de la **traçabilité** :
  chaque brique reprise laisse une trace de son origine dans ce journal.
- **Procédure de calcul de `usable_at`** : c'est la décision qui manque le plus. Sans elle, la sémantique
  point-in-time n'est pas implémentable, et le slice ne peut pas démarrer.
- **Registre d'unités et référentiel spatial** : absent de tous les dépôts audités. À créer de zéro, avec une
  géométrie et un CRS — le « géospatial » de l'ancien BORÉE n'est qu'un ensemble de chaînes de caractères.
- **Point d'entrée console `torne`** : provisoire. Il énonce l'état du paquet et sera remplacé par le premier slice
  vertical ; il ne contient aucun code métier.
- **Temporalité** : les conventions temporelles propres à TORNE restent à définir. Les règles du protocole scellé
  Borée H3 sont hors périmètre et ne sont pas reprises.
