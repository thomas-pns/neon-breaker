# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Écran d'aide illustré en trois pages : capsules (bonus, malus,
    pouvoirs), briques (dessinées et animées), commandes et OVERDRIVE.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Mini-démonstration animée de chaque pouvoir.
"""

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from jeu.brique import fabriquer_brique
from jeu.capsule import CATALOGUE, Capsule, COULEURS_CATEGORIE
from ecrans.base import EcranBase, voile
from ecrans.hud import panneau, dessiner_inventaire, dessiner_overdrive

PAGES = ["CAPSULES", "POUVOIRS ET OVERDRIVE", "BRIQUES", "COMMANDES"]
# Format vertical (téléphone) : une catégorie de capsules par page, et les commandes au doigt.
PAGES_VERTICAL = ["BONUS", "MALUS", "POUVOIRS", "BRIQUES", "AU DOIGT"]
LIGNES_DOIGT = [
    ("BOUGER", "GLISSE LE DOIGT DANS LA ZONE DU BAS"),
    ("LANCER", "TOUCHE LE TERRAIN"),
    ("POUVOIRS", "LES 3 CASES A GAUCHE, SOUS LE TERRAIN"),
    ("SUPERNOVA", "LE BOUTON DE DROITE, QUAND IL S'ALLUME"),
    ("OVERDRIVE", "SE REMPLIT EN CASSANT DES BRIQUES"),
    ("", "PLUS VITE AVEC UN GROS MULTIPLICATEUR"),
    ("COMBO", "BRIQUES SANS TOUCHER LA RAQUETTE"),
    ("", "x2 (5)  x3 (10)  x5 (20)  x8 (35)"),
    ("PAUSE", "LE BOUTON ROND EN HAUT DU TERRAIN"),
    ("MENUS", "ONGLETS EN BAS, FLECHE : RETOUR"),
]


def est_vertical():
    return config.HAUTEUR > config.LARGEUR
BRIQUES_AIDE = [
    ("a", "NORMALE", "1 COUP"),
    ("R", "SOLIDE", "2 A 5 COUPS, SE FISSURE"),
    ("M", "METAL", "INDESTRUCTIBLE (SAUF FEU)"),
    ("X", "EXPLOSIVE", "DETRUIT SES 8 VOISINES"),
    ("?", "BONUS", "LACHE TOUJOURS UNE CAPSULE"),
    (">", "MOBILE", "GLISSE DE GAUCHE A DROITE"),
    ("H", "REGENERANTE", "REVIENT SI UNE SOEUR SURVIT"),
    ("*", "FANTOME", "INVISIBLE, 2 COUPS"),
    ("P", "PORTAIL", "TELEPORTE LA BALLE"),
]


class EcranAide(EcranBase):
    """Attributs : page (int), capsules et briques d'illustration."""

    vertical = True               # dessiné aussi au format vertical (téléphone)

    def __init__(self, app):
        super().__init__(app)
        self.page = 0
        self.capsules = {code: Capsule(0, 0, code) for code in CATALOGUE}
        self.briques = []
        self.joueur_demo = type("JoueurDemo", (), {})()
        self.joueur_demo.inventaire = [next(code for code, effet in CATALOGUE.items()
                                            if effet.categorie == "pouvoir")]
        self.joueur_demo.profil = "solo"
        self.joueur_demo.selection = 0
        self.joueur_demo.avec_overdrive = True
        self.joueur_demo.overdrive = 1.0
        self.joueur_demo.supernova = 0.0
        self.joueur_demo.overdrive_pret = lambda: True
        for i, (caractere, nom, texte) in enumerate(BRIQUES_AIDE):
            colonne, ligne = divmod(i, 5)
            brique = fabriquer_brique(caractere, 150 + colonne * 520, 160 + ligne * 96, 70, 26)
            brique.apparition = 1.0
            if hasattr(brique, "revelee"):
                brique.revelee = True
            if hasattr(brique, "x_min"):
                brique.x_min, brique.x_max = brique.x - 20, brique.x + 20
            self.briques.append((brique, nom, texte))
        self.briques_verticales = []
        for i, (caractere, nom, texte) in enumerate(BRIQUES_AIDE):
            brique = fabriquer_brique(caractere, 60, 210 + i * 104, 70, 26)
            brique.apparition = 1.0
            if hasattr(brique, "revelee"):
                brique.revelee = True
            if hasattr(brique, "x_min"):
                brique.x_min, brique.x_max = brique.x - 20, brique.x + 20
            self.briques_verticales.append((brique, nom, texte))

    def pages(self):
        return PAGES_VERTICAL if est_vertical() else PAGES

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        entrees = self.app.entrees
        for capsule in self.capsules.values():
            capsule.temps += dt
        for brique, _, _ in self.briques + self.briques_verticales:
            brique.mettre_a_jour(dt)
        pages = self.pages()
        if entrees.vient_d_appuyer("droite") or entrees.vient_d_appuyer("valider") \
                or (1 in entrees.clics and not entrees.tactile) or entrees.balayage < 0:
            self.page = (self.page + 1) % len(pages)
            self.app.audio.jouer("menu_nav")
        elif entrees.vient_d_appuyer("gauche") or entrees.balayage > 0:
            self.page = (self.page - 1) % len(pages)
            self.app.audio.jouer("menu_nav")
        elif entrees.vient_d_appuyer("retour"):
            if self.dessous is not None:
                self.app.depiler()
            else:
                from ecrans.titre import EcranTitre
                self.app.remplacer(EcranTitre(self.app))

    def dessiner(self, image):
        self.app.fond.dessiner(image)
        voile(image, 170)
        if est_vertical():
            self._dessiner_vertical(image)
            return
        self.page %= len(PAGES)
        dessiner_texte(image, f"AIDE  -  {PAGES[self.page]}", config.LARGEUR / 2, 46, 5,
                       config.CYAN)
        for i in range(len(PAGES)):
            couleur = config.AMBRE if i == self.page else (90, 60, 120)
            pygame.draw.circle(image, couleur, (config.LARGEUR // 2 - 20 + i * 20, 86), 5)
        [self._page_capsules, self._page_pouvoirs, self._page_briques,
         self._page_commandes][self.page](image)
        dessiner_texte(image, "← → : PAGE    ECHAP : RETOUR", config.LARGEUR / 2,
                       config.HAUTEUR - 24, 2, (150, 120, 200), lueur=False)

    def _dessiner_vertical(self, image):
        """Aide au format vertical : une page par sujet, on glisse pour changer."""
        from ecrans.menus import marge_haut
        self.page %= len(PAGES_VERTICAL)
        nom = PAGES_VERTICAL[self.page]
        haut = 40 + marge_haut()
        dessiner_texte(image, "AIDE", config.LARGEUR / 2, haut + 20, 6, config.CYAN)
        dessiner_texte(image, nom, config.LARGEUR / 2, haut + 80, 4, config.AMBRE)
        for i in range(len(PAGES_VERTICAL)):
            couleur = config.AMBRE if i == self.page else (90, 60, 120)
            pygame.draw.circle(image, couleur, (config.LARGEUR // 2 - 40 + i * 20, haut + 118), 6)
        cadre = pygame.Rect(24, haut + 146, config.LARGEUR - 48, config.HAUTEUR - haut - 260)
        if nom in ("BONUS", "MALUS", "POUVOIRS"):
            categorie = {"BONUS": "bonus", "MALUS": "malus", "POUVOIRS": "pouvoir"}[nom]
            couleur = COULEURS_CATEGORIE[categorie]
            panneau(image, cadre, couleur)
            sous_titre = {"bonus": "EFFET IMMEDIAT", "malus": "A EVITER",
                          "pouvoir": "A STOCKER : 3 CASES SOUS LE TERRAIN"}[categorie]
            dessiner_texte(image, sous_titre, cadre.centerx, cadre.y + 34, 2, couleur, lueur=False)
            effets = [e for e in CATALOGUE.values() if e.categorie == categorie]
            pas = min(120, (cadre.h - 80) // max(1, len(effets)))
            from moteur.icones import dessiner_icone
            for ligne, effet in enumerate(effets):
                y = cadre.y + 90 + ligne * pas
                case = pygame.Rect(0, 0, 64, 64)
                case.center = (cadre.x + 64, y + 10)
                pygame.draw.rect(image, (20, 4, 40), case, border_radius=10)
                pygame.draw.rect(image, effet.couleur(), case, 2, border_radius=10)
                dessiner_icone(image, effet.code, case.center, effet.couleur(), 5, lueur=True)
                dessiner_texte(image, effet.nom, cadre.x + 120, y - 6, 3, config.BLANC,
                               ancrage="gauche", lueur=False)
                dessiner_texte(image, effet.description, cadre.x + 120, y + 26, 2,
                               (190, 170, 230), ancrage="gauche", lueur=False, ombre=False)
        elif nom == "BRIQUES":
            panneau(image, cadre, config.ROSE)
            decalage_y = cadre.y + 60 - 210
            for brique, titre, texte in self.briques_verticales:
                ancien_y = brique.y
                brique.y = ancien_y + decalage_y
                brique.dessiner(image, self.temps)
                brique.y = ancien_y
                y = ancien_y + decalage_y
                dessiner_texte(image, titre, 160, y + 4, 3, config.BLANC, ancrage="gauche", lueur=False)
                dessiner_texte(image, texte, 160, y + 36, 2, (190, 170, 230), ancrage="gauche",
                               lueur=False, ombre=False)
        else:
            panneau(image, cadre, config.CYAN)
            y = cadre.y + 40
            for titre, texte in LIGNES_DOIGT:
                if titre:                    # nouveau sujet ; sinon, suite du précédent
                    y += 48
                    dessiner_texte(image, titre, cadre.x + 30, y, 3, config.AMBRE, ancrage="gauche",
                                   lueur=False)
                y += 32
                dessiner_texte(image, texte, cadre.x + 30, y, 2, config.BLANC, ancrage="gauche",
                               lueur=False, ombre=False)
        dessiner_texte(image, "GLISSE POUR CHANGER DE PAGE", config.LARGEUR / 2,
                       config.HAUTEUR - 70, 2, (150, 120, 200), lueur=False)

    def _page_capsules(self, image):
        titres = {"bonus": "BONUS (VERT) : EFFET IMMEDIAT",
                  "malus": "MALUS (ROUGE) : A EVITER",
                  "pouvoir": "POUVOIRS (OR) : A STOCKER"}
        for colonne, categorie in enumerate(("bonus", "malus", "pouvoir")):
            x = 40 + colonne * 410
            rect = pygame.Rect(x - 10, 110, 400, 520)
            panneau(image, rect, COULEURS_CATEGORIE[categorie])
            dessiner_texte(image, titres[categorie], rect.centerx, 134, 2,
                           COULEURS_CATEGORIE[categorie], lueur=False)
            effets = [e for e in CATALOGUE.values() if e.categorie == categorie]
            for ligne, effet in enumerate(effets):
                y = 190 + ligne * 66
                from moteur.icones import dessiner_icone
                case = pygame.Rect(0, 0, 40, 40)
                case.center = (x + 30, y + 2)
                pygame.draw.rect(image, (20, 4, 40), case, border_radius=8)
                pygame.draw.rect(image, effet.couleur(), case, 2, border_radius=8)
                dessiner_icone(image, effet.code, case.center, effet.couleur(), 3, lueur=True)
                dessiner_texte(image, effet.nom, x + 72, y - 10, 2, config.BLANC,
                               ancrage="gauche", lueur=False)
                dessiner_texte(image, effet.description, x + 72, y + 14, 2,
                               (190, 170, 230), ancrage="gauche", lueur=False, ombre=False)
        dessiner_texte(image, "SOLO : 1 2 3 = POUVOIRS     2 JOUEURS : CHOISIR PUIS ACTIVER",
                       config.LARGEUR / 2, 656, 2,
                       config.AMBRE, lueur=False)

    def _page_briques(self, image):
        for brique, nom, texte in self.briques:
            brique.dessiner(image, self.temps)
            x = brique.x + 100
            dessiner_texte(image, nom, x, brique.y + 4, 3, config.BLANC, ancrage="gauche",
                           lueur=False)
            dessiner_texte(image, texte, x, brique.y + 32, 2, (190, 170, 230),
                           ancrage="gauche", lueur=False, ombre=False)

    def _page_pouvoirs(self, image):
        """But : expliquer l'inventaire et illustrer la jauge OVERDRIVE."""
        rect = pygame.Rect(90, 120, 1100, 500)
        panneau(image, rect, config.AMBRE)
        dessiner_texte(image, "3 CASES : UNE CAPSULE DOREE ATTRAPEE VA DANS LA PREMIERE CASE LIBRE",
                       640, 154, 2, config.BLANC)
        dessiner_inventaire(image, 640, 208, self.joueur_demo, ["1", "2", "3"], 44)
        lignes = ["SOLO : 1 2 3 LANCENT LA CASE 1 2 OU 3",
                  "A OU TAB : CHOISIR UNE CASE   E : LANCER LA CASE CHOISIE",
                  "A DEUX : J1 A CHOISIR / E LANCER   J2 CTRL D CHOISIR / MAJ D LANCER",
                  "OVERDRIVE : LA JAUGE SE REMPLIT EN CASSANT DES BRIQUES",
                  "PLUS VITE AVEC UN GROS MULTIPLICATEUR",
                  "JAUGE PLEINE : MAJ (J1 S, J2 FLECHE BAS) DECLENCHE LA SUPERNOVA",
                  "QUELQUES SECONDES DE PUISSANCE, PUIS LA JAUGE REPART DE ZERO"]
        for i, texte in enumerate(lignes):
            dessiner_texte(image, texte, 640, 276 + i * 34, 2,
                           config.AMBRE if i == 5 else config.BLANC)
        dessiner_overdrive(image, pygame.Rect(490, 536, 300, 16), self.joueur_demo, self.temps, "MAJ")

    def _page_commandes(self, image):
        blocs = [("SOLO", "solo", config.CYAN, 60), ("JOUEUR 1", "j1", config.ROSE, 470),
                 ("JOUEUR 2", "j2", config.AMBRE, 880)]
        for titre, profil, couleur, x in blocs:
            rect = pygame.Rect(x - 20, 110, 370, 310)
            panneau(image, rect, couleur)
            dessiner_texte(image, titre, rect.centerx, 150, 3, couleur)
            from moteur.entrees import libelles_touches
            for i, (touche, action) in enumerate(libelles_touches(self.app, profil)):
                y = 184 + i * 25
                dessiner_texte(image, touche, rect.x + 24, y, 2, config.BLANC,
                               ancrage="gauche", lueur=False)
                dessiner_texte(image, action, rect.right - 24, y, 2, (190, 170, 230),
                               ancrage="droite", lueur=False)
        rect = pygame.Rect(40, 430, 1200, 230)
        panneau(image, rect, config.BLANC)
        lignes = [
            ("OVERDRIVE", "SE REMPLIT A CHAQUE BRIQUE (PLUS VITE EN COMBO) ET AVEC LES CAPSULES"),
            ("SUPERNOVA", "JAUGE PLEINE : 6 S DE BALLES DE FEU + RAYON AU-DESSUS DE LA RAQUETTE"),
            ("COMBO", "BRIQUES SANS TOUCHER LA RAQUETTE : x2 (5)  x3 (10)  x5 (20)  x8 (35)"),
            ("CLAVIER", "TOUCHES PHYSIQUES : MEME PLACE EN AZERTY ET EN QWERTY"),
            ("ECRAN", "F11 : PLEIN ECRAN    F3 : IMAGES PAR SECONDE    ECHAP : PAUSE"),
        ]
        for i, (titre, texte) in enumerate(lignes):
            y = 470 + i * 38
            dessiner_texte(image, titre, rect.x + 30, y, 2, config.AMBRE, ancrage="gauche",
                           lueur=False)
            dessiner_texte(image, texte, rect.x + 200, y, 2,
                           config.BLANC, ancrage="gauche", lueur=False, ombre=False)
