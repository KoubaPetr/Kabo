import pygame

# from src.game import Game
from src.rules import CARD_AMOUNTS
from src.graphics_config import *
from typing import Dict, Tuple
from src.card import Card
from src.discard_pile import DiscardPile

pygame.init()


class GUI:
    def __init__(self, game):  # TODO: Game not typed due to circular import
        self.bounds = BOUNDS
        self.window = pygame.display.set_mode(self.bounds)
        self.card_width = CARD_WIDTH
        self.card_height = CARD_HEIGHT
        self.card_gap = HAND_CARD_GAP
        self.main_deck_position = MAIN_DECK_POSITION
        self.discard_pile_position = DISCARD_PILE_POSITION
        self.cardBack = self.load_card(
            CARD_BACK_IMAGE_PATH_SCRIBBLE, CARD_WIDTH, CARD_HEIGHT
        )
        self.cardFronts = {
            value: self.load_card(
                CARD_IMAGE_PATH_SCRIBBLE.format(value),
                self.card_width,
                self.card_height,
            )
            for value in CARD_AMOUNTS.keys()
        }
        self.game = game
        self.discard_pile: DiscardPile = None
        pygame.display.set_caption(CAPTION)

    def load_card(self, path: str, width: int, height: int):
        """
        Load card image (front or back)
        :param path: path to image
        :param width: int, width to which rescale the image
        :param height: int, height to which rescale the image
        :return: image of the card
        """
        card = pygame.image.load(path)
        card = pygame.transform.scale(card, (width, height))
        return card

    def set_discard_pile(self, discard_pile: DiscardPile):
        """
        Setter to set the discard pile which is initialized in round only
        :param discard_pile:
        :return:
        """
        self.discard_pile = discard_pile

    def draw_card(self, card: Card, x: int, y: int, rotation: int = 0):
        """

        :param card: Card, card to be drawn
        :param x: int, x_position where to draw the card
        :param y: int, y_position where to draw the card
        :param rotated: int, degree of rotation of the image
        :return:
        """
        if card.publicly_visible:
            card_to_draw = self.cardFronts[card.value]
            card_to_draw = pygame.transform.rotate(card_to_draw, rotation)
        else:
            card_to_draw = self.cardBack
            card_to_draw = pygame.transform.rotate(card_to_draw, rotation)
        self.window.blit(card_to_draw, (x, y))

    def draw_discard_pile(self):
        """
        Given the discard pile (which is owned by round) draw the discard pile
        :return:
        """
        if self.discard_pile:
            self.draw_card(
                self.discard_pile[-1],
                x=self.discard_pile_position[0],
                y=self.discard_pile_position[1],
                rotation=0,
            )

    def get_hands_positions(self):
        """
        Based on the number of players, return the hand positions and orientations for the correct layout
        :return: hand_directions, hand_origins, rotation_degrees
        """
        if self.game.num_players == 2:
            hand_directions, hand_origins, rotation_degrees = (
                PLAYER_HANDS_DIRECTION_2_PLAYERS,
                PLAYER_HANDS_ORIGIN_2_PLAYERS,
                ROTATION_DEGREES_2_PLAYERS,
            )
        else:
            hand_directions, hand_origins, rotation_degrees = (
                PLAYER_HANDS_DIRECTION,
                PLAYER_HANDS_ORIGIN,
                ROTATION_DEGREES,
            )
        return hand_directions, hand_origins, rotation_degrees

    def get_card_in_hand_position(
        self,
        hand_directions: Dict[int, Tuple],
        hand_origins: Dict[int, Tuple],
        rotation_degrees: Tuple[int],
        p_position: int,
        c_position: int,
    ):
        """
        Select position and orientation for one card on hand of a player

        :param hand_directions:
        :param hand_origins:
        :param rotation_degrees:
        :param p_position:
        :param c_position:
        :return: int, int, int: where to place the card and how to orient it
        """
        width_direction, height_direction = hand_directions[p_position]
        origin_width, origin_height = hand_origins[p_position]
        rotation_degree = rotation_degrees[p_position]

        new_card_width_position = (
            origin_width
            + c_position * width_direction * self.card_width
            + self.card_gap
        )
        new_card_height_position = (
            origin_height
            + c_position * height_direction * self.card_width
            + self.card_gap
        )
        return new_card_width_position, new_card_height_position, rotation_degree

    def render_game(self):
        """
        Render the GUI
        :return:
        """
        self.window.fill(BACKGROUND_COLOR)
        # font = pygame.font.SysFont("arial", 60, True)
        self.window.blit(
            self.cardBack, self.main_deck_position
        )  # back of the Main deck

        self.draw_discard_pile()
        ### below is a reference circle, to check coordinates on the screen
        # pygame.draw.circle(
        #     surface=self.window,
        #     color="black",
        #     center=(
        #         BOUNDS[0] / 2 - (4 * CARD_WIDTH + 3 * HAND_CARD_GAP) / 2,
        #         HAND_EDGE_GAP,
        #     ),
        #     radius=5,
        # )
        hand_directions, hand_origins, rotation_degrees = self.get_hands_positions()

        for p_position, p in enumerate(self.game.players):  # render players hands
            # TODO: handle the case with too many cards on hand
            # TODO: Probably show players names and scores
            # TODO: fix the card orientation - to make it constant given a reference player
            # TODO: GUIs for each player - use rotation to have the player owning the gui in the "pole" position
            for c_position, c in enumerate(p.hand):  # render cards in those hands
                (
                    new_card_width_position,
                    new_card_height_position,
                    rotation_degree,
                ) = self.get_card_in_hand_position(
                    hand_directions,
                    hand_origins,
                    rotation_degrees,
                    p_position,
                    c_position,
                )
                self.draw_card(
                    card=c,
                    x=new_card_width_position,
                    y=new_card_height_position,
                    rotation=rotation_degree,
                )

    def update_screen(self):
        """
        Update the appearance of GUI
        :return:
        """
        self.render_game()
        pygame.display.update()

    # TODO: functions to animate moves (such as swap, peak, card exchange etc.)
