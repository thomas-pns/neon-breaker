# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Parties ouvertes, salons d'attente et parties en ligne, sur une seule
    connexion WebSocket par joueur.

    Messages du client (champ "t") :
      auth {jeton, protocole}      lister                  creer {mode, niveau}
      rejoindre {id}               quitter                 pret {v}
      lancer                       cmd {x, vx, a}          abandon
      ping {c}                     file {v}   (file des parties classées, 2.0)
    Messages du serveur :
      bienvenue {pseudo}           salons {liste, en_ligne, max}
      salon {...}                  debut {mode, niveau, numero, joueurs}
      etat {instantané, pause}     fin {resultat, gains}
      erreur {msg}                 pong {c}
      file {v, attente, joueurs, elo}  (recherche d'adversaire classé)

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import asyncio
import itertools
import json
import logging
import time

from moteur.version import PROTOCOLE
from serveur import config
from serveur.securite import empreinte_jeton
from reseau.instantane import capturer
from serveur.simulation import Simulation
from serveur.succes import niveau_pour

journal = logging.getLogger("neon.salons")
MODES_EN_LIGNE = ("coop", "duel", "course")
_ids = itertools.count(1)


class Connexion:
    """
    Un joueur connecté. Les envois passent par une file pour qu'un client
    lent ne bloque jamais la boucle de jeu (les vieux états sont jetés).
    """

    def __init__(self, websocket, joueur):
        self.websocket = websocket
        self.joueur_id = joueur["id"]
        self.pseudo = joueur["pseudo"]
        self.couleur = joueur["couleur"]
        self.skin = joueur["skin"] if "skin" in joueur.keys() else "neon"
        self.banniere = joueur["banniere"] if "banniere" in joueur.keys() else ""
        self.niveau = niveau_pour(joueur["xp"])
        self.elo = joueur["elo"] if "elo" in joueur.keys() else 1000
        self.salon = None
        self.file = []                    # messages à envoyer, dans l'ordre (texte JSON)
        self.etat_en_attente = None       # dernier état de partie pas encore envoyé (dict)
        self.signal = asyncio.Event()
        self.boucle = asyncio.get_running_loop()
        self.ouverte = True
        self.tache_envoi = asyncio.create_task(self._envoyer_en_continu())

    def envoyer(self, message):
        """
        But : mettre un message en file (sans attendre). Les états de partie ne
        s'empilent pas : si le réseau du joueur a un raté, il reçoit directement
        l'état le plus récent (fusionné pour ne perdre aucune brique ni effet)
        au lieu de rattraper une file d'états périmés.
        """
        if not self.ouverte:
            return
        if message.get("t") == "etat":
            if self.etat_en_attente is not None:
                from reseau.instantane import fusionner_etats
                message = fusionner_etats(self.etat_en_attente, message)
            self.etat_en_attente = message
        else:
            if self.etat_en_attente is not None:      # garder l'ordre : l'état d'abord
                self.file.append(json.dumps(self.etat_en_attente, separators=(",", ":")))
                self.etat_en_attente = None
            self.file.append(json.dumps(message, separators=(",", ":")))
            del self.file[:-200]
        self._reveiller()

    def _reveiller(self):
        """But : réveiller la tâche d'envoi, même depuis une autre boucle (tests, fils)."""
        try:
            meme_boucle = asyncio.get_running_loop() is self.boucle
        except RuntimeError:
            meme_boucle = False
        if meme_boucle:
            self.signal.set()
        else:
            self.boucle.call_soon_threadsafe(self.signal.set)

    async def _envoyer_en_continu(self):
        try:
            while True:
                await self.signal.wait()
                self.signal.clear()
                while self.file or self.etat_en_attente is not None:
                    if self.file:
                        texte = self.file.pop(0)
                    else:
                        texte = json.dumps(self.etat_en_attente, separators=(",", ":"))
                        self.etat_en_attente = None
                    await self.websocket.send_text(texte)
        except Exception:                       # connexion fermée
            self.ouverte = False

    def fermer(self):
        self.ouverte = False
        self.tache_envoi.cancel()


class Salon:
    """
    Une partie ouverte. Attributs : id, mode, niveau, membres (list de
    pseudos, dans l'ordre J1, J2), prets (set), etat ("attente" / "jeu"),
    simulation, absents (pseudo -> date limite de retour).
    """

    def __init__(self, mode, niveau, hote):
        self.id = next(_ids)
        self.mode = mode
        self.niveau = niveau
        self.membres = [hote]
        self.prets = set()
        self.etat = "attente"
        self.simulation = None
        self.tache = None
        self.absents = {}
        self.classee = False

    def hote(self):
        return self.membres[0] if self.membres else ""

    def resume(self):
        return {"id": self.id, "mode": self.mode, "niveau": self.niveau, "hote": self.hote(),
                "joueurs": list(self.membres), "etat": self.etat,
                "places": config.JOUEURS_PAR_PARTIE, "classee": self.classee}


class Gestionnaire:
    """Toutes les connexions et tous les salons du serveur."""

    def __init__(self, base):
        self.base = base
        self.connexions = {}
        self.salons = {}
        self.file_classee = {}          # pseudo -> (cote, entrée dans la file)
        self.tache_file = None

    # --- Connexions ------------------------------------------------------------

    async def accueillir(self, websocket):
        """
        But : boucle de vie d'une connexion WebSocket (authentification, puis
        traitement des messages jusqu'à la déconnexion).
        """
        await websocket.accept()
        try:
            premier = json.loads(await asyncio.wait_for(websocket.receive_text(), 10))
        except Exception:
            await websocket.close()
            return
        if premier.get("protocole") != PROTOCOLE:
            await websocket.send_text(json.dumps({"t": "erreur", "fatal": True,
                                                  "msg": "MISE A JOUR NECESSAIRE"}))
            await websocket.close()
            return
        joueur = self.base.joueur_par_session(empreinte_jeton(str(premier.get("jeton", ""))))
        if premier.get("t") != "auth" or joueur is None:
            await websocket.send_text(json.dumps({"t": "erreur", "fatal": True,
                                                  "msg": "SESSION EXPIREE"}))
            await websocket.close()
            return
        connexion = Connexion(websocket, joueur)
        self.brancher(connexion)
        try:
            while True:
                message = json.loads(await websocket.receive_text())
                if isinstance(message, dict):
                    self.traiter(connexion, message)
        except Exception:
            pass
        finally:
            self.debrancher(connexion)

    def brancher(self, connexion):
        ancienne = self.connexions.get(connexion.pseudo)
        if ancienne is not None:
            ancienne.salon = None
            ancienne.fermer()
        self.connexions[connexion.pseudo] = connexion
        self.base.toucher(connexion.joueur_id)
        connexion.envoyer({"t": "bienvenue", "pseudo": connexion.pseudo})
        # Retour dans une partie en cours après une coupure ?
        for salon in self.salons.values():
            if salon.etat == "jeu" and connexion.pseudo in salon.membres:
                connexion.salon = salon
                salon.absents.pop(connexion.pseudo, None)
                self._envoyer_debut(salon, connexion)
                connexion.envoyer({"t": "etat", **salon.simulation.instantane_force()})
                break
        self.diffuser_liste()

    def debrancher(self, connexion):
        connexion.fermer()
        self.file_classee.pop(connexion.pseudo, None)
        if self.connexions.get(connexion.pseudo) is connexion:
            del self.connexions[connexion.pseudo]
            salon = connexion.salon
            if salon is not None:
                if salon.etat == "jeu":
                    journal.info("%s déconnecté pendant la partie %s", connexion.pseudo, salon.id)
                    salon.absents[connexion.pseudo] = time.monotonic() + config.ATTENTE_RECONNEXION
                else:
                    self.quitter_salon(connexion)
        self.diffuser_liste()

    # --- Liste et salons --------------------------------------------------------------

    def diffuser_liste(self):
        """But : envoyer la liste des parties à tous ceux qui ne jouent pas."""
        message = {"t": "salons", "liste": [s.resume() for s in self.salons.values()],
                   "en_ligne": sorted(set(self.connexions) - self.base.pseudos_invisibles()),
                   "max": config.MAX_PARTIES}
        for connexion in self.connexions.values():
            if connexion.salon is None or connexion.salon.etat == "attente":
                connexion.envoyer(message)

    def envoyer_salon(self, salon):
        joueurs = []
        for pseudo in salon.membres:
            connexion = self.connexions.get(pseudo)
            joueurs.append({"pseudo": pseudo, "pret": pseudo in salon.prets,
                            "couleur": connexion.couleur if connexion else "cyan",
                            "skin": connexion.skin if connexion else "neon",
                            "banniere": connexion.banniere if connexion else "",
                            "niveau": connexion.niveau if connexion else 1})
        message = {"t": "salon", **salon.resume(), "joueurs": joueurs}
        for pseudo in salon.membres:
            if pseudo in self.connexions:
                self.connexions[pseudo].envoyer(message)

    def traiter(self, connexion, message):
        """But : répondre à un message d'un client."""
        nature = message.get("t")
        salon = connexion.salon
        if nature == "cmd":
            if salon is not None and salon.etat == "jeu" and connexion.pseudo in salon.membres:
                numero = salon.membres.index(connexion.pseudo) + 1
                salon.simulation.recevoir_commande(numero, message)
        elif nature == "rebond":
            if salon is not None and salon.etat == "jeu" and connexion.pseudo in salon.membres:
                numero = salon.membres.index(connexion.pseudo) + 1
                salon.simulation.recevoir_rebond(numero, message)
        elif nature == "ping":
            connexion.envoyer({"t": "pong", "c": message.get("c")})
        elif nature == "lister":
            self.diffuser_liste()
        elif nature in ("creer", "rejoindre") and salon is not None and salon.etat == "jeu":
            # Un écran resté en arrière ne doit jamais faire quitter une partie en cours :
            # seuls « abandon » et « quitter » y mettent fin.
            journal.info("%s : « %s » ignoré pendant la partie %s", connexion.pseudo, nature, salon.id)
            connexion.envoyer({"t": "erreur", "msg": "PARTIE EN COURS"})
        elif nature == "creer":
            self.creer_salon(connexion, message)
        elif nature == "rejoindre":
            self.rejoindre(connexion, message.get("id"))
        elif nature == "quitter":
            self.quitter_salon(connexion)
        elif nature == "pret" and salon is not None and salon.etat == "attente":
            if message.get("v", True):
                salon.prets.add(connexion.pseudo)
            else:
                salon.prets.discard(connexion.pseudo)
            self.envoyer_salon(salon)
        elif nature == "lancer" and salon is not None:
            self.lancer(connexion, salon)
        elif nature == "file":
            mode = message.get("mode") if message.get("mode") in ("duel", "course") else "duel"
            self.file(connexion, bool(message.get("v", True)), mode)
        elif nature == "abandon" and salon is not None and salon.etat == "jeu":
            journal.info("%s abandonne la partie %s", connexion.pseudo, salon.id)
            asyncio.create_task(self.terminer(salon, abandon=connexion.pseudo))

    def creer_salon(self, connexion, message):
        mode = message.get("mode")
        if mode not in MODES_EN_LIGNE:
            connexion.envoyer({"t": "erreur", "msg": "MODE INCONNU"})
            return
        if len(self.salons) >= config.MAX_PARTIES:
            connexion.envoyer({"t": "erreur", "msg": f"{config.MAX_PARTIES} PARTIES MAXIMUM"})
            return
        self.quitter_salon(connexion)
        try:
            niveau = max(0, min(11, int(message.get("niveau", 0))))
        except (TypeError, ValueError):
            niveau = 0
        salon = Salon(mode, niveau if mode == "coop" else 0, connexion.pseudo)
        self.salons[salon.id] = salon
        connexion.salon = salon
        self.envoyer_salon(salon)
        self.diffuser_liste()

    def rejoindre(self, connexion, identifiant):
        salon = self.salons.get(identifiant)
        if salon is None or salon.etat != "attente":
            connexion.envoyer({"t": "erreur", "msg": "PARTIE INTROUVABLE"})
            return
        if connexion.pseudo in salon.membres:
            return
        if len(salon.membres) >= config.JOUEURS_PAR_PARTIE:
            connexion.envoyer({"t": "erreur", "msg": "PARTIE COMPLETE"})
            return
        self.quitter_salon(connexion)
        salon.membres.append(connexion.pseudo)
        connexion.salon = salon
        self.envoyer_salon(salon)
        self.diffuser_liste()

    def quitter_salon(self, connexion):
        salon = connexion.salon
        if salon is None:
            return
        connexion.salon = None
        if salon.etat == "jeu":
            asyncio.create_task(self.terminer(salon, abandon=connexion.pseudo))
            return
        if connexion.pseudo in salon.membres:
            salon.membres.remove(connexion.pseudo)
        salon.prets.discard(connexion.pseudo)
        if not salon.membres:
            self.salons.pop(salon.id, None)
        else:
            salon.prets.clear()
            self.envoyer_salon(salon)
        self.diffuser_liste()

    # --- Parties classées (2.0) -----------------------------------------------------

    def file(self, connexion, entrer, mode="duel"):
        """But : entrer dans la file des parties classées (Duel ou Course), ou en sortir."""
        if not entrer:
            self.file_classee.pop(connexion.pseudo, None)
            connexion.envoyer({"t": "file", "v": False})
            return
        if connexion.salon is not None and connexion.salon.etat == "jeu":
            return
        self.quitter_salon(connexion)
        joueur = self.base.joueur_par_id(connexion.joueur_id)
        connexion.elo = joueur["elo"]
        self.file_classee[connexion.pseudo] = (connexion.elo, time.monotonic(), mode)
        self._etat_file()
        if self.tache_file is None or self.tache_file.done():
            self.tache_file = asyncio.create_task(self._boucle_file())

    def _etat_file(self):
        maintenant = time.monotonic()
        for pseudo, (cote, entree, mode) in self.file_classee.items():
            connexion = self.connexions.get(pseudo)
            if connexion is not None:
                meme_mode = sum(1 for e in self.file_classee.values() if e[2] == mode)
                connexion.envoyer({"t": "file", "v": True, "attente": round(maintenant - entree),
                                   "joueurs": meme_mode, "elo": cote, "mode": mode})

    async def _boucle_file(self):
        """But : toutes les secondes, former des paires et prévenir ceux qui attendent."""
        from reseau.classee import apparier
        while self.file_classee:
            for mode in ("duel", "course"):
                file = {p: e[:2] for p, e in self.file_classee.items() if e[2] == mode}
                for a, b in apparier(file, time.monotonic()):
                    self.file_classee.pop(a, None)
                    self.file_classee.pop(b, None)
                    if a in self.connexions and b in self.connexions:
                        self._demarrer_classee(a, b, mode)
                    else:                               # l'un est parti entre-temps
                        for pseudo in (a, b):
                            if pseudo in self.connexions:
                                self.file_classee[pseudo] = (self.connexions[pseudo].elo,
                                                             time.monotonic(), mode)
            self._etat_file()
            await asyncio.sleep(1)

    def _demarrer_classee(self, a, b, mode="duel"):
        if len(self.salons) >= config.MAX_PARTIES:
            for pseudo in (a, b):
                self.file_classee[pseudo] = (self.connexions[pseudo].elo, time.monotonic(), mode)
            return
        salon = Salon(mode, 0, a)
        salon.classee = True
        salon.membres.append(b)
        salon.prets = {a, b}
        self.salons[salon.id] = salon
        for pseudo in (a, b):
            self.connexions[pseudo].salon = salon
        journal.info("Partie classée (%s) : %s contre %s", mode, a, b)
        self._demarrer(salon)

    def lancer(self, connexion, salon):
        if salon.etat != "attente" or connexion.pseudo != salon.hote():
            return
        if len(salon.membres) < config.JOUEURS_PAR_PARTIE:
            connexion.envoyer({"t": "erreur", "msg": "IL MANQUE UN JOUEUR"})
            return
        if set(salon.membres) - salon.prets:
            connexion.envoyer({"t": "erreur", "msg": "TOUT LE MONDE DOIT ETRE PRET"})
            return
        self._demarrer(salon)

    def _demarrer(self, salon):
        """But : lancer la simulation d'un salon complet et prévenir les joueurs."""
        salon.etat = "jeu"
        salon.simulation = SimulationReseau(salon.mode, salon.membres, salon.niveau)
        for pseudo in salon.membres:
            if pseudo in self.connexions:
                self._envoyer_debut(salon, self.connexions[pseudo])
        salon.tache = asyncio.create_task(self.boucle(salon))
        self.diffuser_liste()

    def _envoyer_debut(self, salon, connexion):
        connexion.envoyer({"t": "debut", "mode": salon.mode, "niveau": salon.niveau,
                           "numero": salon.membres.index(connexion.pseudo) + 1,
                           "joueurs": list(salon.membres), "classee": salon.classee,
                           "elos": [self.connexions[p].elo if p in self.connexions else 1000
                                    for p in salon.membres],
                           "skins": [self.connexions[p].skin if p in self.connexions else "neon"
                                     for p in salon.membres]})

    def _resultat_classee(self, salon, resultat, abandon, gains):
        """But : appliquer l'Elo d'une partie classée et l'ajouter aux gains de chacun."""
        if len(salon.membres) != 2:
            return
        gagnant = gagnant_classee(salon.membres, resultat, abandon)
        if gagnant is None:
            return
        perdant = next(p for p in salon.membres if p != gagnant)
        joueurs = {p: self.base.joueur_par_pseudo(p) for p in salon.membres}
        if any(j is None for j in joueurs.values()):
            return
        cotes = self.base.appliquer_classee(joueurs[gagnant]["id"], joueurs[perdant]["id"])
        for pseudo, joueur in joueurs.items():
            gains[pseudo] = dict(gains.get(pseudo) or {}, classee=True, victoire_classee=pseudo == gagnant,
                                 **cotes[joueur["id"]])
            if pseudo in self.connexions:
                self.connexions[pseudo].elo = cotes[joueur["id"]]["elo"]

    # --- Boucle de jeu ---------------------------------------------------------------

    async def boucle(self, salon):
        """But : faire tourner la partie à 60 images par seconde."""
        periode = 1 / 60
        boucle = asyncio.get_running_loop()
        prochain = boucle.time()
        image = 0
        envoi_tous = max(1, round(60 / config.FREQUENCE_INSTANTANES))
        try:
            while salon.etat == "jeu":
                maintenant = time.monotonic()
                expires = [p for p, limite in salon.absents.items() if maintenant > limite]
                if expires:
                    await self.terminer(salon, abandon=expires[0])
                    return
                if not salon.absents:
                    salon.simulation.avancer(periode)
                image += 1
                if image % envoi_tous == 0:
                    self._diffuser_etat(salon)
                if salon.simulation.resultat() is not None:
                    self._diffuser_etat(salon)
                    await self.terminer(salon)
                    return
                prochain += periode
                attente = prochain - boucle.time()
                if attente < -0.25:
                    prochain = boucle.time()          # trop en retard : on repart
                await asyncio.sleep(max(0.0, attente))
        except Exception:
            journal.exception("Erreur dans la partie %s", salon.id)
            await self.terminer(salon, abandon="SERVEUR")

    def _diffuser_etat(self, salon):
        donnees = salon.simulation.instantane()
        if salon.absents:
            donnees["pause"] = {p: round(l - time.monotonic(), 1) for p, l in salon.absents.items()}
        message = {"t": "etat", **donnees}
        for pseudo in salon.membres:
            connexion = self.connexions.get(pseudo)
            if connexion is not None and connexion.salon is salon:
                connexion.envoyer(message)

    async def terminer(self, salon, abandon=None):
        """
        But : clore une partie : enregistrer les résultats (sauf abandon),
        prévenir les joueurs, fermer le salon.
        """
        if salon.etat != "jeu":
            return
        salon.etat = "fini"
        journal.info("Partie %s terminée, rebonds annoncés : %s", salon.mode,
                     salon.simulation.rebonds)
        resultat = salon.simulation.resultat() if abandon is None else None
        gains = {}
        if resultat is not None:
            for rapport in resultat.get("rapports", []):
                numero = rapport.get("numero", 1)
                if numero - 1 >= len(salon.membres):
                    continue
                pseudo = salon.membres[numero - 1]
                joueur = self.base.joueur_par_pseudo(pseudo)
                if joueur is not None:
                    gains[pseudo] = self.base.enregistrer_partie(joueur["id"], rapport, en_ligne=True)
            public = {k: v for k, v in resultat.items() if k != "rapports"}
            if "couleur" in public:
                public["couleur"] = list(public["couleur"])
        else:
            raison = "COUPURE TROP LONGUE" if abandon in salon.absents else "ABANDON"
            public = {"victoire": False, "titre": "PARTIE INTERROMPUE", "score": 0,
                      "mode": salon.mode, "lignes": [(raison, str(abandon or "?"))]}
            if salon.classee and abandon in salon.membres:
                public["titre"] = f"{abandon.upper()[:10]} ABANDONNE"
                public["lignes"].append(("CLASSEE", "VICTOIRE A L'AUTRE"))
        if abandon is not None:
            journal.info("Partie %s (%s) interrompue : %s (%s)", salon.id, salon.mode, abandon,
                         "coupure" if abandon in salon.absents else "abandon")
        if salon.classee:
            try:
                self._resultat_classee(salon, resultat, abandon, gains)
            except Exception:
                journal.exception("Elo de la partie %s non appliqué", salon.id)
        for pseudo in salon.membres:
            connexion = self.connexions.get(pseudo)
            if connexion is not None and connexion.salon is salon:
                connexion.envoyer({"t": "fin", "resultat": public, "gains": gains.get(pseudo)})
                connexion.salon = None
        self.salons.pop(salon.id, None)
        if salon.tache is not None and salon.tache is not asyncio.current_task():
            salon.tache.cancel()
        self.diffuser_liste()


def gagnant_classee(membres, resultat, abandon):
    """
    But : pseudo du gagnant d'une partie classée (celui qui abandonne ou ne
    revient pas perd ; une panne du serveur ne compte pas).
    Sortie : (str ou None).
    """
    if abandon is not None:
        if abandon not in membres:
            return None
        return next((p for p in membres if p != abandon), None)
    if resultat is None:
        return None
    for rapport in resultat.get("rapports", []):
        gagnant = rapport.get("gagnant")
        if gagnant in (1, 2) and gagnant - 1 < len(membres):
            return membres[gagnant - 1]
    return None


class SimulationReseau(Simulation):
    """Simulation avec un envoi « complet » pour les joueurs qui reviennent."""

    def instantane_force(self):
        """État complet (toutes les briques) sans vider le journal des effets."""
        return {**capturer(self.mode, self.app.fond, {}, forcer=True), "fx": []}
