from __future__ import annotations

import pygame  # type: ignore[import-not-found]

from cinetcg.engine.ai import AISpec
from cinetcg.engine.match import MatchConfig, new_match
from cinetcg.services.inventory import DeckEntry, SavedHand

from ..app import GameContext
from ..scene_base import Scene, SceneTransition
from ..ui import Button, TextInput, draw_text


class DecksScene:
    def __init__(self, ctx: GameContext, mode: str) -> None:
        self.ctx = ctx
        self.mode = mode  # manage | pick_for_ranked
        self._next: SceneTransition | None = None
        self.selected_index: int = 0
        self._build_ui()

    def _build_ui(self) -> None:
        self.btn_back = Button(
            rect=pygame.Rect(20, 20, 120, 40),
            text="Back",
            on_click=self._on_back,
        )
        self.btn_new = Button(rect=pygame.Rect(160, 20, 160, 40), text="New", on_click=self._on_new)
        self.btn_edit = Button(rect=pygame.Rect(340, 20, 160, 40), text="Edit", on_click=self._on_edit)
        self.btn_default = Button(
            rect=pygame.Rect(520, 20, 200, 40),
            text="Set Default",
            on_click=self._on_set_default,
        )
        self.btn_play = Button(
            rect=pygame.Rect(740, 20, 240, 40),
            text="Play Ranked",
            on_click=self._on_play_ranked,
            enabled=(self.mode == "pick_for_ranked"),
        )


    def _on_back(self) -> None:
        from .main_menu import MainMenuScene

        self._go(MainMenuScene(self.ctx))

    def _go(self, scene: Scene) -> None:
        self._next = SceneTransition(scene)

    def _decks(self) -> list[SavedHand]:
        inv = self.ctx.inventory
        return inv.list_decks() if inv is not None else []

    def _on_new(self) -> None:
        inv = self.ctx.inventory
        if inv is None:
            return
        name = f"Hand {len(inv.profile.saved_hands) + 1}"
        deck = inv.create_deck(name)
        self._next = SceneTransition(DeckEditorScene(self.ctx, deck_id=deck.id, return_mode=self.mode))

    def _on_edit(self) -> None:
        decks = self._decks()
        if not decks:
            return
        deck = decks[self.selected_index]
        self._next = SceneTransition(DeckEditorScene(self.ctx, deck_id=deck.id, return_mode=self.mode))

    def _on_set_default(self) -> None:
        inv = self.ctx.inventory
        decks = self._decks()
        if inv is None or not decks:
            return
        inv.set_default_deck(decks[self.selected_index].id)

    def _ai_spec_from_rating(self, rating: int) -> AISpec:
        if rating < 900:
            return AISpec(difficulty=0)
        if rating < 1200:
            return AISpec(difficulty=1)
        return AISpec(difficulty=2)

    def _on_play_ranked(self) -> None:
        if self.mode != "pick_for_ranked":
            return
        inv = self.ctx.inventory
        cards_db = self.ctx.cards
        if inv is None or cards_db is None:
            return
        decks = self._decks()
        if not decks:
            return
        deck = decks[self.selected_index]
        ok, _msg = inv.validate_deck(deck)
        if not ok:
            return
        player_deck = inv.deck_card_list(deck)
        ai_deck = list(player_deck)

        # deterministic seed derived from profile meta seed
        seed = (inv.profile.meta_rng_seed * 1103515245 + 12345) & 0x7FFFFFFF
        state = new_match(cards_db, player_deck, ai_deck, seed=seed, config=MatchConfig())
        ai_spec = self._ai_spec_from_rating(inv.profile.ranked.rating)
        from .match import MatchScene

        self._next = SceneTransition(
            MatchScene(self.ctx, match_state=state, ai_spec=ai_spec, player_deck_id=deck.id)
        )

    def handle_event(self, event: pygame.event.Event) -> None:
        for b in (self.btn_back, self.btn_new, self.btn_edit, self.btn_default, self.btn_play):
            if b.handle_event(event):
                return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_list_click(event.pos)

    def _handle_list_click(self, pos: tuple[int, int]) -> None:
        decks = self._decks()
        x0, y0 = 40, 120
        row_h = 46
        for i, _d in enumerate(decks):
            rect = pygame.Rect(x0, y0 + i * row_h, 600, row_h - 6)
            if rect.collidepoint(pos):
                self.selected_index = i
                return

    def update(self, dt: float) -> SceneTransition | None:
        return self._next

    def render(self, screen: pygame.Surface) -> None:
        screen.fill((14, 12, 18))
        fonts = self.ctx.assets.fonts
        for b in (self.btn_back, self.btn_new, self.btn_edit, self.btn_default, self.btn_play):
            b.draw(screen, fonts.ui)

        decks = self._decks()
        draw_text(screen, fonts.big, "Saved Hands", (40, 70))

        inv = self.ctx.inventory
        x0, y0 = 40, 120
        row_h = 46
        for i, d in enumerate(decks):
            rect = pygame.Rect(x0, y0 + i * row_h, 600, row_h - 6)
            bg = (50, 50, 70) if i == self.selected_index else (28, 28, 38)
            pygame.draw.rect(screen, bg, rect, border_radius=8)
            pygame.draw.rect(screen, (0, 0, 0), rect, width=2, border_radius=8)
            flag = " (Default)" if d.is_default else ""
            draw_text(screen, fonts.ui, f"{d.name}{flag}", (rect.x + 10, rect.y + 10))
            if inv is not None:
                ok, msg = inv.validate_deck(d)
                color = (120, 240, 120) if ok else (240, 120, 120)
                draw_text(screen, fonts.small, msg, (rect.right + 10, rect.y + 14), color=color)

        if self.mode == "pick_for_ranked":
            draw_text(screen, fonts.small, "Pick a deck and press Play Ranked.", (40, 700))
        else:
            draw_text(screen, fonts.small, "Create and edit deck presets. Deck size must be 30.", (40, 700))


