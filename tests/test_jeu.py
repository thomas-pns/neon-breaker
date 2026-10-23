# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Tests unitaires (python -m unittest) : structures maison, collisions,
    rebond raquette, anti-traversée à grande vitesse, lecture des niveaux,
    multiplicateur de combo, sauvegarde.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026
"""

import math
import os
import shutil
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests import dossier_temporaire  # noqa: E402
import pygame  # noqa: E402

from structures.liste import Liste  # noqa: E402
from structures.file import File  # noqa: E402
from structures.pile import Pile  # noqa: E402
from moteur import sauvegarde  # noqa: E402
from moteur.version import VERSION  # noqa: E402
from ecrans.titre import texte_version  # noqa: E402
from jeu.balle import Balle  # noqa: E402
from jeu.brique import BriqueNormale, BriqueMetal, BriqueSolide, fabriquer_brique  # noqa: E402
from jeu.niveau import lire_niveau, charger_campagne, ErreurNiveau  # noqa: E402
from jeu import terrain as t  # noqa: E402
from jeu.joueur import Joueur, multiplicateur_pour  # noqa: E402
from jeu.capsule import CATALOGUE, tirer_effet  # noqa: E402
from jeu.pouvoirs import appliquer_capsule, activer_pouvoir, declencher_supernova  # noqa: E402


class TestStructures(unittest.TestCase):

    def test_liste_ajout_suppression(self):
        liste = Liste()
        a, b, c = object(), object(), object()
        for x in (a, b, c):
            liste.ajouter_fin(x)
        self.assertEqual(len(liste), 3)
        self.assertTrue(liste.supprimer(b))
        self.assertEqual(list(liste), [a, c])
        self.assertTrue(liste.supprimer(c))
        liste.ajouter_fin(b)                 # la queue doit être à jour
        self.assertEqual(list(liste), [a, b])

    def test_liste_retirer_si(self):
        liste = Liste()
        for i in range(10):
            liste.ajouter_fin(i)
        self.assertEqual(liste.retirer_si(lambda v: v % 2 == 0), 5)
        self.assertEqual(list(liste), [1, 3, 5, 7, 9])
        liste.ajouter_fin(11)
        self.assertEqual(list(liste)[-1], 11)
        liste.retirer_si(lambda v: True)
        self.assertTrue(liste.est_vide())
        liste.ajouter_fin(1)
        self.assertEqual(list(liste), [1])

    def test_file_et_pile(self):
        file, pile = File(), Pile()
        for i in range(3):
            file.enfiler(i)
            pile.empiler(i)
        self.assertEqual([file.defiler() for _ in range(3)], [0, 1, 2])
        self.assertEqual(pile.sommet(), 2)
        self.assertEqual([pile.depiler() for _ in range(3)], [2, 1, 0])
        self.assertTrue(file.est_vide() and pile.est_vide())


class TestCollisions(unittest.TestCase):

    def setUp(self):
        pygame.init()

    def test_disque_touche_boite(self):
        boite = (0, 0, 100, 20)
        self.assertTrue(t.disque_touche_boite(50, 25, 8, boite))
        self.assertFalse(t.disque_touche_boite(50, 30, 8, boite))
        # Coin : distance diagonale.
        self.assertFalse(t.disque_touche_boite(106, 26, 8, boite))
        self.assertTrue(t.disque_touche_boite(104, 24, 8, boite))

    def test_rebond_face_du_dessous(self):
        balle = Balle(50, 26)
        balle.vx, balle.vy = 100, -300
        face = t.rebondir_sur_boite(balle, (0, 0, 100, 20))
        self.assertEqual(face, "bas")
        self.assertGreater(balle.vy, 0)
        self.assertGreaterEqual(balle.y, 20 + balle.rayon)

    def test_rebond_raquette_angle(self):
        # Impact au centre en tombant verticalement : repart verticalement.
        balle = Balle(100, 0)
        balle.vx, balle.vy = 0, 500
        t.rebond_raquette(balle, (50, 0, 150, 16))
        self.assertAlmostEqual(balle.vx, 0, places=5)
        self.assertLess(balle.vy, 0)
        self.assertAlmostEqual(balle.vitesse(), 500, places=3)
        # Impact au bord droit : repart vers la droite, au plus 70° de la verticale.
        balle = Balle(150, 0)
        balle.vx, balle.vy = 300, 400
        t.rebond_raquette(balle, (50, 0, 150, 16))
        angle = math.degrees(math.atan2(balle.vx, -balle.vy))
        self.assertGreater(angle, 0)
        self.assertLessEqual(angle, 70.0001)

    def test_rebond_raquette_du_haut(self):
        # Raquette du haut (Duel, jalon 4) : la balle repart vers le bas.
        balle = Balle(100, 0)
        balle.vx, balle.vy = 0, -500
        t.rebond_raquette(balle, (50, 0, 150, 16), sens=1)
        self.assertAlmostEqual(balle.vx, 0, places=5)
        self.assertGreater(balle.vy, 0)

    def test_pas_de_traversee_a_grande_vitesse(self):
        terrain = t.Terrain(pygame.Rect(0, 0, 400, 600))
        briques = Liste()
        brique = BriqueMetal(150, 200, 100, 10)       # brique très fine
        briques.ajouter_fin(brique)
        terrain.remplir(briques)
        balle = Balle(200, 400)
        balle.collee = False
        balle.vx, balle.vy = 0, -6000                  # 50 px par pas !
        terrain.balles.ajouter_fin(balle)
        for _ in range(8):                            # 400 px de trajet possible
            terrain.mettre_a_jour(1 / 120, {})
        self.assertGreater(balle.vy, 0, "la balle aurait dû rebondir")
        self.assertGreater(balle.y, 210)

    def test_balle_perdue_et_evenements(self):
        terrain = t.Terrain(pygame.Rect(0, 0, 400, 600))
        balle = Balle(20, 590)
        balle.collee = False
        balle.vx, balle.vy = 0, 900
        terrain.balles.ajouter_fin(balle)
        for _ in range(10):
            terrain.mettre_a_jour(1 / 120, {})
        natures = []
        while not terrain.evenements.est_vide():
            natures.append(terrain.evenements.defiler()[0])
        self.assertIn("balle_perdue", natures)
        self.assertIn("plus_de_balle", natures)
        self.assertIn("niveau_vide", natures)        # aucune brique


class TestBriquesEtNiveaux(unittest.TestCase):

    def test_briques(self):
        normale = BriqueNormale(0, 0, 10, 10, (1, 2, 3))
        self.assertTrue(normale.frapper())
        solide = BriqueSolide(0, 0, 10, 10, (1, 2, 3), vie=3)
        self.assertFalse(solide.frapper())
        self.assertFalse(solide.frapper())
        self.assertTrue(solide.frapper())
        metal = BriqueMetal(0, 0, 10, 10)
        for _ in range(20):
            self.assertFalse(metal.frapper())
        self.assertFalse(metal.destructible)

    def test_fabrique(self):
        self.assertIsInstance(fabriquer_brique("a", 0, 0), BriqueNormale)
        self.assertIsInstance(fabriquer_brique("R", 0, 0), BriqueSolide)
        self.assertEqual(fabriquer_brique("4", 0, 0).vie, 4)
        self.assertIsInstance(fabriquer_brique("M", 0, 0), BriqueMetal)
        self.assertIsNone(fabriquer_brique(".", 0, 0))

    def test_lire_niveau(self):
        niveau = lire_niveau("nom: TEST\nvitesse: 1.2\n---\naa..\n\nMM\n")
        self.assertEqual(niveau.nom, "TEST")
        self.assertAlmostEqual(niveau.vitesse, 1.2)
        self.assertEqual(niveau.grille, ["aa..", "MM"])
        briques = niveau.construire(t.Terrain(pygame.Rect(0, 0, 760, 700)))
        self.assertEqual(len(briques), 4)
        with self.assertRaises(ErreurNiveau):
            lire_niveau("nom: SANS SEPARATEUR\naaaa")

    def test_campagne_livree(self):
        niveaux = charger_campagne()
        self.assertEqual(len(niveaux), 12)
        self.assertEqual([n.boss for n in niveaux if n.boss], ["sunset", "gridlock", "core"])
        for niveau in niveaux:
            for rangee in niveau.grille:
                self.assertEqual(len(rangee), 12, niveau.nom)
            briques = niveau.construire(t.Terrain(pygame.Rect(260, 24, 760, 696)))
            self.assertTrue(any(b.destructible for b in briques), niveau.nom)


class TestScoreEtSauvegarde(unittest.TestCase):

    def test_multiplicateur(self):
        self.assertEqual(multiplicateur_pour(0), 1)
        self.assertEqual(multiplicateur_pour(4), 1)
        self.assertEqual(multiplicateur_pour(5), 2)
        self.assertEqual(multiplicateur_pour(10), 3)
        self.assertEqual(multiplicateur_pour(20), 5)
        self.assertEqual(multiplicateur_pour(99), 8)

    def test_sauvegarde_aller_retour_et_corruption(self):
        dossier = dossier_temporaire("neon_test_sauvegarde_")
        self.addCleanup(shutil.rmtree, dossier, True)
        chemin = os.path.join(dossier, "s.json")
        donnees = sauvegarde.charger(chemin)            # absent -> défaut
        donnees["meilleurs"]["campagne"] = 1234
        self.assertTrue(sauvegarde.enregistrer(donnees, chemin))
        self.assertEqual(sauvegarde.charger(chemin)["meilleurs"]["campagne"], 1234)
        with open(chemin, "w", encoding="utf-8") as fichier:
            fichier.write("{pas du json")
        relu = sauvegarde.charger(chemin)
        self.assertEqual(relu["meilleurs"], {})
        self.assertIn("crt", relu["reglages"])


class TestEcranTitre(unittest.TestCase):
    def test_texte_version(self):
        self.assertEqual(texte_version(), "V" + VERSION)


class TestNouveautes11(unittest.TestCase):
    """Défi du jour, skins et musique (version 1.1)."""

    def test_defi_identique_pour_tous(self):
        from jeu.modes.defi import defi_pour, jour_du_defi
        from jeu.niveau import generer_rangee
        import datetime
        import random
        graine, modificateur = defi_pour("2026-10-21")
        self.assertEqual((graine, modificateur), defi_pour("2026-10-21"))
        self.assertNotEqual(graine, defi_pour("2026-10-22")[0])
        a, b = random.Random(graine), random.Random(graine)
        self.assertEqual([generer_rangee(v / 6, a) for v in range(30)],
                         [generer_rangee(v / 6, b) for v in range(30)])
        self.assertEqual(jour_du_defi(datetime.datetime(2026, 1, 2, 23, 59)), "2026-01-02")

    def test_skins_debloques(self):
        from reseau.profil import skins_debloques, SKINS, SKINS_PAR_CODE
        self.assertEqual(skins_debloques(1, set()), ["neon"])
        self.assertIn("cryo", skins_debloques(5, set()))
        self.assertNotIn("cryo", skins_debloques(4, set()))
        self.assertIn("noyau", skins_debloques(1, {"boss_core"}))
        self.assertEqual(len(skins_debloques(99, {s["condition"][1] for s in SKINS
                                                  if s["condition"] and s["condition"][0] == "succes"})),
                         len(SKINS))
        from jeu.joueur import Joueur
        joueur = Joueur(2, "j2", "J2")
        bord = joueur.couleur_bord
        joueur.appliquer_skin("sunset", garder_bord=True)
        self.assertEqual(joueur.couleur_bord, bord)
        self.assertEqual(joueur.couleur_corps, SKINS_PAR_CODE["sunset"]["corps"])
        joueur.appliquer_skin("inconnu")
        self.assertEqual(joueur.skin, "neon")

    def test_condition_skin_emploie_rang(self):
        from reseau.profil import condition_lisible, SKINS_PAR_CODE
        self.assertEqual(condition_lisible(SKINS_PAR_CODE["cryo"]), "SE DEBLOQUE AU RANG 5")
    def test_musique_boucle(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest("numpy absent")
        from moteur import musique
        boucle = musique.composer("overdrive", np)
        self.assertLessEqual(float(np.max(np.abs(boucle))), 0.86)
        mesures = len(musique.PARTITIONS["overdrive"]["accords"])
        attendu = 60 / musique.PARTITIONS["overdrive"]["bpm"] * 4 * mesures
        self.assertAlmostEqual(len(boucle) / musique.FREQ, attendu, delta=0.01)


if __name__ == "__main__":
    unittest.main()
