"""Connaissance : enregistrement d'une exécution et vérification de sa lignée.

Ce package est la forme exécutable de la frontière « Produits de connaissance »
(`docs/ARCHITECTURE.md` §4) et de la préoccupation transversale « provenance »
(§6.1). Il relie une exécution de modèle aux objets qui portent la preuve —
source, preuve brute, observation — et permet de remonter du résultat publié
jusqu'aux preuves brutes.

Répartition :

- `record` — l'enregistrement d'exécution, sa lignée, sa publication sous
  forme de produit de connaissance, et la vérification de cette lignée.

Les sous-modules sont importés explicitement (`from torne.knowledge.record import
build_record`). Il n'y a pas de surface d'API implicite à maintenir : ce package
ne crée ni registre, ni service, ni moteur, ni format de stockage. Un produit
n'est pas un catalogue de l'existant : il est un état, daté, versionné et
traçable.
"""
