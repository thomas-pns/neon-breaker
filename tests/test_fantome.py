# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Tests du fantôme du record (2.0) : enregistrement, lecture (position
    interpolée, score à temps égal), validation, et garde du record local.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 25/10/2026
"""

import unittest

from reseau.fantome import Enregistreur, Fantome, valide


class TestFantome(unittest.TestCase):

    def test_aller_retour(self):
        enregistreur = Enregistreur()
        for k in range(100):                      # 10 s : la raquette va de gauche à droite
            enregistreur.avancer(0.1, k / 99, k * 10)
        donnees = enregistreur.exporter()
        self.assertTrue(valide(donnees))
        fantome = Fantome(donnees, "ANA", 990)
        self.assertAlmostEqual(fantome.x_a(0), 0, delta=0.02)
        self.assertAlmostEqual(fantome.x_a(5), 0.5, delta=0.03)
        self.assertIsNone(fantome.x_a(60))        # après la fin : plus de raquette
        self.assertEqual(fantome.score_a(3.5), 290)       # score noté à t = 3 s
        self.assertEqual(fantome.score_a(999), fantome.scores[-1])

    def test_validation(self):
        self.assertFalse(valide(None))
        self.assertFalse(valide({"x": "pas du base64 !", "s": []}))
        self.assertFalse(valide({"x": "AAAA", "s": ["a"]}))
        self.assertFalse(valide({"x": "A" * 70000, "s": []}))


if __name__ == "__main__":
    unittest.main()
