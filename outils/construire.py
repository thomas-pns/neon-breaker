# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Fabriquer l'exécutable du jeu avec PyInstaller (utilisé par GitHub
    Actions, mais lançable à la main) :
      - Windows : dist/NeonBreaker.exe (un seul fichier) ;
      - macOS   : dist/NeonBreaker.app, puis dist/NeonBreaker-mac.zip.
    La version (étiquette Git vX.Y.Z) et l'adresse du serveur sont
    injectées au moment de la fabrication : elles ne sont pas dans le code.

    Utilisation :
        pip install pyinstaller pillow -r requirements.txt
        python outils/construire.py --version 1.2.0 --serveur https://neon.exemple.synology.me

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import argparse
import os
import re
import subprocess
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    analyseur = argparse.ArgumentParser()
    analyseur.add_argument("--version", required=True, help="X.Y.Z")
    analyseur.add_argument("--serveur", default="", help="adresse https du serveur")
    arguments = analyseur.parse_args()
    version = arguments.version.lstrip("v")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        sys.exit(f"Version invalide : {version}")

    # 1. Version dans le code (copie de travail de la fabrication seulement).
    chemin_version = os.path.join(RACINE, "moteur", "version.py")
    with open(chemin_version, encoding="utf-8") as fichier:
        texte = fichier.read()
    texte = re.sub(r'^VERSION = ".*"$', f'VERSION = "{version}"', texte, flags=re.M)
    with open(chemin_version, "w", encoding="utf-8") as fichier:
        fichier.write(texte)

    # 2. Adresse du serveur, lue par moteur/version.py dans l'exécutable.
    with open(os.path.join(RACINE, "data", "serveur.txt"), "w", encoding="utf-8") as fichier:
        fichier.write(arguments.serveur.strip())

    # 3. PyInstaller.
    separateur = ";" if sys.platform == "win32" else ":"
    donnees = [("data/niveaux", "data/niveaux"), ("data/fond.png", "data"),
               ("data/icone.png", "data"), ("data/serveur.txt", "data")]
    commande = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
                "--name", "NeonBreaker", "--icon", os.path.join("outils", "icone.png"),
                "--collect-submodules", "websockets", "--collect-submodules", "jeu",
                "--collect-submodules", "ecrans", "--exclude-module", "serveur",
                "--exclude-module", "tests", "--exclude-module", "tkinter",
                "--hidden-import", "outils.autotest", "--collect-submodules", "reseau"]
    for source, destination in donnees:
        commande += ["--add-data", f"{source}{separateur}{destination}"]
    if sys.platform == "darwin":
        commande += ["--osx-bundle-identifier", "fr.neonbreaker.jeu"]
    else:
        commande += ["--onefile"]
    commande.append("main.py")
    print(" ".join(commande))
    subprocess.run(commande, cwd=RACINE, check=True)

    # 4. macOS : archive .zip qui garde les droits (ditto).
    if sys.platform == "darwin":
        subprocess.run(["ditto", "-c", "-k", "--keepParent", "dist/NeonBreaker.app",
                        "dist/NeonBreaker-mac.zip"], cwd=RACINE, check=True)
        print("Fabriqué : dist/NeonBreaker-mac.zip")
    else:
        print("Fabriqué : dist/NeonBreaker.exe")


if __name__ == "__main__":
    main()
