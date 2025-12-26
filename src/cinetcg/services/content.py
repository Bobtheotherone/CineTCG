from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from jsonschema import Draft202012Validator

from cinetcg.engine.types import (
    BuffEffect,
    CardDatabase,
    CardDefinition,
    CreatureStats,
    DamageEffect,
    DrawEffect,
    Effect,
    HealEffect,
    Keyword,
    Rarity,
    SummonEffect,
)


class ContentError(RuntimeError):
    pass


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise ContentError(f"Missing content file: {path}") from e
    except json.JSONDecodeError as e:
        raise ContentError(f"Invalid JSON in {path}: {e}") from e


def _load_schema(path: Path) -> object:
    return _load_json(path)


def validate_json(instance: object, schema: object, *, context: str) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: e.path)
    if errors:
        lines = [f"Schema validation failed for {context}:"]
        for err in errors[:10]:
            loc = "/".join(str(p) for p in err.absolute_path)
            lines.append(f"- {loc}: {err.message}")
        raise ContentError("\n".join(lines))


def _require_str(obj: Mapping[str, object], key: str) -> str:
    v = obj.get(key)
    if not isinstance(v, str):
        raise ContentError(f"Expected string for {key}")
    return v


def _require_int(obj: Mapping[str, object], key: str) -> int:
    v = obj.get(key)
    if not isinstance(v, int):
        raise ContentError(f"Expected int for {key}")
    return v


def _require_list(obj: Mapping[str, object], key: str) -> list[object]:
    v = obj.get(key)
    if not isinstance(v, list):
        raise ContentError(f"Expected list for {key}")
    return v


def _optional_str(obj: Mapping[str, object], key: str) -> str | None:
    v = obj.get(key)
    if v is None:
        return None
    if not isinstance(v, str):
        raise ContentError(f"Expected string for {key}")
    return v


def _parse_keywords(raw: object) -> tuple[Keyword, ...]:
    if not isinstance(raw, list):
        raise ContentError("keywords must be a list")
    kws: list[Keyword] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        # trust schema for allowed values
        kws.append(item)  # type: ignore[assignment]
    return tuple(kws)


def _parse_effect(raw: Mapping[str, object]) -> Effect:
    t = raw.get("type")
    if not isinstance(t, str):
        raise ContentError("Effect missing type")
    if t == "damage":
        return DamageEffect(
            type="damage",
            amount=_require_int(raw, "amount"),
            target=_require_str(raw, "target"),  # schema restricts values
        )  # type: ignore[arg-type]
    if t == "heal":
        return HealEffect(
            type="heal",
            amount=_require_int(raw, "amount"),
            target=_require_str(raw, "target"),  # type: ignore[arg-type]
        )
    if t == "draw":
        return DrawEffect(type="draw", count=_require_int(raw, "count"))
    if t == "buff":
        return BuffEffect(
            type="buff",
            attack_delta=_require_int(raw, "attack_delta"),
            health_delta=_require_int(raw, "health_delta"),
            target=_require_str(raw, "target"),  # type: ignore[arg-type]
        )
    if t == "summon":
        return SummonEffect(
            type="summon",
            token_card_id=_require_str(raw, "token_card_id"),
            count=_require_int(raw, "count"),
        )
    raise ContentError(f"Unknown effect type: {t}")


def _parse_creature_stats(raw: Mapping[str, object] | None) -> CreatureStats | None:
    if raw is None:
        return None
    atk = raw.get("attack")
    hp = raw.get("health")
    if not isinstance(atk, int) or not isinstance(hp, int):
        raise ContentError("Invalid creature_stats")
    return CreatureStats(attack=atk, health=hp)


@dataclass(frozen=True)
class CutsceneConfig:
    type: str  # frames|procedural
    duration: float
    sfx_cue: str


@dataclass(frozen=True)
class CutsceneCatalog:
    cutscenes: dict[str, CutsceneConfig]


@dataclass(frozen=True)
class ProductGrant:
    type: str  # gems|gold|cosmetic|card_set|pack
    id: str
    qty: int


@dataclass(frozen=True)
class Product:
    id: str
    category: str
    title: str
    description: str
    price_display: str
    currency_cost: dict[str, int]
    grants: tuple[ProductGrant, ...]
    odds: tuple[dict[str, object], ...] | None = None


@dataclass(frozen=True)
class ProductCatalog:
    products: dict[str, Product]
    by_category: dict[str, list[Product]]
    card_sets: dict[str, list[str]]
    packs: dict[str, dict[str, object]]


