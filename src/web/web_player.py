"""
WebPlayer - bridges the synchronous game thread with the async NiceGUI UI.

Each decision method emits a state snapshot + input request via EventBus,
then blocks on a queue.Queue until the UI submits the player's response.
"""
import queue
from typing import List, Optional, Type, Tuple, TypeVar

from src.player import Player
from src.card import Card
from src.round import Round
from src.web.event_bus import EventBus
from src.web.game_state import (
    GameStateSnapshot, PlayerView, CardView, InputRequest,
)

P = TypeVar("P", bound=Player)


class WebPlayer(Player):
    """Player subclass that gets input from a browser UI via queue-based blocking."""

    def __init__(self, name: str):
        super().__init__(name, character="WEB")
        self._response_queue: queue.Queue = queue.Queue()
        self.event_bus: Optional[EventBus] = None
        self._current_round: Optional[Round] = None

    def __hash__(self):
        return self.player_id

    def set_event_bus(self, bus: EventBus) -> None:
        self.event_bus = bus

    def submit_response(self, response) -> None:
        """Called from the UI thread to unblock the game thread."""
        self._response_queue.put(response)

    def _wait_for_response(self):
        """Block the game thread until the UI submits a response."""
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
        )

    def _can_see_card(self, card: Card, owner: Player) -> bool:
        """Only faceup (publicly_visible) cards are shown in the hand display.
        All other card values are hidden to preserve the memory challenge."""
        return card.publicly_visible

    def _emit_input_request(self, state: GameStateSnapshot) -> None:
        """Emit game state update with input request to UI."""
        if self.event_bus:
            self.event_bus.emit("state_update", state)
            self.event_bus.emit("input_request", state.input_request)

    # --- Decision methods ---

    def pick_turn_type(self, _round: Round = None) -> str:
        self._current_round = _round
        state = self._build_state_snapshot(_round)
        options = ["HIT_DECK", "HIT_DISCARD_PILE"]
        if not _round.kabo_called:
            options.append("KABO")
        state.input_request = InputRequest(
            request_type="pick_turn_type",
            prompt=f"Your turn! Discard pile top: {state.discard_top_value}. Choose your action:",
            options=options,
        )
        self._emit_input_request(state)
        response = self._wait_for_response()
        print(f"  {self.name} chose: {response}")
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
        return self._wait_for_response()

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
        if isinstance(response, int):
            response = [response]
        return [self.hand[i] for i in response]

    def pick_position_for_new_card(self, available_positions: List[int]) -> Optional[int]:
        if not available_positions:
            return None
        if len(available_positions) == 1:
            return available_positions[0]

        state = self._build_state_snapshot(self._current_round)
        state.input_request = InputRequest(
            request_type="pick_position_for_new_card",
            prompt="Choose where to place your new card:",
            options=[str(p) for p in available_positions],
        )
        self._emit_input_request(state)
        return int(self._wait_for_response())

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
            prompt="Choose an opponent and one of their cards to spy on:",
            extra={"opponents": opponent_info},
        )
        self._emit_input_request(state)
        response = self._wait_for_response()  # {"opponent": name, "card_idx": int}
        opponent = _round.get_player_by_name(response["opponent"])
        card = opponent.hand[response["card_idx"]]
        print(f"  {self.name} spies on {opponent.name}'s card at position {response['card_idx']}.")
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
            prompt="Choose your card, an opponent, and their card to swap:",
            extra={"opponents": opponent_info, "hand_info": hand_info},
        )
        self._emit_input_request(state)
        response = self._wait_for_response()
        # {"own_card_idx": int, "opponent": name, "opp_card_idx": int}
        opponent = _round.get_player_by_name(response["opponent"])
        print(f"  {self.name} swaps own card (pos {response['own_card_idx']}) "
              f"with {opponent.name}'s card (pos {response['opp_card_idx']}).")
        return opponent, response["own_card_idx"], response["opp_card_idx"]

    def report_known_cards_on_hand(self) -> None:
        """Send known cards info to UI via event bus."""
        hand_display = []
        for c in self.hand:
            if c.known_to_owner or c.publicly_visible:
                hand_display.append(str(c.value))
            else:
                hand_display.append("?")
        if self.event_bus:
            self.event_bus.emit("log", f"{self.name}'s hand: [{', '.join(hand_display)}]")

    def tell_player_card_value(self, card: Card, effect: str) -> None:
        """Show the peeked/spied card value to the web player."""
        if effect == "PEAK":
            msg = f"You peeked at your card: value is {card.value}"
        else:
            msg = f"You spied on a card: value is {card.value}"
        if self.event_bus:
            self.event_bus.emit("log", msg)
            self.event_bus.emit("card_revealed", {
                "effect": effect,
                "value": card.value,
            })
