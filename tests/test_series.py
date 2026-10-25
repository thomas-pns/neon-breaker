# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Tests des séries de défis (jours et semaines d'affilée) et du défi de la
    semaine (même mur pour tout le monde, deux règles différentes).

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 25/10/2026
"""

import datetime
import unittest

from reseau import series


class TestSeries(unittest.TestCase):

    def test_jours(self):
        jours = ["2026-10-20", "2026-10-21", "2026-10-22", "2026-10-24", "2026-10-25"]
        self.assertEqual(series.record(jours), 3)
        self.assertEqual(series.en_cours(jours, datetime.date(2026, 10, 25)), 2)
        self.assertEqual(series.en_cours(jours, datetime.date(2026, 10, 26)), 2)  # hier compte
        self.assertEqual(series.en_cours(jours, datetime.date(2026, 10, 27)), 0)
        self.assertEqual(series.record([]), 0)
        self.assertEqual(series.en_cours(["n'importe"], datetime.date(2026, 1, 1)), 0)
        self.assertEqual(series.record(["2026-10-20", "2026-10-20"]), 1)

    def test_semaines(self):
        self.assertEqual(series.id_semaine(datetime.date(2026, 10, 25)), "2026-W43")
        self.assertEqual(series.lundi_de("2026-W43"), datetime.date(2026, 10, 19))
        semaines = ["2026-W41", "2026-W42", "2026-W43"]
        self.assertEqual(series.record(semaines, semaines=True), 3)
        self.assertEqual(series.en_cours(semaines, datetime.date(2026, 10, 28), semaines=True), 3)
        self.assertEqual(series.en_cours(semaines, datetime.date(2026, 11, 1), semaines=True), 3)
        self.assertEqual(series.en_cours(semaines, datetime.date(2026, 11, 2), semaines=True), 0)
        # Passage d'année (2026 a 53 semaines ISO).
        self.assertEqual(series.record(["2026-W53", "2027-W01"], semaines=True), 2)

    def test_defi_semaine(self):
        from jeu.modes.defi import defi_semaine_pour, semaine_du_defi
        graine, mods = defi_semaine_pour("2026-W43")
        self.assertEqual((graine, mods), defi_semaine_pour("2026-W43"))
        self.assertEqual(len(mods), 2)
        self.assertNotEqual(mods[0][0], mods[1][0])
        self.assertNotIn("classique", [m[0] for m in mods])
        self.assertEqual(semaine_du_defi(datetime.datetime(2026, 10, 25, 12)), "2026-W43")


if __name__ == "__main__":
    unittest.main()