class DeckEditorScene:
    def __init__(self, ctx: GameContext, deck_id: str, return_mode: str) -> None:
        self.ctx = ctx
        self.deck_id = deck_id
        self.return_mode = return_mode
        self._next: SceneTransition | None = None

        inv = self.ctx.inventory
        cards_db = self.ctx.cards
        if inv is None or cards_db is None:
            raise RuntimeError("Inventory/content not loaded")

        deck = next((d for d in inv.list_decks() if d.id == deck_id), None)
        if deck is None:
            raise RuntimeError("Deck not found")

        self.deck = deck
        self.counts: dict[str, int] = {e.card_id: e.count for e in self.deck.cards}

        self.btn_back = Button(rect=pygame.Rect(20, 20, 120, 40), text="Back", on_click=self._on_back)
        self.btn_save = Button(rect=pygame.Rect(500, 20, 140, 40), text="Save", on_click=self._on_save)
        self.btn_autofill = Button(rect=pygame.Rect(660, 20, 160, 40), text="Auto-fill", on_click=self._on_autofill)
        self.btn_clear = Button(rect=pygame.Rect(840, 20, 140, 40), text="Clear", on_click=self._on_clear)

        self.name_input = TextInput(
            rect=pygame.Rect(160, 20, 320, 40),
            text=self.deck.name,
            on_submit=self._on_rename,
        )

        self._rows: list[tuple[str, pygame.Rect, pygame.Rect]] = []

    def _on_rename(self, name: str) -> None:
        self.deck.name = name

    def _on_back(self) -> None:
        self._next = SceneTransition(DecksScene(self.ctx, mode=self.return_mode))

    def _sync_deck(self) -> None:
        self.deck.cards = [DeckEntry(card_id=cid, count=cnt) for cid, cnt in sorted(self.counts.items()) if cnt > 0]

    def _deck_size(self) -> int:
        return sum(self.counts.values())

    def _on_save(self) -> None:
        inv = self.ctx.inventory
        if inv is None:
            return
        self._sync_deck()
        ok, _msg = inv.validate_deck(self.deck)
        if not ok:
            return
        inv.update_deck(self.deck)
        self._next = SceneTransition(DecksScene(self.ctx, mode=self.return_mode))

    def _on_clear(self) -> None:
        self.counts = {}
        self._sync_deck()

    def _on_autofill(self) -> None:
        inv = self.ctx.inventory
        cards_db = self.ctx.cards
        if inv is None or cards_db is None:
            return
        total = self._deck_size()
        if total >= 30:
            return
        candidates = [c for c in cards_db.cards.values() if "Token" not in c.keywords]
        candidates.sort(key=lambda c: (c.cost, c.rarity, c.id))
        for c in candidates:
            if total >= 30:
                break
            owned = inv.owned_count(c.id)
            cur = self.counts.get(c.id, 0)
            while total < 30 and cur < min(4, owned):
                cur += 1
                total += 1
            if cur > 0:
                self.counts[c.id] = cur
        self._sync_deck()

    def _set_count(self, card_id: str, new_count: int) -> None:
        inv = self.ctx.inventory
        if inv is None:
            return
        owned = inv.owned_count(card_id)
        clamped = max(0, min(new_count, min(4, owned)))
        if clamped <= 0:
            self.counts.pop(card_id, None)
        else:
            self.counts[card_id] = clamped
        self._sync_deck()

    def handle_event(self, event: pygame.event.Event) -> None:
        for b in (self.btn_back, self.btn_save, self.btn_autofill, self.btn_clear):
            if b.handle_event(event):
                return
        if self.name_input.handle_event(event):
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_click(event.pos)

    def _handle_click(self, pos: tuple[int, int]) -> None:
        for cid, minus_r, plus_r in self._rows:
            if minus_r.collidepoint(pos):
                cur = self.counts.get(cid, 0)
                self._set_count(cid, cur - 1)
                return
            if plus_r.collidepoint(pos):
                cur = self.counts.get(cid, 0)
                self._set_count(cid, cur + 1)
                return

    def update(self, dt: float) -> SceneTransition | None:
        # Save enabled only if valid size
        self.btn_save.enabled = self._deck_size() == 30
        return self._next

    def render(self, screen: pygame.Surface) -> None:
        screen.fill((12, 12, 16))
        fonts = self.ctx.assets.fonts
        inv = self.ctx.inventory
        cards_db = self.ctx.cards
        assert inv is not None and cards_db is not None

        for b in (self.btn_back, self.btn_save, self.btn_autofill, self.btn_clear):
            b.draw(screen, fonts.ui)
        self.name_input.draw(screen, fonts.ui)

        draw_text(screen, fonts.big, "Deck Editor", (40, 70))
        size = self._deck_size()
        color = (120, 240, 120) if size == 30 else (240, 200, 120)
        draw_text(screen, fonts.ui, f"Deck size: {size}/30", (40, 110), color=color)
        draw_text(screen, fonts.small, "Click + / - to adjust counts (max 4, up to owned).", (40, 136))

        # Card list
        cards = [c for c in cards_db.cards.values() if "Token" not in c.keywords]
        cards.sort(key=lambda c: (c.cost, c.rarity, c.id))

        x0, y0 = 40, 170
        row_h = 32
        self._rows = []
        for i, c in enumerate(cards[:16]):  # keep UI minimal in V1 (enough for sample set)
            y = y0 + i * row_h
            owned = inv.owned_count(c.id)
            in_deck = self.counts.get(c.id, 0)
            draw_text(screen, fonts.small, f"[{c.cost}] {c.name}", (x0, y))
            draw_text(screen, fonts.small, f"owned {owned}", (x0 + 260, y))
            draw_text(screen, fonts.small, f"deck {in_deck}", (x0 + 360, y))

            minus_r = pygame.Rect(x0 + 460, y - 2, 26, 24)
            plus_r = pygame.Rect(x0 + 492, y - 2, 26, 24)
            pygame.draw.rect(screen, (50, 50, 60), minus_r, border_radius=4)
            pygame.draw.rect(screen, (0, 0, 0), minus_r, width=2, border_radius=4)
            pygame.draw.rect(screen, (50, 50, 60), plus_r, border_radius=4)
            pygame.draw.rect(screen, (0, 0, 0), plus_r, width=2, border_radius=4)
            draw_text(screen, fonts.small, "-", (minus_r.x + 9, minus_r.y + 3))
            draw_text(screen, fonts.small, "+", (plus_r.x + 9, plus_r.y + 3))

            self._rows.append((c.id, minus_r, plus_r))

        draw_text(
            screen,
            fonts.small,
            "Note: sample set is small — V1 skeleton focuses on loop + determinism.",
            (40, 720),
        )
