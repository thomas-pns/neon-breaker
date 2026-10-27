# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Verifier l'affichage et les interactions de la grille des succes du profil.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Realise le 23/10/2026
"""

import os
import sys
import unittest
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402
from ecrans.en_ligne.joueurs import EcranProfil, couper_en_lignes  # noqa: E402
from moteur import config  # noqa: E402


class EntreesTest:
    """Entrees simples pour simuler clavier et souris."""

    def __init__(self):
        self.actions = set()
        self.clics = []
        self.souris = (0, 0)
        self.souris_bougee = False
        self.appuis_tactiles = set()
        self.glisse_long = 0
        self.glisse_bord = False

    def vient_d_appuyer(self, action):
        """But : consommer une action. Entree(s) : action (str). Sortie : bool."""
        resultat = action in self.actions
        self.actions.discard(action)
        return resultat


class AppTest:
    """Application factice sans reseau."""

    def __init__(self):
        self.entrees = EntreesTest()
        self.fond = SimpleNamespace(dessiner=lambda image: None)
        self.en_ligne = SimpleNamespace(connecte=False, pseudo="TEST", niveau=1, couleur="cyan")
        self.audio = SimpleNamespace(jouer=lambda nom: None)
        self.remplace = None

    def remplacer(self, ecran):
        """But : memoriser un changement d'ecran. Entree(s) : ecran. Sortie : aucune."""
        self.remplace = ecran


class TestProfilSucces(unittest.TestCase):
    """Tests du detail des succes."""

    def creer_profil(self):
        """But : creer un profil factice. Entree(s) : aucune. Sortie : EcranProfil."""
        app = AppTest()
        ecran = EcranProfil.__new__(EcranProfil)
        ecran.app = app
        ecran.temps = 0
        ecran.pseudo = "TEST"
        ecran.retour = "joueurs"
        ecran.profil = {"succes": [{"nom": "NOM TRES LONG DE SUCCES", "categorie": "debuts",
                                    "description": "DESCRIPTION DU SUCCES", "obtenu_le": None}],
                        "stats": {}}
        ecran.erreur = ""
        ecran.choix = 0
        ecran.fiche_ouverte = False
        ecran.zones_succes = [pygame.Rect(470, 270, 100, 72)]
        ecran.rect_fiche = pygame.Rect(315, 180, 650, 360)
        return app, ecran

    def test_coupe_nom_sur_deux_lignes(self):
        """But : verifier la coupure d'un nom long. Entree(s) : aucune. Sortie : aucune."""
        self.assertEqual(couper_en_lignes("PREMIER IMPACT", 8), ("PREMIER", "IMPACT"))

    def test_ouverture_fermeture_clavier_et_clic(self):
        """But : verifier ouverture et fermeture par ENTREE, ECHAP et clic. Entree(s) : aucune. Sortie : aucune."""
        app, ecran = self.creer_profil()
        app.entrees.actions.add("valider")
        ecran.mettre_a_jour(1 / 60)
        self.assertTrue(ecran.fiche_ouverte)
        self.assertIsNone(app.remplace)
        app.entrees.actions.add("retour")
        ecran.mettre_a_jour(1 / 60)
        self.assertFalse(ecran.fiche_ouverte)
        app.entrees.souris = ecran.zones_succes[0].center
        app.entrees.clics = [1]
        ecran.mettre_a_jour(1 / 60)
        self.assertTrue(ecran.fiche_ouverte)
        app.entrees.clics = [1]
        app.entrees.souris = (5, 5)
        ecran.mettre_a_jour(1 / 60)
        self.assertFalse(ecran.fiche_ouverte)
        self.assertIsNone(app.remplace)

    def test_entree_ne_quitte_pas_ecran(self):
        """But : verifier qu'ENTREE conserve le profil actif. Entree(s) : aucune. Sortie : aucune."""
        app, ecran = self.creer_profil()
        app.entrees.actions.add("valider")
        ecran.mettre_a_jour(1 / 60)
        self.assertIsNone(app.remplace)
        self.assertTrue(ecran.fiche_ouverte)


class TestNombreSucces(unittest.TestCase):
    def test_nombre_succes_suit_le_serveur(self):
        """But : le total affiché côté jeu suit la liste du serveur. Sortie : aucune."""
        from reseau.profil import NOMBRE_SUCCES
        from serveur.succes import SUCCES
        self.assertEqual(NOMBRE_SUCCES, len(SUCCES))


if __name__ == "__main__":
    unittest.main()
