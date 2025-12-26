from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from .actions import Action, AttackAction, EndTurnAction, PlayCardAction, TargetRef
from .types import (
    BuffEffect,
    CardDatabase,
    CardDefinition,
    DamageEffect,
    DrawEffect,
    Effect,
    HealEffect,
    Keyword,
    SummonEffect,
)

Event = dict[str, object]


@dataclass(frozen=True)
class MatchConfig:
    starting_health: int = 20
    starting_hand: int = 5
    deck_size: int = 30
    board_slots: int = 5
    max_energy: int = 10


@dataclass
class CreatureInstance:
    card_id: str
    attack: int
    health: int
    keywords: frozenset[Keyword]
    summoning_sick: bool = True
    has_attacked: bool = False

    def has(self, kw: Keyword) -> bool:
        return kw in self.keywords


@dataclass
class PlayerState:
    health: int
    energy_max: int
    energy: int
    deck: list[str]
    hand: list[str]
    board: list[CreatureInstance | None]
    discard: list[str] = field(default_factory=list)
    turns_taken: int = 0  # used for "no draw on first turn" logic


@dataclass
class StepResult:
    ok: bool
    events: list[Event]
    error: str | None = None


@dataclass
class MatchState:
    cards: CardDatabase
    config: MatchConfig
    seed: int
    rng: random.Random
    players: list[PlayerState]
    current_player: int = 0
    winner: int | None = None
    action_log: list[Action] = field(default_factory=list)
    event_log: list[Event] = field(default_factory=list)

    def opponent(self, player: int) -> int:
        return 1 - player


def _shuffle(rng: random.Random, items: list[str]) -> None:
    rng.shuffle(items)


def _draw_one(state: MatchState, player: int) -> None:
    ps = state.players[player]
    if not ps.deck:
        return
    card_id = ps.deck.pop()
    ps.hand.append(card_id)
    state.event_log.append({"type": "CARD_DRAWN", "player": player, "card_id": card_id})


def _start_turn(state: MatchState, player: int) -> None:
    ps = state.players[player]
    # Energy ramp
    ps.energy_max = min(state.config.max_energy, ps.energy_max + 1)
    ps.energy = ps.energy_max

    # Refresh creatures
    for c in ps.board:
        if c is None:
            continue
        c.has_attacked = False
        c.summoning_sick = False

    # Draw (but not on your first turn — starting hand already drawn)
    if ps.turns_taken > 0:
        _draw_one(state, player)
    ps.turns_taken += 1

    state.event_log.append({"type": "TURN_STARTED", "player": player, "energy": ps.energy_max})


def _find_empty_slot(board: Sequence[CreatureInstance | None]) -> int | None:
    for i, c in enumerate(board):
        if c is None:
            return i
    return None


def _remove_dead(state: MatchState) -> None:
    for p_i, ps in enumerate(state.players):
        for slot, c in enumerate(ps.board):
            if c is None:
                continue
            if c.health <= 0:
                ps.discard.append(c.card_id)
                ps.board[slot] = None
                state.event_log.append(
                    {"type": "CREATURE_DIED", "player": p_i, "slot": slot, "card_id": c.card_id}
                )


def _heal_player(state: MatchState, player: int, amount: int) -> None:
    if amount <= 0:
        return
    ps = state.players[player]
    before = ps.health
    ps.health = min(state.config.starting_health, ps.health + amount)
    healed = ps.health - before
    if healed > 0:
        state.event_log.append({"type": "HEAL_PLAYER", "player": player, "amount": healed})


def _damage_player(state: MatchState, player: int, amount: int) -> int:
    if amount <= 0:
        return 0
    ps = state.players[player]
    dealt = min(ps.health, amount)
    ps.health -= amount
    state.event_log.append({"type": "DAMAGE_PLAYER", "player": player, "amount": amount, "dealt": dealt})
    return dealt

def _damage_creature(state: MatchState, player: int, slot: int, amount: int) -> int:
    ps = state.players[player]
    c = ps.board[slot]
    if c is None:
        return 0
    dealt = min(c.health, amount)
    c.health -= amount
    state.event_log.append(
        {"type": "DAMAGE_CREATURE", "player": player, "slot": slot, "amount": amount}
    )
    return dealt


def _check_winner(state: MatchState) -> None:
    if state.winner is not None:
        return
    p0 = state.players[0].health
    p1 = state.players[1].health
    if p0 <= 0 and p1 <= 0:
        # Deterministic tie-break: current player loses (so last attacker wins)
        state.winner = state.opponent(state.current_player)
        state.event_log.append({"type": "GAME_ENDED", "winner": state.winner, "reason": "double_ko"})
    elif p0 <= 0:
        state.winner = 1
        state.event_log.append({"type": "GAME_ENDED", "winner": 1, "reason": "health_0"})
    elif p1 <= 0:
        state.winner = 0
        state.event_log.append({"type": "GAME_ENDED", "winner": 0, "reason": "health_0"})


