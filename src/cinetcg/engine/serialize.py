from __future__ import annotations


from .actions import Action, AttackAction, EndTurnAction, PlayCardAction, TargetRef
from .match import CreatureInstance, MatchState, PlayerState


def _target_to_dict(t: TargetRef | None) -> dict[str, object] | None:
    if t is None:
        return None
    return {"kind": t.kind, "player": t.player, "slot": t.slot}


def action_to_dict(a: Action) -> dict[str, object]:
    if isinstance(a, PlayCardAction):
        return {
            "type": "play",
            "player": a.player,
            "hand_index": a.hand_index,
            "target": _target_to_dict(a.target),
        }
    if isinstance(a, AttackAction):
        return {
            "type": "attack",
            "player": a.player,
            "attacker_slot": a.attacker_slot,
            "target": _target_to_dict(a.target),
        }
    if isinstance(a, EndTurnAction):
        return {"type": "end_turn", "player": a.player}
    # should be unreachable
    return {"type": "unknown"}


def _creature_to_dict(c: CreatureInstance | None) -> dict[str, object] | None:
    if c is None:
        return None
    return {
        "card_id": c.card_id,
        "attack": c.attack,
        "health": c.health,
        "keywords": sorted(list(c.keywords)),
        "summoning_sick": c.summoning_sick,
        "has_attacked": c.has_attacked,
    }


def _player_to_dict(p: PlayerState) -> dict[str, object]:
    return {
        "health": p.health,
        "energy_max": p.energy_max,
        "energy": p.energy,
        "deck": list(p.deck),
        "hand": list(p.hand),
        "board": [_creature_to_dict(c) for c in p.board],
        "discard": list(p.discard),
        "turns_taken": p.turns_taken,
    }


def snapshot(state: MatchState) -> dict[str, object]:
    """Return a JSON-serializable canonical snapshot of the current match state."""
    return {
        "seed": state.seed,
        "current_player": state.current_player,
        "winner": state.winner,
        "players": [_player_to_dict(p) for p in state.players],
        "action_log": [action_to_dict(a) for a in state.action_log],
    }
