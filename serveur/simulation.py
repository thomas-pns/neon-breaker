# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Faire tourner une partie en ligne sur le serveur, sans affichage, avec
    les mêmes modes que le jeu (Coop, Duel, Course).

    Le mode croit parler à une Application normale : on lui fournit une
    « application serveur » dont l'audio, le filtre CRT et les effets
    spéciaux ENREGISTRENT les appels au lieu de produire des sons et des
    particules. Ce journal est envoyé aux clients, qui rejouent les effets
    chez eux. Les commandes arrivent du réseau (EntreesReseau).

    Chaque joueur pilote sa raquette en local (réponse immédiate) et envoie
    sa position ; le serveur l'applique, puis simule tout le reste.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import os
import types

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from moteur import config                             # noqa: E402
from moteur.effets import GestionnaireEffets          # noqa: E402
from reseau.instantane import capturer               # noqa: E402

ACTIONS_JOUEUR = {"action", "changer", "activer", "overdrive", "pouvoir1", "pouvoir2",
                  "pouvoir3", "valider"}


def _json(valeur):
    """Convertit tuples / Rect en listes pour le journal."""
    if hasattr(valeur, "x") and hasattr(valeur, "w") and hasattr(valeur, "h"):
        return [valeur.x, valeur.y, valeur.w, valeur.h]
    if isinstance(valeur, (tuple, list)):
        return [_json(v) for v in valeur]
    if isinstance(valeur, float):
        return round(valeur, 2)
    return valeur


class EffetsEnregistreur(GestionnaireEffets):
    """
    Effets spéciaux côté serveur : la partie visuelle est notée dans un
    journal (pour les clients) ; le gel et le ralenti, qui changent le
    rythme du jeu, sont appliqués pour de vrai.
    """

    VISUELS = ("explosion", "debris_brique", "etincelles", "texte", "onde", "secouer",
               "eclair")

    def __init__(self):
        super().__init__()
        self.journal = []
        for nom in self.VISUELS:
            setattr(self, nom, self._enregistreur(nom))

    def _enregistreur(self, nom):
        def enregistrer(*args, **kwargs):
            self.journal.append([nom, _json(list(args)), _json(kwargs)])
        return enregistrer

    def geler(self, duree):
        super().geler(duree)
        self.journal.append(["geler", [round(duree, 3)], {}])

    def ralentir(self, facteur, duree):
        super().ralentir(facteur, duree)
        self.journal.append(["ralentir", [facteur, duree], {}])

    def trainee(self, *args, **kwargs):
        """Les traînées sont calculées par les clients eux-mêmes."""


class AudioEnregistreur:
    def __init__(self, journal):
        self.journal = journal
        self.volume_effets = 1.0

    def jouer(self, nom, volume=1.0):
        self.journal.append(["son", [nom, round(volume, 2)], {}])

    def jouer_brique(self, combo):
        self.journal.append(["son_brique", [combo], {}])


class CrtEnregistreur:
    def __init__(self, journal):
        self.journal = journal

    def declencher_aberration(self, force=1.0):
        self.journal.append(["crt", [round(force, 2)], {}])


class FondServeur:
    """Ce que les modes règlent sur le fond animé : transmis aux clients."""

    def __init__(self):
        self.monde = 1
        self.progression = 0.0
        self.vitesse_cible = 0.8

    def changer_monde(self, monde):
        self.monde = monde


class EntreesReseau:
    """
    Commandes des joueurs reçues par le réseau, avec la même interface que
    moteur.entrees.Entrees (profils "j1" et "j2").
    """

    def __init__(self):
        self.appuis = {}            # profil -> set d'actions de cette image
        self.souris = (0, 0)
        self.souris_bougee = False
        self.clics = set()
        self.molette = 0
        self.texte = ""
        self.forcees = set()

    def recevoir(self, profil, actions):
        """But : ajouter les actions reçues d'un joueur (traitées à l'image suivante)."""
        self.appuis.setdefault(profil, set()).update(a for a in actions if a in ACTIONS_JOUEUR)

    def debut_image(self):
        self.appuis.clear()

    def vient_d_appuyer(self, action, profil="menu"):
        if profil == "menu":
            # « Valider » (bilan de niveau) : n'importe quel joueur.
            return any(action in a or (action == "valider" and "action" in a)
                       for a in self.appuis.values())
        return action in self.appuis.get(profil, ())

    def est_maintenue(self, action, profil="menu"):
        return False

    def direction(self, profil):
        return 0


