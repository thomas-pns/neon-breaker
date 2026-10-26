# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Pont entre le jeu et le navigateur, pour la version web (pygbag) :
    stockage local (sauvegarde), requêtes HTTP et WebSocket.

    Le navigateur n'a pas de fils d'exécution. Les requêtes et le WebSocket
    sont donc confiés au JavaScript de la page (objet window.neon, défini
    dans web/modele.html) ; le jeu relève les réponses à chaque image.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 26/10/2026
"""

import json

from moteur import config


def _fenetre():
    """But : objet window du navigateur (None hors du navigateur)."""
    if not config.EST_WEB:
        return None
    import platform
    return platform.window


def _neon():
    fenetre = _fenetre()
    return None if fenetre is None else fenetre.neon


# --- Stockage local ---------------------------------------------------------------------------

def lire(cle):
    """But : texte rangé dans le stockage du navigateur (None si absent)."""
    try:
        valeur = _fenetre().localStorage.getItem(cle)
    except Exception:
        return None
    return None if valeur is None else str(valeur)


def ecrire(cle, texte):
    """But : ranger un texte dans le stockage du navigateur. Sortie : (bool) succès."""
    try:
        _fenetre().localStorage.setItem(cle, texte)
        return True
    except Exception:
        return False


# --- Adresse du site ---------------------------------------------------------------------------

def origine():
    """But : adresse du site qui sert le jeu (ex. https://neon.exemple.fr), "" si inconnue."""
    try:
        origine = str(_fenetre().location.origin)
    except Exception:
        return ""
    return origine if origine.startswith("http") else ""


def demarre():
    """But : le jeu tourne : retirer l'écran CHARGEMENT de la page."""
    try:
        _neon().parti()
    except Exception:
        pass


def telephone():
    """But : est-ce un téléphone (écran tactile, petit) ? Il a alors le format vertical."""
    try:
        return bool(_neon().telephone())
    except Exception:
        return False


def proportion():
    """But : hauteur / largeur de la page (téléphone en portrait : environ 2,1). 0 si inconnue."""
    try:
        return float(_neon().proportion())
    except Exception:
        return 0.0


def marges(largeur_image):
    """
    But : zones sûres de l'écran (encoche, barre d'accueil de l'iPhone), converties en
    pixels de l'image du jeu. Entrée : largeur_image (int). Sortie : (haut, bas).
    """
    try:
        valeurs = json.loads(str(_neon().marges()))
        echelle = largeur_image / max(1.0, float(valeurs.get("largeur", 0)) or largeur_image)
        return int(valeurs.get("haut", 0) * echelle), int(valeurs.get("bas", 0) * echelle)
    except Exception:
        return 0, 0


def parametre(nom):
    """But : l'adresse de la page contient-elle ?nom (ex. ?profil) ? Sortie : (bool)."""
    try:
        return nom in str(_fenetre().location.search)
    except Exception:
        return False


def journal(texte):
    """But : écrire dans la console du navigateur (outils de développement)."""
    try:
        _fenetre().console.log(str(texte))
    except Exception:
        print(texte)


def demander_texte(titre, valeur=""):
    """
    But : faire taper un texte au clavier du téléphone (fenêtre du navigateur).
    Sortie : (str ou None si annulé).
    """
    try:
        reponse = _fenetre().prompt(titre, valeur)
    except Exception:
        return None
    return None if reponse is None else str(reponse)


def recharger():
    """But : recharger la page (nouvelle version du jeu)."""
    try:
        _fenetre().location.reload()
    except Exception:
        pass


# --- Requêtes HTTP -----------------------------------------------------------------------------

def requete(methode, url, corps=None, jeton=""):
    """
    But : lancer une requête (fetch) sans attendre.
    Sortie : (int) numéro de la requête, à retrouver dans reponses().
    """
    return int(_neon().requete(methode, url, json.dumps(corps) if corps is not None else "",
                               jeton or ""))


def reponses():
    """
    But : requêtes terminées depuis le dernier appel.
    Sortie : (list de (numero, code, texte)) ; code 0 si le serveur est injoignable.
    """
    texte = str(_neon().reponses())
    return [(int(n), int(code), str(corps)) for n, code, corps in json.loads(texte)]


# --- WebSocket ---------------------------------------------------------------------------------

def ws_ouvrir(url):
    _neon().ws_ouvrir(url)


def ws_envoyer(texte):
    _neon().ws_envoyer(texte)


def ws_fermer():
    _neon().ws_fermer()


def ws_etat():
    """But : "connexion", "ouvert", "ferme" ou "erreur", et le message d'erreur."""
    return str(_neon().ws_etat), str(_neon().ws_erreur)


def ws_messages():
    """But : textes reçus depuis le dernier appel (list de str)."""
    return json.loads(str(_neon().ws_messages()))


# --- Outil de mesure (?profil) -------------------------------------------------------------------

def profiler(fonction, nombre=25):
    """
    But : (outil) exécuter fonction() et renvoyer les fonctions les plus coûteuses
    (temps propre), y compris celles de pygame. Le Python du navigateur n'a ni
    cProfile ni profile : on suit les appels avec sys.setprofile.
    Sortie : (str) tableau à afficher.
    """
    import sys
    import time
    pile = []
    propre = {}
    appels = {}

    def nom_de(cadre, evenement, argument):
        if evenement.startswith("c_"):
            qualifie = getattr(argument, "__qualname__", getattr(argument, "__name__", "?"))
            appelant = cadre.f_code
            return f"{appelant.co_filename.rsplit('/', 1)[-1]}:{appelant.co_name} > {qualifie}"
        code = cadre.f_code
        return f"{code.co_filename.rsplit('/', 1)[-1]}:{code.co_name}"

    def suivi(cadre, evenement, argument):
        maintenant = time.perf_counter()
        if evenement in ("call", "c_call"):
            if pile:
                pile[-1][2] += maintenant - pile[-1][1]
            pile.append([nom_de(cadre, evenement, argument), maintenant, 0.0])
        elif pile:
            nom, debut, cumul = pile.pop()
            propre[nom] = propre.get(nom, 0.0) + cumul + maintenant - debut
            appels[nom] = appels.get(nom, 0) + 1
            if pile:
                pile[-1][1] = maintenant

    sys.setprofile(suivi)
    try:
        fonction()
    finally:
        sys.setprofile(None)
    total = sum(propre.values()) or 1
    lignes = [f"{'temps propre':>12} {'%':>5} {'appels':>8}  fonction"]
    for nom, valeur in sorted(propre.items(), key=lambda e: -e[1])[:nombre]:
        lignes.append(f"{valeur * 1000:10.1f}ms {valeur / total * 100:5.1f} {appels[nom]:8d}  {nom}")
    return "\n".join(lignes)
