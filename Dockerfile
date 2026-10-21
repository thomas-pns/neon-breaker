# Serveur NEON BREAKER pour Container Manager (Synology) ou tout Docker.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SDL_VIDEODRIVER=dummy \
    SDL_AUDIODRIVER=dummy \
    PYGAME_HIDE_SUPPORT_PROMPT=1 \
    NEON_DONNEES_SERVEUR=/data \
    NEON_DONNEES=/tmp/neon \
    PUID=1026 \
    PGID=100

WORKDIR /app
COPY serveur/requirements.txt /app/serveur/requirements.txt
RUN pip install --no-cache-dir -r /app/serveur/requirements.txt

# Seuls les modules utiles au serveur (pas d'écrans de menus, pas d'outils).
COPY structures /app/structures
COPY moteur /app/moteur
COPY jeu /app/jeu
COPY reseau /app/reseau
COPY ecrans/__init__.py ecrans/hud.py ecrans/base.py /app/ecrans/
COPY serveur /app/serveur
COPY data/niveaux /app/data/niveaux
COPY outils/entree_docker.sh /entree_docker.sh
RUN chmod +x /entree_docker.sh

EXPOSE 8765
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/sante', timeout=4)"
ENTRYPOINT ["/entree_docker.sh"]
