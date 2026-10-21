# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Sélection du niveau de départ (Campagne ou Coop) : grille de 12 cases
    réparties en 3 mondes ; seuls les niveaux déjà atteints sont ouverts.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Meilleur score par niveau.
"""

import math

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from moteur.rendu import halo_rect
from jeu.niveau import charger_campagne
from ecrans.base import EcranBase

NOMS_MONDES = {1: "SUNSET GRID", 2: "NEON CITY", 3: "CYBER CORE"}
COULEURS_MONDES = {1: config.ROSE, 2: config.CYAN, 3: config.VERT}


class EcranNiveaux(EcranBase):
    """Attributs : code ("campagne"/"coop"), niveaux, debloque (int), indice."""

    def __init__(self, app, code):
        super().__init__(app)
        self.code = code
        self.niveaux = charger_campagne()
        self.debloque = min(app.niveau_debloque(code), len(self.niveaux) - 1)
        self.indice = self.debloque
        self.zones = []

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        entrees = self.app.entrees
        ancien = self.indice
        if entrees.vient_d_appuyer("gauche"):
            self.indice = max(0, self.indice - 1)
        if entrees.vient_d_appuyer("droite"):
            self.indice = min(self.debloque, self.indice + 1)
        if entrees.vient_d_appuyer("haut"):
            self.indice = max(0, self.indice - 4)
        if entrees.vient_d_appuyer("bas"):
            self.indice = min(self.debloque, self.indice + 4)
        if entrees.souris_bougee:
            for i, zone in enumerate(self.zones):
                if zone.collidepoint(entrees.souris) and i <= self.debloque:
                    self.indice = i
        if self.indice != ancien:
            self.app.audio.jouer("menu_nav")
            self.app.fond.changer_monde(self.niveaux[self.indice].monde)
        clic = 1 in entrees.clics and any(
            z.collidepoint(entrees.souris) for z in self.zones[:self.debloque + 1])
        if entrees.vient_d_appuyer("valider") or clic:
            from ecrans.partie import EcranPartie
            from ecrans.modes import fabrique_mode
            self.app.audio.jouer("menu_ok")
            self.app.remplacer(EcranPartie(self.app, fabrique_mode(self.code, self.indice)))
        elif entrees.vient_d_appuyer("retour"):
            from ecrans.modes import EcranModes
            self.app.remplacer(EcranModes(self.app))

    def dessiner(self, image):
        self.app.fond.dessiner(image)
        voile = pygame.Surface(image.get_size())
        voile.fill((8, 0, 20))
        voile.set_alpha(130)
        image.blit(voile, (0, 0))
        titre = "CAMPAGNE" if self.code == "campagne" else "COOP"
        dessiner_texte(image, f"{titre} : CHOIX DU NIVEAU", config.LARGEUR / 2, 60, 5,
                       config.CYAN)
        self.zones = []
        for i, niveau in enumerate(self.niveaux):
            monde, colonne = divmod(i, 4)
            x = config.LARGEUR / 2 + (colonne - 1.5) * 230
            y = 200 + monde * 165
            if colonne == 0:
                dessiner_texte(image, f"MONDE {monde + 1}  {NOMS_MONDES.get(monde + 1, '')}",
                               config.LARGEUR / 2, y - 68, 2,
                               COULEURS_MONDES.get(monde + 1, config.BLANC), lueur=False)
            rect = pygame.Rect(0, 0, 200, 100)
            rect.center = (int(x), int(y))
            self.zones.append(rect)
            ouvert = i <= self.debloque
            choisi = i == self.indice
            couleur = COULEURS_MONDES.get(niveau.monde, config.BLANC)
            if not ouvert:
                couleur = (80, 60, 100)
            if choisi:
                lueur = halo_rect(rect.w, rect.h, couleur, rayon=10, epaisseur=4)
                image.blit(lueur, (rect.x - 20, rect.y - 20), special_flags=pygame.BLEND_RGB_ADD)
            pygame.draw.rect(image, (14, 2, 32), rect, border_radius=8)
            pygame.draw.rect(image, couleur, rect, 3 if choisi else 2, border_radius=8)
            dessiner_texte(image, str(i + 1), rect.centerx, rect.centery - 14, 5, couleur,
                           lueur=choisi)
            if ouvert:
                etiquette = "BOSS" if niveau.boss else niveau.nom.split("  ")[-1][:14]
                dessiner_texte(image, etiquette, rect.centerx, rect.bottom - 20, 2,
                               config.ROUGE if niveau.boss else config.BLANC, lueur=False)
            else:
                dessiner_texte(image, "VERROUILLE", rect.centerx, rect.bottom - 20, 2,
                               couleur, lueur=False)
        if math.sin(self.temps * 5) > -0.4:
            dessiner_texte(image, "ENTREE : JOUER    ECHAP : RETOUR", config.LARGEUR / 2,
                           config.HAUTEUR - 30, 2, (150, 120, 200), lueur=False)
