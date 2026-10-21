# Mettre NEON BREAKER en ligne (NAS Synology + GitHub)

Ce guide se suit une seule fois, dans l'ordre. Compter environ 30 minutes.
Dans les exemples, remplacez :

- `votre-nom.synology.me` par votre nom DDNS Synology ;
- le dépôt GitHub est `thomas-pns/neon-breaker`.

Le jeu sera joignable à l'adresse `https://neon.votre-nom.synology.me`.

```
Joueurs ──HTTPS 443──► Box ──► DSM (proxy inversé) ──► conteneur neon-serveur :8765
                                                         └── /volume1/docker/neon-breaker/data
GitHub Actions ──(exécutables, par morceaux)──► même adresse
```

---

## 1. Préparer un jeton secret

Ce jeton autorise GitHub à envoyer les exécutables à votre NAS. Générez-en un, une seule fois :

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Gardez-le de côté : il servira à l'étape 2 (GitHub) et à l'étape 4 (Container Manager).

## 2. GitHub

1. Le dépôt **public** `neon-breaker` contient le code (je l'y envoie dès que vous me donnez accès).
2. **Settings > Secrets and variables > Actions** :
   - onglet **Secrets**, *New repository secret* : nom `NEON_JETON_DEPLOIEMENT`, valeur = le jeton de l'étape 1 ;
   - onglet **Variables**, *New repository variable* : nom `NEON_SERVEUR_URL`, valeur = `https://neon.votre-nom.synology.me`.
3. **Actions** : vérifiez que le workflow **Serveur (image Docker)** est passé au vert. Il publie l'image `ghcr.io/thomas-pns/neon-breaker`.
4. Rendez cette image publique, pour que le NAS puisse la télécharger sans mot de passe :
   page du dépôt > **Packages** (colonne de droite) > `neon-breaker` > **Package settings** > **Change visibility** > **Public**.

## 3. Certificat HTTPS pour le sous-domaine

DSM > **Panneau de configuration > Sécurité > Certificat**.

- Si votre certificat Let's Encrypt `votre-nom.synology.me` couvre déjà `*.votre-nom.synology.me` (le détail du certificat l'indique), passez à l'étape 4.
- Sinon : **Ajouter > Remplacer un certificat existant** > choisissez celui de `votre-nom.synology.me` > **Se procurer un certificat auprès de Let's Encrypt**.
  - Nom de domaine : `votre-nom.synology.me` ;
  - Autre nom de l'objet : `*.votre-nom.synology.me`.

## 4. Container Manager

1. **File Station** : dans le dossier partagé `docker`, créez le dossier `neon-breaker`.
2. **Container Manager > Projet > Créer** :
   - Nom du projet : `neon-breaker` ;
   - Chemin : `/docker/neon-breaker` ;
   - Source : **Créer docker-compose.yml**, puis collez le contenu du fichier `docker-compose.yml` du dépôt.
3. Dans le texte collé, remplacez la valeur « À CHANGER » : `NEON_JETON_DEPLOIEMENT` = le jeton de l'étape 1.
4. Si votre utilisateur DSM n'est pas le premier créé, adaptez `PUID` / `PGID`. Pour les connaître : `id` en SSH ; la valeur par défaut est 1026 / 100.
5. **Suivant**, puis **Terminé**. Le conteneur `neon-serveur` démarre.

Vérification depuis un PC de la maison : `http://IP-DU-NAS:8765/api/sante` doit afficher `{"ok":true,...}`.

## 5. Proxy inversé

DSM > **Panneau de configuration > Portail de connexion > Avancé > Proxy inversé > Créer** :

| Champ | Valeur |
|---|---|
| Description | `neon-breaker` |
| Source : protocole | HTTPS |
| Source : nom d'hôte | `neon.votre-nom.synology.me` |
| Source : port | 443 |
| Destination : protocole | HTTP |
| Destination : nom d'hôte | `localhost` |
| Destination : port | 8765 |

Puis onglet **En-tête personnalisé > Créer > WebSocket**. Cela ajoute deux lignes `Upgrade` et `Connection`, indispensables aux parties en ligne. Enregistrez.

