import itertools
from typing import List, Callable
from card import Card
from random import shuffle
from player import Player
from rules import NUMBER_OF_CARDS_TO_SEE, CARDS_PER_PLAYER

class Round:
    """
    Class representing single round of the game, that is part of game starting with cards being dealt and ending after
    Kabo or deck of cards being empty

    :param cards: List[Card], copy of the global game list of all the cards
    :param players: List[Player], players playing the round
    """

    id_incremental: Callable = itertools.count().__next__  # Probably bad - we will need to be able to reset the counter

    def __init__(self, cards: List[Card], players: List[Player]):
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

        self._start_playing()

        #TODO: when to calculate the game scores (based on Kabo etc?) Some function at the end of round needed?

    def _deal_cards_to_players(self, cards_per_player: int = 4) -> None:
        """
        This function deals the cards to players hands
        :return:
        """
        for player in self.players:
            for _ in range(CARDS_PER_PLAYER):
                _dealt_card: Card = self.main_deck.pop()
                self._deal_single_card(_dealt_card, player)

    def _deal_single_card(self, card: Card, player: Player) -> None:
        """

        :param card: Card, to be dealt
        :param player: Player, to be given the card
        :return:
        """
        player.hand.append(card)
        card.status = 'HAND'
        card.owner = player

    def _discard_card(self) -> None:
        """
        Method to move the card from the main deck on top of the discard pile (and handle its visibility)

        :return:
        """
        _new_card: Card = self.main_deck.pop()
        _new_card.status = 'DISCARD_PILE'
        _new_card.publicly_visible = True #maybe cover the previously top card and make it again not visible?

        self.discard_pile.append(_new_card)

    def _let_players_see_cards(self) -> None:
        """
        Method calling all players in the round to see certain number of their cards.
        :return:
        """
        for player in self.players:
            _which_cards = player.card_checking_preference()
            player.check_own_cards(num_cards=NUMBER_OF_CARDS_TO_SEE, which_hand_position= _which_cards)

    def _start_playing(self):
        """
        Method calling the Players to play until the end of Round is reached.

        :return:
        """
        ... #TODO