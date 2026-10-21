# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Base de données SQLite du serveur : joueurs, sessions, parties jouées,
    succès débloqués et statistiques cumulées. Une seule connexion protégée
    par un verrou (le trafic d'un groupe d'amis est faible), mode WAL pour
    que les lectures ne bloquent pas les écritures.

    Tables :
      joueurs(id, pseudo, mdp, couleur, xp, cree_le, vu_le, banni, skin)
      sessions(empreinte, joueur_id, expire_le)
      parties(id, uid, joueur_id, mode, score, victoire, en_ligne, duree, details, joue_le,
              jour)                     -- jour : date du défi du jour (mode "defi")
      succes(joueur_id, code, obtenu_le)
      cumuls(joueur_id, donnees)          -- JSON des statistiques cumulées

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import json
import os
import sqlite3
import threading
import time

from serveur import config, succes as catalogue

SCHEMA = """
CREATE TABLE IF NOT EXISTS joueurs (
    id INTEGER PRIMARY KEY,
    pseudo TEXT NOT NULL UNIQUE COLLATE NOCASE,
    mdp TEXT NOT NULL,
    couleur TEXT NOT NULL DEFAULT 'cyan',
    xp INTEGER NOT NULL DEFAULT 0,
    cree_le REAL NOT NULL,
    vu_le REAL NOT NULL,
    banni INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS sessions (
    empreinte TEXT PRIMARY KEY,
    joueur_id INTEGER NOT NULL REFERENCES joueurs(id) ON DELETE CASCADE,
    expire_le REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS parties (
    id INTEGER PRIMARY KEY,
    uid TEXT UNIQUE,
    joueur_id INTEGER NOT NULL REFERENCES joueurs(id) ON DELETE CASCADE,
    mode TEXT NOT NULL,
    score INTEGER NOT NULL,
    victoire INTEGER NOT NULL DEFAULT 0,
    en_ligne INTEGER NOT NULL DEFAULT 0,
    duree REAL NOT NULL DEFAULT 0,
    details TEXT NOT NULL DEFAULT '{}',
    joue_le REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS parties_mode_score ON parties(mode, score DESC);
CREATE INDEX IF NOT EXISTS parties_joueur ON parties(joueur_id, joue_le DESC);
CREATE TABLE IF NOT EXISTS succes (
    joueur_id INTEGER NOT NULL REFERENCES joueurs(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    obtenu_le REAL NOT NULL,
    PRIMARY KEY (joueur_id, code)
);
CREATE TABLE IF NOT EXISTS cumuls (
    joueur_id INTEGER PRIMARY KEY REFERENCES joueurs(id) ON DELETE CASCADE,
    donnees TEXT NOT NULL DEFAULT '{}'
);
"""

MODES_SCORE = ("campagne", "arcade", "hardcore", "coop", "defi")
MODES_VICTOIRES = ("duel", "course")


