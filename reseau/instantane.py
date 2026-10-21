# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Traduire l'état d'une partie en « instantané » JSON (côté serveur) et
    appliquer cet instantané aux objets du jeu (côté client). Le client
    réutilise exactement les mêmes classes (modes, terrains, briques,
    raquettes, balles, boss) que le jeu local : il ne simule rien, il
    recopie l'état reçu puis le dessine avec le code habituel.

    Les briques ne sont envoyées que lorsqu'elles changent (signature).
    Entre deux instantanés (30 par seconde), le client prolonge les
    mouvements (vitesses) pour que l'affichage reste fluide.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import itertools

import pygame

from structures.liste import Liste
from jeu.balle import Balle
from jeu.boss import BOSS
from jeu.brique import code_type, creer_depuis_code
from jeu.capsule import Capsule
from jeu.projectiles import Laser, TirBoss
from jeu.terrain import Terrain

_compteur = itertools.count(1)
NOMS_BOSS = {classe: nom for nom, classe in BOSS.items()}


def nid(objet):
    """But : identifiant réseau stable d'un objet (attribué au premier appel)."""
    identifiant = getattr(objet, "nid", None)
    if identifiant is None:
        identifiant = next(_compteur)
        objet.nid = identifiant
    return identifiant


def couleur_vers_int(couleur):
    r, v, b = couleur[:3]
    return (int(r) << 16) | (int(v) << 8) | int(b)


def int_vers_couleur(valeur):
    return ((valeur >> 16) & 255, (valeur >> 8) & 255, valeur & 255)


def r1(valeur):
    """Arrondi au dixième (instantanés plus légers)."""
    return round(float(valeur), 1)


def en_tuples(valeur):
    """But : listes JSON -> tuples (couleurs, rectangles), récursivement."""
    if isinstance(valeur, list):
        return tuple(en_tuples(v) for v in valeur)
    return valeur


# =============================================================================
#  Côté serveur : capture
# =============================================================================

def signature_briques(terrain):
    """But : empreinte qui change dès qu'une brique change (hors glissement)."""
    total_vie = total_y = revelees = 0
    for brique in terrain.briques:
        total_vie += brique.vie
        total_y += round(brique.y)
        revelees += int(getattr(brique, "revelee", False))
    return (len(terrain.briques), total_vie, total_y, revelees)


def capturer_briques(terrain):
    briques = []
    for b in terrain.briques:
        entree = [nid(b), code_type(b), r1(b.x), r1(b.y), b.largeur, b.hauteur, b.vie,
                  b.vie_max, couleur_vers_int(b.couleur), int(getattr(b, "revelee", False))]
        if hasattr(b, "x_min"):
            entree += [r1(b.vitesse), r1(b.x_min), r1(b.x_max)]
        briques.append(entree)
    return briques


def capturer_boss(boss):
    if boss is None:
        return None
    return {"type": NOMS_BOSS.get(type(boss), "sunset"), "x": r1(boss.x), "y": r1(boss.y),
            "vie": boss.vie, "vie_max": boss.vie_max, "phase": boss.phase,
            "angle": round(getattr(boss, "angle", 0.0), 3), "flash": round(boss.flash, 2),
            "mort": round(boss.mort, 2), "temps": r1(boss.temps),
            "rayons": [[r1(x), round(t, 2), e] for x, t, e in getattr(boss, "rayons", [])]}


