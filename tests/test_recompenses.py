# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Tests des récompenses du serveur (2.1) : top 3 des défis payé une seule
    fois, fin de saison classée (NEONS, bannières, cote rapprochée de 1000),
    historique des NEONS et messages.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 25/10/2026
"""

import datetime
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

try:
    import fastapi  # noqa: F401  (dépendances du serveur présentes ?)
    DISPONIBLE = True
except ImportError:
    DISPONIBLE = False


recompenses = None


@unittest.skipUnless(DISPONIBLE, "serveur non installé")
class TestRecompenses(unittest.TestCase):

    def setUp(self):
        # Import tardif : le module serveur.config lit NEON_DONNEES_SERVEUR, réglé par test_serveur.
        global recompenses
        from serveur.base import Base
        from serveur import recompenses
        from tests import dossier_temporaire
        self.base = Base(os.path.join(dossier_temporaire("neon_recompenses_"), "base.sqlite3"))
        self.ids = [self.base.creer_joueur(p, "x") for p in ("Ana", "Bob", "Cid", "Dan")]

    def test_top3_du_jour(self):
        for k, (jid, score) in enumerate(zip(self.ids, (500, 900, 700, 100))):
            self.base.enregistrer_partie(jid, {"uid": f"d{k}", "mode": "defi", "score": score,
                                               "jour": "2026-10-24"})
        avant = {jid: self.base.joueur_par_id(jid)["neons"] for jid in self.ids}
        recompenses.verser_defis(self.base, datetime.date(2026, 10, 25))
        gains = {jid: self.base.joueur_par_id(jid)["neons"] - avant[jid] for jid in self.ids}
        self.assertEqual(gains, {self.ids[1]: 50, self.ids[2]: 30, self.ids[0]: 20, self.ids[3]: 0})
        recompenses.verser_defis(self.base, datetime.date(2026, 10, 25))      # pas deux fois
        self.assertEqual(self.base.joueur_par_id(self.ids[1])["neons"] - avant[self.ids[1]], 50)
        messages = self.base.messages_non_lus(self.ids[1])
        self.assertTrue(messages[0]["titre"].startswith("1ER DEFI"))
        self.base.marquer_lus(self.ids[1], [m["id"] for m in messages])
        self.assertEqual(self.base.messages_non_lus(self.ids[1]), [])
        self.assertEqual(self.base.historique(self.ids[1])[0]["montant"], 50)

    def test_fin_de_saison(self):
        recompenses.verser_saison(self.base, datetime.date(2026, 11, 3))      # début : rien
        self.base.ecrire("UPDATE joueurs SET elo = 1300, saison_max = 1420, classees = 12 WHERE id = ?",
                         (self.ids[0],))
        avant = self.base.joueur_par_id(self.ids[0])["neons"]
        recompenses.verser_saison(self.base, datetime.date(2026, 11, 30))     # même saison : rien
        self.assertEqual(self.base.joueur_par_id(self.ids[0])["neons"], avant)
        recompenses.verser_saison(self.base, datetime.date(2026, 12, 1))      # nouvelle saison
        joueur = self.base.joueur_par_id(self.ids[0])
        self.assertEqual(joueur["neons"] - avant, 350)                        # PLATINE
        self.assertEqual(joueur["elo"], 1150)
        self.assertEqual(joueur["saison_max"], 0)
        self.assertIn("saison_platine", self.base.bannieres_de(self.ids[0]))
        self.assertIn("saison_or", self.base.bannieres_de(self.ids[0]))

    def test_historique_des_achats(self):
        self.base.crediter(self.ids[0], 500, "TEST")
        self.base.acheter(self.ids[0], "aube", 120)
        self.assertEqual(self.base.historique(self.ids[0])[0]["montant"], -120)


if __name__ == "__main__":
    unittest.main()
