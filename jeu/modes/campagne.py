# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Modes à niveaux :
      - Campagne : 12 niveaux en 3 mondes, un boss tous les 4 niveaux,
        3 vies, vie bonus tous les 20 000 points, progression sauvegardée ;
      - Hardcore : la même campagne en 1 vie, balle +30 %, malus seulement,
        ni pouvoirs ni OVERDRIVE, score x2 ;
      - Coop : deux raquettes en bas sur un terrain plus large, vies et
        score d'équipe.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Niveaux secrets, chrono par niveau.
"""

import math

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from jeu.boss import BOSS
from jeu.joueur import Joueur
from jeu.modes.base import ModeDeJeu
from jeu.niveau import charger_campagne
from jeu.terrain import Terrain
from ecrans import hud

RECT_SOLO = pygame.Rect(260, 24, 760, 696)
PANNEAU_G = pygame.Rect(20, 24, 220, 672)
PANNEAU_D = pygame.Rect(1040, 24, 220, 672)
COULEURS_MONDES = {1: config.CYAN, 2: config.BLEU, 3: config.VERT}
BONUS_VIE = 1000
BONUS_TEMPS_MAX = 3000
TEMPS_CIBLE = 100                 # 3e étoile : niveau fini en moins de 100 s...
TEMPS_CIBLE_BOSS = 150            # ... ou 150 s pour un boss


def temps_cible(niveau):
    """But : temps à battre pour la 3e étoile d'un niveau (s). Sortie : (int)."""
    return TEMPS_CIBLE_BOSS if niveau.boss else TEMPS_CIBLE


def etoiles_niveau(pertes, temps, niveau):
    """
    But : étoiles gagnées sur un niveau terminé, sous forme de masque : bit 0 pour
    l'avoir fini, bit 1 sans perdre de vie, bit 2 sous le temps cible. Chaque
    étoile peut être gagnée lors d'une partie différente. Sortie : (int) 1 à 7.
    """
    return 1 | (2 if pertes == 0 else 0) | (4 if temps <= temps_cible(niveau) else 0)


def nombre_etoiles(masque):
    """But : nombre d'étoiles d'un masque. Sortie : (int) 0 à 3."""
    return bin(int(masque) & 7).count("1")


