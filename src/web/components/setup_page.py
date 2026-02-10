"""
Setup page - game configuration form before starting a game.
"""
from nicegui import ui
from typing import Callable


def render_setup_page(on_start: Callable) -> None:
    """Render the game setup form.

    Args:
        on_start: callback(player_name: str, ai_count: int) when Start is clicked
    """
    with ui.card().classes("w-96 mx-auto mt-12 p-6"):
        ui.label("KABO").classes("text-4xl font-bold text-center w-full text-white mb-2")
        ui.label("Card Game").classes("text-lg text-center w-full text-gray-400 mb-6")

        ui.separator()

        name_input = ui.input(
            "Your Name",
            value="Player",
        ).classes("w-full mb-4").props("outlined dark")

        ai_slider = ui.slider(min=1, max=3, value=1, step=1).classes("w-full")
        ai_label = ui.label("AI opponents: 1").classes("text-sm text-gray-400 mb-4")
        ai_slider.on_value_change(
            lambda e: ai_label.set_text(f"AI opponents: {int(e.value)}")
        )

        def start_game():
            name = name_input.value.strip()
            if not name:
                ui.notify("Please enter your name", type="warning")
                return
            ai_count = int(ai_slider.value)
            on_start(name, ai_count)

        ui.button("Start Game", on_click=start_game).classes(
            "w-full mt-4"
        ).props("color=positive size=lg")
