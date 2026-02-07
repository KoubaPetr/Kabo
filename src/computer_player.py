"""
Class ComputerPlayer - AI player with basic greedy strategy
"""
import random
from src.player import Player
from src.round import Round
from src.card import Card
from typing import List, Optional, Type, Tuple, TypeVar

P = TypeVar("P", bound=Player)

KABO_THRESHOLD = 5  # Call kabo when estimated hand sum <= this


class ComputerPlayer(Player):
    """
    AI player that uses a basic greedy strategy:
    - Tracks known card values
    - Calls kabo when estimated hand sum is low
    - Prefers keeping low-value cards and discarding high-value ones
    """

    def __init__(self, name: str):
        super().__init__(name, character="COMPUTER")

    def __hash__(self):
        return self.player_id

    def _known_hand_values(self) -> List[Optional[int]]:
        """Return list of known card values in hand (None for unknown)."""
        result = []
        for card in self.hand:
            if card.known_to_owner or card.publicly_visible:
                result.append(card.value)
            else:
                result.append(None)
        return result

    def _estimated_hand_sum(self) -> float:
        """Estimate total hand value. Unknown cards assumed to be average (~6)."""
        total = 0.0
        for val in self._known_hand_values():
            if val is not None:
                total += val
            else:
                total += 6.0  # average card value estimate
        return total

    def _highest_known_card_index(self) -> Optional[int]:
        """Return index of the highest known card in hand, or None."""
        best_idx = None
        best_val = -1
        for i, card in enumerate(self.hand):
            if (card.known_to_owner or card.publicly_visible) and card.value > best_val:
                best_val = card.value
                best_idx = i
        return best_idx

    def pick_turn_type(self, _round: Round = None) -> str:
        estimated = self._estimated_hand_sum()
        if estimated <= KABO_THRESHOLD:
            return "KABO"

        # Check discard pile top - if it's low and we have a known high card, take it
        if _round and _round.discard_pile:
            discard_top = _round.discard_pile[-1].value
            highest_idx = self._highest_known_card_index()
            if highest_idx is not None:
                highest_val = self.hand[highest_idx].value
                if discard_top < highest_val and discard_top <= 4:
                    return "HIT_DISCARD_PILE"

        return "HIT_DECK"

    def decide_on_card_use(self, card: Card) -> str:
        known_values = self._known_hand_values()
        avg_known = None
        known_count = sum(1 for v in known_values if v is not None)
        if known_count > 0:
            avg_known = sum(v for v in known_values if v is not None) / known_count

        # If card has a useful effect, use it
        if card.effect:
            return "EFFECT"

        # If card is low, keep it (replacing highest known card)
        if avg_known is not None and card.value < avg_known:
            return "KEEP"

        # If card value is low enough in absolute terms, keep it
        if card.value <= 3:
            return "KEEP"

        return "DISCARD"

    def pick_hand_cards_for_exchange(self, drawn_card: Card) -> List[Card]:
        """Replace the highest known-value card, or a random card if none known."""
        highest_idx = self._highest_known_card_index()
        if highest_idx is not None:
            return [self.hand[highest_idx]]

        # No known cards - pick a random one
        return [random.choice(self.hand)]

    def pick_position_for_new_card(self, available_positions: List[int]) -> Optional[int]:
        if not available_positions:
            return None
        return available_positions[0]

    def pick_cards_to_see(self, num_cards_to_see: int) -> List[int]:
        """Look at cards not yet known."""
        unknown_indices = [
            i for i, card in enumerate(self.hand)
            if not card.known_to_owner and not card.publicly_visible
        ]
        # Prefer unknown cards
        if len(unknown_indices) >= num_cards_to_see:
            return unknown_indices[:num_cards_to_see]
        # Fill with any indices if not enough unknown
        all_indices = list(range(len(self.hand)))
        selected = unknown_indices[:]
        for idx in all_indices:
            if idx not in selected and len(selected) < num_cards_to_see:
                selected.append(idx)
        return selected[:num_cards_to_see]

    def specify_spying(self, _round: Round) -> Tuple[Type[P], Card]:
        """Spy on a random opponent's random unknown card."""
        opponents = [p for p in _round.players if p != self]
        opponent = random.choice(opponents)
        # Pick a card we don't know about
        unknown_cards = [
            (i, c) for i, c in enumerate(opponent.hand)
            if self not in c.known_to_other_players and not c.publicly_visible
        ]
        if unknown_cards:
            idx, card = random.choice(unknown_cards)
        else:
            idx = random.randrange(len(opponent.hand))
            card = opponent.hand[idx]
        return opponent, card

    def specify_swap(self, _round: Round) -> Tuple[Type[P], int, int]:
        """Swap own highest known card with a random opponent's unknown card."""
        own_idx = self._highest_known_card_index()
        if own_idx is None:
            own_idx = random.randrange(len(self.hand))

        opponents = [p for p in _round.players if p != self]
        opponent = random.choice(opponents)
        opp_idx = random.randrange(len(opponent.hand))
        return opponent, own_idx, opp_idx

    def report_known_cards_on_hand(self) -> None:
        """AI doesn't need to print its hand to the terminal."""
        pass

    def tell_player_card_value(self, card: Card, effect: str) -> None:
        """AI notes the card value internally (already tracked via known_to_owner)."""
        pass
