# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Classements mondiaux : un onglet par mode (meilleur score de chaque
    joueur, ou nombre de victoires en Duel et en Course). La ligne du
    joueur connecté est mise en évidence.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from ecrans.hud import panneau
from ecrans.en_ligne.commun import EcranEnLigneBase, couleur_profil, NOMS_MODES, GRIS

ONGLETS = ["defi", "campagne", "arcade", "hardcore", "coop", "duel", "course"]
COULEURS_RANGS = [config.AMBRE, (220, 220, 240), (230, 140, 80)]


class EcranClassementsMondiaux(EcranEnLigneBase):
    """Attributs : onglet (int), donnees (dict mode -> réponse du serveur)."""

    titre = "CLASSEMENTS MONDIAUX"

    def __init__(self, app):
        super().__init__(app)
        self.onglet = 0
        self.donnees = {}
        self.erreur = ""
        self.charger()

    def charger(self):
        mode = ONGLETS[self.onglet]
        if mode not in self.donnees:
            if mode == "defi":
                from jeu.modes.defi import jour_du_defi
                chemin = f"/api/defi/{jour_du_defi()}"
            else:
                chemin = f"/api/classements/{mode}"
            self.app.en_ligne.appeler("GET", chemin,
                                      rappel=lambda r, m=mode: self._recu(m, r))

    def _recu(self, mode, resultat):
        if resultat["ok"]:
            self.donnees[mode] = resultat["donnees"]
        else:
            self.erreur = resultat["erreur"]

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        entrees = self.app.entrees
        if entrees.vient_d_appuyer("retour"):
            from ecrans.en_ligne.hub import EcranHub
            self.app.remplacer(EcranHub(self.app))
            return
        sens = int(entrees.vient_d_appuyer("droite") or 1 in entrees.clics) \
            - int(entrees.vient_d_appuyer("gauche"))
        if sens:
            self.onglet = (self.onglet + sens) % len(ONGLETS)
            self.app.audio.jouer("menu_nav")
            self.charger()

    def dessiner(self, image):
        self.dessiner_fond(image)
        for i, mode in enumerate(ONGLETS):
            rect = pygame.Rect(0, 0, 166, 40)
            rect.center = (int(config.LARGEUR / 2 + (i - (len(ONGLETS) - 1) / 2) * 174), 116)
            choisi = i == self.onglet
            pygame.draw.rect(image, config.CYAN if choisi else (60, 30, 90), rect,
                             0 if choisi else 2, border_radius=8)
            dessiner_texte(image, NOMS_MODES[mode], rect.centerx, rect.centery, 2,
                           (20, 0, 30) if choisi else config.CYAN, lueur=False)
        mode = ONGLETS[self.onglet]
        cadre = pygame.Rect(0, 0, 760, 500)
        cadre.midtop = (config.LARGEUR / 2, 152)
        panneau(image, cadre, config.CYAN)
        donnees = self.donnees.get(mode)
        if donnees is None:
            dessiner_texte(image, self.erreur or "CHARGEMENT...", cadre.centerx, cadre.centery, 3,
                           config.ROUGE if self.erreur else config.CYAN, lueur=False)
            return
        unite = "VICTOIRES" if donnees["type"] == "victoires" else "SCORE"
        if mode == "defi":
            jour = "/".join(reversed(donnees.get("jour", "--").split("-")[1:]))
            dessiner_texte(image, f"DEFI DU {jour}", cadre.x + 40, cadre.y + 24, 2, config.AMBRE,
                           ancrage="gauche", lueur=False)
        dessiner_texte(image, unite, cadre.right - 40, cadre.y + 24, 2, GRIS, ancrage="droite",
                       lueur=False)
        if not donnees["lignes"]:
            dessiner_texte(image, "PERSONNE N'A ENCORE JOUE", cadre.centerx, cadre.centery, 3,
                           (120, 90, 170), lueur=False)
        moi = self.app.en_ligne.pseudo.lower()
        for i, ligne in enumerate(donnees["lignes"][:10]):
            y = cadre.y + 64 + i * 43
            teinte = COULEURS_RANGS[i] if i < 3 else config.BLANC
            if ligne["pseudo"].lower() == moi:
                pygame.draw.rect(image, (50, 20, 80), (cadre.x + 16, y - 18, cadre.w - 32, 36),
                                 border_radius=6)
            dessiner_texte(image, f"{i + 1:2d}", cadre.x + 50, y, 3, teinte, ancrage="gauche",
                           lueur=i == 0)
            pygame.draw.circle(image, couleur_profil(ligne["couleur"]), (cadre.x + 130, y), 8)
            dessiner_texte(image, ligne["pseudo"].upper(), cadre.x + 150, y, 3, teinte,
                           ancrage="gauche", lueur=i == 0)
            dessiner_texte(image, f"NIV {ligne['niveau']}", cadre.x + 470, y, 2, GRIS,
                           ancrage="gauche", lueur=False)
            valeur = ligne["valeur"] if unite == "VICTOIRES" else f"{ligne['valeur']:07d}"
            dessiner_texte(image, str(valeur), cadre.right - 40, y, 3, teinte, ancrage="droite",
                           lueur=i == 0)
        self.pied(image, "← → : MODE    ECHAP : RETOUR")
