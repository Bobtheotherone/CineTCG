from __future__ import annotations

from dataclasses import dataclass

from .actions import AttackAction, EndTurnAction, PlayCardAction, TargetRef
from .match import MatchState, get_valid_attack_targets, get_valid_targets_for_play, step
from .types import BuffEffect, CardDefinition, DamageEffect, DrawEffect, HealEffect, SummonEffect


@dataclass(frozen=True)
class AISpec:
    """Simple AI tuning parameters.

    difficulty:
      0 = easy (makes mistakes)
      1 = normal
      2 = hard (plays greedier + fewer mistakes)
    """

    difficulty: int = 1


def _card_value(card: CardDefinition) -> float:
    if card.type == "creature":
        assert card.creature_stats is not None
        v = float(card.creature_stats.attack * 2 + card.creature_stats.health)
        if "Guard" in card.keywords:
            v += 1.5
        if "Haste" in card.keywords:
            v += 1.0
        if "Lifesteal" in card.keywords:
            v += 1.0
        return v

    # Spell: rough estimate from effects
    v = 0.0
    for eff in card.effects:
        if isinstance(eff, DamageEffect):
            v += float(eff.amount) * (2.0 if eff.target != "enemy_player" else 1.2)
        elif isinstance(eff, HealEffect):
            v += float(eff.amount) * 0.9
        elif isinstance(eff, DrawEffect):
            v += float(eff.count) * 1.4
        elif isinstance(eff, BuffEffect):
            v += float(eff.attack_delta * 1.8 + eff.health_delta * 1.2)
        elif isinstance(eff, SummonEffect):
            v += float(eff.count) * 2.0
    return v


def _pick_best_play(state: MatchState, player: int, spec: AISpec) -> PlayCardAction | None:
    ps = state.players[player]
    best: tuple[float, PlayCardAction] | None = None

    for idx, card_id in enumerate(ps.hand):
        card = state.cards.get(card_id)
        if card.cost > ps.energy:
            continue
        if card.type == "creature":
            # board space needed
            if all(c is not None for c in ps.board):
                continue
            score = _card_value(card)
            cand = PlayCardAction(player=player, hand_index=idx, target=None)
            if best is None or score > best[0]:
                best = (score, cand)
            continue

        # spells
        targets = get_valid_targets_for_play(state, player, card_id)
        if not targets:
            # no target required
            score = _card_value(card)
            cand = PlayCardAction(player=player, hand_index=idx, target=None)
            if best is None or score > best[0]:
                best = (score, cand)
            continue

        # pick a reasonable target
        chosen = _choose_spell_target(state, player, card, targets)
        if chosen is None:
            continue
        score = _card_value(card)
        cand = PlayCardAction(player=player, hand_index=idx, target=chosen)
        if best is None or score > best[0]:
            best = (score, cand)

    if best is None:
        return None

    # Difficulty-based mistakes (easy AI sometimes skips best play)
    if spec.difficulty <= 0:
        if state.rng.random() < 0.35:
            return None
    elif spec.difficulty == 1:
        if state.rng.random() < 0.10:
            return None
    return best[1]


