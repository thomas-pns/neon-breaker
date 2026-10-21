# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Réglages du serveur NEON BREAKER, lus dans les variables
    d'environnement (fichier .env de Container Manager).

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import os

DOSSIER_DONNEES = os.environ.get("NEON_DONNEES_SERVEUR", "/data")
CHEMIN_BASE = os.path.join(DOSSIER_DONNEES, "neon.sqlite3")
DOSSIER_BUILDS = os.path.join(DOSSIER_DONNEES, "builds")
PORT = int(os.environ.get("NEON_PORT", "8765"))

# Jeton secret utilisé par GitHub Actions pour envoyer les exécutables.
JETON_DEPLOIEMENT = os.environ.get("NEON_JETON_DEPLOIEMENT", "")

MAX_PARTIES = int(os.environ.get("NEON_MAX_PARTIES", "4"))
JOUEURS_PAR_PARTIE = 2
DUREE_SESSION_JOURS = 90
ATTENTE_RECONNEXION = 30.0          # secondes avant d'abandonner une partie
FREQUENCE_INSTANTANES = 30          # envois d'état par seconde

# Limite anti-spam : tentatives de connexion / inscription par adresse IP.
TENTATIVES_PAR_MINUTE = 10

PSEUDO_MIN, PSEUDO_MAX = 3, 12
MDP_MIN = 6
from reseau.profil import COULEURS  # noqa: E402,F401