def capturer_terrain(terrain, signatures, forcer=False):
    """
    But : état d'un terrain ; les briques ne sont incluses que si elles ont
    changé depuis le dernier envoi (ou si forcer).
    Entrées : terrain ; signatures (dict id(terrain) -> signature, modifié) ;
              forcer (bool). Sortie : (dict).
    """
    donnees = {
        "rect": list(terrain.rect), "mur_haut": terrain.mur_haut,
        "bord": couleur_vers_int(terrain.couleur_bord), "chrono": r1(terrain.chrono),
        "temps": r1(terrain.temps), "regen": len(terrain.regenerations),
        "raquettes": [[r.joueur.numero if r.joueur else 0, r1(r.x), r1(r.y), r1(r.largeur),
                       r.sens, r1(r.vx), round(r.etourdie, 2), round(r.gelee, 2),
                       round(r.ecrasement, 2)] for r in terrain.raquettes],
        "balles": [[nid(b), r1(b.x), r1(b.y), r1(b.vx), r1(b.vy), b.rayon, int(b.collee),
                    b.proprietaire.numero if b.proprietaire else 0, round(b.feu, 2)]
                   for b in terrain.balles],
        "capsules": [[r1(c.x), r1(c.y), c.code, c.sens, round(c.temps, 2)]
                     for c in terrain.capsules],
        "lasers": [[r1(l.x), r1(l.y), l.sens, l.joueur.numero if l.joueur else 0]
                   for l in terrain.lasers],
        "tirs": [[r1(t.x), r1(t.y), r1(t.vx), r1(t.vy), t.rayon, couleur_vers_int(t.couleur)]
                 for t in terrain.tirs],
        "mobiles": [[nid(b), r1(b.x), r1(b.vitesse)] for b in terrain.briques
                    if hasattr(b, "x_min")],
        "boss": capturer_boss(terrain.boss),
    }
    signature = signature_briques(terrain)
    if forcer or signatures.get(id(terrain)) != signature:
        signatures[id(terrain)] = signature
        donnees["briques"] = capturer_briques(terrain)
    return donnees


def capturer_joueur(joueur):
    return {"numero": joueur.numero, "nom": joueur.nom, "score": joueur.score,
            "combo": joueur.combo, "multi": joueur.multiplicateur,
            "inventaire": list(joueur.inventaire), "selection": joueur.selection,
            "overdrive": round(joueur.overdrive, 3), "supernova": round(joueur.supernova, 2),
            "effets": {c: round(t, 2) for c, t in joueur.effets.items()},
            "bombe": joueur.bombe_armee, "aimant": joueur.aimant_prises,
            "filets": joueur.filets, "points": joueur.points_manche,
            "briques": joueur.stats["briques"], "meilleur_combo": joueur.stats["meilleur_combo"]}


def capturer(mode, fond, signatures, forcer=False):
    """
    But : instantané complet d'une partie.
    Entrées : mode (ModeDeJeu) ; fond (objet avec monde, progression,
              vitesse_cible) ; signatures (dict, modifié) ; forcer (bool).
    Sortie : (dict) prêt pour json.dumps.
    """
    donnees = {
        "etat": mode.etat, "minuteur": round(mode.minuteur, 2), "temps": r1(mode.temps),
        "message": mode.message, "couleur_message": couleur_vers_int(mode.couleur_message),
        "temps_message": round(mode.temps_message, 2),
        "fond": [getattr(fond, "monde", 1), round(getattr(fond, "progression", 0), 3),
                 round(getattr(fond, "vitesse_cible", 0.8), 2)],
        "joueurs": [capturer_joueur(j) for j in mode.joueurs],
        "terrains": [capturer_terrain(t, signatures, forcer) for t in mode.terrains],
    }
    for attribut in ("vies", "indice", "total_briques", "bilan_affiche", "manche", "vague",
                     "mur_initial", "avant_descente", "intervalle"):
        if hasattr(mode, attribut):
            donnees[attribut] = getattr(mode, attribut)
    if hasattr(mode, "bilan"):
        donnees["bilan"] = mode.bilan
    if hasattr(mode, "attente"):
        donnees["attente"] = {str(j.numero): round(t, 2) for j, t in mode.attente.items()}
    if hasattr(mode, "fleches"):
        donnees["fleches"] = [{**f, "couleur": couleur_vers_int(f["couleur"])}
                              for f in mode.fleches]
    return donnees


# =============================================================================
#  Côté client : application
# =============================================================================

