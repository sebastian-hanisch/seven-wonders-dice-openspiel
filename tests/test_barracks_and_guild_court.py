"""Integration tests driving the real state machine for the two trickiest
formulas: Barracks attack-minus-defense VP, and Guild Court's
compare-to-neighbors gating (incl. the 2-player "strictly greater" case).
"""

import pyspiel
import sevenwonders_dice  # noqa: F401
from sevenwonders_dice.constants import BuildingKind
from sevenwonders_dice.state import ACTION_BUILD_BASE, ACTION_PASS

RED_FORUM_INDEX = 4  # STARTING_DICE = (GREY,GREY,GREY,BLUE,RED,YELLOW,GREEN)
# DieColor.RED faces (see dice.py): index 1 = West attack, quadrant 0 = free.
WEST_ATTACK_ACTION = ACTION_BUILD_BASE + RED_FORUM_INDEX
WEST_ATTACK_SHAKE_ACTION = 1 * 4 + 0


def _deal_in_order(state, num_players):
  for _ in range(num_players):
    state.apply_action(0)  # always take the first remaining board


def _shake_all(state, forced_actions=None):
  forced_actions = forced_actions or {}
  for die_idx in range(7):
    state.apply_action(forced_actions.get(die_idx, 0))


def test_barracks_attack_minus_defense_vp():
  game = pyspiel.load_game("python_seven_wonders_dice", {"players": 4})
  state = game.new_initial_state()
  _deal_in_order(state, 4)
  _shake_all(state, {RED_FORUM_INDEX: WEST_ATTACK_SHAKE_ACTION})

  assert state.current_player() == pyspiel.PlayerId.SIMULTANEOUS
  actions = [ACTION_PASS] * 4
  actions[0] = WEST_ATTACK_ACTION  # player 0 attacks their left neighbor (3)
  state.apply_actions(actions)

  p0 = state._players[0]
  p3 = state._players[3]
  assert p0.barracks_w_attack == 1
  # Space 0's printed VP is 2 (see boards.py _standard_barracks); target had
  # 0 defense crossed, so the full printed VP is granted.
  assert p0.barracks_vp_total == 2
  assert p3.barracks_e_defense == 0  # untouched; sanity check on the setup


def test_guild_court_two_player_requires_strictly_more():
  game = pyspiel.load_game("python_seven_wonders_dice", {"players": 2})
  state = game.new_initial_state()
  _deal_in_order(state, 2)
  _shake_all(state)

  p0, p1 = state._players
  # Equal counts (both 0) -> the purple-die condition should not be met.
  assert not state._guild_court_condition_met(p0, BuildingKind.WAREHOUSE)
  p0.warehouse_crossed = 1
  assert state._guild_court_condition_met(p0, BuildingKind.WAREHOUSE)
  assert not state._guild_court_condition_met(p1, BuildingKind.WAREHOUSE)


def test_guild_court_multiplayer_requires_at_least_both_neighbors():
  game = pyspiel.load_game("python_seven_wonders_dice", {"players": 3})
  state = game.new_initial_state()
  _deal_in_order(state, 3)
  _shake_all(state)

  p0, p1, p2 = state._players
  p0.warehouse_crossed = 2
  p1.warehouse_crossed = 2
  p2.warehouse_crossed = 3
  # p0 ties p1 but is behind p2 -> condition fails (must be >= both).
  assert not state._guild_court_condition_met(p0, BuildingKind.WAREHOUSE)
  p0.warehouse_crossed = 3
  assert state._guild_court_condition_met(p0, BuildingKind.WAREHOUSE)
