# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Tests des parties classées (2.0) : cote Elo, divisions, appariement de
    la file d'attente, gagnant d'une partie classée (abandon compris).

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 25/10/2026
"""

import unittest

from reseau import classee as c


class TestElo(unittest.TestCase):

    def test_cote_symetrique(self):
        gagne = c.nouvelle_cote(1000, 1000, True, 20)
        perd = c.nouvelle_cote(1000, 1000, False, 20)
        self.assertEqual(gagne - 1000, 1000 - perd)
        self.assertEqual(gagne, 1000 + c.K_NORMAL // 2)

    def test_surprise_rapporte_plus(self):
        exploit = c.nouvelle_cote(1000, 1400, True, 20) - 1000
        attendu = c.nouvelle_cote(1400, 1000, True, 20) - 1400
        self.assertGreater(exploit, attendu)

    def test_placement(self):
        self.assertGreater(c.nouvelle_cote(1000, 1000, True, 0), c.nouvelle_cote(1000, 1000, True, 50))

    def test_divisions(self):
        self.assertEqual(c.division(1000)[0], "BRONZE")
        self.assertEqual(c.division(1100)[0], "ARGENT")
        self.assertEqual(c.division(1600)[0], "NEON")
        self.assertIsNone(c.division(1600)[3])


class TestFile(unittest.TestCase):

    def test_cotes_proches_appariees(self):
        file = {"a": (1000, 0), "b": (1020, 0), "c": (1500, 0)}
        self.assertEqual(c.apparier(file, 0), [("a", "b")])

    def test_ecart_qui_grandit(self):
        file = {"a": (1000, 0), "c": (1500, 0)}
        self.assertEqual(c.apparier(file, 1), [])
        self.assertEqual(c.apparier(file, 20), [("a", "c")])


class TestGagnant(unittest.TestCase):

    def test_gagnant(self):
        try:
            from serveur.salons import gagnant_classee
        except ImportError:
            self.skipTest("serveur non installé")
        membres = ["Ana", "Bob"]
        self.assertEqual(gagnant_classee(membres, None, "Ana"), "Bob")
        self.assertIsNone(gagnant_classee(membres, None, "SERVEUR"))
        resultat = {"rapports": [{"numero": 1, "gagnant": 2}, {"numero": 2, "gagnant": 2}]}
        self.assertEqual(gagnant_classee(membres, resultat, None), "Bob")


if __name__ == "__main__":
    unittest.main()
