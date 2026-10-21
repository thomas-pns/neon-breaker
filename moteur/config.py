# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Regrouper toutes les constantes du jeu : résolution, couleurs néon,
    dimensions du terrain, vitesses, touches. Modifier ici pour équilibrer.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Commandes configurables.
"""

import os
import sys

import pygame

# --- Chemins -------------------------------------------------------------
# Deux sortes de fichiers :
#   - les RESSOURCES livrées avec le jeu (niveaux, fond.png), en lecture seule.
#     Dans l'exécutable PyInstaller, elles sont décompressées dans sys._MEIPASS ;
#   - les DONNÉES du joueur (sauvegarde, sons générés, journal), qui doivent
#     survivre aux mises à jour : dossier utilisateur du système.
EST_EXECUTABLE = getattr(sys, "frozen", False)
RACINE = getattr(sys, "_MEIPASS",
                 os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOSSIER_RESSOURCES = os.path.join(RACINE, "data")


def _dossier_utilisateur():
    """
    But : dossier où écrire les données du joueur.
    Entrée : aucune. Sortie : (str) chemin (créé si besoin).
    """
    if os.environ.get("NEON_DONNEES"):
        dossier = os.environ["NEON_DONNEES"]
    elif not EST_EXECUTABLE:
        dossier = DOSSIER_RESSOURCES            # lancé depuis le code source
    elif sys.platform == "win32":
        dossier = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")),
                               "NeonBreaker")
    elif sys.platform == "darwin":
        dossier = os.path.expanduser("~/Library/Application Support/NeonBreaker")
    else:
        dossier = os.path.expanduser("~/.local/share/neonbreaker")
    os.makedirs(dossier, exist_ok=True)
    return dossier


DOSSIER_DATA = _dossier_utilisateur()
DOSSIER_SONS = os.path.join(DOSSIER_DATA, "sons")
DOSSIER_NIVEAUX = os.path.join(DOSSIER_RESSOURCES, "niveaux")
CHEMIN_FOND = os.path.join(DOSSIER_RESSOURCES, "fond.png")

# --- Affichage -----------------------------------------------------------
TITRE = "NEON BREAKER"
LARGEUR = 1280
HAUTEUR = 720
FPS = 60
PAS_PHYSIQUE = 1 / 120          # physique à pas fixe : 120 Hz
PAS_MAX_PAR_IMAGE = 8           # garde-fou si le PC rame

# --- Palette synthwave (reprise du projet d'origine) ----------------------
AMBRE = (255, 176, 0)
ROSE = (255, 43, 214)
VIOLET = (192, 60, 255)
BLEU = (77, 107, 255)
CYAN = (0, 229, 255)
COULEURS_NEON = [AMBRE, ROSE, VIOLET, BLEU, CYAN]
INTERIEUR = (18, 0, 43)
RAQUETTE_CORPS = (45, 226, 230)
RAQUETTE_BORD = (255, 106, 213)
BLANC = (255, 255, 255)
NOIR = (0, 0, 0)
ROUGE = (255, 50, 80)
VERT = (60, 255, 140)
OR = (255, 215, 90)
GRIS_METAL = (150, 160, 190)
CIEL_HAUT = (10, 2, 30)
CIEL_MILIEU = (60, 14, 110)
CIEL_HORIZON = (255, 43, 160)

# --- Terrain solo (centré, panneaux HUD à gauche et à droite) ------------
TERRAIN_X = 260
TERRAIN_Y = 24
TERRAIN_L = 760
TERRAIN_H = HAUTEUR - TERRAIN_Y
EPAISSEUR_BORD = 3

# --- Briques -------------------------------------------------------------
BRIQUE_L = 56
BRIQUE_H = 22
BRIQUE_ESPACE = 4
BRIQUE_MARGE_HAUT = 70
NB_COLONNES = 12

# --- Raquette ------------------------------------------------------------
RAQUETTE_L = 120
RAQUETTE_H = 16
RAQUETTE_MARGE_BAS = 46
RAQUETTE_VITESSE_MAX = 980      # px/s
RAQUETTE_ACCEL = 9000           # px/s²
RAQUETTE_FREIN = 12000          # px/s² quand on lâche les touches

# --- Balle ---------------------------------------------------------------
BALLE_RAYON = 8
BALLE_VITESSE_DEPART = 580      # px/s
BALLE_VITESSE_MAX = 980
BALLE_ACCEL_PAR_COUP = 7        # gain de vitesse à chaque brique
ANGLE_NORMALE_MAX = 30          # degrés (repris de partie.py)
ANGLE_MAX_VERTICALE = 70        # degrés (repris de partie.py)

# --- Règles --------------------------------------------------------------
VIES_DEPART = 3
VIE_BONUS_TOUS_LES = 20000          # une vie offerte tous les 20 000 points
PALIERS_COMBO = [(35, 8), (20, 5), (10, 3), (5, 2), (0, 1)]

# --- Capsules, pouvoirs, OVERDRIVE ----------------------------------------
CHANCE_CAPSULE = 0.12               # probabilité qu'une brique lâche une capsule
VITESSE_CAPSULE = 170               # px/s
POIDS_CATEGORIES = {"bonus": 55, "malus": 25, "pouvoir": 20}
TAILLE_INVENTAIRE = 3
OVERDRIVE_PAR_BRIQUE = 0.008        # x (1 + multiplicateur) / 2
OVERDRIVE_PAR_CAPSULE = 0.03
DUREE_SUPERNOVA = 6.0
BALLES_MAX = 12

# --- Touches : codes PHYSIQUES (scancodes) ---------------------------------
# Un scancode désigne l'emplacement de la touche, pas sa lettre : KSCAN_A
# est la touche « Q » d'un clavier AZERTY et « A » d'un QWERTY. Les jeux à
# deux joueurs marchent donc pareil quelle que soit la disposition.
S = pygame
TOUCHES = {
    "menu": {
        "haut": [S.KSCAN_UP, S.KSCAN_W],
        "bas": [S.KSCAN_DOWN, S.KSCAN_S],
        "gauche": [S.KSCAN_LEFT, S.KSCAN_A],
        "droite": [S.KSCAN_RIGHT, S.KSCAN_D],
        "valider": [S.KSCAN_RETURN, S.KSCAN_KP_ENTER, S.KSCAN_SPACE],
        "retour": [S.KSCAN_ESCAPE, S.KSCAN_BACKSPACE],
        "pause": [S.KSCAN_ESCAPE, S.KSCAN_P],
    },
    "solo": {
        "gauche": [S.KSCAN_LEFT, S.KSCAN_A],
        "droite": [S.KSCAN_RIGHT, S.KSCAN_D],
        "action": [S.KSCAN_SPACE, S.KSCAN_UP, S.KSCAN_W],
        "pouvoir1": [S.KSCAN_1, S.KSCAN_KP_1],
        "pouvoir2": [S.KSCAN_2, S.KSCAN_KP_2],
        "pouvoir3": [S.KSCAN_3, S.KSCAN_KP_3],
        "changer": [S.KSCAN_Q, S.KSCAN_TAB],
        "activer": [S.KSCAN_E, S.KSCAN_LCTRL],
        "overdrive": [S.KSCAN_LSHIFT, S.KSCAN_RSHIFT, S.KSCAN_S, S.KSCAN_DOWN],
    },
    "j1": {
        "gauche": [S.KSCAN_A],
        "droite": [S.KSCAN_D],
        "action": [S.KSCAN_W],
        "changer": [S.KSCAN_Q],
        "activer": [S.KSCAN_E],
        "overdrive": [S.KSCAN_S],
    },
    "j2": {
        "gauche": [S.KSCAN_LEFT],
        "droite": [S.KSCAN_RIGHT],
        "action": [S.KSCAN_UP],
        "changer": [S.KSCAN_RCTRL, S.KSCAN_KP_PERIOD],
        "activer": [S.KSCAN_RSHIFT, S.KSCAN_KP_0],
        "overdrive": [S.KSCAN_DOWN],
    },
}

# Libellés affichés (clavier AZERTY).
AIDE_TOUCHES = {
    "solo": [("\u2190 \u2192 Q D", "BOUGER"), ("SOURIS", "BOUGER"),
             ("ESPACE", "LANCER"), ("1 2 3", "POUVOIRS"),
             ("MAJ", "OVERDRIVE"), ("ECHAP", "PAUSE")],
    "j1": [("Q D", "BOUGER"), ("Z", "LANCER"), ("A", "CHOISIR"),
           ("E", "POUVOIR"), ("S", "OVERDRIVE")],
    "j2": [("\u2190 \u2192", "BOUGER"), ("\u2191", "LANCER"),
           ("CTRL D", "CHOISIR"), ("MAJ D", "POUVOIR"),
           ("\u2193", "OVERDRIVE")],
}

# Couleurs des joueurs (corps, bord).
COULEURS_JOUEURS = {1: ((45, 226, 230), (255, 106, 213)),
                    2: ((255, 120, 200), (255, 176, 0))}
