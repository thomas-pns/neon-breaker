# -*- coding: utf-8 -*-
"""
Objectifs du fichier :
    Hiérarchie des briques (reprise de la version Tkinter) : classe de base
    Brique, puis BriqueNormale, BriqueSolide (plusieurs coups, fissures) et
    BriqueMetal (indestructible, reflet chromé). Chaque brique sait se
    dessiner en néon et réagir à un coup (flash, tremblement).

Par :
    Thomas CHASSANIS PONS et Camil BOUZIRI (refonte avec Claude)

Réalisé le 20/10/2026

ToDo List:
    Explosive, Bonus, Mobile, Régénérante, Fantôme, Portail (jalon 2).
"""

import math
import random

import pygame

from moteur import config
from moteur.rendu import halo_rect, attenuer, melanger


class Brique:
    """
    Classe de base des briques du jeu.
    Attributs :
        x, y : coin supérieur gauche (pixels, l'axe y est orienté vers le bas).
        largeur, hauteur : dimensions (pixels).
        vie, vie_max : coups restants / coups au départ.
        points : points attribués à la destruction.
        couleur : couleur néon de base.
        destructible (bool) : False pour le métal (ne compte pas pour la victoire).
        flash (float) : intensité du flash blanc après un coup (0..1).
        secousse (float) : petite vibration après un coup (px).
    """

    destructible = True     # compte pour la victoire
    solide = True           # False : la balle la traverse (portail)
    explosive = False       # détruit ses voisines en mourant
    capsule_garantie = False
    regenerante = False
    morte = False           # True une fois retirée du terrain

    def __init__(self, x, y, largeur, hauteur, vie, points, couleur):
        """
        But : initialiser une brique.
        Entrées :
            x, y (float) : position du coin supérieur gauche.
            largeur, hauteur (int) : dimensions.
            vie (int) : coups nécessaires pour la détruire.
            points (int) : points gagnés à la destruction.
            couleur (tuple) : couleur néon RVB.
        Sortie : aucune.
        """
        self.x = x
        self.y = y
        self.largeur = largeur
        self.hauteur = hauteur
        self.vie = vie
        self.vie_max = vie
        self.points = points
        self.couleur = couleur
        self.flash = 0.0
        self.secousse = 0.0
        self.apparition = 0.0          # animation d'entrée (0 -> 1)
        self.delai_apparition = 0.0

    # --- Logique (reprise de la version Tkinter) ---------------------------

    def est_detruite(self):
        """
        But : indiquer si la brique n'a plus de vie.
        Entrée : aucune.
        Sortie : (bool) True si vie <= 0, False sinon.
        """
        return self.vie <= 0

    def frapper(self, puissance=1, feu=False):
        """
        But : appliquer un coup de balle à la brique.
        Entrées : puissance (int) : nombre de points de vie retirés ;
                  feu (bool) : coup d'une balle de feu (fait fondre le métal).
        Sortie : (bool) True si la brique est détruite par ce coup.
        """
        self.flash = 1.0
        self.secousse = 3.0
        self.vie -= puissance
        return self.est_detruite()

    def couleur_actuelle(self):
        """
        But : donner la couleur d'affichage (redéfinie si elle dépend de la vie).
        Entrée : aucune.
        Sortie : (tuple) couleur RVB.
        """
        return self.couleur

    def obtenir_boite(self):
        """
        But : fournir le rectangle englobant, utile aux tests de collision.
        Entrée : aucune.
        Sortie : (tuple) (x_min, y_min, x_max, y_max).
        """
        return (self.x, self.y, self.x + self.largeur, self.y + self.hauteur)

    def rect(self):
        """
        But : rectangle pygame de la brique.
        Entrée : aucune. Sortie : (pygame.Rect).
        """
        return pygame.Rect(int(self.x), int(self.y), self.largeur, self.hauteur)

    # --- Animation et dessin ----------------------------------------------

    def mettre_a_jour(self, dt):
        """
        But : faire décroître flash et secousse, jouer l'apparition.
        Entrée : dt (float) secondes. Sortie : aucune.
        """
        self.flash = max(0.0, self.flash - dt * 5)
        self.secousse = max(0.0, self.secousse - dt * 25)
        if self.delai_apparition > 0:
            self.delai_apparition -= dt
        elif self.apparition < 1:
            self.apparition = min(1.0, self.apparition + dt * 4)

    def _rect_affiche(self):
        """Rectangle animé (apparition qui tombe en place + vibration)."""
        dx = random.uniform(-self.secousse, self.secousse) if self.secousse else 0
        chute = (1 - self._lisser(self.apparition)) * -40
        return pygame.Rect(int(self.x + dx), int(self.y + chute),
                           self.largeur, self.hauteur)

    @staticmethod
    def _lisser(t):
        """Courbe « rebond » pour l'apparition (dépasse un peu puis revient)."""
        return 1 - (1 - t) ** 3 + math.sin(t * math.pi) * 0.08

    def dessiner(self, image, temps):
        """
        But : dessiner la brique en néon : halo, intérieur sombre teinté,
        contour lumineux, reflet en haut, flash blanc après un coup.
        Entrées : image (Surface), temps (float) : horloge pour les animations.
        Sortie : aucune.
        """
        if self.apparition <= 0:
            return
        couleur = self.couleur_actuelle()
        rect = self._rect_affiche()
        lueur = halo_rect(self.largeur, self.hauteur, attenuer(couleur, 0.55),
                          rayon=6)
        image.blit(lueur, (rect.x - 12, rect.y - 12),
                   special_flags=pygame.BLEND_RGB_ADD)
        interieur = melanger(config.INTERIEUR, couleur, 0.28)
        pygame.draw.rect(image, interieur, rect, border_radius=3)
        # Bande claire en haut : effet de volume.
        image.fill(melanger(interieur, couleur, 0.45),
                   (rect.x + 3, rect.y + 3, rect.w - 6, 4))
        pygame.draw.rect(image, couleur, rect, 2, border_radius=3)
        self.dessiner_details(image, rect, couleur, temps)
        if self.flash > 0:
            blanc = attenuer(config.BLANC, self.flash)
            image.fill(blanc, rect, special_flags=pygame.BLEND_RGB_ADD)

    def dessiner_details(self, image, rect, couleur, temps):
        """
        But : détails propres à chaque type (fissures, reflets...).
        Entrées : image, rect, couleur, temps. Sortie : aucune.
        """

    def __str__(self):
        """
        But : représentation textuelle pour le débogage.
        Entrée : aucune.
        Sortie : (str) description de la brique.
        """
        return (f"{type(self).__name__}(vie={self.vie}, "
                f"points={self.points}, couleur={self.couleur})")


