# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Verifier le chargement des nouveautes et la navigation entre versions.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Realise le 23/10/2026
"""

import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from moteur import config  # noqa: E402
from ecrans.nouveautes import EcranNouveautes, charger_nouveautes  # noqa: E402


class EntreesTest:
    """Entrees programmables pour tester l'ecran sans fenetre."""

    def __init__(self):
        self.actions = set()
        self.clics = []
        self.souris = (0, 0)

    def vient_d_appuyer(self, action):
        """But : lire une action simulee. Entree(s) : action (str). Sortie : bool."""
        resultat = action in self.actions
        self.actions.discard(action)
        return resultat


class AppTest:
    """Application minimale pour tester l'ecran."""

    def __init__(self):
        self.entrees = EntreesTest()
        self.fond = type("Fond", (), {"dessiner": lambda self, image: None})()
        self.remplace = None

    def remplacer(self, ecran):
        """But : memoriser l'ecran demande. Entree(s) : ecran. Sortie : aucune."""
        self.remplace = ecran


class TestNouveautes(unittest.TestCase):

    def test_chargement_depuis_ressources(self):
        """But : verifier la lecture du JSON via DOSSIER_RESSOURCES. Entree(s) : aucune. Sortie : aucune."""
        versions = charger_nouveautes()
        self.assertTrue(versions)
        self.assertEqual(versions[0]["version"], "BETA")
        self.assertEqual(len(versions[0]["lignes"]), 4)
        self.assertEqual(os.path.basename(config.DOSSIER_RESSOURCES), "data")

    def test_navigation_et_ouverture_fermeture(self):
        """But : verifier haut, bas et entree. Entree(s) : aucune. Sortie : aucune."""
        app = AppTest()
        ecran = EcranNouveautes(app)
        app.entrees.actions.add("bas")
        ecran.mettre_a_jour(1 / 60)
        self.assertEqual(ecran.indice, 1)
        app.entrees.actions.add("valider")
        ecran.mettre_a_jour(1 / 60)
        self.assertEqual(ecran.ouvert, 1)
        app.entrees.actions.add("valider")
        ecran.mettre_a_jour(1 / 60)
        self.assertIsNone(ecran.ouvert)
        app.entrees.actions.add("haut")
        ecran.mettre_a_jour(1 / 60)
        self.assertEqual(ecran.indice, 0)

