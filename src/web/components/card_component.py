"""
Card rendering component - HTML/CSS cards using Tailwind classes.
Shows card value face-up or "?" for unknown cards.
"""
from nicegui import ui
from src.web.game_state import CardView


# Color mapping for card values
CARD_COLORS = {
    0: "#2d2d2d",   # black (king)
    1: "#1a7a1a",   # dark green
    2: "#1a7a1a",
    3: "#1a7a1a",
    4: "#b8860b",   # dark goldenrod
    5: "#b8860b",
    6: "#b8860b",
    7: "#1565c0",   # blue (KUK/peek)
    8: "#1565c0",
    9: "#7b1fa2",   # purple (ŠPION/spy)
    10: "#7b1fa2",
    11: "#c62828",  # red (KŠEFT/swap)
    12: "#c62828",
    13: "#2d2d2d",  # black (king)
}

EFFECT_NAMES = {
    7: "KUK", 8: "KUK",
    9: "ŠPION", 10: "ŠPION",
    11: "KŠEFT", 12: "KŠEFT",
}


def render_card(card: CardView, size: str = "normal",
                clickable: bool = False, on_click=None,
                selected: bool = False, label: str = "") -> None:
    """Render a single card as an HTML element.

    Args:
        card: CardView with value (or None for face-down)
        size: "small" for opponent cards, "normal" for player's own
        clickable: whether the card should be clickable
        on_click: callback when clicked
        selected: whether to show selected highlight
        label: optional label below the card (e.g. position number)
    """
    if size == "small":
        w, h, text_size = "w-12", "h-16", "text-sm"
    else:
        w, h, text_size = "w-16", "h-22", "text-lg"

    is_face_up = card.value is not None

    if is_face_up:
        bg_color = CARD_COLORS.get(card.value, "#555")
        display_text = str(card.value)
        effect = EFFECT_NAMES.get(card.value, "")
    else:
        bg_color = "#37474f"  # blue-grey for card backs
        display_text = "?"
        effect = ""

    border = "border-2 border-yellow-400" if selected else "border border-gray-600"
    cursor = "cursor-pointer hover:scale-110 transition-transform" if clickable else ""
    shadow = "shadow-lg" if selected else "shadow-md"

    with ui.column().classes(f"items-center gap-0.5"):
        card_el = ui.element("div").classes(
            f"{w} {h} rounded-lg {border} {cursor} {shadow} "
            f"flex flex-col items-center justify-center select-none"
        ).style(f"background-color: {bg_color}; color: white;")

        with card_el:
            ui.label(display_text).classes(f"{text_size} font-bold")
            if effect:
                ui.label(effect).classes("text-xs opacity-80")

        if clickable and on_click:
            card_el.on("click", lambda e, cb=on_click: cb())

        if label:
            ui.label(label).classes("text-xs text-gray-400")


def render_card_back(size: str = "normal", label: str = "",
                     clickable: bool = False, on_click=None) -> None:
    """Render a face-down card (deck, unknown card)."""
    render_card(
        CardView(position=0, value=None, is_known=False, is_publicly_visible=False),
        size=size, label=label, clickable=clickable, on_click=on_click,
    )


def render_deck(cards_left: int, clickable: bool = False, on_click=None) -> None:
    """Render the draw deck with card count."""
    if cards_left == 0:
        with ui.column().classes("items-center"):
            ui.element("div").classes(
                "w-16 h-22 rounded-lg border border-dashed border-gray-600 "
                "flex items-center justify-center"
            ).style("background-color: transparent; color: #666;")
            ui.label("Empty").classes("text-xs text-gray-500")
        return

    cursor = "cursor-pointer hover:scale-105 transition-transform" if clickable else ""
    with ui.column().classes("items-center gap-0.5"):
        deck_el = ui.element("div").classes(
            f"w-16 h-22 rounded-lg border border-gray-500 {cursor} shadow-md "
            f"flex flex-col items-center justify-center select-none"
        ).style("background-color: #263238; color: #90a4ae;")

        with deck_el:
            ui.label("DECK").classes("text-xs font-bold")
            ui.label(str(cards_left)).classes("text-lg")

        if clickable and on_click:
            deck_el.on("click", lambda e, cb=on_click: cb())


def render_discard_pile(top_value: int = None) -> None:
    """Render the discard pile showing the top card."""
    with ui.column().classes("items-center gap-0.5"):
        if top_value is not None:
            bg_color = CARD_COLORS.get(top_value, "#555")
            card_el = ui.element("div").classes(
                "w-16 h-22 rounded-lg border border-gray-400 shadow-md "
                "flex flex-col items-center justify-center select-none"
            ).style(f"background-color: {bg_color}; color: white;")

            with card_el:
                ui.label(str(top_value)).classes("text-lg font-bold")
                effect = EFFECT_NAMES.get(top_value, "")
                if effect:
                    ui.label(effect).classes("text-xs opacity-80")
        else:
            ui.element("div").classes(
                "w-16 h-22 rounded-lg border border-dashed border-gray-600 "
                "flex items-center justify-center"
            ).style("background-color: transparent; color: #666;")

        ui.label("Discard").classes("text-xs text-gray-400")
