# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Onglet CASIER (2.1) : toute la collection du joueur, en solo comme en
    ligne : raquettes, bannières et couleur. Les objets possédés s'équipent
    avec Entrée ; les autres montrent comment les obtenir (rang, succès,
    boutique). Le choix est gardé par le serveur (il faut être connecté).

    Commandes : flèches dans la grille ; ← depuis la 1re colonne passe à la
    liste des catégories (↑ ↓ pour en changer, → pour revenir).

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 25/10/2026
"""

import pygame

from moteur import config
from moteur.bannieres import dessiner_banniere
from moteur.police_pixel import dessiner_texte
from reseau.boutique import BANNIERES, COULEURS_RARETES, NOMS_RARETES
from reseau.profil import COULEURS, SKINS, condition_lisible
from ecrans.menus import EcranMenu, GRIS, carte

CATEGORIES = [("raquettes", "RAQUETTES"), ("bannieres", "BANNIERES"), ("couleur", "COULEUR")]
COLONNES, LIGNES_VISIBLES = 4, 3
CASE = (200, 136)
X_GRILLE, Y_GRILLE = 370, 96


def comment_obtenir(banniere):
    """But : sous-titre d'une bannière : sa rareté, ou comment la gagner (boss, saison)."""
    recompense = banniere.get("recompense") or ""
    if recompense.startswith("boss_"):
        return "BATTRE LE BOSS " + recompense[5:].upper()
    if recompense == "saison":
        division = {"saison_or": "OR", "saison_platine": "PLATINE", "saison_neon": "NEON"}.get(
            banniere["code"], "OR")
        return f"SAISON EN {division}"
    return NOMS_RARETES[banniere["rarete"]]


