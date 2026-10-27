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

import time

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from ecrans.hud import panneau
from ecrans.en_ligne.commun import EcranEnLigneBase, GRIS, date_courte
from ecrans.menus import bouton, carte

ACTIONS = [("bot", "BOT DE TEST"), ("neons", "+100 NEONS"), ("suspendre", "SUSPENDRE / RETABLIR"),
           ("cote", "COTE A 1000"), ("invisible", "INVISIBLE / VISIBLE"), ("mdp", "MOT DE PASSE PROVISOIRE"),
           ("supprimer", "SUPPRIMER LE COMPTE")]
A_CONFIRMER = {"mdp", "supprimer"}         # deux appuis de suite sur le même joueur
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
        self.provisoire = ""             # dernier mot de passe provisoire (à donner au joueur)
        self.confirmation = None         # (action, pseudo, instant) en attente du 2e appui
        self.zones_joueurs, self.zones_actions = [], []

    def entrer(self):
        self.app.en_ligne.appeler("GET", "/api/admin/joueurs", rappel=self._recu)

    def _recu(self, resultat):
        if not resultat["ok"]:
            self.message = resultat["erreur"] or "ACCES REFUSE"
            return
        donnees = resultat["donnees"]
        if donnees.get("mdp"):
            self.provisoire = donnees["mdp"]
        self.joueurs = donnees["joueurs"]
        self.indice = min(self.indice, max(0, len(self.joueurs) - 1))
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
        if code in A_CONFIRMER:
            maintenant = time.monotonic()
            attendu = (code, joueur["pseudo"])
            if not self.confirmation or self.confirmation[:2] != attendu or maintenant - self.confirmation[2] > 5:
                self.confirmation = (code, joueur["pseudo"], maintenant)
                quoi = "SUPPRIMER" if code == "supprimer" else "CHANGER LE MOT DE PASSE DE"
                self.message = f"{quoi} {joueur['pseudo'].upper()} ? REAPPUIE POUR CONFIRMER"
                return
            self.confirmation = None
        self.provisoire = ""
        corps = {"action": code, "valeur": 100}
        self.message = "COMPTE SUPPRIME" if code == "supprimer" else "..."
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
        if 1 in entrees.clics:                   # souris ou doigt : joueur, puis action
            for i, zone in self.zones_joueurs:
                if zone.collidepoint(entrees.souris):
                    self.indice = i
            for k, zone in self.zones_actions:
                if zone.collidepoint(entrees.souris):
                    self.action = k
                    self.app.audio.jouer("menu_ok")
                    self._agir()
        if entrees.molette and total:
            self.indice = max(0, min(total - 1, self.indice - entrees.molette))
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
        self.zones_joueurs, self.zones_actions = [], []
        for k, joueur in enumerate((self.joueurs or [])[self.debut:self.debut + VISIBLES]):
            i = self.debut + k
            y = liste.y + 60 + k * 46
            self.zones_joueurs.append((i, pygame.Rect(liste.x + 14, y - 20, liste.w - 28, 42)))
            if i == self.indice:
                pygame.draw.rect(image, (50, 20, 80), (liste.x + 14, y - 18, liste.w - 28, 38), border_radius=6)
            couleur = (150, 90, 120) if joueur["banni"] else config.BLANC
            point = config.VERT if joueur["pseudo"] in self.en_ligne_pseudos else (70, 50, 100)
            pygame.draw.circle(image, point, (liste.x + 32, y), 6)
            etiquette = " (INV)" if joueur.get("invisible") else (" (ADMIN)" if joueur["admin"] else "")
            dessiner_texte(image, joueur["pseudo"].upper() + etiquette,
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
            r = pygame.Rect(cote.x + 24, cote.y + 52 + k * 54, cote.w - 48, 44)
            self.zones_actions.append((k, r))
            if k == self.action:
                bouton(image, r, nom, config.AMBRE, 2)
            else:
                pygame.draw.rect(image, (60, 40, 30), r, 2, border_radius=8)
                dessiner_texte(image, nom, r.centerx, r.centery, 2, config.AMBRE, lueur=False)
            if code == "bot":
                etat = "OUI" if self.app.donnees.get("bot_actif") else "NON"
                dessiner_texte(image, etat, r.right - 16, r.centery, 2,
                               config.VERT if etat == "OUI" else GRIS, ancrage="droite", lueur=False)
        if self.provisoire:                     # à recopier et donner au joueur
            dessiner_texte(image, "MOT DE PASSE PROVISOIRE :", cote.x + 24, cote.y + 436, 2, GRIS,
                           ancrage="gauche", lueur=False)
            dessiner_texte(image, self.provisoire.upper(), cote.centerx, cote.y + 476, 3, config.VERT)
            dessiner_texte(image, "(LE JOUEUR LE CHANGE DANS LA ROUE)", cote.x + 24, cote.y + 512, 2, GRIS,
                           ancrage="gauche", lueur=False)
        else:
            aide = ["BOT : TA RAQUETTE EN LIGNE (F8)", "MOT DE PASSE ET SUPPRIMER :",
                    "APPUIE DEUX FOIS."]
            for k, ligne in enumerate(aide):
                dessiner_texte(image, ligne, cote.x + 24, cote.y + 436 + k * 26, 2, GRIS, ancrage="gauche",
                               lueur=False)
        if self.message:
            dessiner_texte(image, self.message, config.LARGEUR / 2, 660, 2, config.AMBRE, lueur=False)
        self.pied(image, "↑↓ : JOUEUR    ←→ : ACTION    ENTREE : APPLIQUER    ECHAP : ACCUEIL")
