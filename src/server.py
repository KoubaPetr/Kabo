import socket
import _thread
import threading
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
        # self.lock = threading.Lock()
        self.start_server()

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
            connected_socket, client_addr = self.socket.accept()
            print("Connected to: ", client_addr)
            # self.lock.acquire()
            _thread.start_new_thread(self.threaded_client, (connected_socket,))

            """
            
            Description of current issue: here the self.client_names seem to not get updated, 
            when it is updated from the new thread (when second player is added there, 
            here is still just one, and it falls behind by one player) How to synchronize the threads the best?
            
            => the Game does not get initialized here when both players join
            
            """
            ### If enough players joined, start the game
            print(
                "client names = {} num_clients = {}".format(
                    self.client_names, self.num_clients
                )
            )
            if len(self.client_names) == self.num_clients:
                print("Starting game")
                game = Game(
                    {p: "HUMAN" for p in self.client_names}, using_gui=True
                )  ###TODO: Is this now in the correct thread?
                self.set_game(game=game)
                self.game.play_game()  # starting the game!

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
        player_id_encoded: str = str(len(self.client_names)).encode(
            encoding=self.encoding
        )
        print(player_id_encoded)
        connected_socket.send(player_id_encoded)
        connected_player_name: str = connected_socket.recv(self.receive_data_limit)
        print("message_received by the server {}".format(connected_player_name))
        connected_socket.send(
            "Welcome in the game {}".format(connected_player_name).encode(self.encoding)
        )
        if connected_player_name not in self.client_names:
            decoded_name: str = connected_player_name.decode()
            self.client_names.append(decoded_name)
            print("client_names from threaded client are {}".format(self.client_names))
            # self.lock.release()
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
                    dont_break: bool = self.handle_init_message(
                        clients_message=clients_message,
                        connected_socket=connected_socket,
                    )
                    if not dont_break:
                        break
                elif ...:  # handle further messages here
                    pass
                else:
                    raise ValueError("Unexpected message from the client")

            except Exception as e:
                print(e)
                break

        print("Lost connection")
        connected_socket.close()

    def handle_init_message(
        self, clients_message: str, connected_socket: socket.socket
    ) -> bool:
        """

        :param clients_message: expected message "Init me"
        :param connected_socket: socket for communication
        :return: bool whether to continue to while loop
        """
        if not clients_message:
            print("Disconected")
            return False
        elif clients_message == "Init me":
            _waiting: bool = True
            while _waiting:
                if self.game and self.game.rounds and self.game.rounds[-1].discard_pile:
                    init_state: str = "{} {}".format(
                        self.game.num_players,
                        self.game.rounds[-1].discard_pile[-1].value,
                    )
                    connected_socket.sendall(
                        str.encode(init_state, encoding=self.encoding)
                    )
                    _waiting = False
                else:
                    pass
            return True
        else:
            print("Unexpected message from the client")
            return False
