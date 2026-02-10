"""
GameSession - manages a game running in a background thread.

Creates players, runs Game.play_game() in a daemon thread, and captures
print output via PrintInterceptor so it appears in the browser log.

Supports both single-player (solo vs AI) and multiplayer (room-based) modes.
"""
import io
import sys
import threading
from typing import List, Optional

from src.card import Card
from src.game import Game
from src.web.event_bus import EventBus
from src.web.web_player import WebPlayer
from src.computer_player import ComputerPlayer


class PrintInterceptor(io.TextIOBase):
    """Captures writes to stdout and forwards them to both the original
    stdout and one or more EventBuses as log events."""

    def __init__(self, original_stdout, event_buses: List[EventBus]):
        self._original = original_stdout
        self._event_buses = event_buses

    def write(self, text: str) -> int:
        if text and text.strip():
            for bus in self._event_buses:
                try:
                    bus.emit("log", text.strip())
                except Exception:
                    pass
        self._original.write(text)
        return len(text)

    def flush(self):
        self._original.flush()

    def fileno(self):
        return self._original.fileno()


class GameSession:
    """Manages a single game session for the web UI."""

    def __init__(self, player_name: str, ai_count: int, event_bus: EventBus):
        self.event_bus = event_bus
        self.player_name = player_name
        self.ai_count = ai_count
        self.web_player: Optional[WebPlayer] = None
        self.game: Optional[Game] = None
        self._thread: Optional[threading.Thread] = None
        self._finished = False
        self._all_event_buses: List[EventBus] = [event_bus]
        self._room = None

    def start(self) -> WebPlayer:
        """Create players and start the game in a background thread."""
        # Create the web player
        self.web_player = WebPlayer(self.player_name)
        self.web_player.set_event_bus(self.event_bus)

        # Create AI players
        players = [self.web_player]
        for i in range(self.ai_count):
            players.append(ComputerPlayer(f"AI_{i + 1}"))

        # Reset counters for fresh game
        Card.reset_id_counter()
        from src.player import Player
        Player.reset_id_counter()
        from src.round import Round
        Round.reset_id_counter()

        # Create game with pre-built players
        self.game = Game(players=players)

        # Start game in a daemon thread
        self._thread = threading.Thread(target=self._run_game, daemon=True)
        self._thread.start()

        return self.web_player

    @classmethod
    def from_room(cls, room) -> "GameSession":
        """Create a GameSession for a multiplayer room.

        Creates WebPlayers for each human player and ComputerPlayers for AI,
        then starts the game thread.
        """
        session = cls.__new__(cls)
        session.event_bus = None
        session.player_name = None
        session.ai_count = room.ai_count
        session.web_player = None
        session.game = None
        session._thread = None
        session._finished = False
        session._room = room

        players = []
        all_event_buses = []

        # Create WebPlayers for each human in the room
        for name, info in room.players.items():
            wp = WebPlayer(name)
            wp.set_event_bus(info["event_bus"])
            wp.set_room(room)
            info["web_player"] = wp
            players.append(wp)
            all_event_buses.append(info["event_bus"])

        session._all_event_buses = all_event_buses

        # Create AI players
        for i in range(room.ai_count):
            players.append(ComputerPlayer(f"AI_{i + 1}"))

        # Reset counters for fresh game
        Card.reset_id_counter()
        from src.player import Player
        Player.reset_id_counter()
        from src.round import Round
        Round.reset_id_counter()

        # Create game with pre-built players
        session.game = Game(players=players)

        # Start game in a daemon thread
        session._thread = threading.Thread(
            target=session._run_game, daemon=True
        )
        session._thread.start()

        return session

    def _run_game(self) -> None:
        """Run the game loop, capturing stdout."""
        original_stdout = sys.stdout
        interceptor = PrintInterceptor(original_stdout, self._all_event_buses)
        sys.stdout = interceptor
        try:
            self.game.play_game()
        except Exception as e:
            for bus in self._all_event_buses:
                try:
                    bus.emit("log", f"Game error: {e}")
                    bus.emit("game_error", str(e))
                except Exception:
                    pass
        finally:
            sys.stdout = original_stdout
            self._finished = True
            if self._room:
                self._room.state = "finished"
                self._room.broadcast_game_over(None)
            else:
                self.event_bus.emit("game_over", None)

    @property
    def is_finished(self) -> bool:
        return self._finished
