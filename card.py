import itertools

class Card:
    """
    Class representing the cards available in the game. Class variables control the types of cards which are available
    in the game. Legal instances generate their effect based on value.

    :param value: int, value
    """
    legal_values = tuple([i for i in range(14)])
    effects = {
        7: 'KUK',
        8: 'KUK',
        9: 'ŠPION',
        10: 'ŠPION',
        11: 'KŠEFT',
        12: 'KŠEFT'
               }
    id_incremental = itertools.count()

    def __init__(self, value: int):
        """
        Constructor method
        """

        # Checking type and value of the input 'value'
        if not isinstance(value,int):
            raise TypeError(f'Card value needs to be an int. You passed {type(value)}.')

        if value not in Card.legal_values:
            raise ValueError(f'The value you have entered is out of the legal range: {Card.legal_values}')

        self.value = value
        self.effect = Card.effects.get(value) #get method returns None if key not available
        self.id = next(Card.id_incremental) #gets the incremental id of the card