def _choose_spell_target(
    state: MatchState, player: int, card: CardDefinition, targets: list[TargetRef]
) -> TargetRef | None:
    enemy = state.opponent(player)
    # Prefer enemy creatures for damage spells, own player for heals, strongest ally for buffs
    for eff in card.effects:
        if isinstance(eff, DamageEffect):
            if eff.target in ("enemy_creature", "any"):
                # pick highest-attack enemy creature if possible
                best_t: TargetRef | None = None
                best_attack = -1
                for t in targets:
                    if t.kind != "creature" or t.player != enemy or t.slot is None:
                        continue
                    c = state.players[enemy].board[t.slot]
                    if c is None:
                        continue
                    if c.attack > best_attack:
                        best_attack = c.attack
                        best_t = t
                if best_t is not None:
                    return best_t
            if eff.target in ("enemy_player", "any"):
                return TargetRef.player_target(enemy)

        if isinstance(eff, HealEffect) and eff.target == "self_player":
            return None  # no target needed
        if isinstance(eff, HealEffect) and eff.target == "self_creature":
            # heal lowest health ally
            ps = state.players[player]
            best_t = None
            best_hp = 10**9
            for t in targets:
                if t.kind != "creature" or t.player != player or t.slot is None:
                    continue
                c = ps.board[t.slot]
                if c is None:
                    continue
                if c.health < best_hp:
                    best_hp = c.health
                    best_t = t
            return best_t

        if isinstance(eff, BuffEffect):
            # buff highest attack ally (or any creature if any_creature)
            best_t = None
            best_atk = -1
            for t in targets:
                if t.kind != "creature" or t.slot is None:
                    continue
                if eff.target == "self_creature" and t.player != player:
                    continue
                c = state.players[t.player].board[t.slot]
                if c is None:
                    continue
                if c.attack > best_atk:
                    best_atk = c.attack
                    best_t = t
            return best_t

    # fallback: pick first
    return targets[0] if targets else None


def _pick_attack(state: MatchState, player: int, spec: AISpec) -> AttackAction | None:
    ps = state.players[player]
    enemy = state.opponent(player)
    eps = state.players[enemy]
    for slot, c in enumerate(ps.board):
        if c is None:
            continue
        if c.summoning_sick or c.has_attacked:
            continue
        valid = get_valid_attack_targets(state, player)

        # If must hit guard, pick lowest-health guard
        guard_targets = [t for t in valid if t.kind == "creature" and t.player == enemy]
        if guard_targets:
            best_t = None
            best_hp = 10**9
            for t in guard_targets:
                assert t.slot is not None
                ec = eps.board[t.slot]
                if ec is None:
                    continue
                if ec.health < best_hp:
                    best_hp = ec.health
                    best_t = t
            if best_t is not None:
                if spec.difficulty <= 0 and state.rng.random() < 0.25:
                    return None
                return AttackAction(player=player, attacker_slot=slot, target=best_t)

        # Otherwise look for favorable trade
        best_trade: tuple[int, TargetRef] | None = None
        for t in valid:
            if t.kind != "creature" or t.slot is None:
                continue
            dc = eps.board[t.slot]
            if dc is None:
                continue
            # Favorable trade: kill without dying
            kills = c.attack >= dc.health
            survives = c.health > dc.attack
            if kills and survives:
                score = dc.attack  # take out biggest threats
                if best_trade is None or score > best_trade[0]:
                    best_trade = (score, t)
        if best_trade is not None:
            if spec.difficulty <= 0 and state.rng.random() < 0.25:
                return None
            return AttackAction(player=player, attacker_slot=slot, target=best_trade[1])

        # else face if allowed
        face = TargetRef.player_target(enemy)
        if face in valid:
            if spec.difficulty <= 0 and state.rng.random() < 0.25:
                return None
            return AttackAction(player=player, attacker_slot=slot, target=face)

        # otherwise first valid creature
        for t in valid:
            if t.kind == "creature":
                if spec.difficulty <= 0 and state.rng.random() < 0.25:
                    return None
                return AttackAction(player=player, attacker_slot=slot, target=t)
    return None


def ai_take_turn(state: MatchState, player: int, spec: AISpec | None = None) -> None:
    """Advance the match through the AI player's turn.

    The AI uses the engine RNG (`state.rng`) so it remains deterministic for a given seed.
    """
    spec = spec or AISpec()
    while state.winner is None and state.current_player == player:
        play = _pick_best_play(state, player, spec)
        if play is not None:
            step(state, play)
            continue
        atk = _pick_attack(state, player, spec)
        if atk is not None:
            step(state, atk)
            continue
        step(state, EndTurnAction(player=player))
        break
