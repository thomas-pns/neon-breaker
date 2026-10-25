# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Séries (« streaks ») des défis, partagées par le jeu et le serveur :
    nombre de jours d'affilée où l'on a joué le défi du jour, et de semaines
    d'affilée pour le défi de la semaine. Une série « en cours » reste
    valable tant que le dernier défi joué date d'aujourd'hui ou d'hier
    (de cette semaine ou de la précédente).

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 25/10/2026
"""

import datetime


def id_semaine(date):
    """But : identifiant ISO d'une semaine, ex. « 2026-W43 ». Entrée : date. Sortie : (str)."""
    annee, semaine, _ = date.isocalendar()
    return f"{annee}-W{semaine:02d}"


def lundi_de(identifiant):
    """But : date du lundi d'une semaine « AAAA-Www » (None si invalide)."""
    try:
        annee, semaine = identifiant.split("-W")
        return datetime.date.fromisocalendar(int(annee), int(semaine), 1)
    except (ValueError, AttributeError):
        return None


def _jour(texte):
    try:
        return datetime.date.fromisoformat(str(texte)[:10])
    except ValueError:
        return None


def _dates(elements, semaines):
    convertir = lundi_de if semaines else _jour
    return sorted({d for d in (convertir(e) for e in elements) if d is not None})


def record(elements, semaines=False):
    """
    But : plus longue série de jours (ou de semaines) consécutifs.
    Entrées : elements (itérable de « AAAA-MM-JJ » ou « AAAA-Www ») ; semaines (bool).
    Sortie : (int).
    """
    pas = 7 if semaines else 1
    meilleur = courant = 0
    precedente = None
    for date in _dates(elements, semaines):
        courant = courant + 1 if precedente and (date - precedente).days == pas else 1
        meilleur = max(meilleur, courant)
        precedente = date
    return meilleur


def en_cours(elements, aujourd_hui, semaines=False):
    """
    But : série en cours, encore valable si le dernier défi date d'aujourd'hui ou
    d'hier (de cette semaine ou de la précédente).
    Entrées : elements ; aujourd_hui (date) ; semaines (bool). Sortie : (int).
    """
    pas = 7 if semaines else 1
    dates = _dates(elements, semaines)
    if not dates:
        return 0
    reference = lundi_de(id_semaine(aujourd_hui)) if semaines else aujourd_hui
    if (reference - dates[-1]).days > pas:
        return 0
    serie = 1
    for plus_recente, precedente in zip(reversed(dates), list(reversed(dates))[1:]):
        if (plus_recente - precedente).days != pas:
            break
        serie += 1
    return serie


def resume(elements, aujourd_hui, semaines=False):
    """But : {"en_cours", "record"} d'une liste de défis joués."""
    return {"en_cours": en_cours(elements, aujourd_hui, semaines),
            "record": record(elements, semaines)}
