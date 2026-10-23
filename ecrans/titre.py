# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Écran titre : fond.png du projet d'origine en parallaxe, logo NEON
    BREAKER qui pulse, menu principal (Jouer, En ligne, Scores, Aide, Options, Quitter).

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Démo automatique après 15 s, crédits.
"""

import math
import os

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from moteur.rendu import attenuer
from moteur.version import VERSION
from ecrans.base import EcranBase, MenuVertical


def texte_version():
    """
    But : texte de la version affichée en bas à droite de l'écran titre.
    Entrée : aucune. Sortie : (str) ex. « V1.1.0 ».
    """
    return f"V{VERSION}"


class EcranTitre(EcranBase):
    """Menu principal."""

    def __init__(self, app):
        super().__init__(app)
        self.image_fond = self._charger_fond()
        self.menu = MenuVertical([], config.LARGEUR / 2, 350, 3, 46)
        self._construire_menu()

    @staticmethod
    def _charger_fond():
        """Image du projet d'origine, agrandie pour couvrir 1280x720 (+ marge)."""
        if not os.path.exists(config.CHEMIN_FOND):
            return None
        image = pygame.image.load(config.CHEMIN_FOND).convert()
        return pygame.transform.smoothscale(image, (1360, 1020))

    def _construire_menu(self):
        """(Re)crée les libellés, qui affichent l'état des réglages."""
        indice = self.menu.indice
        self.menu.options = [
            ("JOUER", self._jouer),
            (self._libelle_en_ligne(), self._en_ligne),
            ("MEILLEURS SCORES", self._scores),
            ("AIDE", self._aide),
            ("OPTIONS", self._options),
            ("QUITTER", self._quitter),
        ]
        self.menu.indice = indice

    def _libelle_en_ligne(self):
        en_ligne = self.app.en_ligne
        if en_ligne.jeton:
            return f"EN LIGNE : {en_ligne.pseudo.upper()}"
        return "EN LIGNE"

    def _en_ligne(self):
        if self.app.en_ligne.jeton:
            from ecrans.en_ligne.hub import EcranHub
            self.app.remplacer(EcranHub(self.app))
        else:
            from ecrans.en_ligne.connexion import EcranConnexion
            self.app.remplacer(EcranConnexion(self.app))

    def _jouer(self):
        from ecrans.modes import EcranModes
        self.app.remplacer(EcranModes(self.app))

    def _scores(self):
        from ecrans.scores import EcranScores
        self.app.remplacer(EcranScores(self.app))

    def _aide(self):
        from ecrans.aide import EcranAide
        self.app.remplacer(EcranAide(self.app))

    def _options(self):
        from ecrans.options import EcranOptions
        self.app.empiler(EcranOptions(self.app))

    def _quitter(self):
        self.app.en_marche = False

    def reprendre(self):
        self.app.entrees.debut_image()
        self._construire_menu()

    def entrer(self):
        self.app.fond.changer_monde(1)
        self.app.fond.progression = 0.0
        self.app.fond.vitesse_cible = 0.8

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        if self.app.entrees.vient_d_appuyer("retour"):
            self._quitter()
            return
        self.menu.mettre_a_jour(dt, self.app.entrees, self.app.audio)

    def dessiner(self, image):
        # Parallaxe : le fond suit doucement la souris et ondule.
        if self.image_fond is not None:
            sx, sy = self.app.entrees.souris
            dx = -40 - (sx / config.LARGEUR - 0.5) * 50
            dy = -200 - (sy / config.HAUTEUR - 0.5) * 30 + math.sin(self.temps * 0.5) * 6
            image.blit(self.image_fond, (dx, dy))
        else:
            self.app.fond.dessiner(image)
        sombre = pygame.Surface(image.get_size())
        sombre.fill((10, 0, 30))
        sombre.set_alpha(110)
        image.blit(sombre, (0, 0))

        # Logo : ombre rose décalée + texte cyan qui respire.
        pulse = 0.85 + 0.15 * math.sin(self.temps * 2.4)
        y_logo = 140 + math.sin(self.temps * 1.3) * 6
        dessiner_texte(image, "NEON", config.LARGEUR / 2 + 6, y_logo - 50 + 6, 12,
                       attenuer(config.ROSE, 0.9), lueur=False, ombre=False)
        dessiner_texte(image, "NEON", config.LARGEUR / 2, y_logo - 50, 12,
                       attenuer(config.CYAN, pulse))
        dessiner_texte(image, "BREAKER", config.LARGEUR / 2 + 5, y_logo + 65 + 5, 9,
                       attenuer(config.VIOLET, 0.9), lueur=False, ombre=False)
        dessiner_texte(image, "BREAKER", config.LARGEUR / 2, y_logo + 65, 9,
                       attenuer(config.AMBRE, pulse))
        largeur_ligne = int(420 + 40 * math.sin(self.temps * 2))
        pygame.draw.line(image, config.ROSE,
                         (config.LARGEUR / 2 - largeur_ligne / 2, y_logo + 125),
                         (config.LARGEUR / 2 + largeur_ligne / 2, y_logo + 125), 3)

        self.menu.dessiner(image)
        if config.EST_TEST:
            dessiner_texte(image, "VERSION DE TEST", config.LARGEUR - 16,
                           config.HAUTEUR - 78, 2, config.AMBRE, ancrage="droite", lueur=False)
            dessiner_texte(image, "SCORES NON ENVOYES", config.LARGEUR - 16, config.HAUTEUR - 56,
                           2, config.AMBRE, ancrage="droite", lueur=False)
        dessiner_texte(image, texte_version(), config.LARGEUR - 16, config.HAUTEUR - 30,
                       2, (150, 120, 200), ancrage="droite", lueur=False)
        dessiner_texte(image, "THOMAS CHASSANIS PONS & CAMIL BOUZIRI  -  CPE 3A",
                       config.LARGEUR / 2, config.HAUTEUR - 30, 2,
                       (150, 120, 200), lueur=False)

