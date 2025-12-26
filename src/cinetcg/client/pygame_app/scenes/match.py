from __future__ import annotations

import pygame  # type: ignore[import-not-found]

from cinetcg.engine.actions import AttackAction, EndTurnAction, PlayCardAction, TargetRef
from cinetcg.engine.ai import AISpec, ai_take_turn
from cinetcg.engine.match import MatchState, get_valid_attack_targets, get_valid_targets_for_play, step

from ..app import GameContext
from ..cutscene_player import CutscenePlayer
from ..scene_base import Scene, SceneTransition
from ..ui import Button, draw_text


class MatchScene:
    def __init__(self, ctx: GameContext, match_state: MatchState, ai_spec: AISpec, player_deck_id: str) -> None:
        self.ctx = ctx
        self.state = match_state
        self.ai_spec = ai_spec
        self.player_deck_id = player_deck_id

        self._next: SceneTransition | None = None
        self._message: str = ""
        self._pending_target_for_card: tuple[int, str] | None = None  # (hand_index, card_id)
        self._pending_attacker_slot: int | None = None

        self._cutscene: CutscenePlayer | None = None
        self._queued_cutscenes: list[tuple[str, str]] = []  # (cutscene_id, card_id)

        self._did_apply_rewards = False
        self._reward_summary: dict[str, int] | None = None

        self.btn_end = Button(rect=pygame.Rect(860, 660, 140, 50), text="End Turn", on_click=self._on_end_turn)
        self.btn_menu = Button(rect=pygame.Rect(860, 20, 140, 40), text="Menu", on_click=self._on_menu)

        self.btn_continue = Button(
            rect=pygame.Rect(360, 420, 300, 56),
            text="Continue",
            on_click=self._on_continue,
        )
        self.btn_shop = Button(
            rect=pygame.Rect(360, 490, 300, 56),
            text="Go to Shop",
            on_click=self._on_go_shop,
        )

        # Ensure player 0 is local player
        if self.state.current_player == 1:
            # AI started; take its turn immediately (rare; but safe)
            self._run_ai_turn()

    def _go(self, scene: Scene) -> None:
        self._next = SceneTransition(scene)

    def _on_menu(self) -> None:
        from .main_menu import MainMenuScene

        self._go(MainMenuScene(self.ctx))


    def _on_continue(self) -> None:
        from .main_menu import MainMenuScene

        self._go(MainMenuScene(self.ctx))

    def _on_go_shop(self) -> None:
        from .shop import ShopScene

        self._go(ShopScene(self.ctx))

    def _rarity_triggers_cutscene(self, rarity: str) -> bool:
        inv = self.ctx.inventory
        always = inv.profile.settings.always_show_cutscenes if inv is not None else False
        if always:
            return True
        return rarity in ("epic", "legendary")

    def _maybe_queue_cutscene(self, card_id: str) -> None:
        if self.ctx.cards is None or self.ctx.cutscenes is None:
            return
        card = self.ctx.cards.cards.get(card_id)
        if card is None:
            return
        if card.cutscene_id is None:
            return
        if not self._rarity_triggers_cutscene(card.rarity):
            return
        cs_id = card.cutscene_id
        if cs_id not in self.ctx.cutscenes.cutscenes:
            return
        self._queued_cutscenes.append((cs_id, card_id))

    def _start_next_cutscene_if_needed(self) -> None:
        if self._cutscene is not None:
            return
        if not self._queued_cutscenes:
            return
        cs_id, card_id = self._queued_cutscenes.pop(0)
        assert self.ctx.cutscenes is not None and self.ctx.cards is not None
        cfg = self.ctx.cutscenes.cutscenes[cs_id]
        card = self.ctx.cards.cards[card_id]
        art = self.ctx.assets.get_image(card.art_path, size=(256, 356))
        self._cutscene = CutscenePlayer(self.ctx.assets, config=cfg, card_art=art, cutscene_id=cs_id)

    def _on_end_turn(self) -> None:
        if self.state.winner is not None:
            return
        if self._cutscene is not None:
            return
        if self.state.current_player != 0:
            return
        res = step(self.state, EndTurnAction(player=0))
        if not res.ok and res.error:
            self._message = res.error
            return
        self._message = ""
        # AI turn
        self._run_ai_turn()

    def _run_ai_turn(self) -> None:
        if self.state.winner is not None:
            return
        if self.state.current_player != 1:
            return
        before = len(self.state.event_log)
        ai_take_turn(self.state, player=1, spec=self.ai_spec)
        after_events = self.state.event_log[before:]
        for ev in after_events:
            if ev.get("type") == "CARD_PLAYED":
                card_id = str(ev.get("card_id", ""))
                self._maybe_queue_cutscene(card_id)

    def handle_event(self, event: pygame.event.Event) -> None:
        if self._cutscene is not None:
            self._cutscene.handle_event(event)
            return

        if self.state.winner is not None:
            self.btn_continue.handle_event(event)
            self.btn_shop.handle_event(event)
            self.btn_menu.handle_event(event)
            return

        self.btn_end.handle_event(event)
        self.btn_menu.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_click(event.pos)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            # cancel targeting
            self._pending_target_for_card = None
            self._pending_attacker_slot = None

    def _handle_click(self, pos: tuple[int, int]) -> None:
        if self.state.current_player != 0:
            return

        # If selecting a target for spell or attack, resolve it
        if self._pending_target_for_card is not None:
            hand_index, card_id = self._pending_target_for_card
            target = self._hit_test_target(pos)
            if target is None:
                return
            res = step(self.state, PlayCardAction(player=0, hand_index=hand_index, target=target))
            if res.ok:
                self._maybe_queue_cutscene(card_id)
                self._pending_target_for_card = None
                self._message = ""
            else:
                self._message = res.error or "Invalid action."
            return

        if self._pending_attacker_slot is not None:
            target = self._hit_test_target(pos)
            if target is None:
                return
            res = step(
                self.state,
                AttackAction(player=0, attacker_slot=self._pending_attacker_slot, target=target),
            )
            if res.ok:
                self._pending_attacker_slot = None
                self._message = ""
            else:
                self._message = res.error or "Invalid action."
            return

        # Otherwise: click hand to play, or board to attack
        hit_hand = self._hit_test_hand(pos)
        if hit_hand is not None:
            hand_index, card_id = hit_hand
            targets = get_valid_targets_for_play(self.state, 0, card_id)
            if targets:
                self._pending_target_for_card = (hand_index, card_id)
                self._message = "Choose target..."
                return
            res = step(self.state, PlayCardAction(player=0, hand_index=hand_index, target=None))
            if res.ok:
                self._maybe_queue_cutscene(card_id)
                self._message = ""
            else:
                self._message = res.error or "Invalid action."
            return

        hit_creature = self._hit_test_player_board(pos)
        if hit_creature is not None:
            slot = hit_creature
            # only if can attack
            c = self.state.players[0].board[slot]
            if c is None:
                return
            if c.summoning_sick or c.has_attacked:
                self._message = "Creature can't attack yet."
                return
            self._pending_attacker_slot = slot
            self._message = "Choose attack target..."
            return

    def _hit_test_hand(self, pos: tuple[int, int]) -> tuple[int, str] | None:
        ps = self.state.players[0]
        x0, y0 = 40, 560
        w, h = 140, 64
        for i, cid in enumerate(ps.hand):
            rect = pygame.Rect(x0 + i * (w + 8), y0, w, h)
            if rect.collidepoint(pos):
                return i, cid
        return None

    def _slot_rect(self, player: int, slot: int) -> pygame.Rect:
        x0 = 220
        y0 = 120 if player == 1 else 380
        w, h = 150, 90
        return pygame.Rect(x0 + slot * (w + 10), y0, w, h)

    def _player_rect(self, player: int) -> pygame.Rect:
        # health panel
        if player == 1:
            return pygame.Rect(40, 60, 160, 60)
        return pygame.Rect(40, 640, 160, 60)

    def _hit_test_player_board(self, pos: tuple[int, int]) -> int | None:
        for slot in range(5):
            if self._slot_rect(0, slot).collidepoint(pos):
                return slot
        return None

    def _hit_test_target(self, pos: tuple[int, int]) -> TargetRef | None:
        # both players, board slots and player panel
        for p in (0, 1):
            if self._player_rect(p).collidepoint(pos):
                return TargetRef.player_target(p)
            for slot in range(5):
                if self._slot_rect(p, slot).collidepoint(pos):
                    return TargetRef.creature_target(p, slot)
        return None

    def update(self, dt: float) -> SceneTransition | None:
        # Cutscene queue
        if self._cutscene is not None:
            self._cutscene.update(dt)
            if self._cutscene.done:
                self._cutscene = None
        self._start_next_cutscene_if_needed()

        # When match ends, apply rewards once
        if self.state.winner is not None and not self._did_apply_rewards:
            inv = self.ctx.inventory
            if inv is not None:
                won = self.state.winner == 0
                self._reward_summary = inv.apply_match_result(won=won)
                self._did_apply_rewards = True

        return self._next

    def render(self, screen: pygame.Surface) -> None:
        screen.fill((8, 10, 14))
        fonts = self.ctx.assets.fonts
        inv = self.ctx.inventory

        # header / controls
        self.btn_menu.draw(screen, fonts.ui)
        self.btn_end.enabled = self.state.current_player == 0 and self._cutscene is None and self.state.winner is None
        self.btn_end.draw(screen, fonts.ui)

        # player panels
        self._draw_player_panel(screen, player=1, y=20)
        self._draw_player_panel(screen, player=0, y=600)

        # boards
        self._draw_board(screen, player=1)
        self._draw_board(screen, player=0)

        # hand
        self._draw_hand(screen)

        # targeting overlays
        if self._pending_target_for_card is not None:
            hand_index, card_id = self._pending_target_for_card
            valid = get_valid_targets_for_play(self.state, 0, card_id)
            self._draw_target_highlights(screen, valid)
        if self._pending_attacker_slot is not None:
            valid = get_valid_attack_targets(self.state, 0)
            self._draw_target_highlights(screen, valid)

        # messages
        if self._message:
            draw_text(screen, fonts.ui, self._message, (40, 520), color=(240, 200, 120))

        # game over overlay
        if self.state.winner is not None:
            self._draw_game_over(screen)

        # cutscene overlay
        if self._cutscene is not None:
            self._cutscene.render(screen)

    def _draw_player_panel(self, screen: pygame.Surface, player: int, y: int) -> None:
        ps = self.state.players[player]
        rect = self._player_rect(player)
        pygame.draw.rect(screen, (24, 24, 32), rect, border_radius=10)
        pygame.draw.rect(screen, (0, 0, 0), rect, width=2, border_radius=10)
        draw_text(screen, self.ctx.assets.fonts.ui, f"P{player+1} HP: {ps.health}", (rect.x + 10, rect.y + 8))
        draw_text(
            screen,
            self.ctx.assets.fonts.small,
            f"Energy: {ps.energy}/{ps.energy_max}",
            (rect.x + 10, rect.y + 34),
        )

    def _draw_board(self, screen: pygame.Surface, player: int) -> None:
        ps = self.state.players[player]
        for slot in range(5):
            rect = self._slot_rect(player, slot)
            pygame.draw.rect(screen, (18, 18, 24), rect, border_radius=8)
            pygame.draw.rect(screen, (0, 0, 0), rect, width=2, border_radius=8)
            c = ps.board[slot]
            if c is None:
                draw_text(screen, self.ctx.assets.fonts.small, "(empty)", (rect.x + 10, rect.y + 34), color=(120, 120, 140))
                continue
            draw_text(screen, self.ctx.assets.fonts.small, c.card_id, (rect.x + 8, rect.y + 8))
            draw_text(
                screen,
                self.ctx.assets.fonts.small,
                f"{c.attack}/{c.health}",
                (rect.x + 8, rect.y + 32),
                color=(240, 240, 240),
            )
            kw = ", ".join(sorted(list(c.keywords)))
            if kw:
                draw_text(screen, self.ctx.assets.fonts.small, kw, (rect.x + 8, rect.y + 56), color=(180, 180, 220))

            # Summoning sickness indicator
            if player == 0 and c.summoning_sick:
                draw_text(screen, self.ctx.assets.fonts.small, "SICK", (rect.right - 48, rect.y + 32), color=(240, 120, 120))
            if player == 0 and c.has_attacked:
                draw_text(screen, self.ctx.assets.fonts.small, "DONE", (rect.right - 52, rect.y + 56), color=(160, 160, 160))

    def _draw_hand(self, screen: pygame.Surface) -> None:
        ps = self.state.players[0]
        x0, y0 = 40, 560
        w, h = 140, 64
        for i, cid in enumerate(ps.hand[:6]):  # limit for UI readability
            rect = pygame.Rect(x0 + i * (w + 8), y0, w, h)
            pygame.draw.rect(screen, (28, 28, 40), rect, border_radius=8)
            pygame.draw.rect(screen, (0, 0, 0), rect, width=2, border_radius=8)
            if self.ctx.cards is not None and cid in self.ctx.cards.cards:
                card = self.ctx.cards.cards[cid]
                draw_text(screen, self.ctx.assets.fonts.small, f"{card.name}", (rect.x + 6, rect.y + 8))
                draw_text(screen, self.ctx.assets.fonts.small, f"Cost {card.cost}", (rect.x + 6, rect.y + 34))
            else:
                draw_text(screen, self.ctx.assets.fonts.small, cid, (rect.x + 6, rect.y + 8))

    def _draw_target_highlights(self, screen: pygame.Surface, targets: list[TargetRef]) -> None:
        for t in targets:
            if t.kind == "player":
                rect = self._player_rect(t.player)
            else:
                if t.slot is None:
                    continue
                rect = self._slot_rect(t.player, t.slot)
            pygame.draw.rect(screen, (240, 240, 120), rect, width=3, border_radius=8)

    def _draw_game_over(self, screen: pygame.Surface) -> None:
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))

        winner = self.state.winner
        title = "YOU WIN!" if winner == 0 else "YOU LOSE"
        draw_text(screen, self.ctx.assets.fonts.big, title, (360, 320), color=(240, 240, 240))

        if self._reward_summary is not None:
            gold = self._reward_summary.get("gold", 0)
            delta = self._reward_summary.get("rating_delta", 0)
            draw_text(
                screen,
                self.ctx.assets.fonts.ui,
                f"Rewards: +{gold} gold   Rating {delta:+d}",
                (340, 370),
                color=(240, 240, 240),
            )

        self.btn_continue.draw(screen, self.ctx.assets.fonts.ui)
        self.btn_shop.draw(screen, self.ctx.assets.fonts.ui)
