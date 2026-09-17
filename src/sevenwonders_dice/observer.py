"""Human-readable observations (no tensor encoding -- see GameType)."""

from sevenwonders_dice.constants import QUADRANT_COSTS


class SevenWondersDiceObserver:
  """Observer, conforming to the PyObserver interface (see observation.py)."""

  def __init__(self, iig_obs_type, params):
    assert not bool(params)
    self.iig_obs_type = iig_obs_type
    self.tensor = None
    self.dict = {}

  def set_from(self, state, player):
    del state, player  # no tensor representation; see string_from

  def string_from(self, state, player):
    del player  # perfect information: everyone sees the same board state
    if state._phase == "DEAL":
      return "Dealing boards..."
    lines = [f"Phase: {state._phase}"]
    forum = ", ".join(
        f"{c.name}(cost {QUADRANT_COSTS[q]})"
        for c, q in zip(state._forum_colors, state._forum_quadrant))
    lines.append(f"Forum: {forum}")
    for i, ps in enumerate(state._players):
      if ps is None:
        continue
      lines.append(
          f"P{i} [{ps.board.city}]: coins={ps.coins} resources={ps.resources} "
          f"bonuses={ps.bonus_crossed} wonder={ps.wonder_crossed}/3 "
          f"vp_so_far={ps.total_end_game_vp()}")
    return "\n".join(lines)
