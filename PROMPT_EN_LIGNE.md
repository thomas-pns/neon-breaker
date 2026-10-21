# PROMPT — NEON BREAKER EN LIGNE

> Phase 2 du projet. Validée par Thomas le 21/10/2026.
> Base : NEON BREAKER (jalons 1 à 4 de `PROMPT.md`).

## 1. Objectif

Rendre NEON BREAKER jouable en ligne entre amis grâce au NAS Synology DS220+ (Container Manager) :

- un compte par joueur (pseudo + mot de passe), connexion directement dans le jeu ;
- les modes **Coop, Duel et Course en ligne**, à 2 joueurs, trouvés dans une **liste de parties ouvertes** (4 au maximum, sans mot de passe, sans chat) ;
- les **classements mondiaux**, la **liste de tous les joueurs** et leur **page de profil** (niveau, couleur, statistiques, records, succès) ;
- **24 succès**, définis côté serveur (on peut en ajouter sans mettre le jeu à jour) ;
- un `.exe` Windows et une application macOS (puces Apple et Intel) qui **se mettent à jour automatiquement**.

## 2. Décisions

| Sujet | Décision |
|---|---|
| Public | Toute personne qui a l'exécutable (en pratique : les amis de Thomas, moins de 10 joueurs) |
| Comptes | Pseudo (3 à 12 caractères, unique) + mot de passe (6 caractères minimum, stocké avec scrypt). Pas d'e-mail |
| Mot de passe oublié | Commande d'administration dans le conteneur (`reset-mdp PSEUDO`) |
| Autorité | Le serveur simule les parties en ligne ; les clients envoient leurs commandes et affichent l'état reçu |
| Scores solo | Envoyés par le client (confiance) ; les parties jouées hors ligne sont mises en file et envoyées à la reconnexion |
| Profil | Niveau calculé à partir de l'XP + une couleur néon au choix |
| Base de données | SQLite (un fichier dans `docker/neon-breaker/data`), mode WAL |
| Accès | DDNS Synology gratuit + proxy inversé DSM déjà en place sur le port 443 : une règle de plus (sous-domaine) vers le conteneur, WebSocket activé |
| Code | Dépôt GitHub public, **sans exécutables ni secrets** |
| Exécutables | Fabriqués par GitHub Actions, puis **envoyés au NAS** avec un jeton secret ; le NAS les distribue et sert la mise à jour |
| Hors ligne | Le jeu reste entièrement jouable sans connexion |

## 3. Architecture

```
NAS (Container Manager)
└── conteneur « neon-serveur » (Python 3.12, FastAPI + uvicorn, ~100 Mo de RAM)
    ├── API REST  /api/...           comptes, scores, joueurs, profils, succès, version
    ├── WebSocket /ws                 liste des parties, salon d'attente, parties en ligne
    ├── /telechargements/...          exécutables Windows / macOS
    ├── simulation des parties        mêmes modules jeu/ que le client, sans affichage
    └── /data                         neon.sqlite3, builds/, journal

PC / Mac du joueur
└── NeonBreaker (.exe / .app)
    ├── jeu local (inchangé)          solo et 2 joueurs sur le même clavier
    ├── reseau/                       client HTTP + WebSocket dans un fil séparé
    └── ecrans/en_ligne/              connexion, hub, parties, salon, partie miroir, joueurs, profil, classements
```

### Parties en ligne

