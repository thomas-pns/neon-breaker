# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    ACCUEIL (2.1, garde le nom EcranTitre : tous les « retour au menu » y
    mènent) : barre du haut, grande bannière du joueur (profil), carte
    REPRENDRE la campagne avec le décor du monde atteint, gros bouton JOUER,
    et à droite les accès rapides (défi du jour, défi de la semaine,
    boutique du jour). Aide, options et quitter sont dans la roue en haut.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026, refait le 25/10/2026
"""

import math

import pygame

from moteur import config
from moteur.bannieres import dessiner_banniere
from moteur.police_pixel import dessiner_texte
from moteur.rendu import figer
from moteur.version import VERSION
from ecrans.hud import barre, dessiner_etoiles
from ecrans.menus import (EcranMenu, GRIS, JAUNE_SERIE, VIOLET_SERIE, bas_contenu, bouton, carte,
                          division_joueur, ecusson, est_vertical, flamme, haut_contenu,
                          series_locales)

ZONES = ["profil", "reprendre", "jouer", "defi", "semaine", "boutique"]
# voisins pour les flèches : zone -> (haut, bas, gauche, droite)
VOISINS = {"profil": (None, "reprendre", None, "defi"),
           "reprendre": ("profil", "jouer", None, "semaine"),
           "jouer": ("reprendre", None, None, "boutique"),
           "defi": (None, "semaine", "profil", None),
           "semaine": ("defi", "boutique", "reprendre", None),
           "boutique": ("semaine", None, "jouer", None)}
RECT = {"profil": pygame.Rect(40, 86, 760, 110), "reprendre": pygame.Rect(40, 214, 760, 186),
        "jouer": pygame.Rect(40, 418, 760, 184), "defi": pygame.Rect(830, 86, 410, 160),
        "semaine": pygame.Rect(830, 262, 410, 160), "boutique": pygame.Rect(830, 438, 410, 164)}


# Format vertical (téléphone) : les cartes l'une sous l'autre, défis côte à côte.
VOISINS_VERTICAL = {"profil": (None, "reprendre", None, None),
                    "reprendre": ("profil", "jouer", None, None),
                    "jouer": ("reprendre", "defi", None, None),
                    "defi": ("jouer", "boutique", None, "semaine"),
                    "semaine": ("jouer", "boutique", "defi", None),
                    "boutique": ("defi", None, None, None)}


def rects_verticaux():
    """
    But : cartes de l'accueil au format vertical, empilées entre la barre du haut et
    les onglets du bas ; la place en plus agrandit REPRENDRE et JOUER.
    Sortie : (dict) zone -> Rect.
    """
    haut, bas = haut_contenu() + 14, bas_contenu() - 14
    ecart = 18
    # Les deux défis côte à côte s'il y a la place, sinon l'un sous l'autre (pleine largeur).
    empiles = config.LARGEUR < 720
    hauteurs = {"profil": 110, "reprendre": 176, "jouer": 170, "defis": 220, "boutique": 120}
    if empiles:
        hauteurs["defis"] = 2 * 160 + ecart
    surplus = max(0, bas - haut - sum(hauteurs.values()) - 4 * ecart)
    hauteurs["reprendre"] += min(150, surplus // 2)
    hauteurs["jouer"] += min(150, surplus // 2)
    ecart += max(0, surplus - 300) // 4
    largeur = config.LARGEUR - 40
    y = haut
    rects = {}
    for nom in ("profil", "reprendre", "jouer", "defis", "boutique"):
        h = hauteurs[nom]
        if nom == "defis" and empiles:
            rects["defi"] = pygame.Rect(20, y, largeur, 160)
            rects["semaine"] = pygame.Rect(20, y + 160 + ecart, largeur, 160)
        elif nom == "defis":
            moitie = (largeur - 20) // 2
            rects["defi"] = pygame.Rect(20, y, moitie, h)
            rects["semaine"] = pygame.Rect(40 + moitie, y, moitie, h)
        else:
            rects[nom] = pygame.Rect(20, y, largeur, h)
        y += h + ecart
    return rects


def texte_version():
    """
    But : texte de la version affichée (menu de la roue, écran d'accueil).
    Entrée : aucune. Sortie : (str) ex. « V2.1.0 ».
    """
    return f"V{VERSION}"


class EcranTitre(EcranMenu):
    """Accueil. Attributs : choix (str : zone sélectionnée), decor (Surface : monde atteint)."""

    bouton_retour = False          # au doigt : pas de bouton RETOUR commun
    vertical = True

    onglet = "ACCUEIL"

    def __init__(self, app):
        super().__init__(app)
        self.choix = "jouer"
        self.decor = None
        self.rayures = None
        self.vitrine = None
        self.code_decor = None

    def entrer(self):
        self.app.fond.changer_monde(1)
        self.app.fond.progression = 0.0
        self.app.fond.vitesse_cible = 0.8
        if self.app.en_ligne.jeton and hasattr(self.app.en_ligne, "charger_boutique"):
            self.app.en_ligne.charger_boutique(self._recu_boutique)

    def reprendre(self):
        self.app.entrees.debut_image()

    def _recu_boutique(self, resultat):
        if resultat.get("ok"):
            self.vitrine = resultat["donnees"].get("selection")

    # --- Données ------------------------------------------------------------------------

    def _campagne(self):
        from jeu.niveau import charger_campagne
        if not hasattr(self, "_niveaux"):
            self._niveaux = charger_campagne()
        indice = min(self.app.niveau_debloque("campagne"), len(self._niveaux) - 1)
        etoiles = self.app.donnees.get("etoiles", {}).get("campagne", {})
        return self._niveaux, indice, int(etoiles.get(str(indice), 0))

    def rects(self):
        """But : cartes de l'accueil (format paysage ou vertical)."""
        return rects_verticaux() if est_vertical() else RECT

    def _decor(self, monde, rect):
        """Bout de la carte du monde atteint, arrondi, pour la carte REPRENDRE (en cache)."""
        if self.code_decor == (monde, rect.size) and self.decor is not None:
            return self.decor
        from ecrans.carte import EcranCarte
        carte_monde = EcranCarte(self.app, "campagne")
        debut = int(carte_monde.bornes.get(monde, (0, 0))[0]) + 60
        debut = max(0, min(debut, carte_monde.decors.get_width() - rect.w))
        decor = carte_monde.decors.subsurface(pygame.Rect(debut, 150, rect.w, rect.h)).copy()
        sombre = pygame.Surface(rect.size, pygame.SRCALPHA)
        sombre.fill((8, 0, 20, 90))
        decor.blit(sombre, (0, 0))
        masque = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(masque, (255, 255, 255, 255), masque.get_rect(), border_radius=12)
        avec_alpha = decor.convert_alpha() if pygame.display.get_surface() else decor
        avec_alpha.blit(masque, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        self.decor, self.code_decor = figer(avec_alpha), (monde, rect.size)
        return avec_alpha

    # --- Actions -----------------------------------------------------------------------

    def _en_ligne(self):
        """But : aller jouer en ligne (mise à jour obligatoire ? connexion ?)."""
        infos = self.app.en_ligne.mise_a_jour_requise()
        if infos:
            from ecrans.mise_a_jour import EcranMiseAJour
            self.app.empiler(EcranMiseAJour(self.app, infos))
            return
        if self.app.en_ligne.jeton:
            from ecrans.jouer import EcranJouer
            self.app.remplacer(EcranJouer(self.app, "en_ligne"))
        else:
            from ecrans.en_ligne.connexion import EcranConnexion
            self.app.remplacer(EcranConnexion(self.app))

    def activer(self, zone):
        from ecrans.jouer import EcranJouer
        app = self.app
        app.audio.jouer("menu_ok")
        if zone == "profil":
            self.ouvrir_profil()
        elif zone == "reprendre":
            from ecrans.carte import EcranCarte
            app.remplacer(EcranCarte(app, "campagne"))
        elif zone == "jouer":
            app.remplacer(EcranJouer(app), transition=False)
        elif zone in ("defi", "semaine"):
            from ecrans.partie import EcranPartie
            from ecrans.modes import fabrique_mode
            app.remplacer(EcranPartie(app, fabrique_mode(zone)))
        elif zone == "boutique":
            self.aller("BOUTIQUE")

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        if self.naviguer():
            return
        entrees = self.app.entrees
        if entrees.vient_d_appuyer("retour"):
            self.ouvrir_reglages()
            return
        ancien = self.choix
        rects = self.rects()
        haut, bas, gauche, droite = (VOISINS_VERTICAL if est_vertical() else VOISINS)[self.choix]
        for action, voisin in (("haut", haut), ("bas", bas), ("gauche", gauche), ("droite", droite)):
            if entrees.vient_d_appuyer(action) and voisin:
                self.choix = voisin
                break
        if entrees.souris_bougee:
            for zone, rect in rects.items():
                if rect.collidepoint(entrees.souris):
                    self.choix = zone
        if self.choix != ancien:
            self.app.audio.jouer("menu_nav")
        clic = 1 in entrees.clics and rects[self.choix].collidepoint(entrees.souris)
        if entrees.vient_d_appuyer("valider") or clic:
            self.activer(self.choix)

    # --- Dessin ------------------------------------------------------------------------

    def dessiner(self, image):
        self.dessiner_fond(image, 120)
        rects = self.rects()
        self._dessiner_profil(image, rects["profil"], self.choix == "profil")
        self._dessiner_reprendre(image, rects["reprendre"], self.choix == "reprendre")
        self._dessiner_jouer(image, rects["jouer"], self.choix == "jouer")
        self._dessiner_defi(image, rects["defi"], "defi", self.choix == "defi")
        self._dessiner_defi(image, rects["semaine"], "semaine", self.choix == "semaine")
        self._dessiner_boutique(image, rects["boutique"], self.choix == "boutique")
        if config.EST_TEST:
            dessiner_texte(image, "VERSION DE TEST - SCORES NON ENVOYES", config.LARGEUR / 2, 640, 2,
                           config.AMBRE, lueur=False)
        dessiner_texte(image, texte_version(), config.LARGEUR - 16, config.HAUTEUR - 18, 1, GRIS,
                       ancrage="droite", lueur=False)
        self.dessiner_barre(image)

    def _cadre_choix(self, image, rect, choisi, couleur):
        if choisi:
            pygame.draw.rect(image, couleur, rect.inflate(8, 8), 2, border_radius=14)

    def _dessiner_profil(self, image, r, choisi):
        en_ligne = self.app.en_ligne
        jours, semaines = series_locales(self.app)
        if not en_ligne.jeton:
            carte(image, r, config.VERT, choisi)
            dessiner_texte(image, "JOUE EN LIGNE", r.x + 30, r.y + 38, 4, config.VERT, ancrage="gauche")
            if est_vertical():                  # téléphone : plus court, plus gros
                dessiner_texte(image, "CLASSEMENTS, NEONS, BOUTIQUE", r.x + 30, r.y + 80, 3, GRIS,
                               ancrage="gauche", lueur=False)
                dessiner_texte(image, "SE CONNECTER >", r.right - 22, r.y + 38, 2, config.BLANC,
                               ancrage="droite", lueur=False)
                return
            dessiner_texte(image, "CREE TON COMPTE : CLASSEMENTS, BOUTIQUE...",
                           r.x + 30, r.y + 78, 2, GRIS, ancrage="gauche", lueur=False)
            dessiner_texte(image, "SE CONNECTER >", r.right - 20, r.bottom - 18, 2, config.BLANC,
                           ancrage="droite", lueur=False)
            return
        if not dessiner_banniere(image, en_ligne.banniere_active(), r, self.temps, voile=70):
            carte(image, r, config.ROSE, choisi)
        self._cadre_choix(image, r, choisi, config.BLANC)
        nom_division, couleur_division, cote = division_joueur(self.app)
        ecusson(image, (r.x + 62, r.centery), 40, couleur_division,
                cote if getattr(en_ligne, "classees", 0) else None, 2)
        etroit = r.w < 700                      # téléphone : séries à droite, sans « PROFIL > »
        pseudo = en_ligne.pseudo.upper()
        echelle = 5 if not etroit or len(pseudo) * 30 < r.w - 150 else 4
        dessiner_texte(image, pseudo, r.x + 130, r.y + 36, echelle, config.BLANC, ancrage="gauche")
        dessiner_texte(image, f"RANG {en_ligne.niveau}   {nom_division}", r.x + 132, r.y + 72, 2,
                       config.AMBRE, ancrage="gauche", lueur=False)
        from reseau.profil import niveau_pour, xp_pour_niveau
        niveau = niveau_pour(en_ligne.xp)
        debut, fin = xp_pour_niveau(niveau), xp_pour_niveau(niveau + 1)
        barre(image, pygame.Rect(r.x + 132, r.y + 88, 200 if etroit else 300, 8),
              (en_ligne.xp - debut) / max(1, fin - debut), config.AMBRE)
        if etroit:
            flamme(image, (r.right - 170, r.y + 80), JAUNE_SERIE, 3, f"{jours} J")
            flamme(image, (r.right - 84, r.y + 80), VIOLET_SERIE, 3, f"{semaines} S")
            return
        flamme(image, (r.x + 470, r.y + 76), JAUNE_SERIE, 3, f"{jours} J")
        flamme(image, (r.x + 570, r.y + 76), VIOLET_SERIE, 3, f"{semaines} S")
        dessiner_texte(image, "PROFIL >", r.right - 18, r.bottom - 16, 2, config.BLANC, ancrage="droite",
                       lueur=False)

    def _dessiner_reprendre(self, image, r, choisi):
        from ecrans.carte import NOMS_MONDES, COULEURS_MONDES
        niveaux, indice, masque = self._campagne()
        niveau = niveaux[indice]
        couleur = COULEURS_MONDES.get(niveau.monde, config.CYAN)
        image.blit(self._decor(niveau.monde, r), r.topleft)
        pygame.draw.rect(image, couleur, r, 3, border_radius=12)
        self._cadre_choix(image, r, choisi, config.BLANC)
        etat = "REPRENDRE" if indice else "COMMENCER"
        dessiner_texte(image, f"{etat}  -  MONDE {niveau.monde}  {NOMS_MONDES.get(niveau.monde, '')}",
                       r.x + 28, r.y + 30, 2, config.BLANC, ancrage="gauche", lueur=False)
        nom = niveau.nom.split("  ")[-1] if "  " in niveau.nom else niveau.nom
        titre = f"BOSS {niveau.boss.upper()}" if niveau.boss else f"NIVEAU {indice + 1}  {nom}"
        titre = titre[:20]
        echelle = 5
        while echelle > 3 and len(titre) * 6 * echelle > r.w - 60:   # écran étroit : un cran plus petit
            echelle -= 1
        dessiner_texte(image, titre, r.x + 28, r.y + 72, echelle, couleur, ancrage="gauche")
        dessiner_etoiles(image, 0, (r.x + 68, r.y + 118), 12, masque=masque)
        b = pygame.Rect(r.right - 250, r.bottom - 72, 220, 50)
        bouton(image, b, "CONTINUER" if indice else "JOUER", couleur)

    def _dessiner_jouer(self, image, r, choisi):
        carte(image, r, config.ROSE, True)
        # Rayures qui défilent : un motif dessiné une fois (36 px plus large), dont on
        # copie la bonne fenêtre à chaque image.
        if self.rayures is None or self.rayures.get_height() != r.h:
            self.rayures = pygame.Surface((r.w + 36, r.h), pygame.SRCALPHA)
            for k in range(0, r.w + r.h + 36, 36):
                pygame.draw.line(self.rayures, (255, 60, 200, 22), (k, 0), (k - r.h, r.h), 12)
            figer(self.rayures)
        decalage = int(self.temps * 30) % 36
        # Sans les coins (12 px, arrondis de la carte) : bande du milieu, puis côtés.
        x0 = 36 - decalage
        for zone in (pygame.Rect(12, 0, r.w - 24, r.h), pygame.Rect(0, 12, 12, r.h - 24),
                     pygame.Rect(r.w - 12, 12, 12, r.h - 24)):
            image.blit(self.rayures, (r.x + zone.x, r.y + zone.y), zone.move(x0, 0))
        self._cadre_choix(image, r, choisi, config.BLANC)
        pulse = 1.0 if not choisi else 1.0 + 0.04 * math.sin(self.temps * 5)
        dessiner_texte(image, "JOUER", r.centerx, r.y + max(76, r.h // 2 - 20), int(10 * pulse),
                       config.ROSE)
        modes = "CAMPAGNE  -  ARCADE  -  CLASSEE  -  DUEL  -  COOP  -  DEFIS"
        if len(modes) * 12 > r.w - 40:
            modes = "CAMPAGNE - ARCADE - DUEL - COOP - DEFIS"
        dessiner_texte(image, modes, r.centerx, r.bottom - 36, 2, config.BLANC, lueur=False)

    def _dessiner_defi(self, image, r, code, choisi):
        from jeu.modes import defi as d
        if code == "defi":
            jour = d.jour_du_defi()
            modificateurs = [d.defi_pour(jour)[1]]
            titre, couleur, periode, unite = "DEFI DU JOUR", JAUNE_SERIE, "jour", "J"
            serie = series_locales(self.app)[0]
            reste = ""
        else:
            jour = d.semaine_du_defi()
            modificateurs = d.defi_semaine_pour(jour)[1]
            titre, couleur, periode, unite = ("DEFI DE LA SEMAINE" if r.w > 480 else "DEFI SEMAINE",
                                              VIOLET_SERIE, "semaine", "S")
            serie = series_locales(self.app)[1]
            import datetime
            jours_restants = 7 - datetime.date.today().isoweekday()
            reste = f"ENCORE {jours_restants} JOUR{'S' if jours_restants > 1 else ''}" if jours_restants \
                else "DERNIER JOUR !"
        carte(image, r, couleur, choisi)
        vertical = est_vertical()
        taille, pas = (3, 32) if vertical else (2, 24)    # téléphone : textes plus gros
        dessiner_texte(image, titre, r.x + 22, r.y + 32, 3, couleur, ancrage="gauche")
        y = r.y + (78 if vertical else 70)
        for m in modificateurs:
            dessiner_texte(image, m[1], r.x + 22, y, taille, config.BLANC, ancrage="gauche", lueur=False)
            y += pas
        x_etat, ancrage = r.x + 22, "gauche"
        if vertical and r.w > 500:          # carte large et basse (défis l'un sous l'autre) :
            y = r.bottom - 32 - 6           # l'état à droite, au-dessus des jours restants
            x_etat, ancrage = r.right - 84, "droite"
        y_etat = r.y + 72 if ancrage == "droite" else y + 6
        joue = jour in d.defis_joues(self.app, periode)
        if not joue:
            if math.sin(self.temps * 5) > -0.3:
                dessiner_texte(image, "A JOUER !", x_etat, y_etat, taille, config.ROSE, ancrage=ancrage,
                               lueur=False)
        else:
            record = d.record_du_jour(self.app, jour, code)
            dessiner_texte(image, f"RECORD {record}" if vertical else f"TON RECORD {record}", x_etat,
                           y_etat, taille, GRIS, ancrage=ancrage, lueur=False)
        if reste and vertical and r.w > 500:
            dessiner_texte(image, reste, r.right - 84, y + 6, 2, GRIS, ancrage="droite", lueur=False)
        elif reste:
            dessiner_texte(image, reste, r.x + 22, y + 6 + pas + 2, 2, GRIS, ancrage="gauche", lueur=False)
        flamme(image, (r.right - 76, r.y + 32), couleur, 3, f"{serie} {unite}")
        from ecrans.tactile import bouton_podium            # voir le classement de ce défi
        bouton_podium(image, self.app, (r.right - 36, r.bottom - 36), couleur, f"classement_{code}")

    def _dessiner_boutique(self, image, r, choisi):
        from reseau.boutique import COULEURS_RARETES
        carte(image, r, config.VIOLET, choisi)
        dessiner_texte(image, "BOUTIQUE DU JOUR", r.x + 22, r.y + 32, 3, config.VIOLET, ancrage="gauche")
        if not self.app.en_ligne.jeton:
            dessiner_texte(image, "CONNECTE-TOI POUR VOIR", r.x + 22, r.y + 74, 2, GRIS, ancrage="gauche",
                           lueur=False)
            dessiner_texte(image, "LES SKINS ET BANNIERES", r.x + 22, r.y + 98, 2, GRIS, ancrage="gauche",
                           lueur=False)
            return
        if not self.vitrine:
            dessiner_texte(image, "CHARGEMENT...", r.x + 22, r.y + 74, 2, GRIS, ancrage="gauche", lueur=False)
            return
        promo = next((o for o in self.vitrine if o.get("promo")), self.vitrine[0])
        dessiner_texte(image, f"{promo['nom']}  -30 %" if promo.get("promo") else promo["nom"],
                       r.x + 22, r.y + 74, 2, config.BLANC, ancrage="gauche", lueur=False)
        dessiner_texte(image, f"ET {len(self.vitrine) - 1} AUTRES OBJETS", r.x + 22, r.y + 98, 2, GRIS,
                       ancrage="gauche", lueur=False)
        zone = pygame.Rect(r.x + 22, r.y + 118, 260, 30)
        if promo["type"] == "banniere":
            dessiner_banniere(image, promo["code"], zone, self.temps)
        else:
            pygame.draw.rect(image, COULEURS_RARETES[promo["rarete"]], zone, 2, border_radius=6)
            dessiner_texte(image, "SKIN " + promo["nom"], zone.centerx, zone.centery, 2,
                           COULEURS_RARETES[promo["rarete"]], lueur=False)
