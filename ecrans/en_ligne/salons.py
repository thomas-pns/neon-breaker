# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Parties en ligne : liste des parties ouvertes (4 au maximum), création
    d'une partie (Coop avec choix du niveau, Duel, Course), puis salon
    d'attente (deux places, « prêt », lancement par l'hôte).

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import math

import pygame

from moteur import config
from moteur.police_pixel import dessiner_texte
from moteur.rendu import halo_rect, attenuer
from ecrans.hud import panneau
from ecrans.en_ligne.commun import EcranEnLigneBase, couleur_profil, NOMS_MODES, GRIS

MODES = ["coop", "duel", "course"]
COULEURS_MODES = {"coop": config.VERT, "duel": config.VIOLET, "course": config.AMBRE}


class EcranTempsReel(EcranEnLigneBase):
    """Écran qui écoute la connexion WebSocket et répartit les messages."""

    def __init__(self, app):
        super().__init__(app)
        self.temps_reel = app.en_ligne.ouvrir_temps_reel()
        self.erreur = ""
        self.etat_precedent = None

    def traiter_reseau(self):
        """But : réagir aux messages reçus (méthodes sur_<type>)."""
        etat = self.temps_reel.etat
        if etat == "ouvert" and self.etat_precedent != "ouvert":
            self.sur_connexion()
        self.etat_precedent = etat
        for message in self.temps_reel.messages():
            methode = getattr(self, "sur_" + str(message.get("t")), None)
            if methode is not None:
                methode(message)

    def sur_connexion(self):
        """Crochet : la connexion vient de s'ouvrir."""

    def sur_erreur(self, message):
        self.erreur = message.get("msg", "ERREUR")
        self.app.audio.jouer("metal")
        if message.get("fatal"):
            self.temps_reel.fermer()

    def sur_debut(self, message):
        from ecrans.en_ligne.partie import EcranPartieEnLigne
        self.app.remplacer(EcranPartieEnLigne(self.app, message), transition=True)

    def retour_hub(self):
        from ecrans.en_ligne.hub import EcranHub
        self.app.remplacer(EcranHub(self.app))

    def dessiner_etat_connexion(self, image, y):
        etat = self.temps_reel.etat
        if etat == "connexion":
            texte, couleur = "CONNEXION AU SERVEUR...", config.CYAN
        elif etat == "erreur":
            texte, couleur = "SERVEUR INJOIGNABLE  -  ENTREE : REESSAYER", config.ROUGE
        elif self.erreur:
            texte, couleur = self.erreur, config.ROUGE
        else:
            return
        dessiner_texte(image, texte, config.LARGEUR / 2, y, 2, couleur, lueur=False)


