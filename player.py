from itertools import count
from typing import List, Optional
from rules import POINT_VALUE_AFTER_HITTING_TARGET, KABO_MALUS, ALLOWED_PLAYS
from round import Round
from card import Card


class Player:
    """
    Class for representing individual players of the game
    :param name, str - name of the Player
    :param character, str - default = HUMAN. Type of the player, for now str, but can be changed to Enum or some other
                            alternative (CHECK options) - this should expect values HUMAN or COMPUTER
                            (later differentiate computer into different kinds of agents, GREEDY, RANDOM etc.)
    """

    _id_incremental: count = count(0)

    def __init__(self, name: str, character: str = 'HUMAN'):
        """
        Constructor method
        """
        self.name: str = name  # type checking of the input args?
        self.character: str = character  # type checking of the input args?
        self.hand: list = []
        self.matched_100: bool = False  # by 100 we mean generally the Game.TARGET_POINT_VALUE
        self.players_game_score: int = 0
        self.id: int = next(self._id_incremental)
        self.called_kabo: bool = False

        if character != 'HUMAN':
            raise ValueError("Sofar only human players are supported, other kinds of agents will be implemented later")

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
        elif other.id == self.id and other.name == self.name:
            return True
        else:
            return False

    def play_turn(self, round: Round) -> bool:
        """
        Instance method which performs the play of the player. Can be conditioned on self.character.
        :return: bool, representing whether the player called Kabo
        """

        """
        For human players this should take as an argument the type of move they want to play. For computer players,
        the move can be decided based on their character
        """
        _players_play_decision = ...  # TODO: implement me - for human player just ask for his decision, for comp. call strategy

        if _players_play_decision == 'KABO':
            self.call_kabo(round=round)
            return True
        elif _players_play_decision == 'HIT_DECK':
            self.hit_deck(round=round)
            return False
        elif _players_play_decision == 'HIT_DISCARD_PILE':
            self.hit_discard_pile(round=round)
            return False
        else:
            raise ValueError(
                f"The attempted type of play = {_players_play_decision} is not supported. Supported plays are {ALLOWED_PLAYS}")

    def get_players_score_in_round(self, round: Round) -> int:
        """
        Function to look through the hand of the player and count his score - Only reflects the score in the round!
        :param: Round, round in which we want to get the players score
        :return: int, player's score with the current hand
        """
        _sum_hand: int = sum([c.value for c in self.hand])

        if not self.called_kabo:
            return _sum_hand
        else:
            _other_player_scores: List[int] = [plr.get_players_score_in_round(round) for plr in round.players if
                                               plr != self]

            if min(_other_player_scores) < _sum_hand:  # Kabo successful
                return 0
            else:
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

    def check_own_cards(self, num_cards: int, which_hand_position: Optional[List[int]] = None) -> None:
        """
        Method to handle looking of the player at his/her own cards
        :param num_cards: int, number of own cards the player should see
        :param which_hand_position: List[int], positions of the cards in the players hand
                                    (which the player wants to see)
        :return:
        """
        if not isinstance(num_cards, int):
            raise TypeError(f"num_cards should be int, but it is {type(num_cards)}")

        if num_cards < 0 or num_cards > len(self.hand):
            raise ValueError(
                f"The desired number of cards to see = {num_cards} is out of range for hand of size {len(self.hand)}")

        if not isinstance(which_hand_position, list):
            raise TypeError(f"which_hand_position should be list of ints, but it is {type(which_hand_position)}")

        for position in which_hand_position:
            if not isinstance(position, int):
                raise TypeError(f"which_hand_position should contain ints, but it contains {type(position)}")
            if position < 0 or position > len(self.hand):
                raise ValueError(f"The desired position = {position} is out of range for hand of size {len(self.hand)}")

        if not which_hand_position:  # unspecified positions, check cards in the order from the left
            for card in self.hand[:num_cards]:
                card.visible_to_owner = True
        else:
            for position in which_hand_position:
                self.hand[position].visible_to_owner = True

    def card_checking_preference(self) -> List[int]:
        """
        Function which returns the positions of the cards that the player wants to look at the start of the round
        :return: List[int]
        """
        return []  # TODO: for human player we can query him for his/her preference here - by default no preference

    def reset_player_after_round(self) -> None:
        """
        Method which resets values of players attributes, which might have changed during round
        :return:
        """
        self.hand.clear()
        self.matched_100 = False
        self.called_kabo = False

    # TURNS:

    def call_kabo(self, round: Round) -> None:
        """
        Method to perform the logic of player calling Kabo
        :param: Round, current round
        :return:
        """
        if round.kabo_called:
            raise ValueError(f"Kabo cannot be called twice in the same round!")

        self.called_kabo = True

    def hit_deck(self, round: Round) -> None:
        """
        Method to perform the logic of player hitting the main deck for a new card
        :param round: Round, current round
        :return:
        """
        ...  # TODO: implement me - decide on using the effect (and how) or not, if switching card decide on the position (or double, triple switch...)

    def hit_discard_pile(self, round: Round) -> None:
        """
        Method to perform the logic of player hitting the discard pile for a new card - this one is publicly visible
        :param round: Round, current round
        :return:
        """
        ...  # TODO: implement me - if switching card decide on the position (or double, triple switch...)

    def peak(self, card: Card) -> None:
        """
        perform the effect 'Peak' and check the given card
        :param card: Card, the card to be peaked at as decided by the player
        :return:
        """
        card.known_to_owner = True

    def spy(self, card: Card) -> None:
        """
        perform the effect 'Spy' and check the given card
        :param card: Card, the card to be spied at as decided by the player
        :return:
        """
        card.known_to_other_players.append(self)

    def swap(self, own_card: Card, opponents_card: Card) -> None:
        """
        perform the effect 'Swap' and exchange the given cards
        :param own_card: Card, from own hand belonging to 'self'
        :param opponents_card: Card, from opponents hand
        :return:
        """
        ...  # TODO: implement me - be careful, owner changes - so handle for BOTH cards BOTH known to owner and known to other players!!!

    # TODO: implement the functions returning the players' decisions (on playing and on how to handle the card) - these might be overloaded based on players character (human/computer(type of agent...)) - check the polymorphism and inheritence in Python!
