import pygame
from graphics_config import CARD_BACK_IMAGE_PATH_SCRIBBLE

pygame.init()
bounds = (1024, 768)
window = pygame.display.set_mode(bounds)
pygame.display.set_caption("Kabo")

cardBack = pygame.image.load(CARD_BACK_IMAGE_PATH_SCRIBBLE)
cardBack = pygame.transform.scale(cardBack, (int(238 * 0.8), int(332 * 0.8)))


def render_game(window):
    window.fill((15, 169, 0))
    # font = pygame.font.SysFont("arial", 60, True)
    window.blit(cardBack, (100, 200))


pygame.display.update()
render_game(window)
pygame.display.update()
print("wait")
