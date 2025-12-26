from __future__ import annotations

import pygame  # type: ignore[import-not-found]

from cinetcg.services.content import Product

from ..app import GameContext
from ..cutscene_player import CutscenePlayer
from ..scene_base import Scene, SceneTransition
from ..ui import Button, draw_text

CATEGORIES = ["gems", "cosmetics", "bundles", "packs"]


class ShopScene:
    def __init__(self, ctx: GameContext) -> None:
        self.ctx = ctx
        self._next: SceneTransition | None = None
        self.selected_category: str = "gems"
        self.selected_product_id: str | None = None
        self.message: str = ""

        self.btn_back = Button(rect=pygame.Rect(20, 20, 120, 40), text="Back", on_click=self._on_back)
        self.btn_restore = Button(
            rect=pygame.Rect(160, 20, 200, 40),
            text="Restore Purchases",
            on_click=self._on_restore,
        )

        self._cat_buttons: list[Button] = []
        for i, cat in enumerate(CATEGORIES):
            self._cat_buttons.append(
                Button(
                    rect=pygame.Rect(20 + i * 160, 80, 150, 36),
                    text=cat.title(),
                    on_click=lambda c=cat: self._set_cat(c),
                )
            )

        self.btn_purchase = Button(rect=pygame.Rect(700, 640, 280, 56), text="Purchase", on_click=self._on_purchase)


    def _on_back(self) -> None:
        from .main_menu import MainMenuScene

        self._go(MainMenuScene(self.ctx))

    def _go(self, scene: Scene) -> None:
        self._next = SceneTransition(scene)

    def _set_cat(self, cat: str) -> None:
        self.selected_category = cat
        self.selected_product_id = None
        self.message = ""

    def _products_in_cat(self) -> list[Product]:
        cat = self.selected_category
        catalog = self.ctx.products
        if catalog is None:
            return []
        return catalog.by_category.get(cat, [])

    def _on_restore(self) -> None:
        res = self.ctx.billing.restore_purchases()
        self.message = res.message

    def _on_purchase(self) -> None:
        inv = self.ctx.inventory
        catalog = self.ctx.products
        if inv is None or catalog is None:
            return
        if self.selected_product_id is None:
            return
        prod = catalog.products[self.selected_product_id]

        # Currency-only items: enforce affordability. Mock-IAP items (currency_cost empty) always proceed via billing.
        record_purchase = len(prod.currency_cost) == 0
        if prod.currency_cost and not inv.can_afford(prod):
            self.message = "Not enough currency."
            return

        if record_purchase:
            res = self.ctx.billing.purchase(prod.id)
            if not res.ok:
                self.message = res.message
                return

        summary = inv.apply_product(prod, record_purchase=record_purchase)
        self.message = "Purchased."

        pack_cards = summary.get("pack_cards")
        if isinstance(pack_cards, list) and pack_cards:
            # Go to pack reveal flow
            self._next = SceneTransition(PackRevealScene(self.ctx, card_ids=[str(x) for x in pack_cards]))

    def handle_event(self, event: pygame.event.Event) -> None:
        self.btn_back.handle_event(event)
        self.btn_restore.handle_event(event)
        for b in self._cat_buttons:
            b.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_list_click(event.pos)

        self.btn_purchase.handle_event(event)

    def _handle_list_click(self, pos: tuple[int, int]) -> None:
        products = self._products_in_cat()
        x0, y0 = 20, 130
        row_h = 54
        for i, p in enumerate(products):
            rect = pygame.Rect(x0, y0 + i * row_h, 540, row_h - 8)
            if rect.collidepoint(pos):
                self.selected_product_id = p.id
                self.message = ""
                return

    def update(self, dt: float) -> SceneTransition | None:
        inv = self.ctx.inventory
        catalog = self.ctx.products
        if inv is None or catalog is None:
            self.btn_purchase.enabled = False
        else:
            if self.selected_product_id is None:
                self.btn_purchase.enabled = False
            else:
                prod = catalog.products[self.selected_product_id]
                self.btn_purchase.enabled = (not prod.currency_cost) or inv.can_afford(prod)
        return self._next

    def render(self, screen: pygame.Surface) -> None:
        screen.fill((12, 12, 18))
        fonts = self.ctx.assets.fonts
        inv = self.ctx.inventory

        self.btn_back.draw(screen, fonts.ui)
        self.btn_restore.draw(screen, fonts.ui)
        for b in self._cat_buttons:
            # highlight selected
            b.enabled = True
            b.draw(screen, fonts.small)
        draw_text(screen, fonts.big, "Shop", (20, 100))

        if inv is not None:
            draw_text(
                screen,
                fonts.ui,
                f"Gold {inv.profile.currencies.get('gold', 0)}   Gems {inv.profile.currencies.get('gems', 0)}   Shards {inv.profile.shards}",
                (620, 30),
            )

        products = self._products_in_cat()

        # List
        x0, y0 = 20, 130
        row_h = 54
        for i, p in enumerate(products):
            rect = pygame.Rect(x0, y0 + i * row_h, 540, row_h - 8)
            bg = (50, 50, 70) if p.id == self.selected_product_id else (28, 28, 38)
            pygame.draw.rect(screen, bg, rect, border_radius=8)
            pygame.draw.rect(screen, (0, 0, 0), rect, width=2, border_radius=8)
            draw_text(screen, fonts.ui, p.title, (rect.x + 10, rect.y + 8))
            draw_text(screen, fonts.small, p.price_display, (rect.x + 10, rect.y + 30), color=(200, 200, 220))

        # Details panel
        panel = pygame.Rect(590, 130, 410, 500)
        pygame.draw.rect(screen, (24, 24, 30), panel, border_radius=10)
        pygame.draw.rect(screen, (0, 0, 0), panel, width=2, border_radius=10)
        draw_text(screen, fonts.ui, "Details", (panel.x + 10, panel.y + 10))

        if self.selected_product_id is not None and self.ctx.products is not None:
            prod = self.ctx.products.products[self.selected_product_id]
            y = panel.y + 40
            draw_text(screen, fonts.ui, prod.title, (panel.x + 10, y))
            y += 28
            for line in _wrap(prod.description, 44):
                draw_text(screen, fonts.small, line, (panel.x + 10, y))
                y += 18
            y += 8
            draw_text(screen, fonts.small, f"Price: {prod.price_display}", (panel.x + 10, y))
            y += 22
            if prod.currency_cost:
                draw_text(screen, fonts.small, f"Cost: {prod.currency_cost}", (panel.x + 10, y))
                y += 22
            draw_text(screen, fonts.small, "Grants:", (panel.x + 10, y))
            y += 18
            for g in prod.grants:
                draw_text(screen, fonts.small, f"- {g.type} {g.id} x{g.qty}", (panel.x + 20, y))
                y += 18

            # Odds panel (required near purchase UI for packs)
            if prod.odds is not None:
                y += 12
                odds_rect = pygame.Rect(panel.x + 10, y, panel.w - 20, 120)
                pygame.draw.rect(screen, (18, 18, 22), odds_rect, border_radius=8)
                pygame.draw.rect(screen, (0, 0, 0), odds_rect, width=2, border_radius=8)
                draw_text(screen, fonts.small, "ODDS DISCLOSURE (per card):", (odds_rect.x + 8, odds_rect.y + 8), color=(240, 220, 120))
                oy = odds_rect.y + 32
                for o in prod.odds:
                    rarity = str(o.get("rarity", ""))
                    prob = float(o.get("probability", 0.0))
                    draw_text(screen, fonts.small, f"{rarity.title():10s}  {prob*100:5.2f}%", (odds_rect.x + 10, oy))
                    oy += 18

        self.btn_purchase.draw(screen, fonts.ui)

        if self.message:
            draw_text(screen, fonts.ui, self.message, (590, 650), color=(240, 200, 120))


