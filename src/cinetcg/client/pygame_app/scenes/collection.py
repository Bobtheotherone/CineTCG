from __future__ import annotations

import pygame  # type: ignore[import-not-found]

from cinetcg.engine.types import CardDefinition

from ..app import GameContext
from ..scene_base import Scene, SceneTransition
from ..ui import Button, draw_text

RARITIES = ["all", "common", "rare", "epic", "legendary"]
TYPES = ["all", "creature", "spell"]


class CollectionScene:
    def __init__(self, ctx: GameContext) -> None:
        self.ctx = ctx
        self._next: SceneTransition | None = None
        self.rarity_filter = "all"
        self.type_filter = "all"
        self.max_cost: int | None = None
        self.selected_card_id: str | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        self.btn_back = Button(
            rect=pygame.Rect(20, 20, 120, 40),
            text="Back",
            on_click=self._on_back,
        )
        self.btn_rarity = Button(
            rect=pygame.Rect(160, 20, 220, 40),
            text="Rarity: all",
            on_click=self._cycle_rarity,
        )
        self.btn_type = Button(
            rect=pygame.Rect(400, 20, 220, 40),
            text="Type: all",
            on_click=self._cycle_type,
        )
        self.btn_cost = Button(
            rect=pygame.Rect(640, 20, 260, 40),
            text="Cost: any",
            on_click=self._cycle_cost,
        )


    def _on_back(self) -> None:
        from .main_menu import MainMenuScene

        self._go(MainMenuScene(self.ctx))

    def _go(self, scene: Scene) -> None:
        self._next = SceneTransition(scene)

    def _cycle_rarity(self) -> None:
        i = RARITIES.index(self.rarity_filter)
        self.rarity_filter = RARITIES[(i + 1) % len(RARITIES)]
        self.btn_rarity.text = f"Rarity: {self.rarity_filter}"

    def _cycle_type(self) -> None:
        i = TYPES.index(self.type_filter)
        self.type_filter = TYPES[(i + 1) % len(TYPES)]
        self.btn_type.text = f"Type: {self.type_filter}"

    def _cycle_cost(self) -> None:
        if self.max_cost is None:
            self.max_cost = 3
        elif self.max_cost == 3:
            self.max_cost = 5
        elif self.max_cost == 5:
            self.max_cost = 7
        elif self.max_cost == 7:
            self.max_cost = 10
        else:
            self.max_cost = None
        self.btn_cost.text = f"Cost: <= {self.max_cost}" if self.max_cost is not None else "Cost: any"

    def _filtered_cards(self) -> list[CardDefinition]:
        cards_db = self.ctx.cards
        if cards_db is None:
            return []
        cards = list(cards_db.cards.values())
        cards.sort(key=lambda c: (c.cost, c.rarity, c.id))
        out: list[CardDefinition] = []
        for c in cards:
            if self.rarity_filter != "all" and c.rarity != self.rarity_filter:
                continue
            if self.type_filter != "all" and c.type != self.type_filter:
                continue
            if self.max_cost is not None and c.cost > self.max_cost:
                continue
            out.append(c)
        return out

    def handle_event(self, event: pygame.event.Event) -> None:
        for b in (self.btn_back, self.btn_rarity, self.btn_type, self.btn_cost):
            if b.handle_event(event):
                return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_grid_click(event.pos)

    def _handle_grid_click(self, pos: tuple[int, int]) -> None:
        cards = self._filtered_cards()
        x0, y0 = 20, 90
        cell_w, cell_h = 300, 40
        cols = 2
        for i, c in enumerate(cards):
            col = i % cols
            row = i // cols
            rect = pygame.Rect(x0 + col * (cell_w + 10), y0 + row * (cell_h + 8), cell_w, cell_h)
            if rect.collidepoint(pos):
                self.selected_card_id = c.id
                return

    def update(self, dt: float) -> SceneTransition | None:
        return self._next

    def render(self, screen: pygame.Surface) -> None:
        screen.fill((14, 14, 18))
        fonts = self.ctx.assets.fonts
        for b in (self.btn_back, self.btn_rarity, self.btn_type, self.btn_cost):
            b.draw(screen, fonts.ui)

        inv = self.ctx.inventory
        cards = self._filtered_cards()

        # Grid
        x0, y0 = 20, 90
        cell_w, cell_h = 300, 40
        cols = 2
        for i, c in enumerate(cards):
            col = i % cols
            row = i // cols
            rect = pygame.Rect(x0 + col * (cell_w + 10), y0 + row * (cell_h + 8), cell_w, cell_h)
            pygame.draw.rect(screen, (30, 30, 40), rect, border_radius=6)
            pygame.draw.rect(screen, (0, 0, 0), rect, width=2, border_radius=6)
            owned = inv.owned_count(c.id) if inv is not None else 0
            draw_text(screen, fonts.small, f"{c.name} (Cost {c.cost})", (rect.x + 8, rect.y + 10))
            draw_text(screen, fonts.small, f"x{owned}", (rect.right - 50, rect.y + 10))

        # Detail panel
        panel = pygame.Rect(650, 90, 350, 650)
        pygame.draw.rect(screen, (24, 24, 30), panel, border_radius=10)
        pygame.draw.rect(screen, (0, 0, 0), panel, width=2, border_radius=10)
        draw_text(screen, fonts.ui, "Card Details", (panel.x + 10, panel.y + 10))
        if self.selected_card_id is None and cards:
            self.selected_card_id = cards[0].id

        if self.selected_card_id and self.ctx.cards and self.selected_card_id in self.ctx.cards.cards:
            c = self.ctx.cards.cards[self.selected_card_id]
            owned = inv.owned_count(c.id) if inv is not None else 0
            art = self.ctx.assets.get_image(c.art_path, size=(256, 356))
            screen.blit(art, (panel.x + 45, panel.y + 40))
            draw_text(screen, fonts.ui, c.name, (panel.x + 10, panel.y + 410))
            draw_text(
                screen,
                fonts.small,
                f"{c.type.upper()} • {c.rarity.upper()} • Cost {c.cost} • Owned {owned}",
                (panel.x + 10, panel.y + 440),
            )
            # rules text wrap
            y = panel.y + 470
            for line in _wrap(c.rules_text, 40):
                draw_text(screen, fonts.small, line, (panel.x + 10, y))
                y += 18
            if c.keywords:
                draw_text(screen, fonts.small, "Keywords: " + ", ".join(c.keywords), (panel.x + 10, y + 8))
        else:
            draw_text(screen, fonts.small, "Select a card from the grid.", (panel.x + 10, panel.y + 60))


def _wrap(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur: list[str] = []
    for w in words:
        if sum(len(x) for x in cur) + len(cur) + len(w) <= max_chars:
            cur.append(w)
        else:
            lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines[:6]
