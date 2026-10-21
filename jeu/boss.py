# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Les trois boss de la campagne, chacun avec plusieurs phases :
      - SUNSET   : le soleil rayé, protégé par une rangée de briques qui se
                   reforme ; tire des boules de feu (3 à la fois en phase 2).
      - GRIDLOCK : vaisseau qui invoque des rangées de briques ; en phase 2,
                   rayons verticaux annoncés par une ligne d'alerte.
      - CORE     : noyau protégé par un bouclier tournant ; phase 2 :
                   rayons ; phase 3 : rafales de malus et rotation rapide.
    Les tirs qui touchent une raquette l'étourdissent une seconde.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Boss secret, attaques coordonnées en Coop.
"""

import math
import random

import pygame

from structures.liste import Liste
from moteur import config
from moteur.police_pixel import dessiner_texte
from moteur.rendu import halo_cercle, halo_rect, attenuer, melanger
from jeu.brique import BriqueGarde, BriqueGardeSolide
from jeu.capsule import Capsule, CATALOGUE
from jeu.projectiles import TirBoss


def rebondir_sur_cercle(balle, cx, cy, rayon):
    """
    But : collision et rebond d'une balle sur un disque (réflexion sur la
    normale au point de contact, puis dégagement).
    Entrées : balle (Balle) ; cx, cy, rayon (float) : le disque.
    Sortie : (bool) True s'il y a eu contact.
    """
    dx, dy = balle.x - cx, balle.y - cy
    distance = math.hypot(dx, dy)
    if distance >= rayon + balle.rayon or distance == 0:
        return False
    nx, ny = dx / distance, dy / distance
    produit = balle.vx * nx + balle.vy * ny
    if produit < 0:
        balle.vx -= 2 * produit * nx
        balle.vy -= 2 * produit * ny
    balle.x = cx + nx * (rayon + balle.rayon + 0.5)
    balle.y = cy + ny * (rayon + balle.rayon + 0.5)
    balle.rebondir_effet(nx, ny)
    return True


class Boss:
    """
    Classe de base.
    Attributs : nom (str), x, y (centre), vie, vie_max (int), phase (int),
    temps, invulnerable (s), flash (0..1), mort (s écoulées depuis la mort,
    -1 si vivant), couleur.
    """

    nom = "BOSS"
    couleur = config.ROSE

    def __init__(self, terrain, vie):
        self.x = terrain.rect.centerx
        self.y = terrain.rect.top + 150
        self.vie = vie
        self.vie_max = vie
        self.phase = 1
        self.temps = 0.0
        self.invulnerable = 0.0
        self.flash = 0.0
        self.mort = -1.0
        self.vie_affichee = float(vie)

    # --- Interface utilisée par le terrain -----------------------------------

    def est_vaincu(self):
        """But : le boss a-t-il fini d'exploser ? Sortie : (bool)."""
        return self.mort >= 1.6

    def vivant(self):
        """But : le boss se bat-il encore ? Sortie : (bool)."""
        return self.mort < 0

    def blesser(self, degats, terrain):
        """
        But : infliger des dégâts (avec une courte invulnérabilité).
        Entrées : degats (int) ; terrain (Terrain). Sortie : aucune.
        """
        if not self.vivant() or self.invulnerable > 0:
            return
        self.vie -= degats
        self.invulnerable = 0.12
        self.flash = 1.0
        terrain.evenements.enfiler(("boss_blesse", self.x, self.y))
        nouvelle_phase = self.calculer_phase()
        if nouvelle_phase != self.phase:
            self.phase = nouvelle_phase
            terrain.evenements.enfiler(("boss_phase", self.phase))
        if self.vie <= 0:
            self.vie = 0
            self.mort = 0.0
            terrain.tirs.vider()
            terrain.evenements.enfiler(("boss_mort", self.x, self.y))

    def calculer_phase(self):
        """But : phase selon la vie restante (2 phases par défaut)."""
        return 1 if self.vie > self.vie_max / 2 else 2

    def subir_explosion(self, zone, puissance, terrain):
        """But : une explosion qui touche le boss le blesse."""
        if self.touche_boite(zone):
            self.blesser(puissance, terrain)

    def mettre_a_jour(self, dt, terrain):
        """
        But : animer le boss (mouvement, attaques), ou son explosion finale.
        Entrées : dt (float) ; terrain (Terrain). Sortie : aucune.
        """
        self.temps += dt
        self.invulnerable = max(0.0, self.invulnerable - dt)
        self.flash = max(0.0, self.flash - dt * 5)
        self.vie_affichee += (self.vie - self.vie_affichee) * min(1, dt * 6)
        if self.mort >= 0:
            ancien = self.mort
            self.mort += dt
            # Une explosion toutes les 0,2 s pendant l'agonie.
            if int(self.mort / 0.2) != int(ancien / 0.2):
                terrain.evenements.enfiler((
                    "boss_explosion", self.x + random.uniform(-70, 70),
                    self.y + random.uniform(-50, 50)))
            return
        self.attaquer(dt, terrain)

    def attaquer(self, dt, terrain):
        """But : comportement propre à chaque boss (à redéfinir)."""

    def collision_balle(self, balle, terrain):
        """But : rebond de la balle sur le boss ; Sortie : (bool) touché."""
        return False

    def touche_boite(self, boite):
        """But : le boss chevauche-t-il une boîte ? Sortie : (bool)."""
        return False

    # --- Outils ---------------------------------------------------------------

    def raquette_visee(self, terrain):
        """But : raquette la plus proche (cible des tirs)."""
        if not terrain.raquettes:
            return None
        return min(terrain.raquettes, key=lambda r: abs(r.x - self.x))

    def tirer_vers(self, terrain, cible_x, cible_y, vitesse=320, ecarts=(0,),
                   couleur=config.AMBRE):
        """
        But : tirer une ou plusieurs boules vers un point.
        Entrées : terrain ; cible_x, cible_y (float) ; vitesse (px/s) ;
                  ecarts (tuple de degrés) ; couleur. Sortie : aucune.
        """
        angle = math.atan2(cible_y - self.y, cible_x - self.x)
        for ecart in ecarts:
            a = angle + math.radians(ecart)
            terrain.tirs.ajouter_fin(TirBoss(self.x, self.y + 30,
                                             math.cos(a) * vitesse,
                                             math.sin(a) * vitesse,
                                             couleur=couleur))
        terrain.evenements.enfiler(("boss_tir", self.x, self.y))

    def dessiner_barre_vie(self, image, terrain):
        """But : nom et barre de vie en haut du terrain."""
        rect = pygame.Rect(terrain.rect.x + 40, terrain.rect.y + 12,
                           terrain.rect.w - 80, 10)
        pygame.draw.rect(image, (50, 10, 40), rect)
        ratio = max(0.0, self.vie_affichee / self.vie_max)
        rempli = rect.copy()
        rempli.w = int(rect.w * ratio)
        couleur = melanger(config.ROUGE, self.couleur, ratio)
        if rempli.w > 0:
            image.fill(couleur, rempli)
        pygame.draw.rect(image, config.BLANC, rect, 1)
        dessiner_texte(image, f"{self.nom}  PHASE {self.phase}", rect.centerx,
                       rect.bottom + 14, 2, couleur, lueur=False)

    def dessiner(self, image, terrain):
        """But : dessin du boss (à redéfinir) + barre de vie."""
        if self.vivant():
            self.dessiner_barre_vie(image, terrain)


