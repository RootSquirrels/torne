# TORNE — Rapport P0 : socle d'ingénierie

**Mission :** P0 — Socle d'ingénierie (`docs/PROGRAMME.md`, section P0).
**Date :** 31 octobre 2026.
**Référence Git :** `7153a2966385e417102eebe3fd8658f5fbb460a5` (`7153a29`), branche `main`, remote
`https://github.com/RootSquirrels/torne.git`.
**Aucun commit n'a été fait** : ce rapport, les fichiers modifiés et le verrou sont laissés en
l'état de travail, le commit revient au principal.

---

## 1. Modifications apportées

| Fichier | Rôle de la modification |
|---|---|
| `pyproject.toml` | Version de référence Python 3.12 explicitée ; **huit dépendances runtime retirées** (aucune n'était importée) ; `required-version = ">=0.13.6"` ajouté pour `uv` ; reste du fichier inchangé (Hatchling, `src/` layout, pytest, ruff). |
| `uv.lock` | Verrou **régénéré** (`uv lock`) : 32 paquets → **8** (pytest, ruff et leurs dépendances). Toujours versionné, toujours non ignoré. |
| `.github/workflows/ci.yml` | **Nouveau.** Gate P0 en GitHub Actions : Python 3.12, `uv` épinglé, synchronisation depuis le verrou, ruff (check + format), pytest, construction du paquet, installation du paquet construit. |
| `README.md` | Sections « Installation et tests » (commandes réellement exécutées) et « Qualité » (nouvelle) ; en-tête « État réel », « Arborescence » et « État du projet » mis à jour. Les formulations conditionnelles (« ces commandes n'ont pas été exécutées ») sont supprimées. |
| `docs/P0-RAPPORT.md` | **Nouveau.** Le présent rapport. |
| `.gitignore` | **Inchangé** : il couvrait déjà `.venv/`, `__pycache__/`, `*.py[cod]`, `.pytest_cache/`, `.ruff_cache/`, `dist/`, `build/`, `*.egg-info/`, `.env*`. `uv.lock` n'y figure pas et n'y doit pas figurer. |
| `src/torne/`, `tests/` | **Inchangés.** Aucun code n'a été ajouté ni modifié : il n'y a aucun modèle à tester, et fabriquer du code pour faire passer un test est exclu par le programme. |

Fichiers lus mais **non modifiés** (hors périmètre) : `docs/PROGRAMME.md`, `MISSION.md`,
`docs/DECISIONS.md`, `docs/REUSE_AUDIT.md`, `docs/SLICE-PREMIER.md`, `docs/VISION.md`,
`docs/ARCHITECTURE.md`, `docs/RESEARCH_AND_VALIDATION.md`, `docs/audit/`.

### Audit préalable — ce qui a été trouvé

- **HEAD réel :** `7153a2966385e417102eebe3fd8658f5fbb460a5`, identique à la référence `7153a29`
  annoncée dans le programme. Un seul commit dans l'historique, branche `main` suivant
  `origin/main`, aucune autre branche locale.
- **État Git au départ :** `M docs/DECISIONS.md`, `M docs/REUSE_AUDIT.md` (modifications d'autres
  agents, hors périmètre, laissées intactes), `?? docs/PROGRAMME.md` (hors périmètre),
  `?? uv.lock` (non encore versionné).
- **`git` n'est pas dans le `PATH` du poste.** Les commandes Git ont été passées par le binaire de
  GitHub Desktop : `C:\Users\Romain\AppData\Local\GitHubDesktop\app-3.6.10\resources\app\git\cmd\git.exe`.
- **Outillage :** `uv` 0.13.6 à `%APPDATA%\Python\Python314\Scripts\uv.exe` (hors `PATH`), Python
  système 3.14.3, et **un Python 3.12.3 déjà installé**
  (`C:\Users\Romain\AppData\Local\Programs\Python\Python312`). Le réseau fonctionne :
  `uv python install 3.12` a téléchargé le Python 3.12.16 managé (21 Mio, 6,95 s).
- **Verrou :** `uv.lock` n'est pas ignoré (`git check-ignore -v uv.lock` → code 1) ; il est donc
  visible par `git status` et versionnable.
- **Dépendances :** les huit dépendances runtime déclarées n'étaient importées par aucun module.
  `src/torne/__init__.py` et `tests/test_package.py` n'utilisent que la bibliothèque standard.
- **Hygiène :** balayage de motifs (`api_key`, `secret`, `password`, `token`, `bearer`, `AKIA`,
  `ghp_`, clé privée, URL porteuse d'identifiants) sur tout l'arbre : **aucun secret en clair**,
  seulement des mentions textuelles dans les documents. Aucun jeu de données ; `experiments/`
  ne contient qu'un `README.md`.
- **Artefacts :** `__pycache__/` (dans `src/torne/` et `tests/`), `.pytest_cache/` et `.ruff_cache/`
  étaient présents physiquement dans l'arbre de travail — bien qu'ignorés par Git, ils ont été
  **supprimés physiquement** (`mavis-trash`, suppression récupérable). Le `.venv/` et le `dist/`
  restent ignorés.

---

## 2. Commandes exécutées — sortie réelle et code de retour

### 2.1 Avant toute modification (état de départ, Python 3.14.3)

Reproduction des mesures annoncées par le principal, **plus `uv build`, qui n'avait jamais été
testé** :

| Commande | Sortie réelle | Code |
|---|---|---|
| `uv sync --locked` | (aucune sortie) | 0 |
| `uv run pytest -q` | `..  [100%]` / `2 passed in 0.02s` | 0 |
| `uv run ruff check .` | `All checks passed!` | 0 |
| `uv run ruff format --check .` | `15 files already formatted` | 0 |
| `uv build` | `Building source distribution...` / `Building wheel from source distribution...` / `Successfully built dist\torne-0.1.0.tar.gz` / `Successfully built dist\torne-0.1.0-py3-none-any.whl` | **0** |

`uv build` **passe** : ce n'était pas un point de blocage.

### 2.2 Après modification — gate complet sur Python 3.12

Interpréteur de référence : `CPython 3.12.3` (`C:\Users\Romain\AppData\Local\Programs\Python\Python312\python.exe`),
mode `UV_PYTHON_PREFERENCE=only-system` (identique à la configuration CI).

| Commande | Sortie réelle | Code |
|---|---|---|
| `uv sync --locked` | `Resolved 8 packages in 1ms` / `Checked 8 packages in 2ms` | 0 |
| `uv run pytest -q` | `..  [100%]` / `2 passed in 0.03s` | 0 |
| `uv run ruff check .` | `All checks passed!` | 0 |
| `uv run ruff format --check .` | `16 files already formatted` | 0 |
| `uv build` | `Building source distribution...` / `Building wheel from source distribution...` / `Successfully built dist\torne-0.1.0.tar.gz` / `Successfully built dist\torne-0.1.0-py3-none-any.whl` | 0 |
| `uv run python -c "import torne; print(torne.__version__)"` | `0.1.0` | 0 |

Le passage de 15 à 16 fichiers comptés par ruff vient de `docs/CONTRATS_FONDAMENTAUX.md`, créé
pendant la mission par l'agent P2-A — pas d'un artefact.

### 2.3 Verrou

| Commande | Sortie réelle | Code |
|---|---|---|
| `uv lock` | `Resolved 8 packages in 19ms` puis 24 paquets retirés (dont `numpy 2.5.4`, `pandas 3.1.0`, `pyarrow 26.0.0`, `duckdb 2.0.0`, `scikit-learn 1.9.1`, `scipy 1.18.1`, `requests 2.34.2`, `pyyaml 6.0.3`, `pydantic 2.14.2`) | 0 |
| `uv python install 3.12` | `Downloaded cpython-3.12.16-windows-x86_64-none (download)` / `Installed Python 3.12.16 in 6.95s` | 0 |
| `uv sync --locked` (Python managé) | `Using CPython 3.12.16` → `Installed 8 packages in 493ms` | 0 |
| `uv sync --locked` (`only-system`) | `Using CPython 3.12.3 interpreter at: ...\Python312\python.exe` → `Installed 8 packages in 496ms` | 0 |
| `git check-ignore -v uv.lock` | (aucune correspondance) — exit 1 = **non ignoré**, donc versionnable | 1 (attendu) |

### 2.4 Installation propre du paquet construit

Preuve que le wheel produit par `uv build` s'installe et fonctionne hors du dépôt — la même
séquence que celle exécutée par la CI, validée sur Windows :

| Commande | Sortie réelle | Code |
|---|---|---|
| `uv venv --python 3.12 <jetable>` | `Using CPython 3.12.3 interpreter at: ...` / `Creating virtual environment at: ...` | 0 |
| `uv pip install --python <jetable>\Scripts\python.exe dist\torne-0.1.0-py3-none-any.whl` | `Resolved 1 package in 5ms` / `Prepared 1 package in 19ms` / `Installed 1 package in 27ms` / `+ torne==0.1.0 (from ...dist\torne-0.1.0-py3-none-any.whl)` | 0 |
| `<jetable>\Scripts\python.exe -c "import torne; print('import ok', torne.__version__)"` | `import ok 0.1.0` | 0 |
| `<jetable>\Scripts\torne.exe` | `torne 0.1.0 — socle documentaire (aucun modèle implémenté)` | 0 |

Contenu du wheel (5 entrées) : `torne/__init__.py`, `torne-0.1.0.dist-info/METADATA`,
`WHEEL`, `entry_points.txt`, `RECORD`. Contenu de la sdist : **19 entrées**, aucun artefact
Python, aucun secret — `MISSION.md`, `README.md`, `pyproject.toml`, `uv.lock`, `src/`, `tests/`,
`docs/`, `experiments/`.

### 2.5 Workflow CI

| Contrôle | Sortie réelle | Code |
|---|---|---|
| Analyse YAML de `.github/workflows/ci.yml` (parseur Python, hors projet) | `YAML OK` / `jobs: ['quality']` / `etapes: ['actions/checkout@v4', 'python 3.12', 'uv', 'dépendances (verrou tel quel)', 'ruff', 'pytest', 'construction du paquet', "le paquet construit s'installe et s'importe"]` | 0 |

**Le workflow n'a pas été exécuté** : il n'existe aucune preuve de son exécution, et il ne
tourera qu'à la première poussée sur `main`.

---

## 3. Décisions prises

### 3.1 Version de Python : 3.12 (le plancher)

`requires-python = ">=3.12"` est conservé tel quel ; 3.12 est déclaré comme **version de
référence** (ruff `target-version = "py312"`, CI sur 3.12). Motifs :

- Le programme impose de ne pas dépasser le plancher sans besoin démontré, et le plancher est
  3.12.
- Le verrou reste **multi-version** : `requires-python = ">=3.12"` dans `uv.lock`, donc 3.13 et
  3.14 restent valides pour un poste de travail.
- La CI sur 3.12 est le cas le plus contraignant : c'est là que les incompatibilités se voient.
- Vérifié, pas supposé : synchronisation et gate complet passés sous **3.12.3** (système) et
  **3.12.16** (managé par `uv`). Aucun téléchargement n'a été nécessaire pour 3.12.3 : il était
  déjà installé.

### 3.2 Dépendances : les huit retirées

Le code actuel n'importe **aucune** des huit dépendances runtime déclarées
(`numpy`, `pandas`, `pyarrow`, `duckdb`, `scikit-learn`, `requests`, `pyyaml`, `pydantic`) :
`src/torne/__init__.py` et `tests/test_package.py` n'utilisent que la bibliothèque standard.
Leur justification initiale était « une capacité démontrée dans au moins deux documents du
paquet de référence V2.0 » — c'est-à-dire, littéralement, le motif que le programme proscrit
(« ne pas installer une bibliothèque simplement parce qu'elle apparaît dans un document
d'architecture »), et que le gate P0 qualifie (« absence de dépendances inutilisées »).

Décision : `dependencies = []`. Le paquet n'utilise que la bibliothèque standard, ce qui est
exact. Chaque bibliothèque reviendra **au moment du premier import réel**, jamais avant :

| Bibliothèque | Phase de retour | Besoin |
|---|---|---|
| `requests` | P1→P2-B | Acquisition HTTP des sources publiques (USDA, USACE, USGS). |
| `pyyaml` | P2-A→P2-B | Déclaration lisible et versionnée des contrats. |
| `pydantic` | P2-A→P2-B | Validation des contrats d'objets. |
| `pyarrow` | P2-B | Schéma colonnaire et Parquet pour le magasin brut. |
| `duckdb` | P2-B | Requête analytique locale sur Parquet. |
| `numpy`, `pandas` | P2 | Calcul numérique et données tabulaires, si un besoin concret apparaît. |
| `scikit-learn` | À instruire | Le noyau statistique viendra d'`athanor.stats` (réécriture) : l'utilisateur de `scikit-learn` n'est même pas acquis. |

Conséquences assumées :

- `docs/DECISIONS.md` (hors périmètre, appartient au principal) contient une décision datée du
  2026-10-31, « **Huit dépendances**, ancrées par capacité et non par convention », qui devient
  **caduque**. Elle n'a pas été amendée ici : ce journal n'est pas dans mon périmètre.
- Le verrou passe de 32 à 8 paquets : installation plus rapide, surface de CI plus faible,
  moins de « resolving markers » multi-plateforme dans `uv.lock`.
- Le programme garde son orientation (« réutiliser les bibliothèques scientifiques éprouvées
  avant de réimplémenter les mathématiques ») : elle s'applique au moment d'écrire le code, pas
  au moment de le garnir de bibliothèques non utilisées.

### 3.3 `uv` : version minimale déclarée

`[tool.uv] required-version = ">=0.13.6"` est ajouté. Le verrou commité porte `revision = 5`,
qu'un `uv` plus ancien ne sait pas lire : mieux vaut un refus explicite qu'une reproduction
supposée.

### 3.4 Forme du workflow CI

GitHub Actions, puisque le dépôt est hébergé sur `github.com/RootSquirrels/torne`. La structure
suit l'infrastructure de référence du propriétaire (`boree/.gitea/workflows/ci.yml`) : version
d'`uv` épinglée en variable d'environnement et installation par le script officiel,
synchronisation **depuis le verrou**, ruff, pytest. **Ni les secrets ni le job « application »
(Node/Playwright) n'ont été repris** : TORNE n'a pas d'interface.

Écarts assumés par rapport au workflow Gitea de référence :

- `actions/setup-python@v5` installe le 3.12 (le runner Gitea a un Python système) ;
  `UV_PYTHON=3.12` et `UV_PYTHON_PREFERENCE=only-system` garantissent qu'`uv` utilise exactement
  cet interpréteur, sans téléchargement managé. Configuration **validée localement**.
- `uv sync --locked` est preferred à `--frozen` : `--locked` échoue si `pyproject.toml` et
  `uv.lock` divergent, c'est-à-dire s'il y a dérive des dépendances.
- Le job ne comporte ni matrice de versions Python, ni seuil de couverture, ni déploiement.
- Une étape supplémentaire : après `uv build`, le wheel est **installé dans un environnement
  jetable hors du dépôt** (`$RUNNER_TEMP`), puis importé et exécuté. Construire ne prouve pas que
  l'artefact s'installe ; cette étape le prouve. La séquence a été validée localement.
- Les actions sont épinglées par version majeure (`@v4`, `@v5`), comme dans la référence du
  propriétaire ; le script d'installation d'`uv` est **épinglé par version** (`0.13.6`), qui est
  celle qui a produit le verrou.

### 3.5 Autres décisions

- **Pas de LICENSE** : consigne du programme (dépôt privé, propriété intellectuelle gérée
  séparément).
- **`.gitignore` inchangé** : il couvrait déjà tous les artefacts exigés.
- **Aucun fichier `.python-version`** : hors périmètre. Le 3.12 est piloté par `requires-python`
  et par `UV_PYTHON` en CI.

---

## 4. Limitations constatées

- **La CI n'a pas été exécutée.** Le workflow est écrit et syntaxiquement valide, rien de plus :
  aucune preuve de son exécution n'existe. Il ne tournera qu'à la première poussée.
- **`git` absent du `PATH`** du poste : les commandes Git ont été passées par le binaire de
  GitHub Desktop. Sans incidence sur le dépôt, mais à savoir pour qui reproduira l'audit.
- **`ruff format` et le Markdown** : ruff 0.17.3 (version épinglée par le verrou) compte les
  fichiers `.md` dans son décompte mais ne les formate pas hors mode preview —
  `ruff format --diff <fichier.md>` échoue avec « Markdown formatting is experimental, enable
  preview mode ». Le gate (`--check`) passe ; aucun formatage Markdown n'est donc appliqué.
- **`uv build` a été validé sous Windows**, pas sous Linux : le comportement de la CI sur
  `ubuntu-latest` est attendu mais non exécuté.
- **La sdist embarque le dépôt** (19 entrées : documentation, tests, verrou). C'est le
  comportement standard de Hatchling ; aucun artefact ni secret n'y figure, vérifié par
  `tar -tzf`. Le wheel, lui, ne contient que le paquet.
- **`uv build` écrit `dist/`** dans l'arbre de travail (ignoré par Git).
- **Python 3.12.16 managé** a été téléchargé par `uv` (21 Mio) pour vérifier le cas « Python
  managé ». Le cas « Python système » (3.12.3) a été vérifié séparément, et c'est celui retenu
  pour la CI.

---

## 5. Tâches non réalisées

- **Aucun commit, aucun `git add`, aucun `git push`** : le principal commite.
- **`docs/DECISIONS.md` non amendé** (hors périmètre) alors que la décision datée « huit
  dépendances » du 2026-10-31 est caduque : à amender par son propriétaire.
- **La CI n'a pas été exécutée** (impossible avant une poussée) : le rapport ne revendique rien
  sur son comportement réel.
- **Pas de `LICENSE`** (consigne).
- **Pas de `.python-version`** (hors périmètre).
- **Aucun code métier, aucun test de modèle** : il n'existe aucun modèle à tester. Aucun code n'a
  été fabriqué pour faire passer un test.

---

## 6. Commandes exactes pour reproduire le gate

Sur ce poste, `uv` n'est pas dans le `PATH` :

```powershell
$env:PATH = "$env:APPDATA\Python\Python314\Scripts;$env:PATH"
Set-Location C:\Users\Romain\Documents\GitHub\torne
```

Gate P0, dans l'ordre du programme :

```powershell
uv sync --locked
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv build
```

Pour reproduire **exactement** l'interpréteur de la CI (Python 3.12 système, sans téléchargement
managé) :

```powershell
$env:UV_PYTHON = '3.12'
$env:UV_PYTHON_PREFERENCE = 'only-system'
```

Vérification complémentaire de l'installation du paquet construit (équivalent de la dernière
étape de la CI, adaptée à Windows) :

```powershell
uv build
uv venv --python 3.12 "$env:TEMP\torne-verif"
uv pip install --python "$env:TEMP\torne-verif\Scripts\python.exe" (Get-ChildItem dist\*.whl)[0].FullName
& "$env:TEMP\torne-verif\Scripts\python.exe" -c "import torne; print(torne.__version__)"
& "$env:TEMP\torne-verif\Scripts\torne.exe"
```

Sous Linux (comme dans la CI) :

```bash
uv sync --locked
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv build
uv venv --python 3.12 "$RUNNER_TEMP/verif"
uv pip install --python "$RUNNER_TEMP/verif/bin/python" "$(ls dist/*.whl)"
"$RUNNER_TEMP/verif/bin/python" -c "import torne; print(torne.__version__)"
"$RUNNER_TEMP/verif/bin/torne"
```
