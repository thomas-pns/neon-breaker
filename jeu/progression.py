# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Progression du joueur gardée sur son compte, pour la retrouver sur tous ses appareils
    (PC, Mac, téléphone) : niveaux débloqués, étoiles, records, top 10, défis joués (séries),
    bulles d'aide déjà vues.

    Deux appareils peuvent jouer chacun de leur côté : on ne remplace jamais une
    progression par l'autre, on les FUSIONNE en gardant le meilleur de chaque côté
    (niveau le plus loin, toutes les étoiles, meilleur score, tous les défis joués...).
    Le même code sert au jeu et au serveur.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 27/10/2026
"""

import json

CLES = ("progression", "etoiles", "meilleurs", "classements", "defis_joues", "defi", "semaine",
        "bulles_vues")
TAILLE_MAX = 64 * 1024              # octets (JSON) : bien plus que nécessaire


def _entier(valeur):
    try:
        return max(0, int(valeur))
    except (TypeError, ValueError):
        return 0


def _dict(valeur):
    return valeur if isinstance(valeur, dict) else {}


def _liste(valeur):
    return valeur if isinstance(valeur, list) else []


def extraire(donnees):
    """
    But : la partie de la sauvegarde qui suit le compte.
    Entrée : donnees (dict) : sauvegarde du jeu. Sortie : (dict) progression nettoyée.
    """
    return nettoyer({cle: donnees.get(cle) for cle in CLES if cle in donnees})


def nettoyer(brut):
    """
    But : ne garder que des valeurs du bon type (données venues du réseau).
    Entrée : brut (dict ou autre). Sortie : (dict).
    """
    brut = _dict(brut)
    propre = {}
    propre["progression"] = {str(k)[:20]: _entier(v) for k, v in _dict(brut.get("progression")).items()}
    propre["etoiles"] = {
        str(mode)[:20]: {str(_entier(i)): _entier(m) & 7 for i, m in _dict(niveaux).items()}
        for mode, niveaux in _dict(brut.get("etoiles")).items()}
    propre["meilleurs"] = {str(k)[:20]: _entier(v) for k, v in _dict(brut.get("meilleurs")).items()}
    propre["classements"] = {}
    for mode, top in _dict(brut.get("classements")).items():
        lignes = [{"nom": str(e.get("nom", ""))[:3], "score": _entier(e.get("score"))}
                  for e in _liste(top) if isinstance(e, dict)]
        propre["classements"][str(mode)[:20]] = lignes[:10]
    joues = _dict(brut.get("defis_joues"))
    propre["defis_joues"] = {p: [str(j)[:10] for j in _liste(joues.get(p))][-400:]
                             for p in ("jour", "semaine") if p in joues}
    for cle in ("defi", "semaine"):
        defi = _dict(brut.get(cle))
        if defi.get("jour"):
            propre[cle] = {"jour": str(defi["jour"])[:10], "record": _entier(defi.get("record"))}
    propre["bulles_vues"] = [str(b)[:40] for b in _liste(brut.get("bulles_vues"))][:200]
    return propre


def fusionner(a, b):
    """
    But : réunir deux progressions en gardant le meilleur de chacune.
    Entrées : a, b (dict, déjà nettoyés ou non). Sortie : (dict) progression fusionnée.
    """
    a, b = nettoyer(a), nettoyer(b)
    fusion = {}
    fusion["progression"] = {k: max(a["progression"].get(k, 0), b["progression"].get(k, 0))
                             for k in {**a["progression"], **b["progression"]}}
    fusion["etoiles"] = {}
    for mode in {**a["etoiles"], **b["etoiles"]}:
        na, nb = a["etoiles"].get(mode, {}), b["etoiles"].get(mode, {})
        fusion["etoiles"][mode] = {i: na.get(i, 0) | nb.get(i, 0) for i in {**na, **nb}}
    fusion["meilleurs"] = {k: max(a["meilleurs"].get(k, 0), b["meilleurs"].get(k, 0))
                           for k in {**a["meilleurs"], **b["meilleurs"]}}
    fusion["classements"] = {}
    for mode in {**a["classements"], **b["classements"]}:
        # Top 10 : les lignes des deux appareils, sans compter deux fois la même partie.
        vues, top = set(), []
        for ligne in sorted(a["classements"].get(mode, []) + b["classements"].get(mode, []),
                            key=lambda e: -e["score"]):
            cle = (ligne["nom"], ligne["score"])
            if cle not in vues:
                vues.add(cle)
                top.append(ligne)
        fusion["classements"][mode] = top[:10]
    fusion["defis_joues"] = {}
    for periode in {**a["defis_joues"], **b["defis_joues"]}:
        jours = set(a["defis_joues"].get(periode, [])) | set(b["defis_joues"].get(periode, []))
        fusion["defis_joues"][periode] = sorted(jours)[-400:]
    for cle in ("defi", "semaine"):
        da, db = a.get(cle), b.get(cle)
        if da and db and da["jour"] == db["jour"]:
            fusion[cle] = {"jour": da["jour"], "record": max(da["record"], db["record"])}
        elif da or db:
            fusion[cle] = max((d for d in (da, db) if d), key=lambda d: d["jour"])
    fusion["bulles_vues"] = sorted(set(a["bulles_vues"]) | set(b["bulles_vues"]))[:200]
    return fusion


def appliquer(donnees, progression):
    """
    But : mettre une progression (fusionnée) dans la sauvegarde du jeu.
    Entrées : donnees (dict) : sauvegarde, modifiée sur place ; progression (dict).
    Sortie : (bool) True si quelque chose a changé.
    """
    avant = empreinte(extraire(donnees))
    for cle, valeur in fusionner(extraire(donnees), progression).items():
        donnees[cle] = valeur
    return empreinte(extraire(donnees)) != avant


def empreinte(progression):
    """But : texte stable d'une progression (pour savoir si elle a changé)."""
    return json.dumps(progression, sort_keys=True, separators=(",", ":"))
