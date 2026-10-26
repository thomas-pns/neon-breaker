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

LARGEUR_CARTE, HAUTEUR_CARTE = 205, 236
COLONNES = 3
GAUCHE, HAUT = 590, 104                # sélection du jour à droite (2.1)
VEDETTE = pygame.Rect(40, 104, 520, 500)
CASE_BOITE = 6                     # indice de la boîte mystère (après les 6 objets)


def disposition():
    """
    But : (vedette, gauche, haut) : en paysage, la vedette à gauche et la sélection à
    droite ; au format vertical (téléphone), la vedette en haut et la sélection dessous.
    """
    from ecrans.menus import est_vertical, haut_contenu
    if not est_vertical():
        return VEDETTE, GAUCHE, HAUT
    haut = haut_contenu() + 16
    vedette = pygame.Rect(20, haut, config.LARGEUR - 40, 480)
    largeur = COLONNES * LARGEUR_CARTE + (COLONNES - 1) * 15
    return vedette, (config.LARGEUR - largeur) // 2, vedette.bottom + 52


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

    vertical = True               # dessiné aussi au format vertical (téléphone)

    titre = "BOUTIQUE"
    onglet = "BOUTIQUE"

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
            rect = pygame.Rect(0, 0, largeur, max(38, largeur // 5))
            rect.center = centre
            dessiner_banniere(image, objet["code"], rect, temps)
            dessiner_texte(image, self.app.en_ligne.pseudo.upper(), rect.centerx, rect.centery,
                           2 if rect.h < 60 else 4, config.BLANC)
        else:
            raquette = self._apercu(objet["code"]).raquette
            if largeur > 300:                 # vedette : raquette agrandie x2
                toile = pygame.Surface((260, 60))
                toile.fill((0, 0, 0))
                raquette.x = 130 + math.sin(temps * 1.6) * 20
                raquette.y = 30 - raquette.hauteur / 2
                raquette.dessiner(toile, temps)
                grande = pygame.transform.scale(toile, (520, 120))
                image.blit(grande, grande.get_rect(center=centre), special_flags=pygame.BLEND_RGB_ADD)
                return
            raquette.x = centre[0] + math.sin(temps * 1.6) * min(50, largeur / 8)
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
            self.objet_achete = self._objet_courant()
            self.app.en_ligne.acheter(self.objet_achete["code"], self._recu_achat)

    def _recu_achat(self, resultat):
        self.en_attente = False
        self.etat = "vitrine"
        if not resultat["ok"]:
            self._refus(resultat["erreur"] or "ACHAT REFUSE")
            return
        objet = self.objet_achete
        objet["possede"] = True
        self.app.audio.jouer("succes")
        self.message = f"{objet['nom']} EST A TOI !  ENTREE : EQUIPER"
        self.minuteur = 4.0

    def _recu_historique(self, resultat):
        if resultat["ok"] and self.historique is not None:
            self.historique = resultat["donnees"]["mouvements"] or [{"montant": 0, "raison": "AUCUN MOUVEMENT",
                                                                     "le": 0}]

    def _dessiner_historique(self, image):
        from ecrans.menus import carte
        cadre = pygame.Rect(0, 0, 720, 500)
        cadre.center = (config.LARGEUR / 2, 380)
        voile = pygame.Surface(image.get_size(), pygame.SRCALPHA)
        voile.fill((5, 0, 15, 190))
        image.blit(voile, (0, 0))
        carte(image, cadre, config.CYAN, True, alpha=245)
        dessiner_texte(image, f"HISTORIQUE DES {MONNAIE}", cadre.centerx, cadre.y + 36, 4, config.CYAN)
        if not self.historique:
            dessiner_texte(image, "CHARGEMENT...", cadre.centerx, cadre.centery, 2, GRIS, lueur=False)
        for k, ligne in enumerate(self.historique[:12]):
            y = cadre.y + 86 + k * 32
            date = datetime.datetime.fromtimestamp(ligne["le"]).strftime("%d/%m") if ligne["le"] else ""
            dessiner_texte(image, date, cadre.x + 30, y, 2, GRIS, ancrage="gauche", lueur=False)
            dessiner_texte(image, str(ligne["raison"])[:30], cadre.x + 110, y, 2, config.BLANC,
                           ancrage="gauche", lueur=False)
            montant = ligne["montant"]
            if montant:
                dessiner_texte(image, f"{'+' if montant > 0 else ''}{montant}", cadre.right - 30, y, 2,
                               config.VERT if montant > 0 else config.ROSE, ancrage="droite", lueur=False)
        dessiner_texte(image, "H OU ECHAP : FERMER", cadre.centerx, cadre.bottom - 24, 2, GRIS, lueur=False)

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
            elif entrees.vient_d_appuyer("retour") and not self.en_attente:
                self.etat = "vitrine"
            return
        if (pygame.KSCAN_H in entrees.appuis or "historique" in entrees.appuis_tactiles) \
                and self.etat == "vitrine":
            self.historique = None if getattr(self, "historique", None) is not None else []
            if self.historique == []:
                self.app.en_ligne.appeler("GET", "/api/moi/historique", rappel=self._recu_historique)
            return
        if entrees.vient_d_appuyer("retour"):
            if getattr(self, "historique", None) is not None:
                self.historique = None
                return
            self.retour_accueil()
            return
        if self.etat != "vitrine" or getattr(self, "historique", None) is not None:
            return
        ancien = self.indice
        if entrees.vient_d_appuyer("droite"):
            if self.indice == CASE_BOITE:
                self.indice = 0
            elif self.indice % COLONNES < COLONNES - 1:
                self.indice += 1
        if entrees.vient_d_appuyer("gauche"):
            if self.indice != CASE_BOITE:
                self.indice = CASE_BOITE if self.indice % COLONNES == 0 else self.indice - 1
        if entrees.vient_d_appuyer("bas") and self.indice < COLONNES:
            self.indice += COLONNES
        if entrees.vient_d_appuyer("haut") and COLONNES <= self.indice < CASE_BOITE:
            self.indice -= COLONNES
        if entrees.souris_bougee:
            for i in list(range(len(self.selection[:CASE_BOITE]))) + [CASE_BOITE]:
                if self._rect_carte(i).collidepoint(entrees.souris):
                    self.indice = i
        if self.indice != ancien:
            self.app.audio.jouer("menu_nav")
        clic = 1 in entrees.clics and self._rect_carte(self.indice).collidepoint(entrees.souris)
        if entrees.vient_d_appuyer("valider") or clic:
            self._valider()

    # --- Dessin ----------------------------------------------------------------------------

    def _rect_carte(self, i):
        vedette, gauche, haut = disposition()
        if i == CASE_BOITE:
            return vedette
        return pygame.Rect(gauche + (i % COLONNES) * (LARGEUR_CARTE + 15),
                           haut + (i // COLONNES) * (HAUTEUR_CARTE + 28),
                           LARGEUR_CARTE, HAUTEUR_CARTE)

    def _dessiner_carte(self, image, i, objet):
        from ecrans.menus import carte
        rect = self._rect_carte(i)
        couleur = COULEURS_RARETES[objet["rarete"]]
        choisie = i == self.indice
        carte(image, rect, couleur if choisie else attenuer(couleur, 0.8), choisie)
        dessiner_texte(image, NOMS_RARETES[objet["rarete"]] + ("  SKIN" if objet["type"] == "skin"
                                                               else "  BANNIERE"),
                       rect.centerx, rect.y + 22, 1, couleur, lueur=False)
        self._dessiner_objet(image, objet, (rect.centerx, rect.y + 82), self.temps, rect.w - 30)
        dessiner_texte(image, objet["nom"], rect.centerx, rect.y + 142, 2, config.BLANC)
        if objet.get("possede"):
            dessiner_texte(image, "POSSEDE", rect.centerx, rect.bottom - 34, 3, config.VERT)
            return
        if objet.get("promo"):
            barre = dessiner_texte(image, str(objet["prix_normal"]), rect.centerx, rect.bottom - 64,
                                   2, GRIS, lueur=False)
            pygame.draw.line(image, config.ROSE, (barre.x - 2, barre.centery),
                             (barre.right + 2, barre.centery), 2)
            etiquette = pygame.Rect(rect.right - 70, rect.y - 10, 62, 22)
            pygame.draw.rect(image, config.ROSE, etiquette, border_radius=4)
            dessiner_texte(image, "-30%", etiquette.centerx, etiquette.centery, 2, config.BLANC,
                           lueur=False)
        abordable = self.app.en_ligne.neons >= objet["prix"]
        zone = dessiner_texte(image, str(objet["prix"]), rect.centerx + 12, rect.bottom - 34, 3,
                              config.CYAN if abordable else (150, 90, 120))
        dessiner_piece(image, (zone.x - 16, zone.centery), 10, self.temps)

    def _vedette(self):
        """Objet légendaire mis en avant (le même toute la journée), à gagner dans la boîte."""
        if getattr(self, "_objet_vedette", None) is None:
            import random
            from reseau.boutique import tous_les_objets
            legendaires = [o for o in tous_les_objets() if o["rarete"] == "legendaire"]
            hasard = random.Random("vedette-" + datetime.date.today().isoformat())
            self._objet_vedette = hasard.choice(legendaires) if legendaires else None
        return self._objet_vedette

    def _dessiner_boite(self, image):
        from ecrans.menus import bouton, carte
        rect = disposition()[0]
        choisie = self.indice == CASE_BOITE
        couleur = COULEURS_RARETES["legendaire"]
        carte(image, rect, couleur if choisie else attenuer(couleur, 0.8), choisie)
        dessiner_texte(image, "EN VEDETTE", rect.x + 26, rect.y + 30, 2, GRIS, ancrage="gauche",
                       lueur=False)
        vedette = self._vedette()
        if vedette is not None:
            self._dessiner_objet(image, vedette, (rect.centerx, rect.y + 130), self.temps, rect.w - 80)
            dessiner_texte(image, vedette["nom"], rect.centerx, rect.y + 226, 5, couleur)
            genre = "BANNIERE" if vedette["type"] == "banniere" else "SKIN"
            dessiner_texte(image, f"{genre} LEGENDAIRE", rect.centerx, rect.y + 268, 2, GRIS, lueur=False)
            dessiner_texte(image, "SEULEMENT DANS LA BOITE MYSTERE", rect.centerx, rect.y + 294, 2,
                           config.AMBRE, lueur=False)
        self._dessiner_cube(image, (rect.x + 96, rect.y + 362), 44, self.temps, 0.0)
        for k, ligne in enumerate(("BOITE MYSTERE", "UN OBJET AU HASARD", "JAMAIS EN DOUBLE")):
            dessiner_texte(image, ligne, rect.x + 166, rect.y + 336 + k * 26, 3 if k == 0 else 2,
                           couleur if k == 0 else GRIS, ancrage="gauche", lueur=False)
        b = pygame.Rect(0, 0, 340, 56)
        b.midbottom = (rect.centerx, rect.bottom - 22)
        abordable = self.app.en_ligne.neons >= PRIX_BOITE
        pygame.draw.rect(image, couleur if abordable else (120, 90, 60), b, border_radius=8)
        dessiner_texte(image, "OUVRIR", b.x + 30, b.centery, 4, (20, 0, 30), ancrage="gauche", lueur=False,
                       ombre=False)
        zone = dessiner_texte(image, str(PRIX_BOITE), b.right - 24, b.centery, 4, (20, 0, 30),
                              ancrage="droite", lueur=False, ombre=False)
        dessiner_piece(image, (zone.x - 20, zone.centery), 11, self.temps)

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
        _, gauche, haut = disposition()
        y = haut - 20
        dessiner_texte(image, "SELECTION DU JOUR", gauche, y, 2, config.VIOLET, ancrage="gauche",
                       lueur=False)
        dessiner_texte(image, f"NOUVELLE DANS {temps_avant_minuit()}", config.LARGEUR - 46, y, 2, GRIS,
                       ancrage="droite", lueur=False)
        if self.app.entrees.tactile and self.etat == "vitrine":       # pas de touche H au doigt
            from ecrans.tactile import bouton
            rect = pygame.Rect(0, 0, 210, 44)
            rect.midtop = (config.LARGEUR / 2, haut + 2 * (HAUTEUR_CARTE + 28) - 10)
            bouton(image, self.app, rect, "historique", config.VIOLET, "HISTORIQUE")

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

    def _boutons_oui_non(self, image, cadre, oui, non):
        """But : au doigt, deux boutons sous la fenêtre (Entrée / Échap). Sortie : (bool) dessinés."""
        if not self.app.entrees.tactile:
            return False
        from ecrans.tactile import bouton
        largeur = (cadre.w - 60) // 2
        bouton(image, self.app, pygame.Rect(cadre.x + 20, cadre.bottom + 16, largeur, 64), "valider",
               config.VERT, oui)
        bouton(image, self.app, pygame.Rect(cadre.right - 20 - largeur, cadre.bottom + 16, largeur, 64),
               "retour", config.ROSE, non)
        return True

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
        y_message = 640
        if config.HAUTEUR > config.LARGEUR:
            y_message = disposition()[2] + 2 * (HAUTEUR_CARTE + 28) + 60
        if self.message and self.minuteur > 0:
            dessiner_texte(image, self.message, config.LARGEUR / 2, y_message, 3, config.AMBRE)
        elif config.HAUTEUR > config.LARGEUR:
            dessiner_texte(image, f"GAGNE DES {MONNAIE} : CAMPAGNE, BOSS, DEFIS, EN LIGNE",
                           config.LARGEUR / 2, y_message, 2, (130, 110, 190), lueur=False)
        else:
            dessiner_texte(image, f"GAGNE DES {MONNAIE} : CAMPAGNE, BOSS, DEFIS, SERIES, SUCCES, EN LIGNE",
                           config.LARGEUR / 2, y_message, 2, (130, 110, 190), lueur=False)

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
            if not self._boutons_oui_non(image, cadre, "ACHETER", "NON"):
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
            if not self._boutons_oui_non(image, cadre, "EQUIPER", "PLUS TARD"):
                dessiner_texte(image, "ENTREE : EQUIPER      ECHAP : PLUS TARD", cadre.centerx,
                               cadre.bottom - 30, 2, GRIS, lueur=False)
        if getattr(self, "historique", None) is not None:
            self._dessiner_historique(image)
        self.pied(image, "FLECHES : CHOISIR    ENTREE : ACHETER / EQUIPER    H : HISTORIQUE    TAB : ONGLET")