class ModeCampagne(ModeDeJeu):
    """
    Attributs : niveaux (list de Niveau), indice (int), niveau (Niveau),
    vies (int), hardcore (bool), bilan (list), bilan_affiche (float),
    temps_niveau (float), total_briques (int).
    """

    code = "campagne"
    titre = "CAMPAGNE"

    def __init__(self, app, effets, indice=0, hardcore=False):
        super().__init__(app, effets)
        self.hardcore = hardcore
        if hardcore:
            self.code, self.titre = "hardcore", "HARDCORE"
            self.multiplicateur_score = 2
        self.niveaux = charger_campagne()
        self.joueurs = self.creer_joueurs()
        for joueur in self.joueurs:
            joueur.avec_overdrive = not hardcore
            joueur.avec_pouvoirs = not hardcore
        self.vies = 1 if hardcore else self.vies_depart()
        self.prochaine_vie = config.VIE_BONUS_TOUS_LES
        self.bilan = []
        self.bilan_affiche = 0.0
        self.temps_niveau = 0.0
        self.temps_total = 0.0
        self.indice = indice
        self.indice_depart = indice
        self.etoiles_partie = {}
        self.etoiles_niveau = 0
        self.charger_niveau(indice)

    # --- Mise en place -------------------------------------------------------------

    def creer_joueurs(self):
        """But : un joueur solo (souris + clavier)."""
        self.souris_active = True
        return [Joueur(1, "solo", "J1")]

    def vies_depart(self):
        return config.VIES_DEPART

    def rect_terrain(self):
        return RECT_SOLO

    def charger_niveau(self, indice):
        """
        But : installer le niveau n° indice (nouveau terrain, boss éventuel,
        thème du monde, balle sur la raquette).
        Entrée : indice (int). Sortie : aucune.
        """
        self.indice = indice
        self.niveau = self.niveaux[indice]
        terrain = Terrain(self.rect_terrain())
        for i, joueur in enumerate(self.joueurs):
            raquette = terrain.ajouter_raquette(joueur, -1)
            if len(self.joueurs) > 1:
                raquette.x = terrain.rect.x + terrain.rect.w * (i + 1) / (len(self.joueurs) + 1)
            joueur.reinitialiser_manche()
            joueur.filets = 0
            joueur.stats["malus_niveau"] = 0
        terrain.remplir(self.niveau.construire(terrain))
        terrain.vitesse_balle = (config.BALLE_VITESSE_DEPART * self.niveau.vitesse
                                 * (1.3 if self.hardcore else 1.0))
        if self.hardcore:
            terrain.poids_capsules = {"malus": 1}
            terrain.chance_capsule = 0.10
        if self.niveau.boss in BOSS:
            terrain.boss = BOSS[self.niveau.boss](terrain)
        terrain.couleur_bord = COULEURS_MONDES.get(self.niveau.monde, config.CYAN)
        self.terrains = [terrain]
        self.app.fond.changer_monde(self.niveau.monde)
        self.total_briques = max(1, terrain.briques_restantes())
        self.temps_niveau = 0.0
        self.pertes_niveau = 0
        self.servir()
        self.etat = "pret"
        if self.niveau.boss:
            self.annoncer("ALERTE BOSS !", config.ROUGE, 2.2)
            self.audio("alerte", 0.8)
            self.effets.eclair(0.4, config.ROUGE)

    def servir(self):
        """But : une balle posée sur chaque raquette."""
        terrain = self.terrains[0]
        terrain.balles.vider()
        terrain.capsules.vider()
        terrain.tirs.vider()
        for raquette in terrain.raquettes:
            terrain.nouvelle_balle_collee(raquette)

    # --- Règles -------------------------------------------------------------------

    def regles(self, dt, dt_jeu):
        terrain = self.terrains[0]
        if self.etat == "jeu":
            self.temps_niveau += dt_jeu
        if not self.hardcore and self.score_total() >= self.prochaine_vie:
            self.prochaine_vie += config.VIE_BONUS_TOUS_LES
            self.gagner_vie(self.joueurs[0])
        fond = self.app.fond
        fond.vitesse_cible = 0.6 + max(j.multiplicateur for j in self.joueurs) * 0.4
        fond.progression = 1 - terrain.briques_restantes() / self.total_briques
        if self.etat == "victoire":
            self.minuteur -= dt
            if self.minuteur <= 0:
                self.preparer_bilan()
        elif self.etat == "bilan":
            self.mettre_a_jour_bilan(dt)
        elif self.etat == "perdu":
            self.minuteur -= dt
            if self.minuteur <= 0:
                self.terminer(False)

    def gagner_vie(self, joueur):
        self.vies += 1
        raquette = joueur.raquette
        self.effets.texte("+1 VIE", raquette.x, raquette.y - 50, config.VERT, 3,
                          duree=1.3)
        self.audio("victoire", 0.4)

    def sur_plus_de_balle(self, terrain):
        if self.etat in ("jeu", "pret"):
            self.perdre_vie()

    def perdre_vie(self):
        """Plus aucune balle en jeu : une vie de moins."""
        self.vies -= 1
        self.pertes_niveau = getattr(self, "pertes_niveau", 0) + 1
        terrain = self.terrains[0]
        for joueur in self.joueurs:
            joueur.reinitialiser_manche()
            joueur.stats["vies_perdues"] += 1
        raquette = terrain.raquettes[0]
        self.effets.secouer(14)
        self.effets.eclair(0.35, config.ROUGE)
        self.effets.geler(0.12)
        self.effets.onde(raquette.x, raquette.y, config.ROUGE, 300, 0.7, 10)
        self.app.crt.declencher_aberration(1.0)
        self.audio("vie_perdue")
        if self.vies <= 0:
            self.etat = "perdu"
            self.minuteur = 1.4
            self.effets.ralentir(0.3, 1.4)
        else:
            self.annoncer(f"{self.vies} VIE{'S' if self.vies > 1 else ''}", config.ROUGE, 1.2)
            self.servir()
            self.etat = "pret"

    def sur_niveau_vide(self, terrain):
        if self.etat not in ("jeu", "pret"):
            return
        self.etat = "victoire"
        self.minuteur = 1.8
        for joueur in self.joueurs:
            joueur.stats["niveaux_finis"] += 1
            if joueur.stats["malus_niveau"] >= 5:
                joueur.stats["niveau_5_malus"] = True
            if self.niveau.boss:
                joueur.stats["boss_vaincus"].append(self.niveau.boss)
        self.effets.ralentir(0.25, 1.2)
        self.effets.eclair(0.8)
        self.effets.secouer(8)
        self.app.crt.declencher_aberration(1.0)
        cx, cy = terrain.rect.center
        self.effets.onde(cx, cy, config.AMBRE, 600, 1.0, 12)
        for couleur in config.COULEURS_NEON:
            self.effets.explosion(cx, cy - 100, couleur, 20, 520, taille=4, vie=1.4,
                                  gravite=250)
        self.audio("victoire")

    def preparer_bilan(self):
        """Bonus de fin de niveau, affichés un par un."""
        terrain = self.terrains[0]
        terrain.balles.vider()
        terrain.capsules.vider()
        self.temps_total += self.temps_niveau
        facteur = self.multiplicateur_score
        bonus_temps = max(0, int(BONUS_TEMPS_MAX - self.temps_niveau * 20)) // 10 * 10
        self.bilan = [("BONUS VIES", self.vies * BONUS_VIE * facteur),
                      ("BONUS TEMPS", bonus_temps * facteur)]
        if self.niveau.boss:
            self.bilan.append(("BOSS VAINCU", 0))
        self.scores_avant = [j.score for j in self.joueurs]
        self.bilan_affiche = 0.0
        self.etat = "bilan"
        self.etoiles_niveau = etoiles_niveau(self.pertes_niveau, self.temps_niveau, self.niveau)
        cumul = self.memoriser_etoiles(self.indice, self.etoiles_niveau)
        self.etoiles_partie[str(self.indice)] = nombre_etoiles(cumul)
        self.debloquer(self.indice + 1)

    def memoriser_etoiles(self, indice, etoiles):
        """
        But : ajouter les étoiles gagnées à celles du niveau (carte du monde).
        Sortie : (int) masque cumulé.
        """
        toutes = self.app.donnees.setdefault("etoiles", {}).setdefault(self.code, {})
        ancien = int(toutes.get(str(indice), 0))
        if self.en_ligne:
            return ancien | etoiles
        if ancien | etoiles != ancien:
            toutes[str(indice)] = ancien | etoiles
            self.app.enregistrer()
        return ancien | etoiles

    def mettre_a_jour_bilan(self, dt):
        """Décompte des bonus, puis Entrée pour continuer."""
        self.bilan_affiche = min(len(self.bilan), self.bilan_affiche + dt * 2.5)
        total = sum(v for _, v in self.bilan[:int(self.bilan_affiche)])
        part = total // len(self.joueurs)
        for joueur, avant in zip(self.joueurs, self.scores_avant):
            joueur.score = avant + part
        entrees = self.app.entrees
        if self.bilan_affiche >= len(self.bilan) and (
                entrees.vient_d_appuyer("valider") or 1 in entrees.clics
                or any(entrees.vient_d_appuyer("action", j.profil) for j in self.joueurs)):
            self.niveau_suivant()

    def debloquer(self, indice):
        """But : mémoriser le niveau atteint (sélection de niveau)."""
        progression = self.app.donnees.setdefault("progression", {})
        cle = "coop" if self.code == "coop" else "campagne"
        if indice > progression.get(cle, 0):
            progression[cle] = min(indice, len(self.niveaux) - 1)
            self.app.enregistrer()

    def niveau_suivant(self):
        """Niveau suivant (avec transition VHS) ou fin de la campagne."""
        self.etat = "fin_niveau"
        if self.indice + 1 < len(self.niveaux):
            suivant = self.indice + 1
            self.app.lancer_transition(lambda: self.charger_niveau(suivant))
        else:
            self.terminer(True)

    def terminer(self, victoire):
        """But : remplir le résultat de la partie."""
        self.etat = "fin"
        meilleur_combo = max(j.stats["meilleur_combo"] for j in self.joueurs)
        briques = sum(j.stats["briques"] for j in self.joueurs)
        self.resultat = {
            "victoire": victoire, "score": self.score_total(), "mode": self.code,
            "titre": "VICTOIRE !" if victoire else "GAME OVER",
            "lignes": [("NIVEAU ATTEINT", f"{self.indice + 1} / {len(self.niveaux)}"),
                       ("BRIQUES CASSEES", str(briques)),
                       ("MEILLEUR COMBO", str(meilleur_combo))],
            "rapports": self.rapports(victoire=victoire, indice_depart=self.indice_depart,
                                      niveau_atteint=self.indice + 1,
                                      etoiles=dict(self.etoiles_partie),
                                      score_equipe=self.score_total()),
        }

    # --- Dessin -------------------------------------------------------------------

    def dessiner_hud(self, image):
        joueur = self.joueurs[0]
        hud.panneau(image, PANNEAU_G, config.ROSE)
        hud.etiquette(image, "RECORD", PANNEAU_G.centerx, 50)
        record = max(self.app.meilleur_score(self.code), joueur.score)
        dessiner_texte(image, f"{record:07d}", PANNEAU_G.centerx, 72, 2,
                       config.BLANC, lueur=False)
        hud.bloc_joueur_vertical(image, PANNEAU_G, joueur, 104, self.temps,
                                 touches_pouvoirs=["1", "2", "3"], touche_overdrive="MAJ")
        hud.etiquette(image, "VIES", PANNEAU_G.centerx, 606)
        hud.dessiner_vies(image, PANNEAU_G.centerx, 636, self.vies)
        self.dessiner_panneau_droit(image)

    def dessiner_panneau_droit(self, image, rect=PANNEAU_D, aide="solo"):
        """Niveau, briques restantes, vitesse, commandes."""
        hud.panneau(image, rect, config.CYAN)
        cx = rect.centerx
        hud.etiquette(image, "NIVEAU", cx, 50)
        dessiner_texte(image, f"{self.indice + 1} / {len(self.niveaux)}", cx, 84, 4,
                       config.CYAN)
        for i, ligne in enumerate(couper(self.niveau.nom, 14)[:3]):
            dessiner_texte(image, ligne, cx, 124 + i * 20, 2, config.BLANC, lueur=False)
        hud.etiquette(image, "BRIQUES", cx, 210)
        dessiner_texte(image, str(self.terrains[0].briques_restantes()), cx, 242, 4,
                       config.AMBRE)
        hud.etiquette(image, "VITESSE", cx, 296)
        vitesse = max((b.vitesse() * b.facteur_vitesse() for b in self.terrains[0].balles),
                      default=0)
        hud.barre(image, pygame.Rect(rect.x + 24, 316, rect.w - 48, 10),
                  vitesse / (config.BALLE_VITESSE_MAX * 1.3), config.ROSE)
        if self.hardcore:
            dessiner_texte(image, "HARDCORE x2", cx, 362, 2, config.ROUGE)
        hud.etiquette(image, "COMMANDES", cx, 500, config.ROSE)
        hud.dessiner_commandes(image, rect, aide, 528)

    def dessiner_overlay(self, image):
        """Texte « lancer », bilan de niveau."""
        terrain = self.terrains[0]
        if self.etat == "pret" and math.sin(self.temps * 6) > -0.3:
            texte = "ESPACE / CLIC : LANCER" if (not self.deux_joueurs or self.en_ligne) \
                else "Z  /  ↑ : LANCER"
            dessiner_texte(image, texte, terrain.rect.centerx, terrain.raquettes[0].y - 70,
                           2, config.AMBRE)
        if self.etat == "bilan":
            self.dessiner_bilan(image)

    def dessiner_bilan(self, image):
        from ecrans.base import voile
        terrain = self.terrains[0]
        cadre = pygame.Rect(0, 0, 560, 360)
        cadre.center = terrain.rect.center
        voile(image, 120)
        hud.panneau(image, cadre, config.AMBRE)
        dessiner_texte(image, "NIVEAU TERMINE !", cadre.centerx, cadre.y + 45, 4,
                       config.AMBRE)
        apparues = self.etoiles_niveau & ((1 << min(3, int(self.bilan_affiche * 2))) - 1)
        hud.dessiner_etoiles(image, 0, (cadre.centerx, cadre.y + 92), 16, masque=apparues)
        cible = temps_cible(self.niveau)
        dessiner_texte(image, f"{'SANS PERDRE DE VIE' if self.pertes_niveau == 0 else 'VIE PERDUE'}"
                       f"   {int(self.temps_niveau)} S / {cible} S", cadre.centerx, cadre.y + 122,
                       2, (170, 140, 220), lueur=False)
        for i, (libelle, valeur) in enumerate(self.bilan):
            if i >= int(self.bilan_affiche):
                break
            y = cadre.y + 160 + i * 34
            dessiner_texte(image, libelle, cadre.x + 40, y, 2, config.CYAN,
                           ancrage="gauche", lueur=False)
            dessiner_texte(image, f"+{valeur}", cadre.right - 40, y, 2, config.BLANC,
                           ancrage="droite", lueur=False)
        if self.bilan_affiche >= len(self.bilan):
            y = cadre.y + 170 + len(self.bilan) * 34
            pygame.draw.line(image, config.AMBRE, (cadre.x + 40, y - 18),
                             (cadre.right - 40, y - 18), 1)
            dessiner_texte(image, "SCORE", cadre.x + 40, y, 3, config.AMBRE,
                           ancrage="gauche", lueur=False)
            dessiner_texte(image, f"{self.score_total():07d}", cadre.right - 40, y, 3,
                           config.AMBRE, ancrage="droite")
            if math.sin(self.temps * 6) > -0.3:
                suite = "NIVEAU SUIVANT" if self.indice + 1 < len(self.niveaux) \
                    else "VOIR LE RESULTAT"
                dessiner_texte(image, f"ENTREE : {suite}", cadre.centerx,
                               cadre.bottom - 30, 2, config.ROSE)


