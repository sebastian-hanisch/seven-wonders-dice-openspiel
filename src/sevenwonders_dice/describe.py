"""Human-readable text for buildings, effects and actions -- used by the
Streamlit app (app.py) and handy for debugging/observers generally.
Deliberately has no dependency on state.py (state.py depends on this, not
the other way around) so it stays easy to reuse.
"""

from typing import Sequence

from sevenwonders_dice.constants import BuildingKind, DieColor, EffectType
from sevenwonders_dice.effects import Effect

BUILDING_NAMES = {
    BuildingKind.WAREHOUSE: "Warehouse",
    BuildingKind.AGORA: "Agora",
    BuildingKind.BARRACKS_WEST: "Western Barracks",
    BuildingKind.BARRACKS_EAST: "Eastern Barracks",
    BuildingKind.MARKET: "Market",
    BuildingKind.UNIVERSITY: "University",
    BuildingKind.GUILD_COURT: "Guild Court",
    BuildingKind.GALLERY: "Gallery of Leaders",
    BuildingKind.WONDER: "Wonder",
}

DIE_COLOR_NAMES = {
    DieColor.GREY: "Grey",
    DieColor.BLUE: "Blue",
    DieColor.RED: "Red",
    DieColor.YELLOW: "Yellow",
    DieColor.GREEN: "Green",
    DieColor.BLACK: "Black (Spy)",
    DieColor.WHITE: "White (Gallery)",
    DieColor.PURPLE: "Purple (Guild Court)",
}


def describe_effect(effect: Effect) -> str:
  t = effect.type
  if t == EffectType.CROSS_SPACE:
    return f"cross a space of {BUILDING_NAMES[effect.building]}"
  if t == EffectType.CROSS_SPACE_ONE_OF:
    names = " or ".join(BUILDING_NAMES[b] for b in effect.buildings)
    return f"cross a space of {names}"
  if t == EffectType.CROSS_UP_TO_TWO:
    return f"cross up to 2 spaces of {BUILDING_NAMES[effect.building]}"
  if t == EffectType.GAIN_COINS:
    return f"gain {effect.amount} coins"
  if t == EffectType.FREE_ACTION_A_NO_DIE_COST:
    return "take a free Build action (no die cost)"
  if t == EffectType.TAKE_ANOTHER_ACTION:
    return "take another action"
  if t == EffectType.COIN_AND_VP_PER_SPACE:
    return (f"gain {effect.amount} coins now + {effect.amount} VP per "
            f"crossed space of {BUILDING_NAMES[effect.building]} at game end")
  if t == EffectType.DIE_COST_MINUS_1:
    color = DIE_COLOR_NAMES[effect.color] if effect.color is not None else "all dice"
    return f"{color} cost -1 (permanent)"
  if t == EffectType.DIE_COST_ZERO:
    return f"{DIE_COLOR_NAMES[effect.color]} cost is now 0 (permanent)"
  if t == EffectType.COINS_ON_DIE_CHOICE:
    return f"+{effect.amount} coins whenever you pick a {DIE_COLOR_NAMES[effect.color]} die"
  if t == EffectType.UNLOCK_DIE:
    return f"unlock the {DIE_COLOR_NAMES[effect.color]} die"
  if t == EffectType.FLAT_VP:
    return f"gain {effect.amount} VP"
  if t == EffectType.GALLERY_VP_PER_SPACE:
    return "gain 1 VP per crossed Gallery space at game end"
  raise ValueError(t)


def describe_effects(effects: Sequence[Effect]) -> str:
  if not effects:
    return "no effect"
  return "; ".join(describe_effect(e) for e in effects)
