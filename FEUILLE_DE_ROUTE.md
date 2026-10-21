# Feuille de route NEON BREAKER

Idées et corrections notées pour les prochaines versions (retours de Thomas après la 1.1).

## Priorité 1 : à corriger

- [ ] **Erreur « Failed to load Python DLL » après la mise à jour automatique (Windows).**
  Après METTRE A JOUR, le jeu redémarre et affiche `Failed to load Python DLL ...\_MEIxxxx\python312.dll`.
  Il marche si on le relance à la main.
  Cause : le nouvel exécutable est lancé par l'ancien, dont il hérite les variables
  d'environnement PyInstaller. Il cherche alors ses fichiers dans le dossier temporaire de
  l'ancien, déjà effacé.
  Correction : lancer le script de remplacement avec `PYINSTALLER_RESET_ENVIRONMENT=1`, sans les
  variables `_PYI_*` et `_MEIPASS2` (dans `reseau/mise_a_jour.py`, sous Windows et sous macOS).
  Attention : cette correction ne sert qu'à partir de la mise à jour suivante. La mise à jour
  vers la version corrigée elle-même affichera encore l'erreur une dernière fois.

## Version et mises à jour

- [ ] Afficher la version du jeu en bas à droite de l'écran titre.
- [ ] Menu **NOUVEAUTES** avec l'historique des versions, chaque version en volet dépliable :
  - les bêtas avant la 1.0 : jalons du jeu solo (moteur, briques spéciales, boss, modes à
    2 joueurs, effets…) ;
  - la 1.0 : jeu en ligne ;
  - la 1.1 : musique, défi, skins…
- [ ] Jeu pas à jour + clic sur **EN LIGNE** ou **PARTIES EN LIGNE** : bloquer l'accès et
  proposer **METTRE A JOUR**. Ne pas interrompre une partie solo en cours.
- [ ] Serveur injoignable (redémarrage du conteneur) : remplacer le code d'erreur brut affiché
  sur l'écran titre par un message clair (« SERVEUR EN MAINTENANCE, JEU HORS LIGNE ») et se
  reconnecter tout seul quand il revient.
- [ ] (plus tard, facultatif) Mode maintenance côté admin : annoncer une mise à jour, couper
  le jeu en ligne une fois les parties finies.

## Aide et lisibilité

- [ ] Refaire l'écran **AIDE**, avec des explications claires sur :
  - **OVERDRIVE** : jauge remplie en cassant des briques, en attrapant des capsules ou en
    touchant un boss. Pleine, elle déclenche la **SUPERNOVA** (MAJ ou clic droit) : 6 s de balle
    de feu qui traverse tout, balle +25 %, et un rayon qui détruit les briques au-dessus de la
    raquette ;
  - **POUVOIRS** : inventaire de 3 places. En solo, 1, 2 ou 3 lancent directement un
    emplacement, et A (ou TAB) + E servent à choisir puis à lancer. À deux, chacun a sa
    touche pour changer et sa touche pour lancer.
- [ ] **Explications dans le jeu**, car peu de joueurs ouvrent l'aide :
  - dans le HUD, à côté de l'inventaire, afficher les vraies touches de chaque joueur : 1 2 3,
    « A / TAB : CHOISIR », « E : LANCER » (en solo), et celles de J1 et de J2 à deux ;
  - la première fois qu'on attrape un pouvoir, une bulle explique comment le choisir et le lancer ;
  - la première fois que la jauge OVERDRIVE est pleine, une bulle indique « MAJ / CLIC DROIT : SUPERNOVA » ;
  - ces bulles ne s'affichent qu'une fois (mémorisé dans la sauvegarde) et se réactivent dans OPTIONS.
- [ ] Vérifier pourquoi les touches 1 2 3 semblent parfois ne pas répondre
  (pavé numérique, touches au-dessus des lettres en AZERTY sans MAJ).
- [ ] **Icônes en pixel art** générées par le jeu pour toutes les capsules : bonus, malus,
  pouvoirs et spéciales. Elles remplacent les lettres, en gardant le code couleur actuel.
  Les mêmes icônes servent dans l'inventaire et dans l'aide.

## Succès (page de profil)

- [ ] Clic ou survol à la souris sur un succès : une fiche détaillée s'ouvre (nom complet,
  description, date d'obtention). Aujourd'hui, la fiche n'apparaît qu'avec les flèches.
- [ ] Les noms sont coupés sur les tuiles (« EN ROUT… ») : les écrire en entier sur deux lignes.
- [ ] Une icône en pixel art par succès (x8, un soleil pour SUNSET, une bombe pour ARTIFICIER…),
  en couleur une fois obtenu, en gris avant.

## Vocabulaire

- [ ] « NIVEAU » veut dire deux choses (le niveau du joueur, gagné avec l'XP, et les 12 niveaux de
  la campagne) : c'est trompeur. Renommer le niveau du joueur en **RANG** (« RANG 5 »), partout :
  menu en ligne, profils, liste des joueurs, salon, conditions des skins, notifications.
- [ ] Barre d'XP : le texte « 1009 / 1350 XP » (XP totale) ne correspond pas à la barre, qui
  montre la progression dans le rang en cours. Afficher plutôt « 409 / 750 XP AVANT LE RANG 4 ».
- [ ] Aperçu des skins : « PROCHAIN : CRYO - NIVEAU 5 » se lit comme « vous êtes niveau 5 ».
  Écrire « CRYO SE DEBLOQUE AU RANG 5 ».

## Difficulté

- [ ] Le boss 1 (SUNSET) est déjà très dur : rééquilibrer le monde 1 (moins de tirs, garde plus
  lente) et/ou ajouter une difficulté au choix (FACILE / NORMAL), ainsi qu'une vie de plus
  avant chaque boss.

## Défi du jour

- [ ] **Séries (streaks)** : nombre de jours d'affilée où l'on a joué le défi.
  - Profil : série en cours, record de série, historique (calendrier).
  - Classement mondial : onglet « SERIES ».
  - Succès de série : 3, 7 et 30 jours.

## Campagne

- [ ] **Carte du monde** façon Geometry Dash / carte de jeu de plateforme :
  - un chemin 2D qui relie les niveaux 1, 2, 3… ;
  - un décor illustré pour chaque monde ;
  - le brouillard cache la suite de la carte tant qu'elle n'est pas atteinte ;
  - le curseur se déplace le long du chemin, et les boss sont des étapes spéciales.

## Duel en ligne

- [ ] Aujourd'hui, les deux joueurs voient le même écran : J1 en bas, J2 en haut. **Retourner la vue
  du J2** pour que chacun se voie en bas : on dessine le terrain dans une image à part, retournée
  verticalement, puis on ajoute par-dessus les textes et le HUD à l'endroit. Les commandes
  gauche / droite restent naturelles (le retournement est vertical uniquement).

## Mode 4 joueurs (gros chantier)

- [ ] Terrain carré plus grand, une raquette par côté (bas, haut, gauche, droite), raquettes
  verticales pour les côtés. Chaque joueur voit sa raquette en bas (vue tournée).
- [ ] Variantes : chacun pour soi (chaque côté protège son but, 5 vies chacun) et 2 contre 2.
- [ ] Le serveur gère déjà les parties ; il faudra passer les salons à 4 places et adapter les
  instantanés, plus un écran d'attente à 4.

## Déjà prévu avant

- [ ] Commandes configurables, manettes.
- [ ] Parties à 4 joueurs.
- [ ] Chat (pas pour l'instant).
