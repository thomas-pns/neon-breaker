# -*- coding: utf-8 -*-
"""(Outil) Banc d'essai des opérations de dessin, pour la version web (?banc)."""

import time

import pygame


def mesurer(nom, fonction, fois=20):
    debut = time.perf_counter()
    for _ in range(fois):
        fonction()
    return f"  {nom:<46} {(time.perf_counter() - debut) / fois * 1000:7.2f} ms"


def banc():
    L, H = 1280, 720
    image = pygame.Surface((L, H))
    image.fill((40, 10, 60))
    alpha = pygame.Surface((L, H), pygame.SRCALPHA)
    alpha.fill((0, 0, 0, 60))
    opaque = pygame.Surface((L, H))
    opaque.fill((200, 200, 200))
    alpha_cvt = alpha.convert_alpha() if pygame.display.get_surface() else alpha
    opaque_alpha = opaque.copy()
    opaque_alpha.set_alpha(60)
    rle = alpha.copy()
    bande = pygame.Surface((L, 1))
    bande.fill((200, 200, 200))
    montagne = pygame.Surface((L, 170), pygame.SRCALPHA)
    pygame.draw.polygon(montagne, (14, 4, 40, 255), [(300, 170), (500, 20), (900, 60), (1100, 170)])
    pygame.draw.line(montagne, (0, 200, 255, 200), (300, 170), (500, 20), 2)
    montagne_rle = montagne.copy()
    montagne_rle.set_alpha(255, pygame.RLEACCEL)
    montagne_ck = pygame.Surface((L, 170))
    montagne_ck.fill((255, 0, 255))
    pygame.draw.polygon(montagne_ck, (14, 4, 40), [(300, 170), (500, 20), (900, 60), (1100, 170)])
    montagne_ck.set_colorkey((255, 0, 255), pygame.RLEACCEL)
    texte = pygame.Surface((300, 40), pygame.SRCALPHA)
    pygame.draw.rect(texte, (255, 0, 200, 255), (10, 10, 200, 20))
    texte_rle = texte.copy()
    texte_rle.set_alpha(255, pygame.RLEACCEL)
    def cadre(rle, coins=True):
        c = pygame.Surface((760, 690))
        c.fill((255, 0, 255))
        pygame.draw.rect(c, (10, 0, 26), c.get_rect(), border_radius=12 if coins else 0)
        if coins:
            c.set_colorkey((255, 0, 255), pygame.RLEACCEL if rle else 0)
        c.set_alpha(205, pygame.RLEACCEL if rle else 0)
        return c
    cadre_ck, cadre_rle, cadre_simple = cadre(False), cadre(True), cadre(False, False)
    cadre_simple_rle = cadre(True, False)
    lignes = [
        "NEON BANC",
        mesurer("cadre 760x690 alpha uniforme", lambda: image.blit(cadre_simple, (0, 0))),
        mesurer("cadre alpha uniforme + RLE", lambda: image.blit(cadre_simple_rle, (0, 0))),
        mesurer("cadre colorkey + alpha", lambda: image.blit(cadre_ck, (0, 0))),
        mesurer("cadre colorkey + alpha + RLE", lambda: image.blit(cadre_rle, (0, 0))),
        mesurer("montagne SRCALPHA", lambda: image.blit(montagne, (0, 300))),
        mesurer("montagne SRCALPHA + RLEACCEL", lambda: image.blit(montagne_rle, (0, 300))),
        mesurer("montagne colorkey + RLEACCEL", lambda: image.blit(montagne_ck, (0, 300))),
        mesurer("texte 300x40 SRCALPHA x20", lambda: [image.blit(texte, (0, 0)) for _ in range(20)]),
        mesurer("texte 300x40 RLEACCEL x20", lambda: [image.blit(texte_rle, (0, 0)) for _ in range(20)]),
        mesurer("blit SRCALPHA plein ecran", lambda: image.blit(alpha, (0, 0))),
        mesurer("blit SRCALPHA convert_alpha", lambda: image.blit(alpha_cvt, (0, 0))),
        mesurer("blit opaque plein ecran", lambda: image.blit(opaque, (0, 0))),
        mesurer("blit opaque + set_alpha", lambda: image.blit(opaque_alpha, (0, 0))),
        mesurer("blit BLEND_RGB_MULT plein ecran",
                lambda: image.blit(opaque, (0, 0), special_flags=pygame.BLEND_RGB_MULT)),
        mesurer("blit BLEND_RGB_ADD plein ecran",
                lambda: image.blit(opaque, (0, 0), special_flags=pygame.BLEND_RGB_ADD)),
        mesurer("fill BLEND_RGB_MULT plein ecran",
                lambda: image.fill((200, 200, 200), special_flags=pygame.BLEND_RGB_MULT)),
        mesurer("240 fill MULT d'une ligne", lambda: [
            image.fill((200, 200, 200), (0, y, L, 1), special_flags=pygame.BLEND_RGB_MULT)
            for y in range(0, H, 3)]),
        mesurer("240 blit MULT d'une bande", lambda: [
            image.blit(bande, (0, y), special_flags=pygame.BLEND_RGB_MULT)
            for y in range(0, H, 3)]),
        mesurer("fill plein ecran", lambda: image.fill((10, 2, 30))),
        mesurer("copy plein ecran", lambda: image.copy()),
        mesurer("smoothscale 1280->640", lambda: pygame.transform.smoothscale(image, (640, 360))),
        mesurer("scale 640->1280", lambda: pygame.transform.scale(
            pygame.Surface((640, 360)), (L, H))),
        mesurer("draw.line x100 epaisseur 2", lambda: [
            pygame.draw.line(image, (255, 0, 255), (0, i * 7), (L, i * 7), 2) for i in range(100)]),
    ]
    return "\n".join(lignes)