> Le port 443 de votre box pointe déjà vers le NAS (pour votre site) : il n'y a **rien à ouvrir de plus**. N'ouvrez surtout pas le port 8765 sur la box.

Vérification depuis un téléphone en 4G : `https://neon.votre-nom.synology.me` affiche la page NEON BREAKER (encore sans téléchargement).

## 6. Première version des exécutables

Sur votre PC, dans le dépôt :

```bash
git tag v1.0.0
git push --tags
```

GitHub > **Actions > Exécutables** : trois fabrications (Windows, Mac Apple, Mac Intel), environ 10 minutes. Chacune fabrique l'exécutable, le teste (autotest de tous les écrans) et l'envoie au NAS.
La page `https://neon.votre-nom.synology.me` propose alors les trois téléchargements : c'est le lien à envoyer à vos amis.

## 7. Mises à jour

| Quoi | Comment |
|---|---|
| Le jeu | Nouvelle étiquette : `git tag v1.0.1 && git push --tags`. Au lancement suivant, le jeu de chaque ami propose **METTRE A JOUR**, se télécharge, se remplace et redémarre. |
| Le serveur | Chaque envoi sur `main` publie une nouvelle image. Container Manager > **Projet > neon-breaker > Action > Construire** récupère la dernière version (`pull_policy: always`). |
| Les succès | Ils sont définis dans `serveur/succes.py` : une mise à jour du serveur suffit, le jeu des joueurs affiche ce que le serveur envoie. |

Si les messages réseau changent de format, j'augmente `PROTOCOLE` dans `moteur/version.py`. Les anciens jeux voient alors « MISE A JOUR NECESSAIRE » en ligne, mais restent jouables hors ligne.

## 8. Administration

Container Manager > **Conteneur > neon-serveur > Action > Ouvrir le terminal > Créer** (bash), puis :

```bash
python -m serveur.admin lister                 # tous les joueurs
python -m serveur.admin reset-mdp PSEUDO       # mot de passe provisoire à donner à l'ami
python -m serveur.admin reset-mdp PSEUDO neon2026   # ... ou celui que vous choisissez
python -m serveur.admin bannir PSEUDO
python -m serveur.admin debannir PSEUDO
python -m serveur.admin supprimer PSEUDO       # efface le compte et ses parties
```

Les mots de passe sont chiffrés (scrypt) : personne, vous compris, ne peut les lire dans la base.

## 9. Sauvegarde

**Hyper Backup** : ajoutez le dossier `docker/neon-breaker/data`. Il contient toute la base (`neon.sqlite3`) et les exécutables.

## 10. En cas de problème

| Symptôme | Piste |
|---|---|
| « SERVEUR INJOIGNABLE » dans le jeu | `https://neon.votre-nom.synology.me/api/sante` répond-il ? Sinon, vérifiez la règle de proxy inversé et le certificat. |
| La connexion marche mais les parties en ligne ne se lancent pas | Il manque l'en-tête **WebSocket** dans la règle de proxy inversé (étape 5). |
| Le conteneur redémarre en boucle | Container Manager > Conteneur > neon-serveur > **Journal**. Erreur « Permission denied » sur /data : corrigez `PUID` / `PGID`. |
| Le workflow Exécutables échoue à l'envoi | Vérifiez la variable `NEON_SERVEUR_URL` et que le secret `NEON_JETON_DEPLOIEMENT` est identique à celui du NAS. |
| Windows : « Windows a protégé votre ordinateur » | Normal sans signature payante : **Informations complémentaires > Exécuter quand même**. |
| Mac : « impossible de vérifier le développeur » | **Clic droit > Ouvrir**, la première fois seulement. Sinon : Réglages Système > Confidentialité et sécurité > **Ouvrir quand même**. |
| Un ami a oublié son mot de passe | `python -m serveur.admin reset-mdp SON_PSEUDO` (étape 8). |

## Jouer depuis le code source (sans exécutable)

```bash
pip install -r requirements.txt
NEON_SERVEUR=https://neon.votre-nom.synology.me python main.py
```

Sans cette variable, l'écran de connexion propose de saisir l'adresse du serveur.