def appliquer(mode, donnees, app, numero_local):
    """
    But : recopier un instantané dans les objets du mode client.
    Entrées : mode (ModeDeJeu créé localement) ; donnees (dict) ; app
              (Application) ; numero_local (int) : joueur de ce PC (sa
              raquette est pilotée localement et n'est pas écrasée).
    Sortie : aucune.
    """
    mode.etat = donnees["etat"]
    mode.minuteur = donnees["minuteur"]
    mode.temps = donnees["temps"]
    mode.message = donnees["message"]
    mode.temps_message = donnees["temps_message"]
    mode.couleur_message = int_vers_couleur(donnees["couleur_message"])
    monde, progression, vitesse = donnees["fond"]
    app.fond.changer_monde(monde)
    app.fond.progression = progression
    app.fond.vitesse_cible = vitesse

    par_numero = {j.numero: j for j in mode.joueurs}
    for etat_joueur in donnees["joueurs"]:
        joueur = par_numero.get(etat_joueur["numero"])
        if joueur is not None:
            appliquer_joueur(joueur, etat_joueur)

    for attribut in ("vies", "total_briques", "bilan_affiche", "manche", "vague",
                     "mur_initial", "avant_descente", "intervalle"):
        if attribut in donnees:
            setattr(mode, attribut, donnees[attribut])
    if "indice" in donnees and hasattr(mode, "niveaux") and mode.niveaux:
        if donnees["indice"] != getattr(mode, "indice", None):
            mode.indice = donnees["indice"]
            mode.niveau = mode.niveaux[min(mode.indice, len(mode.niveaux) - 1)]
    if "bilan" in donnees:
        mode.bilan = [tuple(ligne) for ligne in donnees["bilan"]]
    if "attente" in donnees:
        mode.attente = {par_numero[int(n)]: t for n, t in donnees["attente"].items()
                        if int(n) in par_numero}
    if "fleches" in donnees:
        mode.fleches = [{**f, "couleur": int_vers_couleur(f["couleur"])}
                        for f in donnees["fleches"]]

    terrains = donnees["terrains"]
    if len(mode.terrains) != len(terrains) or any(
            list(t.rect) != d["rect"] for t, d in zip(mode.terrains, terrains)):
        mode.terrains = [Terrain(pygame.Rect(d["rect"]), d["mur_haut"]) for d in terrains]
    for terrain, etat_terrain in zip(mode.terrains, terrains):
        appliquer_terrain(terrain, etat_terrain, par_numero, numero_local)


def appliquer_joueur(joueur, d):
    joueur.nom = d["nom"]
    joueur.score = d["score"]
    joueur.combo = d["combo"]
    joueur.multiplicateur = d["multi"]
    joueur.inventaire = list(d["inventaire"])
    joueur.selection = d["selection"]
    joueur.overdrive = d["overdrive"]
    joueur.supernova = d["supernova"]
    joueur.effets = dict(d["effets"])
    joueur.bombe_armee = d["bombe"]
    joueur.aimant_prises = d["aimant"]
    joueur.filets = d["filets"]
    joueur.points_manche = d["points"]
    joueur.stats["briques"] = d["briques"]
    joueur.stats["meilleur_combo"] = d["meilleur_combo"]


