import pygame
import socket
from typing import Tuple, List
from src.gui import GUI


class Client:
    def __init__(
        self,
        player_name: str,
        address: str = "192.168.0.104",
        port_num: int = 5555,
    ):
        self.player_name: str = player_name
        self.run: bool = True
        self.address: str = address  # confusing naming? See address vs addr
        self.port: int = port_num
        self.clock = pygame.time.Clock()
        self.ticking_unit: int = 60
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_addr: Tuple[str, int] = (self.address, self.port)
        self.capacity_message: int = 2048
        self.id: int = int(self.connect())  # receives return message
        print("Client ID = {}".format(self.id))
        self.send_to_server(data=self.player_name)
        self.init_setup: dict = self.ask_for_init_game_setup()
        self.gui = GUI(self.init_setup["num_players"], self.init_setup["discard_pile"])
        # TODO: Continue interacting with the GUI + change the GUI class so that it doesnt use Players nor Game and only uses messages
        # TODO: Check that we dont need the Card Ids as these might get mixed up by creating new cards for each GUI
        # TODO: as part of the init, should we tell the client what cards were drawn? - try without this, the image can be loaded upon getting info from server
        # TODO: run client loop

    def connect(self):
        """
        Connect to a server and receive response
        :return:
        """
        try:
            self.client_socket.connect(self.server_addr)
            return self.client_socket.recv(self.capacity_message).decode()
        except:
            pass

    def send_to_server(self, data: str):
        """
        Send message to the server and receive response
        :param data: str, message to be sent
        :return:
        """

        try:
            print("Message sent to server  = {}".format(data))
            self.client_socket.send(str.encode(data))
            return self.client_socket.recv(self.capacity_message).decode()
        except socket.error as err:
            print(err)

    def ask_for_init_game_setup(self):
        """
        Ask the server how many players there are and what is the initial card at discard pile
        :return:
        """
        init_setup_message: str = self.send_to_server("Init me")
        init_setup_message_split: List[str] = init_setup_message.split()
        decoded_init_setup: dict = {
            "num_players": int(init_setup_message_split[0]),
            "discard_pile": int(init_setup_message_split[1]),
        }
        return decoded_init_setup

    def client_loop(self):

        while self.run:
            self.clock.tick(self.ticking_unit)

            for event in pygame.event.get():  # TODO: listen to events
                if event.type == pygame.QUIT:
                    run = False
                    pygame.quit()

            # TODO: REDRAW PLAYERS GUI FROM HERE
