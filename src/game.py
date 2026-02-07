"""
Class Game
"""
# from collections import deque
from typing import Dict, List, Type
from src.card import Card
from src.human_player import HumanPlayer, P
from src.computer_player import ComputerPlayer
from src.network_player import NetworkPlayer
from src.round import Round
from config.rules import ALLOWED_PLAYER_COUNTS, CARD_AMOUNTS, TARGET_POINT_VALUE
from src.gui import GUI


class Game:
    """
    Class representation for a single game. One game consists of several Rounds, until some player busts
    TARGET_POINT_VALUE (typically 100)
    :param player_names_and_chars: List[str], list of player names who will play this game (length should be 2-4)
    """

    characters_to_child_classes: Dict[str, Type[P]] = {
        "HUMAN": HumanPlayer,
        "COMPUTER": ComputerPlayer,
    }

    def __init__(self, player_names_and_chars: Dict[str, str] = None,
                 using_gui: bool = False, players: List = None):
        """
        Constructor method. Either pass player_names_and_chars dict to create players,
        or pass pre-created player instances directly.
        """
        if players:
            if len(players) not in ALLOWED_PLAYER_COUNTS:
                raise ValueError(
                    f"Need 2-4 players, got {len(players)}."
                )
            self.players = players
            self.player_name_list = [p.name for p in players]
        else:
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
            self.players: List[Type[P]] = Game.create_players_by_character(
                player_names_and_chars
            )
        self.num_players: int = len(self.players)
        self.rounds: List[Round] = []  # to remember the rounds
        self._start_player_index: int = 0  # index of starting player for next round

        self.using_gui: bool = using_gui
        self.GUI = None

    def __repr__(self):
        """
        Overloading representation of the Game class
        :return: description of the instance, which can be passed to eval
        """
        return f"Game({self.player_name_list})"

    def _init_round(self) -> Round:
        """
        Function to play a new _round
        :return:
        """
        CARDS: List[Card] = [
            Card(value) for value, amount in CARD_AMOUNTS.items() for i in range(amount)
        ]

        _round: Round = Round(cards=CARDS, players=self.players, game=self,
                              start_player_index=self._start_player_index)
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
        print("Game started")
        while True:
            _round: Round = self._init_round()

            if self.using_gui and self.GUI is None:
                import pygame
                pygame.init()
                self.GUI = GUI(self.num_players, _round.discard_pile[-1].value)

            if self.GUI:
                self.GUI.set_discard_pile(_round.discard_pile)
                self.GUI.update_screen([p.hand for p in self.players])
            self.rounds.append(_round)
            self.rounds[-1].start_playing(gui=self.GUI)

            _scores: Dict[Type[P], int] = self._read_players_game_scores()
            _play_next_round: bool = True

            for player, score in _scores.items():
                if score == TARGET_POINT_VALUE:
                    _play_next_round = _play_next_round and player.reached_score_100()

                elif score > TARGET_POINT_VALUE:
                    _play_next_round = False

            # Update start player for next round: lowest scorer goes first
            self._update_start_player()

            self._report_standings_after_round(_round=_round)
            if not _play_next_round:
                break
        self._report_standings_after_game()

    def _update_start_player(self) -> None:
        """
        Update the start player index: lowest total game scorer starts next round.
        :return:
        """
        lowest_score = min(p.players_game_score for p in self.players)
        for i, p in enumerate(self.players):
            if p.players_game_score == lowest_score:
                self._start_player_index = i
                break

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
        Utility to report final standings. Tie-break: among players with the same total score,
        the one with the lowest score in the last round wins.
        :return: None (for now, printing a statement only)
        """
        last_round = self.rounds[-1]
        _sorted_players: List[Type[P]] = sorted(
            self.players,
            key=lambda plr: (plr.players_game_score,
                             plr.get_players_score_in_round(last_round))
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
