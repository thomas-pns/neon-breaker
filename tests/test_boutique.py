# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Tests de l'économie de la 2.0 (reseau/boutique.py) : gains d'une partie
    (une seule fois par niveau, boss, défi), plafond de participation,
    sélection du jour et boîte mystère.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 25/10/2026
"""

import random
import unittest

from reseau import boutique as b
from reseau.profil import SKINS


class TestGains(unittest.TestCase):

    def test_niveaux_et_boss_payes_une_seule_fois(self):
        cumul = {}
        rapport = {"mode": "campagne", "indice_depart": 0, "duree": 10,
                   "stats": {"niveaux_finis": 3, "boss_vaincus": ["sunset"]}}
        detail = b.gains_partie(rapport, cumul, "2026-10-25")
        self.assertEqual(b.total(detail), 3 * b.GAIN_NIVEAU + b.GAIN_BOSS)
        self.assertEqual(b.total(b.gains_partie(rapport, cumul, "2026-10-25")), 0)
        # Les niveaux suivants rapportent, pas ceux déjà payés.
        suite = {"mode": "campagne", "indice_depart": 2, "duree": 10,
                 "stats": {"niveaux_finis": 2, "boss_vaincus": []}}
        self.assertEqual(b.total(b.gains_partie(suite, cumul, "2026-10-25")), b.GAIN_NIVEAU)

    def test_hardcore_paie_double(self):
        rapport = {"mode": "hardcore", "indice_depart": 0, "duree": 0,
                   "stats": {"niveaux_finis": 1}}
        self.assertEqual(b.total(b.gains_partie(rapport, {}, "2026-10-25")), 2 * b.GAIN_NIVEAU)

    def test_defi_et_serie(self):
        cumul = {}
        rapport = {"mode": "defi", "jour": "2026-10-25", "duree": 0, "stats": {}}
        detail = b.gains_partie(rapport, cumul, "2026-10-25", serie_defi=4)
        self.assertEqual(b.total(detail), b.GAIN_DEFI + 3 * b.GAIN_DEFI_SERIE)
        self.assertEqual(b.gains_partie(rapport, cumul, "2026-10-25", 4), [])

    def test_participation_plafonnee_par_jour(self):
        cumul = {}
        rapport = {"mode": "arcade", "duree": 60, "score": 10 ** 6, "stats": {}}
        gagne = sum(b.total(b.gains_partie(rapport, cumul, "2026-10-25")) for _ in range(20))
        self.assertEqual(gagne, b.PARTICIPATION_JOUR)
        self.assertGreater(b.total(b.gains_partie(rapport, cumul, "2026-10-26")), 0)
        courte = {"mode": "arcade", "duree": 10, "score": 10 ** 6, "stats": {}}
        self.assertEqual(b.gains_partie(courte, {}, "2026-10-25"), [])

    def test_victoire_en_ligne(self):
        rapport = {"mode": "duel", "en_ligne": True, "numero": 2, "gagnant": 2,
                   "duree": 0, "stats": {}}
        self.assertEqual(b.total(b.gains_partie(rapport, {}, "2026-10-25")),
                         b.GAIN_PARTIE_EN_LIGNE + b.GAIN_VICTOIRE_EN_LIGNE)


class TestBoutique(unittest.TestCase):

    def test_catalogue_coherent(self):
        codes = [o["code"] for o in b.tous_les_objets()]
        self.assertEqual(len(codes), len(set(codes)), "codes en double")
        for o in b.tous_les_objets():
            self.assertIn(o["rarete"], b.RARETES)
            self.assertGreater(o["prix"], 0)
        self.assertTrue(b.skins_premium())
        self.assertFalse(set(codes) & {s["code"] for s in SKINS
                                       if not s["condition"] or s["condition"][0] != "boutique"})

    def test_selection_du_jour(self):
        jour = b.selection_du_jour("2026-10-25")
        self.assertEqual(jour, b.selection_du_jour("2026-10-25"))     # même pour tous
        self.assertEqual(len(jour), b.TAILLE_SELECTION)
        self.assertEqual(sum(o["promo"] for o in jour), 1)
        self.assertEqual(sum(o["type"] == "skin" for o in jour), 2)
        self.assertFalse(any(o["rarete"] == "legendaire" for o in jour))
        promo = next(o for o in jour if o["promo"])
        self.assertLess(promo["prix"], promo["prix_normal"])
        autres = {o["code"] for o in b.selection_du_jour("2026-10-26")}
        self.assertNotEqual({o["code"] for o in jour}, autres)

    def test_boite_mystere(self):
        hasard = random.Random(3)
        possedes = set()
        for _ in range(len(b.tous_les_objets())):
            gagne = b.tirer_boite(possedes, hasard)
            self.assertNotIn(gagne["code"], possedes)
            possedes.add(gagne["code"])
        self.assertIsNone(b.tirer_boite(possedes, hasard))


if __name__ == "__main__":
    unittest.main()
