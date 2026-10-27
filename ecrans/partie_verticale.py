# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Partie au format vertical (téléphone), d'après la maquette B choisie par Thomas :
      - en haut, un bandeau : score, record, multiplicateur, info du mode, vies, jauge ;
      - au milieu, le terrain, à sa taille normale ;
      - en bas, une zone où glisser le doigt pour bouger la raquette (le doigt ne
        cache plus la balle), les 3 pouvoirs à gauche et la SUPERNOVA à droite.

    La logique du jeu ne change pas : le terrain garde ses coordonnées du format
    paysage. On le dessine dans une image paysage (avec ses effets), puis on recopie
    sa zone dans l'image verticale. Le jeu en ligne marche donc tel quel.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 26/10/2026
"""

import pygame

from jeu.capsule import CATALOGUE, OR_POUVOIR
from moteur import config
from moteur.icones import dessiner_icone
from moteur.police_pixel import dessiner_texte
from ecrans import hud
from ecrans.tactile import bouton

# Disposition (image verticale de 640 px de large, aux proportions du téléphone). La place
# en plus agrandit les commandes du bas.
MARGE_TERRAIN = 20


def decalage():
    """But : marge ajoutée en haut sur un écran plus allongé que 16:9."""
    if config.MARGES_CONNUES:                   # zone sûre mesurée (iPhone : encoche)
        return config.MARGE_HAUT_ECRAN
    return min(90, max(0, config.VERTICAL[1] - config.VERTICAL[0] * 16 // 9) // 2)


def bandeau_rect():
    return pygame.Rect(16, 18 + decalage(), config.VERTICAL[0] - 32, 160)
GRIS = (170, 140, 220)


def zone_monde(terrain):
    """But : zone de l'image paysage recopiée (le terrain et sa lueur)."""
    return terrain.rect.inflate(2 * MARGE_TERRAIN, 2 * MARGE_TERRAIN).clip(
        pygame.Rect((0, 0), config.PAYSAGE))


