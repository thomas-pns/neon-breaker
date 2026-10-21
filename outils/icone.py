# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Dessiner l'icône de l'application (outils/icone.png, 512 x 512) dans le
    style du jeu : soleil rayé, grille, briques néon, raquette et balle.
    PyInstaller la convertit en .ico (Windows) et .icns (macOS).
    Utilisation : python outils/icone.py

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import math
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from moteur import config  # noqa: E402
from moteur.rendu import flouter, melanger  # noqa: E402

TAILLE = 512


def dessiner():
    pygame.init()
    image = pygame.Surface((TAILLE, TAILLE), pygame.SRCALPHA)
    fond = pygame.Surface((TAILLE, TAILLE))
    for y in range(TAILLE):
        t = y / TAILLE
        couleur = melanger((14, 2, 40), (120, 20, 140), t ** 1.4) if t < 0.62 else \
            melanger((40, 6, 70), (8, 0, 24), (t - 0.62) / 0.38)
        pygame.draw.line(fond, couleur, (0, y), (TAILLE, y))
    # Soleil rayé.
    for dy in range(-120, 121):
        demi = math.sqrt(max(0, 120 ** 2 - dy * dy))
        y = 300 + dy
        if y > 318:
            continue
        if dy > -20 and (dy // 10) % 2:
            continue
        couleur = melanger((255, 236, 110), (255, 60, 140), (dy + 120) / 240)
        pygame.draw.line(fond, couleur, (256 - demi, y), (256 + demi, y))
    # Grille.
    pygame.draw.line(fond, (255, 200, 255), (0, 318), (TAILLE, 318), 3)
    for k in range(1, 9):
        y = 318 + 194 / (9 - k + 0.6) * 1.1
        pygame.draw.line(fond, config.ROSE, (0, int(y)), (TAILLE, int(y)), 2)
    for i in range(-8, 9):
        pygame.draw.line(fond, config.CYAN, (256 + i * 6, 318), (256 + i * 80, TAILLE), 2)
    # Briques, raquette, balle (sur un calque lumineux).
    neon = pygame.Surface((TAILLE, TAILLE), pygame.SRCALPHA)
    for ligne, couleur in enumerate((config.AMBRE, config.ROSE, config.CYAN)):
        for colonne in range(4):
            rect = pygame.Rect(60 + colonne * 100, 60 + ligne * 44, 88, 32)
            pygame.draw.rect(neon, (*melanger((20, 0, 40), couleur, 0.35), 255), rect, border_radius=6)
            pygame.draw.rect(neon, (*couleur, 255), rect, 5, border_radius=6)
    pygame.draw.rect(neon, (*config.RAQUETTE_CORPS, 255), (176, 420, 160, 26), border_radius=10)
    pygame.draw.rect(neon, (*config.RAQUETTE_BORD, 255), (176, 420, 160, 26), 5, border_radius=10)
    pygame.draw.circle(neon, (255, 255, 255, 255), (300, 370), 18)
    fond.blit(flouter(neon, 14), (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    fond.blit(neon, (0, 0))
    # Coins arrondis.
    masque = pygame.Surface((TAILLE, TAILLE), pygame.SRCALPHA)
    pygame.draw.rect(masque, (255, 255, 255, 255), (0, 0, TAILLE, TAILLE), border_radius=96)
    image.blit(fond, (0, 0))
    image.blit(masque, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return image


if __name__ == "__main__":
    chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icone.png")
    pygame.image.save(dessiner(), chemin)
    print("Icône écrite :", chemin)
