# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Police bitmap 5x7 dessinée en code (aucun fichier externe) et rendu de
    texte néon : lettres pixel, ombre portée, halo lumineux. Les rendus
    sont mis en cache car le texte change rarement d'une image à l'autre.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Minuscules, alignement justifié.
"""

import unicodedata

import pygame

from moteur.rendu import halo

# Chaque glyphe : 7 lignes de 5 caractères, "#" = pixel allumé.
GLYPHES = {
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".####"],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": [".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "J": ["..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "N": ["#...#", "#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "Q": [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."],
    "X": ["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "Z": ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": [".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."],
    " ": [".....", ".....", ".....", ".....", ".....", ".....", "....."],
    ".": [".....", ".....", ".....", ".....", ".....", ".##..", ".##.."],
    ",": [".....", ".....", ".....", ".....", ".##..", "..#..", ".#..."],
    ":": [".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."],
    "!": ["..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."],
    "?": [".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."],
    "-": [".....", ".....", ".....", ".###.", ".....", ".....", "....."],
    "+": [".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."],
    "x": [".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"],
    "/": ["....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."],
    "'": ["..#..", "..#..", ".#...", ".....", ".....", ".....", "....."],
    "(": ["...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."],
    ")": [".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."],
    "<": ["...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."],
    ">": [".#...", "..#..", "...#.", "....#", "...#.", "..#..", ".#..."],
    "|": ["..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "■": [".....", "####.", "####.", "####.", "####.", "####.", "....."],
    "□": [".....", "####.", "#..#.", "#..#.", "#..#.", "####.", "....."],
    "%": ["##..#", "##..#", "...#.", "..#..", ".#...", "#..##", "#..##"],
    "#": [".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."],
    "*": [".....", "#.#.#", ".###.", "#####", ".###.", "#.#.#", "....."],
    "=": [".....", ".....", "#####", ".....", "#####", ".....", "....."],
    "&": [".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"],
    "\u2190": [".....", "..#..", ".#...", "#####", ".#...", "..#..", "....."],
    "\u2192": [".....", "..#..", "...#.", "#####", "...#.", "..#..", "....."],
    "\u2191": ["..#..", ".###.", "#.#.#", "..#..", "..#..", "..#..", "..#.."],
    "\u2193": ["..#..", "..#..", "..#..", "..#..", "#.#.#", ".###.", "..#.."],
    "[": [".###.", ".#...", ".#...", ".#...", ".#...", ".#...", ".###."],
    "]": [".###.", "...#.", "...#.", "...#.", "...#.", "...#.", ".###."],
    "_": [".....", ".....", ".....", ".....", ".....", ".....", "#####"],
    "♥": [".....", ".#.#.", "#####", "#####", ".###.", "..#..", "....."],
    "★": ["..#..", "..#..", "#####", ".###.", ".###.", "##.##", "#...#"],
}

_cache_glyphes = {}
_cache_textes = {}
TAILLE_CACHE_MAX = 400


def normaliser(texte):
    """
    But : passer le texte en majuscules sans accents (É -> E) pour qu'il
    corresponde aux glyphes disponibles. Le « x » minuscule est gardé
    car il sert de signe de multiplication (COMBO x8).
    Entrée : texte (str). Sortie : (str) texte affichable.
    """
    resultat = []
    for car in texte:
        if car == "x" or (car in GLYPHES and not car.isalpha()):
            resultat.append(car)
            continue
        decompose = unicodedata.normalize("NFD", car)
        base = "".join(c for c in decompose if not unicodedata.combining(c))
        resultat.append(base.upper())
    return "".join(resultat)


def _glyphe(car, echelle, couleur):
    """
    But : produire (avec cache) la surface d'un caractère.
    Entrées : car (str), echelle (int) : taille d'un pixel, couleur (tuple).
    Sortie : (pygame.Surface) glyphe 5x7 agrandi.
    """
    cle = (car, echelle, couleur)
    surface = _cache_glyphes.get(cle)
    if surface is None:
        motif = GLYPHES.get(car, GLYPHES["?"])
        surface = pygame.Surface((5 * echelle, 7 * echelle), pygame.SRCALPHA)
        for ligne, rangee in enumerate(motif):
            for colonne, pixel in enumerate(rangee):
                if pixel == "#":
                    surface.fill(couleur, (colonne * echelle, ligne * echelle,
                                           echelle, echelle))
        _cache_glyphes[cle] = surface
    return surface


def taille_texte(texte, echelle):
    """
    But : calculer la taille en pixels d'un texte.
    Entrées : texte (str), echelle (int).
    Sortie : (tuple) (largeur, hauteur).
    """
    nb = len(normaliser(texte))
    if nb == 0:
        return 0, 7 * echelle
    return nb * 6 * echelle - echelle, 7 * echelle


def rendre_texte(texte, echelle, couleur, ombre=True, lueur=True):
    """
    But : fabriquer (avec cache) la surface d'un texte néon complet.
    Entrées :
        texte (str) : contenu.
        echelle (int) : taille d'un pixel de police (2 = petit, 6 = titre).
        couleur (tuple) : couleur RVB.
        ombre (bool) : ombre portée violette décalée.
        lueur (bool) : halo flou autour des lettres.
    Sortie : (pygame.Surface) texte prêt à être affiché.
    """
    cle = (texte, echelle, couleur, ombre, lueur)
    surface = _cache_textes.get(cle)
    if surface is not None:
        return surface

    propre = normaliser(texte)
    largeur, hauteur = taille_texte(propre, echelle)
    marge = echelle * 3 if lueur else echelle
    surface = pygame.Surface((largeur + 2 * marge, hauteur + 2 * marge),
                             pygame.SRCALPHA)
    nette = pygame.Surface((max(1, largeur), hauteur), pygame.SRCALPHA)
    for i, car in enumerate(propre):
        nette.blit(_glyphe(car, echelle, couleur), (i * 6 * echelle, 0))

    if lueur:
        lumiere = halo(nette, rayon=echelle * 2, intensite=0.9)
        surface.blit(lumiere, (marge - (lumiere.get_width() - largeur) // 2,
                               marge - (lumiere.get_height() - hauteur) // 2))
    if ombre:
        sombre = nette.copy()
        sombre.fill((60, 0, 90, 255), special_flags=pygame.BLEND_RGBA_MULT)
        decalage = max(1, echelle // 2)
        surface.blit(sombre, (marge + decalage, marge + decalage))
    surface.blit(nette, (marge, marge))

    if len(_cache_textes) > TAILLE_CACHE_MAX:
        _cache_textes.clear()
    _cache_textes[cle] = surface
    return surface


def dessiner_texte(ecran, texte, x, y, echelle=3, couleur=(255, 255, 255),
                   ancrage="centre", ombre=True, lueur=True, alpha=255):
    """
    But : afficher un texte néon à une position donnée.
    Entrées :
        ecran (Surface) : surface cible.
        texte (str), x, y (float) : contenu et point d'ancrage.
        echelle (int), couleur (tuple) : apparence.
        ancrage (str) : "centre", "gauche", "droite", "haut_gauche".
        alpha (int) : opacité 0..255.
    Sortie : (pygame.Rect) zone occupée par le texte.
    """
    surface = rendre_texte(texte, echelle, couleur, ombre, lueur)
    if alpha < 255:
        surface = surface.copy()
        surface.set_alpha(alpha)
    rect = surface.get_rect()
    if ancrage == "centre":
        rect.center = (int(x), int(y))
    elif ancrage == "gauche":
        rect.midleft = (int(x), int(y))
    elif ancrage == "droite":
        rect.midright = (int(x), int(y))
    else:
        rect.topleft = (int(x), int(y))
    ecran.blit(surface, rect)
    return rect
