import random

from sevenwonders_dice.bots.base import Bot


class RandomBot(Bot):
  """Uniform random legal action. The baseline everything else should beat."""

  name = "Random"

  def __init__(self, rng: random.Random = None):
    self._rng = rng or random.Random()

  def step(self, state, player: int) -> int:
    return self._rng.choice(state.legal_actions(player))
