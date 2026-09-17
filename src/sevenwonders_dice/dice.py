"""Die faces and the Forum (shared dice pool) shake mechanic.

Each die has 6 faces; a face determines *which* building/lane/symbol-group a
die targets once picked (see module docstring in boards.py for provenance).
The physical "shake" is modeled as, for each of the 7 Forum dice
independently: a uniform-random face (6 outcomes) and a uniform-random
quadrant 0-3 (4 outcomes) -- i.e. 24 equiprobable outcomes per die, applied
as one small OpenSpiel chance node per die so nothing enumerates a huge
joint outcome space at once.
"""

import dataclasses
from typing import Optional, Tuple

from sevenwonders_dice.constants import BuildingKind, DieColor, QUADRANT_COSTS


@dataclasses.dataclass(frozen=True)
class DieFace:
  # Fixed-target colors (grey/yellow/white) leave everything else None.
  agora_group: Optional[int] = None          # BLUE: 0 or 1
  barracks_is_attack: Optional[bool] = None  # RED: True=attack, False=defense
  barracks_is_west: Optional[bool] = None    # RED: which side
  university_lane: Optional[str] = None      # GREEN: "black" | "purple" | "white"
  wildcard_building: Optional[BuildingKind] = None  # BLACK (Spy)
  guild_target: Optional[BuildingKind] = None       # PURPLE


# 6 faces per die color. RED/GREEN/BLACK/PURPLE encode real per-face choice;
# GREY/YELLOW/WHITE are single-target dice so all 6 faces are identical.
FACES = {
    DieColor.GREY: tuple(DieFace() for _ in range(6)),
    DieColor.YELLOW: tuple(DieFace() for _ in range(6)),
    DieColor.WHITE: tuple(DieFace() for _ in range(6)),
    DieColor.BLUE: tuple(DieFace(agora_group=i % 2) for i in range(6)),
    DieColor.RED: (
        DieFace(barracks_is_attack=True, barracks_is_west=False),   # East attack (sword)
        DieFace(barracks_is_attack=True, barracks_is_west=True),    # West attack (axe)
        DieFace(barracks_is_attack=False, barracks_is_west=False),  # East defense (shield)
        DieFace(barracks_is_attack=False, barracks_is_west=True),   # West defense (shield)
        DieFace(barracks_is_attack=True, barracks_is_west=False),
        DieFace(barracks_is_attack=True, barracks_is_west=True),
    ),
    DieColor.GREEN: (
        DieFace(university_lane="black"),
        DieFace(university_lane="black"),
        DieFace(university_lane="purple"),
        DieFace(university_lane="purple"),
        DieFace(university_lane="white"),
        DieFace(university_lane="white"),
    ),
    DieColor.BLACK: tuple(
        DieFace(wildcard_building=b) for b in (
            BuildingKind.WAREHOUSE, BuildingKind.AGORA,
            BuildingKind.BARRACKS_WEST, BuildingKind.BARRACKS_EAST,
            BuildingKind.MARKET, BuildingKind.UNIVERSITY,
        )
    ),
    DieColor.PURPLE: tuple(
        DieFace(guild_target=b) for b in (
            BuildingKind.WAREHOUSE, BuildingKind.AGORA,
            BuildingKind.BARRACKS_WEST, BuildingKind.BARRACKS_EAST,
            BuildingKind.MARKET, BuildingKind.UNIVERSITY,
        )
    ),
}

FACES_PER_DIE = 6
NUM_SHAKE_OUTCOMES_PER_DIE = FACES_PER_DIE * len(QUADRANT_COSTS)  # 24


def decode_shake_outcome(action: int) -> Tuple[int, int]:
  """action in [0, 24) -> (face_index in [0,6), quadrant in [0,4))."""
  return action // len(QUADRANT_COSTS), action % len(QUADRANT_COSTS)
