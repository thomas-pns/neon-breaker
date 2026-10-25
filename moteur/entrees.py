# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Traduire clavier et souris en « actions » de jeu, par profil :
    "menu" (navigation), "solo", "j1" et "j2" (deux joueurs sur le même
    clavier). On lit les codes PHYSIQUES des touches (scancodes) : les
    commandes tombent au même endroit en AZERTY et en QWERTY.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

    Manettes (2.0) : boutons et sticks deviennent des noms (« a », « stick_gauche »...)
    rangés à part, avec le numéro de la manette (0 pour J1, 1 pour J2).
"""

import pygame

from moteur import config

try:
    from pygame._sdl2 import controller as _manettes
except ImportError:                       # pygame trop ancien : pas de manette
    _manettes = None

BOUTONS = {}
if _manettes is not None:
    BOUTONS = {pygame.CONTROLLER_BUTTON_A: "a", pygame.CONTROLLER_BUTTON_B: "b",
               pygame.CONTROLLER_BUTTON_X: "x", pygame.CONTROLLER_BUTTON_Y: "y",
               pygame.CONTROLLER_BUTTON_START: "start", pygame.CONTROLLER_BUTTON_BACK: "back",
               pygame.CONTROLLER_BUTTON_LEFTSHOULDER: "lb",
               pygame.CONTROLLER_BUTTON_RIGHTSHOULDER: "rb",
               pygame.CONTROLLER_BUTTON_DPAD_UP: "haut", pygame.CONTROLLER_BUTTON_DPAD_DOWN: "bas",
               pygame.CONTROLLER_BUTTON_DPAD_LEFT: "gauche",
               pygame.CONTROLLER_BUTTON_DPAD_RIGHT: "droite"}
SEUIL, SEUIL_RELACHE = 0.5, 0.35           # sticks et gâchettes (avec hystérésis)


class Entrees:
    """
    État des commandes pour l'image courante.
    Attributs :
        touches (dict) : profil -> action -> liste de scancodes.
        tenues (set) : scancodes actuellement enfoncés.
        appuis (set) : scancodes enfoncés pendant cette image.
        souris (tuple) : position de la souris en coordonnées internes.
        souris_bougee (bool), clics (set de boutons), molette (int).
        texte (str) : caractères tapés pendant l'image (saisie du nom).
    """

    def __init__(self, ecran, touches=None):
        self.ecran = ecran
        self.touches = touches or config.TOUCHES
        self.tenues = set()
        self.appuis = set()
        self.forcees = set()          # (profil, action) injectées (tests, bots)
        self.souris = (config.LARGEUR / 2, config.HAUTEUR / 2)
        self.souris_bougee = False
        self.clics = set()
        self.molette = 0
        self.texte = ""
        self.manettes = {}            # instance -> (numéro 0/1/..., objet Controller)
        self.tenues_manette = set()   # (numéro, nom)
        self.appuis_manette = set()
        self.derniere_touche = None   # (scancode, nom) : pour reconfigurer une commande
        if _manettes is not None:
            try:
                _manettes.init()
            except pygame.error:
                pass

    def debut_image(self):
        """
        But : oublier les appuis de l'image précédente.
        Entrée : aucune. Sortie : aucune.
        """
        self.appuis.clear()
        self.appuis_manette.clear()
        self.derniere_touche = None
        self.forcees.clear()
        self.clics.clear()
        self.souris_bougee = False
        self.molette = 0
        self.texte = ""

    def traiter(self, evenement):
        """
        But : prendre en compte un événement pygame.
        Entrée : evenement (pygame.event.Event). Sortie : aucune.
        """
        if evenement.type == pygame.KEYDOWN:
            code = getattr(evenement, "scancode", None)
            if code is not None:
                self.tenues.add(code)
                self.appuis.add(code)
                self.derniere_touche = (code, pygame.key.name(evenement.key).upper())
            if evenement.unicode and evenement.unicode.isprintable():
                self.texte += evenement.unicode
        elif evenement.type == pygame.KEYUP:
            self.tenues.discard(getattr(evenement, "scancode", None))
        elif evenement.type in (pygame.WINDOWFOCUSLOST, pygame.ACTIVEEVENT):
            if getattr(evenement, "gain", 0) == 0:
                self.tenues.clear()
                self.tenues_manette.clear()
        elif evenement.type == pygame.MOUSEMOTION:
            self.souris = self.ecran.vers_interne(evenement.pos)
            self.souris_bougee = True
        elif evenement.type == pygame.MOUSEBUTTONDOWN:
            self.souris = self.ecran.vers_interne(evenement.pos)
            self.clics.add(evenement.button)
        elif evenement.type == pygame.MOUSEWHEEL:
            self.molette += evenement.y
        elif _manettes is not None:
            self._traiter_manette(evenement)

    # --- Manettes -------------------------------------------------------------------

    def _traiter_manette(self, evenement):
        if evenement.type == pygame.CONTROLLERDEVICEADDED:
            try:
                manette = _manettes.Controller(evenement.device_index)
                instance = manette.as_joystick().get_instance_id()
            except (pygame.error, AttributeError):
                return
            pris = {numero for numero, _ in self.manettes.values()}
            numero = next(n for n in range(8) if n not in pris)
            self.manettes[instance] = (numero, manette)
        elif evenement.type == pygame.CONTROLLERDEVICEREMOVED:
            numero, _ = self.manettes.pop(getattr(evenement, "instance_id", -1), (None, None))
            self.tenues_manette = {t for t in self.tenues_manette if t[0] != numero}
        elif evenement.type in (pygame.CONTROLLERBUTTONDOWN, pygame.CONTROLLERBUTTONUP):
            numero = self._numero(evenement)
            nom = BOUTONS.get(evenement.button)
            if numero is None or nom is None:
                return
            if evenement.type == pygame.CONTROLLERBUTTONDOWN:
                self._appuyer_manette(numero, nom)
            else:
                self.tenues_manette.discard((numero, nom))
        elif evenement.type == pygame.CONTROLLERAXISMOTION:
            numero = self._numero(evenement)
            if numero is None:
                return
            valeur = evenement.value / 32767
            axes = {pygame.CONTROLLER_AXIS_LEFTX: ("stick_gauche", "stick_droite"),
                    pygame.CONTROLLER_AXIS_LEFTY: ("stick_haut", "stick_bas"),
                    pygame.CONTROLLER_AXIS_TRIGGERLEFT: (None, "lt"),
                    pygame.CONTROLLER_AXIS_TRIGGERRIGHT: (None, "rt")}
            if evenement.axis in axes:
                negatif, positif = axes[evenement.axis]
                for nom, pousse in ((negatif, -valeur), (positif, valeur)):
                    if nom is None:
                        continue
                    if pousse > SEUIL:
                        self._appuyer_manette(numero, nom)
                    elif pousse < SEUIL_RELACHE:
                        self.tenues_manette.discard((numero, nom))

    def _numero(self, evenement):
        entree = self.manettes.get(getattr(evenement, "instance_id", -1))
        return entree[0] if entree else None

    def _appuyer_manette(self, numero, nom):
        if (numero, nom) not in self.tenues_manette:
            self.appuis_manette.add((numero, nom))
        self.tenues_manette.add((numero, nom))

    def _noms_manette(self, action, profil):
        """But : (numéros de manette acceptés, noms de boutons) d'une action."""
        table = config.MANETTE["menu" if profil == "menu" else "jeu"]
        numeros = {"j1": (0,), "j2": (1,)}.get(profil)
        return numeros, table.get(action, ())

    def _manette(self, action, profil, ensemble):
        numeros, noms = self._noms_manette(action, profil)
        return any(nom in noms and (numeros is None or numero in numeros)
                   for numero, nom in ensemble)

    def manette_branchee(self):
        """But : au moins une manette est branchée ? Sortie : (bool)."""
        return bool(self.manettes)

    # --- Commandes personnalisées -----------------------------------------------------

    def appliquer_perso(self, perso):
        """
        But : remplacer les touches par défaut par celles choisies dans OPTIONS.
        Entrée : perso (dict) profil -> action -> {"code", "nom"}.
        """
        self.touches = {profil: dict(actions) for profil, actions in config.TOUCHES.items()}
        for profil, actions in (perso or {}).items():
            for action, choix in actions.items():
                if profil in self.touches and action in self.touches[profil]:
                    self.touches[profil][action] = [int(choix["code"])]

    def forcer(self, action, profil="menu"):
        """
        But : simuler l'appui d'une action (bots de test, démo).
        Entrées : action (str), profil (str). Sortie : aucune.
        """
        self.forcees.add((profil, action))

    def vient_d_appuyer(self, action, profil="menu"):
        """
        But : savoir si une action vient d'être déclenchée.
        Entrées : action (str), profil (str). Sortie : (bool).
        """
        if (profil, action) in self.forcees:
            return True
        codes = self.touches.get(profil, {}).get(action, ())
        return any(code in self.appuis for code in codes) \
            or (bool(self.appuis_manette) and self._manette(action, profil, self.appuis_manette))

    def est_maintenue(self, action, profil="menu"):
        """
        But : savoir si une touche de l'action est tenue enfoncée.
        Entrées : action (str), profil (str). Sortie : (bool).
        """
        if (profil, action) in self.forcees:
            return True
        codes = self.touches.get(profil, {}).get(action, ())
        return any(code in self.tenues for code in codes) \
            or (bool(self.tenues_manette) and self._manette(action, profil, self.tenues_manette))

    def direction(self, profil):
        """
        But : direction horizontale demandée (-1, 0 ou +1).
        Entrée : profil (str). Sortie : (int).
        """
        return (int(self.est_maintenue("droite", profil))
                - int(self.est_maintenue("gauche", profil)))


