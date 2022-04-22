import itertools
from typing import Dict, List, Tuple
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
    def __init__(self, cards: List[Card], players: List[Player]):
        """
        Constructor method
        """

        self.main_deck: List[Card] = cards
        shuffle(self.main_deck) #shuffles the cards in place

        self.players: List[Player] = players
        self._deal_cards_to_players()

        self.discard_pile: List[Card] = []
        self._discard_card() #init the discard pile

        #TODO: let the players peek at 2 cards

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

    def _discard_card(self):
        """
        Method to move the card from the main deck on top of the discard pile (and handle its visibility)
        :return:
        """
        _new_card: Card = self.main_deck.pop()
        #Todo: handle visibility
        self.discard_pile.append(_new_card)

    # def _show_card_to_owner(self):
    #     ...  # TODO: implement me
    #     raise NotImplementedError('_show_card_to_owner function has not yet been implemented')