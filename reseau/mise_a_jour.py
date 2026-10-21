# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Mise à jour automatique de l'exécutable.
      - Windows : le nouveau .exe est téléchargé à côté de l'ancien ; un
        petit script attend que le jeu se ferme, remplace le fichier et
        relance le jeu.
      - macOS : l'archive .zip de l'application est décompressée avec
        « ditto » (qui garde les droits d'exécution), puis un script
        remplace l'ancienne application et la relance.
    L'empreinte SHA-256 annoncée par le serveur est vérifiée avant tout
    remplacement. Lancé depuis le code source, le jeu ne se met pas à jour
    lui-même (on utilise git).

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import hashlib
import os
import platform
import subprocess
import sys
import tempfile
import urllib.request

from moteur import config
from moteur.version import VERSION, comparer_versions


def plateforme():
    """But : nom de la plateforme pour le serveur ("windows", "mac_arm", "mac_intel")."""
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "mac_arm" if platform.machine() == "arm64" else "mac_intel"
    return "linux"


def version_disponible(reponse):
    """
    But : informations sur la nouvelle version si elle est plus récente.
    Entrée : reponse (dict de /api/version ou None).
    Sortie : (dict ou None) {"version", "url", "sha256", "taille", "auto"}.
    """
    if not reponse:
        return None
    infos = reponse.get("plateformes", {}).get(plateforme())
    if not infos or comparer_versions(infos.get("version", "0"), VERSION) <= 0:
        return None
    return {**infos, "auto": config.EST_EXECUTABLE}


def telecharger(url, destination, empreinte_attendue, progression=None):
    """
    But : télécharger un fichier et vérifier son empreinte (bloquant).
    Entrées : url, destination (str) ; empreinte_attendue (str) ;
              progression (fonction(float) ou None).
    Sortie : aucune. Lève ValueError si l'empreinte ne correspond pas.
    """
    from reseau.client import contexte_ssl
    options = {"timeout": 30}
    if url.startswith("https://"):
        options["context"] = contexte_ssl()
    empreinte = hashlib.sha256()
    with urllib.request.urlopen(url, **options) as reponse, open(destination, "wb") as fichier:
        total = int(reponse.headers.get("Content-Length", 0)) or 1
        recu = 0
        while True:
            morceau = reponse.read(1 << 16)
            if not morceau:
                break
            fichier.write(morceau)
            empreinte.update(morceau)
            recu += len(morceau)
            if progression:
                progression(min(1.0, recu / total))
    if empreinte_attendue and empreinte.hexdigest() != empreinte_attendue:
        os.remove(destination)
        raise ValueError("Fichier corrompu (empreinte différente)")


def installer_windows(nouveau):
    """Remplace l'exécutable courant après sa fermeture, puis le relance."""
    actuel = sys.executable
    script = os.path.join(tempfile.gettempdir(), "neonbreaker_maj.bat")
    with open(script, "w", encoding="utf-8") as fichier:
        fichier.write(f'''@echo off
:attente
timeout /t 1 /nobreak >nul
move /y "{nouveau}" "{actuel}" >nul 2>&1 || goto attente
start "" "{actuel}"
del "%~f0"
''')
    drapeaux = 0x00000008 | 0x08000000          # DETACHED_PROCESS | CREATE_NO_WINDOW
    subprocess.Popen(["cmd", "/c", script], creationflags=drapeaux, close_fds=True)


def installer_mac(archive):
    """Remplace l'application .app après sa fermeture, puis la relance."""
    paquet = os.path.abspath(os.path.join(os.path.dirname(sys.executable), "..", ".."))
    if not paquet.endswith(".app"):
        raise RuntimeError("Application macOS introuvable")
    dossier = tempfile.mkdtemp(prefix="neonbreaker_")
    subprocess.run(["ditto", "-x", "-k", archive, dossier], check=True)
    nouvelles = [n for n in os.listdir(dossier) if n.endswith(".app")]
    if not nouvelles:
        raise RuntimeError("Archive invalide")
    nouveau = os.path.join(dossier, nouvelles[0])
    script = os.path.join(dossier, "maj.sh")
    with open(script, "w", encoding="utf-8") as fichier:
        fichier.write(f'''#!/bin/sh
while kill -0 {os.getpid()} 2>/dev/null; do sleep 0.5; done
rm -rf "{paquet}"
mv "{nouveau}" "{paquet}"
xattr -dr com.apple.quarantine "{paquet}" 2>/dev/null
open "{paquet}"
''')
    subprocess.Popen(["/bin/sh", script], start_new_session=True, close_fds=True)


def mettre_a_jour(adresse, infos, progression=None):
    """
    But : télécharger et préparer l'installation ; le jeu doit ensuite se
    fermer pour que le script remplace l'exécutable.
    Entrées : adresse (str) du serveur ; infos (dict de version_disponible) ;
              progression (fonction ou None).
    """
    url = adresse + infos["url"]
    if plateforme() == "windows":
        nouveau = sys.executable + ".nouveau"
        telecharger(url, nouveau, infos.get("sha256"), progression)
        installer_windows(nouveau)
    elif plateforme().startswith("mac"):
        archive = os.path.join(tempfile.gettempdir(), "NeonBreaker-maj.zip")
        telecharger(url, archive, infos.get("sha256"), progression)
        installer_mac(archive)
    else:
        raise RuntimeError("Mise à jour automatique non prise en charge")
