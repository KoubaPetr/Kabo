import socket


class Network:
    def __init__(
        self,
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
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_addr = (self.address, self.port)
        self.capacity_message = 2048
        self.id = self.connect()
        print(self.id)

    def connect(self):
        """
        Connect to a server and receive response
        :return:
        """
        try:
            self.client.connect(self.server_addr)
            return self.client.recv(self.capacity_message).decode()
        except:
            pass

    def send(self, data: str):
        """
        Send message to the server and receive response
        :param data: str, message to be sent
        :return:
        """

        try:
            self.client.send(str.encode(data))
            return self.client.recv(self.capacity_message).decode()
        except socket.error as err:
            print(err)


n = Network()
print(n.send("hello"))
print(n.send("world"))
