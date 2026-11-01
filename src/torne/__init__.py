"""TORNE — plateforme computationnelle de connaissance du monde réel."""

__version__ = "0.1.0"


def main() -> None:
    """Décrit l'état du paquet.

    Le socle est exécutable : l'acquisition, la conservation de la preuve, les
    contrats, l'exécution, l'évaluation, la provenance et une méthode
    scientifique réelle existent. Trois sources sont intégrées et ont été
    interrogées sur le réseau.

    Une première couche sémantique existe — l'hydrologie — et un jalon a été
    exécuté sur le monde réel : des relevés quotidiens du Mississippi à
    Grafton (1933→2026), une climatologie qui reproduit les statistiques
    publiées par l'agence, un indice d'anomalie standardisée, et un produit de
    connaissance dont la lignée a été vérifiée.

    Aucune **performance** sur le monde réel n'est démontrée : le modèle y
    tourne et y est évalué hors échantillon, mais aucune performance n'est
    *établie*. Cette fonction reste un point d'entrée console provisoire :
    elle sera remplacée par le premier slice vertical.
    """
    print(
        f"torne {__version__} — exécution, évaluation et preuve implémentées ; "
        "premier jalon sur données réelles publié ; aucune performance démontrée"
    )


if __name__ == "__main__":
    main()
