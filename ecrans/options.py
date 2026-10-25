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
        self.menu = MenuVertical([], config.LARGEUR / 2, 206, 3, 36)
        self.bulles_reactivees = False
        self._construire()

    @property
    def attenuer_musique(self):
        return getattr(self.dessous, "attenuer_musique", False)

    def musique(self):
        return self.dessous.musique() if self.dessous is not None else "menu"

    def reprendre(self):
        """
        But : actualiser les noms apres fermeture de leur ecran de saisie.
        Entree(s) : aucune. Sortie : aucune.
        """
        self._construire()

    def _saisir_nom(self, numero):
        """
        But : ouvrir la saisie du nom de record du joueur indique.
        Entree(s) : numero (int). Sortie : aucune.
        """
        from ecrans.saisie import EcranSaisieNom
        self.app.empiler(EcranSaisieNom(self.app, None, None, reglage=numero))

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
            ("COMMANDES / MANETTE", self._commandes),
            (f"NOM DES RECORDS J1 : {self._nom_defaut(1)}", lambda: self._saisir_nom(1)),
            (f"NOM DES RECORDS J2 : {self._nom_defaut(2)}", lambda: self._saisir_nom(2)),
            ("BULLES D'AIDE : " + ("REACTIVEES" if self.bulles_reactivees else "REVOIR"),
             self._revoir_bulles),
            ("RETOUR", self._retour),
        ]
        self.menu.indice = indice

    def _nom_defaut(self, numero):
        """
        But : obtenir le nom qui sera pre-rempli dans le classement.
        Entree(s) : numero (int). Sortie : (str) nom de trois caracteres.
        """
        from ecrans.saisie import nom_par_defaut
        return nom_par_defaut(self.app, numero)

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

    def _commandes(self):
        from ecrans.commandes import EcranCommandes
        self.app.empiler(EcranCommandes(self.app))

    def _retour(self):
        self.app.depiler()

    def _revoir_bulles(self):
        """But : effacer les bulles deja vues pour les reactiver."""
        self.app.donnees["bulles_vues"] = []
        self.bulles_reactivees = True
        self.app.audio.jouer("menu_ok")
        self.app.enregistrer()
        self._construire()

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
        dessiner_texte(image, "OPTIONS", config.LARGEUR / 2, 138 + decalage, 6, config.CYAN)
        self.menu.dessiner(image)
        dessiner_texte(image, "↑↓ : CHOISIR   ←→ : REGLER   ECHAP : RETOUR", config.LARGEUR / 2,
                       cadre.bottom - 26, 2, (150, 120, 200), lueur=False)
