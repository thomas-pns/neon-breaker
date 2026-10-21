@echo off
REM Lanceur NEON BREAKER : installe pygame-ce si besoin puis lance le jeu.
cd /d "%~dp0"
python -c "import pygame, websockets, certifi" 2>nul || python -m pip install -r requirements.txt
python main.py %*
if errorlevel 1 pause
