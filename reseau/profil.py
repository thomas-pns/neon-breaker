# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Règles de profil partagées par le jeu et le serveur : couleurs
    disponibles et calcul du niveau à partir de l'XP.

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
