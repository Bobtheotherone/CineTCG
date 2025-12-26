from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pygame  # type: ignore[import-not-found]

from cinetcg.engine.types import CardDatabase
from cinetcg.paths import Paths
from cinetcg.services.billing import BillingProvider
from cinetcg.services.content import ContentService, CutsceneCatalog, ProductCatalog
from cinetcg.services.inventory import InventoryService
from cinetcg.services.telemetry import TelemetryService

from .asset_manager import AssetManager
from .scene_base import Scene, SceneTransition


@dataclass
class GameContext:
    screen: pygame.Surface
    clock: pygame.time.Clock
    paths: Paths
    assets: AssetManager
    content: ContentService
    billing: BillingProvider
    telemetry: TelemetryService

    # Loaded at boot
    cards: Optional[CardDatabase] = None
    products: Optional[ProductCatalog] = None
    cutscenes: Optional[CutsceneCatalog] = None
    inventory: Optional[InventoryService] = None


class App:
    def __init__(self, ctx: GameContext, initial_scene: Scene) -> None:
        self.ctx = ctx
        self.scene: Scene = initial_scene
        self.running = True

    def run(self) -> int:
        while self.running:
            dt = self.ctx.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                self.scene.handle_event(event)

            tr = self.scene.update(dt)
            if tr is not None:
                self.scene = tr.next_scene

            self.scene.render(self.ctx.screen)
            pygame.display.flip()

        return 0
