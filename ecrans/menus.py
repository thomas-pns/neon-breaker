# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Navigation des menus (2.1) : barre du haut avec les onglets ACCUEIL,
    JOUER, CLASSEMENTS, CASIER et BOUTIQUE, solde de NEONS, petite bannière
    du joueur (cliquer dessus ouvre le profil) et roue des réglages (menu
    déroulant : nouveautés, aide, options, joueurs, connexion, quitter).
    Fournit aussi les éléments de dessin communs aux nouveaux écrans
    (cartes, boutons, écusson de division, flammes des séries).

    Commandes : Tab / Maj+Tab (ou LB / RB à la manette) changent d'onglet ;
    la souris clique sur les onglets, la bannière et la roue.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 25/10/2026
"""

import math

import pygame

from moteur import config
from moteur.bannieres import dessiner_banniere, dessiner_piece
from moteur.icones import dessiner_icone
from moteur.police_pixel import dessiner_texte
from moteur.rendu import attenuer, halo_rect, melanger
from moteur.version import VERSION
from ecrans.base import EcranBase

GRIS = (170, 140, 220)
ONGLETS = [("ACCUEIL", config.CYAN), ("JOUER", config.ROSE), ("CLASSEMENTS", config.AMBRE),
           ("CASIER", config.ROSE), ("BOUTIQUE", config.VIOLET)]
HAUTEUR_BARRE = 64
JAUNE_SERIE, VIOLET_SERIE = config.AMBRE, (190, 90, 255)


# --- Éléments de dessin ------------------------------------------------------------------

def carte(image, rect, couleur, choisie=False, alpha=225, rayon=12):
    """But : panneau néon arrondi (lumineux si choisi)."""
    fond = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(fond, (*melanger((12, 0, 30), couleur, 0.14 if choisie else 0.05), alpha),
                     fond.get_rect(), border_radius=rayon)
    image.blit(fond, rect.topleft)
    if choisie:
        lueur = halo_rect(rect.w, rect.h, attenuer(couleur, 0.9), rayon=12, epaisseur=4)
        image.blit(lueur, (rect.x - 24, rect.y - 24), special_flags=pygame.BLEND_RGB_ADD)
    pygame.draw.rect(image, couleur if choisie else attenuer(couleur, 0.5), rect,
                     3 if choisie else 2, border_radius=rayon)


def bouton(image, rect, texte, couleur, echelle=4):
    """But : bouton plein (texte sombre sur la couleur)."""
    pygame.draw.rect(image, couleur, rect, border_radius=8)
    dessiner_texte(image, texte, rect.centerx, rect.centery, echelle, (20, 0, 30), lueur=False,
                   ombre=False)


def ecusson(image, centre, taille, couleur, texte=None, echelle=2):
    """But : écusson hexagonal de division (avec la cote au milieu, si donnée)."""
    cx, cy = centre
    points = [(cx, cy - taille), (cx + taille * 0.85, cy - taille * 0.55),
              (cx + taille * 0.7, cy + taille * 0.55), (cx, cy + taille),
              (cx - taille * 0.7, cy + taille * 0.55), (cx - taille * 0.85, cy - taille * 0.55)]
    pygame.draw.polygon(image, (20, 8, 40), points)
    pygame.draw.polygon(image, couleur, points, max(2, int(taille // 10)))
    if texte:
        dessiner_texte(image, str(texte), cx, cy, echelle, config.BLANC, lueur=False)


def flamme(image, centre, couleur, echelle=2, texte=None):
    """But : flamme de série (jaune : jours, violette : semaines), avec un nombre à droite."""
    dessiner_icone(image, "flamme", (int(centre[0]), int(centre[1])), couleur, echelle)
    if texte is not None:
        dessiner_texte(image, str(texte), centre[0] + 6 * echelle, centre[1], max(2, echelle - 1),
                       couleur, ancrage="gauche", lueur=False)


def engrenage(image, centre, couleur):
    cx, cy = centre
    for k in range(8):
        angle = k * math.pi / 4
        pygame.draw.line(image, couleur, (cx + math.cos(angle) * 8, cy + math.sin(angle) * 8),
                         (cx + math.cos(angle) * 13, cy + math.sin(angle) * 13), 4)
    pygame.draw.circle(image, couleur, centre, 9, 3)


def division_joueur(app):
    """But : (nom, couleur, cote) de la division du joueur connecté (gris sans partie classée)."""
    from reseau.classee import division
    en_ligne = app.en_ligne
    cote = getattr(en_ligne, "elo", 1000)
    if not getattr(en_ligne, "classees", 0):
        return "NON CLASSE", (120, 100, 150), cote
    nom, couleur, _, _ = division(cote)
    return nom, couleur, cote


def series_locales(app):
    """But : (série de jours, série de semaines) des défis sur ce PC."""
    from jeu.modes.defi import serie_locale
    try:
        return serie_locale(app, "jour"), serie_locale(app, "semaine")
    except Exception:            # sauvegarde abîmée : pas de série affichée
        return 0, 0


def fond_menu(app, image, voile=140):
    """But : fond synthwave assombri des menus."""
    app.fond.dessiner(image)
    sombre = pygame.Surface(image.get_size())
    sombre.fill((8, 0, 20))
    sombre.set_alpha(voile)
    image.blit(sombre, (0, 0))


def nouvelle_version_non_vue(app):
    """But : la version actuelle n'a pas encore été ouverte dans NOUVEAUTÉS ? (point sur la roue)"""
    return app.donnees.get("nouveautes_vues") != VERSION


