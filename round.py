import itertools
from typing import List, Callable
from card import Card
from random import shuffle
from player import Player

class Round:
    """
    #TODO fill the constructor arguments
    """
    ... #TODO: implement me
    """
    One Round consists of shuffling the deck, dealing the cards and playing until end by Kabo or end by depleting the deck
    KICK-START the round in the constructor! 
    Increment the IDs of the rounds!
    1)  Generate the cards into the main deck
    2)  Deal the cards to the players
    3)  Put one card to the discard deck - maintain visibility
    4)  Let the players peek at 2 cards - maintain visibility
    5)  Let the players play
    6)  At the end of the round, get the score of the players in the round and use it to increment their game scores, 
        also take in consideration the effect of Kabo
    """
    id_incremental: Callable = itertools.count().__next__  # Probably bad - we will need to be able to reset the counter

    def __init__(self, cards: List[Card], players: List[Player], starting_player: Player):
        """
        Constructor method
        """
        self.id = Round.id_incremental()

        self.main_deck: List[Card] = cards
        shuffle(self.main_deck) #shuffles the cards in place

        self.players: List[Player] = players
        self._deal_cards_to_players()

        self.discard_pile: List[Card] = []
        self._discard_card() #init the discard pile

        self._let_players_see_cards()

        self._start_playing(starting_player= starting_player)

        #TODO: when to calculate the game scores (based on Kabo etc?) Some function at the end of round needed?

    def _deal_cards_to_players(self, cards_per_player: int = 4) -> None:
        """
        This function deals the cards to players hands
        :return:
        """
        for player in self.players:
            _new_hand: List[Card] = []
            for _ in range(cards_per_player):
                _new_hand.append(self.main_deck.pop())
            player.hand = _new_hand

    def _discard_card(self) -> None:
        """
        Method to move the card from the main deck on top of the discard pile (and handle its visibility)

        :return:
        """
        _new_card: Card = self.main_deck.pop()
        #Todo: handle visibility
        self.discard_pile.append(_new_card)

    def _let_players_see_cards(self, number_of_cards_to_see: int = 2) -> None:
        """
        Method calling all players in the round to see certain number of their cards.

        :param number_of_cards_to_see: int, denoting how many cards is each player allowed to see
        :return:
        """
        for player in self.players:
            player.check_own_cards(num_cards=number_of_cards_to_see)

    def _start_playing(self, starting_player: Player):
        """
        Method calling the Players to play until the end of Round is met.

        :param starting_player:
        :return:
        """