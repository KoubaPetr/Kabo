import itertools
from typing import Callable, List
from rules import POINT_VALUE_AFTER_HITTING_TARGET

class Player:
    """
    Class for representing individual players of the game
    :param name, str - name of the Player
    :param character, str - default = HUMAN. Type of the player, for now str, but can be changed to Enum or some other
                            alternative (CHECK options) - this should expect values HUMAN or COMPUTER
                            (later differentiate computer into different kinds of agents, GREEDY, RANDOM etc.)
    """

    id_incremental: Callable = itertools.count().__next__ #Probably bad - we will need to be able to reset the counter

    def __init__(self, name: str, character: str = 'HUMAN'):
        """
        Constructor method
        """
        self.name: str = name  # type checking of the input args?
        self.character: str = character  # type checking of the input args?
        self.hand: list = []
        self.matched_100: bool = False #by 100 we mean generally the Game.TARGET_POINT_VALUE
        self.players_game_score: int = 0
        self.id: int = Player.id_incremental()

        if character != 'HUMAN':
            raise ValueError("Sofar only human players are supported, other kinds of agents will be implemented later")

    def __repr__(self):
        """
        Dunder returning the text describing the instance, which can be passed to eval to generate same instance
        :return: str
        """
        return f"Player({self.name})"

    def play_turn(self):
        """
        Instance method which performs the play of the player. Can be conditioned on self.character.
        :return:
        """
        pass  # TODO: implement me
        """
        For human players this should take as an argument the type of move they want to play. For computer players,
        the move can be decided based on their character
        """

    def get_players_score_in_round(self) -> int:
        """
        Function to look through the hand of the player and count his score - Only reflects the score in the round!
        :return: int, player's score with the current hand
        """

        _sum_scores: int = sum([c.value for c in self.hand]) #TODO: modify if the player called "Kabo"
        return _sum_scores

    def reached_score_100(self) -> bool:
        """
        :param: target_value_to_drop_to, int, number specified in Game class, to which score drops after hitting
                target value (100) for the first time (usually 50)
        :return: bool,  value indicating whether the player hit 100 for second time already and the game
                        should not continue
        """

        if self.matched_100:
            _play_next_round = False
        else:
            self.matched_100 = True #TODO: after each round this needs to be reset
            self.players_game_score = POINT_VALUE_AFTER_HITTING_TARGET
            _play_next_round = True
        return _play_next_round

    def check_own_cards(self, num_cards: int, which_hand_position: List[int] = []) -> None:
        """

        :param num_cards: int, number of own cards the player should see
        :param which_hand_position: List[int], positions of the cards in the players hand
                                    (which the player wants to see)
        :return:
        """
        if not isinstance(num_cards,int):
            raise TypeError(f"num_cards should be int, but it is {type(num_cards)}")

        if num_cards < 0 or num_cards > len(self.hand):
            raise ValueError(f"The desired number of cards to see = {num_cards} is out of range for hand of size {len(self.hand)}")

        if not isinstance(which_hand_position,list):
            raise TypeError(f"which_hand_position should be list of ints, but it is {type(which_hand_position)}")

        for position in which_hand_position:
            if not isinstance(position, int):
                raise TypeError(f"which_hand_position should contain ints, but it contains {type(position)}")
            if position < 0 or position > len(self.hand):
                raise ValueError(f"The desired position = {position} is out of range for hand of size {len(self.hand)}")


        if not which_hand_position: #unspecified positions, check cards in the order from the left
            for card in self.hand[:num_cards]:
                card.visible_to_owner = True
        else:
            for position in which_hand_position:
                self.hand[position].visible_to_owner = True

    def card_checking_preference(self) -> List[int]:
        """
        Function which returns the positions of the cards that the player wants to look at at the start of the round
        :return: List[int]
        """
        return [] #TODO: for human player we can query him for his/her preference here - by default no preference