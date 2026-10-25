# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Effets spéciaux (« juice ») : particules, étincelles, textes flottants,
    ondes de choc, tremblement d'écran, flash, gel d'image (hit-stop) et
    ralenti. Toutes les entités vivent dans des Liste chaînées maison.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Débris de briques rotatifs, éclairs, confettis de victoire.
"""

import math
import random

import pygame

from structures.liste import Liste
from moteur import config
from moteur.police_pixel import dessiner_texte
from moteur.rendu import attenuer

PARTICULES_MAX = {"bas": 150, "moyen": 400, "haut": 900}


class Particule:
    """
    Petit carré lumineux soumis à la gravité qui disparaît en fondu.
    Attributs : x, y, vx, vy (float), vie, vie_max (s), couleur, taille,
                gravite (px/s²), frottement (0..1 par seconde).
    """

    __slots__ = ("x", "y", "vx", "vy", "vie", "vie_max", "couleur", "taille",
                 "gravite", "frottement")

    def __init__(self, x, y, vx, vy, vie, couleur, taille=3, gravite=600,
                 frottement=0.0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.vie = vie
        self.vie_max = vie
        self.couleur = couleur
        self.taille = taille
        self.gravite = gravite
        self.frottement = frottement

    def mettre_a_jour(self, dt):
        """
        But : avancer la particule d'un pas de temps.
        Entrée : dt (float) secondes. Sortie : (bool) True si encore vivante.
        """
        self.vie -= dt
        if self.frottement:
            facteur = max(0.0, 1 - self.frottement * dt)
            self.vx *= facteur
            self.vy *= facteur
        self.vy += self.gravite * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        return self.vie > 0


class TexteFlottant:
    """Texte qui monte, grossit puis disparaît (« +50 », « COMBO x5 »)."""

    def __init__(self, texte, x, y, couleur, echelle=2, duree=0.9,
                 vitesse=-60):
        self.texte = texte
        self.x = x
        self.y = y
        self.couleur = couleur
        self.echelle = echelle
        self.vie = duree
        self.duree = duree
        self.vitesse = vitesse

    def mettre_a_jour(self, dt):
        """
        But : faire monter le texte. Entrée : dt (float).
        Sortie : (bool) True si encore visible.
        """
        self.vie -= dt
        self.y += self.vitesse * dt
        return self.vie > 0


class OndeDeChoc:
    """Anneau lumineux qui s'élargit (explosions, perte de vie)."""

    def __init__(self, x, y, couleur, rayon_max=120, duree=0.45, epaisseur=6):
        self.x = x
        self.y = y
        self.couleur = couleur
        self.rayon_max = rayon_max
        self.vie = duree
        self.duree = duree
        self.epaisseur = epaisseur

    def mettre_a_jour(self, dt):
        """
        But : élargir l'anneau. Entrée : dt (float).
        Sortie : (bool) True si encore visible.
        """
        self.vie -= dt
        return self.vie > 0