class Base:
    """Accès à la base. Attributs : chemin (str), connexion, verrou."""

    def __init__(self, chemin=config.CHEMIN_BASE):
        dossier = os.path.dirname(chemin)
        if dossier:
            os.makedirs(dossier, exist_ok=True)
        self.chemin = chemin
        self.connexion = sqlite3.connect(chemin, check_same_thread=False)
        self.connexion.row_factory = sqlite3.Row
        self.verrou = threading.Lock()
        with self.verrou:
            self.connexion.execute("PRAGMA journal_mode=WAL")
            self.connexion.execute("PRAGMA foreign_keys=ON")
            self.connexion.executescript(SCHEMA)
            # Migration 1.1 : colonne « jour » pour le défi du jour.
            colonnes = {l[1] for l in self.connexion.execute("PRAGMA table_info(parties)")}
            if "jour" not in colonnes:
                self.connexion.execute("ALTER TABLE parties ADD COLUMN jour TEXT")
            # Migration 1.1 : skin de raquette choisi par le joueur.
            colonnes = {l[1] for l in self.connexion.execute("PRAGMA table_info(joueurs)")}
            if "skin" not in colonnes:
                self.connexion.execute("ALTER TABLE joueurs ADD COLUMN skin TEXT NOT NULL DEFAULT 'neon'")
            self.connexion.execute("CREATE INDEX IF NOT EXISTS parties_jour ON parties(jour, score DESC)")
            self.connexion.commit()

    def _executer(self, requete, parametres=(), commit=False):
        with self.verrou:
            curseur = self.connexion.execute(requete, parametres)
            lignes = curseur.fetchall()
            if commit:
                self.connexion.commit()
            return lignes, curseur.lastrowid

    def lire(self, requete, parametres=()):
        """But : lignes d'une requête SELECT. Sortie : (list de sqlite3.Row)."""
        return self._executer(requete, parametres)[0]

    def ecrire(self, requete, parametres=()):
        """But : requête qui modifie la base. Sortie : (int) dernier id inséré."""
        return self._executer(requete, parametres, commit=True)[1]

    # --- Joueurs et sessions -------------------------------------------------------

    def creer_joueur(self, pseudo, mdp_hache, couleur="cyan"):
        """But : créer un compte. Sortie : (int ou None) id, None si pseudo pris."""
        maintenant = time.time()
        try:
            return self.ecrire("INSERT INTO joueurs (pseudo, mdp, couleur, cree_le, vu_le) "
                               "VALUES (?, ?, ?, ?, ?)",
                               (pseudo, mdp_hache, couleur, maintenant, maintenant))
        except sqlite3.IntegrityError:
            return None

    def joueur_par_pseudo(self, pseudo):
        lignes = self.lire("SELECT * FROM joueurs WHERE pseudo = ?", (pseudo,))
        return lignes[0] if lignes else None

    def joueur_par_id(self, joueur_id):
        lignes = self.lire("SELECT * FROM joueurs WHERE id = ?", (joueur_id,))
        return lignes[0] if lignes else None

    def creer_session(self, joueur_id, empreinte):
        expire = time.time() + config.DUREE_SESSION_JOURS * 86400
        self.ecrire("INSERT INTO sessions (empreinte, joueur_id, expire_le) VALUES (?, ?, ?)",
                    (empreinte, joueur_id, expire))

    def joueur_par_session(self, empreinte):
        """But : joueur d'une session valide (non expirée, non banni), ou None."""
        lignes = self.lire("SELECT j.* FROM sessions s JOIN joueurs j ON j.id = s.joueur_id "
                           "WHERE s.empreinte = ? AND s.expire_le > ? AND j.banni = 0",
                           (empreinte, time.time()))
        return lignes[0] if lignes else None

    def supprimer_session(self, empreinte):
        self.ecrire("DELETE FROM sessions WHERE empreinte = ?", (empreinte,))

    def supprimer_sessions_joueur(self, joueur_id):
        self.ecrire("DELETE FROM sessions WHERE joueur_id = ?", (joueur_id,))

    def toucher(self, joueur_id):
        """But : noter la dernière visite d'un joueur."""
        self.ecrire("UPDATE joueurs SET vu_le = ? WHERE id = ?", (time.time(), joueur_id))

    def changer_couleur(self, joueur_id, couleur):
        self.ecrire("UPDATE joueurs SET couleur = ? WHERE id = ?", (couleur, joueur_id))

    def changer_skin(self, joueur_id, skin):
        self.ecrire("UPDATE joueurs SET skin = ? WHERE id = ?", (skin, joueur_id))

    def skins_de(self, joueur):
        """But : skins débloqués par un joueur (niveau et succès)."""
        from reseau.profil import skins_debloques
        return skins_debloques(catalogue.niveau_pour(joueur["xp"]), set(self.succes_de(joueur["id"])))

    def changer_mdp(self, joueur_id, mdp_hache):
        self.ecrire("UPDATE joueurs SET mdp = ? WHERE id = ?", (mdp_hache, joueur_id))

    def bannir(self, joueur_id, banni=True):
        self.ecrire("UPDATE joueurs SET banni = ? WHERE id = ?", (int(banni), joueur_id))

    # --- Parties, XP, succès --------------------------------------------------------

    def cumul(self, joueur_id):
        lignes = self.lire("SELECT donnees FROM cumuls WHERE joueur_id = ?", (joueur_id,))
        return json.loads(lignes[0]["donnees"]) if lignes else {}

    def succes_de(self, joueur_id):
        """But : {code: date d'obtention} des succès d'un joueur."""
        return {l["code"]: l["obtenu_le"] for l in
                self.lire("SELECT code, obtenu_le FROM succes WHERE joueur_id = ?", (joueur_id,))}

    def enregistrer_partie(self, joueur_id, rapport, en_ligne=False):
        """
        But : enregistrer une partie, mettre à jour XP et statistiques,
        débloquer les succès.
        Entrées : joueur_id (int) ; rapport (dict) ; en_ligne (bool) : partie
                  jouée sur le serveur (score fiable).
        Sortie : (dict) {"doublon", "xp", "niveau", "nouveaux_succes"}.
        """
        rapport = dict(rapport)
        rapport["en_ligne"] = en_ligne
        mode = str(rapport.get("mode", "?"))[:20]
        score = max(0, min(int(rapport.get("score_equipe", rapport.get("score", 0))), 10 ** 9))
        victoire = bool(rapport.get("victoire")) or rapport.get("gagnant") == rapport.get("numero")
        uid = rapport.get("uid")
        jour = str(rapport.get("jour"))[:10] if mode == "defi" and rapport.get("jour") else None
        try:
            self.ecrire("INSERT INTO parties (uid, joueur_id, mode, score, victoire, en_ligne, "
                        "duree, details, joue_le, jour) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (uid, joueur_id, mode, score, int(victoire), int(en_ligne),
                         float(rapport.get("duree", 0)), json.dumps(rapport)[:20000],
                         float(rapport.get("joue_le", time.time())), jour))
        except sqlite3.IntegrityError:
            return {"doublon": True, "nouveaux_succes": []}
        cumul = catalogue.mettre_a_jour_cumul(self.cumul(joueur_id), rapport)
        self.ecrire("INSERT INTO cumuls (joueur_id, donnees) VALUES (?, ?) "
                    "ON CONFLICT(joueur_id) DO UPDATE SET donnees = excluded.donnees",
                    (joueur_id, json.dumps(cumul)))
        gain = catalogue.xp_partie(rapport)
        self.ecrire("UPDATE joueurs SET xp = xp + ?, vu_le = ? WHERE id = ?",
                    (gain, time.time(), joueur_id))
        nouveaux = catalogue.evaluer(rapport, cumul, set(self.succes_de(joueur_id)))
        for code in nouveaux:
            self.ecrire("INSERT OR IGNORE INTO succes (joueur_id, code, obtenu_le) VALUES (?, ?, ?)",
                        (joueur_id, code, time.time()))
        xp = self.joueur_par_id(joueur_id)["xp"]
        return {"doublon": False, "xp_gagnee": gain, "xp": xp,
                "niveau": catalogue.niveau_pour(xp),
                "nouveaux_succes": [catalogue.PAR_CODE[c].en_dict() for c in nouveaux]}

    # --- Lectures publiques ----------------------------------------------------------

    def classement(self, mode, limite=20):
        """
        But : meilleur score de chaque joueur dans un mode (ou nombre de
        victoires en Duel / Course).
        Sortie : (list de dict) {"pseudo", "couleur", "valeur", "niveau"}.
        """
        if mode in MODES_VICTOIRES:
            lignes = self.lire(
                "SELECT j.pseudo, j.couleur, j.xp, SUM(p.victoire) AS valeur, COUNT(*) AS parties "
                "FROM parties p JOIN joueurs j ON j.id = p.joueur_id "
                "WHERE p.mode = ? AND j.banni = 0 GROUP BY p.joueur_id "
                "ORDER BY valeur DESC, parties ASC LIMIT ?", (mode, limite))
        else:
            lignes = self.lire(
                "SELECT j.pseudo, j.couleur, j.xp, MAX(p.score) AS valeur "
                "FROM parties p JOIN joueurs j ON j.id = p.joueur_id "
                "WHERE p.mode = ? AND j.banni = 0 GROUP BY p.joueur_id "
                "ORDER BY valeur DESC LIMIT ?", (mode, limite))
        return [{"pseudo": l["pseudo"], "couleur": l["couleur"], "valeur": int(l["valeur"] or 0),
                 "niveau": catalogue.niveau_pour(l["xp"])} for l in lignes]

    def classement_defi(self, jour, limite=20):
        """But : meilleur score de chaque joueur au défi d'un jour donné."""
        lignes = self.lire(
            "SELECT j.pseudo, j.couleur, j.xp, MAX(p.score) AS valeur, COUNT(*) AS essais "
            "FROM parties p JOIN joueurs j ON j.id = p.joueur_id "
            "WHERE p.mode = 'defi' AND p.jour = ? AND j.banni = 0 GROUP BY p.joueur_id "
            "ORDER BY valeur DESC LIMIT ?", (jour, limite))
        return [{"pseudo": l["pseudo"], "couleur": l["couleur"], "valeur": int(l["valeur"] or 0),
                 "niveau": catalogue.niveau_pour(l["xp"]), "essais": l["essais"]} for l in lignes]

    def liste_joueurs(self):
        """But : tous les joueurs (non bannis), du plus haut niveau au plus bas."""
        lignes = self.lire("SELECT id, pseudo, couleur, xp, vu_le FROM joueurs "
                           "WHERE banni = 0 ORDER BY xp DESC, pseudo")
        nb_succes = {l["joueur_id"]: l["n"] for l in
                     self.lire("SELECT joueur_id, COUNT(*) AS n FROM succes GROUP BY joueur_id")}
        return [{"pseudo": l["pseudo"], "couleur": l["couleur"], "xp": l["xp"],
                 "niveau": catalogue.niveau_pour(l["xp"]), "vu_le": l["vu_le"],
                 "succes": nb_succes.get(l["id"], 0)} for l in lignes]

    def profil(self, pseudo):
        """But : page de profil d'un joueur, ou None s'il n'existe pas."""
        joueur = self.joueur_par_pseudo(pseudo)
        if joueur is None or joueur["banni"]:
            return None
        jid = joueur["id"]
        records = {}
        for mode in MODES_SCORE:
            ligne = self.lire("SELECT MAX(score) AS s FROM parties WHERE joueur_id = ? AND mode = ?",
                              (jid, mode))
            records[mode] = int(ligne[0]["s"] or 0)
        cumul = self.cumul(jid)
        obtenus = self.succes_de(jid)
        liste_succes = []
        for definition in catalogue.SUCCES:
            obtenu = definition.code in obtenus
            entree = definition.en_dict()
            if definition.secret and not obtenu:
                entree.update(nom="???", description="Succes secret")
            entree["obtenu_le"] = obtenus.get(definition.code)
            liste_succes.append(entree)
        dernieres = [{"mode": l["mode"], "score": l["score"], "victoire": bool(l["victoire"]),
                      "en_ligne": bool(l["en_ligne"]), "joue_le": l["joue_le"]}
                     for l in self.lire("SELECT mode, score, victoire, en_ligne, joue_le FROM parties "
                                        "WHERE joueur_id = ? ORDER BY joue_le DESC LIMIT 8", (jid,))]
        niveau = catalogue.niveau_pour(joueur["xp"])
        return {"pseudo": joueur["pseudo"], "couleur": joueur["couleur"], "xp": joueur["xp"],
                "skin": joueur["skin"], "niveau": niveau, "xp_niveau": catalogue.xp_pour_niveau(niveau),
                "xp_suivant": catalogue.xp_pour_niveau(niveau + 1),
                "cree_le": joueur["cree_le"], "vu_le": joueur["vu_le"],
                "stats": {"parties": cumul.get("parties", 0), "briques": cumul.get("briques", 0),
                          "temps": cumul.get("temps", 0),
                          "meilleur_combo": cumul.get("meilleur_combo", 0),
                          "supernovas": cumul.get("supernovas", 0),
                          "victoires": cumul.get("victoires", {}),
                          "boss_vaincus": cumul.get("boss_vaincus", {})},
                "records": records, "succes": liste_succes, "dernieres_parties": dernieres}
