# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Écran ADMIN (2.1, menu de la roue, administrateurs seulement) : le bot de
    test (oui / non), et la liste des joueurs avec les actions de base :
    suspendre ou rétablir un compte, donner 100 NEONS, remettre la cote
    classée à 1000. Tout est vérifié par le serveur.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 25/10/2026
"""

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from ecrans.hud import panneau
from ecrans.en_ligne.commun import EcranEnLigneBase, GRIS, date_courte
from ecrans.menus import bouton, carte

ACTIONS = [("bot", "BOT DE TEST"), ("neons", "+100 NEONS"), ("suspendre", "SUSPENDRE / RETABLIR"),
           ("cote", "COTE A 1000")]
VISIBLES = 10


class EcranAdmin(EcranEnLigneBase):
    """Attributs : joueurs (list de dict), indice (int), action (int), message (str)."""

    titre = "ADMIN"
    onglet = ""

    def __init__(self, app):
        super().__init__(app)
        self.joueurs = None
        self.en_ligne_pseudos = []
        self.indice = 0
        self.action = 0
        self.debut = 0
        self.message = "CHARGEMENT..."

    def entrer(self):
        self.app.en_ligne.appeler("GET", "/api/admin/joueurs", rappel=self._recu)

    def _recu(self, resultat):
        if not resultat["ok"]:
            self.message = resultat["erreur"] or "ACCES REFUSE"
            return
        donnees = resultat["donnees"]
        self.joueurs = donnees["joueurs"]
        self.en_ligne_pseudos = donnees.get("en_ligne", self.en_ligne_pseudos)
        self.message = ""

    def _agir(self):
        code = ACTIONS[self.action][0]
        if code == "bot":
            self.app.donnees["bot_actif"] = not self.app.donnees.get("bot_actif", False)
            self.app.enregistrer()
            self.message = "BOT ACTIVE : IL JOUERA TES PARTIES EN LIGNE" if self.app.donnees["bot_actif"] \
                else "BOT COUPE"
            return
        if not self.joueurs:
            return
        joueur = self.joueurs[self.indice]
        if code == "suspendre" and joueur["banni"]:
            code = "retablir"
        corps = {"action": code, "valeur": 100}
        self.message = "..."
        self.app.en_ligne.appeler("POST", f"/api/admin/joueurs/{joueur['pseudo']}", corps, self._recu)

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        entrees = self.app.entrees
        if entrees.vient_d_appuyer("retour"):
            self.retour_accueil()
            return
        total = len(self.joueurs or [])
        if entrees.vient_d_appuyer("haut") and total:
            self.indice = (self.indice - 1) % total
        if entrees.vient_d_appuyer("bas") and total:
            self.indice = (self.indice + 1) % total
        if entrees.vient_d_appuyer("gauche"):
            self.action = (self.action - 1) % len(ACTIONS)
        if entrees.vient_d_appuyer("droite"):
            self.action = (self.action + 1) % len(ACTIONS)
        if entrees.vient_d_appuyer("valider"):
            self.app.audio.jouer("menu_ok")
            self._agir()
        self.debut = max(0, min(self.indice - VISIBLES // 2, total - VISIBLES))

    def dessiner(self, image):
        self.dessiner_fond(image)
        liste = pygame.Rect(40, 90, 760, 540)
        panneau(image, liste, config.AMBRE)
        dessiner_texte(image, "JOUEURS", liste.x + 24, liste.y + 24, 2, config.AMBRE, ancrage="gauche",
                       lueur=False)
        for k, joueur in enumerate((self.joueurs or [])[self.debut:self.debut + VISIBLES]):
            i = self.debut + k
            y = liste.y + 60 + k * 46
            if i == self.indice:
                pygame.draw.rect(image, (50, 20, 80), (liste.x + 14, y - 18, liste.w - 28, 38), border_radius=6)
            couleur = (150, 90, 120) if joueur["banni"] else config.BLANC
            point = config.VERT if joueur["pseudo"] in self.en_ligne_pseudos else (70, 50, 100)
            pygame.draw.circle(image, point, (liste.x + 32, y), 6)
            dessiner_texte(image, joueur["pseudo"].upper() + ("  (ADMIN)" if joueur["admin"] else ""),
                           liste.x + 50, y, 2, couleur, ancrage="gauche", lueur=False)
            dessiner_texte(image, f"RANG {joueur['niveau']}", liste.x + 330, y, 2, GRIS, ancrage="gauche",
                           lueur=False)
            dessiner_texte(image, f"{joueur['neons']} N", liste.x + 450, y, 2, config.CYAN, ancrage="gauche",
                           lueur=False)
            dessiner_texte(image, "SUSPENDU" if joueur["banni"] else date_courte(joueur["vu_le"]),
                           liste.right - 24, y, 2, config.ROUGE if joueur["banni"] else GRIS,
                           ancrage="droite", lueur=False)
        cote = pygame.Rect(830, 90, 410, 540)
        carte(image, cote, config.AMBRE, False)
        dessiner_texte(image, "ACTIONS", cote.x + 24, cote.y + 24, 2, config.AMBRE, ancrage="gauche", lueur=False)
        for k, (code, nom) in enumerate(ACTIONS):
            r = pygame.Rect(cote.x + 24, cote.y + 60 + k * 70, cote.w - 48, 52)
            if k == self.action:
                bouton(image, r, nom, config.AMBRE, 2)
            else:
                pygame.draw.rect(image, (60, 40, 30), r, 2, border_radius=8)
                dessiner_texte(image, nom, r.centerx, r.centery, 2, config.AMBRE, lueur=False)
            if code == "bot":
                etat = "OUI" if self.app.donnees.get("bot_actif") else "NON"
                dessiner_texte(image, etat, r.right - 16, r.centery, 2,
                               config.VERT if etat == "OUI" else GRIS, ancrage="droite", lueur=False)
        aide = ["LE BOT JOUE TA RAQUETTE DANS", "LES PARTIES EN LIGNE (F8 EN JEU).",
                "LANCE LE JEU DEUX FOIS : L'UN EN", "BOT, L'AUTRE POUR TOI."]
        for k, ligne in enumerate(aide):
            dessiner_texte(image, ligne, cote.x + 24, cote.y + 360 + k * 26, 2, GRIS, ancrage="gauche",
                           lueur=False)
        if self.message:
            dessiner_texte(image, self.message, config.LARGEUR / 2, 660, 2, config.AMBRE, lueur=False)
        self.pied(image, "↑↓ : JOUEUR    ←→ : ACTION    ENTREE : APPLIQUER    ECHAP : ACCUEIL")
