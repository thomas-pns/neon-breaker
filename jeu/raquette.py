# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Définir la raquette : déplacement fluide au clavier (accélération et
    freinage), suivi de la souris, limites du terrain, largeur animée
    (élargir / rétrécir), glace, étourdissement, canons laser, aimant,
    effet d'écrasement au contact. Une raquette peut être en bas
    (sens = -1, la balle repart vers le haut) ou en haut (sens = +1, Duel).

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

    Les skins (reseau/profil.py) ajoutent un motif sur le corps et
    parfois une traînée d'images fantômes.
"""

import colorsys
import math
import random

import pygame

from moteur import config
from moteur.rendu import halo_rect, attenuer, melanger


class Raquette:
    """
    Attributs :
        x (float) : centre horizontal ; y (float) : haut de la raquette.
        largeur_base, largeur, hauteur (float).
        sens (int) : -1 raquette du bas, +1 raquette du haut.
        joueur (Joueur ou None).
        vx (float) : vitesse horizontale (px/s).
        x_min, x_max (float) : limites du terrain.
        cible_souris (float ou None) : position visée à la souris.
        ecrasement (float) : animation de rebond (0..1).
        etourdie (float) : secondes d'immobilisation (tir de boss).
        gelee (float) : immobilisation (pénalité du mode Course).
    """

    def __init__(self, x_min, x_max, y, largeur=config.RAQUETTE_L,
                 hauteur=config.RAQUETTE_H, sens=-1, joueur=None):
        self.x_min = x_min
        self.x_max = x_max
        self.x = (x_min + x_max) / 2
        self.y = y
        self.largeur_base = largeur
        self.largeur = largeur
        self.hauteur = hauteur
        self.sens = sens
        self.joueur = joueur
        self.vx = 0.0
        self.cible_souris = None
        self.ecrasement = 0.0
        self.etourdie = 0.0
        self.gelee = 0.0
        self.temps = 0.0
        self.fantomes = []           # positions récentes (traînée des skins)

    # --- Géométrie ----------------------------------------------------------

    def rect(self):
        """But : rectangle de collision. Sortie : (pygame.Rect)."""
        return pygame.Rect(int(self.x - self.largeur / 2), int(self.y),
                           int(self.largeur), int(self.hauteur))

    def obtenir_boite(self):
        """But : boîte (x_min, y_min, x_max, y_max). Sortie : (tuple)."""
        return (self.x - self.largeur / 2, self.y,
                self.x + self.largeur / 2, self.y + self.hauteur)

    def face_y(self):
        """
        But : ordonnée de la face qui renvoie la balle (haut pour la
        raquette du bas, bas pour celle du haut).
        Sortie : (float).
        """
        return self.y if self.sens < 0 else self.y + self.hauteur

    def couleurs(self):
        """But : (corps, bord) selon le joueur. Sortie : (tuple, tuple)."""
        if self.joueur is not None:
            return self.joueur.couleur_corps, self.joueur.couleur_bord
        return config.RAQUETTE_CORPS, config.RAQUETTE_BORD

    # --- Mouvement ----------------------------------------------------------

    def mettre_a_jour(self, dt, direction):
        """
        But : déplacer la raquette.
        Entrées : dt (float) ; direction (int) : -1 gauche, +1 droite, 0 rien.
        Sortie : aucune.
        """
        self.temps += dt
        joueur = self.joueur
        glace = joueur is not None and joueur.actif("glace")
        if joueur is not None:
            cible = self.largeur_base * joueur.facteur_largeur()
            self.largeur += (cible - self.largeur) * min(1.0, dt * 8)
        self.etourdie = max(0.0, self.etourdie - dt)
        self.gelee = max(0.0, self.gelee - dt)
        if self.etourdie > 0 or self.gelee > 0:
            direction = 0
            self.cible_souris = None

        acceleration = config.RAQUETTE_ACCEL * (0.22 if glace else 1)
        freinage = config.RAQUETTE_FREIN * (0.06 if glace else 1)
        if direction != 0:
            self.cible_souris = None
            if self.vx * direction < 0 and not glace:
                self.vx = 0.0                      # demi-tour franc
            self.vx += direction * acceleration * dt
            limite = config.RAQUETTE_VITESSE_MAX
            self.vx = max(-limite, min(limite, self.vx))
        elif self.cible_souris is not None:
            ecart = self.cible_souris - self.x
            self.vx += (ecart * 22 - self.vx) * (0.15 if glace else 1.0)
        else:
            frein = freinage * dt
            if abs(self.vx) <= frein:
                self.vx = 0.0
            else:
                self.vx -= math.copysign(frein, self.vx)

        self.x += self.vx * dt
        self.contraindre()
        self.ecrasement = max(0.0, self.ecrasement - dt * 6)

    def contraindre(self):
        """But : garder la raquette entre les murs du terrain."""
        demi = self.largeur / 2
        if self.x - demi < self.x_min:
            self.x = self.x_min + demi
            self.vx = max(0.0, self.vx) * (0.5 if self._glisse() else 0)
        elif self.x + demi > self.x_max:
            self.x = self.x_max - demi
            self.vx = min(0.0, self.vx) * (0.5 if self._glisse() else 0)

    def _glisse(self):
        return self.joueur is not None and self.joueur.actif("glace")

    def viser_souris(self, x):
        """But : faire suivre la souris. Entrée : x (float) interne."""
        if self.etourdie <= 0 and self.gelee <= 0:
            self.cible_souris = x

    def frappee(self):
        """But : déclencher l'écrasement visuel (la balle vient de rebondir)."""
        self.ecrasement = 1.0

    def positions_canons(self):
        """But : abscisses des deux canons laser. Sortie : (tuple)."""
        return (self.x - self.largeur / 2 + 8, self.x + self.largeur / 2 - 8)

    # --- Dessin ---------------------------------------------------------------

    def dessiner(self, image, temps):
        """
        But : dessiner la raquette néon (corps dégradé, bords lumineux,
        réacteurs, canons laser, aimant, étincelles si étourdie).
        Entrées : image (Surface), temps (float). Sortie : aucune.
        """
        corps, bord = self.couleurs()
        joueur = self.joueur
        skin = self._skin()
        if skin["motif"].startswith("spectre"):
            r, v, b = colorsys.hsv_to_rgb((temps * 0.25) % 1.0, 0.75, 1.0)
            corps = (int(r * 255), int(v * 255), int(b * 255))
            r, v, b = colorsys.hsv_to_rgb((temps * 0.25 + 0.5) % 1.0, 0.6, 1.0)
            if not getattr(joueur, "bord_impose", False):
                bord = (int(r * 255), int(v * 255), int(b * 255))
        if skin["motif"] == "pulse":
            corps = melanger(corps, config.BLANC, 0.25 + 0.25 * math.sin(temps * 6))
        if (self.etourdie > 0 or self.gelee > 0) and int(temps * 16) % 2:
            corps, bord = (90, 90, 120), (160, 160, 200)
        if joueur is not None and joueur.actif("glace"):
            corps = melanger(corps, (200, 240, 255), 0.6)
        ecrase = math.sin(self.ecrasement * math.pi) * 0.3 if self.ecrasement else 0
        largeur = int(self.largeur * (1 + ecrase * 0.5))
        hauteur = max(4, int(self.hauteur * (1 - ecrase)))
        rect = pygame.Rect(0, 0, largeur, hauteur)
        if self.sens < 0:
            rect.midbottom = (int(self.x), int(self.y + self.hauteur))
        else:
            rect.midtop = (int(self.x), int(self.y))

        if skin["trainee"]:
            self._dessiner_trainee(image, rect, corps)
        lueur = halo_rect(largeur, hauteur, attenuer(bord, 0.8), rayon=8,
                          epaisseur=4)
        image.blit(lueur, (rect.x - 16, rect.y - 16),
                   special_flags=pygame.BLEND_RGB_ADD)
        for i in range(hauteur):
            t = i / max(1, hauteur - 1)
            if self.sens > 0:
                t = 1 - t
            couleur = melanger((230, 255, 255), corps, t * 0.8)
            couleur = melanger(couleur, (20, 30, 90), max(0, t - 0.6))
            pygame.draw.line(image, couleur, (rect.x + 3, rect.y + i),
                             (rect.right - 4, rect.y + i))
        self._dessiner_motif(image, rect, skin["motif"], corps, bord, temps)
        pygame.draw.rect(image, bord, rect, 2, border_radius=6)

        intensite = 0.5 + 0.5 * min(1.0, abs(self.vx) / config.RAQUETTE_VITESSE_MAX)
        pulse = 0.75 + 0.25 * math.sin(temps * 20)
        for bord_x in (rect.x + 2, rect.right - 9):
            image.fill(attenuer(config.AMBRE, intensite * pulse),
                       (bord_x, rect.y + 3, 7, max(2, hauteur - 6)),
                       special_flags=pygame.BLEND_RGB_ADD)

        if joueur is not None and joueur.actif("laser"):
            for cx in self.positions_canons():
                canon = pygame.Rect(0, 0, 6, 10)
                if self.sens < 0:
                    canon.midbottom = (int(cx), rect.top + 2)
                else:
                    canon.midtop = (int(cx), rect.bottom - 2)
                pygame.draw.rect(image, config.ROUGE, canon)
                image.fill(config.BLANC, canon.inflate(-4, -4))
        if joueur is not None and joueur.aimant_prises > 0:
            y = rect.top - 3 if self.sens < 0 else rect.bottom + 2
            for k in range(joueur.aimant_prises):
                image.fill(config.VERT, (rect.centerx - 22 + k * 10, y, 6, 2))

    # --- Skins --------------------------------------------------------------------

    def _skin(self):
        from reseau.profil import SKINS_PAR_CODE
        code = getattr(self.joueur, "skin", "neon") if self.joueur is not None else "neon"
        return SKINS_PAR_CODE.get(code) or SKINS_PAR_CODE["neon"]

    def _dessiner_trainee(self, image, rect, couleur):
        """Images fantômes derrière la raquette quand elle bouge."""
        self.fantomes.append(rect.centerx)
        del self.fantomes[:-6]
        for k, x in enumerate(self.fantomes[:-1]):
            if abs(x - rect.centerx) < 4:
                continue
            fantome = rect.copy()
            fantome.centerx = int(x)
            image.fill(attenuer(couleur, 0.08 + 0.05 * k), fantome.inflate(-6, -4),
                       special_flags=pygame.BLEND_RGB_ADD)

    def _dessiner_motif(self, image, rect, motif, corps, bord, temps):
        """Motif propre au skin, dessiné sur le corps de la raquette."""
        if motif in ("uni", "pulse", "spectre"):
            return
        if motif == "spectre_etoiles":
            motif = "etoiles"
        ancienne_zone = image.get_clip()
        image.set_clip(rect.inflate(-4, -4))
        trait = attenuer(bord, 0.55)
        if motif == "rayures":
            decal = int(temps * 30) % 12
            for x in range(rect.x - rect.h - 12 + decal, rect.right + 12, 12):
                pygame.draw.line(image, trait, (x, rect.bottom), (x + rect.h, rect.y), 3)
        elif motif == "grille":
            for x in range(rect.x + 6, rect.right, 10):
                pygame.draw.line(image, trait, (x, rect.y), (x, rect.bottom))
            pygame.draw.line(image, trait, (rect.x, rect.centery), (rect.right, rect.centery))
        elif motif == "damier":
            taille = max(4, rect.h // 2)
            for i, x in enumerate(range(rect.x, rect.right, taille)):
                for j, y in enumerate(range(rect.y, rect.bottom, taille)):
                    if (i + j) % 2:
                        image.fill(attenuer(bord, 0.45), (x, y, taille, taille))
        elif motif == "coeur":
            rayon = max(3, int(rect.h * (0.35 + 0.12 * math.sin(temps * 5))))
            pygame.draw.circle(image, config.BLANC, rect.center, rayon)
            pygame.draw.circle(image, bord, rect.center, rayon + 3, 2)
        elif motif == "vagues":
            points = [(x, rect.centery + math.sin(x * 0.12 + temps * 5) * rect.h * 0.28)
                      for x in range(rect.x, rect.right + 4, 4)]
            pygame.draw.lines(image, trait, False, points, 2)
        elif motif == "etoiles":
            for k in range(max(3, rect.w // 14)):
                eclat = 0.5 + 0.5 * math.sin(temps * 4 + k * 2.3)
                x = rect.x + 4 + (k * 37) % max(1, rect.w - 8)
                y = rect.y + 3 + (k * 11) % max(1, rect.h - 6)
                image.fill(melanger(corps, config.BLANC, eclat), (x, y, 2, 2))
        elif motif == "glitch":
            hasard = random.Random(int(temps * 12))
            for _ in range(3):
                bande = pygame.Rect(rect.x + hasard.randrange(max(1, rect.w - 20)),
                                    rect.y + hasard.randrange(max(1, rect.h - 3)),
                                    hasard.randrange(8, 24), 3)
                image.fill(hasard.choice((bord, config.BLANC, (255, 40, 120))), bande)
        image.set_clip(ancienne_zone)
