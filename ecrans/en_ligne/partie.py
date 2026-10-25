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
        self.classee = bool(debut.get("classee"))
        self.effets = GestionnaireEffets()
        self.effets.qualite = app.reglages["particules"]
        self.mode = creer_mode_client(self.code, app, self.effets, debut.get("niveau", 0))
        # Duel : le joueur 2 (raquette du haut) voit le terrain retourné, donc lui en bas.
        self.vue_retournee = self.code == "duel" and self.numero == 2
        self.mode.vue_retournee = self.vue_retournee
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
        self.sons_a_ignorer = []         # instants des rebonds joués ici (sons du serveur en double)
        self.diagnostic = {"intervalles": [], "lissages": 0, "sauts": 0, "trous": 0, "coupures": 0}

    def joueur_local(self):
        return self.mode.joueurs[self.numero - 1]

    # --- Messages du serveur -------------------------------------------------------

    def sur_etat(self, message):
        self._mesurer_arrivee()
        proteges = self._balles_protegees()
        affichees = {balle.nid: (balle.x, balle.y, balle.vx, balle.vy)
                     for terrain in self.mode.terrains for balle in terrain.balles
                     if getattr(balle, "nid", None) is not None and not balle.collee}
        appliquer(self.mode, message, self.app, self.numero)
        compenser_latence(self.mode, min(0.15, self.temps_reel.ping / 2000))
        self._restaurer_balles(proteges)
        self._lisser_balles(affichees, proteges)
        rejouer_effets(self._filtrer_sons(message.get("fx", [])), self.app, self.effets)
        self.recu = True
        self.pause = message.get("pause")
        # Un niveau Coop atteint en ligne se débloque aussi pour le joueur.
        if self.code == "coop" and getattr(self.mode, "indice", 0) > self.app.niveau_debloque("coop"):
            self.mode.debloquer(self.mode.indice)

    def sur_debut(self, message):
        """Retour après une coupure : la partie continue."""
        self.coupure = None

    def sur_fin(self, message):
        resultat = message.get("resultat") or {}
        if resultat.get("titre") == "PARTIE INTERROMPUE" or "ABANDONNE" in str(resultat.get("titre")):
            from reseau.client import journaliser
            journaliser(f"fin de partie {self.code} : {resultat.get('titre')} {resultat.get('lignes')} "
                        f"(ping {self.temps_reel.ping:.0f} ms, coupures {self.diagnostic.get('coupures', 0)})")
        gains = message.get("gains")
        if gains:
            ancien = self.app.en_ligne.niveau
            self.app.en_ligne.memoriser({"xp": gains.get("xp", self.app.en_ligne.xp),
                                         "niveau": gains.get("niveau", ancien)})
            self.app.en_ligne.annoncer_gains(gains)
            if self.app.en_ligne.niveau > ancien:
                self.app.notifier(f"RANG {self.app.en_ligne.niveau} !", "AMBRE")
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
                from reseau.client import journaliser
                journaliser(f"abandon volontaire ({self.code})")
                self.temps_reel.envoyer({"t": "abandon"})
                from ecrans.en_ligne.salons import EcranSalons
                self.app.remplacer(EcranSalons(self.app))
            return
        if self.recu:
            self._piloter(dt)
        prolonger(self.mode, dt)
        self._recaler_balles_collees()
        if self.recu:
            self._rebonds_locaux()

    def _surveiller_connexion(self):
        """Coupure : on retente toutes les 2 s, et on abandonne après 35 s."""
        if self.temps_reel.etat == "ouvert":
            self.coupure = None
            return
        if self.coupure is None:
            self.coupure = self.temps
            self.diagnostic["coupures"] = self.diagnostic.get("coupures", 0) + 1
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
        # « rc » : ce jeu annonce lui-même les rebonds sur sa raquette (voir _rebonds_locaux).
        self.temps_reel.envoyer({"t": "cmd", "x": round(raquette.x, 1), "vx": round(raquette.vx),
                                 "a": sorted(self.actions), "p": round(self.temps_reel.ping),
                                 "rc": 1})
        self.actions.clear()

    # --- Rebonds décidés par ce PC --------------------------------------------------------

    def _delai_protection(self):
        """But : durée pendant laquelle un rebond local prime sur le serveur (s)."""
        return max(0.5, 2 * self.temps_reel.ping / 1000 + 0.25)

    def _rebonds_locaux(self):
        """
        But : la balle touche MA raquette sur mon écran : elle rebondit tout de suite
        (même calcul que le jeu solo) et le serveur est prévenu. Il s'aligne s'il juge
        le rebond plausible. Plus de rebond en retard ni de balle qui traverse.
        """
        from jeu.terrain import rebond_raquette
        joueur = self.joueur_local()
        raquette, terrain = joueur.raquette, joueur.terrain
        if raquette is None or terrain is None:
            for t in self.mode.terrains:
                for balle in t.balles:
                    balle.y_prec = balle.y
            return
        sens = raquette.sens
        for t in self.mode.terrains:
            for balle in t.balles:
                precedente = getattr(balle, "y_prec", balle.y)
                balle.y_prec = balle.y
                if t is not terrain or balle.collee or balle.vy * sens >= 0:
                    continue
                if raquette.etourdie > 0 or raquette.gelee > 0:
                    continue
                face, r = raquette.face_y(), balle.rayon
                dos = face - sens * raquette.hauteur       # arrière de la raquette
                # Contact (comme dans le jeu solo) : la balle touche la raquette sans
                # être passée derrière ; ou, après un saut dû au réseau, son centre
                # vient de franchir la face entre deux images.
                if sens < 0:
                    contact = balle.y + r >= face and balle.y <= dos
                    franchie = precedente <= face and balle.y > dos
                else:
                    contact = balle.y - r <= face and balle.y >= dos
                    franchie = precedente >= face and balle.y < dos
                if not (contact or franchie) or abs(balle.x - raquette.x) > raquette.largeur / 2 + r:
                    continue
                balle.y = face + sens * (r + 0.5)
                rebond_raquette(balle, raquette.obtenir_boite(), sens=sens)
                if joueur.aimant_prises > 0:
                    balle.collee = True              # le serveur confirmera le collage
                balle.y_prec = balle.y
                balle.rebond_local = self.temps
                raquette.frappee()
                self.app.audio.jouer("raquette")
                self.sons_a_ignorer.append(self.temps)
                self.temps_reel.envoyer({
                    "t": "rebond", "n": getattr(balle, "nid", -1), "x": round(balle.x, 1),
                    "y": round(balle.y, 1), "vx": round(balle.vx, 1), "vy": round(balle.vy, 1),
                    "rx": round(raquette.x, 1), "p": round(self.temps_reel.ping)})

    def _balles_protegees(self):
        """But : balles qui viennent de rebondir ici : leur état local, par identifiant."""
        limite = self.temps - self._delai_protection()
        return {balle.nid: (balle.x, balle.y, balle.vx, balle.vy, balle.collee)
                for terrain in self.mode.terrains for balle in terrain.balles
                if getattr(balle, "rebond_local", -1e9) > limite and getattr(balle, "nid", None)}

    def _restaurer_balles(self, proteges):
        """
        But : tant que le serveur n'a pas encore traité mon rebond (sa balle arrive
        toujours sur ma raquette), garder la balle de mon écran au lieu de la faire sauter.
        """
        if not proteges:
            return
        sens = self.joueur_local().raquette.sens if self.joueur_local().raquette else -1
        for terrain in self.mode.terrains:
            for balle in terrain.balles:
                local = proteges.get(getattr(balle, "nid", None))
                if local is None:
                    continue
                if balle.vy * sens < 0 and not balle.collee:
                    balle.x, balle.y, balle.vx, balle.vy, balle.collee = local
                else:
                    balle.rebond_local = -1e9        # le serveur a suivi : il reprend la main
                balle.y_prec = balle.y

    def _lisser_balles(self, affichees, proteges):
        """
        But : petit écart entre la balle affichée et la nouvelle position du serveur :
        au lieu de la téléporter, on garde l'affichage et on rattrape l'écart en
        douceur sur quelques images (voir prolonger). Un vrai changement de direction
        (rebond sur une brique, un mur...) est appliqué tout de suite.
        """
        for terrain in self.mode.terrains:
            for balle in terrain.balles:
                ancien = affichees.get(getattr(balle, "nid", None))
                if ancien is None or balle.collee or balle.nid in proteges:
                    continue
                x, y, vx, vy = ancien
                ecart = ((x - balle.x) ** 2 + (y - balle.y) ** 2) ** 0.5
                meme_direction = vx * balle.vx + vy * balle.vy > 0
                if meme_direction and 1.0 < ecart < 90:
                    balle.correction = (x - balle.x, y - balle.y)
                    balle.x, balle.y = x, y
                    self.diagnostic["lissages"] += 1
                elif ecart >= 90:
                    self.diagnostic["sauts"] += 1

    def _mesurer_arrivee(self):
        """But : régularité des instantanés reçus (diagnostic F3)."""
        import time
        maintenant = time.monotonic()
        precedent = self.diagnostic.get("derniere")
        if precedent is not None:
            intervalles = self.diagnostic["intervalles"]
            intervalles.append(maintenant - precedent)
            del intervalles[:-120]
            if maintenant - precedent > 0.4:              # trou réseau : noté pour comprendre
                self.diagnostic["trous"] = self.diagnostic.get("trous", 0) + 1
                if self.diagnostic["trous"] <= 30:
                    from reseau.client import journaliser
                    journaliser(f"trou de {(maintenant - precedent) * 1000:.0f} ms sans etat "
                                f"(ping {self.temps_reel.ping:.0f} ms)")
        self.diagnostic["derniere"] = maintenant

    def _dessiner_diagnostic(self, image):
        """But : touche F3 : ping, cadence et régularité du réseau, corrections."""
        intervalles = self.diagnostic["intervalles"]
        if intervalles:
            moyenne = sum(intervalles) / len(intervalles)
            gigue = (sum((i - moyenne) ** 2 for i in intervalles) / len(intervalles)) ** 0.5
            cadence = 1 / moyenne if moyenne else 0
        else:
            moyenne = gigue = cadence = 0
        lignes = [f"PING {self.temps_reel.ping:.0f} MS",
                  f"ETATS {cadence:.0f} / S",
                  f"GIGUE {gigue * 1000:.0f} MS",
                  f"MAX {max(intervalles, default=0) * 1000:.0f} MS",
                  f"LISSAGES {self.diagnostic['lissages']}",
                  f"SAUTS {self.diagnostic['sauts']}",
                  f"TROUS {self.diagnostic.get('trous', 0)}",
                  f"COUPURES {self.diagnostic.get('coupures', 0)}"]
        cadre = pygame.Rect(config.LARGEUR - 230, 60, 214, 30 + 24 * len(lignes))
        pygame.draw.rect(image, (10, 0, 24), cadre, border_radius=8)
        pygame.draw.rect(image, config.CYAN, cadre, 1, border_radius=8)
        for i, ligne in enumerate(lignes):
            dessiner_texte(image, ligne, cadre.x + 14, cadre.y + 22 + i * 24, 2, config.BLANC,
                           ancrage="gauche", lueur=False, ombre=False)

    def _filtrer_sons(self, effets):
        """But : ne pas rejouer le son d'un rebond déjà joué sur ce PC."""
        self.sons_a_ignorer = [t for t in self.sons_a_ignorer if self.temps - t < 1.0]
        if not self.sons_a_ignorer:
            return effets
        resultat = []
        for effet in effets:
            if effet[0] == "son" and effet[1] and effet[1][0] == "raquette" and self.sons_a_ignorer:
                self.sons_a_ignorer.pop(0)
                continue
            resultat.append(effet)
        return resultat

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
        """
        Une balle posée sur MA raquette suit ma raquette locale. On se fie au
        propriétaire de la balle (et non à la raquette la plus proche : en Coop, les
        deux raquettes sont à la même hauteur).
        """
        raquette = self.joueur_local().raquette
        if raquette is None:
            return
        for terrain in self.mode.terrains:
            for balle in terrain.balles:
                if not balle.collee or balle.proprietaire is not self.joueur_local():
                    continue
                decalage = getattr(balle, "x_serveur", balle.x) - getattr(raquette, "x_serveur", raquette.x)
                balle.x = raquette.x + max(-raquette.largeur / 2, min(raquette.largeur / 2, decalage))

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
        if self.vue_retournee:
            self._dessiner_retourne(image)
        else:
            self.mode.dessiner(image)
            self.effets.dessiner(image)
        self.mode.dessiner_overlay(image)
        self.mode.dessiner_message(image)
        self.effets.dessiner_flash(image)
        ping = self.temps_reel.ping
        if self.app.debug:
            self._dessiner_diagnostic(image)
        couleur_ping = config.VERT if ping < 80 else config.AMBRE if ping < 150 else config.ROUGE
        dessiner_texte(image, f"PING {ping:.0f} MS", config.LARGEUR - 14, config.HAUTEUR - 12, 2,
                       couleur_ping, ancrage="droite", lueur=False, ombre=False)
        if self.pause:
            pseudo, reste = next(iter(self.pause.items()))
            self._bandeau(image, f"EN ATTENTE DE {pseudo.upper()}", f"RETOUR POSSIBLE : {max(0, reste):.0f} S")
        elif self.coupure is not None:
            self._bandeau(image, "CONNEXION PERDUE", "RECONNEXION EN COURS...")
        if self.menu_quitter:
            if self.classee:
                self._bandeau(image, "ABANDONNER ? = DEFAITE CLASSEE", "ENTREE : OUI    ECHAP : NON")
            else:
                self._bandeau(image, "QUITTER LA PARTIE ?", "ENTREE : OUI    ECHAP : NON")

    def _dessiner_retourne(self, image):
        """
        But : vue du joueur 2 en Duel : le terrain est dessiné puis retourné de haut en
        bas, pour que sa raquette soit en bas. Le fond est retourné avant puis remis à
        l'endroit par le second retournement ; capsules (icônes) et textes flottants
        sont dessinés ensuite, à leur place miroir mais à l'endroit, puis le HUD.
        """
        from structures.liste import Liste
        terrain = self.mode.terrains[0]
        zone = terrain.rect.inflate(48, 48).clip(image.get_rect())
        miroir = terrain.rect.top + terrain.rect.bottom
        self._retourner(image, zone)
        capsules, terrain.capsules = terrain.capsules, Liste()
        try:
            terrain.dessiner(image)
            self.mode.dessiner_mediane(image)
            self.effets.dessiner(image, textes=False)
        finally:
            terrain.capsules = capsules
        self._retourner(image, zone)
        for capsule in capsules:
            y = capsule.y
            capsule.y = miroir - y
            capsule.dessiner(image)
            capsule.y = y
        self.effets.dessiner_textes(image, miroir_y=miroir)
        self.mode.dessiner_hud(image)

    @staticmethod
    def _retourner(image, zone):
        """But : retourner verticalement une zone de l'image, sur place."""
        morceau = pygame.transform.flip(image.subsurface(zone).copy(), False, True)
        image.blit(morceau, zone.topleft)

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
        y = cadre.y + 80
        if "xp_gagnee" in self.gains:
            dessiner_texte(image, f"+{self.gains.get('xp_gagnee', 0)} XP", cadre.centerx, y, 4,
                           config.AMBRE)
            from moteur.bannieres import dessiner_piece
            zone = dessiner_texte(image, f"+{self.gains.get('neons_gagnes', 0)}", cadre.centerx + 16,
                                  y + 44, 4, config.CYAN)
            dessiner_piece(image, (zone.x - 22, zone.centery), 12, self.temps)
            dessiner_texte(image, f"RANG {self.gains.get('niveau', 1)}", cadre.centerx, y + 82, 2,
                           config.BLANC, lueur=False)
            y += 116
        if self.gains.get("classee"):
            from reseau.classee import division
            delta = self.gains.get("elo_delta", 0)
            nom, couleur, _, _ = division(self.gains.get("elo", 1000))
            dessiner_texte(image, f"{'+' if delta >= 0 else ''}{delta} COTE", cadre.centerx, y, 3,
                           config.VERT if delta >= 0 else config.ROUGE)
            dessiner_texte(image, f"{nom}  {self.gains.get('elo', 1000)}", cadre.centerx, y + 32, 2,
                           couleur, lueur=False)
            y += 64
        succes = self.gains.get("nouveaux_succes", [])
        if succes:
            dessiner_texte(image, "SUCCES DEBLOQUES", cadre.centerx, y, 2, config.OR, lueur=False)
        for i, entree in enumerate(succes[:4]):
            dessiner_texte(image, entree["nom"], cadre.centerx, y + 28 + i * 26, 2,
                           config.BLANC, lueur=False)