class AppServeur:
    """Application minimale fournie aux modes côté serveur."""

    def __init__(self):
        self.effets_journal = []
        self.audio = AudioEnregistreur(self.effets_journal)
        self.crt = CrtEnregistreur(self.effets_journal)
        self.fond = FondServeur()
        self.entrees = EntreesReseau()
        self.donnees = {"meilleurs": {}, "classements": {}, "progression": {}}
        self.reglages = {"particules": "bas"}
        self.transitions = []        # [temps restant, action]

    def enregistrer(self):
        """Pas de sauvegarde locale sur le serveur."""

    def meilleur_score(self, mode):
        return 0

    def lancer_transition(self, action):
        """Les clients jouent le balayage VHS ; l'action a lieu à mi-chemin."""
        self.effets_journal.append(["transition", [], {}])
        self.transitions.append([0.22, action])

    def mettre_a_jour_transitions(self, dt):
        for transition in list(self.transitions):
            transition[0] -= dt
            if transition[0] <= 0:
                self.transitions.remove(transition)
                transition[1]()


def maj_raquette_distante(raquette, dt, direction):
    """
    Remplace Raquette.mettre_a_jour côté serveur : la position vient du
    joueur ; on ne gère que les minuteries et la largeur animée.
    """
    raquette.temps += dt
    if raquette.joueur is not None:
        cible = raquette.largeur_base * raquette.joueur.facteur_largeur()
        raquette.largeur += (cible - raquette.largeur) * min(1.0, dt * 8)
    raquette.etourdie = max(0.0, raquette.etourdie - dt)
    raquette.gelee = max(0.0, raquette.gelee - dt)
    raquette.ecrasement = max(0.0, raquette.ecrasement - dt * 6)
    position = getattr(raquette, "position_distante", None)
    if position is not None and raquette.etourdie <= 0 and raquette.gelee <= 0:
        raquette.x, raquette.vx = position
    else:
        raquette.vx = 0.0
    raquette.contraindre()


def creer_mode(code, app, effets, niveau=0):
    """But : instancier le mode en ligne demandé ("coop", "duel", "course")."""
    from jeu.modes.campagne import ModeCoop
    from jeu.modes.duel import ModeDuel
    from jeu.modes.course import ModeCourse
    if code == "coop":
        return ModeCoop(app, effets, niveau)
    if code == "duel":
        return ModeDuel(app, effets)
    return ModeCourse(app, effets)


