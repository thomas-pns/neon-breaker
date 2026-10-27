# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Liste de tous les joueurs (niveau, succès, en ligne ou non) et page de
    profil d'un joueur : niveau et XP, statistiques, records par mode,
    grille des 24 succès (le succès choisi affiche sa description).

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import pygame
import time

from moteur import config
from moteur.police_pixel import dessiner_texte
from moteur.bannieres import dessiner_banniere
from moteur.rendu import halo_rect, attenuer
from reseau.profil import NOMBRE_SUCCES
from ecrans.hud import panneau, barre
from ecrans.en_ligne.commun import (EcranEnLigneBase, couleur_profil, date_courte,
                                    duree_lisible, NOMS_MODES, GRIS)

COULEURS_CATEGORIES = {"debuts": config.CYAN, "campagne": config.ROSE, "habilete": config.AMBRE,
                       "modes": config.VIOLET, "coop": config.VERT, "collection": config.OR,
                       "endurance": config.BLEU, "secret": (200, 200, 255),
                       "defi": config.ROUGE}
# Paliers des succès (2.6) : mêmes couleurs que les divisions de la classée.
NOMS_PALIERS = ("ARGENT", "OR", "PLATINE")
COULEURS_PALIERS = ((200, 210, 230), (255, 210, 60), (90, 240, 220))
COLONNES_SUCCES = 7
LIGNES_SUCCES = 5


def est_vertical():
    return config.HAUTEUR > config.LARGEUR


def colonnes_succes():
    """But : succès par ligne (3 au format vertical : cases larges, noms lisibles)."""
    return 3 if est_vertical() else COLONNES_SUCCES


def lignes_succes():
    return 8 if est_vertical() else LIGNES_SUCCES


def hauteur_case():
    """But : hauteur d'une case de succès (plus haute au format vertical)."""
    return 84 if est_vertical() else 64


def couper_en_lignes(texte, largeur_max_caracteres, max_lignes=2):
    """
    But : couper un texte sur des espaces en lignes d'au plus largeur_max_caracteres.
    Entree(s) : texte (str), largeur_max_caracteres (int), max_lignes (int) : au-dela,
                le reste est ajoute a la derniere ligne.
    Sortie : tuple de max_lignes lignes (vides si inutiles).
    """
    mots = str(texte).split()
    if not mots:
        return ("", "")
    lignes = [""]
    for mot in mots:
        candidat = (lignes[-1] + " " + mot).strip()
        if len(candidat) <= largeur_max_caracteres:
            lignes[-1] = candidat
        elif len(lignes) < max_lignes:
            lignes.append(mot)
        else:
            lignes[-1] += " " + mot
    return tuple((lignes + [""] * max_lignes)[:max_lignes])


