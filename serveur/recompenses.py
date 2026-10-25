# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Récompenses versées par le serveur (2.1), vérifiées toutes les 10 minutes :
      - top 3 du défi du jour (50 / 30 / 20 NEONS), versé le lendemain ;
      - top 3 du défi de la semaine (150 / 100 / 50), versé la semaine suivante ;
      - fin de saison classée (chaque mois) : NEONS selon la meilleure division
        atteinte, bannières exclusives (OR, PLATINE, NEON), puis cote rapprochée
        de 1000.
    Chaque versement est noté (table recompenses) pour ne jamais payer deux fois,
    et un message prévient le joueur à sa prochaine connexion.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 25/10/2026
"""

import datetime
import logging

from reseau import boutique, classee
from reseau.series import id_semaine

journal = logging.getLogger("neon.recompenses")
PLACES = ["1ER", "2E", "3E"]


def _payer_top(base, periode, lignes, montants, libelle):
    for place, (ligne, montant) in enumerate(zip(lignes, montants)):
        joueur = base.joueur_par_pseudo(ligne["pseudo"])
        if joueur is None:
            continue
        base.crediter(joueur["id"], montant, f"{PLACES[place]} {libelle}")
        base.envoyer_message(joueur["id"], f"{PLACES[place]} {libelle} !", f"+{montant} NEONS")
    base.marquer_versee(periode)


def verser_defis(base, aujourd_hui):
    """But : payer les top 3 des défis terminés (7 derniers jours, 4 dernières semaines)."""
    for recul in range(1, 8):
        jour = (aujourd_hui - datetime.timedelta(days=recul)).isoformat()
        periode = f"jour:{jour}"
        if not base.periode_versee(periode):
            _payer_top(base, periode, base.classement_defi(jour, 3, "defi"), boutique.RECOMPENSES_JOUR,
                       f"DEFI DU {jour[8:10]}/{jour[5:7]}")
    for recul in range(1, 5):
        semaine = id_semaine(aujourd_hui - datetime.timedelta(weeks=recul))
        periode = f"semaine:{semaine}"
        if not base.periode_versee(periode):
            _payer_top(base, periode, base.classement_defi(semaine, 3, "semaine"),
                       boutique.RECOMPENSES_SEMAINE, f"SEMAINE {semaine.split('-W')[-1]}")


def cloturer_saison(base, ancienne):
    """But : récompenser la saison qui se termine puis rapprocher les cotes de 1000."""
    nom = "PRE-SAISON" if classee.numero_saison(ancienne) < 1 else \
        f"SAISON {classee.numero_saison(ancienne)}"
    for joueur in base.lire("SELECT id, saison_max FROM joueurs WHERE saison_max > 0"):
        division, _, _, _ = classee.division(joueur["saison_max"])
        montant = classee.RECOMPENSES_SAISON.get(division, 0)
        base.crediter(joueur["id"], montant, f"FIN {nom}")
        nouvelles = [code for code in classee.BANNIERES_SAISON.get(division, [])
                     if base.donner(joueur["id"], code, "saison")]
        texte = f"+{montant} NEONS" + ("  +BANNIERE" if nouvelles else "")
        base.envoyer_message(joueur["id"], f"FIN {nom} : {division}", texte)
    for joueur in base.lire("SELECT id, elo FROM joueurs WHERE classees > 0"):
        base.ecrire("UPDATE joueurs SET elo = ?, saison_max = 0 WHERE id = ?",
                    (classee.cote_apres_saison(joueur["elo"]), joueur["id"]))
    journal.info("%s clôturée", nom)


def verser_saison(base, aujourd_hui):
    """But : changer de saison au début de chaque mois (une seule fois)."""
    actuelle = classee.id_saison(aujourd_hui)
    precedente = base.valeur_periode("saison")
    if precedente is None:
        base.marquer_versee("saison", actuelle)          # première fois : rien à clôturer
    elif precedente != actuelle:
        cloturer_saison(base, precedente)
        base.marquer_versee("saison", actuelle)


def verser_tout(base, aujourd_hui):
    """But : toutes les récompenses dues (appelé au démarrage puis régulièrement)."""
    try:
        verser_defis(base, aujourd_hui)
        verser_saison(base, aujourd_hui)
    except Exception:                    # une récompense ratée ne doit jamais arrêter le serveur
        journal.exception("Erreur pendant le versement des récompenses")
