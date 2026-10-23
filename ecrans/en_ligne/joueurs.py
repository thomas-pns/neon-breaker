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

from moteur import config
from moteur.police_pixel import dessiner_texte
from moteur.rendu import halo_rect, attenuer
from ecrans.hud import panneau, barre
from ecrans.en_ligne.commun import (EcranEnLigneBase, couleur_profil, date_courte,
                                    duree_lisible, NOMS_MODES, GRIS)

COULEURS_CATEGORIES = {"debuts": config.CYAN, "campagne": config.ROSE, "habilete": config.AMBRE,
                       "modes": config.VIOLET, "coop": config.VERT, "collection": config.OR,
                       "endurance": config.BLEU, "secret": (200, 200, 255),
                       "defi": config.ROUGE}
COLONNES_SUCCES = 7


class EcranJoueurs(EcranEnLigneBase):
    """Tous les joueurs du serveur."""

    titre = "JOUEURS"

    def __init__(self, app):
        super().__init__(app)
        self.joueurs = None
        self.erreur = ""
        self.indice = 0
        self.zones = []
        app.en_ligne.appeler("GET", "/api/joueurs", rappel=self._recu)

    def _recu(self, resultat):
        if resultat["ok"]:
            self.joueurs = resultat["donnees"]["joueurs"]
            moi = self.app.en_ligne.pseudo.lower()
            self.indice = next((i for i, j in enumerate(self.joueurs)
                                if j["pseudo"].lower() == moi), 0)
        else:
            self.erreur = resultat["erreur"]

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        entrees = self.app.entrees
        if entrees.vient_d_appuyer("retour"):
            from ecrans.en_ligne.hub import EcranHub
            self.app.remplacer(EcranHub(self.app))
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
            pygame.draw.circle(image, couleur, (rect.x + 26, rect.centery), 10)
            dessiner_texte(image, joueur["pseudo"].upper(), rect.x + 52, rect.centery, 3, couleur,
                           ancrage="gauche", lueur=choisi)
            dessiner_texte(image, f"RANG {joueur['niveau']}", rect.x + 430, rect.centery, 2,
                           config.AMBRE, ancrage="gauche", lueur=False)
            dessiner_texte(image, f"SUCCES {joueur['succes']}/24", rect.x + 560, rect.centery, 2,
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

    def __init__(self, app, pseudo, retour="hub"):
        super().__init__(app)
        self.pseudo = pseudo
        self.retour = retour
        self.profil = None
        self.erreur = ""
        self.choix = 0
        app.en_ligne.appeler("GET", f"/api/joueurs/{pseudo}", rappel=self._recu)

    def _recu(self, resultat):
        if resultat["ok"]:
            self.profil = resultat["donnees"]
        else:
            self.erreur = resultat["erreur"]

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        entrees = self.app.entrees
        if entrees.vient_d_appuyer("retour") or entrees.vient_d_appuyer("valider"):
            if self.retour == "joueurs":
                self.app.remplacer(EcranJoueurs(self.app))
            else:
                from ecrans.en_ligne.hub import EcranHub
                self.app.remplacer(EcranHub(self.app))
            return
        ancien = self.choix
        total = min(COLONNES_SUCCES * 4, len(self.profil["succes"])) if self.profil else 1
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
        dessiner_texte(image, p["pseudo"].upper(), carte.centerx, carte.y + 46,
                       6 if len(p["pseudo"]) <= 8 else 4, couleur)
        dessiner_texte(image, f"RANG {p['niveau']}", carte.centerx, carte.y + 104, 4, config.AMBRE)
        barre(image, pygame.Rect(carte.x + 40, carte.y + 134, carte.w - 80, 10),
              (p["xp"] - p["xp_niveau"]) / max(1, p["xp_suivant"] - p["xp_niveau"]), config.AMBRE)
        dessiner_texte(image, f"{p['xp'] - p['xp_niveau']} / {p['xp_suivant'] - p['xp_niveau']} "
                       f"XP AVANT LE RANG {p['niveau'] + 1}", carte.centerx, carte.y + 160,
                       1, GRIS, lueur=False)
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
                  ("DUELS GAGNES", victoires.get("duel", 0)),
                  ("COURSES GAGNEES", victoires.get("course", 0))]
        for i, (libelle, valeur) in enumerate(lignes):
            y = bloc.y + 30 + i * 32
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
        succes = self.profil["succes"]
        obtenus = sum(1 for s in succes if s["obtenu_le"])
        panneau(image, cadre, config.OR)
        dessiner_texte(image, f"SUCCES  {obtenus} / {len(succes)}", cadre.centerx, cadre.y + 24,
                       2, config.OR, lueur=False)
        largeur = (cadre.w - 40) // COLONNES_SUCCES
        for i, entree in enumerate(succes[:COLONNES_SUCCES * 4]):
            ligne, colonne = divmod(i, COLONNES_SUCCES)
            rect = pygame.Rect(cadre.x + 20 + colonne * largeur, cadre.y + 48 + ligne * 82,
                               largeur - 8, 72)
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
            initiale = entree["nom"][:2] if obtenu else "?"
            dessiner_texte(image, initiale, rect.centerx, rect.y + 26, 4, couleur, lueur=obtenu)
            dessiner_texte(image, entree["nom"][:8], rect.centerx, rect.bottom - 14, 2,
                           config.BLANC if obtenu else (110, 90, 140), lueur=False, ombre=False)
        entree = succes[self.choix] if self.choix < len(succes) else None
        if entree:
            texte = entree["nom"] + " : " + entree["description"].upper()
            if entree["obtenu_le"]:
                texte += f"  ({date_courte(entree['obtenu_le'])})"
            dessiner_texte(image, texte[:62], cadre.centerx, cadre.bottom - 20, 2, config.BLANC,
                           lueur=False)