def zone_ecran(terrain):
    """But : où cette zone est posée dans l'image verticale (centrée, réduite si trop large)."""
    zone = zone_monde(terrain)
    largeur = min(zone.w, config.VERTICAL[0])
    hauteur = zone.h * largeur // zone.w
    return pygame.Rect((config.VERTICAL[0] - largeur) // 2, 186 + decalage(), largeur, hauteur)


def disposition(terrain):
    """
    But : rectangles des commandes du bas.
    Sortie : (dict) "glisse", "supernova" (Rect) et "pouvoirs" (list de Rect).
    """
    haut = zone_ecran(terrain).bottom + 14
    hauteur = config.VERTICAL[1] - 24 - config.MARGE_BAS_ECRAN - haut
    colonne = 120
    ecart = 14
    case = (hauteur - 2 * ecart) // 3
    return {
        "pouvoirs": [pygame.Rect(16, haut + i * (case + ecart), colonne, case) for i in range(3)],
        "supernova": pygame.Rect(config.VERTICAL[0] - 16 - colonne, haut, colonne, hauteur),
        "glisse": pygame.Rect(16 + colonne + ecart, haut,
                              config.VERTICAL[0] - 2 * (16 + colonne + ecart), hauteur),
    }


class CommandesVerticales:
    """
    Commandes au format vertical : glisser dans la zone du bas bouge la raquette
    (déplacement relatif, comme un pavé tactile), toucher le terrain lance la balle.
    Attributs : prise (tuple ou None) : (x du doigt, x de la raquette) au début du glisser.
    """

    def __init__(self):
        self.prise = None

    def lire(self, app, mode, joueur=None):
        joueur = joueur or mode.joueur_au_doigt()
        if joueur is None or joueur.raquette is None or joueur.terrain is None:
            return
        entrees = app.entrees
        terrain = joueur.terrain
        zones = disposition(terrain)
        glisse = zones["glisse"]
        souris = entrees.souris
        pose = entrees.doigt_pose if entrees.tactile else (souris if 1 in entrees.clics else None)
        if pose is not None:               # au doigt : dès qu'il se pose (réactif)
            if glisse.collidepoint(pose):
                self.prise = (pose[0], joueur.raquette.x)
            elif zone_ecran(terrain).collidepoint(pose):
                entrees.forcer("action", joueur.profil)
                entrees.forcer("action", "solo")        # en ligne : commandes du profil solo
        if entrees.tactile:
            if not entrees.doigts:
                self.prise = None
            elif self.prise is not None and entrees.souris_bougee:
                gain = terrain.rect.w / glisse.w * 1.15
                x = self.prise[1] + (souris[0] - self.prise[0]) * gain
                self._viser(joueur, terrain, x)
        elif entrees.souris_bougee and glisse.collidepoint(souris):
            # Souris (essai sur PC) : position directe dans la zone.
            x = terrain.rect.x + (souris[0] - glisse.x) / glisse.w * terrain.rect.w
            self._viser(joueur, terrain, x)

    @staticmethod
    def _viser(joueur, terrain, x):
        if joueur.actif("inversion"):
            x = 2 * terrain.rect.centerx - x
        joueur.raquette.viser_souris(max(terrain.rect.left, min(terrain.rect.right, x)))


def dessiner_partie(app, mode, image, monde, dessiner_monde, joueur=None):
    """
    But : dessiner une partie au format vertical.
    Entrées : app ; mode (ModeDeJeu) ; image (Surface verticale) ; monde (Surface
              paysage de travail) ; dessiner_monde (fonction(Surface)) : dessine le
              terrain, les effets et les textes ; joueur : celui qui joue ici.
    """
    joueur = joueur or mode.joueur_au_doigt() or mode.joueurs[0]
    terrain = joueur.terrain or mode.terrains[0]
    source, cible = zone_monde(terrain), zone_ecran(terrain)
    app.fond.dessiner(image)
    # Le terrain est transparent : on lui met dessous le fond vertical.
    if source.size == cible.size:
        monde.blit(image, source.topleft, cible)
    else:
        monde.blit(pygame.transform.smoothscale(image.subsurface(cible), source.size), source)
    config.orienter(config.PAYSAGE)
    try:
        dessiner_monde(monde)
    finally:
        config.orienter(config.VERTICAL)
    if source.size == cible.size:
        image.blit(monde, cible.topleft, source)
    else:                                  # terrain plus large que l'écran (Coop)
        image.blit(pygame.transform.smoothscale(monde.subsurface(source), cible.size), cible)
    dessiner_bandeau(image, mode, joueur)
    dessiner_commandes(image, app, mode, joueur, terrain)


def dessiner_bandeau(image, mode, joueur):
    """But : bandeau du haut : score, record, multiplicateur, info du mode, vies, jauge."""
    r = bandeau_rect()
    hud.panneau(image, r, joueur.couleur_bord)
    gauche = r.x + r.w // 5 + 8
    titre_g, valeur_g, sous_g = mode.score_vertical(joueur)
    hud.etiquette(image, titre_g, gauche, r.y + 24)
    dessiner_texte(image, valeur_g, gauche, r.y + 58, 4, config.AMBRE)
    if sous_g:
        hud.etiquette(image, sous_g, gauche, r.y + 94)
    hud.dessiner_multiplicateur(image, r.centerx - 6, r.y + 56, joueur, mode.temps, 5)
    titre, sous_titre, couleur = mode.infos_vertical(joueur)
    droite = r.right - r.w // 5 - 8
    dessiner_texte(image, titre, droite, r.y + 34, 4 if len(titre) <= 8 else 3, couleur)
    if sous_titre:
        hud.etiquette(image, sous_titre, droite, r.y + 70, config.BLANC)
    vies = getattr(mode, "vies", None)
    if vies is not None:
        hud.dessiner_vies(image, droite, r.y + 100, vies)
    hud.dessiner_overdrive(image, pygame.Rect(r.x + 24, r.bottom - 38, r.w - 48, 12), joueur,
                           mode.temps)


def dessiner_commandes(image, app, mode, joueur, terrain):
    """But : pouvoirs (gauche), zone de glisse (milieu), SUPERNOVA (droite), pause."""
    zones = disposition(terrain)
    if joueur.avec_pouvoirs:
        for i, case in enumerate(zones["pouvoirs"]):
            plein = i < len(joueur.inventaire)
            bouton(image, app, case, f"pouvoir{i + 1}", OR_POUVOIR, actif=plein)
            if plein:
                code = joueur.inventaire[i]
                if not dessiner_icone(image, code, case.center, OR_POUVOIR, 5):
                    dessiner_texte(image, CATALOGUE[code].lettre, case.centerx, case.centery, 4,
                                   config.BLANC, lueur=False)
            else:
                dessiner_texte(image, str(i + 1), case.centerx, case.centery, 3, (90, 60, 120),
                               lueur=False, ombre=False)
    if joueur.avec_overdrive:
        r = zones["supernova"]
        pret = joueur.overdrive_pret()
        bouton(image, app, r, "overdrive", config.ROSE, actif=pret)
        couleur = config.BLANC if pret else (90, 60, 120)
        for k, ligne in enumerate(("SUPER", "NOVA")):
            dessiner_texte(image, ligne, r.centerx, r.centery - 16 + 32 * k, 2, couleur, lueur=False)
        if not pret:                         # remplissage de la jauge
            hauteur = int((r.h - 12) * max(0.0, min(1.0, joueur.overdrive)))
            image.fill((90, 20, 70), (r.x + 6, r.bottom - 6 - hauteur, r.w - 12, hauteur),
                       special_flags=pygame.BLEND_RGB_ADD)
    glisse = zones["glisse"]
    pygame.draw.rect(image, (14, 2, 32), glisse, border_radius=18)
    pygame.draw.rect(image, (150, 30, 120), glisse, 2, border_radius=18)
    for k in range(-2, 3):
        x = glisse.centerx + k * 26
        pygame.draw.line(image, (150, 30, 120), (x, glisse.centery - 16), (x, glisse.centery + 16), 3)
    dessiner_texte(image, "<  GLISSE ICI  >", glisse.centerx, glisse.centery + 50, 2,
                   (200, 60, 170), lueur=False)
    from ecrans.tactile import bouton_pause
    cible = zone_ecran(terrain)
    bouton_pause(image, app, (cible.right - 58, cible.y + 58))
