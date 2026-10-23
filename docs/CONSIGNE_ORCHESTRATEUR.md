# Consigne pour le Claude Code orchestrateur — NEON BREAKER

Tu reprends le projet NEON BREAKER sans connaître son historique. Ce document suffit pour
démarrer. Le **protocole de délégation** (comment appeler les agents ChatGPT Codex `codex1` et
`codex2`, via Buzz ou en ligne de commande) est décrit dans le `CLAUDE.md` du dépôt. **Il prime
sur ce document en cas de désaccord.**

Le propriétaire est Thomas (étudiant CPE 3A). Il écrit en français, souvent à la voix, et joue
avec un petit groupe d'amis. Réponds-lui en français, simplement et sans jargon. Il veut des
résultats testables sur son PC Windows.

---

## 1. Ton rôle

- **Toi (Claude)** : architecture, découpage en tâches, rédaction des consignes pour Codex,
  relecture de chaque diff, intégration, tests, passe finale sur le rendu visuel, et toute
  partie sensible (réseau temps réel, base de données, déploiement, sécurité, mise à jour
  automatique).
- **Codex (`codex1`, `codex2`)** : écriture de code sur des tâches bien bornées, avec des
  critères d'acceptation écrits par toi.
- Objectif : économiser les crédits Claude **sans baisser la qualité**. Ne délègue pas une
  tâche que tu ne sais pas spécifier en moins d'une page. Relis toujours tout avant
  d'intégrer.

## 2. Le projet en bref

Casse-brique **Pygame (pygame-ce 2.5.8)**, style synthwave néon, avec un jeu en ligne.

- Rendu interne 1280×720 mis à l'échelle, physique à pas fixe de 120 Hz (sous-pas), filtre CRT,
  police bitmap 5×7 maison (`moteur/police_pixel.py` : majuscules, chiffres, un peu de
  ponctuation et ■ □ |).
- Modes : Campagne (12 niveaux, 3 mondes, boss SUNSET / GRIDLOCK / CORE), Arcade (mini-boss DRONE
  toutes les 10 vagues), Hardcore, Défi du jour (Arcade à graine fixe par date), Coop, Duel,
  Course.
- Bonus, malus, pouvoirs (inventaire de 3 places), jauge OVERDRIVE puis SUPERNOVA.
- Musiques composées au premier lancement avec numpy (`moteur/musique.py`), sons générés
  (`moteur/audio.py`), menu OPTIONS.
- En ligne :
  - comptes (pseudo + mot de passe) ;
  - parties Coop, Duel et Course à 2, **simulées par le serveur**, qui envoie un instantané
    30 fois par seconde ;
  - classements, profils, 28 succès, XP et niveau de joueur, 9 skins de raquette.
- Serveur : FastAPI + uvicorn + websockets + SQLite (WAL), dans un conteneur Docker sur le NAS
  Synology de Thomas (DS220+, 2 Go de RAM), derrière le proxy inversé de DSM (HTTPS 443).
- Exécutables : PyInstaller (Windows en un seul fichier ; macOS `.app` zippée, Apple et Intel),
  **mise à jour automatique** depuis le NAS, avec vérification SHA-256.

### Arborescence

```
main.py              point d'entrée (NEON_AUTOTEST=1 : visite automatique de tous les écrans)
moteur/              config, application (pile d'écrans), rendu, police, fond, effets, audio,
                     musique, entrées (scancodes), sauvegarde, version (VERSION, PROTOCOLE)
jeu/                 balle, raquette (skins), briques, capsules, projectiles, joueur, pouvoirs,
                     boss, niveaux, terrain (physique + file d'événements)
jeu/modes/           base, campagne (+ hardcore, coop), arcade, defi, duel, course
ecrans/              titre, modes, niveaux, partie, hud, pause, options, aide, scores, saisie,
                     fin, mise_a_jour
ecrans/en_ligne/     connexion, hub, salons, partie en ligne, joueurs/profil, classements
reseau/              client HTTP + WebSocket (fil séparé), instantanés, profil partagé
                     (niveaux, skins), mise à jour automatique
serveur/             api, base (migrations au démarrage), salons, simulation, succès, admin
structures/          Liste, File, Pile maison (reprises du TP : à utiliser, pas à remplacer)
outils/              construire.py (PyInstaller), envoyer_build.py, autotest.py, verifier.py,
                     icône, Docker
tests/               python -m unittest (52 tests)
.github/workflows/   tests.yml, serveur.yml, executables.yml
FEUILLE_DE_ROUTE.md  toutes les idées et corrections à venir
DEPLOIEMENT.md       installation sur le NAS
```

### Conventions de code (à imposer à Codex)

