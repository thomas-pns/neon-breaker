# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Écran BOUTIQUE (2.0, menu EN LIGNE) : la sélection du jour (2 skins et
    4 bannières, dont une en promotion), la boîte mystère et le solde de
    NEONS. Tout achat est décidé par le serveur ; l'écran ne fait que
    demander et afficher. Après un achat, Entrée équipe l'objet.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 25/10/2026
"""

import datetime
import math

import pygame

from moteur import config
from moteur.bannieres import dessiner_banniere, dessiner_piece
from moteur.police_pixel import dessiner_texte
from moteur.rendu import attenuer, halo_rect, melanger
from reseau.boutique import COULEURS_RARETES, MONNAIE, NOMS_RARETES, PRIX_BOITE
from ecrans.hud import panneau
from ecrans.en_ligne.commun import EcranEnLigneBase, GRIS

LARGEUR_CARTE, HAUTEUR_CARTE = 290, 190
COLONNES = 3
GAUCHE, HAUT = 70, 120
CASE_BOITE = 6                     # indice de la boîte mystère (après les 6 objets)


def temps_avant_minuit():
    """But : texte « 5 H 12 » jusqu'à la prochaine sélection (heure locale)."""
    maintenant = datetime.datetime.now()
    demain = (maintenant + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0,
                                                               microsecond=0)
    minutes = int((demain - maintenant).total_seconds() // 60)
    return f"{minutes // 60} H {minutes % 60:02d}"


class EcranBoutique(EcranEnLigneBase):
    """
    Boutique. Attributs : selection (list de dict), indice (int), etat
    ("chargement", "vitrine", "confirmer", "ouverture", "revele", "erreur"),
    message (str), gagne (dict : objet sorti de la boîte), apercus (dict code -> Joueur).
    """

    titre = "BOUTIQUE"

    def __init__(self, app):
        super().__init__(app)
        self.selection = []
        self.indice = 0
        self.etat = "chargement"
        self.message = ""
        self.gagne = None
        self.minuteur = 0.0
        self.apercus = {}
        self.en_attente = False

    def entrer(self):
        self.app.en_ligne.charger_boutique(self._recu_vitrine)

    def _recu_vitrine(self, resultat):
        if not resultat["ok"]:
            self.etat, self.message = "erreur", resultat["erreur"] or "BOUTIQUE INJOIGNABLE"
            return
        self.selection = resultat["donnees"]["selection"]
        self.etat = "vitrine"

    # --- Aperçus ----------------------------------------------------------------------

    def _apercu(self, code):
        """Raquette de démonstration (une par skin, pour garder sa traînée)."""
        if code not in self.apercus:
            from jeu.joueur import Joueur
            from jeu.raquette import Raquette
            joueur = Joueur(1, "solo", "J1")
            joueur.raquette = Raquette(0, config.LARGEUR, 0, joueur=joueur)
            joueur.appliquer_skin(code)
            self.apercus[code] = joueur
        return self.apercus[code]

    def _dessiner_objet(self, image, objet, centre, temps, largeur=230):
        """Aperçu d'un objet : bannière avec le pseudo, ou raquette au skin."""
        if objet["type"] == "banniere":
            rect = pygame.Rect(0, 0, largeur, 38)
            rect.center = centre
            dessiner_banniere(image, objet["code"], rect, temps)
            dessiner_texte(image, self.app.en_ligne.pseudo.upper(), rect.centerx, rect.centery, 2,
                           config.BLANC)
        else:
            raquette = self._apercu(objet["code"]).raquette
            raquette.x = centre[0] + math.sin(temps * 1.6) * 50
            raquette.y = centre[1] - raquette.hauteur / 2
            raquette.dessiner(image, temps)

    # --- Actions -------------------------------------------------------------------------

    def _objet_courant(self):
        return self.selection[self.indice] if self.indice < len(self.selection) else None

    def _valider(self):
        en_ligne = self.app.en_ligne
        if self.indice == CASE_BOITE:
            if en_ligne.neons < PRIX_BOITE:
                self._refus(f"IL FAUT {PRIX_BOITE} {MONNAIE}")
                return
            self.etat = "confirmer"
            return
        objet = self._objet_courant()
        if objet is None:
            return
        if objet.get("possede"):
            self._equiper(objet)
            return
        if en_ligne.neons < objet["prix"]:
            self._refus(f"IL TE MANQUE {objet['prix'] - en_ligne.neons} {MONNAIE}")
            return
        self.etat = "confirmer"

    def _refus(self, texte):
        self.message = texte
        self.minuteur = 2.5
        self.app.audio.jouer("metal")

    def _confirmer(self):
        if self.en_attente:
            return
        self.en_attente = True
        if self.indice == CASE_BOITE:
            self.etat, self.minuteur = "ouverture", 1.6
            self.gagne = None
            self.app.audio.jouer("menu_ok")
            self.app.en_ligne.ouvrir_boite(self._recu_boite)
        else:
            self.app.en_ligne.acheter(self._objet_courant()["code"], self._recu_achat)

    def _recu_achat(self, resultat):
        self.en_attente = False
        self.etat = "vitrine"
        if not resultat["ok"]:
            self._refus(resultat["erreur"] or "ACHAT REFUSE")
            return
        objet = self._objet_courant()
        objet["possede"] = True
        self.app.audio.jouer("succes")
        self.message = f"{objet['nom']} EST A TOI !  ENTREE : EQUIPER"
        self.minuteur = 4.0

    def _recu_boite(self, resultat):
        self.en_attente = False
        if not resultat["ok"]:
            self.etat = "vitrine"
            self._refus(resultat["erreur"] or "BOITE INDISPONIBLE")
            return
        self.gagne = resultat["donnees"]["objet"]
        for objet in self.selection:
            if objet["code"] == self.gagne["code"]:
                objet["possede"] = True

    def _equiper(self, objet):
        en_ligne = self.app.en_ligne
        if objet["type"] == "banniere":
            en_ligne.changer_banniere(objet["code"])
        else:
            en_ligne.changer_skin(objet["code"])
        self.app.audio.jouer("menu_ok")
        self.message = f"{objet['nom']} EQUIPE"
        self.minuteur = 2.5

    # --- Boucle ----------------------------------------------------------------------------

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        entrees = self.app.entrees
        self.minuteur = max(0.0, self.minuteur - dt)
        if self.etat == "ouverture":
            if self.minuteur <= 0 and self.gagne is not None:
                self.etat, self.minuteur = "revele", 0.0
                self.app.audio.jouer("succes")
            return
        if self.etat == "revele":
            if entrees.vient_d_appuyer("valider"):
                self._equiper(self.gagne)
                self.etat = "vitrine"
            elif entrees.vient_d_appuyer("retour"):
                self.etat = "vitrine"
            return
        if self.etat == "confirmer":
            if entrees.vient_d_appuyer("valider"):
                self._confirmer()
            elif entrees.vient_d_appuyer("retour"):
                self.etat = "vitrine"
            return
        if entrees.vient_d_appuyer("retour"):
            from ecrans.en_ligne.hub import EcranHub
            self.app.remplacer(EcranHub(self.app))
            return
        if self.etat != "vitrine":
            return
        ancien = self.indice
        if entrees.vient_d_appuyer("droite"):
            self.indice = CASE_BOITE if self.indice % COLONNES == COLONNES - 1 and \
                self.indice != CASE_BOITE else min(CASE_BOITE, self.indice + 1)
        if entrees.vient_d_appuyer("gauche"):
            self.indice = 2 if self.indice == CASE_BOITE else max(0, self.indice - 1)
        if entrees.vient_d_appuyer("bas") and self.indice < COLONNES:
            self.indice += COLONNES
        if entrees.vient_d_appuyer("haut") and COLONNES <= self.indice < CASE_BOITE:
            self.indice -= COLONNES
        if self.indice != ancien:
            self.app.audio.jouer("menu_nav")
        if entrees.vient_d_appuyer("valider"):
            self._valider()

    # --- Dessin ----------------------------------------------------------------------------

    def _rect_carte(self, i):
        if i == CASE_BOITE:
            return pygame.Rect(GAUCHE + COLONNES * (LARGEUR_CARTE + 20), HAUT,
                               240, 2 * HAUTEUR_CARTE + 20)
        return pygame.Rect(GAUCHE + (i % COLONNES) * (LARGEUR_CARTE + 20),
                           HAUT + (i // COLONNES) * (HAUTEUR_CARTE + 20),
                           LARGEUR_CARTE, HAUTEUR_CARTE)

    def _dessiner_carte(self, image, i, objet):
        rect = self._rect_carte(i)
        couleur = COULEURS_RARETES[objet["rarete"]]
        choisie = i == self.indice
        if choisie:
            lueur = halo_rect(rect.w, rect.h, attenuer(couleur, 0.9), rayon=10)
            image.blit(lueur, (rect.x - 16, rect.y - 16), special_flags=pygame.BLEND_RGB_ADD)
        panneau(image, rect, couleur if choisie else attenuer(couleur, 0.55))
        dessiner_texte(image, NOMS_RARETES[objet["rarete"]] + ("  SKIN" if objet["type"] == "skin"
                                                               else "  BANNIERE"),
                       rect.x + 14, rect.y + 20, 2, couleur, ancrage="gauche", lueur=False)
        self._dessiner_objet(image, objet, (rect.centerx, rect.y + 78), self.temps)
        dessiner_texte(image, objet["nom"], rect.centerx, rect.y + 122, 3, config.BLANC)
        if objet.get("possede"):
            dessiner_texte(image, "POSSEDE", rect.centerx, rect.bottom - 30, 3, config.VERT)
            return
        prix = rect.centerx + 14
        if objet.get("promo"):
            barre = dessiner_texte(image, str(objet["prix_normal"]), rect.x + 50, rect.bottom - 30,
                                   2, GRIS, lueur=False)
            pygame.draw.line(image, config.ROSE, (barre.x - 2, barre.centery),
                             (barre.right + 2, barre.centery), 2)
            etiquette = pygame.Rect(rect.right - 80, rect.y - 12, 72, 24)
            pygame.draw.rect(image, config.ROSE, etiquette, border_radius=4)
            dessiner_texte(image, "-30%", etiquette.centerx, etiquette.centery, 2, config.BLANC,
                           lueur=False)
        abordable = self.app.en_ligne.neons >= objet["prix"]
        zone = dessiner_texte(image, str(objet["prix"]), prix, rect.bottom - 30, 3,
                              config.CYAN if abordable else (150, 90, 120))
        dessiner_piece(image, (zone.x - 18, zone.centery), 10, self.temps)

    def _dessiner_boite(self, image):
        rect = self._rect_carte(CASE_BOITE)
        choisie = self.indice == CASE_BOITE
        couleur = COULEURS_RARETES["legendaire"]
        if choisie:
            lueur = halo_rect(rect.w, rect.h, attenuer(couleur, 0.9), rayon=10)
            image.blit(lueur, (rect.x - 16, rect.y - 16), special_flags=pygame.BLEND_RGB_ADD)
        panneau(image, rect, couleur if choisie else attenuer(couleur, 0.55))
        dessiner_texte(image, "BOITE", rect.centerx, rect.y + 34, 4, couleur)
        dessiner_texte(image, "MYSTERE", rect.centerx, rect.y + 72, 4, couleur)
        self._dessiner_cube(image, (rect.centerx, rect.y + 190), 56, self.temps, 0.0)
        for k, ligne in enumerate(("UN OBJET AU HASARD", "JAMAIS EN DOUBLE", "LEGENDAIRE : 5 %")):
            dessiner_texte(image, ligne, rect.centerx, rect.y + 286 + k * 22, 2,
                           config.AMBRE if k == 2 else GRIS, lueur=False)
        abordable = self.app.en_ligne.neons >= PRIX_BOITE
        zone = dessiner_texte(image, str(PRIX_BOITE), rect.centerx + 14, rect.bottom - 30, 3,
                              config.CYAN if abordable else (150, 90, 120))
        dessiner_piece(image, (zone.x - 18, zone.centery), 10, self.temps)

    def _dessiner_cube(self, image, centre, taille, temps, secousse):
        """Boîte mystère en néon : un cube qui flotte (et tremble à l'ouverture)."""
        cx = centre[0] + math.sin(temps * 40) * 6 * secousse
        cy = centre[1] + math.sin(temps * 2) * 6
        teinte = melanger(config.ROSE, config.CYAN, 0.5 + 0.5 * math.sin(temps * 2))
        demi = taille / 2
        face = pygame.Rect(0, 0, taille, taille)
        face.center = (cx - 8, cy + 8)
        dessus = [(face.x, face.y), (face.x + 16, face.y - 16), (face.right + 16, face.y - 16),
                  (face.right, face.y)]
        cote = [(face.right, face.y), (face.right + 16, face.y - 16),
                (face.right + 16, face.bottom - 16), (face.right, face.bottom)]
        pygame.draw.rect(image, (30, 10, 60), face)
        pygame.draw.polygon(image, (50, 20, 90), dessus)
        pygame.draw.polygon(image, (20, 5, 45), cote)
        for forme in (dessus, cote):
            pygame.draw.polygon(image, teinte, forme, 2)
        pygame.draw.rect(image, teinte, face, 2)
        dessiner_texte(image, "?", face.centerx, face.centery, int(demi // 8) + 1, config.BLANC)

    def _dessiner_entete(self, image):
        en_ligne = self.app.en_ligne
        zone = dessiner_texte(image, f"{en_ligne.neons}", config.LARGEUR - 40, 80, 4, config.CYAN,
                              ancrage="droite")
        dessiner_piece(image, (zone.x - 26, zone.centery), 14, self.temps)
        dessiner_texte(image, f"NOUVELLE SELECTION DANS {temps_avant_minuit()}", GAUCHE, 88, 2, GRIS,
                       ancrage="gauche", lueur=False)

    def _dessiner_superpose(self, image, titre, lignes, couleur):
        voile = pygame.Surface(image.get_size())
        voile.fill((5, 0, 15))
        voile.set_alpha(190)
        image.blit(voile, (0, 0))
        cadre = pygame.Rect(0, 0, 640, 300)
        cadre.center = (config.LARGEUR / 2, config.HAUTEUR / 2)
        panneau(image, cadre, couleur)
        dessiner_texte(image, titre, cadre.centerx, cadre.y + 44, 4, couleur)
        return cadre

    def dessiner(self, image):
        self.dessiner_fond(image)
        if self.etat in ("chargement", "erreur"):
            texte = "CHARGEMENT..." if self.etat == "chargement" else self.message
            dessiner_texte(image, texte, config.LARGEUR / 2, config.HAUTEUR / 2, 3,
                           config.CYAN if self.etat == "chargement" else config.ROSE)
            self.pied(image, "ECHAP : RETOUR")
            return
        self._dessiner_entete(image)
        for i, objet in enumerate(self.selection[:CASE_BOITE]):
            self._dessiner_carte(image, i, objet)
        self._dessiner_boite(image)
        if self.message and self.minuteur > 0:
            dessiner_texte(image, self.message, config.LARGEUR / 2, 572, 3, config.AMBRE)
        else:
            objet = self._objet_courant()
            aide = ("ENTREE : OUVRIR UNE BOITE" if self.indice == CASE_BOITE else
                    "ENTREE : EQUIPER" if objet and objet.get("possede") else "ENTREE : ACHETER")
            dessiner_texte(image, aide, config.LARGEUR / 2, 572, 2, GRIS, lueur=False)
        dessiner_texte(image, f"GAGNE DES {MONNAIE} : CAMPAGNE, BOSS, DEFIS, SERIES, SUCCES, EN LIGNE",
                       config.LARGEUR / 2, 620, 2, (130, 110, 190), lueur=False)

        if self.etat == "confirmer":
            if self.indice == CASE_BOITE:
                cadre = self._dessiner_superpose(image, "BOITE MYSTERE ?", [], config.AMBRE)
                self._dessiner_cube(image, (cadre.centerx, cadre.y + 140), 50, self.temps, 0)
                prix = PRIX_BOITE
            else:
                objet = self._objet_courant()
                cadre = self._dessiner_superpose(image, f"ACHETER {objet['nom']} ?", [],
                                                 COULEURS_RARETES[objet["rarete"]])
                self._dessiner_objet(image, objet, (cadre.centerx, cadre.y + 130), self.temps, 300)
                prix = objet["prix"]
            zone = dessiner_texte(image, f"{prix}", cadre.centerx + 14, cadre.y + 212, 3, config.CYAN)
            dessiner_piece(image, (zone.x - 18, zone.centery), 10, self.temps)
            dessiner_texte(image, "ENTREE : OUI      ECHAP : NON", cadre.centerx, cadre.bottom - 30,
                           2, GRIS, lueur=False)
        elif self.etat == "ouverture":
            cadre = self._dessiner_superpose(image, "OUVERTURE...", [], config.AMBRE)
            secousse = min(1.0, (1.6 - self.minuteur) / 1.2)
            self._dessiner_cube(image, (cadre.centerx, cadre.y + 160), 60 + 20 * secousse,
                                self.temps, secousse)
        elif self.etat == "revele" and self.gagne:
            couleur = COULEURS_RARETES[self.gagne["rarete"]]
            cadre = self._dessiner_superpose(image, NOMS_RARETES[self.gagne["rarete"]] + " !", [],
                                             couleur)
            rayons = pygame.Surface((cadre.w - 8, 120), pygame.SRCALPHA)
            for k in range(12):
                angle = self.temps * 0.8 + k * math.pi / 6
                fin = (rayons.get_width() / 2 + math.cos(angle) * 400,
                       60 + math.sin(angle) * 400)
                pygame.draw.polygon(rayons, (*couleur, 40), [(rayons.get_width() / 2, 60), fin,
                                                            (fin[0] + 40, fin[1] + 40)])
            image.blit(rayons, (cadre.x + 4, cadre.y + 74))
            self._dessiner_objet(image, self.gagne, (cadre.centerx, cadre.y + 134), self.temps, 300)
            dessiner_texte(image, self.gagne["nom"], cadre.centerx, cadre.y + 200, 4, config.BLANC)
            dessiner_texte(image, "ENTREE : EQUIPER      ECHAP : PLUS TARD", cadre.centerx,
                           cadre.bottom - 30, 2, GRIS, lueur=False)
        self.pied(image, "FLECHES : CHOISIR    ENTREE : VALIDER    ECHAP : RETOUR")
