"""
Class Card
"""
import collections
import pygame

pygame.init()  # is this needed for every module?
from itertools import count
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from src.player import Player

from src.rules import (
    CARD_EFFECTS,
    CARD_LEGAL_VALUES,
    NUM_KINDS_FOR_MULTIPLE_DISCARD,
    CARD_IMAGE_PATH_ORIGINAL,
    CARD_IMAGE_PATH_SCRIBBLE,
)


class Card:
    """
    Class representing the cards available in the game. Class variables control the types of cards which are available
    in the game. Legal instances generate their effect based on value.
    :param value: int, value
    """

    _id_incremental: count = count(0)

    def __init__(self, value: int, using_gui: bool = False):
        """
        Constructor method
        """

        # Checking type and value of the input 'value'
        if not isinstance(value, int):
            raise TypeError(f"Card value needs to be an int. You passed {type(value)}.")

        if value not in CARD_LEGAL_VALUES:
            raise ValueError(
                f"The value you have entered is out of the legal range: {CARD_LEGAL_VALUES}"
            )

        self.value: int = value
        self.effect: Optional[str] = CARD_EFFECTS.get(
            value
        )  # get method returns None if key not available
        self.id: int = next(self._id_incremental)
        self.publicly_visible: bool = False
        self.known_to_owner: bool = False
        self.known_to_other_players: List[Player] = []
        self.status: str = "MAIN_DECK"  # other options are DISCARD_PILE and HAND
        self.owner: Optional[Player] = None
        if using_gui:
            self.image = pygame.image.load(CARD_IMAGE_PATH_SCRIBBLE.format(value))

    def __repr__(self):
        """
        Dunder returning the text describing the instance with extra id written, this one cannot be recreated by eval!
        :return: str
        """
        return f"Card({self.value}), id = {self.id}"

    def __str__(self):
        if self.publicly_visible:
            return str(self.value)
        else:
            return "X"

    @staticmethod
    def check_card_list_consistency(cards: List["Card"]) -> bool:
        """
        Check whether given list contains cards of same value
        :param cards: List[Card]
        :return: bool, truth statment whether all cards in the list have same value
        """
        _card_vals = [c.value for c in cards]
        _card_frequencies = collections.Counter(_card_vals)
        if len(_card_frequencies) > NUM_KINDS_FOR_MULTIPLE_DISCARD:
            return False
        else:
            return True
