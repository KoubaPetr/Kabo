import socket
import _thread
from typing import List
import sys


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
        self.start_server()
        self.client_names: List[str] = []

    def threaded_client(self, conn):
        """

        :param conn: connection of a new client
        :return:
        """
        conn.send(str.encode("Connected", encoding=self.encoding))
        connected_player_name: str = conn.recv(self.receive_data_limit)

        if connected_player_name not in self.client_names:
            self.client_names.append(connected_player_name)
        else:
            raise ValueError(
                f"Player {connected_player_name} already exists on the server!"
            )

        reply = ""
        while True:
            try:
                data = conn.recv(self.receive_data_limit)
                reply = data.decode(self.encoding)
                if not data:
                    print("Disconected")
                    break
                else:
                    print("Received: ", reply)
                    print("Sending: ", reply)
                conn.sendall(str.encode(reply, encoding=self.encoding))
            except:
                break

        print("Lost connection")
        conn.close()

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
            conn, addr = self.socket.accept()
            print("Connected to: ", addr)

            _thread.start_new_thread(self.threaded_client, (conn,))
