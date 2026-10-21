# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Définir la balle : position et vitesse en pixels/seconde, état « collée »
    à la raquette avant le lancement, traînée lumineuse, déformation à
    l'impact. La physique de collision est dans terrain.py.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Balles spéciales de boss.
"""

import math
from collections import deque

import pygame

from moteur import config
from moteur.rendu import halo_cercle, attenuer

LONGUEUR_TRAINEE = 14


class Balle:
    """
    Attributs :
        x, y (float) : centre ; vx, vy (float) : vitesse en px/s.
        rayon (int).
        collee (bool) : posée sur la raquette en attente de lancement.
        decalage_collage (float) : position relative sur la raquette.
        trainee (deque) : dernières positions, pour la traînée.
        impact (float) : déformation après un rebond (0..1).
        couleur (tuple) : couleur du halo.
        proprietaire (Joueur ou None) : dernier joueur à l'avoir renvoyée.
        raquette_collage (Raquette ou None) : raquette qui la porte.
        temps_collage (float) : relance automatique de l'aimant.
        feu (float) : secondes de balle de feu restantes.
        delai_portail (float) : évite de repasser aussitôt dans un portail.
    """

    def __init__(self, x, y, rayon=config.BALLE_RAYON):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.rayon = rayon
        self.collee = True
        self.decalage_collage = 0.0
        self.trainee = deque(maxlen=LONGUEUR_TRAINEE)
        self.impact = 0.0
        self.axe_impact = (0.0, 1.0)
        self.couleur = config.CYAN
        self.proprietaire = None
        self.raquette_collage = None
        self.temps_collage = 0.0
        self.feu = 0.0
        self.delai_portail = 0.0

    def vitesse(self):
        """
        But : norme de la vitesse.
        Entrée : aucune. Sortie : (float) px/s.
        """
        return math.hypot(self.vx, self.vy)

    def fixer_vitesse(self, norme):
        """
        But : changer la norme de la vitesse sans changer la direction.
        Entrée : norme (float) px/s. Sortie : aucune.
        """
        actuelle = self.vitesse()
        if actuelle > 0:
            self.vx *= norme / actuelle
            self.vy *= norme / actuelle

    def facteur_vitesse(self):
        """
        But : multiplicateur de vitesse dû aux effets du propriétaire.
        Entrée : aucune. Sortie : (float).
        """
        if self.proprietaire is None:
            return 1.0
        return self.proprietaire.facteur_vitesse_balles()

    def en_feu(self):
        """But : la balle est-elle une balle de feu ? Sortie : (bool)."""
        joueur = self.proprietaire
        return self.feu > 0 or (joueur is not None and (
            joueur.supernova > 0 or joueur.actif("feu")))

    def lancer(self, norme, angle_degres=-15, sens=-1):
        """
        But : décoller la balle de la raquette vers le haut.
        Entrées : norme (float) px/s ; angle_degres (float) : écart à la
                  verticale (négatif = vers la gauche).
        Sortie : aucune.
        """
        angle = math.radians(angle_degres)
        self.vx = norme * math.sin(angle)
        self.vy = sens * norme * math.cos(angle)
        self.collee = False
        self.raquette_collage = None

    def rebondir_effet(self, axe_x, axe_y):
        """
        But : déclencher la déformation visuelle (écrasement) à l'impact.
        Entrées : axe_x, axe_y (float) : normale de la surface touchée.
        Sortie : aucune.
        """
        self.impact = 1.0
        self.axe_impact = (axe_x, axe_y)

    def mettre_a_jour_visuel(self, dt):
        """
        But : mémoriser la position (traînée) et relâcher la déformation.
        Entrée : dt (float). Sortie : aucune.
        """
        self.trainee.append((self.x, self.y))
        self.impact = max(0.0, self.impact - dt * 7)
        self.feu = max(0.0, self.feu - dt)
        self.delai_portail = max(0.0, self.delai_portail - dt)

    def dessiner(self, image, temps=0.0):
        """
        But : dessiner traînée, halo et cœur de la balle (version feu ou
        fantôme selon les effets).
        Entrées : image (Surface), temps (float). Sortie : aucune.
        """
        fantome = (self.proprietaire is not None
                   and self.proprietaire.actif("fantome"))
        if fantome and math.sin(temps * 9) < 0.75:
            # Presque invisible : un simple point sombre.
            pygame.draw.circle(image, (60, 50, 90), (int(self.x), int(self.y)),
                               self.rayon, 1)
            return
        self.couleur = (255, 120, 30) if self.en_feu() else (
            self.proprietaire.couleur_corps if self.proprietaire else config.CYAN)
        # Traînée : disques de plus en plus petits et sombres.
        rapidite = min(1.0, self.vitesse() / config.BALLE_VITESSE_MAX)
        nb = len(self.trainee)
        for i, (tx, ty) in enumerate(self.trainee):
            ratio = (i + 1) / max(1, nb)
            rayon = max(1, int(self.rayon * ratio * (0.5 + 0.5 * rapidite)))
            couleur = attenuer(self.couleur, ratio * (0.25 + 0.5 * rapidite))
            pygame.draw.circle(image, couleur, (int(tx), int(ty)), rayon)

        lueur = halo_cercle(self.rayon + (3 if self.en_feu() else 0),
                            attenuer(self.couleur, 0.9), rayon=9)
        image.blit(lueur, lueur.get_rect(center=(int(self.x), int(self.y))),
                   special_flags=pygame.BLEND_RGB_ADD)

        # Déformation : ellipse écrasée le long de la normale d'impact.
        ecrase = self.impact * 0.35
        if ecrase > 0.02:
            ax, ay = self.axe_impact
            largeur = self.rayon * 2 * (1 + ecrase * abs(ay) - ecrase * abs(ax))
            hauteur = self.rayon * 2 * (1 + ecrase * abs(ax) - ecrase * abs(ay))
            ellipse = pygame.Rect(0, 0, int(largeur), int(hauteur))
            ellipse.center = (int(self.x), int(self.y))
            pygame.draw.ellipse(image, config.BLANC, ellipse)
        else:
            pygame.draw.circle(image, config.BLANC, (int(self.x), int(self.y)),
                               self.rayon)
            pygame.draw.circle(image, (200, 250, 255),
                               (int(self.x) - 2, int(self.y) - 2),
                               max(1, self.rayon // 3))
