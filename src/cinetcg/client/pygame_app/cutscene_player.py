from __future__ import annotations

import glob
from dataclasses import dataclass

import pygame  # type: ignore[import-not-found]

from cinetcg.services.content import CutsceneConfig

from .asset_manager import AssetManager


@dataclass
class CutscenePlayer:
    assets: AssetManager
    config: CutsceneConfig
    card_art: pygame.Surface
    cutscene_id: str = ""
    elapsed: float = 0.0
    done: bool = False
    _frames: list[pygame.Surface] | None = None

    def __post_init__(self) -> None:
        if self.config.type == "frames":
            self._frames = self._load_frames()
        else:
            self._frames = None

    def _load_frames(self) -> list[pygame.Surface]:
        # assets/cutscenes/<id>/frame_*.png
        base = self.assets.assets_dir / "cutscenes" / self.cutscene_id
        pattern = str(base / "frame_*.png")
        files = sorted(glob.glob(pattern))
        frames: list[pygame.Surface] = []
        for f in files:
            try:
                frames.append(pygame.image.load(f).convert())
            except Exception:
                continue
        return frames

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.done:
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.done = True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.done = True

    def update(self, dt: float) -> None:
        if self.done:
            return
        self.elapsed += dt
        if self.elapsed >= self.config.duration:
            self.done = True

    def render(self, screen: pygame.Surface) -> None:
        # dim background
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        w, h = screen.get_size()

        if self.config.type == "frames" and self._frames:
            idx = int((self.elapsed / self.config.duration) * len(self._frames))
            idx = max(0, min(len(self._frames) - 1, idx))
            frame = self._frames[idx]
            frame = pygame.transform.smoothscale(frame, (w, h))
            screen.blit(frame, (0, 0))
        else:
            # procedural: zoom card art + flash
            t = min(1.0, self.elapsed / max(0.0001, self.config.duration))
            zoom = 1.0 + 0.25 * (1.0 - (t - 1.0) * (t - 1.0))
            card_w, card_h = self.card_art.get_size()
            target_w = int(card_w * 2.0 * zoom)
            target_h = int(card_h * 2.0 * zoom)
            art = pygame.transform.smoothscale(self.card_art, (target_w, target_h))
            rect = art.get_rect(center=(w // 2, h // 2))
            screen.blit(art, rect.topleft)

            # simple flash at start
            if t < 0.15:
                flash = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
                flash.fill((255, 255, 255, int(180 * (0.15 - t) / 0.15)))
                screen.blit(flash, (0, 0))

        # UI hint
        font = self.assets.fonts.ui
        hint = font.render("Click / ESC to skip", True, (240, 240, 240))
        screen.blit(hint, (20, h - 40))
