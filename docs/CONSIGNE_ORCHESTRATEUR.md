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
outils/              construire.py (PyInstaller), envoyer_build.py, autotest.py, icône, Docker
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

| Workflow | Déclencheur actuel | Effet |
|---|---|---|
| `tests.yml` | push sur `main`, pull requests | tests unitaires et autotest |
| `serveur.yml` | push sur `main` touchant serveur/jeu/moteur/reseau…, ou lancement manuel | construit et **publie `ghcr.io/thomas-pns/neon-breaker:latest`**. Le NAS ne la récupère que lorsque Thomas fait « Nettoyer » puis « Créer » dans Container Manager |
| `executables.yml` | push sur `main` modifiant `moteur/version.py`, `outils/envoyer_build.py` ou ce workflow ; **ou une étiquette `v*.*.*` poussée depuis n'importe quelle branche** ; ou lancement manuel | fabrique Windows, Mac Apple et Mac Intel, les teste, puis **les envoie au NAS**, ce qui publie une mise à jour pour tous les joueurs |

Points de vigilance :

- Une étiquette `v…` ou un lancement manuel d'`executables.yml` **depuis une branche de
  dev publie quand même** la mise à jour à tous les joueurs. Il en va de même pour un
  lancement manuel de `serveur.yml`, qui écrase `:latest`.
- Un exécutable fabriqué par la CI contient l'adresse du serveur de production (variable
  GitHub `NEON_SERVEUR_URL`, injectée dans `data/serveur.txt`). Une version de test se connecte
  donc au **vrai** serveur et y envoie de vrais scores.
- `outils/construire.py` n'accepte aujourd'hui que des versions `X.Y.Z`.
- Le jeu range ses données dans `%APPDATA%/NeonBreaker`. Une version de test et la vraie
  partagent donc la même sauvegarde.
- Secrets (jeton de déploiement, adresse du serveur) : uniquement dans les secrets et variables
  GitHub et dans le compose du NAS. **Ne les écris jamais dans le dépôt (il est public), ni
  dans une consigne donnée à Codex.**

## 4. Lot 0 — à faire toi-même avant toute délégation

1. Créer la branche `dev/v2-delegation` à partir de `main`. Tout le travail se fait dessus,
   ou sur des sous-branches `dev/v2-delegation/<tache>` (une par agent, de préférence dans
   des `git worktree` séparés).
2. Sécuriser la CI :
   - `executables.yml` et `serveur.yml` : les étapes d'envoi au NAS et de publication sur GHCR
     ne doivent s'exécuter que si `github.ref == 'refs/heads/main'`. Pour les étiquettes,
     vérifier que le commit étiqueté est bien sur `main`, ou supprimer le déclencheur par
     étiquette ;
   - `tests.yml` : ajouter les branches `dev/**`.
3. Nouveau workflow `test-windows.yml` : sur push vers `dev/**` (et en lancement manuel), il
   fabrique **seulement l'exe Windows**, lance l'autotest, puis le publie en **artefact
   GitHub** (`actions/upload-artifact`, conservé 7 jours). Pas d'envoi au NAS.
   - Version : `X.Y.Z-dev.<numéro de run>`. Il faut adapter `construire.py`, et vérifier
     `comparer_versions` : une version `-dev` doit être considérée comme plus récente que la
     version en ligne, pour que le jeu de test ne propose pas de « mise à jour » qui
     l'écraserait.
   - Dossier de données séparé quand la version contient `-dev` (par exemple
     `NeonBreaker-dev`), pour ne pas toucher à la vraie sauvegarde de Thomas.
   - Serveur : par défaut, celui de production, **uniquement si le protocole et le serveur
     n'ont pas changé**. Pour une tâche qui touche au serveur, tester en local
     (`NEON_DONNEES_SERVEUR=./donnees_serveur python -m serveur`, puis
     `NEON_SERVEUR=http://localhost:8765 python main.py`). Un second conteneur « test » sur le
     NAS est une option à proposer à Thomas plus tard.
4. Corriger le bug du redémarrage après mise à jour (voir P1-1) : la partie Windows ne peut se
   vérifier qu'avec un vrai exe.

Thomas teste l'artefact sur son PC. **On ne fusionne dans `main` que s'il est d'accord.**
La fusion, le changement de `VERSION` et l'envoi sur `main` déclenchent alors le déploiement
normal.

## 5. Travaux par priorité

Légende : **[C]** à garder pour Claude · **[D]** délégable à Codex (consigne et critères écrits
par Claude, relecture complète) · **[D→C]** Codex écrit, Claude fait la passe finale (visuel ou
équilibrage).

### P1 — Version 1.2 « confort » (petites tâches indépendantes)

1. **[C] Redémarrage après la mise à jour** (`reseau/mise_a_jour.py`) : lancer le script de
   remplacement avec `PYINSTALLER_RESET_ENVIRONMENT=1`, sans les variables `_PYI_*` et
   `_MEIPASS2`. Aujourd'hui, le nouvel exe affiche « Failed to load Python DLL » au redémarrage.
   La correction ne profite qu'à la mise à jour suivante.
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

## 6. Consignes données à Codex : modèle

Chaque consigne tient en une page et contient :

1. le contexte minimal (fichiers concernés, extraits utiles) ;
2. le but et le comportement attendu, avec des exemples ;
3. les **fichiers autorisés**, de sorte que deux agents ne modifient jamais le même fichier en
   même temps ;
4. les conventions de la section 2 ;
5. les critères d'acceptation : tests à ajouter, commandes qui doivent passer, ce qui ne doit
   pas changer ;
6. les interdits :
   - pas de push sur `main`, pas d'étiquette, pas de lancement manuel de workflow ;
   - ne modifier ni `.github/`, ni `docker-compose.yml`, ni `moteur/version.py` (sauf demande
     explicite) ;
   - aucun secret, pas de nouvelle dépendance, pas de reformatage de fichiers entiers.

## 7. Relecture et validation (à chaque tâche)

```bash
pip install -r requirements.txt -r serveur/requirements.txt httpx
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m unittest -v
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy NEON_AUTOTEST=1 NEON_DONNEES=/tmp/neon python main.py
```

- Relire le diff ligne à ligne : conventions, effets de bord, compatibilité des sauvegardes
  (`moteur/sauvegarde.py` fusionne les clés par défaut), compatibilité avec les **anciens jeux**
  encore installés chez les amis (champs JSON en plus : oui ; champs retirés ou renommés :
  non, sauf en augmentant `PROTOCOLE`).
- Migrations de base : uniquement des ajouts, idempotents, faits au démarrage dans
  `serveur/base.py` (voir les migrations `jour` et `skin`), et testés sur une base 1.0 (voir
  `test_migration_base_1_0`). Prévenir Thomas de sauvegarder `data/` sur le NAS avant une
  fusion qui touche au serveur.
- Passe visuelle : créer l'écran avec `SDL_VIDEODRIVER=dummy`, avancer quelques images
  (`app._mettre_a_jour(1/60)` puis `app._dessiner()`), enregistrer
  `pygame.image.save(app.ecran.image, ...)` et **regarder** les captures (textes qui se
  chevauchent, qui débordent, lisibilité).
- Avant de proposer une fusion : la CI de la branche est verte, l'artefact Windows est publié,
  et Thomas a un court résumé de ce qui a changé et de quoi tester.

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
