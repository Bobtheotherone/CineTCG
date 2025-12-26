# Data formats

All gameplay content in V1 is data-driven via JSON:

- `src/cinetcg/data/cards.json`
- `src/cinetcg/data/products.json`
- `src/cinetcg/data/cutscenes.json`

Each has a JSON Schema under `src/cinetcg/data/schemas/`.

## Cards (`cards.json`)

Fields (high-level):
- `id`, `name`, `type` (`creature|spell`), `rarity` (`common|rare|epic|legendary`)
- `cost` (0..10)
- `art_path` (local path under `/assets`)
- `cutscene_id` (optional)
- `rules_text`, `keywords`, `effects`

Effects (V1): `damage`, `heal`, `draw`, `buff`, `summon`

## Products (`products.json`)

Products drive the shop UI. If a product grants a randomized pack:
- include an `odds` field in the product
- the Shop shows an **odds panel near purchase UI**

## Cutscenes (`cutscenes.json`)

Maps `cutscene_id` → config:
- `type`: `procedural` or `frames`
- `duration_ms`
- `sfx_cue` (string id; audio is placeholder in V1)

## Validation

Validation runs at boot in the client and in CI via tests:

```bash
python -m pytest -k schema
```
