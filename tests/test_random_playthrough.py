import random

import pyspiel
import pytest
import sevenwonders_dice  # noqa: F401


def _play_random_game(game, rng):
  state = game.new_initial_state()
  steps = 0
  max_steps = 20000
  while not state.is_terminal():
    steps += 1
    assert steps < max_steps, "game did not terminate: " + str(state)
    if state.is_chance_node():
      outcomes, probs = zip(*state.chance_outcomes())
      action = rng.choices(outcomes, weights=probs, k=1)[0]
      state.apply_action(action)
    elif state.current_player() == pyspiel.PlayerId.SIMULTANEOUS:
      actions = [
          rng.choice(state.legal_actions(p))
          for p in range(game.num_players())
      ]
      state.apply_actions(actions)
    else:
      player = state.current_player()
      action = rng.choice(state.legal_actions(player))
      state.apply_action(action)
  return state


@pytest.mark.parametrize("num_players", [2, 3, 4, 7])
def test_random_playthrough_terminates_and_scores(num_players):
  rng = random.Random(1234 + num_players)
  game = pyspiel.load_game("python_seven_wonders_dice", {"players": num_players})
  for _ in range(3):
    state = _play_random_game(game, rng)
    returns = state.returns()
    assert len(returns) == num_players
    # Victory points can't be negative and a full game realistically stays
    # well under this ceiling given the boards' space counts.
    assert all(0.0 <= r < 200.0 for r in returns)


def test_many_short_random_games_no_crash():
  rng = random.Random(42)
  game = pyspiel.load_game("python_seven_wonders_dice", {"players": 3})
  for _ in range(15):
    _play_random_game(game, rng)
