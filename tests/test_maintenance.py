# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Verifier la gestion de maintenance du serveur et la proposition de mise a jour.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Realise le 23/10/2026
"""

import os
import sys
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reseau import client
from moteur import config


class TestMaintenance(unittest.TestCase):
    """Tests des erreurs HTTP et du controle de version."""

    def test_serveur_injoignable(self):
        """But : verifier un serveur injoignable. Entree(s) : aucune. Sortie : aucune."""
        resultat = client.requete_http("http://127.0.0.1:9")
        self.assertEqual(resultat["erreur"], "SERVEUR EN MAINTENANCE")
        self.assertTrue(resultat["maintenance"])

    def test_codes_http(self):
        """But : verifier le classement des erreurs HTTP. Entree(s) : aucune. Sortie : aucune."""
        for code, message, maintenance in ((502, "SERVEUR EN MAINTENANCE", True),
                                           (404, "ABSENT", False)):
            erreur = __import__("urllib.error", fromlist=["HTTPError"]).HTTPError(
                "http://127.0.0.1:9", code, "", {}, None)
            erreur.read = lambda: b'{"detail":"ABSENT"}'
            with mock.patch("urllib.request.urlopen", side_effect=erreur):
                resultat = client.requete_http("http://127.0.0.1:9")
            self.assertEqual(resultat["erreur"], message)
            self.assertEqual(resultat["maintenance"], maintenance)

    def test_mise_a_jour_requise(self):
        """But : verifier les exclusions de mise a jour. Entree(s) : aucune. Sortie : aucune."""
        class App:
            donnees = {"compte": {}}
            reglages = {}
        service = client.ServiceEnLigne(App())
        service.version_serveur = {"plateformes": {}}
        with mock.patch.object(config, "EST_TEST", True):
            self.assertIsNone(service.mise_a_jour_requise())
        with mock.patch.object(config, "EST_TEST", False):
            service.version_serveur = None
            self.assertIsNone(service.mise_a_jour_requise())

    def test_titre_propose_une_mise_a_jour(self):
        """But : verifier le choix d'ecran du titre. Entree(s) : aucune. Sortie : aucune."""
        from ecrans.titre import EcranTitre
        class App:
            def __init__(self, infos):
                self.en_ligne = mock.Mock(jeton="")
                self.en_ligne.mise_a_jour_requise.return_value = infos
                self.empiler = mock.Mock()
                self.remplacer = mock.Mock()
        infos = {"version": "9.9.9"}
        with mock.patch("ecrans.mise_a_jour.EcranMiseAJour") as ecran:
            app = App(infos)
            titre = object.__new__(EcranTitre)
            titre.app = app
            titre._en_ligne()
            app.empiler.assert_called_once_with(ecran.return_value)
            app.remplacer.assert_not_called()
        app = App(None)
        titre = object.__new__(EcranTitre)
        titre.app = app
        with mock.patch("ecrans.en_ligne.connexion.EcranConnexion") as connexion:
            titre._en_ligne()
        app.remplacer.assert_called_once_with(connexion.return_value)


if __name__ == "__main__":
    unittest.main()
