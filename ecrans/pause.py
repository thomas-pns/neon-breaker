# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Menu pause, posé par-dessus l'écran de partie (écran transparent de la
    Pile) : reprendre, recommencer, aide, options (volumes...), menu principal, quitter.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

"""

import math

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from ecrans.base import EcranBase, MenuVertical, voile
from ecrans.hud import panneau


class EcranPause(EcranBase):
    """Pause : la partie reste visible, assombrie, et ne bouge plus."""

    vertical = True               # dessiné aussi au format vertical (téléphone)

    transparent = True
    attenuer_musique = True

    def musique(self):
        return self.partie.musique()

    def __init__(self, app, partie):
        super().__init__(app)
        self.partie = partie
        self.menu = MenuVertical([
            ("REPRENDRE", self._reprendre),
            ("RECOMMENCER", self.partie.recommencer),
            ("AIDE", self._aide),
            ("OPTIONS", self._options),
            ("ACCUEIL", self._menu),
        ] + ([] if config.EST_WEB else [("QUITTER", self._quitter)]),
            config.LARGEUR / 2, 290, 3, 50)

    def _reprendre(self):
        self.app.depiler()

    def _aide(self):
        from ecrans.aide import EcranAide
        self.app.empiler(EcranAide(self.app))

    def _options(self):
        from ecrans.options import EcranOptions
        self.app.empiler(EcranOptions(self.app))

    def reprendre(self):
        self.app.entrees.debut_image()

    def _menu(self):
        from ecrans.titre import EcranTitre
        self.app.remplacer(EcranTitre(self.app))

    def _quitter(self):
        self.app.en_marche = False

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        if self.app.entrees.vient_d_appuyer("pause"):
            self.app.audio.jouer("pause")
            self._reprendre()
            return
        self.menu.mettre_a_jour(dt, self.app.entrees, self.app.audio)

    def dessiner(self, image):
        voile(image, 150)
        cadre = pygame.Rect(0, 0, 480, 430)
        cadre.center = (config.LARGEUR / 2, 385)
        if config.HAUTEUR > config.LARGEUR:  # téléphone : grand, au milieu de l'écran
            _, ecart, _ = self.menu.mise_en_page()
            cadre = pygame.Rect(0, 0, config.LARGEUR - 60, 170 + ecart * len(self.menu.options))
            cadre.center = (config.LARGEUR / 2, config.HAUTEUR / 2)
        self.menu.x, self.menu.y = config.LARGEUR / 2, cadre.y + (150 if config.HAUTEUR > config.LARGEUR
                                                                   else 120)
        panneau(image, cadre, config.ROSE)
        decalage = math.sin(self.temps * 3) * 3
        dessiner_texte(image, "PAUSE", config.LARGEUR / 2, cadre.y + 52 + decalage, 6, config.ROSE)
        self.menu.dessiner(image)
