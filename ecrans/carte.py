# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Carte du monde de la Campagne (2.0), façon jeu de plateforme : un chemin
    néon qui serpente à travers les trois mondes (SUNSET GRID, NEON CITY,
    CYBER CORE), un nœud par niveau avec ses étoiles, les boss en grand, et
    une petite raquette qui se déplace de nœud en nœud. La caméra suit le
    niveau choisi. Remplace l'ancienne grille de sélection des niveaux.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 25/10/2026
"""

import math
import random

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from moteur.rendu import attenuer, halo_rect, melanger
from jeu.niveau import charger_campagne
from jeu.modes.campagne import nombre_etoiles, temps_cible
from ecrans.base import EcranBase
from ecrans.hud import dessiner_etoiles, panneau

NOMS_MONDES = {1: "SUNSET GRID", 2: "NEON CITY", 3: "CYBER CORE"}
COULEURS_MONDES = {1: config.ROSE, 2: config.CYAN, 3: config.VERT}
CIELS = {1: ((30, 5, 50), (120, 30, 90)), 2: ((5, 10, 40), (30, 40, 110)),
         3: ((0, 20, 20), (10, 70, 60))}
ICONES_BOSS = {"sunset": "boss_sunset", "gridlock": "boss_gridlock", "core": "boss_core"}
PAS = 290                       # écart horizontal entre deux niveaux
ECART_MONDE = 140               # espace en plus entre deux mondes
MARGE = 330
HORIZON = 470
VERROU = ["..XXX..", ".X...X.", ".X...X.", "XXXXXXX", "XXX.XXX", "XXX.XXX", "XXXXXXX"]


def positions_noeuds(niveaux):
    """
    But : position (x, y) de chaque niveau sur la carte (coordonnées du monde).
    Entrée : niveaux (list de Niveau). Sortie : (list de (float, float)).
    """
    positions = []
    x = MARGE
    for i, niveau in enumerate(niveaux):
        if i and niveau.monde != niveaux[i - 1].monde:
            x += ECART_MONDE
        y = 360 + math.sin(i * 1.25 + 0.6) * 95 - (40 if niveau.boss else 0)
        positions.append((x, y))
        x += PAS
    return positions


def courbe(points, pas=14):
    """But : points d'une courbe lisse (Catmull-Rom) passant par `points`."""
    if len(points) < 2:
        return list(points)
    etendus = [points[0]] + list(points) + [points[-1]]
    resultat = []
    for i in range(1, len(etendus) - 2):
        p0, p1, p2, p3 = etendus[i - 1:i + 3]
        n = max(2, int(math.dist(p1, p2) / pas))
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            resultat.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t
                                         + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                         + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3)
                                  for j in range(2)))
    resultat.append(points[-1])
    return resultat


