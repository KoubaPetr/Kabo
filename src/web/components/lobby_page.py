"""
Lobby page - landing page with solo play, create room, and join room options.
"""
from nicegui import ui
from typing import Callable


def render_lobby_page(on_solo: Callable, on_create_room: Callable,
                      on_join_room: Callable) -> None:
    """Render the lobby page.

    Args:
        on_solo: callback() - switch to solo setup form
        on_create_room: callback(player_name, max_players, ai_count)
        on_join_room: callback(player_name, room_code)
    """
    with ui.card().classes("w-96 mx-auto mt-8 p-6"):
        ui.label("KABO").classes(
            "text-4xl font-bold text-center w-full text-white mb-1"
        )
        ui.label("Card Game").classes(
            "text-lg text-center w-full text-gray-400 mb-4"
        )

        ui.separator()

        # --- Play Solo ---
        ui.button("Play Solo (vs AI)", on_click=on_solo).classes(
            "w-full mt-4"
        ).props("color=positive size=lg")

        ui.separator().classes("my-4")

        # --- Create Room ---
        ui.label("Create a Room").classes(
            "text-lg font-bold text-white mb-2"
        )

        create_name = ui.input(
            "Your Name", value="Player"
        ).classes("w-full mb-2").props("outlined dark")

        max_slider = ui.slider(min=2, max=4, value=4, step=1).classes("w-full")
        max_label = ui.label("Max human players: 4").classes(
            "text-sm text-gray-400 mb-1"
        )
        max_slider.on_value_change(
            lambda e: max_label.set_text(f"Max human players: {int(e.value)}")
        )

        ai_slider = ui.slider(min=0, max=3, value=0, step=1).classes("w-full")
        ai_label = ui.label("AI opponents: 0").classes(
            "text-sm text-gray-400 mb-2"
        )
        ai_slider.on_value_change(
            lambda e: ai_label.set_text(f"AI opponents: {int(e.value)}")
        )

        def do_create():
            name = create_name.value.strip()
            if not name:
                ui.notify("Please enter your name", type="warning")
                return
            max_p = int(max_slider.value)
            ai_c = int(ai_slider.value)
            total = max_p + ai_c
            if total < 2:
                ui.notify("Need at least 2 total players", type="warning")
                return
            if total > 4:
                ui.notify("Max 4 total players (humans + AI)", type="warning")
                return
            on_create_room(name, max_p, ai_c)

        ui.button("Create Room", on_click=do_create).classes(
            "w-full"
        ).props("color=primary size=md")

        ui.separator().classes("my-4")

        # --- Join Room ---
        ui.label("Join a Room").classes(
            "text-lg font-bold text-white mb-2"
        )

        join_name = ui.input(
            "Your Name", value="Player"
        ).classes("w-full mb-2").props("outlined dark")

        room_code_input = ui.input(
            "Room Code", placeholder="e.g. ABC12"
        ).classes("w-full mb-2").props("outlined dark")

        def do_join():
            name = join_name.value.strip()
            code = room_code_input.value.strip().upper()
            if not name:
                ui.notify("Please enter your name", type="warning")
                return
            if not code:
                ui.notify("Please enter a room code", type="warning")
                return
            on_join_room(name, code)

        ui.button("Join Room", on_click=do_join).classes(
            "w-full"
        ).props("color=secondary size=md")
