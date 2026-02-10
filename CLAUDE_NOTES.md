# CLAUDE_NOTES.md - Kabo Project Reference

## Architecture

### Two-Thread Model
1. **Game Thread** (background daemon) - Runs `Game.play_game()` synchronously. WebPlayer decision methods BLOCK on `queue.Queue.get()` until the UI responds.
2. **UI Thread** (NiceGUI main thread) - Serves `http://localhost:8080`. A `ui.timer(0.1)` polls a `_ui_queue` every 100ms to drain game events and update the UI. User clicks call `submit_response()` which does `queue.put()` to unblock the game thread.

### Communication Flow
```
Game Thread                          UI Thread
-----------                          ---------
WebPlayer._build_state_snapshot()
EventBus.emit("state_update")   -->  [_ui_queue] --> ui.timer drains
EventBus.emit("input_request")  -->  ActionPanel.show_request()
_response_queue.get() [BLOCKS]  <--  user click --> on_submit(resp) --> queue.put()
continue game logic...
```

### Key Classes
- **EventBus** (`src/web/event_bus.py`): Thread-safe pub/sub with `threading.Lock`. Callbacks run synchronously in the caller's thread.
- **WebPlayer** (`src/web/web_player.py`): Bridges sync game thread with async UI. Emits `InputRequest` via EventBus, blocks on `_response_queue`.
- **WebApp** (`src/web/app.py`): NiceGUI entry point. Uses a separate `_ui_queue` for game-to-UI events (polled by timer).

---

## File Structure

### Core Game Logic (`src/`)
| File | Lines | Purpose |
|------|-------|---------|
| `card.py` | ~82 | Card class: value, effect (KUK/SPION/KSEFT), visibility tracking |
| `deck.py` | ~23 | Deck wrapper around `List[Card]` with shuffle |
| `discard_pile.py` | ~38 | DiscardPile with add/hit methods |
| `game.py` | ~188 | Game orchestrator: manages rounds, scores, winners, player creation |
| `round.py` | ~213 | Round logic: deal, turn cycle, KABO countdown, Kamikadze check |
| `player.py` | ~389 | Abstract Player base: turn logic, card effects, score calculation |
| `human_player.py` | ~266 | Terminal-based input via `input()` with validation |
| `computer_player.py` | ~173 | Greedy AI: estimates hand value, KABO threshold <= 5 |
| `network_player.py` | ~167 | LAN multiplayer via TCP socket, length-prefixed JSON |
| `server.py` | — | Game server for LAN multiplayer |
| `client.py` | — | Client for LAN multiplayer |

### Web GUI (`src/web/`)
| File | Purpose |
|------|---------|
| `app.py` | NiceGUI entry point, cross-thread event handling, dark mode |
| `event_bus.py` | Thread-safe pub/sub for game-to-UI events |
| `game_state.py` | Dataclasses: `GameStateSnapshot`, `PlayerView`, `CardView`, `InputRequest` |
| `game_session.py` | Manages game in daemon thread, `PrintInterceptor` captures stdout |
| `web_player.py` | Bridges sync game thread with async NiceGUI via queues |

### Web Components (`src/web/components/`)
| File | Purpose |
|------|---------|
| `setup_page.py` | Initial form: player name + AI count slider |
| `game_table.py` | Main layout: opponents, deck/discard, player hand, action panel, log |
| `action_panel.py` | Dynamic controls for 7+ input request types |
| `card_component.py` | HTML/CSS card rendering with Tailwind, color-coded by value |
| `game_log.py` | Scrollable log (200-message limit, auto-scroll) |
| `scoreboard.py` | Player scores sorted ascending, highlights current player |

### Config & Entry
| File | Purpose |
|------|---------|
| `main.py` | CLI entry: `--mode hotseat|server|client|web` |
| `config/rules.py` | Constants: `TARGET_POINT_VALUE=100`, `KABO_MALUS=10`, `CARDS_PER_PLAYER=4`, card effects map |

---

## Game Rules (Kabo/Cabo)

### Setup
- 2-4 players, 52-card deck (values 0-13)
- 4 cards dealt face-down per player
- Player peeks at 2 of their cards at round start
- Top card of discard pile revealed

### Goal
- Lowest hand value wins the round
- First to exceed 100 total points loses
- Hit exactly 100 -> drop to 50 (once per game)

### Turn Options
1. **Call KABO** - triggers final round (everyone else gets 1 more turn)
2. **Draw from deck** - then choose KEEP / DISCARD / USE EFFECT
3. **Take from discard** - card is automatically kept (publicly visible)

