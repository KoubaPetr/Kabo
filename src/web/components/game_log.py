"""
Scrolling game event log component.
"""
from nicegui import ui
from typing import List


class GameLog:
    """Scrollable log panel that displays game events."""

    def __init__(self):
        self._messages: List[str] = []
        self._log_container = None
        self._scroll_area = None

    def build(self) -> None:
        """Create the log UI element."""
        with ui.card().classes("w-full"):
            ui.label("Game Log").classes("text-sm font-bold text-gray-300")
            self._scroll_area = ui.scroll_area().classes("h-48 w-full")
            with self._scroll_area:
                self._log_container = ui.column().classes("w-full gap-0.5 p-1")

    def add_message(self, message: str) -> None:
        """Add a message to the log and auto-scroll."""
        if not message or not message.strip():
            return
        self._messages.append(message.strip())
        # Keep last 200 messages
        if len(self._messages) > 200:
            self._messages = self._messages[-200:]

        if self._log_container:
            with self._log_container:
                ui.label(message.strip()).classes(
                    "text-xs text-gray-300 font-mono whitespace-pre-wrap"
                )
            if self._scroll_area:
                self._scroll_area.scroll_to(percent=1.0)

    def clear(self) -> None:
        """Clear all messages."""
        self._messages.clear()
        if self._log_container:
            self._log_container.clear()
