"""
Serializable snapshot of the game state for the UI.

The game thread builds a GameStateSnapshot from live game objects.
The UI reads it to render cards, scores, and other info.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class CardView:
    """How a single card appears to the viewing player."""
    position: int
    value: Optional[int]  # None if face-down / unknown
    is_known: bool  # whether the viewer knows the value
    is_publicly_visible: bool


@dataclass
class PlayerView:
    """How a player's hand appears to the viewing player."""
    name: str
    character: str  # "WEB", "COMPUTER", etc.
    is_current_player: bool  # is this the viewing player?
    cards: List[CardView] = field(default_factory=list)
    game_score: int = 0
    called_kabo: bool = False


@dataclass
class InputRequest:
    """Describes what input the UI should collect from the player."""
    request_type: str  # "pick_turn_type", "decide_on_card_use", etc.
    prompt: str
    options: List[str] = field(default_factory=list)
    extra: Dict = field(default_factory=dict)


@dataclass
class GameStateSnapshot:
    """Complete snapshot of the game state as seen by a specific player."""
    phase: str  # "setup", "peek", "playing", "round_over", "game_over"
    round_number: int = 0
    current_player_name: str = ""
    discard_top_value: Optional[int] = None
    deck_cards_left: int = 0
    players: List[PlayerView] = field(default_factory=list)
    input_request: Optional[InputRequest] = None
    scores: Dict[str, int] = field(default_factory=dict)
    kabo_called: bool = False
    kabo_caller: str = ""
    active_turn_player_name: str = ""
