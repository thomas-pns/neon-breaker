# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Tests des manettes et des commandes personnalisées (2.0) : boutons et
    stick traduits en actions, J1 / J2 sur deux manettes, touche changée
    dans OPTIONS, pense-bête des commandes à jour.

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

from moteur import entrees as e  # noqa: E402


def entrees_test():
    entrees = e.Entrees(SimpleNamespace(vers_interne=lambda p: p))
    entrees.manettes = {10: (0, None), 11: (1, None)}
    return entrees


@unittest.skipIf(e._manettes is None, "pygame sans manettes")
class TestManette(unittest.TestCase):

    def test_bouton_a_lance_et_valide(self):
        entrees = entrees_test()
        entrees.traiter(pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, instance_id=10,
                                           button=pygame.CONTROLLER_BUTTON_A))
        self.assertTrue(entrees.vient_d_appuyer("action", "solo"))
        self.assertTrue(entrees.vient_d_appuyer("valider"))
        self.assertTrue(entrees.vient_d_appuyer("action", "j1"))
        self.assertFalse(entrees.vient_d_appuyer("action", "j2"))     # c'est la manette de J1
        entrees.debut_image()
        self.assertFalse(entrees.vient_d_appuyer("action", "solo"))
        self.assertTrue(entrees.est_maintenue("action", "solo"))

    def test_stick(self):
        entrees = entrees_test()
        entrees.traiter(pygame.event.Event(pygame.CONTROLLERAXISMOTION, instance_id=11,
                                           axis=pygame.CONTROLLER_AXIS_LEFTX, value=-30000))
        self.assertEqual(entrees.direction("j2"), -1)
        self.assertEqual(entrees.direction("j1"), 0)
        entrees.traiter(pygame.event.Event(pygame.CONTROLLERAXISMOTION, instance_id=11,
                                           axis=pygame.CONTROLLER_AXIS_LEFTX, value=-2000))
        self.assertEqual(entrees.direction("j2"), 0)

    def test_gachette_overdrive(self):
        entrees = entrees_test()
        entrees.traiter(pygame.event.Event(pygame.CONTROLLERAXISMOTION, instance_id=10,
                                           axis=pygame.CONTROLLER_AXIS_TRIGGERRIGHT, value=32000))
        self.assertTrue(entrees.vient_d_appuyer("overdrive", "solo"))


class TestCommandesPerso(unittest.TestCase):

    def test_touche_changee(self):
        entrees = entrees_test()
        entrees.appliquer_perso({"solo": {"action": {"code": pygame.KSCAN_W, "nom": "W"}}})
        entrees.appuis.add(pygame.KSCAN_SPACE)
        self.assertFalse(entrees.vient_d_appuyer("action", "solo"))
        entrees.appuis.add(pygame.KSCAN_W)
        self.assertTrue(entrees.vient_d_appuyer("action", "solo"))
        entrees.appliquer_perso({})
        self.assertIn(pygame.KSCAN_SPACE, entrees.touches["solo"]["action"])

    def test_pense_bete(self):
        app = SimpleNamespace(entrees=entrees_test(), reglages={"touches": {}})
        app.entrees.manettes = {}
        self.assertEqual(e.libelles_touches(app, "j1")[0], ("Q D", "BOUGER"))
        app.reglages["touches"] = {"j1": {"gauche": {"code": 4, "nom": "K"}}}
        self.assertEqual(e.libelles_touches(app, "j1")[0], ("K D", "BOUGER"))
        app.entrees.manettes = {1: (0, None)}
        self.assertEqual(e.libelles_touches(app, "solo")[0][0], "STICK")


if __name__ == "__main__":
    unittest.main()
