# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Service « en ligne » du jeu : appels HTTP au serveur (comptes, scores,
    profils), connexion WebSocket temps réel (parties en ligne), file
    d'attente des scores joués hors ligne et notifications de succès.

    Rien ne bloque l'affichage : chaque appel part dans un fil séparé et
    son résultat revient dans une file, traitée une fois par image par
    l'application (méthode traiter). Le jeu reste jouable hors ligne : si
    le serveur ne répond pas, on garde simplement les scores pour plus tard.

    Pour les tests, NEON_LATENCE_MS ajoute un délai aux messages temps réel, et
    NEON_GIGUE_MS un délai aléatoire en plus (l'ordre des messages est gardé).

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import asyncio
import json
import os
import queue
import threading
import time
import urllib.error
import urllib.request
import uuid

from moteur import config, web
from moteur.version import PROTOCOLE, VERSION, adresse_serveur

LATENCE = float(os.environ.get("NEON_LATENCE_MS", "0")) / 1000
GIGUE = float(os.environ.get("NEON_GIGUE_MS", "0")) / 1000      # tests : réseau irrégulier


def contexte_ssl():
    """Certificats fournis par certifi (indispensable dans l'application macOS)."""
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


class TempsReel:
    """
    Connexion WebSocket dans un fil dédié (avec sa propre boucle asyncio).
    Attributs : etat ("ferme", "connexion", "ouvert", "erreur"), recus (queue).
    """

    def __init__(self, url, jeton):
        self.derniere_echeance = 0.0
        self.url = url
        self.jeton = jeton
        self.etat = "ferme"
        self.erreur = ""
        self.recus = queue.Queue()
        self.boucle = None
        self.a_envoyer = None
        self.fil = None
        self.ping = 0.0
        self.en_retard = []          # messages dont la latence simulée court encore

    def ouvrir(self):
        if self.etat in ("connexion", "ouvert"):
            return
        self.etat = "connexion"
        self.fil = threading.Thread(target=self._executer, daemon=True)
        self.fil.start()

    def _executer(self):
        self.boucle = asyncio.new_event_loop()
        try:
            self.boucle.run_until_complete(self._session())
        except Exception as erreur:            # serveur injoignable, coupure...
            self.erreur = (type(erreur).__name__ + " " + str(erreur))[:120]
        finally:
            if self.etat != "ferme":
                journaliser(f"coupure : {self.erreur or 'fermee sans raison'} "
                            f"(ping {self.ping:.0f} ms)")
            if self.etat != "ferme":
                self.etat = "erreur"
            self.boucle.close()

    async def _session(self):
        import websockets
        self.a_envoyer = asyncio.Queue()
        options = {"open_timeout": 8, "max_size": 2 ** 22}
        if self.url.startswith("wss://"):
            options["ssl"] = contexte_ssl()
        async with websockets.connect(self.url, **options) as socket:
            await socket.send(json.dumps({"t": "auth", "jeton": self.jeton,
                                          "protocole": PROTOCOLE, "version": VERSION}))
            self.etat = "ouvert"

            async def recevoir():
                async for texte in socket:
                    # Latence simulée : le message est daté, pas mis en attente
                    # (sinon les retards s'additionneraient).
                    echeance = time.monotonic() + LATENCE / 2
                    if GIGUE:
                        import random
                        echeance = max(self.derniere_echeance, echeance + random.uniform(0, GIGUE))
                        self.derniere_echeance = echeance
                    self.recus.put((echeance, json.loads(texte)))

            async def envoyer():
                while True:
                    echeance, message = await self.a_envoyer.get()
                    if message is None:
                        await socket.close()
                        return
                    attente = echeance - time.monotonic()
                    if attente > 0:
                        await asyncio.sleep(attente)
                    await socket.send(json.dumps(message, separators=(",", ":")))

            async def pinger():
                while True:
                    await asyncio.sleep(2)
                    self._poster({"t": "ping", "c": time.monotonic()})

            taches = [asyncio.ensure_future(t()) for t in (recevoir, envoyer, pinger)]
            finies, _ = await asyncio.wait(taches, return_when=asyncio.FIRST_COMPLETED)
            for tache in taches:
                tache.cancel()
            for tache in finies:
                if not tache.cancelled() and tache.exception() is not None:
                    raise tache.exception()
            code = getattr(socket, "close_code", None)
            if code is not None and code != 1000:
                self.erreur = f"fermee par le serveur, code {code} {getattr(socket, 'close_reason', '')}"

    def _poster(self, message):
        """Dans la boucle réseau : mettre un message en file d'envoi (daté)."""
        self.a_envoyer.put_nowait((time.monotonic() + LATENCE / 2, message))

    def envoyer(self, message):
        """But : envoyer un message (depuis le fil du jeu)."""
        if self.etat == "ouvert" and self.boucle is not None:
            self.boucle.call_soon_threadsafe(self._poster, message)

    def messages(self):
        """
        But : messages reçus (et arrivés à échéance) depuis le dernier appel.
        Sortie : (list de dict).
        """
        maintenant = time.monotonic()
        resultat = []
        while self.en_retard and self.en_retard[0][0] <= maintenant:
            resultat.append(self.en_retard.pop(0)[1])
        while True:
            try:
                echeance, message = self.recus.get_nowait()
            except queue.Empty:
                break
            if echeance > maintenant:
                self.en_retard.append((echeance, message))
            else:
                resultat.append(message)
        for message in resultat:
            if message.get("t") == "pong" and message.get("c"):
                self.ping = (time.monotonic() - message["c"]) * 1000
        return resultat

    def fermer(self):
        if self.etat == "ouvert" and self.boucle is not None:
            self.boucle.call_soon_threadsafe(self._poster, None)
        self.etat = "ferme"


class TempsReelWeb:
    """
    Même rôle que TempsReel pour la version navigateur : le WebSocket est
    celui de la page (moteur/web.py) et le jeu relève les messages à chaque image.
    """

    def __init__(self, url, jeton):
        self.url = url
        self.jeton = jeton
        self.ping = 0.0
        self._etat = "ferme"
        self.erreur = ""
        self._authentifie = False
        self._prochain_ping = 0.0

    @property
    def etat(self):
        if self._etat in ("connexion", "ouvert"):
            etat, erreur = web.ws_etat()
            if etat == "ouvert" and not self._authentifie:
                self._authentifie = True
                web.ws_envoyer(json.dumps({"t": "auth", "jeton": self.jeton,
                                           "protocole": PROTOCOLE, "version": VERSION}))
            if etat in ("ferme", "erreur") and self._etat != "ferme":
                self.erreur = erreur or "fermee sans raison"
                journaliser(f"coupure : {self.erreur} (ping {self.ping:.0f} ms)")
                etat = "erreur"
            self._etat = etat
        return self._etat

    @etat.setter
    def etat(self, valeur):
        self._etat = valeur

    def ouvrir(self):
        if self.etat in ("connexion", "ouvert"):
            return
        self._etat = "connexion"
        self._authentifie = False
        web.ws_ouvrir(self.url)

    def envoyer(self, message):
        if self.etat == "ouvert":
            web.ws_envoyer(json.dumps(message, separators=(",", ":")))

    def messages(self):
        if self.etat != "ouvert":
            return []
        maintenant = time.monotonic()
        if maintenant >= self._prochain_ping:
            self._prochain_ping = maintenant + 2
            self.envoyer({"t": "ping", "c": maintenant})
        resultat = [json.loads(texte) for texte in web.ws_messages()]
        for message in resultat:
            if message.get("t") == "pong" and message.get("c"):
                self.ping = (time.monotonic() - message["c"]) * 1000
        return resultat

    def fermer(self):
        if self._etat in ("connexion", "ouvert"):
            web.ws_fermer()
        self._etat = "ferme"


class ServiceEnLigne:
    """
    Tout ce qui touche au serveur, côté jeu.
    Attributs : app ; jeton, pseudo, couleur, niveau, xp ; connecte (bool :
    session vérifiée) ; joignable (bool ou None : serveur atteint ?) ;
    temps_reel (TempsReel ou None) ; version_serveur (dict ou None).
    """

    def __init__(self, app):
        self.app = app
        compte = app.donnees.setdefault("compte", {})
        self.jeton = compte.get("jeton", "")
        self.pseudo = compte.get("pseudo", "")
        self.couleur = compte.get("couleur", "cyan")
        self.niveau = compte.get("niveau", 1)
        self.xp = compte.get("xp", 0)
        self.skin = compte.get("skin", "neon")
        self.skins = compte.get("skins", ["neon"])
        self.neons = compte.get("neons", 0)
        self.banniere = compte.get("banniere", "")
        self.bannieres = compte.get("bannieres", [])
        self.elo = compte.get("elo", 1000)
        self.classees = compte.get("classees", 0)
        self.elo_max = compte.get("elo_max", self.elo)
        self.classees_victoires = compte.get("classees_victoires", 0)
        self.classees_recents = compte.get("classees_recents", "")
        self.admin = bool(compte.get("admin", False))
        self.connecte = False
        self.joignable = None
        self.temps_reel = None
        self.version_serveur = None
        self.reponses = queue.Queue()
        self.envoi_en_cours = False
        self._prochaine_verification_version = time.monotonic() + 30
        self.requetes_web = {}          # version navigateur : numéro -> rappel
        # Progression gardée sur le compte : dernière version envoyée (empreinte), envoi en
        # cours, et prochaine vérification (la sauvegarde a-t-elle changé depuis ?).
        self.progression_envoyee = None
        self.envoi_progression = False
        self._prochaine_progression = 0.0

    # --- Adresse ---------------------------------------------------------------

    def adresse(self):
        if config.EST_WEB:
            return web.origine()        # la page est servie par le serveur du jeu
        return adresse_serveur(self.app.reglages)

    def adresse_ws(self):
        adresse = self.adresse()
        if adresse.startswith("https://"):
            return "wss://" + adresse[8:] + "/ws"
        return "ws://" + adresse.split("://", 1)[-1] + "/ws"

    # --- HTTP -------------------------------------------------------------------

    def appeler(self, methode, chemin, corps=None, rappel=None, authentifie=True):
        """
        But : requête HTTP en arrière-plan ; rappel(resultat) sera appelé
        par le fil du jeu, avec resultat = {"ok", "code", "donnees", "erreur"}.
        """
        adresse = self.adresse()
        if not adresse:
            if rappel:
                self.reponses.put((rappel, {"ok": False, "code": 0, "donnees": None,
                                            "erreur": "AUCUN SERVEUR CONFIGURE",
                                            "maintenance": False}))
            return
        jeton = self.jeton if authentifie else ""
        if config.EST_WEB:
            numero = web.requete(methode, adresse + chemin, corps, jeton)
            self.requetes_web[numero] = rappel
            return

        def executer():
            resultat = requete_http(adresse + chemin, methode, corps, jeton)
            self.joignable = resultat["code"] != 0
            if rappel:
                self.reponses.put((rappel, resultat))

        threading.Thread(target=executer, daemon=True).start()

    def traiter(self):
        """But : exécuter les rappels arrivés (appelé à chaque image)."""
        if self.jeton and time.monotonic() >= self._prochaine_progression:
            self._prochaine_progression = time.monotonic() + 20
            self.synchroniser_progression()
        if self.version_serveur is None and time.monotonic() >= self._prochaine_verification_version:
            self._prochaine_verification_version = time.monotonic() + 30
            # Vérification silencieuse : on mémorise la version, sans fenêtre pendant
            # une partie ; l'accès au jeu en ligne proposera la mise à jour.
            self.verifier_version(lambda resultat: None)
        if self.requetes_web:
            for numero, code, texte in web.reponses():
                rappel = self.requetes_web.pop(numero, None)
                resultat = resultat_http(code, texte)
                self.joignable = code != 0
                if rappel:
                    self.reponses.put((rappel, resultat))
        while True:
            try:
                rappel, resultat = self.reponses.get_nowait()
            except queue.Empty:
                return
            try:
                rappel(resultat)
            except Exception as erreur:          # un écran fermé entre-temps, etc.
                print("Rappel réseau :", erreur)

    # --- Compte ------------------------------------------------------------------

    def memoriser(self, donnees):
        """But : garder la session et le profil dans la sauvegarde locale."""
        if donnees.get("jeton"):
            self.jeton = donnees["jeton"]
        self.pseudo = donnees.get("pseudo", self.pseudo)
        self.couleur = donnees.get("couleur", self.couleur)
        self.niveau = donnees.get("niveau", self.niveau)
        self.xp = donnees.get("xp", self.xp)
        self.skin = donnees.get("skin", self.skin)
        if "skins" in donnees:
            nouveaux = [s for s in donnees["skins"] if s not in self.skins]
            if nouveaux and self.app.donnees.get("compte", {}).get("skins"):
                from reseau.profil import SKINS_PAR_CODE
                for code in nouveaux:
                    if code in SKINS_PAR_CODE:
                        self.app.notifier("NOUVEAU SKIN !", "ROSE", SKINS_PAR_CODE[code]["nom"])
            self.skins = list(donnees["skins"])
        self.neons = donnees.get("neons", self.neons)
        self.banniere = donnees.get("banniere", self.banniere)
        self.bannieres = list(donnees.get("bannieres", self.bannieres))
        self.elo = donnees.get("elo", self.elo)
        self.classees = donnees.get("classees", self.classees)
        self.elo_max = donnees.get("elo_max", getattr(self, "elo_max", self.elo))
        self.classees_victoires = donnees.get("classees_victoires", getattr(self, "classees_victoires", 0))
        self.classees_recents = donnees.get("classees_recents", getattr(self, "classees_recents", ""))
        self.admin = bool(donnees.get("admin", getattr(self, "admin", False)))
        if donnees.get("messages"):
            self.annoncer_messages(donnees["messages"])
        self.connecte = True
        self.app.donnees["compte"] = {"jeton": self.jeton, "pseudo": self.pseudo,
                                      "couleur": self.couleur, "niveau": self.niveau,
                                      "xp": self.xp, "skin": self.skin, "skins": self.skins,
                                      "neons": self.neons, "banniere": self.banniere,
                                      "bannieres": self.bannieres, "elo": self.elo,
                                      "classees": self.classees, "elo_max": self.elo_max,
                                      "classees_victoires": self.classees_victoires,
                                      "classees_recents": self.classees_recents,
                                      "admin": self.admin}
        self.app.enregistrer()

    def synchroniser_progression(self, forcer=False):
        """
        But : garder la progression sur le compte (niveaux, étoiles, records, séries...).
        L'appareil envoie la sienne et reçoit la fusion avec celle du compte (le meilleur des
        deux), qu'il adopte. Rien n'est envoyé si elle n'a pas changé depuis le dernier envoi.
        """
        from jeu import progression
        if not self.jeton or self.envoi_progression or self.protege():
            return
        locale = progression.extraire(self.app.donnees)
        if not forcer and progression.empreinte(locale) == self.progression_envoyee:
            return
        self.envoi_progression = True

        def recu(resultat):
            self.envoi_progression = False
            if not resultat["ok"] or not isinstance(resultat["donnees"], dict):
                return
            if progression.appliquer(self.app.donnees, resultat["donnees"].get("progression", {})):
                self.app.enregistrer()
            self.progression_envoyee = progression.empreinte(progression.extraire(self.app.donnees))
        self.appeler("PUT", "/api/moi/progression", {"progression": locale}, recu)

    def changer_mdp(self, ancien, nouveau, rappel):
        """But : changer son mot de passe (une nouvelle session est donnée par le serveur)."""
        def recu(resultat):
            if resultat["ok"]:
                self.memoriser(resultat["donnees"])
            rappel(resultat)
        self.appeler("PUT", "/api/moi/mdp", {"ancien": ancien, "nouveau": nouveau}, recu)

    def se_connecter(self, pseudo, mdp, inscription, rappel):
        def recu(resultat):
            if resultat["ok"]:
                self.memoriser(resultat["donnees"])
                self.vider_file()
                self.synchroniser_progression(forcer=True)
            rappel(resultat)
        chemin = "/api/inscription" if inscription else "/api/connexion"
        self.appeler("POST", chemin, {"pseudo": pseudo, "mdp": mdp}, recu, authentifie=False)

    def verifier_session(self, rappel=None):
        """But : au démarrage, vérifier que la session enregistrée est valide."""
        if not self.jeton:
            return

        def recu(resultat):
            if resultat["ok"]:
                self.memoriser(resultat["donnees"])
                self.vider_file()
                self.synchroniser_progression(forcer=True)
            elif resultat["code"] == 401:
                self.oublier()
            if rappel:
                rappel(resultat)
        self.appeler("GET", "/api/moi", rappel=recu)

    def oublier(self):
        self.jeton = ""
        self.progression_envoyee = None
        self.connecte = False
        self.skin, self.skins = "neon", ["neon"]
        self.neons, self.banniere, self.bannieres = 0, "", []
        self.admin = False
        self.app.donnees["compte"] = {}
        self.app.enregistrer()

    def se_deconnecter(self):
        self.appeler("POST", "/api/deconnexion")
        if self.temps_reel:
            self.temps_reel.fermer()
            self.temps_reel = None
        self.oublier()

    def changer_couleur(self, couleur, rappel=None):
        def recu(resultat):
            if resultat["ok"]:
                self.memoriser({"couleur": couleur})
            if rappel:
                rappel(resultat)
        self.appeler("PUT", "/api/moi/couleur", {"couleur": couleur}, recu)

    def protege(self):
        """
        But : version de test branchée sur le vrai serveur ? Dans ce cas, aucun score
        n'est envoyé et les parties en ligne sont désactivées (consultation seulement).
        Un serveur de test choisi avec la variable NEON_SERVEUR lève cette protection.
        Sortie : (bool).
        """
        from moteur import config
        return config.EST_TEST and not os.environ.get("NEON_SERVEUR")

    def skin_actif(self):
        """But : skin à afficher pour le joueur local ("neon" sans compte)."""
        return self.skin if self.jeton and self.skin in self.skins else "neon"

    def changer_skin(self, skin, rappel=None):
        def recu(resultat):
            if resultat["ok"]:
                self.memoriser({"skin": skin})
            if rappel:
                rappel(resultat)
        self.skin = skin
        self.appeler("PUT", "/api/moi/skin", {"skin": skin}, recu)

    # --- Boutique (2.0) -------------------------------------------------------------

    def banniere_active(self):
        """But : bannière du joueur local ("" sans compte ou si elle n'est plus possédée)."""
        return self.banniere if self.jeton and self.banniere in self.bannieres else ""

    def changer_banniere(self, banniere, rappel=None):
        def recu(resultat):
            if resultat["ok"]:
                self.memoriser({"banniere": banniere})
            if rappel:
                rappel(resultat)
        self.banniere = banniere
        self.appeler("PUT", "/api/moi/banniere", {"banniere": banniere}, recu)

    def _rappel_profil(self, rappel):
        """Rappel qui garde le nouveau solde (et les objets) renvoyés par le serveur."""
        def recu(resultat):
            if resultat["ok"] and isinstance(resultat["donnees"], dict) \
                    and "neons" in resultat["donnees"]:
                self.memoriser(resultat["donnees"])
            if rappel:
                rappel(resultat)
        return recu

    def charger_boutique(self, rappel):
        self.appeler("GET", "/api/boutique", rappel=self._rappel_profil(rappel))

    def acheter(self, code, rappel):
        self.appeler("POST", "/api/boutique/acheter", {"code": code}, self._rappel_profil(rappel))

    def ouvrir_boite(self, rappel):
        self.appeler("POST", "/api/boutique/boite", {}, self._rappel_profil(rappel))

    # --- Scores ------------------------------------------------------------------

    def ajouter_rapports(self, rapports):
        """
        But : mettre des parties solo dans la file d'envoi (sauvegardée), puis
        tenter l'envoi si on est connecté.
        """
        if not self.jeton:
            return
        if self.protege():
            if not getattr(self, "test_annonce", False):
                self.test_annonce = True
                self.app.notifier("VERSION DE TEST", "AMBRE", "SCORES NON ENVOYES")
            return
        file = self.app.donnees.setdefault("a_envoyer", [])
        for rapport in rapports:
            file.append({**rapport, "uid": uuid.uuid4().hex, "joue_le": time.time()})
        del file[:-200]                       # au plus 200 parties en attente
        self.app.enregistrer()
        self.vider_file()

    def vider_file(self):
        """But : envoyer les parties en attente ; les succès obtenus sont annoncés."""
        file = self.app.donnees.get("a_envoyer", [])
        if not file or not self.jeton or self.envoi_en_cours or self.protege():
            return
        lot = list(file[:50])
        self.envoi_en_cours = True

        def recu(resultat):
            self.envoi_en_cours = False
            if not resultat["ok"]:
                return
            envoyes = {r["uid"] for r in lot}
            self.app.donnees["a_envoyer"] = [r for r in self.app.donnees.get("a_envoyer", [])
                                             if r["uid"] not in envoyes]
            donnees = resultat["donnees"]
            ancien_niveau = self.niveau
            self.memoriser(donnees)
            for retour in donnees.get("resultats", []):
                self.annoncer_gains(retour)
            if self.niveau > ancien_niveau:
                self.app.notifier(f"RANG {self.niveau} !", "AMBRE")
        self.appeler("POST", "/api/parties", {"rapports": lot}, recu)

    def annoncer_messages(self, messages):
        """But : récompenses du serveur (top 3, fin de saison) : notification puis « lu »."""
        deja = getattr(self, "messages_vus", set())
        nouveaux = [m for m in messages if m.get("id") not in deja]
        for message in nouveaux:
            self.app.notifier(message.get("titre", ""), "OR", message.get("texte", ""))
            deja.add(message.get("id"))
        self.messages_vus = deja
        if nouveaux:
            self.appeler("POST", "/api/moi/messages", {"ids": [m["id"] for m in nouveaux]})

    def annoncer_gains(self, gains):
        """But : notifications des succès débloqués (réponse du serveur)."""
        if not gains:
            return
        if gains.get("neons_gagnes"):
            from reseau.boutique import MONNAIE
            lignes = gains.get("detail_neons", [])
            detail = (f"{lignes[0][0]} +{lignes[0][1]}" if lignes else "") \
                + (f" (+{len(lignes) - 1} AUTRES)" if len(lignes) > 1 else "")
            self.app.notifier(f"+{gains['neons_gagnes']} {MONNAIE}", "CYAN", detail)
        if "neons" in gains:
            self.neons = gains["neons"]
        if "elo" in gains:
            self.elo, self.classees = gains["elo"], gains.get("classees", self.classees)
            self.elo_max = max(getattr(self, "elo_max", 0), self.elo)
            self.classees_victoires = getattr(self, "classees_victoires", 0) + int(bool(gains.get("victoire_classee")))
            self.classees_recents = (getattr(self, "classees_recents", "") + ("V" if gains.get("victoire_classee") else "D"))[-10:]
        for succes in gains.get("nouveaux_succes", []):
            # Paliers : la notification prend la couleur du palier (argent, or, platine).
            palier = succes["code"].rsplit("_", 1)[-1]
            couleur = {"argent": "BLANC", "or": "OR", "platine": "CYAN"}.get(palier, "OR")
            titre = "PALIER : " if palier in ("argent", "or", "platine") else "SUCCES : "
            self.app.notifier(titre + succes["nom"], couleur, succes["description"])

    # --- Temps réel ----------------------------------------------------------------

    def ouvrir_temps_reel(self):
        """But : ouvrir (ou rouvrir) la connexion WebSocket. Sortie : TempsReel."""
        if self.temps_reel is None or self.temps_reel.etat in ("ferme", "erreur"):
            classe = TempsReelWeb if config.EST_WEB else TempsReel
            self.temps_reel = classe(self.adresse_ws(), self.jeton)
            self.temps_reel.ouvrir()
        return self.temps_reel

    # --- Mise à jour ------------------------------------------------------------------

    def verifier_version(self, rappel):
        self._prochaine_verification_version = time.monotonic() + 30
        def recu(resultat):
            if resultat["ok"]:
                self.version_serveur = resultat["donnees"]
            rappel(resultat)
        self.appeler("GET", "/api/version", rappel=recu, authentifie=False)

    def mise_a_jour_requise(self):
        """But : trouver une mise a jour disponible. Entree(s) : aucune. Sortie : dict ou None."""
        from moteur import config
        if config.EST_TEST or self.version_serveur is None:
            return None
        from reseau.mise_a_jour import version_disponible
        return version_disponible(self.version_serveur)


def journaliser(texte):
    """
    But : noter un incident réseau (date + texte) dans reseau.log, à côté de la
    sauvegarde, pour comprendre les coupures. Le fichier ne dépasse pas 50 Ko.
    """
    try:
        from moteur import config
        chemin = os.path.join(config.DOSSIER_DATA, "reseau.log")
        if os.path.exists(chemin) and os.path.getsize(chemin) > 50000:
            os.replace(chemin, chemin + ".1")
        with open(chemin, "a", encoding="utf-8") as fichier:
            fichier.write(time.strftime("%Y-%m-%d %H:%M:%S ") + texte + "\n")
    except OSError:
        pass


def resultat_http(code, texte):
    """
    But : mettre la réponse d'une requête faite par le navigateur au même format
    que requete_http. Entrées : code (int, 0 = injoignable) ; texte (str) : corps.
    """
    if code == 0:
        return {"ok": False, "code": 0, "donnees": None,
                "erreur": "SERVEUR EN MAINTENANCE", "maintenance": True}
    try:
        donnees = json.loads(texte) if texte else {}
    except ValueError:
        donnees = None
    if 200 <= code < 300:
        if donnees is None:
            return {"ok": False, "code": code, "donnees": None,
                    "erreur": "REPONSE INVALIDE", "maintenance": False}
        return {"ok": True, "code": code, "donnees": donnees, "erreur": "", "maintenance": False}
    maintenance = code in (502, 503, 504)
    detail = donnees.get("detail", "") if isinstance(donnees, dict) else ""
    return {"ok": False, "code": code, "donnees": None,
            "erreur": "SERVEUR EN MAINTENANCE" if maintenance else str(detail or f"ERREUR {code}"),
            "maintenance": maintenance}


def requete_http(url, methode="GET", corps=None, jeton="", delai=8):
    """
    But : requête HTTP JSON (bloquante, à appeler dans un fil).
    Sortie : (dict) {"ok", "code", "donnees", "erreur"}.
    """
    donnees = json.dumps(corps).encode("utf-8") if corps is not None else None
    entetes = {"Content-Type": "application/json", "User-Agent": f"NeonBreaker/{VERSION}"}
    if jeton:
        entetes["Authorization"] = "Bearer " + jeton
    requete = urllib.request.Request(url, data=donnees, method=methode, headers=entetes)
    options = {"timeout": delai}
    if url.startswith("https://"):
        options["context"] = contexte_ssl()
    try:
        with urllib.request.urlopen(requete, **options) as reponse:
            texte = reponse.read().decode("utf-8")
            return {"ok": True, "code": reponse.status,
                    "donnees": json.loads(texte) if texte else {}, "erreur": "", "maintenance": False}
    except urllib.error.HTTPError as erreur:
        try:
            detail = json.loads(erreur.read().decode("utf-8")).get("detail", "")
        except (ValueError, AttributeError):
            detail = ""
        maintenance = erreur.code in (502, 503, 504)
        return {"ok": False, "code": erreur.code, "donnees": None,
                "erreur": "SERVEUR EN MAINTENANCE" if maintenance else str(detail or f"ERREUR {erreur.code}"),
                "maintenance": maintenance}
    except (urllib.error.URLError, OSError, ValueError) as erreur:
        maintenance = not isinstance(erreur, ValueError)
        return {"ok": False, "code": 0, "donnees": None,
                "erreur": "SERVEUR EN MAINTENANCE" if maintenance else "REPONSE INVALIDE",
                "maintenance": maintenance}
