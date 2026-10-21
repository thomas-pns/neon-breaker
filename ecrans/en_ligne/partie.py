# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Partie en ligne côté joueur. Le serveur fait tourner la partie ; cet
    écran :
      - crée localement le même mode (pour réutiliser tout l'affichage) ;
      - recopie chaque instantané reçu et rejoue les effets spéciaux ;
      - pilote la raquette du joueur EN LOCAL (aucun délai ressenti) et
        envoie sa position et ses actions au serveur 60 fois par seconde ;
      - prolonge les mouvements entre deux instantanés (fluidité) ;
      - gère la coupure (reconnexion automatique pendant 30 s) et la pause
        quand l'autre joueur est déconnecté.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import pygame

from moteur import config
from moteur.effets import GestionnaireEffets
from moteur.police_pixel import dessiner_texte
from reseau.instantane import appliquer, prolonger, en_tuples, rejouer_effets, compenser_latence
from ecrans.base import voile
from ecrans.fin import EcranFin
from ecrans.hud import panneau
from ecrans.en_ligne.salons import EcranTempsReel
from ecrans.en_ligne.commun import GRIS

ACTIONS = ("action", "pouvoir1", "pouvoir2", "pouvoir3", "changer", "activer", "overdrive")


def creer_mode_client(code, app, effets, niveau):
    """But : le mode affiché localement (jamais simulé côté client)."""
    from jeu.modes.campagne import ModeCoop
    from jeu.modes.duel import ModeDuel
    from jeu.modes.course import ModeCourse
    if code == "coop":
        mode = ModeCoop(app, effets, niveau)
    elif code == "duel":
        mode = ModeDuel(app, effets)
    else:
        mode = ModeCourse(app, effets)
    mode.en_ligne = True
    return mode


class EcranPartieEnLigne(EcranTempsReel):
    """
    Attributs : numero (int : 1 ou 2), mode (ModeDeJeu miroir), effets,
    recu (bool : premier instantané arrivé), pause (dict ou None),
    actions (set : à envoyer), coupure (float ou None : début de la coupure).
    """

    def __init__(self, app, debut):
        super().__init__(app)
        self.numero = debut["numero"]
        self.code = debut["mode"]
        self.effets = GestionnaireEffets()
        self.effets.qualite = app.reglages["particules"]
        self.mode = creer_mode_client(self.code, app, self.effets, debut.get("niveau", 0))
        skins = debut.get("skins") or []
        for i, (joueur, pseudo) in enumerate(zip(self.mode.joueurs, debut["joueurs"])):
            joueur.nom = pseudo
            joueur.appliquer_skin(skins[i] if i < len(skins) else "neon", garder_bord=True)
        self.effets.particules.vider()
        self.effets.textes.vider()
        self.recu = False
        self.pause = None
        self.actions = set()
        self.coupure = None
        self.menu_quitter = False

    def joueur_local(self):
        return self.mode.joueurs[self.numero - 1]

    # --- Messages du serveur -------------------------------------------------------

    def sur_etat(self, message):
        appliquer(self.mode, message, self.app, self.numero)
        compenser_latence(self.mode, min(0.15, self.temps_reel.ping / 2000))
        rejouer_effets(message.get("fx", []), self.app, self.effets)
        self.recu = True
        self.pause = message.get("pause")
        # Un niveau Coop atteint en ligne se débloque aussi pour le joueur.
        if self.code == "coop" and getattr(self.mode, "indice", 0) > self.app.niveau_debloque("coop"):
            self.mode.debloquer(self.mode.indice)

    def sur_debut(self, message):
        """Retour après une coupure : la partie continue."""
        self.coupure = None

    def sur_fin(self, message):
        gains = message.get("gains")
        if gains:
            ancien = self.app.en_ligne.niveau
            self.app.en_ligne.memoriser({"xp": gains.get("xp", self.app.en_ligne.xp),
                                         "niveau": gains.get("niveau", ancien)})
            self.app.en_ligne.annoncer_gains(gains)
            if self.app.en_ligne.niveau > ancien:
                self.app.notifier(f"NIVEAU {self.app.en_ligne.niveau} !", "AMBRE")
        self.app.remplacer(EcranFinEnLigne(self.app, message["resultat"], gains))

    # --- Boucle -------------------------------------------------------------------------

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        self.traiter_reseau()
        if self.app.ecran_actif() is not self:
            return
        entrees = self.app.entrees
        self.effets.mettre_a_jour(dt)
        self._surveiller_connexion()
        if pygame.KSCAN_ESCAPE in entrees.appuis:
            self.menu_quitter = not self.menu_quitter
        if self.menu_quitter:
            if pygame.KSCAN_RETURN in entrees.appuis or ("menu", "valider") in entrees.forcees:
                self.temps_reel.envoyer({"t": "abandon"})
                from ecrans.en_ligne.salons import EcranSalons
                self.app.remplacer(EcranSalons(self.app))
            return
        if self.recu:
            self._piloter(dt)
        prolonger(self.mode, dt)
        self._recaler_balles_collees()

    def _surveiller_connexion(self):
        """Coupure : on retente toutes les 2 s, et on abandonne après 35 s."""
        if self.temps_reel.etat == "ouvert":
            self.coupure = None
            return
        if self.coupure is None:
            self.coupure = self.temps
        elif self.temps - self.coupure > 35:
            from ecrans.en_ligne.salons import EcranSalons
            self.app.notifier("CONNEXION PERDUE", "ROUGE")
            self.app.remplacer(EcranSalons(self.app))
        elif int((self.temps - self.coupure) * 10) % 20 == 0:
            self.temps_reel = self.app.en_ligne.ouvrir_temps_reel()

    def _piloter(self, dt):
        """Raquette locale (prédite) + envoi des commandes au serveur."""
        entrees = self.app.entrees
        joueur = self.joueur_local()
        raquette = joueur.raquette
        if raquette is None:
            return
        direction = entrees.direction("solo")
        if joueur.actif("inversion"):
            direction = -direction
        terrain = joueur.terrain
        if entrees.souris_bougee and terrain is not None and \
                terrain.rect.inflate(300, 0).collidepoint(entrees.souris):
            x = entrees.souris[0]
            if joueur.actif("inversion"):
                x = 2 * terrain.rect.centerx - x
            raquette.viser_souris(x)
        raquette.mettre_a_jour(dt, direction)
        self._ecarter_des_autres(raquette)
        for action in ACTIONS:
            if entrees.vient_d_appuyer(action, "solo"):
                self.actions.add(action)
        if entrees.vient_d_appuyer("valider"):
            self.actions.add("valider")
        if 1 in entrees.clics:
            self.actions.add("action")
        if 3 in entrees.clics:
            self.actions.add("overdrive")
        self.temps_reel.envoyer({"t": "cmd", "x": round(raquette.x, 1), "vx": round(raquette.vx),
                                 "a": sorted(self.actions), "p": round(self.temps_reel.ping)})
        self.actions.clear()

    def _ecarter_des_autres(self, raquette):
        """Coop : ma raquette ne traverse pas celle de mon coéquipier."""
        terrain = raquette.joueur.terrain if raquette.joueur else None
        if terrain is None:
            return
        for autre in terrain.raquettes:
            if autre is raquette or autre.sens != raquette.sens:
                continue
            contact = (raquette.largeur + autre.largeur) / 2 + 4
            ecart = contact - abs(raquette.x - autre.x)
            if ecart > 0:
                raquette.x += ecart if raquette.x >= autre.x else -ecart
                raquette.vx = 0.0
                raquette.contraindre()
                if abs(raquette.x - autre.x) < contact - 1:
                    # Coincée contre un mur : on passe de l'autre côté.
                    cote = -1 if raquette.x > autre.x else 1
                    raquette.x = autre.x + cote * contact
                    raquette.contraindre()

    def _recaler_balles_collees(self):
        """Une balle posée sur MA raquette suit ma raquette locale."""
        for terrain in self.mode.terrains:
            for balle in terrain.balles:
                if not balle.collee or not terrain.raquettes:
                    continue
                raquette = min(terrain.raquettes, key=lambda r: abs(r.face_y() - balle.y))
                if raquette.joueur is not None and raquette.joueur.numero == self.numero:
                    decalage = getattr(balle, "x_serveur", balle.x) - getattr(raquette, "x_serveur", raquette.x)
                    balle.x = raquette.x + decalage

    # --- Dessin -------------------------------------------------------------------------

    def musique(self):
        return self.mode.musique()

    def tremblement(self):
        return self.effets.decalage_tremblement()

    def dessiner(self, image):
        self.app.fond.dessiner(image)
        if not self.recu:
            dessiner_texte(image, "SYNCHRONISATION...", config.LARGEUR / 2, config.HAUTEUR / 2,
                           4, config.CYAN)
            return
        self.mode.dessiner(image)
        self.effets.dessiner(image)
        self.mode.dessiner_overlay(image)
        self.mode.dessiner_message(image)
        self.effets.dessiner_flash(image)
        ping = self.temps_reel.ping
        dessiner_texte(image, f"PING {ping:.0f} MS", config.LARGEUR - 14, config.HAUTEUR - 12, 2,
                       config.VERT if ping < 80 else config.AMBRE, ancrage="droite", lueur=False,
                       ombre=False)
        if self.pause:
            pseudo, reste = next(iter(self.pause.items()))
            self._bandeau(image, f"EN ATTENTE DE {pseudo.upper()}", f"RETOUR POSSIBLE : {max(0, reste):.0f} S")
        elif self.coupure is not None:
            self._bandeau(image, "CONNEXION PERDUE", "RECONNEXION EN COURS...")
        if self.menu_quitter:
            self._bandeau(image, "QUITTER LA PARTIE ?", "ENTREE : OUI    ECHAP : NON")

    def _bandeau(self, image, titre, sous_titre):
        voile(image, 120)
        cadre = pygame.Rect(0, 0, 640, 150)
        cadre.center = (config.LARGEUR / 2, config.HAUTEUR / 2)
        panneau(image, cadre, config.ROSE)
        dessiner_texte(image, titre, cadre.centerx, cadre.y + 50, 4, config.ROSE)
        dessiner_texte(image, sous_titre, cadre.centerx, cadre.y + 105, 2, GRIS, lueur=False)


class EcranFinEnLigne(EcranFin):
    """Fin d'une partie en ligne : résultat, XP gagnée, retour aux parties."""

    def __init__(self, app, resultat, gains):
        resultat = {**resultat, "lignes": [tuple(l) for l in resultat.get("lignes", [])]}
        if "couleur" in resultat:
            resultat["couleur"] = en_tuples(resultat["couleur"])
        resultat.setdefault("score", 0)
        resultat.setdefault("victoire", False)
        super().__init__(app, resultat, fabrique=None)
        self.gains = gains or {}
        self.menu.options = [("RETOUR AUX PARTIES", self._parties),
                             ("MENU EN LIGNE", self._hub)]

    def _parties(self):
        from ecrans.en_ligne.salons import EcranSalons
        self.app.remplacer(EcranSalons(self.app))

    def _hub(self):
        from ecrans.en_ligne.hub import EcranHub
        self.app.remplacer(EcranHub(self.app))

    def a_un_top(self):
        return True

    def _dessiner_top(self, image, cadre):
        panneau(image, cadre, config.CYAN)
        dessiner_texte(image, "RECOMPENSES", cadre.centerx, cadre.y + 30, 3, config.CYAN)
        if not self.gains:
            dessiner_texte(image, "PARTIE NON COMPTEE", cadre.centerx, cadre.centery, 2, GRIS,
                           lueur=False)
            return
        dessiner_texte(image, f"+{self.gains.get('xp_gagnee', 0)} XP", cadre.centerx,
                       cadre.y + 90, 5, config.AMBRE)
        dessiner_texte(image, f"NIVEAU {self.gains.get('niveau', 1)}", cadre.centerx,
                       cadre.y + 140, 3, config.BLANC)
        succes = self.gains.get("nouveaux_succes", [])
        if succes:
            dessiner_texte(image, "SUCCES DEBLOQUES", cadre.centerx, cadre.y + 190, 2,
                           config.OR, lueur=False)
        for i, entree in enumerate(succes[:5]):
            dessiner_texte(image, entree["nom"], cadre.centerx, cadre.y + 222 + i * 26, 2,
                           config.BLANC, lueur=False)
