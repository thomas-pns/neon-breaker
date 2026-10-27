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
CREATE TABLE IF NOT EXISTS fantomes (
    mode TEXT NOT NULL,
    jour TEXT NOT NULL,
    joueur_id INTEGER NOT NULL REFERENCES joueurs(id) ON DELETE CASCADE,
    score INTEGER NOT NULL,
    donnees TEXT NOT NULL,
    PRIMARY KEY (mode, jour, joueur_id)
);
CREATE TABLE IF NOT EXISTS recompenses (
    periode TEXT PRIMARY KEY,
    valeur TEXT NOT NULL DEFAULT '',
    verse_le REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    joueur_id INTEGER NOT NULL REFERENCES joueurs(id) ON DELETE CASCADE,
    titre TEXT NOT NULL,
    texte TEXT NOT NULL DEFAULT '',
    cree_le REAL NOT NULL,
    lu INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS mouvements (
    id INTEGER PRIMARY KEY,
    joueur_id INTEGER NOT NULL REFERENCES joueurs(id) ON DELETE CASCADE,
    montant INTEGER NOT NULL,
    raison TEXT NOT NULL,
    le REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS mouvements_joueur ON mouvements(joueur_id, le DESC);
CREATE TABLE IF NOT EXISTS possessions (
    joueur_id INTEGER NOT NULL REFERENCES joueurs(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    origine TEXT NOT NULL DEFAULT 'achat',
    obtenu_le REAL NOT NULL,
    PRIMARY KEY (joueur_id, code)
);
CREATE TABLE IF NOT EXISTS progressions (
    joueur_id INTEGER PRIMARY KEY REFERENCES joueurs(id) ON DELETE CASCADE,
    donnees TEXT NOT NULL,
    maj_le REAL NOT NULL
);
"""


def aujourd_hui():
    """But : date du jour à Paris (heure des joueurs), ou UTC si le fuseau manque."""
    import datetime
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo("Europe/Paris")).date()
    except Exception:                   # pas de base de fuseaux horaires
        return datetime.datetime.utcnow().date()

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
        self.verrou_progression = threading.Lock()      # lire + fusionner + écrire d'un bloc
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
            # Migration 2.0 : monnaie (NEONS) et bannière ; cadeau de bienvenue aux anciens.
            if "neons" not in colonnes:
                self.connexion.execute("ALTER TABLE joueurs ADD COLUMN neons INTEGER NOT NULL DEFAULT 0")
                self.connexion.execute("ALTER TABLE joueurs ADD COLUMN banniere TEXT NOT NULL DEFAULT ''")
                self._cadeaux_bienvenue()
            # Migration 2.0 : parties classées (cote Elo).
            if "elo" not in colonnes:
                self.connexion.execute("ALTER TABLE joueurs ADD COLUMN elo INTEGER NOT NULL DEFAULT 1000")
                self.connexion.execute("ALTER TABLE joueurs ADD COLUMN elo_max INTEGER NOT NULL DEFAULT 1000")
                self.connexion.execute("ALTER TABLE joueurs ADD COLUMN classees INTEGER NOT NULL DEFAULT 0")
            # Migration 2.1 : bilan des parties classées (victoires, derniers résultats « VDVVD »).
            colonnes = {l[1] for l in self.connexion.execute("PRAGMA table_info(joueurs)")}
            if "admin" not in colonnes:
                self.connexion.execute("ALTER TABLE joueurs ADD COLUMN admin INTEGER NOT NULL DEFAULT 0")
            # Les administrateurs sont donnés par NEON_ADMINS (réglage du serveur).
            self.connexion.execute("UPDATE joueurs SET admin = 0")
            for pseudo in config.ADMINS:
                self.connexion.execute("UPDATE joueurs SET admin = 1 WHERE pseudo = ?", (pseudo,))
            if "saison_max" not in colonnes:
                self.connexion.execute("ALTER TABLE joueurs ADD COLUMN saison_max INTEGER NOT NULL DEFAULT 0")
            # Migration 2.7 : joueur invisible (comptes d'admin) : absent des listes et classements.
            if "invisible" not in colonnes:
                self.connexion.execute("ALTER TABLE joueurs ADD COLUMN invisible INTEGER NOT NULL DEFAULT 0")
            if "classees_victoires" not in colonnes:
                self.connexion.execute("ALTER TABLE joueurs ADD COLUMN classees_victoires INTEGER NOT NULL DEFAULT 0")
                self.connexion.execute("ALTER TABLE joueurs ADD COLUMN classees_recents TEXT NOT NULL DEFAULT ''")
            # Migration 2.6 : anciens succès devenus des paliers (ex. briques_10000 -> briques_or).
            from serveur.succes import ANCIENS_CODES
            for ancien, nouveaux in ANCIENS_CODES.items():
                for nouveau in nouveaux:
                    self.connexion.execute(
                        "INSERT OR IGNORE INTO succes (joueur_id, code, obtenu_le) "
                        "SELECT joueur_id, ?, obtenu_le FROM succes WHERE code = ?", (nouveau, ancien))
                self.connexion.execute("DELETE FROM succes WHERE code = ?", (ancien,))
            self.connexion.commit()

    def _cadeaux_bienvenue(self):
        """But : créditer les joueurs existants selon ce qu'ils ont déjà accompli (2.0)."""
        from reseau.boutique import cadeau_bienvenue
        for joueur in self.connexion.execute("SELECT id, xp FROM joueurs").fetchall():
            ligne = self.connexion.execute("SELECT donnees FROM cumuls WHERE joueur_id = ?",
                                           (joueur["id"],)).fetchone()
            boss = json.loads(ligne["donnees"]).get("boss_vaincus", {}) if ligne else {}
            nb_succes = self.connexion.execute("SELECT COUNT(*) FROM succes WHERE joueur_id = ?",
                                               (joueur["id"],)).fetchone()[0]
            montant = cadeau_bienvenue(boss, nb_succes, catalogue.niveau_pour(joueur["xp"]))
            self.connexion.execute("UPDATE joueurs SET neons = ? WHERE id = ?",
                                   (montant, joueur["id"]))
            if ligne and boss:                  # boss déjà payés par le cadeau
                from reseau.boutique import MODES_CAMPAGNE
                cumul = json.loads(ligne["donnees"])
                cumul["boss_payes"] = sorted(f"{m}:{b}" for b in boss for m in MODES_CAMPAGNE)
                self.connexion.execute("UPDATE cumuls SET donnees = ? WHERE joueur_id = ?",
                                       (json.dumps(cumul), joueur["id"]))

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
            from reseau.boutique import cadeau_bienvenue
            return self.ecrire("INSERT INTO joueurs (pseudo, mdp, couleur, cree_le, vu_le, neons) "
                               "VALUES (?, ?, ?, ?, ?, ?)",
                               (pseudo, mdp_hache, couleur, maintenant, maintenant,
                                cadeau_bienvenue({}, 0, 1)))
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
        return skins_debloques(catalogue.niveau_pour(joueur["xp"]), set(self.succes_de(joueur["id"])),
                               self.possessions_de(joueur["id"]))

    # --- Monnaie et boutique (2.0) ---------------------------------------------------

    def possessions_de(self, joueur_id):
        """But : codes des objets de boutique d'un joueur. Sortie : (set)."""
        return {l["code"] for l in
                self.lire("SELECT code FROM possessions WHERE joueur_id = ?", (joueur_id,))}

    def bannieres_de(self, joueur_id):
        """But : bannières possédées (achetées, gagnées, ou de boss), dans l'ordre du catalogue."""
        from reseau.boutique import BANNIERES, bannieres_recompenses
        possedes = self.possessions_de(joueur_id) | bannieres_recompenses(set(self.succes_de(joueur_id)))
        return [b["code"] for b in BANNIERES if b["code"] in possedes]

    def crediter(self, joueur_id, montant, raison="PARTIE"):
        """But : ajouter (ou retirer) des NEONS, noté dans l'historique. Sortie : (int) solde."""
        self.ecrire("UPDATE joueurs SET neons = MAX(0, neons + ?) WHERE id = ?",
                    (int(montant), joueur_id))
        if montant:
            self.noter_mouvement(joueur_id, montant, raison)
        return self.joueur_par_id(joueur_id)["neons"]

    def noter_mouvement(self, joueur_id, montant, raison):
        self.ecrire("INSERT INTO mouvements (joueur_id, montant, raison, le) VALUES (?, ?, ?, ?)",
                    (joueur_id, int(montant), str(raison)[:40], time.time()))

    def historique(self, joueur_id, limite=20):
        """But : derniers mouvements de NEONS. Sortie : (list de dict) {montant, raison, le}."""
        return [dict(l) for l in self.lire("SELECT montant, raison, le FROM mouvements WHERE joueur_id = ? "
                                           "ORDER BY le DESC, id DESC LIMIT ?", (joueur_id, limite))]

    def envoyer_message(self, joueur_id, titre, texte=""):
        self.ecrire("INSERT INTO messages (joueur_id, titre, texte, cree_le) VALUES (?, ?, ?, ?)",
                    (joueur_id, str(titre)[:40], str(texte)[:60], time.time()))

    def messages_non_lus(self, joueur_id):
        return [dict(l) for l in self.lire("SELECT id, titre, texte FROM messages WHERE joueur_id = ? "
                                           "AND lu = 0 ORDER BY id LIMIT 10", (joueur_id,))]

    def marquer_lus(self, joueur_id, ids):
        for identifiant in list(ids)[:50]:
            self.ecrire("UPDATE messages SET lu = 1 WHERE id = ? AND joueur_id = ?",
                        (int(identifiant), joueur_id))

    def periode_versee(self, periode):
        return bool(self.lire("SELECT 1 FROM recompenses WHERE periode = ?", (periode,)))

    def marquer_versee(self, periode, valeur=""):
        self.ecrire("INSERT OR REPLACE INTO recompenses (periode, valeur, verse_le) VALUES (?, ?, ?)",
                    (periode, valeur, time.time()))

    def valeur_periode(self, periode):
        lignes = self.lire("SELECT valeur FROM recompenses WHERE periode = ?", (periode,))
        return lignes[0]["valeur"] if lignes else None

    def donner(self, joueur_id, code, origine):
        """But : offrir un objet (sans le payer). Sortie : (bool) True s'il est nouveau."""
        with self.verrou:
            curseur = self.connexion.execute(
                "INSERT OR IGNORE INTO possessions (joueur_id, code, origine, obtenu_le) VALUES (?, ?, ?, ?)",
                (joueur_id, code, origine, time.time()))
            self.connexion.commit()
            return curseur.rowcount == 1

    def acheter(self, joueur_id, code, prix, origine="achat"):
        """
        But : acheter un objet : débit et ajout dans une seule transaction.
        Sortie : (str ou None) message d'erreur, None si l'achat a réussi.
        """
        with self.verrou:
            try:
                deja = self.connexion.execute(
                    "SELECT 1 FROM possessions WHERE joueur_id = ? AND code = ?",
                    (joueur_id, code)).fetchone()
                if deja:
                    return "Deja possede"
                debit = self.connexion.execute(
                    "UPDATE joueurs SET neons = neons - ? WHERE id = ? AND neons >= ?",
                    (int(prix), joueur_id, int(prix)))
                if debit.rowcount != 1:
                    self.connexion.rollback()
                    return "Pas assez de NEONS"
                self.connexion.execute(
                    "INSERT INTO possessions (joueur_id, code, origine, obtenu_le) VALUES (?, ?, ?, ?)",
                    (joueur_id, code, origine, time.time()))
                self.connexion.execute(
                    "INSERT INTO mouvements (joueur_id, montant, raison, le) VALUES (?, ?, ?, ?)",
                    (joueur_id, -int(prix), ("BOITE MYSTERE" if origine == "boite" else "ACHAT") + " "
                     + code.upper()[:20], time.time()))
                self.connexion.commit()
                return None
            except sqlite3.Error:
                self.connexion.rollback()
                return "Erreur de la base"

    def ouvrir_boite(self, joueur_id, hasard=None):
        """
        But : acheter et ouvrir une boîte mystère.
        Sortie : (dict) {"erreur"} ou {"objet", "rembourse"}.
        """
        from reseau.boutique import PRIX_BOITE, REMBOURSEMENT_BOITE, tirer_boite
        joueur = self.joueur_par_id(joueur_id)
        if joueur["neons"] < PRIX_BOITE:
            return {"erreur": "Pas assez de NEONS"}
        gagne = tirer_boite(self.possessions_de(joueur_id), hasard)
        if gagne is None:
            return {"erreur": "Tu possedes deja tout !"}
        erreur = self.acheter(joueur_id, gagne["code"], PRIX_BOITE, origine="boite")
        if erreur:
            return {"erreur": erreur}
        return {"objet": gagne, "rembourse": 0}

    def appliquer_classee(self, gagnant_id, perdant_id):
        """
        But : mettre à jour les cotes Elo après une partie classée.
        Sortie : (dict) joueur_id -> {"elo", "elo_delta", "classees"}.
        """
        from reseau.classee import nouvelle_cote
        gagnant, perdant = self.joueur_par_id(gagnant_id), self.joueur_par_id(perdant_id)
        nouvelles = {gagnant_id: nouvelle_cote(gagnant["elo"], perdant["elo"], True, gagnant["classees"]),
                     perdant_id: nouvelle_cote(perdant["elo"], gagnant["elo"], False, perdant["classees"])}
        resultat = {}
        for joueur in (gagnant, perdant):
            cote = nouvelles[joueur["id"]]
            gagne = joueur["id"] == gagnant_id
            recents = (joueur["classees_recents"] + ("V" if gagne else "D"))[-10:]
            self.ecrire("UPDATE joueurs SET elo = ?, elo_max = MAX(elo_max, ?), classees = classees + 1, "
                        "classees_victoires = classees_victoires + ?, classees_recents = ?, "
                        "saison_max = MAX(saison_max, ?) WHERE id = ?",
                        (cote, cote, int(gagne), recents, cote, joueur["id"]))
            resultat[joueur["id"]] = {"elo": cote, "elo_delta": cote - joueur["elo"],
                                      "classees": joueur["classees"] + 1}
        return resultat

    def enregistrer_fantome(self, joueur_id, mode, jour, score, donnees):
        """But : garder le fantôme de la meilleure partie d'un joueur à un défi."""
        from reseau.fantome import valide
        if not valide(donnees):
            return
        self.ecrire("INSERT INTO fantomes (mode, jour, joueur_id, score, donnees) VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT(mode, jour, joueur_id) DO UPDATE SET score = excluded.score, "
                    "donnees = excluded.donnees WHERE excluded.score > fantomes.score",
                    (mode, jour, joueur_id, score, json.dumps(donnees)))
        # Ménage : on ne garde que les fantômes des 15 derniers défis.
        self.ecrire("DELETE FROM fantomes WHERE jour NOT IN (SELECT DISTINCT jour FROM fantomes "
                    "ORDER BY jour DESC LIMIT 15)")

    def meilleur_fantome(self, mode, jour):
        """But : fantôme du meilleur score d'un défi, ou None."""
        lignes = self.lire("SELECT f.score, f.donnees, j.pseudo FROM fantomes f JOIN joueurs j "
                           "ON j.id = f.joueur_id WHERE f.mode = ? AND f.jour = ? AND j.banni = 0 AND j.invisible = 0 "
                           "ORDER BY f.score DESC LIMIT 1", (mode, jour))
        if not lignes:
            return None
        return {"pseudo": lignes[0]["pseudo"], "score": lignes[0]["score"],
                "fantome": json.loads(lignes[0]["donnees"])}

    def est_admin(self, joueur):
        """But : le joueur est-il administrateur ? (réglage NEON_ADMINS du serveur)"""
        return bool(joueur["admin"]) or joueur["pseudo"].lower() in {a.lower() for a in config.ADMINS}

    def liste_admin(self):
        """But : tous les joueurs (bannis compris) avec ce qu'il faut pour les gérer."""
        return [{"pseudo": l["pseudo"], "niveau": catalogue.niveau_pour(l["xp"]), "neons": l["neons"],
                 "elo": l["elo"], "banni": bool(l["banni"]), "admin": bool(l["admin"]),
                 "invisible": bool(l["invisible"]),
                 "vu_le": l["vu_le"]}
                for l in self.lire("SELECT * FROM joueurs ORDER BY vu_le DESC")]

    def changer_banniere(self, joueur_id, code):
        self.ecrire("UPDATE joueurs SET banniere = ? WHERE id = ?", (code, joueur_id))

    def changer_mdp(self, joueur_id, mdp_hache):
        self.ecrire("UPDATE joueurs SET mdp = ? WHERE id = ?", (mdp_hache, joueur_id))

    # --- Progression gardée sur le compte (2.5) ------------------------------------------

    def progression(self, joueur_id):
        """But : progression enregistrée du joueur. Sortie : (dict), vide s'il n'en a pas."""
        lignes = self.lire("SELECT donnees FROM progressions WHERE joueur_id = ?", (joueur_id,))
        try:
            return json.loads(lignes[0]["donnees"]) if lignes else {}
        except ValueError:
            return {}

    def fusionner_progression(self, joueur_id, recue):
        """
        But : ajouter la progression d'un appareil à celle du compte (on garde le meilleur
        des deux, voir jeu/progression.py). Sortie : (dict) progression fusionnée.
        """
        from jeu.progression import fusionner
        with self.verrou_progression:
            fusion = fusionner(self.progression(joueur_id), recue)
            self.ecrire("INSERT INTO progressions (joueur_id, donnees, maj_le) VALUES (?, ?, ?) "
                        "ON CONFLICT(joueur_id) DO UPDATE SET donnees = excluded.donnees, "
                        "maj_le = excluded.maj_le",
                        (joueur_id, json.dumps(fusion, separators=(",", ":")), time.time()))
        return fusion

    def supprimer_joueur(self, joueur_id):
        """But : effacer un compte et tout ce qui lui appartient (parties, succès...)."""
        self.ecrire("DELETE FROM joueurs WHERE id = ?", (joueur_id,))

    def rattraper_paliers(self, joueur_id):
        """
        But : donner les paliers déjà mérités d'après les statistiques (ex. 2 344 briques
        cassées avant l'arrivée des paliers), avec leurs NEONS, sans attendre une partie.
        Sortie : (list de dict) succès donnés (pour les annoncer).
        """
        from reseau import boutique
        cumul = self.cumul(joueur_id)
        deja = set(self.succes_de(joueur_id))
        donnes = []
        for famille in catalogue.PALIERS:
            valeur = famille.mesurer(cumul)
            for code, seuil in zip(famille.codes(), famille.seuils):
                if code not in deja and valeur >= seuil:
                    self.ecrire("INSERT OR IGNORE INTO succes (joueur_id, code, obtenu_le) VALUES (?, ?, ?)",
                                (joueur_id, code, time.time()))
                    self.crediter(joueur_id, boutique.GAINS_PALIERS[code.rsplit("_", 1)[1]],
                                  "PALIER " + catalogue.PAR_CODE[code].nom)
                    donnes.append(catalogue.PAR_CODE[code].en_dict())
        return donnes

    def rendre_invisible(self, joueur_id, invisible=True):
        self.ecrire("UPDATE joueurs SET invisible = ? WHERE id = ?", (int(invisible), joueur_id))

    def pseudos_invisibles(self):
        """But : pseudos des joueurs invisibles (à cacher de la liste « en ligne »)."""
        return {l["pseudo"] for l in self.lire("SELECT pseudo FROM joueurs WHERE invisible = 1")}

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
        fantome = rapport.pop("fantome", None)
        rapport["en_ligne"] = en_ligne
        mode = str(rapport.get("mode", "?"))[:20]
        score = max(0, min(int(rapport.get("score_equipe", rapport.get("score", 0))), 10 ** 9))
        victoire = bool(rapport.get("victoire")) or rapport.get("gagnant") == rapport.get("numero")
        uid = rapport.get("uid")
        jour = str(rapport.get("jour"))[:10] if mode in ("defi", "semaine") and rapport.get("jour") \
            else None
        try:
            self.ecrire("INSERT INTO parties (uid, joueur_id, mode, score, victoire, en_ligne, "
                        "duree, details, joue_le, jour) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (uid, joueur_id, mode, score, int(victoire), int(en_ligne),
                         float(rapport.get("duree", 0)), json.dumps(rapport)[:20000],
                         float(rapport.get("joue_le", time.time())), jour))
        except sqlite3.IntegrityError:
            return {"doublon": True, "nouveaux_succes": []}
        if jour and fantome is not None:
            self.enregistrer_fantome(joueur_id, mode, jour, score, fantome)
        from reseau import boutique
        from reseau.series import en_cours
        cumul = self.cumul(joueur_id)
        serie = 0
        if mode == "defi" and jour:
            import datetime
            try:
                serie = en_cours(set(cumul.get("jours_defi", [])) | {jour},
                                 datetime.date.fromisoformat(jour))
            except ValueError:
                serie = 0
        detail = boutique.gains_partie(rapport, cumul, aujourd_hui().isoformat(), serie)
        ancien_niveau = catalogue.niveau_pour(self.joueur_par_id(joueur_id)["xp"])
        cumul = catalogue.mettre_a_jour_cumul(cumul, rapport)
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
        niveau = catalogue.niveau_pour(xp)
        simples = [c for c in nouveaux if c not in catalogue.PALIERS_PAR_CODE]
        if simples:
            detail.append((f"SUCCES x{len(simples)}", boutique.GAIN_SUCCES * len(simples)))
        for code in nouveaux:                   # paliers : plus le palier est haut, plus il rapporte
            if code in catalogue.PALIERS_PAR_CODE:
                palier = code.rsplit("_", 1)[1]
                detail.append((f"PALIER {palier.upper()}", boutique.GAINS_PALIERS[palier]))
        if niveau > ancien_niveau:
            detail.append((f"RANG {niveau}", boutique.GAIN_RANG * (niveau - ancien_niveau)))
        gagnes = boutique.total(detail)
        solde = self.crediter(joueur_id, gagnes, "PARTIE " + mode.upper()) if gagnes \
            else self.joueur_par_id(joueur_id)["neons"]
        return {"doublon": False, "xp_gagnee": gain, "xp": xp, "niveau": niveau,
                "neons_gagnes": gagnes, "detail_neons": detail, "neons": solde,
                "nouveaux_succes": [catalogue.PAR_CODE[c].en_dict() for c in nouveaux]}

    # --- Lectures publiques ----------------------------------------------------------

    def classement(self, mode, limite=20):
        """
        But : meilleur score de chaque joueur dans un mode (ou nombre de
        victoires en Duel / Course).
        Sortie : (list de dict) {"pseudo", "couleur", "valeur", "niveau"}.
        """
        if mode == "classe":
            lignes = self.lire(
                "SELECT pseudo, couleur, xp, banniere, elo AS valeur, classees FROM joueurs "
                "WHERE banni = 0 AND invisible = 0 AND classees > 0 ORDER BY elo DESC, classees ASC LIMIT ?", (limite,))
        elif mode in MODES_VICTOIRES:
            lignes = self.lire(
                "SELECT j.pseudo, j.couleur, j.xp, j.banniere, SUM(p.victoire) AS valeur, COUNT(*) AS parties "
                "FROM parties p JOIN joueurs j ON j.id = p.joueur_id "
                "WHERE p.mode = ? AND j.banni = 0 AND j.invisible = 0 GROUP BY p.joueur_id "
                "ORDER BY valeur DESC, parties ASC LIMIT ?", (mode, limite))
        else:
            lignes = self.lire(
                "SELECT j.pseudo, j.couleur, j.xp, j.banniere, MAX(p.score) AS valeur "
                "FROM parties p JOIN joueurs j ON j.id = p.joueur_id "
                "WHERE p.mode = ? AND j.banni = 0 AND j.invisible = 0 GROUP BY p.joueur_id "
                "ORDER BY valeur DESC LIMIT ?", (mode, limite))
        return [{"pseudo": l["pseudo"], "couleur": l["couleur"], "valeur": int(l["valeur"] or 0),
                 "niveau": catalogue.niveau_pour(l["xp"]), "banniere": l["banniere"]} for l in lignes]

    def classement_defi(self, jour, limite=20, mode="defi"):
        """But : meilleur score de chaque joueur au défi d'un jour (ou d'une semaine)."""
        lignes = self.lire(
            "SELECT j.pseudo, j.couleur, j.xp, j.banniere, MAX(p.score) AS valeur, COUNT(*) AS essais "
            "FROM parties p JOIN joueurs j ON j.id = p.joueur_id "
            "WHERE p.mode = ? AND p.jour = ? AND j.banni = 0 AND j.invisible = 0 GROUP BY p.joueur_id "
            "ORDER BY valeur DESC LIMIT ?", (mode, jour, limite))
        return [{"pseudo": l["pseudo"], "couleur": l["couleur"], "valeur": int(l["valeur"] or 0),
                 "niveau": catalogue.niveau_pour(l["xp"]), "essais": l["essais"],
                 "banniere": l["banniere"]} for l in lignes]

    def jours_joues(self, joueur_id, mode="defi"):
        """But : jours (ou semaines) où le joueur a fait ce défi."""
        return [l["jour"] for l in self.lire(
            "SELECT DISTINCT jour FROM parties WHERE joueur_id = ? AND mode = ? AND jour IS NOT NULL",
            (joueur_id, mode))]

    def series_de(self, joueur_id, aujourd_hui):
        """But : séries du défi du jour et du défi de la semaine d'un joueur."""
        from reseau.series import resume
        return {"jour": resume(self.jours_joues(joueur_id, "defi"), aujourd_hui),
                "semaine": resume(self.jours_joues(joueur_id, "semaine"), aujourd_hui,
                                  semaines=True)}

    def classement_series(self, aujourd_hui, limite=20):
        """
        But : séries du défi du jour de tous les joueurs, de la plus longue en cours
        à la plus courte (le record départage).
        Sortie : (list de dict) {"pseudo", "couleur", "niveau", "valeur", "record"}.
        """
        from reseau.series import resume
        par_joueur = {}
        for l in self.lire("SELECT p.joueur_id, p.jour FROM parties p JOIN joueurs j "
                           "ON j.id = p.joueur_id WHERE p.mode = 'defi' AND p.jour IS NOT NULL "
                           "AND j.banni = 0 AND j.invisible = 0"):
            par_joueur.setdefault(l["joueur_id"], set()).add(l["jour"])
        lignes = []
        for joueur_id, jours in par_joueur.items():
            joueur = self.joueur_par_id(joueur_id)
            serie = resume(jours, aujourd_hui)
            lignes.append({"pseudo": joueur["pseudo"], "couleur": joueur["couleur"],
                           "banniere": joueur["banniere"],
                           "niveau": catalogue.niveau_pour(joueur["xp"]),
                           "valeur": serie["en_cours"], "record": serie["record"]})
        lignes.sort(key=lambda l: (-l["valeur"], -l["record"], l["pseudo"].lower()))
        return lignes[:limite]

    def liste_joueurs(self, tous=False):
        """
        But : les joueurs (non bannis, et visibles sauf si tous=True), du plus haut niveau
        au plus bas.
        """
        lignes = self.lire("SELECT id, pseudo, couleur, xp, vu_le, banniere FROM joueurs "
                           "WHERE banni = 0" + ("" if tous else " AND invisible = 0") +
                           " ORDER BY xp DESC, pseudo")
        nb_succes = {l["joueur_id"]: l["n"] for l in
                     self.lire("SELECT joueur_id, COUNT(*) AS n FROM succes GROUP BY joueur_id")}
        return [{"pseudo": l["pseudo"], "couleur": l["couleur"], "xp": l["xp"],
                 "niveau": catalogue.niveau_pour(l["xp"]), "vu_le": l["vu_le"],
                 "banniere": l["banniere"], "succes": nb_succes.get(l["id"], 0)} for l in lignes]

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
        for famille in catalogue.PALIERS:       # succès à paliers d'abord (avec leur progression)
            atteints = catalogue.palier_obtenu(famille, obtenus)
            dates = [obtenus[c] for c in famille.codes() if c in obtenus]
            liste_succes.append({
                "code": famille.code, "icone": famille.icone, "nom": famille.nom,
                "description": famille.description.format(n="..."), "categorie": famille.categorie,
                "secret": False, "palier": atteints, "seuils": list(famille.seuils),
                "valeur": famille.mesurer(cumul), "obtenu_le": max(dates) if dates else None})
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
                "skin": joueur["skin"], "banniere": joueur["banniere"],
                "elo": joueur["elo"], "elo_max": joueur["elo_max"], "classees": joueur["classees"],
                "classees_victoires": joueur["classees_victoires"],
                "classees_recents": joueur["classees_recents"],
                "objets": len(self.possessions_de(jid)), "niveau": niveau, "xp_niveau": catalogue.xp_pour_niveau(niveau),
                "xp_suivant": catalogue.xp_pour_niveau(niveau + 1),
                "cree_le": joueur["cree_le"], "vu_le": joueur["vu_le"],
                "stats": {"parties": cumul.get("parties", 0), "briques": cumul.get("briques", 0),
                          "temps": cumul.get("temps", 0),
                          "meilleur_combo": cumul.get("meilleur_combo", 0),
                          "supernovas": cumul.get("supernovas", 0),
                          "victoires": cumul.get("victoires", {}),
                          "boss_vaincus": cumul.get("boss_vaincus", {})},
                "records": records, "succes": liste_succes, "dernieres_parties": dernieres}
