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
            _getCardRect(handId, posIdx) {
                const el = document.getElementById(handId);
                if (!el) return null;
                const cards = el.querySelectorAll('[class*="rounded-lg"]');
                if (cards.length > posIdx && posIdx >= 0) {
                    return cards[posIdx].getBoundingClientRect();
                }
                return el.getBoundingClientRect();
            },
            _getElRect(id) {
                const el = document.getElementById(id);
                return el ? el.getBoundingClientRect() : null;
            },
            _createCardEl(x, y, w, h, faceUp, cardValue) {
                const card = document.createElement('div');
                const bg = faceUp ? '#1a237e' : '#263238';
                const border = faceUp ? '#42a5f5' : '#90a4ae';
                const content = faceUp && cardValue != null ? cardValue : '?';
                const textColor = faceUp ? '#fff' : '#90a4ae';
                const fontSize = faceUp ? Math.max(14, h * 0.35) : Math.max(12, h * 0.3);
                card.style.cssText = `position:absolute;left:${x}px;top:${y}px;width:${w}px;height:${h}px;background:${bg};border:2px solid ${border};border-radius:8px;display:flex;align-items:center;justify-content:center;color:${textColor};font-weight:bold;font-size:${fontSize}px;z-index:10000;box-shadow:0 4px 16px rgba(0,0,0,0.6);pointer-events:none;`;
                card.textContent = content;
                return card;
            },
            _createIcon(emoji, x, y, size) {
                const el = document.createElement('div');
                el.style.cssText = `position:absolute;left:${x}px;top:${y}px;font-size:${size}px;transform:translate(-50%,-50%) scale(0);transition:transform 0.3s ease-out, opacity 0.3s;opacity:0;z-index:10000;filter:drop-shadow(0 0 10px rgba(255,255,255,0.5));`;
                el.textContent = emoji;
                return el;
            },
            _createLabel(text, x, y) {
                const lbl = document.createElement('div');
                lbl.style.cssText = `position:absolute;left:${x}px;top:${y}px;transform:translate(-50%,0) scale(0);transition:transform 0.3s ease-out, opacity 0.3s;opacity:0;font-size:14px;font-weight:bold;color:white;text-shadow:0 0 8px rgba(0,0,0,0.8);white-space:nowrap;z-index:10000;`;
                lbl.textContent = text;
                return lbl;
            },

            showDrawAnimation(fromId, toId, cardValue, durationMs) {
                const ov = this._createOverlay();
                const fr = this._getElRect(fromId);
                const tr = this._getElRect(toId);
                if (!fr || !tr) return;
                const cw = 56, ch = 76;
                const sx = fr.left + fr.width/2 - cw/2;
                const sy = fr.top + fr.height/2 - ch/2;
                const ex = tr.left + tr.width/2 - cw/2;
                const ey = tr.top + tr.height/2 - ch/2;
                const faceUp = cardValue != null;
                const card = this._createCardEl(sx, sy, cw, ch, faceUp, cardValue);
                card.style.transition = 'none';
                card.style.transform = 'scale(0.5)';
                card.style.opacity = '0';
                ov.appendChild(card);
                // Trail glow
                const trail = document.createElement('div');
                trail.style.cssText = `position:absolute;left:${sx}px;top:${sy}px;width:${cw}px;height:${ch}px;border-radius:8px;background:transparent;box-shadow:0 0 20px rgba(251,191,36,0.6);z-index:9999;transition:none;opacity:0;pointer-events:none;`;
                ov.appendChild(trail);
                const travelTime = durationMs * 0.65;
                requestAnimationFrame(() => {
                    card.style.transition = `left ${travelTime}ms cubic-bezier(0.25,0.1,0.25,1), top ${travelTime}ms cubic-bezier(0.25,0.1,0.25,1), transform ${travelTime}ms ease, opacity 0.2s ease`;
                    trail.style.transition = `left ${travelTime}ms cubic-bezier(0.25,0.1,0.25,1), top ${travelTime}ms cubic-bezier(0.25,0.1,0.25,1), opacity 0.3s ease`;
                    card.style.opacity = '1';
                    card.style.transform = 'scale(1.15)';
                    trail.style.opacity = '0.7';
                    // Move along slight arc using intermediate position
                    const mx = (sx + ex) / 2;
                    const my = Math.min(sy, ey) - 30;
                    card.style.left = mx + 'px';
                    card.style.top = my + 'px';
                    trail.style.left = mx + 'px';
                    trail.style.top = my + 'px';
                    setTimeout(() => {
                        card.style.transition = `left ${travelTime*0.5}ms ease-in-out, top ${travelTime*0.5}ms ease-in-out, transform ${travelTime*0.5}ms ease, opacity 0.3s ease`;
                        card.style.left = ex + 'px';
                        card.style.top = ey + 'px';
                        card.style.transform = 'scale(1.0)';
                        trail.style.left = ex + 'px';
                        trail.style.top = ey + 'px';
                    }, travelTime * 0.55);
                });
                setTimeout(() => {
                    card.style.opacity = '0';
                    card.style.transform = 'scale(0.8)';
                    trail.style.opacity = '0';
                    setTimeout(() => { card.remove(); trail.remove(); }, 400);
                }, durationMs - 400);
            },

            showPeekFlip(handId, posIdx, cardValue, durationMs) {
                const ov = this._createOverlay();
                const rect = this._getCardRect(handId, posIdx);
                if (!rect) return;
                const cx = rect.left + rect.width/2;
                const cy = rect.top + rect.height/2;
                const cw = rect.width || 56;
                const ch = rect.height || 76;
                // Create overlay card at exact card position
                const card = document.createElement('div');
                card.style.cssText = `position:absolute;left:${rect.left}px;top:${rect.top}px;width:${cw}px;height:${ch}px;background:#263238;border:2px solid #90a4ae;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#90a4ae;font-weight:bold;font-size:${Math.max(14, ch*0.35)}px;z-index:10000;pointer-events:none;transform-style:preserve-3d;perspective:400px;`;
                card.textContent = '?';
                ov.appendChild(card);
                // Eye icon above
                const icon = this._createIcon('\\ud83d\\udc41', cx, cy - ch/2 - 30, 36);
                ov.appendChild(icon);
                const lbl = this._createLabel('PEEK', cx, cy - ch/2 - 8);
                ov.appendChild(lbl);
                const flipTime = durationMs * 0.15;
                const holdTime = durationMs * 0.45;
                // Phase 1: lift up
                card.style.transition = `transform ${flipTime}ms ease-out, top ${flipTime}ms ease-out`;
                requestAnimationFrame(() => {
                    card.style.top = (rect.top - 25) + 'px';
                    card.style.transform = 'rotateY(0deg)';
                });
                // Phase 2: flip to reveal
                setTimeout(() => {
                    card.style.transition = `transform ${flipTime}ms ease-in`;
                    card.style.transform = 'rotateY(90deg)';
                }, flipTime);
                // Phase 3: change face and flip back
                setTimeout(() => {
                    card.style.background = '#1a237e';
                    card.style.borderColor = '#42a5f5';
                    card.style.color = '#fff';
                    card.textContent = cardValue != null ? cardValue : '?';
                    card.style.transition = `transform ${flipTime}ms ease-out`;
                    card.style.transform = 'rotateY(0deg)';
                    // Show icon
                    icon.style.transform = 'translate(-50%,-50%) scale(1)';
                    icon.style.opacity = '1';
                    lbl.style.transform = 'translate(-50%,0) scale(1)';
                    lbl.style.opacity = '1';
                }, flipTime * 2);
                // Phase 4: hold, then flip back to face-down
                setTimeout(() => {
                    card.style.transition = `transform ${flipTime}ms ease-in`;
                    card.style.transform = 'rotateY(90deg)';
                }, flipTime * 2 + holdTime);
                setTimeout(() => {
                    card.style.background = '#263238';
                    card.style.borderColor = '#90a4ae';
                    card.style.color = '#90a4ae';
                    card.textContent = '?';
                    card.style.transition = `transform ${flipTime}ms ease-out, top ${flipTime}ms ease-out, opacity 0.3s ease`;
                    card.style.transform = 'rotateY(0deg)';
                    card.style.top = rect.top + 'px';
                    icon.style.transform = 'translate(-50%,-50%) scale(0)';
                    icon.style.opacity = '0';
                    lbl.style.transform = 'translate(-50%,0) scale(0)';
                    lbl.style.opacity = '0';
                }, flipTime * 3 + holdTime);
                // Cleanup
                setTimeout(() => {
                    card.style.opacity = '0';
                    setTimeout(() => { card.remove(); icon.remove(); lbl.remove(); }, 400);
                }, durationMs - 400);
            },

            showSpyReveal(fromHandId, toHandId, posIdx, cardValue, durationMs) {
                const ov = this._createOverlay();
                const fromRect = this._getElRect(fromHandId);
                const toRect = this._getCardRect(toHandId, posIdx);
                if (!fromRect || !toRect) return;
                const fx = fromRect.left + fromRect.width/2;
                const fy = fromRect.top + fromRect.height/2;
                const tx = toRect.left + toRect.width/2;
                const ty = toRect.top + toRect.height/2;
                const cw = toRect.width || 56;
                const ch = toRect.height || 76;
                // Detective icon traveling from spy to target
                const detective = this._createIcon('\\ud83d\\udd75', fx, fy, 40);
                ov.appendChild(detective);
                requestAnimationFrame(() => {
                    detective.style.transform = 'translate(-50%,-50%) scale(1)';
                    detective.style.opacity = '1';
                });
                const travelTime = durationMs * 0.25;
                setTimeout(() => {
                    detective.style.transition = `left ${travelTime}ms ease-in-out, top ${travelTime}ms ease-in-out`;
                    detective.style.left = tx + 'px';
                    detective.style.top = (ty - ch/2 - 30) + 'px';
                }, 200);
                // Golden dashed line
                const svg = document.createElementNS('http://www.w3.org/2000/svg','svg');
                svg.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;';
                const line = document.createElementNS('http://www.w3.org/2000/svg','line');
                line.setAttribute('x1',fx); line.setAttribute('y1',fy);
                line.setAttribute('x2',fx); line.setAttribute('y2',fy);
                line.setAttribute('stroke','#fbbf24'); line.setAttribute('stroke-width','2');
                line.setAttribute('stroke-dasharray','8,4'); line.setAttribute('opacity','0.6');
                line.style.transition = `all ${travelTime}ms ease-out`;
                svg.appendChild(line);
                ov.appendChild(svg);
                setTimeout(() => {
                    line.setAttribute('x2', tx);
                    line.setAttribute('y2', ty);
                }, 200);
                // SPY label
                const lbl = this._createLabel('SPY', tx, ty - ch/2 - 8);
                ov.appendChild(lbl);
                // Card flip reveal at target position (after detective arrives)
                const arrivalTime = 200 + travelTime;
                const flipTime = durationMs * 0.1;
                const holdTime = durationMs * 0.3;
                setTimeout(() => {
                    // Create overlay card
                    const card = document.createElement('div');
                    card.style.cssText = `position:absolute;left:${toRect.left}px;top:${toRect.top}px;width:${cw}px;height:${ch}px;background:#263238;border:2px solid #90a4ae;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#90a4ae;font-weight:bold;font-size:${Math.max(14, ch*0.35)}px;z-index:10000;pointer-events:none;`;
                    card.textContent = '?';
                    ov.appendChild(card);
                    // Lift and flip
                    card.style.transition = `transform ${flipTime}ms ease-out, top ${flipTime}ms ease-out`;
                    card.style.top = (toRect.top - 20) + 'px';
                    lbl.style.transform = 'translate(-50%,0) scale(1)';
                    lbl.style.opacity = '1';
                    setTimeout(() => {
                        card.style.transition = `transform ${flipTime}ms ease-in`;
                        card.style.transform = 'rotateY(90deg)';
                    }, flipTime);
                    setTimeout(() => {
                        card.style.background = '#1a237e';
                        card.style.borderColor = '#42a5f5';
                        card.style.color = '#fff';
                        card.textContent = cardValue != null ? cardValue : '?';
                        card.style.transition = `transform ${flipTime}ms ease-out`;
                        card.style.transform = 'rotateY(0deg)';
                    }, flipTime * 2);
                    // Hold then flip back
                    setTimeout(() => {
                        card.style.transition = `transform ${flipTime}ms ease-in`;
                        card.style.transform = 'rotateY(90deg)';
                    }, flipTime * 2 + holdTime);
                    setTimeout(() => {
                        card.style.background = '#263238';
                        card.style.borderColor = '#90a4ae';
                        card.style.color = '#90a4ae';
                        card.textContent = '?';
                        card.style.transition = `transform ${flipTime}ms ease-out, top ${flipTime}ms ease-out, opacity 0.3s`;
                        card.style.transform = 'rotateY(0deg)';
                        card.style.top = toRect.top + 'px';
                    }, flipTime * 3 + holdTime);
                    setTimeout(() => {
                        card.style.opacity = '0';
                        setTimeout(() => card.remove(), 300);
                    }, flipTime * 4 + holdTime);
                }, arrivalTime);
                // Cleanup all
                setTimeout(() => {
                    detective.style.opacity = '0';
                    lbl.style.opacity = '0';
                    svg.style.opacity = '0';
                    setTimeout(() => { detective.remove(); lbl.remove(); svg.remove(); }, 400);
                }, durationMs - 400);
            },

            showSwapCards(hand1Id, pos1, hand2Id, pos2, durationMs) {
                const ov = this._createOverlay();
                const r1 = this._getCardRect(hand1Id, pos1);
                const r2 = this._getCardRect(hand2Id, pos2);
                if (!r1 || !r2) return;
                const cw = 56, ch = 76;
                const x1 = r1.left + r1.width/2 - cw/2;
                const y1 = r1.top + r1.height/2 - ch/2;
                const x2 = r2.left + r2.width/2 - cw/2;
                const y2 = r2.top + r2.height/2 - ch/2;
                const card1 = this._createCardEl(x1, y1, cw, ch, false, null);
                const card2 = this._createCardEl(x2, y2, cw, ch, false, null);
                card1.style.borderColor = '#fbbf24';
                card2.style.borderColor = '#fbbf24';
                ov.appendChild(card1);
                ov.appendChild(card2);
                // Swap icon at midpoint
                const mx = (r1.left + r1.width/2 + r2.left + r2.width/2) / 2;
                const my = (r1.top + r1.height/2 + r2.top + r2.height/2) / 2;
                const icon = this._createIcon('\\ud83d\\udd04', mx, my, 36);
                ov.appendChild(icon);
                const travelTime = durationMs * 0.6;
                // Arc offset for crossing
                const arcOffset = 40;
                const dx = x2 - x1;
                const dy = y2 - y1;
                const len = Math.sqrt(dx*dx + dy*dy) || 1;
                const nx = -dy/len * arcOffset;
                const ny = dx/len * arcOffset;
                requestAnimationFrame(() => {
                    card1.style.transition = `left ${travelTime}ms cubic-bezier(0.4,0,0.2,1), top ${travelTime}ms cubic-bezier(0.4,0,0.2,1), box-shadow ${travelTime}ms ease`;
                    card2.style.transition = `left ${travelTime}ms cubic-bezier(0.4,0,0.2,1), top ${travelTime}ms cubic-bezier(0.4,0,0.2,1), box-shadow ${travelTime}ms ease`;
                    card1.style.boxShadow = '0 0 20px rgba(251,191,36,0.6)';
                    card2.style.boxShadow = '0 0 20px rgba(251,191,36,0.6)';
                    card1.style.left = x2 + 'px';
                    card1.style.top = y2 + 'px';
                    card2.style.left = x1 + 'px';
                    card2.style.top = y1 + 'px';
                });
                // Show swap icon at midpoint
                setTimeout(() => {
                    icon.style.transform = 'translate(-50%,-50%) scale(1.2)';
                    icon.style.opacity = '1';
                }, travelTime * 0.3);
                setTimeout(() => {
                    icon.style.transform = 'translate(-50%,-50%) scale(0)';
                    icon.style.opacity = '0';
                }, travelTime * 0.7);
                // Fade out at destination
                setTimeout(() => {
                    card1.style.opacity = '0';
                    card2.style.opacity = '0';
                    setTimeout(() => { card1.remove(); card2.remove(); icon.remove(); }, 400);
                }, durationMs - 400);
            },

            showExchangeToDiscard(handId, posIdx, durationMs) {
                const ov = this._createOverlay();
                const cardRect = this._getCardRect(handId, posIdx);
                const discardRect = this._getElRect('kabo-discard');
                if (!cardRect) return;
                const targetRect = discardRect || this._getElRect('kabo-center');
                if (!targetRect) return;
                const cw = 56, ch = 76;
                const sx = cardRect.left + cardRect.width/2 - cw/2;
                const sy = cardRect.top + cardRect.height/2 - ch/2;
                const ex = targetRect.left + targetRect.width/2 - cw/2;
                const ey = targetRect.top + targetRect.height/2 - ch/2;
                const card = this._createCardEl(sx, sy, cw, ch, false, null);
                card.style.transition = 'none';
                ov.appendChild(card);
                const travelTime = durationMs * 0.7;
                requestAnimationFrame(() => {
                    card.style.transition = `left ${travelTime}ms ease-in-out, top ${travelTime}ms ease-in-out, transform ${travelTime}ms ease-in-out, opacity 0.3s ease`;
                    card.style.left = ex + 'px';
                    card.style.top = ey + 'px';
                    card.style.transform = 'rotate(15deg)';
                });
                setTimeout(() => {
                    card.style.opacity = '0';
                    card.style.transform = 'rotate(15deg) scale(0.7)';
                    setTimeout(() => card.remove(), 400);
                }, durationMs - 400);
            },

            showDiscardCard(cardValue, durationMs) {
                const ov = this._createOverlay();
                const centerRect = this._getElRect('kabo-center');
                const discardRect = this._getElRect('kabo-discard');
                if (!centerRect) return;
                const targetRect = discardRect || centerRect;
                const cw = 56, ch = 76;
                const sx = centerRect.left + centerRect.width/2 - cw/2;
                const sy = centerRect.top + centerRect.height/2 - ch/2 - 20;
                const ex = targetRect.left + targetRect.width/2 - cw/2;
                const ey = targetRect.top + targetRect.height/2 - ch/2;
                const card = this._createCardEl(sx, sy, cw, ch, true, cardValue);
                card.style.transition = 'none';
                card.style.transform = 'scale(1.2)';
                ov.appendChild(card);
                const travelTime = durationMs * 0.6;
                requestAnimationFrame(() => {
                    card.style.transition = `left ${travelTime}ms ease-in-out, top ${travelTime}ms ease-in-out, transform ${travelTime}ms ease, opacity 0.3s ease`;
                    card.style.left = ex + 'px';
                    card.style.top = ey + 'px';
                    card.style.transform = 'scale(1.0)';
                });
                setTimeout(() => {
                    card.style.opacity = '0';
                    card.style.transform = 'scale(0.8)';
                    setTimeout(() => card.remove(), 400);
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
            f'kaboAnimations.showDrawAnimation("kabo-deck", "{hand_id}", null, {event.duration_ms})'
        )
        ui.timer(event.duration_ms / 1000.0, self._play_next_animation, once=True)

    def _anim_draw_discard(self, event: AnimationEvent) -> None:
        hand_id = self._hand_id(event.player_name)
        cv = event.card_value
        val_js = f'{cv}' if cv is not None else 'null'
        ui.run_javascript(
            f'kaboAnimations.showDrawAnimation("kabo-discard", "{hand_id}", {val_js}, {event.duration_ms})'
        )
        ui.timer(event.duration_ms / 1000.0, self._play_next_animation, once=True)

    def _anim_exchange(self, event: AnimationEvent) -> None:
        hand_id = self._hand_id(event.player_name)
        pos = event.card_positions[0] if event.card_positions else 0
        ui.run_javascript(
            f'kaboAnimations.showExchangeToDiscard("{hand_id}", {pos}, {event.duration_ms})'
        )
        ui.timer(event.duration_ms / 1000.0, self._play_next_animation, once=True)

    def _anim_discard(self, event: AnimationEvent) -> None:
        cv = event.card_value
        val_js = f'{cv}' if cv is not None else 'null'
        ui.run_javascript(
            f'kaboAnimations.showDiscardCard({val_js}, {event.duration_ms})'
        )
        ui.timer(event.duration_ms / 1000.0, self._play_next_animation, once=True)

    def _anim_peek(self, event: AnimationEvent) -> None:
        hand_id = self._hand_id(event.player_name)
        pos = event.card_positions[0] if event.card_positions else 0
        cv = event.card_value
        val_js = f'{cv}' if cv is not None else 'null'
        ui.run_javascript(
            f'kaboAnimations.showPeekFlip("{hand_id}", {pos}, {val_js}, {event.duration_ms})'
        )
        ui.timer(event.duration_ms / 1000.0, self._play_next_animation, once=True)

    def _anim_spy(self, event: AnimationEvent) -> None:
        spy_hand_id = self._hand_id(event.player_name)
        target_hand_id = self._hand_id(event.target_player_name)
        pos = event.target_positions[0] if event.target_positions else 0
        cv = event.card_value
        val_js = f'{cv}' if cv is not None else 'null'
        ui.run_javascript(
            f'kaboAnimations.showSpyReveal("{spy_hand_id}", "{target_hand_id}", {pos}, {val_js}, {event.duration_ms})'
        )
        ui.timer(event.duration_ms / 1000.0, self._play_next_animation, once=True)

    def _anim_swap(self, event: AnimationEvent) -> None:
        hand1_id = self._hand_id(event.player_name)
        hand2_id = self._hand_id(event.target_player_name)
        pos1 = event.card_positions[0] if event.card_positions else 0
        pos2 = event.target_positions[0] if event.target_positions else 0
        ui.run_javascript(
            f'kaboAnimations.showSwapCards("{hand1_id}", {pos1}, "{hand2_id}", {pos2}, {event.duration_ms})'
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
