"""
File holding all the constants relevant for the game (coming from the rules)
"""
from typing import Dict, List, Tuple
import os

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
    13: 2,
}
# at the beginning of the Round, after the cards are dealt
NUMBER_OF_CARDS_TO_SEE: int = 2
# number of cards to be dealt to each player at the beginning of round
CARDS_PER_PLAYER: int = 4

CARD_LEGAL_VALUES: Tuple[int, ...] = tuple([i for i in range(14)])
CARD_EFFECTS: Dict[int, str] = {
    7: "KUK",
    8: "KUK",
    9: "ŠPION",
    10: "ŠPION",
    11: "KŠEFT",
    12: "KŠEFT",
}

KABO_MALUS: int = 10
ALLOWED_PLAYS: List[str] = ["KABO", "HIT_DECK", "HIT_DISCARD_PILE"]

# edit if in the rules more than 4 are allowed
NUMBER_OF_CARDS_FOR_KAMIKADZE: List[int] = [4]
KAMIKADZE_VALUES: Dict[int, int] = {12: 2, 13: 2}
KAMIKADZE_PENALTY: int = 50

# when multi-discarding how many different values are allowed
NUM_KINDS_FOR_MULTIPLE_DISCARD: int = 1
MAIN_DECK_CARD_DECISIONS: List[str] = ["KEEP", "DISCARD", "EFFECT"]
DISCARD_PILE_CARD_DECISIONS: List[str] = ["KEEP", "DISCARD"]

# paths to images
CARD_IMAGE_PATH_ORIGINAL = os.path.join("images", "original", "card_{}.svg")
CARD_IMAGE_PATH_SCRIBBLE = os.path.join("images", "scribble", "card_{}.svg")
