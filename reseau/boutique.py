# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Économie de la 2.0, partagée par le jeu et le serveur :
      - la monnaie (les NEONS) et les gains d'une partie ;
      - le catalogue des bannières (affichées au-dessus du pseudo) ;
      - la boutique : sélection tournante du jour et boîte mystère.
    Les skins premium sont dans reseau/profil.py (condition « boutique »).
    Le serveur est seul à créditer et débiter : le jeu ne fait qu'afficher.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 25/10/2026
"""

import random

from reseau.profil import SKINS

MONNAIE = "NEONS"

# --- Raretés et prix ------------------------------------------------------------------------

RARETES = ["commune", "rare", "epique", "legendaire"]
NOMS_RARETES = {"commune": "COMMUNE", "rare": "RARE", "epique": "EPIQUE",
                "legendaire": "LEGENDAIRE"}
COULEURS_RARETES = {"commune": (170, 190, 220), "rare": (60, 200, 255),
                    "epique": (200, 90, 255), "legendaire": (255, 200, 50)}
PRIX = {"banniere": {"commune": 120, "rare": 250, "epique": 450, "legendaire": 900},
        "skin": {"commune": 200, "rare": 350, "epique": 600, "legendaire": 1200}}
PRIX_BOITE = 220
POIDS_BOITE = {"commune": 50, "rare": 30, "epique": 15, "legendaire": 5}
REMBOURSEMENT_BOITE = 150            # boîte ouverte alors que tout est déjà possédé
REMISE_PROMO = 0.3                   # un objet de la sélection du jour à -30 %
TAILLE_SELECTION = 6

# --- Bannières ----------------------------------------------------------------------------
# motif : degrade, rayures, grille, etoiles, vagues, circuit, pixels, damier, flammes,
#         aurore, spectre, glitch ; icone : code de moteur/icones.py (ou None).
BANNIERES = [
    {"code": "aube", "nom": "AUBE", "rarete": "commune", "motif": "degrade",
     "couleurs": ((255, 60, 150), (255, 170, 60)), "icone": None},
    {"code": "ocean", "nom": "OCEAN", "rarete": "commune", "motif": "degrade",
     "couleurs": ((40, 80, 220), (60, 230, 255)), "icone": None},
    {"code": "menthe", "nom": "MENTHE", "rarete": "commune", "motif": "degrade",
     "couleurs": ((40, 200, 140), (170, 255, 220)), "icone": None},
    {"code": "lavande", "nom": "LAVANDE", "rarete": "commune", "motif": "degrade",
     "couleurs": ((120, 70, 220), (230, 160, 255)), "icone": None},
    {"code": "braise", "nom": "BRAISE", "rarete": "commune", "motif": "rayures",
     "couleurs": ((150, 20, 40), (255, 120, 40)), "icone": None},
    {"code": "zebre", "nom": "ZEBRE NEON", "rarete": "commune", "motif": "rayures",
     "couleurs": ((20, 20, 40), (60, 240, 255)), "icone": None},
    {"code": "grille", "nom": "HORIZON", "rarete": "rare", "motif": "grille",
     "couleurs": ((40, 10, 70), (255, 60, 200)), "icone": None},
    {"code": "nuit", "nom": "NUIT ETOILEE", "rarete": "rare", "motif": "etoiles",
     "couleurs": ((10, 10, 40), (200, 220, 255)), "icone": None},
    {"code": "vagues", "nom": "VAGUES", "rarete": "rare", "motif": "vagues",
     "couleurs": ((10, 40, 90), (60, 220, 255)), "icone": None},
    {"code": "circuit", "nom": "CIRCUIT", "rarete": "rare", "motif": "circuit",
     "couleurs": ((10, 40, 20), (90, 255, 120)), "icone": None},
    {"code": "pixels", "nom": "PIXELS", "rarete": "rare", "motif": "pixels",
     "couleurs": ((30, 20, 60), (255, 220, 60)), "icone": None},
    {"code": "arcade", "nom": "ARCADE", "rarete": "rare", "motif": "damier",
     "couleurs": ((255, 60, 140), (255, 230, 60)), "icone": None},
    {"code": "flammes", "nom": "FLAMMES", "rarete": "epique", "motif": "flammes",
     "couleurs": ((90, 10, 10), (255, 160, 40)), "icone": "feu"},
    {"code": "foudre", "nom": "FOUDRE", "rarete": "epique", "motif": "rayures",
     "couleurs": ((20, 20, 70), (120, 200, 255)), "icone": "onde"},
    {"code": "galaxie", "nom": "GALAXIE", "rarete": "epique", "motif": "etoiles",
     "couleurs": ((50, 10, 80), (255, 140, 255)), "icone": "multi"},
    {"code": "aurore", "nom": "AURORE", "rarete": "epique", "motif": "aurore",
     "couleurs": ((10, 30, 50), (90, 255, 180)), "icone": None},
    {"code": "supernova", "nom": "SUPERNOVA", "rarete": "legendaire", "motif": "spectre",
     "couleurs": ((30, 10, 60), (255, 255, 255)), "icone": "supernova"},
    {"code": "couronne", "nom": "COURONNE", "rarete": "legendaire", "motif": "degrade",
     "couleurs": ((120, 70, 10), (255, 220, 80)), "icone": "campagne"},
    {"code": "signal", "nom": "SIGNAL PERDU", "rarete": "legendaire", "motif": "glitch",
     "couleurs": ((15, 15, 30), (60, 255, 230)), "icone": None},
]
BANNIERES_PAR_CODE = {b["code"]: b for b in BANNIERES}


def skins_premium():
    """But : skins vendus en boutique (condition « boutique »). Sortie : (list de dict)."""
    return [s for s in SKINS if s["condition"] and s["condition"][0] == "boutique"]


def objet(code):
    """
    But : description d'un objet de boutique (bannière ou skin premium).
    Entrée : code (str). Sortie : (dict) {"code", "nom", "type", "rarete", "prix"} ou None.
    """
    if code in BANNIERES_PAR_CODE:
        b = BANNIERES_PAR_CODE[code]
        return {"code": code, "nom": b["nom"], "type": "banniere", "rarete": b["rarete"],
                "prix": PRIX["banniere"][b["rarete"]]}
    for skin in skins_premium():
        if skin["code"] == code:
            rarete = skin["condition"][1]
            return {"code": code, "nom": skin["nom"], "type": "skin", "rarete": rarete,
                    "prix": PRIX["skin"][rarete]}
    return None


def tous_les_objets():
    """But : tous les objets à gagner (bannières puis skins premium)."""
    return [objet(b["code"]) for b in BANNIERES] + [objet(s["code"]) for s in skins_premium()]


def selection_du_jour(jour):
    """
    But : sélection tournante de la boutique, la même pour tout le monde un
    jour donné : 2 skins et 4 bannières (hors légendaires, réservés à la
    boîte mystère), dont un objet en promotion.
    Entrée : jour (str « AAAA-MM-JJ »). Sortie : (list de dict) objets avec
    « prix » (prix payé) et « promo » (bool).
    """
    hasard = random.Random("boutique-" + str(jour))
    vendables = [o for o in tous_les_objets() if o["rarete"] != "legendaire"]
    skins = [o for o in vendables if o["type"] == "skin"]
    bannieres = [o for o in vendables if o["type"] == "banniere"]
    choix = hasard.sample(skins, min(2, len(skins)))
    choix += hasard.sample(bannieres, min(TAILLE_SELECTION - len(choix), len(bannieres)))
    promo = hasard.randrange(len(choix))
    resultat = []
    for i, o in enumerate(choix):
        o = dict(o, promo=(i == promo), prix_normal=o["prix"])
        if o["promo"]:
            o["prix"] = int(round(o["prix"] * (1 - REMISE_PROMO) / 10) * 10)
        resultat.append(o)
    return resultat


def tirer_boite(possedes, hasard=None):
    """
    But : contenu d'une boîte mystère : une rareté tirée au sort (pondérée),
    puis un objet pas encore possédé de cette rareté (sinon d'une autre).
    Entrées : possedes (ensemble de codes) ; hasard (random.Random ou None).
    Sortie : (dict) objet gagné, ou None si le joueur possède déjà tout.
    """
    hasard = hasard or random.SystemRandom()
    restants = [o for o in tous_les_objets() if o["code"] not in possedes]
    if not restants:
        return None
    raretes = [r for r in RARETES if any(o["rarete"] == r for o in restants)]
    rarete = hasard.choices(raretes, weights=[POIDS_BOITE[r] for r in raretes])[0]
    return hasard.choice([o for o in restants if o["rarete"] == rarete])


# --- Gains -----------------------------------------------------------------------------------

GAIN_NIVEAU = 10                  # niveau de campagne réussi pour la première fois
GAIN_BOSS = 50                    # boss vaincu pour la première fois (par mode)
GAIN_DEFI = 20                    # première partie du défi du jour...
GAIN_DEFI_SERIE = 5               # ... + 5 par jour de série (au plus +30)
GAIN_SEMAINE = 60                 # première partie du défi de la semaine
GAIN_VICTOIRE_EN_LIGNE = 15
GAIN_PARTIE_EN_LIGNE = 5
GAIN_SUCCES = 25
GAIN_RANG = 30
PARTICIPATION_MAX = 10            # par partie (≥ 45 s), selon le score
PARTICIPATION_JOUR = 60           # plafond quotidien de la participation
MODES_CAMPAGNE = ("campagne", "hardcore", "coop")


def niveaux_reussis(rapport):
    """
    But : clés « mode:indice » des niveaux de campagne terminés dans la partie.
    Entrée : rapport (dict). Sortie : (list de str).
    """
    mode = rapport.get("mode")
    if mode not in MODES_CAMPAGNE:
        return []
    depart = int(rapport.get("indice_depart", 0) or 0)
    finis = int(rapport.get("stats", {}).get("niveaux_finis", 0) or 0)
    return [f"{mode}:{i}" for i in range(depart, depart + max(0, min(finis, 60)))]


def gains_partie(rapport, cumul, jour, serie_defi=0):
    """
    But : NEONS gagnés pour une partie (le cumul est celui d'AVANT la partie,
    il est mis à jour ici avec ce qui ne rapporte qu'une fois).
    Entrées : rapport (dict) ; cumul (dict, modifié) ; jour (str « AAAA-MM-JJ »,
              jour du serveur) ; serie_defi (int) : série de défis du jour en
              comptant cette partie.
    Sortie : (list de (str, int)) détail des gains, ex. [("NIVEAU 3", 10)].
    """
    detail = []
    mode = rapport.get("mode")
    stats = rapport.get("stats", {})
    deja = set(cumul.get("niveaux_payes", []))
    for cle in niveaux_reussis(rapport):
        if cle not in deja:
            deja.add(cle)
            mode_niveau, indice = cle.split(":")
            gain = GAIN_NIVEAU * (2 if mode_niveau == "hardcore" else 1)
            detail.append((f"NIVEAU {int(indice) + 1}", gain))
    cumul["niveaux_payes"] = sorted(deja)
    boss_payes = set(cumul.get("boss_payes", []))
    for nom in stats.get("boss_vaincus", []):
        cle = f"{mode}:{nom}"
        if cle not in boss_payes:
            boss_payes.add(cle)
            detail.append((f"BOSS {str(nom).upper()}", GAIN_BOSS))
    cumul["boss_payes"] = sorted(boss_payes)

    if mode == "defi" and rapport.get("jour"):
        jours = set(cumul.get("defis_payes", []))
        cle = str(rapport["jour"])[:10]
        if cle not in jours:
            jours.add(cle)
            bonus = GAIN_DEFI_SERIE * max(0, min(6, serie_defi - 1))
            detail.append(("DEFI DU JOUR", GAIN_DEFI))
            if bonus:
                detail.append((f"SERIE x{serie_defi}", bonus))
        cumul["defis_payes"] = sorted(jours)[-60:]
    if mode == "semaine" and rapport.get("jour"):
        semaines = set(cumul.get("semaines_payees", []))
        cle = str(rapport["jour"])[:8]
        if cle not in semaines:
            semaines.add(cle)
            detail.append(("DEFI DE LA SEMAINE", GAIN_SEMAINE))
        cumul["semaines_payees"] = sorted(semaines)[-30:]

    if rapport.get("en_ligne") and mode in ("duel", "course", "coop"):
        detail.append(("PARTIE EN LIGNE", GAIN_PARTIE_EN_LIGNE))
        if mode in ("duel", "course") and rapport.get("gagnant") == rapport.get("numero"):
            detail.append(("VICTOIRE", GAIN_VICTOIRE_EN_LIGNE))

    if float(rapport.get("duree", 0) or 0) >= 45:
        jour_part, deja_part = cumul.get("participation", [None, 0])
        if jour_part != jour:
            deja_part = 0
        score = int(rapport.get("score_equipe", rapport.get("score", 0)) or 0)
        gain = min(PARTICIPATION_MAX, 2 + max(0, score) // 5000,
                   PARTICIPATION_JOUR - deja_part)
        if gain > 0:
            detail.append(("PARTIE JOUEE", gain))
            deja_part += gain
        cumul["participation"] = [jour, deja_part]
    return detail


def total(detail):
    """But : somme d'un détail de gains. Sortie : (int)."""
    return sum(montant for _, montant in detail)


def cadeau_bienvenue(boss_vaincus, nb_succes, niveau):
    """
    But : NEONS offerts aux joueurs qui existaient avant la 2.0, selon ce
    qu'ils avaient déjà accompli. Sortie : (int).
    """
    return 100 + GAIN_BOSS * len(boss_vaincus) + GAIN_SUCCES * nb_succes \
        + GAIN_RANG * max(0, niveau - 1)
