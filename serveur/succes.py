# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Catalogue des succès et règles pour les débloquer. Les succès vivent
    uniquement sur le serveur : pour en ajouter un, on complète la liste
    SUCCES ci-dessous et on met à jour le conteneur, sans toucher au jeu
    des joueurs (le jeu affiche ce que le serveur lui envoie).

    Chaque condition reçoit :
      - rapport : résumé de la partie qui vient de se terminer ;
      - cumul : statistiques cumulées du joueur (déjà mises à jour).

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026

ToDo List:
    Succès à paliers (bronze, argent, or).
"""

# Codes de toutes les capsules et de tous les pouvoirs du jeu.
TOUTES_CAPSULES = {"elargir", "multi", "feu", "ralenti", "aimant", "filet", "vie",
                   "retrecir", "vitesse", "inversion", "brouillard", "glace", "fantome",
                   "laser", "bouclier", "onde", "bombe", "chrono", "guidage"}
TOUS_POUVOIRS = {"laser", "bouclier", "onde", "bombe", "chrono", "guidage"}


def _stat(rapport, cle, defaut=0):
    return rapport.get("stats", {}).get(cle, defaut)


def _adverse(rapport):
    """Points de l'adversaire (Duel, Course)."""
    points = rapport.get("points") or [0, 0]
    numero = rapport.get("numero", 1)
    return points[1] if numero == 1 else points[0]


def _gagne(rapport):
    return rapport.get("gagnant") == rapport.get("numero")


def _campagne_complete(rapport, modes=("campagne", "hardcore")):
    return (rapport.get("mode") in modes and rapport.get("victoire")
            and rapport.get("indice_depart", 0) == 0)


class Succes:
    """Attributs : code, nom, description, categorie, secret (bool), condition."""

    def __init__(self, code, nom, description, categorie, condition, secret=False):
        self.code = code
        self.nom = nom
        self.description = description
        self.categorie = categorie
        self.condition = condition
        self.secret = secret

    def en_dict(self):
        return {"code": self.code, "nom": self.nom, "description": self.description,
                "categorie": self.categorie, "secret": self.secret}


SUCCES = [
    Succes("premiere_brique", "PREMIER IMPACT", "Casser une brique", "debuts",
           lambda r, c: _stat(r, "briques") >= 1),
    Succes("premier_niveau", "EN ROUTE", "Finir un niveau de campagne", "debuts",
           lambda r, c: _stat(r, "niveaux_finis") >= 1),
    Succes("premiere_en_ligne", "CONNECTE", "Jouer une partie en ligne", "debuts",
           lambda r, c: bool(r.get("en_ligne"))),
    Succes("boss_sunset", "COUCHER DE SOLEIL", "Vaincre SUNSET", "campagne",
           lambda r, c: "sunset" in _stat(r, "boss_vaincus", [])),
    Succes("boss_gridlock", "DEBLOCAGE", "Vaincre GRIDLOCK", "campagne",
           lambda r, c: "gridlock" in _stat(r, "boss_vaincus", [])),
    Succes("boss_core", "COEUR BRISE", "Vaincre CORE", "campagne",
           lambda r, c: "core" in _stat(r, "boss_vaincus", [])),
    Succes("campagne", "LEGENDE NEON", "Finir la campagne depuis le niveau 1", "campagne",
           lambda r, c: _campagne_complete(r)),
    Succes("campagne_parfaite", "SANS FAUTE", "Finir la campagne sans perdre de vie",
           "campagne", lambda r, c: _campagne_complete(r) and _stat(r, "vies_perdues") == 0),
    Succes("combo_8", "x8", "Atteindre le multiplicateur x8", "habilete",
           lambda r, c: _stat(r, "meilleur_combo") >= 35),
    Succes("combo_50", "INARRETABLE", "Combo de 50 briques", "habilete",
           lambda r, c: _stat(r, "meilleur_combo") >= 50),
    Succes("supernova", "SUPERNOVA", "Declencher une SUPERNOVA", "habilete",
           lambda r, c: _stat(r, "supernovas") >= 1),
    Succes("bombe_10", "ARTIFICIER", "10 briques avec une seule bombe", "habilete",
           lambda r, c: _stat(r, "bombe_max") >= 10),
    Succes("arcade_30", "SURVIVANT", "Atteindre la vague 30 en Arcade", "modes",
           lambda r, c: r.get("mode") == "arcade" and r.get("vagues", 0) >= 30),
    Succes("arcade_drone", "CHASSEUR DE DRONES", "Vaincre un mini-boss DRONE", "modes",
           lambda r, c: "drone" in _stat(r, "boss_vaincus", [])),
    Succes("hardcore_monde", "HARDCORE", "Finir un monde en Hardcore", "modes",
           lambda r, c: r.get("mode") == "hardcore" and len(_stat(r, "boss_vaincus", [])) >= 1),
    Succes("duel_7_0", "ECRASANT", "Gagner un Duel 7-0", "modes",
           lambda r, c: r.get("mode") == "duel" and _gagne(r) and _adverse(r) == 0),
    Succes("course_parfaite", "FLECHE NEON", "Gagner une Course sans perdre de manche",
           "modes", lambda r, c: r.get("mode") == "course" and _gagne(r) and _adverse(r) == 0),
    Succes("coop_10", "DUO", "10 parties en Coop en ligne", "coop",
           lambda r, c: c.get("parties_par_mode", {}).get("coop", 0) >= 10),
    Succes("coop_boss", "FORCES COMBINEES", "Vaincre un boss en Coop", "coop",
           lambda r, c: r.get("mode") == "coop" and len(_stat(r, "boss_vaincus", [])) >= 1),
    Succes("coop_campagne", "INSEPARABLES", "Finir la campagne en Coop", "coop",
           lambda r, c: _campagne_complete(r, ("coop",))),
    Succes("collection_capsules", "COLLECTIONNEUR", "Attraper chaque type de capsule",
           "collection", lambda r, c: TOUTES_CAPSULES <= set(c.get("capsules_types", []))),
    Succes("tous_pouvoirs", "ARSENAL", "Utiliser chaque pouvoir", "collection",
           lambda r, c: TOUS_POUVOIRS <= set(c.get("pouvoirs_utilises", []))),
    Succes("briques_10000", "DEMOLISSEUR", "10 000 briques au total", "endurance",
           lambda r, c: c.get("briques", 0) >= 10000),
    Succes("parties_100", "ACCRO", "100 parties jouees", "endurance",
           lambda r, c: c.get("parties", 0) >= 100),
    Succes("defi_1", "DEFI RELEVE", "Jouer un defi du jour", "defi",
           lambda r, c: r.get("mode") == "defi"),
    Succes("defi_7", "HABITUE", "Jouer le defi 7 jours differents", "defi",
           lambda r, c: len(c.get("jours_defi", [])) >= 7),
    Succes("defi_vague_20", "MUR DU JOUR", "Atteindre la vague 20 dans un defi", "defi",
           lambda r, c: r.get("mode") == "defi" and r.get("vagues", 0) >= 20),
    Succes("secret_malus", "MASOCHISTE", "Finir un niveau en ayant attrape 5 malus",
           "secret", lambda r, c: bool(_stat(r, "niveau_5_malus")), secret=True),
]
PAR_CODE = {s.code: s for s in SUCCES}