class BossSunset(Boss):
    """Boss du monde 1 : le soleil rayé et sa garde de briques."""

    nom = "SUNSET"
    couleur = config.AMBRE
    rayon = 66

    def __init__(self, terrain):
        super().__init__(terrain, vie=24)
        self.y = terrain.rect.top + 140
        self.prochain_tir = 2.5
        self.prochaine_garde = 0.0
        self.gardes = Liste()

    def attaquer(self, dt, terrain):
        amplitude = terrain.rect.w / 2 - self.rayon - 30
        vitesse = 0.55 if self.phase == 1 else 0.9
        self.x = terrain.rect.centerx + math.sin(self.temps * vitesse) * amplitude
        self.prochain_tir -= dt
        if self.prochain_tir <= 0:
            cible = self.raquette_visee(terrain)
            if cible is not None:
                if self.phase == 1:
                    self.tirer_vers(terrain, cible.x, cible.y, 300)
                    self.prochain_tir = 2.2
                else:
                    self.tirer_vers(terrain, cible.x, cible.y, 340, (-18, 0, 18))
                    self.prochain_tir = 1.5
        self.prochaine_garde -= dt
        if self.prochaine_garde <= 0:
            self.prochaine_garde = 8.0 if self.phase == 1 else 5.0
            self._reformer_garde(terrain)

    def _reformer_garde(self, terrain):
        """Recrée les briques de garde manquantes sous le soleil."""
        pas_x, _ = terrain.pas_grille()
        y = self.y + self.rayon + 40
        vivantes = {round(b.x) for b in terrain.briques if isinstance(b, BriqueGarde)
                    and abs(b.y - y) < 2}
        nouvelles = []
        debut = terrain.rect.left + 22
        for colonne in range(12):
            x = debut + colonne * pas_x
            if round(x) in vivantes or colonne % 4 == 3:
                continue
            garde = BriqueGarde(x, y, terrain.brique_l, terrain.brique_h,
                                config.AMBRE if colonne % 2 else config.ROSE)
            terrain.briques.ajouter_fin(garde)
            nouvelles.append(garde)
        terrain.preparer_briques(nouvelles, cascade=False)
        for garde in nouvelles:
            garde.apparition = 0.0

    def collision_balle(self, balle, terrain):
        if not self.vivant():
            return False
        if rebondir_sur_cercle(balle, self.x, self.y, self.rayon):
            self.blesser(1, terrain)
            return True
        return False

    def touche_boite(self, boite):
        x_min, y_min, x_max, y_max = boite
        px = min(max(self.x, x_min), x_max)
        py = min(max(self.y, y_min), y_max)
        return (self.x - px) ** 2 + (self.y - py) ** 2 <= self.rayon ** 2

    def dessiner(self, image, terrain):
        if self.mort >= 1.0:
            return
        rayon = self.rayon
        lueur = halo_cercle(rayon, attenuer(config.ROSE, 0.8), rayon=24)
        image.blit(lueur, lueur.get_rect(center=(int(self.x), int(self.y))),
                   special_flags=pygame.BLEND_RGB_ADD)
        for dy in range(-rayon, rayon + 1, 2):
            demi = math.sqrt(max(0, rayon * rayon - dy * dy))
            t = (dy + rayon) / (2 * rayon)
            # Bandes vides qui défilent dans la moitié basse.
            if dy > -rayon * 0.2 and int((dy + self.temps * 30) / 7) % 3 == 0:
                continue
            couleur = melanger((255, 236, 110), (255, 60, 120), t)
            if self.flash > 0:
                couleur = melanger(couleur, config.BLANC, self.flash)
            pygame.draw.line(image, couleur, (self.x - demi, self.y + dy),
                             (self.x + demi, self.y + dy), 2)
        # Yeux en colère.
        colere = 8 if self.phase == 2 else 4
        for sens in (-1, 1):
            ox = self.x + sens * 24
            pygame.draw.line(image, (40, 0, 30), (ox - 12, self.y - 22 - colere * sens * -1),
                             (ox + 12, self.y - 22 + colere * sens * -1), 5)
        super().dessiner(image, terrain)


