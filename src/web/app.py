"""
NiceGUI entry point for the Kabo web GUI.

Handles page routing, event wiring between game session and UI components.
Supports both solo play (single player vs AI) and multiplayer room-based play.

Cross-thread communication: The game runs in a background thread, but NiceGUI
UI elements can only be modified from the UI thread. We solve this by having
EventBus callbacks enqueue events, and a ui.timer on the UI thread drains
the queue and applies UI updates.
"""
import os
import queue
from nicegui import ui, app
from typing import Optional

from src.web.event_bus import EventBus
from src.web.game_session import GameSession
from src.web.web_player import WebPlayer
from src.web.game_state import GameStateSnapshot, AnimationEvent
from src.web.game_room import (
    GameRoom, create_room, join_room, get_room, remove_room,
)
from src.web.components.setup_page import render_setup_page
from src.web.components.lobby_page import render_lobby_page
from src.web.components.room_waiting_page import render_room_waiting_page
from src.web.components.join_page import render_join_page
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
        # Multiplayer state
        self.room: Optional[GameRoom] = None
        self.player_name: Optional[str] = None
        self.is_host: bool = False

    def start_game(self, player_name: str, ai_count: int) -> None:
        """Initialize and start a new solo game session."""
        self.event_bus = EventBus()
        self.session = GameSession(player_name, ai_count, self.event_bus)
        self._subscribe_to_bus(self.event_bus)

        # Start the game (creates WebPlayer, launches game thread)
        self.web_player = self.session.start()

    def start_multiplayer_game(self) -> None:
        """Start the game for a multiplayer room (called by host)."""
        if not self.room:
            return
        self.room.start_game()
        # After start_game, each player's WebPlayer is created in room.players
        uname = self.player_name.upper()
        info = self.room.players.get(uname)
        if info:
            self.web_player = info["web_player"]

    def connect_to_room_game(self) -> None:
        """Connect this WebApp to an already-started room game.

        Used by non-host players when the game starts, or by reconnecting players.
        """
        if not self.room or not self.player_name:
            return
        uname = self.player_name.upper()
        info = self.room.players.get(uname)
        if info:
            self.web_player = info["web_player"]

    def _subscribe_to_bus(self, bus: EventBus) -> None:
        """Subscribe to events on the given EventBus."""
        bus.subscribe("state_update", lambda s: self._ui_queue.put(("state_update", s)))
        bus.subscribe("input_request", lambda r: self._ui_queue.put(("input_request", r)))
        bus.subscribe("log", lambda m: self._ui_queue.put(("log", m)))
        bus.subscribe("game_over", lambda d: self._ui_queue.put(("game_over", d)))
        bus.subscribe("card_revealed", lambda d: self._ui_queue.put(("card_revealed", d)))
        bus.subscribe("notification", lambda n: self._ui_queue.put(("notification", n)))
        bus.subscribe("animation", lambda a: self._ui_queue.put(("animation", a)))

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
                elif event_type == "notification":
                    self._on_notification(data)
                elif event_type == "animation":
                    self._on_animation(data)
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

    def _on_notification(self, notification) -> None:
        if self.game_table:
            self.game_table.show_notification(notification)

    def _on_animation(self, event: AnimationEvent) -> None:
        if self.game_table:
            self.game_table.enqueue_animation(event)


