from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from cinetcg.engine.types import CardDatabase, CardDefinition
from cinetcg.services.content import Product, ProductCatalog


class InventoryError(RuntimeError):
    pass


@dataclass
class CosmeticsLoadout:
    board_skin_id: str = "default_board"
    card_back_id: str = "default_back"
    avatar_id: str = "default_avatar"

    @staticmethod
    def from_dict(d: Mapping[str, object]) -> "CosmeticsLoadout":
        return CosmeticsLoadout(
            board_skin_id=str(d.get("board_skin_id", "default_board")),
            card_back_id=str(d.get("card_back_id", "default_back")),
            avatar_id=str(d.get("avatar_id", "default_avatar")),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "board_skin_id": self.board_skin_id,
            "card_back_id": self.card_back_id,
            "avatar_id": self.avatar_id,
        }


@dataclass
class DeckEntry:
    card_id: str
    count: int

    @staticmethod
    def from_dict(d: Mapping[str, object]) -> "DeckEntry":
        cid = d.get("card_id")
        cnt = d.get("count")
        if not isinstance(cid, str) or not isinstance(cnt, int):
            raise InventoryError("Invalid deck entry")
        return DeckEntry(card_id=cid, count=cnt)

    def to_dict(self) -> dict[str, object]:
        return {"card_id": self.card_id, "count": self.count}


@dataclass
class SavedHand:
    id: str
    name: str
    cards: list[DeckEntry]
    cosmetics: CosmeticsLoadout
    is_default: bool = False

    @staticmethod
    def from_dict(d: Mapping[str, object]) -> "SavedHand":
        did = d.get("id")
        name = d.get("name")
        if not isinstance(did, str) or not isinstance(name, str):
            raise InventoryError("Invalid saved hand")
        cards_raw = d.get("cards", [])
        cards: list[DeckEntry] = []
        if isinstance(cards_raw, list):
            for e in cards_raw:
                if isinstance(e, dict):
                    cards.append(DeckEntry.from_dict(e))
        cosmetics_raw = d.get("cosmetics", {})
        cosmetics = (
            CosmeticsLoadout.from_dict(cosmetics_raw)
            if isinstance(cosmetics_raw, dict)
            else CosmeticsLoadout()
        )
        is_def = bool(d.get("is_default", False))
        return SavedHand(id=did, name=name, cards=cards, cosmetics=cosmetics, is_default=is_def)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "cards": [c.to_dict() for c in self.cards],
            "cosmetics": self.cosmetics.to_dict(),
            "is_default": self.is_default,
        }


@dataclass
class RankedState:
    rating: int = 1000
    peak_rating: int = 1000

    @staticmethod
    def from_dict(d: Mapping[str, object]) -> "RankedState":
        rating = d.get("rating", 1000)
        peak = d.get("peak_rating", 1000)
        return RankedState(
            rating=int(rating) if isinstance(rating, int) else 1000,
            peak_rating=int(peak) if isinstance(peak, int) else 1000,
        )

    def to_dict(self) -> dict[str, object]:
        return {"rating": self.rating, "peak_rating": self.peak_rating}


@dataclass
class SettingsState:
    always_show_cutscenes: bool = False

    @staticmethod
    def from_dict(d: Mapping[str, object]) -> "SettingsState":
        return SettingsState(always_show_cutscenes=bool(d.get("always_show_cutscenes", False)))

    def to_dict(self) -> dict[str, object]:
        return {"always_show_cutscenes": self.always_show_cutscenes}


