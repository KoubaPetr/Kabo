import pygame
from graphics_config import (
    CARD_BACK_IMAGE_PATH_SCRIBBLE,
    BOUNDS,
    BACKGROUND_COLOR,
    CAPTION,
    CARD_WIDTH,
    CARD_HEIGHT,
)

pygame.init()


class GUI:
    def __init__(self):
        self.bounds = BOUNDS
        self.window = pygame.display.set_mode(self.bounds)
        self.cardBack = pygame.image.load(CARD_BACK_IMAGE_PATH_SCRIBBLE)
        self.cardBack = pygame.transform.scale(self.cardBack, (CARD_WIDTH, CARD_HEIGHT))
        pygame.display.set_caption(CAPTION)

    def render_game(self):
        self.window.fill(BACKGROUND_COLOR)
        # font = pygame.font.SysFont("arial", 60, True)
        self.window.blit(self.cardBack, (100, 200))  # back of the Main deck
        # TODO: render discard pile and players cards, conditioned upon their visibility

    def update_screen(self):
        self.render_game(self.window)
        pygame.display.update()