def mettre_a_jour_cumul(cumul, rapport):
    """
    But : ajouter une partie aux statistiques cumulées d'un joueur.
    Entrées : cumul (dict, modifié) ; rapport (dict). Sortie : (dict) cumul.
    """
    stats = rapport.get("stats", {})
    mode = rapport.get("mode", "?")
    cumul["parties"] = cumul.get("parties", 0) + 1
    cumul["briques"] = cumul.get("briques", 0) + int(stats.get("briques", 0))
    cumul["temps"] = round(cumul.get("temps", 0) + float(rapport.get("duree", 0)), 1)
    cumul["supernovas"] = cumul.get("supernovas", 0) + int(stats.get("supernovas", 0))
    cumul["meilleur_combo"] = max(cumul.get("meilleur_combo", 0),
                                  int(stats.get("meilleur_combo", 0)))
    for cle in ("capsules_types", "pouvoirs_utilises"):
        cumul[cle] = sorted(set(cumul.get(cle, [])) | set(stats.get(cle, [])))
    parties = cumul.setdefault("parties_par_mode", {})
    parties[mode] = parties.get(mode, 0) + 1
    if rapport.get("victoire") or _gagne(rapport):
        victoires = cumul.setdefault("victoires", {})
        victoires[mode] = victoires.get(mode, 0) + 1
    if mode == "defi" and rapport.get("jour"):
        cumul["jours_defi"] = sorted(set(cumul.get("jours_defi", [])) | {str(rapport["jour"])[:10]})
    boss = cumul.setdefault("boss_vaincus", {})
    for nom in stats.get("boss_vaincus", []):
        boss[nom] = boss.get(nom, 0) + 1
    return cumul


def evaluer(rapport, cumul, deja):
    """
    But : succès nouvellement débloqués par cette partie.
    Entrées : rapport, cumul (dict) ; deja (set de codes déjà obtenus).
    Sortie : (list de str) codes nouveaux.
    """
    nouveaux = []
    for succes in SUCCES:
        if succes.code in deja:
            continue
        try:
            if succes.condition(rapport, cumul):
                nouveaux.append(succes.code)
        except (TypeError, ValueError, KeyError):
            continue                     # rapport incomplet : on ignore
    return nouveaux


def xp_partie(rapport):
    """But : XP gagnée pour une partie. Sortie : (int)."""
    return int(20 + min(2000, max(0, rapport.get("score", 0)) / 50))


from reseau.profil import niveau_pour, xp_pour_niveau  # noqa: E402,F401  (partagés avec le jeu)