class PackRevealScene:
    def __init__(self, ctx: GameContext, card_ids: list[str]) -> None:
        self.ctx = ctx
        self.card_ids = card_ids
        self.index = 0
        self._next: SceneTransition | None = None
        self._cutscene: CutscenePlayer | None = None
        self._done = False

        self.btn_back = Button(rect=pygame.Rect(20, 20, 160, 40), text="Back to Shop", on_click=self._on_back)
        self._start_current()

    def _on_back(self) -> None:
        self._next = SceneTransition(ShopScene(self.ctx))

    def _start_current(self) -> None:
        if self.ctx.cutscenes is None or self.ctx.cards is None:
            self._done = True
            return
        if self.index >= len(self.card_ids):
            self._done = True
            return
        cid = self.card_ids[self.index]
        card = self.ctx.cards.cards.get(cid)
        if card is None:
            self.index += 1
            self._start_current()
            return
        cfg = self.ctx.cutscenes.cutscenes.get("cs_pack_reveal")
        if cfg is None:
            self._done = True
            return
        art = self.ctx.assets.get_image(card.art_path, size=(256, 356))
        self._cutscene = CutscenePlayer(self.ctx.assets, config=cfg, card_art=art, cutscene_id="cs_pack_reveal")

    def handle_event(self, event: pygame.event.Event) -> None:
        self.btn_back.handle_event(event)
        if self._cutscene is not None:
            self._cutscene.handle_event(event)
            # if skipped, advance immediately
            if self._cutscene.done:
                self._cutscene = None
                self.index += 1
                self._start_current()

    def update(self, dt: float) -> SceneTransition | None:
        if self._cutscene is not None:
            self._cutscene.update(dt)
            if self._cutscene.done:
                self._cutscene = None
                self.index += 1
                self._start_current()
        return self._next

    def render(self, screen: pygame.Surface) -> None:
        screen.fill((8, 10, 14))
        fonts = self.ctx.assets.fonts
        self.btn_back.draw(screen, fonts.ui)
        draw_text(screen, fonts.big, "Pack Reveal", (220, 30))
        draw_text(screen, fonts.small, "Click / ESC to skip each reveal.", (220, 70))

        if self._done:
            draw_text(screen, fonts.ui, "All cards revealed!", (380, 320))
            y = 360
            for cid in self.card_ids:
                draw_text(screen, fonts.small, f"- {cid}", (380, y))
                y += 18
            return

        if self._cutscene is not None:
            self._cutscene.render(screen)


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
    return lines[:10]
