# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Tableau des meilleurs scores : un onglet par mode classé (Campagne,
    Arcade, Hardcore, Coop), top 10 avec noms en 3 lettres.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Date de chaque record.
"""

import math

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from ecrans.base import EcranBase, voile
from ecrans.hud import panneau

ONGLETS = [("campagne", "CAMPAGNE", config.CYAN), ("arcade", "ARCADE", config.ROSE),
           ("hardcore", "HARDCORE", config.ROUGE), ("coop", "COOP", config.VERT)]
COULEURS_RANGS = [config.AMBRE, (220, 220, 240), (230, 140, 80)]


class EcranScores(EcranBase):
    """Attribut : onglet (int)."""

    def __init__(self, app):
        super().__init__(app)
        self.onglet = 0

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        entrees = self.app.entrees
        if entrees.vient_d_appuyer("droite") or 1 in entrees.clics:
            self.onglet = (self.onglet + 1) % len(ONGLETS)
            self.app.audio.jouer("menu_nav")
        elif entrees.vient_d_appuyer("gauche"):
            self.onglet = (self.onglet - 1) % len(ONGLETS)
            self.app.audio.jouer("menu_nav")
        elif entrees.vient_d_appuyer("retour") or entrees.vient_d_appuyer("valider"):
            from ecrans.titre import EcranTitre
            self.app.remplacer(EcranTitre(self.app))

    def dessiner(self, image):
        self.app.fond.dessiner(image)
        voile(image, 150)
        dessiner_texte(image, "MEILLEURS SCORES", config.LARGEUR / 2, 60, 6, config.AMBRE)
        for i, (_, titre, couleur) in enumerate(ONGLETS):
            x = config.LARGEUR / 2 + (i - 1.5) * 230
            choisi = i == self.onglet
            rect = pygame.Rect(0, 0, 210, 44)
            rect.center = (int(x), 130)
            pygame.draw.rect(image, couleur if choisi else (60, 30, 90), rect,
                             0 if choisi else 2, border_radius=8)
            dessiner_texte(image, titre, rect.centerx, rect.centery, 2,
                           (20, 0, 30) if choisi else couleur, lueur=False)
        code, titre, couleur = ONGLETS[self.onglet]
        cadre = pygame.Rect(0, 0, 640, 470)
        cadre.midtop = (config.LARGEUR / 2, 172)
        panneau(image, cadre, couleur)
        top = self.app.classement(code)
        if not top:
            dessiner_texte(image, "AUCUN SCORE POUR L'INSTANT", cadre.centerx, cadre.centery,
                           3, (150, 120, 200), lueur=False)
        for i, entree in enumerate(top):
            y = cadre.y + 40 + i * 43
            teinte = COULEURS_RANGS[i] if i < 3 else config.BLANC
            agrandi = 3 if i == 0 else 2
            dessiner_texte(image, f"{i + 1:2d}", cadre.x + 60, y, agrandi, teinte,
                           ancrage="gauche", lueur=i == 0)
            dessiner_texte(image, entree["nom"], cadre.x + 170, y, agrandi + 1, teinte,
                           ancrage="gauche", lueur=i == 0)
            dessiner_texte(image, f"{entree['score']:07d}", cadre.right - 60, y, agrandi + 1,
                           teinte, ancrage="droite", lueur=i == 0)
        if math.sin(self.temps * 5) > -0.4:
            dessiner_texte(image, "← → : MODE    ECHAP : RETOUR", config.LARGEUR / 2,
                           config.HAUTEUR - 30, 2, (150, 120, 200), lueur=False)
