# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Mode Duel : J1 en bas, J2 en haut, un mur de briques symétrique au
    centre. Une balle qui sort par le camp d'un joueur donne un point à
    l'adversaire ; le perdant remet en jeu. Les capsules partent vers le
    joueur qui a cassé la brique, et les malus attrapés sont envoyés à
    l'adversaire. Le mur se reconstruit quand il est presque détruit.
    Premier à 7 points.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Variante « mort subite », obstacles mobiles.
"""

import math
import random

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from jeu.joueur import Joueur
from jeu.modes.base import ModeDeJeu
from jeu.niveau import construire_grille, generer_mur_duel
from jeu.terrain import Terrain, boites_se_touchent
from ecrans import hud

RECT_DUEL = pygame.Rect(260, 8, 760, 704)
PANNEAU_J1 = pygame.Rect(20, 24, 220, 672)
PANNEAU_J2 = pygame.Rect(1040, 24, 220, 672)
POINTS_VICTOIRE = 7
SEUIL_RECONSTRUCTION = 0.3


class ModeDuel(ModeDeJeu):
    """Attributs : mur_initial (int) : nombre de briques du mur complet."""

    code = "duel"
    titre = "DUEL"
    deux_joueurs = True
    classement = False

    def __init__(self, app, effets):
        super().__init__(app, effets)
        self.joueurs = [Joueur(1, "j1", "J1"), Joueur(2, "j2", "J2")]
        terrain = Terrain(RECT_DUEL, mur_haut=False)
        terrain.ajouter_raquette(self.joueurs[0], -1)
        terrain.ajouter_raquette(self.joueurs[1], +1)
        terrain.couleur_bord = config.VIOLET
        terrain.chance_capsule = 0.18
        self.terrains = [terrain]
        terrain.remplir(self.construire_mur())
        self.mur_initial = max(1, terrain.briques_restantes())
        self.app.fond.changer_monde(2)
        for joueur in self.joueurs:
            terrain.nouvelle_balle_collee(joueur.raquette)
        self.etat = "compte"
        self.minuteur = 3.0

    def construire_mur(self):
        """But : briques du mur central (symétrique, tiré au hasard)."""
        terrain = self.terrains[0]
        _, pas_y = terrain.pas_grille()
        grille = generer_mur_duel(random)
        y0 = terrain.rect.centery - len(grille) * pas_y / 2
        return construire_grille(grille, terrain, y0)

    # --- Règles -------------------------------------------------------------------

    def regles(self, dt, dt_jeu):
        terrain = self.terrains[0]
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
            if terrain.briques_restantes() < self.mur_initial * SEUIL_RECONSTRUCTION:
                self.reconstruire_mur()
        elif self.etat == "perdu":
            self.minuteur -= dt
            if self.minuteur <= 0:
                self.terminer()
        meneur = max(j.points_manche for j in self.joueurs)
        self.app.fond.vitesse_cible = 0.8 + meneur * 0.25

    def reconstruire_mur(self):
        """Ajoute les briques du nouveau mur là où la place est libre."""
        terrain = self.terrains[0]
        nouvelles = []
        for brique in self.construire_mur():
            boite = brique.obtenir_boite()
            libre = not any(boites_se_touchent(boite, b.obtenir_boite()) for b in terrain.briques)
            loin_des_balles = all(
                not boites_se_touchent(boite, (b.x - 20, b.y - 20, b.x + 20, b.y + 20))
                for b in terrain.balles)
            if libre and loin_des_balles:
                terrain.briques.ajouter_fin(brique)
                nouvelles.append(brique)
        terrain.preparer_briques(nouvelles, cascade=False)
        for brique in nouvelles:
            brique.apparition = 0.0
        self.annoncer("NOUVEAU MUR", config.VIOLET, 1.0)
        self.audio("combo", 0.5)

    def sur_balle_perdue(self, terrain, balle, cote):
        super().sur_balle_perdue(terrain, balle, cote)
        if self.etat != "jeu":
            return
        marqueur = self.joueurs[0] if cote == "haut" else self.joueurs[1]
        perdant = self.adversaire(marqueur)
        marqueur.points_manche += 1
        self.effets.secouer(10)
        self.effets.eclair(0.3, marqueur.couleur_bord)
        self.app.crt.declencher_aberration(0.8)
        self.audio("vie_perdue", 0.7)
        if marqueur.points_manche >= POINTS_VICTOIRE:
            self.annoncer(f"{self.nom_joueur(marqueur)} GAGNE !", marqueur.couleur_bord, 3.0)
            self.etat = "perdu"
            self.minuteur = 2.0
            self.effets.ralentir(0.3, 1.8)
            self.audio("victoire")
            return
        self.annoncer(f"POINT {self.nom_joueur(marqueur)}  {self.joueurs[0].points_manche} - "
                      f"{self.joueurs[1].points_manche}", marqueur.couleur_bord, 1.2)
        perdant.reinitialiser_manche()
        # Le perdant remet en jeu s'il n'a plus de balle à lui.
        a_une_balle = any(b.proprietaire is perdant for b in terrain.balles)
        if len(terrain.balles) < 2 or not a_une_balle:
            terrain.nouvelle_balle_collee(perdant.raquette)

    def sur_plus_de_balle(self, terrain):
        """Ne devrait pas arriver (remise en jeu immédiate), par sécurité."""
        if self.etat == "jeu":
            for joueur in self.joueurs:
                terrain.nouvelle_balle_collee(joueur.raquette)

    def sur_niveau_vide(self, terrain):
        if self.etat == "jeu":
            self.reconstruire_mur()
            terrain.niveau_annonce_vide = False

    def cible_capsule(self, effet, joueur):
        """Les malus attrapés sont envoyés à l'adversaire."""
        if effet.categorie == "malus":
            return self.adversaire(joueur)
        return joueur

    def terminer(self):
        j1, j2 = self.joueurs
        gagnant = j1 if j1.points_manche > j2.points_manche else j2
        self.etat = "fin"
        self.resultat = {
            "victoire": True, "score": gagnant.score, "mode": self.code,
            "titre": f"{self.nom_joueur(gagnant)} GAGNE !", "couleur": gagnant.couleur_bord,
            "lignes": [("SCORE", f"{j1.points_manche} - {j2.points_manche}"),
                       ("BRIQUES J1 / J2", f"{j1.stats['briques']} / {j2.stats['briques']}"),
                       ("COMBO J1 / J2", f"{j1.stats['meilleur_combo']} / "
                                         f"{j2.stats['meilleur_combo']}")],
            "rapports": self.rapports(gagnant=gagnant.numero,
                                      points=[j1.points_manche, j2.points_manche]),
        }

    # --- Dessin -------------------------------------------------------------------

    def dessiner(self, image):
        super().dessiner(image)
        self.dessiner_mediane(image)

    def dessiner_mediane(self, image):
        """But : ligne médiane en pointillés."""
        terrain = self.terrains[0]
        y = terrain.rect.centery
        for x in range(terrain.rect.left, terrain.rect.right, 24):
            image.fill((90, 40, 140), (x, y, 12, 2))

    def dessiner_hud(self, image):
        # En ligne, le joueur 2 voit le terrain retourné : il est en bas chez lui.
        retourne = getattr(self, "vue_retournee", False)
        places = ("HAUT", "BAS") if retourne else ("BAS", "HAUT")
        for joueur, rect, place, aide in ((self.joueurs[0], PANNEAU_J1, places[0], "j1"),
                                          (self.joueurs[1], PANNEAU_J2, places[1], "j2")):
            hud.panneau(image, rect, joueur.couleur_bord)
            dessiner_texte(image, f"{self.nom_joueur(joueur)}  {place}", rect.centerx, 50,
                           3 if len(self.nom_joueur(joueur)) < 7 else 2, joueur.couleur_bord)
            dessiner_texte(image, f"{joueur.points_manche}", rect.centerx - 30, 104, 8,
                           config.BLANC)
            dessiner_texte(image, f"/{POINTS_VICTOIRE}", rect.centerx + 40, 116, 3,
                           (170, 140, 220), lueur=False)
            hud.bloc_joueur_vertical(image, rect, joueur, 160, self.temps, score=False,
                                     touche_overdrive="MAJ" if self.en_ligne else (
                                         "S" if joueur.numero == 1 else "↓"))
            hud.etiquette(image, "COMMANDES", rect.centerx, 486, config.ROSE)
            hud.dessiner_commandes(image, rect, "solo" if self.en_ligne else aide, 512,
                                    self.app)

    def dessiner_overlay(self, image):
        if self.etat == "compte":
            chiffre = max(1, math.ceil(self.minuteur))
            echelle = 14 + int((self.minuteur % 1) * 6)
            dessiner_texte(image, str(chiffre), config.LARGEUR / 2, config.HAUTEUR / 2,
                           echelle, config.AMBRE)
