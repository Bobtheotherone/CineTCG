from __future__ import annotations

import json
import os
from pathlib import Path

# Allow headless generation (CI, terminals without a display)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # type: ignore[import-not-found]


def _repo_root() -> Path:
    # tools/generate_placeholder_assets.py -> parents: [tools, repo_root]
    return Path(__file__).resolve().parents[1]


RARITY_COLORS: dict[str, tuple[int, int, int]] = {
    "common": (80, 80, 80),
    "rare": (40, 80, 140),
    "epic": (110, 60, 150),
    "legendary": (170, 120, 40),
}


def generate_all() -> None:
    root = _repo_root()
    data_dir = root / "src" / "cinetcg" / "data"
    assets_dir = root / "assets"
    cards_dir = assets_dir / "cards"
    cutscenes_dir = assets_dir / "cutscenes"
    ui_dir = assets_dir / "ui"
    cards_dir.mkdir(parents=True, exist_ok=True)
    cutscenes_dir.mkdir(parents=True, exist_ok=True)
    ui_dir.mkdir(parents=True, exist_ok=True)

    cards = json.loads((data_dir / "cards.json").read_text(encoding="utf-8"))["cards"]
    cutscenes = json.loads((data_dir / "cutscenes.json").read_text(encoding="utf-8"))["cutscenes"]

    pygame.init()
    pygame.font.init()
    font = pygame.font.SysFont(None, 24)
    font_small = pygame.font.SysFont(None, 18)

    # Card art placeholders
    size = (256, 356)
    for card in cards:
        cid = card["id"]
        rarity = card.get("rarity", "common")
        name = card.get("name", cid)
        color = RARITY_COLORS.get(rarity, (90, 90, 90))
        surf = pygame.Surface(size)
        surf.fill((20, 20, 20))
        pygame.draw.rect(surf, color, pygame.Rect(8, 8, size[0] - 16, size[1] - 16), border_radius=12)
        pygame.draw.rect(surf, (0, 0, 0), pygame.Rect(12, 12, size[0] - 24, size[1] - 24), width=3, border_radius=10)

        title = font.render(name, True, (240, 240, 240))
        surf.blit(title, (16, 16))

        meta = f"{card.get('type','?').upper()}  |  COST {card.get('cost', '?')}  |  {rarity.upper()}"
        meta_s = font_small.render(meta, True, (230, 230, 230))
        surf.blit(meta_s, (16, 44))

        rules = card.get("rules_text", "")
        # naive wrap
        y = 290
        for line in _wrap_text(rules, 26):
            txt = font_small.render(line, True, (230, 230, 230))
            surf.blit(txt, (16, y))
            y += 18

        out_path = cards_dir / f"{cid}.png"
        pygame.image.save(surf, out_path.as_posix())

    # UI icons
    _make_icon(ui_dir / "icon_gold.png", (220, 200, 60), "G")
    _make_icon(ui_dir / "icon_gems.png", (80, 180, 240), "💎")
    _make_icon(ui_dir / "icon_shards.png", (200, 120, 240), "S")

    # Cutscene frames for any "frames" cutscene
    for cs_id, cfg in cutscenes.items():
        if cfg.get("type") != "frames":
            continue
        cs_path = cutscenes_dir / cs_id
        cs_path.mkdir(parents=True, exist_ok=True)
        _generate_cutscene_frames(cs_path, cs_id, font)

    pygame.quit()
    print("Generated placeholder assets under ./assets/")


def _wrap_text(text: str, max_chars: int) -> list[str]:
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
    return lines[:4]


def _make_icon(path: Path, color: tuple[int, int, int], glyph: str) -> None:
    surf = pygame.Surface((48, 48), pygame.SRCALPHA)
    pygame.draw.circle(surf, color, (24, 24), 22)
    pygame.draw.circle(surf, (0, 0, 0), (24, 24), 22, width=3)
    try:
        font = pygame.font.SysFont(None, 28)
        txt = font.render(glyph, True, (0, 0, 0))
        rect = txt.get_rect(center=(24, 24))
        surf.blit(txt, rect.topleft)
    except Exception:
        pass
    pygame.image.save(surf, path.as_posix())


def _generate_cutscene_frames(out_dir: Path, cutscene_id: str, font: pygame.font.Font) -> None:
    w, h = 640, 360
    for i in range(12):
        surf = pygame.Surface((w, h))
        surf.fill((10, 10, 10))
        # moving bar
        x = int((w + 200) * (i / 11.0)) - 200
        pygame.draw.rect(surf, (200, 80, 80), pygame.Rect(x, 0, 200, h))
        pygame.draw.rect(surf, (240, 240, 240), pygame.Rect(0, 0, w, h), width=6)
        title = font.render(f"CUTSCENE: {cutscene_id}", True, (240, 240, 240))
        surf.blit(title, (18, 18))
        frame_path = out_dir / f"frame_{i+1:04d}.png"
        pygame.image.save(surf, frame_path.as_posix())


if __name__ == "__main__":
    generate_all()
