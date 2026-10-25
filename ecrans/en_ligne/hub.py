# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Menu « EN LIGNE » : parties en ligne, joueurs, classements mondiaux,
    profil, couleur du joueur, skin de raquette (avec aperçu), déconnexion.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import math

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from reseau.profil import (COULEURS as LISTE_COULEURS, niveau_pour, xp_pour_niveau, SKINS,
                           SKINS_PAR_CODE, condition_lisible)
from ecrans.base import MenuVertical
from ecrans.hud import panneau, barre
from ecrans.en_ligne.commun import EcranEnLigneBase, couleur_profil, GRIS


class EcranHub(EcranEnLigneBase):
    """Menu principal en ligne."""

    def __init__(self, app):
        super().__init__(app)
        self.menu = MenuVertical([], config.LARGEUR / 2, 316, 3, 44)
        self.statut = ""
        self.apercu = self._creer_apercu()
        self._construire()

    def _creer_apercu(self):
        """Raquette de démonstration qui montre le skin choisi."""
        from jeu.joueur import Joueur
        from jeu.raquette import Raquette
        joueur = Joueur(1, "solo", "J1")
        raquette = Raquette(960, 1220, 520, joueur=joueur)
        joueur.raquette = raquette
        return joueur

    def entrer(self):
        self.app.en_ligne.verifier_session(self._session)

    def _session(self, resultat):
        if resultat["code"] == 401:
            from ecrans.en_ligne.connexion import EcranConnexion
            self.app.remplacer(EcranConnexion(self.app))
        elif not resultat["ok"]:
            self.statut = resultat["erreur"]

    def _construire(self):
        indice = self.menu.indice
        self.menu.options = [
            ("PARTIES EN LIGNE", self._parties),
            ("JOUEURS", self._joueurs),
            ("CLASSEMENTS MONDIAUX", self._classements),
            ("MON PROFIL", self._profil),
            (f"COULEUR : {self.app.en_ligne.couleur.upper()}", self._couleur),
            (f"SKIN : {SKINS_PAR_CODE.get(self.app.en_ligne.skin_actif(), SKINS[0])['nom']}",
             lambda: self._skin(1), self._skin),
            ("SE DECONNECTER", self._deconnecter),
            ("RETOUR", self._retour),
        ]
        self.menu.indice = indice

    def _parties(self):
        infos = self.app.en_ligne.mise_a_jour_requise()
        if infos:
            from ecrans.mise_a_jour import EcranMiseAJour
            self.app.empiler(EcranMiseAJour(self.app, infos))
            return
        if self.app.en_ligne.protege():
            self.statut = "VERSION DE TEST : PAS DE PARTIE EN LIGNE SUR LE VRAI SERVEUR"
            self.app.audio.jouer("metal")
            return
        from ecrans.en_ligne.salons import EcranSalons
        self.app.remplacer(EcranSalons(self.app))

    def _joueurs(self):
        from ecrans.en_ligne.joueurs import EcranJoueurs
        self.app.remplacer(EcranJoueurs(self.app))

    def _classements(self):
        from ecrans.en_ligne.classements import EcranClassementsMondiaux
        self.app.remplacer(EcranClassementsMondiaux(self.app))

    def _profil(self):
        from ecrans.en_ligne.joueurs import EcranProfil
        self.app.remplacer(EcranProfil(self.app, self.app.en_ligne.pseudo))

    def _couleur(self):
        actuelle = self.app.en_ligne.couleur
        suivante = LISTE_COULEURS[(LISTE_COULEURS.index(actuelle) + 1) % len(LISTE_COULEURS)] \
            if actuelle in LISTE_COULEURS else LISTE_COULEURS[0]
        self.app.en_ligne.changer_couleur(suivante, lambda r: self._construire())
        self.app.en_ligne.couleur = suivante
        self._construire()

    def _skin(self, sens):
        en_ligne = self.app.en_ligne
        liste = [s["code"] for s in SKINS if s["code"] in en_ligne.skins] or ["neon"]
        actuel = en_ligne.skin_actif()
        indice = liste.index(actuel) if actuel in liste else 0
        suivant = liste[(indice + sens) % len(liste)]
        if suivant != actuel:
            en_ligne.changer_skin(suivant, lambda r: self._construire())
            self.app.audio.jouer("menu_nav")
        self._construire()

    def _deconnecter(self):
        from ecrans.titre import EcranTitre
        self.app.en_ligne.se_deconnecter()
        self.app.remplacer(EcranTitre(self.app))

    def _retour(self):
        from ecrans.titre import EcranTitre
        self.app.remplacer(EcranTitre(self.app))

    def _dessiner_apercu(self, image):
        """Panneau à droite : la raquette avec le skin choisi, et le prochain à débloquer."""
        en_ligne = self.app.en_ligne
        cadre = pygame.Rect(950, 300, 300, 230)
        panneau(image, cadre, config.ROSE)
        dessiner_texte(image, "SKIN", cadre.centerx, cadre.y + 24, 2, GRIS, lueur=False)
        skin = SKINS_PAR_CODE.get(en_ligne.skin_actif(), SKINS[0])
        joueur = self.apercu
        if joueur.skin != skin["code"]:
            joueur.appliquer_skin(skin["code"])
        raquette = joueur.raquette
        raquette.x = cadre.centerx + math.sin(self.temps * 1.8) * 70
        raquette.y = cadre.y + 120
        raquette.dessiner(image, self.temps)
        dessiner_texte(image, skin["nom"], cadre.centerx, cadre.y + 170, 3, joueur.couleur_bord)
        debloques = sum(1 for s in SKINS if s["code"] in en_ligne.skins)
        dessiner_texte(image, f"{debloques} / {len(SKINS)} DEBLOQUES", cadre.centerx,
                       cadre.y + 206, 2, GRIS, lueur=False)
        prochain = next((s for s in SKINS if s["code"] not in en_ligne.skins), None)
        if prochain is not None:
            dessiner_texte(image, f"PROCHAIN : {prochain['nom']}", cadre.centerx, cadre.bottom + 22,
                           2, config.AMBRE, lueur=False)
            dessiner_texte(image, condition_lisible(prochain), cadre.centerx, cadre.bottom + 46, 2,
                           GRIS, lueur=False)

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        if self.app.entrees.vient_d_appuyer("retour"):
            self._retour()
            return
        self.menu.mettre_a_jour(dt, self.app.entrees, self.app.audio)

    def dessiner(self, image):
        self.dessiner_fond(image)
        en_ligne = self.app.en_ligne
        couleur = couleur_profil(en_ligne.couleur)
        cadre = pygame.Rect(0, 0, 620, 170)
        cadre.midtop = (config.LARGEUR / 2, 100)
        panneau(image, cadre, couleur)
        dessiner_texte(image, en_ligne.pseudo.upper(), cadre.centerx, cadre.y + 46, 6, couleur)
        niveau = niveau_pour(en_ligne.xp)
        debut, fin = xp_pour_niveau(niveau), xp_pour_niveau(niveau + 1)
        dessiner_texte(image, f"RANG {niveau}", cadre.centerx, cadre.y + 100, 3, config.AMBRE)
        barre(image, pygame.Rect(cadre.x + 80, cadre.y + 126, cadre.w - 160, 10),
              (en_ligne.xp - debut) / max(1, fin - debut), config.AMBRE)
        dessiner_texte(image, f"{en_ligne.xp - debut} / {fin - debut} XP AVANT LE RANG {niveau + 1}",
                       cadre.centerx, cadre.y + 150, 2,
                       GRIS, lueur=False)
        self.menu.dessiner(image)
        self._dessiner_apercu(image)
        attente = len(self.app.donnees.get("a_envoyer", []))
        bas = self.statut or (f"{attente} PARTIE(S) EN ATTENTE D'ENVOI" if attente else "")
        if bas:
            dessiner_texte(image, bas, config.LARGEUR / 2, config.HAUTEUR - 60, 2,
                           config.ROSE, lueur=False)
        self.pied(image, "ENTREE : CHOISIR    ECHAP : RETOUR")
