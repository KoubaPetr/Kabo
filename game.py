"""
Class Game
"""
from collections import deque
from typing import Dict, List
from card import Card
from player import Player
from round import Round
from rules import ALLOWED_PLAYER_COUNTS, CARD_AMOUNTS, TARGET_POINT_VALUE


class Game:
    """
    Class representation for a single game. One game consists of several Rounds, until some player busts
    TARGET_POINT_VALUE (typically 100)
    :param player_names: List[str], list of player names who will play this game (length should be 2-4)
    """

    CARDS: List[Card] = [
        Card(value) for value, amount in CARD_AMOUNTS.items() for i in range(amount)
    ]

    def __init__(self, player_names: List[str]):
        """
        Constructor method
        """
        if type(player_names) != list:
            raise TypeError(
                f"The player names should be passed as a list. Not as {type(player_names)}"
            )

        if len(player_names) not in ALLOWED_PLAYER_COUNTS:
            raise ValueError(
                f"The list of the players should have length 2-4. The provided list has different length "
                f"= {len(player_names)}."
            )

        self.player_name_list: List[str] = player_names

        _player_deque: deque = deque(player_names)
        _player_deque.rotate(
            1
        )  # rotate player names to leave room for later rotation into original order
        # TODO: consider reseting players id counter before creating them ?
        self.players: List[Player] = [Player(name) for name in _player_deque]
        self.rounds: List[
            Round
        ] = []  # use it to remember the rounds - those should remember the turns

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

    def _read_players_game_scores(self) -> Dict[Player, int]:
        """

        :return: Dict[Player,int], with current match scores of all players
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
            _scores: Dict[Player, int] = self._read_players_game_scores()
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
                f"{p.name}({p.id}) has {p.players_game_score}. With {p.get_players_score_in_round(round=round)} "
                f"points obtained in latest round."
            )
        print("-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-")

    def _report_standings_after_game(self) -> None:
        """
        Utility to report standings in between rounds
        :return: None (for now, printing a statement only)
        """
        _sorted_players: List[Player] = sorted(
            self.players, key=lambda plr: plr.players_game_score, reverse=True
        )

        print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
        print(f"Results of the game")
        for p_position, p in enumerate(_sorted_players):
            print(f"{p_position + 1}. {p.name} with {p.players_game_score} points")
        print(f"Congratulations, {_sorted_players[0].name}!!!")
        print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
