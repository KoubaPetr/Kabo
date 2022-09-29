"""
Main script to run everything
"""
from src.game import Game

if __name__ == "__main__":
    g = Game(
        {"Petr": "HUMAN", "Anicka": "HUMAN"},
        using_gui=True,
    )
    # TODO: throw GUI prompt for players names - shared for multiplayer ..?
    g.play_game()
