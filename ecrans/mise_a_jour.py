# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Écran « nouvelle version disponible » : télécharger et redémarrer, ou
    plus tard. La mise à jour tourne dans un fil, avec une barre de
    progression ; en cas d'échec, on affiche l'adresse de téléchargement.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import threading

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from moteur.version import VERSION
from ecrans.base import EcranBase, MenuVertical, voile
from ecrans.hud import panneau, barre


class EcranMiseAJour(EcranBase):
    """Attributs : infos (dict), etat ("choix", "telechargement", "fini", "erreur")."""

    transparent = True

    def __init__(self, app, infos):
        super().__init__(app)
        self.infos = infos
        self.etat = "choix"
        self.progression = 0.0
        self.erreur = ""
        options = [("PLUS TARD", self.app.depiler)]
        if config.EST_WEB:
            options.insert(0, ("RECHARGER LA PAGE", self._recharger))
        elif infos.get("auto"):
            options.insert(0, ("METTRE A JOUR", self._lancer))
        self.menu = MenuVertical(options, config.LARGEUR / 2, 430, 3, 50)

    def _recharger(self):
        """Version web : la nouvelle version est déjà sur le serveur, il suffit de recharger."""
        from moteur import web
        web.recharger()

    def _lancer(self):
        from reseau.mise_a_jour import mettre_a_jour
        self.etat = "telechargement"
        adresse = self.app.en_ligne.adresse()

        def travail():
            try:
                mettre_a_jour(adresse, self.infos, self._progresser)
                self.etat = "fini"
            except Exception as erreur:
                self.erreur = str(erreur)[:60]
                self.etat = "erreur"
        threading.Thread(target=travail, daemon=True).start()

    def _progresser(self, valeur):
        self.progression = valeur

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        if self.etat == "choix":
            self.menu.mettre_a_jour(dt, self.app.entrees, self.app.audio)
        elif self.etat == "fini" and self.temps > 0:
            self.app.en_marche = False          # le script prend le relais et relance le jeu
        elif self.etat == "erreur" and (self.app.entrees.vient_d_appuyer("valider")
                                        or self.app.entrees.vient_d_appuyer("retour")):
            self.app.depiler()

    def dessiner(self, image):
        voile(image, 190)
        cadre = pygame.Rect(0, 0, 720, 380)
        cadre.center = (config.LARGEUR / 2, config.HAUTEUR / 2)
        panneau(image, cadre, config.AMBRE)
        dessiner_texte(image, "NOUVELLE VERSION !", cadre.centerx, cadre.y + 50, 5, config.AMBRE)
        dessiner_texte(image, f"{VERSION}  ->  {self.infos['version']}", cadre.centerx,
                       cadre.y + 110, 3, config.BLANC)
        if self.etat == "choix":
            if not self.infos.get("auto") and not config.EST_WEB:
                dessiner_texte(image, "LANCE DEPUIS LE CODE : FAITES UN GIT PULL", cadre.centerx,
                               cadre.y + 160, 2, config.CYAN, lueur=False)
            self.menu.dessiner(image)
        elif self.etat in ("telechargement", "fini"):
            dessiner_texte(image, "TELECHARGEMENT..." if self.etat != "fini" else "REDEMARRAGE...",
                           cadre.centerx, cadre.y + 190, 3, config.CYAN)
            barre(image, pygame.Rect(cadre.x + 80, cadre.y + 240, cadre.w - 160, 18),
                  self.progression, config.ROSE)
        else:
            dessiner_texte(image, "ECHEC DE LA MISE A JOUR", cadre.centerx, cadre.y + 180, 3,
                           config.ROUGE)
            dessiner_texte(image, self.erreur, cadre.centerx, cadre.y + 220, 2, config.BLANC,
                           lueur=False)
            dessiner_texte(image, "TELECHARGEZ-LA SUR " + self.app.en_ligne.adresse()[:40],
                           cadre.centerx, cadre.y + 270, 2, config.CYAN, lueur=False)
            dessiner_texte(image, "ENTREE : CONTINUER", cadre.centerx, cadre.y + 320, 2,
                           (170, 140, 220), lueur=False)