class EcranSalons(EcranTempsReel):
    """
    Liste des parties. Attributs : salons (list de dict), en_ligne (list),
    indice (int : ligne choisie), mode_creation (int), niveau (int).
    """

    titre = "PARTIES EN LIGNE"

    def __init__(self, app):
        super().__init__(app)
        self.salons = []
        self.joueurs_en_ligne = []
        self.maximum = 4
        self.indice = 0
        self.mode_creation = 0
        self.niveau = self.niveau_max()
        self.zones = []

    def niveau_max(self):
        """But : dernier niveau Coop proposable (atteint en Campagne ou en Coop)."""
        return min(11, max(self.app.niveau_debloque("campagne"), self.app.niveau_debloque("coop")))

    def sur_connexion(self):
        self.temps_reel.envoyer({"t": "lister"})

    def sur_salons(self, message):
        self.salons = [s for s in message["liste"]]
        self.joueurs_en_ligne = message.get("en_ligne", [])
        self.maximum = message.get("max", 4)
        self.indice = min(self.indice, self.nb_lignes() - 1)

    def sur_salon(self, message):
        self.app.remplacer(EcranSalon(self.app, message), transition=False)

    def nb_lignes(self):
        return len(self.salons) + (2 if MODES[self.mode_creation] == "coop" else 1)

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        self.traiter_reseau()
        entrees = self.app.entrees
        if pygame.KSCAN_ESCAPE in entrees.appuis:
            self.retour_hub()
            return
        if self.temps_reel.etat in ("erreur", "ferme"):
            if entrees.vient_d_appuyer("valider"):
                self.erreur = ""
                self.temps_reel = self.app.en_ligne.ouvrir_temps_reel()
            return
        ancien = self.indice
        if entrees.vient_d_appuyer("haut"):
            self.indice = (self.indice - 1) % self.nb_lignes()
        if entrees.vient_d_appuyer("bas"):
            self.indice = (self.indice + 1) % self.nb_lignes()
        if entrees.souris_bougee:
            for i, zone in enumerate(self.zones):
                if zone.collidepoint(entrees.souris):
                    self.indice = i
        if self.indice != ancien:
            self.app.audio.jouer("menu_nav")
        ligne_creation = len(self.salons)
        sens = int(entrees.vient_d_appuyer("droite")) - int(entrees.vient_d_appuyer("gauche"))
        if sens and self.indice == ligne_creation:
            self.mode_creation = (self.mode_creation + sens) % len(MODES)
            self.app.audio.jouer("menu_nav")
        elif sens and self.indice == ligne_creation + 1:
            self.niveau = (self.niveau + sens) % (self.niveau_max() + 1)
            self.app.audio.jouer("menu_nav")
        clic = 1 in entrees.clics and any(z.collidepoint(entrees.souris) for z in self.zones)
        if entrees.vient_d_appuyer("valider") or clic:
            self.erreur = ""
            if self.indice < len(self.salons):
                self.temps_reel.envoyer({"t": "rejoindre", "id": self.salons[self.indice]["id"]})
            else:
                self.temps_reel.envoyer({"t": "creer", "mode": MODES[self.mode_creation],
                                         "niveau": self.niveau})
            self.app.audio.jouer("menu_ok")

    def dessiner(self, image):
        self.dessiner_fond(image)
        self.zones = []
        liste = pygame.Rect(60, 100, 820, 520)
        panneau(image, liste, config.CYAN)
        dessiner_texte(image, f"PARTIES OUVERTES  {len(self.salons)} / {self.maximum}",
                       liste.x + 24, liste.y + 26, 2, GRIS, ancrage="gauche", lueur=False)
        y = liste.y + 60
        if not self.salons and self.temps_reel.etat == "ouvert":
            dessiner_texte(image, "AUCUNE PARTIE : CREEZ-EN UNE !", liste.centerx, y + 60, 3,
                           (120, 90, 170), lueur=False)
        for i, salon in enumerate(self.salons):
            rect = pygame.Rect(liste.x + 20, y, liste.w - 40, 64)
            self._ligne_salon(image, rect, salon, i == self.indice)
            self.zones.append(rect)
            y += 74
        # Ligne « créer une partie ».
        y = max(y + 10, liste.bottom - 170)
        rect = pygame.Rect(liste.x + 20, y, liste.w - 40, 64)
        mode = MODES[self.mode_creation]
        choisi = self.indice == len(self.salons)
        self._cadre(image, rect, choisi, COULEURS_MODES[mode])
        dessiner_texte(image, "CREER :", rect.x + 24, rect.centery, 3, config.BLANC,
                       ancrage="gauche", lueur=False)
        dessiner_texte(image, f"< {NOMS_MODES[mode]} >", rect.x + 360, rect.centery, 4,
                       COULEURS_MODES[mode], lueur=choisi)
        self.zones.append(rect)
        if mode == "coop":
            rect = pygame.Rect(liste.x + 20, y + 74, liste.w - 40, 56)
            choisi = self.indice == len(self.salons) + 1
            self._cadre(image, rect, choisi, config.VERT)
            dessiner_texte(image, "NIVEAU DE DEPART", rect.x + 24, rect.centery, 2, GRIS,
                           ancrage="gauche", lueur=False)
            dessiner_texte(image, f"< {self.niveau + 1} >", rect.x + 360, rect.centery, 3,
                           config.VERT, lueur=choisi)
            if self.niveau_max() < 11:
                dessiner_texte(image, f"DEBLOQUES : 1 A {self.niveau_max() + 1}", rect.right - 24,
                               rect.centery, 2, GRIS, ancrage="droite", lueur=False)
            self.zones.append(rect)

        cote = pygame.Rect(910, 100, 310, 520)
        panneau(image, cote, config.ROSE)
        dessiner_texte(image, f"EN LIGNE ({len(self.joueurs_en_ligne)})", cote.centerx,
                       cote.y + 30, 2, config.ROSE, lueur=False)
        for k, pseudo in enumerate(self.joueurs_en_ligne[:14]):
            yy = cote.y + 70 + k * 30
            pygame.draw.circle(image, config.VERT, (cote.x + 30, yy), 5)
            dessiner_texte(image, pseudo.upper(), cote.x + 48, yy, 2, config.BLANC,
                           ancrage="gauche", lueur=False)
        self.dessiner_etat_connexion(image, 650)
        self.pied(image, "↑↓ : CHOISIR   ←→ : MODE   ENTREE : REJOINDRE / CREER"
                         "   ECHAP : RETOUR")

    def _cadre(self, image, rect, choisi, couleur):
        pygame.draw.rect(image, (16, 4, 36), rect, border_radius=8)
        if choisi:
            lueur = halo_rect(rect.w, rect.h, attenuer(couleur, 0.8), rayon=8)
            image.blit(lueur, (rect.x - 16, rect.y - 16), special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.rect(image, couleur if choisi else attenuer(couleur, 0.45), rect,
                         3 if choisi else 2, border_radius=8)

    def _ligne_salon(self, image, rect, salon, choisi):
        couleur = COULEURS_MODES.get(salon["mode"], config.CYAN)
        self._cadre(image, rect, choisi, couleur)
        titre = NOMS_MODES.get(salon["mode"], "?")
        if salon["mode"] == "coop":
            titre += f"  NIV {salon['niveau'] + 1}"
        dessiner_texte(image, titre, rect.x + 24, rect.centery, 3, couleur, ancrage="gauche",
                       lueur=False)
        dessiner_texte(image, " + ".join(p.upper() for p in salon["joueurs"]), rect.x + 330,
                       rect.centery, 2, config.BLANC, ancrage="gauche", lueur=False)
        complet = len(salon["joueurs"]) >= salon.get("places", 2)
        statut = "EN JEU" if salon["etat"] != "attente" else (
            "COMPLET" if complet else f"{len(salon['joueurs'])}/{salon.get('places', 2)}")
        dessiner_texte(image, statut, rect.right - 24, rect.centery, 2,
                       config.ROUGE if statut in ("EN JEU", "COMPLET") else config.VERT,
                       ancrage="droite", lueur=False)


class EcranSalon(EcranTempsReel):
    """Salon d'attente avant une partie en ligne."""

    titre = "SALON"

    def __init__(self, app, salon):
        super().__init__(app)
        self.salon = salon
        self.indice = 0
        self.zones = []

    def sur_salon(self, message):
        self.salon = message

    def suis_pret(self):
        return any(j["pseudo"] == self.app.en_ligne.pseudo and j["pret"]
                   for j in self.salon["joueurs"])

    def suis_hote(self):
        return self.salon.get("hote") == self.app.en_ligne.pseudo

    def options(self):
        options = [("PAS PRET" if self.suis_pret() else "PRET !", self._pret)]
        if self.suis_hote():
            options.append(("LANCER LA PARTIE", self._lancer))
        options.append(("QUITTER", self._quitter))
        return options

    def _pret(self):
        self.temps_reel.envoyer({"t": "pret", "v": not self.suis_pret()})

    def _lancer(self):
        self.temps_reel.envoyer({"t": "lancer"})

    def _quitter(self):
        self.temps_reel.envoyer({"t": "quitter"})
        self.app.remplacer(EcranSalons(self.app), transition=False)

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        self.traiter_reseau()
        entrees = self.app.entrees
        if pygame.KSCAN_ESCAPE in entrees.appuis:
            self._quitter()
            return
        options = self.options()
        self.indice = min(self.indice, len(options) - 1)
        ancien = self.indice
        if entrees.vient_d_appuyer("haut") or entrees.vient_d_appuyer("gauche"):
            self.indice = (self.indice - 1) % len(options)
        if entrees.vient_d_appuyer("bas") or entrees.vient_d_appuyer("droite"):
            self.indice = (self.indice + 1) % len(options)
        if entrees.souris_bougee:
            for i, zone in enumerate(self.zones):
                if zone.collidepoint(entrees.souris):
                    self.indice = i
        if self.indice != ancien:
            self.app.audio.jouer("menu_nav")
        clic = 1 in entrees.clics and any(z.collidepoint(entrees.souris) for z in self.zones)
        if entrees.vient_d_appuyer("valider") or clic:
            self.erreur = ""
            self.app.audio.jouer("menu_ok")
            options[self.indice][1]()

    def dessiner(self, image):
        mode = self.salon["mode"]
        titre = NOMS_MODES.get(mode, "?") + (f"  -  NIVEAU {self.salon['niveau'] + 1}"
                                             if mode == "coop" else "")
        self.dessiner_fond(image, titre)
        couleur_mode = COULEURS_MODES.get(mode, config.CYAN)
        for place in range(2):
            rect = pygame.Rect(0, 0, 440, 260)
            rect.center = (config.LARGEUR / 2 + (place * 2 - 1) * 250, 280)
            joueurs = self.salon["joueurs"]
            if place < len(joueurs):
                joueur = joueurs[place]
                couleur = couleur_profil(joueur["couleur"])
                panneau(image, rect, couleur)
                dessiner_texte(image, f"J{place + 1}" + ("  HOTE" if place == 0 else ""),
                               rect.centerx, rect.y + 30, 2, GRIS, lueur=False)
                dessiner_texte(image, joueur["pseudo"].upper(), rect.centerx, rect.y + 100, 5,
                               couleur)
                dessiner_texte(image, f"NIVEAU {joueur['niveau']}", rect.centerx, rect.y + 150,
                               2, config.AMBRE, lueur=False)
                pret = joueur["pret"]
                dessiner_texte(image, "PRET !" if pret else "PAS PRET", rect.centerx,
                               rect.bottom - 44, 4, config.VERT if pret else (120, 90, 170),
                               lueur=pret)
            else:
                panneau(image, rect, (90, 60, 120))
                points = "." * (1 + int(self.temps * 2) % 3)
                dessiner_texte(image, "EN ATTENTE" + points, rect.centerx, rect.centery, 3,
                               (120, 90, 170), lueur=False)
        self.zones = []
        for i, (libelle, _) in enumerate(self.options()):
            rect = pygame.Rect(0, 0, 300, 52)
            rect.center = (config.LARGEUR / 2, 470 + i * 62)
            choisi = i == self.indice
            pygame.draw.rect(image, couleur_mode if choisi else (16, 4, 36), rect, border_radius=8)
            pygame.draw.rect(image, couleur_mode, rect, 2, border_radius=8)
            dessiner_texte(image, libelle, rect.centerx, rect.centery, 3,
                           (20, 0, 30) if choisi else couleur_mode, lueur=False)
            self.zones.append(rect)
        if self.suis_hote() and len(self.salon["joueurs"]) < 2 and math.sin(self.temps * 3) > 0:
            dessiner_texte(image, "EN ATTENTE D'UN DEUXIEME JOUEUR", config.LARGEUR / 2, 425, 2,
                           GRIS, lueur=False)
        self.dessiner_etat_connexion(image, 660)
        self.pied(image, "EN JEU : ←→ / Q D / SOURIS  -  ESPACE LANCER  -  1 2 3 POUVOIRS"
                         "  -  MAJ OVERDRIVE")
