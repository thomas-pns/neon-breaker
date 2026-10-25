# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Briques d'affichage tête haute (HUD) réutilisées par tous les modes :
    panneau néon, bloc « joueur » vertical (score, multiplicateur, combo,
    inventaire de pouvoirs, jauge OVERDRIVE, effets actifs) ou horizontal
    (mode Course), vies, rappel des commandes.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Icônes dessinées pour chaque pouvoir.
"""

import math

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from moteur.rendu import halo_rect, attenuer
from jeu.capsule import CATALOGUE, OR_POUVOIR

COULEURS_MULTI = {1: config.CYAN, 2: config.VERT, 3: config.AMBRE,
                  5: config.ROSE, 8: config.BLANC}
GRIS = (170, 140, 220)

_cache_panneaux = {}


def panneau(image, rect, couleur):
    """
    But : dessiner un cadre néon semi-transparent.
    Entrées : image (Surface), rect (Rect), couleur (tuple). Sortie : aucune.
    """
    cle = rect.size
    fond = _cache_panneaux.get(cle)
    if fond is None:
        fond = pygame.Surface(rect.size, pygame.SRCALPHA)
        fond.fill((10, 0, 26, 200))
        _cache_panneaux[cle] = fond
    image.blit(fond, rect.topleft)
    lueur = halo_rect(rect.w, rect.h, attenuer(couleur, 0.45), rayon=8)
    image.blit(lueur, (rect.x - 16, rect.y - 16), special_flags=pygame.BLEND_RGB_ADD)
    pygame.draw.rect(image, couleur, rect, 2, border_radius=6)


def etiquette(image, texte, x, y, couleur=GRIS, ancrage="centre"):
    """But : petit titre de rubrique."""
    dessiner_texte(image, texte, x, y, 2, couleur, lueur=False, ancrage=ancrage)


def barre(image, rect, ratio, couleur, fond=(60, 30, 90)):
    """But : barre de progression arrondie."""
    pygame.draw.rect(image, fond, rect, border_radius=3)
    rempli = rect.copy()
    rempli.w = int(rect.w * max(0.0, min(1.0, ratio)))
    if rempli.w > 0:
        pygame.draw.rect(image, couleur, rempli, border_radius=3)


# --- Éléments ---------------------------------------------------------------------

def dessiner_multiplicateur(image, cx, y, joueur, temps, echelle=6):
    """But : « x3 » qui tremble quand il est élevé + barre de combo."""
    multi = joueur.multiplicateur
    couleur = COULEURS_MULTI.get(multi, config.BLANC)
    agitation = 0 if multi < 3 else math.sin(temps * 40) * (multi / 4)
    dessiner_texte(image, f"x{multi}", cx + agitation, y, echelle + (1 if multi >= 5 else 0),
                   couleur)
    etiquette(image, f"COMBO {joueur.combo}", cx, y + echelle * 6, config.BLANC)
    paliers = sorted(seuil for seuil, _ in config.PALIERS_COMBO)
    suivant = next((s for s in paliers if s > joueur.combo), None)
    precedent = max((s for s in paliers if s <= joueur.combo), default=0)
    ratio = (joueur.combo - precedent) / (suivant - precedent) if suivant else 1.0
    barre(image, pygame.Rect(cx - 70, y + echelle * 6 + 16, 140, 8), ratio, couleur)


def dessiner_inventaire(image, cx, y, joueur, touches=None, taille=44):
    """
    But : les 3 emplacements de pouvoirs (lettre dorée), l'emplacement
    choisi est entouré de blanc (modes 2 joueurs).
    Entrées : image ; cx, y (centre de la rangée) ; joueur ;
              touches (list de str ou None) : libellés sous les cases ;
              taille (int) : côté des cases.
    """
    ecart = taille + 8
    debut = cx - ecart * (config.TAILLE_INVENTAIRE - 1) / 2
    for i in range(config.TAILLE_INVENTAIRE):
        rect = pygame.Rect(0, 0, taille, taille - 6)
        rect.center = (int(debut + i * ecart), int(y))
        plein = i < len(joueur.inventaire)
        couleur = OR_POUVOIR if plein else (90, 60, 120)
        pygame.draw.rect(image, (20, 5, 40), rect, border_radius=5)
        if plein:
            effet = CATALOGUE[joueur.inventaire[i]]
            lueur = halo_rect(rect.w, rect.h, attenuer(OR_POUVOIR, 0.5), rayon=5)
            image.blit(lueur, (rect.x - 10, rect.y - 10), special_flags=pygame.BLEND_RGB_ADD)
            from moteur.icones import dessiner_icone
            if not dessiner_icone(image, effet.code, rect.center, OR_POUVOIR,
                                  3 if taille >= 40 else 2):
                dessiner_texte(image, effet.lettre, rect.centerx, rect.centery, 3,
                               config.BLANC, lueur=False)
        selection = joueur.profil != "solo" and i == joueur.selection and plein
        pygame.draw.rect(image, config.BLANC if selection else couleur, rect,
                         3 if selection else 2, border_radius=5)
        if touches:
            etiquette(image, touches[i], rect.centerx, rect.bottom + 10)


def dessiner_overdrive(image, rect, joueur, temps, touche=""):
    """
    But : jauge OVERDRIVE en 10 segments ; pleine, elle clignote ; pendant
    la SUPERNOVA, elle affiche le temps restant.
    """
    if not joueur.avec_overdrive:
        etiquette(image, "OVERDRIVE OFF", rect.centerx, rect.centery, (90, 60, 120))
        return
    segments = 10
    largeur = (rect.w - (segments - 1) * 3) / segments
    if joueur.supernova > 0:
        ratio = joueur.supernova / config.DUREE_SUPERNOVA
        couleur = config.BLANC
    else:
        ratio = joueur.overdrive
        couleur = config.ROSE if ratio < 1 else (
            config.BLANC if int(temps * 8) % 2 else config.AMBRE)
    for k in range(segments):
        seg = pygame.Rect(int(rect.x + k * (largeur + 3)), rect.y, int(largeur), rect.h)
        allume = ratio * segments > k
        pygame.draw.rect(image, couleur if allume else (55, 25, 80), seg, border_radius=2)
    if joueur.supernova > 0:
        etiquette(image, "SUPERNOVA !", rect.centerx, rect.bottom + 12, config.BLANC)
    elif joueur.overdrive_pret():
        etiquette(image, f"PRET ! {touche}", rect.centerx, rect.bottom + 12, config.AMBRE)


def lignes_effets(joueur):
    """
    But : liste des effets à afficher : (code de l'icône, nom, couleur, ratio restant).
    Entrée : joueur. Sortie : (list de tuples).
    """
    lignes = []
    for code, reste in sorted(joueur.effets.items(), key=lambda e: -e[1]):
        effet = CATALOGUE.get(code)
        if effet is None:
            continue
        lignes.append((effet.code, effet.nom, effet.couleur(),
                       reste / max(0.1, effet.duree)))
    if joueur.aimant_prises:
        lignes.append(("aimant", f"AIMANT x{joueur.aimant_prises}", (60, 255, 140), None))
    if joueur.filets:
        lignes.append(("filet", "FILET" + (" x2" if joueur.filets > 1 else ""),
                       (60, 255, 140), None))
    if joueur.bombe_armee:
        lignes.append(("bombe", "BOMBE ARMEE", OR_POUVOIR, None))
    return lignes


def _pastille(image, rect, code, couleur):
    """But : petite case sombre bordée de la couleur de l'effet, avec son icône."""
    from moteur.icones import dessiner_icone
    pygame.draw.rect(image, (20, 4, 40), rect, border_radius=6)
    pygame.draw.rect(image, couleur, rect, 1, border_radius=6)
    dessiner_icone(image, code, rect.center, couleur, 2)


def dessiner_effets(image, x, y, largeur, joueur, max_lignes=4):
    """But : effets actifs, une ligne chacun (pastille, nom, barre de durée)."""
    for i, (code, nom, couleur, ratio) in enumerate(lignes_effets(joueur)[:max_lignes]):
        ligne_y = y + i * 30
        _pastille(image, pygame.Rect(x, ligne_y - 11, 24, 22), code, couleur)
        nb_caracteres = max(4, (largeur - 40) // 12)
        dessiner_texte(image, nom[:nb_caracteres], x + 32, ligne_y - 3, 2,
                       couleur, ancrage="gauche", lueur=False, ombre=False)
        if ratio is not None:
            barre(image, pygame.Rect(x + 32, ligne_y + 9, largeur - 42, 4), ratio, couleur)


def dessiner_vies(image, cx, y, vies, couleurs=(config.RAQUETTE_CORPS, config.RAQUETTE_BORD)):
    """But : vies sous forme de petites raquettes (3 par ligne)."""
    if vies > 6:
        dessiner_texte(image, f"x {vies}", cx, y, 3, couleurs[0])
        return
    for i in range(vies):
        rang, colonne = divmod(i, 3)
        rect = pygame.Rect(0, 0, 44, 10)
        rect.center = (cx - 52 + colonne * 52, y + rang * 22)
        pygame.draw.rect(image, couleurs[0], rect, border_radius=4)
        pygame.draw.rect(image, couleurs[1], rect, 2, border_radius=4)


def dessiner_commandes(image, rect, profil, y, app=None):
    """But : rappel des touches d'un profil (à jour des OPTIONS et de la manette), en deux colonnes."""
    if app is not None:
        from moteur.entrees import libelles_touches
        lignes = libelles_touches(app, profil)
    else:
        lignes = config.AIDE_TOUCHES[profil]
    for i, (touche, action) in enumerate(lignes):
        ligne_y = y + i * 22
        dessiner_texte(image, touche, rect.x + 14, ligne_y, 2, config.BLANC,
                       ancrage="gauche", lueur=False, ombre=False)
        dessiner_texte(image, action, rect.right - 14, ligne_y, 2, GRIS,
                       ancrage="droite", lueur=False, ombre=False)


# --- Blocs complets -----------------------------------------------------------------

def bloc_joueur_vertical(image, rect, joueur, y, temps, titre=None, touches_pouvoirs=None,
                         touche_overdrive="", score=True, aide_pouvoirs=False):
    """
    But : bloc complet d'un joueur dans un panneau latéral, à partir de y.
    Sortie : (int) ordonnée sous le bloc.
    """
    cx = rect.centerx
    if titre:
        dessiner_texte(image, titre, cx, y, 3, joueur.couleur_bord)
        y += 36
    if score:
        etiquette(image, "SCORE", cx, y)
        dessiner_texte(image, f"{joueur.score:07d}", cx, y + 30,
                       4 if rect.w >= 210 else 3, config.AMBRE)
        y += 72
    etiquette(image, "MULTIPLICATEUR", cx, y)
    dessiner_multiplicateur(image, cx, y + 38, joueur, temps, 5)
    y += 112
    if joueur.avec_pouvoirs:
        etiquette(image, "POUVOIRS", cx, y)
        dessiner_inventaire(image, cx, y + 34, joueur, touches_pouvoirs,
                            44 if rect.w >= 210 else 40)
        y += 94 if touches_pouvoirs else 74
        if aide_pouvoirs:
            dessiner_texte(image, "A/TAB CHOISIR  E LANCER", cx, y - 12, 1,
                           config.BLANC, lueur=False)
            y += 16
    etiquette(image, "OVERDRIVE", cx, y)
    dessiner_overdrive(image, pygame.Rect(rect.x + 18, y + 16, rect.w - 36, 14),
                       joueur, temps, touche_overdrive)
    y += 72
    dessiner_effets(image, rect.x + 14, y, rect.w - 20, joueur, 3)
    return y + 90


def bloc_joueur_horizontal(image, rect, joueur, temps, gauche_texte="", droite_texte=""):
    """
    But : bandeau compact d'un joueur (mode Course) : score, multiplicateur,
    inventaire, OVERDRIVE, effets.
    """
    panneau(image, rect, joueur.couleur_bord)
    etiquette_joueur = getattr(joueur, "etiquette", f"J{joueur.numero}")
    if len(etiquette_joueur) <= 2:
        dessiner_texte(image, etiquette_joueur, rect.x + 36, rect.y + 26, 4, joueur.couleur_bord)
    else:
        # Pseudo (jeu en ligne) : sur la ligne du bas, devant le texte de gauche.
        gauche_texte = f"{etiquette_joueur[:8]}  {gauche_texte}"
    dessiner_texte(image, f"{joueur.score:07d}", rect.x + 70, rect.y + 22, 3,
                   config.AMBRE, ancrage="gauche")
    multi = joueur.multiplicateur
    dessiner_texte(image, f"x{multi}", rect.x + 250, rect.y + 22, 3,
                   COULEURS_MULTI.get(multi, config.BLANC))
    if gauche_texte:
        etiquette(image, gauche_texte, rect.x + 70 if len(etiquette_joueur) <= 2 else rect.x + 16,
                  rect.y + 56, config.BLANC, "gauche")
    dessiner_inventaire(image, rect.x + 370, rect.y + 26, joueur, None, 34)
    dessiner_overdrive(image, pygame.Rect(rect.x + 300, rect.y + 52, 140, 9), joueur, temps)
    if droite_texte:
        dessiner_texte(image, droite_texte, rect.right - 70, rect.y + 24, 3, config.BLANC)
    lignes = lignes_effets(joueur)
    for i, (code, _, couleur, _) in enumerate(lignes[:4]):
        _pastille(image, pygame.Rect(rect.right - 124 + i * 28, rect.y + 44, 24, 22), code, couleur)


def dessiner_etoiles(image, obtenues, centre, taille=12, total=3, couleur=None, ecart=None,
                     masque=None):
    """
    But : rangée d'étoiles (pleines pour les obtenues, en creux pour les autres).
    Entrées : image ; obtenues (int) ; centre (x, y) ; taille (rayon) ; total (int) ;
              couleur (tuple ou None : or) ; ecart (px entre deux étoiles) ;
              masque (int ou None) : étoile k pleine si le bit k est mis (remplace obtenues).
    """
    couleur = couleur or config.OR
    ecart = ecart or taille * 2.4
    cx, cy = centre
    for k in range(total):
        x = cx + (k - (total - 1) / 2) * ecart
        points = []
        for i in range(10):
            angle = -math.pi / 2 + i * math.pi / 5
            rayon = taille if i % 2 == 0 else taille * 0.45
            points.append((x + math.cos(angle) * rayon, cy + math.sin(angle) * rayon))
        pleine = (masque >> k) & 1 if masque is not None else k < obtenues
        if pleine:
            pygame.draw.polygon(image, couleur, points)
            pygame.draw.polygon(image, (255, 250, 210), points, 1)
        else:
            pygame.draw.polygon(image, (40, 20, 70), points)
            pygame.draw.polygon(image, (110, 80, 150), points, 1)
