from __future__ import annotations

import traceback

import pygame  # type: ignore[import-not-found]

from cinetcg.services.inventory import InventoryService
from ..app import GameContext
from ..scene_base import SceneTransition
from ..ui import Button, draw_text
from .main_menu import MainMenuScene


class BootScene:
    def __init__(self, ctx: GameContext) -> None:
        self.ctx = ctx
        self._did_boot = False
        self._error: str | None = None
        self._quit_button: Button | None = None

    def handle_event(self, event: pygame.event.Event) -> None:
        if self._quit_button is not None:
            self._quit_button.handle_event(event)

    def update(self, dt: float) -> SceneTransition | None:
        if self._did_boot:
            return None
        self._did_boot = True
        try:
            self.ctx.content.validate_all()
            self.ctx.cards = self.ctx.content.load_cards_db()
            self.ctx.products = self.ctx.content.load_products()
            self.ctx.cutscenes = self.ctx.content.load_cutscenes()

            self.ctx.paths.userdata_dir.mkdir(parents=True, exist_ok=True)
            self.ctx.inventory = InventoryService(
                profile_path=self.ctx.paths.userdata_dir / "profile.json",
                cards_db=self.ctx.cards,
                products=self.ctx.products,
            )

            self.ctx.telemetry.log("boot", {"ok": True})
            return SceneTransition(MainMenuScene(self.ctx))
        except Exception as e:
            tb = traceback.format_exc(limit=8)
            self._error = f"{e}\n\n{tb}"
            self.ctx.telemetry.log("boot", {"ok": False, "error": str(e)})
            # Offer quit button
            self._quit_button = Button(
                rect=pygame.Rect(20, 700, 140, 44),
                text="Quit",
                on_click=lambda: pygame.event.post(pygame.event.Event(pygame.QUIT)),
            )
            return None

    def render(self, screen: pygame.Surface) -> None:
        screen.fill((10, 10, 10))
        font = self.ctx.assets.fonts.big
        draw_text(screen, font, "CineTCG", (20, 20))

        font2 = self.ctx.assets.fonts.ui
        if self._error is None:
            draw_text(screen, font2, "Booting... validating data, loading profile.", (20, 80))
            draw_text(screen, self.ctx.assets.fonts.small, "Tip: run `python tools/generate_placeholder_assets.py`", (20, 110))
        else:
            draw_text(screen, font2, "BOOT ERROR", (20, 80), color=(240, 80, 80))
            y = 120
            for line in self._error.splitlines()[:22]:
                draw_text(screen, self.ctx.assets.fonts.small, line[:120], (20, y), color=(230, 230, 230))
                y += 18
            if self._quit_button is not None:
                self._quit_button.draw(screen, font2)