class BriqueNormale(Brique):
    """Brique détruite en un coup."""

    def __init__(self, x, y, largeur, hauteur, couleur):
        super().__init__(x, y, largeur, hauteur, vie=1, points=10,
                         couleur=couleur)


class BriqueSolide(Brique):
    """
    Brique à plusieurs coups : des fissures apparaissent et sa couleur
    pâlit à chaque coup encaissé.
    """

    def __init__(self, x, y, largeur, hauteur, couleur, vie=2):
        super().__init__(x, y, largeur, hauteur, vie=vie, points=25 * vie,
                         couleur=couleur)
        aleatoire = random.Random(int(x * 31 + y * 17))
        # Fissures pré-tirées (en coordonnées relatives) pour rester stables.
        self.fissures = [[(aleatoire.uniform(0.2, 0.8), aleatoire.uniform(0, 1))
                          for _ in range(4)] for _ in range(3)]

    def couleur_actuelle(self):
        """Plus la brique est abîmée, plus sa couleur tire vers le blanc."""
        degats = 1 - self.vie / self.vie_max
        return melanger(self.couleur, (255, 230, 255), degats * 0.6)

    def dessiner_details(self, image, rect, couleur, temps):
        """Double contour intérieur + fissures selon les dégâts."""
        pygame.draw.rect(image, attenuer(couleur, 0.7), rect.inflate(-8, -8), 1,
                         border_radius=2)
        nb_fissures = self.vie_max - self.vie
        for fissure in self.fissures[:nb_fissures]:
            points = [(rect.x + fx * rect.w, rect.y + fy * rect.h)
                      for fx, fy in fissure]
            pygame.draw.lines(image, config.BLANC, False, points, 1)


