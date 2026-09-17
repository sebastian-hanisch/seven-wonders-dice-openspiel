"""The 7 city boards.

Data source and confidence
---------------------------
Transcribed from real photographs of physical copies (not the generic
rulebook, which doesn't print per-board numbers as text — see RULES.md for
the full source list and per-section confidence notes). In short:

- Warehouse costs, the Barracks attack/defense track shape, the University's
  3-lane unlock structure, and the 3 bonus-slot effects were each confirmed
  across *multiple independent photos* of *multiple different boards* and
  read identically every time -> treated as a **shared template** used by
  all 7 boards (HIGH confidence; the asymmetry between cities lives in the
  Wonder and in which bonus/space effects sit where, not in base costs).
- The Giza board's Agora/Market/Guild Court numbers were read from clear
  macro photos (MEDIUM-HIGH confidence).
- The other 6 Wonders are real historical 7-Wonders-of-the-Ancient-World
  cities confirmed to be the game's city roster (via the group photo
  showing 6 of the 7 boards side by side), each given a unique, thematic
  3-step Wonder built from the confirmed effect vocabulary (MEDIUM
  confidence on exact costs/VP -- the *shape* of "3 escalating steps with
  a unique payoff" is confirmed, the specific numbers are a reasonable
  reconstruction pending a physical copy to verify against).

Nothing here reproduces the game's artwork or rulebook text -- only
structural/numeric data needed to run the simulation.
"""

import dataclasses
from typing import List, Optional, Sequence, Tuple

from sevenwonders_dice.constants import BuildingKind, DieColor, EffectType
from sevenwonders_dice.effects import Effect


@dataclasses.dataclass(frozen=True)
class Space:
  cost: int                          # resource cost (paid: resources, then coins for shortfall)
  effects: Tuple[Effect, ...] = ()   # crossed immediately on completion of this space
  printed_vp: int = 0                # Barracks attack spaces only: base VP before defense reduction
  agora_symbol_group: Optional[int] = None  # Agora spaces only: 0 or 1 (which blue-die symbols fill it)


@dataclasses.dataclass(frozen=True)
class BuildingDef:
  kind: BuildingKind
  spaces: Tuple[Space, ...]
  ordered: bool = True  # False only for Market (fillable in any order)


@dataclasses.dataclass(frozen=True)
class UniversityDef:
  """3 unlock lanes, each ending in unlocking one special die."""
  lane_black: Tuple[Space, ...]
  lane_purple: Tuple[Space, ...]
  lane_white: Tuple[Space, ...]


@dataclasses.dataclass(frozen=True)
class BarracksDef:
  attack: Tuple[Space, ...]   # crossed via the RED die's attack-this-side faces
  defense: Tuple[Space, ...]  # crossed via the RED die's defense-this-side faces


@dataclasses.dataclass(frozen=True)
class BoardDef:
  city: str
  wonder_name: str
  wonder: Tuple[Space, ...]
  warehouse: BuildingDef
  agora: BuildingDef
  agora_completion_bonus_vp: int
  market: BuildingDef
  university: UniversityDef
  guild_court: BuildingDef
  gallery: BuildingDef
  barracks_west: BarracksDef
  barracks_east: BarracksDef
  bonus_slots: Tuple[Effect, ...]
  source_note: str


# ---------------------------------------------------------------------------
# Shared template (confirmed identical across every photographed board).
# ---------------------------------------------------------------------------

def _standard_warehouse() -> BuildingDef:
  costs = (0, 0, 0, 1, 1, 1)
  return BuildingDef(
      kind=BuildingKind.WAREHOUSE,
      spaces=tuple(Space(cost=c) for c in costs),
  )


def _standard_barracks(side: BuildingKind) -> BarracksDef:
  del side  # symmetric; kept as a parameter for readability at call sites
  attack_costs = (0, 1, 2, 3, 4)
  attack_vp = (2, 3, 4, 5, 6)
  attack = tuple(Space(cost=c, printed_vp=vp)
                  for c, vp in zip(attack_costs, attack_vp))
  defense = (Space(cost=1), Space(cost=2))
  return BarracksDef(attack=attack, defense=defense)


def _standard_agora() -> Tuple[BuildingDef, int]:
  # 8 regular spaces (2 symbol groups x 4), ascending cost/VP; +3 bonus is a
  # separate top-right marker (not a numbered space), matching the rulebook.
  costs = (0, 1, 1, 2, 2, 3, 3, 4)
  vps = (1, 2, 2, 3, 3, 4, 4, 5)
  groups = (0, 1, 0, 1, 0, 1, 0, 1)
  spaces = tuple(
      Space(cost=c, agora_symbol_group=g,
            effects=(Effect(EffectType.FLAT_VP, amount=vp),))
      for c, vp, g in zip(costs, vps, groups)
  )
  return BuildingDef(kind=BuildingKind.AGORA, spaces=spaces), 3


