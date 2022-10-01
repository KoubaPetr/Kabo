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
        # The below code is not  executed because the server above still waits for new connections
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
