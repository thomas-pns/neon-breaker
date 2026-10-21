# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Connexion et création de compte (pseudo + mot de passe). Tab ou
    flèches pour changer de champ, Entrée pour valider, Échap pour revenir.
    Si aucune adresse de serveur n'est connue (jeu lancé depuis le code
    source), un troisième champ permet de la saisir.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from moteur.version import adresse_serveur
from ecrans.hud import panneau
from ecrans.en_ligne.commun import EcranEnLigneBase, ChampTexte, CARACTERES_PSEUDO, GRIS


class EcranConnexion(EcranEnLigneBase):
    """Attributs : champs (list de ChampTexte), focus (int), inscription (bool)."""

    def __init__(self, app, inscription=False):
        super().__init__(app)
        self.inscription = inscription
        self.pseudo = ChampTexte("PSEUDO", app.en_ligne.pseudo, maximum=12,
                                 autorises=CARACTERES_PSEUDO)
        self.mdp = ChampTexte("MOT DE PASSE", masque=True, maximum=32)
        self.champs = [self.pseudo, self.mdp]
        self.adresse = None
        if not adresse_serveur(app.reglages):
            self.adresse = ChampTexte("ADRESSE DU SERVEUR (HTTPS://...)", maximum=60)
            self.champs.append(self.adresse)
        self.boutons = []
        self.focus = 0
        self.message = ""
        self.couleur_message = config.ROUGE
        self.en_cours = False

    def nb_elements(self):
        return len(self.champs) + 2

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        entrees = self.app.entrees
        appuis = entrees.appuis
        if pygame.KSCAN_ESCAPE in appuis:
            from ecrans.titre import EcranTitre
            self.app.remplacer(EcranTitre(self.app))
            return
        if pygame.KSCAN_TAB in appuis or pygame.KSCAN_DOWN in appuis:
            self.focus = (self.focus + 1) % self.nb_elements()
            self.app.audio.jouer("menu_nav")
        if pygame.KSCAN_UP in appuis:
            self.focus = (self.focus - 1) % self.nb_elements()
            self.app.audio.jouer("menu_nav")
        if 1 in entrees.clics:
            for i, element in enumerate(self.champs + self.boutons):
                if element.rect.collidepoint(entrees.souris):
                    self.focus = i
                    if i >= len(self.champs):
                        self.activer_bouton(i - len(self.champs))
        if self.focus < len(self.champs):
            self.champs[self.focus].saisir(entrees)
        valider = pygame.KSCAN_RETURN in appuis or pygame.KSCAN_KP_ENTER in appuis \
            or ("menu", "valider") in entrees.forcees
        if valider:
            if self.focus < len(self.champs):
                if self.focus < len(self.champs) - 1:
                    self.focus += 1
                else:
                    self.envoyer()
            else:
                self.activer_bouton(self.focus - len(self.champs))

    def activer_bouton(self, indice):
        if indice == 0:
            self.envoyer()
        else:
            self.inscription = not self.inscription
            self.message = ""
            self.app.audio.jouer("menu_nav")

    def envoyer(self):
        if self.en_cours:
            return
        pseudo, mdp = self.pseudo.valeur.strip(), self.mdp.valeur
        if self.adresse is not None:
            adresse = self.adresse.valeur.strip().rstrip("/")
            if not adresse.startswith(("http://", "https://")):
                self.message = "L'ADRESSE DOIT COMMENCER PAR HTTPS://"
                return
            self.app.reglages["serveur"] = adresse
            self.app.enregistrer()
        if len(pseudo) < 3:
            self.message = "PSEUDO : 3 CARACTERES MINIMUM"
            return
        if len(mdp) < 6:
            self.message = "MOT DE PASSE : 6 CARACTERES MINIMUM"
            return
        self.en_cours = True
        self.message = "CONNEXION..."
        self.couleur_message = config.CYAN
        self.app.audio.jouer("menu_ok")
        self.app.en_ligne.se_connecter(pseudo, mdp, self.inscription, self.reponse)

    def reponse(self, resultat):
        self.en_cours = False
        if resultat["ok"]:
            from ecrans.en_ligne.hub import EcranHub
            self.app.notifier(f"BIENVENUE {self.app.en_ligne.pseudo.upper()} !", "CYAN")
            self.app.remplacer(EcranHub(self.app))
        else:
            self.message = resultat["erreur"].upper()[:48]
            self.couleur_message = config.ROUGE
            self.app.audio.jouer("metal")

    def dessiner(self, image):
        self.dessiner_fond(image, "CREER UN COMPTE" if self.inscription else "CONNEXION")
        cadre = pygame.Rect(0, 0, 640, 170 + 90 * len(self.champs))
        cadre.midtop = (config.LARGEUR / 2, 110)
        panneau(image, cadre, config.CYAN)
        y = cadre.y + 60
        for i, champ in enumerate(self.champs):
            champ.dessiner(image, cadre.centerx, y, 520, self.focus == i, self.temps)
            y += 90
        libelles = ["CREER LE COMPTE" if self.inscription else "SE CONNECTER",
                    "J'AI DEJA UN COMPTE" if self.inscription else "CREER UN COMPTE"]
        self.boutons = []
        for k, libelle in enumerate(libelles):
            choisi = self.focus == len(self.champs) + k
            rect = pygame.Rect(0, 0, 250, 48)
            rect.center = (cadre.centerx + (k * 2 - 1) * 135, y + 20)
            pygame.draw.rect(image, config.AMBRE if choisi else (60, 30, 90), rect,
                             0 if choisi else 2, border_radius=8)
            dessiner_texte(image, libelle, rect.centerx, rect.centery, 2,
                           (20, 0, 30) if choisi else config.AMBRE, lueur=False)
            bouton = ChampTexte("")
            bouton.rect = rect
            self.boutons.append(bouton)
        if self.message:
            dessiner_texte(image, self.message, config.LARGEUR / 2, cadre.bottom + 30, 2,
                           self.couleur_message, lueur=False)
        if self.inscription:
            dessiner_texte(image, "PAS D'E-MAIL : NOTEZ BIEN VOTRE MOT DE PASSE",
                           config.LARGEUR / 2, cadre.bottom + 64, 2, GRIS, lueur=False)
        self.pied(image, "TAB / ↑↓ : CHAMP    ENTREE : VALIDER    ECHAP : RETOUR")
