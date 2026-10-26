# Feuille de route NEON BREAKER

Idées et corrections notées pour les prochaines versions (retours de Thomas après la 1.1).

## Priorité 1 : à corriger

- [x] **Erreur « Failed to load Python DLL » après la mise à jour automatique (Windows).**
  Après METTRE A JOUR, le jeu redémarre et affiche `Failed to load Python DLL ...\_MEIxxxx\python312.dll`.
  Il marche si on le relance à la main.
  Cause : le nouvel exécutable est lancé par l'ancien, dont il hérite les variables
  d'environnement PyInstaller. Il cherche alors ses fichiers dans le dossier temporaire de
  l'ancien, déjà effacé.
  Correction : lancer le script de remplacement avec `PYINSTALLER_RESET_ENVIRONMENT=1`, sans les
  variables `_PYI_*` et `_MEIPASS2` (dans `reseau/mise_a_jour.py`, sous Windows et sous macOS).
  Attention : cette correction ne sert qu'à partir de la mise à jour suivante. La mise à jour
  vers la version corrigée elle-même affichera encore l'erreur une dernière fois.

## Noms des records

- [x] Ne plus demander les 3 lettres à chaque record :
  - un réglage **NOM DES RECORDS** dans OPTIONS ; par défaut, les 3 premières lettres du pseudo
    en ligne, sinon les dernières lettres saisies ;
  - à un nouveau record, le nom est déjà rempli : ENTREE valide tout de suite, ou on le modifie
    avant de rejouer ;
  - à deux joueurs, un nom par joueur (J1, J2).

## Latence en ligne

Aujourd'hui, le serveur calcule tout et envoie l'état 60 fois par seconde (30 avant la 1.5). Votre raquette répond
tout de suite, mais la balle et l'autre joueur arrivent avec le retard du réseau (environ un
demi-ping, plus le temps entre deux images du serveur). C'est surtout sensible quand la balle
touche **votre** raquette. Pistes, de la plus rentable à la plus lourde :

- [x] **(fait en 1.3)** **Rebond décidé par le joueur qui tient la raquette** : quand la balle touche votre
  raquette sur votre écran, votre jeu fait rebondir la balle tout de suite et prévient le
  serveur, qui s'aligne (on fait confiance entre amis). Plus aucune balle « traversée » ni de
  rebond en retard sur sa propre raquette.
- [x] **(fait en 1.5)** **Recalage doux de la balle** : un petit écart avec le serveur est
  rattrapé en 0,1 s au lieu de faire sauter la balle (5 fois moins de sauts en test).
- [x] **(fait en 1.5)** **Raquette de l'autre joueur fluide** : elle continue sur sa lancée
  entre deux images du serveur et glisse en douceur (2 fois moins de saccades en test).
- [x] **(fait en 1.5)** Serveur à **60 images par seconde**.
- [x] **(fait en 1.5)** Coop : la balle collée à la raquette de l'autre joueur ne suit plus la
  vôtre (bogue présent depuis la 1.0).
- [x] **(fait en 1.5)** Touche **F3** en ligne : ping, images reçues par seconde, gigue,
  recalages et sauts de balle, pour diagnostiquer une partie qui saccade.
- [ ] **Prédiction complète de la balle** (murs et briques simulés côté joueur) si le jeu
  saccade encore chez certains.
- [ ] N'envoyer que ce qui change, pour réduire le débit si le serveur peine.
- [x] Afficher le **ping** dans le HUD en ligne (vert / orange / rouge) pour savoir d'où vient
  la gêne. Si le ping est élevé, c'est le trajet Internet jusqu'au NAS, pas le jeu.

## Version et mises à jour

- [x] Afficher la version du jeu en bas à droite de l'écran titre.
- [x] Menu **NOUVEAUTES** avec l'historique des versions, chaque version en volet dépliable :
  - les bêtas avant la 1.0 : jalons du jeu solo (moteur, briques spéciales, boss, modes à
    2 joueurs, effets…) ;
  - la 1.0 : jeu en ligne ;
  - la 1.1 : musique, défi, skins…