### Card Effects (only on discard, not on keep)
- **7-8 (KUK/Peek)**: Look at one of your own cards
- **9-10 (SPION/Spy)**: Look at one of an opponent's cards
- **11-12 (KSEFT/Swap)**: Swap one of your cards with an opponent's card (blind)

### Multi-Card Discard
- Can discard multiple cards of the SAME value simultaneously
- If values differ -> penalty: cards revealed + draw extra card face-down

### Kamikadze
- Hand with 2 twelves + 2 thirteens = instant win
- All other players get 50 penalty points

### KABO Scoring
- Successful KABO (caller has lowest score): 0 points
- Failed KABO (not lowest): hand_sum + 10 penalty

---

## Player Type Hierarchy

```
Player (abstract base - src/player.py)
  ├── HumanPlayer   (terminal input)
  ├── ComputerPlayer (greedy AI)
  ├── NetworkPlayer  (LAN via TCP)
  └── WebPlayer      (NiceGUI via EventBus + Queue)
```

### Key Abstract Methods (implemented by each subclass)
- `pick_turn_type(round)` -> `"KABO" | "HIT_DECK" | "HIT_DISCARD_PILE"`
- `decide_on_card_use(card)` -> `"KEEP" | "DISCARD" | "EFFECT"`
- `pick_hand_cards_for_exchange(drawn_card)` -> `List[Card]`
- `pick_position_for_new_card(positions)` -> `int`
- `pick_cards_to_see(num)` -> `List[int]`
- `specify_spying(round)` -> `Tuple[Player, Card]`
- `specify_swap(round)` -> `Tuple[Player, int, int]`

### Card Visibility Model
```python
card.publicly_visible: bool          # Everyone can see
card.known_to_owner: bool            # Only owner can see
card.known_to_other_players: List[Player]  # Specific players can see
```

---

## Key Code Patterns

### InputRequest Flow (WebPlayer)
```python
# 1. WebPlayer builds state snapshot with perspective-aware visibility
state = self._build_state_snapshot(_round)
state.input_request = InputRequest(
    request_type="pick_turn_type",
    prompt="Your turn! Choose action:",
    options=["HIT_DECK", "HIT_DISCARD_PILE", "KABO"],
    extra={"discard_top": 5}
)
# 2. Emit to EventBus -> queued for UI thread
self._emit_input_request(state)
# 3. Block until user responds
response = self._wait_for_response()  # queue.get()
```

### Game Loop (Round.start_playing)
```python
_players_cycle = cycle(self.players)  # infinite iterator
_kabo_counter = len(self.players)
_kabo_active = False

while self.main_deck.cards:
    if _kabo_counter == 0:
        break
    current_player = next(_players_cycle)
    kabo_called = current_player.perform_turn(_round=self)
    if kabo_called:
        self.kabo_called = True
        _kabo_active = True
    if _kabo_active:
        _kabo_counter -= 1
```

### ComputerPlayer Strategy
- Estimates hand: known card values + 6 for unknown cards
- Calls KABO when estimated sum <= 5
- Takes from discard if top card value <= 4 and replaces highest known card
- On draw: keeps cards with value <= 4, discards higher
- Always uses effects when available
- Replaces highest known card during exchange

---

## Known Issues & Areas for Improvement

### TODOs in Code
1. `src/player.py:386` - Card knowledge tracking after swap needs cleanup (remove owner from `known_to_other_players`)
2. `src/round.py:42` - `game` param not typed due to circular import
3. Network mode (`server.py`, `client.py`) - Largely untested with current architecture

### Code Quality
- No automated tests (only manual `test.py` scratch file)
- Print statements used instead of a logging framework
- String constants for choices instead of Enums (e.g. `"KABO"`, `"HIT_DECK"`)
- Some circular import workarounds via `TYPE_CHECKING`
- No input validation in some paths (invalid card positions could crash)
- Potential duplicate player names not checked

### From `list_of_good_practices.txt`
- Consider declaring all instance attributes in `__init__`
- Use Enums for string constants
- Apply typing more rigorously
- Add error handling to improve input function readability
- Address code repetitions between player types
- Use properties for complex attribute setters

### Web GUI Specific
- No duplicate-click prevention (rapid clicking could submit twice)
- Game-over "Play Again" restarts full session; no way to change settings
- PrintInterceptor captures ALL stdout, could catch unrelated output
- Single-player session only (one WebPlayer per NiceGUI instance)

---

## Running the Project

```bash
# Web mode (primary)
python main.py --mode web
# Open http://localhost:8080

# Terminal hotseat
python main.py --mode hotseat

# LAN server
python main.py --mode server

# LAN client
python main.py --mode client
```

### Dependencies
- `nicegui >= 1.4`
- Python 3.10+
- See `requirements-web.txt`
