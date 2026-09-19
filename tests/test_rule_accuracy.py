"""Integration tests for the rule simplifications resolved into exact
rules: Agora's 2 gated symbol-group tracks, Market's real per-space choice
(not auto-pick-cheapest), CROSS_SPACE_ONE_OF and every other ambiguous
"cross a space of X" resolution (Spy/Barracks/University) as real player
choices, and the University-unlock die swap as a genuine, correctly-timed
chance node.
"""

import pyspiel
import sevenwonders_dice  # noqa: F401
from sevenwonders_dice.constants import BuildingKind, DieColor
from sevenwonders_dice.state import ACTION_BUILD_BASE, ACTION_MARKET_BASE, ACTION_PASS

GREY_FORUM_INDEX = 0
BLUE_FORUM_INDEX = 3  # STARTING_DICE = (GREY,GREY,GREY,BLUE,RED,YELLOW,GREEN)
YELLOW_FORUM_INDEX = 5


def _deal_in_order(state, num_players):
  for _ in range(num_players):
    state.apply_action(0)  # always take the first remaining board


def _shake_all(state, forced_actions=None):
  forced_actions = forced_actions or {}
  for die_idx in range(7):
    state.apply_action(forced_actions.get(die_idx, 0))


def test_agora_two_symbol_groups_are_independently_gated():
  """Rolling the *same* blue-die symbol group twice must advance that
  group's own track twice, never spill into the other group's spaces --
  the bug the single-sequence simplification had (see RULES.md)."""
  game = pyspiel.load_game("python_seven_wonders_dice", {"players": 2})
  state = game.new_initial_state()
  _deal_in_order(state, 2)

  blue_action = ACTION_BUILD_BASE + BLUE_FORUM_INDEX
  for _ in range(2):
    # Blue die face index 0 -> agora_group 0 (dice.py: group = i % 2).
    _shake_all(state, {BLUE_FORUM_INDEX: 0})
    state.apply_actions([blue_action, ACTION_PASS])

  p0 = state._players[0]
  assert p0.agora_group_progress == {0: 2, 1: 0}
  # 2 group-0 crossings must cross group-0's own 1st and 2nd spaces (board
  # indices 0 and 2, since spaces alternate group 0/1/0/1/...), and *not*
  # group-1's space (index 1) even though a naive "2 spaces done" count
  # would otherwise land there.
  assert p0.agora_space_crossed(0) and p0.agora_space_crossed(2)
  assert not p0.agora_space_crossed(1)
  assert not p0.agora_space_crossed(4)


def test_market_can_pick_any_open_space_not_just_cheapest():
  """Building Market via the Yellow die must let the player choose *which*
  open space to fill (rulebook: fillable in any order), not silently
  auto-pick the cheapest one."""
  game = pyspiel.load_game("python_seven_wonders_dice", {"players": 2})
  state = game.new_initial_state()
  _deal_in_order(state, 2)
  _shake_all(state)

  legal = state.legal_actions(0)
  market_actions = [a for a in legal if a >= ACTION_MARKET_BASE]
  assert len(market_actions) == 6  # all 6 spaces affordable with 7 coins

  # Space #5 (index 5, 0-based) is the most expensive (cost 3) and carries
  # a flat +4 VP -- pick it explicitly instead of the cheapest (index 0/1).
  chosen = ACTION_MARKET_BASE + 5
  state.apply_actions([chosen, ACTION_PASS])

  p0 = state._players[0]
  assert p0.market_crossed_mask == (1 << 5)
  assert p0.coins == 7 - 3  # die cost 0 (quadrant 0) + space cost 3
  assert p0.total_end_game_vp() == 4


def _build_via_die(state, player, die_idx, other_players):
  actions = [ACTION_PASS] * state.num_players()
  actions[player] = ACTION_BUILD_BASE + die_idx
  for p in other_players:
    actions[p] = ACTION_PASS
  state.apply_actions(actions)


