# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Défi du jour : une partie d'Arcade dont les rangées de briques et la
    règle spéciale (le « modificateur ») sont tirées à partir de la date.
    Tous les joueurs ont donc exactement le même mur le même jour, et le
    serveur tient un classement du jour. Nouveau défi à minuit.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import datetime
import hashlib
import random

from moteur import config
from moteur.police_pixel import dessiner_texte
from jeu.modes.arcade import ModeArcade, PANNEAU_D
from ecrans import hud

# (code, nom affiché, description courte)
MODIFICATEURS = [
    ("classique", "CLASSIQUE", "SANS SURPRISE"),
    ("rapide", "BALLE RAPIDE", "BALLE +25 %"),
    ("capsules", "PLUIE DE CAPSULES", "CAPSULES x2,5"),
    ("presse", "MUR PRESSE", "DESCENTES x1,4"),
    ("une_vie", "UNE SEULE VIE", "1 VIE, SCORE x2"),
    ("geant", "MUR GEANT", "10 RANGEES"),
]


def jour_du_defi(maintenant=None):
    """But : date du défi (heure locale du joueur), au format AAAA-MM-JJ."""
    return (maintenant or datetime.datetime.now()).strftime("%Y-%m-%d")


def defi_pour(jour):
    """
    But : graine et modificateur du défi d'un jour donné.
    Entrée : jour (str AAAA-MM-JJ). Sortie : (int graine, tuple modificateur).
    """
    graine = int(hashlib.sha256(f"neon-breaker-defi-{jour}".encode()).hexdigest()[:12], 16)
    modificateur = MODIFICATEURS[random.Random(graine).randrange(len(MODIFICATEURS))]
    return graine, modificateur


def record_du_jour(app, jour):
    """But : meilleur score local du défi de ce jour (0 si pas encore joué)."""
    defi = app.donnees.get("defi", {})
    return defi.get("record", 0) if defi.get("jour") == jour else 0


class ModeDefi(ModeArcade):
    """Arcade à graine fixe. Attributs : jour (str), modificateur (tuple)."""

    code = "defi"
    titre = "DEFI DU JOUR"
    classement = False             # pas de top 10 local : le classement est en ligne

    def __init__(self, app, effets, jour=None):
        self.jour = jour or jour_du_defi()
        graine, self.modificateur = defi_pour(self.jour)
        self.rangees_depart = 10 if self.modificateur[0] == "geant" else None
        super().__init__(app, effets, graine)
        code = self.modificateur[0]
        terrain = self.terrains[0]
        if code == "rapide":
            terrain.vitesse_balle = config.BALLE_VITESSE_DEPART * 1.25
        elif code == "capsules":
            terrain.chance_capsule = min(0.6, config.CHANCE_CAPSULE * 2.5)
        elif code == "presse":
            self.intervalle *= 0.7
            self.avant_descente = self.intervalle
        elif code == "une_vie":
            self.vies = 1
            self.multiplicateur_score = 2
            self.prochaine_vie = float("inf")
        self.servir()
        jour_affiche = "/".join(reversed(self.jour.split("-")[1:]))
        self.annoncer(f"DEFI DU {jour_affiche} : {self.modificateur[1]}", config.AMBRE, 2.6)

    def terminer(self):
        super().terminer()
        joueur = self.joueurs[0]
        self.resultat["titre"] = "DEFI TERMINE"
        self.resultat["rapports"] = self.rapports(victoire=False, vagues=self.vague, jour=self.jour,
                                                  modificateur=self.modificateur[0])
        ancien = record_du_jour(self.app, self.jour)
        if joueur.score > ancien:
            self.app.donnees["defi"] = {"jour": self.jour, "record": joueur.score}
            self.app.enregistrer()
            self.resultat["lignes"].insert(0, ("RECORD DU JOUR", "NOUVEAU !"))
        else:
            self.resultat["lignes"].insert(0, ("RECORD DU JOUR", str(ancien)))

    def record_affiche(self):
        return record_du_jour(self.app, self.jour)

    def dessiner_hud(self, image):
        super().dessiner_hud(image)
        cx = PANNEAU_D.centerx
        hud.etiquette(image, "DEFI DU JOUR", cx, 340, config.AMBRE)
        dessiner_texte(image, "/".join(reversed(self.jour.split("-")[1:])), cx, 370, 3,
                       config.AMBRE)
        dessiner_texte(image, self.modificateur[1], cx, 406, 2, config.BLANC, lueur=False)
        dessiner_texte(image, self.modificateur[2], cx, 430, 2, (170, 140, 220), lueur=False)
