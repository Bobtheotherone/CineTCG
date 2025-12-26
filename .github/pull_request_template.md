## Summary

- What does this PR change?
- Why is it needed?

## Testing

- [ ] `python -m pytest` passes
- [ ] `python -m ruff check .` passes
- [ ] `python -m mypy src` passes

## Determinism / Engine changes (if applicable)

- [ ] No `pygame` imports in `src/cinetcg/engine/**`
- [ ] All randomness goes through `MatchState.rng` (explicit seed)
- [ ] Replay determinism still holds (same seed + same actions => same snapshot)

## Data / Schema changes (if applicable)

- [ ] Updated JSON Schemas under `src/cinetcg/data/schemas/**`
- [ ] `tests/test_schema_validation.py` passes

## UI / Shop changes (if applicable)

- [ ] All assets loaded via `AssetManager`
- [ ] If any product grants randomized packs, odds are disclosed near purchase UI and stored in `products.json`