def appliquer_terrain(terrain, d, par_numero, numero_local):
    terrain.couleur_bord = int_vers_couleur(d["bord"])
    terrain.chrono = d["chrono"]
    terrain.temps = d["temps"]
    terrain.regenerations = [None] * d["regen"]

    # Raquettes : on recrée la liste si sa composition change.
    voulues = [(e[0], e[4]) for e in d["raquettes"]]
    actuelles = [(r.joueur.numero if r.joueur else 0, r.sens) for r in terrain.raquettes]
    if voulues != actuelles:
        terrain.raquettes = []
        for numero, sens in voulues:
            joueur = par_numero.get(numero)
            if joueur is not None:
                terrain.ajouter_raquette(joueur, sens)
    for raquette, e in zip(terrain.raquettes, d["raquettes"]):
        _, x, y, largeur, _, vx, etourdie, gelee, ecrasement = e
        raquette.y = y
        raquette.etourdie = etourdie
        raquette.gelee = gelee
        raquette.ecrasement = max(raquette.ecrasement, ecrasement)
        raquette.x_serveur = x
        if raquette.joueur is not None and raquette.joueur.numero == numero_local:
            continue                         # pilotée par ce PC (prédiction locale)
        raquette.largeur = largeur
        raquette.cible_reseau = (x, vx)

    # Briques.
    if "briques" in d:
        existantes = {b.nid: b for b in terrain.briques if getattr(b, "nid", None)}
        premiere = not existantes            # premier envoi : apparition en cascade
        nouvelles = Liste()
        ajoutees = []
        for e in d["briques"]:
            identifiant, code, x, y, l, h, vie, vie_max, couleur, revelee = e[:10]
            brique = existantes.get(identifiant)
            if brique is None:
                brique = creer_depuis_code(code, x, y, l, h, int_vers_couleur(couleur), vie_max)
                brique.nid = identifiant
                brique.vie_max = vie_max
                ajoutees.append(brique)
            elif vie < brique.vie:
                brique.flash = 1.0
                brique.secousse = 3.0
            brique.vie = vie
            brique.x, brique.y = x, y
            if hasattr(brique, "revelee"):
                brique.revelee = bool(revelee)
            if len(e) > 10:
                brique.vitesse, brique.x_min, brique.x_max = e[10], e[11], e[12]
            nouvelles.ajouter_fin(brique)
        terrain.briques = nouvelles
        terrain.preparer_briques(ajoutees, cascade=premiere)
        if not premiere:
            for brique in ajoutees:
                brique.apparition = 0.0
    mobiles = {e[0]: e for e in d["mobiles"]}
    if mobiles:
        for brique in terrain.briques:
            e = mobiles.get(getattr(brique, "nid", None))
            if e is not None:
                brique.x, brique.vitesse = e[1], e[2]

    # Balles (on garde les objets pour conserver leurs traînées).
    existantes = {getattr(b, "nid", None): b for b in terrain.balles}
    balles = Liste()
    for identifiant, x, y, vx, vy, rayon, collee, proprio, feu in d["balles"]:
        balle = existantes.get(identifiant)
        if balle is None:
            balle = Balle(x, y, rayon)
            balle.nid = identifiant
        balle.x, balle.y, balle.vx, balle.vy = x, y, vx, vy
        balle.x_serveur = x
        balle.collee = bool(collee)
        balle.proprietaire = par_numero.get(proprio)
        balle.feu = feu
        balles.ajouter_fin(balle)
    terrain.balles = balles

    terrain.capsules = Liste()
    for x, y, code, sens, temps in d["capsules"]:
        capsule = Capsule(x, y, code, sens)
        capsule.temps = temps
        terrain.capsules.ajouter_fin(capsule)
    terrain.lasers = Liste()
    for x, y, sens, numero in d["lasers"]:
        terrain.lasers.ajouter_fin(Laser(x, y, sens, par_numero.get(numero)))
    terrain.tirs = Liste()
    for x, y, vx, vy, rayon, couleur in d["tirs"]:
        terrain.tirs.ajouter_fin(TirBoss(x, y, vx, vy, rayon, int_vers_couleur(couleur)))

    boss = d["boss"]
    if boss is None:
        terrain.boss = None
    else:
        classe = BOSS.get(boss["type"])
        if terrain.boss is None or type(terrain.boss) is not classe:
            terrain.boss = classe(terrain)
        b = terrain.boss
        b.x, b.y, b.vie, b.vie_max, b.phase = boss["x"], boss["y"], boss["vie"], boss["vie_max"], boss["phase"]
        b.flash, b.mort, b.temps = boss["flash"], boss["mort"], boss["temps"]
        if hasattr(b, "angle"):
            b.angle = boss["angle"]
        if hasattr(b, "rayons"):
            b.rayons = [list(r) for r in boss["rayons"]]


