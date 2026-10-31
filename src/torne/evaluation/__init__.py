"""Évaluation et validation : mesurer un modèle contre des références.

Ce package est la forme exécutable de la préoccupation transversale
« validation » de `docs/ARCHITECTURE.md` §6.4. Il ne contient qu'une chose :
des fonctions qui découpent, qui mesurent, et qui enregistrent.

Répartition :

- `splits` — les découpages temporels stricts, et le walk-forward cumulatif ;
- `metrics` — les métriques d'erreur, la couverture, le décompte des
  points écartés, et l'incertitude qui qualifie chaque métrique ;
- `uncertainty` — l'intervalle de confiance et la taille effective de
  l'échantillon qui fonde l'incertitude d'une métrique ;
- `baselines` — les trois références naïves (persistence, moyenne, dérive) ;
- `report` — le rapport d'évaluation, reproductible et rejouable.

Les sous-modules sont importés explicitement (`from torne.evaluation.report
import evaluate_walk_forward`). Il n'y a pas de surface d'API implicite à
maintenir : chaque module expose un vocabulaire distinct et un seul.

**Les absences sont représentées par `None`, jamais par un nombre.** Une
série, un bloc d'entraînement ou une séquence de métriques peut porter des
absences : elles traversent l'évaluation, elles sont comptées et qualifiées,
et elles ne sont ni converties en zéro ni comblées par une supposition.

Aucune dépendance n'est cachée, aucun service n'est créé : les statistiques
employées — variance HAC de Newey-West, fenêtre de Bartlett — sont celles du
paquet `torne.methods`, déjà utilisées par le test apparié de Diebold-Mariano,
et aucune n'est réimplémentée ici. L'intervalle de confiance des métriques
est celui de la variance HAC (Newey-West) avec taille effective, **pas** celui
d'un bootstrap : `uncertainty` en donne la méthode exacte et ses limites.
"""