- Code, noms et commentaires **en français**, sans accents dans les identifiants.
- En-tête de chaque fichier : `Objectifs du fichier`, `Par : Thomas CHASSANIS PONS et Camil
  BOUZIRI (refonte avec Claude)`, `Réalisé le JJ/MM/AAAA`, et `ToDo List` facultatif.
- Docstring de chaque fonction au format `But / Entrée(s) / Sortie`.
- Textes affichés en MAJUSCULES, uniquement avec les caractères de la police bitmap (pas
  d'accents à l'écran, ils sont retirés automatiquement).
- Entrées : profils de touches (`menu`, `solo`, `j1`, `j2`) en **scancodes** dans
  `moteur/config.py`, pour fonctionner en AZERTY comme en QWERTY.
- Pas de nouvelle dépendance sans ton accord. Pas d'accès réseau dans la boucle de jeu (tout
  passe par `reseau/client.py`, en arrière-plan).
- Les écrans héritent d'`EcranBase` (`ecrans/base.py`). Les menus utilisent `MenuVertical` :
  une option peut avoir un 3e élément `fonction(sens)` pour ←→.
- Toute nouvelle fonctionnalité est accompagnée d'un test, et l'autotest ne doit pas casser.

## 3. Déploiement : ce qui se déclenche, et quand

| Workflow | Déclencheur | Effet |
|---|---|---|
| `tests.yml` | push sur `main` ou `dev/**`, pull requests | tests unitaires et autotest |
| `serveur.yml` | push sur `main` ou `dev/**` touchant serveur/jeu/moteur/reseau… ; lancement manuel | construit et teste l'image Docker. **Sur `main` seulement**, publie `ghcr.io/thomas-pns/neon-breaker:latest`. Le NAS ne la récupère que lorsque Thomas fait « Nettoyer » puis « Créer » dans Container Manager |
| `executables.yml` | **`main` seulement** : push modifiant `moteur/version.py` ou `outils/envoyer_build.py` ; lancement manuel depuis `main` | fabrique Windows, Mac Apple et Mac Intel, les teste, puis **les envoie au NAS**, ce qui publie la mise à jour à tous les joueurs |
| `test-windows.yml` | push sur `dev/**` ; lancement manuel (pas sur `main`) | fabrique un **exe Windows de test** `X.Y.Z-dev.N`, le passe à l'autotest et le dépose en **artefact GitHub** (7 jours). Rien n'est publié |

L'**exe de test** (canal « dev », fichier `data/canal.txt` écrit par `outils/construire.py`,
ou variable `NEON_CANAL=dev` depuis le code source) :
- range ses données dans `NeonBreaker-dev`, et ne touche donc pas à la vraie sauvegarde ;
- n'envoie **aucun score** au vrai serveur ;
- **désactive les parties en ligne** sur le vrai serveur. La consultation reste possible :
  connexion, joueurs, profils, classements ;
- ne se met **jamais** à jour tout seul ;
- affiche « VERSION DE TEST » sur l'écran titre.

Pour tester les parties en ligne ou une modification du serveur, lancer un serveur local et
le choisir avec `NEON_SERVEUR`, ce qui lève la protection :
`NEON_DONNEES_SERVEUR=./donnees_serveur python -m serveur`, puis
`NEON_SERVEUR=http://localhost:8765 python main.py`. Un second conteneur « test » sur le NAS
est une option à proposer à Thomas s'il veut tester à plusieurs.

Secrets (jeton de déploiement, adresse du serveur) : uniquement dans les secrets et variables
GitHub et dans le compose du NAS. **Ne les écris jamais dans le dépôt (il est public), ni
dans une consigne donnée à Codex.**

## 4. Lot 0 — déjà fait (23/10/2026)

- Branche **`dev/v2-delegation`** créée à partir de `main`. Tout le travail se fait dessus, ou
  sur des sous-branches `dev/v2-delegation/<tache>` dans des `git worktree` si deux agents
  touchent des fichiers proches.
- CI sécurisée : publication au NAS et sur GHCR depuis `main` uniquement, et plus de
  déclenchement par étiquette.
- `test-windows.yml` et le canal « dev » décrits ci-dessus.
- **Bug du redémarrage après mise à jour corrigé** dans `reseau/mise_a_jour.py`
  (`environnement_propre()` : `PYINSTALLER_RESET_ENVIRONMENT=1`, sans variables `_PYI_*` ni
  `_MEI*`). La correction ne sera visible qu'à la mise à jour qui suivra sa publication.
- `python outils/verifier.py` : tests unitaires et autotest en une commande, sur toutes les
  plateformes.
- `CLAUDE.md` à la racine : protocole de délégation.

Thomas teste l'artefact sur son PC. **On ne fusionne dans `main` que s'il est d'accord.**
La fusion, puis le changement de `VERSION` sur `main`, déclenchent le déploiement normal.

## 5. Travaux par priorité