@dataclass
class Profile:
    version: int
    currencies: dict[str, int]
    shards: int
    collection: dict[str, int]
    cosmetics_owned: list[str]
    cosmetics_selected: CosmeticsLoadout
    ranked: RankedState
    saved_hands: list[SavedHand]
    settings: SettingsState
    purchases: list[str]
    meta_rng_seed: int

    @staticmethod
    def default(cards_db: CardDatabase) -> "Profile":
        # Starter collection: enough to build at least one 30-card deck.
        collection: dict[str, int] = {}
        for cid, card in cards_db.cards.items():
            if "Token" in card.keywords:
                continue
            if card.rarity == "common":
                collection[cid] = 4
            elif card.rarity == "rare":
                collection[cid] = 2
            else:
                collection[cid] = 0

        # Starter deck: 30 cards using commons/rares.
        def add(deck: dict[str, int], card_id: str, count: int) -> None:
            deck[card_id] = deck.get(card_id, 0) + count

        deck_counts: dict[str, int] = {}
        # Prefer low-cost commons for a smooth curve
        for cid, qty in list(collection.items()):
            if qty <= 0:
                continue
            if len(deck_counts) >= 10:
                break
            add(deck_counts, cid, min(4, qty))

        # Fill to 30 with whatever is available
        total = sum(deck_counts.values())
        for cid, qty in collection.items():
            if total >= 30:
                break
            if qty <= 0:
                continue
            space = 30 - total
            to_add = min(space, qty, 4 - deck_counts.get(cid, 0))
            if to_add <= 0:
                continue
            add(deck_counts, cid, to_add)
            total = sum(deck_counts.values())

        starter_hand = SavedHand(
            id="deck_starter",
            name="Starter Hand",
            cards=[DeckEntry(card_id=k, count=v) for k, v in sorted(deck_counts.items())],
            cosmetics=CosmeticsLoadout(),
            is_default=True,
        )

        return Profile(
            version=1,
            currencies={"gold": 250, "gems": 100},
            shards=0,
            collection=collection,
            cosmetics_owned=["default_board", "default_back", "default_avatar"],
            cosmetics_selected=CosmeticsLoadout(),
            ranked=RankedState(),
            saved_hands=[starter_hand],
            settings=SettingsState(),
            purchases=[],
            meta_rng_seed=1234567,
        )

    @staticmethod
    def from_dict(d: Mapping[str, object], cards_db: CardDatabase) -> "Profile":
        try:
            version = int(d.get("version", 1))
        except Exception:
            version = 1
        currencies_raw = d.get("currencies", {})
        currencies: dict[str, int] = {"gold": 0, "gems": 0}
        if isinstance(currencies_raw, dict):
            for k in ("gold", "gems"):
                v = currencies_raw.get(k, 0)
                if isinstance(v, int):
                    currencies[k] = v
        shards_raw = d.get("shards", 0)
        shards = int(shards_raw) if isinstance(shards_raw, int) else 0

        collection_raw = d.get("collection", {})
        collection: dict[str, int] = {}
        if isinstance(collection_raw, dict):
            for k, v in collection_raw.items():
                if isinstance(k, str) and isinstance(v, int):
                    collection[k] = v

        cosmetics_owned_raw = d.get("cosmetics_owned", [])
        cosmetics_owned = [str(x) for x in cosmetics_owned_raw] if isinstance(cosmetics_owned_raw, list) else []

        cosmetics_sel_raw = d.get("cosmetics_selected", {})
        cosmetics_selected = (
            CosmeticsLoadout.from_dict(cosmetics_sel_raw)
            if isinstance(cosmetics_sel_raw, dict)
            else CosmeticsLoadout()
        )

        ranked_raw = d.get("ranked", {})
        ranked = RankedState.from_dict(ranked_raw) if isinstance(ranked_raw, dict) else RankedState()

        saved_raw = d.get("saved_hands", [])
        saved: list[SavedHand] = []
        if isinstance(saved_raw, list):
            for sh in saved_raw:
                if isinstance(sh, dict):
                    saved.append(SavedHand.from_dict(sh))
        if not saved:
            # Ensure at least one deck exists
            return Profile.default(cards_db)

        settings_raw = d.get("settings", {})
        settings = SettingsState.from_dict(settings_raw) if isinstance(settings_raw, dict) else SettingsState()

        purchases_raw = d.get("purchases", [])
        purchases = [str(x) for x in purchases_raw] if isinstance(purchases_raw, list) else []

        seed_raw = d.get("meta_rng_seed", 1234567)
        meta_seed = int(seed_raw) if isinstance(seed_raw, int) else 1234567

        # Guarantee exactly one default deck
        any_default = any(sh.is_default for sh in saved)
        if not any_default:
            saved[0].is_default = True
        else:
            seen = False
            for sh in saved:
                if sh.is_default:
                    if seen:
                        sh.is_default = False
                    else:
                        seen = True

        return Profile(
            version=version,
            currencies=currencies,
            shards=shards,
            collection=collection,
            cosmetics_owned=cosmetics_owned,
            cosmetics_selected=cosmetics_selected,
            ranked=ranked,
            saved_hands=saved,
            settings=settings,
            purchases=purchases,
            meta_rng_seed=meta_seed,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "currencies": dict(self.currencies),
            "shards": self.shards,
            "collection": dict(self.collection),
            "cosmetics_owned": list(self.cosmetics_owned),
            "cosmetics_selected": self.cosmetics_selected.to_dict(),
            "ranked": self.ranked.to_dict(),
            "saved_hands": [d.to_dict() for d in self.saved_hands],
            "settings": self.settings.to_dict(),
            "purchases": list(self.purchases),
            "meta_rng_seed": self.meta_rng_seed,
        }