- [x] Jeu pas à jour + clic sur **EN LIGNE** ou **PARTIES EN LIGNE** : bloquer l'accès et
  proposer **METTRE A JOUR**. Ne pas interrompre une partie solo en cours.
- [x] Serveur injoignable (redémarrage du conteneur) : remplacer le code d'erreur brut affiché
  sur l'écran titre par un message clair (« SERVEUR EN MAINTENANCE, JEU HORS LIGNE ») et se
  reconnecter tout seul quand il revient.
- [ ] (plus tard, facultatif) Mode maintenance côté admin : annoncer une mise à jour, couper
  le jeu en ligne une fois les parties finies.

## Aide et lisibilité

- [x] Refaire l'écran **AIDE**, avec des explications claires sur :
  - **OVERDRIVE** : jauge remplie en cassant des briques, en attrapant des capsules ou en
    touchant un boss. Pleine, elle déclenche la **SUPERNOVA** (MAJ ou clic droit) : 6 s de balle
    de feu qui traverse tout, balle +25 %, et un rayon qui détruit les briques au-dessus de la
    raquette ;
  - **POUVOIRS** : inventaire de 3 places. En solo, 1, 2 ou 3 lancent directement un
    emplacement, et A (ou TAB) + E servent à choisir puis à lancer. À deux, chacun a sa
    touche pour changer et sa touche pour lancer.
- [x] **Explications dans le jeu**, car peu de joueurs ouvrent l'aide :
  - dans le HUD, à côté de l'inventaire, afficher les vraies touches de chaque joueur : 1 2 3,
    « A / TAB : CHOISIR », « E : LANCER » (en solo), et celles de J1 et de J2 à deux ;
  - la première fois qu'on attrape un pouvoir, une bulle explique comment le choisir et le lancer ;
  - la première fois que la jauge OVERDRIVE est pleine, une bulle indique « MAJ / CLIC DROIT : SUPERNOVA » ;
  - ces bulles ne s'affichent qu'une fois (mémorisé dans la sauvegarde) et se réactivent dans OPTIONS.
- [x] Vérifier pourquoi les touches 1 2 3 semblent parfois ne pas répondre
  (pavé numérique, touches au-dessus des lettres en AZERTY sans MAJ).
- [x] **Icônes en pixel art** générées par le jeu pour toutes les capsules : bonus, malus,
  pouvoirs et spéciales. Elles remplacent les lettres, en gardant le code couleur actuel.
  Les mêmes icônes servent dans l'inventaire et dans l'aide.

## Succès (page de profil)

- [x] Clic ou survol à la souris sur un succès : une fiche détaillée s'ouvre (nom complet,
  description, date d'obtention). Aujourd'hui, la fiche n'apparaît qu'avec les flèches.
- [x] Les noms sont coupés sur les tuiles (« EN ROUT… ») : les écrire en entier sur deux lignes.
- [x] Une icône en pixel art par succès (x8, un soleil pour SUNSET, une bombe pour ARTIFICIER…),
  en couleur une fois obtenu, en gris avant.

## Vocabulaire

- [x] « NIVEAU » veut dire deux choses (le niveau du joueur, gagné avec l'XP, et les 12 niveaux de
  la campagne) : c'est trompeur. Renommer le niveau du joueur en **RANG** (« RANG 5 »), partout :
  menu en ligne, profils, liste des joueurs, salon, conditions des skins, notifications.
- [x] Barre d'XP : le texte « 1009 / 1350 XP » (XP totale) ne correspond pas à la barre, qui
  montre la progression dans le rang en cours. Afficher plutôt « 409 / 750 XP AVANT LE RANG 4 ».
- [x] Aperçu des skins : « PROCHAIN : CRYO - NIVEAU 5 » se lit comme « vous êtes niveau 5 ».
  Écrire « CRYO SE DEBLOQUE AU RANG 5 ».

## Difficulté

> Décision de Thomas (25/10) : **on garde la difficulté actuelle**. Un début trop facile
> rendrait le jeu vite ennuyeux. À revoir seulement si les amis bloquent vraiment.

