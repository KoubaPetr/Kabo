"""
Class HumanPlayer is a subclass of Player class, which specifies Players playing behaviour in such a way,
which allowes interactive input by a user
"""
from src.player import Player
from src.round import Round
from config.rules import ALLOWED_PLAYS, MAIN_DECK_CARD_DECISIONS
from typing import List, Optional, Type, Tuple, TypeVar
from src.card import Card

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

    def pick_turn_type(self, _round: Round = None) -> str:
        """
        Method which asks the player to input the type of play he/she wants to play
        :return: str , play type chosen by the human player
        """
        while True:
            input_turn: str = input(
                f"{self.name}: Choose your type of play KABO/HIT_DECK/HIT_DISCARD_PILE\n"
            )
            input_turn = input_turn.strip().upper()
            if input_turn in ALLOWED_PLAYS:
                return input_turn
            print(f"Invalid play type '{input_turn}'. Allowed plays are {ALLOWED_PLAYS}.")

    def pick_hand_cards_for_exchange(self, drawn_card: Card) -> List[Card]:
        """
        Method which asks the player to input the positions of the cards in his/her hand which he/she wants to exchange
        :param drawn_card: Card, the card drawn for which we want to exchange our card(s)
        :return: List[Card] , cards chosen for exchange
        """
        while True:
            chosen_cards: str = input(
                f"{self.name}: You have drawn {drawn_card.value}. Pick the cards you wish to exchange (numbered from left in your hand = {[str(card) for card in self.hand]}\n"
            )
            chosen_cards = chosen_cards.strip()
            chosen_cards_list: List[str] = chosen_cards.split()
            _selected_cards: List[Card] = []
            valid = True

            for card_position in chosen_cards_list:
                try:
                    card_position_int: int = int(card_position)
                    if card_position_int in range(len(self.hand)):
                        _selected_cards.append(self.hand[card_position_int])
                    else:
                        print(f"Position {card_position} is out of range (0 to {len(self.hand) - 1}).")
                        valid = False
                        break
                except (ValueError, TypeError):
                    print(f"Invalid input '{card_position}' - must be an integer.")
                    valid = False
                    break

            if valid and _selected_cards:
                return _selected_cards
            if valid and not _selected_cards:
                print("No cards selected. Please select at least one card.")

    def decide_on_card_use(self, card: Card):
        """
        method to ask the human player whether he/she wants to keep or discard the current card -
        it is assumed this was taken from the MAIN_DECK (for discard deck, we automatically assume the card is kept)
        :param card: Card, which was drawn from from the main deck or from the discard pile
        :return: str, KEEP/DISCARD
        """
        while True:
            if not card.effect:
                input_decision = input(
                    f"{self.name}: You have drawn the Card {card.value} do you want to KEEP it or DISCARD it?\n"
                )
            else:
                input_decision = input(
                    f"{self.name}: You have drawn the Card {card.value} {card.effect} do you want to KEEP it, DISCARD it or play the EFFECT?\n"
                )
            input_decision = input_decision.strip().upper()
            if input_decision in MAIN_DECK_CARD_DECISIONS:
                return input_decision
            print(f"Unknown decision '{input_decision}'. Allowed: {MAIN_DECK_CARD_DECISIONS}")

    def pick_position_for_new_card(
        self, available_positions: List[int]
    ) -> Optional[int]:
        """
        method to select where to put the new card out of the free slots freed by the discarded cards
        :param available_positions: List[int] list of available positions in players hand
        :return:
        """
        if len(available_positions) == 0:
            print("No position for placing the card was made available. The card wont be kept.")
            return None

        if len(available_positions) == 1:
            picked_position = available_positions[0]
        else:
            while True:
                picked_input: str = input(
                    f"{self.name}: Pick position in your hand, where to place the new card. Available positions: {available_positions}\n"
                )
                try:
                    picked_position = int(picked_input.strip())
                    if picked_position in available_positions:
                        break
                    print(f"Position {picked_position} is not available. Choose from {available_positions}.")
                except (ValueError, TypeError):
                    print(f"Position must be an integer. You entered '{picked_input}'.")

        print(f"{self.name}: Your new card is being placed at position {picked_position}")
        return int(picked_position)

    def pick_cards_to_see(self, num_cards_to_see: int) -> List[int]:
        """
        Ask the human player to specify positions of the card/cards (based on num_cards_to_see) which he/she wants to see
        :param num_cards_to_see: int
        :return:
        """
        while True:
            if num_cards_to_see > 1:
                picked_positions = input(
                    f"{self.name}: Pick {num_cards_to_see} cards in your hand {[str(c) for c in self.hand]}, which you want to see. Specify them by card index separated by space.\n"
                )
            elif num_cards_to_see == 1:
                picked_positions = input(
                    f"{self.name}: Pick card in your hand {[str(c) for c in self.hand]}, which you want to see. Specify it by card index.\n"
                )
            else:
                raise ValueError(f"Invalid number of cards to see {num_cards_to_see}.")

            picked_positions_list = picked_positions.strip().split()
            try:
                picked_indices = [int(p) for p in picked_positions_list]
            except (ValueError, TypeError):
                print(f"Positions must be integers. You entered '{picked_positions}'.")
                continue

            if len(picked_indices) != num_cards_to_see:
                print(f"You must select exactly {num_cards_to_see} card(s).")
                continue

            if all(0 <= idx < len(self.hand) for idx in picked_indices):
                return picked_indices
            print(f"Some positions are out of range (0 to {len(self.hand) - 1}).")

    def specify_spying(self, _round: Round) -> Tuple[Type[P], Card]:
        """
        Ask the human player which player he/she wants to spy on and which card he/she wants to spy
        :param _round: Round, current round
        :return: Tuple[Type[Player],Card]
        """
        available_players: List[str] = [p.name for p in _round.players if p != self]

        while True:
            input_name: str = input(
                f"{self.name}, please specify the opponent you wish to spy on, valid names are: {available_players}\n"
            )
            input_name = input_name.strip().upper()
            if input_name in available_players:
                break
            print(f"Unknown opponent '{input_name}'. Valid names: {available_players}")

        opponent_to_be_spied: Type[P] = _round.get_player_by_name(input_name)

        while True:
            input_position: str = input(
                f"{self.name}, please specify the card of {opponent_to_be_spied.name} you wish to spy, "
                f"{opponent_to_be_spied}'s hand is: {[str(c) for c in opponent_to_be_spied.hand]}\n"
            )
            try:
                input_position_idx: int = int(input_position.strip())
                if input_position_idx in range(len(opponent_to_be_spied.hand)):
                    break
                print(f"Position out of range (0 to {len(opponent_to_be_spied.hand) - 1}).")
            except (ValueError, TypeError):
                print(f"Position must be an integer. You entered '{input_position}'.")

        spied_card: Card = opponent_to_be_spied.hand[input_position_idx]
        return opponent_to_be_spied, spied_card

    def specify_swap(self, _round: Round) -> Tuple[Type[P], int, int]:
        """
        Ask the human player which player he/she wants to swap with and which cards he/she wants to swap (specified by idx)
        :param _round: Round, current round
        :return: Tuple[Type[Player],int,int] opponent, own_card_idx, opponents_card_idx
        """
        # Get own card for swap
        while True:
            own_card_input: str = input(
                f"{self.name}, please specify the position of your card you wish to swap, "
                f"Your hand is: {[str(c) for c in self.hand]}\n"
            )
            try:
                own_card_idx: int = int(own_card_input.strip())
                if own_card_idx in range(len(self.hand)):
                    break
                print(f"Position out of range (0 to {len(self.hand) - 1}).")
            except (ValueError, TypeError):
                print(f"Position must be an integer. You entered '{own_card_input}'.")

        # Get opponent for swap
        available_players: List[str] = [p.name for p in _round.players if p != self]
        while True:
            input_name: str = input(
                f"{self.name}, please specify the opponent you wish to swap with, valid names are: {available_players}\n"
            )
            input_name = input_name.strip().upper()
            if input_name in available_players:
                break
            print(f"Unknown opponent '{input_name}'. Valid names: {available_players}")

        opponent_for_swap: Type[P] = _round.get_player_by_name(input_name)

        # Get opponent's card for swap
        while True:
            input_position: str = input(
                f"{self.name}, please specify the card of {opponent_for_swap.name} you wish to swap, "
                f"{opponent_for_swap.name}'s hand is: {[str(c) for c in opponent_for_swap.hand]}\n"
            )
            try:
                opponents_card_idx: int = int(input_position.strip())
                if opponents_card_idx in range(len(opponent_for_swap.hand)):
                    break
                print(f"Position out of range (0 to {len(opponent_for_swap.hand) - 1}).")
            except (ValueError, TypeError):
                print(f"Position must be an integer. You entered '{input_position}'.")

        return opponent_for_swap, own_card_idx, opponents_card_idx

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
