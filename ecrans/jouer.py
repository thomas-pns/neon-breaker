# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Onglet JOUER (2.1) : un carrousel de grandes cartes, en trois familles
    (SOLO, EN LIGNE, DÉFIS). La carte du milieu est grande et détaillée
    (progression, records, division classée...), les autres défilent sur
    les côtés. ← → : carte ; ↑ ↓ : famille ; Entrée : jouer.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 25/10/2026
"""

import math

import pygame

from moteur import config
from moteur.icones import dessiner_icone, TROPHEE
from moteur.police_pixel import dessiner_texte
from moteur.rendu import attenuer
from ecrans.hud import barre, dessiner_etoiles
from ecrans.menus import (bas_contenu, est_vertical, haut_contenu, EcranMenu, GRIS, JAUNE_SERIE, VIOLET_SERIE, bouton, carte,
                          division_joueur, ecusson, flamme, series_locales)

FAMILLES = [("solo", "SOLO", config.CYAN), ("en_ligne", "EN LIGNE", config.VERT),
            ("defis", "DEFIS", config.AMBRE)]

# code, nom, couleur, icône, deux lignes (petite carte)
CARTES = {
    "solo": [
        ("arcade", "ARCADE", config.CYAN, "multi", ["LE MUR DESCEND", "SANS FIN"]),
        ("campagne", "CAMPAGNE", config.ROSE, "campagne", ["12 NIVEAUX, 3 MONDES", "3 BOSS"]),
        ("hardcore", "HARDCORE", config.ROUGE, "hardcore_monde", ["1 VIE, BALLE +30 %", "SCORE x2"]),
        ("coop", "COOP LOCALE", config.VERT, "coop_boss", ["2 RAQUETTES EN BAS", "SUR CE PC"]),
        ("duel", "DUEL LOCAL", config.VIOLET, "duel_7_0", ["J1 EN BAS, J2 EN HAUT", "SUR CE PC"]),
        ("course", "COURSE LOCALE", config.AMBRE, "vitesse_mode", ["ECRAN PARTAGE", "SUR CE PC"]),
    ],
    "en_ligne": [
        ("duel_en_ligne", "DUEL", config.VIOLET, "duel_7_0", ["CONTRE UN AMI", "PREMIER A 7"]),
        ("classee", "CLASSEE", config.ROSE, "TROPHEE", ["DUEL, COTE ELO", "DIVISIONS"]),
        ("classee_course", "CLASSEE COURSE", config.AMBRE, "TROPHEE", ["COURSE, MEME COTE", "QUE LE DUEL"]),
        ("course_en_ligne", "COURSE", config.AMBRE, "vitesse_mode", ["A QUI VIDE LE PLUS", "VITE SON MUR"]),
        ("coop_en_ligne", "COOP", config.VERT, "coop_boss", ["LA CAMPAGNE", "A DEUX"]),
        ("parties", "PARTIES", config.CYAN, "premiere_en_ligne", ["REJOINDRE UNE", "PARTIE OUVERTE"]),
    ],
    "defis": [
        ("defi", "DEFI DU JOUR", config.AMBRE, "defi_1", ["UNE REGLE SPECIALE", "CLASSEMENT DU JOUR"]),
        ("semaine", "DEFI SEMAINE", VIOLET_SERIE, "semaine_1", ["DEUX REGLES", "CLASSEMENT SEMAINE"]),
    ],
}
DESCRIPTIONS = {
    "arcade": ["LE MUR DESCEND SANS FIN", "TIENS LE PLUS LONGTEMPS", "SCORE ET VAGUES"],
    "hardcore": ["1 VIE, BALLE +30 %", "MALUS SEULEMENT", "SCORE x2"],
    "coop": ["DEUX RAQUETTES EN BAS", "VIES ET SCORE COMMUNS", "J1 Q D Z    J2 ← → ↑"],
    "duel": ["J1 EN BAS, J2 EN HAUT", "MALUS POUR L'AUTRE", "PREMIER A 7 POINTS"],
    "course": ["ECRAN PARTAGE", "COMBO 5 = ATTAQUE", "2 MANCHES GAGNANTES"],
    "duel_en_ligne": ["CHACUN SE VOIT EN BAS", "MALUS POUR L'AUTRE", "PREMIER A 7 POINTS"],
    "course_en_ligne": ["CHACUN SON MUR", "COMBO 5 = ATTAQUE", "2 MANCHES GAGNANTES"],
    "coop_en_ligne": ["LA CAMPAGNE A DEUX", "VIES ET SCORE COMMUNS", "NIVEAU AU CHOIX"],
    "parties": ["LISTE DES PARTIES", "OUVERTES PAR LES AUTRES", "REJOINS OU CREE"],
}
GRANDE, PETITE = (420, 450), (240, 300)
ECART = 345
Y_CARTES = 360


def tailles():
    """But : (GRANDE, PETITE, ECART) : plus grandes au format vertical (plus de hauteur)."""
    if est_vertical():
        return (480, 540), (260, 330), 390
    return GRANDE, PETITE, ECART


def y_cartes():
    """But : hauteur du centre des cartes (format paysage, ou milieu du contenu en vertical)."""
    if not est_vertical():
        return Y_CARTES
    return (haut_contenu() + 90 + bas_contenu() - 120) // 2


def icone(image, code, centre, couleur, echelle):
    dessiner_icone(image, code, (int(centre[0]), int(centre[1])), couleur, echelle, defaut=TROPHEE)


class EcranJouer(EcranMenu):
    """
    Carrousel des modes. Attributs : famille (int), indices (list : carte choisie
    dans chaque famille), position (float : carte affichée, glisse vers l'indice).
    """

    vertical = True

    onglet = "JOUER"

    def __init__(self, app, famille="solo"):
        super().__init__(app)
        codes = [f[0] for f in FAMILLES]
        self.famille = codes.index(famille) if famille in codes else 0
        self.indices = [1, 1, 0]           # la carte phare au milieu : CAMPAGNE, CLASSEE, DEFI
        self.position = float(self.indices[self.famille])
        self.zones = []
        self.zone_bouton = None
        self.zones_familles = []

    # --- Données ------------------------------------------------------------------------

    def cartes(self):
        return CARTES[FAMILLES[self.famille][0]]

    def _progression_campagne(self):
        from jeu.niveau import charger_campagne
        from jeu.modes.campagne import nombre_etoiles
        niveaux = charger_campagne()
        indice = min(self.app.niveau_debloque("campagne"), len(niveaux) - 1)
        etoiles = {int(k): int(v) for k, v in self.app.donnees.get("etoiles", {}).get("campagne", {}).items()}
        boss_vaincus = sum(1 for i, n in enumerate(niveaux) if n.boss and etoiles.get(i, 0) & 1)
        total_boss = sum(1 for n in niveaux if n.boss)
        return niveaux, indice, etoiles, sum(nombre_etoiles(m) for m in etoiles.values()), \
            boss_vaincus, total_boss

    # --- Actions -----------------------------------------------------------------------

    def lancer(self, code):
        from ecrans.partie import EcranPartie
        from ecrans.modes import fabrique_mode
        app = self.app
        self.app.audio.jouer("menu_ok")
        if code in ("campagne", "coop"):
            from ecrans.carte import EcranCarte
            app.remplacer(EcranCarte(app, code))
        elif code in ("arcade", "hardcore", "duel", "course", "defi", "semaine"):
            app.remplacer(EcranPartie(app, fabrique_mode(code)))
        else:
            self._en_ligne(code)

    def _en_ligne(self, code):
        app = self.app
        infos = app.en_ligne.mise_a_jour_requise()
        if infos:
            from ecrans.mise_a_jour import EcranMiseAJour
            app.empiler(EcranMiseAJour(app, infos))
            return
        if not app.en_ligne.jeton:
            from ecrans.en_ligne.connexion import EcranConnexion
            app.remplacer(EcranConnexion(app))
            return
        if app.en_ligne.protege():
            self.message = "VERSION DE TEST : PAS DE PARTIE EN LIGNE SUR LE VRAI SERVEUR"
            self.minuteur = 3.0
            app.audio.jouer("metal")
            return
        from ecrans.en_ligne.salons import EcranSalons, EcranFileClassee
        if code in ("classee", "classee_course"):
            # il entre dans la file dès la connexion
            app.remplacer(EcranFileClassee(app, "course" if code == "classee_course" else "duel"))
        elif code == "parties":
            app.remplacer(EcranSalons(app))
        else:
            mode = code.replace("_en_ligne", "")
            app.remplacer(EcranSalons(app, creer=mode))

    # --- Boucle ------------------------------------------------------------------------

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        self.minuteur = max(0.0, getattr(self, "minuteur", 0.0) - dt)
        if self.naviguer():
            return
        entrees = self.app.entrees
        if entrees.vient_d_appuyer("retour"):
            self.aller("ACCUEIL")
            return
        cartes = self.cartes()
        indice = self.indices[self.famille]
        ancien = (self.famille, indice)
        if entrees.vient_d_appuyer("gauche"):
            indice = max(0, indice - 1)
        if entrees.vient_d_appuyer("droite"):
            indice = min(len(cartes) - 1, indice + 1)
        famille = self.famille
        if entrees.vient_d_appuyer("haut"):
            famille = (famille - 1) % len(FAMILLES)
        if entrees.vient_d_appuyer("bas"):
            famille = (famille + 1) % len(FAMILLES)
        if entrees.balayage:                 # doigt glissé vers la gauche : carte suivante
            indice = max(0, min(len(cartes) - 1, indice - entrees.balayage))
        if 1 in entrees.clics:
            for i, zone in enumerate(self.zones_familles):
                if zone.collidepoint(entrees.souris):
                    famille = i
            for k, zone in self.zones:
                if zone.collidepoint(entrees.souris) and k != indice:
                    indice = k
        if famille != self.famille:
            self.indices[self.famille] = indice
            self.famille = famille
            indice = self.indices[famille]
            self.position = float(indice)
        self.indices[self.famille] = indice
        if (self.famille, indice) != ancien:
            self.app.audio.jouer("menu_nav")
        self.position += (indice - self.position) * min(1.0, dt * 12)
        clic_bouton = 1 in entrees.clics and self.zone_bouton is not None \
            and self.zone_bouton.collidepoint(entrees.souris) and (self.famille, indice) == ancien
        if entrees.tactile and 1 in entrees.clics and (self.famille, indice) == ancien:
            # Au doigt : toucher la carte du milieu lance aussi le mode (cible plus grande).
            clic_bouton = clic_bouton or any(k == indice and zone.collidepoint(entrees.souris)
                                             for k, zone in self.zones)
        if entrees.vient_d_appuyer("valider") or clic_bouton:
            self.lancer(self.cartes()[indice][0])

    # --- Dessin ------------------------------------------------------------------------

    def dessiner(self, image):
        self.dessiner_fond(image)
        self.zones_familles = []
        y_familles = haut_contenu() + 30
        for k, (_, nom, couleur) in enumerate(FAMILLES):
            cx = config.LARGEUR / 2 + (k - 1) * (250 if est_vertical() else 210)
            actif = k == self.famille
            zone = dessiner_texte(image, nom, cx, y_familles, 3, couleur if actif else GRIS, lueur=actif)
            self.zones_familles.append(zone.inflate(30, 30))
            if actif:
                pygame.draw.line(image, couleur, (cx - 70, y_familles + 22), (cx + 70, y_familles + 22), 3)
        cartes = self.cartes()
        indice = self.indices[self.famille]
        self.zones = []
        self.zone_bouton = None
        ordre = sorted(range(len(cartes)), key=lambda k: -abs(k - self.position))
        for k in ordre:
            self._dessiner_carte(image, k, cartes[k], k - self.position, k == indice)
        n = len(cartes)
        y_points = y_cartes() + tailles()[0][1] // 2 + 27
        for k in range(n):
            pygame.draw.circle(image, config.ROSE if k == indice else (80, 60, 120),
                               (int(config.LARGEUR / 2 - (n - 1) * 12 + k * 24), y_points), 6)
        if getattr(self, "minuteur", 0) > 0:
            dessiner_texte(image, self.message, config.LARGEUR / 2, y_points + 38, 2, config.ROSE,
                           lueur=False)
        elif self.app.entrees.tactile:
            dessiner_texte(image, "GLISSE POUR CHANGER DE MODE", config.LARGEUR / 2, y_points + 38, 2,
                           GRIS, lueur=False)
        elif math.sin(self.temps * 4) > -0.5:
            dessiner_texte(image, "← → : CHOISIR     ↑ ↓ : SOLO / EN LIGNE / DEFIS     ENTREE : JOUER",
                           config.LARGEUR / 2, y_points + 38, 2, GRIS, lueur=False)
        self.dessiner_barre(image)

    def _dessiner_carte(self, image, k, donnees, ecart, choisie):
        code, nom, couleur, code_icone, lignes = donnees
        grande, petite, espacement = tailles()
        if est_vertical() and abs(ecart) > 1.3:
            return                          # écran étroit : seulement les deux voisines
        proche = max(0.0, 1.0 - abs(ecart))
        largeur = int(petite[0] + (grande[0] - petite[0]) * proche)
        hauteur = int(petite[1] + (grande[1] - petite[1]) * proche)
        decalage = ecart * espacement + (45 * (1 if ecart > 0 else -1) * min(1.0, abs(ecart)))
        rect = pygame.Rect(0, 0, largeur, hauteur)
        rect.center = (int(config.LARGEUR / 2 + decalage), y_cartes())
        if rect.right < -20 or rect.left > config.LARGEUR + 20:
            return
        self.zones.append((k, rect))
        carte(image, rect, couleur if proche > 0.5 else attenuer(couleur, 0.7), choisie and proche > 0.8)
        if choisie and abs(ecart) < 0.3:
            self._detail(image, rect, code, nom, couleur, code_icone)
            return
        icone(image, code_icone, (rect.centerx, rect.y + 95), couleur, 6)
        dessiner_texte(image, nom, rect.centerx, rect.y + 180, 3 if len(nom) <= 11 else 2, couleur)
        for j, ligne in enumerate(self._lignes_petite(code, lignes)):
            dessiner_texte(image, ligne, rect.centerx, rect.y + 216 + j * 26, 2, GRIS, lueur=False)

    def _lignes_petite(self, code, lignes):
        record = self.app.meilleur_score(code) if code in ("arcade", "hardcore") else 0
        if record:
            return [lignes[0], f"RECORD {record}"]
        if code == "campagne":
            _, indice, _, total, _, _ = self._progression_campagne()
            return [f"NIVEAU {indice + 1}", f"{total} ETOILES"]
        return lignes

    def _bouton(self, image, rect, texte, couleur):
        b = pygame.Rect(0, 0, 360, 76) if est_vertical() else pygame.Rect(0, 0, 260, 52)
        b.midbottom = (rect.centerx, rect.bottom - 20)
        bouton(image, b, texte, couleur)
        self.zone_bouton = b

    def _detail(self, image, r, code, nom, couleur, code_icone):
        dessiner_texte(image, nom, r.centerx, r.y + 38, 5 if len(nom) <= 10 else 4, couleur)
        if code == "campagne":
            self._detail_campagne(image, r, couleur)
        elif code in ("classee", "classee_course"):
            self._detail_classee(image, r, couleur)
        elif code in ("defi", "semaine"):
            self._detail_defi(image, r, code, couleur)
        else:
            icone(image, code_icone, (r.centerx, r.y + 130), couleur, 8)
            for j, ligne in enumerate(DESCRIPTIONS.get(code, [])):
                dessiner_texte(image, ligne, r.centerx, r.y + 220 + j * 30, 2, config.BLANC, lueur=False)
            record = self.app.meilleur_score(code) if code in ("arcade", "hardcore") else 0
            if record:
                dessiner_texte(image, f"RECORD  {record}", r.centerx, r.y + 330, 3, config.AMBRE)
            en_ligne = code.endswith("_en_ligne") or code == "parties"
            self._bouton(image, r, "CREER" if code.endswith("_en_ligne") else
                         ("VOIR" if code == "parties" else "JOUER"), couleur)
            if en_ligne and not self.app.en_ligne.jeton:
                dessiner_texte(image, "CONNEXION REQUISE", r.centerx, r.bottom - 92, 2, config.ROSE,
                               lueur=False)

    def _detail_campagne(self, image, r, couleur):
        from ecrans.carte import NOMS_MONDES
        niveaux, indice, etoiles, total, boss, total_boss = self._progression_campagne()
        niveau = niveaux[indice]
        icone(image, "campagne", (r.centerx, r.y + 110), couleur, 7)
        dessiner_texte(image, f"MONDE {niveau.monde}  {NOMS_MONDES.get(niveau.monde, '')}", r.centerx,
                       r.y + 180, 3, config.CYAN)
        nom = niveau.nom.split("  ")[-1] if "  " in niveau.nom else niveau.nom
        dessiner_texte(image, f"NIVEAU {indice + 1}  {nom}"[:26], r.centerx, r.y + 212, 2, config.BLANC,
                       lueur=False)
        dessiner_etoiles(image, 0, (r.centerx, r.y + 250), 14, masque=etoiles.get(indice, 0))
        stats = [("ETOILES", f"{total} / {3 * len(niveaux)}"), ("BOSS VAINCUS", f"{boss} / {total_boss}"),
                 ("MEILLEUR SCORE", str(self.app.meilleur_score("campagne")))]
        for k, (a, b) in enumerate(stats):
            dessiner_texte(image, a, r.x + 50, r.y + 290 + k * 28, 2, GRIS, ancrage="gauche", lueur=False)
            dessiner_texte(image, b, r.right - 50, r.y + 290 + k * 28, 2, config.BLANC, ancrage="droite",
                           lueur=False)
        self._bouton(image, r, "CONTINUER" if indice else "COMMENCER", couleur)

    def _detail_classee(self, image, r, couleur):
        from reseau.classee import division
        en_ligne = self.app.en_ligne
        if not en_ligne.jeton:
            icone(image, "TROPHEE", (r.centerx, r.y + 140), couleur, 9)
            dessiner_texte(image, "DUEL CONTRE UN JOUEUR", r.centerx, r.y + 240, 2, config.BLANC, lueur=False)
            dessiner_texte(image, "DE TON NIVEAU", r.centerx, r.y + 266, 2, config.BLANC, lueur=False)
            dessiner_texte(image, "CONNEXION REQUISE", r.centerx, r.bottom - 92, 2, config.ROSE, lueur=False)
            self._bouton(image, r, "SE CONNECTER", couleur)
            return
        nom_division, couleur_division, cote = division_joueur(self.app)
        _, _, minimum, suivante = division(cote)
        import datetime
        from reseau.classee import jours_avant_fin, nom_saison
        aujourd_hui = datetime.date.today()
        jours = jours_avant_fin(aujourd_hui)
        dessiner_texte(image, f"{nom_saison(aujourd_hui)}  -  FIN DANS {jours} J", r.centerx, r.y + 72, 2,
                       config.AMBRE if jours <= 3 else GRIS, lueur=False)
        ecusson(image, (r.x + 100, r.y + 150), 56, couleur_division, cote, 3)
        dessiner_texte(image, nom_division, r.x + 100, r.y + 228, 3 if len(nom_division) < 8 else 2,
                       couleur_division)
        victoires = getattr(en_ligne, "classees_victoires", 0)
        parties = getattr(en_ligne, "classees", 0)
        recents = getattr(en_ligne, "classees_recents", "")
        serie = len(recents) - len(recents.rstrip("V")) if recents.endswith("V") else 0
        stats = [("BILAN", f"{victoires}V {parties - victoires}D"),
                 ("TAUX", f"{round(100 * victoires / parties)} %" if parties else "-"),
                 ("SERIE", f"{serie} V" if serie else "-"),
                 ("RECORD", str(getattr(en_ligne, "elo_max", cote)))]
        for k, (a, b) in enumerate(stats):
            dessiner_texte(image, a, r.x + 190, r.y + 100 + k * 36, 2, GRIS, ancrage="gauche", lueur=False)
            dessiner_texte(image, b, r.right - 26, r.y + 100 + k * 36, 3,
                           config.VERT if a == "SERIE" and serie else config.BLANC,
                           ancrage="droite", lueur=False)
        if parties < 10:
            dessiner_texte(image, f"PLACEMENT : {parties} / 10 PARTIES", r.centerx, r.y + 284, 2,
                           config.AMBRE, lueur=False)
        elif suivante:
            barre(image, pygame.Rect(r.x + 40, r.y + 262, r.w - 80, 8),
                  (cote - minimum) / max(1, suivante - minimum), couleur_division)
            dessiner_texte(image, f"DIVISION SUIVANTE DANS {suivante - cote} POINTS", r.centerx,
                           r.y + 284, 2, config.OR, lueur=False)
        for k, resultat in enumerate(recents[-5:]):
            case = pygame.Rect(0, 0, 34, 26)
            case.center = (r.centerx - 80 + k * 40, r.y + 326)
            teinte = config.VERT if resultat == "V" else config.ROUGE
            pygame.draw.rect(image, teinte, case, 2, border_radius=5)
            dessiner_texte(image, resultat, case.centerx, case.centery, 2, teinte, lueur=False)
        self._bouton(image, r, "CHERCHER", couleur)

    def _detail_defi(self, image, r, code, couleur):
        from jeu.modes import defi as d
        if code == "defi":
            jour = d.jour_du_defi()
            modificateurs = [d.defi_pour(jour)[1]]
            titre = "DU " + "/".join(reversed(jour.split("-")[1:]))
            serie, teinte, unite = series_locales(self.app)[0], JAUNE_SERIE, "J"
        else:
            jour = d.semaine_du_defi()
            modificateurs = d.defi_semaine_pour(jour)[1]
            titre = "SEMAINE " + jour.split("-W")[-1]
            serie, teinte, unite = series_locales(self.app)[1], VIOLET_SERIE, "S"
        dessiner_texte(image, titre, r.centerx, r.y + 78, 2, GRIS, lueur=False)
        y = r.y + 120
        for m in modificateurs:
            dessiner_texte(image, m[1], r.centerx, y, 3, config.BLANC)
            dessiner_texte(image, m[2], r.centerx, y + 28, 2, GRIS, lueur=False)
            y += 70
        flamme(image, (r.centerx - 40, r.y + 270), teinte, 4, f"{serie} {unite}")
        record = d.record_du_jour(self.app, jour, code)
        joue = jour in d.defis_joues(self.app, "jour" if code == "defi" else "semaine")
        dessiner_texte(image, f"TON RECORD  {record}" if record else "PAS ENCORE JOUE", r.centerx,
                       r.y + 320, 2, config.AMBRE if record else config.BLANC, lueur=False)
        if not joue and math.sin(self.temps * 5) > -0.2:
            dessiner_texte(image, "A JOUER !", r.centerx, r.y + 350, 3, config.ROSE)
        self._bouton(image, r, "JOUER", couleur)