- [ ] Le boss 1 (SUNSET) est déjà très dur : rééquilibrer le monde 1 (moins de tirs, garde plus
  lente) et/ou ajouter une difficulté au choix (FACILE / NORMAL), ainsi qu'une vie de plus
  avant chaque boss.

## Défi du jour

- [x] **Séries (streaks)** : nombre de jours d'affilée où l'on a joué le défi.
  - Profil : série en cours, record de série, historique (calendrier).
  - Classement mondial : onglet « SERIES ».
  - Succès de série : 3, 7 et 30 jours.

## Défi de la semaine, monnaie et boutique

- [x] **Défi de la semaine** (du lundi au dimanche), en plus du défi du jour : un mur plus long et
  deux règles spéciales combinées, avec son propre classement.
- [x] **Séries hebdomadaires** : nombre de semaines d'affilée où l'on a joué le défi de la
  semaine (série en cours et record sur le profil, succès à 4 et 12 semaines).
- [x] **(fait en 2.0)** **Monnaie du jeu**, les **NEONS** : niveaux (10, 20 en Hardcore) et
  boss (50) réussis pour la première fois, étoiles (5), défi du jour (20 + 5 par jour de série),
  défi de la semaine (60), partie en ligne (5) et victoire (15), succès (25), rang (30),
  participation plafonnée à 60 par jour. Cadeau de bienvenue aux anciens joueurs. Solde affiché
  dans le menu EN LIGNE.
- [x] **(fait en 2.1)** Top 3 du jour (50 / 30 / 20) et de la semaine (150 / 100 / 50) payés
  automatiquement par le serveur, avec un message au joueur.
- [x] **(fait en 2.0, 8 skins premium et 3 nouveaux motifs : vagues, étoiles, glitch)**
  **Boutique** (menu EN LIGNE) : des skins **premium**, en plus de ceux qui se débloquent avec
  le rang et les succès, qui ne s'achètent qu'avec des NEONS :
  - motifs animés (plasma, glitch VHS, matrice qui défile, flammes, aurore) ;
  - traînées de particules, étincelles propres au skin quand la balle rebondit ;
  - balle assortie au skin, son de rebond spécial ;
  - des « saisons » : quelques skins disponibles pour un temps limité.
- [x] **(fait en 2.0, sans le rétroactif par niveau : les boss déjà battus sont dans le cadeau)**
  **Gains en campagne** : NEONS à la première réussite de chaque niveau (plus pour les boss :
  SUNSET, GRIDLOCK, CORE). Versement rétroactif pour les niveaux déjà réussis, d'après
  l'historique des parties sur le serveur.
- [x] **(fait en 2.0 : 19 bannières, dont 4 légendaires animées)** **Bannières** affichées
  derrière le pseudo (salon, profil, liste des joueurs, classements). Bannières de boss et
  bannières animées faites en 2.1. Reste à faire :
  - titres (« LE GOAT », « ZEUS », « LE MONSTRE »…).
- [x] **(fait en 2.0)** **Boutique tournante** : 6 objets par jour (2 skins, 4 bannières), dont
  un à -30 %. Les légendaires ne sortent que de la boîte mystère.
- [x] **(fait en 2.0)** **Boîte mystère** (220 NEONS) : un objet au hasard, jamais en double
  (commune 50 %, rare 30 %, épique 15 %, légendaire 5 %).
- [x] **(fait en 2.0)** Côté serveur : solde et objets en base, achats atomiques, gains calculés
  par le serveur.
- [x] **(fait en 2.1)** Historique des mouvements de NEONS (touche H dans la boutique).

## Campagne

- [ ] **Campagne à 2** (la Coop existe déjà, en local et en ligne) : adapter la difficulté au
  nombre de joueurs (vie des boss, cadence de tir, nombre de vies) ; plus tard, campagne à 4
  avec la même règle. À 2, c'est le format le plus facile à remplir.

- [x] **(fait en 2.0, avec 3 étoiles par niveau ; le brouillard reste à faire)** **Carte du
  monde** façon Geometry Dash / carte de jeu de plateforme :
  - un chemin 2D qui relie les niveaux 1, 2, 3… ;
  - un décor illustré pour chaque monde ;
  - le brouillard cache la suite de la carte tant qu'elle n'est pas atteinte ;
  - le curseur se déplace le long du chemin, et les boss sont des étapes spéciales.

