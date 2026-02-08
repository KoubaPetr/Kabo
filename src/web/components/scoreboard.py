"""
Scoreboard component - displays player scores.
"""
from nicegui import ui
from typing import List
from src.web.game_state import PlayerView


class Scoreboard:
    """Displays current game scores for all players."""

    def __init__(self):
        self._container = None

    def build(self) -> None:
        """Create the scoreboard UI element."""
        self._container = ui.card().classes("w-full")
        with self._container:
            ui.label("Scores").classes("text-sm font-bold text-gray-300")

    def update(self, players: List[PlayerView]) -> None:
        """Update the scoreboard with current player data."""
        if not self._container:
            return
        self._container.clear()
        with self._container:
            ui.label("Scores").classes("text-sm font-bold text-gray-300")
            for p in sorted(players, key=lambda x: x.game_score):
                kabo_badge = " [KABO]" if p.called_kabo else ""
                with ui.row().classes("items-center gap-2 w-full"):
                    name_style = "font-bold text-yellow-300" if p.is_current_player else "text-gray-300"
                    ui.label(f"{p.name}{kabo_badge}").classes(f"text-sm {name_style}")
                    ui.label(str(p.game_score)).classes("text-sm text-white ml-auto")
