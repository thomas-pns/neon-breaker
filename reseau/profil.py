# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Règles de profil partagées par le jeu et le serveur : couleurs
    disponibles, calcul du niveau à partir de l'XP, skins de raquette et
    conditions pour les débloquer.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import math

COULEURS = ["cyan", "rose", "ambre", "violet", "vert", "bleu"]


def niveau_pour(xp):
    """But : niveau de joueur correspondant à une XP totale. Sortie : (int)."""
    return 1 + int(math.sqrt(max(0, xp) / 150))


def xp_pour_niveau(niveau):
    """But : XP minimale d'un niveau (pour la barre de progression)."""
    return int(150 * (niveau - 1) ** 2)


# --- Skins de raquette ---------------------------------------------------------------------
# condition : None (toujours), ("niveau", n) ou ("succes", code). Couleurs en RVB.
# motif : uni, rayures, grille, damier, pulse, spectre, coeur ; trainee : images fantômes.
SKINS = [
    {"code": "neon", "nom": "NEON", "condition": None,
     "corps": None, "bord": None, "motif": "uni", "trainee": False},
    {"code": "sunset", "nom": "SUNSET", "condition": ("niveau", 3),
     "corps": (255, 140, 60), "bord": (255, 60, 150), "motif": "rayures", "trainee": False},
    {"code": "cryo", "nom": "CRYO", "condition": ("niveau", 5),
     "corps": (150, 230, 255), "bord": (230, 250, 255), "motif": "grille", "trainee": False},
    {"code": "vapor", "nom": "VAPORWAVE", "condition": ("niveau", 8),
     "corps": (255, 110, 220), "bord": (60, 240, 255), "motif": "damier", "trainee": True},
    {"code": "spectre", "nom": "SPECTRE", "condition": ("niveau", 12),
     "corps": None, "bord": None, "motif": "spectre", "trainee": True},
    {"code": "toxique", "nom": "TOXIQUE", "condition": ("succes", "combo_8"),
     "corps": (90, 255, 90), "bord": (200, 255, 60), "motif": "pulse", "trainee": False},
    {"code": "noyau", "nom": "NOYAU", "condition": ("succes", "boss_core"),
     "corps": (170, 80, 255), "bord": (255, 255, 255), "motif": "coeur", "trainee": False},
    {"code": "drone", "nom": "DRONE", "condition": ("succes", "arcade_drone"),
     "corps": (255, 60, 140), "bord": (40, 20, 70), "motif": "grille", "trainee": True},
    {"code": "or", "nom": "LEGENDE", "condition": ("succes", "campagne"),
     "corps": (255, 210, 60), "bord": (255, 250, 200), "motif": "pulse", "trainee": True},
]
SKINS_PAR_CODE = {s["code"]: s for s in SKINS}


def skins_debloques(niveau, succes):
    """
    But : codes des skins accessibles.
    Entrées : niveau (int) ; succes (ensemble de codes de succès obtenus).
    Sortie : (list de str) dans l'ordre du catalogue.
    """
    resultat = []
    for skin in SKINS:
        condition = skin["condition"]
        if condition is None or (condition[0] == "niveau" and niveau >= condition[1]) \
                or (condition[0] == "succes" and condition[1] in succes):
            resultat.append(skin["code"])
    return resultat


def condition_lisible(skin):
    """But : texte « NIVEAU 5 » ou « SUCCES ... » pour un skin verrouillé."""
    condition = skin["condition"]
    if condition is None:
        return ""
    if condition[0] == "niveau":
        return f"NIVEAU {condition[1]}"
    return "SUCCES " + {"combo_8": "x8", "boss_core": "COEUR BRISE",
                        "arcade_drone": "CHASSEUR DRONES",
                        "campagne": "LEGENDE NEON"}.get(condition[1], condition[1].upper())
