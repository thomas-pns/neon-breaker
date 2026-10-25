# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Tests du bot de test (2.1) : point d'arrivée de la balle avec rebonds sur
    les murs, et pilotage (il vise la balle, il lance quand elle est collée).

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 25/10/2026
"""

import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from jeu.bot import Bot, point_d_arrivee  # noqa: E402


class TestBot(unittest.TestCase):

    def test_point_d_arrivee(self):
        balle = SimpleNamespace(x=100, y=0, vx=0, vy=100, rayon=0)
        self.assertAlmostEqual(point_d_arrivee(balle, 500, 0, 400), 100)
        balle = SimpleNamespace(x=300, y=0, vx=200, vy=100, rayon=0)   # rebond sur le mur droit
        self.assertAlmostEqual(point_d_arrivee(balle, 100, 0, 400), 300 + 200 - 2 * 100)
        balle = SimpleNamespace(x=100, y=500, vx=0, vy=100, rayon=0)   # s'éloigne
        self.assertIsNone(point_d_arrivee(balle, 0, 0, 400))

    def test_pilotage(self):
        from jeu import terrain as t
        from jeu.joueur import Joueur
        from moteur.entrees import Entrees
        terrain = t.Terrain(pygame.Rect(0, 0, 400, 600))
        joueur = Joueur(1, "solo", "J1")
        raquette = terrain.ajouter_raquette(joueur, -1) or terrain.raquettes[0]
        joueur.raquette, joueur.terrain = raquette, terrain
        app = SimpleNamespace(entrees=Entrees(SimpleNamespace(vers_interne=lambda p: p)))
        terrain.nouvelle_balle_collee(raquette)
        bot = Bot()
        bot.piloter(app, joueur, 1.0)
        self.assertIn(("solo", "action"), app.entrees.forcees)        # balle collée : il lance
        balle = next(iter(terrain.balles))
        balle.collee, balle.x, balle.y, balle.vx, balle.vy = False, 320, 100, 0, 300
        app.entrees.debut_image()
        bot.piloter(app, joueur, 0.1)
        self.assertLess(abs(app.entrees.souris[0] - 320), raquette.largeur * 0.3)


if __name__ == "__main__":
    unittest.main()
