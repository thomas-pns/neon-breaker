# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Bot de test (2.1, réservé aux administrateurs) : il pilote la raquette du
    joueur local dans une partie en ligne, comme le ferait une souris. On
    lance le jeu deux fois (deux PC, ou deux fenêtres), l'un en bot, et on
    joue contre lui pour tester la latence sans avoir besoin d'un ami.

    Il vise l'endroit où la balle va arriver (rebonds sur les murs compris),
    avec un petit décalage pour varier les angles, lance la balle, et utilise
    de temps en temps pouvoirs et overdrive.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 25/10/2026
"""

import math


def point_d_arrivee(balle, y_cible, gauche, droite):
    """
    But : abscisse où la balle croisera la hauteur y_cible, en tenant compte des
    rebonds sur les murs gauche et droit (None si elle s'éloigne).
    Entrées : balle (x, y, vx, vy, rayon) ; y_cible, gauche, droite (float).
    Sortie : (float ou None).
    """
    if balle.vy == 0 or (y_cible - balle.y) / balle.vy < 0:
        return None
    temps = (y_cible - balle.y) / balle.vy
    gauche, droite = gauche + balle.rayon, droite - balle.rayon
    largeur = max(1.0, droite - gauche)
    x = balle.x - gauche + balle.vx * temps
    x = x % (2 * largeur)                     # dépliage des rebonds
    if x > largeur:
        x = 2 * largeur - x
    return gauche + x


class Bot:
    """Pilote automatique. Attributs : temps (float), dernier_lancer (float)."""

    def __init__(self):
        self.temps = 0.0
        self.dernier_lancer = 0.0
        self.dernier_pouvoir = 0.0

    def cible(self, joueur, terrain):
        """But : abscisse que la raquette doit viser. Sortie : (float)."""
        raquette = joueur.raquette
        face = raquette.face_y()
        balles = [b for b in terrain.balles if not b.collee and b.vy * raquette.sens < 0]
        if not balles:
            capsules = [c for c in terrain.capsules if getattr(c, "bonus", True)]
            if capsules:
                return min(capsules, key=lambda c: abs(c.y - face)).x
            return terrain.rect.centerx + math.sin(self.temps * 0.7) * terrain.rect.w * 0.2
        balle = min(balles, key=lambda b: abs((face - b.y) / b.vy) if b.vy else 1e9)
        x = point_d_arrivee(balle, face, terrain.rect.left, terrain.rect.right)
        if x is None:
            x = balle.x
        return x + math.sin(self.temps * 1.7) * raquette.largeur * 0.25

    def piloter(self, app, joueur, dt):
        """
        But : une image de pilotage : place la « souris » sur la cible et appuie
        sur les touches qu'il faut (lancer, pouvoir, overdrive).
        Entrées : app ; joueur (Joueur local) ; dt (float).
        """
        self.temps += dt
        terrain, raquette = joueur.terrain, joueur.raquette
        if terrain is None or raquette is None:
            return
        entrees = app.entrees
        entrees.souris = (int(self.cible(joueur, terrain)), int(terrain.rect.centery))
        entrees.souris_bougee = True
        if any(b.collee for b in terrain.balles) and self.temps - self.dernier_lancer > 0.8:
            entrees.forcer("action", "solo")
            self.dernier_lancer = self.temps
        if self.temps - self.dernier_pouvoir > 4.0:
            self.dernier_pouvoir = self.temps
            if getattr(joueur, "overdrive_pret", lambda: False)():
                entrees.forcer("overdrive", "solo")
            else:
                entrees.forcer("activer", "solo")
