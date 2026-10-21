# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Sécurité des comptes : hachage des mots de passe (scrypt, bibliothèque
    standard), jetons de session aléatoires (seule leur empreinte est
    stockée en base), validation des pseudos et limite de tentatives par
    adresse IP contre le spam.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import hashlib
import hmac
import re
import secrets
import time
from collections import defaultdict, deque

from serveur import config

PARAMETRES_SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1, "dklen": 32}
MOTIF_PSEUDO = re.compile(r"^[A-Za-z0-9_\-]+$")


def hacher_mdp(mdp, sel=None):
    """
    But : empreinte scrypt d'un mot de passe.
    Entrées : mdp (str) ; sel (bytes ou None : en tirer un nouveau).
    Sortie : (str) "sel_hex$empreinte_hex".
    """
    sel = sel or secrets.token_bytes(16)
    empreinte = hashlib.scrypt(mdp.encode("utf-8"), salt=sel, maxmem=64 * 1024 * 1024,
                               **PARAMETRES_SCRYPT)
    return sel.hex() + "$" + empreinte.hex()


def verifier_mdp(mdp, stocke):
    """
    But : vérifier un mot de passe contre son empreinte (comparaison à temps
    constant).
    Entrées : mdp (str) ; stocke (str) : "sel$empreinte". Sortie : (bool).
    """
    try:
        sel_hex, _ = stocke.split("$", 1)
        attendu = hacher_mdp(mdp, bytes.fromhex(sel_hex))
    except ValueError:
        return False
    return hmac.compare_digest(attendu, stocke)


def nouveau_jeton():
    """But : jeton de session aléatoire. Sortie : (str) 43 caractères."""
    return secrets.token_urlsafe(32)


def empreinte_jeton(jeton):
    """But : empreinte SHA-256 d'un jeton (ce qui est stocké en base)."""
    return hashlib.sha256(jeton.encode("utf-8")).hexdigest()


def erreur_pseudo(pseudo):
    """
    But : vérifier un pseudo. Sortie : (str ou None) message d'erreur.
    """
    if not (config.PSEUDO_MIN <= len(pseudo) <= config.PSEUDO_MAX):
        return f"Le pseudo doit faire {config.PSEUDO_MIN} à {config.PSEUDO_MAX} caractères."
    if not MOTIF_PSEUDO.match(pseudo):
        return "Pseudo : lettres, chiffres, - et _ seulement."
    return None


def erreur_mdp(mdp):
    """But : vérifier un mot de passe. Sortie : (str ou None) message d'erreur."""
    if len(mdp) < config.MDP_MIN:
        return f"Le mot de passe doit faire au moins {config.MDP_MIN} caractères."
    if len(mdp) > 128:
        return "Mot de passe trop long."
    return None


class Limiteur:
    """Limite le nombre d'appels par clé (adresse IP) sur une fenêtre glissante."""

    def __init__(self, maximum, fenetre=60.0):
        self.maximum = maximum
        self.fenetre = fenetre
        self.appels = defaultdict(deque)

    def autoriser(self, cle):
        """
        But : enregistrer un appel et dire s'il est permis.
        Entrée : cle (str). Sortie : (bool).
        """
        maintenant = time.monotonic()
        file = self.appels[cle]
        while file and maintenant - file[0] > self.fenetre:
            file.popleft()
        if len(file) >= self.maximum:
            return False
        file.append(maintenant)
        return True
