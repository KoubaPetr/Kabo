from typing import List
from src.card import Card
from random import shuffle


class Deck:
    def __init__(self, cards: List[Card]):
        self.cards: List[Card] = cards

    def shuffle(self):
        """
        In place shuffles the cards in the deck
        :return:
        """
        shuffle(self.cards)
