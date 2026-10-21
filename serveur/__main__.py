# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Lancer le serveur : python -m serveur
    (dans le conteneur Docker, ou en local pour les tests avec
    NEON_DONNEES_SERVEUR=./donnees_serveur).

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 21/10/2026
"""

import logging
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import uvicorn  # noqa: E402

from serveur import config  # noqa: E402

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    uvicorn.run("serveur.api:app", host="0.0.0.0", port=config.PORT, proxy_headers=True,
                forwarded_allow_ips="*", ws_ping_interval=20, ws_ping_timeout=20,
                log_level="info")
