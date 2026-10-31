"""Tests de fumée du paquet TORNE.

Le socle est documentaire : ces tests vérifient uniquement que le paquet s'importe et
que sa version est déclarée. Aucun test de modèle n'existe, car aucun modèle n'est
implémenté.
"""

import re

import torne


def test_le_paquet_s_importe_et_expose_une_version():
    """L'import du paquet doit réussir et exposer une version exploitable."""
    assert torne.__doc__
    assert isinstance(torne.__version__, str)
    assert re.fullmatch(r"\d+\.\d+\.\d+", torne.__version__)


def test_le_point_d_entree_console_est_appelable():
    """Le script console `torne` doit pointer vers une fonction réellement existante."""
    assert callable(torne.main)
