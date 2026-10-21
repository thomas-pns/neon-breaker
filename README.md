# NEON BREAKER

Refonte en **Pygame** du casse-brique Tkinter du TP4-5-6 (CPE 3A), par
Thomas CHASSANIS PONS et Camil BOUZIRI, avec Claude.
Style synthwave néon : fond animé, halos lumineux, filtre CRT, effets spéciaux.

> Cahiers des charges : `PROMPT.md` (jeu) et `PROMPT_EN_LIGNE.md` (jeu en ligne).
> Mise en ligne sur le NAS : **`DEPLOIEMENT.md`**.
> **Version 1.1** : musiques synthwave générées, nouveaux sons, menu OPTIONS, défi du jour,
> skins de raquette, mini-boss en Arcade, Coop en ligne limitée aux niveaux débloqués.

## Installation

Pour les joueurs : télécharger l'exécutable Windows ou Mac sur la page du serveur.

Depuis le code source : double-cliquer sur `LANCER.bat`, qui installe les dépendances si besoin. Ou bien :

```bash
pip install -r requirements.txt
python main.py
```

Options : `python main.py --plein-ecran`, `python main.py --debug` (affiche les FPS).

## Modes de jeu

| Mode | Joueurs | Principe |
|---|---|---|
| **Campagne** | 1 | 12 niveaux en 3 mondes (Sunset Grid, Neon City, Cyber Core), un boss tous les 4 niveaux, progression sauvegardée |
| **Arcade** | 1 | Le mur descend de plus en plus vite et des rangées aléatoires arrivent en haut : tenir le plus longtemps possible. Un mini-boss DRONE toutes les 10 vagues |
| **Défi du jour** | 1 | Une Arcade identique pour tout le monde le même jour (mêmes rangées, une règle spéciale tirée au sort), avec son classement du jour |
| **Hardcore** | 1 | La campagne en 1 vie, balle +30 %, malus seulement, ni pouvoirs ni OVERDRIVE, score x2 |
| **Coop** | 2 | Deux raquettes en bas, vies et score d'équipe, niveaux de la campagne |
| **Duel** | 2 | J1 en bas, J2 en haut, mur au centre ; les malus attrapés partent chez l'adversaire ; premier à 7 points |
| **Course** | 2 | Écran partagé ; chaque combo de 5 envoie une attaque à l'adversaire ; 2 manches gagnantes |

Les modes solo ont un top 10, avec saisie du nom en 3 lettres. Les boss :

- **SUNSET** : se protège avec des briques qui se reforment et tire des boules de feu.
- **GRIDLOCK** : invoque des rangées de briques, puis tire des rayons annoncés par une ligne rouge.
- **CORE** : bouclier tournant, rayons, puis rafales de malus.

## En ligne

Menu **EN LIGNE** : créer un compte (pseudo + mot de passe), puis

- **Parties en ligne** : liste des parties ouvertes (4 au maximum). Créez une Coop (avec choix parmi les niveaux déjà atteints), un Duel ou une Course, ou rejoignez celle d'un ami. Dans le salon, chacun se déclare **PRET**, puis l'hôte lance.
- **Joueurs** : tous les inscrits, leur niveau, leurs succès, qui est en ligne.
- **Profil** : niveau et XP, statistiques, records par mode, grille des 28 succès.
- **Classements mondiaux** : défi du jour, meilleur score par mode, victoires en Duel et en Course.
- **Couleur** : la couleur de votre pseudo.
- **Skin** : l'habillage de votre raquette (9 skins, débloqués par le niveau et les succès), visible par l'autre joueur en ligne.

Les parties en ligne sont calculées par le serveur. Votre raquette répond immédiatement (elle est pilotée sur votre PC), et le décalage réseau est compensé.
Les scores solo (Campagne, Arcade, Hardcore, Défi) sont envoyés automatiquement. Ceux joués hors ligne partent à la prochaine connexion.
Les succès débloqués apparaissent en notification en haut à droite. Le jeu se met à jour tout seul quand une nouvelle version sort.

## Commandes

Les touches sont lues par leur **emplacement** : elles marchent pareil en AZERTY et en QWERTY.

| Action | Solo | Joueur 1 | Joueur 2 |
|---|---|---|---|
| Bouger | ← → ou Q D, ou la souris | Q D | ← → |
| Lancer la balle / relâcher l'aimant | Espace, ou clic gauche | Z | ↑ |
| Utiliser un pouvoir | 1 2 3 | A (choisir) puis E (activer) | Ctrl droit (choisir) puis Maj droite (activer) |
| OVERDRIVE | Maj, ou clic droit | S | ↓ |
| Pause | Échap ou P | | |

F11 : plein écran. F3 : images par seconde.

## Capsules

