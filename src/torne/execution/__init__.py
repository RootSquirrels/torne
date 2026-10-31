"""Exécution de modèle : le maillon « exécution » de la chaîne de TORNE.

Ce package contient le seul mécanisme d'exécution du dépôt. Il valide des
entrées et des paramètres, construit une `ExecutionConfig` **sans
horodatage** — donc d'empreinte stable — appelle le modèle, et rend le
résultat avec les métadonnées de temps de l'exécution.

Trois règles y tiennent :

- les erreurs du modèle remontent intactes, jamais masquées ;
- l'état aléatoire global n'est jamais touché : la graine est transmise au
  modèle, qui fabrique son propre générateur ;
- le temps ne porte jamais la configuration : il porte l'issue.

Ce package ne crée ni registre, ni service, ni moteur, ni plugin. Les
sous-modules sont importés explicitement (`from torne.execution.runner import
execute`) : il n'y a pas de surface d'API implicite à maintenir.
"""
