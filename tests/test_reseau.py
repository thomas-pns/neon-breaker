# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Tests du réseau côté jeu : un instantané capturé sur le serveur puis
    appliqué au client reproduit fidèlement la partie (briques, balles,
    raquettes, scores, boss), comparaison de versions, plateformes.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import json
import os
import sys
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ["NEON_DONNEES"] = tempfile.mkdtemp(prefix="neon_test_client_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from moteur.version import comparer_versions  # noqa: E402
from reseau.instantane import appliquer, rejouer_effets  # noqa: E402
from serveur.simulation import Simulation  # noqa: E402


class FausseApp:
    """Le strict nécessaire pour appliquer un instantané sans fenêtre."""

    class Fond:
        monde, progression, vitesse_cible = 1, 0, 0.8

        def changer_monde(self, monde):
            self.monde = monde

    class Muet:
        def __getattr__(self, nom):
            return lambda *a, **k: None

    def __init__(self):
        self.fond = self.Fond()
        self.audio = self.Muet()
        self.crt = self.Muet()
        self.entrees = self.Muet()
        self.donnees = {"progression": {}}
        self.reglages = {"particules": "bas"}

    def lancer_transition(self, action):
        pass

    def enregistrer(self):
        pass

    def meilleur_score(self, mode):
        return 0


class TestInstantanes(unittest.TestCase):

    def setUp(self):
        pygame.init()

    def jouer(self, code, images=400, niveau=0):
        simulation = Simulation(code, ["ALICE", "BOB"], niveau)
        for i in range(images):
            for numero in (1, 2):
                joueur = simulation.mode.joueurs[numero - 1]
                balles = [b for b in joueur.terrain.balles if not b.collee]
                x = balles[0].x if balles else joueur.raquette.x
                simulation.recevoir_commande(numero, {"x": x, "vx": 0,
                                                      "a": ["action"] if i % 20 == 0 else []})
            simulation.avancer(1 / 60)
        return simulation

    def comparer(self, code, niveau=0):
        from ecrans.en_ligne.partie import creer_mode_client
        from moteur.effets import GestionnaireEffets
        simulation = self.jouer(code, niveau=niveau)
        donnees = json.loads(json.dumps(simulation.instantane(forcer=True)))
        app = FausseApp()
        effets = GestionnaireEffets()
        client = creer_mode_client(code, app, effets, niveau)
        appliquer(client, donnees, app, numero_local=1)
        rejouer_effets(donnees["fx"], app, effets)
        serveur = simulation.mode
        self.assertEqual(client.etat, serveur.etat)
        self.assertEqual([j.score for j in client.joueurs], [j.score for j in serveur.joueurs])
        for t_client, t_serveur in zip(client.terrains, serveur.terrains):
            self.assertEqual(len(t_client.briques), len(t_serveur.briques))
            self.assertEqual(sorted(b.vie for b in t_client.briques),
                             sorted(b.vie for b in t_serveur.briques))
            self.assertEqual(len(t_client.balles), len(t_serveur.balles))
            for bc, bs in zip(t_client.balles, t_serveur.balles):
                self.assertAlmostEqual(bc.x, bs.x, delta=0.2)
                self.assertAlmostEqual(bc.y, bs.y, delta=0.2)
            self.assertEqual(t_client.briques_restantes(), t_serveur.briques_restantes())
            # La raquette distante est en route vers sa position serveur.
            distante = t_client.raquettes[-1]
            if distante.joueur.numero == 2:
                self.assertAlmostEqual(distante.cible_reseau[0], t_serveur.raquettes[-1].x, delta=0.2)
        return client, serveur

    def test_coop(self):
        self.comparer("coop")

    def test_duel(self):
        self.comparer("duel")

    def test_course(self):
        client, serveur = self.comparer("course")
        self.assertEqual(len(client.terrains), 2)

    def test_coop_boss(self):
        client, serveur = self.comparer("coop", niveau=3)
        self.assertIsNotNone(client.terrains[0].boss)
        self.assertEqual(client.terrains[0].boss.vie, serveur.terrains[0].boss.vie)

    def test_instantane_leger_sans_changement(self):
        simulation = self.jouer("duel", images=5)
        simulation.instantane()
        suivant = simulation.instantane()
        # Rien n'a bougé entre deux envois : les briques ne sont pas renvoyées.
        self.assertNotIn("briques", suivant["terrains"][0])


class TestVersions(unittest.TestCase):

    def test_comparaison(self):
        self.assertEqual(comparer_versions("1.0.10", "1.0.9"), 1)
        self.assertEqual(comparer_versions("v1.2.0", "1.2"), 0)
        self.assertEqual(comparer_versions("0.9.9", "1.0.0"), -1)

    def test_version_disponible(self):
        from reseau.mise_a_jour import version_disponible, plateforme
        reponse = {"plateformes": {plateforme(): {"version": "99.0.0", "url": "/x", "sha256": ""}}}
        self.assertEqual(version_disponible(reponse)["version"], "99.0.0")
        reponse = {"plateformes": {plateforme(): {"version": "0.0.1", "url": "/x"}}}
        self.assertIsNone(version_disponible(reponse))
        self.assertIsNone(version_disponible(None))


if __name__ == "__main__":
    unittest.main()
