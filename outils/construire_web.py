# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Fabriquer la version navigateur de NEON BREAKER (pygbag, Python en
    WebAssembly), à servir par le serveur du jeu :

        build/web/jeu/        page du jeu (index.html, neonbreaker.apk, icônes...)
        build/web/archives/   moteur Python du navigateur (copie de pygame-web/archives)

    Étapes :
      1. copier le code du jeu dans un dossier de travail ;
      2. fabriquer les sons et les musiques en .ogg (numpy et ffmpeg nécessaires),
         car le navigateur ne les composerait pas assez vite ;
      3. lancer pygbag avec notre modèle de page (web/modele.html) ;
      4. copier le moteur (dossier --moteur, un clone de github.com/pygame-web/archives)
         en le réglant pour qu'il ne charge rien ailleurs que sur notre serveur ;
      5. compresser les gros fichiers (.gz servis tels quels par le serveur).

    Utilisation :
        python outils/construire_web.py --moteur CHEMIN/archives [--sortie build/web]

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 26/10/2026
"""

import argparse
import gzip
import json
import os
import shutil
import subprocess
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

VERSION_MOTEUR = "0.9"              # dossier du moteur dans pygame-web/archives
PYTHON_WEB = "cp312"
NOM = "neonbreaker"
CDN = f"/archives/{VERSION_MOTEUR}/"
DOSSIERS_CODE = ["moteur", "jeu", "ecrans", "reseau", "structures"]
A_COMPRESSER = (".wasm", ".data", ".js", ".py", ".json", ".html")   # pas .apk ni .whl : déjà des zip


def copier_code(destination):
    """But : copier le code et les ressources du jeu (sans sauvegarde ni sons générés)."""
    ignorer = shutil.ignore_patterns("__pycache__", "*.pyc", "sons", "sauvegarde.json*",
                                     "erreurs.log", "reseau.log*", "serveur.txt")
    for dossier in DOSSIERS_CODE + ["data"]:
        shutil.copytree(os.path.join(RACINE, dossier), os.path.join(destination, dossier),
                        ignore=ignorer)
    shutil.copy(os.path.join(RACINE, "main.py"), destination)
    os.makedirs(os.path.join(destination, "outils"))
    for nom in ("__init__.py", "banc_web.py"):          # banc d'essai (?banc)
        shutil.copy(os.path.join(RACINE, "outils", nom), os.path.join(destination, "outils"))


def fabriquer_sons(destination):
    """
    But : écrire tous les effets et les musiques en .ogg dans data/sons_web/.
    Entrée : destination (str) : dossier de travail du jeu.
    """
    import numpy as np
    from moteur import audio, musique

    dossier = os.path.join(destination, "data", "sons_web")
    os.makedirs(dossier, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporaire:
        a_convertir = []
        for nom, recette in audio.recette_sons().items():
            wav = os.path.join(temporaire, nom + ".wav")
            audio.ecrire_wav(wav, recette())
            a_convertir.append((wav, os.path.join(dossier, nom + ".ogg")))
        for nom in musique.PARTITIONS:
            wav = os.path.join(temporaire, "musique_" + nom + ".wav")
            musique.ecrire_wav(wav, musique.composer(nom, np))
            a_convertir.append((wav, os.path.join(dossier, "musique_" + nom + ".ogg")))
        for wav, ogg in a_convertir:
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", wav,
                            "-c:a", "libvorbis", "-q:a", "4", ogg], check=True)
    print(f"  {len(a_convertir)} sons en .ogg")


def lancer_pygbag(dossier_jeu):
    """But : construire la page et l'archive du jeu avec pygbag."""
    commande = [sys.executable, "-m", "pygbag", "--build", "--no_opt", "--app_name", NOM,
                "--title", "NEON BREAKER", "--ume_block", "1", "--cdn", CDN,
                "--template", os.path.join(RACINE, "web", "modele.html"),
                "--icon", os.path.join(RACINE, "web", "icone-192.png"), dossier_jeu]
    subprocess.run(commande, check=True, stdout=subprocess.DEVNULL)
    return os.path.join(dossier_jeu, "build", "web")