# --- Ouverture des onglets ------------------------------------------------------------------

def ecran_onglet(app, nom):
    """But : écran correspondant à un onglet de la barre."""
    if nom == "JOUER":
        from ecrans.jouer import EcranJouer
        return EcranJouer(app)
    if nom == "CLASSEMENTS":
        from ecrans.en_ligne.classements import EcranClassementsMondiaux
        return EcranClassementsMondiaux(app)
    if nom == "CASIER":
        from ecrans.casier import EcranCasier
        return EcranCasier(app)
    if nom == "BOUTIQUE":
        if not app.en_ligne.jeton:
            from ecrans.en_ligne.connexion import EcranConnexion
            return EcranConnexion(app)
        from ecrans.en_ligne.boutique import EcranBoutique
        return EcranBoutique(app)
    from ecrans.titre import EcranTitre
    return EcranTitre(app)


class Navigation:
    """
    Mixin des écrans qui ont la barre du haut. Attribut de classe : onglet
    (nom de l'onglet allumé, ou "" pour aucun, ex. le profil).
    Les écrans appellent self.naviguer() au début de mettre_a_jour (True si la
    barre a pris la main) et self.dessiner_barre(image) à la fin de dessiner.
    """

    onglet = ""

    def _zones_barre(self):
        zones = {}
        x = 160
        for nom, _ in ONGLETS:
            largeur = len(nom) * 12 + 30
            zones[nom] = pygame.Rect(x, 14, largeur, 38)
            x += largeur + 4
        zones["profil"] = pygame.Rect(config.LARGEUR - 304, 12, 236, 42)
        zones["neons"] = pygame.Rect(config.LARGEUR - 418, 16, 104, 34)
        zones["reglages"] = pygame.Rect(config.LARGEUR - 58, 12, 42, 42)
        return zones

    def aller(self, nom):
        """But : ouvrir un onglet (ou ne rien faire si c'est déjà lui)."""
        if nom == self.onglet:
            return
        self.app.audio.jouer("menu_nav")
        self.app.remplacer(ecran_onglet(self.app, nom), transition=False)

    def ouvrir_reglages(self):
        self.app.audio.jouer("menu_ok")
        self.app.empiler(EcranReglages(self.app))

    def ouvrir_profil(self):
        en_ligne = self.app.en_ligne
        self.app.audio.jouer("menu_ok")
        if not en_ligne.jeton:
            from ecrans.en_ligne.connexion import EcranConnexion
            self.app.remplacer(EcranConnexion(self.app), transition=False)
            return
        from ecrans.en_ligne.joueurs import EcranProfil
        self.app.remplacer(EcranProfil(self.app, en_ligne.pseudo), transition=False)

    def naviguer(self):
        """But : Tab / LB / RB et clics sur la barre. Sortie : (bool) True si elle a agi."""
        entrees = self.app.entrees
        noms = [nom for nom, _ in ONGLETS]
        actuel = noms.index(self.onglet) if self.onglet in noms else 0
        sens = 0
        if entrees.vient_d_appuyer("onglet"):
            sens = -1 if pygame.key.get_mods() & pygame.KMOD_SHIFT else 1
        elif entrees.vient_d_appuyer("onglet_precedent"):
            sens = -1
        if sens:
            self.aller(noms[(actuel + sens) % len(noms)])
            return True
        if 1 in entrees.clics:
            zones = self._zones_barre()
            for nom in noms:
                if zones[nom].collidepoint(entrees.souris):
                    self.aller(nom)
                    return True
            if zones["profil"].collidepoint(entrees.souris):
                self.ouvrir_profil()
                return True
            if zones["reglages"].collidepoint(entrees.souris):
                self.ouvrir_reglages()
                return True
        return False

    def dessiner_barre(self, image):
        """But : barre du haut (onglets, NEONS, petite bannière, roue des réglages)."""
        bande = pygame.Surface((config.LARGEUR, HAUTEUR_BARRE), pygame.SRCALPHA)
        bande.fill((6, 0, 18, 235))
        image.blit(bande, (0, 0))
        pygame.draw.line(image, attenuer(config.CYAN, 0.6), (0, HAUTEUR_BARRE),
                         (config.LARGEUR, HAUTEUR_BARRE), 2)
        dessiner_texte(image, "NEON", 30, 22, 3, config.CYAN, ancrage="gauche")
        dessiner_texte(image, "BREAKER", 30, 46, 2, config.AMBRE, ancrage="gauche", lueur=False)
        zones = self._zones_barre()
        souris = self.app.entrees.souris
        for nom, couleur in ONGLETS:
            r = zones[nom]
            if nom == self.onglet:
                pygame.draw.rect(image, couleur, r, border_radius=6)
                dessiner_texte(image, nom, r.centerx, r.centery, 2, (10, 0, 25), lueur=False,
                               ombre=False)
            else:
                survol = r.collidepoint(souris)
                dessiner_texte(image, nom, r.centerx, r.centery, 2,
                               config.BLANC if survol else GRIS, lueur=False)
        en_ligne = self.app.en_ligne
        profil = zones["profil"]
        if en_ligne.jeton:
            n = zones["neons"]
            pygame.draw.rect(image, (16, 6, 40), n, border_radius=17)
            pygame.draw.rect(image, attenuer(config.CYAN, 0.5), n, 2, border_radius=17)
            dessiner_piece(image, (n.x + 22, n.centery), 9, self.temps)
            dessiner_texte(image, str(getattr(en_ligne, "neons", 0)), n.right - 16, n.centery, 2,
                           config.CYAN, ancrage="droite", lueur=False)
            zone = image.get_clip()
            image.set_clip(profil)
            if not dessiner_banniere(image, en_ligne.banniere_active(), profil, self.temps,
                                     cadre=False, voile=110, icone=False):
                image.fill((16, 6, 40), profil)
            image.set_clip(zone)
            survol = profil.collidepoint(souris)
            pygame.draw.rect(image, config.BLANC if survol else attenuer(config.ROSE, 0.7), profil, 2,
                             border_radius=6)
            _, couleur_division, _ = division_joueur(self.app)
            ecusson(image, (profil.x + 24, profil.centery), 14, couleur_division)
            dessiner_texte(image, en_ligne.pseudo.upper()[:9], profil.x + 48, profil.centery - 7, 2,
                           config.BLANC, ancrage="gauche", lueur=False)
            dessiner_texte(image, f"RANG {en_ligne.niveau}", profil.x + 48, profil.centery + 11, 1,
                           config.AMBRE, ancrage="gauche", lueur=False)
        else:
            pygame.draw.rect(image, (16, 6, 40), profil, border_radius=6)
            pygame.draw.rect(image, config.VERT, profil, 2, border_radius=6)
            dessiner_texte(image, "SE CONNECTER", profil.centerx, profil.centery, 2, config.VERT,
                           lueur=False)
        jours, semaines = series_locales(self.app)
        if en_ligne.jeton:
            flamme(image, (profil.right - 84, profil.centery), JAUNE_SERIE, 2, jours)
            flamme(image, (profil.right - 40, profil.centery), VIOLET_SERIE, 2, semaines)
        roue = zones["reglages"]
        engrenage(image, roue.center, config.BLANC if roue.collidepoint(souris) else GRIS)
        if nouvelle_version_non_vue(self.app) and math.sin(self.temps * 5) > -0.3:
            pygame.draw.circle(image, config.ROSE, (roue.right - 6, roue.y + 8), 5)