def couper(texte, largeur):
    """But : couper un texte en lignes d'au plus `largeur` caractères."""
    lignes, courante = [], ""
    for mot in texte.split():
        essai = (courante + " " + mot).strip()
        if len(essai) > largeur and courante:
            lignes.append(courante)
            courante = mot
        else:
            courante = essai
    lignes.append(courante)
    return lignes


class ModeCoop(ModeCampagne):
    """Deux raquettes en bas, vies et score d'équipe, terrain plus large."""

    code = "coop"
    titre = "COOP"
    deux_joueurs = True
    RECT = pygame.Rect(220, 24, 840, 696)
    PANNEAU_G = pygame.Rect(20, 24, 180, 672)
    PANNEAU_D = pygame.Rect(1080, 24, 180, 672)

    def creer_joueurs(self):
        self.souris_active = False
        return [Joueur(1, "j1", "J1"), Joueur(2, "j2", "J2")]

    def vies_depart(self):
        return 4

    def rect_terrain(self):
        return self.RECT

    def dessiner_hud(self, image):
        gauche, droite = self.PANNEAU_G, self.PANNEAU_D
        hud.panneau(image, gauche, self.joueurs[0].couleur_bord)
        hud.etiquette(image, "EQUIPE", gauche.centerx, 46)
        dessiner_texte(image, f"{self.score_total():07d}", gauche.centerx, 74, 3, config.AMBRE)
        hud.dessiner_vies(image, gauche.centerx, 110, self.vies)
        hud.bloc_joueur_vertical(image, gauche, self.joueurs[0], 172, self.temps,
                                 titre=self.nom_joueur(self.joueurs[0]),
                                 touche_overdrive="MAJ" if self.en_ligne else "S")
        hud.panneau(image, droite, self.joueurs[1].couleur_bord)
        hud.etiquette(image, "NIVEAU", droite.centerx, 46)
        dessiner_texte(image, f"{self.indice + 1} / {len(self.niveaux)}", droite.centerx,
                       76, 3, config.CYAN)
        hud.etiquette(image, f"BRIQUES {self.terrains[0].briques_restantes()}",
                      droite.centerx, 110, config.AMBRE)
        hud.bloc_joueur_vertical(image, droite, self.joueurs[1], 172, self.temps,
                                 titre=self.nom_joueur(self.joueurs[1]),
                                 touche_overdrive="MAJ" if self.en_ligne else "↓")
