"""
Game Client - connects to a Kabo game server, displays GUI, handles user input.
"""
import json
import socket
import sys
from typing import List, Optional


class Client:
    def __init__(
        self,
        player_name: str,
        address: str = "127.0.0.1",
        port_num: int = 5555,
        use_gui: bool = False,
    ):
        self.player_name = player_name
        self.address = address
        self.port = port_num
        self.use_gui = use_gui
        self.running = True
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.gui = None
        self.hand: List[Optional[int]] = []  # known card values (None for unknown)
        self.num_players = 0
        self.player_names: List[str] = []

    def _send(self, msg: dict) -> None:
        """Send a length-prefixed JSON message to the server."""
        data = json.dumps(msg).encode("utf-8")
        header = len(data).to_bytes(4, "big")
        self.socket.sendall(header + data)

    def _recv(self) -> dict:
        """Receive a length-prefixed JSON message from the server."""
        header = b""
        while len(header) < 4:
            chunk = self.socket.recv(4 - len(header))
            if not chunk:
                raise ConnectionError("Server disconnected")
            header += chunk
        msg_len = int.from_bytes(header, "big")

        data = b""
        while len(data) < msg_len:
            chunk = self.socket.recv(msg_len - len(data))
            if not chunk:
                raise ConnectionError("Server disconnected")
            data += chunk
        return json.loads(data.decode("utf-8"))

    def connect(self) -> bool:
        """Connect to the server and perform handshake."""
        try:
            self.socket.connect((self.address, self.port))
            # Send join request
            self._send({"type": "join", "name": self.player_name})
            # Receive acknowledgment
            response = self._recv()
            if response.get("type") == "join_ack":
                print(response.get("message", "Connected!"))
                return True
            print(f"Unexpected response: {response}")
            return False
        except (ConnectionError, socket.error) as e:
            print(f"Connection failed: {e}")
            return False

    def run(self):
        """Main client loop - connect and handle messages."""
        if not self.connect():
            return

        print("Connected to server. Waiting for game to start...")

        try:
            while self.running:
                msg = self._recv()
                self._handle_message(msg)
        except ConnectionError:
            print("Disconnected from server.")
        except KeyboardInterrupt:
            print("\nDisconnected.")
        finally:
            self.socket.close()

    def _handle_message(self, msg: dict):
        """Route incoming server messages to the appropriate handler."""
        msg_type = msg.get("type")
        handler = {
            "game_start": self._on_game_start,
            "your_turn": self._on_your_turn,
            "decide_card": self._on_decide_card,
            "pick_exchange": self._on_pick_exchange,
            "pick_position": self._on_pick_position,
            "pick_cards_to_see": self._on_pick_cards_to_see,
            "specify_spy": self._on_specify_spy,
            "specify_swap": self._on_specify_swap,
            "hand_update": self._on_hand_update,
            "card_reveal": self._on_card_reveal,
            "game_end": self._on_game_end,
        }.get(msg_type)

        if handler:
            handler(msg)
        else:
            print(f"Unknown message type: {msg_type}")

    def _on_game_start(self, msg: dict):
        self.num_players = msg["num_players"]
        self.player_names = msg["player_names"]
        print(f"Game starting with {self.num_players} players: {', '.join(self.player_names)}")

    def _on_hand_update(self, msg: dict):
        self.hand = msg["hand"]
        hand_display = [str(v) if v is not None else "?" for v in self.hand]
        print(f"Your hand: {hand_display}")

    def _on_card_reveal(self, msg: dict):
        effect = msg["effect"]
        value = msg["card_value"]
        if effect == "PEAK":
            print(f"Peeked card value: {value}")
        else:
            print(f"Spied card value: {value}")

    def _on_your_turn(self, msg: dict):
        hand_display = [str(v) if v is not None else "?" for v in msg["hand"]]
        print(f"\n--- YOUR TURN ---")
        print(f"Your hand: {hand_display}")
        if msg.get("discard_top") is not None:
            print(f"Discard pile top: {msg['discard_top']}")

        while True:
            action = input("Choose: KABO / HIT_DECK / HIT_DISCARD_PILE\n").strip().upper()
            if action in ("KABO", "HIT_DECK", "HIT_DISCARD_PILE"):
                self._send({"action": action})
                return
            print("Invalid choice.")

    def _on_decide_card(self, msg: dict):
        value = msg["card_value"]
        effect = msg.get("card_effect")
        hand_display = [str(v) if v is not None else "?" for v in msg["hand"]]
        print(f"Your hand: {hand_display}")

        if effect:
            prompt = f"Drawn card: {value} ({effect}). Choose: KEEP / DISCARD / EFFECT\n"
            valid = ("KEEP", "DISCARD", "EFFECT")
        else:
            prompt = f"Drawn card: {value}. Choose: KEEP / DISCARD\n"
            valid = ("KEEP", "DISCARD")

        while True:
            choice = input(prompt).strip().upper()
            if choice in valid:
                self._send({"choice": choice})
                return
            print(f"Invalid choice. Options: {valid}")

    def _on_pick_exchange(self, msg: dict):
        hand_display = [str(v) if v is not None else "?" for v in msg["hand"]]
        hand_size = msg["hand_size"]
        print(f"Your hand: {hand_display}")
        print(f"Drawn card value: {msg['drawn_value']}")

        while True:
            positions_str = input(
                f"Pick card position(s) to exchange (0 to {hand_size - 1}, space-separated):\n"
            ).strip()
            try:
                positions = [int(p) for p in positions_str.split()]
                if all(0 <= p < hand_size for p in positions) and positions:
                    self._send({"positions": positions})
                    return
                print(f"Positions must be in range 0 to {hand_size - 1}.")
            except ValueError:
                print("Enter integers separated by spaces.")

    def _on_pick_position(self, msg: dict):
        available = msg["available_positions"]
        if len(available) == 1:
            self._send({"position": available[0]})
            return

        while True:
            pos_str = input(f"Pick position for new card. Available: {available}\n").strip()
            try:
                pos = int(pos_str)
                if pos in available:
                    self._send({"position": pos})
                    return
                print(f"Must be one of {available}.")
            except ValueError:
                print("Enter an integer.")

    def _on_pick_cards_to_see(self, msg: dict):
        num = msg["num_cards"]
        hand_size = msg["hand_size"]
        hand_display = [str(v) if v is not None else "?" for v in msg["hand"]]
        print(f"Your hand: {hand_display}")

        while True:
            positions_str = input(
                f"Pick {num} card position(s) to look at (0 to {hand_size - 1}):\n"
            ).strip()
            try:
                positions = [int(p) for p in positions_str.split()]
                if len(positions) == num and all(0 <= p < hand_size for p in positions):
                    self._send({"positions": positions})
                    return
                print(f"Select exactly {num} valid position(s).")
            except ValueError:
                print("Enter integers separated by spaces.")

    def _on_specify_spy(self, msg: dict):
        opponents = msg["opponents"]
        opp_names = [o["name"] for o in opponents]
        print(f"Opponents: {opp_names}")
        for opp in opponents:
            hand_display = [str(v) if v is not None else "?" for v in opp["hand"]]
            print(f"  {opp['name']}: {hand_display}")

        while True:
            name = input(f"Spy on which opponent? {opp_names}\n").strip().upper()
            if name in opp_names:
                break
            print(f"Invalid name. Choose from {opp_names}.")

        opponent = next(o for o in opponents if o["name"] == name)
        while True:
            pos_str = input(f"Which card position? (0 to {opponent['hand_size'] - 1})\n").strip()
            try:
                pos = int(pos_str)
                if 0 <= pos < opponent["hand_size"]:
                    self._send({"opponent_name": name, "position": pos})
                    return
                print(f"Position must be 0 to {opponent['hand_size'] - 1}.")
            except ValueError:
                print("Enter an integer.")

    def _on_specify_swap(self, msg: dict):
        opponents = msg["opponents"]
        opp_names = [o["name"] for o in opponents]
        hand_display = [str(v) if v is not None else "?" for v in msg["hand"]]
        print(f"Your hand: {hand_display}")
        print(f"Opponents: {opp_names}")
        for opp in opponents:
            opp_hand = [str(v) if v is not None else "?" for v in opp["hand"]]
            print(f"  {opp['name']}: {opp_hand}")

        hand_size = len(msg["hand"])
        while True:
            own_str = input(f"Your card position to swap (0 to {hand_size - 1}):\n").strip()
            try:
                own_pos = int(own_str)
                if 0 <= own_pos < hand_size:
                    break
                print(f"Position must be 0 to {hand_size - 1}.")
            except ValueError:
                print("Enter an integer.")

        while True:
            name = input(f"Swap with which opponent? {opp_names}\n").strip().upper()
            if name in opp_names:
                break
            print(f"Invalid name.")

        opponent = next(o for o in opponents if o["name"] == name)
        while True:
            opp_str = input(f"Opponent's card position (0 to {opponent['hand_size'] - 1}):\n").strip()
            try:
                opp_pos = int(opp_str)
                if 0 <= opp_pos < opponent["hand_size"]:
                    self._send({
                        "own_position": own_pos,
                        "opponent_name": name,
                        "opponent_position": opp_pos,
                    })
                    return
                print(f"Position must be 0 to {opponent['hand_size'] - 1}.")
            except ValueError:
                print("Enter an integer.")

    def _on_game_end(self, msg: dict):
        print("\n" + "=" * 50)
        print("GAME OVER!")
        scores = msg["final_scores"]
        for name, score in sorted(scores.items(), key=lambda x: x[1]):
            print(f"  {name}: {score} points")
        print(f"Winner: {msg['winner']}!")
        print("=" * 50)
        self.running = False