class BriqueMetal(Brique):
    """Brique indestructible : la balle rebondit dessus avec un son métallique."""

    destructible = False

    def __init__(self, x, y, largeur, hauteur):
        super().__init__(x, y, largeur, hauteur, vie=1, points=0,
                         couleur=config.GRIS_METAL)

    def frapper(self, puissance=1, feu=False):
        """Le métal encaisse sans casser, sauf face au feu qui le fait fondre."""
        self.flash = 0.6
        self.secousse = 1.5
        if feu:
            self.vie = 0
            self.points = 50
            return True
        return False

    def dessiner_details(self, image, rect, couleur, temps):
        """Rivets et reflet qui balaie la brique de temps en temps."""
        for coin_x in (rect.x + 5, rect.right - 6):
            image.fill((220, 225, 245), (coin_x, rect.centery - 1, 2, 2))
        cycle = (temps * 0.6 + rect.x * 0.002) % 1.0
        if cycle < 0.25:
            position = rect.x + cycle / 0.25 * (rect.w + 20) - 10
            for i in range(4):
                x = int(position + i)
                if rect.x + 2 < x < rect.right - 4:
                    pygame.draw.line(image, (240, 245, 255),
                                     (x, rect.y + 3), (x - 4, rect.bottom - 4))


class BriqueExplosive(Brique):
    """Brique rouge pulsante : en explosant, elle endommage ses 8 voisines."""

    explosive = True

    def __init__(self, x, y, largeur, hauteur):
        super().__init__(x, y, largeur, hauteur, vie=1, points=30,
                         couleur=config.ROUGE)

    def couleur_actuelle(self):
        return config.ROUGE

    def dessiner_details(self, image, rect, couleur, temps):
        """Cœur qui pulse et petit symbole de danger."""
        pulse = 0.5 + 0.5 * math.sin(temps * 8 + rect.x * 0.05)
        coeur = rect.inflate(-rect.w * 0.55, -10)
        image.fill(attenuer((255, 140, 60), 0.4 + 0.6 * pulse), coeur,
                   special_flags=pygame.BLEND_RGB_ADD)
        cx, cy = rect.center
        pygame.draw.polygon(image, (255, 230, 120),
                            [(cx, cy - 6), (cx - 6, cy + 5), (cx + 6, cy + 5)], 1)


class BriqueBonus(Brique):
    """Brique scintillante « ? » : lâche toujours une capsule."""

    capsule_garantie = True

    def __init__(self, x, y, largeur, hauteur):
        super().__init__(x, y, largeur, hauteur, vie=1, points=20,
                         couleur=config.OR)

    def dessiner_details(self, image, rect, couleur, temps):
        """Point d'interrogation et étincelles qui tournent."""
        from moteur.police_pixel import dessiner_texte
        dessiner_texte(image, "?", rect.centerx, rect.centery, 2, config.BLANC,
                       lueur=False, ombre=False)
        angle = temps * 5 + rect.x
        for k in range(2):
            a = angle + k * math.pi
            x = rect.centerx + math.cos(a) * rect.w * 0.42
            y = rect.centery + math.sin(a) * rect.h * 0.35
            image.fill(config.BLANC, (int(x), int(y), 2, 2))


