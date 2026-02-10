"""
NiceGUI entry point for the Kabo web GUI.

Handles page routing, event wiring between game session and UI components.

Cross-thread communication: The game runs in a background thread, but NiceGUI
UI elements can only be modified from the UI thread. We solve this by having
EventBus callbacks enqueue events, and a ui.timer on the UI thread drains
the queue and applies UI updates.
"""
import queue
from nicegui import ui, app
from typing import Optional

from src.web.event_bus import EventBus
from src.web.game_session import GameSession
from src.web.web_player import WebPlayer
from src.web.game_state import GameStateSnapshot
from src.web.components.setup_page import render_setup_page
from src.web.components.game_table import GameTable


class WebApp:
    """Per-session web application state."""

    def __init__(self):
        self.event_bus: Optional[EventBus] = None
        self.session: Optional[GameSession] = None
        self.web_player: Optional[WebPlayer] = None
        self.game_table: Optional[GameTable] = None
        self._last_state: Optional[GameStateSnapshot] = None
        # Thread-safe queue for events from game thread -> UI thread
        self._ui_queue: queue.Queue = queue.Queue()

    def start_game(self, player_name: str, ai_count: int) -> None:
        """Initialize and start a new game session."""
        self.event_bus = EventBus()
        self.session = GameSession(player_name, ai_count, self.event_bus)

        # Subscribe to events - these callbacks run on the game thread,
        # so they just enqueue events for the UI timer to process
        self.event_bus.subscribe("state_update", lambda s: self._ui_queue.put(("state_update", s)))
        self.event_bus.subscribe("input_request", lambda r: self._ui_queue.put(("input_request", r)))
        self.event_bus.subscribe("log", lambda m: self._ui_queue.put(("log", m)))
        self.event_bus.subscribe("game_over", lambda d: self._ui_queue.put(("game_over", d)))
        self.event_bus.subscribe("card_revealed", lambda d: self._ui_queue.put(("card_revealed", d)))

        # Start the game (creates WebPlayer, launches game thread)
        self.web_player = self.session.start()

    def submit_response(self, response) -> None:
        """Forward UI response to the WebPlayer."""
        if self.web_player:
            self.web_player.submit_response(response)

    def process_ui_events(self) -> None:
        """Drain the event queue and apply UI updates. Called by ui.timer on UI thread."""
        while not self._ui_queue.empty():
            try:
                event_type, data = self._ui_queue.get_nowait()
            except queue.Empty:
                break

            try:
                if event_type == "state_update":
                    self._on_state_update(data)
                elif event_type == "input_request":
                    self._on_input_request(data)
                elif event_type == "log":
                    self._on_log(data)
                elif event_type == "game_over":
                    self._on_game_over(data)
                elif event_type == "card_revealed":
                    self._on_card_revealed(data)
            except Exception as e:
                print(f"[WebApp] Error processing {event_type}: {e}")

    def _on_state_update(self, state: GameStateSnapshot) -> None:
        self._last_state = state
        if self.game_table:
            self.game_table.update_state(state)

    def _on_input_request(self, request) -> None:
        if self.game_table and request:
            self.game_table.action_panel.show_request(request)

    def _on_log(self, message) -> None:
        if self.game_table:
            self.game_table.game_log.add_message(str(message))

    def _on_game_over(self, _data) -> None:
        if self.game_table and self._last_state:
            self.game_table.show_game_over(self._last_state)

    def _on_card_revealed(self, data) -> None:
        """Legacy handler - card reveals are now shown via action panel confirmation."""
        pass


def start_web_gui() -> None:
    """Launch the NiceGUI web application."""

    @ui.page("/")
    def index():
        _webapp = WebApp()

        ui.dark_mode().enable()
        ui.query("body").style("background-color: #1a1a2e;")

        # Main container
        main = ui.column().classes("w-full min-h-screen items-center")

        with main:
            setup_container = ui.column().classes("w-full items-center")
            game_container = ui.column().classes("w-full items-center hidden")

        # Timer that polls the event queue every 100ms (runs on UI thread)
        ui.timer(0.1, _webapp.process_ui_events)

        def on_game_start(player_name: str, ai_count: int):
            # Hide setup, show game
            setup_container.classes(add="hidden")
            game_container.classes(remove="hidden")

            # Build game table
            with game_container:
                _webapp.game_table = GameTable(on_submit=_webapp.submit_response)
                _webapp.game_table.build()

            # Start the game
            _webapp.start_game(player_name, ai_count)

            # Show waiting state
            _webapp.game_table.action_panel.show_waiting(
                "Game starting... peeking at initial cards"
            )

        with setup_container:
            render_setup_page(on_start=on_game_start)

    ui.run(title="KABO - Card Game", port=8080, reload=False)
