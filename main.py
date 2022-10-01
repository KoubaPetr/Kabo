"""
Main script to run everything
"""
from src.game import Game
from src.server import Server

if __name__ == "__main__":
    playing_multiplayer: bool = True
    hosting_multiplayer: bool = True

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
