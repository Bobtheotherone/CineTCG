from __future__ import annotations

import pygame  # type: ignore[import-not-found]

from ..app import GameContext
from ..scene_base import Scene, SceneTransition
from ..ui import Button, Toggle, draw_text


class SettingsScene:
    def __init__(self, ctx: GameContext) -> None:
        self.ctx = ctx
        self._next: SceneTransition | None = None
        inv = self.ctx.inventory
        current = inv.profile.settings.always_show_cutscenes if inv is not None else False

        self.btn_back = Button(rect=pygame.Rect(20, 20, 120, 40), text="Back", on_click=self._on_back)
        self.toggle_cutscenes = Toggle(
            rect=pygame.Rect(40, 120, 520, 44),
            label="Always show cutscenes (even for common/rare)",
            value=current,
            on_change=self._on_toggle_cutscenes,
        )


    def _on_back(self) -> None:
        from .main_menu import MainMenuScene

        self._go(MainMenuScene(self.ctx))

    def _go(self, scene: Scene) -> None:
        self._next = SceneTransition(scene)

    def _on_toggle_cutscenes(self, value: bool) -> None:
        inv = self.ctx.inventory
        if inv is None:
            return
        inv.set_always_show_cutscenes(value)

    def handle_event(self, event: pygame.event.Event) -> None:
        self.btn_back.handle_event(event)
        self.toggle_cutscenes.handle_event(event)

    def update(self, dt: float) -> SceneTransition | None:
        return self._next

    def render(self, screen: pygame.Surface) -> None:
        screen.fill((12, 12, 18))
        fonts = self.ctx.assets.fonts
        self.btn_back.draw(screen, fonts.ui)
        draw_text(screen, fonts.big, "Settings", (40, 70))
        self.toggle_cutscenes.draw(screen, fonts.ui)
