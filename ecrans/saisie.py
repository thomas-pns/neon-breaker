# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Saisie du nom en 3 lettres, façon borne d'arcade : flèches haut/bas
    pour changer la lettre, gauche/droite pour changer de case, ou taper
    directement au clavier ; Entrée pour valider.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Saisie à la manette.
"""

import math

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from ecrans.base import EcranBase, voile
from ecrans.hud import panneau

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "


class EcranSaisieNom(EcranBase):
    """Attributs : lettres (list de 3 indices dans ALPHABET), case (int)."""

    def __init__(self, app, resultat, fabrique):
        super().__init__(app)
        self.resultat = resultat
        self.fabrique = fabrique
        dernier = app.donnees.get("dernier_nom", "AAA")
        self.lettres = [ALPHABET.index(c) if c in ALPHABET else 0 for c in dernier[:3]]
        self.case = 0

    def entrer(self):
        self.app.audio.jouer("victoire")

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        entrees = self.app.entrees
        audio = self.app.audio
        if pygame.KSCAN_UP in entrees.appuis:
            self.lettres[self.case] = (self.lettres[self.case] - 1) % len(ALPHABET)
            audio.jouer("menu_nav")
        if pygame.KSCAN_DOWN in entrees.appuis:
            self.lettres[self.case] = (self.lettres[self.case] + 1) % len(ALPHABET)
            audio.jouer("menu_nav")
        if pygame.KSCAN_LEFT in entrees.appuis:
            self.case = max(0, self.case - 1)
        if pygame.KSCAN_RIGHT in entrees.appuis:
            self.case = min(2, self.case + 1)
        for caractere in entrees.texte.upper():
            if caractere in ALPHABET.strip():
                self.lettres[self.case] = ALPHABET.index(caractere)
                self.case = min(2, self.case + 1)
                audio.jouer("menu_nav")
        # Seules les flèches naviguent : les lettres servent à écrire le nom.
        valider = (pygame.KSCAN_RETURN in entrees.appuis or pygame.KSCAN_KP_ENTER in entrees.appuis
                   or ("menu", "valider") in entrees.forcees)
        if valider or 1 in entrees.clics:
            self._valider()

    def _valider(self):
        from ecrans.fin import EcranFin
        nom = "".join(ALPHABET[i] for i in self.lettres).strip() or "???"
        self.app.donnees["dernier_nom"] = nom
        rang = self.app.ajouter_au_classement(self.resultat["mode"], nom,
                                              self.resultat["score"])
        self.app.audio.jouer("menu_ok")
        self.app.remplacer(EcranFin(self.app, self.resultat, self.fabrique, rang))

    def dessiner(self, image):
        self.app.fond.dessiner(image)
        voile(image, 150)
        cadre = pygame.Rect(0, 0, 640, 420)
        cadre.center = (config.LARGEUR / 2, config.HAUTEUR / 2)
        panneau(image, cadre, config.AMBRE)
        dessiner_texte(image, "TOP 10 !", cadre.centerx, cadre.y + 56, 7, config.AMBRE)
        dessiner_texte(image, f"SCORE {self.resultat['score']:07d}", cadre.centerx,
                       cadre.y + 126, 3, config.BLANC)
        dessiner_texte(image, "ENTREZ VOTRE NOM", cadre.centerx, cadre.y + 176, 2,
                       (170, 140, 220), lueur=False)
        for i, indice in enumerate(self.lettres):
            x = cadre.centerx + (i - 1) * 110
            y = cadre.y + 270
            choisie = i == self.case
            couleur = config.CYAN if choisie else config.BLANC
            dessiner_texte(image, ALPHABET[indice] if ALPHABET[indice] != " " else "_",
                           x, y, 10, couleur)
            if choisie:
                decalage = math.sin(self.temps * 8) * 4
                dessiner_texte(image, "↑", x, y - 70 + decalage, 3, config.ROSE, lueur=False)
                dessiner_texte(image, "↓", x, y + 70 - decalage, 3, config.ROSE, lueur=False)
        dessiner_texte(image, "↑↓ LETTRE   ←→ CASE   ENTREE : VALIDER",
                       cadre.centerx, cadre.bottom - 30, 2, (170, 140, 220), lueur=False)
