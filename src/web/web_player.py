"""
WebPlayer - bridges the synchronous game thread with the async NiceGUI UI.

Each decision method emits a state snapshot + input request via EventBus,
then blocks on a queue.Queue until the UI submits the player's response.

In multiplayer, also broadcasts state to other players via the GameRoom.
"""
import queue
from typing import List, Optional, Type, Tuple, TypeVar

from src.player import Player
from src.card import Card
from src.round import Round
from src.web.event_bus import EventBus
from src.web.game_state import (
    GameStateSnapshot, PlayerView, CardView, InputRequest, RoundSummary,
    TurnNotification,
)

P = TypeVar("P", bound=Player)


class WebPlayer(Player):
    """Player subclass that gets input from a browser UI via queue-based blocking."""

    def __init__(self, name: str):
        super().__init__(name, character="WEB")
        self._response_queue: queue.Queue = queue.Queue()
        self.event_bus: Optional[EventBus] = None
        self._current_round: Optional[Round] = None
        self._room = None  # GameRoom reference for multiplayer
        self._last_new_card_position: Optional[int] = None

    def __hash__(self):
        return self.player_id

    def set_event_bus(self, bus: EventBus) -> None:
        self.event_bus = bus

    def set_room(self, room) -> None:
        """Set the GameRoom for multiplayer broadcasting."""
        self._room = room

    def submit_response(self, response) -> None:
        """Called from the UI thread to unblock the game thread."""
        self._response_queue.put(response)

    def _wait_for_response(self):
        """Block the game thread until the UI submits a response.

        Blocks indefinitely — regular game actions should not time out.
        Only round-end confirmation uses a separate timeout.
        """
        return self._response_queue.get()

    def _build_state_snapshot(self, _round: Optional[Round] = None,
                              phase: str = "playing") -> GameStateSnapshot:
        """Build a GameStateSnapshot from the perspective of this player."""
        players = []
        if _round:
            for p in _round.players:
                cards = []
                for i, card in enumerate(p.hand):
                    if card is None:
                        continue
                    visible = self._can_see_card(card, p)
                    cards.append(CardView(
                        position=i,
                        value=card.value if visible else None,
                        is_known=visible,
                        is_publicly_visible=card.publicly_visible,
                    ))
                players.append(PlayerView(
                    name=p.name,
                    character=p.character,
                    is_current_player=(p == self),
                    cards=cards,
                    game_score=p.players_game_score,
                    called_kabo=p.called_kabo,
                ))

            discard_top = _round.discard_pile[-1].value if _round.discard_pile else None
            deck_left = len(_round.main_deck.cards)
            round_number = _round.round_id
            kabo_called = _round.kabo_called
            kabo_caller = ""
            for p in _round.players:
                if p.called_kabo:
                    kabo_caller = p.name
                    break
        else:
            # No round context - build minimal state from self.hand
            cards = []
            for i, card in enumerate(self.hand):
                if card is None:
                    continue
                visible = card.publicly_visible
                cards.append(CardView(
                    position=i,
                    value=card.value if visible else None,
                    is_known=visible,
                    is_publicly_visible=card.publicly_visible,
                ))
            players = [PlayerView(
                name=self.name,
                character=self.character,
                is_current_player=True,
                cards=cards,
                game_score=self.players_game_score,
                called_kabo=self.called_kabo,
            )]
            discard_top = None
            deck_left = 0
            round_number = 0
            kabo_called = False
            kabo_caller = ""

        return GameStateSnapshot(
            phase=phase,
            round_number=round_number,
            current_player_name=self.name,
            discard_top_value=discard_top,
            deck_cards_left=deck_left,
            players=players,
            kabo_called=kabo_called,
            kabo_caller=kabo_caller,
            scores={p.name: p.game_score for p in players},
            active_turn_player_name=self.name,
        )

    def _can_see_card(self, card: Card, owner: Player) -> bool:
        """Only faceup (publicly_visible) cards are shown in the hand display.
        All other card values are hidden to preserve the memory challenge."""
        return card.publicly_visible

    def _emit_input_request(self, state: GameStateSnapshot) -> None:
        """Emit game state update with input request to UI.

        In multiplayer, also broadcasts a 'waiting' state to other players.
        """
        if self.event_bus:
            self.event_bus.emit("state_update", state)
            self.event_bus.emit("input_request", state.input_request)

        # Broadcast to other players in the room
        if self._room and self._current_round:
            self._room.broadcast_state_to_others(
                self.name, self._current_round
            )

    # --- Notification broadcasting ---

    def _broadcast_action(self, action_type: str, description: str,
                          extra: dict = None) -> None:
        """Broadcast an action notification to all other players."""
        if not self._room:
            return
        notification = TurnNotification(
            message=description,
            notification_type="opponent_action",
            action_type=action_type,
            player_name=self.name,
            extra=extra or {},
        )
        with self._room._lock:
            others = {name: info for name, info in self._room.players.items()
                      if name != self.name}
        for name, info in others.items():
            bus = info.get("event_bus")
            if bus:
                try:
                    bus.emit("notification", notification)
                except Exception:
                    pass

    # --- Round lifecycle ---

    def notify_round_start(self, _round: Round) -> None:
        """Broadcast initial table state to this player at round start."""
        self._current_round = _round
        state = self._build_state_snapshot(_round)
        state.input_request = InputRequest(
            request_type="waiting",
            prompt="Round starting... waiting for players to peek at cards.",
            options=[],
        )
        if self.event_bus:
            self.event_bus.emit("state_update", state)
            self.event_bus.emit("input_request", state.input_request)

    # --- Overrides for state emission and log masking ---

    def perform_card_exchange(self, cards_selected_for_exchange: List[Card],
                              drawn_card: Card, _round: Round) -> None:
        """Override to mask card values in print when log toggle is off."""
        show_values = not self._room or getattr(self._room, "show_revelations", False)
        if show_values:
            super().perform_card_exchange(cards_selected_for_exchange, drawn_card, _round)
        else:
            # Call super but suppress its print by temporarily redirecting
            import io, sys
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            try:
                super().perform_card_exchange(cards_selected_for_exchange, drawn_card, _round)
            finally:
                sys.stdout = old_stdout
            count = len(cards_selected_for_exchange)
            print(f"  {self.name} exchanged {count} card(s) for a new card.")

    def failed_multi_exchange(self, drawn_card: Card,
                              attempted_cards: List[Card], _round: Round) -> None:
        """Override to mask card values in print when log toggle is off."""
        show_values = not self._room or getattr(self._room, "show_revelations", False)
        if show_values:
            super().failed_multi_exchange(drawn_card, attempted_cards, _round)
        else:
            import io, sys
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            try:
                super().failed_multi_exchange(drawn_card, attempted_cards, _round)
            finally:
                sys.stdout = old_stdout
            count = len(attempted_cards)
            print(f"  Exchange FAILED! {self.name} attempted {count} cards but they don't match.")

    def keep_drawn_card(self, drawn_card: Card, _round: Round) -> None:
        """Override to emit updated state after exchange completes."""
        super().keep_drawn_card(drawn_card, _round)
        # Emit updated state so UI reflects changes (extra cards, face-up cards)
        if self._room:
            self._room.broadcast_state_to_others(self.name, _round)
        state = self._build_state_snapshot(_round)

        extra = {}
        if self._last_new_card_position is not None:
            try:
                new_idx = self.hand.index(drawn_card)
                extra["new_card_index"] = new_idx
                extra["compacted"] = True
            except ValueError:
                pass
            self._last_new_card_position = None

        state.input_request = InputRequest(
            request_type="waiting", prompt="Exchange complete.", options=[],
            extra=extra)
        if self.event_bus:
            self.event_bus.emit("state_update", state)

    # --- Decision methods ---

    def pick_turn_type(self, _round: Round = None) -> str:
        self._current_round = _round
        state = self._build_state_snapshot(_round)
        options = ["HIT_DECK"]
        if _round.discard_pile:
            options.append("HIT_DISCARD_PILE")
        if not _round.kabo_called:
            options.append("KABO")
        state.input_request = InputRequest(
            request_type="pick_turn_type",
            prompt=f"Your turn! Discard pile top: {state.discard_top_value}. Choose your action:",
            options=options,
        )
        self._emit_input_request(state)
        response = self._wait_for_response()
        if response is None:
            response = "HIT_DECK"  # safe default on timeout
        print(f"  {self.name} chose: {response}")
        # Broadcast action to other players
        action_map = {
            "HIT_DECK": ("draw_deck", f"{self.name} draws from deck"),
            "HIT_DISCARD_PILE": ("draw_discard", f"{self.name} takes from discard pile"),
            "KABO": ("kabo", f"{self.name} calls KABO!"),
        }
        action_type, desc = action_map.get(response, ("unknown", f"{self.name} acts"))
        notification_type = "kabo_called" if response == "KABO" else "opponent_action"
        if self._room:
            notification = TurnNotification(
                message=desc, notification_type=notification_type,
                action_type=action_type, player_name=self.name,
            )
            with self._room._lock:
                others = {n: info for n, info in self._room.players.items()
                          if n != self.name}
            for n, info in others.items():
                bus = info.get("event_bus")
                if bus:
                    try:
                        bus.emit("notification", notification)
                    except Exception:
                        pass
        return response

    def decide_on_card_use(self, card: Card) -> str:
        state = self._build_state_snapshot(self._current_round)
        options = ["KEEP", "DISCARD"]
        if card.effect:
            options.append("EFFECT")
        state.input_request = InputRequest(
            request_type="decide_on_card_use",
            prompt=f"You drew card {card.value}"
                   + (f" ({card.effect})" if card.effect else "")
                   + ". What do you want to do?",
            options=options,
            extra={"drawn_card_value": card.value, "drawn_card_effect": card.effect},
        )
        self._emit_input_request(state)
        response = self._wait_for_response()
        if response is None:
            response = "DISCARD"
        # Broadcast decision to other players
        decision_map = {
            "KEEP": ("keep", f"{self.name} keeps the drawn card"),
            "DISCARD": ("discard", f"{self.name} discards the drawn card"),
            "EFFECT": ("effect", f"{self.name} uses card effect: {card.effect}"),
        }
        action_type, desc = decision_map.get(response, ("unknown", f"{self.name} acts"))
        self._broadcast_action(action_type, desc)
        return response

    def pick_hand_cards_for_exchange(self, drawn_card: Card) -> List[Card]:
        state = self._build_state_snapshot(self._current_round)
        hand_info = []
        for i, c in enumerate(self.hand):
            visible = c.publicly_visible
            hand_info.append({"pos": i, "value": c.value if visible else None})

        state.input_request = InputRequest(
            request_type="pick_hand_cards_for_exchange",
            prompt=f"You're keeping card {drawn_card.value}. Select card(s) in your hand to discard:",
            options=[str(i) for i in range(len(self.hand))],
            extra={"drawn_card_value": drawn_card.value, "hand_info": hand_info},
        )
        self._emit_input_request(state)
        response = self._wait_for_response()  # list of position ints
        if response is None:
            response = [0]
        if isinstance(response, int):
            response = [response]
        return [self.hand[i] for i in response]

    def pick_position_for_new_card(self, available_positions: List[int]) -> Optional[int]:
        if not available_positions:
            return None
        chosen = max(available_positions)
        self._last_new_card_position = chosen
        return chosen

    def pick_cards_to_see(self, num_cards_to_see: int) -> List[int]:
        state = self._build_state_snapshot(self._current_round, phase="peek")
        state.input_request = InputRequest(
            request_type="pick_cards_to_see",
            prompt=f"Choose {num_cards_to_see} card(s) to peek at:",
            options=[str(i) for i in range(len(self.hand))],
            extra={"num_cards_to_see": num_cards_to_see},
        )
        self._emit_input_request(state)
        response = self._wait_for_response()  # list of ints
        if response is None:
            return list(range(num_cards_to_see))
        if isinstance(response, int):
            response = [response]
        return response

    def specify_spying(self, _round: Round) -> Tuple[Type[P], Card]:
        opponents = [p for p in _round.players if p != self]
        opponent_info = []
        for opp in opponents:
            opponent_info.append({
                "name": opp.name,
                "hand_size": len(opp.hand),
            })

        state = self._build_state_snapshot(_round)
        state.input_request = InputRequest(
            request_type="specify_spying",
            prompt="Click an opponent's card on the table to spy on it:",
            extra={"opponents": opponent_info},
        )
        self._emit_input_request(state)
        response = self._wait_for_response()  # {"opponent": name, "card_idx": int}
        if response is None:
            opp = opponents[0]
            return opp, opp.hand[0]
        opponent = _round.get_player_by_name(response["opponent"])
        card = opponent.hand[response["card_idx"]]
        print(f"  {self.name} spies on {opponent.name}'s card at position {response['card_idx']}.")
        self._broadcast_action(
            "spy", f"{self.name} spied on {opponent.name}'s card at position {response['card_idx']}")
        return opponent, card

    def specify_swap(self, _round: Round) -> Tuple[Type[P], int, int]:
        opponents = [p for p in _round.players if p != self]
        opponent_info = []
        for opp in opponents:
            opponent_info.append({
                "name": opp.name,
                "hand_size": len(opp.hand),
            })
        hand_info = []
        for i, c in enumerate(self.hand):
            visible = c.publicly_visible
            hand_info.append({"pos": i, "value": c.value if visible else None})

        state = self._build_state_snapshot(_round)
        state.input_request = InputRequest(
            request_type="specify_swap",
            prompt="Click your card first, then an opponent's card to swap:",
            extra={"opponents": opponent_info, "hand_info": hand_info},
        )
        self._emit_input_request(state)
        response = self._wait_for_response()
        if response is None:
            opp = opponents[0]
            return opp, 0, 0
        # {"own_card_idx": int, "opponent": name, "opp_card_idx": int}
        opponent = _round.get_player_by_name(response["opponent"])
        print(f"  {self.name} swaps own card (pos {response['own_card_idx']}) "
              f"with {opponent.name}'s card (pos {response['opp_card_idx']}).")
        self._broadcast_action(
            "swap", f"{self.name} swapped a card with {opponent.name}")
        return opponent, response["own_card_idx"], response["opp_card_idx"]

    def report_known_cards_on_hand(self) -> None:
        """Show known cards to the web player and wait for confirmation."""
        known_cards = []
        hand_display = []
        for i, c in enumerate(self.hand):
            if c.known_to_owner or c.publicly_visible:
                hand_display.append(str(c.value))
                known_cards.append({"position": i, "value": c.value})
            else:
                hand_display.append("?")

        # Log: show values only if toggle is on or solo mode (no room)
        show_values = not self._room or getattr(self._room, "show_revelations", False)
        if self.event_bus:
            if show_values:
                self.event_bus.emit("log", f"{self.name}'s hand: [{', '.join(hand_display)}]")
            else:
                self.event_bus.emit("log", "Memorize your starting cards!")

        # Build revealed_cards for in-place display on game table
        revealed_cards = [
            {"owner": self.name, "position": kc["position"], "value": kc["value"]}
            for kc in known_cards
        ]

        # Action panel always shows actual card values for the viewing player
        state = self._build_state_snapshot(self._current_round)
        state.input_request = InputRequest(
            request_type="initial_peek_reveal",
            prompt=f"Your cards: [{', '.join(hand_display)}]. Memorize them!",
            options=["OK"],
            extra={"known_cards": known_cards, "hand_display": hand_display,
                   "revealed_cards": revealed_cards},
        )
        self._emit_input_request(state)
        self._wait_for_response()

    def tell_player_card_value(self, card: Card, effect: str) -> None:
        """Show the peeked/spied card value and wait for player confirmation."""
        if effect == "PEAK":
            full_msg = f"You peeked at your card: value is {card.value}"
            masked_msg = "You peeked at your card"
        else:
            full_msg = f"You spied on a card: value is {card.value}"
            masked_msg = "You spied on a card"

        # Log: show value only if toggle is on or solo mode (no room)
        show_values = not self._room or getattr(self._room, "show_revelations", False)
        log_msg = full_msg if show_values else masked_msg
        if self.event_bus:
            self.event_bus.emit("log", log_msg)

        # Build revealed card info for in-place display on game table
        revealed_cards = []
        if effect == "PEAK":
            try:
                card_position = self.hand.index(card)
            except ValueError:
                card_position = -1
            revealed_cards.append({
                "owner": self.name, "position": card_position, "value": card.value,
            })
        else:  # SPY
            owner = card.owner
            if owner:
                try:
                    card_position = owner.hand.index(card)
                except ValueError:
                    card_position = -1
                revealed_cards.append({
                    "owner": owner.name, "position": card_position, "value": card.value,
                })

        # Action panel always shows the actual card value for the viewing player
        state = self._build_state_snapshot(self._current_round)
        state.input_request = InputRequest(
            request_type="card_reveal",
            prompt=full_msg,
            options=["OK"],
            extra={"value": card.value, "effect": effect,
                   "revealed_cards": revealed_cards},
        )
        self._emit_input_request(state)
        self._wait_for_response()

    def wait_for_round_end_confirmation(self, round_summary: RoundSummary,
                                        _round: Round) -> None:
        """Show round-end summary and wait for player to confirm continuation."""
        # Build state with all cards revealed
        state = self._build_state_snapshot(_round, phase="round_over")
        # Replace player views with fully revealed versions
        state.players = round_summary.player_hands
        # Mark the current player in the revealed views
        for pv in state.players:
            pv.is_current_player = (pv.name == self.name)
        state.round_summary = round_summary
        state.input_request = InputRequest(
            request_type="round_end_confirm",
            prompt="Round complete! Review scores and continue.",
            options=["OK"],
            extra={
                "round_scores": round_summary.round_scores,
                "game_scores": round_summary.game_scores,
                "kabo_caller": round_summary.kabo_caller,
                "kabo_successful": round_summary.kabo_successful,
            },
        )
        if self.event_bus:
            self.event_bus.emit("state_update", state)
            self.event_bus.emit("input_request", state.input_request)
        # Block with timeout - auto-continue if player doesn't confirm
        try:
            self._response_queue.get(timeout=60)
        except queue.Empty:
            pass
