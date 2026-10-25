# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Dessin des bannières (2.0) : un bandeau décoré, affiché derrière le
    pseudo d'un joueur (hub, profil, salons, classements, boutique).
    Le catalogue (couleurs, motif, icône) est dans reseau/boutique.py.
    Le fond fixe est mis en cache ; seuls les motifs animés sont redessinés.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 25/10/2026
"""

import colorsys
import math
import random

import pygame

from moteur import config
from moteur.rendu import attenuer, melanger
from reseau.boutique import BANNIERES_PAR_CODE, COULEURS_RARETES

_CACHE = {}
ANIMES = {"etoiles", "spectre", "glitch", "aurore", "flammes", "vagues"}


def _fond(banniere, taille):
    """But : fond fixe d'une bannière (dégradé + motif statique), en cache."""
    cle = (banniere["code"], taille)
    if cle in _CACHE:
        return _CACHE[cle]
    largeur, hauteur = taille
    sombre, vive = banniere["couleurs"]
    fond = pygame.Surface(taille)
    motif = banniere["motif"]
    for x in range(largeur):
        t = x / max(1, largeur - 1)
        if motif == "degrade":
            couleur = melanger(sombre, vive, t)
        else:
            couleur = melanger(sombre, attenuer(vive, 0.35), 0.5 - 0.5 * math.cos(t * math.pi))
        pygame.draw.line(fond, couleur, (x, 0), (x, hauteur))
    trait = attenuer(vive, 0.6)
    if motif == "rayures":
        for x in range(-hauteur, largeur + hauteur, 14):
            pygame.draw.line(fond, trait, (x, hauteur), (x + hauteur, 0), 4)
    elif motif == "grille":
        horizon = hauteur * 0.35
        for k in range(1, 6):
            y = horizon + (hauteur - horizon) * (k / 5) ** 1.8
            pygame.draw.line(fond, trait, (0, y), (largeur, y))
        for k in range(-12, 13):
            pygame.draw.line(fond, trait, (largeur / 2 + k * 6, horizon),
                             (largeur / 2 + k * 40, hauteur))
        pygame.draw.line(fond, vive, (0, horizon), (largeur, horizon), 2)
    elif motif == "circuit":
        hasard = random.Random(banniere["code"])
        for _ in range(largeur // 18):
            x, y = hasard.randrange(largeur), hasard.randrange(4, max(5, hauteur - 4))
            fin = x + hasard.randrange(10, 40)
            pygame.draw.line(fond, trait, (x, y), (fin, y), 2)
            pygame.draw.line(fond, trait, (fin, y), (fin + 6, y - 6 if y > hauteur / 2 else y + 6), 2)
            pygame.draw.circle(fond, vive, (fin + 6, y - 6 if y > hauteur / 2 else y + 6), 2)
    elif motif == "pixels":
        hasard = random.Random(banniere["code"])
        for x in range(0, largeur, 6):
            for y in range(0, hauteur, 6):
                if hasard.random() < 0.18 * (x / largeur + 0.3):
                    fond.fill(melanger(trait, vive, hasard.random()), (x, y, 5, 5))
    elif motif == "damier":
        cote = max(6, hauteur // 3)
        for i, x in enumerate(range(0, largeur, cote)):
            for j, y in enumerate(range(0, hauteur, cote)):
                if (i + j) % 2:
                    fond.fill(attenuer(vive, 0.5), (x, y, cote, cote))
    _CACHE[cle] = fond
    return fond


def _anime(image, banniere, rect, temps):
    """But : couche animée de certains motifs (dessinée par-dessus le fond)."""
    sombre, vive = banniere["couleurs"]
    motif = banniere["motif"]
    if motif == "etoiles":
        hasard = random.Random(banniere["code"])
        for k in range(rect.w // 10):
            x = rect.x + hasard.randrange(rect.w)
            y = rect.y + hasard.randrange(rect.h)
            eclat = 0.5 + 0.5 * math.sin(temps * (2 + hasard.random() * 3) + k)
            taille = 1 + int(eclat * 2)
            image.fill(attenuer(vive, 0.3 + 0.7 * eclat), (x, y, taille, taille))
    elif motif == "vagues":
        for k in range(3):
            points = [(x, rect.centery + math.sin(x * 0.05 + temps * 2 + k * 2) * rect.h * 0.25
                       + (k - 1) * rect.h * 0.22) for x in range(rect.x, rect.right + 6, 6)]
            pygame.draw.lines(image, attenuer(vive, 0.4 + 0.2 * k), False, points, 2)
    elif motif == "aurore":
        for x in range(rect.x, rect.right, 3):
            h = (math.sin(x * 0.03 + temps * 1.3) * 0.5 + 0.5) * rect.h * 0.8
            teinte = (0.35 + 0.15 * math.sin(x * 0.01 + temps)) % 1
            r, v, b = colorsys.hsv_to_rgb(teinte, 0.7, 0.9)
            image.fill((int(r * 120), int(v * 120), int(b * 120)),
                       (x, rect.bottom - int(h), 3, int(h)), special_flags=pygame.BLEND_RGB_ADD)
    elif motif == "flammes":
        for x in range(rect.x, rect.right, 4):
            h = (0.35 + 0.35 * abs(math.sin(x * 0.11 + temps * 6)) +
                 0.2 * math.sin(x * 0.37 - temps * 9)) * rect.h
            image.fill(attenuer(vive, 0.55), (x, rect.bottom - int(h), 4, int(h)),
                       special_flags=pygame.BLEND_RGB_ADD)
    elif motif == "spectre":
        for x in range(rect.x, rect.right, 4):
            r, v, b = colorsys.hsv_to_rgb(((x - rect.x) / rect.w + temps * 0.25) % 1, 0.8, 1)
            image.fill((int(r * 110), int(v * 110), int(b * 110)), (x, rect.y, 4, rect.h),
                       special_flags=pygame.BLEND_RGB_ADD)
    elif motif == "glitch":
        hasard = random.Random(int(temps * 10))
        for _ in range(5):
            bande = pygame.Rect(rect.x + hasard.randrange(rect.w), rect.y + hasard.randrange(rect.h),
                                hasard.randrange(10, 60), hasard.randrange(2, 6))
            image.fill(hasard.choice((vive, (255, 40, 120), config.BLANC)), bande.clip(rect))


def dessiner_banniere(image, code, rect, temps=0.0, cadre=True, voile=0):
    """
    But : dessiner une bannière dans un rectangle (rien si le code est vide ou inconnu).
    Entrées : image ; code (str) ; rect (pygame.Rect) ; temps (float) : animations ;
              cadre (bool) : liseré de la couleur de la rareté ;
              voile (int 0..255) : assombrir (pour lire un texte coloré par-dessus).
    Sortie : (bool) True si une bannière a été dessinée.
    """
    banniere = BANNIERES_PAR_CODE.get(code)
    if banniere is None or rect.w < 4 or rect.h < 4:
        return False
    rect = pygame.Rect(rect)
    image.blit(_fond(banniere, rect.size), rect.topleft)
    if banniere["motif"] in ANIMES:
        zone = image.get_clip()
        image.set_clip(rect.clip(zone) if zone else rect)
        _anime(image, banniere, rect, temps)
        image.set_clip(zone)
    if banniere["icone"]:
        from moteur.icones import dessiner_icone
        echelle = max(1, rect.h // 14)
        for cx in (rect.x + rect.h * 0.6, rect.right - rect.h * 0.6):
            dessiner_icone(image, banniere["icone"], (int(cx), rect.centery),
                           banniere["couleurs"][1], echelle)
    if voile:
        sombre = pygame.Surface(rect.size)
        sombre.fill((8, 0, 20))
        sombre.set_alpha(voile)
        image.blit(sombre, rect.topleft)
    if cadre:
        pygame.draw.rect(image, COULEURS_RARETES[banniere["rarete"]], rect, 2)
    return True


def dessiner_piece(image, centre, rayon, temps=0.0):
    """
    But : pièce de NEONS : un hexagone néon qui tourne doucement, avec un « N ».
    Entrées : image ; centre (x, y) ; rayon (int) ; temps (float).
    """
    cx, cy = centre
    ecrasement = 0.55 + 0.45 * abs(math.cos(temps * 1.5))
    points = [(cx + math.cos(math.pi / 3 * k + math.pi / 6) * rayon * ecrasement,
               cy + math.sin(math.pi / 3 * k + math.pi / 6) * rayon) for k in range(6)]
    pygame.draw.polygon(image, (20, 60, 90), points)
    pygame.draw.polygon(image, config.CYAN, points, 2)
    if ecrasement > 0.7 and rayon >= 8:
        from moteur.police_pixel import dessiner_texte
        dessiner_texte(image, "N", cx, cy, max(1, rayon // 7), config.BLANC, lueur=False,
                       ombre=False)
