# Expériences

Ce répertoire accueille des scripts d'exploration jetables : analyses exploratoires, tests
rapides d'hypothèses, comparaison d'options, petites simulations de faisabilité.

Ce qui n'y entre pas :

- tout ce qui est destiné à devenir un prototype de production — ce code-là appartient dans
  `src/torne/`, avec ses tests ;
- les données et les secrets, qui restent hors du dépôt et ne sont référencés que par leur
  provenance ;
- les résultats présentés comme acquis sans être passés par le dossier de validation.

Règle de passage : **une expérience ne devient du code que si elle survit à la relecture** —
c'est-à-dire si une autre personne peut la relire, la comprendre, la reproduire et en
reconnaître l'intérêt. Ce qui échoue à ce test reste ici, ou disparaît.

## Ce qui s'y trouve aujourd'hui

| Script | Ce qu'il fait |
|---|---|
| `mission_001_demo.py` | Démonstration sur données synthétiques : acquisition, exécution, évaluation, enregistrement. Ne touche ni au réseau ni au disque. |
| `mission_002_real_world.py` | Le même enchaînement, **sur le monde réel** : 33 481 relevés quotidiens du Mississippi à Grafton (USGS-05587450, 1933→2026) acquis par l'API OGC, lus en observations, climatologie journalière comparée aux statistiques publiées par l'agence, indice d'anomalie standardisée, et publication d'un produit de connaissance dont la lignée est vérifiée. |

`mission_002_real_world.py` **touche le réseau** : il lui faut une clé d'API USGS dans
`USGS_API_KEY` au-delà du quota anonyme (1 000 requêtes par heure), et il écrit la preuve
brute dans un répertoire temporaire qu'il indique à la fin. La clé n'est jamais écrite :
elle est lue au dernier moment et ne figure dans aucune demande consignée.