def grille():
    """
    But : disposition de la grille : (colonnes, lignes visibles, x, y, catégories en haut ?).
    Format vertical (téléphone) : catégories en onglets en haut, grille de 3 colonnes.
    """
    from ecrans.menus import bas_contenu, est_vertical, haut_contenu
    if not est_vertical():
        return COLONNES, LIGNES_VISIBLES, X_GRILLE, Y_GRILLE, False
    y = haut_contenu() + 90
    lignes = max(1, (bas_contenu() - 80 - y) // (CASE[1] + 14))
    largeur = 3 * CASE[0] + 2 * 18
    return 3, lignes, (config.LARGEUR - largeur) // 2 - 8, y, True


class EcranCasier(EcranMenu):
    """Attributs : categorie (int), indice (int), dans_liste (bool : focus sur les catégories)."""

    onglet = "CASIER"
    vertical = True

    def __init__(self, app):
        super().__init__(app)
        self.categorie = 0
        self.indice = 0
        self.dans_liste = False
        self.premiere_ligne = 0
        self.message = ""
        self.minuteur = 0.0
        self.apercus = {}
        self.zones = []
        self.zones_categories = []

    # --- Objets ------------------------------------------------------------------------

    def objets(self):
        """But : objets de la catégorie : (code, nom, possédé, équipé, sous-titre)."""
        en_ligne = self.app.en_ligne
        code = CATEGORIES[self.categorie][0]
        if code == "raquettes":
            actif = en_ligne.skin_actif()
            return [(s["code"], s["nom"], s["code"] in en_ligne.skins or s["condition"] is None,
                     s["code"] == actif, condition_lisible(s)) for s in SKINS]
        if code == "bannieres":
            possedes = set(getattr(en_ligne, "bannieres", []))
            actif = en_ligne.banniere_active() if en_ligne.jeton else ""
            liste = [("", "AUCUNE", True, actif == "", "")]
            return liste + [(b["code"], b["nom"], b["code"] in possedes, b["code"] == actif,
                             comment_obtenir(b)) for b in BANNIERES]
        return [(c, c.upper(), True, c == en_ligne.couleur, "") for c in COULEURS]

    def _apercu(self, code):
        if code not in self.apercus:
            from jeu.joueur import Joueur
            from jeu.raquette import Raquette
            joueur = Joueur(1, "solo", "J1")
            joueur.raquette = Raquette(0, config.LARGEUR, 0, joueur=joueur)
            joueur.appliquer_skin(code)
            self.apercus[code] = joueur
        return self.apercus[code]

    def equiper(self, objet):
        code, nom, possede, equipe, sous_titre = objet
        en_ligne = self.app.en_ligne
        if not en_ligne.jeton:
            self._dire("CONNECTE-TOI POUR CHANGER TON STYLE")
            return
        if not possede:
            self._dire(sous_titre or "PAS ENCORE DEBLOQUE")
            self.app.audio.jouer("metal")
            return
        categorie = CATEGORIES[self.categorie][0]
        if categorie == "raquettes":
            en_ligne.changer_skin(code)
        elif categorie == "bannieres":
            en_ligne.changer_banniere(code)
        else:
            en_ligne.couleur = code
            en_ligne.changer_couleur(code)
        self.app.audio.jouer("menu_ok")
        self._dire(f"{nom} EQUIPE")

    def _dire(self, texte):
        self.message, self.minuteur = texte, 2.5

    # --- Boucle ------------------------------------------------------------------------

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        self.minuteur = max(0.0, self.minuteur - dt)
        if self.naviguer():
            return
        entrees = self.app.entrees
        if entrees.vient_d_appuyer("retour"):
            self.aller("ACCUEIL")
            return
        objets = self.objets()
        colonnes, lignes_visibles, _, _, _ = grille()
        ancien = (self.categorie, self.indice, self.dans_liste)
        if self.dans_liste:
            if entrees.vient_d_appuyer("haut"):
                self.categorie = (self.categorie - 1) % len(CATEGORIES)
            if entrees.vient_d_appuyer("bas"):
                self.categorie = (self.categorie + 1) % len(CATEGORIES)
            if entrees.vient_d_appuyer("droite") or entrees.vient_d_appuyer("valider"):
                self.dans_liste = False
            if self.categorie != ancien[0]:
                self.indice, self.premiere_ligne = 0, 0
        else:
            if entrees.vient_d_appuyer("gauche"):
                if self.indice % colonnes == 0:
                    self.dans_liste = True
                else:
                    self.indice -= 1
            if entrees.vient_d_appuyer("droite"):
                self.indice = min(len(objets) - 1, self.indice + 1)
            if entrees.vient_d_appuyer("bas"):
                self.indice = min(len(objets) - 1, self.indice + colonnes)
            if entrees.vient_d_appuyer("haut") and self.indice >= colonnes:
                self.indice -= colonnes
            if entrees.vient_d_appuyer("valider"):
                self.equiper(objets[self.indice])
        if 1 in entrees.clics:
            for i, zone in enumerate(self.zones_categories):
                if zone.collidepoint(entrees.souris) and i != self.categorie:
                    self.categorie, self.indice, self.premiere_ligne = i, 0, 0
            for i, zone in self.zones:
                if zone.collidepoint(entrees.souris):
                    if i == self.indice:
                        self.equiper(objets[i])
                    self.indice, self.dans_liste = i, False
        if entrees.molette:
            self.premiere_ligne = max(0, self.premiere_ligne - entrees.molette)
        ligne = self.indice // colonnes
        if ligne < self.premiere_ligne:
            self.premiere_ligne = ligne
        if ligne >= self.premiere_ligne + lignes_visibles:
            self.premiere_ligne = ligne - lignes_visibles + 1
        derniere = max(0, (len(self.objets()) - 1) // colonnes - lignes_visibles + 1)
        self.premiere_ligne = min(self.premiere_ligne, derniere)
        if (self.categorie, self.indice, self.dans_liste) != ancien:
            self.app.audio.jouer("menu_nav")

    # --- Dessin ------------------------------------------------------------------------

    def dessiner(self, image):
        self.dessiner_fond(image)
        self.zones_categories = []
        colonnes, lignes_visibles, x_grille, y_grille, en_haut = grille()
        for k, (code, nom) in enumerate(CATEGORIES):
            objets_categorie = self._compte(code)
            if en_haut:
                largeur = (config.LARGEUR - 40 - 2 * 12) // len(CATEGORIES)
                r = pygame.Rect(20 + k * (largeur + 12), y_grille - 80, largeur, 58)
            else:
                r = pygame.Rect(40, Y_GRILLE + k * 64, 300, 52)
            self.zones_categories.append(r)
            actif = k == self.categorie
            carte(image, r, config.ROSE if actif else (90, 60, 130), actif and self.dans_liste)
            dessiner_texte(image, f"{nom}  {objets_categorie}", r.x + 20, r.centery, 2,
                           config.BLANC if actif else GRIS, ancrage="gauche", lueur=False)
        objets = self.objets()
        self.zones = []
        debut = self.premiere_ligne * colonnes
        for i in range(debut, min(len(objets), debut + colonnes * lignes_visibles)):
            col, lig = (i - debut) % colonnes, (i - debut) // colonnes
            r = pygame.Rect(x_grille + col * (CASE[0] + 18), y_grille + lig * (CASE[1] + 14), *CASE)
            self.zones.append((i, r))
            self._dessiner_objet(image, r, objets[i], i == self.indice and not self.dans_liste)
        lignes_total = (len(objets) - 1) // colonnes + 1
        if lignes_total > lignes_visibles:
            hauteur = lignes_visibles * (CASE[1] + 14) - 14
            pygame.draw.rect(image, (40, 20, 70), (x_grille + colonnes * (CASE[0] + 18) - 4, y_grille, 6, hauteur), border_radius=3)
            curseur = hauteur * lignes_visibles / lignes_total
            y = y_grille + (hauteur - curseur) * self.premiere_ligne / max(1, lignes_total - lignes_visibles)
            pygame.draw.rect(image, config.ROSE, (x_grille + colonnes * (CASE[0] + 18) - 4, int(y), 6, int(curseur)), border_radius=3)
        x_message = config.LARGEUR / 2 if en_haut else 810
        y_message = y_grille + lignes_visibles * (CASE[1] + 14) + 20 if en_haut else 572
        if self.minuteur > 0:
            dessiner_texte(image, self.message, x_message, y_message, 2, config.AMBRE, lueur=False)
        elif not self.app.en_ligne.jeton:
            dessiner_texte(image, "CONNECTE-TOI POUR EQUIPER TES SKINS ET BANNIERES", x_message,
                           y_message, 2, config.ROSE, lueur=False)
        else:
            dessiner_texte(image, "TON STYLE SE VOIT EN SOLO ET EN LIGNE", x_message, y_message, 2,
                           GRIS, lueur=False)
        if not en_haut:
            dessiner_texte(image, "FLECHES : CHOISIR    ENTREE : EQUIPER    TAB : ONGLET",
                           config.LARGEUR / 2, config.HAUTEUR - 26, 2, (150, 120, 200), lueur=False)
        self.dessiner_barre(image)

    def _compte(self, code):
        en_ligne = self.app.en_ligne
        if code == "raquettes":
            return f"{len([s for s in SKINS if s['code'] in en_ligne.skins or s['condition'] is None])}/{len(SKINS)}"
        if code == "bannieres":
            return f"{len(getattr(en_ligne, 'bannieres', []))}/{len(BANNIERES)}"
        return ""

    def _dessiner_objet(self, image, r, objet, choisi):
        code, nom, possede, equipe, sous_titre = objet
        categorie = CATEGORIES[self.categorie][0]
        teinte = config.CYAN
        if categorie == "bannieres" and code:
            from reseau.boutique import BANNIERES_PAR_CODE
            teinte = COULEURS_RARETES[BANNIERES_PAR_CODE[code]["rarete"]]
        carte(image, r, teinte if (choisi or equipe) else (90, 60, 130), choisi)
        couleur_nom = config.BLANC if possede else (110, 90, 150)
        if categorie == "raquettes":
            raquette = self._apercu(code).raquette
            raquette.x, raquette.y = r.centerx, r.y + 40
            raquette.dessiner(image, self.temps)
        elif categorie == "bannieres":
            zone = pygame.Rect(r.x + 14, r.y + 26, r.w - 28, 34)
            if code:
                dessiner_banniere(image, code, zone, self.temps)
            else:
                pygame.draw.rect(image, (60, 40, 90), zone, 2, border_radius=6)
            if not possede:
                voile = pygame.Surface(zone.size, pygame.SRCALPHA)
                voile.fill((8, 0, 20, 150))
                image.blit(voile, zone.topleft)
        else:
            from ecrans.en_ligne.commun import couleur_profil
            pygame.draw.circle(image, couleur_profil(code), (r.centerx, r.y + 46), 24)
            pygame.draw.circle(image, config.BLANC, (r.centerx, r.y + 46), 24, 2)
        dessiner_texte(image, nom[:16], r.centerx, r.y + 88, 2 if len(nom) <= 14 else 1, couleur_nom)
        if equipe:
            dessiner_texte(image, "EQUIPE", r.centerx, r.y + 114, 2, config.VERT, lueur=False)
        elif not possede:
            texte = sous_titre if sous_titre.startswith(("BATTRE", "SAISON")) else "VERROUILLE"
            dessiner_texte(image, texte, r.centerx, r.y + 114, 2 if len(texte) <= 14 else 1, (150, 90, 120),
                           lueur=False)
        elif sous_titre and categorie == "bannieres":
            dessiner_texte(image, sous_titre, r.centerx, r.y + 114, 2, teinte, lueur=False)
