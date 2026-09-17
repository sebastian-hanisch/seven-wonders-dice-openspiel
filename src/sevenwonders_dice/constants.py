"""Shared enums and constants for the 7 Wonders Dice OpenSpiel implementation."""

import enum


class DieColor(enum.IntEnum):
  """The 8 die colors. GREY/BLUE/RED/YELLOW/GREEN start in the Forum;
  BLACK/WHITE/PURPLE are unlocked during play (see University)."""
  GREY = 0
  BLUE = 1
  RED = 2
  YELLOW = 3
  GREEN = 4
  BLACK = 5
  WHITE = 6
  PURPLE = 7


STARTING_DICE = (
    DieColor.GREY, DieColor.GREY, DieColor.GREY,
    DieColor.BLUE, DieColor.RED, DieColor.YELLOW, DieColor.GREEN,
)
SPECIAL_DICE = (DieColor.BLACK, DieColor.WHITE, DieColor.PURPLE)
NUM_FORUM_DICE = 7
NUM_QUADRANTS = 4
QUADRANT_COSTS = (0, 1, 2, 3)


class BuildingKind(enum.IntEnum):
  """The building types every board has one of (Barracks is split W/E)."""
  WAREHOUSE = 0        # grey
  AGORA = 1             # blue
  BARRACKS_WEST = 2     # red (attack west-neighbor / defend against them)
  BARRACKS_EAST = 3     # red (attack east-neighbor / defend against them)
  MARKET = 4            # yellow
  UNIVERSITY = 5        # green
  GUILD_COURT = 6       # purple (unlocked)
  GALLERY = 7           # white (unlocked)
  WONDER = 8            # no die needed


# Buildings a player can compare themselves against on the Guild Court /
# that the Spy (black die) can directly advance. Wonder excluded (no die).
COMPARABLE_BUILDINGS = (
    BuildingKind.WAREHOUSE, BuildingKind.AGORA, BuildingKind.BARRACKS_WEST,
    BuildingKind.BARRACKS_EAST, BuildingKind.MARKET, BuildingKind.UNIVERSITY,
)

DIE_TO_BUILDING = {
    DieColor.GREY: BuildingKind.WAREHOUSE,
    DieColor.BLUE: BuildingKind.AGORA,
    DieColor.RED: None,  # resolved per-face: BARRACKS_WEST or BARRACKS_EAST
    DieColor.YELLOW: BuildingKind.MARKET,
    DieColor.GREEN: BuildingKind.UNIVERSITY,
    DieColor.WHITE: BuildingKind.GALLERY,
    DieColor.PURPLE: BuildingKind.GUILD_COURT,
    # BLACK (Spy) is wildcard: resolved per-face to any COMPARABLE_BUILDINGS.
}


class ActionType(enum.IntEnum):
  """The 3 choices every player simultaneously makes each round."""
  CONSTRUCT_BUILDING = 0  # requires picking one of the 7 Forum dice too
  CONSTRUCT_WONDER = 1
  PASS = 2


class EffectType(enum.IntEnum):
  """The complete effect vocabulary from the official Player Aid."""
  CROSS_SPACE = 0                 # cross a space of `building`
  CROSS_SPACE_ONE_OF = 1          # cross a space of any one of `buildings`
  CROSS_UP_TO_TWO = 2             # cross up to two spaces of `building`
  GAIN_COINS = 3                  # gain `amount` coins now
  FREE_ACTION_A_NO_DIE_COST = 4   # take action A now, die cost waived
  TAKE_ANOTHER_ACTION = 5         # take another A/B/C now, same Forum config
  COIN_AND_VP_PER_SPACE = 6       # now: `amount` coins/space; end: `amount` VP/space of `building`
  DIE_COST_MINUS_1 = 7            # permanent: die cost of `color` (or all) -1
  DIE_COST_ZERO = 8               # permanent: die cost of `color` is 0
  COINS_ON_DIE_CHOICE = 9         # permanent: +`amount` coins whenever `color` die chosen
  UNLOCK_DIE = 10                 # permanent: unlock `color` (black/white/purple) into the Forum
  FLAT_VP = 11                    # end of game: gain `amount` VP
  GALLERY_VP_PER_SPACE = 12       # end of game: 1 VP per crossed Gallery space (incl. this one)


PASS_COINS = 3
BONUSES_TO_END_GAME = 3
