"""
Class Round
"""
from itertools import count, cycle
from typing import TYPE_CHECKING, List, Dict, Optional, Type
import collections
from src.card import Card
from src.deck import Deck

# from src.game import Game
from src.discard_pile import DiscardPile
from src.rules import (
    CARDS_PER_PLAYER,
    NUMBER_OF_CARDS_TO_SEE,
    NUMBER_OF_CARDS_FOR_KAMIKADZE,
    KAMIKADZE_VALUES,
    KAMIKADZE_PENALTY,
)

if TYPE_CHECKING:
    from src.player import Player


class Round:
    """
    Class representing single round of the game, that is part of game starting with cards being dealt and ending after
    Kabo or deck of cards being empty
    :param cards: List[Card], copy of the global game list of all the cards
    :param players: List[Player], players playing the round
    """

    _id_incremental: count = count(0)

    def __init__(
        self, cards: List[Card], players: List["Player"], game
    ):  # TODO: game not typed due to circular import
        """
        Constructor method
        """
        # Init round attributes
        self.round_id: int = next(self._id_incremental)
        self.players: List[Type[Player]] = (
            players[self.round_id :] + players[: self.round_id]
        )
        self.game = game
        self.kabo_called: bool = (
            False  # indicator whether kabo was called in this round already
        )
        self.discard_pile: DiscardPile = DiscardPile([])
        self.main_deck: Deck = Deck(cards)

        # Reset players attributes which might have been altered in previous rounds
        self._reset_players()

        # Shuffle and deal the cards
        self.main_deck.shuffle()  # shuffles the cards in place
        self._deal_cards_to_players()

        # Init the discard pile
        _first_discarded_card: Card = self.main_deck.cards.pop()
        self.discard_card(_first_discarded_card)
        if self.game.using_gui:
            self.game.GUI.update_screen()
        # Start actions of players
        self._let_players_see_cards()
        # TODO: show in the GUI when there is a multiplayer
        self._start_playing()

        # Update players score after round
        self._update_players_game_scores()
        # TODO: show scores?

    def _deal_cards_to_players(self) -> None:
        """
        This function deals the cards to players hands
        :return:
        """
        for player in self.players:
            for _ in range(CARDS_PER_PLAYER):
                _dealt_card: Card = self.main_deck.cards.pop()
                self._deal_single_card(_dealt_card, player)

    def discard_card(self, card: Card) -> None:
        """
        Method to put the given card from on top of the discard pile (and handle its visibility)

        :return:
        """
        card.status = "DISCARD_PILE"
        card.publicly_visible = (
            True  # maybe cover the previously top card and make it again not visible?
        )

        self.discard_pile.add(card)

    def _let_players_see_cards(self) -> None:
        """
        Method calling all players in the round to see certain number of their cards.
        :return:
        """
        for player in self.players:
            _which_cards = player.card_checking_preference()
            player.check_own_cards(
                num_cards=NUMBER_OF_CARDS_TO_SEE, which_position=_which_cards
            )
            player.report_known_cards_on_hand()

    def _start_playing(self):
        """
        Method calling the Players to play until the end of Round is reached.

        :return:
        """
        _players_cycle: cycle = cycle(self.players)
        _kabo_counter: int = len(self.players)
        _kabo_active: bool = False

        while self.main_deck.cards:
            if _kabo_counter == 0:
                break

            current_player: "Player" = next(_players_cycle)
            kabo_called = current_player.perform_turn(_round=self)
            if self.game.using_gui:
                self.game.GUI.update_screen()

            if kabo_called:
                self.kabo_called = True
                _kabo_active = True

            if _kabo_active:
                _kabo_counter -= 1

    def _reset_players(self) -> None:
        """
        Method to reset players attributes which might have changed in previous round
        :return:
        """

        for player in self.players:
            player.reset_player_after_round()

    def get_player_by_name(self, name: str):  # Missing typing
        """
        helper method to search for a player in the round, by his/her name
        :param name: str, name of the player to be searched for
        :return:
        """
        return [player for player in self.players if player.name == name][0]

    def _update_players_game_scores(self) -> None:
        """
        Function which invokes all players game score update
        :return:
        """
        kamikadze_player = self._check_kamikadze()
        if kamikadze_player:
            for player in self.players:
                if player != kamikadze_player:
                    player.players_game_score += KAMIKADZE_PENALTY
        else:
            for player in self.players:
                player.players_game_score += player.get_players_score_in_round(
                    _round=self
                )

    def _check_kamikadze(self) -> Optional["Player"]:
        """
        Check whether some player in this round reached Kamikadze
        :return: Optional[Player], Player who reached Kamikadze (or None if no player reached it)
        """
        for player in self.players:
            if len(player.hand) in NUMBER_OF_CARDS_FOR_KAMIKADZE:
                _card_values: List[int] = [c.value for c in player.hand]
                _card_frequencies: Dict[int, int] = collections.Counter(_card_values)
                _player_activated_kamikadze: bool = True
                for card_val, card_freq in KAMIKADZE_VALUES.items():
                    if _card_frequencies[card_val] < card_freq:
                        _player_activated_kamikadze = False
                if _player_activated_kamikadze:
                    print(f"{player}) achieved Kamikadze!!!")
                    return player
        return None

    @staticmethod
    def _deal_single_card(card: Card, player: "Player") -> None:
        """
        static method for dealing a single card from main deck to player
        :param card: Card, to be dealt
        :param player: Player, to be given the card
        :return:
        """
        player.hand.append(card)
        card.status = "HAND"
        card.owner = player
