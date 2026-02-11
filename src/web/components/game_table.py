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

from src.web.game_state import GameStateSnapshot, PlayerView, CardView, RoundSummary
from src.web.components.card_component import render_card, render_deck, render_discard_pile
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

    def build(self) -> None:
        """Create the full game table layout."""
        self._main_container = ui.column().classes(
            "w-full max-w-4xl mx-auto gap-4 p-4"
        )

        with self._main_container:
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

        # Render opponents
        if self._opponents_container:
            self._opponents_container.clear()
            with self._opponents_container:
                for opp in opponent_views:
                    self._render_opponent_hand(opp)

        # Render center (deck + discard)
        if self._center_container:
            self._center_container.clear()
            with self._center_container:
                render_deck(state.deck_cards_left)
                render_discard_pile(state.discard_top_value)

        # Render player's hand
        if self._player_hand_container:
            self._player_hand_container.clear()
            with self._player_hand_container:
                if web_player_view:
                    for card in web_player_view.cards:
                        render_card(card, size="normal", label=f"#{card.position}")

        # Update scoreboard
        self.scoreboard.update(state.players)

    def _render_opponent_hand(self, opponent: PlayerView) -> None:
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
                    render_card(card, size="small")

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
