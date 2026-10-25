# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Tests de la fluidité en ligne (version 1.5) : la raquette d'un autre
    joueur continue sur sa lancée entre deux instantanés sans dépasser le
    terrain, et l'écart de position d'une balle est rattrapé en douceur.

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

from jeu import terrain as t  # noqa: E402
from jeu.balle import Balle  # noqa: E402
from jeu.joueur import Joueur  # noqa: E402
from reseau.instantane import prolonger  # noqa: E402


class TestFluidite(unittest.TestCase):

    def preparer(self):
        terrain = t.Terrain(pygame.Rect(0, 0, 400, 600))
        joueur = Joueur(1, "j1", "A")
        raquette = terrain.ajouter_raquette(joueur, -1) or terrain.raquettes[0]
        return SimpleNamespace(terrains=[terrain]), terrain, raquette

    def test_raquette_distante_continue_sur_sa_lancee(self):
        mode, _, raquette = self.preparer()
        raquette.x = 200.0
        raquette.cible_reseau = (200.0, 300.0)      # va vers la droite à 300 px/s
        raquette.age_cible = 0.0
        for _ in range(6):                           # 0,1 s sans nouvel instantané
            prolonger(mode, 1 / 60)
        self.assertGreater(raquette.x, 210)          # elle avance, plus d'escalier
        for _ in range(120):                         # 2 s : la lancée est plafonnée
            prolonger(mode, 1 / 60)
        self.assertLessEqual(raquette.x, 200 + 300 * 0.12 + 0.5)

    def test_raquette_distante_reste_dans_le_terrain(self):
        mode, _, raquette = self.preparer()
        bord = raquette.x_max - raquette.largeur / 2
        raquette.x = bord - 2
        raquette.cible_reseau = (bord - 2, 2000.0)
        raquette.age_cible = 0.0
        for _ in range(30):
            prolonger(mode, 1 / 60)
        self.assertLessEqual(raquette.x, bord + 1e-6)

    def test_correction_de_balle_rattrapee_en_douceur(self):
        mode, terrain, _ = self.preparer()
        balle = Balle(200.0, 300.0)
        balle.vx = balle.vy = 0.0
        balle.collee = False
        balle.correction = (-20.0, 0.0)              # le serveur la voit 20 px plus loin
        terrain.balles.ajouter_fin(balle)
        prolonger(mode, 1 / 60)
        self.assertLess(balle.x - 200.0, 10)         # pas de téléportation d'un coup
        self.assertGreater(balle.x, 200.0)
        for _ in range(30):
            prolonger(mode, 1 / 60)
        self.assertAlmostEqual(balle.x, 220.0, delta=0.5)
        self.assertIsNone(balle.correction)


class TestFusionEtats(unittest.TestCase):

    def test_briques_et_effets_gardes(self):
        from reseau.instantane import fusionner_etats
        ancien = {"t": "etat", "terrains": [{"balles": [1], "briques": ["vieilles"]}], "fx": [["a"]]}
        nouveau = {"t": "etat", "terrains": [{"balles": [2]}], "fx": [["b"]]}
        fusion = fusionner_etats(ancien, nouveau)
        self.assertEqual(fusion["terrains"][0]["balles"], [2])          # le plus récent
        self.assertEqual(fusion["terrains"][0]["briques"], ["vieilles"])  # rien de perdu
        self.assertEqual(fusion["fx"], [["a"], ["b"]])
        recent = {"t": "etat", "terrains": [{"balles": [3], "briques": ["neuves"]}], "fx": []}
        self.assertEqual(fusionner_etats(ancien, recent)["terrains"][0]["briques"], ["neuves"])


if __name__ == "__main__":
    unittest.main()
