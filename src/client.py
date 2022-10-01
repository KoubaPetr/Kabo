import pygame
from src.network import Network


class Client:
    def __init__(self, player_name: str):
        self.player_name = player_name
        self.run = True
        self.network = Network(player_name=player_name)
        self.clock = pygame.time.Clock()
        self.ticking_unit = 60
        self.network.send_to_server(self.player_name)  # send your name to the server

    def ask_for_init_game_setup(self):
        pass

    def client_loop(self):

        while self.run:
            self.clock.tick(self.ticking_unit)

            for event in pygame.event.get():  # TODO: listen to events
                if event.type == pygame.QUIT:
                    run = False
                    pygame.quit()

            # TODO: REDRAW PLAYERS GUI FROM HERE
