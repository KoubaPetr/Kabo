from card import Card
from typing import Dict, List, Tuple
from player import Player
from round import Round


class Game:
    """
    Class representation for a single game. One game consists of several Rounds, until some player busts
    TARGET_POINT_VALUE (typically 100)

    :param player_names: List[str], list of player names who will play this game (length should be 2-4)
    """
    CARD_AMMOUNTS: Dict[int, int] = {
        0: 2,
        1: 4,
        2: 4,
        3: 4,
        4: 4,
        5: 4,
        6: 4,
        7: 4,
        8: 4,
        9: 4,
        10: 4,
        11: 4,
        12: 4,
        13: 2
    }
    CARDS: List[Card] = [Card(value) for value, ammount in CARD_AMMOUNTS.items() for i in range(ammount)]
    TARGET_POINT_VALUE: int = 100
    ALLOWED_PLAYER_COUNTS: Tuple[int, ...] = (2, 3, 4)

    def __init__(self, player_names: List[str]):
        """
        Constructor method
        """
        if type(player_names) != list:
            raise TypeError(f"The player names should be passed as a list. Not as {type(player_names)}")

        if len(player_names) not in Game.ALLOWED_PLAYER_COUNTS:
            raise ValueError(f"The list of the players should have length 2-4. The provided list has different length "
                             f"= {len(player_names)}.")

        self.players: List[Player] = [Player(name) for name in player_names]
        self.rounds: List[Round] = []  # use it to remember the rounds - those should remember the turns

    def __repr__(self):
        """
        Overloading representation of the Game class
        :return: description of the instance, which can be passed to eval
        """
        return "Game()"

    def _play_round(self) -> Round:
        """
        Function to play a new round
        :return:
        """
        round: Round = Round()  # the constructor of round should kick-start it
        return round

    def _read_players_match_scores(self) -> List[int]:
        """

        :return: List[int], with current match scores of all players
        """
        return [p.players_game_score for p in self.players]

    def play_game(self) -> None:
        """
        Call for new rounds and check the score in the meantime, to see whether the game did not finish
        :return:
        """

        while True:
            round: Round = self._play_round()
            self.rounds.append(round)
            _scores: List[int] = self._read_players_match_scores()
            _max_score: int = max(_scores)

            if _max_score > Game.TARGET_POINT_VALUE:  # TODO check for second (and other) max scores because of matching 100!!!
                break
            elif _max_score == Game.TARGET_POINT_VALUE:
                ...
                # TODO edit the players bool attr for matching target_value - end if it was already positive
            else:
                continue
            # TODO: save the score after round into game history ?
            self._report_standings_after_round(round=round)
        self._report_standings_after_game()

    def _report_standings_after_round(self, round: Round) -> None:
        """
        Utility to report standings in between rounds
        :return: None (for now, printing a statement only)
        """
        print('-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-')
        print(f'Score after round {round.id}')
        for p in self.players:
            print(
                f'{p.name}({p.id}) has {p.players_game_score}. With {p.get_players_score_in_round()} points obtained in latest round.')
        print("-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-")

    def _report_standings_after_game(self) -> None:
        """
        Utility to report standings in between rounds
        :return: None (for now, printing a statement only)
        """
        _sorted_players: List[Player] = sorted(self.players, key=lambda p: p.players_game_score, reverse=True)

        print('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$')
        print(f'Results of the game')
        for p_position, p in enumerate(_sorted_players):
            print(f'{p_position + 1}. {p.name} with {p.players_game_score} points')
        print(f'Congratulations, {_sorted_players[0].name}!!!')
        print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
