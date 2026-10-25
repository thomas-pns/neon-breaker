# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Tests des icônes en pixel art : une icône pour chaque capsule et chaque
    succès, grilles bien formées, rendu et cache.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 25/10/2026
"""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from moteur import icones


class TestIcones(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_grilles_bien_formees(self):
        for code, motif in icones.GRILLES.items():
            self.assertEqual(len(motif), icones.TAILLE, code)
            for ligne in motif:
                self.assertEqual(len(ligne), icones.TAILLE, code)
                self.assertTrue(set(ligne) <= set(".Xod"), code)

    def test_une_icone_par_capsule_et_par_succes(self):
        from jeu.capsule import CATALOGUE
        from serveur.succes import SUCCES
        self.assertEqual(set(CATALOGUE) - set(icones.CAPSULES), set())
        self.assertEqual({s.code for s in SUCCES} - set(icones.SUCCES), set())

    def test_rendu_et_cache(self):
        image = icones.surface_icone("feu", (255, 120, 40), 3)
        self.assertEqual(image.get_size(), (9 * 3 + 2, 9 * 3 + 2))
        self.assertIs(image, icones.surface_icone("feu", (255, 120, 40), 3))
        self.assertIsNone(icones.surface_icone("inconnu", (255, 0, 0)))
        self.assertIsNotNone(icones.surface_icone("inconnu", (255, 0, 0), defaut=icones.TROPHEE))
        ecran = pygame.Surface((100, 100))
        self.assertTrue(icones.dessiner_icone(ecran, "vie", (50, 50), (0, 255, 0), 2,
                                              lueur=True, largeur=8))
        self.assertFalse(icones.dessiner_icone(ecran, "inconnu", (50, 50), (0, 255, 0)))


if __name__ == "__main__":
    unittest.main()
