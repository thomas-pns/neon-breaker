# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Lire et écrire data/sauvegarde.json (meilleurs scores, réglages,
    progression). Écriture atomique : on écrit un fichier temporaire puis
    on le renomme, pour ne jamais corrompre la sauvegarde. Si le fichier
    est illisible, on repart des valeurs par défaut sans planter.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Top 10 par mode avec noms (jalon 3).
"""

import copy
import json
import os

from moteur import config

CHEMIN = os.path.join(config.DOSSIER_DATA, "sauvegarde.json")

DEFAUT = {
    "version": 1,
    "reglages": {"crt": True, "tremblement": True, "particules": "haut",
                 "volume_effets": 0.7, "volume_musique": 0.5},
    "meilleurs": {},          # mode -> meilleur score
    "classements": {},        # mode -> top 10 [{"nom", "score"}]
    "progression": {},        # "campagne" / "coop" -> dernier niveau débloqué
}


def fusionner(defaut, lu):
    """
    But : compléter les données lues avec les clés par défaut manquantes
    (utile quand une nouvelle version ajoute des réglages).
    Entrées : defaut (dict), lu (dict). Sortie : (dict) fusion.
    """
    resultat = copy.deepcopy(defaut)
    for cle, valeur in lu.items():
        if isinstance(valeur, dict) and isinstance(resultat.get(cle), dict):
            resultat[cle] = fusionner(resultat[cle], valeur)
        else:
            resultat[cle] = valeur
    return resultat


def charger(chemin=CHEMIN):
    """
    But : lire la sauvegarde.
    Entrée : chemin (str). Sortie : (dict) données (défaut si absent/corrompu).
    """
    try:
        with open(chemin, encoding="utf-8") as fichier:
            lu = json.load(fichier)
        if not isinstance(lu, dict):
            raise ValueError("format inattendu")
        return fusionner(DEFAUT, lu)
    except (OSError, ValueError):
        return copy.deepcopy(DEFAUT)


def enregistrer(donnees, chemin=CHEMIN):
    """
    But : écrire la sauvegarde de façon atomique.
    Entrées : donnees (dict), chemin (str). Sortie : (bool) succès.
    """
    temporaire = chemin + ".tmp"
    try:
        os.makedirs(os.path.dirname(chemin), exist_ok=True)
        with open(temporaire, "w", encoding="utf-8") as fichier:
            json.dump(donnees, fichier, indent=2, ensure_ascii=False)
        os.replace(temporaire, chemin)
        return True
    except OSError:
        return False
