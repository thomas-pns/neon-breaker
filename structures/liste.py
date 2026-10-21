# Header
# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Implémenter liste chainée (ajout/suppression/recherche/parcours), itérateur, utiliser pour liste de briques/balles.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI

Réalisé le 06/10/2026

ToDo List:
    Liste doublement chainée, tri fusion, suppression doublons, liste circulaire.
"""

class Noeud:
    """
    Maillon d'une liste chaînée.
    Attributs :
        valeur : donnée stockée.
        suivant : maillon suivant (None en fin de liste).
    """

    def __init__(self, valeur, suivant=None):
        self.valeur = valeur
        self.suivant = suivant


class Liste:
    """
    Liste simplement chaînée avec pointeurs de tête et de queue.
    Attributs :
        tete, queue : premier et dernier maillons (None si vide).
        taille : nombre d'éléments.
    """

    def __init__(self):
        self.tete = None
        self.queue = None
        self.taille = 0

    def est_vide(self):
        """
        But : tester si la liste est vide.
        Entrée : aucune.
        Sortie : (bool) True si aucun élément.
        """
        return self.tete is None

    def ajouter_debut(self, valeur):
        """
        But : insérer un élément en tête (coût constant).
        Entrée : valeur (object) : élément à insérer.
        Sortie : aucune.
        """
        noeud = Noeud(valeur, self.tete)
        self.tete = noeud
        if self.queue is None:
            self.queue = noeud
        self.taille += 1

    def ajouter_fin(self, valeur):
        """
        But : insérer un élément en queue (coût constant).
        Entrée : valeur (object) : élément à insérer.
        Sortie : aucune.
        """
        noeud = Noeud(valeur)
        if self.queue is None:
            self.tete = noeud
        else:
            self.queue.suivant = noeud
        self.queue = noeud
        self.taille += 1

    def retirer_debut(self):
        """
        But : retirer et renvoyer le premier élément (coût constant).
        Entrée : aucune.
        Sortie : (object) valeur retirée.
        Lève IndexError si la liste est vide.
        """
        if self.tete is None:
            raise IndexError("Retrait impossible : structure vide")
        noeud = self.tete
        self.tete = noeud.suivant
        if self.tete is None:
            self.queue = None
        self.taille -= 1
        return noeud.valeur

    def supprimer(self, valeur):
        """
        But : supprimer la première occurrence d'un objet (comparaison par
        identité, adaptée à des objets comme les briques). Coût linéaire.
        Entrée : valeur (object) : objet à supprimer.
        Sortie : (bool) True si l'objet a été trouvé et supprimé.
        """
        precedent = None
        courant = self.tete
        while courant is not None:
            if courant.valeur is valeur:
                if precedent is None:
                    self.tete = courant.suivant
                else:
                    precedent.suivant = courant.suivant
                if courant is self.queue:
                    self.queue = precedent
                self.taille -= 1
                return True
            precedent = courant
            courant = courant.suivant
        return False

    def __iter__(self):
        """
        But : parcourir les valeurs de la tête vers la queue.
        Entrée : aucune.
        Sortie : (générateur) valeurs successives.
        """
        courant = self.tete
        while courant is not None:
            yield courant.valeur
            courant = courant.suivant

    def __len__(self):
        return self.taille

    # --- Ajouts refonte NEON BREAKER -------------------------------------

    def retirer_si(self, predicat):
        """
        But : supprimer en un seul parcours tous les éléments pour lesquels
        predicat(valeur) est vrai (utile pour les particules mortes).
        Entrée : predicat (fonction) : valeur -> bool.
        Sortie : (int) nombre d'éléments retirés.
        """
        retires = 0
        precedent = None
        courant = self.tete
        while courant is not None:
            if predicat(courant.valeur):
                if precedent is None:
                    self.tete = courant.suivant
                else:
                    precedent.suivant = courant.suivant
                if courant is self.queue:
                    self.queue = precedent
                self.taille -= 1
                retires += 1
            else:
                precedent = courant
            courant = courant.suivant
        return retires

    def vider(self):
        """
        But : retirer tous les éléments.
        Entrée : aucune. Sortie : aucune.
        """
        self.tete = None
        self.queue = None
        self.taille = 0