def copier_moteur(archives, sortie):
    """
    But : copier le moteur Python du navigateur et le paquet pygame, puis les régler pour
    tout charger depuis notre serveur (par défaut, ils vont sur pygame-web.github.io).
    Entrées : archives (str) : clone de pygame-web/archives ; sortie (str) : build/web.
    """
    source = os.path.join(archives, VERSION_MOTEUR)
    cible = os.path.join(sortie, "archives", VERSION_MOTEUR)
    garder = {"pythons.js", "cpythonrc.py", "browserfs.min.js", "empty.html", "empty.ogg",
              "vtx.js", "vt", f"cpython{PYTHON_WEB[2:]}", "favicon.png"}
    os.makedirs(cible)
    for nom in os.listdir(source):
        if nom in garder:
            chemin = os.path.join(source, nom)
            if os.path.isdir(chemin):
                shutil.copytree(chemin, os.path.join(cible, nom))
            else:
                shutil.copy(chemin, cible)

    # Le moteur cherche ses paquets sur pygame-web.github.io : on le renvoie vers /archives/repo/.
    rc = os.path.join(cible, "cpythonrc.py")
    with open(rc, encoding="utf-8") as fichier:
        texte = fichier.read()
    repere = "    del home\n"
    if repere not in texte:
        raise SystemExit("cpythonrc.py inattendu : impossible de régler le dépôt de paquets")
    texte = texte.replace(repere, repere + (
        "    # NEON BREAKER : paquets servis par le même site que le moteur\n"
        "    os.environ.setdefault('PYGPI', sys.executable.rsplit('/', 3)[0] + '/repo/')\n"), 1)
    with open(rc, "w", encoding="utf-8") as fichier:
        fichier.write(texte)

    depot_source = os.path.join(archives, "repo")
    depot = os.path.join(sortie, "archives", "repo")
    os.makedirs(os.path.join(depot, PYTHON_WEB))
    index_nom = f"index-090-{PYTHON_WEB}.json"
    with open(os.path.join(depot_source, index_nom), encoding="utf-8") as fichier:
        index = json.load(fichier)
    paquet = index["pygame.base"].replace("<abi>", PYTHON_WEB).replace(
        "<api>", "wasm32_bi_emscripten")
    index = {"-CDN-": "/archives/repo/", "pygame.base": index["pygame.base"]}
    with open(os.path.join(depot, index_nom), "w", encoding="utf-8") as fichier:
        json.dump(index, fichier)
    shutil.copy(os.path.join(depot_source, "repodata.json"), depot)
    shutil.copy(os.path.join(depot_source, paquet), os.path.join(depot, PYTHON_WEB))


def compresser(dossier):
    """But : écrire une copie .gz des gros fichiers (le serveur l'envoie aux navigateurs)."""
    total = brut = 0
    for racine, _, fichiers in os.walk(dossier):
        for nom in fichiers:
            if not nom.endswith(A_COMPRESSER):
                continue
            chemin = os.path.join(racine, nom)
            with open(chemin, "rb") as fichier:
                donnees = fichier.read()
            compresse = gzip.compress(donnees, compresslevel=9, mtime=0)
            with open(chemin + ".gz", "wb") as fichier:
                fichier.write(compresse)
            brut += len(donnees)
            total += len(compresse)
    print(f"  compression : {brut / 1e6:.1f} Mo -> {total / 1e6:.1f} Mo")


def main():
    analyseur = argparse.ArgumentParser(description="Construire la version navigateur")
    analyseur.add_argument("--moteur", required=True,
                           help="clone de github.com/pygame-web/archives")
    analyseur.add_argument("--sortie", default=os.path.join(RACINE, "build", "web"))
    arguments = analyseur.parse_args()

    sortie = os.path.abspath(arguments.sortie)
    if os.path.exists(sortie):
        shutil.rmtree(sortie)
    os.makedirs(sortie)
    with tempfile.TemporaryDirectory() as travail:
        dossier_jeu = os.path.join(travail, NOM)
        print("Copie du code...")
        copier_code(dossier_jeu)
        print("Sons et musiques...")
        fabriquer_sons(dossier_jeu)
        print("pygbag...")
        page = lancer_pygbag(dossier_jeu)
        os.makedirs(os.path.join(sortie, "jeu"))
        for nom in ("index.html", f"{NOM}.apk"):
            shutil.copy(os.path.join(page, nom), os.path.join(sortie, "jeu"))
    for nom in os.listdir(os.path.join(RACINE, "web")):
        if nom != "modele.html":
            shutil.copy(os.path.join(RACINE, "web", nom), os.path.join(sortie, "jeu"))
    print("Moteur Python du navigateur...")
    copier_moteur(arguments.moteur, sortie)
    compresser(sortie)
    print("Version web prête :", sortie)


if __name__ == "__main__":
    main()