def _has_guard(ps: PlayerState) -> bool:
    for c in ps.board:
        if c is None:
            continue
        if c.has("Guard"):
            return True
    return False


def _valid_attack_targets(state: MatchState, attacker_player: int) -> list[TargetRef]:
    defender = state.opponent(attacker_player)
    dps = state.players[defender]
    targets: list[TargetRef] = []
    guard_only = _has_guard(dps)
    for i, c in enumerate(dps.board):
        if c is None:
            continue
        if guard_only and not c.has("Guard"):
            continue
        targets.append(TargetRef.creature_target(defender, i))
    if not guard_only:
        targets.append(TargetRef.player_target(defender))
    return targets


def get_valid_targets_for_play(
    state: MatchState, player: int, card_id: str
) -> list[TargetRef]:
    """Returns all valid targets for playing card_id right now.

    If the card needs no target, returns an empty list.
    """
    card = state.cards.get(card_id)
    if card.type == "creature":
        return []

    needs_target = False
    target_refs: list[TargetRef] = []
    for eff in card.effects:
        if isinstance(eff, DamageEffect) and eff.target in ("enemy_creature", "enemy_player", "any"):
            needs_target = needs_target or eff.target in ("enemy_creature", "enemy_player", "any")
        if isinstance(eff, HealEffect) and eff.target == "self_creature":
            needs_target = True
        if isinstance(eff, BuffEffect):
            needs_target = True

    if not needs_target:
        return []

    enemy = state.opponent(player)
    ps = state.players[player]
    eps = state.players[enemy]

    # Self creatures
    for i, c in enumerate(ps.board):
        if c is None:
            continue
        target_refs.append(TargetRef.creature_target(player, i))

    # Enemy creatures
    for i, c in enumerate(eps.board):
        if c is None:
            continue
        target_refs.append(TargetRef.creature_target(enemy, i))

    # Players
    target_refs.append(TargetRef.player_target(player))
    target_refs.append(TargetRef.player_target(enemy))
    return target_refs


def _resolve_spell(state: MatchState, player: int, card: CardDefinition, target: TargetRef | None) -> StepResult:
    events: list[Event] = []
    enemy = state.opponent(player)

    def require(cond: bool, msg: str) -> StepResult | None:
        if not cond:
            return StepResult(ok=False, events=[], error=msg)
        return None

    for eff in card.effects:
        if isinstance(eff, DamageEffect):
            if eff.target == "enemy_player":
                if target is not None:
                    chk = require(target.kind == "player" and target.player == enemy, "Target enemy player.")
                    if chk:
                        return chk
                _damage_player(state, enemy, eff.amount)
            elif eff.target == "enemy_creature":
                chk = require(
                    target is not None and target.kind == "creature" and target.player == enemy,
                    "Target an enemy creature.",
                )
                if chk:
                    return chk
                assert target is not None and target.slot is not None
                _damage_creature(state, enemy, target.slot, eff.amount)
            elif eff.target == "any":
                chk = require(target is not None, "Select a target.")
                if chk:
                    return chk
                assert target is not None
                if target.kind == "player":
                    _damage_player(state, target.player, eff.amount)
                else:
                    assert target.slot is not None
                    _damage_creature(state, target.player, target.slot, eff.amount)

        elif isinstance(eff, HealEffect):
            if eff.target == "self_player":
                _heal_player(state, player, eff.amount)
            elif eff.target == "self_creature":
                chk = require(
                    target is not None and target.kind == "creature" and target.player == player,
                    "Target one of your creatures.",
                )
                if chk:
                    return chk
                assert target is not None and target.slot is not None
                # Heal creature up to its current max-ish (we don't track max health separately in V1)
                ps = state.players[player]
                c = ps.board[target.slot]
                if c is not None:
                    before = c.health
                    c.health += eff.amount
                    healed = c.health - before
                    if healed > 0:
                        state.event_log.append(
                            {"type": "HEAL_CREATURE", "player": player, "slot": target.slot, "amount": healed}
                        )

        elif isinstance(eff, DrawEffect):
            for _ in range(max(0, eff.count)):
                _draw_one(state, player)

        elif isinstance(eff, BuffEffect):
            if eff.target == "self_creature":
                chk = require(
                    target is not None and target.kind == "creature" and target.player == player,
                    "Target one of your creatures.",
                )
                if chk:
                    return chk
            elif eff.target == "any_creature":
                chk = require(target is not None and target.kind == "creature", "Target a creature.")
                if chk:
                    return chk
            assert target is not None and target.slot is not None
            ps = state.players[target.player]
            c = ps.board[target.slot]
            if c is not None:
                c.attack += eff.attack_delta
                c.health += eff.health_delta
                state.event_log.append(
                    {
                        "type": "BUFF_APPLIED",
                        "player": target.player,
                        "slot": target.slot,
                        "attack_delta": eff.attack_delta,
                        "health_delta": eff.health_delta,
                    }
                )

        elif isinstance(eff, SummonEffect):
            for _ in range(max(0, eff.count)):
                slot = _find_empty_slot(state.players[player].board)
                if slot is None:
                    break
                token_def = state.cards.get(eff.token_card_id)
                if token_def.creature_stats is None:
                    continue
                inst = CreatureInstance(
                    card_id=eff.token_card_id,
                    attack=token_def.creature_stats.attack,
                    health=token_def.creature_stats.health,
                    keywords=frozenset(token_def.keywords),
                    summoning_sick=True,
                    has_attacked=False,
                )
                # Tokens can have haste too, if defined.
                if inst.has("Haste"):
                    inst.summoning_sick = False
                state.players[player].board[slot] = inst
                state.event_log.append(
                    {"type": "CREATURE_SUMMONED", "player": player, "slot": slot, "card_id": inst.card_id}
                )

    _remove_dead(state)
    _check_winner(state)
    events.extend(state.event_log[-10:])  # small tail for immediate UI usage
    return StepResult(ok=True, events=events)


