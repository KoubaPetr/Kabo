from typing import Tuple, Dict, List

"""
File holding all the constants relevant for the game (coming from the rules)
"""

TARGET_POINT_VALUE: int = 100
POINT_VALUE_AFTER_HITTING_TARGET: int = 50
ALLOWED_PLAYER_COUNTS: Tuple[int, ...] = (2, 3, 4)
CARD_AMOUNTS: Dict[int, int] = {
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
NUMBER_OF_CARDS_TO_SEE: int = 2  # at the beginning of the Round, after the cards are dealt
CARDS_PER_PLAYER: int = 4  # number of cards to be dealt to each player at the beginning of round

CARD_LEGAL_VALUES: Tuple[int, ...] = tuple([i for i in range(14)])
CARD_EFFECTS: Dict[int, str] = {
    7: 'KUK',
    8: 'KUK',
    9: 'ŠPION',
    10: 'ŠPION',
    11: 'KŠEFT',
    12: 'KŠEFT'
}

KABO_MALUS: int = 10
ALLOWED_PLAYS: List[str] = ['KABO', 'HIT_DECK', 'HIT_DISCARD_PILE']