"""
Room waiting page - displayed after creating/joining a room, before the game starts.
Shows connected players, room code, and start button for the host.
"""
from nicegui import ui
from typing import Callable, Optional

# Track auto-start per room to prevent multiple triggers
_auto_started_rooms: set = set()


def render_room_waiting_page(room_code: str, player_name: str,
                             is_host: bool,
                             get_room_info: Callable,
                             on_start: Callable,
                             on_leave: Callable,
                             join_url: str = "") -> ui.column:
    """Render the waiting room page.

    Args:
        room_code: the room code to display
        player_name: this player's name (uppercased)
        is_host: whether this player is the host
        get_room_info: callback() -> dict with keys: players, max_players, ai_count, state
        on_start: callback() - host starts the game
        on_leave: callback() - player leaves the room
    """
    container = ui.column().classes("w-96 mx-auto mt-8 items-center")

    with container:
        ui.label("KABO").classes(
            "text-3xl font-bold text-white mb-2"
        )

        # Room code display
        with ui.card().classes("w-full p-4 mb-4"):
            ui.label("Room Code").classes(
                "text-sm text-gray-400 text-center w-full"
            )
            code_label = ui.label(room_code).classes(
                "text-4xl font-bold text-yellow-300 text-center w-full "
                "tracking-widest select-all cursor-pointer"
            )
            code_label.tooltip("Click to select, then copy!")
            if join_url:
                ui.label("Or share this link:").classes(
                    "text-xs text-gray-500 text-center w-full mt-2"
                )
                with ui.row().classes("w-full items-center gap-1"):
                    link_input = ui.input(value=join_url).classes(
                        "flex-grow"
                    ).props("outlined dense dark readonly")

                    async def _set_full_url():
                        origin = await ui.run_javascript('window.location.origin')
                        link_input.value = f'{origin}{join_url}'

                    ui.timer(0.5, _set_full_url, once=True)

                    copy_js = (
                        'function(){var t=document.createElement("textarea");'
                        't.value=window.location.origin+"' + join_url + '";'
                        't.style.position="fixed";t.style.left="-9999px";'
                        'document.body.appendChild(t);t.select();'
                        'document.execCommand("copy");document.body.removeChild(t)}'
                    )
                    ui.button(
                        icon="content_copy",
                    ).props("flat dense").classes("text-yellow-300").on(
                        "click",
                        js_handler=f'() => {{ ({copy_js})(); $emit("copied") }}',
                    ).on("copied", lambda: ui.notify("Link copied!", type="positive"))
            else:
                ui.label("Share this code with your friends!").classes(
                    "text-xs text-gray-500 text-center w-full mt-1"
                )

        # Players list
        players_card = ui.card().classes("w-full p-4 mb-4")
        players_container = ui.column().classes("w-full")

        # Settings display
        settings_label = ui.label("").classes(
            "text-sm text-gray-400 mb-4"
        )

        # Start / Leave buttons
        start_btn = None
        if is_host:
            start_btn = ui.button(
                "Start Game", on_click=on_start
            ).classes("w-full mb-2").props("color=positive size=lg")
            start_btn.disable()

        ui.button(
            "Leave Room", on_click=on_leave
        ).classes("w-full").props("color=negative size=sm outline")

        # Status label
        status_label = ui.label("Waiting for players...").classes(
            "text-sm text-gray-500 mt-2"
        )

    def refresh():
        """Poll room state and update UI."""
        try:
            info = get_room_info()
        except Exception:
            return

        if info is None:
            return

        # If game started, the app.py handler will switch to game view
        if info["state"] == "playing":
            status_label.set_text("Game starting!")
            return

        player_names = info["players"]
        max_p = info["max_players"]
        ai_c = info["ai_count"]

        # Update settings label
        show_rev = info.get("show_revelations", False)
        rev_text = " | Card values in log: ON" if show_rev else " | Card values in log: OFF"
        settings_label.set_text(
            f"Players: {len(player_names)}/{max_p} humans"
            + (f" + {ai_c} AI" if ai_c else "")
            + rev_text
        )

        # Update players list
        with players_card:
            players_container.clear()
            with players_container:
                for pname in player_names:
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("person").classes("text-green-400")
                        label = pname
                        if pname == info.get("host_name"):
                            label += " (Host)"
                        ui.label(label).classes("text-white")

                # Show AI slots
                for i in range(ai_c):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("smart_toy").classes("text-blue-400")
                        ui.label(f"AI_{i + 1}").classes("text-gray-400")

                # Show empty slots
                empty = max_p - len(player_names)
                for _ in range(empty):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("person_outline").classes("text-gray-600")
                        ui.label("Waiting...").classes("text-gray-600 italic")

        # Enable start button when enough players
        total = len(player_names) + ai_c
        if start_btn:
            if total >= 2 and len(player_names) >= 1:
                start_btn.enable()
            else:
                start_btn.disable()

        # Auto-start when all human slots are filled
        if (is_host
                and len(player_names) >= max_p
                and room_code not in _auto_started_rooms):
            _auto_started_rooms.add(room_code)
            status_label.set_text("All players joined! Starting in 2s...")
            ui.timer(2.0, on_start, once=True)

    # Poll every second
    ui.timer(1.0, refresh)
    # Initial render
    refresh()

    return container
