from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pygame  # type: ignore[import-not-found]


@dataclass
class Fonts:
    ui: pygame.font.Font
    small: pygame.font.Font
    big: pygame.font.Font


class AssetManager:
    def __init__(self, repo_root: Path, assets_dir: Path) -> None:
        self.repo_root = repo_root
        self.assets_dir = assets_dir
        self._cache: dict[tuple[str, int, int], pygame.Surface] = {}

        pygame.font.init()
        self.fonts = Fonts(
            ui=pygame.font.SysFont(None, 24),
            small=pygame.font.SysFont(None, 18),
            big=pygame.font.SysFont(None, 34),
        )

    def _resolve(self, path_str: str) -> Path:
        p = Path(path_str)
        if p.is_absolute():
            return p
        # Allow data files to reference "assets/..."
        if path_str.startswith("assets/"):
            return self.repo_root / path_str
        return self.assets_dir / path_str

    def get_image(self, path_str: str, size: tuple[int, int] | None = None) -> pygame.Surface:
        w, h = size if size is not None else (0, 0)
        key = (path_str, w, h)
        if key in self._cache:
            return self._cache[key]

        path = self._resolve(path_str)
        if path.exists():
            try:
                img = pygame.image.load(path.as_posix()).convert_alpha()
                if size is not None:
                    img = pygame.transform.smoothscale(img, size)
                self._cache[key] = img
                return img
            except Exception:
                pass

        # Fallback placeholder
        fallback = pygame.Surface(size or (64, 64))
        fallback.fill((200, 40, 200))
        self._cache[key] = fallback
        return fallback
