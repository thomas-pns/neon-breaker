# Serveur NEON BREAKER pour Container Manager (Synology) ou tout Docker.

# --- Étape 1 : version navigateur (pygbag), servie par le serveur sur /jeu/ ---------------
FROM python:3.12-slim AS web
# Moteur Python du navigateur : copie figée de github.com/pygame-web/archives.
ARG ARCHIVES_COMMIT=5ab484fcee674a99492cceb7bf3340239da63d7a
RUN apt-get update && apt-get install -y --no-install-recommends git ffmpeg \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pygbag==0.9.3 numpy==2.3.4 pygame-ce==2.5.8
RUN git init -q /archives && cd /archives \
    && git remote add origin https://github.com/pygame-web/archives \
    && git fetch -q --depth 1 --filter=blob:none origin "$ARCHIVES_COMMIT" \
    && git sparse-checkout set --no-cone '/0.9/*' '!/0.9/pkpy14/' '!/0.9/cpython313/' \
       '/repo/index-090-cp312.json' '/repo/repodata.json' '/repo/cp312/pygame_static-*' \
    && git checkout -q FETCH_HEAD
WORKDIR /src
ENV SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYGAME_HIDE_SUPPORT_PROMPT=1
COPY main.py /src/
COPY structures /src/structures
COPY moteur /src/moteur
COPY jeu /src/jeu
COPY ecrans /src/ecrans
COPY reseau /src/reseau
COPY data /src/data
COPY web /src/web
COPY outils/__init__.py outils/construire_web.py outils/banc_web.py /src/outils/
RUN python outils/construire_web.py --moteur /archives --sortie /web

# --- Étape 2 : le serveur ---------------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SDL_VIDEODRIVER=dummy \
    SDL_AUDIODRIVER=dummy \
    PYGAME_HIDE_SUPPORT_PROMPT=1 \
    NEON_DONNEES_SERVEUR=/data \
    NEON_DONNEES=/tmp/neon \
    NEON_WEB=/app/web \
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
COPY --from=web /web /app/web
COPY outils/entree_docker.sh /entree_docker.sh
RUN chmod +x /entree_docker.sh

EXPOSE 8765
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/sante', timeout=4)"
ENTRYPOINT ["/entree_docker.sh"]
