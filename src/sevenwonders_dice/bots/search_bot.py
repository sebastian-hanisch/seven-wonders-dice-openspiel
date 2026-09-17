"""A Monte Carlo search bot for this game's SIMULTANEOUS dynamics.

OpenSpiel's built-in MCTS (`open_spiel.python.algorithms.mcts`) assumes a
single actor per tree node and doesn't apply directly to SIMULTANEOUS
games. This is a self-contained "decoupled" approach instead, standard
for simultaneous-move search (the same idea behind e.g. Decoupled UCT):

  1. At the root, run UCB1 as a flat multi-armed bandit over *our own*
     legal actions (each action is one arm; no combinatorial blow-up from
     also branching on opponents' choices).
  2. Each simulation: fix our action, let `rollout_policy` act for
     everyone else *and* for every player, including us, for a short
     horizon of further decisions (default: HeuristicBot -- see below for
     why plain random rollouts measurably hurt this bot).
  3. At the horizon (or at a true terminal state, whichever comes first),
     score the resulting position with the same VP/coins/resources/
     progress heuristic `HeuristicBot` uses, and backpropagate that to
     the arm we pulled.
  4. After the rollout budget is spent, play the arm with the highest
     mean return.

This is deliberately simpler than a full multi-level simultaneous game
tree (which would need per-node decoupled bandits at every future
decision too) -- it's a 1-ply decoupled bandit with short, heuristically-
guided rollouts, rather than a full multi-ply tree.

Two calibration points that mattered in practice (found by actually
evaluating this bot, not just reading the code):

- **Rollout policy matters more than rollout depth.** An earlier version
  used uniform-random rollouts to a true terminal state. It was slow (one
  real game ≈ 24s with a 64-rollout budget) *and*, worse, lost the
  majority of games against plain `HeuristicBot`: simulating "what
  happens if everyone including my opponent plays randomly from here"
  is a poor model of what an actual (non-random) opponent will do, so
  the root action it preferred often wasn't the one that was actually
  best against a competent opponent. Using `HeuristicBot` for the
  rollout policy and cutting rollouts short (`horizon_decisions`) instead
  of always running to terminal fixed both problems at once.
- **UCB1's exploration bonus needs to match the reward scale.** The
  textbook `c = sqrt(2)` assumes rewards roughly in [0, 1]; this game's
  returns are raw Victory Point totals (commonly ~20-100). Left
  uncorrected, the bonus term is negligible next to the mean term and
  UCB1 degenerates into almost-pure greedy exploitation after the first
  seeding pass. `exploration_constant` here is applied to rewards
  normalized by `_REWARD_SCALE` instead, so the default value still
  behaves like the textbook constant.
"""

import math
import random

from sevenwonders_dice.bots.base import Bot
from sevenwonders_dice.bots.driver import step_one_decision
from sevenwonders_dice.bots.heuristic_bot import HeuristicBot, snapshot_value

_REWARD_SCALE = 100.0  # rough max_utility scale for this game (see game.py)


class _FixedFirstActionBot(Bot):
  """Plays `first_action` on its very first call, then defers to `policy`.
  Lets `SearchBot` reuse the ordinary game-loop driver for the root move."""

  def __init__(self, first_action: int, policy: Bot):
    self._first_action = first_action
    self._used = False
    self._policy = policy

  def step(self, state, player: int) -> int:
    if not self._used:
      self._used = True
      return self._first_action
    return self._policy.step(state, player)


class SearchBot(Bot):
  """See module docstring."""

  name = "Search"

  def __init__(self, num_rollouts: int = 16, rollout_policy: Bot = None,
               exploration_constant: float = 1.4,
               horizon_decisions: int = 6,
               rng: random.Random = None):
    self._num_rollouts = num_rollouts
    # bonus_chain_depth=0: a rollout runs this up to
    # num_rollouts * horizon_decisions * num_players times per real
    # decision, so it needs to be cheap -- no recursive bonus-chain
    # lookahead, just a single clone+score per candidate action. Still
    # avoids HeuristicBot's original PASS-spam failure mode (see
    # heuristic_bot.py) since the progress/VP/coin scoring itself is
    # unchanged; it just doesn't additionally plan 2 bonus-chain steps
    # ahead the way the standalone HeuristicBot does.
    self._rollout_policy = rollout_policy or HeuristicBot(bonus_chain_depth=0)
    self._c = exploration_constant
    self._horizon_decisions = horizon_decisions
    self._rng = rng or random.Random()

  def step(self, state, player: int) -> int:
    legal = state.legal_actions(player)
    if len(legal) == 1:
      return legal[0]

    counts = {a: 0 for a in legal}
    totals = {a: 0.0 for a in legal}
    total_n = 0

    # Seed every arm once so UCB1's log(total_n)/count term is well-defined.
    for a in legal:
      totals[a] += self._simulate(state, player, a)
      counts[a] += 1
      total_n += 1

    for _ in range(max(0, self._num_rollouts - len(legal))):
      a = self._select_ucb(legal, counts, totals, total_n)
      totals[a] += self._simulate(state, player, a)
      counts[a] += 1
      total_n += 1

    return max(legal, key=lambda a: totals[a] / counts[a])

  def _select_ucb(self, legal, counts, totals, total_n):
    best_action, best_score = legal[0], -math.inf
    for a in legal:
      mean = totals[a] / counts[a] / _REWARD_SCALE
      bonus = self._c * math.sqrt(math.log(total_n) / counts[a])
      score = mean + bonus
      if score > best_score:
        best_score, best_action = score, a
    return best_action

  def _simulate(self, state, player: int, action: int) -> float:
    clone = state.clone()
    bots = [self._rollout_policy] * clone.num_players()
    bots[player] = _FixedFirstActionBot(action, self._rollout_policy)

    decisions = 0
    while not clone.is_terminal() and decisions < self._horizon_decisions:
      step_one_decision(clone, bots, self._rng)
      decisions += 1

    if clone.is_terminal():
      return clone.returns()[player]
    # Horizon reached without a true terminal state: score the position
    # with the same heuristic HeuristicBot uses (VP + coins + resources +
    # building progress), not just banked VP, so partially-built progress
    # this rollout made still counts.
    return snapshot_value(clone.player_state(player))
