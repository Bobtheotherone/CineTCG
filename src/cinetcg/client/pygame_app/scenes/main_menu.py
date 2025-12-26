from __future__ import annotations

import random

import pygame  # type: ignore[import-not-found]

from cinetcg.engine.match import MatchConfig, new_match
from cinetcg.engine.ai import AISpec

from ..app import GameContext
from ..scene_base import Scene, SceneTransition
from ..ui import Button, draw_text
from .collection import CollectionScene
from .decks import DecksScene
from .match import MatchScene
from .settings import SettingsScene
from .shop import ShopScene


class MainMenuScene:
    def __init__(self, ctx: GameContext) -> None:
        self.ctx = ctx
        self._buttons: list[Button] = []
        self._build_ui()

    def _build_ui(self) -> None:
        def go(scene: Scene) -> None:
            self._next = SceneTransition(scene)

        self._next: SceneTransition | None = None
        x = 60
        y = 160
        w = 320
        h = 56
        gap = 14

        self._buttons = [
            Button(
                rect=pygame.Rect(x, y, w, h),
                text="Ranked (vs AI)",
                on_click=self._on_ranked,
            ),
            Button(
                rect=pygame.Rect(x, y + (h + gap) * 1, w, h),
                text="Collection",
                on_click=lambda: go(CollectionScene(self.ctx)),
            ),
            Button(
                rect=pygame.Rect(x, y + (h + gap) * 2, w, h),
                text="Saved Hands",
                on_click=lambda: go(DecksScene(self.ctx, mode="manage")),
            ),
            Button(
                rect=pygame.Rect(x, y + (h + gap) * 3, w, h),
                text="Shop",
                on_click=lambda: go(ShopScene(self.ctx)),
            ),
            Button(
                rect=pygame.Rect(x, y + (h + gap) * 4, w, h),
                text="Settings",
                on_click=lambda: go(SettingsScene(self.ctx)),
            ),
            Button(
                rect=pygame.Rect(x, y + (h + gap) * 5, w, h),
                text="Quit",
                on_click=lambda: pygame.event.post(pygame.event.Event(pygame.QUIT)),
            ),
        ]

    def _ai_spec_from_rating(self, rating: int) -> AISpec:
        if rating < 900:
            return AISpec(difficulty=0)
        if rating < 1200:
            return AISpec(difficulty=1)
        return AISpec(difficulty=2)

    def _on_ranked(self) -> None:
        inv = self.ctx.inventory
        cards_db = self.ctx.cards
        if inv is None or cards_db is None:
            return
        deck = inv.get_default_deck()
        if deck is None:
            self._next = SceneTransition(DecksScene(self.ctx, mode="pick_for_ranked"))
            return
        ok, _msg = inv.validate_deck(deck)
        if not ok:
            self._next = SceneTransition(DecksScene(self.ctx, mode="pick_for_ranked"))
            return

        player_deck = inv.deck_card_list(deck)
        ai_deck = list(player_deck)

        seed = random.randrange(1, 2**31 - 1)
        state = new_match(cards_db, player_deck, ai_deck, seed=seed, config=MatchConfig())
        ai_spec = self._ai_spec_from_rating(inv.profile.ranked.rating)
        self._next = SceneTransition(MatchScene(self.ctx, match_state=state, ai_spec=ai_spec, player_deck_id=deck.id))

    def handle_event(self, event: pygame.event.Event) -> None:
        for b in self._buttons:
            if b.handle_event(event):
                return

    def update(self, dt: float) -> SceneTransition | None:
        return self._next

    def render(self, screen: pygame.Surface) -> None:
        screen.fill((12, 12, 18))
        fonts = self.ctx.assets.fonts
        draw_text(screen, fonts.big, "CineTCG", (60, 40))
        inv = self.ctx.inventory
        if inv is not None:
            draw_text(
                screen,
                fonts.ui,
                f"Gold: {inv.profile.currencies.get('gold', 0)}   Gems: {inv.profile.currencies.get('gems', 0)}   Shards: {inv.profile.shards}",
                (60, 100),
            )
            draw_text(
                screen,
                fonts.ui,
                f"Ranked Rating: {inv.profile.ranked.rating}   (Peak {inv.profile.ranked.peak_rating})",
                (60, 126),
            )
        for b in self._buttons:
            b.draw(screen, fonts.ui)

        draw_text(
            screen,
            fonts.small,
            "V1 MVP: deterministic engine + local profile. Purchases are mock and ethical.",
            (60, 720),
        )
