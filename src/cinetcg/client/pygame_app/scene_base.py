from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pygame  # type: ignore[import-not-found]


@dataclass
class SceneTransition:
    next_scene: "Scene"


class Scene(Protocol):
    def handle_event(self, event: pygame.event.Event) -> None: ...
    def update(self, dt: float) -> SceneTransition | None: ...
    def render(self, screen: pygame.Surface) -> None: ...
