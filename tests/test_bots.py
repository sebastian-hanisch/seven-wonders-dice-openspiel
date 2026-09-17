"""Bot sanity checks. Kept deliberately cheap (tiny rollout budgets, few
games) so CI stays fast -- see examples/evaluate_bots.py for a real
tournament-strength comparison.
"""

import random

import pyspiel
import sevenwonders_dice  # noqa: F401
from sevenwonders_dice.bots import HeuristicBot, RandomBot, SearchBot, play_full_game


def test_random_bot_always_legal_and_finishes():
  rng = random.Random(0)
  game = pyspiel.load_game("python_seven_wonders_dice", {"players": 2})
  bots = [RandomBot(rng), RandomBot(rng)]
  state = play_full_game(game, bots, rng)
  assert state.is_terminal()
  assert len(state.returns()) == 2


def test_heuristic_bot_always_legal_and_finishes():
  rng = random.Random(0)
  game = pyspiel.load_game("python_seven_wonders_dice", {"players": 2})
  bots = [HeuristicBot(), HeuristicBot()]
  state = play_full_game(game, bots, rng)
  assert state.is_terminal()


def test_heuristic_bot_builds_more_than_it_passes():
  # Regression test for a real bug found while evaluating this bot: an
  # earlier weighting valued the guaranteed +3 coins from passing over
  # building progress, so the bot passed ~70% of the time instead of
  # building a city. It should now build far more often than it passes.
  from sevenwonders_dice.bots.base import advance_through_chance_nodes
  from sevenwonders_dice.state import ACTION_PASS

  rng = random.Random(3)
  game = pyspiel.load_game("python_seven_wonders_dice", {"players": 2})
  bot = HeuristicBot()
  state = game.new_initial_state()
  advance_through_chance_nodes(state, rng)

  passes, builds, decisions = 0, 0, 0
  while not state.is_terminal() and decisions < 20:
    if state.current_player() == pyspiel.PlayerId.SIMULTANEOUS:
      actions = []
      for p in range(2):
        a = bot.step(state, p)
        actions.append(a)
        if a == ACTION_PASS:
          passes += 1
        else:
          builds += 1
      state.apply_actions(actions)
    else:
      p = state.current_player()
      state.apply_action(bot.step(state, p))
    advance_through_chance_nodes(state, rng)
    decisions += 1

  assert builds > passes


def test_heuristic_bot_beats_random_bot_on_average():
  rng = random.Random(11)
  game = pyspiel.load_game("python_seven_wonders_dice", {"players": 2})
  heuristic_wins = 0
  num_games = 6
  for _ in range(num_games):
    bots = [RandomBot(rng), HeuristicBot()]
    state = play_full_game(game, bots, rng)
    returns = state.returns()
    if returns[1] > returns[0]:
      heuristic_wins += 1
  # Not every single game (variance from the dice), but a clear majority.
  assert heuristic_wins >= num_games - 1


def test_search_bot_always_legal_and_finishes_with_tiny_budget():
  rng = random.Random(0)
  game = pyspiel.load_game("python_seven_wonders_dice", {"players": 2})
  bots = [RandomBot(rng), SearchBot(num_rollouts=4, horizon_decisions=2, rng=rng)]
  state = play_full_game(game, bots, rng)
  assert state.is_terminal()


def test_search_bot_prefers_the_higher_scoring_simulated_action():
  # Cheap, deterministic unit test of the bandit itself rather than a full
  # game: with a rollout budget big enough to try every arm many times and
  # a fixed rng, it should consistently prefer an action a stub rollout
  # policy scores strictly higher than the alternatives.
  class _StubPolicy:
    """Always passes -- makes _simulate's outcome depend almost entirely
    on the root action, so the bandit's preference is unambiguous."""

    def step(self, state, player):
      from sevenwonders_dice.state import ACTION_PASS
      return ACTION_PASS

  rng = random.Random(0)
  game = pyspiel.load_game("python_seven_wonders_dice", {"players": 2})
  from sevenwonders_dice.bots.base import advance_through_chance_nodes
  state = game.new_initial_state()
  advance_through_chance_nodes(state, rng)

  bot = SearchBot(num_rollouts=20, horizon_decisions=1,
                   rollout_policy=_StubPolicy(), rng=rng)
  action = bot.step(state, 0)
  legal = state.legal_actions(0)
  assert action in legal

  from sevenwonders_dice.state import ACTION_PASS
  if ACTION_PASS in legal and len(legal) > 1:
    # With horizon_decisions=1 the simulated return *is* the immediate
    # post-root-action snapshot (VP + coins + resources + progress -- see
    # heuristic_bot.snapshot_value), so the bandit should reliably prefer
    # any building/wonder move over an all-PASS root action.
    assert action != ACTION_PASS