class EcranMenu(Navigation, EcranBase):
    """Écran avec la barre du haut (fond synthwave assombri)."""

    def dessiner_fond(self, image, voile=140):
        fond_menu(self.app, image, voile)


# --- Menu des réglages (roue) -------------------------------------------------------------

class EcranReglages(EcranBase):
    """Menu déroulant de la roue : posé par-dessus l'écran actuel."""

    transparent = True

    def __init__(self, app):
        super().__init__(app)
        self.indice = 0
        self.zones = []

    @property
    def attenuer_musique(self):
        return getattr(self.dessous, "attenuer_musique", False)

    def musique(self):
        return self.dessous.musique() if self.dessous is not None else "menu"

    def options(self):
        connecte = bool(self.app.en_ligne.jeton)
        options = [("NOUVEAUTES", self._nouveautes), ("AIDE", self._aide), ("OPTIONS", self._options),
                   ("JOUEURS", self._joueurs)]
        if connecte and getattr(self.app.en_ligne, "admin", False):
            options.append(("ADMIN", self._admin))
        return options + [("SE DECONNECTER" if connecte else "SE CONNECTER", self._compte),
                          ("QUITTER LE JEU", self._quitter)]

    def _admin(self):
        from ecrans.en_ligne.admin import EcranAdmin
        self.app.remplacer(EcranAdmin(self.app), transition=False)

    def _fermer(self):
        self.app.depiler()

    def _nouveautes(self):
        from ecrans.nouveautes import EcranNouveautes
        self.app.donnees["nouveautes_vues"] = VERSION
        self.app.enregistrer()
        self.app.remplacer(EcranNouveautes(self.app), transition=False)

    def _aide(self):
        from ecrans.aide import EcranAide
        self.app.remplacer(EcranAide(self.app), transition=False)

    def _options(self):
        from ecrans.options import EcranOptions
        self.app.depiler()
        self.app.empiler(EcranOptions(self.app))

    def _joueurs(self):
        if not self.app.en_ligne.jeton:
            self._compte()
            return
        from ecrans.en_ligne.joueurs import EcranJoueurs
        self.app.remplacer(EcranJoueurs(self.app), transition=False)

    def _compte(self):
        from ecrans.titre import EcranTitre
        from ecrans.en_ligne.connexion import EcranConnexion
        if self.app.en_ligne.jeton:
            self.app.en_ligne.se_deconnecter()
            self.app.remplacer(EcranTitre(self.app), transition=False)
        else:
            self.app.remplacer(EcranConnexion(self.app), transition=False)

    def _quitter(self):
        self.app.en_marche = False

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        entrees = self.app.entrees
        options = self.options()
        if entrees.vient_d_appuyer("retour"):
            self._fermer()
            return
        ancien = self.indice
        if entrees.vient_d_appuyer("haut"):
            self.indice = (self.indice - 1) % len(options)
        if entrees.vient_d_appuyer("bas"):
            self.indice = (self.indice + 1) % len(options)
        if entrees.souris_bougee:
            for i, zone in enumerate(self.zones):
                if zone.collidepoint(entrees.souris):
                    self.indice = i
        if self.indice != ancien:
            self.app.audio.jouer("menu_nav")
        if 1 in entrees.clics and self.zones:
            dedans = [i for i, z in enumerate(self.zones) if z.collidepoint(entrees.souris)]
            if not dedans:
                self._fermer()                     # clic ailleurs : on ferme
                return
            self.indice = dedans[0]
            options[self.indice][1]()
            return
        if entrees.vient_d_appuyer("valider"):
            self.app.audio.jouer("menu_ok")
            options[self.indice][1]()

    def dessiner(self, image):
        options = self.options()
        cadre = pygame.Rect(config.LARGEUR - 250, HAUTEUR_BARRE + 6, 234, 22 + 40 * len(options))
        carte(image, cadre, config.CYAN, True, alpha=245)
        self.zones = []
        for i, (nom, _) in enumerate(options):
            ligne = pygame.Rect(cadre.x + 8, cadre.y + 10 + i * 40, cadre.w - 16, 36)
            self.zones.append(ligne)
            choisi = i == self.indice
            if choisi:
                pygame.draw.rect(image, (40, 15, 80), ligne, border_radius=6)
            couleur = config.ROUGE if nom.startswith("QUITTER") else (
                config.BLANC if choisi else GRIS)
            dessiner_texte(image, nom, ligne.x + 16, ligne.centery, 2, couleur, ancrage="gauche",
                           lueur=False)
            if nom == "NOUVEAUTES" and nouvelle_version_non_vue(self.app):
                pygame.draw.circle(image, config.ROSE, (ligne.right - 16, ligne.centery), 5)
