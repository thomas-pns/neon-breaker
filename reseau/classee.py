# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Parties classées (2.0), partagé par le jeu et le serveur : cote Elo,
    divisions (BRONZE à NEON), et règle d'appariement de la file d'attente.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 25/10/2026
"""

ELO_DEPART = 1000
PARTIES_PLACEMENT = 10          # les 10 premières parties comptent plus (K plus grand)
K_PLACEMENT, K_NORMAL = 40, 24
ECART_DEPART = 100              # écart de cote accepté dans la file au départ...
ECART_PAR_SECONDE = 25          # ... et qui s'élargit à chaque seconde d'attente

# (cote minimale, nom, couleur RVB), de la plus basse à la plus haute.
DIVISIONS = [
    (0, "BRONZE", (205, 127, 50)),
    (1100, "ARGENT", (200, 210, 230)),
    (1250, "OR", (255, 210, 60)),
    (1400, "PLATINE", (90, 240, 220)),
    (1550, "NEON", (255, 60, 200)),
]


def attendu(cote, adverse):
    """But : probabilité de victoire attendue (0..1) face à un adversaire."""
    return 1 / (1 + 10 ** ((adverse - cote) / 400))


def nouvelle_cote(cote, adverse, victoire, parties):
    """
    But : cote après une partie classée.
    Entrées : cote, adverse (int) ; victoire (bool) ; parties (int) : parties
              classées déjà jouées (placement si moins de 10).
    Sortie : (int) nouvelle cote (jamais sous 100).
    """
    k = K_PLACEMENT if parties < PARTIES_PLACEMENT else K_NORMAL
    return max(100, round(cote + k * ((1.0 if victoire else 0.0) - attendu(cote, adverse))))


def division(cote):
    """But : (nom, couleur, cote minimale, cote de la suivante ou None) d'une cote."""
    for i in range(len(DIVISIONS) - 1, -1, -1):
        minimum, nom, couleur = DIVISIONS[i]
        if cote >= minimum:
            suivante = DIVISIONS[i + 1][0] if i + 1 < len(DIVISIONS) else None
            return nom, couleur, minimum, suivante
    return DIVISIONS[0][1], DIVISIONS[0][2], 0, DIVISIONS[1][0]


def apparier(file, maintenant):
    """
    But : former des paires dans la file d'attente : les cotes les plus proches
    d'abord, avec un écart accepté qui grandit avec l'attente.
    Entrées : file (dict pseudo -> (cote, entree_le)) ; maintenant (float).
    Sortie : (list de (pseudo, pseudo)).
    """
    restants = sorted(file, key=lambda p: file[p][0])
    paires = []
    while len(restants) >= 2:
        meilleure = None
        for a, b in zip(restants, restants[1:]):
            ecart = abs(file[a][0] - file[b][0])
            attente = maintenant - max(file[a][1], file[b][1])
            if ecart <= ECART_DEPART + ECART_PAR_SECONDE * max(0, attente):
                if meilleure is None or ecart < meilleure[0]:
                    meilleure = (ecart, a, b)
        if meilleure is None:
            break
        _, a, b = meilleure
        paires.append((a, b))
        restants.remove(a)
        restants.remove(b)
    return paires
