# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Projectiles : tirs laser des raquettes et tirs des boss (boules de feu,
    rayons). Un tir de boss qui touche une raquette l'étourdit un instant.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Tirs à tête chercheuse.
"""

import pygame

from moteur import config
from moteur.rendu import halo_cercle, halo_rect, attenuer


class Laser:
    """
    Trait lumineux tiré par une raquette.
    Attributs : x, y (float), sens (-1 vers le haut, +1 vers le bas),
                joueur (Joueur) : tireur, vivant (bool).
    """

    vitesse = 950
    longueur = 16

    def __init__(self, x, y, sens, joueur):
        self.x = x
        self.y = y
        self.sens = sens
        self.joueur = joueur
        self.vivant = True

    def boite(self):
        """But : boîte de collision. Sortie : (tuple x_min, y_min, x_max, y_max)."""
        return (self.x - 2, self.y - self.longueur / 2,
                self.x + 2, self.y + self.longueur / 2)

    def mettre_a_jour(self, dt):
        """But : avancer. Entrée : dt (float)."""
        self.y += self.vitesse * self.sens * dt

    def dessiner(self, image):
        """But : trait blanc entouré d'un halo de la couleur du tireur."""
        couleur = self.joueur.couleur_bord if self.joueur else config.ROUGE
        lueur = halo_rect(4, self.longueur, attenuer(couleur, 0.8), rayon=4)
        image.blit(lueur, (int(self.x) - 2 - 8, int(self.y - self.longueur / 2) - 8),
                   special_flags=pygame.BLEND_RGB_ADD)
        image.fill(config.BLANC, (int(self.x) - 1, int(self.y - self.longueur / 2),
                                  3, self.longueur))


class TirBoss:
    """
    Boule d'énergie tirée par un boss.
    Attributs : x, y, vx, vy (float), rayon (int), couleur (tuple), vivant.
    """

    def __init__(self, x, y, vx, vy, rayon=9, couleur=config.AMBRE):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.rayon = rayon
        self.couleur = couleur
        self.vivant = True
        self.temps = 0.0

    def boite(self):
        """But : boîte de collision (un peu plus petite que le dessin)."""
        r = self.rayon * 0.8
        return (self.x - r, self.y - r, self.x + r, self.y + r)

    def mettre_a_jour(self, dt):
        """But : avancer. Entrée : dt (float)."""
        self.temps += dt
        self.x += self.vx * dt
        self.y += self.vy * dt

    def dessiner(self, image):
        """But : boule lumineuse qui palpite."""
        lueur = halo_cercle(self.rayon, attenuer(self.couleur, 0.9), rayon=8)
        image.blit(lueur, lueur.get_rect(center=(int(self.x), int(self.y))),
                   special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.circle(image, (255, 245, 200), (int(self.x), int(self.y)),
                           max(2, self.rayon - 3))
