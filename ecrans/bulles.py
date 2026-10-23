# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Afficher les bulles d'aide ponctuelles pendant une partie.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Realise le 23/10/2026
"""

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from ecrans.hud import panneau

DUREE = 5.0


def afficher(mode, code, joueur):
    """But : memoriser et afficher une bulle si elle n'a jamais ete vue."""
    if mode.en_ligne or getattr(mode, "hardcore", False):
        return
    if code == "pouvoir" and not joueur.avec_pouvoirs:
        return
    vues = mode.app.donnees.setdefault("bulles_vues", [])
    if code in vues:
        return
    vues.append(code)
    mode.app.enregistrer()
    numero = joueur.numero
    if code == "pouvoir":
        if mode.deux_joueurs and numero == 1:
            texte = "J1 POUVOIR STOCKE ! A CHOISIR / E LANCER"
        elif mode.deux_joueurs:
            texte = "J2 POUVOIR STOCKE ! CTRL D CHOISIR / MAJ D LANCER"
        else:
            texte = "POUVOIR STOCKE ! 1 2 3 OU E POUR LE LANCER"
    else:
        touche = ("S" if numero == 1 else "FLECHE BAS") if mode.deux_joueurs else "MAJ"
        texte = f"OVERDRIVE PLEIN ! {touche} : SUPERNOVA"
    mode.bulle = (texte, DUREE)


def dessiner(mode, image):
    """But : dessiner la bulle active avec un fondu d'entree et de sortie."""
    if not getattr(mode, "bulle", None):
        return
    texte, reste = mode.bulle
    alpha = max(0, min(255, int((DUREE - reste) * 255 / 0.35), int(reste * 255 / 0.5)))
    cadre = pygame.Rect(0, 0, 700, 66)
    cadre.center = (config.LARGEUR // 2, 112)
    couche = pygame.Surface(cadre.size, pygame.SRCALPHA)
    panneau(couche, couche.get_rect(), config.AMBRE)
    couche.set_alpha(alpha)
    image.blit(couche, cadre.topleft)
    dessiner_texte(image, texte, cadre.centerx, cadre.centery, 2, config.BLANC,
                   alpha=alpha, lueur=False)
