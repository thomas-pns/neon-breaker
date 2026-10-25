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
COLONNES_SUCCES = 7
LIGNES_SUCCES = 5


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
        cadre = pygame.Rect(190, 100, 900, 550)
        panneau(image, cadre, config.ROSE)
        self.zones = []
        self.debut = 0
        if self.joueurs is None:
            texte = self.erreur or "CHARGEMENT..."
            dessiner_texte(image, texte, cadre.centerx, cadre.centery, 3,
                           config.ROUGE if self.erreur else config.CYAN, lueur=False)
            return
        visibles = 9
        self.debut = max(0, min(self.indice - visibles // 2, len(self.joueurs) - visibles))
        for k, joueur in enumerate(self.joueurs[self.debut:self.debut + visibles]):
            i = self.debut + k
            rect = pygame.Rect(cadre.x + 24, cadre.y + 24 + k * 58, cadre.w - 48, 50)
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
            pygame.draw.circle(image, couleur, (rect.x + 26, rect.centery), 10)
            dessiner_texte(image, joueur["pseudo"].upper(), rect.x + 52, rect.centery, 3, couleur,
                           ancrage="gauche", lueur=choisi)
            dessiner_texte(image, f"RANG {joueur['niveau']}", rect.x + 430, rect.centery, 2,
                           config.AMBRE, ancrage="gauche", lueur=False)
            total_succes = joueur.get("total_succes", NOMBRE_SUCCES)
            dessiner_texte(image, f"SUCCES {joueur['succes']}/{total_succes}", rect.x + 560, rect.centery, 2,
                           config.OR, ancrage="gauche", lueur=False)
            if joueur.get("en_ligne"):
                dessiner_texte(image, "EN LIGNE", rect.right - 20, rect.centery, 2, config.VERT,
                               ancrage="droite", lueur=False)
            else:
                dessiner_texte(image, date_courte(joueur["vu_le"]), rect.right - 20,
                               rect.centery, 2, GRIS, ancrage="droite", lueur=False)
        self.pied(image, f"{len(self.joueurs)} JOUEURS    ENTREE : VOIR LE PROFIL    ECHAP : RETOUR")


class EcranProfil(EcranEnLigneBase):
    """Page de profil d'un joueur."""

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
        self.zones_succes = []
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
        if not self.fiche_ouverte and self.profil and entrees.souris_bougee:
            for i, zone in enumerate(self.zones_succes):
                if zone.collidepoint(entrees.souris):
                    self.choix = i
                    break
        clic = 1 in entrees.clics
        if clic and not self.fiche_ouverte:
            for i, zone in enumerate(self.zones_succes):
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
        total = min(COLONNES_SUCCES * LIGNES_SUCCES, len(self.profil["succes"])) if self.profil else 1
        total = max(1, total)
        if entrees.vient_d_appuyer("droite"):
            self.choix = (self.choix + 1) % total
        if entrees.vient_d_appuyer("gauche"):
            self.choix = (self.choix - 1) % total
        if entrees.vient_d_appuyer("bas"):
            self.choix = (self.choix + COLONNES_SUCCES) % total
        if entrees.vient_d_appuyer("haut"):
            self.choix = (self.choix - COLONNES_SUCCES) % total
        if self.choix != ancien:
            self.app.audio.jouer("menu_nav")

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
        # Carte d'identité.
        carte = pygame.Rect(30, 96, 400, 270)
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
        bloc = pygame.Rect(30, 382, 400, 290)
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
        pas = min(29, (bloc.h - 48) / max(1, len(lignes) - 1))
        for i, (libelle, valeur) in enumerate(lignes):
            y = bloc.y + 26 + i * pas
            dessiner_texte(image, libelle, bloc.x + 24, y, 2, GRIS, ancrage="gauche", lueur=False)
            dessiner_texte(image, str(valeur), bloc.right - 24, y, 2, config.BLANC,
                           ancrage="droite", lueur=False)
        # Records.
        records = pygame.Rect(450, 96, 800, 110)
        panneau(image, records, config.AMBRE)
        for i, (mode, valeur) in enumerate(p["records"].items()):
            ecart = records.w // max(1, len(p["records"]))
            x = records.x + ecart // 2 + i * ecart
            dessiner_texte(image, NOMS_MODES.get(mode, mode.upper()), x, records.y + 34, 2, GRIS,
                           lueur=False)
            dessiner_texte(image, f"{valeur:07d}", x, records.y + 74, 3, config.AMBRE)
        self._grille_succes(image, pygame.Rect(450, 222, 800, 450))

    def _grille_succes(self, image, cadre):
        """But : dessiner la grille et sa fiche. Entree(s) : image, cadre. Sortie : aucune."""
        succes = self.profil["succes"]
        obtenus = sum(1 for s in succes if s["obtenu_le"])
        panneau(image, cadre, config.OR)
        dessiner_texte(image, f"SUCCES  {obtenus} / {len(succes)}", cadre.centerx, cadre.y + 24,
                       2, config.OR, lueur=False)
        largeur = (cadre.w - 40) // COLONNES_SUCCES
        self.zones_succes = []
        for i, entree in enumerate(succes[:COLONNES_SUCCES * LIGNES_SUCCES]):
            ligne, colonne = divmod(i, COLONNES_SUCCES)
            rect = pygame.Rect(cadre.x + 20 + colonne * largeur, cadre.y + 46 + ligne * 70,
                               largeur - 8, 64)
            self.zones_succes.append(rect.copy())
            obtenu = bool(entree["obtenu_le"])
            couleur = COULEURS_CATEGORIES.get(entree["categorie"], config.CYAN)
            if not obtenu:
                couleur = (80, 60, 110)
            choisi = i == self.choix
            pygame.draw.rect(image, (16, 4, 36), rect, border_radius=8)
            if choisi:
                lueur = halo_rect(rect.w, rect.h, attenuer(couleur, 0.9), rayon=6)
                image.blit(lueur, (rect.x - 12, rect.y - 12), special_flags=pygame.BLEND_RGB_ADD)
            pygame.draw.rect(image, couleur, rect, 3 if choisi else 2, border_radius=8)
            from moteur.icones import dessiner_icone, TROPHEE
            secret_cache = entree.get("secret") and not obtenu
            if secret_cache or not dessiner_icone(
                    image, entree["code"], (rect.centerx, rect.y + 17),
                    couleur if obtenu else (95, 75, 130), 2, lueur=obtenu, defaut=TROPHEE):
                dessiner_texte(image, "?", rect.centerx, rect.y + 18, 3, couleur, lueur=False)
            nom = entree["nom"].upper()
            lignes = couper_en_lignes(nom, max(1, (rect.w - 8) // 12))
            echelle = 1 if any(len(l) * 12 > rect.w - 8 for l in lignes) else 2
            if echelle == 1:
                lignes = couper_en_lignes(nom, max(1, (rect.w - 8) // 6))
            lignes = [l for l in lignes if l]
            pas = 9 * echelle
            haut = rect.y + 45 - pas * (len(lignes) - 1) / 2
            for n, ligne_texte in enumerate(lignes):
                dessiner_texte(image, ligne_texte, rect.centerx, haut + n * pas,
                               echelle, config.BLANC if obtenu else (110, 90, 140),
                               lueur=False, ombre=False)
        dessiner_texte(image, "CLIC / ENTREE : DETAIL", cadre.centerx, cadre.bottom - 20,
                       2, config.BLANC, lueur=False)
        if self.fiche_ouverte and succes:
            entree = succes[self.choix]
            pygame.draw.rect(image, (12, 2, 28), self.rect_fiche, border_radius=10)
            panneau(image, self.rect_fiche, config.CYAN)
            obtenu = bool(entree["obtenu_le"])
            couleur = COULEURS_CATEGORIES.get(entree["categorie"], config.CYAN) if obtenu else GRIS
            from moteur.icones import dessiner_icone, TROPHEE
            if not (entree.get("secret") and not obtenu):
                dessiner_icone(image, entree["code"],
                               (self.rect_fiche.x + 60, self.rect_fiche.y + 60),
                               couleur, 5, lueur=obtenu, defaut=TROPHEE)
            dessiner_texte(image, entree["nom"].upper(), self.rect_fiche.centerx,
                           self.rect_fiche.y + 42, 3, config.BLANC)
            dessiner_texte(image, entree["categorie"].upper(), self.rect_fiche.centerx,
                           self.rect_fiche.y + 88, 2, couleur, lueur=False)
            description = entree["description"].upper()
            lignes = couper_en_lignes(description, 50, 5)
            for i, ligne_texte in enumerate(lignes):
                dessiner_texte(image, ligne_texte, self.rect_fiche.centerx,
                               self.rect_fiche.y + 150 + i * 32, 2, config.BLANC, lueur=False)
            etat = f"OBTENU LE {date_courte(entree['obtenu_le'])}" if obtenu else "PAS ENCORE OBTENU"
            dessiner_texte(image, etat, self.rect_fiche.centerx, self.rect_fiche.bottom - 42,
                           2, couleur, lueur=False)