def _standard_market() -> BuildingDef:
  # Any order; alternates immediate coins and a passive coin+end-VP building
  # bonus, matching "earn money / reduce costs / score end-game VP" (review).
  spaces = (
      Space(cost=1, effects=(Effect(EffectType.GAIN_COINS, amount=1),)),
      Space(cost=1, effects=(Effect(EffectType.GAIN_COINS, amount=2),)),
      Space(cost=2, effects=(Effect(EffectType.DIE_COST_MINUS_1,
                                     color=DieColor.YELLOW),)),
      Space(cost=2, effects=(Effect(EffectType.COIN_AND_VP_PER_SPACE,
                                     building=BuildingKind.MARKET, amount=1),)),
      Space(cost=3, effects=(Effect(EffectType.GAIN_COINS, amount=3),)),
      Space(cost=3, effects=(Effect(EffectType.FLAT_VP, amount=4),)),
  )
  return BuildingDef(kind=BuildingKind.MARKET, spaces=spaces, ordered=False)


def _standard_university() -> UniversityDef:
  # Confirmed structure from a clear macro photo: 3 lanes of 3 spaces each,
  # costs (2,3,4) / (3,4,5) / (0,3,6), each lane's final space unlocking one
  # special die (black/purple/white respectively).
  lane_black = (
      Space(cost=2, effects=(Effect(EffectType.GAIN_COINS, amount=1),)),
      Space(cost=3, effects=(Effect(EffectType.DIE_COST_ZERO,
                                     color=DieColor.GREEN),)),
      Space(cost=4, effects=(Effect(EffectType.UNLOCK_DIE,
                                     color=DieColor.BLACK),)),
  )
  lane_purple = (
      Space(cost=3, effects=(Effect(EffectType.COINS_ON_DIE_CHOICE,
                                     color=DieColor.RED, amount=2),)),
      Space(cost=4, effects=(Effect(EffectType.COIN_AND_VP_PER_SPACE,
                                     building=BuildingKind.UNIVERSITY, amount=1),)),
      Space(cost=5, effects=(Effect(EffectType.UNLOCK_DIE,
                                     color=DieColor.PURPLE),)),
  )
  lane_white = (
      Space(cost=0, effects=(Effect(EffectType.GAIN_COINS, amount=1),)),
      Space(cost=3, effects=(Effect(EffectType.CROSS_SPACE,
                                     building=BuildingKind.AGORA),)),
      Space(cost=6, effects=(Effect(EffectType.UNLOCK_DIE,
                                     color=DieColor.WHITE),)),
  )
  return UniversityDef(lane_black=lane_black, lane_purple=lane_purple,
                        lane_white=lane_white)


def _standard_guild_court() -> BuildingDef:
  costs = (2, 3, 4)
  vps = (5, 6, 7)
  spaces = tuple(Space(cost=c, effects=(Effect(EffectType.FLAT_VP, amount=vp),))
                 for c, vp in zip(costs, vps))
  return BuildingDef(kind=BuildingKind.GUILD_COURT, spaces=spaces)


def _standard_gallery() -> BuildingDef:
  costs = (1, 2, 3, 4)
  spaces = tuple(
      Space(cost=c, effects=(Effect(EffectType.GALLERY_VP_PER_SPACE),))
      for c in costs
  )
  return BuildingDef(kind=BuildingKind.GALLERY, spaces=spaces)


def _standard_bonus_slots() -> Tuple[Effect, ...]:
  # Confirmed identical icon set (refresh / multi-building / "7 coins") on
  # every photographed board.
  return (
      Effect(EffectType.TAKE_ANOTHER_ACTION),
      Effect(EffectType.CROSS_SPACE_ONE_OF,
             buildings=(BuildingKind.WAREHOUSE, BuildingKind.AGORA,
                        BuildingKind.MARKET)),
      Effect(EffectType.GAIN_COINS, amount=7),
  )


def _make_standard_board(city: str, wonder_name: str,
                          wonder: Sequence[Space],
                          source_note: str) -> BoardDef:
  agora, agora_bonus = _standard_agora()
  return BoardDef(
      city=city,
      wonder_name=wonder_name,
      wonder=tuple(wonder),
      warehouse=_standard_warehouse(),
      agora=agora,
      agora_completion_bonus_vp=agora_bonus,
      market=_standard_market(),
      university=_standard_university(),
      guild_court=_standard_guild_court(),
      gallery=_standard_gallery(),
      barracks_west=_standard_barracks(BuildingKind.BARRACKS_WEST),
      barracks_east=_standard_barracks(BuildingKind.BARRACKS_EAST),
      bonus_slots=_standard_bonus_slots(),
      source_note=source_note,
  )


# ---------------------------------------------------------------------------
# The 7 boards. Each Wonder is unique to its city; base buildings share the
# standard template above (see module docstring for confidence notes).
# ---------------------------------------------------------------------------

GIZA = _make_standard_board(
    city="Giza",
    wonder_name="The Great Pyramid",
    wonder=(
        Space(cost=3, effects=(Effect(EffectType.COIN_AND_VP_PER_SPACE,
                                       building=BuildingKind.WONDER, amount=2),)),
        Space(cost=1, effects=(Effect(EffectType.TAKE_ANOTHER_ACTION),)),
        Space(cost=7, effects=(Effect(EffectType.FLAT_VP, amount=7),)),
    ),
    source_note=("HIGH confidence: photographed in detail from 2 independent "
                  "sources (meepleandthemoose.com; whatsericplaying.com "
                  "gameplay-3-4.jpg) including its worked final-scoring "
                  "example (rulebook p.8: total 86 VP)."),
)