class BossGridlock(Boss):
    """Boss du monde 2 : vaisseau qui invoque des briques et tire des rayons."""

    nom = "GRIDLOCK"
    couleur = config.CYAN
    largeur = 220
    hauteur = 56

    def __init__(self, terrain):
        super().__init__(terrain, vie=32)
        self.y = terrain.rect.top + 120
        self.prochaine_invocation = 3.0
        self.prochain_rayon = 4.0
        self.rayons = []           # [x, temps_restant, etat "alerte"/"feu"]
        self.vitesse = 120.0

    def boite(self):
        return (self.x - self.largeur / 2, self.y - self.hauteur / 2,
                self.x + self.largeur / 2, self.y + self.hauteur / 2)

    def attaquer(self, dt, terrain):
        vitesse = self.vitesse * (1 if self.phase == 1 else 1.8)
        self.x += vitesse * dt
        gauche = terrain.rect.left + self.largeur / 2 + 10
        droite = terrain.rect.right - self.largeur / 2 - 10
        if self.x < gauche or self.x > droite:
            self.x = max(gauche, min(droite, self.x))
            self.vitesse = -self.vitesse
        self.prochaine_invocation -= dt
        if self.prochaine_invocation <= 0:
            self.prochaine_invocation = 9.0 if self.phase == 1 else 7.0
            self._invoquer(terrain)
        if self.phase >= 2:
            self.prochain_rayon -= dt
            if self.prochain_rayon <= 0:
                self.prochain_rayon = 3.2
                cible = self.raquette_visee(terrain)
                if cible is not None:
                    self.rayons.append([cible.x, 0.9, "alerte"])
        self._mettre_a_jour_rayons(dt, terrain)

    def _invoquer(self, terrain):
        """Une rangée de briques apparaît sous le vaisseau."""
        pas_x, pas_y = terrain.pas_grille()
        y = self.y + self.hauteur / 2 + 30
        occupees = {round(b.x) for b in terrain.briques if abs(b.y - y) < 2}
        nouvelles = []
        for colonne in range(12):
            x = terrain.rect.left + 22 + colonne * pas_x
            if round(x) in occupees or random.random() < 0.3:
                continue
            classe = BriqueGardeSolide if random.random() < 0.3 else BriqueGarde
            if classe is BriqueGardeSolide:
                garde = classe(x, y, terrain.brique_l, terrain.brique_h, config.BLEU)
            else:
                garde = classe(x, y, terrain.brique_l, terrain.brique_h, config.CYAN)
            terrain.briques.ajouter_fin(garde)
            nouvelles.append(garde)
        terrain.preparer_briques(nouvelles, cascade=False)
        for garde in nouvelles:
            garde.apparition = 0.0
        terrain.evenements.enfiler(("boss_invocation", self.x, y))

    def _mettre_a_jour_rayons(self, dt, terrain):
        """Ligne d'alerte (0,9 s) puis rayon mortel (0,5 s)."""
        for rayon in self.rayons:
            rayon[1] -= dt
            if rayon[2] == "alerte" and rayon[1] <= 0:
                rayon[2], rayon[1] = "feu", 0.5
                terrain.evenements.enfiler(("boss_rayon", rayon[0]))
            if rayon[2] == "feu":
                for raquette in terrain.raquettes:
                    if abs(raquette.x - rayon[0]) < raquette.largeur / 2 + 10:
                        joueur = raquette.joueur
                        if raquette.etourdie <= 0 and not (joueur and joueur.actif("bouclier")):
                            raquette.etourdie = 0.7
                            terrain.evenements.enfiler(("raquette_touchee", raquette))
        self.rayons = [r for r in self.rayons if not (r[2] == "feu" and r[1] <= 0)]

    def collision_balle(self, balle, terrain):
        from jeu.terrain import disque_touche_boite, rebondir_sur_boite
        if not self.vivant():
            return False
        boite = self.boite()
        if disque_touche_boite(balle.x, balle.y, balle.rayon, boite):
            rebondir_sur_boite(balle, boite)
            self.blesser(1, terrain)
            return True
        return False

    def touche_boite(self, boite):
        from jeu.terrain import boites_se_touchent
        return self.vivant() and boites_se_touchent(self.boite(), boite)

    def dessiner(self, image, terrain):
        if self.mort >= 1.0:
            return
        self.dessiner_rayons(image, terrain)
        x_min, y_min, x_max, y_max = self.boite()
        rect = pygame.Rect(int(x_min), int(y_min), self.largeur, self.hauteur)
        lueur = halo_rect(rect.w, rect.h, attenuer(self.couleur, 0.8), rayon=10)
        image.blit(lueur, (rect.x - 20, rect.y - 20), special_flags=pygame.BLEND_RGB_ADD)
        corps = melanger((20, 30, 80), config.BLANC, self.flash)
        points = [(rect.x, rect.centery), (rect.x + 30, rect.y), (rect.right - 30, rect.y),
                  (rect.right, rect.centery), (rect.right - 30, rect.bottom),
                  (rect.x + 30, rect.bottom)]
        pygame.draw.polygon(image, corps, points)
        pygame.draw.polygon(image, self.couleur, points, 3)
        # Grille lumineuse sur la coque + œil central qui suit la raquette.
        for k in range(1, 6):
            x = rect.x + k * rect.w / 6
            pygame.draw.line(image, attenuer(self.couleur, 0.4), (x, rect.y + 6),
                             (x, rect.bottom - 6))
        cible = self.raquette_visee(terrain)
        decal = 0 if cible is None else max(-20, min(20, (cible.x - self.x) / 10))
        pygame.draw.circle(image, config.ROUGE if self.phase == 2 else config.ROSE,
                           (int(self.x + decal), rect.centery), 10)
        pygame.draw.circle(image, config.BLANC, (int(self.x + decal), rect.centery), 4)
        super().dessiner(image, terrain)


