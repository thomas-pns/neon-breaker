# Header
# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Implémenter pile LIFO (empiler/dépiler/sommet/vide), utiliser pour undo/redo ou backtracking niveau.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI

Réalisé le 06/10/2026

ToDo List:
    Pile avec max/min en O(1), historique limité, sérialisation, pile persistante.
"""
from structures.liste import Liste

class Pile:
    """Pile (LIFO) : le dernier élément empilé est le premier dépilé."""

    def __init__(self):
        self.elements = Liste()

    def empiler(self, valeur):
        """
        But : ajouter un élément au sommet.
        Entrée : valeur (object). Sortie : aucune.
        """
        self.elements.ajouter_debut(valeur)

    def depiler(self):
        """
        But : retirer et renvoyer l'élément du sommet.
        Entrée : aucune. Sortie : (object) élément retiré.
        Lève IndexError si la pile est vide.
        """
        return self.elements.retirer_debut()

    def sommet(self):
        """
        But : consulter le sommet sans le retirer.
        Entrée : aucune. Sortie : (object) élément du sommet.
        Lève IndexError si la pile est vide.
        """
        if self.elements.est_vide():
            raise IndexError("Pile vide")
        return self.elements.tete.valeur

    def est_vide(self):
        return self.elements.est_vide()

    def __len__(self):
        return len(self.elements)

