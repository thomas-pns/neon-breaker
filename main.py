# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Point d'entrée de NEON BREAKER : lit les options de la ligne de
    commande, crée l'Application et lance l'écran titre.

    Utilisation :
        python main.py               (fenêtre 1280x720 redimensionnable)
        python main.py --plein-ecran
        python main.py --debug       (FPS affichés, F3 pour basculer)

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    --mode campagne|arcade|hardcore|coop|duel|course (jalons 3 et 4).
"""

import argparse
import os
import sys
import traceback

# Permet de lancer « python main.py » depuis n'importe quel dossier.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import pygame  # noqa: F401
except ImportError:
    print("Pygame n'est pas installé. Lancez :  pip install pygame-ce")
    sys.exit(1)

from moteur import config
from moteur.application import Application
from ecrans.titre import EcranTitre


def lire_arguments():
    """
    But : analyser la ligne de commande.
    Entrée : aucune. Sortie : (argparse.Namespace).
    """
    analyseur = argparse.ArgumentParser(description="NEON BREAKER")
    analyseur.add_argument("--plein-ecran", action="store_true",
                           help="démarrer en plein écran")
    analyseur.add_argument("--debug", action="store_true",
                           help="afficher les FPS")
    return analyseur.parse_args()


def main():
    """
    But : lancer le jeu ; en cas de plantage, écrire l'erreur dans
    data/erreurs.log avant de la réafficher.
    Entrée : aucune. Sortie : aucune.
    """
    arguments = lire_arguments()
    if os.environ.get("NEON_AUTOTEST") == "1":
        from outils.autotest import lancer as autotest
        sys.exit(autotest(Application()))
    try:
        app = Application(plein_ecran=arguments.plein_ecran,
                          debug=arguments.debug)
        app.lancer(EcranTitre(app))
    except Exception:
        os.makedirs(config.DOSSIER_DATA, exist_ok=True)
        with open(os.path.join(config.DOSSIER_DATA, "erreurs.log"), "a",
                  encoding="utf-8") as journal:
            journal.write(traceback.format_exc() + "\n")
        raise


if __name__ == "__main__":
    main()
