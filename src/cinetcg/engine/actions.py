from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TargetKind = Literal["player", "creature"]


@dataclass(frozen=True)
class TargetRef:
    kind: TargetKind
    player: int
    slot: int | None = None

    @staticmethod
    def player_target(player: int) -> "TargetRef":
        return TargetRef(kind="player", player=player, slot=None)

    @staticmethod
    def creature_target(player: int, slot: int) -> "TargetRef":
        return TargetRef(kind="creature", player=player, slot=slot)


@dataclass(frozen=True)
class PlayCardAction:
    player: int
    hand_index: int
    target: TargetRef | None = None


@dataclass(frozen=True)
class AttackAction:
    player: int
    attacker_slot: int
    target: TargetRef


@dataclass(frozen=True)
class EndTurnAction:
    player: int


Action = PlayCardAction | AttackAction | EndTurnAction
