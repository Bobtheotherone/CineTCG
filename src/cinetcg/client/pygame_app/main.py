from __future__ import annotations

import argparse

import pygame  # type: ignore[import-not-found]

from cinetcg.paths import get_paths
from cinetcg.services.billing import MockBillingProvider
from cinetcg.services.content import ContentService
from cinetcg.services.telemetry import TelemetryService

from .app import App, GameContext
from .asset_manager import AssetManager
from .scenes.boot import BootScene


def main() -> int:
    parser = argparse.ArgumentParser(prog="cinetcg")
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=768)
    args = parser.parse_args()

    pygame.init()
    screen = pygame.display.set_mode((args.width, args.height))
    pygame.display.set_caption("CineTCG — V1")

    clock = pygame.time.Clock()
    paths = get_paths()

    assets = AssetManager(repo_root=paths.repo_root, assets_dir=paths.assets_dir)
    content = ContentService(data_dir=paths.data_dir, schema_dir=paths.schema_dir)
    billing = MockBillingProvider()
    telemetry = TelemetryService(paths.userdata_dir / "telemetry.jsonl")

    ctx = GameContext(
        screen=screen,
        clock=clock,
        paths=paths,
        assets=assets,
        content=content,
        billing=billing,
        telemetry=telemetry,
    )

    app = App(ctx, BootScene(ctx))
    return app.run()