def _play_card(state: MatchState, action: PlayCardAction) -> StepResult:
    if action.player != state.current_player:
        return StepResult(ok=False, events=[], error="Not your turn.")
    ps = state.players[action.player]
    if action.hand_index < 0 or action.hand_index >= len(ps.hand):
        return StepResult(ok=False, events=[], error="Invalid hand index.")

    card_id = ps.hand[action.hand_index]
    card = state.cards.get(card_id)

    if card.cost > ps.energy:
        return StepResult(ok=False, events=[], error="Not enough energy.")

    if card.type == "creature":
        slot = _find_empty_slot(ps.board)
        if slot is None:
            return StepResult(ok=False, events=[], error="Board is full.")
        if card.creature_stats is None:
            return StepResult(ok=False, events=[], error="Invalid creature definition.")
        # Pay + remove from hand
        ps.energy -= card.cost
        ps.hand.pop(action.hand_index)
        inst = CreatureInstance(
            card_id=card_id,
            attack=card.creature_stats.attack,
            health=card.creature_stats.health,
            keywords=frozenset(card.keywords),
            summoning_sick=True,
            has_attacked=False,
        )
        if inst.has("Haste"):
            inst.summoning_sick = False
        ps.board[slot] = inst
        state.event_log.append({"type": "CARD_PLAYED", "player": action.player, "card_id": card_id})
        state.event_log.append(
            {"type": "CREATURE_SUMMONED", "player": action.player, "slot": slot, "card_id": card_id}
        )
        _check_winner(state)
        return StepResult(ok=True, events=state.event_log[-5:])

    # Spell
    ps.energy -= card.cost
    ps.hand.pop(action.hand_index)
    ps.discard.append(card_id)
    state.event_log.append({"type": "CARD_PLAYED", "player": action.player, "card_id": card_id})
    result = _resolve_spell(state, action.player, card, action.target)
    if not result.ok:
        # Rollback-like behavior for V1: if spell targeting fails, undo the play.
        # This keeps the UI forgiving and reduces "lost card" edge cases.
        ps.energy += card.cost
        ps.hand.insert(action.hand_index, card_id)
        ps.discard.pop()
        # Also remove the CARD_PLAYED event we just appended
        if state.event_log and state.event_log[-1].get("type") == "CARD_PLAYED":
            state.event_log.pop()
    return result