class BriqueMobile(Brique):
    """
    Brique qui glisse de gauche à droite entre deux bornes (calculées par
    le terrain selon la place libre sur sa ligne).
    """

    def __init__(self, x, y, largeur, hauteur, couleur=config.CYAN):
        super().__init__(x, y, largeur, hauteur, vie=1, points=30,
                         couleur=couleur)
        self.x_min = x
        self.x_max = x
        self.vitesse = 90.0

    def mettre_a_jour(self, dt):
        super().mettre_a_jour(dt)
        if self.x_max - self.x_min < 2:
            return
        self.x += self.vitesse * dt
        if self.x <= self.x_min:
            self.x = self.x_min
            self.vitesse = abs(self.vitesse)
        elif self.x >= self.x_max:
            self.x = self.x_max
            self.vitesse = -abs(self.vitesse)

    def dessiner_details(self, image, rect, couleur, temps):
        """Petites flèches dans le sens du mouvement."""
        sens = 1 if self.vitesse > 0 else -1
        cy = rect.centery
        for k in (-8, 4):
            x = rect.centerx + k * sens
            pygame.draw.lines(image, config.BLANC, False,
                              [(x, cy - 4), (x + 4 * sens, cy), (x, cy + 4)], 2)


class BriqueRegenerante(Brique):
    """Brique verte : revient 6 s après sa destruction si une sœur survit."""

    regenerante = True

    def __init__(self, x, y, largeur, hauteur):
        super().__init__(x, y, largeur, hauteur, vie=1, points=15,
                         couleur=config.VERT)

    def dessiner_details(self, image, rect, couleur, temps):
        """Battement de cœur : une ligne d'électrocardiogramme."""
        phase = (temps * 1.4) % 1.0
        x0, cy = rect.x + 6, rect.centery
        points = [(x0, cy), (x0 + 12, cy), (x0 + 16, cy - 6), (x0 + 20, cy + 5),
                  (x0 + 24, cy), (rect.right - 6, cy)]
        lumiere = 1.0 if phase < 0.25 else 0.5
        pygame.draw.lines(image, attenuer((200, 255, 210), lumiere), False,
                          points, 1)


class BriqueFantome(Brique):
    """
    Brique invisible : le premier coup la révèle, le second la détruit.
    Un léger scintillement trahit sa présence de temps en temps.
    """

    def __init__(self, x, y, largeur, hauteur):
        super().__init__(x, y, largeur, hauteur, vie=2, points=40,
                         couleur=(200, 200, 255))
        self.revelee = False

    def frapper(self, puissance=1, feu=False):
        self.revelee = True
        return super().frapper(puissance, feu)

    def dessiner(self, image, temps):
        if self.revelee:
            super().dessiner(image, temps)
            return
        # Invisible : simple scintillement ponctuel des coins.
        if math.sin(temps * 1.7 + self.x * 0.13 + self.y * 0.07) > 0.93:
            rect = self.rect()
            for coin in (rect.topleft, rect.bottomright):
                image.fill((120, 120, 200), (coin[0], coin[1] - 1, 3, 3))


