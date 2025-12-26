from __future__ import annotations

from cinetcg.engine.actions import EndTurnAction, PlayCardAction, TargetRef, AttackAction
from cinetcg.engine.match import new_match, replay, step, get_valid_targets_for_play, get_valid_attack_targets
from cinetcg.engine.serialize import snapshot
from cinetcg.paths import get_paths
from cinetcg.services.content import ContentService


def _load_cards():
    paths = get_paths()
    content = ContentService(paths.data_dir, paths.schema_dir)
    return content.load_cards_db()


def _choose_action(state) -> object:
    p = state.current_player
    ps = state.players[p]
    enemy = 1 - p

    # Prefer playable creature
    for i, cid in enumerate(ps.hand):
        card = state.cards.get(cid)
        if card.cost > ps.energy:
            continue
        if card.type == "creature":
            if any(slot is None for slot in ps.board):
                return PlayCardAction(player=p, hand_index=i, target=None)

    # Then spells
    for i, cid in enumerate(ps.hand):
        card = state.cards.get(cid)
        if card.cost > ps.energy:
            continue
        if card.type == "spell":
            targets = get_valid_targets_for_play(state, p, cid)
            if not targets:
                return PlayCardAction(player=p, hand_index=i, target=None)
            # deterministic choice: prefer enemy player if present
            ep = TargetRef.player_target(enemy)
            if ep in targets:
                return PlayCardAction(player=p, hand_index=i, target=ep)
            return PlayCardAction(player=p, hand_index=i, target=targets[0])

    # Then attacks
    for slot, c in enumerate(ps.board):
        if c is None or c.summoning_sick or c.has_attacked:
            continue
        targets = get_valid_attack_targets(state, p)
        # deterministic: prefer face if allowed
        face = TargetRef.player_target(enemy)
        tgt = face if face in targets else targets[0]
        return AttackAction(player=p, attacker_slot=slot, target=tgt)

    return EndTurnAction(player=p)


def test_engine_determinism_replay() -> None:
    cards = _load_cards()

    # Mixed decks so shuffling matters, but deterministic via seed.
    deck0 = (["street_extra"] * 15) + (["flashbang"] * 15)
    deck1 = (["camera_grip"] * 15) + (["healing_montage"] * 15)

    seed = 424242
    state1 = new_match(cards, deck0, deck1, seed=seed)

    actions = []
    for _ in range(20):
        if state1.winner is not None:
            break
        a = _choose_action(state1)
        actions.append(a)
        step(state1, a)

    snap1 = snapshot(state1)

    state2 = replay(cards, deck0, deck1, seed=seed, actions=actions)
    snap2 = snapshot(state2)

    assert snap1 == snap2