class EcranJoueurs(EcranEnLigneBase):
    """Tous les joueurs du serveur."""

    vertical = True               # dessiné aussi au format vertical (téléphone)

    titre = "JOUEURS"
    onglet = ""

    def __init__(self, app):
        super().__init__(app)
        self.joueurs = None
        self.erreur = ""
        self.chargement = False
        self.prochaine_tentative = 0.0
        self.indice = 0
        self.zones = []
        self._charger()

    def _charger(self):
        """But : demander les donnees au serveur, une requete a la fois. Entree(s) : aucune. Sortie : aucune."""
        if self.chargement:
            return
        self.chargement = True
        self.app.en_ligne.appeler("GET", "/api/joueurs", rappel=self._recu)

    def _recu(self, resultat):
        self.chargement = False
        if resultat["ok"]:
            self.joueurs = resultat["donnees"]["joueurs"]
            moi = self.app.en_ligne.pseudo.lower()
            self.indice = next((i for i, j in enumerate(self.joueurs)
                                if j["pseudo"].lower() == moi), 0)
        else:
            self.erreur = "SERVEUR EN MAINTENANCE" if resultat.get("maintenance") else resultat["erreur"]
            if resultat.get("maintenance"):
                self.prochaine_tentative = time.monotonic() + 5

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        if self.erreur == "SERVEUR EN MAINTENANCE" and time.monotonic() >= self.prochaine_tentative:
            self._charger()
        entrees = self.app.entrees
        if entrees.vient_d_appuyer("retour"):
            self.retour_accueil()
            return
        if not self.joueurs:
            return
        ancien = self.indice
        if entrees.vient_d_appuyer("haut"):
            self.indice = (self.indice - 1) % len(self.joueurs)
        if entrees.vient_d_appuyer("bas"):
            self.indice = (self.indice + 1) % len(self.joueurs)
        if entrees.souris_bougee:
            for i, zone in enumerate(self.zones):
                if zone.collidepoint(entrees.souris):
                    self.indice = self.debut + i
        if self.indice != ancien:
            self.app.audio.jouer("menu_nav")
        clic = 1 in entrees.clics and any(z.collidepoint(entrees.souris) for z in self.zones)
        if entrees.vient_d_appuyer("valider") or clic:
            self.app.audio.jouer("menu_ok")
            self.app.remplacer(EcranProfil(self.app, self.joueurs[self.indice]["pseudo"],
                                           retour="joueurs"))

    def dessiner(self, image):
        self.dessiner_fond(image)
        vertical = est_vertical()
        if vertical:
            from ecrans.menus import bas_contenu, haut_contenu
            cadre = pygame.Rect(20, haut_contenu() + 16, config.LARGEUR - 40,
                                bas_contenu() - haut_contenu() - 32)
        else:
            cadre = pygame.Rect(190, 100, 900, 550)
        panneau(image, cadre, config.ROSE)
        self.zones = []
        self.debut = 0
        if self.joueurs is None:
            texte = self.erreur or "CHARGEMENT..."
            dessiner_texte(image, texte, cadre.centerx, cadre.centery, 3,
                           config.ROUGE if self.erreur else config.CYAN, lueur=False)
            return
        pas = 84 if vertical else 58
        visibles = (cadre.h - 40) // pas if vertical else 9
        self.debut = max(0, min(self.indice - visibles // 2, len(self.joueurs) - visibles))
        for k, joueur in enumerate(self.joueurs[self.debut:self.debut + visibles]):
            i = self.debut + k
            rect = pygame.Rect(cadre.x + 24, cadre.y + 24 + k * pas, cadre.w - 48, pas - 8)
            self.zones.append(rect)
            couleur = couleur_profil(joueur["couleur"])
            choisi = i == self.indice
            pygame.draw.rect(image, (16, 4, 36), rect, border_radius=8)
            if choisi:
                lueur = halo_rect(rect.w, rect.h, attenuer(couleur, 0.7), rayon=8)
                image.blit(lueur, (rect.x - 16, rect.y - 16), special_flags=pygame.BLEND_RGB_ADD)
            pygame.draw.rect(image, couleur if choisi else attenuer(couleur, 0.4), rect, 2,
                             border_radius=8)
            dessiner_banniere(image, joueur.get("banniere", ""),
                              pygame.Rect(rect.x + 44, rect.y + 7, 360, rect.h - 14), self.temps,
                              cadre=False, voile=130)
            y_nom = rect.y + 24 if vertical else rect.centery
            pygame.draw.circle(image, couleur, (rect.x + 26, y_nom), 10)
            dessiner_texte(image, joueur["pseudo"].upper(), rect.x + 52, y_nom, 3, couleur,
                           ancrage="gauche", lueur=choisi)
            # Format vertical : rang et succès sur une deuxième ligne.
            x_rang, y_infos = (rect.x + 52, rect.bottom - 16) if vertical else (rect.x + 430, rect.centery)
            dessiner_texte(image, f"RANG {joueur['niveau']}", x_rang, y_infos, 2,
                           config.AMBRE, ancrage="gauche", lueur=False)
            total_succes = joueur.get("total_succes", NOMBRE_SUCCES)
            dessiner_texte(image, f"SUCCES {joueur['succes']}/{total_succes}", x_rang + 130, y_infos, 2,
                           config.OR, ancrage="gauche", lueur=False)
            if joueur.get("en_ligne"):
                dessiner_texte(image, "EN LIGNE", rect.right - 20, y_infos, 2, config.VERT,
                               ancrage="droite", lueur=False)
            else:
                dessiner_texte(image, date_courte(joueur["vu_le"]), rect.right - 20,
                               y_infos, 2, GRIS, ancrage="droite", lueur=False)
        self.pied(image, f"{len(self.joueurs)} JOUEURS    ENTREE : VOIR LE PROFIL    ECHAP : RETOUR")


class EcranProfil(EcranEnLigneBase):
    """Page de profil d'un joueur."""

    vertical = True               # dessiné aussi au format vertical (téléphone)

    titre = "PROFIL"
    onglet = ""

    def __init__(self, app, pseudo, retour="hub"):
        super().__init__(app)
        self.pseudo = pseudo
        self.retour = retour
        self.profil = None
        self.erreur = ""
        self.chargement = False
        self.prochaine_tentative = 0.0
        self.choix = 0
        self.fiche_ouverte = False
        self.zones_succes = []           # (indice dans la liste, Rect) des succès affichés
        self.premiere_ligne = 0          # grille des succès : première ligne affichée (défilement)
        self.lignes_visibles = LIGNES_SUCCES
        self.rect_fiche = pygame.Rect(0, 0, 650, 360)
        self.rect_fiche.center = (850, 447)
        self._charger()

    def _charger(self):
        """But : demander les donnees au serveur, une requete a la fois. Entree(s) : aucune. Sortie : aucune."""
        if self.chargement:
            return
        self.chargement = True
        self.app.en_ligne.appeler("GET", f"/api/joueurs/{self.pseudo}", rappel=self._recu)

    def _recu(self, resultat):
        self.chargement = False
        if resultat["ok"]:
            self.profil = resultat["donnees"]
        else:
            self.erreur = "SERVEUR EN MAINTENANCE" if resultat.get("maintenance") else resultat["erreur"]
            if resultat.get("maintenance"):
                self.prochaine_tentative = time.monotonic() + 5

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        if self.erreur == "SERVEUR EN MAINTENANCE" and time.monotonic() >= self.prochaine_tentative:
            self._charger()
        entrees = self.app.entrees
        retour = entrees.vient_d_appuyer("retour")
        valider = entrees.vient_d_appuyer("valider")
        if retour:
            if self.fiche_ouverte:
                self.fiche_ouverte = False
            else:
                self._retour_ecran()
                return
        if self.fiche_ouverte and 1 in entrees.clics:
            if not self.rect_fiche.collidepoint(entrees.souris):
                self.fiche_ouverte = False
            return
        if not self.fiche_ouverte and entrees.molette:          # molette ou doigt glissé
            self.premiere_ligne -= entrees.molette
        if not self.fiche_ouverte and self.profil and entrees.souris_bougee and not entrees.tactile:
            for i, zone in self.zones_succes:
                if zone.collidepoint(entrees.souris):
                    self.choix = i
                    break
        clic = 1 in entrees.clics
        if clic and not self.fiche_ouverte:
            for i, zone in self.zones_succes:
                if zone.collidepoint(entrees.souris):
                    self.choix = i
                    valider = True
                    break
        if valider and self.profil:
            self.fiche_ouverte = not self.fiche_ouverte
            if self.fiche_ouverte:
                self.app.audio.jouer("menu_ok")
            return
        ancien = self.choix
        total = max(1, len(self.profil["succes"]) if self.profil else 1)
        if entrees.vient_d_appuyer("droite"):
            self.choix = (self.choix + 1) % total
        if entrees.vient_d_appuyer("gauche"):
            self.choix = (self.choix - 1) % total
        if entrees.vient_d_appuyer("bas"):
            self.choix = (self.choix + colonnes_succes()) % total
        if entrees.vient_d_appuyer("haut"):
            self.choix = (self.choix - colonnes_succes()) % total
        if self.choix != ancien:
            self.app.audio.jouer("menu_nav")
            ligne = self.choix // colonnes_succes()          # le succès choisi reste visible
            self.premiere_ligne = min(max(self.premiere_ligne, ligne - self.lignes_visibles + 1), ligne)

    def _retour_ecran(self):
        """But : revenir a la liste ou au hub. Entree(s) : aucune. Sortie : aucune."""
        if self.retour == "joueurs":
            self.app.remplacer(EcranJoueurs(self.app))
        else:
            self.retour_accueil()

    def dessiner(self, image):
        self.dessiner_fond(image, "PROFIL")
        if self.profil is None:
            dessiner_texte(image, self.erreur or "CHARGEMENT...", config.LARGEUR / 2, 360, 3,
                           config.ROUGE if self.erreur else config.CYAN, lueur=False)
            return
        p = self.profil
        couleur = couleur_profil(p["couleur"])
        vertical = est_vertical()
        if vertical:                     # téléphone : tout l'un sous l'autre
            from ecrans.menus import bas_contenu, haut_contenu
            y = haut_contenu() + 12
            carte = pygame.Rect(20, y, config.LARGEUR - 40, 270)
            bloc = pygame.Rect(20, carte.bottom + 12, config.LARGEUR - 40, 150)
            records = pygame.Rect(20, bloc.bottom + 12, config.LARGEUR - 40, 110)
            zone_succes = pygame.Rect(20, records.bottom + 12, config.LARGEUR - 40,
                                      bas_contenu() - records.bottom - 24)
            self.rect_fiche.size = (config.LARGEUR - 30, 440)
            self.rect_fiche.center = (config.LARGEUR // 2, config.HAUTEUR // 2)
        else:
            carte = pygame.Rect(30, 96, 400, 270)
            bloc = pygame.Rect(30, 382, 400, 290)
            records = pygame.Rect(450, 96, 800, 110)
            zone_succes = pygame.Rect(450, 222, 800, 450)
        # Carte d'identité.
        panneau(image, carte, couleur)
        dessiner_banniere(image, p.get("banniere", ""),
                          pygame.Rect(carte.x + 20, carte.y + 16, carte.w - 40, 60), self.temps)
        dessiner_texte(image, p["pseudo"].upper(), carte.centerx, carte.y + 46,
                       6 if len(p["pseudo"]) <= 8 else 4, couleur)
        dessiner_texte(image, f"RANG {p['niveau']}", carte.centerx, carte.y + 104, 4, config.AMBRE)
        barre(image, pygame.Rect(carte.x + 40, carte.y + 134, carte.w - 80, 10),
              (p["xp"] - p["xp_niveau"]) / max(1, p["xp_suivant"] - p["xp_niveau"]), config.AMBRE)
        dessiner_texte(image, f"{p['xp'] - p['xp_niveau']} / {p['xp_suivant'] - p['xp_niveau']} "
                       f"XP AVANT LE RANG {p['niveau'] + 1}", carte.centerx, carte.y + 160,
                       2, GRIS, lueur=False)
        etat = "EN LIGNE" if p.get("en_ligne") else f"VU LE {date_courte(p['vu_le'])}"
        dessiner_texte(image, etat, carte.centerx, carte.y + 192, 2,
                       config.VERT if p.get("en_ligne") else GRIS, lueur=False)
        from reseau.profil import SKINS_PAR_CODE
        skin = SKINS_PAR_CODE.get(p.get("skin", "neon"), SKINS_PAR_CODE["neon"])
        dessiner_texte(image, f"INSCRIT LE {date_courte(p['cree_le'])}", carte.centerx,
                       carte.y + 220, 2, GRIS, lueur=False)
        dessiner_texte(image, f"SKIN : {skin['nom']}", carte.centerx, carte.y + 248, 2,
                       config.ROSE, lueur=False)
        # Statistiques.
        stats = p["stats"]
        panneau(image, bloc, config.CYAN)
        victoires = stats.get("victoires", {})
        boss = stats.get("boss_vaincus", {})
        lignes = [("PARTIES", stats["parties"]), ("BRIQUES", stats["briques"]),
                  ("TEMPS DE JEU", duree_lisible(stats["temps"])),
                  ("MEILLEUR COMBO", stats["meilleur_combo"]),
                  ("SUPERNOVAS", stats["supernovas"]),
                  ("BOSS VAINCUS", sum(boss.values())),
                  ("DUELS / COURSES", f"{victoires.get('duel', 0)} / {victoires.get('course', 0)}")]
        series = p.get("series")
        if series:
            jour, semaine = series.get("jour", {}), series.get("semaine", {})
            lignes.append(("SERIE DEFI", f"{jour.get('en_cours', 0)} J  MAX {jour.get('record', 0)}"))
            lignes.append(("SERIE SEMAINE",
                           f"{semaine.get('en_cours', 0)} S  MAX {semaine.get('record', 0)}"))
        if p.get("classees"):
            from reseau.classee import division
            lignes.append(("CLASSEE", f"{division(p['elo'])[0]} {p['elo']}"))
        colonnes = 2 if vertical else 1
        par_colonne = (len(lignes) + colonnes - 1) // colonnes
        pas = min(29, (bloc.h - 48) / max(1, par_colonne - 1))
        largeur_colonne = bloc.w // colonnes
        for i, (libelle, valeur) in enumerate(lignes):
            colonne, rang = divmod(i, par_colonne)
            y = bloc.y + 26 + rang * pas
            x = bloc.x + colonne * largeur_colonne
            dessiner_texte(image, libelle, x + 24, y, 2, GRIS, ancrage="gauche", lueur=False)
            dessiner_texte(image, str(valeur), x + largeur_colonne - 24, y, 2, config.BLANC,
                           ancrage="droite", lueur=False)
        # Records.
        panneau(image, records, config.AMBRE)
        for i, (mode, valeur) in enumerate(p["records"].items()):
            ecart = records.w // max(1, len(p["records"]))
            x = records.x + ecart // 2 + i * ecart
            dessiner_texte(image, NOMS_MODES.get(mode, mode.upper()), x, records.y + 34, 2, GRIS,
                           lueur=False)
            texte = f"{valeur:07d}"
            echelle = 3 if len(texte) * 18 < ecart - 6 else 2      # étroit : chiffres plus petits
            dessiner_texte(image, texte if echelle == 3 else str(valeur), x, records.y + 74, echelle,
                           config.AMBRE)
        self._grille_succes(image, zone_succes)

    def _grille_succes(self, image, cadre):
        """But : dessiner la grille et sa fiche. Entree(s) : image, cadre. Sortie : aucune."""
        succes = self.profil["succes"]
        obtenus = sum(s.get("palier", 1) if s.get("seuils") else 1 for s in succes if s["obtenu_le"])
        total = sum(len(s["seuils"]) if s.get("seuils") else 1 for s in succes)
        panneau(image, cadre, config.OR)
        dessiner_texte(image, f"SUCCES  {obtenus} / {total}", cadre.centerx, cadre.y + 24,
                       2, config.OR, lueur=False)
        colonnes = colonnes_succes()
        largeur = (cadre.w - 40) // colonnes
        haut_case = hauteur_case()
        visibles = min(lignes_succes(), max(1, (cadre.h - 80) // (haut_case + 6)))
        nb_lignes = (len(succes) + colonnes - 1) // colonnes
        self.lignes_visibles = visibles
        self.premiere_ligne = max(0, min(self.premiere_ligne, nb_lignes - visibles))
        debut = self.premiere_ligne * colonnes
        self.zones_succes = []
        for i, entree in enumerate(succes[debut:debut + colonnes * visibles], start=debut):
            ligne, colonne = divmod(i - debut, colonnes)
            rect = pygame.Rect(cadre.x + 20 + colonne * largeur, cadre.y + 46 + ligne * (haut_case + 6),
                               largeur - 8, haut_case)
            self.zones_succes.append((i, rect.copy()))
            self._case_succes(image, rect, entree, i == self.choix)
        if nb_lignes > visibles:             # barre de défilement à droite
            piste = pygame.Rect(cadre.right - 12, cadre.y + 46, 4, visibles * (haut_case + 6) - 6)
            pygame.draw.rect(image, (50, 30, 80), piste, border_radius=2)
            hauteur = max(20, piste.h * visibles // nb_lignes)
            y = piste.y + (piste.h - hauteur) * self.premiere_ligne // max(1, nb_lignes - visibles)
            pygame.draw.rect(image, config.OR, (piste.x, y, 4, hauteur), border_radius=2)
        aide = "GLISSE POUR VOIR LA SUITE" if nb_lignes > visibles and self.app.entrees.tactile \
            else ("TOUCHE UN SUCCES : DETAIL" if self.app.entrees.tactile else "CLIC / ENTREE : DETAIL")
        dessiner_texte(image, aide, cadre.centerx, cadre.bottom - 20, 2, config.BLANC, lueur=False)
        if self.fiche_ouverte and succes:
            self._fiche(image, succes[min(self.choix, len(succes) - 1)])

    def _case_succes(self, image, rect, entree, choisi):
        """But : une case de la grille (icône, nom ; paliers : couleur du palier et barre)."""
        from moteur.icones import dessiner_icone, TROPHEE
        seuils = entree.get("seuils")
        palier = entree.get("palier", 0) if seuils else 0
        obtenu = bool(entree["obtenu_le"])
        couleur = COULEURS_CATEGORIES.get(entree["categorie"], config.CYAN)
        if seuils and palier:
            couleur = COULEURS_PALIERS[palier - 1]
        if not obtenu:
            couleur = (80, 60, 110)
        pygame.draw.rect(image, (16, 4, 36), rect, border_radius=8)
        if choisi:
            lueur = halo_rect(rect.w, rect.h, attenuer(couleur, 0.9), rayon=6)
            image.blit(lueur, (rect.x - 12, rect.y - 12), special_flags=pygame.BLEND_RGB_ADD)
        if palier == 3:                       # platine : un reflet passe sur la case
            x = rect.x + int((self.temps * 90) % (rect.w + 60)) - 30
            reflet = pygame.Rect(max(rect.x + 2, x), rect.y + 2, 10, rect.h - 4).clip(rect.inflate(-4, -4))
            if reflet.w > 0:
                image.fill((30, 60, 55), reflet, special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.rect(image, couleur, rect, 3 if choisi else 2, border_radius=8)
        secret_cache = entree.get("secret") and not obtenu
        if secret_cache or not dessiner_icone(
                image, entree.get("icone", entree["code"]), (rect.centerx, rect.y + 17),
                couleur if obtenu else (95, 75, 130), 2, lueur=obtenu, defaut=TROPHEE):
            dessiner_texte(image, "?", rect.centerx, rect.y + 18, 3, couleur, lueur=False)
        nom = entree["nom"].upper()
        if est_vertical():                   # téléphone : toujours la même taille, sur 2 lignes
            lignes = [l for l in couper_en_lignes(nom, max(1, (rect.w - 12) // 12)) if l]
            echelle, pas = 2, 20
            haut = rect.y + 50 - pas * (len(lignes) - 1) / 2
        else:
            lignes = couper_en_lignes(nom, max(1, (rect.w - 8) // 12))
            echelle = 1 if any(len(l) * 12 > rect.w - 8 for l in lignes) else 2
            if echelle == 1:
                lignes = couper_en_lignes(nom, max(1, (rect.w - 8) // 6))
            lignes = [l for l in lignes if l]
            pas = 9 * echelle
            haut = rect.y + (42 if seuils else 45) - pas * (len(lignes) - 1) / 2
        for n, ligne_texte in enumerate(lignes):
            dessiner_texte(image, ligne_texte, rect.centerx, haut + n * pas,
                           echelle, config.BLANC if obtenu else (110, 90, 140),
                           lueur=False, ombre=False)
        if seuils:                            # barre vers le palier suivant
            barre_rect = pygame.Rect(rect.x + 8, rect.bottom - 8, rect.w - 16, 4)
            pygame.draw.rect(image, (45, 30, 70), barre_rect, border_radius=2)
            part = 1.0 if palier >= 3 else min(1.0, entree.get("valeur", 0) / max(1, seuils[palier]))
            teinte = COULEURS_PALIERS[min(palier, 2)]
            if part > 0:
                image.fill(teinte, (barre_rect.x, barre_rect.y, max(2, int(barre_rect.w * part)), 4))

    def _fiche(self, image, entree):
        """But : fiche d'un succès ; pour un succès à paliers, les 3 paliers et la progression."""
        from moteur.icones import dessiner_icone, TROPHEE
        r = self.rect_fiche
        pygame.draw.rect(image, (12, 2, 28), r, border_radius=10)
        panneau(image, r, config.CYAN)
        obtenu = bool(entree["obtenu_le"])
        seuils = entree.get("seuils")
        palier = entree.get("palier", 0) if seuils else 0
        couleur = COULEURS_CATEGORIES.get(entree["categorie"], config.CYAN) if obtenu else GRIS
        if seuils and palier:
            couleur = COULEURS_PALIERS[palier - 1]
        if not (entree.get("secret") and not obtenu):
            dessiner_icone(image, entree.get("icone", entree["code"]), (r.x + 60, r.y + 60),
                           couleur, 5, lueur=obtenu, defaut=TROPHEE)
        dessiner_texte(image, entree["nom"].upper(), r.centerx, r.y + 42, 3, config.BLANC)
        titre = entree["categorie"].upper()
        if seuils:
            titre = NOMS_PALIERS[palier - 1] if palier else "AUCUN PALIER"
        dessiner_texte(image, titre, r.centerx, r.y + 88, 2, couleur, lueur=False)
        if not seuils:
            lignes = couper_en_lignes(entree["description"].upper(), max(10, (r.w - 40) // 12), 5)
            for i, ligne_texte in enumerate(lignes):
                dessiner_texte(image, ligne_texte, r.centerx, r.y + 150 + i * 32, 2, config.BLANC,
                               lueur=False)
            etat = f"OBTENU LE {date_courte(entree['obtenu_le'])}" if obtenu else "PAS ENCORE OBTENU"
            dessiner_texte(image, etat, r.centerx, r.bottom - 42, 2, couleur, lueur=False)
            return
        # Les trois paliers, puis la barre de progression vers le suivant.
        valeur = entree.get("valeur", 0)
        prochain = f"{seuils[min(palier, 2)]:,}".replace(",", " ")
        dessiner_texte(image, entree["description"].upper().replace("...", prochain), r.centerx, r.y + 126,
                       2, config.BLANC, lueur=False)
        for k, (nom, seuil) in enumerate(zip(NOMS_PALIERS, seuils)):
            y = r.y + 172 + k * 40
            atteint = k < palier
            teinte = COULEURS_PALIERS[k] if atteint else (110, 90, 140)
            pygame.draw.circle(image, teinte, (r.x + 50, y), 10, 0 if atteint else 2)
            dessiner_texte(image, nom, r.x + 74, y, 3, teinte, ancrage="gauche", lueur=atteint)
            dessiner_texte(image, f"{seuil:,}".replace(",", " "), r.right - 40, y, 3,
                           config.BLANC if atteint else (150, 130, 180), ancrage="droite", lueur=False)
        bas = r.y + 172 + 3 * 40 - 8
        barre_rect = pygame.Rect(r.x + 40, bas, r.w - 80, 14)
        pygame.draw.rect(image, (45, 30, 70), barre_rect, border_radius=7)
        if palier >= 3:
            image.fill(COULEURS_PALIERS[2], barre_rect.inflate(-4, -4))
            texte = f"PLATINE !  {valeur:,}".replace(",", " ")
        else:
            cible = seuils[palier]
            depart = seuils[palier - 1] if palier else 0
            part = max(0.0, min(1.0, (valeur - depart) / max(1, cible - depart)))
            if part > 0:
                interieur = barre_rect.inflate(-4, -4)
                image.fill(COULEURS_PALIERS[palier], (interieur.x, interieur.y,
                                                      max(3, int(interieur.w * part)), interieur.h))
            texte = (f"{valeur:,} / {cible:,}".replace(",", " ") + f"  VERS {NOMS_PALIERS[palier]}")
        dessiner_texte(image, texte, r.centerx, bas + 40, 2, config.BLANC, lueur=False)
