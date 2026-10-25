# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    OPTIONS > COMMANDES (2.0) : changer la touche de chaque action, pour le
    joueur solo et pour J1 / J2 sur le même clavier. Entrée sur une ligne,
    puis on appuie sur la nouvelle touche (Échap annule). Si la touche sert
    déjà à une autre action du même joueur, les deux s'échangent.
    Rappelle aussi les boutons de la manette.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 25/10/2026
"""

import pygame

from moteur import config
from moteur.entrees import nom_commande
from moteur.police_pixel import dessiner_texte
from moteur.rendu import attenuer, halo_rect
from ecrans.base import EcranBase, voile
from ecrans.hud import panneau

PROFILS = [("solo", "SOLO", config.CYAN), ("j1", "JOUEUR 1", config.ROSE),
           ("j2", "JOUEUR 2", config.AMBRE)]
TOUCHES_INTERDITES = {pygame.KSCAN_ESCAPE, pygame.KSCAN_F11, pygame.KSCAN_F3}


class EcranCommandes(EcranBase):
    """
    Attributs : onglet (int : profil), indice (int : ligne), attente (bool :
    on attend la nouvelle touche), message (str).
    """

    transparent = True

    def __init__(self, app):
        super().__init__(app)
        self.onglet = 0
        self.indice = 0
        self.attente = False
        self.message = ""

    @property
    def attenuer_musique(self):
        return getattr(self.dessous, "attenuer_musique", False)

    def musique(self):
        return self.dessous.musique() if self.dessous is not None else "menu"

    def _profil(self):
        return PROFILS[self.onglet][0]

    def _lignes(self):
        return config.COMMANDES[self._profil()] + [(None, "PAR DEFAUT", ""), (None, "RETOUR", "")]

    def _perso(self):
        return self.app.reglages.setdefault("touches", {})

    def _enregistrer(self):
        self.app.entrees.appliquer_perso(self._perso())
        self.app.enregistrer()

    def _assigner(self, action, code, nom):
        """But : donner une touche à une action (échange si elle était déjà prise)."""
        profil = self._profil()
        perso = self._perso().setdefault(profil, {})
        ancien = {"code": self.app.entrees.touches[profil][action][0],
                  "nom": nom_commande(self._perso(), profil, action)}
        for autre, _, _ in config.COMMANDES[profil]:
            if autre != action and code in self.app.entrees.touches[profil].get(autre, []):
                perso[autre] = ancien
                self.message = f"ECHANGE AVEC {dict((c, l) for c, l, _ in config.COMMANDES[profil])[autre]}"
        perso[action] = {"code": code, "nom": nom}
        self._enregistrer()

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        entrees = self.app.entrees
        lignes = self._lignes()
        if self.attente:
            if entrees.derniere_touche is not None:
                code, nom = entrees.derniere_touche
                self.attente = False
                if code == pygame.KSCAN_ESCAPE:
                    self.message = "ANNULE"
                elif code in TOUCHES_INTERDITES:
                    self.message = "TOUCHE RESERVEE"
                    self.app.audio.jouer("metal")
                else:
                    self.message = ""
                    self._assigner(lignes[self.indice][0], code, nom)
                    self.app.audio.jouer("menu_ok")
            return
        if entrees.vient_d_appuyer("retour") or entrees.vient_d_appuyer("pause"):
            self.app.audio.jouer("menu_ok")
            self.app.depiler()
            return
        ancien = (self.onglet, self.indice)
        if entrees.vient_d_appuyer("gauche"):
            self.onglet = (self.onglet - 1) % len(PROFILS)
        if entrees.vient_d_appuyer("droite"):
            self.onglet = (self.onglet + 1) % len(PROFILS)
        lignes = self._lignes()
        self.indice = min(self.indice, len(lignes) - 1)
        if entrees.vient_d_appuyer("haut"):
            self.indice = (self.indice - 1) % len(lignes)
        if entrees.vient_d_appuyer("bas"):
            self.indice = (self.indice + 1) % len(lignes)
        if (self.onglet, self.indice) != ancien:
            self.app.audio.jouer("menu_nav")
            self.message = ""
        if entrees.vient_d_appuyer("valider"):
            action, libelle, _ = lignes[self.indice]
            if libelle == "RETOUR":
                self.app.depiler()
            elif libelle == "PAR DEFAUT":
                self._perso().pop(self._profil(), None)
                self._enregistrer()
                self.message = "TOUCHES PAR DEFAUT REMISES"
            else:
                self.attente = True
                self.message = ""
            self.app.audio.jouer("menu_ok")

    def dessiner(self, image):
        voile(image, 225)
        cadre = pygame.Rect(0, 0, 820, 600)
        cadre.center = (config.LARGEUR / 2, config.HAUTEUR / 2)
        _, _, couleur = PROFILS[self.onglet]
        panneau(image, cadre, couleur)
        dessiner_texte(image, "COMMANDES", cadre.centerx, cadre.y + 40, 5, couleur)
        for i, (_, nom, teinte) in enumerate(PROFILS):
            onglet = pygame.Rect(0, 0, 200, 36)
            onglet.center = (cadre.centerx + (i - 1) * 220, cadre.y + 92)
            choisi = i == self.onglet
            pygame.draw.rect(image, teinte if choisi else (40, 20, 70), onglet,
                             0 if choisi else 2, border_radius=8)
            dessiner_texte(image, nom, onglet.centerx, onglet.centery, 2,
                           (20, 0, 30) if choisi else teinte, lueur=False)
        perso = self.app.reglages.get("touches", {})
        for i, (action, libelle, _) in enumerate(self._lignes()):
            y = cadre.y + 142 + i * 34
            choisi = i == self.indice
            ligne = pygame.Rect(cadre.x + 60, y - 15, cadre.w - 120, 30)
            if choisi:
                lueur = halo_rect(ligne.w, ligne.h, attenuer(couleur, 0.6), rayon=6)
                image.blit(lueur, (ligne.x - 16, ligne.y - 16), special_flags=pygame.BLEND_RGB_ADD)
                pygame.draw.rect(image, (40, 15, 70), ligne, border_radius=6)
            if action is None:
                dessiner_texte(image, libelle, cadre.centerx, y, 2, couleur if choisi else config.BLANC,
                               lueur=False)
                continue
            dessiner_texte(image, libelle, ligne.x + 20, y, 2, config.BLANC, ancrage="gauche",
                           lueur=False)
            if choisi and self.attente:
                texte, teinte = "APPUIE SUR UNE TOUCHE...", config.AMBRE
            else:
                texte = nom_commande(perso, self._profil(), action)
                teinte = couleur if self._profil() in perso and action in perso[self._profil()] \
                    else (190, 170, 230)
            dessiner_texte(image, texte, ligne.right - 20, y, 2, teinte, ancrage="droite", lueur=False)
        if self.message:
            dessiner_texte(image, self.message, cadre.centerx, cadre.bottom - 78, 2, config.AMBRE,
                           lueur=False)
        manette = "MANETTE BRANCHEE : " if self.app.entrees.manette_branchee() else "MANETTE : "
        dessiner_texte(image, manette + "STICK  A LANCER  X CHOISIR  Y POUVOIR  B OVERDRIVE",
                       cadre.centerx, cadre.bottom - 50, 2, (150, 120, 200), lueur=False)
        dessiner_texte(image, "←→ : JOUEUR   ↑↓ : ACTION   ENTREE : CHANGER   ECHAP : RETOUR",
                       cadre.centerx, cadre.bottom - 22, 2, (150, 120, 200), lueur=False)
