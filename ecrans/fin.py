# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Écran de fin de partie : GAME OVER avec effet « glitch » ou VICTOIRE
    avec feu d'artifice néon, statistiques, top 10 du mode (la ligne du
    joueur clignote), rejouer ou menu.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Générique de fin de campagne.
"""

import math
import random

import pygame

from moteur import config
from moteur.effets import GestionnaireEffets
from moteur.police_pixel import dessiner_texte, rendre_texte
from ecrans.base import EcranBase, MenuVertical, voile
from ecrans.hud import panneau


class EcranFin(EcranBase):
    """
    Attributs : resultat (dict rempli par le mode), fabrique (pour rejouer),
    rang (int ou None) : place obtenue dans le top 10.
    """

    vertical = True               # dessiné aussi au format vertical (téléphone)
    bouton_retour = False         # au doigt : REJOUER / ACCUEIL suffisent

    def musique(self):
        return None                     # silence : jingle de victoire / game over

    def __init__(self, app, resultat, fabrique, rang=None):
        super().__init__(app)
        self.resultat = resultat
        self.fabrique = fabrique
        self.rang = rang
        self.victoire = resultat["victoire"]
        self.effets = GestionnaireEffets()
        self.prochain_feu = 0.0
        self.menu = MenuVertical([("REJOUER", self._rejouer),
                                  ("ACCUEIL", self._menu)],
                                 config.LARGEUR / 2, 610, 3, 46)

    def entrer(self):
        self.app.audio.jouer("victoire" if self.victoire else "game_over")
        self.app.fond.progression = 0.0 if self.victoire else 0.6

    def _rejouer(self):
        from ecrans.partie import EcranPartie
        self.app.remplacer(EcranPartie(self.app, self.fabrique))

    def _menu(self):
        from ecrans.titre import EcranTitre
        self.app.remplacer(EcranTitre(self.app))

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        self.effets.mettre_a_jour(dt)
        self.app.fond.vitesse_cible = 0.3 if not self.victoire else 1.5
        if self.victoire:
            self.prochain_feu -= dt
            if self.prochain_feu <= 0:
                self.prochain_feu = random.uniform(0.25, 0.6)
                x = random.uniform(150, config.LARGEUR - 150)
                y = random.uniform(80, 280)
                self.effets.explosion(x, y, random.choice(config.COULEURS_NEON),
                                      40, 420, taille=3, vie=1.3, gravite=220)
                self.effets.onde(x, y, config.BLANC, 90, 0.4, 3)
        if self.temps > 0.8:
            self.menu.mettre_a_jour(dt, self.app.entrees, self.app.audio)

    def dessiner(self, image):
        self.app.fond.dessiner(image)
        voile(image, 140)
        self.effets.dessiner(image)
        titre = self.resultat["titre"]
        vertical = config.HAUTEUR > config.LARGEUR       # téléphone : tout l'un sous l'autre
        y_titre = int(config.HAUTEUR * 0.12) if vertical else 100
        echelle = 9 if len(titre) < 11 else 7
        while vertical and len(titre) * 6 * echelle > config.LARGEUR - 40 and echelle > 3:
            echelle -= 1
        if self.victoire:
            pulse = 0.5 + 0.5 * math.sin(self.temps * 4)
            couleur = self.resultat.get("couleur", (255, int(176 + 60 * pulse), int(80 * pulse)))
            dessiner_texte(image, titre, config.LARGEUR / 2, y_titre, echelle, couleur)
        else:
            self._titre_glitch(image, titre, y_titre, echelle)

        avec_top = self.a_un_top()
        largeur = 500
        cadre = pygame.Rect(0, 0, largeur, 360)
        pas, taille = 40, 2
        if vertical:
            # Téléphone : cadre plus large, assez haut pour toutes les lignes, textes plus gros.
            pas, taille = 52, 3
            cadre.size = (min(700, config.LARGEUR - 40), 200 + pas * len(self.resultat["lignes"]))
            cadre.midtop = (config.LARGEUR / 2, y_titre + 70)
        elif avec_top:
            cadre.midright = (config.LARGEUR / 2 - 20, 380)
        else:
            cadre.center = (config.LARGEUR / 2, 380)
        panneau(image, cadre, config.ROSE if not self.victoire else config.AMBRE)
        dessiner_texte(image, "SCORE FINAL", cadre.centerx, cadre.y + 34, 2,
                       (170, 140, 220), lueur=False)
        dessiner_texte(image, f"{self.resultat['score']:07d}", cadre.centerx,
                       cadre.y + 80, 6, config.AMBRE)
        if self.rang == 0 and math.sin(self.temps * 7) > -0.2:
            dessiner_texte(image, "NOUVEAU RECORD !", cadre.centerx, cadre.y + 130, 3,
                           config.ROSE)
        for i, (libelle, valeur) in enumerate(self.resultat["lignes"]):
            y = cadre.y + 190 + i * pas
            dessiner_texte(image, libelle, cadre.x + 40, y, taille, config.CYAN,
                           ancrage="gauche", lueur=False)
            dessiner_texte(image, valeur, cadre.right - 40, y, taille, config.BLANC,
                           ancrage="droite", lueur=False)
        if avec_top and vertical:
            bas_menu = config.HAUTEUR - 230 - config.MARGE_BAS_ECRAN - 62
            self._dessiner_top(image, pygame.Rect(cadre.x, cadre.bottom + 24,
                                                  cadre.w, min(360, bas_menu - cadre.bottom - 24)))
        elif avec_top:
            self._dessiner_top(image, pygame.Rect(config.LARGEUR / 2 + 20, cadre.y,
                                                  420, cadre.h))
        self.menu.x = config.LARGEUR / 2
        self.menu.y = config.HAUTEUR - 230 - config.MARGE_BAS_ECRAN if vertical else 610
        if self.temps > 0.8:
            self.menu.dessiner(image)

    def a_un_top(self):
        """But : faut-il un panneau à droite (top 10 local du mode) ?"""
        mode = self.resultat["mode"]
        return bool(mode in self.app.donnees.get("classements", {}) and self.app.classement(mode))

    def _dessiner_top(self, image, cadre):
        """Top 10 du mode ; la ligne obtenue clignote."""
        panneau(image, cadre, config.CYAN)
        dessiner_texte(image, f"TOP 10  {self.resultat['mode'].upper()}", cadre.centerx,
                       cadre.y + 28, 2, config.CYAN)
        for i, entree in enumerate(self.app.classement(self.resultat["mode"])):
            y = cadre.y + 64 + i * 28
            if y > cadre.bottom - 14:           # téléphone : seulement les lignes qui tiennent
                break
            couleur = config.BLANC
            if i == self.rang:
                couleur = config.AMBRE if int(self.temps * 6) % 2 else config.ROSE
            dessiner_texte(image, f"{i + 1:2d}. {entree['nom']}", cadre.x + 40, y, 2,
                           couleur, ancrage="gauche", lueur=False)
            dessiner_texte(image, f"{entree['score']:07d}", cadre.right - 40, y, 2, couleur,
                           ancrage="droite", lueur=False)

    def _titre_glitch(self, image, texte, y, echelle=9):
        """
        But : titre découpé en tranches horizontales décalées au hasard,
        avec copies rouge et cyan séparées (signal vidéo abîmé).
        """
        surface = rendre_texte(texte, echelle, config.ROUGE)
        rect = surface.get_rect(center=(config.LARGEUR / 2, y))
        intense = random.random() < 0.12
        for couleur, decalage in ((config.CYAN, -4), (config.ROSE, 4)):
            fantome = rendre_texte(texte, echelle, couleur, ombre=False, lueur=False).copy()
            fantome.set_alpha(110)
            image.blit(fantome, fantome.get_rect(
                center=(rect.centerx + decalage * (3 if intense else 1), y)))
        hauteur_tranche = 8
        for haut in range(0, rect.h, hauteur_tranche):
            dx = random.randint(-14, 14) if (intense or random.random() < 0.06) else 0
            image.blit(surface, (rect.x + dx, rect.y + haut),
                       (0, haut, rect.w, hauteur_tranche))
