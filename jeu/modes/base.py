# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Classe ModeDeJeu commune à tous les modes. Elle lit les commandes de
    chaque joueur (déplacement, lancement, pouvoirs, OVERDRIVE), fait
    avancer les terrains, défile leurs Files d'événements et y réagit
    (score, combos, effets spéciaux, sons, capsules). Chaque mode ne
    redéfinit que ses règles propres : vies, victoire, défaite, attaques.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Rejouer une partie (enregistrement des commandes).
"""

import math

from moteur import config
from jeu.capsule import CATALOGUE
from jeu.joueur import stats_serialisables
from jeu.pouvoirs import appliquer_capsule, activer_pouvoir, declencher_supernova


class ModeDeJeu:
    """
    Attributs :
        app (Application), effets (GestionnaireEffets).
        joueurs (list de Joueur), terrains (list de Terrain).
        etat (str) : "compte", "pret", "jeu", "victoire", "bilan", "manche",
                     "perdu", "fin".
        minuteur (float) : temps restant de l'état courant.
        resultat (dict ou None) : rempli quand la partie est finie.
        multiplicateur_score (int) : 2 en Hardcore.
        souris_active (bool) : la souris pilote le joueur 1 (solo).
        message (str), couleur_message, temps_message : bandeau central.
    """

    code = "mode"
    titre = "MODE"
    en_ligne = False              # True : copie affichée d'une partie du serveur
    deux_joueurs = False
    classement = True             # le score entre-t-il dans un top 10 ?

    def __init__(self, app, effets):
        self.app = app
        self.effets = effets
        self.joueurs = []
        self.terrains = []
        self.etat = "pret"
        self.minuteur = 0.0
        self.resultat = None
        self.multiplicateur_score = 1
        self.souris_active = False
        self.temps = 0.0
        self.message = ""
        self.couleur_message = config.BLANC
        self.temps_message = 0.0
        self.bulle = None

    # --- Outils -----------------------------------------------------------------

    def musique(self):
        """
        But : musique à jouer : (fond, dessus). Thème du monde ou du boss,
        et la musique OVERDRIVE par-dessus pendant une SUPERNOVA.
        """
        if any(getattr(terrain, "boss", None) for terrain in self.terrains):
            fond = "boss"
        else:
            fond = f"monde{getattr(self.app.fond, 'monde', 1)}"
        dessus = "overdrive" if any(j.supernova > 0 for j in self.joueurs) else None
        return fond, dessus

    def audio(self, nom, volume=1.0):
        """But : jouer un son (raccourci)."""
        self.app.audio.jouer(nom, volume)

    def annoncer(self, texte, couleur=config.BLANC, duree=1.6):
        """But : afficher un message au centre de l'écran."""
        self.message = texte
        self.couleur_message = couleur
        self.temps_message = duree

    def nom_joueur(self, joueur):
        """But : « J1 » en local, le pseudo (8 lettres max) en ligne."""
        return joueur.nom.upper()[:8] if self.en_ligne else f"J{joueur.numero}"

    def adversaire(self, joueur):
        """But : l'autre joueur (modes 2 joueurs), None en solo."""
        autres = [j for j in self.joueurs if j is not joueur]
        return autres[0] if autres else None

    def score_total(self):
        """But : score de référence de la partie (somme des joueurs)."""
        return sum(j.score for j in self.joueurs)

    def rapports(self, **details):
        """
        But : résumé de la partie pour chaque joueur, envoyé au serveur
        (classements, XP et succès).
        Entrée : details (mots-clés) : informations propres au mode.
        Sortie : (list de dict) un rapport par joueur.
        """
        return [{"numero": j.numero, "score": j.score, "mode": self.code,
                 "duree": round(self.temps, 1), "stats": stats_serialisables(j.stats),
                 **details} for j in self.joueurs]

    # --- Boucle -------------------------------------------------------------------

    def mettre_a_jour(self, dt, dt_jeu):
        """
        But : une image de jeu.
        Entrées : dt (float) : temps réel ; dt_jeu (float) : temps de jeu
                  (ralenti / gel compris). Sortie : aucune.
        """
        self.temps += dt
        self.temps_message = max(0.0, self.temps_message - dt)
        if self.etat in ("pret", "jeu"):
            self.lire_commandes()
        for joueur in self.joueurs:
            pret = joueur.overdrive_pret()
            if pret and not getattr(joueur, "overdrive_annonce", False):
                from ecrans.bulles import afficher
                afficher(self, "overdrive", joueur)
                self.audio("overdrive_pret", 0.8)
                self.effets.texte("OVERDRIVE PRET !", joueur.raquette.x,
                                  joueur.raquette.y - 50 * -joueur.raquette.sens,
                                  config.AMBRE, 2, duree=1.2)
            joueur.overdrive_annonce = pret
            for fini in joueur.mettre_a_jour(dt_jeu):
                if fini in CATALOGUE and CATALOGUE[fini].categorie == "malus":
                    self.effets.texte("OUF !", joueur.raquette.x, joueur.raquette.y - 30,
                                      config.VERT, 2)
        for terrain in self.terrains:
            terrain.mettre_a_jour_visuel(dt_jeu)
            self.traiter_evenements(terrain)
        if self.bulle:
            self.bulle = (self.bulle[0], max(0.0, self.bulle[1] - dt))
            if self.bulle[1] <= 0:
                self.bulle = None
        self.regles(dt, dt_jeu)

    def pas_physique(self, dt):
        """
        But : un pas de physique à 120 Hz pour tous les terrains.
        Entrée : dt (float). Sortie : aucune.
        """
        if self.etat not in ("pret", "jeu", "victoire"):
            return
        for terrain in self.terrains:
            directions = {}
            for raquette in terrain.raquettes:
                directions[raquette] = self.direction_joueur(raquette.joueur)
            terrain.mettre_a_jour(dt, directions)

    def regles(self, dt, dt_jeu):
        """But : règles propres au mode (minuteries, fin de partie...)."""

    # --- Commandes ------------------------------------------------------------------

    def direction_joueur(self, joueur):
        """
        But : direction voulue par un joueur (avec le malus INVERSION).
        Entrée : joueur (Joueur). Sortie : (int) -1, 0 ou +1.
        """
        if joueur is None or self.etat not in ("pret", "jeu", "victoire"):
            return 0
        direction = self.app.entrees.direction(joueur.profil)
        if joueur.actif("inversion"):
            direction = -direction
        return direction

    def joueur_au_doigt(self):
        """
        But : joueur qui joue au doigt sur cet appareil (boutons à l'écran) : le seul
        joueur en local, ou le joueur local en ligne (attribut joueur_tactile).
        Sortie : (Joueur ou None).
        """
        if hasattr(self, "joueur_tactile"):
            return self.joueur_tactile
        return self.joueurs[0] if len(self.joueurs) == 1 else None

    def lire_commandes(self):
        """But : lancement, pouvoirs et OVERDRIVE de chaque joueur."""
        entrees = self.app.entrees
        for joueur in self.joueurs:
            profil = joueur.profil
            raquette = joueur.raquette
            terrain = joueur.terrain
            clic = self.souris_active and joueur.numero == 1
            if clic and entrees.souris_bougee and terrain.rect.inflate(300, 0).collidepoint(entrees.souris):
                x = entrees.souris[0]
                if joueur.actif("inversion"):
                    x = 2 * terrain.rect.centerx - x
                raquette.viser_souris(x)
            if entrees.vient_d_appuyer("action", profil) or (clic and 1 in entrees.clics):
                if terrain.lancer_balles(raquette):
                    self.audio("lancement")
                    if self.etat == "pret":
                        self.etat = "jeu"
            # Touches 1 2 3 : profil solo, et joueurs en ligne (chacun son clavier).
            for indice in range(config.TAILLE_INVENTAIRE):
                if entrees.vient_d_appuyer(f"pouvoir{indice + 1}", profil):
                    self.utiliser_pouvoir(joueur, indice)
            if entrees.vient_d_appuyer("changer", profil) or (clic and entrees.molette):
                joueur.changer_selection()
                self.audio("menu_nav")
            if entrees.vient_d_appuyer("activer", profil):
                self.utiliser_pouvoir(joueur, joueur.selection)
            if entrees.vient_d_appuyer("overdrive", profil) or (clic and 3 in entrees.clics):
                self.lancer_supernova(joueur)

    def utiliser_pouvoir(self, joueur, indice):
        """
        But : sortir un pouvoir de l'inventaire et le déclencher.
        Entrées : joueur (Joueur) ; indice (int). Sortie : aucune.
        """
        code = joueur.retirer_pouvoir(indice)
        if code is None:
            return
        activer_pouvoir(code, joueur, joueur.terrain)
        joueur.stats["pouvoirs_utilises"].add(code)
        effet = CATALOGUE[code]
        self.effets.texte(effet.nom + " !", joueur.raquette.x,
                          joueur.raquette.y + 40 * joueur.raquette.sens,
                          effet.couleur(), 3, duree=1.0, vitesse=-40 * -joueur.raquette.sens)
        self.audio("pouvoir")
        self.app.crt.declencher_aberration(0.4)

    def lancer_supernova(self, joueur):
        """But : déclencher la SUPERNOVA si la jauge est pleine."""
        if not declencher_supernova(joueur):
            return
        joueur.stats["supernovas"] += 1
        terrain = joueur.terrain
        self.effets.eclair(0.9)
        self.effets.secouer(10)
        self.effets.geler(0.15)
        self.app.crt.declencher_aberration(1.0)
        self.effets.onde(joueur.raquette.x, joueur.raquette.y, joueur.couleur_bord, 500, 0.8, 12)
        self.effets.texte("SUPERNOVA !", terrain.rect.centerx, terrain.rect.centery,
                          config.BLANC, 6, duree=1.4, vitesse=-20)
        self.audio("supernova")

    # --- Événements des terrains --------------------------------------------------------

    def traiter_evenements(self, terrain):
        """But : défiler la File d'événements d'un terrain et y réagir."""
        file = terrain.evenements
        while not file.est_vide():
            evenement = file.defiler()
            methode = getattr(self, "sur_" + evenement[0], None)
            if methode is not None:
                methode(terrain, *evenement[1:])

    def sur_raquette(self, terrain, balle, raquette):
        couleur = raquette.joueur.couleur_corps if raquette.joueur else config.CYAN
        from reseau.profil import style_skin
        self.audio(style_skin(getattr(raquette.joueur, "skin", "neon"))[2])
        self.effets.etincelles(balle.x, balle.y, couleur, raquette.sens, 8)
        if raquette.joueur is not None:
            raquette.joueur.casser_combo()

    def sur_mur(self, terrain, balle):
        self.audio("mur", 0.6)
        self.effets.etincelles(balle.x, balle.y, config.VIOLET, 1, 3)

    def sur_brique_touchee(self, terrain, brique, balle):
        if brique.destructible:
            joueur = balle.proprietaire if balle else None
            self.app.audio.jouer_brique(joueur.combo if joueur else 0)
        else:
            self.audio("metal", 0.8)
        if balle is not None:
            self.effets.etincelles(balle.x, balle.y, brique.couleur_actuelle(),
                                   1 if balle.vy > 0 else -1, 6)
        self.effets.secouer(1.5)

    def sur_brique_detruite(self, terrain, brique, joueur):
        rect = brique.rect()
        self.effets.debris_brique(rect, brique.couleur)
        self.effets.secouer(2.5)
        self.audio("detruite", 0.5)
        if joueur is None:
            return
        gain, monte = joueur.marquer_brique(brique.points * self.multiplicateur_score)
        if gain:
            self.effets.texte(f"+{gain}", rect.centerx, rect.centery, brique.couleur, 2)
        self.app.audio.jouer_brique(joueur.combo)
        for balle in terrain.balles:
            if balle.proprietaire is joueur and not balle.collee:
                balle.fixer_vitesse(min(config.BALLE_VITESSE_MAX,
                                        balle.vitesse() + config.BALLE_ACCEL_PAR_COUP))
                break
        if monte:
            self.effets.texte(f"COMBO x{joueur.multiplicateur}", terrain.rect.centerx,
                              terrain.rect.centery + 60, joueur.couleur_bord, 5,
                              duree=1.1, vitesse=-30)
            self.effets.onde(rect.centerx, rect.centery, config.AMBRE, 160)
            self.app.crt.declencher_aberration(0.7)
            self.audio("combo")
            self.effets.geler(0.05)
        self.apres_brique(terrain, joueur)

    def apres_brique(self, terrain, joueur):
        """But : crochet pour les modes (attaques du mode Course)."""

    def sur_explosion(self, terrain, x, y, rayon):
        self.effets.onde(x, y, config.ROUGE, rayon, 0.4, 8)
        self.effets.explosion(x, y, (255, 140, 40), 30, 380, taille=4)
        self.effets.secouer(7)
        self.effets.geler(0.06)
        self.audio("explosion", 0.8)

    def sur_capsule(self, terrain, capsule, joueur):
        effet = capsule.effet()
        cible = self.cible_capsule(effet, joueur)
        if cible is None:
            return
        resultat = appliquer_capsule(effet.code, cible, cible.terrain)
        if resultat == "stocke":
            from ecrans.bulles import afficher
            afficher(self, "pouvoir", cible)
        if resultat == "vie":
            self.gagner_vie(cible)
        raquette = cible.raquette
        texte = effet.nom
        if cible is not joueur:
            texte = f"{effet.nom} -> J{cible.numero}"
        elif resultat == "plein":
            texte = "INVENTAIRE PLEIN +500"
        elif resultat == "stocke":
            texte = f"{effet.nom} EN STOCK"
        self.effets.texte(texte, raquette.x, raquette.y - 34 * -raquette.sens,
                          effet.couleur(), 2, duree=1.2, vitesse=40 * raquette.sens)
        self.effets.explosion(capsule.x, capsule.y, effet.couleur(), 14, 200, gravite=0)
        if effet.categorie == "malus":
            self.audio("capsule_malus")
            self.effets.secouer(4)
        else:
            self.audio("capsule_bonus", 0.8)

    def cible_capsule(self, effet, joueur):
        """But : qui reçoit l'effet (le Duel envoie les malus à l'adversaire)."""
        return joueur

    def gagner_vie(self, joueur):
        """But : une vie de plus (redéfini par les modes qui ont des vies)."""

    def sur_portail(self, terrain, balle):
        self.audio("portail", 0.7)
        self.effets.onde(balle.x, balle.y, config.VIOLET, 50, 0.3, 3)

    def sur_filet(self, terrain, joueur):
        self.audio("raquette")
        self.effets.texte("FILET !", joueur.raquette.x, joueur.raquette.y - 30,
                          config.VERT, 2)

    def sur_tir_laser(self, terrain, raquette):
        self.audio("laser", 0.6)

    def sur_onde(self, terrain, x, y):
        self.effets.onde(x, y, config.CYAN, 700, 0.6, 10)
        self.effets.secouer(8)
        self.audio("explosion", 0.6)

    def sur_raquette_touchee(self, terrain, raquette):
        self.effets.secouer(8)
        self.effets.texte("ETOURDI !", raquette.x, raquette.y - 30, config.AMBRE, 2)
        self.effets.explosion(raquette.x, raquette.y, config.AMBRE, 16, 260)
        self.audio("metal")

    def sur_boss_touche(self, terrain, balle):
        self.effets.etincelles(balle.x, balle.y, config.BLANC, 1, 10)

    def sur_boss_blesse(self, terrain, x, y):
        self.effets.secouer(3)
        self.audio("metal", 0.7)
        for joueur in terrain.joueurs():
            joueur.score += 100 * self.multiplicateur_score
            joueur.ajouter_overdrive(0.02)

    def sur_boss_phase(self, terrain, phase):
        self.annoncer(f"PHASE {phase} !", config.ROUGE, 1.4)
        self.effets.eclair(0.5, config.ROUGE)
        self.app.crt.declencher_aberration(1.0)
        self.effets.secouer(10)
        self.audio("vie_perdue", 0.6)

    def sur_boss_tir(self, terrain, x, y):
        self.audio("boss_tir", 0.6)

    def sur_boss_rayon(self, terrain, x):
        self.effets.secouer(5)
        self.audio("explosion", 0.4)

    def sur_boss_invocation(self, terrain, x, y):
        self.effets.onde(x, y, config.CYAN, 300, 0.5, 4)

    def sur_boss_mort(self, terrain, x, y):
        self.effets.ralentir(0.3, 1.5)
        self.effets.eclair(1.0)
        self.app.crt.declencher_aberration(1.0)
        self.annoncer("BOSS VAINCU !", config.AMBRE, 2.5)
        for joueur in terrain.joueurs():
            joueur.score += 5000 * self.multiplicateur_score

    def sur_boss_explosion(self, terrain, x, y):
        self.effets.explosion(x, y, config.AMBRE, 30, 450, taille=4, vie=1.0)
        self.effets.onde(x, y, config.BLANC, 140, 0.4, 5)
        self.effets.secouer(9)
        self.audio("explosion", 0.7)

    def sur_balle_perdue(self, terrain, balle, cote):
        y = terrain.rect.bottom - 4 if cote == "bas" else terrain.rect.top + 4
        self.effets.explosion(balle.x, y, config.ROUGE, 26, 380, gravite=200)

    def sur_plus_de_balle(self, terrain):
        """Crochet : plus aucune balle sur ce terrain."""

    def sur_niveau_vide(self, terrain):
        """Crochet : toutes les briques (et le boss) sont détruites."""

    # --- Dessin -------------------------------------------------------------------------

    def dessiner(self, image):
        """But : terrains puis HUD (à compléter par les modes)."""
        for terrain in self.terrains:
            terrain.dessiner(image)
        self.dessiner_hud(image)

    def dessiner_hud(self, image):
        """But : affichage tête haute propre au mode."""

    def dessiner_message(self, image):
        """But : bandeau central temporaire."""
        from moteur.police_pixel import dessiner_texte
        if self.temps_message > 0:
            alpha = 255 if self.temps_message > 0.3 else int(255 * self.temps_message / 0.3)
            echelle = 6 if len(self.message) < 14 else 4
            y = config.HAUTEUR / 2 - 40 + math.sin(self.temps * 4) * 4
            dessiner_texte(image, self.message, config.LARGEUR / 2, y, echelle,
                           self.couleur_message, alpha=alpha)