class Simulation:
    """
    Une partie en ligne : mode + application serveur + commandes.
    Attributs : app (AppServeur), effets (EffetsEnregistreur), mode,
    pseudos (list : pseudo du joueur 1 puis du joueur 2), signatures.
    """

    def __init__(self, code, pseudos, niveau=0):
        self.code = code
        self.app = AppServeur()
        self.effets = EffetsEnregistreur()
        self.effets.journal = self.app.effets_journal
        self.mode = creer_mode(code, self.app, self.effets, niveau)
        self.mode.en_ligne = True                    # pseudos au lieu de « J1 / J2 »
        self.pseudos = list(pseudos)
        for joueur, pseudo in zip(self.mode.joueurs, self.pseudos):
            joueur.nom = pseudo
        self.signatures = {}
        self.accumulateur = 0.0
        self.rebonds = {"acceptes": 0, "refuses": 0}   # rebonds annoncés par les joueurs
        self.preparer_raquettes()

    def preparer_raquettes(self):
        """Branche le pilotage distant sur toute raquette (nouveaux terrains compris)."""
        for terrain in self.mode.terrains:
            for raquette in terrain.raquettes:
                if not getattr(raquette, "distante", False):
                    raquette.distante = True
                    raquette.mettre_a_jour = types.MethodType(maj_raquette_distante, raquette)

    def profil(self, numero):
        return "j1" if numero == 1 else "j2"

    def recevoir_commande(self, numero, message):
        """
        But : appliquer un message de commandes d'un joueur.
        Entrées : numero (int : 1 ou 2) ; message (dict) avec "x", "vx"
                  (position de sa raquette) et "a" (actions appuyées).
        """
        joueur = self.mode.joueurs[numero - 1]
        if message.get("rc") and joueur.raquette is not None:
            # Jeu récent : il annonce lui-même les rebonds sur sa raquette.
            ping = min(400.0, max(0.0, float(message.get("p", 0) or 0)))
            joueur.raquette.rebond_client = True
            joueur.raquette.delai_rebond = min(0.45, 0.12 + ping / 1000)
        if joueur.raquette is not None and "x" in message:
            try:
                x, vx = float(message["x"]), float(message.get("vx", 0))
                # Compensation du trajet réseau : la position date d'un demi-ping.
                retard = min(0.15, max(0.0, float(message.get("p", 0)) / 2000))
                joueur.raquette.position_distante = (x + vx * retard, vx)
            except (TypeError, ValueError):
                pass
        self.app.entrees.recevoir(self.profil(numero), message.get("a", []))

    def recevoir_rebond(self, numero, message):
        """
        But : rebond sur sa raquette annoncé par un joueur. Accepté s'il est
        plausible (balle qui arrive sur cette raquette, position et vitesse proches).
        Entrées : numero (int) ; message (dict) : n (identifiant de la balle), x, y,
                  vx, vy (balle juste après le rebond), rx (raquette), p (ping en ms).
        Sortie : (bool) True si le rebond a été appliqué.
        """
        joueur = self.mode.joueurs[numero - 1]
        raquette, terrain = joueur.raquette, joueur.terrain
        if raquette is None or terrain is None or not getattr(raquette, "rebond_client", False):
            return False
        try:
            n = int(message["n"])
            x, y, vx, vy = (float(message[c]) for c in ("x", "y", "vx", "vy"))
            rx = float(message.get("rx", raquette.x))
            ping = min(400.0, max(0.0, float(message.get("p", 0) or 0)))
        except (KeyError, TypeError, ValueError):
            return False
        balle = next((b for b in terrain.balles if getattr(b, "nid", None) == n), None)
        if balle is None or balle.collee:
            return False
        arrive = balle.vy * raquette.sens < 0 or getattr(balle, "sursis", None) is not None
        proche = abs(balle.x - x) < 240 and abs(balle.y - raquette.face_y()) < 200 \
            and abs(y - raquette.face_y()) < 60
        vitesse = balle.vitesse()
        coherente = vy * raquette.sens > 0 and 0.5 * vitesse <= (vx * vx + vy * vy) ** 0.5 \
            <= 1.6 * vitesse + 1
        if not (arrive and proche and coherente):
            self.rebonds["refuses"] += 1
            return False
        self.rebonds["acceptes"] += 1
        raquette.x = rx
        raquette.contraindre()
        terrain.rebond_client(balle, raquette, x, y, vx, vy, avance=ping / 2000)
        return True

    def avancer(self, dt):
        """
        But : une image de jeu (60 par seconde).
        Entrée : dt (float). Sortie : aucune.
        """
        effets = self.effets
        effets.mettre_a_jour(dt)
        dt_jeu = dt * effets.facteur_temps()
        self.accumulateur += dt_jeu
        pas = 0
        while self.accumulateur >= config.PAS_PHYSIQUE and pas < config.PAS_MAX_PAR_IMAGE:
            self.mode.pas_physique(config.PAS_PHYSIQUE)
            self.accumulateur -= config.PAS_PHYSIQUE
            pas += 1
        self.mode.mettre_a_jour(dt, dt_jeu)
        self.app.entrees.debut_image()
        self.app.mettre_a_jour_transitions(dt)
        self.preparer_raquettes()

    def instantane(self, forcer=False):
        """But : état à envoyer + effets survenus depuis le dernier envoi."""
        donnees = capturer(self.mode, self.app.fond, self.signatures, forcer)
        donnees["fx"] = list(self.app.effets_journal)
        self.app.effets_journal.clear()
        return donnees

    def resultat(self):
        return self.mode.resultat

