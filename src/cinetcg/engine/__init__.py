"""Deterministic, headless rules engine for CineTCG.

IMPORTANT: This package must never import pygame.
"""

from .actions import AttackAction, EndTurnAction, PlayCardAction, TargetRef
from .match import MatchConfig, MatchState, new_match, step
from .types import CardType, Keyword, Rarity

__all__ = [
    "AttackAction",
    "EndTurnAction",
    "PlayCardAction",
    "TargetRef",
    "MatchConfig",
    "MatchState",
    "new_match",
    "step",
    "CardType",
    "Keyword",
    "Rarity",
]