class BossCore(Boss):
    """Boss final : noyau à bouclier tournant, 3 phases."""

    nom = "CORE"
    couleur = config.VIOLET
    rayon = 52
    rayon_orbite = 104
    nb_segments = 6

    def __init__(self, terrain):
        super().__init__(terrain, vie=42)
        self.y = terrain.rect.top + 210
        self.angle = 0.0
        self.prochain_tir = 2.0
        self.prochain_rayon = 3.0
        self.prochain_malus = 3.0
        self.rayons = []

    def calculer_phase(self):
        ratio = self.vie / self.vie_max
        return 1 if ratio > 0.66 else (2 if ratio > 0.33 else 3)

    def segments(self):
        """But : boîtes des segments du bouclier tournant."""
        boites = []
        for k in range(self.nb_segments):
            a = self.angle + k * 2 * math.pi / self.nb_segments
            cx = self.x + math.cos(a) * self.rayon_orbite
            cy = self.y + math.sin(a) * self.rayon_orbite
            boites.append((cx - 18, cy - 9, cx + 18, cy + 9))
        return boites

    def attaquer(self, dt, terrain):
        vitesse = {1: 0.8, 2: 1.2, 3: 2.0}[self.phase]
        self.angle += vitesse * dt
        self.x = terrain.rect.centerx + math.sin(self.temps * 0.4) * 120
        self.prochain_tir -= dt
        if self.prochain_tir <= 0:
            self.prochain_tir = 2.6 if self.phase == 1 else 2.0
            cible = self.raquette_visee(terrain)
            if cible is not None:
                self.tirer_vers(terrain, cible.x, cible.y, 300, (-25, 0, 25),
                                couleur=config.VIOLET)
        if self.phase >= 2:
            self.prochain_rayon -= dt
            if self.prochain_rayon <= 0:
                self.prochain_rayon = 3.5 if self.phase == 2 else 2.4
                cible = self.raquette_visee(terrain)
                if cible is not None:
                    self.rayons.append([cible.x, 0.9, "alerte"])
            BossGridlock._mettre_a_jour_rayons(self, dt, terrain)
        if self.phase == 3:
            self.prochain_malus -= dt
            if self.prochain_malus <= 0:
                self.prochain_malus = 3.0
                malus = [c for c, e in CATALOGUE.items() if e.categorie == "malus"]
                terrain.capsules.ajouter_fin(Capsule(self.x, self.y + self.rayon,
                                                     random.choice(malus), 1))

    def collision_balle(self, balle, terrain):
        from jeu.terrain import disque_touche_boite, rebondir_sur_boite
        if not self.vivant():
            return False
        for boite in self.segments():
            if disque_touche_boite(balle.x, balle.y, balle.rayon, boite):
                rebondir_sur_boite(balle, boite)
                terrain.evenements.enfiler(("mur", balle))
                return False
        if rebondir_sur_cercle(balle, self.x, self.y, self.rayon):
            self.blesser(1, terrain)
            return True
        return False

    def touche_boite(self, boite):
        return BossSunset.touche_boite(self, boite)

    def dessiner(self, image, terrain):
        if self.mort >= 1.0:
            return
        _dessiner_rayons(self, image, terrain)
        pulse = 0.7 + 0.3 * math.sin(self.temps * 6)
        couleur = {1: config.VIOLET, 2: config.ROSE, 3: config.ROUGE}[self.phase]
        lueur = halo_cercle(self.rayon, attenuer(couleur, pulse), rayon=26)
        image.blit(lueur, lueur.get_rect(center=(int(self.x), int(self.y))),
                   special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.circle(image, melanger((30, 0, 50), config.BLANC, self.flash),
                           (int(self.x), int(self.y)), self.rayon)
        for k in range(3):
            r = int(self.rayon * (0.85 - k * 0.25))
            pygame.draw.circle(image, attenuer(couleur, 1 - k * 0.25),
                               (int(self.x), int(self.y)), r, 3)
        pygame.draw.circle(image, config.BLANC, (int(self.x), int(self.y)), 8)
        for x_min, y_min, x_max, y_max in self.segments():
            rect = pygame.Rect(int(x_min), int(y_min), int(x_max - x_min), int(y_max - y_min))
            pygame.draw.rect(image, (40, 40, 70), rect, border_radius=3)
            pygame.draw.rect(image, config.GRIS_METAL, rect, 2, border_radius=3)
        super().dessiner(image, terrain)


def _dessiner_rayons(boss, image, terrain):
    """Rayons verticaux (partagé par GRIDLOCK et CORE)."""
    for x, reste, etat in boss.rayons:
        if etat == "alerte":
            if int(reste * 12) % 2:
                pygame.draw.line(image, config.ROUGE, (x, boss.y),
                                 (x, terrain.rect.bottom), 1)
        else:
            hauteur = int(terrain.rect.bottom - boss.y)
            lueur = halo_rect(18, hauteur, config.ROUGE, rayon=8, epaisseur=18)
            image.blit(lueur, (x - 9 - 16, boss.y - 16),
                       special_flags=pygame.BLEND_RGB_ADD)
            image.fill(config.BLANC, (x - 3, boss.y, 6, hauteur))


BossGridlock.dessiner_rayons = _dessiner_rayons

BOSS = {"sunset": BossSunset, "gridlock": BossGridlock, "core": BossCore}
