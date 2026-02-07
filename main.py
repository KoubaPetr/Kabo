"""
Main script to run the Kabo card game.

Usage:
    python main.py                           # Hot-seat mode, 2 human players, no GUI
    python main.py --gui                     # Hot-seat mode with GUI
    python main.py --players Petr Anicka Jan # 3 human players
    python main.py --ai 1                   # 1 human + 1 AI
    python main.py --mode server --num-players 2  # Start server
    python main.py --mode client --name Petr      # Join as client
"""
import argparse
from src.game import Game


def main():
    parser = argparse.ArgumentParser(description="Kabo Card Game")
    parser.add_argument("--mode", choices=["hotseat", "server", "client"],
                        default="hotseat", help="Game mode")
    parser.add_argument("--gui", action="store_true", help="Enable GUI")
    parser.add_argument("--players", nargs="+", default=["Petr", "Anicka"],
                        help="Player names (hot-seat mode)")
    parser.add_argument("--ai", type=int, default=0,
                        help="Number of AI players to add")
    parser.add_argument("--name", type=str, default="Player",
                        help="Your name (client mode)")
    parser.add_argument("--num-players", type=int, default=2,
                        help="Number of players (server mode)")
    parser.add_argument("--address", type=str, default="127.0.0.1",
                        help="Server address")
    parser.add_argument("--port", type=int, default=5555,
                        help="Server port")

    args = parser.parse_args()

    if args.mode == "hotseat":
        player_config = {name: "HUMAN" for name in args.players}
        for i in range(args.ai):
            player_config[f"AI_{i + 1}"] = "COMPUTER"
        game = Game(player_config, using_gui=args.gui)
        game.play_game()

    elif args.mode == "server":
        from src.server import Server
        Server(number_of_clients=args.num_players, address=args.address,
               port_num=args.port)

    elif args.mode == "client":
        from src.client import Client
        client = Client(player_name=args.name, address=args.address,
                        port_num=args.port)
        client.run()


if __name__ == "__main__":
    main()
