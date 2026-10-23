# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Package tests de NEON BREAKER, avec un utilitaire commun de dossier
    temporaire.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 23/10/2026
"""

import os
import tempfile
import uuid


def dossier_temporaire(prefixe="neon_test_"):
    """
    But : créer un dossier temporaire utilisable aussi dans le sandbox des agents.
          Sous Windows, depuis Python 3.13, tempfile.mkdtemp pose une ACL réservée
          à l'utilisateur que le jeton restreint du sandbox ne peut pas utiliser :
          on crée donc le dossier avec os.makedirs, sans mode, dans le dossier
          temporaire courant (TEMP, redirigé par outils/verifier.py).
    Entrée : prefixe (str). Sortie : (str) chemin du dossier créé.
    """
    if os.name != "nt":
        return tempfile.mkdtemp(prefix=prefixe)
    chemin = os.path.join(tempfile.gettempdir(), prefixe + uuid.uuid4().hex[:12])
    os.makedirs(chemin)
    return chemin
