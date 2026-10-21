# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Outils de rendu néon : halos lumineux mis en cache, filtre CRT
    (scanlines + vignette), aberration chromatique, et gestion de la
    fenêtre (rendu interne 1280x720 mis à l'échelle, plein écran F11).

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Courbure d'écran CRT, bloom global optionnel.
"""

import math

import pygame

from moteur import config

_cache_halos = {}


def flouter(surface, rayon):
    """
    But : flouter une surface (gaussien si disponible, sinon réduction /
    agrandissement lissé, qui donne un flou proche).
    Entrées : surface (Surface), rayon (int) : force du flou.
    Sortie : (Surface) nouvelle surface floutée, même taille.
    """
    rayon = max(1, int(rayon))
    try:
        return pygame.transform.gaussian_blur(surface, rayon)
    except (AttributeError, ValueError, pygame.error):
        largeur, hauteur = surface.get_size()
        facteur = max(2, rayon)
        petite = pygame.transform.smoothscale(
            surface, (max(1, largeur // facteur), max(1, hauteur // facteur)))
        return pygame.transform.smoothscale(petite, (largeur, hauteur))


def halo(surface, rayon=6, intensite=1.0):
    """
    But : créer le halo flou (avec transparence) d'une surface.
    Entrées : surface (Surface SRCALPHA), rayon (int), intensite (float 0..1+).
    Sortie : (Surface) halo plus grand de 2*rayon dans chaque direction.
    """
    marge = rayon * 2
    largeur, hauteur = surface.get_size()
    base = pygame.Surface((largeur + 2 * marge, hauteur + 2 * marge),
                          pygame.SRCALPHA)
    base.blit(surface, (marge, marge))
    flou = flouter(base, rayon)
    if intensite != 1.0:
        niveau = max(0, min(255, int(255 * intensite)))
        flou.fill((255, 255, 255, niveau), special_flags=pygame.BLEND_RGBA_MULT)
    return flou


def halo_rect(largeur, hauteur, couleur, rayon=8, epaisseur=3):
    """
    But : halo additif (fond noir) d'un rectangle néon, mis en cache.
    À afficher avec special_flags=pygame.BLEND_RGB_ADD.
    Entrées : largeur, hauteur (int), couleur (tuple), rayon (int) : étendue
              de la lueur, epaisseur (int) : trait du contour lumineux.
    Sortie : (Surface) halo ; position = coin du rectangle - rayon*2.
    """
    cle = ("rect", largeur, hauteur, couleur, rayon, epaisseur)
    surface = _cache_halos.get(cle)
    if surface is None:
        marge = rayon * 2
        surface = pygame.Surface((largeur + 2 * marge, hauteur + 2 * marge))
        surface.fill(config.NOIR)
        pygame.draw.rect(surface, couleur,
                         (marge, marge, largeur, hauteur), epaisseur,
                         border_radius=3)
        surface = flouter(surface, rayon)
        _cache_halos[cle] = surface
    return surface


def halo_cercle(rayon_objet, couleur, rayon=10, plein=True):
    """
    But : halo additif (fond noir) d'un disque, mis en cache.
    Entrées : rayon_objet (int), couleur (tuple), rayon (int) : lueur,
              plein (bool) : disque plein ou simple anneau.
    Sortie : (Surface) halo carré centré sur le disque.
    """
    cle = ("cercle", rayon_objet, couleur, rayon, plein)
    surface = _cache_halos.get(cle)
    if surface is None:
        cote = (rayon_objet + rayon * 2) * 2
        surface = pygame.Surface((cote, cote))
        surface.fill(config.NOIR)
        pygame.draw.circle(surface, couleur, (cote // 2, cote // 2),
                           rayon_objet, 0 if plein else 3)
        surface = flouter(surface, rayon)
        _cache_halos[cle] = surface
    return surface


def attenuer(couleur, facteur):
    """
    But : assombrir (facteur < 1) ou éclaircir (facteur > 1) une couleur.
    Entrées : couleur (tuple RVB), facteur (float). Sortie : (tuple RVB).
    """
    return tuple(max(0, min(255, int(c * facteur))) for c in couleur[:3])


def melanger(couleur_a, couleur_b, t):
    """
    But : interpolation linéaire entre deux couleurs.
    Entrées : couleur_a, couleur_b (tuple RVB), t (float 0..1).
    Sortie : (tuple RVB).
    """
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(couleur_a, couleur_b))


class FiltreCRT:
    """
    Filtre rétro appliqué sur l'image finale : scanlines, vignette, et
    aberration chromatique ponctuelle lors des gros impacts.
    """

    def __init__(self, largeur, hauteur):
        """
        But : pré-calculer les calques du filtre.
        Entrées : largeur, hauteur (int) : taille de l'image interne.
        Sortie : aucune.
        """
        self.actif = True
        self.scanlines = pygame.Surface((largeur, hauteur), pygame.SRCALPHA)
        for y in range(0, hauteur, 3):
            pygame.draw.line(self.scanlines, (0, 0, 0, 55), (0, y),
                             (largeur, y))
        self.vignette = self._creer_vignette(largeur, hauteur)
        self.aberration = 0.0

    @staticmethod
    def _creer_vignette(largeur, hauteur):
        """
        But : calculer un assombrissement radial des bords (en petit puis
        agrandi en lissé, pour rester rapide en Python pur).
        Entrées : largeur, hauteur (int). Sortie : (Surface SRCALPHA).
        """
        petit_l, petit_h = 160, 90
        petite = pygame.Surface((petit_l, petit_h), pygame.SRCALPHA)
        for y in range(petit_h):
            for x in range(petit_l):
                dx = (x - petit_l / 2) / (petit_l / 2)
                dy = (y - petit_h / 2) / (petit_h / 2)
                distance = math.sqrt(dx * dx * 0.8 + dy * dy)
                alpha = max(0.0, distance - 0.65) * 230
                petite.set_at((x, y), (0, 0, 0, min(170, int(alpha))))
        return pygame.transform.smoothscale(petite, (largeur, hauteur))

    def declencher_aberration(self, force=1.0):
        """
        But : lancer un décalage des couleurs (gros impact).
        Entrée : force (float) : 1.0 = décalage de 3 px.
        Sortie : aucune.
        """
        self.aberration = max(self.aberration, force)

    def mettre_a_jour(self, dt):
        """
        But : faire décroître l'aberration.
        Entrée : dt (float) : secondes écoulées. Sortie : aucune.
        """
        self.aberration = max(0.0, self.aberration - dt * 4)

    def appliquer(self, image):
        """
        But : appliquer le filtre sur l'image finale (modifiée sur place).
        Entrée : image (Surface). Sortie : aucune.
        """
        if self.aberration > 0.05:
            decalage = int(round(self.aberration * 3))
            if decalage:
                rouge = image.copy()
                rouge.fill((255, 0, 0), special_flags=pygame.BLEND_RGB_MULT)
                image.fill((0, 255, 255), special_flags=pygame.BLEND_RGB_MULT)
                image.blit(rouge, (decalage, 0),
                           special_flags=pygame.BLEND_RGB_ADD)
        if self.actif:
            image.blit(self.scanlines, (0, 0))
            image.blit(self.vignette, (0, 0))


class Ecran:
    """
    Fenêtre du jeu. On dessine toujours sur une image interne 1280x720 qui
    est ensuite mise à l'échelle (avec bandes noires) dans la fenêtre.
    """

    def __init__(self, plein_ecran=False):
        """
        But : créer la fenêtre et l'image interne.
        Entrée : plein_ecran (bool). Sortie : aucune.
        """
        self.image = pygame.Surface((config.LARGEUR, config.HAUTEUR))
        self.plein_ecran = plein_ecran
        self.fenetre = None
        self.zone = pygame.Rect(0, 0, config.LARGEUR, config.HAUTEUR)
        self.tremblement = (0, 0)
        self._ouvrir()

    def _ouvrir(self):
        """
        But : (ré)ouvrir la fenêtre selon le mode courant.
        Entrée : aucune. Sortie : aucune.
        """
        if self.plein_ecran:
            self.fenetre = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.fenetre = pygame.display.set_mode(
                (config.LARGEUR, config.HAUTEUR), pygame.RESIZABLE)
        self._calculer_zone()

    def basculer_plein_ecran(self):
        """
        But : passer du mode fenêtré au plein écran et inversement (F11).
        Entrée : aucune. Sortie : aucune.
        """
        self.plein_ecran = not self.plein_ecran
        self._ouvrir()

    def redimensionner(self):
        """
        But : recalculer la zone d'affichage après un redimensionnement.
        Entrée : aucune. Sortie : aucune.
        """
        self._calculer_zone()

    def _calculer_zone(self):
        """
        But : trouver le plus grand rectangle 16:9 qui tient dans la
        fenêtre, centré (bandes noires sur les côtés si besoin).
        Entrée : aucune. Sortie : aucune.
        """
        largeur, hauteur = self.fenetre.get_size()
        echelle = min(largeur / config.LARGEUR, hauteur / config.HAUTEUR)
        zone_l = int(config.LARGEUR * echelle)
        zone_h = int(config.HAUTEUR * echelle)
        self.zone = pygame.Rect((largeur - zone_l) // 2,
                                (hauteur - zone_h) // 2, zone_l, zone_h)

    def vers_interne(self, position):
        """
        But : convertir une position de souris (fenêtre) en coordonnées
        de l'image interne 1280x720.
        Entrée : position (tuple) (x, y) fenêtre.
        Sortie : (tuple) (x, y) internes.
        """
        x = (position[0] - self.zone.x) * config.LARGEUR / max(1, self.zone.w)
        y = (position[1] - self.zone.y) * config.HAUTEUR / max(1, self.zone.h)
        return x, y

    def presenter(self):
        """
        But : copier l'image interne dans la fenêtre (avec tremblement)
        et afficher le résultat.
        Entrée : aucune. Sortie : aucune.
        """
        self.fenetre.fill(config.NOIR)
        dx, dy = self.tremblement
        if self.zone.size == (config.LARGEUR, config.HAUTEUR):
            self.fenetre.blit(self.image, (self.zone.x + dx, self.zone.y + dy))
        else:
            echelle = self.zone.w / config.LARGEUR
            image = pygame.transform.smoothscale(self.image, self.zone.size)
            self.fenetre.blit(image, (self.zone.x + int(dx * echelle),
                                      self.zone.y + int(dy * echelle)))
        pygame.display.flip()
