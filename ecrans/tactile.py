# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Boutons à l'écran pour jouer au doigt (téléphone, tablette, écran tactile).
    Ils remplacent le rappel des touches dans le panneau de droite dès qu'un
    doigt a touché l'écran : les 3 pouvoirs, la SUPERNOVA et la PAUSE.
    Le reste se fait sur le terrain : glisser pour bouger, toucher pour lancer.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 26/10/2026
"""

import pygame

from jeu.capsule import CATALOGUE, OR_POUVOIR
from moteur import config
from moteur.icones import dessiner_icone
from moteur.police_pixel import dessiner_texte
from moteur.rendu import attenuer

GRIS = (90, 60, 120)


def bouton(image, app, rect, action, couleur, texte="", actif=True, epaisseur=3):
    """But : dessiner un bouton tactile et le déclarer aux commandes."""
    pygame.draw.rect(image, attenuer(couleur, 0.22 if actif else 0.08), rect, border_radius=10)
    pygame.draw.rect(image, couleur if actif else GRIS, rect, epaisseur, border_radius=10)
    if texte:
        dessiner_texte(image, texte, rect.centerx, rect.centery, 2,
                       config.BLANC if actif else GRIS, lueur=False)
    app.entrees.bouton_tactile(rect, action)


def dessiner_boutons_partie(image, app, rect, y, joueur):
    """
    But : boutons d'une partie au doigt, en bas d'un panneau latéral.
    Entrées : image ; app ; rect (Rect du panneau) ; y (int) : haut de la zone ;
              joueur (Joueur) : pour l'inventaire et la jauge.
    """
    largeur = rect.w - 24
    x = rect.x + 12
    if joueur.avec_pouvoirs:
        cote = (largeur - 16) // 3
        for i in range(config.TAILLE_INVENTAIRE):
            case = pygame.Rect(x + i * (cote + 8), y, cote, cote)
            plein = i < len(joueur.inventaire)
            bouton(image, app, case, f"pouvoir{i + 1}", OR_POUVOIR, actif=plein)
            if plein:
                code = joueur.inventaire[i]
                if not dessiner_icone(image, code, case.center, OR_POUVOIR, 3):
                    dessiner_texte(image, CATALOGUE[code].lettre, case.centerx, case.centery, 3,
                                   config.BLANC, lueur=False)
        y += cote + 10
    if joueur.avec_overdrive:
        pleine = joueur.overdrive_pret()
        bouton(image, app, pygame.Rect(x, y, largeur, 52), "overdrive", config.ROSE,
               "SUPERNOVA", actif=pleine)
        y += 62
    bouton(image, app, pygame.Rect(x, y, largeur, 44), "pause", config.CYAN, "PAUSE")


def bouton_pause(image, app, centre=(config.LARGEUR - 40, 40)):
    """But : petit bouton PAUSE rond (écrans sans panneau latéral)."""
    rect = pygame.Rect(0, 0, 56, 56)
    rect.center = centre
    pygame.draw.rect(image, (20, 5, 40), rect, border_radius=28)
    pygame.draw.rect(image, config.CYAN, rect, 3, border_radius=28)
    for dx in (-8, 8):
        image.fill(config.CYAN, (rect.centerx + dx - 3, rect.centery - 11, 6, 22))
    app.entrees.bouton_tactile(rect, "pause")


def bouton_retour(image, app):
    """But : bouton RETOUR (flèche) en bas à gauche des menus, à la place de la touche Échap."""
    rect = pygame.Rect(14, config.HAUTEUR - 70, 56, 56)
    pygame.draw.rect(image, (20, 5, 40), rect, border_radius=28)
    pygame.draw.rect(image, config.CYAN, rect, 3, border_radius=28)
    cx, cy = rect.center
    pygame.draw.polygon(image, config.CYAN, [(cx - 13, cy), (cx + 1, cy - 12), (cx + 1, cy + 12)])
    image.fill(config.CYAN, (cx, cy - 4, 13, 8))
    app.entrees.bouton_tactile(rect, "retour")
