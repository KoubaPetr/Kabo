"""
Class HumanPlayer is a subclass of Player class, which specifies Players playing behaviour in such a way,
which allowes interactive input by a user
"""
from player import Player
from round import Round
from rules import ALLOWED_PLAYS, MAIN_DECK_CARD_DECISIONS
from typing import List, Optional, Type, Tuple, TypeVar
from card import Card

P = TypeVar("P", bound=Player)


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
        return self.player_id

    def pick_turn_type(self) -> str:
        """
        Method which asks the player to input the type of play he/she wants to play
        :return: str , play type chosen by the human player
        """
        input_turn: str = input(
            f"{self.name}: Choose your type of play KABO/HIT_DECK/HIT_DISCARD_PILE\n"
        )
        input_turn = input_turn.strip()
        input_turn = input_turn.upper()

        if input_turn not in ALLOWED_PLAYS:
            raise ValueError(
                f"Input play type = {input_turn} unknown. Only plays {ALLOWED_PLAYS} are allowed."
            )
        return input_turn

    def pick_hand_cards_for_exchange(self, drawn_card: Card) -> List[Card]:
        """
        Method which asks the player to input the positions of the cards in his/her hand which he/she wants to exchange
        :param drawn_card: Card, the card drawn for which we want to exchange our card(s)
        :return: List[Card] , cards chosen for exchange
        """
        chosen_cards: str = input(
            f"{self.name}: You have drawn {drawn_card.value}. Pick the cards you wish to exchange (numbered from left in your hand = {[str(card) for card in self.hand]}\n"
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
        if not _selected_cards:  # no cards selected
            raise ValueError(
                "No cards were selected for exchange, but you already decided to keep the newly drawn card."
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
                f"{self.name}: You have drawn the Card {card.value} do you want to KEEP it or DISCARD it?\n"
            )
        else:
            input_decision = input(
                f"{self.name}: You have drawn the Card {card.value} {card.effect} do you want to KEEP it, DISCARD it or play the effect?\n"
            )
        input_decision = input_decision.strip()
        input_decision = input_decision.upper()

        if input_decision not in MAIN_DECK_CARD_DECISIONS:
            raise ValueError(
                f"Uknown decision on what to do with the card {input_decision}. Allowed decisions when drawing from the main deck are {MAIN_DECK_CARD_DECISIONS}"
            )
        else:
            return input_decision

    def pick_position_for_new_card(
        self, available_positions=List[int]
    ) -> Optional[int]:
        """
        method to select where to put the new card out of the free slots freed by the discarded cards
        :param available_positions: List[int] list of available positions in players hand
        :return:
        """
        if len(available_positions) > 1:
            picked_position: str = input(
                f"{self.name}: Pick position in your hand, where to place the new card. Available positions: {available_positions}\n"
            )
        elif len(available_positions) == 1:
            picked_position = available_positions[0]
        elif len(available_positions) == 0:
            print(
                f"No position for placing the card was made available. The card wont be kept."
            )
            return None
        print(
            f"{self.name}: Your new card is being placed at position {picked_position}"
        )
        return int(picked_position)  # not checking input whether it can be int

    def pick_cards_to_see(self, num_cards_to_see: int) -> List[int]:
        """
        Ask the human player to specify positions of the card/cards (based on num_cards_to_see) which he/she wants to see
        :param num_cards_to_see: int
        :return:
        """
        picked_positions: str
        if num_cards_to_see > 1:
            picked_positions = input(
                f"{self.name}: Pick cards in your hand {[str(c) for c in self.hand]}, which you want to see. Specify them by card index separated by space.\n"
            )
        elif num_cards_to_see == 1:
            picked_positions = input(
                f"{self.name}: Pick card in your hand {[str(c) for c in self.hand]}, which you want to see. Specify it by card index.\n"
            )
        else:
            raise ValueError(f"Invalid number of cards to see {num_cards_to_see}.")

        picked_positions_list = picked_positions.strip().split()
        picked_indices: List[int]
        try:
            picked_indices = [int(p) for p in picked_positions_list]
        except:
            raise ValueError(
                f"Specified positions of cards to see should be convertable to int. You entered {picked_positions}"
            )
        if len(picked_positions_list) != num_cards_to_see:
            raise ValueError(
                f"You didnt select enough cards to look at. You should look at {num_cards_to_see}"
            )
        return picked_indices

    def specify_spying(self, _round: Round) -> Tuple[Type[P], Card]:
        """
        Ask the human player which player he/she wants to spy on and which card he/she wants to spy
        :param _round: Round, current round
        :return: Tuple[Type[Player],Card]
        """
        available_players: List[str] = [p.name for p in _round.players if p != self]
        input_name: str = input(
            f"{self.name}, please specify the opponent you wish to spy on, valid names are: {available_players}\n"
        )
        input_name = input_name.strip().upper()
        if input_name not in available_players:
            raise ValueError(f"Unknown opponent {input_name}")

        opponent_to_be_spied: Type[P] = _round.get_player_by_name(input_name)
        input_position: str = input(
            f"{self.name}, please specify the card of {opponent_to_be_spied.name} you wish to spy, "
            f"{opponent_to_be_spied}'s hand is: {[str(c) for c in opponent_to_be_spied.hand]}\n"
        )
        input_position = input_position.strip()
        try:
            input_position_idx: int = int(input_position)
            if input_position_idx not in range(len(opponent_to_be_spied.hand)):
                raise ValueError(
                    f"Specified card is out of range for {opponent_to_be_spied.name}'s hand"
                )
        except:
            raise TypeError(
                f"The input card position should be convertable to int. You have entered {input_position}"
            )
        spied_card: Card = opponent_to_be_spied.hand[input_position_idx]
        return opponent_to_be_spied, spied_card

    def specify_swap(self, _round: Round) -> Tuple[Type[P], int, int]:
        """
        Ask the human player which player he/she wants to swap with and which cards he/she wants to swap (specified by idx)
        :param _round: Round, current round
        :return: Tuple[Type[Player],int,int] opponent, own_card_idx, opponents_card_idx
        """
        # Get own card for swap
        own_card_input: str = input(
            f"{self.name}, please specify the position of your card you wish to swap, "
            f"Your hand is: {[str(c) for c in self.hand]}\n"  # why is print printing None when str gives X ? and why are the cards not visible?
        )
        own_card_input = own_card_input.strip()
        try:
            own_card_idx: int = int(own_card_input)
            if own_card_idx not in range(len(self.hand)):
                raise ValueError(f"Specified card is out of range for your hand")
        except:
            raise TypeError(
                f"The input card position should be convertable to int. You have entered {own_card_input}"
            )  # TODO: code repetition to be fixed

        # Get opponent for swap
        available_players: List[str] = [p.name for p in _round.players if p != self]
        input_name: str = input(
            f"{self.name}, please specify the opponent you wish to swap with, valid names are: {available_players}\n"
        )
        input_name = input_name.strip().upper()
        if input_name not in available_players:
            raise ValueError(f"Unknown opponent {input_name}")

        opponent_for_swap: Type[P] = _round.get_player_by_name(input_name)
        input_position: str = input(
            f"{self.name}, please specify the card of {opponent_for_swap.name} you wish to swap, "
            f"{opponent_for_swap.name}'s hand is: {[str(c) for c in opponent_for_swap.hand]}\n"
        )

        # Get opponents card for swap
        input_position = input_position.strip()
        try:
            spied_card_idx: int = int(input_position)
            if spied_card_idx not in range(len(opponent_for_swap.hand)):
                raise ValueError(
                    f"Specified card is out of range for {opponent_for_swap.name}'s hand"
                )
        except:
            raise TypeError(
                f"The input card position should be convertable to int. You have entered {input_position}"
            )
        return opponent_for_swap, own_card_idx, spied_card_idx

    def report_known_cards_on_hand(self) -> None:
        """
        Helper method to print the cards based on the knowledge to the owner on public visibility
        :return:
        """
        print(
            f"{self.name}, your cards are:{[c.value if c.known_to_owner or c.publicly_visible else 'X' for c in self.hand]}"
        )

    def tell_player_card_value(self, card: Card, effect: str) -> None:
        """

        :param card: Card, the card which value we want to tell the player
        :param effect: str, the effect from which this was invokec
        :return:
        """
        if effect == "PEAK":
            print(f"The value of your card you have peaked on is: {card.value}")
        else:
            print(f"The value of the card you have spied on is: {card.value}")
