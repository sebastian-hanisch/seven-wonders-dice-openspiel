import pyspiel
import sevenwonders_dice  # noqa: F401
from sevenwonders_dice.boards import ALL_BOARDS
from sevenwonders_dice.player_state import PlayerState
from sevenwonders_dice.constants import BuildingKind, DieColor, EffectType
from sevenwonders_dice.effects import Effect, apply_immediate


class _FakeResolver:
  """Minimal resolver stub for testing effects in isolation."""

  def __init__(self):
    self.crossed = []
    self.unlocked = []

  def begin_cross(self, player, building, times=1):
    self.crossed.append((building, times))

  def queue_cross_one_of(self, player, buildings):
    self.crossed.append(("one_of", tuple(buildings)))

  def unlock_special_die(self, player, color):
    self.unlocked.append(color)


def _player():
  return PlayerState(ALL_BOARDS[0], 0)


def test_gain_coins():
  p, r = _player(), _FakeResolver()
  apply_immediate(Effect(EffectType.GAIN_COINS, amount=5), p, r)
  assert p.coins == PlayerState(ALL_BOARDS[0], 0).coins + 5


def test_flat_vp():
  p, r = _player(), _FakeResolver()
  apply_immediate(Effect(EffectType.FLAT_VP, amount=7), p, r)
  assert p.total_end_game_vp() == 7


def test_die_cost_zero():
  p, r = _player(), _FakeResolver()
  apply_immediate(Effect(EffectType.DIE_COST_ZERO, color=DieColor.RED), p, r)
  assert p.effective_die_cost(DieColor.RED, 3) == 0
  assert p.effective_die_cost(DieColor.BLUE, 3) == 3


def test_die_cost_minus_one_specific_and_global():
  p, r = _player(), _FakeResolver()
  apply_immediate(Effect(EffectType.DIE_COST_MINUS_1, color=DieColor.BLUE), p, r)
  assert p.effective_die_cost(DieColor.BLUE, 2) == 1
  apply_immediate(Effect(EffectType.DIE_COST_MINUS_1), p, r)  # all colors
  assert p.effective_die_cost(DieColor.BLUE, 2) == 0  # floored at 0
  assert p.effective_die_cost(DieColor.GREEN, 2) == 1


def test_coins_on_die_choice_stacks():
  p, r = _player(), _FakeResolver()
  apply_immediate(Effect(EffectType.COINS_ON_DIE_CHOICE, color=DieColor.GREY,
                          amount=2), p, r)
  apply_immediate(Effect(EffectType.COINS_ON_DIE_CHOICE, color=DieColor.GREY,
                          amount=2), p, r)
  assert p.coins_on_die_choice[DieColor.GREY] == 4


def test_unlock_die_delegates_to_resolver():
  p, r = _player(), _FakeResolver()
  apply_immediate(Effect(EffectType.UNLOCK_DIE, color=DieColor.BLACK), p, r)
  assert r.unlocked == [DieColor.BLACK]


def test_cross_space_delegates_to_resolver():
  p, r = _player(), _FakeResolver()
  apply_immediate(Effect(EffectType.CROSS_SPACE, building=BuildingKind.AGORA),
                   p, r)
  assert r.crossed == [(BuildingKind.AGORA, 1)]


def test_cross_up_to_two_delegates_to_resolver_with_times_2():
  p, r = _player(), _FakeResolver()
  apply_immediate(Effect(EffectType.CROSS_UP_TO_TWO,
                          building=BuildingKind.BARRACKS_WEST), p, r)
  assert r.crossed == [(BuildingKind.BARRACKS_WEST, 2)]


def test_cross_space_one_of_queues_a_bonus_choice():
  p, r = _player(), _FakeResolver()
  apply_immediate(Effect(EffectType.CROSS_SPACE_ONE_OF,
                          buildings=(BuildingKind.WAREHOUSE, BuildingKind.AGORA)),
                   p, r)
  assert r.crossed == [("one_of", (BuildingKind.WAREHOUSE, BuildingKind.AGORA))]


def test_coin_and_vp_per_space_pays_now_and_banks_multiplier():
  p, r = _player(), _FakeResolver()
  p.warehouse_crossed = 3
  before = p.coins
  apply_immediate(Effect(EffectType.COIN_AND_VP_PER_SPACE,
                          building=BuildingKind.WAREHOUSE, amount=2), p, r)
  assert p.coins == before + 2 * 3
  p.warehouse_crossed = 5  # more spaces crossed later...
  assert p.total_end_game_vp() == 2 * 5  # ...still count at game end


def test_gallery_vp_per_space_does_not_double_count_across_multiple_spaces():
  p, r = _player(), _FakeResolver()
  p.gallery_crossed = 1
  apply_immediate(Effect(EffectType.GALLERY_VP_PER_SPACE), p, r)
  p.gallery_crossed = 2
  apply_immediate(Effect(EffectType.GALLERY_VP_PER_SPACE), p, r)
  p.gallery_crossed = 4
  assert p.total_end_game_vp() == 4  # not 8
