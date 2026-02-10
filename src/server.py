"""
Game Server - server-authoritative model for LAN multiplayer.
Manages client connections and runs the game logic.
"""
import json
import socket
import threading
from typing import List
from src.game import Game
from src.network_player import NetworkPlayer


class Server:
    def __init__(
        self,
        number_of_clients: int,
        address: str = "127.0.0.1",
        port_num: int = 5555,
    ):
        self.num_clients = number_of_clients
        self.address = address
        self.port = port_num
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.players: List[NetworkPlayer] = []
        self._all_connected = threading.Event()
        self._lock = threading.Lock()
        self.game: Game = None
        self.start_server()

    def _send(self, conn: socket.socket, msg: dict) -> None:
        """Send a length-prefixed JSON message."""
        data = json.dumps(msg).encode("utf-8")
        header = len(data).to_bytes(4, "big")
        conn.sendall(header + data)

    def _recv(self, conn: socket.socket) -> dict:
        """Receive a length-prefixed JSON message."""
        header = b""
        while len(header) < 4:
            chunk = conn.recv(4 - len(header))
            if not chunk:
                raise ConnectionError("Client disconnected")
            header += chunk
        msg_len = int.from_bytes(header, "big")

        data = b""
        while len(data) < msg_len:
            chunk = conn.recv(msg_len - len(data))
            if not chunk:
                raise ConnectionError("Client disconnected")
            data += chunk
        return json.loads(data.decode("utf-8"))

    def start_server(self):
        """Bind, listen, accept connections, then start the game."""
        try:
            self.socket.bind((self.address, self.port))
        except socket.error as err:
            print(f"Server bind error: {err}")
            raise

        self.socket.listen(self.num_clients)
        print(f"Server started on {self.address}:{self.port}")
        print(f"Waiting for {self.num_clients} player(s) to connect...")

        # Accept connections
        while len(self.players) < self.num_clients:
            conn, addr = self.socket.accept()
            print(f"Connection from {addr}")

            try:
                # Handshake: receive player name
                msg = self._recv(conn)
                if msg.get("type") != "join":
                    print(f"Unexpected message from {addr}: {msg}")
                    conn.close()
                    continue

                player_name = msg["name"]
                player_id = len(self.players)

                # Send acknowledgment with player ID
                self._send(conn, {
                    "type": "join_ack",
                    "player_id": player_id,
                    "message": f"Welcome {player_name}! Waiting for other players..."
                })

                # Create NetworkPlayer
                player = NetworkPlayer(player_name, conn)
                with self._lock:
                    self.players.append(player)

                print(f"Player '{player_name}' joined ({len(self.players)}/{self.num_clients})")

            except (ConnectionError, json.JSONDecodeError) as e:
                print(f"Error during handshake with {addr}: {e}")
                conn.close()

        # All players connected - notify them and start the game
        print("All players connected! Starting game...")
        player_names = [p.name for p in self.players]

        for player in self.players:
            player.send_game_event({
                "type": "game_start",
                "num_players": self.num_clients,
                "player_names": player_names,
                "your_name": player.name,
            })

        # Create and run the game
        self.game = Game(players=self.players)
        self.game.play_game()

        # Game over - notify clients
        for player in self.players:
            try:
                player.send_game_event({
                    "type": "game_end",
                    "final_scores": {p.name: p.players_game_score for p in self.players},
                    "winner": min(self.players, key=lambda p: p.players_game_score).name,
                })
            except ConnectionError:
                pass

        # Clean up
        for player in self.players:
            try:
                player.conn.close()
            except OSError:
                pass
        self.socket.close()
        print("Server shut down.")
