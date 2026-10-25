# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Classe mère de tous les écrans (titre, jeu, pause, fin...) et petit
    menu vertical réutilisable avec sélection au clavier et à la souris.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

    Une option peut avoir une 3e valeur, fonction(sens) appelée par les
    flèches gauche / droite (curseurs de volume du menu OPTIONS).
"""

import math

import pygame

from moteur.police_pixel import dessiner_texte, taille_texte


class EcranBase:
    """
    Écran générique.
    Attributs :
        app (Application) : accès à l'écran, aux entrées, à l'audio.
        transparent (bool) : True si l'écran du dessous reste visible.
        dessous (EcranBase ou None) : écran situé sous celui-ci dans la pile.
        temps (float) : secondes depuis l'entrée dans l'écran.
    """

    transparent = False

    def __init__(self, app):
        self.app = app
        self.dessous = None
        self.temps = 0.0

    def entrer(self):
        """But : appelé quand l'écran arrive au sommet de la pile."""

    def quitter(self):
        """But : appelé quand l'écran est retiré de la pile."""

    def reprendre(self):
        """But : appelé quand l'écran redevient le sommet (après une pause)."""

    def mettre_a_jour(self, dt):
        """
        But : faire évoluer l'écran.
        Entrée : dt (float) secondes. Sortie : aucune.
        """
        self.temps += dt

    def dessiner(self, image):
        """
        But : dessiner l'écran.
        Entrée : image (Surface). Sortie : aucune.
        """

    def musique(self):
        """
        But : musique voulue sur cet écran : nom, (fond, dessus) ou None (silence).
        """
        return "menu"

    def tremblement(self):
        """
        But : décalage d'écran à appliquer (secousses).
        Entrée : aucune. Sortie : (tuple) (dx, dy).
        """
        return 0, 0


class MenuVertical:
    """
    Liste d'options sélectionnables (flèches, Z/S, souris, Entrée, clic).
    Attributs :
        options (list de (texte, fonction)) : libellé et action.
        indice (int) : option sélectionnée.
        x, y (float) : centre de la première option ; ecart (px) entre options.
    """

    def __init__(self, options, x, y, echelle=3, ecart=50):
        self.options = options
        self.indice = 0
        self.x = x
        self.y = y
        self.echelle = echelle
        self.ecart = ecart
        self.zones = []
        self.temps = 0.0

    def mettre_a_jour(self, dt, entrees, audio):
        """
        But : déplacer la sélection et déclencher l'option choisie.
        Entrées : dt (float), entrees (Entrees), audio (Audio).
        Sortie : aucune.
        """
        self.temps += dt
        ancien = self.indice
        if entrees.vient_d_appuyer("haut"):
            self.indice = (self.indice - 1) % len(self.options)
        if entrees.vient_d_appuyer("bas"):
            self.indice = (self.indice + 1) % len(self.options)
        if entrees.souris_bougee:
            for i, zone in enumerate(self.zones):
                if zone.collidepoint(entrees.souris):
                    self.indice = i
        if self.indice != ancien:
            audio.jouer("menu_nav")
        option = self.options[self.indice]
        sens = int(entrees.vient_d_appuyer("droite")) - int(entrees.vient_d_appuyer("gauche"))
        if sens and len(option) > 2:
            option[2](sens)
            return
        clic_valide = 1 in entrees.clics and any(
            zone.collidepoint(entrees.souris) for zone in self.zones)
        if entrees.vient_d_appuyer("valider") or clic_valide:
            audio.jouer("menu_ok")
            option[1]()

    def dessiner(self, image):
        """
        But : afficher les options, la sélection pulse entre deux chevrons.
        Entrée : image (Surface). Sortie : aucune.
        """
        self.zones = []
        for i, (texte, *_) in enumerate(self.options):
            y = self.y + i * self.ecart
            choisi = i == self.indice
            if choisi:
                # 8 paliers seulement : le texte lumineux reste en cache (un flou par
                # couleur), sinon chaque image refaisait un flou coûteux (chutes de FPS).
                pulsation = round((0.5 + 0.5 * math.sin(self.temps * 8)) * 7) / 7
                couleur = (255, int(176 + 79 * pulsation), int(255 * pulsation * 0.4))
                libelle = f"> {texte} <"
            else:
                couleur = (170, 140, 220)
                libelle = texte
            dessiner_texte(image, libelle, self.x, y, self.echelle, couleur,
                           lueur=choisi)
            largeur, hauteur = taille_texte(f"> {texte} <", self.echelle)
            self.zones.append(pygame.Rect(self.x - largeur / 2,
                                          y - hauteur / 2 - 8,
                                          largeur, hauteur + 16))


def voile(image, alpha=170, couleur=(8, 0, 20)):
    """
    But : assombrir toute l'image (fond des menus de pause / fin).
    Entrées : image (Surface), alpha (int), couleur (tuple).
    Sortie : aucune.
    """
    calque = pygame.Surface(image.get_size())
    calque.fill(couleur)
    calque.set_alpha(alpha)
    image.blit(calque, (0, 0))
