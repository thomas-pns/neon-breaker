# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Vérifier que les touches 1 2 3 des pouvoirs marchent en AZERTY comme en
    QWERTY, sur la rangée des chiffres et sur le pavé numérique (verrouillage
    numérique actif ou non) : seul le scancode physique compte.

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 23/10/2026
"""

import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from moteur.entrees import Entrees  # noqa: E402

# (scancode, touche logique, caractère) tels que les envoie SDL selon le clavier.
CAS = {
    "pouvoir1": [(pygame.KSCAN_1, pygame.K_AMPERSAND, "&"),     # AZERTY, rangée du haut
                 (pygame.KSCAN_1, pygame.K_1, "1"),              # QWERTY
                 (pygame.KSCAN_KP_1, pygame.K_KP_1, "1"),        # pavé, verr. num. actif
                 (pygame.KSCAN_KP_1, pygame.K_END, "")],         # pavé, verr. num. éteint
    "pouvoir2": [(pygame.KSCAN_2, pygame.K_2, "é"),
                 (pygame.KSCAN_2, pygame.K_2, "2"),
                 (pygame.KSCAN_KP_2, pygame.K_KP_2, "2"),
                 (pygame.KSCAN_KP_2, pygame.K_DOWN, "")],
    "pouvoir3": [(pygame.KSCAN_3, pygame.K_QUOTEDBL, "\""),
                 (pygame.KSCAN_3, pygame.K_3, "3"),
                 (pygame.KSCAN_KP_3, pygame.K_KP_3, "3"),
                 (pygame.KSCAN_KP_3, pygame.K_PAGEDOWN, "")],
}


class TestTouchesPouvoirs(unittest.TestCase):

    def appui(self, scancode, touche, caractere):
        """
        But : simuler l'appui d'une touche sur une image.
        Entrée(s) : scancode (int), touche (int), caractere (str). Sortie : Entrees.
        """
        entrees = Entrees(None)
        entrees.debut_image()
        entrees.traiter(pygame.event.Event(pygame.KEYDOWN, scancode=scancode, key=touche,
                                           unicode=caractere, mod=0))
        return entrees

    def test_rangee_et_pave_en_azerty_et_qwerty(self):
        for action, cas in CAS.items():
            for scancode, touche, caractere in cas:
                with self.subTest(action=action, touche=pygame.key.name(touche)):
                    entrees = self.appui(scancode, touche, caractere)
                    self.assertTrue(entrees.vient_d_appuyer(action, "solo"))
                    autres = {"pouvoir1", "pouvoir2", "pouvoir3"} - {action}
                    self.assertFalse(any(entrees.vient_d_appuyer(a, "solo") for a in autres))

    def test_pave_2_ne_deplace_pas_le_menu(self):
        # Verr. num. éteint, le 2 du pavé envoie la flèche BAS logique : le menu ne doit
        # pas la prendre pour la vraie flèche (scancode différent).
        entrees = self.appui(pygame.KSCAN_KP_2, pygame.K_DOWN, "")
        self.assertFalse(entrees.vient_d_appuyer("bas", "menu"))


if __name__ == "__main__":
    unittest.main()
