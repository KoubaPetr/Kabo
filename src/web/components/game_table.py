"""
Main game table view - renders the full game board.

Layout:
  - Top: Opponent hands
  - Center: Deck + Discard pile
  - Bottom: Player's hand
  - Below: Action panel
  - Footer: Game log + Scoreboard
"""
from nicegui import ui, app
from typing import Optional

from src.web.game_state import (
    GameStateSnapshot, PlayerView, CardView, RoundSummary, TurnNotification,
)
from src.web.components.card_component import render_card, render_card_back, render_deck, render_discard_pile
from src.web.components.game_log import GameLog
from src.web.components.scoreboard import Scoreboard
from src.web.components.action_panel import ActionPanel


class GameTable:
    """Manages the complete game table UI."""

    def __init__(self, on_submit):
        """
        Args:
            on_submit: callback(response) when user submits an action
        """
        self.on_submit = on_submit
        self.game_log = GameLog()
        self.scoreboard = Scoreboard()
        self.action_panel = ActionPanel(on_submit=on_submit)

        # UI containers for dynamic updates
        self._opponents_container = None
        self._center_container = None
        self._player_hand_container = None
        self._status_label = None
        self._main_container = None
        self._notification_container = None
        self._notification_timer = None
        # Click-to-interact state
        self._clickable_mode: Optional[str] = None
        self._last_state: Optional[GameStateSnapshot] = None

    def build(self) -> None:
        """Create the full game table layout."""
        # Add CSS animations for cards
        ui.add_head_html("""
        <style>
        @keyframes slideFromDeck {
            0% { transform: translateX(-100px) translateY(-50px) scale(0.5); opacity: 0; }
            100% { transform: translateX(0) translateY(0) scale(1); opacity: 1; }
        }
        @keyframes slideToDiscard {
            0% { transform: translateX(0) translateY(0) scale(1); opacity: 1; }
            100% { transform: translateX(100px) translateY(-50px) scale(0.5); opacity: 0; }
        }
        @keyframes flipCard {
            0% { transform: perspective(400px) rotateY(0deg); }
            50% { transform: perspective(400px) rotateY(90deg); }
            100% { transform: perspective(400px) rotateY(0deg); }
        }
        @keyframes cardAppear {
            0% { transform: scale(0.3); opacity: 0; }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); opacity: 1; }
        }
        .animate-draw { animation: slideFromDeck 0.4s ease-out; }
        .animate-discard { animation: slideToDiscard 0.3s ease-in; }
        .animate-flip { animation: flipCard 0.5s ease-in-out; }
        .animate-appear { animation: cardAppear 0.3s ease-out; }
        .card-hover:hover { transform: translateY(-4px); transition: transform 0.15s ease; }
        </style>
        """)

        self._main_container = ui.column().classes(
            "w-full max-w-4xl mx-auto gap-4 p-4"
        )

        with self._main_container:
            # Notification overlay
            self._notification_container = ui.element("div").classes(
                "w-full text-center hidden"
            ).style(
                "transition: all 0.3s ease-in-out;"
            )

            # Status bar
            with ui.row().classes("w-full items-center justify-between"):
                self._status_label = ui.label("Game starting...").classes(
                    "text-lg font-bold text-yellow-300"
                )
                self._round_label = ui.label("").classes("text-sm text-gray-400")

            # Opponents section
            self._opponents_container = ui.row().classes(
                "w-full justify-center gap-6 flex-wrap"
            )

            ui.separator()

            # Center: Deck + Discard
            self._center_container = ui.row().classes(
                "w-full justify-center items-center gap-8"
            )

            ui.separator()

            # Player's hand
            ui.label("Your Hand").classes("text-sm font-bold text-gray-300")
            self._player_hand_container = ui.row().classes(
                "w-full justify-center gap-3"
            )

            ui.separator()

            # Action panel
            self.action_panel._game_table = self
            self.action_panel.build()

            # Bottom: Log + Scoreboard side by side
            with ui.row().classes("w-full gap-4"):
                with ui.column().classes("flex-grow"):
                    self.game_log.build()
                with ui.column().classes("w-48"):
                    self.scoreboard.build()

    def update_state(self, state: GameStateSnapshot) -> None:
        """Update the entire table from a game state snapshot."""
        if not self._main_container:
            return

        # Detect changes for animations
        prev_hand_count = 0
        if self._last_state:
            for p in self._last_state.players:
                if p.is_current_player:
                    prev_hand_count = len(p.cards)
                    break
        self._last_state = state

        # Handle round_over phase with summary display
        if state.phase == "round_over" and state.round_summary:
            self._show_round_summary(state)
            return

        # Update status
        if self._status_label:
            if state.kabo_called:
                self._status_label.set_text(
                    f"KABO called by {state.kabo_caller}! Final turns..."
                )
                self._status_label.classes(replace="text-lg font-bold text-red-400")
            elif (state.active_turn_player_name
                  and state.active_turn_player_name != state.current_player_name):
                # Multiplayer: another player's turn
                self._status_label.set_text(
                    f"Waiting for {state.active_turn_player_name}..."
                )
                self._status_label.classes(replace="text-lg font-bold text-gray-400")
            else:
                self._status_label.set_text("Your turn!")
                self._status_label.classes(replace="text-lg font-bold text-yellow-300")
                # Show YOUR TURN notification for pick_turn_type
                if (state.input_request and
                        state.input_request.request_type == "pick_turn_type"):
                    self.show_notification(TurnNotification(
                        message="YOUR TURN!",
                        notification_type="your_turn",
                        player_name=state.current_player_name,
                    ))

        if self._round_label:
            self._round_label.set_text(
                f"Round {state.round_number + 1} | Deck: {state.deck_cards_left}"
            )

        # Find the web player (is_current_player=True)
        web_player_view = None
        opponent_views = []
        for p in state.players:
            if p.is_current_player:
                web_player_view = p
            else:
                opponent_views.append(p)

        # Render opponents (clickable in spy/swap modes)
        opponents_clickable = self._clickable_mode in (
            "specify_spying", "specify_swap_opponent"
        )
        if self._opponents_container:
            self._opponents_container.clear()
            with self._opponents_container:
                for opp in opponent_views:
                    self._render_opponent_hand(
                        opp, clickable=opponents_clickable
                    )

        # Determine clickable mode from input request
        self._clickable_mode = None
        if state.input_request:
            rt = state.input_request.request_type
            if rt == "pick_turn_type":
                self._clickable_mode = "pick_turn_type"
            elif rt in ("pick_hand_cards_for_exchange", "pick_cards_to_see"):
                self._clickable_mode = rt
            elif rt == "pick_position_for_new_card":
                self._clickable_mode = "pick_position_for_new_card"
            elif rt == "specify_spying":
                self._clickable_mode = "specify_spying"
            elif rt == "specify_swap":
                self._clickable_mode = "specify_swap_own"

        # Render center (deck + discard)
        deck_clickable = (self._clickable_mode == "pick_turn_type")
        discard_clickable = (self._clickable_mode == "pick_turn_type"
                             and state.discard_top_value is not None)
        if self._center_container:
            self._center_container.clear()
            with self._center_container:
                render_deck(
                    state.deck_cards_left,
                    clickable=deck_clickable,
                    on_click=self._on_deck_click if deck_clickable else None,
                )
                render_discard_pile(
                    state.discard_top_value,
                    clickable=discard_clickable,
                    on_click=self._on_discard_click if discard_clickable else None,
                )

        # Render player's hand
        hand_clickable = self._clickable_mode in (
            "pick_hand_cards_for_exchange", "pick_cards_to_see",
            "pick_position_for_new_card", "specify_swap_own",
        )
        cur_hand_count = len(web_player_view.cards) if web_player_view else 0
        hand_changed = (cur_hand_count != prev_hand_count and prev_hand_count > 0)
        if self._player_hand_container:
            self._player_hand_container.clear()
            with self._player_hand_container:
                if web_player_view:
                    for card in web_player_view.cards:
                        selected = card.position in self.action_panel._selected_cards
                        anim = "animate-appear" if hand_changed else ""
                        render_card(
                            card, size="normal",
                            label=f"#{card.position}",
                            clickable=hand_clickable,
                            selected=selected,
                            animate=anim,
                            on_click=(
                                lambda p=card.position: self._on_hand_card_click(p)
                            ) if hand_clickable else None,
                        )
                    # Show empty slot placeholders for pick_position_for_new_card
                    if self._clickable_mode == "pick_position_for_new_card":
                        available = state.input_request.options if state.input_request else []
                        existing_positions = {c.position for c in web_player_view.cards}
                        for pos_str in available:
                            pos = int(pos_str)
                            if pos not in existing_positions:
                                render_card_back(
                                    size="normal",
                                    label=f"#{pos} (empty)",
                                    clickable=True,
                                    on_click=lambda p=pos: self._on_hand_card_click(p),
                                )

        # Update scoreboard
        self.scoreboard.update(state.players)

    def _render_opponent_hand(self, opponent: PlayerView,
                              clickable: bool = False) -> None:
        """Render a single opponent's hand."""
        with ui.column().classes("items-center gap-1"):
            label_text = opponent.name
            if opponent.character == "COMPUTER":
                label_text += " (AI)"
            if opponent.called_kabo:
                label_text += " [KABO]"
            ui.label(label_text).classes("text-sm font-bold text-gray-300")
            with ui.row().classes("gap-1"):
                for card in opponent.cards:
                    render_card(
                        card, size="small",
                        clickable=clickable,
                        on_click=(
                            lambda n=opponent.name, idx=card.position:
                                self._on_opponent_card_click(n, idx)
                        ) if clickable else None,
                    )

    def _on_deck_click(self) -> None:
        """Handle click on the deck - submit HIT_DECK."""
        self._clickable_mode = None
        self.action_panel._submit("HIT_DECK")

    def _on_discard_click(self) -> None:
        """Handle click on the discard pile - submit HIT_DISCARD_PILE."""
        self._clickable_mode = None
        self.action_panel._submit("HIT_DISCARD_PILE")

    def _on_hand_card_click(self, position: int) -> None:
        """Handle click on a hand card - toggle selection or submit position."""
        if self._clickable_mode == "pick_hand_cards_for_exchange":
            self.action_panel._toggle_card_selection(position)
        elif self._clickable_mode == "pick_cards_to_see":
            num_to_see = 1
            if self.action_panel._current_request:
                num_to_see = self.action_panel._current_request.extra.get(
                    "num_cards_to_see", 1)
            self.action_panel._toggle_peek_selection(position, num_to_see)
        elif self._clickable_mode == "pick_position_for_new_card":
            self._clickable_mode = None
            self.action_panel._submit(position)
        elif self._clickable_mode == "specify_swap_own":
            self.action_panel.select_swap_own(position)

    def _on_opponent_card_click(self, opponent_name: str, card_idx: int) -> None:
        """Handle click on an opponent's card — for spy or swap."""
        if self._clickable_mode == "specify_spying":
            self._clickable_mode = None
            self.action_panel._submit({
                "opponent": opponent_name,
                "card_idx": card_idx,
            })
        elif self._clickable_mode == "specify_swap_opponent":
            self._clickable_mode = None
            self.action_panel.complete_swap(opponent_name, card_idx)

    def _render_opponents_for_mode(self, state: GameStateSnapshot) -> None:
        """Re-render opponents section with current clickable mode."""
        opponent_views = [p for p in state.players if not p.is_current_player]
        opponents_clickable = self._clickable_mode in (
            "specify_spying", "specify_swap_opponent"
        )
        if self._opponents_container:
            self._opponents_container.clear()
            with self._opponents_container:
                for opp in opponent_views:
                    self._render_opponent_hand(
                        opp, clickable=opponents_clickable
                    )

    def show_notification(self, notification: TurnNotification) -> None:
        """Display an animated notification banner."""
        if not self._notification_container:
            return

        self._notification_container.clear()
        self._notification_container.classes(remove="hidden")

        style_map = {
            "your_turn": (
                "bg-yellow-600 text-white text-xl font-bold py-3 px-6 rounded-lg "
                "animate-pulse shadow-lg"
            ),
            "opponent_action": (
                "bg-blue-700 text-white text-base font-semibold py-2 px-4 rounded-lg "
                "shadow-md"
            ),
            "kabo_called": (
                "bg-red-700 text-white text-xl font-bold py-3 px-6 rounded-lg "
                "animate-bounce shadow-lg"
            ),
        }
        css = style_map.get(notification.notification_type,
                            "bg-gray-700 text-white py-2 px-4 rounded-lg")

        with self._notification_container:
            ui.label(notification.message).classes(css)

        # Auto-dismiss: YOUR_TURN stays 3s, opponent actions 4s, kabo 5s
        dismiss_ms = {
            "your_turn": 3000,
            "opponent_action": 4000,
            "kabo_called": 5000,
        }.get(notification.notification_type, 3000)

        # Cancel previous dismiss timer
        if self._notification_timer:
            self._notification_timer.deactivate()

        self._notification_timer = ui.timer(
            dismiss_ms / 1000.0, self._dismiss_notification, once=True
        )

    def _dismiss_notification(self) -> None:
        """Hide the notification container."""
        if self._notification_container:
            self._notification_container.classes(add="hidden")
            self._notification_container.clear()
        self._notification_timer = None

    def _show_round_summary(self, state: GameStateSnapshot) -> None:
        """Display round-end summary with all cards revealed and scores."""
        summary = state.round_summary

        if self._status_label:
            self._status_label.set_text(f"Round {summary.round_number + 1} Complete!")
            self._status_label.classes(replace="text-xl font-bold text-green-400")

        if self._round_label:
            if summary.kabo_caller:
                result = "Successful!" if summary.kabo_successful else "Failed!"
                self._round_label.set_text(
                    f"KABO by {summary.kabo_caller}: {result}"
                )
            else:
                self._round_label.set_text("Deck depleted")

        # Show all players' revealed hands (opponents section)
        if self._opponents_container:
            self._opponents_container.clear()
            with self._opponents_container:
                for pv in state.players:
                    if not pv.is_current_player:
                        self._render_opponent_hand(pv)

        # Show center area with round scores
        if self._center_container:
            self._center_container.clear()
            with self._center_container:
                with ui.card().classes("p-4"):
                    ui.label("Round Scores").classes(
                        "text-lg font-bold text-yellow-300 mb-2"
                    )
                    for name, score in sorted(
                        summary.round_scores.items(), key=lambda x: x[1]
                    ):
                        game_total = summary.game_scores.get(name, 0)
                        with ui.row().classes("items-center gap-2 w-full"):
                            ui.label(name).classes("text-white font-bold w-24")
                            ui.label(f"+{score}").classes("text-yellow-300")
                            ui.label(f"(Total: {game_total})").classes(
                                "text-gray-400 text-sm"
                            )

        # Show the current player's revealed hand
        if self._player_hand_container:
            self._player_hand_container.clear()
            with self._player_hand_container:
                web_pv = next((p for p in state.players if p.is_current_player), None)
                if web_pv:
                    for card in web_pv.cards:
                        render_card(card, size="normal", label=f"#{card.position}")

        # Update scoreboard
        self.scoreboard.update(state.players)

    def show_game_over(self, state: GameStateSnapshot) -> None:
        """Show game over screen."""
        if self._status_label:
            self._status_label.set_text("Game Over!")
            self._status_label.classes(replace="text-2xl font-bold text-green-400")

        if self.action_panel._container:
            self.action_panel._container.clear()
            with self.action_panel._container:
                ui.label("Game Over!").classes("text-xl font-bold text-white")
                # Show final scores
                sorted_players = sorted(state.players, key=lambda p: p.game_score)
                for i, p in enumerate(sorted_players):
                    medal = ["🥇", "🥈", "🥉"]
                    prefix = medal[i] if i < 3 else f"{i+1}."
                    ui.label(f"{prefix} {p.name}: {p.game_score} points").classes(
                        "text-lg text-white"
                    )
                def play_again():
                    app.storage.user.pop("room_code", None)
                    app.storage.user.pop("player_name", None)
                    ui.navigate.to("/")

                ui.button("Play Again", on_click=play_again).props(
                    "color=positive size=lg"
                ).classes("mt-4")
