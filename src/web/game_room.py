"""
GameRoom - manages a multiplayer lobby and shared game session.

Players create or join rooms via short codes. When the host starts the game,
a shared GameSession runs with one WebPlayer per browser and optional AI players.
"""
import random
import string
import threading
from typing import Dict, List, Optional

from src.web.event_bus import EventBus
from src.web.game_state import GameStateSnapshot, InputRequest


class GameRoom:
    """A multiplayer game room that holds player slots and manages shared game state."""

    def __init__(self, room_code: str, host_name: str,
                 max_players: int = 4, ai_count: int = 0):
        self.room_code = room_code
        self.host_name = host_name.upper()
        self.max_players = max_players
        self.ai_count = ai_count
        self.state = "waiting"  # waiting, playing, finished
        # Player slots: upper-cased name -> {"event_bus": EventBus, "web_player": None}
        self.players: Dict[str, dict] = {}
        self.session = None
        self._lock = threading.Lock()

    def add_player(self, name: str, event_bus: EventBus) -> None:
        """Add a human player to the room."""
        uname = name.upper()
        with self._lock:
            if self.state != "waiting":
                raise ValueError("Game already started")
            if len(self.players) >= self.max_players:
                raise ValueError("Room is full")
            if uname in self.players:
                raise ValueError(f"Name '{uname}' is already taken")
            self.players[uname] = {"event_bus": event_bus, "web_player": None}

    def remove_player(self, name: str) -> None:
        """Remove a player from the room."""
        uname = name.upper()
        with self._lock:
            self.players.pop(uname, None)

    def reconnect_player(self, name: str, new_event_bus: EventBus) -> None:
        """Re-wire a player's EventBus after a browser refresh."""
        uname = name.upper()
        with self._lock:
            if uname not in self.players:
                raise ValueError(f"Player '{uname}' not in room")
            self.players[uname]["event_bus"] = new_event_bus
            wp = self.players[uname].get("web_player")
            if wp:
                wp.set_event_bus(new_event_bus)

    def get_all_event_buses(self) -> List[EventBus]:
        """Return all connected EventBuses."""
        with self._lock:
            return [info["event_bus"] for info in self.players.values()
                    if info["event_bus"] is not None]

    def get_player_names(self) -> List[str]:
        """Return list of connected player names."""
        with self._lock:
            return list(self.players.keys())

    def is_full(self) -> bool:
        return len(self.players) >= self.max_players

    def total_player_count(self) -> int:
        """Total players including AI."""
        return len(self.players) + self.ai_count

    def broadcast_log(self, message: str) -> None:
        """Send a log message to all connected players."""
        for bus in self.get_all_event_buses():
            try:
                bus.emit("log", message)
            except Exception:
                pass

    def broadcast_game_over(self, data=None) -> None:
        """Send game_over to all connected players."""
        for bus in self.get_all_event_buses():
            try:
                bus.emit("game_over", data)
            except Exception:
                pass

    def broadcast_state_to_others(self, active_player_name: str, _round) -> None:
        """Push a 'waiting' state snapshot to all non-active players.

        Each non-active WebPlayer builds its own perspective snapshot, then
        we attach a 'waiting' InputRequest and emit to that player's EventBus.
        """
        with self._lock:
            others = {name: info for name, info in self.players.items()
                      if name != active_player_name}

        for name, info in others.items():
            wp = info.get("web_player")
            bus = info.get("event_bus")
            if wp and bus and _round:
                try:
                    state = wp._build_state_snapshot(_round)
                    state.active_turn_player_name = active_player_name
                    state.input_request = InputRequest(
                        request_type="waiting",
                        prompt=f"Waiting for {active_player_name}'s turn...",
                        options=[],
                    )
                    bus.emit("state_update", state)
                    bus.emit("input_request", state.input_request)
                except Exception as e:
                    print(f"[GameRoom] Error broadcasting to {name}: {e}")

    def start_game(self):
        """Create WebPlayers, ComputerPlayers, and start the shared GameSession."""
        from src.web.game_session import GameSession

        with self._lock:
            if self.state != "waiting":
                raise ValueError("Game already started")
            self.state = "playing"

        self.session = GameSession.from_room(self)
        return self.session


# --- Module-level room registry ---

_rooms: Dict[str, GameRoom] = {}
_rooms_lock = threading.Lock()


def _generate_code(length: int = 5) -> str:
    """Generate a unique room code."""
    chars = string.ascii_uppercase + string.digits
    while True:
        code = "".join(random.choices(chars, k=length))
        if code not in _rooms:
            return code


def create_room(host_name: str, max_players: int = 4,
                ai_count: int = 0) -> GameRoom:
    """Create a new room and add the host as the first player."""
    with _rooms_lock:
        code = _generate_code()
        room = GameRoom(code, host_name, max_players, ai_count)
        _rooms[code] = room
    return room


def join_room(code: str, player_name: str,
              event_bus: EventBus) -> GameRoom:
    """Join an existing room."""
    with _rooms_lock:
        room = _rooms.get(code.upper())
    if not room:
        raise ValueError("Room not found")
    room.add_player(player_name, event_bus)
    return room


def get_room(code: str) -> Optional[GameRoom]:
    """Look up a room by code."""
    with _rooms_lock:
        return _rooms.get(code.upper())


def remove_room(code: str) -> None:
    """Remove a room from the registry."""
    with _rooms_lock:
        _rooms.pop(code.upper(), None)
