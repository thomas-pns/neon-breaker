# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Tests du serveur en ligne : comptes, sécurité, scores et succès,
    classements et profils, envoi des exécutables, et parties en ligne par
    WebSocket (création, salon, lancement, déconnexion, retour, abandon).
    Nécessite fastapi et httpx (pip install -r serveur/requirements.txt httpx).

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import os
import sys
import tempfile
import time
import unittest

DOSSIER = tempfile.mkdtemp(prefix="neon_test_serveur_")
os.environ["NEON_DONNEES_SERVEUR"] = DOSSIER
os.environ["NEON_JETON_DEPLOIEMENT"] = "jeton-de-test"
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from fastapi.testclient import TestClient
    from serveur import api, config, securite
    from serveur.succes import evaluer, mettre_a_jour_cumul, SUCCES
    from moteur.version import PROTOCOLE
    DISPONIBLE = True
except ImportError:                       # dépendances du serveur absentes
    DISPONIBLE = False


def recevoir_jusqua(socket, nature, essais=400):
    """Lit les messages jusqu'à en trouver un du type voulu."""
    for _ in range(essais):
        message = socket.receive_json()
        if message.get("t") == nature:
            return message
    raise AssertionError(f"message {nature} jamais reçu")


@unittest.skipUnless(DISPONIBLE, "fastapi / httpx non installés")
class TestServeur(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(api.app)
        api.limiteur.maximum = 1000

    def inscrire(self, pseudo, mdp="motdepasse"):
        reponse = self.client.post("/api/inscription", json={"pseudo": pseudo, "mdp": mdp})
        self.assertEqual(reponse.status_code, 200, reponse.text)
        return reponse.json()["jeton"]

    def test_comptes(self):
        jeton = self.inscrire("Zoe")
        self.assertEqual(self.client.post("/api/inscription",
                                          json={"pseudo": "ZOE", "mdp": "abcdefg"}).status_code, 409)
        self.assertEqual(self.client.post("/api/inscription",
                                          json={"pseudo": "a b", "mdp": "abcdefg"}).status_code, 400)
        self.assertEqual(self.client.post("/api/connexion",
                                          json={"pseudo": "zoe", "mdp": "faux!!"}).status_code, 401)
        ok = self.client.post("/api/connexion", json={"pseudo": "zoe", "mdp": "motdepasse"})
        self.assertEqual(ok.json()["pseudo"], "Zoe")
        moi = self.client.get("/api/moi", headers={"Authorization": f"Bearer {jeton}"})
        self.assertEqual(moi.json()["niveau"], 1)
        self.client.post("/api/deconnexion", headers={"Authorization": f"Bearer {jeton}"})
        self.assertEqual(self.client.get("/api/moi", headers={"Authorization": f"Bearer {jeton}"})
                         .status_code, 401)

    def test_mots_de_passe(self):
        empreinte = securite.hacher_mdp("secret42")
        self.assertTrue(securite.verifier_mdp("secret42", empreinte))
        self.assertFalse(securite.verifier_mdp("secret43", empreinte))
        self.assertNotIn("secret42", empreinte)
        limiteur = securite.Limiteur(2)
        self.assertTrue(limiteur.autoriser("ip") and limiteur.autoriser("ip"))
        self.assertFalse(limiteur.autoriser("ip"))

    def test_scores_succes_profil(self):
        jeton = self.inscrire("Lea")
        entetes = {"Authorization": f"Bearer {jeton}"}
        rapport = {"uid": "x1", "mode": "arcade", "score": 5000, "duree": 120, "vagues": 31,
                   "stats": {"briques": 80, "meilleur_combo": 12, "supernovas": 0}}
        reponse = self.client.post("/api/parties", json={"rapports": [rapport, rapport,
                                                                       {"mode": "duel", "score": 9}]})
        self.assertEqual(reponse.status_code, 401)
        reponse = self.client.post("/api/parties", headers=entetes,
                                   json={"rapports": [rapport, rapport, {"mode": "duel", "score": 9}]})
        resultats = reponse.json()["resultats"]
        codes = [s["code"] for s in resultats[0]["nouveaux_succes"]]
        self.assertIn("arcade_30", codes)
        self.assertTrue(resultats[1]["doublon"])
        self.assertTrue(resultats[2]["refuse"])           # le Duel est compté par le serveur
        classement = self.client.get("/api/classements/arcade").json()["lignes"]
        self.assertEqual(classement[0]["pseudo"], "Lea")
        profil = self.client.get("/api/joueurs/lea").json()
        self.assertEqual(profil["records"]["arcade"], 5000)
        self.assertEqual(len(profil["succes"]), 24)
        secret = [s for s in profil["succes"] if s["code"] == "secret_malus"][0]
        self.assertEqual(secret["nom"], "???")
        self.assertIn("Lea", [j["pseudo"] for j in self.client.get("/api/joueurs").json()["joueurs"]])

    def test_catalogue_succes(self):
        self.assertEqual(len(SUCCES), 24)
        cumul = mettre_a_jour_cumul({}, {"mode": "duel", "numero": 1, "gagnant": 1,
                                         "points": [7, 0], "stats": {"briques": 3}})
        codes = evaluer({"mode": "duel", "numero": 1, "gagnant": 1, "points": [7, 0],
                         "stats": {"briques": 3}, "en_ligne": True}, cumul, set())
        self.assertIn("duel_7_0", codes)
        self.assertIn("premiere_en_ligne", codes)
        self.assertEqual(cumul["victoires"]["duel"], 1)

    def test_builds(self):
        import hashlib
        contenu = b"MZ" + os.urandom(250000)
        empreinte = hashlib.sha256(contenu).hexdigest()
        morceaux = [contenu[i:i + 100000] for i in range(0, len(contenu), 100000)]
        url = f"/api/builds/windows/1.2.3/{{}}?total={len(morceaux)}&sha256={empreinte}"
        refuse = self.client.post(url.format(0), content=morceaux[0],
                                  headers={"X-Jeton-Deploiement": "mauvais"})
        self.assertEqual(refuse.status_code, 403)
        entetes = {"X-Jeton-Deploiement": "jeton-de-test"}
        self.assertEqual(self.client.post(url.format(1), content=morceaux[1],
                                          headers=entetes).status_code, 409)   # ordre exigé
        for i, morceau in enumerate(morceaux):
            ok = self.client.post(url.format(i), content=morceau, headers=entetes)
            self.assertEqual(ok.status_code, 200, ok.text)
        self.assertIn("publie", ok.json())
        version = self.client.get("/api/version").json()
        self.assertEqual(version["protocole"], PROTOCOLE)
        self.assertEqual(version["plateformes"]["windows"]["version"], "1.2.3")
        self.assertEqual(self.client.get("/telechargements/windows").content, contenu)
        self.assertIn("WINDOWS", self.client.get("/").text)

    def test_partie_en_ligne(self):
        config.ATTENTE_RECONNEXION = 2.0
        jeton_a, jeton_b = self.inscrire("Hote1"), self.inscrire("Invite1")
        with self.client.websocket_connect("/ws") as a, self.client.websocket_connect("/ws") as b:
            a.send_json({"t": "auth", "jeton": jeton_a, "protocole": PROTOCOLE})
            b.send_json({"t": "auth", "jeton": jeton_b, "protocole": PROTOCOLE})
            recevoir_jusqua(a, "bienvenue")
            recevoir_jusqua(b, "bienvenue")
            a.send_json({"t": "creer", "mode": "duel"})
            salon = recevoir_jusqua(a, "salon")
            b.send_json({"t": "rejoindre", "id": salon["id"]})
            self.assertEqual(len(recevoir_jusqua(b, "salon")["joueurs"]), 2)
            a.send_json({"t": "lancer"})
            self.assertIn("PRET", recevoir_jusqua(a, "erreur")["msg"])
            a.send_json({"t": "pret", "v": True})
            b.send_json({"t": "pret", "v": True})
            time.sleep(0.2)
            a.send_json({"t": "lancer"})
            debut = recevoir_jusqua(a, "debut")
            self.assertEqual(debut["numero"], 1)
            self.assertEqual(recevoir_jusqua(b, "debut")["numero"], 2)
            etat = recevoir_jusqua(a, "etat")
            self.assertEqual(len(etat["terrains"][0]["raquettes"]), 2)
            self.assertIn("briques", etat["terrains"][0])
            a.send_json({"t": "cmd", "x": 400, "vx": 0, "a": ["action"]})
            # Le joueur 2 se déconnecte : la partie se met en pause.
            b.close()
            for _ in range(200):
                etat = recevoir_jusqua(a, "etat")
                if etat.get("pause"):
                    break
            self.assertIn("Invite1", etat["pause"])
            # Il revient : la partie reprend.
            with self.client.websocket_connect("/ws") as b2:
                b2.send_json({"t": "auth", "jeton": jeton_b, "protocole": PROTOCOLE})
                self.assertEqual(recevoir_jusqua(b2, "debut")["numero"], 2)
                self.assertIn("briques", recevoir_jusqua(b2, "etat")["terrains"][0])
                b2.send_json({"t": "abandon"})
                fin = recevoir_jusqua(a, "fin")
                self.assertEqual(fin["resultat"]["titre"], "PARTIE INTERROMPUE")

    def test_protocole_trop_ancien(self):
        with self.client.websocket_connect("/ws") as socket:
            socket.send_json({"t": "auth", "jeton": "x", "protocole": -1})
            self.assertIn("MISE A JOUR", recevoir_jusqua(socket, "erreur")["msg"])


if __name__ == "__main__":
    unittest.main()
