# Contributing

Thanks for helping improve **CineTCG**.

## Development setup

### Python
- Recommended: **Python 3.12**
- Supported by this repo: **>=3.12,<3.14** (pygame wheels may lag new CPython versions)

### Install

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\.venv\Scripts\Activate.ps1

pip install -e ".[dev]"
```

### Quality gates

```bash
python -m ruff check .
python -m mypy src
python -m pytest
```

## Repository rules (important)

- **Engine is headless & deterministic**
  - No `pygame` imports in `src/cinetcg/engine/**`
  - All randomness flows through `MatchState.rng` with an explicit seed
  - Keep action logs replayable

- **Data-driven content**
  - Any changes to `cards.json`, `products.json`, `cutscenes.json` must validate against schemas

## Optional: pre-commit hooks

If you use `pre-commit`, this repo includes `.pre-commit-config.yaml`:

```bash
pip install pre-commit
pre-commit install
```
  - If you add fields, update the schema + parser + tests

- **Ethical monetization only**
  - If adding randomized packs: odds must be shown near purchase UI and stored in `products.json`

## PR checklist

- [ ] Tests/ruff/mypy pass
- [ ] Engine determinism preserved (if engine touched)
- [ ] Schema tests pass (if data touched)
- [ ] UI: cutscenes remain skippable
