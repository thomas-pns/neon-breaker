# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Catalogue de tous les effets (bonus, malus, pouvoirs stockables) et
    capsules qui tombent des briques. Code couleur : vert = bonus,
    rouge = malus, doré = pouvoir à stocker dans l'inventaire.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Capsules rares « jackpot », capsule mystère.
"""

import math
import random

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from moteur.rendu import halo_rect, attenuer, melanger

VERT_BONUS = (60, 255, 140)
ROUGE_MALUS = (255, 60, 90)
OR_POUVOIR = (255, 205, 60)
COULEURS_CATEGORIE = {"bonus": VERT_BONUS, "malus": ROUGE_MALUS,
                      "pouvoir": OR_POUVOIR}


class Effet:
    """
    Description d'un effet.
    Attributs : code (str), nom (str), categorie ("bonus"/"malus"/"pouvoir"),
    lettre (str), duree (float, 0 = instantané), poids (int : fréquence
    relative dans sa catégorie), description (str : pour l'écran d'aide).
    """

    def __init__(self, code, nom, categorie, lettre, duree, poids, description):
        self.code = code
        self.nom = nom
        self.categorie = categorie
        self.lettre = lettre
        self.duree = duree
        self.poids = poids
        self.description = description

    def couleur(self):
        """But : couleur de la catégorie. Sortie : (tuple RVB)."""
        return COULEURS_CATEGORIE[self.categorie]


CATALOGUE = {e.code: e for e in [
    # --- Bonus : effet immédiat ---
    Effet("elargir", "ELARGIR", "bonus", "E", 15, 4, "RAQUETTE +50 %"),
    Effet("multi", "MULTI-BALLE", "bonus", "M", 0, 4, "DIVISE CHAQUE BALLE EN 3"),
    Effet("feu", "BALLE DE FEU", "bonus", "F", 8, 3, "TRAVERSE TOUT + METAL"),
    Effet("ralenti", "RALENTI", "bonus", "S", 12, 3, "BALLES -35 %"),
    Effet("aimant", "AIMANT", "bonus", "A", 0, 3, "LA BALLE COLLE (5 PRISES)"),
    Effet("filet", "FILET", "bonus", "N", 0, 3, "SAUVE UNE BALLE UNE FOIS"),
    Effet("vie", "VIE", "bonus", "+", 0, 1, "UNE VIE EN PLUS"),
    # --- Malus ---
    Effet("retrecir", "RETRECIR", "malus", "R", 12, 4, "RAQUETTE -40 %"),
    Effet("vitesse", "TURBO", "malus", "V", 10, 4, "BALLES +40 %"),
    Effet("inversion", "INVERSION", "malus", "I", 8, 3, "COMMANDES INVERSEES"),
    Effet("brouillard", "BROUILLARD", "malus", "B", 8, 3, "ON NE VOIT PRESQUE RIEN"),
    Effet("glace", "GLACE", "malus", "G", 10, 3, "RAQUETTE QUI GLISSE"),
    Effet("fantome", "BALLE FANTOME", "malus", "X", 6, 3, "BALLE PRESQUE INVISIBLE"),
    # --- Pouvoirs à stocker (inventaire) ---
    Effet("laser", "LASER", "pouvoir", "L", 5, 4, "DEUX CANONS PENDANT 5 S"),
    Effet("bouclier", "BOUCLIER", "pouvoir", "D", 10, 3, "MUR D'ENERGIE 10 S"),
    Effet("onde", "ONDE DE CHOC", "pouvoir", "O", 0, 3, "FRAPPE 3 LIGNES PROCHES"),
    Effet("bombe", "BOMBE", "pouvoir", "K", 0, 3, "BRIQUE SUIVANTE : BOUM"),
    Effet("chrono", "CHRONO", "pouvoir", "T", 4, 3, "TEMPS RALENTI, PAS TOI"),
    Effet("guidage", "GUIDAGE", "pouvoir", "H", 6, 3, "LA BALLE VISE LES BRIQUES"),
]}


def tirer_effet(poids_categories=None, aleatoire=random):
    """
    But : tirer au sort un effet selon les poids des catégories puis des
    effets.
    Entrées : poids_categories (dict catégorie -> poids, None = défaut) ;
              aleatoire (module ou Random).
    Sortie : (str) code de l'effet, ou None si aucune catégorie possible.
    """
    poids = poids_categories or config.POIDS_CATEGORIES
    categories = [c for c, p in poids.items() if p > 0]
    if not categories:
        return None
    categorie = aleatoire.choices(categories, [poids[c] for c in categories])[0]
    effets = [e for e in CATALOGUE.values() if e.categorie == categorie]
    return aleatoire.choices(effets, [e.poids for e in effets])[0].code


class Capsule:
    """
    Capsule qui tombe (sens = +1) ou monte (sens = -1, joueur du haut en Duel).
    Attributs : x, y (centre), code (str), sens (int), joueur_cible (Joueur
    ou None : en Duel, la capsule va vers celui qui a cassé la brique),
    temps (float), largeur, hauteur.
    """

    largeur = 40
    hauteur = 16

    def __init__(self, x, y, code, sens=1, joueur_cible=None):
        self.x = x
        self.y = y
        self.code = code
        self.sens = sens
        self.joueur_cible = joueur_cible
        self.temps = random.uniform(0, 3)

    def effet(self):
        """But : description de l'effet. Sortie : (Effet)."""
        return CATALOGUE[self.code]

    def rect(self):
        """But : rectangle de collision. Sortie : (pygame.Rect)."""
        return pygame.Rect(int(self.x - self.largeur / 2),
                           int(self.y - self.hauteur / 2),
                           self.largeur, self.hauteur)

    def mettre_a_jour(self, dt):
        """But : faire tomber la capsule. Entrée : dt (float)."""
        self.temps += dt
        self.y += config.VITESSE_CAPSULE * self.sens * dt

    def dessiner(self, image):
        """
        But : pilule néon qui tourne (écrasement horizontal sinusoïdal)
        avec l'icône en pixel art de l'effet (moteur/icones.py).
        Entrée : image (Surface). Sortie : aucune.
        """
        from moteur.icones import dessiner_icone
        effet = self.effet()
        couleur = effet.couleur()
        rotation = abs(math.cos(self.temps * 3))
        # Dessin un peu plus grand que la zone de collision, pour que l'icône se lise.
        largeur_dessin, hauteur_dessin = 46, 24
        largeur = max(6, int(largeur_dessin * (0.3 + 0.7 * rotation)))
        rect = pygame.Rect(0, 0, largeur, hauteur_dessin)
        rect.center = (int(self.x), int(self.y))
        lueur = halo_rect(largeur_dessin, hauteur_dessin, attenuer(couleur, 0.7), rayon=6)
        image.blit(lueur, (int(self.x - largeur_dessin / 2) - 12, rect.y - 12),
                   special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.rect(image, melanger((20, 0, 40), couleur, 0.25), rect, border_radius=10)
        pygame.draw.rect(image, couleur, rect, 2, border_radius=10)
        if rotation > 0.35:
            icone = melanger(couleur, (255, 255, 255), 0.35)
            if not dessiner_icone(image, effet.code, rect.center, icone, 2,
                                  largeur=int(20 * min(1.0, rotation * 1.3))):
                dessiner_texte(image, effet.lettre, rect.centerx, rect.centery + 1,
                               2, config.BLANC, lueur=False, ombre=False)
