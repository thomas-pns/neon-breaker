# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Test de la vue retournée du Duel en ligne : chez le joueur 2, sa raquette
    (en haut sur le serveur) est dessinée en bas de l'écran.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 25/10/2026
"""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from tests import dossier_temporaire  # noqa: E402

os.environ.setdefault("NEON_DONNEES", dossier_temporaire())


class FauxTempsReel:
    etat = "ouvert"
    ping = 40

    def messages(self):
        return []

    def envoyer(self, message):
        pass

    def fermer(self):
        pass


class TestVueDuel(unittest.TestCase):

    def test_j2_se_voit_en_bas(self):
        from moteur.application import Application
        from serveur.simulation import Simulation
        from ecrans.en_ligne.partie import EcranPartieEnLigne
        app = Application()
        app.en_ligne.ouvrir_temps_reel = lambda: FauxTempsReel()
        simulation = Simulation("duel", ["a", "b"])
        etat = simulation.instantane(forcer=True)
        couleur_j2 = simulation.mode.joueurs[1].couleur_bord
        for numero in (1, 2):
            ecran = EcranPartieEnLigne(app, {"numero": numero, "mode": "duel",
                                             "joueurs": ["a", "b"]})
            app.remplacer(ecran, transition=False)
            ecran.sur_etat(dict(etat))
            app._dessiner()
            terrain = ecran.mode.terrains[0]
            raquette_j2 = ecran.mode.joueurs[1].raquette
            x = int(raquette_j2.x)
            haut = int(raquette_j2.y + raquette_j2.hauteur / 2)
            bas = terrain.rect.top + terrain.rect.bottom - haut
            image = app.ecran.image
            # Le bord de la raquette du J2 (sa couleur) est en haut chez J1, en bas chez J2.
            def proche(y):
                return any(sum(abs(a - b) for a, b in zip(image.get_at((x + dx, y + dy))[:3],
                                                           couleur_j2)) < 120
                           for dx in range(-40, 41, 4) for dy in range(-8, 9))
            if numero == 1:
                self.assertTrue(proche(haut))
                self.assertFalse(ecran.vue_retournee)
            else:
                self.assertTrue(proche(bas))
                self.assertTrue(ecran.vue_retournee)


if __name__ == "__main__":
    unittest.main()
