# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Envoyer un exécutable fabriqué au serveur du NAS, par morceaux de
    900 Ko (le proxy inversé de DSM limite la taille des requêtes). Le
    serveur vérifie l'empreinte SHA-256 et publie la version : les jeux
    des joueurs proposeront la mise à jour au prochain lancement.

    Utilisation (GitHub Actions) :
        python outils/envoyer_build.py FICHIER PLATEFORME VERSION
    avec les variables d'environnement NEON_SERVEUR_URL et
    NEON_JETON_DEPLOIEMENT.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import hashlib
import os
import sys
import time
import urllib.error
import urllib.request

TAILLE_MORCEAU = 900 * 1024


def envoyer(chemin, plateforme, version, adresse, jeton):
    with open(chemin, "rb") as fichier:
        contenu = fichier.read()
    empreinte = hashlib.sha256(contenu).hexdigest()
    morceaux = [contenu[i:i + TAILLE_MORCEAU] for i in range(0, len(contenu), TAILLE_MORCEAU)]
    print(f"{chemin} : {len(contenu) / 1e6:.1f} Mo, {len(morceaux)} morceaux, sha256 {empreinte[:12]}...")
    for index, morceau in enumerate(morceaux):
        url = (f"{adresse.rstrip('/')}/api/builds/{plateforme}/{version}/{index}"
               f"?total={len(morceaux)}&sha256={empreinte}")
        for essai in range(5):
            requete = urllib.request.Request(url, data=morceau, method="POST", headers={
                "X-Jeton-Deploiement": jeton, "Content-Type": "application/octet-stream",
                "User-Agent": "NeonBreaker-CI"})
            try:
                with urllib.request.urlopen(requete, timeout=60) as reponse:
                    retour = reponse.read().decode("utf-8")
                break
            except urllib.error.HTTPError as erreur:
                detail = erreur.read().decode("utf-8", "replace")
                if erreur.code in (400, 403, 413):
                    sys.exit(f"Refusé ({erreur.code}) : {detail}")
                print(f"  morceau {index} : erreur {erreur.code}, nouvel essai")
            except (urllib.error.URLError, OSError) as erreur:
                print(f"  morceau {index} : {erreur}, nouvel essai")
            time.sleep(2 * (essai + 1))
        else:
            sys.exit(f"Échec de l'envoi du morceau {index}")
    print("Publié :", retour)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    adresse = os.environ.get("NEON_SERVEUR_URL", "")
    jeton = os.environ.get("NEON_JETON_DEPLOIEMENT", "")
    if not adresse or not jeton:
        sys.exit("NEON_SERVEUR_URL et NEON_JETON_DEPLOIEMENT doivent être définis.")
    envoyer(sys.argv[1], sys.argv[2], sys.argv[3].lstrip("v"), adresse, jeton)
