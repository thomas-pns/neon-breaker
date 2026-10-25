# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Éléments partagés par les écrans en ligne : champ de saisie de texte
    (pseudo, mot de passe), couleurs des joueurs, fond assombri, petits
    utilitaires d'affichage (dates, durées).

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import datetime
import math

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from moteur.rendu import halo_rect, attenuer
from ecrans.base import EcranBase

COULEURS_PROFIL = {"cyan": config.CYAN, "rose": config.ROSE, "ambre": config.AMBRE,
                   "violet": config.VIOLET, "vert": config.VERT, "bleu": config.BLEU}
NOMS_MODES = {"campagne": "CAMPAGNE", "arcade": "ARCADE", "hardcore": "HARDCORE",
              "coop": "COOP", "duel": "DUEL", "course": "COURSE",
              "defi": "DEFI", "semaine": "SEMAINE", "series": "SERIES",
              "classe": "CLASSEE"}
GRIS = (170, 140, 220)
CARACTERES_PSEUDO = ("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
                     "0123456789-_")


def couleur_profil(nom):
    return COULEURS_PROFIL.get(nom, config.CYAN)


def date_courte(horodatage):
    if not horodatage:
        return "-"
    return datetime.datetime.fromtimestamp(horodatage).strftime("%d/%m/%Y")


def duree_lisible(secondes):
    minutes = int(secondes // 60)
    return f"{minutes // 60}H{minutes % 60:02d}"


class EcranEnLigneBase(EcranBase):
    """Écran en ligne : fond synthwave assombri et titre."""

    titre = "EN LIGNE"

    def dessiner_fond(self, image, titre=None):
        self.app.fond.dessiner(image)
        voile = pygame.Surface(image.get_size())
        voile.fill((8, 0, 20))
        voile.set_alpha(150)
        image.blit(voile, (0, 0))
        dessiner_texte(image, titre or self.titre, config.LARGEUR / 2, 50, 5, config.CYAN)
        en_ligne = self.app.en_ligne
        if en_ligne.connecte:
            dessiner_texte(image, f"{en_ligne.pseudo.upper()}  RANG {en_ligne.niveau}",
                           config.LARGEUR - 20, 22, 2, couleur_profil(en_ligne.couleur),
                           ancrage="droite", lueur=False)
            if self.titre != "BOUTIQUE":
                from moteur.bannieres import dessiner_piece
                zone = dessiner_texte(image, str(getattr(en_ligne, "neons", 0)), config.LARGEUR - 20,
                                      46, 2, config.CYAN, ancrage="droite", lueur=False)
                dessiner_piece(image, (zone.x - 12, zone.centery), 8, self.temps)

    def pied(self, image, texte):
        if math.sin(self.temps * 5) > -0.4:
            dessiner_texte(image, texte, config.LARGEUR / 2, config.HAUTEUR - 26, 2,
                           (150, 120, 200), lueur=False)


class ChampTexte:
    """
    Zone de saisie. Attributs : libelle, valeur, masque (bool : mot de
    passe), maximum (int), autorises (str ou None : caractères permis).
    """

    def __init__(self, libelle, valeur="", masque=False, maximum=12, autorises=None):
        self.libelle = libelle
        self.valeur = valeur
        self.masque = masque
        self.maximum = maximum
        self.autorises = autorises
        self.rect = pygame.Rect(0, 0, 0, 0)

    def saisir(self, entrees):
        """But : ajouter les caractères tapés ; Retour arrière efface."""
        for caractere in entrees.texte:
            if len(self.valeur) >= self.maximum or not caractere.isprintable():
                continue
            if self.autorises is not None and caractere not in self.autorises:
                continue
            self.valeur += caractere
        if pygame.KSCAN_BACKSPACE in entrees.appuis:
            self.valeur = self.valeur[:-1]

    def dessiner(self, image, x, y, largeur, actif, temps):
        """But : cadre néon, libellé au-dessus, texte et curseur clignotant."""
        self.rect = pygame.Rect(int(x - largeur / 2), int(y), int(largeur), 48)
        couleur = config.CYAN if actif else (110, 80, 160)
        dessiner_texte(image, self.libelle, self.rect.x, y - 16, 2, GRIS, ancrage="gauche",
                       lueur=False)
        pygame.draw.rect(image, (14, 2, 32), self.rect, border_radius=6)
        if actif:
            lueur = halo_rect(self.rect.w, self.rect.h, attenuer(couleur, 0.7), rayon=8)
            image.blit(lueur, (self.rect.x - 16, self.rect.y - 16),
                       special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.rect(image, couleur, self.rect, 2, border_radius=6)
        texte = "*" * len(self.valeur) if self.masque else self.valeur
        if self.masque:
            texte = "".join("♥" if False else "*" for _ in self.valeur)
        affiche = texte.upper() if not self.masque else texte
        zone = dessiner_texte(image, affiche, self.rect.x + 16, self.rect.centery, 3,
                              config.BLANC, ancrage="gauche", lueur=False)
        if actif and int(temps * 2) % 2 == 0:
            x_curseur = zone.right + 4 if self.valeur else self.rect.x + 18
            image.fill(config.CYAN, (x_curseur, self.rect.y + 10, 3, 28))
