"""Évaluation et validation : mesurer un modèle contre des références.

Ce package est la forme exécutable de la préoccupation transversale
« validation » de `docs/ARCHITECTURE.md` §6.4. Il ne contient qu'une chose :
des fonctions qui découpent, qui mesurent, et qui enregistrent.

Répartition :

- `splits` — les découpages temporels stricts, et le walk-forward cumulatif ;
- `metrics` — les métriques d'erreur, la couverture, et le décompte des
  points écartés ;
- `baselines` — les trois références naïves (persistance, moyenne, dérive) ;
- `report` — le rapport d'évaluation, reproductible et rejouable.

Les sous-modules sont importés explicitement (`from torne.evaluation.report
import evaluate_walk_forward`). Il n'y a pas de surface d'API implicite à
maintenir : chaque module expose un vocabulaire distinct et un seul.

Aucune dépendance n'est cachée, aucun service n'est créé, aucune dépendance
externe n'est requise : la bibliothèque standard suffit.
"""
