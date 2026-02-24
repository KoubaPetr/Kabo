"""
AnimationAwareComputerPlayer - wraps ComputerPlayer to emit animation events.

After each sub-action, emits an AnimationEvent to all connected EventBuses
and sleeps to give the UI time to play the animation.
"""
import time
from typing import List, Optional, Type, Tuple, TypeVar

from src.computer_player import ComputerPlayer
from src.player import Player
from src.card import Card
from src.round import Round
from src.web.event_bus import EventBus
from src.web.game_state import AnimationEvent

P = TypeVar("P", bound=Player)


class AnimationAwareComputerPlayer(ComputerPlayer):
    """ComputerPlayer that emits animation events for the web UI."""

    def __init__(self, name: str, event_buses: Optional[List[EventBus]] = None):
        super().__init__(name)
        self._event_buses: List[EventBus] = event_buses or []
        self._current_round: Optional[Round] = None
        self._room = None  # Set by GameSession if in multiplayer

    def _emit_animation(self, event: AnimationEvent) -> None:
        for bus in self._event_buses:
            try:
                bus.emit("animation", event)
            except Exception:
                pass

    def _sleep_for(self, duration_ms: int) -> None:
        time.sleep(duration_ms / 1000.0)

    def _broadcast_state(self) -> None:
        """Push updated game state to all web players after an animation."""
        if self._room and self._current_round:
            self._room.broadcast_state_to_others(self.name, self._current_round)

    def perform_turn(self, _round: Round) -> bool:
        self._current_round = _round
        return super().perform_turn(_round)

    def hit_deck(self, _round: Round) -> None:
        _drawn_card: Card = _round.main_deck.cards.pop()

        self._emit_animation(AnimationEvent(
            animation_type="draw_deck",
            player_name=self.name,
            duration_ms=1500,
        ))
        self._sleep_for(1700)
        self._broadcast_state()

        decision_on_card = self.decide_on_card_use(_drawn_card)

        if decision_on_card == "KEEP":
            self.keep_drawn_card(drawn_card=_drawn_card, _round=_round)
        elif decision_on_card == "DISCARD":
            _round.discard_card(_drawn_card)
            self._emit_animation(AnimationEvent(
                animation_type="discard",
                player_name=self.name,
                card_value=_drawn_card.value,
                discard_top_value=_drawn_card.value,
                duration_ms=1200,
            ))
            self._sleep_for(1400)
            self._broadcast_state()
        elif decision_on_card == "EFFECT":
            _round.discard_card(_drawn_card)
            self._emit_animation(AnimationEvent(
                animation_type="discard",
                player_name=self.name,
                card_value=_drawn_card.value,
                discard_top_value=_drawn_card.value,
                duration_ms=1200,
            ))
            self._sleep_for(1400)
            self._broadcast_state()

            effect_to_function = {
                "KUK": self._animated_peak,
                "ŠPION": self._animated_spy,
                "KŠEFT": self._animated_swap,
            }
            effect_fn = effect_to_function[_drawn_card.effect]
            if _drawn_card.effect == "KUK":
                effect_fn()
            else:
                effect_fn(_round)

    def hit_discard_pile(self, _round: Round) -> None:
        if not _round.discard_pile:
            self.hit_deck(_round)
            return
        _top_discarded_card: Card = _round.discard_pile.hit()
        discard_val = _top_discarded_card.value

        self._emit_animation(AnimationEvent(
            animation_type="draw_discard",
            player_name=self.name,
            card_value=discard_val,
            duration_ms=1500,
        ))
        self._sleep_for(1700)
        self._broadcast_state()

        self.keep_drawn_card(_top_discarded_card, _round)
        _top_discarded_card.publicly_visible = True

    def keep_drawn_card(self, drawn_card: Card, _round: Round) -> None:
        super().keep_drawn_card(drawn_card, _round)
        self._emit_animation(AnimationEvent(
            animation_type="exchange",
            player_name=self.name,
            duration_ms=1500,
        ))
        self._sleep_for(1700)
        self._broadcast_state()

    def call_kabo(self, _round: Round) -> None:
        super().call_kabo(_round)
        self._emit_animation(AnimationEvent(
            animation_type="kabo_call",
            player_name=self.name,
            duration_ms=3000,
        ))
        self._sleep_for(3500)

    def _animated_peak(self) -> None:
        card_idx_to_be_seen = self.pick_cards_to_see(num_cards_to_see=1)
        peaked_card = self.hand[card_idx_to_be_seen[0]]
        peaked_card.known_to_owner = True

        self._emit_animation(AnimationEvent(
            animation_type="peek",
            player_name=self.name,
            card_positions=card_idx_to_be_seen,
            duration_ms=2500,
        ))
        self._sleep_for(2700)
        self._broadcast_state()

    def _animated_spy(self, _round: Round) -> None:
        spying_specs = self.specify_spying(_round)
        spied_opponent, spied_card = spying_specs
        spied_card.known_to_other_players.append(self)

        try:
            card_pos = spied_opponent.hand.index(spied_card)
        except ValueError:
            card_pos = 0

        self._emit_animation(AnimationEvent(
            animation_type="spy",
            player_name=self.name,
            target_player_name=spied_opponent.name,
            target_positions=[card_pos],
            duration_ms=2500,
        ))
        self._sleep_for(2700)
        self._broadcast_state()

    def _animated_swap(self, _round: Round) -> None:
        swapping_specs = self.specify_swap(_round)
        opponent, own_card_idx, opponents_card_idx = swapping_specs

        # Perform the swap
        self.hand[own_card_idx], opponent.hand[opponents_card_idx] = (
            opponent.hand[opponents_card_idx],
            self.hand[own_card_idx],
        )

        opponents_card = opponent.hand[opponents_card_idx]
        own_card = self.hand[own_card_idx]
        opponents_card.known_to_owner = opponent.check_knowledge_of_card(opponents_card)
        own_card.known_to_owner = self.check_knowledge_of_card(card=own_card)

        self._emit_animation(AnimationEvent(
            animation_type="swap",
            player_name=self.name,
            target_player_name=opponent.name,
            card_positions=[own_card_idx],
            target_positions=[opponents_card_idx],
            duration_ms=2000,
        ))
        self._sleep_for(2200)
        self._broadcast_state()

    def tell_player_card_value(self, card: Card, effect: str) -> None:
        pass
