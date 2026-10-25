# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Choix du mode de jeu : six cartes animées sur deux rangées (SOLO :
    Campagne, Arcade, Hardcore ; 2 JOUEURS : Coop, Duel, Course), et le
    bandeau du DEFI DU JOUR en dessous.
    Navigation aux flèches ou à la souris, Entrée ou clic pour choisir.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Aperçu animé de chaque mode sur sa carte.
"""

import math

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from moteur.rendu import halo_rect, attenuer, melanger
from ecrans.base import EcranBase

CARTES = [
    ("campagne", "CAMPAGNE", config.CYAN,
     ["12 NIVEAUX, 3 MONDES", "3 BOSS A PHASES", "PROGRESSION SAUVEE"]),
    ("arcade", "ARCADE", config.ROSE,
     ["LE MUR DESCEND SANS FIN", "TENEZ LE PLUS LONGTEMPS", "SCORE ET VAGUES"]),
    ("hardcore", "HARDCORE", config.ROUGE,
     ["1 VIE, BALLE +30 %", "MALUS SEULEMENT", "SCORE x2"]),
    ("coop", "COOP", config.VERT,
     ["2 RAQUETTES EN BAS", "VIES ET SCORE COMMUNS", "J1 Q D Z   J2 ← → ↑"]),
    ("duel", "DUEL", config.VIOLET,
     ["J1 EN BAS, J2 EN HAUT", "MALUS POUR L'AUTRE", "PREMIER A 7 POINTS"]),
    ("course", "COURSE", config.AMBRE,
     ["ECRAN PARTAGE", "COMBO 5 = ATTAQUE", "2 MANCHES GAGNANTES"]),
]
LARGEUR_CARTE = 360
HAUTEUR_CARTE = 210


def fabrique_mode(code, indice=0):
    """
    But : fonction qui crée le mode demandé (pour EcranPartie).
    Entrées : code (str) ; indice (int) : niveau de départ.
    Sortie : (fonction(app, effets) -> ModeDeJeu).
    """
    def fabrique(app, effets):
        from jeu.modes.campagne import ModeCampagne, ModeCoop
        from jeu.modes.arcade import ModeArcade
        from jeu.modes.duel import ModeDuel
        from jeu.modes.course import ModeCourse
        if code == "campagne":
            return ModeCampagne(app, effets, indice)
        if code == "hardcore":
            return ModeCampagne(app, effets, indice, hardcore=True)
        if code == "coop":
            return ModeCoop(app, effets, indice)
        if code == "arcade":
            return ModeArcade(app, effets)
        if code == "defi":
            from jeu.modes.defi import ModeDefi
            return ModeDefi(app, effets)
        if code == "semaine":
            from jeu.modes.defi import ModeDefiSemaine
            return ModeDefiSemaine(app, effets)
        if code == "duel":
            return ModeDuel(app, effets)
        return ModeCourse(app, effets)
    return fabrique


class EcranModes(EcranBase):
    """Attributs : indice (int) : carte sélectionnée, zones (list de Rect)."""

    def __init__(self, app):
        super().__init__(app)
        self.indice = 0
        self.zones = []

    def entrer(self):
        self.app.fond.changer_monde(1)

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        entrees = self.app.entrees
        ancien = self.indice
        # 0-5 : cartes ; 6 : défi du jour ; 7 : défi de la semaine.
        if entrees.vient_d_appuyer("gauche"):
            self.indice = (self.indice - 1) % 8
        if entrees.vient_d_appuyer("droite"):
            self.indice = (self.indice + 1) % 8
        if entrees.vient_d_appuyer("bas"):
            self.indice = {0: 3, 1: 4, 2: 5, 3: 6, 4: 6, 5: 7, 6: 0, 7: 2}[self.indice]
        if entrees.vient_d_appuyer("haut"):
            self.indice = {0: 6, 1: 6, 2: 7, 3: 0, 4: 1, 5: 2, 6: 3, 7: 5}[self.indice]
        if entrees.souris_bougee:
            for i, zone in enumerate(self.zones):
                if zone.collidepoint(entrees.souris):
                    self.indice = i
        if self.indice != ancien:
            self.app.audio.jouer("menu_nav")
        clic = 1 in entrees.clics and any(z.collidepoint(entrees.souris) for z in self.zones)
        if entrees.vient_d_appuyer("valider") or clic:
            self.app.audio.jouer("menu_ok")
            self.choisir(CARTES[self.indice][0] if self.indice < 6
                         else ("defi", "semaine")[self.indice - 6])
        elif entrees.vient_d_appuyer("retour"):
            from ecrans.titre import EcranTitre
            self.app.remplacer(EcranTitre(self.app))

    def choisir(self, code):
        """But : lancer le mode, ou passer par la sélection de niveau."""
        from ecrans.partie import EcranPartie
        if code in ("campagne", "coop"):
            from ecrans.carte import EcranCarte
            self.app.remplacer(EcranCarte(self.app, code))
        else:
            self.app.remplacer(EcranPartie(self.app, fabrique_mode(code)))

    def dessiner(self, image):
        self.app.fond.dessiner(image)
        voile = pygame.Surface(image.get_size())
        voile.fill((8, 0, 20))
        voile.set_alpha(120)
        image.blit(voile, (0, 0))
        dessiner_texte(image, "CHOIX DU MODE", config.LARGEUR / 2, 60, 6, config.CYAN)
        self.zones = []
        for i, (code, titre, couleur, lignes) in enumerate(CARTES):
            rangee, colonne = divmod(i, 3)
            cx = config.LARGEUR / 2 + (colonne - 1) * (LARGEUR_CARTE + 30)
            cy = 222 + rangee * (HAUTEUR_CARTE + 40)
            if colonne == 0:
                dessiner_texte(image, "SOLO" if rangee == 0 else "2 JOUEURS",
                               config.LARGEUR / 2, cy - HAUTEUR_CARTE / 2 - 22, 2,
                               (170, 140, 220), lueur=False)
            choisie = i == self.indice
            self.dessiner_carte(image, cx, cy, code, titre, couleur, lignes, choisie)
        self.dessiner_defi(image, "defi", self.indice == 6)
        self.dessiner_defi(image, "semaine", self.indice == 7)
        dessiner_texte(image, "FLECHES : CHOISIR    ENTREE : JOUER    ECHAP : RETOUR",
                       config.LARGEUR / 2, config.HAUTEUR - 26, 2, (150, 120, 200), lueur=False)

    def dessiner_carte(self, image, cx, cy, code, titre, couleur, lignes, choisie):
        """But : une carte de mode (agrandie et lumineuse si sélectionnée)."""
        echelle = 1.06 + 0.02 * math.sin(self.temps * 6) if choisie else 1.0
        rect = pygame.Rect(0, 0, int(LARGEUR_CARTE * echelle), int(HAUTEUR_CARTE * echelle))
        rect.center = (int(cx), int(cy))
        self.zones.append(rect)
        fond = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(fond, (*melanger((12, 0, 30), couleur, 0.12 if choisie else 0.04), 225),
                         fond.get_rect(), border_radius=10)    # coins arrondis comme le cadre
        image.blit(fond, rect.topleft)
        if choisie:
            lueur = halo_rect(rect.w, rect.h, attenuer(couleur, 0.9), rayon=12, epaisseur=4)
            image.blit(lueur, (rect.x - 24, rect.y - 24), special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.rect(image, couleur if choisie else attenuer(couleur, 0.5), rect,
                         3 if choisie else 2, border_radius=10)
        dessiner_texte(image, titre, rect.centerx, rect.y + 40, 5,
                       couleur if choisie else attenuer(couleur, 0.7), lueur=choisie)
        self.dessiner_icone(image, code, rect.centerx, rect.y + 92, couleur)
        for k, ligne in enumerate(lignes):
            dessiner_texte(image, ligne, rect.centerx, rect.y + 132 + k * 24, 2,
                           config.BLANC if choisie else (150, 130, 190), lueur=False)
        record = self.app.meilleur_score(code)
        if record and code not in ("duel", "course"):
            dessiner_texte(image, f"RECORD {record}", rect.centerx, rect.bottom - 16, 2,
                           config.AMBRE, lueur=False)

    def dessiner_defi(self, image, code, choisi):
        """
        But : bandeau d'un défi : titre (date ou semaine), règle(s) du jour, série et
        record de ce PC. Entrées : image ; code ("defi" ou "semaine") ; choisi (bool).
        """
        from jeu.modes import defi as d
        if code == "defi":
            jour = d.jour_du_defi()
            modificateurs = [d.defi_pour(jour)[1]]
            titre = "DEFI DU " + "/".join(reversed(jour.split("-")[1:]))
            couleur, periode, unite = config.AMBRE, "jour", "J"
        else:
            jour = d.semaine_du_defi()
            modificateurs = d.defi_semaine_pour(jour)[1]
            titre = "SEMAINE " + jour.split("-W")[-1]
            couleur, periode, unite = config.ROSE, "semaine", "S"
        largeur = (LARGEUR_CARTE * 3 + 60) // 2 - 10
        echelle = 1.03 + 0.01 * math.sin(self.temps * 6) if choisi else 1.0
        rect = pygame.Rect(0, 0, int(largeur * echelle), int(70 * echelle))
        decalage = largeur // 2 + 10
        rect.center = (config.LARGEUR // 2 + (-decalage if code == "defi" else decalage), 622)
        self.zones.append(rect)
        fond = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(fond, (*melanger((12, 0, 30), couleur, 0.14 if choisi else 0.05), 225),
                         fond.get_rect(), border_radius=10)
        image.blit(fond, rect.topleft)
        if choisi:
            lueur = halo_rect(rect.w, rect.h, attenuer(couleur, 0.9), rayon=12, epaisseur=4)
            image.blit(lueur, (rect.x - 24, rect.y - 24), special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.rect(image, couleur if choisi else attenuer(couleur, 0.5), rect,
                         3 if choisi else 2, border_radius=10)
        dessiner_texte(image, titre, rect.x + 20, rect.centery - 14, 3,
                       couleur if choisi else attenuer(couleur, 0.75), ancrage="gauche",
                       lueur=choisi)
        regles = " + ".join(m[1] for m in modificateurs)
        dessiner_texte(image, regles, rect.x + 20, rect.centery + 16, 2,
                       config.BLANC if choisi else (150, 130, 190), ancrage="gauche", lueur=False)
        record = d.record_du_jour(self.app, jour, code)
        serie = d.serie_locale(self.app, periode)
        infos = (f"SERIE {serie} {unite}  " if serie else "") + \
            (f"RECORD {record}" if record else "A JOUER !")
        # Sur la ligne du bas s'il y a la place à côté des règles, sinon sur celle du titre.
        en_bas = (len(regles) + len(infos)) * 12 + 70 <= rect.w
        dessiner_texte(image, infos, rect.right - 18, rect.centery + (16 if en_bas else -14), 2,
                       couleur, ancrage="droite", lueur=False)

    def dessiner_icone(self, image, code, cx, cy, couleur):
        """But : petit pictogramme du mode (raquettes, briques, balle)."""
        t = self.temps
        def raquette(x, y):
            pygame.draw.rect(image, couleur, (x - 22, y - 3, 44, 6), border_radius=3)
        def brique(x, y, c=couleur):
            pygame.draw.rect(image, c, (x - 12, y - 4, 24, 8), 2, border_radius=2)
        balle_x = cx + math.sin(t * 2.5) * 40
        if code in ("campagne", "hardcore", "arcade"):
            for k in range(-2, 3):
                brique(cx + k * 28, cy - 12, couleur if code != "hardcore" else config.ROUGE)
            raquette(cx + math.sin(t * 2.5) * 30, cy + 18)
            pygame.draw.circle(image, config.BLANC, (int(balle_x), int(cy + 4 + math.cos(t * 5) * 6)), 4)
        elif code == "coop":
            for k in range(-2, 3):
                brique(cx + k * 28, cy - 14)
            raquette(cx - 40, cy + 18)
            raquette(cx + 40, cy + 18)
            pygame.draw.circle(image, config.BLANC, (int(balle_x), int(cy + 2)), 4)
        elif code == "duel":
            raquette(cx + math.sin(t * 2) * 40, cy - 22)
            raquette(cx - math.sin(t * 2) * 40, cy + 22)
            for k in range(-1, 2):
                brique(cx + k * 28, cy)
            pygame.draw.circle(image, config.BLANC,
                               (int(cx + math.sin(t * 3) * 60), int(cy + math.cos(t * 3) * 14)), 4)
        else:
            for decal in (-60, 60):
                pygame.draw.rect(image, couleur, (cx + decal - 40, cy - 22, 80, 44), 1)
                raquette(cx + decal + math.sin(t * 3 + decal) * 16, cy + 16)
            pygame.draw.line(image, config.BLANC, (cx - 8, cy), (cx + 8, cy), 2)
            pygame.draw.lines(image, config.BLANC, False, [(cx + 2, cy - 6), (cx + 8, cy),
                                                            (cx + 2, cy + 6)], 2)
