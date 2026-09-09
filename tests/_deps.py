"""Dependances optionnelles des tests, declarees au lieu d'etre subies.

`make check` doit rendre un vert franc sur un Python nu. Ce n'est pas de la
cosmetique : une suite qui echoue toujours de vingt-trois facons ne signale plus
rien, et il faut alors comparer chaque execution a une liste d'echecs connus pour
savoir si l'on vient de casser quelque chose. C'est exactement ce qu'il a fallu
faire pendant la reorganisation du 2026-09-09.

Quelques tests appellent des scripts qui ont besoin de numpy, de matplotlib ou de
jq. Ces outils ne sont pas des dependances du depot : `scripts/` s'en passe par
principe. Les tests concernes se **sautent** donc explicitement quand l'outil
manque, en le nommant, plutot que de tomber en ImportError.

Un saut reste visible : unittest les compte et les affiche. Un test saute n'est
pas un test qui passe, et le nombre de sauts est la mesure de ce que
l'environnement ne couvre pas.

    from _deps import require_modules, require_commands

    require_modules("numpy")
"""
import importlib.util
import shutil
import unittest


def require_modules(*modules: str) -> None:
    """Saute le module de test si l'un des paquets nommes est absent."""
    for name in modules:
        if importlib.util.find_spec(name) is None:
            raise unittest.SkipTest(
                f"{name} absent : ce test appelle un script qui en depend. "
                f"Installer {name} pour le couvrir."
            )


def require_commands(*commands: str) -> None:
    """Saute le module de test si l'un des executables nommes est absent."""
    for name in commands:
        if shutil.which(name) is None:
            raise unittest.SkipTest(
                f"{name} absent du PATH : ce test l'invoque. "
                f"Installer {name} pour le couvrir."
            )
