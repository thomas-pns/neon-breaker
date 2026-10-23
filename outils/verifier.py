# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Vérification complète du projet en une seule commande, identique sous
    Windows, macOS et Linux : tests unitaires puis autotest de tous les
    écrans, sans fenêtre ni son (pilotes SDL « dummy ») et avec un dossier
    de données temporaire (la vraie sauvegarde n'est jamais touchée).
    À lancer par les agents avant de rendre leur travail :

        python outils/verifier.py            (tout)
        python outils/verifier.py --rapide   (tests unitaires seulement)

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 23/10/2026
"""

import os
import subprocess
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def lancer(titre, commande, env):
    """
    But : exécuter une étape et afficher son résultat.
    Entrées : titre (str) ; commande (list) ; env (dict). Sortie : (bool) réussite.
    """
    print(f"\n=== {titre} ===", flush=True)
    resultat = subprocess.run(commande, cwd=RACINE, env=env)
    print(f"=== {titre} : {'OK' if resultat.returncode == 0 else 'ECHEC'} ===", flush=True)
    return resultat.returncode == 0


def main():
    """But : enchaîner les vérifications. Sortie : code de retour 0 si tout passe."""
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy",
               PYGAME_HIDE_SUPPORT_PROMPT="1",
               NEON_DONNEES=tempfile.mkdtemp(prefix="neon_verif_"))
    env.pop("NEON_SERVEUR", None)
    ok = lancer("TESTS UNITAIRES", [sys.executable, "-m", "unittest", "-q"], env)
    if ok and "--rapide" not in sys.argv:
        ok = lancer("AUTOTEST DES ECRANS", [sys.executable, "main.py"],
                    dict(env, NEON_AUTOTEST="1"))
    print("\nTOUT PASSE" if ok else "\nDES VERIFICATIONS ECHOUENT", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
