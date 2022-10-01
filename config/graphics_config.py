import os

### PATHS TO IMGS
CARD_IMAGE_PATH_ORIGINAL = os.path.join("images", "original", "card_{}.svg")
CARD_IMAGE_PATH_SCRIBBLE = os.path.join("images", "scribble", "card_{}.svg")
CARD_BACK_IMAGE_PATH_SCRIBBLE = os.path.join("images", "scribble", "card_back.svg")

### BOARD AND CARD DIMS AND PARAMS
BOUNDS = 800, 800  # 1024, 768
BACKGROUND_COLOR = (15, 169, 0)
CAPTION = "Kabo"
CARD_WIDTH, CARD_HEIGHT = 100, 140  # 238, 332

### DECKS PARAMS
PILES_GAP = 50
MAIN_DECK_POSITION = int(BOUNDS[0] / 2 - CARD_WIDTH / 2), int(
    BOUNDS[1] / 2 - CARD_HEIGHT / 2
)
DISCARD_PILE_POSITION = (
    MAIN_DECK_POSITION[0] + CARD_WIDTH + PILES_GAP,
    MAIN_DECK_POSITION[1],
)

### HAND PARAMS
HAND_CARD_GAP = 20
HAND_EDGE_GAP = 60  # the gap between cards on hand and closest edge of the board

PLAYER_HANDS_ORIGIN = {
    0: (BOUNDS[0] / 2 - (4 * CARD_WIDTH + 3 * HAND_CARD_GAP) / 2, HAND_EDGE_GAP),
    1: (
        BOUNDS[0] - HAND_EDGE_GAP - CARD_HEIGHT,
        BOUNDS[1] / 2 - (4 * CARD_WIDTH + 3 * HAND_CARD_GAP) / 2,
    ),
    2: (
        BOUNDS[0] / 2 + (4 * CARD_WIDTH + 3 * HAND_CARD_GAP) / 2 - CARD_WIDTH,
        BOUNDS[1] - HAND_EDGE_GAP - CARD_HEIGHT,
    ),
    3: (
        HAND_EDGE_GAP,
        BOUNDS[1] / 2 + (4 * CARD_WIDTH + 3 * HAND_CARD_GAP) / 2 - CARD_WIDTH,
    ),
}
PLAYER_HANDS_ORIGIN_2_PLAYERS = {0: PLAYER_HANDS_ORIGIN[0], 1: PLAYER_HANDS_ORIGIN[2]}
PLAYER_HANDS_DIRECTION = {0: (1, 0), 1: (0, 1), 2: (-1, 0), 3: (0, -1)}
PLAYER_HANDS_DIRECTION_2_PLAYERS = {0: (1, 0), 1: (-1, 0)}

ROTATION_DEGREES = (0, 90, 180, 270)
ROTATION_DEGREES_2_PLAYERS = (0, 180)
