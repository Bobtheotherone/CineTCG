from __future__ import annotations

from cinetcg.engine.actions import AttackAction, EndTurnAction, PlayCardAction, TargetRef
from cinetcg.engine.match import new_match
from cinetcg.paths import get_paths
from cinetcg.services.content import ContentService


def _load_cards():
    paths = get_paths()
    content = ContentService(paths.data_dir, paths.schema_dir)
    return content.load_cards_db()


def test_energy_ramp_and_refresh() -> None:
    cards = _load_cards()
    deck = ["street_extra"] * 30
    state = new_match(cards, deck, deck, seed=123)

    # Player 0 first turn
    p0 = state.players[0]
    assert p0.energy_max == 1
    assert p0.energy == 1
    assert len(p0.hand) == 5  # starting hand

    # End P0, start P1 first turn
    from cinetcg.engine.match import step
    step(state, EndTurnAction(player=0))
    p1 = state.players[1]
    assert p1.energy_max == 1
    assert p1.energy == 1
    assert len(p1.hand) == 5

    # End P1, start P0 second turn => energy 2 and draw 1
    step(state, EndTurnAction(player=1))
    p0 = state.players[0]
    assert p0.energy_max == 2
    assert p0.energy == 2
    assert len(p0.hand) == 6


def test_summoning_sickness_prevents_attack_same_turn() -> None:
    cards = _load_cards()
    deck = ["street_extra"] * 30
    state = new_match(cards, deck, deck, seed=1)

    from cinetcg.engine.match import step

    # Play creature (cost 1)
    res = step(state, PlayCardAction(player=0, hand_index=0))
    assert res.ok
    # Attempt to attack immediately should fail
    res2 = step(state, AttackAction(player=0, attacker_slot=0, target=TargetRef.player_target(1)))
    assert not res2.ok
    assert res2.error is not None
    assert "Summoning sickness" in res2.error


def test_haste_allows_attack_same_turn() -> None:
    cards = _load_cards()
    deck = ["stunt_driver"] * 30  # cost 3, haste
    state = new_match(cards, deck, deck, seed=2)
    from cinetcg.engine.match import step

    # advance to player 0 turn 3 (energy 3)
    step(state, EndTurnAction(player=0))
    step(state, EndTurnAction(player=1))
    step(state, EndTurnAction(player=0))
    step(state, EndTurnAction(player=1))
    assert state.current_player == 0
    assert state.players[0].energy_max == 3

    res = step(state, PlayCardAction(player=0, hand_index=0))
    assert res.ok
    # Haste creature should attack right away
    res2 = step(state, AttackAction(player=0, attacker_slot=0, target=TargetRef.player_target(1)))
    assert res2.ok


def test_guard_rule_forces_attacks() -> None:
    cards = _load_cards()
    deck0 = ["stunt_driver"] * 30  # haste attacker on turn 3
    deck1 = ["bodyguard"] * 30  # guard on turn 2
    state = new_match(cards, deck0, deck1, seed=3)
    from cinetcg.engine.match import step

    # Turn1 p0 end
    step(state, EndTurnAction(player=0))
    # Turn1 p1 end
    step(state, EndTurnAction(player=1))
    # Turn2 p0 end (can't play)
    step(state, EndTurnAction(player=0))
    # Turn2 p1 play guard then end
    res = step(state, PlayCardAction(player=1, hand_index=0))
    assert res.ok
    step(state, EndTurnAction(player=1))

    # Turn3 p0 play haste attacker
    res2 = step(state, PlayCardAction(player=0, hand_index=0))
    assert res2.ok

    # Cannot attack face while guard exists
    res3 = step(state, AttackAction(player=0, attacker_slot=0, target=TargetRef.player_target(1)))
    assert not res3.ok

    # Can attack guard creature (slot 0)
    res4 = step(state, AttackAction(player=0, attacker_slot=0, target=TargetRef.creature_target(1, 0)))
    assert res4.ok


def test_lifesteal_heals_player() -> None:
    cards = _load_cards()
    deck0 = ["vampire_actor"] * 30  # lifesteal 3/4 cost4
    deck1 = ["flashbang"] * 30  # damage any, cost2
    state = new_match(cards, deck0, deck1, seed=4)
    from cinetcg.engine.match import step

    # Turn1 p0 end
    step(state, EndTurnAction(player=0))
    # Turn1 p1 end
    step(state, EndTurnAction(player=1))
    # Turn2 p0 end
    step(state, EndTurnAction(player=0))
    # Turn2 p1 cast flashbang at player0 (deal 2)
    res = step(state, PlayCardAction(player=1, hand_index=0, target=TargetRef.player_target(0)))
    assert res.ok
    step(state, EndTurnAction(player=1))
    assert state.players[0].health == 18

    # Fast-forward to p0 turn4 (energy 4), play lifesteal creature
    # p0 turn3 end
    step(state, EndTurnAction(player=0))
    # p1 turn3 end
    step(state, EndTurnAction(player=1))
    # p0 turn4: play vampire actor
    assert state.current_player == 0
    assert state.players[0].energy_max == 4
    res2 = step(state, PlayCardAction(player=0, hand_index=0))
    assert res2.ok
    step(state, EndTurnAction(player=0))
    # p1 turn4 end
    step(state, EndTurnAction(player=1))

    # p0 turn5: attack face, heal 3 (capped to 20)
    assert state.current_player == 0
    res3 = step(state, AttackAction(player=0, attacker_slot=0, target=TargetRef.player_target(1)))
    assert res3.ok
    assert state.players[0].health == 20


def test_draw_spell_net_hand_increase() -> None:
    cards = _load_cards()
    deck = ["script_rewrite"] * 30  # draw 2, cost3
    state = new_match(cards, deck, deck, seed=5)
    from cinetcg.engine.match import step

    # advance to player 0 turn 3 (energy 3)
    step(state, EndTurnAction(player=0))
    step(state, EndTurnAction(player=1))
    step(state, EndTurnAction(player=0))
    step(state, EndTurnAction(player=1))
    assert state.players[0].energy_max == 3

    before_hand = len(state.players[0].hand)
    res = step(state, PlayCardAction(player=0, hand_index=0))
    assert res.ok
    after_hand = len(state.players[0].hand)
    assert after_hand == before_hand + 1  # -1 played +2 drawn