class BriquePortail(Brique):
    """
    Portail : la balle le traverse et ressort par le portail jumeau avec
    la même vitesse. Indestructible et ne compte pas pour la victoire.
    """

    destructible = False
    solide = False

    def __init__(self, x, y, largeur, hauteur):
        super().__init__(x, y, largeur, hauteur, vie=1, points=0,
                         couleur=config.VIOLET)
        self.jumeau = None

    def frapper(self, puissance=1, feu=False):
        return False

    def dessiner(self, image, temps):
        if self.apparition <= 0:
            return
        rect = self.rect()
        couleur = config.VIOLET if (id(self) // 16) % 2 else config.CYAN
        for k in range(3):
            phase = (temps * 1.5 + k / 3) % 1.0
            ellipse = rect.inflate(-rect.w * phase * 0.8, -rect.h * phase * 0.8)
            pygame.draw.ellipse(image, attenuer(couleur, 1 - phase), ellipse, 2)
        lueur = halo_rect(self.largeur, self.hauteur, attenuer(couleur, 0.5),
                          rayon=6)
        image.blit(lueur, (rect.x - 12, rect.y - 12),
                   special_flags=pygame.BLEND_RGB_ADD)


class BriqueGarde(BriqueNormale):
    """Brique invoquée par un boss : se casse, mais ne compte pas pour la victoire."""

    destructible = False


class BriqueGardeSolide(BriqueSolide):
    """Version solide (2 coups) des briques de garde."""

    destructible = False


# Code réseau de chaque type (pour recréer les briques chez les clients).
CODES_TYPES = {BriqueNormale: "n", BriqueSolide: "s", BriqueMetal: "M",
               BriqueExplosive: "X", BriqueBonus: "?", BriqueMobile: ">",
               BriqueRegenerante: "H", BriqueFantome: "*", BriquePortail: "P",
               BriqueGarde: "g", BriqueGardeSolide: "G"}
TYPES_PAR_CODE = {code: classe for classe, code in CODES_TYPES.items()}


def code_type(brique):
    """But : code réseau d'une brique. Sortie : (str) un caractère."""
    return CODES_TYPES.get(type(brique), "n")


def creer_depuis_code(code, x, y, largeur, hauteur, couleur, vie_max=1):
    """
    But : recréer une brique à partir de son code réseau (jeu en ligne).
    Entrées : code (str), x, y, largeur, hauteur, couleur (tuple), vie_max (int).
    Sortie : (Brique).
    """
    classe = TYPES_PAR_CODE.get(code, BriqueNormale)
    if classe in (BriqueNormale, BriqueGarde):
        brique = classe(x, y, largeur, hauteur, couleur)
    elif classe in (BriqueSolide, BriqueGardeSolide):
        brique = classe(x, y, largeur, hauteur, couleur, vie=vie_max)
    elif classe is BriqueMobile:
        brique = classe(x, y, largeur, hauteur, couleur)
    else:
        brique = classe(x, y, largeur, hauteur)
    brique.couleur = couleur
    return brique


# --- Fabrique : caractère du fichier de niveau -> brique -------------------

COULEURS_LETTRES = {
    "a": config.AMBRE, "r": config.ROSE, "v": config.VIOLET,
    "b": config.BLEU, "c": config.CYAN, "o": config.OR, "g": config.VERT,
}


def fabriquer_brique(caractere, x, y, largeur=config.BRIQUE_L,
                     hauteur=config.BRIQUE_H):
    """
    But : créer la brique correspondant à un caractère de niveau.
        minuscule (a r v b c o g) : brique normale de cette couleur ;
        majuscule (A R V B C O G) : brique solide 2 coups ;
        chiffre 3 à 5 : brique solide 3 à 5 coups (couleur violette à ambre) ;
        M : métal ; X : explosive ; ? : bonus ; < ou > : mobile ;
        H : régénérante ; * : fantôme ; P : portail ; . ou espace : vide.
    Entrées : caractere (str), x, y (float), largeur, hauteur (int).
    Sortie : (Brique ou None).
    """
    if caractere in COULEURS_LETTRES:
        return BriqueNormale(x, y, largeur, hauteur, COULEURS_LETTRES[caractere])
    if caractere.lower() in COULEURS_LETTRES and caractere.isupper():
        return BriqueSolide(x, y, largeur, hauteur,
                            COULEURS_LETTRES[caractere.lower()], vie=2)
    if caractere in "345":
        vie = int(caractere)
        couleur = {3: config.VIOLET, 4: config.ROSE, 5: config.AMBRE}[vie]
        return BriqueSolide(x, y, largeur, hauteur, couleur, vie=vie)
    speciales = {"M": BriqueMetal, "X": BriqueExplosive, "?": BriqueBonus,
                 "H": BriqueRegenerante, "*": BriqueFantome,
                 "P": BriquePortail}
    if caractere in speciales:
        return speciales[caractere](x, y, largeur, hauteur)
    if caractere in "<>":
        brique = BriqueMobile(x, y, largeur, hauteur)
        brique.vitesse = -90.0 if caractere == "<" else 90.0
        return brique
    return None
