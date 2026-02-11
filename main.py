"""
Main script to run the Kabo card game.

Usage:
    python main.py                           # Hot-seat mode, 2 human players
    python main.py --players Petr Anicka Jan # 3 human players
    python main.py --ai 1                   # 2 human + 1 AI (3 total)
    python main.py --players Petr --ai 1    # 1 human + 1 AI (2 total)
    python main.py --mode server --num-players 2  # Start server
    python main.py --mode client --name Petr      # Join as client
    python main.py --mode web                    # Browser GUI at http://localhost:8080
    python main.py --mode web --web-port 9090    # Browser GUI on custom port
"""
import argparse
from src.game import Game


def main():
    parser = argparse.ArgumentParser(description="Kabo Card Game")
    parser.add_argument("--mode", choices=["hotseat", "server", "client", "web"],
                        default="hotseat", help="Game mode")
    parser.add_argument("--players", nargs="+", default=["Petr", "Anicka"],
                        help="Names of HUMAN players (e.g. --players Alice Bob)")
    parser.add_argument("--ai", type=int, default=0,
                        help="Number of AI players to ADD (on top of human players)")
    parser.add_argument("--name", type=str, default="Player",
                        help="Your name (client mode)")
    parser.add_argument("--num-players", type=int, default=2,
                        help="Number of players (server mode)")
    parser.add_argument("--address", type=str, default="127.0.0.1",
                        help="Server address")
    parser.add_argument("--port", type=int, default=5555,
                        help="Server port")
    parser.add_argument("--web-port", type=int, default=8080,
                        help="Port for web mode (default: 8080)")

    args = parser.parse_args()

    if args.mode == "hotseat":
        player_config = {name: "HUMAN" for name in args.players}
        for i in range(args.ai):
            player_config[f"AI_{i + 1}"] = "COMPUTER"

        total = len(player_config)
        human_count = len(args.players)
        ai_count = args.ai
        print("=" * 50)
        print("KABO - Game Setup")
        print("=" * 50)
        print(f"  Human players ({human_count}): {', '.join(args.players)}")
        if ai_count:
            ai_names = [f"AI_{i + 1}" for i in range(ai_count)]
            print(f"  AI players    ({ai_count}): {', '.join(ai_names)}")
        print(f"  Total players: {total}")
        print("=" * 50)

        game = Game(player_config)
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

    elif args.mode == "web":
        from src.web.app import start_web_gui
        start_web_gui(port=args.web_port)


if __name__ == "__main__":
    main()