def test_cross_space_one_of_is_a_real_choice_not_a_fixed_order():
  """Completing Warehouse (6/6 spaces) and picking the standard bonus slot
  whose effect is CROSS_SPACE_ONE_OF(Warehouse, Agora, Market) must offer a
  real choice between Agora and Market (Warehouse is already full, so it's
  correctly excluded) -- not silently resolve to a fixed preference."""
  game = pyspiel.load_game("python_seven_wonders_dice", {"players": 2})
  state = game.new_initial_state()
  _deal_in_order(state, 2)

  for _ in range(6):  # Warehouse costs (0,0,0,1,1,1); grey die is always free
    _shake_all(state)
    _build_via_die(state, 0, GREY_FORUM_INDEX, [1])

  p0 = state._players[0]
  assert p0.building_progress(BuildingKind.WAREHOUSE) == 6
  assert state._phase == "BONUS"
  assert state.current_player() == 0

  # Slot #1 (0-based) is the standard CROSS_SPACE_ONE_OF(Warehouse, Agora,
  # Market) bonus (see boards.py: _standard_bonus_slots).
  state.apply_action(1)

  kind, buildings = p0.pending_bonus_actions[0]
  assert kind == "CROSS_ONE_OF"
  assert buildings == (BuildingKind.WAREHOUSE, BuildingKind.AGORA,
                        BuildingKind.MARKET)

  legal = state.legal_actions(0)
  # index 0 (Warehouse) is excluded: it's already fully built.
  assert legal == [1, 2]

  state.apply_action(1)  # choose Agora (index 1 in the tuple above)

  # Agora itself is ambiguous (both symbol groups are fresh) -> choosing it
  # queues a *further* real choice (which group), it doesn't silently
  # resolve to one -- the same "always ask, never guess" rule applied one
  # level deeper.
  kind2, (building2, times2) = p0.pending_bonus_actions[0]
  assert kind2 == "CROSS_SPACE"
  assert building2 == BuildingKind.AGORA
  assert times2 == 1
  assert state.legal_actions(0) == [0, 1]  # group A, group B

  state.apply_action(1)  # group B (board index 1, cost 1, 2VP)
  assert p0.building_progress(BuildingKind.AGORA) == 1
  assert p0.agora_group_progress == {0: 0, 1: 1}
  assert p0.building_progress(BuildingKind.MARKET) == 0


def test_spy_black_die_ambiguous_barracks_target_is_a_real_choice():
  """The Spy (Black) die's face can target a Barracks side generically;
  since there's no clear photo confirming the physical rule always means
  attack, a real attack-vs-defense choice is exposed instead of guessing
  (see RULES.md) -- consistent with every other ambiguous target."""
  game = pyspiel.load_game("python_seven_wonders_dice", {"players": 2})
  state = game.new_initial_state()
  _deal_in_order(state, 2)

  black_idx = GREY_FORUM_INDEX  # hijack a Grey slot directly for this test
  state._forum_colors[black_idx] = DieColor.BLACK
  state._players[0].unlocked_by_me.add(DieColor.BLACK)
  # Black face index 2 = BARRACKS_WEST (dice.py FACES[BLACK] order:
  # WAREHOUSE, AGORA, BARRACKS_WEST, BARRACKS_EAST, MARKET, UNIVERSITY).
  _shake_all(state, {black_idx: 2 * 4 + 0})

  black_action = ACTION_BUILD_BASE + black_idx
  assert black_action in state.legal_actions(0)
  state.apply_actions([black_action, ACTION_PASS])

  p0 = state._players[0]
  assert state._phase == "BONUS"
  kind, (building, times) = p0.pending_bonus_actions[0]
  assert kind == "CROSS_SPACE"
  assert building == BuildingKind.BARRACKS_WEST
  assert times == 1
  assert state.legal_actions(0) == [0, 1]  # 0=attack, 1=defense

  state.apply_action(1)  # choose defense
  assert p0.barracks_w_defense == 1
  assert p0.barracks_w_attack == 0


def test_university_unlock_is_a_deferred_random_chance_node():
  """Unlocking a special die must not swap it into the Forum immediately
  (mid-round) -- only via a genuine chance node right before the *next*
  SHAKE, matching the physical game (dice can only be swapped between
  rounds) and giving "which grey slot" a real, fair random pick instead of
  a hardcoded one."""
  game = pyspiel.load_game("python_seven_wonders_dice", {"players": 2})
  state = game.new_initial_state()
  _deal_in_order(state, 2)
  _shake_all(state)

  p0 = state._players[0]
  # Invoke the effect directly -- actually playing to a University unlock
  # space would take many rounds; the unlock plumbing itself is what's
  # under test.
  state.unlock_special_die(p0, DieColor.BLACK)

  assert DieColor.BLACK in p0.unlocked_by_me
  assert DieColor.BLACK not in state._forum_colors  # not swapped in yet
  assert state._pending_unlocks == [DieColor.BLACK]

  state.apply_actions([ACTION_PASS, ACTION_PASS])  # finish the round

  assert state._phase == "UNLOCK_CHANCE"
  assert state.is_chance_node()
  outcomes = state.chance_outcomes()
  assert len(outcomes) == 3  # all 3 starting Grey dice still available

  action, _prob = outcomes[1]
  state.apply_action(action)

  assert DieColor.BLACK in state._forum_colors
  assert state._pending_unlocks == []
  assert state._phase == "SHAKE"