def start_web_gui(port: int = 8080) -> None:
    """Launch the NiceGUI web application."""

    @ui.page("/")
    def index():
        _webapp = WebApp()

        ui.dark_mode().enable()
        ui.query("body").style("background-color: #1a1a2e;")

        # Main container
        main = ui.column().classes("w-full min-h-screen items-center")

        with main:
            lobby_container = ui.column().classes("w-full items-center")
            setup_container = ui.column().classes("w-full items-center hidden")
            waiting_container = ui.column().classes("w-full items-center hidden")
            game_container = ui.column().classes("w-full items-center hidden")

        # Timer that polls the event queue every 100ms (runs on UI thread)
        ui.timer(0.1, _webapp.process_ui_events)

        # --- Check for reconnection ---
        stored_room = app.storage.user.get("room_code")
        stored_name = app.storage.user.get("player_name")

        if stored_room and stored_name:
            room = get_room(stored_room)
            if room and room.state == "playing":
                # Reconnect to an active game
                _webapp.room = room
                _webapp.player_name = stored_name
                _webapp.event_bus = EventBus()
                _webapp._subscribe_to_bus(_webapp.event_bus)

                try:
                    room.reconnect_player(stored_name, _webapp.event_bus)
                except ValueError:
                    # Player not in room, clear storage and show lobby
                    app.storage.user.pop("room_code", None)
                    app.storage.user.pop("player_name", None)
                else:
                    _webapp.connect_to_room_game()
                    # Switch to game view
                    lobby_container.classes(add="hidden")
                    game_container.classes(remove="hidden")
                    with game_container:
                        _webapp.game_table = GameTable(
                            on_submit=_webapp.submit_response
                        )
                        _webapp.game_table.build()
                    _webapp.game_table.action_panel.show_waiting(
                        "Reconnected! Waiting for your turn..."
                    )
                    return
            elif room and room.state == "waiting":
                # Room exists but game hasn't started, go to waiting room
                _webapp.room = room
                _webapp.player_name = stored_name
                _webapp.is_host = (room.host_name == stored_name.upper())
                _webapp.event_bus = EventBus()
                _webapp._subscribe_to_bus(_webapp.event_bus)

                # Re-add player if not present (they may have been removed)
                uname = stored_name.upper()
                if uname not in room.players:
                    try:
                        room.add_player(stored_name, _webapp.event_bus)
                    except ValueError:
                        app.storage.user.pop("room_code", None)
                        app.storage.user.pop("player_name", None)
                        # Fall through to lobby
                    else:
                        _show_waiting_room(
                            _webapp, lobby_container, waiting_container,
                            game_container
                        )
                        return
                else:
                    room.reconnect_player(stored_name, _webapp.event_bus)
                    _show_waiting_room(
                        _webapp, lobby_container, waiting_container,
                        game_container
                    )
                    return
            else:
                # Room doesn't exist anymore, clear storage
                app.storage.user.pop("room_code", None)
                app.storage.user.pop("player_name", None)

        # --- Phase transitions ---

        def show_solo_setup():
            lobby_container.classes(add="hidden")
            setup_container.classes(remove="hidden")
            with setup_container:
                render_setup_page(on_start=on_solo_game_start)

        def on_solo_game_start(player_name: str, ai_count: int):
            setup_container.classes(add="hidden")
            game_container.classes(remove="hidden")
            with game_container:
                _webapp.game_table = GameTable(
                    on_submit=_webapp.submit_response
                )
                _webapp.game_table.build()
            _webapp.start_game(player_name, ai_count)
            _webapp.game_table.action_panel.show_waiting(
                "Game starting... peeking at initial cards"
            )

        def on_create_room(player_name: str, max_players: int,
                           ai_count: int, show_revelations: bool = False):
            try:
                room = create_room(player_name, max_players, ai_count,
                                   show_revelations=show_revelations)
                _webapp.event_bus = EventBus()
                _webapp._subscribe_to_bus(_webapp.event_bus)
                room.add_player(player_name, _webapp.event_bus)
                _webapp.room = room
                _webapp.player_name = player_name
                _webapp.is_host = True
                # Persist in storage for reconnection
                app.storage.user["room_code"] = room.room_code
                app.storage.user["player_name"] = player_name
                _show_waiting_room(
                    _webapp, lobby_container, waiting_container,
                    game_container
                )
            except ValueError as e:
                ui.notify(str(e), type="negative")

        def on_join_room(player_name: str, room_code: str):
            try:
                _webapp.event_bus = EventBus()
                _webapp._subscribe_to_bus(_webapp.event_bus)
                room = join_room(room_code, player_name, _webapp.event_bus)
                _webapp.room = room
                _webapp.player_name = player_name
                _webapp.is_host = False
                app.storage.user["room_code"] = room.room_code
                app.storage.user["player_name"] = player_name
                _show_waiting_room(
                    _webapp, lobby_container, waiting_container,
                    game_container
                )
            except ValueError as e:
                ui.notify(str(e), type="negative")

        # --- Render lobby ---
        with lobby_container:
            render_lobby_page(
                on_solo=show_solo_setup,
                on_create_room=on_create_room,
                on_join_room=on_join_room,
            )

    @ui.page("/join/{room_code}")
    def join_page(room_code: str):
        _webapp = WebApp()

        ui.dark_mode().enable()
        ui.query("body").style("background-color: #1a1a2e;")

        main = ui.column().classes("w-full min-h-screen items-center")

        with main:
            lobby_container = ui.column().classes("w-full items-center")
            waiting_container = ui.column().classes("w-full items-center hidden")
            game_container = ui.column().classes("w-full items-center hidden")

        ui.timer(0.1, _webapp.process_ui_events)

        # Check for reconnection
        stored_room = app.storage.user.get("room_code")
        stored_name = app.storage.user.get("player_name")

        if stored_room and stored_name:
            room = get_room(stored_room)
            if room and room.state == "playing":
                _webapp.room = room
                _webapp.player_name = stored_name
                _webapp.event_bus = EventBus()
                _webapp._subscribe_to_bus(_webapp.event_bus)
                try:
                    room.reconnect_player(stored_name, _webapp.event_bus)
                except ValueError:
                    app.storage.user.pop("room_code", None)
                    app.storage.user.pop("player_name", None)
                else:
                    _webapp.connect_to_room_game()
                    lobby_container.classes(add="hidden")
                    game_container.classes(remove="hidden")
                    with game_container:
                        _webapp.game_table = GameTable(
                            on_submit=_webapp.submit_response
                        )
                        _webapp.game_table.build()
                    _webapp.game_table.action_panel.show_waiting(
                        "Reconnected! Waiting for your turn..."
                    )
                    return
            elif room and room.state == "waiting":
                _webapp.room = room
                _webapp.player_name = stored_name
                _webapp.is_host = (room.host_name == stored_name.upper())
                _webapp.event_bus = EventBus()
                _webapp._subscribe_to_bus(_webapp.event_bus)
                uname = stored_name.upper()
                if uname not in room.players:
                    try:
                        room.add_player(stored_name, _webapp.event_bus)
                    except ValueError:
                        app.storage.user.pop("room_code", None)
                        app.storage.user.pop("player_name", None)
                    else:
                        _show_waiting_room(
                            _webapp, lobby_container, waiting_container,
                            game_container
                        )
                        return
                else:
                    room.reconnect_player(stored_name, _webapp.event_bus)
                    _show_waiting_room(
                        _webapp, lobby_container, waiting_container,
                        game_container
                    )
                    return
            else:
                app.storage.user.pop("room_code", None)
                app.storage.user.pop("player_name", None)

        # Validate the room
        code = room_code.upper()
        room = get_room(code)
        room_info = None
        if room and room.state == "waiting":
            room_info = {
                "players": room.get_player_names(),
                "max_players": room.max_players,
                "host_name": room.host_name,
            }

        def on_join_room(player_name: str, code: str):
            try:
                _webapp.event_bus = EventBus()
                _webapp._subscribe_to_bus(_webapp.event_bus)
                r = join_room(code, player_name, _webapp.event_bus)
                _webapp.room = r
                _webapp.player_name = player_name
                _webapp.is_host = False
                app.storage.user["room_code"] = r.room_code
                app.storage.user["player_name"] = player_name
                _show_waiting_room(
                    _webapp, lobby_container, waiting_container,
                    game_container
                )
            except ValueError as e:
                ui.notify(str(e), type="negative")

        with lobby_container:
            render_join_page(
                room_code=code,
                on_join=on_join_room,
                room_info=room_info,
            )

    def _show_waiting_room(_webapp: WebApp, lobby_container,
                           waiting_container, game_container):
        """Transition to the waiting room view."""
        lobby_container.classes(add="hidden")
        waiting_container.classes(remove="hidden")

        def get_room_info():
            if not _webapp.room:
                return None
            return {
                "players": _webapp.room.get_player_names(),
                "max_players": _webapp.room.max_players,
                "ai_count": _webapp.room.ai_count,
                "state": _webapp.room.state,
                "host_name": _webapp.room.host_name,
                "show_revelations": _webapp.room.show_revelations,
            }

        def on_start():
            try:
                _webapp.start_multiplayer_game()
                _webapp.connect_to_room_game()
                _transition_to_game(
                    _webapp, waiting_container, game_container
                )
            except ValueError as e:
                ui.notify(str(e), type="negative")

        def on_leave():
            if _webapp.room and _webapp.player_name:
                _webapp.room.remove_player(_webapp.player_name)
                if _webapp.is_host:
                    remove_room(_webapp.room.room_code)
            app.storage.user.pop("room_code", None)
            app.storage.user.pop("player_name", None)
            ui.navigate.to("/")

        join_path = f"/join/{_webapp.room.room_code}" if _webapp.room else ""

        req = ui.context.request
        base = f"{req.url.scheme}://{req.url.netloc}"
        join_url = base + join_path
        
        with waiting_container:
            render_room_waiting_page(
                room_code=_webapp.room.room_code,
                player_name=_webapp.player_name.upper(),
                is_host=_webapp.is_host,
                get_room_info=get_room_info,
                on_start=on_start,
                on_leave=on_leave,
                join_url=join_url,
            )

        # For non-host players: poll room state to detect game start
        if not _webapp.is_host:
            def check_game_started():
                if _webapp.room and _webapp.room.state == "playing":
                    _webapp.connect_to_room_game()
                    _transition_to_game(
                        _webapp, waiting_container, game_container
                    )
                    timer.deactivate()

            timer = ui.timer(1.0, check_game_started)

    def _transition_to_game(_webapp: WebApp, from_container,
                            game_container):
        """Switch from waiting room to game view."""
        from_container.classes(add="hidden")
        game_container.classes(remove="hidden")
        with game_container:
            _webapp.game_table = GameTable(
                on_submit=_webapp.submit_response
            )
            _webapp.game_table.build()
        _webapp.game_table.action_panel.show_waiting(
            "Game starting... peeking at initial cards"
        )

    host = os.environ.get("HOST", "0.0.0.0")
    effective_port = int(os.environ.get("PORT", port))
    ui.run(
        title="KABO - Card Game",
        host=host,
        port=effective_port,
        reload=False,
        storage_secret=os.environ.get("STORAGE_SECRET", "kabo-default-dev-secret"),
    )
