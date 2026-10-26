# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Tests de la version navigateur (2.2) qui tournent aussi sur PC : réponses
    HTTP relevées dans le navigateur, doigts et boutons tactiles, et
    optimisations de dessin (même rendu qu'avant, en plus rapide).

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 26/10/2026
"""

import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from moteur import config  # noqa: E402
from moteur.entrees import Entrees  # noqa: E402
from moteur.rendu import FiltreCRT, ajouter_lueur, halo_rect  # noqa: E402
from reseau.client import resultat_http  # noqa: E402


class EcranFactice:
    """Fenêtre 1280x720 sans bandes noires : coordonnées internes = fenêtre."""

    def __init__(self):
        self.fenetre = pygame.Surface((config.LARGEUR, config.HAUTEUR))

    @staticmethod
    def vers_interne(position):
        return position


def doigt(nature, x, y, identifiant=1):
    return pygame.event.Event(nature, x=x / config.LARGEUR, y=y / config.HAUTEUR,
                              dx=0, dy=0, finger_id=identifiant, touch_id=1, pressure=1)


class TestReponsesNavigateur(unittest.TestCase):

    def test_formats(self):
        self.assertTrue(resultat_http(200, '{"a": 1}')["ok"])
        self.assertEqual(resultat_http(200, '{"a": 1}')["donnees"], {"a": 1})
        injoignable = resultat_http(0, "")
        self.assertFalse(injoignable["ok"])
        self.assertTrue(injoignable["maintenance"])
        refus = resultat_http(401, '{"detail": "SESSION EXPIREE"}')
        self.assertEqual((refus["code"], refus["erreur"]), (401, "SESSION EXPIREE"))
        self.assertTrue(resultat_http(503, "<html>")["maintenance"])
        self.assertEqual(resultat_http(200, "pas du json")["erreur"], "REPONSE INVALIDE")


class TestTactile(unittest.TestCase):

    def setUp(self):
        pygame.init()
        self.entrees = Entrees(EcranFactice())

    def souris(self):
        return tuple(round(v) for v in self.entrees.souris)

    def nouvelle_image(self, boutons=()):
        for rect, action in boutons:
            self.entrees.bouton_tactile(rect, action)
        self.entrees.debut_image()

    def test_toucher_franc_vaut_un_clic(self):
        """Le clic part quand le doigt se lève sans avoir glissé (pas de clic involontaire)."""
        self.nouvelle_image()
        self.entrees.traiter(doigt(pygame.FINGERDOWN, 640, 500))
        self.assertTrue(self.entrees.tactile)
        self.assertEqual(self.entrees.doigt_pose, (640, 500))     # le jeu réagit tout de suite
        self.assertNotIn(1, self.entrees.clics)
        self.entrees.traiter(doigt(pygame.FINGERUP, 645, 503))
        self.assertIn(1, self.entrees.clics)
        self.assertEqual(self.souris(), (640, 500))

    def test_glisser_ne_clique_pas(self):
        self.nouvelle_image()
        self.entrees.traiter(doigt(pygame.FINGERDOWN, 640, 500))
        self.entrees.traiter(doigt(pygame.FINGERMOTION, 700, 505))
        self.assertEqual(self.souris(), (700, 505))
        self.entrees.traiter(doigt(pygame.FINGERUP, 760, 505))
        self.assertNotIn(1, self.entrees.clics)

    def test_bouton_sans_clic_ni_raquette(self):
        self.nouvelle_image([(pygame.Rect(1050, 600, 200, 50), "pause")])
        self.entrees.traiter(doigt(pygame.FINGERDOWN, 1100, 620))
        self.assertFalse(self.entrees.vient_d_appuyer("pause"))     # pas encore : doigt posé
        self.entrees.traiter(doigt(pygame.FINGERUP, 1102, 622))
        self.assertTrue(self.entrees.vient_d_appuyer("pause"))
        self.assertTrue(self.entrees.vient_d_appuyer("pause", "solo"))
        self.assertFalse(self.entrees.clics)
        self.assertFalse(self.entrees.souris_bougee)
        self.entrees.debut_image()
        self.assertFalse(self.entrees.vient_d_appuyer("pause"))

    def test_bouton_quitte_avant_de_lever(self):
        """Le doigt glisse hors du bouton avant de se lever : rien ne se passe."""
        self.nouvelle_image([(pygame.Rect(1050, 600, 200, 50), "pause")])
        self.entrees.traiter(doigt(pygame.FINGERDOWN, 1100, 620))
        self.entrees.traiter(doigt(pygame.FINGERMOTION, 900, 620))
        self.assertFalse(self.entrees.souris_bougee)              # ne bouge pas la raquette
        self.entrees.traiter(doigt(pygame.FINGERUP, 900, 620))
        self.assertFalse(self.entrees.vient_d_appuyer("pause"))

    def test_deux_doigts(self):
        """Un doigt bouge la raquette pendant que l'autre touche SUPERNOVA."""
        self.nouvelle_image([(pygame.Rect(1050, 560, 200, 50), "overdrive")])
        self.entrees.traiter(doigt(pygame.FINGERDOWN, 500, 600, 1))
        self.entrees.traiter(doigt(pygame.FINGERDOWN, 1100, 580, 2))
        self.entrees.traiter(doigt(pygame.FINGERMOTION, 560, 600, 1))
        self.entrees.traiter(doigt(pygame.FINGERUP, 1100, 580, 2))
        self.assertTrue(self.entrees.vient_d_appuyer("overdrive", "solo"))
        self.assertEqual(self.souris(), (560, 600))

    def test_glisser_fait_defiler(self):
        self.nouvelle_image()
        self.entrees.traiter(doigt(pygame.FINGERDOWN, 640, 500))
        self.entrees.traiter(doigt(pygame.FINGERMOTION, 640, 410))
        self.assertEqual(self.entrees.molette, -2)

    def test_souris_imitee_ignoree(self):
        """SDL imite aussi la souris avec le doigt : on ne compte pas deux fois."""
        self.nouvelle_image()
        self.entrees.traiter(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(10, 10), button=1,
                                                touch=True))
        self.assertFalse(self.entrees.clics)

    def test_clic_souris_sur_un_bouton(self):
        self.nouvelle_image([(pygame.Rect(0, 0, 100, 100), "retour")])
        self.entrees.traiter(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(50, 50), button=1,
                                                touch=False))
        self.assertTrue(self.entrees.vient_d_appuyer("retour"))
        self.assertFalse(self.entrees.clics)


