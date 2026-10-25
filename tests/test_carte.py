# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Tests de la carte du monde et des étoiles (2.0) : masque d'étoiles d'un
    niveau, cumul entre plusieurs parties, positions des nœuds de la carte.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 25/10/2026
"""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from jeu.modes.campagne import etoiles_niveau, nombre_etoiles, temps_cible  # noqa: E402
from jeu.niveau import charger_campagne  # noqa: E402
from ecrans.carte import courbe, positions_noeuds  # noqa: E402


class TestEtoiles(unittest.TestCase):

    def test_masque(self):
        niveau = charger_campagne()[0]
        self.assertEqual(etoiles_niveau(0, 10, niveau), 7)
        self.assertEqual(etoiles_niveau(2, 10, niveau), 5)
        self.assertEqual(etoiles_niveau(0, 999, niveau), 3)
        self.assertEqual(etoiles_niveau(1, 999, niveau), 1)
        self.assertEqual(nombre_etoiles(5), 2)
        # Deux parties différentes : les étoiles s'additionnent.
        self.assertEqual(nombre_etoiles(etoiles_niveau(2, 10, niveau) | etoiles_niveau(0, 999, niveau)), 3)

    def test_temps_cible_boss_plus_long(self):
        niveaux = charger_campagne()
        boss = next(n for n in niveaux if n.boss)
        normal = next(n for n in niveaux if not n.boss)
        self.assertGreater(temps_cible(boss), temps_cible(normal))


class TestCarte(unittest.TestCase):

    def test_positions(self):
        niveaux = charger_campagne()
        positions = positions_noeuds(niveaux)
        self.assertEqual(len(positions), len(niveaux))
        xs = [x for x, _ in positions]
        self.assertEqual(xs, sorted(xs))                    # le chemin avance vers la droite
        for _, y in positions:
            self.assertTrue(150 < y < 470)                  # au-dessus de l'horizon

    def test_courbe_passe_par_les_points(self):
        points = [(0, 0), (100, 50), (200, 0)]
        lisse = courbe(points)
        self.assertEqual(lisse[0], (0, 0))
        self.assertEqual(lisse[-1], (200, 0))
        self.assertTrue(any(abs(x - 100) < 1 and abs(y - 50) < 1 for x, y in lisse))


if __name__ == "__main__":
    unittest.main()
