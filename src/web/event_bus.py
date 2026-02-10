"""
Thread-safe pub/sub event bus for bridging the game thread and the NiceGUI UI.

The game thread emits events (state updates, input requests, log messages).
The UI subscribes to events and updates accordingly.
"""
import threading
from typing import Any, Callable, Dict, List


class EventBus:
    """Simple thread-safe publish/subscribe event bus."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, callback: Callable) -> None:
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type] = [
                    cb for cb in self._subscribers[event_type] if cb != callback
                ]

    def emit(self, event_type: str, data: Any = None) -> None:
        with self._lock:
            callbacks = list(self._subscribers.get(event_type, []))
        for callback in callbacks:
            try:
                callback(data)
            except Exception as e:
                print(f"[EventBus] Error in callback for '{event_type}': {e}")

    def clear(self) -> None:
        with self._lock:
            self._subscribers.clear()
