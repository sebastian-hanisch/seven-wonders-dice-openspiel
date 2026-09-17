import pyspiel
import sevenwonders_dice  # noqa: F401  (registers the game)


def test_game_is_registered():
  assert "python_seven_wonders_dice" in pyspiel.registered_names()


def test_load_default():
  game = pyspiel.load_game("python_seven_wonders_dice")
  assert game.num_players() == 4


def test_load_with_player_count():
  for n in (2, 3, 5, 7):
    game = pyspiel.load_game("python_seven_wonders_dice", {"players": n})
    assert game.num_players() == n
    state = game.new_initial_state()
    assert state.current_player() == pyspiel.PlayerId.CHANCE
