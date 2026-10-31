"""Contrats fondamentaux de TORNE, sous forme exécutable.

Ce package est la forme codée de `docs/CONTRATS_FONDAMENTAUX.md`. Il ne décrit
aucune architecture de stockage, aucun connecteur, aucun service, aucun moteur :
il ne fixe que des responsabilités, des invariants et des formes vérifiables.

Les sous-modules sont importés explicitement (`from torne.contracts.time import
TemporalStamp`). Il n'y a pas de surface d'API implicite à maintenir : chaque
module expose un vocabulaire distinct et un seul.

Répartition :

- `time` — les trois dimensions temporelles et la règle d'utilisabilité ;
- `validity` — le vocabulaire de l'absence, de l'invalidité et du hors-domaine ;
- `model` — le contrat de la frontière « Modèles » ;
- `fingerprint` — l'empreinte canonique d'une structure de données ;
- `observation` — Source, Raw Evidence, Observation (propriété : intégration) ;
- `derived` — la grandeur dérivée : règle de calcul, temporalité propre,
  lignée et qualification d'incertitude ;
- `knowledge` — provenance et produit de connaissance (propriété : intégration).
"""