Elles tombent des briques. Vert = bonus, rouge = malus, or = pouvoir à stocker.

- **Bonus** : E Élargir, M Multi-balle, F Balle de feu, S Ralenti, A Aimant, N Filet, + Vie.
- **Malus** : R Rétrécir, V Turbo, I Inversion, B Brouillard, G Glace, X Balle fantôme.
- **Pouvoirs** (3 emplacements) : L Laser, D Bouclier, O Onde de choc, K Bombe, T Chrono, H Guidage.

**OVERDRIVE** : la jauge se remplit à chaque brique, plus vite en combo, et avec les capsules.
Une fois pleine, elle déclenche **SUPERNOVA** : 6 secondes de balles de feu et un rayon qui balaie la colonne au-dessus de la raquette.

**Combos** : briques cassées sans que la balle touche la raquette. Ils donnent un multiplicateur x2 (5 briques), x3 (10), x5 (20) et x8 (35).

## Créer un niveau

Créer un fichier `data/niveaux/13_mon_niveau.txt` (12 caractères par ligne) :

```
nom: MON MONDE 4-1  MON NIVEAU
monde: 3
vitesse: 1.1
boss: core        (facultatif : sunset, gridlock ou core)
---
aaaaaaaaaaaa
.RRRX??XRRR.
M..3vvvv3..M
P..HHHHHH..P
```

| Caractère | Brique |
|---|---|
| `a r v b c o g` | normale (ambre, rose, violet, bleu, cyan, or, vert) |
| `A R V B C O G` | solide, 2 coups |
| `3 4 5` | solide, 3 à 5 coups |
| `M` | métal (indestructible, sauf feu) |
| `X` | explosive (détruit ses 8 voisines, en chaîne) |
| `?` | bonus (lâche toujours une capsule) |
| `<` `>` | mobile |
| `H` | régénérante (revient au bout de 6 s si une sœur survit) |
| `*` | fantôme (invisible, 2 coups) |
| `P` | portail (relié au `P` suivant) |
| `.` | vide |

## Architecture

```
main.py              point d'entrée (NEON_AUTOTEST=1 : visite automatique de tous les écrans)
moteur/              config, application (Pile d'écrans), rendu néon/CRT, police pixel,
                     fond synthwave (3 thèmes), effets, audio (fondus), musique (compositeur
                     synthwave numpy), entrées, sauvegarde
jeu/                 balle, raquette, briques, capsules, projectiles, joueur, pouvoirs,
                     boss, niveaux, terrain (physique + File d'événements)
jeu/modes/           base, campagne (+ hardcore, coop), arcade, defi, duel, course
ecrans/              titre, modes, niveaux, partie, hud, pause, options, aide, scores, saisie, fin
structures/          Liste, File, Pile (reprises du TP)
reseau/              client HTTP + WebSocket, instantanés de partie, mise à jour automatique
ecrans/en_ligne/     connexion, menu en ligne, parties et salon, partie en ligne, joueurs,
                     profil, classements
serveur/             FastAPI + SQLite : comptes, scores, succès, salons, simulation des parties
outils/              fabrication PyInstaller, envoi au NAS, icône, autotest, démarrage Docker
.github/workflows/   tests, image Docker du serveur, exécutables Windows / macOS
tests/               python -m unittest  (52 tests)
```

- Un **Terrain** est une zone de jeu autonome : la Course en affiche deux côte à côte.
  Il signale tout ce qui arrive (brique détruite, capsule attrapée, balle perdue…) dans une **File**.
  Le **mode** lit cette file et applique ses propres règles.
- La **Pile** d'écrans permet d'empiler la pause, puis l'aide, au-dessus de la partie.
- La physique avance à 120 Hz, en sous-pas : la balle ne traverse jamais rien.
  Le rebond sur la raquette reprend la réflexion de Descartes de la version Tkinter.

## Tests

```bash
pip install -r requirements.txt -r serveur/requirements.txt httpx
python -m unittest -v
```

Pour lancer le serveur en local :

```bash
pip install -r serveur/requirements.txt
NEON_DONNEES_SERVEUR=./donnees_serveur python -m serveur        # http://localhost:8765
NEON_SERVEUR=http://localhost:8765 python main.py               # le jeu, connecté à ce serveur
```

## Musique

`moteur/musique.py` compose six boucles au premier lancement (menu, un thème par monde, boss,
OVERDRIVE) : basse, nappe, arpège avec écho, mélodie et batterie, rendus avec numpy puis
gardés en `.wav` dans le dossier de données. La musique de l'OVERDRIVE se pose par-dessus
celle du niveau, qui reprend là où elle en était. Volumes dans **OPTIONS** (titre ou pause).

## Prochaine étape

Commandes configurables, manettes, parties à 4 joueurs.
