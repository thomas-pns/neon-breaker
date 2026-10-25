# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Écran qui fait tourner n'importe quel mode de jeu : boucle physique à
    pas fixe (120 Hz), effets spéciaux, pause, puis écran de fin (avec
    saisie du nom si le score entre dans le top 10). Successeur de
    partie.py de la version Tkinter.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Démo automatique sur l'écran titre (une IA joue).
"""

from moteur import config
from moteur.effets import GestionnaireEffets
from ecrans.base import EcranBase


class EcranPartie(EcranBase):
    """
    Attributs :
        fabrique (fonction(app, effets) -> ModeDeJeu) : pour (re)commencer.
        mode (ModeDeJeu), effets (GestionnaireEffets), accumulateur (float).
    """

    def __init__(self, app, fabrique):
        super().__init__(app)
        self.fabrique = fabrique
        self.effets = GestionnaireEffets()
        self.effets.qualite = app.reglages["particules"]
        self.mode = fabrique(app, self.effets)
        # Le joueur 1 (celui du compte) porte son skin ; le J2 local garde le style NEON.
        if self.mode.joueurs:
            self.mode.joueurs[0].appliquer_skin(app.en_ligne.skin_actif(),
                                                garder_bord=self.mode.deux_joueurs)
        self.accumulateur = 0.0
        self.fini = False

    def reprendre(self):
        """Au retour de pause, on ignore la touche qui a fermé le menu."""
        self.app.entrees.debut_image()

    def recommencer(self):
        """But : relancer le même mode depuis le début."""
        self.app.remplacer(EcranPartie(self.app, self.fabrique))

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        entrees = self.app.entrees
        mode = self.mode
        self.effets.mettre_a_jour(dt)
        if entrees.vient_d_appuyer("pause") and mode.etat in ("compte", "pret", "jeu"):
            from ecrans.pause import EcranPause
            self.app.audio.jouer("pause")
            self.app.empiler(EcranPause(self.app, self))
            return
        dt_jeu = dt * self.effets.facteur_temps()
        self.accumulateur += dt_jeu
        pas = 0
        while self.accumulateur >= config.PAS_PHYSIQUE and pas < config.PAS_MAX_PAR_IMAGE:
            mode.pas_physique(config.PAS_PHYSIQUE)
            self.accumulateur -= config.PAS_PHYSIQUE
            pas += 1
        if pas == config.PAS_MAX_PAR_IMAGE:
            self.accumulateur = 0.0           # le PC rame : on ne rattrape pas
        mode.mettre_a_jour(dt, dt_jeu)
        if mode.resultat is not None and not self.fini:
            self.fini = True
            self._aller_a_la_fin(mode.resultat)

    def _aller_a_la_fin(self, resultat):
        """Saisie du nom si le score entre dans le top 10, sinon écran de fin."""
        from ecrans.fin import EcranFin
        from ecrans.saisie import EcranSaisieNom
        app = self.app
        if self.mode.code in ("campagne", "arcade", "hardcore", "defi", "semaine") and resultat.get("rapports"):
            app.en_ligne.ajouter_rapports(resultat["rapports"])
        if self.mode.classement and app.entre_dans_classement(resultat["mode"], resultat["score"]):
            app.remplacer(EcranSaisieNom(app, resultat, self.fabrique))
        else:
            app.remplacer(EcranFin(app, resultat, self.fabrique))

    def musique(self):
        return self.mode.musique()

    def tremblement(self):
        return self.effets.decalage_tremblement()

    def dessiner(self, image):
        self.app.fond.dessiner(image)
        self.mode.dessiner(image)
        self.effets.dessiner(image)
        self.mode.dessiner_overlay(image)
        from ecrans.bulles import dessiner
        dessiner(self.mode, image)
        self.mode.dessiner_message(image)
        self.effets.dessiner_flash(image)
