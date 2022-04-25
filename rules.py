from typing import Tuple, Dict

"""
File holding all the constants relevant for the game (coming from the rules)
"""

TARGET_POINT_VALUE: int = 100
POINT_VALUE_AFTER_HITTING_TARGET: int = 50
ALLOWED_PLAYER_COUNTS: Tuple[int, ...] = (2, 3, 4)
CARD_AMMOUNTS: Dict[int, int] = {
        0: 2,
        1: 4,
        2: 4,
        3: 4,
        4: 4,
        5: 4,
        6: 4,
        7: 4,
        8: 4,
        9: 4,
        10: 4,
        11: 4,
        12: 4,
        13: 2
    }
NUMBER_OF_CARDS_TO_SEE: int = 2 #at the beggining of the Round, after the cards are dealt
CARDS_PER_PLAYER: int = 4 #number of cards to be dealt to each player at the beggining of round