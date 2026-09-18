"""SearchBot: OpenSpiel's own MCTSBot, made to work on this game.

The story of how this file got here is worth knowing before tuning it.

**Attempt 1 (superseded): a hand-rolled decoupled-UCB flat bandit.**
OpenSpiel's `open_spiel.python.algorithms.mcts.MCTSBot` requires
`GameType.dynamics == SEQUENTIAL` and refuses SIMULTANEOUS games outright
-- so the first version of this bot was a self-written 1-ply UCB1 bandit
over the root player's own actions, backed by full-game rollouts. It
worked, eventually, after two real bugs were found by actually measuring
it: the rollout policy needed to be something smarter than
uniform-random, and UCB1's exploration constant needed rescaling from
the textbook [0, 1] assumption to this game's VP-sized returns. It was
still a from-scratch reimplementation of something the framework already
has a mature version of, though.

**Attempt 2 (superseded): OpenSpiel's MCTSBot + RandomRolloutEvaluator.**
Exploiting the game's near-independence between players (a player's own
progress/VP/coins each round never depend on what anyone else
simultaneously picks -- see the solo-game explanation below) to run
OpenSpiel's *real* MCTSBot on a per-decision snapshot looked like the
obviously-correct fix for attempt 1's hand-rolled bandit. It compiled,
ran, and looked reasonable in a single-decision smoke test -- but a real
10-game tournament against plain HeuristicBot told a different story:
**0/10 wins**, average score 49 vs. 69. `RandomRolloutEvaluator` plays
fully random games to a true terminal state to value each expanded leaf
-- exactly the "random rollouts are a bad, noisy signal" problem attempt
1 had already hit and fixed, just moved into OpenSpiel's evaluator
instead of a hand-rolled one. Trusting "it's OpenSpiel's own algorithm,
it must be fine" instead of actually running the tournament would have
shipped a materially weaker bot than the one it replaced.

**This version: swap the evaluator, keep the tree search.** `HeuristicEvaluator`
below scores a node directly with the same VP/coins/resources/progress
heuristic `HeuristicBot` uses (see heuristic_bot.snapshot_value) instead
of simulating a random rollout to terminal. This is both cheaper (no
simulation at all -- the freed budget goes into `max_simulations`
instead) and far less noisy, since it's a deterministic function of the
state rather than one random sample of how the rest of a long game might
go. MCTSBot itself -- UCT selection, expansion, backpropagation -- is
untouched; only how a newly-expanded leaf gets its initial value changed.

**The solo-game trick, for context.** `game.py` registers a second,
SEQUENTIAL, 1-player variant of the exact same game
(`python_seven_wonders_dice_solo`) -- same `State` class; a 1-player
SIMULTANEOUS round already collapses to a plain sequential decision (see
`SevenWondersDiceState.current_player()`), so this was a few lines of
registration, not a rewrite. `SevenWondersDiceState.make_solo_snapshot()`
freezes the acting player's current progress and the live Forum into a
fresh solo-game state, at the exact decision point they're actually
facing, for MCTSBot to search from. The one thing this can't see is
opponents' *future* moves (e.g. someone else racing to end the game by
hitting 3 bonuses first) -- a small approximation given how little the
rulebook actually couples players within a round.

Before trusting a number here, run `examples/evaluate_bots.py` yourself:
none of the tuning claims above were true until they were measured.
"""

import numpy as np
import pyspiel
from open_spiel.python.algorithms import mcts

from sevenwonders_dice.bots.base import Bot
from sevenwonders_dice.bots.heuristic_bot import snapshot_value

_SOLO_GAME_NAME = "python_seven_wonders_dice_solo"


class HeuristicEvaluator(mcts.Evaluator):
  """Scores an MCTS leaf with HeuristicBot's heuristic instead of a random
  rollout -- see the module docstring for why that matters here."""

  def evaluate(self, state):
    if state.is_terminal():
      return np.array(state.returns(), dtype=float)
    return np.array([snapshot_value(state.player_state(0))], dtype=float)

  def prior(self, state):
    if state.is_chance_node():
      return state.chance_outcomes()
    legal = state.legal_actions(state.current_player())
    return [(a, 1.0 / len(legal)) for a in legal]


class SearchBot(Bot):
  """MCTS on a per-decision solo-game snapshot. See module docstring."""

  name = "Search"

  def __init__(self, max_simulations: int = 150, uct_c: float = 2.0,
               seed: int = None):
    self._solo_game = pyspiel.load_game(_SOLO_GAME_NAME)
    rng = np.random.RandomState(seed)
    evaluator = HeuristicEvaluator()
    self._mcts_bot = mcts.MCTSBot(
        self._solo_game, uct_c, max_simulations, evaluator,
        random_state=rng, solve=False)

  def step(self, state, player: int) -> int:
    solo_state = state.make_solo_snapshot(player, self._solo_game)
    return self._mcts_bot.step(solo_state)
