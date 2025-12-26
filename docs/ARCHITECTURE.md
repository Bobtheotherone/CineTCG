# Architecture

CineTCG is split into two clear layers:

1. **Engine (headless, deterministic)** — `src/cinetcg/engine/`
2. **Client (Pygame scenes)** — `src/cinetcg/client/pygame_app/`

A small **services** layer binds profile persistence, content validation, and store entitlements.

## Determinism rules

The engine must be deterministic and replayable:
- No `pygame` imports in the engine.
- All randomness flows through `MatchState.rng` which is seeded explicitly.
- `MatchState.action_log` can be replayed with the same seed to get the same final snapshot.

## Data-driven content

Authoritative content lives under `src/cinetcg/data/` and must validate against JSON Schemas at boot and in tests:
- `cards.json` + `schemas/cards.schema.json`
- `products.json` + `schemas/products.schema.json`
- `cutscenes.json` + `schemas/cutscenes.schema.json`

## Runtime flow

1. **BootScene** validates content and loads `./userdata/profile.json` (creating a default profile if missing).
2. Main Menu offers fast navigation, with Ranked as primary.
3. MatchScene drives the loop by sending actions into the engine and rendering the state.
4. Post-match rewards update profile (gold/rating), then user can go to Shop, Decks, etc.

## Services overview

- `ContentService`: JSON load + schema validation
- `InventoryService`: profile state (collection, decks, currencies, cosmetics)
- `BillingProvider`: purchase/restore abstraction (V1 uses `MockBillingProvider`)
- `TelemetryService`: local JSONL event logging
