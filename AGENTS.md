# AGENTS.md — CineTCG Repo Rules (Codex/Agents)

This repository is a **deterministic headless TCG engine + Pygame client**.

## Commands (run from repo root)

Create venv + install:
```bash
python -m venv .venv

# macOS/Linux:
source .venv/bin/activate

# Windows PowerShell:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\.venv\Scripts\Activate.ps1

pip install -e ".[dev]"
```

Generate placeholder assets:
```bash
python tools/generate_placeholder_assets.py
```

Quality gates:
```bash
ruff check .
mypy src
pytest
```

Convenience Makefile:
```bash
make lint
make typecheck
make test
make run
```

On Windows (no `make` by default), run the underlying commands:

```powershell
python -m ruff check .
python -m mypy src
python -m pytest
python -m cinetcg
```

Or use:

```powershell
./scripts/ci.ps1 all
```

## Hard rules
- **Engine is headless and deterministic**:
  - Do **not** import `pygame` (or anything UI-related) in `src/cinetcg/engine/**`.
  - All randomness in the engine must go through the match state's explicit RNG seed.
  - Keep `action_log` replayable.

- **Client is a thin layer**:
  - Pygame code lives only under `src/cinetcg/client/pygame_app/**`.
  - Assets must be loaded via `AssetManager`.

- **Data-driven content**:
  - Card behavior must remain generic and driven by `cards.json` effects.
  - `cards.json`, `products.json`, and `cutscenes.json` must validate against their JSON Schemas.
  - If adding new fields: update schemas + parsing + tests.

- **Ethical monetization only**:
  - No dark patterns.
  - If any product grants randomized packs, show odds near purchase UI and store odds in `products.json`.

## Style & quality
- Use **ruff** formatting/quality rules (see `pyproject.toml`).
- Keep **mypy strict** clean (`mypy src` must pass).
- Add/maintain **pytest** coverage for engine rules + determinism + schema validation.

## Testing expectations
- Determinism test must remain stable:
  - same seed + same action list => same final snapshot.
- Schema validation tests must fail loudly on invalid content.