def nom_commande(perso, profil, action):
    """But : nom de la touche d'une action (personnalisée ou par défaut). Sortie : (str)."""
    choix = (perso or {}).get(profil, {}).get(action)
    if choix:
        return str(choix.get("nom", "?"))[:8]
    return next((defaut for code, _, defaut in config.COMMANDES.get(profil, []) if code == action), "?")


def libelles_touches(app, profil):
    """
    But : lignes (touche, rôle) du pense-bête des commandes, à jour des touches
    choisies dans OPTIONS, ou celles de la manette si une manette est branchée (solo).
    Sortie : (list de (str, str)).
    """
    entrees = getattr(app, "entrees", None)
    if profil == "solo" and entrees is not None and entrees.manette_branchee():
        return list(config.AIDE_MANETTE)
    perso = (getattr(app, "reglages", None) or {}).get("touches", {})
    if not perso.get(profil):
        return list(config.AIDE_TOUCHES[profil])
    nom = lambda action: nom_commande(perso, profil, action)  # noqa: E731
    lignes = [(f"{nom('gauche')} {nom('droite')}", "BOUGER")]
    if profil == "solo":
        lignes.append(("SOURIS", "BOUGER"))
    lignes.append((nom("action"), "LANCER"))
    if profil == "solo":
        lignes.append((f"{nom('pouvoir1')} {nom('pouvoir2')} {nom('pouvoir3')}", "POUVOIRS"))
    lignes += [(nom("changer"), "CHOISIR"), (nom("activer"), "POUVOIR"),
               (nom("overdrive"), "OVERDRIVE")]
    if profil == "solo":
        lignes.append(("ECHAP", "PAUSE"))
    return lignes
