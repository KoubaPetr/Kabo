# Kabo

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

A browser-based multiplayer implementation of the card game **Cabo** (Kabo) built with Python and [NiceGUI](https://nicegui.io/).

**[Play online](https://kabo-production.up.railway.app)**

---

## About the Game

Kabo is a competitive card game for 2-4 players where the goal is to minimize the total value of your hand. The twist: most of your cards are face-down, so you must rely on memory and card effects to track what you hold.

### Rules at a Glance

- **Deck**: 52 cards with values 0-13
- **Setup**: Each player is dealt 4 face-down cards and peeks at 2 of them
- **Objective**: Have the lowest hand value when the round ends
- **Losing condition**: First player to exceed 100 cumulative points across rounds loses (hitting exactly 100 drops you to 50 once)

### On Your Turn

| Action | Description |
|--------|-------------|
| **Draw from deck** | Draw a card, then choose to **Keep** it (exchange with hand cards), **Discard** it, or use its **Effect** |
| **Take from discard** | Take the face-up top card from the discard pile (it stays publicly visible in your hand) |
| **Call KABO** | Declare you have the lowest hand - everyone else gets one more turn, then the round ends |

### Card Effects (triggered only when discarding a drawn card)

| Cards | Effect | Description |
|-------|--------|-------------|
| 7-8 | **Peek** (KUK) | Look at one of your own face-down cards |
| 9-10 | **Spy** (SPION) | Look at one of an opponent's cards |
| 11-12 | **Swap** (KSEFT) | Blindly swap one of your cards with an opponent's |

### Special Mechanics

- **Multi-card exchange**: When keeping a drawn card, you can discard multiple cards of the **same value** at once. If the values don't match, penalty: cards are revealed and you draw an extra card face-down.
- **Kamikadze**: End the round holding exactly 2x12 + 2x13 for an instant win (50 point penalty to all others).
- **KABO scoring**: Successful (caller has lowest) = 0 points. Failed = hand sum + 10 penalty.

---

## Play Modes

### Web (primary)

Browser-based GUI with real-time multiplayer support.

- **Solo**: Play against 1-3 AI opponents
- **Multiplayer**: Create a room, share the 5-character code, and play with friends (optionally add AI players)
- Automatic reconnection on page refresh

### Terminal (hotseat)

Local hot-seat mode for playing on a shared terminal.

### LAN (server/client)

TCP socket-based multiplayer over a local network.

---

## Getting Started

### Quick Start (web mode)

```bash
pip install nicegui>=1.4
python main.py --mode web
# Open http://localhost:8080
```

### All Launch Options

```bash
# Web GUI (default port 8080)
python main.py --mode web
python main.py --mode web --web-port 9090

# Terminal hotseat
python main.py --mode hotseat
python main.py --mode hotseat --players Alice Bob --ai 1

# LAN multiplayer
python main.py --mode server --num-players 2
python main.py --mode client --name Alice
```

### Using Docker

```bash
docker build -t kabo .
docker run -p 8080:8080 kabo
```

### Using Conda

```bash
conda env create -f kabo.yml
conda activate Kabo
pip install nicegui>=1.4
python main.py --mode web
```

---

## Architecture

### Project Structure

```
Kabo/
├── main.py                         # CLI entry point (mode selection)
├── config/
│   └── rules.py                    # Game constants and card definitions
├── src/
│   ├── card.py                     # Card: value, effect, visibility tracking
│   ├── deck.py                     # Deck wrapper with shuffle
│   ├── discard_pile.py             # Discard pile (add/hit)
│   ├── game.py                     # Game loop: rounds, scoring, winner detection
│   ├── round.py                    # Round: deal, turn cycle, KABO countdown
│   ├── player.py                   # Abstract Player base (turn logic, effects)
│   ├── human_player.py             # Terminal input player
│   ├── computer_player.py          # Greedy AI player
│   ├── network_player.py           # TCP socket player (LAN mode)
│   ├── server.py                   # LAN game server
│   ├── client.py                   # LAN game client
│   └── web/
│       ├── app.py                  # NiceGUI entry point, UI state management
│       ├── event_bus.py            # Thread-safe pub/sub
│       ├── game_state.py           # Dataclasses for UI state snapshots
│       ├── game_session.py         # Game thread lifecycle, stdout capture
│       ├── game_room.py            # Multiplayer room management
│       ├── web_player.py           # Bridges sync game thread with async UI
│       └── components/
│           ├── setup_page.py       # Solo game config form
│           ├── lobby_page.py       # Landing page: solo/create/join
│           ├── room_waiting_page.py# Multiplayer waiting room
│           ├── game_table.py       # Main game board layout
│           ├── action_panel.py     # Dynamic controls per game phase
│           ├── card_component.py   # Card rendering (HTML/CSS/Tailwind)
│           ├── game_log.py         # Scrollable event log
│           └── scoreboard.py       # Player scores display
├── Dockerfile                      # Container deployment
├── requirements-web.txt            # nicegui>=1.4
├── kabo.yml                        # Conda environment
└── CLAUDE_NOTES.md                 # Detailed architecture notes
```

### Two-Thread Model

The web mode uses a two-thread architecture to bridge the synchronous game engine with NiceGUI's async UI:

```
Game Thread (daemon)                UI Thread (NiceGUI)
────────────────────                ────────────────────
Game.play_game()
  └─ WebPlayer.pick_turn_type()
       ├─ build GameStateSnapshot
       ├─ EventBus.emit("state_update")  ──>  _ui_queue
       ├─ EventBus.emit("input_request") ──>  _ui_queue
       │                                       ui.timer(0.1) drains queue
       │                                       └─> update GameTable, ActionPanel
       └─ _response_queue.get() [BLOCKS]
                                          user click
                                          └─> submit_response()
          <── queue.put(response) ────────     └─> _response_queue.put()
     process response, continue game...
```

### Player Hierarchy

```
Player (abstract base - src/player.py)
├── HumanPlayer     (terminal input via stdin)
├── ComputerPlayer  (greedy AI with heuristic strategy)
├── NetworkPlayer   (TCP socket for LAN play)
└── WebPlayer       (NiceGUI via EventBus + Queue)
```

All player types implement the same abstract interface:

| Method | Returns | Purpose |
|--------|---------|---------|
| `pick_turn_type(round)` | `"KABO"` / `"HIT_DECK"` / `"HIT_DISCARD_PILE"` | Choose turn action |
| `decide_on_card_use(card)` | `"KEEP"` / `"DISCARD"` / `"EFFECT"` | What to do with drawn card |
| `pick_hand_cards_for_exchange(card)` | `List[Card]` | Select cards to swap out |
| `pick_position_for_new_card(positions)` | `int` | Where to place new card |
| `pick_cards_to_see(num)` | `List[int]` | Peek: which own cards to look at |
| `specify_spying(round)` | `(Player, Card)` | Spy: which opponent's card to see |
| `specify_swap(round)` | `(Player, int, int)` | Swap: card positions to exchange |

### Card Visibility Model

Each card tracks who can see it, preserving the memory challenge:

```python
card.publicly_visible: bool                  # Face-up for everyone (discard, revealed)
card.known_to_owner: bool                    # Owner remembers this card's value
card.known_to_other_players: List[Player]    # Players who spied on this card
```

The web UI only renders card values when `publicly_visible` is `True` - private knowledge (from peeks/spies) is shown temporarily, then hidden again.

### Multiplayer Room System

Rooms are managed server-side in memory (`game_room.py`):

1. **Create room** - generates a 5-character alphanumeric code
2. **Share code** - other players enter the code to join
3. **Start game** - host starts when enough players have joined
4. **State broadcasting** - each player's `WebPlayer` builds perspective-aware snapshots and broadcasts to all others via per-player `EventBus` instances
5. **Reconnection** - browser storage persists `room_code` and `player_name` for automatic rejoin on page refresh

### AI Strategy (ComputerPlayer)

The AI uses a greedy heuristic:

- Estimates hand value: known card values + 6.0 for each unknown card
- Calls KABO when estimated sum <= 5
- Takes from discard pile if top card value <= 4 (replaces highest known card)
- Keeps drawn cards with value <= 3, discards higher ones
- Always uses card effects when available
- Spies on cards it hasn't seen; swaps its highest known card with a random opponent card

### Configuration (`config/rules.py`)

| Constant | Value | Description |
|----------|-------|-------------|
| `TARGET_POINT_VALUE` | 100 | Score threshold that ends the game |
| `POINT_VALUE_AFTER_HITTING_TARGET` | 50 | Score drops to this on first hit of 100 |
| `CARDS_PER_PLAYER` | 4 | Starting hand size |
| `NUMBER_OF_CARDS_TO_SEE` | 2 | Cards peeked at round start |
| `KABO_MALUS` | 10 | Penalty added for failed KABO call |
| `KAMIKADZE_PENALTY` | 50 | Points given to all others on Kamikadze win |

### Event Types

The `EventBus` routes these events from the game thread to the UI:

| Event | Payload | Purpose |
|-------|---------|---------|
| `state_update` | `GameStateSnapshot` | Full game state refresh |
| `input_request` | `InputRequest` | Player must make a decision |
| `log` | `str` | Game event message for log panel |
| `notification` | `TurnNotification` | Opponent action broadcast |
| `game_over` | `None` | Game has ended |

---

## Deployment

The app is deployed on [Railway](https://railway.app) using the included `Dockerfile`. Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8080` | Server port |
| `STORAGE_SECRET` | `kabo-default-dev-secret` | Browser storage encryption key (change in production) |
