# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Un Terrain est une zone de jeu autonome : murs, raquettes (une ou deux,
    en bas et/ou en haut), balles, briques, capsules, projectiles et boss.
    Il ne s'occupe ni du score ni des règles : il signale ce qui arrive en
    enfilant des événements dans une File maison, que le mode de jeu traite.
    Le mode Course utilise deux terrains côte à côte.

    Physique reprise de partie.py (version Tkinter) :
      - rebond raquette : réflexion de Descartes sur une normale inclinée
        selon le point d'impact (±30°), garde-fou à 70° de la verticale ;
      - collision disque/rectangle par le point le plus proche, rebond sur
        la face de plus faible pénétration.
    Ajouts : sous-pas (la balle ne traverse jamais rien), dégagement hors
    des briques, pente minimale, briques spéciales, explosions en chaîne.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Partitionnement spatial si les niveaux deviennent très denses.
"""

import math
import random

import pygame

from structures.file import File
from structures.liste import Liste
from moteur import config
from moteur.rendu import ajouter_lueur, halo_rect, attenuer
from jeu.balle import Balle
from jeu.capsule import Capsule, tirer_effet
from jeu.projectiles import Laser
from jeu.raquette import Raquette

ANGLE_NORMALE_MAX = math.radians(config.ANGLE_NORMALE_MAX)
ANGLE_MAX_VERTICALE = math.radians(config.ANGLE_MAX_VERTICALE)
ANGLE_MIN_HORIZONTAL = math.radians(12)
MARGE_GRILLE = 22
CADENCE_LASER = 0.2
DELAI_REGENERATION = 6.0
DUREE_AIMANT = 3.0


# --- Fonctions de collision (testées dans tests/) --------------------------

def point_le_plus_proche(cx, cy, boite):
    """
    But : trouver le point d'un rectangle le plus proche d'un point
    (projection du centre sur le rectangle, axe par axe).
    Entrées : cx, cy (float) ; boite (tuple) (x_min, y_min, x_max, y_max).
    Sortie : (tuple) (x_proche, y_proche).
    """
    x_min, y_min, x_max, y_max = boite
    return min(max(cx, x_min), x_max), min(max(cy, y_min), y_max)


def disque_touche_boite(cx, cy, rayon, boite):
    """
    But : tester si un disque chevauche un rectangle.
    Entrées : cx, cy, rayon (float) ; boite (tuple). Sortie : (bool).
    """
    px, py = point_le_plus_proche(cx, cy, boite)
    return (cx - px) ** 2 + (cy - py) ** 2 <= rayon ** 2


def boites_se_touchent(a, b):
    """But : intersection de deux boîtes (x_min, y_min, x_max, y_max)."""
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


def face_touchee(balle, boite):
    """
    But : déterminer la face d'un rectangle touchée par la balle.
    Entrées : balle (Balle) ; boite (tuple).
    Sortie : (str) "gauche", "droite", "haut" ou "bas".
    """
    x_min, y_min, x_max, y_max = boite
    px, py = point_le_plus_proche(balle.x, balle.y, boite)
    ecart_x = abs(balle.x - px)
    ecart_y = abs(balle.y - py)
    if ecart_x == 0 and ecart_y == 0:
        penetration_x = min(balle.x - x_min, x_max - balle.x)
        penetration_y = min(balle.y - y_min, y_max - balle.y)
        laterale = penetration_x < penetration_y
    else:
        laterale = ecart_x > ecart_y
    if laterale:
        return "gauche" if balle.x < (x_min + x_max) / 2 else "droite"
    return "haut" if balle.y < (y_min + y_max) / 2 else "bas"


def rebondir_sur_boite(balle, boite):
    """
    But : faire rebondir la balle sur la face touchée (inversion de la
    composante normale) et la replacer juste à l'extérieur de la boîte.
    Entrées : balle (Balle) ; boite (tuple). Sortie : (str) face touchée.
    """
    x_min, y_min, x_max, y_max = boite
    face = face_touchee(balle, boite)
    if face == "gauche":
        balle.vx = -abs(balle.vx)
        balle.x = min(balle.x, x_min - balle.rayon)
        balle.rebondir_effet(1, 0)
    elif face == "droite":
        balle.vx = abs(balle.vx)
        balle.x = max(balle.x, x_max + balle.rayon)
        balle.rebondir_effet(1, 0)
    elif face == "haut":
        balle.vy = -abs(balle.vy)
        balle.y = min(balle.y, y_min - balle.rayon)
        balle.rebondir_effet(0, 1)
    else:
        balle.vy = abs(balle.vy)
        balle.y = max(balle.y, y_max + balle.rayon)
        balle.rebondir_effet(0, 1)
    return face


def rebond_raquette(balle, boite_raquette, sens=-1):
    """
    But : rebond sur la raquette (algorithme de la version Tkinter).
    La normale locale s'incline selon le point d'impact (jusqu'à 30° aux
    extrémités), puis réflexion de Descartes v' = v - 2 (v.n) n, et
    garde-fou : la balle repart à au plus 70° de la verticale.
    Entrées : balle (Balle) ; boite_raquette (tuple) ;
              sens (int) : -1 la balle repart vers le haut, +1 vers le bas.
    Sortie : (float) décalage d'impact dans [-1, 1].
    """
    rx1, _, rx2, _ = boite_raquette
    centre = (rx1 + rx2) / 2
    demi_largeur = (rx2 - rx1) / 2
    decalage = max(-1.0, min(1.0, (balle.x - centre) / demi_largeur))

    alpha = decalage * ANGLE_NORMALE_MAX
    normale_x = math.sin(alpha)
    normale_y = sens * math.cos(alpha)
    produit = balle.vx * normale_x + balle.vy * normale_y
    if produit < 0:
        balle.vx -= 2 * produit * normale_x
        balle.vy -= 2 * produit * normale_y

    norme = math.hypot(balle.vx, balle.vy)
    # Angle par rapport à la verticale, dans le sens de départ voulu
    # (pour sens = -1 : atan2(vx, -vy), exactement comme la version Tkinter).
    angle = math.atan2(balle.vx, sens * balle.vy)
    angle = max(-ANGLE_MAX_VERTICALE, min(ANGLE_MAX_VERTICALE, angle))
    balle.vx = norme * math.sin(angle)
    balle.vy = sens * norme * math.cos(angle)
    balle.rebondir_effet(0, 1)
    return decalage


def corriger_angle(balle):
    """
    But : éviter les trajectoires presque horizontales (allers-retours sans
    fin entre les murs) : au moins 12° de pente.
    Entrée : balle (Balle). Sortie : aucune.
    """
    norme = balle.vitesse()
    if norme == 0:
        return
    if abs(balle.vy) < norme * math.sin(ANGLE_MIN_HORIZONTAL):
        signe_y = 1 if balle.vy >= 0 else -1
        signe_x = 1 if balle.vx >= 0 else -1
        balle.vy = signe_y * norme * math.sin(ANGLE_MIN_HORIZONTAL)
        balle.vx = signe_x * norme * math.cos(ANGLE_MIN_HORIZONTAL)


class Terrain:
    """
    Zone de jeu.
    Attributs :
        rect (pygame.Rect) : limites ; mur_haut (bool) : False en Duel.
        raquettes (list de Raquette) ; balles, briques, capsules,
        lasers, tirs (Liste) ; boss (Boss ou None).
        evenements (File) : ce qui s'est passé, à traiter par le mode.
        vitesse_balle (float) : vitesse de lancement des balles.
        chrono (float) : temps restant du pouvoir CHRONO (balles ralenties).
        chance_capsule (float), poids_capsules (dict ou None).
        brique_l, brique_h (int) : taille des briques de ce terrain.
    Événements enfilés (tuples) :
        ("raquette", balle, raquette) ; ("mur", balle) ;
        ("brique_touchee", brique, balle) ;
        ("brique_detruite", brique, joueur) ; ("explosion", x, y, rayon) ;
        ("capsule", capsule, joueur) ; ("portail", balle) ; ("filet", joueur) ;
        ("balle_perdue", balle, cote) ; ("plus_de_balle",) ;
        ("raquette_touchee", raquette) ; ("boss_touche", balle) ;
        ("niveau_vide",).
    """

    def __init__(self, rect, mur_haut=True):
        self.rect = pygame.Rect(rect)
        self.mur_haut = mur_haut
        self.raquettes = []
        self.balles = Liste()
        self.briques = Liste()
        self.capsules = Liste()
        self.lasers = Liste()
        self.tirs = Liste()
        self.boss = None
        self.evenements = File()
        self.vitesse_balle = config.BALLE_VITESSE_DEPART
        self.temps = 0.0
        self.chrono = 0.0
        self.chance_capsule = config.CHANCE_CAPSULE
        self.poids_capsules = None
        self.regenerations = []
        self.niveau_annonce_vide = False
        self.couleur_bord = config.CYAN
        pas = (self.rect.w - 2 * MARGE_GRILLE + config.BRIQUE_ESPACE) / config.NB_COLONNES
        self.brique_l = int(pas - config.BRIQUE_ESPACE)
        self.brique_h = config.BRIQUE_H
        self.cadre = self._creer_cadre()
        self._minuteurs_laser = {}
        self._minuteurs_rayon = {}

    def _creer_cadre(self):
        """
        Fond assombri du terrain, quadrillé (pré-calculé). Deux calques à opacité
        uniforme (set_alpha) avec une couleur transparente (colorkey), plutôt qu'un
        calque transparent pixel par pixel : même rendu, bien plus rapide à copier.
        Sortie : (list de Surface) à copier l'une après l'autre.
        """
        cle = (255, 0, 255)
        fond = pygame.Surface(self.rect.size)
        fond.fill((10, 0, 26))
        lignes = pygame.Surface(self.rect.size)
        lignes.fill(cle)
        for calque, couleur in ((fond, cle), (lignes, (60, 20, 100))):
            for y in range(0, self.rect.h, 40):
                pygame.draw.line(calque, couleur, (0, y), (self.rect.w, y))
            for x in range(0, self.rect.w, 40):
                pygame.draw.line(calque, couleur, (x, 0), (x, self.rect.h))
            calque.set_colorkey(cle, pygame.RLEACCEL)
        fond.set_alpha(205, pygame.RLEACCEL)
        lignes.set_alpha(60, pygame.RLEACCEL)
        return [fond, lignes]

    # --- Mise en place -------------------------------------------------------

    def ajouter_raquette(self, joueur, sens=-1):
        """
        But : créer la raquette d'un joueur, en bas (sens -1) ou en haut (+1).
        Entrées : joueur (Joueur) ; sens (int). Sortie : (Raquette).
        """
        if sens < 0:
            y = self.rect.bottom - config.RAQUETTE_MARGE_BAS
        else:
            y = self.rect.top + config.RAQUETTE_MARGE_BAS - config.RAQUETTE_H
        raquette = Raquette(self.rect.left, self.rect.right, y, sens=sens,
                            joueur=joueur)
        joueur.raquette = raquette
        joueur.terrain = self
        self.raquettes.append(raquette)
        return raquette

    def joueurs(self):
        """But : joueurs présents sur ce terrain. Sortie : (list)."""
        return [r.joueur for r in self.raquettes if r.joueur is not None]

    def pas_grille(self):
        """But : (pas horizontal, pas vertical) de la grille de briques."""
        return (self.brique_l + config.BRIQUE_ESPACE,
                self.brique_h + config.BRIQUE_ESPACE)

    def remplir(self, briques, cascade=True):
        """
        But : installer les briques d'un niveau : apparition en cascade,
        portails reliés deux à deux, bornes des briques mobiles.
        Entrées : briques (Liste de Brique) ; cascade (bool). Sortie : aucune.
        """
        self.briques = briques
        self.niveau_annonce_vide = False
        self.regenerations = []
        self.preparer_briques(list(briques), cascade)

    def preparer_briques(self, nouvelles, cascade=True):
        """
        But : régler les briques qui viennent d'arriver (portails, mobiles,
        animation d'apparition).
        Entrées : nouvelles (list de Brique) ; cascade (bool). Sortie : aucune.
        """
        pas_x, pas_y = self.pas_grille()
        portails = [b for b in nouvelles if not b.solide and hasattr(b, "jumeau")]
        for a, b in zip(portails[0::2], portails[1::2]):
            a.jumeau, b.jumeau = b, a
        for brique in nouvelles:
            if cascade:
                ligne = (brique.y - self.rect.top) / pas_y
                colonne = (brique.x - self.rect.left) / pas_x
                brique.delai_apparition = max(0, ligne) * 0.06 + colonne * 0.02
            else:
                brique.apparition = 1.0
            if hasattr(brique, "x_min"):
                self._bornes_mobile(brique)

    def _bornes_mobile(self, mobile):
        """Une brique mobile glisse dans l'espace libre de sa ligne."""
        gauche = self.rect.left + 6
        droite = self.rect.right - 6 - mobile.largeur
        for autre in self.briques:
            if autre is mobile or abs(autre.y - mobile.y) > 2:
                continue
            if autre.x + autre.largeur <= mobile.x:
                gauche = max(gauche, autre.x + autre.largeur + config.BRIQUE_ESPACE)
            elif autre.x >= mobile.x + mobile.largeur:
                droite = min(droite, autre.x - config.BRIQUE_ESPACE - mobile.largeur)
        mobile.x_min, mobile.x_max = gauche, max(gauche, droite)

    def nouvelle_balle_collee(self, raquette):
        """
        But : poser une balle sur une raquette (début de vie, service).
        Entrée : raquette (Raquette). Sortie : (Balle) la balle créée.
        """
        balle = Balle(raquette.x, raquette.face_y() + raquette.sens * (config.BALLE_RAYON + 1))
        balle.collee = True
        balle.raquette_collage = raquette
        balle.decalage_collage = 0.0
        balle.proprietaire = raquette.joueur
        self.balles.ajouter_fin(balle)
        return balle

    def lancer_balles(self, raquette):
        """
        But : lancer les balles collées à une raquette.
        Entrée : raquette (Raquette). Sortie : (bool) au moins une est partie.
        """
        lancee = False
        for balle in self.balles:
            if balle.collee and balle.raquette_collage is raquette:
                angle = max(-35, min(35, raquette.vx / 30 + balle.decalage_collage / 3 - 10))
                balle.lancer(self.vitesse_balle, angle, raquette.sens)
                lancee = True
        return lancee

    def briques_restantes(self):
        """
        But : nombre de briques à casser (y compris celles qui vont se
        régénérer). Sortie : (int).
        """
        return (sum(1 for brique in self.briques if brique.destructible)
                + len(self.regenerations))

    def ajouter_balles_multi(self):
        """
        But : diviser chaque balle en trois (bonus MULTI-BALLE).
        Entrée : aucune. Sortie : (int) nombre de balles créées.
        """
        nouvelles = []
        for balle in self.balles:
            if balle.collee:
                continue
            for ecart in (-22, 22):
                if len(self.balles) + len(nouvelles) >= config.BALLES_MAX:
                    break
                copie = Balle(balle.x, balle.y, balle.rayon)
                copie.collee = False
                copie.proprietaire = balle.proprietaire
                copie.feu = balle.feu
                angle = math.radians(ecart)
                copie.vx = balle.vx * math.cos(angle) - balle.vy * math.sin(angle)
                copie.vy = balle.vx * math.sin(angle) + balle.vy * math.cos(angle)
                corriger_angle(copie)
                nouvelles.append(copie)
        for copie in nouvelles:
            self.balles.ajouter_fin(copie)
        return len(nouvelles)

    def decaler_briques(self, dy):
        """
        But : faire descendre (ou monter) toutes les briques (Arcade, Course).
        Entrée : dy (float) pixels. Sortie : aucune.
        """
        for brique in self.briques:
            brique.y += dy
        for entree in self.regenerations:
            entree[0].y += dy

    # --- Simulation ----------------------------------------------------------

    def mettre_a_jour(self, dt, directions):
        """
        But : faire avancer le terrain d'un pas de temps.
        Entrées : dt (float) : secondes de jeu ;
                  directions (dict Raquette -> -1, 0, +1).
        Sortie : aucune (les événements sont dans self.evenements).
        """
        self.temps += dt
        self.chrono = max(0.0, self.chrono - dt)
        for raquette in self.raquettes:
            raquette.mettre_a_jour(dt, directions.get(raquette, 0))
        self._separer_raquettes()
        for brique in self.briques:
            brique.mettre_a_jour(dt)
        self._regenerer(dt)
        if self.boss is not None:
            self.boss.mettre_a_jour(dt, self)

        facteur_temps = 0.4 if self.chrono > 0 else 1.0
        perdues = []
        for balle in self.balles:
            if balle.collee:
                self._suivre_raquette(balle, dt)
                continue
            if getattr(balle, "sursis", None) is not None:
                # En ligne : la balle a passé une raquette dont le joueur décide
                # lui-même des rebonds ; on attend un peu son message avant de la perdre.
                balle.sursis -= dt
                facteur = dt * facteur_temps * balle.facteur_vitesse()
                balle.x += balle.vx * facteur
                balle.y += balle.vy * facteur
                if balle.sursis <= 0:
                    balle.sursis = None
                    perdues.append((balle, balle.cote_sursis))
                continue
            self._guider(balle, dt * facteur_temps)
            cote = self._deplacer_balle(balle, dt * facteur_temps * balle.facteur_vitesse())
            if cote:
                raquette = self._raquette_rebond_client(cote)
                if raquette is not None:
                    balle.sursis = getattr(raquette, "delai_rebond", 0.25)
                    balle.cote_sursis = cote
                else:
                    perdues.append((balle, cote))
        for balle, cote in perdues:
            self.balles.supprimer(balle)
            self.evenements.enfiler(("balle_perdue", balle, cote))
        if perdues and self.balles.est_vide():
            self.evenements.enfiler(("plus_de_balle",))

        self._mettre_a_jour_capsules(dt)
        self._mettre_a_jour_lasers(dt)
        self._mettre_a_jour_tirs(dt * facteur_temps)
        self._rayons_supernova(dt)

        boss_vaincu = self.boss is None or self.boss.est_vaincu()
        if not self.niveau_annonce_vide and boss_vaincu and self.briques_restantes() == 0:
            self.niveau_annonce_vide = True
            self.evenements.enfiler(("niveau_vide",))

    def mettre_a_jour_visuel(self, dt):
        """But : traînées des balles, à chaque image. Entrée : dt (float)."""
        for balle in self.balles:
            balle.mettre_a_jour_visuel(dt)

    def _separer_raquettes(self):
        """Coop : deux raquettes du même côté se repoussent sans se chevaucher."""
        for i, a in enumerate(self.raquettes):
            for b in self.raquettes[i + 1:]:
                if a.sens != b.sens:
                    continue
                ecart = (a.largeur + b.largeur) / 2 + 4 - abs(a.x - b.x)
                if ecart > 0:
                    signe = 1 if a.x >= b.x else -1
                    a.x += signe * ecart / 2
                    b.x -= signe * ecart / 2
                    a.vx, b.vx = b.vx * 0.5, a.vx * 0.5
                    a.contraindre()
                    b.contraindre()

    def _suivre_raquette(self, balle, dt):
        """Une balle collée suit sa raquette ; l'aimant relâche après 3 s."""
        raquette = balle.raquette_collage
        if raquette is None:
            balle.collee = False
            return
        balle.x = raquette.x + balle.decalage_collage
        balle.y = raquette.face_y() + raquette.sens * (balle.rayon + 1)
        if balle.temps_collage > 0:
            balle.temps_collage -= dt
            if balle.temps_collage <= 0:
                angle = max(-50, min(50, balle.decalage_collage))
                balle.lancer(max(self.vitesse_balle, balle.vitesse() or 0),
                             angle, raquette.sens)

    def _guider(self, balle, dt):
        """Pouvoir GUIDAGE : la balle s'oriente vers la brique la plus proche."""
        joueur = balle.proprietaire
        if joueur is None or not joueur.actif("guidage") or joueur.raquette is None:
            return
        if balle.vy * joueur.raquette.sens > 0:       # elle revient vers le joueur
            return
        cibles = [b for b in self.briques if b.destructible]
        if not cibles:
            return
        cible = min(cibles, key=lambda b: (b.x + b.largeur / 2 - balle.x) ** 2
                    + (b.y + b.hauteur / 2 - balle.y) ** 2)
        voulu = math.atan2(cible.y + cible.hauteur / 2 - balle.y,
                           cible.x + cible.largeur / 2 - balle.x)
        actuel = math.atan2(balle.vy, balle.vx)
        ecart = (voulu - actuel + math.pi) % (2 * math.pi) - math.pi
        rotation = max(-2.8 * dt, min(2.8 * dt, ecart))
        norme = balle.vitesse()
        balle.vx = norme * math.cos(actuel + rotation)
        balle.vy = norme * math.sin(actuel + rotation)

    def _deplacer_balle(self, balle, dt):
        """
        But : déplacer une balle en sous-pas et gérer toutes ses collisions.
        Entrées : balle (Balle) ; dt (float).
        Sortie : (str ou None) "bas" / "haut" si la balle sort du terrain.
        """
        distance = balle.vitesse() * dt
        nb_pas = max(1, math.ceil(distance / (balle.rayon * 0.5)))
        sous_dt = dt / nb_pas
        for _ in range(nb_pas):
            balle.x += balle.vx * sous_dt
            balle.y += balle.vy * sous_dt
            self._collision_murs(balle)
            self._collision_barrieres(balle)
            if self._collision_raquettes(balle):
                return None                 # collée par l'aimant
            if self.boss is not None and self.boss.collision_balle(balle, self):
                self.evenements.enfiler(("boss_touche", balle))
            self._collision_briques(balle)
            if balle.y - balle.rayon > self.rect.bottom:
                return "bas"
            if balle.y + balle.rayon < self.rect.top:
                return "haut"
        return None

    def _collision_murs(self, balle):
        """Rebonds sur les murs gauche, droit (et haut s'il existe)."""
        touche = False
        if balle.x - balle.rayon < self.rect.left:
            balle.x = self.rect.left + balle.rayon
            balle.vx = abs(balle.vx)
            balle.rebondir_effet(1, 0)
            touche = True
        elif balle.x + balle.rayon > self.rect.right:
            balle.x = self.rect.right - balle.rayon
            balle.vx = -abs(balle.vx)
            balle.rebondir_effet(1, 0)
            touche = True
        if self.mur_haut and balle.y - balle.rayon < self.rect.top:
            balle.y = self.rect.top + balle.rayon
            balle.vy = abs(balle.vy)
            balle.rebondir_effet(0, 1)
            touche = True
        if touche:
            corriger_angle(balle)
            self.evenements.enfiler(("mur", balle))

    def y_barriere(self, raquette):
        """But : ordonnée de la barrière (bouclier/filet) derrière une raquette."""
        if raquette.sens < 0:
            return self.rect.bottom - 12
        return self.rect.top + 12

    def _collision_barrieres(self, balle):
        """Bouclier (permanent) ou filet (un seul usage) derrière la raquette."""
        for raquette in self.raquettes:
            joueur = raquette.joueur
            if joueur is None or not (joueur.actif("bouclier") or joueur.filets > 0):
                continue
            y = self.y_barriere(raquette)
            if raquette.sens < 0 and balle.vy > 0 and balle.y + balle.rayon >= y:
                balle.y = y - balle.rayon
                balle.vy = -abs(balle.vy)
            elif raquette.sens > 0 and balle.vy < 0 and balle.y - balle.rayon <= y:
                balle.y = y + balle.rayon
                balle.vy = abs(balle.vy)
            else:
                continue
            balle.rebondir_effet(0, 1)
            if not joueur.actif("bouclier"):
                joueur.filets -= 1
                self.evenements.enfiler(("filet", joueur))
            else:
                self.evenements.enfiler(("mur", balle))

    def _raquette_rebond_client(self, cote):
        """
        But : raquette (pilotée en ligne) dont le joueur annonce lui-même les rebonds,
        du côté où la balle vient de sortir. Sortie : (Raquette ou None).
        """
        sens = -1 if cote == "bas" else 1
        for raquette in self.raquettes:
            if raquette.sens == sens and getattr(raquette, "rebond_client", False):
                return raquette
        return None

    def rebond_client(self, balle, raquette, x, y, vx, vy, avance=0.0):
        """
        But : appliquer un rebond annoncé par le joueur qui tient la raquette (jeu en
        ligne : son écran fait foi pour sa propre raquette, ce qui supprime le retard).
        Entrées : balle, raquette ; x, y, vx, vy (float) : balle juste après le rebond,
                  vue par le joueur ; avance (float) : temps écoulé depuis (s).
        Sortie : aucune.
        """
        balle.sursis = None
        joueur = raquette.joueur
        raquette.frappee()
        balle.proprietaire = joueur or balle.proprietaire
        self.evenements.enfiler(("raquette", balle, raquette))
        if joueur is not None and joueur.aimant_prises > 0:
            joueur.aimant_prises -= 1
            decalage = max(-1.0, min(1.0, (x - raquette.x) / max(1.0, raquette.largeur / 2)))
            balle.x = x
            balle.y = raquette.face_y() + raquette.sens * (balle.rayon + 0.5)
            balle.collee = True
            balle.raquette_collage = raquette
            balle.decalage_collage = decalage * raquette.largeur / 2
            balle.temps_collage = DUREE_AIMANT
            return
        balle.x, balle.y, balle.vx, balle.vy = x, y, vx, vy
        avance = max(0.0, min(0.2, avance)) * balle.facteur_vitesse()
        balle.x += vx * avance
        balle.y += vy * avance
        self._collision_murs(balle)

    def _collision_raquettes(self, balle):
        """
        But : rebond sur la raquette que la balle rejoint.
        Sortie : (bool) True si la balle vient d'être collée par l'aimant.
        """
        for raquette in self.raquettes:
            if balle.vy * raquette.sens >= 0:        # elle s'éloigne de cette raquette
                continue
            if getattr(raquette, "rebond_client", False):
                continue                             # c'est son joueur qui décide
            boite = raquette.obtenir_boite()
            if not disque_touche_boite(balle.x, balle.y, balle.rayon, boite):
                continue
            # La balle doit arriver par la face active (pas déjà passée derrière).
            if raquette.sens < 0 and balle.y > raquette.y + raquette.hauteur:
                continue
            if raquette.sens > 0 and balle.y < raquette.y:
                continue
            decalage = rebond_raquette(balle, boite, sens=raquette.sens)
            balle.y = raquette.face_y() + raquette.sens * (balle.rayon + 0.5)
            raquette.frappee()
            balle.proprietaire = raquette.joueur or balle.proprietaire
            self.evenements.enfiler(("raquette", balle, raquette))
            joueur = raquette.joueur
            if joueur is not None and joueur.aimant_prises > 0:
                joueur.aimant_prises -= 1
                balle.collee = True
                balle.raquette_collage = raquette
                balle.decalage_collage = decalage * raquette.largeur / 2
                balle.temps_collage = DUREE_AIMANT
                return True
            return False
        return False

    def _collision_briques(self, balle):
        """
        But : traiter les briques touchées : portail, traversée en feu, ou
        rebond sur la première brique solide.
        """
        for brique in self.briques:
            if brique.morte:
                continue                  # détruite pendant ce parcours
            boite = brique.obtenir_boite()
            if not disque_touche_boite(balle.x, balle.y, balle.rayon, boite):
                continue
            if not brique.solide:
                self._traverser_portail(balle, brique)
                continue
            joueur = balle.proprietaire
            if joueur is not None and joueur.bombe_armee:
                joueur.bombe_armee = False
                detruites = self.exploser_zone(brique.x + brique.largeur / 2,
                                               brique.y + brique.hauteur / 2, 2, joueur, 2)
                joueur.stats["bombe_max"] = max(joueur.stats["bombe_max"], detruites)
                rebondir_sur_boite(balle, boite)
                corriger_angle(balle)
                return
            if balle.en_feu():
                self.endommager(brique, joueur, puissance=1, feu=True, balle=balle)
                continue                              # le feu traverse
            rebondir_sur_boite(balle, boite)
            corriger_angle(balle)
            self.endommager(brique, joueur, balle=balle)
            return

    def _traverser_portail(self, balle, portail):
        """Téléporte la balle au portail jumeau en gardant sa vitesse."""
        jumeau = getattr(portail, "jumeau", None)
        if jumeau is None or balle.delai_portail > 0:
            return
        sens_x = 1 if balle.vx >= 0 else -1
        sens_y = 1 if balle.vy >= 0 else -1
        balle.x = jumeau.x + jumeau.largeur / 2 + sens_x * 2
        balle.y = jumeau.y + jumeau.hauteur / 2 + sens_y * (jumeau.hauteur / 2 + balle.rayon + 1)
        balle.delai_portail = 0.35
        balle.trainee.clear()
        self.evenements.enfiler(("portail", balle))

    # --- Dégâts et destructions -----------------------------------------------

    def endommager(self, brique, joueur, puissance=1, feu=False, balle=None):
        """
        But : frapper une brique ; si elle casse, la détruire (avec ses
        conséquences : explosion, capsule, régénération).
        Entrées : brique (Brique) ; joueur (Joueur ou None) : responsable ;
                  puissance (int) ; feu (bool) ; balle (Balle ou None).
        Sortie : (bool) True si la brique a été détruite.
        """
        if brique not in self.briques:
            return False
        if brique.frapper(puissance, feu):
            self.detruire(brique, joueur)
            return True
        self.evenements.enfiler(("brique_touchee", brique, balle))
        return False

    def detruire(self, brique, joueur):
        """
        But : retirer une brique cassée et déclencher ses effets.
        Entrées : brique (Brique) ; joueur (Joueur ou None). Sortie : aucune.
        """
        if not self.briques.supprimer(brique):
            return
        brique.morte = True
        self.evenements.enfiler(("brique_detruite", brique, joueur))
        self._lacher_capsule(brique, joueur)
        if brique.regenerante:
            self.regenerations.append([brique, DELAI_REGENERATION])
        if brique.explosive:
            cx = brique.x + brique.largeur / 2
            cy = brique.y + brique.hauteur / 2
            self.exploser_zone(cx, cy, 1, joueur, 1)

    def exploser_zone(self, cx, cy, cases, joueur, puissance):
        """
        But : endommager toutes les briques dans un carré de (2*cases+1)
        briques de côté autour d'un point (explosive : 3x3, bombe : 5x5).
        Entrées : cx, cy (float) ; cases (int) ; joueur ; puissance (int).
        Sortie : (int) nombre de briques détruites directement.
        """
        pas_x, pas_y = self.pas_grille()
        demi_l = pas_x * (cases + 0.5)
        demi_h = pas_y * (cases + 0.5)
        zone = (cx - demi_l, cy - demi_h, cx + demi_l, cy + demi_h)
        self.evenements.enfiler(("explosion", cx, cy, max(demi_l, demi_h) * 1.4))
        touchees = [b for b in self.briques
                    if b.solide and boites_se_touchent(zone, b.obtenir_boite())]
        detruites = 0
        for brique in touchees:
            if self.endommager(brique, joueur, puissance=puissance, feu=puissance >= 2):
                detruites += 1
        if self.boss is not None:
            self.boss.subir_explosion(zone, puissance, self)
        return detruites

    def _lacher_capsule(self, brique, joueur):
        """Tirage d'une capsule à la destruction d'une brique."""
        if self.chance_capsule <= 0 and not brique.capsule_garantie:
            return
        if not brique.capsule_garantie and random.random() >= self.chance_capsule:
            return
        code = tirer_effet(self.poids_capsules)
        if code is None:
            return
        sens = 1
        if joueur is not None and joueur.raquette is not None:
            sens = -joueur.raquette.sens
        capsule = Capsule(brique.x + brique.largeur / 2,
                          brique.y + brique.hauteur / 2, code, sens, joueur)
        self.capsules.ajouter_fin(capsule)

    def _regenerer(self, dt):
        """Les briques régénérantes reviennent si une sœur est encore en vie."""
        if not self.regenerations:
            return
        soeur_vivante = any(b.regenerante for b in self.briques)
        restantes = []
        for entree in self.regenerations:
            entree[1] -= dt
            if entree[1] > 0:
                restantes.append(entree)
            elif soeur_vivante:
                brique = entree[0]
                brique.vie = brique.vie_max
                brique.apparition = 0.0
                brique.delai_apparition = 0.0
                brique.flash = 1.0
                brique.morte = False
                self.briques.ajouter_fin(brique)
        if not soeur_vivante:
            restantes = []          # plus aucune sœur : elles ne reviendront pas
        self.regenerations = restantes

    # --- Capsules et projectiles ---------------------------------------------

    def _mettre_a_jour_capsules(self, dt):
        """Chute des capsules et ramassage par une raquette."""
        a_retirer = []
        for capsule in self.capsules:
            capsule.mettre_a_jour(dt)
            rect = capsule.rect()
            for raquette in self.raquettes:
                if rect.colliderect(raquette.rect()):
                    self.evenements.enfiler(("capsule", capsule, raquette.joueur))
                    a_retirer.append(capsule)
                    break
            else:
                if capsule.y > self.rect.bottom + 20 or capsule.y < self.rect.top - 20:
                    a_retirer.append(capsule)
        for capsule in a_retirer:
            self.capsules.supprimer(capsule)

    def _mettre_a_jour_lasers(self, dt):
        """Tir automatique des canons et impacts des lasers."""
        for raquette in self.raquettes:
            joueur = raquette.joueur
            if joueur is None or not joueur.actif("laser"):
                continue
            minuteur = self._minuteurs_laser.get(raquette, 0) - dt
            if minuteur <= 0:
                minuteur = CADENCE_LASER
                for cx in raquette.positions_canons():
                    y = raquette.face_y() + raquette.sens * 10
                    self.lasers.ajouter_fin(Laser(cx, y, raquette.sens, joueur))
                self.evenements.enfiler(("tir_laser", raquette))
            self._minuteurs_laser[raquette] = minuteur
        for laser in self.lasers:
            laser.mettre_a_jour(dt)
            boite = laser.boite()
            for brique in self.briques:
                if brique.solide and boites_se_touchent(boite, brique.obtenir_boite()):
                    if hasattr(brique, "revelee"):
                        brique.revelee = True
                    self.endommager(brique, laser.joueur)
                    laser.vivant = False
                    break
            if laser.vivant and self.boss is not None and self.boss.touche_boite(boite):
                self.boss.blesser(1, self)
                laser.vivant = False
            if not self.rect.inflate(0, 40).collidepoint(laser.x, laser.y):
                laser.vivant = False
        self.lasers.retirer_si(lambda l: not l.vivant)

    def _mettre_a_jour_tirs(self, dt):
        """Tirs du boss : étourdissent la raquette touchée."""
        for tir in self.tirs:
            tir.mettre_a_jour(dt)
            boite = tir.boite()
            for raquette in self.raquettes:
                if boites_se_touchent(boite, raquette.obtenir_boite()):
                    joueur = raquette.joueur
                    if joueur is not None and joueur.actif("bouclier"):
                        pass
                    else:
                        raquette.etourdie = 0.7
                        self.evenements.enfiler(("raquette_touchee", raquette))
                    tir.vivant = False
            if not self.rect.inflate(60, 60).collidepoint(tir.x, tir.y):
                tir.vivant = False
        self.tirs.retirer_si(lambda t: not t.vivant)

    def zone_rayon(self, raquette):
        """But : colonne lumineuse de la SUPERNOVA au-dessus d'une raquette."""
        largeur = 46
        if raquette.sens < 0:
            return pygame.Rect(int(raquette.x - largeur / 2), self.rect.top,
                               largeur, int(raquette.y - self.rect.top))
        bas = raquette.y + raquette.hauteur
        return pygame.Rect(int(raquette.x - largeur / 2), int(bas), largeur,
                           int(self.rect.bottom - bas))

    def _rayons_supernova(self, dt):
        """La SUPERNOVA balaye la colonne de la raquette toutes les 0,12 s."""
        for raquette in self.raquettes:
            joueur = raquette.joueur
            if joueur is None or joueur.supernova <= 0:
                continue
            minuteur = self._minuteurs_rayon.get(raquette, 0) - dt
            if minuteur <= 0:
                minuteur = 0.12
                zone = self.zone_rayon(raquette)
                boite = (zone.left, zone.top, zone.right, zone.bottom)
                for brique in [b for b in self.briques if b.solide]:
                    if boites_se_touchent(boite, brique.obtenir_boite()):
                        self.endommager(brique, joueur, feu=True)
                if self.boss is not None and self.boss.touche_boite(boite):
                    self.boss.blesser(1, self)
            self._minuteurs_rayon[raquette] = minuteur

    # --- Dessin ----------------------------------------------------------------

    def dessiner(self, image):
        """
        But : dessiner tout le terrain dans l'ordre : fond, cadre, barrières,
        briques, boss, capsules, projectiles, raquettes, balles, rayons.
        Entrée : image (Surface). Sortie : aucune.
        """
        couleur_bord = self.couleur_bord
        for calque in self.cadre:
            image.blit(calque, self.rect.topleft)
        lueur = halo_rect(self.rect.w, self.rect.h + (0 if not self.mur_haut else 40),
                          attenuer(couleur_bord, 0.6), rayon=10, epaisseur=3)
        ajouter_lueur(image, lueur, (self.rect.x - 20, self.rect.y - 20))
        bord = config.EPAISSEUR_BORD
        gauche = self.rect.left - bord
        if self.mur_haut:
            pygame.draw.rect(image, couleur_bord, (gauche, self.rect.top - bord,
                                                   self.rect.w + 2 * bord, bord))
        pygame.draw.rect(image, couleur_bord, (gauche, self.rect.top, bord, self.rect.h))
        pygame.draw.rect(image, couleur_bord, (self.rect.right, self.rect.top, bord,
                                               self.rect.h))
        self._dessiner_barrieres(image)
        for brique in self.briques:
            brique.dessiner(image, self.temps)
        if self.boss is not None:
            self.boss.dessiner(image, self)
        for capsule in self.capsules:
            capsule.dessiner(image)
        for laser in self.lasers:
            laser.dessiner(image)
        for tir in self.tirs:
            tir.dessiner(image)
        self._dessiner_rayons(image)
        for raquette in self.raquettes:
            raquette.dessiner(image, self.temps)
        for balle in self.balles:
            balle.dessiner(image, self.temps)
        self._dessiner_brouillard(image)

    def _dessiner_barrieres(self, image):
        """Bouclier (épais, pulsant) ou filet (pointillés) derrière les raquettes."""
        for raquette in self.raquettes:
            joueur = raquette.joueur
            if joueur is None:
                continue
            y = self.y_barriere(raquette)
            if joueur.actif("bouclier"):
                pulse = 0.6 + 0.4 * math.sin(self.temps * 10)
                couleur = attenuer(joueur.couleur_bord, pulse)
                lueur = halo_rect(self.rect.w, 4, couleur, rayon=6)
                image.blit(lueur, (self.rect.x - 12, y - 14),
                           special_flags=pygame.BLEND_RGB_ADD)
                image.fill(config.BLANC, (self.rect.x, y - 1, self.rect.w, 3))
            elif joueur.filets > 0:
                for x in range(self.rect.left, self.rect.right, 16):
                    image.fill(config.VERT, (x, y - 1, 9, 2))

    def _dessiner_rayons(self, image):
        """Colonnes de lumière de la SUPERNOVA."""
        for raquette in self.raquettes:
            joueur = raquette.joueur
            if joueur is None or joueur.supernova <= 0:
                continue
            zone = self.zone_rayon(raquette)
            pulse = 0.7 + 0.3 * math.sin(self.temps * 30)
            lueur = halo_rect(zone.w, zone.h, attenuer(joueur.couleur_bord, pulse),
                              rayon=10, epaisseur=zone.w)
            image.blit(lueur, (zone.x - 20, zone.y - 20),
                       special_flags=pygame.BLEND_RGB_ADD)
            coeur = zone.inflate(-zone.w * 0.6, 0)
            image.fill(attenuer(config.BLANC, pulse), coeur,
                       special_flags=pygame.BLEND_RGB_ADD)

    def zone_joueur(self, joueur):
        """
        But : partie du terrain « appartenant » à un joueur (moitié en Duel,
        tout le terrain sinon) : là où son brouillard s'applique.
        Entrée : joueur (Joueur). Sortie : (pygame.Rect).
        """
        sens_differents = len({r.sens for r in self.raquettes}) > 1
        if not sens_differents or joueur.raquette is None:
            return self.rect
        if joueur.raquette.sens < 0:
            return pygame.Rect(self.rect.x, self.rect.centery, self.rect.w, self.rect.h // 2)
        return pygame.Rect(self.rect.x, self.rect.y, self.rect.w, self.rect.h // 2)

    def _dessiner_brouillard(self, image):
        """Malus BROUILLARD : tout est noir sauf autour des balles et de la raquette."""
        for joueur in self.joueurs():
            if not joueur.actif("brouillard"):
                continue
            zone = self.zone_joueur(joueur)
            voile = pygame.Surface(zone.size, pygame.SRCALPHA)
            voile.fill((4, 0, 12, 238))
            trous = [(b.x, b.y, 95) for b in self.balles]
            trous.append((joueur.raquette.x, joueur.raquette.y, 80))
            for x, y, rayon in trous:
                for k, alpha in ((rayon, 150), (rayon * 0.7, 60), (rayon * 0.45, 0)):
                    pygame.draw.circle(voile, (4, 0, 12, alpha),
                                       (int(x - zone.x), int(y - zone.y)), int(k))
            image.blit(voile, zone.topleft)