Légende : **[C]** à garder pour Claude · **[D]** délégable à Codex (consigne et critères écrits
par Claude, relecture complète) · **[D→C]** Codex écrit, Claude fait la passe finale (visuel ou
équilibrage).

### P1 — Version 1.2 « confort » (petites tâches indépendantes)

1. ~~Redémarrage après la mise à jour~~ : fait au lot 0, sur `dev/v2-delegation`. Il reste à le
   vérifier en conditions réelles lors des deux prochaines mises à jour.
2. **[D] Version affichée** en bas à droite de l'écran titre (`moteur.version.VERSION`).
3. **[D→C] Menu NOUVEAUTÉS** : un écran avec un volet dépliable par version (bêtas, 1.0 jeu en
   ligne, 1.1 musique / défi / skins / mini-boss, 1.2…). Le contenu vient d'un fichier de données
   écrit par Claude.
4. **[D] Renommer le niveau du joueur en RANG** partout : hub, profils, liste des joueurs,
   salon, notifications, conditions des skins. **Ne pas toucher** aux « niveaux » de la campagne.
   Barre d'XP : « 409 / 750 XP AVANT LE RANG 4 ». Aperçu des skins : « CRYO SE DEBLOQUE AU RANG 5 ».
5. **[D] Noms des records** : réglage NOM DES RECORDS dans OPTIONS. Par défaut, les 3
   premières lettres du pseudo. Saisie pré-remplie : ENTRÉE valide directement. Un nom par
   joueur à deux.
6. **[D→C] Aide et explications dans le jeu** :
   - refaire l'écran AIDE (OVERDRIVE et SUPERNOVA, pouvoirs : 1 2 3, A/TAB pour choisir, E
     pour lancer, touches de J1 et de J2) ;
   - afficher les touches dans le HUD à côté de l'inventaire ;
   - bulles « première fois » (premier pouvoir, OVERDRIVE plein), mémorisées dans la
     sauvegarde et réactivables dans OPTIONS.
7. **[D] Page des succès** : fiche au clic ou au survol de la souris, noms en entier sur deux
   lignes.
8. **[D] En ligne pas à jour** : si `/api/version` annonce une version plus récente, l'accès à
   EN LIGNE ou à PARTIES EN LIGNE ouvre l'écran METTRE A JOUR, sans interrompre une partie
   solo. Serveur injoignable : message « SERVEUR EN MAINTENANCE » au lieu d'un code d'erreur,
   puis reconnexion automatique.
9. **[D] Touches 1 2 3** : vérifier le pavé numérique et la rangée des chiffres en AZERTY.

### P2 — Version 1.3 « en ligne »

10. **[C] Rebond décidé par le client propriétaire de la raquette** (priorité de Thomas). Quand
    la balle touche la raquette locale sur l'écran du joueur, le rebond est appliqué tout de
    suite côté client, et un message « rebond » est envoyé au serveur (position, vitesse,
    horodatage). Le serveur l'accepte s'il est plausible et réaligne les autres. Cela demande
    d'augmenter `PROTOCOLE` dans `moteur/version.py` (les anciens jeux voient alors « MISE A
    JOUR NECESSAIRE ») et de mettre à jour les tests réseau.
11. **[D] Ping dans le HUD en ligne** (vert / orange / rouge).
12. **[C] Prédiction de la balle** entre deux instantanés, avec recalage en douceur ; passer à
    60 instantanés par seconde, ou envoyer seulement les changements.
