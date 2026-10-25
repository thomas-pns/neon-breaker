# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Verifier la page d'aide, les bulles de premiere fois et leur sauvegarde.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Realise le 23/10/2026
"""

import os
import sys
import unittest
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from tests import dossier_temporaire  # noqa: E402
from moteur import sauvegarde  # noqa: E402
from ecrans.aide import EcranAide, PAGES  # noqa: E402
from ecrans.bulles import afficher  # noqa: E402
from ecrans.options import EcranOptions  # noqa: E402


class TestAideBulles(unittest.TestCase):
    """But : couvrir les premieres bulles et les pages de l'aide."""

    def setUp(self):
        pygame.init()

    def tearDown(self):
        pygame.quit()

    def test_bulles_pouvoir_et_overdrive_une_fois(self):
        """But : chaque code est affiche et sauvegarde une seule fois."""
        app = SimpleNamespace(donnees={"bulles_vues": []}, enregistrer=lambda: None)
        mode = SimpleNamespace(en_ligne=False, hardcore=False, deux_joueurs=False,
                               app=app, bulle=None)
        joueur = SimpleNamespace(numero=1, avec_pouvoirs=True)
        for code in ("pouvoir", "overdrive", "pouvoir", "overdrive"):
            afficher(mode, code, joueur)
            self.assertEqual(mode.bulle[1], 5.0)
        self.assertEqual(app.donnees["bulles_vues"], ["pouvoir", "overdrive"])

    def test_aucune_bulle_en_ligne(self):
        """But : le mode en ligne ne memorise ni ne montre de bulle."""
        app = SimpleNamespace(donnees={"bulles_vues": []}, enregistrer=lambda: None)
        mode = SimpleNamespace(en_ligne=True, hardcore=False, deux_joueurs=False,
                               app=app, bulle=None)
        afficher(mode, "pouvoir", SimpleNamespace(numero=1, avec_pouvoirs=True))
        self.assertIsNone(mode.bulle)
        self.assertEqual(app.donnees["bulles_vues"], [])

    def test_revoir_vide_les_codes_vus(self):
        """But : REVOIR reactive les bulles dans OPTIONS."""
        app = SimpleNamespace(donnees={"bulles_vues": ["pouvoir"]},
                              audio=SimpleNamespace(jouer=lambda nom: None),
                              ecran=SimpleNamespace(basculer_plein_ecran=lambda: None),
                              enregistrer=lambda: None,
                              reglages={"volume_musique": 0.5, "volume_effets": 0.7,
                                        "crt": True, "tremblement": True,
                                        "particules": "haut"})
        ecran = EcranOptions.__new__(EcranOptions)
        ecran.app = app
        ecran.bulles_reactivees = False
        ecran.menu = SimpleNamespace(indice=0, options=[])
        ecran._nom_defaut = lambda numero: "AAA"
        EcranOptions._revoir_bulles(ecran)
        self.assertEqual(app.donnees["bulles_vues"], [])
        self.assertTrue(ecran.bulles_reactivees)
        self.assertIn("BULLES D'AIDE : REACTIVEES", [o[0] for o in ecran.menu.options])

    def test_ancienne_sauvegarde_et_pages_aide(self):
        """But : completer une sauvegarde ancienne et dessiner toutes les pages."""
        dossier = dossier_temporaire("aide_bulles_")
        chemin = os.path.join(dossier, "sauvegarde.json")
        with open(chemin, "w", encoding="utf-8") as fichier:
            fichier.write('{"version": 1}')
        self.assertEqual(sauvegarde.charger(chemin)["bulles_vues"], [])

        class Fond:
            """Fond factice pour dessiner l'ecran d'aide."""

            def dessiner(self, image):
                """But : effacer la surface."""
                image.fill((0, 0, 0))

        app = SimpleNamespace(fond=Fond())
        aide = EcranAide(app)
        image = pygame.Surface((1280, 720))
        for indice in range(len(PAGES)):
            aide.page = indice
            aide.dessiner(image)
        self.assertIn("POUVOIRS ET OVERDRIVE", PAGES)


if __name__ == "__main__":
    unittest.main()
