import itertools
from typing import Callable, Tuple, Dict, List, Optional
from player import Player

class Card:
    """
    Class representing the cards available in the game. Class variables control the types of cards which are available
    in the game. Legal instances generate their effect based on value.

    :param value: int, value
    """
    legal_values: Tuple[int,...] = tuple([i for i in range(14)])
    effects: Dict[int,str] = {
        7: 'KUK',
        8: 'KUK',
        9: 'ŠPION',
        10: 'ŠPION',
        11: 'KŠEFT',
        12: 'KŠEFT'
               }
    id_incremental: Callable = itertools.count().__next__ #Probably bad - we will need to be able to reset the counter

    def __init__(self, value: int):
        """
        Constructor method
        """

        # Checking type and value of the input 'value'
        if not isinstance(value,int):
            raise TypeError(f'Card value needs to be an int. You passed {type(value)}.')

        if value not in Card.legal_values:
            raise ValueError(f'The value you have entered is out of the legal range: {Card.legal_values}')

        self.value: int = value
        self.effect: Optional[str] = Card.effects.get(value) #get method returns None if key not available
        self.id: int = Card.id_incremental() #gets the incremental id of the card
        self.publicly_visible: bool = False
        self.known_to_owner: bool = False
        self.known_to_other_players: List[Player] = []
        self.status: str = 'MAIN_DECK' #other options are DISCARD_PILE and HAND
        self.owner: Optional[Player] = None

    def __repr__(self):
        """
        Dunder returning the text describing the instance with extra id written, this one cannot be recreated by eval!
        :return: str
        """
        return f"Card({self.value}), id = {self.id}"

    #Todo: function for handling visibility