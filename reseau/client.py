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
import ssl
import threading
import time
import urllib.error
import urllib.request
import uuid

from moteur.version import PROTOCOLE, VERSION, adresse_serveur

LATENCE = float(os.environ.get("NEON_LATENCE_MS", "0")) / 1000
GIGUE = float(os.environ.get("NEON_GIGUE_MS", "0")) / 1000      # tests : réseau irrégulier


def contexte_ssl():
    """Certificats fournis par certifi (indispensable dans l'application macOS)."""
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
            self.erreur = str(erreur)[:80]
        finally:
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
            await asyncio.wait(taches, return_when=asyncio.FIRST_COMPLETED)
            for tache in taches:
                tache.cancel()

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
        self.connecte = False
        self.joignable = None
        self.temps_reel = None
        self.version_serveur = None
        self.reponses = queue.Queue()
        self.envoi_en_cours = False
        self._prochaine_verification_version = time.monotonic() + 30

    # --- Adresse ---------------------------------------------------------------

    def adresse(self):
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

        def executer():
            resultat = requete_http(adresse + chemin, methode, corps, jeton)
            self.joignable = resultat["code"] != 0
            if rappel:
                self.reponses.put((rappel, resultat))

        threading.Thread(target=executer, daemon=True).start()

    def traiter(self):
        """But : exécuter les rappels arrivés (appelé à chaque image)."""
        if self.version_serveur is None and time.monotonic() >= self._prochaine_verification_version:
            self._prochaine_verification_version = time.monotonic() + 30
            # Vérification silencieuse : on mémorise la version, sans fenêtre pendant
            # une partie ; l'accès au jeu en ligne proposera la mise à jour.
            self.verifier_version(lambda resultat: None)
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
        self.connecte = True
        self.app.donnees["compte"] = {"jeton": self.jeton, "pseudo": self.pseudo,
                                      "couleur": self.couleur, "niveau": self.niveau,
                                      "xp": self.xp, "skin": self.skin, "skins": self.skins}
        self.app.enregistrer()

    def se_connecter(self, pseudo, mdp, inscription, rappel):
        def recu(resultat):
            if resultat["ok"]:
                self.memoriser(resultat["donnees"])
                self.vider_file()
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
            elif resultat["code"] == 401:
                self.oublier()
            if rappel:
                rappel(resultat)
        self.appeler("GET", "/api/moi", rappel=recu)

    def oublier(self):
        self.jeton = ""
        self.connecte = False
        self.skin, self.skins = "neon", ["neon"]
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

    def annoncer_gains(self, gains):
        """But : notifications des succès débloqués (réponse du serveur)."""
        if not gains:
            return
        for succes in gains.get("nouveaux_succes", []):
            self.app.notifier("SUCCES : " + succes["nom"], "OR", succes["description"])

    # --- Temps réel ----------------------------------------------------------------

    def ouvrir_temps_reel(self):
        """But : ouvrir (ou rouvrir) la connexion WebSocket. Sortie : TempsReel."""
        if self.temps_reel is None or self.temps_reel.etat in ("ferme", "erreur"):
            self.temps_reel = TempsReel(self.adresse_ws(), self.jeton)
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