def _attack(state: MatchState, action: AttackAction) -> StepResult:
    if action.player != state.current_player:
        return StepResult(ok=False, events=[], error="Not your turn.")
    ps = state.players[action.player]
    if action.attacker_slot < 0 or action.attacker_slot >= len(ps.board):
        return StepResult(ok=False, events=[], error="Invalid attacker slot.")
    attacker = ps.board[action.attacker_slot]
    if attacker is None:
        return StepResult(ok=False, events=[], error="No creature in that slot.")
    if attacker.summoning_sick:
        return StepResult(ok=False, events=[], error="Summoning sickness.")
    if attacker.has_attacked:
        return StepResult(ok=False, events=[], error="Already attacked.")

    valid_targets = _valid_attack_targets(state, action.player)
    if action.target not in valid_targets:
        return StepResult(ok=False, events=[], error="Invalid target (Guard rule?).")

    enemy = state.opponent(action.player)

    if action.target.kind == "player":
        dealt = _damage_player(state, enemy, attacker.attack)
        if attacker.has("Lifesteal") and dealt > 0:
            _heal_player(state, action.player, dealt)
        attacker.has_attacked = True
        state.event_log.append(
            {
                "type": "ATTACK_PLAYER",
                "player": action.player,
                "attacker_slot": action.attacker_slot,
                "amount": attacker.attack,
                "dealt": dealt,
            }
        )
        _check_winner(state)
        return StepResult(ok=True, events=state.event_log[-6:])

    # creature vs creature
    assert action.target.slot is not None
    def_slot = action.target.slot
    dps = state.players[enemy]
    defender = dps.board[def_slot]
    if defender is None:
        return StepResult(ok=False, events=[], error="Target creature missing.")
    # record before for lifesteal (actual damage dealt)
    damage_to_def = attacker.attack
    damage_to_att = defender.attack

    dealt = _damage_creature(state, enemy, def_slot, damage_to_def)
    dealt_back = _damage_creature(state, action.player, action.attacker_slot, damage_to_att)

    if attacker.has("Lifesteal"):
        _heal_player(state, action.player, dealt)

    attacker.has_attacked = True
    state.event_log.append(
        {
            "type": "ATTACK_CREATURE",
            "player": action.player,
            "attacker_slot": action.attacker_slot,
            "defender_slot": def_slot,
        }
    )
    _remove_dead(state)
    _check_winner(state)
    return StepResult(ok=True, events=state.event_log[-10:])


def _end_turn(state: MatchState, action: EndTurnAction) -> StepResult:
    if action.player != state.current_player:
        return StepResult(ok=False, events=[], error="Not your turn.")
    state.event_log.append({"type": "TURN_ENDED", "player": action.player})
    state.current_player = state.opponent(state.current_player)
    _start_turn(state, state.current_player)
    return StepResult(ok=True, events=state.event_log[-5:])


def step(state: MatchState, action: Action) -> StepResult:
    """Apply a single action to the match state.

    This mutates `state` in-place but remains deterministic for a given
    (seed, initial decks, action sequence).
    """
    if state.winner is not None:
        return StepResult(ok=False, events=[], error="Match already ended.")

    # Log first — so replay has a full record of attempted actions
    state.action_log.append(action)

    if isinstance(action, PlayCardAction):
        return _play_card(state, action)
    if isinstance(action, AttackAction):
        return _attack(state, action)
    if isinstance(action, EndTurnAction):
        return _end_turn(state, action)
    return StepResult(ok=False, events=[], error="Unknown action.")


def new_match(
    cards: CardDatabase,
    deck0: Sequence[str],
    deck1: Sequence[str],
    seed: int,
    config: MatchConfig | None = None,
) -> MatchState:
    cfg = config or MatchConfig()
    if len(deck0) != cfg.deck_size or len(deck1) != cfg.deck_size:
        raise ValueError(f"Decks must be exactly {cfg.deck_size} cards.")

    rng = random.Random(seed)
    d0 = list(deck0)
    d1 = list(deck1)
    _shuffle(rng, d0)
    _shuffle(rng, d1)

    p0 = PlayerState(
        health=cfg.starting_health,
        energy_max=0,
        energy=0,
        deck=d0,
        hand=[],
        board=[None for _ in range(cfg.board_slots)],
    )
    p1 = PlayerState(
        health=cfg.starting_health,
        energy_max=0,
        energy=0,
        deck=d1,
        hand=[],
        board=[None for _ in range(cfg.board_slots)],
    )

    state = MatchState(cards=cards, config=cfg, seed=seed, rng=rng, players=[p0, p1])
    # Starting hands
    for _ in range(cfg.starting_hand):
        _draw_one(state, 0)
        _draw_one(state, 1)

    # Start player 0's turn (no extra draw on first turn)
    _start_turn(state, 0)
    state.current_player = 0
    return state


def replay(
    cards: CardDatabase,
    deck0: Sequence[str],
    deck1: Sequence[str],
    seed: int,
    actions: Iterable[Action],
    config: MatchConfig | None = None,
) -> MatchState:
    state = new_match(cards=cards, deck0=deck0, deck1=deck1, seed=seed, config=config)
    for a in actions:
        step(state, a)
        if state.winner is not None:
            break
    return state


def get_valid_attack_targets(state: MatchState, attacker_player: int) -> list[TargetRef]:
    return _valid_attack_targets(state, attacker_player)
