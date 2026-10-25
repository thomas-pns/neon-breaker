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

import pygame

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
        self.preparer_fantome()

    # --- Fantôme du record (2.0) ---------------------------------------------------------

    def preparer_fantome(self):
        """
        But : charger le fantôme à battre : le meilleur joueur du jour (en ligne),
        sinon ton propre record de ce défi ; et commencer à enregistrer ta partie.
        """
        from reseau.fantome import Enregistreur, Fantome
        self.enregistreur = Enregistreur()
        self.fantome = None
        local = self.app.donnees.get("fantomes", {}).get(self.code)
        if local and local.get("jour") == self.jour:
            try:
                self.fantome = Fantome(local["donnees"], "TON RECORD", local.get("score", 0))
            except (KeyError, ValueError):
                self.fantome = None
        en_ligne = getattr(self.app, "en_ligne", None)
        if en_ligne is not None and getattr(en_ligne, "jeton", "") and not self.en_ligne:
            en_ligne.appeler("GET", f"/api/fantome/{self.code}/{self.jour}",
                             rappel=self._recu_fantome, authentifie=False)

    def _recu_fantome(self, resultat):
        from reseau.fantome import Fantome, valide
        donnees = resultat.get("donnees") if resultat.get("ok") else None
        if not donnees or not valide(donnees.get("fantome")):
            return
        if self.fantome is not None and self.fantome.score >= donnees.get("score", 0):
            return                       # ton record local est meilleur
        moi = getattr(self.app.en_ligne, "pseudo", "")
        nom = "TON RECORD" if donnees.get("pseudo", "").lower() == moi.lower() \
            else donnees.get("pseudo", "?").upper()
        self.fantome = Fantome(donnees["fantome"], nom, donnees.get("score", 0))

    def regles(self, dt, dt_jeu):
        super().regles(dt, dt_jeu)
        if self.etat in ("jeu", "pret") and getattr(self, "enregistreur", None) is not None:
            terrain = self.terrains[0]
            raquette = terrain.raquettes[0]
            relatif = (raquette.x - terrain.rect.x) / max(1, terrain.rect.w)
            self.enregistreur.avancer(dt, relatif, self.joueurs[0].score)

    def dessiner_overlay(self, image):
        super().dessiner_overlay(image)
        fantome = getattr(self, "fantome", None)
        reglage = self.app.reglages.get("fantome", "ecart")
        if fantome is None or self.etat == "fin" or reglage == "non":
            return
        terrain = self.terrains[0]
        temps = self.enregistreur.temps
        relatif = fantome.x_a(temps)
        raquette = terrain.raquettes[0]
        if relatif is not None and reglage == "raquette":    # raquette visible seulement sur demande
            rect = pygame.Rect(0, 0, int(raquette.largeur), int(raquette.hauteur))
            rect.midtop = (int(terrain.rect.x + relatif * terrain.rect.w), int(raquette.y))
            voile = pygame.Surface(rect.size, pygame.SRCALPHA)
            voile.fill((200, 220, 255, 60))
            image.blit(voile, rect)
            pygame.draw.rect(image, (200, 220, 255), rect, 1, border_radius=6)
        ecart = self.joueurs[0].score - fantome.score_a(temps)
        couleur = config.VERT if ecart >= 0 else config.ROSE
        dessiner_texte(image, f"RECORD {fantome.nom[:10]}   {'+' if ecart >= 0 else ''}{ecart}",
                       terrain.rect.centerx, terrain.rect.y + 18, 2, couleur, lueur=False)

    def _garder_fantome(self):
        """But : envoyer ta partie comme fantôme, et la garder si c'est ton record du défi."""
        enregistreur = getattr(self, "enregistreur", None)
        if enregistreur is None or not enregistreur.positions:
            return None
        donnees = enregistreur.exporter()
        fantomes = self.app.donnees.setdefault("fantomes", {})
        local = fantomes.get(self.code)
        score = self.joueurs[0].score
        if not local or local.get("jour") != self.jour or score > local.get("score", 0):
            fantomes[self.code] = {"jour": self.jour, "score": score, "donnees": donnees}
        return donnees

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
        fantome = self._garder_fantome()
        if fantome is not None:
            self.resultat["rapports"][0]["fantome"] = fantome
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
