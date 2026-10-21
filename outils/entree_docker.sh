#!/bin/sh
# Démarrage du conteneur : le dossier /data (monté depuis le NAS) appartient
# à l'utilisateur DSM (PUID/PGID). On lui donne ce dossier, puis on lance le
# serveur SANS droits administrateur.
set -e
mkdir -p /data /tmp/neon
chown -R "${PUID}:${PGID}" /data /tmp/neon
exec setpriv --reuid="${PUID}" --regid="${PGID}" --clear-groups python -m serveur
