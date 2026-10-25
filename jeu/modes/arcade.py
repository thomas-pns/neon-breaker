# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Mode Arcade infinie : le mur de briques descend d'un cran à intervalles
    de plus en plus courts, une nouvelle rangée (générée au hasard, de plus
    en plus riche en briques spéciales) apparaît en haut. La partie
    s'arrête quand une brique atteint la raquette ou quand les vies sont
    épuisées. Vider l'écran rapporte un gros bonus et 4 nouvelles rangées.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

    Toutes les 10 vagues, un mini-boss (DRONE) apparaît : le mur s'arrête de
    descendre tant qu'il vole ; le vaincre rapporte des points et une vie.
    Le décor (et la musique) change de monde aux vagues 15 et 30.
"""

import math
import random

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from jeu.joueur import Joueur
from jeu.modes.base import ModeDeJeu
from jeu.modes.campagne import RECT_SOLO, PANNEAU_G, PANNEAU_D
from jeu.boss import BossDrone
from jeu.niveau import construire_grille, generer_rangee
from jeu.terrain import Terrain
from ecrans import hud

INTERVALLE_DEPART = 12.0
INTERVALLE_MIN = 4.5
RANGEES_DEPART = 6
BONUS_ECRAN_VIDE = 2000


class ModeArcade(ModeDeJeu):
    """
    Attributs : vies, vague (int : nombre de descentes), intervalle (s),
    avant_descente (s), aleatoire (Random).
    """

    code = "arcade"
    titre = "ARCADE"

    def __init__(self, app, effets, graine=None):
        super().__init__(app, effets)
        self.aleatoire = random.Random(graine)
        self.souris_active = True
        self.joueurs = [Joueur(1, "solo", "J1")]
        self.vies = config.VIES_DEPART
        self.prochaine_vie = config.VIE_BONUS_TOUS_LES
        self.vague = 0
        self.intervalle = INTERVALLE_DEPART
        self.avant_descente = INTERVALLE_DEPART
        terrain = Terrain(RECT_SOLO)
        terrain.ajouter_raquette(self.joueurs[0], -1)
        terrain.couleur_bord = config.ROSE
        self.terrains = [terrain]
        _, pas_y = terrain.pas_grille()
        rangees = getattr(self, "rangees_depart", None) or RANGEES_DEPART
        grille = [generer_rangee(0, self.aleatoire) for _ in range(rangees)]
        terrain.remplir(construire_grille(grille, terrain))
        self.app.fond.changer_monde(1)
        self.servir()
        self.annoncer("ARCADE INFINIE", config.ROSE, 2.0)

    def servir(self):
        terrain = self.terrains[0]
        terrain.balles.vider()
        terrain.tirs.vider()
        terrain.nouvelle_balle_collee(terrain.raquettes[0])
        self.etat = "pret"

    # --- Règles -------------------------------------------------------------------

    def regles(self, dt, dt_jeu):
        terrain = self.terrains[0]
        joueur = self.joueurs[0]
        if joueur.score >= self.prochaine_vie:
            self.prochaine_vie += config.VIE_BONUS_TOUS_LES
            self.gagner_vie(joueur)
        self.app.fond.vitesse_cible = 0.6 + joueur.multiplicateur * 0.4
        if terrain.boss is not None and terrain.boss.est_vaincu():
            terrain.boss = None
        if self.etat == "jeu":
            if terrain.boss is None:                 # le mur attend la fin du mini-boss
                self.avant_descente -= dt_jeu
            if self.avant_descente <= 0:
                self.descendre()
            self.verifier_invasion()
        elif self.etat == "perdu":
            self.minuteur -= dt
            if self.minuteur <= 0:
                self.terminer()
        terrain.couleur_bord = config.ROUGE if (
            self.etat == "jeu" and self.avant_descente < 1.5
            and int(self.temps * 8) % 2) else config.ROSE

    def descendre(self, nb=1):
        """Le mur descend d'un cran et une nouvelle rangée apparaît en haut."""
        terrain = self.terrains[0]
        _, pas_y = terrain.pas_grille()
        for _ in range(nb):
            self.vague += 1
            terrain.decaler_briques(pas_y)
            rangee = generer_rangee(self.vague / 6, self.aleatoire)
            nouvelles = list(construire_grille([rangee], terrain))
            for brique in nouvelles:
                terrain.briques.ajouter_fin(brique)
            terrain.preparer_briques(nouvelles, cascade=False)
            for brique in nouvelles:
                brique.apparition = 0.0
        terrain.niveau_annonce_vide = False
        self.app.fond.changer_monde(1 + min(2, self.vague // 15))
        if self.vague % 10 == 0 and terrain.boss is None:
            terrain.boss = BossDrone(terrain, self.vague // 10)
            self.annoncer(f"MINI-BOSS : {terrain.boss.nom} !", config.ROUGE, 2.0)
            self.effets.eclair(0.4, config.ROUGE)
            self.audio("alerte", 0.8)
        self.intervalle = max(INTERVALLE_MIN, self.intervalle * 0.95)
        self.avant_descente = self.intervalle
        self.effets.secouer(4)
        self.audio("metal", 0.6)

    def verifier_invasion(self):
        """Une brique atteint la ligne de la raquette : fin de partie."""
        terrain = self.terrains[0]
        limite = terrain.raquettes[0].y - 24
        if any(b.y + b.hauteur >= limite for b in terrain.briques if b.solide):
            self.annoncer("INVASION !", config.ROUGE, 2.5)
            self.vies = 0
            self.fin_de_partie()

    def sur_boss_mort(self, terrain, x, y):
        super().sur_boss_mort(terrain, x, y)
        joueur = self.joueurs[0]
        joueur.stats["boss_vaincus"].append("drone")
        self.gagner_vie(joueur)
        self.annoncer("MINI-BOSS VAINCU ! +1 VIE", config.AMBRE, 2.2)

    def gagner_vie(self, joueur):
        self.vies += 1
        self.effets.texte("+1 VIE", joueur.raquette.x, joueur.raquette.y - 50,
                          config.VERT, 3, duree=1.3)

    def sur_plus_de_balle(self, terrain):
        if self.etat not in ("jeu", "pret"):
            return
        self.vies -= 1
        self.joueurs[0].reinitialiser_manche()
        self.joueurs[0].stats["vies_perdues"] += 1
        self.effets.secouer(14)
        self.effets.eclair(0.35, config.ROUGE)
        self.app.crt.declencher_aberration(1.0)
        self.audio("vie_perdue")
        if self.vies <= 0:
            self.fin_de_partie()
        else:
            self.annoncer(f"{self.vies} VIE{'S' if self.vies > 1 else ''}", config.ROUGE, 1.2)
            self.servir()

    def fin_de_partie(self):
        if self.etat == "perdu":
            return
        self.etat = "perdu"
        self.minuteur = 1.6
        self.effets.ralentir(0.3, 1.5)
        self.effets.eclair(0.5, config.ROUGE)
        self.audio("vie_perdue")

    def sur_niveau_vide(self, terrain):
        """Écran vidé : gros bonus et quatre nouvelles rangées d'un coup."""
        if self.etat != "jeu":
            return
        joueur = self.joueurs[0]
        joueur.score += BONUS_ECRAN_VIDE
        self.annoncer(f"ECRAN VIDE +{BONUS_ECRAN_VIDE}", config.AMBRE, 1.8)
        self.effets.eclair(0.6)
        self.audio("victoire", 0.6)
        self.descendre(4)

    def terminer(self):
        joueur = self.joueurs[0]
        self.etat = "fin"
        self.resultat = {
            "victoire": False, "score": joueur.score, "mode": self.code,
            "titre": "GAME OVER",
            "lignes": [("VAGUES", str(self.vague)),
                       ("BRIQUES CASSEES", str(joueur.stats["briques"])),
                       ("MEILLEUR COMBO", str(joueur.stats["meilleur_combo"]))],
            "rapports": self.rapports(victoire=False, vagues=self.vague),
        }

    # --- Dessin -------------------------------------------------------------------

    def record_affiche(self):
        """But : record montré en haut à gauche."""
        return self.app.meilleur_score(self.code)

    def dessiner_hud(self, image):
        joueur = self.joueurs[0]
        hud.panneau(image, PANNEAU_G, config.ROSE)
        hud.etiquette(image, "RECORD", PANNEAU_G.centerx, 50)
        record = max(self.record_affiche(), joueur.score)
        dessiner_texte(image, f"{record:07d}", PANNEAU_G.centerx, 72, 2, config.BLANC,
                       lueur=False)
        hud.bloc_joueur_vertical(image, PANNEAU_G, joueur, 104, self.temps,
                                 touches_pouvoirs=["1", "2", "3"], touche_overdrive="MAJ")
        hud.etiquette(image, "VIES", PANNEAU_G.centerx, 606)
        hud.dessiner_vies(image, PANNEAU_G.centerx, 636, self.vies)

        hud.panneau(image, PANNEAU_D, config.ROSE)
        cx = PANNEAU_D.centerx
        hud.etiquette(image, "VAGUE", cx, 50)
        dessiner_texte(image, str(self.vague), cx, 86, 5, config.ROSE)
        hud.etiquette(image, "DESCENTE DANS", cx, 150)
        couleur = config.ROUGE if self.avant_descente < 1.5 else config.CYAN
        if self.terrains[0].boss is not None:
            dessiner_texte(image, "BOSS !", cx, 180, 3, config.ROSE)
        else:
            dessiner_texte(image, f"{max(0, self.avant_descente):.1f} S", cx, 180, 3, couleur)
        hud.barre(image, pygame.Rect(PANNEAU_D.x + 24, 204, PANNEAU_D.w - 48, 10),
                  1 - self.avant_descente / self.intervalle, couleur)
        hud.etiquette(image, "BRIQUES", cx, 250)
        dessiner_texte(image, str(self.terrains[0].briques_restantes()), cx, 280, 4,
                       config.AMBRE)
        hud.etiquette(image, "COMMANDES", cx, 500, config.ROSE)
        hud.dessiner_commandes(image, PANNEAU_D, "solo", 528, self.app)

    def dessiner_overlay(self, image):
        terrain = self.terrains[0]
        # Ligne d'invasion : la frontière à ne pas laisser franchir.
        limite = terrain.raquettes[0].y - 24
        for x in range(terrain.rect.left, terrain.rect.right, 20):
            image.fill((120, 20, 50), (x, limite, 10, 2))
        if self.etat == "pret" and math.sin(self.temps * 6) > -0.3:
            dessiner_texte(image, "ESPACE / CLIC : LANCER", terrain.rect.centerx,
                           terrain.raquettes[0].y - 70, 2, config.AMBRE)