class InventoryService:
    def __init__(self, profile_path: Path, cards_db: CardDatabase, products: ProductCatalog) -> None:
        self._path = profile_path
        self.cards_db = cards_db
        self.products = products
        self.profile = self._load_or_create()

    def _load_or_create(self) -> Profile:
        if not self._path.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
            prof = Profile.default(self.cards_db)
            self._path.write_text(json.dumps(prof.to_dict(), indent=2), encoding="utf-8")
            return prof
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            prof = Profile.default(self.cards_db)
            return prof
        return Profile.from_dict(raw, self.cards_db)

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self.profile.to_dict(), indent=2), encoding="utf-8")

    # -------- Collection --------
    def owned_count(self, card_id: str) -> int:
        return int(self.profile.collection.get(card_id, 0))

    def add_cards(self, card_ids: Iterable[str]) -> None:
        for cid in card_ids:
            if cid not in self.cards_db.cards:
                continue
            self.profile.collection[cid] = self.profile.collection.get(cid, 0) + 1

    # -------- Decks (Saved Hands) --------
    def list_decks(self) -> list[SavedHand]:
        return list(self.profile.saved_hands)

    def get_default_deck(self) -> SavedHand | None:
        for d in self.profile.saved_hands:
            if d.is_default:
                return d
        return None

    def set_default_deck(self, deck_id: str) -> None:
        for d in self.profile.saved_hands:
            d.is_default = d.id == deck_id
        self.save()

    def create_deck(self, name: str) -> SavedHand:
        if len(self.profile.saved_hands) >= 10:
            raise InventoryError("Maximum of 10 Saved Hands in V1.")
        did = f"deck_{len(self.profile.saved_hands)+1}"
        deck = SavedHand(id=did, name=name, cards=[], cosmetics=CosmeticsLoadout(), is_default=False)
        self.profile.saved_hands.append(deck)
        self.save()
        return deck

    def delete_deck(self, deck_id: str) -> None:
        self.profile.saved_hands = [d for d in self.profile.saved_hands if d.id != deck_id]
        if not any(d.is_default for d in self.profile.saved_hands) and self.profile.saved_hands:
            self.profile.saved_hands[0].is_default = True
        self.save()

    def update_deck(self, deck: SavedHand) -> None:
        for i, d in enumerate(self.profile.saved_hands):
            if d.id == deck.id:
                self.profile.saved_hands[i] = deck
                self.save()
                return
        raise InventoryError("Deck not found.")

    def deck_card_list(self, deck: SavedHand) -> list[str]:
        cards: list[str] = []
        for entry in deck.cards:
            cards.extend([entry.card_id] * entry.count)
        return cards

    def validate_deck(self, deck: SavedHand) -> tuple[bool, str]:
        cards = self.deck_card_list(deck)
        if len(cards) != 30:
            return False, "Deck must be exactly 30 cards."
        for entry in deck.cards:
            owned = self.owned_count(entry.card_id)
            if entry.count > owned:
                return False, f"Not enough copies of {entry.card_id} (owned {owned})."
            if entry.count < 0 or entry.count > 4:
                return False, "Card counts must be between 0 and 4."
        return True, "OK"

    # -------- Settings --------
    def set_always_show_cutscenes(self, value: bool) -> None:
        self.profile.settings.always_show_cutscenes = value
        self.save()

    # -------- Economy / Grants --------
    def can_afford(self, product: Product) -> bool:
        for k, v in product.currency_cost.items():
            if k == "gold" and self.profile.currencies.get("gold", 0) < v:
                return False
            if k == "gems" and self.profile.currencies.get("gems", 0) < v:
                return False
        return True

    def deduct_cost(self, product: Product) -> None:
        for k, v in product.currency_cost.items():
            if k in ("gold", "gems"):
                self.profile.currencies[k] = max(0, self.profile.currencies.get(k, 0) - v)

    def apply_product(self, product: Product, *, record_purchase: bool) -> dict[str, object]:
        """Apply product grants into the profile. Returns a summary dict for UI."""
        summary: dict[str, object] = {"product_id": product.id, "grants": [], "pack_cards": []}
        if record_purchase:
            self.profile.purchases.append(product.id)

        # Deduct in-game currency cost if applicable
        if product.currency_cost:
            self.deduct_cost(product)

        rng = random.Random(self.profile.meta_rng_seed)

        for g in product.grants:
            if g.type == "gold":
                self.profile.currencies["gold"] = self.profile.currencies.get("gold", 0) + g.qty
                summary["grants"].append({"type": "gold", "qty": g.qty})
            elif g.type == "gems":
                self.profile.currencies["gems"] = self.profile.currencies.get("gems", 0) + g.qty
                summary["grants"].append({"type": "gems", "qty": g.qty})
            elif g.type == "cosmetic":
                if g.id not in self.profile.cosmetics_owned:
                    self.profile.cosmetics_owned.append(g.id)
                summary["grants"].append({"type": "cosmetic", "id": g.id})
            elif g.type == "card_set":
                cards = self.products.card_sets.get(g.id, [])
                gained: list[str] = []
                for cid in cards:
                    # Give 2 copies per card in set to make deck building possible in V1.
                    for _ in range(max(1, g.qty)):
                        if cid in self.cards_db.cards:
                            self.profile.collection[cid] = self.profile.collection.get(cid, 0) + 2
                            gained.append(cid)
                summary["grants"].append({"type": "card_set", "id": g.id, "cards": gained})
            elif g.type == "pack":
                pack_cards, shards_gained = self._open_pack(rng, pack_id=g.id, product=product)
                summary["pack_cards"] = pack_cards
                if shards_gained > 0:
                    summary["grants"].append({"type": "shards", "qty": shards_gained})
            else:
                summary["grants"].append({"type": "unknown", "id": g.id, "qty": g.qty})

        # advance meta RNG seed deterministically
        self.profile.meta_rng_seed = rng.randrange(1, 2**31 - 1)
        self.save()
        return summary

    def _open_pack(self, rng: random.Random, pack_id: str, product: Product) -> tuple[list[str], int]:
        pack_cfg = self.products.packs.get(pack_id, {})
        cards_per_pack = int(pack_cfg.get("cards_per_pack", 5)) if isinstance(pack_cfg, dict) else 5

        # pool: all non-token cards
        pool = [c for c in self.cards_db.cards.values() if "Token" not in c.keywords]
        by_rarity: dict[str, list[CardDefinition]] = {}
        for c in pool:
            by_rarity.setdefault(c.rarity, []).append(c)

        # odds from product
        odds = product.odds
        if odds is None:
            odds = (
                {"rarity": "common", "probability": 0.75},
                {"rarity": "rare", "probability": 0.20},
                {"rarity": "epic", "probability": 0.045},
                {"rarity": "legendary", "probability": 0.005},
            )

        dist: list[tuple[str, float]] = []
        total = 0.0
        for o in odds:
            r = o.get("rarity")
            p = o.get("probability")
            if isinstance(r, str) and isinstance(p, (int, float)):
                dist.append((r, float(p)))
                total += float(p)
        if total <= 0:
            dist = [("common", 1.0)]
            total = 1.0

        def roll_rarity() -> str:
            x = rng.random() * total
            acc = 0.0
            for r, p in dist:
                acc += p
                if x <= acc:
                    return r
            return dist[-1][0]

        gained_cards: list[str] = []
        shards_gained = 0
        for _ in range(cards_per_pack):
            r = roll_rarity()
            candidates = by_rarity.get(r, [])
            if not candidates:
                candidates = pool
            chosen = candidates[rng.randrange(0, len(candidates))]
            cid = chosen.id
            # Duplicate handling: above 4 copies becomes shards
            owned = self.profile.collection.get(cid, 0)
            if owned >= 4:
                shards_gained += 20
                continue
            self.profile.collection[cid] = owned + 1
            gained_cards.append(cid)

        self.profile.shards += shards_gained
        return gained_cards, shards_gained

    # -------- Ranked rewards --------
    def apply_match_result(self, won: bool) -> dict[str, int]:
        if won:
            gold = 50
            delta = 25
        else:
            gold = 15
            delta = -10
        self.profile.currencies["gold"] = self.profile.currencies.get("gold", 0) + gold
        self.profile.ranked.rating = max(0, self.profile.ranked.rating + delta)
        self.profile.ranked.peak_rating = max(self.profile.ranked.peak_rating, self.profile.ranked.rating)
        self.save()
        return {"gold": gold, "rating_delta": delta}
