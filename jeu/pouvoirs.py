# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Appliquer les effets des capsules (bonus, malus), activer les pouvoirs
    de l'inventaire et déclencher la SUPERNOVA (jauge OVERDRIVE pleine).
    Ces fonctions agissent sur un joueur et son terrain ; c'est le mode de
    jeu qui choisit la cible (en Duel, les malus vont à l'adversaire).

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Combinaisons de pouvoirs (laser + feu = laser perçant).
"""

from moteur import config
from jeu.capsule import CATALOGUE

POINTS_INVENTAIRE_PLEIN = 500


def appliquer_capsule(code, joueur, terrain):
    """
    But : appliquer l'effet d'une capsule attrapée.
    Entrées : code (str) ; joueur (Joueur) : qui en profite (ou qui subit
              le malus) ; terrain (Terrain) : terrain de ce joueur.
    Sortie : (str) résultat : "ok", "vie" (le mode ajoute la vie),
             "stocke", "plein" (pouvoir converti en points).
    """
    effet = CATALOGUE[code]
    joueur.stats["capsules"] += 1
    joueur.stats["capsules_types"].add(code)
    if effet.categorie == "malus":
        joueur.stats["malus_niveau"] += 1
    joueur.ajouter_overdrive(config.OVERDRIVE_PAR_CAPSULE)
    if effet.categorie == "pouvoir":
        if not joueur.avec_pouvoirs:
            return "ok"
        if joueur.ajouter_pouvoir(code):
            return "stocke"
        joueur.score += POINTS_INVENTAIRE_PLEIN
        return "plein"
    if code == "vie":
        return "vie"
    if code == "multi":
        terrain.ajouter_balles_multi()
    elif code == "aimant":
        joueur.aimant_prises = 5
    elif code == "filet":
        joueur.filets = min(2, joueur.filets + 1)
    else:
        joueur.ajouter_effet(code, effet.duree)
    return "ok"


def activer_pouvoir(code, joueur, terrain):
    """
    But : déclencher un pouvoir sorti de l'inventaire.
    Entrées : code (str) ; joueur (Joueur) ; terrain (Terrain).
    Sortie : aucune.
    """
    effet = CATALOGUE[code]
    if code == "onde":
        onde_de_choc(joueur, terrain)
    elif code == "bombe":
        joueur.bombe_armee = True
    elif code == "chrono":
        terrain.chrono = effet.duree
        joueur.ajouter_effet("chrono", effet.duree)
    else:                                  # laser, bouclier, guidage
        joueur.ajouter_effet(code, effet.duree)


def onde_de_choc(joueur, terrain):
    """
    But : endommager toutes les briques des 3 lignes les plus proches de
    la raquette du joueur.
    Entrées : joueur (Joueur) ; terrain (Terrain). Sortie : aucune.
    """
    raquette = joueur.raquette
    solides = [b for b in terrain.briques if b.solide]
    if raquette is None or not solides:
        return
    lignes = sorted({round(b.y) for b in solides},
                    key=lambda y: abs(y - raquette.y))[:3]
    for brique in solides:
        if round(brique.y) in lignes:
            terrain.endommager(brique, joueur)
    terrain.evenements.enfiler(("onde", raquette.x, raquette.y))


def declencher_supernova(joueur):
    """
    But : vider la jauge OVERDRIVE et lancer la SUPERNOVA.
    Entrée : joueur (Joueur). Sortie : (bool) True si déclenchée.
    """
    if not joueur.overdrive_pret():
        return False
    joueur.overdrive = 0.0
    joueur.supernova = config.DUREE_SUPERNOVA
    return True
