"""Mutable per-player game state."""

import copy
from typing import Dict, List, Set

from sevenwonders_dice.boards import BoardDef
from sevenwonders_dice.constants import BuildingKind, DieColor

WAREHOUSE_SPACES = 6
AGORA_SPACES = 8
MARKET_SPACES = 6
UNIVERSITY_LANE_SPACES = 3
GUILD_COURT_SPACES = 3
GALLERY_SPACES = 4
BARRACKS_ATTACK_SPACES = 5
BARRACKS_DEFENSE_SPACES = 2
WONDER_SPACES = 3
NUM_BONUS_SLOTS = 3
STARTING_COINS = 7


class PlayerState:
  """All progress/economy tracking for one player. Deep-copied on clone."""

  def __init__(self, board: BoardDef, board_index: int):
    self.board = board
    self.board_index = board_index

    self.resources = 0
    self.coins = STARTING_COINS

    self.warehouse_crossed = 0
    self.agora_crossed = 0
    self.market_crossed_mask = 0
    self.univ_lane_progress: Dict[str, int] = {"black": 0, "purple": 0, "white": 0}
    self.guild_crossed = 0
    self.gallery_crossed = 0
    self.barracks_w_attack = 0
    self.barracks_w_defense = 0
    self.barracks_e_attack = 0
    self.barracks_e_defense = 0
    self.wonder_crossed = 0

    self.bonus_crossed = 0
    self.bonus_used_mask = 0

    self.die_cost_delta: Dict[DieColor, int] = {}
    self.die_cost_delta_all = 0
    self.die_cost_zero: Set[DieColor] = set()
    self.coins_on_die_choice: Dict[DieColor, int] = {}
    self.banked_end_game_vp = 0
    self.barracks_vp_total = 0
    self.unlocked_by_me: Set[DieColor] = set()
    # building -> VP granted per crossed space of that building at game end.
    # A dict (not a list) so triggering the same building's per-space bonus
    # more than once (e.g. it sits on multiple spaces) doesn't double-count.
    self.vp_per_space_rates: Dict[BuildingKind, int] = {}

    self.pending_bonus_actions: List[tuple] = []  # [("ANY"|"FREE_A"|"CHOOSE_BONUS", None)]

  def clone(self) -> "PlayerState":
    return copy.deepcopy(self)

  # -- helpers -----------------------------------------------------------

  def building_progress(self, kind: BuildingKind) -> int:
    if kind == BuildingKind.WAREHOUSE:
      return self.warehouse_crossed
    if kind == BuildingKind.AGORA:
      return self.agora_crossed
    if kind == BuildingKind.MARKET:
      return bin(self.market_crossed_mask).count("1")
    if kind == BuildingKind.UNIVERSITY:
      return sum(self.univ_lane_progress.values())
    if kind == BuildingKind.GUILD_COURT:
      return self.guild_crossed
    if kind == BuildingKind.GALLERY:
      return self.gallery_crossed
    if kind == BuildingKind.BARRACKS_WEST:
      return self.barracks_w_attack + self.barracks_w_defense
    if kind == BuildingKind.BARRACKS_EAST:
      return self.barracks_e_attack + self.barracks_e_defense
    if kind == BuildingKind.WONDER:
      return self.wonder_crossed
    raise ValueError(kind)

  def effective_die_cost(self, color: DieColor, quadrant_cost: int) -> int:
    if color in self.die_cost_zero:
      return 0
    cost = quadrant_cost + self.die_cost_delta_all + self.die_cost_delta.get(color, 0)
    return max(0, cost)

  def pay(self, resource_cost: int, coin_cost: int = 0) -> None:
    use_resources = min(self.resources, resource_cost)
    self.resources -= use_resources
    shortfall = resource_cost - use_resources
    self.coins -= (shortfall + coin_cost)

  def can_pay(self, resource_cost: int, coin_cost: int = 0) -> bool:
    shortfall = max(0, resource_cost - self.resources)
    return self.coins >= (shortfall + coin_cost)

  def add_vp_per_space(self, building: BuildingKind, rate: int) -> None:
    self.vp_per_space_rates[building] = max(self.vp_per_space_rates.get(building, 0), rate)

  def total_end_game_vp(self) -> int:
    vp = self.banked_end_game_vp + self.barracks_vp_total
    for building, rate in self.vp_per_space_rates.items():
      vp += rate * self.building_progress(building)
    return vp
