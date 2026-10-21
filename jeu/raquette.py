# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Définir la raquette : déplacement fluide au clavier (accélération et
    freinage), suivi de la souris, limites du terrain, largeur animée
    (élargir / rétrécir), glace, étourdissement, canons laser, aimant,
    effet d'écrasement au contact. Une raquette peut être en bas
    (sens = -1, la balle repart vers le haut) ou en haut (sens = +1, Duel).

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Skins de raquette.
"""

import math

import pygame

from moteur import config
from moteur.rendu import halo_rect, attenuer, melanger


class Raquette:
    """
    Attributs :
        x (float) : centre horizontal ; y (float) : haut de la raquette.
        largeur_base, largeur, hauteur (float).
        sens (int) : -1 raquette du bas, +1 raquette du haut.
        joueur (Joueur ou None).
        vx (float) : vitesse horizontale (px/s).
        x_min, x_max (float) : limites du terrain.
        cible_souris (float ou None) : position visée à la souris.
        ecrasement (float) : animation de rebond (0..1).
        etourdie (float) : secondes d'immobilisation (tir de boss).
        gelee (float) : immobilisation (pénalité du mode Course).
    """

    def __init__(self, x_min, x_max, y, largeur=config.RAQUETTE_L,
                 hauteur=config.RAQUETTE_H, sens=-1, joueur=None):
        self.x_min = x_min
        self.x_max = x_max
        self.x = (x_min + x_max) / 2
        self.y = y
        self.largeur_base = largeur
        self.largeur = largeur
        self.hauteur = hauteur
        self.sens = sens
        self.joueur = joueur
        self.vx = 0.0
        self.cible_souris = None
        self.ecrasement = 0.0
        self.etourdie = 0.0
        self.gelee = 0.0
        self.temps = 0.0

    # --- Géométrie ----------------------------------------------------------

    def rect(self):
        """But : rectangle de collision. Sortie : (pygame.Rect)."""
        return pygame.Rect(int(self.x - self.largeur / 2), int(self.y),
                           int(self.largeur), int(self.hauteur))

    def obtenir_boite(self):
        """But : boîte (x_min, y_min, x_max, y_max). Sortie : (tuple)."""
        return (self.x - self.largeur / 2, self.y,
                self.x + self.largeur / 2, self.y + self.hauteur)

    def face_y(self):
        """
        But : ordonnée de la face qui renvoie la balle (haut pour la
        raquette du bas, bas pour celle du haut).
        Sortie : (float).
        """
        return self.y if self.sens < 0 else self.y + self.hauteur

    def couleurs(self):
        """But : (corps, bord) selon le joueur. Sortie : (tuple, tuple)."""
        if self.joueur is not None:
            return self.joueur.couleur_corps, self.joueur.couleur_bord
        return config.RAQUETTE_CORPS, config.RAQUETTE_BORD

    # --- Mouvement ----------------------------------------------------------

    def mettre_a_jour(self, dt, direction):
        """
        But : déplacer la raquette.
        Entrées : dt (float) ; direction (int) : -1 gauche, +1 droite, 0 rien.
        Sortie : aucune.
        """
        self.temps += dt
        joueur = self.joueur
        glace = joueur is not None and joueur.actif("glace")
        if joueur is not None:
            cible = self.largeur_base * joueur.facteur_largeur()
            self.largeur += (cible - self.largeur) * min(1.0, dt * 8)
        self.etourdie = max(0.0, self.etourdie - dt)
        self.gelee = max(0.0, self.gelee - dt)
        if self.etourdie > 0 or self.gelee > 0:
            direction = 0
            self.cible_souris = None

        acceleration = config.RAQUETTE_ACCEL * (0.22 if glace else 1)
        freinage = config.RAQUETTE_FREIN * (0.06 if glace else 1)
        if direction != 0:
            self.cible_souris = None
            if self.vx * direction < 0 and not glace:
                self.vx = 0.0                      # demi-tour franc
            self.vx += direction * acceleration * dt
            limite = config.RAQUETTE_VITESSE_MAX
            self.vx = max(-limite, min(limite, self.vx))
        elif self.cible_souris is not None:
            ecart = self.cible_souris - self.x
            self.vx += (ecart * 22 - self.vx) * (0.15 if glace else 1.0)
        else:
            frein = freinage * dt
            if abs(self.vx) <= frein:
                self.vx = 0.0
            else:
                self.vx -= math.copysign(frein, self.vx)

        self.x += self.vx * dt
        self.contraindre()
        self.ecrasement = max(0.0, self.ecrasement - dt * 6)

    def contraindre(self):
        """But : garder la raquette entre les murs du terrain."""
        demi = self.largeur / 2
        if self.x - demi < self.x_min:
            self.x = self.x_min + demi
            self.vx = max(0.0, self.vx) * (0.5 if self._glisse() else 0)
        elif self.x + demi > self.x_max:
            self.x = self.x_max - demi
            self.vx = min(0.0, self.vx) * (0.5 if self._glisse() else 0)

    def _glisse(self):
        return self.joueur is not None and self.joueur.actif("glace")

    def viser_souris(self, x):
        """But : faire suivre la souris. Entrée : x (float) interne."""
        if self.etourdie <= 0 and self.gelee <= 0:
            self.cible_souris = x

    def frappee(self):
        """But : déclencher l'écrasement visuel (la balle vient de rebondir)."""
        self.ecrasement = 1.0

    def positions_canons(self):
        """But : abscisses des deux canons laser. Sortie : (tuple)."""
        return (self.x - self.largeur / 2 + 8, self.x + self.largeur / 2 - 8)

    # --- Dessin ---------------------------------------------------------------

    def dessiner(self, image, temps):
        """
        But : dessiner la raquette néon (corps dégradé, bords lumineux,
        réacteurs, canons laser, aimant, étincelles si étourdie).
        Entrées : image (Surface), temps (float). Sortie : aucune.
        """
        corps, bord = self.couleurs()
        joueur = self.joueur
        if (self.etourdie > 0 or self.gelee > 0) and int(temps * 16) % 2:
            corps, bord = (90, 90, 120), (160, 160, 200)
        if joueur is not None and joueur.actif("glace"):
            corps = melanger(corps, (200, 240, 255), 0.6)
        ecrase = math.sin(self.ecrasement * math.pi) * 0.3 if self.ecrasement else 0
        largeur = int(self.largeur * (1 + ecrase * 0.5))
        hauteur = max(4, int(self.hauteur * (1 - ecrase)))
        rect = pygame.Rect(0, 0, largeur, hauteur)
        if self.sens < 0:
            rect.midbottom = (int(self.x), int(self.y + self.hauteur))
        else:
            rect.midtop = (int(self.x), int(self.y))

        lueur = halo_rect(largeur, hauteur, attenuer(bord, 0.8), rayon=8,
                          epaisseur=4)
        image.blit(lueur, (rect.x - 16, rect.y - 16),
                   special_flags=pygame.BLEND_RGB_ADD)
        for i in range(hauteur):
            t = i / max(1, hauteur - 1)
            if self.sens > 0:
                t = 1 - t
            couleur = melanger((230, 255, 255), corps, t * 0.8)
            couleur = melanger(couleur, (20, 30, 90), max(0, t - 0.6))
            pygame.draw.line(image, couleur, (rect.x + 3, rect.y + i),
                             (rect.right - 4, rect.y + i))
        pygame.draw.rect(image, bord, rect, 2, border_radius=6)

        intensite = 0.5 + 0.5 * min(1.0, abs(self.vx) / config.RAQUETTE_VITESSE_MAX)
        pulse = 0.75 + 0.25 * math.sin(temps * 20)
        for bord_x in (rect.x + 2, rect.right - 9):
            image.fill(attenuer(config.AMBRE, intensite * pulse),
                       (bord_x, rect.y + 3, 7, max(2, hauteur - 6)),
                       special_flags=pygame.BLEND_RGB_ADD)

        if joueur is not None and joueur.actif("laser"):
            for cx in self.positions_canons():
                canon = pygame.Rect(0, 0, 6, 10)
                if self.sens < 0:
                    canon.midbottom = (int(cx), rect.top + 2)
                else:
                    canon.midtop = (int(cx), rect.bottom - 2)
                pygame.draw.rect(image, config.ROUGE, canon)
                image.fill(config.BLANC, canon.inflate(-4, -4))
        if joueur is not None and joueur.aimant_prises > 0:
            y = rect.top - 3 if self.sens < 0 else rect.bottom + 2
            for k in range(joueur.aimant_prises):
                image.fill(config.VERT, (rect.centerx - 22 + k * 10, y, 6, 2))
