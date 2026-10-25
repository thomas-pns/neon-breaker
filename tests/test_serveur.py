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
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests import dossier_temporaire  # noqa: E402

DOSSIER = dossier_temporaire("neon_test_serveur_")
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
        self.assertEqual(len(profil["succes"]), len(SUCCES))
        secret = [s for s in profil["succes"] if s["code"] == "secret_malus"][0]
        self.assertEqual(secret["nom"], "???")
        self.assertIn("Lea", [j["pseudo"] for j in self.client.get("/api/joueurs").json()["joueurs"]])

    def test_catalogue_succes(self):
        self.assertEqual(len(SUCCES), 34)
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
            self.assertEqual(debut["skins"], ["neon", "neon"])
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

    def test_partie_classee(self):
        jeton_a, jeton_b = self.inscrire("Classe1"), self.inscrire("Classe2")
        with self.client.websocket_connect("/ws") as a, self.client.websocket_connect("/ws") as b:
            a.send_json({"t": "auth", "jeton": jeton_a, "protocole": PROTOCOLE})
            b.send_json({"t": "auth", "jeton": jeton_b, "protocole": PROTOCOLE})
            recevoir_jusqua(a, "bienvenue")
            recevoir_jusqua(b, "bienvenue")
            a.send_json({"t": "file", "v": True})
            self.assertTrue(recevoir_jusqua(a, "file")["v"])
            b.send_json({"t": "file", "v": True})
            debut = recevoir_jusqua(a, "debut", essais=2000)
            self.assertTrue(debut["classee"])
            self.assertEqual(debut["elos"], [1000, 1000])
            recevoir_jusqua(b, "debut", essais=2000)
            b.send_json({"t": "abandon"})                # abandonner = perdre
            fin = recevoir_jusqua(a, "fin", essais=2000)
            self.assertEqual(fin["gains"]["elo"], 1000 + 20)
            self.assertTrue(fin["gains"]["victoire_classee"])
        lignes = self.client.get("/api/classements/classe").json()["lignes"]
        self.assertEqual(lignes[0]["pseudo"], "Classe1")
        self.assertEqual(self.client.get("/api/joueurs/Classe2").json()["elo"], 980)

    def test_fantome(self):
        from reseau.fantome import Enregistreur
        enregistreur = Enregistreur()
        for k in range(50):
            enregistreur.avancer(0.1, 0.5, k)
        jeton = self.inscrire("Spectre")
        entete = {"Authorization": f"Bearer {jeton}"}
        rapports = [{"uid": f"f{s}", "mode": "defi", "score": s, "jour": "2026-10-22",
                     "fantome": enregistreur.exporter()} for s in (500, 900, 700)]
        self.client.post("/api/parties", json={"rapports": rapports}, headers=entete)
        reponse = self.client.get("/api/fantome/defi/2026-10-22").json()
        self.assertEqual((reponse["pseudo"], reponse["score"]), ("Spectre", 900))
        self.assertEqual(self.client.get("/api/fantome/defi/2026-10-23").status_code, 404)
        self.assertEqual(self.client.get("/api/fantome/arcade/2026-10-22").status_code, 400)

    def test_defi_du_jour(self):
        jeton = self.inscrire("Defieur")
        entete = {"Authorization": f"Bearer {jeton}"}
        rapports = [{"uid": f"d{i}", "mode": "defi", "score": s, "jour": "2026-10-21",
                     "vagues": 21, "stats": {"briques": 3}} for i, s in enumerate((900, 1500))]
        rapports.append({"uid": "d9", "mode": "defi", "score": 5000, "jour": "2026-10-20"})
        reponse = self.client.post("/api/parties", json={"rapports": rapports}, headers=entete)
        self.assertEqual(reponse.status_code, 200)
        codes = {s["code"] for r in reponse.json()["resultats"] for s in r["nouveaux_succes"]}
        self.assertIn("defi_1", codes)
        self.assertIn("defi_vague_20", codes)
        lignes = self.client.get("/api/defi/2026-10-21").json()["lignes"]
        ligne = next(l for l in lignes if l["pseudo"] == "Defieur")
        self.assertEqual(ligne["valeur"], 1500)          # meilleur score du jour seulement
        self.assertEqual(ligne["essais"], 2)
        self.assertEqual(self.client.get("/api/defi/n-importe").status_code, 400)

    def test_series_et_semaine(self):
        jeton = self.inscrire("Regulier")
        entete = {"Authorization": f"Bearer {jeton}"}
        aujourd_hui = api.aujourd_hui()
        import datetime
        from reseau.series import id_semaine
        jours = [(aujourd_hui - datetime.timedelta(days=k)).isoformat() for k in range(3)]
        rapports = [{"uid": f"s{k}", "mode": "defi", "score": 10, "jour": j}
                    for k, j in enumerate(jours)]
        rapports.append({"uid": "w1", "mode": "semaine", "score": 77, "jour": id_semaine(aujourd_hui)})
        reponse = self.client.post("/api/parties", json={"rapports": rapports}, headers=entete)
        codes = {s["code"] for r in reponse.json()["resultats"] for s in r["nouveaux_succes"]}
        self.assertIn("serie_3", codes)
        self.assertIn("semaine_1", codes)
        profil = self.client.get("/api/joueurs/Regulier").json()
        self.assertEqual(profil["series"]["jour"], {"en_cours": 3, "record": 3})
        self.assertEqual(profil["series"]["semaine"]["en_cours"], 1)
        lignes = self.client.get("/api/series").json()["lignes"]
        self.assertEqual(next(l for l in lignes if l["pseudo"] == "Regulier")["valeur"], 3)
        semaine = self.client.get(f"/api/semaine/{id_semaine(aujourd_hui)}").json()
        self.assertEqual(next(l for l in semaine["lignes"] if l["pseudo"] == "Regulier")["valeur"], 77)
        self.assertEqual(self.client.get("/api/semaine/2026-43").status_code, 400)

    def test_skins(self):
        jeton = self.inscrire("Habille")
        entete = {"Authorization": f"Bearer {jeton}"}
        moi = self.client.get("/api/moi", headers=entete).json()
        self.assertEqual(moi["skin"], "neon")
        self.assertEqual(moi["skins"], ["neon"])
        refus = self.client.put("/api/moi/skin", json={"skin": "cryo"}, headers=entete)
        self.assertEqual(refus.status_code, 400)
        # Un gros score fait monter de niveau : de nouveaux skins se débloquent.
        self.client.post("/api/parties", headers=entete, json={"rapports": [
            {"uid": f"h{i}", "mode": "arcade", "score": 10 ** 6} for i in range(10)]})
        moi = self.client.get("/api/moi", headers=entete).json()
        self.assertIn("cryo", moi["skins"])
        ok = self.client.put("/api/moi/skin", json={"skin": "cryo"}, headers=entete)
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(self.client.get("/api/joueurs/Habille").json()["skin"], "cryo")

    def test_boutique(self):
        jeton = self.inscrire("Acheteur")
        entete = {"Authorization": f"Bearer {jeton}"}
        moi = self.client.get("/api/moi", headers=entete).json()
        self.assertEqual(moi["neons"], 100)                       # cadeau de bienvenue
        # Gagner des NEONS : deux niveaux de campagne et un boss, payés une fois.
        rapport = {"mode": "campagne", "indice_depart": 0, "victoire": False, "score": 0,
                   "stats": {"niveaux_finis": 2, "boss_vaincus": ["sunset"]}}
        reponse = self.client.post("/api/parties", headers=entete, json={"rapports": [
            dict(rapport, uid="b1"), dict(rapport, uid="b2")]}).json()
        gains = [r["neons_gagnes"] for r in reponse["resultats"]]
        self.assertGreaterEqual(gains[0], 70)
        self.assertEqual(gains[1], 0)
        self.assertEqual(reponse["neons"], 100 + gains[0])
        # Boutique du jour, achat, refus si déjà possédé ou trop cher.
        vitrine = self.client.get("/api/boutique", headers=entete).json()
        self.assertEqual(len(vitrine["selection"]), 6)
        api.base.crediter(api.base.joueur_par_pseudo("Acheteur")["id"], 5000)
        banniere = next(o for o in vitrine["selection"] if o["type"] == "banniere")
        achat = self.client.post("/api/boutique/acheter", headers=entete,
                                 json={"code": banniere["code"]})
        self.assertEqual(achat.status_code, 200, achat.text)
        self.assertIn(banniere["code"], achat.json()["bannieres"])
        self.assertEqual(self.client.post("/api/boutique/acheter", headers=entete,
                                          json={"code": banniere["code"]}).status_code, 400)
        self.assertEqual(self.client.post("/api/boutique/acheter", headers=entete,
                                          json={"code": "glitch"}).status_code, 400)
        ok = self.client.put("/api/moi/banniere", headers=entete, json={"banniere": banniere["code"]})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(self.client.get("/api/joueurs/Acheteur").json()["banniere"], banniere["code"])
        self.assertEqual(self.client.put("/api/moi/banniere", headers=entete,
                                         json={"banniere": "couronne"}).status_code, 400)
        # Boîte mystère : un objet nouveau, débité.
        avant = self.client.get("/api/moi", headers=entete).json()["neons"]
        boite = self.client.post("/api/boutique/boite", headers=entete).json()
        self.assertNotEqual(boite["objet"]["code"], banniere["code"])
        self.assertEqual(boite["neons"], avant - 220)
        # Un skin premium possédé devient utilisable.
        skin = next(o for o in vitrine["selection"] if o["type"] == "skin")
        self.client.post("/api/boutique/acheter", headers=entete, json={"code": skin["code"]})
        self.assertEqual(self.client.put("/api/moi/skin", headers=entete,
                                         json={"skin": skin["code"]}).status_code, 200)
        # Pauvre : refus.
        pauvre = {"Authorization": f"Bearer {self.inscrire('Fauche')}"}
        self.assertEqual(self.client.post("/api/boutique/acheter", headers=pauvre,
                                          json={"code": skin["code"]}).status_code, 400)

    def test_migration_base_1_0(self):
        """Une base créée par la version 1.0 (sans skin ni jour) est mise à niveau."""
        import sqlite3
        from serveur.base import Base
        chemin = os.path.join(DOSSIER, "ancienne.sqlite3")
        ancienne = sqlite3.connect(chemin)
        ancienne.executescript("""
            CREATE TABLE joueurs (id INTEGER PRIMARY KEY, pseudo TEXT NOT NULL UNIQUE COLLATE NOCASE,
                mdp TEXT NOT NULL, couleur TEXT NOT NULL DEFAULT 'cyan', xp INTEGER NOT NULL DEFAULT 0,
                cree_le REAL NOT NULL, vu_le REAL NOT NULL, banni INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE parties (id INTEGER PRIMARY KEY, uid TEXT UNIQUE, joueur_id INTEGER NOT NULL,
                mode TEXT NOT NULL, score INTEGER NOT NULL, victoire INTEGER NOT NULL DEFAULT 0,
                en_ligne INTEGER NOT NULL DEFAULT 0, duree REAL NOT NULL DEFAULT 0,
                details TEXT NOT NULL DEFAULT '{}', joue_le REAL NOT NULL);
            INSERT INTO joueurs (pseudo, mdp, cree_le, vu_le) VALUES ('Ancien', 'x', 0, 0);
        """)
        ancienne.commit()
        ancienne.close()
        base = Base(chemin)
        self.assertEqual(base.joueur_par_pseudo("Ancien")["skin"], "neon")
        self.assertEqual(base.joueur_par_pseudo("Ancien")["neons"], 100)    # cadeau 2.0
        base.enregistrer_partie(1, {"uid": "m1", "mode": "defi", "score": 10, "jour": "2026-10-21"})
        self.assertEqual(base.classement_defi("2026-10-21")[0]["pseudo"], "Ancien")

    def test_protocole_trop_ancien(self):
        with self.client.websocket_connect("/ws") as socket:
            socket.send_json({"t": "auth", "jeton": "x", "protocole": -1})
            self.assertIn("MISE A JOUR", recevoir_jusqua(socket, "erreur")["msg"])


if __name__ == "__main__":
    unittest.main()
