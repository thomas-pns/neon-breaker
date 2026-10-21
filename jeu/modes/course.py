# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Mode Course : deux terrains côte à côte avec le même niveau. Le premier
    qui vide son terrain gagne la manche (2 manches gagnantes). Chaque
    combo de 5 envoie une attaque à l'adversaire (malus, rangée de briques
    en plus ou brique de métal), annoncée par une flèche qui traverse
    l'écran. Perdre sa balle coûte 3 secondes de pénalité (vies infinies).

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Choix des niveaux de la course, handicap réglable.
"""

import math
import random

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from jeu.brique import BriqueMetal
from jeu.capsule import CATALOGUE
from jeu.joueur import Joueur
from jeu.modes.base import ModeDeJeu
from jeu.niveau import charger_campagne, construire_grille, generer_rangee
from jeu.pouvoirs import appliquer_capsule
from jeu.terrain import Terrain, boites_se_touchent
from ecrans import hud

RECTS = (pygame.Rect(20, 100, 600, 616), pygame.Rect(660, 100, 600, 616))
BANDEAUX = (pygame.Rect(20, 8, 600, 80), pygame.Rect(660, 8, 600, 80))
MANCHES_VICTOIRE = 2
PENALITE = 3.0
COMBO_ATTAQUE = 5


class ModeCourse(ModeDeJeu):
    """
    Attributs : manche (int), niveaux (list), attente (dict joueur -> s
    avant la remise en jeu), fleches (list d'attaques en vol).
    """

    code = "course"
    titre = "COURSE"
    deux_joueurs = True
    classement = False

    def __init__(self, app, effets):
        super().__init__(app, effets)
        self.joueurs = [Joueur(1, "j1", "J1"), Joueur(2, "j2", "J2")]
        self.niveaux = [n for n in charger_campagne() if not n.boss]
        self.manche = 0
        self.attente = {}
        self.fleches = []
        self.gagnant_manche = None
        self.app.fond.changer_monde(3)
        self.charger_manche()

    def charger_manche(self):
        """But : deux terrains neufs avec le même niveau."""
        niveau = self.niveaux[self.manche % len(self.niveaux)]
        self.niveau = niveau
        self.terrains = []
        for joueur, rect in zip(self.joueurs, RECTS):
            terrain = Terrain(rect)
            terrain.ajouter_raquette(joueur, -1)
            terrain.couleur_bord = joueur.couleur_bord
            terrain.remplir(niveau.construire(terrain))
            terrain.vitesse_balle = config.BALLE_VITESSE_DEPART * niveau.vitesse
            joueur.reinitialiser_manche()
            joueur.filets = 0
            terrain.nouvelle_balle_collee(joueur.raquette)
            self.terrains.append(terrain)
        self.attente = {}
        self.fleches = []
        self.etat = "compte"
        self.minuteur = 3.0
        self.annoncer(f"MANCHE {self.manche + 1}", config.AMBRE, 1.2)

    # --- Règles -------------------------------------------------------------------

    def regles(self, dt, dt_jeu):
        if self.etat == "compte":
            ancien = math.ceil(self.minuteur)
            self.minuteur -= dt
            if math.ceil(self.minuteur) != ancien and self.minuteur > 0:
                self.audio("menu_nav")
            if self.minuteur <= 0:
                self.etat = "jeu"
                self.annoncer("GO !", config.AMBRE, 0.8)
                self.audio("menu_ok")
        elif self.etat == "jeu":
            for joueur in list(self.attente):
                self.attente[joueur] -= dt_jeu
                if self.attente[joueur] <= 0:
                    del self.attente[joueur]
                    joueur.terrain.nouvelle_balle_collee(joueur.raquette)
        elif self.etat == "manche":
            self.minuteur -= dt
            if self.minuteur <= 0:
                if self.gagnant_manche.points_manche >= MANCHES_VICTOIRE:
                    self.terminer()
                else:
                    self.manche += 1
                    self.app.lancer_transition(self.charger_manche)
                    self.etat = "transition"
        for fleche in self.fleches:
            fleche["t"] += dt / 0.6
        self.fleches = [f for f in self.fleches if f["t"] < 1]

    def sur_plus_de_balle(self, terrain):
        if self.etat != "jeu":
            return
        joueur = terrain.joueurs()[0]
        joueur.reinitialiser_manche()
        joueur.raquette.gelee = PENALITE
        self.attente[joueur] = PENALITE
        self.effets.texte(f"PENALITE {PENALITE:.0f} S", terrain.rect.centerx,
                          terrain.rect.centery, config.ROUGE, 3, duree=1.4, vitesse=-20)
        self.effets.secouer(6)
        self.audio("vie_perdue", 0.7)

    def apres_brique(self, terrain, joueur):
        if self.etat == "jeu" and joueur.combo > 0 and joueur.combo % COMBO_ATTAQUE == 0:
            self.attaquer(joueur, self.adversaire(joueur))

    def attaquer(self, attaquant, cible):
        """
        But : envoyer une attaque à l'adversaire : malus, rangée de briques
        ou brique de métal.
        Entrées : attaquant, cible (Joueur). Sortie : aucune.
        """
        terrain = cible.terrain
        nature = random.choice(["malus", "malus", "rangee", "metal"])
        texte = ""
        if nature == "rangee" and self._ajouter_rangee(terrain):
            texte = "+1 RANGEE"
        elif nature == "metal" and self._ajouter_metal(terrain):
            texte = "METAL"
        else:
            malus = [c for c, e in CATALOGUE.items() if e.categorie == "malus"]
            code = random.choice(malus)
            appliquer_capsule(code, cible, terrain)
            texte = CATALOGUE[code].nom
        depart = attaquant.terrain.rect.centerx
        self.fleches.append({"x0": depart, "x1": terrain.rect.centerx, "t": 0.0,
                             "couleur": attaquant.couleur_bord, "texte": texte})
        self.effets.texte(f"ATTAQUE : {texte}", terrain.rect.centerx, terrain.rect.top + 40,
                          config.ROUGE, 2, duree=1.6, vitesse=10)
        self.effets.texte(f"COMBO {COMBO_ATTAQUE} : ATTAQUE !", attaquant.raquette.x,
                          attaquant.raquette.y - 60, attaquant.couleur_bord, 2)
        self.app.crt.declencher_aberration(0.6)
        self.audio("combo")

    def _ajouter_rangee(self, terrain):
        """Pousse les briques d'un cran et ajoute une rangée en haut."""
        _, pas_y = terrain.pas_grille()
        limite = terrain.raquettes[0].y - 140
        if any(b.y + b.hauteur + pas_y > limite for b in terrain.briques):
            return False
        terrain.decaler_briques(pas_y)
        nouvelles = list(construire_grille([generer_rangee(1.5)], terrain))
        for brique in nouvelles:
            terrain.briques.ajouter_fin(brique)
        terrain.preparer_briques(nouvelles, cascade=False)
        for brique in nouvelles:
            brique.apparition = 0.0
        return True

    def _ajouter_metal(self, terrain):
        """Pose une brique de métal dans une case libre du haut du terrain."""
        pas_x, pas_y = terrain.pas_grille()
        x0 = terrain.rect.left + 22
        y0 = terrain.rect.top + config.BRIQUE_MARGE_HAUT
        cases = [(x0 + c * pas_x, y0 + l * pas_y) for c in range(12) for l in range(6)]
        random.shuffle(cases)
        for x, y in cases:
            boite = (x, y, x + terrain.brique_l, y + terrain.brique_h)
            occupee = any(boites_se_touchent(boite, b.obtenir_boite()) for b in terrain.briques)
            proche_balle = any(abs(b.x - x) < 60 and abs(b.y - y) < 60 for b in terrain.balles)
            if not occupee and not proche_balle:
                metal = BriqueMetal(x, y, terrain.brique_l, terrain.brique_h)
                terrain.briques.ajouter_fin(metal)
                return True
        return False

    def sur_niveau_vide(self, terrain):
        if self.etat != "jeu":
            return
        gagnant = terrain.joueurs()[0]
        gagnant.points_manche += 1
        self.gagnant_manche = gagnant
        self.etat = "manche"
        self.minuteur = 3.0
        self.effets.ralentir(0.25, 1.2)
        self.effets.eclair(0.7, gagnant.couleur_bord)
        self.app.crt.declencher_aberration(1.0)
        self.annoncer(f"{self.nom_joueur(gagnant)} GAGNE LA MANCHE !", gagnant.couleur_bord, 3.0)
        self.audio("victoire")
        for t in self.terrains:
            t.balles.vider()

    def terminer(self):
        j1, j2 = self.joueurs
        gagnant = self.gagnant_manche
        self.etat = "fin"
        self.resultat = {
            "victoire": True, "score": gagnant.score, "mode": self.code,
            "titre": f"{self.nom_joueur(gagnant)} GAGNE !", "couleur": gagnant.couleur_bord,
            "lignes": [("MANCHES", f"{j1.points_manche} - {j2.points_manche}"),
                       ("SCORE J1 / J2", f"{j1.score} / {j2.score}"),
                       ("COMBO J1 / J2", f"{j1.stats['meilleur_combo']} / "
                                         f"{j2.stats['meilleur_combo']}")],
            "rapports": self.rapports(gagnant=gagnant.numero,
                                      points=[j1.points_manche, j2.points_manche]),
        }

    # --- Dessin -------------------------------------------------------------------

    def dessiner(self, image):
        # Bande sombre entre les deux terrains (sinon le soleil du fond s'y voit).
        entre = pygame.Rect(RECTS[0].right + 4, RECTS[0].top - 4,
                            RECTS[1].left - RECTS[0].right - 8, RECTS[0].h + 8)
        image.fill((6, 0, 16), entre)
        super().dessiner(image)

    def dessiner_hud(self, image):
        for joueur, bandeau, terrain in zip(self.joueurs, BANDEAUX, self.terrains):
            manches = "*" * joueur.points_manche + "-" * (MANCHES_VICTOIRE - joueur.points_manche)
            joueur.etiquette = self.nom_joueur(joueur)
            hud.bloc_joueur_horizontal(image, bandeau, joueur, self.temps,
                                       gauche_texte=f"BRIQUES {terrain.briques_restantes()}",
                                       droite_texte=manches)
            if joueur in self.attente:
                dessiner_texte(image, f"{self.attente[joueur]:.1f}", terrain.rect.centerx,
                               terrain.rect.centery + 60, 6, config.ROUGE)

    def dessiner_overlay(self, image):
        for fleche in self.fleches:
            t = fleche["t"]
            x = fleche["x0"] + (fleche["x1"] - fleche["x0"]) * (1 - (1 - t) ** 2)
            sens = 1 if fleche["x1"] > fleche["x0"] else -1
            y = config.HAUTEUR / 2
            for k in range(3):
                cx = x - sens * k * 22
                pygame.draw.lines(image, fleche["couleur"], False,
                                  [(cx - sens * 14, y - 18), (cx, y), (cx - sens * 14, y + 18)], 5)
            dessiner_texte(image, fleche["texte"], x, y - 40, 2, fleche["couleur"])
        if self.etat == "compte":
            chiffre = max(1, math.ceil(self.minuteur))
            echelle = 14 + int((self.minuteur % 1) * 6)
            dessiner_texte(image, str(chiffre), config.LARGEUR / 2, config.HAUTEUR / 2 + 40,
                           echelle, config.AMBRE)
