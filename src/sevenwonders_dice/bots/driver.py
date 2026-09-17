"""Shared game-loop driving logic, used by both evaluate_bots.py and
SearchBot's internal rollouts."""

import pyspiel

from sevenwonders_dice.bots.base import advance_through_chance_nodes


def step_one_decision(state, bots, rng) -> None:
  """Applies exactly one decision (all players' picks at a SIMULTANEOUS
  node, or one player's pick at a sequential BONUS node), then advances
  through any chance nodes that follow. Assumes `state` is already at a
  decision node (not chance, not terminal) -- call
  `advance_through_chance_nodes` first if unsure.
  """
  if state.current_player() == pyspiel.PlayerId.SIMULTANEOUS:
    actions = [bots[p].step(state, p) for p in range(len(bots))]
    state.apply_actions(actions)
  else:
    player = state.current_player()
    state.apply_action(bots[player].step(state, player))
  advance_through_chance_nodes(state, rng)


def play_full_game(game, bots, rng):
  """Plays one game to completion with `bots[p]` acting for player p.
  Returns the terminal state (use `.returns()` for final utilities).
  """
  state = game.new_initial_state()
  advance_through_chance_nodes(state, rng)
  while not state.is_terminal():
    step_one_decision(state, bots, rng)
  return state
