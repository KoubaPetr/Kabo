"""
NetworkPlayer - a Player subclass that sends prompts to a remote client
and waits for responses over a socket connection using JSON messages.
"""
import json
import socket
from src.player import Player
from src.round import Round
from src.card import Card
from typing import List, Optional, Type, Tuple, TypeVar

P = TypeVar("P", bound=Player)


class NetworkPlayer(Player):
    """
    Player that communicates with a remote client via JSON over TCP.
    Instead of reading from stdin, it sends requests to the client and
    waits for responses.
    """

    def __init__(self, name: str, conn: socket.socket):
        super().__init__(name, character="NETWORK")
        self.conn = conn
        self._buffer = ""

    def __hash__(self):
        return self.player_id

    def _send(self, msg: dict) -> None:
        """Send a JSON message to the client, length-prefixed."""
        data = json.dumps(msg).encode("utf-8")
        header = len(data).to_bytes(4, "big")
        self.conn.sendall(header + data)

    def _recv(self) -> dict:
        """Receive a length-prefixed JSON message from the client."""
        # Read 4-byte header
        header = b""
        while len(header) < 4:
            chunk = self.conn.recv(4 - len(header))
            if not chunk:
                raise ConnectionError("Client disconnected")
            header += chunk
        msg_len = int.from_bytes(header, "big")

        # Read message body
        data = b""
        while len(data) < msg_len:
            chunk = self.conn.recv(msg_len - len(data))
            if not chunk:
                raise ConnectionError("Client disconnected")
            data += chunk
        return json.loads(data.decode("utf-8"))

    def _hand_info(self) -> List[Optional[int]]:
        """Return hand values visible to this player (None for unknown)."""
        result = []
        for card in self.hand:
            if card.known_to_owner or card.publicly_visible:
                result.append(card.value)
            else:
                result.append(None)
        return result

    def pick_turn_type(self, _round: Round = None) -> str:
        discard_top = _round.discard_pile[-1].value if _round and _round.discard_pile else None
        self._send({
            "type": "your_turn",
            "hand": self._hand_info(),
            "hand_size": len(self.hand),
            "discard_top": discard_top,
        })
        response = self._recv()
        return response["action"]

    def decide_on_card_use(self, card: Card) -> str:
        self._send({
            "type": "decide_card",
            "card_value": card.value,
            "card_effect": card.effect,
            "hand": self._hand_info(),
        })
        response = self._recv()
        return response["choice"]

    def pick_hand_cards_for_exchange(self, drawn_card: Card) -> List[Card]:
        self._send({
            "type": "pick_exchange",
            "drawn_value": drawn_card.value,
            "hand": self._hand_info(),
            "hand_size": len(self.hand),
        })
        response = self._recv()
        positions = response["positions"]
        return [self.hand[p] for p in positions]

    def pick_position_for_new_card(self, available_positions: List[int]) -> Optional[int]:
        if not available_positions:
            return None
        if len(available_positions) == 1:
            return available_positions[0]
        self._send({
            "type": "pick_position",
            "available_positions": available_positions,
        })
        response = self._recv()
        return response["position"]

    def pick_cards_to_see(self, num_cards_to_see: int) -> List[int]:
        self._send({
            "type": "pick_cards_to_see",
            "num_cards": num_cards_to_see,
            "hand": self._hand_info(),
            "hand_size": len(self.hand),
        })
        response = self._recv()
        return response["positions"]

    def specify_spying(self, _round: Round) -> Tuple[Type[P], Card]:
        opponents = [
            {"name": p.name, "hand_size": len(p.hand),
             "hand": [c.value if c.publicly_visible else None for c in p.hand]}
            for p in _round.players if p != self
        ]
        self._send({
            "type": "specify_spy",
            "opponents": opponents,
        })
        response = self._recv()
        opponent = _round.get_player_by_name(response["opponent_name"].upper())
        card = opponent.hand[response["position"]]
        return opponent, card

    def specify_swap(self, _round: Round) -> Tuple[Type[P], int, int]:
        opponents = [
            {"name": p.name, "hand_size": len(p.hand),
             "hand": [c.value if c.publicly_visible else None for c in p.hand]}
            for p in _round.players if p != self
        ]
        self._send({
            "type": "specify_swap",
            "hand": self._hand_info(),
            "opponents": opponents,
        })
        response = self._recv()
        opponent = _round.get_player_by_name(response["opponent_name"].upper())
        return opponent, response["own_position"], response["opponent_position"]

    def report_known_cards_on_hand(self) -> None:
        """Send current hand knowledge to client."""
        self._send({
            "type": "hand_update",
            "hand": self._hand_info(),
        })

    def tell_player_card_value(self, card: Card, effect: str) -> None:
        self._send({
            "type": "card_reveal",
            "effect": effect,
            "card_value": card.value,
        })

    def send_game_event(self, event: dict) -> None:
        """Send a game event notification to the client."""
        self._send(event)