## Parties classées (Elo)

- [x] **(fait en 2.0, Duel)** File **CLASSEE** : on rejoint la file et le serveur forme les
  paires par cote proche (l'écart accepté grandit avec l'attente). Abandon = défaite.
- [x] **(fait en 2.0)** Cote **Elo** (1000 au départ, 10 parties de placement).
- [x] **(fait en 2.0)** Divisions BRONZE, ARGENT, OR, PLATINE, NEON ; onglet CLASSEE dans les
  classements mondiaux ; cote sur le profil.
- [x] **(fait en 2.1)** Course classée ; saisons mensuelles (NEONS selon la division, bannières
  GLADIATEUR / TITAN / LEGENDE NEON, cote rapprochée de 1000).

## Duel en ligne

- [x] (fait en 1.4) Aujourd'hui, les deux joueurs voient le même écran : J1 en bas, J2 en haut. **Retourner la vue
  du J2** pour que chacun se voie en bas : on dessine le terrain dans une image à part, retournée
  verticalement, puis on ajoute par-dessus les textes et le HUD à l'endroit. Les commandes
  gauche / droite restent naturelles (le retournement est vertical uniquement).

## Mode 4 joueurs (gros chantier)

- [ ] Terrain carré plus grand, une raquette par côté (bas, haut, gauche, droite), raquettes
  verticales pour les côtés. Chaque joueur voit sa raquette en bas (vue tournée).
- [ ] Variantes : chacun pour soi (chaque côté protège son but, 5 vies chacun) et 2 contre 2.
- [ ] **RAID** (coopératif à 2, 3 ou 4) : tous ensemble contre des boss géants faits pour ça
  (plusieurs phases, attaques qui visent chaque joueur, points faibles à toucher à plusieurs).
- [ ] Le serveur gère déjà les parties ; il faudra passer les salons à 4 places et adapter les
  instantanés, plus un écran d'attente à 4.

## iPhone / iPad (expérimental)

