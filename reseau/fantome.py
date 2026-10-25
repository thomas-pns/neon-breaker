# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Fantôme du record (2.0), partagé par le jeu et le serveur : pendant un
    défi, on enregistre 10 fois par seconde la position de la raquette (0 à
    255 sur la largeur du terrain) et, chaque seconde, le score. Le meilleur
    joueur du jour devient le fantôme que les autres voient en transparence,
    avec l'écart de score à temps égal.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 25/10/2026
"""

import base64

PAS = 0.1                       # une position toutes les 0,1 s
DUREE_MAX = 30 * 60             # 30 minutes au plus
TAILLE_MAX = 60000              # caractères (sécurité côté serveur)


class Enregistreur:
    """Enregistre une partie. Attributs : positions (bytearray), scores (list), temps (float)."""

    def __init__(self):
        self.positions = bytearray()
        self.scores = []
        self.temps = 0.0

    def avancer(self, dt, x_relatif, score):
        """
        But : faire avancer le temps et noter position et score quand il le faut.
        Entrées : dt (s) ; x_relatif (0..1 sur la largeur du terrain) ; score (int).
        """
        if self.temps >= DUREE_MAX:
            return
        self.temps += dt
        while len(self.positions) * PAS <= self.temps + 1e-6:
            self.positions.append(max(0, min(255, int(round(x_relatif * 255)))))
        while len(self.scores) <= int(self.temps + 1e-6):
            self.scores.append(int(score))

    def exporter(self):
        """But : données compactes à envoyer (dict JSON)."""
        return {"v": 1, "x": base64.b64encode(bytes(self.positions)).decode("ascii"),
                "s": list(self.scores)}


class Fantome:
    """Lecture d'un fantôme. Attributs : nom (str), score (int), positions, scores."""

    def __init__(self, donnees, nom="", score=0):
        self.nom = nom
        self.score = score
        self.positions = base64.b64decode(donnees.get("x", ""))
        self.scores = [int(s) for s in donnees.get("s", [])]

    def x_a(self, temps):
        """But : position relative (0..1) au temps donné, ou None après la fin."""
        if not self.positions:
            return None
        indice = temps / PAS
        i = int(indice)
        if i >= len(self.positions) - 1:
            return None
        t = indice - i
        return (self.positions[i] * (1 - t) + self.positions[i + 1] * t) / 255

    def score_a(self, temps):
        """But : score du fantôme au temps donné (son score final après la fin)."""
        if not self.scores:
            return self.score
        return self.scores[min(len(self.scores) - 1, int(temps))]


def valide(donnees):
    """But : vérifier qu'un fantôme reçu est bien formé et pas trop gros. Sortie : (bool)."""
    try:
        if not isinstance(donnees, dict) or len(donnees.get("x", "")) > TAILLE_MAX:
            return False
        if len(donnees.get("s", [])) > DUREE_MAX + 2:
            return False
        base64.b64decode(donnees["x"], validate=True)
        return all(isinstance(s, int) for s in donnees["s"])
    except (KeyError, ValueError, TypeError):
        return False
