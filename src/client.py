import pygame
from src.network import Network


class Client:
    def __init__(self):
        self.run = True
        self.network = Network()
        self.clock = pygame.time.Clock()
        self.ticking_unit = 60

    def client_loop(self):

        while self.run:
            self.clock.tick(self.ticking_unit)

            for event in pygame.event.get():  # TODO: listen to events
                if event.type == pygame.QUIT:
                    run = False
                    pygame.quit()

            # TODO: REDRAW PLAYERS GUI FROM HERE
