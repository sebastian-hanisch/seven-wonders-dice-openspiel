"""7 Wonders Dice as an OpenSpiel game.

Importing this package registers "python_seven_wonders_dice" with pyspiel:

    import pyspiel
    import sevenwonders_dice
    game = pyspiel.load_game("python_seven_wonders_dice", {"players": 3})
"""

from sevenwonders_dice import game as _game  # noqa: F401  (registers the game)

__all__ = []
