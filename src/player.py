"""
Class Player
"""
from itertools import count
from typing import List, Optional, Callable, Type, Tuple, Dict, TYPE_CHECKING
from src.card import Card
from src.round import Round
from config.rules import ALLOWED_PLAYS, KABO_MALUS, POINT_VALUE_AFTER_HITTING_TARGET

if TYPE_CHECKING:
    from src.human_player import P


class Player:
    """
    Class for representing individual players of the game
    :param name, str - name of the Player
    :param character, str - default = HUMAN. Type of the player, for now str, but can be changed to Enum or some other
                            alternative (CHECK options) - this should expect values HUMAN or COMPUTER
                            (later differentiate computer into different kinds of agents, GREEDY, RANDOM etc.)
    """

    _id_incremental: count = count(0)

    @classmethod
    def reset_id_counter(cls):
        cls._id_incremental = count(0)

    ### Function from the child classes
    pick_turn_type: Callable  # implemented in child class
    pick_hand_cards_for_exchange: Callable
    decide_on_card_use: Callable
    pick_position_for_new_card: Callable
    pick_cards_to_see: Callable
    specify_swap: Callable
    specify_spying: Callable
    report_known_cards_on_hand: Callable
    tell_player_card_value: Callable

    def __init__(self, name: str, character: str = "HUMAN"):
        """
        Constructor method
        """
        self.name: str = (
            name.upper()
        )  # type checking of the input args? #capitalize in the setter
        self.character: str = character  # type checking of the input args?
        self.hand: list = []
        self.matched_100: bool = False  # 100 is generally the TARGET_POINT_VALUE
        self.players_game_score: int = 0
        self.player_id: int = next(self._id_incremental)
        self.called_kabo: bool = False

    def __str__(self):
        """
        Dunder returning the text when instance of the class is passed to print()
        :return: str
        """
        return f"Player {self.name} (id={self.player_id})"

    def __repr__(self):
        """
        Dunder returning the text describing the instance, which can be passed to eval to generate same instance
        :return: str
        """
        return f"Player({self.name})"

    def __eq__(self, other) -> bool:
        """
        Defining equality of players
        :param other: Player
        :return: bool, whether the Players are equal
        """
        if not isinstance(other, Player):
            return False
        return bool(other.player_id == self.player_id and other.name == self.name)

    def perform_turn(self, _round: Round) -> bool:
        """
        Instance method which performs the play of the player. Can be conditioned on self.character.
        :param _round: Round - current round being played
        :return: bool, representing whether the player called Kabo
        """

        print(
            f"Player {self.name}'s turn. {self.name}'s hand: {[str(c) for c in self.hand]}. Top of Discard Pile has {_round.discard_pile[-1].value}. "
        )
        players_play_decision: str = self.pick_turn_type(_round=_round)

        if players_play_decision == "KABO":
            if _round.kabo_called:
                # KABO already called by another player, re-prompt or fall back to HIT_DECK
                print(f"{self.name} wanted KABO but it's already been called. Drawing from deck instead.")
                self.hit_deck(_round=_round)
                return False
            self.call_kabo(_round=_round)
            return True
        if players_play_decision == "HIT_DECK":
            self.hit_deck(_round=_round)
            return False
        if players_play_decision == "HIT_DISCARD_PILE":
            self.hit_discard_pile(_round=_round)
            return False

        raise ValueError(
            f"The attempted type of play = {players_play_decision} is not supported. Supported plays are {ALLOWED_PLAYS}"
        )

    def get_players_score_in_round(self, _round: Round) -> int:
        """
        Function to look through the hand of the player and count his score - Only reflects the score in the round!
        :param: Round, round in which we want to get the players score
        :return: int, player's score with the current hand
        """
        _sum_hand: int = sum([c.value for c in self.hand])

        if not self.called_kabo:
            return _sum_hand

        _other_player_scores: List[int] = [
            plr.get_players_score_in_round(_round)
            for plr in _round.players
            if plr != self
        ]

        if min(_other_player_scores) >= _sum_hand:  # Kabo successful
            return 0

        return _sum_hand + KABO_MALUS  # Kabo failed

    def reached_score_100(self) -> bool:
        """
        :param: target_value_to_drop_to, int, number specified in Game class, to which score drops after hitting
                target value (100) for the first time (usually 50)
        :return: bool,  value indicating whether the player hit 100 for second time already and the game
                        should not continue
        """

        if self.matched_100:
            _play_next_round = False
        else:
            self.matched_100 = True
            self.players_game_score = POINT_VALUE_AFTER_HITTING_TARGET
            _play_next_round = True
        return _play_next_round

    def check_knowledge_of_card(self, card: Card) -> bool:
        """
        function evaluating players knowledge of the card WITHOUT CONSIDERING PUBLIC VISIBILITY
        :param card: Card, the card which we are interested in
        :return: bool, True if Player knows the value of the card
        """

        if card in self.hand:  # the player is the owner
            return card.known_to_owner

        return self in card.known_to_other_players

    def check_own_cards(
        self, num_cards: int, which_position: Optional[List[int]] = None
    ) -> None:
        """
        Method to handle looking of the player at his/her own cards
        :param num_cards: int, number of own cards the player should see
        :param which_position: List[int], positions of the cards in the players hand
                                    (which the player wants to see)
        :return:
        """
        if not isinstance(num_cards, int):
            raise TypeError(f"num_cards should be int, but it is {type(num_cards)}")

        if num_cards < 0 or num_cards > len(self.hand):
            raise ValueError(
                f"The desired number of cards to see = {num_cards} is out of range for hand of size {len(self.hand)}"
            )

        if not isinstance(which_position, list):
            raise TypeError(
                f"which_hand_position should be list of ints, but it is {type(which_position)}"
            )

        for position in which_position:
            if not isinstance(position, int):
                raise TypeError(
                    f"which_hand_position should contain ints, but it contains {type(position)}"
                )
            if position < 0 or position >= len(self.hand):
                raise ValueError(
                    f"The desired position = {position} is out of range for hand of size {len(self.hand)}"
                )

        if not which_position:  # unspecified positions, check cards from the left
            for card in self.hand[:num_cards]:
                card.known_to_owner = True
        else:
            for position in which_position:
                self.hand[position].known_to_owner = True

    def card_checking_preference(self) -> List[int]:
        """
        Function which returns the positions of the cards that the player wants to look at the start of the round
        :return: List[int]
        """
        chosen_cards: List[int] = self.pick_cards_to_see(num_cards_to_see=2)
        return chosen_cards  # by default no preference (checking from left) can be empty list [] if no preference

    def reset_player_after_round(self) -> None:
        """
        Method which resets values of players attributes, which might have changed during round
        :return:
        """
        self.hand.clear()
        self.called_kabo = False

    def reset_player_after_game(self) -> None:
        """
        Method which resets values that persist across rounds but should reset between games
        :return:
        """
        self.matched_100 = False
        self.players_game_score = 0

    # TURNS:

    def call_kabo(self, _round: Round) -> None:
        """
        Method to perform the logic of player calling Kabo
        :param: Round, current round
        :return:
        """
        if _round.kabo_called:
            raise ValueError("Kabo cannot be called twice in the same round!")

        print(f"  {self.name} called KABO! Everyone gets one more turn.")
        self.called_kabo = True

    def hit_deck(self, _round: Round) -> None:
        """
        Method to perform the logic of player hitting the main deck for a new card
        :param _round: Round, current round
        :return:
        """
        _drawn_card: Card = _round.main_deck.cards.pop()
        decision_on_card = self.decide_on_card_use(_drawn_card)
        match decision_on_card:
            case "KEEP":
                self.keep_drawn_card(drawn_card=_drawn_card, _round=_round)
            case "DISCARD":
                _round.discard_card(_drawn_card)
            case "EFFECT":
                _round.discard_card(_drawn_card)
                effect_to_function: Dict[str, Callable] = {
                    "KUK": self.peak,
                    "ŠPION": self.spy,
                    "KŠEFT": self.swap,
                }
                effect_function: Callable = effect_to_function[_drawn_card.effect]
                if _drawn_card.effect == "KUK":
                    effect_function()
                else:
                    effect_function(_round)

    def hit_discard_pile(self, _round: Round) -> None:
        """
        Method to perform the logic of player hitting the discard pile for a new card - this one is publicly visible
        :param _round: Round, current round
        :return:
        """
        _top_discarded_card: Card = _round.discard_pile.hit()
        # here we assume visible card is automatically kept
        self.keep_drawn_card(_top_discarded_card, _round)
        # Per CABO rules: card taken from discard pile stays faceup in hand
        _top_discarded_card.publicly_visible = True

    def keep_drawn_card(self, drawn_card: Card, _round: Round) -> None:
        """
        invoked when player decided he/she wants to keep the drawn card
        :param drawn_card: Card, drawn from MAIN_DECK or DISCARD_PILE - to be kept
        :param _round: Round, current round
        :return:
        """
        drawn_card.status = "HAND"
        drawn_card.publicly_visible = False
        drawn_card.known_to_owner = True

        _cards_to_be_discarded: List[Card] = self.pick_hand_cards_for_exchange(
            drawn_card=drawn_card
        )
        _discarding_corectness = Card.check_card_list_consistency(
            _cards_to_be_discarded
        )
        if _discarding_corectness:
            self.perform_card_exchange(_cards_to_be_discarded, drawn_card, _round)
        else:
            self.failed_multi_exchange(drawn_card, _cards_to_be_discarded, _round)

    def perform_card_exchange(
        self, cards_selected_for_exchange: List[Card], drawn_card: Card, _round: Round
    ) -> None:
        """
        Perform
        :param cards_selected_for_exchange: List[Card] cards selected by the player for discarding (in exchange for a new card)
        :param drawn_card: Card, new drawn card which will be kept in players hand
        :param _round: Round, current round
        :return:
        """
        _free_slots: List[int] = []
        for card in cards_selected_for_exchange:
            _round.discard_card(card)
            _card_idx: int = self.hand.index(card)
            _free_slots.append(_card_idx)
            self.hand[_card_idx] = None

        position_for_new_card: Optional[int] = self.pick_position_for_new_card(
            _free_slots
        )

        if isinstance(position_for_new_card, int):
            self.hand[position_for_new_card] = drawn_card
            self.hand = [c for c in self.hand if c]  # filter Nones
        else:
            _round.discard_card(drawn_card)

    def failed_multi_exchange(self, drawn_card: Card, attempted_cards: List[Card], _round: Round) -> None:
        """
        invoked when multi exchange card was attempted but inconsistent cards were selected for exchange.
        Per official rules: attempted cards are turned face-up, and if 3+ cards were attempted,
        a penalty card is drawn from the deck face-down.
        :param drawn_card: Card, drawn card to be added to hand
        :param attempted_cards: List[Card], the cards the player attempted to exchange
        :param _round: Round, current round (needed for penalty card draw)
        :return:
        """
        # The attempted cards are turned face-up
        for card in attempted_cards:
            card.publicly_visible = True

        # Add the drawn card to the hand
        self.hand.append(drawn_card)

        # If 3+ cards were attempted and failed, draw a penalty card from the deck
        if len(attempted_cards) >= 3 and _round.main_deck.cards:
            penalty_card: Card = _round.main_deck.cards.pop()
            penalty_card.status = "HAND"
            self.hand.append(penalty_card)

    def peak(self) -> None:
        """
        perform the effect 'Peak' and ask the player which card he/she wants to see, and show it to him/her
        :return:
        """
        card_idx_to_be_seen: List[int] = self.pick_cards_to_see(num_cards_to_see=1)
        peaked_card: Card = self.hand[card_idx_to_be_seen[0]]
        peaked_card.known_to_owner = True
        self.tell_player_card_value(peaked_card, "PEAK")

    def spy(self, _round: Round) -> None:
        """
        perform the effect 'Spy' and ask the player what opponent and what card he/she wants to see
        :param _round: Round, current round
        :return:
        """
        spying_specs: Tuple[Type[P], Card] = self.specify_spying(_round)
        spied_opponent, spied_card = spying_specs
        spied_card.known_to_other_players.append(self)
        self.tell_player_card_value(spied_card, "SPY")

    def swap(self, _round: Round) -> None:
        """
        perform the effect 'Swap' and ask the player to specify details (opponent and involved cards)
        :param _round: Round, current round
        :return:
        """
        swapping_specs: Tuple[Type[P], int, int] = self.specify_swap(_round)
        opponent, own_card_idx, opponents_card_idx = swapping_specs

        # switch cards
        self.hand[own_card_idx], opponent.hand[opponents_card_idx] = (
            opponent.hand[opponents_card_idx],
            self.hand[own_card_idx],
        )

        # after exchange
        opponents_card: Card = opponent.hand[opponents_card_idx]
        own_card: Card = self.hand[own_card_idx]

        # update knowledge of the cards to
        # TODO: below: remove the owner from 'known to other players" (could be done as a setter of known_to_owner)
        opponents_card.known_to_owner = opponent.check_knowledge_of_card(opponents_card)
        own_card.known_to_owner = self.check_knowledge_of_card(card=own_card)
