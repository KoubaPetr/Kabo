import socket


class Network:
    def __init__(
        self,
        player_name: str,
        address: str = "192.168.0.104",
        port_num: int = 5555,
    ):
        """
        Initialize Network
        :param address:
        :param port_num:
        """
        self.address = address  # confusing naming? See address vs addr
        self.port = port_num
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_addr = (self.address, self.port)
        self.capacity_message = 2048
        self.id = self.connect()  # receives return message - right now "Connected"
        self.send_to_server(data=player_name)
        print(self.id)

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
            self.client_socket.send(str.encode(data))
            return self.client_socket.recv(self.capacity_message).decode()
        except socket.error as err:
            print(err)
