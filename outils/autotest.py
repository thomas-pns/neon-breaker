# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Visite automatique de tous les écrans et de tous les modes, pour
    vérifier qu'un exécutable fabriqué par PyInstaller fonctionne (aucun
    module ni fichier oublié). Lancé par main.py quand la variable
    d'environnement NEON_AUTOTEST vaut 1 ; quitte avec le code 0 si tout
    va bien, 1 sinon. GitHub Actions l'exécute sur Windows et macOS.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import time
import traceback


def lancer(app):
    """
    But : enchaîner les écrans en simulant quelques secondes de chacun.
    Entrée : app (Application). Sortie : (int) code de sortie.
    """
    from ecrans.titre import EcranTitre
    from ecrans.modes import EcranModes, fabrique_mode
    from ecrans.aide import EcranAide
    from ecrans.jouer import EcranJouer
    from ecrans.casier import EcranCasier
    from ecrans.menus import EcranReglages
    from ecrans.carte import EcranCarte
    from ecrans.nouveautes import EcranNouveautes
    from ecrans.scores import EcranScores
    from ecrans.partie import EcranPartie
    from ecrans.options import EcranOptions
    from ecrans.commandes import EcranCommandes
    from ecrans.pause import EcranPause
    from ecrans.en_ligne.connexion import EcranConnexion
    from ecrans.en_ligne.hub import EcranHub
    from ecrans.en_ligne.boutique import EcranBoutique
    from ecrans.en_ligne.salons import EcranSalons
    from ecrans.en_ligne.joueurs import EcranJoueurs, EcranProfil
    from ecrans.en_ligne.classements import EcranClassementsMondiaux
    from ecrans.en_ligne import partie as _partie  # noqa: F401  (module présent ?)
    from reseau import mise_a_jour as _maj  # noqa: F401
    import websockets  # noqa: F401
    import certifi  # noqa: F401

    def casier(categorie, indice):
        ecran = EcranCasier(app)
        ecran.categorie = categorie
        ecran.indice = min(indice, len(ecran.objets()) - 1)
        return ecran

    etapes = [
        ("titre", lambda: EcranTitre(app)),
        ("modes", lambda: EcranModes(app)),
        ("jouer en ligne", lambda: EcranJouer(app, "en_ligne")),
        ("jouer defis", lambda: EcranJouer(app, "defis")),
        ("casier", lambda: EcranCasier(app)),
        ("casier bannieres (fin de liste)", lambda: casier(1, 99)),
        ("casier couleur", lambda: casier(2, 5)),
        ("reglages", lambda: EcranReglages(app)),
        ("admin", lambda: __import__("ecrans.en_ligne.admin", fromlist=["EcranAdmin"]).EcranAdmin(app)),
        ("aide", lambda: EcranAide(app)),
        ("carte", lambda: EcranCarte(app, "campagne")),
        ("nouveautes", lambda: EcranNouveautes(app)),
        ("scores", lambda: EcranScores(app)),
        ("options", lambda: EcranOptions(app)),
        ("commandes", lambda: EcranCommandes(app)),
        ("connexion", lambda: EcranConnexion(app)),
        ("hub", lambda: EcranHub(app)),
        ("boutique", lambda: EcranBoutique(app)),
        ("salons", lambda: EcranSalons(app)),
        ("joueurs", lambda: EcranJoueurs(app)),
        ("profil", lambda: EcranProfil(app, "personne")),
        ("classements", lambda: EcranClassementsMondiaux(app)),
    ] + [(code, lambda c=code: EcranPartie(app, fabrique_mode(c)))
         for code in ("campagne", "arcade", "hardcore", "coop", "duel", "course", "defi", "semaine")] + [
        ("boss", lambda: EcranPartie(app, fabrique_mode("campagne", 11))),
    ]
    app.charger()
    debut = time.time()
    try:
        for nom, fabrique in etapes:
            app.remplacer(fabrique(), transition=False)
            for image in range(90):
                app.entrees.debut_image()
                if image % 30 == 10:
                    app.entrees.forcer("action", "solo")
                    app.entrees.forcer("action", "j1")
                app.regler_format()
                app._mettre_a_jour(1 / 60)
                app.regler_format()
                app._dessiner()
            print(f"AUTOTEST {nom} : OK")
        # Pause puis options par-dessus une partie, et musique chargée.
        partie = EcranPartie(app, fabrique_mode("arcade"))
        app.remplacer(partie, transition=False)
        app.empiler(EcranPause(app, partie))
        app.empiler(EcranOptions(app))
        for image in range(30):
            app.entrees.debut_image()
            app.regler_format()
            app._mettre_a_jour(1 / 60)
            app.regler_format()
            app._dessiner()
        if app.audio.actif and len(app.audio.musiques) < 6:
            raise RuntimeError(f"musiques manquantes : {sorted(app.audio.musiques)}")
        print(f"AUTOTEST pause + options : OK ({len(app.audio.musiques)} musiques)")
        # Au doigt (téléphone) : boutons à l'écran, toucher les pouvoirs, SUPERNOVA, PAUSE.
        app.entrees.tactile = True
        for code in ("campagne", "arcade", "duel"):
            app.remplacer(EcranPartie(app, fabrique_mode(code)), transition=False)
            for image in range(60):
                app.entrees.debut_image()
                if image == 20:
                    app.entrees.forcer("action", "solo")
                for action in ("pouvoir1", "overdrive") if image == 40 else ():
                    app.entrees.appuis_tactiles.add(action)
                app.regler_format()
                app._mettre_a_jour(1 / 60)
                app.regler_format()
                app._dessiner()
            actions = {action for _, action in app.entrees.boutons_dessines}
            if "pause" not in actions:
                raise RuntimeError(f"tactile {code} : pas de bouton PAUSE ({actions})")
        app.remplacer(EcranTitre(app), transition=False)
        app.entrees.appuis_tactiles.add("retour")
        for image in range(10):
            app.regler_format()
            app._mettre_a_jour(1 / 60)
            app.regler_format()
            app._dessiner()
            app.entrees.debut_image()
        app.entrees.tactile = False
        print("AUTOTEST tactile : OK")
    except Exception:
        traceback.print_exc()
        print("AUTOTEST : ECHEC")
        return 1
    print(f"AUTOTEST : TOUT VA BIEN ({time.time() - debut:.1f} s)")
    return 0
