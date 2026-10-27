# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Commandes d'administration, à lancer dans le terminal du conteneur
    (Container Manager > Conteneur > neon-serveur > Terminal > Créer > bash) :

      python -m serveur.admin lister
      python -m serveur.admin reset-mdp PSEUDO        (donne un mot de passe provisoire)
      python -m serveur.admin bannir PSEUDO
      python -m serveur.admin debannir PSEUDO
      python -m serveur.admin supprimer PSEUDO        (efface le compte et ses parties)

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import datetime
import os
import secrets
import sys

from serveur import securite
from serveur.base import Base


def changer_utilisateur():
    """
    Dans le conteneur, le terminal de Container Manager ouvre une session
    administrateur : on passe à l'utilisateur du serveur (PUID/PGID) pour ne
    pas rendre la base illisible par le serveur.
    """
    if hasattr(os, "geteuid") and os.geteuid() == 0 and os.environ.get("PUID"):
        os.setgid(int(os.environ.get("PGID", "100")))
        os.setuid(int(os.environ["PUID"]))


def main(arguments):
    changer_utilisateur()
    base = Base()
    if not arguments or arguments[0] in ("-h", "--help", "aide"):
        print(__doc__)
        return 0
    commande = arguments[0]
    if commande == "lister":
        for joueur in base.liste_joueurs(tous=True):
            vu = datetime.datetime.fromtimestamp(joueur["vu_le"]).strftime("%d/%m/%Y %H:%M")
            print(f"{joueur['pseudo']:<14} niveau {joueur['niveau']:<3} xp {joueur['xp']:<7} "
                  f"succes {joueur['succes']:<3} vu le {vu}")
        return 0
    if len(arguments) < 2:
        print("Il manque le pseudo.")
        return 1
    joueur = base.joueur_par_pseudo(arguments[1])
    if joueur is None:
        print(f"Joueur « {arguments[1]} » introuvable.")
        return 1
    if commande == "reset-mdp":
        provisoire = arguments[2] if len(arguments) > 2 else secrets.token_urlsafe(6)
        base.changer_mdp(joueur["id"], securite.hacher_mdp(provisoire))
        base.supprimer_sessions_joueur(joueur["id"])
        print(f"Nouveau mot de passe de {joueur['pseudo']} : {provisoire}")
    elif commande == "bannir":
        base.bannir(joueur["id"], True)
        base.supprimer_sessions_joueur(joueur["id"])
        print(f"{joueur['pseudo']} est banni.")
    elif commande == "debannir":
        base.bannir(joueur["id"], False)
        print(f"{joueur['pseudo']} n'est plus banni.")
    elif commande == "supprimer":
        base.ecrire("DELETE FROM joueurs WHERE id = ?", (joueur["id"],))
        print(f"Compte {joueur['pseudo']} supprimé.")
    else:
        print(f"Commande inconnue : {commande}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
