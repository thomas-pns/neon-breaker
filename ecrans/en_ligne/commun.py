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
from ecrans.menus import Navigation

COULEURS_PROFIL = {"cyan": config.CYAN, "rose": config.ROSE, "ambre": config.AMBRE,
                   "violet": config.VIOLET, "vert": config.VERT, "bleu": config.BLEU}
NOMS_MODES = {"campagne": "CAMPAGNE", "arcade": "ARCADE", "hardcore": "HARDCORE",
              "coop": "COOP", "duel": "DUEL", "course": "COURSE",
              "defi": "DEFI", "semaine": "SEMAINE", "series": "SERIES",
              "classe": "CLASSEE", "records": "RECORDS"}
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


class EcranEnLigneBase(Navigation, EcranBase):
    """
    Écran en ligne : fond synthwave assombri et titre. Depuis la 2.1, un écran
    qui définit « onglet » (ex. "CLASSEMENTS", ou "" pour le profil) affiche la
    barre des menus à la place du titre, et Échap ramène à l'accueil.
    """

    titre = "EN LIGNE"
    onglet = None

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        if self.onglet is not None:
            self.naviguer()

    def retour_accueil(self):
        from ecrans.titre import EcranTitre
        self.app.remplacer(EcranTitre(self.app), transition=False)

    def dessiner_fond(self, image, titre=None):
        from ecrans.menus import fond_menu, marge_haut
        fond_menu(self.app, image, 150)
        if self.onglet is not None:
            self.dessiner_barre(image)
            return
        haut = marge_haut()
        dessiner_texte(image, titre or self.titre, config.LARGEUR / 2, 50 + haut, 5, config.CYAN)
        en_ligne = self.app.en_ligne
        if en_ligne.connecte and config.LARGEUR > config.HAUTEUR:
            dessiner_texte(image, f"{en_ligne.pseudo.upper()}  RANG {en_ligne.niveau}",
                           config.LARGEUR - 20, 22, 2, couleur_profil(en_ligne.couleur),
                           ancrage="droite", lueur=False)

    def pied(self, image, texte):
        """But : rappel des touches en bas (pas au doigt ni au format vertical)."""
        if self.app.entrees.tactile or config.HAUTEUR > config.LARGEUR:
            return
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
        if config.EST_WEB and entrees.tactile and 1 in entrees.clics \
                and self.rect.collidepoint(entrees.souris):
            # Téléphone : pas de clavier physique, on ouvre celui du navigateur.
            from moteur import web
            reponse = web.demander_texte(self.libelle, "" if self.masque else self.valeur)
            if reponse is not None:
                self.valeur = "".join(c for c in reponse if c.isprintable() and (
                    self.autorises is None or c in self.autorises))[:self.maximum]
            entrees.clics.discard(1)
            return
        for caractere in entrees.texte:
            if len(self.valeur) >= self.maximum or not caractere.isprintable():
                continue
            if self.autorises is not None and caractere not in self.autorises:
                continue
            self.valeur += caractere
        if pygame.KSCAN_BACKSPACE in entrees.appuis:
            self.valeur = self.valeur[:-1]

    def dessiner(self, image, x, y, largeur, actif, temps, grand=False):
        """
        But : cadre néon, libellé au-dessus, texte et curseur clignotant.
        Entrée : grand (bool) : version plus haute et plus lisible (téléphone).
        """
        self.rect = pygame.Rect(int(x - largeur / 2), int(y), int(largeur), 64 if grand else 48)
        couleur = config.CYAN if actif else (110, 80, 160)
        dessiner_texte(image, self.libelle, self.rect.x, y - (24 if grand else 16), 3 if grand else 2,
                       GRIS, ancrage="gauche", lueur=False)
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
        zone = dessiner_texte(image, affiche, self.rect.x + 16, self.rect.centery, 4 if grand else 3,
                              config.BLANC, ancrage="gauche", lueur=False)
        if actif and int(temps * 2) % 2 == 0:
            x_curseur = zone.right + 4 if self.valeur else self.rect.x + 18
            image.fill(config.CYAN, (x_curseur, self.rect.y + 10, 3, self.rect.h - 20))
