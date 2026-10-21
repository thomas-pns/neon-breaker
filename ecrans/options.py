# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Menu OPTIONS, posé par-dessus l'écran titre ou la pause : volumes de la
    musique et des effets (curseurs ←→), filtre CRT, tremblement,
    particules, plein écran. Tout est enregistré immédiatement.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import math

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from ecrans.base import EcranBase, MenuVertical, voile
from ecrans.hud import panneau


def curseur(valeur):
    """But : jauge texte de 10 crans, ex. « ■■■■■■□□□□ 60% »."""
    crans = round(valeur * 10)
    return "■" * crans + "□" * (10 - crans) + f" {crans * 10}%"


class EcranOptions(EcranBase):
    """Réglages du jeu, par-dessus l'écran précédent (qui reste visible)."""

    transparent = True

    def __init__(self, app):
        super().__init__(app)
        self.menu = MenuVertical([], config.LARGEUR / 2, 240, 3, 52)
        self._construire()

    @property
    def attenuer_musique(self):
        return getattr(self.dessous, "attenuer_musique", False)

    def musique(self):
        return self.dessous.musique() if self.dessous is not None else "menu"

    def _construire(self):
        r = self.app.reglages
        oui_non = {True: "OUI", False: "NON"}
        indice = self.menu.indice
        self.menu.options = [
            (f"MUSIQUE  {curseur(r['volume_musique'])}", lambda: self._volume("volume_musique", 1),
             lambda s: self._volume("volume_musique", s)),
            (f"EFFETS  {curseur(r['volume_effets'])}", lambda: self._volume("volume_effets", 1),
             lambda s: self._volume("volume_effets", s)),
            (f"FILTRE CRT : {oui_non[r['crt']]}", lambda: self._basculer("crt"),
             lambda s: self._basculer("crt")),
            (f"TREMBLEMENT : {oui_non[r['tremblement']]}", lambda: self._basculer("tremblement"),
             lambda s: self._basculer("tremblement")),
            (f"PARTICULES : {r['particules'].upper()}", lambda: self._particules(1),
             self._particules),
            ("PLEIN ECRAN  (F11)", self.app.ecran.basculer_plein_ecran),
            ("RETOUR", self._retour),
        ]
        self.menu.indice = indice

    def _volume(self, cle, sens):
        valeur = round(self.app.reglages[cle] * 10) + sens
        if sens > 0 and valeur > 10:
            valeur = 0                     # Entrée fait le tour : 100 % -> 0 %
        self.app.reglages[cle] = max(0, min(10, valeur)) / 10
        self.app.audio.volume_musique = self.app.reglages["volume_musique"]
        self.app.audio.volume_effets = self.app.reglages["volume_effets"]
        if cle == "volume_effets":
            self.app.audio.jouer("brique_4")
        self.app.enregistrer()
        self._construire()

    def _basculer(self, cle):
        self.app.reglages[cle] = not self.app.reglages[cle]
        self.app.audio.jouer("menu_nav")
        self.app.enregistrer()
        self._construire()

    def _particules(self, sens):
        ordre = ["bas", "moyen", "haut"]
        actuel = ordre.index(self.app.reglages["particules"])
        self.app.reglages["particules"] = ordre[(actuel + sens) % 3]
        self.app.audio.jouer("menu_nav")
        self.app.enregistrer()
        self._construire()

    def _retour(self):
        self.app.depiler()

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        entrees = self.app.entrees
        if entrees.vient_d_appuyer("retour") or entrees.vient_d_appuyer("pause"):
            self.app.audio.jouer("menu_ok")
            self._retour()
            return
        self.menu.mettre_a_jour(dt, entrees, self.app.audio)

    def dessiner(self, image):
        voile(image, 225)
        cadre = pygame.Rect(0, 0, 720, 560)
        cadre.center = (config.LARGEUR / 2, config.HAUTEUR / 2 + 10)
        panneau(image, cadre, config.CYAN)
        decalage = math.sin(self.temps * 3) * 3
        dessiner_texte(image, "OPTIONS", config.LARGEUR / 2, 160 + decalage, 6, config.CYAN)
        self.menu.dessiner(image)
        dessiner_texte(image, "↑↓ : CHOISIR   ←→ : REGLER   ECHAP : RETOUR", config.LARGEUR / 2,
                       cadre.bottom - 26, 2, (150, 120, 200), lueur=False)
