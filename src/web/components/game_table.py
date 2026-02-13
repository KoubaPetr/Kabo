"""
Main game table view - renders the full game board.

Layout:
  - Top: Opponent hands
  - Center: Deck + Discard pile
  - Bottom: Player's hand
  - Below: Action panel
  - Footer: Game log + Scoreboard
"""
from nicegui import ui, app
from typing import Optional, List

from src.web.game_state import (
    GameStateSnapshot, PlayerView, CardView, RoundSummary, TurnNotification,
    AnimationEvent,
)
from src.web.components.card_component import render_card, render_card_back, render_deck, render_discard_pile
from src.web.components.game_log import GameLog
from src.web.components.scoreboard import Scoreboard
from src.web.components.action_panel import ActionPanel


class GameTable:
    """Manages the complete game table UI."""

    def __init__(self, on_submit):
        """
        Args:
            on_submit: callback(response) when user submits an action
        """
        self.on_submit = on_submit
        self.game_log = GameLog()
        self.scoreboard = Scoreboard()
        self.action_panel = ActionPanel(on_submit=on_submit)

        # UI containers for dynamic updates
        self._opponents_container = None
        self._center_container = None
        self._player_hand_container = None
        self._status_label = None
        self._main_container = None
        self._notification_container = None
        self._notification_timer = None
        # Click-to-interact state
        self._clickable_mode: Optional[str] = None
        self._last_state: Optional[GameStateSnapshot] = None
        # Highlight state for newly placed card after multi-exchange
        self._new_card_index: Optional[int] = None
        self._compaction_active: bool = False
        # Animation queue
        self._animation_queue: List[AnimationEvent] = []
        self._animating: bool = False
        self._pending_state: Optional[GameStateSnapshot] = None
        self._animation_overlay = None

    def build(self) -> None:
        """Create the full game table layout."""
        # Add CSS animations for cards
        ui.add_head_html("""
        <style>
        @keyframes slideFromDeck {
            0% { transform: translateX(-100px) translateY(-50px) scale(0.5); opacity: 0; }
            100% { transform: translateX(0) translateY(0) scale(1); opacity: 1; }
        }
        @keyframes slideToDiscard {
            0% { transform: translateX(0) translateY(0) scale(1); opacity: 1; }
            100% { transform: translateX(100px) translateY(-50px) scale(0.5); opacity: 0; }
        }
        @keyframes flipCard {
            0% { transform: perspective(400px) rotateY(0deg); }
            50% { transform: perspective(400px) rotateY(90deg); }
            100% { transform: perspective(400px) rotateY(0deg); }
        }
        @keyframes cardAppear {
            0% { transform: scale(0.3); opacity: 0; }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); opacity: 1; }
        }
        @keyframes newCardGlow {
            0% { box-shadow: 0 0 5px #fbbf24, 0 0 10px #fbbf24; border-color: #fbbf24; }
            50% { box-shadow: 0 0 15px #fbbf24, 0 0 30px #f59e0b; border-color: #f59e0b; }
            100% { box-shadow: 0 0 5px #fbbf24, 0 0 10px #fbbf24; border-color: #fbbf24; }
        }
        @keyframes slideCompact {
            0% { transform: translateX(20px); opacity: 0.7; }
            100% { transform: translateX(0); opacity: 1; }
        }
        .animate-draw { animation: slideFromDeck 0.4s ease-out; }
        .animate-discard { animation: slideToDiscard 0.3s ease-in; }
        .animate-flip { animation: flipCard 0.5s ease-in-out; }
        .animate-appear { animation: cardAppear 0.3s ease-out; }
        .animate-new-card { animation: newCardGlow 1.5s ease-in-out 3; border: 2px solid #fbbf24 !important; }
        .animate-compact { animation: slideCompact 0.4s ease-out; }
        .card-hover:hover { transform: translateY(-4px); transition: transform 0.15s ease; }
        </style>
        """)

        # JavaScript animation helpers
        ui.add_head_html("""
        <script>
        window.kaboAnimations = {
            _createOverlay() {
                let ov = document.getElementById('kabo-anim-overlay');
                if (!ov) {
                    ov = document.createElement('div');
                    ov.id = 'kabo-anim-overlay';
                    ov.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:9999;';
                    document.body.appendChild(ov);
                }
                return ov;
            },
            _createIcon(emoji, x, y, size) {
                const el = document.createElement('div');
                el.style.cssText = `position:absolute;left:${x}px;top:${y}px;font-size:${size}px;transform:translate(-50%,-50%) scale(0);transition:transform 0.3s ease-out, opacity 0.3s;opacity:0;z-index:10000;filter:drop-shadow(0 0 10px rgba(255,255,255,0.5));`;
                el.textContent = emoji;
                return el;
            },
            showEffectIcon(emoji, label, targetId, posIdx, durationMs) {
                const ov = this._createOverlay();
                const target = document.getElementById(targetId);
                if (!target) { return; }
                const cards = target.querySelectorAll('[class*="rounded-lg"]');
                let rect;
                if (cards.length > posIdx && posIdx >= 0) {
                    rect = cards[posIdx].getBoundingClientRect();
                } else {
                    rect = target.getBoundingClientRect();
                }
                const cx = rect.left + rect.width/2;
                const cy = rect.top + rect.height/2;
                const icon = this._createIcon(emoji, cx, cy - 20, 48);
                ov.appendChild(icon);
                // Label below icon
                const lbl = document.createElement('div');
                lbl.style.cssText = `position:absolute;left:${cx}px;top:${cy + 25}px;transform:translate(-50%,0) scale(0);transition:transform 0.3s ease-out, opacity 0.3s;opacity:0;font-size:14px;font-weight:bold;color:white;text-shadow:0 0 8px rgba(0,0,0,0.8);white-space:nowrap;`;
                lbl.textContent = label;
                ov.appendChild(lbl);
                requestAnimationFrame(() => {
                    icon.style.transform = 'translate(-50%,-50%) scale(1)';
                    icon.style.opacity = '1';
                    lbl.style.transform = 'translate(-50%,0) scale(1)';
                    lbl.style.opacity = '1';
                });
                setTimeout(() => {
                    icon.style.transform = 'translate(-50%,-50%) scale(0)';
                    icon.style.opacity = '0';
                    lbl.style.transform = 'translate(-50%,0) scale(0)';
                    lbl.style.opacity = '0';
                    setTimeout(() => { icon.remove(); lbl.remove(); }, 400);
                }, durationMs - 400);
            },
            showSpyLine(fromId, toId, posIdx, durationMs) {
                const ov = this._createOverlay();
                const from = document.getElementById(fromId);
                const to = document.getElementById(toId);
                if (!from || !to) return;
                const fromRect = from.getBoundingClientRect();
                const toCards = to.querySelectorAll('[class*="rounded-lg"]');
                let toRect;
                if (toCards.length > posIdx && posIdx >= 0) {
                    toRect = toCards[posIdx].getBoundingClientRect();
                } else {
                    toRect = to.getBoundingClientRect();
                }
                const x1 = fromRect.left + fromRect.width/2;
                const y1 = fromRect.top + fromRect.height/2;
                const x2 = toRect.left + toRect.width/2;
                const y2 = toRect.top + toRect.height/2;
                const svg = document.createElementNS('http://www.w3.org/2000/svg','svg');
                svg.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;';
                const line = document.createElementNS('http://www.w3.org/2000/svg','line');
                line.setAttribute('x1',x1); line.setAttribute('y1',y1);
                line.setAttribute('x2',x1); line.setAttribute('y2',y1);
                line.setAttribute('stroke','#fbbf24'); line.setAttribute('stroke-width','3');
                line.setAttribute('stroke-dasharray','8,4'); line.setAttribute('opacity','0.8');
                line.style.transition = `all ${durationMs*0.3}ms ease-out`;
                svg.appendChild(line);
                ov.appendChild(svg);
                requestAnimationFrame(() => {
                    line.setAttribute('x2',x2); line.setAttribute('y2',y2);
                });
                setTimeout(() => {
                    line.style.opacity = '0';
                    setTimeout(() => svg.remove(), 400);
                }, durationMs - 400);
            },
            showSwapArrows(hand1Id, pos1, hand2Id, pos2, durationMs) {
                const ov = this._createOverlay();
                const h1 = document.getElementById(hand1Id);
                const h2 = document.getElementById(hand2Id);
                if (!h1 || !h2) return;
                const cards1 = h1.querySelectorAll('[class*="rounded-lg"]');
                const cards2 = h2.querySelectorAll('[class*="rounded-lg"]');
                let r1 = (cards1.length > pos1 && pos1 >= 0) ? cards1[pos1].getBoundingClientRect() : h1.getBoundingClientRect();
                let r2 = (cards2.length > pos2 && pos2 >= 0) ? cards2[pos2].getBoundingClientRect() : h2.getBoundingClientRect();
                const cx = (r1.left+r1.width/2 + r2.left+r2.width/2) / 2;
                const cy = (r1.top+r1.height/2 + r2.top+r2.height/2) / 2;
                const icon = this._createIcon('\\u21C4', cx, cy, 40);
                icon.style.color = '#fbbf24';
                ov.appendChild(icon);
                requestAnimationFrame(() => {
                    icon.style.transform = 'translate(-50%,-50%) scale(1) rotate(0deg)';
                    icon.style.opacity = '1';
                });
                setTimeout(() => {
                    icon.style.transform = 'translate(-50%,-50%) scale(1) rotate(360deg)';
                }, 300);
                setTimeout(() => {
                    icon.style.transform = 'translate(-50%,-50%) scale(0)';
                    icon.style.opacity = '0';
                    setTimeout(() => icon.remove(), 400);
                }, durationMs - 400);
            },
            showKaboCall(playerName, durationMs) {
                const ov = this._createOverlay();
                const el = document.createElement('div');
                el.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%) scale(0);font-size:64px;font-weight:bold;color:#ef4444;text-shadow:0 0 20px rgba(239,68,68,0.8),0 0 40px rgba(239,68,68,0.4);transition:transform 0.4s cubic-bezier(0.34,1.56,0.64,1), opacity 0.4s;opacity:0;z-index:10001;white-space:nowrap;';
                el.innerHTML = 'KABO!<br><span style="font-size:24px;color:white;">' + playerName + '</span>';
                el.style.textAlign = 'center';
                ov.appendChild(el);
                requestAnimationFrame(() => {
                    el.style.transform = 'translate(-50%,-50%) scale(1)';
                    el.style.opacity = '1';
                });
                setTimeout(() => {
                    el.style.transform = 'translate(-50%,-50%) scale(1.2)';
                }, durationMs * 0.3);
                setTimeout(() => {
                    el.style.transform = 'translate(-50%,-50%) scale(0)';
                    el.style.opacity = '0';
                    setTimeout(() => el.remove(), 500);
                }, durationMs - 500);
            },
            showDrawAnimation(fromId, toId, durationMs) {
                const ov = this._createOverlay();
                const from = document.getElementById(fromId);
                const to = document.getElementById(toId);
                if (!from || !to) return;
                const fr = from.getBoundingClientRect();
                const tr = to.getBoundingClientRect();
                const card = document.createElement('div');
                card.style.cssText = `position:absolute;left:${fr.left+fr.width/2-24}px;top:${fr.top+fr.height/2-32}px;width:48px;height:64px;background:#263238;border:2px solid #90a4ae;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#90a4ae;font-weight:bold;font-size:16px;transition:all ${durationMs*0.7}ms ease-in-out;z-index:10000;box-shadow:0 4px 12px rgba(0,0,0,0.5);`;
                card.textContent = '?';
                ov.appendChild(card);
                requestAnimationFrame(() => {
                    card.style.left = (tr.left+tr.width/2-24) + 'px';
                    card.style.top = (tr.top+tr.height/2-32) + 'px';
                    card.style.opacity = '0.7';
                });
                setTimeout(() => card.remove(), durationMs);
            }
        };
        </script>
        """)

        self._main_container = ui.column().classes(
            "w-full max-w-4xl mx-auto gap-4 p-4"
        )

        with self._main_container:
            # Notification overlay
            self._notification_container = ui.element("div").classes(
                "w-full text-center hidden"
            ).style(
                "transition: all 0.3s ease-in-out;"
            )

            # Status bar
            with ui.row().classes("w-full items-center justify-between"):
                self._status_label = ui.label("Game starting...").classes(
                    "text-lg font-bold text-yellow-300"
                )
                self._round_label = ui.label("").classes("text-sm text-gray-400")

            # Opponents section
            self._opponents_container = ui.row().classes(
                "w-full justify-center gap-6 flex-wrap"
            )

            ui.separator()

            # Center: Deck + Discard
            self._center_container = ui.row().classes(
                "w-full justify-center items-center gap-8"
            )
            self._center_container.props('id="kabo-center"')

            ui.separator()

            # Player's hand
            self._player_hand_label = ui.label("Your Hand").classes(
                "text-sm font-bold text-gray-300"
            )
            self._player_hand_container = ui.row().classes(
                "w-full justify-center gap-3"
            )
            self._player_hand_container.props('id="kabo-hand-self"')

            ui.separator()

            # Action panel
            self.action_panel._game_table = self
            self.action_panel.build()

            # Bottom: Log + Scoreboard side by side
            with ui.row().classes("w-full gap-4"):
                with ui.column().classes("flex-grow"):
                    self.game_log.build()
                with ui.column().classes("w-48"):
                    self.scoreboard.build()

    def _get_revealed_cards_map(self, state: GameStateSnapshot):
        """Extract revealed card overrides from the current input request.

        Returns a dict mapping (owner_name, position) -> value for cards
        that should be temporarily shown face-up.
        """
        revealed = {}
        if (state.input_request and
                state.input_request.request_type in ("card_reveal", "initial_peek_reveal")):
            for rc in state.input_request.extra.get("revealed_cards", []):
                key = (rc["owner"], rc["position"])
                revealed[key] = rc["value"]
        return revealed

    def update_state(self, state: GameStateSnapshot) -> None:
        """Update the entire table from a game state snapshot."""
        if not self._main_container:
            return

        # Defer state updates while animations are playing
        if self._animating:
            self._pending_state = state
            return

        # Detect changes for animations
        prev_hand_count = 0
        if self._last_state:
            for p in self._last_state.players:
                if p.is_current_player:
                    prev_hand_count = len(p.cards)
                    break
        self._last_state = state

        # Detect new card placement highlight from multi-exchange
        if (state.input_request and
                state.input_request.extra.get("compacted")):
            self._new_card_index = state.input_request.extra.get("new_card_index")
            self._compaction_active = True
        else:
            self._new_card_index = None
            self._compaction_active = False

        # Handle round_over phase with summary display
        if state.phase == "round_over" and state.round_summary:
            self._show_round_summary(state)
            return

        # Update status
        if self._status_label:
            if state.kabo_called:
                self._status_label.set_text(
                    f"KABO called by {state.kabo_caller}! Final turns..."
                )
                self._status_label.classes(replace="text-lg font-bold text-red-400")
            elif (state.active_turn_player_name
                  and state.active_turn_player_name != state.current_player_name):
                # Multiplayer: another player's turn
                self._status_label.set_text(
                    f"Waiting for {state.active_turn_player_name}..."
                )
                self._status_label.classes(replace="text-lg font-bold text-gray-400")
            else:
                self._status_label.set_text("Your turn!")
                self._status_label.classes(replace="text-lg font-bold text-yellow-300")
                # Show YOUR TURN notification for pick_turn_type
                if (state.input_request and
                        state.input_request.request_type == "pick_turn_type"):
                    self.show_notification(TurnNotification(
                        message="YOUR TURN!",
                        notification_type="your_turn",
                        player_name=state.current_player_name,
                    ))

        if self._round_label:
            self._round_label.set_text(
                f"Round {state.round_number + 1} | Deck: {state.deck_cards_left}"
            )

        # Find the web player (is_current_player=True)
        web_player_view = None
        opponent_views = []
        for p in state.players:
            if p.is_current_player:
                web_player_view = p
            else:
                opponent_views.append(p)

        # Determine clickable mode from input request
        self._clickable_mode = None
        if state.input_request:
            rt = state.input_request.request_type
            if rt == "pick_turn_type":
                self._clickable_mode = "pick_turn_type"
            elif rt == "decide_on_card_use":
                self._clickable_mode = "decide_on_card_use"
            elif rt in ("pick_hand_cards_for_exchange", "pick_cards_to_see"):
                self._clickable_mode = rt
            elif rt == "specify_spying":
                self._clickable_mode = "specify_spying"
            elif rt == "specify_swap":
                self._clickable_mode = "specify_swap_own"

        # Render opponents (clickable in spy/swap modes, with turn indicator)
        opponents_clickable = self._clickable_mode in (
            "specify_spying", "specify_swap_opponent"
        )
        revealed_map = self._get_revealed_cards_map(state)
        self._revealed_map = revealed_map

        if self._opponents_container:
            self._opponents_container.clear()
            with self._opponents_container:
                for opp in opponent_views:
                    is_active = (opp.name == state.active_turn_player_name)
                    self._render_opponent_hand(
                        opp, clickable=opponents_clickable,
                        is_active_turn=is_active,
                        revealed_map=revealed_map,
                    )

        # Render center (deck + discard)
        deck_clickable = (self._clickable_mode == "pick_turn_type")
        discard_clickable = (self._clickable_mode == "pick_turn_type"
                             and state.discard_top_value is not None)
        if self._center_container:
            self._center_container.clear()
            with self._center_container:
                render_deck(
                    state.deck_cards_left,
                    clickable=deck_clickable,
                    on_click=self._on_deck_click if deck_clickable else None,
                )
                render_discard_pile(
                    state.discard_top_value,
                    clickable=discard_clickable,
                    on_click=self._on_discard_click if discard_clickable else None,
                )

        # Render player's hand
        hand_clickable = self._clickable_mode in (
            "decide_on_card_use",
            "pick_hand_cards_for_exchange", "pick_cards_to_see",
            "specify_swap_own",
        )
        cur_hand_count = len(web_player_view.cards) if web_player_view else 0
        hand_changed = (cur_hand_count != prev_hand_count and prev_hand_count > 0)
        if self._player_hand_container:
            self._player_hand_container.clear()
            with self._player_hand_container:
                if web_player_view:
                    for idx, card in enumerate(web_player_view.cards):
                        selected = card.position in self.action_panel._selected_cards
                        if self._new_card_index is not None and idx == self._new_card_index:
                            anim = "animate-new-card"
                        elif self._compaction_active:
                            anim = "animate-compact"
                        elif hand_changed:
                            anim = "animate-appear"
                        else:
                            anim = ""
                        # Check for temporary reveal override
                        display_card = card
                        reveal_key = (web_player_view.name, card.position)
                        if reveal_key in revealed_map:
                            display_card = CardView(
                                position=card.position,
                                value=revealed_map[reveal_key],
                                is_known=True,
                                is_publicly_visible=False,
                            )
                        render_card(
                            display_card, size="normal",
                            label=f"#{card.position}",
                            clickable=hand_clickable,
                            selected=selected,
                            animate=anim,
                            on_click=(
                                lambda p=card.position: self._on_hand_card_click(p)
                            ) if hand_clickable else None,
                        )

        # Update player hand label with turn indicator
        is_my_turn = (
            state.active_turn_player_name == state.current_player_name
        )
        if hasattr(self, "_player_hand_label") and self._player_hand_label:
            if is_my_turn:
                self._player_hand_label.set_text("Your Hand - YOUR TURN!")
                self._player_hand_label.classes(
                    replace="text-sm font-bold text-yellow-300"
                )
            else:
                self._player_hand_label.set_text("Your Hand")
                self._player_hand_label.classes(
                    replace="text-sm font-bold text-gray-300"
                )

        # Update scoreboard
        self.scoreboard.update(state.players)

    def _render_opponent_hand(self, opponent: PlayerView,
                              clickable: bool = False,
                              is_active_turn: bool = False,
                              revealed_map: dict = None) -> None:
        """Render a single opponent's hand."""
        revealed_map = revealed_map or {}
        border = (
            "border-2 border-yellow-400 rounded-lg p-2"
            if is_active_turn else "p-2"
        )
        hand_col = ui.column().classes(f"items-center gap-1 {border}")
        hand_col.props(f'id="kabo-hand-{opponent.name}"')
        with hand_col:
            label_text = opponent.name
            if opponent.character == "COMPUTER":
                label_text += " (AI)"
            if opponent.called_kabo:
                label_text += " [KABO]"
            label_cls = "text-sm font-bold"
            if is_active_turn:
                label_text += " - Playing..."
                label_cls += " text-yellow-300"
            else:
                label_cls += " text-gray-300"
            ui.label(label_text).classes(label_cls)
            with ui.row().classes("gap-1"):
                for card in opponent.cards:
                    # Check for temporary reveal override (spy)
                    display_card = card
                    reveal_key = (opponent.name, card.position)
                    if reveal_key in revealed_map:
                        display_card = CardView(
                            position=card.position,
                            value=revealed_map[reveal_key],
                            is_known=True,
                            is_publicly_visible=False,
                        )
                    render_card(
                        display_card, size="small",
                        clickable=clickable,
                        on_click=(
                            lambda n=opponent.name, idx=card.position:
                                self._on_opponent_card_click(n, idx)
                        ) if clickable else None,
                    )

    def _rerender_player_hand(self, state: GameStateSnapshot) -> None:
        """Re-render just the player's hand cards (for selection updates)."""
        web_player_view = None
        for p in state.players:
            if p.is_current_player:
                web_player_view = p
                break
        if not web_player_view or not self._player_hand_container:
            return
        hand_clickable = self._clickable_mode in (
            "decide_on_card_use",
            "pick_hand_cards_for_exchange", "pick_cards_to_see",
            "specify_swap_own",
        )
        revealed_map = getattr(self, "_revealed_map", {})
        self._player_hand_container.clear()
        with self._player_hand_container:
            for card in web_player_view.cards:
                selected = card.position in self.action_panel._selected_cards
                display_card = card
                reveal_key = (web_player_view.name, card.position)
                if reveal_key in revealed_map:
                    display_card = CardView(
                        position=card.position,
                        value=revealed_map[reveal_key],
                        is_known=True,
                        is_publicly_visible=False,
                    )
                render_card(
                    display_card, size="normal",
                    label=f"#{card.position}",
                    clickable=hand_clickable,
                    selected=selected,
                    on_click=(
                        lambda p=card.position: self._on_hand_card_click(p)
                    ) if hand_clickable else None,
                )

    def _on_deck_click(self) -> None:
        """Handle click on the deck - submit HIT_DECK."""
        self._clickable_mode = None
        self.action_panel._submit("HIT_DECK")

    def _on_discard_click(self) -> None:
        """Handle click on the discard pile - submit HIT_DISCARD_PILE."""
        self._clickable_mode = None
        self.action_panel._submit("HIT_DISCARD_PILE")

    def _on_hand_card_click(self, position: int) -> None:
        """Handle click on a hand card - toggle selection or submit position."""
        if self._clickable_mode == "decide_on_card_use":
            self.action_panel._toggle_card_selection_for_keep(position)
            if self._last_state:
                self._rerender_player_hand(self._last_state)
        elif self._clickable_mode == "pick_hand_cards_for_exchange":
            self.action_panel._toggle_card_selection(position)
            if self._last_state:
                self._rerender_player_hand(self._last_state)
        elif self._clickable_mode == "pick_cards_to_see":
            num_to_see = 1
            if self.action_panel._current_request:
                num_to_see = self.action_panel._current_request.extra.get(
                    "num_cards_to_see", 1)
            self.action_panel._toggle_peek_selection(position, num_to_see)
            # Re-render hand to show updated selection highlight
            if self._last_state:
                self._rerender_player_hand(self._last_state)
        elif self._clickable_mode == "specify_swap_own":
            self.action_panel.select_swap_own(position)

    def _on_opponent_card_click(self, opponent_name: str, card_idx: int) -> None:
        """Handle click on an opponent's card — for spy or swap."""
        if self._clickable_mode == "specify_spying":
            self._clickable_mode = None
            self.action_panel._submit({
                "opponent": opponent_name,
                "card_idx": card_idx,
            })
        elif self._clickable_mode == "specify_swap_opponent":
            self._clickable_mode = None
            self.action_panel.complete_swap(opponent_name, card_idx)

    def _render_opponents_for_mode(self, state: GameStateSnapshot) -> None:
        """Re-render opponents section with current clickable mode."""
        opponent_views = [p for p in state.players if not p.is_current_player]
        opponents_clickable = self._clickable_mode in (
            "specify_spying", "specify_swap_opponent"
        )
        revealed_map = getattr(self, "_revealed_map", {})
        if self._opponents_container:
            self._opponents_container.clear()
            with self._opponents_container:
                for opp in opponent_views:
                    is_active = (opp.name == state.active_turn_player_name)
                    self._render_opponent_hand(
                        opp, clickable=opponents_clickable,
                        is_active_turn=is_active,
                        revealed_map=revealed_map,
                    )

    def show_notification(self, notification: TurnNotification) -> None:
        """Display an animated notification banner."""
        if not self._notification_container:
            return

        self._notification_container.clear()
        self._notification_container.classes(remove="hidden")

        style_map = {
            "your_turn": (
                "bg-yellow-600 text-white text-xl font-bold py-3 px-6 rounded-lg "
                "animate-pulse shadow-lg"
            ),
            "opponent_action": (
                "bg-blue-700 text-white text-base font-semibold py-2 px-4 rounded-lg "
                "shadow-md"
            ),
            "kabo_called": (
                "bg-red-700 text-white text-xl font-bold py-3 px-6 rounded-lg "
                "animate-bounce shadow-lg"
            ),
        }
        css = style_map.get(notification.notification_type,
                            "bg-gray-700 text-white py-2 px-4 rounded-lg")

        with self._notification_container:
            ui.label(notification.message).classes(css)

        # Auto-dismiss: YOUR_TURN stays 3s, opponent actions 4s, kabo 5s
        dismiss_ms = {
            "your_turn": 3000,
            "opponent_action": 4000,
            "kabo_called": 5000,
        }.get(notification.notification_type, 3000)

        # Cancel previous dismiss timer
        if self._notification_timer:
            self._notification_timer.deactivate()

        self._notification_timer = ui.timer(
            dismiss_ms / 1000.0, self._dismiss_notification, once=True
        )

    def _dismiss_notification(self) -> None:
        """Hide the notification container."""
        if self._notification_container:
            self._notification_container.classes(add="hidden")
            self._notification_container.clear()
        self._notification_timer = None

    def _show_round_summary(self, state: GameStateSnapshot) -> None:
        """Display round-end summary with all cards revealed and scores."""
        summary = state.round_summary

        if self._status_label:
            self._status_label.set_text(f"Round {summary.round_number + 1} Complete!")
            self._status_label.classes(replace="text-xl font-bold text-green-400")

        if self._round_label:
            if summary.kabo_caller:
                result = "Successful!" if summary.kabo_successful else "Failed!"
                self._round_label.set_text(
                    f"KABO by {summary.kabo_caller}: {result}"
                )
            else:
                self._round_label.set_text("Deck depleted")

        # Show all players' revealed hands (opponents section)
        if self._opponents_container:
            self._opponents_container.clear()
            with self._opponents_container:
                for pv in state.players:
                    if not pv.is_current_player:
                        self._render_opponent_hand(pv)

        # Show center area with round scores
        if self._center_container:
            self._center_container.clear()
            with self._center_container:
                with ui.card().classes("p-4"):
                    ui.label("Round Scores").classes(
                        "text-lg font-bold text-yellow-300 mb-2"
                    )
                    for name, score in sorted(
                        summary.round_scores.items(), key=lambda x: x[1]
                    ):
                        game_total = summary.game_scores.get(name, 0)
                        with ui.row().classes("items-center gap-2 w-full"):
                            ui.label(name).classes("text-white font-bold w-24")
                            ui.label(f"+{score}").classes("text-yellow-300")
                            ui.label(f"(Total: {game_total})").classes(
                                "text-gray-400 text-sm"
                            )

        # Show the current player's revealed hand
        if self._player_hand_container:
            self._player_hand_container.clear()
            with self._player_hand_container:
                web_pv = next((p for p in state.players if p.is_current_player), None)
                if web_pv:
                    for card in web_pv.cards:
                        render_card(card, size="normal", label=f"#{card.position}")

        # Update scoreboard
        self.scoreboard.update(state.players)

    def _hand_id(self, player_name: str) -> str:
        """Map a player name to its DOM ID, accounting for 'self' player."""
        if self._last_state:
            for p in self._last_state.players:
                if p.is_current_player and p.name == player_name:
                    return "kabo-hand-self"
        return f"kabo-hand-{player_name}"

    def enqueue_animation(self, event: AnimationEvent) -> None:
        """Add an animation event to the queue and start playback."""
        self._animation_queue.append(event)
        if not self._animating:
            self._play_next_animation()

    def _play_next_animation(self) -> None:
        """Play the next animation in the queue."""
        if not self._animation_queue:
            self._animating = False
            if self._pending_state:
                state = self._pending_state
                self._pending_state = None
                self.update_state(state)
            return

        self._animating = True
        event = self._animation_queue.pop(0)

        handler = getattr(self, f"_anim_{event.animation_type}", None)
        if handler:
            handler(event)
        else:
            # Unknown animation type, skip
            ui.timer(0.1, self._play_next_animation, once=True)

    def _anim_draw_deck(self, event: AnimationEvent) -> None:
        hand_id = self._hand_id(event.player_name)
        ui.run_javascript(
            f'kaboAnimations.showDrawAnimation("kabo-deck", "{hand_id}", {event.duration_ms})'
        )
        ui.timer(event.duration_ms / 1000.0, self._play_next_animation, once=True)

    def _anim_draw_discard(self, event: AnimationEvent) -> None:
        hand_id = self._hand_id(event.player_name)
        ui.run_javascript(
            f'kaboAnimations.showDrawAnimation("kabo-discard", "{hand_id}", {event.duration_ms})'
        )
        ui.timer(event.duration_ms / 1000.0, self._play_next_animation, once=True)

    def _anim_exchange(self, event: AnimationEvent) -> None:
        hand_id = self._hand_id(event.player_name)
        ui.run_javascript(
            f'kaboAnimations.showDrawAnimation("{hand_id}", "kabo-discard", {event.duration_ms})'
        )
        ui.timer(event.duration_ms / 1000.0, self._play_next_animation, once=True)

    def _anim_discard(self, event: AnimationEvent) -> None:
        ui.run_javascript(
            f'kaboAnimations.showDrawAnimation("kabo-center", "kabo-discard", {event.duration_ms})'
        )
        ui.timer(event.duration_ms / 1000.0, self._play_next_animation, once=True)

    def _anim_peek(self, event: AnimationEvent) -> None:
        hand_id = self._hand_id(event.player_name)
        pos = event.card_positions[0] if event.card_positions else 0
        ui.run_javascript(
            f'kaboAnimations.showEffectIcon("\\ud83d\\udc41", "PEEK", "{hand_id}", {pos}, {event.duration_ms})'
        )
        ui.timer(event.duration_ms / 1000.0, self._play_next_animation, once=True)

    def _anim_spy(self, event: AnimationEvent) -> None:
        spy_hand_id = self._hand_id(event.player_name)
        target_hand_id = self._hand_id(event.target_player_name)
        pos = event.target_positions[0] if event.target_positions else 0
        ui.run_javascript(
            f'kaboAnimations.showEffectIcon("\\ud83d\\udd75", "SPY: {event.player_name} \\u2192 {event.target_player_name}", "{target_hand_id}", {pos}, {event.duration_ms})'
        )
        ui.run_javascript(
            f'kaboAnimations.showSpyLine("{spy_hand_id}", "{target_hand_id}", {pos}, {event.duration_ms})'
        )
        ui.timer(event.duration_ms / 1000.0, self._play_next_animation, once=True)

    def _anim_swap(self, event: AnimationEvent) -> None:
        hand1_id = self._hand_id(event.player_name)
        hand2_id = self._hand_id(event.target_player_name)
        pos1 = event.card_positions[0] if event.card_positions else 0
        pos2 = event.target_positions[0] if event.target_positions else 0
        ui.run_javascript(
            f'kaboAnimations.showEffectIcon("\\ud83d\\udd04", "SWAP", "kabo-center", 0, {event.duration_ms})'
        )
        ui.run_javascript(
            f'kaboAnimations.showSwapArrows("{hand1_id}", {pos1}, "{hand2_id}", {pos2}, {event.duration_ms})'
        )
        ui.timer(event.duration_ms / 1000.0, self._play_next_animation, once=True)

    def _anim_kabo_call(self, event: AnimationEvent) -> None:
        ui.run_javascript(
            f'kaboAnimations.showKaboCall("{event.player_name}", {event.duration_ms})'
        )
        ui.timer(event.duration_ms / 1000.0, self._play_next_animation, once=True)

    def show_game_over(self, state: GameStateSnapshot) -> None:
        """Show game over screen."""
        if self._status_label:
            self._status_label.set_text("Game Over!")
            self._status_label.classes(replace="text-2xl font-bold text-green-400")

        if self.action_panel._container:
            self.action_panel._container.clear()
            with self.action_panel._container:
                ui.label("Game Over!").classes("text-xl font-bold text-white")
                # Show final scores
                sorted_players = sorted(state.players, key=lambda p: p.game_score)
                for i, p in enumerate(sorted_players):
                    medal = ["🥇", "🥈", "🥉"]
                    prefix = medal[i] if i < 3 else f"{i+1}."
                    ui.label(f"{prefix} {p.name}: {p.game_score} points").classes(
                        "text-lg text-white"
                    )
                def play_again():
                    app.storage.user.pop("room_code", None)
                    app.storage.user.pop("player_name", None)
                    ui.navigate.to("/")

                ui.button("Play Again", on_click=play_again).props(
                    "color=positive size=lg"
                ).classes("mt-4")
