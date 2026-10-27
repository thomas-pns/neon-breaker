# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Synthèse sonore chiptune en Python pur (ondes carrée, triangle, dent de
    scie, bruit, enveloppe, glissando, arpèges). Les sons sont écrits en
    .wav 22 kHz 16 bits dans data/sons/ au premier lancement, puis joués
    avec pygame.mixer. Si aucune carte son n'est disponible, le jeu
    continue en silence.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

    Les musiques (moteur/musique.py) passent par des canaux réservés :
    fondus enchaînés entre morceaux, et la musique de l'OVERDRIVE se pose
    « par-dessus » celle du niveau, qui continue en silence et reprend
    là où elle en était.
"""

import array
import math
import os
import random

import pygame

from moteur import config

FREQ = 22050
VERSION_SONS = 2          # changer pour forcer la régénération des .wav
GAMME_COMBO = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24, 26]  # pentatonique


def note(demi_tons, base=440.0):
    """
    But : fréquence d'une note à n demi-tons du La 440.
    Entrées : demi_tons (float), base (float). Sortie : (float) Hz.
    """
    return base * 2 ** (demi_tons / 12)


def onde(forme, phase, rapport=0.5):
    """
    But : valeur d'un oscillateur pour une phase dans [0, 1[.
    Entrées : forme ("carre", "triangle", "scie", "bruit"), phase (float),
              rapport (float) : rapport cyclique de la carrée.
    Sortie : (float) dans [-1, 1].
    """
    if forme == "carre":
        return 1.0 if phase < rapport else -1.0
    if forme == "triangle":
        return 4 * phase - 1 if phase < 0.5 else 3 - 4 * phase
    if forme == "scie":
        return 2 * phase - 1
    return random.uniform(-1, 1)


def synth(duree, freq, freq_fin=None, forme="carre", volume=0.45,
          attaque=0.004, relache=0.6, rapport=0.5, vibrato=0.0,
          arpege=None, pas_arpege=0.04):
    """
    But : générer un son élémentaire.
    Entrées :
        duree (s), freq (Hz) de départ, freq_fin (Hz) : glissando jusqu'à
        cette fréquence (None = fixe), forme d'onde, volume (0..1),
        attaque (s), relache (0..1 : part de la durée en décroissance),
        rapport (rapport cyclique), vibrato (Hz d'amplitude),
        arpege (liste de demi-tons parcourus en boucle), pas_arpege (s).
    Sortie : (list de float) échantillons dans [-1, 1].
    """
    nb = int(duree * FREQ)
    echantillons = [0.0] * nb
    phase = 0.0
    debut_relache = nb * (1 - relache)
    bruit_tenu = 0.0
    for i in range(nb):
        t = i / FREQ
        avance = i / max(1, nb - 1)
        f = freq if freq_fin is None else freq + (freq_fin - freq) * avance
        if arpege:
            f *= 2 ** (arpege[int(t / pas_arpege) % len(arpege)] / 12)
        if vibrato:
            f += math.sin(t * 2 * math.pi * 7) * vibrato
        phase = (phase + f / FREQ) % 1.0
        if forme == "bruit":
            # Bruit « 8-bit » : valeur tenue pendant une période de f.
            if phase < f / FREQ:
                bruit_tenu = random.uniform(-1, 1)
            valeur = bruit_tenu
        else:
            valeur = onde(forme, phase, rapport)
        if t < attaque:
            enveloppe = t / attaque
        elif i > debut_relache:
            enveloppe = max(0.0, 1 - (i - debut_relache) /
                            max(1, nb - debut_relache))
        else:
            enveloppe = 1.0
        echantillons[i] = valeur * enveloppe * volume
    return echantillons


def enchainer(*morceaux):
    """
    But : mettre des sons bout à bout.
    Entrée : morceaux (listes d'échantillons). Sortie : (list).
    """
    resultat = []
    for morceau in morceaux:
        resultat.extend(morceau)
    return resultat


def mixer(*morceaux):
    """
    But : superposer des sons (somme, écrêtée dans [-1, 1]).
    Entrée : morceaux (listes). Sortie : (list).
    """
    longueur = max(len(m) for m in morceaux)
    resultat = [0.0] * longueur
    for morceau in morceaux:
        for i, valeur in enumerate(morceau):
            resultat[i] += valeur
    return [max(-1.0, min(1.0, v)) for v in resultat]


def silence(duree):
    """But : échantillons nuls. Entrée : duree (s). Sortie : (list)."""
    return [0.0] * int(duree * FREQ)


def recette_sons():
    """
    But : décrire tous les effets sonores du jeu.
    Entrée : aucune. Sortie : (dict) nom -> fonction sans argument qui
             renvoie les échantillons.
    """
    recettes = {
        "raquette": lambda: synth(0.09, 330, 520, rapport=0.25, volume=0.4),
        # Sons de rebond des skins (2.1)
        "raquette_cristal": lambda: mixer(synth(0.14, 1320, 1760, "triangle", 0.3, relache=0.8),
                                          synth(0.1, 2640, None, "triangle", 0.1, relache=0.9)),
        "raquette_grave": lambda: synth(0.12, 160, 260, rapport=0.5, volume=0.42, relache=0.6),
        "raquette_laser": lambda: synth(0.12, 1800, 500, rapport=0.125, volume=0.25, relache=0.7),
        "raquette_arcade": lambda: synth(0.12, note(7, 523.25), None, rapport=0.25, volume=0.3,
                                         arpege=[0, 12], pas_arpege=0.04),
        "raquette_glitch": lambda: enchainer(synth(0.03, 900, None, "bruit", 0.25),
                                             synth(0.03, 420, None, "carre", 0.3),
                                             synth(0.04, 1300, None, "carre", 0.2)),
        "raquette_chaud": lambda: mixer(synth(0.11, 260, 420, "scie", 0.3, relache=0.6),
                                        synth(0.08, 800, 300, "bruit", 0.1)),
        "mur": lambda: synth(0.035, 220, 200, rapport=0.5, volume=0.25),
        "metal": lambda: mixer(synth(0.18, 1400, 1300, "triangle", 0.35,
                                     relache=0.9),
                               synth(0.05, 2100, None, "carre", 0.15)),
        "detruite": lambda: mixer(synth(0.12, 3000, 800, "bruit", 0.3),
                                  synth(0.1, 700, 300, rapport=0.125,
                                        volume=0.25)),
        "explosion": lambda: mixer(synth(0.55, 1800, 120, "bruit", 0.55,
                                         relache=0.95),
                                   synth(0.35, 120, 40, "carre", 0.35)),
        "lancement": lambda: synth(0.16, note(3), None, rapport=0.25,
                                   volume=0.3, arpege=[0, 7, 12, 19],
                                   pas_arpege=0.035),
        "vie_perdue": lambda: mixer(synth(0.7, 700, 70, "carre", 0.35,
                                          vibrato=25, relache=0.5),
                                    synth(0.5, 900, 60, "bruit", 0.2)),
        "menu_nav": lambda: synth(0.035, 880, None, rapport=0.25, volume=0.2),
        "menu_ok": lambda: synth(0.14, note(3), None, rapport=0.25,
                                 volume=0.3, arpege=[0, 12], pas_arpege=0.06),
        "pause": lambda: synth(0.18, note(-5), None, "triangle", 0.35,
                               arpege=[12, 0], pas_arpege=0.08),
        "victoire": lambda: enchainer(
            *[synth(0.11, note(n, 523.25), None, rapport=0.25, volume=0.3,
                    relache=0.3) for n in (0, 4, 7, 12, 7, 12)],
            synth(0.5, note(16, 523.25), None, rapport=0.25, volume=0.3,
                  vibrato=6)),
        "game_over": lambda: enchainer(
            *[synth(0.26, note(n, 220), None, "triangle", 0.45, relache=0.4)
              for n in (7, 6, 5)],
            synth(0.9, note(4, 220), None, "triangle", 0.45, vibrato=4,
                  relache=0.7)),
        "combo": lambda: synth(0.18, note(3, 880), None, rapport=0.125,
                               volume=0.25, arpege=[0, 4, 7, 12],
                               pas_arpege=0.03),
        # --- Sons ajoutés en 1.1 ---
        "capsule_bonus": lambda: mixer(
            synth(0.32, note(3, 880), None, "triangle", 0.3, arpege=[0, 4, 7, 12, 16, 19, 24],
                  pas_arpege=0.03, relache=0.5),
            synth(0.32, note(15, 880), None, rapport=0.125, volume=0.08, vibrato=12)),
        "capsule_malus": lambda: mixer(
            synth(0.4, 520, 110, rapport=0.5, volume=0.3, vibrato=30, relache=0.6),
            synth(0.4, 260, 55, "scie", 0.18, relache=0.6)),
        "pouvoir": lambda: mixer(
            synth(0.22, 300, 1800, rapport=0.125, volume=0.28, relache=0.5),
            synth(0.22, 2000, 4000, "bruit", 0.1, relache=0.8)),
        "laser": lambda: synth(0.1, 2400, 600, rapport=0.25, volume=0.18, relache=0.8),
        "boss_tir": lambda: mixer(synth(0.16, 900, 180, "scie", 0.22, relache=0.8),
                                  synth(0.1, 1500, 400, "bruit", 0.12)),
        "portail": lambda: mixer(synth(0.3, 200, 1200, "triangle", 0.25, vibrato=40),
                                 synth(0.3, 600, 2400, "bruit", 0.08)),
        "supernova": lambda: enchainer(
            synth(0.35, 120, 1600, "scie", 0.3, attaque=0.3, relache=0.05),
            mixer(synth(1.0, 2200, 60, "bruit", 0.6, relache=0.97),
                  synth(0.8, 140, 35, "carre", 0.45, relache=0.9),
                  synth(0.6, note(3, 440), None, rapport=0.25, volume=0.18,
                        arpege=[0, 7, 12, 19, 24], pas_arpege=0.05))),
        "overdrive_pret": lambda: synth(0.36, note(3, 440), None, "carre", 0.24, rapport=0.25,
                                        arpege=[0, 7, 12, 19, 24, 31], pas_arpege=0.05,
                                        vibrato=4, relache=0.4),
        "alerte": lambda: enchainer(*[synth(0.22, f1, f2, "carre", 0.25, rapport=0.5,
                                            relache=0.1)
                                      for f1, f2 in ((440, 660), (660, 440)) * 2]),
        "succes": lambda: enchainer(
            *[synth(0.08, note(n, 659.25), None, rapport=0.25, volume=0.26, relache=0.4)
              for n in (0, 5, 9)],
            synth(0.4, note(12, 659.25), None, "triangle", 0.32, vibrato=5, relache=0.8)),
    }
    for i, demi_tons in enumerate(GAMME_COMBO):
        recettes[f"brique_{i}"] = (
            lambda d=demi_tons: mixer(
                synth(0.075, note(d, 523.25), None, rapport=0.25,
                      volume=0.32, relache=0.7),
                synth(0.04, note(d + 12, 523.25), None, "triangle", 0.15)))
    return recettes


def ecrire_wav(chemin, echantillons):
    """
    But : enregistrer des échantillons en .wav mono 16 bits.
    Entrées : chemin (str), echantillons (list de float). Sortie : aucune.
    """
    donnees = array.array("h", (int(v * 32000) for v in echantillons))
    import wave         # pas dans le Python du navigateur (sons livrés en .ogg)
    with wave.open(chemin, "wb") as fichier:
        fichier.setnchannels(1)
        fichier.setsampwidth(2)
        fichier.setframerate(FREQ)
        fichier.writeframes(donnees.tobytes())


def generer_sons(rappel_progression=None):
    """
    But : créer les .wav manquants dans data/sons/.
    Entrée : rappel_progression (fonction(float) ou None) : appelée avec
             l'avancement 0..1 pour l'écran de chargement.
    Sortie : (dict) nom -> chemin du fichier .wav.
    """
    os.makedirs(config.DOSSIER_SONS, exist_ok=True)
    recettes = recette_sons()
    chemins = {}
    for i, (nom, recette) in enumerate(recettes.items()):
        chemin = os.path.join(config.DOSSIER_SONS, f"{nom}_v{VERSION_SONS}.wav")
        if not os.path.exists(chemin):
            ecrire_wav(chemin, recette())
        chemins[nom] = chemin
        if rappel_progression:
            rappel_progression((i + 1) / len(recettes))
    return chemins


def sons_web():
    """
    But : sons et musiques livrés en .ogg avec la version web.
    Sortie : (dict nom -> chemin des effets, dict nom -> chemin des musiques).
    """
    effets, musiques = {}, {}
    try:
        fichiers = sorted(os.listdir(config.DOSSIER_SONS_WEB))
    except OSError:
        return effets, musiques
    for fichier in fichiers:
        nom, extension = os.path.splitext(fichier)
        chemin = os.path.join(config.DOSSIER_SONS_WEB, fichier)
        if extension != ".ogg":
            continue
        if nom.startswith("musique_"):
            musiques[nom[len("musique_"):]] = chemin
        else:
            effets[nom] = chemin
    return effets, musiques


CANAUX_MUSIQUE = 3
VITESSE_FONDU = 1.6          # volume par seconde (fondu d'environ 0,6 s)


# Vibrations (millisecondes) qui accompagnent certains sons, au doigt sur Android.
VIBRATIONS = {"raquette": 12, "raquette_arcade": 12, "raquette_chaud": 12, "raquette_cristal": 12,
              "raquette_glitch": 12, "raquette_grave": 12, "raquette_laser": 12, "metal": 10,
              "explosion": 35, "vie_perdue": 120, "supernova": 80, "detruite": 25, "game_over": 200}

class Audio:
    """
    Lecteur des effets sonores et des musiques.
    Attributs : sons (dict nom -> Sound), musiques (dict nom -> Sound),
    volume_effets, volume_musique (0..1), attenuation (0..1 : pause),
    actif (bool : faux si pas de carte son), en_cours (dict nom -> canal,
    volume courant, volume visé).
    """

    def __init__(self):
        self.sons = {}
        self.musiques = {}
        self.volume_effets = 0.7
        self.vibrations = False       # téléphone Android : petite vibration avec certains sons
        self.volume_musique = 0.5
        self.attenuation = 1.0
        self.actif = pygame.mixer.get_init() is not None
        self.en_cours = {}
        self.libres = []
        if self.actif:
            pygame.mixer.set_reserved(CANAUX_MUSIQUE)
            self.libres = [pygame.mixer.Channel(i) for i in range(CANAUX_MUSIQUE)]

    def charger(self, rappel_progression=None):
        """
        But : générer si besoin puis charger tous les sons et les musiques.
        Entrée : rappel_progression (fonction ou None). Sortie : aucune.
        """
        from moteur.musique import generer_musiques

        def sons(v):
            if rappel_progression:
                rappel_progression(v * 0.4)

        def musiques(v):
            if rappel_progression:
                rappel_progression(0.4 + v * 0.6)

        if config.EST_WEB:
            # Navigateur : sons et musiques fabriqués d'avance (outils/construire_web.py).
            chemins, chemins_musique = sons_web()
        else:
            chemins = generer_sons(sons)
            chemins_musique = generer_musiques(musiques)
        if not self.actif:
            return
        for nom, chemin in chemins.items():
            try:
                self.sons[nom] = pygame.mixer.Sound(chemin)
            except pygame.error:
                pass
        for nom, chemin in chemins_musique.items():
            try:
                self.musiques[nom] = pygame.mixer.Sound(chemin)
            except pygame.error:
                pass

    def musique(self, fond, dessus=None):
        """
        But : choisir la musique. `fond` continue de tourner (en silence) tant
        que `dessus` est joué par-dessus (ex. niveau + OVERDRIVE).
        Entrées : fond, dessus (str ou None). Sortie : aucune.
        """
        if not self.actif:
            return
        voulues = {fond: 0.0 if dessus else 1.0}
        if dessus:
            voulues[dessus] = 1.0
        for nom, piste in self.en_cours.items():
            piste["vise"] = voulues.get(nom, 0.0)
            piste["garder"] = nom in voulues
        for nom, vise in voulues.items():
            if nom and nom not in self.en_cours and nom in self.musiques and self.libres:
                canal = self.libres.pop()
                canal.set_volume(0.0)
                canal.play(self.musiques[nom], loops=-1)
                self.en_cours[nom] = {"canal": canal, "volume": 0.0, "vise": vise, "garder": True}

    def mettre_a_jour(self, dt):
        """But : faire avancer les fondus, libérer les morceaux éteints."""
        for nom in list(self.en_cours):
            piste = self.en_cours[nom]
            ecart = piste["vise"] - piste["volume"]
            piste["volume"] += max(-VITESSE_FONDU * dt, min(VITESSE_FONDU * dt, ecart))
            piste["canal"].set_volume(piste["volume"] * self.volume_musique * self.attenuation)
            if not piste["garder"] and piste["volume"] <= 0.0:
                piste["canal"].stop()
                self.libres.append(piste["canal"])
                del self.en_cours[nom]

    def jouer(self, nom, volume=1.0):
        """
        But : jouer un effet (sans erreur s'il n'existe pas).
        Entrées : nom (str), volume (float 0..1) relatif.
        Sortie : aucune.
        """
        son = self.sons.get(nom)
        if son is not None:
            son.set_volume(self.volume_effets * volume)
            son.play()
        if self.vibrations:
            duree = VIBRATIONS.get(nom) or (8 if nom.startswith("brique_") else 0)
            if duree:
                from moteur import web
                web.vibrer(duree)

    def jouer_brique(self, combo):
        """
        But : son de brique dont la note monte avec le combo.
        Entrée : combo (int). Sortie : aucune.
        """
        indice = min(combo, len(GAMME_COMBO) - 1)
        self.jouer(f"brique_{indice}")
