from typing import List
from src.card import Card


class DiscardPile:
    def __init__(self, cards: List[Card]):
        self.cards: List[Card] = cards

    def add(self, card: Card):
        """
        Appending a card to the discard pile
        :param card: card to be discarded
        :return:
        """
        self.cards.append(card)

    def hit(self):
        """
        Hitting a card from the discard pile
        :return: Card: top card of the discard pile
        """
        return self.cards.pop()

    def __bool__(self):
        """
        Method for DiscardPile to have the same bool behaviour as list
        :return: bool
        """
        return bool(self.cards)

    def __getitem__(self, item):
        """
        Method to simplify an interaction with this object
        :param item: index to the list of cards
        :return:
        """
        return self.cards[item]
