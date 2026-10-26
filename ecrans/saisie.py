# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Saisie du nom en 3 lettres, façon borne d'arcade : flèches haut/bas
    pour changer la lettre, gauche/droite pour changer de case, ou taper
    directement au clavier ; Entrée pour valider.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Saisie à la manette.
"""

import math
import unicodedata

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from ecrans.base import EcranBase, voile
from ecrans.hud import panneau

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "


def nom_par_defaut(app, numero):
    """
    But : choisir le nom de record pre-rempli d'un joueur.
    Entrees : app (Application), numero (int 1 ou 2). Sortie : (str) nom de 3 caracteres.
    """
    reglage = app.reglages.get(f"nom_j{numero}", "")
    if reglage:
        nom = "".join(c for c in str(reglage).upper() if c in ALPHABET)[:3]
        return nom.ljust(3)
    if numero == 1:
        pseudo = getattr(getattr(app, "en_ligne", None), "pseudo", None)
        if pseudo:
            normalise = unicodedata.normalize("NFKD", pseudo.upper())
            sans_accents = "".join(c for c in normalise if not unicodedata.combining(c))
            return "".join(c for c in sans_accents if c in ALPHABET)[:3].ljust(3)
        return str(app.donnees.get("dernier_nom", "AAA"))[:3].ljust(3)
    return str(app.donnees.get("dernier_nom_j2", "BBB"))[:3].ljust(3)


class EcranSaisieNom(EcranBase):
    """Attributs : lettres (list de 3 indices dans ALPHABET), case (int)."""

    vertical = True               # dessiné aussi au format vertical (téléphone)

    def musique(self):
        """But : demander le silence pendant la saisie. Entree(s) : aucune. Sortie : None."""
        return None

    def __init__(self, app, resultat, fabrique, reglage=None):
        """
        But : initialiser la saisie d'un score ou d'un nom de reglage.
        Entrees : app, resultat, fabrique, reglage. Sortie : aucune.
        """
        super().__init__(app)
        self.resultat = resultat
        self.fabrique = fabrique
        self.reglage = reglage
        self.joueur = 1
        self.nom_j1 = ""
        self.nom_j2 = ""
        dernier = nom_par_defaut(app, 1)
        self.lettres = [ALPHABET.index(c) if c in ALPHABET else 0 for c in dernier[:3]]
        self.case = 0

    def reprendre(self):
        """
        But : ignorer la touche qui vient de fermer la saisie superposee.
        Entree(s) : aucune. Sortie : aucune.
        """
        self.app.entrees.debut_image()

    def entrer(self):
        """But : jouer le son d'entree. Entree(s) : aucune. Sortie : aucune."""
        self.app.audio.jouer("victoire")

    def mettre_a_jour(self, dt):
        """
        But : traiter les commandes de saisie et de validation.
        Entree(s) : dt (float). Sortie : aucune.
        """
        super().mettre_a_jour(dt)
        entrees = self.app.entrees
        audio = self.app.audio
        if self.reglage is not None and entrees.vient_d_appuyer("retour"):
            self.app.audio.jouer("menu_ok")
            self.app.depiler()
            return
        if pygame.KSCAN_UP in entrees.appuis:
            self.lettres[self.case] = (self.lettres[self.case] - 1) % len(ALPHABET)
            audio.jouer("menu_nav")
        if pygame.KSCAN_DOWN in entrees.appuis:
            self.lettres[self.case] = (self.lettres[self.case] + 1) % len(ALPHABET)
            audio.jouer("menu_nav")
        if pygame.KSCAN_LEFT in entrees.appuis:
            self.case = max(0, self.case - 1)
        if pygame.KSCAN_RIGHT in entrees.appuis:
            self.case = min(2, self.case + 1)
        for caractere in entrees.texte.upper():
            if caractere in ALPHABET.strip():
                self.lettres[self.case] = ALPHABET.index(caractere)
                self.case = min(2, self.case + 1)
                audio.jouer("menu_nav")
        # Seules les flèches naviguent : les lettres servent à écrire le nom.
        valider = (pygame.KSCAN_RETURN in entrees.appuis or pygame.KSCAN_KP_ENTER in entrees.appuis
                   or ("menu", "valider") in entrees.forcees)
        if valider or 1 in entrees.clics:
            self._valider()

    def _valider(self):
        """
        But : enregistrer le reglage ou le nom du score saisi.
        Entree(s) : aucune. Sortie : aucune.
        """
        if self.reglage is not None:
            self.app.reglages[f"nom_j{self.reglage}"] = "".join(
                ALPHABET[i] for i in self.lettres)
            self.app.enregistrer()
            self.app.audio.jouer("menu_ok")
            self.app.depiler()
            return
        from ecrans.fin import EcranFin
        nom = "".join(ALPHABET[i] for i in self.lettres).strip() or "???"
        if self.resultat["mode"] == "coop":
            if self.joueur == 1:
                self.nom_j1 = nom
                self.joueur = 2
                self.lettres = [ALPHABET.index(c) for c in nom_par_defaut(self.app, 2)]
                self.case = 0
                self.app.audio.jouer("menu_ok")
                return
            self.nom_j2 = nom
            nom = f"{self.nom_j1.strip()}+{self.nom_j2.strip()}"
            self.app.donnees["dernier_nom_j2"] = self.nom_j2
        self.app.donnees["dernier_nom"] = self.nom_j1 if self.resultat["mode"] == "coop" else nom
        rang = self.app.ajouter_au_classement(self.resultat["mode"], nom,
                                              self.resultat["score"])
        self.app.audio.jouer("menu_ok")
        self.app.remplacer(EcranFin(self.app, self.resultat, self.fabrique, rang))

    def dessiner(self, image):
        """
        But : afficher le panneau et les trois caracteres a modifier.
        Entree(s) : image (Surface). Sortie : aucune.
        """
        self.app.fond.dessiner(image)
        voile(image, 150)
        cadre = pygame.Rect(0, 0, 640, 420)
        cadre.center = (config.LARGEUR / 2, config.HAUTEUR / 2)
        panneau(image, cadre, config.AMBRE)
        titre = (f"NOM DES RECORDS J{self.reglage}" if self.reglage is not None else
                 f"NOM DU JOUEUR {self.joueur}" if self.resultat["mode"] == "coop" else "TOP 10 !")
        dessiner_texte(image, titre, cadre.centerx, cadre.y + 56,
                       7 if titre == "TOP 10 !" else 5, config.AMBRE)
        if self.reglage is None:
            dessiner_texte(image, f"SCORE {self.resultat['score']:07d}", cadre.centerx,
                           cadre.y + 126, 3, config.BLANC)
        dessiner_texte(image, "ENTREZ VOTRE NOM", cadre.centerx,
                       cadre.y + (176 if self.reglage is None else 146), 2,
                       (170, 140, 220), lueur=False)
        for i, indice in enumerate(self.lettres):
            x = cadre.centerx + (i - 1) * 110
            y = cadre.y + (270 if self.reglage is None else 240)
            choisie = i == self.case
            couleur = config.CYAN if choisie else config.BLANC
            dessiner_texte(image, ALPHABET[indice] if ALPHABET[indice] != " " else "_",
                           x, y, 10, couleur)
            if choisie:
                decalage = math.sin(self.temps * 8) * 4
                dessiner_texte(image, "↑", x, y - 70 + decalage, 3, config.ROSE, lueur=False)
                dessiner_texte(image, "↓", x, y + 70 - decalage, 3, config.ROSE, lueur=False)
        dessiner_texte(image, "↑↓ LETTRE   ←→ CASE   ENTREE : VALIDER",
                       cadre.centerx, cadre.bottom - 30, 2, (170, 140, 220), lueur=False)
