# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Tests du « rebond décidé par le joueur » (jeu en ligne, version 1.3) :
    le serveur ne fait plus rebondir lui-même une raquette dont le jeu
    annonce ses rebonds, laisse un court sursis avant de perdre la balle,
    et n'accepte que des rebonds plausibles.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 25/10/2026
"""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from jeu import terrain as t  # noqa: E402
from jeu.balle import Balle  # noqa: E402
from jeu.joueur import Joueur  # noqa: E402


def natures(terrain):
    resultat = []
    while not terrain.evenements.est_vide():
        resultat.append(terrain.evenements.defiler()[0])
    return resultat


class TestRebondClient(unittest.TestCase):

    def preparer(self):
        terrain = t.Terrain(pygame.Rect(0, 0, 400, 600))
        joueur = Joueur(1, "j1", "A")
        raquette = terrain.ajouter_raquette(joueur, -1) or terrain.raquettes[0]
        raquette.rebond_client = True
        raquette.delai_rebond = 0.2
        balle = Balle(raquette.x, raquette.face_y() - 40)
        balle.collee = False
        balle.vx, balle.vy = 0, 600
        terrain.balles.ajouter_fin(balle)
        balle.nid = 7
        return terrain, joueur, raquette, balle

    def test_le_serveur_ne_fait_plus_rebondir_et_attend(self):
        terrain, _, raquette, balle = self.preparer()
        for _ in range(30):                          # 0,25 s : la balle passe la raquette
            terrain.mettre_a_jour(1 / 120, {})
        self.assertGreater(balle.vy, 0, "pas de rebond décidé par le serveur")
        self.assertNotIn("balle_perdue", natures(terrain))
        for _ in range(40):                          # le sursis expire : balle perdue
            terrain.mettre_a_jour(1 / 120, {})
        self.assertIn("balle_perdue", natures(terrain))

    def test_rebond_annonce_pendant_le_sursis(self):
        terrain, _, raquette, balle = self.preparer()
        for _ in range(30):
            terrain.mettre_a_jour(1 / 120, {})
        terrain.rebond_client(balle, raquette, raquette.x, raquette.face_y() - 8, 50, -600, 0.05)
        self.assertIsNone(balle.sursis)
        self.assertLess(balle.vy, 0)
        for _ in range(60):
            terrain.mettre_a_jour(1 / 120, {})
        self.assertNotIn("balle_perdue", natures(terrain))

    def test_aimant(self):
        terrain, joueur, raquette, balle = self.preparer()
        joueur.aimant_prises = 2
        terrain.rebond_client(balle, raquette, raquette.x + 10, raquette.face_y() - 8, 0, -600)
        self.assertTrue(balle.collee)
        self.assertEqual(joueur.aimant_prises, 1)

    def test_simulation_valide_les_rebonds(self):
        from serveur.simulation import Simulation
        simulation = Simulation("duel", ["a", "b"])
        joueur = simulation.mode.joueurs[0]
        raquette, terrain = joueur.raquette, joueur.terrain
        simulation.recevoir_commande(1, {"x": raquette.x, "vx": 0, "a": [], "p": 60, "rc": 1})
        self.assertTrue(raquette.rebond_client)
        balle = Balle(raquette.x, raquette.face_y() - 30)
        balle.collee = False
        balle.vx, balle.vy = 0, 600 * -raquette.sens
        balle.nid = 99
        terrain.balles.ajouter_fin(balle)
        face = raquette.face_y()
        message = {"n": 99, "x": raquette.x, "y": face + raquette.sens * 9, "vx": 0,
                   "vy": 600 * raquette.sens, "rx": raquette.x, "p": 60}
        self.assertFalse(simulation.recevoir_rebond(1, dict(message, vy=6000 * raquette.sens)))
        self.assertFalse(simulation.recevoir_rebond(1, dict(message, x=raquette.x + 500)))
        self.assertFalse(simulation.recevoir_rebond(1, dict(message, n=12345)))
        self.assertTrue(simulation.recevoir_rebond(1, message))
        self.assertGreater(balle.vy * raquette.sens, 0)
        # La balle repart : un second rebond sur elle est refusé.
        self.assertFalse(simulation.recevoir_rebond(1, message))

    def test_ancien_jeu_sans_rc(self):
        """Un jeu 1.2 n'envoie pas « rc » : le serveur fait rebondir comme avant."""
        from serveur.simulation import Simulation
        simulation = Simulation("duel", ["a", "b"])
        raquette = simulation.mode.joueurs[0].raquette
        simulation.recevoir_commande(1, {"x": raquette.x, "vx": 0, "a": [], "p": 60})
        self.assertFalse(getattr(raquette, "rebond_client", False))


if __name__ == "__main__":
    unittest.main()
