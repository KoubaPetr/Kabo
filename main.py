"""
Main script to run everything
"""
from src.game import Game

if __name__ == "__main__":
    g = Game({"Petr": "HUMAN", "Anicka": "HUMAN"})
    g.play_game()
