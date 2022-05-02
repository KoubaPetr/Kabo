"""
Class Game
"""
from collections import deque
from typing import Dict, List, Type
from card import Card
from human_player import HumanPlayer, P
from player import Player
from round import Round
from rules import ALLOWED_PLAYER_COUNTS, CARD_AMOUNTS, TARGET_POINT_VALUE


class Game:
    """
    Class representation for a single game. One game consists of several Rounds, until some player busts
    TARGET_POINT_VALUE (typically 100)
    :param player_names_and_chars: List[str], list of player names who will play this game (length should be 2-4)
    """

    CARDS: List[Card] = [
        Card(value) for value, amount in CARD_AMOUNTS.items() for i in range(amount)
    ]
    characters_to_child_classes: Dict[str, Type[P]] = {"HUMAN": HumanPlayer}

    def __init__(self, player_names_and_chars: Dict[str, str]):
        """
        Constructor method
        """
        if not isinstance(player_names_and_chars, dict):
            raise TypeError(
                f"The player names and their characters should be passed as a dict. Not as {type(player_names_and_chars)}"
            )

        if len(player_names_and_chars) not in ALLOWED_PLAYER_COUNTS:
            raise ValueError(
                f"The list of the players should have length 2-4. The provided list has different length "
                f"= {len(player_names_and_chars)}."
            )

        self.player_name_list: List[str] = list(player_names_and_chars.keys())
        # TODO: test for name duplicities -then player __repr__ can be done using name only
        _player_deque: deque = deque(self.player_name_list)
        _player_deque.rotate(1)  # rotate player names
        # TODO: consider reseting players id counter before creating them ?
        self.players: List[Type[P]] = Game.create_players_by_character(
            player_names_and_chars
        )
        self.rounds: List[Round] = []  # to remember the rounds

    def __repr__(self):
        """
        Overloading representation of the Game class
        :return: description of the instance, which can be passed to eval
        """
        return f"Game({self.player_name_list})"

    def _play_round(self) -> Round:
        """
        Function to play a new _round
        :return:
        """
        _players_deque: deque = deque(self.players)
        _players_deque.rotate(-1)
        _players_rotated: list = list(_players_deque)

        _round: Round = Round(cards=Game.CARDS.copy(), players=_players_rotated)
        return _round

    def _read_players_game_scores(self) -> Dict[Type[P], int]:
        """

        :return: Dict[Type[Player],int], with current match scores of all players
        """
        return {p: p.players_game_score for p in self.players}

    def play_game(self) -> None:
        """
        Call for new rounds and check the score in the meantime, to see whether the game did not finish
        :return:
        """

        while True:
            _round: Round = self._play_round()
            self.rounds.append(_round)
            _scores: Dict[Type[P], int] = self._read_players_game_scores()
            _play_next_round: bool = True

            for player, score in _scores.items():
                if score == TARGET_POINT_VALUE:
                    _play_next_round = player.reached_score_100()

                elif score > TARGET_POINT_VALUE:
                    _play_next_round = False

            # TODO: save the score after round into game history ?
            self._report_standings_after_round(_round=_round)
            if not _play_next_round:
                break
        self._report_standings_after_game()

    def _report_standings_after_round(self, _round: Round) -> None:
        """
        Utility to report standings in between rounds
        :return: None (for now, printing a statement only)
        """
        print("-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-")
        print(f"Score after round {_round.round_id}")
        for player in self.players:
            print(
                f"{player} has {player.players_game_score}. With {player.get_players_score_in_round(_round=_round)} "
                f"points obtained in latest round."
            )
        print("-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-")

    def _report_standings_after_game(self) -> None:
        """
        Utility to report standings in between rounds
        :return: None (for now, printing a statement only)
        """
        _sorted_players: List[Type[P]] = sorted(
            self.players, key=lambda plr: plr.players_game_score, reverse=True
        )

        print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
        print("Results of the game")
        for player_position, player in enumerate(_sorted_players):
            print(
                f"{player_position + 1}. {player} with {player.players_game_score} points"
            )
        print(f"Congratulations, {_sorted_players[0].name}!!!")
        print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")

    @staticmethod
    def create_players_by_character(
        player_names_and_chars: Dict[str, str]
    ) -> List[Type[P]]:
        """

        :param player_names_and_chars: dict with names of players and their characters
        :return: list of intantiated players (of the respective character)
        """
        ret_val: List[Type[P]] = []

        for name, character in player_names_and_chars.items():
            if character not in Game.characters_to_child_classes.keys():  # None
                raise ValueError(f"The character = {character} is unknown")

            player: Type[P] = Game.characters_to_child_classes[character]
            player_instance = player(name)  # instantiate
            ret_val.append(player_instance)
        return ret_val
