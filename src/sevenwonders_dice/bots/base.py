"""Bot interface used by the bots in this package.

Deliberately *not* a `pyspiel.Bot` subclass: pyspiel.Bot is a pybind11
C++ base class meant mainly for wrapping native bots, and getting a pure
Python override to play nicely with it is more ceremony than it's worth
here. Instead this is a small duck-typed protocol that `examples/
evaluate_bots.py` (and `SearchBot`'s own rollouts) know how to drive
directly -- the same pattern `examples/random_sim.py` already uses for
plain random play.
"""

import abc


class Bot(abc.ABC):
  """A bot picks an action for `player` to take at `state`.

  `state` is always at a decision point for `player` when `step` is
  called: either a SIMULTANEOUS node (one call per player, each only
  supposed to look at information available to them -- but see the
  perfect-information note below) or a single-player sequential node
  (the BONUS phase).
  """

  name = "Bot"

  @abc.abstractmethod
  def step(self, state, player: int) -> int:
    """Returns the action `player` takes at `state`."""

  def restart(self) -> None:
    """Called between games; override if a bot keeps any game-local state."""


def sample_chance_action(state, rng):
  outcomes, probs = zip(*state.chance_outcomes())
  return rng.choices(outcomes, weights=probs, k=1)[0]


def advance_through_chance_nodes(state, rng) -> None:
  """Applies chance actions until `state` reaches a decision node or ends.

  Every driver in this package (bot evaluation, rollouts) needs this same
  bit of glue, since chance nodes aren't a `player`'s decision at all.
  """
  while not state.is_terminal() and state.is_chance_node():
    state.apply_action(sample_chance_action(state, rng))
