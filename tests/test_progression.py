# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Tests de la progression gardée sur le compte (jeu/progression.py) : la fusion de deux
    appareils garde le meilleur de chacun et ne perd rien.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 27/10/2026
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jeu import progression  # noqa: E402


class TestFusion(unittest.TestCase):

    def test_meilleur_des_deux(self):
        a = {"progression": {"campagne": 5, "coop": 1}, "meilleurs": {"arcade": 100},
             "classements": {"arcade": [{"nom": "TOM", "score": 100}, {"nom": "TOM", "score": 50}]},
             "defi": {"jour": "2026-10-27", "record": 300}, "semaine": {"jour": "2026-W43", "record": 9}}
        b = {"progression": {"campagne": 3, "coop": 2}, "meilleurs": {"arcade": 80, "hardcore": 4},
             "classements": {"arcade": [{"nom": "TOM", "score": 100}, {"nom": "CAM", "score": 70}]},
             "defi": {"jour": "2026-10-27", "record": 450}, "semaine": {"jour": "2026-W44", "record": 2}}
        f = progression.fusionner(a, b)
        self.assertEqual(f["progression"], {"campagne": 5, "coop": 2})
        self.assertEqual(f["meilleurs"], {"arcade": 100, "hardcore": 4})
        self.assertEqual([e["score"] for e in f["classements"]["arcade"]], [100, 70, 50])
        self.assertEqual(f["defi"], {"jour": "2026-10-27", "record": 450})
        self.assertEqual(f["semaine"], {"jour": "2026-W44", "record": 2})      # la plus récente
        self.assertEqual(progression.fusionner(b, a), f)                       # l'ordre ne compte pas

    def test_donnees_abimees_ignorees(self):
        f = progression.fusionner({"progression": "n'importe quoi", "etoiles": {"campagne": {"x": "y"}},
                                   "classements": {"arcade": [5, {"nom": 3}]}}, None)
        self.assertEqual(f["progression"], {})
        self.assertEqual(f["classements"]["arcade"], [{"nom": "3", "score": 0}])

    def test_appliquer_a_la_sauvegarde(self):
        sauvegarde = {"reglages": {"crt": True}, "progression": {"campagne": 1}, "compte": {"jeton": "x"}}
        self.assertTrue(progression.appliquer(sauvegarde, {"progression": {"campagne": 6}}))
        self.assertEqual(sauvegarde["progression"]["campagne"], 6)
        self.assertEqual(sauvegarde["reglages"], {"crt": True})                # le reste ne bouge pas
        self.assertEqual(sauvegarde["compte"], {"jeton": "x"})
        self.assertFalse(progression.appliquer(sauvegarde, {"progression": {"campagne": 2}}))


if __name__ == "__main__":
    unittest.main()
