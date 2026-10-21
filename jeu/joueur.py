# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Un Joueur regroupe tout ce qui lui est propre : profil de commandes,
    couleurs, score, combo et multiplicateur, inventaire de pouvoirs,
    jauge OVERDRIVE, effets actifs (bonus/malus temporisés) et statistiques.
    Le même code sert au solo et aux modes à deux joueurs.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Profils sauvegardés (nom, couleur préférée).
"""

from moteur import config


def multiplicateur_pour(combo):
    """
    But : multiplicateur de score correspondant à un combo.
    Entrée : combo (int) : briques détruites depuis le dernier contact raquette.
    Sortie : (int) 1, 2, 3, 5 ou 8.
    """
    for seuil, multiplicateur in config.PALIERS_COMBO:
        if combo >= seuil:
            return multiplicateur
    return 1


def nouvelles_stats():
    """
    But : statistiques d'une partie, envoyées au serveur pour les succès.
    Entrée : aucune. Sortie : (dict).
    """
    return {"briques": 0, "meilleur_combo": 0, "capsules": 0,
            "capsules_types": set(), "pouvoirs_utilises": set(),
            "supernovas": 0, "bombe_max": 0, "vies_perdues": 0,
            "malus_niveau": 0, "niveau_5_malus": False,
            "boss_vaincus": [], "niveaux_finis": 0}


def stats_serialisables(stats):
    """
    But : copie des statistiques convertible en JSON (ensembles -> listes).
    Entrée : stats (dict). Sortie : (dict).
    """
    return {cle: sorted(valeur) if isinstance(valeur, set) else valeur
            for cle, valeur in stats.items()}


class Joueur:
    """
    Attributs :
        numero (int) : 1 ou 2 ; profil (str) : "solo", "j1" ou "j2".
        nom (str) ; couleur_corps, couleur_bord (tuple).
        raquette (Raquette ou None) ; terrain (Terrain ou None).
        score, combo, multiplicateur (int).
        inventaire (list de codes), selection (int) : emplacement choisi (2J).
        overdrive (float 0..1) ; supernova (float) : temps restant.
        effets (dict code -> secondes restantes).
        bombe_armee (bool) ; aimant_prises (int) ; filets (int).
        stats (dict) : briques, meilleur_combo, capsules.
        avec_overdrive, avec_pouvoirs (bool) : désactivés en Hardcore.
    """

    def __init__(self, numero=1, profil="solo", nom="J1"):
        self.numero = numero
        self.profil = profil
        self.nom = nom
        self.couleur_corps, self.couleur_bord = config.COULEURS_JOUEURS[numero]
        self.raquette = None
        self.terrain = None
        self.score = 0
        self.combo = 0
        self.multiplicateur = 1
        self.inventaire = []
        self.selection = 0
        self.overdrive = 0.0
        self.supernova = 0.0
        self.effets = {}
        self.bombe_armee = False
        self.aimant_prises = 0
        self.filets = 0
        self.stats = nouvelles_stats()
        self.avec_overdrive = True
        self.avec_pouvoirs = True
        self.points_manche = 0          # Duel : points ; Course : manches

    # --- Effets temporisés --------------------------------------------------

    def actif(self, code):
        """
        But : savoir si un effet temporisé est en cours.
        Entrée : code (str). Sortie : (bool).
        """
        return self.effets.get(code, 0) > 0

    def ajouter_effet(self, code, duree):
        """
        But : lancer (ou relancer) un effet temporisé. Les effets opposés
        s'annulent (élargir / rétrécir, ralenti / turbo).
        Entrées : code (str), duree (float s). Sortie : aucune.
        """
        opposes = {"elargir": "retrecir", "retrecir": "elargir",
                   "ralenti": "vitesse", "vitesse": "ralenti"}
        contraire = opposes.get(code)
        if contraire and self.actif(contraire):
            del self.effets[contraire]
            return
        self.effets[code] = max(self.effets.get(code, 0), duree)

    def mettre_a_jour(self, dt):
        """
        But : faire s'écouler les effets et la SUPERNOVA.
        Entrée : dt (float). Sortie : (list) codes des effets qui viennent de finir.
        """
        finis = []
        for code in list(self.effets):
            self.effets[code] -= dt
            if self.effets[code] <= 0:
                del self.effets[code]
                finis.append(code)
        if self.supernova > 0:
            self.supernova = max(0.0, self.supernova - dt)
        return finis

    def facteur_vitesse_balles(self):
        """
        But : multiplicateur de vitesse des balles de ce joueur.
        Entrée : aucune. Sortie : (float).
        """
        facteur = 1.0
        if self.actif("ralenti"):
            facteur *= 0.65
        if self.actif("vitesse"):
            facteur *= 1.4
        if self.supernova > 0:
            facteur *= 1.25
        return facteur

    def facteur_largeur(self):
        """But : multiplicateur de largeur de raquette. Sortie : (float)."""
        if self.actif("elargir"):
            return 1.5
        if self.actif("retrecir"):
            return 0.6
        return 1.0

    # --- Score et combo -----------------------------------------------------

    def marquer_brique(self, points):
        """
        But : compter une brique détruite : combo, multiplicateur, score,
        remplissage de la jauge OVERDRIVE.
        Entrée : points (int) : valeur de base de la brique.
        Sortie : (tuple) (points gagnés, True si le multiplicateur a monté).
        """
        self.combo += 1
        self.stats["briques"] += 1
        self.stats["meilleur_combo"] = max(self.stats["meilleur_combo"], self.combo)
        ancien = self.multiplicateur
        self.multiplicateur = multiplicateur_pour(self.combo)
        gain = points * self.multiplicateur
        self.score += gain
        self.ajouter_overdrive(config.OVERDRIVE_PAR_BRIQUE * (1 + self.multiplicateur) / 2)
        return gain, self.multiplicateur > ancien

    def casser_combo(self):
        """But : remettre le combo à zéro (la balle a touché la raquette)."""
        self.combo = 0
        self.multiplicateur = 1

    def ajouter_overdrive(self, quantite):
        """
        But : remplir la jauge (pas pendant une SUPERNOVA).
        Entrée : quantite (float). Sortie : aucune.
        """
        if self.avec_overdrive and self.supernova <= 0:
            self.overdrive = min(1.0, self.overdrive + quantite)

    def overdrive_pret(self):
        """But : la jauge est-elle pleine ? Sortie : (bool)."""
        return self.avec_overdrive and self.overdrive >= 1.0 and self.supernova <= 0

    # --- Inventaire ---------------------------------------------------------

    def ajouter_pouvoir(self, code):
        """
        But : ranger un pouvoir dans l'inventaire.
        Entrée : code (str). Sortie : (bool) False si l'inventaire est plein.
        """
        if len(self.inventaire) >= config.TAILLE_INVENTAIRE:
            return False
        self.inventaire.append(code)
        return True

    def retirer_pouvoir(self, indice):
        """
        But : sortir un pouvoir de l'inventaire.
        Entrée : indice (int). Sortie : (str ou None) code du pouvoir.
        """
        if 0 <= indice < len(self.inventaire):
            code = self.inventaire.pop(indice)
            if self.selection >= len(self.inventaire):
                self.selection = max(0, len(self.inventaire) - 1)
            return code
        return None

    def changer_selection(self):
        """But : passer à l'emplacement suivant (modes 2 joueurs)."""
        if self.inventaire:
            self.selection = (self.selection + 1) % len(self.inventaire)

    def reinitialiser_manche(self):
        """But : remettre à zéro ce qui ne survit pas à une vie perdue."""
        self.casser_combo()
        self.effets.clear()
        self.supernova = 0.0
        self.bombe_armee = False
        self.aimant_prises = 0
