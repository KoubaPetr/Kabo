"""
GameSession - manages a game running in a background thread.

Creates players, runs Game.play_game() in a daemon thread, and captures
print output via PrintInterceptor so it appears in the browser log.
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
    stdout and the EventBus as log events."""

    def __init__(self, original_stdout, event_bus: EventBus):
        self._original = original_stdout
        self._event_bus = event_bus

    def write(self, text: str) -> int:
        if text and text.strip():
            self._event_bus.emit("log", text.strip())
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

    def _run_game(self) -> None:
        """Run the game loop, capturing stdout."""
        original_stdout = sys.stdout
        interceptor = PrintInterceptor(original_stdout, self.event_bus)
        sys.stdout = interceptor
        try:
            self.game.play_game()
        except Exception as e:
            self.event_bus.emit("log", f"Game error: {e}")
            self.event_bus.emit("game_error", str(e))
        finally:
            sys.stdout = original_stdout
            self._finished = True
            self.event_bus.emit("game_over", None)

    @property
    def is_finished(self) -> bool:
        return self._finished
