# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Tests des mécaniques du jalon 2 : joueur (combo, OVERDRIVE, effets,
    inventaire), capsules, pouvoirs, briques spéciales (explosive en
    chaîne, portail, régénérante, fantôme, métal fondu par le feu),
    raquettes multiples.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026
"""

import os
import random
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from structures.liste import Liste  # noqa: E402
from moteur import config  # noqa: E402
from jeu.balle import Balle  # noqa: E402
from jeu.brique import (BriqueExplosive, BriqueNormale, BriqueMetal, BriquePortail,  # noqa: E402
                        BriqueRegenerante, BriqueFantome)
from jeu.capsule import CATALOGUE, tirer_effet  # noqa: E402
from jeu.joueur import Joueur  # noqa: E402
from jeu.pouvoirs import appliquer_capsule, activer_pouvoir, declencher_supernova  # noqa: E402
from jeu.terrain import Terrain  # noqa: E402


def terrain_avec(briques, joueur=None):
    """Terrain 400x600 avec une raquette et les briques données."""
    terrain = Terrain(pygame.Rect(0, 0, 400, 600))
    joueur = joueur or Joueur()
    terrain.ajouter_raquette(joueur, -1)
    liste = Liste()
    for brique in briques:
        liste.ajouter_fin(brique)
    terrain.remplir(liste, cascade=False)
    terrain.chance_capsule = 0
    return terrain, joueur


def vider(terrain):
    """Défile tous les événements et renvoie leurs natures."""
    natures = []
    while not terrain.evenements.est_vide():
        natures.append(terrain.evenements.defiler()[0])
    return natures


class TestJoueur(unittest.TestCase):

    def test_combo_et_overdrive(self):
        joueur = Joueur()
        for _ in range(5):
            gain, monte = joueur.marquer_brique(10)
        self.assertTrue(monte)
        self.assertEqual(joueur.multiplicateur, 2)
        self.assertEqual(gain, 20)
        self.assertGreater(joueur.overdrive, 0)
        joueur.overdrive = 1.0
        self.assertTrue(declencher_supernova(joueur))
        self.assertEqual(joueur.overdrive, 0)
        self.assertGreater(joueur.supernova, 0)
        self.assertFalse(declencher_supernova(joueur))

    def test_effets_et_opposes(self):
        joueur = Joueur()
        joueur.ajouter_effet("elargir", 5)
        self.assertEqual(joueur.facteur_largeur(), 1.5)
        joueur.ajouter_effet("retrecir", 5)           # annule l'élargissement
        self.assertEqual(joueur.facteur_largeur(), 1.0)
        joueur.ajouter_effet("vitesse", 1)
        self.assertAlmostEqual(joueur.facteur_vitesse_balles(), 1.4)
        self.assertEqual(joueur.mettre_a_jour(2), ["vitesse"])
        self.assertFalse(joueur.actif("vitesse"))

    def test_inventaire(self):
        joueur = Joueur()
        terrain, _ = terrain_avec([], joueur)
        for _ in range(3):
            self.assertEqual(appliquer_capsule("laser", joueur, terrain), "stocke")
        self.assertEqual(appliquer_capsule("laser", joueur, terrain), "plein")
        self.assertEqual(joueur.score, 500)
        joueur.selection = 2
        self.assertEqual(joueur.retirer_pouvoir(2), "laser")
        self.assertEqual(joueur.selection, 1)


class TestCapsules(unittest.TestCase):

    def test_catalogue_complet(self):
        categories = [e.categorie for e in CATALOGUE.values()]
        self.assertEqual(categories.count("bonus"), 7)
        self.assertEqual(categories.count("malus"), 6)
        self.assertEqual(categories.count("pouvoir"), 6)
        lettres = [e.lettre for e in CATALOGUE.values()]
        self.assertEqual(len(lettres), len(set(lettres)), "lettres en double")

    def test_tirage_respecte_les_categories(self):
        aleatoire = random.Random(1)
        for _ in range(200):
            code = tirer_effet({"malus": 1}, aleatoire)
            self.assertEqual(CATALOGUE[code].categorie, "malus")
        self.assertIsNone(tirer_effet({"bonus": 0}, aleatoire))

    def test_multi_balle(self):
        terrain, joueur = terrain_avec([])
        balle = Balle(200, 300)
        balle.collee = False
        balle.vx, balle.vy = 100, -400
        terrain.balles.ajouter_fin(balle)
        appliquer_capsule("multi", joueur, terrain)
        self.assertEqual(len(terrain.balles), 3)

    def test_capsule_attrapee(self):
        terrain, joueur = terrain_avec([BriqueNormale(180, 100, 40, 20, config.ROSE)])
        terrain.chance_capsule = 1.0
        brique = next(iter(terrain.briques))
        terrain.endommager(brique, joueur)
        self.assertEqual(len(terrain.capsules), 1)
        capsule = next(iter(terrain.capsules))
        capsule.x = joueur.raquette.x
        for _ in range(600):
            terrain.mettre_a_jour(1 / 120, {})
        self.assertIn("capsule", vider(terrain))


class TestBriquesSpeciales(unittest.TestCase):

    def test_explosion_en_chaine(self):
        # Rangée : explosive, explosive, normale, puis une normale éloignée.
        pas = 44
        briques = [BriqueExplosive(20, 100, 40, 20), BriqueExplosive(20 + pas, 100, 40, 20),
                   BriqueNormale(20 + 2 * pas, 100, 40, 20, config.CYAN),
                   BriqueNormale(20 + 6 * pas, 100, 40, 20, config.CYAN)]
        terrain, joueur = terrain_avec(briques)
        terrain.brique_l = 40
        terrain.endommager(briques[0], joueur)
        restantes = list(terrain.briques)
        self.assertEqual(restantes, [briques[3]])
        self.assertIn("explosion", vider(terrain))

    def test_metal_fondu_par_le_feu(self):
        metal = BriqueMetal(0, 0, 40, 20)
        self.assertFalse(metal.frapper())
        self.assertTrue(metal.frapper(feu=True))

    def test_fantome_deux_coups(self):
        fantome = BriqueFantome(0, 0, 40, 20)
        self.assertFalse(fantome.frapper())
        self.assertTrue(fantome.revelee)
        self.assertTrue(fantome.frapper())

    def test_portail(self):
        entree = BriquePortail(100, 300, 40, 20)
        sortie = BriquePortail(300, 100, 40, 20)
        terrain, _ = terrain_avec([entree, sortie])
        self.assertIs(entree.jumeau, sortie)
        balle = Balle(120, 340)
        balle.collee = False
        balle.vx, balle.vy = 0, -300
        terrain.balles.ajouter_fin(balle)
        for _ in range(20):
            terrain.mettre_a_jour(1 / 120, {})
        self.assertGreater(balle.x, 280)
        self.assertLess(balle.y, 110)
        self.assertIn("portail", vider(terrain))

    def test_regeneration(self):
        a = BriqueRegenerante(20, 100, 40, 20)
        b = BriqueRegenerante(200, 100, 40, 20)
        terrain, joueur = terrain_avec([a, b])
        terrain.endommager(a, joueur)
        self.assertEqual(terrain.briques_restantes(), 2)    # a compte encore
        for _ in range(int(6.2 * 120)):
            terrain.mettre_a_jour(1 / 120, {})
        self.assertIn(a, list(terrain.briques))
        # Les deux détruites coup sur coup : aucune ne revient.
        terrain.endommager(a, joueur)
        terrain.endommager(b, joueur)
        for _ in range(int(6.2 * 120)):
            terrain.mettre_a_jour(1 / 120, {})
        self.assertEqual(terrain.briques_restantes(), 0)


class TestPouvoirs(unittest.TestCase):

    def test_bombe(self):
        briques = [BriqueNormale(20 + c * 44, 100 + l * 26, 40, 20, config.CYAN)
                   for c in range(8) for l in range(5)]
        terrain, joueur = terrain_avec(briques)
        activer_pouvoir("bombe", joueur, terrain)
        self.assertTrue(joueur.bombe_armee)
        balle = Balle(20 + 3 * 44 + 20, 100 + 5 * 26 + 12)
        balle.collee = False
        balle.proprietaire = joueur
        balle.vx, balle.vy = 0, -400
        terrain.balles.ajouter_fin(balle)
        for _ in range(30):
            terrain.mettre_a_jour(1 / 120, {})
        self.assertFalse(joueur.bombe_armee)
        self.assertLessEqual(len(terrain.briques), 40 - 12)

    def test_onde_de_choc(self):
        briques = [BriqueNormale(20 + c * 44, 60 + l * 26, 40, 20, config.CYAN)
                   for c in range(4) for l in range(6)]
        terrain, joueur = terrain_avec(briques)
        activer_pouvoir("onde", joueur, terrain)
        self.assertEqual(len(terrain.briques), 12)            # 3 lignes sur 6 détruites

    def test_laser_et_bouclier(self):
        terrain, joueur = terrain_avec([BriqueNormale(120, 100, 160, 20, config.CYAN)])
        activer_pouvoir("laser", joueur, terrain)
        joueur.raquette.x = 200
        for _ in range(120):
            terrain.mettre_a_jour(1 / 120, {})
        self.assertEqual(len(terrain.briques), 0)
        activer_pouvoir("bouclier", joueur, terrain)
        balle = Balle(200, 560)
        balle.collee = False
        balle.vx, balle.vy = 0, 600
        terrain.balles.ajouter_fin(balle)
        joueur.raquette.x = 60
        for _ in range(120):
            terrain.mettre_a_jour(1 / 120, {})
        self.assertIn(balle, list(terrain.balles))

    def test_raquettes_se_repoussent(self):
        terrain = Terrain(pygame.Rect(0, 0, 600, 600))
        a = terrain.ajouter_raquette(Joueur(1, "j1"), -1)
        b = terrain.ajouter_raquette(Joueur(2, "j2"), -1)
        a.x = b.x = 300
        terrain.mettre_a_jour(1 / 120, {})
        self.assertGreaterEqual(abs(a.x - b.x), (a.largeur + b.largeur) / 2)

    def test_raquette_du_haut_renvoie_vers_le_bas(self):
        terrain = Terrain(pygame.Rect(0, 0, 600, 600), mur_haut=False)
        haut = terrain.ajouter_raquette(Joueur(2, "j2"), +1)
        balle = Balle(haut.x, haut.y + 60)
        balle.collee = False
        balle.vx, balle.vy = 0, -500
        terrain.balles.ajouter_fin(balle)
        for _ in range(20):
            terrain.mettre_a_jour(1 / 120, {})
        self.assertGreater(balle.vy, 0)
        self.assertIs(balle.proprietaire, haut.joueur)


if __name__ == "__main__":
    unittest.main()
