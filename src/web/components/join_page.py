"""
Join page - simplified page for URL-based room joining.
Shows room info and a name input + join button, no option to create rooms.
"""
from nicegui import ui
from typing import Callable, Optional, Dict


def render_join_page(room_code: str, on_join: Callable,
                     room_info: Optional[Dict] = None) -> None:
    """Render a simplified join page for URL-based room joining.

    Args:
        room_code: the room code (from URL)
        on_join: callback(player_name, room_code)
        room_info: dict with players, max_players, host_name (None if room not found)
    """
    with ui.card().classes("w-96 mx-auto mt-8 p-6"):
        ui.label("KABO").classes(
            "text-4xl font-bold text-center w-full text-white mb-1"
        )
        ui.label("Card Game").classes(
            "text-lg text-center w-full text-gray-400 mb-4"
        )

        ui.separator()

        if room_info is None:
            # Room not found or invalid
            ui.label("Room not found").classes(
                "text-xl font-bold text-red-400 text-center w-full mt-4"
            )
            ui.label(
                f"Room '{room_code}' does not exist or the game has already started."
            ).classes("text-sm text-gray-400 text-center w-full mt-2")
            ui.button(
                "Go to Main Lobby", on_click=lambda: ui.navigate.to("/")
            ).classes("w-full mt-4").props("color=primary size=lg")
            return

        # Room code display
        with ui.card().classes("w-full p-4 mt-4 mb-2"):
            ui.label("Joining Room").classes(
                "text-sm text-gray-400 text-center w-full"
            )
            ui.label(room_code).classes(
                "text-3xl font-bold text-yellow-300 text-center w-full "
                "tracking-widest"
            )

        # Room info
        players = room_info.get("players", [])
        max_p = room_info.get("max_players", 4)
        host = room_info.get("host_name", "")
        ui.label(
            f"Host: {host} | Players: {len(players)}/{max_p}"
        ).classes("text-sm text-gray-400 text-center w-full mb-2")

        ui.separator().classes("my-2")

        # Name input
        join_name = ui.input(
            "Your Name", value="Player"
        ).classes("w-full mb-3").props("outlined dark")

        def do_join():
            name = join_name.value.strip()
            if not name:
                ui.notify("Please enter your name", type="warning")
                return
            on_join(name, room_code)

        ui.button("Join Room", on_click=do_join).classes(
            "w-full"
        ).props("color=positive size=lg")

        ui.separator().classes("my-3")

        ui.button(
            "Go to Main Lobby", on_click=lambda: ui.navigate.to("/")
        ).classes("w-full").props("color=secondary size=sm outline")
