"""
Main script to run everything
"""
from src.game import Game
from src.server import Server
from src.client import Client
import sys

if __name__ == "__main__":
    playing_multiplayer: bool = True
    hosting_multiplayer: bool = True
    connecting_multiplayer: bool = False

    if not playing_multiplayer:
        game = Game(
            {"Petr": "HUMAN", "Anicka": "HUMAN"},
            using_gui=True,
        )
        # TODO: throw GUI prompt for players names - shared for multiplayer ..?
        game.play_game()

    elif hosting_multiplayer:
        number_of_players: int = 2
        server: Server = Server(number_of_clients=number_of_players)

        wait_for_players: bool = True
        while wait_for_players:  # TODO: maybe check more robustly
            if len(server.client_names) == number_of_players:
                game = Game({p: "HUMAN" for p in server.client_names}, using_gui=True)
                wait_for_players = False
            elif len(server.client_names) >= number_of_players:
                raise ValueError(
                    f"Too many players! More than announced {number_of_players}."
                )

        server.set_game(game=game)
        # TODO: create GUIs for players (perhaps instead of for game, although that can be useful for an observer)

    elif connecting_multiplayer:
        ...  # TODO: later move other client initializations here