13. **[C] Duel : vue retournée pour le J2** (terrain retourné verticalement, textes et HUD à
    l'endroit).
14. **[C] schéma + [D] code — Séries du défi** : série en cours, record et historique (base,
    API, profil), onglet SERIES dans les classements, succès à 3, 7 et 30 jours.
15. **[C] Difficulté** : rééquilibrer SUNSET et le monde 1, option FACILE / NORMAL, difficulté
    adaptée au nombre de joueurs en Coop. Le code de l'option est délégable, l'équilibrage reste
    à Claude.

### P3 — Version 1.4 « visuel »

16. **[D→C] Icônes en pixel art générées par le code** pour les capsules (bonus, malus,
    pouvoirs), dans l'inventaire et l'aide, en gardant les couleurs actuelles.
17. **[D→C] Icônes des succès** (en couleur si obtenu, en gris sinon).
18. **[C] conception + [D→C] écran — Carte de campagne** : un chemin 2D entre les niveaux, un
    décor par monde, un brouillard sur la suite, les boss en étapes spéciales.

### P4 — Version 2.0 « économie » (schéma de base, API et sécurité : Claude ; code par morceaux : Codex)

19. Défi de la semaine et séries hebdomadaires.
20. Monnaie NEONS : gains calculés **uniquement par le serveur**, avec un historique des
    mouvements.
21. Boutique : skins premium animés, bannières (titres, bannières de boss, bannières animées),
    rotation hebdomadaire, boîte mystère (doublon partiellement remboursé), gains en
    campagne versés aussi rétroactivement.

### P5 — Plus tard

22. **[C]** Parties classées avec Elo : file d'attente, appariement, divisions, saisons.
    **[D]** le calcul Elo et l'onglet de classement.
23. **[C]** Mode 4 joueurs et RAID coopératif contre des boss géants.
24. **[D]** Commandes configurables, manettes.
25. **[C]** Étude d'une version navigateur (pygbag) pour iPhone, avec une icône sur l'écran
    d'accueil (PWA ou profil Web Clip).

Le détail de chaque idée est dans `FEUILLE_DE_ROUTE.md`. Coche les cases au fil des fusions.

## 6. Consignes données à Codex

Suivre le **modèle et la commande du `CLAUDE.md`** (`codexN exec --sandbox workspace-write
"..." > .delegation/codexN.log 2>&1`). Les agents ne commitent pas et ne poussent pas : c'est toi
qui commites après relecture, avec un commit par tâche. Valeurs à reprendre pour ce projet :

- **Contexte** : « Casse-brique Pygame (pygame-ce 2.5.8, Python 3.12), code et commentaires en
  français. Serveur FastAPI + SQLite. Voir l'en-tête des fichiers voisins pour le style. »
- **Fichiers à créer ou modifier** : liste exacte. Deux agents ne reçoivent jamais le même
  fichier en même temps.
- **Ne pas toucher** : par défaut `.github/`, `Dockerfile`, `docker-compose.yml`,
  `moteur/version.py`, `reseau/mise_a_jour.py`, `serveur/base.py`, `outils/construire.py`,
  `outils/envoyer_build.py`, plus tout fichier non listé.
- **Conventions** : celles de la section 2, en particulier les en-têtes, les docstrings
  But / Entrée / Sortie, les textes affichés en majuscules sans accents, les structures maison,
  les scancodes et l'absence de nouvelle dépendance.
- **Terminé quand** : comportement attendu, avec des exemples, plus « `python outils/verifier.py`
  affiche TOUT PASSE », plus les tests à ajouter.
- **Avant de finir** : « lance `python outils/verifier.py` et corrige jusqu'à TOUT PASSE ».
- Jamais de secret, jamais d'adresse du serveur dans une consigne.

En cas d'échec : renvoyer l'erreur à l'agent (2 essais au maximum), puis reprendre la main.
En cas de quota atteint : passer sur l'autre compte, ou faire la tâche soi-même.

## 7. Relecture et validation (à chaque tâche)

```bash
pip install -r requirements.txt -r serveur/requirements.txt httpx   # une fois
python outils/verifier.py
```

- Relire le diff (`git diff --stat`, puis les parties utiles) : conventions, effets de bord,
  compatibilité des sauvegardes (`moteur/sauvegarde.py` fusionne les clés par défaut),
  compatibilité avec les **anciens jeux** encore installés chez les amis (champs JSON en plus :
  oui ; champs retirés ou renommés : non, sauf en augmentant `PROTOCOLE`).
- Migrations de base : uniquement des ajouts, idempotents, faits au démarrage dans
  `serveur/base.py` (voir les migrations `jour` et `skin`), et testés sur une base 1.0 (voir
  `test_migration_base_1_0`). Prévenir Thomas de sauvegarder `data/` sur le NAS avant une
  fusion qui touche au serveur.
- Passe visuelle : créer l'écran avec `SDL_VIDEODRIVER=dummy`, avancer quelques images
  (`app._mettre_a_jour(1/60)` puis `app._dessiner()`), enregistrer
  `pygame.image.save(app.ecran.image, ".delegation/capture.png")` et **regarder** l'image
  (textes qui se chevauchent, qui débordent, lisibilité).
- Puis commit sur `dev/v2-delegation` et push : la CI teste, et `test-windows.yml` fournit l'exe à
  Thomas. Donne-lui un court résumé de ce qui a changé et de quoi tester, avec le lien vers
  l'onglet Actions.

## 8. Après la fusion dans `main`

1. Changer `VERSION` dans `moteur/version.py` sur `main` : cela lance la fabrication et l'envoi
   des trois exécutables. L'envoi sur `main` publie aussi l'image du serveur si le code serveur
   a changé.
2. Si le serveur a changé : demander à Thomas, dans Container Manager, **Projet neon-breaker >
   Action > Nettoyer, puis Action > Créer**. « Démarrer » seul ne recrée pas le conteneur.
   **Il faut le faire avant que les joueurs installent la nouvelle version.**
3. Vérifier que `https://<adresse du serveur>/api/version` annonce la nouvelle version (l'adresse
   est dans la variable GitHub `NEON_SERVEUR_URL` ; demande-la à Thomas, ne l'écris pas dans le
   dépôt).
