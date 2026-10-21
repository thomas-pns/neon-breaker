# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Charger les niveaux de la campagne depuis data/niveaux/ et générer des
    niveaux procéduraux (rangées de l'Arcade, mur central du Duel).

    Format d'un fichier niveau (.txt) :
        nom: SUNSET GRID 1-1
        monde: 1                (thème graphique 1, 2 ou 3)
        vitesse: 1.0            (multiplicateur de la vitesse de balle)
        boss: sunset            (facultatif : sunset, gridlock ou core)
        ---
        ..aaaaaaaa..            (12 caractères par ligne, voir
        .rrrrrrrrrr.             jeu/brique.py : fabriquer_brique)

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Éditeur de niveaux intégré.
"""

import os
import random

from structures.liste import Liste
from moteur import config
from jeu.brique import fabriquer_brique


class ErreurNiveau(Exception):
    """Fichier de niveau mal formé."""


class Niveau:
    """
    Attributs :
        nom (str), monde (int), vitesse (float), boss (str ou None),
        grille (list de str), chemin (str).
    """

    def __init__(self, nom, vitesse, grille, chemin="", monde=1, boss=None):
        self.nom = nom
        self.vitesse = vitesse
        self.grille = grille
        self.chemin = chemin
        self.monde = monde
        self.boss = boss

    def construire(self, terrain, y0=None):
        """
        But : créer les briques du niveau, centrées dans le terrain, à la
        taille des briques de ce terrain.
        Entrées : terrain (Terrain) ; y0 (float ou None) : haut de la grille.
        Sortie : (Liste) briques.
        """
        return construire_grille(self.grille, terrain, y0)


def construire_grille(grille, terrain, y0=None):
    """
    But : transformer une grille de caractères en briques.
    Entrées : grille (list de str) ; terrain (Terrain) ; y0 (float ou None).
    Sortie : (Liste) briques.
    """
    briques = Liste()
    pas_x, pas_y = terrain.pas_grille()
    largeur_grille = config.NB_COLONNES * pas_x - config.BRIQUE_ESPACE
    x0 = terrain.rect.left + (terrain.rect.w - largeur_grille) / 2
    if y0 is None:
        y0 = terrain.rect.top + config.BRIQUE_MARGE_HAUT
    for ligne, rangee in enumerate(grille):
        for colonne, caractere in enumerate(rangee[:config.NB_COLONNES]):
            brique = fabriquer_brique(caractere, x0 + colonne * pas_x,
                                      y0 + ligne * pas_y, terrain.brique_l,
                                      terrain.brique_h)
            if brique is not None:
                briques.ajouter_fin(brique)
    return briques


def lire_niveau(texte, chemin=""):
    """
    But : analyser le contenu d'un fichier niveau.
    Entrées : texte (str) : contenu ; chemin (str) : pour les messages.
    Sortie : (Niveau).
    Lève ErreurNiveau si le séparateur « --- » manque ou si la grille est vide.
    """
    lignes = texte.splitlines()
    propres = [l.strip() for l in lignes]
    if "---" not in propres:
        raise ErreurNiveau(f"{chemin} : séparateur '---' manquant")
    separation = propres.index("---")
    entete = {}
    for ligne in lignes[:separation]:
        if ":" in ligne:
            cle, valeur = ligne.split(":", 1)
            entete[cle.strip().lower()] = valeur.strip()
    grille = [l.rstrip("\n") for l in lignes[separation + 1:] if l.strip()]
    if not grille:
        raise ErreurNiveau(f"{chemin} : grille vide")
    try:
        vitesse = float(entete.get("vitesse", "1.0"))
        monde = int(entete.get("monde", "1"))
    except ValueError as erreur:
        raise ErreurNiveau(f"{chemin} : vitesse ou monde invalide") from erreur
    nom = entete.get("nom", os.path.splitext(os.path.basename(chemin))[0])
    boss = entete.get("boss") or None
    return Niveau(nom, vitesse, grille, chemin, monde, boss)


def charger_campagne(dossier=config.DOSSIER_NIVEAUX):
    """
    But : charger tous les niveaux du dossier, triés par nom de fichier.
    Entrée : dossier (str).
    Sortie : (list de Niveau). Les fichiers invalides sont ignorés.
    """
    niveaux = []
    if not os.path.isdir(dossier):
        return niveaux
    for nom_fichier in sorted(os.listdir(dossier)):
        if not nom_fichier.endswith(".txt"):
            continue
        chemin = os.path.join(dossier, nom_fichier)
        try:
            with open(chemin, encoding="utf-8") as fichier:
                niveaux.append(lire_niveau(fichier.read(), chemin))
        except (OSError, ErreurNiveau) as erreur:
            print("Niveau ignoré :", erreur)
    return niveaux


# --- Générateurs procéduraux ------------------------------------------------

def generer_rangee(difficulte, aleatoire=random):
    """
    But : générer une rangée de 12 briques pour l'Arcade. Plus la
    difficulté monte, plus il y a de briques solides et spéciales.
    Entrées : difficulte (float, 0 au départ, +1 par minute environ) ;
              aleatoire (module ou Random).
    Sortie : (str) 12 caractères au format des niveaux.
    """
    couleur = aleatoire.choice("arvbc")
    motif = aleatoire.choice(["plein", "trous", "alterne", "centre"])
    rangee = []
    for colonne in range(config.NB_COLONNES):
        if motif == "trous" and aleatoire.random() < 0.25:
            rangee.append(".")
            continue
        if motif == "alterne" and colonne % 2:
            rangee.append(".")
            continue
        if motif == "centre" and colonne in (0, 1, 10, 11):
            rangee.append(".")
            continue
        tirage = aleatoire.random()
        speciale = min(0.35, 0.06 + difficulte * 0.04)
        solide = min(0.5, 0.1 + difficulte * 0.08)
        if tirage < speciale:
            rangee.append(aleatoire.choice("X?X?<MH*"))
        elif tirage < speciale + solide:
            rangee.append(aleatoire.choice([couleur.upper(), "3", "4"]
                                           if difficulte > 2 else [couleur.upper()]))
        else:
            rangee.append(couleur)
    return "".join(rangee)


def generer_mur_duel(aleatoire=random):
    """
    But : mur de briques symétrique (haut/bas et gauche/droite) pour le Duel.
    Entrée : aleatoire (module ou Random).
    Sortie : (list de str) 6 lignes de 12 caractères.
    """
    moitie = []
    for ligne in range(3):
        gauche = []
        for colonne in range(6):
            tirage = aleatoire.random()
            if tirage < 0.12:
                gauche.append(".")
            elif tirage < 0.2:
                gauche.append(aleatoire.choice("X?M"))
            elif tirage < 0.4:
                gauche.append("VRB"[ligne])
            else:
                gauche.append("vrb"[ligne])
        moitie.append("".join(gauche) + "".join(reversed(gauche)))
    return moitie + list(reversed(moitie))
