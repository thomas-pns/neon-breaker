# Délégation aux agents ChatGPT (Codex)

Objectif : économiser les crédits Claude. Claude conçoit, découpe le travail, rédige les
consignes et relit. Les agents Codex écrivent l'essentiel du code.

## Agents disponibles

- `codex1` : compte ChatGPT n°1 (offre Free, limites basses).
- `codex2` : compte ChatGPT n°2.
- Si la commande est introuvable, utiliser le chemin complet : `%USERPROFILE%\.agents-bin\codex1.cmd`
  ou `codex2.cmd`.
- Si un compte renvoie une erreur de limite ou de quota, passer sur l'autre. Si les deux sont
  bloqués, faire la tâche soi-même.

## Commande

Toujours lancer depuis la racine du projet (dépôt git), en redirigeant la sortie pour ne pas
remplir le contexte :

```
codex2 exec --sandbox workspace-write "CONSIGNE" > .delegation/codex2.log 2>&1
```

Ensuite, lire seulement :
1. la fin du log (le résumé de l'agent) ;
2. `git diff --stat` ;
3. les parties du diff qui comptent.

Ne jamais relire en entier un fichier que l'agent vient d'écrire si le diff suffit.
`.delegation/` doit être dans `.gitignore`.

## Quoi déléguer

- Composants, pages, routes d'API, fonctions bien spécifiées.
- Tests, documentation, typage, code répétitif, refactoring mécanique.
- Corrections d'erreurs de lint, de types ou de tests.

## Quoi garder pour Claude

- Architecture, choix techniques, découpage des tâches.
- Débogage difficile, sécurité, logique métier délicate.
- Passe finale sur le rendu visuel et le design web.
- Relecture et commits : les agents ne commitent pas et ne poussent pas.

## Modèle de consigne

```
Contexte : [projet, stack, 2-3 lignes max]
Tâche : [une seule tâche, précise]
Fichiers à créer ou modifier : [liste exacte]
Ne pas toucher : [fichiers ou dossiers]
Conventions : [style, noms, librairies à utiliser ou à éviter]
Terminé quand : [critères vérifiables, ex. "npm test passe", "npm run lint sans erreur"]
Avant de finir : lance [commandes de vérification] et corrige jusqu'à ce que tout passe.
Termine par un résumé de 5 lignes maximum : fichiers modifiés, ce qui a été fait, points d'attention.
Pas de commit, pas de push.
```

## Vérification avant relecture

1. L'agent doit avoir fait passer lui-même les tests, le lint et la vérification des types.
2. Si ça ne passe pas, renvoyer l'erreur à l'agent (2 essais au maximum), puis reprendre la main.
3. Pour le web, si Playwright est disponible, faire une capture d'écran et la regarder plutôt que
   relire tout le CSS.

## Parallélisme

`codex1` et `codex2` peuvent travailler en même temps, mais uniquement sur des fichiers
différents. Pour des tâches qui se chevauchent, utiliser un `git worktree` par agent, ou les
enchaîner.

## Règles

- Ne jamais mettre de mots de passe, de clés d'API ou de secrets dans une consigne.
- Une consigne floue coûte plus cher qu'une consigne précise : prendre 30 secondes de plus pour
  bien l'écrire.

---

## Spécifique à NEON BREAKER

Le contexte complet du projet (architecture, conventions, déploiement, travaux par priorité)
est dans **`docs/CONSIGNE_ORCHESTRATEUR.md`**. Le lire avant la première tâche.

- **Stack** : Python 3.12, pygame-ce 2.5.8, numpy (musique). Serveur : FastAPI, uvicorn,
  SQLite. Code, noms et commentaires en français.
- **Vérification** : ce projet n'a ni lint ni vérification des types, et on n'en ajoute pas.
  Pour le champ « Terminé quand » et pour « Avant de finir », utiliser :
  - `python outils/verifier.py` : tests unitaires et autotest de tous les écrans, sans fenêtre,
    sur Windows comme ailleurs, sans toucher à la vraie sauvegarde ;
  - `python outils/verifier.py --rapide` : tests unitaires seulement.
- **Rendu visuel** (à la place de Playwright) : créer l'écran avec `SDL_VIDEODRIVER=dummy`, faire
  quelques `app._mettre_a_jour(1/60)` et `app._dessiner()`, puis
  `pygame.image.save(app.ecran.image, "capture.png")`, et **regarder** l'image. Les captures vont
  dans `.delegation/`.
- **Branches** : travailler sur `dev/v2-delegation` (ou sur une sous-branche
  `dev/v2-delegation/<tache>` dans un worktree). Ne jamais pousser sur `main`, ne jamais créer
  d'étiquette `v…`, ne jamais lancer un workflow à la main. C'est la fusion dans `main` qui publie
  la mise à jour aux joueurs, et seulement avec l'accord de Thomas.
- **Ne pas toucher sans décision de Claude** : `.github/`, `docker-compose.yml`, `Dockerfile`,
  `moteur/version.py` (`VERSION`, `PROTOCOLE`), `reseau/mise_a_jour.py`, `serveur/base.py`
  (migrations), `outils/construire.py`, `outils/envoyer_build.py`.
- **Dossier `.delegation/`** : le créer s'il n'existe pas (`mkdir .delegation`) avant la première
  redirection.
- **Exe de test pour Thomas** : chaque push sur `dev/**` fabrique un exe Windows
  `X.Y.Z-dev.N`, publié en artefact GitHub (Actions > Exe Windows de test). Cette version a
  sa propre sauvegarde, n'envoie aucun score au vrai serveur et ne se met jamais à jour seule.
