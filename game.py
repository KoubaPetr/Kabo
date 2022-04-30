"""
Class Game
"""
from collections import deque
from typing import Dict, List, Type, Optional
from card import Card
from human_player import HumanPlayer
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
    characters_to_child_classes: Dict[str, type] = {"HUMAN": HumanPlayer}

    def __init__(self, player_names_and_chars: Dict[str, str]):
        """
        Constructor method
        """
        if type(player_names_and_chars) != dict:
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
        self.players: List[Type[Player]] = Game.create_players_by_character(
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
        Function to play a new round
        :return:
        """
        _players_deque: deque = deque(self.players)
        _players_deque.rotate(-1)
        _players_rotated: list = list(_players_deque)

        round: Round = Round(cards=Game.CARDS.copy(), players=_players_rotated)
        return round

    def _read_players_game_scores(self) -> Dict[Type[Player], int]:
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
            round: Round = self._play_round()
            self.rounds.append(round)
            _scores: Dict[Type[Player], int] = self._read_players_game_scores()
            _play_next_round: bool = True

            for player, score in _scores.items():
                if score == TARGET_POINT_VALUE:
                    _play_next_round = player.reached_score_100()

                elif score > TARGET_POINT_VALUE:
                    _play_next_round = False

            # TODO: save the score after round into game history ?
            self._report_standings_after_round(round=round)
            if not _play_next_round:
                break
        self._report_standings_after_game()

    def _report_standings_after_round(self, round: Round) -> None:
        """
        Utility to report standings in between rounds
        :return: None (for now, printing a statement only)
        """
        print("-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-")
        print(f"Score after round {round.id}")
        for p in self.players:
            print(
                f"{p} has {p.players_game_score}. With {p.get_players_score_in_round(_round=round)} "
                f"points obtained in latest round."
            )
        print("-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-")

    def _report_standings_after_game(self) -> None:
        """
        Utility to report standings in between rounds
        :return: None (for now, printing a statement only)
        """
        _sorted_players: List[Type[Player]] = sorted(
            self.players, key=lambda plr: plr.players_game_score, reverse=True
        )

        print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
        print(f"Results of the game")
        for p_position, p in enumerate(_sorted_players):
            print(f"{p_position + 1}. {p} with {p.players_game_score} points")
        print(f"Congratulations, {_sorted_players[0].name}!!!")
        print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")

    @staticmethod
    def create_players_by_character(
        player_names_and_chars: Dict[str, str]
    ) -> List[Type[Player]]:
        """

        :param player_names_and_chars: dict with names of players and their characters
        :return: list of intantiated players (of the respective character)
        """
        retVal: List[Type[Player]] = []

        for name, character in player_names_and_chars.items():
            if character not in Game.characters_to_child_classes.keys():  # None
                raise ValueError(f"The character = {character} is unknown")
            else:
                player: Type[Player] = Game.characters_to_child_classes[character]
                player_instance = player(name)  # instantiate
                retVal.append(player_instance)
        return retVal