**Alternative plus simple : version navigateur** avec [pygbag](https://pygame-web.github.io/).
Elle fait tourner pygame-ce dans le navigateur (WebAssembly) et serait hébergée par le NAS, sur
la même adresse. On y jouerait depuis Safari sur iPhone et iPad, sans Mac, sans App Store, et
avec une mise à jour automatique.
- Les modes solo se transposent bien. Le jeu en ligne demande d'adapter le client réseau aux
  WebSocket du navigateur (pas de fils d'exécution), et la boucle principale doit passer en asyncio.
- Il faut les mêmes commandes tactiles, et des musiques pré-générées.
- **Icône sur l'écran d'accueil** : avec un manifeste web (PWA), Safari > Partager > « Sur l'écran
  d'accueil » donne une icône qui ouvre le jeu en plein écran, comme une app. Un profil de
  configuration (.mobileconfig avec un « Web Clip ») fait la même chose en un clic, même non
  signé (iOS affiche « non vérifié »). Un profil ne peut contenir qu'un raccourci vers le site,
  pas une vraie app.


Piste : [pygame-ios](https://github.com/seekerluke/pygame-ios). Cet outil place le jeu dans un
projet Xcode qui embarque Python 3.13 et pygame-ce. Il se décrit lui-même comme « pas prêt pour
la production ».

- [ ] Prérequis : un Mac avec Xcode. Les runners macOS de GitHub Actions peuvent aussi fabriquer
  le projet, mais il faut un certificat Apple pour le signer.
- [ ] Distribution :
  - compte Apple gratuit : installation par câble depuis Xcode, l'app expire au bout de 7 jours,
    3 appareils au maximum ;
  - compte développeur à 99 €/an : TestFlight, qui permet d'inviter les amis par lien.
- [ ] **Pas de mise à jour automatique sur iOS** (interdit par Apple) : il faut republier l'app
  à chaque version.
- [ ] numpy (musique) n'a pas de version iOS facile : fournir les musiques en .wav
  pré-générées dans l'app plutôt que de les composer au lancement.
- [ ] Vérifier que la version de pygame-ce est prise en charge par les modèles de pygame-ios
  (le jeu utilise la 2.5.8).
- [ ] Commandes tactiles :
  - la raquette suit le doigt et un tap lance la balle ;
  - boutons à l'écran pour les 3 pouvoirs et la SUPERNOVA ;
  - interface adaptée au format du téléphone (bandes noires ou HUD repensé).
- [ ] Boucle de jeu : passer par `_ios_tick` au lieu de la boucle `while`.
- [ ] Premier essai réaliste : une version « test » installée par câble sur ton iPhone.

## Déjà prévu avant

- [x] **(fait en 2.0)** Commandes configurables, manettes (J1 et J2 sur deux manettes).
- [x] **(fait en 2.0)** Fantôme du meilleur joueur du jour dans les défis.
- [ ] Chat (pas pour l'instant).

## Menus (2.1)

- [x] **(fait en 2.1)** Barre d'onglets (ACCUEIL, JOUER, CLASSEMENTS, CASIER, BOUTIQUE), roue des
  réglages, accueil avec REPRENDRE, carrousel JOUER, CASIER, boutique en vedette.
- [x] **(fait en 2.1)** Skins complets (balle, traînée, son) et bannières de boss.
- [x] **(fait en 2.1)** Mode admin (NEON_ADMINS sur le serveur) et bot de test (F8).
- [ ] Liste d'amis et classement entre amis.
- [x] **(fait, à publier en 2.2)** **Version navigateur pour téléphone et tablette** avec pygbag,
  servie par le serveur du NAS sur `/jeu/` (lien sur la page d'accueil du serveur) :
  - rien à installer : un lien, et « Sur l'écran d'accueil » (comme une app) sur iPhone,
    iPad et Android ;
  - tout le jeu : solo, compte, scores, boutique et jeu en ligne (requêtes et WebSocket
    passent par le JavaScript de la page, voir `moteur/web.py`) ;
  - au doigt : glisser pour bouger, toucher pour lancer, boutons POUVOIRS, SUPERNOVA,
    PAUSE et RETOUR, clavier du téléphone pour le pseudo et le mot de passe ;
  - paysage (message « tourne ton téléphone » en portrait), plein écran sur Android ;
  - sons et musiques fabriqués d'avance en .ogg, sauvegarde dans le navigateur ;
  - moteur Python (pygame-web/archives) copié sur notre serveur : rien chez un tiers ;
  - dessin accéléré (copies compressées RLE, filtre CRT en un calque, halos par bandes) :
    5 fois plus rapide dans le navigateur, et un peu plus rapide sur PC aussi.
- [ ] Version web : à essayer sur un vrai iPhone et un vrai Android (fluidité, son, texte
  assez grand ?). Outils : `/jeu/?profil` (temps par image) et `/jeu/?banc` dans la console.
- [ ] Version web : sauvegarde de la progression sur le compte (sinon chaque appareil a la
  sienne).

## Idées retenues le 26/10 (après la 2.1)

- [ ] **Accessibilité** (dans OPTIONS) :
  - palette pour daltoniens (briques, capsules et pouvoirs distinguables sans la couleur,
    avec les icônes et des motifs) ;
  - flashs réduits (moins de secousses d'écran, d'éclairs et de clignotements) ;
  - texte plus grand dans les menus et le HUD.
- [ ] **Mode spectateur** : depuis la liste des parties en ligne, regarder une partie en
  cours (le serveur envoie déjà les instantanés ; le spectateur ne joue pas et n'est pas compté
  dans la partie). Plus tard : regarder les parties classées des meilleurs joueurs.
- [ ] **Succès à paliers** : bronze, argent et or pour les succès qui comptent quelque chose
  (briques cassées, parties, séries, victoires en ligne…), avec une récompense en NEONS à chaque
  palier. Ajouter des succès pour les nouveautés : classée (première victoire, divisions),
  étoiles de la Campagne, boutique, saisons.

