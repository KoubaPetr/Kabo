"""
Class Card
"""
from itertools import count
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from player import Player

from rules import CARD_EFFECTS, CARD_LEGAL_VALUES


class Card:
    """
    Class representing the cards available in the game. Class variables control the types of cards which are available
    in the game. Legal instances generate their effect based on value.
    :param value: int, value
    """

    _id_incremental: count = count(0)

    def __init__(self, value: int):
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

    def __repr__(self):
        """
        Dunder returning the text describing the instance with extra id written, this one cannot be recreated by eval!
        :return: str
        """
        return f"Card({self.value}), id = {self.id}"
