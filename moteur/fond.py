# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Fond synthwave procédural animé, dans l'esprit de data/fond.png :
    ciel dégradé étoilé, soleil rayé, montagnes filaires, grille néon en
    perspective qui défile vers le joueur (plus vite quand le combo monte).

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Thèmes par monde (Neon City : immeubles, Cyber Core : circuits).
"""

import math
import random

import pygame

from moteur import config
from moteur.rendu import figer, halo_cercle, melanger, attenuer

HORIZON = 430
POINT_FUITE_X = config.LARGEUR // 2
PROFONDEUR_K = config.HAUTEUR - HORIZON     # d = 1 -> bas de l'écran
NB_LIGNES_PROFONDEUR = 26

# Thèmes des trois mondes de la campagne (+ 0 : menus).
PALETTES = {
    1: {"grille": config.ROSE, "grille2": config.CYAN,
        "soleil_haut": (255, 236, 110), "soleil_bas": (255, 60, 120),
        "ciel": (config.CIEL_HAUT, config.CIEL_MILIEU, config.CIEL_HORIZON)},
    2: {"grille": config.CYAN, "grille2": config.BLEU,
        "soleil_haut": (120, 255, 255), "soleil_bas": (120, 60, 255),
        "ciel": ((2, 4, 24), (20, 30, 110), (0, 170, 220))},
    3: {"grille": config.VERT, "grille2": config.VIOLET,
        "soleil_haut": (255, 120, 255), "soleil_bas": (255, 40, 60),
        "ciel": ((8, 0, 8), (60, 0, 50), (200, 20, 80))},
}


class FondSynthwave:
    """
    Fond animé. Attributs principaux :
        defilement (float) : position de la grille (0..1, cyclique).
        vitesse (float) : vitesse de défilement (cases par seconde).
        progression (float 0..1) : le soleil descend avec l'avancée du niveau.
        palette : couleurs (grille 1, grille 2, soleil haut, soleil bas).
    """

    def __init__(self, palette=None):
        """
        But : pré-calculer ciel, soleil, montagnes et étoiles.
        Entrée : palette (dict ou None) : couleurs du thème.
        Sortie : aucune.
        """
        self.palette = palette or PALETTES[1]
        self.monde = 1
        self.temps = 0.0
        self.defilement = 0.0
        self.vitesse = 0.8
        self.vitesse_cible = 0.8
        self.progression = 0.0
        self.ciel = self._creer_ciel()
        self.soleil = self._creer_soleil(150)
        self._soleils_rayes = {}
        self.montagnes = self._creer_montagnes()
        aleatoire = random.Random(7)
        self.etoiles = [(aleatoire.randint(0, config.LARGEUR),
                         aleatoire.randint(0, HORIZON - 60),
                         aleatoire.uniform(0, 6.28),
                         aleatoire.choice((1, 1, 1, 2)))
                        for _ in range(150)]
        self.sol = self._creer_sol()

    def changer_monde(self, monde):
        """
        But : appliquer le thème de couleurs d'un monde (1, 2 ou 3).
        Entrée : monde (int). Sortie : aucune.
        """
        if monde == self.monde or monde not in PALETTES:
            return
        self.monde = monde
        self.palette = PALETTES[monde]
        self.ciel = self._creer_ciel()
        self.soleil = self._creer_soleil(150)
        self._soleils_rayes = {}

    # --- Pré-calculs -------------------------------------------------------

    def _creer_ciel(self):
        """
        But : dégradé vertical du ciel jusqu'à l'horizon.
        Entrée : aucune. Sortie : (Surface).
        """
        haut, milieu, bas = self.palette["ciel"]
        ciel = pygame.Surface((config.LARGEUR, HORIZON))
        for y in range(HORIZON):
            t = y / HORIZON
            if t < 0.55:
                couleur = melanger(haut, milieu, t / 0.55)
            else:
                couleur = melanger(milieu, bas, ((t - 0.55) / 0.45) ** 1.6)
            pygame.draw.line(ciel, couleur, (0, y), (config.LARGEUR, y))
        return ciel

    def _creer_soleil(self, rayon):
        """
        But : disque en dégradé (jaune en haut, rose en bas).
        Entrée : rayon (int). Sortie : (Surface SRCALPHA).
        """
        soleil = pygame.Surface((rayon * 2, rayon * 2), pygame.SRCALPHA)
        for y in range(rayon * 2):
            demi = math.sqrt(max(0, rayon * rayon - (y - rayon) ** 2))
            couleur = melanger(self.palette["soleil_haut"],
                               self.palette["soleil_bas"], y / (rayon * 2))
            pygame.draw.line(soleil, couleur, (rayon - demi, y),
                             (rayon + demi, y))
        return soleil

    def _creer_montagnes(self):
        """
        But : deux chaînes de montagnes filaires (gauche et droite).
        Entrée : aucune. Sortie : (Surface SRCALPHA) posée sur l'horizon.
        """
        hauteur = 170
        surface = pygame.Surface((config.LARGEUR, hauteur), pygame.SRCALPHA)
        aleatoire = random.Random(42)
        for cote in (-1, 1):
            points = []
            nb = 14
            for i in range(nb + 1):
                t = i / nb
                x = POINT_FUITE_X + cote * (330 + t * 330)
                pic = hauteur - (20 + t * 120 + aleatoire.uniform(-25, 35))
                points.append((x, max(4, pic)))
            polygone = [(POINT_FUITE_X + cote * 300, hauteur)] + points + \
                       [(points[-1][0], hauteur)]
            pygame.draw.polygon(surface, (14, 4, 40, 255), polygone)
            # Arêtes filaires : contour + lignes vers la base.
            pygame.draw.lines(surface, (*config.CYAN, 220), False, points, 2)
            for i, (x, y) in enumerate(points):
                if i % 2 == 0:
                    pygame.draw.line(surface, (*config.BLEU, 120), (x, y),
                                     (x + cote * 40, hauteur), 1)
                if i > 0:
                    px, py = points[i - 1]
                    pygame.draw.line(surface, (*config.VIOLET, 90),
                                     ((x + px) / 2, (y + py) / 2 + 30),
                                     (x, y), 1)
        return figer(surface)

    def _creer_sol(self):
        """
        But : dégradé sombre du sol sous l'horizon.
        Entrée : aucune. Sortie : (Surface).
        """
        hauteur = config.HAUTEUR - HORIZON
        sol = pygame.Surface((config.LARGEUR, hauteur))
        for y in range(hauteur):
            couleur = melanger((40, 6, 70), (8, 0, 20), (y / hauteur) ** 0.6)
            pygame.draw.line(sol, couleur, (0, y), (config.LARGEUR, y))
        return sol

    # --- Animation ---------------------------------------------------------

    def mettre_a_jour(self, dt):
        """
        But : faire défiler la grille et scintiller les étoiles.
        Entrée : dt (float) secondes. Sortie : aucune.
        """
        self.temps += dt
        self.vitesse += (self.vitesse_cible - self.vitesse) * min(1, dt * 2)
        self.defilement = (self.defilement + self.vitesse * dt) % 1.0

    def dessiner(self, ecran):
        """
        But : dessiner tout le fond.
        Entrée : ecran (Surface). Sortie : aucune.
        """
        ecran.blit(self.ciel, (0, 0))
        self._dessiner_etoiles(ecran)
        self._dessiner_soleil(ecran)
        ecran.blit(self.montagnes, (0, HORIZON - self.montagnes.get_height()))
        ecran.blit(self.sol, (0, HORIZON))
        self._dessiner_grille(ecran)

    def _dessiner_etoiles(self, ecran):
        """Étoiles qui scintillent (luminosité sinusoïdale)."""
        for x, y, phase, taille in self.etoiles:
            lumiere = 0.45 + 0.55 * math.sin(self.temps * 2.2 + phase) ** 2
            couleur = attenuer((230, 210, 255), lumiere)
            ecran.fill(couleur, (x, y, taille, taille))
            if taille == 2 and lumiere > 0.9:
                ecran.fill(attenuer(couleur, 0.5), (x - 2, y, 6, 1))
                ecran.fill(attenuer(couleur, 0.5), (x, y - 2, 1, 6))

    def _dessiner_soleil(self, ecran):
        """Soleil rayé : les bandes vides descendent lentement."""
        rayon = self.soleil.get_width() // 2
        centre_y = HORIZON - 80 + int(self.progression * 90)
        lueur = halo_cercle(rayon, attenuer(self.palette["soleil_bas"], 0.7),
                            rayon=40)
        ecran.blit(lueur, lueur.get_rect(center=(POINT_FUITE_X, centre_y)),
                   special_flags=pygame.BLEND_RGB_ADD)
        soleil = self._soleil_raye(rayon, int((self.temps * 12) % 20))
        zone = soleil.get_rect(center=(POINT_FUITE_X, centre_y))
        # On coupe ce qui dépasse sous l'horizon.
        visible = HORIZON - zone.top
        if visible > 0:
            ecran.blit(soleil, zone.topleft,
                       (0, 0, zone.width, min(zone.height, visible)))

    def _soleil_raye(self, rayon, decalage):
        """
        But : soleil avec ses bandes horizontales transparentes, plus épaisses vers
        le bas, décalées de 0 à 19 px (elles descendent lentement). Les 20 images
        sont gardées en cache, compressées (copie rapide, surtout dans le navigateur).
        Entrées : rayon (int) ; decalage (int 0..19). Sortie : (Surface SRCALPHA).
        """
        soleil = self._soleils_rayes.get(decalage)
        if soleil is None:
            soleil = self.soleil.copy()
            debut = rayon * 0.45
            y = debut + decalage
            while y < rayon * 2:
                epaisseur = 1 + (y - debut) / (rayon * 2 - debut) * 11
                soleil.fill((0, 0, 0, 0), (0, int(y), rayon * 2, int(epaisseur)))
                y += 20
            self._soleils_rayes[decalage] = soleil = figer(soleil)
        return soleil

    def _dessiner_grille(self, ecran):
        """Grille en perspective : lignes de fuite + lignes de profondeur."""
        couleur_a = self.palette["grille"]
        couleur_b = self.palette["grille2"]
        bas = config.HAUTEUR
        # Lignes de profondeur (horizontales) qui avancent vers le joueur.
        for n in range(NB_LIGNES_PROFONDEUR):
            distance = n + 1 - self.defilement
            if distance <= 0.05:
                continue
            y = HORIZON + PROFONDEUR_K / distance
            if y > bas:
                continue
            proximite = 1 - min(1.0, distance / NB_LIGNES_PROFONDEUR)
            couleur = attenuer(melanger(couleur_b, couleur_a, proximite),
                               0.25 + 0.75 * proximite)
            epaisseur = 1 if proximite < 0.7 else 2
            pygame.draw.line(ecran, attenuer(couleur, 0.35), (0, int(y) + 1),
                             (config.LARGEUR, int(y) + 1), epaisseur + 2)
            pygame.draw.line(ecran, couleur, (0, int(y)),
                             (config.LARGEUR, int(y)), epaisseur)
        # Lignes de fuite (vers le point central de l'horizon).
        for i in range(-16, 17):
            x_bas = POINT_FUITE_X + i * 110
            couleur = melanger(couleur_a, couleur_b, abs(i) / 16)
            pygame.draw.line(ecran, attenuer(couleur, 0.35),
                             (POINT_FUITE_X + i * 6, HORIZON), (x_bas, bas), 4)
            pygame.draw.line(ecran, couleur,
                             (POINT_FUITE_X + i * 6, HORIZON), (x_bas, bas), 2)
        # Ligne d'horizon brillante.
        pygame.draw.line(ecran, attenuer(couleur_a, 0.6), (0, HORIZON + 1),
                         (config.LARGEUR, HORIZON + 1), 5)
        pygame.draw.line(ecran, (255, 200, 255), (0, HORIZON),
                         (config.LARGEUR, HORIZON), 2)
