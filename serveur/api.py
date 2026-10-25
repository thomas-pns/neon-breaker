# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Application web du serveur (FastAPI) :
      POST /api/inscription, /api/connexion, /api/deconnexion
      GET  /api/moi                 PUT /api/moi/couleur, /api/moi/skin, /api/moi/banniere
      GET  /api/boutique            POST /api/boutique/acheter, /api/boutique/boite
      POST /api/parties             (scores des parties solo, en file d'attente)
      GET  /api/classements/{mode}  GET /api/joueurs   GET /api/joueurs/{pseudo}
      GET  /api/succes              GET /api/version   GET /api/sante
      POST /api/builds/{plateforme}/{version}/{morceau}   (exécutables envoyés par GitHub Actions)
      GET  /telechargements/{plateforme}        GET /  (page de téléchargement)
      WS   /ws                      (parties en ligne, voir salons.py)

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import hashlib
import hmac
import html
import json
import os
import re

from fastapi import FastAPI, Header, HTTPException, Request, WebSocket
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from moteur.version import PROTOCOLE, comparer_versions
from serveur import config, securite
from reseau import boutique
from serveur.base import Base, MODES_SCORE, MODES_VICTOIRES, aujourd_hui
from serveur.salons import Gestionnaire
from serveur.succes import SUCCES, niveau_pour

PLATEFORMES = {"windows": "exe", "mac_arm": "zip", "mac_intel": "zip"}
MODES_SOLO = ("campagne", "arcade", "hardcore", "defi", "semaine")


MORCEAUX_ATTENDUS = {}          # fichier partiel -> numéro du prochain morceau

app = FastAPI(title="NEON BREAKER", docs_url=None, redoc_url=None)
base = Base()
gestionnaire = Gestionnaire(base)
limiteur = securite.Limiteur(config.TENTATIVES_PAR_MINUTE)


class Identifiants(BaseModel):
    pseudo: str
    mdp: str


class Couleur(BaseModel):
    couleur: str


class Skin(BaseModel):
    skin: str


class EnvoiParties(BaseModel):
    rapports: list


class Achat(BaseModel):
    code: str


class Banniere(BaseModel):
    banniere: str


# --- Outils -----------------------------------------------------------------------

def adresse_ip(requete):
    """Adresse du client (derrière le proxy inversé de DSM)."""
    transmise = requete.headers.get("x-forwarded-for", "")
    if transmise:
        return transmise.split(",")[0].strip()
    return requete.client.host if requete.client else "?"


def joueur_connecte(autorisation):
    """But : joueur correspondant à l'en-tête « Authorization: Bearer <jeton> »."""
    if not autorisation or not autorisation.lower().startswith("bearer "):
        raise HTTPException(401, "Connexion requise")
    joueur = base.joueur_par_session(securite.empreinte_jeton(autorisation[7:].strip()))
    if joueur is None:
        raise HTTPException(401, "Session expirée")
    return joueur


def presentation(joueur):
    return {"pseudo": joueur["pseudo"], "couleur": joueur["couleur"], "xp": joueur["xp"],
            "niveau": niveau_pour(joueur["xp"]), "skin": joueur["skin"],
            "skins": base.skins_de(joueur), "neons": joueur["neons"],
            "banniere": joueur["banniere"], "bannieres": base.bannieres_de(joueur["id"]),
            "elo": joueur["elo"], "classees": joueur["classees"]}


def ouvrir_session(joueur):
    jeton = securite.nouveau_jeton()
    base.creer_session(joueur["id"], securite.empreinte_jeton(jeton))
    return {"jeton": jeton, **presentation(joueur)}


# --- Comptes -------------------------------------------------------------------------

@app.post("/api/inscription")
def inscription(identifiants: Identifiants, requete: Request):
    if not limiteur.autoriser(adresse_ip(requete)):
        raise HTTPException(429, "Trop de tentatives, attendez une minute")
    pseudo = identifiants.pseudo.strip()
    erreur = securite.erreur_pseudo(pseudo) or securite.erreur_mdp(identifiants.mdp)
    if erreur:
        raise HTTPException(400, erreur)
    joueur_id = base.creer_joueur(pseudo, securite.hacher_mdp(identifiants.mdp))
    if joueur_id is None:
        raise HTTPException(409, "Ce pseudo est déjà pris")
    return ouvrir_session(base.joueur_par_id(joueur_id))


@app.post("/api/connexion")
def connexion(identifiants: Identifiants, requete: Request):
    if not limiteur.autoriser(adresse_ip(requete)):
        raise HTTPException(429, "Trop de tentatives, attendez une minute")
    joueur = base.joueur_par_pseudo(identifiants.pseudo.strip())
    if joueur is None or not securite.verifier_mdp(identifiants.mdp, joueur["mdp"]):
        raise HTTPException(401, "Pseudo ou mot de passe incorrect")
    if joueur["banni"]:
        raise HTTPException(403, "Compte suspendu")
    return ouvrir_session(joueur)


@app.post("/api/deconnexion")
def deconnexion(authorization: str = Header(default="")):
    if authorization.lower().startswith("bearer "):
        base.supprimer_session(securite.empreinte_jeton(authorization[7:].strip()))
    return {"ok": True}


@app.get("/api/moi")
def moi(authorization: str = Header(default="")):
    joueur = joueur_connecte(authorization)
    base.toucher(joueur["id"])
    return presentation(joueur)


@app.put("/api/moi/couleur")
def changer_couleur(choix: Couleur, authorization: str = Header(default="")):
    joueur = joueur_connecte(authorization)
    if choix.couleur not in config.COULEURS:
        raise HTTPException(400, "Couleur inconnue")
    base.changer_couleur(joueur["id"], choix.couleur)
    return {"ok": True, "couleur": choix.couleur}


@app.put("/api/moi/skin")
def changer_skin(choix: Skin, authorization: str = Header(default="")):
    joueur = joueur_connecte(authorization)
    if choix.skin not in base.skins_de(joueur):
        raise HTTPException(400, "Skin verrouille")
    base.changer_skin(joueur["id"], choix.skin)
    connexion = gestionnaire.connexions.get(joueur["pseudo"])
    if connexion is not None:
        connexion.skin = choix.skin
    return {"ok": True, "skin": choix.skin}


@app.put("/api/moi/banniere")
def changer_banniere(choix: Banniere, authorization: str = Header(default="")):
    joueur = joueur_connecte(authorization)
    if choix.banniere and choix.banniere not in base.bannieres_de(joueur["id"]):
        raise HTTPException(400, "Banniere non possedee")
    base.changer_banniere(joueur["id"], choix.banniere)
    connexion = gestionnaire.connexions.get(joueur["pseudo"])
    if connexion is not None:
        connexion.banniere = choix.banniere
    return {"ok": True, "banniere": choix.banniere}


# --- Boutique (2.0) -----------------------------------------------------------------------

@app.get("/api/boutique")
def voir_boutique(authorization: str = Header(default="")):
    """Sélection du jour (la même pour tous), avec ce que le joueur possède déjà."""
    joueur = joueur_connecte(authorization)
    possedes = base.possessions_de(joueur["id"])
    selection = [dict(o, possede=o["code"] in possedes)
                 for o in boutique.selection_du_jour(aujourd_hui().isoformat())]
    return {"jour": aujourd_hui().isoformat(), "selection": selection,
            "prix_boite": boutique.PRIX_BOITE, "neons": joueur["neons"],
            "possedes": sorted(possedes), "total_objets": len(boutique.tous_les_objets())}


@app.post("/api/boutique/acheter")
def acheter(achat: Achat, authorization: str = Header(default="")):
    joueur = joueur_connecte(authorization)
    offre = next((o for o in boutique.selection_du_jour(aujourd_hui().isoformat())
                  if o["code"] == achat.code), None)
    if offre is None:
        raise HTTPException(400, "Objet pas en vente aujourd'hui")
    erreur = base.acheter(joueur["id"], offre["code"], offre["prix"])
    if erreur:
        raise HTTPException(400, erreur)
    return {"ok": True, "objet": offre, **presentation(base.joueur_par_id(joueur["id"]))}


@app.post("/api/boutique/boite")
def boite_mystere(authorization: str = Header(default="")):
    joueur = joueur_connecte(authorization)
    resultat = base.ouvrir_boite(joueur["id"])
    if "erreur" in resultat:
        raise HTTPException(400, resultat["erreur"])
    return {"ok": True, "objet": resultat["objet"], **presentation(base.joueur_par_id(joueur["id"]))}


# --- Parties, classements, profils ------------------------------------------------------

@app.post("/api/parties")
def envoyer_parties(envoi: EnvoiParties, authorization: str = Header(default="")):
    """Scores des parties solo (jouées connecté ou hors ligne) : on fait confiance au jeu."""
    joueur = joueur_connecte(authorization)
    resultats = []
    for rapport in envoi.rapports[:50]:
        if not isinstance(rapport, dict) or rapport.get("mode") not in MODES_SOLO:
            resultats.append({"refuse": True})
            continue
        resultats.append(base.enregistrer_partie(joueur["id"], rapport, en_ligne=False))
    return {"resultats": resultats, **presentation(base.joueur_par_id(joueur["id"]))}


@app.get("/api/classements/{mode}")
def classement(mode: str):
    if mode not in MODES_SCORE + MODES_VICTOIRES + ("classe",):
        raise HTTPException(404, "Mode inconnu")
    return {"mode": mode, "type": "classe" if mode == "classe" else
            "victoires" if mode in MODES_VICTOIRES else "score",
            "lignes": base.classement(mode)}


@app.get("/api/defi/{jour}")
def defi(jour: str):
    """Classement du défi d'un jour (AAAA-MM-JJ)."""
    if len(jour) != 10 or not jour.replace("-", "").isdigit():
        raise HTTPException(400, "Date invalide")
    return {"mode": "defi", "type": "score", "jour": jour, "lignes": base.classement_defi(jour)}


@app.get("/api/semaine/{semaine}")
def defi_semaine(semaine: str):
    """Classement du défi d'une semaine (AAAA-Www)."""
    from reseau.series import lundi_de
    if lundi_de(semaine) is None:
        raise HTTPException(400, "Semaine invalide")
    return {"mode": "semaine", "type": "score", "jour": semaine,
            "lignes": base.classement_defi(semaine, mode="semaine")}


@app.get("/api/fantome/{mode}/{jour}")
def fantome(mode: str, jour: str):
    """Fantôme du meilleur joueur d'un défi (2.0) : sa raquette et son score à chaque instant."""
    if mode not in ("defi", "semaine") or not re.fullmatch(r"\d{4}-(\d{2}-\d{2}|W\d{2})", jour):
        raise HTTPException(400, "Defi inconnu")
    meilleur = base.meilleur_fantome(mode, jour)
    if meilleur is None:
        raise HTTPException(404, "Pas encore de fantome")
    return meilleur


@app.get("/api/series")
def series():
    """Séries en cours du défi du jour (jours d'affilée), record en second critère."""
    return {"mode": "series", "type": "series", "lignes": base.classement_series(aujourd_hui())}


@app.get("/api/joueurs")
def joueurs():
    en_ligne = set(gestionnaire.connexions)
    return {"joueurs": [{**j, "en_ligne": j["pseudo"] in en_ligne} for j in base.liste_joueurs()]}


@app.get("/api/joueurs/{pseudo}")
def profil(pseudo: str):
    donnees = base.profil(pseudo)
    if donnees is None:
        raise HTTPException(404, "Joueur introuvable")
    donnees["en_ligne"] = donnees["pseudo"] in gestionnaire.connexions
    joueur = base.joueur_par_pseudo(pseudo)
    donnees["series"] = base.series_de(joueur["id"], aujourd_hui())
    return donnees


@app.get("/api/succes")
def liste_succes():
    return {"succes": [s.en_dict() for s in SUCCES]}


@app.get("/api/sante")
def sante():
    return {"ok": True, "joueurs_connectes": len(gestionnaire.connexions),
            "parties": len(gestionnaire.salons)}


# --- Versions et téléchargements ---------------------------------------------------------

def lire_versions():
    try:
        with open(os.path.join(config.DOSSIER_BUILDS, "versions.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


@app.get("/api/version")
def version():
    plateformes = {}
    for plateforme, infos in lire_versions().items():
        plateformes[plateforme] = {**infos, "url": f"/telechargements/{plateforme}"}
    return {"protocole": PROTOCOLE, "plateformes": plateformes}


@app.post("/api/builds/{plateforme}/{numero}/{index}")
async def recevoir_morceau(plateforme: str, numero: str, index: int, total: int, sha256: str,
                           requete: Request, x_jeton_deploiement: str = Header(default="")):
    """
    GitHub Actions envoie chaque exécutable en morceaux (moins de 1 Mo, pour
    passer le proxy inversé de DSM). Au dernier morceau, le fichier est
    vérifié (SHA-256) puis publié.
    """
    if not config.JETON_DEPLOIEMENT or not hmac.compare_digest(
            x_jeton_deploiement, config.JETON_DEPLOIEMENT):
        raise HTTPException(403, "Jeton de déploiement invalide")
    if plateforme not in PLATEFORMES or not re.fullmatch(r"\d+\.\d+\.\d+", numero):
        raise HTTPException(400, "Plateforme ou version invalide")
    if not (0 <= index < total <= 2000) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise HTTPException(400, "Morceau invalide")
    os.makedirs(config.DOSSIER_BUILDS, exist_ok=True)
    nom = f"NeonBreaker-{numero}-{plateforme}.{PLATEFORMES[plateforme]}"
    chemin = os.path.join(config.DOSSIER_BUILDS, nom)
    partiel = chemin + ".part"
    corps = await requete.body()
    if len(corps) > 2 * 1024 * 1024:
        raise HTTPException(413, "Morceau trop gros")
    if index == 0 and os.path.exists(partiel):
        os.remove(partiel)
    taille_actuelle = os.path.getsize(partiel) if os.path.exists(partiel) else 0
    attendu = MORCEAUX_ATTENDUS.get(partiel, 0)
    if index != attendu:
        raise HTTPException(409, f"Morceau {attendu} attendu")
    with open(partiel, "ab") as fichier:
        fichier.write(corps)
    MORCEAUX_ATTENDUS[partiel] = index + 1
    if index < total - 1:
        return {"ok": True, "recu": index, "taille": taille_actuelle + len(corps)}

    MORCEAUX_ATTENDUS.pop(partiel, None)
    empreinte = hashlib.sha256()
    with open(partiel, "rb") as fichier:
        for bloc in iter(lambda: fichier.read(1 << 20), b""):
            empreinte.update(bloc)
    if empreinte.hexdigest() != sha256:
        os.remove(partiel)
        raise HTTPException(400, "Empreinte SHA-256 incorrecte : fichier abîmé pendant l'envoi")
    os.replace(partiel, chemin)
    taille = os.path.getsize(chemin)
    versions = lire_versions()
    ancienne = versions.get(plateforme, {})
    if not ancienne or comparer_versions(numero, ancienne.get("version", "0.0.0")) >= 0:
        versions[plateforme] = {"version": numero, "fichier": nom, "taille": taille,
                                "sha256": sha256}
        with open(os.path.join(config.DOSSIER_BUILDS, "versions.json"), "w", encoding="utf-8") as f:
            json.dump(versions, f, indent=2)
        # On ne garde que les 2 dernières versions de chaque plateforme.
        anciens = sorted((f for f in os.listdir(config.DOSSIER_BUILDS)
                          if f.endswith(f"-{plateforme}.{PLATEFORMES[plateforme]}") and f != nom),
                         key=lambda f: os.path.getmtime(os.path.join(config.DOSSIER_BUILDS, f)))
        for vieux in anciens[:-1]:
            os.remove(os.path.join(config.DOSSIER_BUILDS, vieux))
    return {"ok": True, "publie": nom, "taille": taille}


@app.get("/telechargements/{plateforme}")
def telecharger(plateforme: str):
    infos = lire_versions().get(plateforme)
    if infos is None:
        raise HTTPException(404, "Pas encore de version pour cette plateforme")
    return FileResponse(os.path.join(config.DOSSIER_BUILDS, infos["fichier"]),
                        filename=infos["fichier"], media_type="application/octet-stream")


@app.get("/", response_class=HTMLResponse)
def accueil():
    """Petite page néon pour que les amis téléchargent le jeu."""
    noms = {"windows": "WINDOWS (.EXE)", "mac_arm": "MAC PUCE APPLE (M1, M2...)",
            "mac_intel": "MAC INTEL"}
    liens = "".join(
        f'<a href="/telechargements/{p}">{noms[p]}<span>v{html.escape(i["version"])}</span></a>'
        for p, i in lire_versions().items() if p in noms) or "<p>Aucune version publiee.</p>"
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>NEON BREAKER</title>
<style>body{{margin:0;min-height:100vh;background:linear-gradient(#0a021e,#3c0e6e 60%,#ff2ba0);
color:#fff;font-family:monospace;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:24px;padding:16px}}
h1{{font-size:clamp(32px,8vw,72px);color:#00e5ff;text-shadow:0 0 18px #00e5ff,4px 4px 0 #ff2bd6;margin:0}}
a{{display:flex;justify-content:space-between;gap:24px;min-width:min(420px,90vw);padding:16px 20px;border:2px solid #ffb000;
border-radius:10px;color:#ffb000;text-decoration:none;font-size:18px;background:#12002bcc;box-shadow:0 0 14px #ffb00088}}
a:hover{{background:#ffb000;color:#12002b}} p{{max-width:560px;text-align:center;line-height:1.5;color:#e6d6ff}}</style></head>
<body><h1>NEON BREAKER</h1>{liens}
<p>Windows : si un message bleu « Windows a protege votre ordinateur » apparait, cliquez sur
<b>Informations complementaires</b> puis <b>Executer quand meme</b>.<br>
Mac : dezippez, glissez l'application dans Applications, puis <b>clic droit &gt; Ouvrir</b> la premiere fois.</p>
</body></html>"""


# --- WebSocket ----------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket(socket: WebSocket):
    await gestionnaire.accueillir(socket)