class ContentService:
    def __init__(self, data_dir: Path, schema_dir: Path) -> None:
        self._data_dir = data_dir
        self._schema_dir = schema_dir

    def load_cards_db(self) -> CardDatabase:
        cards_path = self._data_dir / "cards.json"
        schema_path = self._schema_dir / "cards.schema.json"
        raw = _load_json(cards_path)
        schema = _load_schema(schema_path)
        validate_json(raw, schema, context=str(cards_path))

        if not isinstance(raw, dict):
            raise ContentError("cards.json must be an object")
        raw_cards = raw.get("cards")
        if not isinstance(raw_cards, list):
            raise ContentError("cards.json.cards must be a list")

        cards: dict[str, CardDefinition] = {}
        for item in raw_cards:
            if not isinstance(item, dict):
                continue
            card_id = _require_str(item, "id")
            name = _require_str(item, "name")
            ctype = _require_str(item, "type")
            rarity = _require_str(item, "rarity")
            cost = _require_int(item, "cost")
            art_path = _require_str(item, "art_path")
            rules_text = _require_str(item, "rules_text")
            cutscene_id = _optional_str(item, "cutscene_id")
            keywords = _parse_keywords(item.get("keywords", []))
            effects_raw = item.get("effects", [])
            effects: list[Effect] = []
            if isinstance(effects_raw, list):
                for eff in effects_raw:
                    if isinstance(eff, dict):
                        effects.append(_parse_effect(eff))
            creature_stats = None
            if ctype == "creature":
                raw_stats = item.get("creature_stats")
                if isinstance(raw_stats, dict):
                    creature_stats = _parse_creature_stats(raw_stats)
            card = CardDefinition(
                id=card_id,
                name=name,
                type=ctype,  # type: ignore[arg-type]
                rarity=rarity,  # type: ignore[arg-type]
                cost=cost,
                art_path=art_path,
                cutscene_id=cutscene_id,
                rules_text=rules_text,
                keywords=keywords,
                effects=tuple(effects),
                creature_stats=creature_stats,
            )
            cards[card.id] = card
        return CardDatabase(cards=cards)

    def load_cutscenes(self) -> CutsceneCatalog:
        path = self._data_dir / "cutscenes.json"
        schema = _load_schema(self._schema_dir / "cutscenes.schema.json")
        raw = _load_json(path)
        validate_json(raw, schema, context=str(path))
        if not isinstance(raw, dict):
            raise ContentError("cutscenes.json must be an object")
        raw_map = raw.get("cutscenes")
        if not isinstance(raw_map, dict):
            raise ContentError("cutscenes.json.cutscenes must be an object")
        out: dict[str, CutsceneConfig] = {}
        for k, v in raw_map.items():
            if not isinstance(k, str) or not isinstance(v, dict):
                continue
            ctype = _require_str(v, "type")
            duration = v.get("duration")
            if not isinstance(duration, (int, float)):
                raise ContentError("duration must be number")
            sfx = _require_str(v, "sfx_cue")
            out[k] = CutsceneConfig(type=ctype, duration=float(duration), sfx_cue=sfx)
        return CutsceneCatalog(cutscenes=out)

    def load_products(self) -> ProductCatalog:
        path = self._data_dir / "products.json"
        schema = _load_schema(self._schema_dir / "products.schema.json")
        raw = _load_json(path)
        validate_json(raw, schema, context=str(path))
        if not isinstance(raw, dict):
            raise ContentError("products.json must be an object")

        raw_products = raw.get("products")
        if not isinstance(raw_products, list):
            raise ContentError("products.json.products must be a list")

        card_sets: dict[str, list[str]] = {}
        raw_sets = raw.get("card_sets", {})
        if isinstance(raw_sets, dict):
            for set_id, lst in raw_sets.items():
                if not isinstance(set_id, str) or not isinstance(lst, list):
                    continue
                card_ids = [c for c in lst if isinstance(c, str)]
                card_sets[set_id] = card_ids

        packs: dict[str, dict[str, object]] = {}
        raw_packs = raw.get("packs", {})
        if isinstance(raw_packs, dict):
            for pack_id, pack_cfg in raw_packs.items():
                if not isinstance(pack_id, str) or not isinstance(pack_cfg, dict):
                    continue
                packs[pack_id] = pack_cfg

        products: dict[str, Product] = {}
        by_cat: dict[str, list[Product]] = {}
        for p in raw_products:
            if not isinstance(p, dict):
                continue
            pid = _require_str(p, "id")
            cat = _require_str(p, "category")
            title = _require_str(p, "title")
            desc = _require_str(p, "description")
            price = _require_str(p, "price_display")
            cc_raw = p.get("currency_cost", {})
            currency_cost: dict[str, int] = {}
            if isinstance(cc_raw, dict):
                for ck, cv in cc_raw.items():
                    if isinstance(ck, str) and isinstance(cv, int):
                        currency_cost[ck] = cv

            grants_raw = p.get("grants")
            if not isinstance(grants_raw, list):
                raise ContentError("product.grants must be list")
            grants: list[ProductGrant] = []
            for g in grants_raw:
                if not isinstance(g, dict):
                    continue
                grants.append(
                    ProductGrant(
                        type=_require_str(g, "type"),
                        id=_require_str(g, "id"),
                        qty=_require_int(g, "qty"),
                    )
                )
            odds_out: tuple[dict[str, object], ...] | None = None
            raw_odds = p.get("odds")
            if isinstance(raw_odds, list):
                odds_list: list[dict[str, object]] = []
                for o in raw_odds:
                    if isinstance(o, dict):
                        odds_list.append({k: v for k, v in o.items()})
                odds_out = tuple(odds_list)

            prod = Product(
                id=pid,
                category=cat,
                title=title,
                description=desc,
                price_display=price,
                currency_cost=currency_cost,
                grants=tuple(grants),
                odds=odds_out,
            )
            products[pid] = prod
            by_cat.setdefault(cat, []).append(prod)

        # Stable ordering for UI
        for cat, lst in by_cat.items():
            by_cat[cat] = sorted(lst, key=lambda pr: pr.id)

        return ProductCatalog(products=products, by_category=by_cat, card_sets=card_sets, packs=packs)

    def validate_all(self) -> None:
        # Load is validation (schema + parse)
        _ = self.load_cards_db()
        _ = self.load_cutscenes()
        _ = self.load_products()