class EcranCarte(EcranBase):
    """
    Attributs : code ("campagne"/"coop"), niveaux, positions, chemin (points
    de la courbe), debloque (int), indice (int), camera (float),
    marqueur (float : position du marqueur, en indice de niveau), etoiles (dict).
    """

    def __init__(self, app, code):
        super().__init__(app)
        self.code = code
        self.niveaux = charger_campagne()
        self.positions = positions_noeuds(self.niveaux)
        self.debloque = min(app.niveau_debloque(code), len(self.niveaux) - 1)
        self.indice = self.debloque
        self.marqueur = float(self.indice)
        self.largeur_monde = self.positions[-1][0] + MARGE
        self.camera = self._camera_cible()
        self.etoiles = {int(k): int(v) for k, v in
                        app.donnees.get("etoiles", {}).get(code, {}).items()}
        self.segments = [courbe(self.positions[i:i + 2]) if i + 1 < len(self.positions) else []
                         for i in range(len(self.positions))]
        self.bornes = self._bornes_mondes()
        self.decors = self._creer_decors()
        self.zones = []

    # --- Décor -----------------------------------------------------------------------

    def _bornes_mondes(self):
        """But : {monde: (x_debut, x_fin)} en coordonnées du monde."""
        bornes = {}
        for (x, _), niveau in zip(self.positions, self.niveaux):
            debut, fin = bornes.get(niveau.monde, (x, x))
            bornes[niveau.monde] = (min(debut, x), max(fin, x))
        resultat = {}
        mondes = sorted(bornes)
        for k, monde in enumerate(mondes):
            debut = 0 if k == 0 else (bornes[mondes[k - 1]][1] + bornes[monde][0]) / 2
            fin = self.largeur_monde if k == len(mondes) - 1 else \
                (bornes[monde][1] + bornes[mondes[k + 1]][0]) / 2
            resultat[monde] = (debut, fin)
        return resultat

    def _creer_decors(self):
        """But : décor fixe de toute la carte (ciel, silhouettes), dessiné une fois."""
        surface = pygame.Surface((int(self.largeur_monde), config.HAUTEUR))
        bornes = self.bornes
        hasard = random.Random(7)
        for monde, (debut, fin) in bornes.items():
            haut, bas = CIELS.get(monde, CIELS[1])
            for y in range(HORIZON):
                pygame.draw.line(surface, melanger(haut, bas, y / HORIZON), (debut, y), (fin, y))
            surface.fill((8, 2, 20), (debut, HORIZON, fin - debut, config.HAUTEUR - HORIZON))
        mondes = sorted(bornes)
        for gauche, droite in zip(mondes, mondes[1:]):        # ciels fondus entre deux mondes
            frontiere = bornes[droite][0]
            for dx in range(-120, 120, 2):
                t = (dx + 120) / 240
                for y in range(0, HORIZON, 2):
                    ciel_g = melanger(*CIELS.get(gauche, CIELS[1]), y / HORIZON)
                    ciel_d = melanger(*CIELS.get(droite, CIELS[1]), y / HORIZON)
                    surface.fill(melanger(ciel_g, ciel_d, t), (frontiere + dx, y, 2, 2))
        for monde, (debut, fin) in bornes.items():
            couleur = COULEURS_MONDES.get(monde, config.CYAN)
            sol_debut, sol_fin = debut, fin
            if monde != mondes[0]:
                debut += 120
            if monde != mondes[-1]:
                fin -= 120
            for _ in range(int((fin - debut) / 9)):         # étoiles du ciel
                surface.fill(attenuer(config.BLANC, hasard.uniform(0.2, 0.7)),
                             (hasard.uniform(debut, fin), hasard.uniform(0, HORIZON * 0.6), 2, 2))
            if monde == 1:                                  # soleil rayé et montagnes
                cx = (debut + fin) / 2
                for y in range(-110, 110):
                    if y > 10 and (y // 9) % 2:
                        continue
                    demi = math.sqrt(max(0, 110 ** 2 - y * y))
                    pygame.draw.line(surface, melanger((255, 220, 80), (255, 60, 150), (y + 110) / 220),
                                     (cx - demi, HORIZON - 120 + y), (cx + demi, HORIZON - 120 + y))
                x = debut
                while x < fin:
                    largeur = hasard.uniform(120, 260)
                    hauteur = hasard.uniform(60, 150)
                    pygame.draw.polygon(surface, (40, 10, 60),
                                        [(x, HORIZON), (x + largeur / 2, HORIZON - hauteur),
                                         (x + largeur, HORIZON)])
                    pygame.draw.lines(surface, attenuer(couleur, 0.6), False,
                                      [(x, HORIZON), (x + largeur / 2, HORIZON - hauteur),
                                       (x + largeur, HORIZON)], 2)
                    x += largeur * 0.7
            elif monde == 2:                                # gratte-ciel aux fenêtres allumées
                x = debut
                while x < fin:
                    largeur = hasard.uniform(50, 110)
                    hauteur = hasard.uniform(110, 300)
                    immeuble = pygame.Rect(x, HORIZON - hauteur, largeur, hauteur)
                    surface.fill((12, 16, 45), immeuble)
                    pygame.draw.rect(surface, attenuer(couleur, 0.45), immeuble, 1)
                    for fy in range(immeuble.y + 10, HORIZON - 10, 16):
                        for fx in range(immeuble.x + 8, immeuble.right - 8, 14):
                            if hasard.random() < 0.35:
                                surface.fill(hasard.choice(((255, 220, 120), (90, 230, 255),
                                                            (255, 90, 200))), (fx, fy, 5, 7))
                    x += largeur + hasard.uniform(4, 30)
            else:                                           # tours de circuit et hexagones
                for _ in range(int((fin - debut) / 70)):
                    cx, cy = hasard.uniform(debut, fin), hasard.uniform(80, HORIZON - 60)
                    r = hasard.uniform(14, 40)
                    pygame.draw.polygon(surface, attenuer(couleur, 0.35),
                                        [(cx + r * math.cos(a * math.pi / 3),
                                          cy + r * math.sin(a * math.pi / 3)) for a in range(6)], 1)
                x = debut
                while x < fin:
                    largeur, hauteur = hasard.uniform(30, 70), hasard.uniform(80, 240)
                    tour = pygame.Rect(x, HORIZON - hauteur, largeur, hauteur)
                    surface.fill((5, 30, 25), tour)
                    pygame.draw.rect(surface, attenuer(couleur, 0.5), tour, 1)
                    pygame.draw.line(surface, attenuer(couleur, 0.7), tour.midtop,
                                     (tour.centerx, tour.y - 20), 2)
                    surface.fill(couleur, (tour.centerx - 2, tour.y - 24, 4, 4))
                    x += largeur + hasard.uniform(30, 90)
            pygame.draw.line(surface, couleur, (sol_debut, HORIZON), (sol_fin, HORIZON), 2)
            for k in range(1, 9):                           # sol en perspective
                y = HORIZON + (config.HAUTEUR - HORIZON) * (k / 8) ** 1.7
                pygame.draw.line(surface, attenuer(couleur, 0.35), (sol_debut, y), (sol_fin, y))
        return surface

    def _dessiner_sol(self, image):
        """Lignes de fuite du sol (elles suivent la caméra)."""
        for k in range(-20, 21):
            x_bas = config.LARGEUR / 2 + k * 160 - (self.camera % 160)
            monde = self._monde_a(self.camera + x_bas)
            couleur = attenuer(COULEURS_MONDES.get(monde, config.CYAN), 0.3)
            pygame.draw.line(image, couleur, (config.LARGEUR / 2 + (x_bas - config.LARGEUR / 2) * 0.25,
                                              HORIZON), (x_bas, config.HAUTEUR))

    def _monde_a(self, x):
        for monde, (debut, fin) in self.bornes.items():
            if debut <= x <= fin:
                return monde
        return 1

    # --- Logique --------------------------------------------------------------------------

    def _camera_cible(self):
        x = self.positions[int(round(self.marqueur))][0] if hasattr(self, "marqueur") else 0
        x = self._position_marqueur()[0] if hasattr(self, "marqueur") else x
        return max(0.0, min(self.largeur_monde - config.LARGEUR, x - config.LARGEUR / 2))

    def _position_marqueur(self):
        """But : position (monde) du marqueur, sur la courbe entre deux niveaux."""
        i = int(math.floor(self.marqueur))
        t = self.marqueur - i
        if t < 1e-3 or i + 1 >= len(self.positions):
            return self.positions[min(i, len(self.positions) - 1)]
        points = self.segments[i]
        return points[min(len(points) - 1, int(t * (len(points) - 1)))]

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        entrees = self.app.entrees
        ancien = self.indice
        if entrees.vient_d_appuyer("gauche") or entrees.vient_d_appuyer("haut"):
            self.indice = max(0, self.indice - 1)
        if entrees.vient_d_appuyer("droite") or entrees.vient_d_appuyer("bas"):
            if self.indice + 1 <= self.debloque:
                self.indice += 1
            elif self.indice + 1 < len(self.niveaux):
                self.app.audio.jouer("metal")
        if entrees.souris_bougee or 1 in entrees.clics:
            for i, zone in enumerate(self.zones):
                if zone.collidepoint(entrees.souris) and i <= self.debloque:
                    self.indice = i
        if self.indice != ancien:
            self.app.audio.jouer("menu_nav")
            self.app.fond.changer_monde(self.niveaux[self.indice].monde)
        # Le marqueur glisse le long du chemin, la caméra le suit.
        ecart = self.indice - self.marqueur
        self.marqueur += max(-dt * 4, min(dt * 4, ecart)) if abs(ecart) > 0.01 else ecart
        self.camera += (self._camera_cible() - self.camera) * min(1.0, dt * 5)
        clic = 1 in entrees.clics and any(z.collidepoint(entrees.souris)
                                          for z in self.zones[:self.debloque + 1])
        if entrees.vient_d_appuyer("valider") or clic:
            from ecrans.partie import EcranPartie
            from ecrans.modes import fabrique_mode
            self.app.audio.jouer("menu_ok")
            self.app.remplacer(EcranPartie(self.app, fabrique_mode(self.code, self.indice)))
        elif entrees.vient_d_appuyer("retour"):
            from ecrans.modes import EcranModes
            self.app.remplacer(EcranModes(self.app))

    # --- Dessin -----------------------------------------------------------------------------

    def _ecran(self, point):
        return (point[0] - self.camera, point[1])

    def _dessiner_chemin(self, image):
        for i, points in enumerate(self.segments):
            if not points:
                continue
            ouvert = i + 1 <= self.debloque
            couleur = COULEURS_MONDES.get(self.niveaux[i + 1].monde, config.CYAN)
            ecran = [self._ecran(p) for p in points]
            if ecran[-1][0] < -50 or ecran[0][0] > config.LARGEUR + 50:
                continue
            pygame.draw.lines(image, (20, 6, 40), False, ecran, 12)
            if ouvert:
                pygame.draw.lines(image, attenuer(couleur, 0.5), False, ecran, 6)
                for k in range(len(ecran)):              # points lumineux qui avancent
                    if (k - int(self.temps * 12)) % 6 == 0:
                        pygame.draw.circle(image, config.BLANC, ecran[k], 3)
            else:
                for k in range(0, len(ecran), 3):
                    pygame.draw.circle(image, (70, 50, 100), ecran[k], 3)

    def _dessiner_noeud(self, image, i):
        niveau = self.niveaux[i]
        x, y = self._ecran(self.positions[i])
        rayon = 46 if niveau.boss else 34
        zone = pygame.Rect(0, 0, rayon * 2 + 10, rayon * 2 + 10)
        zone.center = (int(x), int(y))
        self.zones.append(zone)
        if x < -80 or x > config.LARGEUR + 80:
            return
        ouvert = i <= self.debloque
        choisi = i == self.indice
        couleur = COULEURS_MONDES.get(niveau.monde, config.CYAN) if ouvert else (80, 60, 110)
        if niveau.boss and ouvert:
            couleur = config.ROUGE
        if choisi:
            pulse = 1 + 0.08 * math.sin(self.temps * 6)
            lueur = halo_rect(int(rayon * 2 * pulse), int(rayon * 2 * pulse), couleur, rayon=rayon,
                              epaisseur=6)
            image.blit(lueur, (x - rayon * pulse - 16, y - rayon * pulse - 16),
                       special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.circle(image, (14, 2, 32), (int(x), int(y)), rayon)
        pygame.draw.circle(image, couleur, (int(x), int(y)), rayon, 4 if choisi else 3)
        pygame.draw.circle(image, attenuer(couleur, 0.4), (int(x), int(y)), rayon - 8, 1)
        if not ouvert:
            from moteur.icones import dessiner_icone
            dessiner_icone(image, "verrou", (int(x), int(y)), couleur, 3, defaut=VERROU)
        elif niveau.boss:
            from moteur.icones import dessiner_icone
            dessiner_icone(image, ICONES_BOSS.get(niveau.boss, "x"), (int(x), int(y) - 4), couleur, 4,
                           lueur=choisi, defaut=VERROU)
        else:
            dessiner_texte(image, str(i + 1), x, y, 4, couleur, lueur=choisi)
        if ouvert and i <= self.debloque and (i < self.debloque or self.etoiles.get(i)):
            dessiner_etoiles(image, 0, (x, y + rayon + 18), 8, masque=self.etoiles.get(i, 0))

    def _dessiner_marqueur(self, image):
        x, y = self._ecran(self._position_marqueur())
        rayon = 46 if self.niveaux[int(round(self.marqueur))].boss else 34
        saut = abs(math.sin(self.temps * 4)) * 10
        haut = y - rayon - 30 - saut
        couleur = config.CYAN
        raquette = pygame.Rect(0, 0, 54, 10)
        raquette.center = (int(x), int(haut + 16))
        pygame.draw.rect(image, couleur, raquette, border_radius=4)
        pygame.draw.rect(image, config.BLANC, raquette, 1, border_radius=4)
        pygame.draw.circle(image, config.BLANC, (int(x), int(haut - 4 - saut * 0.6)), 6)
        pygame.draw.circle(image, couleur, (int(x), int(haut - 4 - saut * 0.6)), 6, 1)

    def _dessiner_titres_mondes(self, image):
        for monde, (debut, fin) in self.bornes.items():
            cx = (debut + fin) / 2 - self.camera
            if -400 < cx < config.LARGEUR + 400:
                couleur = COULEURS_MONDES.get(monde, config.BLANC)
                dessiner_texte(image, f"MONDE {monde}", cx, 120, 2, attenuer(couleur, 0.8), lueur=False)
                dessiner_texte(image, NOMS_MONDES.get(monde, ""), cx, 148, 4, couleur)

    def _dessiner_infos(self, image):
        niveau = self.niveaux[self.indice]
        cadre = pygame.Rect(0, 0, 900, 120)
        cadre.midbottom = (config.LARGEUR / 2, config.HAUTEUR - 50)
        couleur = config.ROUGE if niveau.boss else COULEURS_MONDES.get(niveau.monde, config.CYAN)
        panneau(image, cadre, couleur)
        nom = niveau.nom.split("  ")[-1] if "  " in niveau.nom else niveau.nom
        entete = f"BOSS  {niveau.boss.upper()}" if niveau.boss else f"NIVEAU {self.indice + 1}  {nom}"
        dessiner_texte(image, entete, cadre.x + 28, cadre.y + 30, 3, couleur, ancrage="gauche")
        masque = self.etoiles.get(self.indice, 0)
        criteres = ["FINIR LE NIVEAU", "SANS PERDRE DE VIE",
                    f"EN MOINS DE {temps_cible(niveau)} S"]
        for k, texte in enumerate(criteres):
            x = cadre.x + (46, 330, 630)[k]
            dessiner_etoiles(image, 0, (x, cadre.y + 80), 9, total=1, masque=(masque >> k) & 1)
            dessiner_texte(image, texte, x + 18, cadre.y + 80, 2,
                           config.OR if (masque >> k) & 1 else (150, 120, 190),
                           ancrage="gauche", lueur=False)

    def dessiner(self, image):
        source = pygame.Rect(int(self.camera), 0, config.LARGEUR, config.HAUTEUR)
        image.blit(self.decors, (0, 0), source)
        self._dessiner_sol(image)
        self._dessiner_titres_mondes(image)
        self.zones = []
        self._dessiner_chemin(image)
        for i in range(len(self.niveaux)):
            self._dessiner_noeud(image, i)
        self._dessiner_marqueur(image)
        titre = "CAMPAGNE" if self.code == "campagne" else "COOP"
        dessiner_texte(image, titre, 30, 40, 4, config.CYAN, ancrage="gauche")
        total = sum(nombre_etoiles(m) for m in self.etoiles.values())
        zone = dessiner_texte(image, f"{total} / {3 * len(self.niveaux)}", config.LARGEUR - 30, 40,
                              3, config.OR, ancrage="droite")
        dessiner_etoiles(image, 1, (zone.x - 22, zone.centery), 12, total=1)
        self._dessiner_infos(image)
        if math.sin(self.temps * 5) > -0.4:
            dessiner_texte(image, "FLECHES : CHOISIR    ENTREE : JOUER    ECHAP : RETOUR",
                           config.LARGEUR / 2, config.HAUTEUR - 22, 2, (150, 120, 200), lueur=False)
