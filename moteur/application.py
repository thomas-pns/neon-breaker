# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Fenêtre principale et boucle de jeu. Les écrans (titre, jeu, pause...)
    sont rangés dans une Pile maison : l'écran du sommet est actif, et un
    écran « transparent » (pause) laisse voir celui du dessous.
    Gère aussi les transitions VHS, le plein écran (F11) et le debug (F3).

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

    Choisit aussi la musique selon l'écran actif (méthode musique()).
"""

import os
import random

import pygame

from structures.pile import Pile
from moteur import config, sauvegarde
from moteur.audio import Audio
from moteur.entrees import Entrees
from moteur.fond import FondSynthwave
from moteur.police_pixel import dessiner_texte
from moteur.rendu import Ecran, FiltreCRT

DUREE_TRANSITION = 0.45


def choisir_format():
    """
    But : format de l'image : vertical sur téléphone, paysage ailleurs.
    Sortie : config.VERTICAL ou config.PAYSAGE.
    """
    if os.environ.get("NEON_VERTICAL") == "1":
        return config.VERTICAL
    if config.EST_WEB:
        from moteur import web
        if web.parametre("vertical") or web.telephone():
            # Image aussi allongée que l'écran du téléphone (pas de bandes noires) : la
            # zone des commandes, en bas, s'agrandit.
            proportion = max(16 / 9, min(2.25, web.proportion() or 16 / 9))
            config.VERTICAL = (config.VERTICAL[0], int(config.VERTICAL[0] * proportion))
            config.MARGE_HAUT_ECRAN, config.MARGE_BAS_ECRAN = web.marges(config.VERTICAL[0])
            return config.VERTICAL
    return config.PAYSAGE


class Transition:
    """
    Balayage façon cassette VHS : des bandes horizontales bruitées
    recouvrent l'écran, l'action est exécutée au milieu, puis les bandes
    se retirent.
    """

    def __init__(self, action):
        self.action = action
        self.temps = 0.0
        self.action_faite = False

    def mettre_a_jour(self, dt):
        """
        But : avancer la transition, exécuter l'action à mi-parcours.
        Entrée : dt (float). Sortie : (bool) True si terminée.
        """
        self.temps += dt
        if not self.action_faite and self.temps >= DUREE_TRANSITION / 2:
            self.action_faite = True
            self.action()
        return self.temps >= DUREE_TRANSITION

    def dessiner(self, image):
        """
        But : dessiner les bandes de transition.
        Entrée : image (Surface). Sortie : aucune.
        """
        avance = self.temps / DUREE_TRANSITION
        couverture = 1 - abs(avance * 2 - 1)          # 0 -> 1 -> 0
        hauteur_bande = 24
        for y in range(0, config.HAUTEUR, hauteur_bande):
            retard = (y / config.HAUTEUR) * 0.35
            largeur = max(0.0, min(1.0, couverture * 1.6 - retard)) * config.LARGEUR
            if largeur <= 0:
                continue
            if (y // hauteur_bande) % 2:
                rect = (0, y, largeur, hauteur_bande)
            else:
                rect = (config.LARGEUR - largeur, y, largeur, hauteur_bande)
            image.fill((14, 2, 30), rect)
            if random.random() < 0.5:
                image.fill((70, 20, 110), (rect[0], y + random.randint(0, 20),
                                           largeur, 2))


class Application:
    """
    Cœur du programme.
    Attributs :
        ecran (Ecran) : fenêtre et image interne.
        entrees (Entrees) : commandes.
        audio (Audio) : effets sonores.
        fond (FondSynthwave) : fond animé partagé par les écrans.
        crt (FiltreCRT) : filtre rétro.
        pile (Pile) : écrans empilés.
        reglages (dict) : options (CRT, tremblement, particules...).
    """

    def __init__(self, plein_ecran=False, debug=False):
        """
        But : initialiser pygame, la fenêtre et les ressources partagées.
        Entrées : plein_ecran (bool), debug (bool). Sortie : aucune.
        """
        try:
            pygame.mixer.pre_init(22050, -16, 1, 256)
        except pygame.error:
            pass
        pygame.init()
        try:
            pygame.mixer.init()
            pygame.mixer.set_num_channels(24)
        except pygame.error:
            pass
        pygame.display.set_caption(config.TITRE)
        try:
            pygame.display.set_icon(pygame.image.load(
                os.path.join(config.DOSSIER_RESSOURCES, "icone.png")))
        except (pygame.error, FileNotFoundError):
            pass
        # Format de l'image : vertical sur téléphone (ou pour essayer : NEON_VERTICAL=1,
        # ou ?vertical dans l'adresse de la version web), paysage partout ailleurs.
        self.format = choisir_format()
        self.vertical = self.format == config.VERTICAL
        config.orienter(self.format)
        self.ecran = Ecran(plein_ecran, self.format)
        self.image_paysage = None          # écrans pas encore prévus pour le vertical
        self.entrees = Entrees(self.ecran)
        self.audio = Audio()
        self.fond = FondSynthwave()
        self.crt = FiltreCRT(*self.format)
        self.horloge = pygame.time.Clock()
        self.pile = Pile()
        self.transition = None
        self.en_marche = True
        self.debug = debug
        self.donnees = sauvegarde.charger()
        self.reglages = self.donnees["reglages"]
        self.entrees.appliquer_perso(self.reglages.get("touches"))
        self.audio.volume_effets = self.reglages["volume_effets"]
        self.audio.volume_musique = self.reglages["volume_musique"]
        from reseau.client import ServiceEnLigne
        self.en_ligne = ServiceEnLigne(self)
        self.notifications = []

    def notifier(self, titre, couleur="CYAN", sous_titre=""):
        """
        But : afficher une notification en haut à droite (succès, niveau...).
        Entrées : titre (str) ; couleur (nom dans moteur.config) ; sous_titre (str).
        """
        self.notifications.append({"titre": titre, "sous_titre": sous_titre,
                                   "couleur": getattr(config, couleur, config.CYAN),
                                   "temps": 0.0})
        self.audio.jouer("succes", 0.8)

    def _dessiner_notifications(self, image):
        """Bandeaux qui glissent depuis la droite, l'un sous l'autre."""
        from ecrans.hud import panneau
        y = 16
        for notification in self.notifications[:4]:
            t = notification["temps"]
            entree = min(1.0, t / 0.3)
            sortie = max(0.0, (t - 4.2) / 0.3)
            largeur = 380
            x = config.LARGEUR - (largeur + 16) * (1 - (1 - entree) ** 3) + sortie * (largeur + 20)
            rect = pygame.Rect(int(x), y, largeur, 64 if notification["sous_titre"] else 44)
            panneau(image, rect, notification["couleur"])
            dessiner_texte(image, notification["titre"][:28], rect.x + 16, rect.y + 22, 2,
                           notification["couleur"], ancrage="gauche")
            if notification["sous_titre"]:
                dessiner_texte(image, notification["sous_titre"][:30], rect.x + 16, rect.y + 46,
                               2, config.BLANC, ancrage="gauche", lueur=False, ombre=False)
            y += rect.h + 10

    def enregistrer(self):
        """
        But : écrire réglages et scores sur le disque.
        Entrée : aucune. Sortie : aucune.
        """
        sauvegarde.enregistrer(self.donnees)

    def classement(self, mode):
        """
        But : top 10 d'un mode, du meilleur au moins bon.
        Entrée : mode (str). Sortie : (list de dict {"nom", "score"}).
        """
        return self.donnees.setdefault("classements", {}).setdefault(mode, [])

    def meilleur_score(self, mode):
        """
        But : meilleur score enregistré pour un mode.
        Entrée : mode (str). Sortie : (int).
        """
        top = self.classement(mode)
        return max(self.donnees["meilleurs"].get(mode, 0), top[0]["score"] if top else 0)

    def entre_dans_classement(self, mode, score):
        """
        But : le score mérite-t-il une place dans le top 10 ?
        Entrées : mode (str), score (int). Sortie : (bool).
        """
        top = self.classement(mode)
        return score > 0 and (len(top) < 10 or score > top[-1]["score"])

    def ajouter_au_classement(self, mode, nom, score):
        """
        But : insérer un score dans le top 10 et sauvegarder.
        Entrées : mode (str), nom (str 3 lettres), score (int).
        Sortie : (int) rang obtenu (0 = premier), -1 si hors classement.
        """
        top = self.classement(mode)
        rang = next((i for i, e in enumerate(top) if score > e["score"]), len(top))
        if rang >= 10:
            return -1
        top.insert(rang, {"nom": nom, "score": score})
        del top[10:]
        self.donnees["meilleurs"][mode] = max(self.donnees["meilleurs"].get(mode, 0), score)
        self.enregistrer()
        return rang

    def niveau_debloque(self, cle):
        """But : dernier niveau débloqué (indice) pour "campagne" ou "coop"."""
        return self.donnees.setdefault("progression", {}).get(cle, 0)

    def lancer_transition(self, action):
        """
        But : balayage VHS qui exécute `action` à mi-parcours.
        Entrée : action (fonction sans argument). Sortie : aucune.
        """
        self.transition = Transition(action)

    # --- Gestion des écrans --------------------------------------------------

    def ecran_actif(self):
        """
        But : écran au sommet de la pile (None si vide).
        Entrée : aucune. Sortie : (EcranBase ou None).
        """
        return None if self.pile.est_vide() else self.pile.sommet()

    def empiler(self, ecran):
        """
        But : poser un écran par-dessus l'actuel (ex. pause).
        Entrée : ecran (EcranBase). Sortie : aucune.
        """
        ecran.dessous = self.ecran_actif()
        self.pile.empiler(ecran)
        ecran.entrer()

    def depiler(self):
        """
        But : retirer l'écran du sommet et revenir au précédent.
        Entrée : aucune. Sortie : aucune.
        """
        if not self.pile.est_vide():
            self.pile.depiler().quitter()
        actif = self.ecran_actif()
        if actif is not None:
            actif.reprendre()

    def remplacer(self, ecran, transition=True):
        """
        But : vider la pile et la remplacer par un nouvel écran.
        Entrées : ecran (EcranBase) ; transition (bool) : balayage VHS.
        Sortie : aucune.
        """
        def action():
            while not self.pile.est_vide():
                self.pile.depiler().quitter()
            self.empiler(ecran)

        if transition:
            self.transition = Transition(action)
        else:
            action()

    # --- Boucle principale ---------------------------------------------------

    def charger(self):
        """
        But : générer/charger les sons avec une barre de progression.
        Entrée : aucune. Sortie : aucune.
        """
        def progression(valeur):
            pygame.event.pump()
            image = self.ecran.image
            image.fill(config.CIEL_HAUT)
            cx, cy = config.LARGEUR // 2, config.HAUTEUR // 2
            dessiner_texte(image, "CHARGEMENT", cx, cy - 40, 4, config.CYAN)
            pygame.draw.rect(image, config.ROSE, (cx - 200, cy + 20, 400, 20), 2)
            image.fill(config.ROSE, (cx - 196, cy + 24, int(392 * valeur), 12))
            self.ecran.presenter()

        self.audio.charger(progression)

    def lancer(self, premier_ecran):
        """
        But : boucle principale jusqu'à la fermeture.
        Entrée : premier_ecran (EcranBase) : écran de départ.
        Sortie : aucune.
        """
        self._demarrer(premier_ecran)
        while self.en_marche and self.ecran_actif() is not None:
            self._image()
        pygame.quit()

    async def lancer_web(self, premier_ecran):
        """
        But : boucle principale de la version navigateur : la même, mais on
        rend la main au navigateur après chaque image (sinon la page gèle).
        Entrée : premier_ecran (EcranBase).
        """
        import asyncio
        from moteur import web
        self._demarrer(premier_ecran)
        web.demarre()
        mesure = web.parametre("profil")      # ?profil : mesurer où passe le temps
        if mesure:
            await self._profiler_web(web)
        if web.parametre("banc"):
            from outils.banc_web import banc
            web.journal(banc())
        while self.ecran_actif() is not None:
            if not self.en_marche:              # QUITTER : on revient à l'accueil
                self.en_marche = True
            self._image()
            await asyncio.sleep(0)

    async def _profiler_web(self, web):
        """
        But : (outil) mesurer le temps des images dans le navigateur, sur l'accueil
        puis en Campagne, étape par étape, et l'écrire dans la console du navigateur.
        """
        import asyncio
        import time
        from ecrans.modes import fabrique_mode
        from ecrans.partie import EcranPartie
        temps = {}

        def chronometrer(objet, methode, nom):
            origine = getattr(objet, methode)

            def mesuree(*args, **kwargs):
                debut = time.perf_counter()
                try:
                    return origine(*args, **kwargs)
                finally:
                    temps[nom] = temps.get(nom, 0.0) + time.perf_counter() - debut
            setattr(objet, methode, mesuree)

        web.journal(f"NEON SONS : {len(self.audio.sons)} effets, {len(self.audio.musiques)} musiques "
                    f"(audio actif : {self.audio.actif})")
        chronometrer(self, "_evenements", "evenements")
        chronometrer(self, "_mettre_a_jour", "mise a jour")
        chronometrer(self.fond, "dessiner", "fond")
        chronometrer(self.crt, "appliquer", "filtre CRT")
        chronometrer(pygame.display, "flip", "affichage (flip)")
        chronometrer(pygame.transform, "smoothscale", "mise a l'echelle")
        for nom in ("accueil", "partie"):
            if nom == "partie":
                self.remplacer(EcranPartie(self, fabrique_mode("campagne")), transition=False)
            ecran = self.ecran_actif()
            chronometrer(ecran, "dessiner", "ecran " + nom)
            for _ in range(20):
                self._image()
                await asyncio.sleep(0)
            temps.clear()
            debut = time.perf_counter()
            for _ in range(60):
                self._image()
            total = (time.perf_counter() - debut) / 60 * 1000
            lignes = [f"NEON PROFIL {nom} : {total:.1f} ms par image"]
            for cle, valeur in sorted(temps.items(), key=lambda e: -e[1]):
                lignes.append(f"  {cle:<20} {valeur / 60 * 1000:7.1f} ms")
            web.journal("\n".join(lignes))
            await asyncio.sleep(0)
            detail = web.profiler(lambda: [self._image() for _ in range(10)])
            web.journal("NEON DETAIL " + nom + " (10 images)\n" + detail)
            await asyncio.sleep(0)

    def _demarrer(self, premier_ecran):
        """Charger les sons, afficher le premier écran, vérifier la session."""
        self.charger()
        self.empiler(premier_ecran)
        self.en_ligne.verifier_session()
        self.en_ligne.verifier_version(self._version_recue)

    def _image(self):
        """Une image du jeu : événements, mise à jour, dessin."""
        dt = min(self.horloge.tick(config.FPS) / 1000, 0.1)
        self.regler_format()
        self._evenements()
        self._mettre_a_jour(dt)
        self.regler_format()              # un écran a pu arriver entre-temps
        self._dessiner()

    def pile_dessin(self):
        """But : écrans à dessiner, du sommet vers le bas (les transparents laissent voir)."""
        actif = self.ecran_actif()
        if actif is None:
            return []
        pile = [actif]
        while pile[-1].transparent and pile[-1].dessous:
            pile.append(pile[-1].dessous)
        return pile

    def regler_format(self):
        """
        But : au format vertical, les écrans pas encore prévus pour lui sont dessinés en
        paysage (1280x720), réduits au milieu de l'image. Règle le format en cours
        (config.LARGEUR, config.HAUTEUR) et la zone qui convertit la souris.
        """
        if not self.vertical:
            return
        paysage = not all(ecran.vertical for ecran in self.pile_dessin())
        config.orienter(config.PAYSAGE if paysage else config.VERTICAL)
        if paysage:
            largeur = config.VERTICAL[0]
            hauteur = largeur * config.PAYSAGE[1] // config.PAYSAGE[0]
            self.ecran.sous_zone = pygame.Rect(0, (config.VERTICAL[1] - hauteur) // 2,
                                               largeur, hauteur)
        else:
            self.ecran.sous_zone = None

    def _version_recue(self, resultat):
        """Une version plus récente existe : proposer la mise à jour."""
        if config.EST_TEST or config.EST_WEB:
            return                  # un exe de test ne se remplace jamais tout seul ;
                                    # la version web est toujours celle du serveur
        from reseau.mise_a_jour import version_disponible
        infos = version_disponible(resultat.get("donnees"))
        if infos is not None:
            from ecrans.mise_a_jour import EcranMiseAJour
            self.empiler(EcranMiseAJour(self, infos))

    def _evenements(self):
        """Lire tous les événements pygame de l'image."""
        self.entrees.debut_image()
        for evenement in pygame.event.get():
            if evenement.type == pygame.QUIT:
                self.en_marche = False
            elif evenement.type == pygame.VIDEORESIZE:
                self.ecran.redimensionner()
            elif evenement.type == pygame.KEYDOWN and evenement.key == pygame.K_F11:
                self.ecran.basculer_plein_ecran()
            elif evenement.type == pygame.KEYDOWN and evenement.key == pygame.K_F3:
                self.debug = not self.debug
            self.entrees.traiter(evenement)

    def _mettre_a_jour(self, dt):
        """Faire avancer l'écran actif, la transition et les effets globaux."""
        self.fond.mettre_a_jour(dt)
        self.crt.mettre_a_jour(dt)
        self.crt.actif = self.reglages["crt"]
        self.en_ligne.traiter()
        for notification in self.notifications:
            notification["temps"] += dt
        self.notifications = [n for n in self.notifications if n["temps"] < 4.6]
        if self.transition is not None:
            if self.transition.mettre_a_jour(dt):
                self.transition = None
            # Pas de commandes pendant la transition.
            self.entrees.debut_image()
        actif = self.ecran_actif()
        if actif is not None:
            actif.mettre_a_jour(dt)
        self._musique(dt)

    def _musique(self, dt):
        """Demander à l'écran actif sa musique et faire avancer les fondus."""
        actif = self.ecran_actif()
        if actif is not None:
            voulue = actif.musique()
            fond, dessus = voulue if isinstance(voulue, tuple) else (voulue, None)
            self.audio.musique(fond, dessus)
            self.audio.attenuation = 0.35 if getattr(actif, "attenuer_musique", False) else 1.0
        self.audio.mettre_a_jour(dt)

    def _dessiner(self):
        """Dessiner l'écran actif (et celui du dessous s'il est transparent)."""
        image = self.ecran.image
        actif = self.ecran_actif()
        if actif is None:
            return
        sous_zone = self.ecran.sous_zone
        if sous_zone is not None:          # écran pas encore vertical : dessiné en paysage
            if self.image_paysage is None:
                self.image_paysage = pygame.Surface(config.PAYSAGE)
            cible = self.image_paysage
        else:
            cible = image
        for ecran in reversed(self.pile_dessin()):
            ecran.dessiner(cible)
        onglets_en_bas = (sous_zone is None and self.vertical and hasattr(actif, "dessiner_barre")
                          and getattr(actif, "onglet", None) is not None)
        if self.entrees.tactile and getattr(actif, "bouton_retour", True) and not onglets_en_bas:
            from ecrans.tactile import bouton_retour        # au doigt : pas de touche Échap
            bouton_retour(cible, self)
        if self.transition is not None:
            self.transition.dessiner(cible)
        if sous_zone is not None:
            config.orienter(config.VERTICAL)
            self.fond.dessiner(image)
            image.fill((70, 70, 90), special_flags=pygame.BLEND_RGB_MULT)
            image.blit(pygame.transform.smoothscale(cible, sous_zone.size), sous_zone)
            pygame.draw.rect(image, config.VIOLET, sous_zone.inflate(4, 4), 2)
        if self.notifications:
            self._dessiner_notifications(image)
        self.crt.appliquer(image)
        if self.debug:
            dessiner_texte(image, f"FPS {self.horloge.get_fps():.0f}",
                           8, 8, 2, config.VERT, ancrage="haut_gauche",
                           lueur=False)
        self.ecran.tremblement = actif.tremblement() if \
            self.reglages["tremblement"] else (0, 0)
        self.ecran.presenter()
