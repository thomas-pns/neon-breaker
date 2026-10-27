# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Numéro de version du jeu et adresse du serveur en ligne.
    L'adresse n'est pas écrite dans le code (le dépôt est public) : elle
    vient, dans l'ordre, de la variable d'environnement NEON_SERVEUR, du
    fichier data/serveur.txt (créé par GitHub Actions lors de la
    fabrication de l'exécutable), puis des réglages du joueur.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026

ToDo List:
    Canal « bêta » pour tester une version avant les amis.
"""

import os

from moteur import config

# Changer VERSION et l'envoyer sur main fabrique et publie les exécutables.
VERSION = "2.6.1"
PROTOCOLE = 1          # à augmenter quand les messages réseau changent


def comparer_versions(a, b):
    """
    But : comparer deux versions "X.Y.Z".
    Entrées : a, b (str). Sortie : (int) -1 si a < b, 0 si égales, 1 si a > b.
    """
    def morceaux(version):
        resultat = []
        for partie in version.strip().lstrip("v").split("."):
            try:
                resultat.append(int(partie))
            except ValueError:
                resultat.append(0)
        return resultat + [0] * (3 - len(resultat))
    pa, pb = morceaux(a), morceaux(b)
    return (pa > pb) - (pa < pb)


def adresse_serveur(reglages=None):
    """
    But : adresse du serveur en ligne (ex. https://neon.exemple.synology.me).
    Entrée : reglages (dict ou None) : réglages du joueur.
    Sortie : (str) adresse sans « / » final, ou "" si aucune n'est connue.
    """
    adresse = os.environ.get("NEON_SERVEUR", "")
    if not adresse and reglages and reglages.get("serveur"):
        adresse = reglages["serveur"]
    if not adresse:
        chemin = os.path.join(config.DOSSIER_RESSOURCES, "serveur.txt")
        try:
            with open(chemin, encoding="utf-8") as fichier:
                adresse = fichier.read().strip()
        except OSError:
            adresse = ""
    return adresse.rstrip("/")
