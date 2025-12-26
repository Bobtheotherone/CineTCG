from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

CardType = Literal["creature", "spell"]
Rarity = Literal["common", "rare", "epic", "legendary"]
Keyword = Literal["Guard", "Haste", "Lifesteal", "Token"]

EffectType = Literal["damage", "heal", "draw", "buff", "summon"]

DamageTarget = Literal["enemy_creature", "enemy_player", "any"]
HealTarget = Literal["self_player", "self_creature"]
BuffTarget = Literal["self_creature", "any_creature"]


@dataclass(frozen=True)
class DamageEffect:
    type: Literal["damage"]
    amount: int
    target: DamageTarget


@dataclass(frozen=True)
class HealEffect:
    type: Literal["heal"]
    amount: int
    target: HealTarget


@dataclass(frozen=True)
class DrawEffect:
    type: Literal["draw"]
    count: int


@dataclass(frozen=True)
class BuffEffect:
    type: Literal["buff"]
    attack_delta: int
    health_delta: int
    target: BuffTarget


@dataclass(frozen=True)
class SummonEffect:
    type: Literal["summon"]
    token_card_id: str
    count: int


Effect = DamageEffect | HealEffect | DrawEffect | BuffEffect | SummonEffect


@dataclass(frozen=True)
class CreatureStats:
    attack: int
    health: int


@dataclass(frozen=True)
class CardDefinition:
    id: str
    name: str
    type: CardType
    rarity: Rarity
    cost: int
    art_path: str
    rules_text: str
    keywords: tuple[Keyword, ...]
    effects: tuple[Effect, ...]
    creature_stats: CreatureStats | None = None
    cutscene_id: str | None = None


@dataclass(frozen=True)
class CardDatabase:
    """Immutable card database used by the engine."""

    cards: dict[str, CardDefinition]

    def get(self, card_id: str) -> CardDefinition:
        return self.cards[card_id]

    def all_ids(self) -> Sequence[str]:
        return list(self.cards.keys())
