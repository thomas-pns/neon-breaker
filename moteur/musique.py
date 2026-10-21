# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Compositeur synthwave : génère les musiques en boucle du jeu (menu,
    un thème par monde, boss, OVERDRIVE) sans aucun fichier audio fourni.
    Chaque morceau est décrit par une « partition » (tempo, tonalité,
    grille d'accords, motifs) puis rendu avec numpy : basse en dents de
    scie, nappe désaccordée, arpège avec écho, mélodie, batterie
    électronique (grosse caisse, caisse claire, charleston). Les queues
    de notes qui dépassent la fin sont replacées au début : la boucle
    est parfaitement continue. Les .wav sont écrits dans data/sons/ au
    premier lancement (environ une seconde), puis réutilisés.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import os
import random
import wave

from moteur import config

FREQ = 22050
VERSION_MUSIQUE = 1          # changer pour forcer la régénération

# Accords : (décalage en demi-tons depuis la tonique, "m" mineur / "M" majeur).
PARTITIONS = {
    # Menu : calme, nappe et arpège doux, la mélodie arrive à la 2e moitié.
    "menu": {"bpm": 96, "tonique": 57, "graine": 11, "mesures_par_accord": 2,
             "accords": [(0, "m"), (-4, "M"), (3, "M"), (-2, "M")] * 2,
             "batterie": "douce", "basse": "longue", "arpege": "croches",
             "melodie_depuis": 8, "couleur_lead": "triangle"},
    # Monde 1, Sunset Grid : l'hymne principal.
    "monde1": {"bpm": 118, "tonique": 57, "graine": 3, "mesures_par_accord": 1,
               "accords": [(0, "m"), (-4, "M"), (3, "M"), (-2, "M")] * 4,
               "batterie": "synthwave", "basse": "croches", "arpege": "doubles",
               "melodie_depuis": 8, "couleur_lead": "scie"},
    # Monde 2, Neon City : plus nocturne.
    "monde2": {"bpm": 124, "tonique": 50, "graine": 21, "mesures_par_accord": 1,
               "accords": [(0, "m"), (-4, "M"), (5, "m"), (7, "M")] * 4,
               "batterie": "synthwave", "basse": "octaves", "arpege": "doubles",
               "melodie_depuis": 8, "couleur_lead": "carre"},
    # Monde 3, Cyber Core : sombre et rapide.
    "monde3": {"bpm": 132, "tonique": 52, "graine": 7, "mesures_par_accord": 1,
               "accords": [(0, "m"), (-4, "M"), (5, "m"), (7, "M")] * 4,
               "batterie": "four", "basse": "doubles", "arpege": "doubles",
               "melodie_depuis": 4, "couleur_lead": "scie"},
    # Boss : tension (accord de dominante majeur), basse martelée.
    "boss": {"bpm": 140, "tonique": 48, "graine": 13, "mesures_par_accord": 1,
             "accords": [(0, "m"), (-4, "M"), (5, "m"), (7, "M")] * 4,
             "batterie": "four", "basse": "doubles", "arpege": "stabs",
             "melodie_depuis": 8, "couleur_lead": "carre"},
    # OVERDRIVE : lumineux, très rapide.
    "overdrive": {"bpm": 152, "tonique": 57, "graine": 5, "mesures_par_accord": 1,
                  "accords": [(-4, "M"), (-2, "M"), (0, "m"), (0, "m")] * 2,
                  "batterie": "four", "basse": "octaves", "arpege": "doubles",
                  "melodie_depuis": 0, "couleur_lead": "scie"},
}

GAMME_MINEURE = [0, 2, 3, 5, 7, 8, 10]
PENTA_MINEURE = [0, 3, 5, 7, 10]


def hz(midi):
    """But : fréquence d'une note MIDI. Entrée : midi (float). Sortie : (float)."""
    return 440.0 * 2 ** ((midi - 69) / 12)


def triade(tonique, accord):
    """But : notes MIDI (fondamentale, tierce, quinte) d'un accord."""
    decalage, qualite = accord
    racine = tonique + decalage
    return [racine, racine + (3 if qualite == "m" else 4), racine + 7]


class Rendu:
    """
    Tampon de rendu d'un morceau. Attributs : np (module numpy), longueur
    (échantillons d'une boucle), pistes (dict nom -> tableau), bpm, pas
    (durée d'une double croche en échantillons).
    """

    def __init__(self, np, bpm, mesures):
        self.np = np
        self.bpm = bpm
        self.pas = 60 / bpm / 4 * FREQ
        self.longueur = int(round(self.pas * 16 * mesures))
        self.pistes = {}

    def piste(self, nom):
        if nom not in self.pistes:
            self.pistes[nom] = self.np.zeros(self.longueur + FREQ * 3)
        return self.pistes[nom]

    def poser(self, nom, debut_pas, son):
        """But : ajouter un son à la piste, au pas (double croche) donné."""
        piste = self.piste(nom)
        debut = int(round(debut_pas * self.pas))
        fin = min(len(piste), debut + len(son))
        piste[debut:fin] += son[:fin - debut]

    def replier(self, piste):
        """But : replacer la queue qui dépasse la boucle au début (boucle continue)."""
        boucle = piste[:self.longueur].copy()
        reste = piste[self.longueur:]
        while len(reste):
            morceau = reste[:self.longueur]
            boucle[:len(morceau)] += morceau
            reste = reste[self.longueur:]
        return boucle


# --- Instruments (numpy) ---------------------------------------------------------------------

def oscillateur(np, forme, frequences, duree, rapport=0.5):
    """But : onde de fréquence éventuellement variable. Sortie : tableau [-1, 1]."""
    n = int(duree * FREQ)
    f = np.broadcast_to(np.asarray(frequences, dtype=float), (n,)) if np.ndim(frequences) == 0 \
        else np.asarray(frequences, dtype=float)[:n]
    phase = np.cumsum(f / FREQ) % 1.0
    if forme == "scie":
        return 2 * phase - 1
    if forme == "carre":
        return np.where(phase < rapport, 1.0, -1.0)
    if forme == "triangle":
        return np.where(phase < 0.5, 4 * phase - 1, 3 - 4 * phase)
    return np.sin(2 * np.pi * phase)


def adoucir(np, signal, taille):
    """But : filtre passe-bas grossier (moyenne glissante, appliquée deux fois)."""
    if taille <= 1:
        return signal
    noyau = np.ones(taille) / taille
    return np.convolve(np.convolve(signal, noyau, "same"), noyau, "same")


def enveloppe(np, n, attaque, declin, maintien=0.0, relache=0.02):
    """But : enveloppe ADSR simple (durées en s) sur n échantillons."""
    t = np.arange(n) / FREQ
    env = np.ones(n)
    if attaque > 0:
        env = np.minimum(env, t / attaque)
    duree = n / FREQ
    corps = np.where(t > attaque, maintien + (1 - maintien) * np.exp(-(t - attaque) / max(declin, 1e-3)), 1)
    env = np.minimum(env, corps)
    fin = np.clip((duree - t) / max(relache, 1e-3), 0, 1)
    return env * fin


def note_scie(np, midi, duree, volume, desaccord=0.0, filtre=4, attaque=0.005, declin=0.25,
              maintien=0.6, voix=1):
    """But : note de basse ou de nappe en dents de scie (plusieurs voix désaccordées)."""
    n = int(duree * FREQ)
    son = np.zeros(n)
    for v in range(voix):
        ecart = (v - (voix - 1) / 2) * desaccord
        son += oscillateur(np, "scie", hz(midi + ecart), duree)
    son = adoucir(np, son / voix, filtre)
    return son * enveloppe(np, n, attaque, declin, maintien) * volume


def note_pulse(np, midi, duree, volume, rapport=0.25, declin=0.08, forme="carre", filtre=2):
    """But : note courte d'arpège ou de mélodie."""
    n = int(duree * FREQ)
    son = adoucir(np, oscillateur(np, forme, hz(midi), duree, rapport), filtre)
    return son * enveloppe(np, n, 0.003, declin, 0.15) * volume


def note_lead(np, midi, duree, volume, forme="scie"):
    """But : note de mélodie avec vibrato qui arrive progressivement."""
    n = int(duree * FREQ)
    t = np.arange(n) / FREQ
    vibrato = 0.18 * np.minimum(1, t / 0.25) * np.sin(2 * np.pi * 5.5 * t)
    freq = hz(midi + vibrato)
    son = oscillateur(np, forme, freq, duree, 0.5) + 0.5 * oscillateur(np, forme, freq * 1.004, duree, 0.5)
    son = adoucir(np, son / 1.5, 3)
    return son * enveloppe(np, n, 0.01, 0.4, 0.7, 0.05) * volume


def grosse_caisse(np, volume=1.0):
    duree = 0.32
    n = int(duree * FREQ)
    t = np.arange(n) / FREQ
    freq = 45 + 110 * np.exp(-t / 0.035)
    son = oscillateur(np, "sinus", freq, duree)
    clic = np.random.uniform(-1, 1, n) * np.exp(-t / 0.004) * 0.3
    return (son * np.exp(-t / 0.11) + clic) * volume


def caisse_claire(np, volume=1.0):
    duree = 0.3
    n = int(duree * FREQ)
    t = np.arange(n) / FREQ
    bruit = np.random.uniform(-1, 1, n)
    bruit = bruit - adoucir(np, bruit, 3) * 0.6
    ton = oscillateur(np, "sinus", 190 * (1 + 0.3 * np.exp(-t / 0.02)), duree)
    return (bruit * np.exp(-t / 0.09) * 0.7 + ton * np.exp(-t / 0.05) * 0.5) * volume


def charleston(np, ouvert=False, volume=1.0):
    duree = 0.25 if ouvert else 0.06
    n = int(duree * FREQ)
    t = np.arange(n) / FREQ
    bruit = np.random.uniform(-1, 1, n)
    aigu = bruit - adoucir(np, bruit, 2)
    return aigu * np.exp(-t / (0.08 if ouvert else 0.015)) * volume


def echo(np, boucle, retard, retour, repetitions=4):
    """But : écho (delay) circulaire : les répétitions bouclent avec le morceau."""
    resultat = boucle.copy()
    for k in range(1, repetitions + 1):
        resultat += np.roll(boucle, int(retard * k)) * retour ** k
    return resultat


def reverbe(np, boucle, melange=0.25):
    """But : réverbération grossière et circulaire (retards premiers qui s'estompent)."""
    queue = np.zeros_like(boucle)
    for retard_ms, gain in ((29.7, 0.7), (37.1, 0.65), (41.1, 0.6), (43.7, 0.55)):
        decal = int(retard_ms / 1000 * FREQ)
        for k in range(1, 7):
            queue += np.roll(boucle, decal * k) * gain ** k
    return boucle + queue * melange / 4


# --- Composition ---------------------------------------------------------------------------------

def motif_rythmique(rng, densite):
    """
    But : rythme de mélodie sur 2 mesures (32 doubles croches).
    Sortie : (list de (pas, longueur)).
    """
    pas, motif = 0, []
    longueurs = [2, 2, 4, 2, 6, 4, 3] if densite == "vive" else [4, 4, 2, 6, 8, 4]
    while pas < 30:
        longueur = rng.choice(longueurs)
        if rng.random() < 0.18 and motif:
            pas += 2                       # petite respiration
            continue
        longueur = min(longueur, 32 - pas)
        motif.append((pas, longueur))
        pas += longueur
    return motif


def hauteur_melodie(rng, tonique, accord, temps_fort, precedente):
    """But : note de mélodie : note de l'accord sur les temps forts, pentatonique sinon."""
    candidats = []
    for octave in (12, 24):
        if temps_fort:
            candidats += [n + octave for n in triade(tonique, accord)]
        else:
            candidats += [tonique + octave + d for d in PENTA_MINEURE]
    candidats = [c for c in candidats if tonique + 10 <= c <= tonique + 29]
    if precedente is None:
        return rng.choice(candidats)
    # On préfère les petits intervalles : mélodie chantante.
    candidats.sort(key=lambda c: abs(c - precedente) + rng.random() * 3)
    return candidats[0] if rng.random() < 0.7 else candidats[min(1, len(candidats) - 1)]


def composer(nom, np):
    """
    But : rendre un morceau complet.
    Entrées : nom (clé de PARTITIONS), np (module numpy).
    Sortie : (tableau numpy float) une boucle, normalisée.
    """
    partition = PARTITIONS[nom]
    rng = random.Random(partition["graine"])
    np.random.seed(partition["graine"])
    accords = partition["accords"]
    par_accord = partition["mesures_par_accord"]
    mesures = len(accords) * par_accord
    rendu = Rendu(np, partition["bpm"], mesures)
    tonique = partition["tonique"]
    noire = 4 * rendu.pas / FREQ                  # durée d'un temps (s)
    dc = rendu.pas / FREQ                          # durée d'une double croche (s)

    # Sons de batterie fabriqués une fois.
    gc, cc = grosse_caisse(np), caisse_claire(np)
    ch, cho = charleston(np), charleston(np, ouvert=True)

    for m in range(mesures):
        accord = accords[m // par_accord]
        notes = triade(tonique, accord)
        racine = notes[0]
        debut = m * 16
        # Batterie.
        style = partition["batterie"]
        for p in range(16):
            if style == "douce":
                if p in (0, 10):
                    rendu.poser("batterie", debut + p, gc * 0.55)
                if p in (4, 12) and m % 2:
                    rendu.poser("batterie", debut + p, cc * 0.25)
                if p % 4 == 2:
                    rendu.poser("batterie", debut + p, ch * 0.35)
            else:
                kick = p % 4 == 0 if style == "four" else p in (0, 6, 8) or (p == 14 and m % 4 == 3)
                if kick:
                    rendu.poser("batterie", debut + p, gc * 0.9)
                if p in (4, 12):
                    rendu.poser("batterie", debut + p, cc * 0.65)
                if p % 2 == 0:
                    rendu.poser("batterie", debut + p, (cho if p % 4 == 2 else ch) * 0.3)
                elif style == "four":
                    rendu.poser("batterie", debut + p, ch * 0.18)
            # Roulement de caisse claire à la fin de chaque section de 4 mesures.
            if style != "douce" and m % 4 == 3 and p >= 12:
                rendu.poser("batterie", debut + p, cc * (0.25 + 0.1 * (p - 12)))

        # Basse.
        basse = partition["basse"]
        grave = racine - 12 if racine - 12 >= 33 else racine
        if basse == "longue":
            for b in (0, 8):
                rendu.poser("basse", debut + b, note_scie(np, grave, dc * 7.5, 0.5, filtre=6,
                                                          declin=0.6, maintien=0.5))
        else:
            pas_basse = 1 if basse == "doubles" else 2
            for p in range(0, 16, pas_basse):
                hauteur = grave + (12 if basse == "octaves" and (p // 2) % 2 else 0)
                accent = 1.0 if p % 4 == 0 else 0.75
                rendu.poser("basse", debut + p, note_scie(np, hauteur, dc * pas_basse * 0.9,
                                                          0.42 * accent, filtre=5, declin=0.09,
                                                          maintien=0.25))

        # Nappe (accord tenu sur la durée de l'accord).
        if m % par_accord == 0:
            duree = dc * 16 * par_accord
            for hauteur in notes:
                rendu.poser("nappe", debut, note_scie(np, hauteur + 12, duree, 0.12, desaccord=0.12,
                                                      filtre=9, attaque=0.25, declin=2.0,
                                                      maintien=0.7, voix=3))

        # Arpège.
        style_arp = partition["arpege"]
        ordre = [0, 1, 2, 1, 2, 0, 1, 2] if style_arp != "stabs" else []
        if style_arp == "stabs":
            for p in (0, 3, 6, 10, 12):
                for hauteur in notes:
                    rendu.poser("arpege", debut + p, note_pulse(np, hauteur + 12, dc * 1.6, 0.13,
                                                                rapport=0.5, declin=0.06))
        else:
            pas_arp = 2 if style_arp == "croches" else 1
            for k, p in enumerate(range(0, 16, pas_arp)):
                hauteur = notes[ordre[k % len(ordre)]] + 12 + (12 if (k // 3) % 2 else 0)
                forme = "triangle" if style_arp == "croches" else "carre"
                rendu.poser("arpege", debut + p, note_pulse(np, hauteur, dc * pas_arp * 0.9, 0.16,
                                                            forme=forme, declin=0.07))

    # Mélodie : un motif de 2 mesures, répété et réajusté sur chaque accord.
    depuis = partition["melodie_depuis"]
    motif = motif_rythmique(rng, "vive" if partition["bpm"] >= 130 else "calme")
    variante = motif_rythmique(rng, "vive" if partition["bpm"] >= 130 else "calme")
    precedente = None
    for bloc in range(depuis, mesures, 2):
        rythme = variante if (bloc // 2) % 4 == 3 else motif
        for pas, longueur in rythme:
            m = bloc + pas // 16
            if m >= mesures:
                break
            accord = accords[m // par_accord]
            temps_fort = pas % 8 == 0
            precedente = hauteur_melodie(rng, tonique, accord, temps_fort, precedente)
            rendu.poser("melodie", bloc * 16 + pas,
                        note_lead(np, precedente, dc * longueur * 0.95, 0.2,
                                  partition["couleur_lead"]))

    # Mixage : écho sur l'arpège et la mélodie, réverbération générale.
    pistes = {nom_piste: rendu.replier(piste) for nom_piste, piste in rendu.pistes.items()}
    retard = rendu.pas * 3                            # croche pointée
    if "arpege" in pistes:
        pistes["arpege"] = echo(np, pistes["arpege"], retard, 0.35)
    if "melodie" in pistes:
        pistes["melodie"] = echo(np, pistes["melodie"], retard, 0.28)
    volumes = {"batterie": 0.85, "basse": 0.9, "nappe": 1.0, "arpege": 0.8, "melodie": 0.95}
    mix = sum(pistes[p] * volumes[p] for p in pistes)
    mix = reverbe(np, mix, melange=0.3)
    mix = mix / max(1e-6, np.max(np.abs(mix)))
    mix = np.tanh(mix * 1.6) / np.tanh(1.6)         # saturation douce, pas d'écrêtage dur
    return mix * 0.85


def ecrire_wav(chemin, echantillons):
    """But : enregistrer une boucle en .wav mono 16 bits."""
    donnees = (echantillons.clip(-1, 1) * 32000).astype("<i2")
    temporaire = chemin + ".tmp"
    with wave.open(temporaire, "wb") as fichier:
        fichier.setnchannels(1)
        fichier.setsampwidth(2)
        fichier.setframerate(FREQ)
        fichier.writeframes(donnees.tobytes())
    os.replace(temporaire, chemin)


def chemin_musique(nom):
    return os.path.join(config.DOSSIER_SONS, f"musique_{nom}_v{VERSION_MUSIQUE}.wav")


def generer_musiques(rappel_progression=None):
    """
    But : créer les musiques manquantes.
    Entrée : rappel_progression (fonction(float) ou None).
    Sortie : (dict) nom -> chemin (vide si numpy est absent).
    """
    try:
        import numpy as np
    except ImportError:
        return {}
    os.makedirs(config.DOSSIER_SONS, exist_ok=True)
    chemins = {}
    for i, nom in enumerate(PARTITIONS):
        chemin = chemin_musique(nom)
        if not os.path.exists(chemin):
            ecrire_wav(chemin, composer(nom, np))
        chemins[nom] = chemin
        if rappel_progression:
            rappel_progression((i + 1) / len(PARTITIONS))
    return chemins