class GestionnaireEffets:
    """
    Centralise tous les effets visuels d'un écran de jeu.
    Attributs :
        particules, textes, ondes : Liste chaînées d'effets vivants.
        tremblement : intensité courante du tremblement (px).
        flash : opacité du flash blanc (0..1).
        gel : temps de gel restant (hit-stop, s).
        ralenti / duree_ralenti : facteur de temps et durée restante.
        qualite : "bas", "moyen" ou "haut" (nombre max de particules).
    """

    def __init__(self):
        self.particules = Liste()
        self.textes = Liste()
        self.ondes = Liste()
        self.tremblement = 0.0
        self.tremblement_actif = True
        self.flash = 0.0
        self.couleur_flash = config.BLANC
        self.gel = 0.0
        self.ralenti = 1.0
        self.duree_ralenti = 0.0
        self.qualite = "haut"

    # --- Création d'effets -----------------------------------------------

    def _place_disponible(self):
        """Indique si l'on peut encore ajouter une particule."""
        return len(self.particules) < PARTICULES_MAX[self.qualite]

    def explosion(self, x, y, couleur, nombre=18, vitesse=260, taille=3,
                  vie=0.7, gravite=500):
        """
        But : projeter des particules dans toutes les directions.
        Entrées : x, y (float) : centre ; couleur (tuple) ; nombre (int) ;
                  vitesse (float) px/s ; taille (int) ; vie (s) ; gravite.
        Sortie : aucune.
        """
        for _ in range(nombre):
            if not self._place_disponible():
                return
            angle = random.uniform(0, 2 * math.pi)
            norme = random.uniform(0.25, 1.0) * vitesse
            teinte = couleur if random.random() < 0.75 else config.BLANC
            self.particules.ajouter_fin(Particule(
                x, y, math.cos(angle) * norme, math.sin(angle) * norme,
                random.uniform(0.5, 1.0) * vie, teinte,
                random.randint(max(1, taille - 1), taille + 1), gravite,
                frottement=1.5))

    def debris_brique(self, rect, couleur):
        """
        But : faire éclater une brique en petits morceaux de sa couleur.
        Entrées : rect (pygame.Rect) : brique détruite ; couleur (tuple).
        Sortie : aucune.
        """
        for _ in range(16):
            if not self._place_disponible():
                return
            x = random.uniform(rect.left, rect.right)
            y = random.uniform(rect.top, rect.bottom)
            vx = (x - rect.centerx) * random.uniform(4, 9)
            vy = random.uniform(-260, -40)
            self.particules.ajouter_fin(Particule(
                x, y, vx, vy, random.uniform(0.45, 0.9), couleur,
                random.randint(2, 5), gravite=900, frottement=0.8))

    def etincelles(self, x, y, couleur, direction_y=-1, nombre=6):
        """
        But : petite gerbe d'étincelles (rebond sur raquette ou mur).
        Entrées : x, y (float) ; couleur (tuple) ; direction_y (+1/-1) :
                  sens principal ; nombre (int).
        Sortie : aucune.
        """
        axe = math.pi / 2 if direction_y > 0 else -math.pi / 2
        for _ in range(nombre):
            if not self._place_disponible():
                return
            angle = axe + random.uniform(-1.1, 1.1)
            norme = random.uniform(120, 320)
            self.particules.ajouter_fin(Particule(
                x, y, math.cos(angle) * norme, math.sin(angle) * norme,
                random.uniform(0.15, 0.35), couleur, 2, gravite=300))

    def trainee(self, x, y, couleur, taille=3):
        """
        But : laisser une particule immobile qui s'éteint (traînée).
        Entrées : x, y (float) ; couleur (tuple) ; taille (int).
        Sortie : aucune.
        """
        if self._place_disponible():
            self.particules.ajouter_fin(Particule(
                x + random.uniform(-2, 2), y + random.uniform(-2, 2),
                0, 0, 0.25, couleur, taille, gravite=0))

    def texte(self, texte, x, y, couleur, echelle=2, duree=0.9, vitesse=-60):
        """
        But : afficher un texte flottant.
        Entrées : texte (str) ; x, y ; couleur ; echelle ; duree ; vitesse.
        Sortie : aucune.
        """
        self.textes.ajouter_fin(TexteFlottant(texte, x, y, couleur, echelle,
                                              duree, vitesse))

    def onde(self, x, y, couleur, rayon_max=120, duree=0.45, epaisseur=6):
        """
        But : lancer une onde de choc circulaire.
        Entrées : x, y ; couleur ; rayon_max (px) ; duree (s) ; epaisseur.
        Sortie : aucune.
        """
        self.ondes.ajouter_fin(OndeDeChoc(x, y, couleur, rayon_max, duree,
                                          epaisseur))

    def secouer(self, force):
        """
        But : faire trembler l'écran (les secousses ne s'additionnent pas,
        on garde la plus forte).
        Entrée : force (float) : amplitude en pixels.
        Sortie : aucune.
        """
        self.tremblement = max(self.tremblement, force)

    def eclair(self, force=0.6, couleur=config.BLANC):
        """
        But : flash plein écran.
        Entrées : force (float 0..1) ; couleur (tuple). Sortie : aucune.
        """
        self.flash = max(self.flash, force)
        self.couleur_flash = couleur

    def geler(self, duree):
        """
        But : geler l'action quelques millisecondes (hit-stop).
        Entrée : duree (float) secondes. Sortie : aucune.
        """
        self.gel = max(self.gel, duree)

    def ralentir(self, facteur, duree):
        """
        But : ralentir le temps du jeu (ex. dernière brique).
        Entrées : facteur (float, 0.3 = 30 % de la vitesse) ; duree (s réelles).
        Sortie : aucune.
        """
        self.ralenti = facteur
        self.duree_ralenti = duree

    # --- Mise à jour et dessin -------------------------------------------

    def facteur_temps(self):
        """
        But : facteur à appliquer au temps du jeu (0 pendant un gel).
        Entrée : aucune. Sortie : (float).
        """
        if self.gel > 0:
            return 0.0
        return self.ralenti

    def mettre_a_jour(self, dt):
        """
        But : faire vivre les effets (avec le temps réel, pas le temps du
        jeu : les particules continuent pendant un gel, c'est plus vivant).
        Entrée : dt (float) secondes réelles. Sortie : aucune.
        """
        self.gel = max(0.0, self.gel - dt)
        if self.duree_ralenti > 0:
            self.duree_ralenti -= dt
            if self.duree_ralenti <= 0:
                self.ralenti = 1.0
        self.tremblement = max(0.0, self.tremblement - dt * 40)
        self.flash = max(0.0, self.flash - dt * 3)
        pas = dt * (0.35 if self.gel > 0 else 1.0)
        self.particules.retirer_si(lambda p: not p.mettre_a_jour(pas))
        self.textes.retirer_si(lambda t: not t.mettre_a_jour(dt))
        self.ondes.retirer_si(lambda o: not o.mettre_a_jour(dt))

    def decalage_tremblement(self):
        """
        But : tirer le décalage d'écran de l'image courante.
        Entrée : aucune. Sortie : (tuple) (dx, dy) en pixels.
        """
        if not self.tremblement_actif or self.tremblement < 0.5:
            return 0, 0
        force = self.tremblement
        return (int(random.uniform(-force, force)),
                int(random.uniform(-force, force)))

    def dessiner(self, ecran, textes=True):
        """
        But : dessiner particules, ondes et (si textes) textes flottants.
        Entrées : ecran (Surface) ; textes (bool). Sortie : aucune.
        """
        for onde in self.ondes:
            avance = 1 - onde.vie / onde.duree
            rayon = int(onde.rayon_max * (1 - (1 - avance) ** 3))
            epaisseur = max(1, int(onde.epaisseur * (1 - avance)))
            if rayon > epaisseur:
                pygame.draw.circle(ecran, attenuer(onde.couleur, 1 - avance * 0.7),
                                   (int(onde.x), int(onde.y)), rayon, epaisseur)

        for p in self.particules:
            ratio = p.vie / p.vie_max
            couleur = attenuer(p.couleur, 0.35 + 0.65 * ratio)
            taille = max(1, int(p.taille * (0.4 + 0.6 * ratio)))
            ecran.fill(couleur, (int(p.x), int(p.y), taille, taille),
                       special_flags=pygame.BLEND_RGB_ADD)

        if textes:
            self.dessiner_textes(ecran)

    def dessiner_textes(self, ecran, miroir_y=None):
        """
        But : textes flottants (« +100 », « COMBO x4 »...).
        Entrées : ecran ; miroir_y (float ou None) : si donné, chaque texte est placé à
                  miroir_y - y (vue retournée du joueur du haut en Duel, textes à l'endroit).
        """
        for t in self.textes:
            ratio = t.vie / t.duree
            agrandi = 1 if ratio < 0.85 else 2
            alpha = 255 if ratio > 0.3 else int(255 * ratio / 0.3)
            y = t.y if miroir_y is None else miroir_y - t.y
            dessiner_texte(ecran, t.texte, t.x, y, t.echelle + agrandi - 1,
                           t.couleur, alpha=alpha)

    def dessiner_flash(self, ecran):
        """
        But : dessiner le flash plein écran par-dessus tout le reste.
        Entrée : ecran (Surface). Sortie : aucune.
        """
        if self.flash > 0.01:
            voile = pygame.Surface(ecran.get_size())
            voile.fill(self.couleur_flash)
            voile.set_alpha(int(200 * self.flash))
            ecran.blit(voile, (0, 0))
