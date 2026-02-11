"""
Class Game
"""
# from collections import deque
import threading
from typing import Dict, List, Type
from src.card import Card
from src.human_player import HumanPlayer, P
from src.computer_player import ComputerPlayer
from src.network_player import NetworkPlayer
from src.round import Round
from config.rules import ALLOWED_PLAYER_COUNTS, CARD_AMOUNTS, TARGET_POINT_VALUE


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

    try:
        from src.web.web_player import WebPlayer
        characters_to_child_classes["WEB"] = WebPlayer
    except ImportError:
        pass

    def __init__(self, player_names_and_chars: Dict[str, str] = None,
                 players: List = None):
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

            self.rounds.append(_round)
            self.rounds[-1].start_playing()

            # Show round-end summary to web players (if any)
            self._show_round_end_to_players(_round)

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

    def _show_round_end_to_players(self, _round: Round) -> None:
        """Show round-end summary to WebPlayers and wait for confirmation."""
        from src.web.web_player import WebPlayer
        web_players = [p for p in self.players if isinstance(p, WebPlayer)]
        if not web_players:
            return

        # Build round summary
        from src.web.game_state import RoundSummary, PlayerView, CardView
        player_hands = []
        for p in _round.players:
            cards = []
            for i, card in enumerate(p.hand):
                if card is None:
                    continue
                cards.append(CardView(
                    position=i, value=card.value,
                    is_known=True, is_publicly_visible=True,
                ))
            player_hands.append(PlayerView(
                name=p.name, character=p.character,
                is_current_player=False,
                cards=cards, game_score=p.players_game_score,
                called_kabo=p.called_kabo,
            ))

        kabo_caller = ""
        kabo_successful = False
        for p in _round.players:
            if p.called_kabo:
                kabo_caller = p.name
                round_score = _round.round_scores.get(p.name, 0)
                kabo_successful = (round_score == 0)
                break

        summary = RoundSummary(
            round_number=_round.round_id,
            player_hands=player_hands,
            round_scores=_round.round_scores,
            game_scores={p.name: p.players_game_score for p in _round.players},
            kabo_caller=kabo_caller,
            kabo_successful=kabo_successful,
        )

        # Ask each WebPlayer to confirm in parallel threads
        threads = []
        for wp in web_players:
            t = threading.Thread(
                target=wp.wait_for_round_end_confirmation,
                args=(summary, _round),
                daemon=True,
            )
            threads.append(t)
            t.start()

        # Wait for all with timeout
        for t in threads:
            t.join(timeout=35)

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
