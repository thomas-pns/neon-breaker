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

ToDo List:
    Manettes, commandes configurables.
"""

import pygame

from moteur import config


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

    def debut_image(self):
        """
        But : oublier les appuis de l'image précédente.
        Entrée : aucune. Sortie : aucune.
        """
        self.appuis.clear()
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
            if evenement.unicode and evenement.unicode.isprintable():
                self.texte += evenement.unicode
        elif evenement.type == pygame.KEYUP:
            self.tenues.discard(getattr(evenement, "scancode", None))
        elif evenement.type in (pygame.WINDOWFOCUSLOST, pygame.ACTIVEEVENT):
            if getattr(evenement, "gain", 0) == 0:
                self.tenues.clear()
        elif evenement.type == pygame.MOUSEMOTION:
            self.souris = self.ecran.vers_interne(evenement.pos)
            self.souris_bougee = True
        elif evenement.type == pygame.MOUSEBUTTONDOWN:
            self.souris = self.ecran.vers_interne(evenement.pos)
            self.clics.add(evenement.button)
        elif evenement.type == pygame.MOUSEWHEEL:
            self.molette += evenement.y

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
        return any(code in self.appuis for code in codes)

    def est_maintenue(self, action, profil="menu"):
        """
        But : savoir si une touche de l'action est tenue enfoncée.
        Entrées : action (str), profil (str). Sortie : (bool).
        """
        if (profil, action) in self.forcees:
            return True
        codes = self.touches.get(profil, {}).get(action, ())
        return any(code in self.tenues for code in codes)

    def direction(self, profil):
        """
        But : direction horizontale demandée (-1, 0 ou +1).
        Entrée : profil (str). Sortie : (int).
        """
        return (int(self.est_maintenue("droite", profil))
                - int(self.est_maintenue("gauche", profil)))
