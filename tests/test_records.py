# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Verifier les noms de records, leur saisie en coop et leur sauvegarde.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Realise le 23/10/2026
"""

import json
import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ecrans.saisie import ALPHABET, EcranSaisieNom, nom_par_defaut  # noqa: E402
from moteur.sauvegarde import DEFAUT, fusionner  # noqa: E402
from tests import dossier_temporaire  # noqa: E402


class AudioTest:
    """Audio minimal pour les validations d'ecran."""

    def jouer(self, *args, **kwargs):
        """But : accepter un effet sonore. Entree(s) : arguments variables. Sortie : aucune."""


class AppTest:
    """Application minimale pour tester la saisie des records."""

    def __init__(self, pseudo=""):
        self.reglages = {"nom_j1": "", "nom_j2": ""}
        self.donnees = {}
        self.en_ligne = type("EnLigne", (), {"pseudo": pseudo})()
        self.audio = AudioTest()
        self.enregistre = 0
        self.depile = 0
        self.remplace = None
        self.ajouts = []
        self.entrees = None

    def enregistrer(self):
        """But : compter les sauvegardes demandees. Entree(s) : aucune. Sortie : aucune."""
        self.enregistre += 1

    def depiler(self):
        """But : compter le retrait de l'ecran de saisie. Entree(s) : aucune. Sortie : aucune."""
        self.depile += 1

    def ajouter_au_classement(self, mode, nom, score):
        """But : memoriser le score ajoute. Entrees : mode, nom, score. Sortie : rang."""
        self.ajouts.append((mode, nom, score))
        return 0

    def remplacer(self, ecran):
        """But : memoriser l'ecran suivant. Entree(s) : ecran. Sortie : aucune."""
        self.remplace = ecran


def choisir(ecran, nom):
    """But : placer un nom dans les trois cases de saisie. Entrees : ecran, nom. Sortie : aucune."""
    ecran.lettres = [ALPHABET.index(c) for c in nom]


class TestRecords(unittest.TestCase):

    def test_noms_par_defaut(self):
        """But : verifier les priorites et transformations des noms. Entree(s) : aucune. Sortie : aucune."""
        app = AppTest("Thomas")
        self.assertEqual(nom_par_defaut(app, 1), "THO")
        app.reglages["nom_j1"] = "xyz"
        self.assertEqual(nom_par_defaut(app, 1), "XYZ")
        app.reglages["nom_j1"] = ""
        app.en_ligne.pseudo = "Élo"
        self.assertEqual(nom_par_defaut(app, 1), "ELO")
        app.en_ligne.pseudo = "x"
        self.assertEqual(nom_par_defaut(app, 1), "X  ")
        app.en_ligne.pseudo = ""
        app.donnees["dernier_nom"] = "XYZ"
        app.donnees["dernier_nom_j2"] = "DEF"
        self.assertEqual(nom_par_defaut(app, 1), "XYZ")
        self.assertEqual(nom_par_defaut(app, 2), "DEF")

    def test_saisie_coop_enregistre_deux_noms(self):
        """But : verifier le passage J1/J2 et le format du record coop. Entree(s) : aucune. Sortie : aucune."""
        app = AppTest()
        ecran = EcranSaisieNom(app, {"mode": "coop", "score": 123, "victoire": False}, None)
        choisir(ecran, "ABC")
        ecran._valider()
        self.assertEqual(ecran.joueur, 2)
        choisir(ecran, "DEF")
        ecran._valider()
        self.assertEqual(app.ajouts, [("coop", "ABC+DEF", 123)])
        self.assertEqual(app.donnees["dernier_nom"], "ABC")
        self.assertEqual(app.donnees["dernier_nom_j2"], "DEF")

    def test_mode_reglage_enregistre_et_depile(self):
        """But : verifier la sauvegarde du nom de reglage. Entree(s) : aucune. Sortie : aucune."""
        app = AppTest()
        ecran = EcranSaisieNom(app, None, None, reglage=2)
        choisir(ecran, "XYZ")
        ecran._valider()
        self.assertEqual(app.reglages["nom_j2"], "XYZ")
        self.assertEqual(app.enregistre, 1)
        self.assertEqual(app.depile, 1)
        self.assertEqual(app.ajouts, [])

    def test_ancienne_sauvegarde_recoit_les_nouveaux_reglages(self):
        """But : verifier la compatibilite du dictionnaire de sauvegarde. Entree(s) : aucune. Sortie : aucune."""
        ancienne = {"reglages": {"crt": False}}
        fusion = fusionner(DEFAUT, ancienne)
        self.assertEqual(fusion["reglages"]["nom_j1"], "")
        self.assertEqual(fusion["reglages"]["nom_j2"], "")
        chemin = os.path.join(dossier_temporaire(), "ancienne.json")
        with open(chemin, "w", encoding="utf-8") as fichier:
            json.dump(ancienne, fichier)
        self.assertTrue(os.path.exists(chemin))


if __name__ == "__main__":
    unittest.main()