def ecart_max(a, b):
    import numpy as np
    return int(np.abs(pygame.surfarray.array3d(a).astype(int)
                      - pygame.surfarray.array3d(b).astype(int)).max())


class TestDessinOptimise(unittest.TestCase):
    """Les optimisations (surtout pour le navigateur) gardent le même rendu."""

    def setUp(self):
        try:
            import numpy  # noqa: F401
        except ImportError:
            self.skipTest("numpy absent")
        hasard = random.Random(4)
        self.fond = pygame.Surface((config.LARGEUR, config.HAUTEUR))
        for _ in range(300):
            couleur = [hasard.randint(0, 255) for _ in range(3)]
            self.fond.fill(couleur, (hasard.randint(0, 1200), hasard.randint(0, 700), 80, 40))

    def test_halo_par_bandes(self):
        lueur = halo_rect(760, 690, (0, 200, 255), rayon=10, epaisseur=3)
        complet = self.fond.copy()
        complet.blit(lueur, (240, 10), special_flags=pygame.BLEND_RGB_ADD)
        bandes = self.fond.copy()
        ajouter_lueur(bandes, lueur, (240, 10))
        self.assertLessEqual(ecart_max(complet, bandes), 2)

    def test_filtre_crt_en_un_calque(self):
        filtre = FiltreCRT(config.LARGEUR, config.HAUTEUR)
        attendu = self.fond.copy()
        scanlines = pygame.Surface((config.LARGEUR, config.HAUTEUR), pygame.SRCALPHA)
        for y in range(0, config.HAUTEUR, 3):
            pygame.draw.line(scanlines, (0, 0, 0, 55), (0, y), (config.LARGEUR, y))
        attendu.blit(scanlines, (0, 0))
        attendu.blit(FiltreCRT._creer_vignette(config.LARGEUR, config.HAUTEUR), (0, 0))
        obtenu = self.fond.copy()
        filtre.appliquer(obtenu)
        self.assertLessEqual(ecart_max(attendu, obtenu), 3)


if __name__ == "__main__":
    unittest.main()
