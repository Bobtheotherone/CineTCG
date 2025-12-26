# CineTCG — V1 Playable MVP Skeleton

A minimal but complete playable loop for a **desktop Pygame digital TCG**:

**Main Menu → Collection → Saved Hands (Deck Presets) → Ranked vs AI match → rewards → Shop (mock purchases) → persistence**

> This repository is designed to be a **production-quality scaffold**:
> - deterministic headless engine (replayable)
> - schema-validated, data-driven content
> - scene-based Pygame client with cutscene framework
> - ethical monetization scaffolding (odds disclosure)

## What’s included

- **Engine (headless, deterministic)** — no `pygame` imports in `src/cinetcg/engine/**`
  - 20 health, 30-card decks, 5-card start
  - 5 board slots, summoning sickness
  - energy ramps 1..10 and refreshes each turn
  - keywords: **Guard / Haste / Lifesteal**
  - spells: damage / heal / draw / buff / summon token
  - explicit RNG seed + action log + replay

- **Client (Pygame scenes)**
  - Boot → Main Menu → Collection → Saved Hands → Match → Rewards → Shop → Settings
  - `AssetManager` for all asset loading

- **Cutscenes**
  - `CutscenePlayer` supports:
    - procedural cut-ins
    - frames-based cutscenes (`assets/cutscenes/<id>/frame_*.png`)
  - always skippable (click / ESC)

- **Shop + ethical monetization**
  - Mock billing provider (always succeeds)
  - If any product grants randomized packs:
    - **odds are stored in `products.json`**
    - Shop displays an **odds panel near purchase UI**

- **Persistence**
  - `./userdata/profile.json` (collection, currencies, cosmetics, rating, saved hands)
  - `./userdata/telemetry.jsonl` (local JSONL events)

- **Quality gates**
  - `ruff` + `mypy --strict` + `pytest`
  - JSON Schema validation tests for all data at boot

## Requirements

- Python **3.12** (recommended) or **3.13**
- Desktop with SDL support (Pygame)

> Note (Windows): if you’re on **Python 3.14+**, `pip` may try to **build pygame from source**.
> Use Python **3.12/3.13** for a clean binary-wheel install.

## Quickstart

### Windows PowerShell

```powershell
cd C:\path\to\CineTCG_v1

# Create venv with a stable Python (recommended)
py -3.12 -m venv .venv

# If activation is blocked in this terminal:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

.\.venv\Scripts\Activate.ps1

python -m pip install -U pip setuptools wheel
python -m pip install -e ".[dev]"

# Optional: regenerate placeholder assets (repo already ships placeholders)
python tools\generate_placeholder_assets.py

python -m cinetcg
```

### macOS / Linux

```bash
cd /path/to/CineTCG_v1
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip setuptools wheel
python -m pip install -e ".[dev]"

# Optional: regenerate placeholder assets (repo already ships placeholders)
python tools/generate_placeholder_assets.py

python -m cinetcg
```

## Dev commands

### Quality gates

```bash
python -m ruff check .
python -m mypy src
python -m pytest
```

### Convenience scripts

- macOS/Linux:

```bash
./scripts/ci.sh all
./scripts/ci.sh run
```

- Windows PowerShell:

```powershell
./scripts/ci.ps1 all
./scripts/ci.ps1 run
```

## Repo structure

```
src/cinetcg/
  engine/            # deterministic, headless rules engine (no pygame)
  client/pygame_app/ # pygame scenes, UI widgets, AssetManager
  services/          # content loading/validation, inventory, billing, telemetry
  data/              # cards.json, products.json, cutscenes.json + schemas
assets/              # placeholder art + UI + cutscene frames
tools/
  generate_placeholder_assets.py
tests/
```

## Docs

- `docs/ARCHITECTURE.md` — layering + determinism rules
- `docs/DATA_FORMATS.md` — JSON schemas and authoring notes
- `docs/ETHICAL_MONETIZATION.md` — odds disclosure rules

## Contributing

See `CONTRIBUTING.md`.

Agents/Codex rules live in `AGENTS.md` (ruff, mypy, pytest are mandatory).

## License

MIT — see `LICENSE`.
