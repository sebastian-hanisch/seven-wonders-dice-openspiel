"""Effect dataclass + interpreter for the generic effect vocabulary.

The interpreter (`apply_effect`) is written against a small duck-typed
protocol (see `state.PlayerState`) rather than importing `state` directly,
to keep `boards.py` -> `effects.py` free of a dependency on `state.py`
(which itself depends on `boards.py`).
"""

import dataclasses
from typing import Optional, Sequence

from sevenwonders_dice.constants import BuildingKind, DieColor, EffectType


@dataclasses.dataclass(frozen=True)
class Effect:
  type: EffectType
  building: Optional[BuildingKind] = None
  buildings: Sequence[BuildingKind] = ()
  color: Optional[DieColor] = None
  amount: int = 0


def apply_immediate(effect: Effect, player, resolver) -> None:
  """Applies the immediate part of `effect` to `player`.

  `resolver` is the owning SevenWondersDiceState, used for anything that
  needs cross-player info or queues further decisions (extra actions).
  """
  t = effect.type
  if t == EffectType.CROSS_SPACE:
    resolver.auto_cross_space(player, effect.building)
  elif t == EffectType.CROSS_SPACE_ONE_OF:
    resolver.queue_cross_one_of(player, effect.buildings)
  elif t == EffectType.CROSS_UP_TO_TWO:
    resolver.auto_cross_space(player, effect.building)
    resolver.auto_cross_space(player, effect.building)
  elif t == EffectType.GAIN_COINS:
    player.coins += effect.amount
  elif t == EffectType.FREE_ACTION_A_NO_DIE_COST:
    player.pending_bonus_actions.append(("FREE_A", None))
  elif t == EffectType.TAKE_ANOTHER_ACTION:
    player.pending_bonus_actions.append(("ANY", None))
  elif t == EffectType.COIN_AND_VP_PER_SPACE:
    # One-time coin payout based on the count *right now*; the VP-per-space
    # part is banked as a standing end-game multiplier (final count applies).
    current = player.building_progress(effect.building)
    player.coins += effect.amount * current
    player.add_vp_per_space(effect.building, effect.amount)
  elif t == EffectType.DIE_COST_MINUS_1:
    if effect.color is None:
      player.die_cost_delta_all -= 1
    else:
      player.die_cost_delta[effect.color] = (
          player.die_cost_delta.get(effect.color, 0) - 1)
  elif t == EffectType.DIE_COST_ZERO:
    player.die_cost_zero.add(effect.color)
  elif t == EffectType.COINS_ON_DIE_CHOICE:
    player.coins_on_die_choice[effect.color] = (
        player.coins_on_die_choice.get(effect.color, 0) + effect.amount)
  elif t == EffectType.UNLOCK_DIE:
    resolver.unlock_special_die(player, effect.color)
  elif t == EffectType.FLAT_VP:
    player.banked_end_game_vp += effect.amount
  elif t == EffectType.GALLERY_VP_PER_SPACE:
    player.add_vp_per_space(BuildingKind.GALLERY, 1)
  else:
    raise ValueError(f"Unhandled effect type: {t}")
