"""
Action panel - dynamic controls that change based on what decision the game needs.

Handles all 7+ input request types from WebPlayer.
"""
from nicegui import ui
from typing import Callable, Optional, List
from src.web.game_state import InputRequest


class ActionPanel:
    """Dynamic action panel that renders appropriate controls for each decision type."""

    def __init__(self, on_submit: Callable):
        """
        Args:
            on_submit: callback(response) - called when user submits their choice
        """
        self._on_submit = on_submit
        self._container = None
        self._current_request: Optional[InputRequest] = None
        self._selected_cards: List[int] = []
        self._game_table = None  # Set by GameTable.build()

    def build(self) -> None:
        """Create the action panel container."""
        self._container = ui.card().classes("w-full")
        with self._container:
            ui.label("Waiting for game to start...").classes(
                "text-gray-400 text-center w-full"
            )

    def show_waiting(self, message: str = "Waiting...") -> None:
        """Show a waiting/non-interactive state."""
        if not self._container:
            return
        self._container.clear()
        with self._container:
            with ui.row().classes("items-center justify-center w-full gap-2"):
                ui.spinner(size="sm")
                ui.label(message).classes("text-gray-400")

    def show_request(self, request: InputRequest, reset_selection: bool = True) -> None:
        """Render appropriate controls for the given input request."""
        if not self._container:
            return

        # Route "waiting" requests to the waiting display
        if request.request_type == "waiting":
            self.show_waiting(request.prompt)
            return

        self._current_request = request
        if reset_selection:
            self._selected_cards = []
        self._container.clear()

        with self._container:
            ui.label(request.prompt).classes("text-white font-bold mb-2")

            handler = getattr(self, f"_render_{request.request_type}", None)
            if handler:
                handler(request)
            else:
                self._render_generic_options(request)

    def _render_pick_turn_type(self, request: InputRequest) -> None:
        """Render turn type selection buttons."""
        ui.label(
            "Click the deck to draw, or the discard pile to take"
        ).classes("text-xs text-gray-400 mb-1 italic")
        with ui.row().classes("gap-2 flex-wrap"):
            for option in request.options:
                label_map = {
                    "HIT_DECK": "Draw from Deck",
                    "HIT_DISCARD_PILE": "Take from Discard",
                    "KABO": "Call KABO!",
                }
                label = label_map.get(option, option)
                color_map = {
                    "HIT_DECK": "primary",
                    "HIT_DISCARD_PILE": "secondary",
                    "KABO": "negative",
                }
                color = color_map.get(option, "primary")
                ui.button(label, on_click=lambda e, o=option: self._submit(o)).props(
                    f"color={color}"
                ).classes("text-sm")

    def _render_decide_on_card_use(self, request: InputRequest) -> None:
        """Render keep/discard/effect buttons for a drawn card."""
        drawn_val = request.extra.get("drawn_card_value", "?")
        drawn_eff = request.extra.get("drawn_card_effect")

        with ui.row().classes("items-center gap-4"):
            # Show the drawn card
            from src.web.components.card_component import CardView as CV, render_card
            render_card(CV(position=0, value=drawn_val, is_known=True,
                          is_publicly_visible=False), size="normal")

        with ui.row().classes("gap-2 mt-2"):
            ui.button("Keep", on_click=lambda: self._submit("KEEP")).props(
                "color=positive"
            )
            ui.button("Discard", on_click=lambda: self._submit("DISCARD")).props(
                "color=negative"
            )
            if drawn_eff:
                effect_labels = {"KUK": "Peek (KUK)", "ŠPION": "Spy (ŠPION)", "KŠEFT": "Swap (KŠEFT)"}
                ui.button(
                    effect_labels.get(drawn_eff, f"Effect ({drawn_eff})"),
                    on_click=lambda: self._submit("EFFECT"),
                ).props("color=warning")

    def _render_pick_hand_cards_for_exchange(self, request: InputRequest) -> None:
        """Render card selection for exchange — click cards in hand on the table."""
        drawn_val = request.extra.get("drawn_card_value", "?")

        ui.label(f"New card value: {drawn_val}").classes("text-yellow-300 text-sm mb-1")
        ui.label(
            "Click cards in your hand to select them for exchange"
        ).classes("text-xs text-gray-400 mb-1 italic")

        if self._selected_cards:
            ui.label(
                f"Selected: {', '.join(f'#{p}' for p in self._selected_cards)}"
            ).classes("text-sm text-yellow-300")

        ui.button(
            "Confirm Exchange",
            on_click=lambda: self._submit(self._selected_cards) if self._selected_cards else None,
        ).props("color=positive").classes("mt-2")

    def _render_pick_position_for_new_card(self, request: InputRequest) -> None:
        """Render instruction to click an empty slot in hand."""
        ui.label(
            "Click an empty slot in your hand to place the card"
        ).classes("text-xs text-gray-400 mb-1 italic")

    def _render_pick_cards_to_see(self, request: InputRequest) -> None:
        """Render peek instructions — click cards in hand on the table."""
        num_to_see = request.extra.get("num_cards_to_see", 1)

        ui.label(
            "Click cards in your hand to select them for peeking"
        ).classes("text-xs text-gray-400 mb-1 italic")

        if self._selected_cards:
            ui.label(
                f"Selected: {', '.join(f'#{p}' for p in self._selected_cards)}"
            ).classes("text-sm text-yellow-300")

        self._peek_confirm_btn = ui.button(
            f"Confirm ({len(self._selected_cards)}/{num_to_see} selected)",
            on_click=lambda: self._submit_peek(num_to_see),
        ).props("color=positive").classes("mt-2")

    def _render_specify_spying(self, request: InputRequest) -> None:
        """Render spy instruction — click an opponent's card on the table."""
        ui.label(
            "Click an opponent's card on the table to spy on it"
        ).classes("text-xs text-gray-400 mb-1 italic")

    def _render_specify_swap(self, request: InputRequest) -> None:
        """Render swap instructions — 2-step click-based flow."""
        self._swap_own_idx = None
        self._swap_opponent = None

        self._swap_instruction = ui.label(
            "1. Click YOUR card to swap"
        ).classes("text-sm text-yellow-300 italic")

    def select_swap_own(self, pos: int) -> None:
        """Called from GameTable when own card is clicked during swap step 1."""
        self._swap_own_idx = pos
        if hasattr(self, "_swap_instruction") and self._swap_instruction:
            self._swap_instruction.set_text(
                f"Selected your card #{pos}. 2. Now click an opponent's card to swap with"
            )
        # Switch game table to opponent-clickable mode
        if self._game_table:
            self._game_table._clickable_mode = "specify_swap_opponent"
            # Re-render opponents to make them clickable
            if self._game_table._last_state:
                self._game_table._render_opponents_for_mode(
                    self._game_table._last_state
                )

    def complete_swap(self, opponent_name: str, opp_card_idx: int) -> None:
        """Called from GameTable when opponent card is clicked during swap step 2."""
        if self._swap_own_idx is None:
            ui.notify("Please select your card first!", type="warning")
            return
        self._submit({
            "own_card_idx": self._swap_own_idx,
            "opponent": opponent_name,
            "opp_card_idx": opp_card_idx,
        })

    def _render_card_reveal(self, request: InputRequest) -> None:
        """Render a card reveal (peek/spy) with prominent display and confirmation."""
        value = request.extra.get("value", "?")
        effect = request.extra.get("effect", "")

        if effect == "PEAK":
            title = "You peeked at your card!"
        else:
            title = "You spied on an opponent's card!"

        ui.label(title).classes("text-yellow-300 text-lg font-bold")
        with ui.row().classes("items-center justify-center gap-4 my-2"):
            from src.web.components.card_component import CardView as CV, render_card
            render_card(CV(position=0, value=value, is_known=True,
                          is_publicly_visible=False), size="normal")
        ui.label(f"Card value: {value}").classes("text-white text-xl font-bold text-center")
        ui.button("Got it!", on_click=lambda: self._submit("OK")).props(
            "color=positive size=lg"
        ).classes("mt-2")

    def _render_initial_peek_reveal(self, request: InputRequest) -> None:
        """Render the initial card peek with card values and confirmation."""
        known_cards = request.extra.get("known_cards", [])

        ui.label("Memorize your cards!").classes("text-yellow-300 text-lg font-bold")
        with ui.row().classes("items-center justify-center gap-4 my-2"):
            from src.web.components.card_component import CardView as CV, render_card
            for card_info in known_cards:
                render_card(CV(
                    position=card_info["position"],
                    value=card_info["value"],
                    is_known=True,
                    is_publicly_visible=False,
                ), size="normal", label=f"#{card_info['position']}")

        ui.button("Got it!", on_click=lambda: self._submit("OK")).props(
            "color=positive size=lg"
        ).classes("mt-2")

    def _render_round_end_confirm(self, request: InputRequest) -> None:
        """Render round-end summary confirmation."""
        kabo_caller = request.extra.get("kabo_caller", "")
        kabo_successful = request.extra.get("kabo_successful", False)

        ui.label("Round Complete!").classes("text-xl font-bold text-green-400")

        if kabo_caller:
            if kabo_successful:
                ui.label(f"{kabo_caller}'s KABO was successful!").classes(
                    "text-green-300 font-bold"
                )
            else:
                ui.label(f"{kabo_caller}'s KABO failed!").classes(
                    "text-red-300 font-bold"
                )

        ui.button(
            "Continue to Next Round",
            on_click=lambda: self._submit("OK"),
        ).props("color=positive size=lg").classes("mt-3")

        ui.label("Auto-continuing in 60s...").classes(
            "text-xs text-gray-500 mt-1"
        )

    def _render_generic_options(self, request: InputRequest) -> None:
        """Fallback: render simple buttons for each option."""
        with ui.row().classes("gap-2 flex-wrap"):
            for option in request.options:
                ui.button(
                    option,
                    on_click=lambda e, o=option: self._submit(o),
                ).classes("text-sm")

    def _toggle_card_selection(self, pos: int) -> None:
        if pos in self._selected_cards:
            self._selected_cards.remove(pos)
        else:
            self._selected_cards.append(pos)
        # Re-render the exchange panel (preserve current selection)
        if self._current_request:
            self.show_request(self._current_request, reset_selection=False)
            # Restore selection state visually
            # (handled by checking self._selected_cards in _render_pick_hand_cards_for_exchange)

    def _toggle_peek_selection(self, pos: int, max_select: int) -> None:
        if pos in self._selected_cards:
            self._selected_cards.remove(pos)
        elif len(self._selected_cards) < max_select:
            self._selected_cards.append(pos)
        else:
            # Replace last selection
            self._selected_cards[-1] = pos

        if hasattr(self, "_peek_confirm_btn") and self._peek_confirm_btn:
            self._peek_confirm_btn.text = (
                f"Confirm ({len(self._selected_cards)}/{max_select} selected)"
            )

    def _submit_peek(self, num_required: int) -> None:
        if len(self._selected_cards) == num_required:
            self._submit(list(self._selected_cards))
        else:
            ui.notify(
                f"Please select exactly {num_required} card(s)",
                type="warning",
            )

    def _submit(self, response) -> None:
        """Submit the response and show waiting state."""
        self._current_request = None
        self._selected_cards = []
        if self._game_table:
            self._game_table._clickable_mode = None
        self.show_waiting("Processing...")
        self._on_submit(response)
