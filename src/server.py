import socket
import _thread
from typing import List
from src.game import Game


class Server:
    def __init__(
        self,
        number_of_clients: int,
        address: str = "192.168.0.104",
        port_num: int = 5555,
    ):
        """
        Initialize server
        :param number_of_clients:
        :param address:
        :param port_num:
        """
        self.num_clients = number_of_clients
        self.address = address
        self.port = port_num
        self.socket = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM
        )  # TODO: what are these arguments
        self.receive_data_limit = 2048
        self.encoding = "utf-8"
        self.client_names: List[str] = []
        self.game: Game = None
        self.start_server()

    def set_game(self, game: Game):
        """
        Setter to assign game to a server
        :param game:
        :return:
        """
        self.game = game
        print("Game was set up for the server")

    def threaded_client(self, connected_socket):
        """

        :param connected_socket: connection of a new client
        :return:
        """
        connected_socket.send(len(self.client_names))
        connected_player_name: str = connected_socket.recv(self.receive_data_limit)
        print("message_received by the server {}".format(connected_player_name))
        if connected_player_name not in self.client_names:
            decoded_name: str = connected_player_name.decode()
            self.client_names.append(decoded_name)
        else:
            raise ValueError(
                f"Player {connected_player_name} already exists on the server!"
            )

        reply = ""
        while True:
            try:
                clients_message = connected_socket.recv(self.receive_data_limit)
                clients_message = clients_message.decode(self.encoding)
                if not clients_message:
                    print("Disconected")
                    break
                elif clients_message == "Init me":
                    init_state: str = (
                        "{}".format()
                    )  # TODO: format number of players and discard pile top card (this needs access to round)
                else:
                    print("Received: ", reply)
                    print("Sending: ", reply)
                connected_socket.sendall(str.encode(reply, encoding=self.encoding))
            except:
                break

        print("Lost connection")
        connected_socket.close()

    def start_server(self):
        """
        Bind the port and start listening for connections
        :return:
        """
        try:
            self.socket.bind((self.address, self.port))
        except socket.error as err:
            str(err)  # TODO: is this correct handling?

        self.socket.listen(self.num_clients)
        print("Waiting for connection, Server Started")

        while True:
            ### If enough players joined, start the game
            if len(self.client_names) == self.num_clients:
                game = Game(
                    {p: "HUMAN" for p in self.client_names}, using_gui=True
                )  ###TODO: Is this now in the correct thread?
                self.set_game(game=game)
                self.game.play_game()  # starting the game!

            connected_socket, client_addr = self.socket.accept()
            print("Connected to: ", client_addr)

            _thread.start_new_thread(self.threaded_client, (connected_socket,))