def compenser_latence(mode, retard):
    """
    But : un instantané décrit le serveur il y a un demi-ping : on avance
    les objets mobiles de ce retard pour les montrer là où ils sont
    vraiment (la balle arrive ainsi sous la raquette au bon moment).
    Entrées : mode ; retard (float, secondes). Sortie : aucune.
    """
    if retard <= 0:
        return
    for terrain in mode.terrains:
        facteur_temps = 0.4 if terrain.chrono > 0 else 1.0
        for balle in terrain.balles:
            if not balle.collee:
                facteur = balle.facteur_vitesse() * facteur_temps
                balle.x += balle.vx * retard * facteur
                balle.y += balle.vy * retard * facteur
        for tir in terrain.tirs:
            tir.mettre_a_jour(retard * facteur_temps)
        for laser in terrain.lasers:
            laser.mettre_a_jour(retard)
        for capsule in terrain.capsules:
            capsule.y += 170 * capsule.sens * retard
        for raquette in terrain.raquettes:
            cible = getattr(raquette, "cible_reseau", None)
            if cible is not None:
                raquette.cible_reseau = (cible[0] + cible[1] * retard, cible[1])


def prolonger(mode, dt):
    """
    But : faire avancer l'affichage entre deux instantanés (animations des
    briques, chute des capsules, projectiles, balles, raquettes distantes).
    Entrées : mode ; dt (float). Sortie : aucune.
    """
    for terrain in mode.terrains:
        terrain.temps += dt
        for brique in terrain.briques:
            brique.mettre_a_jour(dt)
        for capsule in terrain.capsules:
            capsule.mettre_a_jour(dt)
        for laser in terrain.lasers:
            laser.mettre_a_jour(dt)
        for tir in terrain.tirs:
            tir.mettre_a_jour(dt)
        for balle in terrain.balles:
            if not balle.collee:
                facteur = balle.facteur_vitesse() * (0.4 if terrain.chrono > 0 else 1)
                balle.x += balle.vx * dt * facteur
                balle.y += balle.vy * dt * facteur
            balle.mettre_a_jour_visuel(dt)
        for raquette in terrain.raquettes:
            cible = getattr(raquette, "cible_reseau", None)
            if cible is not None:
                x, vx = cible
                raquette.x += (x - raquette.x) * min(1.0, dt * 18)
                raquette.vx = vx
            raquette.ecrasement = max(0.0, raquette.ecrasement - dt * 6)
        if terrain.boss is not None:
            terrain.boss.flash = max(0.0, terrain.boss.flash - dt * 5)
            terrain.boss.vie_affichee += (terrain.boss.vie - terrain.boss.vie_affichee) * min(1, dt * 6)


def rejouer_effets(journal, app, effets):
    """
    But : côté client, rejouer les effets reçus du serveur.
    Entrées : journal (list de [nom, args, kwargs]) ; app ; effets.
    """
    for nom, args, kwargs in journal:
        args = [en_tuples(a) for a in args]
        kwargs = {k: en_tuples(v) for k, v in kwargs.items()}
        if nom == "son":
            app.audio.jouer(*args)
        elif nom == "son_brique":
            app.audio.jouer_brique(*args)
        elif nom == "crt":
            app.crt.declencher_aberration(*args)
        elif nom == "transition":
            app.lancer_transition(lambda: None)
        elif nom == "debris_brique":
            effets.debris_brique(pygame.Rect(args[0]), *args[1:])
        elif nom == "geler":
            pass                               # le rythme est donné par le serveur
        elif nom == "ralentir":
            pass
        elif hasattr(effets, nom):
            getattr(effets, nom)(*args, **kwargs)
