"""SearchBot: OpenSpiel's own MCTSBot, made to work on this game.

The story of how this file got here is worth knowing before tuning it.

**First attempt (superseded): a hand-rolled decoupled-UCB flat bandit.**
OpenSpiel's `open_spiel.python.algorithms.mcts.MCTSBot` requires
`GameType.dynamics == SEQUENTIAL` and refuses SIMULTANEOUS games outright
-- so the first version of this bot was a self-written 1-ply UCB1 bandit
over the root player's own actions, backed by full-game rollouts. It
worked, eventually, after two real bugs were found by actually measuring
it (not just reading the code): the rollout policy needed to be something
smarter than uniform-random (random-to-terminal rollouts lost most games
to plain HeuristicBot -- a bad model of a competent opponent), and UCB1's
exploration constant needed to be rescaled from the textbook [0, 1]
assumption to this game's VP-sized returns. Once fixed, it worked
reasonably well -- but it was still a from-scratch reimplementation of
something OpenSpiel already has a mature, well-tested version of.

**This version: exploit the game's actual structure instead.** A
player's own progress, coins and VP this round never depend on what
anyone else simultaneously picks -- dice are never removed from the
Forum (RULES.md) -- only on the shake and their own choice. The *only*
things opponents contribute to a decision are their *current standing*
(for Guild Court/Barracks comparisons). That makes one player's decision
problem close to a solitaire MDP, not a genuinely multi-agent one. So:

  - `game.py` registers a second, SEQUENTIAL, 1-player variant of the
    exact same game (`python_seven_wonders_dice_solo`) -- same State
    class; a 1-player SIMULTANEOUS round already collapses to a plain
    sequential decision (see `SevenWondersDiceState.current_player()`),
    so this is a few lines of registration, not a rewrite.
  - `SevenWondersDiceState.make_solo_snapshot()` freezes the acting
    player's current progress and the live Forum into a fresh solo-game
    state, at the exact decision point they're actually facing.
  - OpenSpiel's real `MCTSBot` (proper multi-ply UCT tree search,
    battle-tested, no hand-tuned exploration constant needed) solves
    that snapshot directly.

This is both more principled and, per informal comparison, at least as
strong as the hand-rolled version -- without carrying a second bespoke
search implementation. The one thing it can't see is opponents' *future*
moves (e.g. someone else racing to end the game by hitting 3 bonuses
first); that residual approximation is the price of decomposing the
search this way, and it's a small one given how little the rulebook
actually couples players within a round.
"""

import numpy as np
import pyspiel
from open_spiel.python.algorithms import mcts

from sevenwonders_dice.bots.base import Bot

_SOLO_GAME_NAME = "python_seven_wonders_dice_solo"


class SearchBot(Bot):
  """MCTS on a per-decision solo-game snapshot. See module docstring."""

  name = "Search"

  def __init__(self, max_simulations: int = 100, uct_c: float = 2.0,
               n_rollouts: int = 2, seed: int = None):
    self._solo_game = pyspiel.load_game(_SOLO_GAME_NAME)
    rng = np.random.RandomState(seed)
    evaluator = mcts.RandomRolloutEvaluator(n_rollouts=n_rollouts, random_state=rng)
    self._mcts_bot = mcts.MCTSBot(
        self._solo_game, uct_c, max_simulations, evaluator,
        random_state=rng, solve=False)

  def step(self, state, player: int) -> int:
    solo_state = state.make_solo_snapshot(player, self._solo_game)
    return self._mcts_bot.step(solo_state)
