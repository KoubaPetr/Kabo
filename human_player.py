"""
Class HumanPlayer is a subclass of Player class, which specifies Players playing behaviour in such a way,
which allowes interactive input by a user
"""
from player import Player
from rules import ALLOWED_PLAYS, MAIN_DECK_CARD_DECISIONS, DISCARD_PILE_CARD_DECISIONS
from typing import List
from card import Card


class HumanPlayer(Player):
    """
    Expects same argument as Player.__init__ to instantiate the respective parent
    :param name, str - name of the Player
    :param character, str - default = HUMAN. Type of the player, for now str, but can be changed to Enum or some other
                            alternative (CHECK options) - this should expect values HUMAN or COMPUTER
                            (later differentiate computer into different kinds of agents, GREEDY, RANDOM etc.)
    """

    def __hash__(self):
        """
        gets the parents id (Player.id) and returns it as a hash
        :return: int
        """
        return self.id

    def pick_turn_type(self) -> str:
        """
        Method which asks the player to input the type of play he/she wants to play
        :return: str , play type chosen by the human player
        """
        input_turn: str = input(
            "Choose your type of play KABO/HIT_DECK/HIT_DISCARD_PILE\n"
        )
        input_turn = input_turn.strip()
        input_turn = input_turn.upper()

        if input_turn not in ALLOWED_PLAYS:
            raise ValueError(
                f"Input play type = {input_turn} unknown. Only plays {ALLOWED_PLAYS} are allowed."
            )
        return input_turn

    def pick_hand_cards_for_exchange(self) -> List[Card]:
        """
        Method which asks the player to input the positions of the cards in his/her hand which he/she wants to exchange
        :return: List[Card] , cards chosen for exchange
        """
        chosen_cards: str = input(
            f"Pick the cards you wish to exchange (numbered from left in your hand = {[str(card) for card in self.hand]}\n"
        )
        chosen_cards = chosen_cards.strip()
        chosen_cards_list: List[str] = chosen_cards.split()
        _selected_cards: List[Card] = []

        for card_position in chosen_cards_list:
            try:
                card_position_int: int = int(card_position)
                if card_position_int in range(len(self.hand)):
                    _selected_card: Card = self.hand[card_position_int]
                    _selected_cards.append(_selected_card)
                else:
                    raise ValueError(
                        f"The inputed card position (={card_position}) needs to be within the range of your hand 0 to {len(self.hand)}"
                    )
            except:
                raise TypeError(
                    f"Your inputed card position = {card_position} has to be int."
                )

        return _selected_cards

    def decide_on_card_use(self, card: Card):
        """
        method to ask the human player whether he/she wants to keep or discard the current card -
        it is assumed this was taken from the MAIN_DECK (for discard deck, we automatically assume the card is kept)
        :param card: Card, which was drawn from from the main deck or from the discard pile
        :return: str, KEEP/DISCARD
        """
        input_decision: str

        if not card.effect:
            input_decision = input(
                f"You have drawn the Card {card.value} do you want to KEEP it or DISCARD it?\n"
            )
        else:
            input_decision = input(
                f"You have drawn the Card {card.value} {card.effect} do you want to KEEP it, DISCARD it or play the effect?\n"
            )
        input_decision = input_decision.strip()
        input_decision = input_decision.upper()

        if input_decision not in MAIN_DECK_CARD_DECISIONS:
            raise ValueError(
                f"Uknown decision on what to do with the card {input_decision}. Allowed decisions when drawing from the main deck are {MAIN_DECK_CARD_DECISIONS}"
            )
        else:
            return input_decision
