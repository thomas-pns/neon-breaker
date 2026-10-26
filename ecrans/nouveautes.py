# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Afficher les nouveautes du jeu par version, avec des volets repliables.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Realise le 23/10/2026
"""

import json
import os

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from ecrans.base import EcranBase, voile
from ecrans.hud import panneau


def charger_nouveautes():
    """But : lire les versions disponibles. Entree(s) : aucune. Sortie : liste de dictionnaires."""
    chemin = os.path.join(config.DOSSIER_RESSOURCES, "nouveautes.json")
    with open(chemin, encoding="utf-8") as fichier:
        return json.load(fichier)


class EcranNouveautes(EcranBase):
    """Ecran de consultation des nouveautes, navigable au clavier et a la souris."""

    vertical = True               # dessiné aussi au format vertical (téléphone)

    def __init__(self, app):
        super().__init__(app)
        self.versions = charger_nouveautes()
        self.indice = 0
        self.ouvert = 0 if self.versions else None
        self.zones = []

    def _basculer(self, indice):
        """But : ouvrir ou fermer un volet. Entree(s) : indice (int). Sortie : aucune."""
        self.indice = indice
        self.ouvert = None if self.ouvert == indice else indice

    def mettre_a_jour(self, dt):
        """But : traiter la navigation et les clics. Entree(s) : dt (float). Sortie : aucune."""
        super().mettre_a_jour(dt)
        entrees = self.app.entrees
        if entrees.vient_d_appuyer("retour"):
            from ecrans.titre import EcranTitre
            self.app.remplacer(EcranTitre(self.app))
            return
        ancien = self.indice
        if self.versions and entrees.vient_d_appuyer("haut"):
            self.indice = (self.indice - 1) % len(self.versions)
        elif self.versions and entrees.vient_d_appuyer("bas"):
            self.indice = (self.indice + 1) % len(self.versions)
        if self.indice != ancien:
            self.ouvert = self.indice           # le volet suit la sélection
            self.app.audio.jouer("menu_nav")
        if entrees.vient_d_appuyer("valider") and self.versions:
            self._basculer(self.indice)
        if 1 in entrees.clics:
            for i, zone in enumerate(self.zones):
                if zone.collidepoint(entrees.souris):
                    if i == self.indice:
                        self._basculer(i)
                    else:
                        self.indice = i
                        self.ouvert = i
                    break

    def dessiner(self, image):
        """But : dessiner la liste et le detail selectionne. Entree(s) : image (Surface). Sortie : aucune."""
        self.app.fond.dessiner(image)
        voile(image, 175)
        vertical = config.HAUTEUR > config.LARGEUR
        haut = (50 + min(110, max(0, config.HAUTEUR - 1422) // 2)) if vertical else 0
        dessiner_texte(image, "NOUVEAUTES", config.LARGEUR / 2, 48 + haut, 5, config.CYAN)
        self.zones = []
        hauteur = min(58, 500 // max(1, len(self.versions)))
        for i, version in enumerate(self.versions):
            if vertical:                     # téléphone : versions en pastilles, 4 par ligne
                ligne, colonne = divmod(i, 4)
                rect = pygame.Rect(24 + colonne * 190, 110 + haut + ligne * 64, 178, 54)
            else:
                rect = pygame.Rect(105, 115 + i * hauteur, 300, hauteur - 8)
            self.zones.append(rect)
            couleur = config.AMBRE if i == self.indice else config.VIOLET
            panneau(image, rect, couleur)
            dessiner_texte(image, version.get("version", ""), rect.centerx, rect.centery,
                           3, couleur)
        if self.ouvert is not None and self.versions:
            version = self.versions[self.ouvert]
            if vertical:
                haut_detail = self.zones[-1].bottom + 30 if self.zones else 120 + haut
                rect = pygame.Rect(24, haut_detail, config.LARGEUR - 48, 500)
            else:
                rect = pygame.Rect(445, 115, 730, 500)
            panneau(image, rect, config.CYAN)
            dessiner_texte(image, version.get("titre", ""), rect.centerx, rect.y + 45,
                           4, config.AMBRE)
            for i, ligne in enumerate(version.get("lignes", [])):
                dessiner_texte(image, ligne, rect.x + 36, rect.y + 105 + i * 36,
                               2, config.BLANC, ancrage="gauche", lueur=False)
        if not vertical:
            dessiner_texte(image, "HAUT / BAS : VERSION    ENTREE / CLIC : OUVRIR    ECHAP : RETOUR",
                           config.LARGEUR / 2, config.HAUTEUR - 26, 2,
                           (150, 120, 200), lueur=False)
