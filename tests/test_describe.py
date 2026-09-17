"""Regression coverage for the human-readable action/effect text used by
app.py (and generally handy for debugging)."""

import random

import pyspiel
import sevenwonders_dice  # noqa: F401
from sevenwonders_dice.bots.base import advance_through_chance_nodes
from sevenwonders_dice.state import ACTION_PASS


def test_legal_action_descriptions_cover_every_legal_action():
  rng = random.Random(0)
  game = pyspiel.load_game("python_seven_wonders_dice", {"players": 2})
  state = game.new_initial_state()
  advance_through_chance_nodes(state, rng)

  pairs = state.legal_action_descriptions(0)
  assert [a for a, _ in pairs] == state.legal_actions(0)
  descriptions = dict(pairs)
  assert descriptions[ACTION_PASS] == "Pass (+3 coins)"
  assert all(isinstance(d, str) and d for d in descriptions.values())


def test_describe_action_does_not_crash_across_a_random_game():
  # Cheap smoke test: every action ever offered during a full random game
  # (across both ACTION and BONUS decision points) must describe cleanly.
  rng = random.Random(7)
  game = pyspiel.load_game("python_seven_wonders_dice", {"players": 2})
  state = game.new_initial_state()
  advance_through_chance_nodes(state, rng)

  steps = 0
  while not state.is_terminal() and steps < 5000:
    steps += 1
    if state.current_player() == pyspiel.PlayerId.SIMULTANEOUS:
      actions = []
      for p in range(2):
        legal = state.legal_actions(p)
        for a in legal:
          state.describe_action(p, a)  # must not raise
        actions.append(rng.choice(legal))
      state.apply_actions(actions)
    else:
      p = state.current_player()
      legal = state.legal_actions(p)
      for a in legal:
        state.describe_action(p, a)
      state.apply_action(rng.choice(legal))
    advance_through_chance_nodes(state, rng)
