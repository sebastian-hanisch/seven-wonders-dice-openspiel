"""A lookahead-free-ish heuristic bot: for each legal action, clones the
state, applies it (other players PASS -- see note below), and scores the
resulting position. Greedily resolves any of its own follow-up BONUS
decisions the same way, up to a small depth, then picks the best root
action.

Why "other players PASS" is a safe stand-in during evaluation: dice are
never removed from the Forum (RULES.md), so within one round a player's
own resulting building progress and VP never depends on what anyone else
picks that same round -- only on the shake and their own choice. It's
used purely as a scoring device here, not a prediction of what opponents
will actually do.
"""

import math

import pyspiel

from sevenwonders_dice.bots.base import Bot
from sevenwonders_dice.constants import BuildingKind
from sevenwonders_dice.state import ACTION_PASS

VP_WEIGHT = 1.0
COIN_WEIGHT = 0.15
RESOURCE_WEIGHT = 0.4
# Crossing a space is worth more than its raw resource/coin conversion
# suggests: it's progress toward a building's completion bonus (extra
# coins/actions/cross-2-spaces -- see the effect catalog in RULES.md) and
# toward unlocking special dice. Without this term the bot systematically
# undervalues building relative to the guaranteed +3 coins from passing
# (found by instrumenting self-play: ~70% PASS actions -- clearly wrong
# for a game about building a city).
PROGRESS_WEIGHT = 1.2

_ALL_BUILDINGS_FOR_PROGRESS = (
    BuildingKind.WAREHOUSE, BuildingKind.AGORA, BuildingKind.MARKET,
    BuildingKind.UNIVERSITY, BuildingKind.GUILD_COURT, BuildingKind.GALLERY,
    BuildingKind.BARRACKS_WEST, BuildingKind.BARRACKS_EAST, BuildingKind.WONDER,
)


def _total_progress(ps) -> int:
  return sum(ps.building_progress(b) for b in _ALL_BUILDINGS_FOR_PROGRESS)


def snapshot_value(ps) -> float:
  return (ps.total_end_game_vp() * VP_WEIGHT +
          ps.coins * COIN_WEIGHT +
          ps.resources * RESOURCE_WEIGHT +
          _total_progress(ps) * PROGRESS_WEIGHT)


def _best_continuation_value(clone, player: int, depth: int, max_depth: int) -> float:
  """Best value `player` can reach from `clone`, greedily resolving their
  own further immediate decisions (BONUS-phase chains) up to `max_depth`
  levels; falls back to a snapshot once it's no longer purely `player`'s
  decision or the depth budget runs out."""
  if clone.is_terminal():
    return snapshot_value(clone.player_state(player))
  if depth >= max_depth or clone.current_player() != player:
    return snapshot_value(clone.player_state(player))
  best = -math.inf
  for action in clone.legal_actions(player):
    child = clone.clone()
    child.apply_action(action)
    best = max(best, _best_continuation_value(child, player, depth + 1, max_depth))
  return best


class HeuristicBot(Bot):
  """Greedy 1-round lookahead with a short self-only BONUS-chain resolve."""

  name = "Heuristic"

  def __init__(self, bonus_chain_depth: int = 2):
    self._bonus_chain_depth = bonus_chain_depth

  def step(self, state, player: int) -> int:
    legal = state.legal_actions(player)
    if len(legal) == 1:
      return legal[0]

    best_action, best_value = legal[0], -math.inf
    for action in legal:
      child = state.clone()
      if child.current_player() == pyspiel.PlayerId.SIMULTANEOUS:
        actions = [ACTION_PASS] * child.num_players()
        actions[player] = action
        child.apply_actions(actions)
      else:
        child.apply_action(action)
      value = _best_continuation_value(child, player, 0, self._bonus_chain_depth)
      if value > best_value:
        best_value, best_action = value, action
    return best_action