RHODES = _make_standard_board(
    city="Rhodes",
    wonder_name="The Colossus of Rhodes",
    wonder=(
        Space(cost=2, effects=(Effect(EffectType.COINS_ON_DIE_CHOICE,
                                       color=DieColor.RED, amount=2),)),
        Space(cost=4, effects=(Effect(EffectType.CROSS_UP_TO_TWO,
                                       building=BuildingKind.BARRACKS_WEST),)),
        Space(cost=6, effects=(Effect(EffectType.FLAT_VP, amount=8),)),
    ),
    source_note=("MEDIUM confidence: board visible in the nerdly.co.uk group "
                  "photo (coastal statue skyline); Wonder numbers are a "
                  "reasonable reconstruction, not a confirmed transcription."),
)

ALEXANDRIA = _make_standard_board(
    city="Alexandria",
    wonder_name="The Lighthouse of Alexandria",
    wonder=(
        Space(cost=2, effects=(Effect(EffectType.GAIN_COINS, amount=4),)),
        Space(cost=3, effects=(Effect(EffectType.DIE_COST_ZERO,
                                       color=DieColor.GREY),)),
        Space(cost=6, effects=(Effect(EffectType.FLAT_VP, amount=7),
                                Effect(EffectType.GAIN_COINS, amount=3))),
    ),
    source_note=("MEDIUM confidence: board visible in the nerdly.co.uk group "
                  "photo (lighthouse/desert skyline); Wonder numbers are a "
                  "reasonable reconstruction, not a confirmed transcription."),
)

BABYLON = _make_standard_board(
    city="Babylon",
    wonder_name="The Hanging Gardens of Babylon",
    wonder=(
        Space(cost=2, effects=(Effect(EffectType.CROSS_SPACE,
                                       building=BuildingKind.UNIVERSITY),)),
        Space(cost=4, effects=(Effect(EffectType.COIN_AND_VP_PER_SPACE,
                                       building=BuildingKind.AGORA, amount=1),)),
        Space(cost=6, effects=(Effect(EffectType.FLAT_VP, amount=8),)),
    ),
    source_note=("MEDIUM confidence: board visible in the nerdly.co.uk group "
                  "photo (garden skyline); Wonder numbers are a reasonable "
                  "reconstruction, not a confirmed transcription."),
)

OLYMPIA = _make_standard_board(
    city="Olympia",
    wonder_name="The Statue of Zeus",
    wonder=(
        Space(cost=3, effects=(Effect(EffectType.GAIN_COINS, amount=3),)),
        Space(cost=3, effects=(Effect(EffectType.FREE_ACTION_A_NO_DIE_COST),)),
        Space(cost=7, effects=(Effect(EffectType.FLAT_VP, amount=9),)),
    ),
    source_note=("LOW-MEDIUM confidence: inferred as the 7th city from the "
                  "standard 7-Wonders roster (not clearly distinguished in "
                  "the group photo); Wonder numbers are a placeholder-grade "
                  "reconstruction pending a clearer source photo."),
)

EPHESUS = _make_standard_board(
    city="Ephesus",
    wonder_name="The Temple of Artemis",
    wonder=(
        Space(cost=2, effects=(Effect(EffectType.CROSS_SPACE,
                                       building=BuildingKind.MARKET),)),
        Space(cost=4, effects=(Effect(EffectType.DIE_COST_MINUS_1),)),  # all colors
        Space(cost=6, effects=(Effect(EffectType.FLAT_VP, amount=8),)),
    ),
    source_note=("LOW-MEDIUM confidence: inferred as one of the 7-Wonders "
                  "roster cities; Wonder numbers are a placeholder-grade "
                  "reconstruction pending a clearer source photo."),
)

HALICARNASSUS = _make_standard_board(
    city="Halicarnassus",
    wonder_name="The Mausoleum at Halicarnassus",
    wonder=(
        Space(cost=2, effects=(Effect(EffectType.GAIN_COINS, amount=2),
                                Effect(EffectType.FLAT_VP, amount=1))),
        Space(cost=4, effects=(Effect(EffectType.CROSS_SPACE_ONE_OF,
                                       buildings=(BuildingKind.BARRACKS_WEST,
                                                  BuildingKind.BARRACKS_EAST)),)),
        Space(cost=7, effects=(Effect(EffectType.FLAT_VP, amount=9),)),
    ),
    source_note=("LOW-MEDIUM confidence: inferred as one of the 7-Wonders "
                  "roster cities; Wonder numbers are a placeholder-grade "
                  "reconstruction pending a clearer source photo."),
)

ALL_BOARDS: Tuple[BoardDef, ...] = (
    GIZA, RHODES, ALEXANDRIA, BABYLON, OLYMPIA, EPHESUS, HALICARNASSUS,
)
