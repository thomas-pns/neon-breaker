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


def semaine_du_defi(maintenant=None):
    """But : semaine du défi hebdomadaire (heure locale), au format AAAA-Www."""
    from reseau.series import id_semaine
    return id_semaine((maintenant or datetime.datetime.now()).date())


def defi_semaine_pour(semaine):
    """
    But : graine et DEUX modificateurs différents (jamais « classique ») du défi
    d'une semaine. Entrée : semaine (str AAAA-Www). Sortie : (int, list de tuples).
    """
    graine = int(hashlib.sha256(f"neon-breaker-semaine-{semaine}".encode()).hexdigest()[:12], 16)
    choix = [m for m in MODIFICATEURS if m[0] != "classique"]
    return graine, random.Random(graine).sample(choix, 2)


def record_du_jour(app, jour, cle="defi"):
    """But : meilleur score local du défi de ce jour / cette semaine (0 si pas joué)."""
    defi = app.donnees.get(cle, {})
    return defi.get("record", 0) if defi.get("jour") == jour else 0


def defis_joues(app, periode="jour"):
    """But : jours (ou semaines) où ce défi a été joué sur ce PC (pour les séries)."""
    return app.donnees.setdefault("defis_joues", {}).setdefault(periode, [])


def serie_locale(app, periode="jour"):
    """But : série en cours de ce PC pour le défi du jour ou de la semaine."""
    from reseau.series import en_cours
    return en_cours(defis_joues(app, periode), datetime.date.today(), semaines=periode == "semaine")


class ModeDefi(ModeArcade):
    """
    Arcade à graine fixe. Attributs : jour (str : date ou semaine), modificateurs
    (list de tuples), periode ("jour" ou "semaine").
    """

    code = "defi"
    titre = "DEFI DU JOUR"
    periode = "jour"
    classement = False             # pas de top 10 local : le classement est en ligne

    def __init__(self, app, effets, jour=None):
        graine = self.preparer(jour)
        codes = [m[0] for m in self.modificateurs]
        self.rangees_depart = (10 if "geant" in codes else self.rangees_base())
        super().__init__(app, effets, graine)
        terrain = self.terrains[0]
        if "rapide" in codes:
            terrain.vitesse_balle = config.BALLE_VITESSE_DEPART * 1.25
        if "capsules" in codes:
            terrain.chance_capsule = min(0.6, config.CHANCE_CAPSULE * 2.5)
        if "presse" in codes:
            self.intervalle *= 0.7
            self.avant_descente = self.intervalle
        if "une_vie" in codes:
            self.vies = 1
            self.multiplicateur_score = 2
            self.prochaine_vie = float("inf")
        self.servir()
        self.annoncer(self.annonce(), config.AMBRE, 2.6)

    # --- Spécifique au défi du jour (redéfini pour la semaine) ------------------------

    def preparer(self, jour):
        self.jour = jour or jour_du_defi()
        graine, modificateur = defi_pour(self.jour)
        self.modificateurs = [modificateur]
        self.modificateur = modificateur
        return graine

    def rangees_base(self):
        return None

    def annonce(self):
        return f"{self.libelle()} : {self.modificateur[1]}"

    def libelle(self):
        return "DEFI DU " + "/".join(reversed(self.jour.split("-")[1:]))

    def date_courte(self):
        return "/".join(reversed(self.jour.split("-")[1:]))

    # --- Fin de partie et affichage -------------------------------------------------------

    def terminer(self):
        super().terminer()
        joueur = self.joueurs[0]
        self.resultat["titre"] = "DEFI TERMINE"
        self.resultat["rapports"] = self.rapports(
            victoire=False, vagues=self.vague, jour=self.jour,
            modificateur="+".join(m[0] for m in self.modificateurs))
        joues = defis_joues(self.app, self.periode)
        if self.jour not in joues:
            joues.append(self.jour)
            del joues[:-400]
        cle = self.code
        ancien = record_du_jour(self.app, self.jour, cle)
        etiquette = "RECORD DU JOUR" if self.periode == "jour" else "RECORD SEMAINE"
        if joueur.score > ancien:
            self.app.donnees[cle] = {"jour": self.jour, "record": joueur.score}
            self.resultat["lignes"].insert(0, (etiquette, "NOUVEAU !"))
        else:
            self.resultat["lignes"].insert(0, (etiquette, str(ancien)))
        serie = serie_locale(self.app, self.periode)
        self.resultat["lignes"].insert(1, ("SERIE", f"{serie} {'J' if self.periode == 'jour' else 'S'}"))
        self.app.enregistrer()

    def record_affiche(self):
        return record_du_jour(self.app, self.jour, self.code)

    def dessiner_hud(self, image):
        super().dessiner_hud(image)
        cx = PANNEAU_D.centerx
        hud.etiquette(image, self.titre, cx, 330, config.AMBRE)
        dessiner_texte(image, self.date_courte(), cx, 358, 3, config.AMBRE)
        y = 392
        for modificateur in self.modificateurs:
            dessiner_texte(image, modificateur[1], cx, y, 2, config.BLANC, lueur=False)
            dessiner_texte(image, modificateur[2], cx, y + 22, 2, (170, 140, 220), lueur=False)
            y += 50


class ModeDefiSemaine(ModeDefi):
    """Défi de la semaine : mur plus haut au départ et deux règles spéciales à la fois."""

    code = "semaine"
    titre = "DEFI SEMAINE"
    periode = "semaine"

    def preparer(self, jour):
        self.jour = jour or semaine_du_defi()
        graine, self.modificateurs = defi_semaine_pour(self.jour)
        self.modificateur = self.modificateurs[0]
        return graine

    def rangees_base(self):
        return 8

    def libelle(self):
        return "SEMAINE " + self.date_courte()

    def annonce(self):
        return f"DEFI DE LA SEMAINE {self.date_courte()}"

    def date_courte(self):
        return self.jour.split("-W")[-1]
