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
# Version navigateur (pygbag, Python compilé en WebAssembly) : pas de fils
# d'exécution, sauvegarde dans le navigateur, sons livrés en .ogg.
EST_WEB = sys.platform == "emscripten"
RACINE = getattr(sys, "_MEIPASS",
                 os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOSSIER_RESSOURCES = os.path.join(RACINE, "data")


def _lire_canal():
    """
    But : canal de la version : "dev" pour un exe de test (fichier data/canal.txt
    écrit par outils/construire.py, ou variable NEON_CANAL), sinon "stable".
    Sortie : (str).
    """
    if os.environ.get("NEON_CANAL"):
        return os.environ["NEON_CANAL"].strip().lower()
    try:
        with open(os.path.join(DOSSIER_RESSOURCES, "canal.txt"), encoding="utf-8") as fichier:
            return fichier.read().strip().lower() or "stable"
    except OSError:
        return "stable"


CANAL = _lire_canal()
# Version de test : sauvegarde séparée, aucun score envoyé au vrai serveur,
# pas de partie en ligne sur le vrai serveur, pas de mise à jour automatique.
EST_TEST = CANAL == "dev"


def _dossier_utilisateur():
    """
    But : dossier où écrire les données du joueur.
    Entrée : aucune. Sortie : (str) chemin (créé si besoin).
    """
    if os.environ.get("NEON_DONNEES"):
        dossier = os.environ["NEON_DONNEES"]
    elif EST_WEB:
        dossier = os.path.expanduser("~/neonbreaker")   # en mémoire : voir moteur/web.py
    elif not EST_EXECUTABLE:
        dossier = DOSSIER_RESSOURCES            # lancé depuis le code source
    elif sys.platform == "win32":
        dossier = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")),
                               "NeonBreaker-dev" if EST_TEST else "NeonBreaker")
    elif sys.platform == "darwin":
        dossier = os.path.expanduser("~/Library/Application Support/"
                                     + ("NeonBreaker-dev" if EST_TEST else "NeonBreaker"))
    else:
        dossier = os.path.expanduser("~/.local/share/neonbreaker" + ("-dev" if EST_TEST else ""))
    os.makedirs(dossier, exist_ok=True)
    return dossier


DOSSIER_DATA = _dossier_utilisateur()
DOSSIER_SONS = os.path.join(DOSSIER_DATA, "sons")
DOSSIER_NIVEAUX = os.path.join(DOSSIER_RESSOURCES, "niveaux")
DOSSIER_SONS_WEB = os.path.join(DOSSIER_RESSOURCES, "sons_web")   # .ogg de la version web
CHEMIN_FOND = os.path.join(DOSSIER_RESSOURCES, "fond.png")

# --- Affichage -----------------------------------------------------------
TITRE = "NEON BREAKER"
# Format de l'image interne. Paysage partout, sauf sur téléphone : vertical (9:16).
# LARGEUR et HAUTEUR donnent le format EN COURS : un écran pas encore prévu pour le
# vertical est dessiné en paysage (voir Application), et ils valent alors 1280x720.
PAYSAGE = (1280, 720)
VERTICAL = (640, 1138)          # 640 de large : tout est 25 % plus gros qu'à 800 (2.5)
LARGEUR, HAUTEUR = PAYSAGE
# Zones sûres du téléphone (encoche en haut, barre d'accueil en bas), en pixels de
# l'image verticale : rien d'important ne doit être dessiné dessous.
MARGE_HAUT_ECRAN, MARGE_BAS_ECRAN = 0, 0
# Vrai quand la page les a mesurées (navigateur du téléphone) : elles valent alors
# peut-être 0 (barre d'état hors du jeu), et on ne devine plus de marge en haut.
MARGES_CONNUES = False


def orienter(taille):
    """But : changer le format en cours (PAYSAGE ou VERTICAL)."""
    global LARGEUR, HAUTEUR
    LARGEUR, HAUTEUR = taille


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
        "onglet": [S.KSCAN_TAB],          # menus 2.1 : onglet suivant (Maj + Tab : précédent)
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

# Manettes (2.0) : boutons standard (disposition Xbox, la PlayStation suit la même place).
# Les profils "solo", "j1" et "j2" utilisent "jeu" ; J1 = première manette, J2 = deuxième.
MANETTE = {
    "menu": {"haut": ["haut", "stick_haut"], "bas": ["bas", "stick_bas"],
             "gauche": ["gauche", "stick_gauche"], "droite": ["droite", "stick_droite"],
             "valider": ["a", "start"], "retour": ["b", "back"], "pause": ["start"],
             "onglet": ["rb"], "onglet_precedent": ["lb"]},
    "jeu": {"gauche": ["gauche", "stick_gauche"], "droite": ["droite", "stick_droite"],
            "action": ["a"], "changer": ["x", "lb"], "activer": ["y", "rb"],
            "overdrive": ["b", "rt", "lt"]},
}
AIDE_MANETTE = [("STICK", "BOUGER"), ("A", "LANCER"), ("X LB", "CHOISIR"), ("Y RB", "POUVOIR"),
                ("B RT", "OVERDRIVE"), ("START", "PAUSE")]

# Commandes qu'on peut changer dans OPTIONS > COMMANDES, avec leur nom par défaut (AZERTY).
COMMANDES = {
    "solo": [("gauche", "GAUCHE", "\u2190 Q"), ("droite", "DROITE", "\u2192 D"),
             ("action", "LANCER", "ESPACE"), ("changer", "CHOISIR", "A TAB"),
             ("activer", "POUVOIR", "E"), ("overdrive", "OVERDRIVE", "MAJ"),
             ("pouvoir1", "POUVOIR 1", "1"), ("pouvoir2", "POUVOIR 2", "2"),
             ("pouvoir3", "POUVOIR 3", "3")],
    "j1": [("gauche", "GAUCHE", "Q"), ("droite", "DROITE", "D"), ("action", "LANCER", "Z"),
           ("changer", "CHOISIR", "A"), ("activer", "POUVOIR", "E"), ("overdrive", "OVERDRIVE", "S")],
    "j2": [("gauche", "GAUCHE", "\u2190"), ("droite", "DROITE", "\u2192"),
           ("action", "LANCER", "\u2191"), ("changer", "CHOISIR", "CTRL D"),
           ("activer", "POUVOIR", "MAJ D"), ("overdrive", "OVERDRIVE", "\u2193")],
}

# Libellés affichés (clavier AZERTY).
AIDE_TOUCHES = {
    "solo": [("\u2190 \u2192 Q D", "BOUGER"), ("SOURIS", "BOUGER"),
             ("ESPACE", "LANCER"), ("1 2 3", "POUVOIRS"),
             ("A TAB", "CHOISIR"), ("E", "POUVOIR"),
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