- Le serveur fait tourner le mode (physique à 120 Hz) et envoie un **instantané 30 fois par seconde** : joueurs, raquettes, balles, capsules, tirs, boss, et briques seulement quand elles changent.
- Les **effets spéciaux et les sons** déclenchés par la partie sont enregistrés côté serveur et rejoués par les clients : particules, textes, ondes de choc, flashs.
- Chaque client **prédit sa propre raquette** (réponse immédiate aux touches) et affiche les autres objets **interpolés** entre deux instantanés.
- Si un joueur se déconnecte, la partie est mise en pause 30 s pour lui laisser le temps de revenir ; sinon elle s'arrête.
- Les résultats (score d'équipe en Coop, victoire en Duel ou en Course) sont enregistrés par le serveur.

## 4. Succès (24)

| Code | Nom | Condition |
|---|---|---|
| premiere_brique | PREMIER IMPACT | Casser une brique |
| premier_niveau | EN ROUTE | Finir un niveau de campagne |
| premiere_en_ligne | CONNECTE | Jouer une partie en ligne |
| boss_sunset | COUCHER DE SOLEIL | Vaincre SUNSET |
| boss_gridlock | DEBLOCAGE | Vaincre GRIDLOCK |
| boss_core | COEUR BRISE | Vaincre CORE |
| campagne | LEGENDE NEON | Finir la campagne |
| campagne_parfaite | SANS FAUTE | Finir la campagne sans perdre de vie |
| combo_8 | x8 | Atteindre le multiplicateur x8 |
| combo_50 | INARRETABLE | Combo de 50 briques |
| supernova | SUPERNOVA | Déclencher une SUPERNOVA |
| bombe_10 | ARTIFICIER | 10 briques détruites par une seule bombe |
| arcade_30 | SURVIVANT | Atteindre la vague 30 en Arcade |
| hardcore_monde | HARDCORE | Finir un monde en Hardcore |
| duel_7_0 | ECRASANT | Gagner un Duel 7-0 |
| course_parfaite | FLECHE NEON | Gagner une Course sans perdre de manche |
| coop_10 | DUO | 10 parties en Coop |
| coop_boss | FORCES COMBINEES | Vaincre un boss en Coop |
| coop_campagne | INSEPARABLES | Finir la campagne en Coop |
| collection_capsules | COLLECTIONNEUR | Attraper chaque type de capsule |
| tous_pouvoirs | ARSENAL | Utiliser chaque pouvoir |
| briques_10000 | DEMOLISSEUR | 10 000 briques au total |
| parties_100 | ACCRO | 100 parties jouées |
| secret_malus | MASOCHISTE | Finir un niveau en ayant attrapé 5 malus (succès secret) |

XP d'une partie = 20 + score / 50 (au plus 2 000). Niveau = 1 + √(XP / 150), arrondi à l'unité inférieure.

## 5. Distribution et mises à jour

1. Thomas pousse une étiquette de version `vX.Y.Z` sur GitHub.
2. GitHub Actions fabrique trois exécutables avec PyInstaller : Windows (`.exe`), macOS Apple (`.app` zippée) et macOS Intel.
3. Chaque exécutable est envoyé au NAS (`POST /api/builds`, protégé par le secret `NEON_JETON_DEPLOIEMENT`).
4. Au lancement, le jeu demande au serveur la dernière version. Si elle est plus récente, il la télécharge, se remplace et redémarre.
5. L'image Docker du serveur est publiée sur GitHub (ghcr.io) à chaque envoi sur `main`. Container Manager la récupère, automatiquement avec Watchtower.

L'adresse du serveur est une variable du dépôt (`NEON_SERVEUR_URL`), injectée au moment de la fabrication : elle n'apparaît pas dans le code.

## 6. Critères d'acceptation

- [ ] Inscription, connexion et déconnexion ; la session reste ouverte entre deux lancements.
- [ ] Créer, rejoindre et quitter une partie ; au plus 4 parties ouvertes ; lancement quand les 2 joueurs sont prêts.
- [ ] Coop, Duel et Course jouables en ligne avec 150 ms de décalage simulé, sans désynchronisation visible.
- [ ] Déconnexion d'un joueur gérée (pause, retour possible, puis fin).
- [ ] Classements mondiaux, liste des joueurs, profils et succès visibles dans le jeu.
- [ ] Notification « SUCCES DEBLOQUE » en jeu.
- [ ] Scores joués hors ligne envoyés à la reconnexion.
- [ ] Jeu entièrement jouable hors ligne, sans message d'erreur bloquant.
- [ ] Mise à jour automatique sous Windows et macOS.
- [ ] `docker compose up` démarre le serveur ; le guide `DEPLOIEMENT.md` permet d'installer sans aide.
- [ ] Tests automatiques : API, succès, et parties en ligne jouées par deux clients bots.
