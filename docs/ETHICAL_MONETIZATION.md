# Ethical monetization

CineTCG V1 implements a **mock** store that is intentionally designed to be ethical and platform-compliant.

## Hard rules
- No dark patterns (no disguised buttons, fake scarcity, nag loops).
- Clear pricing and item descriptions.
- Restore purchases flow exists (mock in V1).

## Randomized packs

If a product grants a randomized pack:
- **Odds must be stored in `products.json`**.
- The Shop UI must show an **odds panel near the purchase UI**.

V1 includes an optional booster pack product demonstrating this.
