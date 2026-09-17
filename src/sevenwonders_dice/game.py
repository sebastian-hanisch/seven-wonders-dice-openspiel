"""pyspiel.Game definition + registration for 7 Wonders Dice."""

import pyspiel
from sevenwonders_dice.state import NUM_ROUND_ACTIONS, SevenWondersDiceState
from sevenwonders_dice.dice import NUM_SHAKE_OUTCOMES_PER_DIE
from sevenwonders_dice.boards import ALL_BOARDS

_NUM_DISTINCT_ACTIONS = max(NUM_ROUND_ACTIONS, NUM_SHAKE_OUTCOMES_PER_DIE,
                            len(ALL_BOARDS))
_MAX_CHANCE_OUTCOMES = max(NUM_SHAKE_OUTCOMES_PER_DIE, len(ALL_BOARDS))
_DEFAULT_NUM_PLAYERS = 4
_MIN_PLAYERS = 2
_MAX_PLAYERS = 7
_MAX_GAME_LENGTH = 1000

_GAME_TYPE = pyspiel.GameType(
    short_name="python_seven_wonders_dice",
    long_name="Python 7 Wonders Dice",
    dynamics=pyspiel.GameType.Dynamics.SIMULTANEOUS,
    chance_mode=pyspiel.GameType.ChanceMode.EXPLICIT_STOCHASTIC,
    information=pyspiel.GameType.Information.PERFECT_INFORMATION,
    utility=pyspiel.GameType.Utility.GENERAL_SUM,
    reward_model=pyspiel.GameType.RewardModel.TERMINAL,
    max_num_players=_MAX_PLAYERS,
    min_num_players=_MIN_PLAYERS,
    provides_information_state_string=False,
    provides_information_state_tensor=False,
    provides_observation_string=True,
    provides_observation_tensor=False,
    provides_factored_observation_string=False,
    parameter_specification={"players": _DEFAULT_NUM_PLAYERS},
)


class SevenWondersDiceGame(pyspiel.Game):
  """7 Wonders Dice (Antoine Bauza / Repos Production, 2025)."""

  def __init__(self, params=None):
    params = params or {}
    self._num_players = params.get("players", _DEFAULT_NUM_PLAYERS)
    game_info = pyspiel.GameInfo(
        num_distinct_actions=_NUM_DISTINCT_ACTIONS,
        max_chance_outcomes=_MAX_CHANCE_OUTCOMES,
        num_players=self._num_players,
        min_utility=0.0,
        max_utility=200.0,
        utility_sum=None,
        max_game_length=_MAX_GAME_LENGTH,
    )
    super().__init__(_GAME_TYPE, game_info, params)

  def new_initial_state(self):
    return SevenWondersDiceState(self, self._num_players)

  def make_py_observer(self, iig_obs_type=None, params=None):
    from sevenwonders_dice.observer import SevenWondersDiceObserver
    return SevenWondersDiceObserver(iig_obs_type, params)


pyspiel.register_game(_GAME_TYPE, SevenWondersDiceGame)
